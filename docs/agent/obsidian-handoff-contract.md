# Obsidian-backed docs and public/private boundary contract

This contract defines how XIC documentation separates public repo artifacts from
private Obsidian notes without breaking repo handoff, PR closeout, or
future-agent recovery after context compaction.

## Verdict

Use a hybrid model:

- repo keeps formal source-of-truth docs and short branch-scoped handoff stubs;
- Obsidian keeps long development history, scratch reasoning, research notes,
  command transcripts, and private/local context;
- PR body remains the durable closeout surface for completed branch work.

Obsidian can deepen context, but the repo must still contain enough sanitized
information for an agent to resume the next 1-3 actions after context
compaction.

## Final direction

As of 2026-06-25, this is the standing documentation policy, not an experiment:

1. The repo is the public product and agent operating record. It keeps formal
   rules, product contracts, machine-checkable state, compact decision records,
   and self-sufficient handoff stubs.
2. Obsidian is the private lab notebook. It keeps long reasoning, command
   diaries, exploratory review, abandoned sequencing, local context, and other
   material that would be inappropriate or noisy in a public repo.
3. Obsidian may deepen context, but it must never be the only source for repo
   behavior, product authority, validation policy, or the next safe action.
4. Historical tracked notes move by a stub-first workflow: extract the stable
   public claim into a canonical repo owner, keep or create a same-path
   sanitized stub while exact referrers exist, then move the long original
   context to Obsidian.
5. Destructive cleanup is a separate final step. `git rm`, archive moves, and
   tracked-file deletion require explicit user approval after the concrete
   paths, replacements, and referrer scan are known.

## Source-of-truth promotion rule

When a historical note contains important material that is not yet organized in
a formal repo owner, do not move it directly to Obsidian and call the work done.
First promote the stable public claim:

1. Identify whether an existing owner already applies: productization control
   plane, diagnostic ledger, evidence rules, product validation contract,
   architecture contract, project layout, or a named spec.
2. Rewrite only the durable claim into that owner: current decision, authority,
   validation status, explicit non-change, and next safe action.
3. Keep the historical file as `repo_stub_plus_obsidian` if exact-path repo
   referrers still exist; otherwise update every referrer to the formal owner.
4. Put the long chronology, discarded hypotheses, command transcript, and
   private/local detail in Obsidian.
5. Verify that a future agent can continue from repo files alone before any
   removal is proposed.

## Public/private publication boundary

Treat the public repo like the publication surface: it may disclose the
approved design, current product contract, validation verdict, and operator
instructions, but it must not expose the full lab notebook behind those
decisions.

Repo documents may contain:

- formal source-of-truth rules;
- public API, CLI, config, schema, workbook, report, and validation contracts;
- compact sanitized decision records;
- branch handoff stubs that are self-sufficient without private vault access;
- evidence summaries that remove private local paths, raw transcripts, and
  sample-level investigation detail.

Repo documents must not contain:

- raw development diary or chat-like chronology;
- private research notes, speculative strategy, or abandoned branch sequencing
  unless rewritten as a compact public decision record;
- command transcripts, local absolute paths, or machine-specific vault paths;
- private RAW layout, sample-level investigation detail, or non-public data
  placement;
- secrets, credentials, tokens, API keys, or auth material.

Obsidian is the private notebook layer. It may hold long-form reasoning,
exploratory analysis, detailed review notes, and local context, but it must not
be the only place that defines repo behavior, product authority, validation
policy, or future-agent next actions. If a private note contains a decision that
should shape the software, distill the stable public claim into the appropriate
repo owner first.

## Layers

| Layer | Owner | Purpose | Must not contain |
| --- | --- | --- | --- |
| Formal repo docs | `docs/agent/`, `docs/superpowers/specs/`, named plans, ledgers | Public contracts, product state, validation policy, source-of-truth claims | private diary, raw transcripts, obsolete branch sequencing |
| Branch handoff stub | `docs/superpowers/handoffs/current/<branch-slug>-<topic>.md` | Current objective, decisions, validation, blocker, next actions, optional Obsidian pointer | long logs, full chat history, private sample investigation |
| Productization status anchor | `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md` | Productization checker anchor phrases and shared status reminders | branch-specific current objectives |
| PR body | GitHub PR description | Durable closeout: problem, solution, verification, residual risk | raw handoff paste or private Obsidian-only context |
| Obsidian note | User-approved private vault | Long-form research, development diary, exploratory analysis, detailed private notes | secrets, credentials, repo-only source-of-truth claims |
| Global `$handoff` output | OS temp conversation handoff | Temporary cross-session transfer | repo authority or PR closeout |

## Branch stub requirements

Every branch that depends on Obsidian notes must keep a repo stub that is useful
without Obsidian access.

Required fields:

- `Branch:`
- `Status:`
- `Validation status:`
- current objective;
- public/sanitized current state;
- active decisions and constraints;
- verification actually run or explicitly skipped;
- blockers and residual risk;
- next 1-3 actions;
- optional Obsidian pointer.

Optional Obsidian pointer format:

```markdown
Obsidian:
- note: [[XIC Docs Cleanup - Hybrid Handoff]]
- status: not_created | pilot_created | readback_verified
- contains: long development history, private review notes, command transcript
```

Do not put absolute vault paths in repo stubs. Use note title, stable alias, or a
non-secret note id. If the pointer is missing or Obsidian is unavailable, the
repo stub must still support the next safe action.

