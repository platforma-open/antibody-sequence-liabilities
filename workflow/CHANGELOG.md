# @platforma-open/milaboratories.antibody-sequence-liabilities.workflow

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
