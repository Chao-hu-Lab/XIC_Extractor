# Tier 2 Sidecar Provenance Gate Checkpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans in checkpoint mode to implement this plan task-by-task. `superpowers:subagent-driven-development` is not the default for this checkpoint because the write surface is a tightly coupled gate/CLI/test contract; use a tester subagent only after implementation if verification integrity becomes the dominant risk. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first executable checkpoint of the Tier 2 evidence producer contract by making the provisional backfill candidate gate accept positive support only from a provenance-validated Tier 2 sidecar, not from `alignment_review.tsv` direct tokens.

**Architecture:** Keep `xic_extractor/alignment/production_candidate_gate.py` as the pure domain owner for candidate eligibility and final status projection, and add a small Tier 2 sidecar contract model/loader inside that module. Keep `tools/diagnostics/provisional_backfill_candidate_gate.py` as the IO facade that reads alignment artifacts plus optional Tier 2 sidecar/RAW manifest paths, validates provenance, then writes the existing diagnostic gate TSV/JSON. This checkpoint does not implement RAW trace re-reading; it creates the sidecar-only gate contract that a later RAW producer must satisfy.

**Tech Stack:** Python 3, `csv`, `json`, `hashlib`, `dataclasses`, `pathlib`, existing `tools.diagnostics.diagnostic_io`, pytest, ruff.

---

## Checkpoint Boundary

Implement now:

- Sidecar-only positive support for `validated_tier2_trace_evidence`.
- Provenance checks for source review/cells hashes, RAW manifest hash, candidate subset hash/count, criteria version, and producer version.
- CLI flags:
  - `--tier2-trace-evidence-tsv <path>`
  - `--tier2-raw-manifest-tsv <path>`
- Regression coverage proving direct `alignment_review.tsv` tokens cannot promote a row.
- Existing no-sidecar behavior remains conservative and compatible.

Do not implement now:

- RAW trace re-read producer.
- RAW file scanning, Thermo DLL use, 8RAW/85RAW long runs, or EIC/manual review import.
- Primary matrix promotion, workbook schema changes, or `scripts.run_alignment` default output changes.

Exit from this checkpoint is `diagnostic_only`: the gate can consume a valid Tier 2 sidecar fixture, but the producer that creates real RAW-backed sidecars remains a separate checkpoint.

## File Structure

Modify:

- `xic_extractor/alignment/production_candidate_gate.py`
  - Add Tier 2 sidecar constants, required columns, `Tier2TraceEvidence`, `Tier2EvidenceContext`, candidate subset signature helper, sidecar loader, and positive-support predicate.
  - Change `evaluate_production_candidate_gate()` to accept optional sidecar evidence and ignore direct review-row `independent_tier2_support_components` for promotion.

- `tools/diagnostics/provisional_backfill_candidate_gate.py`
  - Add paired Tier 2 sidecar/RAW manifest CLI flags.
  - Load and validate sidecar evidence once, pass matching row evidence into the evaluator, and add Tier 2 provenance summary fields to JSON when supplied.

- `tests/test_production_candidate_gate.py`
  - Replace direct-token promotion expectations with sidecar-only expectations.
  - Add unit tests for valid full-schema sidecar promotion, direct-token non-promotion, stale source hash, stale RAW manifest hash, candidate subset mismatch, unknown criteria, unknown producer, missing support component, RAW/coherence non-pass status, missing or blank v0 metrics, inconclusive sidecar, hard blocker, and targeted/dependent-only context.

- `tests/test_provisional_backfill_candidate_gate_cli.py`
  - Add CLI tests for paired Tier 2 args, valid sidecar promotion, missing paired arg failure, and stale provenance emitting machine-readable blockers.

- `tests/test_alignment_tsv_writer.py`
  - Update the matrix guard so it no longer asserts direct review-row token promotion.

- `tools/diagnostics/INDEX.md`
  - Update the existing `provisional_backfill_candidate_gate.py` entry to mention optional Tier 2 sidecar provenance inputs and sidecar-only support.

Create:

- `docs/superpowers/notes/2026-05-29-tier2-sidecar-provenance-gate-checkpoint-validation-note.md`
  - Short validation note with final test commands and explicit `diagnostic_only` limitation.

## Contract Constants

Add these constants to `xic_extractor/alignment/production_candidate_gate.py`:

```python
TIER2_SUPPORT_COMPONENT = "validated_tier2_trace_evidence"
TIER2_ALLOWED_CRITERIA_VERSIONS = frozenset(
    {"tier2_trace_identity_rescued_coherence_v0"}
)
TIER2_RECOGNIZED_PRODUCER_VERSIONS = frozenset({"raw_trace_reread_tier2_v0"})
TIER2_TRACE_EVIDENCE_REQUIRED_COLUMNS = (
    "feature_family_id",
    "evidence_status",
    "support_component",
    "criteria_version",
    "producer_version",
    "raw_trace_reread_status",
    "seed_apex_rt",
    "tier2_apex_rt",
    "apex_delta_sec",
    "scan_support_score",
    "trace_scan_count",
    "boundary_start_rt",
    "boundary_end_rt",
    "boundary_width_sec",
    "neighbor_interference_ratio",
    "rescued_cell_count_checked",
    "rescued_cell_count_supported",
    "rescued_apex_rt_span_sec",
    "rescued_boundary_overlap_min",
    "coherence_status",
    "challenge_blockers",
    "dependent_context",
    "source_alignment_review_sha256",
    "source_alignment_cells_sha256",
    "source_raw_manifest_sha256",
    "source_candidate_subset_sha256",
    "source_candidate_subset_count",
    "source_expected_sample_count",
    "raw_reader_runtime",
    "python_executable",
    "dll_dir",
    "producer_command",
    "generated_at_utc",
)
TIER2_GATE_JOIN_COLUMNS = (
    "feature_family_id",
    "evidence_status",
    "support_component",
    "criteria_version",
    "producer_version",
    "source_alignment_review_sha256",
    "source_alignment_cells_sha256",
    "source_raw_manifest_sha256",
    "source_candidate_subset_sha256",
    "source_candidate_subset_count",
)
TIER2_RAW_MANIFEST_REQUIRED_COLUMNS = (
    "sample_stem",
    "raw_file_path",
    "raw_file_size_bytes",
    "raw_file_mtime_utc",
    "raw_reader_runtime",
    "python_executable",
    "dll_dir",
)
TIER2_CANDIDATE_SUBSET_FIELDS = (
    "feature_family_id",
    "identity_decision",
    "quantifiable_detected_count",
    "quantifiable_rescue_count",
    "duplicate_assigned_count",
    "ambiguous_ms1_owner_count",
    "row_flags",
)
```

