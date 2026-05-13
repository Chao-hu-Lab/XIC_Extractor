# Untargeted Drift-Aware Owner Edge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve untargeted owner-family alignment by converting repeated same-sample signal into owner evidence and using injection-order drift as soft cross-sample edge evidence, without introducing targeted identity rules.

**Architecture:** Keep sample-local ownership, drift evidence, edge scoring, and output diagnostics as separate modules. Production family construction may consume only detected owner strong edges; targeted workbooks are read only by a drift adapter and validation tools, never by production identity logic.

**Tech Stack:** Python 3.10+, dataclasses, openpyxl, pytest, existing `AlignmentConfig`, existing owner-based alignment pipeline, existing Thermo RAW process backend, existing targeted GT audit diagnostics.

---

## Scope Locks

- Worktree: `C:\Users\user\Desktop\XIC_Extractor\.worktrees\untargeted-discovery-v1-implementation`
- Branch: `codex/untargeted-discovery-v1-implementation`
- Design spec: `docs/superpowers/specs/2026-05-13-untargeted-duplicate-drift-soft-edge-design.md`
- Known targeted issue kept out of scope: GitHub issue `#42`, targeted anchor mismatch tolerance around `5-hmdC` / `5-medC`.
- This is an untargeted method. Target labels are checkpoints and validation fixtures only.

## Baseline Artifacts

Implementation and validation must use these paths exactly:

- 8 RAW alignment baseline: `output\alignment\semantics_cleanup_8raw_20260511`
- 8 RAW trace cases: `output\alignment\semantics_cleanup_8raw_20260511\raw_trace_inspection`
- 85 RAW alignment baseline: `output\alignment\gt_audit_checkpoint_85raw_validation_20260512`
- Targeted 8 RAW workbook: `C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1151.xlsx`
- Targeted 85 RAW workbook: `C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1200.xlsx`
- Sample metadata: `C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\SampleInfo.xlsx`
- 8 RAW discovery index: `output\discovery\semantics_cleanup_8raw_20260511\discovery_batch_index.csv`
- 85 RAW discovery index: `output\discovery\tissue85_alignment_v1\discovery_batch_index.csv`
- 8 RAW directory: `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation`
- 85 RAW directory: `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R`
- Thermo DLL directory: `C:\Program Files (x86)\Thermo\Foundation`

If any baseline artifact is missing, stop validation and report the missing path. Do not substitute another run.

## File Structure

- Create: `xic_extractor/alignment/edge_scoring.py`
  - Owns typed edge evidence model, hard gate failure reasons, deterministic score rules, and `evaluate_owner_edge()`.
  - Domain-only module. It must not import openpyxl, CLI scripts, workbook writers, RAW reader, process backend, or GUI code.
- Create: `xic_extractor/alignment/drift_evidence.py`
  - Owns targeted ISTD drift adapter and scoring-safe `DriftEvidenceLookup`.
  - May import `openpyxl` and `xic_extractor.injection_rolling`.
  - Must not expose target analyte labels or ISTD labels through scoring payload dataclasses.
- Modify: `xic_extractor/alignment/owner_clustering.py`
  - Uses `evaluate_owner_edge()` instead of raw boolean `_compatible_owners()`.
  - Builds production groups only from `strong_edge` complete-link compatibility.
  - Collects edge evidence for debug/validation output.
- Modify: `xic_extractor/alignment/debug_writer.py`
  - Adds `write_owner_edge_evidence_tsv()`.
- Modify: `xic_extractor/alignment/output_levels.py`
  - Adds `owner_edge_evidence.tsv` to `debug` and `validation` output levels only.
- Modify: `xic_extractor/alignment/pipeline.py`
  - Accepts optional drift lookup.
  - Records `alignment.run_config` timing metadata including `raw_workers`.
  - Writes edge evidence TSV when requested by output level.
- Modify: `scripts/run_alignment.py`
  - Adds `--sample-info` and `--targeted-istd-workbook`.
  - Adds `--drift-local-window`; CLI default is `40` injections for sparse
    validation subsets, while the lower-level drift adapter keeps its
    `local_window=4` default for direct callers.
  - Builds drift lookup only when both paths are provided.
  - Preserves default no-drift behavior.
- Create: `tools/diagnostics/untargeted_alignment_guardrails.py`
  - Computes duplicate-only, zero-present, high-backfill-dependency, negative target m/z production count, and case1-4 assertions from alignment TSVs.
- Test: `tests/test_alignment_edge_scoring.py`
- Test: `tests/test_alignment_drift_evidence.py`
- Modify: `tests/test_alignment_owner_clustering.py`
- Modify: `tests/test_alignment_debug_writer.py`
- Modify: `tests/test_alignment_output_levels.py`
- Modify: `tests/test_alignment_pipeline.py`
- Modify: `tests/test_run_alignment.py`
- Create: `tests/test_untargeted_alignment_guardrails.py`
- Modify: `tests/test_alignment_boundaries.py`

## Edge Scoring Contract

Hard-gate failure reasons are exact strings:

```python
HardGateFailureReason = Literal[
    "same_sample",
    "neutral_loss_tag_mismatch",
    "precursor_mz_out_of_tolerance",
    "product_mz_out_of_tolerance",
    "observed_loss_out_of_tolerance",
    "non_detected_owner",
    "ambiguous_owner",
    "identity_conflict",
    "backfill_bridge",
]
```

Edge decisions are exact strings:

```python
EdgeDecision = Literal["strong_edge", "weak_edge", "blocked_edge"]
```

Soft evidence enums are exact strings:

```python
DriftPriorSource = Literal["targeted_istd_trend", "batch_istd_trend", "none"]
OwnerQuality = Literal["clean", "weak", "tail_supported", "ambiguous_nearby"]
SeedSupportLevel = Literal["strong", "moderate", "weak"]
DuplicateContext = Literal["none", "same_owner_events", "tail_assignment"]
```

Numeric rules for v1:

```text
strict RT threshold = AlignmentConfig.preferred_rt_sec
wide RT threshold = AlignmentConfig.max_rt_sec
drift-corrected close = rt_drift_corrected_delta_sec <= preferred_rt_sec
raw close = rt_raw_delta_sec <= preferred_rt_sec
drift contradictory = rt_drift_corrected_delta_sec > rt_raw_delta_sec + 10.0
strong seed = evidence_score >= anchor_min_evidence_score and seed_event_count >= anchor_min_seed_events
moderate seed = evidence_score >= 40 and seed_event_count >= 1
weak seed = anything below moderate
```

Score weights after hard gates pass:

```text
+30 if raw RT delta <= preferred_rt_sec
+10 if preferred_rt_sec < raw RT delta <= max_rt_sec
+35 if drift-corrected RT delta <= preferred_rt_sec
+10 if preferred_rt_sec < drift-corrected RT delta <= max_rt_sec
+10 if drift-corrected RT improves raw RT delta by at least 10 sec
-20 if drift-corrected RT delta is contradictory
+15 for strong seed support
+5 for moderate seed support
-30 for weak seed support
+10 for clean owner quality
+5 for tail-supported owner quality
-30 for weak owner quality
-20 for ambiguous-nearby owner quality
+5 for same-owner duplicate context
+5 for tail-assignment duplicate context
```

Decision rules:

```text
hard gate fail -> blocked_edge
edge_depends_on_backfill -> blocked_edge with backfill_bridge
identity_conflict owner -> blocked_edge
no drift prior and raw RT delta > preferred_rt_sec -> weak_edge
drift prior exists and drift is contradictory -> weak_edge
drift prior exists, drift-corrected close, owner quality not weak or ambiguous-nearby, seed support not weak, score >= 60 -> strong_edge
no drift prior, raw close, owner quality not weak or ambiguous-nearby, seed support not weak, score >= 55 -> strong_edge
all other hard-pass cases -> weak_edge
```

## Edge Evidence Locator Fields

`owner_edge_evidence.tsv` must be usable without visual SVG inspection. The edge
model therefore extends the spec minimum fields with locator fields:

```text
left_sample_stem
right_sample_stem
neutral_loss_tag
left_precursor_mz
right_precursor_mz
left_rt_min
right_rt_min
```

These fields are untargeted owner properties. They are not target labels,
ISTD labels, class labels, or targeted confidence labels.

## Guardrail Metric Derivations

All guardrail metrics are computed per `feature_family_id`.

- `detected_count`: number of `alignment_cells.tsv` rows where `status == "detected"`.
- `rescued_count`: number of `alignment_cells.tsv` rows where `status == "rescued"`.
- `duplicate_assigned_count`: number of `alignment_cells.tsv` rows where `status == "duplicate_assigned"`.
- `ambiguous_ms1_owner_count`: number of `alignment_cells.tsv` rows where `status == "ambiguous_ms1_owner"`.
- `production_present_count`: `detected_count + rescued_count`.
- `zero_present_families`: count of feature families where `production_present_count == 0`.
- `duplicate_only_families`: count of feature families where `production_present_count == 0 and duplicate_assigned_count > 0`.
- `high_backfill_dependency_families`: count of feature families where `alignment_review.tsv.warning == "high_backfill_dependency"` or, when the review warning column is absent, `rescued_count > detected_count and rescued_count >= 2`.
- Negative `8-oxodG` accepted production families: count of feature families where `family_center_mz` is within `284.0989 +/- 20 ppm` and `production_present_count > 0`.

Case windows:

```text
case1_mz242_5medC_like: mz 242.114, ppm 20, RT 11.0 to 13.2 min
case2_mz296_dense_duplicate: mz 296.074, ppm 20, RT 19.2 to 20.0 min
case3_mz322_dense_duplicate: mz 322.143, ppm 20, RT 22.4 to 24.1 min
case4_mz251_anchor_shadow_duplicates: mz 251.084, ppm 20, RT 8.0 to 9.0 min
```

Case assertion fields:

- `production_family_count`: families in case window with `production_present_count > 0`.
- `owner_count`: sum of review `event_cluster_count` in case window.
- `event_count`: sum of review `event_member_count` in case window.
- `supporting_event_count`: `max(event_count - owner_count, 0)`.
- `preserved_split_or_ambiguous`: true when case2 candidate has either more than one family in the window or at least one `ambiguous_ms1_owner` cell.
- `strong_edge_count`: number of `owner_edge_evidence.tsv` rows where `decision == "strong_edge"` and both endpoint locator fields match the case window:
  - both `left_precursor_mz` and `right_precursor_mz` are within case m/z +/- ppm;
  - both `left_rt_min` and `right_rt_min` are within the case RT min/max.
