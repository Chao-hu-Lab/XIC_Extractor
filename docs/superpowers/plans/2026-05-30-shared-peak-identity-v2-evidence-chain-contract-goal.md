# Shared Peak Identity V2 Evidence-Chain Contract Goal

```text
/goal
GOAL:
Implement the next Shared Peak Identity V2 diagnostic-only evidence-chain
checkpoint by expanding RAW-backed family MS1 overlay evidence into an
interpretable peak-quality feature vector, so formal MS1 shape support is
auditable as a chain of machine observations rather than only a shape
correlation score.

CONTEXT:
- Repo contract: AGENTS.md.
- Goal and validation routing:
  docs/agent-subagent-routing.md and docs/agent-parameter-settings.md.
- Active design spec:
  docs/superpowers/specs/2026-05-29-shared-peak-identity-evidence-explanation-pilot-design.md.
- Active V1.5 / V2 plan:
  docs/superpowers/plans/2026-05-30-shared-peak-identity-v15-v2-implementation-plan.md.
- V2 diagnostic note:
  docs/superpowers/notes/2026-05-30-shared-peak-identity-v2-diagnostic-note.md.
- Current implementation surfaces:
  xic_extractor/alignment/shared_peak_identity_explanation/ms1_pattern_coherence.py,
  xic_extractor/alignment/shared_peak_identity_explanation/ms1_peak_quality_vector.py,
  xic_extractor/alignment/shared_peak_identity_explanation/machine_evidence_support.py,
  tools/diagnostics/shared_peak_identity_explanation.py, and
  tools/diagnostics/family_ms1_overlay_writers.py.
- Existing RAW-backed overlay JSON already contains per-trace rt/intensity
  arrays, cell boundaries, cell height, local-window maxima, trace maxima, apex
  deltas, and apex-aligned shape similarity.

CONSTRAINTS:
- Keep the checkpoint diagnostic_only.
- Do not change selected peaks, backfill behavior, alignment_matrix.tsv,
  workbooks, primary matrices, product labels, or production promotion policy.
- Do not add a new diagnostic entrypoint or a new CLI flag unless existing
  wiring cannot carry the sidecar.
- Reuse existing family_ms1_overlay trace-data JSON provenance. Do not reread
  RAW files for this checkpoint.
- The feature vector is interpretable evidence, not an ML/DL model, classifier,
  or CNN commitment.
- Optional schema expansion is allowed for
  shared_peak_identity_ms1_pattern_coherence_evidence.tsv; established required
  columns must remain backward compatible.
- Missing or weak DDA/MS2 evidence remains not_observed unless a separate
  opportunity policy proves it should have been observable.
- Verification integrity: do not weaken tests, lint, typecheck, assertions, or
  diagnostic status language to make this pass.

DONE WHEN:
- The V2 spec and plan name the peak-quality feature-vector contract and its
  diagnostic-only boundary.
- Generated MS1 pattern coherence rows can include RAW-backed peak-quality
  vector columns derived from overlay rt/intensity arrays.
- Machine-evidence support records those vector fields in
  observed_machine_metrics.
- A RAW-backed trace_constellation row can close formal_shape_metric only when
  it has both the existing overlay shape basis and a machine-observed
  peak-quality vector basis.
- Overlay rows without rt/intensity vectors remain compatible, but do not count
  as the richer formal shape evidence chain.
- Focused regression tests cover supportive vector extraction, missing-vector
  fail-closed behavior, machine-evidence propagation, and CLI generation.
- The diagnostic index documents the expanded MS1 sidecar semantics.

VERIFY:
- Run focused tests for Shared Peak Identity MS1 pattern, machine evidence /
  shadow labels, and CLI coverage.
- Run ruff on touched Python files/tests.
- Run mypy on xic_extractor if the focused code changes type-checked modules.
- Run Markdown fence/balance smoke check for touched docs.
- Run git diff --check and inspect git status --short --branch.

OUTPUT:
- Changed code/test/docs paths.
- Exact verification commands and results.
- Current verdict using diagnostic_only / exploratory_only language.
- Remaining V2 evidence gaps after this checkpoint.

STOP RULES:
- Stop on secrets, production credentials, destructive operations, or need for
  product label promotion.
- Stop if the feature vector would require new RAW extraction, mzML conversion,
  external network access, or a new ML dependency.
- Stop if repo-local evidence contradicts the proposed schema semantics.
- Stop after three failed attempts on the same validation symptom and revisit
  the contract.
- Do not mark complete until DONE WHEN and VERIFY have been checked.
```
