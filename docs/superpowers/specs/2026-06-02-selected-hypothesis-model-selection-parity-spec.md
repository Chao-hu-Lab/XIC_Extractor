# Selected-Hypothesis Model-Selection Parity Spec

**Date:** 2026-06-02
**Branch:** `codex/cleanup-retirement-foundation`
**Status:** Draft after brainstorming approval
**Behavior label:** parity-first model-selection migration with controlled
expected-diff lane
**Parent addendum:** [Selected-Hypothesis Evidence Decision Public Behavior Addendum](2026-06-02-selected-hypothesis-evidence-decision-public-behavior-addendum.md)
**Primary design:** [Peak Scoring Evidence-Decision Design](retired-provenance:af29f907f881)

Historical roadmap note: this work follows the old peak-scoring cleanup thread,
but the implementation, tests, output metadata, and human-facing wording should
use `selected-hypothesis model selection` rather than roadmap shorthand.

## Verdict

The previous phase made `PeakHypothesisSelectionDecision` a production
projection surface. It did not retire `score_candidate(...)`,
`select_candidate_with_confidence(...)`, weighted raw scores, confidence caps, or
legacy reason text.

This spec defines the gate for replacing scorer-driven candidate selection with
model selection over `PeakHypothesis`.

The default migration path is parity:

```text
legacy scored candidates
  -> select_candidate_with_confidence(...)
  -> current selected candidate oracle

PeakHypothesis candidates
  -> successor model-selection decision
  -> same selected candidate and public projection
```

The spec also allows a controlled `expected_diff` lane. A successor selector may
intentionally diverge from the legacy selector only when the diff is named,
fixture-backed, evidence-backed, public-output-aware, and reviewed before it
enters product behavior.

Raw-score parity is not the future product oracle. Raw score, confidence caps,
and score-breakdown fields are compatibility projections while those values
remain public.

## Product Problem

The current production selector still mixes several ideas in one legacy surface:

- evidence fact extraction;
- score arithmetic;
- confidence caps;
- selected-candidate tie-breaks;
- review-only wording;
- compatibility projection for CSV, XLSX, candidate tables, and score-breakdown
  diagnostics.

That coupling makes scorer retirement risky. A simple rewrite could silently
change selected peaks, final matrix values, or reason text. A pure parity
rewrite would be safer, but it would also preserve legacy behavior that may be
contradicted by newer evidence-chain semantics.

The migration therefore needs two explicit lanes:

- `parity`: successor selection matches the legacy oracle exactly for candidate
  identity and public projections;
- `expected_diff`: successor selection intentionally changes a known row or
  fixture because the evidence-chain explanation is stronger than the old
  score/cap heuristic.

Any unclassified mismatch is a blocker, not an accepted diff.

## Scope

In scope:

- model selection over existing `PeakHypothesis` candidates;
- selected-candidate identity parity;
- decision-class and explanation parity;
- public `confidence` / `reason` projection parity;
- compatibility output parity for score-breakdown, candidate tables, CSV, XLSX,
  and workbooks while those fields remain public;
- controlled `expected_diff` cases with explicit evidence and review;
- retirement-readiness rules for `select_candidate_with_confidence(...)`.

Out of scope:

- adding ML or probabilistic model fitting;
- changing resolver modes or baseline integration behavior;
- changing writer schemas without a schema addendum;
- deleting `xic_extractor.peak_scoring` public imports;
- requiring future model selection to reproduce raw-score arithmetic;
- using CWT, RT, local S/N, shape, MS2/NL, or any single evidence source as
  standalone authority.

## Current Oracle

The current active oracle is:

- `score_candidate(...)` for legacy scored facts and public projection values;
- `select_candidate_with_confidence(...)` for selected-candidate policy;
- `PeakHypothesis.audit.selected` for the current selected candidate after
  legacy selection;
- `PeakHypothesisSelectionDecision` for current production confidence/reason
  projection.

The successor must treat this oracle as the current behavior baseline, not as
the future scientific truth.

## Successor Owner

The successor selection owner should live in the peak-domain layer, not in
writers, GUI code, workbook code, or `extractor.py`.

Preferred future placement:

- `xic_extractor/peak_detection/model_selection.py`

Allowed responsibilities:

- receive a non-empty tuple of `PeakHypothesis` candidates;
- classify each hypothesis with model-selection reasons;
- select exactly one hypothesis when a product peak should be selected;
- emit a selected-hypothesis decision compatible with
  `PeakHypothesisSelectionDecision`;
- emit parity or expected-diff audit facts.

Forbidden responsibilities:

- re-scan RAW files;
- recompute writer schemas;
- mutate candidate objects in place;
- depend on output writers, GUI, CLI wrappers, or workbook rendering;
- preserve raw-score arithmetic as product truth.

