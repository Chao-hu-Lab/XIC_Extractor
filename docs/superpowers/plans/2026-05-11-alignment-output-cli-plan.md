# Alignment Output And CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first user-facing alignment CLI and write a minimal, stable alignment output surface from existing discovery batch results.

**Architecture:** Plan 3 consumes `discovery_batch_index.csv`, loads per-sample `discovery_candidates.csv`, runs Plan 1 clustering, runs Plan 2 conservative MS1 backfill, and writes TSV outputs. Default output is intentionally small: `alignment_review.tsv` and `alignment_matrix.tsv`. Per-cell audit and status matrix are debug opt-in files.

**Tech Stack:** Python, argparse, csv TSV writer, pytest, existing discovery CSV contracts, existing `xic_extractor.alignment` clustering/backfill, existing `RawFileReader` adapter through injected raw openers.

---

## Summary

Plan 3 is the first deliverable alignment surface. It does **not** implement the dream one-command `raw-dir -> discovery -> alignment` workflow yet. It consumes a completed discovery batch so alignment can be debugged independently from discovery.

Default outputs:

- `alignment_review.tsv`: one row per cluster for human review.
- `alignment_matrix.tsv`: area matrix for downstream analysis.

Debug opt-in outputs:

- `alignment_cells.tsv`: one row per `(cluster, sample)` cell.
- `alignment_matrix_status.tsv`: same shape as area matrix, values are cell status.

## Scope

In scope:

- Load discovery batch index and candidate CSVs.
- Convert candidate CSV rows back into `DiscoveryCandidate` objects.
- Run `cluster_candidates()`.
- Run `backfill_alignment_matrix()`.
- Write default TSV outputs atomically.
- Add `xic-align-cli`.
- Optional debug TSV flags.
- Synthetic/fake IO tests only.

Out of scope:

- One-command discovery + alignment wrapper.
- GUI.
- HTML report.
- Excel workbook.
- Real RAW validation.
- Legacy baseline comparison. That is Plan 4.
- Tuning alignment/backfill thresholds.

## Output Contract

### Default File 1: `alignment_review.tsv`

Purpose: human review entry point. One row per cluster.

Columns:

```text
cluster_id
neutral_loss_tag
cluster_center_mz
cluster_center_rt
cluster_product_mz
cluster_observed_neutral_loss_da
has_anchor
member_count
folded_cluster_count
folded_cluster_ids
folded_member_count
folded_sample_fill_count
fold_evidence
detected_count
rescued_count
absent_count
unchecked_count
present_rate
rescued_rate
representative_samples
representative_candidate_ids
warning
reason
```

Definitions:

- `present_rate = (detected_count + rescued_count) / sample_count`.
- `rescued_rate = rescued_count / sample_count`.
- `representative_samples`: semicolon-separated detected/rescued sample stems, capped at 5 then suffix `;...`.
- `representative_candidate_ids`: semicolon-separated detected candidate IDs, capped at 5 then suffix `;...`.
- Near-duplicate folding may remove secondary cluster rows from the review and
  matrix outputs. The retained primary row records folded secondaries in
  `folded_cluster_count`, `folded_cluster_ids`, and `folded_member_count`.
  `folded_sample_fill_count` records how many sample cells were filled from
  folded secondaries. `fold_evidence` records compact CID-only audit evidence
  such as max m/z ppm, max RT seconds, shared detected count, and detected
  Jaccard. `member_count` remains the detected member count of the retained
  primary cluster; it does not include MS1-backfilled cells.
- `warning` should be short and deterministic. Emit only the first matching warning by this precedence:
  - `no_anchor`: `has_anchor` is false.
  - `high_unchecked`: `unchecked_count / sample_count > 0.5`.
  - `high_backfill_dependency`: `rescued_count > detected_count`.
  - blank if no warning.
- `reason` should be concise and derived from counts, e.g.
  `anchor cluster; 7/8 present; 2 MS1 backfilled`.

### Default File 2: `alignment_matrix.tsv`

Purpose: downstream area matrix.

Shape:

- rows = clusters
- first columns:
  - `cluster_id`
  - `neutral_loss_tag`
  - `cluster_center_mz`
  - `cluster_center_rt`
- remaining columns = `sample_order`

Value contract:

- `detected` with `area > 0`: formatted area.
- `rescued` with `area > 0`: formatted area.
- `absent`: blank.
- `unchecked`: blank.
- `area is None`, `area <= 0`, or non-finite area: blank.

Missing and zero values are both blank by design. Downstream analysis should not need to convert zeros back to missing values.

### Debug File: `alignment_cells.tsv`

Only written when `--emit-alignment-cells` is set.

Columns mirror `AlignedCell` plus cluster representatives:

```text
cluster_id
sample_stem
status
area
apex_rt
height
peak_start_rt
peak_end_rt
rt_delta_sec
trace_quality
scan_support_score
source_candidate_id
source_raw_file
neutral_loss_tag
cluster_center_mz
cluster_center_rt
reason
```

### Debug File: `alignment_matrix_status.tsv`

Only written when `--emit-alignment-status-matrix` is set.

Same shape as `alignment_matrix.tsv`, but sample values are `detected`, `rescued`, `absent`, or `unchecked`.

## CLI Contract

Command:

```powershell
xic-align-cli `
  --discovery-batch-index output\discovery\discovery_batch_index.csv `
  --raw-dir C:\path\raws `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\alignment `
  --resolver-mode local_minimum
```

Required arguments:

- `--discovery-batch-index`
- `--raw-dir`
- `--dll-dir`

Optional arguments:

- `--output-dir`, default `output\alignment`
- `--resolver-mode`, choices `legacy_savgol`, `local_minimum`, default `local_minimum`
- `--emit-alignment-cells`
- `--emit-alignment-status-matrix`

Exit codes:

- `0`: outputs written.
- `2`: user/config/input error, including missing batch index, missing raw dir, missing DLL dir, malformed CSV, or raw reader setup error.

The CLI does not rerun discovery. If users want a future one-command workflow, add a wrapper in a later plan.

## Input Path And Escaping Contracts

### CSV Formula Escaping On Read

Discovery CSVs are both user-openable files and machine input for alignment. Discovery writers protect Excel users by prefixing formula-like strings with one leading apostrophe (`'`) when a value starts with `=`, `+`, `-`, or `@`.

Alignment loaders must reverse that escape for known machine fields on read:

- `discovery_batch_index.csv`: `sample_stem`, `raw_file`, `candidate_csv`, and `review_csv` if present.
- `discovery_candidates.csv`: `sample_stem`, `raw_file`, `candidate_id`, `feature_family_id`, and `feature_superfamily_id` if present.

Unescape exactly one leading apostrophe only for values that match `'=`, `'+`, `'-`, or `'@`. Do not strip arbitrary apostrophes from ordinary text. TSV writers still apply Excel formula escaping on output.

### RAW Path Authority

`--raw-dir` is authoritative for backfill RAW files. The `raw_file` value in `discovery_batch_index.csv` is provenance and filename hint only; its original parent directory may be stale.

For each batch row:

1. Unescape `raw_file`.
2. If `raw_file` is non-empty, try `raw_dir / Path(raw_file).name`.
3. If that path is missing or `raw_file` is empty, try `raw_dir / f"{sample_stem}.raw"`.
4. If no RAW file exists, do not fail the run. Pass no RAW source for that sample so Plan 2 backfill leaves eligible missing cells as `unchecked`.

`candidate_csv` remains resolved relative to the batch index parent when it is relative, because it is part of the completed discovery batch artifact.

## File Structure

Create:

- `xic_extractor/alignment/csv_io.py`
  - read discovery batch index.
  - read full discovery candidate CSVs.
  - parse row values into `DiscoveryCandidate`.
- `xic_extractor/alignment/tsv_writer.py`
  - write `alignment_review.tsv`.
  - write `alignment_matrix.tsv`.
  - write debug TSVs.
  - own TSV value formatting and Excel formula escaping.
