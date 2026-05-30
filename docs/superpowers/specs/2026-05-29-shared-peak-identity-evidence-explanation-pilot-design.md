# Shared Peak Identity Evidence Explanation Pilot Design

**Date:** 2026-05-29
**Status:** reviewed draft for Slice 0 implementation planning.
**Readiness label:** `diagnostic_only`
**Target outcome:** `vocabulary_validated` — V1 emits raw readiness facts; the V2
spec owns any entry gate. V1 does not compute a gating verdict.
**Structure:** Slice 0 (hand-validate the seven-family vocabulary) -> Slice 1
(blast-radius / overfit), gated by Slice 0 holding.
**Branch:** `codex/shared-peak-identity-evidence`

## Verdict

Build the first shared peak identity evidence checkpoint as an explanation
pilot, not as a production promotion gate.

V1 must explain why current machine labels differ from manual EIC/MS2 review.
It must not change `alignment_matrix.tsv`, selected peak behavior, rescued-cell
behavior, Tier 2 support tokens, workbook schemas, or production candidate
promotion.

V2 may later try to align machine labels with manual `pass` / `suspect` /
`fail`, but only after V1 proves that the evidence vocabulary can represent the
manual reasoning without special-casing individual families.

The selected strategy is:

```text
manual oracle defines semantics;
8RAW / 85RAW diagnostics define blast-radius risk.
```

Manual review decides what "looks like the same peak identity" means. 8RAW and
85RAW outputs check whether that vocabulary overfits the reviewed rows or would
create broad contradictory explanations.

Explaining only the manual seed rows is not sufficient on its own. V1 does not
emit a single gating verdict; it emits raw readiness facts (how many seed rows
were explained, whether the vocabulary needed a family-specific exception,
whether the blast-radius surface was assessed or stale). The V2 spec owns the
entry gate that reads those facts. V1 must never silently unlock V2
label-convergence planning (see "Slice Structure and Readiness Facts").

## Slice Structure and Readiness Facts

### Two slices

V1 runs in two slices so the evidence vocabulary is validated before the full
blast-radius apparatus is built:

- **Slice 0 — vocabulary validation.** Hand-encode the durable oracle for the
  seven seed families, assemble evidence vectors for the seed rows from existing
  artifacts, classify each row, and read the explanations. Slice 0 outputs are
  the oracle, the evidence vectors, the explanations, the run-facts file, and
  the report only. The decision Slice 0 closes: can the required explanation classes
  cover the seed rows without a family-specific exception? If the vocabulary
  cannot, stop and revise it before building anything else.
- **Slice 1 — blast-radius / overfit.** Only if Slice 0's vocabulary holds. Add
  the blast-radius manifest and summary over seed vs non-seed and available
  8RAW / 85RAW rows. The decision Slice 1 closes: does the vocabulary
  generalize, or does it overfit the seven seed families?

### Row status vs run-level facts

These are two distinct scopes; do not mix the vocabularies:

- **Per-row `explanation_status`** describes one reviewed cell:
  `explained`, `partially_explained`, `unexplained`, `inconclusive`.
- **Run-level readiness facts** describe the whole run and are raw inputs to the
  V2 gate, not a verdict. V1 does not compute `explanation_ready` /
  `partial_readiness` / `inconclusive_readiness`; the V2 spec defines its own
  gate from these facts. The facts live in `shared_peak_identity_run_facts.tsv`
  (machine-readable) and are echoed in the report.

Required run-level readiness facts:

```text
seed_rows_total
seed_rows_explained
seed_rows_unexplained
seed_rows_inconclusive
vocabulary_special_casing_detected
blast_radius_assessed
blast_radius_stale_artifact_count
max_overfit_risk
```

`vocabulary_special_casing_detected=TRUE` is a Slice 0 stop condition.
`blast_radius_assessed` uses the `blast_radius_assessment_status` vocabulary
defined in the enum table; in Slice 0 it is `not_run_slice0`. Stale or
hash-mismatched
machine artifacts are counted in `blast_radius_stale_artifact_count` and
annotated, but they do not force a verdict — V1 has no verdict to force.

## Roadmap Placement

This phase advances `EvidenceVector` and `AuditTrail` semantics. It may inform a
future multi-source `PeakHypothesis` contract, but V1 does not introduce a new
shared concrete peak model.

It does not advance production `Trace` / `TraceGroup`, `IntegrationResult`,
model selection, baseline / AsLS cleanup, or final matrix filtering.

## Decision This Phase Can Close

V1 can close this decision:

> Can one shared evidence vocabulary explain the gap between current machine
> decisions and the user's manual EIC/MS2 judgments across normal selected
> peaks, rescued cells, and Tier 2 diagnostic candidates?

V1 cannot close:

- whether provisional rows should enter the production matrix;
- whether any Tier 2 evidence producer is production-ready;
- whether selected peak scoring should change;
- whether CWT, MS2 pattern similarity, or DDA opportunity should become hard
  gates;
- whether 85RAW is acceptable for production behavior.

## Current Context

Recent work created a `diagnostic_only` Tier 2 RAW trace re-read sidecar and a
candidate gate consumer. The current v0/v0.1 findings show observability, not
product promotion readiness. The machine side still lacks a shared language for
several facts the user used during manual review:

- a coherent RT neighborhood where only one plausible peak exists;
- complete peak shape even when intensity is low;
- similar MS2 / NL / product-ion pattern;
- missing DDA evidence caused by low intensity or stochastic precursor
  selection, not analyte absence;
- boundary agreement under several possible references;
- RT drift or matrix-local behavior that should demote confidence rather than
  veto identity by itself;
- cases where shape is normal but RT and pattern contradict the candidate.

The root concern is broader than backfill: normal selected peaks and rescued
cells should speak the same evidence language. If they do not, improving Tier 2
criteria alone will only polish one diagnostic sidecar while leaving the main
evidence chain under-specified.

## Manual Oracle Seed Cases

V1 starts from the user's current manual judgments. These rows are a calibration
oracle, not product training data and not a production allowlist. The durable
oracle source belongs under:

```text
docs/superpowers/fixtures/shared_peak_identity_manual_oracle_v1.tsv
```

Generated copies may be written under `output/`, but the semantic oracle that
can unlock V2 must be tracked, versioned, and hashable. It must include schema
version, review scope, label source, confidence, reviewed evidence surfaces, and
source date. A cleanable `output/` file alone cannot be the canonical oracle.

| Family | Manual judgment seed | Important reasoning |
| --- | --- | --- |
| `FAM000144` | `NormalBC2312_DNA` and `BenignfatBC1151_DNA` should be rescued; other cells should not. A possible `TumorBC2312_DNA` candidate is not acceptable. | Accepted cells have the only plausible peak in the RT region, complete shape, and similar pattern. The rejected extra candidate has too much RT difference and pattern mismatch even though shape is normal. Low intensity / DDA stochasticity can explain missing fragmentation for accepted cells. TumorBC2312 manual review additionally used the nearest / nearby-injection QC MS1 pattern as a drift-context reference, so V2 should treat injection-local QC pattern similarity as RT-drift support context when such provenance is available. |
| `FAM000610` | All reviewed cells should be rescued. | RT is close, shape is acceptable, and pattern is similar. |
| `FAM001227` | `QC5`, `NormalBC2263_DNA`, and `TumorBC2312_DNA` are OK; `NormalBC2312_DNA` and `TumorBC2263_DNA` are suspect; unmentioned cells are fail. | The evidence chain needs `pass` versus `suspect`, not only binary rescue. |
| `FAM001227` / `FAM001239` | Delta-mass-like relationship is important context for a later untargeted method. | They appear to have very similar shape and pattern with m/z difference around 1. This should be recorded as context, not used as the main V1 decision rule. |
| `FAM001589` | Human review is unable to decide. | Overall peak shape is too poor. This must be represented as `human_unjudgeable`, not forced into pass or fail. |
| `FAM001658` | `BenignfatBC1151_DNA`, `QC3`, `QC5`, and `NormalBC2312_DNA` are supported but low-intensity. | Shape, RT, and pattern support the identity; intensity is too low and should be treated as opportunity / confidence context. |
| `FAM002175` | All reviewed cells pass. | V1 should explain this as coherent multi-cell support, not a special-case family. |

