# Sidecar To Product Label Activation Contract

## Verdict

`shared_peak_identity_*` sidecars are now treated as activation inputs, not as
more evidence to collect. Product activation means an explicit contract decides
whether a sidecar status may change the formal label, promotion, or backfill
result.

This phase does not silently mutate `alignment_matrix.tsv`. It emits an
activation decision sidecar first, then an explicit product output mode may
consume only `auto_activate` / `auto_block` rows after the 85RAW acceptance gate
passes.

The explicit bridge is
`tools/diagnostics/apply_shared_peak_identity_activation.py`. It consumes a
passing activation sidecar and writes product TSVs. `--output-mode formal`
writes the formal downstream contract names: `alignment_matrix.tsv`,
`alignment_review.tsv`, and `alignment_cells.tsv`. The default
`--output-mode activated-copy` keeps the prior `_activated.tsv` review-copy
surface. Formal mode refuses to overwrite source alignment artifacts unless an
operator explicitly passes `--allow-overwrite-source`.

Formal matrix identity is now `peak_hypothesis_id`. `feature_family_id` is
retained as provenance and as the current candidate-container id, but it is no
longer treated as the product identity key in formal output. This does not mean
every legacy family must be split. When no split, wrong-peak, or mode-level
evidence exists, the bridge emits a deterministic
`<feature_family_id>::family_projection` row with
`row_identity_basis=family_projection_no_split_evidence`. A large number of
family-projection rows is therefore acceptable for a bridge/projection output,
but it is a blocker for claiming complete canonical row identity; it means the
existing family consolidation has no current evidence requiring a finer product
unit.

The activation application summary makes this scope explicit:
`canonical_row_identity_ready=FALSE`,
`canonical_row_identity_blockers=family_projection_present`,
`canonical_row_identity_scope=partial_peak_hypothesis_with_family_projections`,
`family_projection_semantics=projection_not_split_proof`, and
`all_family_split_science_ready=FALSE`. In other words, the formal TSV format
can be produced, but canonical row identity is not complete until projection
rows are removed or explicitly excluded from the production scope.

Legacy FH/MZmine RT-row workbooks may be passed as context-only references via
`--legacy-rt-row-oracle-xlsx`. Those rows can populate
`legacy_rt_row_context_id`, but they do not mint product identities and must not
override the `peak_hypothesis_id` contract. The legacy pipeline may not model
matrix RT drift, iRT, or the current evidence chain, so extra legacy RT rows are
treated as provenance hints rather than authority. When any context rows are
emitted, the summary reports
`legacy_rt_row_context_authority=context_only_not_identity_authority`.

If two provenance families map to the same `peak_hypothesis_id` and the same
sample column has different values, the formal bridge records
`matrix_value_conflict_cells` and currently keeps the larger numeric value under
`matrix_value_conflict_policy=max_area_pending_baseline`. This is a temporary
quantitation policy for the pre-AsLS/baseline checkpoint; it is not an identity
failure when the shared hypothesis is otherwise valid.

## Product Effects

The activation vocabulary is:

- `auto_activate`: machine-observed evidence may change a product label to pass
  or accept a rescue/backfill value.
- `auto_block`: machine-observed evidence may fail closed and block a family
  promotion or rescued cell.
- `confidence_only`: evidence may only demote confidence; it must not change the
  formal label by itself.
- `review_required`: evidence is useful, but product behavior must wait for
  manual review or a stronger machine rule.
- `no_change` / `not_applicable`: no product action.

## Direct Label / Promotion Rules

These sidecar states can directly affect product behavior after the 85RAW
activation gate passes:

- `family_required_tag_gate`: direct fail-closed family-level block. If no sample
  in the family has the required NL/PI evidence, the family should not be routed
  into extra rescue evidence or promoted.
