# Backfill Evidence Reconciliation Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backfill evidence reconciliation index and gallery, then conditionally promote only allowlisted backfill slices when product-grade evidence passes reviewed 8RAW and 85RAW gates.

**Architecture:** Keep product behavior and evidence authority separate. Add a package-owned diagnostic reconciliation module under `xic_extractor/diagnostics/` and a thin CLI under `tools/diagnostics/`; consume existing artifacts only for Slice 0/1. Product-gate changes are conditional and require a reviewed promotion sub-contract.

**Tech Stack:** Python, dataclasses, TSV/JSON/HTML writers, pytest, ruff, existing XIC diagnostic and alignment artifacts.

---

## Source Documents

- Spec: `docs/superpowers/specs/2026-06-07-backfill-evidence-reconciliation-gallery-design.md`
- Goal: `docs/superpowers/goals/2026-06-07-backfill-evidence-reconciliation-productization-goal.md`
- Prior product-path plan: `docs/superpowers/plans/2026-06-05-backfill-evidence-gate-productization.md`
- Product authority addendum: `docs/superpowers/plans/2026-06-05-product-authority-reconciliation-v1.md`
- Backfill review notes:
  - `docs/superpowers/notes/2026-05-19-seed-aware-backfill-review-index.md`
  - `docs/superpowers/notes/2026-05-19-untargeted-ms1-coherence-backfill-review.md`
- Routing / validation rules:
  - `AGENTS.md`
  - `docs/agent-subagent-routing.md`
  - `docs/agent-parameter-settings.md`
  - `docs/architecture-contract.md`

## File Structure

Create:

- `xic_extractor/diagnostics/backfill_reconciliation_gallery.py`
  Owns typed TSV adapters, deterministic seed grouping, evidence-authority
  classification, reconciliation classes, representative-cell selection,
  TSV/JSON output rows, and HTML rendering helpers. Reuse
  `xic_extractor.diagnostics.diagnostic_io` for delimited IO, header validation,
  scalar parsing, label splitting, and TSV writing; do not add local
  `_read_required_tsv`, `_write_tsv`, `_bool_value`, or similar copies.
- `tools/diagnostics/backfill_evidence_reconciliation_gallery.py`
  Thin CLI. Parses paths, validates presence of required files, delegates to the
  package module, and prints output paths.
- `tests/test_backfill_evidence_reconciliation_gallery.py`
  Synthetic no-RAW contract tests for grouping, authority mapping,
  representative cells, missing evidence, CLI outputs, HTML escaping, and
  no-composite-score behavior.
- `xic_extractor/diagnostics/retained_backfill_evidence_gate.py`
  Owns the diagnostic-only product-retained backfill evidence gate for actual
  primary-matrix backfill family/seed groups. It consumes existing alignment,
  seed-audit, and overlay artifacts; emits source-hashed support/blocker/missing
  evidence rows; and excludes `detected=0` families from main rows.
- `tools/diagnostics/retained_backfill_evidence_gate.py`
  Thin CLI for writing `alignment_retained_backfill_evidence_gate.tsv` and
  `alignment_retained_backfill_evidence_gate.json`, plus
  `alignment_retained_backfill_missing_overlay_queue.tsv` for rows where seed
  provenance exists but overlay evidence is still missing.
- `tests/test_retained_backfill_evidence_gate.py`
  Synthetic no-RAW contract tests for retained product scope, missing evidence,
  detected-zero exclusion, wide matrix provenance, CLI outputs, and stable
  diagnostic-only summary.

Modify:

- `tools/diagnostics/INDEX.md`
  Add a Backfill Reviews entry for the new diagnostic CLI.
- `docs/superpowers/specs/2026-06-07-backfill-evidence-reconciliation-gallery-design.md`
  Update only if implementation review finds the spec contract was ambiguous.
- `docs/superpowers/notes/<date>-backfill-evidence-reconciliation-productization-note.md`
  Add a closeout note after Slice 0/1 smoke and any validation/promotion result.

Conditional only after Slice 0/1 evidence review:

