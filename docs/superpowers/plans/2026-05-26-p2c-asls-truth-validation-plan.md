# P2c AsLS Truth Validation Implementation Plan

**Status:** Superseded by `docs/superpowers/plans/2026-05-27-p2c-tier-b-b1-b2-redesign-plan.md`

This v1 plan is retained as historical context only. It used a single mixed
`tier_b_status` / `hard_blockers` contract and allowed no-controls blank
statements as a retirement pass. The reviewed B1/B2 redesign supersedes those
semantics.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a diagnostics-only P2c AsLS truth-validation gate that can support C1b planning without falsely authorizing linear-edge deletion.

**Architecture:** Implement the diagnostic as small `tools/diagnostics/asls_truth_validation_*` modules: schema/constants, manifest validation, synthetic benchmark generation, Tier A/Tier C/waiver/prerequisite validation, gate evaluation, and CLI output. The current implementation must be able to emit planning-only and requires-more-evidence decisions; `GO_FOR_LINEAR_EDGE_RETIREMENT` must be impossible unless nonblank Tier C quantitative/cohort evidence, blank/carryover safety disposition, and C1a/C5/rollback prerequisite manifests are valid. A waiver can document why the gate stays planning-only; it is not a retirement substitute.

**Tech Stack:** Python 3.13, pytest, NumPy, existing `tools.diagnostics.diagnostic_io`, existing `xic_extractor.peak_detection.baseline`, TSV/JSON/Markdown outputs.

---

## Scope And Non-Goals

In scope:

- `python -m tools.diagnostics.asls_truth_validation`
- locked Tier A manifest, synthetic fixture manifest, and per-row fixture lock
- manifest-driven synthetic benchmark
- Tier A same-peak/failure-mode guard
- Tier C, waiver-documentation, and prerequisite validation
- deletion-safe exit codes and machine-readable outputs

Out of scope:

- changing AsLS parameters in production
- changing final matrix output
- changing P2b rollback columns
- deleting linear-edge
- running 85RAW; this plan only validates accepted 85RAW/P2b artifact hashes when
  supplied
- committing unless the user asks

## File Structure

- Create `tools/diagnostics/asls_truth_validation_models.py`: field constants, decision constants, dataclasses, JSON loading.
- Create `tools/diagnostics/asls_truth_validation_manifests.py`: fixture manifest and Tier A manifest validation.
- Create `tools/diagnostics/asls_truth_validation_synthetic.py`: manifest-driven trace generation and area comparison.
- Create `tools/diagnostics/asls_truth_validation_inputs.py`: Tier A, Tier C, waiver, and retirement-prerequisite validation.
- Create `tools/diagnostics/asls_truth_validation_analysis.py`: coverage rows, summary rows, gate decision, exit-code mapping.
- Create `tools/diagnostics/asls_truth_validation.py`: CLI and output writer.
- Create `docs/superpowers/fixtures/asls_truth_tier_a_expected_manifest.json`.
- Create `docs/superpowers/fixtures/asls_truth_validation_fixture_manifest.json`.
- Create `docs/superpowers/fixtures/asls_truth_validation_fixture_lock.json`.
- Create tests:
  - `tests/test_asls_truth_validation_models.py`
  - `tests/test_asls_truth_validation_manifests.py`
  - `tests/test_asls_truth_validation_synthetic.py`
  - `tests/test_asls_truth_validation_inputs.py`
  - `tests/test_asls_truth_validation_analysis.py`
  - `tests/test_asls_truth_validation_cli.py`
- Modify `tools/diagnostics/INDEX.md`.
- Create closeout note after implementation:
  - `docs/superpowers/notes/2026-05-26-p2c-asls-truth-validation-implementation-note.md`.

## Task 1: Schema Constants And JSON Loading

**Files:**

