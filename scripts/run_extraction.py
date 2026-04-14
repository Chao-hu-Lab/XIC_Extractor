import argparse
from collections.abc import Sequence
from pathlib import Path

from scripts import csv_to_excel
from xic_extractor import extractor
from xic_extractor.config import load_config


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    base_dir = args.base_dir.resolve()
    config, targets = load_config(base_dir / "config")

    output = extractor.run(
        config,
        targets,
        progress_callback=_print_progress,
    )
    print(f"Processed files: {len(output.file_results)}")
    print(f"Diagnostics: {len(output.diagnostics)}")

    if args.skip_excel:
        print("Excel skipped.")
        return 0

    csv_to_excel.run(base_dir)
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Python XIC extraction and optional Excel conversion."
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path.cwd(),
        help="Project/base directory containing config/ and output/.",
    )
    parser.add_argument(
        "--skip-excel",
        action="store_true",
        help="Write CSV outputs only; skip Excel conversion.",
    )
    return parser.parse_args(argv)


def _print_progress(current: int, total: int, filename: str) -> None:
    print(f"{current}/{total} {filename}")


if __name__ == "__main__":
    raise SystemExit(main())
