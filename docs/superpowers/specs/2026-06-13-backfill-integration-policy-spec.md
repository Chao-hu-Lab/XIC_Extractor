# Backfill Integration Policy Spec

## Status

Design draft after critical review, with first standard-path seed guard slice
implemented on 2026-06-16.

Validation labels are split by lane:

- Standard-path cohort seed guard: `production_candidate` for the standard-path
  pre-activation guard only.
- Non-standard integration taxonomy: `diagnostic_only` / `design_input`.

This spec captures the current owner discussion about standard-peak backfill
seed support, non-standard peak integration, and area uncertainty. The
standard-path seed-support rule is now active in the
`standard_peak_backfill_productization.py` productization bridge as a
pre-activation filter. It does not add fields to `alignment_review.tsv`,
workbook schemas, public `area_policy`, or the primary matrix schema.

The non-standard taxonomy is not an implementation contract for matrix writes.
It is a classification and validation plan. Do not use it to add rows to an
activation allowlist, change `area_policy`, or reinterpret
`matrix_quantitative_use` without a separate schema/test/product contract.

## Decision Summary

Backfill policy has two separate decisions that must not be collapsed:

1. **Identity / same-peak support**: whether the missing cell is plausibly the
   same `PeakHypothesis` or feature.
2. **Quantitative integration support**: whether the area for that cell has a
   defensible boundary and baseline.

Current standard-peak backfill already has a product path. The next
implementation-candidate standard-path policy decision is a cohort-size banded
seed-support guard for the first implementation contract:

```text
if total_N < 20:
    seed_guard_status = "not_applicable_small_cohort"
    cohort_scale_automatic_backfill = False
elif total_N < 80:
    seed_floor = max(2, floor(total_N * 0.05))
    cohort_scale_automatic_backfill = False
else:
    seed_floor = max(4, floor(total_N * 0.05))
    cohort_scale_automatic_backfill = True
```

For `N=85`, this keeps the owner decision unchanged: `detected_count=4` remains
eligible for the existing evidence chain, while `detected_count=3` is blocked.
For smaller cohorts, the rule avoids pretending that a 5% prevalence test has
stable meaning. Small and medium cohorts can still produce per-cell review or
per-cell product decisions through existing identity/boundary/baseline gates,
but they must not trigger broad cohort-scale automatic backfill. This guard
belongs to the currently backfillable standard-peak pathway, not to a future
non-standard path.

Non-standard peaks do not yet have a production backfill policy. They should be
classified by integration pathology first, not by a single "backfill or do not
backfill" switch. Some non-standard shapes are area-assessable when the boundary
and baseline are defensible; others are unassessable even if identity evidence
is strong.

The first non-standard deliverable is a reviewed classification artifact:
`standard_assessable`, `nonstandard_assessable_review_only`,
`baseline_sensitive_review_only`, or `unassessable_hard_block`. It must not write
matrix values.

## Product Spine

This design advances:

- `IntegrationResult`: area, baseline, boundary, and uncertainty provenance.
- `AuditTrail`: why a cell is standard-assessable, non-standard-assessable,
  baseline-sensitive, or unassessable.
- `PeakHypothesis` activation policy: future blockers must remain scoped to
  `peak_hypothesis_id + sample`, not legacy family IDs alone.

This design does not make a diagnostic gallery, manual note, or area uncertainty
sidecar a matrix-writing authority. Any future matrix write still requires a
separate activation contract and matrix-diff acceptance.

## Implementation Lanes

Keep the lanes separate in code, tests, artifacts, and commit scope.

| Lane | Status | May change product matrix? | First deliverable | Stop condition |
| --- | --- | --- | --- | --- |
| Standard seed guard | `production_candidate` | Yes, but only as a blocker on the current standard-peak path | `seed_guard_decisions.tsv`, matrix-diff/write-attribution tests, heldout oracle result contract | Cannot prove `total_N`, `detected_count`, expected diff, and actual writes from the same pre-backfill source |
| Non-standard taxonomy | `diagnostic_only` | No | Gallery/TSV classifying boundary and baseline pathology | Any consumer tries to use the taxonomy as promotion authority |
| Baseline-sensitive audit | `diagnostic_only` | No | Baseline spread report over a named diagnostic-only baseline model set | Baseline set is missing, unstable, or not tied to row provenance |
| Future non-standard promotion | Not approved | Only after a new contract | Schema/test proposal for non-standard matrix writes | Missing manual/EIC or held-out oracle, uncertainty threshold, or matrix-diff acceptance |

The first implementation slice should be the standard seed guard only. It must
not introduce non-standard promotion, new public `area_policy` enums, or
baseline-sensitive matrix writes.

Implementation closeout, 2026-06-16:

- Owner: `xic_extractor.diagnostics.standard_peak_shadow_activation_inputs`
  owns seed-guard context loading, N-band rule evaluation,
  `seed_guard_decisions.tsv`, and heldout oracle result schema/evaluation.
- Productization bridge:
  `xic_extractor.diagnostics.standard_peak_backfill_productization` loads the
  pre-backfill `alignment_matrix.tsv` and `alignment_review.tsv`, passes the
  guard into activation-input construction, and then rewrites
  `seed_guard_decisions.tsv` with actual write attribution from
  `activation_value_delta.tsv`.
- N-band behavior is covered for `N=19`, `20`, `79`, `80`, `85`, and `>85`.
  `N<20` is `not_applicable_small_cohort`; `20<=N<80` can only be
  `eligible_per_cell_only` when the floor passes; `N>=80` can continue toward
  cohort-scale standard backfill only when the large-cohort floor passes.
- Candidate coverage: the guard artifact contains one row per standard-path
  promotion candidate after the existing standard-peak gate and before
  activation decision writing. Non-standard/context rows are not seed-guard
  candidates.
- Write attribution: final productization output joins actual written cells
  from `activation_value_delta.tsv` by `peak_hypothesis_id/sample_stem` and
  records cohort-scale vs per-cell written counts.
- Heldout oracle result contract: deterministic manifest/result evaluation is
  implemented and tested, but no real/reviewed heldout oracle run was executed
  in this slice.
- Heldout oracle CLI closeout, 2026-06-17:
  `tools/diagnostics/standard_peak_heldout_oracle_results.py` now exposes the
  evaluator as an executable gate. It reads `heldout_oracle_manifest.tsv`, reads
  observed boundary/area result rows, records the result source artifact SHA,
  and writes `heldout_oracle_results.tsv` using
  `standard_peak_seed_guard_heldout_oracle_results_v1`. This still does not
  create reviewed oracle rows, run RAW, mutate matrices, or authorize
  non-standard peaks.
- Review hardening closeout, 2026-06-17:
  after subagent review, both the heldout oracle CLI and package evaluator now
  require the full manifest public schema listed below, including
  `mask_strategy`, `target_shape_class`, `baseline_model_set`,
  `baseline_epsilon`, `baseline_residual_threshold`, and
  `expected_integration_pathology`, and lock
  `schema_version=standard_peak_seed_guard_heldout_oracle_manifest_v1`.
  Observed result rows are fail-closed when a duplicate `oracle_case_id`
  appears or when an observed case is not present in the manifest.
  After the 2026-06-17 product decision, manifest rows also fail closed when
  `acceptable_boundary_delta_min` is looser than `0.1` or
  `acceptable_area_relative_error` is looser than `0.10`; reviewed rows may be
  stricter, but cannot widen the first production-readiness gate. Exact
  threshold results use a tiny floating-point guard band so a mathematical
  `0.1 min` boundary error or `0.10` area error is not rejected only because of
  binary float representation.
  Productization also treats any
  `write_authority_status=blocked_unattributed_write` in rewritten
  `seed_guard_decisions.tsv` as `status=fail` with
  `next_action=review_seed_guard_write_attribution_failure`.
- Heldout observed-result provenance closeout, 2026-06-17:
  `heldout_observed_results.tsv` rows are now a public input contract rather
  than loose numeric rows. The CLI and package evaluator require
  `observed_result_source`, `observed_boundary_source`,
  `observed_area_source`, and `observed_independence_basis`; allowed
  independence bases are `product_writer_observed_result`,
  `masked_rerun_observed_result`, and
  `independent_boundary_reintegration_result`. Rows that identify the observed
  source as an oracle/manual-review/review-queue copy fail closed, including
  common whitespace and hyphen variants. The evaluator also requires the
  `result_source_artifact_path` to point to an existing file so
  `result_source_artifact_sha256` cannot be blank. This closes the contract gap
  found by the source audit without fabricating reviewed observed boundaries
  from existing artifacts.
- Heldout observed-source cross-check closeout, 2026-06-17:
  after reviewer `Ptolemy` found a neutral-label bypass, observed rows are also
  validated against their matching manifest row. `observed_result_source`,
  `observed_boundary_source`, and `observed_area_source` cannot canonicalize to
  the same label as the manifest `oracle_source`; repeated whitespace and
  punctuation separators collapse before comparison. This blocks a future
  held-out gate from passing by relabeling the oracle row with a neutral source
  name.
- Heldout original-cell-status guard, 2026-06-17:
  `heldout_oracle_manifest.tsv` now requires
  `heldout_original_cell_status`, and the evaluator accepts only originally
  detected quantifiable statuses: `detected`, `detected_seed`,
  `quantifiable_detected`, or `accepted_detected`. `rescued` cells fail closed
  and cannot count as held-out oracle product-readiness evidence. This matters
  for the two current raw85 reviewed rows that match seed-guard candidates:
  their existing trace artifacts identify the matched sample rows as `rescued`,
  so they remain useful manual support but not valid production-ready held-out
  oracle cases.
- No-RAW 85RAW artifact bridge closeout, 2026-06-17:
  `tools.diagnostics.standard_peak_backfill_productization` was run against the
  existing 85RAW validation-minimal matrix/review and chunk `r1_120` shadow
  projection under `output/standard_peak_backfill_preset_85raw_20260610/`.
  The bridge emitted
  `output/productization_realdata_seed_guard_85raw_20260617/r1_120_no_raw_productization/standard_peak_activation_inputs/seed_guard_decisions.tsv`
  with 2540 standard-path candidates: 1160
  `eligible_continue_existing_gates` rows and 1380
  `blocked_low_seed_support` rows. The resulting
  `activation_value_delta.tsv` has 1160 rows and the summary reports
  `matrix_cells_written=1160`. This validates candidate coverage plus actual
  write attribution on a real 85RAW-derived artifact without opening RAW files.
  It does not replace reviewed heldout oracle cases or approve the 85RAW
  expected diff as a production-ready product change.
