---
'@platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script': minor
'@platforma-open/milaboratories.antibody-sequence-liabilities.workflow': minor
'@platforma-open/milaboratories.antibody-sequence-liabilities.model': minor
'@platforma-open/milaboratories.antibody-sequence-liabilities.ui': minor
'@platforma-open/milaboratories.antibody-sequence-liabilities': minor
---

Add a "Regions to scan" selector that restricts liability detection to chosen regions

Candidates whose parental scaffold carries known-good liabilities were all scoring High on
Developability risk, leaving no way to rank them by the region actually being engineered.
Selecting regions (e.g. CDR3, or the CDRs) now scans only those: their per-region columns are
the only ones emitted, and Developability risk and cost are computed from them alone.

Leaving the selector empty scans every region, which is the previous behaviour — existing
projects are unaffected and their cached results still match.

Is Productive remains whole-molecule: stop-codon and out-of-frame detection still covers
regions left out of the scope. The cysteine checks anchor on FR1 and FR3, so scoping away
from both makes them undetectable; the UI warns when that combination is selected.

Regions are now ordered biologically (FR1, CDR1, FR2, CDR2, FR3, CDR3, FR4), changing the
per-region table column order and the segment order inside `Sequence liabilities summary`.

The results table moved from createPlDataTableV2 to V3 to ensure stale sorts are dropped.
