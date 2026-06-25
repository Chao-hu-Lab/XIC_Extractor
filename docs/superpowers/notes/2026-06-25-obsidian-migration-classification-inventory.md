# Obsidian migration classification inventory

Date: 2026-06-25
Branch: `codex/docs-cleanup`
Status: working classification; not a deletion list

This inventory classifies the documentation surfaces touched by the current
docs-cleanup branch for a future repo-stub + Obsidian migration. It does not
authorize `git rm`, archive moves, or bulk Obsidian writes.

Disposition vocabulary is defined in
`docs/agent/obsidian-handoff-contract.md`.

## Classification Table

| Path | Disposition | Repo owner / replacement | Privacy risk | Agent handoff need | Obsidian target | Required before move | Destructive allowed now |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `AGENTS.md` | `keep_repo` | root routing contract | low | high | none | keep canonical refs current | no |
| `docs/agent/obsidian-handoff-contract.md` | `keep_repo` | Obsidian/repo hybrid contract | low | high | none | new canonical contract | no |
| `docs/project-layout.md` | `keep_repo` | directory and docs source-of-truth boundary | low | high | none | keep as repo public rule | no |
| `docs/agent/communication-review.md` | `keep_repo` | human review and closeout surface rules | low | high | none | keep as repo public rule | no |
| `docs/agent/codex-operating-system.md` | `keep_repo` | agent hooks/routing operating rules | low | high | none | keep as repo public rule | no |
| `docs/agent/product-validation-contract.md` | `keep_repo` | product validation language and public-surface discipline | low | high | none | keep as repo source-of-truth | no |
| `docs/lcms-msms-evidence-rules.md` | `keep_repo` | LC-MS/MS evidence rule source-of-truth | medium | high | none | keep formal evidence contract | no |
| `docs/diagnostic-ledger.md` | `keep_repo` | compact known diagnostic conclusions | medium | high | none | keep compact conclusions only | no |
| `docs/deepresearch/Backfill Production Gate.md` | `repo_stub_plus_obsidian` | control plane and evidence rules for current Backfill gate semantics | medium | medium | optional `[[XIC Backfill Production Gate Deep Notes]]` | stable claims are reflected in formal owners; keep same-path research stub or update exact referrers before full removal | no |
| `docs/superpowers/handoffs/README.md` | `keep_repo` | handoff lifecycle rules | low | high | none | keep branch-scoped handoff rules current | no |
| `docs/superpowers/handoffs/current/codex-docs-cleanup-official-docs-and-handoff.md` | `repo_stub_plus_obsidian` | active branch handoff stub | low | high | `[[XIC Docs Cleanup Hybrid Handoff]]` after pilot | keep stub self-sufficient before any Obsidian pointer is required | no |
| `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md` | `keep_repo` | productization status anchor | low | high | none | keep anchor phrases for checkers; not a branch handoff | no |
| `docs/superpowers/goals/README.md` | `keep_repo` | productization goal routing index | low | high | none | keep productization anchor vs branch handoff distinction | no |
| `docs/superpowers/goals/XIC_Extractor_Productization_Roadmap_Review.md` | `keep_repo` | active productization roadmap index | medium | high | optional deep notes only | keep link labels as productization status anchor, not universal handoff | no |
| `docs/superpowers/plans/README.md` | `keep_repo` | productization plan routing index | low | high | none | keep branch-specific handoff reading order | no |
| `docs/superpowers/plans/2026-06-15-productization-control-plane.md` | `keep_repo` | productization maturity tier and active lane authority | medium | high | none | update only when tier/lane/authority changes | no |
| `docs/superpowers/specs/productization_authority_manifest.v1.json` | `keep_repo` | product writer authority manifest and fail-closed policy | low | high | none | keep with productization checkers | no |
| `docs/superpowers/specs/mechanical_adjudication_schema.v1.json` | `keep_repo` | mechanical adjudication schema contract | low | high | none | keep with authority checker | no |
| `docs/superpowers/validation/mechanical_adjudication_index_v1.tsv` | `keep_repo` | mechanical adjudication index / ProductWriter authority evidence | medium | high | none | keep exact path for checkers and validation references | no |
| `docs/superpowers/validation/productization_status_index_v1.tsv` | `keep_repo` | machine-checkable productization status index | low | high | none | preserve hash/checker consistency before release-slice checks | no |
| `scripts/check_productization_state.py` | `keep_repo` | productization status checker | low | high | none | keep productization anchor behavior explicit | no |
| `scripts/check_cid_nl_discovery_release_slice.py` | `keep_repo` | CID-NL release-slice checker | low | medium | none | checker may call anchor `handoff`, but comment clarifies role | no |
| `docs/superpowers/plans/2026-06-18-backfill-evidence-lifecycle-blueprint.md` | `formalize_repo` | superseded/older Backfill lifecycle plan with reusable gates | medium | medium | `[[XIC Backfill Evidence Lifecycle Blueprint Notes]]` after pilot | confirm 2026-06-19 blueprint and formal owners cover active claims | no |
| `docs/superpowers/plans/2026-05-03-output-maintainability-refactor.md` | `move_to_obsidian_after_stub` | `docs/project-layout.md` for current output/artifact rules | medium | low | `[[XIC Output Maintainability Refactor History]]` | preserve any stable placement rule in `docs/project-layout.md` | no |
| `docs/superpowers/reports/2026-06-15-current-capability-inventory-and-promotion-roadmap.md` | `keep_repo` | control plane still cites this as primary evidence | medium | high | optional deep notes only | keep until control-plane no longer depends on this exact report | no |
| `docs/superpowers/notes/2026-05-24-resolver-default-switch-validation-note.md` | `repo_stub_plus_obsidian` | `docs/diagnostic-ledger.md` for current rerun policy | medium | medium | `[[XIC Resolver Default Switch Validation History]]` | keep same-path sanitized stub or update all exact-path referrers first | no |
| `docs/superpowers/notes/2026-05-26-p2b-area-mismatch-triage-note.md` | `repo_stub_plus_obsidian` | `docs/diagnostic-ledger.md` for current target conclusion | medium | medium | `[[XIC P2b Area Mismatch Triage History]]` | keep same-path sanitized stub or update all exact-path referrers first | no |
| `docs/superpowers/notes/2026-05-26-p8b-85raw-superwindow-acceptance-note.md` | `repo_stub_plus_obsidian` | `docs/diagnostic-ledger.md` for rerun policy and gate summary | medium | medium | `[[XIC P8b 85RAW Superwindow Acceptance History]]` | keep same-path sanitized stub or update all exact-path referrers first | no |
| `docs/superpowers/notes/2026-05-28-qualitative-selection-acceptance-gate-note.md` | `repo_stub_plus_obsidian` | `docs/diagnostic-ledger.md` and evidence rules | medium | medium | `[[XIC Qualitative Selection Acceptance Gate History]]` | keep same-path sanitized stub or update all exact-path referrers first | no |
| `docs/superpowers/notes/2026-06-05-gaussian15-ms1-morphology-production-ready-closeout.md` | `repo_stub_plus_obsidian` | `docs/lcms-msms-evidence-rules.md` for Gaussian15 owner claims | medium | medium | `[[XIC Gaussian15 MS1 Morphology Closeout History]]` | keep same-path sanitized stub or update all exact-path referrers first | no |
| `docs/superpowers/notes/2026-06-05-gaussian15-ms1-peak-group-nl-scope-production-ready-closeout.md` | `repo_stub_plus_obsidian` | `docs/lcms-msms-evidence-rules.md` for Gaussian15 NL scope | medium | medium | `[[XIC Gaussian15 Peak Group NL Scope History]]` | keep same-path sanitized stub or update all exact-path referrers first | no |
| `docs/superpowers/notes/2026-06-15-replay-executor-validation-note.md` | `repo_stub_plus_obsidian` | `docs/diagnostic-ledger.md` or replay formal owner | medium | medium | `[[XIC Replay Executor Validation History]]` | keep same-path sanitized stub or update all exact-path referrers first | no |
| `docs/superpowers/notes/2026-06-18-backfill-autowrite-ground-truth-critical-review.md` | `move_to_obsidian_after_stub` | control plane and Backfill evidence owner docs | medium | medium | `[[XIC Backfill Autowrite Ground Truth Critical Review]]` | retain no-auto-write / truth-boundary decision in formal owners, then keep same-path stub or update exact-path referrers | no |
| `docs/superpowers/notes/2026-06-18-backfill-autowrite-ground-truth-strategy-note.md` | `move_to_obsidian_after_stub` | control plane and Backfill evidence owner docs | medium | medium | `[[XIC Backfill Autowrite Ground Truth Strategy]]` | retain strategy decision in formal owners, then keep same-path stub or update exact-path referrers | no |
| `docs/superpowers/notes/2026-06-18-chatgpt_reset_backfill_productization_objective.md` | `move_to_obsidian_after_stub` | control plane / active roadmap for current objective | medium | low | `[[XIC Backfill Productization Reset History]]` | preserve any active objective in roadmap/control plane, then keep same-path stub or update exact-path referrers | no |
| `docs/superpowers/notes/backfill_broad_autowrite_feasibility_gate_v1.md` | `keep_repo` | current status-index artifact and authority-manifest decision packet for broad Backfill parked state | medium | high | optional deep notes only | do not move until a compact replacement artifact updates status index, authority manifest, hashes, and exact referrers | no |

