# Alignment Clustering Performance Spec

**Status:** Tier 0 implemented and verified. Tier 1 and Tier 2 deprioritized —
post-Tier-0 85-RAW timing triggered Stop Condition 4 (`cluster_owners` is no
longer the dominant stage; `owner_backfill` now dominates).
**Date:** 2026-05-15
**Branch:** `codex/algorithm-performance-optimization`
**Worktree:** `C:\Users\user\Desktop\XIC_Extractor\.worktrees\algorithm-performance-optimization`

---

## Summary

`2026-05-12-untargeted-performance-architecture-spec.md` (Phase 0) called for
cheap stage timing before optimizing anything. That timing instrumentation now
exists (`xic_extractor/diagnostics/timing.py`, `recorder.stage(...)` scopes in
`xic_extractor/alignment/pipeline.py`) and has produced 28 `alignment_timing.json`
reports under `output/diagnostics/`.

The timing reports identify a single dominant compute-phase bottleneck:
**`alignment.cluster_owners`** in `xic_extractor/alignment/owner_clustering.py`.
On the 85-RAW drift run it consumes **2,118 seconds (~35 minutes)** in a single
thread. Multi-tag discovery amplifies this further, which is why 85-RAW
multi-tag alignment runs past 60 minutes without writing
`alignment_review.tsv` / `alignment_matrix.tsv` / `alignment_cells.tsv`.

This spec is the direction decision for fixing the clustering compute phase. It
does **not** address `owner_backfill` I/O (a separate, already-parallelized
axis) and does **not** change alignment scientific output semantics — grouping
results must remain equivalent.

## Relationship To Prior Specs

| Spec | Relationship |
|---|---|
| `2026-05-12-untargeted-performance-architecture-spec.md` | Phase 0 (timing) is **done**. This spec is the follow-up the timing report pointed to. Phase 1 (discovery process backend) and Phase 2 (discovery feature-family indexing) remain that spec's scope and are untouched here. |
| `2026-05-13-untargeted-duplicate-drift-soft-edge-design.md` | Owns `evaluate_owner_edge` *scoring semantics*. This spec must not change scoring; it only changes *which pairs* and *how* the scoring is invoked. |
| `spec-plan-untarget-alignment-local-mini-nested-mountain.md` (Claude-local) | Owns alignment *correctness* (duplicate activation, RT drift, family fragmentation). Out of scope here. |

## Timing Evidence

Wall-clock is the `x1` parent stages. The `*.extract_xic` stages are recorded
per-worker (`x8` / `x85`) and summed across workers, so they over-count wall
time and are excluded from this table.

| Run | candidates | **cluster_owners** | owner_backfill | build_owners | write_outputs |
|---|---|---|---|---|---|
| 8-RAW, single-tag, no drift (prefilter **ON**) | 3,343 | **0.8 s** | 17.5 s | 16.0 s | 4.9 s |
| 8-RAW, single-tag, drift (prefilter **OFF**) | 3,343 | **13.6 s** | 17.7 s | 17.7 s | 2.2 s |
| 8-RAW, multi-tag, drift (prefilter **OFF**) | 4,031 | **23.2 s** | 21.4 s | 18.9 s | 3.0 s |
| 8-RAW, multi-tag, drift, **Tier 0 fix** (prefilter **ON**) | 4,031 | **0.4 s** | 23.4 s | 18.3 s | 3.8 s |
| 85-RAW, single-tag, no drift (prefilter **ON**) | 30,289 | **106 s** | 1,574 s | 90 s | 316 s |
| 85-RAW, single-tag, drift (prefilter **OFF**) | 30,289 | **2,118 s** | 672 s | 103 s | 108 s |
| 85-RAW, multi-tag, drift, **Tier 0 fix** (prefilter **ON**) | 39,287 | **68.9 s** | 1,157 s | 146 s | 176 s |

Sources:
`output/diagnostics/final_identity_contract_8raw_20260514/alignment_timing.json`,
`output/diagnostics/final_identity_contract_8raw_drift_20260514/alignment_timing.json`,
`output/alignment/multi_tag_8raw_drift_timing_20260515/timing.json`,
`output/diagnostics/phase_c_scan_window_85raw/alignment_timing.json`,
`output/diagnostics/final_identity_contract_85raw_drift_20260514/alignment_timing.json`.

Observations:

1. **Prefilter on/off is a 17-20x multiplier on `cluster_owners`.** Same 3,343
   candidates, same 8 RAW files: enabling drift (which disables the prefilter)
   moves `cluster_owners` from 0.8 s to 13.6 s. At 85 RAW the same toggle is
   106 s vs 2,118 s.
2. **`cluster_owners` is super-quadratic regardless of the prefilter.** With
   prefilter OFF, 9.06x candidates -> 155x time (~O(n^2.3)). With prefilter ON,
   9x candidates -> 132x time. The prefilter cuts the constant factor; it does
   not change the complexity class.
