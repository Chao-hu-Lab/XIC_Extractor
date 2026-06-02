# C6 Owner-Family Semantic Convergence Goal

```text
/goal
GOAL:
Complete one end-to-end C6 owner-family semantic convergence PR through
C6-A1, C6-A2, C6-A3, and C6-B:

1. establish a behavior-neutral `CrossSamplePeakGroupHypothesis` shadow
   contract for cross-sample owner membership;
2. project current owner-family edge evidence into successor-visible facts;
3. project split-gate and review-only semantics into successor-visible facts
   without changing live policy disposition;
4. decide the final C6-B disposition of `owner_clustering.py`.

The finish line is not deletion. The finish line is a parity-backed decision:
`owner_clustering.py` is either `keep_as_stage`,
`internal_constructor_candidate`, `compatibility_adapter_candidate`, or
`retirement_candidate_after_parity`, with an explicit exit rule.

CONTEXT:
- Repository/worktree:
  `C:\Users\user\Desktop\XIC_Extractor`, current branch.
- Required repo instructions:
  `AGENTS.md`,
  `docs/agent-subagent-routing.md`,
  `docs/agent-parameter-settings.md`.
- Primary spec:
  `docs/superpowers/specs/2026-06-02-c6-cross-sample-peak-group-hypothesis-shadow-contract-design.md`.
- Parent/background specs:
  `docs/superpowers/specs/2026-06-01-c6-alignment-stage-semantics-value-assessment-design.md`,
  `docs/superpowers/specs/2026-05-11-untargeted-alignment-output-contract.md`,
  `docs/superpowers/specs/2026-06-02-repo-semantic-overlap-inventory-spec.md`,
  `docs/superpowers/specs/2026-06-01-technical-debt-and-dead-code-cleanup-roadmap-v2-spec.md`,
  `docs/superpowers/specs/2026-06-01-peak-pipeline-cleanup-current-state-reassessment-spec.md`.
- Current baseline:
  Event-first alignment is already retired. Owner-first production stages remain
  active. `owner_clustering.py` still constructs cross-sample owner families and
  `OwnerAlignedFeature` remains the active delivery DTO consumed by backfill,
  matrix, claim registry, primary consolidation, and writers.
- Successor direction:
  `family` / `FAM######` is output compatibility language. The product semantic
  center moves toward a cross-sample peak group hypothesis supported,
  challenged, split, or demoted by evidence.

CONSTRAINTS:
- Keep scope to C6 owner-family semantic convergence. Do not reopen event-first
  alignment, C4 peak scoring, region-boundary work, or broad dead-code cleanup.
- Preserve owner-first production behavior:
  sample-local ownership, owner-family construction, backfill scope, owner
  backfill, owner matrix, claim registry, primary consolidation, matrix
  identity, production decisions, writer routing, output-level behavior, and
  process payload compatibility.
- Preserve public output contracts:
  `FAM######` identity, `OwnerAlignedFeature` compatibility shape,
  `alignment_matrix.tsv`, `alignment_cells.tsv`, `alignment_review.tsv`,
  workbook sheets/order/headers/values, `owner_edge_evidence.tsv` when emitted,
  output-level artifact names, and run metadata.
- Do not rename, delete, or publicly replace `OwnerAlignedFeature`,
  `cluster_sample_local_owners(...)`, owner-family IDs, or public alignment
  package exports in this goal.
- Do not import or redefine sample-local `PeakHypothesis`, `peak_hypothesis_id`,
  `shared_peak_identity_explanation`, or product activation semantics for this
  C6 owner-group shadow contract.
- Do not classify `claim_registry.py` or `primary_consolidation.py` as cleanup
  targets in this goal. They remain active arbitration stages unless a separate
  behavior spec says otherwise.
- RAW/85RAW validation is not required for this no-behavior semantic convergence
  goal. If implementation can affect matrix values or output behavior, stop and
  write a behavior/validation plan first.
- Verification integrity:
  do not weaken tests, parity assertions, writer checks, lint, typecheck, or
  no-use/import guards to make the goal pass.

SUBAGENT / REVIEW PROTOCOL:
- Execution may use `superpowers:subagent-driven-development` or
  `superpowers:executing-plans`; either path must preserve this goal's phase
  gates.
- Before execution, review this updated goal with repo-routed read-only
  `strategy-challenger` and `implementation-contract-reviewer`, xhigh if the
  runtime supports it.
- After each phase, run a phase-specific review before commit:
  - strategy review when a phase changes successor semantics or
    `owner_clustering.py` disposition;
  - implementation-contract review when a phase adds code, tests, adapters, or
    parity surfaces.
- Use fix/re-check:
  blocker -> patch -> ask the original reviewer to re-check -> proceed only
  after no blocker.
- Commit after each completed phase only after review blockers are closed and
  phase verification has fresh results.

PHASES:

Phase 0 - Goal Alignment And Review
Purpose:
- Align the executable goal with the C6 A1/A2/A3/B spec and confirm dirty scope.
Done when:
- This goal references the C6 cross-sample peak group hypothesis spec as the
  primary spec.
