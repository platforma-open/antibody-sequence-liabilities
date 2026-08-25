# @platforma-open/milaboratories.antibody-sequence-liabilities.model

## 6.1.0

### Minor Changes

- adb3cb8: Add a "Regions to scan" selector that restricts liability detection to chosen regions

  Candidates whose parental scaffold carries known-good liabilities were all scoring High on
  Developability risk, leaving no way to rank them by the region actually being engineered.
  Selecting regions (e.g. CDR3, or the CDRs) now scans only those: their per-region columns are
  the only ones emitted, and Developability risk and cost are computed from them alone.

  The scope reaches the exported sequence annotation too: liabilities found in regions left out
  are no longer highlighted in the sequence viewer or passed to downstream blocks, so the
  highlighted positions always match what the results table reports.

  Leaving the selector empty scans every region, which is the previous behaviour — existing
  projects are unaffected and their cached results still match.

  A selection left in place while switching to a dataset that has none of those regions also
  falls back to scanning everything, rather than being honoured as "restricted to nothing" —
  that would exclude every analysis column, disabling liability calculation and leaving
  Is Productive, Structural liabilities and Developability risk/cost empty. The UI warns when
  the selection cannot be applied. A selection that is only partly present still narrows the
  scan to the regions that are there.

  Is Productive remains whole-molecule: stop-codon and out-of-frame detection still covers
  regions left out of the scope.

  Regions are now ordered biologically (FR1, CDR1, FR2, CDR2, FR3, CDR3, FR4), changing the
  per-region table column order and the segment order inside `Sequence liabilities summary`.

  The results table moved from createPlDataTableV2 to V3 to ensure stale sorts are dropped.

- 7bf8c3a: Scan repertoire input per region when it carries located regions

  A synthetic-repertoire-profiler dataset was always scanned as one whole sequence, even when the
  run located FR1-FR4/CDR1-3, because the modality was read from the producer's run-id stamp rather
  than from what the dataset actually offers. Such input now takes the antibody path: the region
  selector appears, the antibody rule set is offered, and a region scope is honoured. Runs whose
  region set has no CDR3 — and runs with no regions at all — are unchanged.

### Patch Changes

- 258ffde: Stop offering regions a CDR3-only library cannot scan

  "Regions to scan" listed FR1, CDR1, CDR2 and CDR3 for libraries assembled by CDR3, where CDR3 is
  the only region present. Any annotation column was taken as evidence that regions could be
  extracted from it, but a CDR3-assembled library carries a Segments annotation (V/D/J/C
  boundaries), not the CDRs annotation regions are extracted from. Only a CDRs annotation counts
  now, so these libraries offer CDR3 alone.

  Selecting one of the phantom regions scanned everything instead, without the warning that
  normally appears when a selection cannot be applied.

## 6.0.4

### Patch Changes

- f42a57c: Support bare antibody sets keyed on pl7.app/variantKey

  Three producers now key on `pl7.app/variantKey` and only the run-id in the axis domain says
  which: peptide-extraction, synthetic-repertoire-profiler, and import-vdj-data's bare antibody
  sets. Both the workflow and the model decided modality from the axis name alone, so a bare
  antibody set was treated as peptide — the run died on "No peptide aa sequence found on
  variantKey axis", and the model selected the peptide liability list and accepted a custom
  liability with no regions selected.

  Such a set also carries both chains in one frame, separated by the
  `pl7.app/vdj/scClonotypeChain` column domain, rather than in separate frames. Whether the
  sequence table is built per chain now follows that domain instead of the key axis being
  `pl7.app/vdj/scClonotypeKey`, so both chains are scanned. Columns are labelled Heavy/Light,
  which the calculation script already reads: it analyses each chain and merges the findings into
  one summary per region.

  Columns are prefixed Heavy/Light only when both chains are present.
  `_combine_heavy_light_prefixed_columns` merges the per-chain columns back into one per region by
  intersecting the Heavy and Light base names, so a single-chain set would keep its prefixes and
  the run would fail on a missing `CDR1 aa liabilities`. A one-chain set is shaped like a bulk one
  and is now labelled like one.

  The numbering scheme is now read from the located region columns as well as the whole variable
  domain. import-vdj-data stamps it on the regions, so it arrived empty — and with no scheme the
  detector expects a cysteine at CDR3 position 0, reporting `Missing Cysteines` on every record.
  That is a structural liability, so an entire 1,243-antibody panel scored Non-Developable.

  Peptide, amplicon, bulk and single-cell inputs are unaffected.