- `wrong_peak_conflict`: direct rescued-cell block. This includes
  `family_ms1_overlay_competing_peak_matches_family_consensus`,
  consensus-backed `qc_ms1_reference_status=conflict`, or an explicit
  `rt_pattern_conflict_gate`. It also includes RT-mode sidecar conflicts where
  the selected/rescued cell belongs to a non-tag outlier mode, a split-required
  mode, or a `consolidation_no_go` family.
- machine-observed sample negative evidence with class
  `no_candidate_ms1_evidence`, `pattern_mismatch`, `rt_not_explained`, or
  `local_peak_not_decisive`: direct rescued-cell block.
- `machine_observed_sufficient` with positive current machine label and
  machine-observed shape + pattern basis: pass/accept candidate.

## Confidence / Review-Only Rules

These states must not change the formal label by themselves:

- `dda_opportunity_policy` missing or
  `dda_missing_nl_policy_status=policy_evidence_missing`: review required.
- `dda_missing_nl_policy_status=not_dispositive` or family tag present while the
  sample lacks the tag: confidence demotion only. DDA stochasticity explains why
  missing NL/PI is not dispositive; it is not a positive label by itself.
- RAW-backed MS1 overlay height can satisfy `intensity_opportunity_metric` when
  selected-cell/local/trace intensity is at least `2.5e4` and the evidence comes
  from `family_ms1_overlay_raw_trace` or the RAW trace-vector basis. This avoids
  requiring a separate Tier 2 trace sidecar to repeat intensity evidence that is
  already present in the MS1 overlay evidence vector.
- `product_outside_diagnostic_window` is not dispositive when the family has a
  required tag/context, the sample has sufficient boundary MS2 trigger
  opportunity, and RAW MS1 evidence is supportive. It records
  `dda_missing_nl_policy_status=not_dispositive`, not a positive label by
  itself.
- matrix RT drift support without complete machine-observed MS1 shape/pattern:
  review required. RT drift can explain timing, but cannot replace the peak
  identity shape/pattern check.
- nearest-QC MS1 reference alone is local instrument-condition evidence, not
  product identity authority. QC evidence may close `formal_pattern_metric` only
  when the sidecar reports a consensus-backed evidence level such as
  `qc_consensus_with_local_qc_overlay` or `qc_consensus_qc_overlay`. A lone
  `nearest_valid_qc_local_condition_only` row remains context/review-only.
  If local QC and broader QC consensus disagree, the result is
  `review_required`, not `auto_activate` or `auto_block`.
- QC consensus conflict is not a standalone veto for a target cell that already
  has sample-level RAW MS1 pattern support. It can support `wrong_peak_conflict`
  only when the sample-level pattern/RT/PeakHypothesis evidence also points to a
  wrong selected peak.
- `tailing_confounded` RT-mode evidence: review/diagnostic only. Broad or
  tailing families such as FAM012114 must not be split or blocked solely because
  iRT makes the selected-apex spread look multimodal.
- unclassified `machine_observed_conflict`: review required until promoted to a
  named direct-block rule.

## 85RAW Activation Acceptance

Activation cannot enter product behavior unless a current 85RAW run produces the
activation decision sidecar and acceptance sidecar from matching source hashes.

Initial acceptance thresholds:

- `blast_radius_current` must be `TRUE`.
- must-not-regress oracle families must pass.
- product-affecting rows are `auto_activate + auto_block`.
- product-affecting rows must be at most 2% of assessed 85RAW rows and at most
  50 rows, whichever is smaller.
- `assessed_rows` must come from the current 85RAW blast-radius summary when
  available: `scope=all_available_85raw`,
  `artifact_id=85raw_alignment_cells`, `assessed_row_count`. The activation
  decision row count is only a fallback for non-blast-radius diagnostic runs and
  must be identified as `activation_decision_rows_fallback`.
