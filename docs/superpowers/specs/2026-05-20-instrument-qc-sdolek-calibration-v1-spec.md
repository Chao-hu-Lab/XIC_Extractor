# Instrument QC SDOLEK Calibration v1 Spec

**Date:** 2026-05-20
**Status:** Reviewed draft
**Branch:** `codex/instrument-qc-trend`
**Depends on:** `2026-05-20-instrument-only-qc-trend-spec.md`

## Summary

Phase 1 proved that the opt-in SDOLEK pipeline can discover 11 SDOLEK RAW files
and emit SDO/LEK MS1 trend evidence. The next phase should not jump directly to
workbook presentation. The real-data smoke showed that the current review flags
are warning-heavy because NoSplit reference width may not be directly comparable
to the Phase 1 integration boundary, and LEK MS1 apex RT is systematically
earlier than the NoSplit prior.

Phase 2 therefore has two required parts. First, it introduces a docs-to-manifest
step that converts method / sequence docs into auditable injection-order
metadata. Second, it adds an audit-only SDOLEK calibration/report layer that
reads Phase 1 TSV/JSON outputs, joins the docs-derived injection order, computes
batch-relative trend metrics, and emits a concise human review report.

Batch-relative calibration can still run when the docs-derived manifest is not
yet available, but the Phase 2 acceptance target is not complete until the docs
step exists. Injection order enables order-dependent drift interpretation. This
phase does not reread RAW, does not use HCD/wHCD evidence, and does not change
Phase 1 peak selection.

## Goals

1. Convert Phase 1 SDO/LEK rows into calibrated trend evidence.
2. Separate three meanings that are currently conflated:
   - prior disagreement versus NoSplit reference;
   - batch-relative drift or sensitivity trend;
   - MS1-only identity uncertainty.
3. Add a docs-to-manifest source step so SDO/LEK instrument QC has a real
   pipeline entry point instead of relying on manually supplied order files.
4. Use method-doc-derived sequence metadata through the existing
   `Sample_Name,Injection_Order` contract. `SampleInfo` is downstream evidence
   only and must not be a pipeline input or fallback source.
5. Produce a compact human review artifact that explains SDO/LEK trend without
   burying the user in raw rows.
6. Keep HCD/wHCD fragment evidence deferred until a separate MS2 evidence phase.

## Non-Goals

- No RAW reread.
- No SDO/LEK peak reselection.
- No HCD/wHCD product-ion extraction.
- No identity-confirmed label.
- No workbook-first implementation.
- No main extraction or alignment integration.
- No `xic_results`, targeted reliability, untargeted matrix, scoring, NL, or
  resolver changes.
- No hidden lifecycle append or user-home writes.

## Inputs

Required:

```text
instrument_qc_sdolek_trend.tsv
instrument_qc_sdolek_trend.json
method / sequence docx or reviewed docs-derived manifest
```

Intermediate:

```text
instrument_qc_sequence_manifest.tsv
method-doc-derived Sample_Name,Injection_Order
```

The injection-order file must be generated from method / sequence docs or from a
reviewed manifest that itself was generated from those docs.
`SampleInfo.xlsx` is not an accepted input and must not be treated as an
equivalent fallback. If a `SampleInfo`-like file is used during human review, it
can only validate the converter output; it must not define pipeline truth.

## Sequence Source Contract

There is exactly one authoritative injection-order source for this project:

```text
method / sequence docs -> doc-derived manifest -> Sample_Name,Injection_Order
```

Downstream `SampleInfo` may contain the same information because it is also
derived from docs, but it is not the source of truth for this repo's pipeline.
The pipeline must therefore surface four distinct states:

- `missing`: no method-doc-derived injection order was supplied;
- `provided`: method-doc-derived order was supplied and matched all Phase 1 rows;
- `partial_match`: method-doc-derived order was supplied but not every RAW stem
  matched;
- `invalid`: the supplied source is not a valid docs-derived order file.

Name reconciliation belongs to the docs-to-manifest step, not to SDOLEK
calibration. The calibration layer may join by `sample_name`, but it must not
invent aliases from downstream sample metadata.

### Docs-Derived Manifest Contract

`instrument_qc_sequence_manifest.tsv` is the audit surface for parsing method /
sequence docs. Minimum columns:

| Column | Meaning |
|---|---|
| `source_doc` | method / sequence document path or basename |
| `source_section` | section/table/paragraph identifier when available |
| `doc_display_name` | injection name as written in the docs |
| `raw_stem` | normalized RAW stem intended to match Phase 1 `sample_name` |
| `injection_order` | integer sequence order |
| `instrument_qc_class` | e.g. `SDOLEK`, `MIX_STDS`, `BLANK`, `POOLED_QC`, `UNKNOWN` |
| `match_status` | `matched`, `unmatched`, `ambiguous`, or `manual_review` |
| `match_confidence` | `high`, `medium`, `low` |
| `match_reason` | short explanation of normalization / mismatch |

The manifest writer may also emit a normalized `Sample_Name,Injection_Order`
CSV for existing readers. That CSV is a compatibility output, not the audit
surface.

## Outputs

Phase 2 emits diagnostic/report artifacts only:

```text
instrument_qc_sdolek_calibrated_trend.tsv
instrument_qc_sdolek_calibration_summary.json
instrument_qc_sdolek_review.md
```

No workbook is added in this phase.

## Calibrated Trend TSV Contract

`instrument_qc_sdolek_calibrated_trend.tsv` columns:

| Column | Meaning |
|---|---|
| `sample_name` | RAW stem from Phase 1 |
| `compound` | `SDO` or `LEK` |
| `identity_evidence` | always `MS1_ONLY` in this phase |
| `injection_order` | joined method-doc-derived order if available |
| `status` | Phase 1 status |
| `apex_rt_min` | Phase 1 apex RT |
| `area` | Phase 1 raw area |
| `base_width_min` | Phase 1 base width |
| `reference_rt_min` | NoSplit prior RT |
| `rt_delta_to_reference_min` | Phase 1 prior delta |
| `reference_base_width_min` | NoSplit prior base width |
| `base_width_ratio_to_reference` | Phase 1 base width divided by NoSplit prior width |
| `compound_batch_median_rt_min` | median apex RT for detected rows of the same compound |
| `rt_delta_to_batch_median_min` | apex RT minus compound batch median |
| `compound_batch_median_area` | median area for detected rows of the same compound |
| `log2_area_ratio_to_batch_median` | log2(area / compound median area) |
| `compound_batch_median_width_min` | median base width for detected rows of the same compound |
| `width_ratio_to_batch_median` | base width divided by compound batch median width |
| `prior_conflict_flags` | semicolon labels from NoSplit-prior comparison |
| `batch_trend_flags` | semicolon labels from batch-relative comparison |
| `review_bucket` | calibrated review classification |
| `review_reason` | concise human-readable reason |

## Review Bucket Semantics

Bucket precedence:

1. `not_detected_or_error`
   - Phase 1 status is not `detected`.
2. `identity_evidence_insufficient`
   - sparse detections or internally inconsistent MS1 evidence prevent useful
     trend interpretation.
3. `prior_reference_mismatch`
   - NoSplit prior disagrees, but batch-relative trend is internally consistent.
4. `rt_drift_review`
   - ordered rows show monotonic or local RT movement worth review.
5. `sensitivity_trend_review`
   - area ratio shows ordered response drop/rise worth review.
6. `width_definition_review`
   - prior width and Phase 1 integration width disagree, but batch width is
     internally stable.
7. `stable_ms1_trend`
   - detected, batch-relative RT/area/width are internally stable.

The bucket is a review classification, not a production pass/fail gate.
Missing method-doc-derived injection order is not a row-level failure bucket. It
is reported as run metadata and suppresses only order-dependent drift
interpretation.
`MS1_ONLY` is a required caveat, not by itself an insufficient-evidence bucket.
A stable batch-relative signal with LEK/SDO prior RT or width disagreement should
be classified as `prior_reference_mismatch` or `width_definition_review`, not
as chemical identity confirmation and not as automatic failure.

## Thresholds

V1 thresholds are review flags only:

| Flag | Rule |
|---|---|
| `PRIOR_RT_SHIFT` | `abs(rt_delta_to_reference_min) > 0.50` |
| `PRIOR_WIDTH_SHIFT` | `base_width_ratio_to_reference < 0.50` or `> 1.75` |
| `BATCH_RT_OUTLIER` | `abs(rt_delta_to_batch_median_min) > 0.20` |
| `BATCH_AREA_DROP` | `log2_area_ratio_to_batch_median < -1.0` |
| `BATCH_AREA_RISE` | `log2_area_ratio_to_batch_median > 1.0` |
| `BATCH_WIDTH_OUTLIER` | width ratio to batch median `< 0.60` or `> 1.60` |

If fewer than 3 detected rows exist for a compound, batch-relative fields are
left blank and the affected rows must use `identity_evidence_insufficient` or
`not_detected_or_error` rather than over-interpreting sparse evidence.

`instrument_qc_sdolek_calibration_summary.json` must include both Phase 1
metadata source status and Phase 2 injection-order join status:

```json
{
  "phase1_metadata_source_status": {},
  "calibration_metadata_status": {
    "injection_order_source": "",
    "injection_order_status": "missing",
    "source_contract": "method_docs_only",
    "matched_injection_order_rows": 0,
    "unmatched_injection_order_rows": 0
  }
}
```

Allowed `injection_order_status` values are `missing`, `provided`,
`partial_match`, and `invalid`.

## Human Review Report Contract

`instrument_qc_sdolek_review.md` must fit on one screen before tables:

- verdict: `review_ready`, `metadata_incomplete`, or `insufficient_evidence`;
- count of SDO/LEK detected rows;
- whether injection order was available;
- top SDO/LEK area trend observation;
- top SDO/LEK RT trend observation;
- explicit note that `identity_evidence = MS1_ONLY`;
- top rows needing manual review.

The report should favor short summaries and only link to TSV/JSON for detail.

Verdict semantics:

- `review_ready`: enough detected rows exist for batch-relative calibration.
  Missing method-doc-derived injection order is allowed, but the report must say
  order-dependent drift was not evaluated.
- `metadata_incomplete`: supplied method-doc-derived injection-order metadata is
  invalid or too poorly matched to support requested order-dependent
  interpretation.
- `insufficient_evidence`: too few detected rows, extraction errors, or
  MS1-only conflicts prevent useful calibration.

## CLI Contract

Add a diagnostic CLI:

```powershell
uv --cache-dir .uv-cache run python tools\diagnostics\instrument_qc_sdolek_calibration.py `
  --trend-tsv output\instrument_qc\20260105_sdo_lek\instrument_qc_sdolek_trend.tsv `
  --trend-json output\instrument_qc\20260105_sdo_lek\instrument_qc_sdolek_trend.json `
  --output-dir output\instrument_qc\20260105_sdo_lek_calibration
```

Docs-derived injection-order input:

```powershell
  --injection-order-source path\to\method_doc_derived_injection_order.csv
```

The CLI must reject or clearly mark non-doc-derived sources as invalid. In v1
this can be a documented trust contract plus file provenance metadata; a later
docs parser should make the provenance machine-checkable.

Add a docs-to-manifest CLI:

```powershell
uv --cache-dir .uv-cache run python tools\diagnostics\instrument_qc_sequence_manifest.py `
  --method-doc "C:\Users\user\Desktop\NTU cancer\2025台大乳癌組織數據for Jia\20260105中研院台大Breast cancer tissue\20260105 中研院分析.docx" `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --output-dir output\instrument_qc\20260105_sequence_manifest
```

The CLI must produce:

```text
instrument_qc_sequence_manifest.tsv
instrument_qc_injection_order.csv
instrument_qc_sequence_manifest.json
instrument_qc_sequence_manifest.md
```

## Acceptance Criteria

- Reads Phase 1 outputs without RAW access.
- Produces docs-derived sequence manifest and normalized injection-order CSV.
- Produces calibrated TSV, JSON, and review markdown.
- Preserves `MS1_ONLY` identity semantics.
- Clearly separates prior mismatch from batch-relative drift/sensitivity trend.
- Does not add HCD/wHCD, workbook, lifecycle, or production pipeline changes.
- Real 11-RAW SDOLEK smoke produces `review_ready` if all rows are detected,
  even if prior-reference warnings remain.
- SDOLEK calibration with the generated docs-derived injection-order CSV fills
  injection order for matched SDO/LEK rows or reports exact unmatched names.
