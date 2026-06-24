# Row Completion Confidence Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the version 1 diagnostic-only Final Matrix Row Completion Confidence Benchmark from the reviewed spec.

**Architecture:** Package-owned logic lives under `xic_extractor/diagnostics/row_completion_confidence*`; `tools/diagnostics/row_completion_confidence.py` is a thin CLI that resolves paths and calls package APIs. Version 1 is A-first/B-secondary: artifact-only daily and gate-panel confidence, external reviewer schema validation only, and manual-review trigger flags only.

**Tech Stack:** Python 3, dataclasses, `pathlib`, JSON, TSV via `xic_extractor.tabular_io`, pytest, ruff.

## Global Constraints

- This work is `diagnostic_only`; it must not change selected peaks, selected areas, counted detections, matrix identity, ProductWriter authority, active lane, maturity tier, workbook/TSV schemas, or default preset behavior.
- Do not open RAW, run XIC extraction, launch mature tools, or invoke 85RAW in version 1.
- The CLI under `tools/diagnostics/` must orchestrate only. Reusable loading, schemas, comparison, classification, summaries, and report rendering belong in package modules.
- Reuse `xic_extractor.tabular_io` for TSV/JSON scalar and hashing mechanics; do not add a parallel parser layer.
- Reuse `alignment_health_packet` outputs and `targeted_gt_alignment_audit` outputs. Do not recompute their evidence in the benchmark.
- External reviewer lane is schema-only in version 1. Do not implement a mature-tool adapter, external parser, or scientific disagreement classifier.
- Manual review lane is trigger-only in version 1. Do not write a durable manual-review queue.
- A benchmark report can recommend a fresh run but must not launch RAW processing.
- Existing 85RAW artifacts are stress evidence only when manifest-bound. Stale or unproven 85RAW evidence is `INCONCLUSIVE`.
- Do not commit during execution unless the user explicitly authorizes commits for that execution run. If commits are authorized, stage only files touched by the current task.

## Preflight Contract

Goal:
Create a diagnostic-only row completion confidence benchmark that covers alignment, bounded backfill evidence, and external reviewer schema evidence.

Existing owner/helper to reuse:
`tools/diagnostics/alignment_health_packet.py`, `tools/diagnostics/targeted_gt_alignment_audit.py`, existing alignment artifacts, `xic_extractor.tabular_io`, and productization/control-plane docs for authority boundaries.

New code location:
Package modules under `xic_extractor/diagnostics/row_completion_confidence*`; thin CLI under `tools/diagnostics/row_completion_confidence.py`; canonical panel docs under `docs/superpowers/validation/`.

Evidence provider role:
Health packets, targeted GT audits, bounded backfill evidence, canonical panel rows, and external feature-table schema checks are diagnostic evidence providers only.

Simplest product rule:
No new product rule. The benchmark separates production safety from review utility and reports whether a product-gate candidate packet is required.

Call-cost model:
Artifact-only TSV/JSON scans. No RAW opens, no XIC extraction, no smoothing, no mature-tool subprocesses.

Public contracts at risk:
New diagnostic CLI and output artifact schemas only. Matrix outputs, writer authority, selected values, workbook/TSV product schemas, and control-plane status must remain unchanged.

Validation gate:
Focused synthetic tests, CLI smoke on synthetic artifacts, and optional no-RAW smoke on existing 8RAW artifacts. This is not PR-ready until the repo gate runs.

Stop rule:
Stop and switch to expected-diff/product-gate workflow if implementation needs to alter selected values, counted detections, matrix identity, writer authority, active lane, maturity tier, or default preset behavior.

---

## File Structure

- Create `xic_extractor/diagnostics/row_completion_confidence_schema.py`
  - Own schema constants, dataclasses, acceptance labels, no-authority text, artifact descriptors, output column definitions, and artifact freshness decision rules.
- Create `xic_extractor/diagnostics/row_completion_confidence.py`
  - Own package API for daily artifact lane, baseline/current manifest binding, summary rows, sentinel rows, JSON/TSV/Markdown rendering.
- Create `xic_extractor/diagnostics/row_completion_confidence_panel.py`
  - Own canonical panel TSV/manifest loading and gate-panel evaluation from existing targeted GT audit outputs and sentinel metrics.
- Create `xic_extractor/diagnostics/row_completion_confidence_external.py`
  - Own external feature-table schema validation and mapping-quality pregate only.
- Create `tools/diagnostics/row_completion_confidence.py`
  - Thin CLI facade: parse args, call package API, print output paths. Missing required evidence is packetized as `INCONCLUSIVE` with `run_ok=false`; return `2` only for invalid arguments or non-recoverable output-write failures.
- Create `docs/superpowers/validation/row_completion_canonical_panel_v1.tsv`
  - Small v1 canonical panel definition.
- Create `docs/superpowers/validation/row_completion_canonical_panel_manifest_v1.json`
  - Manifest for the canonical panel file and version.
- Modify `tools/diagnostics/INDEX.md`
  - Add the new diagnostic entry and mark it `diagnostic_only`.
- Test `tests/test_row_completion_confidence_schema.py`
- Test `tests/test_row_completion_confidence_daily.py`
- Test `tests/test_row_completion_confidence_panel.py`
- Test `tests/test_row_completion_confidence_external.py`
- Test `tests/test_row_completion_confidence_cli.py`

---

### Task 1: Schema, Manifest, And Freshness Primitives

**Files:**
- Create: `xic_extractor/diagnostics/row_completion_confidence_schema.py`
- Test: `tests/test_row_completion_confidence_schema.py`

**Interfaces:**
- Produces:
  - `SCHEMA_VERSION: str`
  - `NO_AUTHORITY_STATEMENT: str`
  - `Status`, `RequiredAction`, `MappingStatus`, `MissingEvidenceCode` literal type aliases
  - `ArtifactDescriptor`
  - `ArtifactManifest`
  - `ManifestValidationResult`
  - `FreshnessDecision`
  - `artifact_descriptor(path: Path, *, root: Path, run_id: str, generation_context: str) -> ArtifactDescriptor`
  - `build_artifact_manifest(required_paths: Mapping[str, Path], *, root: Path, run_id: str, generation_context: str) -> ManifestValidationResult`
  - `freshness_decision(change_class: str) -> FreshnessDecision`
  - output column constants

- [ ] **Step 1: Write failing schema tests**

Create `tests/test_row_completion_confidence_schema.py`:

```python
from __future__ import annotations

from pathlib import Path

from xic_extractor.diagnostics.row_completion_confidence_schema import (
    NO_AUTHORITY_STATEMENT,
    SCHEMA_VERSION,
    SUMMARY_COLUMNS,
    artifact_descriptor,
    build_artifact_manifest,
    freshness_decision,
)


def test_artifact_descriptor_records_hash_relpath_size_and_rows(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "run" / "alignment_matrix.tsv"
    artifact.parent.mkdir()
    artifact.write_text("feature_family_id\tSampleA\nFAM1\t10\n", encoding="utf-8")

    descriptor = artifact_descriptor(
        artifact,
        root=tmp_path,
        run_id="synthetic_run_id",
        generation_context="synthetic_run",
    )

    assert descriptor.schema_version == SCHEMA_VERSION
    assert descriptor.run_id == "synthetic_run_id"
    assert descriptor.relpath == "run/alignment_matrix.tsv"
    assert descriptor.size_bytes == artifact.stat().st_size
    assert descriptor.row_count == 1
    assert len(descriptor.sha256) == 64
    assert descriptor.generation_context == "synthetic_run"


def test_manifest_fails_closed_for_missing_required_artifact(tmp_path: Path) -> None:
    result = build_artifact_manifest(
        {"alignment_matrix": tmp_path / "missing.tsv"},
        root=tmp_path,
        run_id="synthetic_run_id",
        generation_context="synthetic_run",
    )

    assert result.run_ok is False
    assert result.gate_ok is False
    assert result.status == "INCONCLUSIVE"
    assert result.missing_evidence_code == "missing_required_artifact"
    assert "missing.tsv" in result.reason


def test_manifest_fails_closed_for_unknown_generation_context(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "alignment_matrix.tsv"
    artifact.write_text("feature_family_id\tSampleA\nFAM1\t10\n", encoding="utf-8")

    result = build_artifact_manifest(
        {"alignment_matrix": artifact},
        root=tmp_path,
        run_id="synthetic_run_id",
        generation_context="unknown",
    )

    assert result.run_ok is False
    assert result.gate_ok is False
    assert result.status == "INCONCLUSIVE"
    assert result.missing_evidence_code == "stale_artifact_manifest"


def test_freshness_decision_separates_artifact_only_from_raw_rerun() -> None:
    docs_only = freshness_decision("docs_only")
    metric_change = freshness_decision("benchmark_metric_logic")
    generation_change = freshness_decision("alignment_generation_code")
    product_gate = freshness_decision("product_gate_packet")
    unknown = freshness_decision("unclassified_change")

    assert docs_only.required_action == "no_rerun"
    assert metric_change.required_action == "artifact_only_rerun"
    assert generation_change.required_action == "fresh_8raw_required"
    assert product_gate.required_action == "fresh_85raw_required_after_8raw"
    assert unknown.required_action == "inconclusive"


def test_output_columns_include_status_reason_manifest_and_authority() -> None:
    assert SUMMARY_COLUMNS == (
        "schema_version",
        "run_id",
        "lane",
        "metric_name",
        "status",
        "current_value",
        "baseline_value",
        "delta",
        "direction",
        "evidence_source",
        "artifact_relpath",
        "artifact_sha256",
        "reason",
        "missing_evidence_code",
        "input_artifact_manifest",
        "no_authority_statement",
    )
    assert "diagnostic_only" in NO_AUTHORITY_STATEMENT
    assert "ProductWriter authority" in NO_AUTHORITY_STATEMENT
    assert "control-plane/status index" in NO_AUTHORITY_STATEMENT
```

