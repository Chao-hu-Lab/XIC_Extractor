# Identity Coherence Engineering Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the V0.4 engineering preflight slice: process-safe identity-coherence payloads, a no-RAW Windows spawn smoke test, a firewall spoof fixture, and engineering Go/No-Go summary rows.

**Architecture:** This slice stays inside the already-built identity-coherence diagnostic surface and does not call RAW readers, XIC extraction, Backfill, workbook/report writers, or alignment orchestration. It adds pickleable payload contracts and validation fixtures that must pass before a later opt-in pre-Backfill diagnostic adapter is allowed to schedule real RAW/XIC work.

**Tech Stack:** Python 3.11+, dataclasses, `multiprocessing.get_context("spawn")`, existing `identity_coherence` domain/output models, TSV/JSONL test fixtures, `pytest`, `ruff`.

---

## Required Working Directory

Run every command from this worktree:

```powershell
Set-Location "C:\Users\user\Desktop\XIC_Extractor\.worktrees\untargeted-backfill-logic-reset"
```

Because this worktree may trip Git safe-directory checks under the sandbox user, set these environment variables before every `git` command in this plan:

```powershell
$env:GIT_CONFIG_COUNT = "1"
$env:GIT_CONFIG_KEY_0 = "safe.directory"
$env:GIT_CONFIG_VALUE_0 = (Get-Location).Path
```

Before starting Task 1, record the base commit:

```powershell
$env:GIT_CONFIG_COUNT = "1"
$env:GIT_CONFIG_KEY_0 = "safe.directory"
$env:GIT_CONFIG_VALUE_0 = (Get-Location).Path
git status --short
git branch --show-current
git rev-parse HEAD
```

Use that exact hash as `<base_commit_before_task1>` in the final scope guard.
If `git branch --show-current` returns `main` or `master`, stop. This plan must
not commit directly to the primary branch.

The working tree must be clean before Task 1 starts. If `git status --short`
prints any tracked, staged, or untracked file, stop and classify it with the
user before continuing. Do not stage unrelated user edits into this plan's
task commits.

Before every task commit, rerun `git status --short` and verify that the only
dirty paths are the files explicitly listed for that task. If any other path is
dirty, stop before `git add`.

## Current State

Already implemented:

- normalized fragment identity request builder;
- request-vs-candidate matcher;
- seed gate;
- RT center estimation;
- tier 1 / tier 2 / tier 3 cell evidence;
- row evaluator and decision summary;
- frozen TSV schema constants and schema parity tests;
- output writer for requests, decisions, cell evidence, controls, and summary;
- TSV controls manifest reader;
- positive-control evaluator;
- identity-decoy evaluator.

Not implemented yet:

- `IdentityCoherenceTraceRequest` / `IdentityCoherenceTraceResult` process payloads;
- `IdentityCoherenceResult` model-level process result container;
- no-RAW Windows spawn smoke for identity-coherence payloads;
- required `tests/fixtures/identity_coherence/firewall_spoof/` fixture;
- engineering Go/No-Go rows in `untargeted_identity_coherence_summary.md`;
- opt-in pipeline/CLI/RAW retrieval adapter.

This plan implements the first five items only. It intentionally leaves pipeline/CLI/RAW retrieval to the next slice.

## Scope Boundary

In scope:

- Add pickleable payload dataclasses under `xic_extractor/alignment/identity_coherence/models.py`.
- Add a tiny importable no-RAW process smoke worker under `xic_extractor/alignment/identity_coherence/process_payload.py`.
- Add tests proving payload validation, pickle round-trip, and Windows `spawn` process round-trip.
- Add engineering preflight fields to `IdentityCoherenceOutputContext` and render an explicit Engineering Go/No-Go table.
- Add the required firewall spoof fixture directory and a fixture-level A/B test
  proving spoofed post-Backfill columns can be detected as present while the
  baseline decision/count/basis projection remains stable.
- Re-export the new public payload surface through `xic_extractor.alignment.identity_coherence`.

Out of scope:

- RAW readers, vendor APIs, `ms1_index_source`, `source_for_owner_backfill_backend`, or any real XIC extraction.
- `scripts/run_alignment.py` CLI flags.
- `xic_extractor/alignment/pipeline.py` orchestration.
- `owner_backfill`, Backfill area/status, final matrix, workbook, HTML report, or downstream background/QC filtering.
- Real 8RAW interpretation. This slice produces engineering preflight tests only.

## File Structure

- Modify `xic_extractor/alignment/identity_coherence/models.py`
  - Add process-safe payload dataclasses:
    - `IdentityCoherenceResult`
    - `IdentityCoherenceTraceRequest`
    - `IdentityCoherenceTraceResult`
  - Add `EngineeringConfig` and wire it into `IdentityCoherenceConfig`.
- Create `xic_extractor/alignment/identity_coherence/process_payload.py`
  - Own the importable no-RAW spawn smoke worker for identity-coherence payloads.
  - Do not import process backends, RAW readers, CLI, workbook, report, or alignment pipeline code.
- Modify `xic_extractor/alignment/identity_coherence/output.py`
  - Add engineering preflight fields to `IdentityCoherenceOutputContext`.
  - Render `## Engineering Go / No-Go` in the summary.
- Modify `xic_extractor/alignment/identity_coherence/__init__.py`
  - Re-export the new payload dataclasses.
  - Do not re-export the no-RAW smoke worker; it is an internal preflight helper,
    not a public facade contract.
- Create `tests/alignment/identity_coherence/test_process_payload.py`
  - Test payload validation, pickleability, and Windows spawn round-trip.
- Create `tests/fixtures/identity_coherence/firewall_spoof/pre_backfill_owner_state.jsonl`
  - Minimal test fixture describing one would-primary and one Review-only baseline decision.
- Create `tests/fixtures/identity_coherence/firewall_spoof/post_backfill_spoof.tsv`
  - Post-Backfill spoof fields that must be marked seen but never used.
- Create `tests/fixtures/identity_coherence/firewall_spoof/expected_decisions.tsv`
  - Expected A/B-stable decision/count/basis fields.
- Create `tests/alignment/identity_coherence/test_firewall_fixture.py`
  - Test fixture presence and A/B invariants.
- Modify `tests/alignment/identity_coherence/test_output_writer.py`
  - Test engineering Go/No-Go summary rendering.
- Modify `tests/alignment/identity_coherence/test_schema_contract.py`
  - Test facade exports and dependency boundary.

## Design Rules

- Payload dataclasses are typed process contracts, not RAW adapters.
- The smoke worker must not read a RAW file; it only proves `spawn` can import the identity-coherence module and round-trip pickleable payloads.
- `IdentityCoherenceResult` is a model-level container. It does not replace `IdentityCoherenceRowResult`; it gives future process adapters a domain-safe return shape without importing `output.py`.
- Firewall spoof data is validation-only. In this slice it is a fixture contract,
  not the future production adapter. The test-local adapter may set
  `forbidden_evidence_seen = true`, but it must never set
  `forbidden_evidence_used = true` and must never alter decision, coherent
  counts, seed gate, or cell identity basis. Production adapter enforcement
  belongs to the later opt-in retrieval/adapter slice.