- Create: `tools/diagnostics/asls_truth_validation_models.py`
- Test: `tests/test_asls_truth_validation_models.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_asls_truth_validation_models.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from tools.diagnostics.asls_truth_validation_models import (
    GATE_C1B_PLAN,
    GATE_NO_GO,
    GATE_REQUIRES_RETIREMENT_PREREQS,
    GATE_REQUIRES_TIER_C,
    GATE_RETIREMENT,
    INCONCLUSIVE_FIXTURE_LOCK_CHANGED,
    INCONCLUSIVE_INVALID_INPUT,
    INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE,
    INCONCLUSIVE_REGENERATE_TIER_A,
    ROW_FIELDS,
    SUMMARY_FIELDS,
    TruthValidationOutputs,
    load_json_object,
)


def test_gate_decisions_are_distinct() -> None:
    assert GATE_C1B_PLAN == "GO_FOR_C1B_PLAN_SYNTHETIC_ONLY"
    assert GATE_RETIREMENT == "GO_FOR_LINEAR_EDGE_RETIREMENT"
    assert GATE_REQUIRES_TIER_C == "REQUIRES_TIER_C"
    assert GATE_REQUIRES_RETIREMENT_PREREQS == "REQUIRES_RETIREMENT_PREREQS"
    assert INCONCLUSIVE_INVALID_INPUT == "INCONCLUSIVE_INVALID_INPUT"
    assert INCONCLUSIVE_REGENERATE_TIER_A == "INCONCLUSIVE_REGENERATE_TIER_A"
    assert INCONCLUSIVE_FIXTURE_LOCK_CHANGED == "INCONCLUSIVE_FIXTURE_LOCK_CHANGED"
    assert INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE == "INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE"
    assert len({GATE_C1B_PLAN, GATE_RETIREMENT, GATE_REQUIRES_TIER_C, GATE_REQUIRES_RETIREMENT_PREREQS, GATE_NO_GO, INCONCLUSIVE_INVALID_INPUT, INCONCLUSIVE_REGENERATE_TIER_A, INCONCLUSIVE_FIXTURE_LOCK_CHANGED, INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE}) == 9


def test_summary_schema_has_prereq_and_optional_evidence_fields() -> None:
    for field in (
        "decision_target",
        "fixture_lock_hash",
        "tier_a_generated_by_git_sha",
        "tier_a_current_code_compatibility_status",
        "p2b_85raw_acceptance_hash",
        "tier_c_status",
        "tier_c_nonblank_status",
        "blank_safety_status",
        "methodology_waiver_hash",
        "waiver_valid",
        "retirement_prereq_status",
        "c1a_status",
        "c5_status",
        "rollback_column_status",
    ):
        assert field in SUMMARY_FIELDS


def test_row_schema_has_error_and_blank_fields() -> None:
    for field in (
        "asls_error_over_linear_error",
        "blank_false_positive",
        "blank_not_quantifiable",
        "failure_reasons",
    ):
        assert field in ROW_FIELDS


def test_outputs_include_conditional_evidence_paths(tmp_path: Path) -> None:
    outputs = TruthValidationOutputs.from_output_dir(tmp_path)
    assert outputs.fixture_lock_json.name == "asls_truth_validation_fixture_lock.json"
    assert outputs.p2b_85raw_acceptance_json.name == "asls_truth_validation_p2b_85raw_acceptance_manifest.json"
    assert outputs.tier_c_evidence_json.name == "asls_truth_validation_tier_c_evidence.json"
    assert outputs.methodology_waiver_json.name == "asls_truth_validation_methodology_waiver.json"
    assert outputs.retirement_prereq_json.name == "asls_truth_validation_retirement_prerequisites.json"


def test_load_json_object_rejects_non_object(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(["bad"]), encoding="utf-8")

    try:
        load_json_object(path)
    except ValueError as exc:
        assert "must be a JSON object" in str(exc)
    else:
        raise AssertionError("expected ValueError")
```

- [ ] **Step 2: Run failing tests**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_asls_truth_validation_models.py -q
```

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement models**

Create `tools/diagnostics/asls_truth_validation_models.py` with constants,
fields, `TruthValidationOutputs.from_output_dir()`, and `load_json_object(path)`.
Include `fixture_lock_json`, `p2b_85raw_acceptance_json`, `tier_c_evidence_json`,
`methodology_waiver_json`, and `retirement_prereq_json` on the outputs
dataclass.

- [ ] **Step 4: Run tests**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_asls_truth_validation_models.py -q
```

Expected: PASS.

## Task 2: Locked Manifest Validation

**Files:**

