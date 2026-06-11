---
"@platforma-open/milaboratories.antibody-sequence-liabilities.workflow": patch
---

Namespace output liability columns and the trace step by a hash of the liability configuration instead of the per-block blockId. Identical configs across blocks and projects now produce the same column identity and dedupe downstream instead of invalidating caches. The hash is derived inside the process templates from their arguments, and mem is passed to the liabilities-calc renders via metaInputs so it stays out of the content key.
