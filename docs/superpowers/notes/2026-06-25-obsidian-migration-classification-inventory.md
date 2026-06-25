# Obsidian migration classification inventory

Date: 2026-06-25
Branch: `codex/docs-cleanup`
Status: direction locked; cleanup patch staging inventory; not a deletion list

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
| `docs/product/README.md` | `keep_repo` | extensible product-topic routing index | low | high | none | keep as public representative-doc entry point; add topics as they become global | no |
| `docs/product/backfill.md` | `keep_repo` | Backfill product-topic source-of-truth summary | medium | high | none | keep global; detailed diaries can move to Obsidian after stable claims are covered | no |
| `docs/product/discovery.md` | `keep_repo` | Discovery product-topic source-of-truth summary | low | high | none | keep global; dated implementation plans can move after stable claims are covered | no |
| `docs/product/alignment.md` | `keep_repo` | Alignment product-topic source-of-truth summary | low | high | none | keep global; dated alignment plans can move after stable claims are covered | no |
| `docs/product/presets.md` | `keep_repo` | Preset product-topic source-of-truth summary | low | high | none | keep global; preset calibration diaries can move after stable claims are covered | no |
| `docs/agent/communication-review.md` | `keep_repo` | human review and closeout surface rules | low | high | none | keep as repo public rule | no |
| `docs/agent/codex-operating-system.md` | `keep_repo` | agent hooks/routing operating rules | low | high | none | keep as repo public rule | no |
| `docs/agent/product-validation-contract.md` | `keep_repo` | product validation language and public-surface discipline | low | high | none | keep as repo source-of-truth | no |
| `docs/lcms-msms-evidence-rules.md` | `keep_repo` | LC-MS/MS evidence rule source-of-truth | medium | high | none | keep formal evidence contract | no |
| `docs/diagnostic-ledger.md` | `keep_repo` | compact known diagnostic conclusions | medium | high | none | keep compact conclusions only | no |
| `docs/deepresearch/Backfill Production Gate.md` | `repo_stub_plus_obsidian` | control plane and evidence rules for current Backfill gate semantics | medium | medium | `[[Backfill Production Gate]]` | same-path public stub landed; keep stub while exact referrers exist | no |
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
| `docs/superpowers/notes/2026-05-24-resolver-default-switch-validation-note.md` | `repo_stub_plus_obsidian` | `docs/diagnostic-ledger.md` for current rerun policy | medium | medium | `[[2026-05-24 Resolver Default Switch Validation Note]]` | same-path public stub landed; keep stub while exact referrers exist | no |
| `docs/superpowers/notes/2026-05-26-p2b-area-mismatch-triage-note.md` | `repo_stub_plus_obsidian` | `docs/diagnostic-ledger.md` for current target conclusion | medium | medium | `[[2026-05-26 P2b Area Mismatch Triage Note]]` | same-path public stub landed; keep stub while exact referrers exist | no |
| `docs/superpowers/notes/2026-05-26-p8b-85raw-superwindow-acceptance-note.md` | `repo_stub_plus_obsidian` | `docs/diagnostic-ledger.md` for rerun policy and gate summary | medium | medium | `[[2026-05-26 P8b 85raw Superwindow Acceptance Note]]` | same-path public stub landed; keep stub while exact referrers exist | no |
| `docs/superpowers/notes/2026-05-28-qualitative-selection-acceptance-gate-note.md` | `repo_stub_plus_obsidian` | `docs/diagnostic-ledger.md` and evidence rules | medium | medium | `[[XIC Qualitative Selection Acceptance Gate History]]` | same-path public stub landed in cleanup patch 3; keep stub while exact referrers exist | no |
| `docs/superpowers/notes/2026-06-05-gaussian15-ms1-morphology-production-ready-closeout.md` | `repo_stub_plus_obsidian` | `docs/lcms-msms-evidence-rules.md` for Gaussian15 owner claims | medium | medium | `[[XIC Gaussian15 MS1 Morphology Closeout History]]` | same-path public stub landed in cleanup patch 3; keep stub while exact referrers exist | no |
| `docs/superpowers/notes/2026-06-05-gaussian15-ms1-peak-group-nl-scope-production-ready-closeout.md` | `repo_stub_plus_obsidian` | `docs/lcms-msms-evidence-rules.md` for Gaussian15 NL scope | medium | medium | `[[XIC Gaussian15 Peak Group NL Scope History]]` | same-path public stub landed in cleanup patch 3; keep stub while exact referrers exist | no |
| `docs/superpowers/notes/2026-06-15-replay-executor-validation-note.md` | `repo_stub_plus_obsidian` | `docs/diagnostic-ledger.md` or replay formal owner | medium | medium | `[[XIC Replay Executor Validation History]]` | same-path public stub landed in cleanup patch 3; keep stub while exact referrers exist | no |
| `docs/superpowers/notes/2026-06-18-backfill-autowrite-ground-truth-critical-review.md` | `repo_stub_plus_obsidian` | control plane and Backfill evidence owner docs | medium | medium | `[[XIC Backfill Autowrite Ground Truth Critical Review]]` | same-path public stub landed in cleanup patch 4; keep stub while exact referrers exist | no |
| `docs/superpowers/notes/2026-06-18-backfill-autowrite-ground-truth-strategy-note.md` | `repo_stub_plus_obsidian` | control plane and Backfill evidence owner docs | medium | medium | `[[XIC Backfill Autowrite Ground Truth Strategy]]` | same-path public stub landed in cleanup patch 4; keep stub while exact referrers exist | no |
| `docs/superpowers/notes/2026-06-18-chatgpt_reset_backfill_productization_objective.md` | `repo_stub_plus_obsidian` | control plane / active roadmap for current objective | medium | low | `[[XIC Backfill Productization Reset History]]` | same-path public stub landed in cleanup patch 4; keep stub while exact referrers exist | no |
| `docs/superpowers/notes/backfill_broad_autowrite_feasibility_gate_v1.md` | `keep_repo` | current status-index artifact and authority-manifest decision packet for broad Backfill parked state | medium | high | optional deep notes only | do not move until a compact replacement artifact updates status index, authority manifest, hashes, and exact referrers | no |

