# Identity Coherence Inline Adapter Slice 2: Trace Retrieval And Process Worker

> Execution order: 2 of 3
> Depends on: Slice 1 committed

## Shared Context

> Shared scope copied from the original monolithic plan. Each slice is executable only in the stated order.


In scope:

- Create an orchestration-edge adapter module outside `xic_extractor/alignment/identity_coherence/`.
- Convert pre-Backfill `DiscoveryCandidate` and `SampleLocalMS1Owner` evidence into `IdentityCoherenceRequest`, `SeedCandidateEvidence`, `CellCandidateEvidence`, and trace payloads.
- Retrieve candidate XIC traces through existing alignment RAW source protocols:
  - `raw_workers=1`: already-open parent `raw_sources`;
  - `raw_workers>1`: process jobs grouped by sample and chunked by `raw_xic_batch_size`.
- Evaluate rows through the existing domain pipeline and write the frozen output bundle.
- Optionally evaluate an existing TSV controls manifest against the generated records.
- Add opt-in `run_alignment()` keyword arguments and matching `scripts/run_alignment.py` flags.
- Preserve deterministic output ordering across serial and process retrieval.

Out of scope:

- No changes to `xic_extractor/raw_reader.py`, `xic_extractor/alignment/raw_sources.py`, `owner_backfill.py`, `ms1_index_source.py`, or any RAW/XIC retrieval implementation.
- No new process backend framework. The identity process worker must follow the existing `process_backend.py` job/result pattern and must not change owner build/backfill semantics.
- No post-hoc `--alignment-dir` report mode.
- No YAML identity-coherence config parsing; this slice uses `IdentityCoherenceConfig()` defaults and CLI-provided controls manifest only.
- No Backfill behavior, production matrix, workbook, report, downstream background/QC filtering, or statistics changes.
- No real 8RAW interpretation claim. This slice only makes the opt-in diagnostic runnable under the same worker/batch policy as alignment.

## Files

- Create: `xic_extractor/alignment/identity_coherence_adapter.py`
  - Own the orchestration adapter.
  - May import alignment ownership/candidate/raw-source/process contracts and identity-coherence domain functions.
  - Must not be imported by modules under `xic_extractor/alignment/identity_coherence/`.
- Modify: `xic_extractor/alignment/process_backend.py`
  - Add identity-trace process jobs/results only; reuse existing process runner helpers.
  - Must not change owner build/backfill worker behavior.
- Modify: `xic_extractor/alignment/pipeline.py`
  - Add opt-in parameters and call the adapter after pre-Backfill owner clustering and before optional pre-Backfill consolidation / owner Backfill.
- Modify: `xic_extractor/alignment/pipeline_outputs.py`
  - Add optional output-dir reporting for the diagnostic bundle.
- Modify: `scripts/run_alignment.py`
  - Add CLI flags and print the diagnostic output directory when emitted.
- Modify: `tests/test_alignment_pipeline.py`
  - Add opt-in pipeline integration tests.
- Create: `tests/test_alignment_identity_coherence_adapter.py`
  - Add adapter unit tests with synthetic candidates, owners, and fake RAW sources.
- Modify: `tests/test_alignment_process_backend.py`
  - Add no-RAW/fake-runner tests for identity trace process job grouping, ordering, and batching.
- Modify: `tests/test_run_alignment.py`
  - Add CLI flag parsing and propagation tests.
- Modify: `tests/alignment/identity_coherence/test_schema_contract.py`
  - Add dependency boundary test proving pure domain modules do not import the adapter.

## Domain Notes

- The adapter emits one seed-level request per pre-Backfill sample-local owner primary identity event.
- The adapter diagnostic input is the sample-local `OwnershipBuildResult`, not consolidated `owner_features`. When `preconsolidate_owner_families=True`, this slice still reports sample-local pre-consolidation identity coherence; it must not be described as the exact production Backfill input surface.
- `decision_id`, `request_id`, and `identity_family_id` are deterministic diagnostic IDs:
  - `ICD000001`, `ICR000001`, `ICF000001`, sorted by seed sample, owner apex RT, and seed candidate ID.
- A seed-gate-failed row must not schedule non-seed trace retrieval.
- Non-seed candidate pools are selected before trace retrieval using cheap pre-Backfill candidate metadata:
  - sample differs from the seed sample;
  - `candidate_id` differs from the seed candidate;
  - precursor m/z is within the request precursor tolerance;
  - candidate `best_seed_rt` is within `alignment_config.identity_rt_candidate_window_sec` of seed `best_seed_rt`;
  - candidate has finite positive MS1 peak morphology fields.
