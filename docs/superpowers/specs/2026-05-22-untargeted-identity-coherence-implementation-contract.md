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

- active discovery/profile neutral-loss tag;
- product m/z and observed neutral-loss tolerance evidence;
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

All identity policy must be explicit in a typed `IdentityCoherenceConfig`.

Identity config keys:

```text
seed_min_ms1_scan_support_score = 0.50
precursor_mz_tolerance_ppm = declared
product_mz_tolerance_ppm = declared
observed_loss_tolerance_ppm = declared
max_rt_sec = 180
preferred_rt_sec = 60
seed_center_candidate_sec = 30
max_center_drift_sec = 30
shape_min_points = 7
shape_resample_points = 25
shape_similarity_min_cosine = 0.85
prototype_width_min_candidates = 3
prototype_width_ratio_min = 0.50
prototype_width_ratio_max = 2.00
min_non_seed_tier12_identity_samples = 2
max_infrastructure_blocked_fraction = 0.05
min_positive_control_pass_fraction = 1.00
max_projected_85raw_identity_xic_requests = required before 85RAW
identity_controls_manifest = optional path before 8RAW, required before interpretation
```

Optional downstream audit values are not identity policy:

```text
background_audit_blank_detection_fraction = optional validation-only value
background_audit_sample_blank_area_ratio = optional validation-only value
background_audit_qc_cv = optional validation-only value
```

The diagnostic summary must echo every effective config value, source, and
unit.

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

## Base Identity Go / No-Go

This table owns engineering and invariant gates. The controls spec adds
control-specific positive/decoy rules.

| Observation after 8RAW | Decision |
| --- | --- |
| `promotion_used_forbidden_evidence = false` and the firewall A/B fixture preserves decisions/counts/basis under spoofed post-Backfill fields | Proceed. |
| `promotion_used_forbidden_evidence = true` | No-Go; identity promotion crossed the evidence firewall. |
| Any emitted would-primary has `weak_basis_reason != none` or `tier12_non_seed_identity_sample_count < min_non_seed_tier12_identity_samples` | No-Go; implementation violated the core weak-basis rule. |
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

### Required `decisions.tsv` Columns

```text
decision_id
source_feature_family_id
seed_candidate_id
seed_sample
seed_owner_id
seed_gate_class
seed_reject_reason
seed_ms1_trace_quality
seed_ms1_delta_min
seed_ms1_scan_support_score
seed_neutral_loss_mass_error_ppm
seed_matched_tag_count
seed_tag_intersection_status
seed_request_candidate_identity_status
seed_evidence_score
seed_evidence_tier
seed_ms2_support
seed_ms1_support
seed_rt_alignment
seed_family_context
decision
decision_reason
total_coherent_sample_count
non_seed_coherent_sample_count
assessed_sample_count
coherent_sample_fraction
min_total_coherent_samples
min_non_seed_coherent_samples
center_decision
center_drift_sec
non_rt_identity_pass_count
tier12_non_seed_identity_sample_count
tier1_cell_count
tier2_cell_count
tier3_cell_count
diagnostic_nl_supported_sample_count
weak_basis_reason
background_audit_status
background_audit_flags
rt_only_candidate_count
blocked_infrastructure_count
data_quality_reject_count
forbidden_evidence_seen
control_class
control_expected_decision
notes
```

The [core identity spec](2026-05-22-untargeted-identity-coherence-core-spec.md)
owns the decision enum. This implementation contract must not maintain a second
independent enum list. Schema tests must reject emitted `decision` values
outside the core enum and must fail if a duplicated schema definition drifts
from the core contract.

`seed_request_candidate_identity_status` values:

```text
pass | fail | not_assessed
```

### Required `cell_evidence.tsv` Columns

```text
decision_id
source_feature_family_id
candidate_id
sample_local_owner_id
pre_backfill_owner_state_id
raw_file_stem
source_row_hash
sample_stem
sample_role
cell_decision
candidate_apex_rt_min
candidate_peak_start_rt_min
candidate_peak_end_rt_min
candidate_peak_width_sec
candidate_area
candidate_height
candidate_point_count
rt_delta_center_sec
rt_gate_result
identity_basis_tier
non_rt_identity_basis
non_rt_identity_result
diagnostic_nl_status
precursor_mz_delta_ppm
product_mz_delta_ppm
observed_loss_delta_ppm
shape_similarity_status
shape_similarity_score
shape_point_count
prototype_width_status
prototype_width_sec
prototype_width_ratio
background_audit_status
background_audit_flags
xic_rt_min
xic_rt_max
xic_point_count
xic_request_id
review_flags
evidence_source
reject_reason
```

Required categorical values:

```text
rt_gate_result = pass | fail | not_assessed
identity_basis_tier = seed | tier1 | tier2 | tier3 | rt_only | blocked | data_quality
non_rt_identity_basis =
  seed_sample | rt_diagnostic_nl_support | rt_shape_similarity |
  rt_prototype_width | none
non_rt_identity_result = pass | fail | not_assessed | blocked
diagnostic_nl_status = pass | fail | ambiguous | not_assessed
shape_similarity_status = pass | fail | low_points | zero_signal | not_assessed
prototype_width_status = pass | fail | too_few_candidates | not_assessed
background_audit_status =
  not_assessed | no_background_signal_observed | background_signal_observed
```

`candidate_id`, `sample_local_owner_id`, `pre_backfill_owner_state_id`,
`raw_file_stem`, and `source_row_hash` are required provenance keys. They make
each per-sample evidence row traceable back to the exact pre-Backfill owner and
candidate evidence surface.

### Required `controls.tsv` Columns

These must match the controls spec exactly:

```text
control_id
control_type
targeted_benchmark_artifact
target_label
sample_stem_or_group
expected_mapping_status
actual_mapping_status
expected_decision
actual_decision
source_feature_family_id
precursor_mz_delta_ppm
product_mz_delta_ppm
observed_loss_delta_ppm
rt_delta_sec
tag_match_status
failure_reason
```

Add a schema parity test that compares this list with the controls spec contract
or a single shared schema definition used by both docs and implementation.

### Required `summary.md` Sections

- command and mode;
- inline pre-Backfill input source, or explicit reason post-hoc run is
  comparison-only;
- input hashes and row counts;
- control manifest path and control mapping counts;
- evidence firewall assertion `promotion_used_forbidden_evidence = false` and
  `forbidden_evidence_seen` counts;
- seed gate counts and seed specificity context distributions;
- RT-only candidate counts;
- independent trace identity pass counts by tier;
- diagnostic-NL-supported sample counts;
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
- process-mode payload boundary is pickleable;
- per-sample evidence surface is frozen;
- controls output is machine-readable;
- `controls.tsv` schema is frozen in this file and parity-checked against the
  controls spec;
- base Go/No-Go table owns firewall, weak-basis, infrastructure, and cost
  criteria;
- decision enum values are sourced from the core spec or a shared schema, not a
  second independent list;
- every `cell_evidence.tsv` row has pre-Backfill provenance keys;
- request counters separate identity from optional downstream audit cost.
