# C4 Evidence-Decision Semantic Convergence Goal

```text
/goal
GOAL:
Complete one C4 semantic convergence PR that turns the peak-scoring overlap into
a single evidence-decision direction: legacy scoring remains the active product
policy where it still owns selection/confidence/caps, while still-valid scorer
facts and public projections are mapped to successor evidence semantics with
clear dispositions, characterization tests, and exit rules.

This is not a scorer deletion goal. Legacy code and tests may remain after this
goal when they protect active policy or public compatibility. Deletion belongs
to a later legacy cleanup goal after successor ownership is proven.

CONTEXT:
- Repository/worktree:
  `C:\Users\user\Desktop\XIC_Extractor`, current branch.
- Required repo instructions:
  `AGENTS.md`,
  `docs/agent-subagent-routing.md`,
  `docs/agent-parameter-settings.md`.
- Primary spec:
  `docs/superpowers/specs/2026-06-01-c4-peak-scoring-evidence-decision-design.md`.
- Related inputs:
  `docs/superpowers/specs/2026-05-24-peak-pipeline-cleanup-hypothesis-model-unification-spec.md`,
  `docs/superpowers/specs/2026-06-02-region-boundary-decision-owner-design.md`,
  `docs/superpowers/specs/2026-06-02-repo-semantic-overlap-inventory-spec.md`,
  `docs/superpowers/specs/2026-06-01-technical-debt-and-dead-code-cleanup-roadmap-v2-spec.md`.
- Code surfaces to inspect first:
  `xic_extractor/peak_scoring.py`,
  `xic_extractor/peak_scoring_evidence.py`,
  `xic_extractor/peak_detection/hypotheses.py`,
  `xic_extractor/evidence_semantics.py`,
  `xic_extractor/peak_detection/facade.py`,
  `xic_extractor/extraction/scoring_factory.py`,
  `xic_extractor/extraction/peak_candidate_table.py`,
  `xic_extractor/extraction/result_assembly.py`.
- Test surfaces to inspect first:
  `tests/test_peak_scoring.py`,
  `tests/test_peak_scoring_selection.py`,
  `tests/test_peak_scoring_evidence.py`,
  `tests/test_scoring_context.py`,
  `tests/test_peak_hypotheses.py`,
  `tests/test_evidence_semantics.py`,
  `tests/test_peak_candidate_table.py`,
  `tests/test_csv_writers.py`,
  `tests/test_csv_to_excel.py`,
  `tests/test_excel_pipeline.py`,
  `tests/test_signal_processing_selection.py`.
- Current baseline:
  `score_candidate(...)`, `select_candidate_with_confidence(...)`, score
  arithmetic, caps, review-only rules, RT policy, local S/N, morphology/shape
  severity, and candidate-selection tie-breaks are active product policy today.
  `EvidenceVector` and `CommonEvidence` already project many scorer facts but do
  not yet own candidate selection or decision policy.

CONSTRAINTS:
- Keep scope to C4 semantic convergence. Do not execute C6 or region-boundary
  migration inside this goal.
- Do not change selected candidate, score, confidence, cap labels, support or
  concern labels, reason text, candidate-table values, CSV/XLSX values,
  workbook schemas, or public output fields unless a separate behavior/output
  spec explicitly approves it.
- Do not move or rewrite active scorer policy in a cleanup-only slice:
  `score_candidate(...)`, `_evidence_from_context(...)`,
  `_is_review_only_evidence(...)`, `select_candidate_with_confidence(...)`,
  confidence thresholds/caps, local S/N computation, morphology severity, RT
  severity, CWT guardrails, or quality penalties.
- Legacy `raw_score`, `confidence`, `cap_labels`, and reason text are public
  compatibility projections while current outputs expose them. They are not the
  future evidence-chain policy target.
- Future policy target is decision/explanation semantics:
  selected hypothesis, decision class, typed evidence facts, conflicts,
  review/not-counted/exclusion/ambiguity reasons, and human-readable
  explanation parity.
- Do not create a fourth evidence model. Map facts to `EvidenceVector`,
  `CommonEvidence`, a future trace morphology evidence component, or an
  explicitly named compatibility projection.
- Preserve public imports from `xic_extractor.peak_scoring` unless a separate
  public migration plan exists.
- Verification integrity:
  do not weaken scorer tests just to claim successor ownership. Move or delete
  tests only when successor tests protect the same product invariant.

SUBAGENT / XHIGH REVIEW PROTOCOL:
- Before execution, review this goal with repo-routed read-only subagents:
  `strategy-challenger` and `implementation-contract-reviewer`, both with
  xhigh reasoning if the runtime supports it.
- Before any code movement, use `implementation-contract-reviewer` to verify
  public projection parity and import compatibility.
- If a phase tries to classify active scorer behavior as successor-owned, ask
  `strategy-challenger` to challenge whether this is real successor ownership
  or only projection.
- Use the repo fix/re-check loop:
  fix blocker -> ask the original blocker reviewer to re-check -> add a third
  reviewer only if the fix moved into validation, docs-handoff, or ops scope.

PHASES:

Phase 0 - Goal Contract And Review
Purpose:
- Land this goal after read-only xhigh review.
Done when:
- `strategy-challenger` and `implementation-contract-reviewer` report no
  blocking findings, or every blocker is fixed in this document.
- Dirty scope is recorded and unrelated dirty files are not staged.

Phase 1 - C4-A Projection Boundary Characterization
Purpose:
- Pin legacy public projection behavior before any projection extraction or
  adapter cleanup.
Allowed work:
- Add or update characterization tests for:
  complete public import smoke from `xic_extractor.peak_scoring`, including
  `Confidence`, `ScoredCandidate`, `ScoringContext`,
  `build_evidence_reason`, `build_reason`, `confidence_from_total`,
  `local_sn_severity`, `nl_support_severity`, `noise_shape_severity`,
  `peak_width_severity`, `rt_centrality_severity`, `rt_prior_severity`,
  `score_breakdown_fields`, `score_candidate`,
  `select_candidate_with_confidence`, `symmetry_severity`,
  `candidate_quality_penalty`, `candidate_selection_quality_penalty`,
  `compute_local_sn_cache`, and `hard_quality_flags`;
  exact `reason` text and `score_breakdown_fields(...)` ordering;
  support/concern/cap label projection;
  review-only and not-counted projection cases;
  candidate TSV / CSV / XLSX confidence and reason projection;
  diagnostic/report consumers of score projection fields, including score
  calibration/report outputs when those fields are touched.
- Create a small closeout table mapping current projection tests to C4-A gate
  rows.
Forbidden work:
- Do not move active decision policy, scorer arithmetic, selection, or severity
  helpers.
Done when:
- Projection behavior has named tests.
- Active policy behavior remains protected by scorer/selection tests.

Phase 2 - C4-A Projection Extraction Or Compatibility Decision
Purpose:
- Decide and implement the smallest projection-boundary cleanup only if
  characterization proves it is useful.
Allowed work:
- Extract pure reason/breakdown formatting to a focused module such as
  `xic_extractor/peak_scoring_projection.py`, or record that direct successor
  projection makes extraction unnecessary.
- Keep `xic_extractor.peak_scoring` as the public compatibility facade.
- Keep review-only/policy calculation in `peak_scoring.py` unless a later C4-C
  behavior contract exists.
Forbidden work:
- No selected-candidate, score, confidence, cap, reason, or schema changes.
- No dependency from projection helpers back into `xic_extractor.peak_scoring`.
Done when:
- Public imports remain valid.
- Exact projection parity tests pass.
- The C4 spec records whether projection is a `compatibility_adapter`,
  `legacy_compatibility_projection`, or deferred successor projection.

Phase 3 - C4-B Typed Evidence Mapping Inventory And Bridge
Purpose:
- Map scorer facts to the successor evidence chain without changing policy.
Allowed work:
- Inventory current scorer facts and classify each as:
  `successor_owned`, `successor_decision_semantics`,
  `legacy_compatibility_projection`, `active_policy`,
  `compatibility_adapter`, `semantic_migration_candidate`, or
  `retire_candidate`.
- Add bridge tests for scorer facts already projected into `EvidenceVector` and
  `CommonEvidence`.
- Add typed evidence fields only when they are internal, preserve output values,
  and do not recompute scorer decisions.
Required mapping families:
- local S/N with AsLS baseline provenance;
- trace morphology: shape, width, noise, continuity, edge recovery, shoulder,
  split/merge, and boundary plausibility;
- CWT as morphology / boundary-hypothesis evidence source;
- MS2/NL as candidate-aligned identity evidence;
- role-aware targeted RT evidence for ISTD/STD contexts.
Done when:
- Every scorer fact family has one owner or a named migration blocker.
- No scorer weight/cap mechanic is promoted as future product semantics.

Phase 4 - C4-C Decision Semantics Contract
Purpose:
- Define the future decision vocabulary and parity oracle before any model
  selection migration.
Allowed work:
- Add or update docs/tests to define decision classes:
  `accepted`, `review`, `not_counted`, `excluded`, and `ambiguous`.
- Map legacy cap/review labels to typed conflict/review/not-counted/exclusion
  reasons without changing public projection values.
- Name the future decision owner, even if active policy stays in
  `peak_scoring.py` for now.
Forbidden work:
- No replacement of current `select_candidate_with_confidence(...)`.
- No behavior changes hidden as cleanup.
Done when:
- The C4 spec records the decision/explanation parity oracle for any future
  C4-D model-selection migration.
- Current active policy remains the oracle until successor model selection is
  implemented and approved.

Phase 5 - Closeout And Verification
Purpose:
- Prove C4 has one semantic direction without pretending legacy scorer policy is
  retired.
Done when:
- C4 spec records completed dispositions, tests moved/kept, and remaining
  active-policy surfaces.
- No unrelated files are staged for this goal.
- Focused tests and docs smoke checks have fresh results.

DONE WHEN:
- C4 has a durable responsibility map with one disposition for every scorer
  responsibility:
  `successor_owned`, `successor_decision_semantics`,
  `legacy_compatibility_projection`, `active_policy`,
  `compatibility_adapter`, `semantic_migration_candidate`, or
  `retire_candidate`.
- Public projection behavior is characterized and either extracted behind a
  compatibility facade or explicitly deferred with an exit rule.
- Typed evidence mapping exists or has named blockers for local S/N,
  morphology, CWT, MS2/NL, and role-aware RT.
- Decision semantics are defined independently from legacy score/cap mechanics.
- Active scorer policy remains protected and is not falsely claimed as retired.
- Public outputs/imports remain unchanged.
- Public import compatibility is proven by a complete import-smoke test or a
  named equivalent. Projection consumers that expose scorer fields in TSV, CSV,
  XLSX, workbook sheets, or diagnostic reports have exact schema/value parity
  when touched.

VERIFY:
Run focused tests, split if needed:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest -q tests/test_peak_scoring.py tests/test_peak_scoring_selection.py tests/test_peak_scoring_evidence.py tests/test_scoring_context.py tests/test_peak_hypotheses.py tests/test_evidence_semantics.py tests/test_peak_candidate_table.py tests/test_peak_candidate_score_calibration_report.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py tests/test_excel_sheets_contract.py tests/test_signal_processing_selection.py
uv run ruff check xic_extractor tests
uv run mypy xic_extractor
git diff --check
git status --short --branch
```

