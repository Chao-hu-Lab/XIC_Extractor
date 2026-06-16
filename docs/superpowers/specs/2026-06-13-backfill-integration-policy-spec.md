# Backfill Integration Policy Spec

## Status

Design draft after critical review. No implementation is included in this
document.

Validation labels are split by lane:

- Standard-path cohort seed guard: `implementation_candidate`.
- Non-standard integration taxonomy: `diagnostic_only` / `design_input`.

This spec captures the current owner discussion about standard-peak backfill
seed support, non-standard peak integration, and area uncertainty. It does not
itself change `run_alignment`, `alignment_matrix.tsv`, activation decisions,
workbook schemas, or any production gate. The seed-support rule below is a
product decision captured for a future standard-path implementation slice; it
is not active until implemented and validated.

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
| Standard seed guard | `implementation_candidate` | Yes, but only as a blocker on the current standard-peak path | Seed-guard decision artifact plus matrix-diff test on standard-path rows | Cannot prove `total_N`, `detected_count`, and expected diff from the same pre-backfill source |
| Non-standard taxonomy | `diagnostic_only` | No | Gallery/TSV classifying boundary and baseline pathology | Any consumer tries to use the taxonomy as promotion authority |
| Baseline-sensitive audit | `diagnostic_only` | No | Baseline spread report over a named diagnostic-only baseline model set | Baseline set is missing, unstable, or not tied to row provenance |
| Future non-standard promotion | Not approved | Only after a new contract | Schema/test proposal for non-standard matrix writes | Missing manual/EIC or held-out oracle, uncertainty threshold, or matrix-diff acceptance |

The first implementation slice should be the standard seed guard only. It must
not introduce non-standard promotion, new public `area_policy` enums, or
baseline-sensitive matrix writes.

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
- `boundary_error_min` must use the manifest formula above.
- `area_relative_error` must use the manifest area denominator rule above.
- Any row included in product acceptance must have `oracle_case_status=pass`.
- Any row with `oracle_case_status` other than `pass` must have
  `included_in_product_acceptance=FALSE`; otherwise the lane fails.

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
