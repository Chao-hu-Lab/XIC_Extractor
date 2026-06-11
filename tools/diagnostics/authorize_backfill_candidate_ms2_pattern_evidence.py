"""Authorize reviewed Candidate MS2 pattern sidecar rows for product projection."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.alignment import (
    backfill_candidate_ms2_product_authority as authority,
)
from xic_extractor.diagnostics.diagnostic_io import read_tsv_required, write_tsv
from xic_extractor.tabular_io import read_tsv_with_header


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        source_header, source_rows = read_tsv_with_header(
            args.candidate_ms2_pattern_evidence_tsv,
            required_columns=authority.required_candidate_ms2_pattern_columns(),
            encoding="utf-8-sig",
        )
        allowlist_rows = read_tsv_required(
            args.authority_allowlist_tsv,
            authority.ALLOWLIST_COLUMNS,
        )
        result = authority.authorize_candidate_ms2_pattern_rows(
            candidate_ms2_pattern_rows=source_rows,
            allowlist_rows=allowlist_rows,
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        authorized_tsv = (
            args.output_dir
            / "shared_peak_identity_candidate_ms2_pattern_product_authorized.tsv"
        )
        audit_tsv = (
            args.output_dir / "backfill_candidate_ms2_product_authority_audit.tsv"
        )
        summary_json = (
            args.output_dir
            / "backfill_candidate_ms2_product_authority_summary.json"
        )
        write_tsv(
            authorized_tsv,
            result.authorized_rows,
            authority.output_columns(source_header),
            lineterminator="\n",
        )
        write_tsv(
            audit_tsv,
            result.audit_rows,
            authority.AUDIT_COLUMNS,
            lineterminator="\n",
        )
        summary_json.write_text(
            json.dumps(result.summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Product-authorized Candidate MS2 pattern TSV: {authorized_tsv}")
    print(f"Product authority audit TSV: {audit_tsv}")
    print(f"Product authority summary JSON: {summary_json}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate-ms2-pattern-evidence-tsv",
        type=Path,
        required=True,
        help=(
            "Source diagnostic "
            "shared_peak_identity_candidate_ms2_pattern_evidence.tsv."
        ),
    )
    parser.add_argument(
        "--authority-allowlist-tsv",
        type=Path,
        required=True,
        help="Reviewed backfill Candidate MS2 product authority allowlist TSV.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for product-authorized sidecar, audit, and summary outputs.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