- [ ] **Step 2: Run the failing schema tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_row_completion_confidence_schema.py -q
```

Expected: FAIL because `row_completion_confidence_schema.py` does not exist.

- [ ] **Step 3: Implement schema primitives**

Create `xic_extractor/diagnostics/row_completion_confidence_schema.py`:

```python
"""Contracts for row-completion confidence diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from xic_extractor.tabular_io import file_sha256

SCHEMA_VERSION = "row_completion_confidence_v1"
NO_AUTHORITY_STATEMENT = (
    "This row-completion confidence report is diagnostic_only. It does not "
    "change matrix authority, ProductWriter authority, selected values, "
    "counted detections, workbook/TSV product schemas, control-plane/status "
    "index, active lane, maturity tier, or default preset behavior."
)

Status = Literal[
    "PASS",
    "WARN",
    "FAIL",
    "INCONCLUSIVE",
    "not_available",
    "schema_valid",
]
RequiredAction = Literal[
    "no_rerun",
    "artifact_only_rerun",
    "fresh_8raw_required",
    "fresh_85raw_required_after_8raw",
    "inconclusive",
]
MappingStatus = Literal[
    "not_available",
    "schema_valid_mapping_quality_unavailable",
    "FAIL",
    "INCONCLUSIVE",
]
MissingEvidenceCode = Literal[
    "",
    "missing_required_artifact",
    "missing_required_column",
    "unknown_schema_version",
    "stale_artifact_manifest",
    "baseline_current_unbound",
    "metric_source_unavailable",
    "canonical_panel_case_unbound",
    "external_mapping_quality_failed",
    "manual_review_required",
    "product_gate_required",
]

SUMMARY_COLUMNS = (
    "schema_version",
    "run_id",
    "lane",
    "metric_name",
    "status",
    "current_value",
    "baseline_value",
    "delta",
    "direction",
    "evidence_source",
    "artifact_relpath",
    "artifact_sha256",
    "reason",
    "missing_evidence_code",
    "input_artifact_manifest",
    "no_authority_statement",
)
SENTINEL_COLUMNS = (
    "schema_version",
    "run_id",
    "rank",
    "case_id",
    "lane",
    "case_type",
    "feature_family_id",
    "sample_stem",
    "production_safety_status",
    "review_utility_status",
    "issue_class",
    "severity_score",
    "evidence_source",
    "recommended_action",
    "requires_manual_review",
    "reason",
)
DISAGREEMENT_COLUMNS = (
    "schema_version",
    "run_id",
    "disagreement_id",
    "external_tool",
    "external_run_id",
    "mapping_status",
    "sample_id",
    "sample_stem",
    "feature_family_id",
    "external_feature_id",
    "mz_delta",
    "rt_delta_min",
    "classification",
    "reason",
)


@dataclass(frozen=True)
class ArtifactDescriptor:
    schema_version: str
    run_id: str
    path: str
    relpath: str
    size_bytes: int
    sha256: str
    row_count: int
    generation_context: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ArtifactManifest:
    schema_version: str
    run_id: str
    generation_context: str
    artifacts: tuple[ArtifactDescriptor, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ManifestValidationResult:
    run_ok: bool
    gate_ok: bool
    status: Status
    reason: str
    missing_evidence_code: MissingEvidenceCode
    manifest: ArtifactManifest | None


@dataclass(frozen=True)
class FreshnessDecision:
    change_class: str
    required_action: RequiredAction
    reason: str


def artifact_descriptor(
    path: Path,
    *,
    root: Path,
    run_id: str,
    generation_context: str,
) -> ArtifactDescriptor:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    row_count = max(0, sum(1 for _line in path.open(encoding="utf-8-sig")) - 1)
    return ArtifactDescriptor(
        schema_version=SCHEMA_VERSION,
        run_id=run_id,
        path=str(path.resolve()),
        relpath=path.resolve().relative_to(root.resolve()).as_posix(),
        size_bytes=path.stat().st_size,
        sha256=file_sha256(path),
        row_count=row_count,
        generation_context=generation_context,
    )


def build_artifact_manifest(
    required_paths: dict[str, Path],
    *,
    root: Path,
    run_id: str,
    generation_context: str,
) -> ManifestValidationResult:
    if not run_id.strip() or generation_context.strip().lower() == "unknown":
        return ManifestValidationResult(
            run_ok=False,
            gate_ok=False,
            status="INCONCLUSIVE",
            reason="run_id and known generation_context are required",
            missing_evidence_code="stale_artifact_manifest",
            manifest=None,
        )
    descriptors: list[ArtifactDescriptor] = []
    for label, path in required_paths.items():
        try:
            descriptors.append(
                artifact_descriptor(
                    path,
                    root=root,
                    run_id=run_id,
                    generation_context=generation_context,
                ),
            )
        except (FileNotFoundError, ValueError) as exc:
            return ManifestValidationResult(
                run_ok=False,
                gate_ok=False,
                status="INCONCLUSIVE",
                reason=f"{label}: {exc}",
                missing_evidence_code="missing_required_artifact",
                manifest=None,
            )
    return ManifestValidationResult(
        run_ok=True,
        gate_ok=True,
        status="PASS",
        reason="required artifacts are manifest-bound",
        missing_evidence_code="",
        manifest=ArtifactManifest(
            schema_version=SCHEMA_VERSION,
            run_id=run_id,
            generation_context=generation_context,
            artifacts=tuple(descriptors),
        ),
    )


def freshness_decision(change_class: str) -> FreshnessDecision:
    normalized = change_class.strip().lower()
    if normalized in {"docs_only", "report_wording", "spec_only"}:
        return FreshnessDecision(change_class, "no_rerun", "no generator changed")
    if normalized in {
        "benchmark_reader",
        "benchmark_metric_logic",
        "benchmark_schema",
        "benchmark_join_logic",
        "canonical_panel_mapping",
        "fail_closed_logic",
    }:
        return FreshnessDecision(
            change_class,
            "artifact_only_rerun",
            "only benchmark interpretation changed",
        )
    if normalized in {
        "alignment_generation_code",
        "discovery_generation_code",
        "extraction_generation_code",
        "backfill_generation_code",
        "scoring_generation_code",
        "matrix_writer_generation_code",
        "publication_check_generation_code",
        "config_or_input_universe",
    }:
        return FreshnessDecision(
            change_class,
            "fresh_8raw_required",
            "artifact generation behavior or input universe changed",
        )
    if normalized in {
        "product_gate_packet",
        "maturity_tier_change",
        "writer_authority_change",
        "selected_value_or_counting_change",
        "85raw_stress_claim",
    }:
        return FreshnessDecision(
            change_class,
            "fresh_85raw_required_after_8raw",
            "large-sample product or stress evidence is claimed",
        )
    return FreshnessDecision(change_class, "inconclusive", "unknown change class")
```

- [ ] **Step 4: Run schema tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_row_completion_confidence_schema.py -q
```

Expected: PASS.

- [ ] **Step 5: Run focused lint**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/diagnostics/row_completion_confidence_schema.py tests/test_row_completion_confidence_schema.py
```

Expected: `All checks passed!`

- [ ] **Step 6: Authorized commit checkpoint**

Only run this step if the user explicitly authorized commits for implementation.

```powershell
git status --short
git add xic_extractor/diagnostics/row_completion_confidence_schema.py tests/test_row_completion_confidence_schema.py
git commit -m "diagnostics: add row completion confidence schema"
```

Expected: commit succeeds without staging unrelated dirty files.

---

### Task 2: Daily Artifact Lane And Report Writers

**Files:**
- Create: `xic_extractor/diagnostics/row_completion_confidence.py`
- Test: `tests/test_row_completion_confidence_daily.py`

**Interfaces:**
- Consumes:
  - `ArtifactDescriptor`, `ArtifactManifest`, `ManifestValidationResult`, `SUMMARY_COLUMNS`, `SENTINEL_COLUMNS`, `DISAGREEMENT_COLUMNS`, `NO_AUTHORITY_STATEMENT`
  - `build_artifact_manifest` from `row_completion_confidence_schema`
- Produces:
  - `RowCompletionOutputs`
  - `build_daily_confidence_packet(current_alignment_dir: Path, current_health_dir: Path, output_dir: Path, baseline_alignment_dir: Path | None = None, run_id: str = "row_completion_confidence", generation_context: str = "unknown") -> RowCompletionOutputs`

- [ ] **Step 1: Write failing daily-lane tests**

Create `tests/test_row_completion_confidence_daily.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from xic_extractor.diagnostics.row_completion_confidence import (
    build_daily_confidence_packet,
)
from xic_extractor.diagnostics.row_completion_confidence_schema import (
    SUMMARY_COLUMNS,
)


def test_daily_packet_writes_no_authority_outputs(tmp_path: Path) -> None:
    current = _write_alignment_artifacts(tmp_path / "current", area="10")
    health = _write_health_packet(tmp_path / "health")
    output = tmp_path / "out"

    outputs = build_daily_confidence_packet(
        current_alignment_dir=current,
        current_health_dir=health,
        output_dir=output,
        run_id="synthetic_daily",
        generation_context="synthetic_current",
    )

    packet = json.loads(outputs.summary_json.read_text(encoding="utf-8"))
    assert packet["schema_version"] == "row_completion_confidence_v1"
    assert packet["run_ok"] is True
    assert packet["gate_ok"] is True
    assert packet["production_ready"] is False
    assert packet["validation_tier"] == "diagnostic_only"
    assert packet["authority_decision"] == "no_control_plane_change"
    assert packet["input_artifact_manifest"]["run_id"] == "synthetic_daily"
    assert "diagnostic_only" in packet["no_authority_statement"]
    summary_header = outputs.summary_tsv.read_text(
        encoding="utf-8",
    ).splitlines()[0].split("\t")
    assert tuple(summary_header) == SUMMARY_COLUMNS
    assert "duplicate_only_family_count" in outputs.summary_tsv.read_text(
        encoding="utf-8",
    )
    assert "FAM_BAD" in outputs.sentinels_tsv.read_text(encoding="utf-8")
    assert outputs.disagreements_tsv.is_file()
    assert "External Reviewer Signal" in outputs.report_md.read_text(
        encoding="utf-8",
    )


def test_daily_packet_marks_selected_value_drift_as_expected_diff_required(
    tmp_path: Path,
) -> None:
    baseline = _write_alignment_artifacts(tmp_path / "baseline", area="10")
    current = _write_alignment_artifacts(tmp_path / "current", area="12")
    health = _write_health_packet(tmp_path / "health")

    outputs = build_daily_confidence_packet(
        current_alignment_dir=current,
        current_health_dir=health,
        output_dir=tmp_path / "out",
        baseline_alignment_dir=baseline,
        run_id="synthetic_drift",
        generation_context="synthetic_current",
    )

    packet = json.loads(outputs.summary_json.read_text(encoding="utf-8"))
    assert packet["production_safety"] == "inconclusive"
    assert packet["authority_decision"] == "expected_diff_required"
    assert "selected_value_drift" in outputs.summary_tsv.read_text(
        encoding="utf-8",
    )


def test_daily_packet_fails_closed_when_backfill_evidence_is_unbound(
    tmp_path: Path,
) -> None:
    current = _write_alignment_artifacts(tmp_path / "current", area="10")
    (current / "alignment_backfill_cell_evidence.tsv").unlink()
    health = _write_health_packet(tmp_path / "health")

    outputs = build_daily_confidence_packet(
        current_alignment_dir=current,
        current_health_dir=health,
        output_dir=tmp_path / "out",
        run_id="missing_backfill",
        generation_context="synthetic_current",
    )

    packet = json.loads(outputs.summary_json.read_text(encoding="utf-8"))
    assert packet["run_ok"] is False
    assert packet["gate_ok"] is False
    assert packet["production_safety"] == "inconclusive"
    assert packet["review_utility"] == "inconclusive"
    assert packet["missing_evidence_code"] == "metric_source_unavailable"


def _write_alignment_artifacts(path: Path, *, area: str) -> Path:
    path.mkdir()
    (path / "alignment_matrix.tsv").write_text(
        "Mz\tRT\tSampleA\n100\t5\t" + area + "\n",
        encoding="utf-8",
    )
    (path / "alignment_matrix_identity.tsv").write_text(
        "peak_hypothesis_id\tmatrix_row_index\tsource_feature_family_ids\t"
        "evidence_status\nP1\t1\tFAM_BAD\tcomplete\n",
        encoding="utf-8",
    )
    (path / "alignment_review.tsv").write_text(
        "feature_family_id\tdetected_count\tambiguous_ms1_owner_count\t"
        "duplicate_assigned_count\tunchecked_count\taccepted_cell_count\t"
        "accepted_rescue_count\treview_rescue_count\tidentity_decision\t"
        "identity_confidence\tprimary_evidence\trow_flags\treason\n"
        "FAM_BAD\t0\t0\t2\t0\t0\t0\t1\taudit_family\treview\towner\t"
        "duplicate_only;duplicate_claim_pressure\tduplicate only\n",
        encoding="utf-8",
    )
    (path / "alignment_backfill_cell_evidence.tsv").write_text(
        "schema_version\tfeature_family_id\tsample_stem\tstatus\t"
        "bounded_by_alignment_row\treason\n"
        "alignment_backfill_cell_evidence_v1\tFAM_BAD\tSampleA\t"
        "review_only\ttrue\tduplicate only\n",
        encoding="utf-8",
    )
    (path / "alignment_owner_backfill_seed_audit.tsv").write_text(
        "schema_version\tfeature_family_id\tsample_stem\tstatus\t"
        "seed_source\treason\n"
        "alignment_owner_backfill_seed_audit_v1\tFAM_BAD\tSampleA\t"
        "review_only\towner\tduplicate only\n",
        encoding="utf-8",
    )
    return path


def _write_health_packet(path: Path) -> Path:
    path.mkdir()
    packet = {
        "schema_version": "alignment_health_packet_v1",
        "summary_metrics": {
            "row_flag_counts": {
                "duplicate_only": 1,
                "zero_present": 0,
                "high_backfill_dependency": 0,
            },
            "accepted_rescue_count_total": 0,
            "review_rescue_count_total": 1,
            "sentinel_count": 1,
        },
        "sentinel_rows": [
            {
                "rank": 1,
                "feature_family_id": "FAM_BAD",
                "issue_class": "duplicate_claim",
                "severity_score": 48,
                "recommended_action": "inspect_owner_assignment",
                "reason": "duplicate only",
            },
        ],
        "status": "diagnostic_only",
    }
    (path / "alignment_health_summary.json").write_text(
        json.dumps(packet, indent=2) + "\n",
        encoding="utf-8",
    )
    (path / "alignment_health_family_sentinels.tsv").write_text(
        "rank\tfeature_family_id\tissue_class\tseverity_score\t"
        "recommended_action\treason\n"
        "1\tFAM_BAD\tduplicate_claim\t48\tinspect_owner_assignment\t"
        "duplicate only\n",
        encoding="utf-8",
    )
    return path
```

- [ ] **Step 2: Run failing daily-lane tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_row_completion_confidence_daily.py -q
```

Expected: FAIL because `row_completion_confidence.py` does not exist.

- [ ] **Step 3: Implement package daily lane**

Create `xic_extractor/diagnostics/row_completion_confidence.py` with these public signatures:

```python
@dataclass(frozen=True)
class RowCompletionOutputs:
    summary_json: Path
    summary_tsv: Path
    sentinels_tsv: Path
    disagreements_tsv: Path
    report_md: Path


def build_daily_confidence_packet(
    *,
    current_alignment_dir: Path,
    current_health_dir: Path,
    output_dir: Path,
    baseline_alignment_dir: Path | None = None,
    run_id: str = "row_completion_confidence",
    generation_context: str = "unknown",
) -> RowCompletionOutputs:
    output_dir.mkdir(parents=True, exist_ok=True)
    packet = _daily_packet(
        current_alignment_dir=current_alignment_dir,
        current_health_dir=current_health_dir,
        baseline_alignment_dir=baseline_alignment_dir,
        run_id=run_id,
        generation_context=generation_context,
    )
    return _write_outputs(packet=packet, output_dir=output_dir)
```

Implementation requirements:

- Load `alignment_health_summary.json` and `alignment_health_family_sentinels.tsv`.
- Build an input artifact manifest for:
  - `current/alignment_review.tsv`
  - `current/alignment_matrix.tsv`
  - `current/alignment_matrix_identity.tsv`
  - `current/alignment_backfill_cell_evidence.tsv`
  - `current/alignment_owner_backfill_seed_audit.tsv`
  - `current_health/alignment_health_summary.json`
  - `current_health/alignment_health_family_sentinels.tsv`
  - baseline files when `baseline_alignment_dir` is provided.
- Emit a complete diagnostic packet with `run_ok=false`, `gate_ok=false`, `production_safety="inconclusive"`, `review_utility="inconclusive"`, and `missing_evidence_code="metric_source_unavailable"` when a metric-bearing required file is missing. Do not raise a hard CLI error for missing evidence.
- Compute daily metrics from `summary_metrics.row_flag_counts`:
  - `duplicate_only_family_count`
  - `zero_present_family_count`
  - `high_backfill_dependency_count`
  - `accepted_rescue_count`
  - `review_rescue_count`
- Compute `selected_value_drift` by comparing `alignment_matrix.tsv` cell values when a baseline is supplied. Any changed non-empty value sets `authority_decision="expected_diff_required"` and `production_safety="inconclusive"`.
- Write all four TSV/JSON outputs plus Markdown report.
- Write an empty `row_completion_disagreements.tsv` with `external_reviewer_signal=not_available`.
- Include `NO_AUTHORITY_STATEMENT` in JSON and Markdown.

- [ ] **Step 4: Run daily-lane tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_row_completion_confidence_daily.py -q
```

Expected: PASS.

- [ ] **Step 5: Run focused lint**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/diagnostics/row_completion_confidence.py tests/test_row_completion_confidence_daily.py
```

Expected: `All checks passed!`

- [ ] **Step 6: Authorized commit checkpoint**

Only run this step if the user explicitly authorized commits for implementation.

```powershell
git status --short
git add xic_extractor/diagnostics/row_completion_confidence.py tests/test_row_completion_confidence_daily.py
git commit -m "diagnostics: add row completion daily lane"
```

Expected: commit succeeds without staging unrelated dirty files.

---

### Task 3: Canonical Panel And Gate Evaluation

**Files:**
- Create: `xic_extractor/diagnostics/row_completion_confidence_panel.py`
- Create: `docs/superpowers/validation/row_completion_canonical_panel_v1.tsv`
- Create: `docs/superpowers/validation/row_completion_canonical_panel_manifest_v1.json`
- Test: `tests/test_row_completion_confidence_panel.py`

**Interfaces:**
- Consumes:
  - `SCHEMA_VERSION`
  - targeted GT `comparison.csv` produced by `tools/diagnostics/targeted_gt_alignment_audit.py`
  - canonical panel manifest JSON
  - current and baseline sentinel summaries from row-completion or alignment-health packets
- Produces:
  - `load_canonical_panel(panel_tsv: Path) -> Sequence[CanonicalPanelCase]`
  - `evaluate_gate_panel(panel_tsv: Path, *, panel_manifest: Path, targeted_gt_dirs: Mapping[str, Path], current_sentinel_summary: Mapping[str, object], baseline_sentinel_summary: Mapping[str, object] | None) -> GatePanelResult`

- [ ] **Step 1: Add canonical panel files**

Create `docs/superpowers/validation/row_completion_canonical_panel_v1.tsv` with exactly this header and starter rows:

```text
case_id	case_type	target_label	feature_family_id	sample_stem	expected_outcome	production_safety_expectation	review_utility_expectation	required_artifacts	baseline_binding	manual_review_trigger	reason
gt_5medc_summary	targeted_gt_summary	5-medC			no_new_split_or_miss	no_regression	recall_stable_or_better	targeted_gt_comparison	baseline_required	on_warn_fail	5-medC targeted GT checkpoint
gt_5hmdc_summary	targeted_gt_summary	5-hmdC			no_new_split_or_miss	no_regression	recall_stable_or_better	targeted_gt_comparison	baseline_required	on_warn_fail	5-hmdC targeted GT checkpoint
sentinel_duplicate_only	duplicate_only				no_new_duplicate_only_production	lower_duplicate_pressure	sentinels	baseline_required	on_any_current	duplicate-only production pressure must not increase
sentinel_zero_present	zero_present				no_new_zero_present_production	lower_zero_present_pressure	sentinels	baseline_required	on_any_current	zero-present production pressure must not increase
sentinel_high_backfill_dependency	high_backfill_dependency				no_unapproved_high_backfill_dependency	lower_backfill_pressure	sentinels	baseline_required	on_increase	high-backfill dependency should not expand without review
sentinel_ambiguous_owner	ambiguous_ms1_owner				no_unapproved_ambiguous_owner_increase	lower_owner_ambiguity	sentinels	baseline_required	on_increase	ambiguous owner pressure should not expand without review
```

Create `docs/superpowers/validation/row_completion_canonical_panel_manifest_v1.json`:

```json
{
  "schema_version": "row_completion_canonical_panel_manifest_v1",
  "panel_tsv": "docs/superpowers/validation/row_completion_canonical_panel_v1.tsv",
  "required_case_count": 6,
  "status": "diagnostic_only",
  "authority": "no_control_plane_change",
  "notes": [
    "Targeted GT summary cases consume targeted_gt_alignment_audit comparison.csv outputs.",
    "Sentinel cases consume row_completion_sentinels.tsv and alignment_health_packet summaries.",
    "Rows with blank feature_family_id are category-level checks and must fail closed if their required artifact is missing."
  ]
}
```

- [ ] **Step 2: Write failing panel tests**

Create `tests/test_row_completion_confidence_panel.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from xic_extractor.diagnostics.row_completion_confidence_panel import (
    evaluate_gate_panel,
    load_canonical_panel,
)


def test_load_canonical_panel_requires_columns(tmp_path: Path) -> None:
    panel = tmp_path / "panel.tsv"
    panel.write_text("case_id\tcase_type\ncase1\ttargeted_gt_summary\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required columns"):
        load_canonical_panel(panel)


def test_gate_panel_passes_only_when_full_canonical_panel_is_bound(
    tmp_path: Path,
) -> None:
    panel = _write_panel(tmp_path / "panel.tsv", include_hmdc=True)
    manifest = _write_panel_manifest(tmp_path / "panel_manifest.json")
    gt_5medc = _write_targeted_gt_dir(
        tmp_path / "5medc",
        rows=[
            {"sample_stem": "S1", "failure_mode": "PASS"},
            {"sample_stem": "S2", "failure_mode": "PASS"},
        ],
    )
    gt_5hmdc = _write_targeted_gt_dir(
        tmp_path / "5hmdc",
        rows=[
            {"sample_stem": "S3", "failure_mode": "PASS"},
            {"sample_stem": "S4", "failure_mode": "PASS"},
        ],
    )

    result = evaluate_gate_panel(
        panel,
        panel_manifest=manifest,
        targeted_gt_dirs={"5-medC": gt_5medc, "5-hmdC": gt_5hmdc},
        current_sentinel_summary={"duplicate_only_family_count": 0},
        baseline_sentinel_summary={"duplicate_only_family_count": 0},
    )

    assert result.status == "PASS"
    assert result.gate_ok is True
    assert result.production_ready is False
    assert result.manual_review_required is False


@pytest.mark.parametrize("failure_mode", ["SPLIT", "MISS", "DRIFT", "DUPLICATE"])
def test_gate_panel_fails_on_targeted_gt_regression(
    tmp_path: Path,
    failure_mode: str,
) -> None:
    panel = _write_panel(tmp_path / "panel.tsv")
    manifest = _write_panel_manifest(tmp_path / "panel_manifest.json")
    gt_5medc = _write_targeted_gt_dir(
        tmp_path / "5medc",
        rows=[
            {"sample_stem": "S1", "failure_mode": "PASS"},
            {"sample_stem": "S2", "failure_mode": failure_mode},
        ],
    )

    result = evaluate_gate_panel(
        panel,
        panel_manifest=manifest,
        targeted_gt_dirs={"5-medC": gt_5medc},
        current_sentinel_summary={"duplicate_only_family_count": 0},
        baseline_sentinel_summary={"duplicate_only_family_count": 0},
    )

    assert result.status == "FAIL"
    assert result.gate_ok is False
    assert result.manual_review_required is True
    assert "targeted GT regression" in result.reason


def test_gate_panel_is_inconclusive_when_second_required_gt_is_missing(
    tmp_path: Path,
) -> None:
    panel = _write_panel(tmp_path / "panel.tsv", include_hmdc=True)
    manifest = _write_panel_manifest(
        tmp_path / "panel_manifest.json",
        required_case_count=2,
    )
    gt_5medc = _write_targeted_gt_dir(
        tmp_path / "5medc",
        rows=[{"sample_stem": "S1", "failure_mode": "PASS"}],
    )

    result = evaluate_gate_panel(
        panel,
        panel_manifest=manifest,
        targeted_gt_dirs={"5-medC": gt_5medc},
        current_sentinel_summary={"duplicate_only_family_count": 0},
        baseline_sentinel_summary={"duplicate_only_family_count": 0},
    )

    assert result.status == "INCONCLUSIVE"
    assert result.gate_ok is False
    assert result.missing_evidence_code == "canonical_panel_case_unbound"


def test_gate_panel_warns_when_sentinel_pressure_increases(tmp_path: Path) -> None:
    panel = _write_panel(tmp_path / "panel.tsv", targeted_only=False)
    manifest = _write_panel_manifest(tmp_path / "panel_manifest.json")

    result = evaluate_gate_panel(
        panel,
        panel_manifest=manifest,
        targeted_gt_dirs={},
        current_sentinel_summary={"duplicate_only_family_count": 2},
        baseline_sentinel_summary={"duplicate_only_family_count": 0},
    )

    assert result.status == "WARN"
    assert result.gate_ok is False
    assert result.manual_review_required is True
    assert result.missing_evidence_code == "manual_review_required"


def test_gate_panel_is_inconclusive_without_sentinel_baseline(tmp_path: Path) -> None:
    panel = _write_panel(tmp_path / "panel.tsv", targeted_only=False)
    manifest = _write_panel_manifest(tmp_path / "panel_manifest.json")

    result = evaluate_gate_panel(
        panel,
        panel_manifest=manifest,
        targeted_gt_dirs={},
        current_sentinel_summary={"duplicate_only_family_count": 0},
        baseline_sentinel_summary=None,
    )

    assert result.status == "INCONCLUSIVE"
    assert result.gate_ok is False
    assert result.missing_evidence_code == "baseline_current_unbound"


def _write_panel(
    path: Path,
    *,
    include_hmdc: bool = False,
    targeted_only: bool = True,
) -> Path:
    rows = [
        "gt_5medc_summary\ttargeted_gt_summary\t5-medC\t\t\t"
        "no_new_split_or_miss\tno_regression\trecall_stable_or_better\t"
        "targeted_gt_comparison\tbaseline_required\ton_warn_fail\t"
        "5-medC targeted GT checkpoint",
    ]
    if include_hmdc:
        rows.append(
            "gt_5hmdc_summary\ttargeted_gt_summary\t5-hmdC\t\t\t"
            "no_new_split_or_miss\tno_regression\trecall_stable_or_better\t"
            "targeted_gt_comparison\tbaseline_required\ton_warn_fail\t"
            "5-hmdC targeted GT checkpoint",
        )
    if not targeted_only:
        rows = [
            "sentinel_duplicate_only\tduplicate_only\t\t\t\t"
            "no_new_duplicate_only_production\tlower_duplicate_pressure\t"
            "sentinels\tbaseline_required\ton_any_current\t"
            "duplicate-only production pressure must not increase",
        ]
    path.write_text(
        "case_id\tcase_type\ttarget_label\tfeature_family_id\tsample_stem\t"
        "expected_outcome\tproduction_safety_expectation\t"
        "review_utility_expectation\trequired_artifacts\tbaseline_binding\t"
        "manual_review_trigger\treason\n"
        + "\n".join(rows)
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_panel_manifest(path: Path, *, required_case_count: int = 1) -> Path:
    path.write_text(
        '{"schema_version":"row_completion_canonical_panel_manifest_v1",'
        f'"required_case_count":{required_case_count},'
        '"status":"diagnostic_only"}\n',
        encoding="utf-8",
    )
    return path


def _write_targeted_gt_dir(path: Path, *, rows: list[dict[str, str]]) -> Path:
    path.mkdir()
    columns = ("sample_stem", "failure_mode")
    with (path / "comparison.csv").open("w", encoding="utf-8", newline="") as handle:
        handle.write(",".join(columns) + "\n")
        for row in rows:
            handle.write(f"{row['sample_stem']},{row['failure_mode']}\n")
    return path
```

- [ ] **Step 3: Run failing panel tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_row_completion_confidence_panel.py -q
```

Expected: FAIL because `row_completion_confidence_panel.py` does not exist.

- [ ] **Step 4: Implement panel loader and evaluator**

Create `xic_extractor/diagnostics/row_completion_confidence_panel.py` with:

```python
@dataclass(frozen=True)
class CanonicalPanelCase:
    case_id: str
    case_type: str
    target_label: str
    feature_family_id: str
    sample_stem: str
    expected_outcome: str
    production_safety_expectation: str
    review_utility_expectation: str
    required_artifacts: str
    baseline_binding: str
    manual_review_trigger: str
    reason: str


@dataclass(frozen=True)
class GatePanelResult:
    status: str
    gate_ok: bool
    production_ready: bool
    reason: str
    manual_review_required: bool
    missing_evidence_code: str
```

Implementation requirements:

- Use `read_tsv_with_header` for panel TSV.
- Load and validate `row_completion_canonical_panel_manifest_v1.json`; fail closed if the manifest schema/version is missing or `required_case_count` does not match the loaded panel.
- Use `csv.DictReader` for targeted GT `comparison.csv`.
- Require every targeted GT summary case in the loaded panel to have a matching entry in `targeted_gt_dirs`; the starter panel requires both `5-medC` and `5-hmdC`.
- Require `comparison.csv` to include `sample_stem` and `failure_mode`; missing comparison columns return `INCONCLUSIVE` with `missing_required_column`.
- Treat targeted GT `PASS` as passing.
- Treat `SPLIT`, `MISS`, `DRIFT`, and `DUPLICATE` as `FAIL` for version 1 target summary cases.
- If a required targeted GT directory or `comparison.csv` is absent, return `INCONCLUSIVE` with `canonical_panel_case_unbound`.
- Require current and baseline sentinel summaries for sentinel cases. Missing baseline/current binding returns `INCONCLUSIVE` with `baseline_current_unbound`.
- If sentinel pressure increases relative to baseline, return `WARN`, `gate_ok=false`, `manual_review_required=true`, and `missing_evidence_code="manual_review_required"`.
- `production_ready` must always be `False` in version 1; this gate reports product-gate candidacy, not production readiness.
- Do not call `targeted_gt_alignment_audit.py`; consume its existing outputs only.

- [ ] **Step 5: Run panel tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_row_completion_confidence_panel.py -q
```

Expected: PASS.

- [ ] **Step 6: Run focused lint**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/diagnostics/row_completion_confidence_panel.py tests/test_row_completion_confidence_panel.py
```

Expected: `All checks passed!`

- [ ] **Step 7: Authorized commit checkpoint**

Only run this step if the user explicitly authorized commits for implementation.

```powershell
git status --short
git add xic_extractor/diagnostics/row_completion_confidence_panel.py tests/test_row_completion_confidence_panel.py docs/superpowers/validation/row_completion_canonical_panel_v1.tsv docs/superpowers/validation/row_completion_canonical_panel_manifest_v1.json
git commit -m "diagnostics: add row completion gate panel"
```

Expected: commit succeeds without staging unrelated dirty files.

---

### Task 4: External Reviewer Schema Pregate

**Files:**
- Create: `xic_extractor/diagnostics/row_completion_confidence_external.py`
- Test: `tests/test_row_completion_confidence_external.py`

**Interfaces:**
- Produces:
  - `ExternalPregateResult`
  - `validate_external_feature_table(path: Path | None) -> ExternalPregateResult`

- [ ] **Step 1: Write failing external pregate tests**

Create `tests/test_row_completion_confidence_external.py`:

```python
from __future__ import annotations

from pathlib import Path

from xic_extractor.diagnostics.row_completion_confidence_external import (
    validate_external_feature_table,
)


def test_external_pregate_is_not_available_when_absent() -> None:
    result = validate_external_feature_table(None)

    assert result.status == "not_available"
    assert result.mapping_status == "not_available"


def test_external_pregate_fails_missing_required_column(tmp_path: Path) -> None:
    table = tmp_path / "external.tsv"
    table.write_text(
        "external_tool\texternal_run_id\tsample_id\nMZmine\trun1\tS1\n",
        encoding="utf-8",
    )

    result = validate_external_feature_table(table)

    assert result.status == "FAIL"
    assert result.missing_evidence_code == "missing_required_column"
    assert "external_tool_version" in result.reason


def test_external_pregate_marks_schema_only_table_as_mapping_unavailable(
    tmp_path: Path,
) -> None:
    table = tmp_path / "external.tsv"
    table.write_text(
        "external_tool\texternal_run_id\texternal_tool_version\t"
        "external_adapter_version\tsample_id\tfeature_id\tmz\trt\t"
        "area_or_intensity\tarea_or_intensity_semantics\t"
        "mz_tolerance_unit\trt_tolerance_unit\tduplicate_feature_policy\t"
        "missing_value_policy\n"
        "MZmine\trun1\t4.9.14\tcontract_v1\tS1\tF1\t100.1\t5.2\t"
        "12345\tarea\tppm\tminutes\tbest_quality_score\tblank_is_missing\n",
        encoding="utf-8",
    )

    result = validate_external_feature_table(table)

    assert result.status == "schema_valid"
    assert result.mapping_status == "schema_valid_mapping_quality_unavailable"
    assert result.row_count == 1
```

- [ ] **Step 2: Run failing external pregate tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_row_completion_confidence_external.py -q
```

Expected: FAIL because `row_completion_confidence_external.py` does not exist.

- [ ] **Step 3: Implement schema-only external pregate**

Create `xic_extractor/diagnostics/row_completion_confidence_external.py`:

```python
@dataclass(frozen=True)
class ExternalPregateResult:
    status: str
    mapping_status: str
    reason: str
    missing_evidence_code: str
    row_count: int
```

Implementation requirements:

- Required columns:
  - `external_tool`
  - `external_run_id`
  - `external_tool_version`
  - `external_adapter_version`
  - `sample_id`
  - `feature_id`
  - `mz`
  - `rt`
  - `area_or_intensity`
  - `area_or_intensity_semantics`
  - `mz_tolerance_unit`
  - `rt_tolerance_unit`
  - `duplicate_feature_policy`
  - `missing_value_policy`
- Use `read_tsv_with_header`.
- Return `not_available` when `path is None`.
- Return `FAIL` with `missing_required_column` on missing columns.
- Return `status="schema_valid"` and `mapping_status="schema_valid_mapping_quality_unavailable"` when required columns are present. Do not return `PASS` because version 1 does not prove external-to-XIC row mapping quality.
- Do not classify disagreements.
- Do not map external features to XIC rows.

- [ ] **Step 4: Run external pregate tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_row_completion_confidence_external.py -q
```

Expected: PASS.

- [ ] **Step 5: Run focused lint**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/diagnostics/row_completion_confidence_external.py tests/test_row_completion_confidence_external.py
```

Expected: `All checks passed!`

- [ ] **Step 6: Authorized commit checkpoint**

Only run this step if the user explicitly authorized commits for implementation.

```powershell
git status --short
git add xic_extractor/diagnostics/row_completion_confidence_external.py tests/test_row_completion_confidence_external.py
git commit -m "diagnostics: add external reviewer schema pregate"
```

Expected: commit succeeds without staging unrelated dirty files.

---

### Task 5: Thin CLI And Diagnostics Index

**Files:**
- Create: `tools/diagnostics/row_completion_confidence.py`
- Modify: `tools/diagnostics/INDEX.md`
- Test: `tests/test_row_completion_confidence_cli.py`

**Interfaces:**
- Consumes:
  - `build_daily_confidence_packet`
- Produces:
  - CLI command `python -m tools.diagnostics.row_completion_confidence`

Version 1 CLI scope:

- Expose only the daily artifact-lane packet.
- Keep canonical panel evaluation and external schema pregate as package APIs with focused tests in version 1. Do not add public CLI flags for those lanes until their output schemas and runbook are stable.

- [ ] **Step 1: Write failing CLI test**

Create `tests/test_row_completion_confidence_cli.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from tools.diagnostics import row_completion_confidence as cli


def test_cli_writes_row_completion_outputs(tmp_path: Path) -> None:
    current = _write_alignment_artifacts(tmp_path / "current")
    health = _write_health_packet(tmp_path / "health")
    output = tmp_path / "out"

    code = cli.main(
        [
            "--current-alignment-dir",
            str(current),
            "--current-health-dir",
            str(health),
            "--output-dir",
            str(output),
            "--run-id",
            "cli_synthetic",
            "--generation-context",
            "synthetic_cli",
        ],
    )

    assert code == 0
    assert (output / "row_completion_confidence_summary.json").is_file()
    packet = json.loads(
        (output / "row_completion_confidence_summary.json").read_text(
            encoding="utf-8",
        ),
    )
    assert packet["run_id"] == "cli_synthetic"
    assert packet["authority_decision"] == "no_control_plane_change"


def test_cli_packetizes_missing_required_evidence(tmp_path: Path) -> None:
    current = _write_alignment_artifacts(tmp_path / "current")
    (current / "alignment_owner_backfill_seed_audit.tsv").unlink()
    health = _write_health_packet(tmp_path / "health")
    output = tmp_path / "out"

    code = cli.main(
        [
            "--current-alignment-dir",
            str(current),
            "--current-health-dir",
            str(health),
            "--output-dir",
            str(output),
            "--run-id",
            "cli_missing_evidence",
            "--generation-context",
            "synthetic_cli",
        ],
    )

    assert code == 0
    packet = json.loads(
        (output / "row_completion_confidence_summary.json").read_text(
            encoding="utf-8",
        ),
    )
    assert packet["run_ok"] is False
    assert packet["gate_ok"] is False
    assert packet["missing_evidence_code"] == "metric_source_unavailable"


def _write_alignment_artifacts(path: Path) -> Path:
    path.mkdir()
    (path / "alignment_matrix.tsv").write_text(
        "Mz\tRT\tSampleA\n100\t5\t10\n",
        encoding="utf-8",
    )
    (path / "alignment_matrix_identity.tsv").write_text(
        "peak_hypothesis_id\tmatrix_row_index\tsource_feature_family_ids\t"
        "evidence_status\nP1\t1\tFAM1\tcomplete\n",
        encoding="utf-8",
    )
    (path / "alignment_review.tsv").write_text(
        "feature_family_id\tdetected_count\tambiguous_ms1_owner_count\t"
        "duplicate_assigned_count\tunchecked_count\taccepted_cell_count\t"
        "accepted_rescue_count\treview_rescue_count\tidentity_decision\t"
        "identity_confidence\tprimary_evidence\trow_flags\treason\n"
        "FAM1\t1\t0\t0\t0\t1\t0\t0\tproduction_family\thigh\towner\t\tok\n",
        encoding="utf-8",
    )
    (path / "alignment_backfill_cell_evidence.tsv").write_text(
        "schema_version\tfeature_family_id\tsample_stem\tstatus\t"
        "bounded_by_alignment_row\treason\n"
        "alignment_backfill_cell_evidence_v1\tFAM1\tSampleA\t"
        "not_needed\ttrue\tok\n",
        encoding="utf-8",
    )
    (path / "alignment_owner_backfill_seed_audit.tsv").write_text(
        "schema_version\tfeature_family_id\tsample_stem\tstatus\t"
        "seed_source\treason\n"
        "alignment_owner_backfill_seed_audit_v1\tFAM1\tSampleA\t"
        "not_needed\towner\tok\n",
        encoding="utf-8",
    )
    return path


def _write_health_packet(path: Path) -> Path:
    path.mkdir()
    packet = {
        "schema_version": "alignment_health_packet_v1",
        "summary_metrics": {
            "row_flag_counts": {},
            "accepted_rescue_count_total": 0,
            "review_rescue_count_total": 0,
            "sentinel_count": 0,
        },
        "sentinel_rows": [],
        "status": "diagnostic_only",
    }
    (path / "alignment_health_summary.json").write_text(
        json.dumps(packet, indent=2) + "\n",
        encoding="utf-8",
    )
    (path / "alignment_health_family_sentinels.tsv").write_text(
        "rank\tfeature_family_id\tissue_class\tseverity_score\t"
        "recommended_action\treason\n",
        encoding="utf-8",
    )
    return path
```

- [ ] **Step 2: Run failing CLI test**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_row_completion_confidence_cli.py -q
```

Expected: FAIL because `tools/diagnostics/row_completion_confidence.py` does not exist.

- [ ] **Step 3: Implement thin CLI**

Create `tools/diagnostics/row_completion_confidence.py`:

```python
"""Build a diagnostic-only row-completion confidence packet."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from xic_extractor.diagnostics.row_completion_confidence import (
    build_daily_confidence_packet,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    outputs = build_daily_confidence_packet(
        current_alignment_dir=args.current_alignment_dir,
        current_health_dir=args.current_health_dir,
        output_dir=args.output_dir,
        baseline_alignment_dir=args.baseline_alignment_dir,
        run_id=args.run_id,
        generation_context=args.generation_context,
    )
    print(f"Row completion summary JSON: {outputs.summary_json}")
    print(f"Row completion summary TSV: {outputs.summary_tsv}")
    print(f"Row completion sentinels TSV: {outputs.sentinels_tsv}")
    print(f"Row completion disagreements TSV: {outputs.disagreements_tsv}")
    print(f"Row completion report MD: {outputs.report_md}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build diagnostic-only row-completion confidence outputs.",
    )
    parser.add_argument("--current-alignment-dir", type=Path, required=True)
    parser.add_argument("--current-health-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--baseline-alignment-dir", type=Path)
    parser.add_argument("--run-id", default="row_completion_confidence")
    parser.add_argument("--generation-context", default="unknown")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