- Create: `tools/diagnostics/asls_truth_validation_manifests.py`
- Create: `docs/superpowers/fixtures/asls_truth_tier_a_expected_manifest.json`
- Create: `docs/superpowers/fixtures/asls_truth_validation_fixture_manifest.json`
- Create: `docs/superpowers/fixtures/asls_truth_validation_fixture_lock.json`
- Test: `tests/test_asls_truth_validation_manifests.py`

**Hard checkpoint:** this task authors and validates manifests only. Do not
implement the synthetic generator, comparator, or gate evaluator until the
fixture manifest, fixture lock, and Tier A manifest have been reviewed and this
plan has been updated if reviewers find manifest issues. This preserves the P2c
preregistration requirement.

- [ ] **Step 1: Write failing manifest tests**

Create tests that enforce:

- Tier A manifest has exactly six expected families and 48 expected rows.
- Synthetic manifest contains all 11 fixture classes.
- Every fixture class has `minimum_heldout_replicates >= 25`.
- The fixture manifest has exactly the 11 preregistered fixture classes; extra
  or duplicate classes are invalid.
- Manifest contains `true_baseline_function`, `true_peak_function`, `parameter_grid`, `split_policy`, `expected_linear_edge_failure_mode`, `tolerance_rationale`, and the fixture-lock path/hash.
- Fixture lock contains all calibration and heldout `fixture_id` values, exact
  parameter values, split labels, strata labels, `true_area_formula_version`,
  integration bounds policy, expected bound indices, and a whole-lock hash.
- Tier A manifest contains generating command, environment profile,
  `generated_by_git_sha`, current-code compatibility rule, Tier A artifact
  hashes, and accepted P2b/85RAW primary-delivery artifact refs for retirement
  target evaluation.
- Tier A source inputs, artifact hashes, and P2b/85RAW refs must resolve on
  disk and match their recorded SHA256 values.
- Every non-blank heldout fixture class covers all nine S/N x peak-width
  combinations. Blank heldout rows cover low-noise, high-noise, sloped,
  hump-baseline, and carryover-like no-true-peak hard-case strata.
- Missing hard-case strata or tolerance rationale raises `ValueError`.

Use assertions like:

```python
assert result.fixture_version == "synthetic_truth_fixture_v1"
assert result.minimum_heldout_replicates_per_class >= 25
assert "flat_peak_control" in result.fixture_classes
assert result.tolerance_profile == "asls_truth_tolerance_v1"
assert result.fixture_lock_hash
```

- [ ] **Step 2: Run failing manifest tests**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_asls_truth_validation_manifests.py -q
```

Expected: FAIL because the module and fixture JSON files do not exist.

- [ ] **Step 3: Add fixture JSON files**

Create `docs/superpowers/fixtures/asls_truth_tier_a_expected_manifest.json` with:

- `manifest_version`;
- `expected_family_count=6`;
- `expected_row_count=48`;
- source input paths from the P2 baseline truth audit;
- generating command, environment profile, generated git SHA, and current-code
  compatibility artifact rule;
- expected Tier A rows, summary, JSON, and Markdown report paths with hashes;
- accepted P2b/85RAW primary-delivery artifact paths and hashes for retirement
  target evaluation;
- the six expected families from the P2c spec.

Create `docs/superpowers/fixtures/asls_truth_validation_fixture_manifest.json` with:

- `fixture_version=synthetic_truth_fixture_v1`;
- `tolerance_profile=asls_truth_tolerance_v1`;
- AsLS params `lam=100000.0`, `p=0.01`, `n_iter=10`;
- `generator_seed=20260526`;
- all 11 fixture classes;
- `minimum_calibration_replicates_per_class=10`;
- `minimum_heldout_replicates_per_class=25`;
- per-class true function names and expected linear-edge failure modes;
- required parameter ranges from the spec;
- `fixture_lock_path=docs/superpowers/fixtures/asls_truth_validation_fixture_lock.json`;
- `fixture_lock_hash`;
- tolerance rationale for every threshold used by the gate.

Create `docs/superpowers/fixtures/asls_truth_validation_fixture_lock.json` with
per-row locked calibration and heldout fixture records. Each record must include:

- `fixture_id`, fixture class, split, replicate id, S/N stratum, peak-width
  stratum, hard-case stratum where applicable;
- exact generator parameter values;
- true-area formula version;
- integration bounds policy and expected bound indices;
- per-row generator input hash;
- whole-lock hash.

- [ ] **Step 4: Implement manifest validators**

Implement:

```python
def load_tier_a_manifest(path: Path) -> TierAManifest: ...
def load_fixture_manifest(path: Path) -> FixtureManifest: ...
def load_fixture_lock(path: Path) -> FixtureLock: ...
```

Validators must reject any manifest that lacks the required class list, required
replicate counts, required parameter-grid keys, true function declarations,
tolerance rationale, fixture-lock hash, Tier A current-code compatibility fields,
or accepted P2b/85RAW artifact refs when retirement evaluation is requested.

- [ ] **Step 5: Run manifest tests**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_asls_truth_validation_manifests.py -q
```

