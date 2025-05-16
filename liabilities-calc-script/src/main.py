#!/usr/bin/env python3
import polars as pl
from polars.exceptions import ShapeError
import re
import argparse
import sys
import json
import os

# --- Original Liability Definitions (ORIG_...) ---
# ... (Unchanged from the previous version) ...
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


# --- Helper functions (get_active_liability_definitions, identify_liabilities, classify_risk, etc.) ---
# ... (Unchanged from the previous version) ...
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

def identify_liabilities(seq: str, region: str, 
                         active_cdr_defs: dict, 
                         active_extra_defs: dict, 
                         active_cys_defs: dict, 
                         expected_cys_map: dict) -> str:
    if not seq or not isinstance(seq, str) or not seq.strip(): return "Unknown"
    liabilities_found = []
    for name, pattern in active_extra_defs.items():
        if re.search(pattern, seq): liabilities_found.append(name)
    if region.startswith("CDR"):
        for name, (pattern, _) in active_cdr_defs.items():
            if name == "Tryptophan Oxidation (W)" and region == "CDR3":
                if re.search(r"W(?!$)", seq): liabilities_found.append(name)
            elif name != "Tryptophan Oxidation (W)" and re.search(pattern, seq):
                 liabilities_found.append(name)
        if region != "CDR3" and "Tryptophan Oxidation (W)" in active_cdr_defs and \
           "Tryptophan Oxidation (W)" not in liabilities_found and \
           re.search(active_cdr_defs["Tryptophan Oxidation (W)"][0], seq):
            liabilities_found.append("Tryptophan Oxidation (W)")
    elif region.startswith("FR"): 
        fr_applicable_names = {"Methionine Oxidation (M)", "Tryptophan Oxidation (W)"}
        for name in fr_applicable_names:
            if name in active_cdr_defs: 
                pattern, _ = active_cdr_defs[name]
                if re.search(pattern, seq): liabilities_found.append(name)
    if active_cys_defs:
        expected_indices = expected_cys_map.get(region, [])
        if expected_indices:
            actual_cys_count = seq.count("C"); expected_count = len(expected_indices)
            if "Missing Cysteines" in active_cys_defs and actual_cys_count < expected_count:
                liabilities_found.append("Missing Cysteines")
            elif "Extra Cysteines" in active_cys_defs and actual_cys_count > expected_count:
                liabilities_found.append("Extra Cysteines")
    return ", ".join(sorted(list(set(liabilities_found)))) if liabilities_found else "None"

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
            if current_max_risk_level == risk_map["High"]: return "High"; continue
        if item in active_cdr_defs:
            item_risk_str = active_cdr_defs[item][1] 
            if risk_map[item_risk_str] > current_max_risk_level: current_max_risk_level = risk_map[item_risk_str]
            if current_max_risk_level == risk_map["High"]: return "High"; continue
        if item in active_extra_pattern_names: 
            if risk_map["High"] > current_max_risk_level: current_max_risk_level = risk_map["High"]
            if current_max_risk_level == risk_map["High"]: return "High"
    return level_to_risk[current_max_risk_level]

def base36_encode(n: int) -> str:
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if n == 0: return "0"
    s = "";
    while n > 0: n, r = divmod(n, 36); s = digits[r] + s
    return s
def base36_decode(s: str) -> int: return int(s, 36)
def parse_annotations(ann: str):
    segs = []
    if not ann or not isinstance(ann, str): return segs
    for part in ann.split("|"):
        if ":" not in part or "+" not in part: continue
        lab, rest = part.split(":", 1); st36, ln36 = rest.split("+", 1)
        try: segs.append((lab, base36_decode(st36), base36_decode(ln36)))
        except ValueError: print(f"Warning: Could not decode part '{part}' in annotation '{ann}'", file=sys.stderr); continue
    return sorted(segs, key=lambda x: x[1])
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
def overall_risk_func(row_struct: dict) -> str:
    risk_values = [str(v).strip() for v in row_struct.values() if v is not None]
    if "High" in risk_values: return "High"
    if "Medium" in risk_values: return "Medium"
    if "Low" in risk_values: return "Low"
    return "None" # Default to None if no specific risk levels found or only "Unknown"
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
    for liability_name, code in liability_map.items(): final_map_all_strings[str(code)] = str(liability_name) # Inverted here
    if output_path:
        try:
            with open(output_path, "w") as f: json.dump(final_map_all_strings, f, indent=2, sort_keys=True) # Added sort_keys
            print(f"✅ {description} label map written to {output_path}")
        except IOError as e: print(f"❌ Error writing {description} label map to '{output_path}': {e}", file=sys.stderr)
    else: print(f"\n{description} label map:\n{json.dumps(final_map_all_strings, indent=2, sort_keys=True)}")


