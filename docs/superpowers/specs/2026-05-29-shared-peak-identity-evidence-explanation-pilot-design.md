# Shared Peak Identity Evidence Explanation Pilot Design

**Date:** 2026-05-29
**Status:** reviewed draft, blockers patched after xhigh subagent review
**Readiness label:** `diagnostic_only`
**Target outcome:** `explanation_ready`
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

`explanation_ready` is not allowed when only the manual seed rows are explained.
If the blast-radius manifest is missing, stale, or too sparse to assess
non-seed behavior, V1 may emit `partially_explained` or `inconclusive`, but it
must not unlock V2 label-convergence planning.

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
| `FAM000144` | `NormalBC2312_DNA` and `BenignfatBC1151_DNA` should be rescued; other cells should not. A possible `TumorBC2312_DNA` candidate is not acceptable. | Accepted cells have the only plausible peak in the RT region, complete shape, and similar pattern. The rejected extra candidate has too much RT difference and pattern mismatch even though shape is normal. Low intensity / DDA stochasticity can explain missing fragmentation for accepted cells. |
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
| `manual_label` | `pass`, `suspect`, `fail`, `human_unjudgeable` |
| `manual_label_source` | `direct_eic_ms2_review`, `direct_eic_only_review`, `scope_rule_unmentioned_fail`, `family_all_reviewed_rule`, `derived_from_related_family_context` |
| `manual_confidence` | `high`, `medium`, `low`, `unjudgeable` |
| `manual_scope` | `reviewed_cell`, `reviewed_family_all_cells`, `reviewed_family_named_cells_only`, `scope_derived_unmentioned_fail` |

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
| Current machine decision | `machine_current_label`, `machine_source_role`, `machine_blockers`, `machine_reason` | Required when available. |
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
| `boundary_reference_ambiguous` | Existing blocker depends on which boundary reference is treated as authority. |
| `rt_drift_policy_gap` | RT difference exists, but V1 cannot decide whether it is drift, matrix behavior, or true mismatch. |
| `human_unjudgeable_shape_bad` | Manual review cannot decide because the trace itself is poor. |
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
calibration TSV + compact Markdown report + blast-radius summary
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

The CLI must parse, validate, orchestrate, and write only. It must not scan RAW
files or recompute domain evidence. If the implementation creates this CLI, the
same diff must update `tools/diagnostics/INDEX.md` with purpose, topic group,
originating spec, and outputs.

Primary join key:

```text
feature_family_id + sample_id + oracle_row_id
```

Machine artifacts may not have `oracle_row_id`, so assembler joins use
`feature_family_id + sample_id` first and preserve all candidate/source matches.
If more than one machine row matches an oracle row, the explanation row must set
`machine_match_status=ambiguous_multiple_matches` and list the matched
`source_row_id` values rather than silently choosing one.

Sorting is deterministic:

```text
feature_family_id, sample_id, oracle_row_id, evidence_source, source_row_id
```

Null policy:

- empty numeric field means `metric_unavailable`;
- empty enum field is invalid unless the column is explicitly optional;
- `not_observed`, `not_assessed`, `not_applicable`, and `unavailable` are
  distinct statuses;
- boolean fields are serialized as `TRUE` / `FALSE`.

### Allowed Status / Enum Values

All controlled enum tokens are lower snake case. Semicolon-separated token
lists use `;` with no embedded whitespace. Free-text is allowed only in
`manual_review_note` and `notes`.

| Field | Allowed values or type |
| --- | --- |
| `evidence_source` | `manual_oracle`, `alignment_review`, `alignment_cells`, `tier2_trace_sidecar`, `identity_coherence_sidecar`, `targeted_benchmark_context`, `blast_radius_manifest` |
| `source_role` | `manual_oracle`, `selected_peak`, `rescued_cell`, `tier2_raw_reread`, `identity_coherence_diagnostic`, `targeted_context`, `blast_radius_context` |
| `machine_current_label` | `source_passthrough_token`, or `not_available` when no machine source exists |
| `machine_match_status` | `no_match`, `single_match`, `ambiguous_multiple_matches`, `stale_source`, `missing_required_key` |
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
| `evidence_gap_class` | values from the Required classes table |
| `secondary_gap_tags` | `semicolon_token_list`; tokens must come from evidence gap classes or manual reason tags |
| `explanation_status` | `explained`, `partially_explained`, `unexplained`, `inconclusive` |
| `recommended_next_action` | `no_action`, `inspect_manual_eic`, `inspect_ms2_pattern`, `add_shape_metric`, `add_pattern_metric`, `add_opportunity_metric`, `check_boundary_reference`, `check_blast_radius`, `block_v2_until_more_evidence` |
| `artifact_role` | `manual_oracle_fixture`, `alignment_review`, `alignment_cells`, `tier2_trace_sidecar`, `identity_diagnostic`, `targeted_context`, `blast_radius_context` |
| `artifact_status` | `present_current`, `present_stale_hash_mismatch`, `missing`, `schema_unsupported`, `not_assessed`, `unavailable` |
| `manual_reason_tags`, `machine_blockers`, `source_roles_seen`, `source_artifacts`, `available_required_fields`, `missing_required_fields` | `semicolon_token_list` |

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

Canonical manual oracle:

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

Evidence vectors:

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

Explanations:

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
machine_match_status
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

Blast-radius manifest:

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

