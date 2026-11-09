---
"@platforma-open/milaboratories.antibody-sequence-liabilities.model": patch
"@platforma-open/milaboratories.antibody-sequence-liabilities.ui": patch
"@platforma-open/milaboratories.antibody-sequence-liabilities.workflow": patch
---

Compute the block label without the UI

The trace label and the subtitle are now built by the model from the liability
settings, so opening the block no longer changes its arguments and a block that was
never opened gets the same label. The trace label now names the block, e.g.
"Sequence Liabilities (All Predefined)". Existing blocks show as stale once after the
update because the arguments change shape.
