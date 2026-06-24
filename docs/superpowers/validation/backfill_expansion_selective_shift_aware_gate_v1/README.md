# Backfill Expansion Selective Shift-Aware Gate v1

Status: `diagnostic_only_selective_gate_replay`.

This artifact replays the current 666-cell Backfill expansion candidate packet
with a PeakHypothesis-first selective shift-aware rule. It does not read RAW
files and does not grant ProductWriter authority.

## What Changed Methodologically

The old family-wide question was:

```text
Does the whole feature family pass the shift-aware standard-peak gate?
```

This diagnostic asks a narrower question:

```text
Does this source_family / sample cell point to the selected hypothesis?
```

That means weak source families no longer block unrelated strong source
families in the same hypothesis, but they also do not get silently filled.

## Current Result

Default diagnostic thresholds:

- selective support: source-family best-shift shape r `>= 0.90`;
- attention only: source-family best-shift shape r `>= 0.85` and `< 0.90`;
- own-max threshold: `> 0.5`.

Current 666-cell replay:

- `491/666` cells pass the selective diagnostic evidence gate;
- `175/666` cells remain held;
- `628/666` cells have source-family shift support;
- `496/666` cells still have own-max support;
- `11` cells are attention-only by source-family shift;
- `27` cells are not same-hypothesis by source-family shift;
- `130` cells are primarily held by below-threshold own-max;
- `7` cells are primarily held by missing own-max.

## Calibration Cases

- `FAM020411`: the old whole-family gate held the family because its weakest
  source-family r was `0.8791`. The selective replay correctly keeps
  high-support source families (`FAM020407`, `FAM020412`, `FAM020408`) and
  yields `25/40` diagnostic-pass cells. The remaining cells are held mostly by
  own-max or attention-only source-family support.
- `FAM017098`: all current candidate cells are mapped to `source_family=FAM017089`
  with source-family best-shift r `0.6086`. The diagnostic therefore holds all
  11 cells. This does not prove the 15-min hypothesis is false; it proves the
  current source-family mapping does not yet capture the user-reviewed
  15-min anchor. The next method step should be an anchor remap/review for this
  case, not automatic ProductWriter activation.
- `FAM012491` and `FAM016893`: both become mostly supported under selective
  source-family gating, but remaining cells are still governed by own-max and
  attention-only holds.

## Authority Boundary

This artifact is evidence for a future expected-diff design only.

It writes:

- compact summary/checks/row manifest under `docs/superpowers/validation/`;
- full 666-cell diagnostic TSV under `output/validation/`.

It does not change:

- default quant matrix;
- workbook or GUI;
- selected peak, selected area, or counted detection;
- active product tier;
- active writer lane;
- ProductWriter authority.
