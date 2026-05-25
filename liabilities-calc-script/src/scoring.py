import re
from typing import Literal

from definitions import (
    _ENGINEERING_FIXABILITIES,
    FIXABILITY_WEIGHTS,
    REGION_WEIGHTS,
    DevelopabilityRisk,
    Fixability,
    RiskLevel,
)


def _parse_liability_names(liabs_str: str | None) -> list[str]:
    """Parse comma-separated liability string to a list of names, excluding None/Unknown."""
    if not liabs_str or liabs_str in ("None", "Unknown"):
        return []
    return [name.strip() for name in liabs_str.split(",") if name.strip() not in ("", "None", "Unknown")]


def classify_is_productive(
    region_to_liabs: dict[str, str | None], fixability_map: dict[str, Fixability]
) -> Literal["Pass", "Fail"]:
    """Fail if any disqualifying liability is found in any region."""
    for liabs_str in region_to_liabs.values():
        for name in _parse_liability_names(str(liabs_str) if liabs_str else "None"):
            if fixability_map.get(name) == "disqualifying":
                return "Fail"
    return "Pass"


def classify_structural_risk(
    region_to_liabs: dict[str, str | None], fixability_map: dict[str, Fixability]
) -> Literal["None", "Present"]:
    """Present if any structural or hard_to_fix liability is found in any region."""
    for liabs_str in region_to_liabs.values():
        for name in _parse_liability_names(str(liabs_str) if liabs_str else "None"):
            if fixability_map.get(name) in {"structural", "hard_to_fix"}:
                return "Present"
    return "None"


def classify_developability_risk(
    region_to_liabs: dict[str, str | None],
    fixability_map: dict[str, Fixability],
    risk_level_map: dict[str, RiskLevel],
) -> DevelopabilityRisk:
    """Developability risk with two structural overrides.

    Precedence (worst wins):
      1. structural   → 'Non-Developable' (requires scaffold redesign;
                       canonical example: Missing Cysteines)
      2. hard_to_fix  → 'Very High'       (harder than routine engineering
                       but not non-developable; e.g. Extra Cysteines)
      3. fixable / easily_fixable → max risk level across those liabilities
                       only: None / Low / Medium / High

    The two overrides fold the Structural liabilities signal into this column
    so a single column carries both engineering severity and structural
    disqualification — readers don't need to cross-reference Structural
    liabilities to see why a candidate is excluded.

    Spec deviation: R6 (docs/text/work/projects/sequence-liability-fixability-scoring/README.md:66)
    defined this column as engineering-only with values None/Low/Medium/High.
    Per 2026-05-25 feedback (continuation of the 2026-05-24 Slack thread),
    the scale now extends to {Very High, Non-Developable} at the top.
    """
    risk_order = {"None": 0, "Low": 1, "Medium": 2, "High": 3}
    level_to_risk = {v: k for k, v in risk_order.items()}
    has_hard_to_fix = False
    current_max = 0
    for liabs_str in region_to_liabs.values():
        for name in _parse_liability_names(str(liabs_str) if liabs_str else "None"):
            fix = fixability_map.get(name)
            # Structural is the harshest override — short-circuit immediately
            # because no later region can change the answer.
            if fix == "structural":
                return "Non-Developable"
            if fix == "hard_to_fix":
                has_hard_to_fix = True
                continue  # keep scanning in case a later region has structural
            if fix not in _ENGINEERING_FIXABILITIES:
                continue
            risk = risk_level_map.get(name)
            if risk:
                level = risk_order.get(risk, 0)
                if level > current_max:
                    current_max = level
    if has_hard_to_fix:
        return "Very High"
    return level_to_risk[current_max]


def compute_developability_score(
    col_to_liabs: dict[str, str | None],
    fixability_map: dict[str, Fixability],
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
