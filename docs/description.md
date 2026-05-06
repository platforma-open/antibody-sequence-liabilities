# Overview

Identifies sequence liabilities in antibody/TCR or peptide amino acid sequences and classifies them by fixability — how tractable each liability is to engineer away. This lets you distinguish candidates that need a quick conservative substitution from those requiring significant reengineering or that are not viable.

The block evaluates sequences for deamidation (`N[GS]`, `N[AHNT]`, `[STK]N`), fragmentation (`DP`, `TS`), isomerization (`D[DGHST]`), N-linked glycosylation (`N[^P][ST]`), oxidation-prone residues (tryptophan, methionine), cysteine issues (missing or extra), and integrin binding motifs. The set of applicable rules adapts to modality: antibody/TCR inputs are evaluated per CDR and framework region and include architecture-specific cysteine and hinge-fragmentation checks, while peptide inputs apply a flat backbone-chemistry rule set without region or cysteine-architecture checks.

Two output columns are emitted for both modalities:

- **Developability risk** — `None`/`Low`/`Medium`/`High`: severity of fixable liabilities (PTM motifs, fragmentation sites)
- **Developability cost** — continuous score: sum of engineering effort weighted by fixability class (antibody mode also weights by region importance); lower = easier to engineer

Antibody/TCR inputs additionally produce:
- **Is Productive** — `Pass`/`Fail`: fails on stop codons or out-of-frame sequences
- **Structural liabilities** — `None`/`Present`: flags missing or extra cysteines

You can extend the predefined liability set with custom motifs defined in the block settings or imported from a JSON file.
