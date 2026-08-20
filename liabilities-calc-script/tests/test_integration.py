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
from annotations import parse_annotations

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
    # Structural override: Missing Cys is 'structural' fixability → Non-Developable.
    assert r["Developability risk"] == "Non-Developable"
    # FR1 weight=1.0, structural fixability_weight=20.0
    assert r["Developability cost"] == pytest.approx(20.0)


def test_extra_cys_is_structural(tmp_path):
    df = run_main(tmp_path)
    r = row(df, "clone_extra_cys")
    assert r["Is Productive"] == "Pass"
    assert r["Structural liabilities"] == "Present"
    # hard_to_fix override: Developability risk = Very High (structural class
    # would be Non-Developable; Extra Cys is hard_to_fix, the milder bucket).
    assert r["Developability risk"] == "Very High"
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
    "fixability, pattern, region, clone, expected_risk, expected_structural, expected_devel_risk",
    [
        ("easily_fixable", "GR", "CDR2", "clone_clean", "Medium", "None", "Medium"),
        ("fixable", "WW", "CDR3", "clone_custom_ww", "High", "None", "High"),
        ("hard_to_fix", "WW", "CDR3", "clone_custom_ww", "High", "Present", "Very High"),
    ],
    ids=["easily_fixable-cdr2-medium", "fixable-cdr3-high", "hard_to_fix-cdr3-veryhigh"],
)
def test_custom_liability_per_region_risk_by_fixability(
    tmp_path,
    fixability,
    pattern,
    region,
    clone,
    expected_risk,
    expected_structural,
    expected_devel_risk,
):
    """A custom liability's riskLevel surfaces in {region} aa risk regardless of
    fixability class (Option B at spec :126). The Structural liabilities column
    additionally flags Present for hard_to_fix/structural matches; engineering-
    only fixabilities (fixable, easily_fixable) leave it None. Developability
    risk reflects the engineering severity (None/Low/Medium/High) for
    engineering-only fixabilities; Very High when hard_to_fix; Non-Developable
    when structural.
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
    assert r["Developability risk"] == expected_devel_risk


@pytest.mark.parametrize(
    "custom_name, pattern, custom_fixability, expected_devel_risk",
    [
        ("MG motif", "MG", "fixable", "High"),
        ("Custom hard M", "M", "hard_to_fix", "Very High"),
    ],
    ids=["custom-fixable-high", "custom-hard_to_fix-veryhigh"],
)
def test_custom_high_overrides_predefined_easily_fixable_medium_in_same_region(
    tmp_path, custom_name, pattern, custom_fixability, expected_devel_risk
):
    """Per-region risk takes the max across all non-disqualifying liabilities in
    the region. clone_met_cdr3 CDR3 has predefined Methionine Oxidation
    (Medium/easily_fixable); adding a custom High in the same region must raise
    CDR3 risk to High. Developability risk depends on the custom's class:
    fixable contributes to engineering severity (High); hard_to_fix triggers the
    hard_to_fix override (Very High).

    Cases:
    - custom-fixable-high: Option A already produced High here (both items
      counted toward engineering risk). Confirms behavior is unchanged.
    - custom-hard_to_fix-veryhigh: under Option A the custom was excluded so
      CDR3 risk stayed at Medium. Under Option B it now contributes; CDR3 → High.
      The hard_to_fix class also flips Developability risk to Very High.
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
    assert r["Developability risk"] == expected_devel_risk


def test_extra_cys_raises_per_region_risk(tmp_path):
    """Extra Cysteines (predefined hard_to_fix, High) in CDR3 must yield CDR3
    aa risk = High and Developability risk = Very High (hard_to_fix override —
    the milder of the two structural-class overrides)."""
    df = run_main(tmp_path)
    r = row(df, "clone_extra_cys")
    assert "Extra Cysteines" in r["CDR3 aa liabilities"]
    assert r["CDR3 aa risk"] == "High"
    assert r["Structural liabilities"] == "Present"
    assert r["Developability risk"] == "Very High"


