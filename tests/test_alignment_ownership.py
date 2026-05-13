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
    assert [assignment.reason for assignment in result.assignments] == [
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
    assert {assignment.assignment_status for assignment in result.assignments} == {
        "ambiguous",
    }


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


def test_missing_raw_source_records_unresolved_assignment():
    result = build_sample_local_owners(
        (_candidate("s1#9999"),),
        raw_sources={},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
    )

    assert result.owners == ()
    assignments = [
        (a.candidate_id, a.assignment_status, a.reason) for a in result.assignments
    ]
    assert assignments == [
        ("s1#9999", "unresolved", "missing_raw_source"),
    ]


def test_peak_not_found_records_unresolved_assignment():
    result = build_sample_local_owners(
        (_candidate("s1#9998"),),
        raw_sources={
            "s1": FakeXICSource(
                rt=np.array([12.55, 12.58, 12.593, 12.61, 12.64], dtype=float),
                intensity=np.array([0.0, 0.0, 0.0, 0.0, 0.0], dtype=float),
            ),
        },
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
    )

    assert result.owners == ()
    assignments = [
        (a.candidate_id, a.assignment_status, a.reason) for a in result.assignments
    ]
    assert assignments == [
        ("s1#9998", "unresolved", "peak_not_found"),
    ]


def test_build_sample_local_owners_uses_batch_source_when_available() -> None:
    from xic_extractor.xic_models import XICTrace

    class BatchSource:
        def __init__(self) -> None:
            self.batch_sizes: list[int] = []

        def extract_xic_many(self, requests):
            requests = tuple(requests)
            self.batch_sizes.append(len(requests))
            return tuple(
                XICTrace.from_arrays(
                    [request.rt_min, 8.0, request.rt_max],
                    [0.0, 100.0, 0.0],
                )
                for request in requests
            )

        def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
            raise AssertionError("batch-capable source should not call extract_xic")

    source = BatchSource()
    candidates = (
        _candidate("s1#batch-1", mz=258.0, seed_rt=8.0),
        _candidate("s1#batch-2", mz=259.0, seed_rt=8.1),
    )

    result = build_sample_local_owners(
        candidates,
        raw_sources={"s1": source},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        peak_resolver=_always_peak_at_seed,
        raw_xic_batch_size=64,
    )

    assert source.batch_sizes == [2]
    assert len(result.assignments) == 2


class FakeXICSource:
    def __init__(self, *, rt, intensity):
        self.rt = rt
        self.intensity = intensity
        self.calls = []

    def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
        self.calls.append((mz, rt_min, rt_max, ppm_tol))
        return self.rt, self.intensity


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


def _always_peak_at_seed(candidate, rt_array, intensity_array, peak_config, seed_rt):
    from xic_extractor.alignment.ownership import ResolvedPeak

    return ResolvedPeak(
        rt=seed_rt,
        peak_start=float(rt_array[0]),
        peak_end=float(rt_array[-1]),
        area=100.0,
        intensity=100.0,
    )


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
