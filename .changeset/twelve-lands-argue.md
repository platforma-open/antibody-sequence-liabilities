---
"@platforma-open/milaboratories.antibody-sequence-liabilities.workflow": minor
"@platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script": minor
"@platforma-open/milaboratories.antibody-sequence-liabilities": patch
---

A repertoire input no longer carries its whole-variant aa sequence into the analysis table.

The calc script reads that column for exactly one thing — the stop-codon and out-of-frame checks
behind `sequence aa liabilities`, which feed the sequence summary, `Is Productive` and the
developability score. It is never scanned per region and never exported. At repertoire scale it is
also the largest column in the block by an order of magnitude: on a 39.4M-variant amplicon run it
passed the 2 GiB that one Arrow string array can hold, and the input frame failed to materialise
before the scan ever started (`Arrow error: Offset overflow error`).

The two checks are now evaluated against the sequence column on its own, and only the resulting
flags travel into the analysis table, where the script rebuilds the same `sequence aa liabilities`
column from them. Same column name, same four values, so the summary, `Is Productive` and the
developability score are unchanged — covered by a test that runs the same rows down both paths and
compares the whole output table.

Only the repertoire path changes. MiXCR bulk, single-cell and bare antibody sets keep sending the
whole-chain sequence exactly as before.
