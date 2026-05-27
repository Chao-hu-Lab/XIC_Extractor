# Evidence Chain Cost Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement P7 evidence-chain cost control so optimized alignment runs can skip provably non-production RAW/XIC and audit evidence while preserving primary matrix equivalence and leaving a row-level skipped-evidence ledger.

**Architecture:** Add a domain-layer backfill scope model, apply it before owner-centered RAW backfill, and keep full-audit behavior as the default rollback path. Selected-family mode is diagnostic-only and carries an immutable family allowlist through CLI, single-process, and process-worker paths.

**Tech Stack:** Python 3, dataclasses, argparse, csv/json sidecars, pytest, openpyxl for workbook Matrix comparison.

---

## Scope

Now:

- Add `full-audit`, `production-equivalent`, and `selected-families` backfill scope support.
- Add row-level `skipped_evidence_ledger.tsv`.
- Add metadata for backfill scope and selected-family diagnostic mode.
- Add selected-family audit gating so AsLS/region audit is computed only for selected feature families in diagnostic selected-family runs.
- Add Matrix-only alignment workbook comparison and P7 cost-summary diagnostics.
- Add unit tests and smoke commands.

Later:

- Decide whether `production-equivalent` can become the default after 8RAW A/B parity and operations gates pass.
- Expand the pre-backfill predictor only if a real-data validation note proves additional skip predicates are equivalent.

Not in scope:

- Changing AsLS promotion semantics.
- Making `preconsolidate_owner_families=True` default.
- Using `.mzML` or `ms1-index` to satisfy equivalence.
- Running full 85RAW full-audit as rollback.

## File Structure

- Create `xic_extractor/alignment/family_compatibility.py`: shared compatibility predicates currently private in `primary_consolidation.py`.
- Modify `xic_extractor/alignment/primary_consolidation.py`: import shared compatibility predicates without changing behavior.
- Create `xic_extractor/alignment/backfill_scope.py`: `BackfillScope`, selected-family allowlist parsing, request-sample helpers, scope classifier, skipped-evidence ledger writer.
- Modify `xic_extractor/alignment/owner_backfill.py`: reuse request-sample helpers and honor optional `region_audit_family_ids`.
- Modify `xic_extractor/alignment/ownership.py`: honor optional `region_audit_family_ids` during sample-local owner build.
- Modify `xic_extractor/alignment/process_backend.py`: pass `region_audit_family_ids` through owner build/backfill process jobs.
- Modify `xic_extractor/alignment/pipeline.py`: apply `select_backfill_features()` before owner backfill, write skipped ledger, record timing metrics and metadata.
- Modify `xic_extractor/alignment/pipeline_outputs.py`: add skipped ledger output path and writer.
- Modify `scripts/run_alignment.py`: add `--backfill-scope`, `--backfill-family-list-tsv`, `--backfill-family-id-column`, and repeated `--backfill-family-id`.
- Create `scripts/compare_alignment_workbooks.py`: compare only the `Matrix` sheet plus stable metadata expectations.
- Create `tools/diagnostics/p7_alignment_parity.py`: compare primary TSV values, primary identity decisions, and targeted ISTD benchmark summaries.
- Create or extend `tools/diagnostics/p7_evidence_cost_summary.py`: summarize baseline/optimized timing JSON, baseline/optimized owner-backfill economics JSON, and skipped ledger.
- Add tests:
  - `tests/test_backfill_scope.py`
  - `tests/test_alignment_family_compatibility.py`
  - extend `tests/test_alignment_owner_backfill.py`
  - extend `tests/test_alignment_pipeline.py`
  - extend `tests/test_alignment_pipeline_backends.py`
  - extend `tests/test_run_alignment.py`
  - add `tests/test_compare_alignment_workbooks.py`
  - add `tests/test_p7_alignment_parity.py`
  - add `tests/test_p7_evidence_cost_summary.py`

---

### Task 1: Shared Family Compatibility

**Files:**
- Create: `xic_extractor/alignment/family_compatibility.py`
- Modify: `xic_extractor/alignment/primary_consolidation.py`
- Test: `tests/test_alignment_family_compatibility.py`
- Existing regression: `tests/test_alignment_primary_consolidation.py`

- [ ] **Step 1: Write compatibility tests**

Add tests proving the shared predicates match the existing primary-consolidation compatibility contract:

```python
from types import SimpleNamespace

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.family_compatibility import (
    compatible_primary_family,
    loose_compatible_primary_family,
)


def _family(
    family_id: str,
    *,
    tag: str = "DNA_dR",
    mz: float = 500.0,
    rt: float = 8.5,
    product_mz: float = 384.0,
    loss: float = 116.0,
    review_only: bool = False,
):
    return SimpleNamespace(
        feature_family_id=family_id,
        neutral_loss_tag=tag,
        family_center_mz=mz,
        family_center_rt=rt,
        family_product_mz=product_mz,
        family_observed_neutral_loss_da=loss,
        review_only=review_only,
    )


def test_compatible_primary_family_rejects_review_only_and_tag_mismatch() -> None:
    config = AlignmentConfig()
    assert compatible_primary_family(_family("F1"), _family("F2"), config)
    assert not compatible_primary_family(
        _family("F1", review_only=True),
        _family("F2"),
        config,
    )
    assert not compatible_primary_family(
        _family("F1", tag="DNA_dR"),
        _family("F2", tag="RNA_R"),
        config,
    )


def test_loose_compatible_allows_product_precursor_shift() -> None:
    config = AlignmentConfig()
    left = _family("F1", mz=500.0, product_mz=384.0)
    right = _family("F2", mz=501.0, product_mz=385.0)
    assert loose_compatible_primary_family(left, right, config)


def test_loose_compatible_rejects_rt_mz_loss_and_review_only_drift() -> None:
    config = AlignmentConfig()
    base = _family("F1")
    assert not loose_compatible_primary_family(
        base,
        _family("F2", mz=base.family_center_mz + 1.0),
        config,
    )
    assert not loose_compatible_primary_family(
        base,
        _family("F2", rt=base.family_center_rt + 10.0),
        config,
    )
    assert not loose_compatible_primary_family(
        base,
        _family("F2", loss=120.0),
        config,
    )
    assert not compatible_primary_family(
        base,
        _family("F2", review_only=True),
        config,
    )
```

