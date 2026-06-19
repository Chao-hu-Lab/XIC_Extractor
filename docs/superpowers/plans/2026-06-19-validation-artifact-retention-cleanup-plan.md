# Validation Artifact Retention Cleanup Implementation Plan

> **For agentic workers:** Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` when available. If those skills are unavailable, execute this checklist directly and keep the same read-before-edit, review, verification, and commit-splitting rules. Steps use checkbox (`- [ ]`) syntax for tracking.

`docs/superpowers/validation/RETENTION.md` is the canonical ongoing retention policy. This plan is the one-time execution handoff for cleaning the current branch and must not redefine long-term policy by duplicating it.

**Goal:** Make `docs/superpowers/validation/` a small, reviewable, version-controlled evidence index instead of a generated result dump, without changing product extraction, ProductWriter output, selected peaks/areas, counted detections, Backfill authority, GUI behavior, or default matrix semantics.

**Architecture:** Keep authoritative contracts, source manifests, hashes, minimal fixtures, and human decision summaries in git. Move rendered HTML/PNG bundles, full row dumps, duplicated input copies, and bulky review work products to ignored local storage under `local_validation_artifacts/externalized_superpowers_validation/`, with tracked summaries that record row counts, hashes, source paths, regeneration commands, and retention decisions.

**Tech Stack:** Python scripts under `scripts/`, focused pytest coverage under `tests/`, TSV/JSON/Markdown artifacts under `docs/superpowers/validation/`, ignored local artifacts under `local_validation_artifacts/`, and existing productization checkers.

## Global Constraints

- Do not change ProductWriter, default extraction, workbook schemas, GUI behavior, selected peak/area logic, counted detection logic, alignment semantics, Backfill authority, or matrix write authority.
- Do not remove or externalize a file that is the only source for a contract, case universe, label template, reviewer decision, status index, productization checker input, or public output expected-diff until the replacement contract and tests are in place.
- Do not create a second independent case manifest. `docs/superpowers/validation/lockbox_shadow_automation_cases_v1.tsv` remains the single 72-case source.
- Do not run RAW/85RAW. This cleanup is metadata, file-retention, and checker work only.
- Every externalized artifact must have a tracked pointer or summary with enough information to regenerate or verify it locally.
- Clean checkout must pass productization/check-only tests without requiring ignored rendered artifacts, unless a command explicitly opts into `--require-rendered-local`.
- Tracked rows must not point at externalized or deleted rendered HTML/PNG as if those files still exist in git. Such references must either become local externalized paths or be explicitly marked as historical/source references with a replacement mapping.
- Commit by purpose:
  1. policy/inventory/current rendered deletion,
  2. retention checker and tests,
  3. lockbox generator path split,
  4. quant-matrix shrink slices,
  5. docs/handoff/control-plane closeout.

## Preflight Contract

- **Owner/helper reuse:** Reuse existing builder/checker scripts and `xic_extractor/tabular_io.py` for TSV/hash-style helpers when needed. Prefer small script-local logic if the rule is retention-only and not domain logic.
- **New code location:** Add a retention checker at `scripts/check_validation_artifact_retention.py` and focused tests at `tests/test_validation_artifact_retention.py`. Do not move domain evidence logic into docs or diagnostics writers.
- **Evidence role:** Retention artifacts prove observability and reproducibility only. They do not grant product authority, truth authority, write authority, or reviewer-slot satisfaction.
- **Simplest rule:** Tracked validation files are contracts, summaries, indexes, hashes, minimal fixtures, and living docs. Generated renders and full run dumps are local artifacts by default.
- **Call-cost model:** Use `git ls-files`, file sizes, extension/type checks, and targeted TSV reads. No RAW scans, scorer runs, or large-data recomputation.
- **Public contracts at risk:** Validation script default output paths, productization status index artifact hashes, lockbox bundle path fields, quant-matrix expected-diff fixtures, and handoff/control-plane wording.
- **Validation gate:** Retention checker, productization state checker, lockbox label schema checker, focused pytest, script check-only modes, `git diff --check`, and a credential/local-path scan for tracked summaries.
- **Stop rule:** If a candidate artifact is referenced by `productization_status_index_v1.tsv`, a checker default, or a test fixture, first update that reference and add focused coverage. If the replacement cannot be verified without RAW or scorer execution, leave the artifact as `shrink_later`.

---

## Phase 0: Freeze Current Cleanup And Classify The Surface

**Purpose:** Preserve the user's current cleanup direction and make the remaining review burden measurable before deleting more.

- [ ] Inspect dirty scope without reverting user work:
  - `git status --short --branch`
  - `git diff --stat -- docs/superpowers/validation docs/superpowers/handoffs/current/cc-framework-improvements-productization.md docs/superpowers/plans/2026-06-15-productization-control-plane.md`
- [ ] Review current retention docs:
  - `docs/superpowers/validation/RETENTION.md`
  - `docs/superpowers/validation/ARTIFACT_INVENTORY.tsv`
  - `docs/superpowers/validation/lockbox_static_review_v1/README.md`
- [ ] Confirm the first cleanup wave only removes rendered review outputs:
  - `docs/superpowers/validation/lockbox_static_review_v1/index.html`
  - `docs/superpowers/validation/lockbox_static_review_v1/cases/*.html`
  - `docs/superpowers/validation/lockbox_static_review_v1/plots/*.png`
  - `docs/superpowers/validation/lockbox_ai_challenge_v1/index.html`
  - `docs/superpowers/validation/lockbox_second_review_v1/index.html`
- [ ] Verify externalized local copies exist under:
  - `local_validation_artifacts/externalized_superpowers_validation/lockbox_static_review_v1/`
  - `local_validation_artifacts/externalized_superpowers_validation/lockbox_ai_challenge_v1/`
  - `local_validation_artifacts/externalized_superpowers_validation/lockbox_second_review_v1/`
- [ ] Audit tracked TSV/JSON/Markdown rows that still mention externalized or deleted rendered paths:
  - `docs/superpowers/validation/**/*.html`
  - `docs/superpowers/validation/**/*.png`
- [ ] For every stale rendered path reference, choose one explicit contract in the same commit:
  - active local path under `local_validation_artifacts/externalized_superpowers_validation/...`;
  - stable rendered artifact ID plus README/inventory replacement mapping;
  - historical/source path clearly labeled as not expected to exist on a clean checkout.
- [ ] Produce a current tracked-artifact size report from `git ls-files docs/superpowers/validation`:
  - total tracked size,
  - count by extension,
  - top 30 largest files,
  - top directories by bytes.
- [ ] Update `ARTIFACT_INVENTORY.tsv` so every remaining tracked file has one of:
  - `keep_contract`
  - `keep_summary`
  - `keep_minimal_fixture`
  - `shrink_later`
  - `externalize`
  - `delete_generated`
- [ ] Do not delete `shrink_later` files in this phase.

**Acceptance:**

- The current cleanup wave is documented and reviewable.
- No product output or checker dependency is silently removed.
- Remaining large files are explicitly named and classified.
- Clean-checkout contract files do not contain unresolved active links to deleted/externalized rendered HTML/PNG.

**Verification:**

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_lockbox_label_schema.py
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_lockbox_label_collection_pack.py tests/test_productization_state_index.py -v --tb=short
git diff --check
```

