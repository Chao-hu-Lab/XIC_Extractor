# Phase 2 Batch 1 Classification Review

Status: review/control artifact only.
Validation status: `diagnostic_only`.

This review classifies the first hand-read batch from the Phase 2 manifest.
It does not authorize moving, deleting, or `git rm`-ing any source file.

## Verdict

The batch should not be moved by directory.

- Repo indexes and active roadmap anchors stay in repo.
- Long research/planning notes with exact referrers become same-path stub plus
  private Obsidian candidates.
- Dated pulses and interpretation reports with no exact repo referrer can move
  to Obsidian after concise public claims are already owned by product-topic or
  control-plane docs.
- Sample-specific or review-rationale material is private-context material, not
  public repo history, unless a checker or retained validation owner needs a
  compact public verdict.

All rows remain `destructive_allowed_now=no`.

## Referrer Scan

Targeted fixed-string scans found exact referrers for:

- `docs/deepresearch/README.md`
- all individual deepresearch notes except through the deepresearch index or
  cleanup map
- the 2026-06-07 Backfill goal
- `XIC_Extractor_Productization_Roadmap_Review.md`
- `2026-06-02-raw-to-final-matrix-product-story.html`
- the Skyline runbook/smoke cluster

No exact repo referrers were found for the four productization pulse reports,
the mature-tool/source-grounded interpretation reports, or the 5hmdC own-max
opt-in review note in this scan.

## Batch Decisions

| Source | Decision | Repo owner | Obsidian target | Why |
| --- | --- | --- | --- | --- |
| `docs/deepresearch/README.md` | `repo_keep_current` | `docs/project-layout.md`; `docs/product/productization.md` | n/a | Cited research index and public routing surface. |
| `docs/deepresearch/Compair.md` | `repo_stub_plus_obsidian` | `docs/product/productization.md`; `docs/product/discovery.md`; `docs/product/alignment.md` | `XIC/30 Research Notes/Deepresearch/` | Mature-tool comparison is useful background, but stable floor/differentiator claims belong in product topics. |
| `docs/deepresearch/LC-MS targeted research.md` | `repo_stub_plus_obsidian` | `docs/lcms-msms-evidence-rules.md`; `docs/product/productization.md` | `XIC/30 Research Notes/Deepresearch/` | Targeted LC-MS/ISTD reasoning belongs in evidence semantics, with private detail outside repo. |
| `docs/deepresearch/LCMS_Backfill_Design_Notes.md` | `repo_stub_plus_obsidian` | `docs/product/backfill.md`; `docs/product/productization.md` | `XIC/30 Research Notes/Deepresearch/` | Large Backfill RFC; public authority and writer claims now belong in Backfill/productization owners. |
| `docs/deepresearch/Resolver.md` | `repo_stub_plus_obsidian` | `docs/product/presets.md`; `docs/lcms-msms-evidence-rules.md` | `XIC/30 Research Notes/Deepresearch/` | Resolver background must not become implicit default/preset authority. |
| `docs/deepresearch/software backfill.md` | `repo_stub_plus_obsidian` | `docs/product/backfill.md`; `docs/product/productization.md` | `XIC/30 Research Notes/Deepresearch/` | Reimport/rerun lessons are background after Backfill public claims are covered. |
| `docs/superpowers/goals/README.md` | `repo_keep_current` | `docs/superpowers/plans/2026-06-15-productization-control-plane.md` | n/a | Routing index for active and historical goals. |
| `docs/superpowers/goals/XIC_Extractor_Productization_Roadmap_Review.md` | `repo_keep_current` | `docs/product/backfill.md`; `docs/superpowers/plans/2026-06-15-productization-control-plane.md` | n/a | Still an active roadmap anchor through the goals README. |
| `docs/superpowers/goals/2026-06-07-backfill-evidence-reconciliation-productization-goal.md` | `repo_stub_plus_obsidian` | `docs/product/backfill.md`; `docs/superpowers/plans/2026-06-15-productization-control-plane.md` | `XIC/20 Archived Plans And Specs/Goals/` | Historical goal has exact plan refs; use stub until those refs are retired. |
| Productization pulse reports, 2026-06-17 to 2026-06-21 | `formalize_then_obsidian` | `docs/product/productization.md`; control plane | `XIC/50 Validation Context/Run Narratives/` | Dated status narratives with no exact repo referrer in this scan. |
| `docs/superpowers/pulse-reports/README.md` | `repo_keep_current` | control plane | n/a | Routing/index file. |
| `2026-06-02-raw-to-final-matrix-product-story.html` | `repo_stub_plus_obsidian` | `docs/product/alignment.md`; `docs/product/productization.md` | `XIC/10 Development History/Command Narratives/` | Human-facing rendered story still has companion spec refs. |
| `2026-06-15-mature-tool-differentiation-conclusion.md` | `formalize_then_obsidian` | `docs/product/productization.md` | `XIC/50 Validation Context/Interpretation Notes/` | Stable product positioning belongs in the productization topic. |
| Skyline preflight/runbook/smoke reports | `repo_stub_plus_obsidian` | `docs/product/productization.md` | `XIC/50 Validation Context/Run Narratives/` | Cluster has internal exact refs and is comparator narrative, not authority. |
| `2026-06-15-source-grounded-parity-and-differentiation-roadmap.md` | `formalize_then_obsidian` | `docs/product/productization.md` | `XIC/50 Validation Context/Interpretation Notes/` | Interpretation report with stable claims already owned by the productization topic. |
| `2026-06-16-5hmdc-own-max-optin-review.md` | `formalize_then_obsidian` | `docs/lcms-msms-evidence-rules.md`; `docs/superpowers/validation/RETENTION.md` | `XIC/40 Review Workbench/Human Review Notes/` | Sample-specific review rationale should be private unless a compact validation verdict is required. |

## Before Any Move

1. Re-run exact referrer scan for the target path.
2. Confirm the repo owner contains the stable public claim.
3. If exact referrers remain, create or keep a same-path sanitized stub.
4. Copy private narrative to the listed Obsidian folder.
5. Ask for explicit user approval before any `git rm` or destructive cleanup.