- Consolidated no-RAW 85RAW artifact bridge closeout, 2026-06-17:
  the same current productization bridge was run against the existing
  consolidated 85RAW shadow projection
  `standard_peak_backfill_preset/consolidated/consolidated_shadow_projection_cells.tsv`
  plus the pre-standard-backfill matrix/identity files from the same
  validation-minimal output. The bridge emitted
  `output/productization_realdata_seed_guard_85raw_20260617/consolidated_no_raw_productization/standard_peak_activation_inputs/seed_guard_decisions.tsv`
  with 7307 standard-path candidates: 4613
  `eligible_continue_existing_gates` rows and 2694
  `blocked_low_seed_support` rows. The resulting
  `activation_value_delta.tsv` has 4613 rows, the summary reports
  `matrix_cells_written=4613`, and there are zero
  `blocked_unattributed_write` rows. This strengthens the
  `production_candidate` evidence across the full existing 85RAW consolidated
  artifact without opening RAW files. It still does not replace reviewed
  heldout oracle cases or approve the 85RAW expected diff as a production-ready
  product change.
- Heldout oracle source audit, 2026-06-17:
  no ready `heldout_oracle_manifest.tsv`, observed oracle TSV, or
  `heldout_oracle_results.tsv` was found under `output/`. The audit output is
  under
  `output/productization_realdata_seed_guard_85raw_20260617/heldout_oracle_source_audit/`.
  It crosswalks 11 raw85 manual verdict rows from
  `backfill_peakhypothesis_raw85_manual_verdicts.tsv` against the current
  consolidated seed-guard decisions. All 11 manual rows have source
  boundary/area values that can seed an oracle manifest, but only 2 match
  current seed-guard candidate keys. Those 2 have observed area through
  `activation_value_delta.tsv`, but they still lack independent observed
  start/end boundary values. The other 9 do not match current seed-guard
  candidate keys. Therefore this lane remains `production_candidate`; the
  `production_ready` checkpoint is blocked on independent observed
  boundary/area result rows satisfying the provenance contract above, not
  merely on running the existing evaluator.
- Heldout trace reintegration oracle, 2026-06-17:
  a bounded originally detected heldout oracle was generated without rerunning
  RAW under
  `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle/`.
  The artifact selects 20 deterministic high-signal clean standard trace cases
  across 20 families from the existing 85RAW validation-minimal trace/evidence
  outputs: originally detected, sample-local MS1 owner with original MS2
  evidence, primary matrix area source
  `gaussian15_positive_asls_residual`, shape similarity >=0.95,
  local/global max ratio >=0.95, cell height >=2e6, original boundary width
  0.30-0.65 min, apex within 0.15 min of family center, and at least 10 scans.
  The observed rows use the existing local-minimum `find_peak_and_area` plus
  `integration_from_peak_trace` over stored trace arrays and are marked with
  `observed_independence_basis=independent_boundary_reintegration_result`.
  The formal heldout oracle CLI wrote `heldout_oracle_results.tsv` with 20/20
  `pass`, 20/20 `included_in_product_acceptance=TRUE`, maximum boundary error
  0.0820502 min, and maximum area relative error 0.0762325. This closes the
  first high-signal clean standard trace oracle checkpoint under the accepted
  `0.1 min / 10% area` ceiling. The same output directory now also contains
  `heldout_trace_reintegration_full_eligible_pool.tsv`, which persists all 80
  pre-observed eligible rows with quality rank, selected flag, and rejection
  reason; unselected rows do not carry observed reintegration outcomes. This is
  the anti-cherry-pick audit surface for the 20 selected cases.
- Heldout low-scan trace reintegration oracle, 2026-06-17:
  `tools/diagnostics/standard_peak_heldout_trace_oracle.py` now makes the
  previously one-off trace-oracle generation reproducible from existing
  `alignment_backfill_cell_evidence.tsv` and `*_trace_data.json` artifacts. The
  low-scan clean scope keeps the same trace status, shape >=0.95,
  local/global >=0.95, height >=2e6, boundary width 0.30-0.65 min, and apex
  within 0.15 min constraints, but requires 7-9 boundary scans instead of at
  least 10. The no-RAW 85RAW run under
  `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle_low_scan_clean_probe/`
  found 56 eligible detected-cell candidates across 11 families, selected all
  11 family-representative cases, and wrote `heldout_oracle_results.tsv` with
  11/11 `pass` and 11/11 `included_in_product_acceptance=TRUE`. Maximum
  boundary error was `4.86717e-05` min and maximum area relative error was
  `0.038786`, within the accepted `0.1 min / 10% area` ceiling. This evidence
  supports only the explicit low-scan clean trace scope; it still does not
  authorize broad 4613-row activation or non-standard peak promotion.
- Broad activation scope note, 2026-06-17:
  the trace reintegration oracle above is positive evidence, not a blanket
  promotion of every current standard-path activation write. The consolidated
  no-RAW bridge still reports 4613 eligible activation writes, and the current
  productization bridge is not limited to the high-signal clean trace
  eligibility used by the oracle artifact. The activation scope audit under
  `output/productization_realdata_seed_guard_85raw_20260617/high_signal_clean_activation_scope_audit/`
  joins all 4613 written activation rows back to projection rows and available
  trace JSON: 72 rows are high-signal clean eligible, 3454 are trace-matched but
  outside the high-signal clean envelope, and 1087 are missing overlay/trace
  evidence. The follow-up `narrow_activation_expected_diff_acceptance.json`
  verifies that the 72-row eligible delta is a clean subset of the full
  `activation_value_delta.tsv` with no duplicate, missing, unexpected,
  non-eligible, unchanged, non-written, or blank-value rows. The next
  `standard_peak_backfill_productization.py` slice implements the explicit
  writer contract for this scope through
  `--high-signal-clean-activation-scope-audit-tsv`; the real no-RAW 85RAW
  consolidated run under
  `output/productization_realdata_seed_guard_85raw_20260617/narrow_high_signal_clean_no_raw_productization/`
  selected 72 eligible shadow rows, wrote 72 matrix cells, and emitted
  `narrow_product_writer_expected_diff_acceptance.json` with
  `acceptance_status=pass`, `readiness_tier=production_ready`, and zero
  duplicate, missing, unexpected, non-eligible, non-written, unchanged, or
  blank-value rows. Therefore the explicit 72-row high-signal-clean writer
  slice is `production_ready`. The same activation scope audit now also writes
  `low_scan_clean_activation_value_delta.tsv` and
  `low_scan_clean_activation_expected_diff_acceptance.json`; the real 85RAW
  no-RAW combined-scope audit found 42 low-scan clean eligible writes and the
  expected-diff gate passed with 42/42 eligible rows and zero duplicate,
  missing, unexpected, non-eligible, unchanged, non-written, or blank-value
  rows. The opt-in writer run under
  `output/productization_realdata_seed_guard_85raw_20260617/narrow_low_scan_clean_no_raw_productization/`
  selected 42 rows, wrote 42 matrix cells, and emitted
  `narrow_product_writer_expected_diff_acceptance.json` with
  `acceptance_status=pass`, `readiness_tier=production_ready`,
  `expected_scope=low_scan_clean_eligible_activation_rows`, and zero blockers.
  Therefore the explicit 42-row low-scan clean writer slice is also
  `production_ready`. Later scoped writers extended the same explicit contract:
  low-height clean writes 57 cells after bounded-window oracle approval,
  low-height-low-scan clean writes 69 cells after bounded-window oracle
  approval, and low-height reintegration-stable writes 220 cells after
  family-scope oracle approval plus writer expected-diff. These five slices are
  current `production_ready` demonstrators; the broad 4613-row standard-path
  seed guard lane remains `production_candidate` until it has broader
  masked/product-writer observed oracle coverage and expected-diff approval for
  any additional writes.
- Heldout low-height trace reintegration probe, 2026-06-17:
  `tools/diagnostics/standard_peak_heldout_trace_oracle.py` also supports
  `standard_low_height_clean_trace`, where all clean trace constraints remain
  in force except `cell_height < 2e6`. This is intentionally a probe, not a
  writer contract. The no-RAW 85RAW packet under
  `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle_low_height_clean_probe/`
  found 230 eligible candidates across 54 families, selected 20
  family-representative cases, and failed with 19/20 pass. The failing case
  `HOLDOUT85TRACE001_FAM008651_TumorBC2312_DNA` had boundary error
  `1.16445 min`, exceeding the accepted `0.1 min` tolerance, while its area
  relative error was about `0.033`. The activation scope audit found 57
  low-height clean eligible writes out of 4613 and
  `low_height_clean_activation_expected_diff_acceptance.json` passed 57/57
  with `product_surface_changed=FALSE`; at that historical checkpoint
  low-height was only `production_candidate`. It was later promoted only after
  a narrower bounded-window oracle packet passed 20/20 at `padding=0.5 min`,
  followed by the explicit
  `--low-height-clean-activation-scope-audit-tsv` product writer with 57/57
  writer expected-diff pass and `readiness_tier=production_ready`. The original
  full-trace 19/20 failure remains evidence that low-height must not be
  broadened without a named oracle rule.
- Low-height reintegration-stable scoped writer, 2026-06-17:
  this follow-up uses the reintegration-stability audit as a candidate pool but
  does not promote all 299 eligible rows. A quick all-stability family check
  had 19/20 pass with one area failure
  (`FAM000949/NormalBC2261_DNA`, area relative error about 19.6%), so direct
  all-stability writer approval remains blocked. The promoted scope is
  stability-eligible written rows whose activation audit has `cell_height <2e6`.
  `standard_low_height_reintegration_stable_candidate_family_trace` requires
  both `--reintegration-stability-audit-tsv` and
  `--activation-scope-audit-tsv`, yielding 220 audit-intersection rows / 66
  families on the current 85RAW no-RAW artifact. The formal family-scope oracle
  is not a row-identity oracle: it records
  `candidate_family_scope_match_level=family_id`,
  `candidate_family_scope_oracle_basis=detected_trace_rows_from_candidate_families`,
  and 1520 available detected trace candidates from those same families. It
  selected 20 family cases and passed 20/20 with max boundary error
  `0.0830019 min` and max area relative error `0.0725986`. The matching
  explicit writer requires
  `--low-height-reintegration-stable-activation-scope-audit-tsv` plus
  `--reintegration-stability-audit-tsv`; the real no-RAW writer run selected
  and wrote 220 cells and its
  `narrow_product_writer_expected_diff_acceptance.json` reports
  `acceptance_status=pass`, `readiness_tier=production_ready`,
  `expected_scope=low_height_reintegration_stable_eligible_activation_rows`,
  and zero duplicate/missing/unexpected/non-eligible/non-written/unchanged/blank
  blockers. This adds 199 cells outside the previous four ready scopes and
  brings the five-scope ready union to 439 cells.
- Generated policy path, 2026-06-17:
  `standard_peak_backfill_productization.py` now has a broad policy-engine
  entry point, `--backfill-policy-source-audit-tsv`. It generates
  `standard_peak_backfill_policy.tsv` for every supplied source-audit row and
  classifies each candidate as `write_ready`, `detected_flagged`, or `blocked`.
  The product writer then replays only generated `write_ready` rows through the
  existing matrix-only activation writer and expected-diff acceptance. This is
  not a new production-ready claim for broad 4613-row activation: the current
  ready evidence classes still come from the five approved writer envelopes.
  The purpose is to stop proliferating manual/nested scoped writer flags and
  make future broadening happen by adding evidence classes to a single
  auditable policy engine.
