# Untargeted Discovery V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-RAW strict MS2 neutral-loss discovery workflow that outputs one review-first `discovery_candidates.csv` with MS1 XIC apex, height, area, and trace evidence.

**Architecture:** Add a new `xic_extractor.discovery` package parallel to targeted extraction. Reuse low-level RAW access, neutral-loss semantics, and `find_peak_and_area`, but keep discovery models, grouping, priority, CSV, and CLI separate from targeted result models and workbook output.

**Tech Stack:** Python 3.10+, `numpy`, existing Thermo `raw_reader`, existing `ExtractionConfig`, `signal_processing.find_peak_and_area`, `pytest`, `ruff`, `mypy`.

---

## File Structure

Create focused modules:

| File | Responsibility |
|---|---|
| `xic_extractor/discovery/__init__.py` | Public discovery package exports. |
| `xic_extractor/discovery/models.py` | `NeutralLossProfile`, `DiscoverySettings`, `DiscoverySeed`, `DiscoverySeedGroup`, `DiscoveryCandidate`, CSV column constants. |
| `xic_extractor/discovery/ms2_seeds.py` | Scan MS2 events and create strict observed-neutral-loss seeds. |
| `xic_extractor/discovery/grouping.py` | Conservative within-file seed grouping and deterministic representative seed selection. |
| `xic_extractor/discovery/ms1_backfill.py` | Extract MS1 XIC for each seed group and attach peak/area evidence. |
| `xic_extractor/discovery/priority.py` | `HIGH` / `MEDIUM` / `LOW` priority and short reason text. |
| `xic_extractor/discovery/csv_writer.py` | Review-first `discovery_candidates.csv` rendering with fixed first 12 columns. |
| `xic_extractor/discovery/pipeline.py` | Orchestrate one raw file: seed scan -> grouping -> MS1 backfill -> CSV. |
| `scripts/run_discovery.py` | CLI entry point for single-RAW discovery. |
| `pyproject.toml` | Add `xic-discovery-cli = "scripts.run_discovery:main"`. |

Test files:

| File | Coverage |
|---|---|
| `tests/test_discovery_ms2_seeds.py` | Strict seed creation and rejection cases. |
| `tests/test_discovery_grouping.py` | Grouping, split conditions, representative seed. |
| `tests/test_discovery_ms1_backfill.py` | MS1 search window, peak found/missing, area propagation. |
| `tests/test_discovery_csv.py` | Header order, sorting, numeric formatting, empty output. |
| `tests/test_discovery_pipeline.py` | End-to-end fake raw workflow, targeted pipeline untouched. |
| `tests/test_run_discovery.py` | CLI argument parsing and error handling without real RAW files. |

Do not modify:

- `xic_extractor/extractor.py`
- `xic_extractor/extraction/*`
- GUI files
- workbook schema files
- targeted config defaults

---

## Task 1: Discovery Models And CSV Contract

**Files:**
- Create: `xic_extractor/discovery/__init__.py`
- Create: `xic_extractor/discovery/models.py`
- Test: `tests/test_discovery_csv.py`

- [ ] **Step 1: Write the failing model/header test**

Create `tests/test_discovery_csv.py`:

```python
from pathlib import Path

from xic_extractor.discovery.models import (
    DISCOVERY_CANDIDATE_COLUMNS,
    DISCOVERY_REVIEW_COLUMNS,
    DiscoveryCandidate,
    DiscoverySeed,
)


def test_discovery_review_columns_are_first_visible_columns() -> None:
    assert DISCOVERY_REVIEW_COLUMNS == (
        "review_priority",
        "candidate_id",
        "precursor_mz",
        "product_mz",
        "observed_neutral_loss_da",
        "best_seed_rt",
        "seed_event_count",
        "ms1_peak_found",
        "ms1_apex_rt",
        "ms1_area",
        "ms2_product_max_intensity",
        "reason",
    )
    assert DISCOVERY_CANDIDATE_COLUMNS[:12] == DISCOVERY_REVIEW_COLUMNS


def test_discovery_candidate_id_uses_sample_and_best_ms2_scan() -> None:
    seed = DiscoverySeed(
        raw_file=Path("TumorBC2312_DNA.raw"),
        sample_stem="TumorBC2312_DNA",
        scan_number=6095,
        rt=8.49,
        precursor_mz=359.045,
        product_mz=242.997,
        product_intensity=54138.0,
        neutral_loss_tag="DNA_dR",
        configured_neutral_loss_da=116.0474,
        observed_neutral_loss_da=116.048,
        observed_loss_error_ppm=5.2,
    )
    candidate = DiscoveryCandidate.from_values(
        raw_file=Path("TumorBC2312_DNA.raw"),
        sample_stem="TumorBC2312_DNA",
        best_seed=seed,
        seed_scan_ids=(6095,),
        seed_event_count=1,
        neutral_loss_tag="DNA_dR",
        configured_neutral_loss_da=116.0474,
        observed_neutral_loss_da=116.048,
        neutral_loss_mass_error_ppm=5.2,
        precursor_mz=359.045,
        product_mz=242.997,
        best_seed_rt=8.49,
        rt_seed_min=8.49,
        rt_seed_max=8.49,
        ms1_search_rt_min=8.29,
        ms1_search_rt_max=8.69,
        ms1_peak_found=True,
        ms1_apex_rt=8.50,
        ms1_seed_delta_min=0.01,
        ms1_peak_rt_start=8.42,
        ms1_peak_rt_end=8.58,
        ms1_height=120000.0,
        ms1_area=450000.0,
        ms1_trace_quality="clean",
        ms2_product_max_intensity=54138.0,
        review_priority="MEDIUM",
        reason="single MS2 NL seed; MS1 peak found",
    )

    assert candidate.candidate_id == "TumorBC2312_DNA#6095"
    assert candidate.seed_scan_ids == (6095,)
```

- [ ] **Step 2: Run the red test**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_csv.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'xic_extractor.discovery'`.

- [ ] **Step 3: Create minimal discovery models**

Create `xic_extractor/discovery/__init__.py`:

```python
"""Single-RAW discovery workflow for strict MS2 neutral-loss candidates."""
```

Create `xic_extractor/discovery/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


ReviewPriority = Literal["HIGH", "MEDIUM", "LOW"]

DISCOVERY_REVIEW_COLUMNS = (
    "review_priority",
    "candidate_id",
    "precursor_mz",
    "product_mz",
    "observed_neutral_loss_da",
    "best_seed_rt",
    "seed_event_count",
    "ms1_peak_found",
    "ms1_apex_rt",
    "ms1_area",
    "ms2_product_max_intensity",
    "reason",
)

DISCOVERY_PROVENANCE_COLUMNS = (
    "raw_file",
    "sample_stem",
    "best_ms2_scan_id",
    "seed_scan_ids",
    "neutral_loss_tag",
    "configured_neutral_loss_da",
    "neutral_loss_mass_error_ppm",
    "rt_seed_min",
    "rt_seed_max",
    "ms1_search_rt_min",
    "ms1_search_rt_max",
    "ms1_seed_delta_min",
    "ms1_peak_rt_start",
    "ms1_peak_rt_end",
    "ms1_height",
    "ms1_trace_quality",
)

DISCOVERY_CANDIDATE_COLUMNS = DISCOVERY_REVIEW_COLUMNS + DISCOVERY_PROVENANCE_COLUMNS


@dataclass(frozen=True)
class NeutralLossProfile:
    tag: str
    neutral_loss_da: float


@dataclass(frozen=True)
class DiscoverySettings:
    neutral_loss_profile: NeutralLossProfile
    nl_tolerance_ppm: float = 20.0
    precursor_mz_tolerance_ppm: float = 20.0
    product_mz_tolerance_ppm: float = 20.0
    product_search_ppm: float = 50.0
    nl_min_intensity_ratio: float = 0.01
    seed_rt_gap_min: float = 0.20
    ms1_search_padding_min: float = 0.20
    rt_min: float = 0.0
    rt_max: float = 999.0
    resolver_mode: str = "local_minimum"


