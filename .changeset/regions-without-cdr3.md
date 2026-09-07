---
'@platforma-open/milaboratories.antibody-sequence-liabilities.workflow': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities': patch
---

Scan whatever FR/CDR regions the input carries, instead of requiring CDR3

A vdj-declared repertoire is now region-scanned over any canonical region it carries; only an
input with no FR/CDR aa region column at all is rejected. CDR3 was never part of the contract:
`synthetic-repertoire-profiler` derives the `vdj` declaration from the region scheme, independent
of which spans end up codon-aligned and so of which amino-acid region columns exist, and a
designed scaffold may legitimately be partitioned FR2/CDR2/FR3 with no CDR3.

The echoed CDR3 sequence column is emitted only when the input carries a CDR3 column to take it
from. Declaring it unconditionally failed the results import on a column the table does not have —
which also broke `import-vdj-data` sets whose FR/CDR mapping omits CDR3, on a path that never
reached the region check above.

Inputs that carry CDR3 are unaffected: same columns, same table.
