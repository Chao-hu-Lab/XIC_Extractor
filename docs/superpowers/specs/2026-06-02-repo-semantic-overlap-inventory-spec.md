# Repo Semantic-Overlap Inventory Spec

**Date:** 2026-06-02
**Status:** Draft v0.1 - repo-wide semantic-overlap routing inventory
**Readiness label:** `diagnostic_only`
**Related roadmap:** [Technical debt and dead-code cleanup roadmap v2](2026-06-01-technical-debt-and-dead-code-cleanup-roadmap-v2-spec.md)
**Related current-state spec:** [Peak pipeline cleanup current-state reassessment](2026-06-01-peak-pipeline-cleanup-current-state-reassessment-spec.md)
**Pilot inputs:** [C4 peak scoring evidence-decision design](2026-06-01-c4-peak-scoring-evidence-decision-design.md), [C6 alignment stage semantics design](2026-06-01-c6-alignment-stage-semantics-value-assessment-design.md)
**First follow-up design:** [Region-boundary decision owner design](2026-06-02-region-boundary-decision-owner-design.md)

## Verdict

The repo does still contain C4/C6-like semantic overlap, but not every large or
old-looking module is a duplicate owner.

The current repo-wide inventory has three high-priority overlap families:

1. C4 peak scoring vs the newer evidence / hypothesis spine.
2. C6 owner-family construction vs a future cross-sample hypothesis / family
   spine.
3. Region and boundary decision logic, where active candidate selection,
   `region_first_safe_merge`, shadow model selection, boundary hypotheses, and
   CWT proposal evidence all answer parts of the same product question:
   "which peak region should be selected and integrated?" This is a
   product/shadow overlap rather than proof that two promoted product owners are
   already competing.

The main new finding from this pass is the third family. It is the closest
non-C4/C6 equivalent to "two semantic systems for one job." Its first bounded
follow-up is now captured in
[Region-boundary decision owner design](2026-06-02-region-boundary-decision-owner-design.md).

Several other areas are real maintainability watchlist items, but currently look
like projections, diagnostics, or compatibility adapters rather than active
duplicate product owners:

- discovery `evidence_score` vs `CommonEvidence`;
- `identity_coherence` vs `shared_peak_identity_explanation`;
- matrix identity / production decision / machine-decision / candidate-gate
  projection layers;
- output, config, baseline, and signal-processing facades.

This spec authorizes no code change, schema change, resolver default change, or
diagnostic promotion. It is a routing inventory for future cleanup goals.

## Why This Spec Exists

The C4 and C6 cleanup discussions exposed a broader maintenance rule:

```text
legacy concept with still-valid product value
  -> successor spine absorbs the invariant
  -> old path becomes active policy, adapter, diagnostic, or retirement target
  -> tests move to product invariants
  -> duplicate implementation disappears
```

This repo needs the same question asked outside the original C4/C6 buckets.
The target is not "delete old code." The target is to stop maintaining two
semantically similar systems after one successor can own the product invariant.

## Inventory Method

This pass used current code and existing specs, not historical roadmap wording.

Current branch at inventory time:

```text
codex/cleanup-retirement-foundation
```

CodeGraph status at inventory time:

```text
files: 697
nodes: 13,594
edges: 30,026
index: up to date
```

Primary structural probes:

```powershell
codegraph context score_candidate
codegraph context build_peak_hypotheses
codegraph context decide_region_selection
codegraph context cluster_sample_local_owners
codegraph context build_production_decisions
codegraph context common_evidence_from_discovery_candidate
codegraph context score_discovery_evidence
codegraph context run_identity_coherence_diagnostic
codegraph context project_machine_decision
```

## Classification Rules

Use these labels for future repo-wide cleanup decisions.

