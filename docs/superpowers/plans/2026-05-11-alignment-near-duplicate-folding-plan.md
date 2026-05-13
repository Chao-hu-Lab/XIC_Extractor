# Alignment Near-Duplicate Folding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse highly credible near-duplicate alignment clusters into one review entity without weakening the conservative alignment core.

**Architecture:** Keep Plan 1 clustering conservative. Add a post-backfill folding layer that inspects `AlignmentMatrix` clusters and cells, folds only strong duplicate pairs/groups, and writes fold evidence into the existing alignment review surface. This avoids m/z/RT-only chain merges while preserving sensitivity from direct `.raw` discovery.

**Tech Stack:** Python 3.13, pytest, `uv`, existing `xic_extractor.alignment` modules.

---

## Scope

This is a small corrective layer for real-data findings from tissue 85/raw:

- 5-medC-like duplicate: two clusters at almost identical m/z/RT/product/NL, one anchored and one no-anchor.
- Many near-identical no-anchor pairs are likely secondary MS2 triggers, not separate biological features.
- High `rescued_count` often means MS1 backfill recovered aligned signal; it should not be presented as automatically bad.

This plan does **not**:

- Relax core clustering tolerances.
- Use connected components over broad `20 ppm / 60 sec` windows.
- Add cross-sample alignment Plan 5+ behavior.
- Change discovery candidate generation.
- Merge clusters when MS2 product or observed neutral loss conflict.

## File Structure

- Modify `xic_extractor/alignment/config.py`
  - Add fold thresholds with conservative defaults.
- Create `xic_extractor/alignment/folding.py`
  - Own duplicate-candidate detection, strict fold compatibility, matrix cell merge, and fold metadata.
- Modify `xic_extractor/alignment/models.py`
  - Add defaulted fold metadata to `AlignmentCluster`.
- Modify `xic_extractor/alignment/pipeline.py`
  - Call folding after `backfill_alignment_matrix()` and before TSV writing.
- Modify `xic_extractor/alignment/tsv_writer.py`
  - Add audit columns and rename high-rescue wording in reason/warning.
- Add `tests/test_alignment_folding.py`
  - Unit contract for folding logic.
- Update `tests/test_alignment_tsv_writer.py`
  - Output columns and warning semantics.
- Update `tests/test_alignment_pipeline.py`
  - Pipeline calls folding before writing.

## Folding Contract

Two clusters may fold only when all are true:

- Same `neutral_loss_tag`.
- `mz_ppm <= duplicate_fold_ppm` default `5.0`.
- `rt_delta_sec <= duplicate_fold_rt_sec` default `2.0`.
- `product_mz` compatible within `duplicate_fold_product_ppm`, default `10.0`.
- `observed_neutral_loss_da` compatible within `duplicate_fold_observed_loss_ppm`, default `10.0`.
- CID-only MS2 evidence is explicitly limited:
  - Current tissue data only provides CID-style neutral-loss/product evidence, not HCD-like full MS2 pattern evidence.
  - v1 must not claim structural identity from full MS2 pattern matching.
  - If future candidate metadata includes full MS2 signature fields, conflicting signatures must block hard folding.
  - If full MS2 signature is absent, hard folding is allowed only through the stricter CID-NL + cross-sample gates below, and output must label the fold basis as `cid_nl_only`.
- Detected sample overlap coefficient is high:
  - `intersection(detected samples) / min(detected_a, detected_b) >= duplicate_fold_min_detected_overlap`
  - default `0.80`.
  - This is the hard evidence gate. `rescued` / MS1-backfilled cells must not create fold eligibility by themselves.
- Absolute shared detected support is high:
  - `shared_detected_count >= duplicate_fold_min_shared_detected_count`
  - default `3`.
  - This prevents one-sample rare `.raw` discoveries from being folded into prevalent features only because overlap coefficient is mathematically high.
- Detected Jaccard is high enough:
  - `intersection(detected samples) / union(detected samples) >= duplicate_fold_min_detected_jaccard`
  - default `0.60`.
  - This prevents tiny subset clusters from being silently absorbed into broad clusters.
- Present sample overlap coefficient is also high:
  - `intersection(present samples) / min(present_a, present_b) >= duplicate_fold_min_present_overlap`
  - default `0.80`.
  - This is a consistency gate after detected overlap passes, not a substitute for shared detected evidence.
- No chain folding:
  - A candidate fold target must be compatible with the primary cluster and every already-folded secondary cluster.
- Primary cluster selection:
  - Prefer `has_anchor=True`.
  - Then higher detected count.
  - Then higher present count.
  - Then lower unchecked count.
  - Then lower absent count.
  - Then lower m/z, lower RT, lower cluster id.
- Output order:
  - Preserve retained primary cluster order from the original alignment matrix.
  - Do not reorder by anchor/evidence score in the public TSV outputs.

Cell merge:

- For each sample, keep the primary cell when it is `detected` or `rescued`.
- If primary is `absent` or `unchecked` and secondary is `detected` or `rescued`, copy the secondary cell into the primary cluster id and append `; folded from <secondary cluster id>` to `reason`.
- Do not sum areas from primary and secondary cells.
- If multiple folded secondary cells can fill the same sample, choose deterministically:
  - `detected` beats `rescued`.
  - Higher `scan_support_score` wins.
  - `trace_quality` order: `clean` > `weak` > `poor` > other/blank.
  - Smaller absolute `rt_delta_sec` wins.
  - Larger positive area wins.
  - Lower source cluster id wins.
- Dropped secondary clusters must be recorded on the primary cluster:
  - `folded_cluster_ids`
  - `folded_member_count`

Output:

- `alignment_review.tsv` adds:
  - `folded_cluster_count`
  - `folded_cluster_ids`
  - `folded_member_count`
  - `folded_sample_fill_count`
  - `fold_evidence`
- `high_rescue_rate` is renamed to `high_backfill_dependency`.
- Reason text uses `MS1 backfilled`, not `rescued`, to reduce negative bias.

---

### Task 0: Preflight Stale Review Findings

**Files:**
- Inspect: `xic_extractor/alignment/backfill.py`
- Inspect: `xic_extractor/alignment/pipeline.py`
- Inspect: `scripts/run_alignment.py`
- Inspect: `xic_extractor/alignment/tsv_writer.py`
- Test: existing tests only

- [ ] **Step 1: Verify the pasted review findings are not still open**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_backfill.py tests/test_alignment_pipeline.py tests/test_run_alignment.py tests/test_alignment_tsv_writer.py -v
```

Expected: PASS. If it fails on NaN/Inf, atomic replace, missing candidate CSV, or `member_count`, fix that issue before Task 1.

- [ ] **Step 2: Commit only if code changes were needed**

If no code changes were needed, do not commit.

If fixes were needed:

```powershell
git add xic_extractor/alignment tests scripts
git commit -m "fix(alignment): close output safety review gaps"
```

### Task 1: Add Folding Config and Cluster Metadata

**Files:**
- Modify: `xic_extractor/alignment/config.py`
- Modify: `xic_extractor/alignment/models.py`
- Test: `tests/test_alignment_config.py`
- Test: `tests/test_alignment_models.py`

- [ ] **Step 1: Write failing config/model tests**

Add to `tests/test_alignment_config.py`:

```python
import pytest