---

## Phase 1: Add A Retention Checker Before More Deletions

**Purpose:** Prevent the same design problem from returning after cleanup.

- [ ] Add `scripts/check_validation_artifact_retention.py`.
- [ ] The checker must read `docs/superpowers/validation/ARTIFACT_INVENTORY.tsv` and inspect `git ls-files docs/superpowers/validation`.
- [ ] Make the policy inventory-driven instead of filename-exception-driven. Required inventory columns:
  - `path`
  - `size_bytes`
  - `line_count`
  - `category`
  - `retention_decision`
  - `keep_reason`
  - `generated_by`
  - `required_by`
  - `replacement_or_summary`
- [ ] The checker must fail when a tracked file is missing from the inventory.
- [ ] The checker must fail when a tracked file is classified as `externalize` or `delete_generated`.
- [ ] The checker must fail when `retention_decision` is not one of the decisions in `RETENTION.md`.
- [ ] The checker must fail for tracked generated/rendered categories by default, based on `category` plus extension:
  - rendered HTML review/report files,
  - PNG or other binary review media,
  - duplicated generated input copies marked for externalization.
- [ ] The checker may allow small Markdown docs, JSON summaries, TSV manifests, and explicit minimal fixtures when the inventory row explains why.
- [ ] Add a size policy:
  - files above a configured threshold, for example 500 KB, require `keep_contract`, `keep_minimal_fixture`, or `shrink_later` plus a non-empty reason/source field.
  - `shrink_later` is allowed temporarily but reported in the checker summary.
