# PeakHypothesis Backfill Promotion Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote a narrow PeakHypothesis-level backfill slice that prioritizes recovering true signal while keeping nonstandard peak-shape rows review-only until a separate integration policy exists.

**Architecture:** Keep gallery/reconciliation as review surfaces and keep product mutation behind allowlisted, machine-readable evidence. MS1 same-peak own-max evidence is strong identity evidence, not a single authority; promotion requires an evidence chain containing PeakHypothesis identity, seed provenance, RT/window compatibility, detected anchors, product-authorized MS1 same-peak support, no wrong-peak blockers, and positive area. Nonstandard-but-assessable peak shapes can support identity review, but this slice blocks them from matrix-write promotion because the integration policy is not settled.

**Tech Stack:** Python dataclasses, TSV/JSON diagnostic writers, existing `shadow_production_projection`, existing `backfill_*_product_authority` sidecars, pytest, ruff, 8RAW/85RAW validation commands from `docs/agent-parameter-settings.md`.

---

## User Decisions Captured

- Backfill productization must solve both true-signal misses and risky rescue/duplicate/zero-present control; true-signal recovery is higher priority.
- MS1 same-peak own-max evidence is accepted as strong evidence in the backfill evidence chain, but not as a standalone authority.
- Promotion unit is PeakHypothesis / sample-cell, not entire legacy family.
- Promotion outputs must carry `peak_hypothesis_id` and `activation_unit_scope=peak_hypothesis`. If those fields cannot be joined from current artifacts, the result is a review queue, not an activation input.
- Conflict / review rows must be reviewed rather than automatically rejected as nonstandard peak shapes.
- Nonstandard-but-assessable peaks may support review/evidence-chain decisions, but must not write matrix values in this slice; integration remains a separate unresolved policy.
- Validation order is 8RAW allowlisted activation first, then focused tests and 85RAW production-equivalent validation.

## Product Contract Addendum

### Evidence Chain

A backfilled cell can become a product-candidate write only when all are true:

- `shadow_decision=accept` in `shadow_production_projection_cells.tsv`;
- `current_production_status=review_rescue`;
- `current_raw_status=rescued`;
- `peak_hypothesis_id` is non-empty;
- `activation_unit_scope=peak_hypothesis`;
- `projected_matrix_written=TRUE`;
- `projected_matrix_value` is finite and positive;
- `product_authority_chain` includes product-authorized MS1 same-peak support at `trace_constellation`;
- `shadow_reasons` includes `product_authorized_same_peak_backfill`;
- `hard_blockers`, `missing_evidence`, and wrong-peak / hypothesis blockers are empty;
- a reviewed allowlist row authorizes the exact `(peak_hypothesis_id, feature_family_id, seed_group_id, sample_stem)` key;
- the allowlist row records the expected shadow projection file SHA256 and expected source row SHA256;
- the allowlist row records the exact expected product authority chain;
- the allowlist row names one area policy: `standard_assessable_area`, `nonstandard_assessable_area`, or `unassessable_area`.

Candidate MS2/NL evidence strengthens the chain when present. Missing Candidate MS2/NL does not become negative evidence for these backfilled cells when MS1 same-peak own-max evidence is product-authorized and no explicit contradiction exists.

### Area Policy

Area policy is separate from identity policy.

| `area_policy` | Matrix write | Sidecar uncertainty | Meaning |
| --- | --- | --- | --- |
| `standard_assessable_area` | yes | `area_uncertainty_state=standard_assessable` | Peak shape and bounds are normal enough for the existing area value. |
| `nonstandard_assessable_area` | no | `area_uncertainty_state=nonstandard_assessable` | Identity/backfill may be supported, but tailing/shoulder/coelution/asymmetry makes area integration unresolved. |
| `unassessable_area` | no | `area_uncertainty_state=unassessable` | Same-peak identity is not enough to trust area integration. |

The first product-candidate slice must not change the public `alignment_matrix.tsv` schema. It should emit a sidecar such as `backfill_peakhypothesis_area_uncertainty.tsv` keyed by matrix row identity and sample. Downstream users that ignore the sidecar still see the usual matrix shape.

For `nonstandard_assessable_area`, the review row must expose why the area is nonstandard and must remain blocked from matrix-write promotion. If numeric uncertainty is available from an integration audit, record `area_uncertainty_fraction`; if it is not available, record `area_uncertainty_fraction_status=not_available`. A future downstream handoff can decide whether `use_with_uncertainty` is acceptable, but that is not part of this slice.

### Readiness

- Synthetic tests only: `diagnostic_only`.
- Existing-artifact projection plus reviewed allowlist: `shadow_ready`.
- 8RAW activation with matrix diff and no targeted benchmark regression: `production_candidate`.
- 85RAW production-equivalent validation plus reviewed acceptance: `production_ready` for this allowlisted slice only.

## File Structure

Create:

- `xic_extractor/diagnostics/backfill_peakhypothesis_promotion.py`
  - Reads shadow projection rows and reviewed allowlist rows.
  - Builds deterministic product-candidate projection rows.
  - Emits area uncertainty sidecar rows.
  - Does not read RAW, generate overlays, mutate alignment artifacts, or write final matrices.
- `tools/diagnostics/backfill_peakhypothesis_promotion.py`
  - Thin CLI around the package module.
- `tests/test_backfill_peakhypothesis_promotion.py`
  - Synthetic no-RAW tests for allowlist keys, area policy, fail-closed behavior, and output schema.

Modify:

- `xic_extractor/diagnostics/shadow_production_projection.py`
  - Add `peak_hypothesis_id` and `activation_unit_scope` to the shadow projection schema when the source alignment cells provide `group_hypothesis_id` or a formal `peak_hypothesis_id` sidecar is joined. If the identity cannot be determined, emit blanks and keep promotion blocked.
- `tools/diagnostics/INDEX.md`
  - Add the diagnostic entry and status note.
- `docs/superpowers/specs/2026-06-07-backfill-evidence-reconciliation-gallery-design.md`
  - Add a short product-promotion addendum pointing to this plan.
- `docs/superpowers/notes/2026-06-07-backfill-evidence-reconciliation-productization-note.md`
  - Add closeout results after the projection smoke and validation.

Conditional only after projection passes review:

- `tools/diagnostics/apply_shared_peak_identity_activation.py`
  - Consume the reviewed promotion projection as an activation input if the existing activation bridge is the right public entry point.
- Focused activation tests that prove matrix rows and area uncertainty sidecar remain consistent.

## Schemas

### Reviewed Allowlist

File name used by tests: `backfill_peakhypothesis_promotion_allowlist.tsv`.

Columns:

```text
schema_version
peak_hypothesis_id
activation_unit_scope
feature_family_id
seed_group_id
sample_stem
authority_status
authority_source
authority_reason
expected_shadow_projection_sha256
expected_shadow_projection_row_sha256
expected_product_authority_chain
area_policy
area_uncertainty_reason
area_uncertainty_fraction
area_uncertainty_fraction_status
integration_bounds_source
peak_start_rt
peak_end_rt
matrix_quantitative_use
reviewer
reviewed_at
```

Allowed values:

- `schema_version=backfill_peakhypothesis_promotion_allowlist_v1`
- `activation_unit_scope=peak_hypothesis`
- `authority_status=product_authorized`
- `area_policy` is one of `standard_assessable_area`, `nonstandard_assessable_area`, `unassessable_area`
- `matrix_quantitative_use` is one of `standard_quantitative_use`, `use_with_uncertainty`, `review_only`

### Promotion Cells

File name: `backfill_peakhypothesis_promotion_cells.tsv`.

Columns:

```text
schema_version
peak_hypothesis_id
activation_unit_scope
feature_family_id
seed_group_id
sample_stem
promotion_decision
promotion_reasons
promotion_blockers
current_production_status
current_raw_status
current_matrix_written
shadow_reasons
projected_matrix_written
projected_matrix_value
area_policy
area_uncertainty_state
area_uncertainty_reason
area_uncertainty_fraction
area_uncertainty_fraction_status
matrix_quantitative_use
product_authority_chain
authority_source
shadow_projection_sha256
shadow_projection_row_sha256
```

Decision values:

- `promote_matrix_write`
- `review_only`
- `blocked`

### Area Uncertainty

File name: `backfill_peakhypothesis_area_uncertainty.tsv`.

Columns:

```text
schema_version
peak_hypothesis_id
activation_unit_scope
feature_family_id
seed_group_id
sample_stem
projected_matrix_value
area_uncertainty_state
area_uncertainty_reason
area_uncertainty_fraction
area_uncertainty_fraction_status
area_policy
integration_bounds_source
peak_start_rt
peak_end_rt
matrix_quantitative_use
product_authority_chain
shadow_projection_sha256
shadow_projection_row_sha256
```

The sidecar writes rows for every `promote_matrix_write` decision. `standard_assessable_area` rows are included so consumers do not have to infer missing sidecar rows as standard.

---

## Task 1: Contract Doc Addendum

**Files:**
- Modify: `docs/superpowers/specs/2026-06-07-backfill-evidence-reconciliation-gallery-design.md`
- Modify: `tools/diagnostics/INDEX.md`

- [ ] **Step 1: Add product-promotion addendum to the spec**

Insert after the existing `### Promotion Policy` section:

```markdown
### PeakHypothesis Backfill Promotion Addendum, 2026-06-08

Promotion is PeakHypothesis / sample-cell scoped and must carry
`peak_hypothesis_id` plus `activation_unit_scope=peak_hypothesis`. MS1
same-peak own-max evidence is strong identity evidence inside the backfill
evidence chain, but it is not a standalone authority. A product-candidate write
requires reviewed allowlist authorization, seed provenance, RT/window
compatibility, detected anchors, product-authorized MS1 same-peak support,
positive projected area, source-row hash agreement, and no wrong-peak or
hypothesis blocker.

Nonstandard but assessable peak shapes may support gallery/evidence-chain
review, but must not become promoted matrix-write candidates in this slice.
Those rows remain blocked with `area_uncertainty_state=nonstandard_assessable`
until a separate integration policy is approved. Identity support and area
confidence are separate decisions. The public `alignment_matrix.tsv` shape
remains unchanged; uncertainty is carried by the review row keyed by
PeakHypothesis / feature family / seed group / sample. If `peak_hypothesis_id`
cannot be resolved, the output remains a review queue and must not be consumed
by activation.
```