- Engineering Go/No-Go rows are summary/audit rows. They do not change identity decisions.
- Synthetic Go/No-Go tests prove renderer/preflight semantics only. A Proceed
  row in this slice is not 8RAW or 85RAW data clearance.
- If a later implementation needs real trace retrieval, it must create a separate adapter plan and keep RAW/XIC calls outside `identity_coherence` domain code.

---

## Task 1: Process-Safe Payload Dataclasses

**Files:**

- Modify: `xic_extractor/alignment/identity_coherence/models.py`
- Modify: `tests/alignment/identity_coherence/test_schema_contract.py`
- Create: `tests/alignment/identity_coherence/test_process_payload.py`

- [ ] **Step 1: Write failing tests for payload validation and pickle round-trip**

Create `tests/alignment/identity_coherence/test_process_payload.py` with:

```python
import pickle
from dataclasses import replace

import pytest

from tests.alignment.identity_coherence.output_fixtures import output_record
from xic_extractor.alignment.identity_coherence.models import (
    CandidateTrace,
    IdentityCoherenceResult,
    IdentityCoherenceTraceRequest,
    IdentityCoherenceTraceResult,
)


def _trace_request() -> IdentityCoherenceTraceRequest:
    return IdentityCoherenceTraceRequest(
        decision_id="DEC-1",
        request_id="REQ-1",
        sample_id="RAW-2",
        candidate_id="CAND-2",
        precursor_mz=500.0,
        ppm_tolerance=10.0,
        rt_min=4.0,
        rt_max=6.0,
    )


def test_trace_request_rejects_empty_identifiers() -> None:
    with pytest.raises(ValueError, match="decision_id must be non-empty"):
        IdentityCoherenceTraceRequest(
            decision_id="",
            request_id="REQ-1",
            sample_id="RAW-2",
            candidate_id="CAND-2",
            precursor_mz=500.0,
            ppm_tolerance=10.0,
            rt_min=4.0,
            rt_max=6.0,
        )


def test_trace_request_rejects_nonfinite_or_invalid_windows() -> None:
    with pytest.raises(ValueError, match="precursor_mz must be finite positive"):
        replace(_trace_request(), precursor_mz=float("nan"))

    with pytest.raises(ValueError, match="ppm_tolerance must be finite positive"):
        replace(_trace_request(), ppm_tolerance=0.0)

    with pytest.raises(ValueError, match="rt_min must be <= rt_max"):
        replace(_trace_request(), rt_min=7.0, rt_max=6.0)


def test_trace_result_rejects_inconsistent_trace_point_count() -> None:
    trace = CandidateTrace(rt_min=(4.0, 5.0), intensity=(10.0, 20.0))

    with pytest.raises(ValueError, match="xic_point_count must equal trace length"):
        IdentityCoherenceTraceResult(
            request=_trace_request(),
            trace=trace,
            status="pass",
            raw_xic_request_count=1,
            raw_chromatogram_call_count=1,
            xic_point_count=3,
            elapsed_sec=0.0,
        )


def test_trace_result_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="unsupported trace result status"):
        IdentityCoherenceTraceResult(
            request=_trace_request(),
            trace=None,
            status="rescued",
            raw_xic_request_count=0,
            raw_chromatogram_call_count=0,
            xic_point_count=0,
            elapsed_sec=0.0,
        )


def test_identity_coherence_result_rejects_join_mismatches() -> None:
    record = output_record()
    mismatched_decision = replace(
        record.row_result.decision,
        decision_id="OTHER-DECISION",
    )

    with pytest.raises(ValueError, match="decision_id mismatch"):
        IdentityCoherenceResult(
            request=record.seed_gate.resolved_request,
            decision=mismatched_decision,
            cells=record.row_result.cells,
        )


def test_identity_coherence_payloads_are_pickleable() -> None:
    record = output_record()
    result = IdentityCoherenceResult(
        request=record.seed_gate.resolved_request,
        decision=record.row_result.decision,
        cells=record.row_result.cells,
    )
    trace_result = IdentityCoherenceTraceResult(
        request=_trace_request(),
        trace=CandidateTrace(rt_min=(4.0, 5.0), intensity=(0.0, 1.0)),
        status="pass",
        raw_xic_request_count=1,
        raw_chromatogram_call_count=1,
        xic_point_count=2,
        elapsed_sec=0.0,
    )

    assert pickle.loads(pickle.dumps(result)) == result
    assert pickle.loads(pickle.dumps(trace_result)) == trace_result
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_process_payload.py -q
```

Expected: FAIL with import errors for `IdentityCoherenceResult`, `IdentityCoherenceTraceRequest`, and `IdentityCoherenceTraceResult`.

- [ ] **Step 3: Add payload dataclasses**

In `xic_extractor/alignment/identity_coherence/models.py`, add these helpers near the top after imports:

```python
_TRACE_RESULT_STATUSES = frozenset(
    {
        "pass",
        "blocked_infrastructure",
        "data_quality_reject",
        "not_assessed",
    }
)


def _require_non_empty_text(value: object, field_name: str) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValueError(f"{field_name} must be non-empty")
    return text


def _require_finite_positive(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field_name} must be finite positive")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric <= 0:
        raise ValueError(f"{field_name} must be finite positive")
    return numeric


def _require_finite_number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field_name} must be finite")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{field_name} must be finite")
    return numeric


def _require_finite_nonnegative(value: object, field_name: str) -> float:
    numeric = _require_finite_number(value, field_name)
    if numeric < 0:
        raise ValueError(f"{field_name} must be nonnegative")
    return numeric


def _require_nonnegative_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a nonnegative integer")
    return value
```

Add `import math` at the top of `models.py`.

Add these dataclasses after `CandidateTrace` and before `IdentityCoherenceConfig`:

```python
@dataclass(frozen=True)
class EngineeringConfig:
    max_infrastructure_blocked_fraction: float = 0.05
    max_projected_85raw_identity_xic_requests: int | None = None

    def __post_init__(self) -> None:
        blocked_fraction = _require_finite_nonnegative(
            self.max_infrastructure_blocked_fraction,
            "max_infrastructure_blocked_fraction",
        )
        if blocked_fraction > 1.0:
            raise ValueError("max_infrastructure_blocked_fraction must be <= 1")
        object.__setattr__(
            self,
            "max_infrastructure_blocked_fraction",
            blocked_fraction,
        )

        budget = self.max_projected_85raw_identity_xic_requests
        if budget is None:
            return
        if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
            raise ValueError(
                "max_projected_85raw_identity_xic_requests must be nonnegative"
            )


@dataclass(frozen=True)
class IdentityCoherenceTraceRequest:
    decision_id: str
    request_id: str
    sample_id: str
    candidate_id: str
    precursor_mz: float
    ppm_tolerance: float
    rt_min: float
    rt_max: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "decision_id",
            _require_non_empty_text(self.decision_id, "decision_id"),
        )
        object.__setattr__(
            self,
            "request_id",
            _require_non_empty_text(self.request_id, "request_id"),
        )
        object.__setattr__(
            self,
            "sample_id",
            _require_non_empty_text(self.sample_id, "sample_id"),
        )
        object.__setattr__(
            self,
            "candidate_id",
            _require_non_empty_text(self.candidate_id, "candidate_id"),
        )
        object.__setattr__(
            self,
            "precursor_mz",
            _require_finite_positive(self.precursor_mz, "precursor_mz"),
        )
        object.__setattr__(
            self,
            "ppm_tolerance",
            _require_finite_positive(self.ppm_tolerance, "ppm_tolerance"),
        )
        rt_min = _require_finite_number(self.rt_min, "rt_min")
        rt_max = _require_finite_number(self.rt_max, "rt_max")
        if rt_min > rt_max:
            raise ValueError("rt_min must be <= rt_max")
        object.__setattr__(self, "rt_min", rt_min)
        object.__setattr__(self, "rt_max", rt_max)


@dataclass(frozen=True)
class IdentityCoherenceTraceResult:
    request: IdentityCoherenceTraceRequest
    trace: CandidateTrace | None
    status: str
    blocked_reason: str = ""
    raw_xic_request_count: int = 0
    raw_chromatogram_call_count: int = 0
    xic_point_count: int = 0
    elapsed_sec: float = 0.0

    def __post_init__(self) -> None:
        status = _require_non_empty_text(self.status, "status")
        if status not in _TRACE_RESULT_STATUSES:
            raise ValueError(f"unsupported trace result status: {status}")
        object.__setattr__(self, "status", status)
        object.__setattr__(
            self,
            "blocked_reason",
            "" if self.blocked_reason is None else str(self.blocked_reason).strip(),
        )
        object.__setattr__(
            self,
            "raw_xic_request_count",
            _require_nonnegative_int(
                self.raw_xic_request_count,
                "raw_xic_request_count",
            ),
        )
        object.__setattr__(
            self,
            "raw_chromatogram_call_count",
            _require_nonnegative_int(
                self.raw_chromatogram_call_count,
                "raw_chromatogram_call_count",
            ),
        )
        point_count = _require_nonnegative_int(self.xic_point_count, "xic_point_count")
        if self.trace is not None and point_count != len(self.trace.rt_min):
            raise ValueError("xic_point_count must equal trace length")
        object.__setattr__(self, "xic_point_count", point_count)
        elapsed = _require_finite_number(self.elapsed_sec, "elapsed_sec")
        if elapsed < 0:
            raise ValueError("elapsed_sec must be nonnegative")
        object.__setattr__(self, "elapsed_sec", elapsed)


@dataclass(frozen=True)
class IdentityCoherenceResult:
    request: IdentityCoherenceRequest
    decision: IdentityDecisionSummary
    cells: tuple[CellEvidenceResult, ...]

    def __post_init__(self) -> None:
        if self.request.decision_id != self.decision.decision_id:
            raise ValueError("decision_id mismatch between request and decision")
        if self.request.seed_candidate_id != self.decision.seed_candidate_id:
            raise ValueError(
                "seed_candidate_id mismatch between request and decision"
            )
        if self.request.seed_sample != self.decision.seed_sample:
            raise ValueError("seed_sample mismatch between request and decision")
        for cell in self.cells:
            if cell.decision_id != self.decision.decision_id:
                raise ValueError("decision_id mismatch between cell and decision")
            if cell.identity_family_id != self.decision.identity_family_id:
                raise ValueError(
                    "identity_family_id mismatch between cell and decision"
                )
```

Modify `IdentityCoherenceConfig` so it has an engineering group:

```python
@dataclass(frozen=True)
class IdentityCoherenceConfig:
    seed_gate: SeedGateConfig = field(default_factory=SeedGateConfig)
    promotion: PromotionConfig = field(default_factory=PromotionConfig)
    rt: RtConfig = field(default_factory=RtConfig)
    shape: ShapeConfig = field(default_factory=ShapeConfig)
    width: WidthConfig = field(default_factory=WidthConfig)
    engineering: EngineeringConfig = field(default_factory=EngineeringConfig)
```

- [ ] **Step 4: Add config and facade tests**

Append to `tests/alignment/identity_coherence/test_schema_contract.py`:

```python
def test_identity_coherence_config_exposes_engineering_group():
    from xic_extractor.alignment.identity_coherence.models import (
        EngineeringConfig,
        IdentityCoherenceConfig,
    )

    config = IdentityCoherenceConfig()

    assert isinstance(config.engineering, EngineeringConfig)
    assert config.engineering.max_infrastructure_blocked_fraction == 0.05
    assert config.engineering.max_projected_85raw_identity_xic_requests is None
```

Do not add facade assertions yet; Task 2 updates `__init__.py` together with the process smoke worker.

- [ ] **Step 5: Run focused tests**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_process_payload.py tests\alignment\identity_coherence\test_schema_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
$env:GIT_CONFIG_COUNT = "1"
$env:GIT_CONFIG_KEY_0 = "safe.directory"
$env:GIT_CONFIG_VALUE_0 = (Get-Location).Path
git status --short
git add xic_extractor\alignment\identity_coherence\models.py tests\alignment\identity_coherence\test_process_payload.py tests\alignment\identity_coherence\test_schema_contract.py
git commit -m "feat: add identity coherence process payload models"
```

---

## Task 2: No-RAW Spawn Smoke Worker

**Files:**

- Create: `xic_extractor/alignment/identity_coherence/process_payload.py`
- Modify: `xic_extractor/alignment/identity_coherence/__init__.py`
- Modify: `tests/alignment/identity_coherence/test_process_payload.py`
- Modify: `tests/alignment/identity_coherence/test_schema_contract.py`

- [ ] **Step 1: Write failing spawn smoke test**

Merge these imports into the existing top import block in
`tests/alignment/identity_coherence/test_process_payload.py`. Do not append
imports after test functions; that would violate ruff `E402`.

```python
import concurrent.futures
import multiprocessing

