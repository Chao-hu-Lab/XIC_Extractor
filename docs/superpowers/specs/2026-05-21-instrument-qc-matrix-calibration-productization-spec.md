# Instrument QC Matrix Calibration Productization Spec

**Date:** 2026-05-21
**Status:** Draft spec after eng/devex review
**Branch:** `codex/instrument-qc-trend`
**Depends on:**

- `2026-05-20-instrument-qc-sdolek-calibration-v1-spec.md`
- `2026-05-20-instrument-qc-phases-3-6-consolidated-spec-plan.md`
- `docs/superpowers/notes/2026-05-20-instrument-qc-hcd-audit-v1-decision.md`
- `docs/superpowers/notes/2026-05-20-instrument-qc-drift-findings.md`

## Summary

Instrument QC standards should become a calibration evidence product, not just a
review workbook. The product goal is to convert clean-standard and biological
ISTD observations into auditable calibration artifacts that can explain, preview,
and eventually correct raw biological matrices.

This spec defines three product layers:

1. RT-axis correction evidence.
2. Signal response drift evidence.
3. Identity / evidence-confidence annotation.

Only RT-axis correction is an early production candidate. Signal response
correction must remain shadow/audit until biological QC ISTDs prove that clean
standard drift transfers into biological matrix behavior. Identity evidence is a
confidence layer and must not directly scale numeric matrix values.

This is a product spec, not an implementation plan. It defines public contracts,
artifact roles, status semantics, and maturity gates. It intentionally does not
define checkpoints or commit order.

## Product Problem

The project now has multiple high-quality standard sources:

- SDO/LEK clean standards with MS1 trend and product-ion context.
- Mix STDs clean standards with broad target coverage and CID/wHCD product
  evidence.
- biological QC ISTDs from the 85-RAW biological run.
- docs-derived injection order from method / sequence documents.

At the moment, these sources explain acquisition behavior, but they are not yet
converted into reusable matrix-calibration inputs. The missing product layer is a
stable bridge:

```text
standards + injection order + product evidence
  -> calibration evidence table
  -> RT / response drift models
  -> matrix preview sidecars
  -> controlled production correction when validated
```

The product should let a reviewer or downstream tool answer:

- what RT drift did the instrument show at each injection order?
- which RT regions are covered by standards versus extrapolated?
- did response intensity drift globally or target-specifically?
- which matrix values would change under preview correction?
- is a matrix feature supported by product/NL/RT evidence, or only MS1 shape?
- which correction is production-safe and which remains audit-only?
- which file is the entrypoint for downstream consumption?

## Goals

1. Convert SDO/LEK, Mix STDs, and biological QC ISTDs into one shared
   calibration evidence table.
2. Build an RT-drift evidence model that can support corrected RT and
   local residual-based alignment-window review.
3. Build a response-drift evidence model that can preview area/height correction
   without changing production biological matrices by default.
4. Treat CID/wHCD products and dR/R/MeR neutral losses as identity/evidence
   annotations, not numeric correction factors.
5. Separate clean-matrix instrument drift from biological-matrix behavior.
6. Produce matrix-facing sidecars that downstream tools can consume without
   reverse-engineering review workbooks.
7. Preserve existing targeted, untargeted, reliability, final matrix, and DNP
   normalization contracts unless a later reviewed plan explicitly promotes a
   correction layer.

## Non-Goals

- No immediate production scaling of biological matrix area values.
- No default resolver, peak selection, scoring, neutral-loss, reliability, or
  matrix identity change.
- No use of clean standards as a substitute for biological QC ISTDs.
- No assumption that one global RT or response model fits all compounds.
- No ML/DL model.
- No GC-MS support.
- No replacement of downstream DNP normalization.
- No hidden correction of exported workbooks or TSVs.
- No production gate based only on HCD/CID evidence.
- No workbook-only machine contract.

## Product Entrypoint

