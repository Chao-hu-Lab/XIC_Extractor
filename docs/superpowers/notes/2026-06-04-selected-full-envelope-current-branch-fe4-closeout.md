# Selected Full-Envelope Current-Branch FE4 Closeout

**Date:** 2026-06-04
**Readiness label:** `diagnostic_only`
**Run status:** `run_ok`
**Gate status:** `externalize`

## Decision

Current-branch FE4 evidence does not support selected full-envelope product
wiring or production-ready quantitation-boundary promotion.

The current implementation can recover clipped flanks on many clean rows, but
the same 8RAW run still exposes unresolved boundary risks that must remain
diagnostic/review-only:

- selected envelopes can become narrower than the resolver interval;
- selected-envelope expansion can encounter split or shoulder evidence;
- a stronger context apex can exist outside the selected envelope.

These are boundary/selection risks, not AsLS baseline failures. They are exactly
the cases that need plot-backed expert review before any primary matrix switch.

## Current 8RAW Output

Output root:

```text
output/selected_full_envelope_realdata_preflight/fe4_8raw_selected_envelope_current_branch_20260604/
```

Primary artifacts:

```text
tissue_8raw_region_first_safe_merge/xic_results_process_w4.xlsx
tissue_8raw_region_first_safe_merge/selected_envelope_diagnostics.tsv
selected_envelope_review_queue/selected_envelope_changed_rows.tsv
selected_envelope_review_queue/selected_envelope_oracle_review_queue.tsv
selected_envelope_review_queue/selected_envelope_diagnostic_manifest.tsv
selected_envelope_review_queue/selected_envelope_review_queue.json
selected_envelope_plot_review/selected_envelope_plot_index.tsv
selected_envelope_plot_review/plots/
validation_summary.csv
```

Manifest:

```text
gate_decision=externalize
changed_row_count=95
changed_row_denominator=95
high_risk_strata=context_apex_conflict;overmerge_rejected;split_supported
unresolved_blocker_count=29
blocked_reasons=selected_envelope_narrower_than_resolver;split_supported_review_required;stronger_context_apex_outside_envelope
next_gate=diagnostic_review_only
```

Distribution:

```text
row_boundary_decision / boundary_change_class / boundary_stop_reason:
  66 accept_candidate / flank_recovered / baseline_return_reached
  16 externalize / overmerge_rejected / selected_envelope_narrower_than_resolver
   7 externalize / split_supported / split_supported_review_required
   6 externalize / context_apex_conflict / stronger_context_apex_outside_envelope
```

Representative plot-backed findings:

```text
TumorBC2263_DNA / 8-oxodG:
  decision=externalize
  class=overmerge_rejected
  reason=selected_envelope_narrower_than_resolver
  resolver=15.98230-16.80756
  envelope=16.27104-16.93184
  area_delta_ratio=-0.00713
  plot=selected_envelope_plot_review/plots/26_high_risk_externalized_TumorBC2263_DNA_8_oxodG.png

Breast_Cancer_Tissue_pooled_QC5 / 8-oxodG:
  decision=externalize
  class=context_apex_conflict
  reason=stronger_context_apex_outside_envelope
  resolver=16.21219-16.40116
  envelope=15.37481-17.20159
  area_delta_ratio=97.57473
  plot=selected_envelope_plot_review/plots/01_high_risk_externalized_Breast_Cancer_Tissue_pooled_QC5_8_oxodG.png

BenignfatBC1055_DNA / N6-medA:
  decision=accept_candidate
  class=flank_recovered
  reason=baseline_return_reached
  resolver=26.19740-26.23889
  envelope=25.98967-26.44638
  area_delta_ratio=1.00086
  plot=selected_envelope_plot_review/plots/30_accepted_area_increase_BenignfatBC1055_DNA_N6_medA.png
```

## Commands

Preflight:

```powershell
Test-Path "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation"
Test-Path "C:\Xcalibur\system\programs"
.venv\Scripts\python.exe --version
.venv\Scripts\python.exe -c "import importlib.util; print('pythonnet', importlib.util.find_spec('pythonnet') is not None); print('pytest', importlib.util.find_spec('pytest') is not None)"
python -m scripts.agent_sandbox_doctor --strict --command ".venv\Scripts\python.exe scripts\validation_harness.py --suite tissue-8raw --base-dir C:\Users\user\Desktop\XIC_Extractor --output-root output\selected_full_envelope_realdata_preflight --run-id fe4_8raw_selected_envelope_current_branch_20260604 --resolver-mode region_first_safe_merge --parallel-mode process --parallel-workers 4 --data-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --setting emit_peak_candidates=true"
```

Observed:

```text
RAW dir exists = True
DLL dir exists = True
.venv python = 3.13.7
pythonnet = True
pytest = True
sandbox doctor status = ok
```

8RAW run:

```powershell
.venv\Scripts\python.exe scripts\validation_harness.py --suite tissue-8raw --base-dir C:\Users\user\Desktop\XIC_Extractor --output-root output\selected_full_envelope_realdata_preflight --run-id fe4_8raw_selected_envelope_current_branch_20260604 --resolver-mode region_first_safe_merge --parallel-mode process --parallel-workers 4 --data-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --setting emit_peak_candidates=true
```

Observed:

```text
tissue-8raw: passed, compare=not_requested
```

Review queue packaging:

```powershell
python tools\diagnostics\selected_envelope_review_queue.py --selected-envelope-diagnostics-tsv output\selected_full_envelope_realdata_preflight\fe4_8raw_selected_envelope_current_branch_20260604\tissue_8raw_region_first_safe_merge\selected_envelope_diagnostics.tsv --output-dir output\selected_full_envelope_realdata_preflight\fe4_8raw_selected_envelope_current_branch_20260604\selected_envelope_review_queue
```

Observed:

```text
Rows: 95; changed: 95; oracle queue: 95; gate: externalize
```

Plot review:

```powershell
.venv\Scripts\python.exe tools\diagnostics\selected_envelope_plot_review.py --selected-envelope-diagnostics-tsv output\selected_full_envelope_realdata_preflight\fe4_8raw_selected_envelope_current_branch_20260604\tissue_8raw_region_first_safe_merge\selected_envelope_diagnostics.tsv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --config-dir config --output-dir output\selected_full_envelope_realdata_preflight\fe4_8raw_selected_envelope_current_branch_20260604\selected_envelope_plot_review --max-high-risk 29 --max-accepted-increase 10 --max-accepted-decrease 10
```

Observed:

```text
Plot index TSV: selected_envelope_plot_review/selected_envelope_plot_index.tsv
Plot directory: selected_envelope_plot_review/plots
```

## Verification

Focused selected-envelope gate:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_selected_full_envelope_policy.py tests/test_selected_full_envelope_diagnostics.py tests/test_selected_full_envelope_projection.py tests/test_selected_full_envelope_oracle.py tests/test_selected_full_envelope_oracle_artifacts.py tests/test_selected_full_envelope_changed_row_review.py tests/test_selected_envelope_review_queue.py tests/test_selected_envelope_plot_review.py
```

Observed:

```text
86 passed
```

## Next Gate

Do not run 85RAW and do not wire `asls_area_selected_envelope` into product
matrix behavior from this state.

The next bounded work is manual/expert review or policy refinement over the
29 blocked high-risk rows, with special attention to:

- whether `selected_envelope_narrower_than_resolver` should remain a hard
  externalization or become a stricter area-decrease/visual-boundary rule;
- whether `context_apex_conflict` is an identity/model-selection issue rather
  than a boundary-policy blocker for targeted rows with strong role-aware RT
  evidence;
- whether `split_supported` rows need a separate overlap/deconvolution research
  slice instead of selected-envelope promotion.