```

Implementation requirements:

- `build_daily_confidence_packet` must write an `INCONCLUSIVE` packet for missing required evidence instead of raising `FileNotFoundError`.
- The CLI returns `0` when a diagnostic packet is written, even if `run_ok=false`.
- The CLI remains daily-lane only in version 1. Do not expose canonical-panel or external-reviewer flags in this task.
- Return `2` only for argparse failures or genuinely non-recoverable output-write failures.

- [ ] **Step 4: Update diagnostics index**

Modify `tools/diagnostics/INDEX.md`:

- Increment the total entry-point count.
- Add `row_completion_confidence.py` under Alignment Diagnostics or a Row Completion/Matrix Diagnostics section.
- Include this status language:

```markdown
Status: diagnostic_only. Builds manifest-bound row-completion confidence outputs from existing alignment health and matrix artifacts. Does not open RAW, recompute evidence, run mature tools, alter matrix authority, or change selected values/counting.
```

- [ ] **Step 5: Run CLI tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_row_completion_confidence_cli.py -q
```

Expected: PASS.

- [ ] **Step 6: Run focused lint**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools/diagnostics/row_completion_confidence.py tests/test_row_completion_confidence_cli.py
```

Expected: `All checks passed!`

- [ ] **Step 7: Authorized commit checkpoint**

Only run this step if the user explicitly authorized commits for implementation.

```powershell
git status --short
git add tools/diagnostics/row_completion_confidence.py tools/diagnostics/INDEX.md tests/test_row_completion_confidence_cli.py
git commit -m "diagnostics: add row completion confidence CLI"
```

Expected: commit succeeds without staging unrelated dirty files.

---

### Task 6: Focused Validation And No-RAW Smoke

**Files:**
- No source file creation required.
- May create normal output artifacts under `output/diagnostics/row_completion_confidence_8raw_20260623/`.

**Interfaces:**
- Consumes:
  - Existing 8RAW alignment artifact directory.
  - Existing `alignment_health_packet_8raw_20260623` output.
- Produces:
  - Validation summary for closeout.

- [ ] **Step 1: Run all focused row-completion tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest `
  tests/test_row_completion_confidence_schema.py `
  tests/test_row_completion_confidence_daily.py `
  tests/test_row_completion_confidence_panel.py `
  tests/test_row_completion_confidence_external.py `
  tests/test_row_completion_confidence_cli.py `
  -q
```

