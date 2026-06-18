# Backfill Quant Matrix Product Blueprint

Date: 2026-06-19
Status: `diagnostic_only` authoritative planning blueprint
Authority: active Backfill / quant-matrix roadmap. Productization tier and
current writer authority still live in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md`.

## Verdict

Backfill values are accepted quantification values, not detections and not
truth claims. The default quant matrix should include detected values plus
accepted Backfill values because downstream quantitative analysis needs usable
numeric coverage. Detection claims remain based on detected cells only.

This blueprint supersedes the 2026-06-18 evidence-lifecycle blueprint as the
active Backfill roadmap. The previous blueprint is an adapt source for evidence
chain, source hashing, and cleanup discipline, but it over-parked Backfill and
treated acceptance as a truth-import problem.

## Current Authority Boundary

Current state is unchanged by this blueprint:

- Current Backfill product authority remains exactly 511 cells.
- Broad Backfill auto-write remains parked.
- The parked item is broad uncontracted Backfill, not the product goal of
  accepted Backfill values entering the default quant matrix.
- Phase 0/1 do not change ProductWriter, matrix, workbook, selected peak,
  selected area, counted detection, GUI, default extraction, or RAW behavior.
- No control-plane update is needed unless tier, active lane, authority,
  selected values, counting behavior, ProductWriter authority, or validation
  readiness actually changes.

## Product Principles

- `Backfill` means filling a missing feature-sample cell with an accepted
  quantification value.
- Backfilled values are not detections.
- Backfilled values are not truth claims.
- Accepted Backfill values are part of the default machine-readable
  `quant_matrix`.
- Detection rate, method sensitivity, and counted detections use detected cells
  only.
- Downstream coverage, LOESS, normalization, and quantitative statistics use
  the default `quant_matrix`.
- Main matrix cells stay numeric. Provenance lives in sidecars and reports.
- Composite scores and weight tuning must not decide write authority.
- Metrics may exist for QA, sensitivity, report sorting, or future evidence
  providers, but cannot replace the evidence-chain contract.

## Evidence Chain

The durable data flow is:

```text
source trace / integration artifact
-> PeakHypothesis
-> CellBackfillDecision
-> ProductionAcceptanceManifest
-> QuantMatrixVersion
-> Gallery/Report + CellProvenance sidecar
```

Responsibilities:

| Layer | Owns | Does not own |
| --- | --- | --- |
| source trace / integration artifact | raw/smoothed trace, integration, source hashes | write authority |
| `PeakHypothesis` | hypothesis-level identity, boundary, RT/shape, integration evidence | family-wide truth |
| `CellBackfillDecision` | one `peak_hypothesis_id + sample_stem` candidate decision | matrix export |
| `ProductionAcceptanceManifest` | Backfill write-authority decision rows | evidence recomputation |
| `QuantMatrixVersion` | exact numeric output version and sidecar linkage | hidden provenance |
| Gallery/Report | explanation and review surface | write authority |

Family context is a window and grouping aid. It must not become the final
identity or write key because a family can contain multiple peaks.

## Existing Owners To Reuse

New code must reuse existing owners/helpers where available:

- `xic_extractor/peak_detection/hypotheses.py`: `PeakHypothesis`,
  `IntegrationResult`, `EvidenceVector`, and `AuditTrail`.
- `xic_extractor/alignment/product_matrix.py`: product matrix identity and
  `peak_hypothesis_id` row identity rules.
- `xic_extractor/alignment/matrix_handoff.py`: trace-to-integration handoff.
- `xic_extractor/alignment/primary_matrix_area.py`: primary matrix area policy.
- `xic_extractor/alignment/production_decisions.py`: production cell decision
  chain.
- `xic_extractor/alignment/shared_peak_identity_explanation/product_activation.py`:
  activation value row provenance and `(peak_hypothesis_id, sample_stem)`
  uniqueness patterns.
- `xic_extractor/tabular_io.py`: TSV reading/writing, scalar parsing, and
  file hashing helpers.

Do not duplicate identity, hash, source-row, TSV parsing, or sample-stem
canonicalization logic inside one-off scripts. If a helper is missing, add the
thinnest helper near the owning module.

## Acceptance Vocabulary

Production acceptance:

```text
acceptance_decision =
  accept_basic_backfill |
  accept_strict_backfill |
  require_review |
  reject_backfill |
  not_evaluated