`TIER2_TRACE_EVIDENCE_REQUIRED_COLUMNS` is the full v0 sidecar schema required
for any sidecar file the gate consumes. `TIER2_GATE_JOIN_COLUMNS` is only an
internal convenience list for provenance-focused assertions; it must never be
used to accept a sidecar file with missing RAW trace or rescued-cell coherence
metrics. A sidecar with correct hashes and `validated/pass/pass` but missing or
blank v0 metric fields is invalid for promotion.

---

### Task 1: Pin Sidecar-Only Behavior In Unit Tests

**Files:**
- Modify: `tests/test_production_candidate_gate.py`

- [ ] **Step 1: Add failing direct-token regression**

Replace `test_retention_candidate_with_explicit_independent_tier2_support_tracks_candidate` with:

```python
def test_direct_review_row_tier2_token_does_not_promote_without_sidecar(
    tmp_path: Path,
) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    decision = evaluate_production_candidate_gate(
        _review_row(
            flags=(
                "single_detected_seed;provisional_retention_candidate;"
                "skip_expensive_evidence"
            ),
            detected=1,
            rescued=2,
            independent_support="validated_tier2_trace_evidence",
        ),
        _cell_rows(detected=1, rescued=2),
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cell_path,
            matrix_path=matrix_path,
        ),
    )

    assert decision.candidate_gate_status == "keep_provisional"
    assert decision.evidence_tier == 1
    assert decision.support_components == ()
    assert decision.tier2_evidence_available is False
    assert "missing_positive_tier2_support" in decision.challenge_blockers
```

- [ ] **Step 2: Add valid sidecar fixture helper and promotion test**

Add `import hashlib` and `import pytest` at the top of the test file. Import
the new helper names, then add:

```python
from xic_extractor.alignment.production_candidate_gate import (
    TIER2_SUPPORT_COMPONENT,
    load_tier2_trace_evidence,
    tier2_candidate_subset_signature,
)
```

Add this test:

```python
def test_valid_tier2_sidecar_support_tracks_candidate(tmp_path: Path) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    review_row = _review_row(
        flags="single_detected_seed;provisional_retention_candidate",
        detected=1,
        rescued=2,
    )
    source_context = source_context_for_artifacts(
        review_path=review_path,
        cell_path=cell_path,
        matrix_path=matrix_path,
    )
    raw_manifest_path = _write_raw_manifest(tmp_path)
    sidecar_path = _write_tier2_sidecar(
        tmp_path,
        review_rows=(review_row,),
        source_context=source_context,
        raw_manifest_path=raw_manifest_path,
        evidence_status="validated",
        support_component=TIER2_SUPPORT_COMPONENT,
        raw_trace_reread_status="pass",
        coherence_status="pass",
    )
    evidence_by_family = load_tier2_trace_evidence(
        sidecar_path=sidecar_path,
        raw_manifest_path=raw_manifest_path,
        candidate_rows=(review_row,),
        source_context=source_context,
    )

    decision = evaluate_production_candidate_gate(
        review_row,
        _cell_rows(detected=1, rescued=2),
        source_context=source_context,
        tier2_evidence=evidence_by_family["FAM001"],
    )

    assert decision.candidate_gate_status == "production_candidate"
    assert decision.evidence_tier == 2
    assert decision.support_components == (TIER2_SUPPORT_COMPONENT,)
    assert decision.tier2_evidence_available is True
    assert decision.challenge_blockers == ()
```

- [ ] **Step 3: Add negative Tier 2 sidecar tests**

Add tests using the same fixture helper:

```python
def test_stale_tier2_source_hash_blocks_support(tmp_path: Path) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    review_row = _review_row(
        flags="single_detected_seed;provisional_retention_candidate",
        detected=1,
        rescued=2,
    )
    source_context = source_context_for_artifacts(
        review_path=review_path,
        cell_path=cell_path,
        matrix_path=matrix_path,
    )
    raw_manifest_path = _write_raw_manifest(tmp_path)
    sidecar_path = _write_tier2_sidecar(
        tmp_path,
        review_rows=(review_row,),
        source_context=source_context,
        raw_manifest_path=raw_manifest_path,
        source_review_sha256="0" * 64,
        evidence_status="validated",
        support_component=TIER2_SUPPORT_COMPONENT,
        raw_trace_reread_status="pass",
        coherence_status="pass",
    )
    evidence = load_tier2_trace_evidence(
        sidecar_path=sidecar_path,
        raw_manifest_path=raw_manifest_path,
        candidate_rows=(review_row,),
        source_context=source_context,
    )["FAM001"]

    decision = evaluate_production_candidate_gate(
        review_row,
        _cell_rows(detected=1, rescued=2),
        source_context=source_context,
        tier2_evidence=evidence,
    )

    assert decision.candidate_gate_status == "audit"
    assert decision.support_components == ()
    assert "source_hash_mismatch" in decision.challenge_blockers
```

```python
def test_unknown_tier2_criteria_version_blocks_support(tmp_path: Path) -> None:
    evidence, review_row, source_context = _load_tier2_fixture(
        tmp_path,
        criteria_version="future_criteria_v9",
    )

    decision = evaluate_production_candidate_gate(
        review_row,
        _cell_rows(detected=1, rescued=2),
        source_context=source_context,
        tier2_evidence=evidence,
    )

    assert decision.candidate_gate_status == "audit"
    assert "criteria_version_not_allowlisted" in decision.challenge_blockers
```

```python
def test_inconclusive_tier2_sidecar_does_not_promote(tmp_path: Path) -> None:
    evidence, review_row, source_context = _load_tier2_fixture(
        tmp_path,
        evidence_status="inconclusive",
        support_component="",
        challenge_blockers="metric_unavailable",
        raw_trace_reread_status="inconclusive",
        coherence_status="inconclusive",
    )

    decision = evaluate_production_candidate_gate(
        review_row,
        _cell_rows(detected=1, rescued=2),
        source_context=source_context,
        tier2_evidence=evidence,
    )

    assert decision.candidate_gate_status == "audit"
    assert decision.support_components == ()
    assert "metric_unavailable" in decision.challenge_blockers
```

