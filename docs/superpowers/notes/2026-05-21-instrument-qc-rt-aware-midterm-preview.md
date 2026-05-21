# Instrument QC RT-Aware Midterm Preview

**Date:** 2026-05-21
**Branch:** `codex/instrument-qc-trend`
**Decision:** `rt_aware_audit_alignment_support`

## Scope

Midterm calibration is allowed only as RT-aware audit / alignment support.

This phase may produce:

- local RT model rows;
- leave-one-anchor-out validation;
- matrix RT preview sidecars;
- local residual and coverage labels;
- iRT-like anchor scope / position evidence.

This phase must not change:

- final untargeted matrix values;
- `alignment_matrix.tsv`;
- `alignment_review.tsv`;
- targeted reliability;
- peak scoring;
- resolver behavior;
- matrix identity / production gates.

## Implemented Contract

When `instrument_qc_matrix_calibration_preview.py` is run with
`--preview-kind rt` or `both`, it now writes:

- `instrument_qc_rt_drift_model.tsv`
- `instrument_qc_rt_drift_model_summary.json`
- `instrument_qc_rt_leave_one_anchor_out.tsv`
- `matrix_rt_calibration_preview.tsv`
- `matrix_rt_calibration_preview_summary.json`

The matrix preview keeps the source matrix/cell table read-only and adds
alignment-support fields:

- `coverage_status`
- `rt_alignment_support_status`
- `local_anchor_count`
- `local_clean_anchor_count`
- `local_biological_istd_anchor_count`
- `local_residual_p95_min`
- `irt_anchor_scope`
- `irt_position`

## Interpretation

`irt_anchor_scope` and `irt_position` are not hard gates. They describe where a
feature sits relative to the observed standard RT axis:

- `inside_anchor_range`: the feature is bracketed by calibration RT anchors.
- `before_anchor_range` / `after_anchor_range`: the feature is extrapolated.
- `single_anchor_rt` / `no_rt_anchors`: iRT-like interpretation is not stable.

`coverage_status` is the practical review label:

- `covered`: local anchors support the cell RT/order position.
- `sparse`: local evidence exists but is limited.
- `extrapolated`: the cell is outside RT or injection-order coverage.
- `incomplete`: source cell RT or docs-derived injection order is missing.
- `unsupported`: no usable RT anchor evidence exists.

## Current Product Boundary

The preview computes `rt_if_standard_corrected_min`, but the correction status
is `shadow_only` when a local model exists. This is intentional: the value is
for alignment review and future gate design, not for exported matrix mutation.

The next promotion decision still requires biological QC ISTD transfer evidence
from current-code targeted artifacts.

## Standard Source And Biological-Sample Expectation

The standard sources have different meanings and must not be collapsed into one
biological detection expectation.

- SDO/LEK is an independent standard set. It is expected only in dedicated pure
  SDO/LEK injections, not in biological samples.
- Mix STDs contains the internal and external standards. It includes ISTDs that
  are also added to biological samples, plus deliberately prepared external
  standards.
- Non-ISTD Mix STDs entries are external standards. They provide clean-matrix
  instrument-QC evidence, but they are not expected to be stably detected across
  biological samples.
- All biological samples receive ISTDs. Therefore, ISTDs are the biological-run
  benchmark for real-matrix transfer.
- SDO/LEK and Mix STDs are prepared in clean matrix. Real biological samples
  include matrix interference, so clean-standard behavior must not be treated as
  direct biological-sample truth.

Therefore, a clean-standard RT model can support review only after biological QC
ISTDs confirm that the drift pattern transfers into biological matrix.

## 8RAW Smoke Result

Command:

```powershell
uv --cache-dir .uv-cache run python tools\diagnostics\instrument_qc_matrix_calibration_preview.py `
  --instrument-qc-dir output\instrument_qc\hcd_audit_v1_sdolek_whcd_review_20260520 `
  --matrix-input output\alignment\instrument_qc_calibration_level1_8raw_20260521\alignment_cells.tsv `
  --matrix-input-role untargeted_cell_table `
  --preview-kind rt `
  --output-dir output\diagnostics\instrument_qc_rt_aware_midterm_level1_8raw_20260521
