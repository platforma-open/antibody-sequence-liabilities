import re

from definitions import FIXABILITY_WEIGHTS, REGION_WEIGHTS, _ENGINEERING_FIXABILITIES


def _parse_liability_names(liabs_str: str) -> list[str]:
    """Parse comma-separated liability string to a list of names, excluding None/Unknown."""
    if not liabs_str or liabs_str in ("None", "Unknown"):
        return []
    return [name.strip() for name in liabs_str.split(",") if name.strip() not in ("", "None", "Unknown")]


def classify_is_productive(region_to_liabs: dict[str, str], fixability_map: dict[str, str]) -> str:
    """Fail if any disqualifying liability is found in any region."""
    for liabs_str in region_to_liabs.values():
        for name in _parse_liability_names(str(liabs_str) if liabs_str else "None"):
            if fixability_map.get(name) == "disqualifying":
                return "Fail"
    return "Pass"


def classify_structural_risk(region_to_liabs: dict[str, str], fixability_map: dict[str, str]) -> str:
    """Present if any structural or hard_to_fix liability is found in any region."""
    for liabs_str in region_to_liabs.values():
        for name in _parse_liability_names(str(liabs_str) if liabs_str else "None"):
            if fixability_map.get(name) in {"structural", "hard_to_fix"}:
                return "Present"
    return "None"


def classify_developability_risk(
    region_to_liabs: dict[str, str],
    fixability_map: dict[str, str],
    risk_level_map: dict[str, str],
) -> str:
    """Max risk level across fixable and easily_fixable liabilities only."""
    risk_order = {"None": 0, "Low": 1, "Medium": 2, "High": 3}
    level_to_risk = {v: k for k, v in risk_order.items()}
    current_max = 0
    for liabs_str in region_to_liabs.values():
        for name in _parse_liability_names(str(liabs_str) if liabs_str else "None"):
            if fixability_map.get(name) not in _ENGINEERING_FIXABILITIES:
                continue
            risk = risk_level_map.get(name)
            if risk:
                level = risk_order.get(risk, 0)
                if level > current_max:
                    current_max = level
                if current_max == 3:
                    return "High"
    return level_to_risk[current_max]


def compute_developability_score(
    col_to_liabs: dict[str, str],
    fixability_map: dict[str, str],
) -> float:
    """Engineering burden: sum of fixability_weight × region_weight for all non-disqualifying liabilities.

    Keys in col_to_liabs may be pure region names ('CDR3') or full column names
    ('Heavy CDR1 aa liabilities'). The region weight is extracted from the key.
    """
    total = 0.0
    for col_name, liabs_str in col_to_liabs.items():
        region_match = re.search(r"\b(CDR[1-3]|FR[1-4])\b", col_name, re.IGNORECASE)
        region = region_match.group(1).upper() if region_match else col_name
        region_w = REGION_WEIGHTS.get(region, 0.5)
        for name in _parse_liability_names(str(liabs_str) if liabs_str else "None"):
            fix = fixability_map.get(name)
            if fix == "disqualifying":
                continue
            total += FIXABILITY_WEIGHTS.get(fix, 0.0) * region_w
    return total