def test_missing_cys_raises_fr1_per_region_risk(tmp_path):
    """Missing Cysteines (predefined structural, High) in FR1 must yield FR1
    aa risk = High and Developability risk = Non-Developable (structural
    override — the harshest bucket). Symmetric to
    test_extra_cys_raises_per_region_risk which covers 'hard_to_fix' → Very High."""
    df = run_main(tmp_path)
    r = row(df, "clone_missing_cys")
    assert "Missing Cysteines" in r["FR1 aa liabilities"]
    assert r["FR1 aa risk"] == "High"
    assert r["Structural liabilities"] == "Present"
    assert r["Developability risk"] == "Non-Developable"


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


def test_structural_supersedes_hard_to_fix_in_developability_risk(tmp_path):
    """When a row carries BOTH a structural and a hard_to_fix liability,
    Developability risk reports Non-Developable. The harsher override wins.

    Setup: clone_extra_cys already has predefined Extra Cysteines (hard_to_fix)
    in CDR3 — alone that yields Developability risk = Very High. Adding a custom
    'structural' liability matching CDR1 must override to Non-Developable.

    Note: the UI restricts custom fixability to {easily_fixable, fixable,
    hard_to_fix}. 'structural' is used here via direct JSON to exercise the
    override-precedence rule; production users reach this state only through
    the predefined Missing Cysteines liability.
    """
    custom = tmp_path / "custom.json"
    custom.write_text(
        json.dumps(
            [
                {
                    "name": "Custom structural",
                    "pattern": "[A-Z]",
                    "riskLevel": "High",
                    "fixability": "structural",
                    "regions": ["CDR1"],
                }
            ]
        )
    )
    df = run_main(tmp_path, ["--custom-liabilities", str(custom)])
    r = row(df, "clone_extra_cys")
    assert "Extra Cysteines" in r["CDR3 aa liabilities"]
    assert "Custom structural" in r["CDR1 aa liabilities"]
    # hard_to_fix alone → Very High; structural wins → Non-Developable.
    assert r["Developability risk"] == "Non-Developable"
    assert r["Structural liabilities"] == "Present"


# ---------------------------------------------------------------------------
# --regions (region scope)
# ---------------------------------------------------------------------------

# Parental-contamination fixture. FR1 and CDR1 carry liabilities the user considers
# known-good (they came in with the parent scaffold); CDR3 is the region actually being
# engineered. Without scoping, both candidates score identically High and cannot be told
# apart — the exact problem region scope exists to solve.
PARENTAL_HEADER = "clonotypeKey\tCDR1 aa\tCDR2 aa\tCDR3 aa\tFR1 aa\n"
PARENTAL_ROWS = (
    "cand_clean_cdr3\tGYTFTNGY\tISPGRGIT\tCARYALD\tQVQLVQSGAEVKKPDPSVKVSCKAS\n"
    "cand_dirty_cdr3\tGYTFTNGY\tISPGRGIT\tCARYNGF\tQVQLVQSGAEVKKPDPSVKVSCKAS\n"
)


def _parental_data(tmp_path: Path) -> Path:
    p = tmp_path / "parental.tsv"
    p.write_text(PARENTAL_HEADER + PARENTAL_ROWS)
    return p


def test_regions_absent_scans_every_region(tmp_path):
    """No --regions flag = pre-feature behaviour: every region present is scanned."""
    df = run_main(tmp_path, data_path=_parental_data(tmp_path))
    assert "CDR1 aa liabilities" in df.columns
    assert "FR1 aa liabilities" in df.columns
    assert "CDR3 aa liabilities" in df.columns