- [ ] Add a stale rendered-path policy:
  - tracked TSV/JSON/Markdown may mention externalized rendered HTML/PNG only when the row/README/inventory also records the replacement mapping or marks the path as historical;
  - active clean-checkout checks must not require ignored rendered files unless `--require-externalized-local` is passed.
- [ ] Add optional flags:
  - `--strict` fails on `shrink_later`;
  - `--json-out <path>` writes machine-readable summary;
  - `--require-externalized-local` verifies local externalized copies where inventory records them.
- [ ] Add `tests/test_validation_artifact_retention.py` with fixture inventories covering:
  - missing inventory row,
  - forbidden tracked PNG,
  - forbidden tracked rendered HTML,
  - allowed contract TSV,
  - allowed summary Markdown,
  - large `shrink_later` warning,
  - strict-mode failure on `shrink_later`,
  - stale rendered path without replacement mapping,
  - allowed historical rendered path with replacement mapping.
- [ ] Keep the checker independent of RAW/scorer/product runs.

**Acceptance:**

- A fresh PR cannot accidentally add generated validation dumps under `docs/superpowers/validation/` without an explicit inventory decision.
- The checker reports remaining debt instead of hiding it.

**Verification:**

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_validation_artifact_retention.py
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_validation_artifact_retention.py -v --tb=short
git diff --check
```

---

## Phase 2: Split Lockbox Contract Outputs From Rendered Review Outputs

**Purpose:** Fix the generator defaults that created tracked rendered artifacts in the first place.

- [ ] Treat this as a public contract migration because `scripts/` CLI defaults, check-only behavior, `bundle_index.tsv` path fields, and summary hashes are public surfaces.
- [ ] Before changing defaults, map current callers and tests:
  - `scripts/import_lockbox_labels.py`
  - `scripts/build_lockbox_ai_challenge_pack.py`
  - `scripts/build_lockbox_second_review_pack.py`
  - `tests/test_lockbox_static_review_bundle.py`
  - lockbox productization/status tests that hash bundle paths.
- [ ] Keep existing public flags as backward-compatible aliases where possible:
  - `--output-dir` remains accepted for legacy full rendered output;
  - new split flags should be additive unless the same commit updates every caller/test/doc that used the old meaning.
- [ ] Update `scripts/build_lockbox_static_review_bundle.py` so tracked contract/index output and rendered output are separate:
  - tracked contract dir default: `docs/superpowers/validation/lockbox_static_review_v1/`
  - rendered dir default: `local_validation_artifacts/externalized_superpowers_validation/lockbox_static_review_v1/`
- [ ] Keep `bundle_index.tsv` tracked if it is used by label import/checkers.
- [ ] Decide and document one path contract for rendered links before changing rows:
  - Preferred: `bundle_index.tsv` records externalized local paths under `local_validation_artifacts/...`.
  - Alternative: `bundle_index.tsv` records stable relative artifact IDs and the README documents how to map them to the local rendered dir.
- [ ] If summary JSON hashes currently include rendered HTML text hashes, preserve the audit intent by recording generated-text SHA in the tracked summary without requiring the rendered file to exist in git.
- [ ] Update `scripts/build_lockbox_ai_challenge_pack.py`:
  - challenge queue/template/contract files remain tracked;
  - rendered `index.html` defaults to ignored local externalized storage.
- [ ] Update `scripts/build_lockbox_second_review_pack.py`:
  - second-review contract/index files remain tracked;
  - rendered `index.html` defaults to ignored local externalized storage.
- [ ] Add or update CLI options consistently:
  - `--contract-dir`
  - `--rendered-output-dir`
  - `--check-only`
  - `--require-rendered-local`
- [ ] `--check-only` must validate tracked contract/index files by default and must not require ignored rendered files.
- [ ] Update the lockbox README to state:
  - what stays in git,
  - what is generated locally,
  - how to regenerate rendered review pages,
  - which commands are check-only and CI-safe.
- [ ] Update focused tests for the builder/checker behavior:
  - static bundle does not write HTML/PNG under `docs/superpowers/validation` by default;
  - challenge pack does not write rendered HTML under tracked validation path by default;
  - second-review pack does not write rendered HTML under tracked validation path by default;
  - check-only works on a clean checkout without rendered local files;
  - missing local rendered files fail only when `--require-rendered-local` is set;
  - legacy `--output-dir` or renamed flags still behave intentionally.

**Acceptance:**

- Running lockbox generators no longer reintroduces generated HTML/PNG into version-controlled paths.
- Existing label import and checker workflows still work from tracked contract/index files.

**Verification:**

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_static_review_bundle.py --check-only
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_lockbox_label_schema.py
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_lockbox_label_collection_pack.py tests/test_validation_artifact_retention.py -v --tb=short
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_validation_artifact_retention.py
git diff --check
```

