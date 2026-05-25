# P3 Third-Party Shadow Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce P3 diagnostic-only third-party shadow evidence for the 8RAW strict ISTD set using the current RAW-derived internal alignment output and user-provided experimental mzML files.

**Architecture:** Keep production XIC_Extractor RAW-first. Add isolated diagnostic tooling under `tools/diagnostics/` that can normalize third-party feature outputs, join them to internal alignment/integration audit rows, and write decision-oriented TSV/JSON/Markdown reports. External asari/MassCube execution is isolated behind optional runner wrappers and an isolated venv; no production module imports third-party packages.

**Current hard constraint:** P3 must not introduce `.raw` -> `.mzML` conversion, must not make mzML a production precondition, and must not change direct `.raw` reading assumptions. The mzML directory is a user-provided experimental input only:

```text
C:\Users\user\Desktop\NTU cancer\NTU Tissue preprocess\mzml
```

**Tech Stack:** Python stdlib, pytest, existing TSV artifacts, optional subprocess calls to asari/MassCube from an isolated venv.

---

## Plan Review Log

- Initial plan status: drafted after P3 spec was patched for the RAW-first / user-provided mzML constraint.
- Plan review patch 1: removed remaining overclaims that asari is per-sample-only or MassCube must use a Python API; external entry points and native schemas must be verified from the installed versions.
- Plan review patch 2: 8RAW mzML staging uses hard links first and stops before copying large files.
- Plan review patch 3: optional native fields (`peak_start`, `peak_end`, `snr`, `confidence`) may remain empty with explicit `native_schema_status`; missing third-party TSVs must be tested as graceful pairwise/inconclusive output.
- Post-implementation patch 4: strict ISTD `asari_only` / `masscube_only` rows are limited to third-party features inside target m/z/RT windows. Off-target untargeted features are ignored rather than counted as internal misses.
- Post-review disposition patch 5: P3 runner / normalizer / joiner code is not retained as maintained Phase 1 code because the external tools are not qualified as production gates or P2b promotion evidence. Preserve findings and local output artifacts only.
- Scope lock: P3 diagnostic only. Do not change production peak detection, area integration, RT correction, alignment, config defaults, workbook schemas, or Cleanup specs.
- External dependency lock: do not edit `pyproject.toml`; do not install asari/MassCube into the main `.venv`.
- Stop condition: if a task requires generating mzML from `.raw`, changing production input contracts, or importing third-party packages from `xic_extractor/`, stop and write a note instead.

## Current Evidence To Preserve

- Active worktree: `.worktrees/peak-pipeline-modernization`
- Branch: `codex/peak-pipeline-modernization`
- P2 status after baseline truth audit: `shadow_ready` for P3 entry; not P2b production-ready.
- Internal P2 AsLS shadow alignment:
  `output/phase1_p2_asls_shadow_validation/alignment/asls_shadow/`
- Internal strict ISTD target mapping:
  `output/phase1_p2_asls_shadow_validation/diagnostics/targeted_istd_benchmark/targeted_istd_benchmark_summary.tsv`
- User-provided mzML directory contains 87 `.mzML` files and covers all 8 internal validation sample stems:
  - `BenignfatBC1055_DNA`
  - `BenignfatBC1151_DNA`
  - `Breast_Cancer_Tissue_pooled_QC3`
  - `Breast_Cancer_Tissue_pooled_QC5`
  - `NormalBC2263_DNA`
  - `NormalBC2312_DNA`
  - `TumorBC2263_DNA`
  - `TumorBC2312_DNA`
- `asari`, `masscube`, and conversion tools are not installed in the main environment; `uv` is available.
- Isolated P3 venv: `C:\tmp\xic_p3_shadow_venv`
- Installed external versions in isolated venv:
  - `asari-metabolomics==1.17.0`
  - `masscube==1.2.20`
- Current third-party documentation check:
  - asari package metadata reports BSD 3-Clause; official docs show `asari process --mode pos --input ...` and `preferred_Feature_table.tsv`.
  - Installed MassCube package metadata reports `CC BY-NC 4.0`; local source shows `data/` is required, while `sample_table.csv` and `parameters.csv` are optional defaults for the untargeted workflow.
  - MassCube workflow import fails in this isolated Python 3.13 venv with a `numba/umap` cache locator error before processing can start; MassCube output is therefore `unsupported_native_output` for this P3 run.

