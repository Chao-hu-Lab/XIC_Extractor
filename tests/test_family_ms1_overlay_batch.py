import csv
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from tools.diagnostics import family_ms1_overlay_batch as batch
from tools.diagnostics import family_ms1_overlay_plot as overlay_plot


def test_batch_uses_structured_queue_columns_and_limit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    queue_tsv = tmp_path / "queue.tsv"
    alignment_cells = tmp_path / "alignment_cells.tsv"
    output_dir = tmp_path / "out"
    alignment_cells.write_text("feature_family_id\nFAM001\n", encoding="utf-8")
    _write_queue(
        queue_tsv,
        [
            _queue_row(
                "FAM001",
                mz="251.165",
                rt_min="1.0",
                rt_max="1.2",
                seed_group_id="seed::FAM001::a",
            ),
            _queue_row("FAM002", mz="252.165", rt_min="2.0", rt_max="2.2"),
        ],
    )
    calls: list[dict[str, object]] = []

    def fake_load_family_cells(_alignment_cells: Path, family_id: str) -> list[str]:
        return [family_id]

    def fake_extract_family_trace_rows(**kwargs):
        calls.append(dict(kwargs))
        return ["trace-row"]

    def fake_write_family_ms1_overlay_outputs(**kwargs):
        prefix = kwargs["output_prefix"]
        for suffix in (".png", ".pdf", "_trace_summary.tsv", "_trace_data.json"):
            (output_dir / f"{prefix}{suffix}").write_text("ok", encoding="utf-8")
        return overlay_plot.FamilyMs1OverlayOutputs(
            png_path=output_dir / f"{prefix}.png",
            pdf_path=output_dir / f"{prefix}.pdf",
            summary_tsv=output_dir / f"{prefix}_trace_summary.tsv",
            trace_data_json=output_dir / f"{prefix}_trace_data.json",
        )

    monkeypatch.setattr(batch.overlay_plot, "load_family_cells", fake_load_family_cells)
    monkeypatch.setattr(
        batch.overlay_plot,
        "extract_family_trace_rows",
        fake_extract_family_trace_rows,
    )
    monkeypatch.setattr(
        batch.overlay_plot,
        "write_family_ms1_overlay_outputs",
        fake_write_family_ms1_overlay_outputs,
    )
    monkeypatch.setattr(
        batch.overlay_plot,
        "build_family_ms1_evidence_summary",
        lambda _rows: {
            "family_verdict": "ms1_shape_supports_family_backfill",
            "dda_trigger_limited_ms2_support": True,
            "detected_count": 2,
            "rescued_count": 80,
            "detected_rescued_count": 82,
            "evaluable_trace_count": 82,
            "global_apex_assessable_trace_count": 80,
            "global_apex_assessable_fraction": 0.975,
            "selected_apex_in_trace_window_count": 79,
            "selected_apex_in_trace_window_fraction": 0.963,
            "local_apex_assessable_trace_count": 78,
            "global_apex_interference_count": 1,
            "shape_supported_fraction": 0.8,
            "absolute_own_max_evaluable_trace_count": 82,
            "absolute_own_max_shape_supported_count": 81,
            "absolute_own_max_shape_supported_fraction": 0.988,
            "absolute_trace_apex_assessable_count": 82,
            "absolute_trace_apex_cluster_count": 80,
            "absolute_trace_apex_cluster_fraction": 0.976,
            "absolute_trace_apex_delta_abs_median_min": 0.012,
            "global_apex_interference_fraction": 0.0125,
            "local_apex_supported_count": 77,
            "local_apex_supported_fraction": 0.987,
        },
    )

    rows = batch.run_overlay_batch(
        review_queue_tsv=queue_tsv,
        alignment_cells=tmp_path / "alignment_cells.tsv",
        raw_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        output_dir=output_dir,
        limit=1,
    )
    batch._write_outputs(output_dir, rows)

    assert len(rows) == 1
    assert rows[0]["feature_family_id"] == "FAM001"
    assert rows[0]["seed_group_id"] == "seed::FAM001::a"
    assert rows[0]["status"] == "success"
    assert rows[0]["family_verdict"] == "ms1_shape_supports_family_backfill"
    assert calls[0]["mz"] == 251.165
    assert calls[0]["ppm"] == 10.0
    assert calls[0]["rt_min"] == 1.0
    assert calls[0]["rt_max"] == 1.2
    summary_tsv = output_dir / "family_ms1_overlay_batch_summary.tsv"
    _assert_summary_tsv_contract(summary_tsv)
    summary = _read_tsv(summary_tsv)
    assert summary[0]["seed_group_id"] == "seed::FAM001::a"
    assert summary[0]["png_path"].endswith("fam001_overlay.png")
    assert summary[0]["ppm"] == "10"
    assert summary[0]["global_apex_assessable_trace_count"] == "80"
    assert summary[0]["selected_apex_in_trace_window_fraction"] == "0.963"
    assert summary[0]["global_apex_interference_count"] == "1"
    assert summary[0]["absolute_own_max_shape_supported_fraction"] == "0.988"
    assert summary[0]["absolute_trace_apex_cluster_fraction"] == "0.976"
    markdown = (output_dir / "family_ms1_overlay_batch.md").read_text(
        encoding="utf-8",
    )
    assert "`FAM001`" in markdown