- [ ] **Step 2: Run the new test and verify failure**

Run:

```powershell
pytest tests\test_alignment_family_compatibility.py -q
```

Expected: fails because `xic_extractor.alignment.family_compatibility` does not exist.

- [ ] **Step 3: Create the shared compatibility module**

Move the compatibility logic from `primary_consolidation.py` into public helpers:

Implement these concrete function names with the compatibility and accessor
logic copied from the current `primary_consolidation.py` private helpers:

- `compatible_primary_family(left, right, config)`
- `loose_compatible_primary_family(left, right, config)`
- `family_center_mz(row)`
- `family_center_rt(row)`
- `family_product_mz(row)`
- `family_observed_loss(row)`

Keep the current fallback behavior: support `family_*` attributes first and `cluster_*` attributes second.

- [ ] **Step 4: Wire `primary_consolidation.py` to the shared helpers**

Replace private calls:

Replace the current private compatibility/helper call sites with the shared
helper calls listed in Step 3.

with imports from `family_compatibility.py`. Preserve private wrapper names only if needed to avoid a wide diff.

- [ ] **Step 5: Run behavior regression tests**

Run:

```powershell
pytest tests\test_alignment_family_compatibility.py tests\test_alignment_primary_consolidation.py -q
```

Expected: pass.

---

### Task 2: Backfill Scope Model And Ledger

**Files:**
- Create: `xic_extractor/alignment/backfill_scope.py`
- Test: `tests/test_backfill_scope.py`

- [ ] **Step 1: Write failing scope tests**

Add tests for the safe skip rules:

```python
from types import SimpleNamespace

from xic_extractor.alignment.backfill_scope import (
    PREDICATE_VERSION,
    BackfillScopeSelection,
    select_backfill_features,
)
from xic_extractor.alignment.config import AlignmentConfig


def _owner(sample: str):
    return SimpleNamespace(sample_stem=sample, area=100.0)


def _feature(
    family_id: str,
    *,
    owners=("S1",),
    mz: float = 500.0,
    rt: float = 8.5,
    product_mz: float = 384.0,
    review_only: bool = False,
    confirm: bool = False,
):
    return SimpleNamespace(
        feature_family_id=family_id,
        neutral_loss_tag="DNA_dR",
        family_center_mz=mz,
        family_center_rt=rt,
        family_product_mz=product_mz,
        family_observed_neutral_loss_da=116.0,
        review_only=review_only,
        confirm_local_owners_with_backfill=confirm,
        backfill_seed_centers=(),
        owners=tuple(_owner(sample) for sample in owners),
    )


def test_production_equivalent_skips_only_isolated_single_detected_family() -> None:
    result = select_backfill_features(
        (_feature("FAM001"),),
        sample_order=("S1", "S2", "S3"),
        raw_sample_stems=frozenset({"S1", "S2", "S3"}),
        alignment_config=AlignmentConfig(),
        scope="production-equivalent",
    )
    assert result.features == ()
    assert [row.sample_stem for row in result.skipped] == ["S2", "S3"]
    assert {row.skip_reason for row in result.skipped} == {
        "single_detected_no_consolidation_candidate"
    }
    assert result.skipped[0].predicate_version == PREDICATE_VERSION


def test_production_equivalent_keeps_single_detected_consolidation_candidate() -> None:
    left = _feature("FAM001", owners=("S1",), rt=8.50)
    right = _feature("FAM002", owners=("S2",), rt=8.52)
    result = select_backfill_features(
        (left, right),
        sample_order=("S1", "S2", "S3"),
        raw_sample_stems=frozenset({"S1", "S2", "S3"}),
        alignment_config=AlignmentConfig(),
        scope="production-equivalent",
    )
    assert result.features == (left, right)
    assert result.skipped == ()


def test_production_equivalent_keeps_confirmed_single_detected_family() -> None:
    feature = _feature("FAM_CONFIRM", owners=("S1",), confirm=True)
    result = select_backfill_features(
        (feature,),
        sample_order=("S1", "S2", "S3"),
        raw_sample_stems=frozenset({"S1", "S2", "S3"}),
        alignment_config=AlignmentConfig(),
        scope="production-equivalent",
    )
    assert result.features == (feature,)
    assert result.skipped == ()


def test_selected_families_is_diagnostic_and_uses_allowlist() -> None:
    kept = _feature("FAM_KEEP", owners=("S1", "S2"))
    skipped = _feature("FAM_SKIP", owners=("S1", "S2"))
    result = select_backfill_features(
        (kept, skipped),
        sample_order=("S1", "S2", "S3"),
        raw_sample_stems=frozenset({"S1", "S2", "S3"}),
        alignment_config=AlignmentConfig(),
        scope="selected-families",
        selected_family_ids=frozenset({"FAM_KEEP"}),
    )
    assert result.features == (kept,)
    assert {row.feature_family_id for row in result.skipped} == {"FAM_SKIP"}
    assert {row.skip_reason for row in result.skipped} == {
        "not_in_selected_family_allowlist"
    }


def test_full_audit_preserves_feature_tuple_and_emits_no_ledger() -> None:
    feature = _feature("FAM001", review_only=True)
    result = select_backfill_features(
        (feature,),
        sample_order=("S1", "S2"),
        raw_sample_stems=frozenset({"S1", "S2"}),
        alignment_config=AlignmentConfig(),
        scope="full-audit",
    )
    assert result.features == (feature,)
    assert result.skipped == ()
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
pytest tests\test_backfill_scope.py -q
```

Expected: import failure.

