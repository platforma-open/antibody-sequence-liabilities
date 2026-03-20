# Liability Definitions
# Format: name → (pattern, risk_level, fixability)
ORIG_CDR_LIABILITIES = {
    "Deamidation (N[GS])": (r"N[GS]", "High", "fixable"),
    "Fragmentation (DP)": (r"DP", "High", "fixable"),
    "Isomerization (D[DGHST])": (r"D[DGHST]", "High", "fixable"),
    "N-linked Glycosylation (N[^P][ST])": (r"N[^P][ST]", "High", "fixable"),
    "Deamidation (N[AHNT])": (r"N[AHNT]", "Medium", "easily_fixable"),
    "Hydrolysis (NP)": (r"NP", "Medium", "fixable"),
    "Fragmentation (TS)": (r"TS", "Medium", "fixable"),
    "Tryptophan Oxidation (W)": (r"W", "Medium", "easily_fixable"),
    "Methionine Oxidation (M)": (r"M", "Medium", "easily_fixable"),
    "Deamidation ([STK]N)": (r"[STK]N", "Low", "easily_fixable"),
    "Integrin binding": (r"RGD|RYD|KGD|NGR|LDV|DGE|GPR", "Low", "easily_fixable"),
}
# Format: name → pattern  (fixability is always "disqualifying")
ORIG_EXTRA_PATTERNS = {
    "Contains stop codon": r"\*",
    "Out of frame": r"_",
}
# Format: name → (risk_level, fixability)
ORIG_CYS_LIABILITIES = {
    "Missing Cysteines": ("High", "structural"),
    "Extra Cysteines": ("High", "hard_to_fix"),
}

# Unified fixability lookup for all predefined liabilities
FIXABILITY_MAP: dict[str, str] = {name: fixability for name, (_pat, _risk, fixability) in ORIG_CDR_LIABILITIES.items()}
FIXABILITY_MAP.update({name: "disqualifying" for name in ORIG_EXTRA_PATTERNS})
FIXABILITY_MAP.update({name: fixability for name, (_risk, fixability) in ORIG_CYS_LIABILITIES.items()})

# Engineering burden weights (used in compute_developability_score)
FIXABILITY_WEIGHTS: dict[str, float] = {
    "easily_fixable": 1.0,
    "fixable": 3.0,
    "hard_to_fix": 8.0,
    "structural": 20.0,
    "disqualifying": 0.0,
}
REGION_WEIGHTS: dict[str, float] = {
    "CDR3": 1.5,
    "CDR1": 1.2,
    "CDR2": 1.2,
    "FR1": 1.0,
    "FR2": 0.5,
    "FR3": 0.5,
    "FR4": 0.3,
}

_ENGINEERING_FIXABILITIES = {"fixable", "easily_fixable"}
# Usage of EXPECTED_CYS_BASE will have to be modified if you add more than one nucleotide coordinate
# Coordinates are added in 0-based index
EXPECTED_CYS_BASE = {"FR1": [21, 22], "FR2": [], "FR3": [], "CDR1": [], "CDR2": [], "CDR3": [0]}
FR1_SPECIFIC_LIABILITIES = {"Missing Cysteines", "Extra Cysteines"}
REGION_ORDER_MAP = {"FR1": 1, "CDR1": 2, "CDR2": 3, "CDR3": 4, "FR2": 5, "FR3": 6, "FR4": 7}  # For sorting summary


def get_active_liability_definitions(user_requested_set: set):
    if not user_requested_set:
        return {}, {}, {}, {}
    active_cdr_l = {n: d for n, d in ORIG_CDR_LIABILITIES.items() if n in user_requested_set}
    active_extra_p = {n: p for n, p in ORIG_EXTRA_PATTERNS.items() if n in user_requested_set}
    active_cys_l = {n: d for n, d in ORIG_CYS_LIABILITIES.items() if n in user_requested_set}
    # active_liability_regex: name → pattern (CDR patterns + extra patterns)
    active_liability_r = {**{nm: details[0] for nm, details in active_cdr_l.items()}, **active_extra_p}
    return active_cdr_l, active_extra_p, active_cys_l, active_liability_r


def build_expected_cys_map(numbering_schema: str | None) -> dict:
    expected = {k: list(v) for k, v in EXPECTED_CYS_BASE.items()}
    if not numbering_schema:
        return expected
    schema = str(numbering_schema).strip().lower()
    schema_fr3_map = {
        "imgt": [-1],
        "kabat": [-3],
        "chothia": [-3],
    }
    if schema in schema_fr3_map:
        expected["FR3"] = schema_fr3_map[schema]
        expected["CDR3"] = []
    return expected
