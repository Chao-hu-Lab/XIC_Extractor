# Discovery Evidence Config Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move discovery evidence weights and thresholds into a focused config module and thread them through scoring without changing default scoring behavior.

**Architecture:** `evidence_score.py` keeps scoring logic. New `evidence_config.py` owns frozen weights, thresholds, and the default profile. `DiscoverySettings` carries an evidence config object so pipeline/scoring integration can be tuned later without exposing raw weights to normal users.

**Tech Stack:** Python dataclasses, Literal types, pytest, existing `xic_extractor.discovery` modules.

---

## File Structure Map

- Create `xic_extractor/discovery/evidence_config.py`
  - `DiscoveryEvidenceWeights`
  - `DiscoveryEvidenceThresholds`
  - `DiscoveryEvidenceProfile`
  - `DEFAULT_EVIDENCE_PROFILE`
- Modify `xic_extractor/discovery/models.py`
  - Add `evidence_profile` to `DiscoverySettings`.
- Modify `xic_extractor/discovery/evidence_score.py`
  - Accept `settings: DiscoverySettings | None = None`.
  - Read weights/thresholds from settings or default profile.
- Modify `xic_extractor/discovery/feature_family.py`
  - `assign_feature_families(..., settings=None)` passes settings into scoring.
- Modify `xic_extractor/discovery/__init__.py`
  - Re-export config types.
- Tests:
  - `tests/test_discovery_evidence.py`
  - `tests/test_discovery_feature_family.py`
  - `tests/test_discovery_pipeline.py`

## User Surface Decision

Do not expose individual weight fields to normal users.

This plan builds a developer-facing foundation. Future user-facing config should be profile-based:

```text
loose
default
strict
```

Only `default` is fully defined in this plan. `loose` and `strict` require calibration and should not be invented without real-data evidence.

## Task 1: Create Evidence Config Module

**Files:**
- Create: `xic_extractor/discovery/evidence_config.py`
- Create or modify: `tests/test_discovery_evidence.py`

- [ ] **Step 1: Write the failing tests**

Add tests that verify:

- `DiscoveryEvidenceWeights()` is frozen and hashable.
- `DiscoveryEvidenceThresholds()` is frozen and hashable.
- `DEFAULT_EVIDENCE_PROFILE.name == "default"`.
- Default values match current `evidence_score.py` magic numbers.

- [ ] **Step 2: Run the red tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_evidence.py -v
```

Expected: FAIL because `evidence_config.py` does not exist.

- [ ] **Step 3: Implement config dataclasses**

Create `evidence_config.py` with frozen dataclasses and these exact field names:

```python
from dataclasses import dataclass
from typing import Literal

DiscoveryEvidenceProfileName = Literal["default"]


@dataclass(frozen=True)
class DiscoveryEvidenceWeights:
    ms1_peak_present: int = 25
    ms1_peak_absent: int = 5
    seed_event_per: int = 8
    seed_event_max: int = 25
    rt_aligned: int = 15
    rt_near: int = 10
    rt_shifted: int = 5
    product_intensity_high: int = 10
    product_intensity_med: int = 5
    area_high: int = 10
    area_med: int = 5
    scan_support_high: int = 5
    scan_support_low: int = -10
    legacy_trace_quality_high: int = 5
    legacy_trace_quality_low: int = -10
    superfamily_representative: int = 5
    superfamily_member: int = -5


@dataclass(frozen=True)
class DiscoveryEvidenceThresholds:
    rt_aligned_max_min: float = 0.05
    rt_near_max_min: float = 0.20
    rt_shifted_max_min: float = 0.40
    product_intensity_high_min: float = 100_000.0
    product_intensity_med_min: float = 10_000.0
    area_high_min: float = 1_000_000.0
    area_med_min: float = 100_000.0
    ms1_support_strong_area_min: float = 10_000_000.0
    ms1_support_moderate_area_min: float = 1_000_000.0
    scan_support_target: int = 10
    scan_support_high_score_min: float = 0.8
    scan_support_low_score_max: float = 0.2


@dataclass(frozen=True)
class DiscoveryEvidenceProfile:
    name: DiscoveryEvidenceProfileName
    weights: DiscoveryEvidenceWeights
    thresholds: DiscoveryEvidenceThresholds


