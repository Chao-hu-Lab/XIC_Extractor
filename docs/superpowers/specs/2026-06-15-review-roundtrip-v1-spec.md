# Review roundtrip v1 spec

日期: 2026-06-15
狀態: first_slice_review_action_import + second_slice_application_plan +
third_slice_expected_diff_template + fourth_slice_apply_readiness_plan +
fifth_slice_apply_changeset_plan
目標 tier: `missing` -> `production_candidate` for action import and dry-run
application/expected-diff/apply-readiness/changeset planning only
控制台: [productization control plane](../plans/2026-06-15-productization-control-plane.md)

## Productization intake

- Feature/lane: `review_roundtrip_v1`
- Current tier:
  - `Review Queue`: `production_surface` as worklist
  - manual boundary / reintegration: `missing`
- Desired tier this slice: `production_candidate` for typed review action import,
  validation, dry-run application plan, and approved expected-diff consumption
  gate
- Product surface touched:
  - `xic_extractor.review_actions`
  - `scripts/validate_review_actions.py`
  - `scripts/plan_review_action_applications.py`
  - `scripts/validate_review_action_expected_diffs.py`
  - `scripts/plan_review_action_apply_readiness.py`
  - `scripts/plan_review_action_apply_changesets.py`
  - future manual review action TSV/CSV schema
  - future mutating-action expected-diff approval TSV schema
- Domain authority owner:
  - `xic_extractor.review_actions` owns action import schema and safety validation.
  - It does not apply actions, recompute area, switch selected candidates, or write matrix values.
- Files/modules likely touched:
  - `xic_extractor/review_actions.py`
  - `scripts/validate_review_actions.py`
  - `scripts/plan_review_action_applications.py`
  - `tests/test_review_actions.py`
- Public contract affected:
  - Adds `review_action_v1` import schema.
  - Adds action types: `accept_current`, `mark_unresolved`, `reject_current`,
    `select_candidate`, `set_manual_boundary`.
- Expected output change:
  - none for extraction outputs.
  - validator reads review action files and returns success/error summary.
  - planner writes additive `review_action_application_plan_v1` TSV for dry-run
    audit/expected-diff review.
  - apply-readiness planner writes additive `review_action_apply_readiness_v1`
    TSV for ready/blocked future apply audit.
  - changeset planner writes additive `review_action_apply_changeset_v1` TSV
    naming future operation, output scope, and recompute/sidecar needs.
- Expected-diff needed: no for this slice; yes before any action can change selected peak, area, counted detection, product state, or workbook/matrix values.
- Validation fixture: focused unit/CLI tests.
- Stop rule:
  - Stop before applying actions to extraction outputs.
  - Stop if action import needs to infer candidate/boundary identity from display-only workbook fields.
  - Stop before recomputing manual boundary area, switching selected candidate,
    changing counted detection, or writing workbook/matrix values.
- Rollback rule:
  - Remove the validator and `review_actions` schema module; no extraction output is affected.
- Downstream consumer:
  - next review reintegration slice.

Product direction update, 2026-06-17: the long-term target is low-manual
intervention. The system should generate bounded candidate switches, manual
boundary recompute proposals, expected-diff packets, and audit outputs so the
user reviews only a small number of obvious or representative cases. This does
not relax the current stop rule: selected peak, selected area, counted
detection, workbook values, or matrix values still must not change without
stable IDs, sidecar contracts, and approved expected-diff evidence.

## First slice contract

This slice intentionally does not implement full review roundtrip. It only
creates the import gate required before roundtrip can be safe.

### Required columns

| Column | Meaning |
|---|---|
| `schema_version` | Must be `review_action_v1`. |
| `sample_name` | RAW/sample identity. |
| `target_label` | Target identity. |
| `action_type` | One of the supported review action types. |
| `candidate_id` | Required for `select_candidate`; must come from candidate sidecars in a later slice. |
| `boundary_id` | Optional v1 pointer for boundary sidecars. |
| `rt_left_min` | Required for `set_manual_boundary`. |
| `rt_apex_min` | Required for `set_manual_boundary`. |
| `rt_right_min` | Required for `set_manual_boundary`. |
| `comment` | Required for `reject_current`; recommended for all mutating actions. |
| `reviewer` | Human/operator identity when available. |
| `reviewed_at` | Human review timestamp when available. |
| `expected_diff_required` | Must be `TRUE` for mutating actions. |