from xic_extractor.alignment.config import AlignmentConfig


def test_alignment_config_duplicate_fold_defaults_are_conservative():
    config = AlignmentConfig()

    assert config.duplicate_fold_ppm == 5.0
    assert config.duplicate_fold_rt_sec == 2.0
    assert config.duplicate_fold_product_ppm == 10.0
    assert config.duplicate_fold_observed_loss_ppm == 10.0
    assert config.duplicate_fold_min_detected_overlap == 0.80
    assert config.duplicate_fold_min_shared_detected_count == 3
    assert config.duplicate_fold_min_detected_jaccard == 0.60
    assert config.duplicate_fold_min_present_overlap == 0.80


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("duplicate_fold_ppm", 0.0),
        ("duplicate_fold_rt_sec", 0.0),
        ("duplicate_fold_product_ppm", 0.0),
        ("duplicate_fold_observed_loss_ppm", 0.0),
        ("duplicate_fold_min_detected_overlap", -0.1),
        ("duplicate_fold_min_detected_overlap", 1.1),
        ("duplicate_fold_min_shared_detected_count", 0),
        ("duplicate_fold_min_detected_jaccard", -0.1),
        ("duplicate_fold_min_detected_jaccard", 1.1),
        ("duplicate_fold_min_present_overlap", -0.1),
        ("duplicate_fold_min_present_overlap", 1.1),
    ],
)
def test_alignment_config_rejects_invalid_duplicate_fold_values(field, value):
    kwargs = {field: value}

    with pytest.raises(ValueError, match=field):
        AlignmentConfig(**kwargs)
```

Add to `tests/test_alignment_models.py`:

```python
from types import SimpleNamespace

from xic_extractor.alignment.models import build_alignment_cluster


def test_alignment_cluster_fold_metadata_defaults_to_empty():
    candidate = SimpleNamespace(
        sample_stem="sample-a",
        neutral_loss_tag="DNA_dR",
        precursor_mz=242.114,
        product_mz=126.066,
        observed_neutral_loss_da=116.048,
        ms1_apex_rt=12.5927,
        best_seed_rt=12.5927,
    )

    cluster = build_alignment_cluster(
        cluster_id="ALN000001",
        neutral_loss_tag="DNA_dR",
        members=(candidate,),
    )

    assert cluster.folded_cluster_ids == ()
    assert cluster.folded_member_count == 0
    assert cluster.folded_sample_fill_count == 0
    assert cluster.fold_evidence == ""
```

- [ ] **Step 2: Run tests to verify red**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_config.py::test_alignment_config_duplicate_fold_defaults_are_conservative tests/test_alignment_config.py::test_alignment_config_rejects_invalid_duplicate_fold_values tests/test_alignment_models.py::test_alignment_cluster_fold_metadata_defaults_to_empty -v
```

Expected: FAIL because fields do not exist.

- [ ] **Step 3: Implement config and model fields**

In `AlignmentConfig`, add fields:

```python
duplicate_fold_ppm: float = 5.0
duplicate_fold_rt_sec: float = 2.0
duplicate_fold_product_ppm: float = 10.0
duplicate_fold_observed_loss_ppm: float = 10.0
duplicate_fold_min_detected_overlap: float = 0.80
duplicate_fold_min_shared_detected_count: int = 3
duplicate_fold_min_detected_jaccard: float = 0.60
duplicate_fold_min_present_overlap: float = 0.80
```

In `__post_init__`, validate:

```python
_require_positive("duplicate_fold_ppm", self.duplicate_fold_ppm)
_require_positive("duplicate_fold_rt_sec", self.duplicate_fold_rt_sec)
_require_positive("duplicate_fold_product_ppm", self.duplicate_fold_product_ppm)
_require_positive(
    "duplicate_fold_observed_loss_ppm",
    self.duplicate_fold_observed_loss_ppm,
)
_require_numeric_range(
    "duplicate_fold_min_detected_overlap",
    self.duplicate_fold_min_detected_overlap,
    0,
    1,
)
_require_positive_int(
    "duplicate_fold_min_shared_detected_count",
    self.duplicate_fold_min_shared_detected_count,
)
_require_numeric_range(
    "duplicate_fold_min_detected_jaccard",
    self.duplicate_fold_min_detected_jaccard,
    0,
    1,
)
_require_numeric_range(
    "duplicate_fold_min_present_overlap",
    self.duplicate_fold_min_present_overlap,
    0,
    1,
)
```

In `AlignmentCluster`, add default fields:

```python
folded_cluster_ids: tuple[str, ...] = ()
folded_member_count: int = 0
folded_sample_fill_count: int = 0
fold_evidence: str = ""
```

Ensure `build_alignment_cluster()` passes no explicit fold metadata, so defaults stay empty.

- [ ] **Step 4: Run tests to verify green**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_config.py tests/test_alignment_models.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/alignment/config.py xic_extractor/alignment/models.py tests/test_alignment_config.py tests/test_alignment_models.py
git commit -m "feat(alignment): add duplicate folding contracts"
```

### Task 2: Implement Matrix-Level Duplicate Folding

**Files:**
- Create: `xic_extractor/alignment/folding.py`
- Test: `tests/test_alignment_folding.py`

- [ ] **Step 1: Write failing folding tests**

Create `tests/test_alignment_folding.py`:

```python
from __future__ import annotations

from pathlib import Path

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.folding import fold_near_duplicate_clusters
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.models import AlignmentCluster


def test_folds_no_anchor_duplicate_into_anchor_primary():
    matrix = AlignmentMatrix(
        clusters=(
            _cluster("ALN000001", has_anchor=True, mz=242.114, rt=12.5927),
            _cluster("ALN000002", has_anchor=False, mz=242.115, rt=12.5916),
        ),
        cells=(
            _cell("s1", "ALN000001", "detected", area=100.0),
            _cell("s2", "ALN000001", "detected", area=120.0),
            _cell("s3", "ALN000001", "detected", area=130.0),
            _cell("s1", "ALN000002", "detected", area=90.0),
            _cell("s2", "ALN000002", "detected", area=110.0),
            _cell("s3", "ALN000002", "detected", area=115.0),
        ),
        sample_order=("s1", "s2", "s3"),
    )

    folded = fold_near_duplicate_clusters(matrix, config=AlignmentConfig())

    assert [cluster.cluster_id for cluster in folded.clusters] == ["ALN000001"]
    assert folded.clusters[0].folded_cluster_ids == ("ALN000002",)
    assert folded.clusters[0].folded_member_count == 1
    assert {(cell.sample_stem, cell.cluster_id, cell.area) for cell in folded.cells} == {
        ("s1", "ALN000001", 100.0),
        ("s2", "ALN000001", 120.0),
        ("s3", "ALN000001", 130.0),
    }