```python
def test_tier2_hard_challenge_blocker_prevents_support(tmp_path: Path) -> None:
    evidence, review_row, source_context = _load_tier2_fixture(
        tmp_path,
        challenge_blockers="neighbor_interference",
    )

    decision = evaluate_production_candidate_gate(
        review_row,
        _cell_rows(detected=1, rescued=2),
        source_context=source_context,
        tier2_evidence=evidence,
    )

    assert decision.candidate_gate_status == "audit"
    assert decision.support_components == ()
    assert "neighbor_interference" in decision.challenge_blockers
```

```python
@pytest.mark.parametrize(
    ("overrides", "expected_blocker"),
    (
        ({"producer_version": "raw_trace_reread_tier2_v99"}, "producer_version_not_recognized"),
        ({"source_raw_manifest_sha256": "0" * 64}, "raw_manifest_hash_mismatch"),
        ({"source_candidate_subset_sha256": "0" * 64}, "candidate_subset_hash_mismatch"),
        ({"source_candidate_subset_count": "999"}, "candidate_subset_hash_mismatch"),
        ({"support_component": ""}, "missing_positive_tier2_support"),
        ({"raw_trace_reread_status": "fail"}, "raw_trace_reread_not_pass"),
        ({"coherence_status": "fail"}, "rescued_coherence_not_pass"),
        ({"scan_support_score": ""}, "metric_unavailable"),
    ),
)
def test_invalid_tier2_sidecar_fields_do_not_promote(
    tmp_path: Path,
    overrides: dict[str, str],
    expected_blocker: str,
) -> None:
    evidence, review_row, source_context = _load_tier2_fixture(
        tmp_path,
        **overrides,
    )

    decision = evaluate_production_candidate_gate(
        review_row,
        _cell_rows(detected=1, rescued=2),
        source_context=source_context,
        tier2_evidence=evidence,
    )

    assert decision.candidate_gate_status == "audit"
    assert decision.support_components == ()
    assert expected_blocker in decision.challenge_blockers
```

```python
def test_tier2_sidecar_missing_v0_metric_column_is_rejected(
    tmp_path: Path,
) -> None:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    review_row = _review_row(
        flags="single_detected_seed;provisional_retention_candidate",
        detected=1,
        rescued=2,
    )
    source_context = source_context_for_artifacts(
        review_path=review_path,
        cell_path=cell_path,
        matrix_path=matrix_path,
    )
    raw_manifest_path = _write_raw_manifest(tmp_path)
    sidecar_path = _write_tier2_sidecar(
        tmp_path,
        review_rows=(review_row,),
        source_context=source_context,
        raw_manifest_path=raw_manifest_path,
        evidence_status="validated",
        support_component=TIER2_SUPPORT_COMPONENT,
        raw_trace_reread_status="pass",
        coherence_status="pass",
        omitted_columns=("trace_scan_count",),
    )

    with pytest.raises(ValueError, match="trace_scan_count"):
        load_tier2_trace_evidence(
            sidecar_path=sidecar_path,
            raw_manifest_path=raw_manifest_path,
            candidate_rows=(review_row,),
            source_context=source_context,
        )
```

- [ ] **Step 4: Add fixture writers**

Add helper functions near existing test helpers:

```python
def _load_tier2_fixture(
    tmp_path: Path,
    *,
    evidence_status: str = "validated",
    support_component: str = TIER2_SUPPORT_COMPONENT,
    criteria_version: str = "tier2_trace_identity_rescued_coherence_v0",
    producer_version: str = "raw_trace_reread_tier2_v0",
    challenge_blockers: str = "",
    dependent_context: str = "",
    raw_trace_reread_status: str = "pass",
    coherence_status: str = "pass",
    source_raw_manifest_sha256: str | None = None,
    source_candidate_subset_sha256: str | None = None,
    source_candidate_subset_count: str | None = None,
    scan_support_score: str = "0.80",
) -> tuple[object, dict[str, str], object]:
    review_path, cell_path, matrix_path = _write_sources(tmp_path)
    review_row = _review_row(
        flags="single_detected_seed;provisional_retention_candidate",
        detected=1,
        rescued=2,
    )
    source_context = source_context_for_artifacts(
        review_path=review_path,
        cell_path=cell_path,
        matrix_path=matrix_path,
    )
    raw_manifest_path = _write_raw_manifest(tmp_path)
    sidecar_path = _write_tier2_sidecar(
        tmp_path,
        review_rows=(review_row,),
        source_context=source_context,
        raw_manifest_path=raw_manifest_path,
        evidence_status=evidence_status,
        support_component=support_component,
        criteria_version=criteria_version,
        producer_version=producer_version,
        challenge_blockers=challenge_blockers,
        dependent_context=dependent_context,
        raw_trace_reread_status=raw_trace_reread_status,
        coherence_status=coherence_status,
        source_raw_manifest_sha256=source_raw_manifest_sha256,
        source_candidate_subset_sha256=source_candidate_subset_sha256,
        source_candidate_subset_count=source_candidate_subset_count,
        scan_support_score=scan_support_score,
    )
    evidence = load_tier2_trace_evidence(
        sidecar_path=sidecar_path,
        raw_manifest_path=raw_manifest_path,
        candidate_rows=(review_row,),
        source_context=source_context,
    )["FAM001"]
    return evidence, review_row, source_context
```

```python
def _write_raw_manifest(tmp_path: Path) -> Path:
    path = tmp_path / "alignment_tier2_raw_manifest.tsv"
    path.write_text(
        (
            "sample_stem\traw_file_path\traw_file_size_bytes\t"
            "raw_file_mtime_utc\traw_reader_runtime\tpython_executable\tdll_dir\n"
            "S001\tC:\\Xcalibur\\data\\S001.raw\t123\t"
            "2026-05-29T00:00:00Z\tpythonnet\t.venv\\Scripts\\python.exe\t"
            "C:\\Xcalibur\\system\\programs\n"
        ),
        encoding="utf-8",
    )
    return path
```

