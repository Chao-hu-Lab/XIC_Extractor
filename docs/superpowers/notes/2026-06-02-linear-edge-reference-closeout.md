# Linear-Edge Reference Closeout

**Date:** 2026-06-02
**Status:** Product path retired; remaining references classified
**Related spec:** [AsLS primary matrix value policy](../specs/2026-06-02-asls-primary-matrix-value-policy-spec.md)

## Verdict

Repository-wide reference review found no maintained product path where
`linear_edge` can be selected as the baseline integration method or final
matrix value source.

The remaining references are allowed only in these categories:

- explicit rejection guards for config, CLI, environment, integration audit, and
  writer entry points;
- historical diagnostic comparison labels and old artifact readers;
- synthetic/historical validation fixtures that name the retired method;
- documentation explaining why linear-edge was retired.

They must not be interpreted as product support, rollback support, or truth
authority for blocking AsLS primary matrix values.

## Active Product Guards

Current product/config surfaces reject `linear_edge` instead of dispatching to
it:

- `scripts/run_alignment.py` rejects `--baseline-integration-method linear_edge`
  and `BASELINE_INTEGRATION_METHOD=linear_edge`.
- `xic_extractor/configuration/settings.py` rejects
  `baseline_integration_method=linear_edge`.
- `xic_extractor/peak_detection/baseline.py` rejects
  `baseline_method="linear_edge"`.
- `xic_extractor/peak_detection/integration_audit.py` rejects
  `baseline_integration_method="linear_edge"`.
- `xic_extractor/alignment/tsv_writer.py` rejects retired linear-edge writer
  method selection.
- `xic_extractor/settings_schema.py` documents the setting as AsLS-only.

Tests cover these guards in config, baseline integration, and TSV writer
surfaces.

## Allowed Historical/Diagnostic References

The following references remain intentionally historical or diagnostic:

- `tools/diagnostics/asls_truth_validation_*`
- `tools/diagnostics/p2b_asls_promotion_gate.py`
- `tools/diagnostics/area_integration_uncertainty_io.py`
- `tools/diagnostics/asls_truth_validation_synthetic.py`, where the comparator
  is named `historical_linear_edge`
- `tools/diagnostics/INDEX.md` lifecycle notes
- `docs/superpowers/fixtures/**` historical evidence fixtures
- pre-2026-06-02 notes/specs that describe the old transition state

These are evidence surfaces, not maintained selectors. If a future cleanup
removes historical fixtures or diagnostic comparators, it should be a separate
artifact-lifecycle cleanup, not a product fallback change.

## Current Product Contract

The final matrix primary value source is:

```text
selected IntegrationResult.area_baseline_corrected
where baseline_type == asls
```

Missing AsLS must blank or review the cell with
`missing_asls_primary_area`; it must not fall back to raw `area`,
`area_raw_counts_seconds`, or any linear-edge-compatible value.