| Label | Meaning | Required action |
|---|---|---|
| `active_overlap` | Two active product-path systems answer the same product question. | Pick a future owner, map invariants, write parity or behavior-change gates, then migrate. |
| `product_shadow_overlap` | A product owner and an audit/shadow successor answer the same decision, but only one is promoted today. | Keep product behavior stable; define the promotion, adapter, or retirement rule before treating shadow evidence as authority. |
| `semantic_migration_candidate` | The old path is active today, but a newer spine plausibly should own the same invariant later. | Keep now; create a migration slice only after the successor has fields, tests, and consumers. |
| `active_policy` | The old path still owns production behavior. | Characterize before movement; do not delete under cleanup-only authority. |
| `policy_projection` | The layer converts product state into output or decision wording. | Preserve public contract; promote or change only through a behavior/output spec. |
| `diagnostic_preserve` | The path supports review, validation, or root-cause evidence. | Keep under diagnostic lifecycle unless a replacement diagnostic proves parity. |
| `compatibility_facade` | The path exists to preserve imports, config, CLI, or output compatibility while delegating inward. | Keep thin; add an exit rule only when public migration is planned. |
| `resolved_retirement` | The old product path is already retired and only rejection/historical evidence remains. | Preserve rejection contract and historical readers; do not re-open without a new behavior spec. |
| `not_overlap_source_projection` | One module produces evidence and others consume or project it. | Keep source-of-truth direction clear; do not merge merely because terms overlap. |

Default to `semantic_migration_candidate` when a successor plausibly covers the
same semantics but current consumers still need proof. Default away from
`retire_candidate` unless no product, diagnostic, or compatibility invariant is
left.

## Repo-Wide Inventory

