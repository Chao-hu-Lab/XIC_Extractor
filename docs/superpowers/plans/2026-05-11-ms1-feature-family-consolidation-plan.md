# MS1 Feature Family Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace event-cluster alignment rows with MS1 feature-family rows so untargeted alignment does not repeat FH's MS2-event-per-row failure mode.

**Architecture:** Keep Plan 1 event clustering as a conservative MS2 evidence layer, then add a separate MS1 feature-family consolidation layer before matrix integration. Final review/matrix rows represent MS1 feature families, not individual MS2 trigger clusters. CID-only evidence can support family consolidation, but the output must not claim full HCD-like MS2 pattern identity.

**Tech Stack:** Python, pytest, `uv`, existing `xic_extractor.alignment` modules, existing `find_peak_and_area()` MS1 integration, fake RAW sources for unit tests, 8raw/85raw validation for real-data checks.

---

## Problem Statement

The current alignment pipeline does:

```text
DiscoveryCandidate -> AlignmentCluster (MS2 event cluster) -> backfill -> alignment row
```

That still makes the final matrix identity too close to FH: one row can mean one MS2 trigger/event cluster, not one MS1 chromatographic feature.

Real 85raw evidence shows repeated near-compatible pairs:

- Same `neutral_loss_tag`.
- m/z within 5 ppm.
- RT center within 2 seconds.
- same product m/z and observed neutral loss.
- high detected containment, often `overlap coefficient = 1.0`.
- substantial shared detected support, for example 40-50 shared samples.
- but Jaccard can fall below 0.60 because one event cluster is a subset of another.

This is not a 5-medC special case. It is a general symptom that secondary MS2 triggers from the same MS1 feature become separate event-cluster rows.

The correct model is:

```text
MS2 event -> MS1 feature family -> alignment matrix row
```

## Core Contracts

- `AlignmentCluster` remains the MS2 event-cluster model.
- New `MS1FeatureFamily` becomes the final row identity for alignment review/matrix output.
- MS2 event clusters are evidence attached to a family, not final rows.
- CID-only compatibility is useful evidence, but not full structural identity.
- If future full MS2 signatures exist and conflict, hard family consolidation is blocked.
- Low-shared rare features must not be absorbed into broad features.
- High shared detected support plus high containment is a general family signal, not an exception.
- Final area values come from family-centered MS1 integration, not from whichever event cluster becomes primary.
- Existing `alignment_cells.tsv` / status debug files may remain opt-in, but should identify family rows and optional source event cluster evidence.

## File Structure

- Create `xic_extractor/alignment/feature_family.py`
  - Owns `MS1FeatureFamily`, family construction, compatibility gates, containment scoring, and family IDs.
- Create `xic_extractor/alignment/family_integration.py`
  - Owns family-centered MS1 re-extraction/integration and produces `AlignmentMatrix` cells for families.
- Modify `xic_extractor/alignment/matrix.py`
  - Introduce `AlignmentRowLike` protocol or type alias so `AlignmentMatrix` can hold family rows.
- Modify `xic_extractor/alignment/pipeline.py`
  - Flow becomes `cluster_candidates -> build_ms1_feature_families -> integrate_feature_family_matrix -> write outputs`.
- Modify `xic_extractor/alignment/tsv_writer.py`
  - Review/matrix output columns become family-oriented.
- Modify `xic_extractor/alignment/legacy_io.py`
  - Load family-oriented XIC matrix/review columns for legacy validation.
- Create `xic_extractor/alignment/near_duplicate_audit.py`
  - Shared audit utility to quantify unresolved event-level near duplicates.
- Create `scripts/audit_alignment_near_duplicates.py`
  - CLI wrapper for before/after real-data audits.
- Tests:
  - `tests/test_alignment_feature_family.py`
  - `tests/test_alignment_family_integration.py`
  - `tests/test_alignment_pipeline.py`
  - `tests/test_alignment_tsv_writer.py`
  - `tests/test_alignment_legacy_io.py`
  - `tests/test_alignment_validation_compare.py`
  - `tests/test_alignment_near_duplicate_audit.py`

---

### Task 0: Add Generic Near-Duplicate Audit Utility

**Files:**
- Create: `xic_extractor/alignment/near_duplicate_audit.py`
- Create: `scripts/audit_alignment_near_duplicates.py`
- Test: `tests/test_alignment_near_duplicate_audit.py`

- [ ] **Step 1: Write failing audit tests**

Create `tests/test_alignment_near_duplicate_audit.py`:

```python
from xic_extractor.alignment.near_duplicate_audit import (
    AlignmentNearDuplicateInput,
    count_near_duplicate_pairs,
)


def test_audit_counts_high_shared_unresolved_near_duplicate_pairs():
    rows = (
        AlignmentNearDuplicateInput(
            row_id="A",
            neutral_loss_tag="DNA_dR",
            mz=242.114,
            rt=12.5927,
            product_mz=126.066,
            observed_neutral_loss_da=116.048,
            present_samples=frozenset({"s1", "s2", "s3", "s4", "s5"}),
        ),
        AlignmentNearDuplicateInput(
            row_id="B",
            neutral_loss_tag="DNA_dR",
            mz=242.115,
            rt=12.5916,
            product_mz=126.066,
            observed_neutral_loss_da=116.048,
            present_samples=frozenset({"s1", "s2", "s3", "s4"}),
        ),
        AlignmentNearDuplicateInput(
            row_id="C",
            neutral_loss_tag="DNA_dR",
            mz=260.0,
            rt=9.0,
            product_mz=144.0,
            observed_neutral_loss_da=116.0,
            present_samples=frozenset({"s1", "s2", "s3", "s4"}),
        ),
    )

    summary = count_near_duplicate_pairs(
        rows,
        mz_ppm=5.0,
        rt_sec=2.0,
        product_ppm=10.0,
        observed_loss_ppm=10.0,
        min_shared_samples=3,
        min_overlap=0.8,
    )

    assert summary.near_pair_count == 1
    assert summary.high_shared_pair_count == 1
    assert summary.top_pairs[0].left_id == "A"
    assert summary.top_pairs[0].right_id == "B"
    assert summary.top_pairs[0].shared_count == 4
    assert summary.top_pairs[0].overlap_coefficient == 1.0
```

- [ ] **Step 2: Run test to verify red**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_near_duplicate_audit.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'xic_extractor.alignment.near_duplicate_audit'`.

- [ ] **Step 3: Implement audit module**

Create `xic_extractor/alignment/near_duplicate_audit.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class AlignmentNearDuplicateInput:
    row_id: str
    neutral_loss_tag: str
    mz: float
    rt: float
    product_mz: float
    observed_neutral_loss_da: float
    present_samples: frozenset[str]


@dataclass(frozen=True)
class NearDuplicatePair:
    left_id: str
    right_id: str
    shared_count: int
    overlap_coefficient: float
    jaccard: float
    mz_ppm: float
    rt_sec: float


@dataclass(frozen=True)
class NearDuplicateSummary:
    near_pair_count: int
    high_shared_pair_count: int
    top_pairs: tuple[NearDuplicatePair, ...]


