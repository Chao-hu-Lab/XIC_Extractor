# Provisional Backfill Production-Candidate Gate Design

## Status

Experimental design approved for diagnostic pilot planning. No implementation is
included in this document.

Validation label for the current evidence: `diagnostic_only`.

The gate proposed here is machine-facing and experimental. It should help the
alignment pipeline classify retained provisional backfill rows without making
human review the normal decision path. It does not change `alignment_matrix.tsv`
primary-matrix semantics.

`production_candidate` is not approved as a product role by this design. It is a
candidate sidecar status that may be emitted only when a named, allowlisted
independent Tier 2 evidence source provides at least one positive support
component and all challenge checks pass. Artifact-derived RT coherence,
scan-support distribution, and local-apex consistency are dependent context only.

## Product Spine

This design advances the machine-readable `EvidenceVector` and `AuditTrail`
spine for untargeted alignment. It does not advance `Trace` / `TraceGroup`,
multi-source `PeakHypothesis`, `IntegrationResult`, or model selection directly.

The experimental row role progression is:

```text
provisional_discovery -> production_candidate -> production_family
```

`production_candidate` means the evidence chain is strong enough for a machine
consumer to track, rank, and challenge the row as a future production candidate.
It is not a primary quantitative output and must not enter `alignment_matrix.tsv`
without a later promotion contract.

## Context

The tiered backfill machine-decision contract currently separates backfill into:

1. evidence collection;
2. provisional row retention;
3. primary matrix inclusion.

The current implementation keeps one-detected-seed rows with coherent rescued
cell evidence as `provisional_discovery`, adds explicit row flags, and exposes a
diagnostic-only machine projection. It deliberately keeps `alignment_matrix.tsv`
primary-only.

The user goal is longer-term machine decision-making: human review should become
a calibration and exception surface, not the default arbiter. A small,
explicitly scoped Tier 2 gate is acceptable if it adds independent evidence and
does not silently promote weak rows into production quantification.

## 8RAW Evidence

Current 8RAW run:

```text
output\tiered_backfill_candidate_gate_8raw_current
```

Command shape:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\tiered_backfill_candidate_gate_8raw_current `
  --expected-sample-count 8 `
  --output-level validation-minimal `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --timing-output output\tiered_backfill_candidate_gate_8raw_current\timing.json `
  --timing-live-output output\tiered_backfill_candidate_gate_8raw_current\timing.live.json
