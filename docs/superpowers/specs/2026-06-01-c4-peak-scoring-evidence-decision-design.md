# C4 — Peak Scoring Evidence-Decision Design

**Date:** 2026-06-01
**Status:** Phase 4 design closeout v0.6 — C4-1 scorer-to-successor field map
**Readiness label:** `diagnostic_only`
**Supersedes for implementation:** [C4 peak_scoring split spec](2026-05-24-peak-pipeline-cleanup-peak-scoring-split-spec.md)
**Depends on:** [C3 hypothesis model unification spec](2026-05-24-peak-pipeline-cleanup-hypothesis-model-unification-spec.md)
**One-goal contract:** [Peak pipeline cleanup one-goal phase contract](2026-06-01-peak-pipeline-cleanup-one-goal-phase-contract-spec.md)

## Verdict

C4 is not a package split. The old plan to convert
`xic_extractor/peak_scoring.py` into a `xic_extractor/peak_scoring/` package is
historical only.

The current problem is responsibility overlap between legacy scoring,
`PeakHypothesis` / `EvidenceVector`, and cross-surface evidence semantics. C4
must not preserve two semantically similar systems indefinitely. The product
priority is fusion-first:

- migrate still-valid scoring invariants into the hypothesis/evidence spine;
- keep legacy scorer code only where it is still the active production decision
  policy;
- reduce legacy surfaces to compatibility adapters when successor coverage
  exists;
- delete implementation-specific legacy tests after successor tests protect the
  product invariant.

Phase 4 itself is docs-only. It authorizes no scorer movement and no confidence,
reason, score, selection, matrix, TSV, or workbook behavior change.

## Fusion-First Decision

C4 uses the same semantic-survival rule as C6: tests and modules protect product
invariants, not historical implementation shapes.

For every scorer responsibility, future C4 work must choose one disposition:

- `successor_owned` - `PeakHypothesis`, `EvidenceVector`, `CommonEvidence`, or a
  future model-selection layer already owns the invariant; migrate tests and
  remove legacy implementation-specific coverage.
- `active_policy` - `peak_scoring.py` still owns production selection,
  confidence, caps, or review-only decisions; characterize it before movement.
- `compatibility_adapter` - the old public API remains temporarily, but delegates
  to the successor or preserves import/config compatibility.
- `retire_candidate` - no production, diagnostic, public import, or migration
  value remains; delete with a rollback/verification plan.

Maintaining both old scorer semantics and new evidence-spine semantics is only a
temporary migration state.

## Pilot Role

C4 is the scorer/evidence pilot for the broader technical-debt roadmap. Its job
is to prove the fusion-first cleanup method on a real overlap surface:

```text
legacy scoring facts / policy / projection
  -> successor evidence and hypothesis semantics where covered
  -> explicit active-policy boundary where not covered
  -> compatibility adapter or retirement after tests migrate
```

Future project-wide cleanup should reuse C4's output shape: responsibility map,
successor candidate, product invariant, consumer surface, test-retirement table,
and exit rule. C4 should not be treated as proof that every legacy scorer helper
is dead; it is proof that every overlapping helper needs a disposition.

## Current Evidence Surfaces

| Surface | Current role | C4 contract |
|---|---|---|
| `EvidenceScore` in `peak_scoring_evidence.py` | Weighted scoring result: raw score, confidence, support labels, concern labels, caps | Active scoring output today; likely becomes an adapter/projection into `EvidenceVector` if successor policy owns confidence. |
| `EvidenceVector` in `peak_detection/hypotheses.py` | Per-hypothesis audit carrier populated from scorer output, candidate fields, and MS2 evidence | Successor audit/evidence carrier. Should absorb still-valid evidence invariants instead of duplicating scorer-specific tests. |
| `CommonEvidence` / `EvidenceSignalSet` in `evidence_semantics.py` | Cross targeted/discovery/alignment semantic layer and evidence-coherence classifier | Successor shared-evidence semantics. Should own cross-surface evidence meanings, not scoring-weight mechanics. |
| `ScoringContext` in `peak_scoring.py` | Extraction-time input bundle for the scorer | Legacy input adapter. Candidate for fusion into `TraceGroup` / `EvidenceVector` fact construction once selection policy migration is defined. |

## Semantic-Survival Inventory

