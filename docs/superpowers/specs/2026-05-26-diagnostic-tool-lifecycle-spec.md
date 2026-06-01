# Diagnostic Tool Lifecycle Spec

**Date:** 2026-05-26
**Status:** Governance rules with 2026-06-01 shared-infrastructure closeout; no
diagnostic behavior, schema, or method change
**Worktree:** `codex/peak-pipeline-modernization`

---

## Purpose

Govern the **lifecycle** of diagnostic tools (create / promote / retire), not
how to split them. This spec answers questions existing cleanup specs leave
open:

- When does a diagnostic belong in `xic_extractor/diagnostics/` instead of
  `tools/diagnostics/`?
- When should a diagnostic be deleted rather than kept "just in case"?
- How do we stop two investigations writing two near-identical tools?

This spec does NOT:

- repeat AGENTS.md dependency-direction rules,
- repeat module-decomposition guidance from existing cleanup specs,
- modify schemas, gates, methods, RAW/XIC retrieval, or any scientific
  behavior,
- execute any cleanup punch list. Deletions and promotions belong to follow-up
  implementation PRs that cite this spec.

## 2026-06-01 Shared-Infrastructure Closeout

The cleanup-retirement branch completed the dependency-direction cleanup that
this spec anticipated for schema-neutral shared helpers:

- `xic_extractor/diagnostics/diagnostic_io.py` is the package-owned canonical
  path for delimited/TSV IO, scalar parsing, header validation, label splitting,
  and value formatting.
- `tools/diagnostics/diagnostic_io.py` remains a compatibility shim for
  existing diagnostic CLIs.
- This move does not promote a diagnostic gate by itself and does not change any
  diagnostic schema or scientific method.
- Future diagnostic tools should reuse the package-owned helper before adding
  local `_read_required_tsv`, `_optional_float`, `_text`, `_required_indexes`,
  or `_write_tsv` copies.

## Problem Statement

Audit on 2026-05-26 (this worktree) found:

- `tools/diagnostics/` contains roughly 108 `.py` files across 30+ topic
  groups.
- `xic_extractor/` and `scripts/` import zero modules from `tools.diagnostics`.
  Every diagnostic is human-triggered only.
- `xic_extractor/diagnostics/` contains only `timing.py`. The in-package
  diagnostic path is effectively dead.
- 11 files have no caller, no docs reference, and no commit in 60+ days, but
  still ship in the repo.
- Multiple topic groups historically duplicated logic. The evidence consistency
  twins (`evidence_spine_consistency_*` and
  `cross_report_evidence_consistency_*`) and the listed writer/loader
  infrastructure were consolidated through `diagnostic_io.py` on 2026-05-26;
  the backfill review trio (`seed_aware`, `family_ms1`, `low_ms1_coverage`)
  still requires method-level review before consolidation.

Root cause: the in-package diagnostic path is dead, so new findings always
land in `tools/diagnostics/`. The 5-file modular template from the post-PR60
cleanup spec is correct on its own terms, but no policy retires the old tools
or promotes the ones production now depends on, so the directory grows
monotonically.

## Existing Specs This Extends

- `AGENTS.md` Architecture And Clean Code Rules (lines 136-178), especially
  the rule that `tools/diagnostics/` is maintained product code.
- `docs/superpowers/specs/2026-05-16-module-responsibility-inventory.md`
- `docs/superpowers/specs/2026-05-16-alignment-module-responsibility-contract.md`
- `docs/superpowers/specs/2026-05-24-post-pr60-codebase-cleanup-spec.md`

This spec adds **lifecycle states** and **placement rules** on top of the
architectural rules those specs already establish. It does not override them.

## Lifecycle States

Every diagnostic tool is in exactly one of four states:

| State | Definition | Allowed location |
|---|---|---|
| `CANDIDATE` | Exploratory; an investigation just produced it. May not survive past the originating spec/note. | `tools/diagnostics/` only |
| `ACTIVE` | Referenced by a spec/plan in the last 14 days, or has commit activity in the last 14 days, or is part of an instrument-QC / phase-gate suite still maturing. | `tools/diagnostics/` |
| `GATED` | Production pipeline code in `xic_extractor/` depends on its output, or a contract test treats its output as a frozen schema. | `xic_extractor/diagnostics/` only |
| `RETIRED` | No caller, no docs reference, no commit in 60+ days; only a sentinel test keeps it alive. | Scheduled for deletion |

