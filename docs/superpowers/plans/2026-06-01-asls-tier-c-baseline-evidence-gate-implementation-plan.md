# AsLS Tier C Baseline Evidence Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Replace the stale Tier C truth-comparator gate with a real-data AsLS-vs-linear-edge baseline-evidence gate in the `asls_truth_validation` diagnostic.

**Architecture:** Keep the diagnostic as the owner of retirement-readiness evidence validation, not production integration behavior. The validator accepts one Tier C axis, `asls_vs_linear_edge_baseline_audit`, rolls family-level baseline review dispositions into machine-readable summary fields, and feeds the existing gate decision function. CLI outputs remain diagnostic-only artifacts and keep copying supplied optional evidence unchanged.

**Tech Stack:** Python 3, dataclasses, JSON/TSV file validation, pytest, ruff, mypy, PowerShell commands.

---

## Scope

### Now

- Implement the Tier C evidence schema from `docs/superpowers/specs/2026-05-26-peak-pipeline-asls-truth-validation-spec.md`.
- Compare AsLS against `linear_edge` baseline evidence only; do not introduce manual-integration, spike-in, or concentration-series truth comparators.
- Replace `tier_c_nonblank_status` with `tier_c_baseline_evidence_status` plus explicit C1b relevance and stress-axis gate status.
- Add row blocker, review-required, C1b relevance, and stress-axis gate fields to summary output.
- Preserve `GO_FOR_C1B_PLAN_SYNTHETIC_ONLY` when Tier C is absent, unresolved, or failing only retirement-only evidence; a Tier C failure blocks C1b planning only when it is in `C1B_RELEVANCE` scope.
- Keep `GO_FOR_LINEAR_EDGE_RETIREMENT` blocked unless Tier A, B1, B2, Tier C baseline evidence, blank/stress safety, and retirement prerequisites pass.

### Future PR

- Delete the legacy `integrate_linear_edge_baseline` production support path after C1a, C5, rollback-column deprecation, and this Tier C gate all pass.
- Generate real Tier C cohort artifacts from RAW data.
- Deprecate rollback audit columns.

### Not In Scope

- RAW validation runs.
- Production default method changes.
- Removing `linear_edge` rollback/comparator code.
- Changing `tools/diagnostics/p2_baseline_truth_audit.py` output schema.
- Commit, push, or PR creation. Repo rules require explicit user authorization before committing.

## File Structure

- Modify `tools/diagnostics/asls_truth_validation_models.py`
  - Owns gate constants, Tier C enum constants, and the summary TSV field order.
- Modify `tools/diagnostics/asls_truth_validation_inputs.py`
  - Owns JSON validation, hashed artifact checks, family-disposition rollup, blank safety contract validation, and waiver validation.
- Modify `tools/diagnostics/asls_truth_validation_analysis.py`
  - Owns gate decision logic after validation has reduced inputs to status fields.
- Modify `tools/diagnostics/asls_truth_validation.py`
  - Owns CLI orchestration, summary row construction, fallback summary fields, and copied optional evidence.
- Modify `tests/test_asls_truth_validation_models.py`
  - Locks the public summary schema.
- Modify `tests/test_asls_truth_validation_inputs.py`
  - Locks Tier C evidence schema, family rollup, blank safety, and waiver contract validation.
- Modify `tests/test_asls_truth_validation_analysis.py`
  - Locks gate behavior for C1b planning and linear-edge retirement.
- Modify `tests/test_asls_truth_validation_cli.py`
  - Locks CLI summary fields, JSON copied evidence, and stale-field removal.

## Contract Details

Tier C evidence input must use this shape. Family dispositions are review
metadata, not authority by themselves; every disposition must link back to the
hashed `baseline_truth_artifacts` rows and summary.

```json
{
  "tier_c_axis": "asls_vs_linear_edge_baseline_audit",
  "tier_c_status": "PASS",
  "tier_c_baseline_evidence_status": "PASS",
  "blank_safety_status": "NOT_APPLICABLE_WITH_EXCLUSION",
  "ratio_metrics_are_descriptive": true,
  "fixed_area_uplift_threshold": null,
  "baseline_truth_artifacts": {
    "rows_tsv": {"path": "path/to/baseline_truth_audit_rows.tsv", "sha256": "sha256"},
    "summary_tsv": {"path": "path/to/baseline_truth_audit_summary.tsv", "sha256": "sha256"},
    "json": {"path": "path/to/baseline_truth_audit.json", "sha256": "sha256"},
    "markdown": {"path": "path/to/baseline_truth_audit.md", "sha256": "sha256"},
    "plot_dir": "path/to/plots"
  },
  "family_dispositions": [
    {
      "target_label": "ISTD-A",
      "feature_family_id": "ISTD-A::100.0::1.20",
      "covered_samples": ["sample_001"],
      "dominant_classification": "linear_edge_over_subtraction_plausible",
      "review_status": "reviewed",
      "decision_scope": "C1B_RELEVANCE",
      "plot_path": "path/to/plots/ISTD-A.png",
      "reviewed_rows": [
        {
          "target_label": "ISTD-A",
          "feature_family_id": "ISTD-A::100.0::1.20",
          "sample_stem": "sample_001",
          "peak_start_rt": "1.10",
          "apex_rt": "1.20",
          "peak_end_rt": "1.30",
          "plot_path": "path/to/plots/ISTD-A.png"
        }
      ],
      "family_disposition": "PASS_BASELINE_SUPPORTED",
      "tier_c_row_blockers": [],
      "reviewer_disposition": "AsLS follows local background better than linear edge.",
      "reason": "Linear edge cuts through the rising shoulder while AsLS tracks baseline."
    }
  ],
  "affected_outputs": ["alignment_matrix.tsv"],
  "blank_control_evidence_status": "NOT_APPLICABLE_WITH_EXCLUSION",
  "blank_control_evidence_refs": [],
  "blank_rows_absence_proof": ["alignment_matrix.tsv has no blank quantitation consumer"],
  "consumer_contract_tests": [
    {"path": "path/to/contract_test.txt", "sha256": "sha256"}
  ],
  "stress_axis_dispositions": [
    {
      "stress_axis": "blank_carryover",
      "status": "NOT_REQUIRED",
      "decision_scope": "RETIREMENT_ONLY",
      "rationale": "Scoped outputs do not consume blank quantitation.",
      "evidence_artifacts": []
    }
  ],
  "row_count": 1,
  "sample_count": 1,
  "raw_file_count": 1,
  "selected_istd_count": 1,
  "high_risk_morphology_row_count": 1,
  "covered_target_classes": ["ISTD"],
  "known_exclusions": [],
  "reviewer_or_generator": "methodology_owner",
  "output_scope": ["alignment_matrix.tsv"],
  "target_classes": ["ISTD"]
}
```

Valid family dispositions:

```python
{
    "PASS_BASELINE_SUPPORTED",
    "PASS_METHODS_SIMILAR",
    "REQUIRES_REVIEW",
    "FAIL",
    "INCONCLUSIVE",
}
```

Valid row blockers:

```python
{
    "asls_under_subtraction_plausible",
    "asls_area_exceeds_raw_area",
    "asls_negative_nonblank_area",
    "mixed_or_review_required",
    "not_assessable",
    "missing_or_stale_plot",
    "missing_row_identifier",
    "stale_artifact_hash",
    "unsupported_classification",
}
```

Rollup rules:

- `tier_c_baseline_evidence_status=PASS` only when all families are `PASS_BASELINE_SUPPORTED` or `PASS_METHODS_SIMILAR`, at least one family is `PASS_BASELINE_SUPPORTED`, every plot/hash resolves, and row blocker count is zero.
- `tier_c_baseline_evidence_status=FAIL` when any family is `FAIL` or a hard AsLS blocker is unresolved.
- `tier_c_baseline_evidence_status=NOT_PROVIDED` when evidence is absent or valid-but-unresolved review is present.
- `REQUIRES_REVIEW` must not roll up to `PASS`; it leaves retirement at `REQUIRES_TIER_C`.
- `tier_c_c1b_relevance_status=FAIL` only when a `C1B_RELEVANCE` family has a hard AsLS failure; retirement-only failures must not block `decision_target=c1b-plan`.
- `tier_c_stress_axis_gate_status=PASS` only when every supplied stress-axis disposition is `PASS` or reviewed `NOT_REQUIRED`; `NOT_PROVIDED` keeps retirement at `REQUIRES_TIER_C`, and `FAIL` blocks retirement.
- `FAMILY_DISPOSITION_INCONCLUSIVE`, malformed JSON, unsupported enums, missing artifact hashes, stale hashes, missing plots, incomplete row identifiers, missing artifact linkage, or malformed baseline audit TSV/JSON return `INCONCLUSIVE_INVALID_INPUT`.
- `blank_safety_status=PASS` requires hashed `blank_control_evidence_refs`; `blank_safety_status=NOT_APPLICABLE_WITH_EXCLUSION` requires `affected_outputs`, `blank_rows_absence_proof`, and hashed `consumer_contract_tests`.

