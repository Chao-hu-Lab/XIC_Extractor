from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.diagnostics.peak_candidate_score_calibration_analysis import (
    _best_challenger,
    _group_risks,
    _has_new_support,
    _label_impact,
    _label_impact_row,
    _median_score,
    _plausible_nl_dropout,
    _recommendations,
    _risk_group_counts,
    _risk_row,
    _risk_rows,
    _same_or_near_apex,
    _score_greater,
    _score_sort_value,
    _selected_nl_fail,
    _selected_no_ms2,
    _selected_review_only,
    _summary,
)
from tools.diagnostics.peak_candidate_score_calibration_io import (
    _bool_value,
    _optional_float,
    _read_peak_candidates,
    _row_from_dict,
)
from tools.diagnostics.peak_candidate_score_calibration_models import (
    _APEX_SHADOW_RT_WINDOW_MIN,
    _LABEL_COLUMNS,
    _REQUIRED_COLUMNS,
    _RISK_COLUMNS,
    _SUMMARY_COLUMNS,
    PeakCandidateScoreRow,
    ScoreLabelImpactRow,
    ScoreRiskRow,
    _split_labels,
)
from tools.diagnostics.peak_candidate_score_calibration_writers import (
    _format_label_impact_row,
    _format_optional_float,
    _format_risk_row,
    _markdown,
    _write_label_impact,
    _write_outputs,
    _write_risk_rows,
    _write_summary,
)

__all__ = [
    "PeakCandidateScoreRow",
    "ScoreLabelImpactRow",
    "ScoreRiskRow",
    "_APEX_SHADOW_RT_WINDOW_MIN",
    "_LABEL_COLUMNS",
    "_REQUIRED_COLUMNS",
    "_RISK_COLUMNS",
    "_SUMMARY_COLUMNS",
    "_best_challenger",
    "_bool_value",
    "_format_label_impact_row",
    "_format_optional_float",
    "_format_risk_row",
    "_group_risks",
    "_has_new_support",
    "_label_impact",
    "_label_impact_row",
    "_markdown",
    "_median_score",
    "_optional_float",
    "_parse_args",
    "_plausible_nl_dropout",
    "_read_peak_candidates",
    "_recommendations",
    "_risk_group_counts",
    "_risk_row",
    "_risk_rows",
    "_row_from_dict",
    "_same_or_near_apex",
    "_score_greater",
    "_score_sort_value",
    "_selected_nl_fail",
    "_selected_no_ms2",
    "_selected_review_only",
    "_split_labels",
    "_summary",
    "_write_label_impact",
    "_write_outputs",
    "_write_risk_rows",
    "_write_summary",
    "main",
]


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        rows = _read_peak_candidates(args.peak_candidates_tsv)
        risk_rows = _risk_rows(rows)
        label_impact = _label_impact(rows)
        summary = _summary(rows, risk_rows)
        payload = {
            "summary": summary,
            "risk_rows": [asdict(row) for row in risk_rows],
            "label_impact": [asdict(row) for row in label_impact],
            "recommendations": _recommendations(summary, risk_rows),
        }
        _write_outputs(args.output_dir, payload, risk_rows, label_impact)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(
        "Peak candidate score calibration JSON: "
        f"{args.output_dir / 'peak_candidate_score_calibration.json'}"
    )
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit peak candidate scoring against newer evidence labels without "
            "changing production selection."
        )
    )
    parser.add_argument("--peak-candidates-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