```python
def _write_tier2_sidecar(
    tmp_path: Path,
    *,
    review_rows: tuple[dict[str, str], ...],
    source_context,
    raw_manifest_path: Path,
    evidence_status: str,
    support_component: str,
    criteria_version: str = "tier2_trace_identity_rescued_coherence_v0",
    producer_version: str = "raw_trace_reread_tier2_v0",
    challenge_blockers: str = "",
    dependent_context: str = "",
    raw_trace_reread_status: str = "pass",
    coherence_status: str = "pass",
    source_review_sha256: str | None = None,
    source_raw_manifest_sha256: str | None = None,
    source_candidate_subset_sha256: str | None = None,
    source_candidate_subset_count: str | None = None,
    scan_support_score: str = "0.80",
    omitted_columns: tuple[str, ...] = (),
) -> Path:
    subset = tier2_candidate_subset_signature(review_rows)
    row = {
        "feature_family_id": "FAM001",
        "evidence_status": evidence_status,
        "support_component": support_component,
        "criteria_version": criteria_version,
        "producer_version": producer_version,
        "raw_trace_reread_status": raw_trace_reread_status,
        "seed_apex_rt": "8.000",
        "tier2_apex_rt": "8.100",
        "apex_delta_sec": "6.0",
        "scan_support_score": scan_support_score,
        "trace_scan_count": "8",
        "boundary_start_rt": "7.950",
        "boundary_end_rt": "8.050",
        "boundary_width_sec": "6.0",
        "neighbor_interference_ratio": "0.10",
        "rescued_cell_count_checked": "2",
        "rescued_cell_count_supported": "2",
        "rescued_apex_rt_span_sec": "6.0",
        "rescued_boundary_overlap_min": "0.80",
        "coherence_status": coherence_status,
        "challenge_blockers": challenge_blockers,
        "dependent_context": dependent_context,
        "source_alignment_review_sha256": (
            source_review_sha256 or source_context.review_sha256
        ),
        "source_alignment_cells_sha256": source_context.cell_sha256,
        "source_raw_manifest_sha256": (
            source_raw_manifest_sha256 or _sha256_file(raw_manifest_path)
        ),
        "source_candidate_subset_sha256": (
            source_candidate_subset_sha256 or subset.sha256
        ),
        "source_candidate_subset_count": (
            source_candidate_subset_count or str(subset.count)
        ),
        "source_expected_sample_count": "8",
        "raw_reader_runtime": "pythonnet",
        "python_executable": ".venv\\Scripts\\python.exe",
        "dll_dir": "C:\\Xcalibur\\system\\programs",
        "producer_command": "synthetic-test-fixture",
        "generated_at_utc": "2026-05-29T00:00:00Z",
    }
    columns = [
        column
        for column in row
        if column not in omitted_columns
    ]
    path = tmp_path / "alignment_tier2_trace_evidence.tsv"
    path.write_text(
        "\n".join(
            (
                "\t".join(columns),
                "\t".join(row[column] for column in columns),
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return path
```

Add a local test helper:

```python
def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()
```

- [ ] **Step 5: Run the focused failing tests**

Run:

```powershell
python -m pytest tests\test_production_candidate_gate.py -q
```

Expected before implementation: at least one failure because `load_tier2_trace_evidence`, `tier2_candidate_subset_signature`, or `tier2_evidence` parameter does not exist.

---

### Task 2: Implement Tier 2 Sidecar Contract In The Domain Gate

**Files:**
- Modify: `xic_extractor/alignment/production_candidate_gate.py`
- Test: `tests/test_production_candidate_gate.py`

- [ ] **Step 1: Add contract dataclasses and signature helper**

Add after `ProductionCandidateGateDecision`:

```python
@dataclass(frozen=True)
class Tier2CandidateSubsetSignature:
    sha256: str
    count: int


@dataclass(frozen=True)
class Tier2TraceEvidence:
    feature_family_id: str
    evidence_status: str
    support_component: str
    criteria_version: str
    producer_version: str
    raw_trace_reread_status: str
    coherence_status: str
    challenge_blockers: tuple[str, ...]
    dependent_context: tuple[str, ...]
    provenance_blockers: tuple[str, ...]
    metric_blockers: tuple[str, ...]
```

Add:

```python
def tier2_candidate_subset_signature(
    candidate_rows: Sequence[Mapping[str, object]],
) -> Tier2CandidateSubsetSignature:
    normalized_lines = ["\t".join(TIER2_CANDIDATE_SUBSET_FIELDS)]
    for row in sorted(
        (_string_row(item) for item in candidate_rows),
        key=lambda item: item.get("feature_family_id", ""),
    ):
        normalized_lines.append(
            "\t".join(row.get(field, "") for field in TIER2_CANDIDATE_SUBSET_FIELDS)
        )
    payload = ("\n".join(normalized_lines) + "\n").encode("utf-8")
    return Tier2CandidateSubsetSignature(
        sha256=hashlib.sha256(payload).hexdigest().upper(),
        count=len(candidate_rows),
    )
```

- [ ] **Step 2: Add sidecar loader**

Add a public loader:

```python
def load_tier2_trace_evidence(
    *,
    sidecar_path: Path,
    raw_manifest_path: Path,
    candidate_rows: Sequence[Mapping[str, object]],
    source_context: GateSourceContext,
) -> dict[str, Tier2TraceEvidence]:
    sidecar_rows = _read_tsv_required(
        sidecar_path,
        TIER2_TRACE_EVIDENCE_REQUIRED_COLUMNS,
    )
    _read_tsv_required(raw_manifest_path, TIER2_RAW_MANIFEST_REQUIRED_COLUMNS)
    raw_manifest_sha256 = _sha256_file(raw_manifest_path)
    subset = tier2_candidate_subset_signature(candidate_rows)
    evidence_by_family: dict[str, Tier2TraceEvidence] = {}
    for row in sidecar_rows:
        evidence = _tier2_evidence_from_row(
            row,
            source_context=source_context,
            raw_manifest_sha256=raw_manifest_sha256,
            candidate_subset=subset,
        )
        if evidence.feature_family_id in evidence_by_family:
            raise ValueError(
                "alignment_tier2_trace_evidence.tsv has duplicate "
                f"feature_family_id: {evidence.feature_family_id}"
            )
        evidence_by_family[evidence.feature_family_id] = evidence
    return evidence_by_family
```

Add private helpers:

```python
def _tier2_evidence_from_row(
    row: Mapping[str, str],
    *,
    source_context: GateSourceContext,
    raw_manifest_sha256: str,
    candidate_subset: Tier2CandidateSubsetSignature,
) -> Tier2TraceEvidence:
    blockers: list[str] = []
    if (
        row.get("source_alignment_review_sha256") != source_context.review_sha256
        or row.get("source_alignment_cells_sha256") != source_context.cell_sha256
    ):
        blockers.append("source_hash_mismatch")
    if row.get("source_raw_manifest_sha256") != raw_manifest_sha256:
        blockers.append("raw_manifest_hash_mismatch")
    if (
        row.get("source_candidate_subset_sha256") != candidate_subset.sha256
        or _int_value(row.get("source_candidate_subset_count"))
        != candidate_subset.count
    ):
        blockers.append("candidate_subset_hash_mismatch")
    criteria_version = row.get("criteria_version", "")
    producer_version = row.get("producer_version", "")
    if criteria_version not in TIER2_ALLOWED_CRITERIA_VERSIONS:
        blockers.append("criteria_version_not_allowlisted")
    if producer_version not in TIER2_RECOGNIZED_PRODUCER_VERSIONS:
        blockers.append("producer_version_not_recognized")
    metric_blockers = _tier2_v0_metric_blockers(row)
    return Tier2TraceEvidence(
        feature_family_id=row.get("feature_family_id", ""),
        evidence_status=row.get("evidence_status", ""),
        support_component=row.get("support_component", ""),
        criteria_version=criteria_version,
        producer_version=producer_version,
        raw_trace_reread_status=row.get("raw_trace_reread_status", ""),
        coherence_status=row.get("coherence_status", ""),
        challenge_blockers=tuple(sorted(_split_tokens(row.get("challenge_blockers")))),
        dependent_context=tuple(sorted(_split_tokens(row.get("dependent_context")))),
        provenance_blockers=tuple(blockers),
        metric_blockers=metric_blockers,
    )
```

Add metric validation helpers. These helpers run even for synthetic test
sidecars because the checkpoint must prove that `validated/pass/pass` is not
enough without v0 row-level evidence:

```python
def _tier2_v0_metric_blockers(row: Mapping[str, str]) -> tuple[str, ...]:
    if row.get("evidence_status") != "validated":
        return ()
    blockers: list[str] = []
    trace_scan_count = _int_value(row.get("trace_scan_count"))
    scan_support_score = _float(row.get("scan_support_score"))
    apex_delta_sec = _float(row.get("apex_delta_sec"))
    boundary_width_sec = _float(row.get("boundary_width_sec"))
    neighbor_interference_ratio = _optional_float_blank_allowed(
        row.get("neighbor_interference_ratio")
    )
    rescued_checked = _int_value(row.get("rescued_cell_count_checked"))
    rescued_supported = _int_value(row.get("rescued_cell_count_supported"))
    rescued_apex_span = _float(row.get("rescued_apex_rt_span_sec"))
    rescued_boundary_overlap_min = _float(row.get("rescued_boundary_overlap_min"))
    if None in {
        trace_scan_count,
        scan_support_score,
        apex_delta_sec,
        boundary_width_sec,
        rescued_checked,
        rescued_supported,
        rescued_apex_span,
        rescued_boundary_overlap_min,
    }:
        blockers.append("metric_unavailable")
        return tuple(blockers)
    if trace_scan_count < 5:
        blockers.append("metric_unavailable")
    if scan_support_score < 0.20:
        blockers.append("low_scan_support")
    elif scan_support_score < 0.50:
        blockers.append("weak_scan_support")
    if apex_delta_sec > 30.0:
        blockers.append("apex_delta_exceeds_v0_threshold")
    if boundary_width_sec <= 0.0 or boundary_width_sec > 180.0:
        blockers.append("boundary_width_out_of_range")
    if (
        neighbor_interference_ratio is not None
        and neighbor_interference_ratio > 0.33
    ):
        blockers.append("neighbor_interference")
    if rescued_checked < 1 or rescued_supported < 1:
        blockers.append("rescued_cell_support_low")
    elif rescued_supported / rescued_checked < 0.50:
        blockers.append("rescued_cell_support_low")
    if rescued_apex_span > 21.0:
        blockers.append("rescued_apex_span_wide")
    if rescued_boundary_overlap_min < 0.50:
        blockers.append("rescued_boundary_overlap_low")
    return _ordered_unique(blockers)
```

```python
def _optional_float_blank_allowed(value: object) -> float | None:
    if value in (None, ""):
        return None
    return _float(value)
```

```python
def _read_tsv_required(
    path: Path,
    required_columns: Sequence[str],
) -> tuple[dict[str, str], ...]:
    import csv

    if not path.exists():
        raise FileNotFoundError(str(path))
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = tuple(reader.fieldnames or ())
        missing = [column for column in required_columns if column not in fieldnames]
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return tuple(dict(row) for row in reader)
```

- [ ] **Step 3: Change evaluator support source**

Change the signature:

```python
def evaluate_production_candidate_gate(
    review_row: Mapping[str, object],
    cell_rows: Sequence[Mapping[str, object]],
    *,
    source_context: GateSourceContext,
    tier2_evidence: Tier2TraceEvidence | None = None,
) -> ProductionCandidateGateDecision:
```

Replace:

```python
support = _explicit_positive_support(review)
tier2_available = bool(support)
dependent = _dependent_context(review, rescued)
blockers = _challenge_blockers(rescued)
```

with:

```python
support = _tier2_positive_support(tier2_evidence)
tier2_available = bool(support)
dependent = _ordered_unique(
    (*_dependent_context(review, rescued), *_tier2_dependent_context(tier2_evidence))
)
blockers = _ordered_unique(
    (*_challenge_blockers(rescued), *_tier2_blockers(tier2_evidence))
)
```

Replace:

```python
if not tier2_available:
    blockers = _ordered_unique((*blockers, "missing_positive_tier2_support"))
```

with:

```python
if not tier2_available and tier2_evidence is None:
    blockers = _ordered_unique((*blockers, "missing_positive_tier2_support"))
```

Remove `_explicit_positive_support()` and `_INDEPENDENT_TIER2_SUPPORT_COMPONENTS`.

Add:

```python
def _tier2_positive_support(
    evidence: Tier2TraceEvidence | None,
) -> tuple[str, ...]:
    if evidence is None:
        return ()
    if _tier2_blockers(evidence):
        return ()
    if evidence.evidence_status != "validated":
        return ()
    if evidence.support_component != TIER2_SUPPORT_COMPONENT:
        return ()
    if evidence.raw_trace_reread_status != "pass":
        return ()
    if evidence.coherence_status != "pass":
        return ()
    return (TIER2_SUPPORT_COMPONENT,)
```