- `xic_extractor/alignment/production_candidate_gate.py`
- `tools/diagnostics/provisional_backfill_candidate_gate.py`
- Their focused tests

These files are touched only if a reviewed product-grade evidence extension is
needed. Do not change them for gallery-only work.

## Acceptance Summary

- Slice 0 writes stable machine indexes with
  `schema_version=backfill_evidence_reconciliation_v0`.
- Slice 1 renders a table-first HTML gallery from the same source index.
- Product behavior, product-grade support, review-only visual support,
  dependent context, human visual judgment, blockers, and missing evidence remain
  separate in TSV/JSON/HTML.
- No Slice 0/1 code reads RAW, calls DLLs, generates overlays, changes product
  behavior, or creates an aggregate `backfill_score`.
- Product promotion is allowlist-only and requires a separate reviewed
  promotion contract plus 8RAW and 85RAW validation.

## Execution Status

Status as of 2026-06-07 implementation pass:

- Slice 0/1 implemented:
  `xic_extractor/diagnostics/backfill_reconciliation_gallery.py`,
  `tools/diagnostics/backfill_evidence_reconciliation_gallery.py`, and
  `tests/test_backfill_evidence_reconciliation_gallery.py`.
- Implemented review fixes: candidate-gate source hash fail-closed behavior,
  malformed candidate-gate blocker handling, disagreement-first ordering,
  portable input/output/PNG links, dangerous PNG href sanitization, exact
  `validation_label` rendering, and source artifact links in row details.
- Follow-up retained evidence gate implemented:
  `xic_extractor/diagnostics/retained_backfill_evidence_gate.py`,
  `tools/diagnostics/retained_backfill_evidence_gate.py`, and
  `tests/test_retained_backfill_evidence_gate.py`. This targets actual
  `include_in_primary_matrix=TRUE` / `identity_decision=production_family`
  backfill rows instead of the older `provisional_retention_candidate` scope.
- Implemented missing-overlay queue and seed-group overlay provenance:
  retained gate now writes `alignment_retained_backfill_missing_overlay_queue.tsv`,
  and `family_ms1_overlay_batch.py` preserves optional `seed_group_id` into
  `family_ms1_overlay_batch_summary.tsv` so seed-specific overlays do not leak
  across multiple seed groups in the same family.
- Verification after this status block should be read from the closeout note and
  latest command output, not from unchecked task boxes below.
- Tasks 6/7 product promotion remain not attempted. This plan still gates those
  tasks behind a separate reviewed allowlist contract plus 8RAW/85RAW
  validation.

---

## Task 1: Slice 0 RED Tests for Grouping and Evidence Authority

**Files:**
- Create: `tests/test_backfill_evidence_reconciliation_gallery.py`
- Future implementation target: `xic_extractor/diagnostics/backfill_reconciliation_gallery.py`

- [ ] **Step 1: Add schema-backed synthetic fixture helpers**

Add helper rows that exercise product behavior, seed audit, overlay summary,
seed-aware review, and candidate-gate authority. Use plain dict rows so tests do
not depend on real RAW artifacts, but build those dicts from the current public
alignment TSV header constants. This prevents tests from passing with invented
field names that real artifacts never produce.

