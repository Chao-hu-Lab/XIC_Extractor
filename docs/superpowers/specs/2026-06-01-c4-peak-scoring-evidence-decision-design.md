# C4 — Peak Scoring Evidence-Decision Design

**Date:** 2026-06-01
**Status:** Phase 4 design closeout v0.7 — evidence-chain successor direction
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

The 2026-06-02 design update narrows the long-term successor target:

- legacy `raw_score`, `confidence`, `cap_labels`, and reason text remain public
  compatibility projections while existing TSV/CSV/XLSX contracts expose them;
- future evidence-chain policy must not treat weighted score arithmetic or
  confidence caps as first-class product semantics;
- successor migration targets decision/explanation parity first: selected
  hypothesis, counted/review/not-counted/excluded/ambiguous decision class,
  typed evidence facts, conflicts, and human-readable reasons;
- any change to current selected peak, score, confidence, cap labels, reason
  text, schema, or workbook values remains a behavior change and is out of
  scope for cleanup-only C4 slices.

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
- `legacy_compatibility_projection` - the value remains in public outputs or
  imports, but it is no longer a future policy target.
- `successor_decision_semantics` - the invariant belongs to typed evidence,
  conflict reasons, decision classes, or model-selection explanation rather
  than scorer weights.

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
| `EvidenceScore` in `peak_scoring_evidence.py` | Weighted scoring result: raw score, confidence, support labels, concern labels, caps | Active scoring output today; future role is compatibility/debug projection while decision semantics move to typed evidence and model-selection explanation. |
| `EvidenceVector` in `peak_detection/hypotheses.py` | Per-hypothesis audit carrier populated from scorer output, candidate fields, and MS2 evidence | Successor audit/evidence carrier. Should absorb still-valid evidence invariants instead of duplicating scorer-specific tests. |
| `CommonEvidence` / `EvidenceSignalSet` in `evidence_semantics.py` | Cross targeted/discovery/alignment semantic layer and evidence-coherence classifier | Successor shared-evidence semantics. Should own cross-surface evidence meanings, not scoring-weight mechanics. |
| `ScoringContext` in `peak_scoring.py` | Extraction-time input bundle for the scorer | Legacy input adapter. Candidate for fusion into `TraceGroup` / `EvidenceVector` fact construction once selection policy migration is defined. |

## Successor Evidence-Chain Direction

C4's future target is not a cleaner weighted scorer. It is a role-aware,
typed-evidence decision layer over `PeakHypothesis` objects.

Decision classes:

| Class | Meaning | Intended output relationship |
|---|---|---|
| `accepted` | Evidence chain is coherent enough for the main quantitative result. | Included in primary quantitative outputs. |
| `review` | A plausible signal exists, but evidence is incomplete, conflicting, or needs operator review. | Preserved with review reason; not silently dropped. |
| `not_counted` | Evidence is retained, but the result should not contribute to formal quantitation/statistics. | Preserved with not-counted reason. |
| `excluded` | High-bar rejection: physically implausible, wrong identity, or strongly contradicted by multiple evidence sources. | Excluded with explicit reason. |
| `ambiguous` | Competing hypotheses cannot be safely resolved. | Preserved as ambiguity, not forced into a winner. |

Legacy `HIGH` / `MEDIUM` / `LOW` / `VERY_LOW` confidence can remain in existing
outputs as compatibility wording, but successor policy should not define itself
as raw-score buckets.

### Cap Label Migration

`cap_labels` are legacy compatibility projections. Successor policy should split
their meaning into typed conflict and routing reasons:

| Legacy cap label | Successor meaning | Default decision pressure |
|---|---|---|
| `no_ms2_cap` | Missing MS2 is `not_observed` unless acquisition opportunity and local sensitivity prove it should have been observable. | `review` or `not_counted`, not automatic exclusion. |
| `nl_fail_cap` | Product/NL conflict when the evidence was observable and candidate-aligned. | `evidence_conflict`; may become `excluded` only with strong opportunity and control evidence. |
| `rt_window_cap` | Targeted RT conflict. RT alone is contextual evidence, not identity veto. | `review`, `ambiguous`, or `not_counted` with corroborating conflicts. |
| `trace_quality_cap` | MS1 trace or boundary evidence is unreliable. | `review` or `not_counted`. |
| `hard_quality_flag_cap` | Local signal quality is too weak or structurally unreliable for counting. | `not_counted` or `review`, depending on supporting evidence. |
| `zero_area_cap` | No measurable or integratable signal remains after selection/integration. | `not_counted`; `excluded` only when a high-bar impossibility or wrong-identity rule is explicit. |
| `anchor_mismatch_cap` and related anchor conflicts | Anchor / paired-evidence conflict. | `evidence_conflict`; may become `not_counted` if unresolved. |

### Typed Evidence Ownership

| Evidence family | Successor owner | C4 rule |
|---|---|---|
| Local S/N | Typed trace evidence on `EvidenceVector` or a future trace evidence component. | Store baseline method, apex-above-baseline, residual MAD/noise source, local S/N ratio, and quality label. AsLS changes make numeric provenance mandatory. |
| Shape, width, and noise | One `trace morphology evidence` family. | Merge legacy symmetry, width, noise, continuity, edge recovery, shoulder/merge/split signals, and boundary plausibility into one morphology concept. |
| CWT | Morphology / boundary-hypothesis evidence source. | Do not describe CWT as merely a score bonus or as standalone identity proof. It can propose or corroborate boundaries, but must be interpreted with other evidence. |
| MS2/NL | Candidate-aligned identity evidence. | Missing evidence defaults to `not_observed`; negative evidence requires opportunity, sensitivity, and comparable controls. |
| RT | Targeted, role-aware contextual evidence. | Use mainly for ISTD-paired targeted workflows; do not generalize to untargeted family alignment here. |

### Role-Aware RT Rule

RT evidence in C4 is targeted-workflow evidence, not a universal peak identity
rule:

- ISTDs are expected to be stable in biological matrices because they are added
  externally and should act as the main transfer anchor.
- Clean standards and MixSTD observations describe instrument/library behavior
  and can support RT reference checks, but they are not biological-sample
  absence proof unless the biological samples were explicitly spiked or an
  approved contract says otherwise.
- Paired analyte/standard and ISTD RTs should be close, but stable-isotope
  labels, especially deuterium labels, can introduce reproducible
  compound/method-specific RT offsets. The expected offset direction and
  tolerance must be learned from current method evidence instead of hard-coded
  globally.
- RT alone may trigger `review`, `ambiguous`, or `not_counted`; it should not
  produce `excluded` without corroborating identity or morphology conflicts.

Reference notes: stable-isotope internal standards are used to compensate matrix
effects when they co-elute with the monitored compound, while deuterium labels
can introduce chromatographic isotope-effect RT shifts whose size and direction
depend on compound and method conditions. See Cerilliant's LC-MS/MS internal
standard note and recent LC-MS isotope-labeling literature for method-context
caveats:

- Cerilliant deuterium-labeled internal standard LC-MS/MS note:
  <https://www.cerilliant.com/news-and-events/poster-article?id=21>
- Triple labeling metabolomics / deuterium RT-shift discussion:
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC12240604/>
- Deuterium-label migration/retention comparison in MS workflows:
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC7540333/>

## Semantic-Survival Inventory

