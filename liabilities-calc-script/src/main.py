#!/usr/bin/env python3
import polars as pl
from polars.exceptions import ShapeError
import re
import argparse
import sys
import json
import os


# Liability Definitions
ORIG_CDR_LIABILITIES = {
    "Deamidation (N[GS])":         (r"N[GS]",    "High"),
    "Fragmentation (DP)":          (r"DP",       "High"),
    "Isomerization (D[DGHST])":    (r"D[DGHST]", "High"),
    "N-linked Glycosylation (N[^P][ST])": (r"N[^P][ST]", "High"),
    "Deamidation (N[AHNT])":       (r"N[AHNT]",  "Medium"),
    "Hydrolysis (NP)":             (r"NP",       "Medium"),
    "Fragmentation (TS)":          (r"TS",       "Medium"),
    "Tryptophan Oxidation (W)":    (r"W",        "Medium"),
    "Methionine Oxidation (M)":    (r"M",        "Medium"),
    "Deamidation ([STK]N)":        (r"[STK]N",   "Low"),
}
ORIG_EXTRA_PATTERNS = {
    "Contains stop codon": r"\*",
    "Out of frame":        r"_",
}
ORIG_CYS_LIABILITIES = {"Missing Cysteines": "High", "Extra Cysteines": "High"}
EXPECTED_CYS    = {"FR1": [22], "CDR3": [1]}
FR1_SPECIFIC_LIABILITIES = {"Missing Cysteines", "Extra Cysteines"}
REGION_ORDER_MAP = {"FR1": 1, "CDR1": 2, "CDR2": 3, "CDR3": 4, "FR2": 5, "FR3": 6, "FR4": 7} # For sorting summary


# Base-36 Utilities
def base36_encode(n: int) -> str:
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if n == 0: return "0"
    s = "";
    while n > 0: n, r = divmod(n, 36); s = digits[r] + s
    return s

# Base-36 Decoding
def base36_decode(s: str) -> int: return int(s, 36)


# Parsing & Extraction
def parse_annotations(ann: str):
    segs = []
    if not ann or not isinstance(ann, str): return segs
    for part in ann.split("|"):
        if ":" not in part or "+" not in part: continue
        lab, rest = part.split(":", 1); st36, ln36 = rest.split("+", 1)
        try: segs.append((lab, base36_decode(st36), base36_decode(ln36)))
        except ValueError: print(f"Warning: Could not decode part '{part}' in annotation '{ann}'", file=sys.stderr); continue
    return sorted(segs, key=lambda x: x[1])


# Extract CDRs & FR1
def extract_cdrs_fr1(seq: str, segments: list, region_map: dict):
    frags, coords = {}, {}
    for lab, start, length in segments:
        name = region_map.get(str(lab))
        if name:
            if start < 0 or start + length > len(seq):
                print(f"Warning: Segment {name} ({start}+{length}) out of bounds for seq length {len(seq)}.", file=sys.stderr); continue
            frags[name]  = seq[start:start+length]; coords[name] = (start, length)
    if "CDR1" in coords:
        s0, _ = coords["CDR1"]
        if s0 > 0: frags["FR1"]  = seq[:s0]; coords["FR1"] = (0, s0)
    return frags, coords


# Helper to get active liability definitions
def get_active_liability_definitions(user_requested_set: set):
    if not user_requested_set:
        return {}, {}, {}, {}
    active_cdr_l = {n: d for n, d in ORIG_CDR_LIABILITIES.items() if n in user_requested_set}
    active_extra_p = {n: p for n, p in ORIG_EXTRA_PATTERNS.items() if n in user_requested_set}
    active_cys_l = {n: r for n, r in ORIG_CYS_LIABILITIES.items() if n in user_requested_set}
    active_liability_r = {
        **{nm: details[0] for nm, details in active_cdr_l.items()},
        **active_extra_p
    }
    return active_cdr_l, active_extra_p, active_cys_l, active_liability_r


