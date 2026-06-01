# AsLS Linear-Edge Retirement B+C Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Advance the B+C path toward linear-edge retirement by correcting the Tier C evidence contract and routing baseline-corrected integration callers through the single selector entry, without deleting linear-edge yet.

**Architecture:** B is an evidence gate: `p2_baseline_truth_audit` compares AsLS against linear-edge on the same trace and boundary and uses linked baseline plots as the objective review surface. C is a cleanup prerequisite: production and audit surfaces that need baseline-corrected integration should call `integrate_with_baseline`, while `integrate_linear_edge_baseline` remains available only as a legacy implementation behind the selector and for diagnostics/tests. C1b deletion remains out of scope until the evidence gate, C5, C1a, and rollback-column deprecation prerequisites are satisfied.

**Tech Stack:** Python 3, NumPy, pytest, ruff, mypy, PowerShell, existing XIC diagnostic TSV/Markdown/plot artifacts.

---

## Scope

Now:

- Correct P2c/C1b wording so Tier C compares AsLS to linear-edge, not manual integration.
- Keep `asls_vs_linear_pct` and subtraction metrics as descriptive context, not fixed uplift thresholds.
- Route C5 production/audit callers through `integrate_with_baseline`.
- Preserve final `Area`, `alignment_matrix.tsv`, and rollback/comparator surfaces.

Not in scope:

- Deleting `integrate_linear_edge_baseline`.
- Removing `integrate_with_baseline`.
- Removing `area_baseline_corrected_linear_edge` or `baseline_score_linear_edge`.
- Claiming AsLS is an absolute manual-truth equivalent.
- Running a new 8RAW/85RAW validation unless requested or required by a later gate.

## File Map

- Modify: `docs/superpowers/specs/2026-05-26-peak-pipeline-asls-truth-validation-spec.md`
  - Owns the Tier C evidence contract and final `GO_FOR_LINEAR_EDGE_RETIREMENT` semantics.
- Modify: `docs/superpowers/specs/2026-05-24-peak-pipeline-cleanup-linear-edge-retirement-spec.md`
  - Owns C1b deletion prerequisites and must point at baseline-truth plots, not manual/spike-in comparators.
- Modify: `xic_extractor/peak_detection/baseline.py`
  - Keep legacy functions, but extend `integrate_with_baseline` so it can reuse precomputed AsLS baseline/noise context.
- Modify: `xic_extractor/peak_detection/integration_audit.py`
  - Produce AsLS primary and linear-edge rollback/comparator values through `integrate_with_baseline`.
- Modify: `xic_extractor/peak_detection/hypotheses.py`
  - Build `IntegrationResult.baseline_type` and baseline-corrected area from `config.baseline_integration_method`.
- Modify: `xic_extractor/extraction/peak_candidate_boundaries.py`
  - Score boundary rows with the configured baseline method.
- Modify: `xic_extractor/peak_detection/region_safe_merge.py`
  - Score region-first boundary candidates with the configured baseline method.
- Modify: `xic_extractor/peak_detection/facade.py`
  - Pass the config method into region-first safe merge.
- Modify: `xic_extractor/extraction/peak_candidate_table.py`
  - Pass the config method into hypothesis construction.
- Modify tests:
  - `tests/test_baseline_integration.py`
  - `tests/test_peak_hypotheses.py`
  - `tests/test_peak_candidate_boundaries.py`
  - `tests/test_peak_candidate_table.py`

## Task 1: Correct The Retirement Evidence Contract

- [x] **Step 1: Update P2c decision wording**

Change `GO_FOR_LINEAR_EDGE_RETIREMENT` required evidence to:

```text
Tier A guard + Tier B1 pass + Tier B2 stress safety disposition +
Tier C AsLS-vs-linear-edge baseline evidence + blank/carryover safety
disposition or exclusion + retirement prerequisite manifest
```

Expected checks:

```powershell
rg -n "manual-vs-AsLS|spike-in recovery|concentration-series|fixed area uplift|nonblank Tier C quantitative" docs\superpowers\specs\2026-05-26-peak-pipeline-asls-truth-validation-spec.md
```