3. **Multi-tag amplification is measured, not just inferred.** The 8-RAW
   multi-tag drift run carries 4,031 candidates (21% more than the 3,343 of the
   single-tag drift run) but `cluster_owners` rises 71% (13.6 s -> 23.2 s).
   Multi-tag does not get an additive `sum(O(n_i^2))` discount: with the
   prefilter off, cross-tag pairs are still fully evaluated, so the cost is
   `O((sum n_i)^2)` over the combined owner set (see R3). Extrapolating the
   measured ~O(n^2.5) scaling to the reported 85-RAW multi-tag candidate count
   (~39,287) puts `cluster_owners` alone near ~2 hours — which is why 85-RAW
   multi-tag runs never reach the atomic write stage.

## Root Cause

`xic_extractor/alignment/owner_clustering.py`:

### R1. The hot loop is complete-link grouping over all owner pairs

`_complete_link_groups` (line 142) iterates every owner against every existing
group, and for each group against every group member. Every distinct owner pair
eventually reaches `_edge_for_pair` -> `evaluate_owner_edge` once (cached in
`edge_cache`). Distinct pairs = n(n-1)/2 = O(n^2). The complete-link inner
`all(... for existing in group)` adds a further group-size factor, producing the
observed ~O(n^2.3).

`evaluate_owner_edge` (`edge_scoring.py:60`) is not cheap per call: ~8 sub-function
calls plus allocation of a 22-field frozen `OwnerEdgeEvidence` dataclass. At
85-RAW scale this is tens of millions of calls and allocations.

### R2. The cheap prefilter is disabled whenever edge evidence is collected

`owner_clustering.py:152`:

```python
use_group_prefilter = edge_evidence_sink is None
```

`edge_evidence_sink` is non-`None` when either:

- `drift_lookup is not None` (`--sample-info` + `--targeted-istd-workbook`
  passed), or
- `output_level` is `debug` or `validation` (`owner_edge_evidence.tsv` is in the
  artifact set — `output_levels.py`).

When the prefilter is off, `_group_can_pass_hard_gates` (a cheap envelope check:
same-sample reject, NL-tag mismatch reject, m/z out-of-range reject) is skipped,
so the expensive `evaluate_owner_edge` runs for **every** pair, including pairs a
one-line check would have rejected.

### R3. Multi-tag amplification

Owners with different `neutral_loss_tag` can never group (`_hard_gate_failure`
returns `neutral_loss_tag_mismatch`). With the prefilter ON, cross-tag pairs are
rejected cheaply by the envelope, so multi-tag cost is roughly additive:
`sum(O(n_i^2))`. With the prefilter OFF, every cross-tag pair still runs the full
`evaluate_owner_edge` before being blocked, so cost becomes `O((sum n_i)^2)` over
the combined owner set. Multi-tag is therefore not a new problem — it is R2
amplified by the square of the tag count's effect on the combined `n`.

## Boundary

In scope:

- `alignment.cluster_owners` compute phase only
  (`xic_extractor/alignment/owner_clustering.py`, and the numeric core of
  `xic_extractor/alignment/edge_scoring.py`).

Out of scope:

- `alignment.owner_backfill` (672-1,574 s on 85 RAW). It is I/O-bound on Thermo
  RAW chromatogram calls and already parallelized with `raw_workers`. Its
  optimization axis (worker count, `raw_xic_batch_size`, `ms1-index` backend) is
  unrelated to clustering and belongs to the prior performance spec.
- Any change to `evaluate_owner_edge` scoring thresholds, decision logic, or the
  `OwnerEdgeEvidence` field set.
- Alignment correctness (duplicate activation, drift modeling, family
  fragmentation).
- Discovery-stage performance.

## Accepted Direction

Three tiers, strictly ordered. Each tier must land and be verified before the
next is started, because each later tier's benefit is measured on top of the
earlier one.

### Tier 0: Re-enable the prefilter (decouple it from the evidence sink)

**Implemented 2026-05-15.** `_complete_link_groups` in
`xic_extractor/alignment/owner_clustering.py` no longer derives
`use_group_prefilter` from `edge_evidence_sink`; `_group_can_pass_hard_gates`
is always applied. Verified on the 8-RAW multi-tag drift run: `cluster_owners`
23.2 s -> 0.4 s (~58x), `alignment_matrix.tsv` and `alignment_review.tsv`
byte-identical to the pre-fix run, full test suite green (1328 passed). The
correctness argument: complete-link requires an owner to pass the per-pair hard
gate against every group member, including the envelope-extreme members, so a
group the envelope rejects is a group complete-link would reject anyway —
grouping is provably unchanged. Option A is implemented and recorded in
`2026-05-11-untargeted-alignment-output-contract.md`.

