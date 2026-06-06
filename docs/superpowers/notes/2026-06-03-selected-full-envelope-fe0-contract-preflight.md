# Selected Full-Envelope FE0 Contract Preflight

**Date:** 2026-06-03
**Goal:** [Selected full-envelope quantitation boundary implementation goal](../plans/2026-06-03-selected-full-envelope-quantitation-boundary-implementation-goal.md)
**Spec:** [Selected full-envelope quantitation boundary spec](../specs/2026-06-03-selected-full-envelope-quantitation-boundary-spec.md)
**Readiness label:** `diagnostic_only`

## Verdict

FE0 locks the implementation contract before selected-envelope behavior is
implemented.

The selected-envelope path must use a package-level domain carrier, not output
writer recomputation and not an overloaded targeted `Area` column.

This note covers the implementation goal's FE0 contract preflight. The
row-level diagnostic comparison described in the primary spec is implemented
later in the goal as FE2, after FE1 locks synthetic boundary policies.

## Public Output Contract

Targeted CSV/workbook `Area` remains raw integrated area for this goal.

Evidence:

- `xic_extractor/output/schema.py` documents long `Area` as
  `raw integrated area`.
- `ExtractionResult.reported_peak_area` returns
  `IntegrationResult.area_raw_counts_seconds` when selected integration exists.
- `xic_extractor/output/csv_writers.py` writes long `Area` from
  `result.reported_peak_area`.

Alignment primary matrix area remains the AsLS-selected product value path.

Evidence:

- `xic_extractor/alignment/primary_matrix_area.py` accepts a primary matrix value
  only when `baseline_type == "asls"` and
  `area_baseline_corrected` is positive finite.

## Domain Carrier Strategy

Selected-envelope work must introduce a named package-level carrier for boundary
evaluation before any product wiring.

Preferred shape:

```text
SelectedEnvelopeBoundaryEvaluation
  selected_candidate_id
  resolver_interval
  selected_envelope_interval
  quantitation_context_interval
  policy_snapshot
  resolved_baseline_return_threshold
  selected_boundary_mode
  legacy_resolver_provenance
  boundary_change_class
  boundary_evidence_sources
  boundary_stop_reason
  asls_area_old_interval
  asls_area_selected_envelope
  area_delta_ratio
  row_boundary_decision
  gate_manifest fields (aggregate only; not a row-level promotion decision)
```

Initial projection should be diagnostic sidecar or appended diagnostic fields.
The carrier may be attached to selected `PeakHypothesis` / audit state or
projected into an `IntegrationResult`-adjacent model. It should not replace
targeted `Area`, mutate workbook product sheets, change the alignment primary
matrix, or require output writers to rescan traces or run baseline integration
before the promotion gate.

## Diagnostic Rendering Boundary

`peak_candidate_boundaries` currently recomputes baseline area during diagnostic
row construction. That is acceptable for the existing boundary-audit TSV, but it
is not acceptable for selected-envelope product diagnostics.

Future selected-envelope diagnostics must consume the domain carrier produced in
`xic_extractor/peak_detection`. Diagnostic writers may render `asls_area_*`
fields, but must not recompute selected-envelope areas.

## `region_first_safe_merge` Boundary

`region_first_safe_merge` remains an existing compatibility resolver token and
can still characterize its current behavior. It must not become the fallback
authorization for selected-envelope promotion.

Selected-envelope promotion must be sourced from the new selected-envelope gate
decision, with any legacy resolver token recorded only as provenance.

## FE0 Test Surface

The FE0 contract is protected by:

- `tests/test_selected_full_envelope_fe0_contract.py`

That test file locks:

- targeted `Area` raw semantics;
- alignment primary matrix AsLS semantics;
- current `IntegrationResult` single-interval limitation;
- diagnostic row-builder recomputation risk;
- `region_first_safe_merge` compatibility/provenance boundary.
