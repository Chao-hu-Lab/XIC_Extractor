# Product Authority Reconciliation v1 Implementation Addendum

> Historical authority-hygiene addendum as of 2026-06-18. Keep for provenance
> and prior validation context. The productization control plane is the current
> authority source for tier, active lane, and writer authority.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for code changes. This plan is intentionally narrow: close active product-authority leaks first, then add exit-rule diagnostics for scientific policy changes.

**Goal:** Product outputs must not be decided by stale legacy score/fallback semantics when typed projection/evidence is required.

**Architecture:** Keep compatibility readers and debug projections available, but make active workbook/config/product paths fail closed when typed projection or canonical defaults are missing. Scientific policy changes remain diagnostic until their evidence can promote, kill, or externalize.

**Tech Stack:** Python, pytest, existing `xic_extractor.output`, `xic_extractor.configuration`, and targeted diagnostics.

---

## Authority Table

| Area | Source | Legacy Equivalent | Selection Usage | Projection Usage | Tests | Disposition |
| --- | --- | --- | --- | --- | --- | --- |
| Workbook long-row product state | `xic_results_long.csv` with `Product State` + `Counted Detection` | Wide `xic_results.csv` inferred row | None | Primary public workbook and summary authority | `tests/test_csv_to_excel.py` | Active; fail closed if absent |
| Wide CSV compatibility rows | `xic_results.csv` | `_wide_to_long_rows` fabricated `Confidence=HIGH` | None | Debug/compat only, no product projection | `tests/test_csv_to_excel.py` | Legacy projection only; no fake confidence |
| Resolver default | `settings_schema.CANONICAL_SETTINGS_DEFAULTS["resolver_mode"]` | `ExtractionConfig.resolver_mode="legacy_savgol"` | Active peak finding route | Metadata/config authority | `tests/test_config.py`, resolver tests | Active default becomes `region_first_safe_merge` |
| Missing config resolver fallback | `getattr(config, "resolver_mode", canonical)` | `getattr(..., "legacy_savgol")` | Active route only for malformed/manual config objects | N/A | resolver tests | Canonical fallback |
| VERY_LOW / review-only evidence | `TargetedProductProjection` + typed semantics | legacy score confidence label | Must not directly select or count | Public projection only | existing targeted projection tests; future expected-diff gate | Pending policy reconciliation |
| Paired area ratio | `paired_area_ratio_projection` | leave-one-out min/max band | Active dropout review/support gate uses leave-one-sample-out median +/- 3 scaled MAD. | Public evidence reason uses `within_robust_range` / `outside_robust_range`; min/max remains reference-only. | `tests/test_paired_area_ratio_projection.py`, `tests/test_target_pair_rt_auto_reselection.py` | Active robust typed gate; min/max retired from authority |
| Gaussian15 final area | Gaussian-smoothed positive AsLS residual, default window 15 | raw/AsLS area fields and shadow morphology area | Candidate morphology/boundary support | Primary targeted/alignment area authority | diagnostic ledger + 85RAW closeout; `gaussian15_area_pressure_audit.py` pressure surface | `production_ready` owner with configured-window provenance and scan-rate pressure audit required for cross-batch claims |
| Gaussian15 fixed-point pressure | `tools/diagnostics/gaussian15_area_pressure_audit.py` | ad hoc raw-vs-smoothed spot checks | None | Observes raw/Gaussian area ratio and estimated smoothing duration from candidate table window provenance. | `tests/test_gaussian15_area_pressure_audit.py` | `diagnostic_only`; no product mutation |
| Owner backfill scalar fallback | `owner.selected_integration` else scalar legacy integration | `alignment_owner_scalar_legacy` | Fail-closed when no Gaussian15 morphology area | Matrix output must stay Gaussian15-only | `alignment_primary_area_authority_audit.py` | Diagnostic trigger-rate audit; non-Gaussian primary area is fail |
| Region verdict / area uncertainty adoption | `RegionSelectionDecision.product_action`, `area_integration_uncertainty_audit.py` | shadow TSV verdicts treated as implied gates | Only adjacent-WIS `safe_merge_eligible` can change product boundaries in this mainline. | Other verdicts and area uncertainty are review/diagnostic surfaces. | `tests/test_region_model_selection.py` | `behavior_change_required` or `diagnostic_only` until a future oracle promotes/kills |
| Untargeted final matrix identity | `alignment_matrix.tsv` as `Mz` / `RT` / sample columns plus hypothesis identity sidecar | FamilyID-keyed matrix or direct `peak_hypothesis_id` matrix | Product decisions may use `peak_hypothesis_id`; `feature_family_id` is provenance/debug only | Downstream matrix remains coordinate/sample format; hypothesis mapping is sidecar/audit | `tests/test_untargeted_final_matrix_contract.py`, `tests/test_shared_peak_identity_product_activation.py` | Active contract correction; FamilyID owner retired from downstream authority |

