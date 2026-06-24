# Final Matrix Row Completion Confidence Benchmark

Status: implemented diagnostic contract plus baseline-bound shadow gate.
Date: 2026-06-23
Branch: `cc/framework-improvements`

Subtitle: Alignment, backfill, and external reviewer evidence for XIC product
matrices.

## Current Verdict

This spec defines a row-completion confidence benchmark with two lanes:
diagnostic artifact acceptance and a baseline-bound product-gate mode. The
product-gate mode can block product-gate eligibility, but it does not change the
default preset, matrix writer authority, selected peaks, selected areas,
counted detections, matrix identity, workbook/TSV schemas, active product lane,
or production-ready maturity tier.

The benchmark's first job is to help method development. It should tell us
whether a rule change improved, regressed, or merely shifted row completion
behavior. Its second job is to support future product gates. Its long-term job
is to produce reviewer-readable evidence that XIC row completion is credible
against mature LC-MS preprocessing/alignment tools.

## Problem Statement

The existing alignment pipeline has useful auditability, but "the current
8RAW/85RAW run did not show an obvious problem" is not enough scientific
confidence. Mature tools have years of edge-case coverage around feature
linking, RT drift, over-grouping, gap filling, peak shape, low-signal recovery,
and external review workflows.

XIC needs a confidence harness that is cheap enough for active modeling and
strict enough for product-gate decisions. The harness must not confuse
diagnostic evidence with matrix-writing authority.

## Conceptual Model

The core product question is not only "did alignment group features correctly?"
It is:

> Did the final matrix row receive the right cell values across samples without
> breaking row identity?

Alignment and backfill are related parts of the same row completion problem:

- `observed_assignment`: discovery observed a feature in a sample, and the
  system must decide which cross-sample row it belongs to.
- `missing_or_weak_completion`: discovery did not directly accept a tagged
  feature or did not observe enough evidence, but RT, MS1 trace, peak shape,
  neighboring samples, row identity, or backfill evidence may justify a cell.
- `row_identity_integrity`: both observed assignment and missing/weak
  completion must preserve the row's chemical or signal identity.

Backfill evidence is therefore part of row completion confidence. It is not a
separate product authority, and it must not automatically promote a row or cell
into the product matrix.

## Goals

- Define a repeatable confidence benchmark for final matrix row completion.
- Support fast artifact-only checks during active rule modeling.
- Define a stricter gate lane for changes that may affect product behavior.
- Treat mature-tool output as external reviewer evidence, not ground truth.
- Separate production safety from review utility.
- Make backfill-derived evidence first-class diagnostic evidence for row
  completion without changing matrix authority.
- Keep the first implementation cheap enough to run repeatedly on existing
  8RAW/85RAW artifacts.

## Non-Goals

- Do not change the alignment algorithm in this spec.
- Do not change backfill policy in this spec.
- Do not change selected peak, area, apex, RT, counted detection, matrix
  identity, active writer scope, or output schema.
- Do not make MZmine, XCMS, MS-DIAL, OpenMS, or any other mature tool a source
  of truth.
- Do not require every modeling iteration to run 85RAW.
- Do not require manual EIC/MS2 review on every run.
- Do not require an HTML report in version 1.

## Version 1 Scope

Version 1 is deliberately A-first and B-secondary.

A-first means the first implementation is limited to:

- `alignment_health_packet` inputs.
- targeted GT outputs for the small canonical panel.
- baseline/current artifact-only comparison.
- a manifest-bound daily report.
- a gate-panel report that can say `PASS`, `WARN`, `FAIL`, or
  `INCONCLUSIVE` without changing product behavior.

B-secondary means mature-tool comparison is only a schema contract in version
1. Do not implement an external parser, mature-tool adapter, disagreement
classifier, or manual-review queue writer until a concrete external export,
sample mapping, and provenance manifest exist.

Manual review in version 1 is trigger-only. The benchmark may say manual review
is required and name the reason; it must not create a durable manual queue
writer until sentinel and disagreement schemas are stable.

Backfill is included only through existing bounded artifacts:

- `alignment_backfill_cell_evidence.tsv`
- `alignment_owner_backfill_seed_audit.tsv`
- `alignment_health_packet` summary and sentinel outputs

