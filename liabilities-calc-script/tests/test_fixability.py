"""Unit tests for the fixability taxonomy functions in main.py.

Tests verify the key requirements from the fixability-aware scoring ticket:
- Met/Trp oxidation-only candidates pass Is Productive and Structural liabilities
  (they were previously false negatives in Lead Selection's default ["None"] filter)
- Stop codons and out-of-frame sequences fail Is Productive
- Missing/extra cysteines appear in Structural liabilities, not Developability risk
- Developability risk correctly reflects the actual riskLevel of fixable/easily_fixable liabilities
- Custom liabilities are region-targeted and participate in all classification steps
"""
import main

# ── Shared maps built from all predefined liability definitions ───────────────

FULL_FM = main._get_fixability_map(
    main.ORIG_CDR_LIABILITIES,
    main.ORIG_EXTRA_PATTERNS,
    main.ORIG_CYS_LIABILITIES,
)

FULL_RLM = main._get_risk_level_map(
    main.ORIG_CDR_LIABILITIES,
    main.ORIG_EXTRA_PATTERNS,
    main.ORIG_CYS_LIABILITIES,
)


# ── classify_is_productive ────────────────────────────────────────────────────


class TestClassifyIsProductive:
    def test_none_input_is_pass(self):
        assert main.classify_is_productive("None", FULL_FM) == "Pass"

    def test_empty_input_is_pass(self):
        assert main.classify_is_productive("", FULL_FM) == "Pass"

    def test_stop_codon_is_fail(self):
        assert main.classify_is_productive("Contains stop codon", FULL_FM) == "Fail"

    def test_out_of_frame_is_fail(self):
        assert main.classify_is_productive("Out of frame", FULL_FM) == "Fail"

    def test_met_oxidation_is_pass(self):
        # Key ticket requirement: easily_fixable liabilities must not disqualify candidates
        assert main.classify_is_productive("Methionine Oxidation (M)", FULL_FM) == "Pass"

    def test_trp_oxidation_is_pass(self):
        assert main.classify_is_productive("Tryptophan Oxidation (W)", FULL_FM) == "Pass"

    def test_missing_cys_is_pass(self):
        # Structural liabilities surface in Structural liabilities column, not here
        assert main.classify_is_productive("Missing Cysteines", FULL_FM) == "Pass"

    def test_stop_codon_combined_with_fixable_is_fail(self):
        assert main.classify_is_productive(
            "Contains stop codon, Methionine Oxidation (M)", FULL_FM
        ) == "Fail"


# Backward-compat alias — classify_sequence_quality must still work
class TestClassifySequenceQuality:
    def test_none_input_is_pass(self):
        assert main.classify_sequence_quality("None", FULL_FM) == "Pass"

    def test_stop_codon_is_fail(self):
        assert main.classify_sequence_quality("Contains stop codon", FULL_FM) == "Fail"

    def test_met_oxidation_is_pass(self):
        assert main.classify_sequence_quality("Methionine Oxidation (M)", FULL_FM) == "Pass"


# ── classify_structural_risk ──────────────────────────────────────────────────


class TestClassifyStructuralRisk:
    def test_none_input_is_none(self):
        assert main.classify_structural_risk("None", FULL_FM) == "None"

    def test_missing_cys_is_present(self):
        # Missing Cysteines is structural → Present
        assert main.classify_structural_risk("Missing Cysteines", FULL_FM) == "Present"

    def test_extra_cys_is_present(self):
        # Extra Cysteines is hard_to_fix → Present
        assert main.classify_structural_risk("Extra Cysteines", FULL_FM) == "Present"

    def test_met_oxidation_is_none(self):
        assert main.classify_structural_risk("Methionine Oxidation (M)", FULL_FM) == "None"

    def test_stop_codon_is_none(self):
        # Disqualifying liabilities surface in Is Productive, not Structural liabilities
        assert main.classify_structural_risk("Contains stop codon", FULL_FM) == "None"

    def test_cys_combined_with_fixable_is_present(self):
        assert main.classify_structural_risk(
            "Missing Cysteines, Methionine Oxidation (M)", FULL_FM
        ) == "Present"

    def test_deamidation_ngs_is_none(self):
        # Deamidation (N[GS]) is fixable, not structural/hard_to_fix → None
        assert main.classify_structural_risk("Deamidation (N[GS])", FULL_FM) == "None"


# ── classify_developability_risk ──────────────────────────────────────────────


