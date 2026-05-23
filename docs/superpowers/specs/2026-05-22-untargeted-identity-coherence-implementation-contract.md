# Untargeted Identity Coherence Implementation Contract

**Date:** 2026-05-22
**Status:** Split review draft v0.4

This spec defines engineering boundaries, IO, config, and frozen outputs. It
depends on:

- [Overview](2026-05-22-untargeted-identity-coherence-prototype-spec.md)
- [Core identity spec](2026-05-22-untargeted-identity-coherence-core-spec.md)
- [Controls spec](2026-05-22-untargeted-identity-coherence-controls-spec.md)
- [Downstream audit boundary](2026-05-22-untargeted-identity-coherence-downstream-audit-boundary.md)

## Data Flow

Preferred inline mode:

```text
discover_candidates
  -> build_sample_local_owners
  -> cluster_sample_local_owners
  -> identity_coherence_diagnostic       # new opt-in diagnostic stage
  -> owner_backfill                      # unchanged production path
  -> build_matrix / review / cells       # unchanged production path
```

The diagnostic needs pre-Backfill owner state. Post-hoc `--alignment-dir` mode
is comparison/reporting only unless an input artifact explicitly encodes the
full pre-Backfill owner state.

## Import Boundary

Domain logic may depend on:

- arrays;
- config values;
- typed context objects;
- small domain models;
- small metric primitives.

Reusable metric primitives must live in a domain-safe module such as
`xic_extractor/alignment/identity_coherence/metrics.py` or an existing
domain-safe package. If a useful metric currently exists only under
`tools/diagnostics`, move or wrap the primitive inward first. Diagnostic tools
import the domain helper; domain logic must not import diagnostic tools.

Domain logic must not import:

- `tools/diagnostics`;
- workbook builders;
- GUI code;
- CLI scripts;
- process backends;
- report renderers;
- RAW adapters.

Diagnostic tools may provide validation artifacts, benchmark files, or example
metrics. They are not imported by `identity_coherence` domain logic.

## Evidence Firewall

Allowed for identity promotion:

- active discovery/profile fragment tag evidence;
- product m/z and mode-specific fragment tolerance evidence;
- pre-Backfill sample-local MS1 owner evidence;
- diagnostic vendor XIC traces collected before Backfill;
- seed coherence and evidence-sufficiency gates derived before Backfill;
- trace identity / shape metrics derived from diagnostic candidate traces.

Validation-only evidence:

- targeted ISTD benchmark/control labels;
- positive-control and identity-decoy labels;
- targeted benchmark diagnostics emitted by `tools/diagnostics/*`;
- discovery `evidence_score` and `evidence_tier` as review-ranking context;
- current production `production_decisions`, `matrix_identity`, and workbook
  outputs;
- post-hoc `alignment-dir` joins used only for comparison/reporting.

Forbidden for identity promotion:

- `owner_backfill` rescued area/status;
- `backfill`, `rescued`, `absent`, `unchecked` production statuses;
- final `include_in_primary_matrix`;
- workbook values;
- family-center re-extraction after Backfill;
- post-Backfill row inclusion or rescue dependency.

Summary assertion:

```text
promotion_used_forbidden_evidence = false
```

Keep `forbidden_evidence_seen` when comparison inputs contain forbidden
evidence. Do not keep a per-row `used` column that is always false.

Required firewall fixture:

- fixture path:
  `tests/fixtures/identity_coherence/firewall_spoof/`;
- baseline input: `pre_backfill_owner_state.jsonl` plus candidate rows needed
  to create at least one would-primary and one Review-only decision;
- spoof input: `post_backfill_spoof.tsv` joined by `decision_id` or
  `source_feature_family_id`, containing conflicting fields such as `rescued`,
  `include_in_primary_matrix`, `production_status`, and workbook-derived area;
- expected output: `expected_decisions.tsv` listing `decision_id`, `decision`,
  `total_coherent_sample_count`, `non_seed_coherent_sample_count`,
  `tier12_non_seed_identity_sample_count`, and `forbidden_evidence_seen`;