Minimum same-path stub format for a moved historical note:

```markdown
# <public title>

Status: `repo_stub_plus_obsidian`
Validation status: `<diagnostic_only | shadow_ready | production_candidate | production_ready | inconclusive>`

This file is a sanitized repo stub. After approved migration, the long private
development history lives in Obsidian. This stub preserves the public decision
needed by repo referrers.

## Public Summary

- <stable public claim>
- <current owner or canonical replacement>
- <what is not changed by this stub>

## Repo Sources Of Truth

- `<formal owner path>`
- `<validation ledger or status artifact path>`

## Optional Private Context

- Obsidian note: `[[<note title or alias>]]`
- Status: `readback_verified`

## Next Safe Action

1. <next action that does not require private vault access>
```

The stub should be short. Do not copy the private note back into the repo under a
different name.

## Classification dispositions

Use these labels when reviewing docs before moving anything:

| Disposition | Meaning | Required before action |
| --- | --- | --- |
| `keep_repo` | Durable source-of-truth or public contract stays in repo | owner file is clear and current |
| `formalize_repo` | Content should stay, but must be rewritten into formal docs first | stable claims moved to a canonical owner |
| `repo_stub_plus_obsidian` | Short sanitized repo stub remains; long details may move to Obsidian | stub is self-sufficient and points to optional note |
| `move_to_obsidian_after_stub` | Repo original can leave version control only after a stub/formal owner exists | explicit user approval before `git rm` |
| `archive_or_delete_later` | Historical artifact is likely removable after evidence is preserved elsewhere | destructive approval and final referrer scan |
| `local_only_no_repo` | Private/local material should never enter version control | keep ignored; no repo referrer may depend on it |

Classification inventory rows should include:

- path;
- disposition;
- current repo owner or replacement owner;
- privacy risk;
- whether future agents need it for handoff;
- Obsidian target note title if known;
- required pre-move action;
- whether destructive action is allowed now.

Default for destructive action is `no`.

Use privacy risk to decide where the long text belongs:

- `low`: already public-contract style, no local transcript or private data;
- `medium`: contains research reasoning, branch chronology, paths, command
  history, or sample-level detail that must be summarized before publication;
- `high`: contains private data placement, raw local context, sensitive
  collaboration detail, credentials, or anything that should never enter public
  repo text.

If a tracked file is still referenced by exact path from another repo file,
`move_to_obsidian_after_stub` is not enough. Before removal, either keep a
sanitized stub at the same path or update every repo referrer to a formal owner
that preserves the same decision. This referrer scan is mandatory even when the
long original content has been copied to Obsidian.

Same-path stubs are temporary unless the exact path is deliberately bound by a
hash, checker, fixture, artifact contract, or compatibility reference. Each
cleanup batch should either update exact referrers to the canonical owner or
record why exact-path retention remains required.

## New docs after migration

When future work creates new documentation:

1. Classify it at creation time as `formal repo doc`, `branch stub`, `private
   Obsidian note`, `ignored artifact`, or `throwaway scratch`.
2. If it changes public behavior, schema, product state, validation policy,
   source-of-truth claims, or agent workflow rules, write the stable claim to
   the canonical repo owner.
3. If it is long exploration, scratch reasoning, private diary, or command
   transcript, write it to Obsidian or an ignored artifact.
4. If private context is needed for cross-turn work, also create or refresh the
   branch handoff stub with only the sanitized next 1-3 actions.
5. Never make a repo document depend on a private Obsidian note for its core
   meaning. Repo references to Obsidian must be optional pointers.
6. Before moving or deleting any tracked doc, scan referrers and ensure each
   remaining repo link lands on a formal owner or sanitized stub.

Before committing new repo docs, scan added lines for secrets, private local
paths, absolute vault paths, raw sample-level investigation detail, and
unreviewed product-authority claims. Before committing new Obsidian pointers,
read back the target note through the CLI/MCP interface when available.

## Cleanup patch gates

A documentation cleanup patch should proceed in this order:

1. Classify each source path in the inventory.
2. Extract stable public claims into formal repo owners.
3. Create same-path sanitized stubs for tracked files that still have exact repo
   referrers.
4. Copy long private history to Obsidian only after a pilot write/readback is
   verified for the target vault.
5. Re-run exact referrer scans against the candidate paths and note titles.
6. Run docs/hook smoke checks plus secret, private local path, and absolute
   vault path scans.
7. Ask for explicit destructive approval before any `git rm`, archive move, or
   tracked-file deletion.

## Obsidian CLI/MCP pilot gate

Do not run a bulk migration until a small pilot is verified.

Pilot requirements:

- user-approved vault target;
- `obsidian help` or MCP capability check succeeds;
- create at most 1-3 pilot notes;
- read back the created note through the same interface;
- update the repo stub with note title and `readback_verified` status;
- verify the repo still has a self-sufficient stub;
- no secrets, API keys, absolute private data paths, or raw sample-level
  investigations are copied into public repo files.

If Obsidian is not running, the CLI may fail with "unable to find Obsidian".
That is a pilot blocker, not a reason to weaken the repo stub rule.

## Stop rules

Stop and ask before:

- `git rm`, archive moves, or tracked file deletion;
- writing to an unconfirmed vault;
- creating public repo links that require private Obsidian access;
- moving a doc whose stable claims do not yet have a formal repo owner;
- touching productization tier, active lane, writer authority, output schema,
  selected peak/area/counting, or matrix authority.
