"""Replay product-ready preset stages from existing alignment artifacts."""

from __future__ import annotations

import argparse
import json
import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from tools.diagnostics.standard_peak_backfill_preset import (
    StandardPeakBackfillPresetOutputs,
    run_standard_peak_backfill_preset,
)
from xic_extractor.diagnostics.product_ready_preset_publication_check import (
    ProductReadyPresetPublicationCheckOutputs,
    check_product_ready_preset_publication,
)
from xic_extractor.diagnostics.timing import TimingRecorder
from xic_extractor.tabular_io import file_sha256

SCHEMA_VERSION = "dna_dr_product_ready_stage_replay_v1"
DEFAULT_SOURCE_RUN_ID = (
    "alignment-preset:builtin:dna_dr_product_ready:standard-peak-backfill"
)
DEFAULT_CHUNK_SIZE = 240
DEFAULT_PUBLICATION_MODE = "matrix-only"
DEFAULT_MIN_SHAPE_R = 0.95
DEFAULT_RENDER_WORKERS = 3
DEFAULT_CHUNK_WORKERS = 2

_REQUIRED_INPUT_FILES = (
    "alignment_review.tsv",
    "alignment_matrix.tsv",
    "alignment_matrix_identity.tsv",
    "alignment_owner_backfill_seed_audit.tsv",
)
_CELL_INPUT_FILES = (
    "alignment_backfill_cell_evidence.tsv",
    "alignment_cells.tsv",
)
_OPTIONAL_INPUT_FILES = (
    "alignment_matrix.pre_standard_peak_backfill.tsv",
    "alignment_matrix_identity.pre_standard_peak_backfill.tsv",
    "skipped_evidence_ledger.tsv",
    "alignment_run_metadata.json",
)
_PUBLIC_OUTPUT_FILES = (
    "alignment_review.tsv",
    "alignment_matrix.tsv",
    "alignment_matrix_identity.tsv",
    "alignment_backfill_cell_evidence.tsv",
    "alignment_cells.tsv",
    "alignment_owner_backfill_seed_audit.tsv",
    "skipped_evidence_ledger.tsv",
    "standard_peak_default_matrix_manifest.json",
)

StandardPeakRunner = Callable[..., StandardPeakBackfillPresetOutputs]
PublicationChecker = Callable[..., ProductReadyPresetPublicationCheckOutputs]


@dataclass(frozen=True)
class StageReplayOutputs:
    output_dir: Path
    manifest_json: Path
    timing_json: Path | None
    standard_peak_summary_json: Path
    publication_summary_json: Path