### Mutating actions

The following actions are product-mutating candidates and must not be applied
without expected-diff review:

- `reject_current`
- `select_candidate`
- `set_manual_boundary`

`accept_current` and `mark_unresolved` are importable without expected-diff, but
they still do not change output in this first slice.

## Second slice contract: dry-run application plan

This slice still does not modify extraction outputs. It matches validated review
actions against the current targeted long output and writes a plan that names
which actions are safe no-output-change records and which actions are blocked
until a later expected-diff/reintegration slice.

### Public surface

- `scripts/plan_review_action_applications.py`
- `review_action_application_plan_v1` TSV

### Required targeted input columns

| Column | Meaning |
|---|---|
| `SampleName` | Current output sample identity. |
| `Target` | Current output target identity. |

Optional current-state columns are copied into the plan when available:

- `Product State`
- `Counted Detection`
- `Review State`

### Application plan columns

The planner writes `review_action_application_plan_v1` rows with sample/target,
action type, current product/review state, expected-diff status, reviewer
metadata, and a reason string.

Current statuses:

- `planned_no_output_change`: `accept_current` can be recorded as review intent
  without changing product outputs in this slice.
- `planned_review_state_only`: `mark_unresolved` is recognized, but still needs
  an audit/write contract before becoming product output.
- `blocked_expected_diff_review`: `reject_current`, `select_candidate`, and
  `set_manual_boundary` are recognized but blocked before product mutation.
- `blocked`: target row is missing, duplicate, or action semantics are
  ambiguous.

### Explicit non-goals

- no selected candidate switch
- no manual boundary recompute
- no area/counting/product-state mutation
- no workbook or matrix rewrite
- no candidate sidecar lookup

## Third slice contract: expected-diff template and approval loader

This slice still does not modify extraction outputs. It adds the review gate
artifact needed before product-mutating ReviewActions can ever be applied.

### Public surface

- optional `scripts/plan_review_action_applications.py --expected-diff-template-tsv`
- `scripts/validate_review_action_expected_diffs.py`
- `review_action_expected_diff_v1` TSV
- `load_review_action_expected_diff_approvals(...)`

### Expected-diff template columns

The template includes a stable row id, sample/target/action identity, candidate
or boundary fields, expected public outputs touched, expected matrix impact,
baseline target state (`Product State`, `Counted Detection`, `Review State`),
evidence fields, reviewer verdict, final label, reviewer metadata, comment, and
approval notes.

Template rows are intentionally not approvals:

- `validation_tier = not_validated`
- `reviewer_verdict = inconclusive`
- `final_label = inconclusive`

`load_review_action_expected_diff_approvals(...)` only accepts durable approved
rows where:

- `reviewer_verdict = approved`
- `final_label = expected_diff`
- `validation_tier != not_validated`
- evidence sources and evidence summary are present
- matrix-affecting expected diffs assess matrix impact and are not approved
  from synthetic-only validation
- the stable row id matches the ReviewAction identity
- the baseline target-state columns stay attached to the approval row so the
  apply-readiness gate can detect stale approvals

### Explicit non-goals

- no product-writing apply loop in this expected-diff template slice
- no approval consumption in extraction runtime
- no manual boundary area recompute
- no selected candidate switch
- no workbook or matrix rewrite

## Fourth slice contract: approved expected-diff consumption gate

This slice still does not modify extraction outputs. It consumes approved
expected-diff rows and writes a dry-run apply-readiness plan. The plan says which
ReviewActions are ready for a future product-writing loop and which are still
blocked.

### Public surface

- `scripts/plan_review_action_apply_readiness.py`
- `review_action_apply_readiness_v1` TSV
- `plan_review_action_apply_readiness(...)`

### Inputs

- `review_action_v1` TSV/CSV
- current targeted long CSV/TSV with `SampleName` and `Target`
- for product-mutating expected-diff readiness, current targeted rows must also
  expose `Product State`, `Counted Detection`, and `Review State`; missing or
  blank baseline state blocks readiness
- optional approved `review_action_expected_diff_v1` TSV

### Current apply-readiness statuses

- `ready_no_output_change`: `accept_current` has no product mutation.
- `ready_expected_diff_approved`: a product-mutating action has a matching
  approved expected-diff row whose baseline target state still matches the
  current targeted row.
- `blocked_expected_diff_missing`: a product-mutating action still lacks a
  matching approved expected-diff row.
