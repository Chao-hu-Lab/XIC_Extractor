# Backfill Evidence Reconciliation Gallery Design

## Status

Design draft for review. No implementation is included in this document.

Validation label: `diagnostic_only` / `shadow_review`.

This design does not change owner backfill, selected peaks, matrix inclusion,
alignment TSV schemas, workbook outputs, RAW/DLL reads, or production gates. It
defines a human review gallery that reconciles current product behavior with
existing backfill evidence artifacts.

## Productization Decisions, 2026-06-07

These decisions scope the follow-up Goal and implementation plan.

### Finish Line

The end-to-end Goal is conditional:

- first reach `production_candidate` with a working reconciliation index,
  gallery, and reviewed evidence chain;
- continue to product promotion only when subagent review, public-contract
  audit, 8RAW validation, and 85RAW validation all pass for a narrow,
  allowlisted slice;
- otherwise stop at `shadow_ready` or `production_candidate` and name the exact
  missing evidence, blocker, or product decision.

### Surface Strategy

- The gallery includes all backfill family/seed groups.
- Review order is disagreement-first so evidence-chain gaps surface early.
- Product promotion is narrow: only allowlisted provisional-retention or
  equivalently reviewed candidate slices may be promoted. Full backfill-system
  promotion is out of scope.

### Evidence Authority Policy

- Strong visual/overlay evidence that lacks product-grade sidecar support may
  trigger upstream evidence work in the same Goal.
- Manual visual judgment can calibrate and challenge the rules, but it cannot
  directly become a product gate.
- Product promotion requires machine-readable, reviewed, product-grade evidence
  and must not be inferred from the gallery alone.

### Validation Policy

- Gallery / reconciliation / `shadow_ready` work can be validated with synthetic
  tests, existing-artifact smoke, and 8RAW or existing 85RAW artifacts.
- Product promotion / `production_ready` requires 85RAW validation.
- A product-ready claim is scoped to the allowlisted slice that passed; blocker
  families remain `review_only`, `blocked`, or `not_assessable`.

### Promotion Policy

Use allowlist promotion:

- promote only family/seed groups that pass the product-grade evidence chain;
- keep blocked, missing-overlay, missing-seed-provenance, stale-source, or
  high-interference groups out of production behavior;
- do not require every backfill family to pass before promoting a proven narrow
  slice;
- never describe the result as full backfill-system `production_ready` unless a
  separate reviewed contract validates that broader scope.

## Goal

Build a backfill evidence reconciliation gallery that lets a reviewer answer:

- what the product currently did for a backfilled or backfill-eligible family;
- which seed/request context explains the backfill;
- which existing evidence supports, blocks, or cannot assess the backfill;
- where visual evidence and product behavior disagree;
- which artifact is missing when the evidence chain is incomplete.

The gallery should expose the same evidence chain that product and diagnostic
sidecars already produce. It must not become a second scorer.

## Product Spine

This design makes existing `EvidenceVector` and `AuditTrail` evidence easier to
inspect. It is a reconciliation and explanation surface for existing product
behavior and existing diagnostics. It does not create new product-grade evidence
authority.

It does not advance `IntegrationResult`, product model selection, final matrix
construction, or `Trace` / `TraceGroup` ownership directly. RAW-backed overlay
trace JSON paths may be linked as evidence provenance, but this gallery does not
re-read RAW files or produce new traces.

## Background

The current backfill stack already has useful but separated evidence surfaces:

- `alignment_cells.tsv` and `alignment_review.tsv` describe product and
  provisional backfill outcomes.
- `alignment_owner_backfill_seed_audit.tsv` records actual owner-backfill seed
  and request context.
- `family_ms1_overlay_*` artifacts show RAW-backed overlay evidence and expose
  shape, coverage, apex, local dominance, and interference metrics.
- `seed_aware_backfill_review.py` classifies rescued-heavy families as a shadow
  review candidate.
- `alignment_production_candidate_gate.tsv`, when present, separates positive
  support, dependent context, and challenge blockers for provisional backfill
  candidate rows.

The problem is not that no evidence exists. The problem is that the product
decision, sidecar evidence, overlay images, and reviewer interpretation can be
hard to inspect in one place. A reviewer may visually see cells that look
backfillable while product behavior remains conservative. That can mean either
the reviewer is over-trusting visual shape, or the evidence chain is broken
between diagnostics and product behavior. The gallery should make that
disagreement explicit.

