# Owner-Based Alignment Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace event-first production alignment with owner-based cross-sample alignment while preserving debug access to MS2 event evidence.

**Architecture:** Consume `SampleLocalMS1Owner` objects from the ownership core, align owners across samples using exact NL tag plus m/z/product/observed-loss constraints, and build the production matrix from owner rows rather than raw MS2 event clusters. Rescued cells can fill already anchored owner groups, but cannot create or bridge identity edges.

**Tech Stack:** Python dataclasses, existing `AlignmentConfig`, existing `AlignmentMatrix`, owner models from `2026-05-11-sample-local-ms1-ownership-core-plan.md`, `pytest`.

---

## Prerequisite

Complete `docs/superpowers/plans/2026-05-11-sample-local-ms1-ownership-core-plan.md` first.

This plan assumes these objects exist:

```python
from xic_extractor.alignment.ownership_models import SampleLocalMS1Owner
from xic_extractor.alignment.ownership import build_sample_local_owners
```

## File Structure

- Create `xic_extractor/alignment/owner_clustering.py`
  - Aligns sample-local owners across samples.
  - Exact NL tag equality is required.
  - Requires explicit RT/drift candidate gate.
  - Uses owner primary identity events for product/observed-loss compatibility.
  - Uses detected owners only. No rescued/backfilled cell may seed or bridge.
- Create `xic_extractor/alignment/owner_matrix.py`
  - Builds `AlignmentMatrix` rows from owner clusters.
  - Emits `detected`, `rescued`, `absent`, `unchecked`, `duplicate_assigned`, and `ambiguous_ms1_owner`.
- Create `xic_extractor/alignment/owner_backfill.py`
  - Fills already formed owner clusters with MS1-only rescued cells.
  - Rescued cells are never input to owner clustering.
- Modify `xic_extractor/alignment/matrix.py`
  - Extend `CellStatus` with `duplicate_assigned` and `ambiguous_ms1_owner`.
  - Do not add owner debug fields to `AlignedCell` in this plan; event-to-owner
    provenance belongs in the debug writer from the output-level plan.
- Modify `xic_extractor/alignment/pipeline.py`
  - Add owner-based path after candidate CSV load and raw open.
  - Keep event-first path behind a private compatibility helper until validation passes.
- Modify `xic_extractor/alignment/tsv_writer.py`
  - Count ambiguous owner cells.
  - Keep matrix values blank for duplicate/ambiguous/unchecked/absent.
- Test `tests/test_alignment_owner_clustering.py`
- Test `tests/test_alignment_owner_matrix.py`
- Update `tests/test_alignment_pipeline.py`
- Update `tests/test_alignment_tsv_writer.py`

## Cross-Sample Identity Gates

Use these exact conditions for v1:

```text
canonical neutral_loss_tag must match exactly
precursor ppm <= AlignmentConfig.max_ppm
product ppm <= AlignmentConfig.product_mz_tolerance_ppm
observed loss ppm <= AlignmentConfig.observed_loss_tolerance_ppm
RT distance may exceed preferred_rt_sec only when all MS2/NL gates pass
RT distance must still be <= AlignmentConfig.identity_rt_candidate_window_sec
```

Do not use rescued/backfilled cells in `owner_clustering.py`.

Add this exact config field in Task 2:

```python
identity_rt_candidate_window_sec: float = 180.0
```

## Task 1: Extend Matrix Status Contract

**Files:**
- Modify: `xic_extractor/alignment/matrix.py`
- Test: `tests/test_alignment_tsv_writer.py`

- [ ] **Step 1: Add failing TSV test for blank duplicate and ambiguous cells**

Append to `tests/test_alignment_tsv_writer.py`:

```python
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix


def test_alignment_matrix_tsv_blanks_duplicate_and_ambiguous_cells(tmp_path):
    cluster = _row_like("FAM000001")
    matrix = AlignmentMatrix(
        clusters=(cluster,),
        sample_order=("s1", "s2", "s3"),
        cells=(
            _cell("s1", "FAM000001", "detected", area=100.0),
            _cell("s2", "FAM000001", "duplicate_assigned", area=None),
            _cell("s3", "FAM000001", "ambiguous_ms1_owner", area=None),
        ),
    )

    path = write_alignment_matrix_tsv(tmp_path / "alignment_matrix.tsv", matrix)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[1].endswith("100\t\t")


def _row_like(row_id):
    from types import SimpleNamespace

    return SimpleNamespace(
        feature_family_id=row_id,
        neutral_loss_tag="DNA_dR",
        family_center_mz=242.114,
        family_center_rt=12.593,
        family_product_mz=126.066,
        family_observed_neutral_loss_da=116.048,
        has_anchor=True,
        event_cluster_ids=("ALN000001",),
        event_member_count=1,
        evidence="owner_based",
    )


def _cell(sample, cluster_id, status, *, area):
    return AlignedCell(
        sample_stem=sample,
        cluster_id=cluster_id,
        status=status,
        area=area,
        apex_rt=12.593 if area else None,
        height=1000.0 if area else None,
        peak_start_rt=12.55 if area else None,
        peak_end_rt=12.64 if area else None,
        rt_delta_sec=0.0 if area else None,
        trace_quality="owner_based",
        scan_support_score=1.0 if area else None,
        source_candidate_id="s1#6095" if area else None,
        source_raw_file=None,
        reason=status,
    )
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_tsv_writer.py::test_alignment_matrix_tsv_blanks_duplicate_and_ambiguous_cells -v
```

