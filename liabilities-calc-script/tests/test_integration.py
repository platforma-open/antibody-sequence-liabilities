"""Integration tests: run main() end-to-end on synthetic TSV data.

Covers the four new global output columns introduced in M2:
  - Is Productive
  - Structural liabilities
  - Developability risk
  - Developability cost

Also exercises --disabled-predefined-liabilities, --use-predefined-liabilities, and --custom-liabilities flags.

Run with coverage (from liabilities-calc-script/):
    uv run pytest tests/ --cov=src --cov-report=term-missing
"""

import json
import sys
from pathlib import Path

import polars as pl
import pytest

import main as m

DATA = Path(__file__).parent / "data" / "sequences.tsv"
DATA_ANNOTATED = Path(__file__).parent / "data" / "sequences_annotated.tsv"
DATA_SC = Path(__file__).parent / "data" / "sequences_sc.tsv"
LABEL_MAP = {"1": "CDR1", "2": "CDR2", "3": "CDR3"}


def run_main(
    tmp_path: Path,
    extra_args: list[str] | None = None,
    data_path: Path | None = None,
) -> pl.DataFrame:
    """Call main() with a synthetic TSV, return the output as a DataFrame."""
    out = tmp_path / "out.tsv"
    argv = ["main.py", str(data_path or DATA), str(out)] + (extra_args or [])
    original = sys.argv
    sys.argv = argv
    try:
        m.main()
    finally:
        sys.argv = original
    return pl.read_csv(out, separator="\t")


def row(df: pl.DataFrame, key: str) -> dict:
    rows = df.filter(pl.col("clonotypeKey") == key).to_dicts()
    assert len(rows) == 1, f"Expected exactly one row for {key!r}, got {len(rows)}"
    return rows[0]


# ---------------------------------------------------------------------------
# Global classification columns
# ---------------------------------------------------------------------------


def test_clean_sequence_passes_all(tmp_path):
    df = run_main(tmp_path)
    r = row(df, "clone_clean")
    assert r["Is Productive"] == "Pass"
    assert r["Structural liabilities"] == "None"
    assert r["Developability risk"] == "None"
    assert r["Developability cost"] == pytest.approx(0.0)


def test_stop_codon_is_not_productive(tmp_path):
    df = run_main(tmp_path)
    r = row(df, "clone_stop")
    assert r["Is Productive"] == "Fail"
    assert r["Structural liabilities"] == "None"
    assert r["Developability risk"] == "None"
    assert r["Developability cost"] == pytest.approx(0.0)


def test_out_of_frame_is_not_productive(tmp_path):
    df = run_main(tmp_path)
    r = row(df, "clone_out_of_frame")
    assert r["Is Productive"] == "Fail"
    assert r["Structural liabilities"] == "None"
    assert r["Developability risk"] == "None"
    assert r["Developability cost"] == pytest.approx(0.0)


def test_missing_cys_is_structural(tmp_path):
    df = run_main(tmp_path)
    r = row(df, "clone_missing_cys")
    assert r["Is Productive"] == "Pass"
    assert r["Structural liabilities"] == "Present"
    assert r["Developability risk"] == "None"
    # FR1 weight=1.0, structural fixability_weight=20.0
    assert r["Developability cost"] == pytest.approx(20.0)


def test_extra_cys_is_structural(tmp_path):
    df = run_main(tmp_path)
    r = row(df, "clone_extra_cys")
    assert r["Is Productive"] == "Pass"
    assert r["Structural liabilities"] == "Present"
    assert r["Developability risk"] == "None"
    # CDR3 weight=1.5, hard_to_fix fixability_weight=8.0
    assert r["Developability cost"] == pytest.approx(12.0)


def test_met_oxidation_cdr3_medium_risk(tmp_path):
    df = run_main(tmp_path)
    r = row(df, "clone_met_cdr3")
    assert r["Is Productive"] == "Pass"
    assert r["Structural liabilities"] == "None"
    assert r["Developability risk"] == "Medium"
    # CDR3 weight=1.5, easily_fixable weight=1.0
    assert r["Developability cost"] == pytest.approx(1.5)


