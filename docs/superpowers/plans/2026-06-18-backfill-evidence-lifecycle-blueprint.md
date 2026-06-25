# Backfill Evidence Lifecycle Blueprint

Date: 2026-06-18
Status: `superseded_by_2026-06-19_backfill_quant_matrix_product_blueprint`
Authority: planning entry point only. Productization tier, active lane, and
writer authority still live in
[productization control plane](2026-06-15-productization-control-plane.md).

Superseded by:
`docs/superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md`.
Keep this file as an adapt source for evidence-chain, source-hash, and cleanup
discipline only. It is no longer the active Backfill roadmap because it
over-parked Backfill and treated acceptance as truth import instead of accepted
quantification write authority.

## Verdict

Backfill should not be treated as a value-replacement mechanism.

The durable product model is:

```text
missing or weak matrix cell
-> recoverable LC-MS evidence
-> reviewable evidence chain
-> approved evidence
-> versioned quant export
-> optional matrix write authority
```

This blueprint converts the new deep-research notes into an engineering map.
It supersedes and removes any next-step wording that would run a scorer as the
next primary productization action. Scorer-centered artifacts should not remain
as dormant durable product surfaces.

## Authority And Reading Order

Use these inputs in this order:

1. Inspect the current dirty scope before edits so user work is not lost.
2. [productization control plane](2026-06-15-productization-control-plane.md)
   for tier, lane, writer authority, broad-Backfill parked state, and public
   contract boundaries.
3. [productization status anchor](../handoffs/current/cc-framework-improvements-productization.md)
   for shared productization status when this blueprint is the active
   productization workflow. Other branches must resolve their own branch-scoped
   current handoff from the active goal or PR workflow.
4. This blueprint for phase order, stop rules, and goal contracts.
5. Named validation/adjudication artifacts cited by the active phase.
6. [deepresearch index](../../deepresearch/README.md) and its notes as design
   background only.

Deepresearch notes can motivate a new proposal, but they cannot override the
current control plane. In particular, broad Backfill auto-write remains parked
unless a future user-approved goal names an independent truth source, updates
the authority model, and passes the required validation gate.

## Product Spine

The product spine has seven layers. Each layer owns one kind of decision.

| Layer | Product Question | Allowed Output | Must Not Do |
|---|---|---|---|
| `MissingCall` | Why is this feature-sample cell not currently usable? | missing state, blocker tokens, expected mz/RT window | invent a numeric value |
| `BackfillCandidate` | Is there recoverable raw or trace evidence in the expected window? | candidate evidence with source hashes | write the matrix |
| `EvidenceChainPacket` | What evidence supports, contradicts, or blocks this candidate? | paths, hashes, status, doublet/manual-negative context | collapse evidence into a truth score |
| `ReviewItem` | What should a human or policy review? | review question, allowed actions, priority | satisfy reviewer slot 2 automatically |
| `ApprovalDecision` | Has evidence been accepted, rejected, or held? | structured decision log | modify raw evidence |
| `QuantExportPolicy` | Which accepted evidence may be selected for a matrix version? | export profile and expected-diff contract | recompute evidence |
| `QuantMatrixVersion` | What exact table was exported and why? | wide matrix plus long evidence table | hide provenance |

The key rule is:

```text
Only versioned quant export can create final quantitative matrix cells.
Backfill engines create evidence, not product values.
```

## XIC-Specific Translation

This repo already has a partial version of these layers, but the names and
authority boundaries are scattered across productization artifacts.

| Blueprint Concept | Current XIC Surface | Current Status | Next Meaning |
|---|---|---|---|
| Missing or blocked cell | 4102 blocked policy rows, including 1087 missing overlay rows | non-authority | classify as evidence gaps, not negatives |
| Backfill candidate | 4613 candidate/audit universe | non-authority | evidence recovery universe only |
| Approved write evidence | 511 generated `write_ready` rows | current writer authority | keep fixed until explicit authority update |
| Evidence chain packet | trace/overlay/hypothesis/lockbox/review artifacts | partial | make row-level chain the main product asset |
| Review item | review queue and lockbox packets | production_candidate | route unresolved rows to structured review |
| Quant export | ProductWriter matrix-only activation and expected-diff | narrow ready slices | keep behind authority manifest |

## Mature-Tool Lessons To Adopt

### Evidence Recovery

From xcms, MZmine, and Skyline-style behavior:

- Filled peaks are evidence with provenance, not native detected peaks.
- Gap filling should search an expected mz/RT region and preserve missing when
  no evidence exists.
- Manual integration should create a new evidence version, not overwrite the
  original auto peak in place.
- Export must distinguish detected, backfilled, manual, missing, rejected, and
  imputed values.

### Engineering Backfill

