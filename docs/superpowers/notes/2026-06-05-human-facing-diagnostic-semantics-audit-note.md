# Human-Facing Diagnostic Semantics Audit Note

Date: 2026-06-05

## Verdict

The visual diagnostics are not uniformly wrong, but several human-facing
surfaces still present legacy container identity (`feature_family_id`) as if it
were the review identity. That is the main source of confusion. Family-level
plots remain useful as context for ordinary single-mode rows, but they must not
be the only review surface when a family can contain multiple selected-apex
modes or multiple PeakHypothesis candidates.

The current target direction is:

- Final downstream matrix identity: `Mz` / `RT` / sample columns.
- Internal product identity sidecar: `peak_hypothesis_id`.
- Legacy family identity: provenance/debug/context only.
- MS1 visual shape: prefer Gaussian15-smoothed trace display for human review,
  with raw/selected/global apex markers preserved when they explain a conflict.

## Human Review Invariants

Every human-facing diagnostic plot, gallery, or report that can influence a
selection/backfill/presence decision should disclose these fields when the
inputs provide them:

| Field | Required meaning |
| --- | --- |
| `review_identity` | `peak_hypothesis_id` when available; otherwise `Mz` / `RT` + target/sample context. |
| `source_feature_family_ids` | Provenance only, never the row identity by itself. |
| `row_identity_basis` | Explicitly says `no_split_peak_hypothesis`, `mode_level`, projection, or unavailable. |
| `active_identity_status` | Present after active gate, removed by active gate, or not supplied. |
| `signal_rendering_source` | Gaussian15-smoothed MS1, raw XIC, AsLS residual, or mixed. |
| `decision_authority` | Product-affecting, review-only, diagnostic-only, or legacy/debug. |

## Surface Audit

| Surface | Current value | Main semantic issue | Disposition |
| --- | --- | --- | --- |
| `selected_envelope_plot_review.py` | Still useful for targeted boundary/window review; already draws Gaussian15 morphology and active interval. | Mostly target/sample keyed, not family-keyed. Needs clear active-vs-legacy boundary legend where overlays stack heavily. | Keep; improve contrast/legend separately. |
| `target_pair_rt_candidate_plot_review.py` | Useful targeted RT candidate plot; draws Gaussian15 morphology. | Should keep target-pair scope explicit and avoid implying targeted truth mutates untargeted identity. | Keep. |
| `family_ms1_overlay_plot.py` / `family_ms1_overlay_batch.py` | Useful family-context plot for single-mode cases and broad MS1 shape sanity checks. | Uses `feature_family_id` as the visible primary identity. Can hide multi-mode / competing-apex cases. | Keep as context-only; add identity disclaimer and pair with mode-aware review when identity sidecars exist. |
| `changed_row_mode_overlay_review.py` | New changed-row review surface that reads family overlay trace JSONs and projects raw selected-apex modes / PeakHypothesis review rows. | RAW-overlay modes are not typed iRT; the quick similarity badge is human triage, not product authority. | Keep; current 2026-06-05 output now uses Gaussian15-smoothed plot traces plus review-only shape/drift/MS1-pattern badges. |
| `qc_ms1_pattern_reference.py` | Useful QC-local MS1 pattern sidecar from overlay trace JSONs. | Still keyed by family/sample because the overlay producer is family-level. | Keep; add PeakHypothesis context when sidecar inputs are available. |
| `family_ms1_backfill_review_report.py` / `seed_aware_backfill_review.py` / low-coverage review tools | Useful queue builders for finding rows that need human review. | Queue identity is family-centric and can be mistaken for final row identity. | Keep as queue/context; outputs should carry `peak_hypothesis_id` / identity sidecar columns when possible. |
| `alignment_decision_report.py` | Useful high-level HTML report. | Report rows still expose family IDs heavily; product readiness can be confused with observability. | Keep; add identity-basis and readiness labels more prominently. |
| `single_dr_production_gate_decision_report.py` | Product-adjacent gate report for single-dR backfill risk. | Must display matrix identity sidecar status and changed-row manual-review status, not just legacy family row IDs. | Keep; align with changed-row mode-aware review links. |
| `targeted_evidence_review_report.py` / targeted benchmark reports | Useful targeted benchmark/review surfaces. | Targeted labels and family matches are benchmark evidence, not untargeted row identity authority. | Keep; label benchmark-only authority explicitly. |
| `peak_candidate_score_calibration_report.py` | Legacy score-calibration surface. | Score is retired from product authority; report can create old-score gravity. | Retire or relabel as compatibility/debug only. |
| `area_integration_uncertainty_audit.py` and older area reports | Useful historical audit evidence. | Some outputs look gate-like but are not currently read by product decisions. | Review separately: promote to product gate or mark review-only. |

