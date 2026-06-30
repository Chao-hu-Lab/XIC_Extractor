# Target Pair RT Auto-Reselection Spec

Doc placement: repo_subcontract_doc
Doc kind: spec
Doc lifecycle: active
Repo owner: docs/product/targeted-selection.md
Doc exit rule: Retire or convert to support after target-pair RT reselection authority, expected-diff gates, and production-ready row-specific behavior are represented in docs/product/targeted-selection.md.

**Date:** 2026-06-03
**Status:** Draft v0.7 - row-specific expected-diff approval is production-ready for BC1055/8-oxodG; full candidate-switch promotion still gated
**Readiness label:** `row_specific_expected_diff_production_ready`; paired-anchor projection is `production_ready` via the targeted evidence-chain alignment spec; broad Phase 3 candidate switching remains `blocked_until_expected_diff_and_transfer_gate`
**Primary surface:** targeted extraction product selection
**Related specs:** [Targeted evidence-chain alignment](retired-provenance:d762b1a67888), [Selected full-envelope quantitation boundary](2026-06-03-selected-full-envelope-quantitation-boundary-spec.md), [Mature package flow reference](retired-provenance:ebcb7b73c424), [Peak-scoring tiered design](retired-provenance:19b77d0bb466)

## Verdict

Targeted extraction needs one explicit, role-aware peak reselection policy:

```text
target candidate evidence
  + paired ISTD / analyte RT relationship
  + Mix STDs pair-RT calibration
  + selected-envelope conflict evidence
  -> targeted evidence/model selection
  -> PeakModelSelectionResult expected-diff gate
  -> TargetedProductProjection
```

This replaces hidden targeted score authority for cases where the selected peak
is probably the wrong chromatographic event. It does not create a second
resolver, a hard backfill rule, or a label-regex identity system.

Boundary policy can propose conflict evidence such as `context_apex_conflict`,
`wrong_peak_conflict`, split/neighbor evidence, or selected-envelope clipping.
It must not silently change the selected targeted peak. Final targeted
reselection authority belongs to the existing selected-hypothesis model-selection
contract. A product candidate switch must be represented as an approved
`PeakModelSelectionResult(selection_status=expected_diff,
product_switch_allowed=True)` before workbook, matrix, or review outputs can use
the successor candidate.

Expected-diff approvals must reference runtime product candidate IDs:
`PeakHypothesis.hypothesis_id` values emitted by the product candidate
enumeration. Review-only overlays, projected plot rows, or
`peak_candidates.tsv` markers whose proposal-source identity differs from the
runtime hypothesis may support the evidence summary, but they must not be copied
as `legacy_selected_candidate_id` or `successor_selected_candidate_id`. If an
approval points to a successor ID that is not present in the current runtime
hypotheses, product selection must fail closed.

Without that expected-diff approval, this spec authorizes only shadow proposals,
blocked reasons, and review artifacts. With a matching expected-diff approval,
the only Phase 3-A product behavior now allowed is a role-gated targeted switch:
ISTD and paired Analyte rows may use the approved successor candidate, while
unpaired analytes stay on the legacy-selected candidate.

2026-06-04 clarification: targeted product projection can now count a paired
analyte as `detected_flagged` when the already-selected candidate has complete
same-sample paired-ISTD anchor support. That anchor must be the paired ISTD's
credible selected MS1 `reported_rt`, not a window/NL anchor. This is not a
`target_pair_rt_auto_reselection` candidate switch. A switch from
legacy-selected candidate to a successor candidate still needs the explicit
expected-diff approval and calibration gates below.

2026-06-04 production update: the `BenignfatBC1055_DNA / 8-oxodG`
row-specific expected-diff approval is production-ready after an 8RAW validation
rerun. The approval registry contains exactly that row, the final workbook uses
the successor right-side peak (`RT=17.1355`, `Area=1850221.22`), and the
target-pair review summary reports `product_switch_allowed_true_count=1`,
`auto_reselected_count=1`, and `product_switch_accepted_count=1`. This promotes
only that explicit approved row. Other expected-diff or row-approval candidates
remain shadow/review-only until they receive their own approval evidence.

2026-06-04 public-surface update: product workbooks must present product
semantics first. `Product State`, `Counted Detection`, `Review State`, and
projection-backed `Reason` are the visible decision surface. Legacy
`Confidence`, score, and cap fields are technical audit evidence only; they must
not drive Review Queue status, Summary visible health metrics, counted
detection, or row-specific product-switch authority.

## Why This Spec Exists

The targeted evidence-chain alignment already retired the older product behavior
where `NL_FAIL`, score caps, or confidence labels directly decided `detected`
versus `ND`.

