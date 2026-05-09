import argparse
import math
import sys
from collections.abc import Sequence
from pathlib import Path

from xic_extractor.config import ExtractionConfig
from xic_extractor.discovery.models import DiscoverySettings, NeutralLossProfile
from xic_extractor.discovery.pipeline import run_discovery
from xic_extractor.raw_reader import RawReaderError
from xic_extractor.settings_schema import CANONICAL_SETTINGS_DEFAULTS

_RT_BOUND_ERROR = "RT bounds must be finite values >= 0"


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    raw_path = args.raw.resolve()
    dll_dir = args.dll_dir.resolve()
    output_dir = args.output_dir.resolve()
    if not raw_path.is_file():
        print(f"{raw_path}: raw file does not exist", file=sys.stderr)
        return 2
    if not dll_dir.is_dir():
        print(f"{dll_dir}: dll directory does not exist", file=sys.stderr)
        return 2

    settings = DiscoverySettings(
        neutral_loss_profile=NeutralLossProfile(
            tag=args.neutral_loss_tag,
            neutral_loss_da=args.neutral_loss_da,
        ),
        nl_tolerance_ppm=args.nl_tolerance_ppm,
        precursor_mz_tolerance_ppm=args.precursor_mz_tolerance_ppm,
        product_mz_tolerance_ppm=args.product_mz_tolerance_ppm,
        product_search_ppm=args.product_search_ppm,
        nl_min_intensity_ratio=args.nl_min_intensity_ratio,
        seed_rt_gap_min=args.seed_rt_gap_min,
        ms1_search_padding_min=args.ms1_search_padding_min,
        rt_min=args.rt_min,
        rt_max=args.rt_max,
        resolver_mode=args.resolver_mode,
    )
    peak_config = _peak_config(raw_path, dll_dir, output_dir, settings)
    try:
        output_path = run_discovery(
            raw_path,
            output_dir=output_dir,
            settings=settings,
            peak_config=peak_config,
        )
    except RawReaderError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Discovery CSV: {output_path}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run single-RAW strict MS2 neutral-loss discovery."
    )
    parser.add_argument("--raw", type=Path, required=True, help="Thermo RAW file.")
    parser.add_argument(
        "--dll-dir",
        type=Path,
        required=True,
        help="Directory containing Thermo RawFileReader DLLs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output") / "discovery",
        help="Directory for discovery_candidates.csv.",
    )
    parser.add_argument("--neutral-loss-tag", default="DNA_dR")
    parser.add_argument("--neutral-loss-da", type=_positive_float, default=116.0474)
    parser.add_argument("--nl-tolerance-ppm", type=_positive_float, default=20.0)
    parser.add_argument(
        "--precursor-mz-tolerance-ppm",
        type=_positive_float,
        default=20.0,
    )
    parser.add_argument(
        "--product-mz-tolerance-ppm",
        type=_positive_float,
        default=20.0,
    )
    parser.add_argument("--product-search-ppm", type=_positive_float, default=50.0)
    parser.add_argument("--nl-min-intensity-ratio", type=_positive_float, default=0.01)
    parser.add_argument("--seed-rt-gap-min", type=_positive_float, default=0.20)
    parser.add_argument("--ms1-search-padding-min", type=_positive_float, default=0.20)
    parser.add_argument("--rt-min", type=_rt_bound, default=0.0)
    parser.add_argument("--rt-max", type=_rt_bound, default=999.0)
    parser.add_argument(
        "--resolver-mode",
        choices=("legacy_savgol", "local_minimum"),
        default="local_minimum",
    )
    args = parser.parse_args(argv)
    if args.rt_min > args.rt_max:
        parser.error("rt-min must be <= rt-max")
    return args


def _peak_config(
    raw_path: Path,
    dll_dir: Path,
    output_dir: Path,
    settings: DiscoverySettings,
) -> ExtractionConfig:
    defaults = CANONICAL_SETTINGS_DEFAULTS
    return ExtractionConfig(
        data_dir=raw_path.parent,
        dll_dir=dll_dir,
        output_csv=output_dir / "xic_results.csv",
        diagnostics_csv=output_dir / "xic_diagnostics.csv",
        smooth_window=int(defaults["smooth_window"]),
        smooth_polyorder=int(defaults["smooth_polyorder"]),
        peak_rel_height=float(defaults["peak_rel_height"]),
        peak_min_prominence_ratio=float(defaults["peak_min_prominence_ratio"]),
        ms2_precursor_tol_da=float(defaults["ms2_precursor_tol_da"]),
        nl_min_intensity_ratio=settings.nl_min_intensity_ratio,
        resolver_mode=settings.resolver_mode,
        resolver_chrom_threshold=float(defaults["resolver_chrom_threshold"]),
        resolver_min_search_range_min=float(defaults["resolver_min_search_range_min"]),
        resolver_min_relative_height=float(defaults["resolver_min_relative_height"]),
        resolver_min_absolute_height=float(defaults["resolver_min_absolute_height"]),
        resolver_min_ratio_top_edge=float(defaults["resolver_min_ratio_top_edge"]),
        resolver_peak_duration_min=float(defaults["resolver_peak_duration_min"]),
        resolver_peak_duration_max=float(defaults["resolver_peak_duration_max"]),
        resolver_min_scans=int(defaults["resolver_min_scans"]),
    )


def _positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a float") from exc
    if parsed <= 0.0:
        raise argparse.ArgumentTypeError("value must be > 0")
    return parsed


def _rt_bound(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(_RT_BOUND_ERROR) from exc
    if not math.isfinite(parsed) or parsed < 0.0:
        raise argparse.ArgumentTypeError(_RT_BOUND_ERROR)
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