Expected: FAIL because `CellStatus` does not include these statuses or helper imports are missing.

- [ ] **Step 3: Extend `CellStatus`**

Modify `xic_extractor/alignment/matrix.py`:

```python
CellStatus = Literal[
    "detected",
    "rescued",
    "absent",
    "unchecked",
    "duplicate_assigned",
    "ambiguous_ms1_owner",
]
```

- [ ] **Step 4: Run TSV writer tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_tsv_writer.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/alignment/matrix.py tests/test_alignment_tsv_writer.py
git commit -m "feat: extend alignment cell status contract"
```

## Task 2: Add Owner Cross-Sample Clustering

**Files:**
- Create: `xic_extractor/alignment/owner_clustering.py`
- Test: `tests/test_alignment_owner_clustering.py`

- [ ] **Step 1: Write owner clustering tests**

Create `tests/test_alignment_owner_clustering.py`:

```python
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.owner_clustering import cluster_sample_local_owners
from xic_extractor.alignment.ownership_models import IdentityEvent, SampleLocalMS1Owner


def test_owner_clustering_allows_rt_drift_when_identity_evidence_matches():
    owners = (
        _owner("OWN-s1-000001", "s1", rt=12.59, mz=242.114, candidate_id="s1#6095"),
        _owner("OWN-s2-000001", "s2", rt=12.88, mz=242.1142, candidate_id="s2#6101"),
    )

    clusters = cluster_sample_local_owners(
        owners,
        config=AlignmentConfig(identity_rt_candidate_window_sec=180.0),
    )

    assert len(clusters) == 1
    assert clusters[0].feature_family_id == "FAM000001"
    assert [owner.owner_id for owner in clusters[0].owners] == [
        "OWN-s1-000001",
        "OWN-s2-000001",
    ]
    assert clusters[0].evidence == "owner_identity;detected_edges=1"


def test_owner_clustering_does_not_merge_different_nl_tags():
    owners = (
        _owner("OWN-s1-000001", "s1", rt=12.59, tag="DNA_dR"),
        _owner("OWN-s2-000001", "s2", rt=12.60, tag="DNA_base_loss"),
    )

    clusters = cluster_sample_local_owners(owners, config=AlignmentConfig())

    assert len(clusters) == 2
    assert {cluster.neutral_loss_tag for cluster in clusters} == {
        "DNA_dR",
        "DNA_base_loss",
    }


def test_owner_clustering_keeps_identity_conflict_owner_as_review_only_feature():
    owner = _owner(
        "OWN-s1-000001",
        "s1",
        rt=12.59,
        tag="DNA_dR",
        identity_conflict=True,
    )

    clusters = cluster_sample_local_owners((owner,), config=AlignmentConfig())

    assert len(clusters) == 1
    assert clusters[0].identity_conflict is True
    assert clusters[0].review_only is True


def test_owner_clustering_rejects_implausible_rt_distance():
    owners = (
        _owner("OWN-s1-000001", "s1", rt=8.0, mz=250.000),
        _owner("OWN-s3-000001", "s3", rt=12.0, mz=250.000),
    )

    clusters = cluster_sample_local_owners(
        owners,
        config=AlignmentConfig(identity_rt_candidate_window_sec=180.0),
    )

    assert len(clusters) == 2


def _owner(
    owner_id,
    sample,
    *,
    rt,
    mz=242.114,
    tag="DNA_dR",
    product_mz=126.066,
    observed_loss=116.048,
    candidate_id=None,
    identity_conflict=False,
):
    candidate_id = candidate_id or f"{sample}#1"
    event = IdentityEvent(
        candidate_id=candidate_id,
        sample_stem=sample,
        raw_file=f"{sample}.raw",
        neutral_loss_tag=tag,
        precursor_mz=mz,
        product_mz=product_mz,
        observed_neutral_loss_da=observed_loss,
        seed_rt=rt,
        evidence_score=80,
        seed_event_count=2,
    )
    return SampleLocalMS1Owner(
        owner_id=owner_id,
        sample_stem=sample,
        raw_file=f"{sample}.raw",
        precursor_mz=mz,
        owner_apex_rt=rt,
        owner_peak_start_rt=rt - 0.04,
        owner_peak_end_rt=rt + 0.04,
        owner_area=1000.0,
        owner_height=100.0,
        primary_identity_event=event,
        supporting_events=(),
        identity_conflict=identity_conflict,
        assignment_reason="owner_exact_apex_match",
    )