## Immediate Changes From This Pass

- `changed_row_mode_overlay_review.py` now draws mode-colored MS1 traces using
  Gaussian15 smoothing while preserving selected-cell and global-trace apex
  markers.
- The 39-row mode-aware changed-row gallery was regenerated at
  `output/backfill_evidence_gate_8raw_20260605/changed_row_mode_overlay_review_20260605/mode_aware_review_gallery.html`.
- The same run writes `changed_row_similarity_review.tsv` and
  `changed_row_similarity_summary.tsv`. These combine Gaussian15-smoothed
  selected-mode shape similarity, global-apex conflict, matrix RT drift policy,
  and optional MS1 pattern sidecar facts into review-only quick badges.
- The 8RAW review queue now has 312 sample-level quick badges: 136
  `shape_coherent_review_only`, 70 `review_required_wrong_apex_risk`, 46
  `review_required_multimodal_family`, 34
  `review_required_partial_similarity`, 18
  `review_required_inconclusive_similarity`, and 8
  `review_required_shape_conflict`.
- The diagnostic index now states that this mode-aware PNG surface is
  Gaussian15-smoothed, mode-aware, and review-only.
- The regenerated gallery now uses a review-first layout: global
  similarity summary, per-family score cards, colored risk badges, the
  mode-aware plot as the primary visual, legacy family overlay in a collapsible
  context panel, and a horizontally scrollable sample evidence table with
  explicit `shape similarity`, `quick score`, and `drift status` columns.

## Repo Skill Candidate: Visual Review Gallery

This pass suggests a reusable repo-local gallery pattern, but it should become a
skill only after at least one more diagnostic surface adopts it successfully.

- Put the human review decision first: queue size, global badge distribution,
  median shape similarity, and median quick score.
- Keep the active/new semantics as the primary plot; put legacy context in a
  collapsible panel so it stays available without dominating the screen.
- Use color only for review state: coherent/supportive, partial/inconclusive,
  and wrong-apex/conflict.
- Keep precise evidence in TSVs and tables; use HTML cards only to guide visual
  triage.
- Every visual score must say whether it is product authority, review-only, or
  diagnostic-only.

## Recommended Refactor Backlog

1. Add a shared `HumanReviewIdentity` adapter for diagnostic tools.
   Inputs: `alignment_matrix_identity.tsv`, optional
   `activation_hypothesis_identity.tsv`, optional changed-row bundle.
   Output fields: `review_identity`, `peak_hypothesis_id`,
   `source_feature_family_ids`, `row_identity_basis`, `active_identity_status`.

2. Add a shared `SignalRenderingDisclosure` helper for plots.
   At minimum each plot index should disclose whether traces are raw XIC,
   AsLS residual, Gaussian15-smoothed residual, or mixed.

3. Update family overlay plots to say “family context/provenance” in titles and
   index rows. Do not remove them; they remain useful when the family is
   single-mode.

4. Update single-dR reports to link family overlay, mode-aware overlay, and the
   review-only quick-similarity TSV side by side. The family plot answers "does
   this group look coherent?"; the mode plot answers "is this family secretly
   multiple review identities?"; the similarity TSV answers "which samples can
   be reviewed first because shape, drift, and apex evidence agree?".

5. Retire or relabel score-era reports that still make `raw_score`,
   `support_labels`, or `feature_family_id` feel authoritative for current
   product decisions.

## Stop Rule

Do not convert every diagnostic tool in one sweep. Convert first the surfaces
that a human is likely to use for product-affecting backfill, boundary, or
presence decisions:

1. changed-row review galleries,
2. single-dR gate reports,
3. family MS1 overlay batch,
4. selected-envelope boundary gallery,
5. targeted benchmark review reports.

Everything else can stay context-only until it is used to justify a product
decision.