## Current Decision

The direction is now fixed: repo is the public source-of-truth surface, while
Obsidian is the private lab-notebook surface. The current branch may prepare
sanitized repo stubs, formal owner updates, Obsidian readback notes, and review
evidence, but it must not remove tracked files from version control.

Repo is the public documentation surface. It should keep formal source-of-truth
docs, public contracts, compact sanitized decision records, and self-sufficient
handoff stubs. Obsidian is the private notebook surface. It should keep long
development history, research reasoning, command diaries, review detail, and
local/private context.

If important content exists only in a historical note, first rewrite the stable
claim into a canonical repo owner or same-path public stub. Only the long
chronology, discarded hypotheses, command transcript, and private/local detail
should move to Obsidian. A repo reader must never need private vault access to
understand the product decision or next safe action.

Related global product topics should be grouped into representative repo docs
instead of left as scattered historical notes. The first-pass grouping is
`docs/product/`: Backfill, Discovery, Alignment, and Presets. This is an
extensible layer, not a claim that these four topics are the full product
taxonomy.

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
| Important historical claim without a formal owner | Existing canonical owner, or a new compact formal owner only if no owner exists | Formalize first, then move long original context to Obsidian |

Before any cleanup patch, run a secret/local-path scan over added repo lines and
an exact referrer scan over candidate paths. Destructive action remains `no`
until the user explicitly approves the concrete file-management patch.

## Direction Lock

Date: 2026-06-25
Status: policy settled
Optional Obsidian index: `[[XIC Docs Cleanup Direction Lock]]`
Obsidian status: `readback_verified`

The stable policy is:

- Keep repo docs as formal public source-of-truth, compact decision records,
  status indexes, validation ledgers, and self-sufficient branch handoff stubs.
- Keep Obsidian as private long-form research and development history.
- For each cleanup candidate, read the note, identify stable claims, verify the
  canonical owner, then create a same-path stub or update referrers before any
  removal proposal.