## Current Decision

The current branch should not migrate files out of version control. It should
land the contract, inventory, branch handoff stub, and review evidence first.

Repo is the public documentation surface. It should keep formal source-of-truth
docs, public contracts, compact sanitized decision records, and self-sufficient
handoff stubs. Obsidian is the private notebook surface. It should keep long
development history, research reasoning, command diaries, review detail, and
local/private context.

This policy does not change productization maturity tier, active lane, writer
authority, workbook schema, output schema, selected peak/area behavior, or any
matrix-writing contract.

## Future File Intake Rule

For every new documentation artifact, classify it before writing:

| Intended content | Default destination | Repo requirement |
| --- | --- | --- |
| Public behavior, CLI/config/API/schema, workbook/report contract, validation policy, product authority, or agent workflow rule | Canonical repo owner | Formal wording, self-sufficient without Obsidian |
| Long exploration, branch diary, command transcript, private review detail, local data layout, or sample-level investigation | Obsidian or ignored artifact | Optional repo stub only if needed for next actions |
| Cross-turn branch state | Branch-scoped repo handoff stub plus optional Obsidian note | Stub must include current objective, decisions, validation, blocker, residual risk, and next 1-3 actions |
| Historical tracked note with exact repo referrers | Same-path sanitized stub or formal owner update | Referrer scan before any removal |

