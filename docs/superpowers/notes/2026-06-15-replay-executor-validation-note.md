# Replay executor 8RAW validation note

日期: 2026-06-15
狀態: `run_ok`, `gate_ok` for targeted 8RAW and 85RAW CSV/workbook replay parity; not full exact artifact replay

## Decision closed

`xic-extractor-cli --replay-manifest` can replay real targeted 8RAW
extractions from `method_manifest.json`.

- CSV-only replay reproduces the analytical CSV sidecars byte-for-byte.
- Excel-mode replay reproduces the analytical workbook sheets under the
  existing workbook comparison contract.

This validates the replay executor surface on the historical tissue 8RAW
validation subset and one full 85RAW tissue run. It does not validate GUI
parity or timestamped workbook hash replay.

## CSV-only fixture

- RAW set: `tissue-8raw`
- RAW path: `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation`
- DLL path: `C:\Xcalibur\system\programs`
- Python runner: `.venv\Scripts\python.exe`
- Base dir: `output\replay_executor_validation_20260615_152153`
- Config source: copied repo `config\settings.csv` and `config\targets.csv`
- Runtime: `process`, `parallel_workers=4`
- Output mode: `csv_only`

## Commands

Initial run:

```powershell
.venv\Scripts\python.exe -m scripts.run_extraction `
  --base-dir output\replay_executor_validation_20260615_152153 `
  --data-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
  --skip-excel `
  --parallel-mode process `
  --parallel-workers 4
```

Replay run:

```powershell
.venv\Scripts\python.exe -m scripts.run_extraction `
  --replay-manifest output\replay_executor_validation_20260615_152153\output\method_manifest.json
```

Runtime override rejection smoke:

```powershell
.venv\Scripts\python.exe -m scripts.run_extraction `
  --replay-manifest output\replay_executor_validation_20260615_152153\output\method_manifest.json `
  --skip-excel
```

This returned `LASTEXITCODE=2` with:

```text
--replay-manifest cannot be combined with --skip-excel
```

## Results

Both initial and replay runs processed `8` RAW files and emitted `155`
diagnostic rows.

Analytical CSV sidecars matched byte-for-byte:

| File | SHA256 | Bytes |
|---|---:|---:|
| `xic_results.csv` | `F1783E22AF31B92F99938FDA9420B8A3A1671BB17587A4EECD936A83E16EF168` | 6763 |
| `xic_results_long.csv` | `1E12B40656DF3585BA46494F67F34D003AC182D17848CBC40B3CAEBAABEF6FBC` | 74663 |
| `xic_diagnostics.csv` | `CC4579357F1DC6800EA0624AB41630B125335FDD18A18E879848A69B2B2E2C20` | 30918 |

Replay manifest after replay:

- `invocation.entrypoint = xic-extractor-cli-replay`
- `invocation.output_mode = csv_only`
- `method_settings.parallel_mode = process`
- `method_settings.parallel_workers = 4`
- `replay_status.capability = manifest_driven_cli_replay`
- `replay_status.exact_replay_ready = false`
- `replay_status.blockers = timestamped_workbook_hash_not_recorded`

## Interpretation

This is enough to treat the replay executor as a `production_surface` for
targeted CLI replay on the 8RAW validation subset.

## Excel-mode fixture

- RAW set: `tissue-8raw`
- RAW path: `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation`
- DLL path: `C:\Xcalibur\system\programs`
- Python runner: `.venv\Scripts\python.exe`
- Base dir: `output\replay_executor_excel_validation_20260615_152658`
- Runtime: `process`, `parallel_workers=4`
- Output mode: `excel`

Initial run:

```powershell
.venv\Scripts\python.exe -m scripts.run_extraction `
  --base-dir output\replay_executor_excel_validation_20260615_152658 `
  --data-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
  --parallel-mode process `
  --parallel-workers 4
```

Replay run:

```powershell
.venv\Scripts\python.exe -m scripts.run_extraction `
  --replay-manifest output\replay_executor_excel_validation_20260615_152658\output\method_manifest.json
```

Workbook compare:

```powershell
python -m scripts.compare_workbooks `
  output\replay_executor_excel_validation_20260615_152658\first_run_snapshot\xic_results_20260615_1527.xlsx `
  output\replay_executor_excel_validation_20260615_152658\output\xic_results_20260615_1528.xlsx
```

Result:

```text
Workbook compare passed.
```

The first workbook compare attempt correctly exposed a validation-tooling gap:
`Run Metadata.method_manifest_sha256` changes after replay because replay
rewrites the manifest. `scripts.compare_workbooks` now ignores
`method_manifest_path` and `method_manifest_sha256` as runtime metadata while
still comparing `method_manifest_schema`.

## 85RAW fixture

- RAW set: `tissue-85raw`
- RAW path: `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R`
- DLL path: `C:\Xcalibur\system\programs`
- Python runner: `.venv\Scripts\python.exe`
- Base dir: `output\replay_executor_85raw_validation_20260615_164051`
- Config source: copied repo `config\settings.csv` and `config\targets.csv`
- Config adjustment in isolated copy: `keep_intermediate_csv=true`
- Runtime: `process`, `parallel_workers=11`
- Output mode: `excel`

Initial run:

```powershell
.venv\Scripts\python.exe -m scripts.run_extraction `
  --base-dir output\replay_executor_85raw_validation_20260615_164051 `
  --data-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R" `
  --parallel-mode process `
  --parallel-workers 11
```

Replay run:

```powershell
.venv\Scripts\python.exe -m scripts.run_extraction `
  --replay-manifest output\replay_executor_85raw_validation_20260615_164051\output\method_manifest.json
```

Both runs processed `85` RAW files and emitted `1715` diagnostic rows.

Analytical CSV sidecars matched byte-for-byte:

| File | SHA256 | Bytes |
|---|---:|---:|
| `xic_results.csv` | `1AA5C9C86D26C68C55522DFCC9BF4AD3B4E227DDFE21ED6F3ECA93DC46C1DF31` | 54842 |
| `xic_results_long.csv` | `12C663CA6F40933389A81BEA1316376717A04BD04ED1744876C9F46636BBC8BE` | 779986 |
| `xic_diagnostics.csv` | `59D3572A85F0F2596388C9374D34628320DF1660FBF722AAFCBB4934A34FC135` | 339765 |

Workbook compare:

```powershell
python -m scripts.compare_workbooks `
  output\replay_executor_85raw_validation_20260615_164051\first_run_snapshot\xic_results_20260615_1643.xlsx `
  output\replay_executor_85raw_validation_20260615_164051\output\xic_results_20260615_1646.xlsx
```

Result:

```text
Workbook compare passed.
```

Replay manifest after replay:

- `invocation.entrypoint = xic-extractor-cli-replay`
- `invocation.output_mode = excel`
- `method_settings.keep_intermediate_csv = true`
- `method_settings.parallel_mode = process`
- `method_settings.parallel_workers = 11`
- `replay_status.capability = manifest_driven_cli_replay`
- `replay_status.exact_replay_ready = false`
- `replay_status.blockers = timestamped_workbook_hash_not_recorded`

## Remaining risk

This is enough to treat the targeted CLI replay executor as validated on 8RAW
and 85RAW for CSV and workbook analytical parity.

It is not enough to claim full exact artifact replay because:

- timestamped workbook hash capture is still absent;
- GUI-generated manifest replay parity has not run because GUI replay is not yet
  connected to the mainline surface.
