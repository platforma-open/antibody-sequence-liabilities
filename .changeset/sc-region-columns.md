---
'@platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script': minor
'@platforma-open/milaboratories.antibody-sequence-liabilities.workflow': minor
'@platforma-open/milaboratories.antibody-sequence-liabilities': minor
---

Scan every region single-cell data provides

Only scFv input had its per-region sequence columns fed into the analysis table. Other
single-cell data was fed the whole chain plus the CDRs annotation, so the scan was limited to the
four regions that annotation yields: FR2, FR3 and FR4 appeared in "Regions to scan" but widened
the scope to everything instead of being applied. Every single-cell input is now fed its region
columns, the way bulk data already was.

A region the input carries as its own column is no longer extracted from the annotation a second
time. On multi-chain input the duplicate column aborted the run whenever a dataset offered some
regions but not all of them; on single-chain input the two copies were named differently, so both
were scanned and the extracted copy was the one reported.

Results change for single-cell datasets. FR2, FR3 and FR4 liability and risk columns appear, and
the other regions are read from the dataset's own columns instead of being re-derived from
annotation offsets. As with full-coverage bulk data, the exported annotation track then carries
the CDR boundaries only, without liability marks.