```python
def _tier2_blockers(evidence: Tier2TraceEvidence | None) -> tuple[str, ...]:
    if evidence is None:
        return ()
    blockers = [
        *evidence.provenance_blockers,
        *evidence.metric_blockers,
        *evidence.challenge_blockers,
    ]
    if evidence.evidence_status == "validated":
        if evidence.support_component != TIER2_SUPPORT_COMPONENT:
            blockers.append("missing_positive_tier2_support")
        if evidence.raw_trace_reread_status != "pass":
            blockers.append("raw_trace_reread_not_pass")
        if evidence.coherence_status != "pass":
            blockers.append("rescued_coherence_not_pass")
    elif evidence.evidence_status in {"blocked", "not_supported", "inconclusive"}:
        if not blockers:
            blockers.append(f"tier2_{evidence.evidence_status}")
    else:
        blockers.append("tier2_evidence_status_unrecognized")
    return _ordered_unique(blockers)
```

```python
def _tier2_dependent_context(
    evidence: Tier2TraceEvidence | None,
) -> tuple[str, ...]:
    return evidence.dependent_context if evidence is not None else ()
```

- [ ] **Step 4: Run unit tests**

Run:

```powershell
python -m pytest tests\test_production_candidate_gate.py -q
```

Expected: all tests in this file pass after imports and type hints are adjusted.

---

### Task 3: Add CLI Tier 2 Sidecar Inputs

**Files:**
- Modify: `tools/diagnostics/provisional_backfill_candidate_gate.py`
- Modify: `tests/test_provisional_backfill_candidate_gate_cli.py`

- [ ] **Step 1: Add CLI tests**

Add a test proving valid sidecar promotion through the CLI:

```python
def test_cli_accepts_valid_tier2_sidecar(tmp_path: Path) -> None:
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
    assert by_id["FAM_CAND"]["candidate_gate_status"] == "production_candidate"
    assert (
        by_id["FAM_CAND"]["support_components"]
        == "validated_tier2_trace_evidence"
    )
    payload = json.loads(
        (output_dir / "alignment_production_candidate_gate.json").read_text(
            encoding="utf-8",
        ),
    )
    assert payload["tier2_trace_evidence_artifact"] == str(sidecar_path)
    assert payload["tier2_raw_manifest_artifact"] == str(raw_manifest_path)
    assert payload["production_candidate_count"] == 1
    assert payload["production_ready"] is False
```

Add a stale provenance test:

```python
def test_cli_stale_tier2_hash_emits_machine_readable_blocker(
    tmp_path: Path,
) -> None:
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
        source_review_sha256="0" * 64,
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
    assert "source_hash_mismatch" in by_id["FAM_CAND"]["challenge_blockers"]
```

Add a paired-argument failure test:

```python
def test_cli_requires_tier2_sidecar_and_manifest_together(
    tmp_path: Path,
    capsys,
) -> None:
    alignment_dir = _write_alignment_run(tmp_path / "alignment")
    sidecar_path = tmp_path / "alignment_tier2_trace_evidence.tsv"
    sidecar_path.write_text("", encoding="utf-8")

    code = gate_cli.main(
        [
            "--alignment-dir",
            str(alignment_dir),
            "--tier2-trace-evidence-tsv",
            str(sidecar_path),
        ],
    )

    assert code == 2
    stderr = capsys.readouterr().err
    assert "tier2_trace_evidence_tsv and tier2_raw_manifest_tsv must be supplied together" in stderr
```

- [ ] **Step 2: Add CLI fixture helpers**

Reuse the unit-test shape, but call production helpers from `gate_cli`:

```python
def _write_raw_manifest(tmp_path: Path) -> Path:
    path = tmp_path / "alignment_tier2_raw_manifest.tsv"
    path.write_text(
        (
            "sample_stem\traw_file_path\traw_file_size_bytes\t"
            "raw_file_mtime_utc\traw_reader_runtime\tpython_executable\tdll_dir\n"
            "S1\tC:\\Xcalibur\\data\\S1.raw\t123\t"
            "2026-05-29T00:00:00Z\tpythonnet\t.venv\\Scripts\\python.exe\t"
            "C:\\Xcalibur\\system\\programs\n"
        ),
        encoding="utf-8",
    )
    return path
```

```python
def _write_tier2_sidecar(
    tmp_path: Path,
    *,
    family_id: str,
    candidate_rows: list[dict[str, str]],
    source_context,
    raw_manifest_path: Path,
    source_review_sha256: str | None = None,
) -> Path:
    subset = gate_cli.tier2_candidate_subset_signature(candidate_rows)
    row = {
        "feature_family_id": family_id,
        "evidence_status": "validated",
        "support_component": "validated_tier2_trace_evidence",
        "criteria_version": "tier2_trace_identity_rescued_coherence_v0",
        "producer_version": "raw_trace_reread_tier2_v0",
        "raw_trace_reread_status": "pass",
        "seed_apex_rt": "8.000",
        "tier2_apex_rt": "8.100",
        "apex_delta_sec": "6.0",
        "scan_support_score": "0.80",
        "trace_scan_count": "8",
        "boundary_start_rt": "7.950",
        "boundary_end_rt": "8.050",
        "boundary_width_sec": "6.0",
        "neighbor_interference_ratio": "0.10",
        "rescued_cell_count_checked": "2",
        "rescued_cell_count_supported": "2",
        "rescued_apex_rt_span_sec": "6.0",
        "rescued_boundary_overlap_min": "0.80",
        "coherence_status": "pass",
        "challenge_blockers": "",
        "dependent_context": "",
        "source_alignment_review_sha256": (
            source_review_sha256 or source_context.review_sha256
        ),
        "source_alignment_cells_sha256": source_context.cell_sha256,
        "source_raw_manifest_sha256": _sha256_file(raw_manifest_path),
        "source_candidate_subset_sha256": subset.sha256,
        "source_candidate_subset_count": str(subset.count),
        "source_expected_sample_count": "8",
        "raw_reader_runtime": "pythonnet",
        "python_executable": ".venv\\Scripts\\python.exe",
        "dll_dir": "C:\\Xcalibur\\system\\programs",
        "producer_command": "synthetic-test-fixture",
        "generated_at_utc": "2026-05-29T00:00:00Z",
    }
    columns = list(row)
    path = tmp_path / "alignment_tier2_trace_evidence.tsv"
    path.write_text(
        "\n".join(
            (
                "\t".join(columns),
                "\t".join(row[column] for column in columns),
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return path
```