- [ ] **Step 2: Add diagnostic index entry**

Append a Backfill Reviews entry to `tools/diagnostics/INDEX.md`:

```markdown
### `backfill_peakhypothesis_promotion.py`

**Purpose**: Convert reviewed PeakHypothesis/sample-cell backfill projection rows
into an allowlisted product-candidate promotion sidecar while keeping
nonstandard but assessable peaks review-only.
**Topic group**: `backfill_peakhypothesis_promotion.py` +
`xic_extractor/diagnostics/backfill_peakhypothesis_promotion.py`
**Originating spec/goal/plan**:
`plans/2026-06-08-peakhypothesis-backfill-promotion-policy.md`
**Status note**: Writes `backfill_peakhypothesis_promotion_cells.tsv`,
`backfill_peakhypothesis_area_uncertainty.tsv`, and
`backfill_peakhypothesis_promotion_summary.json`. It consumes
`shadow_production_projection_cells.tsv` and a reviewed allowlist only. It does
not read RAW, generate overlays, mutate alignment artifacts, change workbook
schemas, or write final matrices. `nonstandard_assessable_area` rows record the
area caveat but stay blocked until a separate integration policy exists.
8RAW activation and 85RAW validation are still required before production-ready
claims.
```

- [ ] **Step 3: Verify docs diff is scoped**

Run:

```powershell
git diff -- docs/superpowers/specs/2026-06-07-backfill-evidence-reconciliation-gallery-design.md tools/diagnostics/INDEX.md
```

Expected: only the addendum and index entry above.

## Task 2: RED Tests for Promotion Projection

**Files:**
- Create: `tests/test_backfill_peakhypothesis_promotion.py`
- Future implementation target: `xic_extractor/diagnostics/backfill_peakhypothesis_promotion.py`

- [ ] **Step 1: Add tests for allowlisted standard promotion and nonstandard review-only blocking**

Create `tests/test_backfill_peakhypothesis_promotion.py` with:

```python
from __future__ import annotations

import csv
import json
from pathlib import Path

from xic_extractor.diagnostics import backfill_peakhypothesis_promotion as promotion


def test_standard_promotes_and_nonstandard_stays_review_only(tmp_path: Path) -> None:
    shadow_rows = [
        _shadow_row(
            family="FAM001",
            seed="seed::FAM001::mz=100::rt=5",
            sample="S1",
            value="123.4",
            chain="MS1:product_authorized:supportive:trace_constellation:feature_family_sample:product_authority_allowlist_and_anchor_own_max_supported | same_peak_reason:family_ms1_overlay_anchor_peak_own_max_shape_supported",
        ),
        _shadow_row(
            family="FAM001",
            seed="seed::FAM001::mz=100::rt=5",
            sample="S2",
            value="234.5",
            chain="MS1:product_authorized:supportive:trace_constellation:feature_family_sample:product_authority_allowlist_and_anchor_own_max_supported | same_peak_reason:family_ms1_overlay_anchor_peak_own_max_shape_supported",
        ),
    ]
    allowlist_rows = [
        _allowlist_row(
            family="FAM001",
            seed="seed::FAM001::mz=100::rt=5",
            sample="S1",
            area_policy="standard_assessable_area",
            reason="clean same-peak backfill",
            expected_chain=shadow_rows[0]["product_authority_chain"],
        ),
        _allowlist_row(
            family="FAM001",
            seed="seed::FAM001::mz=100::rt=5",
            sample="S2",
            area_policy="nonstandard_assessable_area",
            reason="tailing peak; identity supported by same-peak own-max MS1 pattern",
            expected_chain=shadow_rows[1]["product_authority_chain"],
        ),
    ]

    result = promotion.build_promotion_index(
        shadow_projection_rows=shadow_rows,
        allowlist_rows=allowlist_rows,
        shadow_projection_sha256="shadow-sha",
        source_run_id="unit",
    )

    by_sample = {row.sample_stem: row for row in result.rows}
    assert by_sample["S1"].promotion_decision == "promote_matrix_write"
    assert by_sample["S1"].area_uncertainty_state == "standard_assessable"
    assert by_sample["S2"].promotion_decision == "blocked"
    assert by_sample["S2"].promotion_blockers == ("nonstandard_area_review_only",)
    assert by_sample["S2"].area_uncertainty_state == "nonstandard_assessable"
    assert (
        by_sample["S2"].area_uncertainty_reason
        == "tailing peak; identity supported by same-peak own-max MS1 pattern"
    )
    assert result.summary["decision_counts"] == {
        "blocked": 1,
        "promote_matrix_write": 1,
    }


def test_unassessable_area_blocks_matrix_write(tmp_path: Path) -> None:
    shadow = _shadow_row(
        family="FAM002",
        seed="seed::FAM002::mz=200::rt=8",
        sample="S1",
        value="345.6",
    )
    allowlist = _allowlist_row(
        family="FAM002",
        seed="seed::FAM002::mz=200::rt=8",
        sample="S1",
        area_policy="unassessable_area",
        reason="same-peak identity visible, but boundary cannot support area",
        expected_chain=shadow["product_authority_chain"],
    )

    result = promotion.build_promotion_index(
        shadow_projection_rows=[shadow],
        allowlist_rows=[allowlist],
        shadow_projection_sha256="shadow-sha",
        source_run_id="unit",
    )

    assert result.rows[0].promotion_decision == "blocked"
    assert result.rows[0].promotion_blockers == ("area_unassessable",)
    assert result.rows[0].area_uncertainty_state == "unassessable"


def test_shadow_or_chain_drift_fails_closed() -> None:
    shadow = _shadow_row(
        family="FAM003",
        seed="seed::FAM003::mz=300::rt=9",
        sample="S1",
        value="456.7",
        chain="MS1:product_authorized:supportive:trace_constellation:feature_family_sample:current_review | same_peak_reason:family_ms1_overlay_anchor_peak_own_max_shape_supported",
    )
    allowlist = _allowlist_row(
        family="FAM003",
        seed="seed::FAM003::mz=300::rt=9",
        sample="S1",
        expected_chain="MS1:product_authorized:supportive:trace_constellation:feature_family_sample:old",
    )

    result = promotion.build_promotion_index(
        shadow_projection_rows=[shadow],
        allowlist_rows=[allowlist],
        shadow_projection_sha256="shadow-sha",
        source_run_id="unit",
    )

    assert result.rows[0].promotion_decision == "blocked"
    assert result.rows[0].promotion_blockers == ("product_authority_chain_drift",)


def test_writes_cells_uncertainty_and_summary(tmp_path: Path) -> None:
    shadow = _shadow_row(
        family="FAM004",
        seed="seed::FAM004::mz=400::rt=10",
        sample="S1",
        value="567.8",
    )
    allowlist = _allowlist_row(
        family="FAM004",
        seed="seed::FAM004::mz=400::rt=10",
        sample="S1",
        area_policy="standard_assessable_area",
        reason="standard peak and same-peak MS1 pattern is coherent",
        expected_chain=shadow["product_authority_chain"],
    )
    index = promotion.build_promotion_index(
        shadow_projection_rows=[shadow],
        allowlist_rows=[allowlist],
        shadow_projection_sha256="shadow-sha",
        source_run_id="unit",
    )

    outputs = promotion.write_promotion_outputs(tmp_path, index)

    cells = _read_tsv(outputs.cells_tsv)
    uncertainty = _read_tsv(outputs.area_uncertainty_tsv)
    summary = json.loads(outputs.summary_json.read_text(encoding="utf-8"))
    assert cells[0]["promotion_decision"] == "promote_matrix_write"
    assert uncertainty[0]["area_uncertainty_state"] == "standard_assessable"
    assert summary["schema_version"] == "backfill_peakhypothesis_promotion_v1"
    assert summary["readiness_label"] == "diagnostic_only"


def test_incomplete_evidence_chain_fails_closed() -> None:
    missing_reason = {
        **_shadow_row(
            family="FAM005",
            seed="seed::FAM005::mz=500::rt=11",
            sample="S1",
            value="678.9",
        ),
        "shadow_reasons": "",
    }
    not_rescued = {
        **_shadow_row(
            family="FAM005",
            seed="seed::FAM005::mz=500::rt=11",
            sample="S2",
            value="679.1",
        ),
        "current_raw_status": "detected",
    }
    malformed_chain = {
        **_shadow_row(
            family="FAM005",
            seed="seed::FAM005::mz=500::rt=11",
            sample="S3",
            value="679.2",
        ),
        "product_authority_chain": "MS1:product_authorized:supportive:sample_constellation",
    }
    allowlist_rows = [
        _allowlist_row(
            family=row["feature_family_id"],
            seed=row["seed_group_id"],
            sample=row["sample_stem"],
            peak_id=row["peak_hypothesis_id"],
            expected_chain=row["product_authority_chain"],
            expected_row_sha=row["shadow_projection_row_sha256"],
        )
        for row in (missing_reason, not_rescued, malformed_chain)
    ]

    result = promotion.build_promotion_index(
        shadow_projection_rows=[missing_reason, not_rescued, malformed_chain],
        allowlist_rows=allowlist_rows,
        shadow_projection_sha256="shadow-sha",
        source_run_id="unit",
    )

    by_sample = {row.sample_stem: row for row in result.rows}
    assert by_sample["S1"].promotion_blockers == (
        "missing_product_authorized_same_peak_reason",
    )
    assert by_sample["S2"].promotion_blockers == ("current_raw_status_not_rescued",)
    assert by_sample["S3"].promotion_blockers == (
        "malformed_product_authority_chain",
    )


def _shadow_row(
    *,
    family: str,
    seed: str,
    sample: str,
    value: str,
    peak_id: str = "",
    chain: str = "MS1:product_authorized:supportive:trace_constellation:feature_family_sample:product_authority_allowlist_and_anchor_own_max_supported | same_peak_reason:family_ms1_overlay_anchor_peak_own_max_shape_supported",
) -> dict[str, str]:
    hypothesis_id = peak_id or f"{family}::mode_1"
    return {
        "schema_version": "shadow_production_projection_v1",
        "peak_hypothesis_id": hypothesis_id,
        "activation_unit_scope": "peak_hypothesis",
        "feature_family_id": family,
        "seed_group_id": seed,
        "sample_stem": sample,
        "current_production_status": "review_rescue",
        "current_raw_status": "rescued",
        "current_matrix_written": "FALSE",
        "review_rescued_cell": "TRUE",
        "shadow_decision": "accept",
        "shadow_reasons": "product_authorized_same_peak_backfill",
        "shadow_warnings": "",
        "projected_matrix_written": "TRUE",
        "projected_matrix_value": value,
        "projection_authority": "shadow_projection_only",
        "product_authority_chain": chain,
        "shadow_projection_row_sha256": f"sha-{family}-{sample}",
        "hard_blockers": "",
        "missing_evidence": "",
    }


def _allowlist_row(
    *,
    family: str,
    seed: str,
    sample: str,
    expected_chain: str,
    peak_id: str = "",
    area_policy: str = "standard_assessable_area",
    reason: str = "reviewed same-peak backfill",
    expected_row_sha: str = "",
) -> dict[str, str]:
    hypothesis_id = peak_id or f"{family}::mode_1"
    return {
        "schema_version": "backfill_peakhypothesis_promotion_allowlist_v1",
        "peak_hypothesis_id": hypothesis_id,
        "activation_unit_scope": "peak_hypothesis",
        "feature_family_id": family,
        "seed_group_id": seed,
        "sample_stem": sample,
        "authority_status": "product_authorized",
        "authority_source": "unit_test_review",
        "authority_reason": "same_peak_identity_and_area_policy_reviewed",
        "expected_shadow_projection_sha256": "shadow-sha",
        "expected_shadow_projection_row_sha256": expected_row_sha
        or f"sha-{family}-{sample}",
        "expected_product_authority_chain": expected_chain,
        "area_policy": area_policy,
        "area_uncertainty_reason": reason,
        "area_uncertainty_fraction": "",
        "area_uncertainty_fraction_status": "not_available",
        "integration_bounds_source": "shadow_projection_selected_peak",
        "peak_start_rt": "4.8",
        "peak_end_rt": "5.2",
        "matrix_quantitative_use": (
            "use_with_uncertainty"
            if area_policy == "nonstandard_assessable_area"
            else "standard_quantitative_use"
        ),
        "reviewer": "unit",
        "reviewed_at": "2026-06-08",
    }


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))
```

