---
'@platforma-open/milaboratories.antibody-sequence-liabilities.ui': patch
---

Hide "Regions to scan" until an antibody input is selected

The selector was shown for every non-peptide input, including before any dataset was chosen,
where it appeared greyed out. It is now shown only once the input is known to be antibody data.
The same gate applies to the per-region picker on a custom liability.