## Design Principles

- Product behavior remains the authority for what actually happened.
- Existing evidence artifacts remain the authority for support and blockers.
- The gallery renders and reconciles; it does not select, promote, demote, or
  mutate rows.
- Similarity metrics are evidence components, not a new aggregate score.
- Do not recompute a metric in the gallery if an upstream diagnostic already
  owns it.
- Do not add weights that double-count related evidence such as shape
  similarity, apex coherence, and boundary overlap.
- Missing evidence is a first-class state, not an empty cell.
- Evidence that supports backfill and evidence that challenges backfill must be
  shown separately.
- Human review should become a calibration and exception surface, not the hidden
  production decision path.

## Non-Goals

- Do not change `alignment_matrix.tsv`, `alignment_cells.tsv`,
  `alignment_review.tsv`, workbook outputs, or any existing public schema.
- Do not add a production gate.
- Do not promote `production_candidate` into a matrix role.
- Do not automatically generate missing overlays.
- Do not re-read RAW files.
- Do not make similarity score a new single-number decision authority.
- Do not replace `seed_aware_backfill_review.py`,
  `family_ms1_overlay_plot.py`, or `provisional_backfill_candidate_gate.py`.
- Do not require manual review for every backfill row before normal use.

## Inputs

The first implementation should consume existing artifacts only.

Required where available:

- `alignment_review.tsv`
- `alignment_cells.tsv`

Optional evidence inputs:

- `alignment_matrix.tsv`
- `alignment_owner_backfill_seed_audit.tsv`
- one or more `family_ms1_overlay_batch_summary.tsv`
- overlay PNG/PDF paths from overlay summaries
- overlay trace-data JSON paths from overlay summaries
- `seed_aware_backfill_review_families.tsv`
- `seed_aware_backfill_review_summary.tsv`
- `alignment_production_candidate_gate.tsv`
- `alignment_tier2_trace_evidence.tsv`

If an optional input is absent, the gallery should continue and emit explicit
`missing_*` evidence states for affected groups.

## Output Shape

Recommended future CLI:

```text
tools/diagnostics/backfill_evidence_reconciliation_gallery.py
```

Recommended package renderer / model module:

```text
xic_extractor/diagnostics/backfill_reconciliation_gallery.py
```

Recommended outputs:

```text
backfill_evidence_reconciliation_gallery.html
backfill_evidence_reconciliation_groups.tsv
backfill_evidence_reconciliation_representative_cells.tsv
backfill_evidence_reconciliation_summary.json
```

The TSV/JSON outputs are machine-readable review indexes. The HTML is the human
review surface. The HTML should not be the only place where reconciliation class
or missing-evidence state is stored.

### CLI / Input Contract

The first implementation should expose a diagnostic CLI with explicit input
paths. Required arguments:

| Argument | Required | Meaning |
| --- | --- | --- |
| `--alignment-review-tsv` | yes | Source `alignment_review.tsv`. |
| `--alignment-cells-tsv` | yes | Source `alignment_cells.tsv`. |
| `--output-dir` | yes | Directory for HTML, TSV, and JSON review outputs. |

Optional arguments:

| Argument | Repeatable | Meaning |
| --- | --- | --- |
| `--alignment-matrix-tsv` | no | Optional matrix output used only to display matrix inclusion context. |
| `--backfill-seed-audit-tsv` | no | Optional `alignment_owner_backfill_seed_audit.tsv`. |
| `--overlay-batch-summary-tsv` | yes | Optional family/seed overlay batch summary. |
| `--seed-aware-family-tsv` | no | Optional `seed_aware_backfill_review_families.tsv`. |
| `--seed-aware-summary-tsv` | no | Optional `seed_aware_backfill_review_summary.tsv`. |
| `--candidate-gate-tsv` | no | Optional `alignment_production_candidate_gate.tsv`. |
| `--tier2-trace-evidence-tsv` | no | Optional `alignment_tier2_trace_evidence.tsv`. |
| `--source-run-id` | no | Optional user-supplied run label displayed as provenance only. |

The CLI must not accept RAW or DLL paths in v0. If missing overlays should be
generated later, that belongs in an explicit upstream overlay-generation command
or follow-up workflow, not this gallery command.

### Output Schema Contract

All machine-readable outputs should include a `schema_version` field. Initial
version:

```text
backfill_evidence_reconciliation_v0
```