Do not create a new broad Backfill sidecar, truth source, or writer scope as
part of this benchmark. Broad Backfill auto-write remains parked unless a new
independent truth source and a separate expected-diff/product-writer oracle are
approved.

## Preflight Contract

Goal:
Create a row completion confidence benchmark that covers alignment, backfill,
and external reviewer evidence, with diagnostic artifact acceptance separated
from baseline-bound product-gate eligibility.

Existing owner/helper to reuse:

- `tools/diagnostics/targeted_gt_alignment_audit.py`
- `tools/diagnostics/alignment_health_packet.py`
- Existing alignment artifacts:
  - `alignment_review.tsv`
  - `alignment_matrix.tsv`
  - `alignment_matrix_identity.tsv`
  - `alignment_backfill_cell_evidence.tsv`
  - `alignment_owner_backfill_seed_audit.tsv`
- `xic_extractor.tabular_io` for TSV/JSON helpers.
- Existing productization/control-plane docs for authority boundaries.

New code location:
The spec is docs-only. A future CLI can live at
`tools/diagnostics/row_completion_confidence.py`, but that CLI should only
parse arguments, resolve paths, call package APIs, and write contracted
outputs. Reusable loading, schemas, comparison, classification, summaries, and
report models belong under focused package modules, preferably
`xic_extractor/diagnostics/row_completion_confidence*`. TSV/CSV/JSON mechanics
must reuse `xic_extractor.tabular_io`.

Evidence provider role:
Targeted truth panels, backfill evidence, health sentinels, and mature-tool
exports are evidence providers for confidence judgment. They do not directly
write product matrix cells.

Simplest product rule:
No new product rule in version 1. The benchmark separates production safety
from review utility and reports whether a future product gate is eligible.

Call-cost model:
Version 1 is artifact-first. The daily lane reads TSV/JSON artifacts only and
does not open RAW. Gate validation may request a fresh 8RAW run when code
changed. 85RAW is a stress gate, not a daily requirement. External tool exports
are ingested as files; the XIC pipeline must not invoke mature tools as hidden
subprocesses.

Public contracts at risk:
The spec itself only adds a diagnostic contract. Future implementations must
treat CLI flags, config keys, TSV/CSV/workbook schema, matrix identity,
selected values, counted detections, output paths, and artifact names as public
contracts.

Validation gate:
Spec review first. Implementation later requires synthetic fixtures,
artifact-only smoke, 8RAW confidence run, optional 85RAW stress run, and manual
EIC/MS2 review only when the benchmark raises a review gate.

Stop rule:
Stop the diagnostic path and use expected-diff/product-gate workflow if a
change would alter selected values, counted detections, matrix identity, writer
authority, active lane, maturity tier, or default preset behavior.

## Authority Boundary

This benchmark may produce `diagnostic_only` recommendations. It may not update
the productization control plane, authority manifest, status index, active lane,
or current handoff unless a separate product-gate decision explicitly does so.

The benchmark must emit a no-authority statement in every Markdown report:

```text
This row-completion confidence report is diagnostic_only. It does not change
matrix authority, selected values, counted detections, active lane, maturity
tier, or default preset behavior.
```

## Benchmark Lanes

### 1. Daily Artifact Lane

Purpose:
Fast feedback during active modeling.

Inputs:

- Existing alignment TSV/JSON artifacts.
- `alignment_health_packet` summary and sentinel outputs.
- Optional prior benchmark summary for trend comparison.

Cost:
Artifact-only. No RAW reads. No XIC extraction. No mature-tool invocation.

Decision:
Trend/regression only:

- `improved`
- `stable`
- `regressed`
- `shifted`
- `inconclusive`

The daily lane must not emit hard product readiness claims.

### 2. Gate Panel Lane

Purpose:
Check whether a rule is safe enough to approach a product gate.

Inputs:

- A small canonical panel:
  - 5-medC
  - 5-hmdC
  - duplicate-only cases
  - zero-present cases
  - high-backfill-dependency cases
  - ambiguous MS1 owner cases
  - consolidation loser/winner cases
  - external disagreement cases when available
- Current artifact set.
- Baseline artifact set.
- Optional fresh 8RAW run when code changed.

Decision:

- `PASS`
- `WARN`
- `FAIL`
- `INCONCLUSIVE`

The gate lane can block product-gate eligibility, but it does not itself change
product authority.

### 3. External Reviewer Lane

Purpose:
Use mature tools as external reviewers and pressure-test sources.

Version 1 status:
Schema-only. Do not implement a parser or disagreement classifier until the
first external export, sample mapping, and provenance manifest are available.

Input contract:

- `external_tool`
- `external_run_id`
- `external_tool_version`
- `external_adapter_version`
- `sample_id`
- `feature_id`
- `mz` in Da
- `rt` in minutes
- `area_or_intensity`
- `area_or_intensity_semantics`
- Optional `annotation`
- Optional `adduct`
- Optional `charge`
- Optional `quality_score`

Mapping config:

- m/z tolerance in Da or ppm
- RT tolerance in minutes
- sample-name mapping
- optional target/family mapping
- duplicate feature policy
- missing or NaN handling policy
- external export SHA256 and row count

Disagreement classes:

- `xic_likely_better`
- `xic_suspect`
- `external_tool_suspect`
- `both_plausible`
- `needs_manual_eic_ms2_review`
- `not_comparable_due_to_contract`

External tools are never ground truth by default. A disagreement is evidence to
classify, not an automatic defect.

Mapping quality pregate:

- `PASS`: all required columns exist, sample mapping coverage is 100% for the
  compared sample universe, tolerance units are declared, export provenance is
  hashed, duplicate policy is declared, and unmatched/duplicate rates are
  below the gate threshold in the manifest.
- `WARN`: mapping is usable but has declared unmatched or duplicate features
  that require manual review before scientific interpretation.
- `FAIL`: required columns are missing, sample mapping is incomplete, tolerance
  units are absent, or duplicate policy is undeclared.
- `INCONCLUSIVE`: the external export exists but cannot be compared to the XIC
  artifact set without more mapping metadata.

### 4. Manual Review Lane

Purpose:
Use human EIC/MS2 review only when it changes confidence.

Triggers:

- Gate lane `WARN`, `FAIL`, or `INCONCLUSIVE`.
- External reviewer conflict rate crosses a chosen review threshold.
- Production-safety sentinel cases dominate the top ranked panel.
- A rule is being considered for product behavior change.

Output:
Manual adjudication TSV/Markdown that updates benchmark judgment. Manual review
does not directly write product matrix values.

Version 1 status:
Trigger-only. Emit `manual_review_required=true` and a reason, but do not write
a durable manual-review queue artifact.

## Gate Definitions

All lanes must emit the standard acceptance labels below.

### `run_ok`

`run_ok=true` only when:

- required inputs for the lane are present;
- required columns exist;
- schema versions are known or explicitly marked legacy-compatible;
- baseline and current artifacts record relpath, size, SHA256, and row count;
- outputs are written with `schema_version`;
- missing optional artifacts are reported as named missing-evidence codes.

Otherwise `run_ok=false` and the final status is `INCONCLUSIVE`.

### `gate_ok`

Daily artifact lane:

- `gate_ok=true` means the report computed all required daily metrics from
  artifact-bound inputs.
- It does not mean production readiness.

Product-gate mode on the daily artifact lane:

- `--gate-mode product-gate` requires `--baseline-alignment-dir`.
- If no baseline is supplied, `run_ok=true` may still show the current artifacts
  were readable, but `gate_ok=false`, `status=INCONCLUSIVE`,
  `validation_tier=inconclusive`, and
  `missing_evidence_code=baseline_current_unbound`.
- If baseline/current selected values, matrix `Mz`/`RT` anchors, and matrix
  identity are unchanged, `gate_ok=true`, `status=PASS`, and
  `validation_tier=shadow_ready`.
- If selected values, row count, sample columns, `Mz`/`RT` anchors, or ordered
  identity drift, `gate_ok=false`, `status=FAIL`, and
  `authority_decision=expected_diff_required`.

Gate panel lane:

- `PASS`: all required panel cases were evaluated, no production-safety metric
  regressed, targeted GT panel status is stable or improved, and no unapproved
  matrix identity or selected-value drift exists.
