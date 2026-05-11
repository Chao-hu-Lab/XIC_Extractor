# MS2-Constrained MS1 Feature Family Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate feature identity, MS1 measurement, and duplicate ownership semantics so untargeted alignment does not drift back into FH-style MS2 trigger rows or mz/RT-only feature merging.

**Architecture:** Keep the current alignment pipeline shape. Tighten feature-family identity in `feature_family.py`, preserve detected/rescued cell semantics in `family_integration.py`, and make `duplicate_assigned` explicit in TSV/debug outputs. Do not change XLSX/HTML production output in this plan.

**Tech Stack:** Python, pytest, existing `xic_extractor.alignment` models, current TSV writers, synthetic tests only.

---

## Related Specs

- `docs/superpowers/specs/2026-05-11-ms2-constrained-ms1-feature-family-spec.md`
- `docs/superpowers/specs/2026-05-11-untargeted-alignment-output-contract.md`

## Files

- Modify: `xic_extractor/alignment/feature_family.py`
- Modify: `xic_extractor/alignment/family_integration.py`
- Modify: `xic_extractor/alignment/tsv_writer.py`
- Modify: `tests/test_alignment_feature_family.py`
- Modify: `tests/test_alignment_family_integration.py`
- Modify: `tests/test_alignment_tsv_writer.py`
- Optional docs-only update if behavior wording changes: `docs/superpowers/plans/2026-05-11-alignment-output-cli-plan.md`

## Not In Scope

- XLSX writer.
- HTML report.
- Threshold calibration.
- HCD/full-fragment similarity.
- Real RAW validation.
- One-command discovery plus alignment workflow.

## Current Problem Map

```text
Current risk:

event cluster -> backfill matrix -> feature family merge
                     ^
                     |
             rescued cells can support identity

Desired:

event cluster -> original detected evidence -> feature family identity
event cluster -> family center -> MS1 measurement/backfill
family cells  -> ownership conflict resolution -> matrix/review semantics
```

## Task 1: Make Feature-Family Identity Detected-Only

**Files:**
- Modify: `tests/test_alignment_feature_family.py`
- Modify: `xic_extractor/alignment/feature_family.py`

- [ ] **Step 1: Add rescued-only overlap red test**

Add this test to `tests/test_alignment_feature_family.py`:

```python
def test_rescued_overlap_without_shared_detected_does_not_make_one_family():
    left = _cluster(
        "ALN000001",
        has_anchor=True,
        mz=242.114,
        rt=12.5927,
        members=("s1",),
    )
    right = _cluster(
        "ALN000002",
        has_anchor=False,
        mz=242.115,
        rt=12.5916,
        members=("s2",),
    )
    matrix = AlignmentMatrix(
        clusters=(left, right),
        sample_order=("s1", "s2"),
        cells=(
            _cell("s1", "ALN000001", "detected", area=100.0),
            _cell("s2", "ALN000001", "rescued", area=80.0),
            _cell("s1", "ALN000002", "rescued", area=90.0),
            _cell("s2", "ALN000002", "detected", area=95.0),
        ),
    )

    families = build_ms1_feature_families(
        (left, right),
        event_matrix=matrix,
        config=AlignmentConfig(
            duplicate_fold_min_shared_detected_count=1,
            duplicate_fold_min_detected_overlap=0.5,
            duplicate_fold_min_detected_jaccard=0.5,
        ),
    )

    assert [family.event_cluster_ids for family in families] == [
        ("ALN000001",),
        ("ALN000002",),
    ]
```

- [ ] **Step 2: Run red test**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_feature_family.py::test_rescued_overlap_without_shared_detected_does_not_make_one_family -v
```

Expected: FAIL because current `_PRESENT_STATUSES = {"detected", "rescued"}` lets rescued cells contribute to family merge evidence.

- [ ] **Step 3: Replace identity sample helper**

In `xic_extractor/alignment/feature_family.py`, replace `_PRESENT_STATUSES` and `_present_samples()` with detected-specific and measured-specific helpers:

```python
_IDENTITY_STATUSES = {"detected"}
_MEASURED_STATUSES = {"detected", "rescued"}


def _identity_samples(cells: tuple[AlignedCell, ...]) -> frozenset[str]:
    return frozenset(
        cell.sample_stem for cell in cells if cell.status in _IDENTITY_STATUSES
    )