# Liability & Risk Functions
def identify_liabilities(seq: str, region: str,
                         active_cdr_defs: dict,
                         active_extra_defs: dict,
                         active_cys_defs: dict,
                         expected_cys_map: dict,
                         debug_col_name: str = "N/A") -> str:
    call_id = os.urandom(2).hex()
    if not seq or not isinstance(seq, str) or not seq.strip():
        return "Unknown"

    liabilities_found = []

    # General "extra" patterns (applied to all regions first)
    for name, pattern in active_extra_defs.items():
        if re.search(pattern, seq):
            liabilities_found.append(name) # Duplicates removed by set() later

    # Region-specific logic
    if region == "FR1":
        # print(f"DEBUG ID_LIAB (call:{call_id}, Col:'{debug_col_name}', Region:'{region}') Applying FR1-specific Cys checks.")
        if active_cys_defs:
            expected_indices = expected_cys_map.get(region, [])
            if expected_indices: # Only check if expectations are defined for this region
                actual_cys_count = seq.count("C")
                expected_cys_count = len(expected_indices)
                if "Missing Cysteines" in active_cys_defs and actual_cys_count < expected_cys_count:
                    liabilities_found.append("Missing Cysteines")
                if "Extra Cysteines" in active_cys_defs and actual_cys_count > expected_cys_count:
                    liabilities_found.append("Extra Cysteines")

    elif region.startswith("CDR"):
        # Handle Tryptophan Oxidation (W) first due to its specific logic for CDR3 vs other CDRs
        w_oxidation_name = "Tryptophan Oxidation (W)"
        if w_oxidation_name in active_cdr_defs:
            pattern_to_use_for_w = r"W(?!$)" if region == "CDR3" else active_cdr_defs[w_oxidation_name][0]
            if re.search(pattern_to_use_for_w, seq):
                liabilities_found.append(w_oxidation_name)

        # Apply other active_cdr_defs for CDRs (excluding W, which was handled above)
        for name, (pattern, _) in active_cdr_defs.items():
            if name == w_oxidation_name: # Already processed
                continue
            if re.search(pattern, seq):
                liabilities_found.append(name)

        # Cysteine checks for CDRs (if defined in EXPECTED_CYS and active)
        if active_cys_defs:
            expected_indices = expected_cys_map.get(region, [])
            if expected_indices:
                actual_cys_count = seq.count("C")
                expected_cys_count = len(expected_indices)
                if "Missing Cysteines" in active_cys_defs and actual_cys_count < expected_cys_count:
                    liabilities_found.append("Missing Cysteines")
                if "Extra Cysteines" in active_cys_defs and actual_cys_count > expected_cys_count:
                    liabilities_found.append("Extra Cysteines")

    elif region.startswith("FR"): # For other FRs (FR2, FR3, FR4)
        # print(f"DEBUG ID_LIAB (call:{call_id}, Col:'{debug_col_name}', Region:'{region}') Is FR (not FR1). Only Extra_Patterns and Cys applied if active.")
        if active_cys_defs:
            expected_indices = expected_cys_map.get(region, [])
            if expected_indices:
                actual_cys_count = seq.count("C")
                expected_cys_count = len(expected_indices)
                if "Missing Cysteines" in active_cys_defs and actual_cys_count < expected_cys_count:
                    liabilities_found.append("Missing Cysteines")
                if "Extra Cysteines" in active_cys_defs and actual_cys_count > expected_cys_count:
                    liabilities_found.append("Extra Cysteines")

    final_liabs_found_str = ", ".join(sorted(list(set(liabilities_found)))) if liabilities_found else "None"
    # print(f"DEBUG ID_LIAB (call:{call_id}, Col:'{debug_col_name}', Region:'{region}') Final result: '{final_liabs_found_str}'")
    return final_liabs_found_str

# Other helper functions
def classify_risk(liabilities_str: str,
                  active_cdr_defs: dict,
                  active_cys_defs: dict,
                  active_extra_pattern_names: set) -> str:
    if not liabilities_str or liabilities_str == "None" or not isinstance(liabilities_str, str): return "None"
    items = [item.strip() for item in liabilities_str.split(",")]
    current_max_risk_level = 0
    risk_map = {"None": 0, "Low": 1, "Medium": 2, "High": 3}
    level_to_risk = {v: k for k, v in risk_map.items()}
    for item in items:
        if item in active_cys_defs:
            item_risk_str = active_cys_defs[item]
            if risk_map[item_risk_str] > current_max_risk_level: current_max_risk_level = risk_map[item_risk_str]
            if current_max_risk_level == risk_map["High"]: return "High";
            continue
        if item in active_cdr_defs:
            item_risk_str = active_cdr_defs[item][1]
            if risk_map[item_risk_str] > current_max_risk_level: current_max_risk_level = risk_map[item_risk_str]
            if current_max_risk_level == risk_map["High"]: return "High";
            continue
        if item in active_extra_pattern_names:
            if risk_map["High"] > current_max_risk_level: current_max_risk_level = risk_map["High"]
            if current_max_risk_level == risk_map["High"]: return "High"
    return level_to_risk[current_max_risk_level]

def overall_risk_func(row_struct: dict) -> str:
    risk_values = [str(v).strip() for v in row_struct.values() if v is not None]
    if "High" in risk_values: return "High"
    if "Medium" in risk_values: return "Medium"
    if "Low" in risk_values: return "Low"
    return "None"

def _combine_heavy_light_prefixed_columns(df: pl.DataFrame, suffix: str, prefixes: tuple = ("Heavy", "Light")) -> pl.DataFrame:
    prefixed_cols_map = {prefix: {} for prefix in prefixes}
    current_df_columns = df.columns
    for col_name in current_df_columns:
        if col_name.endswith(f" {suffix}"):
            for prefix_val in prefixes:
                if col_name.startswith(f"{prefix_val} "):
                    base_name = col_name[len(prefix_val) + 1 : -(len(suffix) + 1)].strip()
                    if base_name: prefixed_cols_map[prefix_val][base_name] = col_name
                    break
    common_bases = set()
    if prefixed_cols_map[prefixes[0]]:
        common_bases = set(prefixed_cols_map[prefixes[0]].keys())
        for i in range(1, len(prefixes)):
            if prefixed_cols_map[prefixes[i]]: common_bases &= set(prefixed_cols_map[prefixes[i]].keys())
            else: common_bases = set(); break
    else: common_bases = set()
    cols_to_drop = []
    for base_name in common_bases:
        if not base_name: continue
        combined_col_name = f"{base_name} {suffix}"
        concat_expressions = []
        all_chains_present_for_base = True
        temp_cols_to_drop_for_base = []
        for i, prefix_val in enumerate(prefixes):
            if base_name not in prefixed_cols_map[prefix_val]: all_chains_present_for_base = False; break
            col_to_include = prefixed_cols_map[prefix_val][base_name]
            if i > 0: concat_expressions.append(pl.lit(" | "))
            concat_expressions.append(pl.lit(f"{prefix_val}: "))
            if col_to_include in current_df_columns:
                concat_expressions.append(pl.col(col_to_include).cast(pl.Utf8).fill_null("N/A"))
                temp_cols_to_drop_for_base.append(col_to_include)
            else: all_chains_present_for_base = False; break
        if all_chains_present_for_base and concat_expressions:
            if combined_col_name not in df.columns:
                df = df.with_columns(pl.concat_str(concat_expressions).alias(combined_col_name))
                cols_to_drop.extend(temp_cols_to_drop_for_base)
    final_cols_to_drop = [col for col in cols_to_drop if col in df.columns]
    if final_cols_to_drop: df = df.drop(final_cols_to_drop)
    return df