| Legacy responsibility | Current owner | Successor candidate | Current disposition | Required C4 decision |
|---|---|---|---|---|
| Candidate evidence facts: local S/N, shape, RT prior, MS2/NL, trace quality | `ScoringContext`, severity helpers, `score_candidate(...)` | `EvidenceVector`, `CommonEvidence`, `TraceGroup` fact extraction | `successor_owned` or `semantic_migration_candidate` depending on field | Map each fact to successor field/test before deleting scorer-specific tests. |
| Weighted score and confidence caps | `EvidenceScore`, `score_evidence(...)`, `_evidence_from_context(...)` | Future hypothesis decision policy, if adopted | `active_policy` today | Keep as production policy until a successor policy reproduces score/confidence/review-only parity. |
| Candidate selection and tie-breaks | `select_candidate_with_confidence(...)` | Future model selection over `PeakHypothesis` | `active_policy` today | Do not delete until `PeakHypothesis` model selection proves selected-candidate parity. |
| Reason and score breakdown projection | `build_evidence_reason(...)`, `score_breakdown_fields(...)` | Public projection from `EvidenceVector` / selected hypothesis | `compatibility_adapter` candidate | Migrate projection tests to successor output; keep exact public text until schema/copy migration is approved. |
| Public imports from `xic_extractor.peak_scoring` | `peak_scoring.py` module | Compatibility facade | `compatibility_adapter` | Preserve imports during migration; delete facade only with explicit public migration plan. |
| Legacy implementation-specific tests | `tests/test_peak_scoring*.py`, selection/scoring fixtures | Successor invariant tests | `semantic_migration_candidate` | Port product invariants, then delete tests that only assert old implementation mechanics. |

Current labels such as `strict_nl_ok`, `ms2_trace_strong`, `rt_prior_close`,
`local_sn_strong`, `shape_clean`, `trace_clean`, and
`cwt_same_apex_support` are already product evidence. C4 must not duplicate
them into a fourth evidence model.

## C4-0 Concrete Audit Snapshot

Current CodeGraph / `rg` evidence shows a split result:

- `score_candidate(...)` is reached through
  `peak_detection/facade._score_with_context(...)` and audit rescoring in
  `extraction/peak_candidate_table.py`, and
  `select_candidate_with_confidence(...)` is reached through
  `peak_detection/facade.find_peak_and_area(...)`. This is still active
  production peak selection, not dead code.
- `EvidenceVector` is populated from current scorer output by
  `peak_detection/hypotheses._evidence_from_candidate(...)`. It carries
  `confidence`, `raw_score`, support/concern/cap labels, reason, quality flags,
  MS2/NL facts, CWT facts, and `CommonEvidence`. That means the successor spine
  already projects much of the scorer's evidence, but it does not yet choose the
  peak.
- `CommonEvidence` already normalizes targeted, discovery, and aligned-cell
  evidence surfaces. It is a shared semantic owner, not a replacement for the
  current scorer's weighted selection policy.

