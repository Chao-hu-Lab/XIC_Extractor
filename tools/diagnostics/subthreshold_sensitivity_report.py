"""Aggregate Gaussian15 sub-threshold (missed-peak) candidates across a batch.

Diagnostic-only EVIDENCE for deciding whether (and how far) to relax the
within-trace multi-peak detection thresholds in
``ms1_peak_modes.gaussian15_peak_observations``. It reuses
``subthreshold_candidate_report`` (which faithfully mirrors the detector's
local-maximum scan) and reports, across a whole batch of overlay trace-data
JSONs:

* how many local maxima the detector accepted vs rejected,
* which gate (height / prominence / edge / overlapping) blocked the rejected
  ones — both "appears in the reasons" and "is the SOLE blocker", and
* a height-recovery curve: how many additional peaks a relaxed height-fraction
  threshold would clear (an UPPER BOUND — it counts local maxima blocked solely
  by the 20% height gate, before any new non-overlapping suppression).

It changes NO detection logic; it only reads trace data and reports. Use it on a
real (ideally spike-in) batch to see which gate dominates, then make an
evidence-backed threshold change and validate it with spike-in recovery.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.diagnostics.changed_row_mode_overlay_review import (
    SubThresholdCandidate,
    subthreshold_candidate_report,
)
from xic_extractor.diagnostics.diagnostic_io import text_value, write_tsv

HEIGHT_RECOVERY_THRESHOLDS = (0.15, 0.12, 0.10, 0.08, 0.05)

GATE_BREAKDOWN_COLUMNS = (
    "gate",
    "candidates_with_gate",
    "candidates_sole_gate",
)
HEIGHT_RECOVERY_COLUMNS = (
    "height_fraction_threshold",
    "peaks_recovered_upper_bound",
    "traces_with_recovery",
)


@dataclass(frozen=True)
class SensitivitySummary:
    traces_scanned: int
    total_local_maxima: int
    accepted: int
    rejected: int
    gate_rows: tuple[dict[str, str], ...]
    recovery_rows: tuple[dict[str, str], ...]


def _reason_gate(reason: str) -> str:
    if reason.startswith("height"):
        return "height"
    if reason.startswith("prominence"):
        return "prominence"
    if reason.startswith("edge"):
        return "edge"
    if reason.startswith("suppressed"):
        return "overlapping"
    return "other"


def summarize_subthreshold_sensitivity(
    candidates_by_trace: Iterable[tuple[str, Sequence[SubThresholdCandidate]]],
) -> SensitivitySummary:
    """Aggregate per-trace sub-threshold reports into batch-level evidence.

    Pure: takes (trace_key, candidates) pairs and returns counts. Never touches
    detection or files.
    """
    traces_scanned = 0
    total = 0
    accepted = 0
    with_gate: Counter[str] = Counter()
    sole_gate: Counter[str] = Counter()
    recovered: Counter[float] = Counter()
    recovery_traces: dict[float, set[str]] = {
        threshold: set() for threshold in HEIGHT_RECOVERY_THRESHOLDS
    }
    for trace_key, candidates in candidates_by_trace:
        traces_scanned += 1
        for candidate in candidates:
            total += 1
            if candidate.accepted:
                accepted += 1
                continue
            gates = {_reason_gate(reason) for reason in candidate.reject_reasons}
            for gate in gates:
                with_gate[gate] += 1
            if len(candidate.reject_reasons) == 1:
                sole = _reason_gate(candidate.reject_reasons[0])
                sole_gate[sole] += 1
                if sole == "height":
                    for threshold in HEIGHT_RECOVERY_THRESHOLDS:
                        if candidate.height_fraction >= threshold:
                            recovered[threshold] += 1
                            recovery_traces[threshold].add(trace_key)
    gate_rows = tuple(
        {
            "gate": gate,
            "candidates_with_gate": str(with_gate.get(gate, 0)),
            "candidates_sole_gate": str(sole_gate.get(gate, 0)),
        }
        for gate in ("height", "prominence", "edge", "overlapping", "other")
    )
    recovery_rows = tuple(
        {
            "height_fraction_threshold": f"{threshold:.2f}",
            "peaks_recovered_upper_bound": str(recovered.get(threshold, 0)),
            "traces_with_recovery": str(len(recovery_traces[threshold])),
        }
        for threshold in HEIGHT_RECOVERY_THRESHOLDS
    )
    return SensitivitySummary(
        traces_scanned=traces_scanned,
        total_local_maxima=total,
        accepted=accepted,
        rejected=total - accepted,
        gate_rows=gate_rows,
        recovery_rows=recovery_rows,
    )


def iter_trace_candidates(
    trace_data_jsons: Sequence[Path],
) -> Iterator[tuple[str, tuple[SubThresholdCandidate, ...]]]:
    for path in trace_data_jsons:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, Mapping):
            continue
        family_id = text_value(payload.get("family_id")) or path.stem
        traces = payload.get("traces")
        if not isinstance(traces, list):
            continue
        for trace in traces:
            if not isinstance(trace, Mapping):
                continue
            sample_stem = text_value(trace.get("sample_stem")) or "?"
            yield (f"{family_id}:{sample_stem}", subthreshold_candidate_report(trace))


def run_subthreshold_sensitivity_report(
    *,
    trace_data_jsons: Sequence[Path],
    output_dir: Path,
) -> tuple[Path, Path, SensitivitySummary]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize_subthreshold_sensitivity(
        iter_trace_candidates(trace_data_jsons),
    )
    gate_tsv = output_dir / "subthreshold_gate_breakdown.tsv"
    recovery_tsv = output_dir / "subthreshold_height_recovery.tsv"
    write_tsv(gate_tsv, summary.gate_rows, GATE_BREAKDOWN_COLUMNS, lineterminator="\n")
    write_tsv(
        recovery_tsv,
        summary.recovery_rows,
        HEIGHT_RECOVERY_COLUMNS,
        lineterminator="\n",
    )
    return gate_tsv, recovery_tsv, summary


def _resolve_trace_jsons(args: argparse.Namespace) -> list[Path]:
    paths: list[Path] = []
    if args.input_dir is not None:
        paths.extend(sorted(args.input_dir.rglob("*_trace_data.json")))
    if args.trace_data_json:
        paths.extend(args.trace_data_json)
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    trace_jsons = _resolve_trace_jsons(args)
    if not trace_jsons:
        print(
            "no *_trace_data.json found; pass --input-dir or --trace-data-json",
            file=sys.stderr,
        )
        return 2
    gate_tsv, recovery_tsv, summary = run_subthreshold_sensitivity_report(
        trace_data_jsons=trace_jsons,
        output_dir=args.output_dir,
    )
    print(
        f"scanned {summary.traces_scanned} traces; "
        f"{summary.total_local_maxima} local maxima "
        f"({summary.accepted} accepted, {summary.rejected} rejected)",
    )
    print(f"gate breakdown: {gate_tsv}")
    print(f"height recovery (upper bound): {recovery_tsv}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        help="Directory searched recursively for *_trace_data.json overlay files.",
    )
    parser.add_argument(
        "--trace-data-json",
        type=Path,
        action="append",
        help="Explicit overlay trace-data JSON (repeatable).",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
