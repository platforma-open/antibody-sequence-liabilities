---
'@platforma-open/milaboratories.antibody-sequence-liabilities.model': patch
---

Stop offering regions a CDR3-only library cannot scan

"Regions to scan" listed FR1, CDR1, CDR2 and CDR3 for libraries assembled by CDR3, where CDR3 is
the only region present. Any annotation column was taken as evidence that regions could be
extracted from it, but a CDR3-assembled library carries a Segments annotation (V/D/J/C
boundaries), not the CDRs annotation regions are extracted from. Only a CDRs annotation counts
now, so these libraries offer CDR3 alone.

Selecting one of the phantom regions scanned everything instead, without the warning that
normally appears when a selection cannot be applied.
