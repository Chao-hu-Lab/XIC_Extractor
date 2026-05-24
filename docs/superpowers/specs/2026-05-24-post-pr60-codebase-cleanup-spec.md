# Post-PR60 Codebase Cleanup Spec

**Date:** 2026-05-24  
**Status:** Planning spec for the next cleanup branch  
**Branch:** `codex/codebase-cleanup-inventory`  
**Base:** `ef05335` (`Merge pull request #60 from Chao-hu-Lab/codex/untargeted-backfill-logic-reset`)  

---

## Purpose

PR #60 landed a large identity-coherence diagnostic surface plus instrument-QC
work that is useful, tested, and intentionally diagnostic-only. The next branch
should not add another scientific feature. It should reduce responsibility
drift, remove obvious dead surfaces where proven safe, and leave the codebase
easier to reason about before the next algorithmic pass.

This cleanup is not a license to change identity decisions, Backfill behavior,
matrix output, peak scoring, neutral-loss matching, or RAW/XIC retrieval
semantics.

## Hard Boundaries

Do not change these in cleanup PRs:

- final matrix inclusion semantics,
- owner, clustering, Backfill, or primary-consolidation scientific rules,
- identity-coherence frozen TSV schemas,
- workbook sheet names, ordering, hidden states, or columns,
- CLI flags and artifact names under `scripts/`,
- 8RAW / 85RAW acceptance criteria,
- actual RAW/XIC extraction algorithms or batching semantics.

Cleanup may move code, split files, add characterization tests, tighten import
boundaries, delete proven-dead compatibility wrappers, and update docs. Any
behavior change needs its own spec.

## Current Snapshot

Structural scan from the cleanup worktree:

- CodeGraph CLI initialized locally: 503 files, 9,969 nodes, 25,878 edges.
- `xic_extractor/`, `tools/`, and `scripts/` now contain several files over
  the repo-local 500/800-line red-flag thresholds.
- The largest post-PR60 hotspots are now split across three areas:
  identity coherence, instrument QC, and legacy diagnostics.

Largest production / tool modules:

| Lines | File | First cleanup interpretation |
|---:|---|---|
| 1078 | `scripts/validate_identity_coherence_8raw.py` | Public CLI wrapper plus validation logic; split only behind same CLI. |
| 962 | `xic_extractor/peak_scoring.py` | Existing decomposition target; do not mix with identity cleanup. |
| 948 | `xic_extractor/alignment/identity_coherence/controls.py` | New high-value target: manifest parsing, positive controls, decoys, evaluation rows. |
| 936 | `xic_extractor/instrument_qc/calibration_product_preview.py` | Productization surface; likely mixes loaders, models, preview decision logic, and writers. |
| 916 | `tools/diagnostics/alignment_decision_report_rendering.py` | Legacy diagnostic rendering surface; prior specs already identify report splitting. |
| 914 | `xic_extractor/alignment/identity_coherence/output.py` | New high-value target: projection, validation, TSV writers, Markdown summary. |
| 908 | `tools/diagnostics/family_ms1_overlay_plot.py` | Diagnostic plotting; lower production risk but large rendering/data mix. |
| 898 | `xic_extractor/alignment/process_backend.py` | Process mechanics plus alignment/trace payloads; split only with spawn/pickle smoke tests. |
| 872 | `tools/diagnostics/analyze_rt_normalization_anchors.py` | Diagnostic CLI; candidate for loader/model/writer split. |
| 848 | `scripts/local_minimum_param_sweep.py` | Validation/development script; not part of PR60 cleanup unless it blocks tooling. |

Identity-coherence internal line pressure:

| Lines | File | Notes |
|---:|---|---|
| 948 | `identity_coherence/controls.py` | Strong tests exist; split is feasible. |
| 914 | `identity_coherence/output.py` | Strong writer/projection tests exist; split is feasible. |
| 426 | `identity_coherence/models.py` | Near threshold but still mostly dataclasses/configs; avoid premature split. |
| 410 | `identity_coherence/cell_evidence.py` | Acceptable for now; maintain focused domain ownership. |
| 374 | `identity_coherence/shape.py` | Acceptable; keep with shape domain logic. |

Instrument-QC pressure:

| Lines | File | Notes |
|---:|---|---|
| 936 | `instrument_qc/calibration_product_preview.py` | Highest new instrument-QC cleanup target. |
| 635 | `instrument_qc/workbook.py` | Rendering-only boundary should be checked. |
| 560 | `instrument_qc/pipeline.py` | Orchestration; should not absorb preview/writer logic. |
| 541 | `instrument_qc/calibration_rt_model.py` | Domain-heavy; add characterization before moving. |

Test pressure:

| Lines | File | Notes |
|---:|---|---|
| 1948 | `tests/test_alignment_pipeline.py` | Catch-all test file; future additions should move to focused tests. |
| 1646 | `tests/test_extractor.py` | Existing broad targeted extraction suite. |
| 1265 | `tests/test_validate_identity_coherence_8raw.py` | Public validation CLI tests; split only with stable helper fixtures. |
| 1048 | `tests/test_peak_scoring.py` | Existing scoring decomposition target. |

