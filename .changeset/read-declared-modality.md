---
'@platforma-open/milaboratories.antibody-sequence-liabilities.model': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities.workflow': patch
---

Read the input's declared `pl7.app/modality` instead of guessing the modality of a repertoire dataset

`synthetic-repertoire-profiler` runs one pipeline over both antibody/TCR parents and designed
libraries, and everything it emits sits on the modality-neutral `pl7.app/variantKey` axis. It now
declares which kind of repertoire it produced in the entity-axis domain, so this block reads that
declaration: `vdj` selects the per-region antibody path, `amplicon` the whole-sequence path.

Datasets with no declaration keep the previous behaviour — the run-id domain key, plus the
CDR3-region probe for repertoire input — so projects made before the declaration landed are
unaffected.