```

- [ ] **Step 2: Add identity RT gate to config**

Modify `xic_extractor/alignment/config.py`:

```python
identity_rt_candidate_window_sec: float = 180.0
```

Add validation in `AlignmentConfig.__post_init__()`:

```python
        _require_positive(
            "identity_rt_candidate_window_sec",
            self.identity_rt_candidate_window_sec,
        )
```

Add this test to `tests/test_alignment_config.py`:

```python
def test_alignment_config_identity_rt_candidate_window_default():
    assert AlignmentConfig().identity_rt_candidate_window_sec == 180.0
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_owner_clustering.py -v
```

Expected: FAIL because `owner_clustering.py` does not exist.

- [ ] **Step 4: Implement owner clustering**

Create `xic_extractor/alignment/owner_clustering.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.ownership_models import SampleLocalMS1Owner


@dataclass(frozen=True)
class OwnerAlignedFeature:
    feature_family_id: str
    neutral_loss_tag: str
    family_center_mz: float
    family_center_rt: float
    family_product_mz: float
    family_observed_neutral_loss_da: float
    has_anchor: bool
    owners: tuple[SampleLocalMS1Owner, ...]
    evidence: str
    identity_conflict: bool = False
    review_only: bool = False

    @property
    def cluster_id(self) -> str:
        return self.feature_family_id

    @property
    def members(self) -> tuple[SampleLocalMS1Owner, ...]:
        return self.owners

    @property
    def event_cluster_ids(self) -> tuple[str, ...]:
        return tuple(owner.owner_id for owner in self.owners)

    @property
    def event_member_count(self) -> int:
        return sum(len(owner.all_events) for owner in self.owners)


def cluster_sample_local_owners(
    owners: tuple[SampleLocalMS1Owner, ...],
    *,
    config: AlignmentConfig,
) -> tuple[OwnerAlignedFeature, ...]:
    clean_owners = tuple(owner for owner in owners if not owner.identity_conflict)
    conflict_owners = tuple(owner for owner in owners if owner.identity_conflict)
    groups: list[list[SampleLocalMS1Owner]] = []
    for owner in sorted(clean_owners, key=_owner_sort_key):
        for group in groups:
            if all(_compatible_owners(owner, existing, config) for existing in group):
                group.append(owner)
                break
        else:
            groups.append([owner])
    features = [
        _feature_from_group(index, group)
        for index, group in enumerate(groups, start=1)
    ]
    next_index = len(features) + 1
    for owner in sorted(conflict_owners, key=_owner_sort_key):
        features.append(_feature_from_group(next_index, [owner], review_only=True))
        next_index += 1
    return tuple(features)


def _compatible_owners(
    left: SampleLocalMS1Owner,
    right: SampleLocalMS1Owner,
    config: AlignmentConfig,
) -> bool:
    if left.neutral_loss_tag != right.neutral_loss_tag:
        return False
    left_event = left.primary_identity_event
    right_event = right.primary_identity_event
    return (
        _ppm(left.precursor_mz, right.precursor_mz) <= config.max_ppm
        and abs(left.owner_apex_rt - right.owner_apex_rt) * 60.0
        <= config.identity_rt_candidate_window_sec
        and _ppm(left_event.product_mz, right_event.product_mz)
        <= config.product_mz_tolerance_ppm
        and _ppm(
            left_event.observed_neutral_loss_da,
            right_event.observed_neutral_loss_da,
        )
        <= config.observed_loss_tolerance_ppm
    )


def _feature_from_group(
    index: int,
    group: list[SampleLocalMS1Owner],
    *,
    review_only: bool = False,
) -> OwnerAlignedFeature:
    owners = tuple(sorted(group, key=_owner_sort_key))
    return OwnerAlignedFeature(
        feature_family_id=f"FAM{index:06d}",
        neutral_loss_tag=owners[0].neutral_loss_tag,
        family_center_mz=median(owner.precursor_mz for owner in owners),
        family_center_rt=median(owner.owner_apex_rt for owner in owners),
        family_product_mz=median(
            owner.primary_identity_event.product_mz for owner in owners
        ),
        family_observed_neutral_loss_da=median(
            owner.primary_identity_event.observed_neutral_loss_da
            for owner in owners
        ),
        has_anchor=True,
        owners=owners,
        evidence=(
            "identity_conflict_review_only"
            if review_only
            else f"owner_identity;detected_edges={max(0, len(owners) - 1)}"
        ),
        identity_conflict=any(owner.identity_conflict for owner in owners),
        review_only=review_only,
    )