Expected: PASS.

- [ ] **Step 6: Review/freeze fixture manifest before Task 3**

Run:

```powershell
git diff -- docs\superpowers\fixtures\asls_truth_validation_fixture_manifest.json docs\superpowers\fixtures\asls_truth_validation_fixture_lock.json docs\superpowers\fixtures\asls_truth_tier_a_expected_manifest.json
```

Expected: reviewer-visible manifest diff exists.

Stop after this step and request read-only review of the fixture manifest, the
fixture lock, and the Tier A manifest. Do not start Task 3 until all three are
accepted or revised.

## Task 3: Manifest-Driven Synthetic Benchmark

**Files:**

- Create: `tools/diagnostics/asls_truth_validation_synthetic.py`
- Test: `tests/test_asls_truth_validation_synthetic.py`

- [ ] **Step 1: Write failing tests**

Tests must call the generator through the loaded fixture manifest plus fixture
lock, not through ad hoc `seed/classes` or range-sampling arguments. Required
tests:

- total heldout rows are at least `11 * 25`;
- every required class has calibration and heldout rows;
- each non-blank heldout class covers low/medium/high S/N,
  narrow/typical/wide peak-width strata, and all nine S/N x peak-width
  combinations;
- generated fixture IDs exactly match the fixture lock;
- changing the fixture lock hash returns `INCONCLUSIVE_FIXTURE_LOCK_CHANGED`;
- blank `true_area == 0`;
- blank false-positive threshold uses `max(3 * area_uncertainty, 0.005 * reference_nonblank_median_true_area)`;
- comparator creates hard blocker rows when AsLS exceeds raw area or returns negative non-blank area.

- [ ] **Step 2: Run failing tests**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_asls_truth_validation_synthetic.py -q
```

Expected: FAIL because the synthetic module does not exist.

- [ ] **Step 3: Implement synthetic generator and comparator**

Implement:

- `SyntheticTrace`
- `SyntheticComparisonRow`
- `generate_synthetic_traces(manifest: FixtureManifest, lock: FixtureLock) -> tuple[SyntheticTrace, ...]`
- `compare_synthetic_trace(trace, *, asls_params, reference_nonblank_median_true_area) -> SyntheticComparisonRow`
- `blank_false_positive(...) -> bool`

Use the manifest and fixture lock only. Do not sample new heldout parameter
values during comparator implementation. Compute true area from the locked true
peak formula within locked true bounds. Compute linear-edge and AsLS areas using
existing baseline integration helpers where possible.

- [ ] **Step 4: Run synthetic tests**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_asls_truth_validation_synthetic.py -q
```

Expected: PASS.

## Task 4: Tier A Guard And Coverage Validation

**Files:**

- Create: `tools/diagnostics/asls_truth_validation_inputs.py`
- Test: `tests/test_asls_truth_validation_inputs.py`

- [ ] **Step 1: Write failing Tier A tests**

Tests must cover:

- six-family / 48-row valid Tier A passes;
- missing expected family fails;
- missing old P2 `PASS` or `FAIL` representation fails;
- `asls_raw_pct > 100.0` fails;
- summary dominated by `asls_under_subtraction_plausible` fails;
- missing required plot path fails;
- missing required column fails;
- missing `rt_identity_status` or `boundary_status` fails instead of defaulting
  to PASS;
- extra or reordered Tier A rows/summary columns fail because the locked schema
  must be exact;
- Tier A rows with overflow cells or short rows fail as malformed schema, even
  when the header itself is exact;
- invalid required numeric values in Tier A rows or summary fail as malformed
  input instead of being coerced to 0;
