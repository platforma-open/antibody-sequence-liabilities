import polars as pl
import re
import argparse

# Define CDR-specific liabilities (motifs & severity)
CDR_LIABILITIES = {
    "Deamidation (N[GS])": (r"N[GS]", "High"),
    "Fragmentation (DP)": (r"DP", "High"),
    "Isomerization (D[DGHST])": (r"D[DGHST]", "High"),
    "N-linked Glycosylation (N[^P][ST])": (r"N[^P][ST]", "High"),
    "Deamidation (N[AHNT])": (r"N[AHNT]", "Medium"),
    "Hydrolysis (NP)": (r"NP", "Medium"),
    "Fragmentation (TS)": (r"TS", "Medium"),
    "Tryptophan Oxidation (W)": (r"W", "Medium"),
    "Methionine Oxidation (M)": (r"M", "Medium"),
    "Deamidation ([STK]N)": (r"[STK]N", "Low"),
}

# Define cysteine checks for all sequences (with high severity)
EXPECTED_CYSTEINE_POSITIONS = {
    "FR1": [22],  # Framework 1, position 23
    "CDR3": [1],  # CDR3, position 1
}
CYSTEINE_LIABILITIES = {
    "Missing Cysteines": "High",
    "Extra Cysteines": "High",
}

# Risk classification function for a single region's liabilities
def classify_risk(liabilities):
    if liabilities == "None":
        return "None"
    liability_list = liabilities.split(", ")
    if any(liab in CYSTEINE_LIABILITIES and CYSTEINE_LIABILITIES[liab] == "High" for liab in liability_list):
        return "High"
    elif any(liab in CDR_LIABILITIES and CDR_LIABILITIES[liab][1] == "High" for liab in liability_list):
        return "High"
    elif any(liab in CDR_LIABILITIES and CDR_LIABILITIES[liab][1] == "Medium" for liab in liability_list):
        return "Medium"
    elif any(liab in CDR_LIABILITIES and CDR_LIABILITIES[liab][1] == "Low" for liab in liability_list):
        return "Low"
    return "None"

# Liability detection function for a given sequence and region name.
# If no liabilities are found, it returns "None".
def identify_liabilities(sequence, region_name):
    if not sequence or sequence.strip() == "":
        return "None"

    liabilities = []
    # Apply CDR-specific regex if the column name indicates a CDR region.
    if any(sub in region_name for sub in ["CDR"]):
        for liability, (pattern, severity) in CDR_LIABILITIES.items():
            # For Tryptophan Oxidation in CDR3, ignore the last tryptophan.
            if liability == "Tryptophan Oxidation (W)" and "CDR3" in region_name:
                indices = [m.start() for m in re.finditer(r'W', sequence)]
                if any(idx < len(sequence) - 1 for idx in indices):
                    liabilities.append(liability)
            else:
                if re.search(pattern, sequence):
                    liabilities.append(liability)

    # Perform cysteine checks using expected positions if available.
    if "CDR3" in region_name:
        expected_positions = EXPECTED_CYSTEINE_POSITIONS.get("CDR3", [])
    elif "FR1" in region_name:
        expected_positions = EXPECTED_CYSTEINE_POSITIONS.get("FR1", [])
    else:
        expected_positions = []

    # Check for missing cysteines
    if expected_positions:
        missing_cysteines = sequence.count("C") < len(expected_positions)
    else:
        missing_cysteines = False
    # Check for extra cysteines
    extra_cysteines = sequence.count("C") - len(expected_positions)

    if missing_cysteines:
        liabilities.append("Missing Cysteines")
    if extra_cysteines > 0:
        liabilities.append("Extra Cysteines")

    return ", ".join(liabilities) if liabilities else "None"

# Overall risk function that aggregates risk values from all risk columns.
def overall_risk_func(risk_values):
    risks = list(risk_values.values())
    if "High" in risks:
        return "High"
    elif "Medium" in risks:
        return "Medium"
    elif "Low" in risks:
        return "Low"
    else:
        return "None"