- Heldout apex-delta trace reintegration probe, 2026-06-17:
  `tools/diagnostics/standard_peak_heldout_trace_oracle.py` also supports
  `standard_apex_delta_clean_trace`, where supported trace status, shape
  `>=0.95`, local/global `>=0.95`, height `>=2e6`, boundary width
  `0.30-0.65 min`, and `>=10` scans remain in force, but apex delta from the
  family center is greater than `0.15 min`. This probe is not a writer
  contract. The no-RAW 85RAW packet under
  `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle_apex_delta_clean_probe/`
  found 78 eligible candidates across 27 families, selected 20
  family-representative cases, and failed with 17/20 pass. The three failing
  rows were `fail_boundary`, with max boundary error `2.19621 min` and max area
  relative error `0.424518`; two failures already had apex deltas near
  `0.25-0.27 min`, so a simple broad apex-delta threshold is not sufficient
  evidence for automatic matrix writes. There is no apex-delta scoped writer
  flag and no `production_ready` claim is allowed for this class.
- Heldout width trace reintegration probe, 2026-06-17:
  `tools/diagnostics/standard_peak_heldout_trace_oracle.py` also supports
  `standard_width_clean_trace`, where supported trace status, shape `>=0.95`,
  local/global `>=0.95`, height `>=2e6`, apex delta `<=0.15 min`, and `>=10`
  scans remain in force, but boundary width falls outside `0.30-0.65 min`.
  This probe is not a writer contract. The no-RAW 85RAW packet under
  `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle_width_clean_probe/`
  found 4 eligible candidates across 3 families, selected 3
  family-representative cases, and failed with 1/3 pass. The failures include
  one area failure and one boundary failure, with max boundary error
  `1.86561 min` and max area relative error `0.599229`. There is no
  width-only scoped writer flag and no `production_ready` claim is allowed for
  this class.
- Product direction update, 2026-06-17:
  the 72-row high-signal, 42-row low-scan, 57-row low-height,
  69-row low-height-low-scan, and 220-row low-height reintegration-stable
  scopes are safe demonstrators, not the intended ceiling.
  The product north star is to backfill automatically whenever evidence is
  sufficient. Future slices should broaden the evidence class or observed-oracle
  coverage and then approve the additional matrix writes through their own
  expected-diff packet; they must not silently treat the existing 72-row
  acceptance as approval for all 4613 broad writes.
- Validation:
  - `python -m pytest tests\test_standard_peak_shadow_activation_inputs.py tests\test_standard_peak_backfill_productization.py -q`
  - `python -m pytest tests\test_standard_peak_shadow_activation_inputs.py::test_standard_peak_heldout_oracle_results_cli_writes_contract_tsv tests\test_standard_peak_shadow_activation_inputs.py::test_standard_peak_heldout_oracle_results_classify_boundary_and_area -q`
  - `python -m pytest tests\test_standard_peak_shadow_activation_inputs.py::test_standard_peak_heldout_oracle_results_cli_requires_full_manifest_schema tests\test_standard_peak_shadow_activation_inputs.py::test_standard_peak_heldout_oracle_results_rejects_ambiguous_observed_rows tests\test_standard_peak_backfill_productization.py::test_standard_peak_productization_fails_on_unattributed_seed_guard_write -q`
  - `python -m pytest tests\test_standard_peak_shadow_activation_inputs.py::test_standard_peak_heldout_oracle_results_cli_rejects_wrong_manifest_version -q`
  - `python -m pytest tests\test_standard_peak_shadow_activation_inputs.py::test_standard_peak_heldout_oracle_results_rejects_incomplete_manifest_mapping -q`
  - `python -m pytest tests\test_standard_peak_shadow_activation_inputs.py::test_standard_peak_heldout_oracle_results_rejects_loose_tolerances tests\test_standard_peak_shadow_activation_inputs.py::test_standard_peak_heldout_oracle_results_accepts_strict_tolerances -q`
  - `python -m pytest tests\test_standard_peak_shadow_activation_inputs.py::test_standard_peak_heldout_oracle_results_accepts_exact_boundary_tolerance tests\test_standard_peak_shadow_activation_inputs.py::test_standard_peak_heldout_oracle_results_accepts_exact_area_tolerance -q`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.standard_peak_backfill_productization ... --source-run-id seed-guard-realdata-85raw-r1-120-20260617`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.standard_peak_backfill_productization ... --source-run-id seed-guard-realdata-85raw-consolidated-20260617`
  - subagent reviewer `Popper` rechecked the consolidated no-RAW artifacts and
    found no blocking overclaim; this remains `production_candidate` evidence,
    not reviewed-oracle or `production_ready` evidence.
  - no-RAW source audit wrote
    `heldout_oracle_source_audit/raw85_manual_verdict_seed_guard_crosswalk.tsv`
    and `heldout_oracle_source_audit/summary.json`.
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_shadow_activation_inputs.py -k heldout_oracle -q`
    (`25 passed`) after the observed-result provenance contract hardening,
    original-cell-status guard, and observed-source cross-check fixes.
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_shadow_activation_inputs.py tests\test_standard_peak_backfill_productization.py -q`
    (`42 passed`) after the same fixes.
  - touched-file ruff/mypy for the standard-peak modules and tests.
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.standard_peak_heldout_oracle_results --heldout-oracle-manifest-tsv output\productization_realdata_seed_guard_85raw_20260617\heldout_trace_reintegration_oracle\heldout_oracle_manifest.tsv --observed-results-tsv output\productization_realdata_seed_guard_85raw_20260617\heldout_trace_reintegration_oracle\heldout_observed_results.tsv --result-source-artifact output\productization_realdata_seed_guard_85raw_20260617\heldout_trace_reintegration_oracle\heldout_observed_results.tsv --output-tsv output\productization_realdata_seed_guard_85raw_20260617\heldout_trace_reintegration_oracle\heldout_oracle_results.tsv`
    (`20` heldout oracle cases; all pass/included).
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_activation_scope_audit.py -q`
    (`5 passed`) for the activation scope audit builder/CLI.
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_activation_scope_audit.py tests\test_standard_peak_backfill_productization.py -q`
    (`10 passed`) for the activation scope audit and narrow product writer
    contract.
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.standard_peak_activation_scope_audit --activation-value-delta-tsv output\productization_realdata_seed_guard_85raw_20260617\consolidated_no_raw_productization\activated_matrix\activation_value_delta.tsv --shadow-projection-cells-tsv output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\standard_peak_backfill_preset\consolidated\consolidated_shadow_projection_cells.tsv --output-dir output\productization_realdata_seed_guard_85raw_20260617\high_signal_clean_activation_scope_audit --source-run-id seed-guard-realdata-85raw-consolidated-high-signal-scope-20260617`
    (`broad_activation_scope_status=not_ready`; 72 high-signal clean eligible
    writes out of 4613 in the first run; rerun as
    `seed-guard-realdata-85raw-consolidated-combined-scope-20260617` also
    reports 42 low-scan clean eligible writes; both expected-diff artifacts
    report `acceptance_status=pass` and `product_surface_changed=FALSE`).
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.standard_peak_backfill_productization --shadow-projection-cells-tsv output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\standard_peak_backfill_preset\consolidated\consolidated_shadow_projection_cells.tsv --alignment-matrix-tsv output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\alignment_matrix.pre_standard_peak_backfill.tsv --alignment-matrix-identity-tsv output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\alignment_matrix_identity.pre_standard_peak_backfill.tsv --alignment-review-tsv output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\alignment_review.tsv --output-dir output\productization_realdata_seed_guard_85raw_20260617\narrow_high_signal_clean_no_raw_productization --source-run-id seed-guard-realdata-85raw-consolidated-narrow-high-signal-clean-20260617 --high-signal-clean-activation-scope-audit-tsv output\productization_realdata_seed_guard_85raw_20260617\high_signal_clean_activation_scope_audit\activation_high_signal_clean_scope_audit.tsv`
    (`selected_activation_row_count=72`, `matrix_cells_written=72`,
    `activation_value_delta_written_count=72`, and
    `narrow_product_writer_expected_diff_acceptance.json` reports
    `acceptance_status=pass`, `readiness_tier=production_ready`, and
    `product_surface_changed=TRUE`).
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.standard_peak_heldout_trace_oracle --alignment-backfill-cell-evidence-tsv output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\alignment_backfill_cell_evidence.tsv --trace-root output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\standard_peak_backfill_preset\chunks --output-dir output\productization_realdata_seed_guard_85raw_20260617\heldout_trace_reintegration_oracle_low_scan_clean_probe --source-run-id seed-guard-realdata-85raw-heldout-low-scan-clean-probe-20260617 --target-shape-class standard_low_scan_clean_trace`
    (`selected_case_count=11`, `oracle_case_status_pass_count=11`,
    `included_in_product_acceptance_count=11`, max boundary error
    `4.86717e-05`, max area relative error `0.038786`).
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.standard_peak_backfill_productization --shadow-projection-cells-tsv output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\standard_peak_backfill_preset\consolidated\consolidated_shadow_projection_cells.tsv --alignment-matrix-tsv output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\alignment_matrix.pre_standard_peak_backfill.tsv --alignment-matrix-identity-tsv output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\alignment_matrix_identity.pre_standard_peak_backfill.tsv --alignment-review-tsv output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\alignment_review.tsv --output-dir output\productization_realdata_seed_guard_85raw_20260617\narrow_low_scan_clean_no_raw_productization --source-run-id seed-guard-realdata-85raw-consolidated-narrow-low-scan-clean-20260617 --low-scan-clean-activation-scope-audit-tsv output\productization_realdata_seed_guard_85raw_20260617\high_signal_clean_activation_scope_audit\activation_high_signal_clean_scope_audit.tsv`
    (`selected_activation_row_count=42`, `matrix_cells_written=42`,
    `activation_value_delta_written_count=42`, and
    `narrow_product_writer_expected_diff_acceptance.json` reports
    `acceptance_status=pass`, `readiness_tier=production_ready`,
    `expected_scope=low_scan_clean_eligible_activation_rows`, and
    `product_surface_changed=TRUE`).
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_heldout_trace_oracle.py tests\test_standard_peak_backfill_productization.py -q`
    now covers the low-height reintegration-stable family oracle and scoped
    writer tests (`14 passed` and `16 passed` when run as focused files before
    the later full gate).
  - Real no-RAW low-height reintegration-stable oracle:
    `heldout_trace_reintegration_oracle_low_height_reintegration_stable_family/`
    reports 220 audit-intersection rows / 66 families, family-level oracle
    matching, 1520 available detected trace candidates, selected 20/20 pass,
    max boundary error `0.0830019`, and max area relative error `0.0725986`.
  - Real no-RAW low-height reintegration-stable writer:
    `narrow_low_height_reintegration_stable_no_raw_productization/` reports
    220 selected/written cells and
    `narrow_product_writer_expected_diff_acceptance.json` reports
    `acceptance_status=pass`, `readiness_tier=production_ready`,
    `expected_scope=low_height_reintegration_stable_eligible_activation_rows`,
    `product_surface_changed=TRUE`, and stability-audit path/SHA provenance.
