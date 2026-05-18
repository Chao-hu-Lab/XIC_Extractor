# Region-first Safe Merge Promotion v1 Spec

**Date:** 2026-05-18
**Status:** Planned implementation slice
**Branch:** `codex/targeted-nl-dropout-convergence`
**Depends on:** `2026-05-18-region-first-model-selection-shadow-report-v1-spec.md`

## Summary

This phase adds one opt-in resolver mode: `region_first_safe_merge`.

The mode promotes only adjacent WIS-selected local-minimum intervals that look
like one continuous peak envelope. It is designed for the observed failure mode
where local minimum cuts a stable peak into adjacent pieces and under-reports
area, while the selected identity and dominant apex are already correct.

The default resolver remains unchanged.

## Non-goals

- Do not make `region_first_safe_merge` the default.
- Do not promote `split_supported`, `neighbor_apex_preferred`, or
  `wider_boundary_preferred`.
- Do not promote `same_apex_wider_boundary_merge`.
- Do not change target labels, m/z matching, neutral-loss evidence,
  reliability state, workbook schema, or untargeted matrix identity.
- Do not read `peak_region_selection_shadow.tsv` as production input.

## Public Config Contract

`resolver_mode` accepts:

- `legacy_savgol`
- `local_minimum`
- `arbitrated`
- `region_first_safe_merge`

`region_first_safe_merge` is explicit opt-in and experimental. Existing resolver
mode defaults, metadata fields, and config hash behavior are preserved.

## Promotion Gate

Production safe merge may replace only the selected peak integration boundary
and area. It must not change the selected target/sample identity or selected
apex identity. It must also preserve the original selected candidate's MS2/NL
evidence window so widened integration does not change neutral-loss status or
targeted reliability state.

A row is eligible only when the domain region decision has:

- `shadow_status=evaluated`
- `shadow_verdict=merge_suggested`
- `merge_suggestion_source=adjacent_wis_local_minimum_merge`
- `selected_interval_count >= 2`
- `selected_interval_gap_max_min <= 0.08`
- `area_ratio <= 1.20`
- absolute current apex to shadow dominant apex delta `<= 0.03 min`
- every promoted interval includes `local_minimum` proposal support
- no CWT-only promotion source

If any condition is missing or fails, the resolver returns the current selected
peak unchanged.

## Data Flow

```text
raw trace
  -> existing candidate formation
  -> boundary hypotheses
  -> weighted interval selection
  -> decide_region_selection()
  -> safe merge gate
  -> selected peak result
```

The production resolver shares the same domain decision as the shadow report.
It does not depend on generated TSV files.

## Acceptance Criteria

1. `region_first_safe_merge` is accepted by config validation and documented in
   `settings.example.csv`.
2. Existing resolver modes produce unchanged behavior.
3. Adjacent-WIS local-minimum shallow split can update selected area/boundary.
4. Same-apex wider boundary merge remains shadow-only.
5. Split, neighbor, wider-boundary, and CWT-only alternatives never update the
   production selected peak.
6. Default 8RAW output hash remains unchanged.
7. Opt-in 8RAW comparison reports label, m/z, sample, current/safe RT and area,
   area ratio, and promotion reason.
8. 85RAW opt-in validation shows no ISTD benchmark regression before default
   promotion is considered.