That fixed a real ISTD false-negative class, but it left another product gap:

```text
the row may now count the right kind of evidence,
but still anchor to the wrong peak when MS2/NL or boundary/resolver evidence
points away from the true paired RT neighborhood.
```

The concrete domain example is targeted-only:

- A paired ISTD is stable, strong, and externally added.
- Its paired analyte should usually be evaluated near the paired RT relationship,
  not near a distant random DDA/NL event.
- Missing DDA MS2/NL evidence is usually `not_observed` unless acquisition
  opportunity proves it should have been observed.
- If the analyte has no complete MS1 peak, the ISTD must not hard-backfill a
  false positive.

The product problem is therefore not "score this peak higher." The product
problem is:

```text
When the selected targeted candidate has conflict evidence,
can a better complete MS1 candidate near the paired RT relation replace it?
```

## Current Code Facts

Current target configuration is intentionally simple:

```text
label,mz,rt_min,rt_max,ppm_tol,neutral_loss_da,nl_ppm_warn,nl_ppm_max,is_istd,istd_pair
```

The runtime `Target` model currently exposes only:

- `label`;
- `mz`;
- `rt_min` / `rt_max`;
- `ppm_tol`;
- neutral-loss thresholds;
- `is_istd`;
- `istd_pair`.

There is no public `STD` role in targeted output. In this spec, "STD" means a
clean external standard or paired target context from the chemistry discussion.
The product role remains either:

- `ISTD`;
- `Analyte`.

There is also no target-product isotope parser today. Strings such as
`d3-N6-medA`, `d3-5-medC`, `[13C...]`, or `15N...` are currently labels, not
typed product semantics.

Existing `rt_prior_library` already stores RT priors with fields such as
`median_delta_rt` and is consumed by the legacy scoring-context path. This spec
does not ignore that surface. It turns pair RT into typed targeted evidence and
defines a migration path away from hidden score weighting.

## Product Story

The intended product data flow is:

```text
Mix STDs / clean standard runs
  -> instrument_qc_mixstds_trend.tsv
  -> target_pair_rt_calibration.tsv
  -> targeted extraction evidence context
  -> shadow auto-reselection proposal
  -> biological-transfer / changed-row gate
  -> expected-diff approval registry
  -> guarded product auto-reselection
  -> TargetedProductProjection / workbook / matrix / review report
```

Target extraction must not directly rescan Mix STDs RAW files during normal
targeted runs. Clean-standard calibration is an input artifact, not a hidden
runtime side process.

## Target Metadata Contract

Target config may add optional metadata columns:

| Column | Values | Meaning |
|---|---|---|
| `isotope_label_type` | `deuterated`, `heavy_non_deuterium`, `unknown`, blank | Explicit label chemistry used for RT-direction evidence. |
| `paired_rt_relation` | `istd_not_later_than_pair`, `learned_delta_only`, `none`, blank | How the paired ISTD RT should relate to the paired target when calibration is weak. |

Rules:

- Missing columns keep backward compatibility and default to
  `isotope_label_type=unknown`, `paired_rt_relation=none`.
- `isotope_label_type` is owned by ISTD rows. Non-ISTD rows may leave it blank;
  a nonblank non-ISTD value is diagnostic metadata only unless a future spec
  assigns it product meaning.
- `paired_rt_relation` is owned by paired Analyte rows, because those rows name
  `istd_pair`. ISTD rows must leave it blank. A paired Analyte row can use
  `istd_not_later_than_pair` only when the paired ISTD row has
  `isotope_label_type=deuterated`.
- Regex over target labels is not a product rule. A diagnostic may suggest
  metadata for labels like `d3-*`, but product behavior must be driven by the
  explicit config metadata or calibration artifact.
- `deuterated` means the ISTD is expected to be not later than the paired target
  on the C18 behavior assumed by this project. It may be earlier. A materially
  later deuterated ISTD is conflict/review evidence unless a learned calibration
  row explicitly supports it.
- `heavy_non_deuterium` has no deuterium RT-direction rule. Use learned delta or
  fallback tolerance only.
- `learned_delta_only` disables isotope-direction fallback and requires usable
  calibration before role-aware auto-reselection can activate.

## Pair RT Calibration Artifact

Add a standalone calibration artifact:

```text
target_pair_rt_calibration.tsv
```

Required fields:

| Field | Meaning |
|---|---|
| `schema_version` | Artifact schema version, initially `target_pair_rt_calibration_v1`. |
| `target_config_hash` | Hash of the target config used to build the row. |
| `source_artifact` | Source file or upstream artifact name. |
| `source_hash` | Hash of the calibration source artifact when available. |
| `source_hash_status` | `present`, `missing`, or `mismatch`. |
| `target_label` | Target/analyte label being selected. |
| `paired_istd_label` | Paired ISTD label from target config. |
| `pair_rt_delta_min` | Observed or learned `target_rt - istd_rt`. |
| `delta_source` | `mixstds_clean_standard`, `biological_high_confidence`, or `config_fallback`. |
| `point_count` | Number of calibration observations. |
| `rt_delta_median_min` | Robust median delta. |
| `rt_delta_mad_min` | Robust MAD or blank when unavailable. |
| `rt_delta_direction` | `target_later`, `target_earlier`, or `near_zero`. |
| `isotope_label_type` | Copied/normalized target metadata. |
| `paired_rt_relation` | Copied/normalized target metadata. |
| `calibration_status` | `usable`, `insufficient`, `conflicting`, or `review_only`. |
| `calibration_level` | `clean_standard_only`, `biological_transfer`, `row_approved`, or `config_only`. |
| `product_transfer_status` | `not_assessed`, `validated`, `row_approved`, or `blocked`. |

`target_config_hash` is a target-only hash, not the existing run-level
`config_hash`. Phase 1 must add or name an owner such as
`xic_extractor/configuration/hashing.py::compute_target_config_hash(targets_csv)`.
It must exclude settings values, `target_pair_rt_calibration_path`, output paths,
and other runtime-only settings so the calibration artifact does not invalidate
itself by changing where it is loaded from. Schema tests must lock this
include/exclude behavior.

`calibration_status=usable` means the row can support shadow or review evidence.
It is not sufficient by itself for product auto-reselection.

`review_only`, `conflicting`, and `insufficient` rows may emit evidence,
warnings, or review labels. They must not select a different product peak.

`config_fallback` is allowed only when there is no learned row and the target
metadata explicitly permits a fallback relation. It must be named in audit
output and treated as review-only for Phase 3 unless the row has a matching
approved expected-diff record.

Mix STDs / clean-standard rows are instrument and reference evidence. They can
support Phase 1/2 shadow decisions. They cannot alone authorize biological-matrix
product reselection. Phase 3 requires one of:

- `product_transfer_status=validated`, backed by current biological matrix
  changed-row gates; or
- `product_transfer_status=row_approved`, backed by a row-specific approved
  expected-diff record.

## Runtime Ingestion And Ownership

The runtime ingestion surface is a public contract:

- add an optional advanced setting key `target_pair_rt_calibration_path`;
- default blank means disabled;
- no hard-coded default calibration path is allowed;
- target extraction reads the artifact through package code, not
  `tools/diagnostics/`;
- source/schema/hash mismatches block product activation and may still emit
  diagnostics.

Target metadata belongs to `xic_extractor/configuration/*` and the GUI target
import/export surface. Phase 1 must either make the GUI preserve the optional
columns exactly or explicitly mark the GUI as no-edit/pass-through for these
columns. Silently dropping the metadata is a contract failure.

The product activation path also requires the existing
`model_selection_expected_diff_approval_registry` when a candidate switch changes
selected RT, selected area, boundary, workbook detection, or matrix value.

## Relationship To Existing RT Prior Library

`rt_prior_library` is a useful existing source of RT knowledge, but in current
code it is wired into the scoring context. That makes it too easy for pair RT to
act as a hidden score weight rather than an auditable selection reason.

The product-facing path is `target_pair_rt_calibration_path`.
`rt_prior_library` may be adapted into that artifact during Phase 1, or retained
as developer/debug input, but it must not remain a second product candidate
selection authority.

The migration must satisfy these rules:

- pair RT evidence is surfaced as typed support/conflict/review reasons;
- pair RT does not directly mutate `Confidence`, `Score`, or legacy cap fields;
- workbook and matrix detection use `TargetedProductProjection`, not hidden
  scoring thresholds;
- tests prove old score/cap fields are evidence-only after migration.
- when product activation is enabled, scoring-context RT priors must be disabled,
  adapter-only, or proven by tests not to affect final selected candidate
  authority independently from model selection.

## Selection Authority Contract

Auto-reselection is not a new targeted-only product mutator.

Every product candidate switch must flow through:

```text
candidate enumeration
  -> complete candidate evidence comparison
  -> PeakModelSelectionResult(selection_status=expected_diff)
  -> ExpectedDiffApprovalRecord
  -> product_switch_allowed=True
  -> TargetedProductProjection renders the selected result
```

Rules:

- If `product_switch_allowed=False`, workbook and matrix outputs keep the legacy
  selected candidate and emit only `shadow_auto_reselect_proposed` or
  `auto_reselect_blocked`.
