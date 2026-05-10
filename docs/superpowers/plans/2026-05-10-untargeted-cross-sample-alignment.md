# Untargeted Cross-Sample Alignment Plan Index

> **For agentic workers:** Do not execute this index file directly. Execute the smaller implementation plans listed below in order.

**Goal:** Replace the FH + mzmine + metabCombiner + combine_fix pipeline with a single-tool XIC alignment that produces a neutral-loss-compatible hypothesis × sample matrix with detected/rescued/absent semantics, leveraging XIC's same-tool MS1 backfill at cluster centers.

**Architecture:** Four sequential sub-projects: (1) cluster per-sample discovery candidates into cross-sample NL-compatible hypotheses; (2) backfill MS1 measurements at cluster centers in samples that lacked an MS2 NL trigger; (3) emit alignment TSVs and a CLI; (4) validate against the legacy FH and combine_fix outputs the user has on disk.

**Tech Stack:** Python, numpy, pytest, existing `xic_extractor.discovery` and `xic_extractor.signal_processing` modules, MS-data aligner algorithm core ported in (not depended on as a package).

---

## Why This Is Split Into Four Plans

The full goal — replacing the legacy multi-tool pipeline — is too big for one plan. Each sub-plan below produces working, testable software on its own:

- Plan 1 alone produces a clustering function that can be exercised against synthetic candidates without any RAW reading.
- Plan 2 alone consumes Plan 1's clusters plus a RAW source and produces a backfilled matrix object.
- Plan 3 alone consumes Plan 2's matrix and emits files plus a CLI; this is the user-facing deliverable.
- Plan 4 produces a comparison harness against legacy outputs; it is only useful after Plans 1-3 ship but is separable for review and execution.

Splitting also keeps each plan's regression risk bounded: clustering bugs, backfill bugs, and output-schema bugs surface in different test suites and different commits.

## Execution Order

Run these plans in order. **Only Plan 1 is written and executable right now.** Plans 2-4 are roadmap placeholders and must be written/reviewed before execution. Plan 4 may slip after Plan 3 without blocking shipping a usable v1.

1. [Plan 1: Alignment Clustering Core](2026-05-10-alignment-clustering-plan.md)
2. Plan 2: Cross-Sample MS1 Backfill — pending, not yet written.
3. Plan 3: Alignment Output and CLI — pending, not yet written.
4. Plan 4: Legacy Pipeline Validation — pending, not yet written.

## Design Decisions Carried Forward

These were resolved during brainstorming on 2026-05-10. They apply across all four plans.

### V1 Is CID/NL-Compatible Alignment, Not HCD Pattern Matching

The current datasets use CID-style neutral-loss methods, not HCD methods designed for rich fragment fingerprints. Therefore v1 alignment must not claim full MS2 pattern matching. The correct v1 identity model is:

```text
same aligned feature = same neutral-loss-compatible chemical hypothesis across samples
```

Terminology rules:

- Targeted mode: `candidate-aligned NL evidence`.
- Discovery/alignment v1: `NL compatibility evidence`.
- Future HCD extension: `MS2 fragment fingerprint similarity`.

If future HCD data are added, they should extend the alignment compatibility layer with fragment fingerprint / spectral similarity evidence. They should not be mixed into the CID v1 contract.

### NL-Tag Stratification Is The First Hard Constraint

Candidates with different `neutral_loss_tag` values never merge into the same cluster, even when m/z and RT match within tolerance. Reason: the legacy FH method is also NL-driven and the user explicitly wants alignment to preserve this biological identity. Candidates with `neutral_loss_tag == ""` (untagged) form their own stratum.

### NL Compatibility Is Required Inside Each Stratum

Inside a shared `neutral_loss_tag`, precursor m/z and RT are necessary but insufficient. Candidates must also be NL-compatible before they can share a cluster:

- product m/z compatible
- observed neutral loss compatible

Current per-sample discovery candidates are strict-NL inputs, so they carry product and observed-loss evidence. If a future backfill or imported-input path introduces missing MS2 evidence into clustering, missing evidence should be treated as unknown rather than contradiction, but it must not create anchor strength.

This prevents the most dangerous false positive: merging two same-m/z/RT signals whose CID/NL evidence points to different chemical hypotheses.

Cluster compatibility is not any-member matching. Anchored clusters require a new candidate to be compatible with every anchor member. Unanchored clusters require compatibility with every primary member. This conservative complete-link rule prevents A-B / B-C chain merging from collapsing distinct hypotheses into one row.

### Alignment Anchor Policy Drives Seeding With Non-Anchor Fallback

Within each NL stratum, anchor candidates are processed first and seed clusters with `has_anchor=True`. The default anchor policy is stricter than `review_priority == "HIGH"` alone:

- `review_priority in config.anchor_priorities` (default `("HIGH",)`)
- evidence score above the configured anchor threshold
- repeated strict NL seed support
- MS1 peak found with positive area
- usable apex RT
- scan support not poor when scan-support metric is present

Non-anchor candidates that fall within an anchor cluster's tolerance and pass NL compatibility can join it. Non-anchor candidates that do **not** fall within any anchor cluster still seed their own cluster, but it is flagged `has_anchor=False` for downstream filtering. This avoids silently dropping LOW data while preventing weak-evidence members from pulling anchored centers.