Expected: no remaining retirement-gate requirement that makes manual, spike-in, concentration, or fixed uplift ratio the comparator.

- [x] **Step 2: Replace Tier C section with baseline-audit semantics**

The replacement section must say:

```text
Tier C comparator is linear-edge on the same trace and boundary.
p2_baseline_truth_audit rows, summary, JSON, Markdown, and plots are the primary evidence.
ratio_metrics_are_descriptive=true and fixed_area_uplift_threshold=null are required.
```

Expected checks:

```powershell
rg -n "asls_vs_linear_edge_baseline_audit|ratio_metrics_are_descriptive|fixed_area_uplift_threshold|p2_baseline_truth_audit" docs\superpowers\specs\2026-05-26-peak-pipeline-asls-truth-validation-spec.md
```

Expected: all four terms appear in the Tier C contract.

- [x] **Step 3: Update C1b prerequisite wording**

`docs/superpowers/specs/2026-05-24-peak-pipeline-cleanup-linear-edge-retirement-spec.md` must say linear-edge deletion requires the baseline-truth audit evidence gate plus blank/carryover safety or exclusion, not manual integration or fixed area uplift.

Expected check:

```powershell
rg -n "p2_baseline_truth_audit|manual integration as the comparator|fixed area-uplift" docs\superpowers\specs\2026-05-24-peak-pipeline-cleanup-linear-edge-retirement-spec.md
```

Expected: all three terms appear in the corrected blocker paragraph.

## Task 2: Close The C5 Integration-Audit Selector Gap

- [x] **Step 1: Add selector reuse coverage**

Add this behavior to `tests/test_baseline_integration.py`:

```python
def test_integrate_with_baseline_reuses_precomputed_asls_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4])
    intensity = np.asarray([10.0, 25.0, 50.0, 35.0, 20.0])
    baseline = np.full_like(intensity, 10.0)

    def _unexpected_asls(*_args: object, **_kwargs: object) -> np.ndarray:
        raise AssertionError("precomputed baseline should be reused")

    monkeypatch.setattr(
        "xic_extractor.peak_detection.baseline.asls_baseline",
        _unexpected_asls,
    )

    result = integrate_with_baseline(
        intensity,
        rt,
        0,
        5,
        baseline_method="asls",
        baseline_values=baseline,
    )

    assert result.baseline_type == "asls"
    assert result.area_baseline_corrected == pytest.approx(510.0)
```

- [x] **Step 2: Extend `integrate_with_baseline` without changing defaults**

Add optional keyword parameters:

```python
baseline_values: np.ndarray | None = None
uncertainty_baseline_values: np.ndarray | None = None
baseline_residual_mad: float | None = None
baseline_residual_mad_source: str = "asls_residual"
```

Linear-edge dispatch passes noise context to `integrate_linear_edge_baseline`.
AsLS dispatch passes `baseline_values` to `integrate_asls_baseline`.

- [x] **Step 3: Route `integration_audit.py` through the selector**

Replace direct imports of `integrate_linear_edge_baseline` and
`integrate_asls_baseline` with `integrate_with_baseline`. The linear-edge
rollback value still exists, but the production/audit caller no longer reaches
the legacy function directly.

- [x] **Step 4: Add direct-caller guard**

Add a package-level test that scans `xic_extractor/**/*.py`, excluding
`xic_extractor/peak_detection/baseline.py`, and asserts no production module
contains `integrate_linear_edge_baseline`.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_baseline_integration.py -q
```

Expected: pass.

## Task 3: Preserve Config-Driven Baseline Choice Across Evidence Surfaces

- [x] **Step 1: Hypothesis integration**

`build_peak_hypotheses` accepts `baseline_integration_method: BaselineMethod = "asls"` and passes it into `_integration_from_candidate`.

Focused test:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_peak_hypotheses.py::test_build_peak_hypotheses_can_use_linear_edge_baseline_override -q
```

Expected: the override row has `baseline_type == "linear_edge"`.

- [x] **Step 2: Boundary rows**