| Legacy responsibility | Current owner | Successor candidate | Current disposition | Required C4 decision |
|---|---|---|---|---|
| Candidate evidence facts: local S/N, shape, RT prior, MS2/NL, trace quality | `ScoringContext`, severity helpers, `score_candidate(...)` | `EvidenceVector`, `CommonEvidence`, `TraceGroup` fact extraction | `successor_owned` or `semantic_migration_candidate` depending on field | Map each fact to successor field/test before deleting scorer-specific tests. |
| Weighted score and confidence caps | `EvidenceScore`, `score_evidence(...)`, `_evidence_from_context(...)` | Compatibility projection plus future decision/explanation semantics | `active_policy` today; future `legacy_compatibility_projection` | Keep as production policy today. Future successor must not preserve score/cap mechanics as product truth; migrate toward decision class, conflict reason, not-counted reason, exclusion reason, and explanation parity. |
| Candidate selection and tie-breaks | `select_candidate_with_confidence(...)` | Future model selection over `PeakHypothesis` | `active_policy` today | Do not delete until `PeakHypothesis` model selection proves selected hypothesis, decision class, and explanation parity. Raw score parity is a compatibility check only, not the future oracle. |
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
| Evidence fact extraction from `ScoringContext`: local S/N, trace morphology, role-aware RT, MS2/NL, MS2 trace, CWT, quality flags | `extraction/scoring_factory.py`, `extraction/jobs.py`, `extraction/serial_backend.py`, `peak_detection/facade.py`; tests in `tests/test_scoring_context.py`, `tests/test_peak_scoring.py` | `EvidenceVector` and `CommonEvidence` already carry many fields after scoring, but local S/N and morphology lack typed successor fields | `semantic_migration_candidate`; do not delete while it is the scoring input adapter | Map each field to `EvidenceVector` / `CommonEvidence` or a future trace evidence component. Port field-level invariants first; then reduce `ScoringContext` tests to adapter coverage. |
| Weighted score, thresholds, confidence caps, and review-only caps | `score_candidate(...)`, `score_evidence(...)`, `peak_detection/facade.py`, `extraction/peak_candidate_table.py`; tests in `tests/test_peak_scoring_evidence.py` and score/cap sections of `tests/test_peak_scoring.py` | Successor should own decision class, conflict/review/not-counted/exclusion reasons, and explanation; legacy score/cap values remain projected while public outputs expose them | `active_policy` today; future `legacy_compatibility_projection` | Keep current tests as behavior oracle today. Exit to successor only after selected-candidate and decision/explanation parity exists; do not require future raw-score/cap parity except for compatibility outputs. |
| Candidate selection and tie-breaks | `find_peak_and_area(...)` calls `select_candidate_with_confidence(...)`; tests in `tests/test_peak_scoring_selection.py`, `tests/test_signal_processing_selection.py`, `tests/test_scoring_context.py` | `PeakHypothesis` records rank/selected/rejection, but does not select candidates independently | `active_policy` | Keep. Exit only when model selection over `PeakHypothesis` matches selected candidate or has an approved behavior-change spec, and emits decision class plus explanation parity across RT-distance, low-scan, dominant-area, paired-prior, MS2/NL, morphology, and quality fixtures. |
| Reason text and `score_breakdown_fields(...)` projection | Candidate table, CSV/XLSX/public output columns, tests in reason-text sections of `tests/test_peak_scoring.py`, `tests/test_peak_candidate_table.py`, `tests/test_csv_writers.py` | `EvidenceVector.reason`, support/concern/cap labels can become source of projection | `compatibility_adapter` candidate | Keep exact text/schema until public output migration is approved. Projection tests may move to successor output tests, but copy/schema parity remains required. |
| `EvidenceScore` arithmetic helper | `peak_scoring.py` and `tests/test_peak_scoring_evidence.py` | Compatibility/debug metric; not future policy target | `active_policy` support utility today | Keep as scorer utility while public outputs expose raw score. Future movement requires public import compatibility and a replacement decision/explanation oracle, not score arithmetic parity as product truth. |
| CWT and MS2 trace support labels | `score_candidate(...)`, `EvidenceVector`, candidate table output; tests around `cwt_same_apex_support`, MS2 trace tie-breaks, and "does not override RT distance" | Successor carries CWT/MS2 facts; CWT belongs to morphology / boundary-hypothesis evidence | `semantic_migration_candidate` with active guardrails | Preserve guardrail tests until CWT is represented as evidence source plus morphology/boundary facts. Avoid wording that CWT is "support only"; the invariant is that no single evidence source decides identity alone. |
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

This map separates three things that the old scorer currently mixes:

1. public compatibility projection;
2. typed evidence facts;
3. production decision policy.

The future successor target is decision/explanation parity, not score/cap
mechanics parity. Score and cap parity remain cleanup guards only while public
outputs expose those values.

