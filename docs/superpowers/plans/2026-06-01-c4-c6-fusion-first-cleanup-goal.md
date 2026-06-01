# C4/C6 Fusion-First Cleanup Goal

```text
/goal
GOAL:
Complete one focused cleanup PR on `codex/cleanup-retirement-foundation` that
closes the first executable C4/C6 fusion-first cleanup slice: harden C4 scorer
successor-projection coverage without moving active scorer policy, and start C6
event-first alignment retirement by removing private no-use wiring while keeping
public event-first imports on a deprecate-first compatibility path.

This goal is intentionally not a repo-wide dead-code sweep. It closes only the
C4/C6 pilot work that the current specs have made mechanically actionable.

CONTEXT:
- Repository/worktree:
  `C:\Users\user\Desktop\XIC_Extractor`, branch
  `codex/cleanup-retirement-foundation`.
- Required repo instructions:
  `AGENTS.md`,
  `docs/agent-subagent-routing.md`,
  `docs/agent-parameter-settings.md`.
- Primary specs:
  `docs/superpowers/specs/2026-06-01-c4-peak-scoring-evidence-decision-design.md`,
  `docs/superpowers/specs/2026-06-01-c6-alignment-stage-semantics-value-assessment-design.md`,
  `docs/superpowers/specs/2026-06-01-technical-debt-and-dead-code-cleanup-roadmap-v2-spec.md`.
- Historical context / superseded specs:
  `docs/superpowers/specs/2026-05-24-peak-pipeline-cleanup-peak-scoring-split-spec.md`,
  `docs/superpowers/specs/2026-05-24-peak-pipeline-cleanup-alignment-grouping-consolidation-spec.md`,
  `docs/superpowers/specs/2026-05-24-peak-pipeline-cleanup-hypothesis-model-unification-spec.md`,
  `docs/superpowers/specs/2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md`.
- C4 code/test surfaces to inspect first:
  `xic_extractor/peak_scoring.py`,
  `xic_extractor/peak_scoring_evidence.py`,
  `xic_extractor/peak_detection/hypotheses.py`,
  `xic_extractor/evidence_semantics.py`,
  `xic_extractor/peak_detection/facade.py`,
  `xic_extractor/extraction/peak_candidate_table.py`,
  `tests/test_peak_scoring.py`,
  `tests/test_peak_scoring_selection.py`,
  `tests/test_peak_scoring_evidence.py`,
  `tests/test_scoring_context.py`,
  `tests/test_peak_hypotheses.py`,
  `tests/test_evidence_semantics.py`,
  `tests/test_peak_candidate_table.py`,
  `tests/test_csv_writers.py`.
- C6 code/test surfaces to inspect first:
  `xic_extractor/alignment/__init__.py`,
  `xic_extractor/alignment/pipeline.py`,
  `xic_extractor/alignment/clustering.py`,
  `xic_extractor/alignment/backfill.py`,
  `xic_extractor/alignment/feature_family.py`,
  `xic_extractor/alignment/family_integration.py`,
  `xic_extractor/alignment/ownership.py`,
  `xic_extractor/alignment/owner_clustering.py`,
  `xic_extractor/alignment/owner_backfill.py`,
  `xic_extractor/alignment/owner_matrix.py`,
  `xic_extractor/alignment/claim_registry.py`,
  `xic_extractor/alignment/primary_consolidation.py`,
  `tests/test_alignment_clustering.py`,
  `tests/test_alignment_backfill.py`,
  `tests/test_alignment_feature_family.py`,
  `tests/test_alignment_family_integration.py`,
  `tests/test_alignment_config.py`,
  `tests/test_alignment_boundaries.py`,
  `tests/test_alignment_ownership.py`,
  `tests/test_alignment_owner_clustering.py`,
  `tests/test_alignment_owner_backfill.py`,
  `tests/test_alignment_owner_matrix.py`,
  `tests/test_alignment_claim_registry.py`,
  `tests/test_alignment_primary_consolidation.py`,
  `tests/test_alignment_matrix_identity.py`,
  `tests/test_alignment_production_decisions.py`,
  `tests/test_run_alignment.py`,
  `tests/test_alignment_pipeline.py`.
- Current baseline:
  C4 spec v0.6 says scorer evidence projection overlaps the successor spine,
  but score arithmetic, confidence caps, RT policy, local S/N, shape severity,
  and candidate selection remain active scorer policy. C6 spec v0.7 says
  event-first alignment is the strongest retirement/deprecation candidate on a
  deprecate-first public compatibility path, while owner-first construction,
  claim arbitration, consolidation, matrix identity, and production projection
  remain active stages.

CONSTRAINTS:
- Keep scope limited to C4/C6 pilot cleanup. Do not start a broad dead-code
  audit, module architecture rewrite, or unrelated cleanup.
- C4 must not remove, rewrite, or relocate active scorer policy:
  `score_candidate(...)`, `select_candidate_with_confidence(...)`,
  `score_evidence(...)`, confidence thresholds/caps, RT prior/centrality policy,
  local S/N computation, shape/noise severity, CWT chemistry guardrails, or
  candidate-selection tie-breaks.
- C4 may add or update successor projection tests and docs. It may delete or
  weaken scorer tests only when the invariant is proven successor-owned or
  obsolete by the C4-1 field map.
- C6 may retire event-first alignment code only after a fresh final no-use check
  confirms no production, script, diagnostic, or package consumer remains.
- C6 must keep public exports `cluster_candidates` and
  `backfill_alignment_matrix` on a deprecate-first compatibility path in this
  PR. Direct public-export removal is out of scope unless the goal is amended
  with explicit breaking-change approval and reviewed again.
- C6 must not change the owner-first production chain:
  `build_sample_local_owners(...)`, `cluster_sample_local_owners(...)`,
  `select_backfill_features(...)`, `build_owner_backfill_cells(...)`,
  `build_owner_alignment_matrix(...)`, `apply_ms1_peak_claim_registry(...)`,
  `consolidate_primary_family_rows(...)`, matrix identity, production decisions,
  writer behavior, or output-level routing.
- Preserve public outputs unless explicitly changed by the event-first public
  migration note: `alignment_matrix.tsv`, `alignment_cells.tsv`,
  `alignment_review.tsv`, workbook sheets, target CSV schemas, candidate-table
  schemas, run metadata keys, and diagnostic schemas.
- This is not a data migration and does not mutate production data; `dry-run` is
  not applicable unless the scope unexpectedly expands into data mutation. If it
  does, stop and write a separate data-migration contract.
- Rollback/recovery evidence is git-level revertability plus focused parity
  tests. Integrity evidence is no-use classification, public contract tests,
  schema/output parity tests, row counts or schema-header parity where an output
  fixture is touched, and unchanged CI-equivalent checks; checksums are not
  required unless generated binary/workbook artifacts are updated.
- Scope fuse: if execution discovers multiple independent PR-sized changes,
  keep this goal to C4 successor-projection hardening and C6 event-first
  deprecate-first cleanup, then list the additional PRs as follow-up instead of
  expanding this goal.
- Do not change repository settings, branch protection, GitHub metadata,
  automations, or platform settings. If owner/admin access is required, record it
  as a manual blocker.
- Move/delete behavior before changing behavior. This is a cleanup/contract PR;
  score, confidence, selected candidate, matrix identity, and writer-facing
  values must remain unchanged.
- Each implementation phase that changes files should end in one logical commit:
  C4 closeout, C6 event-first cleanup, and final docs/closeout if needed.
- Verification integrity:
  do not weaken or bypass tests, assertions, lint, typecheck, validation,
  generated-output checks, or reviewer blockers to make the goal pass. Fix the
  root cause or record the blocker.

SUBAGENT / XHIGH REVIEW PROTOCOL:
- Before execution, review this goal with repo-routed read-only subagents:
  `strategy-challenger` and `implementation-contract-reviewer`, both with
  xhigh reasoning if the runtime supports it.
- After each implementation phase and before committing that phase, run a
  read-only reviewer pass appropriate to the phase:
  C4 uses `implementation-contract-reviewer`; C6 uses
  `implementation-contract-reviewer`, plus `strategy-challenger` when code is
  removed, public export removal is attempted, or any removed symbol has a
  non-obvious product-value classification.
- If a reviewer says the goal is preserving a bad legacy path, deleting a live
  public contract, or overclaiming successor coverage, stop and fix the contract
  or implementation before continuing.
- Use the repo fix/re-check loop:
  fix blocker -> ask the original blocker reviewer to re-check -> add a third
  reviewer only if the fix moved into a new domain. Stop after three failed
  attempts on the same symptom.

SECOND-ROUND CONVERGENCE RECORD:
- Prior xhigh review blockers have been folded into this contract:
  C4 selected confidence/raw score/labels/reason are
  `successor_projection`, not proof that scorer policy is successor-owned; C6
  public `cluster_candidates` and `backfill_alignment_matrix` imports stay on a
  deprecate-first compatibility path in this PR.
- Direct public-export removal is not an execution detail. It requires explicit
  breaking-change approval, goal amendment, and another review pass.
- If current code evidence contradicts the C4 field map or C6 no-use audit,
  update the spec and rerun the relevant reviewer before implementation.
- If C4 projection tests already exist, do not duplicate them; record the named
  test family in the closeout table. If C6 compatibility shims still need a
  helper module, keep that helper and classify it as compatibility support
  rather than deleting it in this PR.

PHASES:

Phase 0 - Goal Contract And Review
Purpose:
- Land this goal contract after read-only xhigh review.
Done when:
- `strategy-challenger` and `implementation-contract-reviewer` report no
  blocking findings, or every blocker is fixed in this document.
- `git status --short --branch` records only intentional dirty files.

Phase 1 - C4 Scorer Successor-Projection Closeout
Purpose:
- Close C4's first executable cleanup slice by proving which scorer facts are
  already successor-projected while leaving active scorer policy in place.
Allowed work:
- Add or update successor projection tests for facts already carried by
  `EvidenceVector` / `CommonEvidence`: selected confidence/score/labels/reason,
  MS1 apex/area/height/boundaries, MS2/NL facts, MS2 trace metadata, candidate
  quality flag projection, and legacy CWT audit-presence projection.
- Treat selected confidence, raw score, support/concern/cap labels, and reason
  as `successor_projection`, not as proof that scorer policy is successor-owned.
- Add a small scorer-to-successor parity fixture if needed to prevent future
  accidental drift.
- Update the C4 spec with a short execution closeout note that says which facts
  are `successor_owned`, which remain `active_policy`, and which tests were
  moved, kept, or intentionally not moved.
Forbidden work:
- Do not move or rewrite scorer policy, scorer selection, confidence caps,
  local S/N, shape severity, or RT-window policy.
- Do not change output schema, reason text, confidence values, selected
  candidate, score labels, or cap labels.
Done when:
- Successor projection coverage exists or is explicitly shown already present
  for the C4-1 field map's successor-owned rows.
- Active policy rows remain protected by scorer tests.
- The C4 closeout table maps every C4-1 field-map row to a named test family or
  a named missing successor field, using the full classification vocabulary:
  `successor_projection`, `successor_owned`, `active_policy`,
  `compatibility_adapter`, and `semantic_migration_candidate`.
- The C4 spec names any remaining `semantic_migration_candidate` rows and their
  exit rule.

Phase 2 - C6 Event-First Retirement / Public Contract Cleanup
Purpose:
- Start retiring the event-first alignment path without touching the owner-first
  production chain or silently breaking public imports.
Allowed work:
- Run a fresh no-use audit for:
  `cluster_candidates`, `_cluster_candidates_greedy`,
  `backfill_alignment_matrix`, `_build_event_first_matrix`,
  `build_ms1_feature_families`, and `integrate_feature_family_matrix`.
- Classify every residual no-use scan hit as one of:
  `active_consumer`, `compatibility_shim`, `public_contract_test`,
  `historical_doc`, `current_spec_or_goal`, `migration_note`,
  `implementation_test_to_delete`, or `unknown`.
- Remove `_build_event_first_matrix(...)` if no callers remain.
- Keep package-level public imports `cluster_candidates` and
  `backfill_alignment_matrix` available as compatibility shims during this PR,
  with a deprecation/migration note and tests that lock the chosen shim behavior.
- Delete event-first implementation modules and tests only if they are not
  required by the compatibility shims and invariant triage proves their
  remaining tests are obsolete implementation mechanics or their useful
  invariants are already covered by owner-first / hypothesis / diagnostic tests.
- Update C6 spec and roadmap with the final public migration/deprecation
  decision and no-use evidence.
Forbidden work:
- Do not remove or weaken owner-first production modules or tests.
- Do not change `run_alignment(...)` owner-first outputs, writer schemas,
  matrix identity policy, production decisions, claim arbitration, primary
  consolidation, owner-family construction, or owner-backfill behavior.
Done when:
- Private no-use event-first wiring is removed, and public event-first imports
  are reduced to explicit deprecate-first compatibility shims with documented
  exit rules.
- Public exports and boundary tests reflect the compatibility-shim contract.
- The final no-use audit table has no `unknown` hits and no unreviewed
  `active_consumer` hits for any removed symbol.
- Event-first implementation-detail tests are removed only when successor or
  active-owner coverage is recorded.
- The C6 spec records the final classification for every event-first surface:
  `adapter_only`, `retire_candidate`, `obsolete_implementation_detail`, or
  `historical_reference`.

Phase 3 - Closeout, Verification, And PR Readiness
Purpose:
- Prove C4/C6 cleanup did not drift into behavior change or unrelated cleanup.
Done when:
- Specs/roadmap mention the executed C4/C6 closeout state.
- No unrelated dirty files remain.
- Focused tests and CI-equivalent checks have fresh results, or a concrete
  blocker is recorded.
- Final output can state the readiness label. Expected label is
  `diagnostic_only` or cleanup-only unless tests and CI pass; do not claim
  `production_ready` from docs/tests alone.

DONE WHEN:
- C4 successor-projection coverage is hardened and documented without moving
  active scorer policy.
- C4 closeout uses the full classification vocabulary:
  `successor_projection`, `successor_owned`, `active_policy`,
  `compatibility_adapter`, and `semantic_migration_candidate`.
- C6 event-first private no-use wiring is retired, while public event-first
  imports stay on an explicit deprecate-first compatibility path with a public
  migration note and no-use evidence.
- Owner-first alignment production behavior, matrix identity, production
  decisions, target CSV output, and scorer selection behavior are unchanged.
- All changed specs/plans/tests/code align with the C4/C6 fusion-first specs.
- Each completed implementation phase has one logical commit, unless the phase
  produced no file changes.
- Worktree has no unrelated dirty files.

VERIFY:
Run final no-use / contract scans:

```powershell
codegraph status
rg -n "cluster_candidates|_cluster_candidates_greedy|backfill_alignment_matrix|_build_event_first_matrix|build_ms1_feature_families|integrate_feature_family_matrix" xic_extractor tools scripts tests docs
rg -n "score_candidate|select_candidate_with_confidence|score_evidence|local_sn_severity|rt_prior_severity|rt_centrality_severity|noise_shape_severity|peak_width_severity" xic_extractor tests
```

Run focused C4 tests:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest -q tests/test_peak_hypotheses.py tests/test_evidence_semantics.py tests/test_peak_scoring.py tests/test_peak_scoring_selection.py tests/test_peak_scoring_evidence.py tests/test_scoring_context.py tests/test_peak_candidate_table.py tests/test_csv_writers.py tests/test_signal_processing_selection.py
```

