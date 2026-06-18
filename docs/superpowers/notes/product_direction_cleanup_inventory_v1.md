# Product Direction Cleanup Inventory v1

Date: 2026-06-18
Status: `diagnostic_only` cleanup inventory
Scope: Backfill evidence lifecycle direction reset on branch
`cc/framework-improvements`

This inventory records the cleanup decisions made while dismantling the
scorer-centered Backfill follow-up. It does not grant product authority and
does not change ProductWriter, matrix, workbook, selected peak/area, counted
detection, GUI, default extraction, RAW behavior, or broad Backfill state.

Retrospective exception: the three untracked scorer JSON scratch artifacts
listed below were deleted before this inventory was written, so their content
hashes cannot be recovered here. This exception is documented so it is not
mistaken for the durable cleanup pattern. Future delete, archive, rewrite, or
demotion actions must be inventoried before the action, including source hash
when applicable.

## Disposition Table

| Path | Tracked State | Action | Authority Relevance | Reason | Archive Target Or Not Archived Reason | Source Hash |
|---|---|---|---|---|---|---|
| `docs/superpowers/validation/lockbox_shadow_scoring_schema_v1.json` | untracked | retrospective delete exception | none; wrong-direction scorer surface | scorer schema would create a dormant product surface after the direction reset | not archived; untracked scratch artifact and not a source of current authority | unavailable; removed before this inventory was written, and future cleanup must not repeat this pattern |
| `docs/superpowers/validation/lockbox_shadow_metrics_contract_v1.json` | untracked | retrospective delete exception | none; wrong-direction scorer surface | metrics contract would steer future work back to score optimization | not archived; untracked scratch artifact and not a source of current authority | unavailable; removed before this inventory was written, and future cleanup must not repeat this pattern |
| `docs/superpowers/validation/lockbox_shadow_stop_rules_v1.json` | untracked | retrospective delete exception | none; wrong-direction scorer surface | stop-rule JSON implied a scorer-centered lane instead of evidence-chain work | not archived; untracked scratch artifact and not a source of current authority | unavailable; removed before this inventory was written, and future cleanup must not repeat this pattern |
| `scripts/build_lockbox_shadow_automation_experiment_design.py` | tracked | demote scorer diff / retain baseline | existing lockbox automation remains case/review substrate only | scorer adapter changes were not part of the evidence-chain blueprint | not archived; baseline script remains tracked in git | unchanged relative to tracked content at this checkpoint |
| `tests/test_lockbox_shadow_automation_experiment_design.py` | tracked | demote scorer diff / retain baseline | existing lockbox automation remains case/review substrate only | scorer adapter tests were removed with the scorer adapter direction | not archived; baseline tests remain tracked in git | unchanged relative to tracked content at this checkpoint |
| `docs/superpowers/goals/XIC_Extractor_Productization_Roadmap_Review.md` | untracked | rewrite | roadmap only; no authority | replace scorer-centered next step with evidence lifecycle phase order | not archived; this is the active roadmap review artifact | current working-tree file is the source |
| `docs/superpowers/plans/2026-06-18-backfill-evidence-lifecycle-blueprint.md` | untracked | create/rewrite | planning entry point only; no authority | convert deepresearch notes into phase contracts and stop rules | not archived; this is the active blueprint artifact | current working-tree file is the source |
| `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md` | tracked | rewrite/prune | handoff only; no authority | keep current state short and point next work to evidence-chain packet | not archived; current handoff is the active snapshot | current working-tree file is the source |
| `docs/deepresearch/README.md` | tracked | rewrite index wording | background notes only; no authority | index new research while preventing broad Backfill reopening by research wording alone | not archived; README remains active index | current working-tree file is the source |

## Retained Source Assets

- `docs/superpowers/validation/lockbox_shadow_automation_cases_v1.tsv` remains
  the only 72-case lockbox automation source.
- Existing lockbox automation builder/test remain as case/review substrate and
  were not promoted into a scorer or authority lane.
- Productization control-plane authority remains unchanged: current Backfill
  write authority is 511 cells and broad Backfill remains parked.