| Legacy surface | Current consumer evidence | Successor overlap | Concrete decision | Test migration / exit rule |
|---|---|---|---|---|
| Evidence fact extraction from `ScoringContext`: local S/N, shape/noise, RT prior, RT centrality, MS2/NL, MS2 trace, CWT support, quality flags | `extraction/scoring_factory.py`, `extraction/jobs.py`, `extraction/serial_backend.py`, `peak_detection/facade.py`; tests in `tests/test_scoring_context.py`, `tests/test_peak_scoring.py` | `EvidenceVector` and `CommonEvidence` already carry many fields after scoring | `semantic_migration_candidate`; do not delete while it is the scoring input adapter | Map each field to `EvidenceVector` / `CommonEvidence` or a future `TraceGroup` fact builder. Port field-level invariants first; then reduce `ScoringContext` tests to adapter coverage. |
| Weighted score, thresholds, confidence caps, and review-only caps | `score_candidate(...)`, `score_evidence(...)`, `peak_detection/facade.py`, `extraction/peak_candidate_table.py`; tests in `tests/test_peak_scoring_evidence.py` and score/cap sections of `tests/test_peak_scoring.py` | No successor policy reproduces score/confidence/cap parity yet | `active_policy` | Keep. Exit only after a named model-selection policy reproduces raw score, confidence, cap labels, review-only status, and reason parity. |
| Candidate selection and tie-breaks | `find_peak_and_area(...)` calls `select_candidate_with_confidence(...)`; tests in `tests/test_peak_scoring_selection.py`, `tests/test_signal_processing_selection.py`, `tests/test_scoring_context.py` | `PeakHypothesis` records rank/selected/rejection, but does not select candidates independently | `active_policy` | Keep. Exit only when selected `PeakHypothesis` model selection matches current selected candidate across RT-distance, effective-score, low-scan, dominant-area, paired-prior, and quality-penalty fixtures. |
| Reason text and `score_breakdown_fields(...)` projection | Candidate table, CSV/XLSX/public output columns, tests in reason-text sections of `tests/test_peak_scoring.py`, `tests/test_peak_candidate_table.py`, `tests/test_csv_writers.py` | `EvidenceVector.reason`, support/concern/cap labels can become source of projection | `compatibility_adapter` candidate | Keep exact text/schema until public output migration is approved. Projection tests may move to successor output tests, but copy/schema parity remains required. |
| `EvidenceScore` arithmetic helper | `peak_scoring.py` and `tests/test_peak_scoring_evidence.py` | Future policy may absorb or replace it, but no current replacement exists | `active_policy` support utility | Keep as scorer utility. It can move only with score/confidence parity and public import compatibility. |
| CWT and MS2 trace support labels | `score_candidate(...)`, `EvidenceVector`, candidate table output; tests around `cwt_same_apex_support`, MS2 trace tie-breaks, and "does not override RT distance" | Successor carries CWT/MS2 facts, but CWT is not validated as standalone chemistry authority | `semantic_migration_candidate` with active guardrails | Preserve guardrail tests until C3/CWT evidence-chain work owns "support only with chemical/selection context" and "does not override RT distance" invariants. |
| Public imports from `xic_extractor.peak_scoring` | Direct imports in extraction, facade, tests, and any external code relying on the public surface | Compatibility facade is the successor shape | `compatibility_adapter` | Keep until an explicit public migration/deprecation plan exists. Import-smoke tests remain while facade exists. |

### C4-0 Test Retirement Table

| Test family | Current value | Migration action |
|---|---|---|
| `tests/test_peak_scoring_selection.py` | Protects active production candidate selection and tie-break policy. | Keep. Later port to `PeakHypothesis` model-selection parity only after successor selection exists. |
| `tests/test_peak_scoring_evidence.py` | Protects weighted score arithmetic and cap behavior. | Keep while `EvidenceScore` is active policy support. |
| `tests/test_peak_scoring.py` scorer sections | Mixed: active score/cap/selection evidence plus projection text and field-level fact extraction. | Split conceptually during C4 implementation: active policy tests stay; projection tests may move; pure implementation-mechanic tests can retire only after successor field coverage exists. |
| `tests/test_scoring_context.py` | Protects adapter construction of RT, NL/MS2, and ASLS/local S/N facts. | Keep now; later reduce after `TraceGroup` / `EvidenceVector` fact construction owns the same facts. |
| `tests/test_peak_hypotheses.py` and `tests/test_evidence_semantics.py` | Successor spine coverage for hypothesis/evidence projection. | Expand these when migrating scorer facts; they are not yet enough to delete scorer policy tests. |
| Candidate-table / CSV writer / result assembly tests | Protect public projection and output schema. | Keep as public-contract parity until output schema/copy migration is approved. |

C4-0 conclusion: C4 is ready for a bounded migration audit, but not for scorer
deletion. The next implementation slice should start with a scorer-to-successor
field map and test-retirement plan, not code movement.

## C4-1 Scorer Fact To Successor Field Map

This is the concrete field map for the next C4 implementation planning slice.
It separates facts already carried by the successor spine from facts that remain
scorer-owned policy or are missing a successor home.