def test_regions_drops_unselected_region_columns(tmp_path):
    """Deselected regions disappear from the output rather than being emitted empty.

    This is what shrinks the per-region PColumn set the workflow emits: the Tengo side
    builds its output columns from --output-regions-found, which is derived from the same
    filtered column list.
    """
    df = run_main(tmp_path, ["--regions", "CDR3"], data_path=_parental_data(tmp_path))
    assert "CDR3 aa liabilities" in df.columns
    assert "CDR3 aa risk" in df.columns
    for absent in ("CDR1 aa liabilities", "CDR2 aa liabilities", "FR1 aa liabilities"):
        assert absent not in df.columns


def test_regions_found_output_reflects_scope(tmp_path):
    out_regions = tmp_path / "regions.json"
    run_main(
        tmp_path,
        ["--regions", "CDR3", "--output-regions-found", str(out_regions)],
        data_path=_parental_data(tmp_path),
    )
    assert json.loads(out_regions.read_text()) == ["CDR3"]


def test_regions_excludes_parental_liabilities_from_score(tmp_path):
    """The point of the feature: scoping to CDR3 separates candidates that were tied.

    Unscoped, both rows are High because of the shared FR1/CDR1 parental liabilities.
    Scoped to CDR3, the candidate with a clean CDR3 drops to None and the one with a
    real CDR3 liability stays High.
    """
    data = _parental_data(tmp_path)
    unscoped_dir = tmp_path / "a"
    unscoped_dir.mkdir()
    scoped_dir = tmp_path / "b"
    scoped_dir.mkdir()

    unscoped = run_main(unscoped_dir, data_path=data)
    assert row(unscoped, "cand_clean_cdr3")["Developability risk"] == "High"
    assert row(unscoped, "cand_dirty_cdr3")["Developability risk"] == "High"

    scoped = run_main(scoped_dir, ["--regions", "CDR3"], data_path=data)
    clean = row(scoped, "cand_clean_cdr3")
    dirty = row(scoped, "cand_dirty_cdr3")
    assert clean["Developability risk"] == "None"
    assert clean["Developability cost"] == pytest.approx(0.0)
    assert dirty["Developability risk"] == "High"
    # CDR3 weight 1.5 x fixable weight 3.0
    assert dirty["Developability cost"] == pytest.approx(4.5)


def test_regions_multi_select(tmp_path):
    df = run_main(tmp_path, ["--regions", "CDR1,CDR3"], data_path=_parental_data(tmp_path))
    assert "CDR1 aa liabilities" in df.columns
    assert "CDR3 aa liabilities" in df.columns
    assert "FR1 aa liabilities" not in df.columns


def test_regions_is_case_and_whitespace_insensitive(tmp_path):
    df = run_main(tmp_path, ["--regions", " cdr3 , Cdr1 "], data_path=_parental_data(tmp_path))
    assert "CDR3 aa liabilities" in df.columns
    assert "CDR1 aa liabilities" in df.columns
    assert "FR1 aa liabilities" not in df.columns


def test_regions_unknown_name_is_ignored_not_fatal(tmp_path):
    """A stale region name degrades to 'scan what I recognise', never a failed run."""
    df = run_main(tmp_path, ["--regions", "CDR3,NOTAREGION"], data_path=_parental_data(tmp_path))
    assert "CDR3 aa liabilities" in df.columns
    assert "FR1 aa liabilities" not in df.columns


def test_regions_empty_value_falls_back_to_all(tmp_path):
    """Empty scope must mean 'no restriction', not 'restricted to nothing'."""
    df = run_main(tmp_path, ["--regions", ""], data_path=_parental_data(tmp_path))
    assert "CDR1 aa liabilities" in df.columns
    assert "FR1 aa liabilities" in df.columns


