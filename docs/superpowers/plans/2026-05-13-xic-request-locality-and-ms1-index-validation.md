# XIC Request Locality And MS1 Index Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add repeatable diagnostics that distinguish exact scan-window locality wins from approximate MS1-index fast-mode ideas.

**Architecture:** Keep all new behavior in validation scripts and tests. Production alignment continues to use Thermo vendor XIC calls; the scripts only read existing discovery/alignment artifacts and RAW files to report request locality or vendor-vs-local-index drift.

**Tech Stack:** Python 3, argparse, csv/json, NumPy, pytest, Thermo RawFileReader through existing `xic_extractor.raw_reader.open_raw`.

---

## File Structure

- Create `scripts/analyze_xic_request_locality.py`
  - Reads discovery batch index and optional alignment review/cells TSV.
  - Converts requested RT windows to Thermo scan windows per RAW file.
  - Reports original chunk calls, sorted chunk calls, and per-sample upper-bound calls.
- Create `scripts/validate_ms1_scan_index_xic.py`
  - Builds a local MS1 scan index for selected RAW files.
  - Compares vendor `extract_xic()` traces with local mass-window `max` traces.
  - Reports RT-grid match, intensity drift, and peak status/apex/area drift.
- Create `tests/test_analyze_xic_request_locality.py`
  - Tests scan-window grouping, sorted locality improvement, and owner-backfill reconstruction.
- Create `tests/test_validate_ms1_scan_index_xic.py`
  - Tests MS1-index trace extraction and vendor/local comparison metrics with fake RAW objects.
- Modify `docs/superpowers/specs/2026-05-12-untargeted-performance-architecture-spec.md`
  - Record results after real RAW validation.

## Task 1: Request Locality Analyzer

**Files:**
- Create: `scripts/analyze_xic_request_locality.py`
- Test: `tests/test_analyze_xic_request_locality.py`

- [ ] **Step 1: Write failing tests**

Add tests that create tiny discovery/alignment artifacts and fake `open_raw`.

Expected behavior:

- `build_owners` requests are reconstructed from discovery candidate CSV rows.
- `owner_backfill` requests are reconstructed from alignment review/cells TSVs by treating `detected` samples as existing owners and missing samples as backfill requests.
- For batch size 2 and request windows A, B, A:
  - original chunk call count is 3,
  - sorted chunk call count is 2,
  - per-sample upper-bound call count is 2.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest tests\test_analyze_xic_request_locality.py -q
```

Expected: fail because the script does not exist yet.

- [ ] **Step 2: Implement analyzer**

Implement:

```python
@dataclass(frozen=True)
class RequestRecord:
    stage: str
    sample_stem: str
    mz: float
    rt_min: float
    rt_max: float
    ppm_tol: float
```

Core functions:

- `collect_build_owner_requests(batch_index, max_rt_sec, preferred_ppm)`
- `collect_owner_backfill_requests(batch_index, alignment_review, alignment_cells, max_rt_sec, preferred_ppm, owner_backfill_min_detected_samples)`
- `summarize_locality(records, raw_paths, dll_dir, batch_size, open_raw_func=open_raw)`

Return JSON-friendly summaries with:

- `request_count`
- `original_chunk_call_count`
- `sorted_chunk_call_count`
- `upper_bound_call_count`
- `unique_scan_window_count`
- `sample_count`

- [ ] **Step 3: Verify analyzer tests pass**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest tests\test_analyze_xic_request_locality.py -q
```

Expected: pass.

## Task 2: MS1 Scan-Index Validation Harness

**Files:**
- Create: `scripts/validate_ms1_scan_index_xic.py`
- Test: `tests/test_validate_ms1_scan_index_xic.py`

- [ ] **Step 1: Write failing tests**

Add fake RAW tests proving:

- local index uses only MS1 scans,
- local extraction uses max intensity inside the mass tolerance window,
- vendor/local comparison reports length, RT-grid, max absolute intensity drift, sum ratio, and correlation.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest tests\test_validate_ms1_scan_index_xic.py -q
```

Expected: fail because the script does not exist yet.

- [ ] **Step 2: Implement validation harness**

Keep it script-local and explicit. Do not import it into production alignment.

CLI arguments:

- `--discovery-batch-index`
- `--raw-dir`
- `--dll-dir`
- `--sample-count`
- `--request-count`
- `--max-rt-sec`
- `--preferred-ppm`
- `--output-json`

Report per sample and aggregate:

- vendor extraction seconds,
- index build seconds,
- local extraction seconds,
- request count,
- status match count,
- apex RT close counts,
- area relative-difference median/p95/max.

- [ ] **Step 3: Verify harness tests pass**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest tests\test_validate_ms1_scan_index_xic.py -q
```

