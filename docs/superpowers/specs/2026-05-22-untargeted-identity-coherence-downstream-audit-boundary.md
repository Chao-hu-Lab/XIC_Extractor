# Untargeted Identity Coherence Downstream Audit Boundary

**Date:** 2026-05-22
**Status:** Split review draft v0.4

This spec defines what the identity prototype does not own. It depends on:

- [Overview](2026-05-22-untargeted-identity-coherence-prototype-spec.md)
- [Core identity spec](2026-05-22-untargeted-identity-coherence-core-spec.md)

## Boundary

Background / blank / QC behavior is useful audit context, but it is not an
identity-promotion gate in v0.4.

The identity prototype may emit audit fields, but those fields must not:

- change `decision`;
- change coherent counts;
- change per-cell identity basis;
- change matrix inclusion;
- change area values;
- change Backfill behavior;
- change statistical eligibility.

## Non-Gating Background Recurrence Audit

Optional audit status:

```text
background_audit_status =
  not_assessed | no_background_signal_observed | background_signal_observed
```

Optional audit inputs:

- process blanks or solvent blanks;
- QC pools or repeated stable samples;
- sample order / injection order;
- per-cell area or height for assessed samples;
- sample-vs-blank area ratio;
- blank detection count and blank detection fraction;
- QC CV or equivalent repeatability measure.

Optional audit flags:

```text
blank_signal_detected
sample_blank_ratio_low
qc_cv_high
carryover_or_run_order_signal
```

If these fields exist, they are validation context only. They cannot create a
`review_only_*` identity decision.

## Contaminant Consequence

A contaminant can be a real chromatographic feature with coherent RT, shape,
and signal. If it passes the identity-family evidence defined by the core spec,
it may become `would_primary_provisional_identity_family_support`.

That is a design consequence, not an identity diagnostic failure.

Whether that row belongs in the final matrix is a downstream filtering, area
correction, normalization, and statistics decision.

## Downstream Scope

Downstream owns:

- final-matrix feature filtering based on blank abundance, QC CV, biological
  missingness, cohort design, or statistical model needs;
- contaminant filtering;
- area correction;
- normalization;
- imputation;
- batch correction;
- abundance transformation;
- final statistical eligibility.

Identity output is an upstream input to those decisions. Downstream outputs must
not feed back into identity promotion.

## Split Rule

If background/QC handling grows beyond the audit fields above, split it into a
separate downstream validation spec. That spec must run after identity
coherence, and it must not be implemented before the identity prototype.

## Reference Note

Schiffman et al. 2019 documents common QC CV cutoffs, blank fold-change
filtering, and the need for data-adaptive filtering in untargeted LC-MS
metabolomics:

- <https://doi.org/10.1186/s12859-019-2871-9>

This supports the boundary: background/QC filtering is a downstream analytical
decision, not an identity-family formation gate.
