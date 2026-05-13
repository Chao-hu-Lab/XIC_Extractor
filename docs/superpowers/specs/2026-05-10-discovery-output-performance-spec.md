# Discovery Output Performance and Candidate Budget Spec

## Summary

Untargeted discovery will naturally produce more candidates than targeted XIC extraction. Raw file reading, XIC construction, and MS2 scan traversal remain hard costs for now and should primarily be handled by parallel raw-file workers. This spec focuses on the costs that are easier to control without changing scientific detection logic:

- Candidate count growth after MS2 seed extraction and MS1 backfill.
- In-memory sorting, grouping, scoring, and row formatting.
- Output IO volume from full CSV, brief review CSV, batch index, and future diagnostic artifacts.

The goal is not to hide evidence or prematurely prune scientifically meaningful candidates. The goal is to make discovery output scalable by measuring stage costs, separating output levels, and making row-volume tradeoffs explicit.

## Problem

Discovery output has two competing needs:

- Developers need complete provenance to debug scoring, grouping, and future alignment.
- Users need compact review surfaces that do not drown them in rows and columns.

If every run always writes every possible artifact, the workflow can become slow, disk-heavy, and hard to inspect. This is especially risky for full batches, because row count can grow with both sample count and MS2 event density.

## Goals

- Add performance visibility for discovery runs without changing candidate semantics.
- Track candidate volume by pipeline stage, sample, priority, tier, and output artifact.
- Support output levels so users can choose fast iteration, normal review, or full debug output.
- Keep archival full candidate CSV available when the run is intended for downstream alignment.
- Avoid default HTML, plots, Excel, or other expensive renderers in discovery v1.
- Make future optimization decisions data-driven instead of based on intuition.

## Non-Goals

- Do not optimize Thermo RawFileReader access in this spec.
- Do not change XIC extraction, MS2 seed matching, MS1 peak detection, scoring weights, or grouping semantics.
- Do not implement cross-sample alignment.
- Do not add GUI controls in the first implementation.
- Do not remove existing full CSV columns.
- Do not make lossy row filtering the default behavior.

## Core Concepts

### Output Levels

Discovery should support an explicit output level. This is a user-facing concept, while detailed writer flags remain developer-facing.

| Level | Purpose | Outputs | Contract |
|---|---|---|---|
| `minimal` | Fast iteration and smoke checks | batch index plus per-sample `discovery_review.csv` | Not archival. May omit full provenance CSV. |
| `standard` | Default human review plus downstream handoff | batch index, per-sample `discovery_review.csv`, per-sample `discovery_candidates.csv` | Default. Full candidate CSV remains alignment-ready. |
| `debug` | Method development and regression investigation | all `standard` outputs plus optional diagnostics/metrics details | Slower and larger by design. |

`standard` should remain the default for normal discovery runs because it preserves both UX and downstream provenance. `minimal` is useful when checking whether a batch is viable before paying full output cost.

### Performance Metrics

Discovery should emit a lightweight metrics artifact when enabled. The first version should be cheap and text-based, for example `discovery_run_metrics.csv` or `discovery_run_metrics.json`.

Metrics should include:

- `raw_file`
- total runtime
- MS2 seed extraction time
- MS1 backfill time
- feature family assignment time
- evidence scoring and sorting time
- CSV write time by artifact
- candidate count before and after grouping
- candidate counts by `review_priority`
- candidate counts by `evidence_tier`
- output file sizes
- peak memory if it can be measured cheaply on Windows

Timing should use monotonic clocks. Metrics collection must not require real-data post-processing tools.

### Candidate Budget

Candidate budget is an observability and warning mechanism first, not a pruning mechanism.

The initial implementation should report:

- candidates per raw file
- candidates per minute of RT
- candidates per priority/tier
- superfamily representatives vs members
- largest feature/superfamily sizes
- number of rows written to each output file

Warnings can be emitted when a sample exceeds configurable soft limits, such as:

- unusually high candidate count
- unusually high LOW-priority fraction
- unusually high member-to-representative ratio
- unusually large output file

These warnings should not delete candidates. If lossy export limits are added later, they must be opt-in and clearly marked as non-archival.

## Output Surface

### Brief Review CSV

The brief review CSV should be the default human entry point. It should contain enough information to answer:

- Should I inspect this row?
- Why is it ranked here?
- How do I locate it in the full CSV or Xcalibur?

It should not contain every numeric diagnostic. Full diagnostic and alignment fields belong in `discovery_candidates.csv`.

### Full Candidate CSV

The full CSV remains the archival and alignment-ready output. It can grow wider over time through appended provenance columns, but review-first columns should stay stable.

### Batch Index

The batch index should become the navigation surface for multi-RAW output. It should include paths to per-sample review and full candidate CSVs, row counts, priority counts, tier counts, and output sizes.

### HTML and Plots

HTML reports and plots should remain opt-in for discovery. They are useful when the visualization adds information that CSV cannot provide, but they should not be emitted by default for every sample.

## Developer Controls

Developer-facing controls may exist in Python settings or CLI hidden/advanced flags, but normal users should primarily see:

- `--output-level minimal|standard|debug`
- optional `--emit-discovery-metrics`

Detailed writer flags, row budgets, and diagnostic toggles should not become the normal user surface until real runs show they are needed.

## Performance Design Rules

- Prefer one candidate model in memory; avoid generating separate full and brief row models unless needed.
- Reuse the same sorted candidate order for all CSV outputs.
- Stream CSV writing with `csv.DictWriter`; avoid building large intermediate row lists for writing.
- Avoid expensive formatting in hot loops unless it is required by the output contract.
- Do not write plots or HTML from per-sample discovery by default.
- Use metrics to identify bottlenecks before changing algorithms.

## Validation Strategy

Use three run sizes:

- Single RAW: verifies metrics and output-level behavior quickly.
- 8-RAW validation subset: checks practical runtime and output readability.
- 85-RAW full batch: confirms scaling behavior before changing defaults.

For each run, record:

- wall-clock runtime
- output size by artifact
- row counts by artifact
- candidate counts by priority and tier
- whether full CSV row count matches review CSV row count in `standard` and `debug`

The first implementation should not require the 85-RAW run to pass unit tests. Full-batch validation is a manual or harness-level check.

## Acceptance Criteria

- Discovery output level is specified clearly and defaults to `standard`.
- `minimal` output avoids writing full provenance CSV while preserving a reviewable batch.
- `standard` output preserves the existing full candidate CSV contract.
- Metrics make candidate explosion and output IO costs visible per sample.
- No scoring, peak detection, MS2 matching, or feature grouping behavior changes are introduced by this performance layer.
- Real-data validation can compare output size and timing across `minimal`, `standard`, and `debug`.

## Open Questions

- Should `minimal` write all review rows or only a top-N review subset with summary counts?
- Should metrics always be emitted in `debug`, or remain a separate flag?
- Should candidate budget warnings appear in the batch index, a metrics file, or both?
- Should future row limiting be applied only to review CSV, never to full CSV?
- Should output-level config eventually be shared with targeted extraction, or remain discovery-specific?

