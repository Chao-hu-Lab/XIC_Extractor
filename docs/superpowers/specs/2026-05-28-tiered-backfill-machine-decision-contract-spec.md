# Tiered Backfill Machine Decision Contract Spec

## Status

`accepted_next_pr_scope`

This spec captures the design conclusion from the product-priority reset
discussion. It is not an implementation plan and does not change production
behavior by itself.

This revision records the project decision that the next PR should be the
tiered backfill machine-decision PR. The critical-review findings are accepted
as scope guards, not as a reason to defer the work: the first implementation
must focus on one-detected-seed provisional retention plus a pure projection
helper, while keeping Tier 2 routing, new sidecars, and broad pipeline splits
out of scope.

This work is sequenced before ASLS / boundary behavior so the next quantitative
behavior PR does not have to reinterpret row roles, provisional retention, or
primary promotion while it is also changing area/baseline behavior. ASLS remains
high value and is deferred, not cancelled.

## Problem

The current alignment pipeline has a useful evidence chain, but the concepts are
still too tightly coupled:

- owner backfill as evidence collection;
- primary matrix promotion as downstream quantitative delivery;
- audit / review artifacts as human or agent inspection surfaces.

This coupling creates two opposite failure modes:

- under-retention: a one-detected-seed feature may be treated as not worth
  further evidence because it is not primary-matrix-ready;
- over-computation: every possible evidence source may be computed before the
  system knows whether that evidence can change the next decision.

The desired product direction is not to produce more human-readable diagnostic
tables. The desired direction is a compact machine decision contract that can be
tested, challenged, and consumed by downstream correction / statistics tools.

## Framing Decision

The framing decision is now:

1. **Sequencing:** the next PR is the tiered backfill machine-decision PR. ASLS /
   boundary behavior follows after this contract unless a new blocker changes
   priority.
2. **First-PR scope:** the PR includes one-detected-seed provisional retention,
   deterministic projection from existing review/cell fields, tests, and docs.
   It does not include Tier 2 routing, a new sidecar, broad skipped-evidence
   ledger work, or a three-pipeline rewrite.
3. **Consumer:** normal downstream correction/statistics continue to consume
   `alignment_matrix.tsv`, which remains primary-only and therefore ignores
   provisional rows by construction. The immediate named consumers of
   `matrix_role=provisional` / `recommended_action=keep_provisional` are the
   alignment review surface and machine gate diagnostics that decide whether a
   row should be kept for research/review, excluded, or promoted later under a
   separate contract. The next PR must test this default filter.

## Product Principle

Evidence completeness means enough evidence to make the next decision, not
maximum evidence collection.

Backfill must be separated into three decisions:

1. **Evidence collection:** should this cell or row receive additional MS1
   evidence?
2. **Retention:** should this row remain available as a provisional research
   feature?
3. **Promotion:** should this row enter the primary quantitative matrix consumed
   by downstream tools?

These decisions are related but not equivalent.

## Matrix Roles

The long-term machine contract should classify rows into one of these roles:

| Role | Meaning | Downstream action |
| --- | --- | --- |
| `primary` | production quantitative row | use in correction / statistics |
| `provisional` | retained research feature with incomplete production authority | keep, index, optionally revisit |
| `audit` | diagnostic / review-only row | exclude from normal downstream statistics |
| `excluded` | invalid, duplicate loser, or unsupported row | ignore except for traceability |

Current fields such as `include_in_primary_matrix`, `identity_decision`,
`identity_confidence`, `identity_reason`, and `row_flags` may continue to express
this contract until a versioned sidecar is justified.

The next PR should first define a deterministic projection from existing fields
instead of creating a new schema by default:

- `include_in_primary_matrix=TRUE` -> `matrix_role=primary`,
  `recommended_action=use`;
- `identity_decision=provisional_discovery` -> `matrix_role=provisional`,
  `recommended_action=keep_provisional` unless an explicit structural blocker
  requires review;
- `identity_decision=audit_family` with duplicate, ambiguous, rescue-only, zero
  present, review-only, or consolidation-loser reasons -> `matrix_role=audit` or
  `excluded`, with `recommended_action=review` or `exclude`;
- if existing fields cannot project a row deterministically, stop at
  `diagnostic_only` and record the ambiguity rather than expanding Tier 2
  evidence to compensate.

## One-Detected-Seed Rule

A one-detected-seed row is not automatically low value.

Default behavior should be:

- run cheap eligibility checks;
- allow backfill evidence collection when the feature is not duplicate,
  review-only, or structurally invalid;
- retain the row as provisional if backfill finds coherent MS1 evidence;
- do not promote it to the primary matrix from owner backfill alone.

For normal `production-equivalent` runs, this does not mean every one-detected
row should enter expensive evidence collection. A structurally eligible
one-detected row should default to:

```text
candidate_for_provisional_retention = true
candidate_for_primary_gate = false
skip_expensive_evidence = true
matrix_role = provisional
recommended_action = keep_provisional
```

Tier 2 evidence for one-detected rows requires an explicit scope such as
`provisional-candidates`, `selected-families`, or a named validation gate. If
expensive evidence was intentionally skipped, the row should not be called
unsupported solely because the skipped evidence is absent.

Promotion of a one-detected-seed row requires a separate future contract with
stronger independent evidence. Examples include repeated biological support,
strong seed-aware shape evidence, or a method-specific rule approved as a
production behavior change. Until that contract exists, one detected seed plus
many rescued cells is a retained provisional row, not a production quantitative
row.

## Tiered Decision Pipeline

### Tier 0: Cheap Row Routing

Inputs:

- detected seed count;
- neutral-loss tag / feature class;
- review-only and consolidation-loser state;
- duplicate / ambiguous ownership pressure;
- sample coverage;
- current row role and prior reason flags.

Output:

- `candidate_for_primary_gate`;
- `candidate_for_provisional_retention`;
- `skip_expensive_evidence`;
- `exclude`.

Tier 0 must not open RAW files or recompute XICs.

### Tier 1: Cheap Cell Evidence

Inputs:

- `status`;
- area / height / complete peak;
- apex RT and `rt_delta_sec`;
- scan support score;
- trace quality as provenance, not quality proof;
- existing selected-boundary / region fields when already emitted.

Output:

- `ms1_cell_supported`;
- `rt_coherent`;
- `low_ms1_assessable_coverage`;
- `neighbor_interference_blocked`;
- `incomplete_peak`;
- `needs_tier2`.

Tier 1 uses already available alignment cells and should be the main production
gate for normal runs.

### Tier 2: Expensive Evidence

Inputs:

- seed-aware shape overlay;
- family MS1 overlay;
- re-extracted XIC windows;
- low-MS1-coverage review tools;
- targeted benchmark context when explicitly allowed by contract.

Tier 2 runs only when Tier 0 / Tier 1 cannot close a high-value decision or when
the row is part of a named validation gate. It must not be the default path for
every provisional feature.

### Tier 3: Human Review

Human review is a calibration and challenge surface, not the normal delivery
surface. It should receive a compact review index, not exhaustive TSV dumps.

## Next PR Scope

The next implementation should be intentionally narrow:

1. Add or formalize a one-detected-seed retention path only when the row is not
   duplicate, review-only, rescue-only, structurally invalid, or blocked by low
   assessable coverage / neighboring interference.
2. Add a pure projection helper that maps existing review/cell fields into a
   machine decision vector.
3. Keep `alignment_matrix.tsv` unchanged and primary-only.
4. Do not add a new sidecar unless existing fields cannot express the projection
   deterministically.
5. Do not add Tier 2 evidence routing, `provisional-candidates` execution scope,
   or broad skipped-evidence ledger work in the first PR.

This means the next PR is not "the whole tiered framework." It is the smallest
behavior / contract move needed to test whether provisional retention has value.

## Machine Decision Vector

The target contract is a compact vector per row:

```text
feature_family_id
matrix_role = primary | provisional | audit | excluded
evidence_tier = 0 | 1 | 2 | 3
support_reasons = detected_seed;ms1_backfill_supported;rt_coherent
blockers = single_detected_seed;insufficient_identity_support
confidence = high | medium | review | none
recommended_action = use | keep_provisional | exclude | review
```

This vector may initially be projected from existing TSV columns. A new TSV
schema or sidecar should be added only if existing columns cannot express the
contract without ambiguity.

The first implementation should provide a pure projection helper that consumes
an `alignment_review.tsv` row plus optional `alignment_cells.tsv` rows and
returns the vector above. The helper belongs in the alignment decision layer, not
only in a diagnostic writer. Diagnostic tools may load and display the vector,
but they must not re-decide row roles independently.

Most fields in this vector are projections of existing Phase 1b output:
`primary` projects from `include_in_primary_matrix=TRUE`, support/blocker
reasons project from `identity_reason`, and confidence projects from
`identity_confidence` plus row flags. The only materially new state is
`recommended_action=keep_provisional` for rows that should remain available for
research or later review while staying out of the primary quantitative matrix.
That new state requires the consumer decision above.

## Computation Budget Rules

- Do not compute expensive evidence when Tier 0 proves the row cannot affect the
  next decision.
- Do not write large human reports unless the active task explicitly requires
  human inspection.
- Provisional retention should be compact. Keeping a row does not imply keeping
  every diagnostic trace by default.
- RAW-backed evidence should be routed by explicit scope:
  `production-equivalent`, `provisional-candidates`, or `selected-families`.
- In `production-equivalent` runs, one-detected provisional rows must not trigger
  Tier 2 or full-audit evidence by default.
