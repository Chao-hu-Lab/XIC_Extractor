"""CLI for the P2c AsLS truth-validation gate."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Sequence

from tools.diagnostics.asls_truth_validation_analysis import (
    decide_gate,
    exit_code_for_gate,
)
from tools.diagnostics.asls_truth_validation_inputs import (
    FAIL,
    NOT_APPLICABLE_WITH_EXCLUSION,
    NOT_PROVIDED,
    PASS,
    VALID,
    CoverageRow,
    TierAValidationResult,
    validate_retirement_prerequisites,
    validate_tier_a,
    validate_tier_c,
    validate_waiver,
)
from tools.diagnostics.asls_truth_validation_manifests import (
    FixtureLock,
    FixtureManifest,
    TierAManifest,
    load_fixture_lock,
    load_fixture_manifest,
    load_tier_a_manifest,
)
from tools.diagnostics.asls_truth_validation_models import (
    BENCHMARK_STATUS_FAIL,
    BENCHMARK_STATUS_INCONCLUSIVE,
    COVERAGE_FIELDS,
    GATE_RETIREMENT,
    INCONCLUSIVE_INVALID_INPUT,
    INCONCLUSIVE_FIXTURE_SCOPE_MISMATCH,
    LEGACY_FIXTURE_CURRENT,
    ROW_FIELDS,
    ROW_STATUS_HARD_BLOCKER,
    SUMMARY_FIELDS,
    TIER_B2_STATUS_NOT_RUN,
    TIER_B2_STRESS,
    TruthValidationOutputs,
    load_json_object,
)
from tools.diagnostics.asls_truth_validation_synthetic import (
    SyntheticComparisonRow,
    TierBBlockerSummary,
    classify_tier_b_blockers,
    compare_synthetic_trace,
    generate_synthetic_traces,
    validate_synthetic_fixture_lock,
)
from tools.diagnostics.diagnostic_io import write_tsv

SCHEMA_VERSION = "asls_truth_validation_v2"


@dataclass(frozen=True)
class SyntheticBenchmarkResult:
    synthetic_decision_status: str
    tier_b1_status: str
    tier_b1_accuracy_scope: str
    tier_b2_status: str
    fixture_scope_status: str
    legacy_fixture_status: str
    rows: tuple[SyntheticComparisonRow, ...]
    b1_hard_blockers: tuple[str, ...]
    b1_cautions: tuple[str, ...]
    b2_retirement_blockers: tuple[str, ...]
    heldout_row_count: int
    tier_b1_heldout_row_count: int
    b1_adjacent_stress_row_count: int
    tier_b2_heldout_row_count: int
    production_like_heldout_row_count: int
    stress_heldout_row_count: int
    blank_false_positive_rate: float | None
    blank_not_quantifiable_rate: float | None
    worst_heldout_median_relative_error_pct: float | None
    worst_heldout_p95_relative_error_pct: float | None


def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = _parse_args(raw_argv)
    args.command_line = ["tools.diagnostics.asls_truth_validation", *raw_argv]
    outputs = TruthValidationOutputs.from_output_dir(args.output_dir)
    try:
        result = _run(args, outputs)
    except (OSError, ValueError) as exc:
        _write_fallback_outputs(args, outputs, exc)
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Gate decision: {result['gate_decision']}")
    print(f"Summary TSV: {outputs.summary_tsv}")
    print(f"Report: {outputs.markdown_path}")
    return exit_code_for_gate(str(result["gate_decision"]))


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier-a-rows", type=Path, required=True)
    parser.add_argument("--tier-a-summary", type=Path, required=True)
    parser.add_argument("--tier-a-json", type=Path, required=True)
    parser.add_argument("--tier-a-report", type=Path, required=True)
    parser.add_argument("--tier-a-manifest", type=Path, required=True)
    parser.add_argument("--fixture-manifest", type=Path, required=True)
    parser.add_argument("--fixture-lock", type=Path, required=True)
    parser.add_argument("--p2b-85raw-acceptance-manifest", type=Path)
    parser.add_argument("--tier-c-evidence", type=Path)
    parser.add_argument("--methodology-waiver", type=Path)
    parser.add_argument("--retirement-prereq-manifest", type=Path)
    parser.add_argument(
        "--decision-target",
        choices=("c1b-plan", "linear-edge-retirement"),
        required=True,
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def _run(args: argparse.Namespace, outputs: TruthValidationOutputs) -> dict[str, object]:
    outputs.rows_tsv.parent.mkdir(parents=True, exist_ok=True)
    fixture_manifest = load_fixture_manifest(args.fixture_manifest)
    fixture_lock = load_fixture_lock(args.fixture_lock)
    tier_a = validate_tier_a(
        rows_path=args.tier_a_rows,
        summary_path=args.tier_a_summary,
        json_path=args.tier_a_json,
        report_path=args.tier_a_report,
        manifest_path=args.tier_a_manifest,
        fixture_manifest=fixture_manifest,
    )
    tier_a_manifest = _try_load_tier_a_manifest(args.tier_a_manifest)
    benchmark = _run_synthetic_benchmark(fixture_manifest, fixture_lock)
    tier_c = validate_tier_c(args.tier_c_evidence)
    waiver = validate_waiver(args.methodology_waiver)
    prereq = validate_retirement_prerequisites(args.retirement_prereq_manifest)
    optional_inputs = _optional_input_objects(args)
    coverage_status = (
        PASS
        if all(row.coverage_status == PASS for row in tier_a.coverage_rows)
        else "INCONCLUSIVE_FIXTURE_GAP"
    )
    gate = decide_gate(
        decision_target=args.decision_target,
        tier_a_status=tier_a.status,
        tier_b1_status=benchmark.tier_b1_status,
        tier_b2_status=benchmark.tier_b2_status,
        b1_hard_blockers=benchmark.b1_hard_blockers,
        b2_retirement_blockers=benchmark.b2_retirement_blockers,
        coverage_status=coverage_status,
        tier_c_status=tier_c.status,
        tier_c_nonblank_status=tier_c.nonblank_status,
        tier_c_nonblank_decision_scope=tier_c.nonblank_decision_scope,
        blank_safety_status=tier_c.blank_safety_status,
        waiver_state=waiver.waiver_state,
        retirement_prereq_status=prereq.status,
    )
    summary = _summary_row(
        args=args,
        tier_a=tier_a,
        tier_a_manifest=tier_a_manifest,
        fixture_manifest=fixture_manifest,
        fixture_lock=fixture_lock,
        benchmark=benchmark,
        coverage_status=coverage_status,
        tier_c_status=tier_c.status,
        tier_c_nonblank_status=tier_c.nonblank_status,
        blank_safety_status=tier_c.blank_safety_status,
        stress_axis_dispositions=tier_c.stress_axis_disposition_statuses,
        waiver_state=waiver.waiver_state,
        retirement_prereq_status=prereq.status,
        optional_inputs=optional_inputs,
        gate_decision=gate,
    )
    _write_outputs(
        args=args,
        outputs=outputs,
        summary=summary,
        fixture_manifest=fixture_manifest,
        fixture_lock=fixture_lock,
        tier_a_manifest=tier_a_manifest,
        optional_inputs=optional_inputs,
        benchmark=benchmark,
        coverage_rows=tier_a.coverage_rows,
    )
    _copy_artifacts(args, outputs)
    return summary


def _run_synthetic_benchmark(
    fixture_manifest: FixtureManifest,
    fixture_lock: FixtureLock,
) -> SyntheticBenchmarkResult:
    if fixture_manifest.legacy_fixture_status != LEGACY_FIXTURE_CURRENT:
        return _empty_benchmark(
            synthetic_status=BENCHMARK_STATUS_INCONCLUSIVE,
            tier_b1_status=INCONCLUSIVE_FIXTURE_SCOPE_MISMATCH,
            tier_b2_status=TIER_B2_STATUS_NOT_RUN,
            fixture_scope_status=fixture_manifest.fixture_scope_status,
            legacy_fixture_status=fixture_manifest.legacy_fixture_status,
        )
    status = validate_synthetic_fixture_lock(fixture_manifest, fixture_lock)
    if status != PASS:
        return _empty_benchmark(
            synthetic_status=BENCHMARK_STATUS_INCONCLUSIVE,
            tier_b1_status=status,
            tier_b2_status=TIER_B2_STATUS_NOT_RUN,
            fixture_scope_status=status,
            legacy_fixture_status=fixture_manifest.legacy_fixture_status,
        )
    traces = generate_synthetic_traces(fixture_manifest, fixture_lock)
    reference_area = median(trace.true_area for trace in traces if trace.true_area > 0)
    rows = tuple(
        compare_synthetic_trace(
            trace,
            asls_params={
                "lam": fixture_manifest.asls_lam,
                "p": fixture_manifest.asls_p,
                "n_iter": fixture_manifest.asls_n_iter,
            },
            reference_nonblank_median_true_area=reference_area,
        )
        for trace in traces
    )
    blocker_summary = classify_tier_b_blockers(rows)
    heldout = [row for row in rows if row.split == "heldout_gate"]
    blank_rows = [row for row in rows if row.fixture_class == "blank_noise_control"]
    b1_heldout = [
        row
        for row in heldout
        if row.tier_b_layer == "B1_RELEVANCE"
        and row.production_like_bounds_status == "IN_SCOPE"
    ]
    b1_adjacent = [
        row for row in heldout if row.tier_b_layer == "B1_ADJACENT_STRESS"
    ]
    b2_heldout = [row for row in heldout if row.tier_b_layer == TIER_B2_STRESS]
    return SyntheticBenchmarkResult(
        synthetic_decision_status=blocker_summary.tier_b1_status,
        tier_b1_status=blocker_summary.tier_b1_status,
        tier_b1_accuracy_scope=blocker_summary.tier_b1_accuracy_scope,
        tier_b2_status=blocker_summary.tier_b2_status,
        fixture_scope_status=fixture_manifest.fixture_scope_status,
        legacy_fixture_status=fixture_manifest.legacy_fixture_status,
        rows=rows,
        b1_hard_blockers=blocker_summary.b1_hard_blockers,
        b1_cautions=blocker_summary.b1_cautions,
        b2_retirement_blockers=blocker_summary.b2_retirement_blockers,
        heldout_row_count=len(heldout),
        tier_b1_heldout_row_count=len(b1_heldout),
        b1_adjacent_stress_row_count=len(b1_adjacent),
        tier_b2_heldout_row_count=len(b2_heldout),
        production_like_heldout_row_count=len(b1_heldout),
        stress_heldout_row_count=len(b1_adjacent) + len(b2_heldout),
        blank_false_positive_rate=_rate(row.blank_false_positive for row in blank_rows),
        blank_not_quantifiable_rate=_rate(row.blank_not_quantifiable for row in blank_rows),
        worst_heldout_median_relative_error_pct=_median_relative_error(heldout),
        worst_heldout_p95_relative_error_pct=_p95_relative_error(heldout),
    )


def _empty_benchmark(
    *,
    synthetic_status: str,
    tier_b1_status: str,
    tier_b2_status: str,
    fixture_scope_status: str,
    legacy_fixture_status: str,
) -> SyntheticBenchmarkResult:
    return SyntheticBenchmarkResult(
        synthetic_decision_status=synthetic_status,
        tier_b1_status=tier_b1_status,
        tier_b1_accuracy_scope="FAIL" if tier_b1_status == FAIL else "",
        tier_b2_status=tier_b2_status,
        fixture_scope_status=fixture_scope_status,
        legacy_fixture_status=legacy_fixture_status,
        rows=(),
        b1_hard_blockers=(),
        b1_cautions=(),
        b2_retirement_blockers=(),
        heldout_row_count=0,
        tier_b1_heldout_row_count=0,
        b1_adjacent_stress_row_count=0,
        tier_b2_heldout_row_count=0,
        production_like_heldout_row_count=0,
        stress_heldout_row_count=0,
        blank_false_positive_rate=None,
        blank_not_quantifiable_rate=None,
        worst_heldout_median_relative_error_pct=None,
        worst_heldout_p95_relative_error_pct=None,
    )


def _write_outputs(
    *,
    args: argparse.Namespace,
    outputs: TruthValidationOutputs,
    summary: dict[str, object],
    fixture_manifest: FixtureManifest,
    fixture_lock: FixtureLock,
    tier_a_manifest: TierAManifest | None,
    optional_inputs: dict[str, dict[str, Any]],
    benchmark: SyntheticBenchmarkResult,
    coverage_rows: tuple[CoverageRow, ...],
) -> None:
    write_tsv(outputs.rows_tsv, [_row_dict(row) for row in benchmark.rows], ROW_FIELDS)
    write_tsv(outputs.summary_tsv, [summary], SUMMARY_FIELDS)
    write_tsv(
        outputs.coverage_tsv,
        [_coverage_dict(row) for row in coverage_rows],
        COVERAGE_FIELDS,
    )
    payload = _json_payload(
        args=args,
        summary=summary,
        fixture_manifest=fixture_manifest,
        fixture_lock=fixture_lock,
        tier_a_manifest=tier_a_manifest,
        optional_inputs=optional_inputs,
        benchmark=benchmark,
        coverage_rows=coverage_rows,
    )
    outputs.json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(outputs.markdown_path, summary)


def _summary_row(
    *,
    args: argparse.Namespace,
    tier_a: TierAValidationResult,
    tier_a_manifest: TierAManifest,
    fixture_manifest: FixtureManifest,
    fixture_lock: FixtureLock,
    benchmark: SyntheticBenchmarkResult,
    coverage_status: str,
    tier_c_status: str,
    tier_c_nonblank_status: str,
    blank_safety_status: str,
    stress_axis_dispositions: tuple[str, ...],
    waiver_state: str,
    retirement_prereq_status: str,
    optional_inputs: dict[str, dict[str, Any]],
    gate_decision: str,
) -> dict[str, object]:
    tier_c_object = optional_inputs["tier_c_evidence"]["object"]
    waiver_object = optional_inputs["methodology_waiver"]["object"]
    prereq_object = optional_inputs["retirement_prerequisites"]["object"]
    return {
        "readiness_status": "diagnostic_only",
        "benchmark_status": _benchmark_status_for_target(
            args.decision_target,
            benchmark,
            gate_decision,
        ),
        "synthetic_decision_status": benchmark.synthetic_decision_status,
        "gate_decision": gate_decision,
        "fixture_version": fixture_manifest.fixture_version,
        "tolerance_profile": fixture_manifest.tolerance_profile,
        "legacy_fixture_status": benchmark.legacy_fixture_status,
        "decision_target": args.decision_target,
        "fixture_manifest_hash": _hash_or_empty(args.fixture_manifest),
        "fixture_lock_hash": fixture_lock.whole_lock_hash,
        "tier_a_generated_by_git_sha": (
            tier_a_manifest.generated_by_git_sha if tier_a_manifest is not None else ""
        ),
        "tier_a_current_code_compatibility_status": (
            tier_a_manifest.current_code_compatibility_status
            if tier_a_manifest is not None
            else ""
        ),
        "tier_a_rows_hash": _hash_or_empty(args.tier_a_rows),
        "tier_a_summary_hash": _hash_or_empty(args.tier_a_summary),
        "tier_a_json_hash": _hash_or_empty(args.tier_a_json),
        "tier_a_report_hash": _hash_or_empty(args.tier_a_report),
        "tier_a_manifest_hash": _hash_or_empty(args.tier_a_manifest),
        "tier_a_expected_family_count": (
            tier_a_manifest.expected_family_count if tier_a_manifest is not None else ""
        ),
        "tier_a_observed_family_count": tier_a.family_count,
        "tier_a_expected_row_count": (
            tier_a_manifest.expected_row_count if tier_a_manifest is not None else ""
        ),
        "tier_a_observed_row_count": tier_a.row_count,
        "tier_a_source_input_hashes": ";".join(
            str(ref.get("sha256", ""))
            for ref in (
                tier_a_manifest.source_inputs.values()
                if tier_a_manifest is not None
                else ()
            )
        ),
        "p2b_85raw_acceptance_ref": str(args.p2b_85raw_acceptance_manifest or ""),
        "p2b_85raw_acceptance_hash": _hash_or_empty(args.p2b_85raw_acceptance_manifest),
        "asls_lam": fixture_manifest.asls_lam,
        "asls_p": fixture_manifest.asls_p,
        "asls_n_iter": fixture_manifest.asls_n_iter,
        "generator_seed": fixture_manifest.generator_seed,
        "bounds_policy": "locked_true_peak_bounds_v1",
        "heldout_row_count": benchmark.heldout_row_count,
        "tier_b1_status": benchmark.tier_b1_status,
        "tier_b1_accuracy_scope": benchmark.tier_b1_accuracy_scope,
        "tier_b2_status": benchmark.tier_b2_status,
        "fixture_scope_status": benchmark.fixture_scope_status,
        "tier_b1_heldout_row_count": benchmark.tier_b1_heldout_row_count,
        "b1_adjacent_stress_row_count": benchmark.b1_adjacent_stress_row_count,
        "tier_b2_heldout_row_count": benchmark.tier_b2_heldout_row_count,
        "tier_b1_hard_blocker_count": len(benchmark.b1_hard_blockers),
        "tier_b2_stress_blocker_count": len(benchmark.b2_retirement_blockers),
        "production_like_heldout_row_count": benchmark.production_like_heldout_row_count,
        "stress_heldout_row_count": benchmark.stress_heldout_row_count,
        "hard_blocker_count": len(benchmark.b1_hard_blockers)
        + len(benchmark.b2_retirement_blockers),
        "max_asls_raw_area_exceedance_count": _count_reason(
            benchmark.rows,
            "asls_exceeds_raw_area",
        ),
        "max_negative_nonblank_area_count": _count_reason(
            benchmark.rows,
            "asls_negative_nonblank_area",
        ),
        "blank_false_positive_rate": benchmark.blank_false_positive_rate,
        "blank_not_quantifiable_rate": benchmark.blank_not_quantifiable_rate,
        "blank_synthetic_scope": TIER_B2_STRESS,
        "coverage_status": coverage_status,
        "b1_coverage_status": coverage_status,
        "b2_stress_status": benchmark.tier_b2_status,
        "unmapped_observed_pattern_count": sum(
            1 for row in tier_a.coverage_rows if row.unmapped_reason
        ),
        "tier_c_axis": str(tier_c_object.get("tier_c_axis", "")),
        "tier_c_status": tier_c_status,
        "tier_c_nonblank_status": tier_c_nonblank_status,
        "blank_safety_status": blank_safety_status,
        "stress_axis_disposition_statuses": ";".join(stress_axis_dispositions),
        "tier_c_evidence_ref": str(args.tier_c_evidence or ""),
        "tier_c_evidence_hash": _hash_or_empty(args.tier_c_evidence),
        "waiver_ref": str(args.methodology_waiver or ""),
        "methodology_waiver_hash": _hash_or_empty(args.methodology_waiver),
        "methodology_owner": str(waiver_object.get("methodology_owner", "")),
        "waiver_scope": _join_strings(waiver_object.get("output_scope")),
        "waiver_valid": waiver_state == VALID,
        "waiver_expiry_or_revalidation_trigger": str(
            waiver_object.get("expiry_or_revalidation_trigger", "")
        ),
        "retirement_prereq_status": retirement_prereq_status,
        "c1a_status": str(prereq_object.get("c1a_status", "")),
        "c5_status": str(prereq_object.get("c5_status", "")),
        "rollback_column_status": str(prereq_object.get("rollback_column_status", "")),
        "retirement_prereq_manifest_hash": _hash_or_empty(args.retirement_prereq_manifest),
        "worst_heldout_median_relative_error_pct": (
            benchmark.worst_heldout_median_relative_error_pct
        ),
        "worst_heldout_p95_relative_error_pct": (
            benchmark.worst_heldout_p95_relative_error_pct
        ),
        "previous_failed_run_refs": "",
    }


def _json_payload(
    *,
    args: argparse.Namespace,
    summary: dict[str, object],
    fixture_manifest: FixtureManifest,
    fixture_lock: FixtureLock,
    tier_a_manifest: TierAManifest | None,
    optional_inputs: dict[str, dict[str, Any]],
    benchmark: SyntheticBenchmarkResult,
    coverage_rows: tuple[CoverageRow, ...],
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "provenance": {
            "command_line": list(getattr(args, "command_line", ())),
            "code_git_sha": _current_git_sha(args.output_dir),
            "run_timestamp": dt.datetime.now(dt.UTC).isoformat(),
        },
        "inputs": {
            "fixture_manifest": {
                "path": str(args.fixture_manifest),
                "hash": _hash_or_empty(args.fixture_manifest),
                "object": _json_object_or_empty(args.fixture_manifest),
                "validated": asdict(fixture_manifest),
            },
            "fixture_lock": {
                "path": str(args.fixture_lock),
                "hash": fixture_lock.whole_lock_hash,
                "object": _json_object_or_empty(args.fixture_lock),
            },
            "tier_a": {
                "manifest": {
                    "path": str(args.tier_a_manifest),
                    "hash": _hash_or_empty(args.tier_a_manifest),
                    "object": _json_object_or_empty(args.tier_a_manifest),
                    "validated": (
                        asdict(tier_a_manifest) if tier_a_manifest is not None else {}
                    ),
                },
                "artifact_refs": {
                    "rows": str(args.tier_a_rows),
                    "summary": str(args.tier_a_summary),
                    "json": str(args.tier_a_json),
                    "report": str(args.tier_a_report),
                },
                "artifact_hashes": {
                    "rows": _hash_or_empty(args.tier_a_rows),
                    "summary": _hash_or_empty(args.tier_a_summary),
                    "json": _hash_or_empty(args.tier_a_json),
                    "report": _hash_or_empty(args.tier_a_report),
                },
                "source_input_hashes": (
                    {
                        key: ref.get("sha256", "")
                        for key, ref in tier_a_manifest.source_inputs.items()
                    }
                    if tier_a_manifest is not None
                    else {}
                ),
            },
            "p2b_85raw_acceptance": optional_inputs["p2b_85raw_acceptance"],
            "tier_c_evidence": optional_inputs["tier_c_evidence"],
            "methodology_waiver": optional_inputs["methodology_waiver"],
            "retirement_prerequisites": optional_inputs["retirement_prerequisites"],
        },
        "asls_parameters": {
            "lam": fixture_manifest.asls_lam,
            "p": fixture_manifest.asls_p,
            "n_iter": fixture_manifest.asls_n_iter,
        },
        "benchmark": {
            "status": _benchmark_summary_status(benchmark.synthetic_decision_status),
            "synthetic_decision_status": benchmark.synthetic_decision_status,
            "tier_b1_status": benchmark.tier_b1_status,
            "tier_b2_status": benchmark.tier_b2_status,
            "fixture_scope_status": benchmark.fixture_scope_status,
            "legacy_fixture_status": benchmark.legacy_fixture_status,
            "b1_hard_blockers": list(benchmark.b1_hard_blockers),
            "b1_cautions": list(benchmark.b1_cautions),
            "b2_retirement_blockers": list(benchmark.b2_retirement_blockers),
        },
        "tolerance_profile": fixture_manifest.tolerance_profile,
        "coverage": [_coverage_dict(row) for row in coverage_rows],
        "rows": [_row_dict(row) for row in benchmark.rows],
        "summary": [summary],
        "previous_failed_run_refs": summary.get("previous_failed_run_refs", ""),
    }


def _copy_artifacts(args: argparse.Namespace, outputs: TruthValidationOutputs) -> None:
    _copy_if_exists(args.fixture_manifest, outputs.fixture_manifest_json)
    _copy_if_exists(args.fixture_lock, outputs.fixture_lock_json)
    _copy_if_exists(args.tier_a_manifest, outputs.tier_a_manifest_json)
    if args.p2b_85raw_acceptance_manifest is not None:
        _copy_if_exists(args.p2b_85raw_acceptance_manifest, outputs.p2b_85raw_acceptance_json)
    if args.tier_c_evidence is not None:
        _copy_if_exists(args.tier_c_evidence, outputs.tier_c_evidence_json)
    if args.methodology_waiver is not None:
        _copy_if_exists(args.methodology_waiver, outputs.methodology_waiver_json)
    if args.retirement_prereq_manifest is not None:
        _copy_if_exists(args.retirement_prereq_manifest, outputs.retirement_prereq_json)


def _copy_if_exists(source: Path, destination: Path) -> None:
    if source.exists():
        _copy(source, destination)


def _copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def _row_dict(row: SyntheticComparisonRow) -> dict[str, object]:
    return {
        "tier": "B",
        "target_label": "",
        "feature_family_id": "",
        "rt_identity_status": PASS,
        "boundary_status": PASS,
        **asdict(row),
        "failure_reasons": ";".join(row.failure_reasons),
    }


def _coverage_dict(row: CoverageRow) -> dict[str, object]:
    return {
        **asdict(row),
        "required_b1_fixture_classes": ";".join(row.required_b1_fixture_classes),
        "covered_b1_fixture_classes": ";".join(row.covered_b1_fixture_classes),
        "b2_stress_fixture_classes": ";".join(row.b2_stress_fixture_classes),
    }


def _write_markdown(path: Path, summary: dict[str, object]) -> None:
    lines = [
        "# P2c AsLS Truth Validation",
        "",
        f"Gate decision: {summary['gate_decision']}",
        f"Decision target: {summary['decision_target']}",
        f"Benchmark status: {summary['benchmark_status']}",
        f"Hard blockers: {summary['hard_blocker_count']}",
        "",
        "Exit 0 is reserved for `GO_FOR_LINEAR_EDGE_RETIREMENT`.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _hash_or_empty(path: Path | None) -> str:
    if path is None:
        return ""
    from tools.diagnostics.asls_truth_validation_inputs import sha256_file

    try:
        return sha256_file(path)
    except OSError:
        return ""


def _count_reason(rows: tuple[SyntheticComparisonRow, ...], reason: str) -> int:
    return sum(1 for row in rows if reason in row.failure_reasons)


def _rate(values: Iterable[bool]) -> float | None:
    values = tuple(values)
    if not values:
        return None
    return sum(1 for value in values if value) / len(values)


def _try_load_tier_a_manifest(path: Path) -> TierAManifest | None:
    try:
        return load_tier_a_manifest(path)
    except (OSError, ValueError):
        return None


def _optional_input_objects(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    return {
        "p2b_85raw_acceptance": _optional_json_input(
            args.p2b_85raw_acceptance_manifest
        ),
        "tier_c_evidence": _optional_json_input(args.tier_c_evidence),
        "methodology_waiver": _optional_json_input(args.methodology_waiver),
        "retirement_prerequisites": _optional_json_input(args.retirement_prereq_manifest),
    }


def _optional_json_input(path: Path | None) -> dict[str, Any]:
    loaded, error = _json_object_or_error(path)
    return {
        "path": str(path or ""),
        "hash": _hash_or_empty(path),
        "object": loaded,
        "load_error": error,
    }


def _json_object_or_empty(path: Path | None) -> dict[str, Any]:
    loaded, _error = _json_object_or_error(path)
    return loaded


def _json_object_or_error(path: Path | None) -> tuple[dict[str, Any], str]:
    if path is None:
        return {}, ""
    try:
        return load_json_object(path), ""
    except (OSError, ValueError) as exc:
        return {}, str(exc)


def _join_strings(value: object) -> str:
    if isinstance(value, list | tuple):
        return ";".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def _current_git_sha(path_hint: Path) -> str:
    repo_root = _find_repo_root(path_hint)
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def _find_repo_root(path_hint: Path) -> Path:
    start = path_hint.resolve()
    current = start.parent if start.suffix else start
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return Path.cwd()


def _benchmark_summary_status(status: str) -> str:
    if status.startswith("INCONCLUSIVE"):
        return "INCONCLUSIVE"
    return status


def _benchmark_status_for_target(
    decision_target: str,
    benchmark: SyntheticBenchmarkResult,
    gate_decision: str,
) -> str:
    if gate_decision.startswith("INCONCLUSIVE"):
        return BENCHMARK_STATUS_INCONCLUSIVE
    if decision_target == "c1b-plan":
        return _benchmark_summary_status(benchmark.tier_b1_status)
    if gate_decision == GATE_RETIREMENT:
        return PASS
    if benchmark.tier_b1_status == FAIL or benchmark.tier_b2_status == FAIL:
        return BENCHMARK_STATUS_FAIL
    if benchmark.tier_b1_status.startswith("INCONCLUSIVE"):
        return BENCHMARK_STATUS_INCONCLUSIVE
    return PASS


def _write_fallback_outputs(
    args: argparse.Namespace,
    outputs: TruthValidationOutputs,
    exc: Exception,
) -> None:
    outputs.rows_tsv.parent.mkdir(parents=True, exist_ok=True)
    gate = _fallback_gate(str(exc))
    summary = _fallback_summary(args, gate_decision=gate, error_message=str(exc))
    write_tsv(outputs.rows_tsv, [], ROW_FIELDS)
    write_tsv(outputs.summary_tsv, [summary], SUMMARY_FIELDS)
    write_tsv(outputs.coverage_tsv, [], COVERAGE_FIELDS)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "provenance": {
            "command_line": list(getattr(args, "command_line", ())),
            "code_git_sha": _current_git_sha(args.output_dir),
            "run_timestamp": dt.datetime.now(dt.UTC).isoformat(),
            "error": str(exc),
        },
        "inputs": {
            "fixture_manifest": _optional_json_input(args.fixture_manifest),
            "fixture_lock": _optional_json_input(args.fixture_lock),
            "tier_a": {
                "manifest": _optional_json_input(args.tier_a_manifest),
                "artifact_refs": {
                    "rows": str(args.tier_a_rows),
                    "summary": str(args.tier_a_summary),
                    "json": str(args.tier_a_json),
                    "report": str(args.tier_a_report),
                },
                "artifact_hashes": {
                    "rows": _hash_or_empty(args.tier_a_rows),
                    "summary": _hash_or_empty(args.tier_a_summary),
                    "json": _hash_or_empty(args.tier_a_json),
                    "report": _hash_or_empty(args.tier_a_report),
                },
            },
            **_optional_input_objects(args),
        },
        "benchmark": {
            "status": "INCONCLUSIVE",
            "synthetic_decision_status": "INCONCLUSIVE",
            "tier_b1_status": gate,
            "tier_b2_status": TIER_B2_STATUS_NOT_RUN,
            "fixture_scope_status": gate,
            "legacy_fixture_status": "",
            "b1_hard_blockers": [],
            "b1_cautions": [],
            "b2_retirement_blockers": [],
        },
        "coverage": [],
        "rows": [],
        "summary": [summary],
        "previous_failed_run_refs": str(exc),
    }
    outputs.json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(outputs.markdown_path, summary)
    _copy_artifacts(args, outputs)


def _fallback_gate(message: str) -> str:
    if "fixture_lock_hash does not match" in message or "whole_lock_hash" in message:
        from tools.diagnostics.asls_truth_validation_models import (
            INCONCLUSIVE_FIXTURE_LOCK_CHANGED,
        )

        return INCONCLUSIVE_FIXTURE_LOCK_CHANGED
    return INCONCLUSIVE_INVALID_INPUT


def _fallback_summary(
    args: argparse.Namespace,
    *,
    gate_decision: str,
    error_message: str,
) -> dict[str, object]:
    row = {field: "" for field in SUMMARY_FIELDS}
    row.update(
        {
            "readiness_status": "diagnostic_only",
            "benchmark_status": "INCONCLUSIVE",
            "synthetic_decision_status": "INCONCLUSIVE",
            "gate_decision": gate_decision,
            "decision_target": args.decision_target,
            "legacy_fixture_status": "",
            "fixture_scope_status": gate_decision,
            "tier_b1_status": gate_decision,
            "tier_b2_status": TIER_B2_STATUS_NOT_RUN,
            "tier_b1_accuracy_scope": "",
            "blank_synthetic_scope": TIER_B2_STRESS,
            "b1_coverage_status": gate_decision,
            "b2_stress_status": TIER_B2_STATUS_NOT_RUN,
            "fixture_manifest_hash": _hash_or_empty(args.fixture_manifest),
            "fixture_lock_hash": _hash_or_empty(args.fixture_lock),
            "tier_a_rows_hash": _hash_or_empty(args.tier_a_rows),
            "tier_a_summary_hash": _hash_or_empty(args.tier_a_summary),
            "tier_a_json_hash": _hash_or_empty(args.tier_a_json),
            "tier_a_report_hash": _hash_or_empty(args.tier_a_report),
            "tier_a_manifest_hash": _hash_or_empty(args.tier_a_manifest),
            "p2b_85raw_acceptance_ref": str(args.p2b_85raw_acceptance_manifest or ""),
            "p2b_85raw_acceptance_hash": _hash_or_empty(
                args.p2b_85raw_acceptance_manifest
            ),
            "tier_c_status": NOT_PROVIDED,
            "tier_c_nonblank_status": NOT_PROVIDED,
            "blank_safety_status": NOT_PROVIDED,
            "tier_c_evidence_ref": str(args.tier_c_evidence or ""),
            "tier_c_evidence_hash": _hash_or_empty(args.tier_c_evidence),
            "waiver_ref": str(args.methodology_waiver or ""),
            "methodology_waiver_hash": _hash_or_empty(args.methodology_waiver),
            "waiver_valid": False,
            "retirement_prereq_status": NOT_PROVIDED,
            "retirement_prereq_manifest_hash": _hash_or_empty(
                args.retirement_prereq_manifest
            ),
            "previous_failed_run_refs": error_message,
        }
    )
    return row


def _median_relative_error(rows: Sequence[SyntheticComparisonRow]) -> float | None:
    values = [row.asls_relative_error_pct for row in rows if row.asls_relative_error_pct is not None]
    if not values:
        return None
    return float(median(values))


def _p95_relative_error(rows: Sequence[SyntheticComparisonRow]) -> float | None:
    values = sorted(
        row.asls_relative_error_pct
        for row in rows
        if row.asls_relative_error_pct is not None
    )
    if not values:
        return None
    index = min(len(values) - 1, int(round(0.95 * (len(values) - 1))))
    return float(values[index])


if __name__ == "__main__":
    raise SystemExit(main())
