"""Build a row-completion confidence packet."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from xic_extractor.diagnostics.row_completion_confidence import (
    build_daily_confidence_packet,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs = build_daily_confidence_packet(
            current_alignment_dir=args.current_alignment_dir,
            current_health_dir=args.current_health_dir,
            output_dir=args.output_dir,
            baseline_alignment_dir=args.baseline_alignment_dir,
            run_id=args.run_id,
            generation_context=args.generation_context,
            gate_mode=args.gate_mode,
        )
    except OSError as exc:
        if _is_output_write_failure(exc, args.output_dir):
            print(
                f"Row completion confidence output write failed: {exc}",
                file=sys.stderr,
            )
            return 2
        raise
    print(f"Row completion summary JSON: {outputs.summary_json}")
    print(f"Row completion summary TSV: {outputs.summary_tsv}")
    print(f"Row completion sentinels TSV: {outputs.sentinels_tsv}")
    print(f"Row completion disagreements TSV: {outputs.disagreements_tsv}")
    print(f"Row completion report MD: {outputs.report_md}")
    if args.gate_mode == "product-gate" and not _gate_ok(outputs.summary_json):
        return 1
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build row-completion confidence outputs.",
    )
    parser.add_argument("--current-alignment-dir", type=Path, required=True)
    parser.add_argument("--current-health-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--baseline-alignment-dir", type=Path)
    parser.add_argument(
        "--gate-mode",
        choices=("diagnostic", "product-gate"),
        default="diagnostic",
        help=(
            "diagnostic keeps artifact-acceptance semantics; product-gate "
            "requires a baseline/current comparison and fails closed without it"
        ),
    )
    parser.add_argument("--run-id", default="row_completion_confidence")
    parser.add_argument("--generation-context", default="unknown")
    return parser.parse_args(argv)


def _is_output_write_failure(exc: OSError, output_dir: Path) -> bool:
    output_root = output_dir.resolve(strict=False)
    for raw_path in (exc.filename, exc.filename2):
        if raw_path is None:
            continue
        if _path_is_within_output_dir(Path(raw_path), output_root):
            return True
    return False


def _gate_ok(summary_json: Path) -> bool:
    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    return payload.get("gate_ok") is True


def _path_is_within_output_dir(path: Path, output_root: Path) -> bool:
    candidate = path.resolve(strict=False)
    return candidate == output_root or candidate.is_relative_to(output_root)


if __name__ == "__main__":
    raise SystemExit(main())
