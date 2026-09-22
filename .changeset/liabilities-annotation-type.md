---
'@platforma-open/milaboratories.antibody-sequence-liabilities.workflow': minor
'@platforma-open/milaboratories.antibody-sequence-liabilities': minor
---

The emitted sequence-annotation column now declares its own `pl7.app/sequence/annotation/type: "Liabilities"` instead of copying `"CDRs"` from its input column, and its labels follow. The copied type made the output indistinguishable from the MiXCR CDRs annotation it consumes: it matched the block's own input selector, the `type == "CDRs"` lookups in redefine-clonotypes, and the real CDRs column in the MSA color scheme dropdown. Track content is unchanged and still carries the input's region segments alongside the liability hits.

The new domain gives the column a new identity, so a saved MSA color scheme pointing at the old one is dropped and re-picked on next open.