Inspect:
- public imports from `xic_extractor.peak_scoring` still work;
- no public candidate TSV/CSV/XLSX/workbook schema or values changed;
- touched docs do not claim scorer retirement or `production_ready`.
- if a scorer projection consumer is omitted from the focused shard, the
  implementation closeout must name it and explain why the diff cannot affect
  it; otherwise the relevant consumer test or exact artifact parity check is
  required.

OUTPUT:
- Phase-by-phase status.
- Changed files by phase.
- Scorer responsibility disposition table.
- Reviewer findings and fixes.
- Verification commands and results.
- Remaining legacy cleanup candidates, if any, for a later goal.

STOP RULES:
- Stop if C4 cleanup requires changing current selected candidate, score,
  confidence, review-only semantics, cap labels, reason text, or output schema.
- Stop if successor mapping would create a fourth evidence model.
- Stop if RT evidence is generalized beyond the targeted ISTD/STD context
  without a separate contract.
- Stop if CWT becomes standalone identity or selection authority.
- Stop if public projection fields must be renamed, removed, recomputed, or
  replaced without a versioned output-schema/deprecation plan.
- Stop after three failed fixes for the same symptom and revisit the root-cause
  hypothesis.
- Do not mark complete until the current state is checked against `DONE WHEN`.
```
