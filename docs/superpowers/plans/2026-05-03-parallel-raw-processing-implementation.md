# Parallel RAW Processing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Add opt-in per-RAW process parallelism to reduce real-data extraction time while preserving serial default behavior and workbook-equivalent results.
**Architecture:** Keep `xic_extractor.extractor.run()` as the public entry point, split execution into serial and process backends, parallelize Stage 1 ISTD pre-pass and Stage 2 per-file extraction by raw file, and keep output writing in the main process.
**Tech Stack:** Python, pytest, uv, pandas/openpyxl, Windows multiprocessing spawn, PyInstaller-compatible entry points.
**Spec:** `docs/superpowers/specs/2026-05-03-parallel-raw-processing-spec.md`

---

## Execution Rules

1. Use TDD for code changes: red test, confirm failure, implement, confirm green.
2. Keep commits small and task-scoped.
3. Preserve `parallel_mode=serial` as default until a later explicit product decision changes it.
4. Do not change peak picking, NL confirmation, scoring, integration, or workbook schema.
5. Use 8 raw validation subset for daily real-data checks:

   `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation`

6. Full 85 raw validation is a final convergence gate, not the default every-PR check.
7. If subagents are used, split by independent write areas and keep main agent responsible for integration and final verification.

---

## Phase 0 — Baseline Orientation

**Purpose:** Confirm current branch state, current tests, and exact extraction entry points before code changes.

### Task 0.1 — Capture current execution surface

Read:

- `xic_extractor/extractor.py`
- `scripts/run_extraction.py`
- `gui/main.py`
- `gui/sections/settings_section.py`
- existing config/settings tests
- existing output workbook tests

Document in PR notes:

- where raw paths are sorted
- where ISTD pre-pass happens
- where scoring context is assembled
- where per-file extraction result rows are collected
- where workbook writing happens

### Task 0.2 — Baseline tests

Run:

```powershell
uv run pytest --tb=short -q
```

If existing unrelated failures appear, stop and report before implementation.

---

## Phase 1 — Settings, CLI, GUI Contract

**Purpose:** Add the public configuration surface without changing execution behavior.

### Task 1.1 — Add settings schema fields

**Red test**

Add tests that fail because the fields do not exist yet:

- default config has `parallel_mode == "serial"`
- default config has `parallel_workers == 1`
- settings parser accepts `parallel_mode=process`
- settings parser rejects unknown `parallel_mode`
- settings parser rejects `parallel_workers < 1`

Likely files:

- `tests/test_config.py`
- or existing settings schema test file if more appropriate

Run:

```powershell
uv run pytest tests/test_config.py -v
```

**Implementation**

Update config/settings parsing to include:

- `parallel_mode: str = "serial"`
- `parallel_workers: int = 1`

Validation:

- allowed `parallel_mode`: `serial`, `process`
- `parallel_workers >= 1`

Files that must be updated:

- `xic_extractor/config.py`
- `xic_extractor/settings_schema.py`
- `config/settings.example.csv`
- tests covering canonical defaults and config round-trip

**Green test**

```powershell
uv run pytest tests/test_config.py -v
```

**Commit**

```powershell
git add <changed files>
git commit -m "feat(perf): add parallel execution settings"
```

### Task 1.2 — Add CLI overrides

**Red test**

Add CLI parser tests confirming:

- `--parallel-mode process` overrides settings
- `--parallel-workers 4` overrides settings
- invalid mode exits with a clear error

Likely file:

- `tests/test_run_extraction.py`

Run:

```powershell
uv run pytest tests/test_run_extraction.py -v
```

**Implementation**

Update `scripts/run_extraction.py` to accept:

```powershell
--parallel-mode serial|process
--parallel-workers <int>
```

Apply overrides before calling `run()`.

**Green test**

```powershell
uv run pytest tests/test_run_extraction.py -v
```

**Commit**

```powershell
git add <changed files>
git commit -m "feat(perf): add parallel CLI overrides"
```

### Task 1.3 — Add GUI Advanced fields

**Red test**

Add GUI settings tests confirming:

- `parallel_mode` appears in Advanced settings
- `parallel_workers` appears in Advanced settings
- default GUI values match config defaults
- saved values round-trip through settings collection

Likely files:

- `tests/test_settings_section.py`
- or the current GUI settings section test file

Run:

```powershell
uv run pytest tests/test_settings_section.py -v
```

**Implementation**

Update `gui/sections/settings_section.py` to include both fields in Advanced settings.

**Green test**

```powershell
uv run pytest tests/test_settings_section.py -v
```

**Commit**

```powershell
git add <changed files>
git commit -m "feat(gui): expose parallel execution settings"
```

---

## Phase 2 — Workbook Compare and Timing Tooling