def test_secondary_present_sample_can_fill_missing_primary_cell_without_area_sum():
    matrix = AlignmentMatrix(
        clusters=(
            _cluster("ALN000001", has_anchor=True, mz=500.000, rt=8.500),
            _cluster("ALN000002", has_anchor=False, mz=500.001, rt=8.501),
        ),
        cells=(
            _cell("s1", "ALN000001", "detected", area=100.0),
            _cell("s2", "ALN000001", "absent", area=None),
            _cell("s1", "ALN000002", "detected", area=90.0),
            _cell("s2", "ALN000002", "detected", area=80.0),
        ),
        sample_order=("s1", "s2"),
    )

    folded = fold_near_duplicate_clusters(
        matrix,
        config=AlignmentConfig(
            duplicate_fold_min_detected_overlap=0.5,
            duplicate_fold_min_shared_detected_count=1,
            duplicate_fold_min_detected_jaccard=0.5,
            duplicate_fold_min_present_overlap=0.5,
        ),
    )

    assert [cluster.cluster_id for cluster in folded.clusters] == ["ALN000001"]
    cells = {(cell.sample_stem, cell.status, cell.area, cell.reason) for cell in folded.cells}
    assert ("s1", "detected", 100.0, "detected") in cells
    assert ("s2", "detected", 80.0, "detected; folded from ALN000002") in cells


def test_backfilled_present_overlap_without_shared_detected_does_not_fold():
    matrix = AlignmentMatrix(
        clusters=(
            _cluster("ALN000001", has_anchor=True),
            _cluster("ALN000002", has_anchor=False, mz=242.115, rt=12.5916),
        ),
        cells=(
            _cell("s1", "ALN000001", "detected", area=100.0),
            _cell("s2", "ALN000001", "rescued", area=120.0),
            _cell("s2", "ALN000002", "detected", area=90.0),
        ),
        sample_order=("s1", "s2"),
    )

    folded = fold_near_duplicate_clusters(
        matrix,
        config=AlignmentConfig(
            duplicate_fold_min_detected_overlap=0.8,
            duplicate_fold_min_shared_detected_count=2,
            duplicate_fold_min_detected_jaccard=0.6,
            duplicate_fold_min_present_overlap=0.8,
        ),
    )

    assert [cluster.cluster_id for cluster in folded.clusters] == ["ALN000001", "ALN000002"]


def test_one_sample_subset_overlap_does_not_fold_rare_discovery_by_default():
    matrix = AlignmentMatrix(
        clusters=(
            _cluster("ALN000001", has_anchor=True, mz=242.114, rt=12.5927),
            _cluster("ALN000002", has_anchor=False, mz=242.115, rt=12.5916),
        ),
        cells=(
            _cell("s1", "ALN000001", "detected", area=100.0),
            _cell("s2", "ALN000001", "detected", area=120.0),
            _cell("s3", "ALN000001", "detected", area=130.0),
            _cell("s1", "ALN000002", "detected", area=90.0),
        ),
        sample_order=("s1", "s2", "s3"),
    )

    folded = fold_near_duplicate_clusters(matrix, config=AlignmentConfig())

    assert [cluster.cluster_id for cluster in folded.clusters] == ["ALN000001", "ALN000002"]


def test_no_anchor_primary_prefers_higher_detected_count_over_lower_cluster_id():
    matrix = AlignmentMatrix(
        clusters=(
            _cluster("ALN000001", has_anchor=False, mz=500.000, rt=8.000),
            _cluster("ALN000002", has_anchor=False, mz=500.001, rt=8.001),
        ),
        cells=(
            _cell("s1", "ALN000001", "detected", area=100.0),
            _cell("s1", "ALN000002", "detected", area=90.0),
            _cell("s2", "ALN000002", "detected", area=95.0),
        ),
        sample_order=("s1", "s2"),
    )

    folded = fold_near_duplicate_clusters(
        matrix,
        config=AlignmentConfig(
            duplicate_fold_min_detected_overlap=0.5,
            duplicate_fold_min_shared_detected_count=1,
            duplicate_fold_min_detected_jaccard=0.5,
            duplicate_fold_min_present_overlap=0.5,
        ),
    )

    assert [cluster.cluster_id for cluster in folded.clusters] == ["ALN000002"]
    assert folded.clusters[0].folded_cluster_ids == ("ALN000001",)


def test_secondary_cell_fill_uses_deterministic_evidence_winner():
    matrix = AlignmentMatrix(
        clusters=(
            _cluster("ALN000001", has_anchor=True, mz=500.000, rt=8.000),
            _cluster("ALN000002", has_anchor=False, mz=500.001, rt=8.001),
            _cluster("ALN000003", has_anchor=False, mz=500.002, rt=8.002),
        ),
        cells=(
            _cell("shared", "ALN000001", "detected", area=100.0),
            _cell("fill", "ALN000001", "absent", area=None),
            _cell("shared", "ALN000002", "detected", area=90.0),
            _cell(
                "fill",
                "ALN000002",
                "detected",
                area=70.0,
                scan_support_score=0.5,
            ),
            _cell("shared", "ALN000003", "detected", area=80.0),
            _cell(
                "fill",
                "ALN000003",
                "detected",
                area=60.0,
                scan_support_score=0.9,
            ),
        ),
        sample_order=("shared", "fill"),
    )

    folded = fold_near_duplicate_clusters(
        matrix,
        config=AlignmentConfig(
            duplicate_fold_min_detected_overlap=0.5,
            duplicate_fold_min_shared_detected_count=1,
            duplicate_fold_min_detected_jaccard=0.5,
            duplicate_fold_min_present_overlap=0.5,
        ),
    )

    fill_cell = next(cell for cell in folded.cells if cell.sample_stem == "fill")
    assert fill_cell.area == 60.0
    assert fill_cell.reason == "detected; folded from ALN000003"