From AutoQC, SkylineBatch, Nextflow pipelines, and ReDU-style rebuilds:

- Freeze an input snapshot before a backfill job runs.
- Treat expensive intermediate artifacts as cacheable first-class objects.
- Use idempotency keys and source hashes before accepting a rerun result.
- Classify retryable I/O separately from deterministic scientific failures.
- Emit trace/report/timeline or equivalent execution artifacts.
- Prefer versioned rebuild/export over in-place mutation when semantics change.

### XIC Differentiation

Mature tools can fill gaps or rerun workflows. XIC's differentiation should be:

```text
auditable LC-MS evidence chain + explicit matrix-write authority boundary
```

XIC should explain why a cell is missing, recoverable, blocked, accepted,
manual, rejected, or exportable. It should not hide these states behind one
summary label, one broad threshold, or one opaque final matrix value.

## State Model

Use these states as product vocabulary before adding code:

| State | Meaning | Can Enter Product Matrix? |
|---|---|---|
| `missing_unclassified` | No structured missing reason yet | no |
| `missing_blocked` | Missing reason exists and blocks recovery | no |
| `evidence_gap` | Expected evidence path/window is unavailable | no |
| `backfill_candidate` | Recoverable signal candidate exists | no |
| `review_required` | Evidence exists but requires human or policy review | no |
| `review_rejected` | Evidence was rejected | no |
| `review_accepted` | Evidence was accepted by review or policy | not by itself |
| `write_authorized` | Accepted evidence also passed authority and expected-diff | yes, only through versioned export |
| `imputed_downstream` | Statistical fill value, not peak evidence | no production peak matrix |

This is deliberately different from a scorer enum. The state names describe
where the evidence is in the lifecycle, not how confident a model feels.

## Evidence Chain Packet v1

The next product asset should be an evidence packet, not a score run.

Minimum row-level fields:

```text
schema_version
feature_id
sample_id
source_case_id
source_manifest_path
source_manifest_sha256
current_matrix_status
missing_state
expected_mz_window
expected_rt_window
evidence_state
evidence_paths
evidence_hashes
trace_overlay_status
hypothesis_status
boundary_status
doublet_status
reference_peak_side
doublet_allowed
doublet_source_path
doublet_source_sha256
manual_negative_status
review_question
allowed_review_actions
authority_state
may_feed_product_writer
write_authority
next_required_evidence
```

Required invariants:

- `write_authority=false` unless a later authority manifest explicitly grants
  it.
- `may_feed_product_writer=false` for candidate, review, and evidence-chain
  packets.
- `may_satisfy_reviewer_slot2=false` for all evidence-chain and review-queue
  rows until a separate ApprovalDecision import explicitly records reviewer
  evidence.
- `single_owner_evidence_is_truth_completion=false`; owner-clean evidence is a
  non-authoritative challenge until independent truth is imported.
- Missing overlay rows are `evidence_gap`, not negative truth.
- Owner-clean or single-owner evidence is challenge evidence, not truth
  completion.
- Manual negative evidence can block acceptance but cannot be ignored by a
  summary label.

## Engineering Workstreams

The blueprint splits pre-authority work into five spine workstreams, followed
by one narrow authority phase and one parked engineering workstream. They can
be implemented sequentially or as separate goals, but they should not be merged
into one broad Backfill writer effort.

### Artifact Placement

| Artifact Type | Default Location | Rule |
|---|---|---|
| tier, lane, authority state | `docs/superpowers/plans/2026-06-15-productization-control-plane.md` | update only when tier, active lane, authority, output behavior, or review/replay behavior changes |
| phase specs and schemas | `docs/superpowers/specs/` | every durable TSV/JSON output needs a schema and checker before the phase is done |
| validation indexes and manifests | `docs/superpowers/validation/` | every generated row set records source paths, hashes, row count, and non-authority fields |
| cleanup inventories and narrative notes | `docs/superpowers/notes/` | every delete/demote/archive action records disposition before the action |
| orchestration entry points | `scripts/` or `tools/diagnostics/` | CLIs orchestrate; reusable schema/loading/classification/checking logic moves into package modules if reused |
| active current-state summary | `docs/superpowers/handoffs/current/` | keep short; do not turn it into a long log |

### A. Evidence Inventory

Goal: produce a complete row-level inventory of what evidence exists and what
is missing.

Outputs:

- `backfill_evidence_chain_packet_v1.tsv`
- `backfill_evidence_chain_manifest_v1.json`
- `backfill_evidence_gap_index_v1.tsv`

Acceptance:

- 4613 candidate/audit rows are accounted for.
- 511 current write-authorized rows remain unchanged.
- 1087 missing-overlay rows are marked as evidence gaps.
- No ProductWriter, matrix, workbook, selected area, or counted detection
  behavior changes.

### B. MissingCall Classifier

