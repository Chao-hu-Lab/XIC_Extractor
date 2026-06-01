# C6 - Alignment Stage Semantics And Value Assessment Design

**Date:** 2026-06-01
**Status:** Phase 5 design closeout v0.2 — C6-A characterization inventory
**Readiness label:** `diagnostic_only`
**Supersedes for implementation:** [C6 alignment grouping consolidation](2026-05-24-peak-pipeline-cleanup-alignment-grouping-consolidation-spec.md)
**Execution contract:** [Peak pipeline cleanup one-goal phase contract](2026-06-01-peak-pipeline-cleanup-one-goal-phase-contract-spec.md)
**Current-state input:** [Peak pipeline cleanup current-state reassessment](2026-06-01-peak-pipeline-cleanup-current-state-reassessment-spec.md)
**Output contract input:** [Untargeted alignment output contract](2026-05-11-untargeted-alignment-output-contract.md)

## Verdict

C6 is not a generic grouping consolidation phase anymore.

The current alignment pipeline has several stages that look like grouping, but
they do not all have the same job. Some build candidate/event clusters, some
build owner families, some arbitrate duplicate MS1 peak claims, some decide
winner/loser rows, some deliver matrix identity, and some only explain or audit
evidence.

The next C6 goal is therefore:

```text
inventory alignment stages, name their product value and semantics, and choose
no refactor unless a later slice has a parity oracle and proves identical
semantics.
```

The old `group_by_tolerance`, `eject_and_reattach`, and `tie_break_sort`
primitive plan is historical rationale only. It must not be implemented as the
default C6 direction.

Phase 5 selects no C6-B/C implementation slice. Current evidence supports
keeping the alignment stages distinct until a specific row gains a stronger
characterization test and parity oracle. The recommended next C6 action is
optional C6-B contract hardening for one named high-risk stage, not broad helper
extraction.

## Design Decision

Use C6 as a value-assessment and stage-contract phase.

Do not merge modules just because they all group rows. Each stage must first be
classified by the product decision it protects:

- candidate/event grouping;
- sample-local owner construction;
- owner-family grouping;
- event-family grouping;
- backfill scope or matrix delivery;
- claim arbitration;
- winner/loser consolidation;
- matrix identity policy;
- diagnostic or evidence review.

After classification, each stage gets one disposition:

- `keep_as_stage` - stage has distinct product semantics and should remain a
  named pipeline step.
- `rename_or_document` - behavior is useful, but the name or docs hide its role.
- `contract_harden` - keep behavior, add characterization tests or clearer
  invariants before future edits.
- `targeted_cleanup_candidate` - small cleanup may be safe after parity surfaces
  are named.
- `retire_candidate` - possible only when no production, diagnostic, handoff,
  or compatibility value remains and a removal plan exists.

Every C6-A row also gets a separate C6 targetability label:

- `primitive_candidate` - cross-stage helper extraction might be possible after
  identical semantics and parity are proven.
- `stage_local_cleanup_only` - cleanup may be possible inside the stage, but not
  through a shared primitive.
- `contract_only` - the stage protects product or public-output policy; C6 can
  document or harden it, not consolidate it.
- `diagnostic_preserve` - the module is diagnostic/evidence support and must not
  be mistaken for dead code.
- `out_of_scope_adapter` - IO, backend, validation, or wrapper code whose
  cleanup belongs to a separate adapter-focused spec.

## Why This Replaces The Old C6 Plan

The old C6 spec saw repeated mechanics: tolerance checks, tie-break sorting,
candidate attachment, duplicate detection, and ejection. Those mechanics are
real, but similarity at the loop level is not enough.

Current alignment behavior also includes:

- graph-like relationships between duplicate or near-duplicate identities;
- sample-local owner and cross-sample family semantics;
- review-only identity conflict evidence;
- per-sample MS1 peak claim arbitration;
- primary/provisional/audit matrix identity decisions;
- loser row demotion and audit traceability;
- downstream `alignment_matrix.tsv`, `alignment_review.tsv`, and
  `alignment_cells.tsv` delivery.

