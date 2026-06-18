"""Build Lockbox Label Collection Pack v1.

This script turns the existing 72-case lockbox manifest into human-reviewable
packet files plus an empty structured label template. It is read-only with
respect to product behavior: no ProductWriter, matrix, workbook, selected peak,
selected area, counted detection, default extraction, GUI, or RAW behavior is
modified.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path

from xic_extractor.tabular_io import file_sha256, read_tsv_required, write_tsv

ROOT = Path(__file__).resolve().parents[1]
LOCKBOX_MANIFEST = (
    ROOT / "docs/superpowers/validation/lockbox_sampling_manifest_v1.tsv"
)
REVIEW_QUEUE = ROOT / "docs/superpowers/validation/review_queue_v1.tsv"
TRACE_RECOVERY = (
    ROOT / "docs/superpowers/validation/trace_overlay_recovery_report_v1.tsv"
)
PACKET_DIR = ROOT / "docs/superpowers/validation/lockbox_review_packets_v1"
LABEL_TEMPLATE = ROOT / "docs/superpowers/validation/lockbox_label_template_v1.tsv"

PACKET_INDEX_HEADER = [
    "schema_version",
    "lockbox_case_id",
    "packet_path",
    "row_id",
    "family_id",
    "sample_id",
    "analyte",
    "source_stratum",
    "current_machine_decision",
    "evidence_status",
    "missing_evidence_reason",
    "candidate_peak_summary",
    "trace_data_path",
    "trace_data_sha256",
    "overlay_png_path",
    "overlay_png_sha256",
    "hypothesis_png_path",
    "hypothesis_png_sha256",
    "family_context",
    "nearest_competing_candidate",
    "why_machine_cannot_auto_write",
    "reviewer_question",
    "source_artifacts",
    "source_artifact_hashes",
    "may_touch_matrix",
    "may_grant_product_authority",
]

LABEL_TEMPLATE_HEADER = [
    "schema_version",
    "lockbox_case_id",
    "reviewer_slot",
    "row_id",
    "family_id",
    "sample_id",
    "analyte",
    "reviewer_id",
    "reviewed_at_utc",
    "peak_choice_label",
    "area_label",
    "boundary_label",
    "reviewer_confidence",
    "reviewer_reason_code",
    "reviewer_notes",
    "evidence_viewed",
    "source_artifact_hashes",
    "round_trip_oracle_used",
    "label_grants_product_authority",
    "may_touch_matrix",
]

PACKET_SCHEMA_VERSION = "lockbox_review_packet_v1"
LABEL_SCHEMA_VERSION = "lockbox_label_v1"
NO_AUTHORITY = "FALSE"


def build_lockbox_label_collection_pack(
    *,
    manifest_path: Path = LOCKBOX_MANIFEST,
    review_queue_path: Path = REVIEW_QUEUE,
    trace_recovery_path: Path = TRACE_RECOVERY,
    packet_dir: Path = PACKET_DIR,
    label_template_path: Path = LABEL_TEMPLATE,
) -> dict[str, object]:
    manifest_rows = list(
        read_tsv_required(manifest_path, required_columns=("lockbox_case_id",))
    )
    review_rows = {
        row["row_id"]: row
        for row in read_tsv_required(review_queue_path, required_columns=("row_id",))
    }
    recovery_rows = {
        row["row_id"]: row
        for row in read_tsv_required(trace_recovery_path, required_columns=("row_id",))
    }
    packet_dir.mkdir(parents=True, exist_ok=True)
    packet_index_rows: list[dict[str, str]] = []
    label_rows: list[dict[str, str]] = []

    for row in sorted(manifest_rows, key=lambda item: item["lockbox_case_id"]):
        packet = _packet_index_row(
            row,
            review_rows.get(row.get("row_id", "")),
            recovery_rows.get(row.get("row_id", "")),
            packet_dir=packet_dir,
            manifest_path=manifest_path,
            review_queue_path=review_queue_path,
            trace_recovery_path=trace_recovery_path,
        )
        packet_index_rows.append(packet)
        _write_packet_markdown(packet, row, packet_dir)
        label_rows.extend(_label_template_rows(row, packet))

    write_tsv(
        packet_dir / "packet_index.tsv",
        packet_index_rows,
        PACKET_INDEX_HEADER,
        extrasaction="raise",
        lineterminator="\n",
    )
    write_tsv(
        label_template_path,
        label_rows,
        LABEL_TEMPLATE_HEADER,
        extrasaction="raise",
        lineterminator="\n",
    )
    return {
        "packet_dir": packet_dir,
        "packet_index": packet_dir / "packet_index.tsv",
        "label_template": label_template_path,
        "case_count": len(manifest_rows),
        "label_template_rows": len(label_rows),
    }


def _packet_index_row(
    row: Mapping[str, str],
    review_row: Mapping[str, str] | None,
    recovery_row: Mapping[str, str] | None,
    *,
    packet_dir: Path,
    manifest_path: Path,
    review_queue_path: Path,
    trace_recovery_path: Path,
) -> dict[str, str]:
    evidence = _evidence(row, recovery_row)
    source_hashes = _source_artifact_hashes(
        row,
        evidence,
        manifest_path=manifest_path,
        review_queue_path=review_queue_path,
        trace_recovery_path=trace_recovery_path,
        recovery_row=recovery_row,
    )
    packet_path = packet_dir / f"{row['lockbox_case_id']}.md"
    nearest = (
        review_row.get("nearest_competing_peak_context", "")
        if review_row
        else "not_available_in_current_artifacts"
    )
    why = (
        review_row.get("why_machine_cannot_auto_write", "")
        if review_row
        else _why_machine_cannot_auto_write(row, evidence)
    )
    return {
        "schema_version": PACKET_SCHEMA_VERSION,
        "lockbox_case_id": row["lockbox_case_id"],
        "packet_path": _repo_relative(packet_path),
        "row_id": row.get("row_id", ""),
        "family_id": row.get("family_id", ""),
        "sample_id": row.get("sample_id", ""),
        "analyte": row.get("analyte", ""),
        "source_stratum": row.get("source_stratum", ""),
        "current_machine_decision": row.get("mechanical_decision", ""),
        "evidence_status": evidence["status"],
        "missing_evidence_reason": evidence["missing_reason"],
        "candidate_peak_summary": _candidate_peak_summary(row, evidence),
        "trace_data_path": evidence["trace_path"],
        "trace_data_sha256": evidence["trace_sha256"],
        "overlay_png_path": evidence["overlay_path"],
        "overlay_png_sha256": evidence["overlay_sha256"],
        "hypothesis_png_path": evidence["hypothesis_path"],
        "hypothesis_png_sha256": evidence["hypothesis_sha256"],
        "family_context": _family_context(row, recovery_row),
        "nearest_competing_candidate": nearest,
        "why_machine_cannot_auto_write": why,
        "reviewer_question": _reviewer_question(row, evidence),
        "source_artifacts": _source_artifacts(row, evidence, recovery_row),
        "source_artifact_hashes": source_hashes,
        "may_touch_matrix": NO_AUTHORITY,
        "may_grant_product_authority": NO_AUTHORITY,
    }


def _evidence(
    row: Mapping[str, str],
    recovery_row: Mapping[str, str] | None,
) -> dict[str, str]:
    trace_path = row.get("trace_data_path", "")
    overlay_path = row.get("overlay_png_path", "")
    hypothesis_path = _hypothesis_path_from_overlay(overlay_path)
    status = "complete_visual_evidence"
    missing_reason = ""
    if not _existing_file(trace_path) or not _existing_file(overlay_path) or not (
        _existing_file(hypothesis_path)
    ):
        if recovery_row:
            trace_path = recovery_row.get("recovered_family_trace_data_path", "")
            overlay_path = recovery_row.get("recovered_overlay_png_path", "")
            hypothesis_path = recovery_row.get("recovered_hypothesis_png_path", "")
            status = "recovered_visual_evidence"
        else:
            status = "missing_evidence_recorded"
            missing_reason = "trace_overlay_hypothesis_not_available"
    if status == "recovered_visual_evidence" and not (
        _existing_file(trace_path)
        and _existing_file(overlay_path)
        and _existing_file(hypothesis_path)
    ):
        status = "missing_evidence_recorded"
        missing_reason = "recovered_trace_overlay_hypothesis_not_available"
    if status != "missing_evidence_recorded":
        missing_reason = ""
    return {
        "status": status,
        "missing_reason": missing_reason,
        "trace_path": trace_path,
        "trace_sha256": _hash_if_exists(trace_path),
        "overlay_path": overlay_path,
        "overlay_sha256": _hash_if_exists(overlay_path),
        "hypothesis_path": hypothesis_path,
        "hypothesis_sha256": _hash_if_exists(hypothesis_path),
    }


def _source_artifact_hashes(
    row: Mapping[str, str],
    evidence: Mapping[str, str],
    *,
    manifest_path: Path,
    review_queue_path: Path,
    trace_recovery_path: Path,
    recovery_row: Mapping[str, str] | None,
) -> str:
    parts = [
        f"lockbox_sampling_manifest={file_sha256(manifest_path)}",
        row.get("source_hashes", ""),
    ]
    if row.get("review_packet_id"):
        parts.append(f"review_queue={file_sha256(review_queue_path)}")
    if recovery_row:
        parts.append(f"trace_overlay_recovery_report={file_sha256(trace_recovery_path)}")
    for key in ("trace", "overlay", "hypothesis"):
        value = evidence.get(f"{key}_sha256", "")
        if value:
            parts.append(f"{key}={value}")
    return ";".join(part for part in parts if part)


def _source_artifacts(
    row: Mapping[str, str],
    evidence: Mapping[str, str],
    recovery_row: Mapping[str, str] | None,
) -> str:
    artifacts = [row.get("source_artifacts", "")]
    if recovery_row:
        artifacts.append("docs/superpowers/validation/trace_overlay_recovery_report_v1.tsv")
    for key in ("trace_path", "overlay_path", "hypothesis_path"):
        if evidence.get(key):
            artifacts.append(evidence[key])
    return ";".join(part for part in artifacts if part)


def _label_template_rows(
    manifest_row: Mapping[str, str],
    packet: Mapping[str, str],
) -> list[dict[str, str]]:
    required_count = int(manifest_row.get("required_reviewer_count", "2") or "2")
    rows: list[dict[str, str]] = []
    for slot in range(1, required_count + 1):
        rows.append(
            {
                "schema_version": LABEL_SCHEMA_VERSION,
                "lockbox_case_id": manifest_row["lockbox_case_id"],
                "reviewer_slot": str(slot),
                "row_id": manifest_row.get("row_id", ""),
                "family_id": manifest_row.get("family_id", ""),
                "sample_id": manifest_row.get("sample_id", ""),
                "analyte": manifest_row.get("analyte", ""),
                "reviewer_id": "",
                "reviewed_at_utc": "",
                "peak_choice_label": "",
                "area_label": "",
                "boundary_label": "",
                "reviewer_confidence": "",
                "reviewer_reason_code": "",
                "reviewer_notes": "",
                "evidence_viewed": "",
                "source_artifact_hashes": packet["source_artifact_hashes"],
                "round_trip_oracle_used": NO_AUTHORITY,
                "label_grants_product_authority": NO_AUTHORITY,
                "may_touch_matrix": NO_AUTHORITY,
            },
        )
    return rows


def _write_packet_markdown(
    packet: Mapping[str, str],
    manifest_row: Mapping[str, str],
    packet_dir: Path,
) -> None:
    lines = [
        f"# Lockbox Review Packet: {packet['lockbox_case_id']}",
        "",
        "Status: human label packet only; no product write authority.",
        "",
        "## Identity",
        "",
        f"- Row ID: `{packet['row_id'] or 'not_available'}`",
        f"- Family ID: `{packet['family_id']}`",
        f"- Sample ID: `{packet['sample_id']}`",
        f"- Analyte: `{packet['analyte']}`",
        f"- Source stratum: `{packet['source_stratum']}`",
        f"- Current machine decision: `{packet['current_machine_decision']}`",
        "",
        "## Candidate Peak",
        "",
        f"- {packet['candidate_peak_summary']}",
        f"- Known blockers: `{manifest_row.get('known_blockers', '') or 'none'}`",
        f"- Risk tags: `{manifest_row.get('risk_tags', '') or 'none'}`",
        "",
        "## Evidence",
        "",
        f"- Evidence status: `{packet['evidence_status']}`",
        f"- Missing evidence reason: `{packet['missing_evidence_reason'] or 'none'}`",
        f"- Trace data: `{packet['trace_data_path'] or 'not_available'}`",
        f"- Overlay PNG: `{packet['overlay_png_path'] or 'not_available'}`",
        f"- Hypothesis PNG: `{packet['hypothesis_png_path'] or 'not_available'}`",
        f"- Nearest competing candidate: `{packet['nearest_competing_candidate']}`",
        "",
        "## Review Question",
        "",
        packet["reviewer_question"],
        "",
        "## Why This Is Not Auto-Written",
        "",
        packet["why_machine_cannot_auto_write"],
        "",
        "## Label Fields",
        "",
        "- `peak_choice_label`: correct | wrong_peak | wrong_family | "
        "unresolved | insufficient_evidence",
        "- `area_label`: acceptable | unacceptable | not_assessable",
        "- `boundary_label`: acceptable | too_wide | too_narrow | "
        "shifted | not_assessable",
        "- `reviewer_confidence`: high | medium | low",
        "- `reviewer_reason_code`: use one allowed code from the README",
        "- `evidence_viewed`: packet | packet_trace_overlay_hypothesis | "
        "packet_recovered_trace_overlay_hypothesis | packet_missing_evidence_record",
        "",
        "Do not enter replacement values. Keep source artifact hashes unchanged. "
        "Labels do not grant ProductWriter authority.",
        "",
        "## Source Hashes",
        "",
        f"`{packet['source_artifact_hashes']}`",
        "",
    ]
    path = packet_dir / f"{packet['lockbox_case_id']}.md"
    path.write_text("\n".join(lines), encoding="utf-8")


def _why_machine_cannot_auto_write(
    row: Mapping[str, str],
    evidence: Mapping[str, str],
) -> str:
    if row.get("source_stratum") == "approved_write_ready_control":
        return "Positive control reconfirmation only; labels do not add authority."
    if row.get("source_stratum") == "failed_oracle_negative":
        return (
            "Heldout oracle failure is negative evidence; round-trip oracle is "
            "not truth."
        )
    if row.get("source_stratum") == "manual_wrong_peak_or_no_peak":
        return "Manual negative control; do not promote without independent truth."
    if evidence["status"] == "missing_evidence_recorded":
        return (
            "Visual evidence is missing in current artifacts; reviewer may mark "
            "insufficient evidence."
        )
    return row.get("notes", "") or "Independent peak-choice and area truth required."


def _reviewer_question(row: Mapping[str, str], evidence: Mapping[str, str]) -> str:
    if evidence["status"] == "missing_evidence_recorded":
        return (
            "Is there enough evidence to label peak choice? If not, use "
            "`insufficient_evidence` and `not_assessable` labels."
        )
    if row.get("area_label_required") == "FALSE":
        return (
            "Label peak choice from the available evidence. Area and boundary "
            "may be `not_assessable` when trace evidence is insufficient."
        )
    return (
        "Independently label peak choice, area acceptability, and boundary "
        "quality. Do not enter replacement values."
    )


def _candidate_peak_summary(
    row: Mapping[str, str],
    evidence: Mapping[str, str],
) -> str:
    area = row.get("candidate_area") or row.get("candidate_value_if_any", "")
    height = row.get("candidate_height", "")
    apex = row.get("candidate_apex_rt_min", "")
    start = row.get("candidate_start_rt_min", "")
    end = row.get("candidate_end_rt_min", "")
    if not area and evidence.get("status") == "recovered_visual_evidence":
        area = "see recovered trace packet"
    return (
        f"area={area or 'not_available'}; height={height or 'not_available'}; "
        f"apex_rt_min={apex or 'not_available'}; "
        f"start_rt_min={start or 'not_available'}; "
        f"end_rt_min={end or 'not_available'}"
    )


def _family_context(
    row: Mapping[str, str],
    recovery_row: Mapping[str, str] | None,
) -> str:
    parts = [
        f"split_basis={row.get('split_basis', '')}",
        f"lockbox_split_id={row.get('lockbox_split_id', '')}",
        f"candidate_universe={row.get('candidate_universe', '')}",
        f"source_write_authority={row.get('source_write_authority', '')}",
    ]
    if recovery_row:
        parts.extend(
            [
                f"family_trace_count={recovery_row.get('family_trace_count', '')}",
                "family_detected_count="
                f"{recovery_row.get('family_detected_count', '')}",
                f"sample_trace_present={recovery_row.get('sample_trace_present', '')}",
            ],
        )
    return ";".join(part for part in parts if part)


def _hypothesis_path_from_overlay(overlay_path: str) -> str:
    if not overlay_path:
        return ""
    path = Path(overlay_path)
    return str(path.with_name(path.stem + "_hypothesis" + path.suffix))


def _existing_file(path_value: str) -> bool:
    return bool(path_value) and Path(path_value).exists()


def _hash_if_exists(path_value: str) -> str:
    if not _existing_file(path_value):
        return ""
    return file_sha256(Path(path_value))


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=LOCKBOX_MANIFEST)
    parser.add_argument("--review-queue", type=Path, default=REVIEW_QUEUE)
    parser.add_argument("--trace-recovery", type=Path, default=TRACE_RECOVERY)
    parser.add_argument("--packet-dir", type=Path, default=PACKET_DIR)
    parser.add_argument("--label-template", type=Path, default=LABEL_TEMPLATE)
    args = parser.parse_args(argv)
    result = build_lockbox_label_collection_pack(
        manifest_path=args.manifest,
        review_queue_path=args.review_queue,
        trace_recovery_path=args.trace_recovery,
        packet_dir=args.packet_dir,
        label_template_path=args.label_template,
    )
    print(
        "Built lockbox label collection pack: "
        f"{result['case_count']} cases, "
        f"{result['label_template_rows']} template rows.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
