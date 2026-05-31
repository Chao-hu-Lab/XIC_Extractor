"""Build typed sample-level PeakHypothesis assignments from evidence sidecars."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.alignment.shared_peak_identity_explanation import (
    mode_hypothesis_assignment,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        rows = mode_hypothesis_assignment.build_mode_hypothesis_assignment_rows(
            rt_mode_rows=mode_hypothesis_assignment.load_rt_mode_rows(
                args.rt_mode_evidence_tsv,
            ),
            candidate_ms2_pattern_rows=(
                mode_hypothesis_assignment.load_candidate_ms2_pattern_rows(
                    args.candidate_ms2_pattern_evidence_tsv,
                )
            ),
            ms1_pattern_coherence_rows=(
                mode_hypothesis_assignment.load_ms1_pattern_coherence_rows(
                    args.ms1_pattern_coherence_evidence_tsv,
                )
            ),
            qc_ms1_pattern_reference_rows=(
                mode_hypothesis_assignment.load_qc_ms1_pattern_reference_rows(
                    args.qc_ms1_pattern_reference_evidence_tsv,
                )
            ),
            matrix_rt_drift_policy_rows=(
                mode_hypothesis_assignment.load_matrix_rt_drift_policy_rows(
                    args.matrix_rt_drift_policy_tsv,
                )
            ),
        )
        mode_hypothesis_assignment.write_mode_hypothesis_assignment_rows(
            args.output_tsv,
            rows,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"peak_hypothesis_selection: {args.output_tsv}")
    print(f"assignment_rows: {len(rows)}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rt-mode-evidence-tsv", type=Path, required=True)
    parser.add_argument("--candidate-ms2-pattern-evidence-tsv", type=Path)
    parser.add_argument("--ms1-pattern-coherence-evidence-tsv", type=Path)
    parser.add_argument("--qc-ms1-pattern-reference-evidence-tsv", type=Path)
    parser.add_argument("--matrix-rt-drift-policy-tsv", type=Path)
    parser.add_argument("--output-tsv", type=Path, required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