Before any cleanup patch, run a secret/local-path scan over added repo lines and
an exact referrer scan over candidate paths. Destructive action remains `no`
until the user explicitly approves the concrete file-management patch.

## Cleanup Review Batch 1: Link/Stub Rows

Date: 2026-06-25
Status: reviewed, no destructive action authorized

This batch reviewed five `needs_link_update_or_stub_before_repo_removal` rows
against repo referrers and current authority owners.

| Source path | Batch verdict | Why | Next safe action |
| --- | --- | --- | --- |
| `docs/deepresearch/Backfill Production Gate.md` | `repo_stub_plus_obsidian` | Control plane already extracts the stable claim that `height >= 2e6` is a rollout guardrail, not a product hard gate; exact repo referrers still exist. | Keep a same-path research stub or update exact referrers before full removal. |
| `docs/superpowers/notes/2026-05-24-resolver-default-switch-validation-note.md` | `repo_stub_plus_obsidian` | `docs/diagnostic-ledger.md` owns the durable P2-entry/rerun conclusion, but fixture/spec/plan referrers still cite the exact note path. | Replace with a sanitized same-path stub after confirming referrers do not need the full run diary. |
| `docs/superpowers/notes/2026-05-26-p2b-area-mismatch-triage-note.md` | `repo_stub_plus_obsidian` | `docs/diagnostic-ledger.md` owns the current target conclusion; fixture and older plan referrers still cite the exact note path. | Keep same-path stub unless all exact referrers are updated to the ledger. |
| `docs/superpowers/notes/2026-05-26-p8b-85raw-superwindow-acceptance-note.md` | `repo_stub_plus_obsidian` | `docs/diagnostic-ledger.md` owns the rerun conclusion and `docs/agent-parameter-settings.md` owns the validated 85RAW command profile; exact refs still cite this note as evidence. | Keep same-path stub preserving validation tier, command-profile pointer, and Obsidian link. |
| `docs/superpowers/notes/backfill_broad_autowrite_feasibility_gate_v1.md` | `keep_repo` | `productization_status_index_v1.tsv` uses this exact file as `current_artifact` with hash, and the authority manifest uses it as the parked-lane decision packet. | Do not move or stub until a compact replacement artifact updates status index, authority manifest, hashes, and exact referrers. |

## Obsidian Pilot Status

- CLI discovery: `Get-Command obsidian` found an Obsidian desktop CLI shim on
  `PATH`.
- CLI preflight: sandboxed CLI calls cannot reach Obsidian IPC, but approved
  external CLI execution can list vaults, read the user-approved private vault,
  and write/read a one-note pilot.
- MCP/tooling discovery: no callable Obsidian MCP tool was available in this
  Codex session; only local Obsidian skills were available as instructions.
- Pilot result: `[[XIC Docs Cleanup Hybrid Handoff]]` was created in
  the confirmed private vault, linked from `[[XIC Extractor Handoffs Index]]`,
  and read back through the Obsidian CLI with
  `migration_status: readback_verified`.
- Result: one-note vault write/readback is verified. Bulk migration remains
  blocked until a concrete migration batch is approved.

After the user approves a concrete migration batch, use this order:

1. verify the repo owner or stub for each source file;
2. verify Obsidian CLI/MCP target and readback on 1-3 pilot notes;
3. update each repo stub with optional note pointer;
4. run referrer scan;
5. ask for explicit destructive approval before any tracked-file removal.
