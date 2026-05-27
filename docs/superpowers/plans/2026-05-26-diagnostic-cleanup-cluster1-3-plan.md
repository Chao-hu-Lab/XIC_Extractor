# Diagnostic Cleanup Cluster 1/3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the real duplication in evidence-consistency diagnostics and common diagnostic IO helpers while preserving output schemas and behavior.

**Architecture:** Keep diagnostic entry points and topic-specific models intact. Promote repeated TSV parsing, scalar conversion, label splitting, workbook header lookup, and TSV writing into `tools/diagnostics/diagnostic_io.py`; update duplicated callers to import those helpers instead of carrying local copies.

**Tech Stack:** Python diagnostics, `csv`, `openpyxl`, pytest.

---

## Scope

### Now

- Cluster 1: consolidate duplicated helper logic in:
  - `tools/diagnostics/evidence_spine_consistency_io.py`
  - `tools/diagnostics/evidence_spine_consistency_writers.py`
  - `tools/diagnostics/cross_report_evidence_consistency_io.py`
  - `tools/diagnostics/cross_report_evidence_consistency_writers.py`
- Cluster 3: migrate the listed loader/writer modules to shared helpers where behavior-equivalent:
  - `build_istd_false_missing_fixture.py`
  - `cwt_peak_candidate_audit_io.py`
  - `rt_normalization_anchor_loaders.py`
  - `targeted_gt_alignment_audit_io.py`
  - `targeted_istd_benchmark_loaders.py`
  - `targeted_nl_dropout_root_cause_io.py`
  - `targeted_peak_reliability_loaders.py`
- Update docs/index wording that marks Cluster 1/3 as pending.

### Later

- Do not merge the backfill review trio here. That requires method-level review.
- Do not promote phase gates into package runtime here.

### Acceptance Criteria

- Existing output schemas stay byte-contract compatible: no renamed TSV columns, workbook sheets, JSON keys, or CLI args.
- Shared helpers live in `tools/diagnostics/diagnostic_io.py`; topic modules remain thin and domain-specific.
- Related tests pass:
  - `tests/test_diagnostic_io.py`
  - `tests/test_evidence_spine_consistency.py`
  - `tests/test_cross_report_evidence_consistency.py`
  - `tests/test_cwt_peak_candidate_audit.py`
  - `tests/test_rt_normalization_anchors.py`
  - `tests/test_targeted_gt_alignment_audit.py`
  - `tests/test_targeted_istd_benchmark.py`
  - `tests/test_targeted_nl_dropout_root_cause_audit.py`
  - `tests/test_targeted_peak_reliability_audit.py`
  - `tests/test_istd_false_missing_fixture.py`

## Tasks

### Task 1: Shared Diagnostic IO Helpers

- [ ] Add tests in `tests/test_diagnostic_io.py` for:
  - UTF-8-SIG TSV required-column reads.
  - `optional_float`, `optional_int`, `bool_value`, `text_value`, and `split_semicolon_labels`.
  - `required_indexes` returning stable header indexes and clear missing-column errors.
- [ ] Implement the helpers in `tools/diagnostics/diagnostic_io.py`.
- [ ] Run `python -m pytest tests\test_diagnostic_io.py -q`.

### Task 2: Cluster 1 Evidence Consistency Twins

- [ ] Replace local `_read_required_tsv`, `_optional_float`, `_bool_value`, and writer `_write_tsv` copies with `diagnostic_io` imports.
- [ ] Keep `ConsistencyRow` and `ConsistencySummary` dataclasses topic-specific because the row schemas are not identical.
- [ ] Run `python -m pytest tests\test_evidence_spine_consistency.py tests\test_cross_report_evidence_consistency.py -q`.

### Task 3: Cluster 3 Loader/Writer Infrastructure

- [ ] Migrate listed modules to `diagnostic_io` for repeated scalar parsing, TSV required reads, header lookup, semicolon label parsing, and TSV writes.
- [ ] Preserve stricter per-module error wording where tests assert it.
- [ ] Run the Cluster 3 test list from acceptance criteria.

### Task 4: Docs And Review

- [ ] Update `tools/diagnostics/INDEX.md` and `docs/superpowers/notes/2026-05-26-diagnostic-lifecycle-audit-note.md` so Cluster 1/3 are recorded as addressed, with Cluster 2 still pending method review.
- [ ] Run `git diff --check`.
- [ ] Review diff for public contract drift and accidental schema changes.

## Plan Self-Review

- Spec coverage: Cluster 1 and Cluster 3 are both covered; Cluster 2 and phase-gate promotion are explicitly out of scope.
- Placeholder scan: no TODO/TBD placeholders.
- Contract risk: row dataclasses are not merged because their schemas differ; helper consolidation only.
- Stop condition: if a test shows output schema or error contract drift, fix the helper call site rather than changing expected output.
