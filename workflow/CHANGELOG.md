# @platforma-open/milaboratories.antibody-sequence-liabilities.workflow

## 6.2.1

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

- c482558: Read the input's declared `pl7.app/modality` instead of guessing the modality of a repertoire dataset

  `synthetic-repertoire-profiler` runs one pipeline over both antibody/TCR parents and designed
  libraries, and everything it emits sits on the modality-neutral `pl7.app/variantKey` axis. It now
  declares which kind of repertoire it produced in the entity-axis domain, so this block reads that
  declaration: `vdj` selects the per-region antibody path, `amplicon` the whole-sequence path.

  Datasets with no declaration keep the previous behaviour — the run-id domain key, plus the
  CDR3-region probe for repertoire input — so projects made before the declaration landed are
  unaffected.

- Updated dependencies [9d06317]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@6.1.1

## 6.2.0

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

- 9a8dd3f: Honour IMGT/Kabat/Chothia renumbering on scFv datasets

  Redefining clonotypes with a numbering scheme and then scanning liabilities worked downstream
  of MiXCR clonotyping but not downstream of scFv alignment: every scFv CDR3 came back with a
  Missing Cysteines liability.

  The numbering scheme reaches this block as the `pl7.app/vdj/numberingSchema` annotation that
  redefine-clonotypes stamps onto the sequence columns it renumbers. That stamp was only looked
  for on the assembling-feature column. For MiXCR clonotyping the assembling feature is itself a
  `pl7.app/vdj/sequence` column, so the stamp was there and the scheme was picked up. For scFv the
  assembling feature is the whole construct (`pl7.app/vdj/scFv-sequence`), which is not renumbered
  and therefore never stamped. Therefore, no scheme was found and the conserved cysteine was left at its
  default position, the first residue of CDR3. An IMGT CDR3 does not start with that cysteine,
  which is why the liability fired on every clonotype. The scheme is now also read from the
  per-region sequence columns, where it is always present.

  scFv datasets also fed only FR1 and the CDRs into the scan. Under IMGT the conserved cysteine
  moves out of CDR3 and into FR3, so FR2 and FR3 are now included as well, matching the regions
  already scanned for bulk data. Their per-region liability columns appear for scFv datasets for
  the first time.

- Updated dependencies [09aa4ce]
- Updated dependencies [2f8b97f]
- Updated dependencies [adb3cb8]
- Updated dependencies [e8a4a52]
  - @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script@6.1.0

## 6.1.0

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

## 6.0.6

### Patch Changes

- 386b7f5: Fix crash on heavy-only single-cell (VHH) input. The single-cell output now declares per-chain sequence/annotation columns only for the chains actually present, so heavy-only data no longer fails with `ColumnNotFoundError: unable to find column "Heavy CDR3 aa"`. Single-chain single-cell is fixed for the non-scFv (annotation-extraction) path; scFv single-chain input remains a separate known issue (its region-liability columns stay chain-prefixed).

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
