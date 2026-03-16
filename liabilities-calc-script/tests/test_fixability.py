"""Unit tests for the fixability taxonomy functions in main.py.

Tests verify the key requirements from the fixability-aware scoring ticket:
- Met/Trp oxidation-only candidates pass Sequence quality and Structural liabilities
  (they were previously false negatives in Lead Selection's default [\"None\"] filter)
- Stop codons and out-of-frame sequences fail Sequence quality
- Missing/extra cysteines appear in Structural liabilities, not Engineering liabilities risk
- Engineering liabilities risk correctly reflects hard_to_fix > fixable > easily_fixable
- Custom liabilities are region-targeted and participate in all classification steps
"""
import main

# ── Shared fixability map built from all predefined liability definitions ─────

FULL_FM = main._get_fixability_map(
    main.ORIG_CDR_LIABILITIES,
    main.ORIG_EXTRA_PATTERNS,
    main.ORIG_CYS_LIABILITIES,
)


# ── classify_sequence_quality ─────────────────────────────────────────────────


class TestClassifySequenceQuality:
    def test_none_input_is_pass(self):
        assert main.classify_sequence_quality("None", FULL_FM) == "Pass"

    def test_empty_input_is_pass(self):
        assert main.classify_sequence_quality("", FULL_FM) == "Pass"

    def test_stop_codon_is_fail(self):
        assert main.classify_sequence_quality("Contains stop codon", FULL_FM) == "Fail"

    def test_out_of_frame_is_fail(self):
        assert main.classify_sequence_quality("Out of frame", FULL_FM) == "Fail"

    def test_met_oxidation_is_pass(self):
        # Key ticket requirement: easily_fixable liabilities must not disqualify candidates
        assert main.classify_sequence_quality("Methionine Oxidation (M)", FULL_FM) == "Pass"

    def test_trp_oxidation_is_pass(self):
        assert main.classify_sequence_quality("Tryptophan Oxidation (W)", FULL_FM) == "Pass"

    def test_missing_cys_is_pass(self):
        # Structural liabilities surface in Structural liabilities column, not here
        assert main.classify_sequence_quality("Missing Cysteines", FULL_FM) == "Pass"

    def test_stop_codon_combined_with_fixable_is_fail(self):
        assert main.classify_sequence_quality(
            "Contains stop codon, Methionine Oxidation (M)", FULL_FM
        ) == "Fail"


# ── classify_structural_risk ──────────────────────────────────────────────────


class TestClassifyStructuralRisk:
    def test_none_input_is_none(self):
        assert main.classify_structural_risk("None", FULL_FM) == "None"

    def test_missing_cys_is_present(self):
        assert main.classify_structural_risk("Missing Cysteines", FULL_FM) == "Present"

    def test_extra_cys_is_present(self):
        assert main.classify_structural_risk("Extra Cysteines", FULL_FM) == "Present"

    def test_met_oxidation_is_none(self):
        assert main.classify_structural_risk("Methionine Oxidation (M)", FULL_FM) == "None"

    def test_stop_codon_is_none(self):
        # Disqualifying liabilities surface in Sequence quality, not Structural liabilities
        assert main.classify_structural_risk("Contains stop codon", FULL_FM) == "None"

    def test_cys_combined_with_fixable_is_present(self):
        assert main.classify_structural_risk(
            "Missing Cysteines, Methionine Oxidation (M)", FULL_FM
        ) == "Present"


# ── classify_engineering_risk ─────────────────────────────────────────────────


class TestClassifyEngineeringRisk:
    def test_none_input_is_none(self):
        assert main.classify_engineering_risk("None", FULL_FM) == "None"

    def test_easily_fixable_is_low(self):
        assert main.classify_engineering_risk("Methionine Oxidation (M)", FULL_FM) == "Low"
        assert main.classify_engineering_risk("Tryptophan Oxidation (W)", FULL_FM) == "Low"

    def test_fixable_is_medium(self):
        assert main.classify_engineering_risk("Hydrolysis (NP)", FULL_FM) == "Medium"

    def test_hard_to_fix_is_high(self):
        assert main.classify_engineering_risk("Deamidation (N[GS])", FULL_FM) == "High"

    def test_mixed_levels_returns_max(self):
        assert main.classify_engineering_risk(
            "Methionine Oxidation (M), Deamidation (N[GS])", FULL_FM
        ) == "High"
        assert main.classify_engineering_risk(
            "Methionine Oxidation (M), Hydrolysis (NP)", FULL_FM
        ) == "Medium"

    def test_structural_not_counted(self):
        # Missing/extra cysteines have no engineering risk level
        assert main.classify_engineering_risk("Missing Cysteines", FULL_FM) == "None"

    def test_disqualifying_not_counted(self):
        assert main.classify_engineering_risk("Contains stop codon", FULL_FM) == "None"