- Residual production-ready blocker: none for the five explicit scoped writer
  slices. Broad standard-path seed guard activation still needs a broader
  masked/product-writer observed oracle covering the current 4613-row activation
  scope before claiming broad `production_ready`; all-stability 299-row direct
  writer remains blocked by the family-check area failure.

Implement the seed guard as a pre-activation filter in the existing standard
peak activation/productization path, close to
`standard_peak_shadow_activation_inputs.py` and
`standard_peak_backfill_productization.py`. Do not add fields to
`ProductionRowDecision`, `alignment_review.tsv`, workbook sheets, or public
`area_policy` enums for this slice. The acceptance artifacts below are the
machine-readable proof surface.

Lifecycle mapping:

- Non-standard taxonomy maps to the C2 reconciliation/gallery line.
- Baseline-sensitive audit maps to the C4 area-integration uncertainty line.

## Terminology

### Standard-peak path

The current production-capable path for backfill. It is not a simple
standard/ISTD identity label. It is an evidence chain that can include
machine/manual same-peak support, product authority provenance, and activation
validation. This path is the only current target for the cohort-size banded
seed-support guard.

### Standard-assessable area

The selected cell has a defensible start boundary, end boundary, and baseline.
The current area value can be used as a quantitative matrix value after the
existing identity/product-authority gates pass.

### Non-standard-assessable area

The selected cell is not a clean standard shape, but integration is still
defensible. Identity may be supported, and area may be usable after explicit
uncertainty review. These cells must remain review-only until a separate
promotion contract defines acceptable uncertainty.

Examples:

- tailing peak with clean start and end boundaries;
- shoulder peak where the shoulder does not make the target envelope ambiguous;
- rough or mildly multi-apex envelope that still has one defensible integrated
  chromatographic envelope;
- mild adjacent contact that does not move the chosen integration boundaries.

### Baseline-sensitive area

The peak has defensible boundaries, but the baseline model materially controls
the final area. This is not solved by declaring AsLS better than linear-edge.
The old baseline comparison decision is closed, but baseline reliability remains
a live integration-risk question for non-standard or weak backfill cells.

Examples:

- sloping background under the peak;
- curved baseline caused by broad background;
- baseline pulled by nearby low-intensity signal;
- strong peak present, but baseline subtraction changes the area enough to
  affect quantitative interpretation.

### Unassessable area

The area has no defensible quantitative interpretation. Identity evidence is
not enough. These cells must not be promoted to matrix writes.

Examples:

- unresolved overlap where the target peak and another major peak share the
  same envelope;
- no defensible `boundary_start` or `boundary_end`;
- composite tailing plus multi-peak shape where the target area cannot be
  separated;
- a boundary decision would choose the biological answer rather than measure a
  separable signal.

## User Figure Interpretation

The owner supplied four hand-drawn conceptual shapes. They are product
semantics, not literal fixtures.

| Figure | Shape | Integration interpretation | Product policy |
| --- | --- | --- | --- |
| Fig. 1 | Tailing peak with clear boundaries | Boundary-resolvable; baseline likely manageable | `nonstandard_assessable_area` candidate |
| Fig. 2 | Rough / shoulder-like single envelope with clear boundaries | Boundary-resolvable if the whole envelope is the target | `nonstandard_assessable_area` candidate |
| Fig. 3 | Composite peak with a second major peak and no defensible end boundary | Boundary/identity not separable | `unassessable_area`; hard block |
| Fig. 4 | Clear peak inside boundaries, but unstable sloped baseline | Boundary may be resolvable, baseline is not automatically reliable | baseline-sensitive semantic class; review-only |

Important correction: **multiple local maxima do not automatically mean
unassessable**. A rough envelope can still be integrated if the start/end
boundaries and baseline are defensible and the envelope represents one target
signal. The hard blocker is not "more than one apex"; it is a non-identifiable
boundary, baseline, or target envelope.

## Cohort Seed-Support Guard

### Scope

The cohort-size banded seed guard applies first to the current standard-peak
backfill path. It is not a policy for future non-standard backfill, because that
path is not product-defined yet.

### Rationale

If a feature is detected in only a tiny fraction of the cohort, the detected
cells may be the anomaly rather than the missing cells. Even strong local MS1
evidence should not automatically turn a 3/85 row into an 82-cell rescue.

### Proposed rule

```text
if total_N < 20:
    seed_guard_status = "not_applicable_small_cohort"
    seed_floor = ""
    cohort_scale_automatic_backfill = False
    per_cell_review_allowed = True
elif total_N < 80:
    seed_floor = max(2, floor(total_N * 0.05))
    seed_guard_status = pass/fail against seed_floor
    cohort_scale_automatic_backfill = False
    per_cell_review_allowed = True
else:
    seed_floor = max(4, floor(total_N * 0.05))
    seed_guard_status = pass/fail against seed_floor
    cohort_scale_automatic_backfill = True
    per_cell_review_allowed = True
```

This is now the selected policy shape for the first standard-path implementation
slice. The large-cohort percentage rounding policy is deliberately `floor`,
matching the owner decision that `4/85` remains eligible and `3/85` blocks. The
medium-cohort floor is deliberately lower because requiring four detected seeds
in `N=20-79` would turn a prevalence guard into an overly strict high-prevalence
requirement.

`detected_count` means cells accepted as detected before this backfill decision.
It must not include rescued, promoted-fill, or newly backfilled values from the
same decision path.

For `N=85`:

| detected_count | max(4, floor(85 * 0.05)) | Result |
| ---: | ---: | --- |
| 3 | 4 | Block automatic backfill |
| 4 | 4 | Continue through existing evidence gates |

For `20 <= N < 80`, `seed_floor = max(2, floor(total_N * 0.05))`. Passing this
medium-cohort guard permits only per-cell review/product decisions through the
existing identity, product-authority, boundary, and baseline gates. It does not
authorize broad cohort-scale automatic backfill.

### Initial placement

The first implementation should treat this as a standard-path product
write/promotion blocker, not as a RAW request-planning cost guard. The existing
`owner_backfill_min_detected_samples` request planner gate is a fixed integer
cost-control guard and should not silently change semantics in this spec.

A separate performance plan may later choose to mirror the same threshold in
request planning, but that would be a distinct behavior change with its own
economics and validation.

### Denominator decision

`total_N` is the number of sample cells in the same activation/promotion cohort
that could receive a standard-path backfill value.

Use the sample columns from the source matrix artifact that the standard-peak
activation/consolidation path consumes:

- first choice: `alignment_matrix.pre_standard_peak_backfill.tsv`;
- fallback only when no backup exists: the source `alignment_matrix.tsv` passed
  into the activation/consolidation command before publication.

In both cases, sample columns are the public matrix columns after `Mz` and `RT`,
preserving the matrix writer's sample order. This deliberately avoids deriving
`total_N` from `alignment_review.tsv`, `alignment_cells.tsv`, already-activated
copies, or request-planning owner counts.

The standard-path activation input must also be compatible with the same run's
RAW availability. If a raw availability set is present in the run manifest or
activation summary, the implementation must fail closed when matrix sample
columns and eligible RAW sample stems disagree. Do not silently shrink `total_N`
by intersecting with a later or unrelated RAW manifest.

QC or pooled samples are counted only when they are ordinary eligible sample
columns in that same activation cohort. They are not added from a separate
manifest and not removed merely because they are QC-labeled.

### Numerator/source decision

`detected_count` is the pre-standard-backfill quantifiable detected seed count.
The preferred source is `ProductionRowDecision.quantifiable_detected_count` as
serialized in the pre-standard-backfill `alignment_review.tsv`.

If that row-level field is unavailable, the only allowed fallback is a
recomputation from the matching pre-standard-backfill production decisions:
count cells where `production_status == "detected"` and
`write_matrix_value == True`.

Do not use any of the following as the seed count:

- `feature.owners` from the request planner;
- `accepted_cell_count`, because it includes accepted rescues;
- `quantifiable_rescue_count`;
- current values already written by the same standard-peak backfill path;
- review-only, rejected, duplicate-loser, ambiguous-owner, absent, or unchecked
  cells.

### Cohort-size behavior

For cohorts smaller than 20, the prevalence guard is not applicable and must not
be reported as a pass. Existing identity/product/area gates still apply. A
strong per-cell case may continue as review-positive or product-candidate
through the existing per-cell gates, but small cohorts must not use one or two
seeds as authority for broad cohort-scale automatic backfill.

8RAW remains a diagnostic smoke for schema, provenance, and examples. It cannot
approve or reject the banded seed guard. The first meaningful large-cohort
oracle is a cohort with `total_N >= 80`, with 85RAW as the intended stress
oracle for large-cohort behavior.

`not_applicable_small_cohort` is an internal decision reason for the
seed-support guard's own diagnostic/acceptance artifact. It is not a new
`alignment_review.tsv`, `alignment_matrix.tsv`, `area_policy`, or workbook enum.
Rows in this state must continue through existing gates without claiming the
seed-support guard was validated.

### Implementation contract decisions

The first implementation must use these decisions:

| Decision | Product answer |
| --- | --- |
| Small cohort | `total_N < 20`: `not_applicable_small_cohort`; no prevalence pass/fail; no broad cohort-scale automatic backfill |
| Medium cohort | `20 <= total_N < 80`: `seed_floor=max(2, floor(total_N * 0.05))`; pass permits per-cell review/product gates only; no broad cohort-scale automatic backfill |
| Large cohort | `total_N >= 80`: `seed_floor=max(4, floor(total_N * 0.05))`; pass may continue toward standard-path cohort-scale automatic backfill through existing gates |
| `total_N` source | Sample columns from `alignment_matrix.pre_standard_peak_backfill.tsv`; fallback only to the source activation input `alignment_matrix.tsv` before publication |
| `detected_count` source | `quantifiable_detected_count`; fallback only to pre-backfill `production_status=detected && write_matrix_value=True` |
| Included statuses | Quantifiable detected seeds only |
| Excluded statuses | Rescued, review-only, rejected, duplicate-loser, ambiguous-owner, absent, unchecked, same-path backfilled |
| Small-N behavior | Internal seed-guard decision reason `not_applicable_small_cohort` when `total_N < 20`; do not treat 8RAW as a prevalence oracle |
| Block expectation | No new standard-path automatic backfill writes for that row; existing pre-backfill values remain untouched |
| Pass expectation | Continue through existing identity/product/area gates; pass alone does not write matrix values |
| Candidate coverage | Every source standard-path promotion candidate must appear in `seed_guard_decisions.tsv`; omitted candidates fail the lane |
| Write attribution | Every actual write must join to `activation_value_delta.tsv` by stable cell key and must declare cohort-scale or per-cell product authority |
| Matrix acceptance | `unexpected_matrix_diff_count=0`, `missing_matrix_diff_count=0`, `value_delta_mismatch_count=0` against expected activation rows |
| Held-out oracle | Mask originally detected quantifiable cells, use the remaining unmasked detected seeds as `detected_count`, and require boundary + area recovery within oracle tolerance |