**Goal:** The clustering *decision path* always runs `_group_can_pass_hard_gates`,
regardless of whether `edge_evidence_sink` is set.

**Problem to resolve:** Today the prefilter is coupled to `edge_evidence_sink`
because skipping `_edge_for_pair` also skips appending that pair's
`OwnerEdgeEvidence` to the sink. The two concerns must be separated:

- *Clustering decision* — needs only pairs that can plausibly group.
- *Edge evidence TSV* — a `debug` / `validation` diagnostic artifact.

**Design:**

- Always apply `_group_can_pass_hard_gates`.
- Pairs rejected by the envelope are *definitionally* `blocked_edge` with reason
  `same_sample` / `neutral_loss_tag_mismatch` /
  `precursor_mz_out_of_tolerance` — `_hard_gate_failure` would return the same.
  They never need a full `evaluate_owner_edge`.
- **`owner_edge_evidence.tsv` contract (decided: Option A).** Envelope-rejected
  pairs are not written to `owner_edge_evidence.tsv`. This is a documented
  contract change. Rationale: at 85 RAW, the prefilter-OFF behavior would emit
  ~hundreds of millions of trivially-blocked rows — an unusable artifact. The
  TSV's new contract is "all owner pairs that survived the hard-gate envelope,"
  which is the set actually worth debugging. The previous behavior (every pair,
  including trivially-blocked ones) was an accident of the prefilter being
  coupled to the evidence sink, not an intentional contract.

**Acceptance criteria:**

- `cluster_owners` timing on the 8-RAW drift run drops to within ~2x of the
  8-RAW no-drift run (target: from 13.6 s toward ~1 s).
- `cluster_owners` timing on an 85-RAW drift run drops from ~2,118 s to the same
  order as the 85-RAW no-drift run (~106 s).
- `alignment_review.tsv` / `alignment_matrix.tsv` / `alignment_cells.tsv` are
  byte-identical between prefilter-ON and the previous prefilter-OFF behavior
  for the same input. Grouping is unchanged; only `owner_edge_evidence.tsv`
  content changes, and that change is documented.
- The `owner_edge_evidence.tsv` contract change is recorded in
  `2026-05-11-untargeted-alignment-output-contract.md` (or wherever the artifact
  contract lives).

### Tier 1: (neutral_loss_tag, m/z) bucketing index

**Deprioritized 2026-05-15 — Stop Condition 4 triggered.** The post-Tier-0
85-RAW multi-tag drift run measured `cluster_owners` at 68.9 s, ~4.4% of the
~26-minute wall time. `owner_backfill` (1,157 s, I/O-bound) now dominates.
Bucketing would, optimistically, take `cluster_owners` from ~69 s toward ~10 s
— roughly a 1-minute saving on a 26-minute run. That is not worth the
implementation and equivalence-proof cost while `owner_backfill` is the bottleneck.
Tier 1 should only be revisited if a future change makes `cluster_owners`
dominant again (much larger batches, or after `owner_backfill` is optimized on
its own axis — see the prior performance spec).

**Prerequisite (if revisited):** Tier 0 landed and verified.

**Goal:** Replace the "owner vs every existing group" scan with a bucketed
candidate lookup, turning O(n^2.3) into approximately O(n * k) where k is the
average owners per m/z bucket.

**Rationale:** Two owners can only group if they share `neutral_loss_tag`, are
from different samples, and have precursor m/z within `config.max_ppm` (plus
product m/z and observed-loss tolerances). m/z is sparse in LC-MS data, so a
bucket index over `(neutral_loss_tag, precursor_mz)` eliminates the vast
majority of structurally-impossible pairs without evaluating them.

**Design constraints:**

- Bucket key: `(neutral_loss_tag, floor(precursor_mz / bucket_width))`.
- Each owner is compared only against groups whose envelope overlaps the owner's
  bucket **and its neighboring buckets** — boundary owners near a bucket edge
  must not be missed.
- Grouping equivalence is defined by **family membership**, not by internal
  group-construction order. A characterization fixture must prove identical
  family membership between the legacy scan and the bucketed scan on
  representative synthetic data.
- If the bucketed algorithm cannot be proven membership-equivalent, keep the
  Tier 0 implementation and stop.

**Acceptance criteria:**

- `cluster_owners` scaling becomes near-linear: re-running the 8-RAW and 85-RAW
  drift timing shows the candidate-count ratio and the time ratio within the
  same order of magnitude (no longer ~O(n^2.3)).
- Family membership is identical to Tier 0 output on the 8-RAW and 85-RAW
  validation runs (diff of `alignment_matrix.tsv` and `alignment_cells.tsv`).
- New unit tests cover empty input, single owner, bucket-boundary owners,
  m/z-tolerance-boundary pairs, and multi-tag input.

