#!/usr/bin/env python3
"""Peptide-mode entry point for sequence-liability scanning.

Pipeline differences vs the antibody main.py:
- One amino-acid sequence per row keyed by `variantKey`. No regions, no chains.
- No CDR boundary annotations; regex rules apply to the whole sequence.
- No Cys-position logic.
- Tryptophan oxidation rule is applied uniformly (no terminal-CDR3 exception).
- Disqualifying patterns ("Contains stop codon", "Out of frame") are not
  evaluated — peptide-extraction's filterInvalidPeptides default removes
  invalid peptides upstream.
- Output schema is flat: 3 globals (summary, risk, cost). No per-region
  columns, no Is Productive, no Structural liabilities.
- developability_cost is a flat sum of fixability weights — no region-weight
  term (no regions to weight).
"""
import argparse
import json
import re
import sys

import polars as pl

from definitions import (
    FIXABILITY_WEIGHTS,
    ORIG_REGEX_LIABILITIES,
    PEPTIDE_LIABILITY_NAMES,
    _ENGINEERING_FIXABILITIES,
)


_RISK_ORDER = {"None": 0, "Low": 1, "Medium": 2, "High": 3}
_LEVEL_TO_RISK = {v: k for k, v in _RISK_ORDER.items()}


def _build_active_rules(
    use_predefined: bool,
    disabled_predefined: list[str],
    custom_liabilities: list[dict],
) -> dict[str, dict]:
    """Return name → {pattern (compiled regex), risk_level, fixability}.

    Predefined rules are filtered to PEPTIDE_LIABILITY_NAMES (Phase 1 set);
    user-disabled names are removed; custom liabilities (validated regex,
    no `regions` field) are added.
    """
    rules: dict[str, dict] = {}

    if use_predefined:
        disabled = set(disabled_predefined or [])
        for name in PEPTIDE_LIABILITY_NAMES:
            if name in disabled:
                continue
            if name not in ORIG_REGEX_LIABILITIES:
                continue  # safety: skip if name was removed from definitions
            pattern, risk, fix = ORIG_REGEX_LIABILITIES[name]
            rules[name] = {
                "pattern": re.compile(pattern),
                "risk_level": risk,
                "fixability": fix,
            }

    for c in (custom_liabilities or []):
        name = c.get("name")
        pat = c.get("pattern")
        risk = c.get("riskLevel")
        fix = c.get("fixability")
        if not (name and pat and risk and fix):
            print(f"peptide_main: skipping invalid custom liability {c!r}", file=sys.stderr)
            continue
        if name in rules:
            print(f"peptide_main: custom liability '{name}' collides with predefined; skipping", file=sys.stderr)
            continue
        try:
            compiled = re.compile(pat)
        except re.error as e:
            print(f"peptide_main: invalid regex for '{name}': {e}; skipping", file=sys.stderr)
            continue
        rules[name] = {
            "pattern": compiled,
            "risk_level": risk,
            "fixability": fix,
        }

    return rules


def _scan_sequence(seq: str, rules: dict[str, dict]) -> list[tuple[str, int, str, str]]:
    """Return list of (name, position_1based, risk_level, fixability) for all matches.

    Empty / non-string sequences return [] (caller treats as "Unknown").
    """
    if not isinstance(seq, str) or not seq.strip():
        return []
    matches: list[tuple[str, int, str, str]] = []
    for name, defn in rules.items():
        for m in defn["pattern"].finditer(seq):
            matches.append((name, m.start() + 1, defn["risk_level"], defn["fixability"]))
    return matches


def _summarize(matches: list[tuple[str, int, str, str]]) -> str:
    """Build the human-readable summary string.

    Format: 'Deamidation (N[GS]) at pos 4; Tryptophan Oxidation (W) at pos 12'.
    Sorted by (name, position) for stable output.
    """
    if not matches:
        return "None"
    parts = sorted(
        f"{name} at pos {pos}" for name, pos, _r, _f in matches
    )
    return "; ".join(parts)


