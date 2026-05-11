# Sample-Local MS1 Ownership Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the sample-local MS1 ownership layer that groups same-RAW MS2 event candidates by resolved MS1 chromatographic peak before cross-sample alignment.

**Architecture:** Add focused ownership models and an ownership builder under `xic_extractor/alignment/`. This layer consumes discovery/alignment candidate rows plus per-sample XIC sources, re-extracts MS1 traces, resolves local peaks, assigns MS2 events to one sample-local owner, and emits ambiguous owner records when the local MS1 evidence is not safe to collapse.

**Tech Stack:** Python dataclasses, NumPy arrays, existing `find_peak_and_area()`, `pytest`, existing `AlignmentConfig` and `ExtractionConfig`.

---

## Scope

This plan implements only the local ownership core. It does not replace the current cross-sample clustering pipeline and does not change default CLI outputs.

The core rule is:

```text
Within one RAW file, one resolved MS1 peak owns one area.
MS2 events attached to that peak become identity/supporting evidence, not extra production rows.
```

## File Structure

- Create `xic_extractor/alignment/ownership_models.py`
  - `IdentityEvent`: normalized MS2/NL event evidence copied from the input candidate.
  - `SampleLocalMS1Owner`: one MS1 peak instance in one sample.
  - `OwnerAssignment`: event-to-owner/debug assignment.
  - `AmbiguousOwnerRecord`: checked-but-not-quantified local ambiguity.
- Create `xic_extractor/alignment/ownership.py`
  - XIC extraction protocol.
  - Injectable peak resolver protocol for deterministic ownership tests.
  - Candidate normalization.
  - Per-candidate peak resolving with `find_peak_and_area()`.
  - Same-owner grouping gates.
  - Primary identity event selection.
  - Ambiguity labeling.
- Modify `xic_extractor/alignment/config.py`
  - Add explicit owner gates:
    - `owner_window_overlap_fraction: float = 0.50`
    - `owner_apex_close_sec: float = 2.0`
    - `owner_tail_seed_guard_sec: float = 30.0`
    - `owner_tail_max_secondary_ratio: float = 0.30`
- Test `tests/test_alignment_ownership_models.py`
- Test `tests/test_alignment_ownership.py`

## Named V1 Gates

Use these exact field names. Later plans depend on them.

```python
owner_window_overlap_fraction = 0.50
owner_apex_close_sec = 2.0
owner_tail_seed_guard_sec = 30.0
owner_tail_max_secondary_ratio = 0.30
```

Interpretation:

- `owner_window_overlap_fraction`: `intersection / min(width_a, width_b)` needed for same-owner overlap.
- `owner_apex_close_sec`: apex distance allowed for same-owner overlap.
- `owner_tail_seed_guard_sec`: maximum seed-to-apex distance allowed for shoulder/tail assignment.
- `owner_tail_max_secondary_ratio`: a local maximum above this fraction of owner apex blocks tail assignment and creates ambiguity/separate owner.

## Fixture Manifest

Use these synthetic IDs and expected contracts.

| Fixture | Candidates | Expected |
|---|---|---|
| `case1_same_owner_with_class_drift_local_part` | `s1#6095`, `s1#6096`, same sample, m/z `242.1140`, tag `DNA_dR`, seed RT `12.5927` and `12.5940`, same Gaussian trace apex `12.5930`. | One owner for `s1`; two supporting events; primary is deterministic. |
| `case4_tail_events_on_one_peak_local_part` | `s1#7001`, `s1#7002`, `s1#7003`, same sample, m/z `251.0840`, same peak window `8.40-8.70`, seeds on apex/tail. | One owner; tail assignments recorded as supporting events. |
| `case2_unresolved_doublet_local_part` | `s1#8001`, `s1#8002`, same sample, m/z `296.0740`, two local maxima with low valley separation. | `ambiguous_ms1_owner` record; no automatic cloned area. |
| `negative_different_nl_same_peak_local_part` | `s1#9001` tag `DNA_dR`, `s1#9002` tag `DNA_base_loss`, same apex/window. | One local MS1 owner is allowed; owner carries identity conflict for later cross-sample grouping. |

## Task 1: Characterize AlignmentConfig Owner Gates

**Files:**
- Modify: `xic_extractor/alignment/config.py`
- Test: `tests/test_alignment_config.py`

