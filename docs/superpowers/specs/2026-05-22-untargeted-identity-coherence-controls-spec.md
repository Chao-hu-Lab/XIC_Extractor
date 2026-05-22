# Untargeted Identity Coherence Controls Spec

**Date:** 2026-05-22
**Status:** Split review draft v0.4

This spec defines validation controls for the identity prototype. It depends on:

- [Overview](2026-05-22-untargeted-identity-coherence-prototype-spec.md)
- [Core identity spec](2026-05-22-untargeted-identity-coherence-core-spec.md)
- [Implementation contract](2026-05-22-untargeted-identity-coherence-implementation-contract.md)

## Purpose

Controls validate the identity diagnostic. They do not promote identities.

V0.4 needs both:

- positive controls for sensitivity;
- identity decoys for specificity against false identity promotion.

Background / blank / QC negative controls are downstream-facing audit
yardsticks, not identity-promotion gates.

## Manifest

The control set must be declared before interpreting an 8RAW result:

```text
identity_coherence_controls_manifest.tsv
identity_coherence_controls_manifest.yml
```

Required manifest fields:

```text
control_id
control_type
control_name
expected_mapping_status
control_expected_behavior
fragment_observation_mode
precursor_tolerance_ppm
product_tolerance_ppm
cid_observed_loss_tolerance_ppm
rt_tolerance_sec
required_failure_reason_when_missed
```

`control_type` enum:

```text
positive_targeted_istd
identity_decoy
```

Downstream blank/QC/background controls must not be encoded as identity
controls. They belong to downstream audit specs.

## Positive Controls

Positive controls test identity-diagnostic sensitivity.

Allowed positive-control sources:

- targeted ISTD benchmark output from existing diagnostics;
- selected stable-like ISTD or targeted control rows mapped to untargeted
  candidate families.

Positive-control labels are validation-only evidence. They must not change
`decision`, coherent counts, per-cell identity basis, or any promotion gate.

Expected outcomes:

- pass the seed coherence gate where applicable;
- pass tiered trace identity checks;
- if not promoted, emit a specific failure reason.

## Identity Decoys

Identity decoys test whether the method promotes constructed false identity
requests. This is in scope because the identity layer is responsible for
false independent feature suppression.

Minimum V0.4 `identity_decoy` generation methods:

### `rt_shift`

Clone a real seed/control request, then replace the seed input field
`best_seed_rt` with:

```text
decoy_best_seed_rt = original_best_seed_rt + preferred_rt_sec + seed_center_candidate_sec
```

The original owner peak boundaries and candidate identity constraints remain
unchanged. The decoy is run through the same seed gate as a normal request.
Because the shifted seed RT should fall outside the original owner peak
boundaries, the expected failure is `seed_rt_outside_owner_peak` before
cross-sample XIC retrieval.

Expected outcome:

- not `would_primary_provisional_identity_family_support`;
- likely `review_only_seed_gate_failed`.

### `mz_shift`

Clone a real seed/control request, then replace the seed identity constraints
with:

```text
decoy_precursor_mz = original_precursor_mz shifted outside precursor tolerance
decoy_product_mz = original_product_mz shifted outside product tolerance
```

Keep RT, owner geometry, and provenance unchanged. The decoy is run through the
same seed gate as a normal request. Preserving `candidate_id` is allowed only to
exercise the core request-vs-candidate identity consistency gate; the original
candidate must not override or satisfy the shifted m/z request.

Expected outcome:

- `request_identity_completeness_status = complete`;
- `request_candidate_identity_status = request_candidate_identity_mismatch`;
- seed gate fails with `request_candidate_identity_mismatch`, or all non-seed
  cells fail the decoy identity constraints before promotion;
- no would-primary promotion.

### `fragment_tag_shuffle`

Clone a real seed/control request, then replace the seed identity constraints
with:

```text
decoy_fragment_tags = stable tag set not supported by the source DiscoveryCandidate
decoy_cid_observed_loss_da = corresponding declared loss, if available
```

Keep RT, owner geometry, and provenance unchanged. The decoy is run through the
same seed gate as a normal request. Preserving `candidate_id` is allowed only to
exercise the core request-vs-candidate identity consistency gate; the original
candidate must not override or satisfy the shuffled fragment tag set.

Expected outcome:

- `request_identity_completeness_status = complete`;
- `request_candidate_identity_status = request_candidate_identity_mismatch`;
- seed gate fails with `request_candidate_identity_mismatch`, or all non-seed
  cells fail the decoy identity constraints before promotion;
- no would-primary promotion.

Decoys must be generated from pre-Backfill identity inputs and must not read
post-Backfill outputs, workbook outputs, final matrix inclusion, blank/QC
filters, or downstream audit results.

Decoy evaluation rule: if the decoy request identity does not match the joined
candidate, the decoy must fail the seed gate and must not continue into tier 2
shape promotion using the original seed identity. Shape similarity can only
support a decoy if the decoy identity constraints first pass the same seed gate
and per-cell identity constraints as a real request. This prevents an
m/z-shifted or fragment-shuffled false identity from being rescued by unchanged
chromatographic shape.

Any `identity_decoy` control that becomes
`would_primary_provisional_identity_family_support` is an identity-layer No-Go.

## Controls TSV

Required `untargeted_identity_coherence_controls.tsv` columns:

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

Control mapping must report:

- `mapped`;
- `unmapped`;
- `ambiguous_mapping`;
- targeted label;
- candidate family id;
- precursor/product/loss deltas;
- RT delta;
- fragment tag match status.

## Identity Control-Specific Go / No-Go

The implementation contract owns base engineering Go/No-Go rules. Identity
controls add these control-specific rules:

| Observation after 8RAW | Decision |
| --- | --- |
| `positive_control_pass_fraction >= positive_control_min_pass_fraction` and every miss has an explicit acceptable reason | Proceed to 85RAW threshold-policy review. |
| `positive_control_pass_fraction < positive_control_min_pass_fraction` | No-Go; add trace identity metrics or fix mapping before continuing. |
| `decoy_promoted_count <= max_decoy_promoted_count` | Proceed; constructed false identities were not over-promoted. |
| `decoy_promoted_count > max_decoy_promoted_count` | No-Go; the identity layer is promoting constructed false identities. |
| Every audited decoy failure maps to its expected seed-gate or request-candidate identity mismatch reason | Proceed. |
| Any audited decoy fails for an unexpected or unauditable reason | Pivot; fix decoy generation or seed-gate audit before interpreting specificity. |
| Decoy mapping is ambiguous or cannot be audited | Pivot; fix control mapping before using decoy results. |

Background / blank / QC negative controls must not appear in identity Go/No-Go.

## Learning Ladder

1. First 8RAW identity mechanics run:
   - seed gate;
   - tiered trace checks;
   - positive controls;
   - at least one identity decoy;
   - evidence firewall;
   - identity cost counters.
2. Optional downstream validation/audit run:
   - blank/QC/order inputs;
   - downstream negative blank/background yardsticks;
   - consumes identity outputs and cannot rewrite identity decisions.
3. 85RAW identity expansion:
   - reviewed count+fraction policy;
   - identity request-budget ceiling;
   - positive controls and identity decoys still pass.

## Review Questions

1. Which targeted ISTD/stable rows should seed the first 8RAW positive controls?
2. Which decoy type is cheapest and most informative for the first 8RAW run?
3. Should the first run require one decoy total, or one decoy per high-value
   control family?
4. What failure reasons are acceptable for positive controls that do not promote?
