# Handoff Phase Closeout Contract Fixture

Status: `fixture`

This fixture preserves the small executable closeout matrix contract used by
`tests/test_handoff_phase_closeout_contract.py`. It is not a branch diary.

## Legacy Retirement Readiness Matrix

| Surface | Owner | Label | Evidence | Blocker | Next action | Next PR target |
| --- | --- | --- | --- | --- | --- | --- |
| `TraceGroup` / trace context | `peak_detection.traces`, `extraction.trace_context`, `alignment.trace_context` | `keep_for_now` | Future-facing trace wrapper. | Semantics are not universal across targeted and untargeted paths. | Keep as spine contract. | No |
| `PeakHypothesis` / `EvidenceVector` / `IntegrationResult` / `AuditTrail` | `peak_detection.hypotheses` | `keep_for_now` | Candidate and boundary projections can build rows from hypotheses. | Evidence schema is still evolving. | Treat as preferred domain model, not universal scoring authority. | No |
| `handoff_spine_runtime.py` | `extraction.handoff_spine_runtime` | `keep_for_now` | `selected_handoff_peak(...)` is called by targeted extraction. | Alignment matrix does not consume it. | Keep as targeted bridge. | No |
| `ExtractionResult.selected_hypothesis` and selected integration accessors | `extractor.ExtractionResult` | `facade_only` | Targeted CSV projection reads reported accessors. | Compatibility result still stores legacy peak data. | New consumers should use spine-facing accessors. | No |
| Targeted CSV projection | `output.csv_writers` | `facade_only` | Writer protocol includes reported peak area, intensity, boundary, width, and RT accessors. | Emitted CSV remains public compatibility surface. | Preserve schema. | No |
| `peak_candidates.tsv` / `peak_candidate_boundaries.tsv` projection builders | `extraction.peak_candidate_table`, `output.peak_candidates` | `externalize` | Debug/audit projections with frozen headers. | Useful review artifacts but not canonical product matrix. | Keep optional and non-authoritative. | No |
| `PeakDetectionResult` / `PeakCandidate` / `PeakResult` | `peak_detection.models`, `signal_processing` compatibility facade | `needs_behavior_spec` | Resolver output, scoring context, messages, detection, and fallback behavior still depend on these models. | Retirement could change production selection, messaging, or compatibility imports. | Keep active until a behavior spec migrates one owner at a time. | No |
| `output.messages` and `output.detection` | `output.messages`, `output.detection` | `keep_for_now` | Active user-facing message and counted-detection semantics. | Rules are not fully represented in the hypothesis spine. | Migrate only with message/detection parity tests. | No |
| Anchor diagnostics and ISTD recovery helpers | `extraction.istd_recovery`, alignment / RT diagnostic helpers | `keep_for_now` | Domain-specific recovery and RT evidence behavior used by current outputs and diagnostics. | Spine does not own anchor recovery policy or RT correction semantics. | Keep separate until a behavior spec names the policy. | No |
| `alignment_matrix.tsv` / `AlignedCell` / owner-backfill path | `alignment.matrix`, `alignment.pipeline`, `alignment.backfill` | `needs_behavior_spec` | Alignment output is still produced by alignment cell and owner/backfill models. | Migration can affect matrix values, cell status, and benchmark validation. | Write a parity / behavior spec for spine-derived matrix handoff before migration. | Yes |
| Legacy resolver surfaces | resolver modules and `signal_processing` facade | `needs_behavior_spec` | Resolver choice and selected peak behavior remain production semantics. | Retirement or default switch changes selected RT, boundary, or area behavior. | Keep until a reviewed resolver behavior plan authorizes promotion or retirement. | No |
| Baseline / ASLS surfaces | baseline integration modules and recent baseline specs | `needs_behavior_spec` | ASLS and baseline truth work support future behavior decisions. | Baseline change affects area and requires its own behavior acceptance. | Keep separate from handoff closeout. | No |

## Recommended Next PR

Recommended next PR: `alignment_matrix_handoff_behavior_spec`.