Run focused C6 tests:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest -q tests/test_alignment_boundaries.py tests/test_alignment_config.py tests/test_alignment_ownership.py tests/test_alignment_owner_clustering.py tests/test_alignment_owner_backfill.py tests/test_alignment_owner_matrix.py tests/test_alignment_claim_registry.py tests/test_alignment_primary_consolidation.py tests/test_alignment_matrix_identity.py tests/test_alignment_production_decisions.py tests/test_run_alignment.py tests/test_alignment_pipeline.py tests/test_alignment_pipeline_outputs.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py
```

Run CI-equivalent checks before PR closeout:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run ruff check xic_extractor tests
uv run mypy xic_extractor
uv run pytest -v --tb=short -x
git diff --check
git status --short --branch
```

Inspect:
- C4 spec closeout wording does not claim scorer policy is retired.
- C6 spec closeout wording does not claim owner-first production chain is
  replaced by diagnostics.
- Public event-first imports remain available unless this goal has been amended
  with explicit breaking-change approval and reviewed again.
- No deleted tests were simply hiding active product behavior.

If any CI-equivalent command cannot run because of sandbox, DLL, dependency,
or runtime blockers, rerun with the required approved command shape or stop and
record the exact blocker. Do not substitute stale evidence.

OUTPUT:
- Changed files by phase.
- Key decisions: C4 `successor_projection` / `successor_owned` /
  `active_policy` / `compatibility_adapter` /
  `semantic_migration_candidate` rows; C6 event-first public compatibility
  decision.
- Verification commands and results.
- Whether public imports, target CSVs, alignment TSVs, workbook sheets, or
  diagnostic schemas changed.
- Remaining risk and exact follow-up, if any.

STOP RULES:
- Stop on secrets, production credentials, destructive data operations,
  unclear product decisions, or unsafe permissions.
- Stop if C4 cleanup requires changing score, confidence, selected candidate,
  reason text, cap labels, candidate table columns, CSV/XLSX output, or
  `PeakHypothesis` audit semantics.
- Stop if C6 cleanup requires changing owner-first production behavior,
  `alignment_matrix.tsv`, `alignment_cells.tsv`, `alignment_review.tsv`,
  workbook sheets, matrix identity, claim arbitration, primary consolidation,
  or production decision behavior.
- Stop if final no-use evidence shows a real production/script/diagnostic
  consumer for an event-first public surface that the phase planned to remove.
- Stop if reviewer findings expose a public-contract migration decision not
  already covered by this goal.
- Stop after three failed attempts on the same symptom and revisit the
  root-cause hypothesis.
- Do not mark complete until the current state is checked against `DONE WHEN`.
```