def _owner_sort_key(owner: SampleLocalMS1Owner) -> tuple[object, ...]:
    return (
        owner.neutral_loss_tag,
        owner.precursor_mz,
        owner.owner_apex_rt,
        owner.sample_stem,
        owner.owner_id,
    )


def _ppm(left: float, right: float) -> float:
    denominator = max(abs(left), 1e-12)
    return abs(left - right) / denominator * 1_000_000.0
```

- [ ] **Step 5: Run owner clustering tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_owner_clustering.py tests/test_alignment_config.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add xic_extractor/alignment/config.py xic_extractor/alignment/owner_clustering.py tests/test_alignment_config.py tests/test_alignment_owner_clustering.py
git commit -m "feat: align sample-local MS1 owners"
```

## Task 2b: Add Owner-Centered MS1 Backfill

**Files:**
- Create: `xic_extractor/alignment/owner_backfill.py`
- Test: `tests/test_alignment_owner_backfill.py`

- [ ] **Step 1: Write owner backfill tests**

Create `tests/test_alignment_owner_backfill.py`:

```python
import numpy as np

from tests.test_alignment_owner_clustering import _owner
from tests.test_alignment_ownership import FakeXICSource, _peak_config
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.owner_backfill import build_owner_backfill_cells
from xic_extractor.alignment.owner_clustering import cluster_sample_local_owners


def test_owner_backfill_rescues_missing_sample_without_creating_identity_edge():
    features = cluster_sample_local_owners(
        (_owner("OWN-s1-000001", "s1", rt=12.59),),
        config=AlignmentConfig(),
    )
    source = FakeXICSource(
        rt=np.array([12.55, 12.58, 12.59, 12.62, 12.65], dtype=float),
        intensity=np.array([0.0, 20.0, 100.0, 20.0, 0.0], dtype=float),
    )

    cells = build_owner_backfill_cells(
        features,
        sample_order=("s1", "s2"),
        raw_sources={"s2": source},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
    )

    assert len(cells) == 1
    assert cells[0].sample_stem == "s2"
    assert cells[0].status == "rescued"
    assert cells[0].reason == "owner-centered MS1 backfill"


def test_owner_backfill_skips_review_only_identity_conflict_features():
    owner = _owner("OWN-s1-000001", "s1", rt=12.59, identity_conflict=True)
    features = cluster_sample_local_owners((owner,), config=AlignmentConfig())

    cells = build_owner_backfill_cells(
        features,
        sample_order=("s1", "s2"),
        raw_sources={},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
    )

    assert cells == ()
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_owner_backfill.py -v
```

Expected: FAIL because `owner_backfill.py` does not exist.

- [ ] **Step 3: Implement owner backfill**

Create `xic_extractor/alignment/owner_backfill.py`:

```python
from __future__ import annotations

from collections.abc import Mapping

import numpy as np
from numpy.typing import NDArray

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell
from xic_extractor.alignment.owner_clustering import OwnerAlignedFeature
from xic_extractor.alignment.ownership import OwnershipXICSource
from xic_extractor.config import ExtractionConfig
from xic_extractor.signal_processing import find_peak_and_area


def build_owner_backfill_cells(
    features: tuple[OwnerAlignedFeature, ...],
    *,
    sample_order: tuple[str, ...],
    raw_sources: Mapping[str, OwnershipXICSource],
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
) -> tuple[AlignedCell, ...]:
    cells: list[AlignedCell] = []
    for feature in features:
        if feature.review_only:
            continue
        detected_samples = {owner.sample_stem for owner in feature.owners}
        for sample_stem in sample_order:
            if sample_stem in detected_samples:
                continue
            source = raw_sources.get(sample_stem)
            if source is None:
                continue
            rescued = _rescue_feature_cell(
                feature,
                sample_stem,
                source,
                alignment_config=alignment_config,
                peak_config=peak_config,
            )
            if rescued is not None:
                cells.append(rescued)
    return tuple(cells)


def _rescue_feature_cell(
    feature: OwnerAlignedFeature,
    sample_stem: str,
    source: OwnershipXICSource,
    *,
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
) -> AlignedCell | None:
    rt_min = feature.family_center_rt - alignment_config.max_rt_sec / 60.0
    rt_max = feature.family_center_rt + alignment_config.max_rt_sec / 60.0
    rt, intensity = source.extract_xic(
        feature.family_center_mz,
        rt_min,
        rt_max,
        alignment_config.preferred_ppm,
    )
    rt_array, intensity_array = _validated_trace_arrays(rt, intensity)
    result = find_peak_and_area(
        rt_array,
        intensity_array,
        peak_config,
        preferred_rt=feature.family_center_rt,
        strict_preferred_rt=False,
    )
    if result.status != "OK" or result.peak is None:
        return None
    peak = result.peak
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=feature.feature_family_id,
        status="rescued",
        area=peak.area,
        apex_rt=peak.rt,
        height=peak.intensity,
        peak_start_rt=peak.peak_start,
        peak_end_rt=peak.peak_end,
        rt_delta_sec=(peak.rt - feature.family_center_rt) * 60.0,
        trace_quality="owner_backfill",
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason="owner-centered MS1 backfill",
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
        raise ValueError("owner backfill trace arrays must be finite one-dimensional pairs")
    return rt_array, intensity_array
```