- A/B assertion: baseline and spoof runs must emit identical `decision`,
  coherent counts, seed gate, and per-cell identity basis values. The spoof run
  must additionally mark `forbidden_evidence_seen = true` at row level for the
  affected decisions.

## IdentityCoherenceConfig

All identity policy must be explicit in a typed `IdentityCoherenceConfig`. Code
uses nested config groups. CLI and summary renderers may flatten config for
display, but flat rendering must not drive the domain model.

Config shape:

```text
IdentityCoherenceConfig
  request:
    require_profile_hash
    tag_match_policy = all_request_tags_supported

  seed_gate:
    min_ms1_scan_support_score = 0.50
    require_seed_rt_inside_owner_peak = true

  promotion:
    min_total_coherent_samples = 3
    min_non_seed_coherent_samples = 2
    min_non_seed_tier12_identity_samples = 2

  rt:
    max_rt_sec = 180
    preferred_rt_sec = 60
    seed_center_candidate_sec = 30
    max_center_drift_sec = 30
    center_estimator = median_apex_rt

  fragment:
    precursor_tolerance_ppm = declared
    product_tolerance_ppm = declared
    cid_observed_loss_tolerance_ppm = declared

  shape:
    min_points = 7
    resample_points = 25
    min_cosine = 0.85
    prototype_min_candidates = 3
    prototype_min_non_seed_candidates = 2
    allow_seed_shape_fallback = true
    allow_morphology_rt_medoid = true

  width:
    prototype_min_candidates = 3
    min_ratio = 0.50
    max_ratio = 2.00

  controls:
    positive_control_min_pass_fraction = 1.00
    max_decoy_promoted_count = 0
    decoy_rt_owner_boundary_margin_sec = declared
    identity_controls_manifest = optional path before 8RAW,
      required before interpretation

  engineering:
    max_projected_85raw_identity_xic_requests = required before 85RAW
    max_infrastructure_blocked_fraction = 0.05
```

`decoy_rt_owner_boundary_margin_sec` is configured in seconds for consistency
with identity RT tolerances. Existing candidate RT fields are in minutes, so
decoy generation must add `decoy_rt_owner_boundary_margin_sec / 60.0` to
`owner_peak_end_rt` when constructing the `rt_shift` decoy.

Optional downstream audit values are not identity policy:

```text
background_audit_blank_detection_fraction = optional validation-only value
background_audit_sample_blank_area_ratio = optional validation-only value
background_audit_qc_cv = optional validation-only value
```

The diagnostic summary must echo every effective config value, source, and
unit.

Do not add separate threshold config keys for tier-3-only or RT-only promoted
rows. Tier-3-only and RT-only support are structurally Review-only under the
core spec, so such thresholds would be vestigial.

## Domain Model And Request Builder Boundary

Schema ownership lives in this implementation contract. The core identity spec
owns behavior and links to this file instead of duplicating frozen columns.

Domain-safe payload dataclasses live in
`xic_extractor/alignment/identity_coherence/models.py`.

Conceptual model:

```text
IdentityCoherenceRequest
  request_id
  decision_id
  seed_candidate_id
  seed_sample
  identity: FragmentIdentity

FragmentIdentity
  fragment_observation_mode
  precursor_mz
  product_mz
  fragment_tags
  fragment_tag_match_policy
  precursor_tolerance_ppm
  product_tolerance_ppm
  fragment_profile_id
  fragment_profile_hash
  mode_constraint: CidNeutralLossConstraint

CidNeutralLossConstraint
  cid_observed_loss_da
  cid_observed_loss_tolerance_ppm
```

`fragment_observation_mode = cid_neutral_loss` is the only executable v0.4
mode. HCD/base-product and HCD-observed-neutral-loss support must be added as
new mode-specific constraint dataclasses under the same `FragmentIdentity`
abstraction, not as a parallel identity pipeline.

