import json
from pathlib import Path

import pytest

from xic_extractor.diagnostics.timing import TimingRecorder


def test_timing_recorder_records_stage_metrics_and_writes_json(tmp_path: Path) -> None:
    recorder = TimingRecorder("discovery", run_id="run-1", timer=_Timer([10.0, 12.5]))

    with recorder.stage(
        "discover.ms2_seeds",
        sample_stem="Sample_A",
        metrics={"seed_count": 0},
    ) as stage:
        stage.metrics["seed_count"] = 3
        stage.metrics["raw_file"] = Path("Sample_A.raw")

    assert len(recorder.records) == 1
    record = recorder.records[0]
    assert record.stage == "discover.ms2_seeds"
    assert record.sample_stem == "Sample_A"
    assert record.elapsed_sec == pytest.approx(2.5)
    assert record.metrics == {
        "seed_count": 3,
        "raw_file": "Sample_A.raw",
    }

    output_path = tmp_path / "diagnostics" / "timing.json"
    recorder.write_json(output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == "run-1"
    assert payload["pipeline"] == "discovery"
    assert payload["records"] == [
        {
            "sample_stem": "Sample_A",
            "stage": "discover.ms2_seeds",
            "elapsed_sec": pytest.approx(2.5),
            "metrics": {
                "seed_count": 3,
                "raw_file": "Sample_A.raw",
            },
        }
    ]


def test_timing_recorder_records_exception_stage_before_reraising() -> None:
    recorder = TimingRecorder("alignment", run_id="run-2", timer=_Timer([1.0, 1.25]))

    with pytest.raises(ValueError, match="boom"):
        with recorder.stage("alignment.claim_registry"):
            raise ValueError("boom")

    assert len(recorder.records) == 1
    assert recorder.records[0].stage == "alignment.claim_registry"
    assert recorder.records[0].elapsed_sec == pytest.approx(0.25)


def test_timing_recorder_disabled_mode_records_nothing() -> None:
    recorder = TimingRecorder.disabled("discovery", timer=_Timer([1.0, 2.0]))

    with recorder.stage("discover.group_seeds") as stage:
        stage.metrics["group_count"] = 7

    assert recorder.records == ()


def test_timing_recorder_nested_stages_keep_completion_order() -> None:
    recorder = TimingRecorder(
        "alignment",
        run_id="run-3",
        timer=_Timer([1.0, 2.0, 3.0, 5.0]),
    )

    with recorder.stage("alignment.outer"):
        with recorder.stage("alignment.inner"):
            pass

    assert [record.stage for record in recorder.records] == [
        "alignment.inner",
        "alignment.outer",
    ]
    assert [record.elapsed_sec for record in recorder.records] == [
        pytest.approx(1.0),
        pytest.approx(4.0),
    ]


class _Timer:
    def __init__(self, values: list[float]) -> None:
        self._values = values
        self._index = 0

    def __call__(self) -> float:
        value = self._values[self._index]
        self._index += 1
        return value