- [ ] **Step 3: Implement `backfill_scope.py`**

Implement:

```python
BackfillScope = Literal["full-audit", "production-equivalent", "selected-families"]
PREDICATE_VERSION = "p7-backfill-scope-v1"

@dataclass(frozen=True)
class SkippedEvidenceRecord:
    feature_family_id: str
    sample_stem: str
    family_center_mz: float
    family_center_rt: float
    rt_window_start: float
    rt_window_end: float
    pre_backfill_category: str
    skipped_stage: str
    skip_reason: str
    backfill_scope: BackfillScope
    predicate_version: str
    raw_xic_requests_skipped: int
    would_emit_in_full_audit: bool
    full_audit_available: bool
    source_artifact: str

@dataclass(frozen=True)
class BackfillScopeSelection:
    scope: BackfillScope
    features: Sequence[OwnerAlignedFeature]
    skipped: Sequence[SkippedEvidenceRecord]
    selected_family_ids: frozenset[str]
```

Implement helpers with these exact names and behavior:

- `backfill_seed_centers(feature)`: return `feature.backfill_seed_centers` when
  present; otherwise return one `(family_center_mz, family_center_rt)` pair.
- `backfill_request_sample_stems(feature, sample_order, raw_sample_stems,
  alignment_config)`: reproduce the legacy owner-backfill request predicate,
  including review-only, minimum detected sample count, missing RAW samples, and
  weak-detected-owner confirmation checks.
- `select_backfill_features(features, sample_order, raw_sample_stems,
  alignment_config, scope, selected_family_ids)`: return the selected feature
  tuple and row-level skipped evidence records.
- `read_family_allowlist_tsv(path, family_id_column)`: read a non-empty TSV
  allowlist and raise `ValueError` if the configured column is missing.
- `write_skipped_evidence_ledger_tsv(path, rows)`: write the exact ledger schema
  from the P7 spec.

Use `loose_compatible_primary_family()` for the single-detected consolidation-risk predicate. If any compatible non-review-only feature exists, keep the single-detected family.
If `feature.confirm_local_owners_with_backfill` is true, keep the family even
when it has one owner because detected-owner confirmation can replace a weak
local owner.

- [ ] **Step 4: Run scope tests**

Run:

```powershell
pytest tests\test_backfill_scope.py -q
```

Expected: pass.

---

### Task 3: Owner Backfill And Audit-Scope Plumbing

**Files:**
- Modify: `xic_extractor/alignment/owner_backfill.py`
- Modify: `xic_extractor/alignment/ownership.py`
- Modify: `xic_extractor/alignment/process_backend.py`
- Test: `tests/test_alignment_owner_backfill.py`
- Test: `tests/test_alignment_process_backend.py`

- [ ] **Step 1: Add failing tests for request helper reuse and selected audit scope**

Add an owner-backfill test proving non-selected feature rows do not compute region audit:

```python
def test_owner_backfill_region_audit_can_be_limited_to_selected_families(monkeypatch):
    selected = _feature("FAM_SELECTED")
    nonselected = _feature("FAM_OTHER")
    audit_calls: list[str] = []
    monkeypatch.setattr(
        owner_backfill_module,
        "build_peak_region_audit_summary",
        lambda *args, **kwargs: audit_calls.append(kwargs["trace_group"].family_id) or _audit_summary(),
    )
    cells = build_owner_backfill_cells(
        (selected, nonselected),
        sample_order=("S1", "S2"),
        raw_sources={"S1": _source(), "S2": _source()},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        emit_region_audit=True,
        region_audit_family_ids=frozenset({"FAM_SELECTED"}),
    )
    assert audit_calls == ["FAM_SELECTED"]
    assert {cell.cluster_id for cell in cells if cell.region_audit is not None} == {"FAM_SELECTED"}
```

Add process-backend tests that captured `OwnerBuildSampleJob` and `OwnerBackfillSampleJob` include `region_audit_family_ids=frozenset({"FAM001"})`.

- [ ] **Step 2: Run focused tests and verify failure**

Run:

```powershell
pytest tests\test_alignment_owner_backfill.py tests\test_alignment_process_backend.py -q
```

Expected: failures for missing keyword/job fields.

- [ ] **Step 3: Reuse `backfill_request_sample_stems()` inside owner backfill**

Replace the in-loop detected-sample skip logic in `build_owner_backfill_cells()` with:

```python
request_samples = backfill_request_sample_stems(
    feature,
    sample_order=sample_order,
    raw_sample_stems=frozenset(raw_sources),
    alignment_config=alignment_config,
)
for sample_stem in request_samples:
    for seed_mz, seed_rt in backfill_seed_centers(feature):
        request = XICRequest(
            mz=seed_mz,
            rt_min=seed_rt - rt_window_min,
            rt_max=seed_rt + rt_window_min,
            ppm_tol=alignment_config.preferred_ppm,
        )
        pending[sample_stem].append((feature, sample_stem, request, seed_rt))
```

Keep return type unchanged.

- [ ] **Step 4: Add selected audit scope**

Add optional parameters:

```python
region_audit_family_ids: frozenset[str] | None = None
```

to:

- `build_owner_backfill_cells()`
- `OwnerBackfillSampleJob`
- `run_owner_backfill_process()`
- `_owner_backfill_sample_worker()`
- `build_sample_local_owners()`
- `_resolve_candidates()`
- `OwnerBuildSampleJob`
- `run_owner_build_process()`
- `_owner_build_sample_worker()`

Use this predicate:

```python
def _emit_region_audit_for_family(enabled: bool, family_id: str, selected: frozenset[str] | None) -> bool:
    return enabled and (selected is None or family_id in selected)
```

For candidates, use `candidate.feature_family_id`. For owner-backfill features, use `feature.feature_family_id`.

- [ ] **Step 5: Run plumbing tests**

Run:

```powershell
pytest tests\test_alignment_owner_backfill.py tests\test_alignment_process_backend.py -q
```