from xic_extractor.alignment.identity_coherence.process_payload import (
    identity_coherence_trace_payload_smoke_worker,
)
```

Then append only this test function to the end of the file:

```python
def test_spawn_round_trips_identity_coherence_trace_payload() -> None:
    context = multiprocessing.get_context("spawn")
    request = _trace_request()

    with concurrent.futures.ProcessPoolExecutor(
        max_workers=1,
        mp_context=context,
    ) as executor:
        future = executor.submit(
            identity_coherence_trace_payload_smoke_worker,
            request,
        )
        result = future.result(timeout=30)

    assert result.request == request
    assert result.status == "pass"
    assert result.raw_xic_request_count == 0
    assert result.raw_chromatogram_call_count == 0
    assert result.xic_point_count == 2
    assert result.trace is not None
    assert result.trace.rt_min == (4.0, 6.0)
    assert result.trace.intensity == (0.0, 0.0)
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_process_payload.py::test_spawn_round_trips_identity_coherence_trace_payload -q
```

Expected: FAIL with `ModuleNotFoundError` for `identity_coherence.process_payload`.

- [ ] **Step 3: Add process payload smoke worker**

Create `xic_extractor/alignment/identity_coherence/process_payload.py`:

```python
from __future__ import annotations

from .models import (
    CandidateTrace,
    IdentityCoherenceTraceRequest,
    IdentityCoherenceTraceResult,
)


def identity_coherence_trace_payload_smoke_worker(
    request: IdentityCoherenceTraceRequest,
) -> IdentityCoherenceTraceResult:
    """Round-trip an identity-coherence trace request through a spawn worker.

    This worker is intentionally no-RAW. It proves the diagnostic payload
    boundary is pickleable before a later adapter schedules vendor XIC work.
    """

    trace = CandidateTrace(
        rt_min=(request.rt_min, request.rt_max),
        intensity=(0.0, 0.0),
    )
    return IdentityCoherenceTraceResult(
        request=request,
        trace=trace,
        status="pass",
        raw_xic_request_count=0,
        raw_chromatogram_call_count=0,
        xic_point_count=len(trace.rt_min),
        elapsed_sec=0.0,
    )
```

- [ ] **Step 4: Re-export payload dataclasses only**

In `xic_extractor/alignment/identity_coherence/__init__.py`, import the new names:

```python
from .models import (
    CandidateIdentityMatch,
    CandidateTrace,
    CellCandidateEvidence,
    CellEvidenceResult,
    CidNeutralLossConstraint,
    EngineeringConfig,
    FragmentIdentity,
    IdentityCoherenceConfig,
    IdentityCoherenceRequest,
    IdentityCoherenceResult,
    IdentityCoherenceTraceRequest,
    IdentityCoherenceTraceResult,
    IdentityDecisionSummary,
    PrototypeWidthResult,
    RtCenterResult,
    SeedCandidateEvidence,
    SeedGateConfig,
    SeedGateResult,
    ShapeComparisonResult,
    ShapeConfig,
    ShapeReferenceResult,
    WidthAssessmentResult,
    WidthConfig,
)
```

Add these strings to `__all__`:

```python
"EngineeringConfig",
"IdentityCoherenceResult",
"IdentityCoherenceTraceRequest",
"IdentityCoherenceTraceResult",
```

Do not import or include `identity_coherence_trace_payload_smoke_worker` in
`__all__`. Tests may import it from
`xic_extractor.alignment.identity_coherence.process_payload`, but the package
facade should expose only stable payload models.

- [ ] **Step 5: Add facade export assertions**

Append to `tests/alignment/identity_coherence/test_schema_contract.py`:

```python
def test_identity_coherence_facade_exports_process_payload_surface():
    import xic_extractor.alignment.identity_coherence as identity_coherence

    assert identity_coherence.EngineeringConfig is not None
    assert identity_coherence.IdentityCoherenceResult is not None
    assert identity_coherence.IdentityCoherenceTraceRequest is not None
    assert identity_coherence.IdentityCoherenceTraceResult is not None
    assert "EngineeringConfig" in identity_coherence.__all__
    assert "IdentityCoherenceResult" in identity_coherence.__all__
    assert "IdentityCoherenceTraceRequest" in identity_coherence.__all__
    assert "IdentityCoherenceTraceResult" in identity_coherence.__all__
```

Also add a dependency-boundary test for the new helper module:

```python
def test_identity_coherence_process_payload_stays_no_raw_boundary() -> None:
    source = Path(
        "xic_extractor/alignment/identity_coherence/process_payload.py"
    ).read_text(encoding="utf-8")
    forbidden_snippets = (
        "raw_reader",
        "ms1_index_source",
        "owner_backfill",
        "alignment.pipeline",
        "scripts.run_alignment",
        "source_for_owner_backfill_backend",
        "xic_extractor.output",
        "workbook",
        "report",
    )

    for snippet in forbidden_snippets:
        assert snippet not in source
```

If `Path` is not already imported in `test_schema_contract.py`, merge
`from pathlib import Path` into the top import block.

- [ ] **Step 6: Run focused tests**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_process_payload.py tests\alignment\identity_coherence\test_schema_contract.py -q
```

Expected: PASS. If Windows sandbox process spawning fails with `PermissionError:
[WinError 5]`, Codex workers should rerun the exact same `uv run pytest ...`
command with shell escalation and should not alter test selection. Human
PowerShell fallback: open a normal PowerShell in the required worktree and run
the exact same command after the same env setup. Record both results in the
final implementation note.

- [ ] **Step 7: Commit**

Run:

```powershell
$env:GIT_CONFIG_COUNT = "1"
$env:GIT_CONFIG_KEY_0 = "safe.directory"
$env:GIT_CONFIG_VALUE_0 = (Get-Location).Path
git status --short
git add xic_extractor\alignment\identity_coherence\process_payload.py xic_extractor\alignment\identity_coherence\__init__.py
git add tests\alignment\identity_coherence\test_process_payload.py tests\alignment\identity_coherence\test_schema_contract.py
git commit -m "test: add identity coherence spawn payload smoke"
```

---

## Task 3: Engineering Go/No-Go Summary Rows

**Files:**

- Modify: `xic_extractor/alignment/identity_coherence/output.py`
- Modify: `tests/alignment/identity_coherence/test_output_writer.py`

- [ ] **Step 1: Write failing summary tests**

Append to `tests/alignment/identity_coherence/test_output_writer.py`:

```python
def test_summary_renders_engineering_go_no_go_rows():
    record = output_record()
    markdown = render_identity_coherence_summary(
        (record,),
        context=IdentityCoherenceOutputContext(
            command="pytest",
            mode="inline_pre_backfill",
            input_source="pre_backfill_owner_state.jsonl",
            firewall_fixture_status="pass",
            spawn_payload_smoke_status="pass",
            max_infrastructure_blocked_fraction=0.05,
            projected_85raw_identity_request_count=10,
            max_projected_85raw_identity_xic_requests=20,
        ),
    )

    assert "## Engineering Go / No-Go" in markdown
    assert "| evidence_firewall | Proceed |" in markdown
    assert "| firewall_fixture | Proceed |" in markdown
    assert "| spawn_payload_smoke | Proceed |" in markdown
    assert "| infrastructure_blocked_fraction | Proceed |" in markdown
    assert "| projected_85raw_identity_xic_requests | Proceed |" in markdown


def test_summary_marks_engineering_no_go_when_85raw_budget_missing():
    markdown = render_identity_coherence_summary(
        (output_record(),),
        context=IdentityCoherenceOutputContext(
            command="pytest",
            mode="inline_pre_backfill",
            input_source="pre_backfill_owner_state.jsonl",
            firewall_fixture_status="pass",
            spawn_payload_smoke_status="pass",
            projected_85raw_identity_request_count=10,
            max_projected_85raw_identity_xic_requests=None,
        ),
    )

    assert (
        "| projected_85raw_identity_xic_requests | No-Go for 85RAW | "
        "`max_projected_85raw_identity_xic_requests` not provided |"
    ) in markdown


def test_summary_marks_infrastructure_pivot_when_blocked_fraction_exceeds_limit():
    record = output_record()
    blocked_decision = replace(
        record.row_result.decision,
        infrastructure_blocked_sample_count=2,
    )
    blocked_record = replace(
        record,
        row_result=replace(record.row_result, decision=blocked_decision),
    )

    markdown = render_identity_coherence_summary(
        (blocked_record,),
        context=IdentityCoherenceOutputContext(
            command="pytest",
            mode="inline_pre_backfill",
            input_source="pre_backfill_owner_state.jsonl",
            max_infrastructure_blocked_fraction=0.05,
        ),
    )

    assert (
        "| infrastructure_blocked_fraction | Pivot | "
        "`2 / 8 = 0.25` exceeds `0.05` |"
    ) in markdown


def test_summary_uses_row_level_denominator_for_blocked_fraction():
    record = output_record()
    first_decision = replace(
        record.row_result.decision,
        total_coherent_sample_count=4,
        coherent_fraction=0.5,
        infrastructure_blocked_sample_count=1,
    )
    second_decision = replace(
        record.row_result.decision,
        decision_id="DEC-SECOND",
        identity_family_id="IDF-SECOND",
        total_coherent_sample_count=4,
        coherent_fraction=0.5,
        infrastructure_blocked_sample_count=1,
    )
    first_record = replace(
        record,
        row_result=replace(record.row_result, decision=first_decision),
    )
    second_record = replace(
        record,
        row_result=replace(record.row_result, decision=second_decision),
    )

    markdown = render_identity_coherence_summary(
        (first_record, second_record),
        context=IdentityCoherenceOutputContext(
            command="pytest",
            mode="inline_pre_backfill",
            input_source="pre_backfill_owner_state.jsonl",
            max_infrastructure_blocked_fraction=0.2,
        ),
    )

    assert (
        "| infrastructure_blocked_fraction | Proceed | "
        "`2 / 16 = 0.125` <= `0.2` |"
    ) in markdown


def test_summary_rejects_forbidden_evidence_used_before_go_no_go_render():
    record = output_record()
    forbidden_decision = replace(
        record.row_result.decision,
        forbidden_evidence_used=True,
    )
    forbidden_record = replace(
        record,
        row_result=replace(record.row_result, decision=forbidden_decision),
    )

    with pytest.raises(ValueError, match="forbidden_evidence_used"):
        render_identity_coherence_summary(
            (forbidden_record,),
            context=IdentityCoherenceOutputContext(
                command="pytest",
                mode="inline_pre_backfill",
                input_source="pre_backfill_owner_state.jsonl",
            ),
        )
```

`test_output_writer.py` already imports `replace` at the top of the file. Do
not add `from dataclasses import replace` in the appended block.

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_output_writer.py -q
```

Expected: FAIL because `IdentityCoherenceOutputContext` lacks the engineering fields and summary lacks `## Engineering Go / No-Go`.

- [ ] **Step 3: Extend output context**

In `xic_extractor/alignment/identity_coherence/output.py`, modify `IdentityCoherenceOutputContext`:

```python
@dataclass(frozen=True)
class IdentityCoherenceOutputContext:
    command: str
    mode: str
    input_source: str
    input_hashes: tuple[tuple[str, str], ...] = ()
    control_manifest_path: str = "not_provided"
    raw_xic_request_count: int | None = None
    xic_point_count: int | None = None
    projected_85raw_identity_request_count: int | None = None
    max_projected_85raw_identity_xic_requests: int | None = None
    max_infrastructure_blocked_fraction: float = 0.05
    firewall_fixture_status: str = "not_assessed"
    spawn_payload_smoke_status: str = "not_assessed"
```

- [ ] **Step 4: Add engineering Go/No-Go helpers**

In `output.py`, add these helper functions near `_counter_table`:

```python
def _engineering_go_no_go_rows(
    decision_rows: Sequence[IdentityDecisionSummary],
    *,
    context: IdentityCoherenceOutputContext,
    assessed_sample_total: int,
) -> list[str]:
    blocked_count = _sum_decision_field(
        decision_rows,
        "infrastructure_blocked_sample_count",
    )
    blocked_fraction = (
        0.0 if assessed_sample_total <= 0 else blocked_count / assessed_sample_total
    )
    forbidden_used_count = sum(
        1 for row in decision_rows if row.forbidden_evidence_used
    )
    firewall_row = (
        "| evidence_firewall | Proceed | "
        "`promotion_used_forbidden_evidence = false` |"
        if forbidden_used_count == 0
        else (
            "| evidence_firewall | No-Go | "
            f"`forbidden_evidence_used_count = {forbidden_used_count}` |"
        )
    )
    rows = [
        "| Check | Decision | Basis |",
        "| --- | --- | --- |",
        firewall_row,
        _status_row(
            "firewall_fixture",
            context.firewall_fixture_status,
            pass_basis="firewall A/B fixture passed",
        ),
        _status_row(
            "spawn_payload_smoke",
            context.spawn_payload_smoke_status,
            pass_basis="spawn payload smoke passed",
        ),
    ]
    blocked_basis = (
        f"`{blocked_count} / {assessed_sample_total} = "
        f"{blocked_fraction:.12g}`"
    )
    if blocked_fraction <= context.max_infrastructure_blocked_fraction:
        rows.append(
            "| infrastructure_blocked_fraction | Proceed | "
            f"{blocked_basis} <= `{context.max_infrastructure_blocked_fraction}` |"
        )
    else:
        rows.append(
            "| infrastructure_blocked_fraction | Pivot | "
            f"{blocked_basis} exceeds `{context.max_infrastructure_blocked_fraction}` |"
        )

    projected = context.projected_85raw_identity_request_count
    max_projected = context.max_projected_85raw_identity_xic_requests
    if projected is None:
        rows.append(
            "| projected_85raw_identity_xic_requests | No-Go for 85RAW | "
            "`projected_85raw_identity_request_count` not assessed |"
        )
    elif max_projected is None:
        rows.append(
            "| projected_85raw_identity_xic_requests | No-Go for 85RAW | "
            "`max_projected_85raw_identity_xic_requests` not provided |"
        )
    elif projected <= max_projected:
        rows.append(
            "| projected_85raw_identity_xic_requests | Proceed | "
            f"`{projected}` <= `{max_projected}` |"
        )
    else:
        rows.append(
            "| projected_85raw_identity_xic_requests | Pivot | "
            f"`{projected}` exceeds `{max_projected}` |"
        )
    rows.append("")
    return rows