The request/candidate evidence builder is the only adapter surface allowed to
read legacy discovery field names such as `matched_tag_names`,
`neutral_loss_tag`, `observed_neutral_loss_da`, and
`neutral_loss_mass_error_ppm`. Domain gates read only
`IdentityCoherenceRequest`, `FragmentIdentity`, and normalized
`SeedCandidateEvidence`.

Adapter tag source priority:

1. use `matched_tag_names` when present and non-empty;
2. fallback to single-value `neutral_loss_tag` only when `matched_tag_names` is
   absent or empty;
3. if both exist and the legacy single tag is not contained in
   `matched_tag_names`, keep `matched_tag_names` and emit
   `legacy_single_tag_disagrees_with_matched_tags`.

Tag normalization:

- trim whitespace;
- preserve exact case;
- do not case-fold;
- stable unique ordering for TSV output;
- a normalized tag set with no non-empty tokens is a missing constraint;
- empty separator slots inside otherwise valid input are ignored;
- case-only variants are not merged and must emit
  `fragment_tag_case_variant_seen`.

Anti-parallel-variable rule: domain code must not carry both normalized
`fragment_tags` and legacy `neutral_loss_tag` / `matched_tag_names` in parallel.
Legacy names are adapter inputs only. TSV output is flat, but code uses the
nested model above.

The seed-gate slice introduces normalized `SeedCandidateEvidence` as the joined
candidate payload. It carries candidate id, precursor m/z, product m/z, CID
observed loss, supported fragment tags, seed RT, MS1 scan support, and
`evidence_stage`. `evidence_stage` values are `pre_backfill`,
`backfill_only`, and `post_backfill`; only `pre_backfill` may become
`coherent_seed`.

Seed-gate owner assignment handling is intentionally conservative: `primary`
and `supporting` may pass the owner-status check, `unresolved` maps to
`no_quantifiable_owner`, and `ambiguous` or unknown status strings map to
`ambiguous_owner`. Unknown strings must not silently behave like `primary`.

## RAW/XIC Cost Budget

Required counters:

```text
layer1_candidate_count
layer1_seed_gate_failed_count
layer1_blocked_count
layer2_xic_request_count
extract_xic_batch_count
raw_chromatogram_call_count
xic_point_count
xic_request_cache_hit_count
xic_request_deduplicated_count
wall_time_sec
per_raw_xic_request_count
per_decision_xic_request_count
background_audit_xic_request_count
control_xic_request_count
projected_85raw_identity_xic_request_count
```

Projection must separate identity-coherence requests from optional blank/QC or
downstream audit requests.

If an MS1 scan-index or approximate fast path is used, it must be marked as an
explicit approximate diagnostic mode. It must not silently replace vendor XIC as
an equivalent path.

## Engineering Go / No-Go

This table owns engineering, firewall fixture, schema, process, infrastructure,
and cost gates. Core identity promotion invariants are owned by the core spec.
The controls spec owns positive-control and decoy rules.

| Observation after 8RAW | Decision |
| --- | --- |
| `promotion_used_forbidden_evidence = false` and the firewall A/B fixture preserves decisions/counts/basis under spoofed post-Backfill fields | Proceed. |
| `promotion_used_forbidden_evidence = true` | No-Go; identity promotion crossed the evidence firewall. |
| Schema marker parity tests pass for all frozen TSV schemas | Proceed for implementation review. |
| Any frozen schema marker parity test fails | No-Go; docs and code constants drifted. |
| Spawn/process payload smoke test passes on Windows semantics | Proceed for process-mode review. |
| Spawn/process payload smoke test fails | Pivot; fix pickleable payload boundaries before RAW/XIC execution. |
| Request builder imports only domain-safe models and does not import writer/report/workbook/diagnostic-tool surfaces | Proceed. |
| Request builder imports writer/report/workbook/diagnostic-tool surfaces | No-Go; domain import boundary is broken. |
| `infrastructure_blocked_fraction <= max_infrastructure_blocked_fraction` | Proceed for mechanics review. |
| `infrastructure_blocked_fraction > max_infrastructure_blocked_fraction` | Pivot; fix RAW/XIC access or process-mode reliability before interpreting decisions. |
| 85RAW run has a reviewed count+fraction policy and `projected_85raw_identity_xic_request_count <= max_projected_85raw_identity_xic_requests` | Proceed to 85RAW execution. |
| 85RAW run lacks a reviewed count+fraction policy or request-budget ceiling | No-Go for 85RAW; 8RAW mechanics may still be reviewed. |
| `projected_85raw_identity_xic_request_count > max_projected_85raw_identity_xic_requests` | Pivot; reduce request count or change retrieval strategy before 85RAW. |