| Scorer fact / policy | Current scorer source | Successor target | Current judgment | Required migration action |
|---|---|---|---|---|
| Selected candidate `confidence`, `raw_score`, support/concern/cap labels, reason | `EvidenceScore`, `ScoredCandidate`, `_candidate_score_summary(...)` | `EvidenceVector` and `CommonEvidence` projections for existing outputs; future decision class plus explanation | `successor_projection` plus `legacy_compatibility_projection` | Keep scorer as authority today. Future policy should emit decision class and reasons; raw score/cap values are compatibility fields. |
| Candidate MS1 apex, area, height, boundaries | `PeakCandidate.peak`, selected candidate summary | `CommonEvidence` MS1 fields and `IntegrationResult` | `successor_owned` for audit/projection | Move output-facing tests to hypothesis/evidence projection when convenient; no scorer policy migration needed. |
| MS2 present and strict NL match | `ScoringContext.ms2_present`, `nl_match`, `neutral_loss_required`; `nl_support_severity(...)` | `EvidenceVector` MS2/NL fields, `CommonEvidence`, and typed identity evidence | Evidence fact is `successor_owned`; old weight/cap is `active_policy` today | Port fact-projection tests to `tests/test_peak_hypotheses.py` / `tests/test_evidence_semantics.py`. Treat missing MS2 as `not_observed` unless opportunity/sensitivity/control evidence proves otherwise. |
| MS2 trace strength and sparse-apex fallback guard | `ScoringContext.ms2_trace_strength`, `ms2_alignment_source`, `trigger_scan_count`, `strict_nl_scan_count`; `_is_sparse_apex_fallback_ms2(...)` | MS2 trace metadata plus decision explanation | Partially successor-owned; sparse-apex guard remains active policy | Add successor projection tests for trace metadata. Keep scorer tests for sparse-apex, strong/moderate/weak effects, and selection guardrails until model selection migrates. |
| Targeted RT / paired ISTD evidence | `ScoringContext.rt_prior`, `rt_prior_sigma`, `prefer_rt_prior_tiebreak`; `rt_prior_severity(...)`; `rt_centrality_severity(...)`; `rt_window_cap` | Role-aware targeted RT evidence with ISTD transfer context, method-specific offset, and conflict reason | `semantic_migration_candidate`; active policy today | Do not generalize to untargeted family alignment. Add explicit targeted RT fields before retiring scorer RT tests. RT alone does not exclude. |
| Local S/N | `local_sn_severity(...)`, `compute_local_sn_cache(...)` over AsLS baseline and residual MAD | Typed trace evidence with baseline provenance | `semantic_migration_candidate` with missing typed field | Add local S/N fact fields: baseline method, apex-above-baseline, residual MAD/noise source, ratio, and quality label. Keep scorer coverage until successor facts exist. |
| Shape, width, and noise quality | `half_width_ratio`, `fwhm_ratio`, `symmetry_severity(...)`, `peak_width_severity(...)`, `noise_shape_severity(...)` | One `trace morphology evidence` family | `semantic_migration_candidate` with missing typed field | Merge legacy shape/width/noise into morphology evidence before deleting scorer-specific tests. |
| Trace quality flags and ADAP-like soft flags | `trace_quality_severities(...)`, `candidate_quality_penalty(...)`, `candidate_selection_quality_penalty(...)`, `hard_quality_flags(...)` | Raw quality flag projection plus morphology/quality conflict reasons | Raw projection exists; penalty/cap policy remains active | Keep scorer policy tests for selection penalty, hard flag routing, and ADAP-equivalent suppression. |
| CWT same-apex support | `_has_same_apex_cwt_support(...)`, `_has_cwt_chemical_support(...)`, legacy CWT presence metrics | Morphology / boundary-hypothesis evidence source | `semantic_migration_candidate` | Preserve guardrail tests until CWT is represented as an evidence source with boundary/morphology semantics. Avoid "support only" wording; no single evidence source decides identity alone. |
| Weighted score arithmetic, thresholds, and caps | `score_evidence(...)`, confidence thresholds, `apply_confidence_caps(...)`, `_is_review_only_evidence(...)` | Legacy compatibility/debug metric plus typed decision routing reasons | `active_policy` today; not future policy target | Keep current behavior. Exit requires a successor decision/explanation policy or approved behavior-change spec, not raw-score/cap parity as product truth. |
| Candidate selection and tie-breaks | `select_candidate_with_confidence(...)`, effective score, RT distance, low-scan/dominant-area demotion, MS2 trace tie-break, quality penalties | Model selection over `PeakHypothesis` | `active_policy` | Keep. Future model selection must prove selected hypothesis, decision class, and explanation parity or explicitly document behavior changes. |
| Reason and score breakdown output | `build_evidence_reason(...)`, `score_breakdown_fields(...)` | Compatibility projection over existing public output fields | `compatibility_adapter` candidate | May move to a projection module only with exact public text/schema parity. Do not couple projection extraction to policy migration. |