## Required Decision Output

The successor model-selection contract should be concrete enough to test before
any product switch.

Preferred module:

- `xic_extractor/peak_detection/model_selection.py`

Preferred dataclasses:

- `PeakModelSelectionResult`
- `ExpectedDiffApprovalRecord`

The implementation plan may adjust names only if it preserves the same fields
and status semantics. The successor model-selection result must expose these
facts:

| Field | Required meaning |
|---|---|
| `selected_candidate_id` | Successor-selected `PeakHypothesis.hypothesis_id`. |
| `legacy_selected_candidate_id` | Candidate selected by the current legacy oracle. |
| `trace_group_id` | Selected hypothesis trace group. |
| `decision_class` | `accepted`, `review`, `not_counted`, `excluded`, or `ambiguous`. |
| `selection_status` | `parity`, `expected_diff`, `blocked_diff`, or `inconclusive`. |
| `selection_reasons` | Evidence-chain reasons supporting the successor choice. |
| `legacy_reasons` | Compatibility reasons from the current oracle when available. |
| `diff_reasons` | Required when `selection_status=expected_diff` or `blocked_diff`. |
| `public_projection` | Projected `confidence`, `reason`, and compatibility labels. |
| `evidence_sources` | Coarse sources such as MS1 trace, MS2/NL, role-aware RT, CWT context, morphology, local S/N, and compatibility projection. |
| `compatibility_oracle` | `legacy_peak_scoring_current_oracle` while legacy selector remains available. |
| `policy_source` | A semantic policy name such as `selected_hypothesis_model_selection_v1`. |
| `product_switch_allowed` | `True` only for parity rows or approved expected diffs with enough validation. |

`blocked_diff` means the successor and legacy selector disagree, but the
implementation cannot yet justify or approve the divergence. `inconclusive`
means the comparison lacks enough evidence to classify.

## Machine-Readable Gate

`selection_status` is not only human wording. It must drive a machine-readable
gate:

| Status | Product switch rule |
|---|---|
| `parity` | May switch only if selected candidate and public projection parity tests pass. |
| `expected_diff` | May switch only if an `ExpectedDiffApprovalRecord` exists and the validation tier is sufficient for the touched output. |
| `blocked_diff` | Must block product switch. |
| `inconclusive` | Must block product switch. |

Required `ExpectedDiffApprovalRecord` fields:

| Field | Required meaning |
|---|---|
| `stable_row_id` | Stable fixture id or real row id. |
| `sample_name` | Sample identifier when available. |
| `target_label` | Target or analyte label when available. |
| `legacy_selected_candidate_id` | Candidate chosen by legacy selector. |
| `successor_selected_candidate_id` | Candidate chosen by successor selector. |
| `public_outputs_touched` | Tuple naming touched outputs: selected RT, area, boundary, confidence, reason, candidate TSV, CSV, XLSX, workbook, or final matrix value. |
| `matrix_value_impact` | `none`, `area_value_changed`, `presence_changed`, or `not_assessed`. |
| `evidence_sources` | Evidence sources supporting the diff. |
| `evidence_summary` | Short machine-readable reason string. |
| `validation_tier` | `synthetic_fixture`, `targeted_benchmark`, `8raw`, `manual_eic_ms2_review`, or `not_validated`. |
| `reviewer_role` | Reviewer angle that approved the diff. |
| `reviewer_verdict` | `approved`, `blocked`, or `inconclusive`. |
| `final_label` | `expected_diff`, `blocked_diff`, or `inconclusive`. |

Durable registry ingestion:

- `settings.csv` may provide
  `model_selection_expected_diff_approval_registry`; `scripts/run_extraction.py`
  may override it with `--model-selection-expected-diff-approvals`.
- The registry is a TSV projection of `ExpectedDiffApprovalRecord`, keyed by
  `stable_row_id`.
- Durable registry rows must be approved `expected_diff` rows. Missing files,
  blocked, inconclusive, unvalidated, duplicate, or incomplete rows must be
  rejected at load time.
- Matrix-affecting durable rows must not use `synthetic_fixture`; they need
  `targeted_benchmark`, `8raw`, or `manual_eic_ms2_review`.
- Registry ingestion is not sufficient for product switch by itself. Loaded rows
  still pass through the runtime approval matcher and model-selection gate, so
  sample, target, legacy candidate id, successor candidate id, stable row id,
  public-output impact, and matrix impact are rechecked against the current
  run.

Tests must prove:

- `blocked_diff` and `inconclusive` always set `product_switch_allowed=False`;
- `expected_diff` without an approval record sets
  `product_switch_allowed=False`;