- The must-not-regress check should come from a machine-readable expectation TSV
  when available. The current checkpoint fixture is
  `docs/superpowers/fixtures/shared_peak_identity_activation_must_not_regress_v1.tsv`.
  A manual `must_not_regress_status` flag is only a diagnostic fallback.
- The acceptance sidecar must disclose both `activation_decision_scope` and
  row-count bases. For this checkpoint the decision scope is
  `manual_oracle_seed_rows`; passing the acceptance gate means the seed-scope
  activation contract is internally consistent, not that a production writer has
  already mutated 85RAW labels.

Must-not-regress families for this activation checkpoint:

- `FAM000144`: `TumorBC2312` must remain blocked as wrong peak; reviewed
  nearby-pass cells must not become hard fails solely from DDA/low-intensity.
- `FAM000610`: all reviewed cells must not regress from pass/accept candidate.
- `FAM001227`: reviewed OK/suspect cells must not become hard fails; unmentioned
  samples remain fail/review according to scope.
- `FAM001589`: remains not auto-activatable because the human label is
  unjudgeable/shape-bad.
- `FAM001658`: low-intensity supported cells may demote confidence/review, not
  hard fail solely from missing DDA tag.
- `FAM002175`: reviewed all-pass family must not receive hard blocks.
- `FAM011810 / TumorBC2263`: the wrong 6-minute peak must not be accepted.

Hard fail types:

- stale or missing 85RAW activation/blast-radius artifacts;
- schema/version mismatch;
- must-not-regress family violates the expected direction above;
- a direct product label change is driven only by manual-oracle fields;
- any family without required NL/PI evidence is auto-promoted;
- any wrong-peak conflict is auto-accepted;
- any detected row is removed only because RT drift, low intensity, or missing
  DDA NL/PI appeared without the corresponding direct-block rule.

## Outputs

- `shared_peak_identity_activation_decisions.tsv`
- `shared_peak_identity_activation_acceptance.tsv`
- `shared_peak_identity_rt_mode_evidence.tsv` when
  `--generate-rt-mode-evidence` is enabled from selected-apex mode assignment
  artifacts and/or RAW-backed family MS1 overlay trace JSONs.
- `shared_peak_identity_peak_hypothesis_selection.tsv` when
  `--generate-peak-hypothesis-selection` is enabled from RT-mode evidence. This
  legacy producer is diagnostic/review-only for activation-facing authority;
  auto-activation requires a typed mode-hypothesis assignment producer or a
  locked oracle manifest.
- `shared_peak_identity_qc_ms1_pattern_reference.tsv` style inputs must preserve
  the distinction between `local_qc_reference_status` and
  `qc_consensus_status`. `qc_reference_policy` records whether the chosen
  reference is consensus-backed, fallback-valid QC support, mixed review, or
  local-only context.
- `docs/superpowers/fixtures/shared_peak_identity_activation_must_not_regress_v1.tsv`
  defines this checkpoint's must-not-regress expectations.
- In `--output-mode activated-copy`, `alignment_matrix_activated.tsv`,
  `alignment_review_activated.tsv`, and `alignment_cells_activated.tsv` are
  emitted by the explicit application bridge.
- In `--output-mode formal`, `alignment_matrix.tsv`, `alignment_review.tsv`,
  and `alignment_cells.tsv` are emitted as the formal downstream product
  contract files. Formal mode preserves the source public TSV headers for
  `alignment_review.tsv` and `alignment_cells.tsv`; activation audit fields stay
  in activation sidecars so downstream readers do not silently receive a wider
  schema. `alignment_matrix.tsv` uses `peak_hypothesis_id` as the formal row
  identity, keeps `feature_family_id` as provenance, and discloses
  `row_identity_basis` plus optional `legacy_rt_row_context_id`.
- Both modes emit `activation_application_summary.tsv` and
  `activation_value_delta.tsv`.
  `activation_value_delta.tsv` is the human/product-review surface for
  before/after value changes: original matrix value, activated matrix value,
  source cell area, activation effect, `candidate_container_id`,
  `peak_hypothesis_id`, `activation_unit_scope`, and `value_changed`.