Minimum `backfill_evidence_reconciliation_groups.tsv` columns:

| Column | Stable values / meaning |
| --- | --- |
| `schema_version` | `backfill_evidence_reconciliation_v0` |
| `priority_rank` | Integer display rank after disagreement-first sorting. |
| `feature_family_id` | Family ID from source artifacts. |
| `seed_group_id` | Deterministic gallery seed-group key. |
| `seed_group_basis` | `seed_audit`, `seed_aware_summary`, or `family_center_fallback`. |
| `seed_mz` | Seed m/z when known. |
| `seed_rt` | Seed RT when known. |
| `seed_rt_window` | Source request RT window when known. |
| `seed_ppm` | Source request ppm when known. |
| `tag_or_class` | Tag/class field when available; empty otherwise. |
| `product_behavior_state` | Stable value from the Product Behavior Axis. |
| `evidence_authority_state` | `product_grade_support`, `review_only_visual_support`, `dependent_context_only`, `human_visual_judgment_only`, `evidence_blocks_backfill`, `evidence_inconclusive`, or `not_assessable`. |
| `reconciliation_class` | Stable value from Reconciliation Classes. |
| `detected_cell_count` | Count from source artifacts. |
| `rescued_cell_count` | Count from source artifacts. |
| `provisional_cell_count` | Count from source artifacts when available. |
| `top_product_reason` | Existing product/review reason; not newly inferred. |
| `top_support_component` | Source support token, if any. |
| `top_blocker` | Source blocker token, if any. |
| `missing_evidence` | Semicolon-separated `missing_*` / `stale_*` / `join_gap_*` tokens. |
| `overlay_png_path` | Linked overlay PNG when known. |
| `overlay_trace_json_path` | Linked trace-data JSON when known. |
| `source_artifacts` | Semicolon-separated source artifact labels. |
| `source_warnings` | Semicolon-separated stale/hash/join warnings. |

Minimum `backfill_evidence_reconciliation_representative_cells.tsv` columns:

| Column | Stable values / meaning |
| --- | --- |
| `schema_version` | `backfill_evidence_reconciliation_v0` |
| `feature_family_id` | Family ID. |
| `seed_group_id` | Deterministic gallery seed-group key. |
| `representative_roles` | Semicolon-separated role tokens. |
| `sample_stem` | Source sample stem/name. |
| `cell_status` | Source cell status. |
| `product_cell_state` | Source product cell state if available. |
| `shape_similarity` | Existing source metric only; empty if absent. |
| `scan_support_score` | Existing source metric only; empty if absent. |
| `apex_delta_sec` | Existing or directly sourced delta; empty if absent. |
| `boundary_overlap` | Existing source metric only; empty if absent. |
| `interference_signal` | Existing source metric/token only; empty if absent. |
| `representative_reason` | Why this cell was selected for display. |
| `source_row_key` | Stable source key when available. |

Minimum `backfill_evidence_reconciliation_summary.json` keys:

| Key | Meaning |
| --- | --- |
| `schema_version` | `backfill_evidence_reconciliation_v0` |
| `validation_label` | `diagnostic_only` / `shadow_review` |
| `group_count` | Number of rendered groups. |
| `representative_cell_count` | Number of representative rows. |
| `reconciliation_class_counts` | Object keyed by reconciliation class. |
| `missing_evidence_counts` | Object keyed by missing/stale/join-gap token. |
| `input_artifacts` | Paths and optional hashes when available. |
| `matrix_contract_changed` | Always `false` for this diagnostic. |
| `product_behavior_changed` | Always `false` for this diagnostic. |

## Grouping Model

The primary gallery row unit is:

```text
feature_family_id + seed_group_id
```

Seed grouping should prefer actual owner-backfill seed/request provenance:

- seed m/z;
- seed RT;
- request RT window;
- request ppm;
- source seed count or seed group label when present.

If no seed audit is available, the fallback group is:

```text
feature_family_id + family_center_unknown_seed
```

The fallback must be visibly marked because a family-centered overlay can be a
false negative for multi-seed backfill. A group with multiple distinct seeds
should not be collapsed into one visual decision unless the source artifact has
already made that grouping explicit.

`seed_group_id` must be deterministic and must not depend on row order alone.
Recommended construction:

```text
seed::<feature_family_id>::mz=<seed_mz>::rt=<seed_rt>::window=<rt_start>-<rt_end>::ppm=<ppm>
```