- [ ] **Step 4: Run owner backfill tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_owner_backfill.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/alignment/owner_backfill.py tests/test_alignment_owner_backfill.py
git commit -m "feat: add owner-centered MS1 backfill"
```

## Task 3: Build Owner-Based Matrix

**Files:**
- Create: `xic_extractor/alignment/owner_matrix.py`
- Test: `tests/test_alignment_owner_matrix.py`

- [ ] **Step 1: Write owner matrix tests**

Create `tests/test_alignment_owner_matrix.py`:

```python
from xic_extractor.alignment.owner_clustering import cluster_sample_local_owners
from xic_extractor.alignment.owner_matrix import build_owner_alignment_matrix
from xic_extractor.alignment.config import AlignmentConfig
from tests.test_alignment_owner_clustering import _owner


def test_owner_matrix_uses_detected_owner_area_and_blank_missing_values():
    features = cluster_sample_local_owners(
        (
            _owner("OWN-s1-000001", "s1", rt=12.59),
            _owner("OWN-s2-000001", "s2", rt=12.88),
        ),
        config=AlignmentConfig(),
    )

    matrix = build_owner_alignment_matrix(
        features,
        sample_order=("s1", "s2", "s3"),
        ambiguous_by_sample={},
        rescued_cells=(),
    )

    cells = {(cell.cluster_id, cell.sample_stem): cell for cell in matrix.cells}
    assert cells[("FAM000001", "s1")].status == "detected"
    assert cells[("FAM000001", "s2")].status == "detected"
    assert cells[("FAM000001", "s3")].status == "absent"
    assert cells[("FAM000001", "s3")].area is None


def test_owner_matrix_marks_ambiguous_sample_as_checked_but_blank():
    features = cluster_sample_local_owners(
        (_owner("OWN-s1-000001", "s1", rt=12.59),),
        config=AlignmentConfig(),
    )

    matrix = build_owner_alignment_matrix(
        features,
        sample_order=("s1", "s2"),
        ambiguous_by_sample={"s2": ("AMB-s2-000001",)},
        rescued_cells=(),
    )

    cell = [cell for cell in matrix.cells if cell.sample_stem == "s2"][0]
    assert cell.status == "ambiguous_ms1_owner"
    assert cell.area is None
    assert cell.reason == "checked local MS1 region is ambiguous"


def test_owner_matrix_prefers_rescued_cell_over_absent_blank():
    features = cluster_sample_local_owners(
        (_owner("OWN-s1-000001", "s1", rt=12.59),),
        config=AlignmentConfig(),
    )
    rescued = _rescued_cell("FAM000001", "s2", area=88.0)

    matrix = build_owner_alignment_matrix(
        features,
        sample_order=("s1", "s2"),
        ambiguous_by_sample={},
        rescued_cells=(rescued,),
    )

    cell = [cell for cell in matrix.cells if cell.sample_stem == "s2"][0]
    assert cell.status == "rescued"
    assert cell.area == 88.0


def _rescued_cell(cluster_id, sample_stem, *, area):
    from xic_extractor.alignment.matrix import AlignedCell

    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster_id,
        status="rescued",
        area=area,
        apex_rt=12.59,
        height=100.0,
        peak_start_rt=12.55,
        peak_end_rt=12.65,
        rt_delta_sec=0.0,
        trace_quality="owner_backfill",
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason="owner-centered MS1 backfill",
    )
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_owner_matrix.py -v
```

Expected: FAIL because `owner_matrix.py` does not exist.

- [ ] **Step 3: Implement owner matrix builder**

Create `xic_extractor/alignment/owner_matrix.py`:

```python
from __future__ import annotations

from collections.abc import Mapping

from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.owner_clustering import OwnerAlignedFeature
from xic_extractor.alignment.ownership_models import SampleLocalMS1Owner


