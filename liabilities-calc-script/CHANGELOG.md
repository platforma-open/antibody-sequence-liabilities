# @platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script

## 6.1.2

### Patch Changes

- 396ba4d: Drop the orphaned `prepublish` script from the software package

  The structurer migration moved the software package from `pl-pkg` to
  `block-tools software build` and removed the `@platforma-sdk/package-builder`
  devDependency that provided `pl-pkg`. It rewrote `build` and `do-pack` but left
  `prepublish` pointing at the removed binary, so `pnpm -r publish` failed with
  `sh: 1: pl-pkg: not found`.

  No replacement script is needed. `block-tools software build` builds and pushes in
  one pass, and CI already runs it before publishing through
  `build-before-publish-script-name: 'build:release'`, which sets
  `PL_BUILD_LOCATION=remote`. The npm publish then only ships the tarball. This
  matches the software package of an already-migrated block.

## 6.1.1

### Patch Changes

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

## 6.1.0

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

- 09aa4ce: Fail when no column can be scanned

  An input offering no region column and no CDRs annotation produced blank Sequence liabilities
  summary, Structural liabilities and Developability columns for every clonotype, which reads as a
  clean result rather than as a scan that never ran. The run now stops with the columns it was given.

## 6.0.3

### Patch Changes

- 2f3f53c: Anchor FR1 conserved-cysteine check from the region end so reference framing no longer causes false Missing/Extra Cysteines.

## 6.0.2

### Patch Changes

- 0a047a7: Fix false "Missing Cysteines" on germline imputed sequences.

## 6.0.1

### Patch Changes

- f58bc23: Republish calc-script to ship the per-region risk aggregation fix.

## 6.0.0

### Major Changes

- 853c958: Support peptides

## 5.0.0

### Major Changes

- 6ca5696: Ensure software is updated

## 4.2.0

### Minor Changes

- 04076d8: adjusted coordinates for numbering schemes, dependencies updates

## 4.1.0

### Minor Changes

- 8d24e52: Expected cysteins position in light chain is corrected, dependencies updates

## 4.0.0

### Major Changes

- 4a02933: Show running state for tables and graphs, migrate to new project template

## 3.2.7

### Patch Changes

- 9c55f5a: technical release
- 3766c4a: technical release
- 1c704a8: technical release
- 061677e: technical release

## 3.2.6

### Patch Changes

- fac8424: Fix FR1 Cysteine location

## 3.2.5

### Patch Changes

- 929381c: solve error related with features being shorter than the expected location for thei main Cysteine

## 3.2.4

### Patch Changes

- 835d47e: Fix cysteine location check for missing and gained cysteines

## 3.2.3

### Patch Changes

- 4f8afc2: Update python

## 3.2.2

### Patch Changes

- 9d7983b: Full SDK update

## 3.2.1

### Patch Changes

- 8c89b35: Updated SDK.

## 3.2.0

### Minor Changes

- fda18c5: support empty input

## 3.1.3

### Patch Changes

- 96899ef: fix requirements.txt

## 3.1.2

### Patch Changes

- 0db0703: SDK Upgrade & Code migration

## 3.1.1

### Patch Changes

- b2e27c6: chore: update deps

## 3.1.0

### Minor Changes

- de16445: Liabilities summary column

## 3.0.0

### Major Changes

- c96e10a: fragments extraction from assemblingFeature, annotations added

### Minor Changes

- 8528363: Allow liability selection

## 2.0.0

### Major Changes

- 5158f1f: Antibody Liabilities Block
