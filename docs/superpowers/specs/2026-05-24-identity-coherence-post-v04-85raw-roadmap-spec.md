# Identity Coherence Post-V0.4 85RAW Roadmap Spec

**Date:** 2026-05-24
**Status:** Post-8RAW acceptance planning spec
**Branch:** `codex/untargeted-backfill-logic-reset`

This spec defines the task sequence after the V0.4 8RAW identity-coherence
diagnostic acceptance pass. It is a roadmap spec, not an implementation plan.
Each phase below should become a focused implementation plan before code
changes.

## Current Accepted State

The V0.4 8RAW diagnostic loop has passed strict acceptance with reviewed
controls.

Accepted local outputs:

```text
output\identity_coherence_8raw_validation_reviewed\
  identity_coherence_8raw_validation_summary.tsv
  identity_coherence_8raw_validation_report.md
  identity_coherence_v04_acceptance.tsv
  identity_coherence_v04_acceptance.md
```

Accepted reviewed control inputs:

```text
output\identity_coherence_8raw_validation\
  identity_coherence_controls_manifest_8raw.reviewed.tsv
  identity_coherence_controls_manifest_8raw.review_notes.md
```

Strict acceptance result:

```text
serial_process_sidecar_parity = pass
reviewed_controls_manifest = pass
positive_control_sensitivity = pass  # 5/5
identity_decoy_specificity = pass     # 0 promoted, 3/3 rejected
v04_acceptance = pass
```

Representative 8RAW mechanics counters:

```text
input_row_count = 2302
seed_gate_class.coherent_seed = 1705
seed_gate_class.review_only_seed_gate_failed = 597
would_primary_provisional_identity_family_support = 1387
raw_xic_request_count = 15118
xic_point_count = 125661
projected_85raw_identity_request_count = not_assessed
```

This is enough to close V0.4 8RAW method review. It does not clear 85RAW
execution, production defaults, Backfill behavior, final-matrix filtering, area
correction, normalization, or statistics.

## Benchmark Evidence To Carry Forward

The reviewed 8RAW controls were built from the targeted ISTD benchmark output
in the `area-mismatch-production-fix` worktree:

```text
output\diagnostics\
  untargeted_revalidation_after_targeted_fix_8raw\
    targeted_istd_benchmark\targeted_istd_benchmark_summary.tsv
```

The corresponding 85RAW benchmark reference is:

```text
output\diagnostics\
  untargeted_revalidation_after_targeted_fix_85raw\
    targeted_istd_benchmark\targeted_istd_benchmark_summary.tsv
```

8RAW active PASS positive-control sources used in the reviewed manifest:

| Control | 8RAW benchmark | 85RAW benchmark | V0.4 8RAW use |
| --- | --- | --- | --- |
| `d3-5-hmdC` | PASS | PASS | included |
| `d3-5-medC` | PASS | WARN | included with warning noted |
| `15N5-8-oxodG` | PASS | PASS | included |
| `d3-N6-medA` | PASS | PASS | included |
| `d3-dG-C8-MeIQx` | PASS | PASS | included |

Benchmark row not used as a strict 8RAW positive control:

| Control | 8RAW benchmark | 85RAW benchmark | Reason |
| --- | --- | --- | --- |
| `d4-N6-2HE-dA` | PASS | PASS | no current V0.4 8RAW would-primary mapping within 20 ppm and 60 sec |

For 85RAW, `d4-N6-2HE-dA` should be reconsidered rather than permanently
excluded. Its 8RAW exclusion was a current-output mapping fact, not a statement
that the control is invalid.

## Non-Negotiable Boundaries

The implementation order remains:

```text
identity-family formation / false independent feature suppression
  -> Backfill / value recovery for accepted identity families
  -> downstream final-matrix filtering, area correction, normalization, statistics
```

Post-V0.4 tasks must not:

- change Backfill, final matrix inclusion, area values, normalization, or
  statistical eligibility;
- use blank/QC/background behavior as an identity promotion gate;
- let controls or ISTD labels promote identities;
- make 85RAW production-readiness claims from 8RAW acceptance alone;
- reverse the evidence firewall by importing workbook/report/final-matrix
  surfaces into identity domain logic.

