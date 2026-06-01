# C4 — Peak Scoring Evidence-Decision Design

**Date:** 2026-06-01
**Status:** Phase 4 design closeout v0.2 — docs-only implementation contract
**Readiness label:** `diagnostic_only`
**Supersedes for implementation:** [C4 peak_scoring split spec](2026-05-24-peak-pipeline-cleanup-peak-scoring-split-spec.md)
**Depends on:** [C3 hypothesis model unification spec](2026-05-24-peak-pipeline-cleanup-hypothesis-model-unification-spec.md)
**One-goal contract:** [Peak pipeline cleanup one-goal phase contract](2026-06-01-peak-pipeline-cleanup-one-goal-phase-contract-spec.md)

## Verdict

C4 is not a package split. The old plan to convert
`xic_extractor/peak_scoring.py` into a `xic_extractor/peak_scoring/` package is
historical only.

The current problem is responsibility overlap between scoring evidence,
hypothesis audit evidence, and cross-surface evidence semantics. C4 must first
protect current behavior, then separate projection, evidence mapping, and
decision policy in that order.

Phase 4 itself is docs-only. It authorizes no scorer movement and no confidence,
reason, score, selection, matrix, TSV, or workbook behavior change.

## Current Evidence Surfaces

| Surface | Current role | C4 contract |
|---|---|---|
| `EvidenceScore` in `peak_scoring_evidence.py` | Weighted scoring result: raw score, confidence, support labels, concern labels, caps | Owns weighted scoring output. Does not own hypothesis audit fields or cross-surface coherence. |
| `EvidenceVector` in `peak_detection/hypotheses.py` | Per-hypothesis audit carrier populated from scorer output, candidate fields, and MS2 evidence | May preserve scorer labels and audit facts. Must not recompute scoring. |
| `CommonEvidence` / `EvidenceSignalSet` in `evidence_semantics.py` | Cross targeted/discovery/alignment semantic layer and evidence-coherence classifier | May consume scorer labels and common facts. Must not own scoring weights or candidate selection. |
| `ScoringContext` in `peak_scoring.py` | Extraction-time input bundle for the scorer | Provides raw facts to scoring. It is not the evidence-chain source of truth. |

Current labels such as `strict_nl_ok`, `ms2_trace_strong`, `rt_prior_close`,
`local_sn_strong`, `shape_clean`, `trace_clean`, and
`cwt_same_apex_support` are already product evidence. C4 must not duplicate
them into a fourth evidence model.

## Future Slice Contract

| Slice | Owner | Preserved public API | Parity surface before implementation | Exit rule |
|---|---|---|---|---|
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