- `case_assertion_summary.tsv`: tabular companion to `candidate_guardrails.json` with columns `case`, `production_family_count`, `owner_count`, `event_count`, `supporting_event_count`, `strong_edge_count`, `preserved_split_or_ambiguous`, `status`, and `reason`.

The `case_assertion_summary.tsv` file is the required case1-4 raw trace
inspection summary for this implementation pass. It replaces visual-only SVG
inspection with machine-checkable evidence derived from the same case windows
and edge locator fields. The baseline SVGs remain supporting visual context,
not pass/fail evidence.

## Validation Output Paths

Use these output directories when executing the real-data validation tasks:

- Candidate 8 RAW alignment: `output\alignment\drift_soft_edge_8raw_20260513`
- Candidate 8 RAW diagnostics: `output\diagnostics\drift_soft_edge_8raw_20260513`
- Candidate 85 RAW alignment: `output\alignment\drift_soft_edge_85raw_20260513`
- Candidate 85 RAW diagnostics: `output\diagnostics\drift_soft_edge_85raw_20260513`

---

### Task 1: Add Typed Owner Edge Scoring

**Files:**
- Create: `xic_extractor/alignment/edge_scoring.py`
- Create: `tests/test_alignment_edge_scoring.py`

- [ ] **Step 1: Write failing edge scoring tests**

Create `tests/test_alignment_edge_scoring.py`:

```python
from __future__ import annotations

import pytest

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.edge_scoring import evaluate_owner_edge
from xic_extractor.alignment.ownership_models import IdentityEvent, SampleLocalMS1Owner


def test_blocked_edge_reports_neutral_loss_reason() -> None:
    edge = evaluate_owner_edge(
        _owner("sample-a", "a", neutral_loss_tag="DNA_dR"),
        _owner("sample-b", "b", neutral_loss_tag="DNA_R"),
        config=AlignmentConfig(),
    )

    assert edge.decision == "blocked_edge"
    assert edge.failure_reason == "neutral_loss_tag_mismatch"
    assert edge.score == 0


@pytest.mark.parametrize(
    ("left_kwargs", "right_kwargs", "reason"),
    [
        ({"sample_stem": "sample-a"}, {"sample_stem": "sample-a"}, "same_sample"),
        ({"precursor_mz": 242.1136}, {"precursor_mz": 242.2000}, "precursor_mz_out_of_tolerance"),
        ({"product_mz": 126.0662}, {"product_mz": 126.1000}, "product_mz_out_of_tolerance"),
        ({"observed_loss": 116.0474}, {"observed_loss": 116.1000}, "observed_loss_out_of_tolerance"),
    ],
)
def test_blocked_edge_reports_each_numeric_and_sample_gate(
    left_kwargs,
    right_kwargs,
    reason,
) -> None:
    left_kwargs = dict(left_kwargs)
    right_kwargs = dict(right_kwargs)
    left_sample = left_kwargs.pop("sample_stem", "sample-a")
    right_sample = right_kwargs.pop("sample_stem", "sample-b")
    edge = evaluate_owner_edge(
        _owner(left_sample, "a", **left_kwargs),
        _owner(right_sample, "b", **right_kwargs),
        config=AlignmentConfig(max_ppm=50.0),
    )

    assert edge.decision == "blocked_edge"
    assert edge.failure_reason == reason


def test_non_detected_owner_blocks_edge() -> None:
    edge = evaluate_owner_edge(
        _owner("sample-a", "a"),
        _owner("sample-b", "b"),
        config=AlignmentConfig(),
        left_detected_owner=False,
    )

    assert edge.decision == "blocked_edge"
    assert edge.failure_reason == "non_detected_owner"


def test_ambiguous_owner_blocks_edge() -> None:
    edge = evaluate_owner_edge(
        _owner("sample-a", "a"),
        _owner("sample-b", "b"),
        config=AlignmentConfig(),
        right_ambiguous_owner=True,
    )

    assert edge.decision == "blocked_edge"
    assert edge.failure_reason == "ambiguous_owner"


def test_missing_drift_and_raw_over_strict_window_is_weak() -> None:
    edge = evaluate_owner_edge(
        _owner("sample-a", "a", apex_rt=10.0),
        _owner("sample-b", "b", apex_rt=11.2),
        config=AlignmentConfig(preferred_rt_sec=60.0, max_rt_sec=180.0),
    )

    assert edge.decision == "weak_edge"
    assert edge.failure_reason == ""
    assert edge.rt_raw_delta_sec == pytest.approx(72.0)
    assert edge.rt_drift_corrected_delta_sec is None
    assert edge.drift_prior_source == "none"


def test_drift_corrected_close_edge_is_strong_even_when_raw_exceeds_strict() -> None:
    edge = evaluate_owner_edge(
        _owner("sample-a", "a", apex_rt=10.0),
        _owner("sample-b", "b", apex_rt=11.2),
        config=AlignmentConfig(preferred_rt_sec=60.0, max_rt_sec=180.0),
        drift_lookup=_DriftLookup(
            deltas={"sample-a": 0.0, "sample-b": 0.25},
            orders={"sample-a": 1, "sample-b": 20},
            source="targeted_istd_trend",
        ),
    )

    assert edge.decision == "strong_edge"
    assert edge.rt_raw_delta_sec == pytest.approx(72.0)
    assert edge.rt_drift_corrected_delta_sec == pytest.approx(57.0)
    assert edge.injection_order_gap == 19
    assert edge.drift_prior_source == "targeted_istd_trend"
    assert edge.left_sample_stem == "sample-a"
    assert edge.right_sample_stem == "sample-b"
    assert edge.neutral_loss_tag == "DNA_dR"
    assert edge.left_precursor_mz == pytest.approx(242.1136)
    assert edge.right_precursor_mz == pytest.approx(242.1136)
    assert edge.left_rt_min == pytest.approx(10.0)
    assert edge.right_rt_min == pytest.approx(11.2)



def test_weak_seed_support_keeps_hard_pass_edge_weak() -> None:
    edge = evaluate_owner_edge(
        _owner("sample-a", "a", apex_rt=10.0, evidence_score=20, seed_event_count=1),
        _owner("sample-b", "b", apex_rt=10.2, evidence_score=20, seed_event_count=1),
        config=AlignmentConfig(),
    )

    assert edge.decision == "weak_edge"
    assert edge.seed_support_level == "weak"
    assert "weak seed" in edge.reason


def test_identity_conflict_blocks_edge() -> None:
    edge = evaluate_owner_edge(
        _owner("sample-a", "a", identity_conflict=True),
        _owner("sample-b", "b"),
        config=AlignmentConfig(),
    )

    assert edge.decision == "blocked_edge"
    assert edge.failure_reason == "identity_conflict"


def test_edge_depending_on_backfill_is_blocked() -> None:
    edge = evaluate_owner_edge(
        _owner("sample-a", "a"),
        _owner("sample-b", "b"),
        config=AlignmentConfig(),
        edge_depends_on_backfill=True,
    )

    assert edge.decision == "blocked_edge"
    assert edge.failure_reason == "backfill_bridge"


class _DriftLookup:
    def __init__(self, *, deltas: dict[str, float], orders: dict[str, int], source: str):
        self._deltas = deltas
        self._orders = orders
        self.source = source

    def sample_delta_min(self, sample_stem: str) -> float | None:
        return self._deltas.get(sample_stem)

    def injection_order(self, sample_stem: str) -> int | None:
        return self._orders.get(sample_stem)


def _owner(
    sample_stem: str,
    suffix: str,
    *,
    apex_rt: float = 10.0,
    neutral_loss_tag: str = "DNA_dR",
    precursor_mz: float = 242.1136,
    product_mz: float = 126.0662,
    observed_loss: float = 116.0474,
    evidence_score: int = 80,
    seed_event_count: int = 2,
    identity_conflict: bool = False,
) -> SampleLocalMS1Owner:
    event = IdentityEvent(
        candidate_id=f"{sample_stem}#{suffix}",
        sample_stem=sample_stem,
        raw_file=f"{sample_stem}.raw",
        neutral_loss_tag=neutral_loss_tag,
        precursor_mz=precursor_mz,
        product_mz=product_mz,
        observed_neutral_loss_da=observed_loss,
        seed_rt=apex_rt,
        evidence_score=evidence_score,
        seed_event_count=seed_event_count,
    )
    return SampleLocalMS1Owner(
        owner_id=f"OWN-{sample_stem}-{suffix}",
        sample_stem=sample_stem,
        raw_file=f"{sample_stem}.raw",
        precursor_mz=precursor_mz,
        owner_apex_rt=apex_rt,
        owner_peak_start_rt=apex_rt - 0.04,
        owner_peak_end_rt=apex_rt + 0.04,
        owner_area=1000.0,
        owner_height=100.0,
        primary_identity_event=event,
        supporting_events=(),
        identity_conflict=identity_conflict,
        assignment_reason="owner_exact_apex_match",
    )
```

