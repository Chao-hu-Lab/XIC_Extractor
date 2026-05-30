# Shared Peak Identity Slice 0 Goal

```text
/goal
GOAL:
Implement the reviewed Slice 0 shared peak identity explanation pilot so the
seven-family manual oracle is represented as durable oracle rows, evidence
vectors, explanations, run facts, and a compact report, without changing any
production alignment, backfill, Tier 2 support, matrix, or workbook behavior.

CONTEXT:
- Repository/worktree: XIC Extractor,
  branch `codex/shared-peak-identity-evidence`.
- Repo instructions:
  `AGENTS.md`, `docs/agent-subagent-routing.md`,
  `docs/agent-parameter-settings.md`.
- Active spec:
  `docs/superpowers/specs/2026-05-29-shared-peak-identity-evidence-explanation-pilot-design.md`.
- Implementation plan:
  `docs/superpowers/plans/2026-05-29-shared-peak-identity-slice0-implementation-plan.md`.
- Context7/package-semantics note:
  `docs/superpowers/notes/2026-05-29-shared-peak-identity-context7-package-audit.md`.
- Existing machine artifacts for Slice 0 acceptance:
  `output/tiered_backfill_candidate_gate_8raw_current/alignment_review.tsv`,
  `output/tiered_backfill_candidate_gate_8raw_current/alignment_cells.tsv`,
  `output/tier2_v0_1_coherence_8raw_current_gate/alignment_production_candidate_gate.tsv`.
- The candidate-gate TSV is family-level context only. It must not be treated
  as a sample-level Tier 2 RAW reread source or positive Tier 2 support.
- Current decision state: this is an explanation vocabulary validation slice.
  It emits raw readiness facts and no gating verdict. Slice 1 blast-radius and
  V2 label convergence are separate follow-up contracts.

CONSTRAINTS:
- Execute the reviewed implementation plan unless current evidence proves a
  smaller safe adjustment is needed.
- Keep scope limited to Slice 0 vocabulary validation.
- Do not implement Slice 1 blast-radius manifest/summary, V2 shadow label
  convergence, production promotion, selected peak scoring changes, backfill
  rescue changes, Tier 2 support-token derivation changes, CWT ridge tracking,
  RAW re-read, 8RAW rerun, 85RAW rerun, AsLS/baseline work, GUI work, workbook
  changes, or output-level defaults.
- Do not change `alignment_matrix.tsv`, `alignment_review.tsv`,
  `alignment_cells.tsv`, workbook schemas, `scripts.run_alignment`, or existing
  production output behavior.
- Treat manual oracle rows as calibration/explanation semantics only, not
  training data, allowlists, or production pass/fail rules.
- Treat CWT, RT, shape, pattern, DDA opportunity, and delta-mass context as
  evidence facts only. None may silently become a production gate.
- Preserve provenance: output rows must carry source artifact paths, SHA256
  where applicable, source roles, and source row identifiers.
- Preserve ambiguous matches: explanations must carry matched machine source
  row identifiers instead of silently choosing one machine row.
- Preserve verification integrity: do not weaken or bypass tests, token-domain
  validation, lint, generated-output checks, reviewer blockers, or source hash
  checks to make the goal pass; fix the root cause or report the blocker.
- Respect existing repo patterns and use `uv run` for no-RAW Python commands.
- Do not stage, commit, push, merge, revert, or delete unrelated files unless
  the user explicitly requests it.

DONE WHEN:
- `docs/superpowers/fixtures/shared_peak_identity_manual_oracle_v1.tsv` exists
  and encodes the seven seed-family manual oracle at the spec-defined row grain,
  including `pass`, `suspect`, `fail`, `human_unjudgeable`, and
  `not_applicable` context rows.
- `xic_extractor/alignment/shared_peak_identity_explanation/` exists and owns
  schema constants, token validation, oracle loading, machine artifact loading,
  evidence-vector assembly, explanation classification, run-facts generation,
  and writers.
- `tools/diagnostics/shared_peak_identity_explanation.py` exists as a thin
  diagnostic CLI and writes only Slice 0 outputs.
- `tools/diagnostics/INDEX.md` registers the new diagnostic entry point and
  states `diagnostic_only`, no RAW scanning, no `alignment_matrix.tsv` mutation,
  and Slice 0 outputs.
- Focused tests cover oracle schema/grain, enum/token closure, sentinel rows,
  sample_id/sample_stem joining, ambiguous machine matches, no-match behavior,
  evidence-vector provenance, seed-case explanation classes, run facts, CLI
  output, missing input errors, and no Slice 1 output emission.
- Focused tests prove scope-derived manual-fail rows with positive sample-level
  machine evidence are classified as a machine/manual disagreement, not
  `machine_agrees_with_manual`.
- Focused tests treat `matched_source_row_ids` as dynamic provenance, not a
  controlled enum; each listed ID must be traceable to emitted evidence/source
  rows.
- Focused tests include a metamorphic check proving classifier output is driven
  by evidence facts rather than family IDs.
- The real Slice 0 CLI run writes:
  `output/shared_peak_identity_evidence_explanation/shared_peak_identity_manual_oracle.tsv`,
  `shared_peak_identity_evidence_vectors.tsv`,
  `shared_peak_identity_explanations.tsv`,
  `shared_peak_identity_run_facts.tsv`, and
  `shared_peak_identity_explanation_report.md`.
- `shared_peak_identity_run_facts.tsv` has `slice=slice0`,
  `blast_radius_assessed=not_run_slice0`,
  `max_overfit_risk=unassessed`,
  `vocabulary_special_casing_detected=FALSE`,
  `seed_rows_explained=seed_rows_total`,
  `seed_rows_unexplained=0`, and `seed_rows_inconclusive=0`.
- No explanation row uses `evidence_gap_class=unexplained_machine_manual_gap`.
- The report opens with a compact decision summary containing
  `diagnostic_only`, Slice 0 facts, vocabulary-held/blocker status, top
  blocking rows/classes, and explicit next action. It must not present that
  summary as a V1 gating verdict or production-readiness claim.
- No Slice 1 blast-radius files are emitted.
- Plan and goal receive the required repo-routed read-only subagent review,
  and blocking findings are fixed or stopped for user decision.
- Implementation receives focused review/verification before completion, with
  blocking findings fixed or stopped for user decision.
- No unrelated dirty files are modified, staged, committed, pushed, merged, or
  reverted.

VERIFY:
- Run:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_shared_peak_identity_oracle.py tests\test_shared_peak_identity_schema.py tests\test_shared_peak_identity_loaders.py tests\test_shared_peak_identity_assembler.py tests\test_shared_peak_identity_classifier.py tests\test_shared_peak_identity_cli.py -q`
- Run:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\shared_peak_identity_explanation tools\diagnostics\shared_peak_identity_explanation.py tests\test_shared_peak_identity_oracle.py tests\test_shared_peak_identity_schema.py tests\test_shared_peak_identity_loaders.py tests\test_shared_peak_identity_assembler.py tests\test_shared_peak_identity_classifier.py tests\test_shared_peak_identity_cli.py`
- Run:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.shared_peak_identity_explanation --manual-oracle-tsv docs\superpowers\fixtures\shared_peak_identity_manual_oracle_v1.tsv --alignment-review-tsv output\tiered_backfill_candidate_gate_8raw_current\alignment_review.tsv --alignment-cells-tsv output\tiered_backfill_candidate_gate_8raw_current\alignment_cells.tsv --candidate-gate-tsv output\tier2_v0_1_coherence_8raw_current_gate\alignment_production_candidate_gate.tsv --output-dir output\shared_peak_identity_evidence_explanation`
- Inspect:
  `output\shared_peak_identity_evidence_explanation\shared_peak_identity_run_facts.tsv`
  for Slice 0 facts, all seed rows explained, and no V1 gating verdict.