Expected: pass.

---

### Task 4: Pipeline Output, Ledger, Metadata

**Files:**
- Modify: `xic_extractor/alignment/pipeline.py`
- Modify: `xic_extractor/alignment/pipeline_outputs.py`
- Modify: `xic_extractor/alignment/xlsx_writer.py` only if metadata escaping needs adjustment
- Test: `tests/test_alignment_pipeline.py`
- Test: `tests/test_alignment_pipeline_backends.py`
- Test: `tests/test_alignment_pipeline_outputs.py`

- [ ] **Step 1: Write failing pipeline tests**

Add tests:

```python
def test_pipeline_applies_production_equivalent_backfill_scope_and_writes_ledger(tmp_path, monkeypatch):
    # cluster returns one isolated single-detected feature
    # run_alignment is called with backfill_scope="production-equivalent".
    # assert build_owner_backfill_cells receives an empty tuple
    # assert build_owner_alignment_matrix still receives the original feature
    # assert output/skipped_evidence_ledger.tsv exists and has S2/S3 rows
```

```python
def test_pipeline_keeps_compatible_single_detected_families_for_consolidation(tmp_path, monkeypatch):
    # cluster returns two compatible single-detected features
    # run_alignment is called with backfill_scope="production-equivalent".
    # assert both features are passed to backfill
```

```python
def test_pipeline_selected_family_scope_is_diagnostic_and_sets_metadata(tmp_path, monkeypatch):
    # run_alignment is called with backfill_scope="selected-families" and selected_family_ids=frozenset({"FAM001"}).
    # assert metadata has backfill_scope=selected-families and output_scope=diagnostic_only
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
pytest tests\test_alignment_pipeline.py tests\test_alignment_pipeline_backends.py tests\test_alignment_pipeline_outputs.py -q
```

Expected: failures for missing `backfill_scope`, metadata keys, and ledger path.

- [ ] **Step 3: Add output path and atomic writer**

Extend `AlignmentRunOutputs`:

```python
skipped_evidence_ledger_tsv: Path | None = None
```

Extend `output_paths()` with `emit_skipped_evidence_ledger: bool = False`.

In `write_outputs_atomic()`, write the ledger via `write_skipped_evidence_ledger_tsv()` when `outputs.skipped_evidence_ledger_tsv is not None`.

- [ ] **Step 4: Apply scope before owner backfill**

Add to `run_alignment()`:

```python
backfill_scope: BackfillScope = "full-audit"
selected_family_ids: frozenset[str] = frozenset()
```

After `owner_features` and optional pre-backfill consolidation:

```python
scope_selection = select_backfill_features(
    owner_features,
    sample_order=batch.sample_order,
    raw_sample_stems=frozenset(raw_paths),
    alignment_config=alignment_config,
    scope=backfill_scope,
    selected_family_ids=selected_family_ids,
)
backfill_features = scope_selection.features
```

Pass `backfill_features` into owner-backfill, but keep `owner_features` for matrix construction.

- [ ] **Step 5: Record metadata and timing**

Add metadata keys:

```python
"backfill_scope": backfill_scope
"output_scope": "diagnostic_only" if backfill_scope == "selected-families" else backfill_scope
"selected_family_count": str(len(selected_family_ids))
"skipped_evidence_predicate_version": PREDICATE_VERSION
```

Record a timing event:

```python
recorder.record(
    "alignment.backfill_scope",
    elapsed_sec=0.0,
    metrics={
        "backfill_scope": backfill_scope,
        "input_family_count": len(owner_features),
        "backfill_family_count": len(backfill_features),
        "skipped_evidence_row_count": len(scope_selection.skipped),
        "raw_xic_requests_skipped": sum(row.raw_xic_requests_skipped for row in scope_selection.skipped),
    },
)
```

- [ ] **Step 6: Run pipeline tests**

Run:

```powershell
pytest tests\test_alignment_pipeline.py tests\test_alignment_pipeline_backends.py tests\test_alignment_pipeline_outputs.py -q
```

Expected: pass.

- [ ] **Step 7: Add full-audit rollback regression**

Add a deterministic no-RAW test that exercises the default path:

```python
def test_pipeline_full_audit_default_preserves_legacy_surface(tmp_path, monkeypatch):
    # Call run_alignment without backfill_scope.
    # Assert backfill_scope defaults to full-audit.
    # Assert skipped_evidence_ledger.tsv is not written.
    # Assert the feature tuple sent to build_owner_backfill_cells is identical
    # to the clustered feature tuple, including review-only audit features.
    # Assert alignment workbook/TSV output paths stay unchanged.
```

Add an owner-backfill request-order test:

```python
def test_backfill_request_sample_stems_matches_legacy_order_for_full_audit():
    feature = _feature("FAM001", owners=("S1",), confirm=False)
    samples = backfill_request_sample_stems(
        feature,
        sample_order=("S1", "S2", "S3"),
        raw_sample_stems=frozenset({"S1", "S2", "S3"}),
        alignment_config=AlignmentConfig(),
    )
    assert samples == ("S2", "S3")
```

---

### Task 5: CLI Contract

**Files:**
- Modify: `scripts/run_alignment.py`
- Test: `tests/test_run_alignment.py`

- [ ] **Step 1: Write failing CLI tests**

Add tests:

```python
def test_run_alignment_passes_backfill_scope_and_allowlist(tmp_path, monkeypatch):
    allowlist = tmp_path / "families.tsv"
    allowlist.write_text("feature_family_id\nFAM001\n", encoding="utf-8")
    captured = {}
    monkeypatch.setattr(run_alignment_module, "run_alignment", lambda **kwargs: captured.update(kwargs) or _outputs(tmp_path))
    argv = _required_alignment_args(tmp_path) + [
        "--backfill-scope",
        "selected-families",
        "--backfill-family-list-tsv",
        str(allowlist),
    ]
    code = run_alignment_module.main(argv)
    assert code == 0
    assert captured["backfill_scope"] == "selected-families"
    assert captured["selected_family_ids"] == frozenset({"FAM001"})
```

