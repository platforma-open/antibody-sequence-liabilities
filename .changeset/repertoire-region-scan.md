---
'@platforma-open/milaboratories.antibody-sequence-liabilities.model': minor
'@platforma-open/milaboratories.antibody-sequence-liabilities.workflow': minor
'@platforma-open/milaboratories.antibody-sequence-liabilities': minor
---

Scan repertoire input per region when it carries located regions

A synthetic-repertoire-profiler dataset was always scanned as one whole sequence, even when the
run located FR1-FR4/CDR1-3, because the modality was read from the producer's run-id stamp rather
than from what the dataset actually offers. Such input now takes the antibody path: the region
selector appears, the antibody rule set is offered, and a region scope is honoured. Runs whose
region set has no CDR3 — and runs with no regions at all — are unchanged.
