# Post-PR60 Codebase Cleanup Spec

**Date:** 2026-05-24
**Status:** Implementation checkpoint for the cleanup branch
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

## Baseline Snapshot

Structural scan from the cleanup worktree before the first split commits:

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

## Implementation Checkpoint

This branch has now implemented the first identity-coherence cleanup bundle:

- Workstream B: `identity_coherence/output.py` is a compatibility facade.
- Workstream C: `identity_coherence/controls.py` is a compatibility facade.
- Workstream H: the first two `tests/test_alignment_pipeline.py` slices moved
  into focused test files, and their shared batch/matrix fixtures now live in
  `tests/alignment_pipeline_helpers.py`.

The original plan recommended landing Workstream H in a dedicated test-only PR.
This branch intentionally keeps B/C/H in one cleanup bundle after review because
the H commits are test-only, already isolated after the production refactors,
and reduce review pressure on the remaining catch-all file. If PR packaging
requires stricter separation, split the two Workstream H commits into a
dedicated PR before merge.

Post-split line-count checkpoint, measured as total physical lines with
`Get-Content <path>).Count`:

| Lines | File | Status |
|---:|---|---|
| 89 | `xic_extractor/alignment/identity_coherence/controls.py` | Compatibility facade after Workstream C. |
| 37 | `xic_extractor/alignment/identity_coherence/output.py` | Compatibility facade after Workstream B. |
| 356 | `xic_extractor/alignment/identity_coherence/output_summary_model.py` | Summary model and Go/No-Go calculations. |
| 302 | `xic_extractor/alignment/identity_coherence/output_summary.py` | Markdown rendering only. |
| 1382 | `tests/test_alignment_pipeline.py` | Still large; reduced by first Workstream H slices and shared helper extraction. |
| 292 | `tests/test_alignment_identity_coherence_pipeline.py` | Focused identity-coherence pipeline diagnostic tests. |
| 256 | `tests/test_alignment_pipeline_timing.py` | Focused alignment timing/raw-source tests. |
| 282 | `tests/alignment_pipeline_helpers.py` | Shared alignment-pipeline batch/matrix fixtures for focused tests. |

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

## Reviewer Follow-Up Decisions

A parallel review raised five cleanup gaps. Handle them this way:

- Summary model/rendering split: accept. In Workstream B,
  `output_summary.py` must remain a Markdown layout renderer. Counts,
  threshold consistency checks, control pass fractions, decoy metrics, and
  Go/No-Go row shaping belong in `output_summary_model.py`.
- PPM helper duplication: accept as an inventory item, but not as a blind
  Workstream A quick-win. Current helpers differ by signed vs absolute error,
  denominator choice, `None`, and non-positive denominator handling. First
  classify existing semantics, then extract a small helper with characterization
  tests.
- Control model naming: keep `control_models.py` unless implementation proves
  ambiguity. `models.py` owns identity-evidence domain dataclasses/configs;
  `control_models.py` should own control manifest, control config, evaluation
  result, and record-like protocol contracts only. If this still reads poorly
  during Workstream C, prefer a more specific name such as
  `control_contracts.py` before moving behavior.
- Test catch-alls: accept. Large test-file decomposition deserves its own
  Workstream H and should not be hidden inside legacy diagnostics cleanup.
- Performance baseline: accept as a gate for performance-claimed changes, not
  as a blocker for move-only cleanup. `scripts/benchmark_parallel.py` already
  exists for serial/process extraction timing, but future performance PRs need
  a pinned 8RAW command and `docs/perf_baseline.md` with hardware/input/output
  context before claiming no regression.

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
- Before any `identity_coherence/output.py` split, update the boundary smoke
  test so identity-coherence domain modules are forbidden from importing the
  new `output_*` modules, writer modules, report/summary modules, CLI scripts,
  adapters, process backends, workbooks, or GUI code.
- Record any proven-dead public facade exports before deleting them. Deletion
  requires a grep/CodeGraph caller check plus at least one import-contract test.

Exit criteria:

- A reviewer can reproduce the inventory with PowerShell commands.
- No generated graph/cache output enters git.
- Cleanup target order is documented before behavior moves.

### Workstream B - Identity Coherence Output Split

Goal: split `identity_coherence/output.py` without changing frozen outputs.

Required first commit:

- Update the architecture boundary smoke test before moving output code.
- The boundary must scan the existing identity-coherence domain modules and any
  newly introduced output modules. Domain modules such as `candidate_matcher.py`,
  `cell_evidence.py`, `decision.py`, `models.py`, `request_builder.py`,
  `row_evaluator.py`, `rt_center.py`, `schema.py`, `seed_gate.py`, `shape.py`,
  `tags.py`, and `width.py` must not import `identity_coherence.output`,
  `identity_coherence.output_*`, CLI scripts, adapters, process backends,
  report/workbook renderers, or GUI code.

