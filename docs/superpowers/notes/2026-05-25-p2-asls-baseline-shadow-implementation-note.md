# P2 AsLS Baseline Shadow Implementation Note

**Date:** 2026-05-25
**Branch:** codex/peak-pipeline-modernization
**Worktree:** .worktrees/peak-pipeline-modernization
**Gate status:** diagnostic_only

## Decision

- P2 implementation status: implemented for unit and contract testing.
- Production `area_baseline_corrected` remains linear-edge.
- AsLS is emitted only as audit shadow columns when `baseline_audit_method=asls`, `--emit-baseline-audit-asls`, or `BASELINE_AUDIT_METHOD=asls` is set.
- P2 is not a production promotion. P2b remains required before Cleanup can assume AsLS production.

## Changed Files

- `xic_extractor/peak_detection/baseline.py`
- `xic_extractor/peak_detection/integration_audit.py`
- `xic_extractor/peak_detection/region_audit.py`
- `xic_extractor/alignment/tsv_writer.py`
- `xic_extractor/alignment/pipeline_outputs.py`
- `xic_extractor/alignment/pipeline.py`
- `xic_extractor/configuration/models.py`
- `xic_extractor/configuration/settings.py`
- `xic_extractor/settings_schema.py`
- `config/settings.example.csv`
- `scripts/run_alignment.py`
- `tools/diagnostics/p2_asls_shadow_gate.py`
- `tests/test_baseline_integration.py`
- `tests/test_alignment_tsv_writer.py`
- `tests/test_alignment_pipeline_outputs.py`
- `tests/test_alignment_process_backend.py`
- `tests/test_run_alignment.py`
- `tests/test_config.py`
- `tests/test_p2_asls_shadow_gate.py`

## Verification

- Focused pytest:
  `C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_baseline_integration.py tests\test_alignment_tsv_writer.py tests\test_alignment_pipeline_outputs.py tests\test_alignment_process_backend.py tests\test_run_alignment.py tests\test_config.py tests\test_p2_asls_shadow_gate.py -q`
  Result: `157 passed in 3.37s`
- Compile smoke:
  `C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m py_compile xic_extractor\peak_detection\baseline.py xic_extractor\peak_detection\integration_audit.py xic_extractor\peak_detection\region_audit.py xic_extractor\alignment\tsv_writer.py xic_extractor\alignment\pipeline_outputs.py xic_extractor\alignment\pipeline.py xic_extractor\configuration\models.py xic_extractor\configuration\settings.py xic_extractor\settings_schema.py scripts\run_alignment.py tools\diagnostics\p2_asls_shadow_gate.py`
  Result: exit code `0`

## Remaining Real-Data Risk

- 8RAW AsLS shadow alignment and P2 diagnostic gate are not recorded in this implementation note.
- Real-data status remains `diagnostic_only` until the validation note records the 8RAW shadow gate.

## Post-Implementation Review

- Reviewer finding fixed: `p2_asls_shadow_gate` now requires `coverage_denominator_count` from the targeted ISTD benchmark summary and fails with `shadow_coverage_incomplete` when valid shadow rows are fewer than the benchmark denominator.
- Reviewer finding fixed: diagnostic tests now cover `area_rsd_regression` and CLI exit codes `0`, `1`, and `2`.
- Final `git diff --check`: exit code `0` with LF-to-CRLF warnings only.