- Candidate traces are requested over each candidate's original `ms1_peak_rt_start..ms1_peak_rt_end` window. Do not crop all candidates to a common RT window.
- Missing RAW source or extraction exception becomes `blocked_infrastructure` at the trace-result layer and a blocked cell in the final diagnostic row.
- Trace retrieval counters are identity diagnostic counters only. They must be reported separately from existing Backfill counters.
- `raw_workers` and `raw_xic_batch_size` are execution policy, not identity evidence. Changing `raw_workers=1` to `raw_workers=8` or `raw_xic_batch_size=64` must not change decisions, row IDs, or TSV ordering. It may only change timing and retrieval counters.
- In process mode, identity trace requests are grouped by sample. Each worker opens that sample RAW once and evaluates request chunks with `extract_xic_many` when available, using the same batch-size semantics as existing owner build/backfill code.
- This implementation slice includes synthetic serial-vs-process parity tests for the orchestration boundary. Real 8RAW parity and interpretation remain follow-on validation work.
- The adapter uses existing `AlignmentConfig` values for identity request tolerances:
  - precursor tolerance: `alignment_config.preferred_ppm`;
  - product tolerance: `alignment_config.product_mz_tolerance_ppm`;
  - CID observed-loss tolerance: `alignment_config.observed_loss_tolerance_ppm`.
- `fragment_profile_hash="unavailable"` is a known adapter-slice caveat. It will add the existing `fragment_profile_hash_unavailable` request-builder flag to every diagnostic request until a follow-on slice passes the real profile hash.
- Diagnostic failure is fatal when the opt-in flag is enabled. The production alignment path is unchanged when the flag is off; when the user explicitly requests the diagnostic, a partial production run without the requested bundle is more misleading than a loud failure.
- Decoy controls only use `coherent_seed` source records. Review-only seed-gate-failed rows are still written and can be audited, but they are not valid decoy sources because they already failed Layer 1 before any synthetic identity perturbation.


## Slice Acceptance Gate

- Add serial/process identity trace retrieval and process worker support.
- Preserve request order under out-of-order process completion.
- Keep retrieval failures at the narrowest affected scope: sample-level for RAW open failure, chunk-level for extraction failure.
- Commit after Task 2 passes.
- Do not start Slice 3 until this slice is committed.

## Task 2: Trace Retrieval Adapter And Process Worker

**Files:**
- Modify: `xic_extractor/alignment/identity_coherence_adapter.py`
- Modify: `xic_extractor/alignment/process_backend.py`
- Test: `tests/test_alignment_identity_coherence_adapter.py`
- Test: `tests/test_alignment_process_backend.py`

- [ ] **Step 1: Write trace retrieval tests**

Append to `tests/test_alignment_identity_coherence_adapter.py`:

```python
from xic_extractor.alignment.identity_coherence_adapter import (
    build_cell_candidate_evidence,
    retrieve_identity_coherence_trace,
)
from xic_extractor.alignment.identity_coherence.models import (
    CandidateTrace,
    IdentityCoherenceTraceRequest,
    IdentityCoherenceTraceResult,
)


class FakeRawSource:
    def __init__(self) -> None:
        self.calls: list[tuple[float, float, float, float]] = []

    def extract_xic(self, mz: float, rt_min: float, rt_max: float, ppm_tol: float):
        self.calls.append((mz, rt_min, rt_max, ppm_tol))
        return (
            [rt_min, (rt_min + rt_max) / 2.0, rt_max],
            [0.0, 10.0, 0.0],
        )


class FailingRawSource:
    def extract_xic(self, mz: float, rt_min: float, rt_max: float, ppm_tol: float):
        raise OSError("raw unavailable")


def test_retrieve_identity_trace_uses_candidate_peak_boundaries() -> None:
    candidate = _candidate("CAND-2", sample_stem="Sample_B", start_rt=5.10, end_rt=5.20)
    request = IdentityCoherenceTraceRequest(
        decision_id="ICD000001",
        request_id="ICR000001",
        sample_id="Sample_B",
        candidate_id="CAND-2",
        precursor_mz=500.0,
        ppm_tolerance=20.0,
        rt_min=5.10,
        rt_max=5.20,
    )
    source = FakeRawSource()

    result = retrieve_identity_coherence_trace(request, {"Sample_B": source})

    assert result.status == "pass"
    assert result.request == request
    assert result.raw_xic_request_count == 1
    assert result.xic_point_count == 3
    assert source.calls == [(500.0, 5.10, 5.20, 20.0)]
    assert result.trace == CandidateTrace(
        rt_min=(5.10, 5.15, 5.20),
        intensity=(0.0, 10.0, 0.0),
    )


def test_retrieve_identity_trace_blocks_missing_raw_source() -> None:
    request = IdentityCoherenceTraceRequest(
        decision_id="ICD000001",
        request_id="ICR000001",
        sample_id="Missing",
        candidate_id="CAND-2",
        precursor_mz=500.0,
        ppm_tolerance=20.0,
        rt_min=5.10,
        rt_max=5.20,
    )

    result = retrieve_identity_coherence_trace(request, {})

    assert result.status == "blocked_infrastructure"
    assert result.blocked_reason == "missing_raw_source"
    assert result.raw_xic_request_count == 0
    assert result.xic_point_count == 0
    assert result.trace is None


def test_retrieve_identity_trace_blocks_extraction_error() -> None:
    request = IdentityCoherenceTraceRequest(
        decision_id="ICD000001",
        request_id="ICR000001",
        sample_id="Sample_B",
        candidate_id="CAND-2",
        precursor_mz=500.0,
        ppm_tolerance=20.0,
        rt_min=5.10,
        rt_max=5.20,
    )

    result = retrieve_identity_coherence_trace(
        request,
        {"Sample_B": FailingRawSource()},
    )

    assert result.status == "blocked_infrastructure"
    assert result.blocked_reason == "raw_xic_extraction_error"
    assert result.raw_xic_request_count == 1
    assert result.trace is None


def test_build_cell_candidate_evidence_attaches_pass_trace() -> None:
    candidate = _candidate("CAND-2", sample_stem="Sample_B")
    trace_result = retrieve_identity_coherence_trace(
        IdentityCoherenceTraceRequest(
            decision_id="ICD000001",
            request_id="ICR000001",
            sample_id="Sample_B",
            candidate_id="CAND-2",
            precursor_mz=500.0,
            ppm_tolerance=20.0,
            rt_min=4.95,
            rt_max=5.05,
        ),
        {"Sample_B": FakeRawSource()},
    )

    cell = build_cell_candidate_evidence(
        candidate,
        owner_assignment_status="supporting",
        trace_result=trace_result,
    )

    assert cell.sample_id == "Sample_B"
    assert cell.candidate_evidence.candidate_id == "CAND-2"
    assert cell.owner_assignment_status == "supporting"
    assert cell.trace is not None
    assert cell.point_count == 3
    assert cell.blocked_reason == ""


def test_build_cell_candidate_evidence_marks_blocked_trace() -> None:
    candidate = _candidate("CAND-2", sample_stem="Sample_B")
    trace_result = retrieve_identity_coherence_trace(
        IdentityCoherenceTraceRequest(
            decision_id="ICD000001",
            request_id="ICR000001",
            sample_id="Sample_B",
            candidate_id="CAND-2",
            precursor_mz=500.0,
            ppm_tolerance=20.0,
            rt_min=4.95,
            rt_max=5.05,
        ),
        {},
    )

    cell = build_cell_candidate_evidence(
        candidate,
        owner_assignment_status="primary",
        trace_result=trace_result,
    )

    assert cell.trace is None
    assert cell.blocked_reason == "missing_raw_source"


def test_build_cell_candidate_evidence_marks_data_quality_trace() -> None:
    candidate = _candidate("CAND-2", sample_stem="Sample_B")
    request = IdentityCoherenceTraceRequest(
        decision_id="ICD000001",
        request_id="ICR000001",
        sample_id="Sample_B",
        candidate_id="CAND-2",
        precursor_mz=500.0,
        ppm_tolerance=20.0,
        rt_min=4.95,
        rt_max=5.05,
    )
    trace_result = IdentityCoherenceTraceResult(
        request=request,
        trace=None,
        status="data_quality_reject",
        blocked_reason="invalid_trace_payload",
        raw_xic_request_count=1,
    )

    cell = build_cell_candidate_evidence(
        candidate,
        owner_assignment_status="primary",
        trace_result=trace_result,
    )

    assert cell.blocked_reason == ""
    assert cell.data_quality_reason == "invalid_trace_payload"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
uv run pytest tests\test_alignment_identity_coherence_adapter.py::test_retrieve_identity_trace_uses_candidate_peak_boundaries tests\test_alignment_identity_coherence_adapter.py::test_build_cell_candidate_evidence_attaches_pass_trace -q
```

Expected: FAIL because trace adapter helpers do not exist.

- [ ] **Step 3: Implement trace helpers**

Update the existing import block in `identity_coherence_adapter.py` instead of adding duplicate imports:

```python
from pathlib import Path
from time import perf_counter
from typing import Protocol

from xic_extractor.alignment.identity_coherence.models import (
    CandidateTrace,
    CellCandidateEvidence,
    IdentityCoherenceTraceRequest,
    IdentityCoherenceTraceResult,
)
from xic_extractor.alignment.process_backend import run_identity_trace_process
```

Add these definitions:

```python
class IdentityCoherenceRawSource(Protocol):
    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ) -> object:
        raise NotImplementedError


def trace_request_for_candidate(
    *,
    source: IdentityCoherenceSeedSource,
    candidate: DiscoveryCandidate,
    ppm_tolerance: float,
) -> IdentityCoherenceTraceRequest:
    return IdentityCoherenceTraceRequest(
        decision_id=source.decision_id,
        request_id=source.request_id,
        sample_id=candidate.sample_stem,
        candidate_id=candidate.candidate_id,
        precursor_mz=candidate.precursor_mz,
        ppm_tolerance=ppm_tolerance,
        rt_min=float(candidate.ms1_peak_rt_start),
        rt_max=float(candidate.ms1_peak_rt_end),
    )


def retrieve_identity_coherence_trace(
    request: IdentityCoherenceTraceRequest,
    raw_sources: Mapping[str, IdentityCoherenceRawSource],
) -> IdentityCoherenceTraceResult:
    raw_source = raw_sources.get(request.sample_id)
    if raw_source is None:
        return IdentityCoherenceTraceResult(
            request=request,
            trace=None,
            status="blocked_infrastructure",
            blocked_reason="missing_raw_source",
        )

    start = perf_counter()
    try:
        rt_values, intensity_values = raw_source.extract_xic(
            request.precursor_mz,
            request.rt_min,
            request.rt_max,
            request.ppm_tolerance,
        )
    except Exception:
        return IdentityCoherenceTraceResult(
            request=request,
            trace=None,
            status="blocked_infrastructure",
            blocked_reason="raw_xic_extraction_error",
            raw_xic_request_count=1,
            elapsed_sec=perf_counter() - start,
        )

    try:
        trace = CandidateTrace(
            rt_min=tuple(float(value) for value in rt_values),
            intensity=tuple(float(value) for value in intensity_values),
        )
    except (TypeError, ValueError):
        return IdentityCoherenceTraceResult(
            request=request,
            trace=None,
            status="data_quality_reject",
            blocked_reason="invalid_trace_payload",
            raw_xic_request_count=1,
            elapsed_sec=perf_counter() - start,
        )

    return IdentityCoherenceTraceResult(
        request=request,
        trace=trace,
        status="pass",
        raw_xic_request_count=1,
        raw_chromatogram_call_count=1,
        xic_point_count=len(trace.rt_min),
        elapsed_sec=perf_counter() - start,
    )


def retrieve_identity_coherence_traces(
    requests: Sequence[IdentityCoherenceTraceRequest],
    *,
    raw_sources: Mapping[str, IdentityCoherenceRawSource],
    raw_paths: Mapping[str, Path],
    dll_dir: Path,
    raw_workers: int,
    raw_xic_batch_size: int,
) -> tuple[IdentityCoherenceTraceResult, ...]:
    if raw_workers < 1:
        raise ValueError("raw_workers must be >= 1")
    if raw_xic_batch_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")
    if raw_workers == 1:
        return tuple(
            retrieve_identity_coherence_trace(request, raw_sources)
            for request in requests
        )
    process_output = run_identity_trace_process(
        requests,
        raw_paths=raw_paths,
        dll_dir=dll_dir,
        max_workers=raw_workers,
        raw_xic_batch_size=raw_xic_batch_size,
    )
    return process_output.results


def build_cell_candidate_evidence(
    candidate: DiscoveryCandidate,
    *,
    owner_assignment_status: str,
    trace_result: IdentityCoherenceTraceResult | None,
) -> CellCandidateEvidence:
    blocked_reason = ""
    data_quality_reason = ""
    trace = None
    point_count = None
    if trace_result is not None:
        if trace_result.status == "pass":
            trace = trace_result.trace
            point_count = trace_result.xic_point_count
        elif trace_result.status == "blocked_infrastructure":
            blocked_reason = trace_result.blocked_reason
        elif trace_result.status == "data_quality_reject":
            data_quality_reason = trace_result.blocked_reason
    return CellCandidateEvidence(
        sample_id=candidate.sample_stem,
        candidate_evidence=build_seed_candidate_evidence(candidate),
        apex_rt=candidate.ms1_apex_rt,
        peak_start_rt=candidate.ms1_peak_rt_start,
        peak_end_rt=candidate.ms1_peak_rt_end,
        area=candidate.ms1_area,
        height=candidate.ms1_height,
        point_count=point_count,
        owner_assignment_status=owner_assignment_status,
        trace=trace,
        blocked_reason=blocked_reason,
        data_quality_reason=data_quality_reason,
    )
```

- [ ] **Step 4: Add process trace worker**

In `process_backend.py`, follow the existing owner build/backfill process pattern:

- Add frozen dataclasses:
  - `IdentityTraceSampleJob(sample_index, sample_stem, raw_path, dll_dir, requests, raw_xic_batch_size=1)`;
  - `IdentityTraceSampleResult(sample_index, sample_stem, results, timing_stats)`;
  - `IdentityTraceWorkerError(sample_index, sample_stem, raw_name, message)`;
  - `IdentityTraceProcessOutput(results, timing_stats)`.