A blind primitive extraction could preserve line-level structure while erasing
the product reason each stage exists. C6 must first prove which behavior is
mechanical duplication and which behavior is domain policy.

## Phase Shape

### C6-A - Stage Semantics And Value Assessment Inventory

**Type:** docs-only / `diagnostic_only`

Purpose:

- map every grouping-looking alignment stage to its actual role;
- identify which stages are production behavior, diagnostic evidence, or
  compatibility support;
- name the smallest future cleanup candidate, or explicitly close C6 as
  docs-only if no safe cleanup exists.

Allowed changes:

- write a current-state inventory table;
- add module-level notes or spec links if they clarify stage ownership;
- name characterization tests or golden parity surfaces for later phases.

Forbidden changes:

- moving source code;
- extracting generic helpers;
- changing selected alignment rows, winner/loser decisions, owner membership,
  matrix identity, TSV schemas, or review reasons.

DONE WHEN:

- every listed stage has a semantics class, product value statement, public
  surface, current test or missing-test note, risk if merged, disposition, C6
  targetability, and required next action / exit rule;
- every CodeGraph module family row is covered by at least one inventory row, or
  explicitly marked `out_of_scope_adapter` with a reason;
- the inventory identifies either one parity-backed C6-B/C follow-up or says no
  refactor is justified now;
- old C6 generic-primitives wording remains marked historical.

### C6-B - Stage Contract Hardening

**Type:** characterization tests / no behavior change

C6-B is optional and only follows C6-A if one or more stages have valuable but
underspecified behavior.

Allowed changes:

- add focused characterization tests for one named stage;
- document invariants that must survive later cleanup;
- name the exact TSV or row-level oracle used by the test.

Forbidden changes:

- changing stage output;
- broad helper extraction;
- turning diagnostic-only evidence into production behavior.

### C6-C - Targeted Cleanup Candidate

**Type:** narrow cleanup / parity required

C6-C is optional and only follows C6-A/C6-B if the inventory proves that a small
cleanup has identical semantics and a clear oracle.

Allowed changes:

- remove local duplication inside one stage;
- rename private helpers if tests prove public behavior is unchanged;
- extract a helper only when it is stage-local or when identical cross-stage
  semantics have been proven.

Forbidden changes:

- generic `group_by_tolerance`, `eject_and_reattach`, or `tie_break_sort`
  extraction by default;
- changing alignment matrix/review/cells values;
- changing winner/loser, owner, primary/provisional, review, duplicate, or
  claim semantics.

## Inventory Template

Every C6-A row must use this shape:

| Field | Meaning |
| --- | --- |
| Stage | Human-readable pipeline stage name. |
| Module / entrypoint | Exact module and function or public stage hook. |
| Pipeline position | Where it runs relative to clustering, owner build, backfill, matrix build, claim registry, and primary consolidation. |
| Purpose / product value | Why this stage exists for the product, not just what loop it runs. |
| Input model | Main objects or tables consumed. |
| Output model | Main objects, cells, rows, or decisions emitted. |
| Public surfaces affected | TSVs, review rows, audit fields, matrix identity, or downstream behavior affected by this stage. |
| Semantics class | One of the approved classes in this spec. |
| Tests / golden surfaces | Existing test, missing characterization test, or TSV parity surface. |
| Risk if merged/extracted | What product semantics could be erased by a generic helper or module merge. |
| Disposition | `keep_as_stage`, `rename_or_document`, `contract_harden`, `targeted_cleanup_candidate`, or `retire_candidate`. |
| C6 targetability | `primitive_candidate`, `stage_local_cleanup_only`, `contract_only`, `diagnostic_preserve`, or `out_of_scope_adapter`. |
| Required next action / exit rule | Exact action that closes the row, or the condition that reclassifies it after C6-A/C6-B. |

