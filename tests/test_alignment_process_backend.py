import pickle
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.test_alignment_owner_backfill import _feature
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell
from xic_extractor.alignment.process_backend import (
    AlignmentProcessExecutionError,
    OwnerBuildSampleResult,
    OwnerBuildTimingStats,
    OwnerBackfillSampleResult,
    OwnerBackfillTimingStats,
    OwnerBackfillWorkerError,
    OwnerBuildWorkerError,
    run_owner_build_process,
    run_owner_backfill_process,
)
from xic_extractor.alignment.ownership_models import (
    IdentityEvent,
    OwnerAssignment,
    SampleLocalMS1Owner,
)
from xic_extractor.config import ExtractionConfig


def test_owner_backfill_process_builds_pickleable_sample_jobs_and_orders_output(
    tmp_path: Path,
) -> None:
    feature_a = _feature()
    feature_b = replace(_feature(), feature_family_id="FAM000002")
    features = (feature_b, feature_a)
    cell_a = _cell(cluster_id=feature_a.feature_family_id, sample_stem="sample-a")
    cell_b = _cell(cluster_id=feature_b.feature_family_id, sample_stem="sample-b")
    captured_jobs = []

    def fake_runner(jobs, *, max_workers):
        captured_jobs.extend(jobs)
        for job in jobs:
            pickle.loads(pickle.dumps(job))
        assert max_workers == 2
        return [
            OwnerBackfillSampleResult(
                sample_index=2,
                sample_stem="sample-b",
                cells=(cell_b,),
                timing_stats=(
                    OwnerBackfillTimingStats(
                        sample_stem="sample-b",
                        elapsed_sec=2.0,
                        extract_xic_count=3,
                        point_count=30,
                    ),
                ),
            ),
            OwnerBackfillSampleResult(
                sample_index=1,
                sample_stem="sample-a",
                cells=(cell_a,),
                timing_stats=(
                    OwnerBackfillTimingStats(
                        sample_stem="sample-a",
                        elapsed_sec=1.0,
                        extract_xic_count=2,
                        point_count=20,
                    ),
                ),
            ),
        ]

    output = run_owner_backfill_process(
        features,
        sample_order=("sample-a", "sample-b"),
        raw_paths={
            "sample-a": tmp_path / "sample-a.raw",
            "sample-b": tmp_path / "sample-b.raw",
        },
        dll_dir=tmp_path / "dll",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(tmp_path),
        max_workers=2,
        runner=fake_runner,
    )

    assert [job.sample_stem for job in captured_jobs] == ["sample-a", "sample-b"]
    assert [job.sample_index for job in captured_jobs] == [1, 2]
    assert [cell.sample_stem for cell in output.cells] == ["sample-b", "sample-a"]
    assert [stat.sample_stem for stat in output.timing_stats] == [
        "sample-a",
        "sample-b",
    ]


def test_owner_backfill_process_raises_worker_errors(tmp_path: Path) -> None:
    def fake_runner(jobs, *, max_workers):
        return [
            OwnerBackfillWorkerError(
                sample_index=1,
                sample_stem="sample-a",
                raw_name="sample-a.raw",
                message="RuntimeError: boom",
            )
        ]

    with pytest.raises(
        AlignmentProcessExecutionError,
        match="sample-a.raw: RuntimeError: boom",
    ):
        run_owner_backfill_process(
            (_feature(),),
            sample_order=("sample-a",),
            raw_paths={"sample-a": tmp_path / "sample-a.raw"},
            dll_dir=tmp_path / "dll",
            alignment_config=AlignmentConfig(),
            peak_config=_peak_config(tmp_path),
            max_workers=2,
            runner=fake_runner,
        )


def test_owner_build_process_builds_pickleable_sample_jobs_and_merges_output(
    tmp_path: Path,
) -> None:
    owner_a = _owner("sample-a")
    owner_b = _owner("sample-b")
    unresolved_a = OwnerAssignment("sample-a#missing", None, "unresolved", "missing_raw")
    primary_a = OwnerAssignment("sample-a#1", owner_a.owner_id, "primary", "primary")
    primary_b = OwnerAssignment("sample-b#1", owner_b.owner_id, "primary", "primary")
    captured_jobs = []

    def fake_runner(jobs, *, max_workers):
        captured_jobs.extend(jobs)
        for job in jobs:
            pickle.loads(pickle.dumps(job))
        assert max_workers == 2
        return [
            OwnerBuildSampleResult(
                sample_index=2,
                sample_stem="sample-b",
                owners=(owner_b,),
                assignments=(primary_b,),
                ambiguous_records=(),
                timing_stats=(
                    OwnerBuildTimingStats(
                        sample_stem="sample-b",
                        elapsed_sec=2.0,
                        extract_xic_count=3,
                        point_count=30,
                    ),
                ),
            ),
            OwnerBuildSampleResult(
                sample_index=1,
                sample_stem="sample-a",
                owners=(owner_a,),
                assignments=(unresolved_a, primary_a),
                ambiguous_records=(),
                timing_stats=(
                    OwnerBuildTimingStats(
                        sample_stem="sample-a",
                        elapsed_sec=1.0,
                        extract_xic_count=2,
                        point_count=20,
                    ),
                ),
            ),
        ]

    output = run_owner_build_process(
        (_candidate("sample-a"), _candidate("sample-b")),
        sample_order=("sample-a", "sample-b"),
        raw_paths={
            "sample-a": tmp_path / "sample-a.raw",
            "sample-b": tmp_path / "sample-b.raw",
        },
        dll_dir=tmp_path / "dll",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(tmp_path),
        max_workers=2,
        runner=fake_runner,
    )

    assert [job.sample_stem for job in captured_jobs] == ["sample-a", "sample-b"]
    assert [len(job.candidates) for job in captured_jobs] == [1, 1]
    assert output.ownership.owners == (owner_a, owner_b)
    assert output.ownership.assignments == (unresolved_a, primary_a, primary_b)
    assert [stat.sample_stem for stat in output.timing_stats] == [
        "sample-a",
        "sample-b",
    ]


