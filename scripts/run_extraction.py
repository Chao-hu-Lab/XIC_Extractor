import argparse
import multiprocessing
import sys
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from xic_extractor import extractor
from xic_extractor.config import ConfigError, ExtractionConfig, load_config
from xic_extractor.output.excel_pipeline import write_excel_from_run_output
from xic_extractor.output.method_manifest import (
    MethodManifestContext,
    MethodManifestError,
    load_method_manifest_for_replay,
    write_method_manifest,
)
from xic_extractor.peak_detection.model_selection_approval_registry import (
    load_expected_diff_approval_registry,
)
from xic_extractor.raw_reader import RawReaderError
from xic_extractor.targeted_ms1_shape_identity_policy import (
    TARGETED_MS1_SHAPE_IDENTITY_ACTIVATION_POLICIES,
)


def main(argv: Sequence[str] | None = None) -> int:
    multiprocessing.freeze_support()
    cli_argv = tuple(sys.argv[1:] if argv is None else argv)
    args = _parse_args(argv)
    try:
        replay_request = None
        if args.replay_manifest is not None:
            _reject_replay_overrides(args)
            replay_request = load_method_manifest_for_replay(args.replay_manifest)
            base_dir = replay_request.base_dir
            config_dir = replay_request.config_dir
            settings_overrides = replay_request.settings_overrides
            output_mode = replay_request.output_mode
        else:
            base_dir = (args.base_dir or Path.cwd()).resolve()
            config_dir = base_dir / "config"
            settings_overrides = {}
            output_mode = "csv_only" if args.skip_excel else "excel"
            if args.data_dir is not None:
                data_dir = args.data_dir.resolve()
                if not data_dir.is_dir():
                    raise ConfigError(
                        f"{data_dir}: data_dir override must be a directory"
                    )
                settings_overrides["data_dir"] = str(data_dir)
            if args.model_selection_expected_diff_approvals is not None:
                settings_overrides[
                    "model_selection_expected_diff_approval_registry"
                ] = str(args.model_selection_expected_diff_approvals.resolve())
            if args.targeted_ms1_shape_identity_support_tsv is not None:
                settings_overrides["targeted_ms1_shape_identity_support_tsv"] = str(
                    args.targeted_ms1_shape_identity_support_tsv.resolve()
                )
            if args.targeted_ms1_shape_identity_activation_policy is not None:
                settings_overrides[
                    "targeted_ms1_shape_identity_activation_policy"
                ] = args.targeted_ms1_shape_identity_activation_policy

        if settings_overrides:
            config, targets = load_config(
                config_dir,
                settings_overrides=settings_overrides,
            )
        else:
            config, targets = load_config(config_dir)
        if replay_request is None and args.parallel_mode is not None:
            config = replace(config, parallel_mode=args.parallel_mode)
        if replay_request is None and args.parallel_workers is not None:
            config = replace(config, parallel_workers=args.parallel_workers)
        if replay_request is not None:
            config = replace(
                config,
                parallel_mode=replay_request.parallel_mode,
                parallel_workers=replay_request.parallel_workers,
            )
        skip_excel = output_mode == "csv_only"
        run_config = (
            replace(config, keep_intermediate_csv=True)
            if skip_excel
            else config
        )
        approval_registry_path = (
            run_config.model_selection_expected_diff_approval_registry
        )
        try:
            model_selection_expected_diff_approvals = (
                load_expected_diff_approval_registry(approval_registry_path)
                if approval_registry_path is not None
                else None
            )
        except ValueError as exc:
            raise ConfigError(str(exc)) from exc

        output = extractor.run(
            run_config,
            targets,
            progress_callback=_print_progress,
            model_selection_expected_diff_approvals=(
                model_selection_expected_diff_approvals
            ),
        )
        write_method_manifest(
            run_config,
            targets,
            context=MethodManifestContext(
                entrypoint=(
                    "xic-extractor-cli-replay"
                    if replay_request is not None
                    else "xic-extractor-cli"
                ),
                argv=cli_argv,
                base_dir=base_dir,
                config_dir=config_dir,
                settings_overrides=settings_overrides,
                output_mode=output_mode,
            ),
        )
    except (ConfigError, MethodManifestError, RawReaderError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Processed files: {len(output.file_results)}")
    print(f"Diagnostics: {len(output.diagnostics)}")

    if skip_excel:
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
        default=None,
        help="Project/base directory containing config/ and output/.",
    )
    parser.add_argument(
        "--replay-manifest",
        type=Path,
        default=None,
        help=(
            "Replay a previous xic-extractor-cli run from method_manifest.json. "
            "Replay mode does not accept runtime override flags."
        ),
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
    parser.add_argument(
        "--parallel-mode",
        choices=("serial", "process"),
        default=None,
        help="Override settings.csv parallel_mode.",
    )
    parser.add_argument(
        "--parallel-workers",
        type=_positive_int,
        default=None,
        help="Override settings.csv parallel_workers.",
    )
    parser.add_argument(
        "--model-selection-expected-diff-approvals",
        type=Path,
        default=None,
        help=(
            "Override settings.csv model_selection_expected_diff_approval_registry "
            "with a durable expected-diff approval TSV."
        ),
    )
    parser.add_argument(
        "--targeted-ms1-shape-identity-support-tsv",
        type=Path,
        default=None,
        help=(
            "Override settings.csv targeted_ms1_shape_identity_support_tsv with a "
            "reviewed targeted_ms1_shape_identity_v0 support TSV."
        ),
    )
    parser.add_argument(
        "--targeted-ms1-shape-identity-activation-policy",
        choices=TARGETED_MS1_SHAPE_IDENTITY_ACTIVATION_POLICIES,
        default=None,
        help=(
            "Override settings.csv targeted_ms1_shape_identity_activation_policy. "
            "Use limited_5hmdc_5medc_v1 to restrict support TSV activation to "
            "5-hmdC and 5-medC."
        ),
    )
    return parser.parse_args(argv)


def _reject_replay_overrides(args: argparse.Namespace) -> None:
    conflicts = []
    if args.base_dir is not None:
        conflicts.append("--base-dir")
    if args.data_dir is not None:
        conflicts.append("--data-dir")
    if args.skip_excel:
        conflicts.append("--skip-excel")
    if args.excel:
        conflicts.append("--excel")
    if args.parallel_mode is not None:
        conflicts.append("--parallel-mode")
    if args.parallel_workers is not None:
        conflicts.append("--parallel-workers")
    if args.model_selection_expected_diff_approvals is not None:
        conflicts.append("--model-selection-expected-diff-approvals")
    if args.targeted_ms1_shape_identity_support_tsv is not None:
        conflicts.append("--targeted-ms1-shape-identity-support-tsv")
    if args.targeted_ms1_shape_identity_activation_policy is not None:
        conflicts.append("--targeted-ms1-shape-identity-activation-policy")
    if conflicts:
        joined = ", ".join(conflicts)
        raise ConfigError(f"--replay-manifest cannot be combined with {joined}")


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("parallel-workers must be >= 1")
    return parsed


def _print_progress(current: int, total: int, filename: str) -> None:
    print(f"{current}/{total} {filename}")


def _excel_output_path(config: ExtractionConfig) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return config.output_csv.parent / f"xic_results_{timestamp}.xlsx"


if __name__ == "__main__":
    raise SystemExit(main())
