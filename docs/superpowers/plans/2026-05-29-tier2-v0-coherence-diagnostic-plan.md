# Tier 2 V0 Coherence Diagnostic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans in checkpoint mode to implement this plan task-by-task. `superpowers:subagent-driven-development` is not the default for this checkpoint because the write surface is a tightly coupled producer/gate/schema/test contract; use repo-routed read-only reviewer subagents before execution and after implementation. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `diagnostic_only` Tier 2 v0.1 coherence sidecar pilot so RAW trace re-read rows expose richer diagnostic context without promoting rows or changing `alignment_matrix.tsv`.

**Architecture:** Keep `xic_extractor/alignment/tier2_trace_producer.py` as the owner of RAW trace diagnostic metrics and sidecar row construction. Keep `xic_extractor/alignment/production_candidate_gate.py` as the owner of sidecar provenance loading and candidate-gate projection, with an explicit v0.1 diagnostic-only blocker so v0.1 rows cannot become positive Tier 2 support. Keep `tools/diagnostics/` CLIs as IO wrappers that write/consume paired sidecars and summaries.

**Tech Stack:** Python 3, standard-library `csv`, `json`, `hashlib`, `math`, `statistics`, `dataclasses`, `pathlib`, existing diagnostic TSV helpers, pytest, ruff, Thermo RAW through the existing `.venv` runner for the 8RAW rerun only.

---

## Checkpoint Boundary

Implement now:

- New criteria version:
  `tier2_trace_identity_rescued_coherence_v0_1_diagnostic`.
- Diagnostic columns for:
  - scan availability separate from `scan_support_score`;
  - local signal/noise/shape context;
  - seed-vs-rescued, rescued-pairwise, and family-consensus boundary views;
  - raw apex span, seed-to-rescued apex span, and rescued-only apex span;
  - neighbor-interference not-assessed context.
- Gate consumption of v0.1 sidecars as diagnostic context only.
- Unit/contract tests and one 8RAW diagnostic rerun.
- Validation note and diagnostic index wording update.

Do not implement now:

- 85RAW.
- Product promotion.
- Formal neighbor-interference computation.
- Drift-normalized apex-span gate.
- `alignment_matrix.tsv`, workbook, GUI, or `scripts.run_alignment` behavior changes.

Exit rule:

- If v0.1 metrics differentiate the current blockers, promote only to the next
  reviewed diagnostic/shadow contract, not to production support.
- If v0.1 metrics only restate owner-backfill provenance, kill or externalize
  the producer.
- If 8RAW cannot distinguish poor criteria from poor data, return
  `inconclusive`; do not tune thresholds into a positive gate.

## File Structure

Modify:

- `xic_extractor/alignment/production_candidate_gate.py`
  - Add v0/v0.1 criteria constants and v0.1 diagnostic-only blocker.
  - Split v0/v0.1 sidecar column sets so old v0 artifacts remain loadable while
    the v0.1 producer writes the expanded schema.
  - Preserve current legacy v0 diagnostic-gate support semantics for
    compatibility, while making only v0.1 diagnostic-only.
  - Remove uncomputed neighbor interference from v0.1 positive criteria by
    preventing any v0.1 positive-support path.

- `xic_extractor/alignment/tier2_trace_producer.py`
  - Change producer criteria version to v0.1 diagnostic.
  - Expand `_TraceMetrics` with signal/noise/shape context.
  - Compute boundary-reference and apex-span diagnostic views.
  - Emit v0.1 rows as diagnostic context, with no support component.

- `tools/diagnostics/tier2_raw_trace_reread_producer.py`
  - Continue writing paired sidecars and JSON summary using the expanded v0.1
    writer schema.
  - Keep `readiness_label=diagnostic_only` and add summary fields that make
    v0.1 diagnostic-only status obvious.

- `tools/diagnostics/provisional_backfill_candidate_gate.py`
  - Keep paired Tier 2 sidecar/manifest consumption.
  - Ensure v0.1 sidecar consume output remains `diagnostic_only` with zero
    production candidates.

- `tools/diagnostics/INDEX.md`
  - Update the Tier 2 RAW trace producer entry with v0.1 diagnostic-only
    wording and no-85RAW boundary.

- `tests/test_tier2_raw_trace_producer.py`
  - Add v0.1 metric/schema/status tests.

- `tests/test_tier2_raw_trace_reread_producer_cli.py`
  - Add CLI v0.1 summary and gate-consume diagnostic-only tests.

- `tests/test_production_candidate_gate.py`
  - Add v0.1 diagnostic-only gate tests and backward-compatible v0 loading
    tests.

- `tests/test_provisional_backfill_candidate_gate_cli.py`
  - Add CLI test proving a v0.1 sidecar is consumed but does not promote.

- `tests/test_alignment_tsv_writer.py`
  - Keep the direct-review-token matrix guard unchanged.

Create:

- `docs/superpowers/notes/2026-05-29-tier2-v0-coherence-diagnostic-validation-note.md`

## Public Contract

New constants in `production_candidate_gate.py`:

```python
TIER2_CRITERIA_V0 = "tier2_trace_identity_rescued_coherence_v0"
TIER2_CRITERIA_V0_1 = "tier2_trace_identity_rescued_coherence_v0_1_diagnostic"
TIER2_DIAGNOSTIC_ONLY_CRITERIA_VERSIONS = frozenset({TIER2_CRITERIA_V0_1})
TIER2_ALLOWED_CRITERIA_VERSIONS = frozenset({TIER2_CRITERIA_V0, TIER2_CRITERIA_V0_1})
TIER2_RECOGNIZED_PRODUCER_VERSIONS = frozenset(
    {"raw_trace_reread_tier2_v0", "raw_trace_reread_tier2_v0_1"}
)
```

Expanded v0.1 sidecar columns:

```python
TIER2_TRACE_EVIDENCE_V0_1_COLUMNS = (
    *TIER2_TRACE_EVIDENCE_V0_COLUMNS,
    "scan_availability_score",
    "trace_apex_intensity",
    "trace_baseline_noise",
    "trace_signal_to_noise_proxy",
    "trace_apex_prominence_score",
    "scan_support_basis",
    "seed_rescued_boundary_overlap_min",
    "rescued_pairwise_boundary_overlap_min",
    "family_consensus_boundary_overlap_min",
    "seed_rescued_apex_span_sec",
    "rescued_only_apex_span_sec",
    "neighbor_interference_status",
)
```

Keep `TIER2_TRACE_EVIDENCE_REQUIRED_COLUMNS` as the writer schema for the new
producer:

```python
TIER2_TRACE_EVIDENCE_REQUIRED_COLUMNS = TIER2_TRACE_EVIDENCE_V0_1_COLUMNS
```

But loader behavior must be version-aware:

```python
def _tier2_required_columns_for_row(row: Mapping[str, str]) -> tuple[str, ...]:
    if row.get("criteria_version") == TIER2_CRITERIA_V0:
        return TIER2_TRACE_EVIDENCE_V0_COLUMNS
    if row.get("criteria_version") == TIER2_CRITERIA_V0_1:
        return TIER2_TRACE_EVIDENCE_V0_1_COLUMNS
    return TIER2_TRACE_EVIDENCE_V0_COLUMNS
```

The loader may accept old v0 artifacts for readability. The v0.1 producer must
write only `TIER2_TRACE_EVIDENCE_V0_1_COLUMNS`.

Legacy compatibility policy:

- v0 sidecars with the original v0 column set remain loadable.
- Existing v0 diagnostic-gate positive-support behavior remains unchanged for
  compatibility tests and existing diagnostic artifacts.
- v0 compatibility does not imply `production_ready`, does not change
  `alignment_matrix.tsv`, and does not create a production promotion path.
- v0.1 sidecars are diagnostic context only and must never produce positive
  support in this checkpoint, even if a row is spoofed as `validated` with
  `support_component=validated_tier2_trace_evidence`.

---

### Task 0: Preconditions And Review Gate

**Files:**
- Read: `docs/superpowers/specs/2026-05-29-tier2-v0-coherence-criteria-review-design.md`
- Read: `docs/agent-parameter-settings.md`

- [ ] **Step 1: Verify current dirty scope**

Run:

```powershell
git status --short --branch
```

Expected before implementation:

```text
## codex/tiered-backfill-machine-decision
 M docs/superpowers/specs/2026-05-29-tier2-v0-coherence-criteria-review-design.md
?? docs/superpowers/plans/2026-05-29-tier2-v0-coherence-diagnostic-goal.md
?? docs/superpowers/plans/2026-05-29-tier2-v0-coherence-diagnostic-plan.md
```

- [ ] **Step 2: Verify 8RAW precondition hashes**

Run:

```powershell
Get-FileHash output\tier2_raw_trace_reread_8raw_current\alignment_tier2_trace_evidence.tsv -Algorithm SHA256
Get-FileHash output\tier2_raw_trace_reread_8raw_current\alignment_tier2_raw_manifest.tsv -Algorithm SHA256
Get-FileHash output\tier2_raw_trace_reread_8raw_current\alignment_tier2_trace_evidence_summary.json -Algorithm SHA256
Get-FileHash output\tier2_raw_trace_reread_8raw_current_gate\alignment_production_candidate_gate.tsv -Algorithm SHA256
Get-FileHash output\tier2_raw_trace_reread_8raw_current_gate\alignment_production_candidate_gate.json -Algorithm SHA256
```

Expected hashes are exactly the five values in the spec's
`Pilot Preconditions` table. Stop if any hash differs.

- [ ] **Step 3: Review goal and plan with repo-routed subagents**

Dispatch read-only reviewers before implementation:

- `strategy-challenger`: challenge whether the goal/plan remains diagnostic-only
  and has a real exit rule.
- `implementation-contract-reviewer`: challenge schema/version compatibility,
  public contract drift, and test coverage.

Expected: no blocking findings, or blockers patched before Task 1.

---

### Task 1: Pin V0.1 Diagnostic Schema In Tests

**Files:**
- Modify: `tests/test_tier2_raw_trace_producer.py`
- Modify: `tests/test_tier2_raw_trace_reread_producer_cli.py`

- [ ] **Step 1: Add imports for criteria constants**

In `tests/test_tier2_raw_trace_producer.py`, import:

```python
from xic_extractor.alignment.production_candidate_gate import (
    TIER2_CRITERIA_V0_1,
    TIER2_RAW_MANIFEST_REQUIRED_COLUMNS,
    TIER2_TRACE_EVIDENCE_REQUIRED_COLUMNS,
    GateSourceContext,
    evaluate_production_candidate_gate,
    load_tier2_trace_evidence,
    tier2_candidate_subset_signature,
)
```

- [ ] **Step 2: Update the existing positive-support producer test**

Rename `test_tier2_trace_producer_rows_are_consumable_positive_support` to:

```python
def test_tier2_trace_producer_rows_are_v0_1_diagnostic_only(
    tmp_path: Path,
) -> None:
```

Replace the final assertions with:

```python
    assert row["criteria_version"] == TIER2_CRITERIA_V0_1
    assert row["evidence_status"] == "inconclusive"
    assert row["support_component"] == ""
    assert row["raw_trace_reread_status"] == "pass"
    assert row["coherence_status"] == "inconclusive"
    assert "tier2_v0_1_diagnostic_only" in row["challenge_blockers"]
    assert "neighbor_interference_not_assessed" in row["dependent_context"]
    assert row["source_candidate_subset_sha256"] == subset.sha256
    assert row["source_candidate_subset_count"] == "1"

    for column in (
        "scan_availability_score",
        "trace_apex_intensity",
        "trace_baseline_noise",
        "trace_signal_to_noise_proxy",
        "trace_apex_prominence_score",
        "scan_support_basis",
        "seed_rescued_boundary_overlap_min",
        "rescued_pairwise_boundary_overlap_min",
        "family_consensus_boundary_overlap_min",
        "seed_rescued_apex_span_sec",
        "rescued_only_apex_span_sec",
        "neighbor_interference_status",
    ):
        assert column in row

    assert row["scan_support_basis"] == "scan_count_only"
    assert row["neighbor_interference_status"] == "not_assessed"

    sidecar_path = tmp_path / "alignment_tier2_trace_evidence.tsv"
    _write_tsv(sidecar_path, rows, TIER2_TRACE_EVIDENCE_REQUIRED_COLUMNS)
    evidence = load_tier2_trace_evidence(
        sidecar_path=sidecar_path,
        raw_manifest_path=raw_manifest_path,
        candidate_rows=review_rows,
        source_context=source_context,
    )["FAM001"]
    decision = evaluate_production_candidate_gate(
        review_rows[0],
        cell_rows,
        source_context=source_context,
        tier2_evidence=evidence,
    )

    assert decision.candidate_gate_status == "audit"
    assert decision.tier2_evidence_available is False
    assert decision.support_components == ()
    assert "tier2_v0_1_diagnostic_only" in decision.challenge_blockers
```

- [ ] **Step 3: Add metric-shape assertions**

Add a new test:

```python
def test_tier2_trace_producer_emits_signal_shape_and_reference_views(
    tmp_path: Path,
) -> None:
    rows = build_tier2_trace_evidence_rows(
        candidate_rows=[_candidate_review_row()],
        cells_by_family={"FAM001": tuple(_candidate_cell_rows())},
        source_context=_source_context(tmp_path),
        raw_manifest_sha256="ABC123",
        source_expected_sample_count=3,
        trace_loader=_passing_trace_loader,
        config=Tier2TraceProducerConfig(ppm_tolerance=20.0, rt_padding_min=0.02),
        producer_command="pytest fake producer",
        generated_at_utc="2026-05-29T00:00:00Z",
        python_executable=".venv\\Scripts\\python.exe",
        dll_dir="C:\\Xcalibur\\system\\programs",
    )

    row = rows[0]

    assert float(row["scan_availability_score"]) >= 1.0
    assert float(row["trace_apex_intensity"]) > 0.0
    assert float(row["trace_signal_to_noise_proxy"]) >= 0.0
    assert float(row["trace_apex_prominence_score"]) >= 0.0
    assert float(row["seed_rescued_boundary_overlap_min"]) > 0.0
    assert float(row["family_consensus_boundary_overlap_min"]) > 0.0
    assert float(row["seed_rescued_apex_span_sec"]) >= 0.0
    assert float(row["rescued_only_apex_span_sec"]) >= 0.0
```

- [ ] **Step 4: Update CLI producer summary expectations**

In `tests/test_tier2_raw_trace_reread_producer_cli.py`, update the first test:

```python
    assert rows[0]["candidate_gate_status"] == "audit"
    assert rows[0]["tier2_evidence_available"] == "FALSE"
    assert "tier2_v0_1_diagnostic_only" in rows[0]["challenge_blockers"]
    assert producer_summary["producer_version"] == "raw_trace_reread_tier2_v0_1"
    assert (
        producer_summary["criteria_version"]
        == "tier2_trace_identity_rescued_coherence_v0_1_diagnostic"
    )
    assert producer_summary["positive_support_count"] == 0
    assert producer_summary["validated_count"] == 0
    assert producer_summary["inconclusive_count"] == 1
```

- [ ] **Step 5: Run failing tests**

Run:

```powershell
python -m pytest tests\test_tier2_raw_trace_producer.py tests\test_tier2_raw_trace_reread_producer_cli.py -q
```

Expected before implementation: failures for missing constants/columns and new
v0.1 diagnostic-only behavior. Existing legacy v0 positive-support fixture
behavior remains covered by later gate compatibility tests.

---

### Task 2: Implement V0.1 Producer Metrics

**Files:**
- Modify: `xic_extractor/alignment/production_candidate_gate.py`
- Modify: `xic_extractor/alignment/tier2_trace_producer.py`

- [ ] **Step 1: Add criteria/schema constants**

In `production_candidate_gate.py`, replace the v0-only constants with the public
contract constants shown in the `Public Contract` section. Keep
`TIER2_TRACE_EVIDENCE_V0_COLUMNS` equal to the current v0 schema and set
`TIER2_TRACE_EVIDENCE_REQUIRED_COLUMNS` to the v0.1 writer schema.

- [ ] **Step 2: Make sidecar loading version-aware**

Replace the first sidecar read inside `load_tier2_trace_evidence()` with a
version-aware helper:

```python
    sidecar_rows = _read_tsv_versioned_tier2_sidecar(sidecar_path)
```

Add:

```python
def _read_tsv_versioned_tier2_sidecar(path: Path) -> tuple[dict[str, str], ...]:
    if not path.is_file():
        raise FileNotFoundError(f"Required TSV not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = tuple(reader.fieldnames or ())
        rows = tuple({key: value or "" for key, value in row.items()} for row in reader)
    if not fieldnames:
        raise ValueError(f"TSV has no header: {path}")
    base_missing = [column for column in TIER2_TRACE_EVIDENCE_V0_COLUMNS if column not in fieldnames]
    if base_missing:
        raise ValueError(f"{path} missing required columns: {', '.join(base_missing)}")
    for row in rows:
        required = _tier2_required_columns_for_row(row)
        missing = [column for column in required if column not in fieldnames]
        if missing:
            raise ValueError(f"{path} missing required columns: {', '.join(missing)}")
    return rows
```

- [ ] **Step 3: Add authoritative diagnostic-only blocker for v0.1**

In `_tier2_evidence_from_row()`, keep v0/v0.1 versions allowlisted for loading.
In `_tier2_blockers()`, add a version guard before evidence-status-specific
logic so the gate, not the row, is the authoritative source of v0.1
diagnostic-only behavior:

```python
    if evidence.criteria_version in TIER2_DIAGNOSTIC_ONLY_CRITERIA_VERSIONS:
        blockers.append("tier2_v0_1_diagnostic_only")
```

This guard must apply even when the v0.1 row is spoofed as `validated` with
`support_component=validated_tier2_trace_evidence`, and even when the row omits
`tier2_v0_1_diagnostic_only` from `challenge_blockers`.

Do not add a neighbor-interference blocker for v0.1 blank values. The blank
value is valid when `dependent_context` contains
`neighbor_interference_not_assessed`.

- [ ] **Step 4: Expand `_TraceMetrics`**

In `tier2_trace_producer.py`, update:

```python
CRITERIA_VERSION = "tier2_trace_identity_rescued_coherence_v0_1_diagnostic"
PRODUCER_VERSION = "raw_trace_reread_tier2_v0_1"
```

Add fields to `_TraceMetrics`:

```python
scan_availability_score: float
trace_apex_intensity: float
trace_baseline_noise: float
trace_signal_to_noise_proxy: float
trace_apex_prominence_score: float
```

- [ ] **Step 5: Compute signal/noise/shape diagnostics**

Add helpers:

```python
def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _trace_context_scores(intensities: tuple[float, ...]) -> tuple[float, float, float, float]:
    if not intensities:
        return 0.0, 0.0, 0.0, 0.0
    apex = max(intensities)
    baseline = _median(intensities)
    noise = _median(tuple(abs(value - baseline) for value in intensities))
    denominator = max(noise, 1.0)
    signal_to_noise = max(0.0, apex - baseline) / denominator
    edge_max = max(intensities[0], intensities[-1])
    prominence = max(0.0, apex - edge_max) / max(abs(apex), 1.0)
    return apex, noise, signal_to_noise, prominence
```

In `_trace_metrics_for_cell()`, compute:

```python
    region_intensities = tuple(value for _rt, value in region)
    scan_availability_score = _scan_support_score(
        region_intensities,
        scans_target=config.scans_target,
    )
    apex_intensity, noise, signal_to_noise, prominence = _trace_context_scores(
        region_intensities
    )
```

Set both `scan_support_score` and `scan_availability_score` to the scan-count
availability score for backward readability. The separate v0.1 columns make it
explicit that positive signal support is not established by scan count alone.

- [ ] **Step 6: Write v0.1 seed metrics**

Update `_apply_seed_metrics()`:

```python
            "scan_support_score": _format_float(metrics.scan_support_score),
            "scan_availability_score": _format_float(metrics.scan_availability_score),
            "trace_apex_intensity": _format_float(metrics.trace_apex_intensity),
            "trace_baseline_noise": _format_float(metrics.trace_baseline_noise),
            "trace_signal_to_noise_proxy": _format_float(metrics.trace_signal_to_noise_proxy),
            "trace_apex_prominence_score": _format_float(metrics.trace_apex_prominence_score),
            "scan_support_basis": "scan_count_only",
            "neighbor_interference_ratio": "",
            "neighbor_interference_status": "not_assessed",
```

- [ ] **Step 7: Run producer tests**

Run:

```powershell
python -m pytest tests\test_tier2_raw_trace_producer.py -q
```

Expected: producer unit tests pass after Task 3 is complete; before Task 3,
coherence-view assertions may still fail.

---

### Task 3: Implement Boundary And Apex Diagnostic Views

**Files:**
- Modify: `xic_extractor/alignment/tier2_trace_producer.py`

- [ ] **Step 1: Add apex span helpers**

Add:

```python
def _seed_rescued_apex_span_sec(
    seed_metrics: _TraceMetrics,
    rescue_metrics: Sequence[_TraceMetrics],
) -> float | None:
    if not rescue_metrics:
        return None
    return max(
        abs(seed_metrics.tier2_apex_rt - item.tier2_apex_rt) * 60.0
        for item in rescue_metrics
    )


def _rescued_only_apex_span_sec(
    rescue_metrics: Sequence[_TraceMetrics],
) -> float | None:
    if len(rescue_metrics) < 2:
        return None
    values = [item.tier2_apex_rt for item in rescue_metrics]
    return (max(values) - min(values)) * 60.0
```

- [ ] **Step 2: Add boundary reference helpers**

Add:

```python
def _rescued_pairwise_boundary_overlap_min(
    rescue_metrics: Sequence[_TraceMetrics],
) -> float | None:
    if len(rescue_metrics) < 2:
        return None
    values = [
        _boundary_overlap_fraction(first, second)
        for index, first in enumerate(rescue_metrics)
        for second in rescue_metrics[index + 1 :]
    ]
    return min(values) if values else None


def _family_consensus_boundary_overlap_min(
    seed_metrics: _TraceMetrics,
    rescue_metrics: Sequence[_TraceMetrics],
) -> float | None:
    metrics = (seed_metrics, *tuple(rescue_metrics))
    if len(metrics) < 2:
        return None
    consensus_start = _median(tuple(item.boundary_start_rt for item in metrics))
    consensus_end = _median(tuple(item.boundary_end_rt for item in metrics))
    if consensus_start >= consensus_end:
        return 0.0
    consensus = _TraceMetrics(
        cell_apex_rt=seed_metrics.cell_apex_rt,
        tier2_apex_rt=seed_metrics.tier2_apex_rt,
        apex_delta_sec=seed_metrics.apex_delta_sec,
        scan_support_score=seed_metrics.scan_support_score,
        scan_availability_score=seed_metrics.scan_availability_score,
        trace_scan_count=seed_metrics.trace_scan_count,
        boundary_start_rt=consensus_start,
        boundary_end_rt=consensus_end,
        boundary_width_sec=(consensus_end - consensus_start) * 60.0,
        trace_apex_intensity=seed_metrics.trace_apex_intensity,
        trace_baseline_noise=seed_metrics.trace_baseline_noise,
        trace_signal_to_noise_proxy=seed_metrics.trace_signal_to_noise_proxy,
        trace_apex_prominence_score=seed_metrics.trace_apex_prominence_score,
    )
    return min(_boundary_overlap_fraction(consensus, item) for item in metrics)
```