- Add `run_identity_trace_process(requests, raw_paths, dll_dir, max_workers, raw_xic_batch_size=1, runner=None)`.
- Group `IdentityCoherenceTraceRequest` objects by `sample_id`; samples missing from `raw_paths` return `blocked_infrastructure` trace results with `blocked_reason="missing_raw_source"`.
- Worker opens one sample RAW once using the same local `open_raw()` import pattern as owner build/backfill workers.
- Chunk requests by `raw_xic_batch_size`; before calling RAW batch APIs, convert each `IdentityCoherenceTraceRequest` into `XICRequest(mz=request.precursor_mz, rt_min=request.rt_min, rt_max=request.rt_max, ppm_tol=request.ppm_tolerance)`.
- Within each chunk call `timed_raw.extract_xic_many(...)` when available, then zip returned traces back to the original `IdentityCoherenceTraceRequest` objects by chunk order and convert them into `CandidateTrace` / `IdentityCoherenceTraceResult`.
- `open_raw()` failure is a sample-level diagnostic data gap; extraction failure is a chunk-level data gap. Synthesize `blocked_infrastructure` results for every affected request with `blocked_reason="raw_xic_extraction_error"` and keep later chunks assessable. Reserve `IdentityTraceWorkerError` for programmer/payload failures that prevent the worker from constructing per-request results.
- Preserve final result ordering by the original request order, not process completion order.
- Validate process job payloads with existing `validate_process_job_payload()`.
- Do not change `run_owner_build_process()`, `run_owner_backfill_process()`, owner build/backfill dataclasses, or RAW source implementations.

First add the identity trace imports and update the existing `xic_models` import:

```python
from xic_extractor.alignment.identity_coherence.models import (
    CandidateTrace,
    IdentityCoherenceTraceRequest,
    IdentityCoherenceTraceResult,
)
```

```python
from xic_extractor.xic_models import XICRequest, XICTrace
```

`XICRequest` exists in the current repo and must be used directly rather than
inventing a parallel request shape.

Then add this implementation near the existing owner process dataclasses and runners:

```python
@dataclass(frozen=True)
class IdentityTraceSampleJob:
    sample_index: int
    sample_stem: str
    raw_path: Path
    dll_dir: Path
    requests: tuple[tuple[int, IdentityCoherenceTraceRequest], ...]
    raw_xic_batch_size: int = 1


@dataclass(frozen=True)
class IdentityTraceTimingStats:
    sample_stem: str
    elapsed_sec: float
    extract_xic_count: int
    point_count: int
    extract_xic_batch_count: int = 0
    raw_chromatogram_call_count: int = 0


@dataclass(frozen=True)
class IdentityTraceSampleResult:
    sample_index: int
    sample_stem: str
    indexed_results: tuple[tuple[int, IdentityCoherenceTraceResult], ...]
    timing_stats: tuple[IdentityTraceTimingStats, ...] = ()


@dataclass(frozen=True)
class IdentityTraceProcessOutput:
    results: tuple[IdentityCoherenceTraceResult, ...]
    timing_stats: tuple[IdentityTraceTimingStats, ...]


@dataclass(frozen=True)
class IdentityTraceWorkerError:
    sample_index: int
    sample_stem: str
    raw_name: str
    message: str


IdentityTraceWorkerResult = IdentityTraceSampleResult | IdentityTraceWorkerError


def run_identity_trace_process(
    requests: Sequence[IdentityCoherenceTraceRequest],
    *,
    raw_paths: Mapping[str, Path],
    dll_dir: Path,
    max_workers: int,
    raw_xic_batch_size: int = 1,
    runner: Callable[..., list[IdentityTraceWorkerResult]] | None = None,
) -> IdentityTraceProcessOutput:
    if max_workers < 1:
        raise ValueError("max_workers must be >= 1")
    if raw_xic_batch_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")

    indexed_requests = tuple(enumerate(requests))
    grouped: dict[str, list[tuple[int, IdentityCoherenceTraceRequest]]] = {}
    for index, request in indexed_requests:
        grouped.setdefault(request.sample_id, []).append((index, request))

    jobs: list[IdentityTraceSampleJob] = []
    parent_results: list[IdentityTraceSampleResult] = []
    for sample_index, sample_stem in enumerate(sorted(grouped), start=1):
        sample_requests = tuple(grouped[sample_stem])
        raw_path = raw_paths.get(sample_stem)
        if raw_path is None:
            parent_results.append(
                IdentityTraceSampleResult(
                    sample_index=sample_index,
                    sample_stem=sample_stem,
                    indexed_results=tuple(
                        (
                            index,
                            _identity_trace_blocked_result(
                                request,
                                "missing_raw_source",
                            ),
                        )
                        for index, request in sample_requests
                    ),
                )
            )
            continue
        jobs.append(
            IdentityTraceSampleJob(
                sample_index=sample_index,
                sample_stem=sample_stem,
                raw_path=raw_path,
                dll_dir=dll_dir,
                requests=sample_requests,
                raw_xic_batch_size=raw_xic_batch_size,
            )
        )

    active_runner = runner or run_identity_trace_jobs
    worker_results = active_runner(jobs, max_workers=max_workers) if jobs else []
    return collect_identity_trace_results(
        (*parent_results, *worker_results),
        request_count=len(indexed_requests),
    )


def run_identity_trace_jobs(
    jobs: Iterable[IdentityTraceSampleJob],
    *,
    max_workers: int,
    executor_factory: Callable[..., Any] | None = None,
) -> list[IdentityTraceWorkerResult]:
    return _run_process_jobs(
        jobs,
        worker=extract_identity_trace_sample_job,
        error_factory=_identity_trace_worker_error,
        max_workers=max_workers,
        executor_factory=executor_factory,
    )


def collect_identity_trace_results(
    results: Iterable[IdentityTraceWorkerResult],
    *,
    request_count: int,
) -> IdentityTraceProcessOutput:
    successes: list[IdentityTraceSampleResult] = []
    errors: list[IdentityTraceWorkerError] = []
    for result in results:
        if isinstance(result, IdentityTraceWorkerError):
            errors.append(result)
        else:
            successes.append(result)
    if errors:
        messages = "; ".join(
            f"{error.raw_name}: {error.message}"
            for error in sorted(errors, key=lambda item: item.sample_index)
        )
        raise AlignmentProcessExecutionError(messages)

    indexed: list[tuple[int, IdentityCoherenceTraceResult]] = [
        item for result in successes for item in result.indexed_results
    ]
    indexed.sort(key=lambda item: item[0])
    if [index for index, _result in indexed] != list(range(request_count)):
        raise AlignmentProcessExecutionError("identity trace results are incomplete")
    timing_stats = tuple(
        stat
        for result in sorted(successes, key=lambda item: item.sample_index)
        for stat in result.timing_stats
    )
    return IdentityTraceProcessOutput(
        results=tuple(result for _index, result in indexed),
        timing_stats=timing_stats,
    )


def extract_identity_trace_sample_job(
    job: IdentityTraceSampleJob,
) -> IdentityTraceWorkerResult:
    from xic_extractor.raw_reader import open_raw

    stats = _TimedProcessStats(sample_stem=job.sample_stem)
    try:
        raw_context = open_raw(job.raw_path, job.dll_dir)
        raw = raw_context.__enter__()
    except Exception:
        indexed_results = tuple(
            (
                index,
                _identity_trace_blocked_result(
                    request,
                    "raw_xic_extraction_error",
                    raw_xic_request_count=1,
                ),
            )
            for index, request in job.requests
        )
    else:
        exc_info = (None, None, None)
        try:
            timed_raw = _TimedProcessRawSource(raw, stats=stats)
            indexed_results = _extract_identity_trace_results_for_sample(
                job.requests,
                timed_raw,
                raw_xic_batch_size=job.raw_xic_batch_size,
            )
        except BaseException as error:
            exc_info = (type(error), error, error.__traceback__)
            raise
        finally:
            raw_context.__exit__(*exc_info)

    return IdentityTraceSampleResult(
        sample_index=job.sample_index,
        sample_stem=job.sample_stem,
        indexed_results=indexed_results,
        timing_stats=(
            IdentityTraceTimingStats(
                sample_stem=job.sample_stem,
                elapsed_sec=stats.elapsed_sec,
                extract_xic_count=stats.extract_xic_count,
                point_count=stats.point_count,
                extract_xic_batch_count=stats.extract_xic_batch_count,
                raw_chromatogram_call_count=stats.raw_chromatogram_call_count,
            ),
        ),
    )


def _extract_identity_trace_results_for_sample(
    indexed_requests: tuple[tuple[int, IdentityCoherenceTraceRequest], ...],
    timed_raw: _TimedProcessRawSource,
    *,
    raw_xic_batch_size: int,
) -> tuple[tuple[int, IdentityCoherenceTraceResult], ...]:
    indexed_results: list[tuple[int, IdentityCoherenceTraceResult]] = []
    for chunk in _chunked(indexed_requests, raw_xic_batch_size):
        xic_requests = tuple(
            _identity_trace_to_xic_request(request) for _, request in chunk
        )
        try:
            traces = tuple(timed_raw.extract_xic_many(xic_requests))
        except Exception:
            indexed_results.extend(
                (
                    index,
                    _identity_trace_blocked_result(
                        request,
                        "raw_xic_extraction_error",
                        raw_xic_request_count=1,
                    ),
                )
                for index, request in chunk
            )
            continue
        for (index, request), xic_trace in zip(chunk, traces, strict=True):
            try:
                trace = CandidateTrace(
                    rt_min=tuple(float(value) for value in xic_trace.rt),
                    intensity=tuple(float(value) for value in xic_trace.intensity),
                )
            except (TypeError, ValueError):
                result = _identity_trace_data_quality_result(
                    request,
                    "invalid_trace_payload",
                )
            else:
                result = IdentityCoherenceTraceResult(
                    request=request,
                    trace=trace,
                    status="pass",
                    raw_xic_request_count=1,
                    xic_point_count=len(trace.rt_min),
                )
            indexed_results.append((index, result))
    return tuple(indexed_results)


def _identity_trace_to_xic_request(
    request: IdentityCoherenceTraceRequest,
) -> XICRequest:
    return XICRequest(
        mz=request.precursor_mz,
        rt_min=request.rt_min,
        rt_max=request.rt_max,
        ppm_tol=request.ppm_tolerance,
    )


def _identity_trace_blocked_result(
    request: IdentityCoherenceTraceRequest,
    blocked_reason: str,
    *,
    raw_xic_request_count: int = 0,
) -> IdentityCoherenceTraceResult:
    return IdentityCoherenceTraceResult(
        request=request,
        trace=None,
        status="blocked_infrastructure",
        blocked_reason=blocked_reason,
        raw_xic_request_count=raw_xic_request_count,
    )


def _identity_trace_data_quality_result(
    request: IdentityCoherenceTraceRequest,
    reason: str,
) -> IdentityCoherenceTraceResult:
    return IdentityCoherenceTraceResult(
        request=request,
        trace=None,
        status="data_quality_reject",
        blocked_reason=reason,
        raw_xic_request_count=1,
    )


def _identity_trace_worker_error(
    job: IdentityTraceSampleJob,
    exc: Exception,
) -> IdentityTraceWorkerError:
    return IdentityTraceWorkerError(
        sample_index=job.sample_index,
        sample_stem=job.sample_stem,
        raw_name=job.raw_path.name,
        message=f"{type(exc).__name__}: {exc}",
    )


def _chunked(
    values: Sequence[Any],
    size: int,
) -> Iterable[tuple[Any, ...]]:
    if size < 1:
        raise ValueError("size must be >= 1")
    for index in range(0, len(values), size):
        yield tuple(values[index : index + size])
```

