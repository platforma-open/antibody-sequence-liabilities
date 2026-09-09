---
"@platforma-open/milaboratories.antibody-sequence-liabilities.liabilities-calc-script": minor
"@platforma-open/milaboratories.antibody-sequence-liabilities.workflow": minor
"@platforma-open/milaboratories.antibody-sequence-liabilities.model": minor
"@platforma-open/milaboratories.antibody-sequence-liabilities.ui": minor
"@platforma-open/milaboratories.antibody-sequence-liabilities": minor
---

Correctly handle non-canonical regions (with sub-regions)

A region partition may split a region one level deep, so a span named for a canonical region —
CDR2, say — can be a container holding a designed insert plus its flanks. The cysteine rules
assume a canonical immunoglobulin region and read the insert's own disulfide architecture as a
defect: on a KnotBody-style graft every variant came back `Extra Cysteines`, High and
`hard_to_fix`, carrying Developability risk to Very High and excluding it from lead selection by
default. The verdict was inverted too — an intact knot, a partly broken knot and a badly broken
knot all flagged identically, while a knot with every cysteine destroyed scored clean.

Regions holding a sub-region partition are now scanned with the peptide rule set plus N-linked
glycosylation. That withholds `Missing Cysteines`, `Extra Cysteines` and `Fragmentation (TS)` from
those regions and nothing else; every other liability, the disqualifying patterns and any custom
rules still apply there. N-linked glycosylation is kept because the peptide path drops it on the
grounds that a synthetic peptide never passes through an ER, whereas a grafted scaffold is secreted
from a mammalian line and the sequon is real.

A subdivided **framework** region gets less than that, deliberately. The predefined motif set has
always been CDR-scoped: a canonical FR region receives the cysteine checks, the disqualifying
patterns and any custom rules, but never the motif rules. Withholding its cysteine checks therefore
leaves a subdivided FR region with the disqualifying patterns and custom rules alone. 

Which regions those are is resolved per variant rather than per run. The fact is a property of the
parent reference and two scaffolds in one run can graft into different regions, so a single shared
`aaSeqCDR2` column holds a graft for one parent and a genuine CDR2 for another. It is read from
`synthetic-repertoire-profiler`'s `pl7.app/repertoire/subdividedRegions` and joined onto each
variant through the existing `pl7.app/repertoire/parentLink` linker; a run-wide flag would have
switched the cysteine checks off on real antibody regions belonging to non-subdividing parents.

The main page carries a notice naming the affected regions and the checks that were withheld. It
appears only when a scanned region actually holds a sub-region partition and at least one of those
checks was enabled, so narrowing the region scope past the container, or disabling those checks,
leaves it hidden.

Whole-molecule verdict columns are unchanged: with the cysteine rules out of the graft region
nothing can trigger the structural overrides, so the verdict settles on its own.

Inputs without sub-regions are untouched and take the same code path as before — bulk and
single-cell MiXCR runs produce byte-identical output.