## Task 1: Lock Summary Schema And Tier C Constants

**Files:**

- Modify: `tests/test_asls_truth_validation_models.py`
- Modify: `tools/diagnostics/asls_truth_validation_models.py`

- [x] **Step 1: Replace stale summary-schema test**

In `tests/test_asls_truth_validation_models.py`, replace the assertion that expects `tier_c_nonblank_status` with this test:

```python
def test_summary_fields_expose_tier_c_baseline_evidence_fields() -> None:
    assert "tier_c_axis" in SUMMARY_FIELDS
    assert "tier_c_status" in SUMMARY_FIELDS
    assert "tier_c_baseline_evidence_status" in SUMMARY_FIELDS
    assert "tier_c_c1b_relevance_status" in SUMMARY_FIELDS
    assert "tier_c_stress_axis_gate_status" in SUMMARY_FIELDS
    assert "tier_c_row_blocker_count" in SUMMARY_FIELDS
    assert "tier_c_review_required_count" in SUMMARY_FIELDS
    assert "blank_safety_status" in SUMMARY_FIELDS
    assert "tier_c_nonblank_status" not in SUMMARY_FIELDS
```

- [x] **Step 2: Run the schema test and confirm failure**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_asls_truth_validation_models.py::test_summary_fields_expose_tier_c_baseline_evidence_fields -q
```

Expected before implementation:

```text
FAILED
```

The failure should show `tier_c_baseline_evidence_status` or one of the count fields missing from `SUMMARY_FIELDS`.

- [x] **Step 3: Add Tier C constants and update summary fields**

In `tools/diagnostics/asls_truth_validation_models.py`, add these constants after `TIER_B2_STATUS_NOT_RUN`:

```python
TIER_C_AXIS_BASELINE_AUDIT = "asls_vs_linear_edge_baseline_audit"
TIER_C_GATE_PASS = "PASS"
TIER_C_GATE_FAIL = "FAIL"
TIER_C_GATE_NOT_PROVIDED = "NOT_PROVIDED"

FAMILY_DISPOSITION_PASS_BASELINE_SUPPORTED = "PASS_BASELINE_SUPPORTED"
FAMILY_DISPOSITION_PASS_METHODS_SIMILAR = "PASS_METHODS_SIMILAR"
FAMILY_DISPOSITION_REQUIRES_REVIEW = "REQUIRES_REVIEW"
FAMILY_DISPOSITION_FAIL = "FAIL"
FAMILY_DISPOSITION_INCONCLUSIVE = "INCONCLUSIVE"

FAMILY_DISPOSITIONS = frozenset(
    {
        FAMILY_DISPOSITION_PASS_BASELINE_SUPPORTED,
        FAMILY_DISPOSITION_PASS_METHODS_SIMILAR,
        FAMILY_DISPOSITION_REQUIRES_REVIEW,
        FAMILY_DISPOSITION_FAIL,
        FAMILY_DISPOSITION_INCONCLUSIVE,
    }
)

TIER_C_ROW_BLOCKERS = frozenset(
    {
        "asls_under_subtraction_plausible",
        "asls_area_exceeds_raw_area",
        "asls_negative_nonblank_area",
        "mixed_or_review_required",
        "not_assessable",
        "missing_or_stale_plot",
        "missing_row_identifier",
        "stale_artifact_hash",
        "unsupported_classification",
    }
)
```

In `SUMMARY_FIELDS`, replace:

```python
    "tier_c_nonblank_status",
    "blank_safety_status",
```

with:

```python
    "tier_c_baseline_evidence_status",
    "tier_c_c1b_relevance_status",
    "tier_c_stress_axis_gate_status",
    "tier_c_row_blocker_count",
    "tier_c_review_required_count",
    "blank_safety_status",
```

- [x] **Step 4: Run the schema test and confirm pass**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_asls_truth_validation_models.py::test_summary_fields_expose_tier_c_baseline_evidence_fields -q
```

Expected:

```text
1 passed
```

## Task 2: Replace Tier C Input Tests With Baseline-Evidence Tests

**Files:**

- Modify: `tests/test_asls_truth_validation_inputs.py`

- [x] **Step 1: Update imports and add test helpers for hashed artifacts and baseline evidence**

Add `FAIL` to the import list from `tools.diagnostics.asls_truth_validation_inputs` because the new failure-path tests assert it directly:

```python
    FAIL,
```

Add these helpers near the existing JSON helper functions in `tests/test_asls_truth_validation_inputs.py`:

```python
def _artifact_ref(path: Path, text: str = "artifact\n") -> dict[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {"path": str(path), "sha256": sha256_file(path)}


def _baseline_rows_text(plot_path: Path) -> str:
    header = (
        "target_label",
        "feature_family_id",
        "sample_stem",
        "status",
        "raw_area",
        "linear_area",
        "asls_area",
        "linear_raw_pct",
        "asls_raw_pct",
        "asls_vs_linear_pct",
        "linear_baseline_subtracted_pct",
        "asls_baseline_subtracted_pct",
        "linear_edge_delta_pct",
        "outside_background_pct",
        "peak_start_rt",
        "apex_rt",
        "peak_end_rt",
        "trace_point_count",
        "classification",
        "review_reason",
        "plot_path",
    )
    row = (
        "ISTD-A",
        "ISTD-A::100.0::1.20",
        "sample_001",
        "PASS",
        "100.0",
        "60.0",
        "95.0",
        "60.0",
        "95.0",
        "58.3",
        "40.0",
        "5.0",
        "35.0",
        "20.0",
        "1.10",
        "1.20",
        "1.30",
        "11",
        "linear_edge_over_subtraction_plausible",
        "linear edge crosses the shoulder",
        str(plot_path),
    )
    return "\t".join(header) + "\n" + "\t".join(row) + "\n"


def _baseline_summary_text(plot_path: Path) -> str:
    header = (
        "target_label",
        "feature_family_id",
        "row_count",
        "dominant_classification",
        "classification_counts",
        "median_linear_baseline_subtracted_pct",
        "median_asls_baseline_subtracted_pct",
        "median_asls_vs_linear_pct",
        "max_asls_vs_linear_pct",
        "median_linear_edge_delta_pct",
        "median_outside_background_pct",
        "review_status",
        "plot_path",
    )
    row = (
        "ISTD-A",
        "ISTD-A::100.0::1.20",
        "1",
        "linear_edge_over_subtraction_plausible",
        '{"linear_edge_over_subtraction_plausible": 1}',
        "40.0",
        "5.0",
        "58.3",
        "58.3",
        "35.0",
        "20.0",
        "reviewed",
        str(plot_path),
    )
    return "\t".join(header) + "\n" + "\t".join(row) + "\n"


def _baseline_json_text(plot_path: Path) -> str:
    return json.dumps(
        {
            "families": [
                {
                    "target_label": "ISTD-A",
                    "feature_family_id": "ISTD-A::100.0::1.20",
                    "dominant_classification": "linear_edge_over_subtraction_plausible",
                    "plot_path": str(plot_path),
                }
            ]
        }
    )


def _tier_c_baseline_evidence(
    tmp_path: Path,
    *,
    baseline_status: str = PASS,
    tier_c_status: str = PASS,
    family_disposition: str = "PASS_BASELINE_SUPPORTED",
    row_blockers: list[str] | None = None,
    blank_safety_status: str = NOT_APPLICABLE_WITH_EXCLUSION,
) -> dict[str, object]:
    plot_dir = tmp_path / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    plot_path = plot_dir / "ISTD-A.png"
    plot_path.write_text("plot\n", encoding="utf-8")
    contract_ref = _artifact_ref(tmp_path / "contract_test.txt", "pass\n")
    blank_refs: list[dict[str, str]] = []
    blank_absence_proof = ["alignment_matrix.tsv excludes blank quantitation"]
    contract_tests = [contract_ref]
    if blank_safety_status == PASS:
        blank_refs = [
            _artifact_ref(
                tmp_path / "blank_control_evidence.tsv",
                "sample_stem\tblank_status\nblank_001\tPASS\n",
            )
        ]
        blank_absence_proof = []
        contract_tests = []
    blockers = [] if row_blockers is None else row_blockers
    return {
        "tier_c_axis": "asls_vs_linear_edge_baseline_audit",
        "tier_c_status": tier_c_status,
        "tier_c_baseline_evidence_status": baseline_status,
        "blank_safety_status": blank_safety_status,
        "ratio_metrics_are_descriptive": True,
        "fixed_area_uplift_threshold": None,
        "baseline_truth_artifacts": {
            "rows_tsv": _artifact_ref(
                tmp_path / "baseline_truth_audit_rows.tsv",
                _baseline_rows_text(plot_path),
            ),
            "summary_tsv": _artifact_ref(
                tmp_path / "baseline_truth_audit_summary.tsv",
                _baseline_summary_text(plot_path),
            ),
            "json": _artifact_ref(
                tmp_path / "baseline_truth_audit.json",
                _baseline_json_text(plot_path),
            ),
            "markdown": _artifact_ref(tmp_path / "baseline_truth_audit.md", "# audit\n"),
            "plot_dir": str(plot_dir),
        },
        "family_dispositions": [
            {
                "target_label": "ISTD-A",
                "feature_family_id": "ISTD-A::100.0::1.20",
                "covered_samples": ["sample_001"],
                "dominant_classification": "linear_edge_over_subtraction_plausible",
                "review_status": "reviewed",
                "decision_scope": "C1B_RELEVANCE",
                "plot_path": str(plot_path),
                "reviewed_rows": [
                    {
                        "target_label": "ISTD-A",
                        "feature_family_id": "ISTD-A::100.0::1.20",
                        "sample_stem": "sample_001",
                        "peak_start_rt": "1.10",
                        "apex_rt": "1.20",
                        "peak_end_rt": "1.30",
                        "plot_path": str(plot_path),
                    }
                ],
                "family_disposition": family_disposition,
                "tier_c_row_blockers": blockers,
                "reviewer_disposition": "AsLS baseline is more plausible than linear edge.",
                "reason": "Linear edge crosses the peak shoulder on the linked plot.",
            }
        ],
        "affected_outputs": ["alignment_matrix.tsv"],
        "blank_control_evidence_status": blank_safety_status,
        "blank_control_evidence_refs": blank_refs,
        "blank_rows_absence_proof": blank_absence_proof,
        "consumer_contract_tests": contract_tests,
        "stress_axis_dispositions": [
            {
                "stress_axis": "blank_carryover",
                "status": "NOT_REQUIRED",
                "decision_scope": "RETIREMENT_ONLY",
                "rationale": "Scoped outputs do not consume blank quantitation.",
                "evidence_artifacts": [],
            }
        ],
        "row_count": 1,
        "sample_count": 1,
        "raw_file_count": 1,
        "selected_istd_count": 1,
        "high_risk_morphology_row_count": 1,
        "covered_target_classes": ["ISTD"],
        "known_exclusions": [],
        "reviewer_or_generator": "methodology_owner",
        "output_scope": ["alignment_matrix.tsv"],
        "target_classes": ["ISTD"],
    }
```

