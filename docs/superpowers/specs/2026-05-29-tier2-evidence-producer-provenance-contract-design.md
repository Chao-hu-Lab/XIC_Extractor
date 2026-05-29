# Tier 2 Evidence Producer / Provenance Contract Design

Date: 2026-05-29

Validation label for this design: `diagnostic_only`.

## Decision

Implement the next phase as a `diagnostic_only` Tier 2 evidence producer and
provenance contract, not as product promotion.

The first producer is a RAW trace re-read producer for retained provisional
backfill candidates. It emits a sidecar, and the provisional candidate gate may
join that sidecar to derive `validated_tier2_trace_evidence`. The producer does
not mutate `alignment_review.tsv`, `alignment_cells.tsv`, `alignment_matrix.tsv`,
or workbook outputs.

Targeted, ISTD, and evidence-spine cross-report evidence are allowed in v0 only
as calibration context or challenge evidence. They cannot directly emit the
positive support token.

## Context

The current provisional backfill candidate gate already separates retained
provisional rows from the primary matrix contract. Existing 8RAW and 85RAW
sidecars show seven retained provisional backfill candidates and zero
`production_candidate` rows because no independent Tier 2 support source exists.

The current allowlist token is:

```text
validated_tier2_trace_evidence
```

That token is intentionally not enough by itself. This design defines who may
produce it and what provenance must exist before the gate may treat it as
positive support.

The initial v0 producer and criteria identifiers are:

```text
producer_name=raw_trace_reread_tier2
producer_version=raw_trace_reread_tier2_v0
criteria_version=tier2_trace_identity_rescued_coherence_v0
```

## Goals

- Establish a named Tier 2 evidence producer that can evaluate retained
  provisional backfill rows without changing primary matrix behavior.
- Require RAW trace re-read evidence plus rescued-cell coherence for positive
  support.
- Make every positive support decision traceable to row-level sidecar evidence,
  artifact hashes, producer version, and criteria version.
- Keep the candidate gate as a consumer of sidecar evidence, not a RAW trace
  calculator.
- Preserve `alignment_matrix.tsv` as primary-only until a separate promotion
  contract exists.

## Non-Goals

- Primary matrix promotion.
- Workbook schema changes.
- Broad Tier 2 evaluation for every provisional discovery row.
- Treating targeted, ISTD, or evidence-spine agreement as direct positive
  support in v0.
- Resolver, ASLS, or extraction behavior changes.
- Human EIC review import as the first positive support producer.

## Selected Approach

Use a sidecar-join architecture:

```text
alignment_review.tsv + alignment_cells.tsv + RAW/manifest
        |
        v
RAW trace re-read Tier 2 producer
        |
        v
alignment_tier2_trace_evidence.tsv/json
        |
        v
provisional_backfill_candidate_gate.py --tier2-trace-evidence-tsv ...
        |
        v
alignment_production_candidate_gate.tsv/json
```

The producer owns trace re-read and evidence classification. The candidate gate
owns provenance validation and final sidecar status projection.

## Producer Scope

The v0 producer evaluates only retained provisional backfill candidates:

- projected matrix role is provisional;
- `identity_decision=provisional_discovery`;
- `row_flags` include `single_detected_seed`;
- `row_flags` include `provisional_retention_candidate`;
- structural exclude flags are absent.

The producer may skip non-eligible rows or emit them as `inconclusive`, but it
must not broaden evaluation to all provisional discovery rows by default.

## Evidence Requirements

Positive support requires both classes of evidence:

1. RAW trace identity evidence
   - re-read trace exists for the candidate family window;
   - apex is coherent with the candidate family or seed context;
   - scan support is sufficient;
   - selected boundary is not overwide or incoherent;
   - local trace is not dominated by neighboring interference.

2. Rescued-cell coherence
   - rescued cells are re-evaluated against the retained family context;
   - supported rescued cells have a coherent apex distribution;
   - supported rescued cells have compatible boundaries;
   - scan support distribution is sufficient;
   - incoherent rescued cells are reported as challenge evidence.

Owner-backfill provenance, rescued status, family MS1 context, scan-support
fields already present in alignment artifacts, and artifact-derived RT
coherence remain dependent context unless the RAW re-read producer recomputes
and records them under this contract.

## Tier 2 Sidecar Contract

The producer writes:

```text
alignment_tier2_trace_evidence.tsv
alignment_tier2_trace_evidence.json
```

The TSV is row-level. One row corresponds to one `feature_family_id` in the
candidate subset.

### Required TSV Columns

Identity and join columns:

| Column | Meaning |
|---|---|
| `feature_family_id` | Alignment feature family id. |
| `evidence_status` | `validated`, `not_supported`, `blocked`, or `inconclusive`. |
| `support_component` | `validated_tier2_trace_evidence` only when validated. |
| `criteria_version` | Criteria identifier used for this row. |
| `producer_version` | Producer implementation identifier. |

RAW trace re-read columns:

| Column | Meaning |
|---|---|
| `raw_trace_reread_status` | `pass`, `fail`, `blocked`, or `inconclusive`. |
| `seed_apex_rt` | Seed apex RT used as reference, in minutes. |
| `tier2_apex_rt` | Re-read Tier 2 apex RT, in minutes. |
| `apex_delta_sec` | Absolute apex delta, in seconds. |
| `scan_support_score` | Recomputed support score for the re-read trace. |
| `trace_scan_count` | Number of scans in the assessed trace region. |
| `boundary_start_rt` | Re-read boundary start RT, in minutes. |
| `boundary_end_rt` | Re-read boundary end RT, in minutes. |
| `boundary_width_sec` | Re-read boundary width, in seconds. |

Rescued-cell coherence columns:

| Column | Meaning |
|---|---|
| `rescued_cell_count_checked` | Rescued cells assessed by the producer. |
| `rescued_cell_count_supported` | Rescued cells passing producer criteria. |
| `rescued_apex_rt_span_sec` | Apex RT span among supported rescued cells. |
| `rescued_boundary_overlap_min` | Minimum supported boundary overlap. |
| `coherence_status` | `pass`, `fail`, `blocked`, or `inconclusive`. |

Challenge and provenance columns:

| Column | Meaning |
|---|---|
| `challenge_blockers` | Semicolon-separated hard or soft blockers. |
| `dependent_context` | Semicolon-separated context that cannot promote alone. |
| `source_alignment_review_sha256` | SHA256 of the review artifact used. |
| `source_alignment_cells_sha256` | SHA256 of the cells artifact used. |
| `source_raw_manifest_sha256` | SHA256 of the RAW input manifest or equivalent source inventory. |
| `producer_command` | Command shape sufficient to reproduce the sidecar. |
| `generated_at_utc` | UTC timestamp for sidecar generation. |

### JSON Summary

The JSON summary must include:

- `readiness_label=diagnostic_only`;
- source artifact paths and hashes;
- producer version;
- criteria version;
- rows evaluated;
- counts by `evidence_status`;
- count of rows with `support_component=validated_tier2_trace_evidence`;
- `production_ready=false`;
- `matrix_contract_changed=false`.

## Candidate Gate Integration

`tools/diagnostics/provisional_backfill_candidate_gate.py` may accept:

```text
--tier2-trace-evidence-tsv <path>
```

When the argument is absent, behavior remains unchanged. Existing artifact-only
8RAW and 85RAW runs should continue to produce zero `production_candidate` rows
unless a valid sidecar is supplied.

When the sidecar is supplied, the gate:

1. Loads sidecar rows by `feature_family_id`.
2. Verifies source hashes match the current `alignment_review.tsv` and
   `alignment_cells.tsv`.
3. Verifies `criteria_version` is allowlisted.
4. Verifies `producer_version` is non-empty and recognized by the contract.
5. Accepts `support_component=validated_tier2_trace_evidence` only when
   `evidence_status=validated`.
6. Treats all other sidecar statuses as blockers, context, or inconclusive
   evidence.

The gate does not re-read RAW data and does not recompute Tier 2 trace metrics.

After this contract is implemented, review-row
`independent_tier2_support_components` must not be accepted as positive support.
The support token is derived from the sidecar join only. Tests that currently
inject the token directly into review rows should move to Tier 2 sidecar
fixtures.

## Positive Support Rule

The gate may emit `support_components=validated_tier2_trace_evidence` only when
all of these are true:

- the row is a retained provisional backfill candidate;
- a sidecar row exists for the same `feature_family_id`;
- sidecar source hashes match the current alignment artifacts;
- sidecar `criteria_version` is allowlisted;
- sidecar `producer_version` is recognized;
- `evidence_status=validated`;
- `support_component=validated_tier2_trace_evidence`;
- RAW trace re-read status is passing;
- rescued-cell coherence status is passing;
- no hard challenge blocker is present.

If any provenance check fails, the gate must not use the support token. It
should add a machine-readable blocker such as `missing_valid_tier2_provenance`
or `stale_tier2_trace_evidence`.

## Status Semantics