```

Observed:

- RT anchors: 208 total (`mixstds`: 192; `sdolek`: 16).
- Matrix preview coverage: `covered` 17266 cells, `sparse` 54 cells,
  `extrapolated` 1080 cells.
- Leave-one-anchor-out: `PASS` 107, `WARN` 41, `FAIL` 60.
- LOAO median absolute error: 0.1460 min.
- LOAO p95 absolute error: 0.6330 min.

Decision:

- The product can enter midterm as **RT-aware audit / alignment-support**.
- The current anchor set is not production-correction ready because LOAO p95 is
  still high and failures concentrate in specific standards / RT windows.
- iRT-like evidence is useful as a coverage/residual explanation layer, not yet
  as a hard correction or matrix mutation.

Next review focus:

- inspect LOAO failures such as `t6A`, `Etheno-dA`, `5-hmdC`, and late/early
  Mix STDs anchors;
- decide whether those are stale RT priors, broad windows, local selection
  mistakes, or true instrument drift;
- add current-code biological QC ISTD transfer evidence before any production
  RT correction.

## Research Follow-Up

The next analysis split the standards by intended use instead of treating every
standard as a biological-sample expectation.

LOAO status by source:

- Mix STDs: `PASS` 94, `WARN` 38, `FAIL` 60.
- SDO/LEK: `PASS` 13, `WARN` 3, `FAIL` 0.

This means the current high LOAO failure count is not a global instrument-QC
collapse. It is concentrated in Mix STDs rows and likely reflects a mix of
compound-specific RT behavior, target prior/window issues, and selected-peak
review cases.

Notable LOAO failure concentrations:

- `d3-N6-medA`, `d3-5-hmdC`, `t6A`, `ncm5U`, `N6-medA`, and `hm5C`: 4 failures
  each.
- `5-hmdC` and `Etheno-dA`: 3 failures each.

Manual review update:

- `d3-N6-medA` QC1/QC2 EICs are valid early-injection true-drift peaks.
- The original targeted reliability demotion was caused by RT-prior/window
  gating, not by weak MS1/MS2/NL evidence.
- After the targeted RT-gate fix, `d3-N6-medA` becomes `85/85`
  `benchmark_eligible` in:
  `output\diagnostics\instrument_qc_bio_istd_85raw_after_rt_gate_fix_20260521\targeted_reliability\targeted_peak_reliability_summary.tsv`.

Clean-to-biological ISTD transfer evidence is more useful than external-standard
coverage for biological matrix interpretation:

| ISTD | Biological QC RT range (min) | Biological slope (min/inj) | Clean slope (min/inj) | Interpretation |
| --- | ---: | ---: | ---: | --- |
| `15N5-8-oxodG` | 0.609 | -0.0048 | -0.0025 | Same direction; clean standard underestimates magnitude. |
| `[13C,15N2]-8-oxo-Guo` | 0.748 | -0.0050 | -0.0022 | Same direction; useful as ISTD evidence when this tag is in scope. |
| `d3-5-hmdC` | 0.887 | -0.0050 | -0.0001 | Biological drift is not captured by clean-standard slope. |
| `d3-5-medC` | 0.941 | 0.0087 | 0.0094 | Strong direction and magnitude agreement. |
| `d3-N6-medA` | 2.119 | 0.0205 | 0.0110 | Same direction, but biological matrix shows much larger drift. |
| `d4-N1-2HE-dA` | 0.917 | 0.0088 | 0.0086 | Strong direction and magnitude agreement. |
| `d4-N6-2HE-dA` | 0.917 | 0.0088 | 0.0086 | Strong direction and magnitude agreement. |

Current interpretation:

- SDO is stable and supports system suitability.
- LEK has a stable direction/offset pattern in the clean SDO/LEK set; it should
  be interpreted inside that dedicated standard context, not as biological
  evidence.
- Mix STDs provides useful clean-matrix anchors, but non-ISTD external standards
  must not be used as biological-sample expected detections.
- Biological QC ISTDs show that some clean-standard RT trends transfer
  directionally into biological samples, but matrix effects can change magnitude
  substantially.

Midterm conclusion remains unchanged:

- Proceed with RT-aware audit / alignment-support.
- Do not promote this to production RT correction, production area correction,
  or matrix mutation.
- Next evidence step should compare current-code biological QC ISTD residuals
  against the local clean-standard model and flag target-specific transfer
  quality: `transfer_supported`, `direction_supported_magnitude_shifted`,
  `transfer_not_supported`, or `insufficient_biological_istd`.

## Biological ISTD Transfer Audit

The transfer check is now a focused diagnostic with clean module boundaries:

- domain classifier:
  `xic_extractor/instrument_qc/rt_transfer_audit.py`
- TSV / JSON / Markdown adapter:
  `xic_extractor/instrument_qc/rt_transfer_audit_io.py`
- thin CLI wrapper:
  `tools/diagnostics/instrument_qc_biological_istd_transfer_audit.py`

Command:

```powershell
uv --cache-dir .uv-cache run python tools\diagnostics\instrument_qc_biological_istd_transfer_audit.py `
  --clean-standard-summary-tsv output\diagnostics\instrument_qc_midterm_evidence_20260521\clean_standard_rt_response_summary.tsv `
  --biological-qc-istd-summary-tsv output\diagnostics\instrument_qc_midterm_evidence_20260521\biological_qc_istd_drift_summary.tsv `
  --istd-scope provided_biological_qc_istd_summary_rows `
  --output-dir output\diagnostics\instrument_qc_biological_istd_transfer_audit_20260521
