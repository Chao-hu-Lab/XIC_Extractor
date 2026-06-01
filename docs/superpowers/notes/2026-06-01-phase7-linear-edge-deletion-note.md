# Phase 7 Linear-Edge Deletion Note

Status: `C1B_LINEAR_EDGE_DELETION_COMPLETE`

Verdict:

- Maintained production selector support for `linear_edge` baseline integration
  has been retired.
- Old public input behavior is rejection, not aliasing:
  `baseline_integration_method=linear_edge`,
  `--baseline-integration-method linear_edge`, and
  `BASELINE_INTEGRATION_METHOD=linear_edge` raise or return an actionable
  message: `linear_edge baseline integration is retired; use asls`.
- AsLS remains the only accepted production baseline integration method.

Behavior changes:

- `integrate_linear_edge_baseline` is deleted from the production
  `xic_extractor.peak_detection.baseline` API.
- `BaselineMethod` is now `Literal["asls"]`.
- The alignment audit writer and cell integration audit builder reject
  `baseline_integration_method="linear_edge"`.
- Config validation rejects `baseline_integration_method=linear_edge`.
- `scripts/run_alignment.py` rejects both CLI and environment variable
  `linear_edge` overrides before calling `run_alignment`.
- If an AsLS baseline cannot be fit, the integration audit returns the empty
  audit sentinel instead of falling back to linear edge.

Residual `linear_edge` references:

- Production/package references are limited to rejection messages and validation
  checks for retired public input.
- Tests retain `linear_edge` strings only as regression coverage for rejection,
  removed rollback columns, and historical retirement evidence.
- `tools/diagnostics/asls_truth_validation_synthetic.py` retains a local
  `_integrate_historical_linear_edge_baseline` comparator strictly for locked
  retirement evidence. It does not provide product selector support.
- Existing AsLS truth-validation and P2 diagnostic readers continue to accept
  historical comparator columns such as `area_baseline_corrected_linear_edge`
  when reading old artifacts.

Focused verification:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\peak_detection\baseline.py xic_extractor\peak_detection\integration_audit.py xic_extractor\alignment\tsv_writer.py xic_extractor\configuration\settings.py xic_extractor\settings_schema.py scripts\run_alignment.py tools\diagnostics\asls_truth_validation_synthetic.py tests\test_baseline_integration.py tests\test_config.py tests\test_run_alignment.py tests\test_peak_hypotheses.py tests\test_handoff_spine_runtime.py tests\test_alignment_tsv_writer.py tests\test_alignment_pipeline_outputs.py
```

Observed result: `All checks passed!`

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_baseline_integration.py tests\test_config.py tests\test_run_alignment.py tests\test_peak_hypotheses.py tests\test_handoff_spine_runtime.py tests\test_alignment_tsv_writer.py tests\test_alignment_pipeline_outputs.py tests\test_asls_truth_validation_synthetic.py
```

Observed result: `206 passed`.

Scan evidence:

```powershell
rg -n "integrate_linear_edge_baseline" xic_extractor scripts tests tools
```

Observed result:

- No production/package caller remains.
- The only hit is the regression test that scans `xic_extractor/` for the
  deleted helper name.

```powershell
rg -n "baseline_integration_method.*linear_edge|--baseline-integration-method.*linear_edge|BASELINE_INTEGRATION_METHOD.*linear_edge" xic_extractor scripts tests tools
```

Observed result:

- Hits are limited to retired-input rejection checks and tests.

