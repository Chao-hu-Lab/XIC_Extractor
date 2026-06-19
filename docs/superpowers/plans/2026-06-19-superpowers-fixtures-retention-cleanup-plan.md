# Superpowers Fixtures Retention Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan one task at a time. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `docs/superpowers/fixtures/` a clearly classified contract/manual-oracle/diagnostic-ledger fixture surface, with an inventory and checker that prevent active product fixtures and historical diagnostic snapshots from being confused.

**Architecture:** Keep active fixtures in git when they are manual oracles, expected-diff contracts, schema fixtures, or check inputs. Keep dated diagnostic-ledger snapshots only when they are explicitly referenced by the ledger and have a source/hash story. Run the hash/duplicate audit before moving or reclassifying snapshots, because ledger-era files may have stale embedded hashes or duplicate bodies. Do not move active fixture paths unless every tool/test/spec reference is updated in the same task.

**Tech Stack:** Python 3.13, `uv`, `pytest`, `ruff`, `mypy`, `xic_extractor.tabular_io`, existing `docs/diagnostic-ledger.md` references, existing fixture-consuming tests and diagnostic tools.

## Global Constraints

- Worktree/branch: repo root worktree, branch `cc/framework-improvements`.
- Scope is `docs/superpowers/fixtures/`; do not edit `docs/superpowers/validation/` under this plan except for explicit cross-reference notes if a later review requires them.
- Do not run RAW or 85RAW.
- Do not change ProductWriter/default extraction/workbook/GUI/selected peak/area/counting/Backfill authority/matrix semantics.
- Do not change active fixture paths that are consumed by tests, tools, specs, or validation artifacts unless the same task updates all references and focused tests prove the path migration.
- Dated diagnostic-ledger snapshots are evidence archives, not active product authority.
- If execution changes a maturity tier, active lane, output schema, review/replay behavior, selected area/counting, or matrix authority, update `docs/superpowers/plans/2026-06-15-productization-control-plane.md` and the current handoff. If it stays fixture-retention-only, state explicitly that no tier update is needed.

---

## Preflight Contract

Goal: classify and guard `docs/superpowers/fixtures/` without moving product behavior.
Existing owner/helper to reuse: `xic_extractor.tabular_io`, `docs/diagnostic-ledger.md`, existing fixture-consuming tests and diagnostic CLIs.
New code location: `scripts/check_superpowers_fixture_retention.py` and `tests/test_superpowers_fixture_retention.py`.
Evidence provider role: none. This is fixture-retention and review-surface cleanup only.
Simplest product rule: active fixtures are durable oracles/contracts; dated ledger snapshots are archived evidence; generated dumps need a summary/index or a specific human-reviewed reason to stay.
Call-cost model: no RAW calls; no scorer calls; only git path enumeration, TSV/CSV/JSON/Markdown metadata reads, and text reference checks.
Public contracts at risk: fixture paths consumed by tests/tools/specs, diagnostic-ledger references, and validation artifacts that cite manual negative fixtures.
Validation gate: fixture retention checker, existing fixture-consuming tests, targeted docs reference checks, `git diff --check`, and diff credential/local-path scan before commit.
Stop rule: if a fixture path is consumed by code/tests/specs and cannot be migrated safely with focused coverage, keep the path and only classify/index it.

## Current Surface Map

`docs/superpowers/fixtures/` currently has `25` tracked files:

- Root active fixtures: `9` files, including shared-peak identity manual oracle/contracts, target-pair manual oracle, selected-envelope manual review fixture, targeted NL-fail expected diff, selected-envelope manifest, and alignment schema fixture.
- Dated diagnostic-ledger snapshots: `16` files under `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/`.
- File types: `19` TSV, `3` CSV, `2` Markdown, `1` JSON.
- Size profile: no current file is large by validation-retention standards; the largest files are `phase1b_85raw_policy_delta.tsv` at about `46 KB / 97 lines` and `phase1b_8raw_policy_delta.tsv` at about `40 KB / 81 lines`.

