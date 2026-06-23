"""Evaluate standard-peak held-out oracle result rows."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from xic_extractor.diagnostics.diagnostic_io import read_tsv_required
from xic_extractor.diagnostics.standard_peak_shadow_activation_inputs import (
    HELDOUT_ORACLE_MANIFEST_REQUIRED_COLUMNS,
    HELDOUT_ORACLE_OBSERVED_REQUIRED_COLUMNS,
    build_heldout_oracle_results,
    write_heldout_oracle_results,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    manifest_rows = read_tsv_required(
        args.heldout_oracle_manifest_tsv,
        HELDOUT_ORACLE_MANIFEST_REQUIRED_COLUMNS,
    )
    observed_rows = read_tsv_required(
        args.observed_results_tsv,
        HELDOUT_ORACLE_OBSERVED_REQUIRED_COLUMNS,
    )
    rows = build_heldout_oracle_results(
        manifest_rows,
        observed_rows,
        result_source_artifact_path=args.result_source_artifact,
    )
    args.output_tsv.parent.mkdir(parents=True, exist_ok=True)
    write_heldout_oracle_results(args.output_tsv, rows)
    print(f"Held-out oracle results TSV: {args.output_tsv}")
    print(f"Held-out oracle cases: {len(rows)}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--heldout-oracle-manifest-tsv", type=Path, required=True)
    parser.add_argument("--observed-results-tsv", type=Path, required=True)
    parser.add_argument("--result-source-artifact", type=Path, required=True)
    parser.add_argument("--output-tsv", type=Path, required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
