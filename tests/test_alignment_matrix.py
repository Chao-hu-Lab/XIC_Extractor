from pathlib import Path

from xic_extractor.alignment import AlignedCell, AlignmentMatrix, CellStatus


def test_cell_status_contract_values():
    statuses: set[CellStatus] = {"detected", "rescued", "absent", "unchecked"}

    assert statuses == {"detected", "rescued", "absent", "unchecked"}


def test_aligned_cell_exposes_traceability_fields():
    cell = AlignedCell(
        sample_stem="sample-a",
        cluster_id="ALN000001",
        status="detected",
        area=123.4,
        apex_rt=5.1,
        height=99.0,
        peak_start_rt=5.0,
        peak_end_rt=5.2,
        rt_delta_sec=6.0,
        trace_quality="clean",
        scan_support_score=0.75,
        source_candidate_id="sample-a#42",
        source_raw_file=Path("sample-a.raw"),
        reason="detected candidate",
    )

    assert cell.sample_stem == "sample-a"
    assert cell.cluster_id == "ALN000001"
    assert cell.status == "detected"
    assert cell.area == 123.4
    assert cell.apex_rt == 5.1
    assert cell.height == 99.0
    assert cell.peak_start_rt == 5.0
    assert cell.peak_end_rt == 5.2
    assert cell.rt_delta_sec == 6.0
    assert cell.trace_quality == "clean"
    assert cell.scan_support_score == 0.75
    assert cell.source_candidate_id == "sample-a#42"
    assert cell.source_raw_file == Path("sample-a.raw")
    assert cell.reason == "detected candidate"


def test_alignment_matrix_preserves_cluster_and_sample_order():
    clusters = ("cluster-a", "cluster-b")
    cells = (
        AlignedCell(
            sample_stem="sample-a",
            cluster_id="ALN000001",
            status="unchecked",
            area=None,
            apex_rt=None,
            height=None,
            peak_start_rt=None,
            peak_end_rt=None,
            rt_delta_sec=None,
            trace_quality="unchecked",
            scan_support_score=None,
            source_candidate_id=None,
            source_raw_file=None,
            reason="not checked",
        ),
    )

    matrix = AlignmentMatrix(
        clusters=clusters,
        cells=cells,
        sample_order=("sample-b", "sample-a"),
    )

    assert matrix.clusters == clusters
    assert matrix.cells == cells
    assert matrix.sample_order == ("sample-b", "sample-a")