# ── compute_engineering_burden ────────────────────────────────────────────────


class TestComputeEngineeringBurden:
    def test_none_is_zero(self):
        assert main.compute_engineering_burden("None", FULL_FM) == 0.0

    def test_single_easily_fixable_is_one(self):
        assert main.compute_engineering_burden("Methionine Oxidation (M)", FULL_FM) == 1.0

    def test_single_fixable_is_one(self):
        assert main.compute_engineering_burden("Hydrolysis (NP)", FULL_FM) == 1.0

    def test_two_engineering_liabilities_is_two(self):
        assert main.compute_engineering_burden(
            "Methionine Oxidation (M), Hydrolysis (NP)", FULL_FM
        ) == 2.0

    def test_structural_not_counted(self):
        assert main.compute_engineering_burden("Missing Cysteines", FULL_FM) == 0.0

    def test_hard_to_fix_not_counted(self):
        # hard_to_fix maps to High engineering risk but contributes 0 to burden count
        assert main.compute_engineering_burden("Deamidation (N[GS])", FULL_FM) == 0.0

    def test_mixed_counts_only_fixable_and_easily_fixable(self):
        # Met oxidation (easily_fixable) counts; Deamidation (hard_to_fix) and Missing Cys (structural) do not
        assert main.compute_engineering_burden(
            "Methionine Oxidation (M), Deamidation (N[GS]), Missing Cysteines", FULL_FM
        ) == 1.0


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
        assert main.classify_engineering_risk("Test DG Pattern", fm) == "Medium"
        assert main.classify_sequence_quality("Test DG Pattern", fm) == "Pass"
        assert main.classify_structural_risk("Test DG Pattern", fm) == "None"

    def test_hard_to_fix_custom_contributes_high_risk(self):
        hard_def = {**self._DG_CDR12, "fixability": "hard_to_fix", "regions": ["CDR3"]}
        liabilities = main.identify_liabilities(
            "ADGSS", "CDR3", {}, {}, {}, {}, active_custom_defs=[hard_def]
        )
        fm = main._get_fixability_map({}, {}, {})
        fm[hard_def["name"]] = "hard_to_fix"
        assert main.classify_engineering_risk(liabilities, fm) == "High"

    def test_easily_fixable_custom_contributes_to_burden(self):
        easy_def = {**self._DG_CDR12, "fixability": "easily_fixable", "regions": ["CDR1"]}
        liabilities = main.identify_liabilities(
            "ADGSS", "CDR1", {}, {}, {}, {}, active_custom_defs=[easy_def]
        )
        fm = main._get_fixability_map({}, {}, {})
        fm[easy_def["name"]] = "easily_fixable"
        assert main.classify_engineering_risk(liabilities, fm) == "Low"
        assert main.compute_engineering_burden(liabilities, fm) == 1.0

    def test_no_match_when_pattern_does_not_match(self):
        liabilities = main.identify_liabilities(
            "ACGSS", "CDR1", {}, {}, {}, {}, active_custom_defs=[self._DG_CDR12]
        )
        assert "Test DG Pattern" not in liabilities


# ── integration: key ticket requirement (Lead Selection false negatives) ──────


class TestLeadSelectionFalseNegatives:
    """The ticket motivation: candidates with only Met/Trp oxidation were discarded
    by Lead Selection's default filter [\"None\"] on the old single \"Liabilities risk\" column.
    With the taxonomy split they now pass both Sequence quality and Structural liabilities,
    so the default filter lets them through.
    """

    def test_met_oxidation_only_passes_default_filters(self):
        liabilities = "Methionine Oxidation (M)"
        assert main.classify_sequence_quality(liabilities, FULL_FM) == "Pass"
        assert main.classify_structural_risk(liabilities, FULL_FM) == "None"

    def test_trp_oxidation_only_passes_default_filters(self):
        liabilities = "Tryptophan Oxidation (W)"
        assert main.classify_sequence_quality(liabilities, FULL_FM) == "Pass"
        assert main.classify_structural_risk(liabilities, FULL_FM) == "None"

    def test_missing_cys_caught_by_structural_filter(self):
        liabilities = "Missing Cysteines"
        assert main.classify_structural_risk(liabilities, FULL_FM) == "Present"
        assert main.classify_engineering_risk(liabilities, FULL_FM) == "None"

    def test_stop_codon_still_excluded_by_sequence_quality(self):
        liabilities = "Contains stop codon"
        assert main.classify_sequence_quality(liabilities, FULL_FM) == "Fail"
