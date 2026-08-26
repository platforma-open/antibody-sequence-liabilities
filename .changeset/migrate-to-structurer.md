---
'@platforma-open/milaboratories.antibody-sequence-liabilities.kind': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities.model': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities.ui': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities.workflow': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities': patch
---

Migrate onto the structurer template

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