def _status_row(name: str, status: str, *, pass_basis: str) -> str:
    normalized = "" if status is None else str(status).strip()
    if normalized == "pass":
        return f"| {name} | Proceed | {pass_basis} |"
    if normalized == "not_assessed" or not normalized:
        return f"| {name} | Not assessed | `{name}` not assessed |"
    return f"| {name} | Pivot | `{normalized}` |"
```

- [ ] **Step 5: Render the Go/No-Go section**

In `render_identity_coherence_summary()`, place the Engineering Go/No-Go section
as a complete block immediately before the Cost Counters section. The heading
and table rows must stay adjacent:

```python
    lines.extend(
        [
            "## Engineering Go / No-Go",
            "",
        ]
    )
    lines.extend(
        _engineering_go_no_go_rows(
            decision_rows,
            context=context,
            assessed_sample_total=max(
                1,
                _total_assessed_sample_count(decision_rows),
            ),
        )
    )
```

Do not append the rows after the Cost Counters or Writer Contract Checks
sections. Also update the existing heading-order test so
`## Engineering Go / No-Go` appears before `## Cost Counters`.

Add helpers:

```python
def _assessed_sample_count_for_decision(
    row: IdentityDecisionSummary,
) -> int:
    if row.coherent_fraction in {None, 0}:
        return 1
    return max(1, round(row.total_coherent_sample_count / row.coherent_fraction))


def _total_assessed_sample_count(
    decision_rows: Sequence[IdentityDecisionSummary],
) -> int:
    return sum(_assessed_sample_count_for_decision(row) for row in decision_rows)
```

Use `max(1, ...)` in the caller so empty synthetic fixtures do not divide by
zero. Do not use a single maximum inferred sample count as the denominator
across multiple rows; that overestimates blocked fraction when several identity
families are summarized together.

- [ ] **Step 6: Run focused tests**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_output_writer.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```powershell
$env:GIT_CONFIG_COUNT = "1"
$env:GIT_CONFIG_KEY_0 = "safe.directory"
$env:GIT_CONFIG_VALUE_0 = (Get-Location).Path
git status --short
git add xic_extractor\alignment\identity_coherence\output.py tests\alignment\identity_coherence\test_output_writer.py
git commit -m "feat: render identity coherence engineering gates"
```

---

## Task 4: Firewall Spoof Fixture And A/B Test

**Files:**

- Create: `tests/fixtures/identity_coherence/firewall_spoof/pre_backfill_owner_state.jsonl`
- Create: `tests/fixtures/identity_coherence/firewall_spoof/post_backfill_spoof.tsv`
- Create: `tests/fixtures/identity_coherence/firewall_spoof/expected_decisions.tsv`
- Create: `tests/alignment/identity_coherence/test_firewall_fixture.py`

- [ ] **Step 1: Create firewall fixture directory and files**

Run:

```powershell
New-Item -ItemType Directory -Force tests\fixtures\identity_coherence\firewall_spoof
```

Create `tests/fixtures/identity_coherence/firewall_spoof/pre_backfill_owner_state.jsonl`:

```jsonl
{"decision_id":"DEC-FW-PASS","identity_family_id":"IDF-FW-PASS","seed_candidate_id":"CAND-FW-PASS","seed_sample":"RAW-1","expected_decision":"would_primary_provisional_identity_family_support","total_coherent_sample_count":3,"non_seed_coherent_sample_count":2,"tier12_non_seed_identity_sample_count":2,"seed_gate_class":"coherent_seed","cell_identity_basis":"rt_fragment_support"}
{"decision_id":"DEC-FW-REVIEW","identity_family_id":"IDF-FW-REVIEW","seed_candidate_id":"CAND-FW-REVIEW","seed_sample":"RAW-1","expected_decision":"review_only_seed_gate_failed","total_coherent_sample_count":1,"non_seed_coherent_sample_count":0,"tier12_non_seed_identity_sample_count":0,"seed_gate_class":"review_only_seed_gate_failed","cell_identity_basis":"none"}
```

Create `tests/fixtures/identity_coherence/firewall_spoof/post_backfill_spoof.tsv`:

```text
decision_id	production_status	include_in_primary_matrix	backfill_status	workbook_area	spoof_note
DEC-FW-PASS	rescued	true	backfill_rescued	999999.0	Forbidden values must be seen but not used
DEC-FW-REVIEW	detected	true	backfill_rescued	888888.0	Review-only row must remain review-only
```

Create `tests/fixtures/identity_coherence/firewall_spoof/expected_decisions.tsv`:

```text
decision_id	decision	total_coherent_sample_count	non_seed_coherent_sample_count	tier12_non_seed_identity_sample_count	seed_gate_class	cell_identity_basis	forbidden_evidence_seen
DEC-FW-PASS	would_primary_provisional_identity_family_support	3	2	2	coherent_seed	rt_fragment_support	true
DEC-FW-REVIEW	review_only_seed_gate_failed	1	0	0	review_only_seed_gate_failed	none	true
```

- [ ] **Step 2: Add fixture contract tests**

Create `tests/alignment/identity_coherence/test_firewall_fixture.py`:

```python
import csv
import json
from dataclasses import replace
from pathlib import Path

from tests.alignment.identity_coherence.output_fixtures import output_record
from xic_extractor.alignment.identity_coherence.models import (
    CellEvidenceResult,
    IdentityDecisionSummary,
)
from xic_extractor.alignment.identity_coherence.schema import (
    CellIdentityBasis,
    IdentityDecision,
    SeedGateClass,
    SeedRejectReason,
)

FIXTURE_DIR = (
    Path(__file__).parents[2]
    / "fixtures"
    / "identity_coherence"
    / "firewall_spoof"
)


def _jsonl_rows(path: Path) -> tuple[dict[str, object], ...]:
    with path.open("r", encoding="utf-8") as handle:
        return tuple(json.loads(line) for line in handle if line.strip())


def _tsv_rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return tuple(csv.DictReader(handle, dialect="excel-tab"))


def _record_from_fixture(row: dict[str, object], *, spoofed: bool):
    record = output_record()
    decision = _decision_from_fixture(
        record.row_result.decision,
        row,
        forbidden_evidence_seen=spoofed,
    )
    cells = _cells_from_fixture(
        record.row_result.cells,
        row,
        forbidden_evidence_seen=spoofed,
    )
    seed_gate = replace(
        record.seed_gate,
        seed_gate_class=SeedGateClass(str(row["seed_gate_class"])),
        seed_reject_reason=(
            SeedRejectReason.LOW_MS1_SCAN_SUPPORT
            if row["seed_gate_class"] == "review_only_seed_gate_failed"
            else None
        ),
        resolved_request=replace(
            record.seed_gate.resolved_request,
            decision_id=str(row["decision_id"]),
            seed_candidate_id=str(row["seed_candidate_id"]),
            seed_sample=str(row["seed_sample"]),
        ),
    )
    return replace(
        record,
        seed_gate=seed_gate,
        row_result=replace(record.row_result, cells=cells, decision=decision),
    )


def _decision_from_fixture(
    decision: IdentityDecisionSummary,
    row: dict[str, object],
    *,
    forbidden_evidence_seen: bool,
) -> IdentityDecisionSummary:
    return replace(
        decision,
        decision_id=str(row["decision_id"]),
        identity_family_id=str(row["identity_family_id"]),
        seed_candidate_id=str(row["seed_candidate_id"]),
        seed_sample=str(row["seed_sample"]),
        seed_gate_class=SeedGateClass(str(row["seed_gate_class"])),
        decision=IdentityDecision(str(row["expected_decision"])),
        total_coherent_sample_count=int(row["total_coherent_sample_count"]),
        non_seed_coherent_sample_count=int(row["non_seed_coherent_sample_count"]),
        tier12_non_seed_identity_sample_count=int(
            row["tier12_non_seed_identity_sample_count"]
        ),
        forbidden_evidence_seen=forbidden_evidence_seen,
        forbidden_evidence_used=False,
    )


def _cells_from_fixture(
    cells: tuple[CellEvidenceResult, ...],
    row: dict[str, object],
    *,
    forbidden_evidence_seen: bool,
) -> tuple[CellEvidenceResult, ...]:
    if row["cell_identity_basis"] == "none":
        return ()
    return tuple(
        replace(
            cell,
            decision_id=str(row["decision_id"]),
            identity_family_id=str(row["identity_family_id"]),
            cell_identity_basis=CellIdentityBasis(str(row["cell_identity_basis"])),
            forbidden_evidence_seen=forbidden_evidence_seen,
        )
        for cell in cells
    )


def _decision_projection(record) -> dict[str, object]:
    decision = record.row_result.decision
    basis = (
        "none"
        if not record.row_result.cells
        else str(record.row_result.cells[0].cell_identity_basis.value)
    )
    return {
        "decision_id": decision.decision_id,
        "decision": decision.decision.value,
        "total_coherent_sample_count": decision.total_coherent_sample_count,
        "non_seed_coherent_sample_count": decision.non_seed_coherent_sample_count,
        "tier12_non_seed_identity_sample_count": (
            decision.tier12_non_seed_identity_sample_count
        ),
        "seed_gate_class": decision.seed_gate_class.value,
        "cell_identity_basis": basis,
        "forbidden_evidence_seen": decision.forbidden_evidence_seen,
        "forbidden_evidence_used": decision.forbidden_evidence_used,
    }


def _apply_firewall_spoof_fixture(
    baseline_records: tuple[object, ...],
    spoof_rows: tuple[dict[str, str], ...],
) -> tuple[object, ...]:
    """Test adapter for the firewall A/B fixture contract.

    This is not the future post-hoc diagnostic adapter. It exercises the same
    fixture-level semantics required before that adapter exists: forbidden
    post-Backfill fields may be detected as present, but only
    `forbidden_evidence_seen` may change in this A/B projection.
    """

    required_spoof_columns = {
        "decision_id",
        "production_status",
        "include_in_primary_matrix",
        "backfill_status",
        "workbook_area",
    }
    for row in spoof_rows:
        missing = required_spoof_columns.difference(row)
        assert not missing
        assert row["production_status"]
        assert row["include_in_primary_matrix"]
        assert row["backfill_status"]
        assert row["workbook_area"]

    spoofed_decision_ids = {row["decision_id"] for row in spoof_rows}
    updated = []
    for record in baseline_records:
        seen = record.row_result.decision.decision_id in spoofed_decision_ids
        decision = replace(
            record.row_result.decision,
            forbidden_evidence_seen=seen,
            forbidden_evidence_used=False,
        )
        cells = tuple(
            replace(cell, forbidden_evidence_seen=seen)
            for cell in record.row_result.cells
        )
        updated.append(
            replace(
                record,
                row_result=replace(record.row_result, decision=decision, cells=cells),
            )
        )
    return tuple(updated)


def test_firewall_spoof_fixture_files_exist() -> None:
    assert (FIXTURE_DIR / "pre_backfill_owner_state.jsonl").is_file()
    assert (FIXTURE_DIR / "post_backfill_spoof.tsv").is_file()
    assert (FIXTURE_DIR / "expected_decisions.tsv").is_file()


def test_firewall_spoof_marks_seen_without_changing_identity_decisions() -> None:
    baseline_rows = _jsonl_rows(FIXTURE_DIR / "pre_backfill_owner_state.jsonl")
    spoof_rows = _tsv_rows(FIXTURE_DIR / "post_backfill_spoof.tsv")
    expected_rows = _tsv_rows(FIXTURE_DIR / "expected_decisions.tsv")

    baseline_records = tuple(
        _record_from_fixture(row, spoofed=False) for row in baseline_rows
    )
    spoof_records = _apply_firewall_spoof_fixture(baseline_records, spoof_rows)

    baseline_projection = [_decision_projection(record) for record in baseline_records]
    spoof_projection = [_decision_projection(record) for record in spoof_records]

    for before, after in zip(baseline_projection, spoof_projection, strict=True):
        assert before["decision_id"] == after["decision_id"]
        assert before["decision"] == after["decision"]
        assert before["total_coherent_sample_count"] == (
            after["total_coherent_sample_count"]
        )
        assert before["non_seed_coherent_sample_count"] == (
            after["non_seed_coherent_sample_count"]
        )
        assert before["tier12_non_seed_identity_sample_count"] == (
            after["tier12_non_seed_identity_sample_count"]
        )
        assert before["seed_gate_class"] == after["seed_gate_class"]
        assert before["cell_identity_basis"] == after["cell_identity_basis"]
        assert before["forbidden_evidence_used"] is False
        assert after["forbidden_evidence_used"] is False
        assert after["forbidden_evidence_seen"] is True

    expected_by_id = {row["decision_id"]: row for row in expected_rows}
    for projected in spoof_projection:
        expected = expected_by_id[projected["decision_id"]]
        assert projected["decision"] == expected["decision"]
        assert str(projected["total_coherent_sample_count"]) == (
            expected["total_coherent_sample_count"]
        )
        assert str(projected["non_seed_coherent_sample_count"]) == (
            expected["non_seed_coherent_sample_count"]
        )
        assert str(projected["tier12_non_seed_identity_sample_count"]) == (
            expected["tier12_non_seed_identity_sample_count"]
        )
        assert projected["seed_gate_class"] == expected["seed_gate_class"]
        assert projected["cell_identity_basis"] == expected["cell_identity_basis"]
        assert str(projected["forbidden_evidence_seen"]).lower() == (
            expected["forbidden_evidence_seen"]
        )
```

