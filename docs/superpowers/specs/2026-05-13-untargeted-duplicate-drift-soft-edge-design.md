# Untargeted Duplicate And Drift Soft-Edge Design

**Date:** 2026-05-13
**Status:** Design approved for spec review; implementation plan not written yet
**Branch:** `codex/untargeted-discovery-v1-implementation`
**Worktree:** `C:\Users\user\Desktop\XIC_Extractor\.worktrees\untargeted-discovery-v1-implementation`

## Summary

This design defines the next untargeted alignment correction pass.

The two main problems are:

1. repeated MS2/NL events and tail events creating duplicate production
   feature rows;
2. retention-time drift across injection order causing clean same-feature
   owners to split across sample blocks.

The accepted direction is targeted-inspired soft edge scoring. The targeted
pipeline is used as a reference for mature evidence handling, drift
interpretation, and validation fixtures. It is not copied as a target-specific
production rule.

The core rule remains:

```text
This is an untargeted method.
Known targeted compounds are checkpoints, not algorithmic exceptions.
```

## Current Evidence

The current 8-RAW inspection set shows four representative cases:

| Case | Signal | Interpretation |
|---|---|---|
| Case 1 | m/z 242, 5-medC-like | repeated events and class/order-linked RT drift split a likely same feature |
| Case 2 | m/z 296 | dense/doublet region; unsafe to force merge |
| Case 3 | m/z 322 | drifted same-feature-like owners split across samples |
| Case 4 | m/z 251 | anchor/tail/shadow events duplicate one MS1 feature |

Targeted workbooks provide repeatable checkpoints:

| Target | Role in this design |
|---|---|
| `5-medC` | positive GT checkpoint; expected to reduce split without increasing miss |
| `5-hmdC` | positive GT checkpoint; expected to reduce split without increasing miss |
| `8-oxodG` | negative checkpoint; should not produce accepted untargeted production family |

Targeted issue #42 records a separate targeted-method limitation:

```text
Targeted anchor mismatch tolerance can over-demote high-confidence
5-hmdC/5-medC peaks because the current paired target anchor guard uses
allowed +/- 0.25 min.
```

That issue is intentionally out of scope for this untargeted correction pass.
The targeted tolerance is a warning about validation interpretation, not a
parameter to copy into untargeted alignment.

## Boundary

### In Scope

- reduce same-sample duplicate signal before production row formation;
- make cross-sample owner alignment drift-aware through soft evidence;
- use injection order and ISTD RT trend as external drift evidence;
- keep `Sample_Type` diagnostic-only for this batch;
- validate with targeted GT checkpoints and 8-RAW/85-RAW artifacts;
- run real-data validation with 8 RAW workers where available.

### Out Of Scope

- changing targeted extraction behavior;
- relaxing targeted anchor mismatch tolerance;
- using target labels as production merge rules;
- using `Sample_Type` as edge evidence in this batch;
- implementing multi-tag discovery or R/dR compatibility;
- making rescued/backfilled cells seed or bridge alignment edges;
- introducing ML, class-aware priors, or learned parameters.

## Design Principles

### 1. Candidate Generation Wide, Scoring Strict

Untargeted discovery may remain sensitive. Repeated events should be preserved
early and resolved later through owner and edge evidence.

### 2. MS1 Ownership Before Cross-Sample Alignment

Same-RAW duplicate cleanup must happen at the sample-local MS1 owner layer.
Multiple MS2/NL events on one MS1 peak should become supporting events for one
owner, not separate production rows.

### 3. Drift Is Evidence, Not A Dictator

Injection-order and ISTD RT trend can explain why two clean owners should align.
They cannot override neutral-loss, precursor, product, or owner-quality
incompatibility.

### 4. Targeted Is A Checkpoint Source

Targeted results provide:

- validation fixtures;
- ISTD RT trend evidence;
- examples of mature evidence scoring.

They do not provide:

- production target-specific merge exceptions;
- untargeted RT thresholds to copy directly;
- target-label-based identity.

## Architecture

The design uses three layers.

### Layer 1: Sample-Local Owner Cleanup

For each RAW file:

1. resolve candidate MS1 peaks from XIC traces;
2. group same-apex/window candidates into one owner;
3. assign peak-tail events as supporting evidence when the dominant MS1 peak is
   clear;
4. mark unresolved doublet/multiplet regions as ambiguous instead of forcing a
   merge.

This layer does not use sample type, injection order, targeted labels, or batch
drift priors.

