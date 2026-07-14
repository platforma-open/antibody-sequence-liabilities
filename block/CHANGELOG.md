# @platforma-open/milaboratories.antibody-sequence-liabilities

## 5.0.11

### Patch Changes

- 386b7f5: Fix crash on heavy-only single-cell (VHH) input. The single-cell output now declares per-chain sequence/annotation columns only for the chains actually present, so heavy-only data no longer fails with `ColumnNotFoundError: unable to find column "Heavy CDR3 aa"`. Single-chain single-cell is fixed for the non-scFv (annotation-extraction) path; scFv single-chain input remains a separate known issue (its region-liability columns stay chain-prefixed).
- Updated dependencies [386b7f5]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@6.0.6

## 5.0.10

### Patch Changes

- Updated dependencies [187cc98]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@6.0.3
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@6.0.5
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@6.0.4

## 5.0.9

### Patch Changes

- 43391db: Publish to the stable channel by default — remove the `--unstable` flag from the block's publish script.

## 5.0.8

### Patch Changes

- @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@6.0.4

## 5.0.7

### Patch Changes

- Updated dependencies [fa708ec]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@6.0.3

## 5.0.6

### Patch Changes

- Updated dependencies [55fd24e]
- Updated dependencies [ef5ba21]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@6.0.2

## 5.0.5

### Patch Changes

- Updated dependencies [f58bc23]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@6.0.1

## 5.0.4

### Patch Changes

- c02e2aa: Fix: per-region "{region} Risk" columns now reflect any matching liability, not just engineering-fixable ones.

  Previously, when a region matched a `hard_to_fix` or `structural` liability (e.g. `Extra Cysteines`, or a custom liability with fixability `Hard to fix`), the corresponding `{region} Risk` column reported `None`, even though `{region} Liabilities` listed the liability. The two columns now agree: `{region} Risk` is the worst `riskLevel` of any non-disqualifying liability detected in that region.

  The spec at `docs/text/work/projects/sequence-liability-fixability-scoring/README.md:126` listed both behaviors as defensible and deferred the call to the implementor. The original v4.0.0 implementation picked Option A (engineering-only); this release switches to Option B (all non-disqualifying).

  `Developability risk` gains two new top-level values that fold the structural-liability signal into this column:

  - `hard_to_fix` liabilities (e.g. `Extra Cysteines`, custom liabilities marked "Hard to fix") → `Very High`
  - `structural` liabilities (e.g. `Missing Cysteines`) → `Non-Developable`
  - Both present in the same row → `Non-Developable` wins

  The discrete scale becomes `[None, Low, Medium, High, Very High, Non-Developable]`. Default cutoff stays `[None, Low, Medium]`, so High, Very High, and Non-Developable are all filtered out by default — readers no longer need to cross-reference `Structural liabilities` to spot disqualified candidates.

  `Structural liabilities` is hidden by default — Developability risk's `Very High` and `Non-Developable` values now carry its signal at higher resolution. The column stays available via the column picker for users who want the raw boolean.

## 5.0.3

### Patch Changes

- Updated dependencies [9b881d8]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@6.0.2
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@6.0.3

## 5.0.2

### Patch Changes

- Updated dependencies [169fc9c]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@6.0.1
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@6.0.2

## 5.0.1

### Patch Changes

- Updated dependencies [9e17876]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@6.0.1

## 5.0.0

### Major Changes

- 853c958: Support peptides

### Patch Changes

- Updated dependencies [853c958]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@6.0.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@6.0.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@6.0.0

## 4.0.3

### Patch Changes

- Updated dependencies [b4901a2]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@5.1.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@5.1.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@5.1.0

## 4.0.2

### Patch Changes

- Updated dependencies [32c76f3]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@5.0.1

## 4.0.1

### Patch Changes

- @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@5.0.1

## 4.0.0

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
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@5.0.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@5.0.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@5.0.0

## 3.2.1