Expected: all tests PASS.

- [ ] **Step 2: Run focused lint for all new code**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check `
  xic_extractor/diagnostics/row_completion_confidence_schema.py `
  xic_extractor/diagnostics/row_completion_confidence.py `
  xic_extractor/diagnostics/row_completion_confidence_panel.py `
  xic_extractor/diagnostics/row_completion_confidence_external.py `
  tools/diagnostics/row_completion_confidence.py `
  tests/test_row_completion_confidence_schema.py `
  tests/test_row_completion_confidence_daily.py `
  tests/test_row_completion_confidence_panel.py `
  tests/test_row_completion_confidence_external.py `
  tests/test_row_completion_confidence_cli.py
```

Expected: `All checks passed!`

- [ ] **Step 3: Run no-RAW 8RAW smoke when the required artifact directories exist**

Check:

```powershell
Test-Path output\performance\dna_dr_product_ready_8raw_stage_replay_cache_reviewfix_v3_20260623
Test-Path output\diagnostics\alignment_health_packet_8raw_20260623
```

If both commands return `True`, run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python -m tools.diagnostics.row_completion_confidence `
  --current-alignment-dir output\performance\dna_dr_product_ready_8raw_stage_replay_cache_reviewfix_v3_20260623 `
  --current-health-dir output\diagnostics\alignment_health_packet_8raw_20260623 `
  --output-dir output\diagnostics\row_completion_confidence_8raw_20260623 `
  --run-id row_completion_confidence_8raw_20260623 `
  --generation-context dna_dr_product_ready_8raw_stage_replay_cache_reviewfix_v3_20260623