def build_owner_alignment_matrix(
    features: tuple[OwnerAlignedFeature, ...],
    *,
    sample_order: tuple[str, ...],
    ambiguous_by_sample: Mapping[str, tuple[str, ...]],
    rescued_cells: tuple[AlignedCell, ...],
) -> AlignmentMatrix:
    cells: list[AlignedCell] = []
    for feature in features:
        owners_by_sample = {owner.sample_stem: owner for owner in feature.owners}
        rescued_by_sample = {
            cell.sample_stem: cell
            for cell in rescued_cells
            if cell.cluster_id == feature.feature_family_id
        }
        for sample_stem in sample_order:
            owner = owners_by_sample.get(sample_stem)
            if owner is not None:
                cells.append(_detected_cell(feature, owner))
            elif sample_stem in rescued_by_sample:
                cells.append(rescued_by_sample[sample_stem])
            elif ambiguous_by_sample.get(sample_stem):
                cells.append(_ambiguous_cell(feature, sample_stem))
            else:
                cells.append(_absent_cell(feature, sample_stem))
    return AlignmentMatrix(
        clusters=features,
        cells=tuple(cells),
        sample_order=sample_order,
    )


def _detected_cell(feature: OwnerAlignedFeature, owner: SampleLocalMS1Owner) -> AlignedCell:
    return AlignedCell(
        sample_stem=owner.sample_stem,
        cluster_id=feature.feature_family_id,
        status="detected",
        area=owner.owner_area,
        apex_rt=owner.owner_apex_rt,
        height=owner.owner_height,
        peak_start_rt=owner.owner_peak_start_rt,
        peak_end_rt=owner.owner_peak_end_rt,
        rt_delta_sec=(owner.owner_apex_rt - feature.family_center_rt) * 60.0,
        trace_quality="owner_detected",
        scan_support_score=None,
        source_candidate_id=owner.primary_identity_event.candidate_id,
        source_raw_file=None,
        reason="sample-local MS1 owner with original MS2 evidence",
    )


def _absent_cell(feature: OwnerAlignedFeature, sample_stem: str) -> AlignedCell:
    return _blank_cell(feature, sample_stem, status="absent", reason="no local MS1 owner")


def _ambiguous_cell(feature: OwnerAlignedFeature, sample_stem: str) -> AlignedCell:
    return _blank_cell(
        feature,
        sample_stem,
        status="ambiguous_ms1_owner",
        reason="checked local MS1 region is ambiguous",
    )


def _blank_cell(
    feature: OwnerAlignedFeature,
    sample_stem: str,
    *,
    status: str,
    reason: str,
) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=feature.feature_family_id,
        status=status,
        area=None,
        apex_rt=None,
        height=None,
        peak_start_rt=None,
        peak_end_rt=None,
        rt_delta_sec=None,
        trace_quality=status,
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason=reason,
    )
```

- [ ] **Step 4: Run owner matrix tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_owner_matrix.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/alignment/owner_matrix.py tests/test_alignment_owner_matrix.py
git commit -m "feat: build matrix from MS1 owners"
```

## Task 4: Wire Owner Pipeline Behind Alignment Run

**Files:**
- Modify: `xic_extractor/alignment/pipeline.py`
- Test: `tests/test_alignment_pipeline.py`

- [ ] **Step 1: Add pipeline test proving owners are built before alignment**

Add a fake raw source test to `tests/test_alignment_pipeline.py` that creates a batch index with two same-sample candidate events and asserts only one feature row appears in `alignment_matrix.tsv`:

```python
def test_run_alignment_uses_sample_local_ownership_before_output(tmp_path):
    batch_index = _write_batch_with_candidates(
        tmp_path,
        sample_stem="s1",
        candidate_rows=[
            _candidate_row("s1#6095", best_seed_rt="12.5927"),
            _candidate_row("s1#6096", best_seed_rt="12.5940"),
        ],
    )
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "s1.raw").write_text("fake", encoding="utf-8")

    outputs = run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path,
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=lambda raw_path, dll_dir: FakeRawContext(
            FakeXICSource(
                rt=np.array([12.55, 12.58, 12.593, 12.61, 12.64], dtype=float),
                intensity=np.array([0.0, 30.0, 100.0, 30.0, 0.0], dtype=float),
            )
        ),
    )

    rows = outputs.matrix_tsv.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 2
    assert rows[1].startswith("FAM000001\tDNA_dR\t")
```

Add these local helpers if the file does not already expose equivalent local
helpers:

```python
import csv
from xic_extractor.discovery.models import DISCOVERY_CANDIDATE_COLUMNS


def _write_batch_with_candidates(tmp_path, *, sample_stem, candidate_rows):
    candidate_path = tmp_path / sample_stem / "discovery_candidates.csv"
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    with candidate_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DISCOVERY_CANDIDATE_COLUMNS)
        writer.writeheader()
        writer.writerows(candidate_rows)
    batch_path = tmp_path / "discovery_batch_index.csv"
    with batch_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("sample_stem", "raw_file", "candidate_csv"),
        )
        writer.writeheader()
        writer.writerow(
            {
                "sample_stem": sample_stem,
                "raw_file": f"{sample_stem}.raw",
                "candidate_csv": str(candidate_path.relative_to(tmp_path)),
            }
        )
    return batch_path


def _candidate_row(candidate_id, *, best_seed_rt):
    row = {column: "" for column in DISCOVERY_CANDIDATE_COLUMNS}
    row.update(
        {
            "review_priority": "HIGH",
            "evidence_tier": "strong",
            "evidence_score": "80",
            "ms2_support": "strict_nl",
            "ms1_support": "peak",
            "rt_alignment": "seed",
            "family_context": "single",
            "candidate_id": candidate_id,
            "feature_family_id": "FF000001",
            "feature_family_size": "1",
            "feature_superfamily_id": "SF000001",
            "feature_superfamily_size": "1",
            "feature_superfamily_role": "representative",
            "feature_superfamily_confidence": "MEDIUM",
            "feature_superfamily_evidence": "single",
            "precursor_mz": "242.114",
            "product_mz": "126.066",
            "observed_neutral_loss_da": "116.048",
            "best_seed_rt": best_seed_rt,
            "seed_event_count": "2",
            "ms1_peak_found": "TRUE",
            "ms1_apex_rt": "",
            "ms1_area": "",
            "ms2_product_max_intensity": "1000",
            "reason": "synthetic",
            "raw_file": "s1.raw",
            "sample_stem": "s1",
            "best_ms2_scan_id": "6095",
            "seed_scan_ids": "6095",
            "neutral_loss_tag": "DNA_dR",
            "configured_neutral_loss_da": "116.0474",
            "neutral_loss_mass_error_ppm": "1.0",
            "rt_seed_min": "12.55",
            "rt_seed_max": "12.64",
            "ms1_search_rt_min": "12.50",
            "ms1_search_rt_max": "12.70",
            "ms1_seed_delta_min": "",
            "ms1_peak_rt_start": "",
            "ms1_peak_rt_end": "",
            "ms1_height": "",
            "ms1_trace_quality": "synthetic",
            "ms1_scan_support_score": "",
        }
    )
    return row


class FakeRawContext:
    def __init__(self, source):
        self.source = source

    def __enter__(self):
        return self.source

    def __exit__(self, exc_type, exc, tb):
        return False
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_pipeline.py::test_run_alignment_uses_sample_local_ownership_before_output -v
```

Expected: FAIL because pipeline still emits event/family rows.

- [ ] **Step 3: Replace event-family production path with owner path**

In `xic_extractor/alignment/pipeline.py`, after raw handles are opened, replace the event-family block:

```python
        clusters = cluster_candidates(candidates, config=alignment_config)
        event_matrix = backfill_alignment_matrix(...)
        families = build_ms1_feature_families(...)
        matrix = integrate_feature_family_matrix(...)
```

with:

```python
        ownership = build_sample_local_owners(
            candidates,
            raw_sources=raw_sources,
            alignment_config=alignment_config,
            peak_config=peak_config,
        )
        features = cluster_sample_local_owners(
            ownership.owners,
            config=alignment_config,
        )
        rescued_cells = build_owner_backfill_cells(
            features,
            sample_order=batch.sample_order,
            raw_sources=raw_sources,
            alignment_config=alignment_config,
            peak_config=peak_config,
        )
        ambiguous_by_sample = _ambiguous_by_sample(ownership.ambiguous_records)
        matrix = build_owner_alignment_matrix(
            features,
            sample_order=batch.sample_order,
            ambiguous_by_sample=ambiguous_by_sample,
            rescued_cells=rescued_cells,
        )
```

Add imports:

```python
from xic_extractor.alignment.owner_backfill import build_owner_backfill_cells
from xic_extractor.alignment.owner_clustering import cluster_sample_local_owners
from xic_extractor.alignment.owner_matrix import build_owner_alignment_matrix
from xic_extractor.alignment.ownership import build_sample_local_owners
```

Add helper:

```python
def _ambiguous_by_sample(records):
    grouped: dict[str, list[str]] = {}
    for record in records:
        grouped.setdefault(record.sample_stem, []).append(record.ambiguity_id)
    return {sample: tuple(ids) for sample, ids in grouped.items()}
```

Do not delete old event-family modules in this task; they remain available for comparison until validation passes.

- [ ] **Step 4: Run pipeline and owner tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_pipeline.py tests/test_alignment_owner_clustering.py tests/test_alignment_owner_matrix.py tests/test_alignment_ownership.py -v
```

Expected: PASS.

- [ ] **Step 5: Run run_alignment CLI tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_run_alignment.py -v
```