- `xic_extractor/alignment/pipeline.py`
  - orchestrate load -> cluster -> backfill -> write.
  - accept injected raw opener for tests.
  - lazily import `open_raw` only in default opener.
- `scripts/run_alignment.py`
  - CLI wrapper.
- `tests/test_alignment_csv_io.py`
- `tests/test_alignment_tsv_writer.py`
- `tests/test_alignment_pipeline.py`
- `tests/test_run_alignment.py`

Modify:

- `pyproject.toml`
  - add `xic-align-cli = "scripts.run_alignment:main"`.
- `docs/superpowers/plans/2026-05-10-untargeted-cross-sample-alignment.md`
  - link Plan 3 and keep Plan 4 pending.

## Atomic Output Rule

Default outputs are a trusted pair. Do not allow `alignment_review.tsv` from a new run and `alignment_matrix.tsv` from a stale run.

Write all requested TSVs to `.tmp` paths first. Only after all writes succeed, replace final paths. On failure, delete temp files and leave existing final files untouched.

Tests must simulate a writer failure after stale outputs already exist.

## RAW Handle Lifecycle

The pipeline must own RAW reader lifetimes with `contextlib.ExitStack`.

- Open only RAW paths that exist under `--raw-dir` after applying the RAW path authority rule.
- Enter each RAW reader context before passing handles to `backfill_alignment_matrix()`.
- Close all entered RAW handles on success and on any failure, including clustering errors, backfill errors, or TSV writer failures.
- Keep the default opener lazy so tests can inject fake context managers without importing Thermo dependencies.

## Tasks

### Task 0: Dependency Check

**Files:**
- Read: `xic_extractor/alignment/clustering.py`
- Read: `xic_extractor/alignment/backfill.py`

- [ ] Confirm Plans 1 and 2 are implemented.

Run:

```powershell
Test-Path xic_extractor\alignment\clustering.py
Test-Path xic_extractor\alignment\backfill.py
```

Expected: both output `True`.

- [ ] Run existing alignment tests.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_config.py tests/test_alignment_models.py tests/test_alignment_compatibility.py tests/test_alignment_clustering.py tests/test_alignment_matrix.py tests/test_alignment_backfill.py -v
```

Expected: PASS. If Plan 1/2 tests are missing or failing, stop.

### Task 1: Discovery CSV Input Loader

**Files:**
- Create: `xic_extractor/alignment/csv_io.py`
- Test: `tests/test_alignment_csv_io.py`

- [ ] Write red tests:
  - reads `discovery_batch_index.csv` preserving row order as `sample_order`.
  - resolves `candidate_csv` paths relative to batch index parent when relative.
  - unescapes formula-escaped batch fields: `sample_stem`, `raw_file`, `candidate_csv`, and optional `review_csv`.
  - parses a full `discovery_candidates.csv` row into `DiscoveryCandidate`.
  - unescapes formula-escaped candidate fields: `sample_stem`, `raw_file`, `candidate_id`, `feature_family_id`, and `feature_superfamily_id`.
  - does not strip ordinary apostrophes from non-escaped text.
  - rejects missing required columns with `ValueError`.
  - rejects malformed bool/int/float tuple fields with row-numbered `ValueError`.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_csv_io.py -v
```

Expected red: missing `xic_extractor.alignment.csv_io`.

- [ ] Implement:
  - `DiscoveryBatchInput(sample_order, candidate_csvs)`.
  - `read_discovery_batch_index(path: Path) -> DiscoveryBatchInput`.
  - `read_discovery_candidates_csv(path: Path) -> tuple[DiscoveryCandidate, ...]`.
  - strict parsing for `DISCOVERY_CANDIDATE_COLUMNS`.