| Area | Current owners | Successor or related owner | Classification | Current decision | Exit rule |
|---|---|---|---|---|---|
| C4 peak scoring / evidence decision | `xic_extractor/peak_scoring.py`, `peak_scoring_evidence.py`, scorer tests, candidate selection through `peak_detection/facade.py` | `PeakHypothesis`, `EvidenceVector`, `CommonEvidence`, future model selection | `active_overlap` / `active_policy` | Follow the C4 design. Legacy scorer still owns production confidence, caps, and candidate selection today. | Exit only after successor tests prove selected hypothesis plus decision/explanation parity, or an approved behavior-change spec replaces parity. |
| C6 owner-family construction | `owner_clustering.cluster_sample_local_owners`, `OwnerAlignedFeature`, writer-visible owner-family IDs and evidence | Future cross-sample `TraceGroup` / `PeakHypothesis` family spine | `semantic_migration_candidate` | Keep active. It still creates matrix family structure. | Exit only after successor family spine proves `alignment_matrix.tsv`, `alignment_cells.tsv`, review/audit, no-same-sample-merge, drift-edge, conflict-split, and family-id parity. |
| Region / boundary decision stack | `selection.select_candidate`, `region_safe_merge.apply_region_first_safe_merge`, `region_model_selection.decide_region_selection`, boundary hypotheses, CWT proposal evidence | Future boundary/model-selection owner over `PeakHypothesis` / `IntegrationResult` / `AuditTrail` | `product_shadow_overlap` / `semantic_migration_candidate` | Follow the region-boundary decision owner design before code movement. | Exit requires one owner for product selection vs audit-only model selection, with tests covering shallow-valley merge, true split, wider boundary, neighbor apex, CWT-only alternatives, and unchanged public outputs unless behavior change is approved. |
| CWT evidence role | `peak_detection/cwt.py`, boundary/proposal rows, `cwt_same_apex_support` scorer labels | Morphology / boundary-hypothesis evidence family | `semantic_migration_candidate` | Keep. It is not serious standalone evidence yet, but it is not dead code. | Exit requires a role-specific CWT evidence contract: apex proposal, width prior, ridge/persistence, shoulder/overlap evidence, or explicit retirement with replacement evidence. |
| Discovery evidence score | `discovery/evidence_score.py`, discovery CSV fields, alignment edge / identity-gate consumers | `CommonEvidence`, typed evidence thresholds, identity gates | `policy_projection` / `semantic_migration_candidate` | Keep as ranking/context today. Do not treat numeric score as future identity authority. | Exit requires naming whether discovery score is only a review ranking, a weak quality prior, or replaced by typed evidence thresholds. Alignment gate consumers must be updated with parity tests. |
| `CommonEvidence` projections | `evidence_semantics.py` projections from targeted, discovery, and aligned cells | Product evidence spine | `not_overlap_source_projection` | Preserve as shared semantic projection. It is a successor surface, not a duplicate scorer by itself. | If it starts making product decisions, create a behavior spec and output/test contract. |
| Identity coherence diagnostics | `identity_coherence_adapter.py`, `identity_coherence/*`, validation scripts and outputs | Shared evidence / hypothesis diagnostics and future family-spine validation | `diagnostic_preserve` | Preserve. It can falsify confidence and expose failure modes, but it does not mutate source alignment today. | Retirement or fusion requires diagnostic status/reason/output parity and a replacement validation oracle. |
| Shared peak identity explanation | `alignment/shared_peak_identity_explanation/*`, diagnostic CLIs, activation and support sidecars | Evidence review / productization projection | `diagnostic_preserve` / `policy_projection` | Preserve, but watch size and schema coupling. It overlaps language with identity coherence but not current source alignment mutation. | Split or fuse only behind schema, CLI, and machine-readable output tests. Activation into product behavior needs separate promotion spec. |
| Matrix identity / production projection | `matrix_identity.py`, `production_decisions.py`, `machine_decision.py`, `production_candidate_gate.py`, writers | Writer-facing matrix policy and candidate-gate diagnostics | `policy_projection` | Preserve. These stages mostly transform already-built matrix/evidence into public decisions. | If candidate gate stops being `diagnostic_only`, require promotion spec, status/code contract, and matrix/review/cells/workbook parity. |
| MS2 / neutral-loss evidence source | `neutral_loss.py`, `ms2_trace_evidence.py`, candidate MS2 evidence models | Scorer, hypothesis, common evidence, diagnostics | `not_overlap_source_projection` | Preserve source-to-consumer direction. | Do not merge source calculation into scorer/diagnostics. Consumers may migrate to typed evidence fields with projection tests. |
| Baseline integration | `peak_detection/baseline.py`, `integration_audit.py`, AsLS-only compatibility guards | `IntegrationResult` and audit fields | `resolved_retirement` | AsLS is the production method. `linear_edge` remains only as rejection/historical diagnostic wording. | Do not reintroduce `linear_edge` without new behavior spec. Naming cleanup for `*_asls` audit fields is allowed only as schema-compatible docs/test cleanup or explicit schema migration. |
| Resolver modes | `legacy_savgol`, `local_minimum`, `region_first_safe_merge` in config/facade/CLI | Future evidence-based model selection | `active_policy` / `compatibility_facade` per mode | Keep all accepted modes for now. `arbitrated` is retired. | Resolver renaming or demotion needs C2 contract migration. Product behavior changes require focused validation. |
| Config facade | `xic_extractor/config.py` | `xic_extractor/configuration/*` | `compatibility_facade` | Not a semantic overlap. Keep thin public import surface. | Remove only with public migration plan. |
| Signal-processing facade | `xic_extractor/signal_processing.py` | `xic_extractor/peak_detection/*` | `compatibility_facade` | Not a semantic overlap. Keep while public import compatibility matters. | Remove only with public migration plan and import-smoke coverage. |
| Baseline facade | `xic_extractor/baseline.py` | `xic_extractor/peak_detection/baseline.py` | `compatibility_facade` | Not a semantic overlap. | Remove only with public migration plan. |
| Workbook CLI wrapper | `scripts/csv_to_excel.py` | `xic_extractor/output/*` | `compatibility_facade` | Not a semantic overlap. It is a public wrapper over output modules. | Keep wrapper; move behavior only when output tests remain authoritative. |
| Instrument QC | `instrument_qc/*` | validation/audit surfaces | `diagnostic_preserve` | Separate audit role, not current product duplicate owner. | Reclassify only if QC starts driving production RT/area/matrix correction. |
| Legacy IO adapters | `alignment/legacy_io.py` and related adapter paths | current IO/output contracts | `compatibility_facade` / adapter | Not a C6-like grouping duplicate. | Clean under IO adapter cleanup only; do not mix with semantic retirement. |

