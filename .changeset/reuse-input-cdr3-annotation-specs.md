---
'@platforma-open/milaboratories.antibody-sequence-liabilities.workflow': patch
---

Echo the CDR3 sequence and CDRs annotation columns using each input column's own name and domain instead of re-deriving them in clonotype-process. VDJ inputs are unchanged; amplicon (Amplicon Profiling) inputs now keep their native pl7.app/sequence namespace on the echoed CDR3 column in the block's own table. Only the primary chain's specs are echoed, so a secondary single-cell chain can no longer leak into the exported annotation.