@dataclass(frozen=True)
class DiscoverySeed:
    raw_file: Path
    sample_stem: str
    scan_number: int
    rt: float
    precursor_mz: float
    product_mz: float
    product_intensity: float
    neutral_loss_tag: str
    configured_neutral_loss_da: float
    observed_neutral_loss_da: float
    observed_loss_error_ppm: float


@dataclass(frozen=True)
class DiscoverySeedGroup:
    raw_file: Path
    sample_stem: str
    seeds: tuple[DiscoverySeed, ...]
    neutral_loss_tag: str
    configured_neutral_loss_da: float
    precursor_mz: float
    product_mz: float
    observed_neutral_loss_da: float
    neutral_loss_mass_error_ppm: float
    rt_seed_min: float
    rt_seed_max: float


@dataclass(frozen=True)
class DiscoveryCandidate:
    candidate_id: str
    raw_file: Path
    sample_stem: str
    best_ms2_scan_id: int
    seed_scan_ids: tuple[int, ...]
    seed_event_count: int
    neutral_loss_tag: str
    configured_neutral_loss_da: float
    observed_neutral_loss_da: float
    neutral_loss_mass_error_ppm: float
    precursor_mz: float
    product_mz: float
    best_seed_rt: float
    rt_seed_min: float
    rt_seed_max: float
    ms1_search_rt_min: float
    ms1_search_rt_max: float
    ms1_peak_found: bool
    ms1_apex_rt: float | None
    ms1_seed_delta_min: float | None
    ms1_peak_rt_start: float | None
    ms1_peak_rt_end: float | None
    ms1_height: float | None
    ms1_area: float | None
    ms1_trace_quality: str
    ms2_product_max_intensity: float
    review_priority: ReviewPriority
    reason: str

    @classmethod
    def from_values(
        cls,
        *,
        raw_file: Path,
        sample_stem: str,
        best_seed: DiscoverySeed,
        seed_scan_ids: tuple[int, ...],
        seed_event_count: int,
        neutral_loss_tag: str,
        configured_neutral_loss_da: float,
        observed_neutral_loss_da: float,
        neutral_loss_mass_error_ppm: float,
        precursor_mz: float,
        product_mz: float,
        best_seed_rt: float,
        rt_seed_min: float,
        rt_seed_max: float,
        ms1_search_rt_min: float,
        ms1_search_rt_max: float,
        ms1_peak_found: bool,
        ms1_apex_rt: float | None,
        ms1_seed_delta_min: float | None,
        ms1_peak_rt_start: float | None,
        ms1_peak_rt_end: float | None,
        ms1_height: float | None,
        ms1_area: float | None,
        ms1_trace_quality: str,
        ms2_product_max_intensity: float,
        review_priority: ReviewPriority,
        reason: str,
    ) -> "DiscoveryCandidate":
        return cls(
            candidate_id=f"{sample_stem}#{best_seed.scan_number}",
            raw_file=raw_file,
            sample_stem=sample_stem,
            best_ms2_scan_id=best_seed.scan_number,
            seed_scan_ids=seed_scan_ids,
            seed_event_count=seed_event_count,
            neutral_loss_tag=neutral_loss_tag,
            configured_neutral_loss_da=configured_neutral_loss_da,
            observed_neutral_loss_da=observed_neutral_loss_da,
            neutral_loss_mass_error_ppm=neutral_loss_mass_error_ppm,
            precursor_mz=precursor_mz,
            product_mz=product_mz,
            best_seed_rt=best_seed_rt,
            rt_seed_min=rt_seed_min,
            rt_seed_max=rt_seed_max,
            ms1_search_rt_min=ms1_search_rt_min,
            ms1_search_rt_max=ms1_search_rt_max,
            ms1_peak_found=ms1_peak_found,
            ms1_apex_rt=ms1_apex_rt,
            ms1_seed_delta_min=ms1_seed_delta_min,
            ms1_peak_rt_start=ms1_peak_rt_start,
            ms1_peak_rt_end=ms1_peak_rt_end,
            ms1_height=ms1_height,
            ms1_area=ms1_area,
            ms1_trace_quality=ms1_trace_quality,
            ms2_product_max_intensity=ms2_product_max_intensity,
            review_priority=review_priority,
            reason=reason,
        )
```

- [ ] **Step 4: Run the model/header test green**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_csv.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git add xic_extractor/discovery/__init__.py xic_extractor/discovery/models.py tests/test_discovery_csv.py
git commit -m "feat: add discovery candidate models"
```

---

## Task 2: Strict MS2 Neutral-Loss Seed Scanner

**Files:**
- Create: `xic_extractor/discovery/ms2_seeds.py`
- Modify: `xic_extractor/discovery/__init__.py`
- Test: `tests/test_discovery_ms2_seeds.py`

- [ ] **Step 1: Write failing seed scanner tests**

Create `tests/test_discovery_ms2_seeds.py`:

```python
from pathlib import Path

import numpy as np

from xic_extractor.discovery.models import DiscoverySettings, NeutralLossProfile
from xic_extractor.discovery.ms2_seeds import collect_strict_nl_seeds
from xic_extractor.raw_reader import Ms2Scan, Ms2ScanEvent


NEUTRAL_LOSS_DA = 116.0474


class FakeRaw:
    def __init__(self, events: list[Ms2ScanEvent]) -> None:
        self.events = events
        self.requested_window: tuple[float, float] | None = None

    def iter_ms2_scans(self, rt_min: float, rt_max: float):
        self.requested_window = (rt_min, rt_max)
        yield from self.events


def _settings() -> DiscoverySettings:
    return DiscoverySettings(
        neutral_loss_profile=NeutralLossProfile("DNA_dR", NEUTRAL_LOSS_DA),
        nl_tolerance_ppm=20.0,
        product_search_ppm=50.0,
        nl_min_intensity_ratio=0.01,
        rt_min=0.0,
        rt_max=30.0,
    )


def _scan(
    *,
    scan_number: int = 6095,
    rt: float = 8.49,
    precursor_mz: float = 359.0450,
    product_mz: float | None = None,
    product_intensity: float = 50000.0,
) -> Ms2Scan:
    product = product_mz if product_mz is not None else precursor_mz - NEUTRAL_LOSS_DA
    return Ms2Scan(
        scan_number=scan_number,
        rt=rt,
        precursor_mz=precursor_mz,
        masses=np.array([product, product + 0.1]),
        intensities=np.array([product_intensity, 50.0]),
        base_peak=product_intensity,
    )


def test_collect_strict_nl_seeds_accepts_observed_loss_match() -> None:
    raw = FakeRaw([Ms2ScanEvent(scan=_scan(), parse_error=None, scan_number=6095)])

    seeds = collect_strict_nl_seeds(
        raw,
        raw_file=Path("TumorBC2312_DNA.raw"),
        settings=_settings(),
    )

    assert raw.requested_window == (0.0, 30.0)
    assert len(seeds) == 1
    assert seeds[0].sample_stem == "TumorBC2312_DNA"
    assert seeds[0].scan_number == 6095
    assert seeds[0].precursor_mz == 359.0450
    assert seeds[0].product_mz == 359.0450 - NEUTRAL_LOSS_DA
    assert seeds[0].observed_loss_error_ppm == 0.0


def test_collect_strict_nl_seeds_rejects_product_outside_loss_tolerance() -> None:
    bad_product = 359.0450 - (NEUTRAL_LOSS_DA * (1 + 100.0 / 1_000_000.0))
    raw = FakeRaw(
        [
            Ms2ScanEvent(
                scan=_scan(product_mz=bad_product),
                parse_error=None,
                scan_number=6095,
            )
        ]
    )

    seeds = collect_strict_nl_seeds(
        raw,
        raw_file=Path("TumorBC2312_DNA.raw"),
        settings=_settings(),
    )

    assert seeds == ()


def test_collect_strict_nl_seeds_ignores_parse_errors_and_low_intensity() -> None:
    low = _scan(product_intensity=5.0)
    low = Ms2Scan(
        scan_number=low.scan_number,
        rt=low.rt,
        precursor_mz=low.precursor_mz,
        masses=low.masses,
        intensities=low.intensities,
        base_peak=1000.0,
    )
    raw = FakeRaw(
        [
            Ms2ScanEvent(scan=None, parse_error="broken filter", scan_number=1),
            Ms2ScanEvent(scan=low, parse_error=None, scan_number=6095),
        ]
    )

    seeds = collect_strict_nl_seeds(
        raw,
        raw_file=Path("TumorBC2312_DNA.raw"),
        settings=_settings(),
    )

    assert seeds == ()
```

