---
title: "Owner-backfill fast-mode negative 8RAW gate"
date: "2026-06-29"
category: "validation"
module: "alignment.owner_backfill"
status: "current"
tags: ["performance", "owner-backfill", "fast-mode", "8raw", "expected-diff"]
source_refs:
  - "tools/diagnostics/dna_dr_product_ready_fast_mode_expected_diff.py"
  - "output/performance/family_abstraction_rt_cache_full_alignment_8raw_20260629"
---

# Owner-Backfill Fast-Mode Negative 8RAW Gate

## When To Read

Read this before trying to speed up `alignment.owner_backfill` by switching to
the MS1 scan-index backends or changing the `super-window` span.

## Problem

The slow 85RAW stress path is dominated by owner-backfill XIC volume, but the
fast-looking alternatives can either increase Thermo RAW call fragmentation or
change public alignment outputs. 8RAW must reject those candidates before they
reach 85RAW.

## Tempting Wrong Path

Do not assume "fewer points" or "MS1 index" means faster. In the 2026-06-29
8RAW pass, smaller windows and scan-index backends either made the target stage
slower or changed matrix/review/cell-evidence outputs.

## Working Pattern

Use the exact RAW backend plus `super-window` span factor 2 as the comparison
baseline, then classify each candidate with:

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.dna_dr_product_ready_fast_mode_expected_diff --exact-dir <exact-dir> --candidate NAME=<candidate-dir> --output-dir <expected-diff-dir>
```

A candidate is not useful unless the public hashes match and
`alignment.owner_backfill` is faster.

## Evidence

- Exact baseline: `output/performance/family_abstraction_rt_cache_full_alignment_8raw_20260629`
- `ms1-index-hybrid`: `diagnostic_only`; public hashes matched, but
  `alignment.owner_backfill` slowed from 14.56s to 64.89s.
- `ms1-index` owner-backfill backend: `diagnostic_only`; public hashes changed,
  matrix rows dropped from 811 to 782, and owner-backfill slowed to 20.22s.
- `owner-build ms1-index`: `diagnostic_only`; public hashes changed, matrix rows
  rose from 811 to 1125, missing/extra matrix cells were 179/208, and
  owner-backfill slowed to 18.57s.
- `super-window` span factor 1: public TSV hashes matched, but raw calls jumped
  from 72 to 17,910 and owner-backfill slowed to 50.55s.
- `super-window` span factor 3: public TSV hashes matched and owner-backfill was
  roughly tied at 14.35s, but point volume rose from 9.16M to 15.62M and the
  result did not clear a useful margin.
- Reviewer check: validation-evidence-reviewer rejected `ms1-index-hybrid` as a
  fast-mode candidate because locality and target-stage timing got worse.

## Limits

This note does not prove all approximate backends are impossible. It only says
these 8RAW candidates should not be wired as defaults and should not be promoted
to 85RAW without a new reason.

## Next Time

1. Start from the exact baseline and rerun the expected-diff packet before any
   85RAW attempt.
2. Prefer reducing duplicated exact RAW work over changing backend semantics.
3. If a new fast mode changes public hashes, treat it as an expected-diff
   product decision, not a performance-only change.
