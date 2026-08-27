#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys

import polars as pl
from polars.exceptions import ShapeError

from annotations import base36_encode, extract_cdrs_fr1, parse_annotations
from definitions import (
    FIXABILITY_MAP,
    ORIG_CYS_LIABILITIES,
    ORIG_EXTRA_PATTERNS,
    ORIG_REGEX_LIABILITIES,
    REGION_ORDER_MAP,
    build_expected_cys_map,
    get_active_liability_definitions,
)
from detection import (
    _build_risk_level_map,
    _evaluate_cys_liabilities,
    _get_expected_cys_positions,
    classify_risk,
    identify_liabilities,
)
from scoring import (
    classify_developability_risk,
    compute_developability_score,
)

# Canonical region names. _column_region uses whole-word matching.
CANONICAL_REGIONS = ["CDR1", "CDR2", "CDR3", "FR1", "FR2", "FR3", "FR4"]

# Chains arrive as receptor-neutral slots; --chain-labels carries the display names.
CHAIN_SLOTS = ("A", "B")
DEFAULT_CHAIN_LABELS = {"A": "Heavy", "B": "Light"}


def _column_region(col_name: str) -> str | None:
    """Map a sequence/fragment column name to its canonical region, or None.

    Region scope is chain-agnostic: "A CDR3 aa" and "CDR3 aa" both return "CDR3".
    """
    for region in CANONICAL_REGIONS:
        if re.search(r"\b" + re.escape(region) + r"\b", col_name, re.IGNORECASE):
            return region
    return None


def _is_productive_expr(
    liab_cols: list[str],
    fixability_map: dict[str, str],
    extra_seq_cols: list[str] | None = None,
) -> pl.Expr:
    """Return a Polars expression that evaluates to 'Fail'/'Pass' for each row.

    'Fail' when any liability column contains the name of a disqualifying liability.
    Uses vectorised str.contains + any_horizontal instead of per-row map_elements.

    `extra_seq_cols` are scanned for stop codons (*) and out-of-frame markers (_): productivity
    is whole-molecule, so a stop codon in a region the user deselected must still fail the row.
    """
    disqualifying = {name for name, fix in fixability_map.items() if fix == "disqualifying"}
    conditions = [pl.col(c).str.contains(name, literal=True) for c in liab_cols for name in disqualifying]
    for c in extra_seq_cols or []:
        _col = pl.col(c).cast(pl.Utf8)
        conditions.append(_col.str.contains(r"\*", literal=False).fill_null(False))
        conditions.append(_col.str.contains(r"_", literal=False).fill_null(False))
    if not conditions:
        return pl.lit("Pass")
    return pl.when(pl.any_horizontal(conditions)).then(pl.lit("Fail")).otherwise(pl.lit("Pass"))


def _structural_risk_expr(liab_cols: list[str], fixability_map: dict[str, str]) -> pl.Expr:
    """Return a Polars expression that evaluates to 'Present'/'None' for each row.

    'Present' when any liability column contains the name of a structural or hard_to_fix liability.
    Uses vectorised str.contains + any_horizontal instead of per-row map_elements.
    """
    structural = {name for name, fix in fixability_map.items() if fix in {"structural", "hard_to_fix"}}
    conditions = [pl.col(c).str.contains(name, literal=True) for c in liab_cols for name in structural]
    if not conditions:
        return pl.lit("None")
    return pl.when(pl.any_horizontal(conditions)).then(pl.lit("Present")).otherwise(pl.lit("None"))


def _combine_chain_prefixed_columns(
    df: pl.DataFrame, suffix: str, chain_labels: dict[str, str], prefixes: tuple = CHAIN_SLOTS
) -> pl.DataFrame:
    prefixed_cols_map = {prefix: {} for prefix in prefixes}
    current_df_columns = df.columns
    for col_name in current_df_columns:
        if col_name.endswith(f" {suffix}"):
            for prefix_val in prefixes:
                if col_name.startswith(f"{prefix_val} "):
                    base_name = col_name[len(prefix_val) + 1 : -(len(suffix) + 1)].strip()
                    if base_name:
                        prefixed_cols_map[prefix_val][base_name] = col_name
                    break
    all_bases = set()
    for prefix_val in prefixes:
        all_bases |= set(prefixed_cols_map[prefix_val].keys())
    # The chain label distinguishes two chains' values inside one cell, so it is only written when
    # the frame actually holds more than one chain.
    label_chains = len([prefix_val for prefix_val in prefixes if prefixed_cols_map[prefix_val]]) > 1
    cols_to_drop = []
    for base_name in sorted(all_bases):
        if not base_name:
            continue
        combined_col_name = f"{base_name} {suffix}"
        concat_expressions = []
        temp_cols_to_drop_for_base = []
        for prefix_val in prefixes:
            col_to_include = prefixed_cols_map[prefix_val].get(base_name)
            if col_to_include is None or col_to_include not in current_df_columns:
                continue
            if concat_expressions:
                concat_expressions.append(pl.lit(" | "))
            if label_chains:
                concat_expressions.append(pl.lit(f"{chain_labels.get(prefix_val, prefix_val)}: "))
            concat_expressions.append(pl.col(col_to_include).cast(pl.Utf8).fill_null("N/A"))
            temp_cols_to_drop_for_base.append(col_to_include)
        if concat_expressions:
            if combined_col_name not in df.columns:
                df = df.with_columns(pl.concat_str(concat_expressions).alias(combined_col_name))
                cols_to_drop.extend(temp_cols_to_drop_for_base)
    final_cols_to_drop = [col for col in cols_to_drop if col in df.columns]
    if final_cols_to_drop:
        df = df.drop(final_cols_to_drop)
    return df


def _output_final_label_map(base_map: dict, liability_map: dict, output_path: str | None, description: str):
    final_map_all_strings = {}
    for key, value in base_map.items():
        final_map_all_strings[str(key)] = str(value)
    for liability_name, code in liability_map.items():
        final_map_all_strings[str(code)] = str(liability_name)
    if output_path:
        try:
            with open(output_path, "w") as f:
                json.dump(final_map_all_strings, f, indent=2, sort_keys=True)
            print(f"{description} label map written to {output_path}")
        except IOError as e:
            print(f"Error writing {description} label map to '{output_path}': {e}", file=sys.stderr)
    else:
        print(f"\n{description} label map:\n{json.dumps(final_map_all_strings, indent=2, sort_keys=True)}")