## Files

- Create: `docs/superpowers/fixtures/RETENTION.md`
- Create: `docs/superpowers/fixtures/README.md`
- Create: `docs/superpowers/fixtures/ARTIFACT_INVENTORY.tsv`
- Create: `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/README.md`
- Create: `scripts/check_superpowers_fixture_retention.py`
- Create: `tests/test_superpowers_fixture_retention.py`
- Modify: `docs/project-layout.md`
- Modify: `docs/diagnostic-ledger.md` only to link the fixture inventory/dated snapshot README; do not rewrite ledger conclusions.
- Modify: `docs/superpowers/plans/2026-06-15-productization-control-plane.md` only if a maturity tier or active lane changes.
- Modify: `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md` only if the current-state snapshot needs to mention the fixture-retention gate.

## Retention Decisions

Use these decisions in `docs/superpowers/fixtures/ARTIFACT_INVENTORY.tsv`:

- `keep_contract`: active schema, expected-diff, activation, or mode-window contract consumed by tools/tests/specs.
- `keep_manual_oracle`: human-reviewed oracle or manual negative fixture that must remain stable for review and validation.
- `keep_manifest`: short manifest or lock file.
- `keep_ledger_snapshot`: dated diagnostic-ledger evidence snapshot referenced by `docs/diagnostic-ledger.md` or a dated packet README, with a current SHA recorded in inventory.
- `keep_summary`: short summary or README explaining a fixture group.
- `needs_human_review`: retained temporarily because it looks like a manual oracle, but lacks a direct checker/test consumer or a clear owner decision.
- `archive_later`: retained temporarily, but needs a later move/summary after references are rewritten or duplicate/hash drift is resolved.
- `externalize`: not expected for current files; use only if a future full generated dump appears.
- `remove_generated`: not expected for current files; use only when the file is reproducible, unreferenced, and not a human oracle or ledger snapshot.

## Task 0: Hash And Duplicate Audit

**Files:**
- Read: `docs/superpowers/fixtures/**`
- Read: `docs/diagnostic-ledger.md`
- Output during execution: notes folded into `docs/superpowers/fixtures/ARTIFACT_INVENTORY.tsv` and dated README, not a separate generated dump.

**Interfaces:**
- Consumes: current fixture bytes, any embedded SHA references in `docs/diagnostic-ledger.md`, and direct fixture path references.
- Produces: the evidence needed to classify duplicate snapshots, stale-hash rows, and weak manual oracles without guessing.

- [ ] **Step 1: Compute fixture hashes and duplicate groups**

Run:

```powershell
git ls-files docs/superpowers/fixtures | ForEach-Object {
  $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $_).Hash.ToLowerInvariant()
  "$hash`t$_"
}
```

Record duplicate groups in the inventory `next_action` column using `duplicate_of=<path>` for the duplicate row that should eventually be archived.

- [ ] **Step 2: Compare embedded ledger hashes**

Search for fixture paths and SHA-looking tokens:

```powershell
rg -n "docs/superpowers/fixtures|sha256|SHA256|hash" docs/diagnostic-ledger.md docs/superpowers/notes docs/superpowers/plans
```

If an embedded hash differs from the current file hash, do not silently overwrite the old ledger claim. Record the current SHA in inventory and add a dated README note such as `hash_drift_observed=<old_or_referenced_hash>` / `current_sha256=<current_hash>`.

- [ ] **Step 3: Confirm direct consumers**

Run:

```powershell
rg -n "docs/superpowers/fixtures|shared_peak_identity_manual_oracle_v1|alignment_cell_integration_audit_current_asls_schema|target_pair_chrom_morphology_area_ratio_manual_oracle|chrom_peak_segment_presence_review_manual_oracle|phase1b_.*policy_delta" tests tools scripts docs
```

Use direct test/tool/script consumers to distinguish active fixtures from note-only snapshots.

## Task 1: Add Fixture Retention Policy And Inventory

**Files:**
- Create: `docs/superpowers/fixtures/RETENTION.md`
- Create: `docs/superpowers/fixtures/README.md`
- Create: `docs/superpowers/fixtures/ARTIFACT_INVENTORY.tsv`
- Test: none yet; Task 2 adds checker tests.

**Interfaces:**
- Consumes: current tracked paths under `docs/superpowers/fixtures/`.
- Produces: one explicit decision row per fixture file.

- [ ] **Step 1: Create `RETENTION.md`**

Write a concise policy with these sections:

```markdown
# Superpowers Fixture Retention Policy