- [x] **Step 2: Replace old Tier C axis tests**

Remove tests whose names or fixture payloads use these old axes:

```text
spike_in_recovery
linearity
blank_carryover
blinded_manual_integration
real_85raw_cohort
```

Add these tests in the same section:

```python
def test_validate_tier_c_baseline_audit_passes_with_reviewed_linear_edge_support(
    tmp_path: Path,
) -> None:
    path = _write_json(tmp_path / "tier_c.json", _tier_c_baseline_evidence(tmp_path))

    result = validate_tier_c(path)

    assert result.status == PASS
    assert result.baseline_evidence_status == PASS
    assert result.blank_safety_status == NOT_APPLICABLE_WITH_EXCLUSION
    assert result.axis == "asls_vs_linear_edge_baseline_audit"
    assert result.row_blocker_count == 0
    assert result.review_required_count == 0
    assert result.stress_axis_disposition_statuses == ("blank_carryover=NOT_REQUIRED",)


def test_validate_tier_c_rejects_fixed_ratio_threshold_authority(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    data["ratio_metrics_are_descriptive"] = False
    data["fixed_area_uplift_threshold"] = 1.25
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "ratio_metrics_are_descriptive" in result.reasons[0]


def test_validate_tier_c_review_required_does_not_roll_up_to_pass(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        _tier_c_baseline_evidence(
            tmp_path,
            baseline_status=NOT_PROVIDED,
            tier_c_status="MIXED",
            family_disposition="REQUIRES_REVIEW",
            row_blockers=["mixed_or_review_required"],
        ),
    )

    result = validate_tier_c(path)

    assert result.status == "MIXED"
    assert result.baseline_evidence_status == NOT_PROVIDED
    assert result.row_blocker_count == 1
    assert result.review_required_count == 1


def test_validate_tier_c_hard_asls_blocker_fails_baseline_evidence(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        _tier_c_baseline_evidence(
            tmp_path,
            baseline_status=FAIL,
            tier_c_status=FAIL,
            family_disposition="FAIL",
            row_blockers=["asls_area_exceeds_raw_area"],
        ),
    )

    result = validate_tier_c(path)

    assert result.status == FAIL
    assert result.baseline_evidence_status == FAIL
    assert result.row_blocker_count == 1


def test_validate_tier_c_rejects_manual_truth_comparator_axis(tmp_path: Path) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    data["tier_c_axis"] = "blinded_manual_integration"
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "unsupported tier_c_axis" in result.reasons[0]


def test_validate_tier_c_blank_exclusion_requires_contract_tests(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    data["consumer_contract_tests"] = []
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "consumer_contract_tests" in result.reasons[0]


def test_validate_tier_c_blank_pass_requires_blank_evidence_refs(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(
        tmp_path,
        blank_safety_status=PASS,
    )
    data["blank_control_evidence_refs"] = []
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "blank_control_evidence_refs" in result.reasons[0]


def test_validate_tier_c_rejects_malformed_baseline_rows_artifact(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    rows_ref = data["baseline_truth_artifacts"]["rows_tsv"]
    rows_path = Path(rows_ref["path"])
    rows_ref["sha256"] = _artifact_ref(rows_path, "target_label\nISTD-A\n")["sha256"]
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "baseline rows fieldnames" in result.reasons[0]


def test_validate_tier_c_rejects_baseline_rows_with_unexpected_column(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    rows_ref = data["baseline_truth_artifacts"]["rows_tsv"]
    rows_path = Path(rows_ref["path"])
    bad_rows = rows_path.read_text(encoding="utf-8").replace(
        "plot_path\n",
        "plot_path\tunexpected_column\n",
    )
    rows_ref["sha256"] = _artifact_ref(rows_path, bad_rows)["sha256"]
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "baseline rows fieldnames" in result.reasons[0]


def test_validate_tier_c_rejects_family_disposition_without_row_link(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    data["family_dispositions"][0]["reviewed_rows"][0]["sample_stem"] = "missing_sample"
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "reviewed row not found" in result.reasons[0]


def test_validate_tier_c_inconclusive_family_is_invalid_input(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(
        tmp_path,
        baseline_status=NOT_PROVIDED,
        tier_c_status="MIXED",
        family_disposition="INCONCLUSIVE",
    )
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "family_disposition=INCONCLUSIVE" in result.reasons[0]


def test_validate_tier_c_empty_stress_axis_is_not_retirement_ready(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    data["stress_axis_dispositions"] = []
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == "MIXED"
    assert result.stress_axis_gate_status == NOT_PROVIDED
```

- [x] **Step 3: Update waiver tests**

In waiver fixture payloads, replace:

```python
"waived_tier_c_axes": ["spike_in_recovery"],
```

with:

```python
"waived_tier_c_evidence": ["asls_vs_linear_edge_baseline_audit"],
```

Replace the success assertion:

```python
assert result.nonblank_tier_c_status == NOT_PROVIDED
```

with:

```python
assert result.baseline_evidence_status == NOT_PROVIDED
```

- [x] **Step 4: Run input tests and confirm failure**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_asls_truth_validation_inputs.py -q
```

Expected before implementation:

```text
FAILED
```

The first failures should mention missing `baseline_evidence_status`, unsupported new field names, or stale waiver field names.

## Task 3: Implement Tier C Baseline Evidence Validator

**Files:**

- Modify: `tools/diagnostics/asls_truth_validation_inputs.py`
- Test: `tests/test_asls_truth_validation_inputs.py`

- [x] **Step 1: Import model constants and update supported axes**

In `tools/diagnostics/asls_truth_validation_inputs.py`, extend the import from `tools.diagnostics.asls_truth_validation_models`:

```python
    FAMILY_DISPOSITION_FAIL,
    FAMILY_DISPOSITION_INCONCLUSIVE,
    FAMILY_DISPOSITION_PASS_BASELINE_SUPPORTED,
    FAMILY_DISPOSITION_PASS_METHODS_SIMILAR,
    FAMILY_DISPOSITION_REQUIRES_REVIEW,
    FAMILY_DISPOSITIONS,
    TIER_C_AXIS_BASELINE_AUDIT,
    TIER_C_GATE_FAIL,
    TIER_C_GATE_NOT_PROVIDED,
    TIER_C_GATE_PASS,
    TIER_C_ROW_BLOCKERS,