## Existing Contracts To Preserve

This spec extends, not replaces:

- `docs/superpowers/specs/2026-05-16-module-responsibility-inventory.md`
- `docs/superpowers/specs/2026-05-16-alignment-module-responsibility-contract.md`
- `docs/superpowers/specs/2026-05-24-identity-coherence-post-v04-85raw-roadmap-spec.md`
- `AGENTS.md` ownership map and dependency rules.

The old contract already says not to start with `primary_consolidation.py`,
`clustering.py`, or `ownership.py`. That still stands. PR #60 adds a new,
safer cleanup front: identity-coherence output/control surfaces have much better
localized tests and are diagnostic-only.

## Cleanup Workstreams

### Workstream A - Tooling And Inventory Baseline

Goal: make future cleanup reviewable before moving code.

Tasks:

- Keep `.codegraph/` and `graphify-out/` ignored; do not commit generated graph
  indexes.
- Add a small script or documented command set for line-count and dependency
  inventory if repeated scans remain useful.
- Add an architecture boundary smoke test for the newest diagnostic surfaces:
  domain modules must not import report/workbook/CLI/process adapter layers.
- Record any proven-dead public facade exports before deleting them. Deletion
  requires a grep/CodeGraph caller check plus at least one import-contract test.

Exit criteria:

- A reviewer can reproduce the inventory with PowerShell commands.
- No generated graph/cache output enters git.
- Cleanup target order is documented before behavior moves.

### Workstream B - Identity Coherence Output Split

Goal: split `identity_coherence/output.py` without changing frozen outputs.

Candidate module split:

- `identity_coherence/output_models.py`
  - `IdentityCoherenceOutputContext`
  - `IdentityCoherenceOutputPaths`
  - `IdentityCoherenceOutputRecord`
- `identity_coherence/output_projection.py`
  - `project_request_row`
  - `project_cell_evidence_row`
  - `project_decision_row`
  - `project_control_row`
- `identity_coherence/output_validation.py`
  - record join-key checks
  - seed sample exclusion
  - forbidden evidence guards
- `identity_coherence/output_writers.py`
  - TSV writer functions
  - bundle writer
- `identity_coherence/output_summary.py`
  - Markdown summary renderer and Go/No-Go rows
- keep `identity_coherence/output.py` as a compatibility facade until imports
  settle.

Required tests:

- Existing output projection/writer tests must pass unchanged first.
- Add facade import tests so old public import paths remain valid.
- Add column-order parity tests at the new module boundaries.
- Run `uv run pytest tests/alignment/identity_coherence/test_output_projection.py tests/alignment/identity_coherence/test_output_writer.py -q`.

Non-goals:

- no schema column changes,
- no summary section behavior changes,
- no changes to acceptance logic.

### Workstream C - Identity Coherence Controls Split

Goal: split `identity_coherence/controls.py` into manifest IO, positive-control
evaluation, decoy evaluation, and aggregate result shaping.

Candidate module split:

- `identity_coherence/control_models.py`
  - control manifest entries,
  - control configs,
  - evaluation result dataclasses.
- `identity_coherence/control_manifest.py`
  - TSV/YAML rejection,
  - row parsing,
  - extra-field rejection.
- `identity_coherence/positive_controls.py`
  - positive-control mapping checks.
- `identity_coherence/decoy_controls.py`
  - RT-shift, m/z-shift, tag-shuffle decoy evaluation.
- `identity_coherence/control_evaluation.py`
  - aggregate `evaluate_identity_controls`.
- keep `identity_coherence/controls.py` as compatibility facade until imports
  settle.

Required tests:

- Existing `test_controls_manifest.py` and `test_controls_evaluation.py` pass
  unchanged before refactoring assertions.
- Add facade import tests for stable control API names.
- Add no-import-backwards test: control evaluation must not import output
  writer/summary modules.

Non-goals:

- no control manifest schema changes,
- no decoy policy changes,
- no positive-control promotion semantics.

### Workstream D - Identity Coherence CLI Validator Split

Goal: keep `scripts/validate_identity_coherence_8raw.py` as public CLI while
moving validation internals behind focused modules.

Candidate target package:

- `xic_extractor/alignment/identity_coherence_validation/`
  - `bundle.py`: frozen output bundle discovery and reads,
  - `compare.py`: serial/process parity checks,
  - `controls_summary.py`: positive/decoy method rows,
  - `decoy_manifest_proposal.py`: proposal generation,
  - `acceptance.py`: V0.4 acceptance verdict,
  - `writer.py`: validation summary TSV/Markdown outputs.

`scripts/validate_identity_coherence_8raw.py` should become an argparse
wrapper around this package.

Required tests:

- Existing `tests/test_validate_identity_coherence_8raw.py` must pass.
- Add import tests for the script entry point.
- Add contract tests that output filenames and exit-code semantics are
  unchanged.

Non-goals:

- no new 8RAW acceptance threshold,
- no automatic sorting workaround for parity failures,
- no RAW reads in the validator.

### Workstream E - Identity Coherence Adapter Boundary

Goal: review `identity_coherence_adapter.py` after PR #60 and decide whether it
should remain one orchestration adapter or split by source mapping, trace
retrieval, row evaluation, and controls.

Potential split only after Workstreams B/C stabilize:

- `identity_coherence_source_mapping.py`
- `identity_coherence_trace_retrieval.py`
- `identity_coherence_record_builder.py`

Required tests:

- `tests/test_alignment_identity_coherence_adapter.py`
- `tests/test_alignment_process_backend.py`
- no-RAW process spawn/pickle smoke test for process payloads.

Non-goals:

- no batching changes,
- no process-mode behavior changes,
- no RAW/XIC retrieval algorithm changes.

### Workstream F - Instrument-QC Responsibility Pass

Goal: inventory and split the newest instrument-QC productization surfaces only
where tests make behavior safe.

Recommended order:

1. `instrument_qc/calibration_product_preview.py`
   - separate loaders, preview domain model, preview decision logic, and writer
     orchestration.
2. `instrument_qc/workbook.py`
   - verify it is rendering-only; move any decision logic out.
3. `instrument_qc/pipeline.py`
   - keep orchestration only; move report/product-specific helpers out.
4. `instrument_qc/calibration_rt_model.py`
   - do not split until characterization tests pin model fitting output.

Required tests:

- `tests/test_instrument_qc_matrix_calibration_preview.py`
- `tests/test_instrument_qc_matrix_calibration_preview_cli.py`
- relevant writer/workbook tests.

Non-goals:

- no calibration thresholds,
- no SDolek target list changes,
- no HCD/CID evidence semantics changes.

### Workstream G - Legacy Diagnostics And Test Suite Hygiene

Goal: continue the 2026-05-16 diagnostic decomposition, but avoid mixing it with
identity-coherence internals.

Targets already partly improved:

- `alignment_decision_report.py` appears to have split into model/rendering
  pieces, but rendering is still 916 lines.
- targeted reliability, low-MS1 coverage, and targeted ISTD benchmark now have
  more focused modules but still carry large tests and report renderers.

Actions:

- Prefer rendering/layout splits before domain rule changes.
- Stop adding new cases to `tests/test_alignment_pipeline.py` unless the
  behavior truly spans the whole pipeline.
- When splitting a large test file, move shared factories into local fixture
  helpers rather than centralizing everything in `tests/conftest.py`.

## Do Not Start Here

These are important but should not be the first cleanup PR after PR #60:

- `xic_extractor/alignment/ownership.py`
- `xic_extractor/alignment/clustering.py`
- `xic_extractor/alignment/primary_consolidation.py`
- `xic_extractor/peak_scoring.py`
- `xic_extractor/signal_processing.py`
- RAW reader, XIC extraction, or process backend behavior.

Touching them first creates scientific regression risk before the new
diagnostic/reporting surfaces have settled.

## Recommended First PR

First cleanup PR should be Workstream B only:

**Title:** `refactor: split identity coherence output surface`

Why first:

- It is diagnostic-only.
- It has direct tests.
- It reduces a 914-line file with multiple clear responsibilities.
- It improves reviewability before any further identity-coherence features.

Definition of done:

- `identity_coherence/output.py` becomes a compatibility facade.
- New focused output modules own models, projection, validation, writers, and
  summary separately.
- No frozen TSV, Markdown section, CLI, or schema behavior changes.
- Narrow tests pass:
  - `uv run pytest tests/alignment/identity_coherence/test_output_projection.py tests/alignment/identity_coherence/test_output_writer.py -q`
- Broader identity-coherence tests pass before merge:
  - `uv run pytest tests/alignment/identity_coherence -q`

## Follow-Up PR Order

1. Split identity-coherence output.
2. Split identity-coherence controls.
3. Split 8RAW validation CLI internals.
4. Review identity-coherence adapter boundary.
5. Inventory instrument-QC productization modules with a new focused spec.
6. Continue legacy diagnostic rendering splits.
7. Only then revisit alignment domain-heavy modules with characterization tests.

## Review Checklist For Cleanup PRs

- Is this move-only? If not, is the behavior change explicitly scoped?
- Are public imports and CLI commands preserved?
- Are frozen TSV/Markdown/JSON/workbook contracts unchanged?
- Did the PR avoid RAW/XIC retrieval semantics?
- Did the PR avoid matrix identity and Backfill decisions?
- Did domain modules avoid importing writers, reports, CLI scripts, workbooks,
  GUI, or process backends?
- Did tests move toward focused ownership instead of expanding catch-all files?
- Is there at least one import/facade compatibility test when public paths move?
- If a large file remains large, does it still have one reason to change?