## Phase 5 C6-A Stage Inventory

This table is the Phase 5 closeout inventory. It is intentionally compact; each
row preserves the required C6-A fields by naming product value, public surface,
oracle or missing oracle, risk if merged, disposition, targetability, and exit
rule.

| Stage | Module / entrypoint | Product value / public surface | Semantics class | Oracle or missing oracle | Risk if merged/extracted | Disposition / targetability | Required next action / exit rule |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Candidate event clustering | `xic_extractor.alignment.clustering.cluster_candidates` | Builds candidate/event clusters used by event-first alignment and review outputs. | candidate/event grouping | Existing clustering tests plus `alignment_review.tsv` / event-first output parity if touched. | A generic grouping helper could erase anchor, compatibility, ejection, and tie-break policy. | `keep_as_stage` / `stage_local_cleanup_only` | No C6 cleanup now; only local helper cleanup after event-first parity is named. |
| Sample-local owner build | `xic_extractor.alignment.ownership.build_sample_local_owners` | Assigns MS1 trace ownership per sample and emits owner/ambiguous records used by production alignment. | sample-local owner construction | Existing ownership and pipeline backend tests; `event_to_ms1_owner.tsv` and `ambiguous_ms1_owners.tsv` parity when emitted. | Shared grouping would hide RAW-backed ownership and ambiguous-owner semantics. | `keep_as_stage` / `contract_only` | Preserve as named stage; future edits need owner assignment parity. |
| Owner family grouping | `xic_extractor.alignment.owner_clustering.cluster_sample_local_owners` | Builds cross-sample owner families and edge evidence for owner-first matrix delivery. | owner-family grouping | Missing stronger family-edge characterization; owner-edge and matrix row parity required. | Complete-link gates and edge evidence could be flattened into tolerance-only grouping. | `contract_harden` / `stage_local_cleanup_only` | Optional C6-B candidate: add family-edge characterization, then reclassify to keep or targeted local cleanup. |
| Pre-backfill consolidation | `xic_extractor.alignment.pre_backfill_consolidation.consolidate_pre_backfill_identity_families` | Consolidates identity families before backfill scope selection. | identity-family consolidation before backfill | Existing alignment tests plus missing row-level pre/post consolidation fixture. | Generic merge could change which family enters backfill. | `contract_harden` / `stage_local_cleanup_only` | Add focused consolidation fixture before cleanup; otherwise keep as stage. |
| Event-first backfill | `xic_extractor.alignment.backfill.backfill_alignment_matrix` | Constructs event-first matrix cells for the alternate alignment path. | event-first backfill and cell construction | Event-first tests plus `alignment_cells.tsv` parity if touched. | Owner-first and event-first backfill semantics could be conflated. | `contract_harden` / `stage_local_cleanup_only` | Preserve until event-first product role is revalidated; no shared primitive now. |
| Owner backfill | `xic_extractor.alignment.owner_backfill.build_owner_backfill_cells` | Rescues owner-family cells and feeds owner matrix delivery. | backfill scope and matrix cell creation | Owner backfill tests, process backend tests, `alignment_cells.tsv` parity. | Generic backfill helper could change detected/rescued/absent labels. | `keep_as_stage` / `contract_only` | No C6 cleanup now; future edits require cell status parity. |
| Owner alignment matrix | `xic_extractor.alignment.owner_matrix.build_owner_alignment_matrix` | Delivers owner-first alignment matrix rows. | matrix delivery | Matrix tests and `alignment_matrix.tsv` parity. | Merge could change row ordering, family identity, or downstream schema. | `keep_as_stage` / `contract_only` | Preserve as delivery stage. |
| MS1 peak claim registry | `xic_extractor.alignment.claim_registry.apply_ms1_peak_claim_registry` | Arbitrates duplicate MS1 peak claims and claim assignment fields. | claim arbitration | Existing claim tests plus missing duplicate-claim parity fixture for affected rows. | Shared grouping could change winner/duplicate assignment. | `contract_harden` / `contract_only` | Optional C6-B candidate: harden claim assignment parity before any cleanup. |
| Primary family consolidation | `xic_extractor.alignment.primary_consolidation.consolidate_primary_family_rows` | Selects primary rows, demotes losers, and preserves loser audit traceability. | winner/loser consolidation | Existing primary consolidation tests plus `alignment_review.tsv` / loser audit parity. | Generic consolidation could erase winner/loser and near-duplicate demotion semantics. | `contract_harden` / `contract_only` | Optional C6-B candidate: strengthen winner/loser fixture; no helper extraction now. |
| Matrix identity decisions | `xic_extractor.alignment.matrix_identity.build_matrix_identity_decisions` | Classifies primary/provisional/audit matrix identity. | matrix identity policy | Matrix identity and production decision tests; matrix/review/cells parity. | Merging with grouping would turn identity policy into tolerance mechanics. | `keep_as_stage` / `contract_only` | Preserve; behavior changes require separate spec. |
| Production decisions | `xic_extractor.alignment.production_decisions.build_production_decisions` | Projects writer-facing row/cell decisions. | writer-facing production projection | Production decision and writer tests; output-level oracle matrix. | Generic output grouping could change public TSV values. | `keep_as_stage` / `contract_only` | Preserve as public projection owner. |
| Event-first feature family path | `feature_family.build_ms1_feature_families`, `family_integration.integrate_feature_family_matrix` | Maintains alternate/event-first feature-family integration path. | event-family grouping and matrix integration | Missing current product-role note plus event-first parity if touched. | Could be mistaken for dead code or merged into owner-first path without contract. | `contract_harden` / `stage_local_cleanup_only` | Revalidate role before cleanup; no retirement in Phase 5. |
| Near-duplicate folding | `xic_extractor.alignment.folding.fold_near_duplicate_clusters` | Folds near-duplicate clusters before downstream review. | near-duplicate folding behavior | Folding tests plus near-duplicate row parity if touched. | Shared primitive could alter fold threshold/order semantics. | `contract_harden` / `stage_local_cleanup_only` | Add threshold/order fixture before local cleanup. |
| Near-duplicate audit | `xic_extractor.alignment.near_duplicate_audit.count_near_duplicate_pairs` | Diagnostic evidence for near-duplicate behavior. | diagnostic or evidence review | Diagnostic count tests or report parity if touched. | Could be falsely retired as non-production despite validation value. | `keep_as_stage` / `diagnostic_preserve` | Preserve diagnostic evidence; retirement requires no-use evidence. |
| Identity gates | `xic_extractor.alignment.identity_gates.*` | Applies identity/evidence gate policy using `CommonEvidence`. | identity/evidence gate policy | Identity gate tests and decision parity. | Grouping consolidation would hide evidence policy behind mechanics. | `keep_as_stage` / `contract_only` | Preserve; policy changes need behavior spec. |
| Identity coherence adapter | `xic_extractor.alignment.identity_coherence_adapter.run_identity_coherence_diagnostic` | Bridges production alignment evidence into identity-coherence diagnostics. | diagnostic or evidence review | Identity coherence adapter/pipeline tests. | Could be mistaken as duplicate diagnostic code despite current validation role. | `keep_as_stage` / `diagnostic_preserve` | Preserve diagnostic bridge. |
| Identity coherence diagnostics | `xic_extractor.alignment.identity_coherence.*` | Emits diagnostic verdicts/status/reasons for coherence review. | diagnostic or evidence review | Identity coherence diagnostic tests and output parity. | Broad consolidation could erase diagnostic semantics. | `keep_as_stage` / `diagnostic_preserve` | Preserve; retirement requires diagnostic replacement. |
| Shared peak identity explanation | `xic_extractor.alignment.shared_peak_identity_explanation.*` | Explains shared-peak/wrong-peak root causes for review. | diagnostic or evidence review | Existing explanation tests or diagnostic report parity if touched. | Could be misclassified as dead code; it provides evidence for product decisions. | `keep_as_stage` / `diagnostic_preserve` | Preserve unless a replacement diagnostic is accepted. |

