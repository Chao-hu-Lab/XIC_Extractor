"""Diagnose wrong-peak activation blocks without mutating product outputs."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.diagnostics.diagnostic_io import read_tsv_required, write_tsv
from xic_extractor.alignment.shared_peak_identity_explanation import (
    wrong_peak_root_cause,
)
from xic_extractor.alignment.shared_peak_identity_explanation.schema import (
    WRONG_PEAK_ROOT_CAUSE_COLUMNS,
)

_ACTIVATION_REQUIRED_COLUMNS = (
    "feature_family_id",
    "sample_id",
    "activation_status",
    "product_effect",
    "contract_rule_id",
)
_MACHINE_SUPPORT_REQUIRED_COLUMNS = (
    "feature_family_id",
    "sample_id",
    "observed_machine_metrics",
)
_ALIGNMENT_CELL_REQUIRED_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "status",
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs = run_diagnostic(
            activation_decisions_tsv=args.activation_decisions_tsv,
            machine_evidence_support_tsv=args.machine_evidence_support_tsv,
            alignment_cells_tsv=args.alignment_cells_tsv,
            output_dir=args.output_dir,
            trace_data_json=args.trace_data_json,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for label, path in outputs.items():
        print(f"{label}: {path}")
    return 0


def run_diagnostic(
    *,
    activation_decisions_tsv: Path,
    machine_evidence_support_tsv: Path,
    alignment_cells_tsv: Path,
    output_dir: Path,
    trace_data_json: Sequence[Path] = (),
) -> Mapping[str, Path]:
    decision_rows = read_tsv_required(
        activation_decisions_tsv,
        _ACTIVATION_REQUIRED_COLUMNS,
    )
    support_rows = read_tsv_required(
        machine_evidence_support_tsv,
        _MACHINE_SUPPORT_REQUIRED_COLUMNS,
    )
    cell_rows = read_tsv_required(
        alignment_cells_tsv,
        _ALIGNMENT_CELL_REQUIRED_COLUMNS,
    )
    trace_index = wrong_peak_root_cause.load_overlay_trace_data(trace_data_json)
    rows = wrong_peak_root_cause.build_wrong_peak_root_cause_rows(
        activation_decision_rows=decision_rows,
        machine_evidence_support_rows=support_rows,
        alignment_cell_rows=cell_rows,
        overlay_traces=trace_index,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "shared_peak_identity_wrong_peak_root_cause.tsv"
    write_tsv(path, rows, WRONG_PEAK_ROOT_CAUSE_COLUMNS, lineterminator="\n")
    return {"wrong_peak_root_cause": path}


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--activation-decisions-tsv",
        type=Path,
        required=True,
        help="shared_peak_identity_activation_decisions.tsv",
    )
    parser.add_argument(
        "--machine-evidence-support-tsv",
        type=Path,
        required=True,
        help="shared_peak_identity_machine_evidence_support.tsv",
    )
    parser.add_argument(
        "--alignment-cells-tsv",
        type=Path,
        required=True,
        help="alignment_cells.tsv used by the activation run",
    )
    parser.add_argument(
        "--trace-data-json",
        type=Path,
        action="append",
        default=[],
        help="family_ms1_overlay_* trace-data JSON; repeatable",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for wrong-peak root-cause sidecar outputs",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
