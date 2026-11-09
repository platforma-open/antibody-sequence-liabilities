---
"@platforma-open/milaboratories.antibody-sequence-liabilities.workflow": patch
"@platforma-open/milaboratories.antibody-sequence-liabilities": patch
---

Scan centroid datasets from Sequence Clustering when the clustered dataset came from Amplicon Profiling. In whole-sequence mode the block now reads the amino-acid sequence column marked `pl7.app/isMainSequence`, and falls back to the `peptide` / `amplicon-sequence` feature columns for data without the marker. Before, a centroid dataset clustered on a region failed with "No amplicon aa sequence found on variantKey axis".

Update the SDK to 1.88 (model 1.88.0, ui-vue 1.88.3, workflow-tengo 6.22.0) and the toolchain to Node 24.22.1 and pnpm 12.