## CodeGraph Module Function Map

This map is based on the 2026-06-01 CodeGraph-assisted scan of
`xic_extractor/alignment/`. It exists to keep C6-A from inspecting only the
modules that visibly "cluster" rows.

CodeGraph snapshot at this update:

- index status: up to date;
- alignment package files: 113;
- repository nodes: 13,848;
- repository edges: 31,043.

| Module family | Modules / entrypoints | C6-A role | Phase 5 disposition / oracle or out-of-scope reason |
| --- | --- | --- | --- |
| Pipeline orchestration | `pipeline.run_alignment`, `_build_event_first_matrix` | sequence owner; records where each stage runs and which output path it can affect | `contract_only`; preserve as sequence owner. Oracle: `tests/test_run_alignment.py`, pipeline output/atomic-write tests, and output-level artifact parity when routing is touched. |
| Event-first grouping path | `clustering.cluster_candidates`, `backfill.backfill_alignment_matrix`, `feature_family.build_ms1_feature_families`, `family_integration.integrate_feature_family_matrix` | alternate/event-first matrix path; inventory before deciding whether it is compatibility, diagnostic, or still product-relevant | `contract_harden`; no cleanup until event-first product role and row parity are named. Oracle: clustering/backfill/feature-family/family-integration tests plus matrix/cells parity if writer-facing. |
| Owner-first production path | `ownership.build_sample_local_owners`, `owner_clustering.cluster_sample_local_owners`, `pre_backfill_consolidation.consolidate_pre_backfill_identity_families`, `backfill_scope.select_backfill_features`, `owner_backfill.build_owner_backfill_cells`, `owner_matrix.build_owner_alignment_matrix` | current production path that constructs owner families, selects backfill scope, rescues cells, and builds matrix rows | `keep_as_stage` or `contract_harden` per row above. Oracle: owner/backfill/matrix tests plus `alignment_matrix.tsv` and `alignment_cells.tsv` parity. |
| Claim and consolidation policy | `claim_registry.apply_ms1_peak_claim_registry`, `primary_consolidation.consolidate_primary_family_rows` | duplicate claim, winner/loser, demotion, and loser audit semantics; not generic grouping | `contract_harden`; optional C6-B only after winner/loser and claim-assignment fixtures are named. Oracle: claim registry/primary consolidation tests plus review/cells parity. |
| Matrix identity and production projection | `cell_quality.build_cell_quality_decisions`, `matrix_identity.build_matrix_identity_decisions`, `promotion_policy.classify_backfill_promotion`, `machine_decision.project_machine_decision`, `production_decisions.build_production_decisions`, `production_candidate_gate.evaluate_production_candidate_gate` | production/provisional/audit policy and writer-facing row/cell decisions; C6 can only characterize these, not merge them into grouping helpers | `keep_as_stage` / `contract_only`; policy changes need separate behavior spec. Oracle: matrix identity, production decision, production gate, and public output parity tests. |
| Compatibility and scoring helpers | `compatibility.*`, `family_compatibility.*`, `edge_scoring.evaluate_owner_edge`, `drift_evidence.*`, `rt_normalization.*` | evidence and compatibility helpers used by stages; inventory their consumers before moving or sharing them | `contract_harden`; local cleanup only after consumers and parity fixture are named. Oracle: compatibility/edge evidence/drift tests plus owner-edge parity when emitted. |
| Output and public delivery | `tsv_writer.write_alignment_matrix_tsv`, `tsv_writer.write_alignment_review_tsv`, `tsv_writer.write_alignment_cells_tsv`, `xlsx_writer.write_alignment_results_xlsx`, `html_report.write_alignment_review_html`, `pipeline_outputs.write_outputs_atomic`, `output_rows.*` | public contract projection; any C6-B/C oracle must name which writer-facing values are protected | `keep_as_stage` / `contract_only`; no grouping consolidation. Oracle: writer tests, output-level tests, and the Public Output Oracle Matrix in this spec. |
| Tier2 trace and candidate-gate sidecars | `tier2_trace_producer.build_tier2_trace_evidence_rows`, `production_candidate_gate.evaluate_production_candidate_gate`, `tools/diagnostics/tier2_raw_trace_reread_producer.py`, `tools/diagnostics/provisional_backfill_candidate_gate.py` | diagnostic/gate sidecar family that can support production-candidate decisions and shared-peak evidence review | `diagnostic_preserve` / `contract_only`; no grouping consolidation. Oracle: sidecar schema/value/provenance parity plus candidate-gate decision parity. |
| Diagnostics and evidence review | `identity_coherence_adapter.run_identity_coherence_diagnostic`, `identity_coherence/*`, `identity_coherence_validation/*`, `shared_peak_identity_explanation/*`, `near_duplicate_audit.count_near_duplicate_pairs`, `cell_region_audit.*` | maintained diagnostic/evidence code; do not classify as dead code merely because it is outside the primary matrix path | `keep_as_stage` / `diagnostic_preserve`; no retirement without replacement evidence. Oracle: diagnostic verdict/status/reason parity and existing diagnostic tests. |
| IO, backend, and validation adapters | `csv_io.*`, `raw_sources.*`, `ms1_index_source.*`, `process_backend.*`, `legacy_io.*`, `validation_pipeline.*`, `validation_writer.*`, `validation_compare.*` | adapter and validation surfaces; C6 should not move them unless a separate IO/backend cleanup slice owns the public contract | `out_of_scope_adapter`; belongs to IO/backend/validation cleanup, not C6 grouping. Oracle must be defined in that separate adapter spec. |
| Models and contracts | `models.*`, `matrix.*`, `ownership_models.*`, `config.AlignmentConfig`, `output_levels.AlignmentOutputLevel` | shared contracts; inventory consumers before renaming fields, moving dataclasses, or changing compatibility imports | `contract_only`; no renames or field movement in C6. Oracle: import/schema/consumer parity and output-level tests if touched. |