def test_owner_build_process_raises_worker_errors(tmp_path: Path) -> None:
    def fake_runner(jobs, *, max_workers):
        return [
            OwnerBuildWorkerError(
                sample_index=1,
                sample_stem="sample-a",
                raw_name="sample-a.raw",
                message="RuntimeError: boom",
            )
        ]

    with pytest.raises(
        AlignmentProcessExecutionError,
        match="sample-a.raw: RuntimeError: boom",
    ):
        run_owner_build_process(
            (_candidate("sample-a"),),
            sample_order=("sample-a",),
            raw_paths={"sample-a": tmp_path / "sample-a.raw"},
            dll_dir=tmp_path / "dll",
            alignment_config=AlignmentConfig(),
            peak_config=_peak_config(tmp_path),
            max_workers=2,
            runner=fake_runner,
        )


def test_timed_process_raw_source_records_batch_calls() -> None:
    import xic_extractor.alignment.process_backend as process_module
    from xic_extractor.xic_models import XICRequest, XICTrace

    class BatchSource:
        def __init__(self) -> None:
            self.raw_chromatogram_call_count = 0

        def extract_xic_many(self, requests):
            self.raw_chromatogram_call_count += 1
            return tuple(
                XICTrace.from_arrays([request.rt_min], [request.mz])
                for request in requests
            )

        def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
            self.raw_chromatogram_call_count += 1
            return [rt_min], [mz]

    stats = process_module._TimedProcessStats(sample_stem="Sample_A")
    source = process_module._TimedProcessRawSource(BatchSource(), stats=stats)

    traces = source.extract_xic_many(
        (
            XICRequest(mz=258.0, rt_min=8.0, rt_max=9.0, ppm_tol=20.0),
            XICRequest(mz=259.0, rt_min=8.0, rt_max=9.0, ppm_tol=20.0),
        )
    )

    assert [trace.intensity.tolist() for trace in traces] == [[258.0], [259.0]]
    assert stats.extract_xic_count == 2
    assert stats.extract_xic_batch_count == 1
    assert stats.raw_chromatogram_call_count == 1
    assert stats.point_count == 2


def _cell(*, cluster_id: str, sample_stem: str) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster_id,
        status="rescued",
        area=100.0,
        apex_rt=8.5,
        height=50.0,
        peak_start_rt=8.4,
        peak_end_rt=8.6,
        rt_delta_sec=0.0,
        trace_quality="owner_backfill",
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason="owner-centered MS1 backfill",
    )


def _candidate(sample_stem: str):
    return SimpleNamespace(
        sample_stem=sample_stem,
        candidate_id=f"{sample_stem}#1",
    )


def _owner(sample_stem: str) -> SampleLocalMS1Owner:
    event = IdentityEvent(
        candidate_id=f"{sample_stem}#1",
        sample_stem=sample_stem,
        raw_file=f"{sample_stem}.raw",
        neutral_loss_tag="NL116",
        precursor_mz=500.0,
        product_mz=383.9526,
        observed_neutral_loss_da=116.0474,
        seed_rt=8.5,
        evidence_score=80,
        seed_event_count=2,
    )
    return SampleLocalMS1Owner(
        owner_id=f"OWN-{sample_stem}-000001",
        sample_stem=sample_stem,
        raw_file=f"{sample_stem}.raw",
        precursor_mz=500.0,
        owner_apex_rt=8.5,
        owner_peak_start_rt=8.4,
        owner_peak_end_rt=8.6,
        owner_area=100.0,
        owner_height=50.0,
        primary_identity_event=event,
        supporting_events=(),
        identity_conflict=False,
        assignment_reason="owner_exact_apex_match",
    )


def _peak_config(tmp_path: Path) -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=tmp_path,
        dll_dir=tmp_path / "dll",
        output_csv=tmp_path / "xic_results.csv",
        diagnostics_csv=tmp_path / "xic_diagnostics.csv",
        smooth_window=3,
        smooth_polyorder=1,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.01,
        ms2_precursor_tol_da=1.6,
        nl_min_intensity_ratio=0.01,
    )