def test_ngs_cdr3_high_risk(tmp_path):
    df = run_main(tmp_path)
    r = row(df, "clone_ngs_cdr3")
    assert r["Is Productive"] == "Pass"
    assert r["Structural liabilities"] == "None"
    assert r["Developability risk"] == "High"
    # CDR3 weight=1.5, fixable weight=3.0
    assert r["Developability cost"] == pytest.approx(4.5)


def test_ngs_and_met_combined_score(tmp_path):
    """Two liabilities in different regions: score is the sum."""
    df = run_main(tmp_path)
    r = row(df, "clone_ngs_met")
    assert r["Is Productive"] == "Pass"
    assert r["Structural liabilities"] == "None"
    assert r["Developability risk"] == "High"
    # CDR2 Met: easily_fixable(1.0) × CDR2_weight(1.2) = 1.2
    # CDR3 N[GS]: fixable(3.0) × CDR3_weight(1.5) = 4.5
    assert r["Developability cost"] == pytest.approx(5.7, abs=1e-9)


# ---------------------------------------------------------------------------
# Per-region liability columns
# ---------------------------------------------------------------------------


def test_per_region_liability_columns_present(tmp_path):
    df = run_main(tmp_path)
    expected_cols = {
        "CDR1 aa liabilities",
        "CDR2 aa liabilities",
        "CDR3 aa liabilities",
        "FR1 aa liabilities",
    }
    assert expected_cols <= set(df.columns)


def test_per_region_liabilities_content(tmp_path):
    df = run_main(tmp_path)
    r = row(df, "clone_ngs_met")
    assert "Methionine Oxidation (M)" in r["CDR2 aa liabilities"]
    assert "Deamidation (N[GS])" in r["CDR3 aa liabilities"]
    assert r["CDR1 aa liabilities"] == "None"
    assert r["FR1 aa liabilities"] == "None"


def test_stop_codon_per_region(tmp_path):
    df = run_main(tmp_path)
    r = row(df, "clone_stop")
    assert "Contains stop codon" in r["CDR1 aa liabilities"]


def test_stop_codon_with_coexisting_fixable_liability(tmp_path):
    """Disqualifying liabilities make sequence non-productive but do not suppress
    developability score contributions from coexisting fixable liabilities."""
    df = run_main(tmp_path)
    r = row(df, "clone_stop_and_met")
    assert r["Is Productive"] == "Fail"
    # Met oxidation in CDR3 (easily_fixable × CDR3_weight = 1.0 × 1.5 = 1.5)
    assert r["Developability cost"] == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# --disabled-predefined-liabilities flag
# ---------------------------------------------------------------------------


def test_disabled_deamidation_clears_ngs_risk(tmp_path):
    disabled = tmp_path / "disabled.json"
    disabled.write_text(json.dumps(["Deamidation (N[GS])"]))
    df = run_main(tmp_path, ["--disabled-predefined-liabilities", str(disabled)])
    r = row(df, "clone_ngs_cdr3")
    # Deamidation suppressed — no fixable liabilities remain
    assert r["Developability risk"] == "None"
    assert r["Developability cost"] == pytest.approx(0.0)