- [ ] **Step 2: Run the red test**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_ms2_seeds.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `xic_extractor.discovery.ms2_seeds`.

- [ ] **Step 3: Implement strict seed collection**

Create `xic_extractor/discovery/ms2_seeds.py`:

```python
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

import numpy as np

from xic_extractor.discovery.models import DiscoverySeed, DiscoverySettings
from xic_extractor.raw_reader import Ms2Scan, Ms2ScanEvent


class MS2ScanSource(Protocol):
    def iter_ms2_scans(self, rt_min: float, rt_max: float) -> Iterator[Ms2ScanEvent]:
        ...


def collect_strict_nl_seeds(
    raw: MS2ScanSource,
    *,
    raw_file: Path,
    settings: DiscoverySettings,
) -> tuple[DiscoverySeed, ...]:
    seeds: list[DiscoverySeed] = []
    sample_stem = raw_file.stem
    for event in raw.iter_ms2_scans(settings.rt_min, settings.rt_max):
        if event.parse_error is not None or event.scan is None:
            continue
        seed = _seed_from_scan(
            event.scan,
            raw_file=raw_file,
            sample_stem=sample_stem,
            settings=settings,
        )
        if seed is not None:
            seeds.append(seed)
    return tuple(seeds)


def _seed_from_scan(
    scan: Ms2Scan,
    *,
    raw_file: Path,
    sample_stem: str,
    settings: DiscoverySettings,
) -> DiscoverySeed | None:
    evidence = _best_strict_product(scan, settings=settings)
    if evidence is None:
        return None
    product_mz, product_intensity, observed_loss_da, observed_loss_error_ppm = evidence
    return DiscoverySeed(
        raw_file=raw_file,
        sample_stem=sample_stem,
        scan_number=scan.scan_number,
        rt=scan.rt,
        precursor_mz=scan.precursor_mz,
        product_mz=product_mz,
        product_intensity=product_intensity,
        neutral_loss_tag=settings.neutral_loss_profile.tag,
        configured_neutral_loss_da=settings.neutral_loss_profile.neutral_loss_da,
        observed_neutral_loss_da=observed_loss_da,
        observed_loss_error_ppm=observed_loss_error_ppm,
    )


def _best_strict_product(
    scan: Ms2Scan,
    *,
    settings: DiscoverySettings,
) -> tuple[float, float, float, float] | None:
    neutral_loss_da = settings.neutral_loss_profile.neutral_loss_da
    expected_product = scan.precursor_mz - neutral_loss_da
    if expected_product <= 0.0 or scan.base_peak <= 0.0:
        return None

    masses = np.asarray(scan.masses, dtype=float)
    intensities = np.asarray(scan.intensities, dtype=float)
    if masses.size == 0 or intensities.size == 0 or masses.size != intensities.size:
        return None

    intensity_floor = scan.base_peak * settings.nl_min_intensity_ratio
    product_ppm = np.abs(masses - expected_product) / expected_product * 1_000_000.0
    mask = (intensities >= intensity_floor) & (product_ppm <= settings.product_search_ppm)
    if not mask.any():
        return None

    candidates: list[tuple[float, float, float, float]] = []
    for index in np.flatnonzero(mask):
        product_mz = float(masses[int(index)])
        observed_loss_da = scan.precursor_mz - product_mz
        observed_loss_error_ppm = (
            abs(observed_loss_da - neutral_loss_da) / neutral_loss_da * 1_000_000.0
        )
        if observed_loss_error_ppm <= settings.nl_tolerance_ppm:
            candidates.append(
                (
                    product_mz,
                    float(intensities[int(index)]),
                    observed_loss_da,
                    observed_loss_error_ppm,
                )
            )
    if not candidates:
        return None
    return min(candidates, key=lambda item: (item[3], -item[1]))
```

- [ ] **Step 4: Run seed tests green**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_ms2_seeds.py tests/test_discovery_csv.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

Run:

```powershell
git add xic_extractor/discovery/ms2_seeds.py tests/test_discovery_ms2_seeds.py
git commit -m "feat: collect discovery neutral loss seeds"
```

---

## Task 3: Conservative Seed Grouping

**Files:**
- Create: `xic_extractor/discovery/grouping.py`
- Test: `tests/test_discovery_grouping.py`

- [ ] **Step 1: Write failing grouping tests**

Create `tests/test_discovery_grouping.py`:

```python
from pathlib import Path

from xic_extractor.discovery.grouping import group_discovery_seeds, select_best_seed
from xic_extractor.discovery.models import DiscoverySeed, DiscoverySettings, NeutralLossProfile


def _settings() -> DiscoverySettings:
    return DiscoverySettings(
        neutral_loss_profile=NeutralLossProfile("DNA_dR", 116.0474),
        precursor_mz_tolerance_ppm=20.0,
        product_mz_tolerance_ppm=20.0,
        nl_tolerance_ppm=20.0,
        seed_rt_gap_min=0.20,
    )


def _seed(
    scan: int,
    *,
    rt: float,
    precursor_mz: float = 359.0450,
    product_mz: float = 242.9976,
    intensity: float = 1000.0,
    ppm: float = 3.0,
) -> DiscoverySeed:
    return DiscoverySeed(
        raw_file=Path("TumorBC2312_DNA.raw"),
        sample_stem="TumorBC2312_DNA",
        scan_number=scan,
        rt=rt,
        precursor_mz=precursor_mz,
        product_mz=product_mz,
        product_intensity=intensity,
        neutral_loss_tag="DNA_dR",
        configured_neutral_loss_da=116.0474,
        observed_neutral_loss_da=precursor_mz - product_mz,
        observed_loss_error_ppm=ppm,
    )


def test_group_discovery_seeds_merges_close_rt_and_mz_events() -> None:
    groups = group_discovery_seeds(
        [
            _seed(10, rt=8.40, intensity=1000.0),
            _seed(11, rt=8.55, intensity=2000.0),
        ],
        settings=_settings(),
    )

    assert len(groups) == 1
    assert groups[0].seed_count == 2
    assert groups[0].seed_scan_ids == (10, 11)
    assert groups[0].rt_seed_min == 8.40
    assert groups[0].rt_seed_max == 8.55
    assert groups[0].precursor_mz == 359.0450


def test_group_discovery_seeds_splits_large_rt_gap() -> None:
    groups = group_discovery_seeds(
        [
            _seed(10, rt=8.40),
            _seed(11, rt=8.75),
        ],
        settings=_settings(),
    )

    assert len(groups) == 2
    assert [group.seed_scan_ids for group in groups] == [(10,), (11,)]


def test_group_discovery_seeds_splits_precursor_outside_tolerance() -> None:
    groups = group_discovery_seeds(
        [
            _seed(10, rt=8.40, precursor_mz=359.0450),
            _seed(11, rt=8.45, precursor_mz=359.0800),
        ],
        settings=_settings(),
    )

    assert len(groups) == 2


def test_select_best_seed_prefers_intensity_then_mass_error_then_scan_number() -> None:
    best = select_best_seed(
        (
            _seed(12, rt=8.50, intensity=2000.0, ppm=8.0),
            _seed(11, rt=8.45, intensity=2000.0, ppm=3.0),
            _seed(10, rt=8.40, intensity=1000.0, ppm=1.0),
        )
    )

    assert best.scan_number == 11
```

- [ ] **Step 2: Run the red test**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_grouping.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `xic_extractor.discovery.grouping`.

- [ ] **Step 3: Add grouping properties to `DiscoverySeedGroup`**

Modify `xic_extractor/discovery/models.py` by adding these properties inside `DiscoverySeedGroup`:

```python
    @property
    def seed_count(self) -> int:
        return len(self.seeds)

    @property
    def seed_scan_ids(self) -> tuple[int, ...]:
        return tuple(seed.scan_number for seed in self.seeds)
```

