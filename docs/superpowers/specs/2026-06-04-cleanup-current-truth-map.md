# Cleanup Current Truth Map

**Date:** 2026-06-04
**Branch:** `codex/cleanup-retirement-foundation`
**Status:** Current control map v0.6 - implementation-backed snapshot, not a behavior spec
**Readiness label:** `diagnostic_only`
**Use before:** any C3, C4, C6, Region, dead-code, semantic-overlap, or
public-behavior cleanup work

## Purpose

This is the control map for the cleanup branch. It exists because the repo has
too many overlapping plans and old names can look like dead code even when they
still carry product invariants.

This document does not approve implementation. It tells future work where the
current owner is, where the successor candidate is, and which work must stop
until a behavior contract exists.

If this map conflicts with a phase-specific behavior addendum, use this map for
routing and use the addendum for product behavior.

## Plain Verdict

Stop broad cleanup, but also stop indefinite shadowing. The goal is explicit
transformation: successor modules absorb the useful capability and product
invariants of legacy owners, fix their pain points, then retire or reduce the
legacy owner to a thin compatibility adapter.

The main problem is not "old code still exists"; it is unclear decision
ownership between legacy product paths and the newer evidence/hypothesis/decision
spine.

Only continue one ownership lane at a time. A cleanup slice is allowed only when
it can name:

1. the current product owner;
2. the successor owner or adapter boundary;
3. the public surface touched;
4. the parity or expected-diff evidence;
5. the stop rule if behavior would change.

Tests protect product invariants, not old module shapes. If a test only protects
the legacy implementation detail after the successor has absorbed the invariant,
migrate it to the successor surface or delete it. Keep old-owner tests only for
public compatibility, explicit rejection/migration behavior, or parity during an
active transition.

## Sources Checked

- [Technical debt and dead-code cleanup roadmap v2](2026-06-01-technical-debt-and-dead-code-cleanup-roadmap-v2-spec.md)
- [Peak pipeline cleanup current-state reassessment](2026-06-01-peak-pipeline-cleanup-current-state-reassessment-spec.md)
- [Repo semantic-overlap inventory](2026-06-02-repo-semantic-overlap-inventory-spec.md)
- [C4 / C6 / Region public behavior productization design](2026-06-02-public-behavior-retirement-productization-design.md)
- [Region-boundary public behavior addendum](2026-06-02-region-boundary-public-behavior-addendum.md)

Quick code reality checks on 2026-06-04 confirmed that the successor primitives
exist in package code, `xic_extractor/alignment/clustering.py` and
`xic_extractor/alignment/backfill.py` are absent, and package code does not
import `tools.diagnostics`.

## Settled State

| Area | Current truth | Do not reopen unless a new behavior spec says so |
|---|---|---|
| `linear_edge` | Retired from product quantitation and writer schema. It may remain in historical tests, rejection paths, and ASLS audit evidence. | Do not restore product area integration, final matrix value, or public output columns. |
| `arbitrated` | Retired resolver mode. Existing configs should fail or migrate according to the retirement contract. | Do not add it back as a hidden fallback or compatibility alias. |
| Old event-first C6 modules | `xic_extractor/alignment/clustering.py` and `xic_extractor/alignment/backfill.py` are already absent. | Do not recreate broad event-first grouping/backfill modules just to make old specs executable. |
| `legacy_savgol` | Still valid as current candidate-formation / compatibility behavior. It is not dead code. | Do not delete or rename it during cleanup. |
| `local_minimum` and CWT | Evidence/proposal sources. They can support or challenge decisions; they are not final product authority by themselves. | Do not promote or delete them without a specific evidence-chain contract. |
| `region_first_safe_merge` | Public compatibility token for narrow adjacent-WIS safe-merge behavior. | Do not treat it as generalized model selection or delete it as stale naming. |

## Current Ownership Map

