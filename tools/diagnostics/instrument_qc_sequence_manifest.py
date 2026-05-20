from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from xic_extractor.instrument_qc.sequence_manifest import build_sequence_manifest
from xic_extractor.instrument_qc.sequence_manifest_writers import (
    write_injection_order_csv,
    write_sequence_manifest_json,
    write_sequence_manifest_markdown,
    write_sequence_manifest_tsv,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build docs-derived instrument QC sequence manifest.",
    )
    parser.add_argument("--method-doc", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.method_doc.exists():
        print(f"method doc not found: {args.method_doc}", file=sys.stderr)
        return 2
    if args.method_doc.name.casefold().startswith("sampleinfo"):
        print(
            "SampleInfo is downstream evidence, not an accepted method-doc input.",
            file=sys.stderr,
        )
        return 2
    if args.method_doc.suffix.lower() != ".docx":
        print(
            f"unsupported method doc type: {args.method_doc.suffix}",
            file=sys.stderr,
        )
        return 2
    if not args.raw_dir.exists():
        print(f"raw dir not found: {args.raw_dir}", file=sys.stderr)
        return 2

    try:
        rows = build_sequence_manifest(
            method_doc=args.method_doc,
            raw_dir=args.raw_dir,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    output_dir = args.output_dir
    manifest_tsv = output_dir / "instrument_qc_sequence_manifest.tsv"
    injection_order_csv = output_dir / "instrument_qc_injection_order.csv"
    manifest_json = output_dir / "instrument_qc_sequence_manifest.json"
    manifest_md = output_dir / "instrument_qc_sequence_manifest.md"

    write_sequence_manifest_tsv(manifest_tsv, rows)
    write_injection_order_csv(injection_order_csv, rows)
    write_sequence_manifest_json(manifest_json, rows)
    write_sequence_manifest_markdown(manifest_md, rows)

    print(f"Wrote {manifest_tsv}")
    print(f"Wrote {injection_order_csv}")
    print(f"Wrote {manifest_json}")
    print(f"Wrote {manifest_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
