from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.drift_evidence import read_targeted_istd_drift_evidence
from xic_extractor.alignment.pipeline import run_alignment
from xic_extractor.alignment.process_backend import AlignmentProcessExecutionError
from xic_extractor.config import ExtractionConfig
from xic_extractor.diagnostics.timing import TimingRecorder
from xic_extractor.raw_reader import RawReaderError
from xic_extractor.settings_schema import CANONICAL_SETTINGS_DEFAULTS, RESOLVER_MODES

_DEFAULT_DRIFT_LOCAL_WINDOW = 40
_DEFAULT_RAW_WORKERS = 1
_DEFAULT_RAW_XIC_BATCH_SIZE = 1
_PERFORMANCE_PROFILES = {
    "validation-fast": {
        "raw_workers": 8,
        "raw_xic_batch_size": 64,
    },
}


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if (args.sample_info is None) != (args.targeted_istd_workbook is None):
        print(
            (
                "--sample-info is required with --targeted-istd-workbook, "
                "and both must be provided together"
            ),
            file=sys.stderr,
        )
        return 2

    discovery_batch_index = args.discovery_batch_index.resolve()
    raw_dir = args.raw_dir.resolve()
    dll_dir = args.dll_dir.resolve()
    output_dir = args.output_dir.resolve()
    raw_workers, raw_xic_batch_size = _resolve_raw_execution_settings(args)
    identity_coherence_output_dir = (
        args.identity_coherence_output_dir.resolve()
        if args.identity_coherence_output_dir is not None
        else None
    )
    identity_coherence_controls_manifest = (
        args.identity_coherence_controls_manifest.resolve()
        if args.emit_identity_coherence_diagnostic
        and args.identity_coherence_controls_manifest is not None
        else None
    )

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
    if (
        args.emit_identity_coherence_diagnostic
        and identity_coherence_controls_manifest is not None
        and not identity_coherence_controls_manifest.is_file()
    ):
        print(
            (
                f"{identity_coherence_controls_manifest}: identity coherence "
                "controls manifest does not exist"
            ),
            file=sys.stderr,
        )
        return 2
    if args.sample_info is not None and args.targeted_istd_workbook is not None:
        sample_info = args.sample_info.resolve()
        targeted_istd_workbook = args.targeted_istd_workbook.resolve()
        if not sample_info.is_file():
            print(f"{sample_info}: sample info does not exist", file=sys.stderr)
            return 2
        if not targeted_istd_workbook.is_file():
            print(
                f"{targeted_istd_workbook}: targeted ISTD workbook does not exist",
                file=sys.stderr,
            )
            return 2
    else:
        sample_info = None
        targeted_istd_workbook = None

    timing_recorder = (
        TimingRecorder("alignment") if args.timing_output is not None else None
    )
    timing_kwargs = (
        {"timing_recorder": timing_recorder}
        if timing_recorder is not None
        else {}
    )
    try:
        drift_lookup = (
            read_targeted_istd_drift_evidence(
                targeted_workbook=targeted_istd_workbook,
                sample_info=sample_info,
                local_window=args.drift_local_window,
            )
            if sample_info is not None and targeted_istd_workbook is not None
            else None
        )
        outputs = run_alignment(
            discovery_batch_index=discovery_batch_index,
            raw_dir=raw_dir,
            dll_dir=dll_dir,
            output_dir=output_dir,
            alignment_config=AlignmentConfig(
                owner_backfill_min_detected_samples=(
                    args.owner_backfill_min_detected_samples
                ),
            ),
            peak_config=_peak_config(
                raw_dir,
                dll_dir,
                output_dir,
                _alignment_production_resolver_mode(args.resolver_mode),
                baseline_audit_method=_baseline_audit_method(args),
            ),
            output_level=args.output_level,
            emit_alignment_cells=args.emit_alignment_cells,
            emit_alignment_status_matrix=args.emit_alignment_status_matrix,
            emit_alignment_integration_audit=args.emit_alignment_integration_audit,
            emit_alignment_backfill_seed_audit=(
                args.emit_alignment_backfill_seed_audit
            ),
            raw_workers=raw_workers,
            raw_xic_batch_size=raw_xic_batch_size,
            owner_backfill_xic_backend=_owner_backfill_xic_backend(
                args.owner_backfill_xic_backend
            ),
            preconsolidate_owner_families=args.preconsolidate_owner_families,
            emit_identity_coherence_diagnostic=(
                args.emit_identity_coherence_diagnostic
            ),
            identity_coherence_output_dir=identity_coherence_output_dir,
            identity_coherence_controls_manifest=identity_coherence_controls_manifest,
            drift_lookup=drift_lookup,
            **timing_kwargs,
        )
    except (
        AlignmentProcessExecutionError,
        RawReaderError,
        ValueError,
        OSError,
        KeyError,
    ) as exc:
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
    if outputs.integration_audit_tsv is not None:
        print(f"Alignment integration audit TSV: {outputs.integration_audit_tsv}")
    if outputs.backfill_seed_audit_tsv is not None:
        print(f"Alignment backfill seed audit TSV: {outputs.backfill_seed_audit_tsv}")
    if outputs.status_matrix_tsv is not None:
        print(f"Alignment status matrix TSV: {outputs.status_matrix_tsv}")
    if outputs.event_to_owner_tsv is not None:
        print(f"Event to MS1 owner TSV: {outputs.event_to_owner_tsv}")
    if outputs.ambiguous_owners_tsv is not None:
        print(f"Ambiguous MS1 owners TSV: {outputs.ambiguous_owners_tsv}")
    if outputs.edge_evidence_tsv is not None:
        print(f"Owner edge evidence TSV: {outputs.edge_evidence_tsv}")
    if outputs.identity_coherence_output_dir is not None:
        print(
            "Identity coherence diagnostic: "
            f"{outputs.identity_coherence_output_dir}"
        )
    if timing_recorder is not None:
        timing_path = args.timing_output.resolve()
        timing_recorder.write_json(timing_path)
        print(f"Timing JSON: {timing_path}")
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
        "--timing-output",
        type=Path,
        help="Optional JSON path for alignment stage timing.",
    )
    parser.add_argument(
        "--raw-workers",
        type=_positive_int,
        help=(
            "Number of RAW worker processes for sample-local alignment backfill. "
            f"Default {_DEFAULT_RAW_WORKERS}, unless --performance-profile sets "
            "a profile value."
        ),
    )
    parser.add_argument(
        "--raw-xic-batch-size",
        type=_positive_int,
        default=None,
        help=(
            "Maximum XIC requests per RAW API batch. Default "
            f"{_DEFAULT_RAW_XIC_BATCH_SIZE} preserves the pre-batch execution "
            "shape unless --performance-profile sets a profile value."
        ),
    )
    parser.add_argument(
        "--performance-profile",
        choices=tuple(_PERFORMANCE_PROFILES),
        help=(
            "Named alignment execution profile. 'validation-fast' uses the "
            "8-RAW-equivalent fast path: raw-workers=8 and "
            "raw-xic-batch-size=64. Explicit raw flags override profile values."
        ),
    )
    parser.add_argument(
        "--owner-backfill-min-detected-samples",
        type=_positive_int,
        default=1,
        help=(
            "Only run owner-centered MS1 backfill for features detected in at "
            "least this many samples. Default 1 preserves full backfill."
        ),
    )
    parser.add_argument(
        "--owner-backfill-xic-backend",
        choices=("raw", "ms1-index", "ms1-index-hybrid"),
        default="raw",
        help=(
            "XIC backend for owner-centered MS1 backfill. Default 'raw' uses "
            "Thermo vendor chromatograms. 'ms1-index' is an explicit "
            "approximate fast mode and may change peak areas. "
            "'ms1-index-hybrid' uses MS1-index prefiltering but writes "
            "vendor-confirmed rescued cells."
        ),
    )
    parser.add_argument(
        "--preconsolidate-owner-families",
        action="store_true",
        help=(
            "Experimental algorithm mode: merge identity-compatible "
            "single-sample owner families before owner-centered backfill."
        ),
    )
    parser.add_argument(
        "--emit-identity-coherence-diagnostic",
        action="store_true",
        help=(
            "Emit the opt-in pre-Backfill identity coherence diagnostic. "
            "This diagnostic writes sidecar outputs and does not mutate the "
            "alignment matrix."
        ),
    )
    parser.add_argument(
        "--identity-coherence-output-dir",
        type=Path,
        help=(
            "Output directory for identity coherence diagnostic sidecars. "
            "Defaults to <output-dir>/identity_coherence when the diagnostic "
            "is enabled."
        ),
    )
    parser.add_argument(
        "--identity-coherence-controls-manifest",
        type=Path,
        help=(
            "Optional controls manifest for the identity coherence diagnostic. "
            "Ignored unless --emit-identity-coherence-diagnostic is set."
        ),
    )
    parser.add_argument(
        "--sample-info",
        type=Path,
        help="Sample metadata CSV used with --targeted-istd-workbook for drift priors.",
    )
    parser.add_argument(
        "--targeted-istd-workbook",
        type=Path,
        help="Targeted ISTD workbook used with --sample-info for drift priors.",
    )
    parser.add_argument(
        "--drift-local-window",
        type=_positive_int,
        default=_DEFAULT_DRIFT_LOCAL_WINDOW,
        help=(
            "Injection-order half-window used to build targeted ISTD drift "
            f"priors. Default {_DEFAULT_DRIFT_LOCAL_WINDOW} supports sparse "
            "validation subsets while preserving sample-local rolling medians."
        ),
    )
    parser.add_argument(
        "--resolver-mode",
        choices=RESOLVER_MODES,
        default="region_first_safe_merge",
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
    parser.add_argument("--emit-alignment-integration-audit", action="store_true")
    parser.add_argument(
        "--emit-baseline-audit-asls",
        action="store_true",
        help="Emit AsLS shadow columns in alignment_cell_integration_audit.tsv.",
    )
    parser.add_argument("--emit-alignment-backfill-seed-audit", action="store_true")
    parser.add_argument("--emit-alignment-status-matrix", action="store_true")
    return parser.parse_args(argv)


def _resolve_raw_execution_settings(args: argparse.Namespace) -> tuple[int, int]:
    profile = _PERFORMANCE_PROFILES.get(args.performance_profile or "", {})
    raw_workers = (
        args.raw_workers
        if args.raw_workers is not None
        else profile.get("raw_workers", _DEFAULT_RAW_WORKERS)
    )
    raw_xic_batch_size = (
        args.raw_xic_batch_size
        if args.raw_xic_batch_size is not None
        else profile.get("raw_xic_batch_size", _DEFAULT_RAW_XIC_BATCH_SIZE)
    )
    return raw_workers, raw_xic_batch_size


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be an integer >= 1") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be an integer >= 1")
    return parsed


def _owner_backfill_xic_backend(value: str) -> str:
    if value == "ms1-index":
        return "ms1_index"
    if value == "ms1-index-hybrid":
        return "ms1_index_hybrid"
    return value


def _alignment_production_resolver_mode(resolver_mode: str) -> str:
    if resolver_mode == "region_first_safe_merge":
        return "local_minimum"
    return resolver_mode


def _baseline_audit_method(args: argparse.Namespace) -> str:
    if args.emit_baseline_audit_asls:
        return "asls"
    env_method = os.environ.get("BASELINE_AUDIT_METHOD", "").strip().lower()
    if env_method in {"", "asls"}:
        return env_method
    raise ValueError("BASELINE_AUDIT_METHOD must be empty or asls")


def _peak_config(
    raw_dir: Path,
    dll_dir: Path,
    output_dir: Path,
    resolver_mode: str,
    baseline_audit_method: str = "",
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
        baseline_audit_method=baseline_audit_method,
    )


if __name__ == "__main__":
    raise SystemExit(main())