def _create_sequence_liabilities_summary_str(row_dict: dict, chain_labels: dict[str, str]) -> str:
    """
    Creates a formatted string summarizing liabilities for a sequence (row).
    Input: row_dict where keys are liability column names and values are their string values.
    """
    per_slot_data: dict[str, list] = {slot: [] for slot in CHAIN_SLOTS}
    # For regions that carry no slot prefix even in per-chain mode, or for all in bulk mode
    bulk_parts_data = []

    # First pass to determine whether any relevant column carries a slot prefix
    per_chain_mode = any(col_name.startswith(f"{slot} ") for col_name in row_dict for slot in CHAIN_SLOTS)

    for col_name, liability_value in row_dict.items():
        # Standardize missing/unknown liability values for the summary string
        if (
            liability_value is None
            or liability_value == "Unknown"
            or str(liability_value).strip() == ""
            or liability_value == "None"
        ):
            liability_value = "None"

        # Omit segments with no liabilities from the summary string
        if liability_value == "None":
            continue

        current_col_name = col_name
        current_prefix = ""  # A, B, or empty (for bulk or common regions)

        for slot in CHAIN_SLOTS:
            if current_col_name.startswith(f"{slot} "):
                current_prefix = slot
                current_col_name = current_col_name[len(slot) + 1 :]
                break

        # Remove " aa liabilities" or " liabilities" suffix to get the base region name
        if current_col_name.endswith(" aa liabilities"):
            region_base = current_col_name[: -len(" aa liabilities")]
        elif current_col_name.endswith(" liabilities"):
            region_base = current_col_name[: -len(" liabilities")]
        else:  # Should not happen if source cols are chosen carefully
            region_base = current_col_name

        # Use original case for region_base in output string, but UPPER for map key
        sort_key = REGION_ORDER_MAP.get(region_base.upper(), 99)  # .upper() for robust key lookup
        entry_str = f"{region_base}: {liability_value}"

        if per_chain_mode and current_prefix:
            per_slot_data[current_prefix].append((sort_key, region_base, entry_str))
        else:  # Bulk mode, or a common region not specific to one chain
            bulk_parts_data.append((sort_key, region_base, entry_str))

    final_summary_elements = []

    if per_chain_mode:
        bulk_parts_data.sort()  # Sort "other" common regions too
        any_slot_data = False
        for slot in CHAIN_SLOTS:
            parts = per_slot_data[slot]
            if not parts:
                continue
            parts.sort()  # Sorts by (sort_key, region_base, entry_str)
            any_slot_data = True
            label = chain_labels.get(slot, slot)
            final_summary_elements.append(f"{label} chain: " + ", ".join([item[2] for item in parts]))

        # If there were non-prefixed items (common regions) in per-chain mode, add them.
        if bulk_parts_data:
            prefix_for_common = "Other: " if any_slot_data else ""
            final_summary_elements.append(prefix_for_common + ", ".join([item[2] for item in bulk_parts_data]))
    else:  # Bulk mode (no slot prefixes detected among liability columns)
        bulk_parts_data.sort()
        if bulk_parts_data:
            final_summary_elements.append(", ".join([item[2] for item in bulk_parts_data]))

    if not final_summary_elements:
        return "None"

    return " | ".join(final_summary_elements)


