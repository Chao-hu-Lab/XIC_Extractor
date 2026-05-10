# Alignment Clustering Core Implementation Plan

> **For agentic workers:** implement this plan task-by-task with TDD. This plan is intentionally smaller than the earlier draft. Do not re-expand it with large inline code blocks unless a test or contract truly needs it.

## Summary

Implement the Plan 1 core for cross-sample untargeted alignment: group per-sample `DiscoveryCandidate` records into cross-sample `AlignmentCluster` records using **CID-aware neutral-loss compatibility** plus MS1 m/z/RT proximity.

This is **not** HCD fragment-pattern alignment. Current data are CID-style neutral-loss methods, so v1 must not claim full MS2 pattern matching. The v1 identity model is:

```text
same aligned feature = same neutral-loss-compatible chemical hypothesis across samples
```

That means m/z and RT are necessary but insufficient. Two candidates with matching m/z/RT must still pass NL compatibility checks before they can share a cluster.

## Scope

In scope:

- New pure-Python package `xic_extractor/alignment/`.
- `AlignmentConfig`, `AlignmentCluster`, and `cluster_candidates()`.
- NL-tag stratification.
- CID/NL compatibility guards.
- Anchor policy based on reliable discovery evidence.
- Deterministic clustering, same-sample collision handling, and final cleanup.
- Synthetic unit tests only.

Out of scope:

- RAW reading.
- MS1 backfill.
- CLI/output schema.
- GUI integration.
- HCD spectrum similarity, library matching, or top-N fragment fingerprinting.
- Real-data validation. Plan 3/4 will own end-to-end validation.

## Core Contracts

### CID / HCD Evidence Boundary

Use these terms consistently:

- Targeted mode: `candidate-aligned NL evidence`.
- Discovery/alignment v1: `NL compatibility evidence`.
- Future HCD extension: `MS2 fragment fingerprint similarity`.

Do not describe v1 as `MS2 pattern matching`. In CID data, strict observed neutral loss is strong evidence, but it is not a full fragment fingerprint.

### Cluster Identity

Candidates can merge only when all hard guards pass:

1. Same `neutral_loss_tag`.
2. Precursor m/z within `max_ppm`.
3. RT within `max_rt_sec`.
4. Product m/z compatible.
5. Observed neutral loss compatible.

Current `DiscoveryCandidate` inputs come from strict NL seeds, so they carry product and observed-loss evidence. If a future plan allows non-MS2 inputs into clustering, missing product / observed-loss evidence may be treated as unknown rather than conflict, but it must not create anchor strength.

### Anchor Policy

`review_priority == "HIGH"` alone is not the full anchor rule. Review priority is a UX funnel label; alignment anchors need enough evidence to define a cluster center.

Default anchor policy:

- `review_priority in config.anchor_priorities` (default `("HIGH",)`)
- `evidence_score >= config.anchor_min_evidence_score` (default `60`)
- `seed_event_count >= config.anchor_min_seed_events` (default `2`)
- `ms1_peak_found is True`
- `ms1_apex_rt is not None`
- `ms1_area is not None and ms1_area > 0`
- if `ms1_scan_support_score is not None`, it must be `>= config.anchor_min_scan_support_score` (default `0.5`)

Non-anchors may join compatible anchor clusters. Non-anchors outside all anchor clusters still seed `has_anchor=False` clusters so data are not silently dropped.

### Cluster Center

Do not weight center directly by raw `ms1_area`. Area reflects biology and sample abundance; it is not a center reliability score.

For v1:

- If a cluster has anchors, center uses anchor members only.
- If a cluster has no anchors, center uses all members.
- `cluster_center_mz` is the median precursor m/z of contributing members.
- `cluster_center_rt` is the median RT of contributing members, using `ms1_apex_rt` when available and `best_seed_rt` as fallback.

This keeps high-abundance biological outliers from pulling the cross-sample center.

### Same-Sample Collision

A final aligned matrix can have only one primary value per `(cluster, sample)`. Plan 1 must therefore prevent ambiguous same-sample membership.

Default v1 rule:

- A cluster may contain at most one primary member per `sample_stem`.
- If a candidate would join a cluster that already has the same sample, keep the better member by:
  1. higher anchor status
  2. higher `evidence_score`
  3. higher `seed_event_count`
  4. higher `ms1_area` (missing sorts last)
  5. smaller absolute `neutral_loss_mass_error_ppm`
  6. lower `candidate_id` for deterministic tie-break
