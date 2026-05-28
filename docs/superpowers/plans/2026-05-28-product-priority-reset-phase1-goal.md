# Product Priority Reset Phase 1 Goal

```text
/goal
GOAL:
Complete the Product Priority Reset Phase 1 qualitative selection gate by
executing the reviewed implementation plan and producing exactly one gate
classification ready for user acceptance.

CONTEXT:
- Repository/worktree:
  C:\Users\user\Desktop\XIC_Extractor\.worktrees\product-priority-reset
- Decision spec:
  docs/superpowers/specs/2026-05-28-product-priority-reset-decision-spec.md
- Implementation plan:
  docs/superpowers/plans/2026-05-28-product-priority-reset-phase1-implementation-plan.md
- Operational settings:
  docs/agent-parameter-settings.md
- Existing oracle notes:
  docs/superpowers/notes/2026-05-28-pr70-alignment-matrix-handoff-raw-validation-note.md
  docs/superpowers/notes/2026-05-24-resolver-default-switch-validation-note.md
  docs/superpowers/validation/identity_coherence_v04_8raw_acceptance_handoff.md
  docs/superpowers/notes/2026-05-27-asls-minimal-closeout-note.md
  tools/diagnostics/INDEX.md
- Stable local validation inputs:
  C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv
  C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\85raw\discovery_batch_index.csv

CONSTRAINTS:
- Execute the reviewed implementation plan unless live evidence forces a smaller
  safe adjustment that preserves the decision spec.
- Do not change production code, resolver defaults, baseline behavior, boundary
  selection, matrix schema, or diagnostic CLIs.
- Do not create broad new diagnostics, HTML/XLSX reports, external-tool audits,
  ML/DL scaffolding, or Phase2 cleanup work.
- Use C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe for RAW /
  alignment commands unless a verified worktree .venv junction exists.
- Do not use Start-Process or background polling for RAW validation.
- 85RAW: reuse accepted PR70 parity evidence by default. Run a new foreground
  85RAW only if 8RAW row evidence is GO, accepted 85RAW evidence is stale, and
  the refresh can change the classification, and the active worktree has a
  verified .venv runner compatible with `--expected-sample-count 85`. If that
  preflight is missing, classify as INCONCLUSIVE instead of relaunching a
  known-bad shape.
- Verification integrity: do not weaken or bypass tests, assertions, validation,
  generated-output checks, review gates, or external blockers to make the goal
  pass; fix the root cause or report the blocker.
- Keep scope limited to Phase 1 gate completion.

DONE WHEN:
- docs/superpowers/notes/2026-05-28-qualitative-selection-acceptance-gate-note.md
  exists.
- The gate note contains a fixed review manifest and per-row decision matrix
  evidence for the required Phase 1 rows, plus the V0.4 aggregate decoy oracle.
- The gate note contains exactly one authoritative `Final Classification:` line:
  GO_FOR_NEXT_NARROW_BEHAVIOR_PR, GO_FOR_NEXT_PRODUCT_DECISION_PR,
  NO_GO_FIX_SELECTION_OR_BOUNDARY_FIRST, or
  INCONCLUSIVE_NEEDS_NAMED_MINIMAL_EVIDENCE.
- The `d3-N6-medA / NormalBC2312_DNA` prior-warning row either resolves from
  target-derived `source_candidate_id` to a current primary matrix family, or
  the final classification is NO_GO or INCONCLUSIVE with the failing row key
  named as a blocker.
- If classification is GO, the gate note names exactly one recommended next
  product decision / PR target and ties it to reviewed evidence.
- If classification is NO_GO or INCONCLUSIVE, the gate note names the blockers
  with sample, label/family, status, missing/failing evidence, and cheapest next
  action.
- Subagent implementation review has been run on the completed gate note and
  blocking findings have been fixed or explicitly converted into the final gate
  classification.
- The gate note or final response records reviewer roles, blocking findings, and
  resolution status so the review gate is auditable outside the chat transcript.
- The final classification is reported to the user for explicit acceptance. Do
  not mark the runtime goal complete or start Phase 2 behavior work until the
  user accepts the classification.

VERIFY:
- Run the freshness checks and 8RAW row-evidence extraction from the
  implementation plan.
- Run the Markdown fence and placeholder smoke checks from the implementation
  plan.
- Run the gate-note contract-field verifier from the implementation plan.
- Capture command outputs and the final classification in the final response.
- If any verification cannot run, stop and explain the exact blocker.

OUTPUT:
- Changed files.
- Gate classification.
- Evidence used and validation commands run.
- Whether 85RAW was reused or refreshed, with reason.
- Remaining risk.
- Recommended next action.

STOP RULES:
- Stop on missing stable validation inputs, missing RAW/DLL/runtime paths,
  production access, production credentials, destructive data operations,
  secrets, unsafe permissions, or unclear product decisions.
- If 8RAW freshness or row evidence is NO_GO or INCONCLUSIVE, stop escalation
  to 85RAW and write the gate note as NO_GO or INCONCLUSIVE with named blockers.
- Stop after three failed attempts on the same symptom and revisit the root
  cause hypothesis.
- Do not mark complete until the current state has been checked against DONE
  WHEN and VERIFY.
```
