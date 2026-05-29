# Tier 2 V0 Coherence Diagnostic Goal

```text
/goal
GOAL:
Implement the reviewed `diagnostic_only` Tier 2 v0.1 coherence criteria
sidecar pilot so RAW trace re-read output exposes signal/shape/noise,
boundary-reference, apex-span, and neighbor-interference context without
promoting rows or changing `alignment_matrix.tsv`.

CONTEXT:
- Repository/worktree: active XIC Extractor worktree,
  branch `codex/tiered-backfill-machine-decision`.
- Repo instructions:
  `AGENTS.md`, `docs/agent-subagent-routing.md`, and
  `docs/agent-parameter-settings.md`.
- Reviewed spec:
  `docs/superpowers/specs/2026-05-29-tier2-v0-coherence-criteria-review-design.md`.
- Implementation plan:
  `docs/superpowers/plans/2026-05-29-tier2-v0-coherence-diagnostic-plan.md`.
- Existing implementation baseline:
  `xic_extractor/alignment/tier2_trace_producer.py`,
  `xic_extractor/alignment/production_candidate_gate.py`,
  `tools/diagnostics/tier2_raw_trace_reread_producer.py`,
  `tools/diagnostics/provisional_backfill_candidate_gate.py`,
  `tests/test_tier2_raw_trace_producer.py`,
  `tests/test_tier2_raw_trace_reread_producer_cli.py`,
  `tests/test_production_candidate_gate.py`,
  `tests/test_provisional_backfill_candidate_gate_cli.py`, and
  `tests/test_alignment_tsv_writer.py`.
- Required baseline artifacts and hashes are listed in the spec's
  `Pilot Preconditions` table. They must match before the 8RAW v0.1 rerun.
- Execution mode:
  checkpoint mode using `superpowers:executing-plans`, not
  `superpowers:subagent-driven-development` by default, because the write
  surface is a tightly coupled producer/gate/schema/test contract. Use
  repo-routed read-only reviewer subagents before execution and after
  implementation.

CONSTRAINTS:
- Execute the reviewed plan unless current evidence proves a smaller safe
  adjustment is needed.
- Keep scope limited to the v0.1 diagnostic sidecar pilot and gate consumption
  guardrails; do not promote retained provisional rows, change
  `alignment_matrix.tsv`, workbook schemas, `scripts.run_alignment` defaults,
  matrix writer behavior, or downstream correction/statistics contracts.
- v0.1 criteria must use a new criteria version distinct from
  `tier2_trace_identity_rescued_coherence_v0`.
- v0.1 sidecar rows must expose diagnostic context but must not provide
  positive Tier 2 support. Any v0.1 row that reaches the gate remains audit or
  keep-provisional context, with `production_ready=false`.
- Preserve existing v0 sidecar diagnostic-gate compatibility where needed,
  including current v0 synthetic positive-support fixture behavior. This is
  compatibility for the committed diagnostic sidecar contract, not production
  readiness and not a primary matrix promotion path.
- Keep scan availability separate from signal/shape/noise context. Do not treat
  scan-count ratio alone as positive support.
- Keep boundary-reference and apex-span metrics diagnostic until a later
  reviewed plan chooses a hard gate.
- Keep neighbor interference as `not_assessed` context until a formal
  computation exists.
- Do not run 85RAW. A later 85RAW run requires a reviewed follow-up plan after
  the v0.1 8RAW diagnostic rerun is `run_ok` and the diagnostic gate is
  `gate_ok` for the decision that larger run can close.
- Verification integrity: do not weaken or bypass tests, assertions, lint,
  validation, generated-output checks, source hashes, provenance checks, or
  reviewer blockers to make the goal pass; fix the root cause or report the
  blocker.
- Respect repository instructions and existing diagnostic-tool patterns.
- Do not stage, commit, push, merge, revert, rename, or delete unrelated work
  unless the user explicitly requests it.

DONE WHEN:
- The spec has been reviewed by repo-routed read-only subagents and blocking
  findings are fixed.
- This goal and the implementation plan have been reviewed by repo-routed
  read-only subagents and blocking findings are fixed or stopped for user
  decision.
- `tier2_trace_producer.py` emits v0.1 diagnostic columns for scan
  availability, signal/noise/shape context, three boundary-reference views,
  raw/seed-rescued/rescued-only apex spans, and neighbor-interference
  not-assessed context.
- `production_candidate_gate.py` can load v0.1 sidecars, keeps provenance checks
  intact, and prevents v0.1 diagnostic rows from producing positive support.
- Legacy v0 sidecars remain loadable with the current v0 diagnostic-gate
  semantics, and v0.1 sidecars with missing new columns are rejected.
- CLI producer and gate outputs remain paired sidecars and summaries; no
  primary matrix or workbook contract changes.
- Focused unit/contract tests cover v0.1 schema, metric calculations,
  diagnostic-only gate behavior, and backward-compatible v0 artifact loading.
- An 8RAW diagnostic rerun writes v0.1 sidecars and a gate consume output with
  `readiness_label=diagnostic_only`, `production_candidate_count=0`,
  `production_ready=false`, and `matrix_contract_changed=false`.
- A validation note records commands, results, changed artifacts, and remaining
  risk.
- Final implementation has a repo-routed subagent review/acceptance pass, and
  blockers are fixed or explicitly deferred as non-blocking.

VERIFY:
- Run focused no-RAW tests:
  `python -m pytest tests\test_tier2_raw_trace_producer.py tests\test_tier2_raw_trace_reread_producer_cli.py tests\test_production_candidate_gate.py tests\test_provisional_backfill_candidate_gate_cli.py tests\test_alignment_tsv_writer.py::test_direct_tier2_review_token_does_not_change_matrix_writer -q`
- Run focused lint:
  `python -m ruff check xic_extractor\alignment\tier2_trace_producer.py xic_extractor\alignment\production_candidate_gate.py tools\diagnostics\tier2_raw_trace_reread_producer.py tools\diagnostics\provisional_backfill_candidate_gate.py tests\test_tier2_raw_trace_producer.py tests\test_tier2_raw_trace_reread_producer_cli.py tests\test_production_candidate_gate.py tests\test_provisional_backfill_candidate_gate_cli.py tests\test_alignment_tsv_writer.py`
- Verify the current 8RAW precondition hashes before rerun:
  `Get-FileHash` against the five artifact hashes listed in the spec.
- Run the v0.1 8RAW producer with `.venv\Scripts\python.exe` and the
  documented 8RAW RAW/DLL paths from `docs/agent-parameter-settings.md`.
- Run the gate consume command against the v0.1 sidecar/manifest pair using
  `python -m tools.diagnostics.provisional_backfill_candidate_gate`.
- Inspect the producer and gate JSON summaries for `diagnostic_only`,
  `production_ready=false`, `matrix_contract_changed=false`, and zero positive
  production candidates.
- Run docs smoke checks for placeholders, stale v0-only wording, trailing
  whitespace, and `git diff --check` on touched files.
- Inspect `git status --short --branch`.
- If verification cannot run, stop and report the exact blocker and remaining
  risk.

OUTPUT:
- Changed files and generated artifact paths.
- Reviewer roles used, blocking findings, and fixes applied.
- Key decisions, especially why v0.1 is diagnostic-only and why 85RAW is out of
  scope.
- Verification output for pytest, ruff, 8RAW producer, gate consume, docs smoke,
  diff check, and git status.
- Remaining risk, explicitly including that this proves diagnostic observability
  and not production readiness.
- Next action recommendation: review v0.1 8RAW evidence before considering any
  larger run or promotion contract.

STOP RULES:
- Stop if implementation would require changing `alignment_matrix.tsv`,
  workbook schemas, `scripts.run_alignment` defaults, output levels, primary
  matrix row inclusion semantics, or downstream correction/statistics contracts.
- Stop if v0.1 positive support can only be justified by owner-backfill
  provenance, scan count alone, direct review-row tokens, or uncomputed neighbor
  interference.
- Stop if current 8RAW precondition hashes do not match.
- Stop before launching 85RAW or any likely >30 minute RAW/DLL run.
- Stop on missing RAW/DLL paths, unsafe permissions, secrets, production
  credentials, destructive data operations, unclear product decisions, or
  reviewer findings that contradict the user-approved diagnostic-only direction.
- Stop after three failed attempts on the same symptom and revisit the
  root-cause hypothesis.
- Do not mark complete until the current state has been checked against
  DONE WHEN and VERIFY.
```