- The rejected same-sample candidate remains eligible for another compatible cluster or becomes a `has_anchor=False` singleton.

Plan 3 may later expose duplicates in a diagnostics file, but Plan 1 must keep cluster membership deterministic.

### Determinism

Cluster membership and IDs must be invariant to input order.

Required test cases:

- Same candidates in all input permutations produce identical cluster memberships.
- A-B close, B-C close, A-C not close does not chain-merge into one feature.
- Same m/z/RT but conflicting product m/z or observed neutral loss splits.
- Current strict-NL `DiscoveryCandidate` inputs always carry product and observed-loss evidence; tests should not invent nullable product fields unless the model changes first.

## File Structure

Create:

- `xic_extractor/alignment/__init__.py`
- `xic_extractor/alignment/config.py`
- `xic_extractor/alignment/models.py`
- `xic_extractor/alignment/compatibility.py`
- `xic_extractor/alignment/clustering.py`
- `tests/test_alignment_config.py`
- `tests/test_alignment_models.py`
- `tests/test_alignment_compatibility.py`
- `tests/test_alignment_clustering.py`

No file in `xic_extractor/alignment/` may import RAW readers, GUI, workbook output, HTML report rendering, or discovery pipeline orchestration.

## Public API

`xic_extractor.alignment` exports exactly:

- `AlignmentConfig`
- `AlignmentCluster`
- `cluster_candidates`

Internal helpers may be imported by tests from focused modules, but downstream production code should use the public API.

## Data Model

### `AlignmentConfig`

Fields:

```python
preferred_ppm: float = 20.0
max_ppm: float = 50.0
preferred_rt_sec: float = 60.0
max_rt_sec: float = 180.0
product_mz_tolerance_ppm: float = 20.0
observed_loss_tolerance_ppm: float = 20.0
mz_bucket_neighbor_radius: int = 2
anchor_priorities: tuple[ReviewPriority, ...] = ("HIGH",)
anchor_min_evidence_score: int = 60
anchor_min_seed_events: int = 2
anchor_min_scan_support_score: float = 0.5
rt_unit: Literal["min"] = "min"
fragmentation_model: Literal["cid_nl"] = "cid_nl"
```

Validation:

- preferred tolerances must be `<=` max tolerances.
- all tolerances must be positive.
- `anchor_priorities` cannot be empty.
- `anchor_min_evidence_score` must be `0..100`.
- `anchor_min_seed_events >= 1`.
- `anchor_min_scan_support_score` must be `0..1`.
- `rt_unit` must be `"min"` in v1.
- `fragmentation_model` must be `"cid_nl"` in v1.

### `AlignmentCluster`

Fields:

```python
cluster_id: str
neutral_loss_tag: str
cluster_center_mz: float
cluster_center_rt: float
has_anchor: bool
members: tuple[DiscoveryCandidate, ...]
```

`cluster_id` is assigned only by top-level `cluster_candidates()` as `ALN000001`, `ALN000002`, etc.

## Algorithm

1. Validate config and finite candidate values.
2. Stratify by `neutral_loss_tag`.
3. Within each stratum, sort candidates deterministically:
   - anchors first
   - higher evidence score
   - higher seed event count
   - higher MS1 area, missing last
   - lower precursor m/z
   - lower RT
   - sample stem
   - candidate id
4. For each candidate, find compatible clusters by max tolerances and NL compatibility.
5. Attach to the best compatible cluster by match score:
   - hard reject outside `max_ppm` / `max_rt_sec`
   - preferred-window score favors candidates within `preferred_ppm` / `preferred_rt_sec`
   - no product-overlap score in v1
6. Enforce same-sample collision policy.
7. Seed a new cluster if no compatible cluster remains.
8. Recompute centers with median rule.
9. Finalize membership:
   - re-check every member against drifted center
   - eject out-of-tolerance members
   - reattach once
   - remaining ejected candidates become deterministic `has_anchor=False` clusters unless they satisfy anchor policy as singletons
10. Sort clusters by `(cluster_center_mz, cluster_center_rt, neutral_loss_tag)` and assign IDs.

## Tasks

### Task 0: Branch / Worktree Setup

Do not create this work from plain `master` until the discovery-v1 branch is merged. Plan 1 depends on current discovery candidate fields, especially `evidence_score`, `evidence_tier`, `ms1_scan_support_score`, feature family fields, and dual CSV contract.