- [ ] **Step 4: Implement conservative grouping**

Create `xic_extractor/discovery/grouping.py`:

```python
from __future__ import annotations

from statistics import fmean

from xic_extractor.discovery.models import (
    DiscoverySeed,
    DiscoverySeedGroup,
    DiscoverySettings,
)


def group_discovery_seeds(
    seeds: list[DiscoverySeed] | tuple[DiscoverySeed, ...],
    *,
    settings: DiscoverySettings,
) -> tuple[DiscoverySeedGroup, ...]:
    if not seeds:
        return ()

    sorted_seeds = sorted(
        seeds,
        key=lambda seed: (
            seed.neutral_loss_tag,
            seed.precursor_mz,
            seed.product_mz,
            seed.rt,
            seed.scan_number,
        ),
    )
    groups: list[list[DiscoverySeed]] = []
    for seed in sorted_seeds:
        if not groups or not _can_join(groups[-1], seed, settings=settings):
            groups.append([seed])
        else:
            groups[-1].append(seed)
    return tuple(_build_group(group) for group in groups)


def select_best_seed(
    seeds: tuple[DiscoverySeed, ...],
    *,
    ms1_apex_rt: float | None = None,
) -> DiscoverySeed:
    if ms1_apex_rt is None:
        return min(
            seeds,
            key=lambda seed: (
                -seed.product_intensity,
                seed.observed_loss_error_ppm,
                seed.scan_number,
            ),
        )
    return min(
        seeds,
        key=lambda seed: (
            -seed.product_intensity,
            seed.observed_loss_error_ppm,
            abs(seed.rt - ms1_apex_rt),
            seed.scan_number,
        ),
    )


def _can_join(
    current: list[DiscoverySeed],
    seed: DiscoverySeed,
    *,
    settings: DiscoverySettings,
) -> bool:
    previous = current[-1]
    if seed.neutral_loss_tag != previous.neutral_loss_tag:
        return False
    if seed.rt - previous.rt > settings.seed_rt_gap_min:
        return False
    return (
        _ppm_delta(seed.precursor_mz, _mean(current, "precursor_mz"))
        <= settings.precursor_mz_tolerance_ppm
        and _ppm_delta(seed.product_mz, _mean(current, "product_mz"))
        <= settings.product_mz_tolerance_ppm
        and _ppm_delta(
            seed.observed_neutral_loss_da,
            _mean(current, "observed_neutral_loss_da"),
        )
        <= settings.nl_tolerance_ppm
    )


def _build_group(seeds: list[DiscoverySeed]) -> DiscoverySeedGroup:
    seed_tuple = tuple(sorted(seeds, key=lambda seed: seed.rt))
    return DiscoverySeedGroup(
        raw_file=seed_tuple[0].raw_file,
        sample_stem=seed_tuple[0].sample_stem,
        seeds=seed_tuple,
        neutral_loss_tag=seed_tuple[0].neutral_loss_tag,
        configured_neutral_loss_da=seed_tuple[0].configured_neutral_loss_da,
        precursor_mz=_mean(seed_tuple, "precursor_mz"),
        product_mz=_mean(seed_tuple, "product_mz"),
        observed_neutral_loss_da=_mean(seed_tuple, "observed_neutral_loss_da"),
        neutral_loss_mass_error_ppm=min(
            seed.observed_loss_error_ppm for seed in seed_tuple
        ),
        rt_seed_min=min(seed.rt for seed in seed_tuple),
        rt_seed_max=max(seed.rt for seed in seed_tuple),
    )


def _mean(seeds: list[DiscoverySeed] | tuple[DiscoverySeed, ...], field: str) -> float:
    return fmean(float(getattr(seed, field)) for seed in seeds)


def _ppm_delta(value: float, reference: float) -> float:
    if reference <= 0.0:
        return float("inf")
    return abs(value - reference) / reference * 1_000_000.0
```

- [ ] **Step 5: Run grouping tests green**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_grouping.py tests/test_discovery_ms2_seeds.py tests/test_discovery_csv.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

Run:

```powershell
git add xic_extractor/discovery/models.py xic_extractor/discovery/grouping.py tests/test_discovery_grouping.py
git commit -m "feat: group discovery seeds into candidates"
```

---

## Task 4: MS1 XIC Backfill And Candidate Priority

**Files:**
- Create: `xic_extractor/discovery/priority.py`
- Create: `xic_extractor/discovery/ms1_backfill.py`
- Test: `tests/test_discovery_ms1_backfill.py`

- [ ] **Step 1: Write failing MS1 backfill tests**

Create `tests/test_discovery_ms1_backfill.py`:

```python
from dataclasses import replace
from pathlib import Path

import numpy as np

from xic_extractor.config import ExtractionConfig
from xic_extractor.discovery.grouping import group_discovery_seeds
from xic_extractor.discovery.models import DiscoverySeed, DiscoverySettings, NeutralLossProfile
from xic_extractor.discovery.ms1_backfill import backfill_ms1_candidates


def _config() -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=Path("."),
        dll_dir=Path("."),
        output_csv=Path("out.csv"),
        diagnostics_csv=Path("diag.csv"),
        smooth_window=11,
        smooth_polyorder=3,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.10,
        ms2_precursor_tol_da=1.6,
        nl_min_intensity_ratio=0.01,
        resolver_mode="local_minimum",
    )


def _settings() -> DiscoverySettings:
    return DiscoverySettings(
        neutral_loss_profile=NeutralLossProfile("DNA_dR", 116.0474),
        seed_rt_gap_min=0.20,
        ms1_search_padding_min=0.20,
        precursor_mz_tolerance_ppm=20.0,
    )


def _seed(scan: int, rt: float, intensity: float = 1000.0) -> DiscoverySeed:
    return DiscoverySeed(
        raw_file=Path("TumorBC2312_DNA.raw"),
        sample_stem="TumorBC2312_DNA",
        scan_number=scan,
        rt=rt,
        precursor_mz=359.045,
        product_mz=242.9976,
        product_intensity=intensity,
        neutral_loss_tag="DNA_dR",
        configured_neutral_loss_da=116.0474,
        observed_neutral_loss_da=116.0474,
        observed_loss_error_ppm=2.0,
    )


class FakeRaw:
    def __init__(self, rt: np.ndarray, intensity: np.ndarray) -> None:
        self.rt = rt
        self.intensity = intensity
        self.request: tuple[float, float, float, float] | None = None

    def extract_xic(self, mz: float, rt_min: float, rt_max: float, ppm_tol: float):
        self.request = (mz, rt_min, rt_max, ppm_tol)
        mask = (self.rt >= rt_min) & (self.rt <= rt_max)
        return self.rt[mask], self.intensity[mask]


def test_backfill_ms1_candidate_uses_seed_range_plus_padding_and_area() -> None:
    rt = np.linspace(8.0, 9.0, 101)
    intensity = 1000.0 * np.exp(-((rt - 8.50) ** 2) / (2 * 0.04**2))
    raw = FakeRaw(rt, intensity)
    groups = group_discovery_seeds(
        [_seed(10, 8.40, 1000.0), _seed(11, 8.55, 2000.0)],
        settings=_settings(),
    )

    candidates = backfill_ms1_candidates(
        raw,
        groups,
        settings=_settings(),
        peak_config=_config(),
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert raw.request == (359.045, 8.20, 8.75, 20.0)
    assert candidate.review_priority == "HIGH"
    assert candidate.ms1_peak_found is True
    assert candidate.ms1_area is not None
    assert candidate.ms1_area > 0
    assert candidate.best_ms2_scan_id == 11
    assert candidate.reason == "strong MS2 NL seed group; MS1 peak found near seed RT"


def test_backfill_ms1_candidate_keeps_low_priority_when_no_ms1_peak() -> None:
    rt = np.linspace(8.0, 9.0, 101)
    intensity = np.zeros_like(rt)
    raw = FakeRaw(rt, intensity)
    groups = group_discovery_seeds([_seed(10, 8.40)], settings=_settings())

    candidates = backfill_ms1_candidates(
        raw,
        groups,
        settings=_settings(),
        peak_config=_config(),
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.review_priority == "LOW"
    assert candidate.ms1_peak_found is False
    assert candidate.ms1_area is None
    assert candidate.reason == "strict NL seed found; no MS1 peak in seed window"


def test_backfill_ms1_candidate_sets_medium_for_single_seed_with_ms1_peak() -> None:
    rt = np.linspace(8.0, 9.0, 101)
    intensity = 1000.0 * np.exp(-((rt - 8.43) ** 2) / (2 * 0.04**2))
    raw = FakeRaw(rt, intensity)
    groups = group_discovery_seeds([_seed(10, 8.40)], settings=_settings())

    candidates = backfill_ms1_candidates(
        raw,
        groups,
        settings=_settings(),
        peak_config=replace(_config(), resolver_mode="legacy_savgol"),
    )

    assert candidates[0].review_priority == "MEDIUM"
    assert candidates[0].reason == "single MS2 NL seed; MS1 peak found"
```