- source input hash mismatch fails;
- wrong RT identity status fails;
- unacceptable boundary expansion status fails;
- coverage gap produces `INCONCLUSIVE_FIXTURE_GAP`.

- [ ] **Step 2: Write failing Tier C, waiver, and prerequisite tests**

Tests must cover:

- Tier C spike-in evidence is a nonblank retirement axis and requires at least 3 levels, 5 replicates per level, and recovery 80-120%.
- Tier C linearity is a nonblank retirement axis and requires at least 5 levels, 3 replicates per level, positive slope, and R2 >= 0.98.
- Tier C blank/carryover evidence is supplemental safety evidence, not a standalone retirement axis; it requires at least 8 real blank/carryover rows and at least 95% below the spec threshold, or an explicit accepted no-controls residual-risk statement.
- Tier C blinded manual integration is a nonblank retirement axis and requires at least 30 stratified rows, median AsLS-vs-manual relative difference <= 10%, and no unreviewed row above 25%.
- Tier C real 85RAW cohort review is a nonblank retirement axis and requires raw-file count, sample count,
  selected ISTD count, high-risk morphology row count, blank/control row count,
  covered target classes, known exclusions, no unaccepted RT/boundary mismatch,
  and no AsLS raw-area exceedance.
- Unsupported `tier_c_axis` values are invalid, not silently accepted.
- `tier_c_status=NOT_PROVIDED` is a valid supplied state that means more
  evidence is required; it is not malformed input and not a pass.
- Tier C, waiver, and prerequisite evidence artifact refs resolve
  repo-relative paths from the input JSON's repository root, not from process
  cwd.
- Waiver without approved `methodology_owner`, signed/approved review artifact, blank/carryover disposition, accepted residual risks, exact output scope, or parseable expiry/revalidation trigger is invalid.
- Waiver with an expiry date on or before the review date is invalid.
- A valid waiver never satisfies `GO_FOR_LINEAR_EDGE_RETIREMENT` without nonblank Tier C evidence.
- Retirement prerequisite manifest without `c1a_status=LANDED_VALIDATED`, `c5_status=LANDED_VALIDATED`, and `rollback_column_status=DEPRECATED_BY_APPROVED_SCHEMA_NOTE` is schema-valid but not satisfied, not a scientific NO-GO.
- Waiver without exact waived decision, branch/worktree scope, target/sample classes, supporting evidence artifact hashes, and the explicit "delete only after C1a/C5/rollback deprecation" statement is invalid.
- Retirement prerequisite manifest without existing evidence artifact paths, matching evidence hashes, affected public contract review, reviewer identity, and review date is invalid.
- Retirement prerequisite manifest is invalid if the rollback schema/deprecation artifact path does not exist or its hash does not match.
- Retirement prerequisite manifest is not satisfied unless an accepted tabular
  post-rollback audit schema artifact proves
  `area_baseline_corrected_linear_edge` and `baseline_score_linear_edge` are
  absent; C1b parity-surface exclusion or an arbitrary hashed Markdown note is
  not sufficient.
- The post-rollback schema artifact must include the core alignment integration
  audit columns (`feature_family_id`, `sample_stem`, `status`, `area`,
  `apex_rt`, `peak_start_rt`, `peak_end_rt`, `area_baseline_corrected`,
  `area_uncertainty`, `baseline_type`, `baseline_score`,
  `integration_scan_count`) so a weak two-column TSV cannot stand in for the
  accepted schema.
- `post_rollback_absent_columns` must be a list of non-empty strings, not an
  object whose keys happen to name the removed columns.
- Tier A rows/summary/JSON/report hash mismatch returns `INCONCLUSIVE_REGENERATE_TIER_A`.
- Tier A generated git SHA mismatch without an accepted current-code compatibility artifact returns `INCONCLUSIVE_REGENERATE_TIER_A`.
- Missing P2b/85RAW accepted-output artifact refs for retirement-target evaluation returns `INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE`.

