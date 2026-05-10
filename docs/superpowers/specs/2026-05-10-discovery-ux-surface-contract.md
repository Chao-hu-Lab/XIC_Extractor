# Discovery UX Surface Contract

## Summary

Discovery mode must separate backend evidence growth from the primary human review
surface. New evidence may improve scoring, grouping, debugging, and future batch
analysis, but it must not automatically make the first review file wider, noisier,
or harder to act on.

The product contract is:

```text
backend evidence can expand
primary review surface must stay compact
full provenance stays available for debugging and downstream work
batch and visualization layers answer different questions
```

This contract exists to prevent repeated drift between "add more information" and
"make the output easier to read."

## Surface Ownership

| Surface | Audience | Purpose | Expansion Policy |
|---|---|---|---|
| `discovery_review.csv` | Human reviewer | First-pass triage: what to inspect and why | Stable and compact. New columns require explicit contract update. |
| `discovery_candidates.csv` | Developer, downstream alignment, audit | Full candidate-level provenance | May append diagnostics at the end when needed. |
| `discovery_batch_index.csv` | Human reviewer, batch operator | Navigate per-sample outputs and summarize run-level counts | May add sample-level summary columns. Must not become candidate alignment. |
| Metrics artifact | Developer, performance tuning | Runtime, row counts, output sizes, candidate budget | Opt-in or debug-level unless promoted by a plan. |
| HTML / plots | Human reviewer, visual confirmation | Show patterns that tables cannot make obvious | Opt-in or batch-level summary. Do not emit per-sample heavy reports by default. |

## Core Principle

Do not solve a review UX problem by adding more columns to the primary review CSV.

When a new signal is added, route it using this decision:

1. Does it change whether a row should be reviewed now?
   - Use it in `review_priority`, `evidence_tier`, `evidence_score`, or
     `review_note`.
2. Does it explain the calculation, provenance, or debugging detail?
   - Add it to `discovery_candidates.csv`, usually appended after existing
     provenance columns.
3. Does it describe a sample or run, not an individual candidate?
   - Add it to `discovery_batch_index.csv` or a metrics artifact.
4. Does it require shape, trend, or distribution perception?
   - Put it in an opt-in visualization layer.

If none of those answers are clear, do not add the field yet.

## Review CSV Contract

`discovery_review.csv` is not a smaller full CSV. It is the first-pass review
queue. It should answer four questions without horizontal scrolling:

1. Should I inspect this row?
2. What evidence tier is it in?
3. Where do I find it in Xcalibur or the full CSV?
4. Why is it ranked here?

The current review CSV contract is:

```text
review_priority
evidence_tier
evidence_score
ms2_support
ms1_support
rt_alignment
family_context
candidate_id
precursor_mz
best_seed_rt
ms1_area
seed_event_count
neutral_loss_tag
review_note
```

Rules:

- Keep this file around 12-15 columns.
- Do not add raw scan-level diagnostics to this file.
- Do not add every new evidence metric to this file.
- Do not duplicate full CSV provenance here.
- Prefer improving `review_note` over adding a new column when a short phrase is
  enough.
- If a new column is proposed, it must replace or clarify an existing first-pass
  decision, not merely expose another internal variable.
- Any review CSV schema change requires updating tests that pin
  `DISCOVERY_BRIEF_COLUMNS` and this contract.

## Full Candidate CSV Contract

`discovery_candidates.csv` is the archival and alignment-ready candidate table.
It can contain full candidate-level evidence and provenance.

Rules:

- Preserve existing review-first columns unless an approved plan changes them.
- Append new provenance fields after existing provenance columns.
- Keep candidate ids stable enough for cross-file references.
- Keep Excel formula escaping for user-controlled text.
- Do not remove diagnostic fields just because they are not useful in first-pass
  review.
- Do not make full CSV optional in `standard` output level.

The full CSV is allowed to be complex because it is not the first UX surface.

## Batch Index Contract

`discovery_batch_index.csv` is navigation and run summary. It is not cross-sample
alignment.

Allowed batch index information:

- sample stem
- raw file path
- per-sample `discovery_review.csv` path
- per-sample `discovery_candidates.csv` path
- candidate counts
- priority counts
- evidence tier counts
- output sizes or metrics summary when implemented
- warnings about candidate explosion or output budget

Not allowed in v1 batch index:

- aligned feature rows across samples
- per-candidate evidence
- per-candidate family membership
- target annotation details