- [ ] **Step 2: Run the RED test**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_backfill_peakhypothesis_promotion.py
```

Expected: FAIL with `ImportError` because `xic_extractor.diagnostics.backfill_peakhypothesis_promotion` does not exist.

## Task 3: Implement Promotion Projection Module

**Files:**
- Create: `xic_extractor/diagnostics/backfill_peakhypothesis_promotion.py`
- Test: `tests/test_backfill_peakhypothesis_promotion.py`

- [ ] **Step 1: Create models, constants, and validators**

Create `xic_extractor/diagnostics/backfill_peakhypothesis_promotion.py` with:

```python
from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from xic_extractor.diagnostics.diagnostic_io import (
    format_diagnostic_value,
    text_value,
    write_tsv,
)

SCHEMA_VERSION = "backfill_peakhypothesis_promotion_v1"
ALLOWLIST_SCHEMA_VERSION = "backfill_peakhypothesis_promotion_allowlist_v1"

PromotionDecision = Literal["promote_matrix_write", "review_only", "blocked"]

AREA_POLICY_TO_STATE = {
    "standard_assessable_area": "standard_assessable",
    "nonstandard_assessable_area": "nonstandard_assessable",
    "unassessable_area": "unassessable",
}

PROMOTION_COLUMNS = (
    "schema_version",
    "peak_hypothesis_id",
    "activation_unit_scope",
    "feature_family_id",
    "seed_group_id",
    "sample_stem",
    "promotion_decision",
    "promotion_reasons",
    "promotion_blockers",
    "current_production_status",
    "current_raw_status",
    "current_matrix_written",
    "shadow_reasons",
    "projected_matrix_written",
    "projected_matrix_value",
    "area_policy",
    "area_uncertainty_state",
    "area_uncertainty_reason",
    "area_uncertainty_fraction",
    "area_uncertainty_fraction_status",
    "matrix_quantitative_use",
    "product_authority_chain",
    "authority_source",
    "shadow_projection_sha256",
    "shadow_projection_row_sha256",
)

AREA_UNCERTAINTY_COLUMNS = (
    "schema_version",
    "peak_hypothesis_id",
    "activation_unit_scope",
    "feature_family_id",
    "seed_group_id",
    "sample_stem",
    "projected_matrix_value",
    "area_uncertainty_state",
    "area_uncertainty_reason",
    "area_uncertainty_fraction",
    "area_uncertainty_fraction_status",
    "area_policy",
    "integration_bounds_source",
    "peak_start_rt",
    "peak_end_rt",
    "matrix_quantitative_use",
    "product_authority_chain",
    "shadow_projection_sha256",
    "shadow_projection_row_sha256",
)

SHADOW_REQUIRED_COLUMNS = (
    "peak_hypothesis_id",
    "activation_unit_scope",
    "feature_family_id",
    "seed_group_id",
    "sample_stem",
    "current_raw_status",
    "current_production_status",
    "current_matrix_written",
    "shadow_decision",
    "shadow_reasons",
    "projected_matrix_written",
    "projected_matrix_value",
    "product_authority_chain",
    "hard_blockers",
    "missing_evidence",
    "shadow_projection_row_sha256",
)

ALLOWLIST_REQUIRED_COLUMNS = (
    "schema_version",
    "peak_hypothesis_id",
    "activation_unit_scope",
    "feature_family_id",
    "seed_group_id",
    "sample_stem",
    "authority_status",
    "authority_source",
    "expected_shadow_projection_sha256",
    "expected_shadow_projection_row_sha256",
    "expected_product_authority_chain",
    "area_policy",
    "area_uncertainty_reason",
    "area_uncertainty_fraction_status",
    "matrix_quantitative_use",
)


@dataclass(frozen=True)
class PromotionRow:
    peak_hypothesis_id: str
    activation_unit_scope: str
    feature_family_id: str
    seed_group_id: str
    sample_stem: str
    promotion_decision: PromotionDecision
    promotion_reasons: tuple[str, ...]
    promotion_blockers: tuple[str, ...]
    current_production_status: str
    current_raw_status: str
    current_matrix_written: str
    shadow_reasons: str
    projected_matrix_written: str
    projected_matrix_value: str
    area_policy: str
    area_uncertainty_state: str
    area_uncertainty_reason: str
    area_uncertainty_fraction: str
    area_uncertainty_fraction_status: str
    integration_bounds_source: str
    peak_start_rt: str
    peak_end_rt: str
    matrix_quantitative_use: str
    product_authority_chain: str
    authority_source: str
    shadow_projection_sha256: str
    shadow_projection_row_sha256: str


@dataclass(frozen=True)
class PromotionIndex:
    rows: tuple[PromotionRow, ...]
    summary: dict[str, object]


@dataclass(frozen=True)
class PromotionOutputs:
    cells_tsv: Path
    area_uncertainty_tsv: Path
    summary_json: Path
```

- [ ] **Step 2: Implement index builder**

Add:

```python
def build_promotion_index(
    *,
    shadow_projection_rows: Iterable[Mapping[str, str]],
    allowlist_rows: Iterable[Mapping[str, str]],
    shadow_projection_sha256: str,
    source_run_id: str = "",
    readiness_label: str = "diagnostic_only",
) -> PromotionIndex:
    if readiness_label not in {"diagnostic_only", "shadow_ready"}:
        raise ValueError(f"unsupported readiness label: {readiness_label}")
    shadow_by_key = _shadow_by_key(shadow_projection_rows)
    allowlist_by_key = _allowlist_by_key(allowlist_rows)
    rows = tuple(
        sorted(
            (
                _promotion_row(
                    shadow_by_key.get(key),
                    allowlist_row=allowlist_row,
                    shadow_projection_sha256=shadow_projection_sha256,
                )
                for key, allowlist_row in allowlist_by_key.items()
            ),
            key=lambda row: (
                row.promotion_decision != "blocked",
                row.feature_family_id,
                row.seed_group_id,
                row.sample_stem,
            ),
        )
    )
    return PromotionIndex(
        rows=rows,
        summary=_summary(
            rows,
            allowlist_row_count=len(allowlist_by_key),
            source_run_id=source_run_id,
            shadow_projection_sha256=shadow_projection_sha256,
            readiness_label=readiness_label,
        ),
    )


