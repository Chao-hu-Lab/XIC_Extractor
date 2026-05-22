# Untargeted Identity Coherence Diagnostic Prototype Spec

**Date:** 2026-05-22
**Status:** Executable review draft v0.2
**Branch:** `codex/untargeted-backfill-logic-reset`
**Worktree:** `C:\Users\user\Desktop\XIC_Extractor\.worktrees\untargeted-backfill-logic-reset`

---

## Summary

This spec resets the untargeted alignment discussion one layer above Backfill.

Backfill is a value recovery step after an untargeted identity already exists.
The next checkpoint must therefore test identity formation before any new
Backfill rule is designed.

V0.2 is a diagnostic-only prototype. It must not change `alignment_matrix.tsv`,
workbooks, current Backfill behavior, or production promotion logic.

```text
build_owners
  -> cluster_owners
  -> identity_coherence_diagnostic   # new opt-in diagnostic stage
  -> owner_backfill                  # unchanged production path
  -> build_matrix / review / cells   # unchanged production path
```

Core product rule:

```text
Primary Matrix = clean coherent identities and coherent sample values.
Review/Audit = high-recall evidence, weak peaks, conflicts, non-coherent peaks,
               seed provenance, and later Backfill evidence.
Backfill = value recovery after identity promotion, not identity creation.
```

## Problem

Recent work has been stuck at the Backfill layer. That created a loop:

- a weak or ambiguous untargeted identity enters the matrix;
- Backfill rescues many sample-level peaks for that identity;
- the rescue-heavy row looks suspicious;
- new gates are proposed around Backfill;
- the pipeline still has not answered whether the row identity should exist.

This is the wrong abstraction boundary. Backfill can only recover values for an
already-supported identity. It must not become the mechanism that creates
untargeted row identity.

## Design Goals

- Separate identity formation from value recovery.
- Preserve a clean downstream Primary Matrix.
- Keep high-recall evidence visible in Review/Audit.
- Avoid treating current `backfill` / `absent` semantics as final scientific
  acceptance criteria.
- Keep V0.2 small enough to prototype and review on the 8RAW subset first.
- Preserve a clear upgrade path toward multi-seed merge/split and stronger
  scoring later.

## Non-Goals

- No production matrix behavior change in V0.2.
- No replacement of current `owner_backfill.py`.
- No new default Backfill gate.
- No production graph merge/split implementation in V0.2.
- No full scoring model in V0.2.
- No GUI change.
- No workbook schema change.

## Prototype MVP Scope

V0.2 answers one question:

```text
Can seed-centered, Backfill-free coherence separate plausible untargeted
identities from weak or rescue-heavy rows?
```

In scope:

- medium seed qualification;
- one deterministic primary seed center per source candidate;
- seed-centered coherence scan across samples;
- explicit reporting of secondary or overflow seed centers;
- diagnostic tables explaining would-be Primary vs Review-only decisions;
- 8RAW review before any 85RAW validation.

Out of scope until Phase 2:

- production graph merge/split;
- merging multiple coherent seed groups into one production identity;
- splitting conflicting seed groups into multiple production identities;
- changing `matrix_identity`, `primary_consolidation`, or workbook output.

## Prototype Data Flow And Ownership

The diagnostic stage belongs between owner clustering and Backfill:

```text
Discovery events / sample-local owners
  -> build_owners
  -> cluster_owners
  -> identity_coherence_diagnostic
  -> owner_backfill
```

Implementation ownership:

- domain logic should live in a focused alignment module such as
  `xic_extractor/alignment/identity_coherence.py`;
- TSV writing should live in a focused diagnostic writer, not in workbook code;
- RAW opening, vendor XIC extraction, process-mode batching, and cancellation
  stay in orchestration/backend layers;
- the diagnostic must not mutate `AlignmentMatrix`, existing TSVs, workbook
  outputs, or Backfill state.

The diagnostic may read post-run alignment artifacts only for comparison or
provenance. It must not use post-Backfill status, rescue counts, final matrix
inclusion, or workbook values as identity-promotion evidence.

## Evidence Firewall

The prototype must make identity evidence provenance explicit.