The product must have one canonical bundle manifest. Downstream tools and human
reviewers start from the manifest, not from a workbook or an arbitrary TSV.

Required entrypoint:

```text
instrument_qc_calibration_manifest.json
```

The manifest is required at every maturity level. It defines:

| Field | Meaning |
|---|---|
| `schema_version` | calibration product schema version |
| `bundle_id` | stable id for this calibration bundle |
| `run_id` | run id or timestamped run key |
| `product_maturity_level` | `level_0` through `level_5` |
| `overall_verdict` | `diagnostic_only`, `preview_ready`, `rt_audit_ready`, `rt_candidate`, `response_shadow`, `response_candidate`, or `not_usable` |
| `artifact_inventory` | paths, roles, required/optional status, and schema versions |
| `source_artifacts` | input files and hashes |
| `source_contracts` | method-doc, targeted, untargeted, matrix, and DNP contract versions when available |
| `generation_command` | command used to create the bundle |
| `created_at_utc` | generation timestamp |
| `created_by` | tool or script name |
| `status_counts` | summary counts for coverage, transfer, correction, and evidence statuses |
| `first_human_file` | suggested workbook/report to open first |
| `first_machine_file` | suggested TSV/JSON for downstream consumption |

JSON files other than the manifest are summaries or model metadata. TSV files are
row-level contracts. The workbook and figures are review surfaces only.

## Operator Contract

Level 1 preview must be generated by one explicit diagnostic/product command,
not by manually stitching unrelated TSVs. The exact script name may be decided
by implementation, but the product surface must support this shape:

```powershell
uv --cache-dir .uv-cache run python tools\diagnostics\instrument_qc_matrix_calibration_preview.py `
  --instrument-qc-dir <instrument_qc_output_dir> `
  --biological-istd-evidence <current_code_targeted_or_benchmark_artifact> `
  --matrix-input <alignment_cells_or_targeted_matrix_input> `
  --method-doc <method_sequence_docx> `
  --output-dir <calibration_bundle_dir>