### Tier 2: Vectorize the numeric edge core within buckets

**Deprioritized 2026-05-15** — cascades from Tier 1 (Stop Condition 4). Vectorizing
a 68.9 s stage that is ~4.4% of wall time is not worth the equivalence-proof cost.

**Prerequisite (if revisited):** Tier 1 landed and verified.

**Goal:** Within a bucket's k owners, replace the k^2 Python `evaluate_owner_edge`
calls and dataclass allocations with NumPy array operations for the numeric
core.

**Design:**

- Stack per-owner numeric fields into arrays: `precursor_mz`, `owner_apex_rt`,
  `product_mz`, `observed_neutral_loss_da`, `evidence_score`, `seed_event_count`,
  `owner_area`, plus drift-corrected RT inputs.
- Compute pairwise matrices with broadcasting: ppm, raw RT delta,
  drift-corrected RT delta, `_score` components, `_decision` thresholds.
- Keep a thin Python pass only for fields that do not vectorize cleanly
  (`assignment_reason` string checks, `supporting_events` iteration in
  `_has_tail_seed` / `_duplicate_context`), and run that pass **only for pairs
  that survive the numeric gate**.

**Design constraints:**

- The scoring and decision values produced must be identical to
  `evaluate_owner_edge` for every pair. This tier is a pure performance
  refactor of the same arithmetic.
- `OwnerEdgeEvidence` records are still produced for the pairs that need them
  (Tier 0's evidence-sink contract), just constructed from the vectorized
  results rather than per-call.
- pandas 2.x Copy-on-Write: if any intermediate uses a DataFrame, add explicit
  `.copy()` / `.to_numpy(copy=True)` per the repo Python rules.

**Acceptance criteria:**

- `cluster_owners` per-bucket compute time drops measurably versus Tier 1.
- A characterization fixture proves the vectorized core produces identical
  `decision` / `score` / `failure_reason` to `evaluate_owner_edge` on
  representative synthetic owner pairs.
- Existing `edge_scoring` and `owner_clustering` tests pass unchanged.

## Explicitly Not Approved

- Changing `evaluate_owner_edge` scoring thresholds or `_decision` logic.
- Changing the `OwnerEdgeEvidence` field set or the `alignment_review.tsv` /
  `alignment_matrix.tsv` / `alignment_cells.tsv` schemas.
- Parallelizing `cluster_owners` across processes. It is a cross-sample
  synchronization point; process parallelism here would require a different
  spec and carries Windows `spawn` overhead. Tier 0+1 are expected to make it
  cheap enough that this is unnecessary.
- Numba / Cython on the clustering loop. Tier 1 (algorithmic) and Tier 2
  (vectorization) must be exhausted and proven insufficient first.
- Touching `owner_backfill`, discovery, or alignment correctness.

## Verification Strategy

Re-run the same 2x2 timing grid (8-RAW / 85-RAW x drift / no-drift) after each
tier, plus one multi-tag run:

1. Unit tests with synthetic owners (per-tier acceptance criteria above).
2. 8-RAW drift timing run — confirms Tier 0 / Tier 1 / Tier 2 effect cheaply.
3. 8-RAW multi-tag drift timing run — baseline captured at
   `output/alignment/multi_tag_8raw_drift_timing_20260515/timing.json`
   (`cluster_owners` = 23.2 s); re-run after each tier to confirm R3 is resolved.
4. 85-RAW drift timing run — confirms the headline number
   (`cluster_owners` ~2,118 s -> target).
5. 85-RAW multi-tag run — the original failing case; must now write all
   artifacts within budget.

For each real-data validation, record: command, branch and commit, worker
count, wall-clock time, timing JSON path, output directory, and whether
`alignment_matrix.tsv` / `alignment_cells.tsv` matched the pre-change baseline.

## Stop Conditions

Stop and revisit this spec if any of these happen:

- Tier 0 changes `alignment_matrix.tsv` or `alignment_cells.tsv` content (only
  `owner_edge_evidence.tsv` is allowed to change).
- Tier 1 bucketed grouping cannot be proven membership-equivalent to the legacy
  scan.
- Tier 2 vectorized core cannot be proven value-identical to
  `evaluate_owner_edge`.
- Post-Tier-0 timing shows `cluster_owners` is no longer the dominant compute
  stage and `owner_backfill` or another stage now dominates — in that case the
  remaining tiers may not be worth their implementation cost.

## Next Step

Write an implementation plan for **Tier 0 only**: the prefilter / evidence-sink
decoupling, the `owner_edge_evidence.tsv` contract change (Option A — decided),
unit tests for grouping equivalence, and one 8-RAW drift timing run.

Do not implement Tier 1 or Tier 2 until Tier 0 has landed and a fresh timing
report confirms its effect.