- [ ] **Step 3: Populate v0.1 row context**

After current `apex_span_sec` and `boundary_overlap_min` calculations, compute:

```python
    seed_rescued_apex_span_sec = _seed_rescued_apex_span_sec(
        seed_metrics,
        rescue_metrics,
    )
    rescued_only_apex_span_sec = _rescued_only_apex_span_sec(rescue_metrics)
    rescued_pairwise_boundary_overlap_min = _rescued_pairwise_boundary_overlap_min(
        rescue_metrics
    )
    family_consensus_boundary_overlap_min = _family_consensus_boundary_overlap_min(
        seed_metrics,
        rescue_metrics,
    )
```

Update `base.update()`:

```python
            "seed_rescued_boundary_overlap_min": _format_float(boundary_overlap_min),
            "rescued_pairwise_boundary_overlap_min": _format_float(
                rescued_pairwise_boundary_overlap_min
            ),
            "family_consensus_boundary_overlap_min": _format_float(
                family_consensus_boundary_overlap_min
            ),
            "seed_rescued_apex_span_sec": _format_float(seed_rescued_apex_span_sec),
            "rescued_only_apex_span_sec": _format_float(rescued_only_apex_span_sec),
```

Keep the legacy `rescued_apex_rt_span_sec` and
`rescued_boundary_overlap_min` columns populated for backward readability.

- [ ] **Step 4: Demote v0.1 coherence failures to diagnostic context**

For v0.1, do not return a `validated` positive-support row. Replace the final
validated block with:

```python
    base.update(
        {
            "evidence_status": "inconclusive",
            "support_component": "",
            "raw_trace_reread_status": "pass",
            "coherence_status": "inconclusive",
            "challenge_blockers": ";".join(
                _ordered_tokens(
                    (
                        "tier2_v0_1_diagnostic_only",
                        *coherence_blockers,
                        *tuple(sorted(set(rescue_blockers))),
                    )
                )
            ),
            "dependent_context": (
                "neighbor_interference_not_assessed;"
                "raw_trace_reread_v0_1;"
                "rescued_coherence_v0_1"
            ),
        }
    )
```

Keep seed trace unavailability and hard trace metric failures conservative:
`raw_unavailable` stays `inconclusive`; malformed trace metrics may stay
`blocked` or `inconclusive` according to the current helper.

- [ ] **Step 5: Run producer tests**

Run:

```powershell
python -m pytest tests\test_tier2_raw_trace_producer.py -q
```

Expected: all producer unit tests pass.

---

### Task 4: Gate V0.1 As Diagnostic Context

**Files:**
- Modify: `xic_extractor/alignment/production_candidate_gate.py`
- Modify: `tests/test_production_candidate_gate.py`
- Modify: `tests/test_provisional_backfill_candidate_gate_cli.py`

- [ ] **Step 1: Add v0.1 gate unit test**

Add to `tests/test_production_candidate_gate.py`:

```python
def test_v0_1_tier2_sidecar_is_diagnostic_only(tmp_path: Path) -> None:
    evidence, review_row, source_context = _load_tier2_fixture(
        tmp_path,
        criteria_version="tier2_trace_identity_rescued_coherence_v0_1_diagnostic",
        producer_version="raw_trace_reread_tier2_v0_1",
        evidence_status="inconclusive",
        support_component="",
        raw_trace_reread_status="pass",
        coherence_status="inconclusive",
        challenge_blockers="tier2_v0_1_diagnostic_only",
        dependent_context="neighbor_interference_not_assessed;raw_trace_reread_v0_1;rescued_coherence_v0_1",
        row_overrides={
            "scan_availability_score": "1.0",
            "trace_apex_intensity": "1000",
            "trace_baseline_noise": "10",
            "trace_signal_to_noise_proxy": "20",
            "trace_apex_prominence_score": "0.75",
            "scan_support_basis": "scan_count_only",
            "seed_rescued_boundary_overlap_min": "0.8",
            "rescued_pairwise_boundary_overlap_min": "0.85",
            "family_consensus_boundary_overlap_min": "0.82",
            "seed_rescued_apex_span_sec": "6",
            "rescued_only_apex_span_sec": "3",
            "neighbor_interference_status": "not_assessed",
        },
    )

    decision = evaluate_production_candidate_gate(
        review_row,
        _cell_rows(detected=1, rescued=2),
        source_context=source_context,
        tier2_evidence=evidence,
    )

    assert decision.candidate_gate_status == "audit"
    assert decision.evidence_tier == 1
    assert decision.support_components == ()
    assert decision.tier2_evidence_available is False
    assert "tier2_v0_1_diagnostic_only" in decision.challenge_blockers
```

If `_load_tier2_fixture()` does not support `row_overrides`, extend it with:

```python
    row_overrides: dict[str, str] | None = None,
    omitted_columns: tuple[str, ...] = (),
    sidecar_columns: tuple[str, ...] | None = None,
```

and pass those options into `_write_tier2_sidecar()`. Extend
`_write_tier2_sidecar()` with matching arguments:

```python
    omitted_columns: tuple[str, ...] = (),
    row_overrides: dict[str, str] | None = None,
    sidecar_columns: tuple[str, ...] | None = None,
```

Then choose columns with:

```python
    columns = [
        column
        for column in (sidecar_columns or tuple(row))
        if column not in omitted_columns
    ]
```

- [ ] **Step 2: Add v0/v0.1 compatibility and spoofing tests**

Import these constants in `tests/test_production_candidate_gate.py`:

```python
    TIER2_CRITERIA_V0_1,
    TIER2_TRACE_EVIDENCE_V0_COLUMNS,
    TIER2_TRACE_EVIDENCE_V0_1_COLUMNS,
```

Add helper:

```python
def _v0_1_row_overrides() -> dict[str, str]:
    return {
        "scan_availability_score": "1.0",
        "trace_apex_intensity": "1000",
        "trace_baseline_noise": "10",
        "trace_signal_to_noise_proxy": "20",
        "trace_apex_prominence_score": "0.75",
        "scan_support_basis": "scan_count_only",
        "seed_rescued_boundary_overlap_min": "0.8",
        "rescued_pairwise_boundary_overlap_min": "0.85",
        "family_consensus_boundary_overlap_min": "0.82",
        "seed_rescued_apex_span_sec": "6",
        "rescued_only_apex_span_sec": "3",
        "neighbor_interference_status": "not_assessed",
    }
```

Add:

```python
def test_legacy_v0_sidecar_with_v0_columns_still_promotes(
    tmp_path: Path,
) -> None:
    evidence, review_row, source_context = _load_tier2_fixture(
        tmp_path,
        sidecar_columns=TIER2_TRACE_EVIDENCE_V0_COLUMNS,
    )

    decision = evaluate_production_candidate_gate(
        review_row,
        _cell_rows(detected=1, rescued=2),
        source_context=source_context,
        tier2_evidence=evidence,
    )

    assert decision.candidate_gate_status == "production_candidate"
    assert decision.support_components == (TIER2_SUPPORT_COMPONENT,)
    assert decision.tier2_evidence_available is True
```

Add:

```python
def test_v0_1_sidecar_missing_new_column_is_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="trace_apex_intensity"):
        _load_tier2_fixture(
            tmp_path,
            criteria_version=TIER2_CRITERIA_V0_1,
            producer_version="raw_trace_reread_tier2_v0_1",
            evidence_status="inconclusive",
            support_component="",
            raw_trace_reread_status="pass",
            coherence_status="inconclusive",
            row_overrides=_v0_1_row_overrides(),
            sidecar_columns=TIER2_TRACE_EVIDENCE_V0_1_COLUMNS,
            omitted_columns=("trace_apex_intensity",),
        )
```

Add:

```python
def test_v0_1_gate_adds_diagnostic_only_blocker_when_row_omits_it(
    tmp_path: Path,
) -> None:
    evidence, review_row, source_context = _load_tier2_fixture(
        tmp_path,
        criteria_version=TIER2_CRITERIA_V0_1,
        producer_version="raw_trace_reread_tier2_v0_1",
        evidence_status="inconclusive",
        support_component="",
        raw_trace_reread_status="pass",
        coherence_status="inconclusive",
        challenge_blockers="",
        dependent_context="neighbor_interference_not_assessed;raw_trace_reread_v0_1;rescued_coherence_v0_1",
        row_overrides=_v0_1_row_overrides(),
        sidecar_columns=TIER2_TRACE_EVIDENCE_V0_1_COLUMNS,
    )

    decision = evaluate_production_candidate_gate(
        review_row,
        _cell_rows(detected=1, rescued=2),
        source_context=source_context,
        tier2_evidence=evidence,
    )

    assert decision.candidate_gate_status == "audit"
    assert decision.support_components == ()
    assert "tier2_v0_1_diagnostic_only" in decision.challenge_blockers
```

Add:

```python
def test_v0_1_validated_support_spoof_cannot_promote(
    tmp_path: Path,
) -> None:
    evidence, review_row, source_context = _load_tier2_fixture(
        tmp_path,
        criteria_version=TIER2_CRITERIA_V0_1,
        producer_version="raw_trace_reread_tier2_v0_1",
        evidence_status="validated",
        support_component=TIER2_SUPPORT_COMPONENT,
        raw_trace_reread_status="pass",
        coherence_status="pass",
        challenge_blockers="",
        dependent_context="neighbor_interference_not_assessed;raw_trace_reread_v0_1;rescued_coherence_v0_1",
        row_overrides=_v0_1_row_overrides(),
        sidecar_columns=TIER2_TRACE_EVIDENCE_V0_1_COLUMNS,
    )

    decision = evaluate_production_candidate_gate(
        review_row,
        _cell_rows(detected=1, rescued=2),
        source_context=source_context,
        tier2_evidence=evidence,
    )

    assert decision.candidate_gate_status == "audit"
    assert decision.evidence_tier == 1
    assert decision.support_components == ()
    assert decision.tier2_evidence_available is False
    assert "tier2_v0_1_diagnostic_only" in decision.challenge_blockers
```

- [ ] **Step 3: Add v0.1 CLI consume test**

Add to `tests/test_provisional_backfill_candidate_gate_cli.py`:

```python
def test_cli_consumes_v0_1_sidecar_as_diagnostic_only(tmp_path: Path) -> None:
    alignment_dir = _write_alignment_run(tmp_path / "alignment")
    output_dir = tmp_path / "gate"
    raw_manifest_path = _write_raw_manifest(tmp_path)
    source_context = gate_cli.source_context_for_artifacts(
        review_path=alignment_dir / "alignment_review.tsv",
        cell_path=alignment_dir / "alignment_cells.tsv",
        matrix_path=alignment_dir / "alignment_matrix.tsv",
    )
    review_rows = _read_tsv(alignment_dir / "alignment_review.tsv")
    candidate_rows = [
        row for row in review_rows if gate_cli.is_candidate_gate_scope(row)
    ]
    sidecar_path = _write_tier2_sidecar(
        tmp_path,
        family_id="FAM_CAND",
        candidate_rows=candidate_rows,
        source_context=source_context,
        raw_manifest_path=raw_manifest_path,
        criteria_version="tier2_trace_identity_rescued_coherence_v0_1_diagnostic",
        producer_version="raw_trace_reread_tier2_v0_1",
        evidence_status="inconclusive",
        support_component="",
        raw_trace_reread_status="pass",
        coherence_status="inconclusive",
        challenge_blockers="tier2_v0_1_diagnostic_only",
    )

    code = gate_cli.main(
        [
            "--alignment-dir",
            str(alignment_dir),
            "--output-dir",
            str(output_dir),
            "--tier2-trace-evidence-tsv",
            str(sidecar_path),
            "--tier2-raw-manifest-tsv",
            str(raw_manifest_path),
        ],
    )

    assert code == 0
    rows = _read_tsv(output_dir / "alignment_production_candidate_gate.tsv")
    by_id = {row["feature_family_id"]: row for row in rows}
    assert by_id["FAM_CAND"]["candidate_gate_status"] == "audit"
    assert by_id["FAM_CAND"]["support_components"] == ""
    assert "tier2_v0_1_diagnostic_only" in by_id["FAM_CAND"]["challenge_blockers"]
    payload = json.loads(
        (output_dir / "alignment_production_candidate_gate.json").read_text(
            encoding="utf-8",
        )
    )
    assert payload["production_candidate_count"] == 0
    assert payload["production_ready"] is False
```

