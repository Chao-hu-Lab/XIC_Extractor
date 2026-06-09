"""Write diagnostic-only PeakHypothesis backfill promotion projection outputs."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.diagnostics import backfill_peakhypothesis_promotion as promotion
from xic_extractor.diagnostics.diagnostic_io import read_tsv_required


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        shadow_rows = read_tsv_required(
            args.shadow_projection_cells_tsv,
            promotion.SHADOW_REQUIRED_COLUMNS,
        )
        actual_shadow_sha256 = promotion.file_sha256(args.shadow_projection_cells_tsv)
        if args.shadow_projection_sha256.strip().lower() != actual_shadow_sha256:
            raise ValueError(
                "shadow projection SHA256 argument does not match "
                "shadow projection TSV content",
            )
        allowlist_rows = read_tsv_required(
            args.authority_allowlist_tsv,
            promotion.ALLOWLIST_REQUIRED_COLUMNS,
        )
        index = promotion.build_promotion_index(
            shadow_rows,
            allowlist_rows,
            actual_shadow_sha256,
            source_run_id=args.source_run_id,
            readiness_label=args.readiness_label,
        )
        outputs = promotion.write_promotion_outputs(args.output_dir, index)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"backfill PeakHypothesis promotion cells TSV: {outputs.cells_tsv}")
    print(
        "backfill PeakHypothesis area uncertainty TSV: "
        f"{outputs.area_uncertainty_tsv}",
    )
    print(f"backfill PeakHypothesis promotion summary JSON: {outputs.summary_json}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shadow-projection-cells-tsv", required=True, type=Path)
    parser.add_argument("--authority-allowlist-tsv", required=True, type=Path)
    parser.add_argument("--shadow-projection-sha256", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--source-run-id", default="")
    parser.add_argument(
        "--readiness-label",
        choices=("diagnostic_only", "shadow_ready"),
        default="diagnostic_only",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
