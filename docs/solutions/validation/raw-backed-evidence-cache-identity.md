---
title: "RAW-backed evidence cache identity"
date: "2026-06-29"
category: "validation"
module: "standard-peak"
status: "current"
tags: ["raw-validation", "evidence-cache", "standard-peak", "fail-closed"]
source_refs:
  - "tools/diagnostics/INDEX.md"
  - "docs/agent-parameter-settings.md"
  - "docs/superpowers/plans/2026-06-15-productization-control-plane.md"
  - "output/performance/family_abstraction_final_8raw_validation_20260629/timing.json"
---

# RAW-backed Evidence Cache Identity

## When To Read

Read this before adding or accepting a cache, replay, or reuse path that skips
RAW re-extraction while feeding evidence into standard-peak, overlay, backfill,
or product-adjacent validation.

## Problem

The standard-peak evidence cache was keyed by stable request inputs and path
strings, but a RAW file at the same path can be replaced or point to a different
resolved target. Reusing cached trace evidence in that case would make the run
look faster while silently proving the wrong data.

## Tempting Wrong Path

Treating a cache as safe because it is opt-in, path-scoped, or method-development
only is not enough. A stale cache can still influence review replay and product
candidate evidence. Full RAW hashing is also too expensive for the hot path, so
the answer is not to read every RAW byte before every cache hit.

## Working Pattern

Bind each reusable trace row to the current per-sample RAW identity and fail
closed when identity is missing or mismatched.

For the current implementation, cache schema v4 records `path_stat_v1` identity:
the requested path, resolved path, file size, mtime, device, and inode. Cache
hits validate the cached trace payload, stable provenance, and current RAW
identity before reuse. Manifest fallback and cache seeding use the same rule.
When validation fails, the runner falls back to normal RAW extraction instead of
reusing stale evidence.

Keep this separate from resume semantics. `--reuse-existing` can still rebuild
from completed local artifacts under its existing contract; the evidence cache
is the path that needs RAW identity binding because it is explicitly reusable
across runs.

## Evidence

- Commands actually run:
  - `.venv\Scripts\python.exe -m scripts.run_alignment --preset dna_dr_product_ready --expected-sample-count 8 --output-level validation-minimal --backfill-scope production-equivalent --audit-evidence-mode none --performance-profile validation-fast --raw-workers 11 --owner-backfill-window-strategy super-window --owner-backfill-superwindow-span-factor 2 ...`
  - Full PR gate was rerun before PR comment reply.
- Artifact paths:
  - `output/performance/family_abstraction_final_8raw_validation_20260629/timing.json`
  - `output/performance/family_abstraction_final_8raw_validation_20260629/product_ready_preset_publication_check/product_ready_preset_publication_summary.json`
  - `output/performance/family_abstraction_final_8raw_validation_20260629/standard_peak_backfill_preset/standard_peak_backfill_preset_summary.json`
- Tests / reviewers:
  - `test_batch_evidence_cache_rejects_replaced_raw_file_identity`
  - `test_batch_evidence_cache_manifest_fallback_rejects_replaced_raw_file_identity`
  - PR review comment on `--standard-peak-evidence-cache-dir`

## Limits

This proves the cache fails closed for same-path RAW replacement and that the
fresh 8RAW validation-minimal run completes with public TSV parity against the
previous branch baseline. It is not a cryptographic RAW-content guarantee and it
does not make the evidence cache a default one-shot production optimization.
Use 85RAW only when a later change needs stress-scale timing or production
readiness evidence.

## Next Time

1. Before adding a RAW-backed cache, state which RAW identity is bound and what
   happens on mismatch.
2. Add one negative test for replaced same-path RAW data and one for manifest or
   fallback reuse.
3. Run 8RAW validation-minimal first when public output fields or product
   candidate evidence changed; do not jump to 85RAW while 8RAW is inconclusive.
