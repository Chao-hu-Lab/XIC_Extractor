"""Evaluate Mode-Window Assignment Contract Gate v0 sentinel expectations."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.alignment.shared_peak_identity_explanation import (
    mode_window_assignment_gate,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs, summary = run_gate(
            contract_fixture_tsv=args.contract_fixture_tsv,
            peak_hypothesis_selection_tsv=args.peak_hypothesis_selection_tsv,
            output_dir=args.output_dir,
            activation_decisions_tsv=args.activation_decisions_tsv,
            peak_hypothesis_matrix_summary_tsv=(
                args.peak_hypothesis_matrix_summary_tsv
            ),
            qc_ms1_pattern_reference_tsv=args.qc_ms1_pattern_reference_tsv,
            matrix_rt_drift_policy_tsv=args.matrix_rt_drift_policy_tsv,
            ms1_pattern_coherence_tsv=args.ms1_pattern_coherence_tsv,
            candidate_ms2_pattern_evidence_tsv=(
                args.candidate_ms2_pattern_evidence_tsv
            ),
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for label, path in outputs.items():
        print(f"{label}: {path}")
    print(
        "mode_window_assignment_gate_status: "
        f"{summary['mode_window_assignment_gate_status']}"
    )
    if (
        args.fail_on_gate_failure
        and summary["mode_window_assignment_gate_status"] != "pass"
    ):
        return 1
    return 0


def run_gate(
    *,
    contract_fixture_tsv: Path,
    peak_hypothesis_selection_tsv: Path,
    output_dir: Path,
    activation_decisions_tsv: Path | None = None,
    peak_hypothesis_matrix_summary_tsv: Path | None = None,
    qc_ms1_pattern_reference_tsv: Path | None = None,
    matrix_rt_drift_policy_tsv: Path | None = None,
    ms1_pattern_coherence_tsv: Path | None = None,
    candidate_ms2_pattern_evidence_tsv: Path | None = None,
) -> tuple[Mapping[str, Path], Mapping[str, str]]:
    rows = mode_window_assignment_gate.build_gate_rows(
        fixture_rows=mode_window_assignment_gate.load_contract_fixture(
            contract_fixture_tsv,
        ),
        selection_rows=mode_window_assignment_gate.load_peak_hypothesis_selection(
            peak_hypothesis_selection_tsv,
        ),
        activation_rows=mode_window_assignment_gate.load_activation_decisions(
            activation_decisions_tsv,
        ),
        matrix_summary=mode_window_assignment_gate.load_matrix_summary(
            peak_hypothesis_matrix_summary_tsv,
        ),
        qc_reference_rows=mode_window_assignment_gate.load_qc_reference_rows(
            qc_ms1_pattern_reference_tsv,
        ),
        rt_drift_rows=mode_window_assignment_gate.load_rt_drift_rows(
            matrix_rt_drift_policy_tsv,
        ),
        ms1_pattern_rows=mode_window_assignment_gate.load_ms1_pattern_rows(
            ms1_pattern_coherence_tsv,
        ),
        candidate_ms2_pattern_rows=(
            mode_window_assignment_gate.load_candidate_ms2_pattern_rows(
                candidate_ms2_pattern_evidence_tsv,
            )
        ),
    )
    summary = mode_window_assignment_gate.build_gate_summary(rows)
    rows_path, summary_path = mode_window_assignment_gate.write_gate_outputs(
        output_dir=output_dir,
        rows=rows,
        summary=summary,
    )
    return (
        {
            "mode_window_assignment_gate": rows_path,
            "mode_window_assignment_summary": summary_path,
        },
        summary,
    )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract-fixture-tsv", type=Path, required=True)
    parser.add_argument("--peak-hypothesis-selection-tsv", type=Path, required=True)
    parser.add_argument("--activation-decisions-tsv", type=Path)
    parser.add_argument("--peak-hypothesis-matrix-summary-tsv", type=Path)
    parser.add_argument("--qc-ms1-pattern-reference-tsv", type=Path)
    parser.add_argument("--matrix-rt-drift-policy-tsv", type=Path)
    parser.add_argument("--ms1-pattern-coherence-tsv", type=Path)
    parser.add_argument("--candidate-ms2-pattern-evidence-tsv", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--fail-on-gate-failure",
        action="store_true",
        help=(
            "Return exit code 1 when the evaluated sentinel gate status is not "
            "pass. Without this flag the command still writes diagnostic "
            "artifacts and exits 0 when inputs are readable."
        ),
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
