# Obsidian-backed docs and handoff contract

This contract defines how XIC documentation can move toward private Obsidian
notes without breaking repo handoff, PR closeout, or future-agent recovery after
context compaction.

## Verdict

Use a hybrid model:

- repo keeps formal source-of-truth docs and short branch-scoped handoff stubs;
- Obsidian keeps long development history, scratch reasoning, research notes,
  command transcripts, and private/local context;
- PR body remains the durable closeout surface for completed branch work.

Obsidian can deepen context, but the repo must still contain enough sanitized
information for an agent to resume the next 1-3 actions after context
compaction.

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

If a tracked file is still referenced by exact path from another repo file,
`move_to_obsidian_after_stub` is not enough. Before removal, either keep a
sanitized stub at the same path or update every repo referrer to a formal owner
that preserves the same decision. This referrer scan is mandatory even when the
long original content has been copied to Obsidian.

## New docs after migration

When future work creates new documentation:

1. If it changes public behavior, schema, product state, validation policy,
   source-of-truth claims, or agent workflow rules, write it to the canonical
   repo owner.
2. If it is long exploration, scratch reasoning, private diary, or command
   transcript, write it to Obsidian or an ignored artifact.
3. If it is needed for cross-turn work, also create or refresh the branch
   handoff stub.
4. Never make a repo document depend on a private Obsidian note for its core
   meaning. Repo references to Obsidian must be optional pointers.
5. Before moving or deleting any tracked doc, scan referrers and ensure each
   remaining repo link lands on a formal owner or sanitized stub.

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
