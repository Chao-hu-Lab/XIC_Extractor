# Graphify And Complexity Hotspot Inventory

**Date:** 2026-05-20
**Status:** Inventory only
**Branch:** `codex/graphify-code-graphs`
**Graph commit:** `aa46b79b`
**Master baseline:** `origin/master` at `51b2f03`

---

## Summary

This checkpoint refreshes the code graphs and combines graph-structure pressure
with complexity scanner leads. It does not authorize production refactors.

The two signals agree: the highest-pressure areas are alignment core models /
workflow and diagnostics/reporting scripts.

Recommended next step: create a fresh worktree from current `master` for the
first implementation PR. Keep this graph branch as an analysis artifact branch.
If this note has been copied into the implementation worktree, treat it as
context only; do not create another worktree from inside
`codex/diagnostics-structure-optimization`.

## Scope Analyzed

- `xic_extractor` graph refreshed with `graphify update xic_extractor`.
- `tools` graph refreshed with `graphify update tools`.
- `scripts` graph refreshed with `graphify update scripts`.
- `tests` graph refreshed with `graphify update tests`.
- `gui` checked with `graphify update gui`; no topology change.
- Complexity scanner run with generated/cache/output/worktree directories
  excluded.

No production source code was modified in this checkpoint.

## Graphify Findings

### xic_extractor God Nodes

| rank | node | edges | interpretation |
|---:|---|---:|---|
| 1 | `AlignmentConfig` | 46 | broad configuration dependency across alignment |
| 2 | `AlignedCell` | 43 | central output cell contract; risky to keep extending |
| 3 | `XICTrace` | 32 | shared extraction/trace contract |
| 4 | `SampleLocalMS1Owner` | 26 | owner-resolution pressure point |
| 5 | `OwnershipBuildResult` | 25 | owner pipeline result contract |
| 6 | `AlignmentMatrix` | 24 | final matrix/audit carrier |
| 7 | `AmbiguousOwnerRecord` | 23 | ambiguity audit surface |
| 8 | `OwnerAssignment` | 22 | owner decision contract |
| 9 | `OwnerAlignedFeature` | 22 | owner family/cell bridge |
| 10 | `XICRequest` | 21 | trace request primitive |

### xic_extractor Communities

- Community 0 contains owner/backfill/cell-quality/config concepts and is the
  largest current pressure point.
- Community 2 contains alignment clustering and compatibility helpers.
- Community 4 contains peak boundary/audit helpers.

### tools God Nodes

| rank | node | edges | interpretation |
|---:|---|---:|---|
| 1 | `run_rt_normalization_anchor_diagnostic()` | 20 | large diagnostic runner |
| 2 | `run_region_first_safe_merge_comparison()` | 18 | comparison model + IO coupling |
| 3 | `_h()` | 16 | HTML rendering helpers in report modules |
| 4 | `_audit_family()` | 15 | large family audit routine |
| 5 | `build_decision_report()` | 14 | report model assembly pressure |
| 6 | `run_targeted_istd_benchmark()` | 13 | benchmark orchestration pressure |
| 7 | `_summarize_target()` | 13 | targeted summary logic |
| 10 | `build_family_ms1_evidence_summary()` | 12 | MS1 overlay classification summary |

## Complexity Scanner Findings

The scanner output should be treated as leads, not proof. It repeatedly flags:

- nested loops and sort-in-loop patterns in alignment core,
- repeated loader/classifier/writer work in diagnostics,
- script-only hotspots that are less urgent than production or diagnostic
  surfaces.

### Production-adjacent Hotspots

| module | scanner signal | risk | first safe action |
|---|---|---|---|
| `xic_extractor/alignment/clustering.py` | repeated sort and reattach loops | High | add characterization/benchmark first; do not start here |
| `xic_extractor/alignment/family_integration.py` | family x sample integration and conflict component scans | High | characterize matrix equality and owner conflict behavior |
| `xic_extractor/alignment/claim_registry.py` | compatibility grouping and sort-in-loop leads | Medium-high | best first production-side optimization candidate after diagnostics |
| `xic_extractor/alignment/owner_backfill.py` | repeated nested loops in owner backfill request handling | High | do not refactor before backfill identity tests are pinned |
| `xic_extractor/alignment/backfill.py` | cluster x sample loop | Medium | likely expected shape; optimize only if measured |
| `xic_extractor/alignment/drift_evidence.py` | repeated sorting / rolling median lookup | Medium | possible small extraction after tests |

### Diagnostic Hotspots

| module | scanner / graph signal | risk | first safe action |
|---|---|---|---|
| `tools/diagnostics/targeted_peak_reliability_audit.py` | large file, classification + IO + writing | Medium | split loaders/classifier/writers |
| `tools/diagnostics/targeted_istd_benchmark.py` | benchmark orchestration hub | Medium-high | split workbook loader, alignment loader, matcher, stats, writers |
| `tools/diagnostics/evidence_spine_consistency.py` | large diagnostic, nested summary work | Medium | split input rows, matcher, summary, writers |
| `tools/diagnostics/low_ms1_assessable_coverage_audit.py` | large diagnostic, sort-in-loop leads | Medium | split queue building and classifier from writers |
| `tools/diagnostics/family_ms1_overlay_plot.py` | plotting + evidence summary + trace extraction | Medium | split plotting surface from MS1 evidence summary |

## Recommended Checkpoint Order

### Checkpoint 1: Diagnostics Split, First PR

Start with a fresh worktree from `master`.

Target either:

1. `tools/diagnostics/targeted_peak_reliability_audit.py`, or
2. `tools/diagnostics/low_ms1_assessable_coverage_audit.py`.

Split into:

- loaders,
- domain classifier / summary model,
- TSV/JSON/Markdown writers,
- CLI facade.

Do not change output schemas or classification semantics.

### Checkpoint 2: Shared Diagnostic IO

After one diagnostic split proves the pattern, extract shared diagnostic helpers
only where duplication is concrete:

- TSV loading with required-column errors,
- TSV writing,
- safe float/int/bool parsing,
- counter formatting,
- markdown table helpers.

Avoid making a generic framework.

### Checkpoint 3: Alignment Production Hot Path Plan

Only after diagnostic split:

- choose `claim_registry.py` as the first production-side optimization candidate,
- add characterization tests,
- add a small synthetic benchmark or timing fixture,
- preserve matrix/review/cell output equality.

Do not start with `clustering.py`, `family_integration.py`, or
`owner_backfill.py`.

## Stop Conditions

- If a proposed refactor changes matrix identity, targeted reliability,
  production gates, score thresholds, or workbook/TSV schemas, stop and write a
  separate behavior-change plan.
- If tests cannot distinguish move-only from behavior change, add
  characterization tests before moving code.
- If a module is a graph god node and production-adjacent, do not refactor it in
  the same PR as diagnostics cleanup.

## Next Worktree Recommendation

Create a new worktree from current `master`, for example:

```powershell
git worktree add .worktrees/diagnostics-structure-optimization -b codex/diagnostics-structure-optimization master
```

This keeps `codex/graphify-code-graphs` as the graph/inventory branch and keeps
the implementation PR reviewable.