def test_regions_all_absent_from_input_falls_back_to_all(tmp_path):
    """FR2 is canonical, so it survives the unknown-name filter — but no FR2 column exists here.

    Reachable by keeping a selection while switching to a dataset that lacks those regions.
    """
    df = run_main(tmp_path, ["--regions", "FR2"], data_path=_parental_data(tmp_path))
    assert row(df, "cand_clean_cdr3")["Is Productive"] == "Pass"
    assert row(df, "cand_dirty_cdr3")["Developability risk"] == "High"
    for present in ("CDR1 aa liabilities", "CDR2 aa liabilities", "CDR3 aa liabilities", "FR1 aa liabilities"):
        assert present in df.columns


def test_regions_all_absent_reports_every_found_region(tmp_path):
    """The fallback must be visible to the Tengo side, which builds columns from this list."""
    out_regions = tmp_path / "regions.json"
    run_main(
        tmp_path,
        ["--regions", "FR2", "--output-regions-found", str(out_regions)],
        data_path=_parental_data(tmp_path),
    )
    assert json.loads(out_regions.read_text()) == ["FR1", "CDR1", "CDR2", "CDR3"]


def test_regions_partially_absent_still_narrows(tmp_path):
    """One satisfiable region keeps the restriction — the fallback is only for a fully dead scope."""
    df = run_main(tmp_path, ["--regions", "CDR3,FR2"], data_path=_parental_data(tmp_path))
    assert "CDR3 aa liabilities" in df.columns
    for absent in ("CDR1 aa liabilities", "CDR2 aa liabilities", "FR1 aa liabilities"):
        assert absent not in df.columns


# Path A fixture for the exported annotation track: one liability in CDR1 and a different one in
# CDR3, so scope has something to exclude and something to keep. Offsets match DATA_ANNOTATED.
ANN_SCOPE_SEQ = (
    "QVQLVQSGAEVKKPGASVKVSCKAS"  # FR1 (synthesized, 0+25)
    "GYTFDGY"  # CDR1 (25+7) — DG at 29
    "WVRQAPGK"  # not extracted (no segment)
    "ISPGRGIT"  # CDR2 (40+8) — clean
    "ARNTSKPT"  # not extracted (no segment)
    "CARYNGF"  # CDR3 (56+7) — NG at 60
)
ANN_SCOPE_KEY = "ann_two_regions"
CDR1_HIT = ("Isomerization (D[DGHST])", 29)
CDR3_HIT = ("Deamidation (N[GS])", 60)


def _annotated_scope_data(tmp_path: Path) -> Path:
    p = tmp_path / "annotated_scope.tsv"
    p.write_text(
        "clonotypeKey\tsequence aa\tannotations\n" + f"{ANN_SCOPE_KEY}\t{ANN_SCOPE_SEQ}\t1:P+7|2:14+8|3:1K+7\n"
    )
    return p


def _annotation_liability_hits(tmp_path: Path, extra_args: list[str]) -> tuple[list[tuple[str, int]], dict]:
    """Run Path A and decode the exported annotation into (liability name, start) pairs.

    Region segments (codes from the input label map) are filtered out; the rest is what the
    sequence viewer highlights.
    """
    label_map_file = tmp_path / "label_map.json"
    label_map_file.write_text(json.dumps(LABEL_MAP))
    out_map = tmp_path / "out_map.json"
    df = run_main(
        tmp_path,
        ["-m", str(label_map_file), "-o", str(out_map), *extra_args],
        data_path=_annotated_scope_data(tmp_path),
    )
    final_map = json.loads(out_map.read_text())
    hits = [
        (final_map.get(lab), start)
        for lab, start, _length in parse_annotations(row(df, ANN_SCOPE_KEY)["annotations"])
        if lab not in LABEL_MAP
    ]
    return sorted(hits, key=lambda h: h[1]), final_map


def test_annotation_track_unscoped_carries_every_region(tmp_path):
    """Baseline: with no scope both regions' liabilities are highlighted."""
    hits, _ = _annotation_liability_hits(tmp_path, [])
    assert hits == [CDR1_HIT, CDR3_HIT]