# ——— MAIN SCRIPT —————————————————————————————————————
def main():
    p = argparse.ArgumentParser(description="Extract CDRs/FR1, analyze liabilities, compute risk.")
    p.add_argument("input_tsv", help="Input TSV")
    p.add_argument("output_tsv", help="Output TSV")
    p.add_argument("-m", "--label-map", help="JSON file or string for numeric region labels to names.")
    p.add_argument("-o", "--output-label-map", help="Where to write JSON label map. Empty map if no input annotations or no liabilities calculated.")
    p.add_argument("--include-liabilities", type=str,
                   help="A comma-delimited string of specific liability names to calculate (e.g., \"Deamidation (N[GS]),Methionine Oxidation (M)\"). If not provided, no liabilities or risks are calculated.")
    p.add_argument("--output-regions-found", type=str, # New argument
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
            print("⚠️ --include-liabilities provided, but no recognized liability names matched internal definitions. No liabilities will be calculated.")
            CALCULATE_LIABILITIES = False 
            active_cdr_defs, active_extra_defs, active_cys_defs, active_liability_regex = {}, {}, {}, {}
        else:
            # Create a list of actually recognized and active liabilities for the print message
            recognized_active_set = set(active_cdr_defs.keys()) | set(active_extra_defs.keys()) | set(active_cys_defs.keys())
            print(f"ℹ️ Will calculate for requested and recognized liabilities: {sorted(list(recognized_active_set))}")
    else:
        print("ℹ️ --include-liabilities not provided or no recognized names. Liability and risk calculations will be skipped.")
        active_cdr_defs, active_extra_defs, active_cys_defs, active_liability_regex = {}, {}, {}, {}

    initial_region_map = {}
    if args.label_map:
        try:
            if os.path.isfile(args.label_map):
                with open(args.label_map, 'r') as f: initial_region_map = json.load(f)
            else: initial_region_map = json.loads(args.label_map)
            if not isinstance(initial_region_map, dict): initial_region_map = {}
        except Exception as e: print(f"❌ Error loading --label-map: {e}", file=sys.stderr); initial_region_map = {}

    liability_codes = {} 
    existing_numeric_keys = [int(k) for k in initial_region_map.keys() if str(k).isdigit()] if isinstance(initial_region_map, dict) else []
    next_code = max(existing_numeric_keys or [-1]) + 1

    try:
        df = pl.read_csv(args.input_tsv, separator="\t", ignore_errors=True, infer_schema_length=1000)
        df.columns = [" ".join(col.strip().split()) for col in df.columns]
    except Exception as e: sys.exit(f"❌ Error reading input TSV '{args.input_tsv}': {e}")
    df_processed = df.clone()
    
    ann_cols = [c for c in df_processed.columns if c.lower().endswith("annotations")]
    has_input_ann_cols = bool(ann_cols) 
    all_seq_cols = [c for c in df_processed.columns if c.lower().endswith("aa")]
    TARGET_REGION_KEYS = ["cdr1 aa", "cdr2 aa", "cdr3 aa", "fr1 aa"]
    cols_for_liability_analysis = []
    skip_extraction_due_to_preexisting_regions = False

    if has_input_ann_cols: # Pre-extraction check
        unique_ann_prefixes = set()
        for name in ann_cols: prefix = name[:-len("annotations")].strip().rstrip("_"); unique_ann_prefixes.add(prefix)
        if unique_ann_prefixes:
            all_prefix_sets_found_preexisting = True; temp_cols_for_liability_if_skipping = []
            for ann_prefix_raw in unique_ann_prefixes:
                prefix_for_col_lookup = f"{ann_prefix_raw} " if ann_prefix_raw else ""
                current_prefix_all_regions_found = True
                for region_base in ["CDR1", "CDR2", "CDR3", "FR1"]:
                    expected_col_name = " ".join(f"{prefix_for_col_lookup}{region_base} aa".split())
                    if expected_col_name not in df_processed.columns: current_prefix_all_regions_found = False; print(f"ℹ️ Pre-existing check: '{expected_col_name}' not found for prefix '{ann_prefix_raw}'."); break 
                    temp_cols_for_liability_if_skipping.append(expected_col_name)
                if not current_prefix_all_regions_found: all_prefix_sets_found_preexisting = False; break 
            if all_prefix_sets_found_preexisting:
                skip_extraction_due_to_preexisting_regions = True
                cols_for_liability_analysis.extend(temp_cols_for_liability_if_skipping)
                cols_for_liability_analysis = sorted(list(set(cols_for_liability_analysis)))
                print(f"✅ Pre-existing CDR/FR columns found. Skipping extraction. Using: {cols_for_liability_analysis}")

    if skip_extraction_due_to_preexisting_regions:
        print(f"ℹ️ Proceeding with pre-existing columns: {cols_for_liability_analysis}")
    elif has_input_ann_cols: 
        print(f"ℹ️ Path A: Extracting regions and updating annotations (if liabilities are calculated).")
        # --- PATH A ---
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
            if not matched_seq_cols and current_prefix_raw: matched_seq_cols = [sc for sc in all_seq_cols if sc.lower() == f"{current_prefix_raw} aa".lower()]
            if not matched_seq_cols: print(f"⚠️ Path A: Skip {ann_col_name}: No seq col.", file=sys.stderr); continue
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
                    filled_rows = [{key: row.get(key) for key in schema_for_frag_df} for row in fragment_rows_for_col]
                    processed_frag_dfs.append(pl.DataFrame(filled_rows, schema=schema_for_frag_df))
        if processed_frag_dfs: 
            expected_height = len(df_processed)
            aligned_frag_dfs = [df_frag for df_frag in processed_frag_dfs if len(df_frag) == expected_height]
            if aligned_frag_dfs: df_processed = pl.concat([df_processed, pl.concat(aligned_frag_dfs, how="horizontal")], how="horizontal")
        path_a_frag_cols = [c for c in df_processed.columns if c.lower().endswith(" aa") and any(k in c.lower() for k in ["cdr1","cdr2","cdr3","fr1"]) and not c.lower().endswith("sequence aa")]
        cols_for_liability_analysis.extend(path_a_frag_cols); cols_for_liability_analysis = sorted(list(set(cols_for_liability_analysis)))
    elif not has_input_ann_cols: 
        print(f"ℹ️ Path B (No Annotations Mode): Using direct sequence columns.")
        candidate_seq_cols_for_path_b = [c for c in all_seq_cols if any(key_suffix in c.lower() for key_suffix in TARGET_REGION_KEYS)]
        if not candidate_seq_cols_for_path_b:
            print("ℹ️ Path B: No standard sequence columns found. Writing input unchanged."); df_processed.write_csv(args.output_tsv, separator="\t"); return
        cols_for_liability_analysis.extend(candidate_seq_cols_for_path_b); cols_for_liability_analysis = sorted(list(set(cols_for_liability_analysis)))
    
    if not cols_for_liability_analysis and CALCULATE_LIABILITIES: 
        print(f"⚠️ No columns identified for liability analysis, but liabilities were requested.")
    elif not cols_for_liability_analysis and not CALCULATE_LIABILITIES:
        print(f"ℹ️ No columns identified for liability analysis (and none were requested).")

    if CALCULATE_LIABILITIES and cols_for_liability_analysis:
        # ... (Common Downstream Processing for Liabilities and Risks - unchanged from previous version) ...
        print(f"ℹ️ Generating liabilities for columns: {cols_for_liability_analysis}")
        liability_expressions, risk_expressions = [], []
        generated_liability_summary_col_names, generated_risk_col_names = [], []
        for frag_seq_col in cols_for_liability_analysis:
            if frag_seq_col not in df_processed.columns: continue
            match = re.search(r"(FR1|CDR1|CDR2|CDR3)", frag_seq_col, re.IGNORECASE)
            core_region_name = match.group(1).upper() if match else "UNKNOWN_REGION"
            new_liab_col = f"{frag_seq_col} liabilities"
            generated_liability_summary_col_names.append(new_liab_col)
            liability_expressions.append(pl.col(frag_seq_col).cast(pl.Utf8).map_elements(
                lambda s: identify_liabilities(s, core_region_name, active_cdr_defs, active_extra_defs, active_cys_defs, EXPECTED_CYS),
                return_dtype=pl.Utf8, skip_nulls=False).fill_null("Unknown").alias(new_liab_col))
        if liability_expressions: df_processed = df_processed.with_columns(liability_expressions)
        for liab_col in generated_liability_summary_col_names:
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
        
    # --- Output Column Selection & Final Write ---
    # ... (Unchanged from previous version, will naturally exclude liability/risk cols if not calculated) ...
    output_cols_core = ["clonotypeKey"] if "clonotypeKey" in df_processed.columns else []
    final_annotation_cols_list = ann_cols if has_input_ann_cols else [] 
    final_annotation_cols = sorted(list(set(final_annotation_cols_list))) 
    final_cdr3_seq_cols = []
    heavy_light_cdr3 = sorted([c for c in df_processed.columns if re.search(r'^(heavy|light) cdr3 aa$', c, re.IGNORECASE)])
    general_cdr3 = sorted([c for c in df_processed.columns if re.search(r'cdr3 aa$', c, re.IGNORECASE) and c not in heavy_light_cdr3])
    final_cdr3_seq_cols = heavy_light_cdr3 + general_cdr3
    if not final_cdr3_seq_cols:
        potential_cdr3 = sorted([c for c in df_processed.columns if "cdr3" in c.lower() and c.lower().endswith("aa")])
        if potential_cdr3: final_cdr3_seq_cols = potential_cdr3
    individual_frag_liabs, individual_frag_risks = [], []
    combined_chain_liabs, combined_chain_risks = [], []
    combined_region_liabs, combined_region_risks = [], []
    overall_liab_risk_col = []
    if CALCULATE_LIABILITIES: 
        all_liab_cols = [c for c in df_processed.columns if c.endswith(" liabilities")]
        all_risk_cols = [c for c in df_processed.columns if c.endswith(" risk")]
        individual_frag_liabs = sorted([c for c in all_liab_cols if " aa liabilities" in c.lower()])
        individual_frag_risks = sorted([c for c in all_risk_cols if " aa risk" in c.lower()])
        combined_chain_liabs = sorted([c for c in all_liab_cols if c.lower() in ["heavy liabilities", "light liabilities"] and c not in individual_frag_liabs])
        combined_chain_risks = sorted([c for c in all_risk_cols if c.lower() in ["heavy risk", "light risk"] and c not in individual_frag_risks])
        combined_region_liabs = sorted([c for c in all_liab_cols if c not in individual_frag_liabs and c not in combined_chain_liabs and c.lower() != "liabilities risk"])
        combined_region_risks = sorted([c for c in all_risk_cols if c not in individual_frag_risks and c not in combined_chain_risks and c.lower() != "liabilities risk"])
        overall_liab_risk_col = ["Liabilities risk"] if "Liabilities risk" in df_processed.columns else []
    output_cols_ordered = list(dict.fromkeys(
        output_cols_core + final_annotation_cols + final_cdr3_seq_cols + 
        individual_frag_liabs + combined_region_liabs + combined_chain_liabs + 
        individual_frag_risks + combined_region_risks + combined_chain_risks +
        overall_liab_risk_col ))
    output_cols_existing = [c for c in output_cols_ordered if c in df_processed.columns]
    df_out = df_processed.select(output_cols_existing) if output_cols_existing else df_processed
    if not output_cols_existing and df_processed.width > 0: print("⚠️ No columns for final output. Writing entire table.", file=sys.stderr)
    
    try:
        df_out.write_csv(args.output_tsv, separator="\t", quote_style="never")
        print(f"✅ Output table written to {args.output_tsv}")
    except Exception as e: print(f"❌ Error writing output TSV: {e}", file=sys.stderr)

    # --- Generate and Write List of Found Regions (New Output) ---
    if args.output_regions_found:
        found_regions_set = set()
        CANONICAL_REGIONS = ["CDR1", "CDR2", "CDR3", "FR1"]
        # Use cols_for_liability_analysis as it should contain the relevant region sequence columns
        if cols_for_liability_analysis:
            for col_name in cols_for_liability_analysis:
                for region_canonical_name in CANONICAL_REGIONS:
                    # \b ensures whole word match for the region name
                    if re.search(r'\b' + re.escape(region_canonical_name) + r'\b', col_name, re.IGNORECASE):
                        found_regions_set.add(region_canonical_name)
                        break 
            list_of_found_regions = sorted(list(found_regions_set))
        else:
            list_of_found_regions = []
            print("ℹ️ No columns were identified for liability analysis, so the list of found regions will be empty.")
        try:
            with open(args.output_regions_found, 'w') as f:
                json.dump(list_of_found_regions, f, indent=2)
            print(f"✅ List of found regions {list_of_found_regions} written to {args.output_regions_found}")
        except IOError as e:
            print(f"❌ Error writing found regions list to '{args.output_regions_found}': {e}", file=sys.stderr)
    # --- End of Generate and Write List of Found Regions ---

    # Conditional output of label map
    if not has_input_ann_cols:
        _output_final_label_map({}, {}, args.output_label_map, "Empty Label Map")
    elif not CALCULATE_LIABILITIES: 
        _output_final_label_map(initial_region_map, {}, args.output_label_map, "Label Map (Regions Only; No Liabilities Calculated)")
    else: 
        _output_final_label_map(initial_region_map, liability_codes, args.output_label_map, "Final Combined Label Map")

if __name__ == "__main__":
    main()