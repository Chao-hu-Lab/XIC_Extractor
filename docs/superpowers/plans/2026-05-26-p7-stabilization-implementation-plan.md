# P7 Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize P7 so production-equivalent validation remains result-equivalent while heavy audit evidence and process-worker payloads are explicitly gated.

**Architecture:** Keep the existing full-audit rollback path, but split artifact selection from heavy audit execution. Add a resolved audit evidence mode, push owner-backfill request planning to the process-job boundary, and report P7 correctness and operations statuses separately.

**Tech Stack:** Python, pytest, PowerShell, existing alignment pipeline modules, existing P7 diagnostics.

---

## Scope

Now:

- Add an explicit resolved audit evidence mode: `none`, `full`, or `selected`.
- Make `output-level` artifact-only; it must not by itself trigger region audit, integration audit, CWT audit, AsLS, or boundary-scoring.
- In process mode, send each owner-backfill worker only the feature subset that can request that sample.
- Update P7 cost summary fields so `operations_status` cannot be mistaken for correctness parity.
- Keep `selected-families` diagnostic-only, with reproducible allowlist metadata and no production-equivalent claim.
- Keep full-audit behavior available for rollback/manual investigation.

Later:

- 85RAW re-entry after the 8RAW gate is stable and heartbeat/profile artifacts are in place.
- P8 request fusion, chromatogram cache, vectorization, or numeric hot-loop acceleration.

Not in scope:

- `.mzML` conversion or `.mzML` fallback.
- `ms1-index` equivalence claims.
- AsLS production promotion.
- Changing peak selection, RT boundary rules, or area formulas.
- Making `preconsolidate_owner_families=True` default.

## File Structure

- Modify `xic_extractor/alignment/pipeline.py`: resolve audit evidence mode and pass it to owner build/backfill paths.
- Modify `xic_extractor/alignment/pipeline_outputs.py`: add audit-mode metadata fields.
- Modify `xic_extractor/alignment/process_backend.py`: carry request-plan metadata and sample-specific feature payloads in `OwnerBackfillSampleJob`.
- Modify `xic_extractor/alignment/owner_backfill.py`: accept `audit_evidence_mode` and hard short-circuit heavy audit builders when disabled.
- Modify `xic_extractor/alignment/ownership.py`: use the same audit evidence mode for sample-local owner region audit.
- Modify `xic_extractor/alignment/backfill_scope.py`: add reusable per-sample request-plan helper.
- Modify `scripts/run_alignment.py`: add `--audit-evidence-mode {auto,none,full,selected}` and pass the resolved intent to the pipeline.
- Modify `tools/diagnostics/p7_evidence_cost_summary.py`: add explicit correctness/outcome fields.
- Update `output/phase1_p7_evidence_chain_cost_control/notes/p7_validation_decision.md`: reflect current P7 stabilization status.
- Tests:
  - `tests/test_alignment_owner_backfill.py`
  - `tests/test_alignment_ownership.py`
  - `tests/test_alignment_process_backend.py`
  - `tests/test_alignment_pipeline.py`
  - `tests/test_alignment_pipeline_outputs.py`
  - `tests/test_alignment_tsv_writer.py`
  - `tests/test_run_alignment.py`
  - `tests/test_p7_evidence_cost_summary.py`

## Task 1: Audit Evidence Mode Contract

**Files:**

- Modify: `xic_extractor/alignment/pipeline.py`
- Modify: `xic_extractor/alignment/pipeline_outputs.py`
- Modify: `xic_extractor/alignment/owner_backfill.py`
- Modify: `xic_extractor/alignment/ownership.py`
- Modify: `scripts/run_alignment.py`
- Test: listed Task 1 tests below

- [ ] **Step 1: Add failing owner-backfill audit short-circuit test**

Add to `tests/test_alignment_owner_backfill.py`:

```python
def test_owner_backfill_audit_mode_none_skips_all_heavy_audit(monkeypatch) -> None:
    source = FakeBackfillSource(
        rt=np.array([8.40, 8.49, 8.50, 8.51, 8.60]),
        intensity=np.array([0.0, 50.0, 120.0, 50.0, 0.0]),
    )
    calls = {"region": 0}

    def fail_region_audit(*args, **kwargs):
        calls["region"] += 1
        raise AssertionError("heavy audit must not run when audit_evidence_mode=none")

    monkeypatch.setattr(
        owner_backfill_module,
        "build_peak_region_audit_summary",
        fail_region_audit,
    )

    cells = build_owner_backfill_cells(
        (_feature(),),
        sample_order=("sample-a", "sample-b"),
        raw_sources={"sample-b": source},
        alignment_config=AlignmentConfig(max_rt_sec=60.0),
        peak_config=replace(_peak_config(), baseline_audit_method="asls"),
        emit_region_audit=True,
        audit_evidence_mode="none",
    )

    assert len(cells) == 1
    assert calls["region"] == 0
    assert cells[0].region_candidate_count is None
```

Run:

```powershell
python -m pytest tests\test_alignment_owner_backfill.py::test_owner_backfill_audit_mode_none_skips_all_heavy_audit -q
```

Expected: fail because `audit_evidence_mode` is not accepted yet.

- [ ] **Step 2: Add failing pipeline resolution tests**

Add to `tests/test_alignment_pipeline.py`:

```python
def test_pipeline_production_equivalent_validation_does_not_enable_heavy_audit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A", "Sample_B"))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    (raw_dir / "Sample_B.raw").write_text("raw", encoding="utf-8")
    calls = {}

    _patch_owner_pipeline_to_matrix(monkeypatch)

    def fake_owner_backfill(features, **kwargs):
        calls["emit_region_audit"] = kwargs["emit_region_audit"]
        calls["audit_evidence_mode"] = kwargs["audit_evidence_mode"]
        return ()

    monkeypatch.setattr(pipeline_module, "build_owner_backfill_cells", fake_owner_backfill)

    pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=FakeRawOpener(),
        output_level="validation",
        backfill_scope="production-equivalent",
    )

    assert calls["emit_region_audit"] is False
    assert calls["audit_evidence_mode"] == "none"
```

Also add a negative selected-mode test:

```python
def test_pipeline_rejects_selected_audit_mode_outside_selected_scope(
    tmp_path: Path,
    monkeypatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    _patch_owner_pipeline_to_matrix(monkeypatch)

    with pytest.raises(ValueError, match="selected audit evidence mode"):
        pipeline_module.run_alignment(
            discovery_batch_index=batch_index,
            raw_dir=raw_dir,
            dll_dir=tmp_path / "dll",
            output_dir=tmp_path / "out",
            alignment_config=AlignmentConfig(),
            peak_config=_peak_config(),
            raw_opener=FakeRawOpener(),
            backfill_scope="production-equivalent",
            audit_evidence_mode="selected",
        )
```

Run:

```powershell
python -m pytest tests\test_alignment_pipeline.py::test_pipeline_production_equivalent_validation_does_not_enable_heavy_audit tests\test_alignment_pipeline.py::test_pipeline_rejects_selected_audit_mode_outside_selected_scope -q
```

Expected: fail because validation output currently enables region audit through `alignment_cells.tsv`.

- [ ] **Step 3: Add failing CLI parse test**

Add to `tests/test_run_alignment.py`:

```python
def test_run_alignment_passes_audit_evidence_mode(tmp_path: Path, monkeypatch) -> None:
    batch = tmp_path / "discovery_batch_index.csv"
    batch.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    raw_dir.mkdir()
    dll_dir.mkdir()
    captured = {}

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index", str(batch),
            "--raw-dir", str(raw_dir),
            "--dll-dir", str(dll_dir),
            "--audit-evidence-mode", "none",
        ]
    )

    assert code == 0
    assert captured["audit_evidence_mode"] == "none"
```

Run:

```powershell
python -m pytest tests\test_run_alignment.py::test_run_alignment_passes_audit_evidence_mode -q
```

Expected: fail because CLI flag is missing.

- [ ] **Step 4: Add failing metadata and artifact-only writer tests**