### C4-1 Execution Closeout

Phase 1 added a successor-projection parity test without moving scorer policy:

- `tests/test_peak_hypotheses.py::test_build_peak_hypotheses_projects_scorer_facts_to_successor_evidence`
  locks scorer output labels/reason, MS1 geometry, MS2/NL facts, MS2 trace
  metadata, quality flags, RT prior value, CWT audit-presence fields, and
  `CommonEvidence` projection onto the successor evidence spine.
- No scorer policy, confidence caps, selected-candidate logic, score arithmetic,
  local S/N, trace morphology, RT-window behavior, CSV schema, or workbook output
  moved in this slice.
- No scorer tests were deleted. Active policy tests remain the authority for
  scorer-owned behavior.

C4-1 proves projection, not policy ownership. It does not authorize scorer
deletion or future score/cap parity as the successor goal.

## Future Slice Contract

| Slice | Owner | Preserved public API | Parity surface before implementation | Exit rule |
|---|---|---|---|---|
| C4-0 semantic-survival audit | C4 design/spec owner | No code movement; existing scorer and hypothesis imports remain valid. | CodeGraph consumer scan, scorer-to-successor invariant map, and test-retirement table for `tests/test_peak_scoring*.py`, `tests/test_peak_hypotheses.py`, candidate-table tests, and selection tests. | Stop if any proposed deletion lacks successor invariant coverage or public compatibility plan. |
| C4-A projection boundary | `peak_scoring.py` remains the public owner; optional internal owner is `peak_scoring_projection.py` for pure reason/breakdown formatting only. | `from xic_extractor.peak_scoring import build_evidence_reason, score_breakdown_fields` remains valid, along with current scorer imports. | Exact `reason` strings, `score_breakdown_fields(...)` ordering, support/concern/cap label projection, candidate/boundary TSV scoring columns, CSV/XLSX confidence display. | Stop if projection extraction needs `_is_review_only_evidence(...)`, `_evidence_from_context(...)`, `score_candidate(...)`, candidate selection, or any changed score/confidence/reason text. |
| C4-B typed evidence mapping | Existing `evidence_semantics.py`, `peak_detection/hypotheses.py`, and future trace-evidence components own typed facts; `peak_scoring_evidence.py` remains legacy metric support. | Existing `EvidenceScore`, `EvidenceVector`, `CommonEvidence`, and `EvidenceSignalSet` import paths remain valid. Public score/cap outputs remain compatibility projections. | `tests/test_evidence_semantics.py`, `tests/test_peak_hypotheses.py`, candidate-table projection tests, `tests/test_csv_writers.py`, `tests/test_csv_to_excel.py`, `tests/test_excel_pipeline.py`, `tests/test_peak_candidate_score_calibration_report.py`, plus named fixtures for local S/N provenance, morphology, role-aware RT, MS2/NL, and CWT evidence-source mapping. | Stop if mapping recomputes scoring, creates a fourth evidence model, treats CWT audit-presence as validated quality, or changes public output values. |
| C4-C decision semantics contract | Future policy targets decision class, evidence conflicts, review/not-counted/exclusion reasons, and model-selection explanation. `peak_scoring.py` owns active policy until that contract exists. | `score_candidate(...)`, `select_candidate_with_confidence(...)`, severity helpers, `Confidence`, `ScoredCandidate`, and `ScoringContext` imports remain valid. | Decision/explanation oracle: selected hypothesis, decision class, counted/review/not-counted/excluded/ambiguous routing, evidence facts/conflicts/reasons, plus compatibility output parity through candidate TSV, CSV, XLSX, score-breakdown CSV/sheet, and diagnostic consumers while old fields remain public. | Stop and write a behavior spec if current score, confidence, review-only status, selected candidate, tie-breaks, reason text, or output schema changes. |
| C4-D model selection migration | Future `PeakHypothesis` model-selection layer, if approved. | Current scorer public API remains as compatibility facade until replacement is product-ready. | `tests/test_peak_scoring_selection.py`, `tests/test_signal_processing_selection.py`, targeted RT fixtures, morphology fixtures, MS2/NL fixtures, local S/N fixtures, candidate TSV diagnostics, CSV/XLSX score projection, and public-output projection tests. | Stop unless selected-hypothesis parity is proven or behavior changes are explicitly approved. Raw-score parity is not a future policy requirement. |

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