Do not add separate threshold config keys for tier-3-only or RT-only promoted
rows. Tier-3-only and RT-only support are structurally Review-only under the
core spec, so such thresholds would be vestigial.

## CLI / Invocation Contract

Preferred inline mode:

```powershell
python scripts\run_alignment.py `
  <existing args> `
  --emit-identity-coherence-diagnostic `
  --identity-coherence-config <identity_coherence_config.yml> `
  --identity-coherence-output-dir <diagnostic_output_dir>
```

Equivalent diagnostic module mode is acceptable only if it consumes an explicit
pre-Backfill owner-state export:

```powershell
python -m tools.diagnostics.untargeted_identity_coherence `
  --pre-backfill-owner-state <owner_state.jsonl> `
  --identity-coherence-config <identity_coherence_config.yml> `
  --raw-dir <raw_dir> `
  --output-dir <diagnostic_output_dir>
```

Post-hoc comparison mode:

```powershell
python -m tools.diagnostics.untargeted_identity_coherence_report `
  --alignment-dir <existing_alignment_output_dir> `
  --diagnostic-dir <diagnostic_output_dir>
```

Post-hoc comparison mode must not promote identities.

## Process Mode Contract

- Domain-safe payload dataclasses live in
  `xic_extractor/alignment/identity_coherence/models.py`:
  `IdentityCoherenceRequest`, `IdentityCoherenceResult`,
  `IdentityCoherenceTraceRequest`, and `IdentityCoherenceTraceResult`.
- `xic_extractor.alignment.identity_coherence` receives typed
  owner/candidate/config/trace payloads only.
- Serial and process orchestration may call RAW adapters or schedule XIC
  extraction, but that remains outside domain logic.
- RAW/XIC worker adapters live in the orchestration layer, not in core domain
  decision code.
- Process workers receive pickleable request/result payloads.
- Do not pass open RAW handles, nested closures, GUI objects, workbook objects,
  or report writers.
- Add a no-RAW process-mode smoke test using
  `multiprocessing.get_context("spawn")` on Windows semantics, proving
  diagnostic request/result payloads can be imported, sent to a worker, and
  round-tripped without RAW files.

## Frozen Outputs

V0.4 freezes:

```text
untargeted_identity_coherence_requests.tsv
untargeted_identity_coherence_decisions.tsv
untargeted_identity_coherence_cell_evidence.tsv
untargeted_identity_coherence_controls.tsv
untargeted_identity_coherence_summary.md
```

Exploratory, not frozen before 8RAW:

```text
untargeted_identity_coherence_candidates.tsv
untargeted_identity_coherence_groups.tsv
```

### Required `requests.tsv` Columns

This is a seed/request-level audit surface. It must not include per-sample trace
metrics, downstream blank/QC fields, Backfill output, workbook values, or the
full fragment profile blob. It is the flat TSV projection of
`IdentityCoherenceRequest` and `FragmentIdentity`.

```text
<!-- schema:identity_coherence_requests.tsv:start -->
request_id
decision_id
seed_candidate_id
seed_sample
fragment_observation_mode
precursor_mz
product_mz
fragment_tags
fragment_tag_match_policy
fragment_profile_id
fragment_profile_hash
precursor_tolerance_ppm
product_tolerance_ppm
cid_observed_loss_da
cid_observed_loss_tolerance_ppm
request_identity_completeness_status
request_candidate_identity_status
precursor_error_ppm
product_error_ppm
cid_observed_loss_error_ppm
cid_observed_loss_error_da
request_builder_flags
<!-- schema:identity_coherence_requests.tsv:end -->
```