### Implementation source map

| Concept | Source of truth | Public surface impact |
| --- | --- | --- |
| `total_N` | Header sample columns from `alignment_matrix.pre_standard_peak_backfill.tsv`; fallback only to the source activation input `alignment_matrix.tsv` before publication | Internal seed-guard calculation; no `alignment_matrix.tsv` schema change |
| `detected_count` | `alignment_review.tsv` row field `quantifiable_detected_count` from the same pre-standard-backfill source run | Reuses existing `alignment_review.tsv` field |
| `detected_count` fallback | Recomputed production decisions from the same pre-standard-backfill source: `production_status=detected && write_matrix_value=True` | Implementation fallback only; must emit provenance in diagnostic/acceptance artifact |
| Small cohort | Internal seed-guard decision reason `not_applicable_small_cohort` when `total_N < 20` | New diagnostic/acceptance reason only; not an `area_policy`, matrix, workbook, or review-row enum |
| Medium cohort | `seed_floor=max(2, floor(total_N * 0.05))`, `cohort_scale_automatic_backfill=FALSE` | Per-cell gate status only; no broad matrix-fill authority |
| Large cohort | `seed_floor=max(4, floor(total_N * 0.05))`, `cohort_scale_automatic_backfill=TRUE` after existing gates | Standard-path cohort-scale candidate only after expected-diff acceptance |
| Seed-guard placement | Pre-activation standard-peak activation/productization filter near `standard_peak_shadow_activation_inputs.py` / `standard_peak_backfill_productization.py` | No `ProductionRowDecision`, `alignment_review.tsv`, workbook, or public `area_policy` schema change |
| Actual write delta | `activation_value_delta.tsv` rows keyed by `peak_hypothesis_id + sample_stem` | Acceptance artifact only; used to prove no unattributed writes |
| Baseline-sensitive area | Diagnostic-only integration pathology row with `matrix_write_allowed=FALSE` | No promotion allowlist entry until a later schema/test change explicitly adds a baseline-sensitive contract |
| Matrix effect | Existing activation matrix-diff / value-delta acceptance artifacts | Reuses existing acceptance counters |

## Area Policy States

Future policy should avoid overloading the existing names. The following states
are proposed as the semantic target:

| State | Boundary | Baseline | Matrix promotion |
| --- | --- | --- | --- |
| `standard_assessable_area` | stable | stable | allowed after identity/product gates |
| `nonstandard_assessable_area` | defensible | stable or bounded | blocked until uncertainty contract exists |
| baseline-sensitive semantic class | defensible | unstable or model-sensitive | review-only under current public schema |
| `unassessable_area` | not defensible, or target envelope not separable | irrelevant or not defensible | hard block |

Current public promotion schemas do not support `baseline_sensitive_area` as an
`area_policy` enum. Current promotion code also treats
`area_policy=nonstandard_assessable_area` as a reviewed uncertainty path that
still has specific `matrix_quantitative_use` expectations. Therefore
baseline-sensitive cells must not be smuggled into the current promotion
allowlist as `nonstandard_assessable_area + review_only`.

Until a schema/test change explicitly adds a baseline-sensitive public contract,
baseline-sensitive rows belong in a diagnostic artifact only, with fields such
as:

- `integration_pathology=baseline_sensitive`;
- `baseline_assessability=sensitive`;
- `matrix_write_allowed=FALSE`;
- `integration_review_status=review_only`;
- a reason such as `baseline_slope_sensitive` or
  `baseline_background_pull`.

The existing `area_integration_uncertainty_*` line should be reframed as:

```text
area integration uncertainty = boundary uncertainty + baseline uncertainty
```

This makes C4 a cold audit oracle for Fig. 1, Fig. 2, and Fig. 4. It does not
rescue Fig. 3, because Fig. 3 is not an uncertainty problem; it is an
unidentifiable integration target.

## Boundary And Baseline Assessability

This section is the minimum checklist before any non-standard classification can
be considered credible. It is intentionally stricter than a visual "there is a
peak" judgment.

### Boundary defensibility checklist

A cell can be classified as boundary-defensible only when all required items are
true:

| Check | Required answer | Fail-closed state |
| --- | --- | --- |
| Start boundary | Start RT comes from a segment-native boundary, a reviewed manual boundary, or an oracle row tied to the same trace | `no_defensible_start_boundary` |
| End boundary | End RT comes from a segment-native boundary, a reviewed manual boundary, or an oracle row tied to the same trace | `no_defensible_end_boundary` |
| Target envelope | The selected boundary encloses one interpretable target envelope rather than two unresolved major envelopes | `target_envelope_not_separable` |
| Competing apex | No strong competing apex inside or adjacent to the integration envelope that would materially change the target area | `strong_competing_peak_integration_blocker` |
| Boundary provenance | Boundary source row, trace artifact, and source hash are present and fresh | `stale_or_missing_boundary_provenance` |
| Biological answer leakage | Boundary choice is not selected because it gives the expected biological result | `answer_shaped_boundary` |

`selected_full_envelope` is allowed only as review context unless it is backed by
a reviewed oracle row or a later product contract. A wide fallback envelope must
not become a quantitative boundary merely because the same-peak identity score is
strong.

### Baseline defensibility checklist

Baseline stability is assessed against a named baseline model set, not against an
undefined phrase like "defensible baselines".

First-slice baseline model set:

- current reported integration baseline from the source artifact;
- any named diagnostic-only alternate baseline model implemented outside public
  `baseline_integration_method` and never serialized as product/public baseline
  schema;
- reviewed manual baseline if a manual oracle row exists.

If no diagnostic-only alternate model or reviewed manual baseline exists, and
only the current product baseline value is available, baseline stability is
`inconclusive`, not `stable`. If the model set cannot be recomputed against the
same boundary and trace, the cell remains review-only. Do not re-enable retired
public baseline modes to satisfy this audit.

| Check | Required answer | Fail-closed or review-only state |
| --- | --- | --- |
| Shared boundary | All baseline comparisons use the same start/end RT | `baseline_boundary_mismatch` |
| Baseline model provenance | Each baseline model and parameter set is recorded | `missing_baseline_model_provenance` |
| Relative spread | `(max(area) - min(area)) / max(abs(current_area), epsilon) <= 0.20`, with `epsilon` recorded in the oracle manifest | `baseline_sensitive_review_only` |
| Residual/context warning | No baseline residual or background-pull warning above the reviewed threshold recorded in the oracle manifest | `baseline_sensitive_review_only` |
| Manual override | Any manual baseline override has reviewer id/source row/hash | `manual_baseline_not_product_authorized` |

The `0.20` threshold is a first-slice diagnostic threshold, not a product write
threshold for non-standard cells.

## Promotion Rules

### Standard-assessable cells

May continue to matrix-write promotion only when all existing product authority
checks pass, plus any approved cohort seed-support guard.

The seed-support guard only answers cohort-size seed sufficiency and broad
cohort-scale eligibility. It does not approve identity or area quantifiability
by itself. Automatic promotion still requires the existing
same-peak/product-authority chain plus a standard-assessable, or
current-equivalent area-assessable, integration contract.

### Non-standard-assessable cells

Must remain blocked from automatic matrix writes until all of the following are
defined:

- boundary provenance;
- baseline provenance;
- area uncertainty metric;
- acceptable uncertainty threshold;
- manual/EIC or held-out validation oracle;
- matrix-diff acceptance expectation.

### Baseline-sensitive cells

Must not be treated as standard-assessable just because a peak is visible. A
future gate must record baseline model sensitivity, for example:

- area under current baseline;
- area under alternate defensible baseline;
- relative area spread;
- baseline fit residual metric;
- reason code such as `baseline_slope_sensitive` or
  `baseline_background_pull`.

### Unassessable cells

Hard block. The sidecar may keep visual/evidence rows for review, but activation
must not consume them.

## Required Evidence Fields

A future implementation should prefer explicit fields rather than free-text
review notes. Diagnostic-only taxonomy rows can start with the integration fields
below. Any product-consuming row must additionally satisfy the existing
product-authority provenance contract from `docs/lcms-msms-evidence-rules.md`.

- `area_policy`;
- `matrix_quantitative_use`;
- `peak_hypothesis_sample_key`;
- `identity_support_status`;
- `identity_support_source`;
- `identity_support_reason`;
- `product_authority_source`;
- `integration_pathology`;
- `boundary_assessability`;
- `baseline_assessability`;
- `boundary_start_source`;
- `boundary_end_source`;
- `baseline_model_source`;
- `area_uncertainty_fraction`;
- `area_uncertainty_fraction_status`;
- `area_uncertainty_components`;
- `integration_blockers`;
- `integration_review_status`;
- `trace_provenance_hash`.

Additional fields required before any row is consumed by product activation:

- `diagnostic_only`;
- `product_authority_status`;
- `product_authority_scope`;
- `product_authority_source`;
- `source_artifact_schema_version`;
- `source_artifact_sha256`;
- `source_row_sha256`;
- `boundary_artifact_path`;
- `boundary_artifact_sha256`;
- `trace_artifact_path`;
- `trace_artifact_sha256`;
- `review_allowlist_path`;
- `review_allowlist_sha256`.

Do not replace this provenance set with a single `trace_provenance_hash`.
Single-hash provenance is acceptable for a gallery row, not for a matrix-writing
decision.

Suggested enum values:

```text
integration_pathology:
  clean_standard
  tailing_boundary_resolvable
  shoulder_boundary_resolvable
  rough_single_envelope
  baseline_sensitive
  unresolved_overlap
  composite_tail_multipeak
  no_defensible_boundary

boundary_assessability:
  stable
  review_required
  unassessable

baseline_assessability:
  stable
  sensitive
  unassessable
```

## Validation Plan

Validation is split by lane. Passing one lane must not promote another lane.

### Standard seed guard phase

Goal: prove the seed guard can block only the intended standard-path rows.

Required tests/artifacts:

- boundary-transition unit tests for `N=19`, `N=20`, `N=79`, `N=80`,
  `N=85`, and `N>85`;
- fixture proving small cohorts emit `not_applicable_small_cohort` and
  `cohort_scale_automatic_backfill=FALSE`;
- fixture proving medium cohorts can emit `eligible_per_cell_only` but still
  keep `cohort_scale_automatic_backfill=FALSE` and
  `actual_cohort_scale_written_cell_count=0`;
- fixture where `N=85`, `detected_count=3` blocks and `detected_count=4`
  continues;
- fixture proving `candidate_source_row_count == evaluated_row_count` and
  `omitted_candidate_count=0`;