| Evidence | Identity promotion use | Notes |
| --- | --- | --- |
| neutral loss tag from discovery/profile | allowed | Required medium seed evidence. |
| product m/z and observed neutral loss tolerance | allowed | Required medium seed evidence. |
| sample-local MS1 owner before `owner_backfill` | allowed | Must include finite area, apex RT, height, and boundaries. |
| diagnostic vendor RAW XIC extracted before Backfill | allowed | Expensive path; must be counted and timed. |
| config tolerances and sample order | allowed | Must be recorded in summary. |
| `alignment_review.tsv` family ids | provenance/comparison only | Not identity-promotion evidence. |
| `alignment_cells.tsv` detected owner cells | allowed only if pre-Backfill provenance is explicit | Must not mix with rescued/backfilled cells. |
| `owner_backfill` rescued area/status | forbidden | Backfill cannot create identity evidence. |
| `backfill`, `rescued`, `absent`, `unchecked` production statuses | forbidden for promotion | May be shown in comparison columns only. |
| final `include_in_primary_matrix` | forbidden | Current production outcome is not evidence for the new diagnostic. |
| workbook values | forbidden | Rendering surface, not identity evidence. |
| family-center re-extraction after Backfill | forbidden in V0.2 | Would mix identity promotion with value rewriting. |

Every promoted or would-promoted cell must expose `evidence_source`. Valid V0.2
values are:

```text
pre_backfill_owner
diagnostic_vendor_xic
comparison_only_current_alignment
```

Only the first two may support identity promotion.

## Terminology And ID Contract

Use stable IDs so TSVs can be joined and diffed.

| Term | Meaning |
| --- | --- |
| `source_feature_family_id` | Existing pre-Backfill owner/cluster family identifier, when available. |
| `source_candidate_id` | Source discovery or owner candidate id. |
| `seed_id` | Stable id for one qualified medium seed. |
| `coherence_group_id` | Stable id for one seed-centered scan result. |
| `coherence_cell_id` | Stable id for one group/sample decision. |
| `decision_id` | Stable id for one candidate-level diagnostic decision. |
| `would_primary_identity_id` | Diagnostic-only row id for would-be Primary output. |
| `sample_stem` | Sample key matching existing alignment TSV style. |

Recommended id formats:

```text
SEED000001
COH_G000001
COH_C000001_Sample_A
COH_D000001
COH_P000001
```

Sorting must be deterministic: numeric id order, then `sample_stem`, then
`source_candidate_id`.

## Prototype CLI / IO Contract

V0.2 should be an opt-in diagnostic command. The exact Python module can change,
but the contract must be equivalent to:

```powershell
python -m tools.diagnostics.untargeted_identity_coherence `
  --alignment-dir <existing_alignment_output_dir> `
  --output-dir <diagnostic_output_dir> `
  --max-rt-sec 180 `
  --preferred-rt-sec 60 `
  --min-coherent-samples 3
```

Required behavior:

- exit `0` when all diagnostic artifacts are written;
- exit non-zero when required inputs are missing or malformed;
- write only under `--output-dir`;
- never overwrite current `alignment_matrix.tsv`, `alignment_review.tsv`,
  `alignment_cells.tsv`, workbook output, or Backfill audit files;
- record input file hashes, row counts, command arguments, thresholds, and
  no-mutation hash checks in the summary;
- fail with a clear missing-input diagnostic instead of silently falling back to
  Backfill-derived evidence.

## Parameters And RT Units

All RT fields in diagnostic TSVs must include units in the column name.

Baseline parameters:

| Parameter | Default | Unit | Meaning |
| --- | ---: | --- | --- |
| `max_rt_sec` | 180 | seconds | Broad initial extraction window around `seed_rt_min`. |
| `preferred_rt_sec` | 60 | seconds | Narrow gate around provisional center. |
| `min_coherent_samples` | 3 | samples | Minimum coherent cells for V0.2 would-promote. |
| `max_center_drift_sec` | 60 | seconds | Seed anchor guard for provisional center. |

Use explicit minute/second conversion:

```text
initial_rt_min = seed_rt_min - (max_rt_sec / 60.0)
initial_rt_max = seed_rt_min + (max_rt_sec / 60.0)

center_drift_sec =
  abs(provisional_center_rt_min - seed_rt_min) * 60.0

rt_delta_center_sec =
  abs(sample_apex_rt_min - provisional_center_rt_min) * 60.0

coherent_rt_gate =
  rt_delta_center_sec <= preferred_rt_sec