def test_regions_scopes_exported_annotation_track(tmp_path):
    """Scoping away the parental scaffold must not leave its liabilities painted on the sequence,
    here or in any downstream block consuming the annotation.
    """
    hits, final_map = _annotation_liability_hits(tmp_path, ["--regions", "CDR3"])
    assert hits == [CDR3_HIT]
    # A liability whose only occurrence was scoped away leaves no legend entry either.
    assert CDR1_HIT[0] not in final_map.values()


def test_regions_annotation_track_follows_scope_fallback(tmp_path):
    """An unsatisfiable scope widens to 'scan everything' — the annotation track widens with it,
    which is why the write-back happens after the scope decision rather than during extraction.
    """
    hits, _ = _annotation_liability_hits(tmp_path, ["--regions", "FR2"])
    assert hits == [CDR1_HIT, CDR3_HIT]


def test_regions_does_not_affect_is_productive(tmp_path):
    """Is Productive reads the whole-chain column, so region scope must not change it.

    clone_stop carries a stop codon outside CDR3; scoping to CDR3 must still fail it.
    """
    scoped = run_main(tmp_path, ["--regions", "CDR3"])
    assert row(scoped, "clone_stop")["Is Productive"] == "Fail"
    assert row(scoped, "clone_out_of_frame")["Is Productive"] == "Fail"
    assert row(scoped, "clone_clean")["Is Productive"] == "Pass"


# ---------------------------------------------------------------------------
# FR4
# ---------------------------------------------------------------------------

FR4_HEADER = "clonotypeKey\tCDR1 aa\tCDR2 aa\tCDR3 aa\tFR1 aa\tFR4 aa\n"
FR4_ROWS = (
    "fr4_germline\tGYTFAGY\tISPGRGIT\tCARYALD\tQVQLVQSGAEVKKPDPSVKVSCKAS\tWGQGTMVTVSS\n"
    "fr4_extra_cys\tGYTFAGY\tISPGRGIT\tCARYALD\tQVQLVQSGAEVKKPDPSVKVSCKAS\tWGQGTCVTVSS\n"
)


def _fr4_data(tmp_path: Path) -> Path:
    p = tmp_path / "fr4.tsv"
    p.write_text(FR4_HEADER + FR4_ROWS)
    return p


def test_fr4_gets_cysteine_rules_only(tmp_path):
    """Germline FR4 carries a Trp and a Met: motif rules are CDR-only, as for FR1-FR3.
    A cysteine is reported, as it already is for FR2/FR3, and reaches the global columns.
    """
    df = run_main(tmp_path, data_path=_fr4_data(tmp_path))
    clean = row(df, "fr4_germline")
    dirty = row(df, "fr4_extra_cys")
    assert clean["FR4 aa liabilities"] == "None"
    assert clean["Developability risk"] == "None"
    assert dirty["FR4 aa liabilities"] == "Extra Cysteines"
    assert dirty["FR4 aa risk"] == "High"
    assert dirty["Developability risk"] == "Very High"
    # FR4 weight 0.3 x hard_to_fix weight 8.0
    assert dirty["Developability cost"] == pytest.approx(2.4)


def test_fr4_scope_is_honoured_not_widened(tmp_path):
    """A dataset offering FR4 must accept FR4 as a scope instead of falling back to all regions."""
    out_regions = tmp_path / "regions.json"
    df = run_main(
        tmp_path,
        ["--regions", "FR4", "--output-regions-found", str(out_regions)],
        data_path=_fr4_data(tmp_path),
    )
    assert json.loads(out_regions.read_text()) == ["FR4"]
    assert "FR4 aa liabilities" in df.columns
    for absent in ("CDR1 aa liabilities", "CDR2 aa liabilities", "CDR3 aa liabilities", "FR1 aa liabilities"):
        assert absent not in df.columns


