# Lockbox Label Collection Pack v1

Status: `production_candidate` truth-collection package. This is not product
write authority.

## What To Label

Each lockbox case asks three separate questions:

1. `peak_choice_label`: is the candidate the right analyte/family peak?
2. `area_label`: is the candidate area usable for this case?
3. `boundary_label`: if the area is not usable, is the integration boundary
   visibly too wide, too narrow, shifted, or not assessable?

Use `docs/superpowers/validation/lockbox_label_template_v1.tsv` as the only
label entry sheet. It has two reviewer slots per case. Fill labels only after
opening the matching packet under
`docs/superpowers/validation/lockbox_review_packets_v1/`.

## Review UX

For visual review, open:

```text
docs/superpowers/validation/lockbox_static_review_v1/index.html
```

This static bundle has one page per lockbox case and Gaussian15-smoothed review
plots where trace evidence supports a Gaussian-derived review boundary. The
teal shaded window is the Gaussian15 review boundary; orange dotted lines are
the older candidate/raw boundary reference only. The plot is a
review/morphology view only: it does not change matrix values, workbook values,
selected peak, selected area, counted detection, or ProductWriter authority.
Cases without trace evidence, or with trace files that have no usable Gaussian
boundary, stay visibly marked as missing/unavailable evidence; do not infer
labels for them.

## Allowed Labels

`peak_choice_label`:

- `correct`
- `wrong_peak`
- `wrong_family`
- `unresolved`
- `insufficient_evidence`

`area_label`:

- `acceptable`
- `unacceptable`
- `not_assessable`

`boundary_label`:

- `acceptable`
- `too_wide`
- `too_narrow`
- `shifted`
- `not_assessable`

`reviewer_confidence`:

- `high`
- `medium`
- `low`

`reviewer_reason_code`:

- `visual_trace_overlay_review`
- `positive_control_reconfirmation`
- `negative_control_rejection`
- `competing_peak_ambiguity`
- `family_identity_ambiguity`
- `wrong_peak_visible`
- `wrong_family_visible`
- `area_unreliable`
- `boundary_too_wide`
- `boundary_too_narrow`
- `boundary_shifted`
- `insufficient_visual_evidence`
- `reviewer_escalation`

`evidence_viewed`:

- `packet`
- `packet_trace_overlay_hypothesis`
- `packet_recovered_trace_overlay_hypothesis`
- `packet_missing_evidence_record`

## Rules

- Do not invent labels. Leave cells blank until a human reviewer fills them.
- Do not enter replacement areas, replacement RTs, or free-form product values.
- Do not use the current round-trip oracle as peak-choice or area truth.
- Do not treat ISTD as analyte peak-choice or area truth.
- Do not use these labels as ProductWriter authority.
- Do not change matrix, workbook, selected peak, selected area, counted
  detection, default extraction, or GUI behavior from this package.
- Disagreement is expected evidence. Do not force consensus in the label sheet.

## Current Imported Batch

`docs/superpowers/validation/lockbox_reviewer_label_log_v1.tsv` records the
first 2026-06-18 user batch review over the static Gaussian15 review UX. It is
one reviewer pass, not the completed two-reviewer lockbox template.

The generated truth summary is:

```text
docs/superpowers/validation/lockbox_truth_summary_v1.json
```

Current decision: `truth_supports_review_only`.

Meaning in plain language: the 53 cases with usable Gaussian15 static review
plots were visually accepted for peak choice, area usability, and boundary
quality in this first pass; the 18 missing-evidence cases plus 1 unusable
Gaussian-boundary case remain not assessable. This supports the review workflow
and records the evidence gap, but it still does not grant ProductWriter or
matrix write authority.

## Validation

Structural check:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_lockbox_label_schema.py
```

Static review UX check:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_static_review_bundle.py --check-only
```

Local evidence-file hash check, only on a machine with the referenced
`output/` artifacts:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_lockbox_label_schema.py --verify-evidence-files
```

Completed-label check after human labeling:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_lockbox_label_schema.py --require-complete
```

The completed-label check requires two distinct non-empty reviewer IDs per
case, legal enum labels, legal reason codes, legal `evidence_viewed` values,
and unchanged source artifact hashes. It still does not grant product
authority.

Truth-summary import/check:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/import_lockbox_labels.py --generate-user-batch-log
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/import_lockbox_labels.py --check-only
```

The import gate checks static-bundle hash binding, row identity, legal labels,
and no-authority flags. Its output is a decision packet, not a writer input.

Next-action split after the first review batch:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_next_action_plan.py
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_next_action_plan.py --check-only
```

This writes `lockbox_next_action_plan_v1.tsv` and
`lockbox_next_action_summary_v1.json`. Current meaning: 53 plotted Gaussian15
cases are ready for a second independent reviewer; 6 manual wrong-peak/no-peak
cases are existing negative controls; 12 round-trip-oracle negative cases remain
parked because that oracle is not independent peak-choice or area truth; 1
Gaussian boundary-unavailable case needs signal/evidence recovery or remains
not assessable. None of these routes grants write authority.

Second-review collection pack:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_second_review_pack.py
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_second_review_pack.py --check-only
```

This writes `lockbox_second_review_queue_v1.tsv`,
`lockbox_second_review_template_v1.tsv`,
`lockbox_second_review_summary_v1.json`, and
`lockbox_second_review_v1/index.html`. Current meaning: only the 53 plotted
Gaussian15 cases enter reviewer slot 2. The template intentionally leaves all
label fields blank; Codex must not invent the second review. The remaining 19
cases stay outside this collection pack. The linked static pages and plots use
the Gaussian15-smoothed boundary as the review basis. This packet still cannot
feed ProductWriter, touch matrices, alter workbooks, or unpark broad Backfill.