The first oracle TSV must encode "unmentioned cells are fail" for families where
the user explicitly said that rule applies. It must not infer labels for samples
that were not part of the reviewed set unless the oracle records the scope.

Required manual label vocabulary:

| Field | Allowed values |
| --- | --- |
| `manual_label` | `pass`, `suspect`, `fail`, `human_unjudgeable`, `not_applicable` |
| `manual_label_source` | `direct_eic_ms2_review`, `direct_eic_only_review`, `scope_rule_unmentioned_fail`, `family_all_reviewed_rule`, `derived_from_related_family_context` |
| `manual_confidence` | `high`, `medium`, `low`, `unjudgeable`, `not_applicable` |
| `manual_scope` | `reviewed_cell`, `reviewed_family_all_cells`, `reviewed_family_named_cells_only`, `scope_derived_unmentioned_fail`, `family_level_context` |

Required evidence-surface flags:

```text
reviewed_eic
reviewed_ms2_pattern
reviewed_nl_or_product_pattern
reviewed_intensity_opportunity
dda_opportunity_basis
manual_scope_rule_id
manual_review_source
manual_reviewed_at
```

The initial mapping must distinguish direct review labels from scope-derived
fail labels. A `fail` because the user explicitly reviewed RT/pattern mismatch
is not the same evidence as a `fail` because the sample was unmentioned under a
declared family-scope rule.

## Design Principle

V1 is `facts before verdict`.

The machine should first learn to say:

- which manual evidence facts are present;
- which are missing;
- which existing blocker is a true contradiction;
- which blocker is only missing opportunity or unavailable evidence;
- which source produced each fact.

Only V2 should translate these facts into new machine labels.

## Evidence Vocabulary

V1 uses a shared row/cell-level evidence vector. It is intentionally descriptive,
not a score.

Required evidence groups:

| Group | Example fields | V1 posture |
| --- | --- | --- |
| Identity / provenance | `feature_family_id`, `sample_id`, `source_role`, `evidence_source`, `source_artifact`, `source_row_id` | Required. Every fact must have origin. |
| Manual oracle | `manual_label`, `manual_reason_tags`, `manual_scope`, `manual_review_note` | Required for reviewed rows. |
| Current machine decision | `machine_current_label`, `source_role` (machine origin), `machine_blockers`, `machine_reason` | Required when available. The evidence vector stores the machine origin as `source_role`; the explanations file projects it as `machine_source_role`. |
| RT context | `candidate_apex_rt`, `family_reference_rt`, `seed_delta_sec`, `family_consensus_delta_sec`, `matrix_local_delta_sec`, `rt_context_status` | Context, not single hard veto. |
| Shape context | `shape_status`, `apex_clarity_status`, `single_peak_region_status`, `peak_completeness_status`, `shape_blocker` | Descriptive; thresholds are not product gates in V1. |
| Boundary context | `seed_rescued_boundary_overlap`, `rescued_pairwise_boundary_overlap_min`, `family_consensus_boundary_overlap`, `boundary_reference_status` | Multiple references retained. |
| Pattern context | `pattern_similarity_status`, `matched_product_count`, `matched_neutral_loss_count`, `pattern_conflict_status`, `delta_mass_context` | Descriptive; no direct promotion. |
| Opportunity / intensity | `intensity_status`, `dda_opportunity_status`, `fragmentation_observation_status`, `scan_availability_status` | Missing MS2 defaults to `not_observed`, not negative. |
| Explanation | `evidence_gap_class`, `explanation_status`, `smallest_missing_fact`, `recommended_next_action` | Required output. |

All fields that can be unavailable must distinguish:

- `not_observed`;
- `not_assessed`;
- `not_applicable`;
- `unavailable`;
- `conflicting`;
- `present`.

Blank numeric fields must not be interpreted as zero support.

The spec carries four availability vocabularies on purpose; they operate at
different scopes and are not duplicates:

- the six field-level statuses above describe one field in one row;
- `metric_availability_status` summarizes per evidence-vector row whether the
  metric fields are complete (it has its own vocabulary, not the six field
  statuses), and the blast-radius summary's `unavailable_field_count` aggregates
  rows whose `metric_availability_status` is not `complete`;
- `artifact_status` describes one source artifact in the manifest;
- `blast_radius_assessed` (run-level) describes whether the blast-radius surface
  was assessed for the whole run.

`stale_hash_mismatch` appears in more than one because staleness can be detected
at row, artifact, and run scope; the carrying column names the scope.

The V1 model name should be distinct from the existing
`xic_extractor.peak_detection.hypotheses.EvidenceVector`. Use a new V1 contract
name such as `PeakIdentityEvidenceVector` and keep it in a small alignment
diagnostic package, for example:

```text
xic_extractor/alignment/shared_peak_identity_explanation/
```

Do not extend the existing peak-hypothesis `EvidenceVector` or `AuditTrail`
with manual oracle, alignment-cell, Tier 2 sidecar, or explanation-policy
fields. This spec advances those semantics; it does not make the existing
targeted peak-hypothesis model the shared concrete container.

## Explanation Classes

V1 should classify each reviewed cell into one main explanation class plus
optional secondary tags.

Required classes:

| Class | Meaning |
| --- | --- |
| `machine_agrees_with_manual` | Current machine state is consistent with manual judgment. |
| `machine_too_conservative_low_opportunity` | Manual accepts or suspects the cell, but machine lacks MS2 / scan / intensity evidence that should be treated as low opportunity rather than absence. |
| `machine_too_conservative_shape_or_pattern_unmodeled` | Manual uses shape or pattern similarity that machine does not yet represent. |
| `machine_too_permissive_rt_pattern_conflict` | Machine accepts or rescues a cell that manual rejects because RT and pattern conflict, even if shape is normal. |
| `machine_too_permissive_scope_rule_conflict` | Machine accepts or rescues a cell that manual rejects only through a named reviewed-set scope rule such as "unmentioned cells are fail"; this is a machine/manual disagreement, not machine agreement. |
| `boundary_reference_ambiguous` | Existing blocker depends on which boundary reference is treated as authority. |
| `rt_drift_policy_gap` | RT difference exists, but V1 cannot decide whether it is drift, matrix behavior, or true mismatch. |
| `human_unjudgeable_shape_bad` | Manual review cannot decide because the trace itself is poor. Applies only to reviewed-cell rows; a `family_level_context` row with `manual_label=not_applicable` is classified as `delta_mass_related_context_only`, not here. |
| `delta_mass_related_context_only` | A related family / delta-mass pattern may help later, but V1 must not use it as a direct pass/fail rule. |
| `unexplained_machine_manual_gap` | Available facts cannot explain the disagreement. This is a V1 failure mode that must be counted. |

## Architecture

Use a sidecar-style explanation pipeline:

```text
manual oracle TSV
        +
current selected / rescued / Tier 2 diagnostic artifacts
        +
optional existing 8RAW / 85RAW identity diagnostic summaries
        |
        v
shared evidence-vector assembler
        |
        v
manual-vs-machine explanation classifier
        |
        v
Slice 0: evidence-vector TSV + explanations TSV + run-facts TSV + report
        |
        v
Slice 1 (only if Slice 0 vocabulary holds): blast-radius manifest + summary
```

The assembler owns normalization and provenance. The classifier owns
explanation mapping. Writers render facts only; they must not recompute peak
evidence or scan RAW files.

V1 should prefer existing artifacts. It should not launch a new 85RAW run unless
a reviewed plan names the decision the run can close, expected runtime,
preflight, and stop condition.

## Implementation Contract