def test_folding_preserves_retained_primary_output_order():
    matrix = AlignmentMatrix(
        clusters=(
            _cluster("ALN000001", has_anchor=False, mz=100.000, rt=5.000),
            _cluster("ALN000002", has_anchor=False, mz=200.001, rt=8.001),
            _cluster("ALN000003", has_anchor=True, mz=200.000, rt=8.000),
        ),
        cells=(
            _cell("s1", "ALN000001", "detected", area=10.0),
            _cell("s1", "ALN000002", "detected", area=20.0),
            _cell("s1", "ALN000003", "detected", area=30.0),
        ),
        sample_order=("s1",),
    )

    folded = fold_near_duplicate_clusters(
        matrix,
        config=AlignmentConfig(
            duplicate_fold_min_detected_overlap=1.0,
            duplicate_fold_min_shared_detected_count=1,
            duplicate_fold_min_detected_jaccard=1.0,
            duplicate_fold_min_present_overlap=1.0,
        ),
    )

    assert [cluster.cluster_id for cluster in folded.clusters] == ["ALN000001", "ALN000003"]


def test_does_not_fold_when_product_or_observed_loss_conflicts():
    matrix = AlignmentMatrix(
        clusters=(
            _cluster("ALN000001", product=126.066, observed_loss=116.048),
            _cluster("ALN000002", mz=242.115, rt=12.5916, product=130.0, observed_loss=112.0),
        ),
        cells=(
            _cell("s1", "ALN000001", "detected", area=100.0),
            _cell("s1", "ALN000002", "detected", area=90.0),
        ),
        sample_order=("s1",),
    )

    folded = fold_near_duplicate_clusters(matrix, config=AlignmentConfig())

    assert [cluster.cluster_id for cluster in folded.clusters] == ["ALN000001", "ALN000002"]


def test_no_chain_folding_requires_secondary_to_match_existing_folded_members():
    primary = _cluster("ALN000001", mz=500.000, rt=8.000)
    bridge = _cluster("ALN000002", mz=500.002, rt=8.010)
    endpoint = _cluster("ALN000003", mz=500.004, rt=8.020)
    matrix = AlignmentMatrix(
        clusters=(primary, bridge, endpoint),
        cells=(
            _cell("s1", "ALN000001", "detected", area=100.0),
            _cell("s1", "ALN000002", "detected", area=90.0),
            _cell("s1", "ALN000003", "detected", area=80.0),
        ),
        sample_order=("s1",),
    )

    folded = fold_near_duplicate_clusters(
        matrix,
        config=AlignmentConfig(
            duplicate_fold_ppm=5.0,
            duplicate_fold_rt_sec=0.75,
            duplicate_fold_min_detected_overlap=1.0,
            duplicate_fold_min_shared_detected_count=1,
            duplicate_fold_min_detected_jaccard=1.0,
            duplicate_fold_min_present_overlap=1.0,
        ),
    )

    assert [cluster.cluster_id for cluster in folded.clusters] == ["ALN000001", "ALN000003"]
    assert folded.clusters[0].folded_cluster_ids == ("ALN000002",)


def _cluster(
    cluster_id: str,
    *,
    has_anchor: bool = True,
    mz: float = 242.114,
    rt: float = 12.5927,
    product: float = 126.066,
    observed_loss: float = 116.048,
) -> AlignmentCluster:
    return AlignmentCluster(
        cluster_id=cluster_id,
        neutral_loss_tag="DNA_dR",
        cluster_center_mz=mz,
        cluster_center_rt=rt,
        cluster_product_mz=product,
        cluster_observed_neutral_loss_da=observed_loss,
        has_anchor=has_anchor,
        members=(object(),),
        anchor_members=(object(),) if has_anchor else (),
    )


def _cell(
    sample_stem: str,
    cluster_id: str,
    status: str,
    *,
    area: float | None,
    scan_support_score: float | None = None,
    trace_quality: str | None = None,
    rt_delta_sec: float | None = None,
) -> AlignedCell:
    resolved_scan_support = (
        scan_support_score
        if scan_support_score is not None
        else (0.9 if area else None)
    )
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster_id,
        status=status,
        area=area,
        apex_rt=12.5927,
        height=100.0 if area else None,
        peak_start_rt=12.55 if area else None,
        peak_end_rt=12.65 if area else None,
        rt_delta_sec=(
            rt_delta_sec if rt_delta_sec is not None else (0.0 if area else None)
        ),
        trace_quality=trace_quality or ("clean" if area else "absent"),
        scan_support_score=resolved_scan_support,
        source_candidate_id=f"{sample_stem}#{cluster_id}",
        source_raw_file=Path(f"{sample_stem}.raw"),
        reason=status,
    )
```

- [ ] **Step 2: Run tests to verify red**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_folding.py -v
```

Expected: FAIL because `xic_extractor.alignment.folding` does not exist.

- [ ] **Step 3: Implement `folding.py`**

Create `xic_extractor/alignment/folding.py` with:

```python
from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Iterable

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.models import AlignmentCluster

_PRESENT_STATUSES = {"detected", "rescued"}


def fold_near_duplicate_clusters(
    matrix: AlignmentMatrix,
    *,
    config: AlignmentConfig,
) -> AlignmentMatrix:
    cells_by_cluster = _cells_by_cluster(matrix.cells)
    original_index = {
        cluster.cluster_id: index for index, cluster in enumerate(matrix.clusters)
    }
    groups: list[list[AlignmentCluster]] = []
    consumed: set[str] = set()

    for cluster in matrix.clusters:
        if cluster.cluster_id in consumed:
            continue
        group = [cluster]
        for candidate in matrix.clusters:
            if candidate.cluster_id == cluster.cluster_id or candidate.cluster_id in consumed:
                continue
            if _can_join_fold_group(
                candidate,
                group,
                cells_by_cluster=cells_by_cluster,
                config=config,
            ):
                group.append(candidate)
                consumed.add(candidate.cluster_id)
        consumed.add(cluster.cluster_id)
        groups.append(group)

    folded_clusters: list[AlignmentCluster] = []
    folded_cells: list[AlignedCell] = []
    for group in sorted(
        groups,
        key=lambda fold_group: original_index[
            min(
                fold_group,
                key=lambda cluster: _primary_sort_key(cluster, cells_by_cluster),
            ).cluster_id
        ],
    ):
        primary = min(
            group,
            key=lambda cluster: _primary_sort_key(cluster, cells_by_cluster),
        )
        secondaries = [
            cluster
            for cluster in group
            if cluster.cluster_id != primary.cluster_id
        ]
        merged_cells = _merged_cells_for_group(
            primary,
            secondaries,
            sample_order=matrix.sample_order,
            cells_by_cluster=cells_by_cluster,
        )
        folded_clusters.append(
            _with_fold_metadata(
                primary,
                secondaries,
                cells_by_cluster=cells_by_cluster,
                merged_cells=merged_cells,
            )
        )
        folded_cells.extend(
            merged_cells
        )

    return AlignmentMatrix(
        clusters=tuple(folded_clusters),
        cells=tuple(folded_cells),
        sample_order=matrix.sample_order,
    )


def _can_join_fold_group(
    candidate: AlignmentCluster,
    group: list[AlignmentCluster],
    *,
    cells_by_cluster: dict[str, tuple[AlignedCell, ...]],
    config: AlignmentConfig,
) -> bool:
    return all(
        _clusters_are_fold_compatible(
            candidate,
            existing,
            cells_by_cluster=cells_by_cluster,
            config=config,
        )
        for existing in group
    )


def _clusters_are_fold_compatible(
    left: AlignmentCluster,
    right: AlignmentCluster,
    *,
    cells_by_cluster: dict[str, tuple[AlignedCell, ...]],
    config: AlignmentConfig,
) -> bool:
    if left.neutral_loss_tag != right.neutral_loss_tag:
        return False
    if (
        _ppm(left.cluster_center_mz, right.cluster_center_mz)
        > config.duplicate_fold_ppm
    ):
        return False
    if (
        abs(left.cluster_center_rt - right.cluster_center_rt) * 60.0
        > config.duplicate_fold_rt_sec
    ):
        return False
    if _ms2_signature_conflicts(left, right):
        return False
    if (
        _ppm(left.cluster_product_mz, right.cluster_product_mz)
        > config.duplicate_fold_product_ppm
    ):
        return False
    if (
        _ppm(
            left.cluster_observed_neutral_loss_da,
            right.cluster_observed_neutral_loss_da,
        )
        > config.duplicate_fold_observed_loss_ppm
    ):
        return False
    left_cells = cells_by_cluster.get(left.cluster_id, ())
    right_cells = cells_by_cluster.get(right.cluster_id, ())
    detected_overlap = _overlap_coefficient(
        left_cells,
        right_cells,
        statuses={"detected"},
    )
    present_overlap = _overlap_coefficient(
        left_cells,
        right_cells,
        statuses=_PRESENT_STATUSES,
    )
    detected_jaccard = _jaccard(
        left_cells,
        right_cells,
        statuses={"detected"},
    )
    shared_detected_count = _shared_count(
        left_cells,
        right_cells,
        statuses={"detected"},
    )
    return (
        detected_overlap >= config.duplicate_fold_min_detected_overlap
        and shared_detected_count >= config.duplicate_fold_min_shared_detected_count
        and detected_jaccard >= config.duplicate_fold_min_detected_jaccard
        and present_overlap >= config.duplicate_fold_min_present_overlap
    )


def _with_fold_metadata(
    primary: AlignmentCluster,
    secondaries: list[AlignmentCluster],
    *,
    cells_by_cluster: dict[str, tuple[AlignedCell, ...]],
    merged_cells: list[AlignedCell],
) -> AlignmentCluster:
    return replace(
        primary,
        folded_cluster_ids=tuple(cluster.cluster_id for cluster in secondaries),
        folded_member_count=sum(len(cluster.members) for cluster in secondaries),
        folded_sample_fill_count=sum(
            1 for cell in merged_cells if "folded from" in cell.reason
        ),
        fold_evidence=_fold_evidence_summary(
            primary,
            secondaries,
            cells_by_cluster=cells_by_cluster,
        ),
    )


def _merged_cells_for_group(
    primary: AlignmentCluster,
    secondaries: list[AlignmentCluster],
    *,
    sample_order: tuple[str, ...],
    cells_by_cluster: dict[str, tuple[AlignedCell, ...]],
) -> list[AlignedCell]:
    primary_by_sample = _cells_by_sample(
        cells_by_cluster.get(primary.cluster_id, ()),
    )
    secondary_by_sample = {
        cluster.cluster_id: _cells_by_sample(
            cells_by_cluster.get(cluster.cluster_id, ()),
        )
        for cluster in secondaries
    }
    merged: list[AlignedCell] = []
    for sample in sample_order:
        primary_cell = primary_by_sample.get(sample)
        if primary_cell is not None and primary_cell.status in _PRESENT_STATUSES:
            merged.append(primary_cell)
            continue
        replacement = _best_present_secondary_cell(sample, secondary_by_sample)
        if replacement is not None:
            merged.append(
                replace(
                    replacement,
                    cluster_id=primary.cluster_id,
                    reason=f"{replacement.reason}; folded from {replacement.cluster_id}",
                )
            )
        elif primary_cell is not None:
            merged.append(primary_cell)
    return merged


def _best_present_secondary_cell(
    sample: str,
    secondary_by_sample: dict[str, dict[str, AlignedCell]],
) -> AlignedCell | None:
    candidates = [
        cell
        for cells in secondary_by_sample.values()
        for cell in (cells.get(sample),)
        if cell is not None and cell.status in _PRESENT_STATUSES
    ]
    if not candidates:
        return None
    return min(candidates, key=_secondary_cell_sort_key)


def _secondary_cell_sort_key(cell: AlignedCell) -> tuple[object, ...]:
    scan_support = (
        cell.scan_support_score
        if cell.scan_support_score is not None
        else -1.0
    )
    rt_delta = (
        abs(cell.rt_delta_sec)
        if cell.rt_delta_sec is not None
        else float("inf")
    )
    area = cell.area if cell.area is not None and cell.area > 0 else 0.0
    return (
        0 if cell.status == "detected" else 1,
        -scan_support,
        _trace_quality_rank(cell.trace_quality),
        rt_delta,
        -area,
        cell.cluster_id,
    )


def _trace_quality_rank(value: str) -> int:
    return {"clean": 0, "weak": 1, "poor": 2}.get(value, 3)


def _fold_evidence_summary(
    primary: AlignmentCluster,
    secondaries: list[AlignmentCluster],
    *,
    cells_by_cluster: dict[str, tuple[AlignedCell, ...]],
) -> str:
    if not secondaries:
        return ""
    mz_ppms = [_ppm(primary.cluster_center_mz, item.cluster_center_mz) for item in secondaries]
    rt_secs = [
        abs(primary.cluster_center_rt - item.cluster_center_rt) * 60.0
        for item in secondaries
    ]
    shared_detected = [
        _shared_count(
            cells_by_cluster.get(primary.cluster_id, ()),
            cells_by_cluster.get(item.cluster_id, ()),
            statuses={"detected"},
        )
        for item in secondaries
    ]
    detected_jaccards = [
        _jaccard(
            cells_by_cluster.get(primary.cluster_id, ()),
            cells_by_cluster.get(item.cluster_id, ()),
            statuses={"detected"},
        )
        for item in secondaries
    ]
    return (
        "cid_nl_only;"
        f"max_mz_ppm={max(mz_ppms):.3g};"
        f"max_rt_sec={max(rt_secs):.3g};"
        f"min_shared_detected={min(shared_detected)};"
        f"min_detected_jaccard={min(detected_jaccards):.3g}"
    )


def _cells_by_cluster(
    cells: Iterable[AlignedCell],
) -> dict[str, tuple[AlignedCell, ...]]:
    grouped: dict[str, list[AlignedCell]] = defaultdict(list)
    for cell in cells:
        grouped[cell.cluster_id].append(cell)
    return {cluster_id: tuple(values) for cluster_id, values in grouped.items()}


def _cells_by_sample(cells: tuple[AlignedCell, ...]) -> dict[str, AlignedCell]:
    return {cell.sample_stem: cell for cell in cells}


def _overlap_coefficient(
    left_cells: tuple[AlignedCell, ...],
    right_cells: tuple[AlignedCell, ...],
    *,
    statuses: set[str],
) -> float:
    left = _sample_set(left_cells, statuses=statuses)
    right = _sample_set(right_cells, statuses=statuses)
    denominator = min(len(left), len(right))
    if denominator == 0:
        return 0.0
    return len(left & right) / denominator


def _jaccard(
    left_cells: tuple[AlignedCell, ...],
    right_cells: tuple[AlignedCell, ...],
    *,
    statuses: set[str],
) -> float:
    left = _sample_set(left_cells, statuses=statuses)
    right = _sample_set(right_cells, statuses=statuses)
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _shared_count(
    left_cells: tuple[AlignedCell, ...],
    right_cells: tuple[AlignedCell, ...],
    *,
    statuses: set[str],
) -> int:
    return len(
        _sample_set(left_cells, statuses=statuses)
        & _sample_set(right_cells, statuses=statuses)
    )


def _sample_set(
    cells: tuple[AlignedCell, ...],
    *,
    statuses: set[str],
) -> set[str]:
    return {cell.sample_stem for cell in cells if cell.status in statuses}


def _ms2_signature_conflicts(
    left: AlignmentCluster,
    right: AlignmentCluster,
) -> bool:
    left_signature = getattr(left, "cluster_ms2_signature", None)
    right_signature = getattr(right, "cluster_ms2_signature", None)
    if left_signature is None or right_signature is None:
        return False
    return left_signature != right_signature


def _primary_sort_key(
    cluster: AlignmentCluster,
    cells_by_cluster: dict[str, tuple[AlignedCell, ...]],
) -> tuple[object, ...]:
    cells = cells_by_cluster.get(cluster.cluster_id, ())
    detected_count = _count(cells, "detected")
    present_count = _count(cells, "detected") + _count(cells, "rescued")
    unchecked_count = _count(cells, "unchecked")
    absent_count = _count(cells, "absent")
    return (
        0 if cluster.has_anchor else 1,
        -detected_count,
        -present_count,
        unchecked_count,
        absent_count,
        cluster.cluster_center_mz,
        cluster.cluster_center_rt,
        cluster.cluster_id,
    )


def _count(cells: tuple[AlignedCell, ...], status: str) -> int:
    return sum(1 for cell in cells if cell.status == status)


def _ppm(left: float, right: float) -> float:
    return abs(left - right) / left * 1_000_000.0
```