def test_batch_evidence_only_writes_trace_artifacts_without_png(
    tmp_path: Path,
    monkeypatch,
) -> None:
    queue_tsv = tmp_path / "queue.tsv"
    alignment_cells = tmp_path / "alignment_cells.tsv"
    output_dir = tmp_path / "out"
    alignment_cells.write_text("feature_family_id\nFAM001\n", encoding="utf-8")
    _write_queue(queue_tsv, [_queue_row("FAM001")])

    monkeypatch.setattr(
        batch.overlay_plot,
        "load_family_cells",
        lambda _alignment_cells, family_id: [family_id],
    )
    monkeypatch.setattr(
        batch.overlay_plot,
        "extract_family_trace_rows",
        lambda **_kwargs: ["trace-row"],
    )

    def fail_render(**_kwargs):
        raise AssertionError("evidence-only mode must not render PNG overlays")

    def fake_write_summary(path: Path, _rows) -> None:
        path.write_text("sample_stem\nS1\n", encoding="utf-8")

    def fake_write_trace_data(path: Path, **_kwargs) -> None:
        path.write_text(
            json.dumps(
                {
                    "family_id": "FAM001",
                    "provenance": {},
                    "evidence_summary": {
                        "family_verdict": batch.SUPPORT_FAMILY_VERDICT,
                    },
                },
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(
        batch.overlay_plot,
        "write_family_ms1_overlay_outputs",
        fail_render,
    )
    monkeypatch.setattr(batch.overlay_plot, "_write_summary", fake_write_summary)
    monkeypatch.setattr(batch.overlay_plot, "_write_trace_data", fake_write_trace_data)
    monkeypatch.setattr(
        batch.overlay_plot,
        "build_family_ms1_evidence_summary",
        lambda _rows: {"family_verdict": batch.SUPPORT_FAMILY_VERDICT},
    )

    rows = batch.run_overlay_batch(
        review_queue_tsv=queue_tsv,
        alignment_cells=alignment_cells,
        raw_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        output_dir=output_dir,
        limit=1,
        evidence_only=True,
    )
    batch._write_outputs(output_dir, rows)

    assert rows[0]["status"] == "success"
    assert rows[0]["png_path"] == ""
    assert rows[0]["pdf_path"] == ""
    assert rows[0]["trace_summary_tsv"].endswith("fam001_overlay_trace_summary.tsv")
    assert rows[0]["trace_data_json"].endswith("fam001_overlay_trace_data.json")
    summary = _read_tsv(output_dir / "family_ms1_overlay_batch_summary.tsv")
    assert summary[0]["png_path"] == ""
    assert summary[0]["trace_data_json"].endswith("fam001_overlay_trace_data.json")


def test_batch_uses_backfill_seed_mz_when_seed_queue_provides_it(
    tmp_path: Path,
    monkeypatch,
) -> None:
    queue_tsv = tmp_path / "queue.tsv"
    alignment_cells = tmp_path / "alignment_cells.tsv"
    output_dir = tmp_path / "out"
    alignment_cells.write_text("feature_family_id\nFAM_SEED\n", encoding="utf-8")
    row = _queue_row("FAM_SEED", mz="300.0", rt_min="10.0", rt_max="11.0")
    row["backfill_seed_mz"] = "301.123"
    row["ppm"] = "20"
    _write_queue(queue_tsv, [row])
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        batch.overlay_plot,
        "load_family_cells",
        lambda _alignment_cells, family_id: [family_id],
    )

    def fake_extract_family_trace_rows(**kwargs):
        calls.append(dict(kwargs))
        return ["trace-row"]

    monkeypatch.setattr(
        batch.overlay_plot,
        "extract_family_trace_rows",
        fake_extract_family_trace_rows,
    )
    monkeypatch.setattr(
        batch.overlay_plot,
        "write_family_ms1_overlay_outputs",
        lambda **kwargs: overlay_plot.FamilyMs1OverlayOutputs(
            png_path=output_dir / "seed.png",
            pdf_path=output_dir / "seed.pdf",
            summary_tsv=output_dir / "seed_trace_summary.tsv",
            trace_data_json=output_dir / "seed_trace_data.json",
        ),
    )
    monkeypatch.setattr(
        batch.overlay_plot,
        "build_family_ms1_evidence_summary",
        lambda _rows: {"family_verdict": "ms1_shape_supports_family_backfill"},
    )

    rows = batch.run_overlay_batch(
        review_queue_tsv=queue_tsv,
        alignment_cells=tmp_path / "alignment_cells.tsv",
        raw_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        output_dir=output_dir,
        limit=1,
    )

    assert rows[0]["status"] == "success"
    assert calls[0]["mz"] == 301.123
    assert calls[0]["ppm"] == 20.0


def test_batch_no_pdf_skips_pdf_output_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    queue_tsv = tmp_path / "queue.tsv"
    alignment_cells = tmp_path / "alignment_cells.tsv"
    output_dir = tmp_path / "out"
    alignment_cells.write_text("feature_family_id\nFAM_NO_PDF\n", encoding="utf-8")
    _write_queue(queue_tsv, [_queue_row("FAM_NO_PDF")])
    writer_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        batch.overlay_plot,
        "load_family_cells",
        lambda _alignment_cells, family_id: [family_id],
    )
    monkeypatch.setattr(
        batch.overlay_plot,
        "extract_family_trace_rows",
        lambda **_kwargs: ["trace-row"],
    )

    def fake_write_family_ms1_overlay_outputs(**kwargs):
        writer_calls.append(dict(kwargs))
        prefix = kwargs["output_prefix"]
        for suffix in (
            ".png",
            "_hypothesis.png",
            "_trace_summary.tsv",
            "_trace_data.json",
        ):
            (output_dir / f"{prefix}{suffix}").write_text("ok", encoding="utf-8")
        return overlay_plot.FamilyMs1OverlayOutputs(
            png_path=output_dir / f"{prefix}.png",
            pdf_path=None,
            summary_tsv=output_dir / f"{prefix}_trace_summary.tsv",
            trace_data_json=output_dir / f"{prefix}_trace_data.json",
        )

    monkeypatch.setattr(
        batch.overlay_plot,
        "write_family_ms1_overlay_outputs",
        fake_write_family_ms1_overlay_outputs,
    )
    monkeypatch.setattr(
        batch.overlay_plot,
        "build_family_ms1_evidence_summary",
        lambda _rows: {"family_verdict": "ms1_shape_supports_family_backfill"},
    )

    rows = batch.run_overlay_batch(
        review_queue_tsv=queue_tsv,
        alignment_cells=alignment_cells,
        raw_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        output_dir=output_dir,
        limit=1,
        write_pdf=False,
    )
    batch._write_outputs(output_dir, rows)

    assert writer_calls[0]["write_pdf"] is False
    summary = _read_tsv(output_dir / "family_ms1_overlay_batch_summary.tsv")
    assert summary[0]["png_path"].endswith("fam_no_pdf_overlay.png")
    assert summary[0]["pdf_path"] == ""
    assert not (output_dir / "fam_no_pdf_overlay.pdf").exists()
    assert not (output_dir / "fam_no_pdf_overlay_hypothesis.pdf").exists()