Status: living policy for `docs/superpowers/fixtures`.
Scope: durable fixtures, manual oracles, expected-diff contracts, schema fixtures, and dated diagnostic-ledger snapshots.

## Keep In Git

- Manual oracle rows reviewed by a human.
- Expected-diff and activation contracts consumed by tools or tests.
- Schema fixtures that lock writer/checker columns.
- Dated diagnostic-ledger snapshots that are referenced by `docs/diagnostic-ledger.md`.
- Small manifests and group README files.

## Do Not Add By Default

- Full generated output dumps that are not human-reviewed fixtures.
- Recomputed diagnostic outputs without a ledger note, source command, or hash.
- Duplicate copies when a source fixture plus summary is enough.

## Product Boundary

Fixture retention cleanup must not change ProductWriter behavior, selected peak/area, counted detections, workbook/GUI behavior, Backfill authority, matrix values, or maturity tier claims.
```

- [ ] **Step 2: Create root fixture README**

Create `docs/superpowers/fixtures/README.md` as the lightweight landing page. It must link to:

- `RETENTION.md`
- `ARTIFACT_INVENTORY.tsv`
- `diagnostic_ledger_2026_05_28/README.md`

It must state that `docs/superpowers/fixtures/` is not a generated result dump and that new files need an inventory row, SHA, owner scope, and retention decision. `ARTIFACT_INVENTORY.tsv` is the one self-index exception and is checked by schema, not by a self-hash row.

- [ ] **Step 3: Create inventory header**

Create `ARTIFACT_INVENTORY.tsv` with this exact header:

```text
path	size_bytes	line_count	sha256	category	retention_decision	authority_scope	referenced_by	keep_reason	next_action
```

- [ ] **Step 4: Classify root active fixtures**

Use these starting classifications:

```text
docs/superpowers/fixtures/shared_peak_identity_manual_oracle_v1.tsv	manual_oracle	keep_manual_oracle	shared_peak_identity
docs/superpowers/fixtures/shared_peak_identity_mode_window_assignment_contract_v0.tsv	contract_fixture	keep_contract	shared_peak_identity
docs/superpowers/fixtures/shared_peak_identity_activation_must_not_regress_v1.tsv	contract_fixture	keep_contract	shared_peak_identity
docs/superpowers/fixtures/target_pair_chrom_morphology_area_ratio_manual_oracle_v1.tsv	manual_oracle	keep_manual_oracle	lockbox_manual_negative
docs/superpowers/fixtures/chrom_peak_segment_presence_review_manual_oracle_v1.tsv	manual_oracle	needs_human_review	chrom_peak_segment
docs/superpowers/fixtures/selected_envelope_manual_boundary_review_gaussian15_peak_group_20260605.tsv	manual_oracle	keep_manual_oracle	selected_envelope
docs/superpowers/fixtures/targeted_nl_fail_own_max_gate_expected_diff_v0.tsv	expected_diff_contract	keep_contract	targeted_nl_fail_gate
docs/superpowers/fixtures/selected_full_envelope_fe4_preflight_manifest.json	manifest	keep_manifest	selected_envelope
docs/superpowers/fixtures/alignment_cell_integration_audit_current_asls_schema.tsv	schema_fixture	keep_contract	alignment_writer_schema
```

Fill `size_bytes`, `line_count`, `sha256`, `referenced_by`, `keep_reason`, and `next_action` from the current worktree. Do not add a self-row for `docs/superpowers/fixtures/ARTIFACT_INVENTORY.tsv`. For `needs_human_review`, set `next_action` to either `add_consumer_test`, `promote_to_keep_manual_oracle`, or `archive_later_after_owner_review`.

- [ ] **Step 5: Classify dated diagnostic-ledger snapshots**

For files under `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/`, start from:

```text
category=diagnostic_ledger_snapshot
retention_decision=keep_ledger_snapshot
authority_scope=diagnostic_ledger_2026_05_28
```

The `referenced_by` column must mention `docs/diagnostic-ledger.md` when that file contains the path or group reference.

Use these special decisions from Task 0:

- `phase1b_8raw_policy_delta.tsv` and `phase1b_85raw_policy_delta.tsv`: use `archive_later` unless a direct checker/test consumer exists; these are policy-delta dumps, not active product fixtures.
- Duplicate file pairs, such as identical review-row triage snapshots or identical 5medC comparison CSVs: keep the canonical path as `keep_ledger_snapshot`, mark the duplicate as `archive_later`, and record `duplicate_of=<canonical_path>` in `next_action`.
- Files with observed hash drift: keep the current file hash in `sha256`, record the referenced stale hash in `next_action`, and explain the mismatch in the dated packet README.

- [ ] **Step 6: Verify inventory row count manually**

Run:

```powershell
git ls-files docs/superpowers/fixtures; git ls-files --others --exclude-standard docs/superpowers/fixtures
Import-Csv docs/superpowers/fixtures/ARTIFACT_INVENTORY.tsv -Delimiter "`t" | Measure-Object
```

Expected: inventory row count equals the checker candidate count: tracked fixture files plus newly created, nonignored policy/README files, excluding `docs/superpowers/fixtures/ARTIFACT_INVENTORY.tsv`.

## Task 2: Add Fixture Retention Checker

**Files:**
- Create: `scripts/check_superpowers_fixture_retention.py`
- Create: `tests/test_superpowers_fixture_retention.py`

**Interfaces:**
- Consumes: `docs/superpowers/fixtures/RETENTION.md`, `ARTIFACT_INVENTORY.tsv`, `git ls-files docs/superpowers/fixtures`, and selected text references.
- Produces: a local gate that fails on missing inventory rows, invalid decisions, generated dumps without explicit retention, and active fixtures lacking references.

- [ ] **Step 1: Write tests first**

Create `tests/test_superpowers_fixture_retention.py` with tests for:

- `test_current_superpowers_fixture_inventory_accepts_worktree`
- `test_checker_rejects_missing_inventory_row`
- `test_checker_rejects_invalid_retention_decision`
- `test_checker_rejects_sha256_mismatch`
- `test_checker_requires_ledger_reference_for_ledger_snapshot`
- `test_checker_requires_active_fixture_reference`
- `test_checker_rejects_large_generated_dump_without_policy_reason`

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_superpowers_fixture_retention.py -v --tb=short
```

