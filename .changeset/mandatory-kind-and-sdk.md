---
'@platforma-open/milaboratories.antibody-sequence-liabilities.kind': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities.model': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities.workflow': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities.ui': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities': patch
---

Add the mandatory kind component and upgrade the SDK

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