# The pre-existing-regions check is an all-must-be-present gate, not a filter. FR4 has no
# extraction fallback (the CDRs annotation maps only CDR1-3, from which FR1 is derived), so
# gating on it sends annotated inputs lacking FR4 down the extraction path, where the extracted
# fragments collide with the input's own columns of the same name.


def test_annotated_input_without_fr4_uses_preexisting_columns(tmp_path):
    label_map_file = tmp_path / "label_map.json"
    label_map_file.write_text(json.dumps(LABEL_MAP))
    header = "clonotypeKey\tsequence aa\tannotations\tCDR1 aa\tCDR2 aa\tCDR3 aa\tFR1 aa\tFR2 aa\tFR3 aa\n"
    seq = "QVQLVQSGAEVKKPDPSVKVSCKASGYTFAGYWVRQAPGKISPGRGITARNTSKPTLYLQCARYALD"
    data = tmp_path / "annotated_bulk.tsv"
    data.write_text(
        header
        + "\t".join(
            [
                "k1",
                seq,
                "1:P+7|2:14+8|3:1O+7",
                "GYTFAGY",
                "ISPGRGIT",
                "CARYALD",
                "QVQLVQSGAEVKKPDPSVKVSCKAS",
                "WVRQAPGK",
                "ARNTSKPTLYLQ",
            ]
        )
        + "\n"
    )
    df = run_main(tmp_path, ["-m", str(label_map_file)], data_path=data)
    assert "CDR3 aa liabilities" in df.columns
    assert row(df, "k1")["Is Productive"] == "Pass"


# ---------------------------------------------------------------------------
# Chain-asymmetric regions
# ---------------------------------------------------------------------------


def test_single_chain_values_carry_no_chain_label(tmp_path):
    """One chain in the input means the chain label carries no information, and a labelled value
    would not match the discreteValues the risk PColumns declare.
    """
    data = tmp_path / "single_chain.tsv"
    data.write_text(
        "clonotypeKey\tHeavy CDR3 aa\tHeavy FR1 aa\tHeavy FR4 aa\n"
        "one\tCARYALD\tQVQLVQSGAEVKKPDPSVKVSCKAS\tWGQGTCVTVSS\n"
    )
    r = row(run_main(tmp_path, data_path=data), "one")
    assert r["CDR3 aa liabilities"] == "None"
    assert r["CDR3 aa risk"] == "None"
    assert r["FR4 aa liabilities"] == "Extra Cysteines"
    assert r["FR4 aa risk"] == "High"


def test_region_on_one_chain_still_emits_combined_column(tmp_path):
    """The Tengo side declares "<region> aa liabilities" for every region in --output-regions-found,
    never chain-prefixed, so a one-sided region must still produce that name.
    """
    out_regions = tmp_path / "regions.json"
    data = tmp_path / "asym.tsv"
    data.write_text(
        "clonotypeKey\tHeavy CDR3 aa\tHeavy FR1 aa\tHeavy FR4 aa\tLight CDR3 aa\tLight FR1 aa\n"
        "asym\tCARYALD\tQVQLVQSGAEVKKPDPSVKVSCKAS\tWGQGTCVTVSS\tCARYALD\tQVQLVQSGAEVKKPDPSVKVSCKAS\n"
    )
    df = run_main(tmp_path, ["--output-regions-found", str(out_regions)], data_path=data)
    assert row(df, "asym")["FR4 aa liabilities"] == "Heavy: Extra Cysteines"
    assert "Heavy FR4 aa liabilities" not in df.columns
    for region in json.loads(out_regions.read_text()):
        assert f"{region} aa liabilities" in df.columns
        assert f"{region} aa risk" in df.columns


# ---------------------------------------------------------------------------
# Single-cell region columns
# ---------------------------------------------------------------------------