Add process-backend tests using fake jobs/runners first, not real RAW files:

- grouped requests create one job per sample;
- `raw_xic_batch_size=64` is carried into each job;
- worker converts identity requests to `XICRequest` before calling `extract_xic_many`;
- missing sample raw path returns blocked results;
- process-mode extraction failure returns blocked trace results instead of raising the whole diagnostic;
- final results preserve the input request order when runner returns sample results out of order.

Update the imports at the top of `tests/test_alignment_process_backend.py`, then append the test functions below the existing process-backend tests:

```python
from xic_extractor.alignment.identity_coherence.models import (
    IdentityCoherenceTraceRequest,
    IdentityCoherenceTraceResult,
)
from xic_extractor.alignment.process_backend import (
    IdentityTraceSampleJob,
    IdentityTraceSampleResult,
    extract_identity_trace_sample_job,
    run_identity_trace_process,
)
from xic_extractor.xic_models import XICRequest, XICTrace


def _identity_trace_request(sample_id: str, candidate_id: str):
    return IdentityCoherenceTraceRequest(
        decision_id=f"DEC-{candidate_id}",
        request_id=f"REQ-{candidate_id}",
        sample_id=sample_id,
        candidate_id=candidate_id,
        precursor_mz=500.0,
        ppm_tolerance=20.0,
        rt_min=5.0,
        rt_max=5.1,
    )


def test_run_identity_trace_process_groups_requests_by_sample(tmp_path: Path) -> None:
    requests = (
        _identity_trace_request("sample-a", "A1"),
        _identity_trace_request("sample-b", "B1"),
        _identity_trace_request("sample-a", "A2"),
    )
    captured_jobs = []

    def fake_runner(jobs, *, max_workers):
        captured_jobs.extend(jobs)
        assert max_workers == 8
        return [
            IdentityTraceSampleResult(
                sample_index=job.sample_index,
                sample_stem=job.sample_stem,
                indexed_results=tuple(
                    (
                        index,
                        IdentityCoherenceTraceResult(
                            request=request,
                            trace=None,
                            status="blocked_infrastructure",
                            blocked_reason="test_only",
                        ),
                    )
                    for index, request in job.requests
                ),
            )
            for job in jobs
        ]

    run_identity_trace_process(
        requests,
        raw_paths={
            "sample-a": tmp_path / "sample-a.raw",
            "sample-b": tmp_path / "sample-b.raw",
        },
        dll_dir=tmp_path / "dll",
        max_workers=8,
        raw_xic_batch_size=64,
        runner=fake_runner,
    )

    assert [job.sample_stem for job in captured_jobs] == ["sample-a", "sample-b"]
    assert [job.raw_xic_batch_size for job in captured_jobs] == [64, 64]
    assert [index for index, _ in captured_jobs[0].requests] == [0, 2]
    assert [index for index, _ in captured_jobs[1].requests] == [1]


def test_run_identity_trace_process_preserves_request_order(tmp_path: Path) -> None:
    requests = (
        _identity_trace_request("sample-a", "A1"),
        _identity_trace_request("sample-b", "B1"),
    )

    def fake_runner(jobs, *, max_workers):
        results = []
        for job in reversed(tuple(jobs)):
            results.append(
                IdentityTraceSampleResult(
                    sample_index=job.sample_index,
                    sample_stem=job.sample_stem,
                    indexed_results=tuple(
                        (
                            index,
                            IdentityCoherenceTraceResult(
                                request=request,
                                trace=None,
                                status="blocked_infrastructure",
                                blocked_reason="test_only",
                            ),
                        )
                        for index, request in job.requests
                    ),
                )
            )
        return results

    output = run_identity_trace_process(
        requests,
        raw_paths={
            "sample-a": tmp_path / "sample-a.raw",
            "sample-b": tmp_path / "sample-b.raw",
        },
        dll_dir=tmp_path / "dll",
        max_workers=8,
        raw_xic_batch_size=64,
        runner=fake_runner,
    )

    assert [result.request.candidate_id for result in output.results] == ["A1", "B1"]


def test_identity_trace_worker_uses_xic_request_shape(monkeypatch, tmp_path: Path) -> None:
    request = _identity_trace_request("sample-a", "A1")
    seen = {}

    class RawContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def extract_xic_many(self, requests):
            seen["requests"] = tuple(requests)
            assert all(isinstance(item, XICRequest) for item in requests)
            return tuple(XICTrace.from_arrays([5.0, 5.1], [0.0, 10.0]) for _ in requests)

    monkeypatch.setattr(
        "xic_extractor.raw_reader.open_raw",
        lambda raw_path, dll_dir: RawContext(),
    )

    result = extract_identity_trace_sample_job(
        IdentityTraceSampleJob(
            sample_index=1,
            sample_stem="sample-a",
            raw_path=tmp_path / "sample-a.raw",
            dll_dir=tmp_path / "dll",
            requests=((0, request),),
            raw_xic_batch_size=64,
        )
    )

    assert seen["requests"][0].mz == request.precursor_mz
    assert result.indexed_results[0][1].status == "pass"


def test_identity_trace_process_returns_blocked_results_on_extraction_error(
    monkeypatch,
    tmp_path: Path,
) -> None:
    requests = (
        _identity_trace_request("sample-a", "A1"),
        _identity_trace_request("sample-a", "A2"),
    )

    class PartiallyBrokenRawContext:
        def __init__(self):
            self.calls = 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def extract_xic_many(self, requests):
            self.calls += 1
            if self.calls == 1:
                raise OSError("chunk unavailable")
            return tuple(XICTrace.from_arrays([5.0, 5.1], [0.0, 10.0]) for _ in requests)

    monkeypatch.setattr(
        "xic_extractor.raw_reader.open_raw",
        lambda raw_path, dll_dir: PartiallyBrokenRawContext(),
    )

    result = extract_identity_trace_sample_job(
        IdentityTraceSampleJob(
            sample_index=1,
            sample_stem="sample-a",
            raw_path=tmp_path / "sample-a.raw",
            dll_dir=tmp_path / "dll",
            requests=tuple(enumerate(requests)),
            raw_xic_batch_size=1,
        )
    )

    first = result.indexed_results[0][1]
    second = result.indexed_results[1][1]
    assert first.status == "blocked_infrastructure"
    assert first.blocked_reason == "raw_xic_extraction_error"
    assert second.status == "pass"
```