Add to `tests/test_alignment_pipeline_outputs.py` or the existing metadata test:

```python
def test_alignment_metadata_records_audit_evidence_mode() -> None:
    metadata = alignment_metadata(
        discovery_batch_index=Path("batch.csv"),
        raw_dir=Path("raw"),
        dll_dir=Path("dll"),
        owner_backfill_xic_backend="raw",
        output_level="validation",
        peak_config=_peak_config(),
        backfill_scope="production-equivalent",
        output_scope="production-equivalent",
        audit_evidence_mode="none",
        requested_audit_evidence_mode="auto",
        heavy_audit_enabled=False,
        audit_evidence_mode_reason="production_equivalent_default_no_audit",
    )

    assert metadata["audit_evidence_mode"] == "none"
    assert metadata["requested_audit_evidence_mode"] == "auto"
    assert metadata["heavy_audit_enabled"] == "False"
    assert metadata["audit_evidence_mode_reason"] == "production_equivalent_default_no_audit"
```

Add to `tests/test_alignment_tsv_writer.py` a small writer test that constructs
one `AlignedCell` without region audit and writes `alignment_cells.tsv`.
Assert all `region_*` columns are empty while the row still exists. This proves
`alignment_cells.tsv` can be emitted as an artifact without implying heavy
region audit execution.

Run:

```powershell
python -m pytest tests\test_alignment_pipeline_outputs.py tests\test_alignment_tsv_writer.py -q
```

Expected: fail only for missing metadata parameters if no writer test helper
exists; writer behavior may already pass and should then be kept as a regression
test.

- [ ] **Step 5: Add selected-families diagnostic isolation tests**

Add a CLI or pipeline test proving:

- `--backfill-scope selected-families` requires an explicit allowlist.
- selected-family ids flow as an immutable `frozenset`.
- metadata stays `output_scope="diagnostic_only"` and keeps
  `scope_warning="diagnostic_only_incomplete_scope"`.
- `audit_evidence_mode=selected` is accepted only with
  `backfill_scope="selected-families"`.

Use the existing selected-family tests in `tests/test_run_alignment.py` as the
anchor; extend them rather than adding duplicate setup.

Run:

```powershell
python -m pytest tests\test_run_alignment.py tests\test_alignment_pipeline.py -q
```

Expected: selected-mode assertions fail until audit mode plumbing is implemented.

- [ ] **Step 6: Implement audit mode plumbing**

Implement:

- `AuditEvidenceMode = Literal["auto", "none", "full", "selected"]` in a local alignment module or directly in `pipeline.py` if no new module is needed.
- `run_alignment(..., audit_evidence_mode="auto")`.
- `_resolve_audit_evidence_mode(backfill_scope, requested_mode, outputs, peak_config)` with this behavior:
  - explicit `none` returns `none`.
  - explicit `full` returns `full`.
  - explicit `selected` returns `selected` only when `backfill_scope=="selected-families"`; otherwise raise `ValueError`.
  - `auto + full-audit` returns `full` when `outputs.cells_tsv` or `outputs.integration_audit_tsv` is requested; otherwise `none`.
  - `auto + production-equivalent` returns `full` only when `outputs.integration_audit_tsv` is requested or `peak_config.baseline_audit_method=="asls"`; otherwise `none`.
  - `auto + selected-families` returns `selected` only when `outputs.integration_audit_tsv` is requested or `peak_config.baseline_audit_method=="asls"`; otherwise `none`.
- `emit_cell_region_audit = resolved_audit_evidence_mode in {"full", "selected"}`.
- For selected mode, keep `region_audit_family_ids=selected_family_ids`.
- Pass `audit_evidence_mode=resolved_audit_evidence_mode` to owner build/backfill calls.
- Add metadata fields:
  - `audit_evidence_mode`
  - `requested_audit_evidence_mode`
  - `heavy_audit_enabled`
  - `audit_evidence_mode_reason`

- [ ] **Step 7: Implement owner/build short-circuit**

