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
    "aaSeqFR1": [23],  # Framework 1, position 23
    "aaSeqCDR3": [1],  # CDR3, position 1
}
CYSTEINE_LIABILITIES = {
    "Missing Cysteines": "High",
    "Extra Cysteines": "High",
}

# Expected sequence columns
EXPECTED_COLUMNS = ["CDR3 aa", "CDR1 aa", "CDR2 aa", "FR1 aa"]

# Risk classification function for a single region's liabilities
def classify_risk(liabilities):
    if liabilities == "None":
        return "No risk"
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
    # Check if sequence is empty or only whitespace
    if not sequence or sequence.strip() == "":
        return "None"

    liabilities = []
    if "CDR" in region_name:
        for liability, (pattern, severity) in CDR_LIABILITIES.items():
            if re.search(pattern, sequence):
                liabilities.append(liability)

    expected_positions = EXPECTED_CYSTEINE_POSITIONS.get(region_name, [])
    missing_cysteines = [pos for pos in expected_positions if pos <= len(sequence) and sequence[pos - 1] != "C"]
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

    # Filter out rows where CDR3 aa is empty, contains "*" or "_" or doesn't start with "C"
    df = df.filter(
        (pl.col("CDR3 aa").is_not_null()) &
        (pl.col("CDR3 aa") != "") &
        (pl.col("CDR3 aa").str.starts_with("C")) &
        ~(pl.col("CDR3 aa").str.contains(r"\*")) &
        ~(pl.col("CDR3 aa").str.contains("_"))
    )

    available_columns = [col for col in EXPECTED_COLUMNS if col in df.columns]
    if not available_columns:
        print("No recognized sequence columns found in the input file.")
        return

    # List to keep track of the names of risk columns
    risk_columns = []

    # Process each expected sequence column
    for col in available_columns:
        liability_col = f"{col} liabilities"
        risk_col = f"{col} risk"
        risk_columns.append(risk_col)

        # For columns other than "CDR3 aa", if the sequence is empty, assign "None" for liabilities.
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

    # Create overall "Liabilities risk" column by aggregating risk columns from all regions.
    df = df.with_columns(
        pl.struct(risk_columns).map_elements(overall_risk_func, return_dtype=str).alias("Liabilities risk")
    )

    # Select only the desired output columns:
    # "Sample", "clonotype key", "CDR3 aa" and all columns ending with "liabilities" or "risk"
    output_columns = [
        col for col in df.columns
        if col in ["Sample", "Clonotype key", "CDR3 aa"] or col.endswith("liabilities") or col.endswith("risk")
    ]
    if "Liabilities risk" not in output_columns:
        output_columns.append("Liabilities risk")

    df = df.select(output_columns)
    df.write_csv(args.output_tsv, separator="\t", quote_style="never")

if __name__ == "__main__":
    main()