State is determined by audit evidence, not by author intent. A tool is
`GATED` only when an `xic_extractor/` importer actually exists; promising
future use does not count.

## Placement Rules

- `xic_extractor/diagnostics/` is reserved for `GATED` diagnostics. New
  sub-packages (for example `gates/`, `contracts/`) are encouraged when more
  than one `GATED` tool shares a theme.
- `tools/diagnostics/` is for `CANDIDATE` and `ACTIVE` tools. Human-triggered
  CLIs, report renderers, and one-off audits live here permanently if they
  remain `ACTIVE`.
- `scripts/` is for production entry points (`run_*`, `validate_*`,
  `benchmark_*`). Diagnostics do not live under `scripts/`. A wrapper script
  that simply imports a diagnostic and forwards CLI arguments is permitted
  only if the diagnostic itself is `GATED`.

A tool must not be split across both `tools/diagnostics/` and
`xic_extractor/diagnostics/`. Pick one based on whether production code
imports it.

Schema-neutral shared infrastructure is not itself a diagnostic tool. Helpers
such as delimited/TSV IO, scalar parsing, and header validation may live in
`xic_extractor/diagnostics/` when package code depends on them, while
`tools/diagnostics/` keeps a compatibility shim for existing diagnostic CLIs.

## Promotion Trigger: CANDIDATE/ACTIVE → GATED

A tool **must** be promoted to `xic_extractor/diagnostics/` when **any** of:

- A spec or plan in `docs/superpowers/specs/` or `docs/superpowers/plans/`
  explicitly designates the tool as a phase gate, acceptance gate, or
  pipeline-required diagnostic. This designation trigger exists because the
  2026-05-26 audit found zero `xic_extractor/` importers for any
  `tools/diagnostics/` module; without an explicit-designation path, no
  current tool could ever reach `GATED` from the import-count triggers
  alone, and the in-package diagnostic path would remain dead by
  construction.
- A second `xic_extractor/` module starts importing it. The first
  `xic_extractor/` import is allowed under `tools/`; the second triggers
  promotion in the same PR.
- A single `xic_extractor/` importer has remained stable for 90+ days. This
  catches the case where a tool ends up with exactly one long-lived
  production dependency that never grows a second importer but is clearly
  no longer exploratory.
- It becomes a referenced phase gate in pipeline code (for example,
  `xic_extractor/alignment/pipeline.py` calls it during a normal run).
- A contract or acceptance test in `tests/` treats its output as a frozen
  schema (column names, value ranges, or row counts asserted strictly).

Promotion is a move-only PR. It must:

- preserve the public CLI entry point if one existed, by leaving a thin shim
  in `tools/diagnostics/` that imports from the new in-package location,
- include a no-RAW import smoke test for the new in-package module,
- not change any TSV/JSON/Markdown schema during the move.

## Demotion Trigger: ACTIVE → RETIRED

A tool is marked `RETIRED` when **all** of the following hold simultaneously:

- No commit in the last 60 days in the branch lineage feeding `master`.
- No reference in `docs/superpowers/specs/`, `docs/superpowers/plans/`,
  `docs/superpowers/notes/` in the last 30 days. **"Reference" means any
  textual mention of the tool's module name, file path, CLI command, or
  exported function/class - not just commit-log citations.** The 30-day
  window applies to the docs file's last modification date: if a
  spec/plan/note that textually mentions the tool was edited in the last
  30 days, the tool is not `RETIRED`, regardless of whether the mention
  is in a checklist, code example, sample command, or prose paragraph.
  This rule is intentionally conservative; ambiguous cases default to
  `ACTIVE`.
- No caller in `scripts/`, `xic_extractor/`, or `.github/workflows/`. A
  module being imported by another `tools/diagnostics/` file inside the
  same topic group does not exempt the group from `RETIRED` if the group
  as a whole satisfies the other conditions.