def test_batch_fast_path_opens_each_raw_sample_once(tmp_path: Path) -> None:
    alignment_cells = tmp_path / "alignment_cells.tsv"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    raw_dir.mkdir()
    dll_dir.mkdir()
    for sample in ("Sample_A", "Sample_B"):
        (raw_dir / f"{sample}.raw").write_text("raw", encoding="utf-8")
    _write_alignment_cells(
        alignment_cells,
        [
            _cell_row("FAM_A", "Sample_A", "detected", "1000"),
            _cell_row("FAM_A", "Sample_B", "rescued", "500"),
            _cell_row("FAM_B", "Sample_A", "detected", "900"),
            _cell_row("FAM_B", "Sample_B", "rescued", "400"),
        ],
    )
    requests = (
        batch.OverlayBatchRequest(
            rank=1,
            family_id="FAM_A",
            seed_group_id="seed-a",
            mz=251.0,
            ppm=10.0,
            rt_min=1.0,
            rt_max=1.2,
            family_center_rt=1.1,
            output_prefix="fam_a",
        ),
        batch.OverlayBatchRequest(
            rank=2,
            family_id="FAM_B",
            seed_group_id="seed-b",
            mz=252.0,
            ppm=10.0,
            rt_min=2.0,
            rt_max=2.2,
            family_center_rt=2.1,
            output_prefix="fam_b",
        ),
    )
    cells_by_family = overlay_plot.load_family_cells_for_families(
        alignment_cells,
        ("FAM_A", "FAM_B"),
    )
    opened: list[str] = []
    extract_counts: dict[str, int] = {}

    class FakeRaw:
        def __init__(self, sample_stem: str) -> None:
            self.sample_stem = sample_stem
            self.raw_chromatogram_call_count = 0

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def extract_xic_many(self, xic_requests):
            self.raw_chromatogram_call_count += 1
            extract_counts[self.sample_stem] = len(xic_requests)
            return tuple(
                SimpleNamespace(
                    rt=(request.rt_min, request.rt_max),
                    intensity=(request.mz, request.mz + 1),
                )
                for request in xic_requests
            )

    def fake_open_raw(raw_path: Path, _dll_dir: Path) -> FakeRaw:
        opened.append(raw_path.name)
        return FakeRaw(raw_path.stem)

    stats = batch.OverlayExtractionStats.empty()
    rows_by_rank = batch._extract_batch_family_trace_rows(
        requests,
        cells_by_family=cells_by_family,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        max_highlight_rescued=8,
        open_raw_func=fake_open_raw,
        extraction_stats=stats,
    )

    assert opened == ["Sample_A.raw", "Sample_B.raw"]
    assert extract_counts == {"Sample_A": 2, "Sample_B": 2}
    assert stats.to_metrics() == {
        "sample_count": 2,
        "sample_stems": "Sample_A,Sample_B",
        "raw_open_count": 2,
        "extract_xic_batch_count": 2,
        "extract_xic_count": 4,
        "raw_chromatogram_call_count": 2,
        "mean_xic_per_raw_chromatogram_call": 2.0,
        "trace_point_count": 8,
        "exact_scan_window_count": 0,
        "superwindow_group_count": 0,
        "superwindow_fallback_sample_count": 2,
        "superwindow_span_factor": 2,
    }
    assert [row.sample_stem for row in rows_by_rank[1]] == [
        "Sample_A",
        "Sample_B",
    ]
    assert [row.sample_stem for row in rows_by_rank[2]] == [
        "Sample_A",
        "Sample_B",
    ]


