# Provisional Backfill Diagnostic Sidecar Pilot Goal

```text
/goal
GOAL:
Implement the reviewed diagnostic-only provisional backfill candidate sidecar
pilot so retained provisional backfill rows can be classified in
`alignment_production_candidate_gate.tsv` without changing the primary
`alignment_matrix.tsv` contract.

CONTEXT:
- Repository/worktree: XIC Extractor,
  `codex/tiered-backfill-machine-decision`.
- Repo instructions:
  `AGENTS.md`, `docs/agent-subagent-routing.md`, and
  `docs/agent-parameter-settings.md`.
- Active spec:
  `docs/superpowers/specs/2026-05-29-provisional-backfill-production-candidate-gate-design.md`.
- Implementation plan:
  `docs/superpowers/plans/2026-05-29-provisional-backfill-diagnostic-sidecar-pilot-implementation-plan.md`.
- Evidence notes:
  `docs/superpowers/notes/2026-05-29-provisional-backfill-candidate-gate-85raw-evidence-note.md`.
- Existing validation artifacts:
  `output\tiered_backfill_candidate_gate_8raw_current\alignment_review.tsv`,
  `output\tiered_backfill_candidate_gate_8raw_current\alignment_cells.tsv`,
  `output\tiered_backfill_candidate_gate_8raw_current\alignment_matrix.tsv`,
  `output\tiered_backfill_candidate_gate_85raw_current\alignment_review.tsv`,
  `output\tiered_backfill_candidate_gate_85raw_current\alignment_cells.tsv`,
  and
  `output\tiered_backfill_candidate_gate_85raw_current\alignment_matrix.tsv`.
- Current decision state: 8RAW and 85RAW support a selective
  `diagnostic_only` sidecar pilot; they do not prove production readiness or
  authorize primary matrix promotion.
- Existing code surfaces to preserve:
  `xic_extractor/alignment/machine_decision.py`,
  `xic_extractor/alignment/matrix_identity.py`,
  `xic_extractor/alignment/tsv_writer.py`,
  `tools/diagnostics/INDEX.md`, and
  `tools/diagnostics/analyze_matrix_identity_blast_radius.py`.

CONSTRAINTS:
- Execute the reviewed implementation plan unless current evidence proves a
  smaller safe adjustment is needed.
- Keep scope limited to the diagnostic sidecar pilot; do not add unrelated
  cleanup, refactors, GUI/workbook work, ASLS/resolver changes, or broader Tier
  2 routing.
- Do not change `alignment_matrix.tsv` column names, row inclusion semantics,
  row count for existing artifacts, or downstream correction/statistics
  meaning.
- Do not mutate `alignment_review.tsv`, workbook sheets, output levels,
  `scripts.run_alignment` defaults, or existing validation artifacts except for
  writing the new sidecar TSV/JSON under the task-specific output directories.
- Treat `production_candidate` as a sidecar status only. It is not
  `production_ready`, not a product role, and not authority to include rows in
  the primary matrix.
- Treat owner-backfill provenance, `trace_quality=owner_backfill`, RT coherence,
  scan-support distribution, and local-apex consistency as dependent context,
  not positive promotion support. `production_candidate` requires an explicit
  independent non-provenance Tier 2 support source.
- Emit source artifact paths and SHA256 hashes in the sidecar or JSON summary so
  stale-artifact risk is auditable.
- Use existing 8RAW/85RAW artifacts for acceptance unless a concrete freshness
  issue makes them invalid; do not launch another 85RAW run by default.
- If a RAW run becomes necessary, use the documented foreground
  `xic-raw-validation` command shape with heartbeat/timing sidecars. Do not use
  background `Start-Process`.
- Verification integrity: do not weaken or bypass tests, assertions, lint,
  validation, generated-output checks, source hashes, or reviewer blockers to
  make the goal pass; fix the root cause or report the blocker.
- Respect repository instructions and existing Python/diagnostic-tool patterns.
- Do not stage, commit, push, merge, or revert unrelated work unless the user
  explicitly requests it.

DONE WHEN:
- `xic_extractor/alignment/production_candidate_gate.py` exists and owns the
  pure domain evaluator for candidate eligibility, Tier 2 support components,
  dependent context, challenge blockers, source hashing, summary counts, and
  sidecar row projection.
- `tools/diagnostics/provisional_backfill_candidate_gate.py` exists as a thin
  diagnostic CLI that reads an alignment output directory and writes
  `alignment_production_candidate_gate.tsv` plus
  `alignment_production_candidate_gate.json`.
- `tools/diagnostics/INDEX.md` registers the new diagnostic entry-point and
  clearly marks it `diagnostic_only` and non-authoritative for
  `alignment_matrix.tsv`.
- Focused tests cover positive sidecar candidate classification with explicit
  independent Tier 2 support, no-promotion fallback without that support,
  neighboring interference / low coverage blockers, exact-token `review_only`,
  `rescue_only_review` non-exclusion, source hashes, missing artifacts, missing
  columns, CLI sidecar writing, and matrix hash/row-count parity.
- Existing 8RAW and 85RAW artifact directories have the new sidecar TSV/JSON
  generated from existing artifacts, with JSON summaries reporting
  `readiness_label=diagnostic_only`, `production_ready=false`, and
  `matrix_contract_changed=false`. Because these are artifact-only inputs with
  no independent Tier 2 source, `production_candidate_count=0` is expected.
- A validation note records 8RAW/85RAW sidecar counts, source hashes,
  verification commands, and the remaining production-readiness limit.
- `alignment_matrix.tsv` remains primary-only; no row is promoted because of
  this sidecar.
- Plan and goal have been reviewed by the required repo-local read-only
  reviewers, and blocking findings are fixed or explicitly stopped for user
  decision.
- No unrelated dirty files are modified, staged, committed, pushed, merged, or
  reverted.

VERIFY:
- Run:
  `.venv\Scripts\python.exe -m pytest tests\test_production_candidate_gate.py tests\test_provisional_backfill_candidate_gate_cli.py tests\test_alignment_machine_decision.py tests\test_matrix_identity_blast_radius.py tests\test_alignment_tsv_writer.py::test_one_detected_provisional_retention_stays_out_of_primary_matrix tests\test_alignment_tsv_writer.py::test_production_candidate_sidecar_status_does_not_change_matrix_writer -q`
- Run:
  `.venv\Scripts\python.exe -m ruff check xic_extractor\alignment\production_candidate_gate.py tools\diagnostics\provisional_backfill_candidate_gate.py tests\test_production_candidate_gate.py tests\test_provisional_backfill_candidate_gate_cli.py tests\test_alignment_tsv_writer.py`
- Run:
  `.venv\Scripts\python.exe -m tools.diagnostics.provisional_backfill_candidate_gate --alignment-dir output\tiered_backfill_candidate_gate_8raw_current --output-dir output\tiered_backfill_candidate_gate_8raw_current`
- Run:
  `.venv\Scripts\python.exe -m tools.diagnostics.provisional_backfill_candidate_gate --alignment-dir output\tiered_backfill_candidate_gate_85raw_current --output-dir output\tiered_backfill_candidate_gate_85raw_current`
- Inspect:
  both `alignment_production_candidate_gate.json` summaries for
  `readiness_label=diagnostic_only`, `production_ready=false`,
  `matrix_contract_changed=false`, source SHA256 fields, and expected retention
  candidate row counts. For the existing artifact-only 8RAW/85RAW inputs,
  expect `production_candidate_count=0`.
- Inspect:
  existing `alignment_matrix.tsv` hashes and row counts remain unchanged after
  running the diagnostic CLI.
- Run:
  `rg -n "paste the observed|concrete value|prose instruction" docs\superpowers\notes\2026-05-29-provisional-backfill-diagnostic-sidecar-pilot-validation-note.md`
  and expect no matches.
- Run:
  `git diff --check -- xic_extractor\alignment\production_candidate_gate.py tools\diagnostics\provisional_backfill_candidate_gate.py tests\test_production_candidate_gate.py tests\test_provisional_backfill_candidate_gate_cli.py tests\test_alignment_tsv_writer.py tools\diagnostics\INDEX.md docs\superpowers\notes\2026-05-29-provisional-backfill-diagnostic-sidecar-pilot-validation-note.md`
- Inspect:
  `git status --short --branch`.
- If any verification cannot run, stop and report the exact blocker and the
  remaining risk.

OUTPUT:
- Changed files and generated sidecar/validation artifact paths.
- Reviewer roles used and blocker fixes applied.
- Key implementation decisions, especially any deviation from the plan.
- Verification output, including focused tests, ruff, docs smoke, diff check,
  and 8RAW/85RAW sidecar acceptance.
- Remaining risk, explicitly including that this is `diagnostic_only` and not
  production readiness.
- Next action: continue to execution review, commit/PR only if the user asks, or
  write a separate promotion contract only after stronger evidence exists.

STOP RULES:
- Stop if implementation would require changing `alignment_matrix.tsv`,
  workbook schemas, `scripts.run_alignment` defaults, or output-level behavior.
- Stop if the only possible `production_candidate` support is dependent
  owner-backfill context; emit or keep `keep_provisional` / `audit` instead.
- Stop if source artifact hashes cannot be emitted or verified.
- Stop before primary matrix promotion; it requires a separate reviewed
  promotion contract.
- Stop before rerunning 85RAW when current artifacts and hashes already answer
  determinism and scale.
- Stop on missing RAW/DLL paths, unsafe permissions, secrets, production
  credentials, destructive data operations, unclear product decisions, or
  reviewer findings that contradict the user's product direction.
- Stop after three failed attempts on the same symptom and revisit the
  root-cause hypothesis.
- Do not mark complete until the current state has been checked against
  DONE WHEN and VERIFY.
```
