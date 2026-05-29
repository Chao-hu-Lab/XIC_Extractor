# Tier 2 V0.1 Coherence Diagnostic Validation Note

## Verdict

`diagnostic_only`

This checkpoint implements the v0.1 Tier 2 RAW trace coherence diagnostic
sidecar pilot. It exposes richer evidence context but does not promote retained
provisional rows, does not change `alignment_matrix.tsv`, and does not make
Tier 2 evidence production-ready.

## Verification

```text
Focused pytest:
python -m pytest tests\test_tier2_raw_trace_producer.py tests\test_tier2_raw_trace_reread_producer_cli.py tests\test_production_candidate_gate.py tests\test_provisional_backfill_candidate_gate_cli.py tests\test_alignment_tsv_writer.py::test_direct_tier2_review_token_does_not_change_matrix_writer -q
70 passed in 2.11s

Ruff:
python -m ruff check xic_extractor\alignment\tier2_trace_producer.py xic_extractor\alignment\production_candidate_gate.py tools\diagnostics\tier2_raw_trace_reread_producer.py tools\diagnostics\provisional_backfill_candidate_gate.py tests\test_tier2_raw_trace_producer.py tests\test_tier2_raw_trace_reread_producer_cli.py tests\test_production_candidate_gate.py tests\test_provisional_backfill_candidate_gate_cli.py tests\test_alignment_tsv_writer.py
All checks passed!

8RAW v0.1 producer:
.venv\Scripts\python.exe -m tools.diagnostics.tier2_raw_trace_reread_producer --alignment-dir output\tiered_backfill_candidate_gate_8raw_current --output-dir output\tier2_v0_1_coherence_8raw_current --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --expected-sample-count 8
exit 0; wrote alignment_tier2_trace_evidence.tsv, alignment_tier2_raw_manifest.tsv, alignment_tier2_trace_evidence_summary.json

8RAW v0.1 gate consume:
python -m tools.diagnostics.provisional_backfill_candidate_gate --alignment-dir output\tiered_backfill_candidate_gate_8raw_current --output-dir output\tier2_v0_1_coherence_8raw_current_gate --tier2-trace-evidence-tsv output\tier2_v0_1_coherence_8raw_current\alignment_tier2_trace_evidence.tsv --tier2-raw-manifest-tsv output\tier2_v0_1_coherence_8raw_current\alignment_tier2_raw_manifest.tsv
exit 0; diagnostic_only 7 0 False False
```

The first 8RAW producer attempt in the normal sandbox stopped before execution
because the RAW-capable `.venv` could not import NumPy native DLLs
(`DLL load failed ... access denied`). The same documented command succeeded
after approval to run outside the sandbox.

## 8RAW Summary

Producer:

- readiness: `diagnostic_only`
- criteria version: `tier2_trace_identity_rescued_coherence_v0_1_diagnostic`
- producer version: `raw_trace_reread_tier2_v0_1`
- rows evaluated: `7`
- evidence status: `inconclusive=7`
- positive support count: `0`
- production ready: `false`
- matrix contract changed: `false`

`positive_support_count=0` is the expected diagnostic v0.1 outcome. It means
the sidecar is observable and safely non-promoting; it is not a failed product
gate.

Gate consume:

- readiness: `diagnostic_only`
- row count: `7`
- gate status: `audit=7`
- production candidate count: `0`
- production ready: `false`
- matrix contract changed: `false`

Producer blocker distribution:

```text
tier2_v0_1_diagnostic_only;metric_unavailable;weak_scan_support: 1
tier2_v0_1_diagnostic_only;rescued_boundary_overlap_low: 1
tier2_v0_1_diagnostic_only;rescued_apex_span_wide;rescued_boundary_overlap_low: 3
tier2_v0_1_diagnostic_only;metric_unavailable: 1
tier2_v0_1_diagnostic_only;metric_unavailable;low_scan_support: 1
```

Gate blocker distribution:

```text
metric_unavailable;weak_scan_support;tier2_v0_1_diagnostic_only: 1
rescued_boundary_overlap_low;tier2_v0_1_diagnostic_only: 1
rescued_apex_span_wide;rescued_boundary_overlap_low;tier2_v0_1_diagnostic_only: 3
metric_unavailable;tier2_v0_1_diagnostic_only: 1
low_scan_support;metric_unavailable;tier2_v0_1_diagnostic_only: 1
```

## Artifacts

