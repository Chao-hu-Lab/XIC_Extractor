# RAW Validation Contract

Use this before launching or accepting RAW-backed evidence.

## Required Reading

Read first:

- `AGENTS.md`
- `docs/agent-parameter-settings.md`
- `docs/agent-subagent-routing.md`
- active validation spec, plan, output index, or note

Search existing artifacts before rerunning:

- `tools/diagnostics/INDEX.md`
- relevant `docs/superpowers/notes/`
- task-specific `output/` directories

## Reviewer Trigger

Use `validation-evidence-reviewer` for:

- any 85RAW run;
- likely >30 minute RAW run;
- production-equivalent validation;
- benchmark or gate acceptance that affects product readiness.

Use mode `preflight` before launch and mode `acceptance`, `science`, or
`performance` after the run as appropriate.

## Output Surface Rules

For large alignment validation, the primary machine delivery surface is
`alignment_matrix.tsv`. Targeted benchmark diagnostics also need
`alignment_review.tsv` and `alignment_cells.tsv`.

Do not produce `.xlsx`, HTML, owner-edge, status-matrix, event-owner, or
ambiguous-owner outputs for large validation unless a human review or debug task
explicitly needs them.

## Acceptance Labels

- `run_ok`: command completed and emitted expected artifacts.
- `gate_ok`: artifacts satisfy the stated gate.
- `production_ready`: evidence supports production behavior.
- `inconclusive`: result cannot close the decision; name missing evidence or
  exit rule.