Extend the local `_write_tier2_sidecar()` helper with keyword overrides matching
the test signature and append the v0.1 columns listed in the Public Contract.

- [ ] **Step 4: Run gate tests**

Run:

```powershell
python -m pytest tests\test_production_candidate_gate.py tests\test_provisional_backfill_candidate_gate_cli.py -q
```

Expected: all gate and CLI tests pass.

---

### Task 5: Diagnostic Docs And 8RAW Rerun

**Files:**
- Modify: `tools/diagnostics/INDEX.md`
- Create: `docs/superpowers/notes/2026-05-29-tier2-v0-coherence-diagnostic-validation-note.md`

- [ ] **Step 1: Update diagnostic index**

In `tools/diagnostics/INDEX.md`, update the
`tier2_raw_trace_reread_producer.py` entry status note to include:

```markdown
**Status note**: Writes diagnostic-only v0.1 Tier 2 RAW trace evidence and RAW
manifest sidecars. The v0.1 criteria expose scan availability, signal/noise,
shape, boundary-reference, apex-span, and neighbor-interference context, but do
not provide positive Tier 2 support or change `alignment_matrix.tsv`. 85RAW is
out of scope until a reviewed follow-up plan is approved after a successful
v0.1 8RAW diagnostic rerun.
```

- [ ] **Step 2: Run focused tests and lint**

Run:

```powershell
python -m pytest tests\test_tier2_raw_trace_producer.py tests\test_tier2_raw_trace_reread_producer_cli.py tests\test_production_candidate_gate.py tests\test_provisional_backfill_candidate_gate_cli.py tests\test_alignment_tsv_writer.py::test_direct_tier2_review_token_does_not_change_matrix_writer -q
```

Expected: all selected tests pass.

Run:

```powershell
python -m ruff check xic_extractor\alignment\tier2_trace_producer.py xic_extractor\alignment\production_candidate_gate.py tools\diagnostics\tier2_raw_trace_reread_producer.py tools\diagnostics\provisional_backfill_candidate_gate.py tests\test_tier2_raw_trace_producer.py tests\test_tier2_raw_trace_reread_producer_cli.py tests\test_production_candidate_gate.py tests\test_provisional_backfill_candidate_gate_cli.py tests\test_alignment_tsv_writer.py
```

Expected:

```text
All checks passed!
```

- [ ] **Step 3: Rerun 8RAW v0.1 producer**

Run with the RAW-capable `.venv` runner:

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.tier2_raw_trace_reread_producer `
  --alignment-dir output\tiered_backfill_candidate_gate_8raw_current `
  --output-dir output\tier2_v0_1_coherence_8raw_current `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation `
  --dll-dir C:\Xcalibur\system\programs `
  --expected-sample-count 8
```

Expected:

- `alignment_tier2_trace_evidence.tsv`
- `alignment_tier2_raw_manifest.tsv`
- `alignment_tier2_trace_evidence_summary.json`
- summary contains `readiness_label=diagnostic_only`,
  `criteria_version=tier2_trace_identity_rescued_coherence_v0_1_diagnostic`,
  `producer_version=raw_trace_reread_tier2_v0_1`,
  `production_ready=false`, `matrix_contract_changed=false`, and
  `positive_support_count=0`.

- [ ] **Step 4: Consume v0.1 sidecar through gate**

Run:

```powershell
python -m tools.diagnostics.provisional_backfill_candidate_gate `
  --alignment-dir output\tiered_backfill_candidate_gate_8raw_current `
  --output-dir output\tier2_v0_1_coherence_8raw_current_gate `
  --tier2-trace-evidence-tsv output\tier2_v0_1_coherence_8raw_current\alignment_tier2_trace_evidence.tsv `
  --tier2-raw-manifest-tsv output\tier2_v0_1_coherence_8raw_current\alignment_tier2_raw_manifest.tsv
```

Inspect:

```powershell
python -c "import json; p='output/tier2_v0_1_coherence_8raw_current_gate/alignment_production_candidate_gate.json'; d=json.load(open(p, encoding='utf-8')); print(d['readiness_label'], d['row_count'], d['production_candidate_count'], d['production_ready'], d['matrix_contract_changed'])"
```

Expected:

```text
diagnostic_only 7 0 False False
```

- [ ] **Step 5: Write validation note**

Create:

```markdown
# Tier 2 V0.1 Coherence Diagnostic Validation Note

## Verdict

`diagnostic_only`

This checkpoint implements the v0.1 Tier 2 RAW trace coherence diagnostic
sidecar pilot. It exposes richer evidence context but does not promote retained
provisional rows, does not change `alignment_matrix.tsv`, and does not make
Tier 2 evidence production-ready.

## Verification

```text
Focused pytest: actual command summary from this run.
Ruff: actual command summary from this run.
8RAW v0.1 producer: actual command summary from this run.
8RAW v0.1 gate consume: actual command summary from this run.
```

## 8RAW Summary

- Producer readiness:
- Producer statuses:
- Gate readiness:
- Gate status counts:
- Positive support count:

## Contract State

- v0.1 criteria version:
  `tier2_trace_identity_rescued_coherence_v0_1_diagnostic`.
- v0.1 sidecars are diagnostic context only.
- Scan count is separated from signal/shape/noise context.
- Boundary overlap exposes seed-vs-rescued, rescued-pairwise, and family
  consensus views.
- Apex span exposes raw, seed-to-rescued, and rescued-only views.
- Neighbor interference remains `not_assessed` context.

## Remaining Risk

The current 8RAW retained subset is small and biased toward retained
provisional rows. It is sufficient for diagnostic observability and criteria
failure-mode review, not production readiness or 85RAW promotion.
```