V1 should introduce a diagnostic CLI:

```text
tools/diagnostics/shared_peak_identity_explanation.py
```

Reusable parsing, models, assembler, classifier, and writers should live under
a focused package such as:

```text
xic_extractor/alignment/shared_peak_identity_explanation/
```

The default CLI path must parse, validate, orchestrate, and write existing
artifact evidence only. Assemblers and writers must not scan RAW files or
recompute domain evidence. RAW access is allowed only inside an explicitly
opted-in diagnostic producer such as `--candidate-ms2-pattern-batch-index` plus
`--candidate-ms2-pattern-raw-dll-dir`, and that producer must reuse the existing
RAW reader / MS2-NL helper instead of adding a new interpretation model. If the
implementation creates or changes this CLI, the same diff must update
`tools/diagnostics/INDEX.md` with purpose, topic group, originating spec, and
outputs.

Primary join key:

```text
feature_family_id + sample_id + oracle_row_id
```

Machine artifacts may not have `oracle_row_id`, so assembler joins use
`feature_family_id + sample_id` first and preserve all candidate/source matches.
If more than one machine row matches an oracle row, the explanation row must set
`machine_match_status=ambiguous_multiple_matches` and list the matched
`matched_source_row_ids` values rather than silently choosing one. Evidence
vectors are allowed to have multiple rows per oracle row: one row per relevant
source match or source context. The explanations TSV aggregates those source
rows back to one explanation row per `oracle_row_id`.

The oracle uses `sample_id`, but most existing machine artifacts (selected,
rescued, backfill, and cell artifacts) key samples as `sample_stem`; only the
newer `identity_coherence` module already uses `sample_id`. The assembler owns
the `sample_stem` <-> `sample_id` normalization and must record the mapping
basis in provenance. If a sample cannot be reconciled across the two naming
schemes, the explanation row sets `machine_match_status=missing_required_key`
rather than guessing.

### Oracle Row Grain

`oracle_row_id` is the primary join key, so its granularity is fixed:

- **Directly reviewed cell:** one row per (`feature_family_id`, `sample_id`).
  `manual_scope` is `reviewed_cell`, `reviewed_family_named_cells_only`, or
  `reviewed_family_all_cells` when the review covered every cell of the family
  (for example `FAM000610` and `FAM002175`, "all reviewed cells"). A family
  whose cells carry different labels (for example `FAM001227`, where some cells
  are `pass`, some `suspect`) produces one row per named cell, each with its own
  `manual_label`.
- **Scope-rule rows:** "unmentioned cells are fail" is encoded as one row per
  named unmentioned sample when the sample set is known, or as a single
  family-scope rule row with `sample_id=__scope_rule__` when the unmentioned set
  is open-ended. `manual_scope=scope_derived_unmentioned_fail`,
  `manual_label_source=scope_rule_unmentioned_fail`.
- **Cross-family context rows:** the `FAM001227` / `FAM001239` delta-mass
  relationship is recorded once, keyed to the lower-id family
  (`feature_family_id=FAM001227`), with `related_family_id=FAM001239`,
  `sample_id=__family_context__`, `manual_scope=family_level_context`,
  `manual_label_source=derived_from_related_family_context`, and
  `delta_mass_context=related_family_context_only`. It carries no decision
  label; `manual_label=not_applicable` signals "context only, not a pass/fail
  rule".

Reserved `sample_id` sentinels (`__scope_rule__`, `__family_context__`) never
join to a machine `sample_stem`; the assembler leaves their machine columns
`not_applicable` (`machine_match_status=not_applicable`,
`machine_source_role=not_applicable`).

The `oracle_row_id` value is constructed as `<feature_family_id>|<sample_id>`
(so `FAM001227|QC5`, `FAM001227|__scope_rule__`, `FAM001227|__family_context__`);
it is stable and unique within a durable oracle version because the grain rules
above guarantee one row per (`feature_family_id`, `sample_id`).

Sorting is deterministic:

```text
feature_family_id, sample_id, oracle_row_id, evidence_source, source_row_id
```

Null policy:

- empty numeric field means `metric_unavailable`;
- empty enum field is invalid unless the column is explicitly optional;
- `not_observed`, `not_assessed`, `not_applicable`, and `unavailable` are
  distinct statuses;
- non-cell oracle rows use the reserved `sample_id` sentinels `__scope_rule__`
  and `__family_context__`, which never join to a machine `sample_stem`;
- boolean fields are serialized as `TRUE` / `FALSE`.

### Allowed Status / Enum Values

All controlled enum tokens are lower snake case. Semicolon-separated token
lists use `;` with no embedded whitespace. Free-text is allowed only in
`manual_review_note` and `notes`.

| Field | Allowed values or type |
| --- | --- |
| `evidence_source` | `manual_oracle`, `alignment_review`, `alignment_cells`, `candidate_gate_sidecar`, `tier2_trace_sidecar`, `identity_coherence_sidecar`, `targeted_benchmark_context`, `blast_radius_manifest` |
| `source_role` | `manual_oracle`, `selected_peak`, `rescued_cell`, `candidate_gate_family_context`, `tier2_raw_reread`, `identity_coherence_diagnostic`, `targeted_context`, `blast_radius_context` |
| `machine_current_label` | `source_passthrough_token`, `not_available` when no machine source exists, or `not_applicable` on sentinel oracle rows |
| `machine_source_role` | same tokens as `source_role` excluding `manual_oracle`; `not_available` when no machine source matched; `not_applicable` on sentinel oracle rows |
| `machine_match_status` | `no_match`, `single_match`, `ambiguous_multiple_matches`, `missing_required_key`, `not_applicable` |
| `rt_context_status` | `supportive`, `conflicting`, `drift_possible`, `ambiguous`, `not_assessed`, `unavailable` |
| `shape_status` | `complete`, `acceptable`, `distorted`, `low_intensity_but_coherent`, `noisy_unjudgeable`, `not_assessed`, `unavailable`, `ambiguous` |
| `apex_clarity_status` | `clear`, `weak`, `ambiguous`, `not_assessed`, `unavailable` |
| `single_peak_region_status` | `single_plausible_peak`, `multiple_plausible_peaks`, `flat_or_noisy_region`, `not_assessed`, `unavailable` |
| `peak_completeness_status` | `complete`, `clipped`, `partial`, `not_assessed`, `unavailable`, `ambiguous` |
| `boundary_reference_status` | `seed_consistent`, `rescued_pairwise_consistent`, `family_consensus_consistent`, `reference_disagreement`, `not_assessed`, `unavailable` |
| `pattern_similarity_status` | `similar`, `partial_similar`, `mismatch`, `not_observed`, `not_assessed`, `unavailable`, `ambiguous` |
| `pattern_conflict_status` | `none`, `rt_pattern_conflict`, `pattern_only_conflict`, `not_assessed`, `unavailable` |
| `delta_mass_context` | `none`, `related_family_context_only`, `not_assessed`, `unavailable` |
| `intensity_status` | `sufficient`, `low_but_visible`, `too_low_to_assess`, `not_assessed`, `unavailable` |
| `dda_opportunity_status` | `observed`, `low_intensity_stochastic_not_observed`, `expected_but_missing`, `not_assessed`, `not_applicable`, `unavailable` |
| `fragmentation_observation_status` | `observed`, `not_observed`, `conflicting`, `not_assessed`, `unavailable` |
| `scan_availability_status` | `sufficient`, `low`, `not_assessed`, `unavailable` |
| `metric_availability_status` | `complete`, `partial`, `schema_missing`, `artifact_missing`, `stale_hash_mismatch`, `not_assessed` |
| `blast_radius_assessment_status` (values for the `blast_radius_assessed` run-fact column) | `present_current`, `8raw_not_assessed`, `85raw_not_assessed`, `stale_hash_mismatch`, `manifest_missing`, `not_run_slice0`, `not_assessed` |
| `scope` (blast-radius summary) | `seed`, `non_seed_same_family`, `all_available_8raw`, `all_available_85raw`, `overall` |
| `slice` | `slice0`, `slice1` |
| `max_overfit_risk` (run fact) | same value set as `overfit_risk` (`none`, `low`, `medium`, `high`, `unassessed`); the maximum severity over the Slice 1 summary rows, `unassessed` in Slice 0 |
| `vocabulary_special_casing_detected`, `generated_from_existing_artifact` | boolean `TRUE` / `FALSE` |
| `evidence_gap_class` | values from the Required classes table |
| `secondary_gap_tags` | `semicolon_token_list`; tokens must come from the `manual_reason_tags` list below (the primary class is already in `evidence_gap_class`) |
| `explanation_status` | `explained`, `partially_explained`, `unexplained`, `inconclusive` |
| `recommended_next_action` | `no_action`, `inspect_manual_eic`, `inspect_ms2_pattern`, `add_shape_metric`, `add_pattern_metric`, `add_opportunity_metric`, `check_boundary_reference`, `check_blast_radius`, `flag_for_v2_gate_review` |
| `artifact_role` | `manual_oracle_fixture`, `alignment_review`, `alignment_cells`, `tier2_trace_sidecar`, `identity_diagnostic`, `targeted_context`, `blast_radius_context` |
| `artifact_status` | `present_current`, `present_hash_unpinned`, `present_stale_hash_mismatch`, `present_missing_required_fields`, `missing`, `schema_unsupported`, `not_assessed`, `unavailable` |
| `freshness_basis` | `slice0_evidence_vector`, `expected_blast_radius_manifest`, `not_available` |
| `matched_source_row_ids` | `semicolon_source_row_id_list`; dynamic provenance IDs, not controlled enum tokens. Validate no blanks, no embedded whitespace, and that each ID is traceable to an emitted evidence/source row. |
| `manual_reason_tags`, `machine_blockers`, `source_roles_seen`, `source_artifacts`, `available_required_fields`, `missing_required_fields` | `semicolon_token_list` |