- fixture proving every actual write joins to `activation_value_delta.tsv` by
  `peak_hypothesis_id + sample_stem`;
- fixture proving rescued/backfilled/review-only cells are excluded from
  `detected_count`;
- fixture proving denominator comes from the same pre-standard-backfill matrix
  artifact and fails closed on RAW/sample mismatch;
- expected-diff artifact with `unexpected_matrix_diff_count=0`,
  `missing_matrix_diff_count=0`, and `value_delta_mismatch_count=0`.

This lane may become product behavior only for standard-path rows. It must not
create or consume non-standard taxonomy rows.

### Acceptance artifact contract

The first standard seed-guard implementation must emit machine-readable
acceptance artifacts. Matrix diff counters alone are not enough, because a
blocked-row policy also needs proof that candidate rows were evaluated and
intentionally did not write.

#### `seed_guard_decisions.tsv`

One row per standard-path promotion candidate from the source candidate set, not
just one row per row that happened to reach the seed guard. The artifact must
prove that the candidate set was fully evaluated.

Stable cell keys use:

```text
peak_hypothesis_id + sample_stem
```

If a future source needs family disambiguation, add `feature_family_id` as a
separate field, but do not replace the `peak_hypothesis_id + sample_stem` join
key.

All `*_cell_keys` fields are sorted, semicolon-delimited stable cell keys.
An empty set is represented by an empty string plus the companion count field
set to `0`. All `*_cell_count` fields count unique stable cell keys in the
matching key field.

Required fields:

- `schema_version`;
- `source_run_id`;
- `candidate_set_sha256`;
- `candidate_source_row_count`;
- `evaluated_row_count`;
- `omitted_candidate_count`;
- `feature_family_id`;
- `peak_hypothesis_id`;
- `sample_scope`;
- `pre_backfill_matrix_path`;
- `pre_backfill_matrix_sha256`;
- `pre_backfill_review_path`;
- `pre_backfill_review_sha256`;
- `total_N`;
- `detected_count`;
- `seed_floor`;
- `seed_guard_status`;
- `cohort_size_band`;
- `cohort_scale_automatic_backfill`;
- `per_cell_review_allowed`;
- `write_authority_status`;
- `product_authority_scope`;
- `allowed_contract_rule_ids`;
- `per_cell_authority_reason`;
- `expected_write_effect`;
- `expected_no_write_cell_count`;
- `expected_no_write_cell_keys`;
- `actual_written_cell_count`;
- `actual_written_cell_keys`;
- `actual_cohort_scale_written_cell_count`;
- `actual_cohort_scale_written_cell_keys`;
- `actual_per_cell_written_cell_count`;
- `actual_per_cell_written_cell_keys`;
- `activation_value_delta_path`;
- `activation_value_delta_sha256`;
- `decision_reason`;
- `blocking_reason`;
- `raw_sample_match_status`.

Allowed `seed_guard_status` values for the first slice:

- `eligible_continue_existing_gates`;
- `eligible_per_cell_only`;
- `blocked_low_seed_support`;
- `not_applicable_small_cohort`;
- `inconclusive_source_mismatch`.

Allowed `cohort_size_band` values:

- `small_lt20`;
- `medium_20_to_79`;
- `large_ge80`.

Allowed `write_authority_status` values:

- `no_write`;
- `per_cell_product_authorized`;
- `cohort_scale_standard_backfill`;
- `blocked_unattributed_write`.

Acceptance expectations:

- `candidate_source_row_count` must equal `evaluated_row_count`, and
  `omitted_candidate_count` must be `0`.
- `candidate_set_sha256` must match the source standard-path promotion candidate
  artifact used by the implementation.
- `blocked_low_seed_support` rows must have `actual_written_cell_count=0`.
- `not_applicable_small_cohort` rows must have
  `cohort_scale_automatic_backfill=FALSE`.
- `eligible_per_cell_only` rows must have
  `cohort_scale_automatic_backfill=FALSE`; any write must be explainable by an
  explicit per-cell product-authority path, not by cohort-scale backfill.
- When `cohort_scale_automatic_backfill=FALSE`,
  `actual_cohort_scale_written_cell_count` must be `0`.
- `eligible_per_cell_only` must not run a row-level fill over all missing cells.
  Any nonzero write must appear only in
  `actual_per_cell_written_cell_keys`, must join to
  `activation_value_delta.tsv`, and must have
  `product_authority_scope=feature_family_sample` with an allowlisted
  `contract_rule_id` in `allowed_contract_rule_ids`.
- `actual_written_cell_keys` must equal the union of
  `actual_cohort_scale_written_cell_keys` and
  `actual_per_cell_written_cell_keys`.
- `blocked_unattributed_write` is fail-closed and blocks product promotion for
  the lane.
- `eligible_continue_existing_gates` does not by itself approve writes; it only
  permits the row to continue through existing identity/product/area gates.
- `inconclusive_source_mismatch` is fail-closed and must not write.

#### `heldout_oracle_manifest.tsv`

One row per deterministic held-out oracle case. Random ad hoc masks are not
acceptable.

Required fields:

- `schema_version`;
- `oracle_case_id`;
- `source_run_id`;
- `mask_strategy`;
- `masked_sample`;
- `heldout_original_cell_status`;
- `feature_family_id`;
- `peak_hypothesis_id`;
- `target_shape_class`;
- `oracle_source`;
- `oracle_start_rt`;
- `oracle_end_rt`;
- `oracle_area`;
- `baseline_model_set`;
- `baseline_epsilon`;
- `baseline_residual_threshold`;
- `acceptable_boundary_delta_min`;
- `acceptable_area_relative_error`;
- `expected_seed_guard_status`;
- `expected_integration_pathology`;
- `expected_matrix_write_allowed`.

Boundary error is:

```text
abs(observed_start_rt - oracle_start_rt)
+ abs(observed_end_rt - oracle_end_rt)
```

Area relative error is computed against `abs(oracle_area)`. If `oracle_area` is
missing, zero, negative, or otherwise not a valid quantitative denominator, the
case is `inconclusive_review_only`, not a pass. Failure aggregation is per-row:
any row exceeding boundary or area tolerance fails the lane unless the oracle
manifest explicitly labels that row as diagnostic-only and excluded from the
product seed-guard acceptance.

`heldout_original_cell_status` must prove the masked cell was originally a
detected quantifiable cell, not a backfilled/rescued cell. Allowed values are
`detected`, `detected_seed`, `quantifiable_detected`, and `accepted_detected`.
Rows with `rescued`, blank, or unknown status fail before result evaluation.

#### `heldout_observed_results.tsv`

One row per executed held-out oracle case. This is an input to the evaluator,
not the oracle itself. It records what an implementation actually selected and
integrated after the held-out mask, plus why that observation is independent
from the oracle row.

Required fields:

- `oracle_case_id`;
- `observed_start_rt`;
- `observed_end_rt`;
- `observed_area`;
- `observed_result_source`;
- `observed_boundary_source`;
- `observed_area_source`;
- `observed_independence_basis`.

Allowed `observed_independence_basis` values:

- `product_writer_observed_result`;
- `masked_rerun_observed_result`;
- `independent_boundary_reintegration_result`.

The observed source fields must point to the implementation/result producer,
not to the oracle source. Rows copied from `oracle_source`, manual oracle,
manual review, manual verdict, or review-queue source rows fail closed. The
observed row is also compared against the matching manifest row: if
`observed_result_source`, `observed_boundary_source`, or `observed_area_source`
canonicalizes to the same label as manifest `oracle_source`, the row fails even
when the label is otherwise neutral. This is stricter than numeric tolerance on
purpose: it prevents a held-out gate from passing by copying the same reviewed
row into both oracle and observed inputs. The copy detector canonicalizes
whitespace and punctuation before checking source labels, so variants such as
`manual review`, `manual-review`, `review queue`, and `oracle-source` are
treated the same as their underscore forms.

#### `heldout_oracle_results.tsv`

One row per `heldout_oracle_manifest.tsv` row executed. The manifest defines the
expected case; this results artifact records what the implementation actually
selected and integrated.

Required fields:

- `schema_version`;
- `oracle_case_id`;
- `source_run_id`;
- `feature_family_id`;
- `peak_hypothesis_id`;
- `masked_sample`;
- `observed_start_rt`;
- `observed_end_rt`;
- `observed_area`;
- `observed_result_source`;
- `observed_boundary_source`;
- `observed_area_source`;
- `observed_independence_basis`;
- `boundary_error_min`;
- `area_relative_error`;
- `oracle_case_status`;
- `inconclusive_reason`;
- `included_in_product_acceptance`;
- `result_source_artifact_path`;
- `result_source_artifact_sha256`.

Allowed `oracle_case_status` values:

- `pass`;
- `fail_boundary`;
- `fail_area`;
- `inconclusive_review_only`.

Acceptance expectations:

- Every manifest row must have exactly one result row.
- Every observed row used for product acceptance must satisfy the observed
  provenance contract above.
- `result_source_artifact_path` must point to an existing file and
  `result_source_artifact_sha256` must be non-empty.
- `boundary_error_min` must use the manifest formula above.
- `area_relative_error` must use the manifest area denominator rule above.
- Any row included in product acceptance must have `oracle_case_status=pass`.
- Any row with `oracle_case_status` other than `pass` must have
  `included_in_product_acceptance=FALSE`; otherwise the lane fails.

#### `activation_high_signal_clean_scope_audit.tsv`

One row per `activation_value_delta.tsv` row from the current standard-peak
productization bridge. This is a readback gate that asks whether actual written
activation cells are covered by named evidence envelopes used by heldout trace
oracles. It does not authorize writes by itself.

Required fields:

- `schema_version`;
- `source_run_id`;
- `feature_family_id`;
- `peak_hypothesis_id`;
- `sample_id`;
- `matrix_value_effect`;
- `source_cell_status`;
- `activated_matrix_value`;
- `matrix_value_source_row_sha256`;
- `projection_match_status`;
- `projection_cell_status`;
- `projection_gap_fill_state`;
- `projection_local_global_ratio`;
- `projection_overlay_png_path`;
- `trace_data_path`;
- `trace_match_status`;
- `trace_status`;
- `cell_area`;
- `cell_height`;
- `cell_start_rt`;
- `cell_end_rt`;
- `cell_apex_rt`;
- `family_center_rt`;
- `boundary_width_min`;
- `apex_delta_abs_min`;
- `integration_scan_count`;
- `apex_aligned_shape_similarity`;
- `local_window_to_global_max_ratio`;
- `high_signal_clean_status`;
- `high_signal_clean_blockers`;
- `low_scan_clean_status`;
- `low_scan_clean_blockers`;
- `low_height_clean_status`;
- `low_height_clean_blockers`;
- `low_height_low_scan_clean_status`;
- `low_height_low_scan_clean_blockers`.

The high-signal clean envelope for this audit is intentionally identical to the
heldout trace oracle case selector: `trace_status` in `detected` or `rescued`,
shape similarity `>=0.95`, local/global max ratio `>=0.95`, cell height
`>=2e6`, boundary width `0.30-0.65 min`, apex within `0.15 min` of the family
center, and at least `10` scans inside the integration boundary.

