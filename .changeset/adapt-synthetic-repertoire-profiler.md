---
'@platforma-open/milaboratories.antibody-sequence-liabilities.model': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities.workflow': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities.ui': patch
---

Support `synthetic-repertoire-profiler` (amplicon) variant datasets:

- New `"amplicon"` modality. The model recognizes the profiler's `pl7.app/variantKey` axis (axis domain `pl7.app/repertoire/extractionRunId`) as amplicon, distinct from peptide-extraction's `pl7.app/peptide/extractionRunId`. Previously such inputs entered the peptide branch and panicked (no `feature: "peptide"` sequence column found).
- Amplicon runs the same whole-sequence flat liability scan as peptide mode, reading the whole-variant amino-acid sequence (`pl7.app/feature: "amplicon-sequence"`).
- The echoed sequence output column is labeled with the `amplicon-sequence` feature (label "Sequence aa") instead of `peptide` / "Peptide aa", so it attaches to the correct entity.
- The UI treats amplicon as a whole-sequence mode: it hides the per-region selector for custom liabilities and shares the peptide predefined rule set.

Per-region liabilities for amplicon (using the profiler's region subsequence columns) are out of scope here — whole-sequence descriptors only.