### Source / Artifact Vocabulary Crosswalk

`evidence_source`, `source_role`, and `artifact_role` are three axes, not
duplicates: `artifact_role` is the file class in the manifest, `evidence_source`
is which artifact a row came from, and `source_role` is the row's semantic
origin. The intentional spelling differences align as:

| Artifact | `artifact_role` | `evidence_source` | `source_role` |
| --- | --- | --- | --- |
| manual oracle fixture | `manual_oracle_fixture` | `manual_oracle` | `manual_oracle` |
| alignment review | `alignment_review` | `alignment_review` | `selected_peak` |
| alignment cells | `alignment_cells` | `alignment_cells` | `rescued_cell` |
| candidate gate sidecar | `identity_diagnostic` | `candidate_gate_sidecar` | `candidate_gate_family_context` |
| Tier 2 RAW re-read sidecar | `tier2_trace_sidecar` | `tier2_trace_sidecar` | `tier2_raw_reread` |
| identity coherence sidecar | `identity_diagnostic` | `identity_coherence_sidecar` | `identity_coherence_diagnostic` |
| targeted benchmark | `targeted_context` | `targeted_benchmark_context` | `targeted_context` |
| blast-radius manifest | `blast_radius_context` | `blast_radius_manifest` | `blast_radius_context` |

Initial `manual_reason_tags` tokens:

```text
rt_close
rt_too_far
rt_drift_possible
single_plausible_peak
shape_complete
shape_normal
shape_bad
pattern_similar
pattern_partial
pattern_mismatch
low_intensity
dda_stochastic_missing
boundary_consistent
boundary_ambiguous
delta_mass_related
scope_derived_unmentioned_fail
human_unjudgeable
```

### Output Schemas

Canonical manual oracle (Slice 0 durable fixture):

```text
docs/superpowers/fixtures/shared_peak_identity_manual_oracle_v1.tsv
```

Required columns:

```text
oracle_schema_version
oracle_row_id
feature_family_id
sample_id
manual_label
manual_label_source
manual_confidence
manual_scope
manual_scope_rule_id
manual_reason_tags
reviewed_eic
reviewed_ms2_pattern
reviewed_nl_or_product_pattern
reviewed_intensity_opportunity
dda_opportunity_basis
related_family_id
manual_review_note
manual_review_source
manual_reviewed_at
```

Evidence vectors (Slice 0):

```text
shared_peak_identity_evidence_vectors.tsv
```

Required columns:

```text
evidence_schema_version
evidence_record_id
oracle_row_id
feature_family_id
sample_id
evidence_source
source_role
source_artifact
source_artifact_sha256
source_row_id
machine_current_label
machine_reason
machine_blockers
candidate_apex_rt
family_reference_rt
seed_delta_sec
family_consensus_delta_sec
matrix_local_delta_sec
rt_context_status
shape_status
apex_clarity_status
single_peak_region_status
peak_completeness_status
boundary_reference_status
seed_rescued_boundary_overlap
rescued_pairwise_boundary_overlap_min
family_consensus_boundary_overlap
pattern_similarity_status
matched_product_count
matched_neutral_loss_count
pattern_conflict_status
delta_mass_context
intensity_status
dda_opportunity_status
fragmentation_observation_status
scan_availability_status
metric_availability_status
```

Explanations (Slice 0):

```text
shared_peak_identity_explanations.tsv
```

Required columns:

```text
explanation_schema_version
oracle_row_id
feature_family_id
sample_id
manual_label
manual_label_source
manual_confidence
manual_scope
manual_reason_tags
machine_current_label
machine_reason
machine_match_status
matched_source_row_ids
machine_source_role
machine_blockers
evidence_gap_class
secondary_gap_tags
explanation_status
smallest_missing_fact
recommended_next_action
source_roles_seen
source_artifacts
```

Run facts (single row, Slice 0 and Slice 1):

```text
shared_peak_identity_run_facts.tsv
```

Required columns:

```text
run_facts_schema_version
slice
seed_rows_total
seed_rows_explained
seed_rows_unexplained
seed_rows_inconclusive
vocabulary_special_casing_detected
blast_radius_assessed
blast_radius_stale_artifact_count
max_overfit_risk
durable_oracle_path
durable_oracle_sha256
```

This file is the durable, machine-readable home for the run-level readiness
facts and the durable oracle hash. In Slice 0, `slice=slice0`,
`blast_radius_assessed=not_run_slice0`, and `max_overfit_risk=unassessed`.

Blast-radius manifest (Slice 1):

```text
shared_peak_identity_blast_radius_manifest.tsv
```

Required columns:

```text
manifest_schema_version
artifact_id
artifact_role
artifact_path
artifact_sha256
expected_artifact_sha256
freshness_basis
artifact_schema_version
artifact_status
row_count
sample_count
family_count
available_required_fields
missing_required_fields
generated_from_existing_artifact
notes
```

Blast-radius summary (Slice 1):

```text
shared_peak_identity_blast_radius_summary.tsv
```

Required columns:

```text
summary_schema_version
scope
artifact_id
evidence_gap_class
seed_count
context_row_count
non_seed_same_family_count
assessed_row_count
all_available_row_count
compatible_row_count
unavailable_field_count
contradictory_count
ambiguous_machine_match_count
compatible_fraction
contradictory_fraction
ambiguous_fraction
unavailable_fraction
overfit_risk
example_oracle_row_ids
example_feature_family_ids
```

Allowed `overfit_risk` values:

```text
none
low
medium
high
unassessed
```

Slice 1 row-grain rules:

- `seed_count` counts only sample-level Slice 0 explanation rows whose
  `manual_label` is not `not_applicable` and whose `sample_id` is not a reserved
  sentinel.
- `context_row_count` counts sentinel/context rows such as
  `sample_id=__family_context__`. These rows may appear in the report as future
  context, but they never join to `sample_stem` and never participate in
  `non_seed_same_family_count`, `all_available_row_count`, `compatible_row_count`,
  `contradictory_count`, `ambiguous_machine_match_count`, or risk denominators.