Normalize numeric values with the source precision preserved when possible. If a
numeric field is missing, use an explicit token such as `rt=unknown`, not an
empty segment. For fallback groups:

```text
family_center::<feature_family_id>::seed=unknown
```

When upstream mode-aware artifacts provide `peak_hypothesis_id`, v0 may display
it as context but should mark the group `mode_ambiguous` unless the source
artifact already supplies a stable mode/seed join. The gallery must not invent
mode identity from overlay windows.

## Product Behavior Axis

The gallery should classify product behavior separately from evidence support.
Suggested values:

| Value | Meaning |
| --- | --- |
| `product_primary_backfilled` | The product output includes rescued/backfilled cells in a primary matrix role. |
| `product_rescued_context_only` | Cells exist as rescued/provisional context but are not primary matrix evidence. |
| `product_provisional` | The row is retained as provisional or candidate context. |
| `product_review_only` | Existing artifacts mark the row as review-only. |
| `product_not_backfilled` | No current product backfill acceptance is visible for the group. |
| `product_unknown` | Required product artifact is missing or cannot be joined. |

The implementation must document which source fields map to each value. It must
not infer primary matrix inclusion from `status=rescued` alone when the row role
or matrix output says otherwise.

## Evidence Authority Axis

The gallery should classify evidence authority separately from product behavior.
This avoids turning visual triage into hidden product policy.

| Value | Meaning |
| --- | --- |
| `product_grade_support` | Existing allowlisted Tier 2 / candidate-gate evidence supports the row and passes its own provenance/blocker checks. |
| `review_only_visual_support` | Existing seed-aware or overlay verdict supports visual review, but is not product-grade support. |
| `dependent_context_only` | Seed provenance, RT coherence, scan-support distribution, or artifact context explains the row but cannot support promotion alone. |
| `human_visual_judgment_only` | Manual reviewer note supports backfill, but no machine-readable support component is available. |
| `evidence_blocks_backfill` | Existing blockers or overlay verdicts conflict with automatic backfill. |
| `evidence_inconclusive` | Mixed or weak evidence; support and blockers do not resolve the group. |
| `not_assessable` | Missing overlay, missing seed provenance, stale source, or join gap prevents assessment. |

### Evidence Source Mapping

| Source | May provide | Must not provide |
| --- | --- | --- |
| `alignment_production_candidate_gate.tsv` | `product_grade_support`, blockers, dependent context, source hashes, staleness warnings | New scoring or reinterpretation of overlay metrics. |
| `alignment_tier2_trace_evidence.tsv` | Product-grade support only when accepted by the candidate-gate contract | Direct gallery promotion without gate validation. |
| `seed_aware_backfill_review_*` | `review_only_visual_support`, visual blockers, `shadow_gate_ready` context | Product-grade support or matrix readiness. |
| `family_ms1_overlay_batch_summary.tsv` / trace JSON | Visual support/blockers, shape/context metrics, PNG/JSON links | Product-grade support, unless an upstream reviewed gate has already consumed it. |
| `alignment_owner_backfill_seed_audit.tsv` | Seed/request provenance and dependent context | Independent positive support. |
| `alignment_review.tsv` / `alignment_cells.tsv` / `alignment_matrix.tsv` | Product behavior state and source reasons | Visual support or Tier 2 evidence. |
| Manual notes | `human_visual_judgment_only` when explicitly supplied in future | Machine support without a reviewed schema. |

If multiple evidence sources are present, the gallery should show them side by
side. It should not collapse them into a single truth source. The
`evidence_authority_state` column stores the strongest authority level observed,
but supporting detail columns must preserve whether the source was
product-grade, review-only visual, dependent context, or human judgment.

Missing, stale, hash-mismatched, or unsafe joins fail closed into `not_assessable`
with explicit `missing_evidence` / `source_warnings` tokens.

## Reconciliation Classes

Reconciliation class is the cross product of product behavior and evidence
state. Suggested high-level classes:

| Class | Meaning |
| --- | --- |
| `product_accepts_and_product_grade_supports` | Product behavior and product-grade evidence agree. |
| `product_accepts_and_visual_supports` | Product behavior and review-only visual evidence agree, but product-grade support is not established by the gallery. |
| `product_rejects_but_product_grade_supports` | Product is conservative or non-primary, but existing product-grade sidecar evidence supports the row. |
| `product_rejects_but_visual_supports` | Product is conservative or non-primary, while review-only visual evidence supports backfill. |
| `product_accepts_but_evidence_conflicts` | Product accepts or retains backfill while evidence has blockers. |
| `product_rejects_and_evidence_blocks` | Product behavior and evidence both block automatic backfill. |
| `evidence_inconclusive` | Existing evidence cannot decide the disagreement. |
| `not_assessable_missing_overlay` | Visual/trace evidence is missing. |
| `not_assessable_missing_seed_provenance` | Seed-aware grouping is blocked by missing seed context. |
| `not_assessable_join_gap` | Artifacts are present but cannot be joined safely. |

Default sort order should be disagreement-first:

1. `product_rejects_but_product_grade_supports`
2. `product_rejects_but_visual_supports`
3. `product_accepts_but_evidence_conflicts`
4. `not_assessable_missing_overlay`
5. `not_assessable_missing_seed_provenance`
6. `not_assessable_join_gap`
7. `evidence_inconclusive`
8. `product_accepts_and_visual_supports`
9. `product_accepts_and_product_grade_supports`
10. `product_rejects_and_evidence_blocks`

The gallery should include all backfill family/seed groups, not only
disagreements, but it should sort and filter so review starts with the cases
most likely to expose evidence-chain gaps.

## Similarity and Evidence Components

Similarity-related fields may include:

- `shape_similarity_median`
- `rescued_shape_similarity_median`
- per-cell shape similarity when already emitted by an overlay diagnostic
- `selected_apex_in_trace_window_fraction`
- `local_apex_supported_fraction`
- `global_trace_apex_delta_abs_median_min`
- `rescued_boundary_overlap_min`
- `scan_support_score`

Challenge fields may include:

- `neighbor_interference`
- `neighboring_interference_challenge`
- `low_assessable_coverage_challenge`
- `selected_boundary_local_apex_inconsistency`
- `rescued_apex_span_wide`
- `rescued_boundary_overlap_low`
- `low_scan_support`
- `weak_scan_support`

These fields should be displayed as named support/blocker/context components.
The gallery must not combine them into a new weighted score. If a compact
display number is needed, it should be labeled as a source metric such as
`rescued_shape_similarity_median`, not `backfill_score`.

If a required component is not currently emitted by an upstream artifact, the
preferred follow-up is to extend that upstream diagnostic or sidecar. The
gallery renderer should not become the metric owner.

## Representative Cells

The HTML details section must not dump every cell by default. It should show
representative cells and link the full TSV/JSON evidence.

Representative roles:

| Role | Selection intent | Sort key | Tie-break |
| --- | --- | --- | --- |
| `strongest_support` | Rescued cell with strongest existing support evidence. | Highest product-grade support flag, then highest source `shape_similarity`, then highest `scan_support_score`, then highest `boundary_overlap`. | `sample_stem`, then source row key. |
| `strongest_blocker` | Rescued cell with strongest blocker or conflict evidence. | Product-grade blocker first, then highest interference token/severity, then lowest `boundary_overlap`, then widest apex delta. | `sample_stem`, then source row key. |
| `lowest_similarity` | Rescued cell with lowest available shape similarity. | Lowest existing source `shape_similarity`. | `sample_stem`, then source row key. |
| `highest_interference` | Cell with strongest neighboring-interference signal. | Highest existing interference metric/severity; if only tokens exist, blocker token presence sorts before absence. | `sample_stem`, then source row key. |
| `seed_representative` | At least one representative cell for each seed group. | Smallest absolute seed-to-apex delta when available, then first rescued cell by sample. | `sample_stem`, then source row key. |
| `product_disagreement_example` | Cell that best illustrates product/evidence disagreement. | Product/evidence disagreement class priority, then strongest support or blocker according to the group class. | `sample_stem`, then source row key. |

The representative-cell TSV should store all selected representative rows and
their role. If two roles point to the same cell, keep one row with
semicolon-separated representative roles.

The implementation must not invent a composite score for representative-cell
selection. It may sort by existing source metrics and documented tie-breaks
only. If a role cannot be selected because required source metrics are absent,
emit a representative warning rather than selecting a misleading proxy.

## HTML Review Surface

The HTML should be table-first and dense, because it is a review queue, not a
landing page.

### Default Delivery UX Brief

The default gallery is a human review workbench, not a dashboard and not a TSV
clone. Its first job is to help a reviewer decide where to look next without
losing the evidence chain needed to explain a backfill decision.