Goal: replace blank or blocked cells with first-class missing reasons.

Outputs:

- `missing_call_index_v1.tsv`
- blocker-token summary
- links back to source row hashes

Acceptance:

- Every missing or blocked candidate has one explicit missing state or blocker.
- `not found`, `below threshold`, `alignment failed`, `missing overlay`, and
  `manual rejected` remain distinct.

### C. Review Queue From Evidence Chain

Goal: derive review items from evidence packets, not from score thresholds.

Outputs:

- review packet update
- allowed action schema
- review-priority explanation

Acceptance:

- Priority is explainable as risk, impact, and missing evidence.
- Review-ready state only produces queue/template output.
- Review-ready state does not satisfy truth completion, reviewer slot 2, or
  ProductWriter authority.

### D. ApprovalDecision / Truth Import

Goal: import reviewer labels, manual adjudication, or another independent truth
source into a hash-linked decision log.

Outputs:

- approval decision log schema
- source manifest and source-hash record
- accepted/rejected/held/needs-evidence decision table
- checker proving candidate/review rows do not become authority

Acceptance:

- Review-ready is not accepted evidence until a decision source is imported.
- Manual negative and unsafe doublet rows cannot be accepted.
- ApprovalDecision is still non-authority until Phase 6 grants a narrow writer
  scope.

### E. Versioned Quant Export Design

Goal: design how accepted evidence would become a matrix version later.

Outputs:

- export profile spec
- long evidence table schema
- expected-diff contract

Acceptance:

- `DETECTED`, `BACKFILLED_ACCEPTED`, `MANUAL_ACCEPTED`, `MISSING_NA`,
  `BELOW_THRESHOLD`, `REJECTED`, and `IMPUTED` have distinct export semantics.
- Imputed values cannot masquerade as detected or backfilled peak areas.
- No exporter recomputes raw evidence.

### Parked. Backfill Job/Rerun Framework

Goal: only after evidence semantics are stable, design the engineering job
framework for future reruns or recovery.

Outputs:

- input snapshot schema
- idempotency key rule
- cache/resume policy
- retry class taxonomy
- execution artifact manifest

Acceptance:

- Backfill jobs are resumable and explainable.
- Deterministic scientific failures are not retried as transient I/O.
- Rebuild/versioned export is preferred over in-place product mutation.
- This workstream is not part of the primary evidence-to-authority spine unless
  a future goal explicitly pulls it in.

## Goal Execution Model

Run this blueprint one phase at a time. Each phase should become one `/goal`
with one finish line. Do not combine phases just because the same files are
nearby.

Phase state vocabulary:

| State | Meaning |
|---|---|
| `not_started` | No active goal has begun for this phase. |
| `active` | One goal is currently executing this phase. |
| `blocked` | A stop rule fired or a required source/decision is missing. |
| `done` | The phase met its `Done When` and verification was run. |
| `parked` | The phase is intentionally deferred because its entry gate is not met. |

Cadence rules:

- Start every phase by reading this blueprint, the productization control plane,
  the active branch or productization handoff, and the source artifacts named by
  the phase.
- Keep the active handoff as a short current-state snapshot, not a log.
- If a phase discovers broader cleanup, record it as follow-up unless it blocks
  the current phase.
- Do not update the control plane unless maturity tier, active lane, matrix
  authority, selected area/counting, ProductWriter authority, or review/replay
  behavior actually changes.
- No phase may run RAW/85RAW unless its `Verification` explicitly names that
  tier.
- No phase may change ProductWriter, matrix, workbook, selected peak/area,
  counted detection, GUI, or default extraction unless it is the narrow authority
  phase and the control plane is updated.

## Phase 0 - Product Direction Cleanup v1

Objective:

Remove or demote active wrong-direction surfaces so future goals follow the
evidence lifecycle instead of accumulated scorer/sidecar drift.

Entry Gate:

- This blueprint exists and is the read-first Backfill/evidence-chain plan.
- The two new deepresearch reports are indexed.
- Current dirty scope has been inspected.

In Scope:

- Active routing docs under `docs/superpowers/goals/`,
  `docs/superpowers/plans/`, `docs/superpowers/specs/`, and
  `docs/superpowers/handoffs/current/`.
- Validation or scratch artifacts that create a durable wrong-direction surface.
- Script/test diffs that only support retired scorer-centered artifacts.
- A cleanup inventory that classifies each candidate as `keep`, `delete`,
  `archive`, `rewrite`, or `demote`.

Out Of Scope:

- ProductWriter behavior.
- Matrix/workbook/selected peak/selected area/counted detection changes.
- RAW/85RAW reruns.
- Broad Backfill reopening.
- Refactoring unrelated production code.

Outputs:

- Updated active roadmap/handoff surfaces.
- Cleanup inventory under `docs/superpowers/notes/`, written before any
  delete, archive, rewrite, or demotion.
- Deleted or demoted wrong-direction scratch artifacts.

Verification:

- Focused grep finds no active scorer-centered roadmap or goal entry.
- Cleanup inventory records path, tracked/untracked state, action, reason,
  authority relevance, archive target or `not archived` reason, and source hash
  when applicable.
- Existing lockbox automation check still passes if lockbox files are touched.
- `uv run python scripts/check_productization_state.py`.
- `git diff --check`.

Done When:

- No active goal, handoff, or blueprint points future work to a scorer run,
  scorer contract, broad Backfill writer slice, or quality-blocker-derived
  writer predicate.
- A cleanup inventory accounts for every deleted, archived, rewritten, or
  demoted artifact before the action.
- The active handoff names evidence-chain packet work as the next step.
- The final response explicitly says whether a control-plane update was needed.

Stop Rules:

- Stop if a candidate cleanup item is a tracked product contract whose removal
  would change public behavior.
- Stop if the cleanup inventory cannot be written before delete, archive,
  rewrite, or demotion.
- Stop if an existing cleanup candidate should have a source hash and the hash
  cannot be captured before deletion.
- Stop if cleanup would delete validation evidence needed to explain a current
  authority boundary.
- Stop if a control-plane tier or active lane would need to change.

Handoff:

- Rewrite the active handoff after cleanup.
- Keep rejected paths only if a future agent is likely to repeat them.

Goal Seed:

```text
/goal
GOAL:
Complete Product Direction Cleanup v1 for the Backfill evidence lifecycle by
removing, archiving, rewriting, or demoting active wrong-direction surfaces that
conflict with the blueprint, without changing product behavior.

CONTEXT:
- Read docs/superpowers/plans/2026-06-18-backfill-evidence-lifecycle-blueprint.md.
- Read docs/superpowers/plans/2026-06-15-productization-control-plane.md.
- Read the productization status anchor only when this productization blueprint
  is the active workflow; otherwise resolve the branch-scoped current handoff
  named by the goal or PR workflow.
- Inspect current git dirty scope before edits.

CONSTRAINTS:
- Do not change ProductWriter, matrix, workbook, selected peak/area, counted
  detection, GUI, default extraction, RAW behavior, or broad Backfill authority.
- Do not delete evidence needed to explain the current 511-cell authority
  boundary.

DONE WHEN:
- Active roadmap/handoff/spec surfaces no longer point to scorer-centered or
  broad-writer directions.
- A cleanup inventory accounts for every deleted, archived, rewritten, or
  demoted artifact before the action.
- Handoff is a current-state snapshot.

VERIFY:
- Run focused grep for retired scorer/broad-writer active goals.
- Run uv run python scripts/check_productization_state.py.
- Run git diff --check.

STOP RULES:
- Stop if cleanup would change product behavior or require a control-plane tier
  update.
- Stop if any future delete/demote/archive action cannot be inventoried before
  the action, including source hash when applicable.
```

## Phase 1 - Backfill Evidence Chain Packet v1

Objective:

Create a read-only row-level evidence-chain packet and manifest for the current
Backfill candidate/audit universe.

Entry Gate:

- Phase 0 is done.
- The source universe is named from existing authority/adjudication artifacts,
  not reconstructed ad hoc. Default source candidates are the existing
  mechanical adjudication/status/validation artifacts named by the control
  plane; the phase goal must record exact paths, row counts, and hashes before
  generation.
- Current write authority is confirmed as 511 cells.

In Scope:

- Row-level packet generation.
- Source path/hash capture.
- Evidence status and next-required-evidence classification.
- Focused checker/tests for schema, counts, hashes, and no-authority fields.

Out Of Scope:

- RAW/85RAW.
- Scorer-centered contract/run/report.
- ProductWriter or matrix changes.
- New writer slices.
- Decision import or export policy changes.

Outputs:

- `backfill_evidence_chain_packet_v1.tsv`.
- `backfill_evidence_chain_manifest_v1.json`.
- `backfill_evidence_gap_index_v1.tsv`.
- `backfill_evidence_chain_packet_schema_v1.json`.
- `backfill_evidence_chain_manifest_schema_v1.json`.
- Builder/checker code and focused tests.

Verification:

- Packet row count matches the named source universe.
- Manifest records source paths and hashes.
- Checker enforces schema, row count, source hashes,
  `may_feed_product_writer=false`, and `write_authority=false` unless the row
  is already in the current 511-cell authority baseline.
- 511 current write-authorized rows remain exactly 511.
- 1087 missing-overlay rows remain evidence gaps, not negative truth.
- Focused tests include a negative case proving a packet row cannot imply
  ProductWriter or matrix authority.