- matrix-affecting `expected_diff` with only `synthetic_fixture` validation sets
  `product_switch_allowed=False`;
- approved non-matrix `expected_diff` may be switch-eligible only when public
  projection impact is recorded.

## Per-Candidate Evidence Policy

Current production handoff has an important limitation: selected-candidate MS2/NL
evidence may be materialized for the legacy-selected candidate before the
successor selector runs. A successor selector must not treat missing MS2/NL
evidence for non-selected candidates as negative evidence unless acquisition
opportunity and candidate-specific evidence were actually evaluated.

There are two allowed implementation lanes:

| Lane | Allowed use |
|---|---|
| `complete_candidate_evidence` | Materialize candidate-aligned MS2/NL/trace evidence for every hypothesis in the model-selection candidate set before successor selection. MS2/NL can participate in parity or expected-diff decisions. |
| `limited_evidence_shadow` | Compare only the evidence that is complete for all candidates. Candidate-specific MS2/NL for non-selected candidates must be marked `not_observed_for_comparison` or equivalent and cannot justify an MS2/NL-driven expected diff. |

If the implementation cannot provide complete per-candidate MS2/NL evidence, any
MS2/NL-driven mismatch must be `inconclusive`, not `expected_diff`.

This policy does not require writers, GUI code, or workbook code to materialize
evidence. Handoff/runtime code may expand the candidate evidence map, but the
model-selection owner only consumes `PeakHypothesis` and evidence facts.

## Parity Lane

`selection_status=parity` requires:

- same selected candidate id;
- same selected RT, area, boundary, and integration values;
- same public `confidence`;
- same public `reason`;
- same score-breakdown projection while exposed;
- same selected candidate marker in candidate TSV / CSV / XLSX / workbook
  outputs;
- same counted vs not-counted routing while that routing remains public;
- no output schema changes unless a separate schema addendum is approved first.

Exact raw score, positive points, negative points, and cap internals are
compatibility checks only. They are required to stay stable while output fields
expose them, but they are not the successor selector's policy objective.

## Expected-Diff Lane

`selection_status=expected_diff` is allowed only when all of these are true:

1. The legacy and successor selected candidates differ, or public projection
   values differ, for a named fixture or row.
2. The diff is explained by evidence-chain semantics rather than by a hidden
   score tweak.
3. The diff names which public outputs change: selected RT, area, confidence,
   reason, candidate table selected marker, CSV, XLSX, workbook, or matrix value.
4. The diff includes a local fixture or stable row identifier.
5. The diff has an `ExpectedDiffApprovalRecord` with reviewer approval before
   product switching.
6. The closeout records the diff as product behavior, not cleanup.

Expected-diff candidates include:

- legacy score/cap behavior conflicts with multi-evidence support;
- low-scan or dominant-area heuristics are replaced by clearer evidence-chain
  selection reasons;
- role-aware ISTD/STD RT evidence supports a different candidate than legacy RT
  distance alone;
- targeted validation exposes a shared evidence-rule problem that should also
  change untargeted model selection, such as wrong-peak selection, legacy score
  authority, morphology-as-veto behavior, or candidate-aligned product/NL
  attribution;
- MS2 trace, neutral-loss evidence, local S/N, morphology, and CWT context agree
  against the legacy selection;
- AsLS baseline changes local S/N enough that the legacy score is no longer the
  best oracle.

Expected-diff must not be used for:

- unexplained mismatches;
- broad threshold tuning without row-level evidence;
- copying targeted labels, targeted pass/fail states, or sample-specific fixes
  into untargeted matrix identity;
- CWT-only promotion;
- MS2/NL-driven promotion when non-selected candidates lack complete candidate
  evidence;
- RT-only exclusion;
- changing writer schemas without versioning;
- hiding behavior changes inside a cleanup commit.

## Blocked Diff And Inconclusive Handling

A mismatch is `blocked_diff` when the successor disagrees with legacy behavior
but the team cannot yet justify the successor as better product behavior.

A comparison is `inconclusive` when the candidate set, evidence facts, or output
projection is incomplete.

Both states stop product switching. They may create diagnostics, notes, or
fixtures, but they must not retire the legacy selector.

## Required Fixture Families

The parity and expected-diff gates must cover representative examples for:

- clean single-peak selection;
- confidence-rank selection;
- role-aware RT prior and paired ISTD preference;
- strict `selection_rt` behavior;
- final intensity tie-break;
- local S/N, including AsLS baseline provenance;
- peak shape, width, and morphology concerns;
- MS2 present / strict NL OK;
- no-MS2 and NL-fail review/not-counted behavior;
- MS2 trace strong / moderate / weak tie-break behavior;
- CWT same-apex context as support, not standalone authority;
- low-scan demotion;
- dominant strict-NL alternative behavior;
- candidate quality flags and ADAP-like soft penalties;
- stale final peak-result confidence fallback;
- no-candidate / no-peak fallback.