def _measured_samples(cells: tuple[AlignedCell, ...]) -> frozenset[str]:
    return frozenset(
        cell.sample_stem for cell in cells if cell.status in _MEASURED_STATUSES
    )
```

Then update `_same_ms1_feature_family()`, `_sort_family_group()`, and `_family_evidence()` to use `_identity_samples()` anywhere the code computes `shared_detected`, overlap, Jaccard, or sorting by evidence strength.

Do not use `_measured_samples()` for merge eligibility in this task. It is reserved for future diagnostics only.

- [ ] **Step 4: Run feature-family tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_feature_family.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_alignment_feature_family.py xic_extractor/alignment/feature_family.py
git commit -m "fix(alignment): keep rescued cells out of family identity"
```

## Task 2: Preserve Detected vs Rescued In Family Integration

**Files:**
- Modify: `tests/test_alignment_family_integration.py`
- Modify: `xic_extractor/alignment/family_integration.py`

- [ ] **Step 1: Add status semantics tests**

Add these tests to `tests/test_alignment_family_integration.py`:

```python
def test_family_integration_marks_original_member_peak_as_detected():
    family = build_ms1_feature_family(
        family_id="FAM000001",
        event_clusters=(_cluster("ALN000001", has_anchor=True),),
        evidence="single_event_cluster",
    )
    source = FakeXICSource(
        rt=np.array([12.50, 12.54, 12.58, 12.62, 12.66], dtype=float),
        intensity=np.array([0.0, 10.0, 100.0, 10.0, 0.0], dtype=float),
    )

    matrix = integrate_feature_family_matrix(
        (family,),
        sample_order=("s1",),
        raw_sources={"s1": source},
        alignment_config=_alignment_config(),
        peak_config=_peak_config(),
    )

    assert matrix.cells[0].status == "detected"
    assert matrix.cells[0].reason == "family-centered MS1 integration from original detection"


def test_family_integration_marks_anchor_backfill_peak_as_rescued():
    family = build_ms1_feature_family(
        family_id="FAM000001",
        event_clusters=(_cluster("ALN000001", has_anchor=True),),
        evidence="single_event_cluster",
    )
    source = FakeXICSource(
        rt=np.array([12.50, 12.54, 12.58, 12.62, 12.66], dtype=float),
        intensity=np.array([0.0, 10.0, 100.0, 10.0, 0.0], dtype=float),
    )

    matrix = integrate_feature_family_matrix(
        (family,),
        sample_order=("s1", "s2"),
        raw_sources={"s1": source, "s2": source},
        alignment_config=_alignment_config(),
        peak_config=_peak_config(),
    )

    cells = {cell.sample_stem: cell for cell in matrix.cells}
    assert cells["s1"].status == "detected"
    assert cells["s2"].status == "rescued"
    assert cells["s2"].reason == "family-centered MS1 backfill"
```

- [ ] **Step 2: Run red tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_family_integration.py::test_family_integration_marks_original_member_peak_as_detected tests/test_alignment_family_integration.py::test_family_integration_marks_anchor_backfill_peak_as_rescued -v
```

Expected: FAIL because current integration marks every found peak as `detected`.

- [ ] **Step 3: Implement status selection**

In `xic_extractor/alignment/family_integration.py`, add:

```python
def _has_original_detection(family: MS1FeatureFamily, sample_stem: str) -> bool:
    return sample_stem in _event_member_samples(family)
```

Inside `_integrate_family_cell()`, after `peak = result.peak`, compute:

```python
has_original_detection = _has_original_detection(family, sample_stem)
status = "detected" if has_original_detection else "rescued"
reason = (
    "family-centered MS1 integration from original detection"
    if has_original_detection
    else "family-centered MS1 backfill"
)
```

Use `status=status` and `reason=reason` in the returned `AlignedCell`.

Keep the existing non-anchor rule:

```python
if not family.has_anchor and sample_stem not in _event_member_samples(family):
    return _unchecked_cell(...)
```

That means non-anchor families remain detected-only outside their original samples.

- [ ] **Step 4: Run family integration tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_family_integration.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_alignment_family_integration.py xic_extractor/alignment/family_integration.py
git commit -m "fix(alignment): preserve family backfill status semantics"
```

