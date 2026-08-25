---
'@platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script': patch
---

Fail when no column can be scanned

An input offering no region column and no CDRs annotation produced blank Sequence liabilities
summary, Structural liabilities and Developability columns for every clonotype, which reads as a
clean result rather than as a scan that never ran. The run now stops with the columns it was given.