**Purpose:** Create reusable verification tools before adding process execution.

### Task 2.1 — Add workbook compare utility

**Red test**

Add tests for a workbook compare helper:

- identical workbooks pass
- changed analytical value fails
- `generated_at` difference is ignored
- sheet order differences do not matter if sheet names and cell content match

Likely files:

- `tests/test_workbook_compare.py`
- `scripts/compare_workbooks.py`

Run:

```powershell
uv run pytest tests/test_workbook_compare.py -v
```

**Implementation**

Create a script/helper that compares:

- `XIC Results`
- `Summary`
- `Targets`
- `Diagnostics`
- `Run Metadata`
- `Score Breakdown` when present

Normalize:

- `generated_at`
- elapsed/runtime metadata if present
- absolute output paths if present

Numeric tolerance should be small and explicit.

**Green test**

```powershell
uv run pytest tests/test_workbook_compare.py -v
```

**Commit**

```powershell
git add <changed files>
git commit -m "test(perf): add workbook comparison helper"
```

### Task 2.2 — Add benchmark wrapper script

**Red test**

Add tests confirming the wrapper builds the expected command matrix for:

- serial workers=1
- process workers=2
- process workers=4
- one isolated output directory or explicit workbook path per run
- workbook compare receives exact returned workbook paths, not glob guesses

Do not require real `.raw` files in unit tests.

Likely file:

- `tests/test_benchmark_parallel.py`
- `scripts/benchmark_parallel.py`

Run:

```powershell
uv run pytest tests/test_benchmark_parallel.py -v
```

**Implementation**

Add a script that can run:

```powershell
uv run python scripts/benchmark_parallel.py `
  --base-dir . `
  --data-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
  --workers 2,4 `
  --output-dir output\parallel_benchmark
```

The script must isolate outputs by mode/worker count, for example:

```text
output\parallel_benchmark\
  serial_w1\
  process_w2\
  process_w4\
