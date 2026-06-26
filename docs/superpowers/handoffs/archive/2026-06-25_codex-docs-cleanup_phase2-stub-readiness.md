# Phase 2 Same-Path Stub Readiness

Status: review/control artifact only.
Validation status: `diagnostic_only`.

This report reviews `repo_stub_plus_obsidian` candidates from the Phase 2
manifest. Completed rows record same-path stub replacements after private
Obsidian readback. It does not authorize moving, deleting, or `git rm`-ing any
source file.

## Method

- Read the Phase 2 manifest and selected source-of-truth queue rows.
- Ran fixed-string exact-path scans for `repo_stub_plus_obsidian` source paths.
- Excluded the manifest itself from referrer counts.
- Treated self-references inside a source file as noise for move readiness, but
  not as permission to replace the file.

Exact-path scans are necessary but not sufficient. Before any file replacement,
also scan for relative links, basenames, and family-level references.

## First Safe Work Batch

These are good first candidates for Obsidian staged copy/readback and same-path
stub drafting. Rows marked done have already followed that pattern.

| Source group | Sources | Exact referrer result | Repo owner | Next safe action |
| --- | --- | --- | --- | --- |
| Deepresearch background | `docs/deepresearch/Compair.md`, `LC-MS targeted research.md`, `LCMS_Backfill_Design_Notes.md`, `Resolver.md`, `software backfill.md` | mostly batch-review only; Backfill/Resolver/software also appear in the cleanup map | product topics plus LC-MS/MS evidence rules | done for first batch: private Obsidian source copies, staged distillations, and same-path repo stubs |
| Instrument QC notes | `2026-05-20-instrument-qc-drift-findings.md`, `2026-05-20-instrument-qc-hcd-audit-v1-decision.md`, `2026-05-21-instrument-qc-level3-no-go-convergence.md` | product topic and source spec/checklist cite them | `docs/product/instrument-qc-calibration.md` | done for first batch: private Obsidian source copies, one staged synthesis, and same-path repo stubs |
| Skyline comparator cluster | `2026-06-15-skyline-8sample-smoke.md`, `2026-06-15-skyline-expressibility-preflight.md`, `2026-06-15-skyline-expressibility-runbook.md`, `2026-06-15-skyline-single-sample-smoke.md` | cluster has internal exact refs; some files have no external exact refs | `docs/product/productization.md` | done for first batch: private Obsidian source copies, one staged synthesis, and same-path repo stubs |
| Zero-exact-ref candidates | `2026-05-28-handoff-productization-step2-audit-spine-runtime-contract-closeout.md`, `2026-06-09-matrix-only-backfill-activation.md` | no exact-path referrer found in this scan | product topics and relevant source specs | done for first batch: private Obsidian source copies, one staged synthesis, and same-path repo stubs |
| Human-facing HTML reports | `2026-06-02-raw-to-final-matrix-product-story.html` | no exact-path referrer found in this scan | product topics and relevant source specs | keep original tracked HTML in repo; do not convert to stub or migrate to Obsidian by default |

## Backfill Historical Plan Cluster

These were completed as the next cleanup batch after private Obsidian readback.
They are historical goal/plan/policy narratives, not current repo authority.

| Source group | Sources | Repo owner | Completed action |
| --- | --- | --- | --- |
| Backfill productization history | `docs/superpowers/goals/2026-06-07-backfill-evidence-reconciliation-productization-goal.md`, `docs/superpowers/plans/2026-06-05-backfill-evidence-gate-productization.md`, `docs/superpowers/plans/2026-06-05-product-authority-reconciliation-v1.md`, `docs/superpowers/plans/2026-06-07-backfill-evidence-reconciliation-productization-plan.md`, `docs/superpowers/plans/2026-06-08-peakhypothesis-backfill-promotion-policy.md`, `docs/superpowers/plans/2026-06-18-backfill-evidence-lifecycle-blueprint.md` | `docs/product/backfill.md`, `docs/product/quant-matrix.md`, `docs/product/productization.md`, `docs/product/run-provenance.md`, `docs/lcms-msms-evidence-rules.md`, `docs/superpowers/plans/2026-06-15-productization-control-plane.md`, `docs/superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md` | done: full private Obsidian source copies, staged provenance synthesis, same-path repo stubs, and Backfill owner list corrected to drop the superseded 2026-06-18 lifecycle blueprint |

## Remaining High-Confidence Stub Batch