Required categorical values:

```text
request_identity_completeness_status =
  complete |
  missing_fragment_observation_mode |
  missing_precursor_mz |
  missing_product_mz |
  missing_fragment_tags |
  missing_tolerance |
  missing_mode_specific_constraint

request_candidate_identity_status =
  not_assessed |
  match |
  missing_discovery_candidate_join |
  missing_diagnostic_fragment_evidence |
  request_candidate_identity_mismatch |
  unsupported_fragment_observation_mode

fragment_tag_match_policy = all_request_tags_supported
```

For frozen `requests.tsv` output, `request_candidate_identity_status =
not_assessed` is valid only when the request is incomplete or the candidate join
is missing. A missing candidate join should emit
`missing_discovery_candidate_join` when it can be identified cleanly.

First-slice builder objects are pre-gate internal audit candidates. They may
temporarily carry `request_identity_completeness_status = complete` and
`request_candidate_identity_status = not_assessed` before the seed gate has run,
but those objects must not be emitted directly as frozen `requests.tsv` rows.
Final request audit rows require the seed gate or request-vs-candidate check to
resolve complete joined requests to a concrete candidate identity status.

`fragment_profile_hash` may be `unavailable`, but that must add
`fragment_profile_hash_unavailable` to `request_builder_flags`.

Allowed first-slice `request_builder_flags` values are:

```text
missing_seed_sample
fragment_profile_hash_unavailable
fragment_tag_case_variant_seen
legacy_single_tag_disagrees_with_matched_tags
missing_precursor_mz
missing_product_mz
missing_fragment_tags
missing_precursor_tolerance_ppm
missing_product_tolerance_ppm
missing_cid_observed_loss_tolerance_ppm
missing_mode_specific_constraint
```

`precursor_tolerance_ppm`, `product_tolerance_ppm`, and
`cid_observed_loss_tolerance_ppm` are required ppm gates. If any required ppm
tolerance is missing, the completeness status is `missing_tolerance`; do not
borrow `missing_mode_specific_constraint` for common tolerances. Da loss
tolerance is not accepted as a gate. `cid_observed_loss_error_da` is review
context only. For `cid_neutral_loss`, `missing_mode_specific_constraint` is
reserved for the required mode payload itself, such as missing
`cid_observed_loss_da`.

Required m/z, loss, and ppm tolerance values must be finite positive numbers.
Invalid numeric values reuse the corresponding missing-field status/flag
instead of producing a complete request. For `cid_neutral_loss`,
`cid_observed_loss_error_ppm` is relative to `cid_observed_loss_da`; it is not
scaled by precursor m/z.

### Required `decisions.tsv` Columns

```text
<!-- schema:identity_coherence_decisions.tsv:start -->
decision_id
identity_family_id
seed_candidate_id
seed_sample
seed_gate_class
decision
decision_reason
request_identity_completeness_status
request_candidate_identity_status
total_coherent_sample_count
non_seed_coherent_sample_count
tier12_non_seed_identity_sample_count
tier1_fragment_confirmed_sample_count
tier2_shape_supported_sample_count
tier2_seed_shape_fallback_sample_count
tier3_width_only_sample_count
min_total_coherent_samples
min_non_seed_coherent_samples
min_non_seed_tier12_identity_samples
weak_basis_reason
shape_reference_basis
shape_reference_candidate_id
prototype_width_sec
center_rt_sec
center_rt_source
coherent_fraction
infrastructure_blocked_sample_count
data_quality_reject_sample_count
forbidden_evidence_used
<!-- schema:identity_coherence_decisions.tsv:end -->
```