| Lane | Current product owner | Successor or partial spine | Current disposition |
|---|---|---|---|
| Region / boundary | Resolver path behind `find_peak_and_area(...)`, with `region_first_safe_merge` as opt-in safe-merge behavior. | `RegionSelectionDecision` exists and should carry product-facing decision fields through adapters. | Closest executable lane, but only inside the Region addendum table. |
| C4 scoring / confidence / reason | `peak_detection.candidate_scoring.score_candidate(...)` now owns candidate evidence assembly. `peak_scoring.py` is a compatibility facade only. | `peak_detection.scoring_models`, `peak_detection.candidate_selection`, `peak_detection.scoring_quality`, `peak_detection.scoring_reason`, `peak_detection.scoring_metrics`, `peak_detection.scoring_cwt_support`, `PeakHypothesisSelectionDecision`, `EvidenceVector`, `CommonEvidence`, and decision-semantics projections own the migrated slices. | Legacy `peak_scoring.py` is retired as an active product-decision owner; do not add behavior back there. |
| C6 cross-sample owner / delivery | `OwnerAlignedFeature`, `owner_clustering.py`, claim/owner/matrix delivery behavior, and writers. | `CrossSamplePeakGroupHypothesis` exists as a successor candidate. | Characterize and prove parity before extracting shared grouping primitives. |
| Matrix identity / row delivery | Existing alignment matrix, review, audit, and workbook delivery contracts. | Matrix identity and production-decision projections are future policy surfaces. | Preserve unless an expected-diff contract names changed rows and downstream semantics. |
| Diagnostics | `identity_coherence`, shared-peak explanation, safe-merge comparison, targeted reliability, CWT/proposal audits, and similar tooling. | Product-adjacent evidence surfaces, not product owners. | Preserve or lifecycle-manage; do not let writers recompute product decisions from diagnostics. |

## Detailed Module Link Map

### Region / Boundary

Current flow:

```text
peak_detection.facade.find_peak_and_area
  -> find_peak_candidates
       -> legacy_savgol / local_minimum resolver code
  -> peak_scoring.score_candidate and select_candidate_with_confidence
  -> _apply_region_first_safe_merge_if_enabled
       -> region_safe_merge.apply_region_first_safe_merge
       -> region_model_selection.decide_region_selection
       -> RegionSelectionDecision.product_action
       -> only safe_merge_eligible can promote selected bounds/area
  -> PeakDetectionResult
```

Public/audit propagation:

```text
RegionSelectionDecision
  -> PeakRegionAuditSummary
  -> alignment.cell_region_audit.with_region_audit
  -> AlignedCell.region_decision_* fields
  -> alignment_cells.tsv / workbook review surfaces
```

What is integrated already:

- `region_first_safe_merge` must pass through
  `RegionSelectionDecision.product_action == "safe_merge_eligible"` before it
  changes selected bounds/area.
- `RegionSelectionDecision` fields are carried to `PeakRegionAuditSummary`,
  `AlignedCell`, TSV, and XLSX outputs.

What is not integrated yet:

- `find_peak_and_area(...)` is still the product entry point and still starts
  from resolver modes and legacy candidate selection.
- Verdicts such as `wider_boundary_preferred`, `neighbor_apex_preferred`, and
  `split_supported` are visible but not promoted. They remain
  `behavior_change_required` until a stronger oracle exists.
- Region facts are not yet fully stored as `IntegrationResult`, `AuditTrail`,
  `EvidenceVector`, or `PeakHypothesis` ownership.

Smallest real migration slice:

- Make Region verification prove that writers and alignment cells consume
  `RegionSelectionDecision` fields directly, not reconstructed shadow fields.
- Then choose one additional verdict class to productize or explicitly
  externalize. Do not add another broad Region spec before this check.

### C4 / Candidate Selection / Confidence / Reason

Current product flow:

```text
peak_detection.facade.find_peak_and_area
  -> peak_detection.candidate_scoring.score_candidate
  -> peak_detection.candidate_selection.select_candidate_with_confidence
  -> PeakDetectionResult.peak / confidence / reason / candidate_scores
```

Successor flow:

```text
PeakDetectionResult + candidate_scores
  -> build_peak_hypotheses
       -> PeakHypothesis
       -> IntegrationResult
       -> EvidenceVector
       -> AuditTrail
       -> CommonEvidence / EvidenceDecisionSemantics
  -> model_select_peak_hypothesis
       -> PeakModelSelectionResult
       -> product_switch_allowed gate
  -> selected_handoff_peak
       -> selected_hypothesis
       -> selection_decision_from_hypothesis
  -> ExtractionResult.reported_rt / reported_peak_area / confidence / reason
```