Initial C6-A classification from this map:

- `keep_as_stage`: owner-first production path stages, claim registry, primary
  consolidation, matrix identity, production projection, public writers.
- `contract_harden`: event-first path, pre-backfill consolidation,
  near-duplicate folding, backfill scope, promotion/machine-decision
  projection, compatibility helpers with broad consumers.
- `rename_or_document`: modules whose names hide whether they are product
  policy or diagnostic projection after C6-A inventory.
- `targeted_cleanup_candidate`: only a helper or module with identical
  semantics, named consumers, and a parity oracle.
- `retire_candidate`: none by default from this scan.

## Disposition Result-To-Action Rules

C6-A is complete only if every row has a mechanical exit:

| Disposition | Required row-level result |
| --- | --- |
| `keep_as_stage` | Name the invariant already protected, the existing oracle or public surface that protects it, and say `no C6 cleanup now`. |
| `rename_or_document` | Name the exact doc/module note/name to change, or close the row as `keep_as_stage` if the name is acceptable. |
| `contract_harden` | Name the missing invariant/test/oracle, the blocker it protects against, and the reclassification rule after hardening. After C6-B, the row must become `keep_as_stage` or `targeted_cleanup_candidate`. |
| `targeted_cleanup_candidate` | Name one cleanup slice, affected files, affected public surfaces, and the required parity oracle before edits. |
| `retire_candidate` | Name no-use evidence, compatibility impact, removal plan, and rollback/verification. |