The [core identity spec](2026-05-22-untargeted-identity-coherence-core-spec.md)
owns the decision enum. This implementation contract must not maintain a second
independent enum list. Schema tests must reject emitted `decision` values
outside the core enum and must fail if a duplicated schema definition drifts
from the core contract.

`decision_reason` values are stable strings. `tier1_support` means at least one
non-seed tier 1 fragment-confirmed cell supported a provisional would-primary
decision. `tier2_shape_support` means provisional would-primary was supported by
tier 2 shape evidence without any tier 1 fragment-confirmed non-seed cell.

Do not include sample-id list columns such as `coherent_sample_ids`. Per-sample
detail belongs in `cell_evidence.tsv`. Do not include `weak_basis_only`; it is
derived from `weak_basis_reason != none`.

`forbidden_evidence_used` must be false for every emitted decision. Summary
still reports `forbidden_evidence_seen` counts when comparison inputs contain
forbidden evidence.

### Required `cell_evidence.tsv` Columns

This table is one row per assessed non-seed sample. The seed sample is audited
in `requests.tsv` and `decisions.tsv`; duplicating it here would make support
counts ambiguous.

```text
<!-- schema:identity_coherence_cell_evidence.tsv:start -->
decision_id
identity_family_id
sample_id
candidate_id
cell_assessment_status
cell_identity_tier
cell_identity_basis
fragment_observation_mode
fragment_match_status
fragment_tags_supported
rt_delta_center_sec
rt_gate_status
shape_status
shape_similarity_cosine
shape_reference_basis
shape_reference_candidate_id
shape_fallback_used
shape_audit_status
width_status
width_ratio_to_prototype
baseline_audit_status
area_height_status
non_rt_identity_result
coherent_count_contribution
tier12_count_contribution
blocked_reason
data_quality_reason
forbidden_evidence_seen
<!-- schema:identity_coherence_cell_evidence.tsv:end -->
```

Required categorical values:

```text
cell_assessment_status = assessed | blocked | data_quality_reject | not_assessed
cell_identity_tier = tier1 | tier2 | tier3 | rt_only | blocked | data_quality
cell_identity_basis =
  rt_fragment_support | rt_shape_similarity | rt_prototype_width | none
fragment_match_status = pass | fail | ambiguous | not_assessed
rt_gate_status = pass | fail | not_assessed
shape_status = pass | fail | low_points | zero_signal | not_assessed
shape_reference_basis =
  tier1_supported_medoid | morphology_rt_medoid | seed_fallback | none
shape_audit_status =
  pass | fail | shoulder | bimodal | coelution | saturated | clipped |
  unavailable | not_assessed
width_status = pass | fail | not_assessed
baseline_audit_status = pass | fail | unavailable | not_assessed
area_height_status = pass | fail | not_assessed
non_rt_identity_result = pass | fail | not_assessed | blocked
```

`weak_basis_reason` values are owned by the core spec. They include
`seed_shape_fallback_only`; do not add a separate decision enum for that case.

`coherent_count_contribution` may be true for tier 3. `tier12_count_contribution`
may be true only for tier 1 or tier 2 cells, and seed-shape fallback-only
support cannot satisfy `min_non_seed_tier12_identity_samples`.

`baseline_audit_status` is audit context only. It is not a promotion basis.

### Required `controls.tsv` Columns

These must match the controls spec exactly:

```text
<!-- schema:identity_coherence_controls.tsv:start -->
control_id
control_type
control_name
decision_id
identity_family_id
seed_candidate_id
control_status
control_expected_behavior
control_observed_behavior
control_pass
control_failure_reason
fragment_observation_mode
decoy_generation_method
decoy_source_request_id
decoy_shift_value
decoy_identity_constraint_changed
positive_control_mapping_status
positive_control_target_name
positive_control_target_mz
positive_control_target_rt_sec
positive_control_mapping_error_ppm
positive_control_mapping_delta_rt_sec
control_notes
<!-- schema:identity_coherence_controls.tsv:end -->
```

Add a schema parity test that compares this list with the controls spec contract
or a single shared schema definition used by both docs and implementation.