Update signatures in `owner_backfill.py` and `ownership.py` to accept `audit_evidence_mode: str = "full"` or the shared type.

Rules:

- `audit_evidence_mode=="none"` forces `emit_region_audit=False` before any trace group or region audit builder can be called.
- `audit_evidence_mode=="selected"` behaves like audit enabled but still honors `region_audit_family_ids`.
- `audit_evidence_mode=="full"` preserves legacy behavior.

Run:

```powershell
python -m pytest tests\test_alignment_owner_backfill.py tests\test_alignment_ownership.py tests\test_alignment_pipeline.py tests\test_alignment_pipeline_outputs.py tests\test_alignment_tsv_writer.py tests\test_run_alignment.py -q
```

Expected: pass.

## Task 2: Process-Worker Request-Plan Pushdown

**Files:**

- Modify: `xic_extractor/alignment/backfill_scope.py`
- Modify: `xic_extractor/alignment/process_backend.py`
- Modify: `xic_extractor/alignment/pipeline.py`
- Test: `tests/test_alignment_process_backend.py`, `tests/test_backfill_scope.py`, `tests/test_alignment_pipeline_timing.py`

- [ ] **Step 1: Add failing process job subset test**

Add to `tests/test_alignment_process_backend.py`:

```python
def test_owner_backfill_process_sends_only_sample_requested_features(tmp_path: Path) -> None:
    feature_a = replace(
        _feature(feature_family_id="FAM_A"),
        owners=(_owner("sample-a"),),
    )
    feature_b = replace(
        _feature(feature_family_id="FAM_B"),
        owners=(_owner("sample-b"),),
    )
    captured_jobs = []

    def fake_runner(jobs, *, max_workers):
        captured_jobs.extend(jobs)
        return [
            OwnerBackfillSampleResult(sample_index=1, sample_stem="sample-a", cells=()),
            OwnerBackfillSampleResult(sample_index=2, sample_stem="sample-b", cells=()),
        ]

    run_owner_backfill_process(
        (feature_a, feature_b),
        sample_order=("sample-a", "sample-b"),
        raw_paths={
            "sample-a": tmp_path / "sample-a.raw",
            "sample-b": tmp_path / "sample-b.raw",
        },
        dll_dir=tmp_path / "dll",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(tmp_path),
        max_workers=2,
        runner=fake_runner,
    )

    assert [tuple(feature.feature_family_id for feature in job.features) for job in captured_jobs] == [
        ("FAM_B",),
        ("FAM_A",),
    ]
    assert {job.request_plan_id for job in captured_jobs} == {"p7-owner-backfill-request-plan-v1"}
    assert [job.feature_payload_count for job in captured_jobs] == [1, 1]
    assert [job.feature_payload_count for job in captured_jobs] == [
        len(job.features) for job in captured_jobs
    ]
```

Run:

```powershell
python -m pytest tests\test_alignment_process_backend.py::test_owner_backfill_process_sends_only_sample_requested_features -q
```

Expected: fail because every job currently receives the full feature tuple.

- [ ] **Step 2: Add helper tests**

Add to `tests/test_backfill_scope.py`:

```python
def test_backfill_features_for_sample_matches_request_predicate() -> None:
    feature_a = _feature("FAM_A", owners=("sample-a",))
    feature_b = _feature("FAM_B", owners=("sample-b",))

    assert tuple(
        feature.feature_family_id
        for feature in backfill_features_for_sample(
            (feature_a, feature_b),
            sample_stem="sample-a",
            sample_order=("sample-a", "sample-b"),
            raw_sample_stems=frozenset({"sample-a", "sample-b"}),
            alignment_config=AlignmentConfig(),
        )
    ) == ("FAM_B",)
```

In `backfill_scope.py`, add:

```python
REQUEST_PLAN_VERSION = "p7-owner-backfill-request-plan-v1"

def backfill_features_for_sample(
    features: tuple[OwnerAlignedFeature, ...],
    *,
    sample_stem: str,
    sample_order: tuple[str, ...],
    raw_sample_stems: frozenset[str],
    alignment_config: AlignmentConfig,
) -> tuple[OwnerAlignedFeature, ...]:
    return tuple(
        feature
        for feature in features
        if sample_stem
        in backfill_request_sample_stems(
            feature,
            sample_order=sample_order,
            raw_sample_stems=raw_sample_stems,
            alignment_config=alignment_config,
        )
    )
```