```

Expected:

- command exits `0`;
- writes `row_completion_confidence_summary.json`;
- if all required evidence files are present, JSON contains `diagnostic_only`, `run_ok=true`, `gate_ok=true`, and `authority_decision=no_control_plane_change`;
- if bounded backfill or other required evidence files are missing, JSON contains `diagnostic_only`, `run_ok=false`, `gate_ok=false`, `production_safety=inconclusive`, `review_utility=inconclusive`, and a non-empty `missing_evidence_code`; this is a valid fail-closed smoke result, not a success gate;
- no RAW command is launched.

If either path is missing, do not rerun 8RAW. Record smoke as skipped because required existing artifacts are absent.

- [ ] **Step 4: Inspect smoke summary**

Run:

```powershell
$j = Get-Content output\diagnostics\row_completion_confidence_8raw_20260623\row_completion_confidence_summary.json -Raw | ConvertFrom-Json
[pscustomobject]@{
  run_ok = $j.run_ok
  production_safety = $j.production_safety
  review_utility = $j.review_utility
  authority_decision = $j.authority_decision
  manual_review_required = $j.manual_review_required
} | Format-List
```

Expected:

- `authority_decision` is `no_control_plane_change`;
- `run_ok` is `True` only when every required evidence artifact is present; otherwise it is `False` with `missing_evidence_code`;
- `production_safety` and `review_utility` are one of `improved`, `stable`, `regressed`, or `inconclusive`.

- [ ] **Step 5: Report validation tier honestly**

Closeout wording must include:

```text
Validation tier: focused synthetic tests plus optional no-RAW 8RAW artifact smoke.
This is diagnostic_only and not PR-ready unless the full repo gate is run.
No control-plane update is needed because maturity tier, active lane, writer authority, selected values, counted detections, schemas, and default preset behavior are unchanged.
```

- [ ] **Step 6: Authorized final commit checkpoint**

Only run this step if the user explicitly authorized commits for implementation.

```powershell
git status --short
git add `
  xic_extractor/diagnostics/row_completion_confidence_schema.py `
  xic_extractor/diagnostics/row_completion_confidence.py `
  xic_extractor/diagnostics/row_completion_confidence_panel.py `
  xic_extractor/diagnostics/row_completion_confidence_external.py `
  tools/diagnostics/row_completion_confidence.py `
  tools/diagnostics/INDEX.md `
  tests/test_row_completion_confidence_schema.py `
  tests/test_row_completion_confidence_daily.py `
  tests/test_row_completion_confidence_panel.py `
  tests/test_row_completion_confidence_external.py `
  tests/test_row_completion_confidence_cli.py `
  docs/superpowers/validation/row_completion_canonical_panel_v1.tsv `
  docs/superpowers/validation/row_completion_canonical_panel_manifest_v1.json
git diff --cached --check
git commit -m "diagnostics: add row completion confidence benchmark"
```

