---
"@platforma-open/milaboratories.antibody-sequence-liabilities.workflow": minor
"@platforma-open/milaboratories.antibody-sequence-liabilities": minor
"@platforma-open/milaboratories.antibody-sequence-liabilities.model": minor
---

Update the SDK and build the dataset list with buildDatasetOptions (requireEnrichments: false), replacing the custom merge of datasets and their subset filters. With a subset filter, the repertoire parent column is now left-joined onto the filtered rows, which removes the post-build step that dropped the rows it brought back. Results are unchanged.
