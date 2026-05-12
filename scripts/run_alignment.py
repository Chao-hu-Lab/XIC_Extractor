from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.pipeline import run_alignment
from xic_extractor.config import ExtractionConfig
from xic_extractor.raw_reader import RawReaderError
from xic_extractor.settings_schema import CANONICAL_SETTINGS_DEFAULTS


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    discovery_batch_index = args.discovery_batch_index.resolve()
    raw_dir = args.raw_dir.resolve()
    dll_dir = args.dll_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not discovery_batch_index.is_file():
        print(
            f"{discovery_batch_index}: discovery batch index does not exist",
            file=sys.stderr,
        )
        return 2
    if not raw_dir.is_dir():
        print(f"{raw_dir}: raw directory does not exist", file=sys.stderr)
        return 2
    if not dll_dir.is_dir():
        print(f"{dll_dir}: dll directory does not exist", file=sys.stderr)
        return 2

    try:
        outputs = run_alignment(
            discovery_batch_index=discovery_batch_index,
            raw_dir=raw_dir,
            dll_dir=dll_dir,
            output_dir=output_dir,
            alignment_config=AlignmentConfig(),
            peak_config=_peak_config(raw_dir, dll_dir, output_dir, args.resolver_mode),
            output_level=args.output_level,
            emit_alignment_cells=args.emit_alignment_cells,
            emit_alignment_status_matrix=args.emit_alignment_status_matrix,
        )
    except (RawReaderError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if outputs.workbook is not None:
        print(f"Alignment workbook: {outputs.workbook}")
    if outputs.review_html is not None:
        print(f"Alignment review HTML: {outputs.review_html}")
    if outputs.review_tsv is not None:
        print(f"Alignment review TSV: {outputs.review_tsv}")
    if outputs.matrix_tsv is not None:
        print(f"Alignment matrix TSV: {outputs.matrix_tsv}")
    if outputs.cells_tsv is not None:
        print(f"Alignment cells TSV: {outputs.cells_tsv}")
    if outputs.status_matrix_tsv is not None:
        print(f"Alignment status matrix TSV: {outputs.status_matrix_tsv}")
    if outputs.event_to_owner_tsv is not None:
        print(f"Event to MS1 owner TSV: {outputs.event_to_owner_tsv}")
    if outputs.ambiguous_owners_tsv is not None:
        print(f"Ambiguous MS1 owners TSV: {outputs.ambiguous_owners_tsv}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run untargeted discovery alignment from a discovery batch index.",
    )
    parser.add_argument(
        "--discovery-batch-index",
        type=Path,
        required=True,
        help="Path to discovery_batch_index.csv from xic-discovery-cli --raw-dir.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        required=True,
        help="Authoritative directory containing Thermo RAW files for backfill.",
    )
    parser.add_argument(
        "--dll-dir",
        type=Path,
        required=True,
        help="Directory containing Thermo RawFileReader DLLs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output") / "alignment",
        help="Output directory for alignment_review.tsv and alignment_matrix.tsv.",
    )
    parser.add_argument(
        "--resolver-mode",
        choices=("legacy_savgol", "local_minimum"),
        default="local_minimum",
    )
    parser.add_argument(
        "--output-level",
        choices=("production", "machine", "debug", "validation"),
        default="machine",
        help=(
            "Alignment artifact level. Default remains machine until "
            "owner-based validation acceptance."
        ),
    )
    parser.add_argument("--emit-alignment-cells", action="store_true")
    parser.add_argument("--emit-alignment-status-matrix", action="store_true")
    return parser.parse_args(argv)


def _peak_config(
    raw_dir: Path,
    dll_dir: Path,
    output_dir: Path,
    resolver_mode: str,
) -> ExtractionConfig:
    defaults = CANONICAL_SETTINGS_DEFAULTS
    return ExtractionConfig(
        data_dir=raw_dir,
        dll_dir=dll_dir,
        output_csv=output_dir / "xic_results.csv",
        diagnostics_csv=output_dir / "xic_diagnostics.csv",
        smooth_window=int(defaults["smooth_window"]),
        smooth_polyorder=int(defaults["smooth_polyorder"]),
        peak_rel_height=float(defaults["peak_rel_height"]),
        peak_min_prominence_ratio=float(defaults["peak_min_prominence_ratio"]),
        ms2_precursor_tol_da=float(defaults["ms2_precursor_tol_da"]),
        nl_min_intensity_ratio=float(defaults["nl_min_intensity_ratio"]),
        resolver_mode=resolver_mode,
        resolver_chrom_threshold=float(defaults["resolver_chrom_threshold"]),
        resolver_min_search_range_min=float(defaults["resolver_min_search_range_min"]),
        resolver_min_relative_height=float(defaults["resolver_min_relative_height"]),
        resolver_min_absolute_height=float(defaults["resolver_min_absolute_height"]),
        resolver_min_ratio_top_edge=float(defaults["resolver_min_ratio_top_edge"]),
        resolver_peak_duration_min=float(defaults["resolver_peak_duration_min"]),
        resolver_peak_duration_max=float(defaults["resolver_peak_duration_max"]),
        resolver_min_scans=int(defaults["resolver_min_scans"]),
    )


if __name__ == "__main__":
    raise SystemExit(main())
