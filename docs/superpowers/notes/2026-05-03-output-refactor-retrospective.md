# Output maintainability refactor retrospective

Date: 2026-05-03

Scope: PR1-PR3 of `docs/superpowers/plans/2026-05-03-output-maintainability-refactor.md`.

## Summary

The output pipeline moved from extractor-owned CSV/XLSX formatting toward explicit output adapters and Excel-first runtime behavior.

Merged PRs:

| PR | Merge SHA | Summary |
| --- | --- | --- |
| PR1 | `e17bf73` | Extracted output schema, CSV writers, diagnostic messages, and scoring factory helpers |
| PR2 | `5e7bf16` | Wrote Excel directly from in-memory extraction results and made CSV retention opt-in |
| PR3 | `f1573d8` | Added a collapsed GUI Advanced settings section for debug and method-development options |

## Line Count

| File | Before PR1 | After PR3 | Delta |
| --- | ---: | ---: | ---: |
| `xic_extractor/extractor.py` | 1420 | 696 | -724 |

The original final gate targeted `extractor.py <= 500` lines. That gate is not yet met. The remaining 696 lines are substantially smaller than the pre-refactor file, but another focused orchestration cleanup would be needed before treating the line-count gate as complete.

## Test Growth

Approximate test diff by PR:

| PR | Test files changed | Test insertions | Test deletions |
| --- | ---: | ---: | ---: |
| PR1 | 8 | 540 | 29 |
| PR2 | 9 | 675 | 23 |
| PR3 | 1 | 138 | 0 |

New test files added across PR1-PR3:

- `tests/test_csv_writers.py`
- `tests/test_excel_pipeline.py`
- `tests/test_excel_sheets_contract.py`
- `tests/test_messages.py`
- `tests/test_output_metadata.py`
- `tests/test_output_schema_contract.py`
- `tests/test_scoring_factory.py`
- `tests/test_settings_section_advanced.py`

Current local suite at the end of PR3: `360 passed, 1 skipped`.

## Workbook Contract

Default workbook sheets changed from the legacy conversion flow to an Excel-first contract:

| Mode | Sheet count | Sheets |
| --- | ---: | --- |
| Default | 7 | `Overview`, `Review Queue`, `XIC Results`, `Summary`, `Targets`, `Diagnostics`, `Run Metadata` |
| `emit_score_breakdown=true` | 8 | Default sheets plus `Score Breakdown` |

`Overview` is always the active sheet when the workbook opens, even when diagnostics are present.
`Review Queue` is a one-row-per-sample-target worklist, while `Summary` now includes target-health fields (`Flagged Rows`, `Flagged %`, `MS2/NL Flags`, `Low Confidence Rows`) before the existing detection and scoring counts.
`Detected %` answers whether a target produced usable RT/area rows; `Flagged %` answers how often rows require manual review. `Score Breakdown` is a technical audit sheet for scoring signals and should not be treated as the primary manual review queue.

## Output File Count

| Mode | Default output artifacts |
| --- | ---: |
| Before refactor | 5: wide CSV, long CSV, diagnostics CSV, score breakdown CSV when enabled, converted XLSX |
| After PR2/PR3 default | 1: timestamped XLSX |
| After PR2/PR3 debug CSV | XLSX plus CSV files when `keep_intermediate_csv=true`; CSV-only when CLI `--skip-excel` is used |

## Unexpected Findings

- Preserving `settings.csv` text formatting matters because `config_hash` is derived from settings bytes. GUI round-trips must avoid normalizing untouched advanced numeric strings such as `25.0` to `25`.
- Full 85-RAW real-data validation is too slow for ordinary PR gates. The plan now treats `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation` as the PR-level smoke subset.
- `ruff check .` still reports pre-existing long lines in legacy scripts outside the P1-P3 diff. Changed GUI/output files pass scoped lint.
- The refactor clarified that daily users should review Excel workbook sheets, while CSV files are debug/downstream compatibility artifacts.

## Maintainer Rules

- Output schema changes should go through `xic_extractor/output/schema.py`.
- New settings should start in the GUI Advanced section until there is evidence they are routine daily controls.
- Do not expand CSV headers for reproducibility metadata; use the workbook `Run Metadata` sheet.