- [ ] **Step 2: Run the new tests and verify failure**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_alignment_edge_scoring.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'xic_extractor.alignment.edge_scoring'`.

- [ ] **Step 3: Implement `edge_scoring.py`**

Create `xic_extractor/alignment/edge_scoring.py` with this public surface:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.ownership_models import SampleLocalMS1Owner

EdgeDecision = Literal["strong_edge", "weak_edge", "blocked_edge"]
HardGateFailureReason = Literal[
    "same_sample",
    "neutral_loss_tag_mismatch",
    "precursor_mz_out_of_tolerance",
    "product_mz_out_of_tolerance",
    "observed_loss_out_of_tolerance",
    "non_detected_owner",
    "ambiguous_owner",
    "identity_conflict",
    "backfill_bridge",
]
DriftPriorSource = Literal["targeted_istd_trend", "batch_istd_trend", "none"]
OwnerQuality = Literal["clean", "weak", "tail_supported", "ambiguous_nearby"]
SeedSupportLevel = Literal["strong", "moderate", "weak"]
DuplicateContext = Literal["none", "same_owner_events", "tail_assignment"]


class DriftLookupProtocol(Protocol):
    source: DriftPriorSource

    def sample_delta_min(self, sample_stem: str) -> float | None:
        ...

    def injection_order(self, sample_stem: str) -> int | None:
        ...


@dataclass(frozen=True)
class OwnerEdgeEvidence:
    left_owner_id: str
    right_owner_id: str
    left_sample_stem: str
    right_sample_stem: str
    neutral_loss_tag: str
    left_precursor_mz: float
    right_precursor_mz: float
    left_rt_min: float
    right_rt_min: float
    decision: EdgeDecision
    failure_reason: HardGateFailureReason | Literal[""]
    rt_raw_delta_sec: float
    rt_drift_corrected_delta_sec: float | None
    drift_prior_source: DriftPriorSource
    injection_order_gap: int | None
    owner_quality: OwnerQuality
    seed_support_level: SeedSupportLevel
    duplicate_context: DuplicateContext
    score: int
    reason: str


def evaluate_owner_edge(
    left: SampleLocalMS1Owner,
    right: SampleLocalMS1Owner,
    *,
    config: AlignmentConfig,
    drift_lookup: DriftLookupProtocol | None = None,
    edge_depends_on_backfill: bool = False,
    left_detected_owner: bool = True,
    right_detected_owner: bool = True,
    left_ambiguous_owner: bool = False,
    right_ambiguous_owner: bool = False,
) -> OwnerEdgeEvidence:
    raw_delta_sec = abs(left.owner_apex_rt - right.owner_apex_rt) * 60.0
    corrected_delta_sec, drift_source = _drift_corrected_delta(
        left,
        right,
        drift_lookup,
    )
    order_gap = _injection_order_gap(left, right, drift_lookup)
    owner_quality = _owner_quality(left, right, config)
    seed_support = _seed_support_level(left, right, config)
    duplicate_context = _duplicate_context(left, right, config)

    failure = _hard_gate_failure(
        left,
        right,
        config,
        edge_depends_on_backfill=edge_depends_on_backfill,
        left_detected_owner=left_detected_owner,
        right_detected_owner=right_detected_owner,
        left_ambiguous_owner=left_ambiguous_owner,
        right_ambiguous_owner=right_ambiguous_owner,
    )
    if failure:
        return OwnerEdgeEvidence(
            left_owner_id=left.owner_id,
            right_owner_id=right.owner_id,
            left_sample_stem=left.sample_stem,
            right_sample_stem=right.sample_stem,
            neutral_loss_tag=left.neutral_loss_tag,
            left_precursor_mz=left.precursor_mz,
            right_precursor_mz=right.precursor_mz,
            left_rt_min=left.owner_apex_rt,
            right_rt_min=right.owner_apex_rt,
            decision="blocked_edge",
            failure_reason=failure,
            rt_raw_delta_sec=raw_delta_sec,
            rt_drift_corrected_delta_sec=corrected_delta_sec,
            drift_prior_source=drift_source,
            injection_order_gap=order_gap,
            owner_quality=owner_quality,
            seed_support_level=seed_support,
            duplicate_context=duplicate_context,
            score=0,
            reason=f"blocked: {failure}",
        )

    score = _score_edge(
        raw_delta_sec=raw_delta_sec,
        corrected_delta_sec=corrected_delta_sec,
        owner_quality=owner_quality,
        seed_support=seed_support,
        duplicate_context=duplicate_context,
        config=config,
    )
    contradictory = (
        corrected_delta_sec is not None
        and corrected_delta_sec > raw_delta_sec + 10.0
    )
    strong = _is_strong_edge(
        raw_delta_sec=raw_delta_sec,
        corrected_delta_sec=corrected_delta_sec,
        drift_source=drift_source,
        contradictory=contradictory,
        owner_quality=owner_quality,
        seed_support=seed_support,
        score=score,
        config=config,
    )
    if strong:
        decision: EdgeDecision = "strong_edge"
        reason = "strong: hard gates passed; RT evidence close; seed support accepted"
    elif drift_source == "none" and raw_delta_sec > config.preferred_rt_sec:
        decision = "weak_edge"
        reason = "weak: no drift prior and raw RT exceeds strict tolerance"
    elif contradictory:
        decision = "weak_edge"
        reason = "weak: drift evidence contradictory"
    elif seed_support == "weak":
        decision = "weak_edge"
        reason = "weak: weak seed support"
    elif owner_quality in {"weak", "ambiguous_nearby"}:
        decision = "weak_edge"
        reason = f"weak: {owner_quality} owner quality"
    else:
        decision = "weak_edge"
        reason = "weak: hard gates passed but soft evidence below strong threshold"

    return OwnerEdgeEvidence(
        left_owner_id=left.owner_id,
        right_owner_id=right.owner_id,
        left_sample_stem=left.sample_stem,
        right_sample_stem=right.sample_stem,
        neutral_loss_tag=left.neutral_loss_tag,
        left_precursor_mz=left.precursor_mz,
        right_precursor_mz=right.precursor_mz,
        left_rt_min=left.owner_apex_rt,
        right_rt_min=right.owner_apex_rt,
        decision=decision,
        failure_reason="",
        rt_raw_delta_sec=raw_delta_sec,
        rt_drift_corrected_delta_sec=corrected_delta_sec,
        drift_prior_source=drift_source,
        injection_order_gap=order_gap,
        owner_quality=owner_quality,
        seed_support_level=seed_support,
        duplicate_context=duplicate_context,
        score=score,
        reason=reason,
    )
```

Add these private helpers in the same file. Keep `_ppm(left, right)` local to avoid importing the old private helper from `owner_clustering.py`.

```python
def _hard_gate_failure(
    left: SampleLocalMS1Owner,
    right: SampleLocalMS1Owner,
    config: AlignmentConfig,
    *,
    edge_depends_on_backfill: bool,
    left_detected_owner: bool,
    right_detected_owner: bool,
    left_ambiguous_owner: bool,
    right_ambiguous_owner: bool,
) -> HardGateFailureReason | None:
    if edge_depends_on_backfill:
        return "backfill_bridge"
    if not left_detected_owner or not right_detected_owner:
        return "non_detected_owner"
    if left_ambiguous_owner or right_ambiguous_owner:
        return "ambiguous_owner"
    if left.identity_conflict or right.identity_conflict:
        return "identity_conflict"
    if left.sample_stem == right.sample_stem:
        return "same_sample"
    if not left.neutral_loss_tag or left.neutral_loss_tag != right.neutral_loss_tag:
        return "neutral_loss_tag_mismatch"
    if _ppm(left.precursor_mz, right.precursor_mz) > config.max_ppm:
        return "precursor_mz_out_of_tolerance"
    if (
        _ppm(left.primary_identity_event.product_mz, right.primary_identity_event.product_mz)
        > config.product_mz_tolerance_ppm
    ):
        return "product_mz_out_of_tolerance"
    if (
        _ppm(
            left.primary_identity_event.observed_neutral_loss_da,
            right.primary_identity_event.observed_neutral_loss_da,
        )
        > config.observed_loss_tolerance_ppm
    ):
        return "observed_loss_out_of_tolerance"
    return None


def _drift_corrected_delta(
    left: SampleLocalMS1Owner,
    right: SampleLocalMS1Owner,
    drift_lookup: DriftLookupProtocol | None,
) -> tuple[float | None, DriftPriorSource]:
    if drift_lookup is None:
        return None, "none"
    left_delta = drift_lookup.sample_delta_min(left.sample_stem)
    right_delta = drift_lookup.sample_delta_min(right.sample_stem)
    if left_delta is None or right_delta is None:
        return None, "none"
    corrected_left = left.owner_apex_rt - left_delta
    corrected_right = right.owner_apex_rt - right_delta
    return abs(corrected_left - corrected_right) * 60.0, drift_lookup.source


def _injection_order_gap(
    left: SampleLocalMS1Owner,
    right: SampleLocalMS1Owner,
    drift_lookup: DriftLookupProtocol | None,
) -> int | None:
    if drift_lookup is None:
        return None
    left_order = drift_lookup.injection_order(left.sample_stem)
    right_order = drift_lookup.injection_order(right.sample_stem)
    if left_order is None or right_order is None:
        return None
    return abs(left_order - right_order)


def _owner_quality(
    left: SampleLocalMS1Owner,
    right: SampleLocalMS1Owner,
    config: AlignmentConfig,
) -> OwnerQuality:
    if "ambiguous" in left.assignment_reason or "ambiguous" in right.assignment_reason:
        return "ambiguous_nearby"
    if left.owner_area <= 0 or right.owner_area <= 0:
        return "weak"
    context = _duplicate_context(left, right, config)
    if context == "tail_assignment":
        return "tail_supported"
    return "clean"


def _seed_support_level(
    left: SampleLocalMS1Owner,
    right: SampleLocalMS1Owner,
    config: AlignmentConfig,
) -> SeedSupportLevel:
    min_score = min(
        left.primary_identity_event.evidence_score,
        right.primary_identity_event.evidence_score,
    )
    min_seed_count = min(
        left.primary_identity_event.seed_event_count,
        right.primary_identity_event.seed_event_count,
    )
    if (
        min_score >= config.anchor_min_evidence_score
        and min_seed_count >= config.anchor_min_seed_events
    ):
        return "strong"
    if min_score >= 40 and min_seed_count >= 1:
        return "moderate"
    return "weak"


def _duplicate_context(
    left: SampleLocalMS1Owner,
    right: SampleLocalMS1Owner,
    config: AlignmentConfig,
) -> DuplicateContext:
    contexts = {
        _owner_duplicate_context(left, config),
        _owner_duplicate_context(right, config),
    }
    if "tail_assignment" in contexts:
        return "tail_assignment"
    if "same_owner_events" in contexts:
        return "same_owner_events"
    return "none"


def _owner_duplicate_context(
    owner: SampleLocalMS1Owner,
    config: AlignmentConfig,
) -> DuplicateContext:
    if owner.assignment_reason == "owner_tail_assignment":
        return "tail_assignment"
    for event in owner.supporting_events:
        if abs(event.seed_rt - owner.owner_apex_rt) * 60.0 > config.owner_apex_close_sec:
            return "tail_assignment"
    if owner.supporting_events:
        return "same_owner_events"
    return "none"


def _score_edge(
    *,
    raw_delta_sec: float,
    corrected_delta_sec: float | None,
    owner_quality: OwnerQuality,
    seed_support: SeedSupportLevel,
    duplicate_context: DuplicateContext,
    config: AlignmentConfig,
) -> int:
    score = 0
    if raw_delta_sec <= config.preferred_rt_sec:
        score += 30
    elif raw_delta_sec <= config.max_rt_sec:
        score += 10

    if corrected_delta_sec is not None:
        if corrected_delta_sec <= config.preferred_rt_sec:
            score += 35
        elif corrected_delta_sec <= config.max_rt_sec:
            score += 10
        if corrected_delta_sec <= raw_delta_sec - 10.0:
            score += 10
        if corrected_delta_sec > raw_delta_sec + 10.0:
            score -= 20

    if seed_support == "strong":
        score += 15
    elif seed_support == "moderate":
        score += 5
    else:
        score -= 30

    if owner_quality == "clean":
        score += 10
    elif owner_quality == "tail_supported":
        score += 5
    elif owner_quality == "weak":
        score -= 30
    else:
        score -= 20

    if duplicate_context in {"same_owner_events", "tail_assignment"}:
        score += 5
    return score


def _is_strong_edge(
    *,
    raw_delta_sec: float,
    corrected_delta_sec: float | None,
    drift_source: DriftPriorSource,
    contradictory: bool,
    owner_quality: OwnerQuality,
    seed_support: SeedSupportLevel,
    score: int,
    config: AlignmentConfig,
) -> bool:
    if owner_quality in {"weak", "ambiguous_nearby"} or seed_support == "weak":
        return False
    if drift_source != "none":
        return (
            corrected_delta_sec is not None
            and corrected_delta_sec <= config.preferred_rt_sec
            and not contradictory
            and score >= 60
        )
    return raw_delta_sec <= config.preferred_rt_sec and score >= 55


def _ppm(left: float, right: float) -> float:
    denominator = max(abs(left), 1e-12)
    return abs(left - right) / denominator * 1_000_000.0
```