- [ ] **Step 4: Run tests to verify green**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_folding.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/alignment/folding.py tests/test_alignment_folding.py
git commit -m "feat(alignment): fold near-duplicate clusters"
```

### Task 3: Wire Folding Into Alignment Pipeline

**Files:**
- Modify: `xic_extractor/alignment/pipeline.py`
- Test: `tests/test_alignment_pipeline.py`

- [ ] **Step 1: Write failing pipeline test**

Add to `tests/test_alignment_pipeline.py`:

```python
def test_pipeline_folds_matrix_before_writing(tmp_path: Path, monkeypatch) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    calls = {}

    monkeypatch.setattr(
        pipeline_module,
        "cluster_candidates",
        lambda candidates, *, config: (_cluster(),),
    )
    monkeypatch.setattr(
        pipeline_module,
        "backfill_alignment_matrix",
        lambda clusters, *, sample_order, raw_sources, **kwargs: _matrix(sample_order),
    )
    sentinel_matrix = AlignmentMatrix(
        clusters=(_cluster(cluster_id="ALN999999"),),
        cells=(),
        sample_order=("Sample_A",),
    )

    def fake_fold(matrix, *, config):
        calls["folded"] = True
        calls["config"] = config
        return sentinel_matrix

    monkeypatch.setattr(pipeline_module, "fold_near_duplicate_clusters", fake_fold)
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

    assert calls["folded"] is True
    assert isinstance(calls["config"], AlignmentConfig)
    assert calls["written_matrix"] is sentinel_matrix
```

- [ ] **Step 2: Run test to verify red**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_pipeline.py::test_pipeline_folds_matrix_before_writing -v
```

Expected: FAIL because `pipeline_module.fold_near_duplicate_clusters` is not imported/called.

- [ ] **Step 3: Implement pipeline call**

In `xic_extractor/alignment/pipeline.py`, import:

```python
from xic_extractor.alignment.folding import fold_near_duplicate_clusters
```

After `backfill_alignment_matrix(...)`, add:

```python
matrix = fold_near_duplicate_clusters(matrix, config=alignment_config)
```

The call must happen before `_write_outputs_atomic(outputs, matrix)`.

- [ ] **Step 4: Run tests to verify green**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_pipeline.py tests/test_alignment_folding.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/alignment/pipeline.py tests/test_alignment_pipeline.py
git commit -m "feat(alignment): apply duplicate folding in pipeline"
```

### Task 4: Make Alignment Review Explain Folding and Backfill

**Files:**
- Modify: `docs/superpowers/plans/2026-05-11-alignment-output-cli-plan.md`
- Modify: `xic_extractor/alignment/tsv_writer.py`
- Test: `tests/test_alignment_tsv_writer.py`

- [ ] **Step 1: Update the alignment review schema contract**

In `docs/superpowers/plans/2026-05-11-alignment-output-cli-plan.md`, update the
`alignment_review.tsv` schema section so `member_count` is followed by:

```text
folded_cluster_count
folded_cluster_ids
folded_member_count
folded_sample_fill_count
fold_evidence
```

Add this contract note:

```markdown
Near-duplicate folding may remove secondary cluster rows from the review and
matrix outputs. The retained primary row records folded secondaries in
`folded_cluster_count`, `folded_cluster_ids`, and `folded_member_count`.
`folded_sample_fill_count` records how many sample cells were filled from folded
secondaries. `fold_evidence` records compact CID-only audit evidence such as
max m/z ppm, max RT seconds, shared detected count, and detected Jaccard.
`member_count` remains the detected member count of the retained primary cluster;
it does not include MS1-backfilled cells.
```

- [ ] **Step 2: Write failing review TSV tests**

Update `REVIEW_COLUMNS` in `tests/test_alignment_tsv_writer.py` to include these columns immediately after `member_count`:

```python
"folded_cluster_count",
"folded_cluster_ids",
"folded_member_count",
"folded_sample_fill_count",
"fold_evidence",
```

Update the expected row in `test_write_alignment_review_tsv_columns_counts_rates_and_reason`:

```python
"folded_cluster_count": "0",
"folded_cluster_ids": "",
"folded_member_count": "0",
"folded_sample_fill_count": "0",
"fold_evidence": "",
"warning": "",
"reason": "anchor cluster; 2/4 present; 1 MS1 backfilled",
```

Add a focused folded-cluster test:

```python
def test_write_alignment_review_tsv_reports_folded_clusters(tmp_path: Path):
    from xic_extractor.alignment.tsv_writer import write_alignment_review_tsv

    matrix = AlignmentMatrix(
        clusters=(
            _cluster(
                has_anchor=True,
                member_count=2,
                folded_cluster_ids=("ALN000002", "ALN000003"),
                folded_member_count=5,
                folded_sample_fill_count=1,
                fold_evidence="cid_nl_only;max_mz_ppm=2;max_rt_sec=1;min_shared_detected=4",
            ),
        ),
        cells=(
            _cell("sample-a", "detected", area=10.0, candidate_id="sample-a#1"),
            _cell("sample-b", "rescued", area=20.0),
        ),
        sample_order=("sample-a", "sample-b"),
    )

    rows = _read_tsv(write_alignment_review_tsv(tmp_path / "review.tsv", matrix))

    assert rows[0]["folded_cluster_count"] == "2"
    assert rows[0]["folded_cluster_ids"] == "ALN000002;ALN000003"
    assert rows[0]["folded_member_count"] == "5"
    assert rows[0]["folded_sample_fill_count"] == "1"
    assert rows[0]["fold_evidence"].startswith("cid_nl_only;")
    assert rows[0]["reason"] == (
        "anchor cluster; 2/2 present; 1 MS1 backfilled; "
        "folded 2 near-duplicate clusters"
    )
