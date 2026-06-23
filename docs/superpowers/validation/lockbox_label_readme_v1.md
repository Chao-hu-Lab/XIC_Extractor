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
local_validation_artifacts/externalized_superpowers_validation/lockbox_static_review_v1/index.html
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
- In the current single-developer setting, subagents may be used for
  adversarial QA, link/hash checks, and obvious visual contradiction checks.
  They must not be entered into `reviewer_slot=2` as if they were a second
  independent human truth reviewer.

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

## Single-Developer Review Boundary

The first imported label batch is a valid owner/domain review pass. It is not a
completed two-human lockbox. If no second human reviewer is available, the next
safe move is to use a subagent as a non-authoritative challenge reviewer that
flags cases for owner re-review. That AI challenge output can reduce manual
work, but it must be stored separately from `reviewer_slot=2` unless a future
goal explicitly approves a downgraded single-owner + AI-challenge evidence
contract. The completed-label checker and truth-summary import gate now accept
human truth labels only from the explicit reviewer registry in
`docs/superpowers/specs/lockbox_label_schema_v1.json`; agent/subagent-looking or
unregistered reviewer IDs are rejected. Either way, labels still cannot become
ProductWriter authority without a later authority manifest update and
expected-diff product goal.

The owner confirmation for this boundary is recorded in:

```text
docs/superpowers/validation/lockbox_owner_boundary_confirmation_v1.json
```

That owner-boundary artifact records only upstream human-review evidence and
no-authority rules. It deliberately does not hash downstream second-review
summaries, so the AI challenge and second-review packets cannot form a cyclic
source-artifact dependency.

## AI Challenge Result

The non-authoritative AI/subagent challenge pass is recorded in:

```text
docs/superpowers/validation/lockbox_ai_challenge_result_log_v1.tsv
docs/superpowers/validation/lockbox_ai_challenge_result_summary_v1.json
```

Current decision: `ai_challenge_no_owner_recheck_required`.

Plain-language meaning: the AI/subagent challenge now has 72 of 72
`no_issue` rows. The previous flag for
`LOCKBOXV1_60CEB35837FAF38CC4DE9021` was resolved by the owner rule for
double-peak raw traces: when the Backfill/detect reference apex is on the left
peak, the current boundary is acceptable; if it is indistinguishable or on the
right peak, the case stays flagged. Existing recovered trace evidence records
`cell_apex_rt=15.1553` and `trace_apex_rt=15.1553` on the left peak, while the
right competing peak is around `15.4366`. This resolution is still not a truth
label, not a reviewer-slot-2 label, and not ProductWriter authority.

## Single-Owner + AI Challenge Gate

The current low-manual decision packet is recorded in:

```text
docs/superpowers/validation/lockbox_single_owner_ai_challenge_gate_v1.json
```

Build/check commands:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_single_owner_ai_challenge_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_single_owner_ai_challenge_gate.py --check-only
```

Current decision:
`single_owner_ai_challenge_supports_shadow_automation_experiment`.

Plain-language meaning: the owner has one clean review pass for 53 assessable
Gaussian15 cases, the AI challenge has zero open owner-recheck flags, and the
remaining 19 cases stay excluded as insufficient/not assessable. This is enough
to design a later shadow-only automation experiment, but it is not two-human
truth completion, not `reviewer_slot=2`, not ProductWriter authority, and not a
matrix/workbook/selected-peak/area/counting change.

## Shadow Automation Experiment Design

The current shadow-only experiment design packet is recorded in:

```text
docs/superpowers/validation/lockbox_shadow_automation_experiment_v1.json
docs/superpowers/validation/lockbox_shadow_automation_cases_v1.tsv
```

Build/check commands:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_shadow_automation_experiment_design.py
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_shadow_automation_experiment_design.py --check-only
```

Current decision: `shadow_scoring_contract_adapter_v1_ready`.

Plain-language meaning: all 72 lockbox cases now have an explicit shadow
contract route. 53 owner-clean Gaussian15 cases are non-authoritative accept
challenges, 6 existing manual wrong-peak/no-peak controls are reject hard
stops, and 12 round-trip-oracle negative cases plus 1
Gaussian-boundary-unavailable case remain `not_scored`. The result may only
write shadow contract fields and review flags.

The review boundary policy is now explicit: Gaussian15-smoothed boundaries are
the review basis. For raw-trace doublets, accept only when the Backfill/detect
reference is on the left peak; if the reference is indistinguishable or on the
right peak, keep the case flagged for review. This policy still does not grant
ProductWriter, matrix, workbook, selected-peak, selected-area, counted
detection, reviewer slot2, GUI, default extraction, or broad Backfill
authority.

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
the rendered index under
`local_validation_artifacts/externalized_superpowers_validation/lockbox_second_review_v1/index.html`.
Current meaning: only the 53 plotted Gaussian15 cases enter reviewer slot 2,
and only after the AI challenge result summary is current with
`ai_challenge_no_owner_recheck_required` and zero flagged cases. The template
intentionally leaves all label fields blank; Codex must not invent the second
review. The remaining 19 cases stay outside this collection pack. The linked
static pages and plots use the Gaussian15-smoothed boundary as the review
basis. This packet still cannot feed ProductWriter, touch matrices, alter
workbooks, or unpark broad Backfill.

AI challenge packet:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_ai_challenge_pack.py
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_ai_challenge_pack.py --check-only
```

This writes `lockbox_ai_challenge_queue_v1.tsv`,
`lockbox_ai_challenge_template_v1.tsv`,
`lockbox_ai_challenge_summary_v1.json`, and
the rendered index under
`local_validation_artifacts/externalized_superpowers_validation/lockbox_ai_challenge_v1/index.html`.
Current meaning: all 72 lockbox cases are available for non-authoritative
AI/subagent QA. The 53 plotted Gaussian15 cases may receive only visual
contradiction checks; the 19 non-ready cases may receive only route/evidence
integrity checks. The template intentionally leaves all challenge result fields
blank. AI challenge output cannot satisfy `reviewer_slot=2`, cannot become a
truth label, cannot feed ProductWriter, and cannot touch
matrix/workbook/selected peak/selected area/counted detection, default
extraction, GUI, or broad Backfill authority.