- `WARN`: no wrong inclusion or identity drift is detected, but review burden,
  high-backfill dependency, external conflict pressure, or manual-review need
  increased enough to block automatic confidence promotion.
- `FAIL`: a required panel case regressed, wrong inclusion appears, zero-present
  or duplicate-only production risk increases, targeted GT recall regresses, or
  matrix identity / selected value / counted detection drifts without
  expected-diff approval.
- `INCONCLUSIVE`: required artifacts are missing or stale, the panel manifest
  cannot bind cases to artifacts, required metrics cannot be computed, or
  external mapping quality fails before disagreement classification.

External reviewer lane:

- `gate_ok=true` only after the mapping quality pregate passes.
- Without external inputs, the lane is `not_available`, not failed.

### `production_ready`

This benchmark cannot mark `production_ready` by itself. Product readiness
requires a separate expected-diff/product-gate packet, focused public-contract
tests, artifact-bound 8RAW and 85RAW evidence, and a control-plane decision if
behavior or authority changes.

### `inconclusive`

Use explicit missing-evidence codes:

- `missing_required_artifact`
- `missing_required_column`
- `unknown_schema_version`
- `stale_artifact_manifest`
- `baseline_current_unbound`
- `metric_source_unavailable`
- `canonical_panel_case_unbound`
- `external_mapping_quality_failed`
- `manual_review_required`
- `product_gate_required`

## Artifact Freshness And RAW Rerun Decision

Existing artifacts are usable only when the artifact manifest binds relpath,
SHA256, size, row count, run id, and generation context to the code/config/input
surface being evaluated.

| Change class | Required action | Reason |
| --- | --- | --- |
| Docs-only wording, report wording, or this spec only | no rerun | no artifact generation behavior changed |
| Benchmark reader, metric aggregation, schema rendering, Markdown report, or manifest formatting only | artifact-only rerun of the benchmark | existing alignment artifacts remain valid; only benchmark interpretation changed |
| Benchmark join keys, metric source mapping, canonical panel mapping, or fail-closed logic changed | artifact-only rerun plus focused synthetic tests | RAW artifacts remain valid, but benchmark classification may change |
| Alignment, discovery, extraction, backfill, scoring, primary consolidation, matrix writer, publication check, or artifact writer generation code changed | fresh 8RAW required before gate lane can pass | existing artifacts may be stale relative to generation behavior |
| Config defaults, preset flags, target list, RAW set, sample universe, sample mapping, tolerance settings, or external table mapping changed | fresh 8RAW required before gate lane can pass | the sample/target or matching universe changed |
| Product-gate packet, maturity-tier change, writer authority change, selected value/counting change, or 85RAW stress claim | 85RAW required after focused and 8RAW evidence | stress evidence is needed only for product-gate or final large-sample claims |
| Current 85RAW artifact manifest is missing, stale, or generation context cannot be proven | `INCONCLUSIVE`; do not silently substitute old 85RAW | stale large-run evidence is worse than missing evidence |
| Change class cannot be classified | `INCONCLUSIVE` | unknown blast radius requires human review before rerun or acceptance |

This table is a decision rule, not a command launcher. The benchmark report may
recommend a fresh run, but it must not launch RAW processing.

## Implementation Contract

Future implementation must follow these placement rules:

- CLI: `tools/diagnostics/row_completion_confidence.py`.
- Package API: `xic_extractor/diagnostics/row_completion_confidence*`.
- Shared TSV/JSON mechanics: `xic_extractor.tabular_io`.
- Production-decision semantics: read existing alignment outputs or reuse
  `xic_extractor.alignment.production_decisions`; do not reconstruct writer
  authority from scratch in a diagnostic.
- Diagnostic writers render only. They must not recompute evidence, re-read
  RAW, or run mature tools.

All outputs must include:

- `schema_version`
- `run_id`
- `lane`
- `status`
- `reason`
- `input_artifact_manifest`
- `no_authority_statement`

Baseline/current comparison must be manifest-bound. A baseline or current
artifact set is usable only if every required file has relpath, SHA256, size,
row count, and generation context. If generation context is unavailable, the
lane must be `INCONCLUSIVE`, not silently rerun RAW.

## Metric Model

The benchmark must not emit a single blended score. It emits separate judgments
for production safety and review utility.

### Production Safety Metrics