## Task 3: Make Duplicate Ownership A First-Class Status

**Files:**
- Modify: `tests/test_alignment_family_integration.py`
- Modify: `tests/test_alignment_tsv_writer.py`
- Modify: `xic_extractor/alignment/family_integration.py`
- Modify: `xic_extractor/alignment/tsv_writer.py`

- [ ] **Step 1: Update ownership tests**

In `tests/test_alignment_family_integration.py`, update duplicate ownership assertions from ordinary absence to `duplicate_assigned`:

```python
assert cells["FAM000001"].status == "duplicate_assigned"
assert cells["FAM000001"].area is None
assert cells["FAM000001"].trace_quality == "assigned_duplicate"
assert cells["FAM000001"].reason == (
    "MS1 peak assigned to selected feature family FAM000002"
)
```

Apply this to both duplicate ownership tests.

- [ ] **Step 2: Add TSV status/matrix tests**

Add these tests to `tests/test_alignment_tsv_writer.py`:

```python
def test_write_alignment_matrix_tsv_blanks_duplicate_assigned_cells(tmp_path: Path):
    from xic_extractor.alignment.tsv_writer import write_alignment_matrix_tsv

    matrix = AlignmentMatrix(
        clusters=(_cluster(),),
        cells=(
            _cell(
                "sample-a",
                "duplicate_assigned",
                area=100.0,
                trace_quality="assigned_duplicate",
            ),
        ),
        sample_order=("sample-a",),
    )

    rows = _read_tsv(write_alignment_matrix_tsv(tmp_path / "matrix.tsv", matrix))

    assert rows[0]["sample-a"] == ""


def test_write_alignment_status_matrix_tsv_preserves_duplicate_assigned(tmp_path: Path):
    from xic_extractor.alignment.tsv_writer import write_alignment_status_matrix_tsv

    matrix = AlignmentMatrix(
        clusters=(_cluster(),),
        cells=(
            _cell(
                "sample-a",
                "duplicate_assigned",
                area=None,
                trace_quality="assigned_duplicate",
            ),
        ),
        sample_order=("sample-a",),
    )

    rows = _read_tsv(
        write_alignment_status_matrix_tsv(tmp_path / "status.tsv", matrix)
    )

    assert rows[0]["sample-a"] == "duplicate_assigned"
```

- [ ] **Step 3: Run red tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_family_integration.py tests/test_alignment_tsv_writer.py::test_write_alignment_matrix_tsv_blanks_duplicate_assigned_cells tests/test_alignment_tsv_writer.py::test_write_alignment_status_matrix_tsv_preserves_duplicate_assigned -v
```

Expected: FAIL because ownership losers are currently encoded as `absent`.

- [ ] **Step 4: Implement duplicate-assigned status**

In `xic_extractor/alignment/family_integration.py`, update `_assigned_to_selected_family()`:

```python
return replace(
    cell,
    status="duplicate_assigned",
    area=None,
    apex_rt=None,
    height=None,
    peak_start_rt=None,
    peak_end_rt=None,
    rt_delta_sec=None,
    trace_quality="assigned_duplicate",
    scan_support_score=None,
    reason=f"MS1 peak assigned to selected feature family {winners_family_id}",
)
```

In `xic_extractor/alignment/tsv_writer.py`, keep `_matrix_area()` restrictive:

```python
if cell is None or cell.status not in {"detected", "rescued"}:
    return ""
```

This already blanks `duplicate_assigned`; the test locks the contract.

- [ ] **Step 5: Run TSV and integration tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_family_integration.py tests/test_alignment_tsv_writer.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add tests/test_alignment_family_integration.py tests/test_alignment_tsv_writer.py xic_extractor/alignment/family_integration.py xic_extractor/alignment/tsv_writer.py
git commit -m "fix(alignment): expose duplicate-assigned cell status"
```

## Task 4: Align Review Counts With Status Semantics

**Files:**
- Modify: `tests/test_alignment_tsv_writer.py`
- Modify: `xic_extractor/alignment/tsv_writer.py`

- [ ] **Step 1: Add review count test**

Add this test to `tests/test_alignment_tsv_writer.py`:

```python
def test_write_alignment_review_tsv_counts_duplicate_assigned_separately(tmp_path: Path):
    from xic_extractor.alignment.tsv_writer import write_alignment_review_tsv

    matrix = AlignmentMatrix(
        clusters=(_cluster(has_anchor=True),),
        cells=(
            _cell("sample-a", "detected", area=100.0),
            _cell("sample-b", "rescued", area=90.0),
            _cell(
                "sample-c",
                "duplicate_assigned",
                area=None,
                trace_quality="assigned_duplicate",
            ),
            _cell("sample-d", "absent", area=None),
        ),
        sample_order=("sample-a", "sample-b", "sample-c", "sample-d"),
    )

    rows = _read_tsv(write_alignment_review_tsv(tmp_path / "review.tsv", matrix))

    assert rows[0]["detected_count"] == "1"
    assert rows[0]["absent_count"] == "1"
    assert rows[0]["unchecked_count"] == "0"
    assert rows[0]["present_rate"] == "0.5"
    assert "1 duplicate-assigned" in rows[0]["reason"]
```

- [ ] **Step 2: Run red or characterization test**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_tsv_writer.py::test_write_alignment_review_tsv_counts_duplicate_assigned_separately -v
```

Expected:

- If it fails, current review logic is counting duplicate assignment incorrectly.
- If it passes, keep it as characterization for the new status contract.

- [ ] **Step 3: Implement only if needed**

If the test fails, update `_review_rows()` in `xic_extractor/alignment/tsv_writer.py` so:

```python
duplicate_assigned_count = _count(cells, "duplicate_assigned")
```

Then pass that count into `_reason()`.

Do not count `duplicate_assigned` as absent, unchecked, detected, rescued, or present.

- [ ] **Step 4: Run full alignment writer tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_tsv_writer.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_alignment_tsv_writer.py xic_extractor/alignment/tsv_writer.py
git commit -m "fix(alignment): keep duplicate assignments out of absence counts"
```

## Task 5: Narrow Regression Gate

**Files:**
- No production files unless tests expose a regression.

- [ ] **Step 1: Run focused alignment tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_feature_family.py tests/test_alignment_family_integration.py tests/test_alignment_tsv_writer.py tests/test_alignment_pipeline.py -v
```

Expected: PASS.

- [ ] **Step 2: Run lint**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\\alignment tests\\test_alignment_feature_family.py tests\\test_alignment_family_integration.py tests\\test_alignment_tsv_writer.py
```

Expected: PASS.

- [ ] **Step 3: Record validation status**

Do not run real RAW by default for this cleanup. If the tests pass, record in the
PR summary that real-data validation is deferred because this plan fixes
algorithm semantics and synthetic contracts first.

- [ ] **Step 4: Commit docs if needed**

If this plan or the spec changed during implementation:

```powershell
git add docs/superpowers/specs/2026-05-11-ms2-constrained-ms1-feature-family-spec.md docs/superpowers/plans/2026-05-11-ms2-constrained-ms1-feature-family-plan.md
git commit -m "docs(alignment): define MS2-constrained MS1 family semantics"
```

## Engineering Review

Review mode: plan-level engineering review.

Findings fixed before execution:

1. Initial design risk: requiring shared detected evidence could sound like FH
   event rows are the final identity. Fixed by making the contract explicit:
   original MS2/NL evidence constrains identity, MS1 peak evidence decides
   chromatographic family, and backfill measures missing samples.
2. Initial output risk: duplicate-assigned cells could disappear into blank
   matrix cells. Fixed by requiring `duplicate_assigned` to remain visible in
   review/status/debug surfaces even when the production matrix value is blank.
3. Initial scope risk: production XLSX/HTML decisions could mix with algorithm
   cleanup. Fixed by keeping this plan limited to feature-family identity,
   family integration statuses, duplicate ownership, and existing TSV/debug
   contracts.

No unresolved decisions in this plan.

## Acceptance Criteria

- `rescued` cells do not create feature-family merge eligibility.
- `shared_detected` evidence counts original detected cells only.
- family-centered integration outputs `detected` for original members and
  `rescued` for anchor-family backfilled samples.
- duplicate ownership losers use `duplicate_assigned`, not ordinary `absent`.
- matrix values remain blank for `duplicate_assigned`.
- status/debug output preserves `duplicate_assigned`.
- focused alignment tests and ruff pass.
