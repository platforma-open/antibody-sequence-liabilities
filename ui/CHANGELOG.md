# @platforma-open/milaboratories.antibody-sequence-liabilities.ui

## 5.0.1

### Patch Changes

- 32c76f3: Add docs link to import tooltip

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

### Patch Changes

- Updated dependencies [5dff4dc]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@5.0.0

## 4.3.1

### Patch Changes

- Updated dependencies [b9600e4]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@4.3.1

## 4.3.0

### Minor Changes

- 04076d8: adjusted coordinates for numbering schemes, dependencies updates

### Patch Changes

- Updated dependencies [04076d8]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@4.3.0

## 4.2.0

### Minor Changes

- 8d24e52: Expected cysteins position in light chain is corrected, dependencies updates

### Patch Changes

- Updated dependencies [8d24e52]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@4.2.0

## 4.1.1

### Patch Changes

- 6579b7d: Labels migration

## 4.1.0

### Minor Changes

- ee5a48c: Support custom block title

### Patch Changes

- Updated dependencies [ee5a48c]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@4.1.0

## 4.0.0

### Major Changes

- 4a02933: Show running state for tables and graphs, migrate to new project template

### Patch Changes

- Updated dependencies [4a02933]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@4.0.0

## 3.1.3

### Patch Changes

- 9c55f5a: technical release
- 3766c4a: technical release
- 1c704a8: technical release
- 061677e: technical release
- Updated dependencies [9c55f5a]
- Updated dependencies [3766c4a]
- Updated dependencies [1c704a8]
- Updated dependencies [061677e]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@3.1.2

## 3.1.2

### Patch Changes

- 65d4d91: Fix settings button

## 3.1.1

### Patch Changes

- Updated dependencies [9d7983b]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@3.1.1

## 3.1.0

### Minor Changes

- fda18c5: support empty input

### Patch Changes

- Updated dependencies [fda18c5]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@3.1.0

## 3.0.3

### Patch Changes

- d5abe27: Migrate to use updated PlAgDataTableV2
- Updated dependencies [d5abe27]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@3.0.3

## 3.0.2

### Patch Changes

- 0db0703: SDK Upgrade & Code migration
- Updated dependencies [0db0703]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@3.0.2

## 3.0.1

### Patch Changes

- 47fe485: Add columns manager and filters
- Updated dependencies [47fe485]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@3.0.1

## 3.0.0

### Major Changes

- c96e10a: fragments extraction from assemblingFeature, annotations added

### Minor Changes

- 8528363: Allow liability selection

### Patch Changes

- Updated dependencies [c96e10a]
- Updated dependencies [8528363]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@3.0.0

## 2.1.0

### Minor Changes

- 1b7c43f: query all available frameworks and cdrs

### Patch Changes

- Updated dependencies [1b7c43f]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@2.1.0

## 2.0.0

### Major Changes

- 5158f1f: Antibody Liabilities Block

### Patch Changes

- Updated dependencies [5158f1f]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@2.0.0