The formal output mode is a product output mode, but it is still gate-bound: it
requires a passing activation acceptance sidecar and refuses source overwrite by
default.

## RT-Mode Evidence Boundary

`shared_peak_identity_rt_mode_evidence.tsv` is a diagnostic sidecar that consumes
selected-apex mode assignment artifacts from RAW/iRT overlay diagnostics and,
for coverage, RAW-backed family MS1 overlay trace JSONs. It does not discover
new peaks by itself. Its job is to make the FAM011810 lesson machine-readable:

- iRT can refine mode membership, but it must not collapse multiple real modes
  into one product family.
- `tag_backed_core_with_outlier_modes` means the tag-bearing core may remain a
  product candidate, while non-tag outlier modes must fail closed as
  wrong-peak/rescue conflicts.
- `consolidation_no_go` means the current family consolidation is too mixed for
  product promotion/backfill until a split/reconsolidation contract exists.
- `tailing_confounded` means the family is broad or tailing enough that mode
  assignment is not decisive; it stays review-only.
- `raw_mode_review_only` means RAW-overlay-only mode splitting saw possible
  multimodality, but lacks enough independent iRT/tag support to block product
  activation. It must stay review-only so drift or low-intensity cases such as
  FAM001658 are not hard-failed by raw RT clustering alone.

The sidecar may contribute `rt_basis_status=machine_observed` and may trigger
the activation `wrong_peak_conflict` rule, but it does not replace MS1
shape/pattern evidence, candidate-MS2 tag evidence, or the matrix RT drift
policy.

## PeakHypothesis Selection Boundary

`shared_peak_identity_peak_hypothesis_selection.tsv` is the pre-product bridge
between provisional family consolidation and product activation. It consumes
`shared_peak_identity_rt_mode_evidence.tsv` and makes the product unit explicit:

- `feature_family_id` is a candidate/provenance container key. It identifies
  the provisional family that supplied evidence, but it is not itself product
  identity proof and must not be used as the unit that shares evidence across
  mixed RT modes.
- `peak_hypothesis_id` is the activation candidate unit when a mode-level
  product candidate exists. Downstream activation decisions copy this id into
  `peak_hypothesis_id` and set `activation_unit_scope=peak_hypothesis` before a
  machine rule may accept a pass/rescue.
- `product_unit_scope=candidate_container` means the provisional family is being
  blocked as a container. It does not mint a product identity row and it does not
  retarget cells into another peak.
- `product_candidate_core` means the selected RT/iRT mode is the candidate
  `PeakHypothesis` unit. The family id remains provenance, not proof that every
  cell in the provisional family belongs to the same product feature.
- `cross_mode_rescue_blocked` means the current cell belongs to a non-core mode
  in a tag-backed mixed family. Activation treats this as `wrong_peak_conflict`
  and blocks that rescue cell; it does not retarget to another peak.
- `mode_split_required` and `consolidation_no_go` block family promotion until
  a mode-aware consolidation/reconsolidation contract creates product-level
  families.
- `tailing_review_only` stays review-only because broad/tailing peak shape can
  make mode assignment look worse after iRT normalization.
- `raw_mode_review_only` stays review-only because raw overlay mode splitting is
  a hypothesis source, not an independent RT drift correction or product
  retargeting rule. This review-only state takes precedence over
  `wrong_peak_conflict`: raw/overlay-only mode evidence may explain why a row is
  suspicious, but it must not auto-block or auto-activate a product cell until a
  typed mode assignment or locked oracle manifest supplies product-facing
  authority.

This checkpoint deliberately does not edit `primary_consolidation.py` yet. It
turns the FAM011810 lesson into a machine-readable activation input first, so a
future consolidation change can be tested against an explicit expected
PeakHypothesis surface instead of relying on after-the-fact retargeting.