def _classify_risk(matches: list[tuple[str, int, str, str]]) -> str:
    """Max risk level across engineering-fixable matches.

    Mirrors the antibody classify_developability_risk semantics: structural,
    hard_to_fix, and disqualifying liabilities are excluded from the per-row
    risk score (they're tracked by other columns in the antibody pipeline;
    for peptides those columns don't exist, so those liabilities just don't
    contribute to risk here).
    """
    current_max = 0
    for _name, _pos, risk, fix in matches:
        if fix not in _ENGINEERING_FIXABILITIES:
            continue
        level = _RISK_ORDER.get(risk, 0)
        if level > current_max:
            current_max = level
        if current_max == 3:
            return "High"
    return _LEVEL_TO_RISK[current_max]


def _compute_cost(matches: list[tuple[str, int, str, str]]) -> float:
    """Flat sum of fixability weights — no region-weight term.

    Disqualifying patterns are excluded (weight 0 in FIXABILITY_WEIGHTS already,
    but explicit skip is clearer).
    """
    total = 0.0
    for _name, _pos, _risk, fix in matches:
        if fix == "disqualifying":
            continue
        total += FIXABILITY_WEIGHTS.get(fix, 0.0)
    return total


def run(
    input_tsv: str,
    output_tsv: str,
    use_predefined: bool,
    disabled_predefined: list[str],
    custom_liabilities: list[dict],
) -> None:
    df = pl.read_csv(input_tsv, separator="\t")

    if "variantKey" not in df.columns or "sequence aa" not in df.columns:
        raise ValueError(
            f"peptide_main: expected columns 'variantKey' and 'sequence aa'; got {df.columns}"
        )

    rules = _build_active_rules(use_predefined, disabled_predefined, custom_liabilities)

    summaries: list[str] = []
    risks: list[str] = []
    costs: list[float] = []
    for seq in df["sequence aa"].to_list():
        matches = _scan_sequence(seq if isinstance(seq, str) else "", rules)
        summaries.append(_summarize(matches))
        risks.append(_classify_risk(matches))
        costs.append(_compute_cost(matches))

    # Echo the peptide aa sequence to the output so the table view shows it
    # alongside the liability columns. Renamed to "peptide_aa" (no space) for
    # cleaner TSV column naming.
    out = df.select(
        "variantKey",
        pl.col("sequence aa").alias("peptide_aa"),
    ).with_columns([
        pl.Series("liabilities_summary", summaries, dtype=pl.Utf8),
        pl.Series("developability_risk", risks, dtype=pl.Utf8),
        pl.Series("developability_cost", costs, dtype=pl.Float64),
    ])
    out.write_csv(output_tsv, separator="\t")


def _load_json_list(path: str | None, label: str) -> list:
    """Read a JSON file expected to contain a list. Returns [] when the path
    is empty or None (the workflow always writes a file with at least '[]').
    """
    if not path:
        return []
    with open(path) as f:
        value = json.load(f)
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a JSON list, got {type(value).__name__}")
    return value


def main():
    parser = argparse.ArgumentParser(description="Peptide sequence-liability scanner")
    parser.add_argument("--input_tsv", required=True)
    parser.add_argument("--output_tsv", required=True)
    parser.add_argument(
        "--use_predefined_liabilities",
        action="store_true",
        help="Apply the predefined PEPTIDE_LIABILITY_NAMES rule set (filtered by --disabled_predefined_liabilities)",
    )
    parser.add_argument(
        "--disabled_predefined_liabilities",
        default=None,
        help="Path to a JSON file containing an array of predefined liability names to disable.",
    )
    parser.add_argument(
        "--custom_liabilities",
        default=None,
        help="Path to a JSON file containing an array of {name, pattern, riskLevel, fixability} objects.",
    )
    args = parser.parse_args()

    disabled = _load_json_list(args.disabled_predefined_liabilities, "--disabled_predefined_liabilities")
    custom = _load_json_list(args.custom_liabilities, "--custom_liabilities")

    run(
        input_tsv=args.input_tsv,
        output_tsv=args.output_tsv,
        use_predefined=args.use_predefined_liabilities,
        disabled_predefined=disabled,
        custom_liabilities=custom,
    )


if __name__ == "__main__":
    main()
