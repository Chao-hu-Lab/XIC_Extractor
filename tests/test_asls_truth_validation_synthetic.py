from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from tools.diagnostics.asls_truth_validation_manifests import (
    REQUIRED_FIXTURE_CLASSES,
    load_fixture_lock,
    load_fixture_manifest,
)
from tools.diagnostics.asls_truth_validation_models import (
    BLOCKER_SCOPE_B1_C1B,
    BLOCKER_SCOPE_B2_RETIREMENT,
    BLOCKER_SCOPE_CAUTION,
    INCONCLUSIVE_FIXTURE_LOCK_CHANGED,
    PRODUCTION_LIKE_IN_SCOPE,
    ROW_STATUS_HARD_BLOCKER,
    ROW_STATUS_PASS,
    TIER_B1_RELEVANCE,
    TIER_B2_STRESS,
)
from tools.diagnostics.asls_truth_validation_synthetic import (
    SyntheticComparisonRow,
    SyntheticTrace,
    blank_false_positive,
    classify_tier_b_blockers,
    compare_synthetic_trace,
    generate_synthetic_traces,
    tier_b_hard_blockers,
    validate_synthetic_fixture_lock,
)
from xic_extractor.peak_detection.baseline import BaselineIntegration


FIXTURE_DIR = Path("docs/superpowers/fixtures")
FIXTURE_MANIFEST = FIXTURE_DIR / "asls_truth_validation_fixture_manifest.json"
FIXTURE_LOCK = FIXTURE_DIR / "asls_truth_validation_fixture_lock.json"


def test_generate_synthetic_traces_uses_locked_manifest_and_lock() -> None:
    manifest = load_fixture_manifest(FIXTURE_MANIFEST)
    lock = load_fixture_lock(FIXTURE_LOCK)

    traces = generate_synthetic_traces(manifest, lock)

    assert [trace.fixture_id for trace in traces] == [
        record.fixture_id for record in lock.records
    ]
    assert len([trace for trace in traces if trace.split == "heldout_gate"]) >= 11 * 25
    assert {trace.fixture_class for trace in traces} == set(REQUIRED_FIXTURE_CLASSES)
    counts = Counter((trace.fixture_class, trace.split) for trace in traces)
    for class_name in REQUIRED_FIXTURE_CLASSES:
        assert counts[(class_name, "calibration")] >= 10
        assert counts[(class_name, "heldout_gate")] >= 25
    assert all(len(trace.rt_values) == len(trace.intensity_values) for trace in traces)
    assert all(float(trace.intensity_values.min()) >= 0.0 for trace in traces)


def test_generate_synthetic_traces_preserves_heldout_cross_coverage() -> None:
    manifest = load_fixture_manifest(FIXTURE_MANIFEST)
    lock = load_fixture_lock(FIXTURE_LOCK)

    traces = generate_synthetic_traces(manifest, lock)

    for class_name in REQUIRED_FIXTURE_CLASSES:
        heldout = [
            trace
            for trace in traces
            if trace.fixture_class == class_name and trace.split == "heldout_gate"
        ]
        if class_name == "blank_noise_control":
            assert {trace.true_area for trace in heldout} == {0.0}
            continue
        assert {trace.sn_stratum for trace in heldout} == {"low", "medium", "high"}
        assert {trace.peak_width_stratum for trace in heldout} == {
            "narrow",
            "typical",
            "wide",
        }
        assert {
            (trace.sn_stratum, trace.peak_width_stratum) for trace in heldout
        } == {
            ("low", "narrow"),
            ("low", "typical"),
            ("low", "wide"),
            ("medium", "narrow"),
            ("medium", "typical"),
            ("medium", "wide"),
            ("high", "narrow"),
            ("high", "typical"),
            ("high", "wide"),
        }


def test_validate_synthetic_fixture_lock_reports_hash_drift() -> None:
    manifest = load_fixture_manifest(FIXTURE_MANIFEST)
    lock = load_fixture_lock(FIXTURE_LOCK)
    stale_manifest = replace(manifest, fixture_lock_hash="stale")

    status = validate_synthetic_fixture_lock(stale_manifest, lock)

    assert status == INCONCLUSIVE_FIXTURE_LOCK_CHANGED
    with pytest.raises(ValueError, match=INCONCLUSIVE_FIXTURE_LOCK_CHANGED):
        generate_synthetic_traces(stale_manifest, lock)