## High-Priority Follow-Up: Region / Boundary Decision Owner

This is the main new overlap candidate.

Current region-related code answers overlapping questions at different layers:

- `select_candidate(...)` chooses a candidate by strongest apex or RT-proximal
  anchor logic.
- `region_first_safe_merge` can alter local-minimum candidate intervals under
  conservative merge rules.
- `decide_region_selection(...)` produces audit/shadow verdicts such as
  `merge_suggested`, `split_supported`, `neighbor_apex_preferred`,
  `wider_boundary_preferred`, and `current_supported`.
- CWT can add proposal / same-apex support evidence, but is not a standalone
  authority.
- `PeakHypothesis` and `IntegrationResult` can carry selected and rejected
  candidate state, but they do not yet own region selection policy.

The next spec should answer:

1. Which module owns production region selection today?
2. Which module owns audit-only alternate-boundary explanation?
3. Which facts belong on `EvidenceVector`, `IntegrationResult`, or
   `AuditTrail`?
4. Does `region_first_safe_merge` become an internal constructor, an adapter
   token, or an active resolver mode?
5. What exact parity oracle proves the successor can absorb old behavior?

No implementation should delete or demote region logic until those questions
are answered.

## Watchlist Follow-Up: Discovery Score And Evidence Semantics

`discovery/evidence_score.py` still computes weighted discovery scores and
tiers. `CommonEvidence` can project many of the same facts into shared evidence
semantics. This is not yet a direct duplicate owner because discovery score is
mostly ranking/context, while `CommonEvidence` is a shared projection.

The risk is that discovery score leaks into alignment policy through gate or
edge thresholds. Future cleanup should decide whether those thresholds are:

- compatibility use of an old score;
- a weak quality prior;
- a real product evidence gate;
- or a candidate for typed evidence thresholds.

## Watchlist Follow-Up: Diagnostic Evidence Families

`identity_coherence` and `shared_peak_identity_explanation` both speak about
identity consistency, RT/mode evidence, MS1/MS2 support, and wrong-peak /
shared-peak failure modes.

They are not currently the same product owner:

- identity coherence is a diagnostic/validation bridge from alignment evidence
  into coherence records;
- shared peak identity explanation is a broader report/sidecar/productization
  evidence family.

The maintainability risk is real because the language and outputs can drift.
Future work should define one diagnostic evidence review contract or a clear
handoff between the two, but only after preserving schema, CLI, and diagnostic
status/reason parity.

## Recommended Execution Order

1. Continue C4 under its existing spec until scorer evidence facts, decision
   classes, and compatibility projections are mapped.
2. Continue C6 owner-family parity work until the successor family spine can
   prove matrix/cells parity.
3. Execute the region-boundary decision owner design in RB0/RB1-sized slices
   before moving wider region/CWT behavior.
4. Defer discovery-score cleanup until C4 typed evidence language stabilizes.
5. Defer diagnostic-family fusion until C6 and shared-identity productization
   surfaces are clearer.

This order avoids preserving duplicate systems forever while also avoiding a
large repo-wide rewrite without parity or product authority.

## Non-Goals

- Do not run broad dead-code deletion from this inventory.
- Do not re-open `linear_edge` or `arbitrated`.
- Do not delete `legacy_savgol`.
- Do not treat CWT as a deletion target.
- Do not merge diagnostic packages merely because they use similar evidence
  vocabulary.
- Do not change TSV, workbook, config, CLI, GUI, or public import contracts
  without a separate behavior or public-surface spec.

## Acceptance Criteria For This Spec

- Every C4/C6-like candidate is classified as active overlap,
  product/shadow overlap, migration candidate, diagnostic preserve, policy
  projection, compatibility facade, source/projection, or resolved retirement.
- Each high-priority candidate has an exit rule.
- The newly identified region/boundary overlap has a concrete next-spec target.
- Watchlist items do not authorize code deletion.
- Compatibility facades are explicitly separated from semantic duplication.