Replace the summary sentences with the observed command output before
completion.

- [ ] **Step 6: Docs smoke and diff check**

Run:

```powershell
$placeholderPattern = ("paste ob" + "ser" + "ved|<ob" + "serv" + "ed|<pa" + "ste|TB" + "D|TO" + "DO")
rg -n $placeholderPattern docs\superpowers\notes\2026-05-29-tier2-v0-coherence-diagnostic-validation-note.md
rg -n "[ \t]+$" docs\superpowers\plans\2026-05-29-tier2-v0-coherence-diagnostic-goal.md docs\superpowers\plans\2026-05-29-tier2-v0-coherence-diagnostic-plan.md docs\superpowers\notes\2026-05-29-tier2-v0-coherence-diagnostic-validation-note.md
git diff --check -- xic_extractor\alignment\tier2_trace_producer.py xic_extractor\alignment\production_candidate_gate.py tools\diagnostics\tier2_raw_trace_reread_producer.py tools\diagnostics\provisional_backfill_candidate_gate.py tests\test_tier2_raw_trace_producer.py tests\test_tier2_raw_trace_reread_producer_cli.py tests\test_production_candidate_gate.py tests\test_provisional_backfill_candidate_gate_cli.py tests\test_alignment_tsv_writer.py tools\diagnostics\INDEX.md docs\superpowers\specs\2026-05-29-tier2-v0-coherence-criteria-review-design.md docs\superpowers\plans\2026-05-29-tier2-v0-coherence-diagnostic-goal.md docs\superpowers\plans\2026-05-29-tier2-v0-coherence-diagnostic-plan.md docs\superpowers\notes\2026-05-29-tier2-v0-coherence-diagnostic-validation-note.md
```

Expected:

- first `rg` exits `1` with no matches after placeholders are filled;
- second `rg` exits `1` with no trailing whitespace;
- `git diff --check` exits `0`.

---

## Final Verification

Run:

```powershell
python -m pytest tests\test_tier2_raw_trace_producer.py tests\test_tier2_raw_trace_reread_producer_cli.py tests\test_production_candidate_gate.py tests\test_provisional_backfill_candidate_gate_cli.py tests\test_alignment_tsv_writer.py::test_direct_tier2_review_token_does_not_change_matrix_writer -q

python -m ruff check xic_extractor\alignment\tier2_trace_producer.py xic_extractor\alignment\production_candidate_gate.py tools\diagnostics\tier2_raw_trace_reread_producer.py tools\diagnostics\provisional_backfill_candidate_gate.py tests\test_tier2_raw_trace_producer.py tests\test_tier2_raw_trace_reread_producer_cli.py tests\test_production_candidate_gate.py tests\test_provisional_backfill_candidate_gate_cli.py tests\test_alignment_tsv_writer.py

git diff --check -- xic_extractor\alignment\tier2_trace_producer.py xic_extractor\alignment\production_candidate_gate.py tools\diagnostics\tier2_raw_trace_reread_producer.py tools\diagnostics\provisional_backfill_candidate_gate.py tests\test_tier2_raw_trace_producer.py tests\test_tier2_raw_trace_reread_producer_cli.py tests\test_production_candidate_gate.py tests\test_provisional_backfill_candidate_gate_cli.py tests\test_alignment_tsv_writer.py tools\diagnostics\INDEX.md docs\superpowers\specs\2026-05-29-tier2-v0-coherence-criteria-review-design.md docs\superpowers\plans\2026-05-29-tier2-v0-coherence-diagnostic-goal.md docs\superpowers\plans\2026-05-29-tier2-v0-coherence-diagnostic-plan.md docs\superpowers\notes\2026-05-29-tier2-v0-coherence-diagnostic-validation-note.md
```

Acceptance:

- v0.1 sidecar rows include the expanded diagnostic metric columns.
- v0.1 rows cannot produce positive Tier 2 support or `production_candidate`.
- Current v0 artifacts remain readable for compatibility.
- `alignment_matrix.tsv` and workbook contracts remain unchanged.
- 8RAW v0.1 producer and gate consume outputs are `diagnostic_only`, with
  `production_ready=false`, `matrix_contract_changed=false`, and zero production
  candidates.
- No 85RAW command was run.

## Stop Rules

- Stop if implementation requires changing `alignment_matrix.tsv`, workbook
  schemas, `scripts.run_alignment` defaults, output levels, or primary matrix
  row inclusion semantics.
- Stop if v0.1 positive support can only be justified by owner-backfill
  provenance, scan count alone, direct review-row tokens, or uncomputed neighbor
  interference.
- Stop if current 8RAW precondition hashes do not match.
- Stop before launching 85RAW or any likely >30 minute RAW/DLL run.
- Stop after three failed attempts on the same symptom and revisit the
  root-cause hypothesis.

## Self-Review

Spec coverage:

- `scan_support_score` split is covered by Tasks 1-2.
- Boundary-reference ambiguity is covered by Task 3.
- Apex-span drift risk is covered by Task 3 and kept diagnostic-only.
- Neighbor interference is context-only in Tasks 2 and 4.
- No production promotion and no 85RAW are covered by the checkpoint boundary,
  goal constraints, Task 5, and stop rules.

Placeholder scan:

- The only placeholders are inside the validation-note template in Task 5 and
  are explicitly required to be replaced before completion.

Type consistency:

- `TIER2_CRITERIA_V0_1`, `TIER2_TRACE_EVIDENCE_V0_1_COLUMNS`,
  `_read_tsv_versioned_tier2_sidecar`, and the new diagnostic columns are
  defined before use in tests, producer, and CLI helpers.