def count_near_duplicate_pairs(
    rows: tuple[AlignmentNearDuplicateInput, ...],
    *,
    mz_ppm: float,
    rt_sec: float,
    product_ppm: float,
    observed_loss_ppm: float,
    min_shared_samples: int,
    min_overlap: float,
) -> NearDuplicateSummary:
    pairs: list[NearDuplicatePair] = []
    for left, right in combinations(rows, 2):
        if left.neutral_loss_tag != right.neutral_loss_tag:
            continue
        mz_distance = _ppm(left.mz, right.mz)
        rt_distance = abs(left.rt - right.rt) * 60.0
        if mz_distance > mz_ppm or rt_distance > rt_sec:
            continue
        if _ppm(left.product_mz, right.product_mz) > product_ppm:
            continue
        if (
            _ppm(left.observed_neutral_loss_da, right.observed_neutral_loss_da)
            > observed_loss_ppm
        ):
            continue
        shared = left.present_samples & right.present_samples
        union = left.present_samples | right.present_samples
        denominator = min(len(left.present_samples), len(right.present_samples))
        overlap = len(shared) / denominator if denominator else 0.0
        jaccard = len(shared) / len(union) if union else 0.0
        if len(shared) >= min_shared_samples and overlap >= min_overlap:
            pairs.append(
                NearDuplicatePair(
                    left_id=left.row_id,
                    right_id=right.row_id,
                    shared_count=len(shared),
                    overlap_coefficient=overlap,
                    jaccard=jaccard,
                    mz_ppm=mz_distance,
                    rt_sec=rt_distance,
                ),
            )
    sorted_pairs = tuple(
        sorted(
            pairs,
            key=lambda pair: (
                -pair.shared_count,
                -pair.overlap_coefficient,
                pair.mz_ppm,
                pair.rt_sec,
                pair.left_id,
                pair.right_id,
            ),
        ),
    )
    return NearDuplicateSummary(
        near_pair_count=len(pairs),
        high_shared_pair_count=sum(
            1 for pair in pairs if pair.shared_count >= min_shared_samples
        ),
        top_pairs=sorted_pairs[:20],
    )


def _ppm(left: float, right: float) -> float:
    return abs(left - right) / max(abs(left), 1e-12) * 1_000_000.0
```

- [ ] **Step 4: Add CLI wrapper**

Create `scripts/audit_alignment_near_duplicates.py`:

```python
from __future__ import annotations

import argparse
import csv
from collections.abc import Sequence
from pathlib import Path

from xic_extractor.alignment.near_duplicate_audit import (
    AlignmentNearDuplicateInput,
    count_near_duplicate_pairs,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    rows = _load_rows(args.review_tsv, args.matrix_tsv)
    summary = count_near_duplicate_pairs(
        rows,
        mz_ppm=args.mz_ppm,
        rt_sec=args.rt_sec,
        product_ppm=args.product_ppm,
        observed_loss_ppm=args.observed_loss_ppm,
        min_shared_samples=args.min_shared_samples,
        min_overlap=args.min_overlap,
    )
    print(f"near_pair_count={summary.near_pair_count}")
    print(f"high_shared_pair_count={summary.high_shared_pair_count}")
    for pair in summary.top_pairs:
        print(
            f"{pair.left_id}\\t{pair.right_id}\\t"
            f"shared={pair.shared_count}\\t"
            f"overlap={pair.overlap_coefficient:.3f}\\t"
            f"jaccard={pair.jaccard:.3f}\\t"
            f"mz_ppm={pair.mz_ppm:.3g}\\t"
            f"rt_sec={pair.rt_sec:.3g}"
        )
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit unresolved near-duplicate alignment rows.",
    )
    parser.add_argument("--review-tsv", type=Path, required=True)
    parser.add_argument("--matrix-tsv", type=Path, required=True)
    parser.add_argument("--mz-ppm", type=float, default=5.0)
    parser.add_argument("--rt-sec", type=float, default=2.0)
    parser.add_argument("--product-ppm", type=float, default=10.0)
    parser.add_argument("--observed-loss-ppm", type=float, default=10.0)
    parser.add_argument("--min-shared-samples", type=int, default=30)
    parser.add_argument("--min-overlap", type=float, default=0.8)
    return parser.parse_args(argv)


def _load_rows(
    review_tsv: Path,
    matrix_tsv: Path,
) -> tuple[AlignmentNearDuplicateInput, ...]:
    with matrix_tsv.open(newline="", encoding="utf-8") as handle:
        matrix_rows = {
            row[_first_present(row, ("feature_family_id", "cluster_id"))]: row
            for row in csv.DictReader(handle, delimiter="\\t")
        }
    with review_tsv.open(newline="", encoding="utf-8") as handle:
        review_rows = list(csv.DictReader(handle, delimiter="\\t"))
    output: list[AlignmentNearDuplicateInput] = []
    for row in review_rows:
        row_id = row[_first_present(row, ("feature_family_id", "cluster_id"))]
        matrix_row = matrix_rows[row_id]
        metadata = {
            "feature_family_id",
            "cluster_id",
            "neutral_loss_tag",
            "family_center_mz",
            "cluster_center_mz",
            "family_center_rt",
            "cluster_center_rt",
        }
        present_samples = frozenset(
            key for key, value in matrix_row.items()
            if key not in metadata and value not in ("", None)
        )
        output.append(
            AlignmentNearDuplicateInput(
                row_id=row_id,
                neutral_loss_tag=row["neutral_loss_tag"],
                mz=float(row.get("family_center_mz") or row["cluster_center_mz"]),
                rt=float(row.get("family_center_rt") or row["cluster_center_rt"]),
                product_mz=float(
                    row.get("family_product_mz") or row["cluster_product_mz"]
                ),
                observed_neutral_loss_da=float(
                    row.get("family_observed_neutral_loss_da")
                    or row["cluster_observed_neutral_loss_da"]
                ),
                present_samples=present_samples,
            ),
        )
    return tuple(output)


def _first_present(row: dict[str, str], names: tuple[str, ...]) -> str:
    for name in names:
        if name in row:
            return name
    raise ValueError(f"missing any of required columns: {', '.join(names)}")


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests to verify green**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_near_duplicate_audit.py -v
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/alignment/near_duplicate_audit.py scripts/audit_alignment_near_duplicates.py tests/test_alignment_near_duplicate_audit.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add xic_extractor/alignment/near_duplicate_audit.py scripts/audit_alignment_near_duplicates.py tests/test_alignment_near_duplicate_audit.py
git commit -m "test(alignment): add near-duplicate audit utility"
```

### Task 1: Add MS1 Feature Family Model

**Files:**
- Create: `xic_extractor/alignment/feature_family.py`
- Modify: `xic_extractor/alignment/matrix.py`
- Test: `tests/test_alignment_feature_family.py`

- [ ] **Step 1: Write failing model tests**

Create `tests/test_alignment_feature_family.py`:

```python
from types import SimpleNamespace

from xic_extractor.alignment.feature_family import build_ms1_feature_family
from xic_extractor.alignment.models import AlignmentCluster