- [ ] **Step 3: Run failing input tests**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_asls_truth_validation_inputs.py -q
```

Expected: FAIL because the input module does not exist.

- [ ] **Step 4: Implement validators**

Implement:

- `sha256_file(path)`
- `validate_tier_a(rows_path, summary_path, json_path, report_path, manifest_path, fixture_manifest)`
- `build_coverage_rows(tier_a_summary_rows, fixture_manifest)`
- `validate_tier_c(path | None)`
- `validate_waiver(path | None)`
- `validate_retirement_prerequisites(path | None)`

Represent absent evidence, schema-valid-but-not-satisfied evidence, freshness
drift, and invalid supplied evidence separately. Invalid supplied
Tier C/waiver/prerequisite inputs return `INCONCLUSIVE_INVALID_INPUT` and exit
`2`; Tier A freshness/hash/current-code drift returns
`INCONCLUSIVE_REGENERATE_TIER_A`; fixture-lock hash drift returns
`INCONCLUSIVE_FIXTURE_LOCK_CHANGED`; missing P2b/85RAW acceptance refs return
`INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE`. None of these are scientific
`NO_GO_KEEP_LINEAR_EDGE` findings.

- [ ] **Step 5: Run input tests**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_asls_truth_validation_inputs.py -q
```

Expected: PASS.

## Task 5: Gate Evaluation And Exit Codes

**Files:**

- Create: `tools/diagnostics/asls_truth_validation_analysis.py`
- Test: `tests/test_asls_truth_validation_analysis.py`

- [ ] **Step 1: Write failing gate tests**

Required cases:

- Tier A `FAIL` returns `NO_GO_KEEP_LINEAR_EDGE`.
- Tier A `INCONCLUSIVE_*` returns that inconclusive decision.
- `exit_code_for_gate("INCONCLUSIVE_*")` returns `2`.
- Tier A PASS + Tier B PASS + `decision_target=c1b-plan` + no Tier C returns `GO_FOR_C1B_PLAN_SYNTHETIC_ONLY`, exit `3`.
- Tier A PASS + Tier B PASS + `decision_target=linear-edge-retirement` + no Tier C returns `REQUIRES_TIER_C`, exit `3`.
- Tier A PASS + Tier B `INCONCLUSIVE` returns an inconclusive decision, not planning GO.
- Tier A PASS + Tier B `NOT_PROVIDED` returns an inconclusive decision, not planning GO.
- Valid supplied `tier_c_status=FAIL` returns `NO_GO_KEEP_LINEAR_EDGE`, exit `1`, before `REQUIRES_TIER_C`.
- Invalid supplied Tier C, waiver, or prerequisite input returns `INCONCLUSIVE_INVALID_INPUT`, exit `2`.
- Valid waiver plus no nonblank Tier C returns `REQUIRES_TIER_C` for `linear-edge-retirement`.
- Blank/carryover-only Tier C returns `REQUIRES_TIER_C` for `linear-edge-retirement`.
- Nonblank Tier C PASS with missing blank/carryover safety disposition returns `REQUIRES_TIER_C`.
- Nonblank Tier C PASS plus blank/carryover safety disposition but missing or not-satisfied retirement prerequisites returns `REQUIRES_RETIREMENT_PREREQS`, exit `3`.
- Nonblank Tier C PASS plus blank/carryover safety disposition plus valid retirement prerequisites returns `GO_FOR_LINEAR_EDGE_RETIREMENT`, exit `0`.
- Tier B hard blocker returns `NO_GO_KEEP_LINEAR_EDGE`, exit `1`.

