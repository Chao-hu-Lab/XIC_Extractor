"""Classify targeted/untargeted area mismatch by integration uncertainty."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.diagnostics.area_integration_uncertainty_analysis import (
    _abs_gt,
    _boundary_sensitive,
    _build_row,
    _classify,
    _format_counter,
    _gt,
    _has_high_uncertainty,
    _label_mismatch,
    _lt,
    _nonempty_diff,
    _ratio_in_window,
    _summarize,
)
from tools.diagnostics.area_integration_uncertainty_io import (
    _bool_value,
    _optional_float,
    _ratio,
    _read_alignment_integration_audits,
    _read_boundary_alternatives,
    _read_evidence_rows,
    _read_required_tsv,
    _read_targeted_audits,
)
from tools.diagnostics.area_integration_uncertainty_models import (
    BOUNDARY_DELTA_CONCERN_MIN,
    HIGH_UNCERTAINTY_FRACTION,
    LOW_BASELINE_FRACTION,
    RAW_AREA_RATIO_MAX,
    RAW_AREA_RATIO_MIN,
    ROW_FIELDS,
    SUMMARY_FIELDS,
    AlignmentIntegrationAudit,
    AreaIntegrationRow,
    AreaIntegrationSummary,
    AreaIntegrationUncertaintyOutputs,
    AreaIntegrationUncertaintyResult,
    EvidenceRow,
    TargetedAudit,
)
from tools.diagnostics.area_integration_uncertainty_writers import (
    _fmt,
    _format_value,
    _write_markdown,
    _write_outputs,
    _write_tsv,
)

__all__ = [
    "BOUNDARY_DELTA_CONCERN_MIN",
    "HIGH_UNCERTAINTY_FRACTION",
    "LOW_BASELINE_FRACTION",
    "RAW_AREA_RATIO_MAX",
    "RAW_AREA_RATIO_MIN",
    "ROW_FIELDS",
    "SUMMARY_FIELDS",
    "AlignmentIntegrationAudit",
    "AreaIntegrationRow",
    "AreaIntegrationSummary",
    "AreaIntegrationUncertaintyOutputs",
    "AreaIntegrationUncertaintyResult",
    "EvidenceRow",
    "TargetedAudit",
    "_abs_gt",
    "_bool_value",
    "_boundary_sensitive",
    "_build_row",
    "_classify",
    "_fmt",
    "_format_counter",
    "_format_value",
    "_gt",
    "_has_high_uncertainty",
    "_label_mismatch",
    "_lt",
    "_nonempty_diff",
    "_optional_float",
    "_parse_args",
    "_ratio",
    "_ratio_in_window",
    "_read_alignment_integration_audits",
    "_read_boundary_alternatives",
    "_read_evidence_rows",
    "_read_required_tsv",
    "_read_targeted_audits",
    "_summarize",
    "_write_markdown",
    "_write_outputs",
    "_write_tsv",
    "main",
    "run_area_integration_uncertainty_audit",
]


def run_area_integration_uncertainty_audit(
    *,
    evidence_spine_rows_tsv: Path,
    targeted_peak_candidates_tsv: Path,
    targeted_boundaries_tsv: Path,
    alignment_integration_audit_tsv: Path,
    output_dir: Path,
) -> tuple[AreaIntegrationUncertaintyOutputs, AreaIntegrationUncertaintyResult]:
    evidence_rows = _read_evidence_rows(evidence_spine_rows_tsv)
    targeted_audits = _read_targeted_audits(targeted_peak_candidates_tsv)
    boundary_alternatives = _read_boundary_alternatives(targeted_boundaries_tsv)
    alignment_audits = _read_alignment_integration_audits(
        alignment_integration_audit_tsv
    )
    rows = tuple(
        _build_row(
            evidence,
            targeted_audits=targeted_audits,
            boundary_alternatives=boundary_alternatives,
            alignment_audits=alignment_audits,
        )
        for evidence in evidence_rows
    )
    result = AreaIntegrationUncertaintyResult(
        summary=_summarize(rows),
        rows=rows,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = AreaIntegrationUncertaintyOutputs(
        summary_tsv=output_dir / "area_integration_uncertainty_summary.tsv",
        rows_tsv=output_dir / "area_integration_uncertainty_rows.tsv",
        json_path=output_dir / "area_integration_uncertainty.json",
        markdown_path=output_dir / "area_integration_uncertainty.md",
    )
    _write_outputs(outputs, result)
    return outputs, result


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify targeted/untargeted area mismatch by integration audit.",
    )
    parser.add_argument("--evidence-spine-rows-tsv", type=Path, required=True)
    parser.add_argument("--targeted-peak-candidates-tsv", type=Path, required=True)
    parser.add_argument("--targeted-boundaries-tsv", type=Path, required=True)
    parser.add_argument("--alignment-integration-audit-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs, _result = run_area_integration_uncertainty_audit(
            evidence_spine_rows_tsv=args.evidence_spine_rows_tsv,
            targeted_peak_candidates_tsv=args.targeted_peak_candidates_tsv,
            targeted_boundaries_tsv=args.targeted_boundaries_tsv,
            alignment_integration_audit_tsv=args.alignment_integration_audit_tsv,
            output_dir=args.output_dir,
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Summary TSV: {outputs.summary_tsv}")
    print(f"Rows TSV: {outputs.rows_tsv}")
    print(f"Uncertainty JSON: {outputs.json_path}")
    print(f"Uncertainty report: {outputs.markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