def test_batch_superwindow_crops_back_to_original_scan_windows(
    tmp_path: Path,
) -> None:
    from xic_extractor.xic_models import XICTrace

    alignment_cells = tmp_path / "alignment_cells.tsv"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    raw_dir.mkdir()
    dll_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    _write_alignment_cells(
        alignment_cells,
        [
            _cell_row("FAM_A", "Sample_A", "detected", "1000"),
            _cell_row("FAM_B", "Sample_A", "detected", "900"),
        ],
    )
    requests = (
        batch.OverlayBatchRequest(
            rank=1,
            family_id="FAM_A",
            seed_group_id="seed-a",
            mz=251.0,
            ppm=10.0,
            rt_min=1.0,
            rt_max=2.0,
            family_center_rt=1.5,
            output_prefix="fam_a",
        ),
        batch.OverlayBatchRequest(
            rank=2,
            family_id="FAM_B",
            seed_group_id="seed-b",
            mz=252.0,
            ppm=10.0,
            rt_min=1.2,
            rt_max=2.2,
            family_center_rt=1.7,
            output_prefix="fam_b",
        ),
    )
    cells_by_family = overlay_plot.load_family_cells_for_families(
        alignment_cells,
        ("FAM_A", "FAM_B"),
    )
    extract_batch_sizes: list[int] = []
    rt_lookup_counts: dict[int, int] = {}

    class FakeRaw:
        raw_chromatogram_call_count = 0

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def scan_window_for_request(self, request):
            return int(round(request.rt_min * 10)), int(round(request.rt_max * 10))

        def retention_time_for_scan(self, scan_number: int):
            rt_lookup_counts[scan_number] = rt_lookup_counts.get(scan_number, 0) + 1
            return scan_number / 10.0

        def extract_xic_many(self, xic_requests):
            self.raw_chromatogram_call_count += 1
            extract_batch_sizes.append(len(xic_requests))
            rt = [1.0, 1.1, 1.2, 2.0, 2.1, 2.2]
            return tuple(
                XICTrace.from_arrays(
                    rt,
                    [request.mz + offset for offset, _rt in enumerate(rt)],
                )
                for request in xic_requests
            )

    def fake_open_raw(_raw_path: Path, _dll_dir: Path) -> FakeRaw:
        return FakeRaw()

    stats = batch.OverlayExtractionStats.empty()
    rows_by_rank = batch._extract_batch_family_trace_rows(
        requests,
        cells_by_family=cells_by_family,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        max_highlight_rescued=8,
        open_raw_func=fake_open_raw,
        extraction_stats=stats,
    )

    assert extract_batch_sizes == [2]
    assert rows_by_rank[1][0].rt == (1.0, 1.1, 1.2, 2.0)
    assert rows_by_rank[2][0].rt == (1.2, 2.0, 2.1, 2.2)
    assert stats.to_metrics()["extract_xic_batch_count"] == 1
    assert stats.to_metrics()["raw_chromatogram_call_count"] == 1
    assert stats.to_metrics()["exact_scan_window_count"] == 2
    assert stats.to_metrics()["superwindow_group_count"] == 1
    assert stats.to_metrics()["trace_point_count"] == 8
    assert rt_lookup_counts == {10: 1, 12: 1, 20: 1, 22: 1}


