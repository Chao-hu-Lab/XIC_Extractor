# Validation Artifact Fixture Surface Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan one task at a time. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the remaining `docs/superpowers/validation/` `shrink_later` fixture-like artifact debt with explicit summary/hash contracts plus minimal golden fixtures, without changing extraction, ProductWriter, workbook, GUI, selected peak/area/counting, Backfill authority, or matrix semantics.

**Architecture:** Keep `docs/superpowers/validation/` as a tracked contract/index/hash/minimal-fixture surface. Full QuantMatrix result tables may still be generated for local review, but default builders and checkers must not require full generated TSVs to be tracked in git when a summary plus golden slice is sufficient. Product behavior stays unchanged; this is no-RAW artifact-retention and fixture-contract work.

**Scope Note:** This plan is only for fixture-like artifacts under `docs/superpowers/validation/`. The canonical fixture directory `docs/superpowers/fixtures/` has a separate cleanup plan and must not be edited by agents executing this plan.

**Tech Stack:** Python 3.13, `uv`, `pytest`, `ruff`, `mypy`, `xic_extractor.tabular_io`, existing QuantMatrix builder/checker modules.

## Global Constraints

- Worktree/branch: repo root worktree, branch `cc/framework-improvements`.
- Scope is `docs/superpowers/validation/` only; do not edit `docs/superpowers/fixtures/` under this plan.
- Do not run RAW or 85RAW.
- Do not alter ProductWriter/default extraction/workbook/GUI/selected peak/area/counting/Backfill authority/matrix semantics.
- Do not silently promote or demote a productization maturity tier.
- If execution changes a maturity tier, active lane, output schema, review/replay behavior, or matrix authority, update `docs/superpowers/plans/2026-06-15-productization-control-plane.md` and `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md`.
- If execution remains fixture-retention-only, state explicitly in closeout that no control-plane tier update is needed.
- Keep full generated artifacts under ignored `local_validation_artifacts/externalized_superpowers_validation/` or another ignored local validation path, not as tracked validation files.
- `scripts/check_validation_artifact_retention.py --strict` is the final acceptance gate for eliminating `shrink_later`.

---

## Preflight Contract

Goal: shrink the remaining validation fixture/result debt to tracked summaries and minimal fixtures.
Existing owner/helper to reuse: `scripts/check_validation_artifact_retention.py`, QuantMatrix builder/checker scripts, `xic_extractor.tabular_io`.
New code location: small reusable fixture-summary helpers in `xic_extractor/alignment/quant_matrix_fixture_contract.py`; builder/checker wiring in existing QuantMatrix scripts.
Evidence provider role: none. This work only preserves validation replay contracts and fixture checks.
Simplest product rule: tracked validation fixtures prove schema, authority flags, counts, hashes, and replay wiring; full generated rows are local artifacts unless they are the explicit minimal golden slice.
Call-cost model: no RAW calls; no scorer calls; only TSV reads/hashes over existing validation artifacts and synthetic tests.
Public contracts at risk: validation artifact paths, retention inventory decisions, QuantMatrix check-only expectations, productization status hash entries, and handoff/control-plane wording.
Validation gate: retention checker default and strict mode, productization state checker, focused QuantMatrix tests, scoped ruff, `mypy xic_extractor`, `git diff --check`, staged credential/local-path scan before commit.
Stop rule: if a full TSV is still required by a checker default, productization status index, or test after the summary/slice replacement is added, keep that file as `shrink_later` and document the blocker instead of deleting it.

## Current Fixture Debt

`ARTIFACT_INVENTORY.tsv` currently has `166` retained validation files, `132` externalized artifacts, and `4` `shrink_later` rows:

- `docs/superpowers/validation/quant_matrix_default_product_activation_v1/default_output/cell_provenance.tsv` - `18,001` lines, full result TSV, still used by default activation checks.
- `docs/superpowers/validation/quant_matrix_real_bundle_v1/quant_matrix_version/cell_provenance.tsv` - `18,001` lines, full result TSV, still used by real-bundle readiness/downstream/check-only paths.
- `docs/superpowers/validation/quant_matrix_real_bundle_v1/review/quant_matrix_review_rows.tsv` - `18,001` lines, full review TSV, still used as review/replay context.
- `docs/superpowers/validation/quant_matrix_promotion_validation_packet_v1/readiness_integration_fixture/inputs/cell_provenance.tsv` - `3` lines, synthetic readiness integration fixture; this is already a minimal fixture and should be reclassified, not shrunk.