`contract_harden` is not a permanent parking state. If C6-A cannot name the
missing test or invariant for a `contract_harden` row, the row must be
reclassified as `keep_as_stage` with a residual-risk note instead of pretending
that an unspecified hardening task exists.

## Value Assessment Rules

A stage has current value if any of these are true:

- it affects production matrix rows or identity decisions;
- it protects duplicate, claim, winner/loser, owner, primary, provisional, or
  review semantics;
- it emits audit evidence that explains a product decision;
- it supports diagnostics needed to validate product behavior;
- it defines a stable handoff surface for downstream analysis;
- it is a compatibility surface that cannot be removed without a migration
  contract.

A stage can become `retire_candidate` only if all of these are true:

- no production pipeline entrypoint uses it;
- no current tests, diagnostics, docs, or handoff notes depend on it;
- it does not preserve a compatibility import or file format;
- no diagnostic or audit value remains;
- removal has a compatibility and verification plan.

## Golden Parity Surfaces

Any future C6-B/C implementation must name the smallest relevant oracle before
editing code. Candidate surfaces include:

- focused unit tests for the touched stage;
- row-level parity for `alignment_matrix.tsv`;
- row-level parity for `alignment_review.tsv`;
- row-level parity for `alignment_cells.tsv`;
- claim registry winner/duplicate assignment parity;
- primary consolidation winner/loser/audit parity;
- matrix identity primary/provisional/audit parity.

