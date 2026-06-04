# Selected Full-Envelope FE2 Diagnostic Characterization

**Date:** 2026-06-03
**Goal:** [Selected full-envelope quantitation boundary implementation goal](../plans/2026-06-03-selected-full-envelope-quantitation-boundary-implementation-goal.md)
**Spec:** [Selected full-envelope quantitation boundary spec](../specs/2026-06-03-selected-full-envelope-quantitation-boundary-spec.md)
**Readiness label:** `diagnostic_only`

## Verdict

FE2 introduces a package-level diagnostic projection for selected full-envelope
evaluations. It does not add product wiring, primary matrix mutation, workbook
schema changes, RAW execution, or a `tools/diagnostics` CLI entry-point.

Because no diagnostic CLI or `tools/diagnostics` entry-point was added, the
diagnostic tool index is intentionally unchanged in this phase.

## Diagnostic Owner

Domain evaluator:

- `xic_extractor/peak_detection/selected_envelope.py`

Diagnostic projection and aggregate manifest:

- `xic_extractor/peak_detection/selected_envelope_diagnostics.py`

The projection consumes `SelectedEnvelopeBoundaryEvaluation`; it does not rescan
traces, recompute boundaries, or run baseline integration in a writer layer.

## Row Versus Manifest Decisions

Row-level selected-envelope diagnostic output uses:

- `row_boundary_decision = accept_candidate | reject | externalize | defer`

Aggregate diagnostic manifest output uses:

- `gate_decision = promote | no_go | externalize | defer`

This keeps a clean single-row boundary disposition from being mistaken for a
phase-level product promotion decision.

An empty diagnostic surface is not evidence. If no selected-envelope rows are
evaluated, the manifest must emit `gate_decision=defer`,
`blocked_reasons=no_evaluated_rows`, and `next_gate=bounded_follow_up_required`.

`split_supported` is a first-class row-level change class. Near-apex secondary
maxima or shoulders are externalized as `row_boundary_decision=externalize` with
`boundary_stop_reason=split_supported_review_required`. They must appear in
manifest high-risk strata. More distant competing apices remain
`neighbor_apex`.

## FE2 Test Surface

The FE2 diagnostic contract is protected by:

- `tests/test_selected_full_envelope_diagnostics.py`
- `tests/test_selected_full_envelope_policy.py`
- `tests/test_selected_full_envelope_fe0_contract.py`

The tests lock:

- selected candidate id is required for diagnostic projection;
- policy snapshot and resolved baseline-return threshold are rendered from the
  domain carrier;
- diagnostic rows do not emit row-level `gate_decision`;
- aggregate manifests compute `promote`, `no_go`, `externalize`, and `defer`;
- empty manifests cannot promote;
- `split_supported` rows are externalized and included in high-risk strata;
- AsLS area remains owned by the evaluator, not by output writers.