- `all_available_row_count` is the machine-row denominator for the current
  `scope` whose required fields are available for the class profile.
- `compatible_row_count` is the subset of `all_available_row_count` whose
  machine-side profile is compatible with the class.
- `contradictory_count` is machine-side contradiction only; it is not a
  non-seed manual truth label.

Deterministic `overfit_risk` interpretation:

| Risk | Required condition |
| --- | --- |
| `none` | Context-only class or no sample-level seed rows for the class. |
| `unassessed` | Required 8RAW / 85RAW surface is missing, unpinned, stale, or lacks fields needed to build a denominator. |
| `high` | `seed_count > 0`, denominator is sufficient (`assessed_row_count >= max(50, 5 * seed_count)`), `compatible_row_count=0`, `unavailable_fraction < 0.20`, and `ambiguous_fraction < 0.20`; or `contradictory_fraction >= 0.50`. |
| `medium` | Denominator exists but is weak or noisy: insufficient denominator, `0 < compatible_fraction < 0.01`, `0.10 <= contradictory_fraction < 0.50`, `ambiguous_fraction >= 0.20`, or `unavailable_fraction >= 0.20`. |
| `low` | Both 8RAW and 85RAW required surfaces are current, denominator is sufficient, `compatible_fraction >= 0.01`, `contradictory_fraction < 0.10`, `ambiguous_fraction < 0.20`, and `unavailable_fraction < 0.20`. |

The thresholds are diagnostic guardrails, not scientific proof of semantic truth.
They exist so the Slice 1 report can change the next action instead of emitting
uninterpretable counts.

The Markdown report is human-facing and must summarize these TSVs. It must not
be the only place where counts, hashes, or status values exist.

## Artifact Contract

Planned V1 outputs:

```text
output/shared_peak_identity_evidence_explanation/
  shared_peak_identity_manual_oracle.tsv
  shared_peak_identity_evidence_vectors.tsv
  shared_peak_identity_explanations.tsv
  shared_peak_identity_run_facts.tsv
  shared_peak_identity_blast_radius_manifest.tsv      # Slice 1 only
  shared_peak_identity_blast_radius_summary.tsv       # Slice 1 only
  shared_peak_identity_explanation_report.md
```

The output manual oracle is a generated copy of the durable fixture. It must
record the durable fixture path and SHA256 in the report or manifest. The
generated copy is intentionally named without the `_v1` suffix
(`shared_peak_identity_manual_oracle.tsv`); the durable fixture keeps it
(`docs/superpowers/fixtures/shared_peak_identity_manual_oracle_v1.tsv`). Do not
rename the generated copy to match the fixture.

Minimum `shared_peak_identity_explanations.tsv` columns. This is a strict subset
of the Output Schemas "Required columns" for this file; that block is the source
of truth and this list only names fields that must never be dropped:

```text
oracle_row_id
feature_family_id
sample_id
manual_label
manual_reason_tags
manual_scope
machine_current_label
machine_match_status
matched_source_row_ids
machine_source_role
machine_blockers
evidence_gap_class
explanation_status
smallest_missing_fact
recommended_next_action
source_roles_seen
source_artifacts
```

`oracle_row_id` is the primary join key and `machine_match_status` carries the
`ambiguous_multiple_matches` warning. `matched_source_row_ids` carries the
auditable source rows behind that status, so none of these fields may be
omitted even from the minimum output.

Minimum Slice 0 report sections:

- compact decision summary at the top: `diagnostic_only`, Slice 0 facts,
  whether the vocabulary held or which raw fact blocked it, top blocking
  rows/classes, and explicit next action. This is a human summary of the facts,
  not a V1 gating verdict and not a production-readiness claim;
- run-level readiness facts echoed from `shared_peak_identity_run_facts.tsv`
  (`seed_rows_explained` vs `seed_rows_total`,
  `vocabulary_special_casing_detected`, `blast_radius_assessed`,
  `max_overfit_risk`); V1 states facts, not a gating verdict;
- manual rows covered and uncovered;
- disagreements by explanation class;
- examples where machine is too conservative;
- examples where machine is too permissive;
- V2 candidates and explicit non-goals.

Additional Slice 1 report sections:

- blast-radius summary from the pinned 8RAW / 85RAW manifest, including
  explicit `not_assessed` or `unavailable` statuses;
- blast-radius manifest status, including any missing or stale artifact.

## 8RAW / 85RAW Blast-Radius Role

8RAW / 85RAW diagnostics are not the semantic oracle in V1. They answer:

- does a proposed evidence class appear only in the manual seed rows, or across
  many rows;
- would the class create many `machine_too_conservative` or
  `machine_too_permissive` cases;
- does missing evidence dominate because the artifact lacks fields, not because
  the chemistry is ambiguous;
- does the explanation vocabulary collapse too many unrelated cases into one
  bucket.

An existing read-only tool,
`tools/diagnostics/analyze_matrix_identity_blast_radius.py`, already reports
blast radius for proposed matrix-identity decisions. It answers a different
question (impact of identity decisions on the primary matrix), so V1 neither
replaces it nor reuses its output schema. V1 may, however, reuse its
review/cell parsing helpers instead of re-implementing artifact loading. The
new `shared_peak_identity_blast_radius_*` outputs measure evidence-class overfit
across seed vs non-seed rows, not matrix promotion impact.

V1 acceptance must use a pinned blast-radius manifest. The manifest must cover:

- manual seed oracle rows;
- non-seed same-family rows available in current machine artifacts;
- all available 8RAW review/cell rows relevant to the current diagnostic
  surface;
- all available 85RAW review/cell rows relevant to the current diagnostic
  surface.

If 85RAW artifacts are unavailable or lack the fields required for the
blast-radius summary, V1 sets `blast_radius_assessed=85raw_not_assessed` in
`shared_peak_identity_run_facts.tsv` and records it in the report; this is a raw
fact for the V2 gate, not a verdict V1 computes.

Freshness must have an explicit comparison authority:

- for artifacts already referenced by Slice 0 evidence vectors,
  `expected_artifact_sha256` comes from the matching `source_artifact` /
  `source_artifact_sha256` pair in
  `shared_peak_identity_evidence_vectors.tsv`;
- for 85RAW artifacts or optional sidecars that were not referenced by Slice 0,
  `expected_artifact_sha256` must come from a role-bearing expected manifest
  supplied to the Slice 1 command;
- if no expected hash exists, the artifact may be counted for coverage but its
  `artifact_status` is `present_hash_unpinned`, the run cannot set
  `blast_radius_assessed=present_current`, and the report must name the missing
  freshness evidence.

The expected blast-radius manifest is only a freshness / stale-artifact guard.
It must not be interpreted as proof that the evidence chain is complete,
linear, or scientifically validated. If the only available 85RAW artifacts come
from an older evidence-chain shape, V2 may still run in `exploratory_only` mode
to expose the gap, but it must not treat that freshness check as a semantic
generalization gate.

`blast_radius_assessed` is `present_current` only when both the 8RAW and 85RAW
surfaces were assessed, required fields were available, and every required
manifest artifact had an expected hash that matched the observed hash. If a
manifested machine artifact is stale or hash-mismatched, V1 increments
`blast_radius_stale_artifact_count`, annotates the artifact in the manifest
(`artifact_status=present_stale_hash_mismatch`), and warns; it does not stop or
emit a production verdict. The durable oracle's `durable_oracle_sha256` is still
recorded so the V2 gate can verify the oracle the run was computed against.

Slice 1 exit interpretation:

- `max_overfit_risk=high`: kill or revise the explanation vocabulary before any
  V2 shadow-label-alignment planning.
- `max_overfit_risk=medium`, `blast_radius_assessed` not equal to
  `present_current`, any stale required artifact, or missing-field dominance:
  externalize the missing evidence and do not begin V2 gate work from this run.