def test_generate_synthetic_traces_rejects_unsupported_true_area_formula() -> None:
    manifest = load_fixture_manifest(FIXTURE_MANIFEST)
    lock = load_fixture_lock(FIXTURE_LOCK)
    records = list(lock.records)
    records[0] = replace(records[0], true_area_formula_version="unknown_formula_v1")
    stale_lock = replace(lock, records=tuple(records))

    with pytest.raises(ValueError, match="unsupported true_area_formula_version"):
        generate_synthetic_traces(manifest, stale_lock)


def test_blank_false_positive_uses_uncertainty_and_nonblank_reference() -> None:
    assert blank_false_positive(
        asls_area=16.0,
        area_uncertainty=5.0,
        reference_nonblank_median_true_area=1000.0,
    )
    assert not blank_false_positive(
        asls_area=15.0,
        area_uncertainty=5.0,
        reference_nonblank_median_true_area=1000.0,
    )
    assert blank_false_positive(
        asls_area=51.0,
        area_uncertainty=1.0,
        reference_nonblank_median_true_area=10000.0,
    )
    assert not blank_false_positive(
        asls_area=50.0,
        area_uncertainty=1.0,
        reference_nonblank_median_true_area=10000.0,
    )
    assert blank_false_positive(
        asls_area=6.0,
        area_uncertainty=None,
        reference_nonblank_median_true_area=1000.0,
    )


def test_compare_synthetic_trace_flags_asls_hard_blockers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = load_fixture_manifest(FIXTURE_MANIFEST)
    lock = load_fixture_lock(FIXTURE_LOCK)
    trace = next(
        trace
        for trace in generate_synthetic_traces(manifest, lock)
        if trace.fixture_class == "flat_peak_control" and trace.split == "heldout_gate"
    )

    def fake_asls(*_args: object, **_kwargs: object) -> BaselineIntegration:
        return BaselineIntegration(
            area_baseline_corrected=-1.0,
            area_uncertainty=2.0,
            baseline_type="asls",
            baseline_score=None,
        )

    monkeypatch.setattr(
        "tools.diagnostics.asls_truth_validation_synthetic.integrate_asls_baseline",
        fake_asls,
    )

    row = compare_synthetic_trace(
        trace,
        asls_params={
            "lam": manifest.asls_lam,
            "p": manifest.asls_p,
            "n_iter": manifest.asls_n_iter,
        },
        reference_nonblank_median_true_area=1000.0,
    )

    assert row.asls_negative_nonblank_area
    assert "asls_negative_nonblank_area" in row.failure_reasons
    assert row.row_status == ROW_STATUS_HARD_BLOCKER


def test_compare_synthetic_trace_flags_asls_raw_area_exceedance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = load_fixture_manifest(FIXTURE_MANIFEST)
    lock = load_fixture_lock(FIXTURE_LOCK)
    trace = next(
        trace
        for trace in generate_synthetic_traces(manifest, lock)
        if trace.fixture_class == "flat_peak_control" and trace.split == "heldout_gate"
    )

    def fake_asls(*_args: object, **_kwargs: object) -> BaselineIntegration:
        return BaselineIntegration(
            area_baseline_corrected=1e12,
            area_uncertainty=2.0,
            baseline_type="asls",
            baseline_score=None,
        )

    monkeypatch.setattr(
        "tools.diagnostics.asls_truth_validation_synthetic.integrate_asls_baseline",
        fake_asls,
    )

    row = compare_synthetic_trace(
        trace,
        asls_params={
            "lam": manifest.asls_lam,
            "p": manifest.asls_p,
            "n_iter": manifest.asls_n_iter,
        },
        reference_nonblank_median_true_area=1000.0,
    )

    assert row.asls_exceeds_raw_area
    assert "asls_exceeds_raw_area" in row.failure_reasons
    assert row.row_status == ROW_STATUS_HARD_BLOCKER


def test_tier_b_hard_blockers_include_heldout_error_thresholds() -> None:
    rows = (
        _comparison_row("flat_peak_control", linear_abs=1.0, asls_abs=6.0, true_area=100.0),
        _comparison_row("flat_peak_control", linear_abs=1.0, asls_abs=6.0, true_area=100.0),
        _comparison_row("flat_peak_control", linear_abs=1.0, asls_abs=10.0, true_area=100.0),
    )

    summary = classify_tier_b_blockers(rows)

    assert "flat_peak_control:median_asls_relative_error_gt_5pct" in summary.b1_hard_blockers
    assert "flat_peak_control:p95_asls_relative_error_gt_8pct" in summary.b1_cautions


