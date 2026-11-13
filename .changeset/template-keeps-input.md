---
"@platforma-open/milaboratories.antibody-sequence-liabilities.kind": minor
"@platforma-open/milaboratories.antibody-sequence-liabilities.model": patch
---

Keep the input dataset in a project template. A project made from a template came with Sequence Liabilities without its dataset, so it could not run until the dataset was picked by hand in every block. The kind now carries `inputAnchor` and `filterRef`, references to the upstream dataset and its subset, and the block made from a template points at the dataset the original project used.