- `uv run python scripts/check_productization_state.py`.
- `git diff --check`.

Done When:

- Every source row has a packet row or a fail-closed blocker.
- Every packet has evidence state, authority state, source hash, and next
  required evidence.
- Every durable TSV/JSON output has a schema/checker/test gate.
- No output can feed ProductWriter or change matrix/workbook values.
- Handoff records the new packet paths and verification.

Stop Rules:

- Stop if the source universe cannot be tied to existing source hashes.
- Stop if row counts disagree with the current authority/adjudication baseline.
- Stop if any packet field implies truth completion or write authority.

Handoff:

- Record packet paths, source hashes, row counts, validation, and remaining
  evidence gaps.

Goal Seed:

```text
/goal
GOAL:
Build Backfill Evidence Chain Packet v1 as a read-only, source-hash-linked
packet for the current Backfill candidate/audit universe.

CONTEXT:
- Read the Backfill Evidence Lifecycle Blueprint.
- Read the control plane for current 511-cell authority and parked broad
  Backfill state.
- Read the active branch or productization handoff and named
  validation/adjudication artifacts.

CONSTRAINTS:
- No RAW/85RAW.
- No scorer-centered artifacts.
- No ProductWriter, matrix, workbook, selected peak/area, counted detection,
  GUI, default extraction, or authority update.

DONE WHEN:
- Packet, manifest, and evidence-gap index exist.
- All source rows are accounted for and hash-linked.
- Packet and manifest schemas exist and are enforced by focused checker tests.
- 511 authority remains unchanged.
- Missing-overlay rows are evidence gaps, not negatives.

VERIFY:
- Run focused packet/checker tests.
- Run uv run python scripts/check_productization_state.py.
- Run git diff --check.

STOP RULES:
- Stop on source-hash mismatch, count mismatch, or any write-authority drift.
```

## Phase 2 - MissingCall / Evidence Gap Index v1

Objective:

Turn unresolved, blank, blocked, or missing-evidence rows into first-class
missing/evidence-gap states.

Entry Gate:

- Phase 1 packet exists and validates.
- Every unresolved row has a stable packet identifier.

In Scope:

- Missing-state enum and schema.
- Evidence-gap index derived from Phase 1 packets.
- Blocker-token normalization.
- Checker/tests for state completeness and no numeric fill.

Out Of Scope:

- Searching RAW for new evidence.
- Filling values.
- Decision import.
- Matrix export.

Outputs:

- `missing_call_index_v1.tsv`.
- `missing_call_schema_v1.json` or equivalent schema section.
- Summary of blocker/missing-state counts.

Verification:

- Every unresolved or blocked packet maps to exactly one missing/evidence-gap
  state.
- `not_detected`, `below_threshold`, `no_signal_in_expected_window`,
  `filtered_out`, `alignment_failed`, `missing_overlay`, `review_rejected`, and
  `not_applicable` stay distinguishable where source evidence supports them.
- No missing state produces a numeric value.

Done When:

- Missing/evidence-gap states are complete, machine-checkable, and hash-linked
  to Phase 1 packet rows.
- Handoff records which buckets need evidence recovery versus review.

Stop Rules:

- Stop if a missing state would require RAW evidence not present in the packet.
- Stop if missing-overlay rows are treated as negative labels.
- Stop if the enum collapses scientifically different causes into one
  ambiguous state.

Handoff:

- Record state counts, unresolved buckets, and the next evidence source needed.

Goal Seed:

```text
/goal
GOAL:
Build MissingCall / Evidence Gap Index v1 from the Phase 1 evidence-chain
packet, without filling values or changing product outputs.

DONE WHEN:
- Every unresolved/blocked packet has one machine-checkable missing or evidence
  gap state.
- No numeric fill or ProductWriter authority is introduced.
- Missing-overlay rows remain evidence gaps.

VERIFY:
- Run focused missing-state tests/checker.
- Run uv run python scripts/check_productization_state.py.
- Run git diff --check.

STOP RULES:
- Stop if classification needs absent RAW evidence or collapses distinct
  missing causes into one vague bucket.
```

## Phase 3 - Review Queue From Evidence Chain v1

Objective:

Derive review items from evidence-chain packets and MissingCall states, not
from scorer thresholds.

Entry Gate:

- Phase 1 packet validates.
- Phase 2 missing/evidence-gap index validates.
- Review-ready versus evidence-recovery rows are separated.

In Scope:

- Review item schema or schema update.
- Allowed actions.
- Review question generation from packet fields.
- Priority explanation based on evidence risk, downstream impact, and missing
  evidence.

Out Of Scope:

- Reviewer-slot completion.
- Truth-label completion.
- ProductWriter authority.
- Matrix/export changes.

Outputs:

- Review queue derived from evidence-chain packets.
- Review decision log template/update, not a completed decision log.
- Checker/tests proving review-ready rows remain non-authority and
  non-accepted until Phase 5 imports a decision source.

Verification:

- Every review item links to a packet row and source hash.
- Every review item has one review question and allowed actions.
- Review queue output cannot record acceptance; acceptance belongs to Phase 5.
- Manual negatives and doublets remain hard safety gates.

Done When:

- Review-ready rows are separated from evidence-gap rows.
- No review output can grant ProductWriter authority, satisfy reviewer slot 2,
  or complete truth.
- Handoff records review queue paths and remaining evidence-recovery buckets.

Stop Rules:

- Stop if the review queue tries to route evidence-gap rows as review-ready.
- Stop if review-ready state is treated as accepted evidence.
- Stop if review output would alter matrix/workbook values.
- Stop if reviewer slot 2 or truth completion is implied.

Handoff:

- Record review-ready counts, evidence-gap counts, allowed actions, and
  non-authority constraints.

Goal Seed:

```text
/goal
GOAL:
Build Review Queue From Evidence Chain v1 so review packets derive from
evidence-chain and missing-state records, not scorer thresholds.

DONE WHEN:
- Review items are packet-linked, hash-linked, and have allowed actions.
- Evidence-gap rows are not routed as review-ready.
- Review-ready remains non-authority and non-accepted until Phase 5 imports a
  decision source.

VERIFY:
- Run focused review-queue/checker tests.
- Run uv run python scripts/check_productization_state.py.
- Run git diff --check.

STOP RULES:
- Stop if review-ready state touches matrix/workbook output, truth completion,
  reviewer slot 2, or ProductWriter authority.
```

## Phase 4 - Versioned Quant Export Contract v1

Objective:

Specify and check how accepted evidence could later become a matrix version,
before any writer implementation changes.

Entry Gate:

- Phase 1 packet exists.
- Phase 3 review queue non-authority boundary is clear.
- A future export decision needs a contract before implementation.

In Scope:

- Export profiles and value-type semantics.
- Long evidence table schema.
- Expected-diff contract.
- Checker/tests for export contract consistency.

Out Of Scope:

- ProductWriter implementation.
- Matrix output changes.
- New authority.
- RAW/85RAW.

Outputs:

- Versioned quant export spec.
- Long evidence table schema.
- Expected-diff contract/checker.

Verification:

- `DETECTED`, `BACKFILLED_ACCEPTED`, `MANUAL_ACCEPTED`, `MISSING_NA`,
  `BELOW_THRESHOLD`, `REJECTED`, and `IMPUTED` are distinct.
- Every future non-NA production cell must be explainable by selected evidence
  or imputation policy.
- Imputed values cannot masquerade as detected/backfilled/manual peak area.

Done When:

- Export contract can be checked without changing current product outputs.
- Handoff records that writer implementation remains blocked until authority
  exists.

Stop Rules:

- Stop if the contract requires modifying current ProductWriter behavior.
- Stop if export semantics hide provenance.
- Stop if expected-diff cannot be expressed before implementation.

Handoff:

- Record export profiles, schemas, expected-diff gates, and implementation
  blockers.

Goal Seed:

```text
/goal
GOAL:
Write Versioned Quant Export Contract v1 for future Backfill evidence export,
without changing ProductWriter or matrix outputs.

DONE WHEN:
- Export profiles, value types, long evidence schema, and expected-diff
  requirements are specified and checkable.
- No current product output changes.

VERIFY:
- Run focused schema/checker tests.
- Run uv run python scripts/check_productization_state.py.
- Run git diff --check.

STOP RULES:
- Stop if implementation changes are needed before the export contract is
  checkable.
```

## Phase 5 - ApprovalDecision / Truth Import v1

Objective:

Import reviewer labels, manual adjudication, or another independent truth
source into a hash-linked decision log, without granting writer authority.

Entry Gate:

- Phase 1 packet exists and validates.
- Phase 3 review queue exists, or another independent decision source is named.
- Every decision source has a path, content hash, owner, and decision status
  vocabulary.
- Manual negative and doublet safety fields exist in the packet or source.

In Scope:

- ApprovalDecision schema.
- Decision-source manifest.
- Decision status enum: `accepted`, `rejected`, `held`,
  `needs_more_evidence`, `not_reviewed`.
- Source-hash-linked accept/reject/hold import.
- Checker/tests proving candidate-only and review-ready rows remain
  non-authority.

Out Of Scope:

- ProductWriter output.
- Matrix/export changes.
- Reviewer-slot completion by a single-owner evidence source.
- Treating owner-clean, AI challenge, or missing-overlay evidence as truth.
- RAW/85RAW unless a later authority goal names that tier.

Outputs:

- `approval_decision_log_v1.tsv`.
- `approval_decision_manifest_v1.json`.
- `approval_decision_schema_v1.json`.
- Checker/tests for source hashes, status enum, manual negatives, doublets, and
  no-authority fields.

Verification:

- Every accepted/rejected/held row links to one Phase 1 packet row and one
  decision source hash.
- Manual negative plus accepted decision is a hard stop.
- Unsafe or unclear doublet rows cannot be accepted.
- Owner-clean or single-owner evidence remains a non-authoritative challenge.
- Checker enforces `may_satisfy_reviewer_slot2=false` and
  `single_owner_evidence_is_truth_completion=false` unless a separate
  independent decision source explicitly satisfies those fields.
- Decision outputs keep `write_authority=false` and
  `may_feed_product_writer=false`.
- Focused tests include candidate-only, review-ready-only, manual-negative, and
  doublet-negative cases.

Done When:

- A decision log can explain which evidence was accepted, rejected, held, or
  still needs evidence.
- No decision output can feed ProductWriter or alter matrix/workbook values.
- Handoff records decision source paths, hashes, status counts, and unresolved
  rows.

Stop Rules:

- Stop if a review queue row is treated as accepted without a decision source.
- Stop if manual negative or unsafe doublet evidence can be accepted.
- Stop if single-owner evidence is treated as truth completion.
- Stop if any decision implies ProductWriter authority.

Handoff:

- Record decision-log paths, source hashes, accepted/rejected/held counts,
  safety-gate failures, and remaining truth gaps.

Goal Seed:

```text
/goal
GOAL:
Build ApprovalDecision / Truth Import v1 so reviewer labels, manual
adjudication, or another independent truth source become a hash-linked
non-authority decision log.

DONE WHEN:
- Every decision row is packet-linked and source-hash-linked.
- Manual negatives and unsafe/unclear doublets cannot be accepted.
- Owner-clean or single-owner evidence remains non-authoritative challenge
  evidence unless an independent decision source is imported.
- Decision outputs cannot grant ProductWriter, matrix, workbook, reviewer slot
  2, or truth completion authority by themselves.

VERIFY:
- Run focused ApprovalDecision schema/checker tests.
- Run uv run python scripts/check_productization_state.py.
- Run git diff --check.

STOP RULES:
- Stop if review-ready, candidate-only, manual-negative, unsafe-doublet, or
  single-owner rows can become authority.
```

## Phase 6 - Narrow Write Authority v1

Objective:

Only after accepted evidence and export policy exist, grant a narrow, explicit
ProductWriter authority update.

Entry Gate:

- Phase 1 packet exists and validates.
- Phase 5 ApprovalDecision / Truth Import artifact exists and validates, or
  another independent truth source is named with equivalent source-hash-linked
  acceptance evidence.
- Phase 4 export contract exists.
- The user explicitly approves an authority goal.

In Scope:

- Authority manifest update.
- ProductWriter expected-diff gate for the exact scope.
- Focused writer tests.
- Appropriate real-data/oracle validation tier.

Out Of Scope:

- Broad Backfill.
- Quality-blocker-derived writer expansion.
- Implicit authority from review-ready rows, scores, sidecars, candidate
  evidence, owner-clean challenge evidence, or single-owner evidence.

Outputs:

- Updated authority manifest/control-plane entry.
- Expected-diff artifact.
- ProductWriter code/tests only for the named scope.

Verification:

- Focused writer tests.
- Expected-diff pass.
- Control-plane update.
- 8RAW/85RAW/targeted/manual validation only if named by the authority goal.

Done When:

- The exact authority scope is explicit, expected-diff passing, and recorded in
  the control plane.
- Every changed matrix cell is explainable from evidence chain and export
  policy.

Stop Rules:

- Stop if the authority scope cannot be expressed as a short human-readable
  rule.
- Stop if evidence is candidate-only, review-ready-only, owner-clean-only, or
  single-owner-only.
- Stop if manual negative or unsafe doublet evidence is within the accepted
  scope.
- Stop if expected-diff includes duplicate, missing, unexpected, non-eligible,
  non-written, unchanged, or blank blockers.
- Stop if the work would broaden Backfill by quality blockers.

Handoff:

- Record exact authority scope, validation tier, expected-diff result, and
  residual risk.

Goal Seed:

```text
/goal
GOAL:
Grant Narrow Write Authority v1 for one explicitly approved Backfill evidence
scope, using evidence-chain packets, accepted evidence, versioned export policy,
authority manifest update, and expected-diff validation.

DONE WHEN:
- The exact scope is recorded in the control plane and authority manifest.
- Expected-diff passes for the named scope.
- ProductWriter tests cover the named scope only.

VERIFY:
- Run focused ProductWriter/expected-diff tests.
- Run the validation tier named by the goal.
- Run uv run python scripts/check_productization_state.py.
- Run git diff --check.

STOP RULES:
- Stop if the scope is broad, quality-blocker-derived, candidate-only,
  review-ready-only, single-owner-only, unsafe-doublet, manual-negative, or
  cannot be explained as a short product rule.
```