```python
def test_run_alignment_requires_allowlist_for_selected_families(tmp_path):
    argv = _required_alignment_args(tmp_path) + [
        "--backfill-scope",
        "selected-families",
    ]
    code = run_alignment_module.main(argv)
    assert code == 2
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
pytest tests\test_run_alignment.py -q
```

Expected: failures for missing flags.

- [ ] **Step 3: Add argparse flags and validation**

Add:

```python
parser.add_argument("--backfill-scope", choices=("full-audit", "production-equivalent", "selected-families"), default="full-audit")
parser.add_argument("--backfill-family-list-tsv", type=Path)
parser.add_argument("--backfill-family-id-column", default="feature_family_id")
parser.add_argument("--backfill-family-id", action="append", default=())
```

Resolve selected ids with `read_family_allowlist_tsv()` plus repeated ids. If `selected-families` has no ids, print an error and return `2`. If allowlist flags are used outside `selected-families`, print an error and return `2`.

- [ ] **Step 4: Run CLI tests**

Run:

```powershell
pytest tests\test_run_alignment.py -q
```

Expected: pass.

---

### Task 6: Parity Comparators And Cost Summary

**Files:**
- Create: `scripts/compare_alignment_workbooks.py`
- Create: `tools/diagnostics/p7_alignment_parity.py`
- Create: `tools/diagnostics/p7_evidence_cost_summary.py`
- Test: `tests/test_compare_alignment_workbooks.py`
- Test: `tests/test_p7_alignment_parity.py`
- Test: `tests/test_p7_evidence_cost_summary.py`

- [ ] **Step 1: Write failing comparator tests**

Create two small alignment workbooks with `Matrix`, `Review`, `Audit`, `Metadata`. Assert:

```python
def test_compare_alignment_workbooks_compares_matrix_only(tmp_path):
    # Matrix same, Review differs
    result = compare_alignment_workbooks(
        left,
        right,
        output_tsv=tmp_path / "matrix_parity.tsv",
        output_report=tmp_path / "matrix_compare.txt",
    )
    assert result.matched is True
    assert (tmp_path / "matrix_parity.tsv").is_file()
    assert (tmp_path / "matrix_compare.txt").is_file()
```

```python
def test_compare_alignment_workbooks_reports_matrix_difference(tmp_path):
    # Matrix value differs
    result = compare_alignment_workbooks(
        left,
        right,
        output_tsv=tmp_path / "matrix_parity.tsv",
        output_report=tmp_path / "matrix_compare.txt",
    )
    assert result.matched is False
    assert "Matrix!R2C5" in result.differences[0]
```

- [ ] **Step 2: Write failing primary TSV and benchmark parity tests**

Create baseline/optimized `alignment_matrix.tsv`, `alignment_review.tsv`, and
`targeted_istd_benchmark_summary.tsv` fixtures. Assert:

```python
def test_p7_alignment_parity_accepts_same_primary_rows_and_no_new_active_failures(tmp_path):
    result = run_p7_alignment_parity(
        baseline_alignment_dir=tmp_path / "baseline_alignment",
        optimized_alignment_dir=tmp_path / "optimized_alignment",
        baseline_benchmark_summary_tsv=tmp_path / "baseline_benchmark.tsv",
        optimized_benchmark_summary_tsv=tmp_path / "optimized_benchmark.tsv",
        output_dir=tmp_path / "compare",
    )
    assert result.overall_status == "PASS"
    assert (tmp_path / "compare" / "8raw_matrix_parity.tsv").is_file()
    assert (tmp_path / "compare" / "8raw_identity_parity.tsv").is_file()
    assert (tmp_path / "compare" / "8raw_targeted_benchmark_delta.tsv").is_file()
```

```python
def test_p7_alignment_parity_fails_on_identity_or_new_active_failure(tmp_path):
    # Change optimized primary identity_decision or add a new active FAIL row.
    result = run_p7_alignment_parity(
        baseline_alignment_dir=tmp_path / "baseline_alignment",
        optimized_alignment_dir=tmp_path / "optimized_alignment",
        baseline_benchmark_summary_tsv=tmp_path / "baseline_benchmark.tsv",
        optimized_benchmark_summary_tsv=tmp_path / "optimized_benchmark.tsv",
        output_dir=tmp_path / "compare",
    )
    assert result.overall_status == "FAIL"
```

The comparator must at minimum compare primary-included `feature_family_id`,
primary matrix sample values, `identity_decision`, `identity_confidence`,
`primary_evidence`, and `identity_reason`.

- [ ] **Step 3: Write failing P7 summary tests**

Use baseline/optimized timing JSON files, baseline/optimized economics JSON
files, and a skipped ledger TSV. Assert JSON/TSV summary includes:

```python
"baseline_owner_backfill_elapsed_sec"
"optimized_owner_backfill_elapsed_sec"
"owner_backfill_elapsed_sec"
"request_target_reduction_pct"
"owner_backfill_speedup_ratio"
"whole_alignment_wall_clock_improvement_pct"
"raw_xic_requests_skipped"
"skipped_evidence_row_count"
"owner_backfill_raw_chromatogram_call_saved"
"backfill_scope"
"operations_status"
"operations_status_reason"
```

Add deterministic operation-gate cases:

```python
def test_p7_cost_summary_passes_on_positive_resource_improvement(tmp_path):
    # baseline requests=100, optimized requests=40, baseline owner_backfill=100s,
    # optimized owner_backfill=40s.
    result = run_p7_evidence_cost_summary(
        baseline_timing_json=tmp_path / "baseline_timing.json",
        optimized_timing_json=tmp_path / "optimized_timing.json",
        baseline_owner_backfill_economics_json=tmp_path / "baseline_economics.json",
        optimized_owner_backfill_economics_json=tmp_path / "optimized_economics.json",
        skipped_evidence_ledger_tsv=tmp_path / "skipped_evidence_ledger.tsv",
        output_dir=tmp_path / "out",
    )
    assert result.operations_status == "PASS"
    assert result.request_target_reduction_pct == 60.0
    assert result.owner_backfill_speedup_ratio == 2.5


def test_p7_cost_summary_marks_inconclusive_when_nothing_improves(tmp_path):
    # baseline and optimized have the same requests, same XIC calls, same timing,
    # and the skipped ledger is empty.
    result = run_p7_evidence_cost_summary(
        baseline_timing_json=tmp_path / "baseline_timing.json",
        optimized_timing_json=tmp_path / "optimized_timing.json",
        baseline_owner_backfill_economics_json=tmp_path / "baseline_economics.json",
        optimized_owner_backfill_economics_json=tmp_path / "optimized_economics.json",
        skipped_evidence_ledger_tsv=tmp_path / "skipped_evidence_ledger.tsv",
        output_dir=tmp_path / "out",
    )
    assert result.operations_status == "inconclusive_perf"
    assert result.operations_status_reason == "no_positive_resource_improvement"
```

- [ ] **Step 4: Implement Matrix workbook comparator**

Implement `compare_alignment_workbooks(left_path, right_path, numeric_tolerance=1e-9)` and CLI:

```powershell
python -m scripts.compare_alignment_workbooks `
  left.xlsx `
  right.xlsx `
  --output-tsv output\phase1_p7_evidence_chain_cost_control\compare\8raw_matrix_parity.tsv `
  --output-report output\phase1_p7_evidence_chain_cost_control\compare\8raw_workbook_matrix_compare.txt
```

Compare only sheet `Matrix`. Ignore `Review`, `Audit`, and volatile metadata for production-equivalent parity.
The CLI must write the TSV/report artifacts even when mismatches are found.

- [ ] **Step 5: Implement primary TSV / targeted benchmark parity**

Implement CLI:

```powershell
python -m tools.diagnostics.p7_alignment_parity `
  --baseline-alignment-dir output\phase1_p7_evidence_chain_cost_control\alignment\8raw_full_audit `
  --optimized-alignment-dir output\phase1_p7_evidence_chain_cost_control\alignment\8raw_production_equivalent `
  --baseline-benchmark-summary-tsv output\phase1_p7_evidence_chain_cost_control\diagnostics\targeted_istd_benchmark_8raw_full_audit\targeted_istd_benchmark_summary.tsv `
  --optimized-benchmark-summary-tsv output\phase1_p7_evidence_chain_cost_control\diagnostics\targeted_istd_benchmark_8raw_production_equivalent\targeted_istd_benchmark_summary.tsv `
  --output-dir output\phase1_p7_evidence_chain_cost_control\compare
```

Write:

- `8raw_matrix_parity.tsv`
- `8raw_identity_parity.tsv`
- `8raw_targeted_benchmark_delta.tsv`
- `8raw_p7_alignment_parity.json`
- `8raw_p7_alignment_parity.md`

- [ ] **Step 6: Implement P7 cost summary**

Implement CLI:

```powershell
python -m tools.diagnostics.p7_evidence_cost_summary `
  --baseline-timing-json output\phase1_p7_evidence_chain_cost_control\alignment\8raw_full_audit\timing.json `
  --optimized-timing-json output\phase1_p7_evidence_chain_cost_control\alignment\8raw_production_equivalent\timing.json `
  --baseline-owner-backfill-economics-json output\phase1_p7_evidence_chain_cost_control\diagnostics\owner_backfill_economics_8raw_full_audit\owner_backfill_request_economics.json `
  --optimized-owner-backfill-economics-json output\phase1_p7_evidence_chain_cost_control\diagnostics\owner_backfill_economics_8raw_production_equivalent\owner_backfill_request_economics.json `
  --skipped-evidence-ledger-tsv output\phase1_p7_evidence_chain_cost_control\alignment\8raw_production_equivalent\skipped_evidence_ledger.tsv `
  --output-dir output\phase1_p7_evidence_chain_cost_control\diagnostics\p7_cost_summary_8raw
