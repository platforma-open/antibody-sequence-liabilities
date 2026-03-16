---
"@platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script": major
"@platforma-open/milaboratories.antibody-sequence-liabilities.workflow": major
"@platforma-open/milaboratories.antibody-sequence-liabilities.model": major
"@platforma-open/milaboratories.antibody-sequence-liabilities.ui": major
"@platforma-open/milaboratories.antibody-sequence-liabilities": major
---

Replace single liabilities risk column with fixability taxonomy, add custom liability support, and new predefined liability controls.

The old "Liabilities risk" column is replaced with four columns:

- **Is Productive** (Pass/Fail) — fails only for disqualifying issues: stop codons and out-of-frame sequences
- **Structural liabilities** (None/Present) — structural (missing Cys) and hard-to-fix (extra Cys) issues
- **Developability risk** (None/Low/Medium/High) — max riskLevel of fixable/easily-fixable liabilities
- **Developability score** (Float) — weighted sum of fixability_weight × region_weight

Predefined liability configuration changes from opt-in (`liabilityTypes`) to opt-out (`usePredefinedLiabilities` + `disabledPredefinedLiabilities`). Integrin binding is added as a new predefined liability, off by default. Fixability classifications updated: Deamidation (N[GS]) and other High-risk patterns are now `fixable` (surfacing in Developability risk), Extra Cysteines changed from `structural` to `hard_to_fix`.

Custom liabilities are defined with name, regex pattern, risk level, fixability, and regions. They are passed as a JSON file rather than inline JSON.