```python
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from xic_extractor.alignment.tsv_writer import (
    ALIGNMENT_CELLS_COLUMNS,
    ALIGNMENT_OWNER_BACKFILL_SEED_AUDIT_COLUMNS,
    ALIGNMENT_REVIEW_COLUMNS,
)
from xic_extractor.diagnostics import backfill_reconciliation_gallery as gallery


def _blank_row(columns: tuple[str, ...]) -> dict[str, str]:
    return {column: "" for column in columns}


def _review_row(
    family: str,
    *,
    identity_decision: str = "provisional_discovery",
    include_in_primary_matrix: str = "FALSE",
    row_flags: str = "single_detected_seed;provisional_retention_candidate",
    detected: str = "1",
    rescued: str = "2",
) -> dict[str, str]:
    row = _blank_row(ALIGNMENT_REVIEW_COLUMNS)
    row.update(
        {
            "feature_family_id": family,
            "group_hypothesis_id": f"{family}::group",
            "public_family_id": family,
            "group_construction_role": "single_detected_seed",
            "group_delivery_role": "review",
            "group_membership_source": "owner_family",
            "family_center_mz": "269.145",
            "family_center_rt": "10.0000",
            "detected_count": detected,
            "quantifiable_detected_count": detected,
            "quantifiable_rescue_count": rescued,
            "accepted_cell_count": str(int(detected) + int(rescued)),
            "accepted_rescue_count": rescued,
            "review_rescue_count": "0",
            "identity_decision": identity_decision,
            "identity_confidence": "review_only",
            "primary_evidence": "owner_backfill_context",
            "identity_reason": "owner_backfill_context",
            "include_in_primary_matrix": include_in_primary_matrix,
            "row_flags": row_flags,
            "reason": "fixture",
        }
    )
    return row


def _cell_row(
    family: str,
    sample: str,
    status: str,
    *,
    scan_support: str = "0.80",
    apex_rt: str = "10.10",
) -> dict[str, str]:
    row = _blank_row(ALIGNMENT_CELLS_COLUMNS)
    row.update(
        {
            "feature_family_id": family,
            "group_hypothesis_id": f"{family}::group",
            "public_family_id": family,
            "group_construction_role": "single_detected_seed",
            "group_delivery_role": "review",
            "group_membership_source": "owner_family",
            "gap_fill_state": "owner_backfill" if status == "rescued" else "observed",
            "gap_fill_reason": "owner_backfill" if status == "rescued" else "",
            "sample_stem": sample,
            "status": status,
            "area": "1200.0",
            "primary_matrix_area": "1200.0" if status == "detected" else "",
            "primary_matrix_area_source": "detected" if status == "detected" else "",
            "primary_matrix_area_reason": "observed" if status == "detected" else "",
            "apex_rt": apex_rt,
            "scan_support_score": scan_support,
            "reason": "fixture",
        }
    )
    return row


def _seed_row(
    family: str,
    sample: str,
    *,
    seed_mz: str = "269.145",
    seed_rt: str = "10.0000",
    rt_start: str = "9.0000",
    rt_end: str = "11.0000",
    ppm: str = "10",
) -> dict[str, str]:
    row = _blank_row(ALIGNMENT_OWNER_BACKFILL_SEED_AUDIT_COLUMNS)
    row.update(
        {
            "feature_family_id": family,
            "group_hypothesis_id": f"{family}::group",
            "public_family_id": family,
            "group_construction_role": "single_detected_seed",
            "group_delivery_role": "review",
            "group_membership_source": "owner_family",
            "gap_fill_state": "owner_backfill",
            "gap_fill_reason": "owner_backfill",
            "sample_stem": sample,
            "status": "rescued",
            "area": "1200.0",
            "apex_rt": seed_rt,
            "family_center_mz": "269.145",
            "family_center_rt": "10.0000",
            "backfill_seed_mz": seed_mz,
            "backfill_seed_rt": seed_rt,
            "backfill_request_rt_min": rt_start,
            "backfill_request_rt_max": rt_end,
            "backfill_request_ppm": ppm,
            "reason": "fixture",
        }
    )
    return row
```

Add a schema guard test:

```python
def test_test_fixtures_use_real_alignment_writer_columns() -> None:
    assert set(_review_row("FAM001")) == set(ALIGNMENT_REVIEW_COLUMNS)
    assert set(_cell_row("FAM001", "S1", "detected")) == set(ALIGNMENT_CELLS_COLUMNS)
    assert set(_seed_row("FAM001", "S2")) == set(
        ALIGNMENT_OWNER_BACKFILL_SEED_AUDIT_COLUMNS
    )
```

Do not use these non-producer names in tests or implementation:
`matrix_role`, `request_rt_start`, `request_rt_end`, or `request_ppm`.

Reference mapping:

| Intended meaning | Existing producer field |
| --- | --- |
| Product row decision | `identity_decision` |
| Product matrix inclusion | `include_in_primary_matrix` |
| Product row annotations | `row_flags` |
| Seed RT window start | `backfill_request_rt_min` |
| Seed RT window end | `backfill_request_rt_max` |
| Seed ppm request | `backfill_request_ppm` |

- [ ] **Step 2: Add RED test for deterministic seed grouping**

```python
def test_builds_deterministic_seed_group_from_seed_audit() -> None:
    result = gallery.build_reconciliation_index(
        review_rows=[_review_row("FAM001")],
        cell_rows=[
            _cell_row("FAM001", "S1", "detected"),
            _cell_row("FAM001", "S2", "rescued"),
        ],
        seed_audit_rows=[_seed_row("FAM001", "S2")],
    )

    assert len(result.groups) == 1
    group = result.groups[0]
    assert group.feature_family_id == "FAM001"
    assert group.seed_group_basis == "seed_audit"
    assert group.seed_group_id == (
        "seed::FAM001::mz=269.145::rt=10.0000::"
        "window=9.0000-11.0000::ppm=10"
    )
```

Expected before implementation: import or attribute failure.

- [ ] **Step 3: Add RED test for authority separation**

```python
def test_product_grade_and_visual_support_remain_separate() -> None:
    result = gallery.build_reconciliation_index(
        review_rows=[_review_row("FAM002")],
        cell_rows=[_cell_row("FAM002", "S2", "rescued")],
        seed_audit_rows=[_seed_row("FAM002", "S2")],
        candidate_gate_rows=[
            {
                "feature_family_id": "FAM002",
                "candidate_gate_status": "production_candidate",
                "support_components": "validated_tier2_trace_evidence",
                "challenge_blockers": "",
                "tier2_evidence_available": "TRUE",
            }
        ],
        seed_aware_rows=[
            {
                "feature_family_id": "FAM002",
                "review_class": "seed_shape_supported_review_candidate",
                "reason": "seed-specific overlays support MS1 shape",
            }
        ],
    )

    group = result.groups[0]
    assert group.evidence_authority_state == "product_grade_support"
    assert "validated_tier2_trace_evidence" in group.product_grade_support_components
    assert "seed_shape_supported_review_candidate" in group.review_only_visual_components
```

- [ ] **Step 4: Run tests to verify RED**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_backfill_evidence_reconciliation_gallery.py
```

Expected: fail because `backfill_reconciliation_gallery` does not exist yet.

---

## Task 2: Implement Slice 0 Package Models and Classification

**Files:**
- Create: `xic_extractor/diagnostics/backfill_reconciliation_gallery.py`
- Test: `tests/test_backfill_evidence_reconciliation_gallery.py`

- [ ] **Step 1: Create package module skeleton**

Implement the public function and dataclasses used by Task 1 tests.

```python
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

SCHEMA_VERSION = "backfill_evidence_reconciliation_v0"


@dataclass(frozen=True)
class RepresentativeCell:
    feature_family_id: str
    seed_group_id: str
    sample_stem: str
    cell_status: str
    representative_roles: tuple[str, ...]
    source_row_key: str
    shape_similarity: str = ""
    scan_support_score: str = ""
    apex_delta_sec: str = ""
    boundary_overlap: str = ""
    interference_signal: str = ""
    representative_reason: str = ""


@dataclass(frozen=True)
class ReconciliationGroup:
    feature_family_id: str
    seed_group_id: str
    seed_group_basis: str
    seed_mz: str = ""
    seed_rt: str = ""
    seed_rt_window: str = ""
    seed_ppm: str = ""
    product_behavior_state: str = "product_unknown"
    evidence_authority_state: str = "not_assessable"
    reconciliation_class: str = "not_assessable_join_gap"
    detected_cell_count: int = 0
    rescued_cell_count: int = 0
    provisional_cell_count: int = 0
    product_grade_support_components: tuple[str, ...] = ()
    review_only_visual_components: tuple[str, ...] = ()
    dependent_context_components: tuple[str, ...] = ()
    blocker_components: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    source_warnings: tuple[str, ...] = ()
    representative_cells: tuple[RepresentativeCell, ...] = ()