Expected: pass.

## Task 3: Real RAW Validation

**Files:**
- Output artifacts under `output\diagnostics\...`; keep untracked.

- [ ] **Step 1: Run locality analyzer on 8-RAW artifacts**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python scripts\analyze_xic_request_locality.py --discovery-batch-index output\discovery\timing_phase0_8raw\discovery_batch_index.csv --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --dll-dir "C:\Xcalibur\system\programs" --alignment-review output\alignment\timing_phase5_batch1_workers8_8raw\alignment_review.tsv --alignment-cells output\alignment\timing_phase5_batch1_workers8_8raw\alignment_cells.tsv --raw-xic-batch-size 64 --output-json output\diagnostics\xic_request_locality_8raw.json
```

Expected: confirms `build_owners` upper bound is close to request count and `owner_backfill` benefits from sorted locality.

- [ ] **Step 2: Run MS1 index validation on one RAW**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python scripts\validate_ms1_scan_index_xic.py --discovery-batch-index output\discovery\timing_phase0_8raw\discovery_batch_index.csv --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --dll-dir "C:\Xcalibur\system\programs" --sample-count 1 --request-count 377 --output-json output\diagnostics\ms1_scan_index_validation_1raw.json
```

Expected: produces a report, not an acceptance claim. If status or area drift is non-trivial, document MS1 index as approximate only.

## Task 4: Verification And Docs

**Files:**
- Modify: `docs/superpowers/specs/2026-05-12-untargeted-performance-architecture-spec.md`

- [ ] **Step 1: Run focused and related tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest tests\test_analyze_xic_request_locality.py tests\test_validate_ms1_scan_index_xic.py tests\test_alignment_owner_backfill.py -q
```

Expected: pass.

- [ ] **Step 2: Run py_compile and diff check**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python -m py_compile scripts\analyze_xic_request_locality.py scripts\validate_ms1_scan_index_xic.py
git diff --check
```

Expected: py_compile succeeds; `git diff --check` has no whitespace errors.

- [ ] **Step 3: Update the spec conclusion**

Record:

- exact locality result,
- MS1-index validation result,
- whether explicit approximate fast mode is worth a separate plan.

## Stop Conditions

Stop and report instead of changing production if:

- locality analyzer cannot reproduce existing raw-call counts closely enough to guide decisions,
- a proposed exact optimization changes current machine TSV output without an intentional contract change,
- a proposed fast mode changes peak status or area but lacks explicit output semantics, validation artifacts, or acceptance criteria.

## 2026-05-13 Execution Notes

This plan was executed against the 8-RAW validation artifacts and one real RAW
file.

Locality output:

- `output\diagnostics\xic_request_locality_8raw.json`

Key locality results:

- `build_owners`: `3343` requests, `3343` sorted batch64 calls, `3343`
  per-sample upper-bound calls. There is no useful scan-window locality.
- `owner_backfill` artifact estimate: `3333` requests, `3198` original
  batch64 calls, `2874` sorted batch64 calls, `2867` upper-bound calls. This
  supports keeping the owner-backfill RT-window sort.

MS1-index output:

- `output\diagnostics\ms1_scan_index_validation_1raw.json`

Key MS1-index results for `BenignfatBC1055_DNA`:

- `377/377` RT grids matched.
- Peak status matched `375/377`.
- Vendor extraction took `6.449s`; index build plus local extraction took
  `1.895s`.
- Median area relative delta was `2.13%`; P95 was `13.93%`; max was
  `714.79%`.

Decision:

- Do not treat MS1-index extraction as equivalent to the current vendor-XIC
  path.
- Keep it as a valid candidate for an explicit fast mode or next-model variant,
  because the alignment algorithm is not final and current `backfill`/`absent`
  semantics may change.
- Do not spend more effort on larger batch sizes for `build_owners`; the
  locality report proves there is no repeated scan window to exploit.
- Use current-output equality as a regression guard only. For intentional
  model changes, require a separate acceptance frame: runtime, peak-status
  drift, apex/area drift, feature-count deltas, present/backfill/absent
  distribution changes, and downstream review impact.

## Self-Review

- Spec coverage: covers scan-window locality, request sorting/merging limits, and MS1-index validation without altering default extraction.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: uses `RequestRecord`, existing `open_raw`, and script-local validation helpers only.