| Scorer fact / policy | Current scorer source | Successor field today | Current judgment | Required migration action |
|---|---|---|---|---|
| Selected candidate confidence, raw score, support labels, concern labels, cap labels, reason | `EvidenceScore`, `ScoredCandidate`, `_candidate_score_summary(...)` | `EvidenceVector.confidence`, `raw_score`, `support_labels`, `concern_labels`, `cap_labels`, `reason`; `CommonEvidence.confidence`, `evidence_score`, `reason` | `successor_projection`, not successor policy | Keep scorer as authority. Successor tests may assert projection parity, but deletion requires independent model-selection parity. |
| Candidate MS1 apex, area, height, boundaries | `PeakCandidate.peak`, selected candidate summary | `CommonEvidence.ms1_apex_rt_min`, `ms1_area`, `ms1_height`, `ms1_peak_rt_start`, `ms1_peak_rt_end`; `IntegrationResult` | `successor_owned` for audit/projection | Move output-facing tests to hypothesis/evidence projection when convenient; no scorer policy migration needed. |
| MS2 present and strict NL match | `ScoringContext.ms2_present`, `nl_match`, `neutral_loss_required`; `nl_support_severity(...)` | `EvidenceVector.ms2_present`, `nl_match`, `nl_status`, `best_loss_ppm`, product/trigger fields; `CommonEvidence.ms2_present`, `nl_match`, `neutral_loss_error_ppm`; `canonical_support_labels(...)` / `canonical_concern_labels(...)` | Evidence fact is successor-owned; scoring weight/cap remains active policy | Port fact-projection tests to `tests/test_peak_hypotheses.py` / `tests/test_evidence_semantics.py`. Keep `nl_fail_cap`, `no_ms2_cap`, and scoring thresholds in scorer tests until model policy migrates. |
| MS2 trace strength and sparse-apex fallback guard | `ScoringContext.ms2_trace_strength`, `ms2_alignment_source`, `trigger_scan_count`, `strict_nl_scan_count`; `_is_sparse_apex_fallback_ms2(...)` | `EvidenceVector.ms2_trace_strength`, `ms2_alignment_source`, `trigger_scan_count`, `strict_nl_scan_count`; `CommonEvidence.ms2_trace_strength` | Partially successor-owned; sparse-apex guard remains scorer policy | Add successor projection tests for trace metadata. Keep scorer tests for `sparse_apex_ms2`, strong/moderate/weak score effects, and "does not override RT distance" until selection policy migrates. |
| RT prior value and paired ISTD tie-break preference | `ScoringContext.rt_prior`, `rt_prior_sigma`, `prefer_rt_prior_tiebreak`; `rt_prior_severity(...)`; `paired_istd_aligned` label | `EvidenceVector.rt_prior_min`; `PeakHypothesis.audit.selection_reference_rt_min`; no sigma/severity/tie-break owner | `active_policy` with incomplete successor fields | Do not delete. If successor owns this later, add `rt_prior_sigma` / severity or explicit model-selection inputs and selected-candidate parity for paired-prior tests. |
| RT centrality and target-window cap | `ScoringContext.rt_min`, `rt_max`; `rt_centrality_severity(...)`; `rt_window_cap` | Candidate boundaries and integration data exist, but no explicit `EvidenceVector` target-window/cap owner except projected `cap_labels` | `active_policy` | Keep scorer tests. Future migration needs explicit target-window fact fields or a model-selection contract plus unchanged output reason/cap parity. |
| Local S/N | `local_sn_severity(...)` over `intensity_array`, `apex_index`, `baseline_array`, `residual_mad`, `dirty_matrix` | Only projected labels in `EvidenceVector.support_labels` / `concern_labels`; no numeric local-S/N fact | `semantic_migration_candidate` but missing successor field | Add a successor fact field or typed evidence component before retiring `tests/test_local_sn_*` coverage. Scorer remains authority for score effect. |
| Shape, width, and noise quality | `half_width_ratio`, `fwhm_ratio`, `symmetry_severity(...)`, `peak_width_severity(...)`, `noise_shape_severity(...)` | `EvidenceVector` has region audit fields and labels, but not half-width/FWHM/noise severity as typed facts | `semantic_migration_candidate` but missing successor field | Decide whether shape belongs to `TraceGroup`, `EvidenceVector`, or a future model-selection feature vector. Port invariants before deleting shape severity tests. |
| Trace quality flags and ADAP-like soft flags | `trace_quality_severities(...)`, `candidate_quality_penalty(...)`, `candidate_selection_quality_penalty(...)`, `hard_quality_flags(...)` | `EvidenceVector.quality_flags`; `CommonEvidence.trace_quality`; canonical concerns include `trace_quality_review` | Fact projection exists; penalty/cap policy remains scorer-owned | Keep scorer policy tests for selection penalty, hard flag caps, and ADAP-equivalent suppression. Successor can own raw flag projection now. |
| CWT same-apex support | `_has_same_apex_cwt_support(...)`, `_has_cwt_chemical_support(...)`, legacy CWT presence metrics | `EvidenceVector.cwt_best_scale`, `cwt_ridge_persistence`; support label projection; `EvidenceVector` doc says legacy fields are audit-presence flags only | `semantic_migration_candidate` with active guardrails | C3/CWT evidence-chain work must own the chemistry/shape interpretation before deletion. Keep tests that CWT requires chemical context and cannot override RT-distance selection. |
| Weighted score arithmetic, thresholds, confidence caps | `score_evidence(...)`, `confidence_from_score(...)`, `apply_confidence_caps(...)`, `_is_review_only_evidence(...)` | Projected into `EvidenceVector` only after scorer runs | `active_policy` | Keep. Exit requires future model-selection policy with exact raw score/confidence/cap/review-only parity or an approved behavior-change spec. |
| Candidate selection and tie-breaks | `select_candidate_with_confidence(...)`, effective score, RT distance, low-scan/dominant-area demotion, MS2 trace tie-break, quality penalties | `PeakHypothesis.audit.selected`, `selection_rank`, rejection reason are downstream records of the scorer-selected result | `active_policy` | Keep. Future model-selection successor must reproduce selected-candidate parity across `tests/test_peak_scoring_selection.py` before deleting scorer selection tests. |
| Reason and score breakdown output | `build_evidence_reason(...)`, `score_breakdown_fields(...)` | `EvidenceVector.reason`, labels, caps; candidate table / CSV / XLSX projections | `compatibility_adapter` candidate | May move to a projection module only with exact public text/schema parity. Do not couple projection extraction to selection-policy movement. |