def test_disabled_cys_clears_structural(tmp_path):
    disabled = tmp_path / "disabled.json"
    disabled.write_text(json.dumps(["Missing Cysteines", "Extra Cysteines"]))
    df = run_main(tmp_path, ["--disabled-predefined-liabilities", str(disabled)])
    r = row(df, "clone_missing_cys")
    assert r["Structural liabilities"] == "None"
    assert r["Developability cost"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# --use-predefined-liabilities false + custom liabilities
# ---------------------------------------------------------------------------


def test_custom_only_detects_ww_motif(tmp_path):
    """Disable predefined liabilities; define a custom WW motif for CDR3."""
    custom = tmp_path / "custom.json"
    custom.write_text(
        json.dumps(
            [
                {
                    "name": "WW motif",
                    "pattern": "WW",
                    "riskLevel": "High",
                    "fixability": "fixable",
                    "regions": ["CDR3"],
                }
            ]
        )
    )
    df = run_main(
        tmp_path,
        [
            "--use-predefined-liabilities",
            "false",
            "--custom-liabilities",
            str(custom),
        ],
    )
    ww = row(df, "clone_custom_ww")
    assert "WW motif" in ww["CDR3 aa liabilities"]
    assert ww["Developability risk"] == "High"
    # CDR3 weight=1.5, fixable=3.0
    assert ww["Developability cost"] == pytest.approx(4.5)

    # All other clones should be clean (no predefined, no WW)
    clean = row(df, "clone_clean")
    assert clean["Is Productive"] == "Pass"
    assert clean["Developability risk"] == "None"
    assert clean["Developability cost"] == pytest.approx(0.0)


def test_no_active_liabilities_emits_empty_columns(tmp_path):
    """When predefined is disabled and no custom defs are provided, stop codon / OOF detection
    still runs (always active). Global columns are present and Is Productive reflects the
    stop codon / OOF check result for each sequence."""
    custom = tmp_path / "custom.json"
    custom.write_text(json.dumps([]))
    df = run_main(
        tmp_path,
        [
            "--use-predefined-liabilities",
            "false",
            "--custom-liabilities",
            str(custom),
        ],
    )
    # Columns are always present (consistent output schema)
    for col in ("Is Productive", "Structural liabilities", "Developability risk", "Developability cost"):
        assert col in df.columns, f"Expected {col!r} to be present for consistent schema"
    r = row(df, "clone_clean")
    # Stop codon / OOF is always active — clean sequence passes
    assert r["Is Productive"] == "Pass"
    # No cys or CDR defs active — structural and developability columns are empty/None/None
    assert r["Structural liabilities"] in ("None", "", None)


# ---------------------------------------------------------------------------
# Sequence liabilities summary column
# ---------------------------------------------------------------------------


def test_clean_sequence_summary_is_none(tmp_path):
    df = run_main(tmp_path)
    r = row(df, "clone_clean")
    assert r["Sequence liabilities summary"] == "None"


def test_summary_lists_all_liable_regions(tmp_path):
    """Summary includes each region that has liabilities and omits clean ones."""
    df = run_main(tmp_path)
    r = row(df, "clone_ngs_met")
    summary = r["Sequence liabilities summary"]
    assert "CDR2" in summary
    assert "CDR3" in summary
    assert "Methionine Oxidation (M)" in summary
    assert "Deamidation (N[GS])" in summary
    assert "CDR1" not in summary


# ---------------------------------------------------------------------------
# --output-regions-found flag
# ---------------------------------------------------------------------------


def test_output_regions_found_writes_json(tmp_path):
    regions_file = tmp_path / "regions.json"
    run_main(tmp_path, ["--output-regions-found", str(regions_file)])
    regions = json.loads(regions_file.read_text())
    assert set(regions) >= {"CDR1", "CDR2", "CDR3", "FR1"}


def test_output_regions_found_ordering(tmp_path):
    """Regions are returned in anatomical order (FR1, CDR1, CDR2, CDR3, ...)."""
    regions_file = tmp_path / "regions.json"
    run_main(tmp_path, ["--output-regions-found", str(regions_file)])
    regions = json.loads(regions_file.read_text())
    cdr_indices = {r: regions.index(r) for r in ["FR1", "CDR1", "CDR2", "CDR3"] if r in regions}
    assert cdr_indices["FR1"] < cdr_indices["CDR1"] < cdr_indices["CDR2"] < cdr_indices["CDR3"]


# ---------------------------------------------------------------------------
# Custom liability region restriction
# ---------------------------------------------------------------------------


def test_custom_liability_restricted_to_fr1(tmp_path):
    """A custom liability targeting FR1 only is detected there but not in CDRs."""
    custom = tmp_path / "custom.json"
    # FR1 for all test clones contains 'P' (e.g. QVQLVQSGAEVKKPGASVKVSCKAS)
    custom.write_text(
        json.dumps(
            [
                {
                    "name": "FR1 Proline",
                    "pattern": "P",
                    "riskLevel": "Low",
                    "fixability": "fixable",
                    "regions": ["FR1"],
                }
            ]
        )
    )
    df = run_main(tmp_path, ["--custom-liabilities", str(custom)])
    r = row(df, "clone_clean")
    assert "FR1 Proline" in r["FR1 aa liabilities"]
    assert "FR1 Proline" not in r["CDR1 aa liabilities"]
    assert "FR1 Proline" not in r["CDR3 aa liabilities"]


# ---------------------------------------------------------------------------
# Annotation-based extraction (Path A)
# ---------------------------------------------------------------------------


def test_annotation_path_clean_sequence(tmp_path):
    """Path A: sequence with no liabilities in any extracted region passes all checks."""
    label_map_file = tmp_path / "label_map.json"
    label_map_file.write_text(json.dumps(LABEL_MAP))
    df = run_main(tmp_path, ["-m", str(label_map_file)], data_path=DATA_ANNOTATED)
    r = row(df, "ann_clean")
    assert r["Is Productive"] == "Pass"
    assert r["Structural liabilities"] == "None"
    assert r["Developability risk"] == "None"
    assert r["Developability cost"] == pytest.approx(0.0)


def test_annotation_path_met_oxidation_cdr3(tmp_path):
    """Path A: Met in CDR3 extracted from annotation produces Medium risk."""
    label_map_file = tmp_path / "label_map.json"
    label_map_file.write_text(json.dumps(LABEL_MAP))
    df = run_main(tmp_path, ["-m", str(label_map_file)], data_path=DATA_ANNOTATED)
    r = row(df, "ann_met_cdr3")
    assert r["Is Productive"] == "Pass"
    assert r["Developability risk"] == "Medium"
    assert r["Developability cost"] == pytest.approx(1.5)  # CDR3 weight=1.5, easily_fixable=1.0


def test_annotation_path_ngs_deamidation_cdr3(tmp_path):
    """Path A: N[GS] in CDR3 extracted from annotation produces High risk."""
    label_map_file = tmp_path / "label_map.json"
    label_map_file.write_text(json.dumps(LABEL_MAP))
    df = run_main(tmp_path, ["-m", str(label_map_file)], data_path=DATA_ANNOTATED)
    r = row(df, "ann_ngs_cdr3")
    assert r["Is Productive"] == "Pass"
    assert r["Developability risk"] == "High"
    assert r["Developability cost"] == pytest.approx(4.5)  # CDR3 weight=1.5, fixable=3.0


def test_annotation_path_label_map_output(tmp_path):
    """Path A: --output-label-map writes a JSON file mapping liability codes to names."""
    label_map_file = tmp_path / "label_map.json"
    label_map_file.write_text(json.dumps(LABEL_MAP))
    out_map = tmp_path / "out_map.json"
    run_main(
        tmp_path,
        ["-m", str(label_map_file), "-o", str(out_map)],
        data_path=DATA_ANNOTATED,
    )
    result = json.loads(out_map.read_text())
    # Region codes from input label map are preserved in the output
    assert result.get("1") == "CDR1"
    assert result.get("2") == "CDR2"
    assert result.get("3") == "CDR3"


# ---------------------------------------------------------------------------
# Multi-chain (single-cell) data
# ---------------------------------------------------------------------------


def test_sc_clean_sequence_passes(tmp_path):
    df = run_main(tmp_path, data_path=DATA_SC)
    r = row(df, "sc_clean")
    assert r["Is Productive"] == "Pass"
    assert r["Structural liabilities"] == "None"
    assert r["Developability risk"] == "None"
    assert r["Developability cost"] == pytest.approx(0.0)


def test_sc_heavy_chain_liability_detected(tmp_path):
    """Met oxidation in Heavy CDR3 is scored correctly; light chain is clean."""
    df = run_main(tmp_path, data_path=DATA_SC)
    r = row(df, "sc_heavy_met_cdr3")
    assert r["Is Productive"] == "Pass"
    assert r["Developability risk"] == "Medium"
    assert r["Developability cost"] == pytest.approx(1.5)


def test_sc_summary_has_chain_prefix(tmp_path):
    """Multi-chain summary uses 'Heavy chain:' / 'Light chain:' prefixes."""
    df = run_main(tmp_path, data_path=DATA_SC)
    r = row(df, "sc_heavy_met_cdr3")
    summary = r["Sequence liabilities summary"]
    assert "Heavy chain" in summary
    assert "Methionine Oxidation (M)" in summary


def test_sc_clean_summary_is_none(tmp_path):
    df = run_main(tmp_path, data_path=DATA_SC)
    r = row(df, "sc_clean")
    assert r["Sequence liabilities summary"] == "None"


def test_sc_both_chains_liabilities(tmp_path):
    """Liabilities in both Heavy and Light chains appear in the summary."""
    df = run_main(tmp_path, data_path=DATA_SC)
    r = row(df, "sc_both_chains_liab")
    summary = r["Sequence liabilities summary"]
    assert "Heavy chain" in summary
    assert "Light chain" in summary


# ---------------------------------------------------------------------------
# Per-region risk by liability class
#
# The spec at :126 (Open Questions) named two options for per-region risk:
# (A) fixable + easily_fixable only, or (B) all liabilities except disqualifying.
# The v4.0.0 implementor picked A and encoded it across R8 :71, Step 2 :252-253,
# Defaults :304, M1 :346, and Risks :395. User feedback (Slack 2026-05-24)
# revealed Option A's predicted counter-argument materialized — per-region
# Liabilities and Risk visibly disagree. These tests lock in the switch to
# Option B: per-region risk is the max riskLevel of any non-disqualifying
# liability in the region, regardless of fixability class.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixability, pattern, region, clone, expected_risk, expected_structural",
    [
        ("easily_fixable", "GR", "CDR2", "clone_clean", "Medium", "None"),
        ("fixable", "WW", "CDR3", "clone_custom_ww", "High", "None"),
        ("hard_to_fix", "WW", "CDR3", "clone_custom_ww", "High", "Present"),
    ],
    ids=["easily_fixable-cdr2-medium", "fixable-cdr3-high", "hard_to_fix-cdr3-high"],
)
def test_custom_liability_per_region_risk_by_fixability(
    tmp_path, fixability, pattern, region, clone, expected_risk, expected_structural
):
    """A custom liability's riskLevel surfaces in {region} aa risk regardless of
    fixability class (Option B at spec :126). The Structural liabilities column
    additionally flags Present for hard_to_fix/structural matches; engineering-
    only fixabilities (fixable, easily_fixable) leave it None.
    """
    liability_name = f"Custom {fixability}"
    custom = tmp_path / "custom.json"
    custom.write_text(
        json.dumps(
            [
                {
                    "name": liability_name,
                    "pattern": pattern,
                    "riskLevel": expected_risk,
                    "fixability": fixability,
                    "regions": [region],
                }
            ]
        )
    )
    df = run_main(
        tmp_path,
        ["--use-predefined-liabilities", "false", "--custom-liabilities", str(custom)],
    )
    r = row(df, clone)
    assert liability_name in r[f"{region} aa liabilities"]
    assert r[f"{region} aa risk"] == expected_risk
    # Custom liability is scoped to one region — other CDRs stay None.
    for other_region in ("CDR1", "CDR2", "CDR3"):
        if other_region != region:
            assert r[f"{other_region} aa risk"] == "None"
    assert r["Structural liabilities"] == expected_structural