- `blocked_expected_diff_baseline_missing`: a matching approval exists, but the
  approval row or current targeted row lacks `Product State`,
  `Counted Detection`, or `Review State` baseline values.
- `blocked_expected_diff_baseline_mismatch`: a matching approval exists, but it
  was reviewed against a different `Product State`, `Counted Detection`, or
  `Review State` than the current targeted row.
- `ready_review_state_only`: `mark_unresolved` can be written to an audited
  targeted-long output copy as `Review State = unresolved_by_review` without
  changing area, product state, counted detection, workbook, or final matrix.
- `blocked_application_plan`: the earlier application plan already blocked the
  action because target rows were missing, duplicated, or ambiguous.

By default, the CLI rejects unused expected-diff approvals so stale approvals do
not silently pass through a different action set. `--allow-unused-approvals`
exists only for explicitly reviewed subset/registry workflows.

### Explicit non-goals

- no product-writing apply loop in this apply-readiness slice
- no manual boundary area recompute
- no selected candidate switch
- no counted detection/product-state mutation
- no workbook or matrix rewrite

## Fifth slice contract: apply changeset contract

This slice converts apply-readiness rows into a field-scope changeset. The
changeset can now be consumed by a guarded writer that creates audited output
copies. It still does not overwrite extraction outputs, workbook files, or
primary matrices.

### Public surface

- `scripts/plan_review_action_apply_changesets.py`
- `scripts/apply_review_action_changesets.py`
- `review_action_apply_changeset_v1` TSV
- `review_action_apply_audit_v1` TSV
- `plan_review_action_apply_changesets(...)`
- `apply_review_action_changeset_rows(...)`

### Current changeset statuses

- `ready_audit_only`: review intent can be recorded without product mutation.
- `ready_review_state_only`: the action can update only `Review State` in an
  audited targeted-long copy.
- `ready_pending_product_writer`: the action has enough approval to be handed to
  a guarded writer. `reject_current` can update product/count/review state in an
  audited targeted-long copy; `select_candidate` and `set_manual_boundary`
  remain deferred because they need candidate sidecars or area recompute.
- `blocked`: the action is not ready for writing.

### Current operations

- `record_accept_current`: audit-only operation for `accept_current`.
- `mark_unresolved`: writes `Review State = unresolved_by_review` to the audited
  targeted-long output copy.
- `reject_current`: writes `Product State = rejected_by_review`,
  `Counted Detection = FALSE`, and `Review State = rejected_by_review` to the
  audited targeted-long output copy after approved expected-diff validation.
- `select_candidate`: records a deferred candidate-sidecar operation; it does
  not switch selected peak or area.
- `set_manual_boundary`: records a deferred area-recompute operation; it does
  not recompute area.

### Apply output contract

`scripts/apply_review_action_changesets.py` reads a current targeted long
CSV/TSV and a `review_action_apply_changeset_v1` TSV, then writes:

- an audited targeted long copy with additive `Review Action ...` audit columns;
- a `review_action_apply_audit_v1` TSV describing old state, new state, action,
  reviewer, expected-diff id, and deferred requirements.

The command refuses to overwrite the input targeted long file and rejects
blocked changeset rows by default.

### Explicit non-goals

- no selected candidate switch
- no manual boundary area recompute
- no workbook or primary matrix rewrite
- no in-place overwrite of extraction outputs
- no area or candidate change without the future recompute/sidecar writer

## Sixth slice contract: candidate sidecar verification

This slice still does not switch selected candidates. It verifies that a
`select_candidate` action's `candidate_id` is present and unique in the
targeted `peak_candidates.tsv` sidecar for the same `sample_name` /
`target_label`, then writes an additive readiness TSV.

### Public surface

- `scripts/plan_review_action_candidate_sidecars.py`
- `review_action_candidate_sidecar_v1` TSV
- `plan_review_action_candidate_sidecars(...)`
- `load_review_action_peak_candidate_rows(...)`

### Candidate sidecar statuses

- `action_duplicate`: more than one `select_candidate` action targets the same
  sample/target in the same review action packet.
- `candidate_verified`: the candidate id exists exactly once in
  `peak_candidates.tsv` for the action target.
- `candidate_current_selection`: the candidate id exists exactly once and is
  already marked `selected=TRUE`; this is evidence for a no-op/current
  selection, not a product switch.
- `candidate_missing`: the action target has candidate rows, but not the
  requested `candidate_id`.
