---
"@platforma-open/milaboratories.antibody-sequence-liabilities": minor
---

Replace single liabilities risk column with fixability taxonomy and add custom liability support.

The old "Liabilities risk" (None/Low/Medium/High) column is replaced with four columns that distinguish between fundamentally different types of issues:

- **Sequence quality** (Pass/Fail) — fails only for disqualifying issues: stop codons and out-of-frame sequences
- **Structural liabilities** (None/Present) — missing or extra conserved cysteines
- **Engineering liabilities risk** (None/Low/Medium/High) — fixable/easily-fixable liabilities only
- **Engineering burden** (Float) — count of engineering liabilities

This prevents Lead Selection's default filter from discarding candidates with trivially fixable issues (Met/Trp oxidation) alongside structurally unrescuable ones (missing conserved Cys).

Custom liabilities can now be defined in the block settings: user-supplied name, regex pattern, risk level, fixability classification, and regions to apply them to.