## Files

- Create: `xic_extractor/alignment/quant_matrix_fixture_contract.py`
- Modify: `scripts/build_quant_matrix_real_bundle.py`
- Modify: `scripts/build_quant_matrix_default_product_activation.py`
- Modify: `scripts/build_quant_matrix_promotion_validation_packet.py`
- Modify: `scripts/check_validation_artifact_retention.py`
- Modify: `docs/superpowers/validation/ARTIFACT_INVENTORY.tsv`
- Modify: `docs/superpowers/validation/RETENTION.md`
- Modify: `docs/superpowers/validation/quant_matrix_real_bundle_v1/quant_matrix_real_bundle_summary.json`
- Modify: `docs/superpowers/validation/quant_matrix_default_product_activation_v1/quant_matrix_default_product_activation_summary.json`
- Modify: `docs/superpowers/validation/productization_status_index_v1.tsv` only if hash/path references change.
- Modify: `docs/superpowers/plans/2026-06-15-productization-control-plane.md` only if execution changes a tier/active lane/public review contract; otherwise note no tier update in closeout.
- Modify: `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md` to keep the current-state snapshot accurate after execution.
- Test: `tests/test_quant_matrix_fixture_contract.py`
- Test: `tests/test_quant_matrix_real_bundle.py`
- Test: `tests/test_quant_matrix_default_product_activation.py`
- Test: `tests/test_quant_matrix_promotion_packet_v2.py`
- Test: `tests/test_validation_artifact_retention.py`
- Test: `tests/test_productization_state_index.py`

## Task 1: Reclassify The Existing Tiny Readiness Fixture

**Files:**
- Modify: `docs/superpowers/validation/ARTIFACT_INVENTORY.tsv`
- Modify: `docs/superpowers/validation/RETENTION.md`
- Test: `tests/test_validation_artifact_retention.py`

**Interfaces:**
- Consumes: current inventory decision values from `RETENTION.md`.
- Produces: one fewer false `shrink_later` row before large TSV shrink work starts.

- [ ] **Step 1: Add a regression test for tiny fixture classification**

Add a test in `tests/test_validation_artifact_retention.py`:

```python
def test_readiness_integration_cell_provenance_is_minimal_fixture() -> None:
    rows = _read_inventory_rows()
    row = rows[
        "docs/superpowers/validation/quant_matrix_promotion_validation_packet_v1/"
        "readiness_integration_fixture/inputs/cell_provenance.tsv"
    ]
    assert row["retention_decision"] == "keep_minimal_fixture"
    assert row["category"] == "tabular_contract"
    assert "synthetic readiness integration fixture" in row["keep_reason"]
```

If `_read_inventory_rows()` does not exist, add it near the existing test helpers:

```python
def _read_inventory_rows() -> dict[str, dict[str, str]]:
    header, rows = read_tsv_with_header(
        Path("docs/superpowers/validation/ARTIFACT_INVENTORY.tsv"),
        required_columns=REQUIRED_INVENTORY_COLUMNS,
    )
    assert header == REQUIRED_INVENTORY_COLUMNS
    return {row["path"]: row for row in rows}
```

- [ ] **Step 2: Run the new test and confirm it fails**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_validation_artifact_retention.py::test_readiness_integration_cell_provenance_is_minimal_fixture -v --tb=short
```

Expected: FAIL because the row is still `shrink_later`.

- [ ] **Step 3: Reclassify only the 3-line fixture row**

In `docs/superpowers/validation/ARTIFACT_INVENTORY.tsv`, update the row for:

```text
docs/superpowers/validation/quant_matrix_promotion_validation_packet_v1/readiness_integration_fixture/inputs/cell_provenance.tsv
```

Use these field values:

```text
category=tabular_contract
retention_decision=keep_minimal_fixture
keep_reason=synthetic readiness integration fixture with one detected and one accepted_backfill row
generated_by=scripts/build_quant_matrix_promotion_validation_packet.py --write-readiness-fixture
required_by=scripts/check_quant_matrix_promotion_readiness.py synthetic readiness contract
replacement_or_summary=
```

In `docs/superpowers/validation/RETENTION.md`, add one sentence under keep rules:

```markdown
- Synthetic fixture TSVs with only the rows needed to exercise readiness/checker branches are `keep_minimal_fixture`, not `shrink_later`.
```

- [ ] **Step 4: Verify Task 1**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_validation_artifact_retention.py::test_readiness_integration_cell_provenance_is_minimal_fixture -v --tb=short
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_validation_artifact_retention.py
```

