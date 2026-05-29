# Tier 2 Sidecar Provenance Gate Checkpoint Goal

```text
/goal
GOAL:
Implement the reviewed Tier 2 sidecar provenance gate checkpoint so retained
provisional backfill rows can receive `validated_tier2_trace_evidence` support
only from a provenance-valid sidecar join, never from direct
`alignment_review.tsv` tokens.

CONTEXT:
- Repository/worktree: XIC Extractor,
  `C:\Users\user\Desktop\XIC_Extractor`,
  branch `codex/tiered-backfill-machine-decision`.
- Repo instructions:
  `AGENTS.md`, `docs/agent-subagent-routing.md`, and
  `docs/agent-parameter-settings.md`.
- Active spec:
  `docs/superpowers/specs/2026-05-29-tier2-evidence-producer-provenance-contract-design.md`.
- Implementation plan:
  `docs/superpowers/plans/2026-05-29-tier2-sidecar-provenance-gate-checkpoint-plan.md`.
- Existing implementation baseline:
  `xic_extractor/alignment/production_candidate_gate.py`,
  `tools/diagnostics/provisional_backfill_candidate_gate.py`,
  `tests/test_production_candidate_gate.py`,
  `tests/test_provisional_backfill_candidate_gate_cli.py`, and
  `tests/test_alignment_tsv_writer.py`.
- Pre-checkpoint known gap:
  `evaluate_production_candidate_gate()` accepted
  `independent_tier2_support_components=validated_tier2_trace_evidence`
  directly from review rows. This goal removes that diagnostic seam.
- Execution mode:
  checkpoint mode using `superpowers:executing-plans`, not
  `superpowers:subagent-driven-development` by default, because the change is a
  tightly coupled gate/CLI/test contract with overlapping write files. Use
  read-only reviewer subagents before execution per repo routing; use a tester
  subagent only if final verification needs an independent clean-context check.

CONSTRAINTS:
- Execute the reviewed checkpoint plan unless current evidence proves a smaller
  safe adjustment is needed.
- Keep scope limited to sidecar-only gate ingestion and provenance validation;
  do not implement RAW trace re-reading, Thermo DLL access, manual EIC import,
  primary matrix promotion, workbook changes, GUI work, resolver changes, or
  unrelated cleanup.
- Preserve `alignment_matrix.tsv` column names, row inclusion semantics, row
  counts for existing artifacts, workbook schemas, and downstream
  correction/statistics meaning.
- Preserve existing no-sidecar diagnostic behavior: artifact-only 8RAW/85RAW
  candidate gate runs must remain conservative and produce no production
  candidates without a valid Tier 2 sidecar.
- Positive support may come only from a sidecar row with matching review/cell
  source hashes, matching RAW manifest hash, matching candidate subset hash and
  count, allowlisted criteria version, recognized producer version,
  `evidence_status=validated`, `support_component=validated_tier2_trace_evidence`,
  `raw_trace_reread_status=pass`, `coherence_status=pass`, all required v0 RAW
  trace and rescued-cell coherence metric columns present and threshold-passing,
  and no hard blockers.
- Treat owner-backfill context, targeted/ISTD/evidence-spine context, and direct
  review-row support tokens as non-promoting context in this checkpoint.
- Do not run 85RAW. If a RAW run becomes necessary, stop and write a new RAW
  producer checkpoint plan using `docs/agent-parameter-settings.md` and
  `xic-raw-validation`.
- Verification integrity: do not weaken or bypass tests, assertions, lint,
  validation, generated-output checks, source hashes, provenance checks, or
  reviewer blockers to make the goal pass; fix the root cause or report the
  blocker.
- Respect repository instructions and existing diagnostic-tool patterns.
- Do not stage, commit, push, merge, revert, rename, or delete unrelated work
  unless the user explicitly requests it.

DONE WHEN:
- The plan and this goal have been reviewed by repo-routed read-only subagents
  and blocking findings are fixed or stopped for user decision.
- `xic_extractor/alignment/production_candidate_gate.py` exposes a Tier 2
  sidecar contract helper and accepts optional sidecar evidence in
  `evaluate_production_candidate_gate()`.
- Direct `alignment_review.tsv`
  `independent_tier2_support_components=validated_tier2_trace_evidence` no
  longer produces `production_candidate` without valid sidecar evidence.
- A valid synthetic Tier 2 sidecar plus RAW manifest can produce
  `production_candidate` in the diagnostic sidecar while keeping
  `production_ready=false` and `matrix_contract_changed=false`; the valid
  fixture includes the full v0 sidecar schema, not just hashes and status flags.
- Stale source hashes, stale RAW manifest hash, candidate subset mismatch,
  unknown criteria version, unknown producer version, inconclusive sidecar rows,
  missing support component, RAW/coherence non-pass status, missing or blank v0
  metric fields, failed v0 thresholds, and hard challenge blockers cannot
  promote.
- `tools/diagnostics/provisional_backfill_candidate_gate.py` accepts paired
  `--tier2-trace-evidence-tsv` and `--tier2-raw-manifest-tsv` flags, rejects
  unpaired Tier 2 args, and records Tier 2 provenance summary fields when used.
- `tools/diagnostics/INDEX.md` documents the sidecar-only support path.
- A validation note records the current commands, results, and remaining
  `diagnostic_only` risk.
- No unrelated dirty scope remains beyond the checkpoint files and expected
  generated no-sidecar smoke output.

VERIFY:
- Run:
  `python -m pytest tests\test_production_candidate_gate.py tests\test_provisional_backfill_candidate_gate_cli.py tests\test_alignment_tsv_writer.py::test_direct_tier2_review_token_does_not_change_matrix_writer -q`
- Run:
  `python -m ruff check xic_extractor\alignment\production_candidate_gate.py tools\diagnostics\provisional_backfill_candidate_gate.py tests\test_production_candidate_gate.py tests\test_provisional_backfill_candidate_gate_cli.py tests\test_alignment_tsv_writer.py`
- Run existing 8RAW no-sidecar smoke only:
  `python -m tools.diagnostics.provisional_backfill_candidate_gate --alignment-dir output\tiered_backfill_candidate_gate_8raw_current --output-dir output\tiered_backfill_candidate_gate_8raw_current`
- Inspect:
  `output\tiered_backfill_candidate_gate_8raw_current\alignment_production_candidate_gate.json`
  for `readiness_label=diagnostic_only`, `row_count=7`,
  `production_candidate_count=0`, `production_ready=false`, and
  `matrix_contract_changed=false`.
- Run:
  `rg -n "paste observed|<paste|TBD|TODO" docs\superpowers\notes\2026-05-29-tier2-sidecar-provenance-gate-checkpoint-validation-note.md`
  and expect no matches.
- Run:
  `git diff --check -- xic_extractor\alignment\production_candidate_gate.py tools\diagnostics\provisional_backfill_candidate_gate.py tests\test_production_candidate_gate.py tests\test_provisional_backfill_candidate_gate_cli.py tests\test_alignment_tsv_writer.py tools\diagnostics\INDEX.md docs\superpowers\plans\2026-05-29-tier2-sidecar-provenance-gate-checkpoint-plan.md docs\superpowers\plans\2026-05-29-tier2-sidecar-provenance-gate-checkpoint-goal.md docs\superpowers\notes\2026-05-29-tier2-sidecar-provenance-gate-checkpoint-validation-note.md`
- Inspect:
  `git status --short --branch`.
- If verification cannot run, stop and report the exact blocker and remaining
  risk.

OUTPUT:
- Changed files and generated artifact paths.
- Reviewer roles used, blocking findings, and fixes applied.
- Key decisions, especially checkpoint-mode scope and why RAW producer work is
  deferred.
- Verification output for pytest, ruff, 8RAW no-sidecar smoke, docs smoke, diff
  check, and git status.
- Remaining risk, explicitly including that this is `diagnostic_only` and does
  not prove RAW evidence quality or production readiness.
- Next action: RAW trace re-read producer checkpoint, not primary matrix
  promotion.

STOP RULES:
- Stop if implementation would require changing `alignment_matrix.tsv`, workbook
  schemas, `scripts.run_alignment` defaults, output levels, or primary matrix
  row inclusion semantics.
- Stop if the gate must re-read RAW data; RAW trace re-read belongs to a
  separate producer checkpoint.
- Stop if positive support can only be inferred from owner-backfill context,
  targeted/ISTD context, or direct review-row tokens.
- Stop if source hashes, RAW manifest hash, candidate subset hash/count,
  criteria version, or producer version cannot be verified.
- Stop before launching 85RAW or any long RAW/DLL run.
- Stop on missing RAW/DLL paths, unsafe permissions, secrets, production
  credentials, destructive data operations, unclear product decisions, or
  reviewer findings that contradict the user-approved checkpoint direction.
- Stop after three failed attempts on the same symptom and revisit the
  root-cause hypothesis.
- Do not mark complete until the current state has been checked against
  DONE WHEN and VERIFY.
```