## Outputs

Runtime outputs under:

```text
output/phase1_p3_third_party_shadow_comparison/
```

Expected artifacts:

- `p3_shadow_input_manifest.tsv`
- `shadow_comparison_asari_8raw.tsv` if asari run or normalized input succeeds
- `shadow_comparison_masscube_8raw.tsv` if MassCube run or normalized input succeeds
- `shadow_comparison_8raw.tsv`
- `shadow_comparison_8raw_summary.tsv`
- `shadow_comparison_8raw.json`
- `shadow_comparison_8raw.md`
- `third_party_shadow_findings.md` copied or summarized into `docs/superpowers/notes/2026-05-25-p3-third-party-shadow-findings.md`

Post-review disposition: runtime artifacts remain as local evidence; the
temporary P3 tooling files were discarded before commit.

## Standardized Third-Party Feature Schema

Adapters normalize external outputs to:

- `tool`
- `sample_stem`
- `feature_id`
- `mz_observed`
- `rt_apex_min`
- `peak_start_min`
- `peak_end_min`
- `area`
- `snr`
- `confidence`
- `native_schema_status`
- `source_path`

The joiner consumes this standardized schema, not native asari/MassCube tables directly. `mz_observed`, `rt_apex_min`, and `area` are required for quantitative matching. `peak_start_min`, `peak_end_min`, `snr`, and `confidence` are optional native evidence fields; if the installed tool does not expose a documented equivalent, leave the value empty and set `native_schema_status=missing_optional_fields`. If `mz_observed`, `rt_apex_min`, or `area` cannot be mapped without guessing, mark that tool `unsupported_native_output`.

## Task 1: P3 Input Manifest And Contract Docs

The task file list below is historical execution detail. These temporary P3
tooling files were discarded before commit after post-implementation review.

**Files:**

- Create: `tools/diagnostics/p3_shadow_inputs.py`
- Create: `tests/test_p3_shadow_inputs.py`
- Create or update: `tools/diagnostics/README.md`

- [x] **Step 1: Add failing tests for mzML manifest coverage**

Create tests that verify:

- `build_mzml_manifest(...)` matches internal sample stems to explicit `.mzML` files by file stem
- missing mzML files are reported as `missing_mzml`
- extra mzML files are retained as `extra_mzml`
- no conversion command or conversion path is produced

- [x] **Step 2: Run tests and confirm failure**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p3_shadow_inputs.py -q
```

Expected: import failure because the module does not exist.

- [x] **Step 3: Implement manifest builder and README contract**

Implement:

- `P3ShadowInputManifestRow`
- `build_mzml_manifest(internal_sample_stems, mzml_dir)`
- `write_mzml_manifest_tsv(rows, path)`

Document in `tools/diagnostics/README.md`:

- P3 production comparator is RAW-derived internal output
- mzML is user-provided experimental input only
- P3 tools never convert `.raw`
- third-party dependencies run only from isolated venv

- [x] **Step 4: Verify Task 1**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p3_shadow_inputs.py -q
```

Expected: Task 1 tests pass.

## Task 2: Join Core TDD

**Files:**

- Create: `tools/diagnostics/shadow_comparison_join.py`
- Create: `tests/test_p3_shadow_comparison_join.py`

- [x] **Step 1: Add failing tests for internal/third-party matching**

Tests should cover:

- strict ISTD internal rows are joined through `targeted_istd_benchmark_summary.tsv` by `selected_feature_id`
- AsLS shadow area is preserved when present
- third-party rows match by same sample, m/z ppm tolerance, and RT tolerance seconds
- missing `--asari-features-tsv` or `--masscube-features-tsv` paths degrade to pairwise or `inconclusive` rows instead of crashing
- `triple_match`, `pair_match_asari`, `pair_match_masscube`, `internal_only`, `asari_only`, `masscube_only`
- verdicts: `agree_within_5pct`, `agree_within_20pct`, `disagree_low_internal`, `disagree_high_internal`, `third_party_missing_internal_present`, `internal_missing_third_party_present`, `boundary_mismatch`