- Dirty scope is recorded; unrelated dirty files are not staged or reverted.
- xhigh strategy and implementation-contract review report no blocking
  findings, or every blocker is fixed in this document.

Phase 1 - C6-A1 Identity And Membership Shadow Contract
Purpose:
- Define the internal `CrossSamplePeakGroupHypothesis` model.
- Project it from `OwnerAlignedFeature`.
- Prove family ID, owner membership, event IDs, event count, and supporting
  events preserve current owner-family membership semantics.
Allowed work:
- Add `xic_extractor/alignment/cross_sample_peak_groups.py` as the fixed
  internal alignment-local successor module.
- Add focused projection tests.
- Add or strengthen writer-visible compact golden triad parity for
  `alignment_matrix.tsv`, `alignment_cells.tsv`, and `alignment_review.tsv`.
- Update `owner_family_successor_contract.py` only for the membership invariant
  actually proven by tests.
Forbidden work:
- No production consumer may import the new shadow model.
- No change to `cluster_sample_local_owners(...)`, `OwnerAlignedFeature`,
  `run_alignment(...)`, writer schemas, workbook contracts, output routing, or
  process payloads.
Done when:
- C6-A1 projection parity is tested, including at least one owner with
  non-empty `supporting_events`.
- Compact TSV parity proves public matrix/cells/review output is unchanged.
- Mechanical no-use/import checks show no forbidden production-path adoption and
  no `PeakHypothesis` / `peak_hypothesis_id` / product-activation leakage.
- The C6 spec or closeout records whether stable membership is
  `successor_owned` or still `successor_gap`, with evidence.

Phase 2 - C6-A2 Edge Evidence Projection
Purpose:
- Project complete-link-compatible edge evidence, drift-prior evidence,
  tolerance evidence, and edge-strength facts into successor-visible
  support/challenge facts.
- Keep hard gates and review-only records as live `active_policy` unless C6-A3
  proves compatible shadow facts.
Allowed work:
- Extend the internal successor module or companion model with edge evidence
  facts.
- Add focused owner-clustering and successor-contract tests that prove current
  edge evidence remains observable.
- Update `owner_family_successor_contract.py` only for edge invariants proven by
  tests.
Forbidden work:
- No change to complete-link merge behavior, edge thresholds, family
  membership, writer output, or production consumer behavior.
Done when:
- Complete-link, drift-prior, weak-edge, no-same-sample, and edge-sink
  semantics are covered by existing or new tests.
- Successor facts can explain edge support/challenge without changing current
  grouping.
- Compact TSV parity and applicable owner-edge evidence checks remain clean.

Phase 3 - C6-A3 Split Gate And Review-Only Shadow Facts
Purpose:
- Project hard split gate and review-only semantics into successor-visible
  challenge/demotion facts.
- Preserve live disposition vocabulary: hard gates and review-only semantics
  remain `active_policy` unless a tested contract update says otherwise.
Allowed work:
- Add shadow challenge/demotion/split facts or companion audit structure.
- Add tests for neutral-loss/product conflict, observed-loss conflict,
  impossible m/z, identity conflict, ambiguous owner, and review-only records.
- Document exact compatibility mapping for existing reason vocabulary.
Forbidden work:
- No split threshold changes.
- No removal of review-only owner records.
- No changes to `alignment_review.tsv`, duplicate/loser audit, or production
  decision reasons.
Done when:
- Current hard split and review-only invariants are either represented as
  successor-visible shadow facts with live disposition still `active_policy`, or
  explicitly listed as `successor_gap`.
- No new disposition label is introduced unless
  `owner_family_successor_contract.py` is deliberately expanded with tests.
- Compact TSV parity confirms public output is unchanged.

Phase 4 - C6-B Owner-Clustering Disposition Decision
Purpose:
- Decide whether owner-family construction can internally build
  `CrossSamplePeakGroupHypothesis` first and adapt back to
  `OwnerAlignedFeature`, or whether `owner_clustering.py` should remain the
  active stage for now.
Allowed outcomes:
- `keep_as_stage`: successor does not own enough invariants.
- `internal_constructor_candidate`: successor owns semantics, but
  `owner_clustering.py` remains the internal constructor.
- `compatibility_adapter_candidate`: successor-owned semantics can adapt back to
  old public output shapes.
- `retirement_candidate_after_parity`: successor owns invariants and public
  parity is proven; actual deletion is deferred to a later cleanup goal.
Forbidden outcome:
- Direct deletion of `owner_clustering.py` in this goal.
Done when:
- C6-B names exactly one disposition for `owner_clustering.py`.
- Any constructor/adaptor experiment proves exact row/value parity for
  `alignment_matrix.tsv`, `alignment_cells.tsv`, `alignment_review.tsv`, and
  `owner_edge_evidence.tsv` when emitted.
- Optional pre-backfill consolidation and backfill-scope consumers are covered
  when seed centers, family membership, review-only state, or backfill
  eligibility could change.
- `owner_family_successor_contract.py` records which invariants are
  `successor_owned`, still `active_policy`, or still `successor_gap`.