```

Replace `_SUPPORTED_TIER_C_AXES` with:

```python
_SUPPORTED_TIER_C_AXES = {TIER_C_AXIS_BASELINE_AUDIT}
```

Replace `_WAIVER_REQUIRED_FIELDS` entry `"waived_tier_c_axes"` with:

```python
    "waived_tier_c_evidence",
```

Replace `_WAIVER_NON_EMPTY_LIST_FIELDS` entry `"waived_tier_c_axes"` with:

```python
    "waived_tier_c_evidence",
```

- [x] **Step 2: Update result dataclasses**

Replace `TierCValidationResult` and `WaiverValidationResult` with:

```python
@dataclass(frozen=True)
class TierCValidationResult:
    status: str
    baseline_evidence_status: str
    c1b_relevance_status: str
    blank_safety_status: str
    stress_axis_gate_status: str
    axis: str
    reasons: tuple[str, ...]
    stress_axis_disposition_statuses: tuple[str, ...] = ()
    row_blocker_count: int = 0
    review_required_count: int = 0


@dataclass(frozen=True)
class WaiverValidationResult:
    status: str
    waiver_state: str
    baseline_evidence_status: str
    reasons: tuple[str, ...]
```

- [x] **Step 3: Add Tier C helper functions**

Add these helpers above `validate_tier_c`:

```python
_BASELINE_ROWS_COLUMNS = (
    "target_label",
    "feature_family_id",
    "sample_stem",
    "status",
    "raw_area",
    "linear_area",
    "asls_area",
    "linear_raw_pct",
    "asls_raw_pct",
    "asls_vs_linear_pct",
    "linear_baseline_subtracted_pct",
    "asls_baseline_subtracted_pct",
    "linear_edge_delta_pct",
    "outside_background_pct",
    "peak_start_rt",
    "apex_rt",
    "peak_end_rt",
    "trace_point_count",
    "classification",
    "review_reason",
    "plot_path",
)

_BASELINE_SUMMARY_COLUMNS = (
    "target_label",
    "feature_family_id",
    "row_count",
    "dominant_classification",
    "classification_counts",
    "median_linear_baseline_subtracted_pct",
    "median_asls_baseline_subtracted_pct",
    "median_asls_vs_linear_pct",
    "max_asls_vs_linear_pct",
    "median_linear_edge_delta_pct",
    "median_outside_background_pct",
    "review_status",
    "plot_path",
)


def _read_tabular_artifact(
    path: Path,
    expected_fieldnames: tuple[str, ...],
    label: str,
) -> list[dict[str, str]]:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if tuple(reader.fieldnames or ()) != expected_fieldnames:
            raise ValueError(f"{label} fieldnames do not match expected schema")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{label} must contain at least one data row")
    for index, row in enumerate(rows, start=2):
        if row.get(None):
            raise ValueError(f"{label} row {index} has unexpected extra cells")
        for column in expected_fieldnames:
            if row.get(column) in {None, ""}:
                raise ValueError(f"{label} row {index} has empty {column}")
    return rows