### C4-1 Next Slice Contract

The next C4 implementation slice, if executed, should be docs/test-first and
bounded:

1. Add or update successor projection tests for facts already carried by
   `EvidenceVector` / `CommonEvidence`: MS1 geometry, MS2/NL facts, MS2 trace
   metadata, scorer output labels, and CWT audit-presence fields.
2. Do not move score arithmetic, confidence caps, RT prior/centrality policy,
   local S/N computation, shape severity, or candidate selection until a
   successor owner is named.
3. Create a temporary scorer-to-successor parity fixture before deleting any
   scorer test.
4. Reclassify each migrated test as `successor_projection`,
   `successor_owned`, `active_policy`, `compatibility_adapter`, or
   `semantic_migration_candidate`.

Stop if the slice requires changed confidence, reason text, selected candidate,
cap labels, candidate table columns, CSV/XLSX output, or `PeakHypothesis` audit
fields. That is a behavior/spec change, not cleanup.

### C4-1 Execution Closeout

Phase 1 added a successor-projection parity test without moving scorer policy:

- `tests/test_peak_hypotheses.py::test_build_peak_hypotheses_projects_scorer_facts_to_successor_evidence`
  locks scorer output labels/reason, MS1 geometry, MS2/NL facts, MS2 trace
  metadata, quality flags, RT prior value, CWT audit-presence fields, and
  `CommonEvidence` projection onto the successor evidence spine.
- No scorer policy, confidence caps, selected-candidate logic, score arithmetic,
  local S/N, shape severity, RT-window behavior, CSV schema, or workbook output
  moved in this slice.
- No scorer tests were deleted. Active policy tests remain the authority for
  scorer-owned behavior.