If a stratum contains zero anchors, every candidate seeds or joins `has_anchor=False` clusters and downstream filtering decides whether to keep them.

### Cluster Center Uses Robust Anchor Median

`cluster_center_mz` is the median precursor m/z of anchor members. `cluster_center_rt` is the median anchor RT, using `ms1_apex_rt` when available and falling back to `best_seed_rt`. If no anchor members exist, medians use all members.

Do not weight centers directly by raw `ms1_area`. Area reflects biology and abundance, not center reliability.

### Cell Status Is Three-State Plus One

Each cell in the final matrix is `detected`, `rescued`, `absent`, or `unchecked`:

- `detected`: the sample has a discovery candidate that joined this cluster.
- `rescued`: the sample had no candidate but its raw MS1 trace at the cluster's m/z + RT contains a peak detected by the same `find_peak_and_area` used in discovery.
- `absent`: the sample's raw MS1 trace was checked and contained no peak above the resolver's thresholds.
- `unchecked`: backfill could not run (e.g., raw file unavailable). Distinct from `absent`.

### MS-Data Aligner Algorithm Is Ported, Not Depended On

The greedy clustering with m/z-bucket index and two-tier (preferred/max) ppm + RT tolerance is ported into `xic_extractor.alignment.clustering`. The XIC version diverges because of the NL compatibility guard, anchor policy, same-sample collision policy, and robust center rule, so a runtime dependency would create coupling that diverges anyway.

### Backfill Reuses `find_peak_and_area`

Cross-sample MS1 backfill calls `xic_extractor.signal_processing.find_peak_and_area` against the same MS1 trace extraction interface (`MS1XicSource`) used by per-sample discovery. No alternate detector. The user's "single-tool, single-evidence-chain" goal collapses if backfill silently swaps in a different peak picker.

### v1 Defaults Mirror MS-Data Aligner

Starting tolerances: `preferred_ppm = 20`, `max_ppm = 50`, `preferred_rt_sec = 60`, `max_rt_sec = 180`, `mz_bucket_neighbor_radius = 2`, `rt_unit = "min"`. v1 ships with these as `AlignmentConfig` defaults. Tuning waits for real data.

### RT Unit Is Locked To Minutes

`AlignmentConfig.rt_unit` is `Literal["min"]` and the only allowed value in v1. The discovery pipeline emits `ms1_apex_rt`, `best_seed_rt`, and `DiscoverySeed.rt` in minutes; alignment converts to seconds only at comparison points against `max_rt_sec` / `preferred_rt_sec`. Any future change that makes RT carry seconds is forced to update this lock, preventing silent 60× errors.

### Final Cleanup Pass Re-Validates Membership

After the per-stratum greedy assignment, cluster centers may have drifted as anchors were added. `finalize_cluster_membership` re-scores every member against its current cluster center, ejects out-of-tolerance or NL-incompatible members, and runs a single re-attachment pass. Members that still cannot find a home become their own non-anchor cluster. This is what keeps the greedy algorithm honest when anchor centers move during a single pass.

### Same-Sample Collisions Must Be Resolved Before Matrix Output

An aligned matrix has one primary value per `(cluster, sample)`. Plan 1 therefore must not allow two primary candidates from the same sample to remain in one cluster. If two candidates from the same sample match the same cluster, keep the better member by anchor status, evidence score, seed count, area, neutral-loss error, then candidate id. The loser remains eligible for another compatible cluster or becomes a singleton.

## Key Data Model Contracts

Defined in Plan 1, used by Plans 2-4:

```python
@dataclass(frozen=True)
class AlignmentConfig:
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

@dataclass(frozen=True)
class AlignmentCluster:
    cluster_id: str  # ALN000001 (six-digit)
    neutral_loss_tag: str
    cluster_center_mz: float
    cluster_center_rt: float  # in minutes
    cluster_product_mz: float
    cluster_observed_neutral_loss_da: float
    has_anchor: bool
    members: tuple[DiscoveryCandidate, ...]
```

Defined in Plan 2:

```python
CellStatus = Literal["detected", "rescued", "absent", "unchecked"]

@dataclass(frozen=True)
class AlignedCell:
    sample_stem: str
    cluster_id: str
    status: CellStatus
    intensity: float | None
    apex_rt: float | None
    trace_quality: str
    scan_support_score: float | None

@dataclass(frozen=True)
class AlignmentMatrix:
    clusters: tuple[AlignmentCluster, ...]
    cells: tuple[AlignedCell, ...]
    sample_order: tuple[str, ...]
```

Concrete schema for output TSVs is defined in Plan 3.

## Out Of Scope

- Sample-pair RT drift correction (loess / spline). Deferred to a later plan once v1 numbers are seen.
- Group awareness (CRC / control / QC). Alignment is biology-agnostic; group filtering belongs downstream.
- GUI integration. v1 is CLI-only.
- mzmine compatibility shims. The user's goal is to retire mzmine for this use case.
- HCD fragment fingerprint / spectrum similarity. The v1 evidence model is CID neutral-loss compatibility only.
- Performance tuning beyond the bucket-index already in Plan 1. Profile after correctness lands.
- Replacing the per-sample discovery pipeline. v1 alignment consumes its existing CSV outputs.