@pytest.mark.parametrize(
    "custom_name, pattern, custom_fixability",
    [
        ("MG motif", "MG", "fixable"),
        ("Custom hard M", "M", "hard_to_fix"),
    ],
    ids=["custom-fixable-high", "custom-hard_to_fix-high"],
)
def test_custom_high_overrides_predefined_easily_fixable_medium_in_same_region(
    tmp_path, custom_name, pattern, custom_fixability
):
    """Per-region risk takes the max across all non-disqualifying liabilities in
    the region. clone_met_cdr3 CDR3 has predefined Methionine Oxidation
    (Medium/easily_fixable); adding a custom High in the same region must raise
    CDR3 risk to High.

    Cases:
    - custom-fixable-high: Option A already produced High here (both items
      counted toward engineering risk). Confirms behavior is unchanged.
    - custom-hard_to_fix-high: under Option A the custom was excluded so CDR3
      risk stayed at Medium. Under Option B it now contributes; CDR3 → High.
    """
    custom = tmp_path / "custom.json"
    custom.write_text(
        json.dumps(
            [
                {
                    "name": custom_name,
                    "pattern": pattern,
                    "riskLevel": "High",
                    "fixability": custom_fixability,
                    "regions": ["CDR3"],
                }
            ]
        )
    )
    df = run_main(tmp_path, ["--custom-liabilities", str(custom)])
    r = row(df, "clone_met_cdr3")
    assert "Methionine Oxidation (M)" in r["CDR3 aa liabilities"]
    assert custom_name in r["CDR3 aa liabilities"]
    assert r["CDR3 aa risk"] == "High"