def run_stage_replay(
    *,
    source_alignment_dir: Path,
    output_dir: Path,
    raw_dir: Path,
    dll_dir: Path,
    stage: str = "standard_peak",
    source_run_id: str = DEFAULT_SOURCE_RUN_ID,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    publication_mode: str = DEFAULT_PUBLICATION_MODE,
    min_shape_r: float = DEFAULT_MIN_SHAPE_R,
    render_workers: int = DEFAULT_RENDER_WORKERS,
    chunk_workers: int = DEFAULT_CHUNK_WORKERS,
    evidence_cache_dir: Path | None = None,
    timing_output: Path | None = None,
    timing_live_output: Path | None = None,
    standard_peak_runner: StandardPeakRunner = run_standard_peak_backfill_preset,
    publication_checker: PublicationChecker = check_product_ready_preset_publication,
) -> StageReplayOutputs:
    """Replay an exact-safe product-ready preset stage from copied artifacts."""

    if stage != "standard_peak":
        raise ValueError("only standard_peak stage replay is currently supported")
    if chunk_size < 1:
        raise ValueError("chunk_size must be >= 1")
    if render_workers < 1:
        raise ValueError("render_workers must be >= 1")
    if chunk_workers < 1:
        raise ValueError("chunk_workers must be >= 1")

    source_alignment_dir = source_alignment_dir.resolve()
    output_dir = output_dir.resolve()
    raw_dir = raw_dir.resolve()
    dll_dir = dll_dir.resolve()
    timing_output = timing_output.resolve() if timing_output is not None else None
    timing_live_output = (
        timing_live_output.resolve() if timing_live_output is not None else None
    )
    evidence_cache_dir = (
        evidence_cache_dir.resolve() if evidence_cache_dir is not None else None
    )

    if not source_alignment_dir.is_dir():
        raise ValueError(f"{source_alignment_dir}: source alignment dir not found")
    if source_alignment_dir == output_dir:
        raise ValueError("output_dir must differ from source_alignment_dir")
    if not raw_dir.is_dir():
        raise ValueError(f"{raw_dir}: raw_dir not found")
    if not dll_dir.is_dir():
        raise ValueError(f"{dll_dir}: dll_dir not found")

    copied_inputs = _copy_alignment_inputs(source_alignment_dir, output_dir)
    recorder = TimingRecorder(
        "dna_dr_product_ready_stage_replay",
        live_output_path=timing_live_output,
    )
    standard_peak_outputs = standard_peak_runner(
        alignment_dir=output_dir,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        source_run_id=source_run_id,
        chunk_size=chunk_size,
        reuse_existing=False,
        write_gallery=False,
        publication_mode=publication_mode,
        min_shape_r=min_shape_r,
        render_workers=render_workers,
        chunk_workers=chunk_workers,
        evidence_cache_dir=evidence_cache_dir,
        timing_recorder=recorder,
    )
    with recorder.stage("stage_replay.product_ready_publication_check") as scope:
        publication_outputs = publication_checker(alignment_dir=output_dir)
        scope.metrics["status"] = publication_outputs.status
        scope.metrics["summary_json"] = str(publication_outputs.summary_json)
    timing_path: Path | None = None
    if timing_output is not None:
        timing_path = recorder.write_json(timing_output)

    manifest_json = output_dir / "dna_dr_product_ready_stage_replay_manifest.json"
    manifest = _build_manifest(
        source_alignment_dir=source_alignment_dir,
        output_dir=output_dir,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        copied_inputs=copied_inputs,
        stage=stage,
        source_run_id=source_run_id,
        chunk_size=chunk_size,
        publication_mode=publication_mode,
        min_shape_r=min_shape_r,
        render_workers=render_workers,
        chunk_workers=chunk_workers,
        evidence_cache_dir=evidence_cache_dir,
        timing_output=timing_path,
        timing_live_output=timing_live_output,
        standard_peak_summary_json=standard_peak_outputs.summary_json,
        publication_summary_json=publication_outputs.summary_json,
        publication_status=publication_outputs.status,
    )
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return StageReplayOutputs(
        output_dir=output_dir,
        manifest_json=manifest_json,
        timing_json=timing_path,
        standard_peak_summary_json=standard_peak_outputs.summary_json,
        publication_summary_json=publication_outputs.summary_json,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    outputs = run_stage_replay(
        source_alignment_dir=args.source_alignment_dir,
        output_dir=args.output_dir,
        raw_dir=args.raw_dir,
        dll_dir=args.dll_dir,
        stage=args.stage,
        source_run_id=args.source_run_id,
        chunk_size=args.chunk_size,
        publication_mode=args.publication_mode,
        min_shape_r=args.min_shape_r,
        render_workers=args.render_workers,
        chunk_workers=args.chunk_workers,
        evidence_cache_dir=args.evidence_cache_dir,
        timing_output=args.timing_output,
        timing_live_output=args.timing_live_output,
    )
    print(f"Stage replay manifest JSON: {outputs.manifest_json}")
    print(f"Standard-peak summary JSON: {outputs.standard_peak_summary_json}")
    print(f"Product-ready publication summary JSON: {outputs.publication_summary_json}")
    if outputs.timing_json is not None:
        print(f"Timing JSON: {outputs.timing_json}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-alignment-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--dll-dir", type=Path, required=True)
    parser.add_argument(
        "--stage",
        choices=("standard_peak",),
        default="standard_peak",
        help="Preset stage to replay. Only standard_peak is supported.",
    )
    parser.add_argument("--source-run-id", default=DEFAULT_SOURCE_RUN_ID)
    parser.add_argument("--chunk-size", type=_positive_int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument(
        "--publication-mode",
        choices=("matrix-only", "review-gallery", "deep-audit"),
        default=DEFAULT_PUBLICATION_MODE,
    )
    parser.add_argument("--min-shape-r", type=float, default=DEFAULT_MIN_SHAPE_R)
    parser.add_argument(
        "--render-workers",
        type=_positive_int,
        default=DEFAULT_RENDER_WORKERS,
    )
    parser.add_argument(
        "--chunk-workers",
        type=_positive_int,
        default=DEFAULT_CHUNK_WORKERS,
    )
    parser.add_argument("--timing-output", type=Path)
    parser.add_argument("--timing-live-output", type=Path)
    parser.add_argument(
        "--evidence-cache-dir",
        type=Path,
        help=(
            "Optional content-keyed cache for standard-peak matrix-only overlay "
            "trace evidence. This is an explicit modeling/replay accelerator."
        ),
    )
    return parser.parse_args(argv)


def _copy_alignment_inputs(
    source_alignment_dir: Path,
    output_dir: Path,
) -> dict[str, dict[str, object]]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"{output_dir}: output_dir must be empty for stage replay")
    output_dir.mkdir(parents=True, exist_ok=True)

    source_files = _input_files(source_alignment_dir)
    copied: dict[str, dict[str, object]] = {}
    for name, source_path in source_files.items():
        destination = output_dir / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
        copied[name] = _artifact_descriptor(destination)
    return copied


def _input_files(source_alignment_dir: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    missing = []
    for name in _REQUIRED_INPUT_FILES:
        path = source_alignment_dir / name
        if path.is_file():
            files[name] = path
        else:
            missing.append(name)

    cell_input = next(
        (
            name
            for name in _CELL_INPUT_FILES
            if (source_alignment_dir / name).is_file()
        ),
        None,
    )
    if cell_input is None:
        missing.append("alignment_backfill_cell_evidence.tsv or alignment_cells.tsv")
    else:
        files[cell_input] = source_alignment_dir / cell_input

    if missing:
        raise ValueError(
            f"{source_alignment_dir}: missing required replay inputs: "
            + ", ".join(missing),
        )

    for name in _OPTIONAL_INPUT_FILES:
        path = source_alignment_dir / name
        if path.is_file():
            files[name] = path
    return files


def _build_manifest(
    *,
    source_alignment_dir: Path,
    output_dir: Path,
    raw_dir: Path,
    dll_dir: Path,
    copied_inputs: dict[str, dict[str, object]],
    stage: str,
    source_run_id: str,
    chunk_size: int,
    publication_mode: str,
    min_shape_r: float,
    render_workers: int,
    chunk_workers: int,
    evidence_cache_dir: Path | None,
    timing_output: Path | None,
    timing_live_output: Path | None,
    standard_peak_summary_json: Path,
    publication_summary_json: Path,
    publication_status: str,
) -> dict[str, object]:
    outputs = {
        name: _artifact_descriptor(path)
        for name in _PUBLIC_OUTPUT_FILES
        if (path := output_dir / name).is_file()
    }
    outputs["standard_peak_summary_json"] = _artifact_descriptor(
        standard_peak_summary_json,
    )
    outputs["publication_summary_json"] = _artifact_descriptor(
        publication_summary_json,
    )
    if timing_output is not None and timing_output.is_file():
        outputs["timing_json"] = _artifact_descriptor(timing_output)
    if timing_live_output is not None and timing_live_output.is_file():
        outputs["timing_live_json"] = _artifact_descriptor(timing_live_output)

    return {
        "schema_version": SCHEMA_VERSION,
        "stage": stage,
        "status": "pass" if publication_status == "pass" else "fail",
        "source_alignment_dir": str(source_alignment_dir),
        "output_dir": str(output_dir),
        "raw_dir": str(raw_dir),
        "dll_dir": str(dll_dir),
        "run_config": {
            "source_run_id": source_run_id,
            "chunk_size": chunk_size,
            "publication_mode": publication_mode,
            "min_shape_r": min_shape_r,
            "render_workers": render_workers,
            "chunk_workers": chunk_workers,
            "evidence_cache_dir": (
                str(evidence_cache_dir) if evidence_cache_dir is not None else ""
            ),
        },
        "input_artifacts": copied_inputs,
        "output_artifacts": outputs,
    }


def _artifact_descriptor(path: Path) -> dict[str, object]:
    descriptor: dict[str, object] = {
        "path": str(path.resolve()),
        "sha256": file_sha256(path, uppercase=True),
        "size_bytes": path.stat().st_size,
    }
    if path.suffix.lower() in {".tsv", ".csv"}:
        descriptor["row_count"] = _data_row_count(path)
    return descriptor


def _data_row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        line_count = sum(1 for _line in handle)
    return max(0, line_count - 1)


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