### Required `summary.md` Sections

- command and mode;
- inline pre-Backfill input source, or explicit reason post-hoc run is
  comparison-only;
- input hashes and row counts;
- request completeness and request-vs-candidate identity status counts;
- control manifest path and control mapping counts;
- evidence firewall assertion `promotion_used_forbidden_evidence = false` and
  `forbidden_evidence_seen` counts;
- seed gate counts and seed coherence/context distributions;
- RT-only candidate counts;
- independent trace identity pass counts by tier;
- diagnostic-fragment-supported sample counts;
- shape similarity score distribution by positive controls, identity decoys,
  would-primary rows, Review-only rows, and shape reference method;
- shape point count distribution and tier-2 pass low-point fraction;
- prototype shape candidate counts, tier-1-supported medoid counts,
  morphology-RT medoid counts, and seed fallback counts;
- would-primary weaker support breakdown:
  `would_primary_with_tier1_supported_shape_medoid_count`,
  `would_primary_with_morphology_rt_shape_medoid_count`,
  `would_primary_with_seed_shape_fallback_count`,
  `would_primary_tier2_only_count`,
  `would_primary_tier2_only_fraction`,
  `would_primary_tier2_only_shape_reference_method_breakdown`,
  `would_primary_tier2_only_morphology_rt_medoid_count`;
- tier-1 cells with width sanity failure;
- weak-basis reason counts;
- background audit status and flag counts;
- per-sample evidence coverage and missing-basis counts;
- infrastructure-blocked counts;
- data-quality reject counts;
- threshold count and fraction summaries;
- RAW/XIC request, point, per-RAW, and timing counters;
- projected 85RAW identity request estimate, with optional downstream audit
  request components reported separately when present;
- Go / No-Go / Pivot table.

## Acceptance Criteria

Implementation contract is ready when:

- evidence firewall fixture is specified;
- identity config is separate from downstream audit values;
- code config is nested by responsibility while CLI/summary may render flat
  values;
- process-mode payload boundary is pickleable;
- `FragmentIdentity` and typed mode constraints are the domain model, with
  `cid_neutral_loss` as the only executable v0.4 mode;
- legacy discovery fields are confined to the request builder adapter;
- seed/request audit surface is frozen in `requests.tsv`;
- per-sample evidence surface is frozen;
- controls output is machine-readable;
- four frozen TSV schemas are represented by code constants and parity-checked
  against marker blocks in this file;
- engineering Go/No-Go table owns firewall fixture, schema parity, process,
  infrastructure, and cost criteria;
- decision enum values are sourced from the core spec or a shared schema, not a
  second independent list;
- every `cell_evidence.tsv` row is a non-seed sample evidence row;
- request counters separate identity from optional downstream audit cost.
- promotion logic tests verify that would-primary rows satisfy
  `total_coherent_sample_count >= min_total_coherent_samples`,
  `non_seed_coherent_sample_count >= min_non_seed_coherent_samples`, and
  `tier12_non_seed_identity_sample_count >=
  min_non_seed_tier12_identity_samples`.
- a count-definition test verifies that whenever `seed_gate_class =
  coherent_seed`, `total_coherent_sample_count == 1 +
  non_seed_coherent_sample_count`, independent of the promotion thresholds.

First implementation slice:

- write scope is limited to:
  - `xic_extractor/alignment/identity_coherence/`;
  - `tests/alignment/identity_coherence/`;
- add `StrEnum` status values for domain states and ordered tuple schema
  constants for the four frozen TSVs;
- add `FragmentIdentity`, `CidNeutralLossConstraint`, and
  `IdentityCoherenceRequest` dataclasses;
- add a duck-typed request builder for `cid_neutral_loss` requests;
- keep request builder tolerant at the adapter edge and strict in normalized
  domain output;
- do not implement request-vs-candidate identity matching yet;
- do not implement a TSV writer yet;
- do not connect RAW/XIC extraction, alignment orchestration, Backfill, workbook,
  report, or CLI surfaces yet.