```

Observed counts:

| Metric | Count |
| --- | ---: |
| `alignment_review.tsv` rows | 2395 |
| `alignment_matrix.tsv` rows | 323 |
| `provisional_discovery` rows | 239 |
| provisional + one detected | 220 |
| provisional + one detected + rescue | 31 |
| `provisional_retention_candidate` rows | 7 |

The seven current candidates are all `DNA_dR` rows with
`primary_evidence=owner_complete_link`. Five are blocked from primary by
`extreme_backfill_dependency`; two are blocked by
`insufficient_detected_identity_support`.

This evidence supports a selective Tier 2 pilot. It does not prove that
`production_candidate` is a production role. Running Tier 2 for all provisional
rows would be too broad; running it for the retention-candidate subset is small
enough to be tractable and decision-relevant.

## 85RAW Evidence

Current 85RAW run:

```text
output\tiered_backfill_candidate_gate_85raw_current
```

Evidence note:

```text
docs\superpowers\notes\2026-05-29-provisional-backfill-candidate-gate-85raw-evidence-note.md
```

Observed counts:

| Metric | Count |
| --- | ---: |
| `alignment_review.tsv` rows | 21812 |
| `alignment_matrix.tsv` rows | 610 |
| `provisional_discovery` rows | 617 |
| provisional + one detected | 549 |
| provisional + one detected + rescue | 85 |
| `provisional_retention_candidate` rows | 7 |

The seven 85RAW candidates are also all `DNA_dR` rows with
`primary_evidence=owner_complete_link`. Four are blocked from primary by
`extreme_backfill_dependency`; three are blocked by
`insufficient_detected_identity_support`.

This resolves the scale question: the candidate pool did not explode in the full
85RAW tissue set. It does not resolve the product-readiness question: the pool
is still concentrated in one feature class, and no independent Tier 2 evidence
has been collected yet.

## Goals

- Add a machine-facing sidecar pilot for retained provisional backfill rows.
- Allow `production_candidate` only when a row passes a stronger Tier 2 evidence
  chain with at least one allowlisted independent non-provenance support
  component from a named source.
- Keep `alignment_matrix.tsv` unchanged and primary-only.
- Keep human review as a calibration and exception path, not the normal
  consumer.
- Make Tier 2 evidence explicit, bounded, allowlisted, and auditable.
- Produce a candidate surface that future gates can consume without parsing
  human-oriented review text.

## Non-Goals

- Do not promote one-detected-seed rows into `alignment_matrix.tsv`.
- Do not run Tier 2 for every `provisional_discovery` row.
- Do not replace owner-backfill selection with a model.
- Do not require manual EIC review for every candidate.
- Do not expand this design into ASLS, resolver, or primary matrix migration.

## Design

### Tier 0 / Tier 1 Eligibility

The production-candidate gate starts from existing machine-decision output and
alignment review/cell rows.

A row is eligible for Tier 2 only when all of these are true:

- `matrix_role=provisional` or equivalent current review fields;
- `identity_decision=provisional_discovery`;
- `row_flags` contains `single_detected_seed`;
- `row_flags` contains `provisional_retention_candidate`;
- `quantifiable_detected_count=1`;
- `quantifiable_rescue_count>0`;
- duplicate and ambiguous counts are zero;
- row is not `review_only` by exact token or `identity_reason`;
- row is not a consolidation loser;
- rescued cells are already supported by Tier 1 cell evidence.

`rescue_only_review` is not the same as `review_only`. It is a production-cell
blanking flag used when a provisional row is not included in the primary matrix.
It must not exclude a row from the diagnostic sidecar by substring matching.

Rows outside this subset keep their existing roles:

- structurally invalid rows remain `audit` or `excluded`;
- weak single-sample local owners remain normal provisional discovery rows;
- low-coverage or neighboring-interference rows remain audit candidates.

### Tier 2 Evidence

Tier 2 must add evidence that is not merely a restatement of
`trace_quality=owner_backfill`. Only named, allowlisted independent sources can
contribute positive support. Current alignment artifacts can provide dependent
context and challenge blockers, but they do not by themselves provide positive
support.

Evidence components are classified by decision power:

Dependent context, useful for orientation but insufficient by itself:

- seed-aware shape overlay around the actual owner-backfill seed;
- family MS1 overlay around the retained family center;
- rescued-cell cross-sample RT coherence;
- rescued-cell scan-support distribution;
- selected boundary and local-apex consistency;

Challenge components, able to demote or block a candidate:

- neighboring-interference challenge;
- low-assessable-coverage challenge;
- selected boundary and local-apex inconsistency;

Positive support components, able to support `production_candidate` only when
emitted by a reviewed, named Tier 2 source and allowlisted by this contract:

- `validated_tier2_trace_evidence`, the initial pilot allowlist token;
- future targeted or ISTD-like positive-control context only after a reviewed
  contract extends the allowlist.

The gate should be conservative. A candidate needs positive support and must
survive challenge checks. If Tier 2 only restates owner-backfill provenance or
artifact-derived dependent context, the row must remain `keep_provisional`.
Arbitrary non-dependent tokens in `independent_tier2_support_components` do not
count as positive support unless they are allowlisted here and implemented in the
gate. Missing allowlisted Tier 2 evidence should produce `keep_provisional`, not
`production_candidate`, unless the row is part of an explicit selected-family
validation run where the missing evidence itself is the finding.

### Output Contract

The first implementation should write a sidecar, not mutate
`alignment_review.tsv` or `alignment_matrix.tsv`.

Recommended sidecar:

```text
alignment_production_candidate_gate.tsv
```

Minimum columns:

| Column | Meaning |
| --- | --- |
| `feature_family_id` | Stable row identifier. |
| `matrix_role` | Existing projected role before Tier 2. |
| `candidate_gate_status` | `production_candidate`, `keep_provisional`, `audit`, or `excluded`. |
| `recommended_action` | `track_candidate`, `keep_provisional`, `review`, or `exclude`. |
| `evidence_tier` | Highest evidence tier used; `2` only when allowlisted independent Tier 2 support is present. |
| `support_components` | Semicolon-separated allowlisted positive evidence components. |
| `dependent_context` | Semicolon-separated context that cannot justify `production_candidate` by itself. |
| `challenge_blockers` | Semicolon-separated blockers or empty. |
| `tier2_evidence_available` | `TRUE` when an allowlisted independent Tier 2 source contributes support. |
| `candidate_confidence` | `medium`, `review`, or `none`. |
| `source_review_artifact` | Path to the review TSV used. |
| `source_cell_artifact` | Path to the cells TSV used. |

The sidecar is a machine artifact. Human-facing summaries can rank or explain it
later, but the TSV must be complete enough for downstream automation.

### Candidate Gate Semantics

`production_candidate` requires:

- no structural blockers;
- Tier 1 supported rescue evidence;
- allowlisted independent Tier 2 evidence available from a named source;
- at least one allowlisted positive support component;
- no high neighboring interference;
- no low assessable coverage;
- no selected-boundary or local-apex inconsistency.

Rescued-cell RT coherence, rescued-cell scan-support distribution, and selected
boundary/local-apex consistency can help explain the row as dependent context,
but cannot satisfy the positive-support requirement.

`keep_provisional` means the row remains useful discovery evidence but does not
meet the stronger candidate gate.

`audit` means the row has conflicting, missing, or ambiguous evidence that a
machine consumer should not silently ignore.

`excluded` remains reserved for structural non-candidates such as rescue-only,
duplicate-only, zero-present, or consolidation-loser rows.

## Data Flow

```text
alignment_review.tsv
alignment_cells.tsv
        |
        v
Tier 0 / Tier 1 machine-decision projection
        |
        v