- [ ] **Step 3: Implement CLI flags and loader call**

Import:

```python
    load_tier2_trace_evidence,
    tier2_candidate_subset_signature,
```

Change `main()` to pass optional args into `run_gate()`:

```python
outputs = run_gate(
    alignment_dir=args.alignment_dir,
    output_dir=output_dir,
    tier2_trace_evidence_tsv=args.tier2_trace_evidence_tsv,
    tier2_raw_manifest_tsv=args.tier2_raw_manifest_tsv,
)
```

Change `run_gate()` signature:

```python
def run_gate(
    *,
    alignment_dir: Path,
    output_dir: Path,
    tier2_trace_evidence_tsv: Path | None = None,
    tier2_raw_manifest_tsv: Path | None = None,
) -> dict[str, Path]:
```

After `candidate_rows` is computed, load evidence only when both args exist:

```python
    if bool(tier2_trace_evidence_tsv) != bool(tier2_raw_manifest_tsv):
        raise ValueError(
            "tier2_trace_evidence_tsv and tier2_raw_manifest_tsv "
            "must be supplied together"
        )
    tier2_evidence_by_family = (
        load_tier2_trace_evidence(
            sidecar_path=tier2_trace_evidence_tsv,
            raw_manifest_path=tier2_raw_manifest_tsv,
            candidate_rows=candidate_rows,
            source_context=source_context,
        )
        if tier2_trace_evidence_tsv is not None
        and tier2_raw_manifest_tsv is not None
        else {}
    )
```

Pass evidence into the evaluator:

```python
tier2_evidence=tier2_evidence_by_family.get(review_row["feature_family_id"]),
```

Add JSON fields when supplied:

```python
if tier2_trace_evidence_tsv is not None and tier2_raw_manifest_tsv is not None:
    summary.update(
        {
            "tier2_trace_evidence_artifact": str(tier2_trace_evidence_tsv),
            "tier2_trace_evidence_sha256": _sha256_file(tier2_trace_evidence_tsv),
            "tier2_raw_manifest_artifact": str(tier2_raw_manifest_tsv),
            "tier2_raw_manifest_sha256": _sha256_file(tier2_raw_manifest_tsv),
            "tier2_candidate_subset_sha256": tier2_candidate_subset_signature(
                candidate_rows
            ).sha256,
            "tier2_candidate_subset_count": len(candidate_rows),
        }
    )
```

Add parser args:

```python
parser.add_argument("--tier2-trace-evidence-tsv", type=Path)
parser.add_argument("--tier2-raw-manifest-tsv", type=Path)
```

- [ ] **Step 4: Run CLI tests**

Run:

```powershell
python -m pytest tests\test_provisional_backfill_candidate_gate_cli.py -q
```

Expected: all CLI tests pass.

---

### Task 4: Update Matrix Guard And Diagnostic Index

**Files:**
- Modify: `tests/test_alignment_tsv_writer.py`
- Modify: `tools/diagnostics/INDEX.md`

- [ ] **Step 1: Update matrix guard expectation**

In `test_production_candidate_sidecar_status_does_not_change_matrix_writer`, remove the injected direct-token promotion assertion and replace it with:

```python
    decision = evaluate_production_candidate_gate(
        sidecar_review_row,
        cell_rows,
        source_context=source_context_for_artifacts(
            review_path=review_path,
            cell_path=cells_path,
            matrix_path=matrix_path,
        ),
    )

    assert decision.candidate_gate_status == "keep_provisional"
    assert decision.support_components == ()
    assert "missing_positive_tier2_support" in decision.challenge_blockers
    assert _read_tsv(matrix_path) == []
```

Rename the test to:

```python
def test_direct_tier2_review_token_does_not_change_matrix_writer(
    tmp_path: Path,
) -> None:
```

- [ ] **Step 2: Update diagnostic index wording**

In `tools/diagnostics/INDEX.md`, update the `provisional_backfill_candidate_gate.py` entry status note to:

```markdown
**Status note**: Writes `alignment_production_candidate_gate.tsv`; optional Tier 2 support must come from `--tier2-trace-evidence-tsv` plus `--tier2-raw-manifest-tsv`, not direct `alignment_review.tsv` tokens. Does not mutate `alignment_review.tsv`, `alignment_matrix.tsv`, workbook schemas, or downstream correction/statistics contracts.
```

- [ ] **Step 3: Run the guard**

Run:

```powershell
python -m pytest tests\test_alignment_tsv_writer.py::test_direct_tier2_review_token_does_not_change_matrix_writer -q
```

Expected: `1 passed`.

---

### Task 5: Validation Note And Final Verification

**Files:**
- Create: `docs/superpowers/notes/2026-05-29-tier2-sidecar-provenance-gate-checkpoint-validation-note.md`

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest `
  tests\test_production_candidate_gate.py `
  tests\test_provisional_backfill_candidate_gate_cli.py `
  tests\test_alignment_tsv_writer.py::test_direct_tier2_review_token_does_not_change_matrix_writer `
  -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run ruff**

Run:

```powershell
python -m ruff check `
  xic_extractor\alignment\production_candidate_gate.py `
  tools\diagnostics\provisional_backfill_candidate_gate.py `
  tests\test_production_candidate_gate.py `
  tests\test_provisional_backfill_candidate_gate_cli.py `
  tests\test_alignment_tsv_writer.py
```

Expected:

```text
All checks passed!
```

- [ ] **Step 3: Run existing no-sidecar artifact smoke**

Run:

```powershell
python -m tools.diagnostics.provisional_backfill_candidate_gate `
  --alignment-dir output\tiered_backfill_candidate_gate_8raw_current `
  --output-dir output\tiered_backfill_candidate_gate_8raw_current