- [ ] **Step 1: Add failing tests for owner gate defaults and validation**

Append these tests to `tests/test_alignment_config.py`:

```python
import pytest

from xic_extractor.alignment.config import AlignmentConfig


def test_alignment_config_owner_gate_defaults_are_explicit():
    config = AlignmentConfig()

    assert config.owner_window_overlap_fraction == 0.50
    assert config.owner_apex_close_sec == 2.0
    assert config.owner_tail_seed_guard_sec == 30.0
    assert config.owner_tail_max_secondary_ratio == 0.30


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("owner_window_overlap_fraction", -0.01),
        ("owner_window_overlap_fraction", 1.01),
        ("owner_apex_close_sec", 0.0),
        ("owner_tail_seed_guard_sec", 0.0),
        ("owner_tail_max_secondary_ratio", -0.01),
        ("owner_tail_max_secondary_ratio", 1.01),
    ],
)
def test_alignment_config_owner_gate_validation(field, value):
    kwargs = {field: value}

    with pytest.raises(ValueError, match=field):
        AlignmentConfig(**kwargs)
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_config.py -v
```

Expected: FAIL because `AlignmentConfig` does not expose the owner gate fields.

- [ ] **Step 3: Add owner gate fields and validation**

Modify `AlignmentConfig` in `xic_extractor/alignment/config.py`:

```python
owner_window_overlap_fraction: float = 0.50
owner_apex_close_sec: float = 2.0
owner_tail_seed_guard_sec: float = 30.0
owner_tail_max_secondary_ratio: float = 0.30
```

Add this validation block in `__post_init__()`:

```python
        _require_numeric_range(
            "owner_window_overlap_fraction",
            self.owner_window_overlap_fraction,
            0,
            1,
        )
        _require_positive("owner_apex_close_sec", self.owner_apex_close_sec)
        _require_positive(
            "owner_tail_seed_guard_sec",
            self.owner_tail_seed_guard_sec,
        )
        _require_numeric_range(
            "owner_tail_max_secondary_ratio",
            self.owner_tail_max_secondary_ratio,
            0,
            1,
        )
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_config.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/alignment/config.py tests/test_alignment_config.py
git commit -m "feat: add MS1 owner alignment gates"
```

## Task 2: Add Ownership Data Models

**Files:**
- Create: `xic_extractor/alignment/ownership_models.py`
- Test: `tests/test_alignment_ownership_models.py`

- [ ] **Step 1: Write model tests**

Create `tests/test_alignment_ownership_models.py`:

```python
from xic_extractor.alignment.ownership_models import (
    AmbiguousOwnerRecord,
    IdentityEvent,
    OwnerAssignment,
    SampleLocalMS1Owner,
)


def test_sample_local_owner_exposes_primary_and_supporting_events():
    primary = IdentityEvent(
        candidate_id="s1#6095",
        sample_stem="s1",
        raw_file="s1.raw",
        neutral_loss_tag="DNA_dR",
        precursor_mz=242.114,
        product_mz=126.066,
        observed_neutral_loss_da=116.048,
        seed_rt=12.5927,
        evidence_score=80,
        seed_event_count=3,
    )
    support = IdentityEvent(
        candidate_id="s1#6096",
        sample_stem="s1",
        raw_file="s1.raw",
        neutral_loss_tag="DNA_dR",
        precursor_mz=242.1141,
        product_mz=126.0661,
        observed_neutral_loss_da=116.048,
        seed_rt=12.594,
        evidence_score=70,
        seed_event_count=1,
    )

    owner = SampleLocalMS1Owner(
        owner_id="OWN-s1-000001",
        sample_stem="s1",
        raw_file="s1.raw",
        precursor_mz=242.114,
        owner_apex_rt=12.593,
        owner_peak_start_rt=12.55,
        owner_peak_end_rt=12.64,
        owner_area=12345.0,
        owner_height=1000.0,
        primary_identity_event=primary,
        supporting_events=(support,),
        identity_conflict=False,
        assignment_reason="same_apex_window",
    )

    assert owner.all_events == (primary, support)
    assert owner.neutral_loss_tag == "DNA_dR"
    assert owner.event_candidate_ids == ("s1#6095", "s1#6096")


def test_owner_assignment_and_ambiguity_records_are_debug_contracts():
    assignment = OwnerAssignment(
        candidate_id="s1#7002",
        owner_id="OWN-s1-000003",
        assignment_status="supporting",
        reason="tail_assignment",
    )
    ambiguous = AmbiguousOwnerRecord(
        ambiguity_id="AMB-s1-000001",
        sample_stem="s1",
        candidate_ids=("s1#8001", "s1#8002"),
        reason="owner_multiplet_ambiguity",
    )

    assert assignment.assignment_status == "supporting"
    assert ambiguous.candidate_ids == ("s1#8001", "s1#8002")
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_ownership_models.py -v
```