Expected: pytest passes; retention checker reports `3 shrink_later` warnings.

## Task 2: Add QuantMatrix Summary And Golden-Slice Helpers

**Files:**
- Create: `xic_extractor/alignment/quant_matrix_fixture_contract.py`
- Test: `tests/test_quant_matrix_fixture_contract.py`

**Interfaces:**
- Consumes: full `cell_provenance.tsv` and `quant_matrix_review_rows.tsv`.
- Produces:
  - `write_cell_provenance_contract(full_tsv: Path, summary_json: Path, fixture_tsv: Path, *, source_relpath: str) -> None`
  - `write_review_rows_contract(full_tsv: Path, summary_json: Path, fixture_tsv: Path, *, source_relpath: str) -> None`
  - `validate_fixture_contract(summary_json: Path, fixture_tsv: Path) -> list[str]`

- [ ] **Step 1: Write tests for cell provenance summary counts**

Create `tests/test_quant_matrix_fixture_contract.py` with a fixture containing one detected and one accepted backfill row. Assert the summary contains:

```python
assert payload["schema_version"] == "quant_matrix_fixture_contract_v1"
assert payload["source_relpath"] == "quant_matrix_version/cell_provenance.tsv"
assert payload["source_row_count"] == 2
assert payload["source_sha256"]
assert payload["column_names"] == CELL_PROVENANCE_COLUMNS
assert payload["counts"]["cell_status"] == {"accepted_backfill": 1, "detected": 1}
assert payload["counts"]["write_authority"] == {"FALSE": 1, "TRUE": 1}
assert payload["counts"]["value_source"] == {
    "ProductionAcceptanceManifest": 1,
    "input_quant_matrix": 1,
}
assert payload["minimal_fixture"]["row_count"] == 2
assert payload["minimal_fixture"]["sha256"] == file_sha256(fixture_tsv)
```

Also assert:

```python
assert validate_fixture_contract(summary_json, fixture_tsv) == []
fixture_tsv.unlink()
assert any(
    "minimal fixture missing" in problem
    for problem in validate_fixture_contract(summary_json, fixture_tsv)
)
```

- [ ] **Step 2: Write tests for review-row summary counts**

Use a two-row review fixture and assert:

```python
assert payload["source_relpath"] == "review/quant_matrix_review_rows.tsv"
assert payload["counts"]["cell_status"] == {"accepted_backfill": 1, "detected": 1}
assert payload["counts"]["report_authority"] == {"review_only": 2}
assert payload["counts"]["truth_status"] == {"": 1, "not_truth_claimed": 1}
assert payload["counts"]["next_evidence_needed"] == {"": 2}
assert payload["row_universe"]["key_columns"] == [
    "peak_hypothesis_id",
    "sample_stem",
    "source_feature_family_ids",
    "cell_status",
]
assert payload["row_universe"]["row_count"] == 2
assert payload["row_universe"]["sha256"]
assert payload["minimal_fixture"]["row_count"] == 2
```