Producer statuses:

| Status | Meaning |
|---|---|
| `validated` | RAW re-read and rescued-cell coherence both support the row. |
| `not_supported` | RAW was assessable and did not support the row. |
| `blocked` | A hard challenge prevents positive support. |
| `inconclusive` | Required inputs or assessable evidence were unavailable. |

Gate behavior:

- `validated` can support `production_candidate` sidecar status if no other gate
  blockers exist.
- `not_supported` keeps the row provisional or audit-labeled with an explicit
  blocker.
- `blocked` maps to `audit` unless the row is structurally excluded.
- `inconclusive` keeps the row provisional or audit-labeled; it is not negative
  evidence by itself.

## Targeted / ISTD / Evidence-Spine Role

Targeted, ISTD, and evidence-spine diagnostics may be joined as:

- `dependent_context`;
- calibration context;
- hard challenge blockers when a later reviewed contract defines such blockers.

They cannot directly produce `validated_tier2_trace_evidence` in v0. This keeps
v0 focused on a general RAW-derived producer and avoids tying candidate support
to uneven targeted coverage.

## Failure Modes

- Missing RAW or unreadable RAW: emit `inconclusive`.
- Stale sidecar hash: gate ignores positive support and emits
  `stale_tier2_trace_evidence`.
- Missing sidecar row for an eligible candidate: gate emits
  `missing_positive_tier2_support`.
- Trace present but low scan support: emit `not_supported` or `blocked`
  according to criteria severity.
- Rescued-cell apex span too wide: emit `blocked`.
- Boundary incoherence: emit `blocked`.
- Neighboring interference: emit `blocked` when criteria classify it as hard;
  otherwise emit dependent context or soft challenge.
- Targeted or ISTD disagreement: emit challenge context only in v0 unless a
  later contract upgrades it to a hard blocker.

## Versioning And Provenance

The producer must define stable strings for:

- producer name;
- producer version;
- criteria version;
- support component vocabulary.

The candidate gate must allowlist criteria versions before accepting positive
support. Unknown criteria versions are treated as invalid provenance.

The initial allowlist contains only:

```text
tier2_trace_identity_rescued_coherence_v0
```

The sidecar must record artifact hashes for the exact alignment artifacts used
by the producer. The gate must compare those hashes against the current inputs
before accepting support.

## Validation Strategy

Unit tests:

- valid sidecar row can produce `production_candidate` sidecar status;
- absent sidecar preserves current behavior;
- stale hash blocks support;
- unknown criteria version blocks support;
- `inconclusive` sidecar row does not promote;
- targeted-only context does not promote;
- hard challenge blocker prevents positive support;
- direct review-row `independent_tier2_support_components` tokens do not
  promote without a valid Tier 2 sidecar row.

CLI tests:

- candidate gate accepts optional `--tier2-trace-evidence-tsv`;
- sidecar provenance failures are machine-readable;
- output remains `diagnostic_only`;
- `alignment_matrix.tsv` content is unchanged.

Real-data pilot:

- run the producer only on the seven retained candidates in the current 8RAW and
  85RAW retained-provisional artifacts;
- re-run candidate gate with the Tier 2 sidecar;
- record counts for `validated`, `not_supported`, `blocked`, and
  `inconclusive`;
- treat zero validated rows as a valid diagnostic outcome if blockers are
  explainable and provenance is complete.

## Acceptance Criteria

- The contract defines one authorized v0 positive support producer.
- Positive support requires RAW trace identity plus rescued-cell coherence.
- The support token is derived from a sidecar join, not copied from
  `alignment_review.tsv`.
- All positive support has source artifact hashes, producer version, criteria
  version, and row-level evidence.
- Missing, stale, or inconclusive Tier 2 evidence cannot promote a row.
- Targeted, ISTD, and evidence-spine evidence cannot directly promote a row in
  v0.
- Existing no-sidecar behavior remains compatible and conservative.
- The primary matrix contract remains unchanged.

## Exit Rule

This phase exits in one of three states:

- `shadow_ready`: producer sidecars are reproducible on 8RAW and 85RAW, and gate
  integration is deterministic, but product promotion remains out of scope.
- `kill`: RAW trace re-read cannot produce independent evidence beyond
  owner-backfill context or produces mostly unresolvable inconclusive rows.
- `externalize`: RAW trace re-read is insufficient, and the next useful oracle is
  targeted, ISTD, or human-reviewed EIC evidence under a separate producer
  contract.

It does not exit as `production_ready`. Primary matrix promotion requires a
separate promotion contract.
