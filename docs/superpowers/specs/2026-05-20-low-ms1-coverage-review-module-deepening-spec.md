# Low MS1 Coverage Review Module Deepening Spec

**Date:** 2026-05-20
**Status:** Ready for implementation planning
**Source inventory:** `docs/superpowers/notes/2026-05-20-graphify-complexity-hotspot-inventory.md`
**Recommended worktree:** `.worktrees/diagnostics-structure-optimization`
**Recommended branch:** `codex/diagnostics-structure-optimization`

---

## Summary

Deepen the low-MS1-assessable-coverage diagnostic into a focused module with a
small review interface and separate adapters. This is the first implementation
step after the graphify/complexity inventory.

This PR must be move-only / structure-only unless explicitly amended by a
separate behavior-change plan. It must not change production matrix behavior,
backfill behavior, scoring, reliability states, targeted benchmark semantics,
or output schemas.

## Problem

`tools/diagnostics/low_ms1_assessable_coverage_audit.py` has become a shallow
module. Its interface is essentially "run the script", while its implementation
contains several different reasons to change:

- TSV input loading and required-column validation.
- Family-level low-coverage classification.
- Seed-specific overlay request queue construction.
- Summary aggregation.
- TSV / JSON / Markdown writing.
- CLI parsing.

The module is currently useful, but the next MS1-backfill review iterations will
keep adding classification and review logic. Without a deeper module shape, the
diagnostic will become harder to test and future agents may mix presentation,
queueing, and evidence semantics in the same place.

## Desired Module Shape

The deepened module should expose one narrow review interface:

```text
run_low_ms1_coverage_review(inputs, config) -> LowMs1CoverageReviewResult
```

The exact names can follow project style, but the responsibilities must be
split by module seam:

| Module seam | Responsibility |
|---|---|
| CLI adapter | parse command-line args and call the review interface |
| loaders | read TSV/JSON inputs, validate required columns, preserve schema semantics |
| review model | typed rows / summary / overlay queue records |
| classifier | decide low-coverage / seed-aware queue classifications |
| writers | emit the existing TSV / JSON / Markdown outputs only |

The classifier is the key domain-adjacent seam. Writers and CLI must not decide
family verdicts or queue eligibility.

## In Scope

- Split `tools/diagnostics/low_ms1_assessable_coverage_audit.py` into focused
  helpers under `tools/diagnostics/`.
- Preserve the existing CLI command and arguments.
- Preserve all current output filenames and schemas.
- Preserve current classification semantics and thresholds.
- Keep real-data rerun commands compatible with existing 85RAW diagnostics.
- Add or move tests so the review interface is testable without invoking the
  CLI.

## Out Of Scope

- No production matrix change.
- No backfill behavior change.
- No final matrix identity change.
- No seed-aware production gate.
- No MS1 shape threshold change.
- No `family_ms1_overlay_plot.py` plotting redesign.
- No shared diagnostic framework beyond helpers required by this split.
- No `claim_registry.py`, `clustering.py`, `family_integration.py`, or
  `owner_backfill.py` changes.

## Public Contracts To Preserve

Existing output contracts must remain byte-level compatible where practical and
schema-compatible where ordering is already public:

- `low_ms1_assessable_coverage_summary.tsv`
- `low_ms1_assessable_coverage_rows.tsv`
- existing queue / seed overlay TSV outputs
- JSON output
- Markdown output
- CLI flags and default values
- missing-column error clarity

If any exact formatting differs, the PR must explain why and prove schema and
semantic equivalence with tests.

## Proposed File Layout

Implementation can choose final names, but this layout is recommended:

```text
tools/diagnostics/low_ms1_assessable_coverage_audit.py
  CLI facade only

tools/diagnostics/low_ms1_coverage_review_models.py
  dataclasses / typed result objects

tools/diagnostics/low_ms1_coverage_review_loaders.py
  TSV input loading and required-column validation

tools/diagnostics/low_ms1_coverage_review_classifier.py
  family classification and queue eligibility logic

tools/diagnostics/low_ms1_coverage_review_writers.py
  TSV / JSON / Markdown output writers
```