Design references used as input:

- GitHub Primer `DataTable`: row identity, table title/description, compact
  density, action column accessibility, and numeric/action alignment.
- IBM Carbon `Data table`: toolbar/search/filter placement, expandable rows,
  row hover and zebra scanning, row/header size consistency, and giving dense
  tables enough page width.
- CFPB table guidance: preserve semantic tables, use horizontal scrolling for
  wide tabular data, and keep cell labels available for responsive views.
- GitHub accessibility-annotation guidance: custom components still need
  explicit focus, keyboard, ARIA, and state contracts even when they follow a
  design system.

Local rules for this gallery:

- The main table is a decision index. It should show one family per row, a
  compact seed m/z/RT/window summary, product state, evidence state, top issue,
  counts, overlay action, and details action.
- The main table should not show every artifact field. Source paths, hashes,
  representative cells, and full support/blocker lists live in collapsed details
  and TSV/JSON links.
- The family column is row identity. It should remain visible during horizontal
  scrolling, while numeric/action columns are visually centered and evidence
  text remains left aligned.
- Details are organized as an evidence chain: seed/request context, product
  behavior, RT/alignment context, Gaussian15 own-max MS1 shape, Candidate MS2/NL
  or product-grade support, blockers/missing evidence, representative cells, and
  source artifacts.
- Status badges must communicate state through text, border weight, and shape;
  color is only a secondary cue.
- The PNG modal should keep a stable header with caption, direct PNG access, and
  close action. Keyboard focus stays inside the modal while open and returns to
  the trigger on close.
- The renderer must not add a composite score or recompute missing evidence to
  make the UI look cleaner.

Required first-screen summary:

- group count;
- rescued/backfill cell count;
- reconciliation class counts;
- missing overlay count;
- missing seed-provenance count;
- input artifact links;
- validation label: `diagnostic_only` / `shadow_review`;
- explicit copy that the gallery does not mutate alignment matrix, cells,
  review TSVs, workbooks, or product decisions.

Main table columns:

- priority;
- family;
- seed group;
- tag / class when available;
- product behavior;
- evidence state;
- reconciliation class;
- rescued/detected/provisional counts;
- top support component;
- top blocker;
- overlay action;
- details.

Details section:

- seed/request provenance;
- source artifact paths and hashes when available;
- support components;
- blockers;
- dependent context;
- representative cells table;
- full TSV/JSON links.

PNG behavior:

- direct PNG anchor fallback;
- lazy thumbnail or explicit open action;
- vanilla JS lightbox only as enhancement;
- escaped DOM attributes only;
- keyboard access and focus restore.

Accessibility:

- `lang="zh-Hant"` for human-facing chrome if the HTML copy is Traditional
  Chinese;
- field tokens remain English;
- status must not rely on color alone;
- table headers need scopes;
- details and modal controls need accessible names.

## Information Volume Controls

The gallery includes all backfill family/seed groups, but must avoid turning the
HTML into a TSV clone.

Controls:

- default collapsed details;
- disagreement-first sorting;
- summary counts instead of full cell floods;
- representative-cell details only;
- filters for reconciliation class, tag, product behavior, evidence state, top
  blocker, and missing evidence;
- no eager loading of all overlay PNGs;
- full evidence remains in TSV/JSON links.

## Join and Staleness Rules

The gallery must fail closed when artifacts cannot be joined safely.

Required join checks:

- family IDs must match exactly when used as keys;
- seed provenance must match by explicit seed fields, not by fuzzy RT/mz alone;
- optional artifact hashes should be displayed when source sidecars provide
  them;
- missing or stale candidate-gate/Tier 2 sidecars must produce
  `not_assessable_join_gap` or a source-staleness warning, not silent support.

If a group is rendered from artifacts that may come from different runs, the
gallery must show a run-provenance warning. Future implementation should prefer
source hashes from existing sidecars rather than inventing a new provenance
scheme.

## Implementation Boundary

The future implementation should keep boundaries aligned with
`docs/architecture-contract.md`:

- package module owns TSV loading helpers, row models, joins, reconciliation
  classification, and HTML/TSV/JSON rendering;
- diagnostic CLI parses arguments, validates path presence, delegates to package
  functions, and reports written outputs;
- no RAW reads;
- no product-domain recomputation inside the HTML renderer;
- no changes to alignment or extraction behavior.