---

## Phase 3: Shrink Quant-Matrix Validation Bundles Safely

**Purpose:** Remove the largest remaining tracked review burden without weakening the public matrix activation evidence.

### Phase 3A: Externalize Rendered Quant-Matrix Review HTML

- [ ] Target `docs/superpowers/validation/quant_matrix_real_bundle_v1/review/quant_matrix_review_report.html`.
- [ ] Move the rendered HTML to `local_validation_artifacts/externalized_superpowers_validation/quant_matrix_real_bundle_v1/review/`.
- [ ] Add a tracked README or JSON summary containing:
  - source builder command,
  - generated file name,
  - byte size,
  - SHA256,
  - creation/update date,
  - purpose,
  - statement that it is review-only and has no write authority.
- [ ] Update any checker or doc reference that expected the tracked HTML path.
- [ ] Add a focused test or checker assertion that the tracked replacement summary is enough for productization state validation.

### Phase 3B: Replace Duplicate `cell_provenance.tsv` Copies With Source Summaries

- [ ] Audit these copies before changing anything:
  - `docs/superpowers/validation/quant_matrix_default_product_activation_v1/default_output/cell_provenance.tsv`
  - `docs/superpowers/validation/quant_matrix_promotion_validation_packet_v2/artifacts/downstream_impact_inputs/cell_provenance.tsv`
  - `docs/superpowers/validation/quant_matrix_real_bundle_v1/quant_matrix_version/cell_provenance.tsv`
- [ ] Confirm whether they are byte-identical or intentionally different.
- [ ] If byte-identical, keep one minimal/source-authoritative summary in git and externalize duplicates.
- [ ] If not byte-identical, create one summary per logical source with:
  - row count,
  - column schema,
  - SHA256,
  - upstream command,
  - upstream source paths,
  - expected downstream consumer.
- [ ] Update productization status hashes and tests after replacement.
- [ ] Do not externalize any `cell_provenance.tsv` copy if `productization_status_index_v1.tsv` or a checker still requires the exact tracked file path and SHA. In that case, leave it as `shrink_later` and open the status-index migration slice first.

### Phase 3C: Shrink Full Review Row Dumps

- [ ] Target large full dumps only after dependency checks:
  - `docs/superpowers/validation/quant_matrix_real_bundle_v1/review/quant_matrix_review_rows.tsv`
  - `docs/superpowers/validation/review_queue_v1.tsv`
  - `docs/superpowers/validation/mechanical_adjudication_index_v1.tsv`
  - `docs/superpowers/validation/trace_overlay_recovery_report_v1.tsv`
- [ ] For each file, run a reference search:
  - scripts,
  - tests,
  - productization status index,
  - handoff/control-plane docs.
- [ ] If a full dump is only human review material, externalize it and keep a tracked summary.
- [ ] If a full dump is a checker input, add a smaller minimal fixture or derived contract first, then update the checker.
- [ ] If a full dump is referenced by `productization_status_index_v1.tsv`, do not replace it with a summary until a new productization status artifact schema exists and is tested. The new schema must record at minimum:
  - original source path,
  - full-source SHA256,
  - row count,
  - replacement summary path,
  - replacement summary SHA256,
  - consumer/checker migration status.
- [ ] Do not collapse review queues into vague prose; tracked summaries must preserve enough counts/hashes/statuses to audit the decision.

### Phase 3D: Rationalize Quant Matrix Expected-Diff Fixtures

- [ ] Keep public expected-diff fixtures only where they lock product surface:
  - final `quant_matrix.tsv` if it is the explicit default-output activation fixture;
  - minimal row/column fixtures needed by tests.
- [ ] Externalize duplicated downstream input copies if they are not the canonical fixture.
- [ ] Add tests that prove public surface remains locked after shrink:
  - row identity,
  - detected + accepted Backfill default matrix inclusion,
  - provenance sidecar availability,
  - `shadow_only=false` only where product activation allows it,
  - no change to selected peak/area/counting semantics.