- [x] **Step 2: Run tests and confirm failure**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p3_shadow_comparison_join.py -q
```

Expected: import failure because join module does not exist.

- [x] **Step 3: Implement join model, matcher, and writers**

Implement:

- `run_shadow_comparison_join(...)`
- TSV readers with required-column validation
- row-level matching by `(sample_stem, ppm, rt tolerance)`
- summary counts by `match_status` and `verdict`
- JSON and Markdown report writers

Default tolerances:

- `preferred_ppm=10.0`
- `max_rt_sec=6.0`
- boundary mismatch threshold `0.05 min`

- [x] **Step 4: Verify Task 2**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p3_shadow_comparison_join.py -q
```

Expected: Task 2 tests pass.

## Task 3: Third-Party Table Normalizers

**Files:**

- Create: `tools/diagnostics/third_party_shadow_tables.py`
- Create: `tests/test_p3_third_party_shadow_tables.py`
- Create or update: `tools/diagnostics/asari_shadow_runner.py`
- Create or update: `tools/diagnostics/masscube_shadow_runner.py`

- [x] **Step 1: Add failing tests for standardized table writing**

Tests should cover:

- normalized row writing to the standard schema
- parser accepts already-normalized TSV as a bypass path
- asari adapter can discover `preferred_Feature_table.tsv` or `export/full_Feature_table.tsv`
- optional native fields can remain empty with `native_schema_status=missing_optional_fields`
- MassCube adapter can discover a documented feature table path once actual output is known; before that, it reports `unsupported_native_output` rather than guessing

- [x] **Step 2: Run tests and confirm failure**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p3_third_party_shadow_tables.py -q
```

Expected: import failure because table normalizer does not exist.

- [x] **Step 3: Implement normalizers and thin runner wrappers**

Implement:

- `ThirdPartyFeatureRow`
- `read_standardized_feature_tsv(...)`
- `write_standardized_feature_tsv(...)`
- `normalize_asari_output(...)`
- `normalize_masscube_output(...)`
- asari runner wrapper that can call an explicit `--venv-python` and `--mzml-dir`, then normalize output if the expected table exists
- MassCube runner wrapper that writes a project scaffold under output and fails cleanly as `unsupported_native_output` until actual MassCube output schema is inspected

Do not import `asari` or `masscube` at module import time.

- [x] **Step 4: Verify Task 3**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p3_third_party_shadow_tables.py -q
```

Expected: Task 3 tests pass.

## Task 4: Isolated Environment And Real 8RAW Shadow Attempt

**Files / Outputs:**

- Write outputs under `output/phase1_p3_third_party_shadow_comparison/`
- Do not edit `pyproject.toml`
- Do not write dependencies into the main `.venv`

- [x] **Step 1: Build input manifest**

Run manifest against the user-provided mzML directory and current internal sample stems:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.p3_shadow_inputs `
  --internal-integration-audit-tsv output\phase1_p2_asls_shadow_validation\alignment\asls_shadow\alignment_cell_integration_audit.tsv `
  --mzml-dir "C:\Users\user\Desktop\NTU cancer\NTU Tissue preprocess\mzml" `
  --output-tsv output\phase1_p3_third_party_shadow_comparison\p3_shadow_input_manifest.tsv
```

Expected: all 8 internal samples have `status=present`.

- [x] **Step 2: Create isolated venv**

Use `C:\tmp\xic_p3_shadow_venv` or another non-repo path.

```powershell
uv venv C:\tmp\xic_p3_shadow_venv
```

- [x] **Step 3: Install third-party tools into isolated venv**

Install only into the isolated venv:

```powershell
C:\tmp\xic_p3_shadow_venv\Scripts\python.exe -m pip install asari-metabolomics masscube
```

If network/dependency install fails, record P3 as `inconclusive_external_install` and keep the join/report code.

- [x] **Step 4: Run asari against only the 8 validation mzML files**

