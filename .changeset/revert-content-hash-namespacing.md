---
"@platforma-open/milaboratories.antibody-sequence-liabilities.workflow": patch
---

Revert namespacing of output liability columns and the trace step by a content hash of the liability configuration: the column domain and trace step id are keyed on the per-block blockId again. The config-hash helper is removed and blockId is threaded back through the process templates.

The independent re-run deduplication fixes are kept: disabledPredefinedLiabilities is still sorted to a canonical order (slices.sortUnique) inside normalize(), the annotation mapping is still encoded with canonical.encode (key-sorted, deterministic) so identical mappings produce identical column specs across runs, and mem is still passed to the calc renders via metaInputs so it stays out of the content key.