Blast-radius summary:

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
non_seed_same_family_count
all_available_row_count
unavailable_field_count
contradictory_count
ambiguous_machine_match_count
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

The Markdown report is human-facing and must summarize these TSVs. It must not
be the only place where counts, hashes, or status values exist.

## Artifact Contract

Planned V1 outputs:

```text
output/shared_peak_identity_evidence_explanation/
  shared_peak_identity_manual_oracle.tsv
  shared_peak_identity_evidence_vectors.tsv
  shared_peak_identity_explanations.tsv
  shared_peak_identity_blast_radius_manifest.tsv
  shared_peak_identity_blast_radius_summary.tsv
  shared_peak_identity_explanation_report.md
```

The output manual oracle is a generated copy of the durable fixture. It must
record the durable fixture path and SHA256 in the report or manifest.

Minimum `shared_peak_identity_explanations.tsv` columns:

```text
feature_family_id
sample_id
manual_label
manual_reason_tags
manual_scope
machine_current_label
machine_source_role
machine_blockers
evidence_gap_class
explanation_status
smallest_missing_fact
recommended_next_action
source_roles_seen
source_artifacts
```

Minimum report sections:

- verdict: `diagnostic_only / explanation_ready` or why not;
- manual rows covered and uncovered;
- disagreements by explanation class;
- examples where machine is too conservative;
- examples where machine is too permissive;
- blast-radius summary from the pinned 8RAW / 85RAW manifest, including
  explicit `not_assessed` or `unavailable` statuses;
- blast-radius manifest status, including any missing or stale artifact;
- V2 candidates and explicit non-goals.

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

V1 acceptance must use a pinned blast-radius manifest. The manifest must cover:

- manual seed oracle rows;
- non-seed same-family rows available in current machine artifacts;
- all available 8RAW review/cell rows relevant to the current diagnostic
  surface;
- all available 85RAW review/cell rows relevant to the current diagnostic
  surface.

If 85RAW artifacts are unavailable or do not contain the fields required for the
blast-radius summary, V1 must emit `blast_radius_status=85raw_not_assessed` and
the maximum readiness is `partially_explained`, not `explanation_ready`. If a
manifested artifact is stale or hash-mismatched, the result is `inconclusive`.

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

## V1 Acceptance Criteria

V1 is complete when:

- the manual oracle records the user-reviewed families above, including
  `pass`, `suspect`, `fail`, and `human_unjudgeable` where applicable;
- the durable oracle exists under `docs/superpowers/fixtures/` with schema
  version, scope, label source, confidence, and reviewed-evidence fields;
- every reviewed cell receives an `explanation_status` of `explained`,
  `partially_explained`, or `unexplained`;
- every `unexplained` row names the missing fact that would be needed next;
- the blast-radius manifest records artifact paths, SHA256 values, row/sample/
  family counts, schema/version fields, and missing-field counts;
- the blast-radius summary reports `seed_count`, `non_seed_same_family_count`,
  `all_available_row_count`, `unavailable_field_count`, `contradictory_count`,
  `ambiguous_machine_match_count`, and `overfit_risk` by
  `evidence_gap_class`;
- missing, stale, or insufficient blast-radius evidence blocks
  `explanation_ready` and returns `partially_explained` or `inconclusive`;
- the report separates machine-too-conservative cases from machine-too-
  permissive cases;
- the FAM000144 extra rescued-style candidate is explainable as a permissive
  machine failure caused by RT and pattern conflict despite normal shape;
- FAM001589 is preserved as human-unjudgeable rather than forced into binary
  training data;
- FAM001227 / FAM001239 delta-mass context is recorded as future context only;
- no output claims `production_ready`;
- no primary matrix, workbook schema, or production candidate gate behavior
  changes;
- existing 8RAW / 85RAW artifacts are used only for blast-radius context unless
  a reviewed validation plan explicitly authorizes a rerun.

## V2 Direction

V2 may begin only after V1 reaches `explanation_ready`.

`partially_explained` is useful but cannot unlock V2. V2 is blocked until the
seed-row explanations survive pinned non-seed and 8RAW/85RAW blast-radius
checks, or until a reviewed follow-up explicitly changes the blast-radius
requirement.

V2 target:

```text
shadow_ready machine label alignment
```

V2 may introduce shadow labels such as:

- `manual_like_pass_candidate`;
- `manual_like_suspect_candidate`;
- `manual_like_fail_candidate`;
- `low_opportunity_supported`;
- `rt_pattern_conflict_blocked`;
- `human_unjudgeable_like`.

V2 must still avoid primary matrix promotion unless a separate promotion
contract exists. Its success metric should be trend alignment with manual
`pass` / `suspect` / `fail`, not perfect agreement.

## Fail-Fast Rules

Stop before implementation if:

- the manual oracle cannot be encoded without ambiguous sample scope;
- the existing artifacts cannot identify machine labels or blockers for the
  reviewed cells;
- the blast-radius manifest is missing, stale, or cannot distinguish seed from
  non-seed behavior;
- multiple machine rows match an oracle row and cannot be represented without
  silently choosing a candidate;
- V1 would require new RAW re-read work before it can explain any manual case;
- package documentation contradicts a proposed metric's assumed behavior;
- a proposed explanation class directly implies production promotion;
- the design starts encoding family-specific exceptions instead of reusable
  evidence facts.

Return `inconclusive` if the artifacts cannot distinguish between missing
evidence and contradictory evidence.

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
