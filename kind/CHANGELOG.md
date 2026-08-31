# @platforma-open/milaboratories.antibody-sequence-liabilities.kind

## 1.0.1

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