Production safety answers whether a row or cell can safely enter the product
matrix.

Required metrics:

- `wrong_inclusion_risk`
- `overmerge_risk`
- `oversplit_risk`
- `duplicate_only_family_count`
- `zero_present_family_count`
- `high_backfill_dependency_count`
- `matrix_identity_drift`
- `selected_value_drift`
- `counted_detection_delta`

Production-safety regressions block product-gate eligibility unless an
expected-diff packet explicitly approves the change.

### Production Safety Source Mapping

Version 1 metrics must be computed from named artifacts and keys:

| Metric | Source artifact | Join key | Direction |
| --- | --- | --- | --- |
| `duplicate_only_family_count` | `alignment_health_summary.json` row flags or `alignment_health_family_sentinels.tsv` | `feature_family_id` | lower is safer |
| `zero_present_family_count` | `alignment_health_summary.json` row flags or sentinels | `feature_family_id` | lower is safer |
| `high_backfill_dependency_count` | `alignment_health_summary.json` row flags and `alignment_backfill_cell_evidence.tsv` | `feature_family_id` | lower is safer |
| `matrix_identity_drift` | baseline/current `alignment_matrix_identity.tsv` | `feature_family_id` | any unapproved drift is unsafe |
| `selected_value_drift` | baseline/current `alignment_matrix.tsv` plus `alignment_backfill_cell_evidence.tsv` when available | `feature_family_id`, `sample_stem` | unapproved value drift is unsafe |
| `counted_detection_delta` | publication check output and matrix identity sidecars | run-level and `feature_family_id` | unapproved delta is unsafe |
| `wrong_inclusion_risk` | canonical panel manifest plus current matrix/identity artifacts | `case_id`, `feature_family_id`, optional `sample_stem` | any confirmed wrong inclusion is unsafe |
| `overmerge_risk` | canonical panel, duplicate/consolidation sentinels, identity drift | `case_id`, `feature_family_id` | lower is safer |
| `oversplit_risk` | canonical panel, targeted GT audit output, external contract when available | `case_id`, target key | lower is safer |

If a source artifact is unavailable, emit `metric_source_unavailable` instead
of inventing the metric from a weaker surface.

### Review Utility Metrics

Review utility answers whether a row or cell helps exploration, adjudication,
or method development.

Required metrics:

- `truth_set_recall`
- `missing_or_weak_completion_recovery`
- `accepted_rescue_count`
- `review_rescue_count`
- `manual_review_burden`
- `needs_eic_ms2_review_count`
- `external_disagreement_coverage`
- `sentinel_explainability`
- `overlay_or_trace_evidence_available`
- `area_correlation_or_drift`
- `apex_rt_drift`

Review utility can improve while production safety remains unchanged or
regresses. A backfill-heavy row can be useful for review and still unsafe for
production matrix inclusion.

### Review Utility Source Mapping

| Metric | Source artifact | Join key | Direction |
| --- | --- | --- | --- |
| `truth_set_recall` | targeted GT audit outputs and canonical panel manifest | `case_id`, target key, `sample_stem` | higher is better |
| `missing_or_weak_completion_recovery` | `alignment_backfill_cell_evidence.tsv` and seed audit | `feature_family_id`, `sample_stem` | higher can be useful but must not bypass safety |
| `accepted_rescue_count` | `alignment_health_summary.json` and backfill evidence | run-level, `feature_family_id` | trend only |
| `review_rescue_count` | `alignment_health_summary.json` and backfill evidence | run-level, `feature_family_id` | trend only |
| `manual_review_burden` | sentinel count, manual-review trigger count, external conflict count | run-level | lower is better |
| `needs_eic_ms2_review_count` | gate panel and external reviewer lane | `case_id` | lower is better |
| `external_disagreement_coverage` | external reviewer contract when available | external feature key, XIC key | higher coverage is better only after mapping passes |
| `sentinel_explainability` | sentinel TSV status/reason/recommended_action fields | `case_id`, `feature_family_id` | named reason required |
| `overlay_or_trace_evidence_available` | backfill evidence and retained trace/overlay manifests when available | `feature_family_id`, `sample_stem` | higher is better |
| `area_correlation_or_drift` | backfill evidence and targeted/external reference when available | `feature_family_id`, `sample_stem` | lower drift is better |
| `apex_rt_drift` | backfill evidence and targeted/external reference when available | `feature_family_id`, `sample_stem` | lower drift is better |

