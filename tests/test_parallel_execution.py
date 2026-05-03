from __future__ import annotations

import concurrent.futures
import multiprocessing
import pickle
from dataclasses import replace
from pathlib import Path

import pytest

from xic_extractor.config import ExtractionConfig, Target


def test_worker_job_and_result_objects_are_pickleable(tmp_path: Path) -> None:
    from xic_extractor.execution import (
        RawFileJob,
        ScoringInputs,
        WorkerError,
        validate_job_payload,
    )
    from xic_extractor.extractor import RawFileExtractionResult

    job = RawFileJob(
        raw_index=3,
        raw_path=tmp_path / "SampleA.raw",
        config=_config(tmp_path),
        targets=(_target("Analyte"),),
        scoring_inputs=ScoringInputs(
            injection_order={"SampleA": 1},
            istd_rts_by_sample={},
            rt_prior_library={},
        ),
    )
    validate_job_payload(job)
    restored_job = pickle.loads(pickle.dumps(job))

    assert restored_job.raw_index == 3
    assert restored_job.scoring_inputs is not None
    assert restored_job.scoring_inputs.injection_order == {"SampleA": 1}

    worker_error = WorkerError(raw_index=3, raw_name="SampleA.raw", message="boom")
    restored_error = pickle.loads(pickle.dumps(worker_error))
    assert restored_error.raw_name == "SampleA.raw"
    assert restored_error.message == "boom"

    result = RawFileExtractionResult(
        raw_index=3,
        sample_name="SampleA",
        file_result=None,
        diagnostics=[],
        wide_rows=[],
        long_rows=[],
        score_breakdown_rows=[],
        error=None,
    )
    restored_result = pickle.loads(pickle.dumps(result))
    assert restored_result.raw_index == 3


def test_aggregation_sorts_successful_results_by_raw_index(tmp_path: Path) -> None:
    from xic_extractor.execution import collect_ordered_results
    from xic_extractor.extractor import RawFileExtractionResult

    result_b = RawFileExtractionResult(
        raw_index=2,
        sample_name="B",
        file_result=None,
        diagnostics=[],
        wide_rows=[],
        long_rows=[],
        score_breakdown_rows=[],
        error=None,
    )
    result_a = replace(result_b, raw_index=1, sample_name="A")

    assert collect_ordered_results([result_b, result_a]) == [result_a, result_b]


def test_worker_error_result_is_surfaced_with_raw_name() -> None:
    from xic_extractor.execution import (
        ParallelExecutionError,
        WorkerError,
        collect_ordered_results,
    )

    with pytest.raises(ParallelExecutionError, match="SampleA.raw"):
        collect_ordered_results(
            [WorkerError(raw_index=1, raw_name="SampleA.raw", message="DLL failed")]
        )


def test_job_payload_rejects_callables_and_open_file_handles(tmp_path: Path) -> None:
    from xic_extractor.execution import RawFileJob, validate_job_payload

    job = RawFileJob(
        raw_index=1,
        raw_path=tmp_path / "SampleA.raw",
        config=_config(tmp_path),
        targets=(_target("Analyte"),),
        scoring_inputs=lambda: None,
    )
    with pytest.raises(TypeError, match="callable"):
        validate_job_payload(job)

    handle = (tmp_path / "payload.txt").open("w", encoding="utf-8")
    try:
        job = replace(job, scoring_inputs=handle)
        with pytest.raises(TypeError, match="file handle"):
            validate_job_payload(job)
    finally:
        handle.close()


def test_process_pool_spawn_can_run_importable_no_raw_worker(
    tmp_path: Path,
) -> None:
    from xic_extractor.execution import SpawnSmokeJob, spawn_smoke_worker

    context = multiprocessing.get_context("spawn")
    job = SpawnSmokeJob(raw_index=5, raw_name="SampleA.raw")
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=1,
        mp_context=context,
    ) as executor:
        future = executor.submit(spawn_smoke_worker, job)
        assert future.result(timeout=30) == "5:SampleA.raw"


def _config(tmp_path: Path) -> ExtractionConfig:
    data_dir = tmp_path / "raw"
    output_dir = tmp_path / "output"
    dll_dir = tmp_path / "dll"
    data_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    dll_dir.mkdir(exist_ok=True)
    return ExtractionConfig(
        data_dir=data_dir,
        dll_dir=dll_dir,
        output_csv=output_dir / "xic_results.csv",
        diagnostics_csv=output_dir / "xic_diagnostics.csv",
        smooth_window=15,
        smooth_polyorder=3,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.10,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.01,
    )


def _target(label: str) -> Target:
    return Target(
        label=label,
        mz=258.1085,
        rt_min=8.0,
        rt_max=10.0,
        ppm_tol=20.0,
        neutral_loss_da=None,
        nl_ppm_warn=None,
        nl_ppm_max=None,
        is_istd=False,
        istd_pair="",
    )