Use one of these paths:

- If current discovery branch is not merged: continue from this worktree or create the alignment worktree from this branch.
- If current discovery branch is merged: sync local `master`, then create a new branch from updated `master`.

Suggested branch name: `codex/alignment-clustering-v1`.

### Task 1: Config And Public API

TDD:

- default config matches v1 tolerances and `fragmentation_model="cid_nl"`.
- invalid ppm / RT / product / observed-loss windows are rejected.
- invalid anchor thresholds are rejected.
- public API exports only `AlignmentConfig`, `AlignmentCluster`, `cluster_candidates`.

Implementation:

- Create `xic_extractor/alignment/config.py`.
- Create package `__init__.py`.
- Do not import discovery pipeline or IO modules.

### Task 2: Models And Median Center

TDD:

- anchor cluster center uses anchors only.
- non-anchor cluster center uses all members.
- center uses median m/z and median RT, not raw area weighted mean.
- RT fallback uses `best_seed_rt` when `ms1_apex_rt` is missing.
- empty center input raises a clear `ValueError`.

Implementation:

- Create `AlignmentCluster`.
- Add center helper in `models.py`.

### Task 3: NL Compatibility

TDD:

- different `neutral_loss_tag` is incompatible.
- same m/z/RT but product m/z conflict is incompatible.
- same m/z/RT but observed neutral-loss conflict is incompatible.
- compatibility tests use strict-NL `DiscoveryCandidate` inputs with real product and observed-loss values.
- CID model rejects attempts to use unsupported fragmentation model values.

Implementation:

- Create `compatibility.py`.
- Keep HCD pattern similarity out of v1.
- Use small helpers for `ppm_distance`, RT seconds difference, product compatibility, and observed-loss compatibility.

### Task 4: Anchor Policy And Candidate Ordering

TDD:

- `review_priority="HIGH"` with weak/missing MS1 does not become an anchor.
- candidate meeting default anchor policy becomes anchor.
- `anchor_min_evidence_score`, `anchor_min_seed_events`, and scan-support thresholds affect the predicate.
- candidate ordering is deterministic and prioritizes anchors before non-anchors.

Implementation:

- Add `is_alignment_anchor(candidate, config)`.
- Add deterministic sort key.

### Task 5: Greedy Clustering With Same-Sample Collision

TDD:

- compatible candidates from different samples merge.
- compatible candidates from the same sample do not both become primary members of the same cluster.
- better same-sample candidate wins by the documented tie-break rules.
- loser remains eligible for another cluster or singleton.
- non-anchor outside all anchor clusters becomes `has_anchor=False` cluster.

Implementation:

- Add per-stratum clustering in `clustering.py`.
- Use an m/z bucket index only after the plain implementation is covered by tests.

### Task 6: Final Cleanup And Permutation Invariance

TDD:

- final cleanup ejects members outside max tolerances after center drift.
- ejected members are reattached once when compatible.
- chain case A-B close, B-C close, A-C not close does not collapse into one cluster.
- input permutations produce identical cluster IDs and memberships.

Implementation:

- Add finalize pass.
- Sort clusters before ID assignment.

### Task 7: Top-Level `cluster_candidates()`

TDD:

- empty input returns empty tuple.
- invalid config fails before clustering.
- mixed NL strata never merge.
- cluster IDs are six-digit `ALN000001` style.
- integration fixture with multiple samples and NL strata produces expected clusters.

Implementation:

- Export `cluster_candidates`.
- Keep all arguments keyword-only.

## Validation

Run after implementation:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_config.py tests/test_alignment_models.py tests/test_alignment_compatibility.py tests/test_alignment_clustering.py -v
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

No real RAW validation is required for Plan 1 because this is pure clustering logic.

## Acceptance Criteria

- `xic_extractor.alignment` is pure domain logic with no RAW, CLI, GUI, workbook, or report dependency.
- V1 terminology says `NL compatibility`, not `MS2 pattern matching`.
- HCD fragment fingerprint similarity is explicitly future scope.
- `cluster_candidates()` is deterministic and input-order invariant.
- Same m/z/RT candidates with contradictory CID/NL evidence do not merge.
- Same-sample duplicates are resolved deterministically.
- Cluster centers are not raw-area weighted.
- Non-anchor data are preserved without silently pulling anchored centers.
