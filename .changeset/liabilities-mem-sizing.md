---
'@platforma-open/milaboratories.antibody-sequence-liabilities.workflow': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities': patch
---

Size the liabilities calculation's memory request from the input's row count instead of a fixed 16 GiB, so multi-million-clonotype inputs get the memory they need. Floors stay at 16 GiB (clonotype mode) and 8 GiB (peptide mode); a memory value set in the block's settings still replaces the computed request.
