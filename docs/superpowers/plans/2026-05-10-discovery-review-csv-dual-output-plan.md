# Discovery Review CSV Dual Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a human-focused `discovery_review.csv` next to the full `discovery_candidates.csv`, and update batch/CLI output contracts to expose both paths.

**Architecture:** Keep `discovery_candidates.csv` as the full alignment-ready artifact. Add a brief review CSV writer that reuses the same candidate sort key and emits only base triage columns plus `review_note`. Pipeline functions return structured output dataclasses instead of bare `Path` so callers can reliably find both CSVs.

**Tech Stack:** Python dataclasses, `csv.DictWriter`, pytest, existing `xic_extractor.discovery` modules.

---

## File Structure Map

- Modify `xic_extractor/discovery/models.py`
  - Add `DISCOVERY_BRIEF_COLUMNS`.
  - Add `DiscoveryRunOutputs` and `DiscoveryBatchOutputs`.
- Modify `xic_extractor/discovery/csv_writer.py`
  - Add `write_discovery_review_csv`.
  - Add `build_discovery_review_note`.
  - Reuse the existing candidate sort key.
- Modify `xic_extractor/discovery/pipeline.py`
  - `run_discovery()` returns `DiscoveryRunOutputs`.
  - `run_discovery_batch()` returns `DiscoveryBatchOutputs`.
  - Batch index gains `review_csv`.
- Modify `scripts/run_discovery.py`
  - CLI fakes and stdout report both single-run output paths.
- Modify `xic_extractor/discovery/__init__.py`
  - Re-export new public discovery output names.
- Tests:
  - `tests/test_discovery_review_csv.py`
  - `tests/test_discovery_pipeline.py`
  - `tests/test_run_discovery.py`
  - `tests/test_discovery_csv.py`

## Contract

Brief CSV columns:

```text
review_priority
evidence_tier
evidence_score
ms2_support
ms1_support
rt_alignment
family_context
candidate_id
precursor_mz
best_seed_rt
ms1_area
seed_event_count
neutral_loss_tag
review_note
```

Full CSV remains unchanged in this plan.

## Task 1: Define Brief Columns And Output Dataclasses

**Files:**
- Modify: `xic_extractor/discovery/models.py`
- Create: `tests/test_discovery_review_csv.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_discovery_review_csv.py` with assertions that:

- `DISCOVERY_BRIEF_COLUMNS` exactly matches the 14-column contract above.
- `DiscoveryRunOutputs(candidates_csv=..., review_csv=...)` exposes both paths.
- `DiscoveryBatchOutputs(batch_index_csv=..., per_sample=...)` exposes the batch index and per-sample outputs.

- [ ] **Step 2: Run the red test**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_review_csv.py -v
```

Expected: FAIL because the new names do not exist.

- [ ] **Step 3: Implement the minimal model changes**

Add the brief column tuple and frozen output dataclasses in `models.py`.

- [ ] **Step 4: Run the green test**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_review_csv.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/discovery/models.py tests/test_discovery_review_csv.py
git commit -m "feat(discovery): define review CSV contract and output dataclasses"
```

## Task 2: Write Brief Review CSV

**Files:**
- Modify: `xic_extractor/discovery/csv_writer.py`
- Modify: `tests/test_discovery_review_csv.py`

- [ ] **Step 1: Write failing tests**

Add tests that verify:

- `write_discovery_review_csv()` writes only `DISCOVERY_BRIEF_COLUMNS`.
- Review CSV and full CSV use the same candidate order.
- Excel formula escaping applies to brief CSV text fields.
- `review_note` is concise and does not equal the full `reason` when `reason` is long.

- [ ] **Step 2: Run the red test**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_review_csv.py -v
```

Expected: FAIL because the writer does not exist.

- [ ] **Step 3: Implement the writer**

In `csv_writer.py`:

- Import `DISCOVERY_BRIEF_COLUMNS`.
- Add `build_discovery_review_note(candidate) -> str`.
- Add `write_discovery_review_csv(path, candidates) -> Path`.
- Keep row formatting through `format_discovery_csv_value`.
- Reuse `_candidate_sort_key`.

Suggested `review_note` v1:

```text
{ms2_support} MS2; {ms1_support} MS1; {rt_alignment} RT; {family_context}
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_review_csv.py tests/test_discovery_csv.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/discovery/csv_writer.py tests/test_discovery_review_csv.py
git commit -m "feat(discovery): write brief review CSV"
```

## Task 3: Return Dual Outputs From Pipeline

**Files:**
- Modify: `xic_extractor/discovery/pipeline.py`
- Modify: `tests/test_discovery_pipeline.py`

- [ ] **Step 1: Write failing tests**

Add or update tests that verify:

- `run_discovery()` returns `DiscoveryRunOutputs`.
- Single RAW writes both `discovery_candidates.csv` and `discovery_review.csv`.
- Empty candidate runs still write header-only full and brief CSVs.
- `run_discovery_batch()` returns `DiscoveryBatchOutputs`.
- Batch index includes `candidate_csv` and `review_csv`.
- Batch index escapes Excel formula strings.

- [ ] **Step 2: Run the red tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_pipeline.py -v
```

Expected: FAIL because pipeline still returns bare `Path`.

- [ ] **Step 3: Implement pipeline output contracts**

Update `run_discovery()` and `run_discovery_batch()` to call both writers and return the new dataclasses.

Use helper functions:

- `_write_dual_csvs(output_dir, candidates) -> DiscoveryRunOutputs`
- `_batch_index_row(..., outputs: DiscoveryRunOutputs, ...) -> dict[str, str]`

- [ ] **Step 4: Run focused tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_pipeline.py tests/test_discovery_review_csv.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/discovery/pipeline.py tests/test_discovery_pipeline.py
git commit -m "feat(discovery): return dual CSV outputs from discovery pipeline"
```

## Task 4: Update CLI Contract

**Files:**
- Modify: `scripts/run_discovery.py`
- Modify: `tests/test_run_discovery.py`
- Modify: `xic_extractor/discovery/__init__.py`

- [ ] **Step 1: Write failing tests**

Update CLI fakes to return `DiscoveryRunOutputs` / `DiscoveryBatchOutputs`. Assert stdout includes:

- `Discovery candidates CSV:`
- `Discovery review CSV:`
- `Discovery batch index:`

- [ ] **Step 2: Run the red tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_run_discovery.py -v
```

Expected: FAIL because CLI still expects bare paths.

- [ ] **Step 3: Implement CLI updates**

Update CLI output handling and public re-exports.

- [ ] **Step 4: Run focused tests and lint**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_run_discovery.py tests/test_discovery_pipeline.py tests/test_discovery_review_csv.py -v
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests scripts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add scripts/run_discovery.py tests/test_run_discovery.py xic_extractor/discovery/__init__.py
git commit -m "feat(discovery): expose dual CSV paths in CLI"
```

## Final Validation

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_review_csv.py tests/test_discovery_pipeline.py tests/test_run_discovery.py tests/test_discovery_csv.py -v
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests scripts
```

Optional real-data smoke:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-discovery-cli --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --dll-dir "C:\Xcalibur\system\programs" --output-dir "output\discovery\tissue8_dual_csv_smoke" --neutral-loss-tag DNA_dR --neutral-loss-da 116.0474 --resolver-mode local_minimum
```