- [ ] **Step 3: Run tests and confirm they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_quant_matrix_fixture_contract.py -v --tb=short
```

Expected: FAIL because the module does not exist.

- [ ] **Step 4: Implement minimal helpers**

Implement `xic_extractor/alignment/quant_matrix_fixture_contract.py` using `read_tsv_required`, `write_tsv`, and `file_sha256`.

Required behavior:

- Read the full source TSV with the exact known columns.
- Count `cell_status`, `write_authority`, and `value_source` for cell provenance.
- Count `cell_status`, `report_authority`, `truth_status`, and `next_evidence_needed` for review rows.
- Select minimal fixture rows deterministically:
  - first `detected` row;
  - first `accepted_backfill` row;
  - if a class is absent, record it in `selection_warnings` and keep available rows only.
- Write the fixture TSV with original columns and original values.
- Write the summary JSON with source SHA, source row count, columns, counts, stable row-universe key columns, row-universe SHA, fixture row count, fixture SHA, selection rule, and `may_grant_product_authority=false`.
- `validate_fixture_contract()` must validate both sides of the replacement contract: summary JSON shape/counts and the minimal fixture file's existence, schema, row count, and SHA.

- [ ] **Step 5: Verify Task 2**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_quant_matrix_fixture_contract.py -v --tb=short
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/alignment/quant_matrix_fixture_contract.py tests/test_quant_matrix_fixture_contract.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

Expected: tests pass; ruff passes; mypy reports no issues.

## Task 3: Rewire Real Bundle To Emit Summaries And Stop Tracking Full Review Rows

**Files:**
- Modify: `scripts/build_quant_matrix_real_bundle.py`
- Modify: `docs/superpowers/validation/quant_matrix_real_bundle_v1/quant_matrix_real_bundle_summary.json`
- Add generated tracked outputs:
  - `docs/superpowers/validation/quant_matrix_real_bundle_v1/quant_matrix_version/cell_provenance_summary.json`
  - `docs/superpowers/validation/quant_matrix_real_bundle_v1/quant_matrix_version/cell_provenance_minimal_fixture.tsv`
  - `docs/superpowers/validation/quant_matrix_real_bundle_v1/review/quant_matrix_review_rows_summary.json`
  - `docs/superpowers/validation/quant_matrix_real_bundle_v1/review/quant_matrix_review_rows_minimal_fixture.tsv`
- Remove from git:
  - `docs/superpowers/validation/quant_matrix_real_bundle_v1/quant_matrix_version/cell_provenance.tsv`
  - `docs/superpowers/validation/quant_matrix_real_bundle_v1/review/quant_matrix_review_rows.tsv`
- Test: `tests/test_quant_matrix_real_bundle.py`

**Interfaces:**
- Consumes: helpers from Task 2.
- Produces: real-bundle check-only validation that binds full-result hashes through summaries and minimal fixtures.

- [ ] **Step 1: Add tests for summary/slice outputs**

In `tests/test_quant_matrix_real_bundle.py`, add assertions to the synthetic build test:

```python
summary = json.loads(outputs["summary_json"].read_text(encoding="utf-8"))
cell_contract = outputs["cell_provenance_summary_json"]
review_contract = outputs["review_rows_summary_json"]
assert cell_contract.is_file()
assert outputs["cell_provenance_minimal_fixture"].is_file()
assert review_contract.is_file()
assert outputs["review_rows_minimal_fixture"].is_file()
assert summary["artifacts"]["cell_provenance_summary"]["sha256"] == file_sha256(cell_contract)
assert summary["artifacts"]["review_rows_summary"]["sha256"] == file_sha256(review_contract)
assert summary["artifacts"]["cell_provenance"]["retention_decision"] == "externalize"
assert summary["artifacts"]["review_rows"]["retention_decision"] == "externalize"
```

Add a tamper test:

```python
payload = json.loads(
    outputs["cell_provenance_summary_json"].read_text(encoding="utf-8")
)
payload["source_row_count"] = 999
outputs["cell_provenance_summary_json"].write_text(
    json.dumps(payload) + "\n",
    encoding="utf-8",
)
problems = validate_quant_matrix_real_bundle(
    summary_json=outputs["summary_json"],
    repo_root=tmp_path,
    expected_source_run_id="synthetic-current-511-authority-replay",
    expected_downstream_scope="synthetic_current_authority_replay",
    expected_accepted_backfill_count=1,
)
assert any("cell_provenance summary" in problem for problem in problems)
```

Add missing/tampered minimal-fixture tests:

```python
outputs["cell_provenance_minimal_fixture"].unlink()
problems = validate_quant_matrix_real_bundle(
    summary_json=outputs["summary_json"],
    repo_root=tmp_path,
    expected_source_run_id="synthetic-current-511-authority-replay",
    expected_downstream_scope="synthetic_current_authority_replay",
    expected_accepted_backfill_count=1,
)
assert any("cell_provenance minimal fixture" in problem for problem in problems)