## Stop Rule

This addendum may reach `production_candidate` for product-authority hygiene after
no-RAW tests pass. It does not reopen untargeted backfill/pre-backfill
consolidation in this mainline. Gaussian15 area production authority is inherited
from the diagnostic ledger/85RAW closeout, and the new pressure audit makes
raw-vs-Gaussian and configured-window scan-rate sensitivity observable before broader
`production_ready` claims. Paired-ratio robust policy is now the active typed
target-pair gate; row-level expected-diff approval and manual EIC/MS2 review
still decide whether a changed targeted row can be product-switched.

## Mainline Validation Snapshot, 2026-06-05

- No-RAW product-authority shard: 226 tests passed.
- Ruff and package mypy passed.
- 8RAW Gaussian15 pressure artifact:
  `output/gaussian15_ms1_morphology_8raw_20260605/targeted_validation/gaussian15_area_pressure_audit_mainline_20260605/`.
- 8RAW pressure summary:
  - `candidate_row_count=211`
  - `selected_candidate_count=96`
  - `median_gaussian_to_raw_ratio=0.978415`
  - `p95_gaussian_to_raw_ratio=1.489969`
  - `selected_large_area_delta_count=0`
  - selected rows outside 20% but not large: 3 rows
  - `fixed_window_wide_count=163`; selected rows with wide fixed-point window: 86

Verdict: the mainline code path is `production_candidate` after no-RAW
verification. The 8RAW area ratio evidence supports continuing with Gaussian15
area as product owner for this branch, but the configured-window scan-rate
pressure is not closed enough to call the broader cross-batch method
`production_ready` without follow-up validation or a reviewed
scan-rate-aware/configured smoothing policy.

## Matrix Identity Correction, 2026-06-05

Downstream final matrices must stay in `Mz` / `RT` / sample-column form.
`peak_hypothesis_id` is the internal product identity for split-aware evidence
and gate application, but it belongs in an identity/provenance sidecar rather
than replacing the public matrix schema. For no-split successor groups the
product identity comes from `group_hypothesis_id`; `feature_family_id` is
explicitly retired as a product row owner because family-level grouping can
merge distinct MS1 peaks and distort matrix truth.

Main product writer correction: explicit child `PeakHypothesis` rows supplied by
the alignment matrix object are emitted as independent public `Mz` / `RT` /
sample rows with matching `alignment_matrix_identity.tsv` rows only when each
child has a non-empty `peak_hypothesis_id`, exactly one
`source_feature_family_id`, and the children form a total/unique assignment of
the parent accepted product cells. Attempts to collapse multiple families into
the same `peak_hypothesis_id` now fail closed in both the main writer and the
formal activation bridge.

Formal activation bridge correction: public `Mz` / `RT` matrices with an
identity sidecar are reloaded by product `peak_hypothesis_id`, not by
`feature_family_id`, so two split rows can share one source family without
overwriting each other. Unresolved `family_projection` rows are excluded from
formal product-shaped outputs by default and are available only through explicit
diagnostic opt-in.