```

Update `_cluster()` test helper signature:

```python
def _cluster(
    *,
    cluster_id: str = "ALN000001",
    neutral_loss_tag: str = "DNA_dR",
    has_anchor: bool = True,
    member_count: int = 0,
    folded_cluster_ids: tuple[str, ...] = (),
    folded_member_count: int = 0,
    folded_sample_fill_count: int = 0,
    fold_evidence: str = "",
) -> AlignmentCluster:
```

And pass the new metadata to `AlignmentCluster`.

- [ ] **Step 3: Run tests to verify red**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_tsv_writer.py -v
```

Expected: FAIL because columns/reason/warning have not changed.

- [ ] **Step 4: Implement TSV writer updates**

In `ALIGNMENT_REVIEW_COLUMNS`, add:

```python
"folded_cluster_count",
"folded_cluster_ids",
"folded_member_count",
"folded_sample_fill_count",
"fold_evidence",
```

In `_review_rows()`, add:

```python
"folded_cluster_count": len(cluster.folded_cluster_ids),
"folded_cluster_ids": ";".join(cluster.folded_cluster_ids),
"folded_member_count": cluster.folded_member_count,
"folded_sample_fill_count": cluster.folded_sample_fill_count,
"fold_evidence": cluster.fold_evidence,
```

Rename warning output:

```python
if rescued_count > detected_count:
    return "high_backfill_dependency"
```

Update `_reason()`:

```python
def _reason(
    cluster: AlignmentCluster,
    present_count: int,
    sample_count: int,
    rescued_count: int,
) -> str:
    prefix = "anchor cluster" if cluster.has_anchor else "no anchor"
    parts = [
        f"{prefix}",
        f"{present_count}/{sample_count} present",
        f"{rescued_count} MS1 backfilled",
    ]
    if cluster.folded_cluster_ids:
        parts.append(
            f"folded {len(cluster.folded_cluster_ids)} near-duplicate clusters",
        )
    return "; ".join(parts)
```

- [ ] **Step 5: Run tests to verify green**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_tsv_writer.py tests/test_alignment_folding.py tests/test_alignment_pipeline.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add docs/superpowers/plans/2026-05-11-alignment-output-cli-plan.md xic_extractor/alignment/tsv_writer.py tests/test_alignment_tsv_writer.py
git commit -m "feat(alignment): report folded duplicate clusters"
```

### Task 5: Real-Data Validation and Focused Audit

**Files:**
- Generated output only under `output/`

- [ ] **Step 1: Run 8/raw alignment**

Run discovery only if the existing discovery batch is stale. Otherwise reuse:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-align-cli --discovery-batch-index "output\discovery\tissue8_alignment_v1\discovery_batch_index.csv" --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --dll-dir "C:\Xcalibur\system\programs" --output-dir "output\alignment\tissue8_alignment_fold_v1" --resolver-mode local_minimum
```

Expected:

- `output\alignment\tissue8_alignment_fold_v1\alignment_review.tsv`
- `output\alignment\tissue8_alignment_fold_v1\alignment_matrix.tsv`

- [ ] **Step 2: Run 85/raw alignment reuse**

Reuse the existing 85/raw discovery batch:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-align-cli --discovery-batch-index "output\discovery\tissue85_alignment_v1\discovery_batch_index.csv" --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R" --dll-dir "C:\Xcalibur\system\programs" --output-dir "output\alignment\tissue85_alignment_fold_v1" --resolver-mode local_minimum
```

Expected:

- `output\alignment\tissue85_alignment_fold_v1\alignment_review.tsv`
- `output\alignment\tissue85_alignment_fold_v1\alignment_matrix.tsv`

- [ ] **Step 3: Run 8/raw validation against legacy files**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-align-validate-cli --alignment-dir "output\alignment\tissue8_alignment_fold_v1" --legacy-fh-tsv "C:\Users\user\Desktop\MS Data process package\MS-data aligner\output\program2_DNA\program2_DNA_v4_alignment_standard.tsv" --legacy-metabcombiner-tsv "C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\metabcombiner_fh_format_20260429_130630.tsv" --legacy-combine-fix-xlsx "C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\metabcombiner_fh_format_20260422_213805_combined_fix_20260422_223242.xlsx" --sample-scope xic --output-dir "output\alignment_validation\tissue8_alignment_fold_v1"
```

Expected:

- `output\alignment_validation\tissue8_alignment_fold_v1\alignment_validation_summary.tsv`
- `output\alignment_validation\tissue8_alignment_fold_v1\alignment_legacy_matches.tsv`