Cross-sample recurrence or alignment must be a separate artifact with its own
contract.

## Visualization Contract

HTML and plots should provide information that tables cannot show clearly:

- XIC shape around the selected candidate
- MS2 spectrum context
- RT or area trend across injection order
- batch-level distribution and outlier patterns
- family/superfamily structure when table rows are insufficient

Rules:

- Do not generate one heavy HTML report per RAW by default.
- Prefer batch-level or on-demand visualization.
- Do not use HTML to repeat the same table content already present in CSV.
- A plot is justified when it reduces ambiguity that a CSV cannot resolve.
- CSV remains the durable export; visualization is a review aid.

## Evidence Routing Table

| Evidence Type | Primary Destination | How It Affects Review |
|---|---|---|
| Strict MS2 NL seed count | Review CSV summary + full CSV detail | Affects `ms2_support`, score, and note. |
| Product intensity | Full CSV; summarized in `ms2_support` | Affects score and tier. |
| MS1 peak found / area / apex | Review CSV essentials + full CSV detail | Affects `ms1_support`, score, and note. |
| MS1 scan support score | Full CSV provenance; summarized in `ms1_support` | Affects score, but not a separate review CSV column by default. |
| RT seed-to-apex delta | Full CSV detail; summarized in `rt_alignment` | Affects score and note. |
| Feature family / superfamily | Full CSV detail; summarized in `family_context` | Helps suppress duplicate attention. |
| Known target annotation | Future full CSV detail; optional review note | Enters review CSV only if it changes first-pass action. |
| Batch recurrence | Future batch summary artifact | Should not be forced into single-sample review CSV. |
| Performance metrics | Metrics artifact / batch index summary | Does not affect candidate review directly. |

## Review Priority Contract

The primary UX must be a funnel, not a data dump.

Expected interpretation:

- `HIGH`: inspect first. Should remain a small subset.
- `MEDIUM`: plausible, but not first-pass unless the reviewer is exploring.
- `LOW`: retained for traceability, not a normal first-pass target.

If `MEDIUM` dominates a batch, the answer is not to add more columns. The next
step is to improve one of:

- evidence scoring thresholds,
- family/superfamily representative selection,
- batch recurrence summary,
- profile selection (`loose`, `default`, `strict` in a future plan),
- or visualization for the ambiguous subset.

## Output Level Contract

Discovery output should eventually support output levels, but the UX contract is
already stable:

| Level | Expected UX |
|---|---|
| `minimal` | Fast run, review CSV and navigation only. Not archival. |
| `standard` | Default. Review CSV plus full candidate CSV. |
| `debug` | Standard outputs plus extra diagnostics, metrics, and optional visuals. |

Until output levels are implemented, current standard output is:

```text
single RAW:
  discovery_review.csv
  discovery_candidates.csv

RAW directory:
  discovery_batch_index.csv
  <sample>/discovery_review.csv
  <sample>/discovery_candidates.csv
```

## Change Control

Before adding a new discovery output field or artifact, answer:

1. Which surface owns it?
2. Who is the reader?
3. What decision does it help?
4. Can it be summarized through an existing review column or `review_note`?
5. Does it create a new public schema contract?
6. Does it require a regression test?
7. Does it increase output volume enough to require metrics or an output-level
   decision?

If the change affects `discovery_review.csv`, it must update:

- this contract,
- `DISCOVERY_BRIEF_COLUMNS`,
- the review CSV schema test,
- and any docs describing the discovery output contract.

If the change only affects `discovery_candidates.csv`, append fields and update
the full CSV schema test.

## Anti-Patterns

Avoid these recurring failure modes:

- Adding a column to `discovery_review.csv` because a new metric exists.
- Turning the batch index into implicit alignment.
- Creating per-sample HTML reports by default.
- Duplicating the same evidence in review, full, batch, and HTML surfaces.
- Hiding full provenance to make the first review file look clean.
- Treating `MEDIUM` row explosion as a formatting problem instead of a funnel
  problem.
- Making users understand evidence weights directly instead of using profiles.

## Relationship To Existing Specs

This document constrains discovery output surfaces. It complements:

- `2026-05-09-untargeted-discovery-v1-spec.md`
- `2026-05-10-discovery-output-performance-spec.md`

If a future implementation plan conflicts with this contract, the plan must
explicitly update this contract first. Silent drift is not allowed.