- [ ] **Step 2: Run the red test**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_ms1_backfill.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `xic_extractor.discovery.ms1_backfill`.

- [ ] **Step 3: Implement priority rules**

Create `xic_extractor/discovery/priority.py`:

```python
from __future__ import annotations

from xic_extractor.discovery.models import DiscoverySeedGroup, ReviewPriority


def assign_review_priority(
    group: DiscoverySeedGroup,
    *,
    ms1_peak_found: bool,
    ms1_apex_rt: float | None,
    ms1_trace_quality: str,
) -> tuple[ReviewPriority, str]:
    if not ms1_peak_found or ms1_apex_rt is None:
        return "LOW", "strict NL seed found; no MS1 peak in seed window"
    if ms1_trace_quality != "clean":
        return "LOW", "strict NL seed found; weak MS1 trace"
    if group.seed_count >= 2 and group.rt_seed_min <= ms1_apex_rt <= group.rt_seed_max:
        return "HIGH", "strong MS2 NL seed group; MS1 peak found near seed RT"
    if group.seed_count >= 2:
        return "HIGH", "strong MS2 NL seed group; MS1 peak found near seed RT"
    return "MEDIUM", "single MS2 NL seed; MS1 peak found"
```

- [ ] **Step 4: Implement MS1 backfill**

Create `xic_extractor/discovery/ms1_backfill.py`:

```python
from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

import numpy as np

from xic_extractor.config import ExtractionConfig
from xic_extractor.discovery.grouping import select_best_seed
from xic_extractor.discovery.models import (
    DiscoveryCandidate,
    DiscoverySeedGroup,
    DiscoverySettings,
)
from xic_extractor.discovery.priority import assign_review_priority
from xic_extractor.signal_processing import find_peak_and_area


class MS1XicSource(Protocol):
    def extract_xic(
        self, mz: float, rt_min: float, rt_max: float, ppm_tol: float
    ) -> tuple[np.ndarray, np.ndarray]:
        ...


def backfill_ms1_candidates(
    raw: MS1XicSource,
    groups: Iterable[DiscoverySeedGroup],
    *,
    settings: DiscoverySettings,
    peak_config: ExtractionConfig,
) -> tuple[DiscoveryCandidate, ...]:
    candidates: list[DiscoveryCandidate] = []
    for group in groups:
        candidates.append(
            _backfill_one(raw, group, settings=settings, peak_config=peak_config)
        )
    return tuple(candidates)


def _backfill_one(
    raw: MS1XicSource,
    group: DiscoverySeedGroup,
    *,
    settings: DiscoverySettings,
    peak_config: ExtractionConfig,
) -> DiscoveryCandidate:
    search_rt_min = group.rt_seed_min - settings.ms1_search_padding_min
    search_rt_max = group.rt_seed_max + settings.ms1_search_padding_min
    rt, intensity = raw.extract_xic(
        group.precursor_mz,
        search_rt_min,
        search_rt_max,
        settings.precursor_mz_tolerance_ppm,
    )
    detection = find_peak_and_area(rt, intensity, peak_config)
    peak = detection.peak
    ms1_peak_found = peak is not None and peak.area > 0.0
    ms1_trace_quality = _trace_quality_label(detection) if ms1_peak_found else "missing"
    ms1_apex_rt = peak.rt if peak is not None else None
    best_seed = select_best_seed(group.seeds, ms1_apex_rt=ms1_apex_rt)
    priority, reason = assign_review_priority(
        group,
        ms1_peak_found=ms1_peak_found,
        ms1_apex_rt=ms1_apex_rt,
        ms1_trace_quality=ms1_trace_quality,
    )
    return DiscoveryCandidate.from_values(
        raw_file=group.raw_file,
        sample_stem=group.sample_stem,
        best_seed=best_seed,
        seed_scan_ids=group.seed_scan_ids,
        seed_event_count=group.seed_count,
        neutral_loss_tag=group.neutral_loss_tag,
        configured_neutral_loss_da=group.configured_neutral_loss_da,
        observed_neutral_loss_da=group.observed_neutral_loss_da,
        neutral_loss_mass_error_ppm=group.neutral_loss_mass_error_ppm,
        precursor_mz=group.precursor_mz,
        product_mz=group.product_mz,
        best_seed_rt=best_seed.rt,
        rt_seed_min=group.rt_seed_min,
        rt_seed_max=group.rt_seed_max,
        ms1_search_rt_min=search_rt_min,
        ms1_search_rt_max=search_rt_max,
        ms1_peak_found=ms1_peak_found,
        ms1_apex_rt=ms1_apex_rt,
        ms1_seed_delta_min=(
            ms1_apex_rt - best_seed.rt if ms1_apex_rt is not None else None
        ),
        ms1_peak_rt_start=peak.peak_start if peak is not None else None,
        ms1_peak_rt_end=peak.peak_end if peak is not None else None,
        ms1_height=peak.intensity if peak is not None else None,
        ms1_area=peak.area if peak is not None else None,
        ms1_trace_quality=ms1_trace_quality,
        ms2_product_max_intensity=max(seed.product_intensity for seed in group.seeds),
        review_priority=priority,
        reason=reason,
    )


def _trace_quality_label(detection: object) -> str:
    return "clean" if getattr(detection, "status", None) == "OK" else "missing"
```

- [ ] **Step 5: Run MS1 backfill tests green**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_ms1_backfill.py tests/test_discovery_grouping.py tests/test_discovery_ms2_seeds.py tests/test_discovery_csv.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 4**

Run:

```powershell
git add xic_extractor/discovery/priority.py xic_extractor/discovery/ms1_backfill.py tests/test_discovery_ms1_backfill.py
git commit -m "feat: backfill discovery candidates with ms1 xic"
```

---

## Task 5: Review-First CSV Writer

**Files:**
- Create: `xic_extractor/discovery/csv_writer.py`
- Modify: `tests/test_discovery_csv.py`

- [ ] **Step 1: Add failing CSV writer tests**

Append to `tests/test_discovery_csv.py`:

```python
import csv

from xic_extractor.discovery.csv_writer import write_discovery_candidates_csv


def _candidate(priority: str, scan: int, *, area: float | None, seeds: int):
    seed = DiscoverySeed(
        raw_file=Path("TumorBC2312_DNA.raw"),
        sample_stem="TumorBC2312_DNA",
        scan_number=scan,
        rt=8.49,
        precursor_mz=359.045,
        product_mz=242.997,
        product_intensity=50000.0 + scan,
        neutral_loss_tag="DNA_dR",
        configured_neutral_loss_da=116.0474,
        observed_neutral_loss_da=116.0479,
        observed_loss_error_ppm=4.3,
    )
    return DiscoveryCandidate.from_values(
        raw_file=Path("TumorBC2312_DNA.raw"),
        sample_stem="TumorBC2312_DNA",
        best_seed=seed,
        seed_scan_ids=(scan,),
        seed_event_count=seeds,
        neutral_loss_tag="DNA_dR",
        configured_neutral_loss_da=116.0474,
        observed_neutral_loss_da=116.0479,
        neutral_loss_mass_error_ppm=4.3,
        precursor_mz=359.045,
        product_mz=242.997,
        best_seed_rt=8.49,
        rt_seed_min=8.49,
        rt_seed_max=8.49,
        ms1_search_rt_min=8.29,
        ms1_search_rt_max=8.69,
        ms1_peak_found=area is not None,
        ms1_apex_rt=8.50 if area is not None else None,
        ms1_seed_delta_min=0.01 if area is not None else None,
        ms1_peak_rt_start=8.42 if area is not None else None,
        ms1_peak_rt_end=8.58 if area is not None else None,
        ms1_height=120000.0 if area is not None else None,
        ms1_area=area,
        ms1_trace_quality="clean" if area is not None else "missing",
        ms2_product_max_intensity=50000.0 + scan,
        review_priority=priority,
        reason="single MS2 NL seed; MS1 peak found",
    )


def test_write_discovery_candidates_csv_uses_review_first_header_and_sorting(tmp_path: Path) -> None:
    output = tmp_path / "discovery_candidates.csv"
    write_discovery_candidates_csv(
        output,
        [
            _candidate("LOW", 1, area=None, seeds=1),
            _candidate("HIGH", 3, area=300.0, seeds=2),
            _candidate("MEDIUM", 2, area=200.0, seeds=1),
        ],
    )

    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert rows[0]["review_priority"] == "HIGH"
    assert rows[1]["review_priority"] == "MEDIUM"
    assert rows[2]["review_priority"] == "LOW"
    assert list(rows[0].keys())[:12] == list(DISCOVERY_REVIEW_COLUMNS)
    assert rows[0]["ms1_area"] == "300.00"
    assert rows[2]["ms1_area"] == ""
    assert rows[0]["seed_scan_ids"] == "3"


def test_write_discovery_candidates_csv_writes_header_for_empty_results(tmp_path: Path) -> None:
    output = tmp_path / "discovery_candidates.csv"
    write_discovery_candidates_csv(output, [])

    with output.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rest = list(reader)

    assert header[:12] == list(DISCOVERY_REVIEW_COLUMNS)
    assert rest == []
```

- [ ] **Step 2: Run the red test**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_csv.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `xic_extractor.discovery.csv_writer`.

- [ ] **Step 3: Implement CSV writer**

Create `xic_extractor/discovery/csv_writer.py`:

```python
from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from xic_extractor.discovery.models import (
    DISCOVERY_CANDIDATE_COLUMNS,
    DiscoveryCandidate,
)

_PRIORITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def write_discovery_candidates_csv(
    path: Path,
    candidates: Iterable[DiscoveryCandidate],
) -> Path:
    ordered = sorted(candidates, key=_sort_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DISCOVERY_CANDIDATE_COLUMNS)
        writer.writeheader()
        for candidate in ordered:
            writer.writerow(_row(candidate))
    return path


def _sort_key(candidate: DiscoveryCandidate) -> tuple[int, int, float, float, float]:
    return (
        _PRIORITY_RANK[candidate.review_priority],
        -candidate.seed_event_count,
        -candidate.ms2_product_max_intensity,
        -(candidate.ms1_area or 0.0),
        candidate.best_seed_rt,
    )


def _row(candidate: DiscoveryCandidate) -> dict[str, str]:
    return {
        "review_priority": candidate.review_priority,
        "candidate_id": candidate.candidate_id,
        "precursor_mz": _fmt(candidate.precursor_mz, 6),
        "product_mz": _fmt(candidate.product_mz, 6),
        "observed_neutral_loss_da": _fmt(candidate.observed_neutral_loss_da, 6),
        "best_seed_rt": _fmt(candidate.best_seed_rt, 4),
        "seed_event_count": str(candidate.seed_event_count),
        "ms1_peak_found": "TRUE" if candidate.ms1_peak_found else "FALSE",
        "ms1_apex_rt": _fmt_optional(candidate.ms1_apex_rt, 4),
        "ms1_area": _fmt_optional(candidate.ms1_area, 2),
        "ms2_product_max_intensity": _fmt(candidate.ms2_product_max_intensity, 2),
        "reason": candidate.reason,
        "raw_file": candidate.raw_file.name,
        "sample_stem": candidate.sample_stem,
        "best_ms2_scan_id": str(candidate.best_ms2_scan_id),
        "seed_scan_ids": ";".join(str(scan) for scan in candidate.seed_scan_ids),
        "neutral_loss_tag": candidate.neutral_loss_tag,
        "configured_neutral_loss_da": _fmt(candidate.configured_neutral_loss_da, 6),
        "neutral_loss_mass_error_ppm": _fmt(candidate.neutral_loss_mass_error_ppm, 3),
        "rt_seed_min": _fmt(candidate.rt_seed_min, 4),
        "rt_seed_max": _fmt(candidate.rt_seed_max, 4),
        "ms1_search_rt_min": _fmt(candidate.ms1_search_rt_min, 4),
        "ms1_search_rt_max": _fmt(candidate.ms1_search_rt_max, 4),
        "ms1_seed_delta_min": _fmt_optional(candidate.ms1_seed_delta_min, 4),
        "ms1_peak_rt_start": _fmt_optional(candidate.ms1_peak_rt_start, 4),
        "ms1_peak_rt_end": _fmt_optional(candidate.ms1_peak_rt_end, 4),
        "ms1_height": _fmt_optional(candidate.ms1_height, 2),
        "ms1_trace_quality": candidate.ms1_trace_quality,
    }


def _fmt(value: float, digits: int) -> str:
    return f"{value:.{digits}f}"


def _fmt_optional(value: float | None, digits: int) -> str:
    if value is None:
        return ""
    return _fmt(value, digits)
```

- [ ] **Step 4: Run CSV tests green**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_csv.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 5**

Run:

```powershell
git add xic_extractor/discovery/csv_writer.py tests/test_discovery_csv.py
git commit -m "feat: write discovery candidate csv"
```

---

## Task 6: Single-RAW Discovery Pipeline

**Files:**
- Create: `xic_extractor/discovery/pipeline.py`
- Test: `tests/test_discovery_pipeline.py`

- [ ] **Step 1: Write failing fake end-to-end pipeline tests**

Create `tests/test_discovery_pipeline.py`:

```python
from pathlib import Path

import numpy as np

from xic_extractor.config import ExtractionConfig
from xic_extractor.discovery.models import DiscoverySettings, NeutralLossProfile
from xic_extractor.discovery.pipeline import run_discovery
from xic_extractor.raw_reader import Ms2Scan, Ms2ScanEvent


class FakeRaw:
    def __init__(self) -> None:
        self.rt = np.linspace(8.0, 9.0, 101)
        self.intensity = 1000.0 * np.exp(-((self.rt - 8.50) ** 2) / (2 * 0.04**2))

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def iter_ms2_scans(self, rt_min: float, rt_max: float):
        precursor = 359.045
        product = precursor - 116.0474
        for scan, rt in [(6095, 8.45), (6096, 8.52)]:
            yield Ms2ScanEvent(
                scan=Ms2Scan(
                    scan_number=scan,
                    rt=rt,
                    precursor_mz=precursor,
                    masses=np.array([product]),
                    intensities=np.array([50000.0 + scan]),
                    base_peak=50000.0 + scan,
                ),
                parse_error=None,
                scan_number=scan,
            )

    def extract_xic(self, mz: float, rt_min: float, rt_max: float, ppm_tol: float):
        mask = (self.rt >= rt_min) & (self.rt <= rt_max)
        return self.rt[mask], self.intensity[mask]


def _config(tmp_path: Path) -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=tmp_path,
        dll_dir=tmp_path,
        output_csv=tmp_path / "xic_results.csv",
        diagnostics_csv=tmp_path / "xic_diagnostics.csv",
        smooth_window=11,
        smooth_polyorder=3,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.10,
        ms2_precursor_tol_da=1.6,
        nl_min_intensity_ratio=0.01,
        resolver_mode="local_minimum",
    )


def test_run_discovery_writes_single_candidate_csv(tmp_path: Path) -> None:
    raw_path = tmp_path / "TumorBC2312_DNA.raw"
    raw_path.write_text("", encoding="utf-8")

    output_path = run_discovery(
        raw_path,
        output_dir=tmp_path / "out",
        settings=DiscoverySettings(
            neutral_loss_profile=NeutralLossProfile("DNA_dR", 116.0474),
            rt_min=0.0,
            rt_max=30.0,
        ),
        peak_config=_config(tmp_path),
        raw_opener=lambda _path, _dll_dir: FakeRaw(),
    )

    text = output_path.read_text(encoding="utf-8")
    assert output_path.name == "discovery_candidates.csv"
    assert text.count("\n") == 2
    assert "HIGH,TumorBC2312_DNA#6096" in text
    assert "strong MS2 NL seed group; MS1 peak found near seed RT" in text


def test_run_discovery_writes_header_when_no_strict_seeds(tmp_path: Path) -> None:
    raw_path = tmp_path / "NoSeeds.raw"
    raw_path.write_text("", encoding="utf-8")

    class NoSeedRaw(FakeRaw):
        def iter_ms2_scans(self, rt_min: float, rt_max: float):
            return iter(())

    output_path = run_discovery(
        raw_path,
        output_dir=tmp_path / "out",
        settings=DiscoverySettings(
            neutral_loss_profile=NeutralLossProfile("DNA_dR", 116.0474),
        ),
        peak_config=_config(tmp_path),
        raw_opener=lambda _path, _dll_dir: NoSeedRaw(),
    )

    assert output_path.read_text(encoding="utf-8").count("\n") == 1
```

