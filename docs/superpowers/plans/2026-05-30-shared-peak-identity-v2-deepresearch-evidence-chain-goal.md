# Shared Peak Identity V2 DeepResearch Evidence-Chain Goal

```text
/goal
GOAL:
Absorb the user-supplied feature-recognition DeepResearch synthesis into the
Shared Peak Identity V2 evidence-chain roadmap so the next checkpoint has a
clear diagnostic-only path from RAW-backed MS1 trace evidence to an
interpretable peak-quality feature vector and shadow-label alignment, without
implying product promotion.

CONTEXT:
- Repo contract: AGENTS.md.
- Goal routing and validation tiers: docs/agent-subagent-routing.md and
  docs/agent-parameter-settings.md.
- DeepResearch input: user-supplied external local markdown
  Feature Recognition_deepresearch_MLDL_chatgpt_deepresearch.md, not committed.
- Current Shared Peak Identity spec:
  docs/superpowers/specs/2026-05-29-shared-peak-identity-evidence-explanation-pilot-design.md.
- Current V1.5 / V2 plan:
  docs/superpowers/plans/2026-05-30-shared-peak-identity-v15-v2-implementation-plan.md.
- Current V2 diagnostic note:
  docs/superpowers/notes/2026-05-30-shared-peak-identity-v2-diagnostic-note.md.
- Current diagnostic implementation:
  tools/diagnostics/shared_peak_identity_explanation.py and
  xic_extractor/alignment/shared_peak_identity_explanation/.

CONSTRAINTS:
- Keep this checkpoint diagnostic_only.
- Scope fuse: this goal may update the Shared Peak Identity spec, V2 plan, V2
  diagnostic note, and this goal contract only; new code, CLI flags, schemas,
  tests, generated outputs, PR settings, or product behavior require a separate
  reviewed goal/plan.
- Do not change selected peaks, backfill behavior, primary matrices, workbook
  schemas, alignment_matrix.tsv, or product labels.
- Treat the DeepResearch synthesis as design input only. Any metric that will
  close a V2 blocker still needs a paper, official-method document, or
  repo-local validation artifact as provenance.
- Preserve the separation between candidate generation and peak-quality
  classification. Existing alignment/rescue candidates provide recall; the V2
  evidence chain explains quality and identity confidence.
- Do not introduce ML/DL model training, CNN inference, mzML conversion, or a new
  diagnostic entrypoint in this checkpoint.
- Missing DDA/MS2 evidence remains not_observed unless acquisition opportunity
  and comparable controls justify stronger negative evidence.
- Verification integrity: do not weaken or bypass tests, assertions, lint,
  typecheck, validation, generated-output checks, Markdown checks, or external
  blockers to make the goal pass; fix the root cause or report the blocker.
- External outcomes such as PR approval, future product promotion, model
  accuracy, or literature acceptance are not guaranteed by this goal.
- If repository or platform settings require owner access, document them as
  manual steps or blockers instead of guessing.

DONE WHEN:
- The Shared Peak Identity spec records the DeepResearch-derived method
  direction, non-goals, and evidence-chain requirements.
- The V1.5 / V2 implementation plan names the next actionable checkpoint: a
  RAW-backed MS1 peak-quality feature-vector sidecar over existing candidates.
- The V2 diagnostic note states the updated verdict: PR #76 makes formal shape
  observable, but V2 product labeling still needs a richer peak-quality vector,
  opportunity policy, and stratified oracle/generalization evidence.
- No code, CLI, schema, generated artifact, or production behavior is changed by
  this absorption step.
- The edited Markdown has balanced fences and the git diff contains no unrelated
  files.

VERIFY:
- Run a Markdown fence/balance smoke check over the touched docs and record the
  output.
- Run git diff --check and record the output.
- Inspect git status --short --branch and confirm only intended docs changed.
- Inspect the edited Markdown diff for scope, stale wording, private local path
  leakage, and overclaiming.
- If verification cannot run, stop and explain the exact blocker.

OUTPUT:
- Changed files.
- Key absorbed design decisions.
- Verification output.
- Remaining V2 evidence gaps and next recommended checkpoint.

STOP RULES:
- Stop on secrets, production credentials, production access, destructive data
  operations, unclear product decisions, unsafe permissions, or any need to
  change repository/platform settings.
- Stop if absorbing the DeepResearch input would require product label
  promotion, primary matrix mutation, new RAW extraction, or a new ML dependency.
- Stop if DeepResearch claims conflict with repo-local evidence or official docs
  in a way that changes the evidence contract.
- Stop after three failed attempts on the same Markdown or validation symptom and
  revisit the goal scope.
- Do not mark complete until the current state has been checked against DONE
  WHEN.
```