outputs = build_quant_matrix_real_bundle(
    source_run_dir=fixture["source_run"],
    output_dir=fixture["output_dir"],
    repo_root=tmp_path,
    downstream_scope="synthetic_current_authority_replay",
)
fixture_text = outputs["review_rows_minimal_fixture"].read_text(encoding="utf-8")
outputs["review_rows_minimal_fixture"].write_text(
    fixture_text.replace("review_only", "authority_changed", 1),
    encoding="utf-8",
)
problems = validate_quant_matrix_real_bundle(
    summary_json=outputs["summary_json"],
    repo_root=tmp_path,
    expected_source_run_id="synthetic-current-511-authority-replay",
    expected_downstream_scope="synthetic_current_authority_replay",
    expected_accepted_backfill_count=1,
)
assert any("review rows minimal fixture" in problem for problem in problems)
```

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_quant_matrix_real_bundle.py -v --tb=short
```

Expected: FAIL because the outputs are not wired yet.

- [ ] **Step 3: Wire builder outputs**

In `scripts/build_quant_matrix_real_bundle.py`:

- Import Task 2 helpers.
- After the existing `build_quant_matrix_review_report` call returns `review_outputs`, write cell provenance and review-row contracts.
- Add returned output keys:

```python
"cell_provenance_summary_json": cell_summary_json,
"cell_provenance_minimal_fixture": cell_fixture_tsv,
"review_rows_summary_json": review_rows_summary_json,
"review_rows_minimal_fixture": review_rows_fixture_tsv,
```

- In summary JSON, keep full source SHA and row count but mark full TSV retention as `externalize`; mark summaries and fixtures as `keep_summary` / `keep_minimal_fixture`.
- In validation, call `validate_fixture_contract()` for every summary/minimal-fixture pair. `validate_quant_matrix_real_bundle()` must fail when the tracked summary is stale, when a minimal fixture is missing, or when a minimal fixture no longer matches the summary SHA.
- For `review_rows_summary_json`, include `truth_status`, `next_evidence_needed`, source row count, source SHA, row-universe key columns, and row-universe SHA. The review-row replacement must preserve review/replay row identity at the summary level even though the full TSV is externalized.
- Preserve the existing local full TSV generation during build, but execution cleanup must move or copy any retained local full TSV under `local_validation_artifacts/externalized_superpowers_validation/<validation-relative-path>`.

- [ ] **Step 4: Regenerate real bundle without RAW**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_quant_matrix_real_bundle.py
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_quant_matrix_real_bundle.py --check-only
```

Expected: build passes; check-only passes; summaries and minimal fixture files are present.

- [ ] **Step 5: Remove tracked full real-bundle TSVs after replacement exists**

Run:

```powershell
git rm docs/superpowers/validation/quant_matrix_real_bundle_v1/quant_matrix_version/cell_provenance.tsv
git rm docs/superpowers/validation/quant_matrix_real_bundle_v1/review/quant_matrix_review_rows.tsv
```

Before removing, ensure the externalized local copies exist under:

```text
local_validation_artifacts/externalized_superpowers_validation/quant_matrix_real_bundle_v1/quant_matrix_version/cell_provenance.tsv
local_validation_artifacts/externalized_superpowers_validation/quant_matrix_real_bundle_v1/review/quant_matrix_review_rows.tsv
```

- [ ] **Step 6: Verify Task 3**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_quant_matrix_real_bundle.py -v --tb=short
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_validation_artifact_retention.py --require-externalized-local
```

Expected: tests pass; retention checker no longer warns for the two real-bundle full TSVs.

## Task 4: Rewire Default Product Activation Fixture Surface

**Files:**
- Modify: `scripts/build_quant_matrix_default_product_activation.py`
- Modify: `docs/superpowers/validation/quant_matrix_default_product_activation_v1/quant_matrix_default_product_activation_summary.json`
- Add generated tracked outputs:
  - `docs/superpowers/validation/quant_matrix_default_product_activation_v1/default_output/cell_provenance_summary.json`
  - `docs/superpowers/validation/quant_matrix_default_product_activation_v1/default_output/cell_provenance_minimal_fixture.tsv`