| C4-1 row | Closeout classification | Named test family / missing field |
|---|---|---|
| Selected candidate confidence, raw score, support/concern/cap labels, reason | `successor_projection` | Projected by `tests/test_peak_hypotheses.py::test_build_peak_hypotheses_projects_scorer_facts_to_successor_evidence`; public projection still covered by candidate-table / CSV writer tests. Scorer remains authority. |
| Candidate MS1 apex, area, height, boundaries | `successor_owned` for audit/projection | `tests/test_peak_hypotheses.py::test_build_peak_hypotheses_projects_scorer_facts_to_successor_evidence` and `tests/test_evidence_semantics.py::test_targeted_candidate_projects_to_common_ms1_ms2_evidence`. |
| MS2 present and strict NL match | Evidence fact is `successor_owned`; score/cap policy is `active_policy` | Projection covered by the new hypothesis test and `tests/test_evidence_semantics.py::test_targeted_candidate_projects_to_common_ms1_ms2_evidence`; `nl_fail_cap`, `no_ms2_cap`, and scoring thresholds remain in scorer tests. |
| MS2 trace strength and sparse-apex fallback guard | Trace metadata is `successor_projection`; sparse-apex guard remains `active_policy` | Trace metadata covered by the new hypothesis test. Sparse-apex, strong/moderate/weak effects, and "does not override RT distance" remain in `tests/test_peak_scoring.py` and `tests/test_scoring_context.py`. |
| RT prior value and paired ISTD tie-break preference | `active_policy` with partial projection | `rt_prior_min` projection covered by the new hypothesis test. Missing successor fields remain `rt_prior_sigma`, RT-prior severity, and paired-prior tie-break inputs; keep scorer selection tests. |
| RT centrality and target-window cap | `active_policy` | Missing successor fields remain explicit target-window/cap facts beyond projected `cap_labels`; keep scorer tests for `rt_window_cap` and RT centrality. |
| Local S/N | `semantic_migration_candidate` | Only label projection exists today. Missing successor field: numeric local-S/N fact or typed evidence component; keep local-S/N scorer coverage. |
| Shape, width, and noise quality | `semantic_migration_candidate` | Missing successor fields: half-width/FWHM/noise severity typed facts; keep shape/noise scorer coverage. |
| Trace quality flags and ADAP-like soft flags | Raw flag projection is `successor_projection`; penalty/cap policy remains `active_policy` | Quality flag projection covered by the new hypothesis test and `CommonEvidence.trace_quality` tests. Penalty, hard caps, and ADAP-equivalent suppression stay in scorer tests. |
| CWT same-apex support | CWT audit fields are `successor_projection`; chemistry/selection guardrails remain `semantic_migration_candidate` | CWT field/support-label projection covered by the new hypothesis test. Guardrails remain in `tests/test_peak_scoring.py` and C3/CWT evidence-chain work. |
| Weighted score arithmetic, thresholds, confidence caps | `active_policy` plus `successor_projection` result fields | Projected `raw_score`, `confidence`, and cap labels covered by the new hypothesis test; arithmetic/caps stay in `tests/test_peak_scoring_evidence.py` and `tests/test_peak_scoring.py`. |
| Candidate selection and tie-breaks | `active_policy` | Keep `tests/test_peak_scoring_selection.py` and `tests/test_signal_processing_selection.py`; successor model-selection parity does not exist yet. |
| Reason and score breakdown output | `compatibility_adapter` candidate | `EvidenceVector.reason` / `CommonEvidence.reason` projection covered by the new hypothesis test; public text/schema parity remains in candidate-table and CSV writer tests. |

## Future Slice Contract

| Slice | Owner | Preserved public API | Parity surface before implementation | Exit rule |
|---|---|---|---|---|
| C4-0 semantic-survival audit | C4 design/spec owner | No code movement; existing scorer and hypothesis imports remain valid. | CodeGraph consumer scan, scorer-to-successor invariant map, and test-retirement table for `tests/test_peak_scoring*.py`, `tests/test_peak_hypotheses.py`, candidate-table tests, and selection tests. | Stop if any proposed deletion lacks successor invariant coverage or public compatibility plan. |
| C4-A projection boundary | `peak_scoring.py` remains the public owner; optional internal owner is `peak_scoring_projection.py` for pure reason/breakdown formatting only. | `from xic_extractor.peak_scoring import build_evidence_reason, score_breakdown_fields` remains valid, along with current scorer imports. | Exact `reason` strings, `score_breakdown_fields(...)` ordering, support/concern/cap label projection, candidate/boundary TSV scoring columns, CSV/XLSX confidence display. | Stop if projection extraction needs `_is_review_only_evidence(...)`, `_evidence_from_context(...)`, `score_candidate(...)`, candidate selection, or any changed score/confidence/reason text. |
| C4-B evidence input mapping | Existing `evidence_semantics.py`, `peak_scoring_evidence.py`, and `peak_detection/hypotheses.py` adapters own the mapping; no new evidence product is introduced. | Existing `EvidenceScore`, `EvidenceVector`, `CommonEvidence`, and `EvidenceSignalSet` import paths remain valid. | `tests/test_evidence_semantics.py`, `tests/test_peak_scoring_evidence.py`, `tests/test_peak_hypotheses.py`, candidate-table projection tests, and a named mapping parity fixture before code movement. | Stop if mapping recomputes scoring, creates a fourth evidence model, or treats CWT audit-presence fields as validated CWT scale/ridge quality. |
| C4-C decision policy boundary | `peak_scoring.py` owns policy until a dedicated policy module is separately justified; public scorer API remains stable. | `score_candidate(...)`, `select_candidate_with_confidence(...)`, severity helpers, `Confidence`, `ScoredCandidate`, and `ScoringContext` imports remain valid. | `tests/test_peak_scoring.py`, `tests/test_peak_scoring_selection.py`, `tests/test_scoring_context.py`, `tests/test_signal_processing_selection.py`, plus selected-candidate/confidence/reason parity. | Stop and write a behavior spec if score, confidence, review-only status, selected candidate, tie-breaks, reason text, or output schema changes. |

