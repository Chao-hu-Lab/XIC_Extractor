# Product Direction Cleanup Inventory v2

Date: 2026-06-18
Status: `diagnostic_only` repo-wide slop cleanup inventory
Scope: active planning/productization surfaces under `docs/superpowers/`.

This inventory is written before the cleanup edits it authorizes. It does not
grant product authority and does not change ProductWriter, matrix/workbook
outputs, selected peak/area, counted detection, GUI, default extraction, RAW
behavior, or broad Backfill state.

## Current Cleanup Decision

The first repo-wide slop problem is not production code deletion. It is active
planning surface ambiguity: old goals/plans/specs remain in top-level
`goals/`, `plans/`, and `specs/` roots and can be mistaken for the current
Backfill roadmap. This pass therefore adds explicit routing indexes and
superseded banners before deleting anything.

## Disposition Table

| Path | Pre-Action SHA256 | Action | Authority Relevance | Reason | Delete? |
|---|---|---|---|---|---|
| `docs/superpowers/goals/README.md` | new file | create routing index | routing only | define that only the roadmap/current goal is active; old goals are historical unless the control plane names them | no |
| `docs/superpowers/plans/README.md` | new file | create routing index | routing only | define control-plane-first reading order and prevent dated plans from being treated as active roadmap | no |
| `docs/superpowers/specs/README.md` | new file | create routing index | routing only | define specs as contracts/background, not automatic active implementation goals | no |
| `docs/superpowers/goals/2026-06-07-backfill-evidence-reconciliation-productization-goal.md` | `B6223BE7EE36A3A467CA0A9E64F6662ED9BDFF5DC1310DB031A1BF30424E5F26` | add superseded banner | diagnostic/gallery provenance; not current authority | old goal can be mistaken for current Backfill productization goal and still names promotion/8RAW/85RAW path | no; referenced by `tools/diagnostics/INDEX.md` |
| `docs/superpowers/plans/2026-06-07-backfill-evidence-reconciliation-productization-plan.md` | `4FEB026FF0C852D76565C6E9F089160A98E252A7B6D65AB5D0B34A745FFE41C4` | add superseded banner | diagnostic/gallery provenance; not current authority | old plan remains useful for diagnostic origin but must not override the evidence lifecycle blueprint | no; referenced by `tools/diagnostics/INDEX.md` |
| `docs/superpowers/specs/2026-06-07-backfill-evidence-reconciliation-gallery-design.md` | `1497BA7E09AEEA9BFBF948015C5C501749FD828DE6CA31C786604823F9216B21` | add superseded-for-roadmap banner | diagnostic/gallery design; not current authority | old design is still a review-gallery provenance doc, but its productization decisions are superseded by the control plane and evidence lifecycle blueprint | no; referenced by `tools/diagnostics/INDEX.md` |
| `docs/superpowers/plans/2026-06-05-backfill-evidence-gate-productization.md` | `FF951C4ECCB0494591AD2DC80392637B4544D682A5363595D7302B5047D7E3B1` | add historical-slice banner | prior product slice evidence; not current roadmap | contains completed product-candidate slice details that should not be mistaken for broad Backfill reopening | no |
| `docs/superpowers/plans/2026-06-05-product-authority-reconciliation-v1.md` | `6EE4B73C17756570F5392593B09D7EF56397204037BAA880F7152998007AA897` | add historical-addendum banner | prior authority hygiene evidence; not current roadmap | contains authority table and readiness claims that now need explicit control-plane-first reading | no |
| `docs/superpowers/notes/backfill_broad_autowrite_feasibility_gate_v1.md` | `1F1BB2ACB7E7A1495BCBE6DC0D679196676E3B44E3F92E5AA84EBB86E7E25474` | keep unchanged | parked decision packet; hash-indexed authority evidence | status index and authority manifest cite this hash; editing would create authority drift | no |
| `docs/superpowers/notes/2026-06-18-backfill-autowrite-ground-truth-critical-review.md` | `1C2E9414B2AE7E8E88CD2949F32899AF07A688B2D310A199BD1EC2CADF37A853` | keep unchanged | critique/background; control-plane-cited provenance | useful as rationale for parking broad Backfill; current roadmap supersedes it for execution | no |
| `docs/superpowers/notes/2026-06-18-backfill-autowrite-ground-truth-strategy-note.md` | `879AFBC34DFD2B87A1B113E0BC5CE25201450246BADF4F06371BCE6592658108` | keep unchanged | strategy/background; control-plane-cited provenance | contains old auto-write north-star exploration; current roadmap supersedes it for execution | no |

## Deferred Candidates

These are plausible slop clusters, but this pass does not delete or rewrite
them because they may still document product behavior, historical validation, or
diagnostic origin:

- old peak-scoring and weighted-confidence docs;
- old provisional Backfill sidecar / machine-decision docs;
- large historical implementation plans under `docs/superpowers/plans/`;
- historical notes under `docs/superpowers/notes/`.

Follow-up cleanup should classify them with source hashes and references before
moving, deleting, or rewriting. Do not delete tracked diagnostic provenance just
because it is no longer the active roadmap.