- [ ] **Step 2: Run the red test**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_pipeline.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `xic_extractor.discovery.pipeline`.

- [ ] **Step 3: Implement pipeline orchestration**

Create `xic_extractor/discovery/pipeline.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import ContextManager, Protocol, cast

from xic_extractor.config import ExtractionConfig
from xic_extractor.discovery.csv_writer import write_discovery_candidates_csv
from xic_extractor.discovery.grouping import group_discovery_seeds
from xic_extractor.discovery.models import DiscoverySettings
from xic_extractor.discovery.ms1_backfill import backfill_ms1_candidates
from xic_extractor.discovery.ms1_backfill import MS1XicSource
from xic_extractor.discovery.ms2_seeds import collect_strict_nl_seeds
from xic_extractor.discovery.ms2_seeds import MS2ScanSource
from xic_extractor.raw_reader import open_raw


class DiscoveryRawHandle(MS1XicSource, MS2ScanSource, Protocol):
    ...


RawOpener = Callable[[Path, Path], ContextManager[DiscoveryRawHandle]]


def run_discovery(
    raw_path: Path,
    *,
    output_dir: Path,
    settings: DiscoverySettings,
    peak_config: ExtractionConfig,
    raw_opener: RawOpener | None = None,
) -> Path:
    output_path = output_dir / "discovery_candidates.csv"
    opener = raw_opener or cast(RawOpener, open_raw)
    with opener(raw_path, peak_config.dll_dir) as raw:
        seeds = collect_strict_nl_seeds(raw, raw_file=raw_path, settings=settings)
        groups = group_discovery_seeds(seeds, settings=settings)
        candidates = backfill_ms1_candidates(
            raw,
            groups,
            settings=settings,
            peak_config=peak_config,
        )
    return write_discovery_candidates_csv(output_path, candidates)
```

- [ ] **Step 4: Run pipeline and discovery tests green**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_pipeline.py tests/test_discovery_ms1_backfill.py tests/test_discovery_grouping.py tests/test_discovery_ms2_seeds.py tests/test_discovery_csv.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 6**

Run:

```powershell
git add xic_extractor/discovery/pipeline.py tests/test_discovery_pipeline.py
git commit -m "feat: run single raw discovery pipeline"
```

---

## Task 7: Discovery CLI

**Files:**
- Create: `scripts/run_discovery.py`
- Modify: `pyproject.toml`
- Test: `tests/test_run_discovery.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_run_discovery.py`:

```python
from pathlib import Path

from scripts import run_discovery


def test_run_discovery_cli_passes_single_raw_settings(monkeypatch, tmp_path: Path, capsys) -> None:
    raw_path = tmp_path / "TumorBC2312_DNA.raw"
    raw_path.write_text("", encoding="utf-8")
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    captured = {}

    def _fake_run_discovery(raw_path_arg, *, output_dir, settings, peak_config):
        captured["raw_path"] = raw_path_arg
        captured["output_dir"] = output_dir
        captured["settings"] = settings
        captured["peak_config"] = peak_config
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / "discovery_candidates.csv"
        output.write_text("review_priority\n", encoding="utf-8")
        return output

    monkeypatch.setattr(run_discovery, "run_discovery", _fake_run_discovery)

    code = run_discovery.main(
        [
            "--raw",
            str(raw_path),
            "--dll-dir",
            str(dll_dir),
            "--output-dir",
            str(tmp_path / "out"),
            "--neutral-loss-da",
            "116.0474",
            "--neutral-loss-tag",
            "DNA_dR",
            "--resolver-mode",
            "local_minimum",
        ]
    )

    assert code == 0
    assert captured["raw_path"] == raw_path
    assert captured["settings"].neutral_loss_profile.tag == "DNA_dR"
    assert captured["settings"].neutral_loss_profile.neutral_loss_da == 116.0474
    assert captured["peak_config"].resolver_mode == "local_minimum"
    assert "discovery_candidates.csv" in capsys.readouterr().out


def test_run_discovery_cli_rejects_missing_raw(tmp_path: Path, capsys) -> None:
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()

    code = run_discovery.main(
        [
            "--raw",
            str(tmp_path / "missing.raw"),
            "--dll-dir",
            str(dll_dir),
        ]
    )

    assert code == 2
    assert "raw file does not exist" in capsys.readouterr().err
```

- [ ] **Step 2: Run the red test**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_run_discovery.py -v
```

Expected: FAIL because `scripts.run_discovery` does not exist.

- [ ] **Step 3: Implement CLI and peak config builder**

Create `scripts/run_discovery.py`:

```python
import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from xic_extractor.config import ExtractionConfig
from xic_extractor.discovery.models import DiscoverySettings, NeutralLossProfile
from xic_extractor.discovery.pipeline import run_discovery
from xic_extractor.raw_reader import RawReaderError
from xic_extractor.settings_schema import CANONICAL_SETTINGS_DEFAULTS


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    raw_path = args.raw.resolve()
    dll_dir = args.dll_dir.resolve()
    output_dir = args.output_dir.resolve()
    if not raw_path.is_file():
        print(f"{raw_path}: raw file does not exist", file=sys.stderr)
        return 2
    if not dll_dir.is_dir():
        print(f"{dll_dir}: dll directory does not exist", file=sys.stderr)
        return 2

    settings = DiscoverySettings(
        neutral_loss_profile=NeutralLossProfile(
            args.neutral_loss_tag,
            args.neutral_loss_da,
        ),
        nl_tolerance_ppm=args.nl_tolerance_ppm,
        precursor_mz_tolerance_ppm=args.precursor_mz_tolerance_ppm,
        product_mz_tolerance_ppm=args.product_mz_tolerance_ppm,
        product_search_ppm=args.product_search_ppm,
        nl_min_intensity_ratio=args.nl_min_intensity_ratio,
        seed_rt_gap_min=args.seed_rt_gap_min,
        ms1_search_padding_min=args.ms1_search_padding_min,
        rt_min=args.rt_min,
        rt_max=args.rt_max,
        resolver_mode=args.resolver_mode,
    )
    peak_config = _peak_config(raw_path, dll_dir, output_dir, settings)
    try:
        output_path = run_discovery(
            raw_path,
            output_dir=output_dir,
            settings=settings,
            peak_config=peak_config,
        )
    except RawReaderError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Discovery CSV: {output_path}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run single-RAW strict MS2 neutral-loss discovery."
    )
    parser.add_argument("--raw", type=Path, required=True, help="Thermo RAW file.")
    parser.add_argument(
        "--dll-dir",
        type=Path,
        required=True,
        help="Directory containing Thermo RawFileReader DLLs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output") / "discovery",
        help="Directory for discovery_candidates.csv.",
    )
    parser.add_argument("--neutral-loss-tag", default="DNA_dR")
    parser.add_argument("--neutral-loss-da", type=_positive_float, default=116.0474)
    parser.add_argument("--nl-tolerance-ppm", type=_positive_float, default=20.0)
    parser.add_argument(
        "--precursor-mz-tolerance-ppm",
        type=_positive_float,
        default=20.0,
    )
    parser.add_argument(
        "--product-mz-tolerance-ppm",
        type=_positive_float,
        default=20.0,
    )
    parser.add_argument("--product-search-ppm", type=_positive_float, default=50.0)
    parser.add_argument("--nl-min-intensity-ratio", type=_positive_float, default=0.01)
    parser.add_argument("--seed-rt-gap-min", type=_positive_float, default=0.20)
    parser.add_argument("--ms1-search-padding-min", type=_positive_float, default=0.20)
    parser.add_argument("--rt-min", type=float, default=0.0)
    parser.add_argument("--rt-max", type=float, default=999.0)
    parser.add_argument(
        "--resolver-mode",
        choices=("legacy_savgol", "local_minimum"),
        default="local_minimum",
    )
    return parser.parse_args(argv)