# ——— MAIN SCRIPT —————————————————————————————————————
def main():
    p = argparse.ArgumentParser(description="Extract CDRs/FR1, analyze liabilities, compute risk.")
    p.add_argument("input_tsv", help="Input TSV")
    p.add_argument("output_tsv", help="Output TSV")
    p.add_argument("-m", "--label-map", help="JSON file or string for numeric region labels to names.")
    p.add_argument(
        "-o",
        "--output-label-map",
        help="Where to write JSON label map. Empty map if no input annotations or no liabilities calculated.",
    )
    p.add_argument(
        "--include-liabilities",
        type=str,
        help=(
            "A comma-delimited string of specific liability names to calculate"
            ' (e.g., "Deamidation (N[GS]),Methionine Oxidation (M)").'
            " If not provided, no liabilities or risks are calculated."
        ),
    )
    p.add_argument(
        "--output-regions-found", type=str, help="Path to output a JSON list of found regions (CDR1, CDR2, CDR3, FR1)."
    )
    p.add_argument(
        "--regions",
        type=str,
        help=(
            "Comma-delimited list of regions to scan (e.g. 'CDR3' or 'CDR1,CDR2,CDR3')."
            " Restricts liability detection to these regions only; regions outside the list are"
            " neither scanned nor reported. Omit to scan every region present in the input."
        ),
    )
    p.add_argument(
        "--numbering-schema",
        type=str,
        help="Optional numbering schema name (e.g., imgt, kabat, chothia) to adjust conserved cysteine coordinates.",
    )
    p.add_argument(
        "--custom-liabilities",
        type=str,
        help="Path to a JSON file containing an array of custom liability definitions.",
    )
    p.add_argument(
        "--use-predefined-liabilities",
        type=str,
        default="true",
        help="Whether to apply predefined liability definitions (default: true).",
    )
    p.add_argument(
        "--disabled-predefined-liabilities",
        type=str,
        help="Path to a JSON file containing an array of predefined liability names to disable.",
    )
    p.add_argument(
        "--chain-labels",
        type=str,
        help="Display names for the chain slots, e.g. 'A=Alpha,B=Beta' (default: 'A=Heavy,B=Light').",
    )
    args = p.parse_args()

    chain_labels = dict(DEFAULT_CHAIN_LABELS)
    for item in (args.chain_labels or "").split(","):
        slot, _, label = item.partition("=")
        if slot.strip().upper() in CHAIN_SLOTS and label.strip():
            chain_labels[slot.strip().upper()] = label.strip()

    use_predefined = str(args.use_predefined_liabilities).strip().lower() not in ("false", "0", "no")

    # None = scan every region present. Unknown names warn rather than raise, so a stale name
    # from an older block version degrades to "scan what I recognise" instead of failing the run.
    REQUESTED_REGIONS: set[str] | None = None
    if args.regions is not None:
        requested_raw = {name.strip().upper() for name in args.regions.split(",") if name.strip()}
        unknown = requested_raw - set(CANONICAL_REGIONS)
        if unknown:
            print(f"Warning: ignoring unknown region name(s) {sorted(unknown)}.", file=sys.stderr)
        REQUESTED_REGIONS = requested_raw & set(CANONICAL_REGIONS)
        if not REQUESTED_REGIONS:
            print("Warning: --regions resolved to an empty set; scanning all regions.", file=sys.stderr)
            REQUESTED_REGIONS = None

    # When --include-liabilities is absent, default to all predefined names.
    # The exclude-list (--disabled-predefined-liabilities) then trims specific entries.
    CALCULATE_LIABILITIES = True
    if args.include_liabilities is not None:
        raw_names = args.include_liabilities.split(",")
        USER_REQUESTED_LIABILITIES = {name.strip() for name in raw_names if name.strip()}
    else:
        USER_REQUESTED_LIABILITIES = set(ORIG_REGEX_LIABILITIES) | set(ORIG_EXTRA_PATTERNS) | set(ORIG_CYS_LIABILITIES)

    if use_predefined:
        active_cdr_defs, active_extra_defs, active_cys_defs, active_liability_regex = get_active_liability_definitions(
            USER_REQUESTED_LIABILITIES
        )
        # Apply disabled predefined liabilities
        if args.disabled_predefined_liabilities:
            try:
                with open(args.disabled_predefined_liabilities) as f:
                    disabled_names = set(json.load(f))
                active_cdr_defs = {n: d for n, d in active_cdr_defs.items() if n not in disabled_names}
                active_extra_defs = {n: p for n, p in active_extra_defs.items() if n not in disabled_names}
                active_cys_defs = {n: d for n, d in active_cys_defs.items() if n not in disabled_names}
                active_liability_regex = {n: p for n, p in active_liability_regex.items() if n not in disabled_names}
            except Exception as e:
                print(f"Warning: Could not load --disabled-predefined-liabilities: {e}", file=sys.stderr)
    else:
        active_cdr_defs, active_extra_defs, active_cys_defs, active_liability_regex = {}, {}, {}, {}

    # Stop codon (*) and out-of-frame (_) detection always runs — no user setting disables it.
    # Kept separate from active_extra_defs so it routes to the full chain sequence (for MiXCR
    # data) rather than per-region fragments, where MiXCR's boundary artifacts cause false
    # positives. See active_extra_defs_for_per_region below for the routing decision.
    active_extra_defs_full_seq = dict(ORIG_EXTRA_PATTERNS)

    # Load custom liabilities
    active_custom_defs: dict[str, dict] = {}
    if args.custom_liabilities:
        try:
            with open(args.custom_liabilities) as f:
                custom_list = json.load(f)
            for entry in custom_list:
                name = entry["name"]
                active_custom_defs[name] = {
                    "pattern": re.compile(entry["pattern"]),
                    "riskLevel": entry["riskLevel"],
                    "fixability": entry["fixability"],
                    "regions": entry["regions"],
                }
        except Exception as e:
            print(f"Warning: Could not load --custom-liabilities: {e}", file=sys.stderr)

    expected_cys_map = build_expected_cys_map(args.numbering_schema)

    if not (
        active_cdr_defs or active_extra_defs or active_cys_defs or active_custom_defs or active_extra_defs_full_seq
    ):
        print(
            "Warning: no active liability definitions after applying predefined/disabled/custom settings."
            " Liability calculations will be skipped."
        )
        CALCULATE_LIABILITIES = False
        active_cdr_defs, active_extra_defs, active_cys_defs, active_liability_regex = {}, {}, {}, {}

    # Build combined fixability and risk-level maps (predefined + custom)
    combined_fixability_map = dict(FIXABILITY_MAP)
    combined_fixability_map.update({name: d["fixability"] for name, d in active_custom_defs.items()})
    combined_risk_level_map = _build_risk_level_map(active_cdr_defs, active_cys_defs)
    combined_risk_level_map.update({name: d["riskLevel"] for name, d in active_custom_defs.items()})

    initial_region_map = {}
    if args.label_map:
        try:
            if os.path.isfile(args.label_map):
                with open(args.label_map, "r") as f:
                    initial_region_map = json.load(f)
            else:
                initial_region_map = json.loads(args.label_map)
            if not isinstance(initial_region_map, dict):
                initial_region_map = {}
        except Exception as e:
            print(f"Error loading --label-map: {e}", file=sys.stderr)
            initial_region_map = {}

    liability_codes = {}
    existing_numeric_keys = (
        [int(k) for k in initial_region_map.keys() if str(k).isdigit()] if isinstance(initial_region_map, dict) else []
    )
    next_code = max(existing_numeric_keys or [-1]) + 1

    try:
        df = pl.read_csv(args.input_tsv, separator="\t", ignore_errors=True, infer_schema_length=1000)
        df.columns = [" ".join(col.strip().split()) for col in df.columns]  # Normalize column names
    except Exception as e:
        sys.exit(f"Error reading input TSV '{args.input_tsv}': {e}")
    df_processed = df.clone()

    ann_cols = [c for c in df_processed.columns if c.lower().endswith("annotations")]
    # Path A: input has annotation columns (MiXCR-origin data — regions extracted from annotations).
    # Path B: no annotation columns (pre-fragmented user data — CDR/FR columns already present).
    has_input_ann_cols = bool(ann_cols)
    all_seq_cols = [c for c in df_processed.columns if c.lower().endswith("aa")]  # All potential sequence columns
    TARGET_REGION_KEYS = ["cdr1 aa", "cdr2 aa", "cdr3 aa", "fr1 aa", "fr2 aa", "fr3 aa", "fr4 aa"]  # For Path B
    cols_for_liability_analysis = []

    # Collect full-chain AA columns (e.g. "A sequence aa") for stop codon / OOF detection.
    # MiXCR places * at CDR/FR region boundaries when a codon spans a V-D-J junction — checking
    # the full chain avoids these false positives in per-region fragments.
    _fragment_keys_lower = {"cdr1", "cdr2", "cdr3", "fr1", "fr2", "fr3", "fr4"}
    full_input_sequence_cols = [
        c
        for c in df_processed.columns
        if c.lower().endswith(" aa") and not any(k in c.lower() for k in _fragment_keys_lower)
    ]

    # Deferred so the region scope, final only once every input path has converged, can be
    # applied to the exported annotation track too.
    pending_annotation_updates: dict[str, list] = {}

    # An annotation column always routes to Path A, even when every region already arrives as its
    # own column. Path A is the only path that writes liability coordinates back into the
    # annotation track, and `already_fed_regions` below keeps it from re-extracting what the input
    # supplies — so short-circuiting it here bought nothing and silently emptied the track.
    if has_input_ann_cols:  # Path A: Annotation-based extraction
        print(
            "Path A: Extracting regions and updating annotations"
            " (with FR1 specific logic if liabilities are calculated)."
        )
        chain_prefixes_found = set()
        for ann_col_name_for_prefix_check in ann_cols:
            if " " in ann_col_name_for_prefix_check:
                chain_prefixes_found.add(ann_col_name_for_prefix_check.split(" ")[0])
        multiple_chains_present = len(chain_prefixes_found) > 1 and any(
            p.upper() in CHAIN_SLOTS for p in chain_prefixes_found
        )

        processed_frag_dfs = []
        str_key_initial_region_map = {str(k): str(v) for k, v in initial_region_map.items()}

        for ann_col_name in ann_cols:
            current_prefix_raw = ann_col_name[: -len("annotations")].strip().rstrip("_")
            seq_col_name_to_find = (
                (f"{current_prefix_raw} sequence aa".lower()) if current_prefix_raw else "sequence aa"
            )
            matched_seq_cols = [sc for sc in all_seq_cols if sc.lower() == seq_col_name_to_find]
            if not matched_seq_cols and current_prefix_raw:
                matched_seq_cols = [
                    sc for sc in all_seq_cols if sc.lower() == f"{current_prefix_raw} aa".lower()
                ]  # Fallback for e.g. "A aa"
            if not matched_seq_cols:
                print(
                    f"⚠️ Path A: Skip {ann_col_name}: No corresponding sequence column '{seq_col_name_to_find}' found.",
                    file=sys.stderr,
                )
                continue

            seq_col_name = matched_seq_cols[0]
            # Regions this chain already carries as their own column are matched by region, not by
            # column name: the extracted copy drops the chain prefix on single-chain input while the
            # input's column keeps it, so the two names differ and the name check below cannot see
            # them. Both copies would then be scanned, and the extracted one would win the
            # unprefixed output column the Tengo side declares.
            fed_col_prefix = f"{current_prefix_raw} " if current_prefix_raw else ""
            existing_cols_lower = {c.lower() for c in df_processed.columns}
            already_fed_regions = {
                region for region in CANONICAL_REGIONS if f"{fed_col_prefix}{region} aa".lower() in existing_cols_lower
            }
            if already_fed_regions:
                print(
                    f"Path A: {sorted(already_fed_regions)} already present as columns"
                    f" for prefix '{current_prefix_raw}'; keeping those, not the extracted copies."
                )
            pending_ann_rows_for_col, fragment_rows_for_col = [], []

            for seq_data, ann_data in zip(df_processed[seq_col_name].to_list(), df_processed[ann_col_name].to_list()):
                if seq_data is None or ann_data is None:
                    pending_ann_rows_for_col.append((None, ann_data, {}))
                    fragment_rows_for_col.append({})
                    continue

                parsed_segments = parse_annotations(ann_data)
                extracted_frags, frag_coords = extract_cdrs_fr1(seq_data, parsed_segments, str_key_initial_region_map)
                current_ann_parts = [p for p in (ann_data.split("|") if ann_data and ann_data.strip() else []) if p]
                # region -> [(liability name, start, length)]. Codes are assigned at write-back,
                # so an out-of-scope region leaves neither an annotation nor a legend entry.
                region_hits: dict[str, list] = {}

                if CALCULATE_LIABILITIES:
                    for region_name, fragment_seq in extracted_frags.items():
                        # Uppercase locally for case-sensitive detection (MiXCR lowercases
                        # germline-imputed residues). Exported fragments below use the
                        # original-case values, so this stays confined to scanning.
                        fragment_seq = fragment_seq.upper()
                        start_coord, _ = frag_coords[region_name]
                        if active_cys_defs and region_name in {"FR1", "FR2", "FR3", "CDR1", "CDR2", "CDR3"}:
                            expected_positions, expected_count, should_check = _get_expected_cys_positions(
                                region_name, expected_cys_map
                            )
                            if should_check:
                                missing_cys, extra_cys, _ = _evaluate_cys_liabilities(
                                    fragment_seq, expected_positions, expected_count
                                )
                                cys_liability_name = None
                                if missing_cys:
                                    cys_liability_name = "Missing Cysteines"
                                elif extra_cys:
                                    cys_liability_name = "Extra Cysteines"

                                if cys_liability_name and cys_liability_name in active_cys_defs:
                                    region_hits.setdefault(region_name, []).append(
                                        (cys_liability_name, start_coord, 0)
                                    )  # Length 0 for point annotation
                        if region_name != "FR1":  # For CDRs and other non-FR1 regions from extraction
                            for liability_name, pattern in active_liability_regex.items():
                                for match in re.finditer(pattern, fragment_seq):
                                    global_start, global_length = (
                                        start_coord + match.start(),
                                        match.end() - match.start(),
                                    )
                                    region_hits.setdefault(region_name, []).append(
                                        (liability_name, global_start, global_length)
                                    )

                pending_ann_rows_for_col.append((current_ann_parts, ann_data, region_hits))
                row_dict = {}
                prefix_for_frag_col = (
                    f"{current_prefix_raw.capitalize()} " if current_prefix_raw and multiple_chains_present else ""
                )
                for r_name, r_seq in extracted_frags.items():
                    if r_name in already_fed_regions:
                        continue
                    row_dict[f"{prefix_for_frag_col}{r_name} aa"] = r_seq
                fragment_rows_for_col.append(row_dict)

            pending_annotation_updates[ann_col_name] = pending_ann_rows_for_col
            if fragment_rows_for_col:
                schema_for_frag_df = None
                first_valid_row = next((item for item in fragment_rows_for_col if item), None)
                if first_valid_row:
                    # Backstop for the horizontal concat below, which aborts the run on a duplicate
                    # name. The region check above is what normally keeps the input's own column.
                    schema_for_frag_df = {
                        col_name: pl.Utf8 for col_name in first_valid_row.keys() if col_name not in df_processed.columns
                    }
                if schema_for_frag_df:
                    filled_rows = [
                        {key: row.get(key) for key in schema_for_frag_df} for row in fragment_rows_for_col
                    ]  # Ensure all rows have all keys
                    try:
                        processed_frag_dfs.append(pl.DataFrame(filled_rows, schema=schema_for_frag_df))
                    except ShapeError:  # If df_processed is empty, zip makes empty lists, then this fails.
                        print(
                            f"Warning: Could not create DataFrame from fragments for {ann_col_name},"
                            " possibly due to empty input or processing issue.",
                            file=sys.stderr,
                        )

        if processed_frag_dfs:
            expected_height = len(df_processed)
            aligned_frag_dfs = [df_frag for df_frag in processed_frag_dfs if len(df_frag) == expected_height]
            if not aligned_frag_dfs and processed_frag_dfs:  # If some frags were processed but height mismatch
                print(
                    f"Warning: Height mismatch for fragment DataFrames. Expected {expected_height},"
                    f" got {[len(df) for df in processed_frag_dfs]}. Skipping fragment concatenation.",
                    file=sys.stderr,
                )

            if aligned_frag_dfs:
                # Concatenate new fragment columns, ensure no duplicate columns are formed if they somehow pre-existed
                # This horizontal concatenation assumes that df_processed and the fragment dfs are row-aligned.
                # Polars' concat(how='horizontal') requires dataframes to have same number of rows.
                try:
                    df_processed = pl.concat([df_processed] + aligned_frag_dfs, how="horizontal")
                except ShapeError as e:
                    print(
                        f"Error during horizontal concatenation of extracted fragments: {e}."
                        " Fragment columns might be missing.",
                        file=sys.stderr,
                    )

        path_a_frag_cols = [
            c
            for c in df_processed.columns
            if c.lower().endswith(" aa")
            and any(k in c.lower() for k in ["cdr1", "cdr2", "cdr3", "fr1", "fr2", "fr3", "fr4"])
            and not c.lower().endswith("sequence aa")
        ]
        cols_for_liability_analysis.extend(path_a_frag_cols)
        cols_for_liability_analysis = sorted(list(set(cols_for_liability_analysis)))

    elif not has_input_ann_cols:  # Path B: No annotations, use direct sequence columns
        print(
            "Path B (No Annotations Mode): Using direct sequence columns ending with predefined keys (e.g., 'CDR1 aa')."
        )
        candidate_seq_cols_for_path_b = [
            c for c in all_seq_cols if any(key_suffix in c.lower() for key_suffix in TARGET_REGION_KEYS)
        ]
        if not candidate_seq_cols_for_path_b:
            print("Path B: No standard FR/CDR sequence columns (e.g., 'CDR1 aa') found.")
        # Don't return early - continue to generate expected output columns even without liabilities
        cols_for_liability_analysis.extend(candidate_seq_cols_for_path_b)
        cols_for_liability_analysis = sorted(list(set(cols_for_liability_analysis)))

    # Filtered here, where all three input paths have converged, so every shape is scoped
    # identically. full_input_sequence_cols is deliberately left unscoped (whole-chain).
    scope_dropped_cols: list[str] = []
    if REQUESTED_REGIONS is not None:
        before_scope = list(cols_for_liability_analysis)
        scoped = [c for c in cols_for_liability_analysis if _column_region(c) in REQUESTED_REGIONS]
        if not scoped and before_scope:
            # Restricted-to-nothing would exclude every analysis column, disabling liability
            # calculation and emptying the required global columns — so widen, as an empty scope does.
            print(
                f"Warning: region scope {sorted(REQUESTED_REGIONS)} matches no column in this input"
                f" (it offers {sorted({r for c in before_scope if (r := _column_region(c))})});"
                " scanning all regions instead.",
                file=sys.stderr,
            )
            REQUESTED_REGIONS = None
        else:
            cols_for_liability_analysis = scoped
            scope_dropped_cols = [c for c in before_scope if c not in scoped]
            print(
                f"Region scope {sorted(REQUESTED_REGIONS)}: analyzing {cols_for_liability_analysis};"
                f" excluded {scope_dropped_cols}"
            )

    # Runs once the scope is final — the fallback above may have widened it. Out-of-scope hits are
    # dropped so the annotation track highlights the same regions the results table reports on.
    for ann_col_name, pending_rows in pending_annotation_updates.items():
        annotation_values = []
        for base_parts, original_ann, region_hits in pending_rows:
            if base_parts is None:  # Row skipped during extraction — keep the input untouched
                annotation_values.append(original_ann)
                continue
            parts = list(base_parts)
            for region_name, hits in region_hits.items():
                if REQUESTED_REGIONS is not None and region_name not in REQUESTED_REGIONS:
                    continue
                for liability_name, start, length in hits:
                    if liability_name not in liability_codes:
                        liability_codes[liability_name] = str(next_code)
                        next_code += 1
                    parts.append(f"{liability_codes[liability_name]}:{base36_encode(start)}+{base36_encode(length)}")
            annotation_values.append("|".join(sorted(set(parts))))
        df_processed = df_processed.with_columns(pl.Series(name=ann_col_name, values=annotation_values))

    if not cols_for_liability_analysis and CALCULATE_LIABILITIES:
        # Skipping here leaves every global column blank, which reads as a clean result.
        if df_processed.width > 0:
            sys.exit(
                "Liabilities were requested but no column can be scanned. Expected a region column"
                f" (e.g. 'CDR3 aa') or a CDRs annotation column, got: {df_processed.columns}"
            )
        CALCULATE_LIABILITIES = False
    elif not cols_for_liability_analysis and not CALCULATE_LIABILITIES:
        print("No columns identified for liability analysis (and no liabilities were requested).")

    if CALCULATE_LIABILITIES and cols_for_liability_analysis:  # Ensure CALCULATE_LIABILITIES is still true
        print(f"Generating liabilities for columns: {cols_for_liability_analysis}")
        liability_expressions, risk_expressions = [], []
        generated_liability_summary_col_names, generated_risk_col_names = [], []

        # MiXCR places * at CDR/FR boundaries (split codons at V-D-J junctions), so per-region
        # stop codon / OOF detection produces false positives on MiXCR-origin data. Annotation
        # columns identify MiXCR-origin data — strip these patterns and rely on the full-sequence
        # check instead. Pre-fragmented input (Path B, no annotations) contains genuine sequences.
        active_extra_defs_for_per_region = (
            {n: p for n, p in active_extra_defs.items() if n not in ORIG_EXTRA_PATTERNS}
            if has_input_ann_cols  # MiXCR data: per-region seqs may have boundary artifacts
            else active_extra_defs  # pre-fragmented user data: stop codon/OOF in fragments is real
        )

        # Stop codon / OOF check on the full chain sequence. Only runs when a non-fragmented
        # chain column exists (e.g. "A sequence aa" from non-scFv MiXCR upstreams).
        # The scFv upstream provides only CDR/FR columns, so this block is skipped — scFv
        # already guarantees productivity via --export-productive-clones-only.
        if active_extra_defs_full_seq and full_input_sequence_cols:
            for full_seq_col in full_input_sequence_cols:
                if full_seq_col not in df_processed.columns:
                    continue
                liab_col_name = f"{full_seq_col} liabilities"
                generated_liability_summary_col_names.append(liab_col_name)
                # Use native Polars str.contains() — runs in Rust, no Python per-row.
                # ORIG_EXTRA_PATTERNS contains exactly two literal patterns (\* and _),
                # so a when/then chain is cleaner and faster than map_elements.
                _col = pl.col(full_seq_col).cast(pl.Utf8)
                _stop = _col.str.contains(r"\*", literal=False)
                _oof = _col.str.contains(r"_", literal=False)
                liability_expressions.append(
                    pl.when(_col.is_null())
                    .then(pl.lit("None"))
                    .when(_stop & _oof)
                    .then(pl.lit("Contains stop codon, Out of frame"))
                    .when(_stop)
                    .then(pl.lit("Contains stop codon"))
                    .when(_oof)
                    .then(pl.lit("Out of frame"))
                    .otherwise(pl.lit("None"))
                    .alias(liab_col_name)
                )

        for frag_seq_col in cols_for_liability_analysis:
            if frag_seq_col not in df_processed.columns:
                continue  # Should not happen if logic is correct
            match = re.search(r"(FR[1-4]|CDR[1-3])", frag_seq_col, re.IGNORECASE)  # More specific match
            core_region_name = match.group(1).upper() if match else "UNKNOWN_REGION"
            new_liab_col = f"{frag_seq_col} liabilities"  # e.g. "A CDR1 aa liabilities"
            generated_liability_summary_col_names.append(new_liab_col)
            liability_expressions.append(
                pl.col(frag_seq_col)
                .cast(pl.Utf8)
                .map_elements(
                    lambda s, crn=core_region_name: identify_liabilities(
                        s,
                        crn,
                        active_cdr_defs,
                        active_extra_defs_for_per_region,
                        active_cys_defs,
                        expected_cys_map,
                        active_custom_defs=active_custom_defs,
                    ),
                    return_dtype=pl.Utf8,
                    skip_nulls=False,
                )
                .fill_null("Unknown")
                .alias(new_liab_col)
            )
        if liability_expressions:
            df_processed = df_processed.with_columns(liability_expressions)

        # ---- START: New section to create "Sequence liabilities summary" ----
        summary_struct_cols = [c for c in generated_liability_summary_col_names if c in df_processed.columns]
        if summary_struct_cols:
            print(f"Generating sequence liabilities summary from columns: {summary_struct_cols}")
            df_processed = df_processed.with_columns(
                pl.struct(summary_struct_cols)
                .map_elements(
                    lambda row, _cl=chain_labels: _create_sequence_liabilities_summary_str(row, _cl),
                    return_dtype=pl.Utf8,
                    skip_nulls=False,
                )
                .fill_null("None")
                .alias("Sequence liabilities summary")
            )
        elif "Sequence liabilities summary" not in df_processed.columns:
            df_processed = df_processed.with_columns(pl.lit("None").cast(pl.Utf8).alias("Sequence liabilities summary"))
        # ---- END: New section ----

        for liab_col in generated_liability_summary_col_names:  # These are the individual "... aa liabilities" cols
            if liab_col not in df_processed.columns:
                continue
            new_risk_col = liab_col.replace(" liabilities", " risk")
            generated_risk_col_names.append(new_risk_col)
            risk_expressions.append(
                pl.col(liab_col)
                .cast(pl.Utf8)
                .map_elements(
                    lambda l_str, cfm=combined_fixability_map, rlm=combined_risk_level_map: classify_risk(
                        l_str, cfm, rlm
                    ),
                    return_dtype=pl.Utf8,
                    skip_nulls=False,
                )
                .fill_null("None")
                .alias(new_risk_col)
            )
        if risk_expressions:
            df_processed = df_processed.with_columns(risk_expressions)

        # Global classification columns: replace the old "Liabilities risk" with four new columns
        liab_cols_for_global = [c for c in generated_liability_summary_col_names if c in df_processed.columns]

        # Pre-fragmented input often lacks a whole-chain column, so scoping away a region would
        # hide a real stop codon. MiXCR-origin reads stop/OOF whole-chain already — nothing to add.
        productivity_extra_cols = (
            [c for c in scope_dropped_cols if c in df_processed.columns] if not has_input_ann_cols else []
        )
        if productivity_extra_cols:
            print(f"Is Productive additionally scans scope-excluded columns: {productivity_extra_cols}")

        if liab_cols_for_global:
            cfm = combined_fixability_map
            rlm = combined_risk_level_map
            df_processed = df_processed.with_columns(
                [
                    _is_productive_expr(liab_cols_for_global, cfm, productivity_extra_cols).alias("Is Productive"),
                    _structural_risk_expr(liab_cols_for_global, cfm).alias("Structural liabilities"),
                    pl.struct(liab_cols_for_global)
                    .map_elements(
                        lambda row, _cfm=cfm, _rlm=rlm: classify_developability_risk(row, _cfm, _rlm),
                        return_dtype=pl.Utf8,
                        skip_nulls=False,
                    )
                    .fill_null("None")
                    .alias("Developability risk"),
                    pl.struct(liab_cols_for_global)
                    .map_elements(
                        lambda row, _cfm=cfm: compute_developability_score(row, _cfm),
                        return_dtype=pl.Float64,
                        skip_nulls=False,
                    )
                    .fill_null(0.0)
                    .alias("Developability cost"),
                ]
            )
        else:
            df_processed = df_processed.with_columns(
                [
                    pl.lit("Pass").cast(pl.Utf8).alias("Is Productive"),
                    pl.lit("None").cast(pl.Utf8).alias("Structural liabilities"),
                    pl.lit("None").cast(pl.Utf8).alias("Developability risk"),
                    pl.lit(0.0).cast(pl.Float64).alias("Developability cost"),
                ]
            )

        df_processed = _combine_chain_prefixed_columns(df_processed, "risk", chain_labels)
        df_processed = _combine_chain_prefixed_columns(df_processed, "liabilities", chain_labels)

    # Output Column Selection & Final Write
    # Include clonotypeKey if it exists, otherwise use empty list
    output_cols_core = ["clonotypeKey"] if "clonotypeKey" in df_processed.columns else []
    final_annotation_cols_list = ann_cols if has_input_ann_cols else []
    final_annotation_cols = sorted(list(set(final_annotation_cols_list)))

    # Handle CDR3 sequence columns
    final_cdr3_seq_cols = []
    if df_processed.width > 0:  # Normal case - find existing columns
        per_chain_cdr3 = sorted(
            [c for c in df_processed.columns if re.search(r"^(a|b) cdr3 aa$", c, re.IGNORECASE)]
        )
        general_cdr3 = sorted(
            [c for c in df_processed.columns if re.search(r"cdr3 aa$", c, re.IGNORECASE) and c not in per_chain_cdr3]
        )
        final_cdr3_seq_cols = per_chain_cdr3 + general_cdr3
        if not final_cdr3_seq_cols:
            potential_cdr3 = sorted(
                [c for c in df_processed.columns if "cdr3" in c.lower() and c.lower().endswith("aa")]
            )
            if potential_cdr3:
                final_cdr3_seq_cols = potential_cdr3
    else:  # Empty input case - generate expected column names
        # For empty input, always generate bulk columns (standard CDR3 column)
        final_cdr3_seq_cols = ["CDR3 aa"]

    individual_frag_liabs, individual_frag_risks = [], []
    combined_chain_liabs, combined_chain_risks = [], []
    combined_region_liabs, combined_region_risks = [], []

    overall_summary_cols = []  # Renamed from overall_liab_risk_col for clarity
    if CALCULATE_LIABILITIES:
        if df_processed.width > 0:  # Normal case - find existing columns
            all_liab_cols = [c for c in df_processed.columns if c.endswith(" liabilities")]
            all_risk_cols = [c for c in df_processed.columns if c.endswith(" risk")]

            individual_frag_liabs = sorted(
                [c for c in all_liab_cols if " aa liabilities" in c.lower() and c != "Sequence liabilities summary"]
            )
            individual_frag_risks = sorted([c for c in all_risk_cols if " aa risk" in c.lower()])

            combined_chain_liabs = sorted(
                [
                    c
                    for c in all_liab_cols
                    if c.lower() in ["a liabilities", "b liabilities"] and c not in individual_frag_liabs
                ]
            )
            combined_chain_risks = sorted(
                [
                    c
                    for c in all_risk_cols
                    if c.lower() in ["a risk", "b risk"] and c not in individual_frag_risks
                ]
            )

            _global_cols = {"Is Productive", "Structural liabilities", "Developability risk", "Developability cost"}
            combined_region_liabs = sorted(
                [
                    c
                    for c in all_liab_cols
                    if c not in individual_frag_liabs
                    and c not in combined_chain_liabs
                    and c not in _global_cols
                    and c != "Sequence liabilities summary"
                ]
            )
            combined_region_risks = sorted(
                [
                    c
                    for c in all_risk_cols
                    if c not in individual_frag_risks and c not in combined_chain_risks and c not in _global_cols
                ]
            )

            # Build overall_summary_cols: 4 new global columns + sequence summary
            _new_global = [
                c
                for c in ["Is Productive", "Structural liabilities", "Developability risk", "Developability cost"]
                if c in df_processed.columns
            ]
            overall_summary_cols = _new_global
            if "Sequence liabilities summary" in df_processed.columns:
                overall_summary_cols = overall_summary_cols + ["Sequence liabilities summary"]
        else:  # Empty input case - generate expected column names
            expected_regions = ["CDR1", "CDR2", "CDR3", "FR1"]
            for region in expected_regions:
                individual_frag_liabs.append(f"{region} aa liabilities")
                individual_frag_risks.append(f"{region} aa risk")
            individual_frag_liabs = sorted(individual_frag_liabs)
            individual_frag_risks = sorted(individual_frag_risks)
            overall_summary_cols = [
                "Is Productive",
                "Structural liabilities",
                "Developability risk",
                "Developability cost",
                "Sequence liabilities summary",
            ]
    else:  # Liabilities not calculated
        if df_processed.width == 0:
            expected_regions = ["CDR1", "CDR2", "CDR3", "FR1"]
            for region in expected_regions:
                individual_frag_liabs.append(f"{region} aa liabilities")
                individual_frag_risks.append(f"{region} aa risk")
            individual_frag_liabs = sorted(individual_frag_liabs)
            individual_frag_risks = sorted(individual_frag_risks)
            overall_summary_cols = [
                "Is Productive",
                "Structural liabilities",
                "Developability risk",
                "Developability cost",
                "Sequence liabilities summary",
            ]

    output_cols_ordered = list(
        dict.fromkeys(
            output_cols_core
            + final_annotation_cols
            + final_cdr3_seq_cols
            + individual_frag_liabs
            + combined_region_liabs
            + combined_chain_liabs
            + individual_frag_risks
            + combined_region_risks
            + combined_chain_risks
            + overall_summary_cols
        )
    )

    # For empty input or when no liabilities calculated, force generation of all expected bulk columns
    # Check if we have insufficient columns (only core + annotations, no liability/risk columns)
    has_insufficient_columns = len(output_cols_ordered) <= 2

    if df_processed.width == 0 or (not CALCULATE_LIABILITIES and has_insufficient_columns):
        # Force generate all expected bulk columns
        expected_bulk_columns = []

        # Add clonotypeKey if it exists in input
        if "clonotypeKey" in df_processed.columns:
            expected_bulk_columns.append("clonotypeKey")

        # Add annotation columns if they exist in input
        if final_annotation_cols:
            expected_bulk_columns.extend(final_annotation_cols)

        # Add all expected bulk columns
        expected_bulk_columns.extend(
            [
                "CDR3 aa",
                "CDR1 aa liabilities",
                "CDR2 aa liabilities",
                "CDR3 aa liabilities",
                "FR1 aa liabilities",
                "CDR1 aa risk",
                "CDR2 aa risk",
                "CDR3 aa risk",
                "FR1 aa risk",
                "Is Productive",
                "Structural liabilities",
                "Developability risk",
                "Developability cost",
                "Sequence liabilities summary",
            ]
        )

        # Create missing columns with empty/default values
        missing_columns = [c for c in expected_bulk_columns if c not in df_processed.columns]
        if missing_columns:
            # Add empty columns for missing ones
            for col in missing_columns:
                df_processed = df_processed.with_columns(pl.lit("").alias(col))

        output_cols_existing = expected_bulk_columns
    else:
        output_cols_existing = [c for c in output_cols_ordered if c in df_processed.columns]

    df_out = (
        df_processed.select(output_cols_existing) if output_cols_existing else df_processed.clone()
    )  # Clone if no selection to avoid issues with empty df_out if df_processed has columns

    if not output_cols_existing and df_processed.width > 0:
        print(
            "No columns selected for final output based on defined order criteria. Writing entire processed DataFrame.",
            file=sys.stderr,
        )
    elif not output_cols_existing and df_processed.width == 0:
        print("Input was empty and no columns processed or selected.", file=sys.stderr)

    if df_out.width == 0 and df_processed.width > 0:
        print(
            "Output selection resulted in an empty DataFrame, but processed data exists."
            " Writing full processed DataFrame instead."
        )
        df_out = df_processed
    elif df_out.width == 0:
        print("Processed DataFrame is empty or output selection is empty. Nothing to write to TSV.", file=sys.stderr)

    if df_out.width > 0:
        try:
            df_out.write_csv(args.output_tsv, separator="\t", quote_style="never")
            print(f"Output table written to {args.output_tsv}")
        except Exception as e:
            print(f"Error writing output TSV: {e}", file=sys.stderr)
    else:  # df_out.width == 0
        if args.output_tsv:  # If output path is given, write empty file with headers
            try:
                with open(args.output_tsv, "w") as f_empty:
                    # Always write headers if they could be determined, even for empty input
                    if output_cols_existing:
                        f_empty.write("\t".join(output_cols_existing) + "\n")
                    elif df_processed.width > 0:
                        f_empty.write("\t".join(df_processed.columns) + "\n")
                    elif df_processed.columns:  # Even if width is 0, columns might exist
                        f_empty.write("\t".join(df_processed.columns) + "\n")
                    # else, an empty file is created (no headers possible)
                print(
                    f"Empty output table with headers written to {args.output_tsv}"
                    " as no data rows were processed/selected."
                )
            except Exception as e:
                print(f"Error writing empty output TSV to '{args.output_tsv}': {e}", file=sys.stderr)

    if args.output_regions_found:
        found_regions_set = set()
        if cols_for_liability_analysis:  # Based on what was analyzed
            for col_name in cols_for_liability_analysis:
                region_canonical_name = _column_region(col_name)
                if region_canonical_name:
                    found_regions_set.add(region_canonical_name)
            list_of_found_regions = sorted(list(found_regions_set), key=lambda x: REGION_ORDER_MAP.get(x, 99))
        else:
            list_of_found_regions = []
        try:
            with open(args.output_regions_found, "w") as f:
                json.dump(list_of_found_regions, f, indent=2)  # sort_keys=True for dicts, not lists
            print(f"List of found regions {list_of_found_regions} written to {args.output_regions_found}")
        except IOError as e:
            print(f"Error writing found regions list to '{args.output_regions_found}': {e}", file=sys.stderr)

    if not has_input_ann_cols and not CALCULATE_LIABILITIES:  # No annotations and no calculation attempt
        _output_final_label_map(
            {}, {}, args.output_label_map, "Empty Label Map (No annotations and no liabilities calculated)"
        )
    elif not CALCULATE_LIABILITIES:  # Annotations might exist, but no calculation
        _output_final_label_map(
            initial_region_map, {}, args.output_label_map, "Label Map (Regions Only; No Liabilities Calculated)"
        )
    else:  # Liabilities were calculated (or attempted)
        _output_final_label_map(initial_region_map, liability_codes, args.output_label_map, "Final Combined Label Map")


if __name__ == "__main__":
    main()