```

Outputs:

- `biological_istd_rt_transfer_audit.tsv`
- `biological_istd_rt_transfer_audit.json`
- `biological_istd_rt_transfer_audit.md`

Result:

- `transfer_supported`: 3
- `direction_supported_magnitude_shifted`: 2 in the original audit; 3 after
  the targeted RT-gate fix.
- `transfer_not_supported`: 1
- `insufficient_biological_istd`: 1 in the original audit; 0 after the
  targeted RT-gate fix.
- `istd_scope`: `provided_biological_qc_istd_summary_rows`
- updated audit:
  `output\diagnostics\instrument_qc_biological_istd_transfer_after_rt_gate_fix_20260521\biological_istd_rt_transfer_audit.tsv`

Per-ISTD interpretation:

- `d3-5-medC`, `d4-N1-2HE-dA`, `d4-N6-2HE-dA`: clean-standard RT trend
  transfers to biological QC ISTDs in both direction and magnitude.
- `15N5-8-oxodG`, `[13C,15N2]-8-oxo-Guo`: direction transfers, but biological
  matrix roughly doubles the apparent RT drift magnitude.
- `d3-5-hmdC`: biological QC shows RT drift, but clean-standard slope is
  effectively flat; clean-standard correction should not be trusted for this
  target without more evidence.
- `d3-N6-medA`: direction appears consistent. Manual review confirmed the two
  early QC points are real drift, and the targeted RT-gate fix restores them as
  benchmark-eligible. Updated status is `direction_supported_magnitude_shifted`:
  direction agrees, but biological matrix drift magnitude is larger than clean
  standards.

This strengthens the midterm scope: RT-aware evidence can support alignment
review for specific ISTD-backed regions, but target-level transfer quality must
be explicit. A single global clean-standard RT correction is still not justified.

## Mid/Long-Term Maturity Gate

The spec's Level 2 through Level 5 goals are now represented by a machine-
readable go/no-go diagnostic.

Command:

```powershell
uv --cache-dir .uv-cache run python tools\diagnostics\instrument_qc_calibration_maturity_gate.py `
  --rt-model-summary-json output\diagnostics\instrument_qc_rt_aware_midterm_level1_8raw_20260521\instrument_qc_rt_drift_model_summary.json `
  --matrix-rt-preview-summary-json output\diagnostics\instrument_qc_rt_aware_midterm_level1_8raw_20260521\matrix_rt_calibration_preview_summary.json `
  --matrix-rt-preview-tsv output\diagnostics\instrument_qc_rt_aware_midterm_level1_8raw_20260521\matrix_rt_calibration_preview.tsv `
  --biological-istd-transfer-json output\diagnostics\instrument_qc_biological_istd_transfer_audit_20260521\biological_istd_rt_transfer_audit.json `
  --output-dir output\diagnostics\instrument_qc_calibration_maturity_gate_20260521
```

Outputs:

- `instrument_qc_calibration_maturity_gate.tsv`
- `instrument_qc_calibration_maturity_gate.json`
- `instrument_qc_calibration_maturity_gate.md`

Maturity decisions:

| Level | Decision | Evidence |
| --- | --- | --- |
| Level 2: RT-aware audit / alignment-support | `go` | After targeted RT-gate fix: `shadow_only=6279`; informative ISTD transfer rows = 6; scope = `provided_biological_qc_istd_summary_rows_after_rt_gate_fix`. |
| Level 3: RT production candidate | `no_go` | After targeted RT-gate fix: LOAO fail count = 60; LOAO p95 = 0.633 min; `transfer_not_supported=1`; extrapolated matrix RT rows = 1080; blocked matrix RT rows = 1434. |
| Level 4: response shadow candidate | `no_go` | response model and biological response transfer audit are not implemented yet. |
| Level 5: response production candidate | `no_go` | Level 4 is not ready and downstream compatibility evidence is missing. |

Current product decision:

- Proceed with Level 2 only.
- Treat local RT / iRT evidence as alignment-support and review-prioritization
  evidence.
- Do not emit production-corrected RT, area, response, reliability, or matrix
  outputs.
- The next research target, if continued, should be response shadow evidence,
  not production correction.
