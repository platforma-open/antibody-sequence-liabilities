"""Integration tests: run main() end-to-end on synthetic TSV data.

Covers the four new global output columns introduced in M2:
  - Is Productive
  - Structural liabilities
  - Developability risk
  - Developability score

Also exercises --disabled-predefined-liabilities, --use-predefined-liabilities, and --custom-liabilities flags.
"""

import json
import sys
from pathlib import Path

import polars as pl
import pytest

import main as m

DATA = Path(__file__).parent / "data" / "sequences.tsv"


def run_main(tmp_path: Path, extra_args: list[str] | None = None) -> pl.DataFrame:
    """Call main() with the synthetic TSV, return the output as a DataFrame."""
    out = tmp_path / "out.tsv"
    argv = [
        "main.py",
        str(DATA),
        str(out),
    ] + (extra_args or [])
    monkeypatch_argv = argv  # captured below
    original = sys.argv
    sys.argv = monkeypatch_argv
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