- [ ] Re-run and commit:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_csv_io.py -v
git add xic_extractor\alignment\csv_io.py tests\test_alignment_csv_io.py
git commit -m "feat(alignment): load discovery batch candidates"
```

### Task 2: TSV Writers

**Files:**
- Create: `xic_extractor/alignment/tsv_writer.py`
- Test: `tests/test_alignment_tsv_writer.py`

- [ ] Write red tests:
  - `alignment_review.tsv` has the exact default columns in this plan.
  - review rows compute detected/rescued/absent/unchecked counts.
  - review rows compute `present_rate` and `rescued_rate`.
  - review warning precedence is deterministic: `no_anchor`, then `high_unchecked` when `unchecked_count / sample_count > 0.5`, then `high_backfill_dependency` when `rescued_count > detected_count`, otherwise blank.
  - matrix writer blanks `absent`, `unchecked`, `None`, `0`, negative, and non-finite areas.
  - matrix writer includes sample columns in `sample_order`.
  - optional cells TSV writes full per-cell audit columns.
  - optional status matrix writes status values.
  - all user-controlled text is Excel-formula escaped.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_tsv_writer.py -v
```

Expected red: missing `xic_extractor.alignment.tsv_writer`.

- [ ] Implement TSV writers:
  - `write_alignment_review_tsv(path, matrix)`.
  - `write_alignment_matrix_tsv(path, matrix)`.
  - `write_alignment_cells_tsv(path, matrix)`.
  - `write_alignment_status_matrix_tsv(path, matrix)`.
  - stable float formatting, using `"{value:.6g}"`.
  - tab delimiter, UTF-8, newline-safe writes.

- [ ] Re-run and commit:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_tsv_writer.py -v
git add xic_extractor\alignment\tsv_writer.py tests\test_alignment_tsv_writer.py
git commit -m "feat(alignment): write review and matrix TSVs"
```

### Task 3: Alignment Pipeline Orchestration

**Files:**
- Create: `xic_extractor/alignment/pipeline.py`
- Test: `tests/test_alignment_pipeline.py`

- [ ] Write red tests:
  - pipeline loads candidate CSVs from batch index.
  - pipeline calls `cluster_candidates()` and `backfill_alignment_matrix()`.
  - raw sources are opened only for samples present in `sample_order`.
  - raw opener receives `(raw_path, dll_dir)`.
  - stale batch-index RAW parent paths are ignored; backfill uses `raw_dir / Path(raw_file).name`.
  - if batch-index `raw_file` is blank or missing, backfill tries `raw_dir / f"{sample_stem}.raw"`.
  - missing per-sample RAW in `raw_dir` does not fail; affected backfill cells can become `unchecked`.
  - RAW handles are entered before backfill receives them.
  - RAW handles are closed on success.
  - RAW handles are closed even when a TSV write fails.
  - default outputs are exactly review + matrix.
  - debug flags add cells/status outputs.
  - stale output pair remains untouched if a later TSV write fails.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_pipeline.py -v
```

Expected red: missing `xic_extractor.alignment.pipeline`.

- [ ] Implement:
  - `AlignmentRunOutputs(review_tsv, matrix_tsv, cells_tsv=None, status_matrix_tsv=None)`.
  - `run_alignment(discovery_batch_index, raw_dir, dll_dir, output_dir, alignment_config, peak_config, emit_alignment_cells=False, emit_alignment_status_matrix=False, raw_opener=None)`.
  - default raw opener lazily imports `xic_extractor.raw_reader.open_raw`.
  - resolve sample RAW files using the RAW path authority rule in this plan.
  - own RAW reader contexts with `ExitStack`.
  - temp-write all requested TSVs before replacing final outputs.

- [ ] Re-run and commit:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_pipeline.py -v
git add xic_extractor\alignment\pipeline.py tests\test_alignment_pipeline.py
git commit -m "feat(alignment): orchestrate alignment outputs"
```

### Task 4: CLI Entry Point

**Files:**
- Create: `scripts/run_alignment.py`
- Modify: `pyproject.toml`
- Test: `tests/test_run_alignment.py`

- [ ] Write red tests:
  - CLI passes resolved batch index, raw dir, dll dir, output dir, resolver mode, and debug flags to `run_alignment()`.
  - CLI rejects missing batch index.
  - CLI rejects missing raw dir.
  - CLI rejects missing dll dir.
  - CLI returns `2` for `RawReaderError` and `ValueError`.
  - pyproject registers `xic-align-cli`.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_run_alignment.py -v
```

