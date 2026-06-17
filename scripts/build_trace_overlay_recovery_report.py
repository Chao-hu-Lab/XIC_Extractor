"""Build the missing-overlay evidence recovery report.

This helper links missing-overlay Backfill rows back to existing family-level
trace/overlay artifacts. It is read-only evidence recovery: it does not run RAW,
call ProductWriter, or mutate matrices, workbooks, selected peaks, areas, or
counted detections.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "docs/superpowers/validation/mechanical_adjudication_index_v1.tsv"
DEFAULT_OUTPUT_DIR = ROOT / "docs/superpowers/validation"
TRACE_ROOTS = [
    ROOT
    / "output/standard_peak_backfill_preset_85raw_20260610"
    / "alignment_preset_dna_dr_85raw_validation_minimal"
    / "standard_peak_backfill_preset",
    ROOT / "output/backfill_light_cell_evidence_85raw_20260609",
]

SCHEMA_VERSION = "trace_overlay_recovery_report_v1"
FAMILY_RE = re.compile(r"(?P<family>fam\d+)_retained_backfill_missing_overlay")

REPORT_HEADER = [
    "schema_version",
    "row_id",
    "family_id",
    "sample_id",
    "analyte",
    "source_mechanical_decision",
    "source_evidence_grade",
    "source_next_required_evidence",
    "source_missing_reason",
    "recovery_status",
    "recovery_scope",
    "recovered_family_trace_data_path",
    "recovered_family_trace_data_sha256",
    "recovered_overlay_png_path",
    "recovered_overlay_png_sha256",
    "recovered_hypothesis_png_path",
    "recovered_hypothesis_png_sha256",
    "sample_trace_present",
    "recovered_sample_trace_status",
    "recovered_sample_cell_area",
    "recovered_sample_cell_height",
    "recovered_sample_cell_apex_rt",
    "recovered_sample_cell_start_rt",
    "recovered_sample_cell_end_rt",
    "recovered_sample_trace_max_intensity",
    "family_trace_count",
    "family_detected_count",
    "post_recovery_mechanical_decision",
    "post_recovery_evidence_grade",
    "post_recovery_next_required_evidence",
    "may_touch_matrix",
    "may_grant_product_authority",
    "source_artifacts",
    "source_hashes",
    "notes",
]


def build_recovery_report(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    index_rows = [
        row
        for row in _read_tsv(INDEX_PATH)
        if row["evidence_grade"] == "D"
        and row["next_required_evidence"]
        == "recover_trace_overlay_or_reintegration_evidence"
    ]
    trace_index = _index_family_trace_artifacts(TRACE_ROOTS)
    trace_cache: dict[Path, dict[str, Any]] = {}
    hash_cache: dict[Path, str] = {}

    report_rows = [
        _build_row(row, trace_index, trace_cache, hash_cache) for row in index_rows
    ]
    report_path = output_dir / "trace_overlay_recovery_report_v1.tsv"
    summary_path = output_dir / "missing_overlay_resolution_summary_v1.json"
    _write_tsv(report_path, REPORT_HEADER, report_rows)

    summary = _summary(report_rows, report_path)
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "report_path": report_path,
        "summary_path": summary_path,
        "row_count": len(report_rows),
        "recovery_status_counts": summary["recovery_status_counts"],
    }


def _build_row(
    row: dict[str, str],
    trace_index: dict[str, dict[str, Path]],
    trace_cache: dict[Path, dict[str, Any]],
    hash_cache: dict[Path, str],
) -> dict[str, str]:
    family_key = row["family_id"].lower()
    artifacts = trace_index.get(family_key)
    payload: dict[str, Any] = {}
    sample_trace: dict[str, Any] = {}
    if artifacts:
        trace_path = artifacts["trace_data"]
        payload = trace_cache.setdefault(trace_path, _read_json(trace_path))
        sample_trace = _find_sample_trace(payload, row["sample_id"])
    else:
        trace_path = None

    overlay_path = artifacts.get("overlay") if artifacts else None
    hypothesis_path = artifacts.get("hypothesis") if artifacts else None
    sample_present = bool(sample_trace)
    trace_hash = _sha256(trace_path, hash_cache)
    overlay_hash = _sha256(overlay_path, hash_cache)
    hypothesis_hash = _sha256(hypothesis_path, hash_cache)
    recovered = bool(
        trace_hash and overlay_hash and hypothesis_hash and sample_present
    )
    status = (
        "family_trace_overlay_recovered"
        if recovered
        else _missing_status(
            trace_path,
            overlay_path,
            hypothesis_path,
            sample_present,
        )
    )
    source_hashes = "mechanical_adjudication_index=" + _sha256(INDEX_PATH, hash_cache)
    if trace_hash:
        source_hashes += ";recovered_family_trace_data=" + trace_hash
    if overlay_hash:
        source_hashes += ";recovered_overlay_png=" + overlay_hash
    if hypothesis_hash:
        source_hashes += ";recovered_hypothesis_png=" + hypothesis_hash

    return {
        "schema_version": SCHEMA_VERSION,
        "row_id": row["row_id"],
        "family_id": row["family_id"],
        "sample_id": row["sample_id"],
        "analyte": row["analyte"],
        "source_mechanical_decision": row["decision"],
        "source_evidence_grade": row["evidence_grade"],
        "source_next_required_evidence": row["next_required_evidence"],
        "source_missing_reason": row["blockers"],
        "recovery_status": status,
        "recovery_scope": "family_trace_overlay_existing_artifact",
        "recovered_family_trace_data_path": _relative(trace_path),
        "recovered_family_trace_data_sha256": trace_hash,
        "recovered_overlay_png_path": _relative(overlay_path),
        "recovered_overlay_png_sha256": overlay_hash,
        "recovered_hypothesis_png_path": _relative(hypothesis_path),
        "recovered_hypothesis_png_sha256": hypothesis_hash,
        "sample_trace_present": _bool(sample_present),
        "recovered_sample_trace_status": str(sample_trace.get("status", "")),
        "recovered_sample_cell_area": str(sample_trace.get("cell_area", "")),
        "recovered_sample_cell_height": str(sample_trace.get("cell_height", "")),
        "recovered_sample_cell_apex_rt": str(sample_trace.get("cell_apex_rt", "")),
        "recovered_sample_cell_start_rt": str(sample_trace.get("cell_start_rt", "")),
        "recovered_sample_cell_end_rt": str(sample_trace.get("cell_end_rt", "")),
        "recovered_sample_trace_max_intensity": str(
            sample_trace.get("trace_max_intensity", "")
        ),
        "family_trace_count": str(payload.get("trace_count", "")),
        "family_detected_count": str(
            payload.get("evidence_summary", {}).get("detected_count", "")
        ),
        "post_recovery_mechanical_decision": "evidence_required",
        "post_recovery_evidence_grade": (
            "C_trace_recovered" if recovered else row["evidence_grade"]
        ),
        "post_recovery_next_required_evidence": (
            "independent_peak_choice_or_area_truth_after_trace_recovery"
            if recovered
            else row["next_required_evidence"]
        ),
        "may_touch_matrix": "FALSE",
        "may_grant_product_authority": "FALSE",
        "source_artifacts": (
            _relative(INDEX_PATH)
            + ";"
            + ";".join(
                path
                for path in (
                    _relative(trace_path),
                    _relative(overlay_path),
                    _relative(hypothesis_path),
                )
                if path
            )
        ),
        "source_hashes": source_hashes,
        "notes": (
            "Evidence link only; does not create review approval or write authority."
        ),
    }


def _index_family_trace_artifacts(
    roots: list[Path],
) -> dict[str, dict[str, Path]]:
    index: dict[str, dict[str, Path]] = {}
    for root in roots:
        if not root.exists():
            continue
        for trace_path in root.rglob(
            "*_retained_backfill_missing_overlay_trace_data.json"
        ):
            match = FAMILY_RE.search(trace_path.name)
            if not match:
                continue
            family = match.group("family")
            current = index.get(family)
            if current and _artifact_rank(current["trace_data"]) <= _artifact_rank(
                trace_path
            ):
                continue
            overlay_path = trace_path.with_name(
                trace_path.name.replace("_trace_data.json", ".png")
            )
            hypothesis_path = trace_path.with_name(
                trace_path.name.replace("_trace_data.json", "_hypothesis.png")
            )
            index[family] = {
                "trace_data": trace_path,
                "overlay": overlay_path,
                "hypothesis": hypothesis_path,
            }
    return index


def _find_sample_trace(
    payload: dict[str, Any],
    sample_id: str,
) -> dict[str, Any]:
    for trace in payload.get("traces", []):
        if isinstance(trace, dict) and trace.get("sample_stem") == sample_id:
            return trace
    return {}


def _artifact_rank(path: Path) -> tuple[int, int, str]:
    text = path.as_posix()
    return (
        0 if "standard_peak_backfill_preset_85raw_20260610" in text else 1,
        len(text),
        text,
    )


def _missing_status(
    trace_path: Path | None,
    overlay_path: Path | None,
    hypothesis_path: Path | None,
    sample_present: bool,
) -> str:
    if not trace_path or not trace_path.exists():
        return "family_trace_data_missing"
    if not overlay_path or not overlay_path.exists():
        return "family_overlay_png_missing"
    if not hypothesis_path or not hypothesis_path.exists():
        return "family_hypothesis_png_missing"
    if not sample_present:
        return "sample_trace_missing"
    return "unknown_recovery_gap"


def _summary(
    report_rows: list[dict[str, str]],
    report_path: Path,
) -> dict[str, Any]:
    status_counts = Counter(row["recovery_status"] for row in report_rows)
    return {
        "schema_version": "missing_overlay_resolution_summary_v1",
        "status": (
            "all_existing_family_trace_overlays_recovered"
            if status_counts == {"family_trace_overlay_recovered": len(report_rows)}
            else "partial_recovery"
        ),
        "report_path": _relative(report_path),
        "report_sha256": _sha256(report_path, {}),
        "source_index": _relative(INDEX_PATH),
        "source_index_sha256": _sha256(INDEX_PATH, {}),
        "candidate_rows": len(report_rows),
        "candidate_families": len({row["family_id"] for row in report_rows}),
        "recovery_status_counts": dict(status_counts),
        "post_recovery_evidence_grade_counts": dict(
            Counter(row["post_recovery_evidence_grade"] for row in report_rows)
        ),
        "authority": {
            "may_touch_matrix": False,
            "may_grant_product_authority": False,
            "product_writer_consumption": "forbidden_without_later_authority_goal",
        },
        "next_action": (
            "use recovered trace links to build review packets or truth labels; "
            "do not auto-write recovered rows"
        ),
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_tsv(
    path: Path,
    header: list[str],
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path | None, cache: dict[Path, str]) -> str:
    if path is None or not path.exists():
        return ""
    if path in cache:
        return cache[path]
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    value = digest.hexdigest().upper()
    cache[path] = value
    return value


def _relative(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _bool(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for trace_overlay_recovery_report_v1.tsv and summary.",
    )
    args = parser.parse_args(argv)
    result = build_recovery_report(args.output_dir)
    print(
        "Trace/overlay recovery report built: "
        f"{result['row_count']} rows -> {result['report_path']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
