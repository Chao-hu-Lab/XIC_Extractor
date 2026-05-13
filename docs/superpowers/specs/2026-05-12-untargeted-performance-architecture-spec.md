# Untargeted Performance Architecture Spec

> **For future agents:** This is the repo-local replacement for
> `C:\Users\user\.claude\plans\untargeted-45-min-target-workers-tidy-phoenix.md`.
> The Claude-local file mixed valid optimization direction with non-repo-native
> ideas such as `.mzML` conversion and Parquet caching. This version is the
> implementation contract for this repo.

**Status:** Phase 0 timing implemented; alignment optimization follow-up active
**Date:** 2026-05-12
**Branch:** `codex/untargeted-discovery-v1-implementation`
**Worktree:** `C:\Users\user\Desktop\XIC_Extractor\.worktrees\untargeted-discovery-v1-implementation`

---

## Summary

The untargeted discovery + alignment workflow has been observed to take more
than 45 minutes on real batches. The targeted extraction workflow is faster in
part because it already has a Windows-safe per-RAW `ProcessPoolExecutor`
backend.

This spec adopts the transferable parts of the targeted pipeline and external
LC-MS performance patterns:

- measure first with cheap stage timing,
- parallelize sample-independent RAW work,
- only optimize O(n^2) grouping if timing proves it is hot,
- avoid new data formats or dependency stacks without direct evidence.

This spec does **not** approve converting Thermo `.raw` files to `.mzML`,
adding Parquet caches, adding Polars, or introducing distributed frameworks.

## Current Facts

| Area | Current state | Evidence |
|---|---|---|
| Targeted parallelism | Uses `ProcessPoolExecutor` with Windows `spawn`; one job per RAW file | `xic_extractor/extraction/jobs.py`, `xic_extractor/extraction/process_backend.py` |
| Targeted config | `ExtractionConfig.parallel_mode` and `parallel_workers` already exist | `xic_extractor/configuration/models.py` |
| Discovery batch execution | Serial loop over RAW files | `xic_extractor/discovery/pipeline.py` |
| Discovery RAW access | Thermo `.raw` via `raw_reader.open_raw()` | `xic_extractor/discovery/pipeline.py`, `xic_extractor/raw_reader.py` |
| Discovery family grouping | Per-sample grouping only; not a cross-sample synchronization point | `xic_extractor/discovery/feature_family.py` requires same `raw_file` and `sample_stem` |
| Alignment synchronization | Cross-sample work lives in alignment ownership/backfill/claim registry | `xic_extractor/alignment/pipeline.py`, `xic_extractor/alignment/claim_registry.py` |
| `.mzML` policy | Existing plans explicitly avoid converting `.raw` to `.mzML` | `docs/superpowers/specs/2026-05-06-numofinder-inspired-ms2-evidence-and-discovery-spec.md` |

## Boundary

The 45-minute runtime must be decomposed into two separately measured surfaces:

1. **Discovery:** RAW -> per-sample `discovery_candidates.csv`,
   `discovery_review.csv`, and batch index.
2. **Alignment:** discovery batch index + RAW files -> alignment artifacts.

Do not mix these into one optimization target. Discovery and alignment fail,
scale, and parallelize differently.

## Accepted Direction

### Phase 0: Stage Timing Foundation

**Goal:** Produce cheap, machine-readable timing for discovery and alignment
without changing scientific output.

**Create:**

- `xic_extractor/diagnostics/timing.py`

**Modify:**

- `xic_extractor/discovery/pipeline.py`
- `xic_extractor/discovery/feature_family.py`
- `xic_extractor/alignment/pipeline.py`
- `scripts/run_discovery.py`
- `scripts/run_alignment.py`

**Timing stages:**

- Discovery:
  - `discover.ms2_seeds`
  - `discover.group_seeds`
  - `discover.ms1_backfill`
  - `discover.feature_family`
  - `discover.write_candidates_csv`
  - `discover.write_review_csv`
  - `discover.write_batch_index`
- Alignment:
  - `alignment.read_batch_index`
  - `alignment.read_candidates`
  - `alignment.open_raw_sources`
  - `alignment.build_owners`
  - `alignment.cluster_owners`
  - `alignment.owner_backfill`
  - `alignment.build_matrix`
  - `alignment.claim_registry`
  - `alignment.write_outputs`

**Output contract:**

Use JSON first, not plots:

```json
{
  "run_id": "20260512_153000",
  "pipeline": "discovery",
  "records": [
    {
      "sample_stem": "Sample_A",
      "stage": "discover.ms2_seeds",
      "elapsed_sec": 12.34,
      "metrics": {
        "seed_count": 123
      }
    }
  ]
}
```

**CLI flags:**

- `scripts/run_discovery.py`: `--timing-output PATH`
- `scripts/run_alignment.py`: `--timing-output PATH`

**Acceptance criteria:**

- Timing disabled by default has negligible overhead.
- Enabling timing does not change any output CSV/TSV/XLSX content.
- Sum of measured stage times is close enough to the CLI wall time to identify
  the dominant bottleneck; exact equality is not required because IO and setup
  happen outside stage scopes.
- Unit tests cover nested stages, exception handling, disabled recorder behavior,
  and JSON serialization.

### Phase 1: Discovery Per-RAW Process Backend

**Prerequisite:** Phase 0 shows that per-sample discovery work, especially MS2
seed collection and MS1 backfill, is a meaningful fraction of total runtime.

**Goal:** Add a discovery process backend modeled after targeted extraction,
with serial fallback.

**Create:**

- `xic_extractor/discovery/process_backend.py`
- `xic_extractor/discovery/jobs.py`

**Modify:**

- `xic_extractor/discovery/pipeline.py`
- `xic_extractor/discovery/models.py`
- `scripts/run_discovery.py`
- `tests/test_discovery_pipeline.py`
- `tests/test_run_discovery.py`

**Design:**

- Job payload contains only pickleable values:
  - raw index,
  - raw path,
  - `DiscoverySettings`,
  - `ExtractionConfig`.
- Worker opens the RAW file inside the child process.
- Worker runs the complete per-sample discovery path:
  - `_discover_raw_file()`
  - `assign_feature_families()`
- Main process preserves input RAW order, writes per-sample CSVs, and writes the
  batch index.
- `parallel_mode="serial"` remains the default until real-data validation proves
  process mode is stable enough to promote.

**Why feature family belongs in the worker:**

`xic_extractor.discovery.feature_family` only groups candidates that share the
same `raw_file`, `sample_stem`, and `neutral_loss_tag`. It is not a cross-sample
synchronization point, so keeping it in the worker reduces main-process CPU
work and avoids an unnecessary serial bottleneck.

**Do not:**

- Do not pass open RAW handles, numpy arrays, or callables across process
  boundaries.
- Do not parallelize by seed, group, or feature family; Windows spawn overhead
  makes that granularity too small.
- Do not change scoring, MS2 matching, MS1 peak detection, grouping semantics,
  or CSV schemas.

**Acceptance criteria:**

- Serial and process mode produce byte-equivalent discovery CSVs for the same
  ordered input RAW files.
- Worker exceptions are surfaced with the RAW file name.
- `--parallel-mode serial|process` and `--parallel-workers N` are validated in
  the discovery CLI.
- One-sample process mode with `--parallel-workers 4` exits cleanly.
- Performance target is based on the measured parallelizable fraction from
  Phase 0, not a hardcoded `serial * 0.4` rule.

### Phase 2: Discovery Feature-Family Indexing, Only If Hot

**Prerequisite:** Phase 0 or Phase 1 timing shows
`discover.feature_family` remains a material bottleneck after per-RAW
parallelism.

**Goal:** Replace the current O(n^2)-style family matching with a narrow
candidate index while preserving exact grouping semantics.

**Modify:**

- `xic_extractor/discovery/feature_family.py`
- `tests/test_discovery_feature_family.py`

**Design constraints:**

- Keep the existing public function `assign_feature_families()`.
- Candidate indexing must include neighboring buckets so boundary candidates are
  not missed.
- Equivalence is defined by family membership, not necessarily by internal
  temporary ordering.
- If the indexed algorithm cannot be proven equivalent, keep the current
  implementation.

**Acceptance criteria:**

- Existing tests pass unchanged.
- New tests cover empty input, single candidate, bucket boundary cases, RT
  boundary cases, and duplicate/overlap cases.
- A characterization fixture proves legacy and indexed family memberships match
  on representative synthetic data.
- No scoring or review-priority behavior changes.

## Explicitly Not Approved

These came from external performance research but are not approved for this
repo's current implementation path:

- `.raw` to `.mzML` conversion.
- `.mzML` to Parquet cache.
- mzMLb adoption.
- Polars migration.
- pandas migration, because the current production dependency set does not use
  pandas for the discovery hot path.