`high_signal_clean_status=eligible` means the row is a candidate for a future
explicit high-signal-clean product scope. `missing_evidence` means the write
cannot be assessed from the current projection/trace artifacts. `ineligible`
means available trace evidence exists but falls outside this oracle envelope.

The low-scan clean envelope uses the same supported trace status, shape,
local/global, height, width, and apex-delta thresholds, but requires `7-9`
scans inside the integration boundary. `low_scan_clean_status=eligible` means
the row is a candidate for the explicit low-scan-clean product scope. It is not
a general low-quality allowance: scan count below `7` or any additional blocker
keeps the row ineligible.

The low-height clean envelope uses the same supported trace status, shape,
local/global, width, apex-delta, and `>=10` scan thresholds as high-signal
clean, but requires `cell_height < 2e6`. `low_height_clean_status=eligible`
means the row is a diagnostic candidate for the explicit low-height product
scope. It became writer-approved only after the later bounded-window heldout
oracle and scoped writer expected-diff passed; the first full-trace oracle
failure remains the reason this class must stay tied to the bounded-window
oracle rule.

The low-height-low-scan clean envelope requires `cell_height < 2e6`, `7-9`
scans, and the same supported trace, shape, local/global, width, and apex-delta
constraints. `low_height_low_scan_clean_status=eligible` means the row is a
candidate for the explicit low-height-low-scan product scope.

#### `activation_high_signal_clean_scope_summary.tsv/json`

The summary records source artifact paths/hashes, written row counts, projection
join counts, trace join counts, high-signal, low-scan, low-height, and
low-height-low-scan
eligible/ineligible/missing-evidence counts, and status fields:

- `broad_activation_scope_status`: may be `ready` only when every written
  activation row is high-signal clean eligible. Otherwise it must remain
  `not_ready`.
- `narrow_activation_scope_status`: may report
  `ready_if_product_scope_is_limited_to_eligible_rows` only as a decision
  candidate. It is not production behavior unless a product writer actually
  limits output to those rows and an expected-diff gate accepts that matrix
  change.
- `low_scan_clean_activation_scope_status`: may report
  `ready_if_product_scope_is_limited_to_low_scan_clean_rows` only as a decision
  candidate. It is not production behavior unless a product writer actually
  limits output to those rows and an expected-diff gate accepts that matrix
  change.
- `low_height_clean_activation_scope_status`: may report
  `ready_if_product_scope_is_limited_to_low_height_clean_rows` only as a
  decision candidate. It is not production behavior unless a product writer
  actually limits output to those rows and an expected-diff gate accepts that
  matrix change.
- `low_height_low_scan_clean_activation_scope_status`: may report
  `ready_if_product_scope_is_limited_to_low_height_low_scan_clean_rows` only as
  a decision candidate. It is not production behavior unless a product writer
  actually limits output to those rows and an expected-diff gate accepts that
  matrix change.

`eligible_activation_value_delta.tsv` is a filtered convenience artifact for the
eligible subset. It is not a replacement for `activation_value_delta.tsv` and
must not be treated as product output unless the activation contract is
explicitly narrowed to that scope.

`low_scan_clean_activation_value_delta.tsv` is the equivalent filtered
convenience artifact for `low_scan_clean_status=eligible` rows and has the same
non-product limitation.

`low_height_clean_activation_value_delta.tsv` and
`low_height_low_scan_clean_activation_value_delta.tsv` are the equivalent
filtered convenience artifacts for `low_height_clean_status=eligible` and
`low_height_low_scan_clean_status=eligible` rows. They have the same
non-product limitation until consumed by an explicit scoped writer with passing
writer expected-diff.

#### `narrow_activation_expected_diff_acceptance.tsv/json`

One-row acceptance artifact for the explicit high-signal-clean activation subset.
It is a delta-level expected-diff gate, not a matrix writer. The gate compares
`eligible_activation_value_delta.tsv` against the full `activation_value_delta.tsv`
and `activation_high_signal_clean_scope_audit.tsv`.

Required fields:

- `schema_version`;
- `source_run_id`;
- `acceptance_status`;
- `expected_scope`;
- `activation_value_delta_tsv`;
- `activation_value_delta_sha256`;
- `activation_scope_audit_tsv`;
- `activation_scope_audit_sha256`;
- `eligible_activation_value_delta_tsv`;
- `eligible_activation_value_delta_sha256`;
- `full_written_delta_row_count`;
- `eligible_audit_row_count`;
- `eligible_delta_row_count`;
- `duplicate_delta_key_count`;
- `missing_delta_row_count`;
- `unexpected_delta_row_count`;
- `non_eligible_delta_row_count`;
- `not_written_delta_row_count`;
- `unchanged_delta_row_count`;
- `blank_activated_value_count`;
- `blocking_reasons`;
- `product_surface_changed`;
- `next_action`.

Acceptance expectations:

- `expected_scope` must be `high_signal_clean_eligible_activation_rows`.
- `acceptance_status=pass` requires no duplicate, missing, unexpected,
  non-eligible, non-written, unchanged, or blank activated-value rows.
- `product_surface_changed` must remain `FALSE` because the gate does not write a
  formal matrix output.
- Passing this gate is sufficient to say the 72-row subset has delta-level
  expected-diff acceptance. It is not sufficient to say production behavior is
  active. A formal product writer must explicitly limit output to this scope
  before a `production_ready` claim can be made.

#### `low_scan_clean_activation_expected_diff_acceptance.tsv/json`

One-row acceptance artifact for the explicit low-scan-clean activation subset.
It uses the same fields and acceptance expectations as
`narrow_activation_expected_diff_acceptance.tsv/json`, except `schema_version`
is `standard_peak_low_scan_activation_expected_diff_acceptance_v1` and
`expected_scope` must be `low_scan_clean_eligible_activation_rows`. Passing this
gate is sufficient to say the 42-row subset has delta-level expected-diff
acceptance; production behavior still requires the explicit scoped writer.

#### `low_height_clean_activation_expected_diff_acceptance.tsv/json`

One-row acceptance artifact for the low-height-clean activation subset. It uses
the same fields and acceptance expectations as
`narrow_activation_expected_diff_acceptance.tsv/json`, except `schema_version`
is `standard_peak_low_height_activation_expected_diff_acceptance_v1` and
`expected_scope` must be `low_height_clean_eligible_activation_rows`. Passing
this gate is sufficient to say the 57-row subset has delta-level expected-diff
cleanliness. Production behavior still requires the explicit scoped writer and
the bounded-window oracle rule.

#### `low_height_low_scan_clean_activation_expected_diff_acceptance.tsv/json`

One-row acceptance artifact for the low-height-low-scan activation subset. It
uses the same fields and acceptance expectations as
`narrow_activation_expected_diff_acceptance.tsv/json`, except `schema_version`
is `standard_peak_low_height_low_scan_activation_expected_diff_acceptance_v1`
and `expected_scope` must be
`low_height_low_scan_clean_eligible_activation_rows`. Passing this gate is
sufficient to say the 69-row subset has delta-level expected-diff cleanliness;
production behavior still requires the explicit scoped writer.

#### Scoped `standard_peak_backfill_productization.py` writer flags

Explicit opt-in writer contract for named Backfill release slices.

- `--high-signal-clean-activation-scope-audit-tsv` filters to
  `high_signal_clean_status=eligible` and writes
  `expected_scope=high_signal_clean_eligible_activation_rows`.
- `--low-scan-clean-activation-scope-audit-tsv` filters to
  `low_scan_clean_status=eligible` and writes
  `expected_scope=low_scan_clean_eligible_activation_rows`.
- `--low-height-clean-activation-scope-audit-tsv` filters to
  `low_height_clean_status=eligible` and writes
  `expected_scope=low_height_clean_eligible_activation_rows`.
- `--low-height-low-scan-clean-activation-scope-audit-tsv` filters to
  `low_height_low_scan_clean_status=eligible` and writes
  `expected_scope=low_height_low_scan_clean_eligible_activation_rows`.
- `--low-height-reintegration-stable-activation-scope-audit-tsv` plus
  `--reintegration-stability-audit-tsv` derives a transient
  `low_height_reintegration_stable_status=eligible` only for rows that are
  stability eligible, still written in the activation scope audit, and have
  `cell_height < 2e6`; it writes
  `expected_scope=low_height_reintegration_stable_eligible_activation_rows`.
- `--backfill-policy-source-audit-tsv` is the broad, non-manual policy path.
  It consumes a source activation-scope audit covering the candidate universe,
  optionally joins `--reintegration-stability-audit-tsv`, emits generated
  `standard_peak_backfill_policy.tsv` /
  `standard_peak_backfill_policy_summary.json`, and then filters the writer to
  generated `backfill_policy_decision=write_ready` rows with
  `expected_scope=backfill_policy_write_ready_rows`. Rows classified as
  `detected_flagged` or `blocked` stay audit-only and do not write matrix cells.

Only one scoped audit flag may be supplied at a time. When a scoped flag is
supplied, the productization bridge reads
`activation_high_signal_clean_scope_audit.tsv`, filters the input
`shadow_production_projection_cells.tsv` to rows whose
`shadow_projection_row_sha256` appears as
`matrix_value_source_row_sha256` with
the selected scope status equal to `eligible` and `matrix_value_effect=written`,
and then runs the existing standard-peak activation input builder plus existing
matrix-only product activation writer on that filtered set.

Fail-closed requirements:

- The scope audit must contain at least one eligible written row.
- Eligible scope-audit source-row hashes must be unique.
- Every eligible scope-audit hash must map to exactly one shadow projection row
  inside the productization input.
- The writer may not broaden to trace-matched ineligible rows, missing-evidence
  rows, non-standard rows, or rows outside the supplied scope audit.
- The flag does not change default extraction, preset behavior, GUI behavior,
  workbook schema, non-standard promotion policy, or the broad 4613-row
  activation bridge.
- The generated backfill policy TSV is an audit/replay artifact, not a manual
  allowlist. Broadening Backfill should add a named evidence class to the
  policy engine and its source artifacts, with oracle/expected-diff evidence,
  rather than adding another nested dataset-specific writer flag.
- `write_ready` policy rows must be `matrix_value_effect=written`, must carry a
  nonblank evidence class, and must have
  `backfill_policy_authority_status=writer_approved`; malformed generated or
  replayed policy rows fail closed before matrix activation.

The productization summary records:

- `schema_version=standard_peak_backfill_productization_v1`;
- `activation_scope_contract`;
- `activation_scope_filter_status`;
- `activation_scope_audit_tsv`;
- `activation_scope_audit_sha256`;
- `reintegration_stability_audit_tsv`;
- `reintegration_stability_audit_sha256`;
- `activation_scope_filter_selected_shadow_row_count`;
- `activation_scope_filter_excluded_shadow_row_count`;
- `activation_scope_filter_eligible_audit_row_count`;
- `narrow_product_writer_expected_diff_acceptance_status`;
- `narrow_product_writer_expected_diff_acceptance_tsv`;
- `narrow_product_writer_expected_diff_acceptance_json`.

