---
"@platforma-open/milaboratories.antibody-sequence-liabilities": patch
"@platforma-open/milaboratories.antibody-sequence-liabilities.workflow": patch
---

Fix crash on heavy-only single-cell (VHH) input. The single-cell output now declares per-chain sequence/annotation columns only for the chains actually present, so heavy-only data no longer fails with `ColumnNotFoundError: unable to find column "Heavy CDR3 aa"`. Single-chain single-cell is fixed for the non-scFv (annotation-extraction) path; scFv single-chain input remains a separate known issue (its region-liability columns stay chain-prefixed).