def _validate_baseline_truth_artifacts(
    data: dict[str, Any],
    *,
    base_path: Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    artifacts = data.get("baseline_truth_artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("baseline_truth_artifacts must be an object")
    rows_path = _validate_ref(artifacts.get("rows_tsv"), base_path=base_path)
    summary_path = _validate_ref(artifacts.get("summary_tsv"), base_path=base_path)
    json_path = _validate_ref(artifacts.get("json"), base_path=base_path)
    _validate_ref(artifacts.get("markdown"), base_path=base_path)
    plot_dir_raw = artifacts.get("plot_dir")
    if not isinstance(plot_dir_raw, str) or not plot_dir_raw:
        raise ValueError("baseline_truth_artifacts.plot_dir must be a non-empty string")
    plot_dir = _resolve_ref_path(plot_dir_raw, base_path)
    if not plot_dir.is_dir():
        raise ValueError(f"baseline_truth_artifacts.plot_dir does not exist: {plot_dir}")
    rows = _read_tabular_artifact(rows_path, _BASELINE_ROWS_COLUMNS, "baseline rows")
    summaries = _read_tabular_artifact(
        summary_path,
        _BASELINE_SUMMARY_COLUMNS,
        "baseline summary",
    )
    json_object = load_json_object(json_path)
    families = json_object.get("families")
    if not isinstance(families, list) or not families:
        raise ValueError("baseline JSON families must be a non-empty list")
    summary_keys = {
        (
            row["target_label"],
            row["feature_family_id"],
            row["dominant_classification"],
        )
        for row in summaries
    }
    for family in families:
        if not isinstance(family, dict):
            raise ValueError("baseline JSON families entries must be objects")
        family_key = (
            _text(family, "target_label"),
            _text(family, "feature_family_id"),
            _text(family, "dominant_classification"),
        )
        if family_key not in summary_keys:
            raise ValueError("baseline JSON family not found in baseline summary")
        json_plot_path = _resolve_ref_path(_text(family, "plot_path"), base_path)
        if not json_plot_path.exists():
            raise ValueError(f"baseline JSON plot_path does not exist: {json_plot_path}")
    return rows, summaries


def _validate_tier_c_metadata(data: dict[str, Any], *, base_path: Path) -> None:
    if data.get("ratio_metrics_are_descriptive") is not True:
        raise ValueError("ratio_metrics_are_descriptive must be true")
    if data.get("fixed_area_uplift_threshold") is not None:
        raise ValueError("fixed_area_uplift_threshold must be null")
    for key in ("affected_outputs", "covered_target_classes", "output_scope", "target_classes"):
        _require_non_empty_list(data, key)
    for key in (
        "row_count",
        "sample_count",
        "raw_file_count",
        "selected_istd_count",
        "high_risk_morphology_row_count",
    ):
        _require_min(data, key, 1)
    _text(data, "reviewer_or_generator")
    exclusions = data.get("known_exclusions")
    if not isinstance(exclusions, list):
        raise ValueError("known_exclusions must be a list")
```

Replace the current `_validate_tier_c_metadata` function at the bottom of the file with the same implementation so there is only one definition.

- [x] **Step 4: Add family-disposition rollup helper**

Add this helper above `validate_tier_c`:

```python
def _roll_up_family_dispositions(
    data: dict[str, Any],
    *,
    base_path: Path,
    rows: list[dict[str, str]],
    summaries: list[dict[str, str]],
) -> tuple[str, str, int, int]:
    families = data.get("family_dispositions")
    if not isinstance(families, list) or not families:
        raise ValueError("family_dispositions must be a non-empty list")

    row_keys = {
        (
            row["target_label"],
            row["feature_family_id"],
            row["sample_stem"],
            row["peak_start_rt"],
            row["apex_rt"],
            row["peak_end_rt"],
        )
        for row in rows
    }
    summary_keys = {
        (
            row["target_label"],
            row["feature_family_id"],
            row["dominant_classification"],
        )
        for row in summaries
    }
    artifact_blockers = {
        "missing_or_stale_plot",
        "missing_row_identifier",
        "stale_artifact_hash",
        "unsupported_classification",
    }
    hard_asls_blockers = {
        "asls_under_subtraction_plausible",
        "asls_area_exceeds_raw_area",
        "asls_negative_nonblank_area",
    }
    review_blockers = {"mixed_or_review_required", "not_assessable"}
    has_baseline_supported = False
    has_fail = False
    has_c1b_family = False
    c1b_fail = False
    review_required_count = 0
    row_blocker_count = 0

    for family in families:
        if not isinstance(family, dict):
            raise ValueError("family_dispositions entries must be objects")
        for key in (
            "target_label",
            "feature_family_id",
            "dominant_classification",
            "review_status",
            "decision_scope",
            "plot_path",
            "family_disposition",
            "reviewer_disposition",
            "reason",
        ):
            _text(family, key)
        covered_samples = _require_non_empty_list(family, "covered_samples")
        if any(not isinstance(item, str) or not item for item in covered_samples):
            raise ValueError("covered_samples must contain non-empty strings")
        disposition = _text(family, "family_disposition")
        if disposition not in FAMILY_DISPOSITIONS:
            raise ValueError(f"unsupported family_disposition {disposition!r}")
        if disposition == FAMILY_DISPOSITION_INCONCLUSIVE:
            raise ValueError("family_disposition=INCONCLUSIVE requires regenerated evidence")
        decision_scope = _text(family, "decision_scope")
        if decision_scope not in {DECISION_SCOPE_C1B, DECISION_SCOPE_RETIREMENT}:
            raise ValueError("unsupported family decision_scope")
        if decision_scope == DECISION_SCOPE_C1B:
            has_c1b_family = True
        blockers = family.get("tier_c_row_blockers")
        if not isinstance(blockers, list):
            raise ValueError("tier_c_row_blockers must be a list")
        for blocker in blockers:
            if not isinstance(blocker, str) or blocker not in TIER_C_ROW_BLOCKERS:
                raise ValueError(f"unsupported tier_c_row_blocker {blocker!r}")
        if any(blocker in artifact_blockers for blocker in blockers):
            raise ValueError("artifact or row-link blocker requires regenerated evidence")
        row_blocker_count += len(blockers)

        plot_path = _resolve_ref_path(_text(family, "plot_path"), base_path)
        if not plot_path.exists():
            raise ValueError(f"family plot_path does not exist: {plot_path}")
        family_summary_key = (
            _text(family, "target_label"),
            _text(family, "feature_family_id"),
            _text(family, "dominant_classification"),
        )
        if family_summary_key not in summary_keys:
            raise ValueError("family disposition not found in baseline summary")
        reviewed_rows = family.get("reviewed_rows")
        if not isinstance(reviewed_rows, list) or not reviewed_rows:
            raise ValueError("reviewed_rows must be a non-empty list")
        for reviewed_row in reviewed_rows:
            if not isinstance(reviewed_row, dict):
                raise ValueError("reviewed_rows entries must be objects")
            reviewed_key = (
                _text(reviewed_row, "target_label"),
                _text(reviewed_row, "feature_family_id"),
                _text(reviewed_row, "sample_stem"),
                _text(reviewed_row, "peak_start_rt"),
                _text(reviewed_row, "apex_rt"),
                _text(reviewed_row, "peak_end_rt"),
            )
            if reviewed_key not in row_keys:
                raise ValueError("reviewed row not found in baseline rows")
            reviewed_plot = _resolve_ref_path(_text(reviewed_row, "plot_path"), base_path)
            if not reviewed_plot.exists():
                raise ValueError(f"reviewed row plot_path does not exist: {reviewed_plot}")

        if disposition == FAMILY_DISPOSITION_PASS_BASELINE_SUPPORTED:
            has_baseline_supported = True
        elif disposition == FAMILY_DISPOSITION_REQUIRES_REVIEW or any(
            blocker in review_blockers for blocker in blockers
        ):
            review_required_count += 1
        elif disposition == FAMILY_DISPOSITION_FAIL or any(
            blocker in hard_asls_blockers for blocker in blockers
        ):
            has_fail = True
            if decision_scope == DECISION_SCOPE_C1B:
                c1b_fail = True

    c1b_status = FAIL if c1b_fail else (PASS if has_c1b_family else NOT_PROVIDED)
    if has_fail:
        return FAIL, c1b_status, row_blocker_count, review_required_count
    if review_required_count:
        return NOT_PROVIDED, c1b_status, row_blocker_count, review_required_count
    if not has_baseline_supported:
        return NOT_PROVIDED, c1b_status, row_blocker_count, review_required_count
    return PASS, c1b_status, row_blocker_count, review_required_count
```

- [x] **Step 5: Replace blank-safety helper**

Replace `_validate_blank_safety` with:

```python
def _validate_blank_safety(data: dict[str, Any], *, base_path: Path) -> str:
    blank = _text(data, "blank_safety_status")
    if blank not in {PASS, FAIL, NOT_PROVIDED, NOT_APPLICABLE_WITH_EXCLUSION}:
        raise ValueError(
            "blank_safety_status must be PASS, FAIL, NOT_PROVIDED, "
            "or NOT_APPLICABLE_WITH_EXCLUSION"
        )
    blank_control = _text(data, "blank_control_evidence_status")
    if blank_control not in {PASS, FAIL, NOT_PROVIDED, NOT_APPLICABLE_WITH_EXCLUSION}:
        raise ValueError(
            "blank_control_evidence_status must be PASS, FAIL, NOT_PROVIDED, "
            "or NOT_APPLICABLE_WITH_EXCLUSION"
        )
    if blank == NOT_APPLICABLE_WITH_EXCLUSION:
        if blank_control != NOT_APPLICABLE_WITH_EXCLUSION:
            raise ValueError(
                "blank_control_evidence_status must match NOT_APPLICABLE_WITH_EXCLUSION"
            )
        _require_non_empty_list(data, "affected_outputs")
        _require_non_empty_list(data, "blank_rows_absence_proof")
        for ref in _require_non_empty_list(data, "consumer_contract_tests"):
            _validate_ref(ref, base_path=base_path)
    elif blank == PASS:
        if blank_control != PASS:
            raise ValueError("blank_control_evidence_status must be PASS")
        for ref in _require_non_empty_list(data, "blank_control_evidence_refs"):
            _validate_ref(ref, base_path=base_path)
    elif blank == FAIL:
        if blank_control != FAIL:
            raise ValueError("blank_control_evidence_status must be FAIL")
    return blank
```

Replace `_validate_stress_axis_dispositions` with:

```python
def _validate_stress_axis_dispositions(
    data: dict[str, Any],
    *,
    base_path: Path,
) -> tuple[tuple[str, ...], str]:
    dispositions = data.get("stress_axis_dispositions", [])
    if not isinstance(dispositions, list):
        raise ValueError("stress_axis_dispositions must be a list")
    if not dispositions:
        return (), NOT_PROVIDED
    statuses: list[str] = []
    has_fail = False
    has_missing = False
    for disposition in dispositions:
        if not isinstance(disposition, dict):
            raise ValueError("stress_axis_dispositions entries must be objects")
        stress_axis = _text(disposition, "stress_axis")
        status = _text(disposition, "status")
        if status not in {PASS, FAIL, "NOT_REQUIRED", NOT_PROVIDED}:
            raise ValueError("unsupported stress_axis disposition status")
        scope = _text(disposition, "decision_scope")
        if scope not in {DECISION_SCOPE_C1B, DECISION_SCOPE_RETIREMENT}:
            raise ValueError("unsupported stress_axis decision_scope")
        if status == "NOT_REQUIRED":
            _text(disposition, "rationale")
        if status == FAIL:
            has_fail = True
        if status == NOT_PROVIDED:
            has_missing = True
        evidence_artifacts = (
            _require_non_empty_list(disposition, "evidence_artifacts")
            if status == PASS
            else disposition.get("evidence_artifacts", [])
        )
        for ref in evidence_artifacts:
            _validate_ref(ref, base_path=base_path)
        statuses.append(f"{stress_axis}={status}")
    if has_fail:
        return tuple(statuses), FAIL
    if has_missing:
        return tuple(statuses), NOT_PROVIDED
    return tuple(statuses), PASS
```

- [x] **Step 6: Replace `validate_tier_c`**

Replace the body of `validate_tier_c` with:

```python
def validate_tier_c(path: Path | None) -> TierCValidationResult:
    if path is None:
        return TierCValidationResult(
            NOT_PROVIDED,
            NOT_PROVIDED,
            NOT_PROVIDED,
            NOT_PROVIDED,
            NOT_PROVIDED,
            "",
            (),
        )
    try:
        data = load_json_object(path)
        axis = _text(data, "tier_c_axis")
        if axis not in _SUPPORTED_TIER_C_AXES:
            raise ValueError(f"unsupported tier_c_axis {axis!r}")
        status = _text(data, "tier_c_status")
        if status not in {PASS, FAIL, NOT_PROVIDED, "MIXED"}:
            raise ValueError("tier_c_status must be PASS, FAIL, MIXED, or NOT_PROVIDED")
        baseline_status = _text(data, "tier_c_baseline_evidence_status")
        if baseline_status not in {PASS, FAIL, NOT_PROVIDED}:
            raise ValueError(
                "tier_c_baseline_evidence_status must be PASS, FAIL, or NOT_PROVIDED"
            )
        if status == NOT_PROVIDED:
            return TierCValidationResult(
                NOT_PROVIDED,
                NOT_PROVIDED,
                NOT_PROVIDED,
                NOT_PROVIDED,
                NOT_PROVIDED,
                axis,
                (),
            )

        rows, summaries = _validate_baseline_truth_artifacts(data, base_path=path)
        _validate_tier_c_metadata(data, base_path=path)
        blank = _validate_blank_safety(data, base_path=path)
        stress_statuses, stress_gate_status = _validate_stress_axis_dispositions(
            data,
            base_path=path,
        )
        (
            rolled_baseline,
            c1b_relevance_status,
            row_blockers,
            review_required,
        ) = _roll_up_family_dispositions(
            data,
            base_path=path,
            rows=rows,
            summaries=summaries,
        )

        if baseline_status == PASS and rolled_baseline != PASS:
            raise ValueError("tier_c_baseline_evidence_status=PASS conflicts with family_dispositions")
        if baseline_status == FAIL and rolled_baseline != FAIL:
            raise ValueError("tier_c_baseline_evidence_status=FAIL conflicts with family_dispositions")
        if baseline_status == NOT_PROVIDED and rolled_baseline == PASS:
            raise ValueError("tier_c_baseline_evidence_status=NOT_PROVIDED conflicts with family_dispositions")

        effective_baseline = rolled_baseline
        effective_status = status
        if effective_baseline == FAIL or blank == FAIL:
            effective_status = FAIL
        elif review_required:
            effective_status = "MIXED"
        elif effective_baseline == PASS and status != FAIL:
            effective_status = PASS

        return TierCValidationResult(
            effective_status,
            effective_baseline,
            c1b_relevance_status,
            blank,
            stress_gate_status,
            axis,
            (),
            stress_axis_disposition_statuses=stress_statuses,
            row_blocker_count=row_blockers,
            review_required_count=review_required,
        )
    except (OSError, TypeError, ValueError) as exc:
        return TierCValidationResult(
            INCONCLUSIVE_INVALID_INPUT,
            NOT_PROVIDED,
            NOT_PROVIDED,
            NOT_PROVIDED,
            NOT_PROVIDED,
            "",
            (str(exc),),
        )
```

- [x] **Step 7: Update waiver validation field names**

In `validate_waiver`, replace the waived-axis block with:

```python
        waived_evidence = set(_require_non_empty_list(data, "waived_tier_c_evidence"))
        unsupported_evidence = waived_evidence - _SUPPORTED_TIER_C_AXES
        if unsupported_evidence:
            raise ValueError(
                f"unsupported waived_tier_c_evidence {sorted(unsupported_evidence)!r}"
            )
```

Keep the success return as:

```python
    return WaiverValidationResult(PASS, VALID, NOT_PROVIDED, ())
```

- [x] **Step 8: Run input tests and confirm pass**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_asls_truth_validation_inputs.py -q
```

Expected:

```text
passed
```

## Task 4: Update Gate Decision Logic

**Files:**

- Modify: `tests/test_asls_truth_validation_analysis.py`
- Modify: `tools/diagnostics/asls_truth_validation_analysis.py`

- [x] **Step 1: Update analysis tests to use baseline evidence, C1b relevance, and stress gate status**

In `tests/test_asls_truth_validation_analysis.py`, replace every keyword argument:

```python
tier_c_nonblank_status=
```

with:

```python
tier_c_baseline_evidence_status=
```

Remove the `tier_c_nonblank_decision_scope` argument from tests. Add explicit
`tier_c_c1b_relevance_status` and `tier_c_stress_axis_gate_status` where a test
needs to distinguish C1b planning from retirement authority.

Update the `_decide` helper defaults at the bottom of the test file to include:

```python
        "tier_c_baseline_evidence_status": NOT_PROVIDED,
        "tier_c_c1b_relevance_status": NOT_PROVIDED,
        "tier_c_stress_axis_gate_status": NOT_PROVIDED,
```

and remove:

```python
        "tier_c_nonblank_status": NOT_PROVIDED,
        "tier_c_nonblank_decision_scope": "C1B_RELEVANCE",
```

Rename the test `test_blank_only_tier_c_still_requires_nonblank_tier_c` to:

```python
def test_retirement_requires_baseline_evidence_not_only_blank_safety() -> None:
```

Its assertion stays:

```python
assert result == GATE_REQUIRES_TIER_C
```

- [x] **Step 2: Add review-required, C1b relevance, and stress-axis gate tests**

Add these tests near the other Tier C gate tests:

```python
def test_valid_but_unresolved_tier_c_review_requires_tier_c() -> None:
    result = _decide(
        decision_target="linear-edge-retirement",
        tier_b2_status=PASS,
        tier_c_status="MIXED",
        tier_c_baseline_evidence_status=NOT_PROVIDED,
        tier_c_c1b_relevance_status=PASS,
        tier_c_stress_axis_gate_status=PASS,
        blank_safety_status=NOT_APPLICABLE_WITH_EXCLUSION,
        retirement_prereq_status=VALID,
    )

    assert result == GATE_REQUIRES_TIER_C
    assert exit_code_for_gate(result) == 3


def test_c1b_plan_allows_retirement_only_tier_c_fail() -> None:
    result = _decide(
        decision_target="c1b-plan",
        tier_c_status=FAIL,
        tier_c_baseline_evidence_status=FAIL,
        tier_c_c1b_relevance_status=PASS,
    )

    assert result == GATE_C1B_PLAN


def test_c1b_plan_blocks_b1_relevance_tier_c_fail() -> None:
    result = _decide(
        decision_target="c1b-plan",
        tier_c_status=FAIL,
        tier_c_baseline_evidence_status=FAIL,
        tier_c_c1b_relevance_status=FAIL,
    )

    assert result == GATE_NO_GO


def test_retirement_requires_resolved_tier_c_stress_axis() -> None:
    result = _decide(
        decision_target="linear-edge-retirement",
        tier_b2_status=PASS,
        tier_c_status=PASS,
        tier_c_baseline_evidence_status=PASS,
        tier_c_c1b_relevance_status=PASS,
        tier_c_stress_axis_gate_status=NOT_PROVIDED,
        blank_safety_status=NOT_APPLICABLE_WITH_EXCLUSION,
        retirement_prereq_status=VALID,
    )

    assert result == GATE_REQUIRES_TIER_C
```

- [x] **Step 3: Run analysis tests and confirm failure**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_asls_truth_validation_analysis.py -q
```

Expected before implementation:

```text
FAILED
```

The failure should be an unexpected keyword argument for `tier_c_baseline_evidence_status`.

- [x] **Step 4: Replace gate signature and logic**

In `tools/diagnostics/asls_truth_validation_analysis.py`, remove `_C1B_RELEVANCE`.

Change the `decide_gate` signature from:

```python
    tier_c_nonblank_status: str,
    tier_c_nonblank_decision_scope: str = _C1B_RELEVANCE,
```

to:

```python
    tier_c_baseline_evidence_status: str,
    tier_c_c1b_relevance_status: str,
    tier_c_stress_axis_gate_status: str,
```

In the `statuses` list, replace `tier_c_nonblank_status` with:

```python
        tier_c_baseline_evidence_status,
        tier_c_c1b_relevance_status,
        tier_c_stress_axis_gate_status,
```

Replace the old Tier C failure branch with:

```python
    if tier_c_c1b_relevance_status == _FAIL:
        return GATE_NO_GO
    if (
        decision_target == "linear-edge-retirement"
        and tier_c_baseline_evidence_status == _FAIL
    ):
        return GATE_NO_GO
```

In the retirement branch, replace:

```python
        if tier_c_nonblank_status != _PASS:
            return GATE_REQUIRES_TIER_C
```

with:

```python
        if tier_b2_status == _STRESS_REQUIRES_TIER_C or b2_retirement_blockers:
            if tier_c_stress_axis_gate_status == _FAIL:
                return GATE_NO_GO
            if tier_c_stress_axis_gate_status != _PASS:
                return GATE_REQUIRES_TIER_C
        elif tier_b2_status != _PASS:
            return GATE_REQUIRES_TIER_C
        if tier_c_baseline_evidence_status != _PASS:
            return GATE_REQUIRES_TIER_C
        if tier_c_stress_axis_gate_status == _FAIL:
            return GATE_NO_GO
        if tier_c_stress_axis_gate_status != _PASS:
            return GATE_REQUIRES_TIER_C
```

- [x] **Step 5: Run analysis tests and confirm pass**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_asls_truth_validation_analysis.py -q
```

Expected:

```text
passed
```

## Task 5: Update CLI Summary And Optional Evidence Handling

**Files:**

- Modify: `tests/test_asls_truth_validation_cli.py`
- Modify: `tools/diagnostics/asls_truth_validation.py`

- [x] **Step 1: Update CLI helper evidence payload**

In `tests/test_asls_truth_validation_cli.py`, update `_write_tier_c` so it writes baseline-evidence Tier C JSON. Use this payload structure inside the helper:

```python
    plot_dir = path.parent / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    plot_path = plot_dir / "ISTD-A.png"
    plot_path.write_text("plot\n", encoding="utf-8")
    contract_ref = _hashed_artifact(path.parent / "contract_test.txt", "pass\n")
    payload = {
        "tier_c_axis": "asls_vs_linear_edge_baseline_audit",
        "tier_c_status": "PASS",
        "tier_c_baseline_evidence_status": "PASS",
        "blank_safety_status": "NOT_APPLICABLE_WITH_EXCLUSION",
        "ratio_metrics_are_descriptive": True,
        "fixed_area_uplift_threshold": None,
        "baseline_truth_artifacts": {
            "rows_tsv": _hashed_artifact(
                path.parent / "rows.tsv",
                _tier_c_rows_text(plot_path),
            ),
            "summary_tsv": _hashed_artifact(
                path.parent / "summary.tsv",
                _tier_c_summary_text(plot_path),
            ),
            "json": _hashed_artifact(
                path.parent / "audit.json",
                _tier_c_audit_json_text(plot_path),
            ),
            "markdown": _hashed_artifact(path.parent / "audit.md", "# audit\n"),
            "plot_dir": str(plot_dir),
        },
        "family_dispositions": [
            {
                "target_label": "ISTD-A",
                "feature_family_id": "ISTD-A::100.0::1.20",
                "covered_samples": ["sample_001"],
                "dominant_classification": "linear_edge_over_subtraction_plausible",
                "review_status": "reviewed",
                "decision_scope": "C1B_RELEVANCE",
                "plot_path": str(plot_path),
                "reviewed_rows": [
                    {
                        "target_label": "ISTD-A",
                        "feature_family_id": "ISTD-A::100.0::1.20",
                        "sample_stem": "sample_001",
                        "peak_start_rt": "1.10",
                        "apex_rt": "1.20",
                        "peak_end_rt": "1.30",
                        "plot_path": str(plot_path),
                    }
                ],
                "family_disposition": "PASS_BASELINE_SUPPORTED",
                "tier_c_row_blockers": [],
                "reviewer_disposition": "AsLS baseline is more plausible than linear edge.",
                "reason": "Linear edge crosses the shoulder.",
            }
        ],
        "affected_outputs": ["alignment_matrix.tsv"],
        "blank_control_evidence_status": "NOT_APPLICABLE_WITH_EXCLUSION",
        "blank_control_evidence_refs": [],
        "blank_rows_absence_proof": ["alignment_matrix.tsv excludes blank quantitation"],
        "consumer_contract_tests": [contract_ref],
        "stress_axis_dispositions": [
            {
                "stress_axis": "blank_carryover",
                "status": "NOT_REQUIRED",
                "decision_scope": "RETIREMENT_ONLY",
                "rationale": "Scoped outputs do not consume blank quantitation.",
                "evidence_artifacts": [],
            }
        ],
        "row_count": 1,
        "sample_count": 1,
        "raw_file_count": 1,
        "selected_istd_count": 1,
        "high_risk_morphology_row_count": 1,
        "covered_target_classes": ["ISTD"],
        "known_exclusions": [],
        "reviewer_or_generator": "methodology_owner",
        "output_scope": ["alignment_matrix.tsv"],
        "target_classes": ["ISTD"],
    }
```

If the file does not already have a helper for hashed test artifacts, add:

```python
def _hashed_artifact(path: Path, text: str) -> dict[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {"path": str(path), "sha256": sha256_file(path)}


def _tier_c_rows_text(plot_path: Path) -> str:
    return (
        "target_label\tfeature_family_id\tsample_stem\tstatus\traw_area\tlinear_area\t"
        "asls_area\tlinear_raw_pct\tasls_raw_pct\tasls_vs_linear_pct\t"
        "linear_baseline_subtracted_pct\tasls_baseline_subtracted_pct\t"
        "linear_edge_delta_pct\toutside_background_pct\tpeak_start_rt\tapex_rt\t"
        "peak_end_rt\ttrace_point_count\tclassification\treview_reason\tplot_path\n"
        "ISTD-A\tISTD-A::100.0::1.20\tsample_001\tPASS\t100.0\t60.0\t95.0\t"
        "60.0\t95.0\t58.3\t40.0\t5.0\t35.0\t20.0\t1.10\t1.20\t1.30\t"
        f"11\tlinear_edge_over_subtraction_plausible\tlinear edge crosses shoulder\t{plot_path}\n"
    )


def _tier_c_summary_text(plot_path: Path) -> str:
    return (
        "target_label\tfeature_family_id\trow_count\tdominant_classification\t"
        "classification_counts\tmedian_linear_baseline_subtracted_pct\t"
        "median_asls_baseline_subtracted_pct\tmedian_asls_vs_linear_pct\t"
        "max_asls_vs_linear_pct\tmedian_linear_edge_delta_pct\t"
        "median_outside_background_pct\treview_status\tplot_path\n"
        "ISTD-A\tISTD-A::100.0::1.20\t1\tlinear_edge_over_subtraction_plausible\t"
        "{\"linear_edge_over_subtraction_plausible\": 1}\t40.0\t5.0\t58.3\t"
        f"58.3\t35.0\t20.0\treviewed\t{plot_path}\n"
    )


def _tier_c_audit_json_text(plot_path: Path) -> str:
    return json.dumps(
        {
            "families": [
                {
                    "target_label": "ISTD-A",
                    "feature_family_id": "ISTD-A::100.0::1.20",
                    "dominant_classification": "linear_edge_over_subtraction_plausible",
                    "plot_path": str(plot_path),
                }
            ]
        }
    )
```

- [x] **Step 2: Update CLI assertions**

In `test_cli_copies_optional_evidence_when_supplied`, replace:

```python
assert summary["tier_c_axis"] == "spike_in_recovery"
```

with:

```python
assert summary["tier_c_axis"] == "asls_vs_linear_edge_baseline_audit"
assert summary["tier_c_baseline_evidence_status"] == "PASS"
assert summary["tier_c_c1b_relevance_status"] == "PASS"
assert summary["tier_c_stress_axis_gate_status"] == "PASS"
assert summary["tier_c_row_blocker_count"] == "0"
assert summary["tier_c_review_required_count"] == "0"
```

Replace the payload axis assertion with:

```python
assert (
    payload["inputs"]["tier_c_evidence"]["object"]["tier_c_axis"]
    == "asls_vs_linear_edge_baseline_audit"
)
```

Add this stale-field assertion:

```python
assert "tier_c_nonblank_status" not in summary
```

Update `_write_waiver` payloads to use:

```python
"waived_tier_c_evidence": ["asls_vs_linear_edge_baseline_audit"],
```

- [x] **Step 3: Run CLI tests and confirm failure**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_asls_truth_validation_cli.py -q
```

Expected before implementation:

```text
FAILED
```

The failure should mention `nonblank_status`, `tier_c_nonblank_status`, or stale summary fields.

- [x] **Step 4: Update CLI orchestration call**

In `tools/diagnostics/asls_truth_validation.py`, change the `decide_gate` call to pass:

```python
        tier_c_baseline_evidence_status=tier_c.baseline_evidence_status,
        tier_c_c1b_relevance_status=tier_c.c1b_relevance_status,
        tier_c_stress_axis_gate_status=tier_c.stress_axis_gate_status,
```

and remove:

```python
        tier_c_nonblank_status=tier_c.nonblank_status,
        tier_c_nonblank_decision_scope=tier_c.nonblank_decision_scope,
```

Change the `_summary_row` call to pass:

```python
        tier_c_baseline_evidence_status=tier_c.baseline_evidence_status,
        tier_c_c1b_relevance_status=tier_c.c1b_relevance_status,
        tier_c_stress_axis_gate_status=tier_c.stress_axis_gate_status,
        tier_c_row_blocker_count=tier_c.row_blocker_count,
        tier_c_review_required_count=tier_c.review_required_count,
```

and remove:

```python
        tier_c_nonblank_status=tier_c.nonblank_status,
```

- [x] **Step 5: Update `_summary_row` signature and output keys**

In `_summary_row`, replace the parameter:

```python
    tier_c_nonblank_status: str,
```

with:

```python
    tier_c_baseline_evidence_status: str,
    tier_c_c1b_relevance_status: str,
    tier_c_stress_axis_gate_status: str,
    tier_c_row_blocker_count: int,
    tier_c_review_required_count: int,
```

In the returned dict, replace:

```python
        "tier_c_nonblank_status": tier_c_nonblank_status,
```

with:

```python
        "tier_c_baseline_evidence_status": tier_c_baseline_evidence_status,
        "tier_c_c1b_relevance_status": tier_c_c1b_relevance_status,
        "tier_c_stress_axis_gate_status": tier_c_stress_axis_gate_status,
        "tier_c_row_blocker_count": tier_c_row_blocker_count,
        "tier_c_review_required_count": tier_c_review_required_count,
```

- [x] **Step 6: Update fallback summary defaults**

In `_fallback_summary`, replace:

```python
            "tier_c_nonblank_status": NOT_PROVIDED,
```

with:

```python
            "tier_c_baseline_evidence_status": NOT_PROVIDED,
            "tier_c_c1b_relevance_status": NOT_PROVIDED,
            "tier_c_stress_axis_gate_status": NOT_PROVIDED,
            "tier_c_row_blocker_count": 0,
            "tier_c_review_required_count": 0,
```

- [x] **Step 7: Run CLI tests and confirm pass**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_asls_truth_validation_cli.py -q
```

Expected:

```text
passed
```

## Task 6: Remove Stale Tier C Schema References

**Files:**

- Modify: `tools/diagnostics/asls_truth_validation_models.py`
- Modify: `tools/diagnostics/asls_truth_validation_inputs.py`
- Modify: `tools/diagnostics/asls_truth_validation_analysis.py`
- Modify: `tools/diagnostics/asls_truth_validation.py`
- Modify: `tests/test_asls_truth_validation_models.py`
- Modify: `tests/test_asls_truth_validation_inputs.py`
- Modify: `tests/test_asls_truth_validation_analysis.py`
- Modify: `tests/test_asls_truth_validation_cli.py`

- [x] **Step 1: Search implementation and tests for stale fields**

Run:

```powershell
rg -n "tier_c_nonblank_status|nonblank_status|nonblank_decision_scope|nonblank_tier_c_status|waived_tier_c_axes|spike_in_recovery|linearity|blinded_manual_integration|real_85raw_cohort|quantitative_truth_comparator_type" -g "asls_truth_validation*.py" -g "test_asls_truth_validation*.py" tools\diagnostics tests
```

Expected after implementation:

```text
no matches
```

- [x] **Step 2: Search for manual truth-comparison wording**

Run:

```powershell
rg -n "manual-vs-AsLS|AsLS-vs-manual|blinded manual|spike-in recovery|concentration-series linearity|quantitative truth comparator" -g "asls_truth_validation*.py" -g "test_asls_truth_validation*.py" tools\diagnostics tests
```

Expected after implementation:

```text
no matches
```

- [x] **Step 3: Fix remaining matches**

For each stale match:

- In implementation files, replace the stale contract with `tier_c_baseline_evidence_status` or `asls_vs_linear_edge_baseline_audit`.
- In test files, replace old comparator fixtures with `_tier_c_baseline_evidence`.
- Do not edit specs in this task unless a code/test requirement contradicts the reviewed spec.

- [x] **Step 4: Re-run stale-field searches**

Run both `rg` commands from Steps 1 and 2 again.

Expected:

```text
no matches
```

## Task 7: Focused Verification

**Files:**

- Verify all files changed in Tasks 1 through 6.

- [x] **Step 1: Compile changed implementation files**

Run:

```powershell
python -m py_compile tools\diagnostics\asls_truth_validation_models.py tools\diagnostics\asls_truth_validation_inputs.py tools\diagnostics\asls_truth_validation_analysis.py tools\diagnostics\asls_truth_validation.py
```

Expected:

```text
no output and exit code 0
```

- [x] **Step 2: Run focused test group**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_asls_truth_validation_models.py tests\test_asls_truth_validation_inputs.py tests\test_asls_truth_validation_analysis.py tests\test_asls_truth_validation_cli.py -q
```

Expected:

```text
passed
```

- [x] **Step 3: Run ruff on changed files**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\asls_truth_validation_models.py tools\diagnostics\asls_truth_validation_inputs.py tools\diagnostics\asls_truth_validation_analysis.py tools\diagnostics\asls_truth_validation.py tests\test_asls_truth_validation_models.py tests\test_asls_truth_validation_inputs.py tests\test_asls_truth_validation_analysis.py tests\test_asls_truth_validation_cli.py
```

Expected:

```text
All checks passed!
```

- [x] **Step 4: Run mypy on changed implementation files**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\asls_truth_validation_models.py tools\diagnostics\asls_truth_validation_inputs.py tools\diagnostics\asls_truth_validation_analysis.py tools\diagnostics\asls_truth_validation.py
```

Expected:

```text
Success: no issues found
```

- [x] **Step 5: Check whitespace and conflict markers**

Run:

```powershell
git diff --check
```

Expected:

```text
no whitespace errors
```

If this command prints only CRLF normalization warnings, record them in the final handoff and do not change unrelated line endings.

- [x] **Step 6: Review final diff**

Run:

```powershell
git diff -- tools\diagnostics\asls_truth_validation_models.py tools\diagnostics\asls_truth_validation_inputs.py tools\diagnostics\asls_truth_validation_analysis.py tools\diagnostics\asls_truth_validation.py tests\test_asls_truth_validation_models.py tests\test_asls_truth_validation_inputs.py tests\test_asls_truth_validation_analysis.py tests\test_asls_truth_validation_cli.py
```

Expected review points:

- `linear_edge` appears only as the comparator in `asls_vs_linear_edge_baseline_audit`, not as a truth method scheduled for deletion in this slice.
- No manual-integration, spike-in, or concentration-series comparator remains in the active Tier C validator.
- `GO_FOR_LINEAR_EDGE_RETIREMENT` requires `tier_c_baseline_evidence_status=PASS`.
- `decision_target=c1b-plan` is blocked only by `tier_c_c1b_relevance_status=FAIL`, not by retirement-only Tier C gaps.
- `tier_c_stress_axis_gate_status=PASS` is required for retirement and `NOT_PROVIDED` stays `REQUIRES_TIER_C`.
- B2 stress blockers are not permanent retirement blockers after
  `tier_c_stress_axis_gate_status=PASS`; they advance to retirement
  prerequisite validation.
- `REQUIRES_REVIEW` family dispositions cannot roll up to `PASS`.
- Family dispositions link to hashed baseline rows/summary and include sample/RT/window row identifiers.
- Fallback summaries use the new Tier C fields.
- Optional evidence JSON is copied unchanged to the output directory.

## Task 8: Handoff Note

**Files:**

- No source file changes in this task.

- [x] **Step 1: Prepare final implementation handoff**

Use this structure:

```text
Verdict: implemented Tier C AsLS-vs-linear-edge baseline evidence gate.

Changed files:
- tools/diagnostics/asls_truth_validation_models.py
- tools/diagnostics/asls_truth_validation_inputs.py
- tools/diagnostics/asls_truth_validation_analysis.py
- tools/diagnostics/asls_truth_validation.py
- tests/test_asls_truth_validation_models.py
- tests/test_asls_truth_validation_inputs.py
- tests/test_asls_truth_validation_analysis.py
- tests/test_asls_truth_validation_cli.py

Verification:
- python -m py_compile tools\diagnostics\asls_truth_validation_models.py tools\diagnostics\asls_truth_validation_inputs.py tools\diagnostics\asls_truth_validation_analysis.py tools\diagnostics\asls_truth_validation.py
- uv run pytest tests\test_asls_truth_validation_models.py tests\test_asls_truth_validation_inputs.py tests\test_asls_truth_validation_analysis.py tests\test_asls_truth_validation_cli.py -q
- uv run ruff check tools\diagnostics\asls_truth_validation_models.py tools\diagnostics\asls_truth_validation_inputs.py tools\diagnostics\asls_truth_validation_analysis.py tools\diagnostics\asls_truth_validation.py tests\test_asls_truth_validation_models.py tests\test_asls_truth_validation_inputs.py tests\test_asls_truth_validation_analysis.py tests\test_asls_truth_validation_cli.py
- uv run mypy tools\diagnostics\asls_truth_validation_models.py tools\diagnostics\asls_truth_validation_inputs.py tools\diagnostics\asls_truth_validation_analysis.py tools\diagnostics\asls_truth_validation.py
- git diff --check

Remaining risk:
- This is diagnostic schema/gate implementation only.
- Real Tier C cohort generation and RAW-backed evidence remain outside this slice.
- Linear-edge production retirement remains blocked until C1a, C5, rollback-column deprecation, and passing Tier C/prereq evidence are all supplied.
- This diagnostic can reject malformed or stale evidence, but it cannot judge human plot-review quality without a real cohort artifact.
```

## Self-Review Checklist

- Spec coverage:
  - Tier C accepted axis is `asls_vs_linear_edge_baseline_audit`: Task 3.
  - Ratio metrics are descriptive only: Task 3.
  - No fixed area uplift threshold: Task 3.
  - Family dispositions and row blockers are closed enums: Task 1 and Task 3.
  - `REQUIRES_REVIEW` cannot roll up to `PASS`: Task 2 and Task 3.
  - `INCONCLUSIVE` or stale artifact/linkage states return `INCONCLUSIVE_INVALID_INPUT`: Task 2 and Task 3.
  - Family review records include `sample_stem` and RT/window row identifiers: Task 2 and Task 3.
  - Baseline rows/summary/JSON artifacts are schema-checked and linked to family dispositions: Task 2 and Task 3.
  - Blank/carryover exclusion requires machine-checkable proof and tests: Task 2 and Task 3.
  - Blank/carryover PASS requires hashed blank evidence refs: Task 2 and Task 3.
  - Summary fields include `tier_c_baseline_evidence_status`, C1b relevance, stress gate, blocker count, and review count: Task 1 and Task 5.
  - Retirement gate requires baseline evidence, stress safety, blank safety, and prereqs: Task 4.
- Red-flag scan:
  - The runnable plan text avoids unfinished-marker phrases and does not ask the implementer to infer missing code paths.
- Type consistency:
  - `TierCValidationResult.baseline_evidence_status`, `c1b_relevance_status`, and `stress_axis_gate_status` are used by validator, analysis, CLI summary, and tests.
  - `WaiverValidationResult.baseline_evidence_status` replaces the stale nonblank field.
  - `tier_c_row_blocker_count` and `tier_c_review_required_count` are integers in Python and serialized by the existing TSV writer.
