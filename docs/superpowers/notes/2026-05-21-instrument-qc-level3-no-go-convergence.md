# Instrument QC Level 3 NO-GO Convergence

## Scope

This note narrows the Level 3 `rt_production_candidate` NO-GO result from the
mid/long-term calibration gate. It uses the current 8RAW diagnostic artifacts:

- `output\diagnostics\instrument_qc_rt_aware_midterm_level1_8raw_20260521\instrument_qc_rt_drift_model_summary.json`
- `output\diagnostics\instrument_qc_rt_aware_midterm_level1_8raw_20260521\instrument_qc_rt_leave_one_anchor_out.tsv`
- `output\diagnostics\instrument_qc_rt_aware_midterm_level1_8raw_20260521\matrix_rt_calibration_preview.tsv`
- `output\diagnostics\instrument_qc_biological_istd_transfer_audit_20260521\biological_istd_rt_transfer_audit.tsv`
- `output\diagnostics\instrument_qc_calibration_maturity_gate_20260521\instrument_qc_calibration_maturity_gate.tsv`

The conclusion remains audit-only. This note does not approve production RT
correction, response correction, scoring changes, matrix identity changes, or
DNP normalization changes.

## Level 3 Result

Level 3 remains `NO-GO`.

Machine-readable blockers:

- `loao_fail_count=60`
- `loao_p95_abs_error_min=0.633035`
- `transfer_not_supported=1`
- `matrix_rt_extrapolated_rows=1080`
- `matrix_rt_blocked_rows=1434`

After manual review and the targeted reliability RT-gate fix,
`insufficient_biological_istd=1` is removed from the blocker list. The updated
maturity gate output is:

- `output\diagnostics\instrument_qc_calibration_maturity_gate_after_rt_gate_fix_20260521\instrument_qc_calibration_maturity_gate.tsv`

Level 3 still remains `NO-GO`, but the remaining blockers are now limited to
LOAO residuals, `transfer_not_supported=1`, extrapolated rows, and blocked rows.

## What The Blockers Mean

### 1. LOAO failure is not only a non-ISTD problem

Current LOAO summary:

| scope | rows | PASS | WARN | FAIL | p95 abs error |
| --- | ---: | ---: | ---: | ---: | ---: |
| all anchors | 208 | 107 | 41 | 60 | ~0.632 min |
| ISTD-like anchors | 28 | 7 | 5 | 16 | ~0.718 min |
| non-ISTD-like anchors | 180 | 100 | 36 | 44 | ~0.626 min |

Important ISTD-like failures:

- `d3-5-hmdC`: 4/4 LOAO rows fail.
- `d3-N6-medA`: 4/4 LOAO rows fail.
- `d3-5-medC`: 2/4 LOAO rows fail.
- `d4-N1-2HE-dA`: 2/4 LOAO rows fail.
- `d4-N6-2HE-dA`: 2/4 LOAO rows fail.
- `15N5-8-oxodG`: 1/4 LOAO rows fail.
- `[13C,15N2]-8-oxo-Guo`: 1/4 LOAO rows fail.

This means the Level 3 blocker cannot be dismissed as "external standards are
not expected in biological samples." Some ISTD-like anchors also show poor
leave-one-anchor-out predictability.

### 2. Edge injection orders drive many failures

LOAO failures by injection order:

| injection order | FAIL rows |
| ---: | ---: |
| 5 | 22 |
| 111 | 18 |
| 44 | 11 |
| 78 | 9 |

The failures are concentrated at the clean-standard injection orders available
to the current model. This suggests that the current model is useful for drift
audit, but too sparse to safely become a production RT correction model.

### 3. Biological transfer is mixed, not globally supported

Biological ISTD transfer statuses:

| status | rows |
| --- | ---: |
| `transfer_supported` | 3 |
| `direction_supported_magnitude_shifted` | 2 |
| `transfer_not_supported` | 1 |
| `insufficient_biological_istd` | 1 |

Specific blockers:

- `d3-5-hmdC`: `transfer_not_supported`
  - Biological QC shows meaningful RT drift, while clean standards are nearly
    flat.
- `d3-N6-medA`: originally `insufficient_biological_istd`, now resolved after
  targeted reliability RT-gate correction.
  - Manual EIC review confirmed the early QC1/QC2 peaks are real
    `d3-N6-medA` signals with strong MS1/MS2/NL evidence.
  - The original demotion was caused by RT-prior/window gating, not by missing
    or weak biological evidence.
  - Updated transfer status:
    `direction_supported_magnitude_shifted`; biological and clean standards
    drift in the same direction, but biological matrix shows larger drift.

This supports the user's domain concern: clean standards are valuable, but they
cannot be assumed to transfer into biological matrix without ISTD evidence.

### 4. Matrix preview has a viable shadow subset, but not a production subset

Current matrix RT preview:

| category | rows |
| --- | ---: |
| total rows | 18400 |
| `shadow_only` | 6279 |
| `blocked_missing_value` | 1434 |
| `covered` | 17266 |
| `extrapolated` | 1080 |
| `sparse` | 54 |

`shadow_only` breakdown:

| filter | rows | families | samples |
| --- | ---: | ---: | ---: |
| all `shadow_only` | 6279 | 1790 | 8 |
| `covered` only | 5776 | 1688 | 8 |
| `covered` + residual <= 0.30 min | 1323 | 584 | 7 |
| `covered` + uncertainty <= 0.30 min | 3919 | 1427 | 8 |
| `covered` + residual <= 0.30 + uncertainty <= 0.30 | 1323 | 584 | 7 |

Critical limitation:

- `local_biological_istd_anchor_count` is currently `0` for the matrix preview
  `shadow_only` rows.

Therefore, the matrix preview is mainly clean-standard anchored. It can explain
RT alignment risk, but it cannot yet justify production biological-matrix RT
correction.

## Converged Interpretation

Level 3 fails for a structural reason:

1. The current local RT model is too sparse under LOAO.
2. Clean-standard drift does not fully transfer to biological ISTD behavior;
   after the RT-gate fix this is mainly represented by `d3-5-hmdC`
   `transfer_not_supported` and magnitude-shifted ISTDs, not by
   `d3-N6-medA` missing evidence.
3. Matrix preview contains extrapolated / blocked rows.
4. The matrix preview does not yet include biological ISTDs as local anchors.

This is not evidence that RT-aware calibration is useless. It is evidence that
the current layer should stay at Level 2: audit / alignment-support.

## Next Narrow Target

Do not try to promote global Level 3 production correction.

The next useful target is a new Level 2.5 shadow gate:

```text
rt_supported_shadow_candidate
```

Candidate requirements:

- `correction_status == shadow_only`
- `coverage_status == covered`
- `rt_alignment_support_status == local_rt_supported`
- `local_residual_p95_min <= 0.30`
- `rt_uncertainty_min <= 0.30`
- no extrapolated RT
- no blocked missing RT
- explicit biological ISTD transfer context available

This would produce a reviewable subset, not a production correction.

## What Must Improve Before Level 3 Can Be Reconsidered

Level 3 should remain blocked until all of these are true:

1. A biological-ISTD-aware matrix preview exists.
   - The preview must include local biological ISTD anchor counts or a clear
     transfer scope by RT region.
2. LOAO is stratified by anchor class and RT region.
   - Edge injection order failures should not be hidden inside a global p95.
3. External standards and ISTDs have separate validation roles.
   - SDO/LEK and non-ISTD MixSTDs support clean-instrument behavior.
   - Biological ISTDs are required for matrix-transfer confidence.
4. Extrapolated and blocked rows have an explicit exclusion policy.
   - Production correction must not silently include them.

## Current Decision

Current decision:

```text
Level 2 GO
Level 3 NO-GO
Next step: Level 2.5 shadow candidate gate, not production correction
```

This preserves the useful RT drift evidence while avoiding premature matrix
mutation.