SC_CHAIN_SEQ = "QVQLVQSGAEVKKPDPSVKVSCKASGYTFAGYWVRQAPGKISPGRGITARNTSKPTLYLQCARYALD"
SC_ANN = "1:P+7|2:14+8|3:1O+7"
SC_REGIONS = {
    "CDR1 aa": "GYTFAGY",
    "CDR2 aa": "ISPGRGIT",
    "CDR3 aa": "CARYALD",
    "FR1 aa": "QVQLVQSGAEVKKPDPSVKVSCKAS",
    "FR2 aa": "WVRQAPGK",
    "FR3 aa": "ARNTSKPTLYLQ",
    "FR4 aa": "WGQGTMVTVSS",
}


def _sc_table(tmp_path: Path, regions: dict, name: str = "sc_regions.tsv") -> Path:
    """Mirrors the single-cell table the workflow builds: per-chain whole sequence, CDRs
    annotation, and the per-chain region columns.
    """
    header, values = ["clonotypeKey"], ["k1"]
    for chain in ("Heavy", "Light"):
        header += [f"{chain}  sequence aa", f"{chain} annotations"]
        values += [SC_CHAIN_SEQ, SC_ANN]
        header += [f"{chain} {region}" for region in regions]
        values += list(regions.values())
    p = tmp_path / name
    p.write_text("\t".join(header) + "\n" + "\t".join(values) + "\n")
    return p


def test_sc_region_columns_cover_every_region(tmp_path):
    """Single-cell input carries all seven regions as columns, as bulk does, so all seven are
    scanned instead of only the four the CDRs annotation can yield.
    """
    label_map_file = tmp_path / "label_map.json"
    label_map_file.write_text(json.dumps(LABEL_MAP))
    out_regions = tmp_path / "regions.json"
    df = run_main(
        tmp_path,
        ["-m", str(label_map_file), "--output-regions-found", str(out_regions)],
        data_path=_sc_table(tmp_path, SC_REGIONS),
    )
    assert json.loads(out_regions.read_text()) == ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]
    for region in ("FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"):
        assert f"{region} aa liabilities" in df.columns
        assert f"{region} aa risk" in df.columns
    # cdr3SeqPrefixed: a fed CDR3 column keeps its chain prefix, and the Tengo side declares it so.
    assert "Heavy CDR3 aa" in df.columns
    assert "Light CDR3 aa" in df.columns


def test_sc_partial_region_columns_do_not_collide_with_extraction(tmp_path):
    """Regions the input lacks are still extracted from the annotation. The extracted copy of a
    region the input does carry must not be added twice — the horizontal concat rejects it.
    """
    label_map_file = tmp_path / "label_map.json"
    label_map_file.write_text(json.dumps(LABEL_MAP))
    out_regions = tmp_path / "regions.json"
    partial = {"CDR3 aa": "CARYALD", "FR4 aa": "WGQGTCVTVSS"}
    df = run_main(
        tmp_path,
        ["-m", str(label_map_file), "--output-regions-found", str(out_regions)],
        data_path=_sc_table(tmp_path, partial, name="sc_partial.tsv"),
    )
    assert json.loads(out_regions.read_text()) == ["FR1", "CDR1", "CDR2", "CDR3", "FR4"]
    assert row(df, "k1")["FR4 aa liabilities"] == "Heavy: Extra Cysteines | Light: Extra Cysteines"
    assert row(df, "k1")["CDR1 aa liabilities"] == "Heavy: None | Light: None"