## Public API Inventory

Current `rg` shows these public consumers of `xic_extractor.peak_scoring`:

- `peak_detection/facade.py`: `ScoringContext`, `score_breakdown_fields`,
  `score_candidate`, `select_candidate_with_confidence`
- `extraction/istd_recovery.py`: `candidate_quality_penalty`,
  `candidate_selection_quality_penalty`
- `extraction/peak_candidate_table.py`: `ScoredCandidate`, `ScoringContext`,
  `score_candidate`
- `extraction/result_assembly.py`: `candidate_quality_penalty`
- `extraction/scoring_factory.py`: `ScoringContext`, `compute_local_sn_cache`,
  `hard_quality_flags`
- tests import broader public symbols and should keep acting as import-smoke
  coverage for future movement.

Future implementation must preserve these imports through
`xic_extractor.peak_scoring` even if internal helpers move elsewhere.

## C4-A — Projection Boundary Extraction

**Type:** characterization-first refactor

C4-A starts with behavior protection, then allows only reason/audit projection
code to move.

C4-A must not run before C4-0 confirms that projection is still a legacy public
surface worth extracting. If C4-0 shows that projection should be emitted
directly from `EvidenceVector` / selected `PeakHypothesis`, C4-A should become a
compatibility wrapper migration instead of a standalone module split.

Allowed code movement:

- `_EVIDENCE_REASON_LABELS`
- `_CAP_REASON_LABELS`
- pure reason-formatting logic extracted from `build_evidence_reason(...)`,
  only if review-only / accepted status is provided by the caller
- `score_breakdown_fields(...)`

Recommended destination:

- `xic_extractor/peak_scoring_projection.py`

Dependency direction:

- `peak_scoring_projection.py` may import `EvidenceScore` and
  `ConfidenceValue` from `peak_scoring_evidence.py`.
- `peak_scoring_projection.py` must not import `xic_extractor.peak_scoring`.
- `_is_review_only_evidence(...)` stays in `peak_scoring.py` until C4-C because
  it owns decision policy, not projection.
- `build_evidence_reason(...)` remains public through
  `xic_extractor.peak_scoring`. In C4-A it may become a compatibility wrapper
  that computes review-only status in `peak_scoring.py` and delegates only pure
  formatting to `peak_scoring_projection.py`.

Compatibility requirement:

- `xic_extractor.peak_scoring` continues to expose
  `build_evidence_reason(...)` and `score_breakdown_fields(...)`.
- Existing imports from `xic_extractor.peak_scoring` remain valid.
- Add or preserve an import smoke test covering the current public imports:
  `Confidence`, `ScoredCandidate`, `ScoringContext`, `build_evidence_reason`,
  `build_reason`, `confidence_from_total`, `local_sn_severity`,
  `nl_support_severity`, `noise_shape_severity`, `peak_width_severity`,
  `rt_centrality_severity`, `rt_prior_severity`, `score_breakdown_fields`,
  `score_candidate`, `select_candidate_with_confidence`, `symmetry_severity`,
  `candidate_quality_penalty`, `candidate_selection_quality_penalty`,
  `compute_local_sn_cache`, and `hard_quality_flags`.

Forbidden in C4-A:

- moving or rewriting `_is_review_only_evidence(...)`
- moving or rewriting `_evidence_from_context(...)`
- moving or rewriting `score_candidate(...)`
- moving or rewriting `select_candidate_with_confidence(...)`
- changing scoring weights, support / concern labels, confidence caps, or
  review-only rules
- changing candidate selection, low-scan demotion, dominant strict-NL demotion,
  RT-prior tie-break, selected peak, confidence, reason text, or TSV values

## C4-A Characterization Gate

Before any projection code movement, tests must pin the current behavior for:

- public imports from `xic_extractor.peak_scoring`;
- scoring labels: `support_labels`, `concern_labels`, `cap_labels`
- decision result: `raw_score`, `confidence`, review-only decision
- projection: exact `reason`, full reason text for accepted, review-only,
  `VERY_LOW`, counted `no_ms2_cap`, not-counted `no_ms2_cap`, and cap-labelled
  cases, and exact `score_breakdown_fields(...)` label order
