# Overview

Identifies sequence liabilities in antibody amino acid sequences and classifies them by fixability — how tractable each liability is to engineer away. This lets you distinguish candidates that need a quick conservative substitution from those requiring significant reengineering or that are not viable.

The block evaluates sequences for deamidation (`N[GS]`, `N[AHNT]`, `[STK]N`), fragmentation (`DP`, `TS`), isomerization (`D[DGHST]`), N-linked glycosylation (`N[^P][ST]`), oxidation-prone residues (tryptophan, methionine), cysteine issues (missing or extra), integrin binding motifs, and sequence quality issues (stop codons, out-of-frame sequences). Liabilities are assessed across CDR and framework regions.

Results are reported in four output columns:

- **Is Productive** — `Pass`/`Fail`: fails on stop codons or out-of-frame sequences
- **Structural liabilities** — `None`/`Present`: flags missing or extra cysteines
- **Developability risk** — `None`/`Low`/`Medium`/`High`: severity of fixable liabilities (PTM motifs, fragmentation sites)
- **Developability cost** — continuous score: sum of engineering effort weighted by fixability class and region importance; lower = easier to engineer

You can extend the predefined liability set with custom motifs defined in the block settings or imported from a JSON file.
