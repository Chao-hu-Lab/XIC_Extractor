# Region-first Model-selection Shadow Report v1 Spec

**Date:** 2026-05-18
**Status:** Implementation slice
**Branch:** `codex/region-first-safe-merge-validation`
**Source memo:** `C:\Users\user\Downloads\lcms_gcms_peak_pipeline_handoff.md`

## Summary

This phase adds an audit-only shadow report for region-first peak model
selection. It uses existing peak candidates, boundary hypotheses, CWT proposal
evidence, and weighted interval selection to explain where the current
local-minimum-driven interval may be too narrow, split, or pointed at a weaker
neighboring apex.

This phase must not change production extraction. `XIC Results`, workbook
schemas, targeted reliability states, `resolver_mode` defaults, and untargeted
matrix logic remain unchanged.

## Non-goals

- Do not add a promoted production resolver.
- Do not add a formal `TraceGroup` abstraction.
- Do not add ML/DL, GC-MS logic, calibration curves, raw ingestion QC, or
  untargeted matrix gates.
- Do not let CWT, local minimum, boundary hypotheses, or WIS become a single
  final authority.

## Shadow Status

Every target/sample review row must emit one status:

- `evaluated`: shadow decision was computed.
- `skipped_no_candidate`: no selected candidate interval was available.
- `skipped_no_boundary`: no boundary hypotheses were available.
- `skipped_low_scan_support`: the selected candidate interval had fewer than
  three scans.
- `skipped_invalid_trace`: required numeric boundary fields were malformed or
  internally inconsistent.

Skipped rows must remain visible and use `shadow_verdict=insufficient_evidence`.

## Shadow Verdict

V1 uses conservative fixed thresholds:

- minimum scan support: `3`
- wider area ratio cutoff: `1.50`
- score delta cutoff: `15`
- split total-score delta cutoff: `20`
- adjacent merge area ratio maximum: `1.20`
- adjacent merge interval gap maximum: `0.08 min`

Verdicts:

- `insufficient_evidence`: no comparable boundary, low scan support, invalid
  trace, or missing selected candidate.
- `current_supported`: current selected candidate interval is not contradicted
  by same-apex boundary evidence, neighbor evidence, merge evidence, or split
  evidence.
- `wider_boundary_preferred`: same selected apex has an alternate boundary with
  area at least `1.50x` current area and boundary score not below current.
- `neighbor_apex_preferred`: a non-CWT-only neighboring apex has score at least
  `15` above current.
- `merge_suggested`: multiple local-minimum candidates either sit inside the
  selected apex's wider envelope, or are adjacent WIS-selected intervals with
  only small area gain. This is the explicit shallow-valley guardrail.
  `merge_suggestion_source` distinguishes the two sources:
  `adjacent_wis_local_minimum_merge` is the only source eligible for a later
  safe-merge production experiment; `same_apex_wider_boundary_merge` remains
  shadow-only unless a later spec promotes it explicitly.
- `split_supported`: WIS-selected non-overlapping intervals have at least two
  supported segments and total score at least `20` above the best single
  interval.

Verdict precedence is:

```text
skipped/insufficient
  -> merge_suggested
  -> split_supported
  -> neighbor_apex_preferred
  -> wider_boundary_preferred
  -> current_supported
```

## Output Contract

When `emit_peak_candidates=true`, write:

- `peak_region_selection_shadow.tsv`
- `peak_region_selection_shadow_summary.tsv`
- `peak_region_selection_shadow_blast_radius.tsv`

The first two files are derived from existing
`peak_candidate_boundary_rows`; they must not reorder or mutate
`peak_candidates.tsv` or `peak_candidate_boundaries.tsv`.

Each shadow row includes sample, group, target label, target m/z, role,
resolver mode, current/shadow RT and area, `shadow_status`,
`shadow_verdict`, `merge_suggestion_source`, score delta, area ratio, scan
support, WIS selected interval count, selected interval max gap, selected
interval total score, best single-boundary score, support labels, concern
labels, and review reason. These numeric model-selection fields are audit
evidence only; they do not change the selected peak or production integration.

For multi-interval `merge_suggested` or `split_supported` rows,
`shadow_rt_apex_min` is the dominant-area selected interval apex. The full
selected interval set remains available through `shadow_boundary_id`,
`selected_interval_count`, and `selected_interval_gap_max_min`. This avoids
presenting a small adjacent local-minimum cut as if it were the replacement
peak apex.

The blast-radius TSV aggregates what would be affected if a later PR promoted
the shadow decision. It must report total rows, rows that would change,
ISTD rows, target labels affected, and area-ratio distribution.

## Acceptance Criteria

1. Single broad peak with a shallow local-minimum split yields
   `merge_suggested` or `wider_boundary_preferred`, not `current_supported`.
2. True double peak with supported non-overlapping intervals yields
   `split_supported`.
3. CWT-only far alternative cannot yield `neighbor_apex_preferred`.
4. Missing or malformed boundary evidence emits a visible skipped row.
5. Existing candidate/boundary TSV headers remain unchanged.
6. Shadow TSVs are written only when `emit_peak_candidates=true`.
7. `XIC Results` selected RT and area remain unchanged.
8. Narrow tests, ruff, and mypy pass before real-data validation.