- Treat same-path stubs as temporary unless a hash, checker, fixture, artifact
  contract, or compatibility reference deliberately binds the exact path. Each
  cleanup batch should either update exact referrers to the canonical owner or
  record why exact-path retention remains required.
- Do not bulk-migrate or delete files just because a note has an Obsidian copy.
- Do not let private Obsidian notes become required reading for product
  behavior, validation policy, or future-agent next actions.

## Cleanup Review Batch 1: Link/Stub Rows

Date: 2026-06-25
Status: reviewed, no destructive action authorized

This batch reviewed five `needs_link_update_or_stub_before_repo_removal` rows
against repo referrers and current authority owners.

| Source path | Batch verdict | Why | Next safe action |
| --- | --- | --- | --- |
| `docs/deepresearch/Backfill Production Gate.md` | `repo_stub_plus_obsidian` | Control plane already extracts the stable claim that `height >= 2e6` is a rollout guardrail, not a product hard gate; exact repo referrers still exist. | Same-path public stub landed in cleanup patch 1; keep it while exact referrers exist. |
| `docs/superpowers/notes/2026-05-24-resolver-default-switch-validation-note.md` | `repo_stub_plus_obsidian` | `docs/diagnostic-ledger.md` owns the durable P2-entry/rerun conclusion, but fixture/spec/plan referrers still cite the exact note path. | Same-path public stub landed in cleanup patch 1; keep it while exact referrers exist. |
| `docs/superpowers/notes/2026-05-26-p2b-area-mismatch-triage-note.md` | `repo_stub_plus_obsidian` | `docs/diagnostic-ledger.md` owns the current target conclusion; fixture and older plan referrers still cite the exact note path. | Same-path public stub landed in cleanup patch 1; keep it while exact referrers exist. |
| `docs/superpowers/notes/2026-05-26-p8b-85raw-superwindow-acceptance-note.md` | `repo_stub_plus_obsidian` | `docs/diagnostic-ledger.md` owns the rerun conclusion and `docs/agent-parameter-settings.md` owns the validated 85RAW command profile; exact refs still cite this note as evidence. | Same-path public stub landed in cleanup patch 1; keep it while exact referrers exist. |
| `docs/superpowers/notes/backfill_broad_autowrite_feasibility_gate_v1.md` | `keep_repo` | `productization_status_index_v1.tsv` uses this exact file as `current_artifact` with hash, and the authority manifest uses it as the parked-lane decision packet. | Do not move or stub until a compact replacement artifact updates status index, authority manifest, hashes, and exact referrers. |

## Cleanup Patch 1: Same-Path Public Stubs

Date: 2026-06-25
Status: patch prepared, no tracked path removal

This patch replaced four long historical repo notes with same-path public stubs.
The stubs keep the public decision, formal owner links, optional private note
title, and next safe action. The full research / validation diary remains in
the user-approved private vault and was read back before the stubs were written.

| Source path | Stub status | Private note | Repo self-contained? |
| --- | --- | --- | --- |
| `docs/deepresearch/Backfill Production Gate.md` | landed | `[[Backfill Production Gate]]` | yes |
| `docs/superpowers/notes/2026-05-24-resolver-default-switch-validation-note.md` | landed | `[[2026-05-24 Resolver Default Switch Validation Note]]` | yes |
| `docs/superpowers/notes/2026-05-26-p2b-area-mismatch-triage-note.md` | landed | `[[2026-05-26 P2b Area Mismatch Triage Note]]` | yes |
| `docs/superpowers/notes/2026-05-26-p8b-85raw-superwindow-acceptance-note.md` | landed | `[[2026-05-26 P8b 85raw Superwindow Acceptance Note]]` | yes |

No `git rm` is part of this patch. These paths should remain tracked while repo
referrers still cite the exact path.

## Cleanup Patch 2: Exact Referrer Review

Date: 2026-06-25
Status: reviewed, no tracked path removal

This pass reviewed exact repo referrers for the four same-path stubs from
cleanup patch 1. It did not update historical plans/specs just to erase old
citations. Instead, it records why exact-path retention remains necessary and
where later cleanup can reduce it.