```

Do not rely on timestamped workbook globbing. Use explicit output paths or the exact paths returned from each run when comparing workbooks.

The script should record:

- mode
- workers
- raw count
- elapsed seconds
- output workbook path
- compare result versus serial baseline

**Green test**

```powershell
uv run pytest tests/test_benchmark_parallel.py -v
```

**Commit**

```powershell
git add <changed files>
git commit -m "test(perf): add parallel benchmark wrapper"
```

---

## Phase 3 — Serial Extraction Boundary Refactor

**Purpose:** Create a shared per-file extraction primitive without changing behavior.

### Task 3.1 — Extract serial backend wrapper

**Red test**

Add or tighten tests that prove `run()` still calls the serial backend by default and output row ordering remains stable.

Likely files:

- `tests/test_extractor_run.py`
- existing output tests

Run:

```powershell
uv run pytest tests/test_extractor_run.py -v
```

**Implementation**

Refactor `extractor.run()` internally:

- keep public signature unchanged
- introduce `_run_serial(...)` or equivalent private helper
- no behavior change
- no output schema change

**Green test**

```powershell
uv run pytest tests/test_extractor_run.py -v
uv run pytest --tb=short -q
```

**Commit**

```powershell
git add <changed files>
git commit -m "refactor(perf): isolate serial extraction backend"
```

### Task 3.2 — Extract per-file result primitive

**Red test**

Add tests for a serial per-file primitive that returns a structured result object containing:

- raw index
- sample name
- wide rows / long rows
- diagnostics
- score breakdown rows
- any per-file errors

Run:

```powershell
uv run pytest tests/test_extractor_run.py -v
```

**Implementation**

Move the existing per-file extraction body into a function that can be called by both serial and process backends.

Rules:

- output writer remains in main process
- result object is pickleable
- raw handle is opened and closed inside the function

**Green test**

```powershell
uv run pytest tests/test_extractor_run.py -v
uv run pytest --tb=short -q
```

**Commit**

```powershell
git add <changed files>
git commit -m "refactor(perf): extract per-file extraction result"
```

---

## Phase 4 — Process Backend

**Purpose:** Add opt-in process execution with deterministic aggregation.

### Task 4.1 — Add process worker dataclasses and fake-runner unit tests

**Red test**

Add tests for:

- worker job/result objects are pickleable
- aggregation sorts by `raw_index`
- worker error result is surfaced clearly
- job payload does not contain callables, closures, raw handles, pythonnet objects, or open file handles
- a tiny actual `ProcessPoolExecutor` spawn smoke can run a top-level worker with a small pickleable job on Windows

Use fake workers or an injectable runner. Do not require Thermo DLL in these unit tests.

Likely files:

- `tests/test_parallel_execution.py`
- `xic_extractor/execution.py` or `xic_extractor/extraction/parallel.py`

Run:

```powershell
uv run pytest tests/test_parallel_execution.py -v
```

**Implementation**

Create a parallel execution module with top-level importable functions and dataclasses.

Add a pure no-RAW spawn smoke test before any real data validation. This test should fail if worker functions are not importable under Windows `spawn` or if job payloads are not pickleable.

**Green test**

```powershell
uv run pytest tests/test_parallel_execution.py -v
```

**Commit**

```powershell
git add <changed files>
git commit -m "feat(perf): add parallel execution primitives"
```

### Task 4.2 — Implement parallel ISTD pre-pass

**Red test**

Add tests confirming process mode Stage 1:

- submits one pre-pass job per raw file
- aggregates ISTD RTs independent of completion order
- reports worker failures with the raw file name

Run:

```powershell
uv run pytest tests/test_parallel_execution.py -v
```

**Implementation**

Add process-backed ISTD pre-pass for `parallel_mode=process`.

Serial mode must keep the existing pre-pass path or call the same primitive serially.

**Green test**

```powershell
uv run pytest tests/test_parallel_execution.py -v
uv run pytest --tb=short -q
```

**Commit**

```powershell
git add <changed files>
git commit -m "feat(perf): parallelize ISTD pre-pass"
```

### Task 4.3 — Implement parallel full extraction

**Red test**

Add tests confirming process mode Stage 2:

- submits one extraction job per raw file
- sorts results by original raw order
- preserves diagnostics and score breakdown rows
- leaves output writing in main process
- process worker exception fails loudly
- sends only pickleable scoring inputs to workers
- rebuilds `build_scoring_context_factory(...)` inside the worker process
- does not pass the nested `scoring_context_factory` closure across process boundaries

Run:

```powershell
uv run pytest tests/test_parallel_execution.py -v
```

**Implementation**

Wire `parallel_mode=process` into `extractor.run()`:

- Stage 1: process ISTD pre-pass
- main process: build pickleable scoring inputs
- Stage 2: process full extraction
- worker process: rebuild scoring context factory from pickleable scoring inputs
- main process: aggregate and write output

**Green test**

```powershell
uv run pytest tests/test_parallel_execution.py -v
uv run pytest --tb=short -q
```

**Commit**

```powershell
git add <changed files>
git commit -m "feat(perf): add process raw execution backend"
```

### Task 4.4 — Preserve progress and cancellation contracts

**Red test**

Add tests confirming process mode:

- calls `progress_callback(current, total, filename)` once per completed Stage 2 raw file
- uses `total == len(raw_paths)`
- polls `should_stop()` before scheduling work and while collecting futures
- cancels pending futures when `should_stop()` becomes true
- does not write workbook output for cancelled GUI runs
- does not emit GUI success summary after cancellation

Likely files:

- `tests/test_parallel_progress_cancellation.py`
- `tests/test_pipeline_worker.py`

Run:

```powershell
uv run pytest tests/test_parallel_progress_cancellation.py -v
uv run pytest tests/test_pipeline_worker.py -v
```

**Implementation**

Add process collector behavior that preserves the existing serial `extractor.run()` contract:

- Stage 1 may report coarse pre-pass progress or no progress, but must not block cancellation polling.
- Stage 2 emits one progress event per completed raw file.
- Pending futures are cancelled on stop.
- Already-running raw jobs may finish, but no new jobs are scheduled after stop.
- `PipelineWorker` keeps the existing post-run `isInterruptionRequested()` guard before writing Excel.

**Green test**

```powershell
uv run pytest tests/test_parallel_progress_cancellation.py -v
uv run pytest tests/test_pipeline_worker.py -v
uv run pytest --tb=short -q
```

**Commit**

```powershell
git add <changed files>
git commit -m "fix(perf): preserve process progress and cancellation"
```

### Task 4.5 — Add Windows frozen-entry support

**Red test**

Add tests or source-level smoke checks confirming supported entry points call `multiprocessing.freeze_support()` early:

- `scripts/run_extraction.py`
- GUI entry point

Run:

```powershell
uv run pytest tests/test_multiprocessing_entrypoints.py -v
```

**Implementation**

Add `multiprocessing.freeze_support()` in CLI and GUI entry points.

**Green test**

```powershell
uv run pytest tests/test_multiprocessing_entrypoints.py -v
uv run pytest --tb=short -q
```

**Commit**

```powershell
git add <changed files>
git commit -m "fix(perf): support frozen multiprocessing entrypoints"
```

---

## Phase 5 — Real-Data Validation

**Purpose:** Prove process mode is equivalent and measure actual speed.

### Task 5.1 — Run validation subset benchmark

Run against:

```powershell
C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation
```

Suggested command:

```powershell
uv run python scripts/benchmark_parallel.py `
  --base-dir . `
  --data-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
  --workers 2,4 `
  --output-dir output\parallel_benchmark
```

