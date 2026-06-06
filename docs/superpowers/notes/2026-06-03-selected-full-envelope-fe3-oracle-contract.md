# Selected Full-Envelope FE3 Oracle Contract

**Date:** 2026-06-03
**Goal:** [Selected full-envelope quantitation boundary implementation goal](../plans/2026-06-03-selected-full-envelope-quantitation-boundary-implementation-goal.md)
**Spec:** [Selected full-envelope quantitation boundary spec](../specs/2026-06-03-selected-full-envelope-quantitation-boundary-spec.md)
**Readiness label:** `diagnostic_only`

## Verdict

FE3 now has a package-level manual/expert oracle comparison contract. It can
compare the current resolver interval and candidate selected-envelope interval
against a reviewed boundary/area oracle and decide whether FE4 8RAW changed-row
review is allowed.

This phase does not load RAW files, generate plots, read targeted workbook
areas as truth, or switch product matrix behavior.

## Oracle Boundary

Accepted oracle sources:

- `manual_overlay`
- `expert_overlay`
- `manual_2raw`

`targeted_workbook_control` can be used only as `benchmark_control_only`.
It cannot be promoted to `expert_reviewed` boundary truth.

Candidate identity must match through `selected_candidate_id`; mismatched rows
are rejected before comparison.

## Gate Meaning

The FE3 oracle manifest emits:

- `gate_decision=promote` when expert/manual oracle rows support the
  selected-envelope candidate over the old resolver interval;
- `gate_decision=no_go` when the old resolver interval is closer to oracle
  boundary/area;
- `gate_decision=defer` when no reviewed boundary oracle rows exist or when
  reviewed rows do not provide positive in-tolerance selected-envelope support.

Positive support requires at least one expert/manual oracle row where the
selected-envelope interval is closer than the resolver interval and the selected
boundary and area are both within the row's accepted tolerance. Ties and
out-of-tolerance selected-envelope rows cannot authorize FE4.

`promote` here means only that FE4 8RAW changed-row review may proceed. It does
not authorize product wiring or primary matrix mutation.

## FE3 Test Surface

The FE3 oracle contract is protected by:

- `tests/test_selected_full_envelope_oracle.py`

The tests lock:

- selected-envelope-vs-resolver comparison against manual/expert boundary and
  area;
- targeted workbook control cannot masquerade as boundary truth;
- benchmark-only rows do not satisfy the oracle gate;
- candidate id mismatches are rejected;
- FE4 is allowed only after reviewed oracle support;
- ties and out-of-tolerance selected-envelope rows defer instead of promote;
- resolver-closer rows produce `no_go`.