- `candidate_duplicate`: the requested `candidate_id` is not unique for the
  action target.
- `target_candidate_rows_missing`: no candidate rows exist for the action's
  sample/target.

Each verified/current-selection row records a SHA-256 of the matched candidate
row plus candidate RT/area/confidence audit fields. Duplicate actions, missing
candidates, duplicate candidate rows, and missing target candidate rows fail
closed. This packet is an input to future expected-diff/reintegration work; it
does not authorize product output mutation by itself.

### Explicit non-goals

- no selected candidate switch
- no manual boundary area recompute
- no area/counting/product-state mutation
- no workbook or primary matrix rewrite
- no use of display-only workbook fields as candidate identity

## Implementation closeout

- Implemented owner: `xic_extractor.review_actions`
- Implemented public surface:
  - `REVIEW_ACTION_SCHEMA_VERSION = review_action_v1`
  - `REVIEW_ACTION_COLUMNS`
  - `REVIEW_ACTION_EXPECTED_DIFF_SCHEMA_VERSION = review_action_expected_diff_v1`
  - `REVIEW_ACTION_EXPECTED_DIFF_COLUMNS`
  - `REVIEW_ACTION_APPLY_READINESS_SCHEMA_VERSION = review_action_apply_readiness_v1`
  - `REVIEW_ACTION_APPLY_READINESS_COLUMNS`
  - `REVIEW_ACTION_APPLY_CHANGESET_SCHEMA_VERSION = review_action_apply_changeset_v1`
  - `REVIEW_ACTION_APPLY_CHANGESET_COLUMNS`
  - `REVIEW_ACTION_APPLY_AUDIT_SCHEMA_VERSION = review_action_apply_audit_v1`
  - `REVIEW_ACTION_APPLY_AUDIT_COLUMNS`
  - `REVIEW_ACTION_CANDIDATE_SIDECAR_SCHEMA_VERSION = review_action_candidate_sidecar_v1`
  - `REVIEW_ACTION_CANDIDATE_SIDECAR_COLUMNS`
  - typed `ReviewAction`
  - `load_review_actions(...)`
  - `summarize_review_actions(...)`
  - `load_review_action_target_states(...)`
  - `load_review_action_peak_candidate_rows(...)`
  - `plan_review_action_applications(...)`
  - `plan_review_action_candidate_sidecars(...)`
  - `plan_review_action_expected_diff_templates(...)`
  - `plan_review_action_apply_readiness(...)`
  - `plan_review_action_apply_changesets(...)`
  - `apply_review_action_changeset_rows(...)`
  - `load_review_action_expected_diff_approvals(...)`
  - `summarize_review_action_applications(...)`
  - `write_review_action_application_plan(...)`
  - `write_review_action_candidate_sidecar_plan(...)`
  - `write_review_action_expected_diff_template(...)`
  - `write_review_action_apply_readiness_plan(...)`
  - `write_review_action_apply_changeset_plan(...)`
  - `scripts/validate_review_actions.py`
  - `scripts/plan_review_action_applications.py`
  - `scripts/plan_review_action_candidate_sidecars.py`
  - `scripts/validate_review_action_expected_diffs.py`
  - `scripts/plan_review_action_apply_readiness.py`
  - `scripts/plan_review_action_apply_changesets.py`
- Tier after sixth slice: `production_candidate` for action import validation,
  dry-run application planning, candidate-sidecar verification,
  expected-diff approval template/loader, apply-readiness planning, and
  changeset planning only; audited targeted-long apply copy is
  `production_surface`; full review/reintegration remains parked for selected
  candidate switch and manual boundary area recompute.
- Expected-diff: approved rows can now be consumed into readiness rows; still no
  product-writing selected-candidate/manual-boundary loop and no mutating action
  can change selected peak, area, counted detection, workbook, or matrix through
  the candidate sidecar packet.
- Validation:
  - `python -m pytest tests\test_review_actions.py -q`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\review_actions.py scripts\plan_review_action_candidate_sidecars.py tests\test_review_actions.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\review_actions.py scripts\plan_review_action_candidate_sidecars.py`
- Residual blocker before full roundtrip:
  - no product-writing selected-candidate switch loop
  - no manual boundary recompute path
  - no audit trail export for applied review actions
  - no product-writing loop that consumes verified candidate sidecar rows plus
    approved expected-diff into selected peak/area output changes