class TestClassifyDevelopabilityRisk:
    def test_none_input_is_none(self):
        assert main.classify_developability_risk("None", FULL_FM, FULL_RLM) == "None"

    def test_easily_fixable_medium_risk_returns_medium(self):
        # Methionine Oxidation (M): easily_fixable + riskLevel Medium → "Medium"
        assert main.classify_developability_risk("Methionine Oxidation (M)", FULL_FM, FULL_RLM) == "Medium"
        # Tryptophan Oxidation (W): easily_fixable + riskLevel Medium → "Medium"
        assert main.classify_developability_risk("Tryptophan Oxidation (W)", FULL_FM, FULL_RLM) == "Medium"

    def test_easily_fixable_low_risk_returns_low(self):
        # Deamidation ([STK]N): easily_fixable + riskLevel Low → "Low"
        assert main.classify_developability_risk("Deamidation ([STK]N)", FULL_FM, FULL_RLM) == "Low"

    def test_fixable_medium_risk_returns_medium(self):
        # Hydrolysis (NP): fixable + riskLevel Medium → "Medium"
        assert main.classify_developability_risk("Hydrolysis (NP)", FULL_FM, FULL_RLM) == "Medium"

    def test_fixable_high_risk_returns_high(self):
        # Deamidation (N[GS]): fixable + riskLevel High → "High"
        assert main.classify_developability_risk("Deamidation (N[GS])", FULL_FM, FULL_RLM) == "High"
        # Fragmentation (DP): fixable + riskLevel High → "High"
        assert main.classify_developability_risk("Fragmentation (DP)", FULL_FM, FULL_RLM) == "High"

    def test_hard_to_fix_is_none(self):
        # Extra Cysteines: hard_to_fix → excluded from Developability risk → "None"
        assert main.classify_developability_risk("Extra Cysteines", FULL_FM, FULL_RLM) == "None"

    def test_structural_not_counted(self):
        # Missing Cysteines: structural → excluded from Developability risk → "None"
        assert main.classify_developability_risk("Missing Cysteines", FULL_FM, FULL_RLM) == "None"

    def test_disqualifying_not_counted(self):
        assert main.classify_developability_risk("Contains stop codon", FULL_FM, FULL_RLM) == "None"

    def test_mixed_levels_returns_max(self):
        # Met(Medium) + N[GS](High) → max is "High"
        assert main.classify_developability_risk(
            "Methionine Oxidation (M), Deamidation (N[GS])", FULL_FM, FULL_RLM
        ) == "High"
        # Met(Medium) + Hydrolysis(Medium) → "Medium"
        assert main.classify_developability_risk(
            "Methionine Oxidation (M), Hydrolysis (NP)", FULL_FM, FULL_RLM
        ) == "Medium"

    def test_hard_to_fix_excluded_max_from_fixable(self):
        # Extra Cys(hard_to_fix, excluded) + Hydrolysis(Medium) → "Medium"
        assert main.classify_developability_risk(
            "Extra Cysteines, Hydrolysis (NP)", FULL_FM, FULL_RLM
        ) == "Medium"


# ── compute_developability_score ──────────────────────────────────────────────


class TestComputeDevelopabilityScore:
    def test_empty_row_is_zero(self):
        assert main.compute_developability_score({}, FULL_FM) == 0.0

    def test_none_value_is_zero(self):
        assert main.compute_developability_score({"CDR3 aa liabilities": "None"}, FULL_FM) == 0.0

    def test_easily_fixable_in_cdr3_uses_region_weight(self):
        # easily_fixable weight=1, CDR3 region weight=1.5 → 1 * 1.5 = 1.5
        score = main.compute_developability_score(
            {"CDR3 aa liabilities": "Methionine Oxidation (M)"}, FULL_FM
        )
        assert score == 1.5

    def test_fixable_in_fr1_uses_region_weight(self):
        # fixable weight=3, FR1 region weight=1.0 → 3 * 1.0 = 3.0
        score = main.compute_developability_score(
            {"FR1 aa liabilities": "Hydrolysis (NP)"}, FULL_FM
        )
        assert score == 3.0

    def test_hard_to_fix_uses_weight_8(self):
        # Extra Cysteines: hard_to_fix weight=8, CDR3 region weight=1.5 → 8 * 1.5 = 12.0
        score = main.compute_developability_score(
            {"CDR3 aa liabilities": "Extra Cysteines"}, FULL_FM
        )
        assert score == 12.0

    def test_structural_uses_weight_20(self):
        # structural weight=20, CDR3 region weight=1.5 → 20 * 1.5 = 30.0
        score = main.compute_developability_score(
            {"CDR3 aa liabilities": "Missing Cysteines"}, FULL_FM
        )
        assert score == 30.0

    def test_disqualifying_contributes_zero(self):
        # disqualifying weight=0
        score = main.compute_developability_score(
            {"CDR3 aa liabilities": "Contains stop codon"}, FULL_FM
        )
        assert score == 0.0

    def test_multiple_regions_summed(self):
        # CDR3: Met oxidation (easily_fixable=1 × 1.5) + CDR1: Hydrolysis (fixable=3 × 1.2) = 1.5 + 3.6 = 5.1
        score = main.compute_developability_score(
            {
                "CDR3 aa liabilities": "Methionine Oxidation (M)",
                "CDR1 aa liabilities": "Hydrolysis (NP)",
            },
            FULL_FM,
        )
        assert abs(score - 5.1) < 1e-9


# ── custom liabilities ────────────────────────────────────────────────────────