def test_tier_b_hard_blockers_enforce_improvement_or_low_error_classes() -> None:
    rows = (
        _comparison_row(
            "tailing_peak",
            linear_abs=10.0,
            asls_abs=9.0,
            true_area=80.0,
        ),
        _comparison_row(
            "tailing_peak",
            linear_abs=10.0,
            asls_abs=9.0,
            true_area=80.0,
        ),
    )

    blockers = tier_b_hard_blockers(rows)

    assert "tailing_peak:asls_lacks_20pct_improvement_or_3pct_abs_error" in blockers


def test_tier_b_hard_blockers_do_not_fail_low_relative_error_for_small_improvement() -> None:
    rows = (
        _comparison_row(
            "sloped_baseline_peak",
            linear_abs=10.0,
            asls_abs=9.5,
            true_area=100.0,
        ),
        _comparison_row(
            "sloped_baseline_peak",
            linear_abs=10.0,
            asls_abs=9.5,
            true_area=100.0,
        ),
    )

    blockers = tier_b_hard_blockers(rows)

    assert not any(
        blocker == "sloped_baseline_peak:asls_lacks_20pct_improvement_or_3pct_abs_error"
        for blocker in blockers
    )


def test_tier_b_hard_blockers_accept_low_absolute_error_without_improvement() -> None:
    rows = (
        _comparison_row(
            "sloped_baseline_peak",
            linear_abs=3.0,
            asls_abs=2.5,
            true_area=1000.0,
        ),
        _comparison_row(
            "sloped_baseline_peak",
            linear_abs=3.0,
            asls_abs=2.5,
            true_area=1000.0,
        ),
    )

    blockers = tier_b_hard_blockers(rows)

    assert not any("sloped_baseline_peak:" in blocker for blocker in blockers)


def test_tier_b_hard_blockers_keep_b2_retirement_scope_out_of_b1_summary() -> None:
    rows = (
        _comparison_row(
            "blank_noise_control",
            linear_abs=0.0,
            asls_abs=20.0,
            true_area=0.0,
            tier_b_layer=TIER_B2_STRESS,
            blocker_scope=BLOCKER_SCOPE_B2_RETIREMENT,
            failure_reasons=("blank_false_positive",),
        ),
    )

    summary = classify_tier_b_blockers(rows)

    assert summary.tier_b1_status == "PASS"
    assert summary.b1_hard_blockers == ()
    assert "blank_false_positive" in summary.b2_retirement_blockers


def _comparison_row(
    fixture_class: str,
    *,
    linear_abs: float,
    asls_abs: float,
    true_area: float,
    tier_b_layer: str = TIER_B1_RELEVANCE,
    blocker_scope: str = "",
    failure_reasons: tuple[str, ...] = (),
) -> SyntheticComparisonRow:
    if failure_reasons and not blocker_scope:
        blocker_scope = BLOCKER_SCOPE_B1_C1B
    if asls_abs > 8.0 and fixture_class == "flat_peak_control":
        blocker_scope = blocker_scope or BLOCKER_SCOPE_CAUTION
    return SyntheticComparisonRow(
        tier_b_layer=tier_b_layer,
        fixture_id=f"{fixture_class}_heldout_gate_test",
        fixture_class=fixture_class,
        split="heldout_gate",
        replicate_id=1,
        stress_role="b1_relevance" if tier_b_layer == TIER_B1_RELEVANCE else "stress",
        production_like_bounds_status=PRODUCTION_LIKE_IN_SCOPE,
        scan_density_stratum="medium",
        integration_point_count=21,
        integration_width_min=0.4,
        raw_area=true_area * 1.5,
        true_area=true_area,
        linear_edge_area=true_area + linear_abs,
        asls_area=true_area + asls_abs,
        linear_edge_abs_error=linear_abs,
        asls_abs_error=asls_abs,
        linear_edge_relative_error_pct=(
            linear_abs / true_area * 100.0 if true_area > 0 else None
        ),
        asls_relative_error_pct=asls_abs / true_area * 100.0 if true_area > 0 else None,
        asls_error_over_linear_error=asls_abs / linear_abs if linear_abs > 0 else None,
        asls_exceeds_raw_area=False,
        asls_negative_nonblank_area=False,
        blank_false_positive=False,
        blank_not_quantifiable=False,
        asls_area_uncertainty=None,
        asls_baseline_residual_mad=None,
        asls_area_uncertainty_noise_source="",
        blocker_scope=blocker_scope,
        row_status=ROW_STATUS_HARD_BLOCKER if failure_reasons else ROW_STATUS_PASS,
        failure_reasons=failure_reasons,
    )