Candidate module split:

- `identity_coherence/output_formatting.py`
  - dependency-free TSV/Markdown formatting primitives,
  - `_format_tsv_value`-equivalent behavior,
  - counter-table Markdown formatting helpers only if they do not compute
    method or engineering verdicts.
- `identity_coherence/output_models.py`
  - `IdentityCoherenceOutputContext`
  - `IdentityCoherenceOutputPaths`
  - `IdentityCoherenceOutputRecord`
  - may import domain result models needed for runtime type-hint resolution,
  - must not import `output_validation.py`.
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
  - Markdown summary renderer only,
  - table/section layout and escaping.
- `identity_coherence/output_summary_model.py` or
  `identity_coherence/output_go_no_go.py`
  - engineering Go/No-Go row computation,
  - threshold/cost row shaping,
  - other summary model calculations that are not pure Markdown formatting.
- keep `identity_coherence/output.py` as a compatibility facade until imports
  settle.

Allowed dependency direction:

| Module | May import | Must not import |
|---|---|---|
| `output_formatting.py` | standard library only | any local output/domain module |
| `output_models.py` | primitive validators local to the file, standard library, domain result models needed by public dataclass annotations | `output_validation.py`, writers, summary |
| `output_validation.py` | `output_models.py`, domain result models | projection, writers, summary |
| `output_projection.py` | schema, tags, formatting, validation, domain result models | writers, summary |
| `output_summary_model.py` / `output_go_no_go.py` | models, validation, schema enums, formatting | writers, CLI, adapters |
| `output_summary.py` | models, validation, formatting, summary model | writers, CLI, adapters |
| `output_writers.py` | models, validation, projection, summary | adapters, CLI |
| `output.py` facade | all new output modules | new behavior |

`IdentityCoherenceOutputContext.__post_init__` should keep primitive
non-negative validation local to `output_models.py` or a dependency-free helper.
It must not depend on `output_validation.py`, otherwise `output_models ->
output_validation -> output_models` becomes a circular import risk.

Required tests:

- Existing output projection/writer tests must pass unchanged first.
- Add facade import tests so old public import paths remain valid.
- Add direct import tests for each new output module so the new modules are not
  only reachable through the facade.
- Add column-order parity tests at the new module boundaries.
- Update the architecture boundary test before moving behavior.
- Run `uv run pytest tests/alignment/identity_coherence/test_output_projection.py tests/alignment/identity_coherence/test_output_writer.py -q`.
- Also run:
  - `uv run pytest tests/alignment/identity_coherence/test_schema_contract.py tests/test_alignment_identity_coherence_adapter.py -q`
  - `uv run pytest --collect-only tests/alignment/identity_coherence -q`
  - `uv run ruff check <new-output-modules> <touched-tests>`

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
  - evaluation result dataclasses,
  - structural record-like protocols currently represented by
    `IdentityCoherenceOutputRecordLike`.
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

Allowed dependency direction:

| Module | May import | Must not import |
|---|---|---|
| `control_models.py` | schema/domain model types needed for protocols | `output*`, writers, summary, CLI, adapters |
| `control_manifest.py` | control models, schema, formatting primitives if needed | output modules, writers, summary, CLI |
| `positive_controls.py` | control models, schema, small domain models | output modules, writers, summary, CLI |
| `decoy_controls.py` | control models, seed gate, request builder, schema | output modules, writers, summary, CLI |
| `control_evaluation.py` | control manifest, positive controls, decoy controls, control models | output modules, writers, summary, CLI |
| `controls.py` facade | new control modules | new behavior |

Controls must keep depending on structural record-like protocols rather than
the concrete `IdentityCoherenceOutputRecord`. This preserves the current
direction where controls can validate records without importing the output
layer.

Required tests:

- Existing `test_controls_manifest.py` and `test_controls_evaluation.py` pass
  unchanged before refactoring assertions.
- Add facade import tests for stable control API names.
- Add no-import-backwards tests for every control module. They must reject
  imports of `identity_coherence.output`, `identity_coherence.output_models`,
  `identity_coherence.output_projection`, `identity_coherence.output_validation`,
  `identity_coherence.output_writers`, `identity_coherence.output_summary`,
  `identity_coherence.output_summary_model`, and
  `identity_coherence.output_go_no_go`.
- Update the existing boundary test module list so newly introduced
  `control_*` files are covered.

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

Migration rule:

- Do not keep expanding `tests/test_validate_identity_coherence_8raw.py`.
- New validator module tests should live under
  `tests/alignment/identity_coherence_validation/`, split by module:
  `test_bundle.py`, `test_compare.py`, `test_controls_summary.py`,
  `test_decoy_manifest_proposal.py`, `test_acceptance.py`, `test_writer.py`,
  and `test_cli_contract.py`.
- Shared test builders should live in
  `tests/alignment/identity_coherence_validation/fixtures.py` or local
  per-file helpers, not in broad `tests/conftest.py`.
- The old `tests/test_validate_identity_coherence_8raw.py` should either keep
  only CLI wrapper / legacy import compatibility / exit-code contract tests, or
  be explicitly split as part of the validator PR.
- During the first split, either keep script-level compatibility re-exports for
  current helper names, or migrate tests to the new package first with explicit
  script entry-point import-contract tests.
- Do not rewrite fixture behavior in the same PR unless the change is strictly
  import-path migration.

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

### Workstream H - Catch-All Test Decomposition

Goal: make future behavior changes easier to localize without changing
production behavior.

First target:

- `tests/test_alignment_pipeline.py`
  - Split into focused files by behavior surface, for example import/boundary
    smoke, owner/backfill integration, primary matrix contracts, and
    process/pipeline orchestration.
  - Move only tests and local fixtures. Do not change production code to make
    the split easier.
  - Preserve existing test names where feasible, or keep searchable behavior
    phrases in the new names.

Required checks:

- Run the moved test files directly.
- Run `uv run pytest --collect-only tests -q` or a narrower collect-only command
  that proves the moved tests still collect once.
- If any shared helper is introduced, keep it local to the new test package
  unless at least two unrelated test areas need it.

Non-goals:

- no assertion broadening,
- no fixture semantic changes,
- no production behavior changes,
- no unrelated large-test cleanup in the same PR.

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

## Original Recommended First PR

The initial planning recommendation was for the first cleanup PR to include the
Workstream A boundary guard plus Workstream B:

**Title:** `refactor: split identity coherence output surface`

Why first:

- It is diagnostic-only.
- It has direct tests.
- It reduces a 914-line file with multiple clear responsibilities.
- It improves reviewability before any further identity-coherence features.
- It establishes the new `output_*` boundary guard before those modules exist
  widely enough to leak into domain code.

Implementation order:

1. Add/update boundary and import-contract tests for the future `output_*`
   module family.
2. Move output models and primitive formatting helpers.
3. Move projection functions.
4. Move validation functions.
5. Move TSV writers and bundle writer.
6. Move summary model / Go-No-Go row shaping.
7. Move Markdown rendering.
8. Reduce `identity_coherence/output.py` to a compatibility facade.
9. Only after tests pass, consider removing unused private helpers left behind.

Stop conditions:

- any frozen TSV header, path, or summary section diff appears,
- schema constants need to change,
- acceptance, decision, promotion, seed-gate, control, or 8RAW policy logic
  needs to change,
- RAW/XIC retrieval, Backfill, final matrix, owner, clustering, or
  primary-consolidation code needs to be touched,
- facade imports cannot be preserved without behavior changes,
- a domain module needs to import an `output_*` module.

Definition of done:

- `identity_coherence/output.py` becomes a compatibility facade.
- New focused output modules own models, projection, validation, writers, and
  summary/report-model responsibilities separately.
- Architecture boundary smoke tests cover `output_*` forbidden imports.
- Direct new-module imports and facade imports are both tested.
- No frozen TSV, Markdown section, CLI, or schema behavior changes.
- Narrow tests pass:
  - `uv run pytest tests/alignment/identity_coherence/test_output_projection.py tests/alignment/identity_coherence/test_output_writer.py -q`
- Contract tests pass:
  - `uv run pytest tests/alignment/identity_coherence/test_schema_contract.py tests/test_alignment_identity_coherence_adapter.py -q`
- Collect/lint smoke passes:
  - `uv run pytest --collect-only tests/alignment/identity_coherence -q`
  - `uv run ruff check <new-output-modules> <touched-tests>`
- Broader identity-coherence tests pass before merge:
  - `uv run pytest tests/alignment/identity_coherence -q`

## Follow-Up PR Order

1. Decide PR packaging for this branch: keep the reviewed B/C/H cleanup bundle,
   or split the two Workstream H commits into a dedicated test-only PR.
2. Split 8RAW validation CLI internals.
3. Review identity-coherence adapter boundary.
4. Inventory instrument-QC productization modules with a new focused spec.
5. Add or refresh a documented 8RAW performance baseline before any
   performance-claimed or process-backend behavior PR.
6. Classify and extract ppm helper semantics only after characterization tests
   prove signed/absolute and denominator behavior stays stable.
7. Continue legacy diagnostic rendering splits.
8. Only then revisit alignment domain-heavy modules with characterization
    tests.

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