Expected: PASS. If CLI tests assume exact old row counts, update only assertions that refer to event-row count and keep artifact path assertions unchanged.

- [ ] **Step 6: Commit**

```powershell
git add xic_extractor/alignment/pipeline.py tests/test_alignment_pipeline.py tests/test_run_alignment.py
git commit -m "feat: run alignment on sample-local MS1 owners"
```

## Task 5: Add Identity Edge Boundary Regressions

**Files:**
- Test: `tests/test_alignment_owner_clustering.py`

- [ ] **Step 1: Add regression test**

Append:

```python
def test_implausible_rt_distance_does_not_merge_owner_clusters():
    detected_left = _owner("OWN-s1-000001", "s1", rt=8.0, mz=250.000)
    detected_right = _owner("OWN-s3-000001", "s3", rt=12.0, mz=250.000)

    clusters = cluster_sample_local_owners(
        (detected_left, detected_right),
        config=AlignmentConfig(identity_rt_candidate_window_sec=180.0),
    )

    assert len(clusters) == 2
    assert [{owner.sample_stem for owner in cluster.owners} for cluster in clusters] == [
        {"s1"},
        {"s3"},
    ]


def test_owner_clustering_api_has_no_cell_status_input():
    import inspect

    parameters = inspect.signature(cluster_sample_local_owners).parameters

    assert tuple(parameters) == ("owners", "config")
```

This pins two contracts:

- RT/drift plausibility is a hard identity edge gate. Same NL/mass/product alone
  cannot merge owners minutes apart.
- Rescued/backfilled `AlignedCell` objects are not input to identity clustering.
  Only detected `SampleLocalMS1Owner` objects can create alignment edges.

- [ ] **Step 2: Run owner clustering tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_owner_clustering.py -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```powershell
git add tests/test_alignment_owner_clustering.py
git commit -m "test: pin owner identity edge boundaries"
```

## Task 6: Run Validation Smoke

**Files:**
- No code changes unless validation exposes a reproducible bug.

- [ ] **Step 1: Run narrow unit tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_ownership.py tests/test_alignment_owner_clustering.py tests/test_alignment_owner_matrix.py tests/test_alignment_pipeline.py tests/test_alignment_tsv_writer.py tests/test_run_alignment.py -v
```

Expected: PASS.

- [ ] **Step 2: Run ruff**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/alignment tests/test_alignment_ownership.py tests/test_alignment_owner_clustering.py tests/test_alignment_owner_matrix.py
```

Expected: PASS.

- [ ] **Step 3: Run 8-RAW alignment smoke**

Use this discovery batch path for the smoke run:

```text
output\discovery_8raw\discovery_batch_index.csv
```

If that file is missing, stop and generate the discovery batch in a separate
step before running alignment. Do not silently switch to a different input
batch, because row-count observations must remain comparable.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/run_alignment.py --discovery-batch-index output\discovery_8raw\discovery_batch_index.csv --raw-dir "C:\Xcalibur\data\20251219_need process data\XIC test" --dll-dir "C:\Xcalibur\system\programs" --output-dir output\alignment\owner_based_8raw_smoke --emit-alignment-cells --emit-alignment-status-matrix
```

Expected:

- command exits 0;
- `alignment_matrix.tsv` exists;
- `alignment_review.tsv` exists;
- `alignment_cells.tsv` exists because debug flags were provided;
- matrix row count decreases for Case 1/3/4-like duplicate event rows;
- Case 2-like unresolved doublet remains separate or ambiguous.

- [ ] **Step 4: Capture validation notes**

Create or append `output/alignment/owner_based_8raw_smoke/validation_notes.md` with:

```markdown
# Owner-Based 8-RAW Smoke Notes

- Command:
- Matrix rows:
- Review rows:
- Case 1 m/z 242.114 observation:
- Case 2 m/z 296.074 observation:
- Case 3 m/z 322.143 observation:
- Case 4 m/z 251.084 observation:
- Blockers:
```

Do not commit `output/`.

## Acceptance Criteria

- Cross-sample grouping consumes `SampleLocalMS1Owner`, not raw event candidates.
- Exact NL tag equality gates production identity.
- One sample-local owner area is not cloned into multiple production rows.
- `ambiguous_ms1_owner` remains blank and visible in status/debug outputs.
- Existing CLI still runs without traceback.

## Stop Conditions

Stop and report before broad fixes if:

- Owner-based pipeline increases production rows versus event-first output for Case 1/3/4-like fixtures.
- The only way to pass tests is to let rescued/backfilled cells enter identity clustering.
- Real 8-RAW smoke shows obvious same-owner events still emitted as multiple production rows.