### Layer 2: Drift-Aware Edge Scoring

For every pair of cross-sample owners, first apply hard compatibility gates.
Only compatible owner pairs receive a soft edge score.

Soft evidence may include:

- raw RT delta;
- drift-corrected RT delta;
- injection-order local consistency;
- ISTD trend support;
- owner trace quality;
- seed support;
- duplicate/tail evidence.

The edge score determines whether a pair becomes a strong merge edge, weak
review edge, or blocked edge.

### Layer 3: Guarded Feature-Family Construction

Production feature families are built from strong detected-owner edges.

Rules:

- rescued/backfilled cells may fill an existing family;
- rescued/backfilled cells may not create, bridge, or expand a family;
- weak edges are review evidence, not automatic merge evidence;
- blocked edges must remain split or debug/review-only.

## External Drift Evidence Layer

The v1 drift evidence layer reads metadata outside the untargeted candidate
table.

Inputs:

| Input | Use |
|---|---|
| `SampleInfo.xlsx` | `Sample_Name` to `Injection_Order` mapping |
| targeted workbook / ISTD trend | observed ISTD RT trend by injection order |
| untargeted owner RTs | owner pair RTs to evaluate |

Output:

```text
drift prior evidence for owner pair comparison
```

The output is not a target identity claim. It only answers whether the observed
owner RT difference is plausible after accounting for injection-order drift.

### Drift Evidence Adapter Firewall

The adapter that reads targeted artifacts must not expose targeted analyte
identity to alignment code.

Allowed adapter output:

| Field | Meaning |
|---|---|
| `sample_stem` | canonical sample name |
| `injection_order` | injection order from `SampleInfo.xlsx` |
| `istd_label` | ISTD label only; analyte labels are not emitted |
| `istd_rt_min` | observed ISTD RT in that sample |
| `local_trend_rt_min` | rolling/local ISTD trend estimate when available |
| `rt_drift_delta_min` | `istd_rt_min - local_trend_rt_min` when available |
| `source` | `targeted_istd_trend` or `batch_istd_trend` |

Forbidden adapter output:

- analyte target labels such as `5-medC`, `5-hmdC`, or `8-oxodG`;
- targeted GT pass/fail modes;
- targeted analyte RT windows or anchor mismatch tolerances;
- targeted confidence labels used as merge evidence.

Validation tools may read target labels after a run. Production alignment code
must not.

`Sample_Type` remains diagnostic-only in this batch because sample class is
confounded with injection block. It may be reconsidered only when a later
dataset has a stronger experimental design, such as interleaved sample classes
or independent batch replication.

## Edge Gates

### Hard Gates

An owner pair cannot merge unless all hard gates pass:

- exact canonical `neutral_loss_tag` match;
- precursor m/z within configured maximum ppm;
- product m/z within configured tolerance;
- observed neutral loss within configured tolerance;
- owners come from different samples;
- both sides are detected sample-local owners;
- neither side is unresolved ambiguous evidence;
- neither side has an identity conflict.

Hard gate failure means blocked edge.

### Hard-Gate Failure Reasons

The implementation plan must use explicit failure reasons so every blocked edge
is testable:

| Reason | Meaning |
|---|---|
| `same_sample` | owners are from the same sample |
| `neutral_loss_tag_mismatch` | canonical tags differ or either tag is missing |
| `precursor_mz_out_of_tolerance` | precursor ppm exceeds configured limit |
| `product_mz_out_of_tolerance` | product ppm exceeds configured limit |
| `observed_loss_out_of_tolerance` | observed neutral-loss ppm exceeds configured limit |
| `non_detected_owner` | one side is not a detected sample-local owner |
| `ambiguous_owner` | one side is unresolved ambiguous MS1 evidence |
| `identity_conflict` | one owner carries incompatible primary/supporting identity evidence |
| `backfill_bridge` | edge would depend on rescued/backfilled cells |

`identity_conflict` means a sample-local owner contains supporting events whose
canonical neutral-loss tag, product m/z, or observed neutral loss cannot be
reconciled under the same hard gates used for cross-sample identity.

### Soft Evidence Fields

The implementation plan should define a small edge evidence model with at least:

| Field | Meaning |
|---|---|
| `rt_raw_delta_sec` | absolute owner RT difference before drift correction |
| `rt_drift_corrected_delta_sec` | owner RT difference after drift evidence correction |
| `drift_prior_source` | `targeted_istd_trend`, `batch_istd_trend`, or `none` |
| `injection_order_gap` | injection-order distance between samples |
| `owner_quality` | clean, weak, tail-supported, or ambiguous-nearby |
| `seed_support` | MS2 seed count/evidence support summary |
| `duplicate_context` | same-owner supporting event or tail-assignment evidence |

### Minimum Edge Evidence Model

The implementation plan must make the edge evidence model typed and
serializable. The minimum fields are:

| Field | Type | Notes |
|---|---|---|
| `left_owner_id` | string | sample-local owner id |
| `right_owner_id` | string | sample-local owner id |
| `decision` | enum | `strong_edge`, `weak_edge`, `blocked_edge` |
| `failure_reason` | enum or empty | populated for `blocked_edge` |
| `rt_raw_delta_sec` | float | absolute RT difference before drift correction |
| `rt_drift_corrected_delta_sec` | float or blank | blank when no drift prior exists |
| `drift_prior_source` | enum | `targeted_istd_trend`, `batch_istd_trend`, or `none` |
| `injection_order_gap` | integer or blank | blank when either sample has no order |
| `owner_quality` | enum | `clean`, `weak`, `tail_supported`, `ambiguous_nearby` |
| `seed_support_level` | enum | `strong`, `moderate`, or `weak` |
| `duplicate_context` | enum | `none`, `same_owner_events`, or `tail_assignment` |
| `score` | integer | deterministic score used only after hard gates pass |
| `reason` | string | compact human-readable explanation |

The exact score weights belong in the implementation plan, but the first plan
must include a rule table and synthetic tests for each decision transition.

### Edge Decisions

| Decision | Meaning | Production behavior |
|---|---|---|
| `strong_edge` | hard gates pass and drift-corrected RT/owner evidence is strong | may merge into one family |
| `weak_edge` | hard gates pass but drift or owner evidence is insufficient | review only; do not auto-merge |
| `blocked_edge` | hard gates fail or identity depends only on backfill/raw wide RT | do not merge |

Raw RT proximity can nominate comparisons, but it cannot be the merge reason.

Minimum v1 decision rules:

| Condition | Decision |
|---|---|
| any hard gate fails | `blocked_edge` |
| hard gates pass and edge relies on rescued/backfilled support | `blocked_edge` |
| hard gates pass, drift prior is absent, and raw RT exceeds existing strict owner RT tolerance | `weak_edge` |
| hard gates pass, drift-corrected RT is close under the implementation-plan threshold, and owner/seed support are not weak | `strong_edge` |
| hard gates pass but owner quality or seed support is weak | `weak_edge` |
| hard gates pass but drift evidence is missing or contradictory | `weak_edge` |

The implementation plan must replace "close" and "weak" with numeric
thresholds or enum rules before implementation starts.

## Validation

### Baseline Artifacts

The implementation plan must bind validation to explicit baseline artifacts
before changing behavior.

Required baseline references:

| Scope | Baseline artifact |
|---|---|
| 8 RAW alignment | `output\alignment\semantics_cleanup_8raw_20260511` |
| 8 RAW raw trace cases | `output\alignment\semantics_cleanup_8raw_20260511\raw_trace_inspection` |
| targeted 8 RAW workbook | `C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1151.xlsx` |
| targeted 85 RAW workbook | `C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1200.xlsx` |
| sample metadata | `C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\SampleInfo.xlsx` |

If any baseline artifact is missing, validation must stop and report the missing
path rather than silently substituting another run.

### Layer 1: 8-RAW Fast Loop

Real-data validation must use 8 RAW workers for alignment runs:

```text
workers = 8
```

The command or run metadata must prove that 8 workers were requested. If the CLI
or local environment cannot run 8 workers, the validation result is `SKIP` with
the exact reason, not `PASS`.

The 8-RAW run must write:

- timing JSON;
- `alignment_review.tsv`;
- `alignment_cells.tsv`;
- targeted GT audit for `5-medC`;
- targeted GT audit for `5-hmdC`;
- negative audit for `8-oxodG`;
- case1-4 raw trace inspection summary.

Expected outcomes:

| Metric | Source | Pass rule |
|---|---|---|
| `5-medC` SPLIT count | targeted GT audit comparison CSV | `new_split <= baseline_split` |
| `5-medC` MISS count | targeted GT audit comparison CSV | `new_miss <= baseline_miss` |
| `5-hmdC` SPLIT count | targeted GT audit comparison CSV | `new_split <= baseline_split` |
| `5-hmdC` MISS count | targeted GT audit comparison CSV | `new_miss <= baseline_miss` |
| `8-oxodG` accepted production families | post-run negative audit | `0` |
| duplicate cleanup timing | edge/owner debug output and `alignment_cells.tsv` | same-peak/tail duplicates should be represented as owners/supporting evidence before claim-registry cleanup |
| worker count | command log, timing JSON, or run metadata | requested worker count is `8` |

For 8 RAW, a reduction in SPLIT is a success signal, but the non-regression rule
is the hard gate. If SPLIT is unchanged and MISS does not increase, the run is
allowed to proceed only if case1-4 diagnostics show no over-merge.

`8-oxodG` is a post-run audit assertion. Production alignment code must not read
or branch on `target_label == "8-oxodG"` or any target-label alias.

### Layer 2: Case-Based Qualitative Gate

| Case | Expected behavior |
|---|---|
| Case 1 | repeated events and drifted owners should form fewer production families |
| Case 2 | doublet/multiplet evidence remains ambiguous or split; no forced merge |
| Case 3 | drifted clean owners should not split solely due to raw RT shift |
| Case 4 | tail/shadow events become supporting/debug evidence, not extra rows |

The implementation plan must translate each case into at least one synthetic or
artifact-backed assertion before implementation. Visual SVG review may support
the decision, but it cannot be the only evidence.

### Layer 3: 85-RAW Guardrail

After the 8-RAW loop passes, run 85 RAW with the same worker policy.

85-RAW acceptance is comparative, not perfection-based:

| Metric | Source | Pass rule |
|---|---|---|
| `5-medC` SPLIT count | targeted GT audit comparison CSV | `new_split <= baseline_split` |
| `5-medC` MISS count | targeted GT audit comparison CSV | `new_miss <= baseline_miss` |
| `5-hmdC` SPLIT count | targeted GT audit comparison CSV | `new_split <= baseline_split` |
| `5-hmdC` MISS count | targeted GT audit comparison CSV | `new_miss <= baseline_miss` |
| `8-oxodG` accepted production families | post-run negative audit | `0` |
| duplicate-only families | alignment review/cells derived metric | `new_count <= baseline_count` |
| zero-present families | alignment review/cells derived metric | `new_count <= baseline_count` |
| high-backfill-dependency families | alignment review warning/derived metric | `new_count <= baseline_count` |
| worker count | command log, timing JSON, or run metadata | requested worker count is `8` |
| timing | timing JSON | recorded; no hard runtime pass/fail in this correctness pass |

The implementation plan must define the exact derivation for duplicate-only,
zero-present, and high-backfill-dependency counts from the available TSV fields
before running 85 RAW.

## Stop Conditions

Stop and revisit the design if:

- positive target fixtures improve only because target labels were used in
  production merge logic;
- `8-oxodG` becomes an accepted production family;
- broad raw RT proximity becomes sufficient to merge;
- rescued/backfilled cells bridge two detected groups;
- 8-RAW validation improves while case2-like doublets are over-collapsed;
- 85-RAW introduces any accepted `8-oxodG` production family;
- 85-RAW increases any baseline guardrail metric listed above unless the user
  explicitly accepts the tradeoff after inspecting the evidence.

## Next Step

After user review of this spec, write an implementation plan.

### Plan Inputs

The implementation plan should assume these initial module boundaries unless
repo exploration proves a better local fit:

| Responsibility | Likely module |
|---|---|
| drift evidence adapter | new `xic_extractor/alignment/drift_evidence.py` |
| edge evidence model and scoring | new `xic_extractor/alignment/edge_scoring.py` |
| owner pair clustering integration | `xic_extractor/alignment/owner_clustering.py` |
| sample-local duplicate ownership | `xic_extractor/alignment/ownership.py` |
| edge/debug TSV output if needed | `xic_extractor/alignment/debug_writer.py` |
| CLI wiring for metadata paths | `scripts/run_alignment.py` |
| targeted GT post-run audits | `tools/diagnostics/targeted_gt_alignment_audit.py` or a new diagnostics wrapper |

These are planning inputs, not pre-approved code changes. The plan must still
read current module boundaries before editing.

The implementation plan must list:

- exact modules to modify;
- synthetic tests for edge gates and drift evidence;
- real-data commands using 8 workers;
- targeted GT audit commands for `5-medC`, `5-hmdC`, and `8-oxodG`;
- expected artifact paths and comparison metrics.
