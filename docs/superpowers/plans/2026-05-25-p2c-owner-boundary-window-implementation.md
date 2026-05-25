# P2c Owner Boundary Window Implementation Plan

**Date:** 2026-05-25
**Status:** Reviewed and revised after rejected backfill-window experiment
**Gate language:** `diagnostic_only` until 8RAW evidence is regenerated.

## Goal

Fix over-wide alignment owner boundaries that come from re-resolving discovery
candidates in broad `seed_rt +/- max_rt_sec` XIC windows. The immediate
representative failure is `d3-5-hmdC`, where the earlier alignment boundary
could reach back to `7.25717` or another unrelated low-signal region while the
visible peak envelope is much narrower.

## Root Cause

`build_sample_local_owners()` extracts the owner XIC using
`candidate_seed_rt +/- alignment_config.max_rt_sec`, and `max_rt_sec` defaults
to `180` seconds. For detected discovery candidates that already carry
`ms1_peak_rt_start/end` and `ms1_search_rt_min/max`, this makes the
local-minimum resolver see unrelated low signal or neighbor peaks and produce an
over-wide candidate interval.

After the owner-bound fix, primary family consolidation exposed a second
selection issue: when a detected observation and a rescued duplicate projection
share the same apex, `_selected_observations_by_sample()` could still choose the
rescued projection only because its area was larger. That can erase MS2-backed
detected status from the production row and turn an otherwise supported ISTD row
into `rescue_only`.

A narrower owner-backfill request window was tested and rejected because it
regressed the targeted ISTD benchmark from PASS to SPLIT/COVERAGE failures. Do
not change owner backfill request width in this P2c fix; backfill remains a
coverage mechanism until a separate reviewed plan handles it.

## Now

1. Add a failing ownership test showing that candidate-specific MS1 peak bounds
   limit the owner XIC request when those fields are finite and contain the
   resolved MS1 apex.
2. Implement a small helper in `xic_extractor/alignment/ownership.py` that
   chooses the owner re-resolution RT window:
   - prefer finite `ms1_peak_rt_start/end` expanded by `0.10` min when those
     bounds contain the candidate MS1 apex or seed RT
   - otherwise use finite `ms1_search_rt_min/max` when `min < seed_rt < max`
   - otherwise fall back to the existing `seed_rt +/- max_rt_sec`
3. Preserve owner backfill request behavior to avoid cross-sample coverage
   regression.
4. Add a failing primary-consolidation test for same-apex detected vs rescued
   duplicate projection, then prefer detected only for that same-apex duplicate
   projection case.
5. Preserve batch and non-batch source behavior.
6. Rerun targeted ownership/backfill/consolidation tests and alignment process
   tests.
7. Rerun 8RAW P2 alignment, P2 gate, baseline truth all-status audit, and the
   existing evidence-spine consistency diagnostic.
8. Record whether the d3-5-hmdC boundary narrows and whether the revised P2b
   conclusion changes.

## Later

- Add a dedicated config knob only if 8RAW shows the fixed `0.10` min padding is
  too tight or too loose for candidate owner re-resolution.
- Revisit owner backfill boundary trimming only in a separate plan that protects
  targeted ISTD coverage first.
- Promote a richer boundary model only after Phase 1 AsLS and boundary evidence
  stabilizes.

## Not In Scope

- Do not change AsLS baseline integration.
- Do not switch production `area_baseline_corrected` to AsLS.
- Do not alter primary family consolidation identity decisions.
- Do not make area-baseline changes to hide a boundary problem.
- Do not implement Cleanup C-specs.

## Acceptance Criteria

- Unit test proves owner XIC extraction uses padded candidate peak bounds when
  safe.
- Unit test proves same-apex rescued duplicate projection no longer replaces a
  detected observation.
- Existing owner grouping, owner backfill, primary consolidation, and process
  tests still pass.
- 8RAW alignment rerun exits `0`.
- For `BenignfatBC1055_DNA / d3-5-hmdC`, the old over-wide alignment row
  `FAM000153` at `7.25717-9.12608` is replaced by the boundary-corrected
  alignment row `FAM000162` at `8.83531-9.12608`.
- No new `area_baseline_corrected_asls > area` row appears in the all-status
  baseline truth audit.
- Final note clearly marks the result as `diagnostic_only` or
  `production_candidate`; it must not imply AsLS production switch.

## Stop Conditions

- Candidate search bounds remove legitimate detected owners in 8RAW.
- P2 gate develops new hard blockers not explained by boundary narrowing.
- Evidence-spine mismatch count improves for one row but regresses broadly.