def _promotion_row(
    shadow_row: Mapping[str, str] | None,
    *,
    allowlist_row: Mapping[str, str],
    shadow_projection_sha256: str,
) -> PromotionRow:
    peak_id, family, seed, sample = _key(allowlist_row)
    area_policy = text_value(allowlist_row.get("area_policy"))
    uncertainty_state = AREA_POLICY_TO_STATE.get(area_policy, "")
    matrix_quantitative_use = text_value(allowlist_row.get("matrix_quantitative_use"))
    shadow_reasons = text_value(shadow_row.get("shadow_reasons")) if shadow_row else ""
    shadow_chain = text_value(shadow_row.get("product_authority_chain")) if shadow_row else ""
    expected_chain = text_value(allowlist_row.get("expected_product_authority_chain"))
    shadow_row_sha = text_value(shadow_row.get("shadow_projection_row_sha256")) if shadow_row else ""
    blockers: list[str] = []
    reasons: list[str] = []
    if shadow_row is None:
        blockers.append("missing_shadow_projection_row")
        shadow_row = {}
    if text_value(allowlist_row.get("schema_version")) != ALLOWLIST_SCHEMA_VERSION:
        blockers.append("allowlist_schema_version_mismatch")
    if text_value(allowlist_row.get("authority_status")) != "product_authorized":
        blockers.append("allowlist_not_product_authorized")
    if text_value(allowlist_row.get("activation_unit_scope")) != "peak_hypothesis":
        blockers.append("allowlist_activation_scope_not_peakhypothesis")
    if text_value(allowlist_row.get("expected_shadow_projection_sha256")) != shadow_projection_sha256:
        blockers.append("shadow_projection_sha256_mismatch")
    if text_value(allowlist_row.get("expected_shadow_projection_row_sha256")) != shadow_row_sha:
        blockers.append("shadow_projection_row_sha256_mismatch")
    if not uncertainty_state:
        blockers.append("unsupported_area_policy")
    if text_value(shadow_row.get("peak_hypothesis_id")) != peak_id:
        blockers.append("peak_hypothesis_id_drift")
    if text_value(shadow_row.get("activation_unit_scope")) != "peak_hypothesis":
        blockers.append("shadow_activation_scope_not_peakhypothesis")
    if text_value(shadow_row.get("shadow_decision")) != "accept":
        blockers.append("shadow_decision_not_accept")
    if text_value(shadow_row.get("current_raw_status")) != "rescued":
        blockers.append("current_raw_status_not_rescued")
    if text_value(shadow_row.get("current_production_status")) != "review_rescue":
        blockers.append("current_status_not_review_rescue")
    if text_value(shadow_row.get("current_matrix_written")) != "FALSE":
        blockers.append("current_matrix_already_written")
    if text_value(shadow_row.get("projected_matrix_written")).upper() != "TRUE":
        blockers.append("projected_matrix_not_written")
    if _positive_number(shadow_row.get("projected_matrix_value")) is None:
        blockers.append("projected_matrix_value_not_positive")
    if text_value(shadow_row.get("hard_blockers")):
        blockers.append("hard_blockers_present")
    if text_value(shadow_row.get("missing_evidence")):
        blockers.append("missing_evidence_present")
    if "product_authorized_same_peak_backfill" not in shadow_reasons:
        blockers.append("missing_product_authorized_same_peak_reason")
    if expected_chain != shadow_chain:
        blockers.append("product_authority_chain_drift")
    if not _valid_same_peak_ms1_chain(shadow_chain):
        blockers.append("malformed_product_authority_chain")
    if area_policy == "unassessable_area":
        blockers.append("area_unassessable")
    if area_policy == "standard_assessable_area" and matrix_quantitative_use != "standard_quantitative_use":
        blockers.append("standard_area_quantitative_use_mismatch")
    if area_policy == "nonstandard_assessable_area":
        if matrix_quantitative_use != "use_with_uncertainty":
            blockers.append("nonstandard_area_uncertainty_not_marked")
        if not (
            text_value(allowlist_row.get("area_uncertainty_fraction"))
            or text_value(allowlist_row.get("area_uncertainty_fraction_status"))
        ):
            blockers.append("missing_area_uncertainty_fraction_status")
        blockers.append("nonstandard_area_review_only")

    if not blockers:
        decision: PromotionDecision = "promote_matrix_write"
        reasons.append("allowlisted_peakhypothesis_same_peak_backfill")
    else:
        decision = "blocked"

    return PromotionRow(
        peak_hypothesis_id=peak_id,
        activation_unit_scope=text_value(allowlist_row.get("activation_unit_scope")),
        feature_family_id=family,
        seed_group_id=seed,
        sample_stem=sample,
        promotion_decision=decision,
        promotion_reasons=tuple(reasons),
        promotion_blockers=tuple(dict.fromkeys(blockers)),
        current_production_status=text_value(shadow_row.get("current_production_status")),
        current_raw_status=text_value(shadow_row.get("current_raw_status")),
        current_matrix_written=text_value(shadow_row.get("current_matrix_written")),
        shadow_reasons=shadow_reasons,
        projected_matrix_written=text_value(shadow_row.get("projected_matrix_written")),
        projected_matrix_value=text_value(shadow_row.get("projected_matrix_value")),
        area_policy=area_policy,
        area_uncertainty_state=uncertainty_state,
        area_uncertainty_reason=text_value(allowlist_row.get("area_uncertainty_reason")),
        area_uncertainty_fraction=text_value(allowlist_row.get("area_uncertainty_fraction")),
        area_uncertainty_fraction_status=text_value(
            allowlist_row.get("area_uncertainty_fraction_status")
        ),
        integration_bounds_source=text_value(allowlist_row.get("integration_bounds_source")),
        peak_start_rt=text_value(allowlist_row.get("peak_start_rt")),
        peak_end_rt=text_value(allowlist_row.get("peak_end_rt")),
        matrix_quantitative_use=matrix_quantitative_use,
        product_authority_chain=shadow_chain,
        authority_source=text_value(allowlist_row.get("authority_source")),
        shadow_projection_sha256=shadow_projection_sha256,
        shadow_projection_row_sha256=shadow_row_sha,
    )
