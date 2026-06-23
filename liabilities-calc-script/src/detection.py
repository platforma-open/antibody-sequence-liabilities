import re

from definitions import Fixability, PerRegionRisk, RiskLevel


# Cysteine position helpers
def _get_expected_cys_positions(region: str, expected_cys_map: dict):
    if region not in expected_cys_map:
        return [], 0, False
    expected_positions = list(expected_cys_map.get(region, []))
    expected_count = 1 if region == "FR1" and expected_positions else len(expected_positions)
    return expected_positions, expected_count, True


def _evaluate_cys_liabilities(seq: str, expected_positions: list, expected_count: int):
    actual_cys_count = seq.count("C")
    allowed_positions = [p for p in expected_positions if -len(seq) <= p < len(seq)]
    missing_cys = False
    if allowed_positions:
        missing_cys = all(seq[p] != "C" for p in allowed_positions)
    extra_cys = False
    if actual_cys_count > expected_count:
        extra_cys = True
    elif missing_cys and actual_cys_count >= expected_count:
        extra_cys = True
    return missing_cys, extra_cys, actual_cys_count


# Liability & Risk Functions
def identify_liabilities(
    seq: str | None,
    region: str,
    active_cdr_defs: dict,
    active_extra_defs: dict,
    active_cys_defs: dict,
    expected_cys_map: dict,
    active_custom_defs: dict | None = None,
) -> str:
    if not seq or not isinstance(seq, str) or not seq.strip():
        return "Unknown"

    # MiXCR emits germline-imputed residues in lowercase; uppercase a local copy so
    # case-sensitive motif/cysteine detection works (does not affect stored sequences).
    seq = seq.upper()

    liabilities_found = []

    # Disqualifying patterns applied to all regions first
    for name, pattern in active_extra_defs.items():
        if re.search(pattern, seq):
            liabilities_found.append(name)

    # Region-specific predefined logic
    if region == "FR1":
        if active_cys_defs:
            expected_positions, expected_count, should_check = _get_expected_cys_positions(region, expected_cys_map)
            if should_check:
                missing_cys, extra_cys, _ = _evaluate_cys_liabilities(seq, expected_positions, expected_count)
                if "Missing Cysteines" in active_cys_defs and missing_cys:
                    liabilities_found.append("Missing Cysteines")
                if "Extra Cysteines" in active_cys_defs and extra_cys:
                    liabilities_found.append("Extra Cysteines")

    elif region.startswith("CDR"):
        # Tryptophan Oxidation: suppress terminal W in CDR3
        w_oxidation_name = "Tryptophan Oxidation (W)"
        if w_oxidation_name in active_cdr_defs:
            pattern_to_use_for_w = r"W(?!$)" if region == "CDR3" else active_cdr_defs[w_oxidation_name][0]
            if re.search(pattern_to_use_for_w, seq):
                liabilities_found.append(w_oxidation_name)

        for name, (pattern, *_rest) in active_cdr_defs.items():
            if name == w_oxidation_name:
                continue
            if re.search(pattern, seq):
                liabilities_found.append(name)

        if active_cys_defs:
            expected_positions, expected_count, should_check = _get_expected_cys_positions(region, expected_cys_map)
            if should_check:
                missing_cys, extra_cys, _ = _evaluate_cys_liabilities(seq, expected_positions, expected_count)
                if "Missing Cysteines" in active_cys_defs and missing_cys:
                    liabilities_found.append("Missing Cysteines")
                if "Extra Cysteines" in active_cys_defs and extra_cys:
                    liabilities_found.append("Extra Cysteines")

    elif region.startswith("FR"):  # FR2, FR3, FR4
        if active_cys_defs:
            expected_positions, expected_count, should_check = _get_expected_cys_positions(region, expected_cys_map)
            if should_check:
                missing_cys, extra_cys, _ = _evaluate_cys_liabilities(seq, expected_positions, expected_count)
                if "Missing Cysteines" in active_cys_defs and missing_cys:
                    liabilities_found.append("Missing Cysteines")
                if "Extra Cysteines" in active_cys_defs and extra_cys:
                    liabilities_found.append("Extra Cysteines")

    # Custom liabilities: only applied if the current region is in their regions list
    if active_custom_defs:
        for name, custom_def in active_custom_defs.items():
            if region in custom_def["regions"]:
                if custom_def["pattern"].search(seq):
                    liabilities_found.append(name)

    return ", ".join(sorted(set(liabilities_found))) if liabilities_found else "None"


def classify_risk(
    liabilities_str: str | None,
    fixability_map: dict[str, Fixability],
    risk_level_map: dict[str, RiskLevel],
) -> PerRegionRisk:
    """Per-region risk: worst riskLevel across all non-disqualifying liabilities
    detected in the region's liabilities column.

    Looks up each liability's risk level in `risk_level_map`, which the caller
    (main.py) builds by merging predefined CDR / Cys liability definitions
    (via _build_risk_level_map) with any custom liabilities. Skips items whose
    fixability is `disqualifying` — those are surfaced via Is Productive = Fail
    and would otherwise force every region to High because identify_liabilities
    appends them to every region's liabilities string.

    The spec (docs/text/work/projects/sequence-liability-fixability-scoring/README.md)
    flagged this at line :126 (Open Questions) as a coin-flip with two defensible
    options: (A) per-region risk reflects fixable + easily_fixable only, or (B)
    per-region risk reflects all liabilities except disqualifying. The implementor
    picked A; R8 (:71), Step 2 (:252-253), Defaults (:304), M1 (:346), and Risks
    (:395) then encoded that choice as binding. User feedback (Slack 2026-05-24)
    confirmed A's counter-argument: per-region Liabilities and Risk visibly
    disagree when a region carries only hard_to_fix / structural matches. This
    function now implements Option B.

    Engineering-only severity is still available in the global "Developability
    risk" column (see scoring.classify_developability_risk), which keeps
    Option-A semantics per R6 (:66) plus a Non-Developable override when
    structural / hard_to_fix matches are present.
    """
    if not liabilities_str or liabilities_str == "None" or not isinstance(liabilities_str, str):
        return "None"
    risk_num = {"None": 0, "Low": 1, "Medium": 2, "High": 3}
    level_to_risk = {v: k for k, v in risk_num.items()}
    current_max = 0
    for item in (n.strip() for n in liabilities_str.split(",")):
        if fixability_map.get(item) == "disqualifying":
            continue
        item_risk = risk_level_map.get(item)
        if not item_risk:
            continue
        level = risk_num.get(item_risk, 0)
        if level > current_max:
            current_max = level
        if current_max == 3:
            return "High"
    return level_to_risk[current_max]


def _build_risk_level_map(active_cdr_defs: dict, active_cys_defs: dict) -> dict[str, RiskLevel]:
    """Build a liability_name → risk_level lookup from active predefined definitions."""
    risk_map: dict[str, RiskLevel] = {}
    for name, (_pat, risk, *_rest) in active_cdr_defs.items():
        risk_map[name] = risk
    for name, (risk, _fix) in active_cys_defs.items():
        risk_map[name] = risk
    return risk_map