`raw_workers` and `raw_xic_batch_size` are performance controls. Using
`raw_workers = 8` and `raw_xic_batch_size = 64` is allowed for 85RAW validation
as long as frozen sidecar semantics and row ordering remain deterministic.

## Phase 1: Freeze The 8RAW Acceptance Handoff

Goal: make the accepted 8RAW evidence reviewable without relying on memory of
the interactive run.

Tasks:

1. Copy or summarize the reviewed 8RAW controls manifest and review notes into a
   tracked validation fixture or tracked handoff note.
2. Record the exact strict command used to produce
   `output\identity_coherence_8raw_validation_reviewed`.
3. Record the benchmark source paths and included/excluded positive controls.
4. Record immutable provenance for the benchmark sources:
   - absolute source path;
   - SHA256 hash;
   - row count;
   - relevant positive-control rows copied or summarized;
   - the current V0.4 mapping decision/family/seed IDs.
5. Record that the reviewed manifest is validation-only and not identity
   promotion evidence.

Deliverable:

```text
docs\superpowers\validation\identity_coherence_v04_8raw_acceptance_handoff.md
```

or an equivalent tracked document. Do not track large RAW-derived sidecar TSVs
unless a later plan explicitly decides to do so.

Stop conditions:

- any copied manifest path is named `.proposed.tsv`;
- the handoff omits the 8RAW or 85RAW benchmark source;
- the handoff implies 85RAW clearance.

## Phase 2: 85RAW Cost And Threshold Policy Preflight

Goal: define what must be true before a full 85RAW identity diagnostic run is
interpretable.

Why this phase is required:

- the 8RAW threshold `seed + 2 non-seed` cannot be copied blindly to 85RAW;
- `3/8` and `3/85` have different meaning;
- the current 8RAW run reports `projected_85raw_identity_request_count =
  not_assessed`;
- 8RAW observed `raw_xic_request_count = 15118`, so a naive linear 85/8 scale is
  already about 160k identity XIC requests before accounting for different seed
  discovery behavior.

Tasks:

1. Add or run a dry-run preflight estimator that reports:
   - projected 85RAW identity XIC request count;
   - projected XIC point count if cheaply estimable;
   - per-RAW request distribution;
   - coherent-seed candidate count before retrieval;
   - controls/decoy retrieval overhead separately from identity evidence
     retrieval.
2. Define an explicit 85RAW request-budget ceiling:
   `max_projected_85raw_identity_xic_requests`.
3. Define the 85RAW count+fraction policy shape. The policy must include both:
   - a minimum count floor;
   - a minimum assessed-sample fraction or an explicit justification for why a
     fraction is not used.
4. Keep the first 85RAW threshold policy provisional until the 85RAW exploratory
   distribution is reviewed.

Recommended policy form:

```text
would_primary_85raw if:
  total_coherent_sample_count >= min_total_coherent_samples_85raw
  non_seed_coherent_sample_count >= min_non_seed_coherent_samples_85raw
  tier12_non_seed_identity_sample_count >= min_non_seed_tier12_identity_samples_85raw
  coherent_fraction >= min_coherent_fraction_85raw
  tier12_identity_sample_fraction >= min_tier12_identity_sample_fraction_85raw
```

`coherent_fraction` already exists in frozen decisions output. Any new
fraction gate, including `tier12_identity_sample_fraction`, must first define
its denominator and be frozen into a TSV schema or be computed from a frozen
per-cell evidence surface in a reviewed implementation plan. Do not enforce a
fraction threshold that is not backed by frozen output.

The spec does not set numeric 85RAW thresholds yet. Numeric thresholds must be
chosen after the preflight distribution and controls are reviewed.

Stop conditions:

- the preflight cannot estimate request count;
- the projected request count exceeds the declared ceiling;
- the policy only specifies counts and ignores fractions without an explicit
  reviewed reason;
- the estimator calls vendor RAW adapters, performs XIC retrieval, increments
  `raw_chromatogram_call_count`, or mutates process sidecar outputs;
- the policy is used to filter final-matrix analytical eligibility.

## Phase 3: 85RAW Bootstrap Diagnostic Execution