Activation decision rows therefore carry both layers:

- `candidate_container_id`: currently the same value as `feature_family_id`,
  retained for provenance and legacy matrix application.
- `peak_hypothesis_id`: the selected mode-level product candidate id when the
  selection sidecar supplies one.
- `activation_unit_scope`: `peak_hypothesis`, `sample_cell`,
  `candidate_container`, `legacy_family_row`, or `not_applicable`.

`auto_activate` requires `activation_unit_scope=peak_hypothesis` in this
checkpoint. A positive machine row without a `peak_hypothesis_id` is demoted to
`review_required` with `contract_rule_id=peak_hypothesis_unit_required`, because
`feature_family_id` is provenance only and must not become an implicit product
identity unit.

The sentinel acceptance fixture for this boundary is
`docs/superpowers/fixtures/shared_peak_identity_mode_window_assignment_contract_v0.tsv`.
`tools/diagnostics/evaluate_mode_window_assignment_contract.py` evaluates it
against 85RAW sidecars and writes
`shared_peak_identity_mode_window_assignment_gate.tsv` plus
`shared_peak_identity_mode_window_assignment_summary.tsv`. Gate v0 is considered
passing only when the expected `peak_hypothesis_id`, `product_unit_scope`,
`selected_mode_id`, activation `peak_hypothesis_id`, and
`activation_unit_scope` also match. Status/action labels alone are not enough,
because a legacy or raw-overlay producer could otherwise fake the same terminal
vocabulary without proving that both selection and activation point at the same
product-facing PeakHypothesis identity. When a fixture row names MS1, QC, RT,
MS2, or tag evidence in `required_evidence_oracle`, the gate must also receive
matching sidecar rows; otherwise the row is `not_assessed` rather than silently
passing.
The sentinel criteria are:

- typed FAM011810 core rows remain product candidates and the typed wrong-peak
  row remains blocked;
- raw/overlay-only rows such as FAM001473, FAM002625, and FAM005937 remain
  review-only, even when other MS1/QC conflict evidence exists;
- QC local-vs-consensus and ISTD phase/trend evidence are present as context,
  not standalone product identity rules;
- any matrix that still has family projection rows reports
  `canonical_row_identity_ready=FALSE` with a non-empty blocker.

Current scoped acceptance is the refreshed 85RAW gate output at
`output/mode_window_assignment_contract_gate_v0_85raw_refreshed/`, not the older
failed sibling directory. Its summary is accepted only as
`sentinel_mode_window_assignment_contract_v0`: `10` fixture rows pass, `0` fail,
and `0` are not assessed. The same summary intentionally keeps
`canonical_row_identity_ready=FALSE`,
`canonical_row_identity_blockers=matrix_construction_blocked`, and
`diagnostic_only=TRUE`; the passing gate therefore closes the typed assignment
contract, but it is not evidence that product activation or full canonical
matrix row identity is ready.

The activation refresh artifact at
`output/mode_window_assignment_contract_gate_v0_85raw_activation_refresh/` is not
an acceptance artifact for product wiring: its
`shared_peak_identity_activation_acceptance.tsv` reports
`acceptance_status=fail` because the current must-not-regress manifest still
expects several rows that are now held at `review_required` by the raw-mode
review-only boundary. That failure is deliberate protection, not a blocker for
the scoped Mode-Window Assignment Gate.

The legacy review vocabulary (`production_family`, `audit_family`) may still
appear in current matrix/review outputs because it is part of the historical
public TSV surface. In this contract it means "legacy matrix row accepted or
audited", not "the provisional family has been proven to be one product
identity".

## Wrong-Peak Root-Cause Diagnostic Boundary

`wrong_peak_conflict` is product-active as a block, not as an automatic retarget.
The correct next diagnostic is to explain why the selected/rescued cell was
wrong and whether RAW overlay evidence contains a plausible alternate peak.