Hash-identical TSV output is preferred for broad move-only refactors. Narrow
stage tests are acceptable only when the touched helper cannot affect downstream
matrix delivery or when the phase explains why the narrower oracle is enough.

### Public Output Oracle Matrix

When a C6-B/C cleanup can affect writer-facing behavior, use this matrix before
editing. The canonical output-level source is
`xic_extractor/alignment/output_levels.py`; path construction is in
`xic_extractor/alignment/pipeline_outputs.py`; output contract rationale is in
[Untargeted alignment output contract](2026-05-11-untargeted-alignment-output-contract.md).

| Surface | Minimum oracle for C6-B/C |
| --- | --- |
| `alignment_matrix.tsv` | Schema/order parity plus row/value parity; broad refactors require hash-identical output. |
| `alignment_review.tsv` | Schema/order parity plus row-level `decision`, `confidence`, counts, flags, and reason parity. |
| `alignment_cells.tsv` | Schema/order parity plus row-level status, source candidate, area, RT, trace quality, and claim/duplicate fields parity. |
| `alignment_cell_integration_audit.tsv` | Schema/order parity plus row/value parity when the integration audit is emitted. |
| `alignment_owner_backfill_seed_audit.tsv` | Schema/order parity plus backfill seed, dependency, and support-label parity when emitted. |
| `alignment_matrix_status.tsv` | Schema/order parity plus status-cell parity when emitted. |
| `event_to_ms1_owner.tsv` | Row parity for event-to-owner assignment and owner metadata when emitted. |
| `ambiguous_ms1_owners.tsv` | Row parity for ambiguous-owner records and reasons when emitted. |
| `owner_edge_evidence.tsv` | Row parity for edge evidence that is intentionally emitted; envelope-rejected pairs remain governed by the existing owner-edge contract. |
| `skipped_evidence_ledger.tsv` | Schema/order parity plus skipped reason/status count parity when emitted. |
| `alignment_results.xlsx` | Workbook sheet-name/order and Matrix sheet value parity when emitted; deeper workbook sheets follow their underlying TSV/projection oracle. |
| `review_report.html` | Content-smoke parity for summary counts, duplicate/claim warnings, and linked artifact names; byte-identical HTML is not required unless the phase changes rendering only. |
| `alignment_run_metadata.json` | Metadata key parity when output-level, runner, baseline, or emitted artifact behavior is touched. |
| `alignment_production_candidate_gate.tsv` | Schema/order parity plus row-level gate decision, blocker, context, evidence-tier, and Tier2 availability parity when candidate-gate sidecars are emitted or consumed. |
| `alignment_production_candidate_gate.json` | Key/value parity for gate summary, source artifact hashes, Tier2 subset metadata, and emitted artifact paths when candidate-gate sidecars are emitted. |
| `alignment_tier2_trace_evidence.tsv` | Schema/order parity plus row-level evidence status, raw/provenance fields, scan/intensity metrics, blocker labels, criteria version, producer version, and subset hash parity. |
| `alignment_tier2_raw_manifest.tsv` | Schema/order parity plus raw path/sample/provenance/hash rows when Tier2 trace evidence is regenerated or consumed. |
| `alignment_tier2_trace_evidence_summary.json` | Key/value parity for Tier2 evidence counts, provenance, source artifact hashes, and generated artifact metadata. |
| identity coherence outputs | Diagnostic verdict/status/reason parity when the identity coherence diagnostic is emitted or when C6 touches its inputs. |

