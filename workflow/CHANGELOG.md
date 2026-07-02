# @platforma-open/milaboratories.antibody-sequence-liabilities.workflow

## 6.0.5

### Patch Changes

- 187cc98: Support `synthetic-repertoire-profiler` (amplicon) variant datasets:

  - New `"amplicon"` modality. The model recognizes the profiler's `pl7.app/variantKey` axis (axis domain `pl7.app/repertoire/extractionRunId`) as amplicon, distinct from peptide-extraction's `pl7.app/peptide/extractionRunId`. Previously such inputs entered the peptide branch and panicked (no `feature: "peptide"` sequence column found).
  - Amplicon runs the same whole-sequence flat liability scan as peptide mode, reading the whole-variant amino-acid sequence (`pl7.app/feature: "amplicon-sequence"`).
  - The echoed sequence output column is labeled with the `amplicon-sequence` feature (label "Sequence aa") instead of `peptide` / "Peptide aa", so it attaches to the correct entity.
  - The UI treats amplicon as a whole-sequence mode: it hides the per-region selector for custom liabilities and shares the peptide predefined rule set.

  Per-region liabilities for amplicon (using the profiler's region subsequence columns) are out of scope here — whole-sequence descriptors only.

## 6.0.4

### Patch Changes

- Updated dependencies [2f3f53c]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@6.0.3

## 6.0.3

### Patch Changes

- fa708ec: Revert namespacing of output liability columns and the trace step by a content hash of the liability configuration: the column domain and trace step id are keyed on the per-block blockId again. The config-hash helper is removed and blockId is threaded back through the process templates.

  The independent re-run deduplication fixes are kept: disabledPredefinedLiabilities is still sorted to a canonical order (slices.sortUnique) inside normalize(), the annotation mapping is still encoded with canonical.encode (key-sorted, deterministic) so identical mappings produce identical column specs across runs, and mem is still passed to the calc renders via metaInputs so it stays out of the content key.

- Updated dependencies [0a047a7]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@6.0.2

## 6.0.2

### Patch Changes

- 55fd24e: Namespace output liability columns and the trace step by a hash of the liability configuration instead of the per-block blockId. Identical configs across blocks and projects now produce the same column identity and dedupe downstream instead of invalidating caches. The hash is derived inside the process templates from their arguments, and mem is passed to the liabilities-calc renders via metaInputs so it stays out of the content key.

  Also sort the disabledPredefinedLiabilities list to a canonical order (slices.sortUnique) inside normalize(). The list is a set, but it reached the liabilities-calc render input, the written disabled-predefined-liabilities.json file, and the config hash as a raw array; the backend canonicalizes map keys on the resource CID but not array element order, so an unsorted list made semantically identical configs hash differently and re-run the calc across blocks/projects. Verified: 4 blocks across 2 projects now collapse to a single calc run.

- ef5ba21: update sdk

## 6.0.1

### Patch Changes

- f58bc23: Republish calc-script to ship the per-region risk aggregation fix.
- Updated dependencies [f58bc23]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@6.0.1

## 6.0.0

### Major Changes

- 853c958: Support peptides

### Patch Changes

- Updated dependencies [853c958]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@6.0.0

## 5.1.0

### Minor Changes

- b4901a2: Improved performance on large datasets

## 5.0.1

### Patch Changes

- Updated dependencies [6ca5696]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@5.0.0

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

## 4.3.0

### Minor Changes

- 04076d8: adjusted coordinates for numbering schemes, dependencies updates

### Patch Changes

- Updated dependencies [04076d8]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@4.2.0

## 4.2.0

### Minor Changes

- 8d24e52: Expected cysteins position in light chain is corrected, dependencies updates

### Patch Changes

- Updated dependencies [8d24e52]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@4.1.0

## 4.1.0

### Minor Changes

- ee5a48c: Support custom block title

## 4.0.0

### Major Changes

- 4a02933: Show running state for tables and graphs, migrate to new project template

### Patch Changes

- Updated dependencies [4a02933]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@4.0.0

## 3.4.10

### Patch Changes

- 0a15327: Support parquet format

## 3.4.9

### Patch Changes

- 9c55f5a: technical release
- 3766c4a: technical release
- 1c704a8: technical release
- 061677e: technical release
- Updated dependencies [9c55f5a]
- Updated dependencies [3766c4a]
- Updated dependencies [1c704a8]
- Updated dependencies [061677e]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@3.2.7

## 3.4.8

### Patch Changes

- Updated dependencies [fac8424]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@3.2.6

## 3.4.7

### Patch Changes

- Updated dependencies [929381c]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@3.2.5

## 3.4.6

### Patch Changes

- Updated dependencies [835d47e]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@3.2.4

## 3.4.5

### Patch Changes

- Updated dependencies [4f8afc2]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@3.2.3

## 3.4.4

### Patch Changes

- Updated dependencies [9d7983b]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@3.2.2

## 3.4.3

### Patch Changes

- a32a024: Update sdk to fix issue with broken python venv

## 3.4.2

### Patch Changes

- Updated dependencies [8c89b35]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@3.2.1

## 3.4.1

### Patch Changes

- Updated dependencies [fda18c5]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@3.2.0

## 3.4.0

### Minor Changes

- 6d674ed: Add blockId to domain of exported cols, improve trace annotation to be able distinguish between exports of different liabilities blocks

## 3.3.1

### Patch Changes

- Updated dependencies [96899ef]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@3.1.3

## 3.3.0

### Minor Changes

- 7c52fa8: support batch system

## 3.2.0

### Minor Changes

- 2ca30b9: Migrate to pframes.tsvFileBuilder()

## 3.1.2

### Patch Changes

- 0db0703: SDK Upgrade & Code migration
- Updated dependencies [0db0703]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@3.1.2

## 3.1.1

### Patch Changes

- Updated dependencies [b2e27c6]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@3.1.1

## 3.1.0

### Minor Changes

- de16445: Liabilities summary column

### Patch Changes

- Updated dependencies [de16445]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@3.1.0

## 3.0.0

### Major Changes

- c96e10a: fragments extraction from assemblingFeature, annotations added

### Minor Changes

- 8528363: Allow liability selection

### Patch Changes

- Updated dependencies [c96e10a]
- Updated dependencies [8528363]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@3.0.0

## 2.1.0

### Minor Changes

- 1b7c43f: query all available frameworks and cdrs

## 2.0.0

### Major Changes

- 5158f1f: Antibody Liabilities Block

### Patch Changes

- Updated dependencies [5158f1f]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@2.0.0