Expected: FAIL because `ownership_models.py` does not exist.

- [ ] **Step 3: Create ownership models**

Create `xic_extractor/alignment/ownership_models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

OwnerAssignmentStatus = Literal["primary", "supporting", "ambiguous", "unresolved"]


@dataclass(frozen=True)
class IdentityEvent:
    candidate_id: str
    sample_stem: str
    raw_file: str
    neutral_loss_tag: str
    precursor_mz: float
    product_mz: float
    observed_neutral_loss_da: float
    seed_rt: float
    evidence_score: int
    seed_event_count: int


@dataclass(frozen=True)
class SampleLocalMS1Owner:
    owner_id: str
    sample_stem: str
    raw_file: str
    precursor_mz: float
    owner_apex_rt: float
    owner_peak_start_rt: float
    owner_peak_end_rt: float
    owner_area: float
    owner_height: float
    primary_identity_event: IdentityEvent
    supporting_events: tuple[IdentityEvent, ...]
    identity_conflict: bool
    assignment_reason: str

    @property
    def all_events(self) -> tuple[IdentityEvent, ...]:
        return (self.primary_identity_event, *self.supporting_events)

    @property
    def neutral_loss_tag(self) -> str:
        return self.primary_identity_event.neutral_loss_tag

    @property
    def event_candidate_ids(self) -> tuple[str, ...]:
        return tuple(event.candidate_id for event in self.all_events)


@dataclass(frozen=True)
class OwnerAssignment:
    candidate_id: str
    owner_id: str | None
    assignment_status: OwnerAssignmentStatus
    reason: str


@dataclass(frozen=True)
class AmbiguousOwnerRecord:
    ambiguity_id: str
    sample_stem: str
    candidate_ids: tuple[str, ...]
    reason: str
```

- [ ] **Step 4: Run model tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_ownership_models.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/alignment/ownership_models.py tests/test_alignment_ownership_models.py
git commit -m "feat: add sample-local MS1 ownership models"
```

## Task 3: Build Owner Resolution From Synthetic XIC Sources

**Files:**
- Create: `xic_extractor/alignment/ownership.py`
- Test: `tests/test_alignment_ownership.py`

- [ ] **Step 1: Write failing tests for same apex/window ownership**

Create `tests/test_alignment_ownership.py` with these fixtures and first test:

```python
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.ownership import build_sample_local_owners
from xic_extractor.config import ExtractionConfig


def test_same_sample_same_resolved_peak_becomes_one_owner():
    candidates = (
        _candidate("s1#6095", seed_rt=12.5927, evidence_score=80),
        _candidate("s1#6096", seed_rt=12.5940, evidence_score=70),
    )
    source = FakeXICSource(
        rt=np.array([12.55, 12.58, 12.593, 12.61, 12.64], dtype=float),
        intensity=np.array([0.0, 30.0, 100.0, 30.0, 0.0], dtype=float),
    )

    result = build_sample_local_owners(
        candidates,
        raw_sources={"s1": source},
        alignment_config=AlignmentConfig(owner_apex_close_sec=2.0),
        peak_config=_peak_config(),
    )

    assert len(result.owners) == 1
    owner = result.owners[0]
    assert owner.owner_id == "OWN-s1-000001"
    assert owner.primary_identity_event.candidate_id == "s1#6095"
    assert [event.candidate_id for event in owner.supporting_events] == ["s1#6096"]
    assert owner.assignment_reason == "owner_exact_apex_match"
    assert [(a.candidate_id, a.assignment_status) for a in result.assignments] == [
        ("s1#6095", "primary"),
        ("s1#6096", "supporting"),
    ]


