import csv
import json
from pathlib import Path

from tools.diagnostics import instrument_qc_biological_istd_transfer_audit

BIO_COLUMNS = [
    "target_label",
    "benchmark_eligible_count",
    "rt_range_min",
    "rt_slope_min_per_injection",
]

CLEAN_COLUMNS = [
    "compound",
    "point_count",
    "rt_delta_range_min",
    "rt_slope_min_per_injection",
    "warning_count",
]


def test_cli_writes_transfer_audit_outputs(tmp_path: Path) -> None:
    bio_tsv = tmp_path / "biological_qc_istd_drift_summary.tsv"
    clean_tsv = tmp_path / "clean_standard_rt_response_summary.tsv"
    output_dir = tmp_path / "out"
    _write_tsv(
        bio_tsv,
        BIO_COLUMNS,
        [
            {
                "target_label": "d3-5-medC",
                "benchmark_eligible_count": "7",
                "rt_range_min": "0.9",
                "rt_slope_min_per_injection": "0.009",
            }
        ],
    )
    _write_tsv(
        clean_tsv,
        CLEAN_COLUMNS,
        [
            {
                "compound": "d3-5-medC",
                "point_count": "4",
                "rt_delta_range_min": "1.0",
                "rt_slope_min_per_injection": "0.010",
                "warning_count": "1",
            }
        ],
    )

    rc = instrument_qc_biological_istd_transfer_audit.main(
        [
            "--clean-standard-summary-tsv",
            str(clean_tsv),
            "--biological-qc-istd-summary-tsv",
            str(bio_tsv),
            "--istd-scope",
            "dna_istd_current_run",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert rc == 0
    rows_tsv = output_dir / "biological_istd_rt_transfer_audit.tsv"
    summary_json = output_dir / "biological_istd_rt_transfer_audit.json"
    review_md = output_dir / "biological_istd_rt_transfer_audit.md"
    assert rows_tsv.exists()
    assert summary_json.exists()
    assert review_md.exists()
    rows = list(csv.DictReader(rows_tsv.open(encoding="utf-8"), delimiter="\t"))
    assert rows[0]["transfer_status"] == "transfer_supported"
    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    assert payload["counts_by_transfer_status"] == {"transfer_supported": 1}
    assert payload["istd_scope"] == "dna_istd_current_run"


def test_cli_reports_missing_required_column(tmp_path: Path, capsys) -> None:
    bio_tsv = tmp_path / "bio.tsv"
    clean_tsv = tmp_path / "clean.tsv"
    _write_tsv(
        bio_tsv,
        ["target_label", "benchmark_eligible_count", "rt_range_min"],
        [
            {
                "target_label": "d3-5-medC",
                "benchmark_eligible_count": "7",
                "rt_range_min": "0.9",
            }
        ],
    )
    _write_tsv(clean_tsv, CLEAN_COLUMNS, [])

    rc = instrument_qc_biological_istd_transfer_audit.main(
        [
            "--clean-standard-summary-tsv",
            str(clean_tsv),
            "--biological-qc-istd-summary-tsv",
            str(bio_tsv),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert rc == 2
    assert "missing required columns" in capsys.readouterr().err


def _write_tsv(
    path: Path,
    columns: list[str],
    rows: list[dict[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
