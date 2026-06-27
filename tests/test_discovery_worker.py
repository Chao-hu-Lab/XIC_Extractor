from pathlib import Path

from gui.workers import discovery_worker as module
from gui.workers.discovery_worker import DiscoveryRequest, DiscoveryWorker
from xic_extractor.alignment.pipeline_outputs import AlignmentRunOutputs


def test_align_only_summary_uses_existing_batch_index_counts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    index_path = tmp_path / "discovery_batch_index.csv"
    index_path.write_text(
        "\n".join(
            [
                "sample,high_count,medium_count,low_count,candidate_count",
                "A.raw,1,2,3,6",
                "B.raw,0,1,0,1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    raw_dir.mkdir()
    output_dir.mkdir()

    def fake_run_alignment(**_kwargs):
        return AlignmentRunOutputs(matrix_tsv=output_dir / "alignment_matrix.tsv")

    monkeypatch.setattr(module, "run_alignment", fake_run_alignment)
    request = DiscoveryRequest(
        mode="align_only",
        preset="dna-dr",
        tuning_overrides={},
        raw_dir=raw_dir,
        raw_file=None,
        dll_dir=tmp_path / "dll",
        output_dir=output_dir,
        discovery_batch_index=index_path,
    )
    worker = DiscoveryWorker(request)
    monkeypatch.setattr(
        worker,
        "_build_gallery",
        lambda _request, _outputs, *, raw_dir: {
            "gallery_html": str(output_dir / "gallery.html"),
            "gallery_error": None,
        },
    )

    summary = worker._run_align_only(request)

    assert summary is not None
    assert summary["sample_count"] == 2
    assert summary["candidate_counts"] == {
        "HIGH": 1,
        "MEDIUM": 3,
        "LOW": 3,
        "total": 7,
    }
    assert summary["discovery_batch_index"] == str(index_path)