- dependency direction: projection helpers must not import
  `xic_extractor.peak_scoring`
- selection: `select_candidate_with_confidence(...)` tie-break,
  low-scan demotion, dominant strict-NL demotion, and RT-prior preference

Representative existing tests may satisfy part of this gate, but the phase note
must name them explicitly. Any missing behavior should be covered by focused
characterization tests before code movement.

Suggested focused verification:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_scoring.py tests/test_peak_scoring_selection.py tests/test_scoring_context.py tests/test_signal_processing_selection.py tests/test_peak_candidate_table.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

No RAW validation is required for C4-A if the diff is limited to projection
extraction and focused tests prove byte-identical reason / breakdown output. If
the implementation can affect selected peak, score, confidence, reason text, or
generated TSV values, stop and reclassify the phase as a behavior change.

## C4-B — Evidence Input Mapping

**Type:** later design / refactor slice

C4-B maps current scorer labels and facts onto the existing evidence-chain
surfaces without creating a new evidence product.

Required decisions before implementation:

- which scorer labels are canonical product evidence labels;
- which fields belong on `EvidenceVector`;
- which shared facts belong on `CommonEvidence`;
- when `EvidenceSignalSet` should be built from scorer labels versus direct
  common facts;
- how CWT evidence is represented without treating legacy CWT presence metrics
  as validated scale or ridge-quality metrics.

C4-B may touch evidence mapping and adapter code only after C4-A projection
behavior is characterized.

DONE WHEN:

- existing adapters between scorer output, `EvidenceVector`, `CommonEvidence`,
  and `EvidenceSignalSet` are inventoried;
- exactly one mapping target is selected;
- parity tests are named before implementation;
- the implementation proves no recomputation of scoring and no new evidence
  model;
- C3 is not `diagnostic_only`, or the C4-B note explicitly states that the work
  is bridge preparation only and does not claim handoff-spine advancement.

## C4-C — Decision Policy Boundary

**Type:** later design / refactor slice

C4-C separates decision policy from evidence extraction and projection. It owns
accepted/review-only decisions, confidence caps, candidate selection, demotion,
and tie-break behavior.

Required characterization before C4-C:

- confidence cap behavior for NL fail, no MS2, anchor mismatch, zero area,
  RT window, trace quality, and hard quality flags;
- low-scan and dominant strict-NL demotion behavior;
- RT-prior preference and strict selection RT behavior;
- MS2 trace tie-break behavior;
- selected candidate identity for representative competing candidates.

C4-C must not be framed as cleanup if it changes score, confidence, selected
candidate, reason text, or output schema.

DONE WHEN:

- the decision policy owner is named, either staying in `peak_scoring.py` behind
  clearer helpers or moving to a dedicated policy module;
- the candidate-selection parity oracle and focused tests are named before
  implementation;
- behavior-change stop rules cover score, confidence, review-only semantics,
  selected candidate, reason text, and output schema;
- C3 is not `diagnostic_only`, or the C4-C note explicitly states that no
  handoff-spine advancement is being claimed.

## Done When

C4 design is ready for implementation planning when:

- this design is linked from the old C4 split spec;
- C4-A / C4-B / C4-C are understood as separate slices;
- C4-A has an explicit characterization-first gate;
- C4-A keeps decision policy out of the projection module;
- C4-A has a dependency-direction rule and import-compatibility smoke;
- C4-B / C4-C each have an artifact, parity oracle, and exit rule before
  implementation;
- old package-split instructions remain historical and non-executable;
- no new evidence model is introduced.

## Stop Rules

Stop and write a separate behavior spec if C4 work requires:

- new scoring weights or labels;
- changed confidence thresholds or caps;
- changed review-only semantics;
- changed selected candidate or tie-break behavior;
- changed generated TSV/workbook schema or values;
- promoting, demoting, or deleting CWT evidence behavior.

## Open Questions

- C4-A implementation should decide whether `peak_scoring_projection.py` is a
  stable long-term module or an intermediate name. The public import path remains
  `xic_extractor.peak_scoring` either way.
- C4-B should decide the exact mapping between scorer labels and
  `CommonEvidence` / `EvidenceSignalSet` after C3 inventory confirms the
  consumer surfaces.
- C4-C should decide whether decision policy remains in `peak_scoring.py` behind
  clearer helper names or moves to a dedicated policy module.
