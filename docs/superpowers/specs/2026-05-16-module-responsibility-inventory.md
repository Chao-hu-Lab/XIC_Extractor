# Module Responsibility Inventory

**Date:** 2026-05-16
**Status:** Planning inventory only
**Worktree:** `codex/module-responsibility-decomposition`

---

## Summary

This inventory captures the current maintainability pressure in the untargeted
alignment and diagnostic surfaces. It is not an instruction to split every large
file. Large files are only a problem when they combine unrelated reasons to
change, duplicate rules, or make future scientific behavior hard to verify.

The immediate refactor target is responsibility clarity, not new behavior:

- no matrix identity changes,
- no production gate changes,
- no backfill behavior changes,
- no iRT or RT-warping gate changes,
- no TSV, XLSX, JSON, Markdown, or HTML schema changes.

## Inventory

| Module | Current responsibilities | Risk | Split priority | First safe extraction target | Required characterization tests |
|---|---|---|---|---|---|
| `tools/diagnostics/alignment_decision_report.py` | CLI parsing, TSV/JSON loading, verdict rules, matrix cleanliness metrics, ISTD summary shaping, backfill economics shaping, RT normalization shaping, HTML rendering, CSS, formatting helpers | Medium | PR1 | Move data loading/report model/rendering into focused helpers while preserving emitted HTML | `tests/test_alignment_decision_report.py`; compare generated section presence, verdict, escaping, missing optional inputs |
| `tools/diagnostics/single_dr_production_gate_decision_report.py` | CLI parsing, alignment TSV loading, discovery candidate loading, RT/ISTD enrichment, single-dR classification, gate candidate aggregation, TSV/JSON/Markdown writing | Medium | PR2 | Move loaders and output writers away from classification and gate candidate model | `tests/test_single_dr_production_gate_decision_report.py`; verify candidate counts, ISTD blocking, missing enrichment, non-dR exclusion |
| `tools/diagnostics/targeted_istd_benchmark.py` | Targeted workbook parsing, active tag filtering, alignment TSV/cell loading, feature matching, RT/area statistics, failure modes, TSV/JSON/Markdown writing | Medium-high | PR3 | Split workbook loader, alignment loader, matcher, statistics, and writers | `tests/test_targeted_istd_benchmark.py`; preserve PASS/MISS/SPLIT/DRIFT/AREA_MISMATCH behavior and JSON shape |
| `xic_extractor/alignment/pipeline.py` | Workflow orchestration, backend choice, raw source opening, timing wrappers, output paths, atomic writes, metadata, HTML/XLSX/TSV dispatch | Medium-high | PR4 | Extract output path/atomic write/metadata helpers and timed raw source adapters | `tests/test_alignment_pipeline.py`, `tests/test_run_alignment.py`, `tests/test_alignment_boundaries.py`; preserve artifact names and lazy RAW import boundary |
| `xic_extractor/alignment/primary_consolidation.py` | Duplicate graph construction, near-duplicate compatibility, winner selection, observation merge, loser clone construction, family stats, status ranking | High | PR5, after characterization | First add graph/winner/cell-merge characterization tests; only then move graph utilities or stats helpers | `tests/test_alignment_primary_consolidation.py`, `tests/test_pre_backfill_consolidation.py`; include loser retention and winner cell merge cases |
| `xic_extractor/alignment/clustering.py` | Anchor sorting, greedy cluster assignment, same-sample replacement, final partitioning, public ID assignment, compatibility accessors | High | Do not split yet | Only extract typed accessor helpers after public cluster behavior is fully characterized | `tests/test_alignment_clustering.py`; preserve cluster IDs, sort order, same-sample replacement |
| `xic_extractor/alignment/ownership.py` | XIC request batching, trace extraction, peak resolution, owner grouping, ambiguity detection, identity event conversion | High | Do not split yet | Only extract request batching or identity-event adapters if tests pin owner assignment behavior | `tests/test_alignment_ownership.py`, `tests/test_alignment_owner_clustering.py`; preserve owner grouping and ambiguous records |
| `xic_extractor/discovery/ms1_backfill.py` | Discovery MS1 windowing, trace extraction, peak support, candidate evidence shaping | Medium-high | Out of this phase | Keep under discovery-specific refactor scope, not alignment responsibility cleanup | `tests/test_discovery_ms1_backfill.py` |
| `xic_extractor/peak_scoring.py` | Peak scoring signals, confidence, severity, reason text, score output | High | Covered by earlier decomposition scope | Do not mix with alignment refactor | `tests/test_peak_scoring.py` |

## Recommended Order

1. Split diagnostic report rendering and loading first. These combine IO,
   report-model shaping, and rendering while carrying lower scientific risk.
2. Split diagnostic gate reports next, keeping production gate rules imported
   from domain helpers rather than reimplemented in report scripts.
3. Split targeted benchmark internals after preserving workbook parsing and
   strict verdict behavior with tests.
4. Split alignment pipeline adapters only after diagnostic surfaces are stable.
5. Touch primary consolidation last. It is central to final matrix identity and
   needs characterization before movement.

## Do Not Split Yet

Do not begin with `primary_consolidation.py`, `clustering.py`, or `ownership.py`.
They are domain-heavy and easy to break in ways that unit tests may not catch
without additional characterization. Their first PR should add tests, not move
logic.

Do not split `peak_scoring.py`, `signal_processing.py`, `extractor.py`, or
`scripts/csv_to_excel.py` as part of this alignment cleanup. Those targets are
already covered by the workbook, extraction, and signal-processing decomposition
spec.

## Success Criteria

- Future agents can identify the right owner module before adding a diagnostic,
  gate, renderer, loader, writer, or domain rule.
- Production logic and diagnostic logic do not maintain parallel copies of the
  same gate or identity rule.
- Refactor PRs can be reviewed as move-only changes unless explicitly scoped as
  behavior changes.
- Any file near 500 lines that receives a new responsibility must either reject
  the change or introduce a focused helper module with tests.