## Legacy Field Versioning Rule

While legacy scorer fields remain public, cleanup slices may not rename, remove,
deprecate, recompute, or replace these fields without an approved
behavior/output-schema spec:

- candidate TSV fields such as `confidence`, `raw_score`, `support_labels`,
  `concern_labels`, `cap_labels`, `reason`, selected/rank/rejection columns, and
  downstream diagnostic consumers of those fields;
- `xic_score_breakdown.csv` headers, order, and values;
- XLSX `XIC Results` confidence/reason display and `Score Breakdown` sheet
  headers, order, and values;
- CSV long/wide result confidence/reason/projection values;
- public imports from `xic_extractor.peak_scoring`.

A future schema migration must either preserve old fields through dual-write /
compatibility output or explicitly version/remove them with regression tests and
an approved behavior spec. Decision-class fields can be added only as additive
surface unless a separate output-schema migration says otherwise.

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

## C4-B — Typed Evidence Mapping

**Type:** later design / refactor slice

C4-B maps current scorer labels and facts onto evidence-chain surfaces without
creating a fourth evidence model or preserving scorer weights as product truth.

Required decisions before implementation:

- which legacy labels are compatibility projections only;
- which facts belong on `EvidenceVector`, `CommonEvidence`, or a future trace
  evidence component;
- how local S/N stores AsLS baseline provenance and numeric evidence;
- how shape, width, noise, continuity, edge recovery, and boundary plausibility
  become one trace morphology evidence family;
- how targeted RT evidence stays role-aware and ISTD-paired;
- how CWT is represented as a morphology / boundary-hypothesis evidence source
  without treating legacy presence metrics as validated CWT quality.

C4-B may touch evidence mapping and adapter code only after C4-A projection
behavior is characterized.

DONE WHEN:

- existing adapters between scorer output, `EvidenceVector`, `CommonEvidence`,
  and `EvidenceSignalSet` are inventoried;
- each typed evidence family has one owner;
- compatibility projection fields are explicitly separated from future policy
  fields;
- parity tests are named before implementation;
- any slice touching legacy projection fields names candidate TSV, CSV writer,
  CSV-to-XLSX, Excel pipeline, score-breakdown, and diagnostic-consumer tests
  before code movement;
- the implementation proves no recomputation of scoring, no new evidence model,
  and no output value/schema changes;
- C3 is not `diagnostic_only`, or the C4-B note explicitly states that the work
  is bridge preparation only and does not claim handoff-spine advancement.

## C4-C — Decision Semantics Boundary

**Type:** later design / refactor slice

C4-C separates decision semantics from evidence extraction and compatibility
projection. It defines the future policy vocabulary before any implementation:

- decision classes: `accepted`, `review`, `not_counted`, `excluded`,
  `ambiguous`;
- conflict/review/not-counted/exclusion reasons replacing caps as future policy;
- decision/explanation parity as the migration oracle;
- legacy `raw_score`, `confidence`, and `cap_labels` as compatibility fields
  while public outputs expose them.

Required characterization before C4-C:

- current cap behavior for NL fail, no MS2, anchor mismatch, zero area,
  RT window, trace quality, and hard quality flags, mapped to future reason
  categories;
