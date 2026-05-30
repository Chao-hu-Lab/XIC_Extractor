"""Build nearest-QC MS1 pattern reference diagnostics from overlay traces."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from tools.diagnostics.diagnostic_io import read_tsv_required, text_value
from xic_extractor.alignment.shared_peak_identity_explanation import (
    qc_ms1_pattern_reference as qc_reference,
)
from xic_extractor.injection_rolling import read_injection_order


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        keys = _load_oracle_keys(args.manual_oracle_tsv, args.oracle_key)
        rows = qc_reference.build_qc_ms1_pattern_reference_rows(
            family_ms1_overlay_trace_data_jsons=args.overlay_trace_data_json,
            oracle_keys=keys,
            injection_order=read_injection_order(args.injection_order_source),
            max_injection_order_delta=args.max_injection_order_delta,
        )
        qc_reference.write_qc_ms1_pattern_reference_rows(args.output_tsv, rows)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"qc_ms1_pattern_reference_tsv: {args.output_tsv}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overlay-trace-data-json",
        action="append",
        type=Path,
        required=True,
        help="family_ms1_overlay_plot trace_data.json. Repeat for multiple families.",
    )
    parser.add_argument(
        "--injection-order-source",
        type=Path,
        required=True,
        help="CSV/XLSX containing Sample_Name and Injection_Order columns.",
    )
    parser.add_argument(
        "--manual-oracle-tsv",
        type=Path,
        help="TSV with feature_family_id and sample_id columns.",
    )
    parser.add_argument(
        "--oracle-key",
        action="append",
        default=[],
        help="Feature/sample key as FAM000000|SampleStem. Repeat as needed.",
    )
    parser.add_argument(
        "--max-injection-order-delta",
        type=int,
        help="Optional maximum injection-order gap for decisive QC reference status.",
    )
    parser.add_argument("--output-tsv", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.manual_oracle_tsv is None and not args.oracle_key:
        parser.error("provide --manual-oracle-tsv or at least one --oracle-key")
    if (
        args.max_injection_order_delta is not None
        and args.max_injection_order_delta < 0
    ):
        parser.error("--max-injection-order-delta must be non-negative")
    return args


def _load_oracle_keys(
    manual_oracle_tsv: Path | None,
    oracle_keys: Sequence[str],
) -> tuple[tuple[str, str], ...]:
    keys: list[tuple[str, str]] = []
    if manual_oracle_tsv is not None:
        rows = read_tsv_required(manual_oracle_tsv, ("feature_family_id", "sample_id"))
        keys.extend(
            (
                text_value(row.get("feature_family_id")),
                text_value(row.get("sample_id")),
            )
            for row in rows
        )
    keys.extend(_parse_oracle_key(value) for value in oracle_keys)
    cleaned = tuple(
        (family_id, sample) for family_id, sample in keys if family_id and sample
    )
    if not cleaned:
        raise ValueError("no oracle keys were supplied")
    return tuple(dict.fromkeys(cleaned))


def _parse_oracle_key(value: str) -> tuple[str, str]:
    separator = "|" if "|" in value else ","
    parts = [part.strip() for part in value.split(separator, 1)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(
            "--oracle-key must use FAM000000|SampleStem or FAM000000,SampleStem"
        )
    return parts[0], parts[1]


if __name__ == "__main__":
    raise SystemExit(main())