- [ ] **Step 4: Run the edge scoring tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_alignment_edge_scoring.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git add xic_extractor\alignment\edge_scoring.py tests\test_alignment_edge_scoring.py
git commit -m "feat: add untargeted owner edge scoring"
```

---

### Task 2: Add Targeted ISTD Drift Evidence Adapter

**Files:**
- Create: `xic_extractor/alignment/drift_evidence.py`
- Create: `tests/test_alignment_drift_evidence.py`

- [ ] **Step 1: Write failing drift evidence tests**

Create `tests/test_alignment_drift_evidence.py`:

```python
from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import pytest
from openpyxl import Workbook

from xic_extractor.alignment.drift_evidence import (
    DriftEvidenceLookup,
    SampleDriftEvidence,
    read_targeted_istd_drift_evidence,
)


def test_lookup_uses_median_sample_drift_and_injection_gap() -> None:
    lookup = DriftEvidenceLookup(
        points=(
            SampleDriftEvidence("sample-a", 1, "trend-001", 9.10, 9.00, 0.10, "targeted_istd_trend"),
            SampleDriftEvidence("sample-a", 1, "trend-002", 12.20, 12.00, 0.20, "targeted_istd_trend"),
            SampleDriftEvidence("sample-b", 5, "trend-001", 9.40, 9.00, 0.40, "targeted_istd_trend"),
        )
    )

    assert lookup.sample_delta_min("sample-a") == pytest.approx(0.15)
    assert lookup.sample_delta_min("sample-b") == pytest.approx(0.40)
    assert lookup.injection_order("sample-a") == 1
    assert lookup.injection_order("sample-b") == 5
    assert lookup.source == "targeted_istd_trend"


def test_targeted_adapter_hides_istd_labels_from_scoring_payload(tmp_path: Path) -> None:
    workbook = tmp_path / "targeted.xlsx"
    sample_info = tmp_path / "SampleInfo.xlsx"
    _write_targeted_workbook(workbook)
    _write_sample_info(sample_info)

    lookup = read_targeted_istd_drift_evidence(
        targeted_workbook=workbook,
        sample_info=sample_info,
        local_window=10,
    )

    payload_fields = {field.name for field in fields(SampleDriftEvidence)}
    assert "istd_label" not in payload_fields
    assert "target_label" not in payload_fields
    assert {point.trend_id for point in lookup.points} == {"trend-001"}
    assert lookup.sample_delta_min("sample-a") == pytest.approx(-0.10)
    assert lookup.sample_delta_min("sample-b") == pytest.approx(0.0)
    assert lookup.sample_delta_min("sample-c") == pytest.approx(0.10)