- Remove from git:
  - `docs/superpowers/validation/quant_matrix_default_product_activation_v1/default_output/cell_provenance.tsv`
- Test: `tests/test_quant_matrix_default_product_activation.py`

**Interfaces:**
- Consumes: Task 2 cell provenance summary helper.
- Produces: default activation check-only validation that preserves detected-only reconstruction evidence via summary/hash/slice instead of a tracked full provenance table.

- [ ] **Step 1: Add default activation tests**

In `tests/test_quant_matrix_default_product_activation.py`, assert the default activation summary records:

```python
assert summary["artifacts"]["cell_provenance"]["retention_decision"] == "externalize"
assert summary["artifacts"]["cell_provenance_summary"]["retention_decision"] == "keep_summary"
assert summary["artifacts"]["cell_provenance_minimal_fixture"]["retention_decision"] == "keep_minimal_fixture"
```

Add a tamper test for summary count mismatch and expect validation failure.

Also add missing/tampered minimal-fixture tests and require `validate_quant_matrix_default_product_activation()` to fail when `cell_provenance_minimal_fixture.tsv` is missing or no longer matches the summary SHA.

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_quant_matrix_default_product_activation.py -v --tb=short
```

Expected: FAIL because the default activation builder still expects the full tracked TSV.

- [ ] **Step 3: Wire default activation builder/checker**

In `scripts/build_quant_matrix_default_product_activation.py`:

- Use Task 2 helper to write the summary and fixture beside default outputs.
- Keep full `cell_provenance.tsv` as a local generated output during the build.
- Update `_cell_counts` and completeness validation to trust the generated full table during the build, but make check-only validate the tracked summary and minimal fixture through `validate_fixture_contract()`.
- Preserve `authority_statement` wording that accepted Backfill values are quantification values, not detections or truth claims.

- [ ] **Step 4: Regenerate and externalize**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_quant_matrix_default_product_activation.py
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_quant_matrix_default_product_activation.py --check-only
```

Move/copy the full generated TSV to:

```text
local_validation_artifacts/externalized_superpowers_validation/quant_matrix_default_product_activation_v1/default_output/cell_provenance.tsv
```

Then remove it from git:

```powershell
git rm docs/superpowers/validation/quant_matrix_default_product_activation_v1/default_output/cell_provenance.tsv
```

- [ ] **Step 5: Verify Task 4**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_quant_matrix_default_product_activation.py -v --tb=short
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_quant_matrix_default_product_activation.py --check-only
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_validation_artifact_retention.py --require-externalized-local
```

Expected: tests pass; default activation check-only passes; retention checker no longer warns for default activation full `cell_provenance.tsv`.

## Task 5: Update Inventory, Strict Gate, Productization State, And Handoff

**Files:**
- Modify: `docs/superpowers/validation/ARTIFACT_INVENTORY.tsv`
- Modify: `docs/superpowers/validation/RETENTION.md`
- Modify: `docs/superpowers/validation/productization_status_index_v1.tsv`
- Modify: `scripts/check_validation_artifact_retention.py`
- Modify: `tests/test_validation_artifact_retention.py`
- Modify: `tests/test_productization_state_index.py`
- Modify: `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md`
- Modify: `docs/superpowers/plans/2026-06-15-productization-control-plane.md` only if a maturity tier, active lane, public review/replay behavior, or matrix authority changed.

**Interfaces:**
- Consumes: outputs from Tasks 1-4.
- Produces: zero `shrink_later` rows and a strict retention gate.

- [ ] **Step 1: Add a strict-retention current-state test**

In `tests/test_validation_artifact_retention.py`, add:

```python
def test_current_validation_retention_inventory_is_strict_clean() -> None:
    result = check_validation_artifact_retention(strict=True)
    assert result.problems == ()
    assert result.summary["shrink_later_count"] == 0
```

- [ ] **Step 2: Run strict test and confirm it fails before inventory update**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_validation_artifact_retention.py::test_current_validation_retention_inventory_is_strict_clean -v --tb=short
```

Expected before completion: FAIL if any `shrink_later` row remains.

- [ ] **Step 3: Split tracked replacement and local externalized path fields**