@dataclass(frozen=True)
class ReconciliationIndex:
    groups: tuple[ReconciliationGroup, ...]
    representative_cells: tuple[RepresentativeCell, ...]
    summary: dict[str, object] = field(default_factory=dict)
```

- [ ] **Step 2: Implement deterministic grouping helpers**

```python
def _seed_group_id(
    family: str,
    *,
    seed_mz: str,
    seed_rt: str,
    rt_start: str,
    rt_end: str,
    ppm: str,
) -> str:
    return (
        f"seed::{family}::mz={seed_mz or 'unknown'}::"
        f"rt={seed_rt or 'unknown'}::"
        f"window={rt_start or 'unknown'}-{rt_end or 'unknown'}::"
        f"ppm={ppm or 'unknown'}"
    )


def _fallback_seed_group_id(family: str) -> str:
    return f"family_center::{family}::seed=unknown"
```

- [ ] **Step 3: Implement authority mapping without aggregate scoring**

Rules:

- candidate-gate `production_candidate` with
  `validated_tier2_trace_evidence` becomes `product_grade_support`;
- seed-aware support becomes `review_only_visual_support`;
- seed audit becomes `dependent_context_only` when no stronger evidence exists;
- missing seed audit adds `missing_seed_provenance`;
- missing overlay rows add `missing_overlay` only when no overlay source covers
  the group.

- [ ] **Step 4: Implement `build_reconciliation_index`**

Signature:

```python
def build_reconciliation_index(
    *,
    review_rows: Iterable[Mapping[str, str]],
    cell_rows: Iterable[Mapping[str, str]],
    matrix_rows: Iterable[Mapping[str, str]] = (),
    seed_audit_rows: Iterable[Mapping[str, str]] = (),
    overlay_summary_rows: Iterable[Mapping[str, str]] = (),
    seed_aware_rows: Iterable[Mapping[str, str]] = (),
    candidate_gate_rows: Iterable[Mapping[str, str]] = (),
    tier2_trace_rows: Iterable[Mapping[str, str]] = (),
) -> ReconciliationIndex:
    """Return deterministic reconciliation groups, representative cells, and summary."""
```

Required behavior:

- materialize inputs exactly once so row order is deterministic;
- group by explicit seed audit tuple when present;
- fall back to `family_center::<feature_family_id>::seed=unknown` when seed
  provenance is absent;
- compute product behavior from product artifacts only;
- compute evidence authority from mapped evidence sources only;
- attach missing/stale/join warnings instead of inferring support;
- return groups sorted by reconciliation priority and stable seed key.

- [ ] **Step 5: Run focused tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_backfill_evidence_reconciliation_gallery.py
```

Expected: Task 1 tests pass or fail only on missing later coverage.

---

## Task 3: Slice 0 Output Schemas and CLI

**Files:**
- Modify: `xic_extractor/diagnostics/backfill_reconciliation_gallery.py`
- Create: `tools/diagnostics/backfill_evidence_reconciliation_gallery.py`
- Modify: `tests/test_backfill_evidence_reconciliation_gallery.py`
- Modify: `tools/diagnostics/INDEX.md`

- [ ] **Step 1: Add writer tests for TSV/JSON outputs**

Add tests that call `gallery.write_reconciliation_outputs(output_dir, index)` and assert the full v0 contract, not only happy-path fields:

```python
EXPECTED_GROUP_COLUMNS = (
    "schema_version",
    "priority_rank",
    "feature_family_id",
    "seed_group_id",
    "seed_group_basis",
    "seed_mz",
    "seed_rt",
    "seed_rt_window",
    "seed_ppm",
    "tag_or_class",
    "product_behavior_state",
    "evidence_authority_state",
    "reconciliation_class",
    "detected_cell_count",
    "rescued_cell_count",
    "provisional_cell_count",
    "top_product_reason",
    "top_support_component",
    "top_blocker",
    "missing_evidence",
    "overlay_png_path",
    "overlay_trace_json_path",
    "source_artifacts",
    "source_warnings",
)

EXPECTED_REPRESENTATIVE_CELL_COLUMNS = (
    "schema_version",
    "feature_family_id",
    "seed_group_id",
    "representative_roles",
    "sample_stem",
    "cell_status",
    "product_cell_state",
    "shape_similarity",
    "scan_support_score",
    "apex_delta_sec",
    "boundary_overlap",
    "interference_signal",
    "representative_reason",
    "source_row_key",
)
```