The diagnostic tool is
`tools/diagnostics/diagnose_shared_peak_wrong_peak.py`. It consumes:

- `shared_peak_identity_activation_decisions.tsv`
- `shared_peak_identity_machine_evidence_support.tsv`
- the source `alignment_cells.tsv`
- optional `family_ms1_overlay_*` trace-data JSON files with `rt` and
  `intensity` arrays

It emits `shared_peak_identity_wrong_peak_root_cause.tsv` with:

- the direct block row and selected-cell evidence;
- root-cause class, such as family-consensus conflict, QC-reference conflict,
  low selected-peak dominance, or MS2 pattern conflict;
- selection failure mode, such as duplicate owner peak claim or low local
  dominance;
- the strongest alternate local maximum outside the selected boundary, when the
  overlay trace can support one;
- `recommended_next_action`, normally
  `inspect_alternate_peak_before_retarget` rather than direct retargeting.

This sidecar is `diagnostic_only`. It must not rewrite selected peaks, mutate
activation decisions, or fill a blocked product cell until a separate retarget
contract defines candidate scoring, blast-radius rules, and regression gates.

## Current 85RAW Representative Run

The diagnostic run at
`output/sidecar_to_product_label_activation_85raw/` uses the current 85RAW
blast-radius artifacts and the wrong-peak / DDA policy sidecars. Its activation
acceptance sidecar reports:

- `blast_radius_current=TRUE`
- `activation_decision_scope=manual_oracle_seed_rows`
- `decision_rows_total=11`
- `assessed_rows=1854020`
- `assessed_rows_basis=blast_radius_summary:all_available_85raw:assessed_row_count`
- `product_affecting_rows=5`
- `auto_activate_count=3`
- `auto_block_count=2`
- `review_required_count=5`
- `must_not_regress_basis=activation_must_not_regress_tsv`
- `acceptance_status=pass`

The two direct blocks are wrong-peak conflicts, including
`FAM011810 / TumorBC2263_DNA`. The three direct activations are the rows where
machine-observed RT, shape, and pattern are sufficient. This run supports the
activation contract, while the separate V2 readiness sidecar still correctly
reports `diagnostic_only` because it is an evidence-readiness sidecar, not the
formal product-output application artifact.

Applied to the current 85RAW alignment outputs, the bridge should blank two
wrong-peak rescue cells and leave the three already-primary auto-activate cells
unchanged unless the source matrix is missing those values.

The applied 85RAW formal-output run at
`output/peak_hypothesis_canonical_matrix_probe_85raw_v3/` is now a stale
pre-tightening artifact for canonical readiness wording. If regenerated under
the current contract, its row-basis distribution should still be interpreted as
partial:

- `activation_output_mode=formal`
- `matrix_row_identity=peak_hypothesis_id`
- `canonical_row_identity_ready=FALSE`
- `canonical_row_identity_blockers=family_projection_present`
- `canonical_row_identity_scope=partial_peak_hypothesis_with_family_projections`
- `family_projection_semantics=projection_not_split_proof`
- `legacy_rt_row_context_authority=not_applicable`
- `all_family_split_science_ready=FALSE`
- `input_matrix_rows=610`
- `output_matrix_rows=613`
- `family_projection_rows=610`
- `legacy_rt_row_context_rows=0`
- `matrix_cells_blanked=2`
- `matrix_cells_written=0`
- row-basis distribution: `activation_peak_hypothesis=3` and
  `family_projection_no_split_evidence=610`

The matching context-only MZmine workbook probe at
`output/peak_hypothesis_canonical_matrix_probe_85raw_with_mzmine_context_v3/`
keeps the same row-basis distribution and reports
`legacy_rt_row_context_rows=418` and
`legacy_rt_row_context_authority=context_only_not_identity_authority`. This
confirms the legacy RT-row workbook is being retained as context without
changing product row identity.