DEFAULT_EVIDENCE_PROFILE = DiscoveryEvidenceProfile(
    name="default",
    weights=DiscoveryEvidenceWeights(),
    thresholds=DiscoveryEvidenceThresholds(),
)
```

The `scan_support_*` field names are part of the contract with Plan C.

- [ ] **Step 4: Run green tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_evidence.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/discovery/evidence_config.py tests/test_discovery_evidence.py
git commit -m "feat(discovery): add evidence config profile foundation"
```

## Task 2: Add Evidence Profile To Settings

**Files:**
- Modify: `xic_extractor/discovery/models.py`
- Modify: `tests/test_discovery_csv.py`

- [ ] **Step 1: Write the failing test**

Add a test that creates `DiscoverySettings(neutral_loss_profile=...)` and asserts:

- `settings.evidence_profile == DEFAULT_EVIDENCE_PROFILE`
- `settings.evidence_profile.weights` and `settings.evidence_profile.thresholds` are available.

- [ ] **Step 2: Run the red test**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_csv.py -v -k evidence_profile
```

Expected: FAIL because `DiscoverySettings` lacks `evidence_profile`.

- [ ] **Step 3: Implement settings field**

Import `DEFAULT_EVIDENCE_PROFILE` in `models.py` and add:

```python
evidence_profile: DiscoveryEvidenceProfile = DEFAULT_EVIDENCE_PROFILE
```

Keep this as a Python-only setting for now. Do not add CLI/GUI/config CSV keys in this plan.

- [ ] **Step 4: Run focused tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_csv.py tests/test_discovery_evidence.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/discovery/models.py tests/test_discovery_csv.py
git commit -m "feat(discovery): attach evidence profile to discovery settings"
```

## Task 3: Read Evidence Config In Scoring

**Files:**
- Modify: `xic_extractor/discovery/evidence_score.py`
- Modify: `tests/test_discovery_evidence.py`

- [ ] **Step 1: Write failing tests**

Add tests that verify:

- Default score for the existing representative fixture remains unchanged.
- Passing custom settings with changed weights changes only the expected score component.
- Classification helpers use thresholds from settings when provided.

- [ ] **Step 2: Run the red tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_evidence.py -v
```

Expected: FAIL because `score_discovery_evidence()` does not accept settings.

- [ ] **Step 3: Implement scoring pass-through**

Change signature:

```python
def score_discovery_evidence(
    candidate: DiscoveryCandidate,
    *,
    settings: DiscoverySettings | None = None,
) -> DiscoveryEvidence:
```

Use:

```python
profile = settings.evidence_profile if settings is not None else DEFAULT_EVIDENCE_PROFILE
weights = profile.weights
thresholds = profile.thresholds
```

Replace hardcoded values with `weights` and `thresholds`.

- [ ] **Step 4: Run focused tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_evidence.py tests/test_discovery_feature_family.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/discovery/evidence_score.py tests/test_discovery_evidence.py
git commit -m "refactor(discovery): score evidence from configured profile"
```

## Task 4: Thread Settings Through Feature Families

**Files:**
- Modify: `xic_extractor/discovery/feature_family.py`
- Modify: `xic_extractor/discovery/pipeline.py`
- Modify: `tests/test_discovery_feature_family.py`
- Modify: `tests/test_discovery_pipeline.py`

- [ ] **Step 1: Write failing integration test**

Add a test where:

- A custom evidence profile changes a clearly isolated score component.
- `run_discovery()` receives settings with that custom profile.
- The written full CSV contains the changed score.

- [ ] **Step 2: Run the red test**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_pipeline.py -v -k evidence_profile
```

Expected: FAIL because pipeline drops the settings before scoring.

- [ ] **Step 3: Implement settings threading**

Change:

```python
assign_feature_families(candidates, *, settings: DiscoverySettings | None = None)
```

and pass settings from pipeline:

```python
assign_feature_families(candidates, settings=settings)
```

- [ ] **Step 4: Run focused tests and type check**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_evidence.py tests/test_discovery_feature_family.py tests/test_discovery_pipeline.py -v
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/discovery/feature_family.py xic_extractor/discovery/pipeline.py tests/test_discovery_feature_family.py tests/test_discovery_pipeline.py
git commit -m "refactor(discovery): thread evidence profile through feature scoring"
```

## Final Validation

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_evidence.py tests/test_discovery_feature_family.py tests/test_discovery_pipeline.py tests/test_discovery_csv.py -v
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests scripts
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```