def test_build_ms1_feature_family_tracks_event_clusters_and_cid_only_evidence():
    anchor = _cluster(
        "ALN000001",
        has_anchor=True,
        mz=242.114,
        rt=12.5927,
        members=("s1", "s2"),
    )
    secondary = _cluster(
        "ALN000002",
        has_anchor=False,
        mz=242.115,
        rt=12.5916,
        members=("s1",),
    )

    family = build_ms1_feature_family(
        family_id="FAM000001",
        event_clusters=(anchor, secondary),
        evidence="cid_nl_only;shared_detected=1;overlap=1",
    )

    assert family.feature_family_id == "FAM000001"
    assert family.neutral_loss_tag == "DNA_dR"
    assert family.family_center_mz == 242.114
    assert family.family_center_rt == 12.5927
    assert family.family_product_mz == 126.066
    assert family.family_observed_neutral_loss_da == 116.048
    assert family.has_anchor is True
    assert family.event_cluster_ids == ("ALN000001", "ALN000002")
    assert family.event_member_count == 3
    assert family.evidence == "cid_nl_only;shared_detected=1;overlap=1"


def test_build_ms1_feature_family_uses_non_anchor_median_when_no_anchor_exists():
    left = _cluster("ALN000001", has_anchor=False, mz=100.0, rt=1.0)
    right = _cluster("ALN000002", has_anchor=False, mz=102.0, rt=1.2)

    family = build_ms1_feature_family(
        family_id="FAM000001",
        event_clusters=(left, right),
        evidence="cid_nl_only",
    )

    assert family.family_center_mz == 101.0
    assert family.family_center_rt == 1.1
    assert family.has_anchor is False


def _cluster(
    cluster_id: str,
    *,
    has_anchor: bool,
    mz: float = 242.114,
    rt: float = 12.5927,
    product: float = 126.066,
    observed_loss: float = 116.048,
    members: tuple[str, ...] = ("s1",),
) -> AlignmentCluster:
    member_objects = tuple(
        SimpleNamespace(sample_stem=sample, candidate_id=f"{cluster_id}#{sample}")
        for sample in members
    )
    return AlignmentCluster(
        cluster_id=cluster_id,
        neutral_loss_tag="DNA_dR",
        cluster_center_mz=mz,
        cluster_center_rt=rt,
        cluster_product_mz=product,
        cluster_observed_neutral_loss_da=observed_loss,
        has_anchor=has_anchor,
        members=member_objects,
        anchor_members=member_objects if has_anchor else (),
    )
```

- [ ] **Step 2: Run test to verify red**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_feature_family.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'xic_extractor.alignment.feature_family'`.

- [ ] **Step 3: Implement model and builder**

Create `xic_extractor/alignment/feature_family.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from xic_extractor.alignment.models import AlignmentCluster


@dataclass(frozen=True)
class MS1FeatureFamily:
    feature_family_id: str
    neutral_loss_tag: str
    family_center_mz: float
    family_center_rt: float
    family_product_mz: float
    family_observed_neutral_loss_da: float
    has_anchor: bool
    event_clusters: tuple[AlignmentCluster, ...]
    event_cluster_ids: tuple[str, ...]
    event_member_count: int
    evidence: str


def build_ms1_feature_family(
    *,
    family_id: str,
    event_clusters: tuple[AlignmentCluster, ...],
    evidence: str,
) -> MS1FeatureFamily:
    if not event_clusters:
        raise ValueError("MS1 feature family requires at least one event cluster")
    contributors = tuple(
        cluster for cluster in event_clusters if cluster.has_anchor
    ) or event_clusters
    neutral_loss_tags = {cluster.neutral_loss_tag for cluster in event_clusters}
    if len(neutral_loss_tags) != 1:
        raise ValueError("MS1 feature family requires one neutral_loss_tag")
    return MS1FeatureFamily(
        feature_family_id=family_id,
        neutral_loss_tag=event_clusters[0].neutral_loss_tag,
        family_center_mz=median(cluster.cluster_center_mz for cluster in contributors),
        family_center_rt=median(cluster.cluster_center_rt for cluster in contributors),
        family_product_mz=median(cluster.cluster_product_mz for cluster in contributors),
        family_observed_neutral_loss_da=median(
            cluster.cluster_observed_neutral_loss_da for cluster in contributors
        ),
        has_anchor=any(cluster.has_anchor for cluster in event_clusters),
        event_clusters=event_clusters,
        event_cluster_ids=tuple(cluster.cluster_id for cluster in event_clusters),
        event_member_count=sum(len(cluster.members) for cluster in event_clusters),
        evidence=evidence,
    )
```

Modify `xic_extractor/alignment/matrix.py`:

```python
from typing import Protocol


class AlignmentRowLike(Protocol):
    neutral_loss_tag: str
    has_anchor: bool
```

Then change:

```python
clusters: tuple[AlignmentCluster, ...]
```

to:

```python
clusters: tuple[AlignmentCluster | AlignmentRowLike, ...]
```

This is a transitional type compatibility step. `tsv_writer.py` will become family-aware in Task 4.

- [ ] **Step 4: Run tests to verify green**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_feature_family.py tests/test_alignment_models.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/alignment/feature_family.py xic_extractor/alignment/matrix.py tests/test_alignment_feature_family.py
git commit -m "feat(alignment): add MS1 feature family model"
```

### Task 2: Consolidate Event Clusters Into MS1 Feature Families

**Files:**
- Modify: `xic_extractor/alignment/feature_family.py`
- Test: `tests/test_alignment_feature_family.py`

- [ ] **Step 1: Add failing consolidation tests**

Append to `tests/test_alignment_feature_family.py`:

```python
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.feature_family import build_ms1_feature_families
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix


def test_high_shared_subset_event_clusters_consolidate_into_one_family():
    primary = _cluster(
        "ALN000001",
        has_anchor=True,
        mz=242.114,
        rt=12.5927,
        members=("s1", "s2", "s3", "s4", "s5"),
    )
    secondary = _cluster(
        "ALN000002",
        has_anchor=False,
        mz=242.115,
        rt=12.5916,
        members=("s1", "s2", "s3", "s4"),
    )
    matrix = _event_matrix((primary, secondary), sample_order=("s1", "s2", "s3", "s4", "s5"))

    families = build_ms1_feature_families(
        (primary, secondary),
        event_matrix=matrix,
        config=AlignmentConfig(),
    )

    assert len(families) == 1
    assert families[0].event_cluster_ids == ("ALN000001", "ALN000002")
    assert "cid_nl_only" in families[0].evidence
    assert "shared_detected=4" in families[0].evidence


def test_low_shared_subset_event_cluster_stays_separate_for_rare_discovery():
    primary = _cluster(
        "ALN000001",
        has_anchor=True,
        members=("s1", "s2", "s3", "s4", "s5"),
    )
    rare = _cluster(
        "ALN000002",
        has_anchor=False,
        mz=242.115,
        rt=12.5916,
        members=("s1",),
    )
    matrix = _event_matrix((primary, rare), sample_order=("s1", "s2", "s3", "s4", "s5"))

    families = build_ms1_feature_families(
        (primary, rare),
        event_matrix=matrix,
        config=AlignmentConfig(),
    )

    assert [family.event_cluster_ids for family in families] == [
        ("ALN000001",),
        ("ALN000002",),
    ]