def main():
    parser = argparse.ArgumentParser(description="Analyze antibody sequence liabilities.")
    parser.add_argument("input_tsv", help="Path to the input TSV file containing antibody sequences.")
    parser.add_argument("output_tsv", help="Path to save the processed TSV with liability reports.")
    args = parser.parse_args()

    df = pl.read_csv(args.input_tsv, separator="\t", infer_schema_length=1000, ignore_errors=True)

    # Define keywords to search in column names.
    KEYWORDS = ["CDR3", "CDR1", "CDR2", "FR1"]

    # Identify columns whose names contain any of the keywords.
    available_columns = [col for col in df.columns if any(keyword in col for keyword in KEYWORDS)]
    if not available_columns:
        print("No recognized sequence columns found in the input file.")
        return

    # filter non-productive sequences
    for col in available_columns:
    # Build the common filters that all columns need.
        base_filter = (
            (pl.col(col).is_not_null()) &
            (pl.col(col) != "") &
            ~(pl.col(col).str.contains(r"\*")) &
            ~(pl.col(col).str.contains("_"))
        )
        
        # For columns containing "CDR3", add the check that sequences start with "C".
        if "CDR3" in col:
            df = df.filter(base_filter & (pl.col(col).str.starts_with("C")))
        else:
            df = df.filter(base_filter)
    
    # Compute liabilities and risk columns for each identified sequence column.
    for col in available_columns:
        liability_col = f"{col} liabilities"
        risk_col = f"{col} risk"
        df = df.with_columns(
            pl.col(col)
            .cast(str)
            .map_elements(lambda seq: identify_liabilities(seq, col) if (seq and seq.strip() != "") else "None", return_dtype=str)
            .alias(liability_col)
        )
        df = df.with_columns(
            pl.col(liability_col)
            .map_elements(classify_risk, return_dtype=str)
            .alias(risk_col)
        )

    # Create overall "Liabilities risk" column by aggregating risk columns.
    risk_colnames = [col for col in df.columns if col.endswith(" risk")]
    df = df.with_columns(
        pl.struct(risk_colnames).map_elements(overall_risk_func, return_dtype=str).alias("Liabilities risk")
    )

    # --- Combine Heavy/Light results for risk columns ---
    heavy_risk = {}
    light_risk = {}
    for col in df.columns:
        if col.startswith("Heavy ") and col.endswith(" risk"):
            base = col[len("Heavy "): -len(" risk")]
            heavy_risk[base] = col
        elif col.startswith("Light ") and col.endswith(" risk"):
            base = col[len("Light "): -len(" risk")]
            light_risk[base] = col
    for base in set(heavy_risk.keys()).intersection(light_risk.keys()):
        combined_name = f"{base} risk"
        df = df.with_columns(
            pl.concat_str([
                pl.lit("Heavy: "), pl.col(heavy_risk[base]),
                pl.lit(" | Light: "), pl.col(light_risk[base])
            ]).alias(combined_name)
        )
        df = df.drop(heavy_risk[base]).drop(light_risk[base])

    # --- Combine Heavy/Light results for liabilities columns ---
    heavy_liab = {}
    light_liab = {}
    for col in df.columns:
        if col.startswith("Heavy ") and col.endswith(" liabilities"):
            base = col[len("Heavy "): -len(" liabilities")]
            heavy_liab[base] = col
        elif col.startswith("Light ") and col.endswith(" liabilities"):
            base = col[len("Light "): -len(" liabilities")]
            light_liab[base] = col
    for base in set(heavy_liab.keys()).intersection(light_liab.keys()):
        combined_name = f"{base} liabilities"
        df = df.with_columns(
            pl.concat_str([
                pl.lit("Heavy: "), pl.col(heavy_liab[base]),
                pl.lit(" | Light: "), pl.col(light_liab[base])
            ]).alias(combined_name)
        )
        df = df.drop(heavy_liab[base]).drop(light_liab[base])
    # --- End heavy/light combination ---

    # --- Finalize output ---
    # Keep identifier columns ("Sample", "Clonotype key", "Clone label"),
    # overall "Liabilities risk", and computed risk or liabilities columns.
    final_columns = [col for col in df.columns if col in ["Heavy CDR3 aa Primary", "Light CDR3 aa Primary", "CDR3 aa", "Heavy CDR3 aa", "Light CDR3 aa",
                                                          "Clonotype key", "Clone label", "Liabilities risk"] or col.endswith("risk") or col.endswith("liabilities")]
    df = df.select(final_columns)

    # Rename computed columns:
    # For instance, "CDR3 aa Primary liabilities" -> "CDR3 liabilities" and similarly for risk.
    rename_mapping = {}
    for col in df.columns:
        new_name = col
        if "aa Primary liabilities" in col:
            new_name = new_name.replace("aa Primary liabilities", "liabilities")
        if "aa Primary risk" in col:
            new_name = new_name.replace("aa Primary risk", "risk")
        if "aa" in col:
            new_name = new_name.replace(" aa ", " ")
            
        rename_mapping[col] = new_name
    df = df.rename(rename_mapping)

    df.write_csv(args.output_tsv, separator="\t", quote_style="never")

if __name__ == "__main__":
    main()