def test_batch_reuses_duplicate_sample_xic_requests_without_dropping_rows(
    tmp_path: Path,
) -> None:
    alignment_cells = tmp_path / "alignment_cells.tsv"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    raw_dir.mkdir()
    dll_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    _write_alignment_cells(
        alignment_cells,
        [
            _cell_row("FAM_A", "Sample_A", "detected", "1000"),
            _cell_row("FAM_B", "Sample_A", "rescued", "900"),
        ],
    )
    requests = (
        batch.OverlayBatchRequest(
            rank=1,
            family_id="FAM_A",
            seed_group_id="seed-a",
            mz=251.0,
            ppm=10.0,
            rt_min=1.0,
            rt_max=1.2,
            family_center_rt=1.1,
            output_prefix="fam_a",
        ),
        batch.OverlayBatchRequest(
            rank=2,
            family_id="FAM_B",
            seed_group_id="seed-b",
            mz=251.0,
            ppm=10.0,
            rt_min=1.0,
            rt_max=1.2,
            family_center_rt=1.1,
            output_prefix="fam_b",
        ),
    )
    cells_by_family = overlay_plot.load_family_cells_for_families(
        alignment_cells,
        ("FAM_A", "FAM_B"),
    )
    extract_batch_sizes: list[int] = []

    class FakeRaw:
        raw_chromatogram_call_count = 0

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def extract_xic_many(self, xic_requests):
            self.raw_chromatogram_call_count += 1
            extract_batch_sizes.append(len(xic_requests))
            return tuple(
                SimpleNamespace(
                    rt=(request.rt_min, request.rt_max),
                    intensity=(request.mz, request.mz + 1),
                )
                for request in xic_requests
            )

    def fake_open_raw(_raw_path: Path, _dll_dir: Path) -> FakeRaw:
        return FakeRaw()

    stats = batch.OverlayExtractionStats.empty()
    rows_by_rank = batch._extract_batch_family_trace_rows(
        requests,
        cells_by_family=cells_by_family,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        max_highlight_rescued=8,
        open_raw_func=fake_open_raw,
        extraction_stats=stats,
    )

    assert extract_batch_sizes == [1]
    assert rows_by_rank[1][0].sample_stem == "Sample_A"
    assert rows_by_rank[2][0].sample_stem == "Sample_A"
    assert rows_by_rank[1][0].rt == (1.0, 1.2)
    assert rows_by_rank[2][0].rt == (1.0, 1.2)
    assert stats.to_metrics()["extract_xic_count"] == 2
    assert stats.to_metrics()["extract_xic_batch_count"] == 1
    assert stats.to_metrics()["raw_chromatogram_call_count"] == 1
    assert stats.to_metrics()["trace_point_count"] == 4


def test_batch_reuses_existing_outputs_without_raw_when_requested(
    tmp_path: Path,
    monkeypatch,
) -> None:
    queue_tsv = tmp_path / "queue.tsv"
    alignment_cells = tmp_path / "alignment_cells.tsv"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    alignment_cells.write_text("feature_family_id\nFAM_REUSE\n", encoding="utf-8")
    seed_group_id = (
        "seed::FAM_REUSE::mz=251.165::rt=1.1000::"
        "window=1.0000-1.2000::ppm=10"
    )
    _write_queue(queue_tsv, [_queue_row("FAM_REUSE", seed_group_id=seed_group_id)])
    prefix = "fam_reuse_overlay"
    for suffix in (".png", ".pdf", "_trace_summary.tsv"):
        (output_dir / f"{prefix}{suffix}").write_text("ok", encoding="utf-8")
    (output_dir / f"{prefix}_trace_data.json").write_text(
        json.dumps(
            {
                "family_id": "FAM_REUSE",
                "mz": 251.165,
                "ppm": 10.0,
                "rt_min": 1.0,
                "rt_max": 1.2,
                "provenance": {
                    "overlay_batch_source": batch.OVERLAY_BATCH_SOURCE,
                    "review_queue_tsv": str(queue_tsv),
                    "review_queue_sha256": _sha256_file(queue_tsv),
                    "alignment_cells_tsv": str(alignment_cells),
                    "alignment_cells_sha256": _sha256_file(alignment_cells),
                    "raw_dir": str(raw_dir),
                    "dll_dir": str(dll_dir),
                    "seed_group_id": seed_group_id,
                    "output_prefix": prefix,
                },
                "evidence_summary": {
                    "family_verdict": "ms1_shape_supports_family_backfill",
                    "detected_count": 2,
                    "rescued_count": 3,
                    "detected_rescued_count": 5,
                    "evaluable_trace_count": 5,
                    "absolute_own_max_shape_supported_fraction": 0.8,
                    "local_apex_supported_fraction": 1.0,
                }
            },
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        batch.overlay_plot,
        "load_family_cells",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("RAW path should not be used"),
        ),
    )

    rows = batch.run_overlay_batch(
        review_queue_tsv=queue_tsv,
        alignment_cells=alignment_cells,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        output_dir=output_dir,
        reuse_existing=True,
        write_incremental=True,
    )

    assert rows[0]["status"] == "success"
    assert rows[0]["family_verdict"] == "ms1_shape_supports_family_backfill"
    assert rows[0]["detected_count"] == 2
    assert rows[0]["png_path"].endswith("fam_reuse_overlay.png")
    summary = _read_tsv(output_dir / "family_ms1_overlay_batch_summary.tsv")
    assert summary[0]["feature_family_id"] == "FAM_REUSE"
    assert summary[0]["absolute_own_max_shape_supported_fraction"] == "0.8"