def test_full_ms2_signature_conflict_blocks_family_consolidation_when_available():
    left = _cluster("ALN000001", has_anchor=True, members=("s1", "s2", "s3"))
    right = _cluster(
        "ALN000002",
        has_anchor=False,
        mz=242.115,
        rt=12.5916,
        members=("s1", "s2", "s3"),
    )
    object.__setattr__(left, "cluster_ms2_signature", ("126.066", "98.060"))
    object.__setattr__(right, "cluster_ms2_signature", ("126.066", "97.010"))
    matrix = _event_matrix((left, right), sample_order=("s1", "s2", "s3"))

    families = build_ms1_feature_families(
        (left, right),
        event_matrix=matrix,
        config=AlignmentConfig(),
    )

    assert [family.event_cluster_ids for family in families] == [
        ("ALN000001",),
        ("ALN000002",),
    ]


def _event_matrix(
    clusters: tuple[AlignmentCluster, ...],
    *,
    sample_order: tuple[str, ...],
) -> AlignmentMatrix:
    cells = []
    for cluster in clusters:
        member_samples = {member.sample_stem for member in cluster.members}
        for sample in sample_order:
            if sample in member_samples:
                cells.append(_cell(sample, cluster.cluster_id, "detected", area=100.0))
            else:
                cells.append(_cell(sample, cluster.cluster_id, "unchecked", area=None))
    return AlignmentMatrix(
        clusters=clusters,
        cells=tuple(cells),
        sample_order=sample_order,
    )


def _cell(
    sample_stem: str,
    cluster_id: str,
    status: str,
    *,
    area: float | None,
) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster_id,
        status=status,
        area=area,
        apex_rt=12.6 if area is not None else None,
        height=10.0 if area is not None else None,
        peak_start_rt=12.55 if area is not None else None,
        peak_end_rt=12.65 if area is not None else None,
        rt_delta_sec=0.0 if area is not None else None,
        trace_quality="clean" if area is not None else "unchecked",
        scan_support_score=1.0 if area is not None else None,
        source_candidate_id=f"{sample_stem}#{cluster_id}" if area is not None else None,
        source_raw_file=None,
        reason=status,
    )
```

- [ ] **Step 2: Run tests to verify red**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_feature_family.py::test_high_shared_subset_event_clusters_consolidate_into_one_family tests/test_alignment_feature_family.py::test_low_shared_subset_event_cluster_stays_separate_for_rare_discovery tests/test_alignment_feature_family.py::test_full_ms2_signature_conflict_blocks_family_consolidation_when_available -v
```

Expected: FAIL because `build_ms1_feature_families` does not exist.

- [ ] **Step 3: Implement consolidation**

Add to `xic_extractor/alignment/feature_family.py`:

```python
from collections import defaultdict
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignmentMatrix

_PRESENT_STATUSES = {"detected", "rescued"}


def build_ms1_feature_families(
    clusters: tuple[AlignmentCluster, ...],
    *,
    event_matrix: AlignmentMatrix,
    config: AlignmentConfig,
) -> tuple[MS1FeatureFamily, ...]:
    cells_by_cluster = _cells_by_cluster(event_matrix)
    consumed: set[str] = set()
    groups: list[list[AlignmentCluster]] = []
    for cluster in clusters:
        if cluster.cluster_id in consumed:
            continue
        group = [cluster]
        for candidate in clusters:
            if candidate.cluster_id == cluster.cluster_id or candidate.cluster_id in consumed:
                continue
            if all(
                _same_ms1_feature_family(
                    candidate,
                    existing,
                    cells_by_cluster=cells_by_cluster,
                    config=config,
                )
                for existing in group
            ):
                group.append(candidate)
                consumed.add(candidate.cluster_id)
        consumed.add(cluster.cluster_id)
        groups.append(group)
    families = [
        build_ms1_feature_family(
            family_id=f"FAM{index:06d}",
            event_clusters=tuple(_sort_family_group(group, cells_by_cluster)),
            evidence=_family_evidence(group, cells_by_cluster),
        )
        for index, group in enumerate(groups, start=1)
    ]
    return tuple(families)


def _same_ms1_feature_family(
    left: AlignmentCluster,
    right: AlignmentCluster,
    *,
    cells_by_cluster: dict[str, tuple[object, ...]],
    config: AlignmentConfig,
) -> bool:
    if left.neutral_loss_tag != right.neutral_loss_tag:
        return False
    if _ppm(left.cluster_center_mz, right.cluster_center_mz) > config.duplicate_fold_ppm:
        return False
    if abs(left.cluster_center_rt - right.cluster_center_rt) * 60.0 > config.duplicate_fold_rt_sec:
        return False
    if _ppm(left.cluster_product_mz, right.cluster_product_mz) > config.duplicate_fold_product_ppm:
        return False
    if _ppm(left.cluster_observed_neutral_loss_da, right.cluster_observed_neutral_loss_da) > config.duplicate_fold_observed_loss_ppm:
        return False
    if _ms2_signature_conflicts(left, right):
        return False
    left_present = _present_samples(cells_by_cluster.get(left.cluster_id, ()))
    right_present = _present_samples(cells_by_cluster.get(right.cluster_id, ()))
    shared = left_present & right_present
    union = left_present | right_present
    denominator = min(len(left_present), len(right_present))
    overlap = len(shared) / denominator if denominator else 0.0
    jaccard = len(shared) / len(union) if union else 0.0
    if len(shared) < config.duplicate_fold_min_shared_detected_count:
        return False
    if overlap < config.duplicate_fold_min_detected_overlap:
        return False
    # Jaccard protects rare subsets. High absolute shared support is stronger
    # evidence for secondary MS2 triggers from the same MS1 family.
    high_shared_support = len(shared) >= 30 and overlap >= 0.8
    return high_shared_support or jaccard >= config.duplicate_fold_min_detected_jaccard
```

Also add helper functions:

```python
def _cells_by_cluster(matrix: AlignmentMatrix) -> dict[str, tuple[object, ...]]:
    grouped: dict[str, list[object]] = defaultdict(list)
    for cell in matrix.cells:
        grouped[cell.cluster_id].append(cell)
    return {cluster_id: tuple(cells) for cluster_id, cells in grouped.items()}


def _present_samples(cells: tuple[object, ...]) -> frozenset[str]:
    return frozenset(
        cell.sample_stem for cell in cells if cell.status in _PRESENT_STATUSES
    )


def _sort_family_group(
    group: list[AlignmentCluster],
    cells_by_cluster: dict[str, tuple[object, ...]],
) -> tuple[AlignmentCluster, ...]:
    return tuple(
        sorted(
            group,
            key=lambda cluster: (
                0 if cluster.has_anchor else 1,
                -len(_present_samples(cells_by_cluster.get(cluster.cluster_id, ()))),
                cluster.cluster_center_mz,
                cluster.cluster_center_rt,
                cluster.cluster_id,
            ),
        ),
    )


def _family_evidence(
    group: list[AlignmentCluster],
    cells_by_cluster: dict[str, tuple[object, ...]],
) -> str:
    if len(group) == 1:
        return "single_event_cluster"
    shared_counts = []
    overlaps = []
    primary = _sort_family_group(group, cells_by_cluster)[0]
    primary_samples = _present_samples(cells_by_cluster.get(primary.cluster_id, ()))
    for secondary in group:
        if secondary.cluster_id == primary.cluster_id:
            continue
        secondary_samples = _present_samples(cells_by_cluster.get(secondary.cluster_id, ()))
        shared = primary_samples & secondary_samples
        denominator = min(len(primary_samples), len(secondary_samples))
        shared_counts.append(len(shared))
        overlaps.append(len(shared) / denominator if denominator else 0.0)
    return (
        "cid_nl_only;"
        f"event_clusters={len(group)};"
        f"shared_detected={min(shared_counts)};"
        f"overlap={min(overlaps):.3f}"
    )


def _ms2_signature_conflicts(left: AlignmentCluster, right: AlignmentCluster) -> bool:
    left_signature = getattr(left, "cluster_ms2_signature", None)
    right_signature = getattr(right, "cluster_ms2_signature", None)
    if left_signature is None or right_signature is None:
        return False
    return left_signature != right_signature


def _ppm(left: float, right: float) -> float:
    return abs(left - right) / max(abs(left), 1e-12) * 1_000_000.0
```

- [ ] **Step 4: Run tests to verify green**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_feature_family.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/alignment/feature_family.py xic_extractor/alignment/matrix.py tests/test_alignment_feature_family.py
git commit -m "feat(alignment): consolidate event clusters into MS1 families"
```

### Task 3: Family-Centered MS1 Integration

**Files:**
- Create: `xic_extractor/alignment/family_integration.py`
- Test: `tests/test_alignment_family_integration.py`

- [ ] **Step 1: Write failing integration tests**

Create `tests/test_alignment_family_integration.py`:

```python
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from xic_extractor.alignment.family_integration import integrate_feature_family_matrix
from xic_extractor.alignment.feature_family import build_ms1_feature_family
from xic_extractor.alignment.models import AlignmentCluster
from xic_extractor.config import ExtractionConfig


def test_family_integration_uses_family_center_not_event_cluster_area():
    family = build_ms1_feature_family(
        family_id="FAM000001",
        event_clusters=(
            _cluster("ALN000001", mz=242.114, rt=12.5927),
            _cluster("ALN000002", mz=242.115, rt=12.5916),
        ),
        evidence="cid_nl_only",
    )
    source = FakeXICSource(
        rt=np.array([12.55, 12.59, 12.63], dtype=float),
        intensity=np.array([10.0, 100.0, 10.0], dtype=float),
    )

    matrix = integrate_feature_family_matrix(
        (family,),
        sample_order=("s1",),
        raw_sources={"s1": source},
        alignment_config=_alignment_config(),
        peak_config=_peak_config(),
    )

    assert matrix.clusters[0].feature_family_id == "FAM000001"
    assert source.calls == [(family.family_center_mz, 9.5927, 15.5927, 20.0)]
    assert matrix.cells[0].cluster_id == "FAM000001"
    assert matrix.cells[0].status == "detected"
    assert matrix.cells[0].area is not None
    assert matrix.cells[0].reason == "family-centered MS1 integration"


def test_family_integration_missing_raw_source_is_unchecked():
    family = build_ms1_feature_family(
        family_id="FAM000001",
        event_clusters=(_cluster("ALN000001"),),
        evidence="single_event_cluster",
    )

    matrix = integrate_feature_family_matrix(
        (family,),
        sample_order=("s1",),
        raw_sources={},
        alignment_config=_alignment_config(),
        peak_config=_peak_config(),
    )

    assert matrix.cells[0].status == "unchecked"
    assert matrix.cells[0].reason == "missing raw source for family integration"


class FakeXICSource:
    def __init__(self, *, rt, intensity):
        self.rt = rt
        self.intensity = intensity
        self.calls = []

    def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
        self.calls.append((mz, rt_min, rt_max, ppm_tol))
        return self.rt, self.intensity
```

Add helper functions:

```python
def _cluster(
    cluster_id: str,
    *,
    mz: float = 242.114,
    rt: float = 12.5927,
) -> AlignmentCluster:
    member = SimpleNamespace(sample_stem="s1", candidate_id=f"{cluster_id}#s1")
    return AlignmentCluster(
        cluster_id=cluster_id,
        neutral_loss_tag="DNA_dR",
        cluster_center_mz=mz,
        cluster_center_rt=rt,
        cluster_product_mz=126.066,
        cluster_observed_neutral_loss_da=116.048,
        has_anchor=True,
        members=(member,),
        anchor_members=(member,),
    )


def _alignment_config():
    from xic_extractor.alignment.config import AlignmentConfig

    return AlignmentConfig(max_rt_sec=180.0, preferred_ppm=20.0)


def _peak_config() -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=Path("."),
        dll_dir=Path("."),
        output_csv=Path("out.csv"),
        diagnostics_csv=Path("diag.csv"),
        smooth_window=3,
        smooth_polyorder=1,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.01,
        ms2_precursor_tol_da=1.6,
        nl_min_intensity_ratio=0.01,
        resolver_mode="local_minimum",
        resolver_chrom_threshold=0.0,
        resolver_min_search_range_min=0.04,
        resolver_min_relative_height=0.0,
        resolver_min_absolute_height=0.0,
        resolver_min_ratio_top_edge=0.0,
        resolver_peak_duration_min=0.0,
        resolver_peak_duration_max=2.0,
        resolver_min_scans=1,
    )
```

- [ ] **Step 2: Run tests to verify red**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_family_integration.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'xic_extractor.alignment.family_integration'`.

- [ ] **Step 3: Implement family integration**

Create `xic_extractor/alignment/family_integration.py`:

```python
from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.feature_family import MS1FeatureFamily
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.config import ExtractionConfig
from xic_extractor.signal_processing import find_peak_and_area


class FamilyIntegrationSource(Protocol):
    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]: ...


def integrate_feature_family_matrix(
    families: tuple[MS1FeatureFamily, ...],
    *,
    sample_order: tuple[str, ...],
    raw_sources: Mapping[str, FamilyIntegrationSource],
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
) -> AlignmentMatrix:
    cells: list[AlignedCell] = []
    for family in families:
        for sample_stem in sample_order:
            cells.append(
                _integrate_family_cell(
                    family,
                    sample_stem,
                    raw_sources=raw_sources,
                    alignment_config=alignment_config,
                    peak_config=peak_config,
                ),
            )
    return AlignmentMatrix(
        clusters=families,
        cells=tuple(cells),
        sample_order=sample_order,
    )
```

Add helper functions:

```python
def _integrate_family_cell(
    family: MS1FeatureFamily,
    sample_stem: str,
    *,
    raw_sources: Mapping[str, FamilyIntegrationSource],
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
) -> AlignedCell:
    source = raw_sources.get(sample_stem)
    if source is None:
        return _unchecked_cell(
            family,
            sample_stem,
            reason="missing raw source for family integration",
        )
    rt_min = family.family_center_rt - alignment_config.max_rt_sec / 60.0
    rt_max = family.family_center_rt + alignment_config.max_rt_sec / 60.0
    try:
        rt, intensity = source.extract_xic(
            family.family_center_mz,
            rt_min,
            rt_max,
            alignment_config.preferred_ppm,
        )
        rt_array, intensity_array = _validated_trace_arrays(rt, intensity)
        result = find_peak_and_area(
            rt_array,
            intensity_array,
            peak_config,
            preferred_rt=family.family_center_rt,
            strict_preferred_rt=False,
        )
    except Exception:
        return _unchecked_cell(
            family,
            sample_stem,
            reason="family integration could not be checked",
        )
    if result.status != "OK" or result.peak is None:
        return _absent_cell(family, sample_stem)
    peak = result.peak
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=family.feature_family_id,
        status="detected",
        area=peak.area,
        apex_rt=peak.rt,
        height=peak.intensity,
        peak_start_rt=peak.peak_start,
        peak_end_rt=peak.peak_end,
        rt_delta_sec=(peak.rt - family.family_center_rt) * 60.0,
        trace_quality="family_centered",
        scan_support_score=_scan_support_score(
            rt_array,
            peak_start=peak.peak_start,
            peak_end=peak.peak_end,
            scans_target=peak_config.resolver_min_scans,
        ),
        source_candidate_id=None,
        source_raw_file=None,
        reason="family-centered MS1 integration",
    )
```

Add the remaining helper functions exactly:

```python
def _unchecked_cell(
    family: MS1FeatureFamily,
    sample_stem: str,
    *,
    reason: str,
) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=family.feature_family_id,
        status="unchecked",
        area=None,
        apex_rt=None,
        height=None,
        peak_start_rt=None,
        peak_end_rt=None,
        rt_delta_sec=None,
        trace_quality="unchecked",
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason=reason,
    )


def _absent_cell(family: MS1FeatureFamily, sample_stem: str) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=family.feature_family_id,
        status="absent",
        area=None,
        apex_rt=None,
        height=None,
        peak_start_rt=None,
        peak_end_rt=None,
        rt_delta_sec=None,
        trace_quality="missing",
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason="family-centered MS1 integration found no peak",
    )


def _validated_trace_arrays(
    rt: object,
    intensity: object,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    rt_array = np.asarray(rt, dtype=float)
    intensity_array = np.asarray(intensity, dtype=float)
    if (
        rt_array.ndim != 1
        or intensity_array.ndim != 1
        or rt_array.shape != intensity_array.shape
        or not np.all(np.isfinite(rt_array))
        or not np.all(np.isfinite(intensity_array))
    ):
        raise ValueError(
            "family integration trace arrays must be finite one-dimensional pairs",
        )
    return rt_array, intensity_array


def _scan_support_score(
    rt: NDArray[np.float64],
    *,
    peak_start: float,
    peak_end: float,
    scans_target: int,
) -> float:
    if scans_target <= 0:
        return 0.0
    scan_count = int(np.count_nonzero((rt >= peak_start) & (rt <= peak_end)))
    return min(1.0, scan_count / scans_target)
```

- [ ] **Step 4: Run tests to verify green**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_family_integration.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/alignment/family_integration.py tests/test_alignment_family_integration.py
git commit -m "feat(alignment): integrate MS1 feature families"
```

### Task 4: Wire Feature Families Into Alignment Pipeline

**Files:**
- Modify: `xic_extractor/alignment/pipeline.py`
- Test: `tests/test_alignment_pipeline.py`

- [ ] **Step 1: Write failing pipeline test**

Add to `tests/test_alignment_pipeline.py`:

```python
def test_pipeline_builds_feature_families_before_family_integration(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    calls = {}

    event_cluster = _cluster(cluster_id="ALN000001")
    family = SimpleNamespace(
        feature_family_id="FAM000001",
        neutral_loss_tag="DNA_dR",
        family_center_mz=500.0,
        family_center_rt=8.5,
        family_product_mz=384.0,
        family_observed_neutral_loss_da=116.0,
        has_anchor=True,
        event_cluster_ids=("ALN000001",),
        event_member_count=1,
        evidence="single_event_cluster",
    )
    family_matrix = AlignmentMatrix(
        clusters=(family,),
        cells=(),
        sample_order=("Sample_A",),
    )

    monkeypatch.setattr(
        pipeline_module,
        "cluster_candidates",
        lambda candidates, *, config: (event_cluster,),
    )

    def fake_build_families(clusters, *, event_matrix, config):
        calls["families_clusters"] = clusters
        calls["event_matrix"] = event_matrix
        return (family,)

    def fake_integrate(families, *, sample_order, raw_sources, **kwargs):
        calls["integrated_families"] = families
        calls["sample_order"] = sample_order
        calls["raw_sources"] = raw_sources
        return family_matrix

    monkeypatch.setattr(pipeline_module, "build_ms1_feature_families", fake_build_families)
    monkeypatch.setattr(pipeline_module, "integrate_feature_family_matrix", fake_integrate)
    monkeypatch.setattr(
        pipeline_module,
        "_write_outputs_atomic",
        lambda outputs, matrix: calls.setdefault("written_matrix", matrix),
    )

    pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=FakeRawOpener(),
    )

    assert calls["families_clusters"] == (event_cluster,)
    assert calls["integrated_families"] == (family,)
    assert calls["written_matrix"] is family_matrix
```

- [ ] **Step 2: Run test to verify red**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_pipeline.py::test_pipeline_builds_feature_families_before_family_integration -v
```

Expected: FAIL because pipeline does not import/call family builders.

- [ ] **Step 3: Implement pipeline flow**

Modify `xic_extractor/alignment/pipeline.py`:

```python
from xic_extractor.alignment.feature_family import build_ms1_feature_families
from xic_extractor.alignment.family_integration import integrate_feature_family_matrix
```

Replace:

```python
matrix = backfill_alignment_matrix(...)
matrix = fold_near_duplicate_clusters(matrix, config=alignment_config)
```

with:

```python
event_matrix = backfill_alignment_matrix(
    clusters,
    sample_order=batch.sample_order,
    raw_sources=raw_sources,
    alignment_config=alignment_config,
    peak_config=peak_config,
)
families = build_ms1_feature_families(
    clusters,
    event_matrix=event_matrix,
    config=alignment_config,
)
matrix = integrate_feature_family_matrix(
    families,
    sample_order=batch.sample_order,
    raw_sources=raw_sources,
    alignment_config=alignment_config,
    peak_config=peak_config,
)
```

Remove the default pipeline call to `fold_near_duplicate_clusters()`. Keep `folding.py` as legacy transitional code until this branch stabilizes; do not delete it in this task.