Required assertions:

- `gallery.GROUP_TSV_COLUMNS == EXPECTED_GROUP_COLUMNS`;
- `gallery.REPRESENTATIVE_CELL_TSV_COLUMNS == EXPECTED_REPRESENTATIVE_CELL_COLUMNS`;
- written TSV headers exactly match those constants and do not contain
  `backfill_score`;
- group rows sort by `priority_rank`, then `feature_family_id`, then
  `seed_group_id`;
- representative cell rows sort by `feature_family_id`, `seed_group_id`,
  `sample_stem`, then role priority;
- `schema_version` is `backfill_evidence_reconciliation_v0` on every TSV row and
  in summary JSON;
- summary JSON has `matrix_contract_changed=false` and
  `product_behavior_changed=false`;
- all stable `evidence_authority_state` values have coverage:
  `product_grade_support`, `review_only_visual_support`,
  `dependent_context_only`, `human_visual_judgment_only`,
  `evidence_blocks_backfill`, `evidence_inconclusive`, `not_assessable`;
- all stable reconciliation classes from the spec have coverage:
  `product_accepts_and_product_grade_supports`,
  `product_accepts_and_visual_supports`,
  `product_rejects_but_product_grade_supports`,
  `product_rejects_but_visual_supports`,
  `product_accepts_but_evidence_conflicts`,
  `product_rejects_and_evidence_blocks`,
  `evidence_inconclusive`,
  `not_assessable_missing_overlay`,
  `not_assessable_missing_seed_provenance`,
  `not_assessable_join_gap`;
- missing/stale/join-gap source problems are rendered as explicit
  `missing_*`, `stale_*`, or `join_gap_*` tokens in `missing_evidence` or
  `source_warnings`, never silently upgraded into support.

- [ ] **Step 2: Implement TSV/JSON writers in package module**

Public function:

```python
def write_reconciliation_outputs(
    output_dir: Path,
    index: ReconciliationIndex,
) -> dict[str, Path]:
    """Write groups TSV, representative-cells TSV, and summary JSON."""
```

Writers must use UTF-8, tab-delimited TSVs, deterministic row order, and stable
column order from the spec.

- [ ] **Step 3: Add thin CLI**

CLI responsibilities only:

- parse arguments;
- confirm required paths exist;
- call package `load_*` adapters, builder, and writers; those package adapters
  must use `xic_extractor.diagnostics.diagnostic_io` for actual delimited IO;
- print written output paths;
- return non-zero with a clear message when required inputs are missing.

Required CLI path:

```text
tools/diagnostics/backfill_evidence_reconciliation_gallery.py
```

- [ ] **Step 4: Update diagnostic index**

Add an entry under `tools/diagnostics/INDEX.md` Backfill Reviews:

```markdown
### `backfill_evidence_reconciliation_gallery.py`

**Purpose**: Build a `diagnostic_only` / `shadow_review` reconciliation index
and HTML gallery for all backfill family/seed groups by joining existing
product, seed provenance, candidate-gate, seed-aware, and overlay artifacts.
**Topic group**: `backfill_evidence_reconciliation_gallery.py` +
`xic_extractor/diagnostics/backfill_reconciliation_gallery.py`
**Originating spec/goal/plan**:
`specs/2026-06-07-backfill-evidence-reconciliation-gallery-design.md`;
`goals/2026-06-07-backfill-evidence-reconciliation-productization-goal.md`;
`plans/2026-06-07-backfill-evidence-reconciliation-productization-plan.md`
**Status note**: Consumes existing artifacts only; does not read RAW/DLL,
generate overlays, compute product evidence, mutate alignment outputs, or
promote backfill behavior.
```