- Dask, Ray, or any distributed execution framework.
- GPU peak picking.
- Numba, unless Phase 0/1/2 timing proves one pure-Python loop still dominates
  and the function can be isolated cleanly.

Reason: the repo intentionally reads Thermo `.raw` through `raw_reader.open_raw()`.
Adding a new data format or table engine would expand deployment and validation
surface before proving that the current bottleneck needs it.

## Relationship To Alignment Correctness Work

This spec does not fix duplicate activation, RT drift, or alignment family
fragmentation. Those are correctness/modeling problems covered by:

- `C:\Users\user\.claude\plans\spec-plan-untarget-alignment-local-mini-nested-mountain.md`

The only alignment change in this spec is timing instrumentation. Optimizing
or removing `claim_registry`, changing `_owner_relation`, or introducing
ISTD-based drift correction belongs to the alignment correctness plan, not this
performance plan.

## Verification Strategy

Use increasing validation scopes:

1. Unit tests with fake RAW sources and synthetic candidates.
2. Single RAW smoke run with timing enabled.
3. 8-RAW validation subset, serial vs process CSV diff.
4. Full batch timing run only after narrow checks pass.

For each real-data validation, record:

- command,
- branch and commit,
- worker count,
- wall-clock time,
- timing JSON path,
- output directory,
- whether serial/process outputs matched.

## Stop Conditions

Stop and revisit the plan if any of these happen:

- Phase 0 shows alignment dominates and discovery is not the main bottleneck.
- Process mode changes CSV output content.
- Worker memory use makes 4 workers unsafe on the validation machine.
- Feature-family indexing cannot be made equivalent to legacy grouping.
- Any proposed optimization requires `.raw` conversion or new heavy dependencies.

## Original Next Step

Write an implementation plan for Phase 0 only:

- timing recorder,
- discovery timing CLI flag,
- alignment timing CLI flag,
- unit tests,
- one real-data timing report.

Do not implement Phase 1 or Phase 2 until Phase 0 has produced a timing report.
This instruction is historical; the addendum below records the measured Phase 0
outcome and the active follow-up direction.

## 2026-05-12 Timing Addendum

Phase 0 timing on the 8-RAW validation subset showed alignment dominates the
measured workflow. Discovery should not be the next optimization target unless
a later full-batch run contradicts this result.

Measured alignment results:

| Mode | Top-stage total | `build_owners` | `owner_backfill` | Notes |
|---|---:|---:|---:|---|
| serial full backfill | 115.48s | 58.74s | 54.64s | baseline |
| `--raw-workers 8` full backfill | 41.11s | 21.17s | 19.05s | fastest full-output setting observed on 8 RAW |
| serial `--owner-backfill-min-detected-samples 2` | 83.94s | 55.61s | 27.12s | low-hardware fast mode; output statuses differ |
| `--raw-workers 8 --owner-backfill-min-detected-samples 2` | 29.29s | 16.11s | 12.51s | fastest observed with explicit completeness tradeoff |

Accepted follow-up direction:

- Keep `--raw-workers 8` as the current fast validation setting.
- Keep full owner backfill as the default output contract.
- Add `--owner-backfill-min-detected-samples N` as an explicit fast-mode knob
  for hardware-constrained users.
- Treat `N > 1` as a completeness tradeoff: rows remain present, but some
  previously rescued cells become absent because low-support features are not
  backfilled across every missing sample.

Rejected follow-up direction:

- Do not replace owner-build RAW extraction with discovery CSV MS1 peak fields
  by default. A prototype reduced `build_owners` RAW calls, but changed the
  feature set on the 8-RAW subset, so it is not an equivalent optimization.

## 2026-05-13 RAW XIC Throughput Addendum

The RAW XIC batching plan was executed against the 8-RAW validation subset.
Machine TSV outputs stayed equivalent, but the timing result did not justify a
default batch-size change by itself.

Measured exact-output runs:

| Mode | `build_owners` calls | `owner_backfill` calls | `build_owners` elapsed | `owner_backfill` elapsed | Output hash |
|---|---:|---:|---:|---:|---|
| `--raw-xic-batch-size 1` | 3343 | 3466 | 64.98s | 70.15s | baseline |
| unsorted `--raw-xic-batch-size 64` | 3343 | 3317 | 65.64s | 67.75s | match |
| sorted `--raw-xic-batch-size 64` | 3343 | 2951 | 66.72s | 62.89s | match |
| `--raw-xic-batch-size 100000` upper bound | 3343 | 2944 | 65.29s | 59.69s | match |

