# Red Flags And Search

## Red Flags

Stop and rethink when:

- a new diagnostic tool needs its own TSV parser, bool/float parser, or row
  grouping helper;
- a writer computes domain evidence or reads RAW;
- a diagnostic sidecar starts to look like production behavior without an exit
  rule;
- a product gate grows by adding dataset-specific adjectives instead of a
  domain-meaningful rule and evidence test;
- 85RAW shape or CID-NL assumptions appear in core models as permanent product
  boundaries;
- correctness is preserved but RAW calls, TSV scans, or smoothing operations
  scale per row when they could be batched or cached;
- a new evidence source wants to write the matrix directly instead of becoming
  evidence for model selection.

## Minimal Search

Use targeted search before coding:

```powershell
rg -n "<concept>|<schema>|<helper>|<evidence-name>" xic_extractor tools tests docs
rg -n "read_tsv|write_tsv|optional_float|EvidenceVector|PeakHypothesis|Activation|value_delta" xic_extractor tools tests
```

Use CodeGraph only when structural caller/callee impact would answer ownership
faster than text search.