If the touched stage affects `output_level` routing, writer inclusion, or
artifact naming, `tests/test_alignment_output_levels.py`,
`tests/test_alignment_pipeline_outputs.py`, and the relevant writer tests become
part of the required oracle.

## Stop Rules

Stop C6 and write a separate behavior spec if the work requires:

- changing alignment output values;
- changing TSV schemas;
- changing primary/provisional/audit identity policy;
- changing owner membership or claim assignment behavior;
- changing winner/loser demotion;
- changing review reasons or diagnostic labels;
- deleting a diagnostic evidence source that still supports validation;
- extracting a helper that needs stage-specific side effects to remain correct.

## Verification

C6-A is docs-only. Required smoke checks:

```powershell
codegraph status
codegraph files --filter xic_extractor/alignment --format flat --no-metadata
rg -n "run_alignment|_build_event_first_matrix|cluster_candidates|build_sample_local_owners|cluster_sample_local_owners|select_backfill_features|build_owner_backfill_cells|build_owner_alignment_matrix|backfill_alignment_matrix|build_ms1_feature_families|integrate_feature_family_matrix|fold_near_duplicate_clusters|count_near_duplicate_pairs|apply_ms1_peak_claim_registry|consolidate_primary_family_rows|build_matrix_identity_decisions|build_production_decisions|build_cell_quality_decisions|classify_backfill_promotion|project_machine_decision|evaluate_production_candidate_gate|consolidate_pre_backfill_identity_families|run_identity_coherence_diagnostic|identity_gates|write_alignment_matrix_tsv|write_alignment_review_tsv|write_alignment_cells_tsv|write_alignment_results_xlsx|write_alignment_review_html|write_outputs_atomic|artifact_names_for_output_level" xic_extractor/alignment tests
git diff --check
```

If C6-B/C later touches code, that later phase must add focused tests for the
touched stage and run the CI-equivalent shard required by the one-goal phase
contract.

## Review Requirements

Before using this spec to launch C6 implementation:

- `implementation-contract-reviewer` checks whether public surfaces and parity
  oracles are named strongly enough.
- `strategy-challenger` is required only if the phase tries to convert C6 from
  inventory into implementation or if it claims a module can be retired.

Reviewer challenge should focus on:

- whether the stage disposition is based on product value rather than file
  aesthetics;
- whether the proposed oracle can catch matrix identity, claim, and
  winner/loser drift;
- whether any diagnostic evidence path is being mistaken for dead code;
- whether C6 is drifting back into broad grouping consolidation without proof.

## Done When For C6

C6 can close without code changes. That is acceptable if the inventory proves
that the modules have distinct value.

The phase is complete when:

- this spec is linked from the historical C6 spec;
- the current inventory is complete enough for the next one-goal cleanup phase;
- every stage has a semantics class, disposition, targetability label, and
  required next action / exit rule;
- every CodeGraph module family has a disposition, oracle, or out-of-scope
  reason;
- no implementation slice is selected without a parity oracle;
- any deferred cleanup candidate has a named blocker or required test.