Expected: commit succeeds only after explicit commit authorization.

---

## Self-Review Notes

Spec coverage:

- A-first/B-secondary scope is implemented by Tasks 2, 3, and 4.
- Package-owned reusable logic is implemented by Tasks 1-4.
- Thin CLI and diagnostics index are implemented by Task 5.
- Artifact freshness and no-RAW behavior are implemented by Task 1 and verified in Task 6.
- Canonical panel location and schema are implemented by Task 3.
- External reviewer lane is schema-only in Task 4.
- Manual review remains trigger-only; no task writes a durable manual-review queue.
- Product authority boundary is tested in Tasks 1, 2, and 6.

Subagent review blocker closure:

- Gate panel cannot pass on partial evidence: full targeted GT cases, sentinel baseline/current binding, manifest `required_case_count`, and comparison columns all fail closed.
- Artifact freshness is manifest-bound: descriptors include `run_id`, manifests reject unknown generation context, and missing metric evidence writes `INCONCLUSIVE` packets instead of hard-failing the CLI.
- Bounded backfill evidence is required in the daily lane: `alignment_backfill_cell_evidence.tsv` and `alignment_owner_backfill_seed_audit.tsv` are required manifest inputs and covered by missing-evidence tests.
- External reviewer schema validation is not mislabeled as mapping success: schema-valid tables return `schema_valid_mapping_quality_unavailable`, not `PASS`.
- CLI public surface is aligned with implementation: version 1 exposes only the daily artifact-lane packet; panel and external evaluators remain package APIs.
- Type and output invariants are explicit: status aliases include schema-only states, summary columns are exact-order tested, and `production_ready` stays `False` for this diagnostic-only benchmark.

Placeholder scan:

- This plan intentionally contains no unresolved placeholder markers, no unbound future parser, and no mature-tool adapter work.
- Any skipped 8RAW smoke must be reported as skipped, not silently replaced by a rerun.

Type consistency:

- `ArtifactDescriptor`, `FreshnessDecision`, and `RowCompletionOutputs` are introduced before use.
- Package APIs are consumed only after their defining task.
- CLI consumes only `build_daily_confidence_packet` in version 1.
