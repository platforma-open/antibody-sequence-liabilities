---
'@platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script': patch
---

Drop the orphaned `prepublish` script from the software package

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