- If no matching `ExpectedDiffApprovalRecord` exists, product output stays on the
  legacy selected candidate.
- If alternate-candidate evidence is incomplete, the model-selection result is
  `inconclusive` or `blocked_diff`, not `expected_diff`.
- Any expected diff that relies on MS2/NL evidence must use
  `evidence_comparison_policy=complete_candidate_evidence`.
- Selected-envelope and boundary diagnostics are conflict or support evidence
  only. They cannot make a positive candidate switch while the selected-envelope
  gate is still externalized.
- `TargetedProductProjection` owns counted detection and product state after the
  selected candidate is chosen; it does not choose the candidate by itself.

## Auto-Reselection Scope

Auto-reselection is allowed only for:

- `ISTD`;
- paired `Analyte` rows where `istd_pair` points to a credible ISTD in the same
  sample.

Auto-reselection is not allowed for:

- unpaired `Analyte`;
- rows without a complete MS1 alternate peak;
- rows where the paired ISTD is missing, ambiguous, or itself under unresolved
  conflict;
- calibration rows that are `review_only`, `insufficient`, or `conflicting`;
- split/neighbor cases where two plausible peaks remain unresolved.
- rows without an approved expected-diff path when selected RT/area/boundary or
  product presence would change.

The paired ISTD is credible only when all are true:

- product state is counted or would be counted after the ISTD role policy;
- positive, complete MS1 peak evidence exists;
- no unresolved `wrong_peak_conflict`, `context_apex_conflict`,
  `overmerge_rejected`, or split-supported conflict remains;
- paired RT metadata/calibration is not contradicted.

## Trigger Rule

Do not auto-reselect simply because another candidate has larger area, smoother
Gaussian15 morphology, or an NL/MS2 event somewhere else.

Phase 2 shadow diagnostics may promote a different review successor with
`selection_basis` suffixed by `chrom_morphology_area_ratio` only when all of the
following are true:

- the row is already an `expected_diff` paired-analyte comparison;
- the current model-selection successor differs from the legacy candidate;
- the alternate candidate has `chrom_peak_segment` / Gaussian15 morphology
  evidence for a complete peak shape;
- the alternate candidate has no hard morphology contraindication such as
  `rt_prior_far`, `rt_centrality_poor`, `rt_window_cap`,
  `trace_quality_cap`, `hard_quality_flag_cap`, `low_scan_support`,
  `poor_edge_recovery`, `edge_clipped`, `too_short`, or `low_scan_count`;
- the alternate candidate / paired ISTD area ratio falls inside the
  leave-one-sample-out target/ISTD reference range;
- the selected area still comes from raw/AsLS integration over the candidate
  interval, not from the smoothed Gaussian15 trace.

This is a targeted-only shadow candidate-selection rule. It must not expand
`parity`, `inconclusive`, or `blocked_diff` rows into new review deltas.
Untargeted may later learn the same morphology-as-hypothesis strategy, but only
through its own hypothesis/evidence contract, not by importing targeted
target/ISTD labels or target-pair area ratios.

Manual review update, 2026-06-04: the first 85RAW
`chrom_morphology_area_ratio` review gallery produced confirmed false positives:
plot ranks 1, 3, 5, and 7 selected the wrong peak, while ranks 17 and 18 should
not select any peak. The durable review oracle is
`docs/superpowers/fixtures/target_pair_chrom_morphology_area_ratio_manual_oracle_v1.tsv`.
Therefore the old min/max `paired_area_ratio_status=within_reference_range`
was not a sufficient positive gate by itself; that reference range can be too
wide and can admit both wrong-apex switches and tiny rescue peaks. Active
paired-area support now uses the robust leave-one-out median +/- 3 scaled MAD
projection (`within_robust_range` / `outside_robust_range`). Product switching
still remains blocked unless the expected-diff registry and row-level
manual/review oracle accept the changed row.

Target/sample applicability update, 2026-06-04: `8-oxo-Guo` is an RNA-standard
target in this tissue-85RAW context. It should be detectable in RNA-containing
samples. In the current 85RAW set, the RNA-containing rows are the
`BC2304`/`BC2286` `DNAandRNA` samples; the other 83 pure DNA samples should not
be rescued or counted for `8-oxo-Guo` by paired ISTD, Gaussian15 morphology,
CWT, area ratio, or missing-MS2 reasoning. This is a target applicability hard
gate, not a score/confidence adjustment. The paired ISTD remains useful for
interpreting RNA-containing rows, and the `NL R` tag is strong RNA-related
evidence, but neither must authorize a pure-DNA product detection for the
RNA-standard analyte.

