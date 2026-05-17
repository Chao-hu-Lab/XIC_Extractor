"""Strict targeted ISTD benchmark gate for untargeted alignment outputs."""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import median

from tools.diagnostics.targeted_istd_benchmark_loaders import (
    read_alignment_cells,
    read_alignment_matrix,
    read_alignment_review,
    read_target_definitions,
    read_targeted_points,
    read_targeted_reliability_points,
)
from tools.diagnostics.targeted_istd_benchmark_models import (
    ISOTOPE_SHIFT_DA,
    AlignmentCell,
    AlignmentFeature,
    BenchmarkOutputs,
    BenchmarkSummary,
    BenchmarkThresholds,
    CandidateMatch,
    TargetDefinition,
    TargetedPoint,
    TargetedReliabilityPoint,
)
from tools.diagnostics.targeted_istd_benchmark_writers import write_benchmark_outputs


def run_targeted_istd_benchmark(
    *,
    targeted_workbook: Path,
    alignment_dir: Path,
    output_dir: Path,
    thresholds: BenchmarkThresholds = BenchmarkThresholds(),
    targeted_reliability_json: Path | None = None,
    strict_targeted_reliability: bool = False,
) -> tuple[BenchmarkOutputs, tuple[BenchmarkSummary, ...]]:
    if strict_targeted_reliability and targeted_reliability_json is None:
        raise ValueError(
            "--strict-targeted-reliability requires --targeted-reliability-json"
        )
    targets = read_target_definitions(targeted_workbook)
    targeted_points = read_targeted_points(targeted_workbook)
    targeted_reliability = (
        read_targeted_reliability_points(targeted_reliability_json)
        if targeted_reliability_json is not None
        else {}
    )
    review_rows = read_alignment_review(alignment_dir / "alignment_review.tsv")
    matrix = read_alignment_matrix(alignment_dir / "alignment_matrix.tsv")
    cells = read_alignment_cells(alignment_dir / "alignment_cells.tsv")

    summaries: list[BenchmarkSummary] = []
    matches: list[CandidateMatch] = []
    for target in targets:
        target_points = tuple(
            point
            for point in targeted_points.get(target.label, ())
            if point.sample_stem in matrix.sample_stems
        )
        matching_points = _benchmark_points(
            target_points,
            reliability=targeted_reliability,
            strict_targeted_reliability=strict_targeted_reliability,
        )
        target_matches = _match_target_to_alignment(
            target,
            review_rows,
            target_points=matching_points,
            thresholds=thresholds,
        )
        matches.extend(target_matches)
        summaries.append(
            _summarize_target(
                target,
                target_points,
                target_matches,
                matrix=matrix.areas_by_family,
                cells=cells,
                thresholds=thresholds,
                reliability=targeted_reliability,
                strict_targeted_reliability=strict_targeted_reliability,
            ),
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = BenchmarkOutputs(
        summary_tsv=output_dir / "targeted_istd_benchmark_summary.tsv",
        matches_tsv=output_dir / "targeted_istd_benchmark_matches.tsv",
        json_path=output_dir / "targeted_istd_benchmark.json",
        markdown_path=output_dir / "targeted_istd_benchmark.md",
    )
    write_benchmark_outputs(
        outputs,
        summaries=summaries,
        matches=matches,
        thresholds=thresholds,
    )
    return outputs, tuple(summaries)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    thresholds = BenchmarkThresholds(
        active_neutral_loss_da=args.active_neutral_loss_da,
        additional_active_neutral_loss_das=tuple(
            args.additional_active_neutral_loss_da
        ),
        active_neutral_loss_tolerance_da=args.active_neutral_loss_tolerance_da,
        default_match_ppm=args.default_match_ppm,
        match_rt_sec=args.match_rt_sec,
        mean_rt_delta_max_min=args.mean_rt_delta_max_min,
        sample_rt_median_abs_delta_max_min=(
            args.sample_rt_median_abs_delta_max_min
        ),
        sample_rt_p95_abs_delta_max_min=args.sample_rt_p95_abs_delta_max_min,
        log_area_spearman_min=args.log_area_spearman_min,
        log_area_pearson_min=args.log_area_pearson_min,
    )
    try:
        outputs, summaries = run_targeted_istd_benchmark(
            targeted_workbook=args.targeted_workbook.resolve(),
            alignment_dir=args.alignment_dir.resolve(),
            output_dir=args.output_dir.resolve(),
            thresholds=thresholds,
            targeted_reliability_json=(
                args.targeted_reliability_json.resolve()
                if args.targeted_reliability_json is not None
                else None
            ),
            strict_targeted_reliability=args.strict_targeted_reliability,
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Summary TSV: {outputs.summary_tsv}")
    print(f"Matches TSV: {outputs.matches_tsv}")
    print(f"Benchmark JSON: {outputs.json_path}")
    print(f"Benchmark report: {outputs.markdown_path}")
    return 1 if any(row.status == "FAIL" for row in summaries) else 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run strict targeted ISTD benchmark for untargeted alignment.",
    )
    parser.add_argument("--targeted-workbook", type=Path, required=True)
    parser.add_argument("--alignment-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--active-neutral-loss-da", type=float, default=116.0474)
    parser.add_argument(
        "--additional-active-neutral-loss-da",
        action="append",
        default=[],
        type=float,
        help=(
            "Additional selected neutral-loss masses treated as active in a "
            "multi-tag benchmark."
        ),
    )
    parser.add_argument(
        "--active-neutral-loss-tolerance-da",
        type=float,
        default=0.01,
    )
    parser.add_argument("--default-match-ppm", type=float, default=20.0)
    parser.add_argument("--match-rt-sec", type=float, default=60.0)
    parser.add_argument("--mean-rt-delta-max-min", type=float, default=0.15)
    parser.add_argument(
        "--sample-rt-median-abs-delta-max-min",
        type=float,
        default=0.15,
    )
    parser.add_argument(
        "--sample-rt-p95-abs-delta-max-min",
        type=float,
        default=0.30,
    )
    parser.add_argument("--log-area-spearman-min", type=float, default=0.90)
    parser.add_argument("--log-area-pearson-min", type=float, default=0.80)
    parser.add_argument("--targeted-reliability-json", type=Path)
    parser.add_argument(
        "--strict-targeted-reliability",
        action="store_true",
        help=(
            "Use only benchmark_eligible targeted samples for coverage and "
            "RT/area calculations."
        ),
    )
    return parser.parse_args(argv)



def _match_target_to_alignment(
    target: TargetDefinition,
    features: tuple[AlignmentFeature, ...],
    *,
    target_points: tuple[TargetedPoint, ...],
    thresholds: BenchmarkThresholds,
) -> tuple[CandidateMatch, ...]:
    target_mean_rt = _mean(
        point.rt for point in target_points if point.positive
    )
    exact_matches = _match_target_to_alignment_with_shift(
        target,
        features,
        target_mean_rt=target_mean_rt,
        thresholds=thresholds,
        mass_shift_da=0.0,
    )
    if (
        any(match.include_in_primary_matrix for match in exact_matches)
        or not _is_active_tag(target, thresholds)
    ):
        return tuple(sorted(exact_matches, key=_match_sort_key))
    isotope_matches = tuple(
        match
        for mass_shift_da in (ISOTOPE_SHIFT_DA, -ISOTOPE_SHIFT_DA)
        for match in _match_target_to_alignment_with_shift(
            target,
            features,
            target_mean_rt=target_mean_rt,
            thresholds=thresholds,
            mass_shift_da=mass_shift_da,
        )
    )
    isotope_matches = _best_isotope_shift_matches(isotope_matches)
    return tuple(sorted((*exact_matches, *isotope_matches), key=_match_sort_key))


def _match_target_to_alignment_with_shift(
    target: TargetDefinition,
    features: tuple[AlignmentFeature, ...],
    *,
    target_mean_rt: float | None,
    thresholds: BenchmarkThresholds,
    mass_shift_da: float,
) -> tuple[CandidateMatch, ...]:
    shifted_mz = target.mz + mass_shift_da
    shifted_product_mz = target.product_mz + mass_shift_da
    match_type = "exact" if mass_shift_da == 0.0 else "isotope_shift"
    matches: list[CandidateMatch] = []
    for feature in features:
        mz_delta_ppm = _ppm_delta(shifted_mz, feature.family_center_mz)
        if abs(mz_delta_ppm) > target.ppm_tol:
            continue
        product_delta_ppm = _ppm_delta(
            shifted_product_mz,
            feature.family_product_mz,
        )
        if abs(product_delta_ppm) > target.ppm_tol:
            continue
        loss_delta_da = (
            feature.family_observed_neutral_loss_da - target.neutral_loss_da
        )
        if abs(loss_delta_da) > thresholds.active_neutral_loss_tolerance_da:
            continue
        rt_delta_sec = _target_rt_delta_sec(
            feature.family_center_rt,
            target,
            target_mean_rt,
        )
        if abs(rt_delta_sec) > thresholds.match_rt_sec:
            continue
        matches.append(
            CandidateMatch(
                target_label=target.label,
                feature_family_id=feature.feature_family_id,
                include_in_primary_matrix=feature.include_in_primary_matrix,
                family_center_mz=feature.family_center_mz,
                family_center_rt=feature.family_center_rt,
                family_product_mz=feature.family_product_mz,
                family_observed_neutral_loss_da=(
                    feature.family_observed_neutral_loss_da
                ),
                mz_delta_ppm=mz_delta_ppm,
                rt_delta_sec=rt_delta_sec,
                product_delta_ppm=product_delta_ppm,
                loss_delta_da=loss_delta_da,
                mass_shift_da=mass_shift_da,
                match_type=match_type,
                distance_score=max(
                    abs(mz_delta_ppm) / target.ppm_tol,
                    abs(product_delta_ppm) / target.ppm_tol,
                    abs(rt_delta_sec) / thresholds.match_rt_sec,
                ),
            )
        )
    return tuple(sorted(matches, key=_match_sort_key))


def _best_isotope_shift_matches(
    matches: tuple[CandidateMatch, ...],
) -> tuple[CandidateMatch, ...]:
    primary_matches = tuple(
        match for match in matches if match.include_in_primary_matrix
    )
    if not primary_matches:
        return matches
    best_shift = min(
        {match.mass_shift_da for match in primary_matches},
        key=lambda shift: (
            min(
                match.distance_score
                for match in primary_matches
                if match.mass_shift_da == shift
            ),
            abs(shift),
        ),
    )
    return tuple(match for match in matches if match.mass_shift_da == best_shift)


def _summarize_target(
    target: TargetDefinition,
    points: tuple[TargetedPoint, ...],
    matches: tuple[CandidateMatch, ...],
    *,
    matrix: Mapping[str, Mapping[str, float]],
    cells: Mapping[tuple[str, str], AlignmentCell],
    thresholds: BenchmarkThresholds,
    reliability: Mapping[tuple[str, str], TargetedReliabilityPoint],
    strict_targeted_reliability: bool,
) -> BenchmarkSummary:
    positives = tuple(point for point in points if point.positive)
    reliability_summary = _reliability_summary(
        points,
        reliability=reliability,
        strict_targeted_reliability=strict_targeted_reliability,
    )
    benchmark_points = (
        reliability_summary.clean_points
        if strict_targeted_reliability
        else positives
    )
    targeted_mean_rt = _mean(point.rt for point in benchmark_points)
    primary_matches = tuple(
        match for match in matches if match.include_in_primary_matrix
    )
    selected = primary_matches[0] if len(primary_matches) == 1 else None
    selected_family = selected.feature_family_id if selected else ""
    selected_matrix = matrix.get(selected_family, {})
    active_tag = _is_active_tag(target, thresholds)
    paired_logs: list[tuple[float, float]] = []
    rt_deltas: list[float] = []
    for point in benchmark_points:
        area = selected_matrix.get(point.sample_stem)
        if area is not None and area > 0 and point.area is not None:
            paired_logs.append((math.log10(point.area), math.log10(area)))
            cell = cells.get((selected_family, point.sample_stem))
            if cell is not None and cell.apex_rt is not None and point.rt is not None:
                rt_deltas.append(cell.apex_rt - point.rt)

    coverage_denominator_count = len(benchmark_points)
    coverage_minimum = max(
        0,
        coverage_denominator_count
        - max(1, math.ceil(coverage_denominator_count * 0.02)),
    )
    family_mean_rt_delta = (
        selected.family_center_rt - targeted_mean_rt
        if selected is not None and targeted_mean_rt is not None
        else None
    )
    pearson = _pearson(paired_logs)
    spearman = _spearman(paired_logs)
    median_rt_delta = _median_abs(rt_deltas)
    p95_rt_delta = _percentile_abs(rt_deltas, 0.95)
    warnings = _targeted_reliability_warnings(
        active_tag=active_tag,
        strict_targeted_reliability=strict_targeted_reliability,
        reliability_summary=reliability_summary,
    )
    if "TARGETED_RELIABILITY_INCONCLUSIVE" in warnings:
        failure_modes = ()
    else:
        failure_modes = _failure_modes(
            active_tag=active_tag,
            primary_matches=primary_matches,
            untargeted_positive_count=len(selected_matrix),
            coverage_minimum=coverage_minimum,
            family_mean_rt_delta=family_mean_rt_delta,
            sample_rt_median_abs_delta=median_rt_delta,
            sample_rt_p95_abs_delta=p95_rt_delta,
            paired_area_n=len(paired_logs),
            pearson=pearson,
            spearman=spearman,
            thresholds=thresholds,
        )
    status = "FAIL" if failure_modes else "WARN" if warnings else "PASS"
    return BenchmarkSummary(
        target_label=target.label,
        role=target.role,
        active_tag=active_tag,
        neutral_loss_da=target.neutral_loss_da,
        target_mz=target.mz,
        target_rt_min=target.rt_min,
        target_rt_max=target.rt_max,
        targeted_positive_count=len(positives),
        targeted_total_count=len(points),
        targeted_mean_rt=targeted_mean_rt,
        candidate_match_count=len(matches),
        primary_match_count=len(primary_matches),
        primary_feature_ids=tuple(match.feature_family_id for match in primary_matches),
        selected_feature_id=selected_family,
        untargeted_positive_count=len(selected_matrix),
        coverage_minimum=coverage_minimum,
        paired_area_n=len(paired_logs),
        log_area_pearson=pearson,
        log_area_spearman=spearman,
        family_mean_rt_delta_min=family_mean_rt_delta,
        sample_rt_pair_n=len(rt_deltas),
        sample_rt_median_abs_delta_min=median_rt_delta,
        sample_rt_p95_abs_delta_min=p95_rt_delta,
        status=status,
        failure_modes=failure_modes,
        note=_note(active_tag, failure_modes, warnings),
        targeted_reliability_mode=(
            "strict"
            if strict_targeted_reliability
            else "annotate"
            if reliability
            else "not_provided"
        ),
        clean_targeted_positive_count=len(reliability_summary.clean_points),
        targeted_review_positive_count=(
            reliability_summary.review_positive_count
        ),
        targeted_review_count=reliability_summary.review_count,
        targeted_negative_count=reliability_summary.negative_count,
        coverage_denominator_count=coverage_denominator_count,
        targeted_reliability_warning_modes=warnings,
    )


@dataclass(frozen=True)
class _ReliabilitySummary:
    clean_points: tuple[TargetedPoint, ...]
    review_positive_count: int
    review_count: int
    negative_count: int
    missing_count: int


def _benchmark_points(
    points: tuple[TargetedPoint, ...],
    *,
    reliability: Mapping[tuple[str, str], TargetedReliabilityPoint],
    strict_targeted_reliability: bool,
) -> tuple[TargetedPoint, ...]:
    if not strict_targeted_reliability:
        return points
    return _reliability_summary(
        points,
        reliability=reliability,
        strict_targeted_reliability=True,
    ).clean_points


def _reliability_summary(
    points: tuple[TargetedPoint, ...],
    *,
    reliability: Mapping[tuple[str, str], TargetedReliabilityPoint],
    strict_targeted_reliability: bool,
) -> _ReliabilitySummary:
    if not reliability:
        positives = tuple(point for point in points if point.positive)
        return _ReliabilitySummary(
            clean_points=positives,
            review_positive_count=0,
            review_count=0,
            negative_count=0,
            missing_count=0,
        )

    clean: list[TargetedPoint] = []
    review_positive_count = 0
    review_count = 0
    negative_count = 0
    missing_count = 0
    for point in points:
        record = reliability.get((point.sample_stem, point.target_label))
        if record is None:
            if point.positive:
                if strict_targeted_reliability:
                    missing_count += 1
                else:
                    clean.append(point)
            continue
        if record.reliability_state == "benchmark_eligible":
            if point.positive:
                clean.append(point)
        elif record.reliability_state == "targeted_review_positive":
            if point.positive:
                review_positive_count += 1
                if not strict_targeted_reliability:
                    clean.append(point)
        elif record.reliability_state == "targeted_review":
            if point.positive:
                review_count += 1
                if not strict_targeted_reliability:
                    clean.append(point)
        elif record.reliability_state == "targeted_negative":
            negative_count += 1
    return _ReliabilitySummary(
        clean_points=tuple(clean),
        review_positive_count=review_positive_count,
        review_count=review_count,
        negative_count=negative_count,
        missing_count=missing_count,
    )


def _targeted_reliability_warnings(
    *,
    active_tag: bool,
    strict_targeted_reliability: bool,
    reliability_summary: _ReliabilitySummary,
) -> tuple[str, ...]:
    warnings: list[str] = []
    if reliability_summary.review_positive_count:
        warnings.append("TARGETED_REVIEW_POSITIVE_EVIDENCE")
    if reliability_summary.review_count:
        warnings.append("TARGETED_REVIEW_EVIDENCE")
    if reliability_summary.missing_count:
        warnings.append("TARGETED_RELIABILITY_MISSING")
    if (
        active_tag
        and strict_targeted_reliability
        and len(reliability_summary.clean_points) < 3
    ):
        warnings.append("TARGETED_RELIABILITY_INCONCLUSIVE")
    return tuple(warnings)


def _failure_modes(
    *,
    active_tag: bool,
    primary_matches: tuple[CandidateMatch, ...],
    untargeted_positive_count: int,
    coverage_minimum: int,
    family_mean_rt_delta: float | None,
    sample_rt_median_abs_delta: float | None,
    sample_rt_p95_abs_delta: float | None,
    paired_area_n: int,
    pearson: float | None,
    spearman: float | None,
    thresholds: BenchmarkThresholds,
) -> tuple[str, ...]:
    if not active_tag:
        return ("FALSE_POSITIVE_TAG",) if primary_matches else ()
    failures: list[str] = []
    if len(primary_matches) == 0:
        failures.append("MISS")
    elif len(primary_matches) > 1:
        failures.append("SPLIT")
    if len(primary_matches) != 1:
        return tuple(failures)
    if untargeted_positive_count < coverage_minimum:
        failures.append("COVERAGE")
    if family_mean_rt_delta is None or abs(family_mean_rt_delta) > (
        thresholds.mean_rt_delta_max_min
    ):
        failures.append("DRIFT")
    if sample_rt_median_abs_delta is None or sample_rt_median_abs_delta > (
        thresholds.sample_rt_median_abs_delta_max_min
    ):
        failures.append("DRIFT")
    if sample_rt_p95_abs_delta is None or sample_rt_p95_abs_delta > (
        thresholds.sample_rt_p95_abs_delta_max_min
    ):
        failures.append("DRIFT")
    if paired_area_n < 3:
        failures.append("AREA_INSUFFICIENT")
    elif (
        pearson is None
        or pearson < thresholds.log_area_pearson_min
        or spearman is None
        or spearman < thresholds.log_area_spearman_min
    ):
        failures.append("AREA_MISMATCH")
    return tuple(dict.fromkeys(failures))


def _target_rt_delta_sec(
    rt: float,
    target: TargetDefinition,
    targeted_mean_rt: float | None,
) -> float:
    if target.rt_min <= rt <= target.rt_max:
        return 0.0
    if targeted_mean_rt is not None:
        return (rt - targeted_mean_rt) * 60.0
    if rt < target.rt_min:
        return (rt - target.rt_min) * 60.0
    return (rt - target.rt_max) * 60.0




def _ppm_delta(reference: float, observed: float) -> float:
    denominator = max(abs(reference), 1e-12)
    return (observed - reference) / denominator * 1_000_000.0


def _match_sort_key(match: CandidateMatch) -> tuple[object, ...]:
    return (
        0 if match.include_in_primary_matrix else 1,
        match.distance_score,
        abs(match.rt_delta_sec),
        abs(match.mz_delta_ppm),
        match.feature_family_id,
    )


def _mean(values: Sequence[float | None] | object) -> float | None:
    finite = [
        float(value)
        for value in values
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    ]
    if not finite:
        return None
    return sum(finite) / len(finite)


def _median_abs(values: Sequence[float]) -> float | None:
    finite = [abs(value) for value in values if math.isfinite(value)]
    if not finite:
        return None
    return float(median(finite))


def _percentile_abs(values: Sequence[float], quantile: float) -> float | None:
    finite = sorted(abs(value) for value in values if math.isfinite(value))
    if not finite:
        return None
    index = math.ceil(len(finite) * quantile) - 1
    return float(finite[min(max(index, 0), len(finite) - 1)])


def _pearson(pairs: Sequence[tuple[float, float]]) -> float | None:
    if len(pairs) < 3:
        return None
    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in pairs)
    x_denominator = math.sqrt(sum((x - x_mean) ** 2 for x in xs))
    y_denominator = math.sqrt(sum((y - y_mean) ** 2 for y in ys))
    denominator = x_denominator * y_denominator
    if denominator == 0:
        return None
    return numerator / denominator