def test_batch_does_not_reuse_existing_outputs_with_mismatched_trace_json(
    tmp_path: Path,
    monkeypatch,
) -> None:
    queue_tsv = tmp_path / "queue.tsv"
    alignment_cells = tmp_path / "alignment_cells.tsv"
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    alignment_cells.write_text("feature_family_id\nFAM_REUSE\n", encoding="utf-8")
    _write_queue(queue_tsv, [_queue_row("FAM_REUSE")])
    prefix = "fam_reuse_overlay"
    for suffix in (".png", ".pdf", "_trace_summary.tsv"):
        (output_dir / f"{prefix}{suffix}").write_text("stale", encoding="utf-8")
    (output_dir / f"{prefix}_trace_data.json").write_text(
        json.dumps(
            {
                "family_id": "FAM_STALE",
                "mz": 999.0,
                "ppm": 20.0,
                "rt_min": 99.0,
                "rt_max": 100.0,
                "evidence_summary": {
                    "family_verdict": "ms1_shape_supports_family_backfill",
                },
            },
        ),
        encoding="utf-8",
    )
    calls: list[str] = []

    def fake_load_family_cells(_alignment_cells: Path, family_id: str) -> list[str]:
        calls.append(family_id)
        return [family_id]

    monkeypatch.setattr(batch.overlay_plot, "load_family_cells", fake_load_family_cells)
    monkeypatch.setattr(
        batch.overlay_plot,
        "extract_family_trace_rows",
        lambda **_kwargs: ["trace-row"],
    )
    monkeypatch.setattr(
        batch.overlay_plot,
        "write_family_ms1_overlay_outputs",
        lambda **kwargs: overlay_plot.FamilyMs1OverlayOutputs(
            png_path=output_dir / f"{kwargs['output_prefix']}.png",
            pdf_path=output_dir / f"{kwargs['output_prefix']}.pdf",
            summary_tsv=output_dir / f"{kwargs['output_prefix']}_trace_summary.tsv",
            trace_data_json=output_dir / f"{kwargs['output_prefix']}_trace_data.json",
        ),
    )
    monkeypatch.setattr(
        batch.overlay_plot,
        "build_family_ms1_evidence_summary",
        lambda _rows: {"family_verdict": "review_required_uncertain_ms1_shape"},
    )

    rows = batch.run_overlay_batch(
        review_queue_tsv=queue_tsv,
        alignment_cells=alignment_cells,
        raw_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        output_dir=output_dir,
        reuse_existing=True,
    )

    assert calls == ["FAM_REUSE"]
    assert rows[0]["status"] == "success"
    assert rows[0]["family_verdict"] == "review_required_uncertain_ms1_shape"


def test_batch_does_not_reuse_legacy_trace_json_without_batch_provenance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    queue_tsv = tmp_path / "queue.tsv"
    alignment_cells = tmp_path / "alignment_cells.tsv"
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    alignment_cells.write_text("feature_family_id\nFAM_REUSE\n", encoding="utf-8")
    _write_queue(queue_tsv, [_queue_row("FAM_REUSE")])
    prefix = "fam_reuse_overlay"
    for suffix in (".png", ".pdf", "_trace_summary.tsv"):
        (output_dir / f"{prefix}{suffix}").write_text("legacy", encoding="utf-8")
    (output_dir / f"{prefix}_trace_data.json").write_text(
        json.dumps(
            {
                "family_id": "FAM_REUSE",
                "mz": 251.165,
                "ppm": 10.0,
                "rt_min": 1.0,
                "rt_max": 1.2,
                "evidence_summary": {
                    "family_verdict": "ms1_shape_supports_family_backfill",
                },
            },
        ),
        encoding="utf-8",
    )
    calls: list[str] = []

    def fake_load_family_cells(_alignment_cells: Path, family_id: str) -> list[str]:
        calls.append(family_id)
        return [family_id]

    monkeypatch.setattr(batch.overlay_plot, "load_family_cells", fake_load_family_cells)
    monkeypatch.setattr(
        batch.overlay_plot,
        "extract_family_trace_rows",
        lambda **_kwargs: ["trace-row"],
    )
    monkeypatch.setattr(
        batch.overlay_plot,
        "write_family_ms1_overlay_outputs",
        lambda **kwargs: overlay_plot.FamilyMs1OverlayOutputs(
            png_path=output_dir / f"{kwargs['output_prefix']}.png",
            pdf_path=output_dir / f"{kwargs['output_prefix']}.pdf",
            summary_tsv=output_dir / f"{kwargs['output_prefix']}_trace_summary.tsv",
            trace_data_json=output_dir / f"{kwargs['output_prefix']}_trace_data.json",
        ),
    )
    monkeypatch.setattr(
        batch.overlay_plot,
        "build_family_ms1_evidence_summary",
        lambda _rows: {"family_verdict": "review_required_uncertain_ms1_shape"},
    )

    rows = batch.run_overlay_batch(
        review_queue_tsv=queue_tsv,
        alignment_cells=alignment_cells,
        raw_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        output_dir=output_dir,
        reuse_existing=True,
    )

    assert calls == ["FAM_REUSE"]
    assert rows[0]["family_verdict"] == "review_required_uncertain_ms1_shape"