- [ ] **Step 5: Run focused tests and ruff**

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_backfill_evidence_reconciliation_gallery.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools/diagnostics/backfill_evidence_reconciliation_gallery.py xic_extractor/diagnostics/backfill_reconciliation_gallery.py tests/test_backfill_evidence_reconciliation_gallery.py
```

---

## Task 4: Slice 1 HTML Gallery Renderer

**Files:**
- Modify: `xic_extractor/diagnostics/backfill_reconciliation_gallery.py`
- Modify: `tests/test_backfill_evidence_reconciliation_gallery.py`

- [ ] **Step 1: Add HTML contract tests**

Assert:

- `<html lang="zh-Hant">`;
- `diagnostic_only` and `shadow_review` visible in summary;
- no copy claims `production_ready`;
- table headers have scopes;
- details are collapsed by default;
- representative cells appear in details;
- PNG fallback anchor is present when `overlay_png_path` exists;
- missing PNG renders a missing-evidence message;
- all malicious sample/family/path text is escaped;
- lightbox markers exist only as progressive enhancement.

- [ ] **Step 2: Implement HTML rendering**

Public function:

```python
def write_reconciliation_gallery_html(
    path: Path,
    index: ReconciliationIndex,
    *,
    source_links: Mapping[str, Path] = {},
) -> None:
    """Write the table-first HTML gallery from a reconciliation index."""
```

Keep the renderer table-first:

- first-screen summary;
- disagreement-first sort;
- collapsed details;
- representative cells only;
- direct PNG fallback;
- vanilla JS lightbox;
- no in-script executable TSV payloads.

- [ ] **Step 3: Wire CLI to emit HTML**

The CLI should write:

```text
backfill_evidence_reconciliation_gallery.html
```

from the same `ReconciliationIndex` used for TSV/JSON.

- [ ] **Step 4: Run focused tests and browser smoke**

Run tests:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_backfill_evidence_reconciliation_gallery.py
```

Browser smoke can use the Codex browser or headless Chrome against a synthetic
fixture HTML. Check desktop, mobile, 200 percent zoom, collapsed details,
horizontal scroll, PNG fallback, lightbox keyboard close, and no overlap.

---

## Task 5: Existing-Artifact Smoke and Review Note

**Files:**
- Create: `docs/superpowers/notes/2026-06-07-backfill-evidence-reconciliation-productization-note.md`
- Output under: `output/backfill_evidence_reconciliation_20260607/`

- [ ] **Step 1: Run Slice 0/1 on a small existing-artifact set**

Use existing artifacts first; do not regenerate RAW/overlay evidence.

Candidate 8RAW source root from prior plan:

```text
output/backfill_evidence_gate_8raw_20260605/
```

If any required source files are absent in the current checkout, stop this smoke
with a note listing the missing paths and use a synthetic fixture smoke instead.

- [ ] **Step 2: Inspect summary JSON**

Confirm:

- `group_count > 0` for real smoke, or expected synthetic fixture count;
- `matrix_contract_changed=false`;
- `product_behavior_changed=false`;
- missing evidence classes are explicit;
- product-grade and visual support are counted separately.

- [ ] **Step 3: Write review note**

The note must include:

- command used;
- input artifact paths;
- output artifact paths;
- group count;
- reconciliation class counts;
- missing evidence counts;
- readiness label;
- whether the next action is upstream evidence, gallery UX, or product-gate
  promotion.

---

## Task 6: Upstream Evidence Gap Decision

**Files:**
- Continue to source-code changes only when Task 5 review identifies a concrete
  product-grade evidence gap that has a reviewed owner addendum:
  - `xic_extractor/alignment/production_candidate_gate.py`
  - `tools/diagnostics/provisional_backfill_candidate_gate.py`
  - focused tests for the modified owner
- Otherwise update the Task 5 review note only and stop before product-gate code.

- [ ] **Step 1: Classify gaps from summary JSON**