Auto-reselection can be considered only when the currently selected candidate
has explicit conflict evidence, such as:

- `paired_rt_conflict`;
- `wrong_peak_conflict`;
- `context_apex_conflict`;
- `split_supported`;
- `overmerge_rejected`;
- `selected_envelope_narrower_than_resolver`;
- malformed boundary, too few scans, or invalid selected envelope;
- target-specific NL/MS2 anchor far from the paired ISTD RT neighborhood.

If the current candidate is `detected_clean`, do not switch it.

If the current candidate is `detected_flagged`, switch only when the flag is a
selection conflict, not when it is a harmless audit note such as plausible DDA
dropout.

## Alternate Candidate Completeness

An alternate candidate is selectable only when it has complete MS1 peak evidence.
Use existing local evidence first; avoid new dead constants.

Required evidence:

- candidate apex and area are finite and positive;
- selected boundary is not malformed and not too narrow for configured
  `resolver_min_scans` / selected-envelope minimum scan support;
- candidate-level MS2/NL evidence has been hydrated for the alternate candidate,
  or the row is explicitly marked `inconclusive` / `limited_evidence_shadow`;
- local S/N and trace continuity are acceptable under existing evidence
  semantics;
- Gaussian15 or named morphology trace supports a single integrable peak shape;
- no stronger neighboring apex or unresolved split evidence remains;
- candidate RT is supported by usable pair RT calibration for shadow/review, or
  by the weaker explicit fallback relation when calibration is absent. Fallback
  relation remains shadow/review-only unless Phase 3 has row-specific expected
  diff approval.

Disallowed evidence shortcuts:

- single spike with no complete peak shape;
- only an ISTD peak with no analyte MS1 peak;
- NL tag without paired RT support;
- area increase alone;
- label-derived isotope assumption without explicit metadata.

## Role Policy

### ISTD

ISTD rows have the widest detection policy because they are externally added and
should be stable.

An ISTD may be counted as `detected_flagged` when:

- complete MS1 peak evidence is present;
- RT evidence is reasonable or calibration-supported;
- missing NL/MS2 is best explained as `not_observed` or plausible DDA dropout;
- no hard conflict remains.

Missing NL/MS2 must be recorded as evidence, not erased.

### Paired Analyte

Paired analytes are more conservative.

A paired analyte may be counted after auto-reselection only when:

- the paired ISTD is credible in the same sample;
- the analyte has its own complete MS1 peak;
- usable pair RT calibration plus biological-transfer or row-approval evidence
  supports the selected candidate;
- missing NL/MS2 is non-dispositive, not contradicted;
- no split, neighbor, or wrong-peak conflict remains;
- an approved expected-diff record permits product switching when selected RT,
  area, boundary, workbook detection, or matrix value changes.

Fallback relations and Mix STDs-only calibration can support review visibility
and shadow proposals. They cannot by themselves count a paired Analyte after
auto-reselection.

For paired analytes whose paired ISTD is `deuterated`:

- the target/analyte candidate may be later than the ISTD;
- the target/analyte candidate should not be materially earlier than the ISTD
  unless learned calibration supports that exception;
- learned delta dominates isotope-direction fallback.

### Unpaired Analyte

Unpaired analytes do not get auto-reselection. They may emit review evidence,
but product selection remains conservative until a separate contract defines an
unpaired-target policy.

## Audit Trail Contract

Every shadow or product auto-reselection event must emit stable audit fields in
machine-readable diagnostics.

The Phase 2 owner artifact is:

```text
target_pair_rt_auto_reselection.tsv
```

It is written under the extraction output directory next to candidate and
selected-envelope diagnostics when `target_pair_rt_calibration_path` is
configured. Its package owner should be a writer/model under
`xic_extractor/output/` or `xic_extractor/peak_detection/`; diagnostic tools and
workbook/report renderers may consume it, but must not recompute the selection
decision.

Required fields:

| Field | Required meaning |
|---|---|
| `sample_name` | Sample/file row identity. |
| `target_label` | Target row identity. |
| `role` | `ISTD` or `Analyte` as rendered by targeted output. |
| `trace_group_id` | Join key to selected-hypothesis / model-selection diagnostics when available. |
| `previous_candidate_id` | Candidate id before shadow/product reselection. |
| `selected_candidate_id` | Proposed or final successor candidate id. |
| `selection_action` | `none`, `shadow_auto_reselect_proposed`, `auto_reselected`, or `auto_reselect_blocked`. |
| `selection_basis` | Stable reason, e.g. `paired_rt_calibration_ms1_complete`; Phase 2 shadow rows may append `chrom_morphology_area_ratio` when Gaussian15 morphology and paired area-ratio evidence choose a better review successor. |
| `selection_status` | Model-selection status such as `expected_diff`, `blocked_diff`, or `inconclusive`. |
| `product_switch_allowed` | Boolean result from the expected-diff gate. |
| `expected_diff_stable_row_id` | Stable row id for the approval registry when applicable. |
| `evidence_comparison_policy` | `complete_candidate_evidence` or `limited_evidence_shadow`. |
| `previous_candidate_rt` | RT of previous selected candidate. |
| `selected_candidate_rt` | RT of proposed/final candidate. |
| `paired_istd_rt` | Same-sample paired ISTD RT when applicable. |
| `pair_rt_delta_expected` | Expected `target_rt - istd_rt`. |
| `pair_rt_delta_observed` | Observed `selected_candidate_rt - paired_istd_rt`. |
| `pair_rt_delta_error` | Observed minus expected delta. |
| `paired_area_ratio_observed` | Candidate area divided by same-sample paired ISTD area when applicable. |
| `paired_area_ratio_reference_n` | Leave-one-sample-out reference count for the target/ISTD area ratio, seeded from counted target detections only. |
| `paired_area_ratio_reference_min` | Minimum counted leave-one-sample-out reference ratio. |
| `paired_area_ratio_reference_median` | Median counted leave-one-sample-out reference ratio. |
| `paired_area_ratio_reference_max` | Maximum counted leave-one-sample-out reference ratio. |
| `paired_area_ratio_status` | Active robust status: `within_robust_range`, `outside_robust_range`, `inconclusive`, or missing-data status. |
| `paired_area_ratio_basis` | Stable basis for the active paired area-ratio calculation: `leave_one_sample_out_median_plus_minus_3_scaled_mad_area_over_istd_area`. |
| `paired_area_ratio_robust_status` | Same active robust comparator status, retained under the robust-prefixed field for schema compatibility. |
| `paired_area_ratio_robust_reference_min` | Active median-minus-3-scaled-MAD lower bound for the target/ISTD area ratio. |
| `paired_area_ratio_robust_reference_median` | Active robust reference median for the target/ISTD area ratio. |
| `paired_area_ratio_robust_reference_max` | Active median-plus-3-scaled-MAD upper bound for the target/ISTD area ratio. |
| `paired_area_ratio_robust_reference_mad` | Active median absolute deviation before scaled-MAD multiplication. |
| `paired_area_ratio_robust_basis` | Stable basis for the robust comparator; matches the active paired area-ratio basis. |
| `calibration_source` | Source from calibration artifact. |
| `calibration_status` | Calibration status used by the decision. |
| `missing_ms2_explanation` | `not_observed`, `dda_dropout_plausible`, `contradicted`, or blank. |
| `role_policy` | `istd`, `paired_analyte`, or `unpaired_analyte`. |
| `gate_decision` | `promote`, `no_go`, `externalize`, or `defer`. |
| `block_reason` | Stable reason when reselection is blocked. |
| `false_positive_review_status` | `row_approval_candidate`, `false_positive_review_required`, `product_switch_accepted`, or `not_applicable`. |
| `false_positive_review_reasons` | Semicolon-separated review reasons such as `paired_area_ratio:outside_robust_range`, `ms2_nl_contradicted`, or `row_specific_expected_diff_required`. |

The old selected candidate must remain inspectable during shadow and changed-row
review. Product activation may change selected RT/area, but must not erase the
previous selection from diagnostics.

## Phase Plan

### Phase 1 - Metadata And Calibration Artifact

Goal:

```text
Make pair RT knowledge explicit and auditable before changing product behavior.
```

Work:

- add optional target metadata fields to parser/model/config examples and GUI
  preservation/no-edit policy;
- validate enum values and backward-compatible missing-column behavior;
- add `target_pair_rt_calibration_path` as the only runtime ingestion setting;
- add a producer or adapter for `target_pair_rt_calibration.tsv` from Mix STDs /
  clean-standard trend output or existing RT prior rows, including schema
  version and source/config hashes;
- add or name the target-only hash owner and tests for the hash include/exclude
  contract;
- document that target extraction consumes the calibration artifact but does not
  run Mix STDs RAW.
- define how `rt_prior_library` is disabled, adapted, or made audit-only when
  product activation is enabled.

Done when:

- schema tests cover optional columns and invalid enum values;
- artifact schema tests cover every required field;
- hash tests prove `target_config_hash` changes with target metadata and does
  not change only because the calibration path or other settings changed;
