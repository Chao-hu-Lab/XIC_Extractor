from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from xic_extractor.alignment.validation_pipeline import run_alignment_validation


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    try:
        alignment_review, alignment_matrix = _alignment_inputs(args)
        legacy_paths = _legacy_paths(args)
        if not legacy_paths:
            raise ValueError("at least one legacy source is required")
        _require_file(alignment_review, "alignment review")
        _require_file(alignment_matrix, "alignment matrix")
        for label, path in legacy_paths.items():
            _require_file(path, label)
        outputs = run_alignment_validation(
            alignment_review=alignment_review,
            alignment_matrix=alignment_matrix,
            output_dir=args.output_dir.resolve(),
            legacy_fh_tsv=legacy_paths.get("legacy FH TSV"),
            legacy_metabcombiner_tsv=legacy_paths.get("legacy metabCombiner TSV"),
            legacy_combine_fix_xlsx=legacy_paths.get("legacy combine-fix XLSX"),
            match_ppm=args.match_ppm,
            match_rt_sec=args.match_rt_sec,
            sample_scope=args.sample_scope,
            match_distance_warn_median=args.match_distance_warn_median,
            match_distance_warn_p90=args.match_distance_warn_p90,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Validation summary TSV: {outputs.summary_tsv}")
    print(f"Validation legacy matches TSV: {outputs.matches_tsv}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate XIC alignment outputs against legacy matrices.",
    )
    parser.add_argument(
        "--alignment-dir",
        type=Path,
        help="Directory containing alignment_review.tsv and alignment_matrix.tsv.",
    )
    parser.add_argument("--alignment-review", type=Path)
    parser.add_argument("--alignment-matrix", type=Path)
    parser.add_argument("--legacy-fh-tsv", type=Path)
    parser.add_argument("--legacy-metabcombiner-tsv", type=Path)
    parser.add_argument("--legacy-combine-fix-xlsx", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output") / "alignment_validation",
    )
    parser.add_argument("--match-ppm", type=float, default=20.0)
    parser.add_argument("--match-rt-sec", type=float, default=60.0)
    parser.add_argument(
        "--sample-scope",
        choices=("xic", "legacy", "intersection"),
        default="xic",
    )
    parser.add_argument("--match-distance-warn-median", type=float, default=0.5)
    parser.add_argument("--match-distance-warn-p90", type=float, default=0.8)
    return parser.parse_args(argv)


def _alignment_inputs(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.alignment_dir is not None:
        alignment_dir = args.alignment_dir.resolve()
        return (
            alignment_dir / "alignment_review.tsv",
            alignment_dir / "alignment_matrix.tsv",
        )
    if args.alignment_review is None or args.alignment_matrix is None:
        raise ValueError(
            "--alignment-dir or both --alignment-review and --alignment-matrix "
            "are required"
        )
    return args.alignment_review.resolve(), args.alignment_matrix.resolve()


def _legacy_paths(args: argparse.Namespace) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    if args.legacy_fh_tsv is not None:
        paths["legacy FH TSV"] = args.legacy_fh_tsv.resolve()
    if args.legacy_metabcombiner_tsv is not None:
        paths["legacy metabCombiner TSV"] = args.legacy_metabcombiner_tsv.resolve()
    if args.legacy_combine_fix_xlsx is not None:
        paths["legacy combine-fix XLSX"] = args.legacy_combine_fix_xlsx.resolve()
    return paths


def _require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise ValueError(f"{path}: {label} does not exist")


if __name__ == "__main__":
    raise SystemExit(main())