```

Shadow adapter:

```text
shadow_decision = accept | flag | reject | not_scored
```

Truth/status:

```text
truth_status =
  not_truth_claimed |
  manual_negative |
  external_truth_positive |
  external_truth_negative |
  unresolved
```

Default machine-accepted Backfill rows use `truth_status=not_truth_claimed`.
Only an explicit manual, standard, or validated oracle artifact may set an
external truth status.

Acceptance basis:

```text
acceptance_basis =
  machine_basic |
  machine_strict |
  manual_review |
  external_oracle |
  not_applicable
```

Manual review can close a strict path, but it must not become a basic path:
`manual_review` pairs with `accept_strict_backfill`.

## Authority Lane Invariants

Shadow lane:

```text
shadow_only=true
write_authority=false
matrix_write_allowed=false
```

Production accepted rows:

```text
shadow_only=false
write_authority=true
matrix_write_allowed=true
acceptance_decision in {accept_basic_backfill, accept_strict_backfill}
```

Production non-write rows:

```text
acceptance_decision in {require_review, reject_backfill, not_evaluated}
matrix_write_allowed=false
```

Hard-fail contradictions:

- `shadow_only=true` with `write_authority=true`.
- `shadow_only=true` with `matrix_write_allowed=true`.
- `shadow_decision=accept` mapped directly to matrix write permission.
- `not_scored` in production `acceptance_decision`.
- `not_evaluated` in shadow `shadow_decision`.

## ProductionAcceptanceManifest v1

The production acceptance manifest is the only Backfill artifact that can grant
`write_authority=true`.

Primary key:

```text
peak_hypothesis_id + sample_stem
```

`feature_family_id` is context/provenance only. A row without a formal
`peak_hypothesis_id` cannot be accepted for matrix write.

Minimum columns:

| Group | Columns |
| --- | --- |
| identity | `peak_hypothesis_id`, `sample_stem`, `feature_family_id` |
| decision | `acceptance_decision`, `acceptance_basis`, `truth_status`, `shadow_only`, `write_authority`, `matrix_write_allowed` |
| value | `quant_value`, `quant_value_source`, `matrix_area_source` |
| counts/context | `detected_count`, `backfilled_count`, `quant_available_count`, `missing_count`, `backfill_fraction`, `prevalence_flags` |
| blockers/closure | `hard_blocker_rule_ids`, `triggered_risk_rule_ids`, `closure_rule_ids`, `decision_reason`, `next_evidence_needed` |
| doublet | `doublet_status`, `reference_side`, `doublet_allowed`, `doublet_source_relpath`, `doublet_source_sha256` |
| provenance | `source_artifact_relpath`, `source_artifact_sha256`, `source_row_sha256`, `manifest_sha256`, `schema_version`, `acceptance_contract_version` |

Paths should be repo/run-root relative. Hashes are the content identity.

## Hard Blockers

These block Backfill matrix writes:

- cell-level `manual_negative`;
- missing `peak_hypothesis_id`;
- missing source path/hash/row hash/manifest hash;
- missing identity anchor or expected window;
- invalid boundary, apex outside boundary, or non-recomputable integration;
- unresolved, right-side, unclear, or reference-side-mismatched doublet;
- accepted value derived only from naked `alignment_cells.tsv:area`;
- direct shadow/report/gallery/candidate artifact trying to write.

`manual_negative` v1 is hard only at cell scope:
`peak_hypothesis_id + sample_stem`. Family-level notes are review flags unless
an explicit future schema says `negative_scope=family_wide`.

## Strict And Report-Only Risks

Strict closure is risk-specific, not a global giant checklist.

| Risk | Required handling |
| --- | --- |
| weak/unstable boundary | strict closure via boundary stability or reintegration agreement |
| RT/shape deviation | strict closure via RT/shape consistency evidence |
| side-sensitive doublet | strict closure only if reference side is resolved and allowed |
| missing overlay only | do not block if trace/integration provenance is reconstructable |
| missing trace/integration provenance | hard blocker |
| low seed / high Backfill dependency | report-only prevalence uncertainty |

Low detected support and high Backfill dependency do not alone block accepted
quant values. They downgrade prevalence/detection claims and must be visible in
sidecar, row summary, and gallery/report.

Seed-floor logic should be adapted as a prevalence/claim signal:

- `N < 20`: seed prevalence not applicable; do not claim pass.
- `20 <= N < 80`: `seed_floor=max(2, floor(N * 0.05))`.
- `N >= 80`: `seed_floor=max(4, floor(N * 0.05))`.
- Passing seed floor does not grant write authority.
- Failing seed floor does not by itself reject a cell-level accepted quant
  value.

## Value And Trace Rules

- Matrix value must come from an accepted value row with provenance, not a naked
  cell `area`.
- The primary matrix area source is Gaussian-smoothed morphology /
  Gaussian15-positive-ASLS-residual provenance where available.
- Raw trace is auxiliary review evidence and should not overturn the primary
  smoothed trace by itself.
- Resolver mode/source must be recorded, but resolver research is a separate
  validation lane. Resolver details do not replace acceptance closure.
- Missing/failed acceptance leaves the quant matrix cell empty/NA. Never fill
  unaccepted missing cells with `0`.

## Output Contracts

Default Phase 3 target:

- `quant_matrix.tsv/csv`: numeric matrix containing detected plus accepted
  Backfill values.
- `cell_provenance`: one row for every non-empty quant matrix cell, at minimum
  all detected and accepted Backfill values.
- `row_summary`: row-level detected/backfilled/available/missing counts and
  interpretation flags.
- detected-only view must be reconstructable from `quant_matrix +
  cell_provenance`; a physical detected-only matrix is optional unless a
  downstream contract requires it.

Invariants:

- Every non-empty quant matrix cell joins to exactly one provenance row.
- Every `cell_provenance` row with `write_authority=true` appears in the quant
  matrix unless an explicit export-scope exception is recorded.
- `detected_count` excludes Backfill.
- `quant_available_count = detected_count + accepted_backfilled_count`.
- Backfill coverage does not raise identity confidence.

## Phase Roadmap

### Phase 0 - Blueprint And Cleanup Map

Status: active in this turn.

Objective:

Create the authoritative Backfill/quant-matrix blueprint and cleanup map. Do
not implement shadow adapter or production manifest code in Phase 0.

Done when:

- This blueprint is the active reading target.
- Active README, roadmap, and handoff point here.
- 2026-06-18 evidence-lifecycle blueprint is downgraded to superseded/adapt
  source.
- Cleanup map classifies active conflicts as `delete`, `downgrade`, `adapt`,
  or `keep`.
- Control plane update is explicitly not needed unless tier/lane/authority
  changed.

Verification:

- focused grep for retired active wording;
- `uv run python scripts/check_productization_state.py`;
- `git diff --check`;
- secret/local-path scan on changed docs.

### Phase 1 - Shadow Scoring Contract Adapter v1

Objective:

Contain the existing lockbox shadow/scoring direction so it cannot become
truth, reviewer completion, or write authority.

Inputs:

- `docs/superpowers/validation/lockbox_shadow_automation_cases_v1.tsv` is the
  only 72-case source.
- Existing shadow experiment JSON and builder may be adapted for source/hash
  and checker patterns.

Must add:

- `shadow_decision={accept,flag,reject,not_scored}`;
- truth/status enum with owner-clean as non-authoritative challenge only;
- manual negative plus accept is a hard stop;
- row-level doublet fields: status, reference side, allowed, source;
- right/unclear/unresolved doublet cannot accept;
- source paths/hash and manifest sha;
- all outputs `shadow_only=true`, `write_authority=false`;
- `may_satisfy_reviewer_slot2=false`;
- `single_owner_evidence_is_truth_completion=false`.

Forbidden:

- no second independent case manifest;
- no scorer run;
- no RAW/85RAW;
- no ProductWriter, matrix, workbook, selected peak/area, counting, GUI, or
  default extraction changes;
- no broad Backfill revival;
- no shadow score as truth or authority.

Verification:

- existing lockbox check-only command;
- existing lockbox test file;
- new focused checker tests for enum, authority flags, manual negative,
  doublet, source/hash/manifest, and single-owner non-authority.

Readiness label: `shadow_ready` only.

### Phase 2 - ProductionAcceptanceManifest v1

Objective:

Define and check the only Backfill `write_authority=true` decision artifact.
This phase does not write the default matrix yet.

Outputs:

- manifest schema and checker;
- focused tests for identity key, provenance, hard blockers, risk-specific
  closure, authority-lane contradictions, and `require_review` evidence gaps.

Forbidden:

- no ProductWriter/output activation;
- no detected logic rewrite;
- no workbook/GUI/default extraction changes.

Readiness label: precursor to `production_candidate`.

### Phase 3 - QuantMatrixVersion Activation

Objective:

Use the production acceptance manifest to generate the default numeric
`quant_matrix` with detected plus accepted Backfill values.

Required:

- expected-diff contract;
- `cell_provenance` sidecar;
- `row_summary`;
- detected-only view reconstructability;
- focused output tests.

Public contracts may change only in this phase or a named Phase 3 slice.

Readiness label: `production_candidate` after expected-diff gates pass.

### Phase 4 - Gallery/Report Alignment

Objective:

Align the existing gallery/report surface with the manifest and sidecar. Do not
rebuild the gallery unless a missing contract requires it.

Required visibility:

- accepted Backfill vs detected;
- low seed/high Backfill dependency/prevalence uncertainty explanation;
- boundary, RT/shape, doublet, manual-negative closure;
- source paths/hashes/manifest sha;
- Gaussian-smoothed trace as primary, raw trace auxiliary;
- detected/backfilled/quant-available counts.

Gallery/report remains explanatory, not authority.

### Phase 5 - Validation And Promotion

Objective:

Separate contract correctness from scientific confidence.

Contract correctness:

- schema, hashes, manifests, authority flags, no unattributed writes,
  expected diff, enum behavior, hard blockers, sidecar completeness.

Scientific confidence:

- boundary/value accuracy, resolver behavior, low seed interpretation,
  downstream LOESS/normalization impact, real cohort behavior, heldout/oracle
  and manual review where needed.

8RAW is smoke/schema/example evidence. 85RAW or another large cohort is needed
for prevalence/cohort behavior. Neither may be run unless the active goal names
that validation tier.

## Cleanup Policy

Phase 0 cleanup is conflict-driven:

| Action | Meaning |
| --- | --- |
| `delete` | active artifact only preserves a wrong direction and has no current reader |
| `downgrade` | retain as historical/research/diagnostic provenance, not active plan |
| `adapt` | keep useful pieces, change semantics to match this blueprint |
| `keep` | already aligned or control-plane authority source |

Do not delete tracked diagnostics, validation evidence, or old specs without
source hashes and reference checks.

## Goal Template

Every follow-up goal should name:

- active phase and slice;
- this blueprint as read-first source;
- allowed files and forbidden files;
- public surface risk;
- authority/write impact;
- source-of-truth artifacts;
- verification commands;
- stop rules;
- handoff update rule;
- whether control plane needs an update.

## Anti-Goals

- No composite scoring/weight tuning for write decisions.
- No second independent lockbox case manifest.
- No shadow/report/gallery/candidate artifact as write authority.
- No owner-clean, reviewer slot 2, single-owner evidence, or shadow accept as
  truth completion.
- No broad uncontracted Backfill writer.
- No Excel workbook as the primary matrix format.
- No hidden overwrite of detected values or manual edits directly in matrix
  files.