- low-scan and dominant strict-NL demotion behavior;
- RT-prior preference and strict selection RT behavior;
- MS2 trace tie-break behavior;
- selected candidate identity for representative competing candidates.

C4-C must not be framed as cleanup if it changes score, confidence, selected
candidate, reason text, or output schema.

DONE WHEN:

- the decision semantics owner is named, either staying in `peak_scoring.py`
  behind clearer helpers or moving to a dedicated policy module;
- the selected-hypothesis and decision/explanation parity oracle is named before
  implementation;
- behavior-change stop rules cover current score, confidence, review-only
  semantics, selected candidate, reason text, and output schema;
- C3 is not `diagnostic_only`, or the C4-C note explicitly states that no
  handoff-spine advancement is being claimed.

## C4-D — PeakHypothesis Model Selection Migration

**Type:** future behavior or characterization-backed migration slice

C4-D is the first slice that may replace scorer-driven candidate selection with
model selection over `PeakHypothesis`. It is not cleanup unless it proves current
selected-candidate and public-output parity.

Required before implementation:

- typed evidence fields from C4-B exist or a reviewed temporary bridge is named;
- decision semantics from C4-C exist;
- fixtures cover selected candidate identity, decision class, explanation,
  local S/N, morphology, role-aware RT, MS2/NL, CWT, low-scan and dominant-area
  cases, and quality penalties;
- legacy projection parity includes candidate TSV diagnostics, CSV writers,
  CSV-to-XLSX, Excel pipeline, and score-breakdown outputs while those fields
  remain public;
- public outputs either remain byte/value compatible or an approved behavior
  spec versions the schema/copy.

DONE WHEN:

- current `select_candidate_with_confidence(...)` remains the oracle until a
  successor selector matches selected hypothesis and decision/explanation parity;
- any intentional divergence is documented as behavior change, not cleanup;
- raw-score parity is used only for compatibility fields while those fields
  remain public.

## Done When

C4 design is ready for implementation planning when:

- this design is linked from the old C4 split spec;
- C4-A / C4-B / C4-C are understood as separate slices;
- C4-D is explicitly future work and not part of cleanup unless parity-backed;
- C4-A has an explicit characterization-first gate;
- C4-A keeps decision policy out of the projection module;
- C4-A has a dependency-direction rule and import-compatibility smoke;
- C4-B / C4-C each have an artifact, parity oracle, and exit rule before
  implementation;
- weighted score and cap mechanics are identified as current compatibility /
  active-policy surfaces, not future successor policy goals;
- typed evidence ownership is named for local S/N, trace morphology, CWT,
  role-aware targeted RT, and MS2/NL;
- old package-split instructions remain historical and non-executable;
- no new evidence model is introduced.

## Stop Rules

Stop and write a separate behavior spec if C4 work requires:

- new scoring weights or labels;
- changed confidence thresholds or caps;
- changed review-only semantics;
- changed selected candidate or tie-break behavior;
- changed candidate TSV, CSV, score-breakdown CSV, XLSX sheet/header/value,
  workbook schema/value, or downstream diagnostic-consumer schema/value;
- promoting, demoting, or deleting CWT evidence behavior;
- changing `raw_score`, `confidence`, `cap_labels`, or reason text in public
  projections;
- renaming, removing, deprecating, recomputing, or replacing legacy projection
  fields without a versioned output-schema/deprecation plan and regression
  tests;
- treating clean standards or MixSTD observations as biological-sample absence
  proof without an explicit experiment/design contract.

## Open Questions

- C4-A implementation should decide whether `peak_scoring_projection.py` is a
  stable long-term module or an intermediate name. The public import path remains
  `xic_extractor.peak_scoring` either way.
- C4-B should decide whether typed local S/N and morphology fields live directly
  on `EvidenceVector` or in a nested trace-evidence component.
- C4-C should decide whether decision semantics remain in `peak_scoring.py`
  behind clearer helper names or move to a dedicated policy module.
- C4-D should decide whether model selection can be cleanup-parity migration or
  must be written as a behavior-change spec.