def _peak_config(
    raw_path: Path,
    dll_dir: Path,
    output_dir: Path,
    settings: DiscoverySettings,
) -> ExtractionConfig:
    defaults = CANONICAL_SETTINGS_DEFAULTS
    return ExtractionConfig(
        data_dir=raw_path.parent,
        dll_dir=dll_dir,
        output_csv=output_dir / "xic_results.csv",
        diagnostics_csv=output_dir / "xic_diagnostics.csv",
        smooth_window=int(defaults["smooth_window"]),
        smooth_polyorder=int(defaults["smooth_polyorder"]),
        peak_rel_height=float(defaults["peak_rel_height"]),
        peak_min_prominence_ratio=float(defaults["peak_min_prominence_ratio"]),
        ms2_precursor_tol_da=float(defaults["ms2_precursor_tol_da"]),
        nl_min_intensity_ratio=settings.nl_min_intensity_ratio,
        resolver_mode=settings.resolver_mode,
        resolver_chrom_threshold=float(defaults["resolver_chrom_threshold"]),
        resolver_min_search_range_min=float(defaults["resolver_min_search_range_min"]),
        resolver_min_relative_height=float(defaults["resolver_min_relative_height"]),
        resolver_min_absolute_height=float(defaults["resolver_min_absolute_height"]),
        resolver_min_ratio_top_edge=float(defaults["resolver_min_ratio_top_edge"]),
        resolver_peak_duration_min=float(defaults["resolver_peak_duration_min"]),
        resolver_peak_duration_max=float(defaults["resolver_peak_duration_max"]),
        resolver_min_scans=int(defaults["resolver_min_scans"]),
    )


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0.0:
        raise argparse.ArgumentTypeError("value must be > 0")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
```

Modify `pyproject.toml`:

```toml
[project.scripts]
xic-extractor = "gui.main:main"
xic-extractor-cli = "scripts.run_extraction:main"
xic-discovery-cli = "scripts.run_discovery:main"
```

- [ ] **Step 4: Run CLI tests green**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_run_discovery.py tests/test_discovery_pipeline.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 7**

Run:

```powershell
git add scripts/run_discovery.py pyproject.toml tests/test_run_discovery.py
git commit -m "feat: add discovery cli"
```

---

## Task 8: Contract Checks And Real-Data Smoke Instructions

**Files:**
- Modify: `docs/superpowers/specs/2026-05-09-untargeted-discovery-v1-spec.md`
- Test: existing discovery tests plus lint/typecheck

- [ ] **Step 1: Add implementation contract notes to the spec**

Append this section to `docs/superpowers/specs/2026-05-09-untargeted-discovery-v1-spec.md` before `## 12. Acceptance Criteria For This Spec`:

```markdown
## Implementation Notes

The first implementation should expose `xic-discovery-cli` as the experimental CLI entry point.

The default real-data smoke command for the FH comparison sample is:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-discovery-cli --raw "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation\TumorBC2312_DNA.raw" --dll-dir "C:\Xcalibur\system\programs" --output-dir "output\discovery\TumorBC2312_DNA" --neutral-loss-tag DNA_dR --neutral-loss-da 116.0474 --resolver-mode local_minimum
```

If the exact RAW path is unavailable in the local machine, use the known FH Program2 raw counterpart and record the chosen path in the PR summary.

Expected smoke checks:

- `discovery_candidates.csv` exists.
- Header starts with the fixed 12 review columns.
- Rows are candidate-level, not one row per MS2 scan.
- Candidate ids map back to Xcalibur scan ids.
- At least one candidate has non-empty `ms1_area` when the sample contains valid MS1 signal.
- Targeted workbook tests remain unchanged.
```

- [ ] **Step 2: Run all discovery and targeted-adjacent tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_ms2_seeds.py tests/test_discovery_grouping.py tests/test_discovery_ms1_backfill.py tests/test_discovery_csv.py tests/test_discovery_pipeline.py tests/test_run_discovery.py tests/test_signal_processing.py tests/test_neutral_loss.py -v
```

Expected: PASS.

- [ ] **Step 3: Run static checks**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests scripts
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

Expected: PASS.

- [ ] **Step 4: Run optional real-data smoke**

Use the known FH single-sample counterpart. If the exact raw is available:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-discovery-cli --raw "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation\TumorBC2312_DNA.raw" --dll-dir "C:\Xcalibur\system\programs" --output-dir "output\discovery\TumorBC2312_DNA" --neutral-loss-tag DNA_dR --neutral-loss-da 116.0474 --resolver-mode local_minimum
```

If that path is not available, search for the raw:

```powershell
Get-ChildItem -Path "C:\Xcalibur\data" -Recurse -Filter "*TumorBC2312_DNA*.raw" -ErrorAction SilentlyContinue
```

Expected:

- The command exits `0`.
- The output path printed is `output\discovery\TumorBC2312_DNA\discovery_candidates.csv`.
- The CSV has one header row and candidate rows if strict NL seeds exist.
- The first 12 headers match `DISCOVERY_REVIEW_COLUMNS`.
- Repeated FH event rows collapse into fewer candidate rows when multiple strict seed events are near the same RT.

- [ ] **Step 5: Commit Task 8**

Run:

```powershell
git add docs/superpowers/specs/2026-05-09-untargeted-discovery-v1-spec.md
git commit -m "docs: document discovery smoke validation"
```

---

## Final Verification

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_ms2_seeds.py tests/test_discovery_grouping.py tests/test_discovery_ms1_backfill.py tests/test_discovery_csv.py tests/test_discovery_pipeline.py tests/test_run_discovery.py -v
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_signal_processing.py tests/test_neutral_loss.py tests/test_run_extraction.py -v
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests scripts
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

Expected:

- All tests pass.
- Ruff passes.
- Mypy passes.
- `git status --short` shows only intended files before final commit.

Do not run 8-raw or 85-raw validation for this PR. This workflow is single-RAW discovery and does not alter targeted extraction.

---

## Spec Coverage Review

| Spec requirement | Implemented by |
|---|---|
| Single RAW only | Task 6 pipeline, Task 7 CLI `--raw`. |
| Strict MS2-first seeds | Task 2 seed scanner. |
| Conservative grouping | Task 3 grouping. |
| MS1 XIC apex/height/area | Task 4 MS1 backfill. |
| One default CSV | Task 5 writer and Task 6 pipeline. |
| Review-first first 12 columns | Task 1 constants and Task 5 writer tests. |
| Candidate id `<sample_stem>#<best_ms2_scan_id>` | Task 1 model and Task 3 representative seed. |
| No GUI / Excel / batch alignment | File structure and final verification scope. |
| Targeted behavior unchanged | Task 8 targeted-adjacent tests and no targeted module edits. |

## Execution Notes

- Use a fresh implementation worktree for this plan. Do not implement directly in `master`.
- Keep one commit per task.
- If implementing Task 7 reveals the raw path or DLL path defaults are wrong for the user's machine, do not hardcode local paths. Keep paths CLI arguments and record the working command in the PR summary.
- If real-data smoke produces too many candidate rows, do not tune thresholds inside the implementation PR without a new plan. Record the row count and examples; threshold calibration is a separate follow-up.