- [ ] **Step 4: Run 85/raw validation against legacy files**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-align-validate-cli --alignment-dir "output\alignment\tissue85_alignment_fold_v1" --legacy-fh-tsv "C:\Users\user\Desktop\MS Data process package\MS-data aligner\output\program2_DNA\program2_DNA_v4_alignment_standard.tsv" --legacy-metabcombiner-tsv "C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\metabcombiner_fh_format_20260429_130630.tsv" --legacy-combine-fix-xlsx "C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\metabcombiner_fh_format_20260422_213805_combined_fix_20260422_223242.xlsx" --sample-scope xic --output-dir "output\alignment_validation\tissue85_alignment_fold_v1"
```

Expected:

- `output\alignment_validation\tissue85_alignment_fold_v1\alignment_validation_summary.tsv`
- `output\alignment_validation\tissue85_alignment_fold_v1\alignment_legacy_matches.tsv`

- [ ] **Step 5: Audit 5-medC-like case**

Run:

```powershell
$path="output\alignment\tissue85_alignment_fold_v1\alignment_review.tsv"
Import-Csv -Path $path -Delimiter "`t" |
  Where-Object {
    [math]::Abs([double]$_.cluster_center_mz - 242.114) -le 0.05 -and
    [math]::Abs([double]$_.cluster_center_rt - 12.5927) -le 0.20
  } |
  Select-Object cluster_id,cluster_center_mz,cluster_center_rt,has_anchor,member_count,folded_cluster_count,folded_cluster_ids,detected_count,rescued_count,present_rate,warning,reason |
  Format-Table -AutoSize
```

Expected:

- The former anchored 5-medC-like row remains.
- The near-identical no-anchor duplicate is folded into it.
- `folded_cluster_ids` includes the no-anchor duplicate cluster id.

- [ ] **Step 6: Compare duplicate pressure and validation metrics before/after**

Run this for both old and new 85/raw review TSVs:

```powershell
$path="output\alignment\tissue85_alignment_fold_v1\alignment_review.tsv"
$rows=Import-Csv -Path $path -Delimiter "`t"
$nearPairs=0
for($i=0; $i -lt $rows.Count; $i++){
  for($j=$i+1; $j -lt $rows.Count; $j++){
    $mz1=[double]$rows[$i].cluster_center_mz
    $mz2=[double]$rows[$j].cluster_center_mz
    $rt1=[double]$rows[$i].cluster_center_rt
    $rt2=[double]$rows[$j].cluster_center_rt
    if([Math]::Abs($mz1-$mz2)/$mz1*1000000 -le 5 -and [Math]::Abs($rt1-$rt2)*60 -le 2){
      $nearPairs++
    }
  }
}
[PSCustomObject]@{
  clusters=$rows.Count
  near_duplicate_pairs_ppm5_rt2sec=$nearPairs
  folded_clusters=($rows | Where-Object { [int]$_.folded_cluster_count -gt 0 }).Count
  no_anchor=($rows | Where-Object { $_.has_anchor -eq "FALSE" }).Count
} | Format-List
```

Then run:

```powershell
$summary = Import-Csv -Path "output\alignment_validation\tissue85_alignment_fold_v1\alignment_validation_summary.tsv" -Delimiter "`t"
$summary |
  Where-Object {
    $_.metric -in @(
      "xic_feature_count",
      "legacy_feature_count",
      "matched_feature_count",
      "unmatched_xic_count",
      "unmatched_legacy_count",
      "median_distance_score",
      "median_present_jaccard",
      "replacement_readiness"
    )
  } |
  Sort-Object source, metric |
  Format-Table source,metric,value,status,note -AutoSize

$matches = Import-Csv -Path "output\alignment_validation\tissue85_alignment_fold_v1\alignment_legacy_matches.tsv" -Delimiter "`t"
$matches |
  Group-Object source |
  ForEach-Object {
    $total = $_.Group.Count
    $ok = ($_.Group | Where-Object { $_.status -eq "OK" }).Count
    [PSCustomObject]@{
      source = $_.Name
      match_count = $total
      ok_count = $ok
      ok_rate = if($total -gt 0){ [Math]::Round($ok / $total, 3) } else { $null }
    }
  } |
  Format-Table -AutoSize

$reviewByCluster = @{}
Import-Csv -Path "output\alignment\tissue85_alignment_fold_v1\alignment_review.tsv" -Delimiter "`t" |
  ForEach-Object { $reviewByCluster[$_.cluster_id] = $_ }
$matches |
  Where-Object {
    $reviewByCluster.ContainsKey($_.xic_cluster_id) -and
    [int]$reviewByCluster[$_.xic_cluster_id].folded_cluster_count -gt 0
  } |
  Select-Object -First 20 source,xic_cluster_id,legacy_feature_id,status,
    @{Name="folded_cluster_ids";Expression={$reviewByCluster[$_.xic_cluster_id].folded_cluster_ids}},
    @{Name="fold_evidence";Expression={$reviewByCluster[$_.xic_cluster_id].fold_evidence}} |
  Format-Table -AutoSize
```

Expected:

- Cluster count decreases.
- Near-duplicate pairs decrease.
- `no_anchor` decreases for duplicate-like rows.
- No broad collapse into one massive cluster.
- Validation summary still reports `replacement_readiness=manual_review_ready`.
- Matched feature counts and OK rates do not materially collapse compared with `tissue85_alignment_v1`.

- [ ] **Step 7: Run targeted test suite**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_config.py tests/test_alignment_models.py tests/test_alignment_folding.py tests/test_alignment_pipeline.py tests/test_alignment_tsv_writer.py tests/test_alignment_validation_pipeline.py -v
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/alignment tests/test_alignment_folding.py tests/test_alignment_tsv_writer.py tests/test_alignment_pipeline.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

Expected: PASS.

- [ ] **Step 8: Commit validation docs only if a summary file is added**

Do not commit generated `output/` files unless this branch has an explicit validation artifact convention. If adding a short markdown note:

```powershell
git add docs/superpowers/plans/2026-05-11-alignment-near-duplicate-folding-plan.md
git commit -m "docs(alignment): plan duplicate cluster folding"
```

Implementation commits should already be made in Tasks 1-4.

---

## Acceptance Criteria

- 5-medC-like anchored/no-anchor duplicate collapses to one review row.
- Folded rows are auditable via `folded_cluster_count`, `folded_cluster_ids`, and `folded_member_count`.
- Matrix area values are not summed across duplicate triggers.
- Product m/z and observed neutral loss conflicts prevent folding.
- Shared detected evidence is required; rescued-only overlap cannot trigger folding.
- Chain-style near-neighbor collapse is prevented.
- Multiple secondary cells for one sample use deterministic evidence-based winner rules.
- `high_rescue_rate` wording is replaced with `high_backfill_dependency` / `MS1 backfilled`.
- Alignment output CLI schema contract is updated for folded-cluster audit columns.
- Existing validation CLI still runs on folded outputs.
- 8/raw and 85/raw alignment outputs are generated for manual review.

## Self-Review

- Spec coverage: This plan addresses duplicate-like cluster rows, 5-medC no-anchor duplicate behavior, rescued/backfill wording, output schema contract drift, and validation CLI compatibility.
- Placeholder scan: No `TBD`, `TODO`, or unspecified implementation steps remain.
- Type consistency: New config fields, cluster metadata, fold eligibility gates, and folding function names are consistent across tasks.