Do not create this full layout if the code does not justify every module. A
smaller split is acceptable if it still creates a deep review interface and
keeps CLI/writers out of classification.

## Checkpoints

### Checkpoint 0: Worktree Guard

- Create a new worktree from current `master`.
- Branch must be `codex/diagnostics-structure-optimization`.
- Confirm no graphify-output-only branch is used for production edits.
- Confirm the worktree is clean before implementation.

### Checkpoint 1: Characterization Tests

Before moving code, add or identify tests that pin:

- low coverage row classification,
- seed-specific overlay queue construction,
- summary aggregation,
- missing required columns,
- optional inputs / empty inputs,
- output filenames and required columns,
- representative output equivalence for TSV rows, queue ordering, JSON keys, and
  Markdown sections.

Expected test files:

- `tests/test_low_ms1_assessable_coverage_audit.py`
- possibly a new focused test file if the review interface becomes public
  within diagnostics.

Review gate: tests should fail only if current behavior is not preserved. If no
pre-refactor golden fixture exists, add characterization assertions that pin the
current output artifacts before moving code.

### Checkpoint 2: Extract Loaders And Models

- Move row dataclasses / typed result objects into a model module.
- Move TSV loading and required-column checks into a loader module.
- Keep CLI behavior unchanged.
- Keep output writing unchanged.

Review gate: no classification or writer behavior change.

### Checkpoint 3: Extract Classifier / Queue Builder

- Move low-coverage classification and seed-aware queue construction behind the
  review interface.
- Ensure writers consume result objects and do not recompute decisions.
- Ensure CLI remains a thin adapter.

Review gate: tests prove all classifications and queue counts match baseline.

### Checkpoint 4: Extract Writers

- Move TSV / JSON / Markdown emission into a writer module.
- Preserve output schemas and filenames.
- Keep formatting helpers local to writer unless used by multiple diagnostics.

Review gate: writer tests compare headers, key rows, JSON keys, and Markdown
sections.

### Checkpoint 5: Validation

Run focused tests:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_low_ms1_assessable_coverage_audit.py -q
```

Then run related diagnostics tests if touched:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_seed_aware_backfill_review.py tests\test_family_ms1_overlay_batch.py -q
```

Final checks:

```powershell
uv --cache-dir .uv-cache run ruff check tools\diagnostics tests\test_low_ms1_assessable_coverage_audit.py
uv --cache-dir .uv-cache run mypy --explicit-package-bases tools\diagnostics\low_ms1_assessable_coverage_audit.py tools\diagnostics\low_ms1_coverage_review_models.py tools\diagnostics\low_ms1_coverage_review_loaders.py tools\diagnostics\low_ms1_coverage_review_classifier.py tools\diagnostics\low_ms1_coverage_review_writers.py
```

If the split changes imports under `xic_extractor`, also run:

```powershell
uv --cache-dir .uv-cache run mypy xic_extractor
```

Real-data rerun is optional for this structure-only split if tests prove output
schema and classification equivalence. If any output formatting or queue logic
changes, rerun the 85RAW low-coverage diagnostic and compare row counts.

## Acceptance Criteria

- `low_ms1_assessable_coverage_audit.py` becomes a CLI facade and no longer
  owns loaders, classifiers, and writers in one file.
- The review interface can be tested directly.
- Output filenames and schemas are unchanged.
- Existing classification semantics are unchanged.
- No production code path is modified.
- No final matrix, targeted reliability, scoring, or benchmark semantics are
  changed.
- The PR is reviewable as a structure-only diagnostics PR.

## Risks

- Over-splitting into many shallow modules. Avoid creating modules that only
  wrap one function without improving locality.
- Accidentally changing queue eligibility while moving classifier code.
- Accidentally treating writer formatting as classification logic.
- Creating shared diagnostic helpers too early. Shared IO should wait until at
  least one split proves the duplication is concrete.

## Follow-up Candidates

After this split lands, evaluate:

1. shared diagnostic IO helpers,
2. `targeted_peak_reliability_audit.py` deepening,
3. `family_ms1_overlay_plot.py` split between evidence summary and plotting,
4. production-side `claim_registry.py` characterization and optimization.
