---
title: "Standard-peak best-shift-only no full-run gain"
date: "2026-06-29"
category: "validation"
module: "standard_peak"
status: "current"
tags: ["performance", "standard-peak", "matrix-only", "8raw", "stage-replay"]
source_refs:
  - "tools/diagnostics/family_ms1_alignment_experiment_batch.py"
  - "tools/diagnostics/standard_peak_backfill_machine_pipeline.py"
---

# Standard-Peak Best-Shift-Only No Full-Run Gain

## When To Read

Read this before wiring `family_ms1_alignment_experiment_batch.py
--best-shift-only` into the `standard_peak` matrix-only preset for one-shot
performance.

## Problem

The CLI already supports writing only `*_source_family_best_shift_summary.tsv`
and skipping auxiliary per-row source-family summaries. That looks attractive
because the matrix-only calibration pack consumes best-shift summaries, not the
review/debug auxiliary summaries.

## Tempting Wrong Path

Do not promote the no-RAW stage replay result directly into the full alignment
preset. A local replay over existing overlay trace JSONs improved, but the full
8RAW one-shot run did not improve the target stage.

## Working Pattern

Use `--best-shift-only` as a diagnostic or local replay option when the goal is
to regenerate only best-shift summaries. Do not wire it as the default
matrix-only preset behavior for performance unless a fresh full-run gate proves
the target stage is faster.

## Evidence

- No-RAW replay default:
  `output/performance/standard_peak_shift_aware_default_replay_8raw_20260629`,
  676 rows, 13.546s wall time.
- No-RAW replay with `--best-shift-only`:
  `output/performance/standard_peak_shift_aware_best_shift_only_replay_8raw_20260629`,
  676 rows, 9.201s wall time.
- The 676 best-shift summary TSV files were byte-identical between the two
  replays. The best-shift-only replay skipped 676 source-family summary TSVs
  and 676 source-family shift summary TSVs.
- Full 8RAW candidate:
  `output/performance/standard_peak_best_shift_only_matrix_only_8raw_20260629`.
  Publication summary passed with failed checks 0, `matrix_cells_written=210`,
  `review_queue_row_count=676`, and `authority_changed=FALSE`.
- Public TSV hashes matched the exact baseline for alignment review, matrix,
  matrix identity, backfill cell evidence, seed audit, skipped ledger, and
  standard-peak activation TSVs.
- Full-run timing did not pass the performance gate:
  `standard_peak.shift_aware_batch` 18.903s -> 19.123s and
  `standard_peak.chunk` 26.033s -> 26.742s. The candidate did improve
  `standard_peak.calibration_pack` 3.099s -> 2.403s, but that was not enough to
  improve the target path.

## Limits

This does not prove best-shift-only is useless for repeated local replays or
manual method development. It only rejects wiring it into the one-shot
matrix-only preset as a performance default based on the 2026-06-29 8RAW gate.

## Next Time

1. If considering this again, start with a full-run 8RAW gate, not just no-RAW
   replay timing.
2. Keep `--best-shift-only` available as an explicit diagnostic replay option.
3. Look for standard-peak gains in exact request reuse, process overhead, or
   authority bundle/calibration joins rather than auxiliary TSV removal alone.