Interpretation:

- `build_owners` has almost no reusable scan-window locality on this subset.
  Batching cannot reduce its true Thermo `GetChromatogramData()` call count.
- `owner_backfill` has enough locality to benefit from sorting pending requests
  by RT window before chunking. This is an exact scoped optimization because
  rescued cells are still emitted in the original feature-major order.
- The sorted `batch64` run reaches nearly the same backfill call count as the
  per-sample upper bound, without sending unbounded settings arrays to Thermo.
- This is still not a complete low-hardware solution because the dominant
  `build_owners` stage remains one vendor XIC call per candidate.

Rejected exact-output shortcuts:

- Directly reusing discovery CSV MS1 peak fields for owner build changed the
  feature set on the 8-RAW subset (`alignment_review.tsv` row count changed
  from 728 to 1096), so it is not an equivalent optimization.
- A local MS1 scan-index prototype was faster for one RAW file
  (`377` vendor XIC calls took `6.408s`; scan index plus local extraction took
  about `1.723s`) but did not reproduce vendor intensities exactly. Peak status
  matched for `375/377` candidates, median area relative difference was about
  `2.13%`, and worst-case area drift was much larger. Treat this only as a
  future explicit approximate fast mode unless a stricter equivalence method is
  found.

Current conclusion:

- Keep the exact pipeline on Thermo vendor XIC calls.
- Keep `--raw-xic-batch-size` as an explicit tuning knob; do not raise its
  default based on this subset alone.
- Keep the owner-backfill RT-window sort because it is exact, localized, and
  improves the only stage where batching has useful locality.
- Future performance work should not spend more time on larger batch sizes or
  discovery-field reuse. The remaining meaningful paths are either an explicit
  approximate MS1-index mode, or a modeling-level reduction in owner-build
  candidate count with its own equivalence/acceptance criteria.

Important framing: exact equality to the current alignment output is a
regression guard, not the final scientific acceptance criterion. The alignment
algorithm is still in flux, and current distinctions such as `backfill` versus
`absent` are not guaranteed to be the final product contract. Non-equivalent
changes remain valid candidates when they are intentional model changes with
explicit output semantics, validation artifacts, and acceptance criteria.

### 2026-05-13 Locality And MS1-Index Diagnostics

Two repeatable validation scripts now support the next decision:

- `scripts/analyze_xic_request_locality.py`
- `scripts/validate_ms1_scan_index_xic.py`

The 8-RAW locality report was written to:

- `output\diagnostics\xic_request_locality_8raw.json`

Measured locality:

| Stage | Requests | Original batch64 calls | Sorted batch64 calls | Per-sample upper bound |
|---|---:|---:|---:|---:|
| `build_owners` | 3343 | 3343 | 3343 | 3343 |
| `owner_backfill` artifact estimate | 3333 | 3198 | 2874 | 2867 |

The `owner_backfill` analyzer reconstructs requests from final alignment
artifacts, so its absolute count is an estimate rather than a substitute for
runtime timing. Its direction matches the measured timing run: backfill has
usable scan-window locality after sorting, while `build_owners` has none.

The single-RAW MS1-index validation report was written to:

- `output\diagnostics\ms1_scan_index_validation_1raw.json`

Measured against `BenignfatBC1055_DNA` with 377 requests:

| Metric | Value |
|---|---:|
| Vendor XIC extraction | 6.449s |
| MS1 index build | 1.611s |
| Local index extraction | 0.284s |
| RT grid match | 377/377 |
| Peak status match | 375/377 |
| Apex within 0.01 min | 352/374 peak pairs |
| Apex within 0.05 min | 361/374 peak pairs |
| Median area relative delta | 2.13% |
| P95 area relative delta | 13.93% |
| Max area relative delta | 714.79% |

Conclusion:

- MS1 scan indexing has real speed potential.
- It is not equivalent to Thermo vendor XIC on the validation subset.
- This does not reject MS1 indexing as a future direction. It only means it
  should not be presented as the same algorithm with the same output contract.
- If implemented before the alignment model is finalized, it should be framed
  as a deliberate fast-mode or next-model variant with visible output semantics,
  validation notes, and downstream acceptance criteria.
- Exact optimization work can still keep the already-validated backfill
  locality sort. Larger gains should be evaluated as model-level changes, such
  as reducing owner-build candidate count or replacing vendor XIC with a local
  MS1-indexed extraction path.