def test_sc_single_chain_fed_region_is_not_extracted_again(tmp_path):
    """On single-chain input the extracted copy is unprefixed while the input's own column is not,
    so a name check cannot pair them. The region must still be scanned once, from the input's
    column, under the unprefixed name the Tengo side declares.
    """
    label_map_file = tmp_path / "label_map.json"
    label_map_file.write_text(json.dumps(LABEL_MAP))
    out_regions = tmp_path / "regions.json"
    data = tmp_path / "sc_one_chain.tsv"
    data.write_text(
        "clonotypeKey\tHeavy  sequence aa\tHeavy annotations\tHeavy CDR3 aa\tHeavy FR4 aa\n"
        f"k1\t{SC_CHAIN_SEQ}\t{SC_ANN}\tCARYALD\tWGQGTCVTVSS\n"
    )
    df = run_main(
        tmp_path,
        ["-m", str(label_map_file), "--output-regions-found", str(out_regions)],
        data_path=data,
    )
    assert json.loads(out_regions.read_text()) == ["FR1", "CDR1", "CDR2", "CDR3", "FR4"]
    # One CDR3 scan, from the fed column, and no second unprefixed copy of it.
    assert "Heavy CDR3 aa liabilities" not in df.columns
    assert "CDR3 aa" not in df.columns
    assert "Heavy CDR3 aa" in df.columns
    r = row(df, "k1")
    assert r["CDR3 aa liabilities"] == "None"
    assert r["FR4 aa liabilities"] == "Extra Cysteines"
    # The regions the input does not carry are still extracted from the annotation.
    assert r["CDR1 aa liabilities"] == "None"


def test_unscannable_input_fails_instead_of_reporting_clean(tmp_path):
    """A table whose only sequence column is neither a region nor a CDRs annotation cannot be
    scanned, and blank global columns would read as a clean result.
    """
    data = tmp_path / "whole_chain_only.tsv"
    data.write_text("clonotypeKey\tHeavy  sequence aa\nk1\tQVQLVQSGAEVKKPGASVKVSCKASCARMGDFWGQGT\n")
    with pytest.raises(SystemExit):
        run_main(tmp_path, data_path=data)


# Same shape as SC_REGIONS but with a CDR3 that actually carries a liability, so the annotation
# has something to record. SC_ANN offsets are unchanged — CDR3 is still 7 aa at 60.
SC_CHAIN_SEQ_HIT = SC_CHAIN_SEQ[:60] + "CARYNGF"
SC_REGIONS_HIT = {**SC_REGIONS, "CDR3 aa": "CARYNGF"}


def _sc_table_hit(tmp_path: Path) -> Path:
    header, values = ["clonotypeKey"], ["k1"]
    for chain in ("Heavy", "Light"):
        header += [f"{chain}  sequence aa", f"{chain} annotations"]
        values += [SC_CHAIN_SEQ_HIT, SC_ANN]
        header += [f"{chain} {region}" for region in SC_REGIONS_HIT]
        values += list(SC_REGIONS_HIT.values())
    p = tmp_path / "sc_regions_hit.tsv"
    p.write_text("\t".join(header) + "\n" + "\t".join(values) + "\n")
    return p


def test_sc_fed_region_columns_still_annotate_liabilities(tmp_path):
    """Feeding every region as its own column must not switch off the annotation write-back.

    The fed columns are what the results table scans, but the annotation track is the only record
    of *where* each liability sits, and only the extraction path writes it. Short-circuiting that
    path when the input already supplies every region left the track carrying region markers only,
    silently: the table stayed correct while the sequence viewer lost every highlight.
    """
    label_map_file = tmp_path / "label_map.json"
    label_map_file.write_text(json.dumps(LABEL_MAP))
    out_map = tmp_path / "out_map.json"
    df = run_main(
        tmp_path,
        ["-m", str(label_map_file), "-o", str(out_map)],
        data_path=_sc_table_hit(tmp_path),
    )
    r = row(df, "k1")

    hits = [
        (lab, start)
        for lab, start, _length in parse_annotations(r["Heavy annotations"])
        if lab not in LABEL_MAP
    ]
    assert hits, f"annotation carries no liability entries: {r['Heavy annotations']}"

    final_map = json.loads(out_map.read_text())
    assert "Deamidation (N[GS])" in final_map.values()

    # The fed columns are still what gets scanned, and extraction adds no duplicate of them.
    assert "Deamidation (N[GS])" in r["CDR3 aa liabilities"]
    assert len(set(df.columns)) == len(df.columns)