```

- [ ] **Step 3: Implement writers and helpers**

Add:

```python
def write_promotion_outputs(output_dir: Path, index: PromotionIndex) -> PromotionOutputs:
    output_dir.mkdir(parents=True, exist_ok=True)
    cells_tsv = output_dir / "backfill_peakhypothesis_promotion_cells.tsv"
    uncertainty_tsv = output_dir / "backfill_peakhypothesis_area_uncertainty.tsv"
    summary_json = output_dir / "backfill_peakhypothesis_promotion_summary.json"
    cell_rows = [_promotion_tsv_row(row) for row in index.rows]
    uncertainty_rows = [
        _area_uncertainty_tsv_row(row)
        for row in index.rows
        if row.promotion_decision == "promote_matrix_write"
    ]
    write_tsv(
        cells_tsv,
        cell_rows,
        PROMOTION_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    write_tsv(
        uncertainty_tsv,
        uncertainty_rows,
        AREA_UNCERTAINTY_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    summary_json.write_text(
        json.dumps(index.summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return PromotionOutputs(
        cells_tsv=cells_tsv,
        area_uncertainty_tsv=uncertainty_tsv,
        summary_json=summary_json,
    )


def _promotion_tsv_row(row: PromotionRow) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "peak_hypothesis_id": row.peak_hypothesis_id,
        "activation_unit_scope": row.activation_unit_scope,
        "feature_family_id": row.feature_family_id,
        "seed_group_id": row.seed_group_id,
        "sample_stem": row.sample_stem,
        "promotion_decision": row.promotion_decision,
        "promotion_reasons": ";".join(row.promotion_reasons),
        "promotion_blockers": ";".join(row.promotion_blockers),
        "current_production_status": row.current_production_status,
        "current_raw_status": row.current_raw_status,
        "current_matrix_written": row.current_matrix_written,
        "shadow_reasons": row.shadow_reasons,
        "projected_matrix_written": row.projected_matrix_written,
        "projected_matrix_value": row.projected_matrix_value,
        "area_policy": row.area_policy,
        "area_uncertainty_state": row.area_uncertainty_state,
        "area_uncertainty_reason": row.area_uncertainty_reason,
        "area_uncertainty_fraction": row.area_uncertainty_fraction,
        "area_uncertainty_fraction_status": row.area_uncertainty_fraction_status,
        "matrix_quantitative_use": row.matrix_quantitative_use,
        "product_authority_chain": row.product_authority_chain,
        "authority_source": row.authority_source,
        "shadow_projection_sha256": row.shadow_projection_sha256,
        "shadow_projection_row_sha256": row.shadow_projection_row_sha256,
    }


def _area_uncertainty_tsv_row(row: PromotionRow) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "peak_hypothesis_id": row.peak_hypothesis_id,
        "activation_unit_scope": row.activation_unit_scope,
        "feature_family_id": row.feature_family_id,
        "seed_group_id": row.seed_group_id,
        "sample_stem": row.sample_stem,
        "projected_matrix_value": row.projected_matrix_value,
        "area_uncertainty_state": row.area_uncertainty_state,
        "area_uncertainty_reason": row.area_uncertainty_reason,
        "area_uncertainty_fraction": row.area_uncertainty_fraction,
        "area_uncertainty_fraction_status": row.area_uncertainty_fraction_status,
        "area_policy": row.area_policy,
        "integration_bounds_source": row.integration_bounds_source,
        "peak_start_rt": row.peak_start_rt,
        "peak_end_rt": row.peak_end_rt,
        "matrix_quantitative_use": row.matrix_quantitative_use,
        "product_authority_chain": row.product_authority_chain,
        "shadow_projection_sha256": row.shadow_projection_sha256,
        "shadow_projection_row_sha256": row.shadow_projection_row_sha256,
    }


def _summary(
    rows: tuple[PromotionRow, ...],
    *,
    allowlist_row_count: int,
    source_run_id: str,
    shadow_projection_sha256: str,
    readiness_label: str,
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "readiness_label": readiness_label,
        "source_run_id": source_run_id,
        "shadow_projection_sha256": shadow_projection_sha256,
        "allowlist_row_count": allowlist_row_count,
        "row_count": len(rows),
        "decision_counts": dict(Counter(row.promotion_decision for row in rows)),
        "area_uncertainty_counts": dict(
            Counter(row.area_uncertainty_state for row in rows)
        ),
        "matrix_contract_changed": False,
        "product_behavior_changed": False,
    }


def _allowlist_by_key(
    rows: Iterable[Mapping[str, str]],
) -> dict[tuple[str, str, str, str], Mapping[str, str]]:
    by_key: dict[tuple[str, str, str, str], Mapping[str, str]] = {}
    for row in rows:
        key = _key(row)
        if not all(key):
            raise ValueError(
                "allowlist rows require peak_hypothesis_id, feature_family_id, seed_group_id, and sample_stem"
            )
        if key in by_key:
            raise ValueError(f"duplicate backfill PeakHypothesis promotion allowlist key: {key}")
        by_key[key] = row
    return by_key


def _shadow_by_key(
    rows: Iterable[Mapping[str, str]],
) -> dict[tuple[str, str, str, str], Mapping[str, str]]:
    by_key: dict[tuple[str, str, str, str], Mapping[str, str]] = {}
    for row in rows:
        key = _key(row)
        if not all(key):
            continue
        if key in by_key:
            raise ValueError(f"duplicate shadow projection PeakHypothesis key: {key}")
        by_key[key] = dict(row)
    return by_key


def _key(row: Mapping[str, str]) -> tuple[str, str, str, str]:
    return (
        text_value(row.get("peak_hypothesis_id")),
        text_value(row.get("feature_family_id")),
        text_value(row.get("seed_group_id")),
        text_value(row.get("sample_stem")),
    )


def _valid_same_peak_ms1_chain(chain: str) -> bool:
    if not chain:
        return False
    return (
        "MS1:product_authorized:" in chain
        and (
            ":supportive:trace_constellation:" in chain
            or ":partial_support:trace_constellation:" in chain
        )
        and "same_peak_reason:family_ms1_overlay_anchor_peak_own_max_shape_supported" in chain
    )


def _positive_number(value: object) -> float | None:
    try:
        numeric = float(str(value))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or numeric <= 0:
        return None
    return numeric
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_backfill_peakhypothesis_promotion.py
```

Expected: `5 passed`.

## Task 4: Add CLI

**Files:**
- Create: `tools/diagnostics/backfill_peakhypothesis_promotion.py`
- Modify: `tests/test_backfill_peakhypothesis_promotion.py`

- [ ] **Step 1: Add CLI test**

Append to `tests/test_backfill_peakhypothesis_promotion.py`:

```python
def test_cli_writes_outputs(tmp_path: Path) -> None:
    shadow = _shadow_row(
        family="FAM005",
        seed="seed::FAM005::mz=500::rt=11",
        sample="S1",
        value="678.9",
    )
    allowlist = _allowlist_row(
        family="FAM005",
        seed="seed::FAM005::mz=500::rt=11",
        sample="S1",
        expected_chain=shadow["product_authority_chain"],
    )
    shadow_tsv = tmp_path / "shadow.tsv"
    allowlist_tsv = tmp_path / "allowlist.tsv"
    output_dir = tmp_path / "out"
    _write_tsv(shadow_tsv, [shadow])
    _write_tsv(allowlist_tsv, [allowlist])

    from tools.diagnostics import backfill_peakhypothesis_promotion as cli

    exit_code = cli.main(
        [
            "--shadow-projection-cells-tsv",
            str(shadow_tsv),
            "--authority-allowlist-tsv",
            str(allowlist_tsv),
            "--shadow-projection-sha256",
            "shadow-sha",
            "--output-dir",
            str(output_dir),
            "--source-run-id",
            "unit",
        ]
    )

    assert exit_code == 0
    assert (output_dir / "backfill_peakhypothesis_promotion_cells.tsv").is_file()
    assert (output_dir / "backfill_peakhypothesis_area_uncertainty.tsv").is_file()
    assert (output_dir / "backfill_peakhypothesis_promotion_summary.json").is_file()


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
```

- [ ] **Step 2: Create CLI implementation**

Create `tools/diagnostics/backfill_peakhypothesis_promotion.py`:

```python
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from xic_extractor.diagnostics import backfill_peakhypothesis_promotion as promotion
from xic_extractor.diagnostics.diagnostic_io import read_tsv_required


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    shadow_rows = read_tsv_required(
        args.shadow_projection_cells_tsv,
        promotion.SHADOW_REQUIRED_COLUMNS,
    )
    allowlist_rows = read_tsv_required(
        args.authority_allowlist_tsv,
        promotion.ALLOWLIST_REQUIRED_COLUMNS,
    )
    index = promotion.build_promotion_index(
        shadow_projection_rows=shadow_rows,
        allowlist_rows=allowlist_rows,
        shadow_projection_sha256=args.shadow_projection_sha256,
        source_run_id=args.source_run_id,
        readiness_label=args.readiness_label,
    )
    outputs = promotion.write_promotion_outputs(args.output_dir, index)
    print(f"wrote {outputs.cells_tsv}")
    print(f"wrote {outputs.area_uncertainty_tsv}")
    print(f"wrote {outputs.summary_json}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build allowlisted PeakHypothesis backfill promotion projection outputs."
        )
    )
    parser.add_argument("--shadow-projection-cells-tsv", type=Path, required=True)
    parser.add_argument("--authority-allowlist-tsv", type=Path, required=True)
    parser.add_argument("--shadow-projection-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-run-id", default="")
    parser.add_argument(
        "--readiness-label",
        choices=("diagnostic_only", "shadow_ready"),
        default="diagnostic_only",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run focused tests and lint**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_backfill_peakhypothesis_promotion.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/diagnostics/backfill_peakhypothesis_promotion.py tools/diagnostics/backfill_peakhypothesis_promotion.py tests/test_backfill_peakhypothesis_promotion.py
```

Expected: tests pass and ruff reports `All checks passed!`.

## Task 5: Existing-Artifact Smoke

**Files:**
- Output only under: `output/backfill_peakhypothesis_promotion_8raw_20260608/`
- Modify after run: `docs/superpowers/notes/2026-06-07-backfill-evidence-reconciliation-productization-note.md`

- [ ] **Step 1: Generate a review queue, not a product allowlist**

Use the existing 8RAW shadow projection:

```powershell
$shadow = "output\backfill_evidence_chain_8raw_seed_audit_20260607\reconciliation_seed_gate_overlay\shadow_production_projection_cells.tsv"
$out = "output\backfill_peakhypothesis_promotion_8raw_20260608"
$queue = Join-Path $out "backfill_peakhypothesis_review_queue.tsv"
$shadowHash = (Get-FileHash -Algorithm SHA256 $shadow).Hash.ToLowerInvariant()
New-Item -ItemType Directory -Force -Path $out | Out-Null
Import-Csv $shadow -Delimiter "`t" |
  Where-Object { $_.shadow_decision -eq "accept" -and $_.projected_matrix_written -eq "TRUE" } |
  Select-Object `
    @{n="schema_version";e={"backfill_peakhypothesis_promotion_allowlist_v1"}},
    peak_hypothesis_id,
    activation_unit_scope,
    feature_family_id,
    seed_group_id,
    sample_stem,
    @{n="authority_status";e={"review_pending"}},
    @{n="authority_source";e={"manual_gallery_review_required"}},
    @{n="authority_reason";e={"pending_same_peak_identity_and_area_policy_review"}},
    @{n="expected_shadow_projection_sha256";e={$shadowHash}},
    @{n="expected_shadow_projection_row_sha256";e={$_.shadow_projection_row_sha256}},
    @{n="expected_product_authority_chain";e={$_.product_authority_chain}},
    @{n="area_policy";e={""}},
    @{n="area_uncertainty_reason";e={""}},
    @{n="area_uncertainty_fraction";e={""}},
    @{n="area_uncertainty_fraction_status";e={""}},
    @{n="integration_bounds_source";e={""}},
    @{n="peak_start_rt";e={""}},
    @{n="peak_end_rt";e={""}},
    @{n="matrix_quantitative_use";e={"review_only"}},
    @{n="reviewer";e={""}},
    @{n="reviewed_at";e={""}} |
  Export-Csv $queue -Delimiter "`t" -NoTypeInformation
```

Expected:

- This creates a review queue only. It must not be passed to the promotion CLI.
- Rows with blank `peak_hypothesis_id` or `activation_unit_scope` stay review-only until `shadow_production_projection` is updated to emit PeakHypothesis identity.
- A human reviewer must manually filter rows and fill `authority_status=product_authorized`, `area_policy`, `matrix_quantitative_use`, reviewer metadata, and uncertainty fields before projection can become `shadow_ready`.

- [ ] **Step 2: Require a reviewed allowlist**

The reviewed file path is:

```powershell
$allow = "output\backfill_peakhypothesis_promotion_8raw_20260608\backfill_peakhypothesis_promotion_allowlist.tsv"
if (-not (Test-Path $allow)) {
  throw "Reviewed product_authorized allowlist is required. The review queue is not an activation input."
}
```

Expected: no automatic conversion from `shadow_decision=accept` to `authority_status=product_authorized`.

- [ ] **Step 3: Run projection CLI**

Run:

```powershell
$shadow = "output\backfill_evidence_chain_8raw_seed_audit_20260607\reconciliation_seed_gate_overlay\shadow_production_projection_cells.tsv"
$allow = "output\backfill_peakhypothesis_promotion_8raw_20260608\backfill_peakhypothesis_promotion_allowlist.tsv"
$shadowHash = (Get-FileHash -Algorithm SHA256 $shadow).Hash.ToLowerInvariant()
$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.backfill_peakhypothesis_promotion `
  --shadow-projection-cells-tsv $shadow `
  --authority-allowlist-tsv $allow `
  --shadow-projection-sha256 $shadowHash `
  --output-dir output\backfill_peakhypothesis_promotion_8raw_20260608\projection `
  --source-run-id backfill_evidence_chain_8raw_seed_audit_20260607 `
  --readiness-label shadow_ready
```

Expected:

- `backfill_peakhypothesis_promotion_cells.tsv`
- `backfill_peakhypothesis_area_uncertainty.tsv`
- `backfill_peakhypothesis_promotion_summary.json`
- `decision_counts.promote_matrix_write` equals manually allowlisted rows that did not drift.
- Rows are blocked if `peak_hypothesis_id`, source row hash, source file hash,
  `current_raw_status=rescued`, `current_matrix_written=FALSE`,
  `shadow_reasons`, product authority chain or reviewed
  `identity_supported_review` context, or area policy is incomplete.
- `nonstandard_assessable_area` rows are blocked with an area review-only reason.
- `matrix_contract_changed=false`
- `product_behavior_changed=false`

- [ ] **Step 4: Write closeout note section**

Append a section to `docs/superpowers/notes/2026-06-07-backfill-evidence-reconciliation-productization-note.md`:

```markdown
## Follow-up: PeakHypothesis Backfill Promotion Projection

Nonstandard but assessable peak shapes may support identity/backfill review, but
they remain blocked from matrix-write promotion until a separate integration
policy is approved.

Projection outputs:

- `output/backfill_peakhypothesis_promotion_8raw_20260608/projection/backfill_peakhypothesis_promotion_cells.tsv`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/projection/backfill_peakhypothesis_area_uncertainty.tsv`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/projection/backfill_peakhypothesis_promotion_summary.json`

Readiness remains `diagnostic_only` if only the review queue exists. It reaches
`shadow_ready` only when a manually reviewed `product_authorized` allowlist is
consumed by the projection CLI. Activation, 8RAW matrix diff, targeted benchmark
check, and 85RAW validation are still required before broader readiness claims.
```

## Task 6: Conditional Activation Planning Gate

**Files:**
- Inspect only first: `tools/diagnostics/apply_shared_peak_identity_activation.py`
- Conditional modify: activation bridge and focused tests

- [ ] **Step 1: Decide activation entry point**

Read:

```powershell
rg -n "activation|matrix|product_authority|backfill|area_uncertainty|alignment_matrix" tools\diagnostics\apply_shared_peak_identity_activation.py tests\test_shared_peak_identity_product_activation.py
```

Expected: identify whether the existing activation bridge can consume `backfill_peakhypothesis_promotion_cells.tsv` without creating a parallel matrix writer.

- [ ] **Step 2: Stop if activation would create a parallel product writer**

If activation cannot reuse the existing public matrix bridge, stop and write an addendum naming:

- current owner;
- successor owner;
- public matrix surface;
- expected matrix diff;
- uncertainty sidecar output;
- tests;
- validation tier.

- [ ] **Step 3: If activation is compatible, write RED tests**

Add focused tests proving:

- promoted rows write only exact allowlisted PeakHypothesis/sample cells;
- nonstandard assessable rows stay blocked and do not write matrix values;
- unassessable rows do not write matrix values;
- stale shadow projection hash fails closed;
- public `alignment_matrix.tsv` remains `Mz` / `RT` / sample columns.

## Verification Commands

Focused no-RAW:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_backfill_peakhypothesis_promotion.py tests/test_shadow_production_projection.py tests/test_backfill_evidence_reconciliation_gallery.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/diagnostics/backfill_peakhypothesis_promotion.py tools/diagnostics/backfill_peakhypothesis_promotion.py tests/test_backfill_peakhypothesis_promotion.py
```

If activation code changes:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_shared_peak_identity_product_activation.py tests/test_alignment_production_decisions.py tests/test_alignment_matrix_identity.py tests/test_untargeted_final_matrix_contract.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

8RAW before 85RAW:

```powershell
python -m scripts.agent_sandbox_doctor
```

Then use the foreground RAW command shapes from `docs/agent-parameter-settings.md`; do not launch 85RAW through background `Start-Process`.

## Self-Review

- Spec coverage: user decisions are captured in the addendum, schema, promotion tests, existing-artifact smoke, and validation gate.
- Filler-wording scan: no task uses forbidden filler wording or an unspecified "add tests" instruction.
- Type consistency: `area_policy`, `area_uncertainty_state`, and `promotion_decision` values are consistent across schemas, tests, and implementation snippets.
- Public contract: `alignment_matrix.tsv` shape remains unchanged; uncertainty is sidecar-only.
- Validation ceiling: synthetic and review-queue-only outputs stay `diagnostic_only`; reviewed projection can reach `shadow_ready`; activation plus 8RAW can reach `production_candidate`; 85RAW is required before `production_ready`.

## Execution Addendum, 2026-06-09

The user-reviewed top14 standard rows were projected through the sidecar path
without activation:

- projection refresh:
  `output/backfill_peakhypothesis_promotion_8raw_20260608/shadow_projection_identity_support_refresh/shadow_production_projection_summary.json`
- reviewed allowlist:
  `output/backfill_peakhypothesis_promotion_8raw_20260608/top14_user_standard_allowlist.tsv`
- sidecar output:
  `output/backfill_peakhypothesis_promotion_8raw_20260608/projection_top14_user_standard/backfill_peakhypothesis_promotion_summary.json`
- projection refresh counts: `block=454`, `context=349`,
  `identity_supported_review=185`, `projected_new_write_count=0`
- top14 sidecar counts: `allowlist_row_count=11`,
  `decision_counts.promote_matrix_write=11`,
  `area_uncertainty_counts.standard_assessable=11`
- contracts: `matrix_contract_changed=false`,
  `product_behavior_changed=false`

This is `shadow_ready` sidecar evidence only. The next gate remains activation
compatibility: consume the sidecar through the existing activation owner, prove
an exact matrix diff on the allowlisted PeakHypothesis/sample cells, and leave
nonstandard/borderline rows review-only.

## Activation Bridge Execution Addendum, 2026-06-09

The activation entry point was confirmed: do not add a parallel matrix writer.
Reviewed backfill promotions should first be converted into existing
`shared_peak_identity_activation_decision_v1` and
`shared_peak_identity_activation_acceptance_v1` sidecars, then applied only by
`tools/diagnostics/apply_shared_peak_identity_activation.py`.

Implemented bridge:

- `xic_extractor/diagnostics/backfill_peakhypothesis_activation_bridge.py`
- `tools/diagnostics/backfill_peakhypothesis_activation_bridge.py`
- `tests/test_backfill_peakhypothesis_activation_bridge.py`

The bridge defaults acceptance to `fail` and requires a later matrix-diff /
must-not-regress gate before product approval. Optional public matrix preflight
uses `alignment_matrix.tsv` plus `alignment_matrix_identity.tsv` to suppress
promotion cells already present in the public matrix. It now also writes
`activation_matrix_preflight.tsv` and distinguishes true already-written cells
from a projection/public-matrix conflict where the promotion snapshot says
`current_matrix_written=FALSE` but the public matrix has a value.

Observed top14 preflight:

- no-matrix bridge:
  `activation_decision_row_count=11`,
  `acceptance_status=fail`,
  `hard_fail_reasons=activation_acceptance_requires_matrix_diff_validation`
- old public-matrix bridge:
   `promotion_row_count=11`,
   `public_matrix_already_written_count=11`,
  `public_matrix_projection_conflict_count=11`,
   `activation_decision_row_count=0`,
  `hard_fail_reasons=public_matrix_conflicts_with_projection_current_snapshot`,
  `next_action=rebuild_alignment_matrix_with_current_writer_before_activation`
- current-writer matrix rebuild:
  `old_public_matrix_rows=343`, `rebuilt_matrix_rows=343`,
  `promotion_rows=11`, `old_written_current_blank=11`
- whole-matrix old/public vs current-writer presence drift:
  `old_written_current_blank=406`, `old_blank_current_written=35`
- current-writer bridge:
  `promotion_row_count=11`,
  `public_matrix_already_written_count=0`,
  `public_matrix_projection_conflict_count=0`,
  `activation_decision_row_count=11`,
  `hard_fail_reasons=activation_acceptance_requires_matrix_diff_validation`,
  `next_action=run_activation_matrix_diff_smoke`
- current-writer diagnostic activation copy:
  `auto_activate_count=11`,
  `canonical_row_identity_ready=TRUE`,
  `matrix_cells_written=11`,
  all 11 value-delta rows `written, TRUE`
- current-writer post-activation matrix-diff acceptance:
  `validation_scope=8raw_current_writer_matrix_diff`,
  `promotion_row_count=11`, `activation_decision_row_count=11`,
  `preflight_needs_activation_count=11`, `value_delta_row_count=11`,
  `changed_matrix_cell_count=11`, `unexpected_matrix_diff_count=0`,
  `missing_matrix_diff_count=0`, `value_mismatch_count=0`,
  `acceptance_status=pass`

Root cause: the 2026-06-07 public `alignment_matrix.tsv` is not a coherent
activation oracle for the current production decision policy. Rebuilding the
matrix from the same `alignment_review.tsv` / `alignment_cells.tsv` with the
current writer blanks the user-reviewed top14 promotion cells, so the old public
matrix values are stale/mixed relative to the current writer. On coherent
current-writer artifacts, the activation path can add the 11 allowlisted
PeakHypothesis/sample values through the existing activation owner, and the
post-activation diff confirms no unrelated public matrix cells changed. This is
8RAW/current-writer diagnostic acceptance for the allowlisted slice only; 85RAW
validation is still required before production use.

## 85RAW Hypothesis-Anchor Slice Gate Addendum, 2026-06-09

Implemented and corrected a direct-transfer gate for the reviewed top14
PeakHypothesis backfill slice:

- `xic_extractor/diagnostics/backfill_peakhypothesis_raw85_slice_gate.py`
- `tools/diagnostics/backfill_peakhypothesis_raw85_slice_gate.py`
- `tests/test_backfill_peakhypothesis_raw85_slice_gate.py`

The gate consumes existing artifacts only:

- `backfill_peakhypothesis_promotion_cells.tsv`
- 85RAW `alignment_review.tsv`
- 85RAW `alignment_cells.tsv`

Correction: cross-run `feature_family_id` is not a stable identity key. The
gate now uses the reviewed promotion seed m/z/RT anchor plus sample to find the
85RAW candidate when a seed anchor is present. Family IDs remain only local
artifact labels. Direct 85RAW activation is allowed only when the anchored
PeakHypothesis/sample cell still exists as a primary matrix row, is not blocked
by unresolved family consolidation, has `detected` or `rescued` status, and has
a positive `gaussian15_positive_asls_residual` primary matrix area. Anchored
detected/rescued cells blocked only by family consolidation or non-primary-row
ownership are reported as `hypothesis_candidate_review`; absent/missing-area or
duplicate-assigned cells still fail closed.

Observed top14 result:

- artifact:
  `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_slice_gate_top14_user_standard/backfill_peakhypothesis_raw85_slice_gate.tsv`
- `gate_status=partial`
- `promotion_row_count=11`
- `candidate_no_regression_count=0`
- `hypothesis_candidate_review_count=11`
- `blocked_count=0`
- `exact_cell_found_count=11`
- `not_primary_matrix_row_count=9`
- `primary_loser_count=9`
- `family_consolidation_review_count=11`
- `duplicate_assigned_count=0`
- `absent_count=0`

The corresponding transfer-readiness artifact was updated to consume the slice
gate summary:

- `raw85_slice_gate_status=partial`
- `raw85_slice_gate_hypothesis_candidate_review_count=11`
- `raw85_slice_gate_blocked_count=0`
- `raw85_peak_shape_review_status=manual_same_peak_supported_all_review_candidates`
- `readiness_label=production_candidate`
- `production_ready=FALSE`
- `hard_fail_reasons=` empty
- `remaining_blockers=explicit_product_transfer_decision_required;raw85_consolidation_policy_not_productized`
- `next_action=define_raw85_consolidation_policy_for_same_peak_non_primary_candidates`

Interpretation: the 8RAW user-reviewed allowlist remains useful evidence for
standard peak shape in those observed cells, and the corrected gate now shows
that the corresponding 85RAW m/z/RT-anchored candidates are present rather than
absent. For example, 8RAW `FAM000572 / Breast_Cancer_Tissue_pooled_QC5` maps to
85RAW `FAM005540`, not to the local 85RAW `FAM000572`, and the matched cell is
`rescued` with `primary_matrix_area=48462.2`. Follow-up manual review confirmed
all 11 anchored 85RAW candidates as selected on the correct same peak. The slice
still does not directly generalize to 85RAW product activation because row
ownership changed under 85RAW family consolidation. The next production-transfer
path is an explicit policy for how same-peak PeakHypothesis evidence is recorded
when broad family consolidation mixes multiple peaks.

## 85RAW Hypothesis Review Queue Addendum, 2026-06-09

The corrected partial slice gate now has a dedicated review queue:

- `xic_extractor/diagnostics/backfill_peakhypothesis_raw85_hypothesis_review.py`
- `tools/diagnostics/backfill_peakhypothesis_raw85_hypothesis_review.py`
- `tests/test_backfill_peakhypothesis_raw85_hypothesis_review.py`

Input:

- `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_slice_gate_top14_user_standard/backfill_peakhypothesis_raw85_slice_gate.tsv`

Observed output:

- `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_hypothesis_review_top14_user_standard/backfill_peakhypothesis_raw85_hypothesis_review_queue.tsv`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_hypothesis_review_top14_user_standard/backfill_peakhypothesis_raw85_hypothesis_review_summary.json`

Observed summary:

- `review_queue_status=manual_review_required`
- `input_row_count=11`
- `candidate_queue_count=11`
- `direct_candidate_count=0`
- `blocked_input_count=0`
- `non_primary_candidate_count=9`
- `primary_row_consolidation_context_count=2`
- `next_action=manual_review_85raw_hypothesis_candidates`

Interpretation: this is the review surface for deciding whether each corrected
85RAW m/z/RT-anchored candidate is same-peak evidence strong enough to carry
forward. It intentionally leaves `reviewer_verdict` and `reviewer_note` blank,
records
`proposed_product_transfer_status=review_only_pending_same_peak_and_consolidation_policy`,
and does not choose peak S/N or mutate product matrices.

## 85RAW Overlay Addendum, 2026-06-09

The review queue now has RAW-backed overlay plots so reviewers do not need to
open each candidate in Xcalibur:

- `xic_extractor/diagnostics/backfill_peakhypothesis_raw85_overlay.py`
- `tools/diagnostics/backfill_peakhypothesis_raw85_overlay.py`
- `tests/test_backfill_peakhypothesis_raw85_overlay.py`

Input:

- `raw85_hypothesis_review_top14_user_standard/backfill_peakhypothesis_raw85_hypothesis_review_queue.tsv`
- 85RAW `alignment_review.tsv`
- `local_validation_artifacts/discovery/accepted_p8b/85raw/discovery_batch_index.csv`
- Thermo DLL dir `C:\Xcalibur\system\programs`

Observed output:

- `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_hypothesis_overlay_top14_user_standard/backfill_peakhypothesis_raw85_overlay_gallery.html`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_hypothesis_overlay_top14_user_standard/backfill_peakhypothesis_raw85_overlay_index.tsv`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_hypothesis_overlay_top14_user_standard/backfill_peakhypothesis_raw85_overlay_summary.json`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_hypothesis_overlay_top14_user_standard/plots/`

Observed summary:

- `overlay_count=11`
- `smooth_method=gaussian15_asls_residual`
- `smooth_window_points=15`
- `matrix_contract_changed=false`
- `product_behavior_changed=false`
- `next_action=review_overlay_pngs_for_same_peak_candidate_status`

Interpretation: each plot overlays raw XIC plus
`gaussian15_asls_residual` smoothed XIC for the candidate m/z and current
consolidation winner m/z in the same RAW sample, with candidate anchor RT,
candidate peak window, and winner RT marked. This is visual review evidence
only. It does not choose S/N or promote any candidate. Representative QA showed
that `FAM000572 -> FAM005540` has a visible candidate-window peak while the
winner RT sits later, and `FAM000808 -> FAM007718` exposes a large candidate-vs-
winner RT disagreement that should not be hidden behind family consolidation.

## 85RAW Manual Same-Peak Review Addendum, 2026-06-09

The user reviewed all 11 RAW+Gaussian15 overlay cards and judged every selected
candidate as the correct same peak:

- `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_hypothesis_manual_review_top14_user_standard/backfill_peakhypothesis_raw85_manual_verdicts.tsv`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_hypothesis_manual_review_top14_user_standard/backfill_peakhypothesis_raw85_manual_verdict_summary.json`

Observed summary:

- `reviewed_candidate_count=11`
- `same_peak_supported_count=11`
- `same_peak_conflict_count=0`
- `unreviewed_candidate_count=0`
- `raw85_peak_shape_review_status=manual_same_peak_supported_all_review_candidates`

The transfer-readiness surface now consumes this manual verdict summary. It no
longer treats the partial slice gate as a peak-shape hard failure; it reports
`readiness_label=production_candidate`, keeps `production_ready=FALSE`, and
names `raw85_consolidation_policy_not_productized` as the remaining blocker.

## Normal-Peak Decision Addendum, 2026-06-09

The user clarified the normal-peak scope with a Gaussian-shape reference:
normal peaks include complete one-peak distributions from broad/flat through
sharp/peaked. The required distinction is the selected segment's Gaussian15
positive AsLS residual morphology, not a narrow sigma, perfect symmetry, raw XIC
spikiness, neighboring peak contact, family/window-level multiplets, or
family consolidation/non-primary ownership context.

Policy definition:

- `normal_peak_shape_definition=gaussian15_asls_residual_selected_segment_single_complete_unimodal_peak;raw_spikes_neighbor_contact_family_multiplet_not_blockers`
- `standard_assessable_area` means the selected PeakHypothesis/sample cell fits
  that complete single-peak shape definition and the existing Gaussian15
  positive AsLS residual area is acceptable as the matrix value. Raw spikes,
  adjacent peak contact, and family/window-level multiplets do not make the
  selected segment nonstandard by themselves.
- `nonstandard_assessable_area` remains outside this goal, even if identity is
  same-peak supported.

Implemented decision surface:

- `xic_extractor/diagnostics/backfill_peakhypothesis_normal_peak_decision.py`
- `tools/diagnostics/backfill_peakhypothesis_normal_peak_decision.py`
- `tests/test_backfill_peakhypothesis_normal_peak_decision.py`

Observed output:

- `output/backfill_peakhypothesis_promotion_8raw_20260608/normal_peak_decision_top14_user_standard/backfill_peakhypothesis_normal_peak_decisions.tsv`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/normal_peak_decision_top14_user_standard/backfill_peakhypothesis_normal_peak_decision_summary.json`

Observed summary:

- `row_count=11`
- `normal_peak_candidate_count=11`
- `required_backfill_count=11`
- `review_only_nonstandard_count=0`
- `blocked_count=0`
- `consolidation_override_count=11`
- `normal_peak_policy_status=normal_peak_backfill_required_all_reviewed_candidates`
- `normal_peak_shape_definition=gaussian15_asls_residual_selected_segment_single_complete_unimodal_peak;raw_spikes_neighbor_contact_family_multiplet_not_blockers`
- `decision_counts.require_backfill=11`

Interpretation: for the current top14 reviewed normal-peak slice, the decision
problem is now explicit at PeakHypothesis/sample-cell scope: all 11 reviewed
normal same-peak candidates must backfill. Family consolidation and
non-primary-row ownership are recorded as policy effects, not evidence that the
peak is wrong.

Activation bridge follow-up:

- `xic_extractor/diagnostics/backfill_peakhypothesis_activation_bridge.py`
  consumes optional `--normal-peak-decisions-tsv` as a fail-closed activation
  prerequisite.
- `tools/diagnostics/backfill_peakhypothesis_activation_bridge.py`
  supports `--normal-peak-decisions-tsv`.
- `tests/test_backfill_peakhypothesis_activation_bridge.py` covers activation
  allowed by `require_backfill`, fail-closed non-required decisions, and CLI
  input wiring.

Observed normal-peak-checked bridge output:

- `output/backfill_peakhypothesis_promotion_8raw_20260608/activation_bridge_top14_user_standard_normal_peak_checked/backfill_peakhypothesis_activation_bridge_summary.json`
- `normal_peak_decision_input_count=11`
- `normal_peak_required_backfill_count=11`
- `normal_peak_decision_blocked_count=0`
- `activation_decision_row_count=11`
- `public_matrix_projection_conflict_count=0`

Observed normal-peak-checked matrix diff acceptance:

- `output/backfill_peakhypothesis_promotion_8raw_20260608/activation_acceptance_top14_user_standard_normal_peak_checked/backfill_peakhypothesis_activation_acceptance_summary.json`
- `acceptance_status=pass`
- `changed_matrix_cell_count=11`
- `expected_written_count=11`
- `application_matrix_cells_written=11`
- `unexpected_matrix_diff_count=0`
- `missing_matrix_diff_count=0`
- `value_mismatch_count=0`

Interpretation: the reviewed normal-peak slice now has both a PeakHypothesis
decision artifact and an activation/matrix-diff acceptance proof. This still
does not make the full 85RAW workflow production-ready; it proves the current
reviewed normal-peak slice can be activated without unrelated public matrix
diffs.

## 85RAW Artifact-Only Activation Trial Addendum, 2026-06-09

Subagent review converged on the same implementation direction:

- Policy review: `normal_peak_decision=require_backfill` may override
  family-consolidation / non-primary ownership only when the decision is
  PeakHypothesis/sample scoped, same-peak supported, normal-peak gated, positive
  Gaussian15 area, and matrix diff acceptance changes only expected cells.
- Code-impact review: the smallest product owner is the existing activation
  owner, not `primary_consolidation`, `claim_registry`, `owner_matrix`, or the
  base matrix writer.
- Validation review: do an artifact-only / no-RAW 85RAW trial before rerunning
  85RAW, because a plain rerun without override counters would recreate current
  artifacts and leave the same policy question unresolved.

Implemented trial surface:

- `xic_extractor/diagnostics/backfill_peakhypothesis_85raw_activation_trial.py`
- `tools/diagnostics/backfill_peakhypothesis_85raw_activation_trial.py`
- `tests/test_backfill_peakhypothesis_85raw_activation_trial.py`

Observed 85RAW preflight:

- command status: `Alignment launch preflight OK`;
- sample count: `85`;
- candidate CSVs found: `85`;
- RAW paths found: `85`;
- canonical 85RAW contract: enforced;
- no candidate CSVs loaded and no RAW files opened.

Observed artifact-only trial output:

- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_trial_artifact_only/backfill_peakhypothesis_85raw_activation_trial.tsv`
- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_trial_artifact_only/backfill_peakhypothesis_85raw_activation_trial_summary.json`

Observed summary:

- `trial_status=pass`;
- `validation_mode=artifact_only_no_raw`;
- `candidate_count=30289`;
- `sample_count=85`;
- `matrix_row_count=685`;
- `normal_peak_required_count=11`;
- `nonstandard_blocked_count=0`;
- `same_peak_supported_count=11`;
- `same_peak_conflict_count=0`;
- `primary_loser_count=9`;
- `primary_winner_count=2`;
- `consolidation_override_count=9`;
- `already_primary_matrix_written_count=0`;
- `expected_matrix_diff_count=11`;
- `unexpected_diff_count=0`;
- `owner_backfill_elapsed_sec=408.9423352999984`;
- `build_matrix_elapsed_sec=60.98443249999946`;
- `claim_registry_elapsed_sec=57.67576149999877`;
- `primary_consolidation_elapsed_sec=89.63260999999875`;
- `write_outputs_elapsed_sec=219.65262780000012`;
- `next_action=implement_normal_peak_override_activation_transfer`.

Interpretation: the current 85RAW public matrix does not already satisfy any of
the 11 reviewed normal-peak same-peak cells, including the two candidates whose
review context is `primary_winner`. The transfer key must be
`raw85_matched_peak_hypothesis_id + sample`, not the 8RAW source FAM ID. The
next code slice should implement a transfer activation path that emits 85RAW
activation decisions for these reviewed normal-peak cells and applies them
through `apply_shared_peak_identity_activation.py` / `product_activation`, then
reruns matrix-diff acceptance. A full 85RAW RAW rerun should wait until that
product path exists; otherwise it will not answer the override-cost question.

## 85RAW Normal-Peak Transfer Activation Closure, 2026-06-09

Implemented:

- `xic_extractor/diagnostics/backfill_peakhypothesis_85raw_activation_transfer.py`
- `tools/diagnostics/backfill_peakhypothesis_85raw_activation_transfer.py`
- `tests/test_backfill_peakhypothesis_85raw_activation_transfer.py`

The transfer diagnostic rewrites the activation key from the reviewed source
PeakHypothesis/FAM id to `raw85_matched_peak_hypothesis_id + sample`. Source
ids remain audit-only provenance and are not used as activation keys.
`source_artifact_sha256` is now the content bundle hash of the normal-peak
decision TSV plus activation-trial TSV, not a synthetic hash derived from
source/activation ids.

Source-bundle rerun, 2026-06-09:

- transfer:
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_artifact_only_source_bundle/`;
- bridge:
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_bridge_transfer_artifact_only_source_bundle/`;
- matrix-only application:
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_matrix_only_source_bundle/`;
- acceptance:
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_acceptance_matrix_only_source_bundle/`.

Observed source-bundle acceptance:

- `acceptance_status=pass`;
- `changed_matrix_cell_count=11`;
- `unexpected_matrix_diff_count=0`;
- `missing_matrix_diff_count=0`;
- `value_mismatch_count=0`;
- `value_delta_mismatch_count=0`;
- all 11 promotion, transfer, and value-delta rows carry the same actual
  `normal_peak_decisions_tsv + activation_trial_tsv` content bundle hash.

Observed transfer + bridge outputs:

- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_artifact_only/backfill_peakhypothesis_85raw_transfer_promotion_cells.tsv`
- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_artifact_only/backfill_peakhypothesis_85raw_activation_transfer_summary.json`
- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_bridge_transfer_artifact_only/backfill_peakhypothesis_activation_bridge_summary.json`

Observed transfer/bridge summary:

- `transfer_status=pass`;
- `promotion_row_count=11`;
- `activation_key_authority=raw85_matched_peak_hypothesis_id`;
- `source_peak_hypothesis_id_authority=audit_only_not_activation_key`;
- `blocked_transfer_row_count=0`;
- bridge `activation_decision_row_count=11`;
- bridge `public_matrix_projection_conflict_count=0`;
- bridge preflight: 11 `needs_activation, emit_activation_decision`.

Diagnostic activation copy:

- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_diagnostic/activation_application_summary.tsv`
- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_diagnostic/activation_value_delta.tsv`
- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_diagnostic/alignment_matrix.tsv`
- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_diagnostic/alignment_matrix_identity.tsv`

Matrix-only activation copy:

- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_matrix_only/activation_application_summary.tsv`
- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_matrix_only/activation_value_delta.tsv`
- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_matrix_only/alignment_matrix.tsv`
- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_matrix_only/alignment_matrix_identity.tsv`
- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_matrix_only/activation_hypothesis_identity.tsv`

Observed activation application summary:

- `auto_activate_count=11`;
- `matrix_cells_written=11`;
- `matrix_cells_blanked=0`;
- `matrix_value_conflict_cells=0`;
- `families_added_to_matrix=9`;
- `input_matrix_rows=685`;
- `output_matrix_rows=694`;
- `canonical_row_identity_ready=TRUE`.

Matrix-only architecture note: this path writes the same reviewed normal-peak
matrix changes without reading or rewriting 85RAW `alignment_cells.tsv`.
`alignment_cells.tsv` remains an audit/debug ledger and evidence-projection
surface; it is no longer a required dependency for reviewed normal-peak
activation once product-authorized activation values are available.

Schema/provenance closure: `activation_value_delta.tsv` is now schema v3 and
records `matrix_value_kind`, `matrix_value_source`,
`matrix_value_source_field`, `matrix_value_source_detail`,
`matrix_value_source_artifact_schema_version`,
`matrix_value_source_artifact_sha256`, and
`matrix_value_source_row_sha256`. Matrix-only normal-peak writes are labeled
`matrix_value_kind=backfill_activation` from
`activation_values_tsv/projected_matrix_value`, so the public matrix can be
filled while the value source remains separate from primary detection.

Post-activation acceptance:

- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_acceptance_transfer_artifact_only/backfill_peakhypothesis_activation_acceptance.tsv`
- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_acceptance_transfer_artifact_only/backfill_peakhypothesis_activation_matrix_diff.tsv`
- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_acceptance_transfer_artifact_only/backfill_peakhypothesis_activation_acceptance_summary.json`
- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_acceptance_matrix_only/backfill_peakhypothesis_activation_acceptance_summary.json`

Observed acceptance summary:

- `validation_scope=85raw_current_writer_matrix_diff`;
- `acceptance_status=pass`;
- `changed_matrix_cell_count=11`;
- `expected_written_count=11`;
- `unexpected_matrix_diff_count=0`;
- `missing_matrix_diff_count=0`;
- `value_mismatch_count=0`;
- `application_summary_mismatch_count=0`;
- `next_action=ready_for_85raw_reviewed_activation_acceptance`.

Acceptance gate update: `backfill_peakhypothesis_activation_acceptance.py` now
allows application row-count changes only when
`families_added_to_matrix`/`families_removed_from_matrix` exactly explain the
input/output matrix row delta. This is required for PeakHypothesis transfer
because 9 reviewed primary-loser cells add raw85 PeakHypothesis rows while still
changing only the 11 expected matrix cells.

## 85RAW Winner-Remap Retraction, 2026-06-09

The winner-remap route below was implemented as a diagnostic proposal, but the
observed top14 artifact generated before the hypothesis-anchor correction is now
obsolete:

- `xic_extractor/diagnostics/backfill_peakhypothesis_raw85_winner_remap.py`
- `tools/diagnostics/backfill_peakhypothesis_raw85_winner_remap.py`
- `tests/test_backfill_peakhypothesis_raw85_winner_remap.py`

Obsolete output:

- `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_winner_remap_top14_user_standard/backfill_peakhypothesis_raw85_winner_remap.tsv`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_winner_remap_top14_user_standard/backfill_peakhypothesis_raw85_winner_remap_summary.json`

Reason: the input slice gate used local `feature_family_id` equality and
therefore mixed unrelated 8RAW and 85RAW family labels. Family winners can also
collapse multiple peaks inside a broad family/window, so they are not
PeakHypothesis authority. Keep the module only as optional family-consolidation
context if regenerated from the corrected hypothesis-anchor slice gate; do not
use the stale top14 winner-remap artifact as product evidence.