def test_extra_cys_raises_per_region_risk(tmp_path):
    """Extra Cysteines (predefined hard_to_fix, High) in CDR3 must yield CDR3
    aa risk = High. Predefined counterpart to the hard_to_fix custom-liability
    cases in test_custom_liability_per_region_risk_by_fixability."""
    df = run_main(tmp_path)
    r = row(df, "clone_extra_cys")
    assert "Extra Cysteines" in r["CDR3 aa liabilities"]
    assert r["CDR3 aa risk"] == "High"
    # Structural liabilities column still flags Present (unchanged).
    assert r["Structural liabilities"] == "Present"
    # Developability risk stays None (engineering-only column, unchanged).
    assert r["Developability risk"] == "None"


def test_missing_cys_raises_fr1_per_region_risk(tmp_path):
    """Missing Cysteines (predefined structural, High) in FR1 must yield FR1
    aa risk = High. Covers the 'structural' fixability class — symmetric to
    test_extra_cys_raises_per_region_risk which covers 'hard_to_fix'."""
    df = run_main(tmp_path)
    r = row(df, "clone_missing_cys")
    assert "Missing Cysteines" in r["FR1 aa liabilities"]
    assert r["FR1 aa risk"] == "High"
    assert r["Structural liabilities"] == "Present"
    # Developability risk stays None (engineering-only column).
    assert r["Developability risk"] == "None"


def test_stop_codon_does_not_raise_per_region_risk(tmp_path):
    """A disqualifying liability (stop codon) in a region's liabilities string
    must NOT contribute to per-region risk for that region. clone_stop has the
    stop codon in CDR1; CDR1 aa risk must stay None even though
    "Contains stop codon" is listed in CDR1 aa liabilities. The disqualifying
    signal surfaces via Is Productive = Fail.

    Guards the 'disqualifying' skip in classify_risk()."""
    df = run_main(tmp_path)
    r = row(df, "clone_stop")
    assert "Contains stop codon" in r["CDR1 aa liabilities"]
    assert r["CDR1 aa risk"] == "None"
    assert r["Is Productive"] == "Fail"
