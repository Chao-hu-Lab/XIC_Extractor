"""Build a row-specific observed oracle for generated Backfill policy rows."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.diagnostics.standard_peak_policy_observed_oracle import (
    DEFAULT_POLICY_DECISION,
    run_policy_observed_oracle,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs = run_policy_observed_oracle(
            backfill_policy_tsv=args.backfill_policy_tsv,
            activation_scope_audit_tsv=args.activation_scope_audit_tsv,
            output_dir=args.output_dir,
            source_run_id=args.source_run_id,
            candidate_policy_decision=args.candidate_policy_decision,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Policy observed oracle summary JSON: {outputs.summary_json}")
    print(f"Policy observed oracle TSV: {outputs.results_tsv}")
    return 0 if outputs.status == "pass" else 1


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backfill-policy-tsv", type=Path, required=True)
    parser.add_argument("--activation-scope-audit-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-run-id", default="")
    parser.add_argument(
        "--candidate-policy-decision",
        default=DEFAULT_POLICY_DECISION,
        help="Generated policy decision to evaluate. Default: detected_flagged.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