Avoid accidentally processing all 87 files unless explicitly requested. Build a temporary 8-file mzML staging folder under `C:\tmp\xic_p3_mzml_8raw` with hard links to the selected validation files. If hard links fail, stop and ask before copying multi-GB mzML files.

Expected command shape from current docs:

```powershell
C:\tmp\xic_p3_shadow_venv\Scripts\python.exe -m asari.main process --mode pos --input C:\tmp\xic_p3_mzml_8raw --output output\phase1_p3_third_party_shadow_comparison\asari_run
```

If asari output schema differs from expected tables, inspect the produced files and patch the normalizer with tests before continuing.

- [x] **Step 5: Attempt MassCube only after sample-table/parameter requirements are explicit**

Installed MassCube source requires a project folder with `data/`; `sample_table.csv` and `parameters.csv` may be absent and default behavior is used. Do not guess unknown required columns. If no minimal no-annotation run can be confirmed locally, record `masscube_inconclusive_schema_or_runner`.

- [x] **Step 6: Join available third-party outputs**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.shadow_comparison_join `
  --internal-integration-audit-tsv output\phase1_p2_asls_shadow_validation\alignment\asls_shadow\alignment_cell_integration_audit.tsv `
  --targeted-istd-summary-tsv output\phase1_p2_asls_shadow_validation\diagnostics\targeted_istd_benchmark\targeted_istd_benchmark_summary.tsv `
  --asari-features-tsv output\phase1_p3_third_party_shadow_comparison\shadow_comparison_asari_8raw.tsv `
  --masscube-features-tsv output\phase1_p3_third_party_shadow_comparison\shadow_comparison_masscube_8raw.tsv `
  --output-dir output\phase1_p3_third_party_shadow_comparison
```

Missing third-party feature TSVs should degrade to pairwise/inconclusive output, not crash.

## Task 5: P3 Findings Note And Post-Implementation Review

**Files:**

- Create: `docs/superpowers/notes/2026-05-25-p3-third-party-shadow-findings.md`
- Update plan checklist as tasks complete

- [x] **Step 1: Write findings note**

The note must state:

- gate status: `diagnostic_only`, `shadow_ready`, or `inconclusive`
- mzML source directory and 8RAW coverage
- third-party tool versions if installed
- exact commands
- which third-party outputs were available
- top disagreements by target/sample/tool
- whether P2 AsLS matrix-hump evidence is supported, contradicted, or still inconclusive
- whether P6 OBI-Warp should be escalated

- [x] **Step 2: Run focused tests**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest `
  tests\test_p3_shadow_inputs.py `
  tests\test_p3_shadow_comparison_join.py `
  tests\test_p3_third_party_shadow_tables.py `
  tests\test_p2_baseline_truth_audit.py `
  tests\test_p2_asls_shadow_gate.py `
  -q
```

- [x] **Step 3: Run compile smoke**

Run:

```powershell
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m py_compile `
  tools\diagnostics\p3_shadow_inputs.py `
  tools\diagnostics\shadow_comparison_join.py `
  tools\diagnostics\third_party_shadow_tables.py `
  tools\diagnostics\asari_shadow_runner.py `
  tools\diagnostics\masscube_shadow_runner.py
```

- [x] **Step 4: Run diff hygiene**

Run:

```powershell
git diff --check
```

- [x] **Step 5: Post-implementation review**

Review for:

- RAW production contract drift
- accidental dependency additions
- third-party output schema overclaiming
- missing or misleading `inconclusive` statuses
- stale P2/P3/P2b wording

Patch defects directly and rerun focused verification.

## Stop Conditions

Stop and ask before continuing if:

- any step requires `.raw` -> `.mzML` conversion
- the only way to run a third-party tool is to install it into the main `.venv`
- asari/MassCube native output cannot be mapped without guessing required m/z/RT/area semantics
- optional native fields such as boundaries, S/N, or confidence are filled from undocumented or unrelated columns
- a third-party run would process all 87 mzML files when only 8RAW validation was intended
- P3 code would need to import optional third-party packages from `xic_extractor/`
- Cleanup C-spec scope becomes necessary