def test_markdown_blocks_top30_expansion_for_review_required_family(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "out"
    rows = [
        _batch_row(1, "FAM_SUPPORT", batch.SUPPORT_FAMILY_VERDICT),
        _batch_row(2, "FAM000906", "review_required_uncertain_ms1_shape"),
    ]

    batch._write_outputs(output_dir, rows)

    markdown = (output_dir / "family_ms1_overlay_batch.md").read_text(
        encoding="utf-8",
    )
    assert "- Top 30 expansion: `blocked`" in markdown
    assert "eligible only when every row succeeds" in markdown
    assert "rank 2 `FAM000906` (`review_required_uncertain_ms1_shape`)" in markdown
    summary = _read_tsv(output_dir / "family_ms1_overlay_batch_summary.tsv")
    assert summary[0]["top30_expansion_gate"] == "blocked"
    assert summary[0]["top30_expansion_blocker"] == ""
    assert summary[1]["top30_expansion_gate"] == "blocked"
    assert summary[1]["top30_expansion_blocker"] == (
        "review_required_family_verdict"
    )
    assert "FAM000906 review_required_uncertain_ms1_shape" in summary[1][
        "top30_expansion_blockers"
    ]


def test_markdown_marks_top30_expansion_eligible_when_all_rows_support(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "out"
    rows = [
        _batch_row(1, "FAM001", batch.SUPPORT_FAMILY_VERDICT),
        _batch_row(2, "FAM002", batch.SUPPORT_FAMILY_VERDICT),
    ]

    batch._write_outputs(output_dir, rows)

    markdown = (output_dir / "family_ms1_overlay_batch.md").read_text(
        encoding="utf-8",
    )
    assert "- Top 30 expansion: `eligible`" in markdown
    assert "- Blocking families: none" in markdown
    summary = _read_tsv(output_dir / "family_ms1_overlay_batch_summary.tsv")
    assert [row["top30_expansion_gate"] for row in summary] == [
        "eligible",
        "eligible",
    ]
    assert [row["top30_expansion_blocker"] for row in summary] == ["", ""]
    assert [row["top30_expansion_blockers"] for row in summary] == ["", ""]


def test_summary_blocks_top30_expansion_for_failed_or_insufficient_seed_rows(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "out"
    rows = [
        _batch_row(1, "FAM_FAIL", "", status="failed"),
        _batch_row(2, "FAM_LOW_SEED", "insufficient_nl_seed_support"),
    ]

    batch._write_outputs(output_dir, rows)

    markdown = (output_dir / "family_ms1_overlay_batch.md").read_text(
        encoding="utf-8",
    )
    assert "- Top 30 expansion: `blocked`" in markdown
    assert "rank 1 `FAM_FAIL` (`failed`)" in markdown
    assert "rank 2 `FAM_LOW_SEED` (`insufficient_nl_seed_support`)" in markdown
    summary = _read_tsv(output_dir / "family_ms1_overlay_batch_summary.tsv")
    assert [row["top30_expansion_blocker"] for row in summary] == [
        "failed_row",
        "insufficient_nl_seed_support",
    ]


def test_missing_required_queue_columns_fail_clearly(tmp_path: Path) -> None:
    queue_tsv = tmp_path / "queue.tsv"
    queue_tsv.write_text("feature_family_id\nFAM001\n", encoding="utf-8")

    try:
        batch.run_overlay_batch(
            review_queue_tsv=queue_tsv,
            alignment_cells=tmp_path / "alignment_cells.tsv",
            raw_dir=tmp_path / "raw",
            dll_dir=tmp_path / "dll",
            output_dir=tmp_path / "out",
        )
    except ValueError as exc:
        assert "missing required columns" in str(exc)
        assert "family_center_mz" in str(exc)
    else:
        raise AssertionError("Expected missing-column failure")


def test_family_failure_is_recorded_and_main_exits_2(
    tmp_path: Path,
    monkeypatch,
) -> None:
    queue_tsv = tmp_path / "queue.tsv"
    alignment_cells = tmp_path / "alignment_cells.tsv"
    output_dir = tmp_path / "out"
    alignment_cells.write_text("feature_family_id\nFAM_FAIL\n", encoding="utf-8")
    _write_queue(queue_tsv, [_queue_row("FAM_FAIL")])

    def fake_load_family_cells(_alignment_cells: Path, _family_id: str) -> list[str]:
        raise FileNotFoundError("missing raw")

    monkeypatch.setattr(batch.overlay_plot, "load_family_cells", fake_load_family_cells)

    code = batch.main(
        [
            "--review-queue-tsv",
            str(queue_tsv),
            "--alignment-cells",
            str(alignment_cells),
            "--raw-dir",
            str(tmp_path / "raw"),
            "--dll-dir",
            str(tmp_path / "dll"),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert code == 2
    summary = _read_tsv(output_dir / "family_ms1_overlay_batch_summary.tsv")
    assert summary[0]["status"] == "failed"
    assert "missing raw" in summary[0]["failure_reason"]


def _queue_row(
    family_id: str,
    *,
    mz: str = "251.165",
    rt_min: str = "1.0",
    rt_max: str = "1.2",
    seed_group_id: str = "",
) -> dict[str, str]:
    return {
        "feature_family_id": family_id,
        "seed_group_id": seed_group_id,
        "family_center_mz": mz,
        "family_center_rt": "1.1",
        "suggested_rt_min": rt_min,
        "suggested_rt_max": rt_max,
        "suggested_output_prefix": f"{family_id.lower()}_overlay",
        "suggested_overlay_command_args": "--family-id WRONG --mz 999",
    }


def _write_queue(path: Path, rows: list[dict[str, str]]) -> None:
    fields = (
        "feature_family_id",
        "seed_group_id",
        "family_center_mz",
        "backfill_seed_mz",
        "ppm",
        "family_center_rt",
        "suggested_rt_min",
        "suggested_rt_max",
        "suggested_output_prefix",
        "suggested_overlay_command_args",
    )
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _cell_row(
    family_id: str,
    sample_stem: str,
    status: str,
    area: str,
) -> dict[str, str]:
    return {
        "feature_family_id": family_id,
        "sample_stem": sample_stem,
        "status": status,
        "area": area,
        "apex_rt": "1.1",
        "height": "100",
        "peak_start_rt": "1.0",
        "peak_end_rt": "1.2",
        "region_shadow_verdict": "current_supported",
        "source_candidate_id": "",
    }


def _write_alignment_cells(path: Path, rows: list[dict[str, str]]) -> None:
    fields = (
        "feature_family_id",
        "sample_stem",
        "status",
        "area",
        "apex_rt",
        "height",
        "peak_start_rt",
        "peak_end_rt",
        "region_shadow_verdict",
        "source_candidate_id",
    )
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _batch_row(
    rank: int,
    family_id: str,
    family_verdict: str,
    *,
    status: str = "success",
) -> dict[str, object]:
    return {
        "rank": rank,
        "feature_family_id": family_id,
        "seed_group_id": "",
        "mz": 251.165 + rank,
        "ppm": 10.0,
        "rt_min": 1.0,
        "rt_max": 1.2,
        "family_center_rt": 1.1,
        "output_prefix": f"{family_id.lower()}_overlay",
        "status": status,
        "family_verdict": family_verdict,
        "dda_trigger_limited_ms2_support": True,
        "detected_count": 2,
        "rescued_count": 80,
        "detected_rescued_count": 82,
        "evaluable_trace_count": 82,
        "global_apex_assessable_trace_count": 80,
        "global_apex_assessable_fraction": 0.975,
        "selected_apex_in_trace_window_count": 79,
        "selected_apex_in_trace_window_fraction": 0.963,
        "local_apex_assessable_trace_count": 78,
        "global_apex_interference_count": 1,
        "shape_supported_fraction": 0.8,
        "absolute_own_max_evaluable_trace_count": 82,
        "absolute_own_max_shape_supported_count": 81,
        "absolute_own_max_shape_supported_fraction": 0.988,
        "absolute_trace_apex_assessable_count": 82,
        "absolute_trace_apex_cluster_count": 80,
        "absolute_trace_apex_cluster_fraction": 0.976,
        "absolute_trace_apex_delta_abs_median_min": 0.012,
        "global_apex_interference_fraction": 0.1,
        "local_apex_supported_count": 77,
        "local_apex_supported_fraction": 0.8,
        "png_path": "",
        "pdf_path": "",
        "trace_summary_tsv": "",
        "trace_data_json": "",
        "failure_reason": "render failed" if status == "failed" else "",
    }


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _assert_summary_tsv_contract(path: Path) -> None:
    assert b"\r\n" not in path.read_bytes()
    assert path.read_text(encoding="utf-8").splitlines()[0].split("\t") == list(
        batch._summary_fields()
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()