- Inspect:
  `output\shared_peak_identity_evidence_explanation\shared_peak_identity_explanation_report.md`
  for clear separation of too-conservative, too-permissive, human-unjudgeable,
  and delta-mass context cases, with the compact decision summary first.
- Run:
  `git diff --check`
- Inspect:
  `git status --short --branch`.
- If any verification cannot run, stop and report the exact blocker and
  remaining risk.

OUTPUT:
- Changed files and generated artifact paths.
- Reviewer roles used and blocker fixes applied.
- Key implementation decisions and any deviation from the plan.
- Verification commands and observed results.
- Remaining risk, explicitly including that this is `diagnostic_only`,
  Slice 0-only, and not production readiness.
- Next action: Slice 1 blast-radius planning only if the Slice 0 vocabulary
  holds; commit/PR only if the user asks.

STOP RULES:
- Stop if implementation would require RAW access, 8RAW/85RAW rerun,
  production matrix mutation, workbook schema changes, selected peak scoring
  changes, backfill rescue behavior changes, or Tier 2 support derivation
  changes.
- Stop if the manual oracle cannot encode sample scope without ambiguity.
- Stop if existing machine artifacts cannot identify machine labels or blockers
  for reviewed cells.
- Stop if classifier logic requires family-specific exceptions to make the seed
  rows pass.
- Stop if multiple machine rows match an oracle row and cannot be represented
  without silent candidate selection.
- Stop if the family-level candidate-gate TSV would need to be treated as
  sample-level Tier 2 evidence to make explanations pass.
- Stop if any seed row remains `unexplained`, unresolved `inconclusive`, or
  classified as `unexplained_machine_manual_gap`; emit diagnostic artifacts if
  useful, but do not mark the goal complete.
- Stop on missing secrets, production credentials, destructive data operations,
  unsafe permissions, unclear product decisions, or reviewer findings that
  contradict the user's product direction.
- Stop after three failed attempts on the same symptom and revisit the
  root-cause hypothesis.
- Do not mark complete until the current state has been checked against
  DONE WHEN and VERIFY.
```