Decision table:

| Observed state | Action |
| --- | --- |
| `product_rejects_but_product_grade_supports` exists | Candidate for allowlist promotion review. |
| `product_rejects_but_visual_supports` exists without product-grade support | Extend upstream product-grade evidence owner or leave review-only. |
| `not_assessable_missing_overlay` dominates | Generate overlay in a separate upstream workflow, not in gallery. |
| `not_assessable_missing_seed_provenance` dominates | Extend seed provenance producer before product gate. |
| stale/hash/join warnings appear | Fix source provenance or stop; do not promote. |

- [ ] **Step 2: If evidence owner work is needed, write the narrow sub-contract**

Before code changes to product-grade evidence owners, write a short addendum in
the review note naming:

- current owner;
- evidence field to add or consume;
- public surface affected;
- expected output diff;
- tests;
- validation tier.

Do not modify product behavior until this addendum exists and has subagent
review.

- [ ] **Step 3: Implement only reviewed upstream evidence work**

If and only if Step 2 produces a reviewed addendum, implement the narrow change
with focused tests. Keep gallery renderer unchanged.

---

## Task 7: Conditional Product Promotion and Validation

**Files:**
- Only after Task 6 produces a reviewed promotion sub-contract.
- Expected product files depend on that sub-contract and must be named there
  before editing.

- [ ] **Step 1: Request strategy + implementation-contract review**

Before product behavior edits, dispatch:

- `strategy-challenger` for promotion scope and overclaim risk;
- `implementation-contract-reviewer` for public TSV/matrix/workbook drift.

- [ ] **Step 2: Run 8RAW validation first**

Use documented runner shape from `docs/agent-parameter-settings.md`. Do not
launch 85RAW if 8RAW is inconclusive.

- [ ] **Step 3: Request validation-evidence acceptance review**

The reviewer must report:

- mode: acceptance/science;
- run_ok;
- gate_ok;
- production_ready for the allowlisted slice or not;
- inconclusive blockers.

- [ ] **Step 4: Run 85RAW only after 8RAW passes**

Use foreground command with timing heartbeat. No background `Start-Process`.
Product promotion requires 85RAW pass for the allowlisted slice.

- [ ] **Step 5: Apply allowlist promotion only if gates pass**

Promotion is scoped to the allowlisted slice. Blocked or unassessable groups
remain review-only / blocked / not_assessable.

---

## Task 8: Closeout and Commit Scope

**Files:**
- Update closeout note from Task 5.
- Update `tools/diagnostics/INDEX.md` if new diagnostic CLI landed.
- Commit only when user requests commit.

- [ ] **Step 1: Run final focused verification**

At minimum:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_backfill_evidence_reconciliation_gallery.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools/diagnostics/backfill_evidence_reconciliation_gallery.py xic_extractor/diagnostics/backfill_reconciliation_gallery.py tests/test_backfill_evidence_reconciliation_gallery.py
```

If product code changed, run the affected product shards and package mypy named
by the promotion sub-contract.

- [ ] **Step 2: Dirty scope audit**

Run:

```powershell
git status --short --branch
git diff --check -- docs/superpowers/specs/2026-06-07-backfill-evidence-reconciliation-gallery-design.md docs/superpowers/goals/2026-06-07-backfill-evidence-reconciliation-productization-goal.md docs/superpowers/plans/2026-06-07-backfill-evidence-reconciliation-productization-plan.md tools/diagnostics/INDEX.md tools/diagnostics/backfill_evidence_reconciliation_gallery.py xic_extractor/diagnostics/backfill_reconciliation_gallery.py tests/test_backfill_evidence_reconciliation_gallery.py
```

Expected: no whitespace errors. Unrelated pre-existing notes/specs remain
unstaged unless the user asks to include them.

- [ ] **Step 3: Final response / handoff**

Report:

- readiness label;
- changed files;
- output artifacts;
- verification commands and results;
- subagent review verdicts;
- remaining risks;
- whether product promotion happened, and if so exactly which allowlisted slice
  is `production_ready`.
