---
"@platforma-open/milaboratories.antibody-sequence-liabilities": patch
"@platforma-open/milaboratories.antibody-sequence-liabilities.model": patch
"@platforma-open/milaboratories.antibody-sequence-liabilities.workflow": patch
---

Add per-cluster centroid dataset and use retentive outputs for tables and charts. The centroid dataset (clonotype-clustering) is peptide-only, so it is now detected as peptide modality and processed through the peptide branch (previously routed to the antibody branch, which produced empty results because the peptide consensus column carries no VDJ feature).