```

If `center_drift_sec > max_center_drift_sec`, the group remains Review-only
with reason `center_unstable_review_only`. This prevents a broad-window
neighbor peak from hijacking the provisional center.

The summary should also include sensitivity counters for review only:

```text
would_promote_at_min_samples_2
would_promote_at_min_samples_3
would_promote_at_min_samples_4
would_promote_at_preferred_rt_sec_30
would_promote_at_preferred_rt_sec_60
would_promote_at_preferred_rt_sec_90
```

These counters do not change the V0.2 default decision.

## Medium Seed Qualification

A medium seed is the minimum evidence unit for creating a Review candidate.

V0.2 medium seed requirements:

- neutral loss tag matches the active profile;
- product m/z is inside tolerance;
- observed neutral loss is inside tolerance;
- sample-local MS1 owner is quantifiable before Backfill;
- `seed_area`, `seed_apex_rt_min`, `seed_height`, `seed_start_rt_min`, and
  `seed_end_rt_min` are present and finite;
- `seed_area > 0`.

V0.2 does not require a high evidence score.

These records do not qualify as medium seeds:

- ambiguous MS1 owner records;
- duplicate losers;
- records without quantifiable MS1 owner evidence;
- records missing product/loss evidence needed by the active profile;
- records whose only quantifiable evidence comes from Backfill/rescue.

Seed ranking for the single-seed MVP is deterministic:

1. qualified medium seeds before non-qualified records;
2. non-ambiguous owner evidence before ambiguous evidence;
3. higher finite `seed_area`;
4. higher finite `seed_height`;
5. lower absolute product/loss tolerance error, if available;
6. lexical `sample_stem`;
7. lexical `source_candidate_id`.

The top-ranked seed becomes `seed_role = primary`. All other compatible seeds
remain visible as `seed_role = secondary` or `seed_role = overflow`.

## Identity Promotion Rule

One medium seed alone creates a Review candidate, not a production Primary row.

V0.2 emits diagnostic decisions:

| Decision | Meaning |
| --- | --- |
| `would_primary_single_seed` | The primary seed group passes V0.2 coherence and has no blocking error. |
| `review_only_insufficient_coherence` | Fewer than `min_coherent_samples` coherent cells. |
| `review_only_center_unstable` | Provisional center drift exceeds `max_center_drift_sec`. |
| `review_only_multi_seed_requires_phase2` | Secondary/overflow seeds create unresolved multi-seed ambiguity. |
| `review_only_error` | Required input, RAW extraction, or non-finite trace failure prevents assessment. |

These are diagnostic outcomes only. They do not change current production
matrix inclusion.

## Coherence Scan

Coherence scan is an identity promotion diagnostic, not Backfill.

For each primary seed center:

```text
primary seed center
  -> broad extraction window in each sample
  -> quantifiable peak candidates
  -> provisional center from complete candidates
  -> seed-anchor center guard
  -> narrow RT acceptance gate
  -> seed-specific coherent group
