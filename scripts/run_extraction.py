import argparse
import sys
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from xic_extractor import extractor
from xic_extractor.config import ConfigError, ExtractionConfig, load_config
from xic_extractor.output.excel_pipeline import write_excel_from_run_output
from xic_extractor.raw_reader import RawReaderError


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    base_dir = args.base_dir.resolve()
    try:
        config, targets = load_config(base_dir / "config")
        if args.data_dir is not None:
            data_dir = args.data_dir.resolve()
            if not data_dir.is_dir():
                raise ConfigError(f"{data_dir}: data_dir override must be a directory")
            config = replace(config, data_dir=data_dir)
        run_config = (
            replace(config, keep_intermediate_csv=True)
            if args.skip_excel
            else config
        )

        output = extractor.run(
            run_config,
            targets,
            progress_callback=_print_progress,
        )
    except (ConfigError, RawReaderError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Processed files: {len(output.file_results)}")
    print(f"Diagnostics: {len(output.diagnostics)}")

    if args.skip_excel:
        print("Excel skipped.")
        return 0

    write_excel_from_run_output(
        config,
        targets,
        output,
        output_path=_excel_output_path(config),
    )
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
        "--data-dir",
        type=Path,
        default=None,
        help="Override settings.csv data_dir for validation subsets.",
    )
    parser.add_argument(
        "--skip-excel",
        action="store_true",
        help="Write CSV outputs only and skip Excel conversion.",
    )
    parser.add_argument(
        "--excel",
        action="store_true",
        help="Run Excel conversion after writing CSV outputs; this is the default.",
    )
    return parser.parse_args(argv)


def _print_progress(current: int, total: int, filename: str) -> None:
    print(f"{current}/{total} {filename}")


def _excel_output_path(config: ExtractionConfig) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return config.output_csv.parent / f"xic_results_{timestamp}.xlsx"


if __name__ == "__main__":
    raise SystemExit(main())