class TestCustomLiabilities:
    _DG_CDR12 = {
        "name": "Test DG Pattern",
        "pattern": r"DG",
        "riskLevel": "Medium",
        "fixability": "fixable",
        "regions": ["CDR1", "CDR2"],
    }

    def test_applied_to_matching_region(self):
        liabilities = main.identify_liabilities(
            "ADGSS", "CDR1", {}, {}, {}, {}, active_custom_defs=[self._DG_CDR12]
        )
        assert "Test DG Pattern" in liabilities

    def test_not_applied_to_excluded_region(self):
        liabilities = main.identify_liabilities(
            "ADGSS", "CDR3", {}, {}, {}, {}, active_custom_defs=[self._DG_CDR12]
        )
        assert liabilities == "None"

    def test_included_in_fixability_map(self):
        fm = main._get_fixability_map({}, {}, {})
        fm["Test DG Pattern"] = self._DG_CDR12["fixability"]
        rlm = main._get_risk_level_map({}, {}, {})
        rlm["Test DG Pattern"] = self._DG_CDR12["riskLevel"]
        assert main.classify_developability_risk("Test DG Pattern", fm, rlm) == "Medium"
        assert main.classify_is_productive("Test DG Pattern", fm) == "Pass"
        assert main.classify_structural_risk("Test DG Pattern", fm) == "None"

    def test_hard_to_fix_custom_contributes_high_risk(self):
        hard_def = {**self._DG_CDR12, "fixability": "hard_to_fix", "regions": ["CDR3"]}
        liabilities = main.identify_liabilities(
            "ADGSS", "CDR3", {}, {}, {}, {}, active_custom_defs=[hard_def]
        )
        fm = main._get_fixability_map({}, {}, {})
        fm[hard_def["name"]] = "hard_to_fix"
        rlm = main._get_risk_level_map({}, {}, {})
        rlm[hard_def["name"]] = hard_def["riskLevel"]
        # hard_to_fix goes to Structural liabilities; Developability risk returns None
        assert main.classify_developability_risk(liabilities, fm, rlm) == "None"

    def test_easily_fixable_custom_returns_actual_risk_level(self):
        easy_def = {**self._DG_CDR12, "fixability": "easily_fixable", "riskLevel": "Medium", "regions": ["CDR1"]}
        liabilities = main.identify_liabilities(
            "ADGSS", "CDR1", {}, {}, {}, {}, active_custom_defs=[easy_def]
        )
        fm = main._get_fixability_map({}, {}, {})
        fm[easy_def["name"]] = "easily_fixable"
        rlm = main._get_risk_level_map({}, {}, {})
        rlm[easy_def["name"]] = easy_def["riskLevel"]
        # easily_fixable with Medium riskLevel → "Medium"
        assert main.classify_developability_risk(liabilities, fm, rlm) == "Medium"
        # easily_fixable weight=1, CDR1 region weight=1.2 → 1.2
        score = main.compute_developability_score({"CDR1 aa liabilities": liabilities}, fm)
        assert abs(score - 1.2) < 1e-9

    def test_no_match_when_pattern_does_not_match(self):
        liabilities = main.identify_liabilities(
            "ACGSS", "CDR1", {}, {}, {}, {}, active_custom_defs=[self._DG_CDR12]
        )
        assert "Test DG Pattern" not in liabilities


# ── integration: key ticket requirement (Lead Selection false negatives) ──────


class TestLeadSelectionFalseNegatives:
    """The ticket motivation: candidates with only Met/Trp oxidation were discarded
    by Lead Selection's default filter ["None"] on the old single "Liabilities risk" column.
    With the taxonomy split they now pass both Is Productive and Structural liabilities,
    so the default filter lets them through.
    """

    def test_met_oxidation_only_passes_default_filters(self):
        liabilities = "Methionine Oxidation (M)"
        assert main.classify_is_productive(liabilities, FULL_FM) == "Pass"
        assert main.classify_structural_risk(liabilities, FULL_FM) == "None"

    def test_trp_oxidation_only_passes_default_filters(self):
        liabilities = "Tryptophan Oxidation (W)"
        assert main.classify_is_productive(liabilities, FULL_FM) == "Pass"
        assert main.classify_structural_risk(liabilities, FULL_FM) == "None"

    def test_missing_cys_caught_by_structural_filter(self):
        liabilities = "Missing Cysteines"
        assert main.classify_structural_risk(liabilities, FULL_FM) == "Present"
        assert main.classify_developability_risk(liabilities, FULL_FM, FULL_RLM) == "None"

    def test_extra_cys_caught_by_structural_filter(self):
        # Extra Cysteines is hard_to_fix → Present in Structural liabilities, None in Developability risk
        liabilities = "Extra Cysteines"
        assert main.classify_structural_risk(liabilities, FULL_FM) == "Present"
        assert main.classify_developability_risk(liabilities, FULL_FM, FULL_RLM) == "None"

    def test_deamidation_ngs_now_in_developability_risk(self):
        # Deamidation (N[GS]) is fixable (High) → surfaces in Developability risk, not Structural liabilities
        liabilities = "Deamidation (N[GS])"
        assert main.classify_structural_risk(liabilities, FULL_FM) == "None"
        assert main.classify_developability_risk(liabilities, FULL_FM, FULL_RLM) == "High"

    def test_stop_codon_still_excluded_by_is_productive(self):
        liabilities = "Contains stop codon"
        assert main.classify_is_productive(liabilities, FULL_FM) == "Fail"
