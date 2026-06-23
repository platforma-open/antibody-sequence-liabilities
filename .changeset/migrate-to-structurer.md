---
'@platforma-open/milaboratories.antibody-sequence-liabilities.model': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities.ui': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities.workflow': patch
'@platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script': patch
---

Migrate the block onto the structurer (block-tools 2.11.1). Full SDK upgrade via the canonical `structure refresh` flow: model/ui-vue 1.79.15, workflow-tengo 6.6.3, tengo-builder 4.0.9, ts-builder 1.5.2. Replaces hand-maintained tsconfig/eslint config with tool-managed oxlint/oxfmt; no behavior change.
