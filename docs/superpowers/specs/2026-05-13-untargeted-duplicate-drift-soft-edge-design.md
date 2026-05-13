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

### Edge Decisions

| Decision | Meaning | Production behavior |
|---|---|---|
| `strong_edge` | hard gates pass and drift-corrected RT/owner evidence is strong | may merge into one family |
| `weak_edge` | hard gates pass but drift or owner evidence is insufficient | review only; do not auto-merge |
| `blocked_edge` | hard gates fail or identity depends only on backfill/raw wide RT | do not merge |

Raw RT proximity can nominate comparisons, but it cannot be the merge reason.

## Validation

### Layer 1: 8-RAW Fast Loop

Real-data validation should use 8 RAW workers when supported by the CLI:

```text
workers = 8
```

The 8-RAW run must write:

- timing JSON;
- `alignment_review.tsv`;
- `alignment_cells.tsv`;
- targeted GT audit for `5-medC`;
- targeted GT audit for `5-hmdC`;
- negative audit for `8-oxodG`;
- case1-4 raw trace inspection summary.

Expected outcomes:

- `5-medC` and `5-hmdC` production-family split decreases;
- `5-medC` and `5-hmdC` miss count does not increase;
- `8-oxodG` does not produce accepted production family;
- duplicate cleanup moves earlier than final duplicate assignment;
- runtime is recorded with workers fixed at 8.

### Layer 2: Case-Based Qualitative Gate

| Case | Expected behavior |
|---|---|
| Case 1 | repeated events and drifted owners should form fewer production families |
| Case 2 | doublet/multiplet evidence remains ambiguous or split; no forced merge |
| Case 3 | drifted clean owners should not split solely due to raw RT shift |
| Case 4 | tail/shadow events become supporting/debug evidence, not extra rows |

### Layer 3: 85-RAW Guardrail

After the 8-RAW loop passes, run 85 RAW with the same worker policy.

85-RAW acceptance is comparative, not perfection-based:

- `5-medC` and `5-hmdC` improve or do not regress relative to baseline;
- `8-oxodG` negative checkpoint remains negative;
- duplicate-only, zero-present, and high-backfill-dependency families decrease;
- timing artifacts are recorded for comparison.

## Stop Conditions

Stop and revisit the design if:

- positive target fixtures improve only because target labels were used in
  production merge logic;
- `8-oxodG` becomes an accepted production family;
- broad raw RT proximity becomes sufficient to merge;
- rescued/backfilled cells bridge two detected groups;
- 8-RAW validation improves while case2-like doublets are over-collapsed;
- 85-RAW introduces large new false-positive families.

## Next Step

After user review of this spec, write an implementation plan.

The implementation plan must list:

- exact modules to modify;
- synthetic tests for edge gates and drift evidence;
- real-data commands using 8 workers;
- targeted GT audit commands for `5-medC`, `5-hmdC`, and `8-oxodG`;
- expected artifact paths and comparison metrics.