Goal: run the identity diagnostic at 85RAW scale without mutating production
outputs and produce frozen outputs that can be used to build reviewed 85RAW
controls.

Execution mode:

```text
emit_identity_coherence_diagnostic = true
raw_workers = 8
raw_xic_batch_size = 64
controls_manifest = none, or a proposal-only manifest that cannot satisfy
  acceptance
```

The preferred 85RAW validation path is process-mode execution with deterministic
frozen outputs. A full serial-vs-process 85RAW exact parity run is not required
by default because it may double the RAW/XIC cost. 8RAW strict parity remains the
process-correctness proof. If 85RAW process behavior looks suspicious, run a
targeted serial/process parity subset before interpreting 85RAW method results.

This phase must not produce a passing 85RAW acceptance claim. Its purpose is to
create the frozen 85RAW request/decision/cell evidence surfaces needed to remap
positive controls and generate 85RAW identity decoys. The bootstrap run can
emit a proposal manifest, but `.proposed.tsv` remains non-reviewed input.

Required outputs:

```text
output\identity_coherence_85raw_validation\
  identity_coherence_85raw_validation_summary.tsv
  identity_coherence_85raw_validation_report.md
  process\identity_coherence\untargeted_identity_coherence_requests.tsv
  process\identity_coherence\untargeted_identity_coherence_decisions.tsv
  process\identity_coherence\untargeted_identity_coherence_cell_evidence.tsv
  process\identity_coherence\untargeted_identity_coherence_controls.tsv
  process\identity_coherence\untargeted_identity_coherence_summary.md
```

The exact script name can be either:

- a generalized validator that accepts `--dataset-label 85raw`; or
- a new `validate_identity_coherence_85raw.py` wrapper.

Do not overload an `8raw`-named script in a way that hides the dataset identity.

Stop conditions:

- `forbidden_evidence_used_count > 0`;
- schema/header parity fails;
- process run is nondeterministic across repeated execution with the same input;
- infrastructure-blocked fraction exceeds the reviewed ceiling;
- the run requires changing RAW/XIC retrieval semantics rather than batching or
  worker-count performance settings.

Over-budget remediation may change candidate/request policy, run partitioning,
batching, or worker strategy. It must not silently change vendor RAW/XIC
semantics, use approximate retrieval, or alter chromatogram extraction behavior
unless a separate diagnostic-mode spec is reviewed and approved.

## Phase 4: 85RAW Controls Manifest And Acceptance

Goal: verify sensitivity and false-identity specificity at 85RAW scale.

Tasks:

1. Build a proposed 85RAW controls manifest from the current 85RAW frozen
   outputs, not by copying 8RAW `decision_id` / `identity_family_id` values.
2. Remap positive controls by current 85RAW `m/z`, RT, and frozen
   `decision_id` / `identity_family_id` / `seed_candidate_id`.
3. Reconsider all active ISTD benchmark rows, including `d4-N6-2HE-dA`.
4. Carry forward warning context for `d3-5-medC`; a targeted benchmark WARN
   requires a review note, not automatic exclusion.
5. Generate identity decoys from 85RAW coherent seeds.
6. Human-review the proposal, save it as `.reviewed.tsv`, and run a strict
   acceptance pass against the frozen 85RAW outputs or a deterministic rerun.
7. Require:
   - positive controls pass at the reviewed threshold;
   - decoy promoted count is zero;
   - decoy failures are auditable;
   - controls remain validation-only.

85RAW reviewed controls must be named with a `.reviewed.tsv` suffix. A
`.proposed.tsv` manifest is not accepted as reviewed input.

Canonical acceptance artifacts:

```text
identity_coherence_85raw_acceptance.tsv
identity_coherence_85raw_acceptance.md
```

The method version belongs inside those files as metadata, not in the file name.

Stop conditions:

- any identity decoy reaches `coherent_seed`;
- any positive control fails without an explicit reviewed acceptable reason;
- a control row maps ambiguously;
- controls are used to alter identity decisions.

## Phase 5: 85RAW Method Review And Production Boundary

Goal: decide what the accepted 85RAW diagnostic means operationally.

Possible outcomes:

