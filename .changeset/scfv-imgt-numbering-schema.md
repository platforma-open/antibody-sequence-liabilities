---
'@platforma-open/milaboratories.antibody-sequence-liabilities.workflow': patch
---

Honour IMGT/Kabat/Chothia renumbering on scFv datasets

Redefining clonotypes with a numbering scheme and then scanning liabilities worked downstream
of MiXCR clonotyping but not downstream of scFv alignment: every scFv CDR3 came back with a
Missing Cysteines liability.

The numbering scheme reaches this block as the `pl7.app/vdj/numberingSchema` annotation that
redefine-clonotypes stamps onto the sequence columns it renumbers. That stamp was only looked
for on the assembling-feature column. For MiXCR clonotyping the assembling feature is itself a
`pl7.app/vdj/sequence` column, so the stamp was there and the scheme was picked up. For scFv the
assembling feature is the whole construct (`pl7.app/vdj/scFv-sequence`), which is not renumbered
and therefore never stamped. Therefore, no scheme was found and the conserved cysteine was left at its
default position, the first residue of CDR3. An IMGT CDR3 does not start with that cysteine,
which is why the liability fired on every clonotype. The scheme is now also read from the
per-region sequence columns, where it is always present.

scFv datasets also fed only FR1 and the CDRs into the scan. Under IMGT the conserved cysteine
moves out of CDR3 and into FR3, so FR2 and FR3 are now included as well, matching the regions
already scanned for bulk data. Their per-region liability columns appear for scFv datasets for
the first time.