def _write_targeted_workbook(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "XIC Results"
    ws.append(
        [
            "SampleName",
            "Group",
            "Target",
            "Role",
            "ISTD Pair",
            "RT",
            "Area",
            "NL",
            "Int",
            "PeakStart",
            "PeakEnd",
            "PeakWidth",
            "Confidence",
            "Reason",
        ]
    )
    ws.append(["sample-a", "Tumor", "d3-5-medC", "ISTD", None, 9.9, 100.0, "ok", 10.0, 9.8, 10.1, 0.3, "HIGH", ""])
    ws.append(["sample-b", "Tumor", "d3-5-medC", "ISTD", None, 10.0, 100.0, "ok", 10.0, 9.9, 10.1, 0.2, "HIGH", ""])
    ws.append(["sample-c", "Tumor", "d3-5-medC", "ISTD", None, 10.1, 100.0, "ok", 10.0, 10.0, 10.2, 0.2, "HIGH", ""])
    wb.save(path)


def _write_sample_info(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(["Sample_Name", "Injection_Order"])
    ws.append(["sample-a", 1])
    ws.append(["sample-b", 2])
    ws.append(["sample-c", 3])
    wb.save(path)
```

- [ ] **Step 2: Run the new drift tests and verify failure**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_alignment_drift_evidence.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'xic_extractor.alignment.drift_evidence'`.

- [ ] **Step 3: Implement `drift_evidence.py`**

Create `xic_extractor/alignment/drift_evidence.py` with these public dataclasses and functions:

```python
from __future__ import annotations

import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from openpyxl import load_workbook

from xic_extractor.injection_rolling import read_injection_order, rolling_median_rt

DriftPriorSource = Literal["targeted_istd_trend", "batch_istd_trend", "none"]


@dataclass(frozen=True)
class SampleDriftEvidence:
    sample_stem: str
    injection_order: int
    trend_id: str
    istd_rt_min: float
    local_trend_rt_min: float
    rt_drift_delta_min: float
    source: Literal["targeted_istd_trend", "batch_istd_trend"]


@dataclass(frozen=True)
class DriftEvidenceLookup:
    points: tuple[SampleDriftEvidence, ...]

    @property
    def source(self) -> DriftPriorSource:
        if not self.points:
            return "none"
        sources = {point.source for point in self.points}
        if "targeted_istd_trend" in sources:
            return "targeted_istd_trend"
        return "batch_istd_trend"

    def sample_delta_min(self, sample_stem: str) -> float | None:
        values = [
            point.rt_drift_delta_min
            for point in self.points
            if point.sample_stem == sample_stem
        ]
        if not values:
            return None
        return float(statistics.median(values))

    def injection_order(self, sample_stem: str) -> int | None:
        orders = {
            point.injection_order
            for point in self.points
            if point.sample_stem == sample_stem
        }
        if not orders:
            return None
        if len(orders) != 1:
            raise ValueError(f"conflicting injection order for {sample_stem!r}")
        return next(iter(orders))
```

Add `read_targeted_istd_drift_evidence(targeted_workbook: Path, sample_info: Path, local_window: int = 4) -> DriftEvidenceLookup`.

Implementation rules:

- Read injection order through existing `read_injection_order(sample_info)`.
- Read sheet `XIC Results` with headers:
  `SampleName`, `Target`, `Role`, `RT`, and optional context columns.
- Propagate `SampleName` down workbook rows because target workbook uses blank sample cells after the first row for each sample.
- Keep only rows with `Role == "ISTD"` and numeric `RT`.
- Build private mapping from sorted ISTD label strings to opaque ids: `trend-001`, `trend-002`, etc.
- For each private ISTD label, compute local median through existing `rolling_median_rt(label, sample, rt_by_sample, injection_order, window=local_window)`.
- Emit a `SampleDriftEvidence` point only when local median exists.
- Do not include ISTD label, analyte target label, GT pass/fail, confidence, target RT windows, or targeted anchor tolerance in `SampleDriftEvidence`.

- [ ] **Step 4: Run drift evidence tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_alignment_drift_evidence.py tests\test_injection_rolling.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

Run:

```powershell
git add xic_extractor\alignment\drift_evidence.py tests\test_alignment_drift_evidence.py
git commit -m "feat: add untargeted drift evidence adapter"
```

---

### Task 3: Integrate Edge Scoring Into Owner Clustering

**Files:**
- Modify: `xic_extractor/alignment/owner_clustering.py`
- Modify: `tests/test_alignment_owner_clustering.py`

- [ ] **Step 1: Add failing owner clustering tests for edge decisions**

Append to `tests/test_alignment_owner_clustering.py`:

```python
def test_owner_clustering_uses_drift_prior_for_strong_edge_over_strict_rt() -> None:
    edge_evidence = []
    features = cluster_sample_local_owners(
        (
            _owner("sample-a", "a", apex_rt=10.0),
            _owner("sample-b", "b", apex_rt=11.2),
        ),
        config=AlignmentConfig(preferred_rt_sec=60.0, max_rt_sec=180.0),
        drift_lookup=_DriftLookup(
            deltas={"sample-a": 0.0, "sample-b": 0.25},
            orders={"sample-a": 1, "sample-b": 10},
            source="targeted_istd_trend",
        ),
        edge_evidence_sink=edge_evidence,
    )

    assert len(features) == 1
    assert features[0].event_cluster_ids == ("OWN-sample-a-a", "OWN-sample-b-b")
    assert [edge.decision for edge in edge_evidence] == ["strong_edge"]


def test_owner_clustering_preserves_weak_no_drift_rt_split() -> None:
    edge_evidence = []
    features = cluster_sample_local_owners(
        (
            _owner("sample-a", "a", apex_rt=10.0),
            _owner("sample-b", "b", apex_rt=11.2),
        ),
        config=AlignmentConfig(preferred_rt_sec=60.0, max_rt_sec=180.0),
        edge_evidence_sink=edge_evidence,
    )

    assert len(features) == 2
    assert [edge.decision for edge in edge_evidence] == ["weak_edge"]


def test_owner_clustering_records_blocked_edge_without_merging() -> None:
    edge_evidence = []
    features = cluster_sample_local_owners(
        (
            _owner("sample-a", "a", neutral_loss_tag="DNA_dR"),
            _owner("sample-b", "b", neutral_loss_tag="DNA_R"),
        ),
        config=AlignmentConfig(),
        edge_evidence_sink=edge_evidence,
    )

    assert len(features) == 2
    assert [edge.failure_reason for edge in edge_evidence] == [
        "neutral_loss_tag_mismatch"
    ]


class _DriftLookup:
    def __init__(self, *, deltas: dict[str, float], orders: dict[str, int], source: str):
        self._deltas = deltas
        self._orders = orders
        self.source = source

    def sample_delta_min(self, sample_stem: str) -> float | None:
        return self._deltas.get(sample_stem)

    def injection_order(self, sample_stem: str) -> int | None:
        return self._orders.get(sample_stem)
```

Update the existing `test_owner_clustering_collapses_5medc_like_class_drift()` so it passes an explicit drift lookup:

```python
drift_lookup=_DriftLookup(
    deltas={
        "tumor-a": -0.35,
        "qc-a": 0.0,
        "qc-b": 0.10,
        "normal-a": 0.35,
        "benign-a": 0.36,
    },
    orders={
        "tumor-a": 1,
        "qc-a": 20,
        "qc-b": 40,
        "normal-a": 60,
        "benign-a": 80,
    },
    source="targeted_istd_trend",
)
```

- [ ] **Step 2: Run owner clustering tests and verify failure**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_alignment_owner_clustering.py -q
```

Expected: FAIL because `cluster_sample_local_owners()` does not accept `drift_lookup` or `edge_evidence_sink`.

- [ ] **Step 3: Modify `owner_clustering.py`**

Change the public signature:

```python
def cluster_sample_local_owners(
    owners: tuple[SampleLocalMS1Owner, ...] | list[SampleLocalMS1Owner],
    *,
    config: AlignmentConfig,
    drift_lookup: DriftLookupProtocol | None = None,
    edge_evidence_sink: list[OwnerEdgeEvidence] | None = None,
) -> tuple[OwnerAlignedFeature, ...]:
```

Replace `_compatible_owners()` use with a cached edge evaluator:

```python
edge_cache: dict[tuple[str, str], OwnerEdgeEvidence] = {}
groups = _complete_link_groups(
    sorted(clean, key=_owner_sort_key),
    config,
    drift_lookup=drift_lookup,
    edge_evidence_sink=edge_evidence_sink,
    edge_cache=edge_cache,
)
```

Inside `_complete_link_groups()`, treat owners as compatible only when every pair returns `decision == "strong_edge"`.

Add helper:

```python
def _edge_for_pair(
    left: SampleLocalMS1Owner,
    right: SampleLocalMS1Owner,
    *,
    config: AlignmentConfig,
    drift_lookup: DriftLookupProtocol | None,
    edge_evidence_sink: list[OwnerEdgeEvidence] | None,
    edge_cache: dict[tuple[str, str], OwnerEdgeEvidence],
) -> OwnerEdgeEvidence:
    key = tuple(sorted((left.owner_id, right.owner_id)))
    edge = edge_cache.get(key)
    if edge is None:
        edge = evaluate_owner_edge(left, right, config=config, drift_lookup=drift_lookup)
        edge_cache[key] = edge
        if edge_evidence_sink is not None:
            edge_evidence_sink.append(edge)
    return edge
```

Keep `_owner_match_score()` as the deterministic tie-breaker, but compute it only among strong-compatible groups. Do not use weak edges for grouping.

- [ ] **Step 4: Run focused owner clustering tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_alignment_owner_clustering.py tests\test_alignment_edge_scoring.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

Run:

```powershell
git add xic_extractor\alignment\owner_clustering.py tests\test_alignment_owner_clustering.py
git commit -m "feat: use drift-aware owner edge clustering"
```

---

### Task 4: Wire Edge Evidence Through Pipeline, Output Levels, and CLI

**Files:**
- Modify: `xic_extractor/alignment/debug_writer.py`
- Modify: `xic_extractor/alignment/output_levels.py`
- Modify: `xic_extractor/alignment/pipeline.py`
- Modify: `scripts/run_alignment.py`
- Modify: `tests/test_alignment_debug_writer.py`
- Modify: `tests/test_alignment_output_levels.py`
- Modify: `tests/test_alignment_pipeline.py`
- Modify: `tests/test_run_alignment.py`
- Modify: `tests/test_alignment_boundaries.py`

- [ ] **Step 1: Add failing debug writer and output-level tests**

Append to `tests/test_alignment_debug_writer.py`:

```python
from xic_extractor.alignment.edge_scoring import OwnerEdgeEvidence
from xic_extractor.alignment.debug_writer import write_owner_edge_evidence_tsv


def test_write_owner_edge_evidence_tsv_uses_stable_columns(tmp_path):
    edge = OwnerEdgeEvidence(
        left_owner_id="OWN-a",
        right_owner_id="OWN-b",
        left_sample_stem="sample-a",
        right_sample_stem="sample-b",
        neutral_loss_tag="DNA_dR",
        left_precursor_mz=242.1136,
        right_precursor_mz=242.1137,
        left_rt_min=10.0,
        right_rt_min=11.2,
        decision="strong_edge",
        failure_reason="",
        rt_raw_delta_sec=72.0,
        rt_drift_corrected_delta_sec=57.0,
        drift_prior_source="targeted_istd_trend",
        injection_order_gap=10,
        owner_quality="clean",
        seed_support_level="strong",
        duplicate_context="same_owner_events",
        score=95,
        reason="strong: hard gates passed",
    )

    path = write_owner_edge_evidence_tsv(tmp_path / "owner_edge_evidence.tsv", [edge])

    assert path.read_text(encoding="utf-8").splitlines() == [
        "left_owner_id\tright_owner_id\tleft_sample_stem\tright_sample_stem\tneutral_loss_tag\tleft_precursor_mz\tright_precursor_mz\tleft_rt_min\tright_rt_min\tdecision\tfailure_reason\trt_raw_delta_sec\trt_drift_corrected_delta_sec\tdrift_prior_source\tinjection_order_gap\towner_quality\tseed_support_level\tduplicate_context\tscore\treason",
        "OWN-a\tOWN-b\tsample-a\tsample-b\tDNA_dR\t242.114\t242.114\t10\t11.2\tstrong_edge\t\t72\t57\ttargeted_istd_trend\t10\tclean\tstrong\tsame_owner_events\t95\tstrong: hard gates passed",
    ]
```

Update `tests/test_alignment_output_levels.py` so `debug` and `validation` include `owner_edge_evidence.tsv`:

```python
def test_validation_output_level_includes_owner_edge_evidence():
    assert "owner_edge_evidence.tsv" in artifact_names_for_output_level("validation")
```

- [ ] **Step 2: Run debug/output tests and verify failure**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_alignment_debug_writer.py tests\test_alignment_output_levels.py -q
```

Expected: FAIL because the writer and output artifact are missing.

- [ ] **Step 3: Implement edge evidence TSV and output artifact**

In `xic_extractor/alignment/debug_writer.py`, add:

```python
from xic_extractor.alignment.edge_scoring import OwnerEdgeEvidence


def write_owner_edge_evidence_tsv(
    path: Path,
    edges: Sequence[OwnerEdgeEvidence],
) -> Path:
    rows = [
        {
            "left_owner_id": edge.left_owner_id,
            "right_owner_id": edge.right_owner_id,
            "left_sample_stem": edge.left_sample_stem,
            "right_sample_stem": edge.right_sample_stem,
            "neutral_loss_tag": edge.neutral_loss_tag,
            "left_precursor_mz": _format_optional_float(edge.left_precursor_mz),
            "right_precursor_mz": _format_optional_float(edge.right_precursor_mz),
            "left_rt_min": _format_optional_float(edge.left_rt_min),
            "right_rt_min": _format_optional_float(edge.right_rt_min),
            "decision": edge.decision,
            "failure_reason": edge.failure_reason,
            "rt_raw_delta_sec": _format_optional_float(edge.rt_raw_delta_sec),
            "rt_drift_corrected_delta_sec": _format_optional_float(
                edge.rt_drift_corrected_delta_sec
            ),
            "drift_prior_source": edge.drift_prior_source,
            "injection_order_gap": ""
            if edge.injection_order_gap is None
            else str(edge.injection_order_gap),
            "owner_quality": edge.owner_quality,
            "seed_support_level": edge.seed_support_level,
            "duplicate_context": edge.duplicate_context,
            "score": str(edge.score),
            "reason": edge.reason,
        }
        for edge in edges
    ]
    return _write_tsv(
        path,
        (
            "left_owner_id",
            "right_owner_id",
            "left_sample_stem",
            "right_sample_stem",
            "neutral_loss_tag",
            "left_precursor_mz",
            "right_precursor_mz",
            "left_rt_min",
            "right_rt_min",
            "decision",
            "failure_reason",
            "rt_raw_delta_sec",
            "rt_drift_corrected_delta_sec",
            "drift_prior_source",
            "injection_order_gap",
            "owner_quality",
            "seed_support_level",
            "duplicate_context",
            "score",
            "reason",
        ),
        rows,
    )
```

Add `_format_optional_float()` in the same module:

```python
def _format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6g}"
```

In `output_levels.py`, append `owner_edge_evidence.tsv` to both `debug` and `validation` artifact tuples.

- [ ] **Step 4: Add pipeline and CLI tests**

Update `tests/test_alignment_pipeline.py` with a test that monkeypatches `cluster_sample_local_owners()` and asserts `drift_lookup` is passed plus `owner_edge_evidence.tsv` is written for validation output. Use a fake edge:

```python
from xic_extractor.alignment.edge_scoring import OwnerEdgeEvidence


def test_pipeline_passes_drift_lookup_and_writes_edge_evidence(monkeypatch, tmp_path):
    captured = {}
    batch_index = _write_batch(tmp_path, ("Sample_A", "Sample_B"))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    (raw_dir / "Sample_B.raw").write_text("raw", encoding="utf-8")
    drift_lookup = object()
    fake_edge = OwnerEdgeEvidence(
        left_owner_id="OWN-a",
        right_owner_id="OWN-b",
        left_sample_stem="Sample_A",
        right_sample_stem="Sample_B",
        neutral_loss_tag="DNA_dR",
        left_precursor_mz=242.1136,
        right_precursor_mz=242.1137,
        left_rt_min=10.0,
        right_rt_min=11.2,
        decision="weak_edge",
        failure_reason="",
        rt_raw_delta_sec=72.0,
        rt_drift_corrected_delta_sec=None,
        drift_prior_source="none",
        injection_order_gap=None,
        owner_quality="clean",
        seed_support_level="strong",
        duplicate_context="none",
        score=55,
        reason="weak: no drift prior",
    )

    def fake_build_owners(*args, **kwargs):
        return SimpleNamespace(owners=("owner",), ambiguous_records=())

    def fake_cluster(owners, *, config, drift_lookup=None, edge_evidence_sink=None):
        captured["drift_lookup"] = drift_lookup
        edge_evidence_sink.append(fake_edge)
        return ()

    def fake_backfill(*args, **kwargs):
        return ()

    def fake_matrix(features, *, sample_order, ambiguous_by_sample, rescued_cells):
        return _matrix(sample_order)

    monkeypatch.setattr(pipeline_module, "build_sample_local_owners", fake_build_owners)
    monkeypatch.setattr(pipeline_module, "cluster_sample_local_owners", fake_cluster)
    monkeypatch.setattr(pipeline_module, "build_owner_backfill_cells", fake_backfill)
    monkeypatch.setattr(pipeline_module, "build_owner_alignment_matrix", fake_matrix)

    outputs = pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        output_level="validation",
        raw_opener=FakeRawOpener(),
        drift_lookup=drift_lookup,
    )

    assert captured["drift_lookup"] is drift_lookup
    assert outputs.edge_evidence_tsv == tmp_path / "out" / "owner_edge_evidence.tsv"
    assert (tmp_path / "out" / "owner_edge_evidence.tsv").read_text(encoding="utf-8")
```

Update `tests/test_run_alignment.py`:

```python
def test_cli_requires_sample_info_with_targeted_istd_workbook(tmp_path, capsys):
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text(
        "sample_stem,raw_file,candidate_csv,review_csv\n",
        encoding="utf-8",
    )
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--targeted-istd-workbook",
            str(tmp_path / "targeted.xlsx"),
        ]
    )

    assert code == 2
    assert "--sample-info is required" in capsys.readouterr().err


def test_cli_passes_drift_lookup_and_raw_worker_metadata(monkeypatch, tmp_path):
    captured = {}

    def fake_read_drift(*, targeted_workbook, sample_info):
        captured["drift_paths"] = (targeted_workbook, sample_info)
        return object()

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        return AlignmentRunOutputs(edge_evidence_tsv=tmp_path / "owner_edge_evidence.tsv")

    monkeypatch.setattr(run_alignment, "read_targeted_istd_drift_evidence", fake_read_drift)
    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)
    # Create minimal existing path inputs and call main with --raw-workers 8.
```

- [ ] **Step 5: Run pipeline/CLI tests and verify failure**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_alignment_pipeline.py tests\test_run_alignment.py -q
```

Expected: FAIL because pipeline and CLI are not wired yet.

- [ ] **Step 6: Implement pipeline and CLI wiring**

Pipeline changes:

- Add `edge_evidence_tsv: Path | None = None` to `AlignmentRunOutputs`.
- Add `drift_lookup: DriftLookupProtocol | None = None` to `run_alignment()`.
- At the beginning of `run_alignment()`, record:

```python
recorder.record(
    "alignment.run_config",
    elapsed_sec=0.0,
    metrics={
        "raw_workers": raw_workers,
        "raw_xic_batch_size": raw_xic_batch_size,
        "output_level": output_level,
        "drift_prior_source": drift_lookup.source if drift_lookup is not None else "none",
    },
)
```

- Before clustering, create `edge_evidence: list[OwnerEdgeEvidence] = []`.
- Call:

```python
owner_features = cluster_sample_local_owners(
    ownership.owners,
    config=alignment_config,
    drift_lookup=drift_lookup,
    edge_evidence_sink=edge_evidence,
)
```

- Include `owner_edge_evidence.tsv` in `_output_paths()`.
- Pass `edge_evidence` into `_write_outputs_atomic()`.
- Write it with `write_owner_edge_evidence_tsv()`.

CLI changes:

- Add arguments:

```python
parser.add_argument("--sample-info", type=Path)
parser.add_argument("--targeted-istd-workbook", type=Path)
parser.add_argument("--drift-local-window", type=_positive_int, default=40)
```

- Immediately after parsing args and before any filesystem path validation, validate pairwise use:

```python
if (args.sample_info is None) != (args.targeted_istd_workbook is None):
    print(
        "--sample-info is required with --targeted-istd-workbook, and both must be provided together",
        file=sys.stderr,
    )
    return 2
```

- Build drift lookup only when both are present:

```python
drift_lookup = None
if args.sample_info is not None and args.targeted_istd_workbook is not None:
    drift_lookup = read_targeted_istd_drift_evidence(
        targeted_workbook=args.targeted_istd_workbook.resolve(),
        sample_info=args.sample_info.resolve(),
    )
```

- Pass `drift_lookup=drift_lookup` into `run_alignment()`.
- Print `Owner edge evidence TSV: {outputs.edge_evidence_tsv}` when not `None`.

Boundary test update:

- Extend `tests/test_alignment_boundaries.py` with an `edge_scoring.py` import boundary that bans RAW reader, workbook writer, CLI, process backend, and GUI imports.
- Allow `drift_evidence.py` to import `openpyxl` because it is an adapter; keep `edge_scoring.py` free of openpyxl and RAW imports.

- [ ] **Step 7: Run focused output and CLI tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_alignment_debug_writer.py tests\test_alignment_output_levels.py tests\test_alignment_pipeline.py tests\test_run_alignment.py tests\test_alignment_boundaries.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit Task 4**

Run:

```powershell
git add xic_extractor\alignment\debug_writer.py xic_extractor\alignment\output_levels.py xic_extractor\alignment\pipeline.py scripts\run_alignment.py tests\test_alignment_debug_writer.py tests\test_alignment_output_levels.py tests\test_alignment_pipeline.py tests\test_run_alignment.py tests\test_alignment_boundaries.py
git commit -m "feat: expose untargeted owner edge diagnostics"
```

---

### Task 5: Add Guardrail and Case Assertion Diagnostics

**Files:**
- Create: `tools/diagnostics/untargeted_alignment_guardrails.py`
- Create: `tests/test_untargeted_alignment_guardrails.py`

- [ ] **Step 1: Write failing guardrail tests**

Create `tests/test_untargeted_alignment_guardrails.py`:

```python
from __future__ import annotations

import csv
from pathlib import Path

from tools.diagnostics.untargeted_alignment_guardrails import (
    compute_guardrails,
    compare_guardrails,
    compare_targeted_audit_counts,
    write_case_assertion_summary_tsv,
)


def test_compute_guardrails_counts_duplicate_zero_and_backfill(tmp_path: Path) -> None:
    alignment_dir = tmp_path / "alignment"
    alignment_dir.mkdir()
    _write_tsv(
        alignment_dir / "alignment_review.tsv",
        ["feature_family_id", "family_center_mz", "family_center_rt", "event_cluster_count", "event_member_count", "warning"],
        [
            ["FAM1", "284.0989", "16.5", "1", "3", ""],
            ["FAM2", "242.114", "12.4", "1", "5", "high_backfill_dependency"],
            ["FAM3", "296.074", "19.5", "2", "2", ""],
        ],
    )
    _write_tsv(
        alignment_dir / "alignment_cells.tsv",
        ["feature_family_id", "sample_stem", "status", "family_center_mz", "family_center_rt"],
        [
            ["FAM1", "s1", "duplicate_assigned", "284.0989", "16.5"],
            ["FAM1", "s2", "absent", "284.0989", "16.5"],
            ["FAM2", "s1", "rescued", "242.114", "12.4"],
            ["FAM2", "s2", "rescued", "242.114", "12.4"],
            ["FAM2", "s3", "detected", "242.114", "12.4"],
            ["FAM3", "s1", "ambiguous_ms1_owner", "296.074", "19.5"],
            ["FAM3", "s2", "detected", "296.074", "19.5"],
        ],
    )
    _write_tsv(
        alignment_dir / "owner_edge_evidence.tsv",
        [
            "left_owner_id",
            "right_owner_id",
            "left_sample_stem",
            "right_sample_stem",
            "neutral_loss_tag",
            "left_precursor_mz",
            "right_precursor_mz",
            "left_rt_min",
            "right_rt_min",
            "decision",
            "rt_raw_delta_sec",
            "rt_drift_corrected_delta_sec",
        ],
        [
            [
                "OWN-a",
                "OWN-b",
                "s1",
                "s2",
                "DNA_dR",
                "322.143",
                "322.1431",
                "23.0",
                "23.5",
                "strong_edge",
                "72",
                "57",
            ]
        ],
    )

    metrics = compute_guardrails(alignment_dir)

    assert metrics.zero_present_families == 1
    assert metrics.duplicate_only_families == 1
    assert metrics.high_backfill_dependency_families == 1
    assert metrics.negative_8oxodg_production_families == 0
    assert metrics.case_assertions["case1_mz242_5medC_like"].supporting_event_count == 4
    assert metrics.case_assertions["case2_mz296_dense_duplicate"].preserved_split_or_ambiguous is True
    assert metrics.case_assertions["case3_mz322_dense_duplicate"].strong_edge_count == 1

    summary_path = write_case_assertion_summary_tsv(
        tmp_path / "case_assertion_summary.tsv",
        metrics.case_assertions,
    )
    assert "case3_mz322_dense_duplicate" in summary_path.read_text(encoding="utf-8")


def test_compare_guardrails_marks_regression_when_candidate_increases() -> None:
    baseline = {"duplicate_only_families": 1, "zero_present_families": 1}
    candidate = {"duplicate_only_families": 2, "zero_present_families": 1}

    rows = compare_guardrails(baseline, candidate)

    assert rows[0]["metric"] == "duplicate_only_families"
    assert rows[0]["status"] == "FAIL"
    assert rows[1]["status"] == "PASS"


def test_compare_targeted_audit_counts_marks_split_and_miss_regressions(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline_comparison.csv"
    candidate = tmp_path / "candidate_comparison.csv"
    _write_csv(
        baseline,
        ["sample_stem", "failure_mode"],
        [["s1", "PASS"], ["s2", "SPLIT"], ["s3", "MISS"]],
    )
    _write_csv(
        candidate,
        ["sample_stem", "failure_mode"],
        [["s1", "SPLIT"], ["s2", "SPLIT"], ["s3", "MISS"], ["s4", "MISS"]],
    )

    rows = compare_targeted_audit_counts(
        baseline,
        candidate,
        target_label="5-hmdC",
    )

    assert rows == [
        {
            "target_label": "5-hmdC",
            "metric": "SPLIT",
            "baseline_count": "1",
            "candidate_count": "2",
            "status": "FAIL",
        },
        {
            "target_label": "5-hmdC",
            "metric": "MISS",
            "baseline_count": "1",
            "candidate_count": "2",
            "status": "FAIL",
        },
    ]


def _write_tsv(path: Path, fieldnames: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(fieldnames)
        writer.writerows(rows)


def _write_csv(path: Path, fieldnames: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(fieldnames)
        writer.writerows(rows)
```

- [ ] **Step 2: Run guardrail tests and verify failure**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_untargeted_alignment_guardrails.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tools.diagnostics.untargeted_alignment_guardrails'`.

- [ ] **Step 3: Implement guardrail diagnostics CLI**

Create `tools/diagnostics/untargeted_alignment_guardrails.py` with:

- `GuardrailMetrics` dataclass.
- `CaseAssertion` dataclass.
- `compute_guardrails(alignment_dir: Path) -> GuardrailMetrics`.
- `compare_guardrails(baseline: Mapping[str, int], candidate: Mapping[str, int]) -> list[dict[str, str]]`.
- `write_case_assertion_summary_tsv(path: Path, cases: Mapping[str, CaseAssertion]) -> Path`.
- `compare_targeted_audit_counts(baseline_csv: Path, candidate_csv: Path, *, target_label: str) -> list[dict[str, str]]`.
- CLI arguments:

```text
--alignment-dir PATH
--baseline-dir PATH
--candidate-dir PATH
--output-json PATH
--case-summary-tsv PATH
--comparison-csv PATH
--baseline-targeted-comparison PATH
--candidate-targeted-comparison PATH
--target-label LABEL
--targeted-comparison-csv PATH
```

CLI behavior:

- With `--alignment-dir`, write one metrics JSON to `--output-json` and write `case_assertion_summary.tsv` when `--case-summary-tsv` is provided.
- With `--baseline-dir` and `--candidate-dir`, write comparison CSV to `--comparison-csv`.
- With `--baseline-targeted-comparison`, `--candidate-targeted-comparison`, `--target-label`, and `--targeted-comparison-csv`, compare `SPLIT` and `MISS` counts mechanically and write a two-row CSV.
- If any required TSV is missing, exit code `2` and print the missing path.
- Metrics JSON must include:
  `zero_present_families`, `duplicate_only_families`, `high_backfill_dependency_families`, `negative_8oxodg_production_families`, and `case_assertions`.
- Comparison CSV metric order must be:
  `duplicate_only_families`, `zero_present_families`, `high_backfill_dependency_families`, `negative_8oxodg_production_families`.

Use the guardrail derivations from this plan. Use `csv.DictReader(delimiter="\t")`; do not import production pipeline modules.

- [ ] **Step 4: Run guardrail tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_untargeted_alignment_guardrails.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 5**

Run:

```powershell
git add tools\diagnostics\untargeted_alignment_guardrails.py tests\test_untargeted_alignment_guardrails.py
git commit -m "feat: add untargeted alignment guardrail diagnostics"
```

---

### Task 6: Run Unit and Contract Test Shard

**Files:**
- No new files.
- Validates Tasks 1-5 together.

- [ ] **Step 1: Run focused alignment shard**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_alignment_edge_scoring.py tests\test_alignment_drift_evidence.py tests\test_alignment_owner_clustering.py tests\test_alignment_debug_writer.py tests\test_alignment_output_levels.py tests\test_alignment_pipeline.py tests\test_run_alignment.py tests\test_untargeted_alignment_guardrails.py tests\test_alignment_boundaries.py -q
```

Expected: PASS.

- [ ] **Step 2: Run broader alignment writer/ownership shard**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_alignment_ownership.py tests\test_alignment_owner_matrix.py tests\test_alignment_tsv_writer.py tests\test_alignment_claim_registry.py tests\test_targeted_gt_alignment_audit.py -q
```

Expected: PASS.

- [ ] **Step 3: Commit only if test fixes were needed**

If Step 1 or Step 2 required code or test fixes, commit those fixes:

```powershell
git add xic_extractor tests tools
git commit -m "test: cover drift-aware owner edge integration"
```

If no files changed after Task 5, skip this commit and continue.

---

### Task 7: Run 8 RAW Real-Data Validation With 8 Workers

**Files:**
- No production edits.
- Produces validation artifacts in `output\alignment\drift_soft_edge_8raw_20260513` and `output\diagnostics\drift_soft_edge_8raw_20260513`.

- [ ] **Step 1: Verify required paths exist**

Run:

```powershell
Test-Path output\discovery\semantics_cleanup_8raw_20260511\discovery_batch_index.csv
Test-Path output\alignment\semantics_cleanup_8raw_20260511
Test-Path C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1151.xlsx
Test-Path "C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\SampleInfo.xlsx"
Test-Path C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation
Test-Path "C:\Program Files (x86)\Thermo\Foundation"
```

Expected: all six commands print `True`. If any prints `False`, stop and report that path.

- [ ] **Step 2: Run 8 RAW alignment with workers=8**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python scripts\run_alignment.py `
  --discovery-batch-index output\discovery\semantics_cleanup_8raw_20260511\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation `
  --dll-dir "C:\Program Files (x86)\Thermo\Foundation" `
  --output-dir output\alignment\drift_soft_edge_8raw_20260513 `
  --output-level validation `
  --raw-workers 8 `
  --raw-xic-batch-size 16 `
  --sample-info "C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\SampleInfo.xlsx" `
  --targeted-istd-workbook C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1151.xlsx `
  --timing-output output\alignment\drift_soft_edge_8raw_20260513\timing.json
```

Expected:

- CLI prints `Alignment workbook`, `Alignment review TSV`, `Alignment cells TSV`, `Owner edge evidence TSV`, and `Timing JSON`.
- `output\alignment\drift_soft_edge_8raw_20260513\owner_edge_evidence.tsv` exists.
- `timing.json` includes a record with `stage == "alignment.run_config"` and `metrics.raw_workers == 8`.

- [ ] **Step 3: Run positive targeted GT audits**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python tools\diagnostics\targeted_gt_alignment_audit.py `
  --target-workbook C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1151.xlsx `
  --alignment-run output\alignment\drift_soft_edge_8raw_20260513 `
  --target-label 5-medC `
  --istd-label d3-5-medC `
  --target-mz 242.1136 `
  --ppm 20 `
  --pass-rt-sec 30 `
  --drift-rt-sec 180 `
  --output-dir output\diagnostics\drift_soft_edge_8raw_20260513\gt_5medc

uv run python tools\diagnostics\targeted_gt_alignment_audit.py `
  --target-workbook C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1151.xlsx `
  --alignment-run output\alignment\drift_soft_edge_8raw_20260513 `
  --target-label 5-hmdC `
  --istd-label d3-5-hmdC `
  --target-mz 258.1085 `
  --ppm 20 `
  --pass-rt-sec 30 `
  --drift-rt-sec 180 `
  --output-dir output\diagnostics\drift_soft_edge_8raw_20260513\gt_5hmdc
```

Expected: both commands write `comparison.csv` and `failure_mode_report.md`.

- [ ] **Step 4: Run negative 8-oxodG audit**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python tools\diagnostics\targeted_gt_alignment_audit.py `
  --target-workbook C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1151.xlsx `
  --alignment-run output\alignment\drift_soft_edge_8raw_20260513 `
  --target-label 8-oxodG `
  --istd-label 15N5-8-oxodG `
  --target-mz 284.0989 `
  --ppm 20 `
  --pass-rt-sec 30 `
  --drift-rt-sec 180 `
  --output-dir output\diagnostics\drift_soft_edge_8raw_20260513\gt_8oxodg
```

Expected: command writes diagnostics. Production acceptance is evaluated by guardrails in the next step, not by production code reading the target label.

- [ ] **Step 5: Compute 8 RAW guardrails and case assertions**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python tools\diagnostics\untargeted_alignment_guardrails.py `
  --alignment-dir output\alignment\semantics_cleanup_8raw_20260511 `
  --output-json output\diagnostics\drift_soft_edge_8raw_20260513\baseline_guardrails.json `
  --case-summary-tsv output\diagnostics\drift_soft_edge_8raw_20260513\baseline_case_assertion_summary.tsv

uv run python tools\diagnostics\untargeted_alignment_guardrails.py `
  --alignment-dir output\alignment\drift_soft_edge_8raw_20260513 `
  --output-json output\diagnostics\drift_soft_edge_8raw_20260513\candidate_guardrails.json `
  --case-summary-tsv output\diagnostics\drift_soft_edge_8raw_20260513\case_assertion_summary.tsv

uv run python tools\diagnostics\untargeted_alignment_guardrails.py `
  --baseline-dir output\alignment\semantics_cleanup_8raw_20260511 `
  --candidate-dir output\alignment\drift_soft_edge_8raw_20260513 `
  --comparison-csv output\diagnostics\drift_soft_edge_8raw_20260513\guardrail_comparison.csv
```

Expected:

- `candidate_guardrails.json` has `"negative_8oxodg_production_families": 0`.
- `case_assertion_summary.tsv` exists and has rows for case1-4.
- `guardrail_comparison.csv` has no `FAIL` rows for duplicate-only, zero-present, or high-backfill-dependency.
- Case1 production family count does not increase.
- Case2 `preserved_split_or_ambiguous` is true.
- Case3 has at least one strong drift-corrected edge if compatible detected owners exist in the case window.
- Case4 has `supporting_event_count > 0`.

- [ ] **Step 6: Inspect targeted audit summaries**

Open the two positive audit reports and compare to baseline 8 RAW:

- Baseline 8 RAW `5-medC`: PASS 8/8, SPLIT 0, DRIFT 0, DUPLICATE 0, MISS 0.
- Baseline 8 RAW `5-hmdC`: PASS 8/8, SPLIT 0, DRIFT 0, DUPLICATE 0, MISS 0.

Pass rule:

- `new_split <= baseline_split`
- `new_miss <= baseline_miss`

If either positive fixture regresses, stop and inspect `owner_edge_evidence.tsv` before proceeding to 85 RAW.

- [ ] **Step 7: Commit 8 RAW validation artifact references if tracked docs are updated**

Do not commit generated output directories unless the repo already tracks them. If a markdown validation note is created under `output\diagnostics` and is tracked by the repo, commit it:

```powershell
git status --short
git add output\diagnostics\drift_soft_edge_8raw_20260513
git commit -m "test: record 8raw drift edge validation"
```

If generated outputs are untracked and intentionally ignored, skip this commit.

---

### Task 8: Run 85 RAW Real-Data Guardrail Validation With 8 Workers

**Files:**
- No production edits.
- Produces validation artifacts in `output\alignment\drift_soft_edge_85raw_20260513` and `output\diagnostics\drift_soft_edge_85raw_20260513`.

- [ ] **Step 1: Verify required 85 RAW paths exist**

Run:

```powershell
Test-Path output\discovery\tissue85_alignment_v1\discovery_batch_index.csv
Test-Path output\alignment\gt_audit_checkpoint_85raw_validation_20260512
Test-Path C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1200.xlsx
Test-Path "C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\SampleInfo.xlsx"
Test-Path C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R
Test-Path "C:\Program Files (x86)\Thermo\Foundation"
```

Expected: all six commands print `True`. If any prints `False`, stop and report that path.

- [ ] **Step 2: Run 85 RAW alignment with workers=8**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python scripts\run_alignment.py `
  --discovery-batch-index output\discovery\tissue85_alignment_v1\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir "C:\Program Files (x86)\Thermo\Foundation" `
  --output-dir output\alignment\drift_soft_edge_85raw_20260513 `
  --output-level validation `
  --raw-workers 8 `
  --raw-xic-batch-size 16 `
  --sample-info "C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\SampleInfo.xlsx" `
  --targeted-istd-workbook C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1200.xlsx `
  --timing-output output\alignment\drift_soft_edge_85raw_20260513\timing.json
```

Expected:

- CLI prints validation artifacts.
- `owner_edge_evidence.tsv` exists.
- `timing.json` includes `alignment.run_config` with `raw_workers == 8`.
- If the run cannot execute 8 workers in the local environment, record validation as `SKIP` with the exact error and do not claim PASS.

- [ ] **Step 3: Run 85 RAW baseline targeted GT audits**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python tools\diagnostics\targeted_gt_alignment_audit.py `
  --target-workbook C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1200.xlsx `
  --alignment-run output\alignment\gt_audit_checkpoint_85raw_validation_20260512 `
  --target-label 5-medC `
  --istd-label d3-5-medC `
  --target-mz 242.1136 `
  --ppm 20 `
  --pass-rt-sec 30 `
  --drift-rt-sec 180 `
  --output-dir output\diagnostics\drift_soft_edge_85raw_20260513\baseline_gt_5medc

uv run python tools\diagnostics\targeted_gt_alignment_audit.py `
  --target-workbook C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1200.xlsx `
  --alignment-run output\alignment\gt_audit_checkpoint_85raw_validation_20260512 `
  --target-label 5-hmdC `
  --istd-label d3-5-hmdC `
  --target-mz 258.1085 `
  --ppm 20 `
  --pass-rt-sec 30 `
  --drift-rt-sec 180 `
  --output-dir output\diagnostics\drift_soft_edge_85raw_20260513\baseline_gt_5hmdc
```

Expected baseline counts:

- `5-medC`: SPLIT 0, MISS 0.
- `5-hmdC`: SPLIT 2, MISS 6.

- [ ] **Step 4: Run 85 RAW candidate targeted GT audits**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python tools\diagnostics\targeted_gt_alignment_audit.py `
  --target-workbook C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1200.xlsx `
  --alignment-run output\alignment\drift_soft_edge_85raw_20260513 `
  --target-label 5-medC `
  --istd-label d3-5-medC `
  --target-mz 242.1136 `
  --ppm 20 `
  --pass-rt-sec 30 `
  --drift-rt-sec 180 `
  --output-dir output\diagnostics\drift_soft_edge_85raw_20260513\gt_5medc

uv run python tools\diagnostics\targeted_gt_alignment_audit.py `
  --target-workbook C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1200.xlsx `
  --alignment-run output\alignment\drift_soft_edge_85raw_20260513 `
  --target-label 5-hmdC `
  --istd-label d3-5-hmdC `
  --target-mz 258.1085 `
  --ppm 20 `
  --pass-rt-sec 30 `
  --drift-rt-sec 180 `
  --output-dir output\diagnostics\drift_soft_edge_85raw_20260513\gt_5hmdc

uv run python tools\diagnostics\targeted_gt_alignment_audit.py `
  --target-workbook C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1200.xlsx `
  --alignment-run output\alignment\drift_soft_edge_85raw_20260513 `
  --target-label 8-oxodG `
  --istd-label 15N5-8-oxodG `
  --target-mz 284.0989 `
  --ppm 20 `
  --pass-rt-sec 30 `
  --drift-rt-sec 180 `
  --output-dir output\diagnostics\drift_soft_edge_85raw_20260513\gt_8oxodg
```

Expected: all commands write `comparison.csv` and `failure_mode_report.md`.

- [ ] **Step 5: Compare 85 RAW targeted SPLIT/MISS mechanically**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python tools\diagnostics\untargeted_alignment_guardrails.py `
  --baseline-targeted-comparison output\diagnostics\drift_soft_edge_85raw_20260513\baseline_gt_5medc\comparison.csv `
  --candidate-targeted-comparison output\diagnostics\drift_soft_edge_85raw_20260513\gt_5medc\comparison.csv `
  --target-label 5-medC `
  --targeted-comparison-csv output\diagnostics\drift_soft_edge_85raw_20260513\targeted_compare_5medc.csv

uv run python tools\diagnostics\untargeted_alignment_guardrails.py `
  --baseline-targeted-comparison output\diagnostics\drift_soft_edge_85raw_20260513\baseline_gt_5hmdc\comparison.csv `
  --candidate-targeted-comparison output\diagnostics\drift_soft_edge_85raw_20260513\gt_5hmdc\comparison.csv `
  --target-label 5-hmdC `
  --targeted-comparison-csv output\diagnostics\drift_soft_edge_85raw_20260513\targeted_compare_5hmdc.csv
```

Expected:

- `targeted_compare_5medc.csv` has no `FAIL` row.
- `targeted_compare_5hmdc.csv` has no `FAIL` row.

- [ ] **Step 6: Compute 85 RAW guardrail comparison**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python tools\diagnostics\untargeted_alignment_guardrails.py `
  --alignment-dir output\alignment\gt_audit_checkpoint_85raw_validation_20260512 `
  --output-json output\diagnostics\drift_soft_edge_85raw_20260513\baseline_guardrails.json `
  --case-summary-tsv output\diagnostics\drift_soft_edge_85raw_20260513\baseline_case_assertion_summary.tsv

uv run python tools\diagnostics\untargeted_alignment_guardrails.py `
  --alignment-dir output\alignment\drift_soft_edge_85raw_20260513 `
  --output-json output\diagnostics\drift_soft_edge_85raw_20260513\candidate_guardrails.json `
  --case-summary-tsv output\diagnostics\drift_soft_edge_85raw_20260513\case_assertion_summary.tsv

uv run python tools\diagnostics\untargeted_alignment_guardrails.py `
  --baseline-dir output\alignment\gt_audit_checkpoint_85raw_validation_20260512 `
  --candidate-dir output\alignment\drift_soft_edge_85raw_20260513 `
  --comparison-csv output\diagnostics\drift_soft_edge_85raw_20260513\guardrail_comparison.csv
```

Expected pass rules:

- `negative_8oxodg_production_families == 0`.
- `duplicate_only_families` candidate <= baseline.
- `zero_present_families` candidate <= baseline.
- `high_backfill_dependency_families` candidate <= baseline.
- `targeted_compare_5medc.csv` and `targeted_compare_5hmdc.csv` have no `FAIL` rows.
- Timing is recorded but has no correctness pass/fail in this round.

- [ ] **Step 7: Stop on guardrail regression**

If `guardrail_comparison.csv` contains any `FAIL`, stop and inspect:

```powershell
Import-Csv output\diagnostics\drift_soft_edge_85raw_20260513\guardrail_comparison.csv | Where-Object { $_.status -eq 'FAIL' }
```

Expected for acceptance: no rows.

- [ ] **Step 8: Commit validation note if a tracked note is created**

If a concise tracked validation note is added, commit it:

```powershell
git status --short
git add output\diagnostics\drift_soft_edge_85raw_20260513
git commit -m "test: record 85raw drift edge validation"
```

If generated outputs are untracked and ignored, skip this commit.

---

### Task 9: Final Review and Commit Hygiene

**Files:**
- No new files unless review fixes are needed.

- [ ] **Step 1: Check production code does not branch on target labels**

Run:

```powershell
rg -n "5-medC|5-hmdC|8-oxodG|8-oxo|15N5|d3-5" xic_extractor scripts
```

Expected:

- Matches are allowed in diagnostics, tests, or comments that explicitly refer to validation fixtures.
- No match in production alignment scoring or family construction logic that changes merge decisions by target label.

- [ ] **Step 2: Check scoring payload does not expose ISTD labels**

Run:

```powershell
rg -n "istd_label|target_label|Confidence|allowed|0.25" xic_extractor\alignment
```

Expected:

- `drift_evidence.py` may use private local variables such as `istd_label` while reading the workbook.
- `SampleDriftEvidence`, `DriftEvidenceLookup`, `edge_scoring.py`, and `owner_clustering.py` must not expose or consume target labels or ISTD labels.
- No implementation copies targeted `allowed +/- 0.25 min` tolerance.

- [ ] **Step 3: Check Sample_Type remains diagnostic-only**

Run:

```powershell
rg -n "Sample_Type|sample_type|Group" xic_extractor\alignment scripts\run_alignment.py
```

Expected:

- No matches in `xic_extractor\alignment\edge_scoring.py`.
- No matches in `xic_extractor\alignment\owner_clustering.py`.
- No matches in `xic_extractor\alignment\pipeline.py` that affect scoring, clustering, or family construction.
- Matches are allowed only in diagnostics/provenance adapters that do not feed edge scoring decisions.

- [ ] **Step 4: Run final focused test shard**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_alignment_edge_scoring.py tests\test_alignment_drift_evidence.py tests\test_alignment_owner_clustering.py tests\test_alignment_debug_writer.py tests\test_alignment_output_levels.py tests\test_alignment_pipeline.py tests\test_run_alignment.py tests\test_untargeted_alignment_guardrails.py tests\test_alignment_boundaries.py tests\test_targeted_gt_alignment_audit.py -q
```

Expected: PASS.

- [ ] **Step 5: Inspect git status**

Run:

```powershell
git status --short
```

Expected:

- Only intentional source, tests, diagnostics, docs, or tracked validation note changes remain.
- Generated untracked output directories may remain uncommitted if ignored by repo policy.

- [ ] **Step 6: Commit final fixes if needed**

If Step 1 through Step 5 caused source/test/doc fixes:

```powershell
git add xic_extractor scripts tools tests docs
git commit -m "chore: finalize untargeted drift edge validation"
```

If no files changed after earlier task commits, skip this commit.

## Stop Conditions

Stop implementation and ask for direction if any of these happen:

- A positive checkpoint improves only after production logic reads target labels.
- `8-oxodG` has any accepted production family in candidate guardrails.
- Weak edges are used to merge production families.
- Rescued or backfilled cells create or bridge owner families.
- Case2 is forced into a single production family when the evidence remains ambiguous.
- 8 RAW validation cannot prove `raw_workers == 8`; mark validation `SKIP`, not `PASS`.
- 85 RAW increases duplicate-only, zero-present, high-backfill-dependency, positive fixture split, or positive fixture miss metrics.