| Referrer class | Paths/examples | Decision | Exit rule |
| --- | --- | --- | --- |
| Canonical evidence owners | `docs/diagnostic-ledger.md`, `docs/agent-parameter-settings.md`, `docs/superpowers/plans/2026-06-15-productization-control-plane.md` | Keep exact stub links for now as evidence provenance and validated command-profile provenance. Sanitize narrative sample-level details when touched. | Update to canonical owner sections only after those owners no longer need note-level provenance. |
| Directory / cleanup coordination | `docs/deepresearch/README.md`, this inventory, current branch handoff, direction-lock archive | Keep while this cleanup branch is active. | Prune coordination refs after the patch lands and no active branch action needs them. |
| Machine fixtures / retained validation artifacts | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/diagnostic_tool_usage_current_8raw.tsv` | Keep exact path because fixtures are retained artifacts and should not be rewritten as prose cleanup. | Change only through a fixture migration with hash/contract update. |
| Historical plans/specs/notes | 2026-05 resolver/P2B/product-priority plans, specs, and closeout notes | Keep exact path as historical compatibility/provenance references. | Do not rewrite old planning history unless a future cleanup explicitly retires or archives that document class. |

This pass also sanitized the directly related `d3-N6-medA` narrative sample
identifier in `docs/diagnostic-ledger.md`. Broader sample identifiers in
retained fixtures and unrelated validation artifacts remain out of scope for
this file-management patch and need a separate privacy/fixture-retention audit
before any bulk rewrite.

## Cleanup Patch 3: Validation Closeout Same-Path Public Stubs

Date: 2026-06-25
Status: patch prepared, no tracked path removal

This patch replaced four long validation/closeout repo notes with same-path
public stubs. The stubs keep the public decision, formal owner links, optional
private note title, and next safe action. The full validation diaries remain in
the user-approved private vault and were read back before the stubs were
written.

| Source path | Stub status | Private note | Repo self-contained? |
| --- | --- | --- | --- |
| `docs/superpowers/notes/2026-05-28-qualitative-selection-acceptance-gate-note.md` | landed | `[[XIC Qualitative Selection Acceptance Gate History]]` | yes |
| `docs/superpowers/notes/2026-06-05-gaussian15-ms1-morphology-production-ready-closeout.md` | landed | `[[XIC Gaussian15 MS1 Morphology Closeout History]]` | yes |
| `docs/superpowers/notes/2026-06-05-gaussian15-ms1-peak-group-nl-scope-production-ready-closeout.md` | landed | `[[XIC Gaussian15 Peak Group NL Scope History]]` | yes |
| `docs/superpowers/notes/2026-06-15-replay-executor-validation-note.md` | landed | `[[XIC Replay Executor Validation History]]` | yes |

No `git rm` is part of this patch. These paths should remain tracked while repo
referrers still cite the exact path.

## Cleanup Patch 4: Backfill Strategy Same-Path Public Stubs

Date: 2026-06-25
Status: patch prepared, no tracked path removal

This patch replaced three Backfill strategy/reset repo notes with same-path
public stubs. Their stable claims are already owned by the productization
control plane, status index, authority manifest, mechanical adjudication
surfaces, and the parked broad-autowrite decision packet. The stubs keep the
public decision, formal owner links, optional private note title, and next safe
action.

| Source path | Stub status | Private note | Repo self-contained? |
| --- | --- | --- | --- |
| `docs/superpowers/notes/2026-06-18-backfill-autowrite-ground-truth-critical-review.md` | landed | `[[XIC Backfill Autowrite Ground Truth Critical Review]]` | yes |
| `docs/superpowers/notes/2026-06-18-backfill-autowrite-ground-truth-strategy-note.md` | landed | `[[XIC Backfill Autowrite Ground Truth Strategy]]` | yes |
| `docs/superpowers/notes/2026-06-18-chatgpt_reset_backfill_productization_objective.md` | landed | `[[XIC Backfill Productization Reset History]]` | yes |

No productization control-plane update is needed for this patch because it does
not change maturity tier, active lane, writer authority, output schema,
review/replay behavior, selected area/counting, or matrix authority.

No `git rm` is part of this patch. These paths should remain tracked while repo
referrers still cite the exact path.

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
