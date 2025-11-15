# Overview

Identifies sequence liabilities in antibody amino acid sequences that may impact manufacturability, stability, or safety during therapeutic development.

The block evaluates sequences for multiple types of liabilities including deamidation sites (`N[GS]`, `N[AHNT]`, `[STK]N`), fragmentation sites (`DP`, `TS`), isomerization (`D[DGHST]`), N-linked glycosylation sites (`N[^P][ST]`), oxidation-prone residues (tryptophan, methionine), cysteine-related issues (missing or extra cysteines), and sequence quality issues (stop codons, out-of-frame sequences). Liabilities are assessed across different antibody regions (CDRs and framework regions) and assigned risk levels (High, Medium, Low) based on their potential impact.