- [ ] **Step 2: Run failing gate tests**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_asls_truth_validation_analysis.py -q
```

Expected: FAIL because the analysis module does not exist.

- [ ] **Step 3: Implement gate evaluator**

Implement `decide_gate(...)` with explicit status inputs:

```python
def decide_gate(
    *,
    decision_target: str,
    tier_a_status: str,
    tier_b_status: str,
    hard_blockers: tuple[str, ...],
    coverage_status: str,
    tier_c_status: str,
    tier_c_nonblank_status: str,
    blank_safety_status: str,
    waiver_state: str,
    retirement_prereq_status: str,
) -> str:
    statuses = (
        tier_a_status,
        tier_b_status,
        coverage_status,
        tier_c_status,
        tier_c_nonblank_status,
        blank_safety_status,
        waiver_state,
        retirement_prereq_status,
    )
    if any(status.startswith("INCONCLUSIVE") for status in statuses):
        return INCONCLUSIVE_INVALID_INPUT if "INCONCLUSIVE_INVALID_INPUT" in statuses else next(status for status in statuses if status.startswith("INCONCLUSIVE"))
    if tier_a_status != "PASS":
        return GATE_NO_GO
    if coverage_status != "PASS":
        return "INCONCLUSIVE_FIXTURE_GAP"
    if hard_blockers or tier_b_status == "FAIL" or tier_c_status == "FAIL" or tier_c_nonblank_status == "FAIL" or blank_safety_status == "FAIL":
        return GATE_NO_GO
    if tier_b_status != "PASS":
        return "INCONCLUSIVE_TIER_B_NOT_PASS"
    if decision_target == "linear-edge-retirement":
        if tier_c_nonblank_status != "PASS":
            return GATE_REQUIRES_TIER_C
        if blank_safety_status not in {"PASS", "ACCEPTED_NO_CONTROLS"}:
            return GATE_REQUIRES_TIER_C
        if retirement_prereq_status != "VALID":
            return GATE_REQUIRES_RETIREMENT_PREREQS
        return GATE_RETIREMENT
    return GATE_C1B_PLAN
```

Implement `exit_code_for_gate(gate_decision)` with exit `0` reserved only for `GO_FOR_LINEAR_EDGE_RETIREMENT`.

- [ ] **Step 4: Run gate tests**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_asls_truth_validation_analysis.py -q
```

Expected: PASS.

## Task 6: CLI, Output Schemas, And Smoke Runs

**Files:**

- Create: `tools/diagnostics/asls_truth_validation.py`
- Test: `tests/test_asls_truth_validation_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Tests must verify:

- CLI writes rows, summary, coverage, JSON, copied fixture manifest, copied
  fixture lock, copied Tier A manifest, and Markdown.
- CLI copies P2b/85RAW acceptance, Tier C/waiver/prerequisite JSON only when supplied.
- `--decision-target c1b-plan` exits `3` and writes `GO_FOR_C1B_PLAN_SYNTHETIC_ONLY` when Tier A/B pass and Tier C is absent.
- `--decision-target linear-edge-retirement` exits `3` and writes `REQUIRES_TIER_C` when Tier C is absent.
- supplied invalid waiver exits `2` with `INCONCLUSIVE_INVALID_INPUT`.
- invalid Tier A input path, stale hash, schema-incompatible input, or
  `INCONCLUSIVE_*` gate exits `2`.

- [ ] **Step 2: Run failing CLI tests**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_asls_truth_validation_cli.py -q
```

Expected: FAIL because the CLI module does not exist.

- [ ] **Step 3: Implement CLI**

Implement `main(argv: Sequence[str] | None = None) -> int` with these args:

- `--tier-a-rows`
- `--tier-a-summary`
- `--tier-a-json`
- `--tier-a-report`
- `--tier-a-manifest`
- `--fixture-manifest`
- `--fixture-lock`
- `--p2b-85raw-acceptance-manifest` optional
- `--tier-c-evidence` optional
- `--methodology-waiver` optional
- `--retirement-prereq-manifest` optional
- `--decision-target`, choices `c1b-plan` and `linear-edge-retirement`
- `--output-dir`

Write all required TSV/JSON/Markdown outputs using `diagnostic_io.write_tsv`.

- [ ] **Step 4: Run CLI tests**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_asls_truth_validation_cli.py -q
```

Expected: PASS.

## Task 7: Index, Smoke Diagnostic, And Closeout

**Files:**

- Modify: `tools/diagnostics/INDEX.md`
- Create: `docs/superpowers/notes/2026-05-26-p2c-asls-truth-validation-implementation-note.md`

- [ ] **Step 1: Run all P2c tests**

```powershell
.venv\Scripts\python.exe -m pytest `
  tests\test_asls_truth_validation_models.py `
  tests\test_asls_truth_validation_manifests.py `
  tests\test_asls_truth_validation_synthetic.py `
  tests\test_asls_truth_validation_inputs.py `
  tests\test_asls_truth_validation_analysis.py `
  tests\test_asls_truth_validation_cli.py `
  -q
```

Expected: PASS.