def _output_final_label_map(base_map: dict, liability_map: dict, output_path: str | None, description: str):
    final_map_all_strings = {}
    for key, value in base_map.items(): final_map_all_strings[str(key)] = str(value)
    for liability_name, code in liability_map.items(): final_map_all_strings[str(code)] = str(liability_name)
    if output_path:
        try:
            with open(output_path, "w") as f: json.dump(final_map_all_strings, f, indent=2, sort_keys=True)
            print(f"{description} label map written to {output_path}")
        except IOError as e: print(f"Error writing {description} label map to '{output_path}': {e}", file=sys.stderr)
    else: print(f"\n{description} label map:\n{json.dumps(final_map_all_strings, indent=2, sort_keys=True)}")


def _create_sequence_liabilities_summary_str(row_dict: dict) -> str:
    """
    Creates a formatted string summarizing liabilities for a sequence (row).
    Input: row_dict where keys are liability column names and values are their string values.
    """
    heavy_parts_data = []
    light_parts_data = []
    # For regions that don't have H/L prefix even in H/L mode, or for all in bulk mode
    bulk_parts_data = [] 
    
    has_any_heavy_prefix = False
    has_any_light_prefix = False

    # First pass to determine if H/L specific prefixes exist on any relevant columns
    for col_name in row_dict.keys():
        if col_name.startswith("Heavy "):
            has_any_heavy_prefix = True
        elif col_name.startswith("Light "):
            has_any_light_prefix = True
    
    is_heavy_light_mode = has_any_heavy_prefix or has_any_light_prefix

    for col_name, liability_value in row_dict.items():
        # Standardize missing/unknown liability values for the summary string
        if liability_value is None or liability_value == "Unknown" or str(liability_value).strip() == "" or liability_value == "None":
            liability_value = "None"

        # Omit segments with no liabilities from the summary string
        if liability_value == "None":
            continue

        current_col_name = col_name
        current_prefix = "" # Heavy, Light, or empty (for bulk or common regions)

        if current_col_name.startswith("Heavy "):
            current_prefix = "Heavy"
            current_col_name = current_col_name[len("Heavy "):]
        elif current_col_name.startswith("Light "):
            current_prefix = "Light"
            current_col_name = current_col_name[len("Light "):]
        
        # Remove " aa liabilities" or " liabilities" suffix to get the base region name
        if current_col_name.endswith(" aa liabilities"):
            region_base = current_col_name[:-len(" aa liabilities")]
        elif current_col_name.endswith(" liabilities"):
             region_base = current_col_name[:-len(" liabilities")]
        else: # Should not happen if source cols are chosen carefully
            region_base = current_col_name 

        # Use original case for region_base in output string, but UPPER for map key
        sort_key = REGION_ORDER_MAP.get(region_base.upper(), 99) # .upper() for robust key lookup
        entry_str = f"{region_base}: {liability_value}"

        if is_heavy_light_mode:
            if current_prefix == "Heavy":
                heavy_parts_data.append((sort_key, region_base, entry_str))
            elif current_prefix == "Light":
                light_parts_data.append((sort_key, region_base, entry_str))
            else: 
                # Non-prefixed column in H/L mode (e.g. a common region not specific to H/L chains)
                bulk_parts_data.append((sort_key, region_base, entry_str))
        else: # Bulk mode, all go to bulk_parts
            bulk_parts_data.append((sort_key, region_base, entry_str))

    final_summary_elements = []

    if is_heavy_light_mode:
        heavy_parts_data.sort() # Sorts by (sort_key, region_base, entry_str)
        light_parts_data.sort()
        bulk_parts_data.sort() # Sort "other" common regions too

        if heavy_parts_data:
            final_summary_elements.append("Heavy chain: " + ", ".join([item[2] for item in heavy_parts_data]))
        if light_parts_data:
            final_summary_elements.append("Light chain: " + ", ".join([item[2] for item in light_parts_data]))
        
        # If there were non-prefixed items (common regions) in H/L mode, add them.
        if bulk_parts_data:
            prefix_for_common = "Other: " if (heavy_parts_data or light_parts_data) else ""
            final_summary_elements.append(prefix_for_common + ", ".join([item[2] for item in bulk_parts_data]))
    else: # Bulk mode (no H/L prefixes detected among liability columns)
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
    p.add_argument("-o", "--output-label-map", help="Where to write JSON label map. Empty map if no input annotations or no liabilities calculated.")
    p.add_argument("--include-liabilities", type=str,
                   help="A comma-delimited string of specific liability names to calculate (e.g., \"Deamidation (N[GS]),Methionine Oxidation (M)\"). If not provided, no liabilities or risks are calculated.")
    p.add_argument("--output-regions-found", type=str,
                   help="Path to output a JSON list of found regions (CDR1, CDR2, CDR3, FR1).")
    args = p.parse_args()

    CALCULATE_LIABILITIES = args.include_liabilities is not None
    USER_REQUESTED_LIABILITIES = set()
    if CALCULATE_LIABILITIES:
        raw_names = args.include_liabilities.split(',')
        USER_REQUESTED_LIABILITIES = {name.strip() for name in raw_names if name.strip()}

    active_cdr_defs, active_extra_defs, active_cys_defs, active_liability_regex = \
        get_active_liability_definitions(USER_REQUESTED_LIABILITIES)

    if CALCULATE_LIABILITIES:
        if not (active_cdr_defs or active_extra_defs or active_cys_defs):
            print("Warning: --include-liabilities provided, but no recognized liability names matched internal definitions. No liabilities will be calculated.")
            CALCULATE_LIABILITIES = False
            active_cdr_defs, active_extra_defs, active_cys_defs, active_liability_regex = {}, {}, {}, {}
        else:
            recognized_active_set = set(active_cdr_defs.keys()) | set(active_extra_defs.keys()) | set(active_cys_defs.keys())
            # print(f"Debug: Calculating the following liabilities: {recognized_active_set}")
    else:
        print("Warning: --include-liabilities not provided or no recognized names. Liability and risk calculations will be skipped.")
        active_cdr_defs, active_extra_defs, active_cys_defs, active_liability_regex = {}, {}, {}, {}

    initial_region_map = {}
    if args.label_map:
        try:
            if os.path.isfile(args.label_map):
                with open(args.label_map, 'r') as f: initial_region_map = json.load(f)
            else: initial_region_map = json.loads(args.label_map)
            if not isinstance(initial_region_map, dict): initial_region_map = {}
        except Exception as e: print(f"Error loading --label-map: {e}", file=sys.stderr); initial_region_map = {}

    liability_codes = {}
    existing_numeric_keys = [int(k) for k in initial_region_map.keys() if str(k).isdigit()] if isinstance(initial_region_map, dict) else []
    next_code = max(existing_numeric_keys or [-1]) + 1

    try:
        df = pl.read_csv(args.input_tsv, separator="\t", ignore_errors=True, infer_schema_length=1000)
        df.columns = [" ".join(col.strip().split()) for col in df.columns] # Normalize column names
    except Exception as e: sys.exit(f"Error reading input TSV '{args.input_tsv}': {e}")
    df_processed = df.clone()

    ann_cols = [c for c in df_processed.columns if c.lower().endswith("annotations")]
    has_input_ann_cols = bool(ann_cols)
    all_seq_cols = [c for c in df_processed.columns if c.lower().endswith("aa")] # All potential sequence columns
    TARGET_REGION_KEYS = ["cdr1 aa", "cdr2 aa", "cdr3 aa", "fr1 aa"] # For Path B
    cols_for_liability_analysis = []
    skip_extraction_due_to_preexisting_regions = False

    if has_input_ann_cols:
        unique_ann_prefixes = set()
        for name in ann_cols: prefix = name[:-len("annotations")].strip().rstrip("_"); unique_ann_prefixes.add(prefix)
        if unique_ann_prefixes:
            all_prefix_sets_found_preexisting = True; temp_cols_for_liability_if_skipping = []
            for ann_prefix_raw in unique_ann_prefixes:
                prefix_for_col_lookup = f"{ann_prefix_raw} " if ann_prefix_raw else ""
                current_prefix_all_regions_found = True
                for region_base in ["CDR1", "CDR2", "CDR3", "FR1"]: # Check for FR1, CDR1, CDR2, CDR3
                    expected_col_name = " ".join(f"{prefix_for_col_lookup}{region_base} aa".split())
                    if expected_col_name not in df_processed.columns: current_prefix_all_regions_found = False; print(f"Pre-existing check: '{expected_col_name}' not found for prefix '{ann_prefix_raw}'."); break
                    temp_cols_for_liability_if_skipping.append(expected_col_name)
                if not current_prefix_all_regions_found: all_prefix_sets_found_preexisting = False; break
            if all_prefix_sets_found_preexisting:
                skip_extraction_due_to_preexisting_regions = True
                cols_for_liability_analysis.extend(temp_cols_for_liability_if_skipping)
                cols_for_liability_analysis = sorted(list(set(cols_for_liability_analysis)))
                print(f"Pre-existing CDR/FR columns found. Skipping extraction. Using: {cols_for_liability_analysis}")

    if skip_extraction_due_to_preexisting_regions:
        print(f"Proceeding with pre-existing columns: {cols_for_liability_analysis}")
    elif has_input_ann_cols: # Path A: Annotation-based extraction
        print(f"Path A: Extracting regions and updating annotations (with FR1 specific logic if liabilities are calculated).")
        chain_prefixes_found = set()
        for ann_col_name_for_prefix_check in ann_cols:
            if " " in ann_col_name_for_prefix_check: chain_prefixes_found.add(ann_col_name_for_prefix_check.split(" ")[0])
        multiple_chains_present = len(chain_prefixes_found) > 1 and any(p.lower() in ["heavy", "light"] for p in chain_prefixes_found)
        
        processed_frag_dfs = []
        str_key_initial_region_map = {str(k): str(v) for k, v in initial_region_map.items()}

        for ann_col_name in ann_cols:
            current_prefix_raw = ann_col_name[:-len("annotations")].strip().rstrip("_")
            seq_col_name_to_find = (f"{current_prefix_raw} sequence aa".lower()) if current_prefix_raw else "sequence aa"
            matched_seq_cols = [sc for sc in all_seq_cols if sc.lower() == seq_col_name_to_find]
            if not matched_seq_cols and current_prefix_raw: matched_seq_cols = [sc for sc in all_seq_cols if sc.lower() == f"{current_prefix_raw} aa".lower()] # Fallback for e.g. "Heavy aa"
            if not matched_seq_cols: print(f"⚠️ Path A: Skip {ann_col_name}: No corresponding sequence column '{seq_col_name_to_find}' found.", file=sys.stderr); continue
            
            seq_col_name = matched_seq_cols[0]
            updated_annotations_for_col, fragment_rows_for_col = [], []

            for seq_data, ann_data in zip(df_processed[seq_col_name].to_list(), df_processed[ann_col_name].to_list()):
                if seq_data is None or ann_data is None: updated_annotations_for_col.append(ann_data); fragment_rows_for_col.append({}); continue
                
                parsed_segments = parse_annotations(ann_data)
                extracted_frags, frag_coords = extract_cdrs_fr1(seq_data, parsed_segments, str_key_initial_region_map)
                current_ann_parts = [p for p in (ann_data.split("|") if ann_data and ann_data.strip() else []) if p]
                
                if CALCULATE_LIABILITIES:
                    for region_name, fragment_seq in extracted_frags.items():
                        start_coord, _ = frag_coords[region_name]
                        if region_name == "FR1":
                            # print(f"DEBUG PathA Annotate: FR1 detected. active_cys_defs: {active_cys_defs.keys()}")
                            if active_cys_defs:
                                expected_indices_fr1 = EXPECTED_CYS.get("FR1", [])
                                if expected_indices_fr1:
                                    actual_cys_fr1 = fragment_seq.count("C")
                                    expected_cys_fr1 = len(expected_indices_fr1)
                                    cys_liability_name = None
                                    if actual_cys_fr1 < expected_cys_fr1: cys_liability_name = "Missing Cysteines"
                                    elif actual_cys_fr1 > expected_cys_fr1: cys_liability_name = "Extra Cysteines"
                                    
                                    if cys_liability_name and cys_liability_name in active_cys_defs:
                                        # print(f"DEBUG PathA Annotate: FR1 Cys liability '{cys_liability_name}' found and active.")
                                        if cys_liability_name not in liability_codes:
                                            liability_codes[cys_liability_name] = str(next_code); next_code +=1
                                        code = liability_codes[cys_liability_name]
                                        current_ann_parts.append(f"{code}:{base36_encode(start_coord)}+{base36_encode(0)}") # Length 0 for point annotation
                        else: # For CDRs and other non-FR1 regions from extraction
                            for liability_name, pattern in active_liability_regex.items():
                                for match in re.finditer(pattern, fragment_seq):
                                    global_start, global_length = start_coord + match.start(), match.end() - match.start()
                                    if liability_name not in liability_codes: liability_codes[liability_name] = str(next_code); next_code += 1
                                    code = liability_codes[liability_name]
                                    current_ann_parts.append(f"{code}:{base36_encode(global_start)}+{base36_encode(global_length)}")
                
                updated_annotations_for_col.append("|".join(sorted(list(set(current_ann_parts)))))
                row_dict = {}
                prefix_for_frag_col = f"{current_prefix_raw.capitalize()} " if current_prefix_raw and multiple_chains_present else ""
                for r_name, r_seq in extracted_frags.items(): row_dict[f"{prefix_for_frag_col}{r_name} aa"] = r_seq
                fragment_rows_for_col.append(row_dict)

            df_processed = df_processed.with_columns(pl.Series(name=ann_col_name, values=updated_annotations_for_col))
            if fragment_rows_for_col:
                schema_for_frag_df = None; first_valid_row = next((item for item in fragment_rows_for_col if item), None)
                if first_valid_row: schema_for_frag_df = {col_name: pl.Utf8 for col_name in first_valid_row.keys()}
                if schema_for_frag_df:
                    filled_rows = [{key: row.get(key) for key in schema_for_frag_df} for row in fragment_rows_for_col] # Ensure all rows have all keys
                    try:
                        processed_frag_dfs.append(pl.DataFrame(filled_rows, schema=schema_for_frag_df))
                    except ShapeError: # If df_processed is empty, zip makes empty lists, then this fails.
                         print(f"Warning: Could not create DataFrame from fragments for {ann_col_name}, possibly due to empty input or processing issue.", file=sys.stderr)


        if processed_frag_dfs:
            expected_height = len(df_processed)
            aligned_frag_dfs = [df_frag for df_frag in processed_frag_dfs if len(df_frag) == expected_height]
            if not aligned_frag_dfs and processed_frag_dfs: # If some frags were processed but height mismatch
                 print(f"Warning: Height mismatch for fragment DataFrames. Expected {expected_height}, got {[len(df) for df in processed_frag_dfs]}. Skipping fragment concatenation.", file=sys.stderr)

            if aligned_frag_dfs:
                # Concatenate new fragment columns, ensure no duplicate columns are formed if they somehow pre-existed
                # This horizontal concatenation assumes that df_processed and the fragment dfs are row-aligned.
                # Polars' concat(how='horizontal') requires dataframes to have same number of rows.
                try:
                    df_processed = pl.concat([df_processed] + aligned_frag_dfs, how="horizontal")
                except ShapeError as e:
                     print(f"Error during horizontal concatenation of extracted fragments: {e}. Fragment columns might be missing.", file=sys.stderr)


        path_a_frag_cols = [c for c in df_processed.columns if c.lower().endswith(" aa") and any(k in c.lower() for k in ["cdr1","cdr2","cdr3","fr1"]) and not c.lower().endswith("sequence aa")]
        cols_for_liability_analysis.extend(path_a_frag_cols); cols_for_liability_analysis = sorted(list(set(cols_for_liability_analysis)))

    elif not has_input_ann_cols: # Path B: No annotations, use direct sequence columns
        print(f"Path B (No Annotations Mode): Using direct sequence columns ending with predefined keys (e.g., 'CDR1 aa').")
        candidate_seq_cols_for_path_b = [c for c in all_seq_cols if any(key_suffix in c.lower() for key_suffix in TARGET_REGION_KEYS)]
        if not candidate_seq_cols_for_path_b:
            print("Path B: No standard FR/CDR sequence columns (e.g., 'CDR1 aa') found.");
            # Don't return early - continue to generate expected output columns even without liabilities
        cols_for_liability_analysis.extend(candidate_seq_cols_for_path_b); cols_for_liability_analysis = sorted(list(set(cols_for_liability_analysis)))
    
    if not cols_for_liability_analysis and CALCULATE_LIABILITIES:
        print(f"Warning: No columns identified for liability analysis, but liabilities were requested. Skipping liability calculation.")
        CALCULATE_LIABILITIES = False # Force skip if no columns to act on
    elif not cols_for_liability_analysis and not CALCULATE_LIABILITIES:
        print(f"No columns identified for liability analysis (and no liabilities were requested).")


    if CALCULATE_LIABILITIES and cols_for_liability_analysis: # Ensure CALCULATE_LIABILITIES is still true
        print(f"Generating liabilities for columns: {cols_for_liability_analysis}")
        liability_expressions, risk_expressions = [], []
        generated_liability_summary_col_names, generated_risk_col_names = [], []

        for frag_seq_col in cols_for_liability_analysis:
            if frag_seq_col not in df_processed.columns: continue # Should not happen if logic is correct
            match = re.search(r"(FR[1-4]|CDR[1-3])", frag_seq_col, re.IGNORECASE) # More specific match
            core_region_name = match.group(1).upper() if match else "UNKNOWN_REGION"
            new_liab_col = f"{frag_seq_col} liabilities" # e.g. "Heavy CDR1 aa liabilities"
            generated_liability_summary_col_names.append(new_liab_col)
            liability_expressions.append(pl.col(frag_seq_col).cast(pl.Utf8).map_elements(
                lambda s, fsc=frag_seq_col, crn=core_region_name: identify_liabilities(s, crn, active_cdr_defs, active_extra_defs, active_cys_defs, EXPECTED_CYS, debug_col_name=fsc),
                return_dtype=pl.Utf8, skip_nulls=False).fill_null("Unknown").alias(new_liab_col))
        if liability_expressions: df_processed = df_processed.with_columns(liability_expressions)

        # ---- START: New section to create "Sequence liabilities summary" ----
        summary_struct_cols = [c for c in generated_liability_summary_col_names if c in df_processed.columns]
        if summary_struct_cols:
            print(f"Generating sequence liabilities summary from columns: {summary_struct_cols}")
            df_processed = df_processed.with_columns(
                pl.struct(summary_struct_cols)
                .map_elements(_create_sequence_liabilities_summary_str, return_dtype=pl.Utf8, skip_nulls=False)
                .fill_null("None")
                .alias("Sequence liabilities summary")
            )
        elif "Sequence liabilities summary" not in df_processed.columns:
            df_processed = df_processed.with_columns(pl.lit("None").cast(pl.Utf8).alias("Sequence liabilities summary"))
        # ---- END: New section ----

        for liab_col in generated_liability_summary_col_names: # These are the individual "... aa liabilities" cols
            if liab_col not in df_processed.columns: continue
            new_risk_col = liab_col.replace(" liabilities", " risk")
            generated_risk_col_names.append(new_risk_col)
            risk_expressions.append(pl.col(liab_col).cast(pl.Utf8).map_elements(
                lambda l_str: classify_risk(l_str, active_cdr_defs, active_cys_defs, set(active_extra_defs.keys())),
                return_dtype=pl.Utf8, skip_nulls=False).fill_null("None").alias(new_risk_col))
        if risk_expressions: df_processed = df_processed.with_columns(risk_expressions)

        existing_risk_cols_for_struct = [c for c in generated_risk_col_names if c in df_processed.columns]
        if existing_risk_cols_for_struct:
            df_processed = df_processed.with_columns(pl.struct([pl.col(c) for c in existing_risk_cols_for_struct])
                .map_elements(overall_risk_func, return_dtype=pl.Utf8, skip_nulls=False).fill_null("None").alias("Liabilities risk"))
        elif "Liabilities risk" not in df_processed.columns:
             df_processed = df_processed.with_columns(pl.lit("None").cast(pl.Utf8).alias("Liabilities risk"))

        df_processed = _combine_heavy_light_prefixed_columns(df_processed, "risk")
        df_processed = _combine_heavy_light_prefixed_columns(df_processed, "liabilities")

    # Output Column Selection & Final Write
    # Include clonotypeKey if it exists, otherwise use empty list
    output_cols_core = ["clonotypeKey"] if "clonotypeKey" in df_processed.columns else []
    final_annotation_cols_list = ann_cols if has_input_ann_cols else []
    final_annotation_cols = sorted(list(set(final_annotation_cols_list)))
    
    # Handle CDR3 sequence columns
    final_cdr3_seq_cols = []
    if df_processed.width > 0:  # Normal case - find existing columns
        heavy_light_cdr3 = sorted([c for c in df_processed.columns if re.search(r'^(heavy|light) cdr3 aa$', c, re.IGNORECASE)])
        general_cdr3 = sorted([c for c in df_processed.columns if re.search(r'cdr3 aa$', c, re.IGNORECASE) and c not in heavy_light_cdr3])
        final_cdr3_seq_cols = heavy_light_cdr3 + general_cdr3
        if not final_cdr3_seq_cols:
            potential_cdr3 = sorted([c for c in df_processed.columns if "cdr3" in c.lower() and c.lower().endswith("aa")])
            if potential_cdr3: final_cdr3_seq_cols = potential_cdr3
    else:  # Empty input case - generate expected column names
        # For empty input, always generate bulk columns (standard CDR3 column)
        final_cdr3_seq_cols = ["CDR3 aa"]

    individual_frag_liabs, individual_frag_risks = [], []
    combined_chain_liabs, combined_chain_risks = [], []
    combined_region_liabs, combined_region_risks = [], []
    
    overall_summary_cols = [] # Renamed from overall_liab_risk_col for clarity
    print(f"DEBUG: CALCULATE_LIABILITIES={CALCULATE_LIABILITIES}, df_processed.width={df_processed.width}", file=sys.stderr)
    if CALCULATE_LIABILITIES:
        if df_processed.width > 0:  # Normal case - find existing columns
            all_liab_cols = [c for c in df_processed.columns if c.endswith(" liabilities")]
            all_risk_cols = [c for c in df_processed.columns if c.endswith(" risk")]
            
            individual_frag_liabs = sorted([c for c in all_liab_cols if " aa liabilities" in c.lower() and c != "Sequence liabilities summary"])
            individual_frag_risks = sorted([c for c in all_risk_cols if " aa risk" in c.lower() and c != "Liabilities risk"])
            
            combined_chain_liabs = sorted([c for c in all_liab_cols if c.lower() in ["heavy liabilities", "light liabilities"] and c not in individual_frag_liabs])
            combined_chain_risks = sorted([c for c in all_risk_cols if c.lower() in ["heavy risk", "light risk"] and c not in individual_frag_risks])
            
            combined_region_liabs = sorted([c for c in all_liab_cols if c not in individual_frag_liabs and c not in combined_chain_liabs and c.lower() != "liabilities risk" and c != "Sequence liabilities summary"])
            combined_region_risks = sorted([c for c in all_risk_cols if c not in individual_frag_risks and c not in combined_chain_risks and c.lower() != "liabilities risk"])
            
            # Build the overall_summary_cols list for output ordering
            if "Liabilities risk" in df_processed.columns:
                overall_summary_cols.append("Liabilities risk")
            if "Sequence liabilities summary" in df_processed.columns:
                if "Liabilities risk" in overall_summary_cols: # Try to place it after "Liabilities risk"
                    try:
                        idx = overall_summary_cols.index("Liabilities risk")
                        overall_summary_cols.insert(idx + 1, "Sequence liabilities summary")
                    except ValueError: # Should not happen
                        overall_summary_cols.append("Sequence liabilities summary")
                else: # No "Liabilities risk" column, just append
                    overall_summary_cols.append("Sequence liabilities summary")
        else:  # Empty input case - generate expected column names
            # For empty input, always generate bulk columns (standard liability and risk columns)
            expected_regions = ["CDR1", "CDR2", "CDR3", "FR1"]
            for region in expected_regions:
                individual_frag_liabs.append(f"{region} aa liabilities")
                individual_frag_risks.append(f"{region} aa risk")
            
            # Add summary columns
            overall_summary_cols = ["Liabilities risk", "Sequence liabilities summary"]
            
            # Sort the generated columns
            individual_frag_liabs = sorted(individual_frag_liabs)
            individual_frag_risks = sorted(individual_frag_risks)
    else: # If liabilities not calculated, ensure these summary columns are not accidentally included if they somehow exist
        if "Liabilities risk" in df_processed.columns and "Liabilities risk" not in output_cols_core:
             # If user wants it even without calc, they'd need to specify it or it's a pre-existing column to keep
             pass # For now, only add if CALCULATE_LIABILITIES is true for generated ones.
        if "Sequence liabilities summary" in df_processed.columns and "Sequence liabilities summary" not in output_cols_core :
             pass
        
        # For empty input without liabilities, still generate expected bulk columns
        if df_processed.width == 0:
            # Generate expected liability and risk columns for empty input (even without calculating)
            expected_regions = ["CDR1", "CDR2", "CDR3", "FR1"]
            for region in expected_regions:
                individual_frag_liabs.append(f"{region} aa liabilities")
                individual_frag_risks.append(f"{region} aa risk")
            
            # Add summary columns
            overall_summary_cols = ["Liabilities risk", "Sequence liabilities summary"]
            
            # Sort the generated columns
            individual_frag_liabs = sorted(individual_frag_liabs)
            individual_frag_risks = sorted(individual_frag_risks)


    output_cols_ordered = list(dict.fromkeys(
        output_cols_core + final_annotation_cols + final_cdr3_seq_cols +
        individual_frag_liabs + combined_region_liabs + combined_chain_liabs +
        individual_frag_risks + combined_region_risks + combined_chain_risks +
        overall_summary_cols )) # <-- "Sequence liabilities summary" and "Liabilities risk" included here
    
    print(f"DEBUG: Column generation - output_cols_core={output_cols_core}", file=sys.stderr)
    print(f"DEBUG: Column generation - final_annotation_cols={final_annotation_cols}", file=sys.stderr)
    print(f"DEBUG: Column generation - final_cdr3_seq_cols={final_cdr3_seq_cols}", file=sys.stderr)
    print(f"DEBUG: Column generation - individual_frag_liabs={individual_frag_liabs}", file=sys.stderr)
    print(f"DEBUG: Column generation - overall_summary_cols={overall_summary_cols}", file=sys.stderr)
    
    # For empty input or when no liabilities calculated, force generation of all expected bulk columns
    # Check if we have insufficient columns (only core + annotations, no liability/risk columns)
    has_insufficient_columns = (len(output_cols_ordered) <= 2)
    print(f"DEBUG: has_insufficient_columns={has_insufficient_columns}, len(output_cols_ordered)={len(output_cols_ordered)}", file=sys.stderr)
    
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
        expected_bulk_columns.extend([
            "CDR3 aa",
            "CDR1 aa liabilities",
            "CDR2 aa liabilities", 
            "CDR3 aa liabilities",
            "FR1 aa liabilities",
            "CDR1 aa risk",
            "CDR2 aa risk",
            "CDR3 aa risk",
            "FR1 aa risk",
            "Liabilities risk",
            "Sequence liabilities summary"
        ])
        
        # Create missing columns with empty/default values
        missing_columns = [c for c in expected_bulk_columns if c not in df_processed.columns]
        if missing_columns:
            print(f"DEBUG: Creating missing columns: {missing_columns}", file=sys.stderr)
            # Add empty columns for missing ones
            for col in missing_columns:
                df_processed = df_processed.with_columns(pl.lit("").alias(col))
        
        output_cols_existing = expected_bulk_columns
        print(f"DEBUG: Forcing bulk columns. df_processed.width={df_processed.width}, CALCULATE_LIABILITIES={CALCULATE_LIABILITIES}", file=sys.stderr)
        print(f"DEBUG: All expected bulk columns: {output_cols_existing}", file=sys.stderr)
    else:
        output_cols_existing = [c for c in output_cols_ordered if c in df_processed.columns]
    
    df_out = df_processed.select(output_cols_existing) if output_cols_existing else df_processed.clone() # Clone if no selection to avoid issues with empty df_out if df_processed has columns
    
    if not output_cols_existing and df_processed.width > 0 : print("No columns selected for final output based on defined order criteria. Writing entire processed DataFrame.", file=sys.stderr)
    elif not output_cols_existing and df_processed.width == 0: print("Input was empty and no columns processed or selected.", file=sys.stderr)


    if df_out.width == 0 and df_processed.width > 0:
        print("Output selection resulted in an empty DataFrame, but processed data exists. Writing full processed DataFrame instead.")
        df_out = df_processed
    elif df_out.width == 0:
        print("Processed DataFrame is empty or output selection is empty. Nothing to write to TSV.", file=sys.stderr)

    if df_out.width > 0:
        try:
            df_out.write_csv(args.output_tsv, separator="\t", quote_style="never")
            print(f"Output table written to {args.output_tsv}")
        except Exception as e: print(f"Error writing output TSV: {e}", file=sys.stderr)
    else: # df_out.width == 0
        if args.output_tsv: # If output path is given, write empty file with headers
            try:
                with open(args.output_tsv, 'w') as f_empty:
                    # Always write headers if they could be determined, even for empty input
                    if output_cols_existing:
                        f_empty.write("\t".join(output_cols_existing) + "\n")
                    elif df_processed.width > 0:
                        f_empty.write("\t".join(df_processed.columns) + "\n")
                    elif df_processed.columns:  # Even if width is 0, columns might exist
                        f_empty.write("\t".join(df_processed.columns) + "\n")
                    # else, an empty file is created (no headers possible)
                print(f"Empty output table with headers written to {args.output_tsv} as no data rows were processed/selected.")
            except Exception as e:
                 print(f"Error writing empty output TSV to '{args.output_tsv}': {e}", file=sys.stderr)

    if args.output_regions_found:
        found_regions_set = set()
        CANONICAL_REGIONS = ["CDR1", "CDR2", "CDR3", "FR1", "FR2", "FR3", "FR4"] # Expanded
        if cols_for_liability_analysis: # Based on what was analyzed
            for col_name in cols_for_liability_analysis:
                for region_canonical_name in CANONICAL_REGIONS:
                    # Use regex to match whole word region name to avoid FR1 matching in e.g. "MYFR10Sequence"
                    if re.search(r'\b' + re.escape(region_canonical_name) + r'\b', col_name, re.IGNORECASE):
                        found_regions_set.add(region_canonical_name)
                        break # Found one canonical region in this col_name
            list_of_found_regions = sorted(list(found_regions_set), key=lambda x: REGION_ORDER_MAP.get(x, 99))
        else: list_of_found_regions = []
        try:
            with open(args.output_regions_found, 'w') as f: json.dump(list_of_found_regions, f, indent=2) # sort_keys=True for dicts, not lists
            print(f"List of found regions {list_of_found_regions} written to {args.output_regions_found}")
        except IOError as e: print(f"Error writing found regions list to '{args.output_regions_found}': {e}", file=sys.stderr)

    if not has_input_ann_cols and not CALCULATE_LIABILITIES: # No annotations and no calculation attempt
        _output_final_label_map({}, {}, args.output_label_map, "Empty Label Map (No annotations and no liabilities calculated)")
    elif not CALCULATE_LIABILITIES: # Annotations might exist, but no calculation
        _output_final_label_map(initial_region_map, {}, args.output_label_map, "Label Map (Regions Only; No Liabilities Calculated)")
    else: # Liabilities were calculated (or attempted)
        _output_final_label_map(initial_region_map, liability_codes, args.output_label_map, "Final Combined Label Map")

if __name__ == "__main__":
    main()