Expected: FAIL because the checker does not exist.

- [ ] **Step 3: Implement checker**

Implement `scripts/check_superpowers_fixture_retention.py` with:

- required inventory columns from Task 1, including `sha256`;
- allowed decisions parsed from `RETENTION.md`;
- git candidate enumeration from tracked and untracked fixture paths, excluding `ARTIFACT_INVENTORY.tsv` to avoid self-hash churn;
- fail on missing inventory rows;
- fail on invalid decision;
- fail on current SHA mismatch for any inventory row whose file exists;
- fail when `diagnostic_ledger_snapshot` rows do not have `keep_ledger_snapshot`;
- fail when `keep_ledger_snapshot` rows lack a `docs/diagnostic-ledger.md` reference or explicit dated-ledger group README reference;
- fail when active root fixtures lack `referenced_by`;
- warn, or fail in `--strict`, when a row is `needs_human_review`;
- warn, or fail in `--strict`, when a fixture above `100 KB` is not a manual oracle, contract, manifest, summary, or ledger snapshot with a keep reason.

- [ ] **Step 4: Verify Task 2**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_superpowers_fixture_retention.py -v --tb=short
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_superpowers_fixture_retention.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts/check_superpowers_fixture_retention.py tests/test_superpowers_fixture_retention.py
```

Expected: all pass.

## Task 3: Add Diagnostic Ledger Snapshot README

**Files:**
- Create: `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/README.md`
- Modify: `docs/diagnostic-ledger.md`
- Modify: `docs/superpowers/fixtures/ARTIFACT_INVENTORY.tsv`
- Modify: `docs/superpowers/fixtures/README.md`
- Test: `tests/test_superpowers_fixture_retention.py`

**Interfaces:**
- Consumes: dated snapshots already present.
- Produces: a compact group-level explanation so the directory does not look like loose generated output.

- [ ] **Step 1: Create group README**

The README must state:

- this is a frozen diagnostic-ledger evidence packet from 2026-05-28;
- it is not an active product fixture;
- files are retained because `docs/diagnostic-ledger.md` cites the packet or individual paths;
- current SHA values are authoritative in `ARTIFACT_INVENTORY.tsv`;
- hash drift or duplicate observations from Task 0 are called out without rewriting historical ledger conclusions;
- rerunning diagnostics should produce new output outside this dated snapshot unless a new ledger entry promotes it.

- [ ] **Step 2: Link README from diagnostic ledger**

Add one short line near the existing 2026-05-28 fixture table in `docs/diagnostic-ledger.md`:

```markdown
The fixture packet is indexed at `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/README.md`.
```

Do not rewrite ledger conclusions. If Task 0 found a stale embedded hash, add a short note that the current inventory records the present file SHA and the dated README records the drift.

- [ ] **Step 3: Update inventory**

Add the root README and dated README rows as:

```text
category=summary_or_policy
retention_decision=keep_summary
authority_scope=diagnostic_ledger_2026_05_28
```

- [ ] **Step 4: Verify Task 3**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_superpowers_fixture_retention.py
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_superpowers_fixture_retention.py -v --tb=short
```

