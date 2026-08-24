Screen antibody, TCR, and peptide sequences for developability liabilities — the motifs that cause deamidation, isomerization, fragmentation, unwanted glycosylation, oxidation, and cysteine problems. This Platforma block flags every occurrence, classifies each by how hard it is to engineer away, and reports a developability risk level and a continuous engineering-cost score per sequence.

Open-source analysis block for Platforma, the biologics discovery platform by MiLaboratories. For the full no-code workflow, see [platforma.bio](https://platforma.bio/).

> **Naming:** this block appears as **Sequence Liabilities** in the Platforma app; the repository is named `antibody-sequence-liabilities`, and the documentation calls it *Antibody Sequence Liabilities Assessment*. They are the same block.

## What it does

A liability flag on its own is not a decision. Almost every real candidate carries some motif, and the useful question is not whether liabilities exist but how much work they represent — a tryptophan in a framework region and a missing structural cysteine are not the same finding.

This block answers that. Every sequence is scanned for the liability motifs you enable, and each hit is classified by **fixability**: easily fixable, fixable, hard to fix, or structural. Those classes carry engineering weights, so a single score reflects real effort rather than a count of hits. For antibodies and TCRs, hits are also weighted by where they occur — a liability in CDR3 costs more than the same motif in FR4, because changing it is more likely to affect binding.

Two columns come out for every modality:

* **Developability risk** — `None`, `Low`, `Medium`, `High`, `Very High`, or `Non-Developable`. The lower bands reflect the severity of fixable liabilities; `Very High` means a hard-to-fix liability is present, such as extra cysteines; `Non-Developable` means a structural liability is present, such as a missing cysteine.
* **Developability cost** — a continuous score summing engineering effort weighted by fixability class, and by region importance for antibody and TCR input. Lower is easier to engineer.

Antibody and TCR input also produces **Is Productive** (`Pass` / `Fail`), which fails on stop codons and out-of-frame sequences.

The applicable rules adapt to the input. Antibody and TCR sequences are evaluated region by region across FR1–FR4 and CDR1–CDR3, and include cysteine architecture checks — a conserved cysteine missing from where the numbering scheme expects it, or an unpaired extra one. Peptide and amplicon variant input applies backbone-chemistry rules to the whole sequence, without region or cysteine checks, since neither applies.

### Predefined liabilities

| Liability | Pattern | Risk | Fixability | Modality |
|---|---|---|---|---|
| Deamidation | `N[GS]` | High | Fixable | Antibody, peptide |
| Fragmentation | `DP` | High | Fixable | Antibody, peptide |
| Isomerization | `D[DGHST]` | High | Fixable | Antibody, peptide |
| N-linked glycosylation | `N[^P][ST]` | High | Fixable | Antibody only |
| Deamidation | `N[AHNT]` | Medium | Easily fixable | Antibody, peptide |
| Hydrolysis | `NP` | Medium | Fixable | Antibody, peptide |
| Fragmentation | `TS` | Medium | Fixable | Antibody only |
| Tryptophan oxidation | `W` | Medium | Easily fixable | Antibody, peptide |
| Methionine oxidation | `M` | Medium | Easily fixable | Antibody, peptide |
| Deamidation | `[STK]N` | Low | Easily fixable | Antibody, peptide |
| Integrin binding | `RGD`, `RYD`, `KGD`, `NGR`, `LDV`, `DGE`, `GPR` | Low | Easily fixable | Antibody, peptide — off by default |
| Missing cysteines | conserved position check | High | Structural | Antibody only |
| Extra cysteines | unpaired cysteine check | High | Hard to fix | Antibody only |

Stop codons and out-of-frame sequences are detected separately and drive the Is Productive column.

Every rule can be switched on or off, and you can add **custom liabilities** of your own: a name, a regex pattern, a risk level, a fixability class, and the regions it applies to. Custom sets can be exported to JSON and imported into another project, so a house liability panel travels between analyses.

## Inputs & outputs

* **Input:** amino acid sequences from bulk or single-cell V(D)J clonotypes, or from peptide and amplicon variant datasets. Antibody and TCR input is evaluated per region, so per-region sequences (FR1–FR4, CDR1–CDR3) give the fullest result.
* **Output:** Developability risk and Developability cost per sequence, Is Productive for antibody and TCR input, and per-region liability annotations recording which motifs were found where — all as columns downstream blocks can filter and rank on.

## Specifications

| | |
|---|---|
| Block title in app | Sequence Liabilities |
| Modalities | Antibodies, TCRs, peptides, amplicon variants |
| Predefined liabilities | 13, covering deamidation, isomerization, fragmentation, hydrolysis, glycosylation, oxidation, integrin binding, and cysteine architecture |
| Custom liabilities | Name, regex pattern, risk level, fixability class, applicable regions; JSON import and export |
| Fixability classes | Easily fixable, fixable, hard to fix, structural |
| Engineering weights | Easily fixable 1, fixable 3, hard to fix 8, structural 20 |
| Region weights (antibody/TCR) | CDR3 1.5, CDR1 1.2, CDR2 1.2, FR1 1.0, FR2 0.5, FR3 0.5, FR4 0.3 |
| Numbering schemes | IMGT and Kabat, for locating conserved cysteines |
| Outputs | Developability risk, Developability cost, Is Productive (antibody/TCR), per-region annotations |

## Use cases

* **Triage before synthesis:** drop candidates carrying structural liabilities and rank the rest by engineering cost, before committing to expression.
* **Developability-aware lead selection:** filter or rank on liability columns in [Lead Selection](https://github.com/platforma-open/antibody-tcr-lead-selection), so the final panel is not compromised on manufacturability.
* **Region-aware assessment:** distinguish a liability in CDR3, where a fix risks binding, from the same motif in a framework region where it is cheap to remove.
* **Library screening:** map liability scores onto the [Sequence Space](https://github.com/platforma-open/clonotype-space) UMAP to see how developability relates to enrichment and diversity across the library.
* **House liability panels:** encode your organization's own motif rules as custom liabilities and reuse the exported JSON across projects.
* **Frame check:** use Is Productive to remove stop-codon and out-of-frame artifacts before any downstream analysis.

## FAQ

### What is a sequence liability?

A short amino acid motif associated with a chemical or biophysical problem in a therapeutic candidate — a deamidation site, an isomerization-prone pair, a fragmentation-prone bond, an N-linked glycosylation sequon, an oxidation-prone residue, or a cysteine that breaks the expected disulfide architecture. Their presence does not disqualify a molecule, but each one is work to remove or a risk to accept.

### What does fixability mean, and why does it matter more than the count?

Fixability is how tractable a liability is to engineer away. An oxidation-prone methionine is usually one conservative substitution; a missing conserved cysteine means the disulfide architecture is broken and the molecule is not viable as-is. Counting hits treats those equally. Weighting by fixability — 1 for easily fixable up to 20 for structural — produces a score that tracks the actual engineering burden.

### Why are liabilities in CDRs weighted more heavily?

Because fixing them is riskier. A substitution in a framework region is usually tolerated; the same change in CDR3 sits in the binding interface and may cost affinity. Region weights (CDR3 1.5 down to FR4 0.3) make a CDR liability count for more in the cost score than an equivalent framework one.

### What is the difference between Developability risk and Developability cost?

Risk is a category for quick filtering — `Non-Developable` and `Very High` tell you a candidate has a structural or hard-to-fix problem. Cost is a continuous score for ranking within a category, summing weighted engineering effort so two `Medium` candidates can still be ordered.

### Does it work on peptides?

Yes. Peptide and amplicon variant input is scanned with the backbone-chemistry rules across the whole sequence. Region weighting, cysteine architecture checks, N-linked glycosylation, and the `TS` fragmentation rule are skipped, since they depend on antibody structure that peptides do not have.

### Can I add my own liability motifs?

Yes. Define a custom liability with a name, a regex pattern, a risk level, a fixability class, and the regions it applies to. Custom sets export to JSON and import into other projects, so an internal liability panel can be shared and reused.

### Why does the numbering scheme matter?

Cysteine checks work by testing whether a conserved cysteine sits where it is expected. That expected position differs between IMGT and Kabat numbering, so selecting the scheme your data uses keeps the missing-cysteine and extra-cysteine calls correct.

### Is Integrin binding off by default?

Yes. Integrin binding motifs are relevant in some programs and not others, so the rule ships disabled and is enabled explicitly when it applies.

## Documentation

Step-by-step guide: [Antibody Sequence Liabilities Assessment](https://docs.platforma.bio/guides/antibody-discovery/sequence-liabilities/)

## Part of the Platforma ecosystem

This block is part of [Platforma](https://platforma.bio/) by [MiLaboratories](https://github.com/milaboratory). Explore the other open-source blocks at [github.com/platforma-open](https://github.com/platforma-open) and the docs for antibody discovery at [docs.platforma.bio/biology-guides/antibody-discovery](https://docs.platforma.bio/biology-guides/antibody-discovery/).