- [ ] **Step 4: Run tests to verify green**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_pipeline.py tests/test_alignment_feature_family.py tests/test_alignment_family_integration.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/alignment/pipeline.py tests/test_alignment_pipeline.py
git commit -m "feat(alignment): use MS1 feature families in pipeline"
```

### Task 5: Update TSV Output Contract To Family Rows

**Files:**
- Modify: `xic_extractor/alignment/tsv_writer.py`
- Modify: `xic_extractor/alignment/legacy_io.py`
- Modify: `docs/superpowers/plans/2026-05-11-alignment-output-cli-plan.md`
- Test: `tests/test_alignment_tsv_writer.py`
- Test: `tests/test_alignment_legacy_io.py`

- [ ] **Step 1: Write failing TSV tests**

Add to `tests/test_alignment_tsv_writer.py`:

```python
def test_write_alignment_review_tsv_outputs_feature_family_columns(tmp_path: Path):
    from types import SimpleNamespace
    from xic_extractor.alignment.tsv_writer import write_alignment_review_tsv

    family = SimpleNamespace(
        feature_family_id="FAM000001",
        neutral_loss_tag="DNA_dR",
        family_center_mz=242.114,
        family_center_rt=12.5927,
        family_product_mz=126.066,
        family_observed_neutral_loss_da=116.048,
        has_anchor=True,
        event_cluster_ids=("ALN000001", "ALN000002"),
        event_member_count=124,
        evidence="cid_nl_only;event_clusters=2;shared_detected=45;overlap=0.849",
    )
    matrix = AlignmentMatrix(
        clusters=(family,),
        cells=(
            _cell("sample-a", "detected", cluster_id="FAM000001", area=10.0),
            _cell("sample-b", "absent", cluster_id="FAM000001"),
        ),
        sample_order=("sample-a", "sample-b"),
    )

    rows = _read_tsv(write_alignment_review_tsv(tmp_path / "review.tsv", matrix))

    assert list(rows[0])[:9] == [
        "feature_family_id",
        "neutral_loss_tag",
        "family_center_mz",
        "family_center_rt",
        "family_product_mz",
        "family_observed_neutral_loss_da",
        "has_anchor",
        "event_cluster_count",
        "event_cluster_ids",
    ]
    assert rows[0]["feature_family_id"] == "FAM000001"
    assert rows[0]["event_cluster_count"] == "2"
    assert rows[0]["event_cluster_ids"] == "ALN000001;ALN000002"
    assert rows[0]["event_member_count"] == "124"
    assert rows[0]["family_evidence"].startswith("cid_nl_only;")
```

- [ ] **Step 2: Run test to verify red**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_tsv_writer.py::test_write_alignment_review_tsv_outputs_feature_family_columns -v
```

Expected: FAIL because TSV writer still outputs cluster-oriented columns.

- [ ] **Step 3: Implement family-oriented TSV writer**

In `xic_extractor/alignment/tsv_writer.py`, replace `ALIGNMENT_REVIEW_COLUMNS` with:

```python
ALIGNMENT_REVIEW_COLUMNS = (
    "feature_family_id",
    "neutral_loss_tag",
    "family_center_mz",
    "family_center_rt",
    "family_product_mz",
    "family_observed_neutral_loss_da",
    "has_anchor",
    "event_cluster_count",
    "event_cluster_ids",
    "event_member_count",
    "detected_count",
    "absent_count",
    "unchecked_count",
    "present_rate",
    "representative_samples",
    "family_evidence",
    "warning",
    "reason",
)
```

Update `_review_rows()` to read family attributes:

```python
"feature_family_id": _row_id(cluster),
"neutral_loss_tag": cluster.neutral_loss_tag,
"family_center_mz": _attr(cluster, "family_center_mz", "cluster_center_mz"),
"family_center_rt": _attr(cluster, "family_center_rt", "cluster_center_rt"),
"family_product_mz": _attr(cluster, "family_product_mz", "cluster_product_mz"),
"family_observed_neutral_loss_da": _attr(
    cluster,
    "family_observed_neutral_loss_da",
    "cluster_observed_neutral_loss_da",
),
"event_cluster_count": len(getattr(cluster, "event_cluster_ids", (cluster.cluster_id,))),
"event_cluster_ids": ";".join(getattr(cluster, "event_cluster_ids", (cluster.cluster_id,))),
"event_member_count": getattr(cluster, "event_member_count", len(cluster.members)),
"family_evidence": getattr(cluster, "evidence", getattr(cluster, "fold_evidence", "")),
```

Update `write_alignment_matrix_tsv()` first columns to:

```python
columns = (
    "feature_family_id",
    "neutral_loss_tag",
    "family_center_mz",
    "family_center_rt",
    *matrix.sample_order,
)
```

Add helpers:

```python
def _row_id(row: object) -> str:
    return getattr(row, "feature_family_id", getattr(row, "cluster_id"))


def _attr(row: object, primary: str, fallback: str) -> object:
    return getattr(row, primary, getattr(row, fallback))
```

Update `xic_extractor/alignment/legacy_io.py` by replacing the hard-coded
`cluster_id`/`cluster_center_*` assumptions in `load_xic_alignment()` with these
helpers:

```python
def _xic_id_column(columns: tuple[str, ...]) -> str:
    if "feature_family_id" in columns:
        return "feature_family_id"
    if "cluster_id" in columns:
        return "cluster_id"
    raise ValueError("XIC alignment is missing feature_family_id or cluster_id")


def _xic_mz_column(columns: tuple[str, ...]) -> str:
    if "family_center_mz" in columns:
        return "family_center_mz"
    if "cluster_center_mz" in columns:
        return "cluster_center_mz"
    raise ValueError("XIC alignment is missing family_center_mz or cluster_center_mz")


def _xic_rt_column(columns: tuple[str, ...]) -> str:
    if "family_center_rt" in columns:
        return "family_center_rt"
    if "cluster_center_rt" in columns:
        return "cluster_center_rt"
    raise ValueError("XIC alignment is missing family_center_rt or cluster_center_rt")
```

Then update the beginning of `load_xic_alignment()`:

```python
review_id_column = _xic_id_column(review_columns)
matrix_id_column = _xic_id_column(matrix_columns)
review_mz_column = _xic_mz_column(review_columns)
matrix_mz_column = _xic_mz_column(matrix_columns)
review_rt_column = _xic_rt_column(review_columns)
matrix_rt_column = _xic_rt_column(matrix_columns)
```

Use those variables everywhere the current function reads `cluster_id`,
`cluster_center_mz`, and `cluster_center_rt`. Keep backward compatibility with
existing cluster-oriented test fixtures.

Add this test to `tests/test_alignment_legacy_io.py`:

```python
def test_load_xic_alignment_accepts_feature_family_schema(tmp_path: Path):
    review = tmp_path / "alignment_review.tsv"
    matrix = tmp_path / "alignment_matrix.tsv"
    review.write_text(
        "feature_family_id\tneutral_loss_tag\tfamily_center_mz\tfamily_center_rt\t"
        "family_product_mz\tfamily_observed_neutral_loss_da\thas_anchor\t"
        "event_cluster_count\tevent_cluster_ids\tevent_member_count\t"
        "detected_count\tabsent_count\tunchecked_count\tpresent_rate\t"
        "representative_samples\tfamily_evidence\twarning\treason\n"
        "FAM000001\tDNA_dR\t242.1144\t12.35\t126.067\t116.047\tTRUE\t"
        "2\tALN000001;ALN000002\t124\t1\t0\t0\t1\tTumorBC2312_DNA\t"
        "cid_nl_only\t\tfamily row\n",
        encoding="utf-8",
    )
    matrix.write_text(
        "feature_family_id\tneutral_loss_tag\tfamily_center_mz\tfamily_center_rt\t"
        "TumorBC2312_DNA\n"
        "FAM000001\tDNA_dR\t242.1144\t12.35\t1000\n",
        encoding="utf-8",
    )

    loaded = load_xic_alignment(review, matrix)

    assert loaded.features[0].feature_id == "FAM000001"
    assert loaded.features[0].mz == 242.1144
    assert loaded.features[0].rt_min == 12.35
    assert loaded.features[0].metadata["event_cluster_ids"] == (
        "ALN000001;ALN000002"
    )
```

Update docs `2026-05-11-alignment-output-cli-plan.md` so default outputs are family-oriented. Explicitly state this is a planned contract change from event-cluster rows to MS1 feature-family rows.

- [ ] **Step 4: Run tests to verify green**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_tsv_writer.py tests/test_alignment_legacy_io.py tests/test_alignment_validation_compare.py -v
```

Expected: PASS after validation loaders support `feature_family_id` / `family_center_*` columns.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/alignment/tsv_writer.py xic_extractor/alignment/legacy_io.py docs/superpowers/plans/2026-05-11-alignment-output-cli-plan.md tests/test_alignment_tsv_writer.py tests/test_alignment_legacy_io.py tests/test_alignment_validation_compare.py
git commit -m "feat(alignment): output MS1 feature-family rows"
```

### Task 6: Real-Data Validation Gates

**Files:**
- Generated output only under `output/`

- [ ] **Step 1: Run 8raw alignment**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-align-cli --discovery-batch-index "output\discovery\tissue8_alignment_v1\discovery_batch_index.csv" --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --dll-dir "C:\Xcalibur\system\programs" --output-dir "output\alignment\tissue8_feature_family_v1" --resolver-mode local_minimum
```

Expected: exit code 0 and writes:

```text
output\alignment\tissue8_feature_family_v1\alignment_review.tsv
output\alignment\tissue8_feature_family_v1\alignment_matrix.tsv
```

- [ ] **Step 2: Audit 8raw unresolved near duplicates**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/audit_alignment_near_duplicates.py --review-tsv "output\alignment\tissue8_feature_family_v1\alignment_review.tsv" --matrix-tsv "output\alignment\tissue8_feature_family_v1\alignment_matrix.tsv" --min-shared-samples 3 --min-overlap 0.8
```

Expected: `near_pair_count` should be lower than the pre-family 8raw output. If it is not lower, stop and inspect the top pairs before continuing.

- [ ] **Step 3: Run 85raw alignment**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-align-cli --discovery-batch-index "output\discovery\tissue85_alignment_v1\discovery_batch_index.csv" --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R" --dll-dir "C:\Xcalibur\system\programs" --output-dir "output\alignment\tissue85_feature_family_v1" --resolver-mode local_minimum
```

Expected: exit code 0.

- [ ] **Step 4: Audit 85raw unresolved high-shared near duplicates**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/audit_alignment_near_duplicates.py --review-tsv "output\alignment\tissue85_feature_family_v1\alignment_review.tsv" --matrix-tsv "output\alignment\tissue85_feature_family_v1\alignment_matrix.tsv" --min-shared-samples 30 --min-overlap 0.8
```

Expected:

- high-shared unresolved near pairs should be materially lower than the current event-cluster output.
- `ALN000002/ALN000003`-like 5-medC pair should no longer appear as two final rows.
- If high-shared unresolved pairs remain, capture the top 20 and classify whether they are:
  - full MS2 signature conflict,
  - insufficient family-centered MS1 evidence,
  - true nearby isomer candidate,
  - or algorithm miss.

- [ ] **Step 5: Run legacy validation**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-align-validate-cli --alignment-dir "output\alignment\tissue85_feature_family_v1" --legacy-fh-tsv "C:\Users\user\Desktop\MS Data process package\MS-data aligner\output\program2_DNA\program2_DNA_v4_alignment_standard.tsv" --legacy-metabcombiner-tsv "C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\metabcombiner_fh_format_20260429_130630.tsv" --legacy-combine-fix-xlsx "C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\metabcombiner_fh_format_20260422_213805_combined_fix_20260422_223242.xlsx" --output-dir "output\alignment_validation\tissue85_feature_family_v1" --sample-scope xic
```

Expected:

- `replacement_readiness = manual_review_ready`.
- blocker count remains 0.
- if matched count drops, inspect whether the drop is due to intended row consolidation or lost true features.

- [ ] **Step 6: Run final narrow tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_feature_family.py tests/test_alignment_family_integration.py tests/test_alignment_pipeline.py tests/test_alignment_tsv_writer.py tests/test_alignment_legacy_io.py tests/test_alignment_validation_compare.py tests/test_alignment_near_duplicate_audit.py -v
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/alignment scripts/audit_alignment_near_duplicates.py tests/test_alignment_feature_family.py tests/test_alignment_family_integration.py tests/test_alignment_legacy_io.py tests/test_alignment_near_duplicate_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

Expected: PASS.

- [ ] **Step 7: Commit only code/docs, not generated validation outputs**

```powershell
git status --short
git add xic_extractor/alignment scripts/audit_alignment_near_duplicates.py tests docs/superpowers/plans/2026-05-11-alignment-output-cli-plan.md
git commit -m "feat(alignment): replace event rows with MS1 feature families"
```

## Acceptance Criteria

- Final alignment review/matrix rows represent MS1 feature families.
- MS2 event clusters are evidence attached to a family, not final row identity.
- High-shared subset event clusters consolidate through generic containment/support rules.
- Low-shared rare features remain separate.
- CID-only consolidation is labeled as `cid_nl_only`.
- Future full MS2 signature conflict blocks hard family consolidation.
- Final area values come from family-centered MS1 integration.
- 85raw high-shared unresolved near-duplicate count materially decreases.
- 85raw legacy validation remains `manual_review_ready`.

## Not In Scope

- Untargeted discovery candidate generation changes.
- GUI mode switching.
- HTML report redesign.
- HCD/full MS2 signature extraction. This plan only reserves a conflict blocker if signatures become available.
- One-command `raw-dir -> discovery -> alignment` wrapper.

## Self-Review

- Spec coverage: The plan addresses data model, consolidation, family integration, output contract, and validation.
- Placeholder scan: No unresolved placeholder markers, no empty "add tests" steps, and every task includes concrete test or implementation snippets.
- Type consistency: `MS1FeatureFamily.feature_family_id` is the final row ID; `AlignmentCluster.cluster_id` remains event-cluster ID.
- Known risk: Task 5 is a deliberate output contract change. It must not be mixed with unrelated UX or threshold tuning.