`build_peak_candidate_boundary_rows` and
`build_peak_candidate_boundary_rows_from_hypotheses` accept
`baseline_integration_method` and pass it into `_row_from_boundary`.

Focused test:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_peak_candidate_boundaries.py -q
```

Expected: default rows use `baseline_type == "asls"` and no boundary audit schema columns disappear.

- [x] **Step 3: Region-first safe merge**

`apply_region_first_safe_merge` and `scored_region_boundaries_for_candidates`
accept `baseline_integration_method`, and the facade passes
`config.baseline_integration_method`.

Focused test:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_region_safe_merge.py tests\test_signal_processing.py -q
```

Expected: existing safe-merge and signal-processing behavior remains green.

- [x] **Step 4: Candidate table plumbing**

`build_peak_candidate_audit_hypotheses` passes
`config.baseline_integration_method` to hypothesis construction.

Focused test:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_peak_candidate_table.py -q
```

Expected: candidate table audit tests pass and preserve existing public schema.

## Task 4: Verification

- [x] **Step 1: Compile changed modules**

```powershell
python -m py_compile xic_extractor\peak_detection\baseline.py xic_extractor\peak_detection\integration_audit.py xic_extractor\peak_detection\hypotheses.py xic_extractor\extraction\peak_candidate_boundaries.py xic_extractor\peak_detection\region_safe_merge.py xic_extractor\peak_detection\facade.py xic_extractor\extraction\peak_candidate_table.py
```

Expected: no output and exit code 0.

- [x] **Step 2: Run focused tests**

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_baseline_integration.py tests\test_peak_hypotheses.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_table.py tests\test_peak_candidate_audit.py tests\test_region_safe_merge.py tests\test_signal_processing.py tests\test_cwt_proposals.py tests\test_result_assembly.py tests\test_csv_writers.py tests\test_alignment_matrix.py tests\test_alignment_cell_quality.py tests\test_alignment_production_decisions.py -q
```

Expected: pass. Existing SciPy `PeakPropertyWarning` warnings from CWT proposal fixtures are acceptable if unchanged.

- [x] **Step 3: Run lint/type checks on touched source and tests**

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\peak_detection\baseline.py xic_extractor\peak_detection\integration_audit.py xic_extractor\peak_detection\hypotheses.py xic_extractor\extraction\peak_candidate_boundaries.py xic_extractor\peak_detection\region_safe_merge.py xic_extractor\peak_detection\facade.py xic_extractor\extraction\peak_candidate_table.py tests\test_baseline_integration.py tests\test_peak_hypotheses.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_table.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\peak_detection\baseline.py xic_extractor\peak_detection\integration_audit.py xic_extractor\peak_detection\hypotheses.py xic_extractor\extraction\peak_candidate_boundaries.py xic_extractor\peak_detection\region_safe_merge.py xic_extractor\peak_detection\facade.py xic_extractor\extraction\peak_candidate_table.py
```

Expected: both pass.

## Task 5: Subagent Review Fixes

- [x] **Step 1: Resolve P2c stale Tier C schema**

Replace remaining `tier_c_nonblank_status` and nonblank quantitative/cohort
wording with `tier_c_baseline_evidence_status`, row blocker enums, and
family-disposition rollup semantics.

- [x] **Step 2: Preserve production handoff override behavior**

Pass `config.baseline_integration_method` from
`build_production_peak_hypotheses` into `build_peak_hypotheses`, and add a
handoff-runtime regression test proving `linear_edge` reaches the selected
hypothesis integration result.

- [x] **Step 3: Clarify diagnostic comparator callers**

Update the C1b spec so C5 owns production package caller migration, while C1b
must migrate or retire maintained diagnostic comparator callers before deleting
`integrate_linear_edge_baseline`.

## Stop Conditions

- Stop before C1b deletion if any production caller still needs direct `integrate_linear_edge_baseline`.
- Stop before claiming retirement readiness if Tier C baseline audit artifacts or plots are missing/stale.
- Stop before schema cleanup if rollback columns still lack an approved deprecation note.
- Do not commit, push, open PR, or merge unless explicitly requested by the user.