retention-candidate subset
        |
        v
Tier 2 selected evidence collection
        |
        v
alignment_production_candidate_gate.tsv
```

The immediate consumers are the selected Tier 2 pilot report and a future
promotion-contract author. The sidecar is not a downstream correction/statistics
input and must not be treated as quantitative matrix data.

## Error Handling

- Missing `alignment_review.tsv` or `alignment_cells.tsv` should fail with a
  clear missing-artifact message.
- Missing required columns should fail unless an explicit incomplete-summary
  mode is used.
- Missing Tier 2 evidence for an eligible row should emit
  `candidate_gate_status=keep_provisional` with a blocker, not silently promote.
- Stale or mismatched artifacts should be reported with source paths and row
  counts.
- Any selected-family or 85RAW run must keep timing heartbeat sidecars.

## Verification Strategy

### Unit / Contract Tests

- Projection tests for `provisional -> production_candidate` only when an
  allowlisted independent support token is present.
- Negative tests proving dependent-only and unknown support tokens do not
  promote.
- Negative tests for duplicate pressure, ambiguity, `review_only`,
  consolidation loser, low coverage, and neighboring interference.
- Sidecar schema tests for required columns and stable enum values.
- Writer tests proving `alignment_matrix.tsv` remains primary-only.

### 8RAW Gate

The first real-data gate should run 8RAW and assert:

- candidate subset count is recorded;
- retention-candidate count is greater than zero and less than or equal to 50;
- retention-candidate count is less than or equal to 5% of review rows;
- every `production_candidate` row comes from the Tier 2 eligible subset;
- no row enters `alignment_matrix.tsv` because of this gate;
- every non-candidate has a machine-readable blocker or missing-evidence reason.

### 85RAW Gate

Run 85RAW only after 8RAW is conclusive. The current 85RAW scale smoke has
already passed for the candidate-pool question: seven retention candidates out
of 21812 review rows.

The implemented sidecar gate should still run an 85RAW acceptance check and
assert:

- retention-candidate count is greater than zero and less than or equal to 100;
- retention-candidate count is less than or equal to 1% of review rows;
- retention-candidate count is not more than 10x the 8RAW count unless a
  validation note explains the new class distribution;
- primary matrix row count and schema remain stable unless a later promotion
  contract explicitly allows a delta;
- candidate statuses are explainable by allowlisted support components,
  dependent context, and blockers;
- timing heartbeat artifacts exist for the foreground run.

## Now / Later / Not In Scope

Now:

- Define the sidecar schema and candidate gate semantics.
- Implement selected Tier 2 evaluation for the retention-candidate subset.
- Verify with unit tests and existing or rerun 8RAW / 85RAW artifacts.

Later:

- Add a human-readable compact review index for candidate calibration.
- Write a separate promotion contract if `production_candidate` rows should ever
  enter the primary matrix.

Not in scope:

- Broad Tier 2 routing for all provisional rows.
- Primary matrix promotion.
- Workbook schema changes.
- ASLS or resolver behavior changes.

## Acceptance Criteria

- The candidate gate emits a deterministic sidecar for a fixed alignment run.
- The sidecar distinguishes `production_candidate`, `keep_provisional`, `audit`,
  and `excluded` without relying on manual review text.
- 8RAW and 85RAW candidate counts and source artifacts are recorded in
  validation notes.
- `alignment_matrix.tsv` remains primary-only.
- Missing or skipped expensive evidence is explicit and does not imply false
  negative support.
- Artifact-derived dependent context alone keeps current 8RAW/85RAW
  `production_candidate_count=0`.

## Critical Assumptions

Strongest assumption: the small 8RAW and 85RAW retention-candidate subsets are
enough to justify a selective Tier 2 experiment. They justify a bounded sidecar
pilot, not a product role or matrix promotion.

Stale-artifact risk: the current 8RAW run was generated on the active branch
with local uncommitted tiered-backfill changes. Any future implementation plan
should rerun or hash-pin the exact artifacts it relies on.

Cheaper oracle: before launching any further RAW run, the current 8RAW and 85RAW
`alignment_review.tsv` / `alignment_cells.tsv` artifacts should answer whether
the gate remains selective and deterministic.

Invalidation condition: if no reviewed named Tier 2 source can add allowlisted
independent support beyond owner-backfill provenance and dependent context, the
`production_candidate` state is not justified. In that case the design should
stop at `keep_provisional` plus ranked discovery review.

Kill rule: if implemented Tier 2 sidecars on 8RAW and 85RAW show no allowlisted
independent support source, or if candidate rows remain concentrated in one
artifact class with no additional challenge resolution, retire the
`production_candidate` status until a separate promotion contract exists and
keep only `keep_provisional` / `audit` diagnostics.

## Stop Rules

- Stop before implementation if the sidecar schema would require changing
  `alignment_matrix.tsv`.
- Stop before additional 85RAW reruns if current 8RAW / 85RAW artifacts already
  answer the scale question.
- Stop before promotion if no separate production promotion contract exists.
- Stop if candidate evidence cannot be represented as machine-readable support
  components and blockers.
