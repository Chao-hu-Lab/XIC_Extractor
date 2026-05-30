# Shared Peak Identity V2 Non-Delta Evidence Closeout Goal

```text
/goal
GOAL:
Close the Shared Peak Identity V2 diagnostic-only evidence-chain contract for
all current non-delta-mass evidence threads, so remaining blockers are expressed
as machine-readable sidecar/readiness fields rather than broad human-only notes.

CONTEXT:
- Repo contract: AGENTS.md.
- XIC goal / validation routing:
  docs/agent-subagent-routing.md and docs/agent-parameter-settings.md.
- Active design spec:
  docs/superpowers/specs/2026-05-29-shared-peak-identity-evidence-explanation-pilot-design.md.
- V2 diagnostic note:
  docs/superpowers/notes/2026-05-30-shared-peak-identity-v2-diagnostic-note.md.
- Diagnostic index:
  tools/diagnostics/INDEX.md.
- Current implementation surfaces:
  tools/diagnostics/shared_peak_identity_explanation.py,
  xic_extractor/alignment/shared_peak_identity_explanation/machine_evidence_support.py,
  xic_extractor/alignment/shared_peak_identity_explanation/schema.py.

CONSTRAINTS:
- Keep the work diagnostic_only / exploratory_only; do not promote product V2
  labels.
- Do not change selected peaks, backfill, alignment_matrix.tsv, workbooks, or
  downstream production contracts.
- Exclude delta_mass_family_model / FAM001227-FAM001239 related-family logic;
  that belongs to a future PR.
- Preserve existing sidecar inputs and fail-closed behavior.
- Missing expected NL/MS2 is opportunity context unless the DDA
  non-dispositive policy has explicit machine evidence.
- Verification integrity: do not weaken tests, lint, typecheck, assertions, or
  diagnostic status wording to pass.

DONE WHEN:
- The spec/note/index state that QC-nearby MS1 reference, MS1 shape/pattern,
  matrix RT drift with ISTD trend provenance, DDA missing-NL non-dispositive
  policy, and sample-level negative evidence are explicit V2 diagnostic
  contracts.
- `shared_peak_identity_machine_evidence_support.tsv` has
  `negative_evidence_basis_status`, `negative_evidence_class`, and
  `negative_evidence_detail`.
- Optional `--sample-negative-evidence-tsv` can close
  `sample_level_negative_evidence` with one of:
  `no_candidate_ms1_evidence`, `pattern_mismatch`, `rt_not_explained`, or
  `local_peak_not_decisive`.
- DDA missing-NL can close `dda_opportunity_policy` only when MS1 identity
  evidence is supportive, MS1 intensity is at least 2.5e4, boundary-aligned RAW
  MS2 trigger count is at least 3, and MS2 trace-strength proxy is
  moderate/strong.
- Delta-mass remains context-only / future work.

VERIFY:
- Run focused Shared Peak Identity schema, shadow-label, CLI, candidate-MS2,
  MS1-pattern, matrix-RT-drift, and QC-reference tests.
- Run ruff on touched Python files/tests.
- Run mypy on xic_extractor.
- Run git diff --check and inspect git status --short --branch.

OUTPUT:
- Changed code/test/docs paths.
- Exact verification commands and results.
- Current diagnostic_only verdict and remaining V2 risk.

STOP RULES:
- Stop on product promotion decisions, destructive operations, secrets, missing
  RAW/DLL paths for any RAW-backed validation, or contradictory repo evidence.
- Stop after three failed attempts on the same validation symptom and revisit
  root cause.
- Do not mark complete until DONE WHEN and VERIFY have been checked.
```