Phase 5 - Closeout And Phase Commit
Purpose:
- Prove the C6 owner-family path has one future direction and no production
  behavior drift.
Done when:
- The C6 spec records A1/A2/A3/B status, invariant mapping, successor gaps,
  final `owner_clustering.py` disposition, and later cleanup candidates.
- Phase verification results are fresh.
- Review blockers are closed.
- No unrelated files are staged.
- Commit contains only the completed phase scope.

DONE WHEN:
- C6-B names exactly one disposition for `owner_clustering.py` after C6-A1,
  C6-A2, and C6-A3 evidence has been evaluated.
- C6-A1, C6-A2, C6-A3, and C6-B phase gates are complete with fresh
  verification.
- `CrossSamplePeakGroupHypothesis` exists as an internal successor shadow
  contract with tested membership, edge evidence, and split/review-only
  projections appropriate to the completed phases.
- `owner_clustering.py` has one documented C6-B disposition and exit rule:
  `keep_as_stage`, `internal_constructor_candidate`,
  `compatibility_adapter_candidate`, or `retirement_candidate_after_parity`.
- Owner-first production behavior and public alignment outputs are unchanged.
- `claim_registry.py` and `primary_consolidation.py` remain active arbitration
  stages unless separately approved.
- Any legacy deletion is deferred to a later parity-backed cleanup goal.

VERIFY:
Run focused tests by phase. The final C6-B shard is:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest -q tests/test_alignment_owner_family_successor_contract.py tests/test_alignment_owner_clustering.py tests/test_pre_backfill_consolidation.py tests/test_backfill_scope.py tests/test_alignment_owner_backfill.py tests/test_alignment_owner_matrix.py tests/test_alignment_claim_registry.py tests/test_alignment_primary_consolidation.py tests/test_alignment_matrix_identity.py tests/test_alignment_production_decisions.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_debug_writer.py tests/test_alignment_output_levels.py tests/test_run_alignment.py tests/test_alignment_pipeline.py tests/test_alignment_pipeline_outputs.py
uv run ruff check xic_extractor tests
uv run mypy xic_extractor
git diff --check
git status --short --branch
```

Mechanical no-use / import checks:

```powershell
git diff --name-only
rg -n "PeakHypothesis|peak_hypothesis_id|shared_peak_identity_explanation|product_activation" xic_extractor\alignment\cross_sample_peak_groups.py tests\test_alignment_owner_family_successor_contract.py
rg -n "CrossSamplePeakGroupHypothesis|cross_sample_peak_group" xic_extractor\alignment\__init__.py xic_extractor\alignment\pipeline.py xic_extractor\alignment\pipeline_outputs.py xic_extractor\alignment\process_backend.py xic_extractor\alignment\owner_backfill.py xic_extractor\alignment\owner_matrix.py xic_extractor\alignment\tsv_writer.py xic_extractor\alignment\xlsx_writer.py xic_extractor\peak_detection\hypotheses.py xic_extractor\alignment\shared_peak_identity_explanation
```

After C6-A1, `xic_extractor\alignment\cross_sample_peak_groups.py` must exist.
If it does not, the phase is not complete. Each phase closeout must compare
`git diff --name-only` against the phase allowlist; any out-of-phase changed
file is a blocker unless the goal is deliberately amended and re-reviewed.

Inspect:
- no event-first path is reintroduced;
- no public package export changes unless separately approved;
- TSV/workbook/output-level contract tests remain unchanged or stronger;
- broad constructor/adaptor changes cite exact row/value parity for the compact
  golden triad plus `owner_edge_evidence.tsv` when emitted;
- narrow changes explain why broader TSV/workbook/debug artifacts cannot
  change.

OUTPUT:
- Phase-by-phase status.
- Changed files by phase.
- Owner-family invariant map.
- Successor gap list.
- Final `owner_clustering.py` disposition and exit rule.
- Reviewer findings and fixes.
- Verification commands and results.
- Later legacy cleanup candidates, if any.

STOP RULES:
- Stop if owner membership, family IDs, matrix values, cell statuses, review
  reasons, edge evidence rows, claim assignments, primary winner/loser behavior,
  output-level routing, or process payload compatibility changes.
- Stop if successor mapping cannot represent a required owner-family invariant;
  record it as `successor_gap`, choose a non-retirement disposition, and name
  the exit evidence.
- Stop if a diagnostic-only surface is used as replacement proof for production
  owner-family construction.
- Stop if public alignment exports, writer schemas, workbook sheets, or process
  payloads need a migration decision.
- Stop if RAW validation becomes necessary to justify this cleanup/semantic
  convergence phase.
- If a stop rule fires before C6-B, report BLOCKED and do not mark the goal
  complete.
- If an invariant cannot be successor-owned, record it as `successor_gap` and
  continue to C6-B with a non-retirement disposition unless behavior or public
  surface change is required.
- Stop after three failed fixes for the same symptom and revisit the root-cause
  hypothesis.
- Do not mark complete until the current state is checked against `DONE WHEN`.
```
