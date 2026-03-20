"""Integration tests: run main() end-to-end on synthetic TSV data.

Covers the four new global output columns introduced in M2:
  - Is Productive
  - Structural liabilities
  - Developability risk
  - Developability score

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
    assert r["Developability score"] == pytest.approx(0.0)


def test_stop_codon_is_not_productive(tmp_path):
    df = run_main(tmp_path)
    r = row(df, "clone_stop")
    assert r["Is Productive"] == "Fail"
    assert r["Structural liabilities"] == "None"
    assert r["Developability risk"] == "None"
    assert r["Developability score"] == pytest.approx(0.0)


def test_out_of_frame_is_not_productive(tmp_path):
    df = run_main(tmp_path)
    r = row(df, "clone_out_of_frame")
    assert r["Is Productive"] == "Fail"
    assert r["Structural liabilities"] == "None"
    assert r["Developability risk"] == "None"
    assert r["Developability score"] == pytest.approx(0.0)


def test_missing_cys_is_structural(tmp_path):
    df = run_main(tmp_path)
    r = row(df, "clone_missing_cys")
    assert r["Is Productive"] == "Pass"
    assert r["Structural liabilities"] == "Present"
    assert r["Developability risk"] == "None"
    # FR1 weight=1.0, structural fixability_weight=20.0
    assert r["Developability score"] == pytest.approx(20.0)


def test_extra_cys_is_structural(tmp_path):
    df = run_main(tmp_path)
    r = row(df, "clone_extra_cys")
    assert r["Is Productive"] == "Pass"
    assert r["Structural liabilities"] == "Present"
    assert r["Developability risk"] == "None"
    # CDR3 weight=1.5, hard_to_fix fixability_weight=8.0
    assert r["Developability score"] == pytest.approx(12.0)


def test_met_oxidation_cdr3_medium_risk(tmp_path):
    df = run_main(tmp_path)
    r = row(df, "clone_met_cdr3")
    assert r["Is Productive"] == "Pass"
    assert r["Structural liabilities"] == "None"
    assert r["Developability risk"] == "Medium"
    # CDR3 weight=1.5, easily_fixable weight=1.0
    assert r["Developability score"] == pytest.approx(1.5)


def test_ngs_cdr3_high_risk(tmp_path):
    df = run_main(tmp_path)
    r = row(df, "clone_ngs_cdr3")
    assert r["Is Productive"] == "Pass"
    assert r["Structural liabilities"] == "None"
    assert r["Developability risk"] == "High"
    # CDR3 weight=1.5, fixable weight=3.0
    assert r["Developability score"] == pytest.approx(4.5)


def test_ngs_and_met_combined_score(tmp_path):
    """Two liabilities in different regions: score is the sum."""
    df = run_main(tmp_path)
    r = row(df, "clone_ngs_met")
    assert r["Is Productive"] == "Pass"
    assert r["Structural liabilities"] == "None"
    assert r["Developability risk"] == "High"
    # CDR2 Met: easily_fixable(1.0) × CDR2_weight(1.2) = 1.2
    # CDR3 N[GS]: fixable(3.0) × CDR3_weight(1.5) = 4.5
    assert r["Developability score"] == pytest.approx(5.7, abs=1e-9)


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
    assert r["Developability score"] == pytest.approx(1.5)


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
    assert r["Developability score"] == pytest.approx(0.0)


def test_disabled_cys_clears_structural(tmp_path):
    disabled = tmp_path / "disabled.json"
    disabled.write_text(json.dumps(["Missing Cysteines", "Extra Cysteines"]))
    df = run_main(tmp_path, ["--disabled-predefined-liabilities", str(disabled)])
    r = row(df, "clone_missing_cys")
    assert r["Structural liabilities"] == "None"
    assert r["Developability score"] == pytest.approx(0.0)


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
    assert ww["Developability score"] == pytest.approx(4.5)

    # All other clones should be clean (no predefined, no WW)
    clean = row(df, "clone_clean")
    assert clean["Is Productive"] == "Pass"
    assert clean["Developability risk"] == "None"
    assert clean["Developability score"] == pytest.approx(0.0)


def test_no_active_liabilities_emits_empty_columns(tmp_path):
    """When predefined is disabled and no custom defs are provided, the script warns
    and skips calculation. Global columns are still emitted (consistent schema) but empty."""
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
    # Columns are present (consistent output schema) but hold empty/null values
    for col in ("Is Productive", "Structural liabilities", "Developability risk", "Developability score"):
        assert col in df.columns, f"Expected {col!r} to be present for consistent schema"
    r = row(df, "clone_clean")
    assert r["Is Productive"] in ("", None), "Expected empty value when no liabilities active"
    assert r["Structural liabilities"] in ("", None)


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
    custom.write_text(json.dumps([{
        "name": "FR1 Proline",
        "pattern": "P",
        "riskLevel": "Low",
        "fixability": "fixable",
        "regions": ["FR1"],
    }]))
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
    assert r["Developability score"] == pytest.approx(0.0)


def test_annotation_path_met_oxidation_cdr3(tmp_path):
    """Path A: Met in CDR3 extracted from annotation produces Medium risk."""
    label_map_file = tmp_path / "label_map.json"
    label_map_file.write_text(json.dumps(LABEL_MAP))
    df = run_main(tmp_path, ["-m", str(label_map_file)], data_path=DATA_ANNOTATED)
    r = row(df, "ann_met_cdr3")
    assert r["Is Productive"] == "Pass"
    assert r["Developability risk"] == "Medium"
    assert r["Developability score"] == pytest.approx(1.5)  # CDR3 weight=1.5, easily_fixable=1.0


def test_annotation_path_ngs_deamidation_cdr3(tmp_path):
    """Path A: N[GS] in CDR3 extracted from annotation produces High risk."""
    label_map_file = tmp_path / "label_map.json"
    label_map_file.write_text(json.dumps(LABEL_MAP))
    df = run_main(tmp_path, ["-m", str(label_map_file)], data_path=DATA_ANNOTATED)
    r = row(df, "ann_ngs_cdr3")
    assert r["Is Productive"] == "Pass"
    assert r["Developability risk"] == "High"
    assert r["Developability score"] == pytest.approx(4.5)  # CDR3 weight=1.5, fixable=3.0


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
    assert r["Developability score"] == pytest.approx(0.0)


def test_sc_heavy_chain_liability_detected(tmp_path):
    """Met oxidation in Heavy CDR3 is scored correctly; light chain is clean."""
    df = run_main(tmp_path, data_path=DATA_SC)
    r = row(df, "sc_heavy_met_cdr3")
    assert r["Is Productive"] == "Pass"
    assert r["Developability risk"] == "Medium"
    assert r["Developability score"] == pytest.approx(1.5)


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
# Custom liability per-region risk (R8)
#
# Custom fixable/easily_fixable liabilities must appear in per-region risk
# columns, not only in global developability columns.
# ---------------------------------------------------------------------------


def test_custom_fixable_liability_raises_per_region_risk(tmp_path):
    """A High-risk fixable custom liability in CDR3 must produce High per-region risk for CDR3.

    Regression: classify_risk() previously ignored custom liabilities, leaving
    CDR3 aa risk at None even when a custom fixable liability was detected there.
    """
    custom = tmp_path / "custom.json"
    custom.write_text(json.dumps([{
        "name": "WW motif",
        "pattern": "WW",
        "riskLevel": "High",
        "fixability": "fixable",
        "regions": ["CDR3"],
    }]))
    df = run_main(
        tmp_path,
        ["--use-predefined-liabilities", "false", "--custom-liabilities", str(custom)],
    )
    r = row(df, "clone_custom_ww")
    # WW is present in CDR3 — per-region risk must reflect it
    assert r["CDR3 aa risk"] == "High"
    # CDR2 has no WW — must remain None
    assert r["CDR2 aa risk"] == "None"


def test_custom_easily_fixable_liability_raises_per_region_risk(tmp_path):
    """A Medium easily_fixable custom liability in CDR2 must raise CDR2 aa risk to Medium."""
    custom = tmp_path / "custom.json"
    custom.write_text(json.dumps([{
        "name": "GR motif",
        "pattern": "GR",
        "riskLevel": "Medium",
        "fixability": "easily_fixable",
        "regions": ["CDR2"],
    }]))
    df = run_main(
        tmp_path,
        ["--use-predefined-liabilities", "false", "--custom-liabilities", str(custom)],
    )
    # clone_clean CDR2 = ISPGRGIT — contains GR
    r = row(df, "clone_clean")
    assert r["CDR2 aa risk"] == "Medium"
    # CDR3 has no GR — must stay None
    assert r["CDR3 aa risk"] == "None"


def test_custom_hard_to_fix_does_not_raise_per_region_risk(tmp_path):
    """A hard_to_fix custom liability routes to Structural liabilities, not per-region risk."""
    custom = tmp_path / "custom.json"
    custom.write_text(json.dumps([{
        "name": "WW hard",
        "pattern": "WW",
        "riskLevel": "High",
        "fixability": "hard_to_fix",
        "regions": ["CDR3"],
    }]))
    df = run_main(
        tmp_path,
        ["--use-predefined-liabilities", "false", "--custom-liabilities", str(custom)],
    )
    r = row(df, "clone_custom_ww")
    assert r["Structural liabilities"] == "Present"
    assert r["CDR3 aa risk"] == "None"


def test_custom_and_predefined_combine_in_per_region_risk(tmp_path):
    """Custom and predefined fixable liabilities in the same region take the higher risk level.

    clone_met_cdr3 CDR3 has Met (predefined Medium/easily_fixable).
    Adding a custom High/fixable motif that also matches CDR3 must raise it to High.
    """
    custom = tmp_path / "custom.json"
    custom.write_text(json.dumps([{
        "name": "MG motif",
        "pattern": "MG",
        "riskLevel": "High",
        "fixability": "fixable",
        "regions": ["CDR3"],
    }]))
    df = run_main(tmp_path, ["--custom-liabilities", str(custom)])
    r = row(df, "clone_met_cdr3")
    # Custom MG (High) beats predefined Met (Medium) — CDR3 risk must be High
    assert r["CDR3 aa risk"] == "High"