First slice files:

```text
xic_extractor/alignment/identity_coherence/__init__.py
xic_extractor/alignment/identity_coherence/models.py
xic_extractor/alignment/identity_coherence/schema.py
xic_extractor/alignment/identity_coherence/request_builder.py
tests/alignment/identity_coherence/test_schema_contract.py
tests/alignment/identity_coherence/test_fragment_identity_request_builder.py
```

First slice code rules:

- domain status values use `StrEnum`; enum values are the only valid TSV
  categorical strings;
- this follows the repo's current `StrEnum` pattern. The package Python floor is
  3.11 because `enum.StrEnum` is part of the public schema implementation
  contract;
- schema columns use ordered tuple constants, not enums;
- `__init__.py` is a thin facade only: re-export stable models, builder, enums,
  and schema constants; do not put logic there;
- request builder accepts duck-typed candidate-like objects and must not import
  `DiscoveryCandidate`;
- caller supplies `request_id`, `decision_id`, three ppm tolerances,
  `fragment_profile_id`, and optional `fragment_profile_hash`;
- missing `request_id`, `decision_id`, `candidate_id`, or
  `fragment_profile_id` raises `ValueError` because no traceable audit row can
  be formed;
- ordinary missing identity fields still create an incomplete request object;
- `request_candidate_identity_status` remains `not_assessed` in this slice only
  on the pre-gate builder object, because candidate-vs-request matching belongs
  to the next slice. Such objects must not be emitted as final `requests.tsv`
  rows.

First slice tag normalization:

- input may be `None`, string, list, tuple, or set;
- string input accepts `;`, `|`, or `,` as separators;
- canonical TSV output delimiter is `;`;
- add a small `format_fragment_tags(tags) -> str` helper so canonical TSV
  formatting is testable before the real writer exists;
- trim whitespace;
- do not case-fold;
- preserve case-only variants and add `fragment_tag_case_variant_seen`;
- `matched_tag_names` wins over fallback `neutral_loss_tag`;
- if both legacy fields exist and the fallback single tag is not a member of
  `matched_tag_names`, keep `matched_tag_names` and add
  `legacy_single_tag_disagrees_with_matched_tags`;
- embedded `;`, `|`, or `,` inside list/tuple items are treated as separators,
  not invalid tokens;
- empty separator slots inside otherwise valid input are ignored; a tag input
  with no non-empty tokens is `missing_fragment_tags`.

First slice missing-precedence rule:

```text
missing_fragment_observation_mode
missing_precursor_mz
missing_product_mz
missing_fragment_tags
missing_tolerance
missing_mode_specific_constraint
complete
```

If multiple fields are missing, emit the first status by this order and record
all missing categories in `request_builder_flags`. `missing_fragment_observation_mode`
is kept for future request adapters; the first slice hardcodes
`cid_neutral_loss`, so that status is not reachable in the first-slice builder.

First slice tests must prove:

- four schema constants have no duplicate columns;
- four schema constants match this file's marker blocks exactly;
- status enum values match the categorical values documented here;
- a complete duck-typed candidate plus explicit ppm tolerances creates a
  complete `cid_neutral_loss` request;
- `matched_tag_names` multi-tag input wins over fallback `neutral_loss_tag`;
- tag input supports `;`, `|`, `,`, list, tuple, and set, with canonical `;`
  output;
- case-sensitive tags such as `base` and `BASE` are not merged and emit a flag;
- legacy single tag does not emit a disagreement flag when it is a member of
  `matched_tag_names`;
- missing product m/z, missing tags, missing common tolerance, missing
  mode-specific tolerance, and missing mode payload each create an incomplete
  request object with deterministic status;
- default `fragment_profile_hash = unavailable` emits
  `fragment_profile_hash_unavailable`;
- `format_fragment_tags(("MeR", "dR")) == "MeR;dR"`;
- missing `request_id`, `decision_id`, `candidate_id`, or
  `fragment_profile_id` raises `ValueError`.