```

Required inputs for Level 1:

- instrument QC evidence with SDO/LEK and Mix STDs rows;
- docs-derived injection order or method doc from which it can be built;
- one explicit matrix input source;
- current-code biological QC ISTD evidence when biological transfer is claimed.

If biological QC ISTD evidence is missing, Level 1 may still produce clean-only
preview artifacts, but response correction status must remain `shadow_only` or
`clean_only_review`.

## Evidence Source Semantics

### Clean SDO/LEK Standards

Primary meaning:

- instrument/system suitability;
- RT-axis behavior at SDO/LEK RT regions;
- response trend in clean matrix;
- product-ion support for SDO/LEK selected peaks.

Limitations:

- sparse RT coverage;
- clean matrix only;
- cannot explain biological matrix effect by itself;
- should not define a global chromatographic warp alone.

### Clean Mix STDs

Primary meaning:

- broader RT coverage;
- target-specific clean-matrix RT and response behavior;
- product-ion support for reviewed bases / target groups;
- stale RT prior/window detection.

Limitations:

- clean matrix only;
- standards may not cover every biological feature RT region;
- compound-specific response can differ from unknown biological features.

### Biological QC ISTDs

Primary meaning:

- real-matrix drift anchor;
- added standards inside biological samples;
- best source for production confidence in RT and response correction;
- target-specific sensitivity / ionization behavior under matrix pressure.

Limitations:

- limited chemical coverage;
- ISTD behavior may not represent every unknown feature;
- targeted extraction reliability must be current-code and benchmark eligible
  before being used as calibration truth.

### HCD/CID Product Evidence

Primary meaning:

- confirms that selected clean-standard peaks are chemically plausible;
- maps Mix STDs to base/product groups;
- distinguishes product-supported evidence from MS1-only evidence.

Limitations:

- not a numeric correction factor;
- missing MS2 trigger may reflect DDA sensitivity, not absence of analyte;
- must remain an annotation/confidence signal unless a later identity gate is
  explicitly reviewed.

## Status Taxonomy

Status fields must use explicit, non-overloaded values. Every row-level status
must be paired with `review_reason`. Summary JSON must count each status.

### Coverage Status

| Status | Meaning | Severity | Allowed next action |
|---|---|---|---|
| `covered` | enough local anchors support the prediction | info | preview may apply |
| `sparse` | limited anchors; prediction is review-only | warning | preview may apply with caution |
| `extrapolated` | outside anchor RT/order coverage | warning | no production use |
| `unsupported` | no usable anchors | blocker | no preview value |

### Model Status

| Status | Meaning | Severity | Allowed next action |
|---|---|---|---|
| `usable` | model can produce preview values | info | Level 1 preview |
| `review` | model usable only for interpretation | warning | no production use |
| `not_usable` | model lacks required evidence | blocker | report only |

### Transfer Status

| Status | Meaning | Severity | Allowed next action |
|---|---|---|---|
| `biological_supported` | biological QC ISTDs support the clean-standard trend | info | response preview can be marked biological-supported |
| `clean_only` | only clean standards support the trend | warning | shadow-only |
| `conflicting` | clean and biological evidence disagree | blocker | no production use |
| `unsupported` | insufficient response anchors | blocker | no preview value |

### Product / MS2 Status Mapping

The calibration product must preserve instrument-QC HCD audit semantics:

| HCD audit status | Calibration product status | Meaning |
|---|---|---|
| `hcd_supported` | `supported` | expected products found |
| `hcd_partial` | `partial` | some but not all expected products found |
| `no_ms2_trigger` | `not_triggered` | DDA did not trigger usable MS2 near apex |
| `no_product_match` | `product_missing` | MS2 exists but expected products not found |
| `hcd_group_unmapped` | `unmapped` | product group cannot be assigned |
| `ms2_parse_error` | `parse_error` | MS2 evidence could not be parsed |
| no product contract | `not_applicable` | product evidence is not expected |

`not_triggered` must never be interpreted as analyte absence.

### Correction Status

| Status | Meaning |
|---|---|
| `applied_preview` | preview value was computed |
| `shadow_only` | value shown for review but not production eligible |
| `biological_supported_preview` | response preview has biological QC support |
| `not_covered` | no model coverage |
| `blocked_missing_value` | source value is missing/blank/ND |
| `blocked_nonpositive_value` | source value is zero or non-positive |
| `review` | value exists but requires review |
| `not_applicable` | correction layer does not apply |

## Calibration Evidence Table Contract

The shared calibration table is the canonical bridge from standards to model
artifacts. It contains calibration anchors, not arbitrary biological matrix
observations.

Required artifacts:

```text
instrument_qc_calibration_evidence.tsv
instrument_qc_calibration_evidence_summary.json
```

Minimum columns:

| Column | Meaning |
|---|---|
| `schema_version` | row schema version |
| `bundle_id` | calibration bundle id |
| `evidence_row_id` | stable row id for joins |
| `source_artifact_id` | manifest artifact id that produced this row |
| `source_artifact_hash` | hash of source artifact if available |
| `source_type` | `sdolek`, `mixstds`, or `biological_qc_istd` |
| `matrix_context` | `clean` or `biological_qc` |
| `sample_name` | review-facing sample name |
| `raw_stem` | normalized RAW stem |
| `source_raw_file` | basename or relative RAW path |
| `raw_path_kind` | `basename`, `relative`, `absolute`, or `not_recorded` |
| `injection_order` | docs-derived injection order |
| `compound` | standard / ISTD / target label |
| `compound_group` | optional group such as `SDO`, `LEK`, `A`, `C`, `G`, `T`, `U`, `dR`, `R`, `MeR` |
| `precursor_mz` | expected precursor m/z |
| `observed_mz` | observed precursor m/z when available |
| `mz_ppm_error` | observed precursor ppm error |
| `reference_rt_min` | reviewed reference RT used for drift calculation |
| `observed_rt_min` | selected apex RT |
| `rt_delta_min` | `observed_rt_min - reference_rt_min` |
| `rt_region` | binned or model-assigned RT region |
| `area` | raw integrated area |
| `height` | peak height if available |
| `log2_area_delta` | log2 ratio to source-specific reference / median |
| `log2_height_delta` | log2 ratio to source-specific reference / median |
| `peak_width_min` | selected peak width |
| `activation_method` | `CID`, `wHCD`, `HCD`, `CIDwHCD`, or `unknown` |
| `product_support_status` | mapped product status from the taxonomy |
| `neutral_loss_support_status` | `supported`, `partial`, `not_triggered`, `product_missing`, `unmapped`, `parse_error`, or `not_applicable` |
| `evidence_confidence` | `high`, `review`, `low`, or `not_assessable` |
| `calibration_eligible` | `true` or `false` |
| `exclusion_reason` | reason when not eligible |

`biological_sample` rows belong in matrix preview or annotation sidecars, not in
this calibration evidence table.

## RT Correction Model Contract

Required artifacts:

```text
instrument_qc_rt_drift_model.tsv
instrument_qc_rt_drift_model_summary.json
```

The RT model estimates:

```text
predicted_rt_delta_min = f(injection_order, rt_region, model_scope)
```

Matrix-facing correction formula:

```text
corrected_rt_min = observed_rt_min - predicted_rt_delta_min
```

Required model outputs:

| Column | Meaning |
|---|---|
| `schema_version` | row schema version |
| `bundle_id` | calibration bundle id |
| `model_id` | stable model id |
| `model_scope` | `compound`, `compound_group`, `rt_region`, or `global_summary` |
| `compound` | compound-specific model label when applicable |
| `compound_group` | group-specific model label when applicable |
| `source_type` | dominant source type or `mixed` |
| `matrix_context` | `clean`, `biological_qc`, or `mixed` |
| `injection_order` | sequence order where prediction applies |
| `rt_region` | RT region / anchor segment |
| `source_mix` | standard sources used in the model |
| `anchor_ids` | semicolon-delimited `evidence_row_id` values |
| `anchor_count` | number of standards supporting this prediction |
| `clean_anchor_count` | clean standard count |
| `biological_istd_anchor_count` | biological ISTD count |
| `predicted_rt_delta_min` | model-estimated RT drift |
| `rt_uncertainty_min` | residual / uncertainty |
| `coverage_status` | coverage status taxonomy value |
| `conflict_status` | `none`, `clean_biological_conflict`, `compound_conflict`, or `insufficient_comparison` |
| `model_status` | model status taxonomy value |
| `review_reason` | concise explanation |

Rows with different `model_scope`, `compound`, `compound_group`, `source_type`,
or `matrix_context` must not overwrite one another. A global row may summarize
the run, but it cannot be the only RT model used for matrix preview.

### RT Model Semantics

The model must be local and evidence-aware:

- use per-compound or RT-region trends before global trends;
- use docs-derived injection order;
- prefer robust smoothing such as low-flexibility LOESS / spline over a high
  flexibility fit;
- expose residuals and uncertainty;
- mark extrapolated RT regions explicitly;
- allow biological QC ISTDs to reduce confidence or override clean-standard
  confidence when the two disagree in real matrix.

The model must not claim that RT drift is globally uniform.

## Matrix Input Contract

Matrix preview must declare the source it is previewing. Accepted Level 1 matrix
input roles:

| Input role | Accepted source | Use |
|---|---|---|
| `untargeted_cell_table` | `alignment_cells.tsv` or equivalent cell-level audit table | cell-level RT/area preview |
| `untargeted_wide_matrix` | `alignment_matrix.tsv` | reference only unless paired with cell-level RT/area |
| `targeted_result_table` | targeted XIC result CSV/workbook with selected RT/area | target-level RT/area preview |
| `external_matrix` | explicitly mapped downstream matrix | response preview only when join keys are provided |

Preview sidecars must include enough keys to rejoin safely:

- `matrix_source`
- `matrix_source_hash`
- `matrix_schema_version`
- `source_row_id`
- `source_cell_key`
- `feature_id`
- `matrix_column_name`
- `sample_name`
- `sample_stem`
- `raw_file_stem`
- `feature_mz`
- `raw_feature_rt_min`

Wide matrix files are not sufficient for RT preview unless they contain or are
joined to sample-cell RT. They can still be used to show area-only response
preview when sample order and matrix columns are unambiguous.

## Matrix RT Application Contract

Required Level 1 preview artifacts when RT preview is requested:

```text
matrix_rt_calibration_preview.tsv
matrix_rt_calibration_summary.json
```

Required preview columns:

| Column | Meaning |
|---|---|
| `schema_version` | row schema version |
| `bundle_id` | calibration bundle id |
| `matrix_source` | source matrix file / run id |
| `matrix_source_hash` | hash of source matrix artifact |
| `matrix_schema_version` | source matrix schema version when known |
| `source_row_id` | source row id |
| `source_cell_key` | stable cell key when cell-level |
| `feature_id` | feature row identity |
| `matrix_column_name` | original matrix column |
| `sample_name` | sample display name |
| `sample_stem` | normalized sample stem |
| `raw_file_stem` | RAW stem joined to sample |
| `feature_mz` | feature m/z |
| `raw_feature_rt_min` | original feature/cell RT |
| `injection_order` | docs-derived order |
| `model_id` | RT model row used |
| `predicted_rt_delta_min` | model correction |
| `corrected_rt_min` | corrected RT |
| `rt_uncertainty_min` | model uncertainty |
| `coverage_status` | RT model coverage |
| `correction_status` | correction status taxonomy value |
| `review_reason` | concise reason |

Production RT use can be considered only at Level 3 or later.

## Response Drift Model Contract

Required artifacts:

```text
instrument_qc_response_drift_model.tsv
instrument_qc_response_drift_model_summary.json
```

The response model estimates:

```text
predicted_log2_response_delta = g(injection_order, compound_group, matrix_context)
```

Preview correction formula:

```text
area_if_response_corrected = raw_area / 2 ** predicted_log2_response_delta
height_if_response_corrected = raw_height / 2 ** predicted_log2_response_delta
```

Required model outputs:

| Column | Meaning |
|---|---|
| `schema_version` | row schema version |
| `bundle_id` | calibration bundle id |
| `model_id` | stable model id |
| `model_scope` | `compound`, `compound_group`, `matrix_context`, or `global_summary` |
| `compound` | compound-specific model label when applicable |
| `compound_group` | compound or response group |
| `matrix_context` | `clean`, `biological_qc`, or `mixed` |
| `source_type` | dominant source type or `mixed` |
| `injection_order` | sequence order where prediction applies |
| `anchor_ids` | semicolon-delimited `evidence_row_id` values |
| `anchor_count` | standards supporting prediction |
| `clean_standard_count` | clean standard rows |
| `biological_istd_count` | biological ISTD rows |
| `predicted_log2_response_delta` | estimated response shift |
| `response_uncertainty_log2` | residual / uncertainty |
| `transfer_status` | transfer status taxonomy value |
| `model_status` | model status taxonomy value |
| `review_reason` | concise reason |

### Response Model Semantics

Response correction is higher risk than RT correction:

- clean standards may identify instrument response events;
- biological QC ISTDs decide whether those events transfer into real matrix;
- compound-specific ionization behavior must be preserved;
- a global median response model is a review summary, not a production scaler;
- DNP / downstream normalization remains responsible for broader biological
  sample normalization.

Clean-only response drift may be shown in preview, but must not scale production
biological matrices.

## Matrix Response Application Contract

Required Level 1 preview artifacts when response preview is requested:

```text
matrix_response_calibration_preview.tsv
matrix_response_calibration_summary.json
```

Required preview columns:

| Column | Meaning |
|---|---|
| `schema_version` | row schema version |
| `bundle_id` | calibration bundle id |
| `matrix_source` | source matrix file / run id |
| `matrix_source_hash` | hash of source matrix artifact |
| `matrix_schema_version` | source matrix schema version when known |
| `source_row_id` | source row id |
| `source_cell_key` | stable cell key when cell-level |
| `feature_id` | feature row identity |
| `matrix_column_name` | original matrix column |
| `sample_name` | sample display name |
| `sample_stem` | normalized sample stem |
| `raw_file_stem` | RAW stem joined to sample |
| `feature_mz` | feature m/z |
| `raw_feature_rt_min` | original feature/cell RT when available |
| `injection_order` | docs-derived order |
| `raw_area` | original matrix area |
| `raw_area_status` | `positive`, `zero`, `missing`, `not_detected`, `not_numeric`, or `not_applicable` |
| `raw_height` | original height when available |
| `raw_height_status` | `positive`, `zero`, `missing`, `not_detected`, `not_numeric`, or `not_applicable` |
| `model_id` | response model row used |
| `predicted_log2_response_delta` | response model correction |
| `area_if_response_corrected` | shadow-corrected area |
| `height_if_response_corrected` | shadow-corrected height |
| `preview_area_status` | `computed`, `blocked`, or `not_applicable` |
| `preview_height_status` | `computed`, `blocked`, or `not_applicable` |
| `response_uncertainty_log2` | model uncertainty |
| `transfer_status` | biological support status |
| `correction_status` | correction status taxonomy value |
| `correction_block_reason` | reason when blocked |
| `review_reason` | concise reason |

### Missing / Zero / ND Policy

Response preview must not impute missing values.

- Missing, blank, non-numeric, absent, unchecked, or not-detected source values
  must produce blank corrected values and `blocked_missing_value`.
- Zero or negative source values must produce blank corrected values and
  `blocked_nonpositive_value`.
- Rescued/backfilled/review-only cells may be previewed only when their raw area
  is positive and finite; their source status must remain visible in
  `review_reason` or an implementation-specific `source_cell_status` column.
- Preview correction must never convert a missing/zero value into a positive
  matrix value.

Production response correction can be considered only at Level 5.

## Identity / Evidence Annotation Contract

Recommended artifacts:

```text
matrix_calibration_evidence_annotation.tsv
matrix_calibration_evidence_annotation_summary.json
```

This layer does not change RT or area. It describes how much confidence exists
behind a feature / target / standard row.

Required columns:

| Column | Meaning |
|---|---|
| `schema_version` | row schema version |
| `bundle_id` | calibration bundle id |
| `matrix_source` | source matrix file / run id |
| `matrix_source_hash` | hash of source matrix artifact |
| `source_row_id` | source row id |
| `source_cell_key` | stable cell key when cell-level |
| `feature_id` | feature row identity |
| `sample_name` | sample display name |
| `sample_stem` | normalized sample stem |
| `compound_or_family` | target label or untargeted family id |
| `matrix_context` | `clean`, `biological_qc`, or `biological_sample` |
| `rt_support_status` | `supported`, `drift_corrected_supported`, `review`, or `unsupported` |
| `product_support_status` | product status taxonomy value |
| `neutral_loss_support_status` | dR/R/MeR evidence state |
| `ms1_shape_support_status` | MS1 shape / overlay evidence state when available |
| `evidence_confidence` | `high`, `review`, `low`, or `not_assessable` |
| `review_reason` | concise reason |

This annotation may feed review reports and future production gates, but must not
silently alter numeric matrix values.

## Product Maturity Levels

The calibration product has staged readiness levels. These are product states,
not implementation checkpoints.

### Level 0: Diagnostic Only

Required:

- manifest exists;
- evidence table exists;
- standards workbook/plots explain current evidence;
- no matrix preview;
- no exported matrix changes.

Acceptance:

- source artifacts and hashes are recorded;
- evidence statuses are counted;
- product cannot be mistaken for a correction output.

### Level 1: Matrix Preview

Required:

- manifest exists;
- evidence table exists;
- at least one selected matrix preview TSV exists;
- raw matrix remains unchanged;
- coverage/extrapolation and correction status are explicit.

Acceptance:

- preview sidecar can be rejoined to source matrix/cells through stable keys;
- no hidden matrix modification occurs;
- missing/zero/ND values are not imputed;
- JSON summaries report status counts and source hashes;
- biological transfer may be absent, but must be labeled as such.

### Level 2: RT-Aware Audit / Alignment Support

Required:

- RT model residuals are exposed;
- corrected RT can explain alignment windows or review mismatches;
- final matrix RT values remain raw unless a later contract says otherwise.

Acceptance:

- high-confidence targets and ISTDs show no regression;
- extrapolated RT regions remain review-only;
- local residual windows are explainable from model artifacts.

### Level 3: RT Production Candidate

Required:

- leave-one-anchor-out residuals improve;
- biological QC ISTD drift is current-code and reproducible;
- extrapolated RT regions are excluded from production correction.

Acceptance:

- downstream matrix identity stays stable;
- rollback path is documented;
- production RT correction is opt-in until promoted by a separate reviewed plan.

### Level 4: Response Shadow Candidate

Required:

- response correction remains preview-only;
- biological QC ISTD transfer evidence exists;
- DNP/downstream normalization compatibility is explicitly tested.

Acceptance:

- no target/ISTD area regression in preview review;
- no artificial group separation is introduced in diagnostic analysis;
- clean-only response signals remain shadow-only.

### Level 5: Response Production Candidate

This is intentionally a high bar. It requires:

- biological QC ISTD support;
- no target/ISTD area regression;
- no artificial biological group separation;
- explicit downstream normalization contract;
- reviewed rollback path.

Response production correction is out of scope for the current product position.

## Output Surface

### Required Level 1 Bundle

Level 1 should keep the required output set small:

```text
instrument_qc_calibration_manifest.json
instrument_qc_calibration_evidence.tsv
instrument_qc_calibration_evidence_summary.json
matrix_rt_calibration_preview.tsv                  # when RT preview requested
matrix_rt_calibration_summary.json                 # when RT preview requested
matrix_response_calibration_preview.tsv            # when response preview requested
matrix_response_calibration_summary.json           # when response preview requested
```

### Optional Model / Review Artifacts

```text
instrument_qc_rt_drift_model.tsv
instrument_qc_rt_drift_model_summary.json
instrument_qc_response_drift_model.tsv
instrument_qc_response_drift_model_summary.json
matrix_calibration_evidence_annotation.tsv
matrix_calibration_evidence_annotation_summary.json
instrument_qc_calibration_review.xlsx
instrument_qc_calibration_review.md
instrument_qc_calibration_overview.png
instrument_qc_calibration_overview.pdf
```

TSV files are row-level contracts. JSON files are manifest, summaries, or model
metadata. Workbook and figures are review surfaces and must never be the only
machine-readable source.

## Review Workbook Contract

The workbook is the first human review surface, not a downstream API.

Recommended sheets:

| Sheet | Responsibility |
|---|---|
| `Overview` | verdict, maturity level, source artifacts, first files to inspect |
| `Coverage` | anchor coverage by RT region, injection order, and source type |
| `Model QC` | model residuals, uncertainty, transfer/conflict summaries |
| `Preview Deltas` | largest RT/area preview changes with review reasons |
| `Evidence Annotation` | product/NL/MS1 support summary |
| `Exceptions` | unsupported, extrapolated, conflicting, blocked, or missing-value rows |
| `Run Metadata` | schema versions, command, hashes, method-doc source |

Workbook tables may duplicate TSV rows for readability, but the TSV/JSON bundle
remains the source of truth.

## Integration Boundaries

### Targeted Extraction

Targeted extraction may consume calibration artifacts for audit-only comparison:

- raw RT versus corrected RT;
- targeted area versus response-corrected preview area;
- product/NL support annotation.

It must not change selected peak, area, reliability state, or workbook schema
unless a later reviewed plan promotes the relevant layer.

### Untargeted Alignment

Untargeted alignment may consume RT model evidence to annotate:

- family RT drift context;
- local residual-based window review;
- backfill / rescued cell RT consistency;
- MS1 shape support under corrected RT.

It must not change matrix identity, production gate, backfill behavior, or final
matrix values unless a later reviewed plan promotes the relevant layer.

### Downstream DNP / Statistical Workflow

Downstream normalization may receive either:

- raw matrix plus calibration sidecars; or
- explicitly versioned calibrated matrix preview.

The default handoff should remain raw matrix plus sidecars until response
correction is validated. This avoids mixing instrument response correction with
biological normalization without an explicit contract.

## Validation And Contract Tests

Any implementation of this product contract must include:

- manifest completeness test;
- schema-version and artifact-inventory test;
- calibration evidence column / enum test;
- HCD/CID status mapping test;
- matrix preview join-key test;
- no-hidden-matrix-change regression test;
- response zero/ND policy test;
- status count summary test;
- current-code biological QC ISTD evidence gate when biological transfer is
  claimed;
- workbook sheet contract test when workbook output is emitted.

Real-data validation should report:

- anchor coverage by RT region and injection order;
- clean-only versus biological-supported response drift;
- largest matrix RT preview deltas;
- largest matrix response preview deltas;
- blocked missing/zero/non-positive values;
- extrapolated or unsupported rows.

## Acceptance Semantics

A calibration product is acceptable when it can answer these questions from the
manifest and row-level sidecars alone:

1. Which standards support each RT region and injection-order segment?
2. Which model predictions are covered versus extrapolated?
3. Which preview rows are rejoinable to the source matrix/cell table?
4. Which response drift signals are clean-only versus biological-supported?
5. Which matrix values would change under preview correction?
6. Which values were blocked because they were missing, zero, or unsupported?
7. Which features are product/NL/MS1-shape supported versus MS1-only?
8. Which outputs are production-safe and which are audit-only?

The product is not acceptable if:

- it hides correction inside a workbook;
- it scales biological matrix area from clean standards alone;
- it collapses compound-specific RT drift into one global offset without
  uncertainty;
- it treats missing DDA MS2 trigger as automatic absence;
- it changes final matrix values without a sidecar and rollback path;
- it produces sidecars without a manifest;
- it cannot prove source matrix values were unchanged.

## Open Design Questions

1. What RT-region binning should be used before enough dense anchors exist?
2. Should biological QC ISTDs override clean-standard RT trends, or only reduce
   confidence when they disagree?
3. How should matrix features outside all anchor coverage be represented in
   downstream tools?
4. What minimum biological QC ISTD support is required before response
   correction can become more than shadow-only?
5. Should DNP consume calibration sidecars directly, or should XIC Extractor
   emit a separate calibrated-preview matrix?

These are product design questions. They must not block Level 1 preview as long
as unsupported and unresolved states are explicit in the manifest.

## Current Product Position

Current evidence supports:

- Level 0 diagnostic-only standards interpretation.
- Level 1 matrix preview as the next product surface.
- RT correction as a realistic future production candidate.
- Response correction as shadow/audit only.
- Product/NL evidence as confidence annotation, not numeric correction.

The next product step should therefore create a manifest-backed calibration
evidence bundle and one explicit matrix preview sidecar before changing any
production matrix.