## Optional Parked Workstream - Backfill Job / Rerun Framework Contract v1

Objective:

Design the future engineering framework for resumable backfill/recovery jobs
only after evidence semantics, decision import, and export boundaries are
stable, or after the user explicitly approves a bounded job framework goal.

Entry Gate:

- Phase 1 packet exists.
- Phase 2 missing/evidence-gap states exist.
- Phase 4 export contract exists or is explicitly not needed for the bounded
  job type.
- The goal names one bounded job type and the product decision it supports.

In Scope:

- Input snapshot schema.
- Idempotency key/content-hash rule.
- Cache/resume policy.
- Retry class taxonomy.
- Execution artifact manifest schema.
- Worker/lease design if implementation is approved later.

Out Of Scope:

- Running a new broad Backfill job.
- ProductWriter output.
- New RAW/85RAW validation unless a later implementation goal names it.
- In-place mutation of locked outputs.

Outputs:

- Backfill job/rerun framework spec.
- Input snapshot schema.
- Execution artifact manifest schema.
- Checker/tests for idempotency key, content hash, retry class, source hash,
  and no-authority fields.

Verification:

- Deterministic scientific failures are not retried as transient I/O.
- Job output cannot become ProductWriter authority without Phase 6.
- Cache/resume behavior is source-hash or content-hash linked.
- Checker rejects mutable-path-only idempotency.
- Checker enforces non-authority output fields.

Done When:

- A future implementation goal can execute one bounded job type without
  redefining idempotency, retry, cache, or artifact rules.
- Required schemas/checkers/tests exist; prose-only is not sufficient.

Stop Rules:

- Stop if the design starts a broad rerun without a named product decision.
- Stop if idempotency depends only on filenames or mutable paths.
- Stop if retry classes blur I/O failure and scientific failure.
- Stop if any job artifact implies ProductWriter authority.

Handoff:

- Record which job type is ready for implementation, required schemas/checkers,
  and which evidence is still missing.

Goal Seed:

```text
/goal
GOAL:
Write optional Backfill Job / Rerun Framework Contract v1 for one bounded
evidence-recovery job type, with snapshot, idempotency, retry, cache, and
execution-artifact rules.

DONE WHEN:
- Input snapshot and execution manifest schemas exist.
- Idempotency/content-hash and retry/no-authority checkers pass.
- The framework does not run or authorize broad Backfill.

VERIFY:
- Run focused job-framework schema/checker tests.
- Run uv run python scripts/check_productization_state.py.
- Run git diff --check.

STOP RULES:
- Stop if the contract implies ProductWriter authority, mutable-path-only
  idempotency, blurred retry classes, or a broad rerun without a named product
  decision.
```

## Stop Rules

Stop immediately if a future plan:

- treats backfill candidate evidence as product truth;
- turns a summary label into a matrix-writing signal;
- opens broad Backfill writer authority from quality blockers;
- uses imputation as peak area evidence;
- lets manual integration overwrite original peaks in place;
- writes ProductWriter output without a versioned export policy;
- creates a second independent case manifest when a source manifest already
  exists;
- treats missing-overlay rows as negative labels;
- treats review-ready, owner-clean, or single-owner evidence as truth
  completion;
- lets manual-negative or unsafe/unclear doublet rows become accepted evidence;
- uses 85RAW cost as a substitute for a named product decision.

## First Recommended Goal

Name:

```text
Backfill Evidence Chain Packet v1
```

Objective:

```text
Create a read-only row-level evidence-chain packet and manifest for the current
Backfill candidate/audit universe, preserving current 511-cell writer authority
and keeping broad Backfill parked.
```

Explicit non-goals:

- no scorer-centered contract, run, or report
- no RAW or 85RAW
- no ProductWriter
- no matrix/workbook/selected peak/area/counting changes
- no new writer slices
- no control-plane tier change unless authority really changes later

Done when:

- every source row is accounted for;
- every packet has source path/hash and evidence status;
- packet/manifest schemas exist and checker tests enforce source hashes,
  row counts, and no-authority fields;
- every missing/evidence-gap row has a next-required-evidence field;
- current 511 write-authorized rows remain exactly 511;
- broad Backfill remains parked;
- handoff points here as the next Backfill read.

## Read This First

Future agents should start here before touching Backfill, review packets,
missing-overlay recovery, or matrix-write authority. The
control plane remains the authority for tiers and writer surface; this file is
the product blueprint for how the next engineering goals should be shaped.