- Only one sentinel test exists (the test created when the tool first
  landed). A test is "sentinel" only if it does not assert frozen schema,
  value ranges, or row counts and is named after the tool itself.

**Seasonal-cadence exception.** If the originating PR explicitly declared a
usage cadence longer than 60 days - for example quarterly instrument-QC
audits, annual calibration reviews, or sequence-manifest checks that fire
once per acquisition campaign - the time-window conditions above are scaled
to "no commit and no docs reference for two full declared cadences." For an
annually-cadenced tool that is roughly two years; for a quarterly tool, six
months. The cadence must appear in the originating PR description (see PR
checklist below) before the first merge, not invented retrospectively to
rescue a tool from `RETIRED`. Without an explicit declaration, the default
60-day rule applies.

`RETIRED` tools, together with their sentinel test, are deleted by a follow-up
cleanup PR. The deletion PR cites this spec and the audit run that classified
them, so the trail of "why was this removed" is auditable.

## Duplication Prevention

Before opening a PR that creates a new tool in `tools/diagnostics/`, the
author must:

1. **Consult `tools/diagnostics/INDEX.md` first.** Identify the topic group
   that matches the new tool's domain and read every entry-point block in
   that group. The INDEX is the canonical catalog of existing entry-points;
   "I did not see this tool exists" is no longer an acceptable PR
   justification. If the INDEX looks stale (a recent PR forgot to update
   it), the fallback is to `grep` `tools/diagnostics/` for shared domain
   keywords (`evidence`, `spine`, `consistency`, `backfill`, `review`,
   `audit`, `calibration`, `coverage`) and to add an entry for the missed
   tool to the INDEX in the same PR.
2. List in the PR description every existing tool that reads the same input
   TSV/workbook the new tool will read.
3. If two or more existing tools already read the same inputs and emit
   overlapping outputs, the new work must either:
   - extend one of the existing tools (preferred), or
   - extract a shared helper module that all overlapping tools migrate to in
     the same PR (no parallel re-implementation).

Shared infrastructure that **must** be reused, not re-implemented:

- `xic_extractor/diagnostics/diagnostic_io.py` for delimited/TSV reads and
  writes, scalar parsing, required-column/header validation, label splitting,
  and formatted-value helpers. `tools/diagnostics/diagnostic_io.py` is the
  compatibility shim for existing diagnostic CLIs.
- A future `tools/diagnostics/_common/` module only if genuinely shared
  `openpyxl` styling, color palettes, or Excel-safe value conversion appear.
  The 8 known re-implementations identified by the 2026-05-26 audit migrated
  to `diagnostic_io.py`, so do not add `_common/` merely for ceremony.
  module on their next touch.

A new tool that re-implements `openpyxl` cell writing, TSV reading, or value
formatting is rejected at review unless the author justifies why the shared
module cannot be extended instead.

## New-Tool PR Checklist

Authors of new diagnostic tools include this section in their PR description:

- [ ] Initial lifecycle state declared (`CANDIDATE` or `ACTIVE`).
- [ ] Placement justified (`tools/diagnostics/` because no production importer
      exists; or `xic_extractor/diagnostics/` because production already
      depends on it).
- [ ] **Usage cadence declared.** Default is "human-triggered, no fixed
      schedule" - the 60-day demotion rule applies. Declare an explicit
      longer cadence (quarterly, annual, per-campaign, etc.) only if the
      tool is genuinely expected to be dormant between scheduled runs; this
      activates the seasonal-cadence exception in the Demotion section.
      Cadence declared retrospectively does not count.
- [ ] Inputs listed (every TSV / workbook / RAW source the tool reads).
- [ ] Outputs listed (every TSV / JSON / Markdown / XLSX / SVG the tool
      writes, with field names).
- [ ] **INDEX.md consultation logged.** Listed which topic group(s) in
      `tools/diagnostics/INDEX.md` were scanned and why every existing
      entry-point in those groups is inadequate for the new need. "No
      overlap" without a group citation is rejected.
- [ ] **INDEX.md updated.** If this PR adds a new entry-point, appended a
      block to the matching group in `tools/diagnostics/INDEX.md` with
      Purpose, Topic group, Originating spec/plan. If this PR retires or
      renames an entry-point, updated or removed the corresponding block
      and adjusted the Table of Contents tool counts.
