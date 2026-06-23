# Backfill Evidence Reconciliation Productization Goal

> Superseded for active Backfill roadmap execution as of 2026-06-18.
> Keep this file as historical diagnostic/gallery provenance because
> `tools/diagnostics/INDEX.md` cites it as an originating goal. Do not execute
> it as the current Backfill productization goal. Use
> `docs/superpowers/goals/XIC_Extractor_Productization_Roadmap_Review.md` and
> `docs/superpowers/plans/2026-06-18-backfill-evidence-lifecycle-blueprint.md`
> for current evidence-chain phase work.

```text
/goal
GOAL:
Deliver the backfill evidence reconciliation path from diagnostic observability
to a conditional product-ready decision: build the machine reconciliation index,
build the human gallery, close or externalize upstream evidence gaps, and promote
only an allowlisted backfill slice when product-grade evidence passes reviewed
8RAW and 85RAW gates.

CONTEXT:
- Repository: XIC_Extractor repo root checkout.
- Repo instructions: AGENTS.md; docs/agent-subagent-routing.md;
  docs/architecture-contract.md; docs/agent-parameter-settings.md.
- Active spec:
  docs/superpowers/specs/2026-06-07-backfill-evidence-reconciliation-gallery-design.md.
- Prior product-path context:
  docs/superpowers/plans/2026-06-05-backfill-evidence-gate-productization.md;
  docs/superpowers/plans/2026-06-05-product-authority-reconciliation-v1.md.
- Existing backfill/overlay review context:
  docs/superpowers/notes/2026-05-19-seed-aware-backfill-review-index.md;
  docs/superpowers/notes/2026-05-19-untargeted-ms1-coherence-backfill-review.md.
- Diagnostic lifecycle and index:
  tools/diagnostics/INDEX.md.
- Likely code owners for implementation:
  xic_extractor/diagnostics/;
  tools/diagnostics/;
  tests/;
  xic_extractor/alignment/production_candidate_gate.py only if a reviewed
  product-grade evidence extension becomes necessary.
- Current readiness baseline from prior productization plan:
  backfill evidence gate product path reached production_candidate, but not
  production_ready, because changed-row EIC/MS2 or targeted benchmark
  adjudication remained incomplete.

CONSTRAINTS:
- Keep scope limited to this goal and the reviewed spec. Do not add unrelated
  cleanup or broad backfill rewrites.
- Preserve public contracts unless a reviewed promotion sub-contract explicitly
  changes them: existing CLI flags, existing alignment TSV schemas,
  alignment_matrix.tsv public shape, workbook schemas, RAW/DLL paths, and
  downstream matrix handoff.
- Do not mutate alignment_review.tsv, alignment_cells.tsv, alignment_matrix.tsv,
  workbooks, selected peaks, selected areas, or product decisions while building
  the diagnostic gallery/index.
- The gallery and reconciliation index must consume existing artifacts only.
  They must not read RAW, call Thermo DLLs, generate overlays, recompute domain
  evidence, or invent a composite backfill score.
- Keep product behavior, product-grade evidence, review-only visual evidence,
  dependent context, and human visual judgment separate in machine-readable
  outputs and HTML.
- Manual visual judgment may calibrate and challenge rules; it must not directly
  become a product gate.
- If strong visual evidence lacks product-grade sidecar support, either extend
  the upstream evidence owner under a reviewed contract or stop with the gap
  named. Do not solve it inside the gallery renderer.
- Product promotion is allowlist-only. Promote only family/seed groups that pass
  the product-grade evidence chain; leave blocked, stale, missing-overlay,
  missing-seed-provenance, high-interference, or join-gap groups as review-only,
  blocked, or not_assessable.
- Verification integrity: do not weaken or bypass tests, assertions, lint,
  typecheck, validation, generated-output checks, screenshots, browser smoke,
  subagent review, or external blockers to make the goal pass; fix the root
  cause or report the blocker.
- RAW/85RAW commands must follow docs/agent-parameter-settings.md. Do not run
  85RAW through background Start-Process from the Codex shell.

DONE WHEN:
- Slice 0 is complete: a diagnostic CLI and package module write
  backfill_evidence_reconciliation_groups.tsv,
  backfill_evidence_reconciliation_representative_cells.tsv, and
  backfill_evidence_reconciliation_summary.json with schema_version
  backfill_evidence_reconciliation_v0; all groups have deterministic
  seed_group_id, product_behavior_state, evidence_authority_state,
  reconciliation_class, missing_evidence, source_warnings, and representative
  cell rows where possible.
- Slice 1 is complete: the same source index renders a table-first
  backfill_evidence_reconciliation_gallery.html that includes all backfill
  family/seed groups, sorts disagreement-first, keeps details collapsed by
  default, shows representative cells only, links full TSV/JSON/PNG evidence,
  and remains usable without JavaScript.
- Evidence gaps are classified: recurring missing overlay, missing seed
  provenance, stale-source, join-gap, or missing product-grade support cases are
  either fixed in their upstream evidence owner, externalized as review-only, or
  listed as blockers with exact source artifacts.
- If product promotion is attempted, the allowlisted slice has a reviewed
  promotion sub-contract, product-grade machine-readable evidence, successful
  subagent implementation/validation review, passing focused tests, passing
  8RAW validation, and passing 85RAW validation. Only then may the slice be
  called production_ready.
- If only Slice 0/1 gallery and machine-index work completes, the final state is
  `shadow_ready`, not `production_candidate`.
- If product promotion is attempted and a reviewed allowlisted slice has
  product-grade evidence but stops before 85RAW acceptance, the slice may be
  reported as `production_candidate` with the precise missing evidence or
  blocker. Do not claim `production_ready`.
- tools/diagnostics/INDEX.md and relevant docs/superpowers handoff notes are
  updated for any new diagnostic CLI or durable output surface.
- No unrelated dirty scope is staged or committed.

VERIFY:
- Run focused no-RAW tests for Slice 0/1:
  $env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_backfill_evidence_reconciliation_gallery.py
- Run focused lint for new/changed diagnostic files:
  $env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools/diagnostics/backfill_evidence_reconciliation_gallery.py xic_extractor/diagnostics/backfill_reconciliation_gallery.py tests/test_backfill_evidence_reconciliation_gallery.py
- If product evidence owners or alignment product behavior change, also run the
  targeted affected shards named by the implementation plan, plus package mypy
  when package types change.
- Run existing-artifact smoke for the reconciliation outputs before any RAW run.
- Run browser smoke for the gallery at desktop, mobile, and 200 percent zoom;
  check sticky/header behavior, collapsed details, filters, PNG fallback,
  lightbox keyboard behavior, and non-overlap.
- Before any 85RAW run, run the documented preflight and get
  validation-evidence reviewer preflight. For product promotion, run 8RAW before
  85RAW, then request validation-evidence reviewer acceptance.
- Capture exact commands, pass/fail output, output artifact paths, readiness
  label, and whether the gate is synthetic, existing-artifact smoke, 8RAW, 85RAW,
  targeted benchmark, manual EIC/MS2 review, or CI shard.

OUTPUT:
- Changed files and new artifacts.
- Key decisions made while executing the goal, especially evidence-authority and
  promotion-scope decisions.
- Verification commands and observed results.
- Readiness verdict: diagnostic_only, shadow_ready, production_candidate,
  production_ready for an allowlisted slice, or inconclusive.
- Remaining product risk and the smallest next action.
- Follow-up list separated into upstream evidence gaps, gallery UX gaps,
  production-gate gaps, and validation gaps.

STOP RULES:
- Stop if the next action would change public TSV/workbook/schema/matrix
  behavior without a reviewed contract.
- Stop if a gallery implementation needs to recompute similarity, make a
  composite score, read RAW, or infer product-grade support from review-only
  visual evidence.
- Stop if source artifacts cannot be joined safely or run provenance is stale;
  emit not_assessable / source warning instead of support.
- Stop if 8RAW is inconclusive; do not launch 85RAW just to see what happens.
- Stop if 85RAW fails, shows unbounded false-positive/interference risk, or
  leaves the allowlisted slice unsupported; report production_candidate or
  shadow_ready instead of production_ready.
- Stop if subagent review finds a blocker that contradicts the current product
  direction and cannot be closed without a user decision.
- Stop after three failed attempts on the same symptom and revisit the root-cause
  hypothesis.
- Do not mark complete until the current state has been checked against DONE
  WHEN and VERIFY.
```