The policy generator also records `source_activation_scope_audit_tsv` and
artifact SHA in `standard_peak_backfill_policy_summary.json`, plus counts for
`write_ready`, `detected_flagged`, and `blocked`. This closes the "TSV as human
white-list" failure mode: every candidate row should receive a machine
classification, even when only a subset is currently writer-approved.

#### `narrow_product_writer_expected_diff_acceptance.tsv/json`

One-row acceptance artifact emitted by each explicit scoped writer.
Unlike `narrow_activation_expected_diff_acceptance.tsv/json`, this gate is tied
to an actual matrix-only productization output and therefore records
`product_surface_changed=TRUE`.

Required fields:

- `schema_version`;
- `source_run_id`;
- `acceptance_status`;
- `readiness_tier`;
- `expected_scope`;
- `activation_scope_audit_tsv`;
- `activation_scope_audit_sha256`;
- `reintegration_stability_audit_tsv`;
- `reintegration_stability_audit_sha256`;
- `product_activation_value_delta_tsv`;
- `product_activation_value_delta_sha256`;
- `activation_application_status`;
- `matrix_cells_written`;
- `eligible_audit_row_count`;
- `product_delta_row_count`;
- `product_written_delta_row_count`;
- `duplicate_delta_key_count`;
- `missing_delta_row_count`;
- `unexpected_delta_row_count`;
- `non_eligible_delta_row_count`;
- `not_written_delta_row_count`;
- `unchanged_delta_row_count`;
- `blank_activated_value_count`;
- `blocking_reasons`;
- `product_surface_changed`;
- `next_action`.

Acceptance expectations:

- `expected_scope` must be one of
  `high_signal_clean_eligible_activation_rows`,
  `low_scan_clean_eligible_activation_rows`,
  `low_height_clean_eligible_activation_rows`,
  `low_height_low_scan_clean_eligible_activation_rows`, or
  `low_height_reintegration_stable_eligible_activation_rows`, or
  `backfill_policy_write_ready_rows`.
- `acceptance_status=pass` requires the product activation delta rows to match
  the eligible audit keys exactly, with no duplicate, missing, unexpected,
  non-eligible, non-written, unchanged, or blank activated-value rows.
- `activation_application_status` must be `applied`.
- `matrix_cells_written` and `product_written_delta_row_count` must both equal
  `eligible_audit_row_count`.
- Passing this gate allows a `production_ready` claim only for the explicit
  scoped writer slice or generated `write_ready` policy scope named by
  `expected_scope`. It does not authorize broad 4613-row standard-path
  activation or default extraction behavior unless every generated
  `write_ready` row is backed by approved evidence classes and the same
  expected-diff gate passes.

### No-RAW / existing-artifact phase

- Use existing blocked gate artifacts to sample examples of
  `standard_peak_gate_blocked`, `peak_not_standard`, manual `non_standard_peak`,
  and any future `nonstandard_peak_shape` rows.
- Produce a representative gallery grouped by integration pathology.
- Do not claim production readiness from token counts or existing summaries.

### Focused fixture phase

Add synthetic or hand-curated traces for:

- Fig. 1 tailing with clean boundaries;
- Fig. 2 shoulder/rough envelope with clean boundaries;
- Fig. 3 unresolved overlap with no defensible boundary;
- Fig. 4 baseline-sensitive peak with clear boundaries but unstable baseline.

Expected outcomes:

- Fig. 1 / Fig. 2: non-standard-assessable, review-only until uncertainty
  threshold exists.
- Fig. 3: unassessable hard block.
- Fig. 4: baseline-sensitive, review-only or uncertainty-gated.

Each fixture must include expected values for:

- `integration_pathology`;
- `boundary_assessability`;
- `baseline_assessability`;
- `matrix_write_allowed`;
- `integration_blockers`;
- boundary source/provenance fields;
- baseline model set and relative area spread, when applicable.

### RAW-backed phase

Only after the fixture phase is stable:

- 8RAW: smoke and gallery review; do not use the seed guard as the decisive
  prevalence oracle because the small-N policy is `not_applicable_small_cohort`.
- 85RAW: stress test the cohort seed-support guard and non-standard pathology
  classifier.
- Held-out detected-cell recovery: mask known detected cells and verify whether
  the integration policy recovers the original boundary, baseline, and area.

Acceptance thresholds for the first implementation slice:

| Oracle | Required threshold / decision |
| --- | --- |
| Boundary recovery | `abs(observed_start_rt - oracle_start_rt) + abs(observed_end_rt - oracle_end_rt) <= 0.1 min` unless a reviewed oracle row specifies stricter tolerance |
| Baseline sensitivity | Relative area spread across the named diagnostic-only baseline model set <= `0.20` for stable baseline; `> 0.20` is baseline-sensitive and review-only |
| Area recovery | Held-out masked-cell area relative error <= `0.10` against a positive reviewed/original detected-cell oracle area; invalid oracle area is `inconclusive_review_only` |
| False promotion | `0` `nonstandard_assessable_area`, baseline-sensitive, or `unassessable_area` cells may reach automatic matrix write unless a separate reviewed promotion contract explicitly allowlists that class |
| False hard-block | `0` standard-assessable large-cohort fixture cells may be blocked by the seed guard when `detected_count >= max(4, floor(total_N * 0.05))`; `0` medium-cohort per-cell fixtures may be blocked when `detected_count >= max(2, floor(total_N * 0.05))` |
| Matrix diff | `unexpected_matrix_diff_count=0`, `missing_matrix_diff_count=0`, and `value_delta_mismatch_count=0` |

The boundary and area recovery tolerances intentionally mirror the existing
selected-envelope oracle defaults: `acceptable_boundary_delta_min = 0.1` and
`acceptable_area_relative_error = 0.1` on `BoundaryOracle`. The `0.20`
baseline-sensitivity threshold follows the existing area-integration uncertainty
diagnostic's high-uncertainty fraction. These are not literature claims. If real
RAW/EIC review shows a threshold is too loose or too strict, change the oracle
manifest or diagnostic threshold first and rerun the matrix-diff acceptance; do
not silently change promotion behavior.

Product decision, 2026-06-17: the first production-readiness oracle gate uses
the defaults above unless a reviewed oracle row specifies a stricter tolerance:
boundary error `<= 0.1 min` and area relative error `<= 0.10`. This acceptance
only fixes the validation gate for reviewed held-out cases. The implemented
heldout oracle evaluator now rejects manifest tolerances looser than these
accepted ceilings. It does not approve any current 85RAW matrix value changes,
broad non-standard promotion, or default automatic backfill without the
expected-diff acceptance packet.

These thresholds are validation/classification oracle thresholds for the
non-standard diagnostic lane. They are not automatic matrix-promotion thresholds
for non-standard or baseline-sensitive cells.

## Stop Rules

Stop at `diagnostic_only` if any of the following remains unresolved:

- standard seed guard implementation does not separate small, medium, and large
  cohort behavior;
- large-cohort implementation does not use
  `max(4, floor(total_N * 0.05))` for `total_N >= 80`;
- medium-cohort implementation claims broad cohort-scale automatic backfill, or
  does not use `max(2, floor(total_N * 0.05))` for per-cell-only eligibility;
- implementation cannot derive `total_N` from the eligible pre-standard-backfill
  activation cohort;
- implementation cannot derive `detected_count` from
  `quantifiable_detected_count` or the allowed pre-backfill production-cell
  fallback;
- small cohorts are reported as pass/fail instead of
  `not_applicable_small_cohort`;
- small or medium cohorts are allowed to claim cohort-scale automatic backfill
  authority;
- `seed_guard_decisions.tsv` does not prove full candidate coverage with
  `candidate_source_row_count == evaluated_row_count` and
  `omitted_candidate_count=0`;
- small or medium cohorts produce
  `actual_cohort_scale_written_cell_count > 0`;
- actual writes cannot join to `activation_value_delta.tsv` by stable
  `peak_hypothesis_id + sample_stem`;
- actual writes exist without `write_authority_status` separating cohort-scale
  writes from per-cell product-authorized writes;
- `heldout_oracle_results.tsv` is missing, incomplete, or does not have exactly
  one result row per manifest row;
- no explicit boundary/baseline provenance fields;
- no machine-checkable boundary defensibility checklist;
- baseline-sensitive rows are represented as current promotion allowlist rows
  instead of diagnostic-only taxonomy rows;
- provenance is reduced to a single trace hash for a product-consuming row;
- no baseline spread, boundary tolerance, or area recovery threshold;
- baseline model set is unnamed or cannot be recomputed on the same boundary;
- no examples of baseline-sensitive and unassessable shapes;
- no held-out validation for non-standard-assessable cells;
- no matrix-diff acceptance contract.

Do not promote non-standard or baseline-sensitive cells merely because same-peak
identity support is strong. Identity support can make a cell worth reviewing; it
does not make the area quantitative.

Do not implement the non-standard taxonomy and the standard seed guard in the
same product-behavior commit. The seed guard changes an existing product path;
the taxonomy is a diagnostic classification surface until a later contract says
otherwise.

## Lifecycle Exit Rules

Diagnostic paths need explicit exits so observability does not become a
permanent substitute for product behavior.

| Line | Current mode | Allowed consumers | Promote when | Externalize when | Retire when |
| --- | --- | --- | --- | --- | --- |
| C2 reconciliation/gallery | `diagnostic_only` support infrastructure | Human review, activation planning, validation sampling | Allowlisted slice has named product authority, expected matrix diff, and reviewer-approved promotion contract | Gallery remains useful for manual review but not for matrix decisions | It no longer changes decisions or duplicates another review surface |
| C4 area integration uncertainty | `diagnostic_only` audit oracle | Integration review, baseline/boundary fixture design, non-standard triage | Boundary and baseline uncertainty metrics have thresholds, held-out recovery, and matrix-diff acceptance | Useful as an audit report but too weak or costly for automatic gates | No future gate, no review consumer, or redundant with `IntegrationResult`/`AuditTrail` fields |

## Relationship To Existing Bucket C

- C1 remains a product-expansion question for PeakHypothesis backfill. The
  standard-peak path can receive the cohort seed-support guard first because it
  is the currently backfillable path.
- C2 remains useful as review/support infrastructure, not product authority.
- C3 is orthogonal: identity coherence can challenge same-peak support but does
  not solve boundary or baseline integration.
- C4 should be preserved and reframed from boundary-only audit to
  boundary-plus-baseline integration uncertainty.

## Non-Goals

- This spec does not implement new gates.
- This spec does not rename existing public TSV columns.
- This spec does not approve non-standard matrix writes.
- This spec does not reopen the AsLS-vs-linear-edge retirement decision.
- This spec does not claim literature consensus can determine local peak
  policy without RAW/EIC validation.