Then add the test above and run:

```powershell
python -m pytest tests\test_backfill_scope.py::test_backfill_features_for_sample_matches_request_predicate -q
```

Expected: pass after the helper is added; this helper is intentionally pure and
small so the failing test for process mode remains the real request-plan guard.

- [ ] **Step 3: Use helper in process jobs**

Update `OwnerBackfillSampleJob` fields:

- `request_plan_id: str = REQUEST_PLAN_VERSION`
- `backfill_scope: str = "full-audit"`
- `audit_evidence_mode: str = "full"`
- `feature_payload_count: int = 0`

Update `run_owner_backfill_process()`:

- accept `backfill_scope` and `audit_evidence_mode`.
- compute `sample_features = backfill_features_for_sample(...)` per sample.
- skip job creation when `sample_features` is empty.
- set `feature_payload_count=len(sample_features)`.
- preserve output ordering with the full `feature_order` from the input feature tuple.

Run:

```powershell
python -m pytest tests\test_alignment_process_backend.py tests\test_backfill_scope.py -q
```

Expected: pass.

## Task 3: P7 Gate Status And Validation Notes

**Files:**

- Modify: `tools/diagnostics/p7_evidence_cost_summary.py`
- Modify: `tests/test_p7_evidence_cost_summary.py`
- Modify: `output/phase1_p7_evidence_chain_cost_control/notes/p7_validation_decision.md`
- Modify: `docs/agent-parameter-settings.md` only if a new stable command setting is needed.

- [ ] **Step 1: Add failing status field tests**

Update `tests/test_p7_evidence_cost_summary.py`:

First define the compatibility contract in test names and assertions:

- `status` is a compatibility alias for `outcome_status`.
- CLI exit code continues to report whether operations improved, not whether
  correctness parity was evaluated.
- `correctness_status`, `operations_status`, `outcome_status`, and
  `outcome_detail` must be present in JSON/TSV/Markdown output.

```python
assert result.correctness_status == "not_evaluated"
assert result.operations_status == "PASS"
assert result.outcome_status == "inconclusive"
assert result.outcome_detail == "correctness_not_evaluated"
```

For no improvement:

```python
assert result.status == result.outcome_status == "inconclusive"
assert result.operations_status == "inconclusive"
assert result.outcome_detail == "perf_stall"
```

Add four status mapping cases:

- correctness not evaluated + operations PASS -> `outcome_status="inconclusive"`, `outcome_detail="correctness_not_evaluated"`
- correctness FAIL + operations PASS -> `outcome_status="diagnostic_only"`, `outcome_detail="correctness_blocker"`
- correctness PASS + operations PASS -> `outcome_status="production_candidate"`, `outcome_detail=""`
- correctness PASS + operations inconclusive -> `outcome_status="inconclusive"`, `outcome_detail="perf_stall"`

Run:

```powershell
python -m pytest tests\test_p7_evidence_cost_summary.py -q
```

Expected: fail because fields and normalized outcome detail are missing.

- [ ] **Step 2: Implement status separation**

In `p7_evidence_cost_summary.py`:

- add result fields:
  - `correctness_status`
  - `operations_status`
  - `outcome_status`
  - `outcome_detail`
- keep `status` as a compatibility alias to `outcome_status`.
- default `correctness_status="not_evaluated"` unless the CLI later receives parity inputs.
- add optional function argument or CLI flag for correctness status only if it
  can be done without pulling parity comparison into this tool. Otherwise keep
  the four mapping tests at function-helper level and leave CLI default as
  `not_evaluated`.
- positive operations improvement sets:
  - `operations_status="PASS"`
  - `outcome_status="inconclusive"`
  - `outcome_detail="correctness_not_evaluated"`