class FakeXICSource:
    def __init__(self, *, rt, intensity):
        self.rt = rt
        self.intensity = intensity
        self.calls = []

    def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
        self.calls.append((mz, rt_min, rt_max, ppm_tol))
        return self.rt, self.intensity


def _candidate(
    candidate_id,
    *,
    sample_stem="s1",
    raw_file="s1.raw",
    neutral_loss_tag="DNA_dR",
    mz=242.114,
    product_mz=126.066,
    observed_loss=116.048,
    seed_rt=12.5927,
    evidence_score=80,
    seed_event_count=2,
):
    return SimpleNamespace(
        candidate_id=candidate_id,
        sample_stem=sample_stem,
        raw_file=Path(raw_file),
        neutral_loss_tag=neutral_loss_tag,
        precursor_mz=mz,
        product_mz=product_mz,
        observed_neutral_loss_da=observed_loss,
        best_seed_rt=seed_rt,
        evidence_score=evidence_score,
        seed_event_count=seed_event_count,
    )


def _peak_config():
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

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_ownership.py::test_same_sample_same_resolved_peak_becomes_one_owner -v
```

Expected: FAIL because `build_sample_local_owners` does not exist.

- [ ] **Step 3: Implement minimal owner builder**

Create `xic_extractor/alignment/ownership.py` with:

```python
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.ownership_models import (
    AmbiguousOwnerRecord,
    IdentityEvent,
    OwnerAssignment,
    SampleLocalMS1Owner,
)
from xic_extractor.config import ExtractionConfig
from xic_extractor.signal_processing import find_peak_and_area


class OwnershipXICSource(Protocol):
    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]: ...


@dataclass(frozen=True)
class ResolvedPeak:
    rt: float
    peak_start: float
    peak_end: float
    area: float
    intensity: float


PeakResolver = Callable[
    [Any, NDArray[np.float64], NDArray[np.float64], ExtractionConfig, float],
    ResolvedPeak | None,
]


@dataclass(frozen=True)
class OwnershipBuildResult:
    owners: tuple[SampleLocalMS1Owner, ...]
    assignments: tuple[OwnerAssignment, ...]
    ambiguous_records: tuple[AmbiguousOwnerRecord, ...]


@dataclass(frozen=True)
class _ResolvedCandidate:
    candidate: Any
    event: IdentityEvent
    apex_rt: float
    peak_start_rt: float
    peak_end_rt: float
    area: float
    height: float


def build_sample_local_owners(
    candidates: Sequence[Any],
    *,
    raw_sources: Mapping[str, OwnershipXICSource],
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
    peak_resolver: PeakResolver | None = None,
) -> OwnershipBuildResult:
    active_peak_resolver = peak_resolver or _default_peak_resolver
    resolved = tuple(
        item
        for item in (
            _resolve_candidate(
                candidate,
                raw_sources,
                alignment_config,
                peak_config,
                active_peak_resolver,
            )
            for candidate in candidates
        )
        if item is not None
    )
    owners: list[SampleLocalMS1Owner] = []
    assignments: list[OwnerAssignment] = []
    ambiguous_records: list[AmbiguousOwnerRecord] = []
    by_sample: dict[str, list[_ResolvedCandidate]] = defaultdict(list)
    for item in resolved:
        by_sample[item.event.sample_stem].append(item)
    for sample_stem in sorted(by_sample):
        sample_owners, sample_assignments, sample_ambiguous = _owners_for_sample(
            sample_stem,
            by_sample[sample_stem],
            alignment_config=alignment_config,
        )
        owners.extend(sample_owners)
        assignments.extend(sample_assignments)
        ambiguous_records.extend(sample_ambiguous)
    return OwnershipBuildResult(
        owners=tuple(owners),
        assignments=tuple(assignments),
        ambiguous_records=tuple(ambiguous_records),
    )