What is integrated already:

- `ExtractionResult.reported_rt` and `reported_peak_area` prefer
  `selected_hypothesis.integration` when present.
- `selection_decision_from_hypothesis` can project confidence/reason from the
  successor selected hypothesis.
- `model_select_peak_hypothesis` can allow product switching when the
  expected-diff gate approves it.
- C4-1 completed the no-MS2 detection-policy slice:
  `ExtractionConfig.count_no_ms2_as_detected` now flows through
  `build_production_peak_hypotheses` / `build_peak_hypotheses` into
  `EvidenceSignalSet`, and `EvidenceDecisionSemantics` owns whether
  `no_ms2_cap` becomes not-counted.
- For that C4-1 slice, `PeakHypothesisSelectionDecision` can mark
  `legacy_projection_status="successor_owned"` and
  `compatibility_oracle="successor_evidence_decision_semantics"` when
  `missing_ms2_policy_not_counted` is the active reason.
- C4-2 moved selection models and candidate arbitration into successor modules:
  `Confidence`, `ScoredCandidate`, `ScoringContext`, confidence conversion, and
  `select_candidate_with_confidence(...)` now live under
  `peak_detection.scoring_models` / `peak_detection.candidate_selection`.
  `peak_scoring.py` keeps only compatibility re-exports for that surface.
- C4-3 moved trace-quality and hard-quality policy into
  `peak_detection.scoring_quality`. Internal consumers now import
  `candidate_quality_penalty`, `candidate_selection_quality_penalty`,
  `hard_quality_flags`, and trace-quality cap helpers from the successor module;
  `peak_scoring.py` only calls or re-exports those helpers for compatibility.
- C4-4 moved public reason/breakdown projection, RT/local-morphology metrics,
  local S/N cache, CWT same-apex support, and `score_candidate(...)` evidence
  assembly into successor modules:
  `peak_detection.scoring_reason`, `peak_detection.scoring_metrics`,
  `peak_detection.scoring_cwt_support`, and
  `peak_detection.candidate_scoring`.
- Package internals now import C4 behavior from successor modules. A repository
  scan found no package code importing `xic_extractor.peak_scoring`; only the
  compatibility test checks that legacy imports still resolve to successor
  functions/classes.

What is not integrated yet:

- `peak_scoring.py` is no longer an active scorer owner; it is a thin
  compatibility facade for legacy imports.
- `build_peak_hypotheses` is mostly projection from legacy-selected candidates
  and successor-owned candidate scores. It does not yet own evidence extraction
  independently outside the no-MS2 detection-policy handoff and migrated scoring
  modules.
- `PeakHypothesisSelectionDecision.legacy_projection_status` remains
  `active_policy_remaining`, and its compatibility oracle remains
  `legacy_peak_scoring_current_oracle`, for the broader hypothesis-selection
  handoff. The old `peak_scoring.py` module is not that oracle anymore.
- Product switching is intentionally gated by expected-diff approval, public
  output impact checks, and targeted role/paired-ISTD rules.

Completed migration slice:

- `no_ms2_cap` / `count_no_ms2_as_detected` now belongs to successor decision
  semantics for not-counted classification.
- Tests were migrated so this invariant no longer depends on legacy
  `reason="review only"` wording.
- Selection models, candidate arbitration, quality policy, public
  reason/breakdown, RT/local-morphology metrics, local-S/N cache, CWT support,
  and score/evidence assembly now belong to successor modules.
- `peak_scoring.py` preserves import compatibility only. Do not add new logic or
  tests that require it as a product owner.

Next real migration slice:

- Continue from the successor modules toward the hypothesis/decision spine:
  decide which candidate-scoring evidence labels should become
  `EvidenceVector` / `EvidenceDecisionSemantics` inputs rather than projected
  candidate-score metadata.
- Preserve public `ExtractionResult` confidence/reason parity unless an
  expected-diff gate explicitly approves a change.

### C6 / Cross-Sample Grouping / Delivery

Current constructor flow:

```text
alignment.pipeline
  -> build_sample_local_owners
  -> owner_clustering.cluster_sample_local_owners
       -> construct_cross_sample_peak_group_hypotheses
       -> CrossSamplePeakGroupHypothesis
       -> OwnerAlignedFeature compatibility facade
```

Current delivery flow:

```text
OwnerAlignedFeature / OwnerGroupDeliveryFeature
  -> owner_backfill.build_owner_backfill_cells
  -> owner_matrix.build_owner_alignment_matrix
  -> claim_registry.apply_ms1_peak_claim_registry
  -> primary_consolidation / recentering
  -> AlignmentMatrix / AlignedCell
  -> alignment_matrix.tsv / alignment_cells.tsv / alignment_review.tsv / workbook
```

What is integrated already:

- Cross-sample group construction already goes through
  `CrossSamplePeakGroupHypothesis`.
- `OwnerAlignedFeature` now carries successor metadata such as
  `group_hypothesis_id`, `public_family_id`, `group_construction_role`,
  `group_delivery_role`, and `group_membership_source`.
- `owner_group_delivery.py` defines a protocol-shaped delivery surface that
  exposes successor group and gap-fill fields to cells and writers.

What is not integrated yet:

- `owner_clustering.py` still returns the concrete `OwnerAlignedFeature` facade.
- `owner_matrix.build_owner_alignment_matrix` still consumes delivery features
  and emits `AlignedCell`; it is not a direct
  `CrossSamplePeakGroupHypothesis` -> matrix pipeline.
- Claim registry, primary consolidation, backfill supersession, gap-fill state,
  missing-observation state, and public writers still depend on the delivery
  facade/cell schema.
- The existing `owner_family_successor_contract.py` names many invariants as
  successor-owned, but its exit rule still keeps `OwnerAlignedFeature` until
  concrete adapter consumers migrate or accept the protocol directly.

Smallest real migration slice:

- Convert one downstream consumer from concrete `OwnerAlignedFeature` to the
  `OwnerGroupDeliveryFeature` protocol or to `CrossSamplePeakGroupHypothesis`
  directly.
- Keep matrix TSV/XLSX parity for that consumer.
- Only then retire one concrete-field dependency from `OwnerAlignedFeature`.

## Why Integration Keeps Stalling

The repeated stall is caused by a valid but expensive pattern:

```text
legacy owner makes decision
  -> successor model records or explains the decision
  -> output projects both old and new fields
  -> gates require proof before successor can change product behavior
  -> next phase adds more review/projection instead of moving one invariant
```

This protects scientific output, but it also means a successor model can exist
for a long time without becoming the owner. The project needs a stronger default
for owner-migration tasks:

- after a successor model exists;
- after the public surface is named;
- after the parity or expected-diff test is named;

the next step should be one bounded ownership transfer, not another broad
shadow/report/addendum pass.

Legacy-bound tests are part of the stall when they protect old implementation
shape instead of product behavior. For every migration slice, classify tests as:

| Test class | Action |
|---|---|
| Product invariant | Move to the successor owner surface and keep it. |
| Public compatibility or rejection contract | Keep, but make the compatibility purpose explicit. |
| Temporary parity during active migration | Keep only until the successor path owns the invariant, then remove or narrow it. |
| Diagnostic evidence | Keep under diagnostic lifecycle rules, not as production authority. |
| Obsolete implementation detail | Delete when the successor test covers the product invariant. |

## Where Old And New Are Fighting

### Region

Old surface: resolver names and shadow fields make it look as if
`region_first_safe_merge` or `shadow_verdict` owns the decision.

New surface: `RegionSelectionDecision` carries decision status, class, product
action, selected ids, evidence, reasons, and baseline method.

Current rule: Phase 1 may promote only the existing adjacent-WIS safe-merge
class after safe gates pass. Everything else is `no_change`, `review_only`, or
`behavior_change_required`.

Allowed next work: verify implementation against the Region addendum. Do not add
new automatic boundary, apex, split, CWT, or wider-envelope behavior.

### C4

Old surface: `peak_scoring.py` still owns score, cap, confidence, reason, and
candidate selection behavior.

New surface: evidence/hypothesis/selection-decision models exist, but they do
not yet own the public candidate selection contract end to end.