```

Write:

- `p7_evidence_cost_summary.json`
- `p7_evidence_cost_summary.tsv`
- `p7_evidence_cost_summary.md`
- `owner_backfill_economics_8raw_full_audit.json`
- `owner_backfill_economics_8raw_production_equivalent.json`
- `skipped_evidence_ledger_8raw.tsv`
- `skipped_evidence_summary_8raw.json`

The last four files are copied or summarized into
`output/phase1_p7_evidence_chain_cost_control/diagnostics/` using the exact
minimum-review-surface names required by the P7 spec.

- [ ] **Step 7: Add validation decision note template**

Create `output/phase1_p7_evidence_chain_cost_control/notes/p7_validation_decision.md`
from the summary CLI or a small writer helper. It must include:

- 8RAW correctness status
- 8RAW operations status and positive resource/timing metrics
- strict targeted ISTD benchmark delta
- skipped-evidence ledger path
- 85RAW preflight budget if the run is launched
- final gate language: `production_candidate`, `diagnostic_only`,
  `inconclusive_perf`, or `inconclusive_timeout`

- [ ] **Step 8: Run diagnostics tests**

Run:

```powershell
pytest tests\test_compare_alignment_workbooks.py tests\test_p7_alignment_parity.py tests\test_p7_evidence_cost_summary.py -q
```

Expected: pass.

---

### Task 7: Integration Verification

**Files:**
- Modify only if tests expose contract gaps.

- [ ] **Step 1: Run focused P7 unit tests**

Run:

```powershell
pytest tests\test_alignment_family_compatibility.py tests\test_backfill_scope.py tests\test_alignment_owner_backfill.py tests\test_alignment_process_backend.py tests\test_alignment_pipeline.py tests\test_alignment_pipeline_backends.py tests\test_alignment_pipeline_outputs.py tests\test_run_alignment.py tests\test_compare_alignment_workbooks.py tests\test_p7_alignment_parity.py tests\test_p7_evidence_cost_summary.py -q
```

Expected: pass.

- [ ] **Step 2: Run primary regression shard**

Run:

```powershell
pytest tests\test_alignment_primary_consolidation.py tests\test_alignment_matrix_identity.py tests\test_alignment_production_decisions.py tests\test_alignment_tsv_writer.py tests\test_alignment_xlsx_writer.py -q
```

Expected: pass.

- [ ] **Step 3: Run spec/doc smoke**

Run:

```powershell
git diff --check
rg -n "PLACEHOLDER|<[^>]+>" docs\superpowers\specs\2026-05-25-peak-pipeline-evidence-chain-cost-control-spec.md docs\superpowers\plans\2026-05-25-evidence-chain-cost-control-implementation-plan.md
```

Expected: `git diff --check` reports no whitespace errors. `rg` should return
no matches; if it returns a fenced-code example that is intentionally literal,
note the false positive in the final implementation review.

- [ ] **Step 4: Do implementation review**

Request a reviewer pass against:

- P7 spec
- this plan
- code diff
- focused test output

Fix Critical and Important findings before reporting completion.

---

## Real-Data Validation Commands To Run After Unit Implementation

These commands are intentionally not part of normal unit verification because they touch RAW data and can be slow.

8RAW full-audit baseline:

```powershell
python -m scripts.run_alignment `
  --discovery-batch-index output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\phase1_p7_evidence_chain_cost_control\alignment\8raw_full_audit `
  --output-level validation `
  --resolver-mode region_first_safe_merge `
  --backfill-scope full-audit `
  --performance-profile validation-fast `
  --raw-workers 8 `
  --raw-xic-batch-size 64 `
  --timing-output output\phase1_p7_evidence_chain_cost_control\alignment\8raw_full_audit\timing.json `
  --emit-alignment-integration-audit `
  --emit-baseline-audit-asls
```

8RAW optimized:

```powershell
python -m scripts.run_alignment `
  --discovery-batch-index output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\phase1_p7_evidence_chain_cost_control\alignment\8raw_production_equivalent `
  --output-level validation `
  --resolver-mode region_first_safe_merge `
  --backfill-scope production-equivalent `
  --performance-profile validation-fast `
  --raw-workers 8 `
  --raw-xic-batch-size 64 `
  --timing-output output\phase1_p7_evidence_chain_cost_control\alignment\8raw_production_equivalent\timing.json
```

8RAW Matrix workbook parity:

```powershell
python -m scripts.compare_alignment_workbooks `
  output\phase1_p7_evidence_chain_cost_control\alignment\8raw_full_audit\alignment_results.xlsx `
  output\phase1_p7_evidence_chain_cost_control\alignment\8raw_production_equivalent\alignment_results.xlsx `
  --output-tsv output\phase1_p7_evidence_chain_cost_control\compare\8raw_matrix_parity.tsv `
  --output-report output\phase1_p7_evidence_chain_cost_control\compare\8raw_workbook_matrix_compare.txt
```

8RAW strict targeted ISTD benchmarks:

```powershell
python -m tools.diagnostics.targeted_istd_benchmark `
  --targeted-workbook output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\xic_results_process_w4.xlsx `
  --alignment-dir output\phase1_p7_evidence_chain_cost_control\alignment\8raw_full_audit `
  --output-dir output\phase1_p7_evidence_chain_cost_control\diagnostics\targeted_istd_benchmark_8raw_full_audit

python -m tools.diagnostics.targeted_istd_benchmark `
  --targeted-workbook output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\xic_results_process_w4.xlsx `
  --alignment-dir output\phase1_p7_evidence_chain_cost_control\alignment\8raw_production_equivalent `
  --output-dir output\phase1_p7_evidence_chain_cost_control\diagnostics\targeted_istd_benchmark_8raw_production_equivalent

python -m tools.diagnostics.p7_alignment_parity `
  --baseline-alignment-dir output\phase1_p7_evidence_chain_cost_control\alignment\8raw_full_audit `
  --optimized-alignment-dir output\phase1_p7_evidence_chain_cost_control\alignment\8raw_production_equivalent `
  --baseline-benchmark-summary-tsv output\phase1_p7_evidence_chain_cost_control\diagnostics\targeted_istd_benchmark_8raw_full_audit\targeted_istd_benchmark_summary.tsv `
  --optimized-benchmark-summary-tsv output\phase1_p7_evidence_chain_cost_control\diagnostics\targeted_istd_benchmark_8raw_production_equivalent\targeted_istd_benchmark_summary.tsv `
  --output-dir output\phase1_p7_evidence_chain_cost_control\compare
```

Owner-backfill economics:

```powershell
python -m tools.diagnostics.owner_backfill_request_economics `
  --alignment-dir output\phase1_p7_evidence_chain_cost_control\alignment\8raw_full_audit `
  --owner-backfill-min-detected-samples 1 `
  --output-dir output\phase1_p7_evidence_chain_cost_control\diagnostics\owner_backfill_economics_8raw_full_audit

python -m tools.diagnostics.owner_backfill_request_economics `
  --alignment-dir output\phase1_p7_evidence_chain_cost_control\alignment\8raw_production_equivalent `
  --owner-backfill-min-detected-samples 1 `
  --output-dir output\phase1_p7_evidence_chain_cost_control\diagnostics\owner_backfill_economics_8raw_production_equivalent

python -m tools.diagnostics.p7_evidence_cost_summary `
  --baseline-timing-json output\phase1_p7_evidence_chain_cost_control\alignment\8raw_full_audit\timing.json `
  --optimized-timing-json output\phase1_p7_evidence_chain_cost_control\alignment\8raw_production_equivalent\timing.json `
  --baseline-owner-backfill-economics-json output\phase1_p7_evidence_chain_cost_control\diagnostics\owner_backfill_economics_8raw_full_audit\owner_backfill_request_economics.json `
  --optimized-owner-backfill-economics-json output\phase1_p7_evidence_chain_cost_control\diagnostics\owner_backfill_economics_8raw_production_equivalent\owner_backfill_request_economics.json `
  --skipped-evidence-ledger-tsv output\phase1_p7_evidence_chain_cost_control\alignment\8raw_production_equivalent\skipped_evidence_ledger.tsv `
  --output-dir output\phase1_p7_evidence_chain_cost_control\diagnostics\p7_cost_summary_8raw
```

