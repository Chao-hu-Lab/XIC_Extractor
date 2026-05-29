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
   - apex delta satisfies the v0 numeric threshold;
   - scan support satisfies the v0 numeric threshold;
   - selected boundary width satisfies the v0 numeric threshold;
   - neighboring interference satisfies the v0 numeric threshold.

2. Rescued-cell coherence
   - rescued cells are re-evaluated against the retained family context;
   - supported rescued-cell fraction satisfies the v0 numeric threshold;
   - rescued-cell apex span satisfies the v0 numeric threshold;
   - rescued-cell boundary overlap satisfies the v0 numeric threshold;
   - failing rescued-cell coherence metrics are reported as challenge evidence.

Owner-backfill provenance, rescued status, family MS1 context, scan-support
fields already present in alignment artifacts, and artifact-derived RT
coherence remain dependent context unless the RAW re-read producer recomputes
and records them under this contract.

### V0 Numeric Criteria

The initial criteria version is
`tier2_trace_identity_rescued_coherence_v0`. These thresholds are intentionally
conservative. They are enough to make the pilot mechanically testable; they do
not define a production promotion policy.

RAW trace identity passes only when all of these are true:

| Metric | V0 threshold |
|---|---|
| `raw_trace_reread_status` | `pass` |
| `trace_scan_count` | `>= 5` scans in the assessed trace region |
| `scan_support_score` | `>= 0.50` |
| `apex_delta_sec` | `<= 30.0` seconds from the seed or family reference apex |
| `boundary_width_sec` | `> 0.0` and `<= 180.0` seconds |
| `neighbor_interference_ratio` | `<= 0.33`, or blank only when no neighboring trace was assessable |

Rescued-cell coherence passes only when all of these are true:

| Metric | V0 threshold |
|---|---|
| `rescued_cell_count_checked` | `>= 1` |
| `rescued_cell_count_supported` | `>= 1` |
| supported rescued-cell fraction | `rescued_cell_count_supported / rescued_cell_count_checked >= 0.50` |
| `rescued_apex_rt_span_sec` | `<= 21.0` seconds |
| `rescued_boundary_overlap_min` | `>= 0.50` |
| `coherence_status` | `pass` |

The producer must use explicit denominators. If a denominator is unavailable,
the row is `inconclusive`, not `validated` and not negative evidence.

### V0 Status Mapping

The producer status is mechanically derived:

| Condition | `evidence_status` | Required blocker or context |
|---|---|---|
| RAW file, DLL/runtime, or candidate window unavailable | `inconclusive` | `raw_unavailable`, `runtime_unavailable`, or `candidate_window_unavailable` |
| Required denominator or metric unavailable | `inconclusive` | `metric_unavailable` |
| RAW trace identity passes and rescued-cell coherence passes | `validated` | no hard blocker |
| Trace is assessable but `scan_support_score < 0.20` | `blocked` | `low_scan_support` |
| Trace is assessable and `0.20 <= scan_support_score < 0.50` | `not_supported` | `weak_scan_support` |
| `apex_delta_sec > 30.0` | `blocked` | `apex_delta_exceeds_v0_threshold` |
| `boundary_width_sec <= 0.0` or `boundary_width_sec > 180.0` | `blocked` | `boundary_width_out_of_range` |
| `neighbor_interference_ratio > 0.33` | `blocked` | `neighbor_interference` |
| rescued-cell supported fraction `< 0.50` | `blocked` | `rescued_cell_support_low` |
| `rescued_apex_rt_span_sec > 21.0` | `blocked` | `rescued_apex_span_wide` |
| `rescued_boundary_overlap_min < 0.50` | `blocked` | `rescued_boundary_overlap_low` |

`not_supported` means the trace was assessable and failed a soft support
threshold. `blocked` means the trace or rescued-cell evidence has a hard
contradiction. `inconclusive` means the producer could not assess the row.

### Hard Blocker Vocabulary

V0 hard blockers are:

```text
apex_delta_exceeds_v0_threshold
boundary_width_out_of_range
low_scan_support
neighbor_interference
rescued_apex_span_wide
rescued_boundary_overlap_low
rescued_cell_support_low
stale_tier2_trace_evidence
missing_valid_tier2_provenance
criteria_version_not_allowlisted
producer_version_not_recognized
source_hash_mismatch
raw_manifest_hash_mismatch
candidate_subset_hash_mismatch
```

Missing metrics and missing RAW inputs are not negative evidence. They emit
`inconclusive` with explicit blockers such as `raw_unavailable`,
`runtime_unavailable`, `candidate_window_unavailable`, or `metric_unavailable`.

## Tier 2 Sidecar Contract

The producer writes:

```text
alignment_tier2_trace_evidence.tsv
alignment_tier2_trace_evidence.json
alignment_tier2_raw_manifest.tsv
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
| `neighbor_interference_ratio` | Neighboring-trace height or area ratio used by v0 interference criteria. |

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
| `source_raw_manifest_sha256` | SHA256 of `alignment_tier2_raw_manifest.tsv`. |
| `source_candidate_subset_sha256` | SHA256 of the normalized retained-candidate subset evaluated by the producer. |
| `source_candidate_subset_count` | Number of retained candidates in the producer subset. |
| `source_expected_sample_count` | Expected sample count for the validation tier, such as `8` or `85`. |
| `raw_reader_runtime` | Runtime identifier used to read RAW data. |
| `python_executable` | Python executable used for the RAW producer. |
| `dll_dir` | Thermo DLL directory used by the RAW producer. |
| `producer_command` | Command shape sufficient to reproduce the sidecar. |
| `generated_at_utc` | UTC timestamp for sidecar generation. |

### RAW Manifest Contract

`alignment_tier2_raw_manifest.tsv` records the RAW inventory used by the
producer. Its normalized rows are hashed to produce
`source_raw_manifest_sha256`.

Required columns:

| Column | Meaning |
|---|---|
| `sample_stem` | Sample stem used by `alignment_cells.tsv`. |
| `raw_file_path` | RAW path used by the producer. |
| `raw_file_size_bytes` | File size observed before producer launch. |
| `raw_file_mtime_utc` | File modification timestamp observed before producer launch. |
| `raw_reader_runtime` | RAW reader runtime identifier. |
| `python_executable` | Python executable used for the run. |
| `dll_dir` | Thermo DLL directory. |

The manifest hash is not a cryptographic hash of large RAW file contents. It is
a freshness and identity guard for this diagnostic pilot. If RAW files move,
change size, change timestamp, or run under a different RAW runtime, the
producer must emit a new manifest and sidecar.

### JSON Summary

The JSON summary must include:

- `readiness_label=diagnostic_only`;
- source artifact paths and hashes;
- raw manifest path and hash;
- candidate subset hash, count, and expected sample count;
- producer version;
- criteria version;
- rows evaluated;
- counts by `evidence_status`;
- count of rows with `support_component=validated_tier2_trace_evidence`;
- `production_ready=false`;
- `matrix_contract_changed=false`.

## Candidate Gate Integration

`tools/diagnostics/provisional_backfill_candidate_gate.py` must accept:

```text
--tier2-trace-evidence-tsv <path>
--tier2-raw-manifest-tsv <path>
```

When both Tier 2 arguments are absent, behavior remains unchanged. Existing
artifact-only 8RAW and 85RAW runs should continue to produce zero
`production_candidate` rows unless a valid sidecar and RAW manifest are supplied.

When the sidecar is supplied, the gate:

1. Loads sidecar rows by `feature_family_id`.
2. Verifies source hashes match the current `alignment_review.tsv` and
   `alignment_cells.tsv`.
3. Verifies the supplied RAW manifest hash matches
   `source_raw_manifest_sha256`.
4. Verifies the candidate subset hash and count match the current retained
   candidate subset.
5. Verifies `criteria_version` is allowlisted.
6. Verifies `producer_version` is non-empty and recognized by the contract.
7. Accepts `support_component=validated_tier2_trace_evidence` only when
   `evidence_status=validated`.
8. Treats all other sidecar statuses as blockers, context, or inconclusive
   evidence.

The gate does not re-read RAW data and does not recompute Tier 2 trace metrics.

After this contract is implemented, review-row
`independent_tier2_support_components` must not be accepted as positive support.
The support token is derived from the sidecar join only. Tests that currently
inject the token directly into review rows should move to Tier 2 sidecar
fixtures.

This is the first implementation checkpoint. Before a RAW producer can be
treated as an acceptance gate, the existing direct review-row token path in
`xic_extractor/alignment/production_candidate_gate.py` must be removed,
disabled, or converted to dependent context. A regression test must prove that
`independent_tier2_support_components=validated_tier2_trace_evidence` in
`alignment_review.tsv` cannot promote a row without a valid Tier 2 sidecar row.

## Positive Support Rule

The gate may emit `support_components=validated_tier2_trace_evidence` only when
all of these are true:

- the row is a retained provisional backfill candidate;
- a sidecar row exists for the same `feature_family_id`;
- sidecar source hashes match the current alignment artifacts;
- the supplied RAW manifest hash matches the sidecar provenance;
- candidate subset hash and count match the current retained-candidate subset;
- sidecar `criteria_version` is allowlisted;
- sidecar `producer_version` is recognized;
- `evidence_status=validated`;
- `support_component=validated_tier2_trace_evidence`;
- RAW trace re-read status is `pass`;
- rescued-cell coherence status is `pass`;
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

## RAW Producer Preflight

The implementation plan must use the repo RAW runner rules from
`docs/agent-parameter-settings.md`. The initial command shape must use
`.venv\Scripts\python.exe` because the producer reads RAW data and Thermo DLLs.

Preflight requirements before any 85RAW producer run:

- run the producer first on the 8RAW retained-candidate subset;
- confirm the candidate subset count is seven for the current pilot artifacts,
  or record the changed count as the first finding;
- confirm the 85RAW discovery/alignment input contains 85 samples before launch;
- include an `--expected-sample-count 85` producer-side guard;
- include RAW directory and Thermo DLL directory parameters from
  `docs/agent-parameter-settings.md`;
- write heartbeat or timing sidecars for any run likely to exceed 30 minutes;
- stop if RAW paths, DLL paths, candidate subset, or sample count are missing
  rather than silently falling back to another data source.

The producer should emit `inconclusive` rows for missing assessable RAW evidence
only after preflight has established that the run itself used the intended RAW
inventory. A failed preflight is not a valid Tier 2 sidecar.

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

- candidate gate accepts `--tier2-trace-evidence-tsv` plus
  `--tier2-raw-manifest-tsv`;
- sidecar provenance failures are machine-readable;
- output remains `diagnostic_only`;
- `alignment_matrix.tsv` content is unchanged.

Real-data pilot:

- run the producer only on the seven retained candidates in the current 8RAW and
  85RAW retained-provisional artifacts;
- re-run candidate gate with the Tier 2 sidecar;
- record counts for `validated`, `not_supported`, `blocked`, and
  `inconclusive`;
- treat zero validated rows as a valid diagnostic outcome only when every row
  has terminal `not_supported`, `blocked`, or `inconclusive` status with
  complete provenance and the exit decision matrix below is applied.

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

- `shadow_ready`: 8RAW and 85RAW sidecars are reproducible; review, cell, RAW
  manifest, and candidate subset hashes validate; every eligible row has a
  terminal status; gate output is deterministic; and each terminal status is
  backed by recomputed RAW trace fields rather than artifact-derived context.
  Zero validated rows may still be `shadow_ready` if the producer proves stable
  negative, blocked, or inconclusive classifications with complete provenance.
- `kill`: the producer cannot emit row-level facts beyond owner-backfill
  artifact context, or more than half of eligible rows are unresolvable
  `inconclusive` because required RAW/metric denominators are unavailable after
  a valid preflight. A killed producer must not remain as a standing diagnostic
  dependency.
- `externalize`: RAW re-read emits stable trace facts but those facts do not
  discriminate identity/coherence decisions. The next decision-changing oracle
  must be named explicitly as targeted, ISTD, or human-reviewed EIC evidence
  under a separate producer contract.

It does not exit as `production_ready`. Primary matrix promotion requires a
separate promotion contract.