```text
output\tier2_v0_1_coherence_8raw_current\alignment_tier2_trace_evidence.tsv
SHA256 31497C66853211ABE5442430D490C8FA77CD5BD79810489AFAC86AC7B37B48FC

output\tier2_v0_1_coherence_8raw_current\alignment_tier2_raw_manifest.tsv
SHA256 66ECF86489C3AAB82D6E9A0BCEDB0B15DBD8F76EED0335167F3581AB99C70C76

output\tier2_v0_1_coherence_8raw_current\alignment_tier2_trace_evidence_summary.json
SHA256 0970AEBFA8F13DAD65D9F5484707B228C3B7C1C07AEF3216319C64EA313FA5C6

output\tier2_v0_1_coherence_8raw_current_gate\alignment_production_candidate_gate.tsv
SHA256 D503CEDF5C5A8341BAB645D8F0A22A201059F3D1D3A220CE1963F497AC2D9FC2

output\tier2_v0_1_coherence_8raw_current_gate\alignment_production_candidate_gate.json
SHA256 7450990B6216A71ECE3C20F6DB2A628FF2E0012C6871D85C8F89F9EE744920A6
```

## Contract State

- v0.1 criteria version:
  `tier2_trace_identity_rescued_coherence_v0_1_diagnostic`.
- v0.1 sidecars are diagnostic context only.
- Legacy v0 sidecars remain loadable for the existing diagnostic-gate
  compatibility contract.
- Scan count is separated from signal/shape/noise context.
- Boundary overlap exposes seed-vs-rescued, rescued-pairwise, and family
  consensus views.
- Apex span exposes raw, seed-to-rescued, and rescued-only views.
- Neighbor interference remains `not_assessed` context.
- `alignment_matrix.tsv` is unchanged by this checkpoint.

## Residual Risk Closeout

### Closed In This Checkpoint

- Promotion leakage is closed for v0.1 diagnostic sidecars. The 8RAW rerun has
  `evidence_status=inconclusive` for all 7 rows, `positive_support_count=0`,
  gate `audit=7`, and `production_candidate_count=0`. The producer invariant
  check found no row missing `tier2_v0_1_diagnostic_only`.
- Uncomputed neighbor interference is explicit context, not a hidden positive
  criterion. All 7 producer rows report `neighbor_interference_status=not_assessed`.
- Scan support is no longer only a scan-count ratio in the sidecar surface.
  v0.1 records scan availability, apex intensity, baseline noise,
  signal-to-noise proxy, and apex prominence as diagnostic context.
- Boundary-reference ambiguity is surfaced rather than collapsed. v0.1 emits
  seed-vs-rescued, rescued-pairwise, and family-consensus overlap fields.
- Apex-span drift risk is bounded as diagnostic evidence. v0.1 emits raw,
  seed-to-rescued, and rescued-only apex spans, but none of those fields can
  promote a row.
- Stale-artifact risk is bounded by source and output SHA256 hashes in the
  summary artifacts and this note. Future reruns must compare the same source
  alignment, candidate subset, manifest, and gate artifacts before using the
  results as a baseline.
- 85RAW scope creep is closed for this checkpoint. No 85RAW command was run, and
  this note does not authorize a larger validation run.

### Still Open But Bounded

- Biological sufficiency is not established. The 8RAW subset has only 7 retained
  provisional rows and is biased toward rows that survived the previous
  diagnostic gate.
- Threshold calibration is not established. Zero positive support is the desired
  diagnostic-only safety outcome, but it also means this run cannot tune a
  future production-positive threshold.
- Signal, shape, and noise fields are diagnostic proxies. They are useful for
  row review and failure-mode clustering, not validated scoring features.
- Boundary-overlap and apex-span blockers may still over-penalize real RT drift
  or matrix-specific behavior. This is especially relevant because 3 of 7 rows
  have both `rescued_apex_span_wide` and `rescued_boundary_overlap_low`.
- Neighbor interference remains external to v0.1 positive criteria until a
  formal computation exists. The current status is `not_assessed`, not pass.
- Legacy v0 compatibility remains compatibility only. It keeps committed
  diagnostic sidecars readable; it is not a product promotion path.

### Next Decision

Current closeout verdict: `diagnostic_only`; product readiness remains
`inconclusive`.

Do not run 85RAW as the immediate next action. First review the 7-row v0.1
evidence surface, preferably through a compact row index or targeted EIC/manual
inspection, and decide whether the v0.1 criteria should be promoted to a shadow
contract, killed, or externalized as review-only context. A later 85RAW run
needs a reviewed follow-up plan that names the decision it can close, the oracle
it will use, expected runtime/artifacts, and the fail-fast or inconclusive path.