- GUI/import/export tests preserve hidden metadata fields or enforce hidden
  no-edit/pass-through behavior; they must not reject, rewrite, or drop fields;
- `rt_prior_library` migration/adaptation path is implemented as a single
  authority fence;
- no product selected peak changes yet.

### Phase 2 - Shadow Auto-Reselection

Goal:

```text
Prove which rows would change, why, and whether false positives appear.
```

Work:

- read the calibration artifact into targeted evidence context;
- hydrate alternate-candidate evidence before evaluating product-switch
  eligibility;
- emit `shadow_auto_reselect_proposed` / `auto_reselect_blocked` diagnostics;
- write `target_pair_rt_auto_reselection.tsv` with the audit fields from this
  spec;
- generate changed-row review tables and overlay plots for sentinel rows;
- keep workbook and matrix product values unchanged.

Done when:

- sentinel cases show the expected proposed selection, including the 16-minute
  `8-oxodG` target case when complete MS1 and pair RT support exist;
- `d3-5-medC` and `d3-N6-medA` remain compatible with the ISTD dropout policy;
- changed-row review surfaces can identify false-positive risks;
- rows without complete analyte MS1 peaks are blocked, not backfilled.
- incomplete alternate evidence is labeled `limited_evidence_shadow` or
  `inconclusive`, not promotion-ready.
- summary counts report `limited_evidence_shadow`, `inconclusive`,
  `blocked_diff`, and `shadow_auto_reselect_proposed` rows.
- schema/join tests prove `target_pair_rt_auto_reselection.tsv` can join back to
  targeted rows, `peak_candidates.tsv`, and selected-envelope/model-selection
  diagnostics through the required identity fields.

### Phase 3 - Guarded Product Activation

Goal:

```text
Promote only the shadow behavior that survives pair RT, MS1 completeness,
and conflict gates.
```

Work:

- enable product auto-reselection for ISTD and paired Analyte only;
- route every candidate switch through `PeakModelSelectionResult` and an
  approved expected-diff registry row;
- project selected RT/area through `TargetedProductProjection`;
- keep old score/cap/NL fields as evidence-only audit fields;
- add regression gates for sentinel rows and no-leak public contract surfaces.

Done when:

- workbook, summary, matrix, and review report consume the same product
  projection;
- selected candidate changes are explainable by stable audit fields;
- unpaired analytes and incomplete paired analytes cannot be auto-promoted;
- targeted product tests prove score/cap/NL cannot override the projection;
- Mix STDs-only and config fallback rows cannot produce `auto_reselected`
  without biological-transfer validation or row-specific expected-diff approval.

Implementation update, 2026-06-04:

- Phase 3-A is implemented only as the minimal guarded activation surface:
  existing `PeakModelSelectionResult(product_switch_allowed=True)` can select the
  successor targeted hypothesis, but targeted extraction now blocks that product
  switch for unpaired analytes and paired analytes without same-sample credible
  paired ISTD RT evidence.
- `target_pair_rt_auto_reselection.tsv` can now report `selection_action=
  auto_reselected` and `product_switch_allowed=TRUE`, but only when the row is
  already product-approved by model selection and the calibration row has product
  transfer support (`biological_transfer` / `row_approved` and
  `validated` / `row_approved`).
- Clean-standard-only, `config_fallback`, non-row-approved Mix STDs,
  hash-mismatched, non-usable, missing-paired-ISTD, or unpaired rows remain
  blocked or shadow-only.
- This does not complete full Phase 3 production readiness. The targeted
  benchmark, sentinel overlays, changed-row review, and wider RAW gates below
  still decide whether the policy can be promoted broadly.
- 2026-06-04 targeted projection validation closed the narrower paired-anchor
  `detected_flagged` policy: 3RAW sentinel and 85RAW default-target outputs pass
  in `output/target_pair_rt_production_ready_20260604/full_85raw_after_anchor_source_fix/`.
  This closes the product-projection gap for already-selected paired analyte
  candidates, but not the broader candidate-switch gate governed by this
  auto-reselection spec.

## Validation And Acceptance

Minimum acceptance before Phase 3 promotion:

- focused unit/schema tests for metadata, calibration artifact, role gates, and
  audit fields;
- targeted default-target benchmark using `config/targets.example.csv` with
  unchanged settings;
- 2RAW fail-fast sentinel gate before any wider RAW run;
- 8RAW shadow changed-row gate with `changed_row_denominator`, false-positive
  strata, old/new selected candidate RT, pair delta error, and missing-MS2
  opportunity class;
- full default-target tissue gate before claiming production readiness for
  product activation;
