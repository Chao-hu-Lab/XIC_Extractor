# Validation Harness

This repo keeps real-data validation explicit and tiered. The default CI test
suite does not require Thermo RAW files.

This document covers `scripts\validation_harness.py`, which is a targeted
extraction / workbook comparison harness. It is not the canonical runner for
large untargeted alignment acceptance. For stable local Python runners, RAW/DLL
paths, 85RAW command shape, `validation-minimal`, heartbeat sidecars, and known
launch anti-patterns, read
[`docs/agent/parameter-settings.md`](../agent/parameter-settings.md)
before starting any RAW run.

## Harness Scope

| Suite | Purpose | Default data | Output contract |
| --- | --- | --- | --- |
| `manual-2raw` | Manual truth area/RT comparison for resolver development | `$env:XIC_MANUAL_2RAW_ROOT` | `local_minimum_param_sweep_summary.xlsx` |
| `tissue-8raw` | Targeted extraction workbook smoke / A-B comparison | `$env:XIC_RAW_VALIDATION_DIR` | `xic_results_<mode>_w<workers>.xlsx` |
| `tissue-85raw` | Full targeted extraction workbook gate, opt-in only | `$env:XIC_RAW_ROOT` | `xic_results_<mode>_w<workers>.xlsx` |

All suites write `validation_summary.csv` under the selected run directory. The
8RAW and 85RAW suites validate the expected `.raw` count before running: 8 and
85 respectively.

If local env vars are not loaded, dry-run/spec construction falls back to
repo-local `local_validation_artifacts/...` placeholders. Real RAW-backed runs
should load `.env.xic-local` or equivalent environment variables first; the
placeholders are for command inspection, not real data discovery.

Use this harness when the decision depends on targeted extraction workbook
behavior. Do not use it for alignment/downstream matrix acceptance. Alignment
validation uses `scripts.run_alignment` and the machine TSV contract described in
`docs/agent/parameter-settings.md`.

## Daily Workbook / Method Validation

Run the manual truth sweep plus the 8RAW targeted extraction subset:

```powershell
.venv\Scripts\python.exe scripts\validation_harness.py `
  --run-id method_dev `
  --output-root output/validation_harness
```

Current defaults:

- `resolver_mode=region_first_safe_merge`
- `parallel_mode=process`
- `parallel_workers=4`
- suites: `manual-2raw`, `tissue-8raw`
- manual sweep grid: `quick`

`manual-2raw` uses the same worker setting, but the quick grid is mostly
sequential because NoSplit and Split use different target CSVs and are staged as
single-RAW runs. `parallel_workers=4` matters most for `tissue-8raw` and
`tissue-85raw`, where each extraction run contains multiple RAW files.

For local-minimum preset calibration, make the resolver mode explicit and use a
focused grid:

```powershell
.venv\Scripts\python.exe scripts\validation_harness.py `
  --suite manual-2raw `
  --resolver-mode local_minimum `
  --grid calibration-v1 `
  --run-id local_minimum_calibration_v1 `
  --output-root output/validation_harness
```

`calibration-v1` keeps the sweep small and targets historical local-minimum
parameter questions such as peak-duration permissiveness and search-range
semantics. `calibration-v2` focuses on `resolver_peak_duration_min` and
`resolver_min_relative_height`. These calibration grids are method-development
evidence; they are not a replacement for current alignment matrix validation.

## Inspect Exact Commands

Dry-run prints exact commands without touching RAW files:

```powershell
.venv\Scripts\python.exe scripts\validation_harness.py `
  --suite all `
  --dry-run `
  --confirm-full-run `
  --run-id method_dev `
  --output-root output/validation_harness
```

Use dry-run before any full targeted extraction workbook gate. If the printed
runner, RAW/DLL path, foreground-run, or heartbeat expectation conflicts with
`docs/agent/parameter-settings.md`, stop and update the docs or runner before
launching a long RAW run. The alignment artifact/profile contract in that file
does not apply to targeted workbook harness suites.

## Baseline Compare

Create a workbook baseline run once:

```powershell
.venv\Scripts\python.exe scripts\validation_harness.py `
  --suite tissue-8raw `
  --run-id current `
  --output-root output/validation_baselines
```

Compare a later run against that baseline by keeping the same `run-id` and
pointing `--baseline-root` at the baseline root:

```powershell
.venv\Scripts\python.exe scripts\validation_harness.py `
  --suite tissue-8raw `
  --run-id current `
  --output-root output/validation_harness `
  --baseline-root output/validation_baselines
```

The compare target is exact:

```text
output/validation_baselines\<run-id>\tissue_8raw_<resolver>\xic_results_process_w4.xlsx
```

Workbook comparison uses `scripts\compare_workbooks.py`, which ignores runtime
metadata such as timestamps and output paths but compares analytical workbook
sheets. This is a targeted extraction regression check, not the downstream
alignment matrix contract.

## Alignment Validation

For untargeted alignment validation, downstream handoff, or 85RAW acceptance,
start from `docs/agent/parameter-settings.md` instead of this harness. The
current large-run contract is:

```text
validation-minimal + production-equivalent + validation-fast + super-window
+ timing heartbeat
```

That shape writes the primary machine gate surface:

- `alignment_matrix.tsv`
- `alignment_review.tsv`
- `alignment_cells.tsv`

It intentionally avoids large `.xlsx`, HTML, owner-edge, status-matrix,
event-owner, and ambiguous-owner artifacts unless a debug or human-review task
explicitly asks for them. Lightweight provenance sidecars, such as
`skipped_evidence_ledger.tsv` and `alignment_run_metadata.json`, may still be
emitted when the chosen backfill scope needs them.

Before starting an alignment validation run:

1. Confirm the active discovery batch index and check its sample count.
2. Confirm RAW and DLL paths with `Test-Path`.
3. Decide whether existing notes or output artifacts already answer the current
   decision.
4. Include `--expected-sample-count 85` for full 85RAW alignment runs.
5. Run the same launch contract with `--preflight-only` when checking a command
   shape before a long run. This checks the shared discovery-batch parser,
   candidate CSV existence, and RAW path existence, but does not load candidate
   rows or open RAW files. With `--expected-sample-count 85`, the CLI also
   enforces the canonical 85RAW profile, heartbeat, and local `.venv` runner.
6. Include both `--timing-output` and `--timing-live-output`.
7. Run in the foreground from the Codex shell, or get explicit approval for an
   external terminal / automation.

Older alignment examples that used heavier artifact levels and workbook parity
were useful during early performance exploration. They should not be copied into
new 85RAW acceptance runs.

## Full Targeted Workbook 85RAW Gate

The `tissue-85raw` harness suite remains available only for full targeted
extraction workbook release checks:

```powershell
.venv\Scripts\python.exe scripts\validation_harness.py `
  --suite tissue-85raw `
  --confirm-full-run `
  --run-id full_tissue_workbook_gate `
  --output-root output/validation_harness
```

Do not use this suite for routine PR checks, and do not use it as the alignment
handoff gate. For alignment, use the canonical foreground command shape in
`docs/agent/parameter-settings.md`.

## Stop Conditions

- If the 8RAW gate is inconclusive, do not launch 85RAW just to gather more
  samples. Fix the blocker or redefine the gate first.
- If a long RAW run lacks a heartbeat sidecar, stop and relaunch only after the
  command shape is corrected.
- If a validation task cannot change the next engineering decision, use the
  smallest confirmation or existing artifact instead of expanding the run.