**Acceptance:**

- The largest tracked quant-matrix validation artifacts are replaced by summaries or minimal fixtures.
- Public output behavior remains covered by expected-diff/output tests.
- No product behavior changes are smuggled into retention cleanup.

**Verification:**

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_validation_artifact_retention.py
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_quant_matrix_default_product_activation.py tests/test_productization_state_index.py tests/test_validation_artifact_retention.py -v --tb=short
git diff --check
```

---

## Phase 4: Add PR Hygiene Guardrails

**Purpose:** Make reviewability a maintained product rule, not a one-time cleanup.

- [ ] Decide where the retention checker is enforced:
  - minimum: documented local gate in `RETENTION.md` and handoff;
  - preferred: included in productization state checker or CI-equivalent validation command.
- [ ] Update `scripts/check_productization_state.py` only if the dependency direction stays simple:
  - productization checker may call/compose retention checker summary;
  - retention checker must not import product domain logic.
- [ ] Add a small docs note under `docs/agent/` or `docs/superpowers/validation/RETENTION.md`:
  - new validation artifacts require an inventory row;
  - full generated artifacts default to ignored local storage;
  - PRs should not add large generated HTML/PNG/TSV dumps without explicit exception.
- [ ] Add a PR-review checklist item to the current handoff:
  - tracked validation diff size;
  - generated artifact check;
  - externalized artifact summary/hash check.
- [ ] Do not modify root `AGENTS.md` unless this becomes a stable repo-wide rule that every future turn needs.

**Acceptance:**

- Future work has a fast way to catch validation artifact drift before PR review.
- The rule is discoverable by agents and maintainers.

**Verification:**

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_validation_artifact_retention.py
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_validation_artifact_retention.py tests/test_productization_state_index.py -v --tb=short
git diff --check
```

---

## Phase 5: Closeout, Commit Split, And Productization Handoff

**Purpose:** Leave the branch in a state where the PR diff is reviewable and the next agent cannot accidentally undo the cleanup.

- [ ] Re-run a full tracked validation inventory report:
  - tracked bytes before/after,
  - generated files removed,
  - externalized local bytes,
  - remaining `shrink_later` files and reasons.
- [ ] Update `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md` as a pruned current-state snapshot, not an appended log:
  - current verdict,
  - retention policy state,
  - counts and canonical links for externalized/deleted files,
  - remaining shrink debt,
  - commands run and verification verdicts.
- [ ] Keep long file lists in `ARTIFACT_INVENTORY.tsv`, per-bundle README files, or generated reports. Do not paste bulky file lists into the active handoff.
- [ ] Update `docs/superpowers/plans/2026-06-15-productization-control-plane.md` only if tier, active lane, authority, or tracked validation gate state changed. If not, state that no control-plane update is needed.
- [ ] Run final verification:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_validation_artifact_retention.py
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_lockbox_label_schema.py
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_validation_artifact_retention.py tests/test_lockbox_label_collection_pack.py tests/test_productization_state_index.py -v --tb=short
git diff --check
```

- [ ] Before each commit:
  - inspect `git status --short --branch`;
  - inspect staged diff;
  - stage only files for that purpose;
  - check for local absolute paths that should not be in tracked docs, except documented ignored artifact roots if intentional;
  - do not include unrelated dirty changes.

**Recommended commits:**

1. `Document validation artifact retention policy`
   - `RETENTION.md`
   - `ARTIFACT_INVENTORY.tsv`
   - lockbox rendered artifact deletions
   - lockbox static review README
2. `Add validation artifact retention checker`
   - checker script
   - tests
   - minimal docs wiring
3. `Externalize lockbox rendered review outputs`
   - generator default path split
   - focused tests
   - README/handoff updates
4. `Shrink quant matrix validation artifacts`
   - one commit per logical bundle if diff remains large
   - summaries/hashes
   - checker/test updates
5. `Close validation artifact cleanup handoff`
   - handoff/control-plane final wording only

**Final acceptance:**

- PR diff no longer contains bulky generated HTML/PNG review bundles.
- Remaining tracked validation artifacts are explainable, inventoried, and checker-enforced.
- Product behavior and public output semantics are unchanged except where a separate explicit product activation commit already changed them.
- A clean checkout can run check-only validation without ignored local rendered artifacts.
- Local rendered review artifacts are still regenerable for human review.
