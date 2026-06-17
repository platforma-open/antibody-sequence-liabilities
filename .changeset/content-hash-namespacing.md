---
"@platforma-open/milaboratories.antibody-sequence-liabilities.workflow": patch
---

Namespace output liability columns and the trace step by a hash of the liability configuration instead of the per-block blockId. Identical configs across blocks and projects now produce the same column identity and dedupe downstream instead of invalidating caches. The hash is derived inside the process templates from their arguments, and mem is passed to the liabilities-calc renders via metaInputs so it stays out of the content key.

Also sort the disabledPredefinedLiabilities list to a canonical order (slices.sortUnique) inside normalize(). The list is a set, but it reached the liabilities-calc render input, the written disabled-predefined-liabilities.json file, and the config hash as a raw array; the backend canonicalizes map keys on the resource CID but not array element order, so an unsorted list made semantically identical configs hash differently and re-run the calc across blocks/projects. Verified: 4 blocks across 2 projects now collapse to a single calc run.
