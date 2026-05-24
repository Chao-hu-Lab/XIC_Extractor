from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.diagnostics.cwt_peak_candidate_audit_analysis import (
    _agreement_class,
    _audit_group,
    _audit_groups,
    _chemically_plausible,
    _conditioned_class,
    _conditioned_class_count,
    _cwt_only_rows,
    _group_class_count,
    _nearest_cwt,
    _summary,
)
from tools.diagnostics.cwt_peak_candidate_audit_io import (
    _float_value,
    _read_peak_candidates,
    _read_target_mz,
    _required_indexes,
    _row_from_dict,
    _text,
)
from tools.diagnostics.cwt_peak_candidate_audit_models import (
    _CWT_ONLY_COLUMNS,
    _CWT_SOURCE,
    _DEFAULT_NEAR_RT_WINDOW_MIN,
    _GROUP_COLUMNS,
    _REQUIRED_COLUMNS,
    _SUMMARY_COLUMNS,
    CwtCandidateRow,
    CwtGroupAuditRow,
    CwtOnlyAuditRow,
)
from tools.diagnostics.cwt_peak_candidate_audit_writers import (
    _format_cwt_only_row,
    _format_group_row,
    _format_optional_float,
    _markdown,
    _write_cwt_only,
    _write_groups,
    _write_outputs,
    _write_summary,
)

__all__ = [
    "CwtCandidateRow",
    "CwtGroupAuditRow",
    "CwtOnlyAuditRow",
    "_CWT_ONLY_COLUMNS",
    "_CWT_SOURCE",
    "_DEFAULT_NEAR_RT_WINDOW_MIN",
    "_GROUP_COLUMNS",
    "_REQUIRED_COLUMNS",
    "_SUMMARY_COLUMNS",
    "_agreement_class",
    "_audit_group",
    "_audit_groups",
    "_chemically_plausible",
    "_conditioned_class",
    "_conditioned_class_count",
    "_cwt_only_rows",
    "_float_value",
    "_format_cwt_only_row",
    "_format_group_row",
    "_format_optional_float",
    "_group_class_count",
    "_markdown",
    "_nearest_cwt",
    "_parse_args",
    "_read_peak_candidates",
    "_read_target_mz",
    "_required_indexes",
    "_row_from_dict",
    "_summary",
    "_text",
    "_write_cwt_only",
    "_write_groups",
    "_write_outputs",
    "_write_summary",
    "main",
]


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        rows = _read_peak_candidates(args.peak_candidates_tsv)
        target_mz_by_label = (
            _read_target_mz(args.targeted_workbook)
            if args.targeted_workbook is not None
            else {}
        )
        groups = _audit_groups(
            rows,
            target_mz_by_label=target_mz_by_label,
            near_rt_window_min=args.near_rt_window_min,
        )
        cwt_only_rows = _cwt_only_rows(rows, target_mz_by_label=target_mz_by_label)
        payload = {
            "summary": _summary(rows, groups, cwt_only_rows),
            "groups": [asdict(row) for row in groups],
            "cwt_only_rows": [asdict(row) for row in cwt_only_rows],
        }
        _write_outputs(args.output_dir, payload, groups, cwt_only_rows)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"CWT audit JSON: {args.output_dir / 'cwt_peak_candidate_audit.json'}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit CWT peak candidate agreement from peak_candidates.tsv.",
    )
    parser.add_argument("--peak-candidates-tsv", type=Path, required=True)
    parser.add_argument(
        "--targeted-workbook",
        type=Path,
        help="Optional XIC workbook with Targets sheet used to enrich target_mz.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--near-rt-window-min",
        type=float,
        default=_DEFAULT_NEAR_RT_WINDOW_MIN,
        help=(
            "Classify selected candidates as selected_cwt_nearby when the "
            "nearest CWT proposal is within this RT window."
        ),
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