```

V0.2 coherence criteria:

- peak exists;
- peak area, apex RT, height, start RT, and end RT are complete;
- area is positive and finite;
- `center_drift_sec <= max_center_drift_sec`;
- `rt_delta_center_sec <= preferred_rt_sec`.

V0.2 intentionally does not gate on normalized MS1 shape or neighbor
interference. The interface must leave room for a future scoring model that can
classify coherent, weak, interfering, ambiguous, and rejected peaks.

## RAW XIC Cost Budget And Stop Conditions

The prototype must report RAW/XIC cost, because the known performance risk is
request count and vendor XIC I/O.

Required counters:

- `candidate_count`;
- `qualified_seed_count`;
- `primary_seed_count`;
- `secondary_seed_count`;
- `overflow_seed_count`;
- `extract_xic_count`;
- `raw_chromatogram_call_count`;
- `xic_point_count`;
- `wall_time_sec`;
- per-sample and per-RAW request counts where available.

85RAW validation must not start until 8RAW has produced these counters and the
estimated 85RAW request cardinality is reviewed.

If an MS1 scan-index or approximate fast path is used, it must be marked as an
explicit approximate diagnostic mode. It must not silently replace vendor XIC
as an equivalent path.

## Multi-Seed Handling In V0.2

V0.2 is deliberately conservative.

- Only the deterministic primary seed center drives `would_primary_single_seed`.
- Secondary and overflow seeds are preserved in `candidates.tsv`.
- If secondary/overflow evidence indicates unresolved competing RT or fragment
  context, the candidate-level decision is
  `review_only_multi_seed_requires_phase2`.
- V0.2 does not merge multiple coherent seed groups.
- V0.2 does not split conflicting seed groups into production identities.

Required overflow fields:

```text
compatible_seed_count
secondary_seed_count
overflow_seed_count
overflow_seed_ids
multi_seed_review_flag
```

Phase 2 may introduce graph merge/split only after V0.2 8RAW review confirms
the single-seed identity-first framing is useful.

## Diagnostic Output Contract

The artifact names are fixed for V0.2:

```text
untargeted_identity_coherence_candidates.tsv
untargeted_identity_coherence_groups.tsv
untargeted_identity_coherence_cells.tsv
untargeted_identity_coherence_decisions.tsv
untargeted_identity_coherence_summary.md
```

### `untargeted_identity_coherence_candidates.tsv`

Required columns:

```text
candidate_id
source_feature_family_id
source_candidate_id
seed_id
seed_role
sample_stem
neutral_loss_tag
precursor_mz
product_mz
observed_neutral_loss_da
seed_rt_min
seed_area
seed_height
seed_start_rt_min
seed_end_rt_min
evidence_source
seed_decision
seed_reject_reason
seed_rank
compatible_seed_count
secondary_seed_count
overflow_seed_count
overflow_seed_ids
```

`seed_decision` enum:

```text
qualified_medium_seed
rejected_missing_fragment_evidence
rejected_no_quantifiable_owner
rejected_ambiguous_owner
rejected_duplicate_loser
rejected_backfill_only_evidence
rejected_nonfinite_peak
```

### `untargeted_identity_coherence_groups.tsv`

Required columns:

```text
coherence_group_id
candidate_id
seed_id
source_feature_family_id
seed_rt_min
initial_rt_min
initial_rt_max
max_rt_sec
preferred_rt_sec
min_coherent_samples
provisional_center_rt_min
center_drift_sec
center_decision
coherent_sample_count
assessed_sample_count
would_promote_at_min_samples_2
would_promote_at_min_samples_3
would_promote_at_min_samples_4
would_promote_at_preferred_rt_sec_30
would_promote_at_preferred_rt_sec_60
would_promote_at_preferred_rt_sec_90
group_decision
group_reject_reason
extract_xic_count
raw_chromatogram_call_count
xic_point_count
wall_time_sec
```

`group_decision` enum:

```text
would_primary_single_seed
review_only_insufficient_coherence
review_only_center_unstable
review_only_multi_seed_requires_phase2
review_only_error
```

### `untargeted_identity_coherence_cells.tsv`

Required columns:

```text
coherence_cell_id
coherence_group_id
candidate_id
seed_id
sample_stem
evidence_source
requested_rt_min
requested_rt_max
peak_found
area
height
apex_rt_min
start_rt_min
end_rt_min
rt_delta_seed_sec
rt_delta_center_sec
cell_decision
cell_exclusion_reason
extraction_error
```

`cell_decision` enum:

```text
coherent
non_coherent_missing_peak
non_coherent_incomplete_peak
non_coherent_nonfinite_peak
non_coherent_outside_rt_gate
non_coherent_center_unstable
unassessed_missing_raw
unassessed_extraction_error
```

### `untargeted_identity_coherence_decisions.tsv`

Required columns:

```text
decision_id
candidate_id
source_feature_family_id
would_primary_identity_id
decision
decision_reason
primary_seed_id
coherence_group_id
coherent_sample_count
min_coherent_samples
secondary_seed_count
overflow_seed_count
multi_seed_review_flag
evidence_sources_used
forbidden_evidence_seen
forbidden_evidence_used
current_production_identity_decision
current_include_in_primary_matrix
notes
```

`forbidden_evidence_used` must always be `false`. If it is `true`, the run
fails acceptance.

### `untargeted_identity_coherence_summary.md`

Required sections:

- command and arguments;
- input files, hashes, and row counts;
- output files;
- thresholds and RT unit contract;
- no-mutation hash check;
- decision counts by reason;
- seed qualification counts by reason;
- cell exclusion counts by reason;
- multi-seed and overflow counts;
- missing input or invalid column diagnostics;
- RAW/XIC request and timing counters;
- top examples for each failure mode;
- sensitivity counters for min coherent samples and RT gates;
- Go / No-Go / Pivot table.

## Failure Modes That Must Be Explainable

Every non-written or Review-only result must have an explicit reason.

Required reason coverage:

- missing required input file;
- missing required input column;
- missing RAW source;
- RAW extraction error;
- non-finite trace or peak field;
- zero candidate peak;
- incomplete peak boundaries;
- center drift unstable;
- outside recentered RT gate;
- insufficient coherent samples;
- ambiguous owner;
- duplicate loser;
- Backfill-only evidence rejected;
- secondary/overflow seed requires Phase 2;
- forbidden evidence detected in input but excluded.

## Acceptance Criteria For Prototype

V0.2 is ready for user review when it can run on the 8RAW validation subset and
produce:

- all five fixed diagnostic artifacts;
- fixed schemas and enum values matching this spec;
- no changes to current `alignment_matrix.tsv`, workbook, or Backfill behavior;
- evidence provenance showing no Backfill-derived promotion evidence;
- explicit RT units and second/minute conversion;
- RAW/XIC request counters and wall time;
- at least one example row for stable-like, weak/single-sample,
  duplicate/conflict-like, and multi-seed/overflow-like cases where present;
- a summary that explains every Review-only or non-coherent decision class.

Minimum test surface before real RAW validation:

- seed qualification unit tests;
- RT unit conversion and recentered gate tests;
- center-drift guard tests;
- deterministic seed ranking and overflow tests;
- schema golden tests for the five artifacts;
- no-mutation contract test;
- no-RAW CLI error-path test;
- process/pickle smoke if the diagnostic uses process workers.

## Go / No-Go / Pivot Rules

| Observation after 8RAW | Decision |
| --- | --- |
| Expected stable-like rows pass coherence without Backfill evidence | Proceed to 85RAW request-count review. |
| Stable-like rows fail mostly because `preferred_rt_sec=60` is too narrow | Run sensitivity review before changing product rule. |
| Single-sample or weak rows become `would_primary_single_seed` often | Tighten seed qualification or require scoring before 85RAW. |
| Backfill/rescued evidence is used for promotion | No-Go; fix evidence firewall before any further validation. |
| Multi-seed/overflow dominates candidate decisions | Pivot to Phase 2 graph merge/split spec before production design. |
| RAW/XIC request count projects poorly to 85RAW | Add locality/request budget design before 85RAW. |
| Center instability dominates | Add scoring or seed-anchor improvements before production design. |
| Diagnostic schemas are not stable enough for diffing | No-Go; stabilize contracts before data review. |

85RAW validation can start only after the 8RAW review signs off on:

- evidence firewall;
- schema stability;
- request-count budget;
- sentinel case behavior;
- decision table interpretation.

## Future Upgrade Path

After V0.2 review, Phase 2 can add graph merge/split:

```text
multiple seed-centered coherent groups
  -> compatibility edges
  -> conflict guard
  -> merge compatible groups or split independent coherent identities
```

The scoring upgrade can replace the simple coherence gate with:

```text
classify_sample_coherence(trace, seed_context, provisional_center) ->
    coherent | weak | neighbor_interference | ambiguous | rejected
```

Future evidence categories:

- normalized MS1 shape coherence;
- neighbor interference;
- local baseline and integration uncertainty;
- scan support;
- area distribution across samples;
- seed quality score;
- drift-aware expected RT;
- targeted ISTD benchmark overlays.

This upgrade must keep the same separation:

```text
identity promotion first;
Backfill/value recovery second.
```

## Review Questions

Review should focus on these decisions before implementation:

1. Is `min_coherent_samples = 3` the right V0.2 default, with 2/3/4 emitted as
   sensitivity counters?
2. Is `preferred_rt_sec = 60` acceptable as the V0.2 narrow RT gate?
3. Is `max_center_drift_sec = 60` a reasonable seed-anchor guard?
4. Is the evidence firewall strict enough to prevent Backfill leakage?
5. Should V0.2 keep the conservative single-seed MVP, or should Phase 2
   multi-seed graph merge/split be planned immediately after 8RAW review?
6. Are these TSV schemas sufficient for reviewing 8RAW and 85RAW?