## Implementation Slices

To keep the first implementation reviewable, split delivery:

### Slice 0: Machine Reconciliation Index

- Load required and optional artifacts.
- Build deterministic family/seed groups.
- Classify product behavior, evidence authority, reconciliation class, missing
  evidence, source warnings, and representative cells.
- Write groups TSV, representative-cells TSV, and summary JSON.
- Do not require HTML polish in this slice.

Slice 0 closes whether the evidence chain can be represented without inventing a
new score or mutating product behavior.

### Slice 1: Human HTML Gallery

- Render the Slice 0 indexes into a table-first gallery.
- Add filters, collapsed details, representative-cell details, and PNG
  lightbox/fallback behavior.
- Keep source TSV/JSON links as the complete evidence record.

Slice 1 closes review-queue usability. It does not close product readiness.

### Slice 2: Upstream Evidence Gaps

Only after Slice 0/1 identifies recurring missing evidence should follow-up work
extend upstream diagnostics, overlay producers, or candidate gates. The gallery
itself should not patch those gaps by recomputing metrics.

## Exit Rules

This diagnostic path must have explicit exits:

- **Promote:** A separate reviewed production-gate or matrix contract consumes
  product-grade evidence. The gallery may provide review evidence for that
  decision, but it cannot be the gate.
- **Externalize:** If the only durable value is human browsing of diagnostics,
  keep the gallery as a review artifact and document that it is not a promotion
  path.
- **Fix upstream:** If repeated `missing_*` states block review, extend the
  upstream artifact that owns the missing evidence. Do not compute the missing
  metric inside the gallery.
- **Kill:** If implementing the gallery requires a composite score, RAW reads,
  or hidden policy decisions, stop the gallery and write a narrower diagnostic
  or production-gate spec instead.

The gallery can close only `review queue observability`. It cannot close
`production_ready`, matrix inclusion, or backfill policy changes.

## Test Strategy

Focused unit tests:

- group construction from family + seed provenance;
- fallback grouping when seed audit is missing;
- product behavior classification from synthetic alignment rows;
- evidence-state classification from candidate-gate and overlay rows;
- reconciliation class cross product;
- representative-cell selection and role deduplication;
- missing overlay / missing seed provenance / join-gap states;
- no aggregate `backfill_score` output;
- HTML escaping for family/sample/tag/path values;
- direct PNG fallback and lightbox markers;
- sticky table/details/a11y markers.

Fixture smoke:

- tiny synthetic artifact set with one group per reconciliation class;
- optional missing-overlay fixture;
- optional multi-seed family fixture showing why seed grouping matters.

Commands for future implementation:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_backfill_evidence_reconciliation_gallery.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools/diagnostics/backfill_evidence_reconciliation_gallery.py xic_extractor/diagnostics/backfill_reconciliation_gallery.py tests/test_backfill_evidence_reconciliation_gallery.py
```

Browser smoke should check:

- desktop and mobile horizontal scroll;
- collapsed default;
- representative-cell details;
- filters;
- PNG fallback;
- lightbox keyboard behavior;
- no overlapping text at 200 percent zoom.

## Acceptance Criteria

- All backfill family/seed groups from the input artifacts appear in the group
  TSV and HTML.
- The gallery visibly separates product behavior, evidence authority state, and
  reconciliation class.
- Product-grade support, review-only visual support, dependent context, and
  human visual judgment remain separate in the machine TSV and HTML.
- Similarity and shape metrics are displayed as source evidence components, not
  as a new aggregate score.
- Missing overlay, missing seed provenance, and join gaps are explicit review
  states.
- Details show representative cells only; complete evidence remains linked.
- No product output or source artifact is mutated.
- The HTML remains usable with JavaScript disabled through direct links and
  details elements.

## Open Questions for Review

1. Are the proposed product behavior classes precise enough for current
   `alignment_review.tsv`, `alignment_cells.tsv`, and optional matrix outputs?
2. Are the proposed output schemas sufficient to prevent an implementer from
   collapsing product-grade support and review-only visual support?
3. Which existing artifact should own any missing per-cell shape-similarity
   metric needed for representative-cell selection?
4. Is `feature_family_id + seed_group_id` sufficient, or should a future
   `peak_hypothesis_id` join be required when mode-aware evidence exists?
5. What is the cheapest real artifact set that can smoke-test all
   reconciliation classes without launching RAW-backed overlay generation?