Expected: checker and tests pass.

## Task 4: Add Existing Fixture Consumer Guardrails

**Files:**
- Modify: `tests/test_superpowers_fixture_retention.py`
- Existing tests to run:
  - `tests/test_shared_peak_identity_oracle.py`
  - `tests/test_shared_peak_identity_classifier.py`
  - `tests/test_shared_peak_identity_assembler.py`
  - `tests/test_shared_peak_identity_schema.py`
  - `tests/test_alignment_tsv_writer.py`

**Interfaces:**
- Consumes: inventory decisions from Task 1.
- Produces: a guard that active fixture paths remain stable unless references are intentionally migrated.

- [ ] **Step 1: Add active path guard test**

In `tests/test_superpowers_fixture_retention.py`, add a test that asserts these paths are present in inventory and on disk:

```python
ACTIVE_FIXTURE_PATHS = {
    "docs/superpowers/fixtures/shared_peak_identity_manual_oracle_v1.tsv",
    "docs/superpowers/fixtures/shared_peak_identity_mode_window_assignment_contract_v0.tsv",
    "docs/superpowers/fixtures/shared_peak_identity_activation_must_not_regress_v1.tsv",
    "docs/superpowers/fixtures/target_pair_chrom_morphology_area_ratio_manual_oracle_v1.tsv",
    "docs/superpowers/fixtures/targeted_nl_fail_own_max_gate_expected_diff_v0.tsv",
    "docs/superpowers/fixtures/alignment_cell_integration_audit_current_asls_schema.tsv",
}
```