- [ ] **Step 3: Run fixture test and verify it passes after fixture files exist**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_firewall_fixture.py -q
```

Expected: PASS.

- [ ] **Step 4: Add summary test for passed firewall fixture status**

Append to `tests/alignment/identity_coherence/test_output_writer.py`:

```python
def test_summary_can_record_passed_firewall_fixture_status():
    markdown = render_identity_coherence_summary(
        (output_record(),),
        context=IdentityCoherenceOutputContext(
            command="pytest",
            mode="inline_pre_backfill",
            input_source="tests/fixtures/identity_coherence/firewall_spoof",
            firewall_fixture_status="pass",
        ),
    )

    assert "| firewall_fixture | Proceed | firewall A/B fixture passed |" in markdown
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_firewall_fixture.py tests\alignment\identity_coherence\test_output_writer.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
$env:GIT_CONFIG_COUNT = "1"
$env:GIT_CONFIG_KEY_0 = "safe.directory"
$env:GIT_CONFIG_VALUE_0 = (Get-Location).Path
git status --short
git add tests\fixtures\identity_coherence\firewall_spoof\pre_backfill_owner_state.jsonl
git add tests\fixtures\identity_coherence\firewall_spoof\post_backfill_spoof.tsv
git add tests\fixtures\identity_coherence\firewall_spoof\expected_decisions.tsv
git add tests\alignment\identity_coherence\test_firewall_fixture.py tests\alignment\identity_coherence\test_output_writer.py
git commit -m "test: add identity coherence firewall spoof fixture"
```

---

## Task 5: Verification, Scope Guard, And Handoff

**Files:**

- Modify only if needed: files already touched in Tasks 1-4.

- [ ] **Step 1: Run engineering-preflight focused tests**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_process_payload.py tests\alignment\identity_coherence\test_firewall_fixture.py tests\alignment\identity_coherence\test_output_writer.py tests\alignment\identity_coherence\test_schema_contract.py -q
```

Expected: PASS. If the spawn smoke test fails in the sandbox with
`PermissionError: [WinError 5]`, Codex workers should rerun this exact command
with shell escalation and should not alter test selection. Human PowerShell
fallback: run the exact command in a normal PowerShell from the required
worktree. Report both sandbox and escalated results.

- [ ] **Step 2: Run identity coherence suite**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence -q
```

Expected: PASS.

- [ ] **Step 3: Run lint for touched surfaces**

Run:

```powershell
uv run ruff check xic_extractor\alignment\identity_coherence tests\alignment\identity_coherence
```

Expected: PASS.

- [ ] **Step 4: Run broad test suite if practical**

Run:

```powershell
uv run pytest --tb=short -q
```

Expected: PASS. If the full suite is too slow for the current turn, run the identity-coherence suite plus `tests\test_parallel_execution.py` and state that the full suite was not run.

- [ ] **Step 5: Scope guard**

Run:

```powershell
$env:GIT_CONFIG_COUNT = "1"
$env:GIT_CONFIG_KEY_0 = "safe.directory"
$env:GIT_CONFIG_VALUE_0 = (Get-Location).Path
git status --short
git diff --name-only <base_commit_before_task1>..HEAD
git diff --name-only
git diff --cached --name-only
git ls-files --others --exclude-standard
```

Expected changed files are limited to:

```text
tests/alignment/identity_coherence/test_firewall_fixture.py
tests/alignment/identity_coherence/test_output_writer.py
tests/alignment/identity_coherence/test_process_payload.py
tests/alignment/identity_coherence/test_schema_contract.py
tests/fixtures/identity_coherence/firewall_spoof/expected_decisions.tsv
tests/fixtures/identity_coherence/firewall_spoof/post_backfill_spoof.tsv
tests/fixtures/identity_coherence/firewall_spoof/pre_backfill_owner_state.jsonl
xic_extractor/alignment/identity_coherence/__init__.py
xic_extractor/alignment/identity_coherence/models.py
xic_extractor/alignment/identity_coherence/output.py
xic_extractor/alignment/identity_coherence/process_payload.py
```

The three working-tree checks (`git diff --name-only`, `git diff --cached
--name-only`, and `git ls-files --others --exclude-standard`) must be empty
except for intentionally uncommitted cleanup files explained in the final note.

If any of these appear in any diff/status output, stop and explain before
committing:

```text
scripts/run_alignment.py
xic_extractor/alignment/pipeline.py
xic_extractor/alignment/owner_backfill.py
xic_extractor/alignment/backfill.py
xic_extractor/alignment/ms1_index_source.py
xic_extractor/extraction/
xic_extractor/output/
```

- [ ] **Step 6: Final commit if cleanup edits were needed**

If Task 5 required cleanup edits:

```powershell
$env:GIT_CONFIG_COUNT = "1"
$env:GIT_CONFIG_KEY_0 = "safe.directory"
$env:GIT_CONFIG_VALUE_0 = (Get-Location).Path
git status --short
git add tests\alignment\identity_coherence\test_firewall_fixture.py tests\alignment\identity_coherence\test_output_writer.py tests\alignment\identity_coherence\test_process_payload.py tests\alignment\identity_coherence\test_schema_contract.py
git add xic_extractor\alignment\identity_coherence\__init__.py xic_extractor\alignment\identity_coherence\models.py xic_extractor\alignment\identity_coherence\output.py xic_extractor\alignment\identity_coherence\process_payload.py
git commit -m "fix: verify identity coherence engineering preflight"
```

If no cleanup edits were required, do not create an empty commit.

---

## Self-Review Checklist

- [ ] No task imports RAW readers, Backfill, workbook/report renderers, CLI scripts, or alignment pipeline code from `identity_coherence` domain modules.
- [ ] The spawn smoke worker is no-RAW and proves only pickle/import/process payload safety.
- [ ] The spawn smoke worker remains importable from `process_payload.py` for tests but is not exported from the package facade.
- [ ] The firewall fixture contains one would-primary and one Review-only row.
- [ ] Spoofed post-Backfill fixture fields can only affect `forbidden_evidence_seen` in the fixture-level A/B projection; they never alter decisions/counts/basis and never set `forbidden_evidence_used`. Production adapter enforcement remains out of scope.
- [ ] Engineering Go/No-Go rows are summary/audit only and cannot mutate identity decisions.
- [ ] The plan leaves opt-in pipeline/CLI/RAW retrieval adapter work to a separate next slice.
- [ ] `uv run pytest tests\alignment\identity_coherence -q` is the minimum required verification before handing this slice to the next plan.

## Next Slice After This Plan

After this preflight passes, the next implementation plan should be an opt-in pre-Backfill diagnostic adapter. It should build `IdentityCoherenceTraceRequest` objects from already-built pre-Backfill owner/candidate state, schedule real XIC retrieval outside domain code, and write frozen identity-coherence outputs. That next plan must still avoid changing production Backfill behavior and must keep the diagnostic behind explicit opt-in CLI/config flags.