- A skipped-evidence ledger is a later option. If added, it must be a versioned
  sidecar with schema/header tests and a named gate consumer; it is not required
  for the first PR.

## Feasibility Assessment

### Low-Cost Feasible Next

These changes are feasible in the current architecture with low to medium risk:

- document the split between backfill evidence collection, retention, and
  primary promotion;
- keep one-detected-seed rows out of primary promotion by default while
  retaining them as provisional;
- make `trace_quality=owner_backfill` provenance-only and require independent
  signals such as scan support for support claims;
- classify existing rows into compact machine states using existing
  `alignment_review.tsv` and `alignment_cells.tsv`;
- add a pure machine-decision projection helper;
- add tests around one-detected-seed retention versus primary promotion and
  `keep_provisional` output.

Expected blast radius: focused alignment decision policy, diagnostics, tests,
and docs.

### Medium-Cost Feasible Later

These changes are feasible but should be a separate PR:

- add an explicit `matrix_role` / `recommended_action` sidecar if existing TSV
  columns remain ambiguous;
- add a `provisional-candidates` evidence scope distinct from
  `production-equivalent` and `full-audit`;
- route one-detected-seed rows into a compact provisional evidence queue without
  generating large human reports;
- make Tier 2 diagnostics consume the machine decision vector instead of
  rediscovering candidate sets independently.

Expected blast radius: alignment output contract, diagnostic loaders/writers,
validation notes, and possible downstream consumers.

### High-Cost / Not Recommended Now

These changes are possible but should not be part of the current PR:

- rewriting the alignment pipeline into a full three-path architecture;
- changing primary `alignment_matrix.tsv` schema;
- making every provisional row run seed-aware overlays by default;
- replacing current owner-backfill selection with an ML/DL model;
- promoting one-detected-seed rows broadly into primary quantitative output.

These would increase runtime and validation cost before the machine contract is
stable.

## Acceptance Criteria For A Future Implementation

A future implementation of this spec is acceptable only if:

- one-detected-seed rows can be retained as provisional without entering primary
  by default;
- primary rows remain explainable by machine-readable reasons;
- skipped expensive evidence is recorded when it matters for traceability;
- RAW validation can still use `validation-minimal` without producing XLSX /
  HTML review artifacts;
- projection-only implementations may validate from existing hash-pinned 8RAW /
  85RAW artifacts without rerunning RAW;
- fresh 8RAW / 85RAW validation is required only when the implementation changes
  RAW-backed evidence execution, final matrix inclusion, or Tier 2 evidence
  scope;
- `recommended_action=keep_provisional` rows carry explicit blockers or missing
  evidence reasons. They must not be emitted with only a generic
  `provisional_discovery` label.

Minimum tests for the first contract PR:

- primary row -> `matrix_role=primary`, `recommended_action=use`;
- one detected seed plus supported rescue evidence -> `matrix_role=provisional`,
  `recommended_action=keep_provisional`, and `include_in_primary_matrix=FALSE`;
- rescue-only, duplicate, ambiguous, zero-present, review-only, or
  consolidation-loser rows map to `audit` or `excluded` with explicit blockers;
- diagnostic projection includes one-detected provisional rows that are not part
  of the current single-dR gate report scope;
- `alignment_matrix.tsv` remains a primary-only downstream quantitative surface.

## Critical Self-Review

Strongest assumption: provisional retention is valuable only if downstream tools
can consume or ignore it deterministically. If provisional rows become an
unbounded parking lot with no action, this design fails.

Main risk: adding a new decision vector too early could duplicate existing
`alignment_review.tsv` columns and create schema drift. The first implementation
should project from existing fields unless ambiguity blocks machine use. The
implementation must keep the actual behavior delta visible: one-detected-seed
rows may be retained as provisional, but remain excluded from the primary
quantitative matrix.

Cheapest falsification test: run 8RAW with the current production-equivalent
path, classify one-detected-seed rows into primary / provisional / audit using
existing artifacts, and verify that the proposed role split changes decisions
without requiring new expensive evidence.

Exit rule: if existing artifacts cannot produce a deterministic role /
recommended-action projection, the next PR stops at `diagnostic_only` with a
recorded blocker. It must not silently widen to Tier 2 evidence, full-audit
reports, or a new sidecar just to make the ambiguity disappear.

## Recommended Next Step

Start the next PR from this spec. Keep the implementation narrow and complete in
that PR:

- primary promotion remains conservative;
- one-detected-seed rows are retained as provisional when supported;
- expensive evidence is routed only when it can close a named decision;
- machine-readable reasons are the delivery surface, not human diagnostic
  reports.

`ASLS / linear-edge quantitative behavior and boundary guard` remains a high
value product behavior move. It is deferred until after the tiered backfill
machine-decision PR so the quantitative PR can focus on area/baseline and
boundary behavior instead of also defining row-role semantics.
