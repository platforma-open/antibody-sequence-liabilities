---
"@platforma-open/milaboratories.antibody-sequence-liabilities": patch
---

Fix: per-region "{region} Risk" columns now reflect any matching liability, not just engineering-fixable ones.

Previously, when a region matched a `hard_to_fix` or `structural` liability (e.g. `Extra Cysteines`, or a custom liability with fixability `Hard to fix`), the corresponding `{region} Risk` column reported `None`, even though `{region} Liabilities` listed the liability. The two columns now agree: `{region} Risk` is the worst `riskLevel` of any non-disqualifying liability detected in that region.

The spec at `docs/text/work/projects/sequence-liability-fixability-scoring/README.md:126` listed both behaviors as defensible and deferred the call to the implementor. The original v4.0.0 implementation picked Option A (engineering-only); this release switches to Option B (all non-disqualifying), which the spec named as the alternative.

Global behavior is unchanged: `Developability risk` still aggregates only `fixable` + `easily_fixable` liabilities, and `Structural liabilities` still flags `Present` for `hard_to_fix` / `structural` matches.
