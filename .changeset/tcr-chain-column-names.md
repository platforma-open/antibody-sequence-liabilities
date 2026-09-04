---
'@platforma-open/milaboratories.antibody-sequence-liabilities.workflow': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script': patch
---

Name TCR chain columns after the receptor instead of Heavy/Light. Chains now travel to the liabilities script as receptor-neutral A/B chain letters, with the display names (Heavy/Light, Alpha/Beta, Gamma/Delta) derived from `pl7.app/vdj/receptor` and passed in via `--chain-labels`.