- [ ] **Step 2: Run planning-target smoke**

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.asls_truth_validation `
  --tier-a-rows output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit_rows.tsv `
  --tier-a-summary output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit_summary.tsv `
  --tier-a-json output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit.json `
  --tier-a-report output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit.md `
  --tier-a-manifest docs\superpowers\fixtures\asls_truth_tier_a_expected_manifest.json `
  --fixture-manifest docs\superpowers\fixtures\asls_truth_validation_fixture_manifest.json `
  --fixture-lock docs\superpowers\fixtures\asls_truth_validation_fixture_lock.json `
  --decision-target c1b-plan `
  --output-dir output\phase1_p2c_asls_truth_validation\c1b_plan
```

Expected at planning time: exit `3`,
`gate_decision=GO_FOR_C1B_PLAN_SYNTHETIC_ONLY` if Tier A and Tier B pass.
If the locked Tier B benchmark exposes hard blockers, keep the diagnostic
result as `NO_GO_KEEP_LINEAR_EDGE`/exit `1` and record the blocker set in the
closeout note. Do not relax fixtures or thresholds just to force a planning GO.

- [ ] **Step 3: Run retirement-target smoke**

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.asls_truth_validation `
  --tier-a-rows output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit_rows.tsv `
  --tier-a-summary output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit_summary.tsv `
  --tier-a-json output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit.json `
  --tier-a-report output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit.md `
  --tier-a-manifest docs\superpowers\fixtures\asls_truth_tier_a_expected_manifest.json `
  --fixture-manifest docs\superpowers\fixtures\asls_truth_validation_fixture_manifest.json `
  --fixture-lock docs\superpowers\fixtures\asls_truth_validation_fixture_lock.json `
  --decision-target linear-edge-retirement `
  --output-dir output\phase1_p2c_asls_truth_validation\linear_edge_retirement
```

Expected at planning time: exit `3`, summary `gate_decision=REQUIRES_TIER_C`;
if Tier B hard blockers exist, `NO_GO_KEEP_LINEAR_EDGE`/exit `1` is the correct
deletion-safe outcome. Never
`REQUIRES_RETIREMENT_PREREQS` without passing nonblank Tier C plus
blank/carryover safety evidence, and never
`GO_FOR_LINEAR_EDGE_RETIREMENT` in this current worktree unless valid Tier
C evidence, blank/carryover safety disposition, and retirement prerequisite
manifests are explicitly supplied.

- [ ] **Step 4: Update diagnostic index**

Add an entry to `tools/diagnostics/INDEX.md`:

```markdown
| `asls_truth_validation.py` | P2c AsLS truth-validation gate with Tier A guard, locked synthetic benchmark, optional Tier C evidence, waiver documentation, retirement prerequisite manifest, and deletion-safe exit codes. | Use before C1b planning; exit `0` is reserved for true linear-edge retirement authority. |
```

- [ ] **Step 5: Write closeout note**

Create `docs/superpowers/notes/2026-05-26-p2c-asls-truth-validation-implementation-note.md` with:

- verdict and gate decisions;
- exact commands and exit codes;
- artifact paths;
- explicit statement that no linear-edge deletion happened;
- explicit statement that P2b rollback-column deprecation, C1a, and C5 still block C1b implementation unless prerequisite manifests prove otherwise.

- [ ] **Step 6: Run diff check**

```powershell
git diff --check -- `
  tools\diagnostics\asls_truth_validation*.py `
  tests\test_asls_truth_validation*.py `
  docs\superpowers\fixtures `
  docs\superpowers\notes\2026-05-26-p2c-asls-truth-validation-implementation-note.md `
  tools\diagnostics\INDEX.md
```

Expected: no whitespace errors. LF/CRLF warnings are acceptable.

## Review Gate Before Implementation

Before executing this plan:

- three read-only reviewers must review this plan;
- all blocking/high findings must be fixed;
- `git diff --check` must pass for the plan and spec docs;
- only then begin Task 1.

## Self-Review

- Spec coverage: Tier A manifest/freshness, Tier B locked manifest/heldout,
  Tier C evidence, waiver documentation, retirement prerequisites, coverage
  output, schemas, exit codes, and C1b non-deletion constraints are covered.
- Placeholder scan: no unresolved placeholders and no deletion step.
- Type consistency: exit `0` is reserved only for `GO_FOR_LINEAR_EDGE_RETIREMENT`; current worktree smoke is expected to exit `3`.