- [ ] Shared helpers reused (`xic_extractor/diagnostics/diagnostic_io.py` or
      successors; `tools/diagnostics/diagnostic_io.py` remains the shim). Any
      new helpers extracted live in a `_common/` location, not inside the tool's
      own 5-file group.
- [ ] If `CANDIDATE`, the originating spec / plan / note is linked. If no
      originating document exists, the tool is treated as a one-off and is
      deleted within 30 days unless promoted to `ACTIVE` by an explicit
      follow-up.

## Audit Cadence

A lifecycle audit runs once per quarter or before any cleanup-claimed PR,
whichever is sooner. The audit produces:

- a table of every `tools/diagnostics/` topic group with current state,
- a list of `RETIRED` candidates with deletion-PR recommendations,
- a list of promotion candidates,
- a list of duplication risks,
- a diff against the current `tools/diagnostics/INDEX.md`: any entry-point
  file in the directory that is missing from INDEX, or any INDEX entry
  that no longer matches a file, is logged as a maintenance gap and fixed
  in the same audit follow-up.

The audit is read-only. Cleanup actions belong to separate PRs that reference
the audit by commit hash.

## Current Disposition Reference

The audit findings (`RETIRED` candidates with exact file paths, promotion
candidates with source specs, duplication clusters with consolidation
recommendations) are recorded in a separate timestamped note rather than
embedded here, so this spec stays evergreen as the inventory evolves:

- `docs/superpowers/notes/2026-05-26-diagnostic-lifecycle-audit-note.md`

Future lifecycle audits append new notes under `docs/superpowers/notes/`
with their own date prefix. This section's link list is the only thing this
spec updates between audits. Cleanup actions belong to implementation PRs
that cite the relevant audit note by date plus this spec's rule numbers.

## Known Limitations

Second-round Codex review on 2026-05-26 identified three edge cases the
current rules do not fully cover. Each is noted here rather than fixed
preemptively, because the right shape of the fix is hard to predict without
a concrete real-world example. They will be revised when an implementation
PR genuinely hits them.

1. **`spec-designation` promotion has no anti-abuse mechanism.** An author
   could in principle write "this tool is a phase gate" in their own plan
   and trigger promotion without independent review. In practice the
   downstream cost of a promotion PR (shim + smoke test + schema
   preservation + move-only diff) is high enough that nuisance designation
   is unlikely. If an unjustified promotion attempt ever lands, add a rule
   that `spec-designation` triggers require a second reviewer's sign-off.

2. **The 90-day stable-importer trigger does not define start-time or
   interruption handling.** The current text says "remained stable for 90+
   days" without specifying whether the clock starts at the first import
   commit, when interruption resets it, or how partial periods compose. The
   interaction with the 60-day demotion rule appears healthy
   (importer-loss demotion fires before promotion-eligibility lapses), so
   the gap is latent. When a real tool ages into this window, define start
   and interruption semantics from the concrete case.

3. **`per-campaign` cadence has no time translation.** The seasonal-cadence
   exception scales the demotion window to "two full declared cadences,"
   but `per-campaign` is acceptable as a declaration without a day count.
   Today this resolves by treating undeclared `per-campaign` as the default
   60-day rule. If a `per-campaign` tool actually needs the exception,
   require the PR description to add an estimated day count alongside the
   cadence label.

These are not blockers for the first cleanup PR (PR A in the 2026-05-26
audit note). They will be revisited only when an implementation PR or
future audit surfaces a concrete case the current rules misjudge.

## Stop Conditions

This spec must be revised before:

- Any change that adds a new diagnostic category not covered by the four
  lifecycle states.
- Any decision to mix production code into `tools/diagnostics/` (currently
  forbidden by placement rules).
- Any cleanup PR that proposes to delete files outside the `RETIRED`
  definition (60 days + no docs + no caller + sentinel-only test).

If a tool's state is genuinely ambiguous, leave it `ACTIVE` and document the
ambiguity in a short note under `docs/superpowers/notes/`. Do not invent new
states informally; revise this spec instead.