## 6.0.3

### Patch Changes

- 187cc98: Support `synthetic-repertoire-profiler` (amplicon) variant datasets:

  - New `"amplicon"` modality. The model recognizes the profiler's `pl7.app/variantKey` axis (axis domain `pl7.app/repertoire/extractionRunId`) as amplicon, distinct from peptide-extraction's `pl7.app/peptide/extractionRunId`. Previously such inputs entered the peptide branch and panicked (no `feature: "peptide"` sequence column found).
  - Amplicon runs the same whole-sequence flat liability scan as peptide mode, reading the whole-variant amino-acid sequence (`pl7.app/feature: "amplicon-sequence"`).
  - The echoed sequence output column is labeled with the `amplicon-sequence` feature (label "Sequence aa") instead of `peptide` / "Peptide aa", so it attaches to the correct entity.
  - The UI treats amplicon as a whole-sequence mode: it hides the per-region selector for custom liabilities and shares the peptide predefined rule set.

  Per-region liabilities for amplicon (using the profiler's region subsequence columns) are out of scope here — whole-sequence descriptors only.

## 6.0.2

### Patch Changes

- 9b881d8: update dependencies

## 6.0.1

### Patch Changes

- 169fc9c: migrate to block model v3

## 6.0.0

### Major Changes

- 853c958: Support peptides

## 5.1.0

### Minor Changes

- b4901a2: Improved performance on large datasets

## 5.0.0

### Major Changes

- 5dff4dc: Replace "Liabilities risk" column with fixability-aware scoring

  **Breaking change:** The global `pl7.app/vdj/liabilitiesRisk` PColumn (no domain) is removed. Existing projects that wired this column into Lead Selection will need to reconfigure their filters to use the new columns.

  Four new output columns replace the old single risk column:

  - **Is Productive** (`Pass`/`Fail`) — fails only on disqualifying sequence errors (stop codons, frameshifts). Default Lead Selection filter: `["Pass"]`.
  - **Structural liabilities** (`None`/`Present`) — present when missing or extra cysteines are found. Default Lead Selection filter: `["None"]`.
  - **Developability risk** (`None`/`Low`/`Medium`/`High`) — maximum risk across fixable and easily-fixable liabilities only. Default Lead Selection filter: `["None","Low","Medium"]`.
  - **Developability score** (continuous float) — engineering burden score (`Σ fixability_weight × region_weight`); lower is easier to fix. Exposed as a ranking criterion only (increasing order).

  Per-region risk columns now reflect fixable liabilities only (structural and disqualifying liabilities surface in the global columns). Per-region risk columns gain `pl7.app/isScore: "true"` making them discoverable as optional Lead Selection filters.

  Custom liabilities can be defined in the settings panel: name, regex pattern, risk level, fixability class (Easy fix / Fixable / Hard to fix), and regions. Custom entries can be exported and imported as JSON. A "Use predefined liabilities" checkbox allows running custom-only detection.

  "Integrin binding" is now disabled by default.

## 4.3.1

### Patch Changes

- b9600e4: Set default block label, use sdk strings for status messages

## 4.3.0

### Minor Changes

- 04076d8: adjusted coordinates for numbering schemes, dependencies updates

## 4.2.0

### Minor Changes

- 8d24e52: Expected cysteins position in light chain is corrected, dependencies updates

## 4.1.0

### Minor Changes

- ee5a48c: Support custom block title

## 4.0.0

### Major Changes

- 4a02933: Show running state for tables and graphs, migrate to new project template

## 3.1.2

### Patch Changes

- 9c55f5a: technical release
- 3766c4a: technical release
- 1c704a8: technical release
- 061677e: technical release

## 3.1.1

### Patch Changes

- 9d7983b: Full SDK update

## 3.1.0

### Minor Changes

- fda18c5: support empty input

## 3.0.3

### Patch Changes

- d5abe27: Migrate to use updated PlAgDataTableV2

## 3.0.2

### Patch Changes

- 0db0703: SDK Upgrade & Code migration

## 3.0.1

### Patch Changes

- 47fe485: Add columns manager and filters

## 3.0.0

### Major Changes

- c96e10a: fragments extraction from assemblingFeature, annotations added

### Minor Changes

- 8528363: Allow liability selection

## 2.1.0

### Minor Changes

- 1b7c43f: query all available frameworks and cdrs

## 2.0.0

### Major Changes

- 5158f1f: Antibody Liabilities Block