Area and apex drift are `metric_source_unavailable` unless both sides of the
comparison have explicit area/apex fields with compatible units.

### Final Judgment Fields

Every benchmark run should emit:

```text
production_safety: improved | stable | regressed | inconclusive
review_utility: improved | stable | regressed | inconclusive
external_reviewer_signal: supportive | conflict_found | not_available | not_comparable
manual_review_required: true | false
product_gate_candidate_packet_required: true | false
authority_decision: no_control_plane_change | expected_diff_required | control_plane_decision_required
```

Hard rule:
Review utility improvement is not production readiness improvement.

## Inputs

### Required For Daily Artifact Lane

- `alignment_review.tsv`
- `alignment_matrix.tsv`
- `alignment_matrix_identity.tsv`
- `alignment_health_summary.json`
- `alignment_health_family_sentinels.tsv`
- baseline/current artifact manifest with relpath, SHA256, size, row count,
  run id, and generation context

### Optional But Preferred

- `alignment_backfill_cell_evidence.tsv`
- `alignment_owner_backfill_seed_audit.tsv`
- `timing.json`
- `timing.live.json`
- `product_ready_preset_publication_check` output
- prior benchmark summary for trend comparison

### Required For Gate Panel Lane

- canonical panel definition:
  `docs/superpowers/validation/row_completion_canonical_panel_v1.tsv`
- canonical panel manifest:
  `docs/superpowers/validation/row_completion_canonical_panel_manifest_v1.json`
- targeted GT audit outputs for 5-medC and 5-hmdC
- current run artifact set
- baseline artifact set
- optional fresh 8RAW evidence when code changed

Canonical panel TSV columns:

- `case_id`
- `case_type`
- `target_label`
- `feature_family_id`
- optional `sample_stem`
- `expected_outcome`
- `production_safety_expectation`
- `review_utility_expectation`
- `required_artifacts`
- `baseline_binding`
- `manual_review_trigger`
- `reason`

### Required For External Reviewer Lane

- external feature table export matching the contract
- sample-name mapping when external sample names differ
- m/z and RT tolerances
- optional target/family mapping

## Outputs

Version 1 should write:

- `row_completion_confidence_summary.json`
- `row_completion_confidence_summary.tsv`
- `row_completion_sentinels.tsv`
- `row_completion_family_sentinels.tsv` compatibility alias
- `row_completion_disagreements.tsv`
- `row_completion_confidence_report.md`

All output schemas use `row_completion_confidence_v1`.

`row_completion_confidence_summary.json` includes the lane-level fields
`gate_mode`, `validation_tier`, `baseline_binding`, `run_ok`, `gate_ok`,
`status`, `product_gate_eligible`, `production_ready`,
`production_safety`, `review_utility`, `authority_decision`,
`missing_evidence_code`, `input_artifact_manifest`, and
`no_authority_statement`.

`row_completion_confidence_summary.tsv` columns:

- `schema_version`
- `run_id`
- `lane`
- `metric_name`
- `status`
- `current_value`
- `baseline_value`
- `delta`
- `direction`
- `evidence_source`
- `artifact_relpath`
- `artifact_sha256`
- `reason`
- `missing_evidence_code`
- `input_artifact_manifest`
- `no_authority_statement`

`row_completion_sentinels.tsv` columns:

`row_completion_family_sentinels.tsv` is a compatibility alias with the same
columns and contents. New consumers should prefer `row_completion_sentinels.tsv`;
existing consumers may keep reading the legacy filename during migration.

- `schema_version`
- `run_id`
- `rank`
- `case_id`
- `lane`
- `case_type`
- `feature_family_id`
- `sample_stem`
- `production_safety_status`
- `review_utility_status`
- `issue_class`
- `severity_score`
- `evidence_source`
- `recommended_action`
- `requires_manual_review`
- `reason`

`row_completion_disagreements.tsv` columns:

- `schema_version`
- `run_id`
- `disagreement_id`
- `external_tool`
- `external_run_id`
- `mapping_status`
- `sample_id`
- `sample_stem`
- `feature_family_id`
- `external_feature_id`
- `mz_delta`
- `rt_delta_min`
- `classification`
- `reason`

If external reviewer inputs are absent, the disagreement output should still be
written with `external_reviewer_signal=not_available` or the equivalent empty
table status.

HTML is explicitly deferred until the sentinel and disagreement schemas are
stable.

## Markdown Report Shape

The human-readable report should use this order:

1. Verdict
2. What Changed Since Baseline
3. Production Safety
4. Review Utility
5. Backfill As Row Completion Evidence
6. External Reviewer Signal
7. Manual Review Queue
8. Product Gate Packet Requirement
9. Inconclusive / Missing Evidence
10. Next Recommended Action

The report should lead with the judgment, not with artifact names.

## Validation Plan

### Spec-Only Validation

- Verify that diagnostic evidence is not described as product authority.
- Verify production safety and review utility are separated.
- Verify mature tools are external reviewers, not ground truth.
- Verify backfill evidence supports row completion confidence without changing
  writer authority.

### Implementation Smoke

Use synthetic fixtures covering:

- duplicate-only row
- zero-present row
- high-backfill-dependency row
- accepted rescue versus review-only rescue
- observed assignment versus missing/weak completion
- external reviewer schema validation and mapping-quality pregate status

No RAW required.

### Artifact-Only Real-Data Smoke

- Run first on existing 8RAW artifacts.
- Optionally run on existing 85RAW artifacts for stress signal.
- Public matrix outputs must not change.

### Gate Panel Validation

Use the canonical panel:

- 5-medC
- 5-hmdC
- duplicate/consolidation sentinel cases
- ambiguous owner cases
- selected external disagreement cases when available

Gate judgment uses `PASS`, `WARN`, `FAIL`, or `INCONCLUSIVE`.

### Product Gate Validation

Only required if a future change wants to alter default preset behavior, writer
authority, selected area/counting, matrix identity, active lane, or maturity
tier.

Product gate validation requires:

- expected-diff packet
- 8RAW evidence
- 85RAW evidence
- control-plane decision
- focused tests covering the public contract that changed

## Stop Rules

Stop diagnostic-only work and switch to expected-diff/product gate if:

- selected peak, area, apex, RT, counted detection, matrix identity, or writer
  authority would change;
- benchmark thresholds are used to automatically include or exclude product
  matrix cells;
- backfill evidence is promoted to default matrix authority;
- external tool disagreement is treated as ground truth;
- manual review output directly writes the product matrix;
- 85RAW fixture shape or CID-NL assumptions are made permanent core rules;
- a diagnostic writer starts recomputing evidence or reading RAW.

## Initial Implementation Plan Shape

The implementation plan created after this spec should start with:

1. Add package-owned row completion schema and manifest models under
   `xic_extractor/diagnostics/row_completion_confidence*`.
2. Add synthetic fixtures for production-safety and review-utility metric
   source mapping.
3. Add the canonical panel TSV/JSON manifest under
   `docs/superpowers/validation/`.
4. Build the artifact-only daily lane on top of `alignment_health_packet`.
5. Add manifest-bound baseline/current comparison and final judgment fields.
6. Add the gate-panel report.
7. Add external reviewer schema validation only. Do not add a mature-tool
   adapter, parser, or disagreement classifier in version 1.
8. Add manual-review trigger fields only. Do not add a manual-review queue
   writer in version 1.

## Resolved Version 1 Decisions

- Canonical panel definitions live under `docs/superpowers/validation/`.
- Synthetic fixtures live under `tests/fixtures/diagnostics/` or focused tests.
- Existing 85RAW artifacts can be used as gate stress evidence only when the
  artifact manifest binds relpaths, hashes, row counts, run id, and generation
  context. They are not part of the daily lane by default.
- No mature-tool adapter is selected in version 1. MZmine can be the first
  reference adapter later only after a concrete export and sample mapping exist.
- Manual review threshold in version 1 is categorical: any gate `WARN`,
  `FAIL`, `INCONCLUSIVE`, unapproved production-safety drift, or failed external
  mapping quality sets `manual_review_required=true`. Numeric thresholds are a
  later version after real sentinel distributions are observed.