def _resolve_candidate(
    candidate: Any,
    raw_sources: Mapping[str, OwnershipXICSource],
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
    peak_resolver: PeakResolver,
) -> _ResolvedCandidate | None:
    sample_stem = str(candidate.sample_stem)
    source = raw_sources.get(sample_stem)
    if source is None:
        return None
    seed_rt = _candidate_seed_rt(candidate)
    rt_min = seed_rt - alignment_config.max_rt_sec / 60.0
    rt_max = seed_rt + alignment_config.max_rt_sec / 60.0
    rt, intensity = source.extract_xic(
        float(candidate.precursor_mz),
        rt_min,
        rt_max,
        alignment_config.preferred_ppm,
    )
    rt_array, intensity_array = _validated_trace_arrays(rt, intensity)
    peak = peak_resolver(candidate, rt_array, intensity_array, peak_config, seed_rt)
    if peak is None:
        return None
    return _ResolvedCandidate(
        candidate=candidate,
        event=_identity_event(candidate, seed_rt=seed_rt),
        apex_rt=peak.rt,
        peak_start_rt=peak.peak_start,
        peak_end_rt=peak.peak_end,
        area=peak.area,
        height=peak.intensity,
    )


def _default_peak_resolver(
    candidate: Any,
    rt_array: NDArray[np.float64],
    intensity_array: NDArray[np.float64],
    peak_config: ExtractionConfig,
    seed_rt: float,
) -> ResolvedPeak | None:
    result = find_peak_and_area(
        rt_array,
        intensity_array,
        peak_config,
        preferred_rt=seed_rt,
        strict_preferred_rt=True,
    )
    if result.status != "OK" or result.peak is None:
        return None
    peak = result.peak
    return ResolvedPeak(
        rt=peak.rt,
        peak_start=peak.peak_start,
        peak_end=peak.peak_end,
        area=peak.area,
        intensity=peak.intensity,
    )


def _owners_for_sample(
    sample_stem: str,
    resolved: list[_ResolvedCandidate],
    *,
    alignment_config: AlignmentConfig,
) -> tuple[list[SampleLocalMS1Owner], list[OwnerAssignment], list[AmbiguousOwnerRecord]]:
    pending = sorted(resolved, key=_resolved_sort_key)
    groups: list[list[_ResolvedCandidate]] = []
    for item in pending:
        for group in groups:
            if _same_owner(group[0], item, alignment_config):
                group.append(item)
                break
        else:
            groups.append([item])
    owners: list[SampleLocalMS1Owner] = []
    assignments: list[OwnerAssignment] = []
    ambiguous: list[AmbiguousOwnerRecord] = []
    for index, group in enumerate(groups, start=1):
        primary, supporting = _primary_and_supporting(group)
        owner_id = f"OWN-{sample_stem}-{index:06d}"
        owners.append(
            SampleLocalMS1Owner(
                owner_id=owner_id,
                sample_stem=sample_stem,
                raw_file=primary.event.raw_file,
                precursor_mz=primary.event.precursor_mz,
                owner_apex_rt=primary.apex_rt,
                owner_peak_start_rt=primary.peak_start_rt,
                owner_peak_end_rt=primary.peak_end_rt,
                owner_area=primary.area,
                owner_height=primary.height,
                primary_identity_event=primary.event,
                supporting_events=tuple(item.event for item in supporting),
                identity_conflict=_identity_conflict(group),
                assignment_reason="owner_exact_apex_match",
            )
        )
        assignments.append(
            OwnerAssignment(primary.event.candidate_id, owner_id, "primary", "primary_identity_event")
        )
        assignments.extend(
            OwnerAssignment(item.event.candidate_id, owner_id, "supporting", "owner_exact_apex_match")
            for item in supporting
        )
    return owners, assignments, ambiguous


def _same_owner(
    left: _ResolvedCandidate,
    right: _ResolvedCandidate,
    config: AlignmentConfig,
) -> bool:
    if _ppm(left.event.precursor_mz, right.event.precursor_mz) > config.max_ppm:
        return False
    apex_delta_sec = abs(left.apex_rt - right.apex_rt) * 60.0
    if apex_delta_sec <= config.owner_apex_close_sec:
        return True
    return _window_overlap_fraction(left, right) >= config.owner_window_overlap_fraction


def _primary_and_supporting(
    group: list[_ResolvedCandidate],
) -> tuple[_ResolvedCandidate, list[_ResolvedCandidate]]:
    ordered = sorted(group, key=_resolved_sort_key)
    return ordered[0], ordered[1:]


def _resolved_sort_key(item: _ResolvedCandidate) -> tuple[object, ...]:
    return (
        -item.event.evidence_score,
        -item.event.seed_event_count,
        -item.area,
        abs(item.event.seed_rt - item.apex_rt),
        item.event.candidate_id,
    )