Current rule: do not split `peak_scoring.py` for line count. First determine
which legacy concepts are product invariants, diagnostics, projections, or dead
implementation details.

Allowed next work: C4 semantic-survival audit or behavior spec. No broad module
split until characterization proves public parity.

### C6

Old surface: owner-first delivery DTOs and writers still decide what downstream
alignment consumers receive.

New surface: `CrossSamplePeakGroupHypothesis` exists, but delivery, missing
observation, gap-fill/backfill, row identity, and provenance are not fully
successor-owned.

Current rule: no generic grouping refactor until current grouping-like stages
are characterized and golden parity exists.

Allowed next work: C6 inventory/parity only. Do not migrate matrix delivery or
gap-fill semantics under a cleanup label.

### Matrix And Identity Projections

Old surface: current TSV/workbook/matrix contracts.

New surface: machine decisions, candidate gates, matrix identity, and shared
identity explanations.

Current rule: these are policy projections unless explicitly promoted. They can
make decisions reviewable, but they do not automatically replace current matrix
or workbook contracts.

Allowed next work: preserve and document. Changing schemas, row identity,
numeric matrix values, confidence, or reason text needs a behavior spec.

## Allowed Next Work

| Work type | Allowed examples | Required evidence |
|---|---|---|
| Docs-only control | Tighten this map, add entry links, remove stale "implementation not started" wording when current code contradicts it. | `git diff --check`, link smoke, stale-wording scan. |
| Region contract verification | Check that code and tests follow the Region addendum disposition table. | Focused output-contract tests; no RAW run unless it can close a named decision. |
| C3 consumer inventory plus migration | Map which consumers still use legacy candidate/boundary DTOs, then move one consumer to the successor model or name why it cannot move. | Inventory plus one parity-backed migration. |
| C4 semantic-survival migration | Classify one scorer concept, then move that concept into the successor decision owner. | Characterization tests before and after the move. |
| C6 characterization plus adapter migration | Map one grouping/delivery stage, then migrate one concrete consumer from `OwnerAlignedFeature` to the protocol or successor group. | Golden parity around the smallest safe stage. |
| Diagnostic lifecycle cleanup | Keep, externalize, retire, or summarize diagnostic tools. | Lifecycle decision and index/handoff update. |

## Do Not Do Until Reapproved

- Do not run broad deletion across old-looking names.
- Do not delete `legacy_savgol`, `local_minimum`, CWT, or `region_first_safe_merge`.
- Do not rename resolver/config tokens for aesthetics.
- Do not split `peak_scoring.py` just because it is large.
- Do not extract generic C6 grouping primitives before characterization parity.
- Do not change selected peak, bounds, area, confidence, reason, matrix identity,
  workbook schema, TSV schema, or config behavior under a cleanup label.
- Do not launch 8RAW, 85RAW, or expensive validation unless the result can close
  a named decision and has the required preflight.
- Do not let diagnostic writers recompute product decisions from legacy audit
  columns.

## Single Recommended Next Step

Freeze implementation and review this control map plus the Region addendum as
the current branch snapshot.

After that, choose exactly one lane:

1. Region Phase 1 verification against the addendum;
2. C3 consumer inventory and one parity-backed migration proposal;
3. C6 characterization before any grouping refactor;
4. C4 next-invariant migration before any scorer split.

Recommended lane after the C4-1 no-MS2 slice: continue C4 one invariant at a
time. Do not split `peak_scoring.py` structurally until enough scorer policy has
successor owners and the remaining module can honestly shrink into a compatibility
adapter.

## Stop Rules

Stop and write or update a behavior spec if a proposed task:

- changes selected peak, selected area, selected bounds, confidence, reason,
  matrix identity, workbook schema, TSV schema, or config behavior;
- cannot name the current product owner and successor owner;
- needs a new CWT, WIS, RT, apex, split, or envelope rule to win automatically;
- treats a diagnostic artifact as proof of production behavior;
- would preserve a legacy DTO by hiding new semantics inside it without an
  explicit adapter contract.

## Source Priority

1. This map for cleanup routing and stop/go control.
2. Phase-specific behavior addenda for product behavior.
3. Roadmap and semantic-overlap inventory for classification.
4. Historical notes for rationale only.