- no operations improvement sets:
  - `operations_status="inconclusive"`
  - `outcome_status="inconclusive"`
  - `outcome_detail="perf_stall"`
- correctness failure maps to:
  - `operations_status` unchanged
  - `outcome_status="diagnostic_only"`
  - `outcome_detail="correctness_blocker"`
- correctness PASS + operations PASS maps to:
  - `outcome_status="production_candidate"`
  - `outcome_detail=""`

Do not mark the default cost summary alone as `production_candidate`; the CLI
default remains `correctness_status="not_evaluated"` unless correctness evidence
is explicitly supplied.

- [ ] **Step 3: Update validation decision note**

Update `output/phase1_p7_evidence_chain_cost_control/notes/p7_validation_decision.md`:

- Current state: `in_progress` or `inconclusive` until P7 stabilization tests pass.
- Record that pre-stabilization 85RAW remains `outcome_status=inconclusive`, `outcome_detail=timeout`.
- Record that full 85RAW must not rerun until:
  - P7 8RAW correctness parity passes.
  - operations status shows any positive resource improvement.
  - heartbeat artifact is required.
  - scoped profile sidecar exists.

Run:

```powershell
python -m pytest tests\test_p7_evidence_cost_summary.py -q
```

Expected: pass.

## Task 4: Integration Verification

**Files:**

- No new production files expected beyond Tasks 1-3.
- Update docs only if tests expose stale wording.

- [ ] **Step 1: Run py_compile**

```powershell
.venv\Scripts\python.exe -m py_compile scripts\run_alignment.py xic_extractor\alignment\pipeline.py xic_extractor\alignment\pipeline_outputs.py xic_extractor\alignment\process_backend.py xic_extractor\alignment\owner_backfill.py xic_extractor\alignment\ownership.py xic_extractor\alignment\backfill_scope.py tools\diagnostics\p7_evidence_cost_summary.py
```

Expected: exit code 0.

- [ ] **Step 2: Run focused no-RAW tests**

```powershell
python -m pytest tests\test_alignment_owner_backfill.py tests\test_alignment_ownership.py tests\test_alignment_process_backend.py tests\test_alignment_pipeline.py tests\test_alignment_pipeline_outputs.py tests\test_alignment_pipeline_timing.py tests\test_alignment_tsv_writer.py tests\test_backfill_scope.py tests\test_run_alignment.py tests\test_p7_evidence_cost_summary.py -q
```

Expected: all pass.

- [ ] **Step 3: Run broader P7-adjacent shard**

```powershell
python -m pytest tests\test_alignment_pipeline_backends.py tests\test_alignment_pipeline_outputs.py tests\test_alignment_primary_consolidation.py tests\test_alignment_process_backend.py tests\test_alignment_family_compatibility.py tests\test_compare_alignment_workbooks.py tests\test_p7_alignment_parity.py tests\test_p7_evidence_cost_summary.py -q
```

Expected: all pass.

- [ ] **Step 4: Run 8RAW validation only after no-RAW tests pass**

Use `.venv\Scripts\python.exe` and include heartbeat. Do not launch full 85RAW in this task.

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\phase1_p7_stabilization\alignment\8raw_production_equivalent `
  --output-level validation `
  --resolver-mode region_first_safe_merge `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --timing-output output\phase1_p7_stabilization\alignment\8raw_production_equivalent\timing.json `
  --timing-live-output output\phase1_p7_stabilization\alignment\8raw_production_equivalent\timing.live.json
```

Expected:

- command exits 0.
- `timing.live.json` exists while running and final `timing.json` exists after completion.
- `alignment.backfill_scope` records a positive skipped request count.
- no heavy audit hot path appears because `audit_evidence_mode=none`.

- [ ] **Step 5: Review implementation**

Request review after implementation. Required review questions:

- Does `output-level` remain artifact-only?
- Does `audit_evidence_mode=none` prevent heavy audit builder calls?
- Does process mode avoid sending every feature to every sample job?
- Are P7/P8 boundaries respected?
- Are correctness and operations status fields separated?

Fix Critical or Important findings before reporting completion.