def _identity_conflict(group: list[_ResolvedCandidate]) -> bool:
    tags = {item.event.neutral_loss_tag for item in group}
    return len(tags) > 1


def _identity_event(candidate: Any, *, seed_rt: float) -> IdentityEvent:
    return IdentityEvent(
        candidate_id=str(candidate.candidate_id),
        sample_stem=str(candidate.sample_stem),
        raw_file=str(candidate.raw_file),
        neutral_loss_tag=str(candidate.neutral_loss_tag),
        precursor_mz=float(candidate.precursor_mz),
        product_mz=float(candidate.product_mz),
        observed_neutral_loss_da=float(candidate.observed_neutral_loss_da),
        seed_rt=seed_rt,
        evidence_score=int(getattr(candidate, "evidence_score", 0)),
        seed_event_count=int(getattr(candidate, "seed_event_count", 0)),
    )


def _candidate_seed_rt(candidate: Any) -> float:
    for field in ("best_seed_rt", "ms1_apex_rt"):
        value = getattr(candidate, field, None)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            return float(value)
    raise ValueError("ownership candidate requires finite best_seed_rt or ms1_apex_rt")


def _window_overlap_fraction(left: _ResolvedCandidate, right: _ResolvedCandidate) -> float:
    intersection = min(left.peak_end_rt, right.peak_end_rt) - max(
        left.peak_start_rt,
        right.peak_start_rt,
    )
    if intersection <= 0:
        return 0.0
    left_width = left.peak_end_rt - left.peak_start_rt
    right_width = right.peak_end_rt - right.peak_start_rt
    denominator = min(left_width, right_width)
    if denominator <= 0:
        return 0.0
    return intersection / denominator


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
        raise ValueError("ownership trace arrays must be finite one-dimensional pairs")
    return rt_array, intensity_array


def _ppm(left: float, right: float) -> float:
    denominator = max(abs(left), 1e-12)
    return abs(left - right) / denominator * 1_000_000.0
```

- [ ] **Step 4: Run the first owner builder test**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_ownership.py::test_same_sample_same_resolved_peak_becomes_one_owner -v
```

Expected: PASS.

## Task 4: Add Tail Assignment, Ambiguity, and Identity Conflict Tests

**Files:**
- Modify: `xic_extractor/alignment/ownership.py`
- Test: `tests/test_alignment_ownership.py`

- [ ] **Step 1: Add failing tests for tail events, doublets, and different NL tags**

Append these tests to `tests/test_alignment_ownership.py`:

```python
def test_tail_events_on_one_peak_become_supporting_events():
    candidates = (
        _candidate("s1#7001", mz=251.084, seed_rt=8.50, evidence_score=85),
        _candidate("s1#7002", mz=251.0841, seed_rt=8.62, evidence_score=60),
        _candidate("s1#7003", mz=251.0842, seed_rt=8.66, evidence_score=55),
    )
    source = FakeXICSource(
        rt=np.array([8.40, 8.48, 8.52, 8.58, 8.64, 8.70], dtype=float),
        intensity=np.array([0.0, 80.0, 100.0, 50.0, 20.0, 0.0], dtype=float),
    )

    result = build_sample_local_owners(
        candidates,
        raw_sources={"s1": source},
        alignment_config=AlignmentConfig(owner_tail_seed_guard_sec=30.0),
        peak_config=_peak_config(),
    )

    assert len(result.owners) == 1
    assert result.owners[0].event_candidate_ids == ("s1#7001", "s1#7002", "s1#7003")
    assert [a.reason for a in result.assignments] == [
        "primary_identity_event",
        "owner_tail_assignment",
        "owner_tail_assignment",
    ]


def test_unresolved_doublet_becomes_ambiguous_owner_record():
    candidates = (
        _candidate("s1#8001", mz=296.074, seed_rt=10.00, evidence_score=80),
        _candidate("s1#8002", mz=296.0741, seed_rt=10.08, evidence_score=78),
    )
    source = FakeXICSource(
        rt=np.array([9.94, 10.00, 10.04, 10.08, 10.14], dtype=float),
        intensity=np.array([0.0, 100.0, 70.0, 95.0, 0.0], dtype=float),
    )

    result = build_sample_local_owners(
        candidates,
        raw_sources={"s1": source},
        alignment_config=AlignmentConfig(owner_apex_close_sec=2.0),
        peak_config=_peak_config(),
        peak_resolver=FakePeakResolver(
            {
                "s1#8001": (10.00, 9.96, 10.05, 1000.0, 100.0),
                "s1#8002": (10.08, 10.03, 10.12, 950.0, 95.0),
            },
        ),
    )

    assert result.owners == ()
    assert len(result.ambiguous_records) == 1
    assert result.ambiguous_records[0].reason == "owner_multiplet_ambiguity"
    assert {a.assignment_status for a in result.assignments} == {"ambiguous"}


class FakePeakResolver:
    def __init__(self, peaks):
        self.peaks = peaks

    def __call__(self, candidate, rt_array, intensity_array, peak_config, seed_rt):
        from xic_extractor.alignment.ownership import ResolvedPeak

        rt, start, end, area, height = self.peaks[candidate.candidate_id]
        return ResolvedPeak(
            rt=rt,
            peak_start=start,
            peak_end=end,
            area=area,
            intensity=height,
        )


def test_same_local_peak_with_different_nl_tags_is_one_owner_with_identity_conflict():
    candidates = (
        _candidate("s1#9001", neutral_loss_tag="DNA_dR", seed_rt=12.5927),
        _candidate("s1#9002", neutral_loss_tag="DNA_base_loss", seed_rt=12.5940),
    )
    source = FakeXICSource(
        rt=np.array([12.55, 12.58, 12.593, 12.61, 12.64], dtype=float),
        intensity=np.array([0.0, 30.0, 100.0, 30.0, 0.0], dtype=float),
    )

    result = build_sample_local_owners(
        candidates,
        raw_sources={"s1": source},
        alignment_config=AlignmentConfig(owner_apex_close_sec=2.0),
        peak_config=_peak_config(),
    )

    assert len(result.owners) == 1
    assert result.owners[0].identity_conflict is True
    assert result.owners[0].event_candidate_ids == ("s1#9001", "s1#9002")
```

- [ ] **Step 2: Run tests and verify the missing behavior fails**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_ownership.py -v
```

Expected: FAIL at least on tail assignment reason and doublet ambiguity.

- [ ] **Step 3: Implement deterministic tail and ambiguity rules**

Modify `_owners_for_sample()` in `xic_extractor/alignment/ownership.py` to call a new component builder:

```python
    components = _candidate_components(pending, alignment_config)
```

Add these helpers and use them before owner creation:

```python
def _candidate_components(
    items: list[_ResolvedCandidate],
    config: AlignmentConfig,
) -> list[list[_ResolvedCandidate]]:
    remaining = set(range(len(items)))
    components: list[list[_ResolvedCandidate]] = []
    while remaining:
        seed = remaining.pop()
        stack = [seed]
        component = {seed}
        while stack:
            current = stack.pop()
            for candidate_index in tuple(remaining):
                relation = _owner_relation(items[current], items[candidate_index], config)
                if relation in {"owner_exact_apex_match", "owner_tail_assignment", "owner_multiplet_ambiguity"}:
                    remaining.remove(candidate_index)
                    stack.append(candidate_index)
                    component.add(candidate_index)
        components.append([items[index] for index in sorted(component)])
    return components


def _owner_relation(
    left: _ResolvedCandidate,
    right: _ResolvedCandidate,
    config: AlignmentConfig,
) -> str | None:
    if _ppm(left.event.precursor_mz, right.event.precursor_mz) > config.max_ppm:
        return None
    apex_delta_sec = abs(left.apex_rt - right.apex_rt) * 60.0
    overlap = _window_overlap_fraction(left, right)
    if apex_delta_sec <= config.owner_apex_close_sec and overlap >= config.owner_window_overlap_fraction:
        return "owner_exact_apex_match"
    if overlap >= config.owner_window_overlap_fraction and _looks_like_unresolved_doublet(left, right):
        return "owner_multiplet_ambiguity"
    if _seed_on_peak_tail(left, right, config) or _seed_on_peak_tail(right, left, config):
        return "owner_tail_assignment"
    return None


