# Docs cleanup branch closeout summary

Branch: `codex/docs-cleanup`
Date: 2026-06-26
Status: PR gate passed; PR closeout seed ready
Validation status: `diagnostic_only`

## Summary

This branch separates public repo documentation from private development
history. The repo now keeps durable source-of-truth docs, public-safe migration
evidence, checker-readable validation contracts, and compact branch handoffs.
Obsidian keeps private diaries, long review rationale, branch sequencing, and
local context. Ignored local artifact storage keeps bulky generated validation
outputs.

This is workflow-only documentation governance. It does not change maturity
tier, active lane, ProductWriter authority, output schema, review/replay
behavior, selected values, selected area/counting, matrix values, or matrix
authority. No productization control-plane tier update is required.

During PR-gate closeout, retained validation JSON summaries were normalized from
invalid Windows-style JSON path escapes to repo-relative forward-slash paths.
The resulting hash cascade was synchronized through the validation inventory,
productization status index, bounded-lane acceptance packet, authority manifest,
and lockbox summaries. This preserved existing authority decisions; it did not
promote or demote any lane.

## Scope

- Added and strengthened formal source-of-truth docs under `docs/product/` and
  `docs/agent/obsidian-handoff-contract.md`.
- Updated layout/routing docs so plans, notes, deep research, handoffs,
  Obsidian, and ignored artifacts have one placement model.
- Added docs placement guardrails and docs-management audit tooling.
- Rewrote public referrers away from private-history paths or toward formal repo
  owners.
- Removed approved no-referrer private-history batches and two later approved
  validation full TSVs from git.
- Externalized bulky validation artifacts while retaining clean-checkout
  summaries, manifests, hashes, minimal fixtures, and contract provenance.

Out of scope:

- product behavior, RAW execution, matrix activation, writer authority, and
  productization tier changes;
- pushing, opening PR, merging, branch deletion, or local artifact cleanup.

## Commit Split

- `b89850ed` to `e2bdcbe0`: define the public/private docs boundary and correct
  productization-impact wording.
- `634d568c`: establish the repo/Obsidian document flow and perform the two
  explicitly approved no-referrer private-history removal batches.
- `a1e43819`: harden docs-management health checks and staged-doc placement
  guard behavior.
- `ead777bf`, `4ebf3c2d`, `1ea1c69a`: review validation retention debt,
  externalize exact approved full TSVs, and leave the validation inventory at
  `249 retained`, `48 externalized`, `0 shrink_later`.

## Handoff Routing Demonstration

This closeout intentionally routes handoff-related content once, so future
agents can copy the pattern without inventing another system.

| Source content | Routed to | Kept out of |
| --- | --- | --- |
| Branch objective, current status, stop rules, next 1-3 actions | ignored local handoff under `docs/superpowers/handoffs/current/` | PR body, Obsidian-only notes |
| Reviewer-readable problem, solution, verification, residual risk | This archive closeout summary, then PR body | Current handoff long history |
| Completed file-management authorization evidence | `docs/superpowers/file-management/docs-cleanup/` manifests, audits, and referrer sidecars | Current handoff |
| Private development diary, command narrative, branch sequencing, detailed review rationale | Obsidian private notebook layer | Repo and PR body |
| Full generated validation TSVs not needed for clean checkout | `local_validation_artifacts/externalized_superpowers_validation/` | Git history |
| Stable product/method claims | `docs/product/`, `docs/agent/`, validation summaries, and named specs | Handoff as authority |

Routing result for this branch:

- The active handoff is now a compact resume stub.
- This archive file is the PR-body seed and completed phase summary.
- No new parallel `docs/product`-like handoff taxonomy was introduced.
- Handoff is not treated as product authority; formal docs and validation
  contracts remain the source of truth.

## Verification

Latest validation run for the current branch state:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x
python -m scripts.check_validation_artifact_retention --require-externalized-local
python -m scripts.check_productization_state
python -m scripts.check_productization_authority
python -m scripts.check_bounded_product_lanes
python tools/diagnostics/docs_management_audit.py
```

Observed results:

- ruff passed;
- mypy reported `Success: no issues found in 359 source files`;
- full pytest reported `4441 passed`, `2 skipped`;
- retention checker passed with `249 retained`, `48 externalized`,
  `0 shrink_later`;
- productization state, authority, and bounded-lane checkers passed;
- docs audit reported `0 blockers`, `0 warnings`;
- manifest local-copy hash/size check passed.

## PR Body Seed

### Summary

- Separates public source-of-truth documentation from private development
  history and Obsidian-only notes.
- Adds repo/Obsidian/handoff routing rules, staged Markdown placement guardrails,
  and a repeatable docs-management audit.
- Externalizes approved bulky validation artifacts while preserving
  clean-checkout summaries, hashes, manifests, minimal fixtures, and provenance
  contracts.
- Readiness: `diagnostic_only`; workflow-only docs governance cleanup.

### Scope

- Lane: `workflow-only`.
- Product output change: no.
- Public contracts at risk: documentation placement rules, validation artifact
  retention metadata, and docs/handoff workflow only.
- Preserved contracts: ProductWriter authority, matrix/workbook schema, selected
  peak/area, counted detection, run metadata behavior, review/replay behavior,
  and productization tiers.

### Validation

- Focused tests/checkers passed:
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x`
  - `python -m scripts.check_validation_artifact_retention --require-externalized-local`
  - `python -m scripts.check_productization_state`
  - `python -m scripts.check_productization_authority`
  - `python -m scripts.check_bounded_product_lanes`
  - `python tools/diagnostics/docs_management_audit.py`
- Real-data/product validation was intentionally not run because this branch does
  not change extraction, alignment, scoring, matrix output, or product behavior.

### Authority Check

- This PR does not grant ProductWriter, workbook, or matrix authority from
  diagnostics, sidecars, review packets, Obsidian notes, or handoffs.
- Tracked deletion was limited to explicitly authorized path sets.
- Handoff content is routed as resume/PR context only; formal docs and retained
  validation artifacts remain authority.

### Residual Risk

- Placement markers and docs audits reduce common mistakes but do not prove that
  future docs are semantically public-safe; human review and secret/local-path
  scans remain required.
- Obsidian is a private depth layer. Repo stubs must remain self-sufficient when
  future work depends on private context.
- The branch diff is large because it removes private-history documents and adds
  formal replacement docs; review should focus on source-of-truth coverage,
  retained evidence, and guard behavior rather than line count alone.