Before changing retention decisions, migrate `ARTIFACT_INVENTORY.tsv` and `scripts/check_validation_artifact_retention.py` from the overloaded `replacement_or_summary` field to two explicit fields:

```text
tracked_replacement_or_summary
externalized_local_path
```

Rules:

- removed full TSV rows use `tracked_replacement_or_summary` for the tracked summary JSON or minimal fixture path;
- removed full TSV rows use `externalized_local_path` for the ignored local full TSV path;
- `--require-externalized-local` checks `externalized_local_path`;
- clean-checkout default checks use `tracked_replacement_or_summary`.

- [ ] **Step 4: Update inventory decisions**

For removed full TSV paths, set:

```text
retention_decision=externalize
tracked_replacement_or_summary=docs/superpowers/validation/<tracked summary json or minimal fixture path>
externalized_local_path=local_validation_artifacts/externalized_superpowers_validation/<validation-relative-path>
```

For new summary JSON files, set:

```text
category=summary_or_policy
retention_decision=keep_summary
```

For new minimal fixture TSV files, set:

```text
category=tabular_contract
retention_decision=keep_minimal_fixture
```

Ensure no inventory row uses `shrink_later`.

- [ ] **Step 5: Update status hashes**

Run the relevant builder check-only commands first, then:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py
```

If it fails on stale hashes, update `docs/superpowers/validation/productization_status_index_v1.tsv` to the new summary/check artifact hashes. Do not change maturity tier text unless the evidence level actually changed.

- [ ] **Step 6: Update handoff**

Rewrite `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md` as a current-state snapshot:

- retention checker strict mode is clean;
- `shrink_later_count=0`;
- full QuantMatrix provenance/review TSVs are local externalized artifacts;
- tracked replacement is summary/hash/minimal fixture;
- no RAW was run;
- no product matrix authority changed.

- [ ] **Step 7: Verify Task 5**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_validation_artifact_retention.py --strict --require-externalized-local
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_validation_artifact_retention.py tests/test_productization_state_index.py -v --tb=short
```

Expected: all pass, with `0 shrink_later`.

## Task 6: Final Focused Verification And Main-Agent Commit Readiness

**Files:**
- All files changed by Tasks 1-5.

**Interfaces:**
- Consumes: completed fixture cleanup.
- Produces: a verified diff that the main agent can stage and commit after explicit user approval.

- [ ] **Step 1: Run no-RAW fixture cleanup gates**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_validation_artifact_retention.py --strict --require-externalized-local
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_quant_matrix_real_bundle.py --check-only
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_quant_matrix_promotion_packet_v2.py --check-only
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_quant_matrix_default_product_activation.py --check-only
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_quant_matrix_fixture_contract.py tests/test_quant_matrix_real_bundle.py tests/test_quant_matrix_default_product_activation.py tests/test_quant_matrix_promotion_packet_v2.py tests/test_validation_artifact_retention.py tests/test_productization_state_index.py -v --tb=short
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/alignment/quant_matrix_fixture_contract.py scripts/build_quant_matrix_real_bundle.py scripts/build_quant_matrix_default_product_activation.py scripts/build_quant_matrix_promotion_validation_packet.py scripts/check_validation_artifact_retention.py tests/test_quant_matrix_fixture_contract.py tests/test_quant_matrix_real_bundle.py tests/test_quant_matrix_default_product_activation.py tests/test_quant_matrix_promotion_packet_v2.py tests/test_validation_artifact_retention.py tests/test_productization_state_index.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
git diff --check
```

Expected: all commands pass.

- [ ] **Step 2: Prepare main-agent diff summary**

Run without staging:

```powershell
git status --short --branch
git diff --stat
```

Expected: diff contains only the validation artifact fixture-retention scope. Staging, staged scans, and commit are main-agent/user-owned, not subagent-owned.

## Self-Review

- Spec coverage: all 4 current `shrink_later` rows are covered by Tasks 1, 3, and 4; strict checker/productization/handoff closeout is covered by Task 5.
- Placeholder scan: no forbidden placeholder markers are intentionally left.
- Type consistency: helper names from Task 2 are used consistently in Tasks 3 and 4.
- Boundary check: this plan is fixture-retention work only. It must not change selected peak/area/counting, ProductWriter behavior, workbook schema, or matrix authority.
