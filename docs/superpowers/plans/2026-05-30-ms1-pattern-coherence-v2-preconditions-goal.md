# MS1 Pattern Coherence V2 Label Closeout Goal

## GOAL

Close the Shared Peak Identity V2 `formal_pattern_metric` precondition as far as
current artifacts allow by implementing a diagnostic-only MS1 pattern coherence
producer, wiring it into the existing V2 readiness path, and rerunning the
shared seed and d3-N6-medA probes. Do not enable production labels.

## CONTEXT

- Repo contract: `AGENTS.md`.
- Goal routing and validation tiers: `docs/agent-subagent-routing.md`,
  `docs/agent-parameter-settings.md`.
- Existing diagnostic entrypoint:
  `tools/diagnostics/shared_peak_identity_explanation.py`.
- Existing V2 note:
  `docs/superpowers/notes/2026-05-30-shared-peak-identity-v2-diagnostic-note.md`.
- Current implementation:
  `xic_extractor/alignment/shared_peak_identity_explanation/`.

## CONSTRAINTS

- Keep this phase `diagnostic_only`.
- Do not mutate `alignment_review.tsv`, `alignment_cells.tsv`,
  `alignment_matrix.tsv`, workbooks, selected peaks, backfill behavior, or
  production labels.
- Reuse the existing Shared Peak Identity diagnostic tool instead of adding a
  parallel entrypoint.
- Do not pretend coarse RT or shape evidence is a product label. Generated MS1
  pattern evidence can use alignment-cell apex/boundary facts, but must not fake
  raw trace-shape correlation.
- Boundary-only disagreement and unmodeled RT shift must be inconclusive unless
  independent evidence supports a conflict.
- Preserve verification integrity; do not weaken tests to make readiness pass.

## DONE WHEN

- The CLI can generate
  `shared_peak_identity_ms1_pattern_coherence_evidence.tsv` through
  `--generate-ms1-pattern-coherence-evidence`.
- `shared_peak_identity_machine_evidence_support.tsv` treats generated MS1
  pattern rows as machine-observed pattern evidence only when the generated row
  is supportive or partial/supportive.
- Weak boundary-only or unmodeled-shift rows remain `inconclusive` and do not
  close `formal_pattern_metric`.
- d3-N6-medA rerun demonstrates whether `formal_pattern_metric` closes when
  independent 85RAW matrix drift evidence is present.
- Focused tests cover supportive, conflict, inconclusive, CLI, and consumer
  contract behavior.

## VERIFY

Run focused no-RAW tests:

```powershell
python -m pytest tests\test_shared_peak_identity_ms1_pattern_coherence.py tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_cli.py -q
```

Run formatting/lint for touched Python files if implementation changes Python:

```powershell
uv --cache-dir .uv-cache run ruff check tools\diagnostics\shared_peak_identity_explanation.py xic_extractor\alignment\shared_peak_identity_explanation tests\test_shared_peak_identity_ms1_pattern_coherence.py tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_cli.py
```

## OUTPUT

- Changed files and new/updated diagnostic arguments.
- Verification commands and observed results.
- Shared seed and d3-N6-medA readiness artifacts.
- Remaining blockers before V2 product label readiness.

## STOP RULES

- Stop if the design requires RAW time-series extraction beyond an optional
  sidecar contract in this phase.
- Stop if product label promotion, matrix correction, workbook schema changes,
  or downstream contract changes become necessary.
- Stop after three repeated failures on the same test or command symptom and
  revisit the root-cause hypothesis.