Expected red: missing `scripts.run_alignment` and pyproject entry point.

- [ ] Implement `scripts/run_alignment.py` using the style of `scripts/run_discovery.py`.
- [ ] Build `ExtractionConfig` from `CANONICAL_SETTINGS_DEFAULTS`, with `resolver_mode` from CLI.
- [ ] Add pyproject script:

```toml
xic-align-cli = "scripts.run_alignment:main"
```

- [ ] Re-run and commit:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_run_alignment.py -v
git add scripts\run_alignment.py pyproject.toml tests\test_run_alignment.py
git commit -m "feat(alignment): add alignment CLI"
```

### Task 5: Public Contract And Docs Sync

**Files:**
- Modify: `docs/superpowers/plans/2026-05-10-untargeted-cross-sample-alignment.md`
- Test: boundary tests if present, otherwise `tests/test_run_alignment.py`

- [ ] Update roadmap index:
  - Plan 3 links to this file.
  - Plan 4 remains pending.
  - Default outputs are stated as `alignment_review.tsv` and `alignment_matrix.tsv`.
  - Debug outputs are opt-in only.

- [ ] Add boundary tests if not already covered:
  - `xic_extractor.alignment.tsv_writer` does not import RAW readers.
  - `xic_extractor.alignment.csv_io` does not import RAW readers.
  - `xic_extractor.alignment.pipeline` may lazily import raw reader only in default opener.

- [ ] Run stale wording checks:

```powershell
$debugDefaultPattern = 'alignment_(cells|matrix_status)\.tsv.*default'
rg -n $debugDefaultPattern docs\superpowers\plans\2026-05-11-alignment-output-cli-plan.md docs\superpowers\plans\2026-05-10-untargeted-cross-sample-alignment.md
$pendingPattern = "Plan 3: Alignment Output and CLI " + [char]0x2014 + " pending"
Select-String -SimpleMatch $pendingPattern docs\superpowers\plans\2026-05-10-untargeted-cross-sample-alignment.md
```

Expected: no incorrect claims. Plan 4 may still be described as pending.

- [ ] Commit:

```powershell
git add docs\superpowers\plans\2026-05-10-untargeted-cross-sample-alignment.md docs\superpowers\plans\2026-05-11-alignment-output-cli-plan.md
git commit -m "docs(alignment): define output and CLI plan"
```

## Validation

Run after implementation:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_csv_io.py tests/test_alignment_tsv_writer.py tests/test_alignment_pipeline.py tests/test_run_alignment.py -v
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_config.py tests/test_alignment_models.py tests/test_alignment_compatibility.py tests/test_alignment_clustering.py tests/test_alignment_matrix.py tests/test_alignment_backfill.py -v
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests scripts
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

No real RAW validation is required in Plan 3. Real data belongs to Plan 4 after the CLI/output contract exists.

## Acceptance Criteria

- `xic-align-cli` exists and consumes an existing discovery batch index.
- Default output writes exactly `alignment_review.tsv` and `alignment_matrix.tsv`.
- `alignment_cells.tsv` and `alignment_matrix_status.tsv` are opt-in only.
- Area matrix blanks absent, unchecked, missing, zero, negative, and non-finite values.
- Review TSV explains counts and rates without requiring users to inspect debug files.
- Output writes are atomic as a trusted set.
- TSV strings are Excel-formula escaped.
- Alignment CSV loaders unescape known formula-escaped machine fields before path and ID handling.
- `--raw-dir` is the authoritative RAW source root for backfill.
- RAW reader handles are closed on success and failure.
- Plan 3 does not rerun discovery and does not add GUI/HTML/Excel output.

## Self-Review Notes

- This plan preserves the UX decision to keep daily alignment output small.
- This plan intentionally delays one-command `raw-dir -> discovery -> alignment` to a later wrapper.
- This plan gives Plan 4 stable files to compare against legacy FH, metabCombiner, and combine-fix outputs.
