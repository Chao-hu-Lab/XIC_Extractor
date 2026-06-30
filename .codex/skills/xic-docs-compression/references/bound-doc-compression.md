# Docs Digestion Reference

This reference turns repeated XIC documentation cleanup failures into a single
decision process: digest meaning before moving files.

## Cradle-To-Grave Model

Every durable document needs both a current role and an exit rule.

| Stage | Repo responsibility | Exit question |
| --- | --- | --- |
| Draft/active plan, spec, goal, or note | Keep enough public context to execute safely. | What owner or active stub keeps the next action recoverable? |
| Implemented or superseded plan/spec | Preserve only stable claims, decisions, gates, and lessons. | Has the stable claim been absorbed into a canonical owner so the original can retire? |
| Validation result/report | Keep checker-readable evidence or compact verdict only if still current. | Is this live evidence, a stale snapshot, or private interpretation? |
| Closeout/handoff | Keep PR body or short stub when it is the durable public surface. | Can future work resume without reading private history? |
| Private history | Keep in Obsidian or ignored artifacts, not as repo authority. | Is there any public claim still missing from repo owners? |

## Three Routes

Final routing has only three answers:

- `obsidian_original`: long original goes to Obsidian. Repo keeps no long body,
  except a compact pointer/stub while provenance or referrers require it.
- `repo_distilled_plus_obsidian_original`: stable public claims go to a repo
  owner or compact stub; long original and private reasoning go to Obsidian.
- `repo_product_doc`: the file itself is a compact product, validation,
  governance, or operating document and stays in repo.

`needs_route_decision` is an audit state, not a destination.

## Route, Lifecycle, And Digestion

Route answers where the document ends. Lifecycle answers whether it is draft,
active, implemented, superseded, rejected, archived, or retired. Digestion
answers whether the useful meaning has been absorbed into the right public owner.

These are separate:

- a `repo_product_doc` may still duplicate another owner;
- a route-retained support file may still need owner absorption;
- an active plan may need to stay in repo now but exit to Obsidian later;
- a same-path stub may be necessary for active context or unresolved referrers
  without carrying authority;
- a generated manifest may be useful as a queue while not being product truth.

## What Bound Means

`exact_referrer_bound_support` means another tracked file names this path. It
does not mean the document still carries unique current knowledge.

Treat bound status as a warning about migration mechanics:

- update or preserve referrers before moving/removing the path;
- keep source lookup stable when an Obsidian original is expected;
- avoid breaking checker/status/manifest paths;
- do not infer semantic importance from the existence of a link.

## Durable Payload

Extract only information that helps current or future work:

- active product behavior, schema, public contract, or agent rule;
- active validation gate, checker input, retained summary, or schema;
- productization status, writer authority, or activation boundary;
- self-sufficient next action for an active handoff/plan;
- final decision and why it still holds;
- reusable failure lesson that prevents a likely repeated mistake;
- tombstone saying which old claim is superseded and where the current owner is.

Everything else is usually private history.

## Product Absorption Gate

Before closing a newly written `spec`, `plan`, `note`, or `handoff`, run a
small-model review whose only job is to compare the transient document against
the long-term owner. The review is not a general docs audit.

Use these outcomes:

- `pass_can_retire`: durable conclusions are present and correct in the owner;
  source-copy the original to Obsidian, then delete the repo original if exact
  referrers are absent.
- `missing_absorption`: a durable conclusion exists only in the transient doc;
  update the owner first.
- `incorrect_absorption`: the owner contains the claim but has drifted,
  weakened, or changed meaning; fix the owner first.
- `still_active`: keep a short active repo stub until execution finishes.

Do not preserve a same-path stub merely because the original existed. Stub only
when active continuation or exact path compatibility needs it.

## Waste Signals

Treat content as likely waste when it:

- records a branch-local pass/fail state without a current gate;
- repeats `diagnostic_only`, no ProductWriter authority, no default matrix
  change, or no workbook change without adding a unique decision;
- gives row/cell counts from old code or old fixtures;
- preserves command chronology, reviewer rationale, or branch sequencing;
- has a later validation family, product doc, or status index that owns the same
  conclusion;
- documents a blocked path that later work solved differently;
- exists only because a previous cleanup was afraid to remove a referrer-bound
  file.

## Topic Owner Rule

One topic gets one canonical repo owner. Same-topic files may remain only as:

- support artifacts;
- validation packets;
- generated manifests or indexes;
- closeouts;
- active stubs;
- checker-readable machine anchors;
- migration stubs that point back to the owner.

Topic indexes are browsing and migration queues. They must not redefine product
authority. If a topic has many support files, collapse the common claim into the
owner or a compact family index before touching individual files.

## Compression Pattern

For each family:

1. Name the current owner: product doc, validation family README, status index,
   authority manifest, schema, retained summary, or topic index.
2. Extract the tiny durable payload:
   - final decision;
   - still-valid reason;
   - current gate/checker;
   - public contract affected or explicitly unaffected;
   - stale/superseded note if needed.
3. Put repeated historical detail in Obsidian or drop it after explicit
   approval.
4. Retarget referrers to the compact owner, not to every historical artifact.
5. Auto-retire the repo original after Obsidian/source-copy handling when exact
   referrers are absent.
6. Leave a same-path stub only when active continuation or exact paths remain
   externally or repo-internally useful.

## Obsidian And Wiki Route

Obsidian is the private notebook, not repo authority. Use wiki/Obsidian skills
for vault-side work:

- `wiki-status` / `wiki-query`: find existing source copies or staged writes;
- `wiki-ingest` / `wiki-update`: write originals or distilled project knowledge
  after public repo claims are represented;
- `obsidian-markdown`: keep manual note syntax valid;
- `wiki-lint`: check links, frontmatter, summaries, provenance, visibility, and
  lifecycle;
- `wiki-stage-commit`: promote or reject staged pages.

Repo pointers should use `source_repo_path:<repo path>` and verified note
title/alias, not absolute vault paths.

## Action Guide

| Situation | Preferred action |
| --- | --- |
| Active product/agent contract | Keep or move claim into canonical repo owner. |
| Active execution plan | Keep short self-sufficient repo stub; long reasoning can go to Obsidian. |
| Implemented/superseded plan/spec | Distill stable claims, then source-copy original or tombstone. |
| Live checker/status/schema artifact | Keep as `current_contract`; do not stub. |
| Many validation reports repeat the same decision | Create/update one family index and retarget referrers. |
| Historical narrative with stable conclusion already in product docs | Source-copy to Obsidian, then delete from repo when exact referrers are absent. |
| Old result contradicted by later work | Tombstone with supersession pointer; do not keep as evidence. |
| File only proves a past implementation step happened | Move to Obsidian history; repo keeps no authority. |
| Exact path is still externally or internally bound | Prefer retargeting refs to the owner; keep a same-path stub only as temporary compatibility. |
| Unclear current value | Stop with `needs_human_decision`; do not migrate mechanically. |

## Backfill/Quant Heuristic

Backfill and quant-matrix validation history is especially likely to contain
high repetition. Start by grouping by validation family prefix, then compare:

- authority language;
- cell/row count claims;
- ProductWriter or default-output disclaimers;
- gate names;
- superseding validation families;
- current product doc links.

If the only unique part is an old count or an old pass/fail snapshot, it usually
belongs in Obsidian history, not as a retained repo authority surface.