- `max_overfit_risk=low` with `blast_radius_assessed=present_current`,
  `blast_radius_stale_artifact_count=0`, and sentinel/context rows excluded from
  sample-level counts: V2 may evaluate shadow label alignment. This still does
  not imply `production_candidate` or `production_ready`.

New expensive validation is out of scope unless a follow-up plan passes the
repo RAW preflight rules.

## Context7 / Package Semantics

This design incorporates Task 0 package-semantics findings from:

```text
docs/superpowers/notes/2026-05-29-shared-peak-identity-context7-package-audit.md
```

V1 consequences:

- CWT stays `audit_only observer`. Existing CWT fields are not calibrated CWT
  ridge evidence and must not drive V1 labels.
- `scipy.signal.find_peaks_cwt`, `find_peaks`, `peak_widths`, and
  `savgol_filter` semantics are package-sensitive. If V1 implements new shape
  or boundary metrics using these APIs, the exact parameter defaults must be
  recorded in the artifact provenance.
- NumPy missing-value and finite-value semantics must be explicit. Do not let
  `NaN` silently become a score.
- If V1 adds new correlation, area, apex tie, or pattern-similarity math, run a
  narrower official-doc check for the exact API before implementation.
- Manual oracle loaders must use explicit sheet names if workbook input is
  introduced. `openpyxl(data_only=True)` cached formula behavior must not become
  hidden truth.

## Literature Support And Evidence Boundaries

V2 evidence changes must be literature-backed and must name whether a fact is
machine-observed, a machine proxy, manual-oracle-derived, or unavailable. The
current seed-run evidence vectors still project several shape / pattern /
opportunity facts from the manual oracle. That is acceptable for explaining the
manual vocabulary, but it is not enough for a machine-only pass/fail labeler.

Primary support used for the next machine-evidence slice:

- **Peak shape / XIC quality:** centWave uses regions of interest plus CWT and
  chromatographic-domain fitting for high-resolution LC/MS feature detection
  ([Tautenhahn 2008](https://pubmed.ncbi.nlm.nih.gov/19040729/)). Zhang and
  Zhao evaluated LC/MS EIC and peak quality metrics including sharpness,
  Gaussian similarity, SNR, peak significance, triangle area similarity, and
  zigzag indices, and concluded combined metrics outperform single metrics
  ([Zhang 2014](https://pubmed.ncbi.nlm.nih.gov/25350128/)). A later
  manually-calibrated peak-picking study again treats peak quality as an
  explicit metric problem rather than a visual-only label
  ([Kumler 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10612323/)).
- **MS2 / neutral-loss pattern:** product ions and neutral losses are valid
  annotation evidence for substructure or family-level context, while full
  spectrum similarity remains a stronger but still non-absolute structural
  relatedness proxy. GNPS molecular networking uses cosine-style spectral
  similarity
  ([Watrous 2012](https://pmc.ncbi.nlm.nih.gov/articles/PMC4379709/)), Spec2Vec
  explicitly warns that cosine-like similarity is imperfect
  ([Huber 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC7909622/)), and
  modified-cosine / neutral-loss alignment behavior depends on molecule class
  and modification context
  ([Biesinger 2022](https://doi.org/10.1021/jasms.2c00153)).
- **DDA opportunity / low abundance:** DDA MS/MS coverage is limited by which
  precursors are selected during elution; iterative exclusion and
  target-directed DDA improve coverage, especially for lower-abundance or
  co-eluting ions
  ([Koelmel 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5408749/),
  [Analytica Chimica Acta 2017](https://doi.org/10.1016/j.aca.2017.08.044)).
  Therefore missing DDA evidence remains `not_observed` unless local acquisition
  opportunity is shown.
- **RT drift / orthogonal evidence:** OBI-Warp exists because LC-MS RT drift is
  a real alignment problem, not a simple hard veto
  ([Prince 2006, via xcms docs](https://sneumann.github.io/xcms/reference/retcor.obiwarp-methods.html)).
  MSI-style reporting requires orthogonal evidence for strong identification,
  such as RT plus mass spectrum or accurate mass plus MS/MS
  ([Sumner 2007](https://pmc.ncbi.nlm.nih.gov/articles/PMC3772505/)).

Any future shape, MS2-pattern, DDA-opportunity, RT-drift, or matrix-behavior
metric that lacks a paper or official-method anchor must stay out of the V2
gate. It may be recorded as exploratory context, but it must not be used to
promote a row, reject a row, or close a blocker.

### DeepResearch method synthesis intake

The user-supplied external synthesis
`Feature Recognition_deepresearch_MLDL_chatgpt_deepresearch.md` is accepted as
design input for the next V2 evidence-chain checkpoint, not as a product
authority. The source file remains an external local artifact and is not
committed. Its strongest usable direction is to separate candidate generation
from peak-quality judgment:

```text
alignment / rescue / gap filling candidate recall
  -> machine-readable peak-quality evidence vector
  -> shadow label alignment
  -> separate future product promotion contract
```

This reinforces the current `diagnostic_only` boundary. V2 should not try to
replace peak picking, alignment, or rescue with a machine-learning model. The
near-term path is a MetaClean / NeatMS-style quality layer over existing
candidate rows: preserve mature candidate generation for recall, then use
machine-observed peak-quality, pattern, RT-drift, and opportunity evidence to
explain or demote rows.

For MS1 shape and pattern evidence, the synthesis adds these V2 requirements:

- `formal_shape_metric` must become a feature vector, not a single correlation.
  Required candidate fields should include local S/N or noise context, FWHM or
  scan-count width, local prominence or sharpness, bell/Gaussian-like similarity
  when parameterized, local zigzag/noise behavior, tailing/asymmetry when
  computable, boundary/margin context, and selected-cell height dominance such
  as `cell_to_local_window_max_ratio`.
- RAW-backed trace evidence should keep the current `family_ms1_overlay_*`
  provenance and may additionally emit a fixed-grid trace segment plus a
  boundary mask inspired by NeatMS. The fixed-grid representation is an evidence
  artifact, not a CNN commitment.
- A supportive MS1 pattern should mean the expected RT region has a coherent
  local peak, comparable boundary/margin context, and no stronger neighboring
  interference. Low apex or selected-cell height can remain
  `inconclusive_opportunity` when local trace shape is present but weak.
- CWT remains an optional shape observer. It can contribute width/ridge/shape
  context only after official API semantics and parameter provenance are pinned.
  It must not become chemical identity evidence.

### V2 Peak-Quality Feature-Vector Contract

The next diagnostic-only checkpoint upgrades the current RAW-backed overlay
shape metric into a small feature vector over the existing
`family_ms1_overlay_*` trace-data JSON. This is an optional expansion of
`shared_peak_identity_ms1_pattern_coherence_evidence.tsv`; it does not add a
new diagnostic entrypoint and does not change production labels.

Source contract:

- provenance is the existing overlay trace-data JSON path stored in
  `family_ms1_overlay_trace_data_json`;
- vector metrics are computed only from per-trace `rt` / `intensity` arrays,
  selected-cell apex/boundary fields, cell height, local-window maximum, and
  trace maximum already present in that JSON;
- no new RAW reread, mzML conversion, ML/DL inference, or product scoring path
  is part of this checkpoint.

Optional TSV columns:

- `peak_quality_vector_status`: `supportive`, `partial_support`,
  `inconclusive`, or `not_available`;
- `peak_quality_vector_basis`: currently
  `family_ms1_overlay_raw_trace_vector` when the vector is machine-observed;
- `peak_quality_trace_point_count` and `peak_quality_boundary_point_count`;
- `peak_quality_signal_to_noise_proxy`;
- `peak_quality_fwhm_sec`;
- `peak_quality_sharpness_score`;
- `peak_quality_zigzag_score`;
- `peak_quality_tailing_ratio`;
- `peak_quality_boundary_margin_ratio`;
- `peak_quality_feature_count`;
- `peak_quality_vector_reason`.

Consumer contract:

- `formal_shape_metric` may be closed by MS1 overlay evidence only when the row
  has the existing `trace_constellation` overlay shape basis and a
  machine-observed `peak_quality_vector_basis`;
- older overlay JSON without `rt` / `intensity` remains readable, but it is no
  longer treated as the full V2 evidence chain;
- weak local height or noisy/ugly trace vectors should become
  `partial_support` or `inconclusive`, not automatic chemical absence.

For labels and calibration, V2 must treat the current manual rows as a seed
oracle rather than a training corpus. A later classifier checkpoint may build a
small stratified oracle, but it must:

- stratify by intensity, RT region/drift phase, matrix, boundary quality,
  DDA/MS2 opportunity, and failure mode;
- keep `human_unjudgeable` and borderline rows out of binary training targets;
- split by sample/raw file or family context rather than random peak rows;
- report precision/recall/F1 or PR-AUC style evidence and calibration behavior
  on paired raw-file units, not thousands of pseudo-independent peaks from the
  same sample.

The synthesis also adds explicit non-goals for the V2 evidence chain:

- no end-to-end ML/DL replacement for current peak picking;
- no profile-mode PeakBot / 3D point-cloud path unless a future research spec
  funds annotation, GPU/model maintenance, and benchmark infrastructure;
- no mzML conversion requirement for the current Thermo RAW-centered product
  path;
- no V2 product label promotion from unverified DeepResearch citations, a CNN
  idea, or a shape-only metric.

The V2 diagnostic must therefore include a machine-evidence provenance sidecar.
A row cannot be counted as machine-observed sufficient if the decisive shape,
pattern, opportunity, RT-drift, or scope fact only came from the manual oracle.
Manual oracle tags may define the reviewed vocabulary, but they are not
evidence by themselves. Once every decisive tag has a machine-observed basis and
`missing_machine_evidence` is empty, the row may be counted as
`machine_observed_sufficient` even though the sidecar still records the manual
tags for auditability.
Machine proxies such as `trace_quality`, `scan_support_score`, current
rescued/detected status, and family-level CID product / neutral-loss context may
explain why the existing pipeline behaved as it did. Family-level pattern
context is recorded when `neutral_loss_tag`, `family_product_mz`, and
`family_observed_neutral_loss_da` are present, but it remains context/proxy only.
It does not by itself close candidate-aligned or sample-level MS2 pattern
evidence.
RT deltas outside the alignment preferred window may be recorded as
machine-observed RT-conflict context, but RT remains contextual evidence rather
than a chemical identity veto unless an explicit RT exclusion policy is added.

The V2 diagnostic may optionally consume existing CWT shape and Tier2 raw-trace
sidecars:

```text
--cwt-shape-evidence-tsv <alignment_tier2_cwt_manual_agreement_probe*.tsv>
--tier2-trace-evidence-tsv <alignment_tier2_trace_evidence.tsv>
--candidate-ms2-pattern-evidence-tsv <candidate_aligned_ms2_pattern.tsv>
--candidate-ms2-pattern-batch-index <discovery_batch_index.csv>
--candidate-ms2-pattern-raw-dll-dir <thermo_rawfile_reader_dll_dir>
```

These inputs may upgrade row provenance to `machine_observed_partial` or
`machine_observed_sufficient` only for rows whose decisive evidence tags are all
covered by machine-observed fields. They must not mark the machine labeler ready
while candidate-aligned MS2 / neutral loss pattern evidence, DDA opportunity
policy, or RT/pattern conflict policy is still missing. Context7's SciPy
documentation check confirms `find_peaks_cwt` identifies relative maxima across
CWT scales in a 1-D signal, and `find_peaks` / `peak_widths` report signal peak
properties. Therefore CWT can support peak-shape evidence only; it is not
chemical identity evidence. CWT conflicts must be evaluated against manual shape
tags such as `shape_complete`, `shape_normal`, or `shape_bad`, not against the
overall manual pass/fail label.

The candidate-aligned MS2 sidecar must be fail-closed. It must be keyed by
`feature_family_id` plus `sample_stem`; target-label-only, RT/mz-only, or
unreviewed heuristic joins are not sufficient. Its required input columns are
`feature_family_id`, `sample_stem`, `candidate_ms2_pattern_status`, and
`candidate_ms2_evidence_level`. Only `candidate_ms2_evidence_level` values
`sample_candidate_aligned` or `sample_boundary_aligned` may affect the
provenance sidecar. A `pattern_mismatch` manual tag is machine-observed only
when the sidecar reports candidate-level `conflict`; a supportive sidecar value
against `pattern_mismatch` is a machine-observed conflict, not a closed gap.
When `--candidate-ms2-pattern-batch-index` is used, the diagnostic may generate
`shared_peak_identity_candidate_ms2_pattern_evidence.tsv` from the same
discovery batch index that fed the alignment run. The generated producer may
mark a row supportive only when `alignment_cells.source_candidate_id` resolves to
a discovery candidate with observed product / neutral-loss tag evidence. Rescued
cells without `source_candidate_id` remain `not_available`; this is a deliberate
fail-closed result, not a negative chemical identity decision.
Direct discovery-candidate neutral-loss evidence must preserve the established
targeted contract: `best_ppm <= nl_ppm_warn` maps to `supportive`,
`nl_ppm_warn < best_ppm <= nl_ppm_max` maps to `partial_support`, and
`best_ppm > nl_ppm_max` maps to `conflict` only for the MS2/NL sidecar. The
current targeted DNA defaults are `nl_ppm_warn=20` and `nl_ppm_max=50`; values
inside the warning band are not chemical absence evidence.

If `--candidate-ms2-pattern-raw-dll-dir` is also provided, the generated producer
may additionally probe those `source_candidate_id`-missing rows against the
sample RAW file declared in the discovery batch index. This fallback is still
`diagnostic_only` and uses the existing RAW reader plus
`neutral_loss.collect_candidate_ms2_evidence`; it does not add a new
fragmentation rule. A row may become `sample_boundary_aligned` only when the
MS2 scan is aligned to the cell peak boundary, apex fallback, or boundary-rescue
window used by that existing helper. `OK` neutral-loss evidence maps to
`supportive`; `WARN` maps to `partial_support`. `conflict` is reserved for a
stricter failure mode where a
boundary-aligned precursor MS2 trigger exists and the nearest non-matching
product peak is the spectrum base peak outside the diagnostic product window.
Other `NL_FAIL` cases, including low-intensity product-below-floor observations,
stay `not_observed`. No precursor MS2 trigger also maps to `not_observed`. These
non-supportive cases must not be treated as chemical absence evidence because
DDA precursor opportunity is known to be incomplete.

RT drift and MS1 pattern evidence may also use injection-local QC context when
the provenance is explicit: choose the QC sample nearest to, or near, the sample
in injection order and compare whether its MS1 pattern contains the same local
peak constellation around the candidate RT. This is a drift-context support
surface, not a standalone production promotion rule, and must cite the injection
order / QC source used.

## V1 Acceptance Criteria

### Slice 0 (vocabulary validation) is complete when

- the durable oracle exists under `docs/superpowers/fixtures/` and records the
  user-reviewed families above (including `pass`, `suspect`, `fail`, and
  `human_unjudgeable` where applicable) with schema version, scope, label
  source, confidence, and reviewed-evidence fields, at the row grain defined in
  "Oracle Row Grain";
- every reviewed seed cell receives an `explanation_status` of `explained`,
  `partially_explained`, `unexplained`, or `inconclusive`;
- every `unexplained` row names the missing fact that would be needed next;
- all seed rows are explained for the Slice 0 vocabulary-validation decision to
  close: `seed_rows_explained=seed_rows_total`,
  `seed_rows_unexplained=0`, `seed_rows_inconclusive=0`, and no explanation row
  uses `evidence_gap_class=unexplained_machine_manual_gap`;
- the FAM000144 extra rescued-style candidate is explainable as a permissive
  machine failure caused by RT and pattern conflict despite normal shape;
- FAM001589 is preserved as human-unjudgeable rather than forced into binary
  training data;
- FAM001227 / FAM001239 delta-mass context is recorded as future context only;
- the required explanation classes cover the seed rows without a family-specific
  exception, so `vocabulary_special_casing_detected` is `FALSE`.

If any seed row remains `unexplained` or unresolved `inconclusive`, if any row
uses `unexplained_machine_manual_gap`, or if
`vocabulary_special_casing_detected` is `TRUE`, Slice 0 may still emit
diagnostic artifacts but the `vocabulary_validated` target is not reached. Stop
and revise the vocabulary or oracle before starting Slice 1.

### Slice 1 (blast-radius / overfit) is complete when

- the blast-radius manifest records artifact paths, SHA256 values, row/sample/
  family counts, schema/version fields, and missing-field counts;
- the blast-radius summary reports `seed_count`, `context_row_count`,
  `non_seed_same_family_count`, `assessed_row_count`, `all_available_row_count`,
  `compatible_row_count`, `unavailable_field_count`, `contradictory_count`,
  `ambiguous_machine_match_count`, fraction fields, and `overfit_risk` by
  `evidence_gap_class` and `scope`;
- `shared_peak_identity_run_facts.tsv` records `blast_radius_assessed`,
  `blast_radius_stale_artifact_count`, and `max_overfit_risk` as raw facts for
  the V2 gate; V1 emits no gating verdict;
- the report separates machine-too-conservative cases from machine-too-
  permissive cases;
- existing 8RAW / 85RAW artifacts are used only for blast-radius context unless
  a reviewed validation plan explicitly authorizes a rerun.

### Both slices

- no output claims `production_ready`;
- no primary matrix, workbook schema, or production candidate gate behavior
  changes.

## V2 Direction

V2 owns its own entry gate; V1 does not gate V2. The V2 spec reads the V1
run-level readiness facts (`seed_rows_explained` vs `seed_rows_total`,
`vocabulary_special_casing_detected`, `blast_radius_assessed`,
`max_overfit_risk`) and decides whether to begin. As a default, V2 should not
begin while `vocabulary_special_casing_detected` is `TRUE`, while seed rows
remain unexplained, or while `blast_radius_assessed` shows the non-seed / 85RAW
surface was never assessed — but that gate is defined and owned by the V2 spec,
not asserted here.

The V1.5 / V2 diagnostic checkpoint relaxes "begin" into two modes:

- `exploratory_only`: V2 may emit shadow-label alignment artifacts over the
  manual seed rows even when blast-radius freshness or semantic generalization is
  not current. This mode is allowed because it answers what the machine evidence
  chain is missing, not because it promotes labels.
- `shadow_ready_candidate`: V2 may report this only when seed vocabulary holds,
  the blast-radius facts are current, overfit risk is low, stale artifact count
  is zero, the seed shadow labels align without contradictions, and the decisive
  evidence basis is machine-observed rather than manual-oracle-derived or
  proxy-only.

V2 target:

```text
shadow_ready machine label alignment
```

V2 may introduce shadow labels such as:

- `manual_like_pass_candidate`;
- `manual_like_suspect_candidate`;
- `manual_like_fail_candidate`;
- `machine_quality_high_candidate`;
- `machine_quality_low_or_noisy`;
- `low_opportunity_supported`;
- `rt_pattern_conflict_blocked`;
- `human_unjudgeable_like`.

V2 output artifacts:

```text
shared_peak_identity_shadow_labels.tsv
shared_peak_identity_shadow_alignment_summary.tsv
shared_peak_identity_v2_readiness.tsv
shared_peak_identity_machine_evidence_support.tsv
shared_peak_identity_candidate_ms2_pattern_evidence.tsv  # optional generated producer
shared_peak_identity_sample_negative_evidence.tsv        # optional sidecar
shared_peak_identity_v2_report.md
```

The readiness artifact owns the clear answer. It must state whether V2 is
`exploratory_only`, `shadow_ready_candidate`, `blocked_by_vocabulary`, or
`blocked_by_overfit_risk`, and must include
`machine_only_labeler_ready=TRUE/FALSE`, `machine_evidence_basis`, row counts
for machine-observed / proxy-only / manual-derived evidence, and the named
machine evidence blockers.

V2 must still avoid primary matrix promotion unless a separate promotion
contract exists. Its success metric should be trend alignment with manual
`pass` / `suspect` / `fail`, not perfect agreement.

### V2 Non-Delta Evidence Closeout

All non-delta V2 evidence obligations are now explicit diagnostic contracts.
The FAM001227/FAM001239 delta-mass relationship remains future work and must not
change current pass/fail shadow labels.

Sample-level negative evidence uses a two-layer contract:

- `negative_evidence_class` is the gate-facing class and must be one of
  `no_candidate_ms1_evidence`, `pattern_mismatch`, `rt_not_explained`, or
  `local_peak_not_decisive`.
- `negative_evidence_detail` preserves narrower review/debug reasons such as
  `ugly_shape`, `bad_boundary`, `multi_peak_interference`, or
  `qc_reference_conflict`.

The class boundary is intentional: `pattern_mismatch` means a local peak is
decidable and clearly unlike the reference pattern; `local_peak_not_decisive`
means the local region is not suitable for a confident identity call because of
shape, boundary, interference, or multiple-peak ambiguity.

Missing expected NL/MS2 remains non-dispositive by default. A missing-NL case can
close the DDA policy blocker only when MS1 identity evidence is supportive, MS1
intensity is at least `2.5e4`, boundary-aligned RAW MS2 trigger count is at least
`3`, and the available MS2 trace-strength proxy is `moderate` or `strong`.
Otherwise it remains opportunity context, not negative identity evidence.

## Fail-Fast Rules

Stop before Slice 0 implementation if:

- the manual oracle cannot be encoded without ambiguous sample scope;
- the existing artifacts cannot identify machine labels or blockers for the
  reviewed cells;
- multiple machine rows match an oracle row and cannot be represented without
  silently choosing a candidate;
- the assembler cannot reconcile oracle `sample_id` with machine-artifact
  `sample_stem` for a reviewed cell;
- V1 would require new RAW re-read work before it can explain any manual case;
- package documentation contradicts a proposed metric's assumed behavior;
- a proposed explanation class directly implies production promotion;
- the design starts encoding family-specific exceptions instead of reusable
  evidence facts.

Stop before Slice 1 implementation if:

- the Slice 0 vocabulary did not hold, or
  `vocabulary_special_casing_detected=TRUE`;
- the blast-radius manifest cannot be constructed with enough artifact
  identity to distinguish seed from non-seed behavior.

If the artifacts cannot distinguish between missing evidence and contradictory
evidence for a row, set that row's `explanation_status=inconclusive` and record
it; V1 does not roll this up into a gating verdict.

## Review Focus

Subagent review for this spec should use `xhigh` reasoning effort and challenge
at least these questions:

- Does the spec preserve the distinction between explanation and label
  convergence?
- Does the manual oracle risk overfitting seven families?
- Are the proposed evidence groups enough to represent the user's actual
  manual reasoning?
- Does the design accidentally make CWT, RT, pattern similarity, or delta-mass
  context more authoritative than intended?
- Is the 8RAW / 85RAW blast-radius role strong enough to prevent one-off
  special casing?
- Are missing DDA and low intensity modeled as opportunity, not negative
  evidence?
- Is there a clear path from V1 explanation to V2 shadow label alignment without
  jumping to production behavior?

## Out Of Scope

- Production promotion.
- Direct changes to selected peak scoring.
- Direct changes to backfill rescue decisions.
- Direct changes to Tier 2 positive support token derivation.
- New 85RAW execution from this design alone.
- Real CWT ridge tracking.
- AsLS / baseline cleanup.
- Workbook schema changes.