These remaining manifest rows were completed after private Obsidian readback.
They are historical closeouts, superseded specs, or dated inventory, not current
repo authority.

| Source group | Sources | Repo owner | Completed action |
| --- | --- | --- | --- |
| Productization/matrix historical stubs | C0 and phase closeout notes; Tier 2 sidecar checkpoint; quantitation-context 8RAW closeout; row-completion implementation plan; dated capability inventory; superseded final-matrix, matrix-identity, cleanup roadmap, modernization, AsLS policy, and shared-spine specs | product-topic owners, current specs, control plane, status index, authority manifest, and LC-MS/MS evidence rules | done: full private Obsidian source copies, one staged synthesis, same-path public stubs, stale product owner links removed, matrix-only activation rule moved into `docs/product/quant-matrix.md`, and 2026-06-19 Backfill blueprint current-authority wording reconciled with the 84-cell production-ready lane |
| Early implementation history | output maintainability, RAW processing, resolver GUI, local-minimum, Excel review/report, weighted evidence, Discovery v1, alignment, MS1/MS2 feature-family, owner-based alignment, and untargeted output-level implementation plans | `docs/project-layout.md`, product-topic owners, LC-MS/MS evidence rules, and active specs | done: full private Obsidian source copies, one staged synthesis, and same-path public stubs |
| Mid implementation history | untargeted performance/locality, final-matrix rescue, matrix identity, multi-NL, targeted benchmark reliability, and identity-coherence implementation/validation plans | product-topic owners, LC-MS/MS evidence rules, active specs, diagnostics index, and validation contracts | done: full private Obsidian source copies, one staged synthesis, and same-path public stubs |
| Selected hypothesis / full-envelope history | selected-hypothesis closeouts, full-envelope FE notes, targeted projection closeout, and selected/full-envelope implementation goals | `docs/product/peak-model-selection.md`, `docs/product/targeted-selection.md`, `docs/product/quantitation-context.md`, `docs/product/quant-matrix.md`, retained specs, diagnostics index, and validation contracts | done: full private Obsidian source copies, one staged synthesis, and same-path public stubs; `2026-06-02-selected-hypothesis-model-selection-characterization-map.md` was promoted to `docs/product/peak-model-selection.md` and the notes path is now a stub |
| Bulk private-history batch | 52 high-confidence notes/plans across resolver/presets, Backfill, evidence-spine, quant matrix, targeted selection, instrument-QC, productization, review, and method-cleanup history | product-topic owners plus architecture/evidence-rule owners | done: private Obsidian source copies with readback/hash verification and same-path public stubs; see `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_bulk-private-history-stub-batch.md`; no control-plane tier/lane or checker contract changed |
| Remaining notes/plans batch | 104 remaining eligible `docs/superpowers/notes/` and `docs/superpowers/plans/` private-history files | product-topic owners plus architecture/evidence-rule owners | done: private Obsidian source copies with readback/hash verification and same-path public stubs; see `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_remaining-notes-plans-stub-batch.md`; only the test-bound characterization map and status/authority-hash-bound broad-autowrite packet remain non-stubbed |

## Not First Batch

These have active public or machine-checkable dependencies. They should not be
stubbed until the named dependency is updated or intentionally kept pointing at
a sanitized same-path stub.

| Source | Why not first |
| --- | --- |
| `docs/superpowers/notes/backfill_broad_autowrite_feasibility_gate_v1.md` | productization status index and authority manifest cite this exact decision packet and hash |

## Policy Decisions

- Same-path stubs are a compatibility layer, not a content dump. They should
  keep a public summary, current repo owner, validation status, and next safe
  action.
- If a source is a machine decision packet, status-index artifact, authority
  manifest input, or control-plane evidence path, do not replace it with a stub
  until hashes/referrers/checkers are updated in the same patch.
- If a source is private narrative with only historical plan or cleanup-map
  refs, prefer Obsidian staged copy/readback first, then a short same-path stub.
- If exact referrers are only batch-control artifacts created by this cleanup,
  do not treat those artifacts as blockers. They are audit trail, not product
  authority.

## Next Safe Action

1. Treat all First Safe Work Batch rows as completed examples of the cleanup
   pattern: private source copy, staged distilled note, and same-path public stub.
2. Update the cleanup map or keep same-path stubs where exact refs remain.
3. Apply the same review pattern to later manifest groups only after reading
   their source docs and owner docs.
4. Ask for explicit user approval before any path move, deletion, or
   `git rm`.
