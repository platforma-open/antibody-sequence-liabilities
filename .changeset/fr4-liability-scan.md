---
'@platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script': minor
'@platforma-open/milaboratories.antibody-sequence-liabilities.workflow': minor
'@platforma-open/milaboratories.antibody-sequence-liabilities': minor
---

Scan FR4 on datasets that provide it

Both region loops filling the analysis table stopped at FR3, so a dataset's FR4 sequence column
never reached the scan. FR4 is now fed in for bulk and scFv data, and its Liabilities and Risk
columns appear.

FR4 gets the cysteine rules only, as FR2 and FR3 already do; motifs stay CDR-only.

Selecting FR4 in "Regions to scan" is now honoured instead of silently scanning every region.

A region present on one chain only now still produces its combined column, carrying just that
chain's value, rather than staying chain-prefixed and failing the pframe import. FR4 is the
likeliest region to be one-sided. The `Heavy:` / `Light:` label inside a value is written only
when the input holds both chains, so single-chain data keeps the bare `None` / `High` values its
Risk columns are declared to hold.

Results change for datasets carrying FR4.
