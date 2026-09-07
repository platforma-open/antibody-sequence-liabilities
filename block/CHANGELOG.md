# @platforma-open/milaboratories.antibody-sequence-liabilities

## 5.2.2

### Patch Changes

- bd4ad1e: Scan whatever FR/CDR regions the input carries, instead of requiring CDR3

  A vdj-declared repertoire is now region-scanned over any canonical region it carries; only an
  input with no FR/CDR aa region column at all is rejected. CDR3 was never part of the contract:
  `synthetic-repertoire-profiler` derives the `vdj` declaration from the region scheme, independent
  of which spans end up codon-aligned and so of which amino-acid region columns exist, and a
  designed scaffold may legitimately be partitioned FR2/CDR2/FR3 with no CDR3.

  The echoed CDR3 sequence column is emitted only when the input carries a CDR3 column to take it
  from. Declaring it unconditionally failed the results import on a column the table does not have —
  which also broke `import-vdj-data` sets whose FR/CDR mapping omits CDR3, on a path that never
  reached the region check above.

  Inputs that carry CDR3 are unaffected: same columns, same table.

## 5.2.1

### Patch Changes

- c482558: Add the mandatory kind component and upgrade the SDK

  block-tools 2.14 makes a `kind/` package a mandatory fourth block component
  alongside model, workflow and ui. The kind carries the block's identity and its
  init-params contract — what a creator or a project template supplies to seed a new
  instance.

  This block's contract is the liability panel: `usePredefinedLiabilities`,
  `disabledPredefinedLiabilities`, `customLiabilities` and `regions`. A team with a
  house panel can pin it in a template and only pick the dataset afterwards. Left
  out: the input ref and the uploaded rules file (both project-local), the modality
  (a fact about the picked dataset), the derived default label, the table state, and
  the memory override.

  The model now declares its kind (`new DataModelBuilder({ kind })`,
  `BlockModelV3.create({ dataModel, kind })`), consumes the contract in `init`, and
  projects the same fields back out through `.templateParams(...)`. The
  custom-liability type moves to the kind, which the contract needs, and the model
  re-exports it so the UI is unaffected.

- 9d06317: Migrate onto the structurer template

  `block-tools structure` now owns the block's layout: tsconfig, oxlint/oxfmt, turbo,
  the block index, the CI workflows and `package.json` across every package. Config
  that used to be maintained by hand is now refreshable tool output, so the next SDK
  upgrade is a single `pnpm run upgrade-sdk`.

  What this changes for a developer:

  - **Linting and formatting move from eslint to oxlint + oxfmt.** The per-package
    `eslint.config.mjs` files and the `eslint` dependency are gone. `pnpm check` runs
    type-check, lint and format-check together; `pnpm fmt` applies fixes.
  - **The build scripts are renamed.** `pnpm build:dev` becomes `pnpm build:dev-local`,
    and `build:dev-no-software`, `build:dev-binary-existing` and `build:release` join it.
  - **`block/` is now a slim facade** with no runtime dependencies: the whole block is
    bundled into its `dist/` and `block-pack/`, and it is the only package that
    publishes.

  - **CI runs the test lane again.** It had been off (`test: false`); the scaffold turns
    it on. The block has no tests, so the dead `test` scripts and vitest configs in
    `model/` and `ui/` were removed — `pnpm test` now builds and passes with no test
    tasks.

  Sources were reformatted by oxfmt. The changes are quote style, line wrapping and
  self-closing void tags; no logic was touched.

## 5.2.0

### Minor Changes

- 2f8b97f: Scan FR4 on datasets that provide it

  Both region loops filling the analysis table stopped at FR3, so a dataset's FR4 sequence column
  never reached the scan. FR4 is now fed in for bulk and scFv data, and its Liabilities and Risk
  columns appear.

  FR4 gets the cysteine rules only, as FR2 and FR3 already do; motifs stay CDR-only.

  Selecting FR4 in "Regions to scan" is now honoured instead of silently scanning every region.

  A region present on one chain only now still produces its combined column, carrying just that
  chain's value, rather than staying chain-prefixed and failing the pframe import. FR4 is the
  likeliest region to be one-sided. The `Heavy:` / `Light:` label inside a value is written only
  when the input holds both chains, so single-chain data keeps the bare `None` / `High` values its
  Risk columns are declared to hold.

  Results change for datasets carrying FR4.

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

- e8a4a52: Scan every region single-cell data provides

  Only scFv input had its per-region sequence columns fed into the analysis table. Other
  single-cell data was fed the whole chain plus the CDRs annotation, so the scan was limited to the
  four regions that annotation yields: FR2, FR3 and FR4 appeared in "Regions to scan" but widened
  the scope to everything instead of being applied. Every single-cell input is now fed its region
  columns, the way bulk data already was.

  A region the input carries as its own column is no longer extracted from the annotation a second
  time. On multi-chain input the duplicate column aborted the run whenever a dataset offered some
  regions but not all of them; on single-chain input the two copies were named differently, so both
  were scanned and the extracted copy was the one reported.

  Results change for single-cell datasets. FR2, FR3 and FR4 liability and risk columns appear, and
  the other regions are read from the dataset's own columns instead of being re-derived from
  annotation offsets. As with full-coverage bulk data, the exported annotation track then carries
  the CDR boundaries only, without liability marks.

### Patch Changes

- Updated dependencies [2f8b97f]
- Updated dependencies [258ffde]
- Updated dependencies [adb3cb8]
- Updated dependencies [76f2c1a]
- Updated dependencies [7bf8c3a]
- Updated dependencies [e8a4a52]
- Updated dependencies [9a8dd3f]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@6.2.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@6.1.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@6.1.0

## 5.1.0

### Minor Changes

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

### Patch Changes

- Updated dependencies [f42a57c]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.workflow@6.1.0
  - @platforma-open/milaboratories.antibody-sequence-liabilities.model@6.0.4
  - @platforma-open/milaboratories.antibody-sequence-liabilities.ui@6.0.5

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
