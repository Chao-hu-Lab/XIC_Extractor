"""Seed a family MS1 overlay evidence cache from existing overlay artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.diagnostics.family_ms1_overlay_batch import (  # noqa: E402
    seed_evidence_cache_from_overlay_summary,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    summary = seed_evidence_cache_from_overlay_summary(
        review_queue_tsv=args.review_queue_tsv,
        alignment_cells=args.alignment_cells,
        raw_dir=args.raw_dir,
        dll_dir=args.dll_dir,
        overlay_batch_summary_tsv=args.overlay_batch_summary_tsv,
        evidence_cache_dir=args.evidence_cache_dir,
        start_rank=args.start_rank,
        limit=args.limit,
        ppm=args.ppm,
        max_highlight_rescued=args.max_highlight_rescued,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Overlay evidence cache seed summary JSON: {args.output_json}")
    print(f"cache_store_count: {summary['cache_store_count']}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-queue-tsv", type=Path, required=True)
    parser.add_argument(
        "--alignment-cells",
        "--alignment-cell-evidence",
        dest="alignment_cells",
        type=Path,
        required=True,
    )
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--dll-dir", type=Path, required=True)
    parser.add_argument("--overlay-batch-summary-tsv", type=Path, required=True)
    parser.add_argument("--evidence-cache-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--start-rank", type=int, default=1)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--ppm", type=float, default=20.0)
    parser.add_argument("--max-highlight-rescued", type=int, default=8)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