- sentinel checks for:
  - `TumorBC2289_DNA / d3-5-medC`;
  - `TumorBC2258_DNA / d3-N6-medA`;
  - `TumorBC2263_DNA / 8-oxodG` selecting the 16-minute candidate only when its
    complete MS1 and paired RT evidence support it;
- changed-row review for analytes whose detected count changes relative to the
  current targeted branch;
- overlay plots for area decreases, wrong-peak corrections, and blocked
  false-positive candidates;
- reviewer signoff that changed rows are not merely score-threshold drift.
- machine-readable `gate_decision=promote|no_go|externalize|defer` for every
  changed or blocked candidate-switch row.

Old workbooks using linear-edge area are reference artifacts, not hard area
gates. They may identify changed rows and suspicious decreases, but AsLS
selected-envelope behavior must be judged by boundary/peak evidence and plots.

Overlay plots and false-positive watch tables are review surfaces. They are not
the product oracle unless the row also has complete candidate evidence,
biological-transfer or row-approval support, and an approved expected-diff gate.
When plot overlays or `peak_candidates.tsv` selected markers disagree with the
runtime product hypothesis ID, the approval must be authored from the product
model-selection row ID and may cite the overlay only as supporting evidence.

## Exit Rules

Promote to product only if:

- Phase 2 shadow changes explain the wrong-peak cases without broad false
  positives;
- pair RT calibration is explicit, usable, and auditable;
- biological-transfer validation or row-specific expected-diff approval supports
  every product candidate switch;
- every product switch has `product_switch_allowed=True`;
- every product changed row has `selection_action` and old/new candidate RT
  evidence;
- no hidden score/cap authority remains in targeted product detection.

Kill or keep diagnostic-only if:

- Mix STDs calibration is too sparse to support real target pairs;
- fallback metadata produces too many false-positive analyte shadow proposals;
- selected-envelope/boundary conflicts cannot distinguish full peaks from
  neighboring peaks;
- auto-reselection cannot be explained with stable audit fields.
- alternate candidate MS2/NL evidence cannot be hydrated enough to compare
  candidates fairly.

Externalize to manual review if:

- two plausible peaks remain after pair RT and morphology evidence;
- the paired ISTD is itself ambiguous;
- learned calibration conflicts with isotope-direction fallback;
- the row needs a target-specific chemistry exception not encoded in metadata.

## Non-Goals

This spec does not:

- add a public `STD` role to target output;
- infer isotope chemistry from label regex as product behavior;
- make smoothed area the final matrix value;
- re-enable linear-edge area comparison as a product gate;
- make ISTD presence sufficient to backfill a missing analyte;
- allow Mix STDs-only or config-fallback rows to switch product candidates
  without biological-transfer validation or expected-diff approval;
- change untargeted matrix identity rules directly;
- require 85RAW production validation before Phase 2 shadow diagnostics.

## Self Review

Verdict after xhigh review: this spec is no longer an immediate
implementation-goal contract for Phase 3. It is suitable for Phase 1 public
contract work and Phase 2 shadow diagnostics. Product activation remains blocked
until expected-diff candidate switching and biological-transfer gates are
implemented and passed.

Strongest assumption: Mix STDs / clean-standard evidence can provide enough
pair RT coverage for shadow diagnostics. If coverage is sparse, product
activation must stay limited to row-specific expected-diff approvals or remain
diagnostic-only.

Public-contract risk: adding optional target metadata columns touches target CSV
schema, config examples, GUI targets table, workbook diagnostics, and tests.
Backward-compatible missing-column behavior is mandatory.

Validation risk: apparent analyte count increases are not automatically good.
Changed rows need false-positive review, especially when NL/MS2 support is
missing and pair RT is the main support.

Implementation-contract risk: the current `rt_prior_library` and
`build_scoring_context_factory` already apply RT priors through scoring. The
migration must prevent pair RT from being maintained twice as both score weight
and product evidence.

Subagent blockers resolved in this draft:

- product switching is bound to `PeakModelSelectionResult` expected-diff
  approval;
- alternate candidates require complete evidence hydration or stay shadow-only;
- Mix STDs-only and config fallback cannot directly switch biological-matrix
  product candidates;
- runtime ingestion, metadata ownership, GUI preservation, and audit fields are
  explicit public-contract surfaces;
- `target_config_hash` has a target-only owner contract and
  `target_pair_rt_auto_reselection.tsv` is the Phase 2 audit artifact;
- sentinel label is corrected to `8-oxodG`.

Smallest safe start: implement Phase 1 metadata parsing, GUI preservation, and
calibration artifact schema/adapter first; then add Phase 2 shadow diagnostics.
Do not implement Phase 3 product mutation from this spec until the gate artifacts
exist.