For each active path, assert:

```python
assert path.exists()
assert inventory[path.as_posix()]["retention_decision"] in {
    "keep_contract",
    "keep_manual_oracle",
    "keep_manifest",
}
```

- [ ] **Step 2: Run consumer tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_superpowers_fixture_retention.py tests/test_shared_peak_identity_oracle.py tests/test_shared_peak_identity_classifier.py tests/test_shared_peak_identity_assembler.py tests/test_shared_peak_identity_schema.py tests/test_alignment_tsv_writer.py -v --tb=short
```

Expected: all pass. If `tests/test_alignment_tsv_writer.py` is too broad, rerun the specific test that checks `alignment_cell_integration_audit_current_asls_schema.tsv`.

## Task 5: Project Layout And Handoff Update

**Files:**
- Modify: `docs/project-layout.md`
- Modify: `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md`
- Modify: `docs/superpowers/plans/2026-06-15-productization-control-plane.md` only if execution changes tier/active lane.

**Interfaces:**
- Consumes: checker and inventory from Tasks 1-4.
- Produces: durable guidance so future agents know the difference between `docs/superpowers/fixtures/` and `docs/superpowers/validation/`.

- [ ] **Step 1: Update project layout**

Add or tighten the `docs/superpowers/fixtures/` entry:

```markdown
| `docs/superpowers/fixtures/` | Durable manual oracles, expected-diff contracts, schema fixtures, and dated diagnostic-ledger snapshots. Not a generated output dump; new files require `ARTIFACT_INVENTORY.tsv` classification. |
```

- [ ] **Step 2: Update current handoff if needed**

If this cleanup is executed on the active branch, add a short current-state section:

- fixture retention checker exists;
- active fixtures remain in place;
- diagnostic ledger snapshots are indexed;
- no RAW run;
- no product authority or maturity tier change.

- [ ] **Step 3: Control-plane decision**

If the work remains policy/index/checker-only, do not edit control-plane tiers. In closeout, explicitly state:

```text
No control-plane tier update is needed because this does not change maturity tier, active lane, output schema, selected area/counting, review/replay behavior, or matrix authority.
```

## Task 6: Final Verification And Main-Agent Commit Readiness

**Files:**
- All files changed by Tasks 1-5.

**Interfaces:**
- Consumes: completed fixture-retention cleanup.
- Produces: a verified diff that the main agent can stage and commit after explicit user approval.

- [ ] **Step 1: Run no-RAW fixture gates**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_superpowers_fixture_retention.py
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_superpowers_fixture_retention.py tests/test_shared_peak_identity_oracle.py tests/test_shared_peak_identity_classifier.py tests/test_shared_peak_identity_assembler.py tests/test_shared_peak_identity_schema.py tests/test_alignment_tsv_writer.py -v --tb=short
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts/check_superpowers_fixture_retention.py tests/test_superpowers_fixture_retention.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
git diff --check
```

Expected: all pass.

- [ ] **Step 2: Prepare main-agent diff summary and scan working diff**

Run without staging:

```powershell
git status --short --branch
git diff --stat
$pattern = '^\+.*(?i)(' + 'sk' + '-[A-Za-z0-9]|api' + '[_-]?key|pass' + 'word|to' + 'ken|sec' + 'ret|[A-Za-z]:[\\/])'
git diff --unified=0 -- . | Select-String -Pattern $pattern
```

Expected: diff contains only the fixture-retention scope and no credential/local-path matches. Staging and commit are main-agent/user-owned, not subagent-owned.

## Self-Review

- Spec coverage: the plan covers root active fixtures, dated diagnostic-ledger snapshots, policy/index/checker, existing consumer tests, and closeout docs.
- Boundary check: this plan must not edit validation artifact shrink work except for deliberate cross-reference wording.
- Product safety: no ProductWriter behavior, selected values, counted detections, workbook schema, GUI behavior, or matrix authority changes are allowed.