85RAW optimized re-entry must only run after 8RAW correctness and operations
gates pass:

Preflight budget block to write into
`output\phase1_p7_evidence_chain_cost_control\notes\p7_validation_decision.md`
before launching 85RAW:

```text
85RAW preflight:
- overall_wall_clock_budget_min: 180
- owner_backfill_stage_budget_min: 75
- timeout_status: inconclusive_timeout
- preserve_stdout: output\phase1_p7_evidence_chain_cost_control\notes\85raw_stdout.txt
- preserve_stderr: output\phase1_p7_evidence_chain_cost_control\notes\85raw_stderr.txt
- preserve_timing: output\phase1_p7_evidence_chain_cost_control\alignment\85raw_production_equivalent\timing.json
- preserve_skipped_ledger: output\phase1_p7_evidence_chain_cost_control\alignment\85raw_production_equivalent\skipped_evidence_ledger.tsv
- preserve_economics: output\phase1_p7_evidence_chain_cost_control\diagnostics\owner_backfill_economics_85raw_production_equivalent
```

Run with an external timeout wrapper or manually stop at the preflight budget.
If the process is stopped, run whatever artifact-preservation commands are still
possible and record `inconclusive_timeout`; do not rerun full 85RAW full-audit as
rollback.

```powershell
python -m scripts.run_alignment `
  --discovery-batch-index output\phase1_p2b_85raw_validation\discovery\dR\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\phase1_p7_evidence_chain_cost_control\alignment\85raw_production_equivalent `
  --output-level validation `
  --resolver-mode region_first_safe_merge `
  --backfill-scope production-equivalent `
  --performance-profile validation-fast `
  --raw-workers 8 `
  --raw-xic-batch-size 64 `
  --timing-output output\phase1_p7_evidence_chain_cost_control\alignment\85raw_production_equivalent\timing.json
```

85RAW strict targeted ISTD benchmark:

```powershell
python -m tools.diagnostics.targeted_istd_benchmark `
  --targeted-workbook output\phase1_p2b_85raw_validation\targeted\region_first_safe_merge\tissue_85raw_region_first_safe_merge\xic_results_process_w4.xlsx `
  --alignment-dir output\phase1_p7_evidence_chain_cost_control\alignment\85raw_production_equivalent `
  --output-dir output\phase1_p7_evidence_chain_cost_control\diagnostics\targeted_istd_benchmark_85raw_production_equivalent
```

85RAW selected-family AsLS diagnostic allowlist and gate:

```powershell
Import-Csv output\phase1_p7_evidence_chain_cost_control\diagnostics\targeted_istd_benchmark_85raw_production_equivalent\targeted_istd_benchmark_summary.tsv -Delimiter "`t" |
  Where-Object { $_.role -eq "ISTD" -and $_.active_tag -eq "TRUE" -and $_.selected_feature_id } |
  Select-Object @{Name="feature_family_id"; Expression={$_.selected_feature_id}} |
  Export-Csv output\phase1_p7_evidence_chain_cost_control\diagnostics\selected_istd_families_85raw.tsv -Delimiter "`t" -NoTypeInformation

python -m scripts.run_alignment `
  --discovery-batch-index output\phase1_p2b_85raw_validation\discovery\dR\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\phase1_p7_evidence_chain_cost_control\alignment\85raw_selected_family_asls `
  --output-level validation `
  --resolver-mode region_first_safe_merge `
  --backfill-scope selected-families `
  --backfill-family-list-tsv output\phase1_p7_evidence_chain_cost_control\diagnostics\selected_istd_families_85raw.tsv `
  --backfill-family-id-column feature_family_id `
  --performance-profile validation-fast `
  --raw-workers 8 `
  --raw-xic-batch-size 64 `
  --timing-output output\phase1_p7_evidence_chain_cost_control\alignment\85raw_selected_family_asls\timing.json `
  --emit-alignment-integration-audit `
  --emit-baseline-audit-asls

python -m tools.diagnostics.p2_asls_shadow_gate `
  --alignment-integration-audit-tsv output\phase1_p7_evidence_chain_cost_control\alignment\85raw_selected_family_asls\alignment_cell_integration_audit.tsv `
  --targeted-istd-benchmark-summary-tsv output\phase1_p7_evidence_chain_cost_control\diagnostics\targeted_istd_benchmark_85raw_production_equivalent\targeted_istd_benchmark_summary.tsv `
  --output-dir output\phase1_p7_evidence_chain_cost_control\diagnostics\p2_selected_asls_shadow_gate_85raw
```

Selected-family full-audit smoke fallback:

```powershell
python -m tools.diagnostics.p2_asls_shadow_gate `
  --alignment-integration-audit-tsv output\phase1_p7_evidence_chain_cost_control\alignment\8raw_full_audit\alignment_cell_integration_audit.tsv `
  --targeted-istd-benchmark-summary-tsv output\phase1_p7_evidence_chain_cost_control\diagnostics\targeted_istd_benchmark_8raw_full_audit\targeted_istd_benchmark_summary.tsv `
  --output-dir output\phase1_p7_evidence_chain_cost_control\diagnostics\selected_family_full_audit_smoke_8raw
```

This smoke reuses the 8RAW `full-audit` run and selected ISTD rows to prove the
full-audit fallback surface remains callable for focused investigation. It is
not a full 85RAW full-audit rerun.
