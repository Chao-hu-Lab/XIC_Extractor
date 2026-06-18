# Backfill Quant Matrix Cleanup Map

Date: 2026-06-19
Status: `diagnostic_only` Phase 0/1 cleanup map
Scope: Backfill/quant-matrix direction reset under `docs/superpowers/`,
`docs/deepresearch/`, lockbox shadow automation docs/scripts/tests, and active
handoff surfaces.

This map records cleanup disposition and Phase 1 follow-through state.
It does not grant product authority and does not change ProductWriter, matrix,
workbook, selected peak/area, counted detection, GUI, default extraction, RAW
behavior, or current broad Backfill state.

## Decision

The active direction is now:

```text
accepted Backfill = quantification value
not detection
not truth claim
default quant matrix = detected + accepted Backfill
write authority = ProductionAcceptanceManifest only
```

The immediate cleanup is docs/source-of-truth alignment. Production code deletion
is out of scope for Phase 0.

## Disposition Table

| Target | Type | Current role | Conflict with new blueprint | Action | Why now / why later | Dependencies / reader risk |
| --- | --- | --- | --- | --- | --- | --- |
| `docs/superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md` | doc | new active blueprint | none | keep | creates the authoritative roadmap | future Backfill goals read this first |
| `docs/superpowers/plans/2026-06-18-backfill-evidence-lifecycle-blueprint.md` | doc | previous active blueprint | over-parks Backfill, uses truth import, Phase 1 points to Evidence Chain Packet | downgrade | keep as adapt source; no delete because it records prior cleanup discipline | high reader risk if left active |
| `docs/superpowers/goals/XIC_Extractor_Productization_Roadmap_Review.md` | doc | active roadmap | says Backfill evidence recovery / broad parked as direction | adapt | roadmap must match accepted-quant Backfill direction | high reader risk |
| `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md` | doc | continuation state | old versions pointed to evidence packet or Phase 1 as future work | adapt complete | handoff now records Phase 1 result and Phase 2 next action | high reader risk |
| `docs/superpowers/plans/README.md` | doc | routing index | points to 2026-06-18 blueprint and parked wording | adapt | active reading order must point to new blueprint | high reader risk |
| `docs/superpowers/goals/README.md` | doc | routing index | active goal surface does not name new blueprint | adapt | reduce dated-goal ambiguity | medium reader risk |
| `docs/superpowers/specs/README.md` | doc | routing index | conflict check names old blueprint | adapt | specs should resolve against new blueprint | medium reader risk |
| `docs/deepresearch/README.md` | doc | research index | synthesis points to old blueprint and old Backfill wording | adapt | deepresearch remains background only but should cite new synthesis | medium reader risk |
| `docs/deepresearch/LCMS_Backfill_Design_Notes.md` | doc | research input | contains both accepted matrix examples and older evidence-recovery framing | adapt source | do not edit now; new blueprint absorbs `BACKFILLED_ACCEPTED` and provenance lessons | research provenance |
| `docs/deepresearch/software backfill.md` | doc | research input | job/rerun lessons could be mistaken for write authority | adapt source | use for job framework later, not Phase 1 authority | research provenance |
| `docs/deepresearch/Resolver.md` | doc | research input | resolver detail could block acceptance v1 | adapt source | use resolver as evidence/research lane; not acceptance blocker | research provenance |
| `docs/deepresearch/Backfill Production Gate.md` | doc | research input | stricter auto-write gate language may over-block low seed/high dependency | adapt source | keep boundary/RT/local evidence lessons; downgrade prevalence to report-only risk | research provenance |
| `scripts/build_lockbox_shadow_automation_experiment_design.py` | code | shadow contract adapter/checker | previous version used scorer wording and `implement_shadow_only_scoring_experiment` | adapt complete | Phase 1 now emits shadow/truth/doublet/source/hash/authority contract fields without running scorer | tests own current contract |
| `tests/test_lockbox_shadow_automation_experiment_design.py` | test | shadow contract adapter tests | previous version asserted scorer next-step wording only | adapt complete | Phase 1 now covers authority invariants, manual-negative hard stop, doublet blockers, source/hash, and owner-clean non-authority | test contract changed in Phase 1 |
| `docs/superpowers/validation/lockbox_shadow_automation_cases_v1.tsv` | artifact | only 72-case shadow source | none if kept as sole source | keep | must not spawn second case manifest | source-of-truth for Phase 1 only |
| `docs/superpowers/validation/lockbox_shadow_automation_experiment_v1.json` | artifact | shadow contract adapter summary | previous version used scoring wording and lacked enum fields | adapt complete | updated through builder/checker with manifest sha and non-authority contract | generated/checker-owned artifact |
| `xic_extractor/diagnostics/standard_peak_shadow_activation_inputs.py` | code | standard-peak activation inputs | has activation/write-authority semantics that cannot be reused for Phase 1 shadow lane | adapt source | reuse source/hash/schema patterns only; do not reuse authority semantics | Phase 2/3 may reuse patterns |
| `docs/superpowers/specs/2026-06-13-backfill-integration-policy-spec.md` | doc | seed guard / activation policy spec | low seed support currently blocks automatic backfill in its lane | adapt source | preserve N-band and source-count rules; reframe as prevalence/claim risk in new blueprint | historical spec, not active roadmap |
| `docs/superpowers/plans/2026-06-15-productization-control-plane.md` | doc | tier/authority board | current broad Backfill parked wording needs nuance but tier/authority did not change | keep | no control-plane update in Phase 0 | machine-readable state checker depends on it |
| old 2026-06-07 Backfill goal/plan/spec | docs | diagnostic/gallery provenance | already superseded for active roadmap | keep | no current reader change needed | referenced by diagnostics index |
| old 2026-06-05 Backfill gate/authority plans | docs | prior validation/authority context | historical broad-Backfill gate slices | keep | already bannered historical; may be mined as adapt source | validation provenance |
| old peak-scoring / weighted-confidence docs | docs | historical scorer designs | scoring can be mistaken for acceptance authority | downgrade later | not touched in Phase 0; inventory before any deletion | likely referenced as historical context |

## Phase 1 Result

Shadow Adapter v1 adapted the current lockbox shadow builder/tests without
creating a second case source. It added the shadow enum, truth/status enum,
manual-negative hard stop, doublet fields, source/hash/manifest checks, and
authority-lane invariants while keeping all outputs `shadow_only=true` and
`write_authority=false`.

## No Control-Plane Update

Phase 0/1 changes source-of-truth routing and shadow contract/checker artifacts
only. It does not change maturity tier, active lane, current writer authority,
ProductWriter behavior, matrix output, selected area/counting, review/replay
behavior, or broad Backfill state. Therefore no control-plane update is needed.