| Outcome | Meaning | Next action |
| --- | --- | --- |
| 85RAW diagnostic fails engineering or controls | method not ready | fix identity diagnostic before production discussion |
| 85RAW diagnostic passes but count/fraction policy is unstable | method mechanically works, policy immature | iterate threshold policy on frozen outputs |
| 85RAW diagnostic passes reviewed policy and controls | identity diagnostic can be considered for opt-in production use | write a production-adoption plan |

Even after 85RAW pass, production adoption is a separate decision. It should
decide:

- whether identity coherence remains opt-in or becomes part of a standard
  validation pipeline;
- whether output artifacts are persisted by default;
- how downstream workflows consume `would_primary_provisional_identity_family_support`;
- how Review-only identity states are handed off;
- how to document that contaminants/background features can still be valid
  identity families and are filtered downstream.

Production adoption must not:

- silently change final matrix inclusion;
- rewrite Backfill values;
- hide Review-only rows;
- convert provisional identity-family support into library-grade identification.

## Phase 6: Downstream Audit Spec, If Needed

Only after identity coherence has a reviewed 85RAW result should downstream
blank/QC/background filtering be specified.

That downstream spec owns:

- blank abundance filtering;
- QC CV filtering;
- contaminant filtering;
- missingness rules;
- area correction;
- normalization;
- imputation;
- batch correction;
- statistical eligibility.

It consumes identity outputs but must not feed back into identity promotion.

## Plan Split

Convert this roadmap into these implementation plans, in order:

1. `identity-coherence-v04-8raw-handoff-plan`
   - tracked handoff note;
   - benchmark source documentation;
   - no code behavior changes.
2. `identity-coherence-85raw-preflight-plan`
   - projected request count;
   - request-budget ceiling;
   - provisional count+fraction policy shape.
3. `identity-coherence-85raw-bootstrap-runner-plan`
   - generalized or 85RAW-specific validation runner;
   - process-mode 85RAW bootstrap diagnostic execution;
   - deterministic output contract.
4. `identity-coherence-85raw-controls-acceptance-plan`
   - reviewed 85RAW controls manifest;
   - positive-control/decoy acceptance;
   - `identity_coherence_85raw_acceptance.*` report.
5. `identity-coherence-production-adoption-boundary-plan`
   - opt-in/default decision;
   - downstream handoff contract;
   - no final-matrix filtering unless a separate downstream spec is approved.

Do not start plan 3 until plan 2 has a reviewed budget and policy shape. Do not
start plan 5 unless plan 4 passes. If plan 4 produces a reviewed No-Go
rationale, the next plan must be a method-fix or threshold-policy iteration
plan, not production adoption.

## Review Questions

1. Should the 85RAW diagnostic use a process-only run plus targeted parity
   subset, or is a full serial/process 85RAW exact parity run worth the cost?
2. What is the first reviewed ceiling for
   `max_projected_85raw_identity_xic_requests`?
3. Should the 85RAW count+fraction policy use a single global fraction, or
   class-specific policies for ubiquitous ISTD-like controls versus biological
   sample-variable features?
4. Should `d3-5-medC` remain a positive control with a WARN note, or be split
   into a sensitivity-only control class?
5. Should 85RAW decoys remain RT-shift only for the first scale run, or add
   `mz_shift` / `fragment_tag_shuffle` once the request-candidate consistency
   gate is already tested?
6. Should the first 85RAW run be bootstrap-only with no reviewed controls, or
   should it accept a proposal-only manifest that is explicitly barred from
   satisfying acceptance?
7. What exact 85RAW command/input contract should be canonical:
   `discovery_batch_index`, `raw-dir`, `dll-dir`, output root, dataset label,
   and runner script name?
8. What output retention policy is acceptable for 85RAW diagnostic sidecars,
   given their size and audit value?

## Acceptance Criteria For This Roadmap

This roadmap is accepted when reviewers agree that:

- 8RAW V0.4 acceptance is closed but not overclaimed;
- 85RAW work is blocked on explicit budget and count+fraction policy, not on
  more seed-gate redesign;
- workers/batch settings are treated as performance settings, not method
  changes;
- controls remain validation-only;
- downstream filtering remains downstream;
- the plan sequence cannot accidentally implement final-matrix filtering before
  identity coherence scale validation.