### Patch Changes

- Updated dependencies [b9600e4]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@4.3.1
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@4.3.1

## 3.2.0

### Minor Changes

- 04076d8: adjusted coordinates for numbering schemes, dependencies updates

### Patch Changes

- Updated dependencies [04076d8]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@4.3.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@4.3.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@4.3.0

## 3.1.0

### Minor Changes

- 8d24e52: Expected cysteins position in light chain is corrected, dependencies updates

### Patch Changes

- Updated dependencies [8d24e52]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@4.2.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@4.2.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@4.2.0

## 3.0.2

### Patch Changes

- Updated dependencies [6579b7d]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@4.1.1

## 3.0.1

### Patch Changes

- Updated dependencies [ee5a48c]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@4.1.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@4.1.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@4.1.0

## 3.0.0

### Major Changes

- 4a02933: Show running state for tables and graphs, migrate to new project template

### Patch Changes

- Updated dependencies [4a02933]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@4.0.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@4.0.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@4.0.0

## 2.4.17

### Patch Changes

- db873a0: Block metadata updated.

## 2.4.16

### Patch Changes

- c5ccfe4: Update SDK

## 2.4.15

### Patch Changes

- Updated dependencies [0a15327]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@3.4.10

## 2.4.14

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
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@3.1.3
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@3.4.9

## 2.4.13

### Patch Changes

- Updated dependencies [65d4d91]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@3.1.2

## 2.4.12

### Patch Changes

- @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@3.4.8

## 2.4.11

### Patch Changes

- @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@3.4.7

## 2.4.10

### Patch Changes

- @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@3.4.6

## 2.4.9

### Patch Changes

- @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@3.4.5

## 2.4.8

### Patch Changes

- Updated dependencies [9d7983b]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@3.1.1
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@3.4.4
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@3.1.1

## 2.4.7

### Patch Changes

- Updated dependencies [a32a024]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@3.4.3

## 2.4.6

### Patch Changes

- @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@3.4.2

## 2.4.5

### Patch Changes

- Updated dependencies [fda18c5]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@3.1.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@3.1.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@3.4.1

## 2.4.4

### Patch Changes

- Updated dependencies [6d674ed]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@3.4.0

## 2.4.3

### Patch Changes

- @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@3.3.1

## 2.4.2

### Patch Changes

- Updated dependencies [7c52fa8]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@3.3.0

## 2.4.1

### Patch Changes

- Updated dependencies [2ca30b9]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@3.2.0

## 2.4.0

### Minor Changes

- 69f8369: allow prepare venv on Windows

## 2.3.6

### Patch Changes

- Updated dependencies [d5abe27]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@3.0.3
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@3.0.3

## 2.3.5

### Patch Changes

- 0db0703: SDK Upgrade & Code migration
- Updated dependencies [0db0703]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@3.1.2
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@3.0.2
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@3.0.2

## 2.3.4

### Patch Changes

- 93a57e2: chore: revert for MSA

## 2.3.3

### Patch Changes

- @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@3.1.1

## 2.3.2

### Patch Changes

- Updated dependencies [de16445]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@3.1.0

## 2.3.1

### Patch Changes

- Updated dependencies [47fe485]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@3.0.1
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@3.0.1

## 2.3.0

### Minor Changes

- 8528363: Allow liability selection

### Patch Changes

- Updated dependencies [c96e10a]
- Updated dependencies [8528363]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@3.0.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@3.0.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@3.0.0

## 2.2.0

### Minor Changes

- 1b7c43f: block tags

### Patch Changes

- Updated dependencies [1b7c43f]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@2.1.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@2.1.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@2.1.0

## 2.1.0

### Minor Changes

- d45b2a4: correct name

## 2.0.0

### Major Changes

- 5158f1f: Antibody Liabilities Block

### Patch Changes

- Updated dependencies [5158f1f]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@2.0.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@2.0.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@2.0.0