def _looks_like_unresolved_doublet(left: _ResolvedCandidate, right: _ResolvedCandidate) -> bool:
    return abs(left.apex_rt - right.apex_rt) * 60.0 > 2.0


def _seed_on_peak_tail(
    owner: _ResolvedCandidate,
    event: _ResolvedCandidate,
    config: AlignmentConfig,
) -> bool:
    seed_delta_sec = abs(event.event.seed_rt - owner.apex_rt) * 60.0
    return (
        owner.peak_start_rt <= event.event.seed_rt <= owner.peak_end_rt
        and seed_delta_sec <= config.owner_tail_seed_guard_sec
    )
```

Then mark any component whose pairwise relation includes `owner_multiplet_ambiguity` as ambiguous:

```python
        if _component_is_ambiguous(group, alignment_config):
            ambiguity_id = f"AMB-{sample_stem}-{len(ambiguous) + 1:06d}"
            candidate_ids = tuple(item.event.candidate_id for item in sorted(group, key=_resolved_sort_key))
            ambiguous.append(
                AmbiguousOwnerRecord(
                    ambiguity_id=ambiguity_id,
                    sample_stem=sample_stem,
                    candidate_ids=candidate_ids,
                    reason="owner_multiplet_ambiguity",
                )
            )
            assignments.extend(
                OwnerAssignment(candidate_id, None, "ambiguous", "owner_multiplet_ambiguity")
                for candidate_id in candidate_ids
            )
            continue
```

Add:

```python
def _component_is_ambiguous(
    group: list[_ResolvedCandidate],
    config: AlignmentConfig,
) -> bool:
    for left_index, left in enumerate(group):
        for right in group[left_index + 1:]:
            if _owner_relation(left, right, config) == "owner_multiplet_ambiguity":
                return True
    return False
```

For assignment reasons, derive `owner_tail_assignment` when the support event seed is more than `owner_apex_close_sec` from the owner apex but inside the owner window.

- [ ] **Step 4: Run ownership tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_ownership.py tests/test_alignment_ownership_models.py -v
```

Expected: PASS.

- [ ] **Step 5: Run alignment-adjacent tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_config.py tests/test_alignment_backfill.py tests/test_alignment_family_integration.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add xic_extractor/alignment/ownership.py tests/test_alignment_ownership.py
git commit -m "feat: resolve sample-local MS1 owners"
```

## Task 5: Boundary and Quality Checks

**Files:**
- Modify: `tests/test_alignment_boundaries.py`

- [ ] **Step 1: Add boundary test that ownership module does not import writers or CLI**

Append:

```python
from pathlib import Path


def test_alignment_ownership_module_stays_domain_focused():
    source = Path("xic_extractor/alignment/ownership.py").read_text(encoding="utf-8")

    forbidden = (
        "xic_extractor.alignment.tsv_writer",
        "scripts.run_alignment",
        "openpyxl",
        "csv.",
    )
    for token in forbidden:
        assert token not in source
```

- [ ] **Step 2: Run focused tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_ownership.py tests/test_alignment_ownership_models.py tests/test_alignment_boundaries.py -v
```

Expected: PASS.

- [ ] **Step 3: Run ruff**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/alignment/ownership.py xic_extractor/alignment/ownership_models.py tests/test_alignment_ownership.py tests/test_alignment_ownership_models.py
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add tests/test_alignment_boundaries.py
git commit -m "test: protect MS1 ownership module boundaries"
```

## Acceptance Criteria

- Same sample, same resolved apex/window produces one owner and supporting events.
- Same sample, same MS1 owner with different NL tags is allowed locally and flagged as `identity_conflict`.
- Doublet/multiplet fixture becomes ambiguous instead of an unconditional merge.
- No pipeline output defaults change.
- Ownership code does not import CLI, TSV writer, workbook writer, or HTML renderer.

## Verification Commands

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_ownership.py tests/test_alignment_ownership_models.py tests/test_alignment_config.py tests/test_alignment_boundaries.py -v
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/alignment tests/test_alignment_ownership.py tests/test_alignment_ownership_models.py
```

## Stop Conditions

Stop and report before changing behavior if:

- `find_peak_and_area()` cannot resolve the synthetic local peaks deterministically.
- The implementation needs candidate CSV peak boundary columns to pass tests.
- The only way to pass the doublet test is to collapse all close peaks into one owner.