def _spearman(pairs: Sequence[tuple[float, float]]) -> float | None:
    if len(pairs) < 3:
        return None
    x_ranks = _ranks([pair[0] for pair in pairs])
    y_ranks = _ranks([pair[1] for pair in pairs])
    return _pearson(tuple(zip(x_ranks, y_ranks, strict=True)))


def _ranks(values: Sequence[float]) -> list[float]:
    ranked = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(ranked):
        end = index + 1
        while end < len(ranked) and ranked[end][1] == ranked[index][1]:
            end += 1
        rank = (index + 1 + end) / 2.0
        for original_index, _value in ranked[index:end]:
            ranks[original_index] = rank
        index = end
    return ranks


def _is_active_tag(
    target: TargetDefinition,
    thresholds: BenchmarkThresholds,
) -> bool:
    active_masses = (
        thresholds.active_neutral_loss_da,
        *thresholds.additional_active_neutral_loss_das,
    )
    return any(
        abs(target.neutral_loss_da - active_mass)
        <= thresholds.active_neutral_loss_tolerance_da
        for active_mass in active_masses
    )


def _note(
    active_tag: bool,
    failure_modes: tuple[str, ...],
    warning_modes: tuple[str, ...],
) -> str:
    if not active_tag and not failure_modes:
        return "inactive tag excluded"
    if warning_modes and not failure_modes:
        return "strict gate warning"
    if not failure_modes:
        return "strict gate passed"
    return "strict gate failed"



if __name__ == "__main__":
    raise SystemExit(main())
