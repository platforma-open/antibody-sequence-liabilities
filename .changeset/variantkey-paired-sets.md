---
'@platforma-open/milaboratories.antibody-sequence-liabilities.workflow': minor
'@platforma-open/milaboratories.antibody-sequence-liabilities.model': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities': minor
---

Support bare antibody sets keyed on pl7.app/variantKey

Three producers now key on `pl7.app/variantKey` and only the run-id in the axis domain says
which: peptide-extraction, synthetic-repertoire-profiler, and import-vdj-data's bare antibody
sets. Both the workflow and the model decided modality from the axis name alone, so a bare
antibody set was treated as peptide — the run died on "No peptide aa sequence found on
variantKey axis", and the model selected the peptide liability list and accepted a custom
liability with no regions selected.

Such a set also carries both chains in one frame, separated by the
`pl7.app/vdj/scClonotypeChain` column domain, rather than in separate frames. Whether the
sequence table is built per chain now follows that domain instead of the key axis being
`pl7.app/vdj/scClonotypeKey`, so both chains are scanned. Columns are labelled Heavy/Light,
which the calculation script already reads: it analyses each chain and merges the findings into
one summary per region.

Columns are prefixed Heavy/Light only when both chains are present.
`_combine_heavy_light_prefixed_columns` merges the per-chain columns back into one per region by
intersecting the Heavy and Light base names, so a single-chain set would keep its prefixes and
the run would fail on a missing `CDR1 aa liabilities`. A one-chain set is shaped like a bulk one
and is now labelled like one.

The numbering scheme is now read from the located region columns as well as the whole variable
domain. import-vdj-data stamps it on the regions, so it arrived empty — and with no scheme the
detector expects a cysteine at CDR3 position 0, reporting `Missing Cysteines` on every record.
That is a structural liability, so an entire 1,243-antibody panel scored Non-Developable.

Peptide, amplicon, bulk and single-cell inputs are unaffected.
