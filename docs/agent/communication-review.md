# Communication And Review Surfaces

This file carries the longer communication and review rules that used to live in
root `AGENTS.md`. Keep the root file limited to high-frequency guardrails.

## Verdict-First Communication

- Non-trivial wrap-ups must state the current verdict first: what is done, what
  is still blocked, and the next recommended step.
- Use plain language before implementation detail. Say what changed, where, how
  it was checked, what was skipped, and what risk remains.
- During long, tool-heavy work, explain what question the current tools are
  answering and how the result changes the next action. Do not rely on internal
  artifact names such as board row counts, slice labels, or TSV filenames
  without translating what they mean for the product decision.
- Final answers for implementation or validation work should include, when
  applicable: conclusion, changed files or artifact paths, verification run,
  remaining risk, and next action.

## Human Review Surfaces

- Separate machine artifacts from human review surfaces. TSV/JSON may be
  exhaustive; Markdown specs are mostly for agents; human-facing reports should
  be short, visual or indexed, and decision-oriented.
- Before creating a new HTML review surface, search for an existing review or
  gallery owner and reuse it when the artifact is the same kind of human
  decision surface. Prefer the established gallery shape (`review-table`,
  `data-filter-control`, `data-search-control`, PNG lightbox/overlay links, and
  `tools/diagnostics/gallery_browser_smoke.py`) over a task-specific standalone
  HTML renderer. A new HTML renderer needs an explicit owner-gap note and exit
  rule.
- Reusing the Gallery means reusing the interaction shell, not automatically
  reusing Backfill domain semantics. Discovery identity, Backfill authority,
  model selection, and MS2 evidence review modes must label their question,
  counts, blockers, overlays, and exit rule in their own vocabulary.
- Overlay/Gallery semantics need a maintained reader guide. If a change alters
  how Backfill, Discovery, or other evidence-review plots should be read,
  update `docs/superpowers/validation/evidence_overlay_interpretation_guide.html`
  in the same change, or state why the existing guide still applies.
- For Codex interactive HTML review, use the in-app Browser by default. Do not
  use Chrome, Computer Use, or standalone browser-control surfaces unless the
  task specifically depends on existing Chrome cookies, profile state, or an
  external browser. If the in-app Browser blocks a local `file://` URL, serve
  only the exact artifact directory on `127.0.0.1` and open that localhost URL
  in the in-app Browser.
- Manual review requests should include a compact review index with identifiers:
  sample, label or family id, m/z, RT/window, status, reason, and linked
  artifact path.
- Worktree or PR closeout should leave an operator-readable handoff: branch/task
  purpose, verdict, important artifacts, validation commands/results, active
  blockers, rejected paths still likely to recur, and an explicit next-step
  recommendation. Keep it as current state, not a chronological log.
- Active handoffs should stay short enough to read every time, normally under
  about 200 lines. Completed phase summaries belong in archive; long logs,
  stack traces, and scratch analysis belong in notes only when still useful.
- Status labels such as `[active]`, `[blocked]`, `[done]`, and `[superseded]`
  are useful in open-work sections. Remove `[done]` and `[superseded]` items
  from the active handoff during the next prune unless they prevent repeated
  mistakes.

## Review Checklist

After completing changes, quickly check:

- requirement fit;
- public contract drift;
- GUI / CLI / API behavior divergence;
- regression risk;
- missing tests;
- security issues;
- over-complexity;
- generated artifacts, marker maps, lockfiles, or docs that should be synced.

When reviewing progress or a checklist, distinguish infrastructure existence
from usable product behavior. Reports, wrappers, sidecars, and audit artifacts
prove observability; they do not prove production behavior.
