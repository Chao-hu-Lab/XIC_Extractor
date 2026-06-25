# Instrument QC Level 2.5 RT-Supported Shadow Gate Validation

Date: 2026-05-21

Branch: `codex/handoff-level2-rt-shadow-gate`

## Scope

This note records the first 8RAW smoke result for the Level 2.5
`rt_supported_shadow_candidate` diagnostic.

The diagnostic is audit-only. It does not change:

- `alignment_matrix.tsv`
- `alignment_review.tsv`
- targeted reliability
- peak scoring
- resolver behavior
- workbook schema
- DNP normalization
- production RT / area / response correction

## Inputs

The smoke run used existing artifacts retained in the sibling
`instrument-qc-trend` worktree:

- matrix RT preview:
  `C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend\output\diagnostics\instrument_qc_rt_aware_midterm_level1_8raw_20260521\matrix_rt_calibration_preview.tsv`
- matrix RT preview summary:
  `C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend\output\diagnostics\instrument_qc_rt_aware_midterm_level1_8raw_20260521\matrix_rt_calibration_preview_summary.json`
- biological ISTD transfer audit:
  `C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend\output\diagnostics\instrument_qc_biological_istd_transfer_after_rt_gate_fix_20260521\biological_istd_rt_transfer_audit.tsv`
- biological ISTD transfer summary:
  `C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend\output\diagnostics\instrument_qc_biological_istd_transfer_after_rt_gate_fix_20260521\biological_istd_rt_transfer_audit.json`
- biological ISTD row anchors:
  `C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend\output\diagnostics\instrument_qc_bio_istd_85raw_after_rt_gate_fix_20260521\midterm_evidence\biological_qc_istd_drift_rows.tsv`

## Output

Output directory:

`output\diagnostics\instrument_qc_level2_5_rt_supported_shadow_gate_8raw_20260521`

Generated files:

- `instrument_qc_rt_supported_shadow_gate_rows.tsv`
- `instrument_qc_rt_supported_shadow_gate_summary.tsv`
- `instrument_qc_rt_supported_shadow_gate.json`
- `instrument_qc_rt_supported_shadow_gate.md`

## Result

Run verdict:

```text
shadow_gate_ready
```

Row classification counts:

| classification | rows |
| --- | ---: |
| `rt_supported_shadow_candidate` | 430 |
| `rt_model_uncertain` | 4453 |
| `clean_standard_only_review` | 893 |
| `coverage_not_supported` | 503 |
| `blocked_or_not_applicable` | 12121 |

The result is useful because it proves the gate can produce a narrow
biological-ISTD-supported review subset instead of only returning
`context_incomplete`.

The smoke was rerun after review fixes that make invalid inputs write an
`input_invalid` artifact, distinguish `clean_standard_only_review` from missing
run-level biological context, and add explicit supporting-anchor columns when
the nearest biological ISTD is not the anchor that supplies positive transfer
evidence.

## Interpretation

The 430 `rt_supported_shadow_candidate` rows are not production-corrected rows.
They are rows where:

- the existing Level 1 RT preview row is `shadow_only`;
- clean-standard RT model support is local and low-uncertainty;
- a nearby biological ISTD anchor exists by RT and injection-order proximity;
- the nearby ISTD's clean-to-biological transfer status is supported or
  directionally supported.

Level 3 remains `NO-GO`. The remaining blockers from the maturity gate still
matter:

- global LOAO residuals are too high;
- clean-standard transfer is target-specific;
- extrapolated and blocked matrix rows exist;
- production exclusion policy is not defined.

## Decision

Current decision:

```text
Level 2.5 shadow_gate_ready
Level 3 still NO-GO
```

Recommended next step is to inspect the 430 candidates by family / RT region /
ISTD anchor source before considering any production candidate plan.