```

Expected: command completes and existing no-sidecar behavior remains conservative.

Inspect:

```powershell
python -c "import json; p='output/tiered_backfill_candidate_gate_8raw_current/alignment_production_candidate_gate.json'; d=json.load(open(p, encoding='utf-8')); print(d['readiness_label'], d['row_count'], d['production_candidate_count'], d['production_ready'], d['matrix_contract_changed'])"
```

Expected:

```text
diagnostic_only 7 0 False False
```

Do not run 85RAW in this checkpoint. Existing no-sidecar 85RAW behavior was already covered by the prior diagnostic sidecar pilot; this checkpoint only changes optional Tier 2 sidecar ingestion and has focused synthetic provenance fixtures.

- [ ] **Step 4: Write validation note**

Create the validation note with:

```markdown
# Tier 2 Sidecar Provenance Gate Checkpoint Validation Note

## Verdict

`diagnostic_only`

This checkpoint implements sidecar-only positive support ingestion for the provisional backfill candidate gate. It disables direct `alignment_review.tsv` token promotion. It does not implement the RAW trace re-read producer and does not change `alignment_matrix.tsv`.

## Verification

```text
Focused pytest: <paste observed summary>
Ruff: <paste observed summary>
8RAW no-sidecar smoke: <paste observed summary>
```

## Contract State

- Positive support can only come from a provenance-valid Tier 2 sidecar row.
- `independent_tier2_support_components=validated_tier2_trace_evidence` in `alignment_review.tsv` no longer promotes by itself.
- Stale source hashes, stale RAW manifest hashes, candidate subset mismatch, unknown criteria, unknown producer, inconclusive evidence, or hard challenge blockers do not promote.
- `production_ready=false` remains the diagnostic summary state.

## Remaining Risk

The RAW trace re-read producer is still the next checkpoint. Synthetic sidecar fixtures prove the gate contract, not real RAW evidence quality.
```

- [ ] **Step 5: Docs smoke and diff check**

Run:

```powershell
rg -n "paste observed|<paste|TBD|TODO" docs\superpowers\notes\2026-05-29-tier2-sidecar-provenance-gate-checkpoint-validation-note.md
rg -n "[ \t]+$" docs\superpowers\plans\2026-05-29-tier2-sidecar-provenance-gate-checkpoint-plan.md docs\superpowers\plans\2026-05-29-tier2-sidecar-provenance-gate-checkpoint-goal.md docs\superpowers\notes\2026-05-29-tier2-sidecar-provenance-gate-checkpoint-validation-note.md
git diff --check -- `
  xic_extractor\alignment\production_candidate_gate.py `
  tools\diagnostics\provisional_backfill_candidate_gate.py `
  tests\test_production_candidate_gate.py `
  tests\test_provisional_backfill_candidate_gate_cli.py `
  tests\test_alignment_tsv_writer.py `
  tools\diagnostics\INDEX.md `
  docs\superpowers\plans\2026-05-29-tier2-sidecar-provenance-gate-checkpoint-plan.md `
  docs\superpowers\plans\2026-05-29-tier2-sidecar-provenance-gate-checkpoint-goal.md `
  docs\superpowers\notes\2026-05-29-tier2-sidecar-provenance-gate-checkpoint-validation-note.md
```

Expected:

- first `rg` exits `1` with no matches after placeholders are filled;
- second `rg` exits `1` with no trailing whitespace;
- `git diff --check` exits `0`.

## Final Verification

Run:

```powershell
python -m pytest `
  tests\test_production_candidate_gate.py `
  tests\test_provisional_backfill_candidate_gate_cli.py `
  tests\test_alignment_tsv_writer.py::test_direct_tier2_review_token_does_not_change_matrix_writer `
  -q

python -m ruff check `
  xic_extractor\alignment\production_candidate_gate.py `
  tools\diagnostics\provisional_backfill_candidate_gate.py `
  tests\test_production_candidate_gate.py `
  tests\test_provisional_backfill_candidate_gate_cli.py `
  tests\test_alignment_tsv_writer.py

git diff --check -- `
  xic_extractor\alignment\production_candidate_gate.py `
  tools\diagnostics\provisional_backfill_candidate_gate.py `
  tests\test_production_candidate_gate.py `
  tests\test_provisional_backfill_candidate_gate_cli.py `
  tests\test_alignment_tsv_writer.py `
  tools\diagnostics\INDEX.md `
  docs\superpowers\plans\2026-05-29-tier2-sidecar-provenance-gate-checkpoint-plan.md `
  docs\superpowers\plans\2026-05-29-tier2-sidecar-provenance-gate-checkpoint-goal.md `
  docs\superpowers\notes\2026-05-29-tier2-sidecar-provenance-gate-checkpoint-validation-note.md
```

Acceptance:

- Valid Tier 2 sidecar fixture can produce `production_candidate` in the diagnostic gate sidecar.
- Direct review-row support token cannot promote without a valid Tier 2 sidecar row.
- Missing sidecar preserves current conservative behavior.
- Stale hashes, unknown criteria/producer, inconclusive rows, and challenge blockers do not promote.
- CLI requires Tier 2 evidence TSV and RAW manifest TSV together.
- Output remains `diagnostic_only`; `production_ready=false`; `matrix_contract_changed=false`.
- Primary matrix writer behavior remains unchanged.

## Stop Rules

- Stop if implementation requires changing `alignment_matrix.tsv`, workbook schemas, `scripts.run_alignment` defaults, output levels, or primary matrix row inclusion semantics.
- Stop if the gate must re-read RAW data; RAW trace re-read belongs to the next producer checkpoint.
- Stop if positive support can only be derived from owner-backfill context or direct review-row tokens.
- Stop if source hashes, RAW manifest hash, candidate subset hash/count, criteria version, or producer version cannot be checked.
- Stop before launching 85RAW; this checkpoint is sidecar-ingestion contract work, not RAW producer validation.
- Stop after three failed attempts on the same symptom and revisit the contract.

## Self-Review

Spec coverage:

- Sidecar-only support is covered by Tasks 1-3.
- Direct review-row token removal is covered by Tasks 1, 2, and 4.
- Provenance checks are covered by Tasks 1-3.
- No-sidecar compatibility is covered by Task 3 and Task 5.
- RAW producer preflight and real RAW evidence are intentionally deferred as the next checkpoint, matching the spec's instruction that the direct-token path must be removed before RAW producer acceptance.

Placeholder scan:

- No task contains `TBD`, `TODO`, or unresolved implementation placeholders. The validation note step explicitly requires observed command summaries before completion.

Type consistency:

- `Tier2CandidateSubsetSignature`, `Tier2TraceEvidence`, `load_tier2_trace_evidence`, and `tier2_candidate_subset_signature` are defined before use and stay in the domain module imported by the CLI.