Existing characterization tests should remain the starting oracle:

- `tests/test_peak_scoring_selection.py`
- `tests/test_signal_processing_selection.py`
- `tests/test_scoring_context.py`
- `tests/test_peak_scoring.py`
- `tests/test_peak_scoring_evidence.py`
- `tests/test_peak_hypotheses.py`
- `tests/test_evidence_semantics.py`
- `tests/test_peak_selection_decision.py`
- `tests/test_result_assembly.py`
- candidate table, CSV, XLSX, and workbook contract tests.

## Implementation Phases

### Phase 1 -- Characterization Map

Create a selector-invariant map before writing the successor selector.

DONE WHEN:

- each legacy selector fixture is mapped to a product invariant;
- invariants are classified as `future_policy`, `compatibility_projection`, or
  `retirement_candidate`;
- no test deletion is proposed unless a successor invariant replaces it.

### Phase 2 -- Shadow Successor Selector

Add successor model selection over `PeakHypothesis` in shadow mode.

DONE WHEN:

- normal product outputs still use the legacy selector;
- `PeakModelSelectionResult` or an equivalent concrete result type exists;
- successor output records `parity`, `expected_diff`, `blocked_diff`, or
  `inconclusive`;
- per-candidate evidence policy is declared as `complete_candidate_evidence` or
  `limited_evidence_shadow`;
- focused tests prove selected-candidate and public-projection parity for the
  required fixture families;
- focused tests prove `blocked_diff` and `inconclusive` cannot product-switch.

### Phase 3 -- Expected-Diff Review

Classify all non-parity rows.

DONE WHEN:

- every mismatch is either approved `expected_diff`, `blocked_diff`, or
  `inconclusive`;
- approved diffs include fixture or row identifiers, public output impact, and
  evidence-chain rationale;
- approved diffs have `ExpectedDiffApprovalRecord` entries;
- blocked and inconclusive rows prevent product switching.

### Phase 4 -- Product Switch Candidate

Switch product selection only after Phase 2 parity and Phase 3 expected-diff
review pass.

DONE WHEN:

- successor selector owns selected-candidate choice;
- legacy selector remains available only as compatibility facade, diagnostic
  oracle, or import-preserving adapter;
- public outputs either remain parity-compatible or record approved
  expected-diff behavior;
- writer schemas remain unchanged unless a schema addendum approves versioning.

## Verification

Focused verification for implementation planning should include:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_scoring.py tests/test_peak_scoring_selection.py tests/test_peak_scoring_evidence.py tests/test_scoring_context.py tests/test_peak_hypotheses.py tests/test_evidence_semantics.py tests/test_peak_selection_decision.py tests/test_result_assembly.py tests/test_target_extraction.py tests/test_peak_candidate_table.py tests/test_peak_candidate_score_calibration_report.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py tests/test_excel_sheets_contract.py tests/test_signal_processing_selection.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
git diff --check
```

If product switching approves expected diffs that affect final matrix values,
focused unit tests are not enough. The approval record must include at least one
of:

- targeted benchmark evidence;
- 8-RAW validation evidence;
- manual EIC/MS2 review evidence.

Synthetic-only expected diffs may prove code behavior, but they are
`shadow_ready` at most and must not be product-switched or called
`production_ready` for real matrix behavior.

## Stop Rules

Stop and re-review if implementation requires:

- changing selected candidate without `expected_diff` classification;
- changing public `confidence`, `reason`, or selected candidate markers without
  public-output impact records;
- deleting scorer tests before successor invariants exist;
- changing writer schema without schema addendum;
- treating raw score as future product truth;
- treating any single evidence source as final authority;
- using missing non-selected candidate MS2/NL as negative evidence;
- adding broad new model-selection architecture outside `PeakHypothesis`;
- changing baseline, resolver, or integration behavior in the same phase;
- hiding product behavior changes inside compatibility cleanup.

## Done When

This spec is ready for an implementation plan when:

- legacy selector is named as current oracle, not future truth;
- successor owner is scoped to peak-domain model selection;
- parity lane and expected-diff lane are both defined;
- unclassified mismatches block product switching;
- expected diffs require a machine-readable approval record;
- non-selected candidate evidence limitations are handled explicitly;
- fixture families cover legacy selector behavior and evidence-chain successor
  semantics;
- output-contract parity is required while legacy fields remain public;
- product switching requires either parity or approved expected diff;
- legacy scorer retirement is blocked until the selector switch has passed this
  gate.