- [ ] **Step 5: Run trace tests**

Run:

```powershell
uv run pytest tests\test_alignment_identity_coherence_adapter.py::test_retrieve_identity_trace_uses_candidate_peak_boundaries tests\test_alignment_identity_coherence_adapter.py::test_retrieve_identity_trace_blocks_missing_raw_source tests\test_alignment_identity_coherence_adapter.py::test_retrieve_identity_trace_blocks_extraction_error tests\test_alignment_identity_coherence_adapter.py::test_build_cell_candidate_evidence_attaches_pass_trace tests\test_alignment_identity_coherence_adapter.py::test_build_cell_candidate_evidence_marks_blocked_trace tests\test_alignment_identity_coherence_adapter.py::test_build_cell_candidate_evidence_marks_data_quality_trace tests\test_alignment_process_backend.py::test_run_identity_trace_process_groups_requests_by_sample tests\test_alignment_process_backend.py::test_identity_trace_worker_uses_xic_request_shape tests\test_alignment_process_backend.py::test_identity_trace_process_returns_blocked_results_on_extraction_error tests\test_alignment_process_backend.py::test_run_identity_trace_process_preserves_request_order -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add xic_extractor\alignment\identity_coherence_adapter.py xic_extractor\alignment\process_backend.py tests\test_alignment_identity_coherence_adapter.py tests\test_alignment_process_backend.py
git commit -m "feat: retrieve identity coherence traces"
```

Use the `git -c safe.directory=...` prefix from Task 1 Step 0 if plain `git` is rejected in this worktree.