Acceptance:

- serial completes
- process workers=2 completes
- process workers=4 completes
- workbook compare passes for process outputs versus serial baseline
- timing table is recorded in PR description

If process output differs from serial:

1. Stop.
2. Use workbook compare diff to identify sheet/cell.
3. Determine whether difference is ordering, metadata, numeric tolerance, or analytical drift.
4. Do not relax compare tolerance until root cause is understood.

### Task 5.2 — Run targeted test suite

Run:

```powershell
uv run pytest tests/test_config.py -v
uv run pytest tests/test_run_extraction.py -v
uv run pytest tests/test_settings_section.py -v
uv run pytest tests/test_workbook_compare.py -v
uv run pytest tests/test_benchmark_parallel.py -v
uv run pytest tests/test_parallel_execution.py -v
uv run pytest tests/test_parallel_progress_cancellation.py -v
uv run pytest tests/test_multiprocessing_entrypoints.py -v
uv run pytest --tb=short -q
```

### Task 5.3 — Final full-dataset gate

Near PR convergence, run full tissue dataset once unless user explicitly defers it.

Record:

- raw count
- serial elapsed if rerun
- process elapsed
- worker count
- workbook compare result
- any reason full dataset was skipped

**Commit validation docs if benchmark report is committed**

Only commit benchmark artifacts if they are small, textual, and useful for future reviewers. Do not commit generated workbooks or large outputs.

```powershell
git add <small benchmark report files only>
git commit -m "docs(perf): record parallel validation results"
```

---

## Suggested Subagent Split

Use subagents only after Phase 0 confirms the current code surface.

Independent candidates:

- **Worker A:** settings / CLI / GUI tests and implementation (`Phase 1`)
- **Worker B:** workbook compare and benchmark tooling (`Phase 2`)

Do not parallelize these until write scopes are explicit:

- extractor backend refactor
- process backend integration
- output aggregation

Main agent must integrate all worker changes and run final verification.

---

## PR Description Requirements

Include:

```markdown
## What
- Adds opt-in per-RAW process parallelism.
- Keeps serial mode as default.
- Adds validation tooling for workbook equivalence and timing.

## Why
- Full tissue workflow is around 14 minutes for 85 RAW files.
- Daily method validation should use the 8 RAW validation subset.

## Validation
| Mode | Workers | RAW count | Elapsed | Speedup | Workbook compare |
|---|---:|---:|---:|---:|---|
| serial | 1 | 8 | ... | 1.00x | baseline |
| process | 2 | 8 | ... | ... | pass/fail |
| process | 4 | 8 | ... | ... | pass/fail |

## Speed Decision
- Equivalent but slower: merge only as experimental opt-in, keep serial default.
- Faster on validation subset only: merge opt-in, do not change default.
- Candidate for default: validation subset and full dataset both show stable speedup with workbook-equivalent output.

## Full Dataset
- Run / deferred with reason:

## Out of Scope
- Peak picking changes
- NL/scoring changes
- Making process mode default
```

---

## GStack Review Summary

### Design Plan Review

**Score：9 / 10**

Strengths:

- The plan preserves user-facing behavior by keeping serial default.
- The validation subset is elevated to a first-class workflow, which directly addresses iteration speed.
- Workbook compare is required before trusting process output.

Changes applied after review:

- Added explicit `freeze_support()` task for Windows/PyInstaller.
- Added warning against using real Thermo DLL as the only unit-test path.
- Added final full-dataset gate but kept it out of daily validation.

### Engineering Plan Review

**Score：9 / 10**

Key engineering constraints now covered:

- Worker functions must be top-level importable and pickleable.
- Raw handles never cross process boundaries.
- Output writing stays single-process.
- Result ordering is based on `raw_index`, not completion order.
- Worker errors fail loudly and identify the raw file.
- Nested scoring context factories are rebuilt in workers rather than pickled.
- Progress and cancellation keep the existing GUI/CLI contract.
- Benchmark workbooks are compared by explicit output path.

Residual risk:

- The true speedup may be limited by raw reader startup, pythonnet initialization, or disk IO. The implementation must measure rather than assume performance gains.

---

## Done When

1. Settings, CLI, and GUI expose opt-in process mode.
2. Serial default behavior remains unchanged.
3. Process mode completes the 8 raw validation subset.
4. Serial and process workbooks compare equivalent.
5. Timing data for serial / process 2 / process 4 is documented.
6. Full test suite passes.
7. Full 85 raw validation is run once near PR convergence, or explicitly deferred with user approval and documented risk.
