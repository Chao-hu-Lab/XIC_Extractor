# Resolver Default Switch Real-Data Validation Note

> Historical validation note: retained as evidence/provenance, not live
> source-of-truth. Current rerun policy and stable P2-entry gate summary live in
> `docs/diagnostic-ledger.md`; product tier and matrix authority live in the
> active control plane, status index, and authority manifest. Removal or
> private-note migration requires an explicit removal approval plus a
> repo-self-contained referrer pass.

**Date:** 2026-05-24
**Branch:** codex/peak-pipeline-modernization
**Worktree:** .worktrees/peak-pipeline-modernization
**Gate status:** production_candidate

## Decision

- Current verdict after 2026-05-25 hotfix evidence-chain continuation,
  reviewed-controls rerun, and pre-change identity-family comparison:
  P1 is GO for P2 entry at `production_candidate` strength. This is an 8RAW
  method / P2-entry decision only; it is not 85RAW-cleared or
  `production_ready`.
- P1 default switch decision after hotfix: GO_FOR_P2_ENTRY
- P1 default switch decision before hotfix: NO-GO
- Reason: `strict_istd_benchmark_new_active_fail`
- Blocking target: `15N5-8-oxodG`
- Blocking evidence: candidate strict ISTD benchmark changed `active_fail_count`
  from `0` to `1` and classified `15N5-8-oxodG` as `FAIL` with
  `AREA_MISMATCH`.

Do not start P2 from the stale pre-hotfix artifact state. The hotfix restored
untargeted alignment production peak picking to `local_minimum` while keeping
`region_first_safe_merge` as audit context for alignment runs. The strict ISTD
blocker is resolved in hotfix artifacts, identity coherence V0.4 acceptance
passes with reviewed controls, and the hotfix-reviewed identity-family decisions
are byte-identical to the pre-change baseline.

## Artifacts

- Targeted local-minimum: `output/phase1_p1_resolver_default_validation/targeted/local_minimum/tissue_8raw_local_minimum/`
- Targeted region-first-safe-merge: `output/phase1_p1_resolver_default_validation/targeted/region_first_safe_merge/tissue_8raw_region_first_safe_merge/`
- Targeted comparison: `output/phase1_p1_resolver_default_validation/diagnostics/targeted_comparison/`
- P1 area/RT gate: `output/phase1_p1_resolver_default_validation/diagnostics/p1_area_rt_gate/`
- Untargeted local-minimum alignment: `output/phase1_p1_resolver_default_validation/alignment/local_minimum/`
- Untargeted region-first-safe-merge alignment: `output/phase1_p1_resolver_default_validation/alignment/region_first_safe_merge/`
- ISTD benchmark local-minimum: `output/phase1_p1_resolver_default_validation/diagnostics/untargeted_istd_benchmark_local_minimum/`
- ISTD benchmark region-first-safe-merge: `output/phase1_p1_resolver_default_validation/diagnostics/untargeted_istd_benchmark_region_first_safe_merge/`
- Hotfix untargeted region-first-safe-merge alignment: `output/phase1_p1_resolver_default_validation/alignment/region_first_safe_merge_hotfix/`
- Hotfix ISTD benchmark region-first-safe-merge: `output/phase1_p1_resolver_default_validation/diagnostics/untargeted_istd_benchmark_region_first_safe_merge_hotfix/`
- Hotfix P1 area/RT gate: `output/phase1_p1_resolver_default_validation/diagnostics/p1_area_rt_gate_hotfix/`
- Hotfix evidence spine consistency, mixed surface:
  `output/phase1_p1_resolver_default_validation/diagnostics/evidence_spine_consistency_hotfix/`
- Hotfix evidence spine production-surface probe:
  `output/phase1_p1_resolver_default_validation/diagnostics/evidence_spine_consistency_surface_probe_targeted_local_vs_hotfix/`
- Region-first audit-surface probe:
  `output/phase1_p1_resolver_default_validation/diagnostics/evidence_spine_consistency_surface_probe_targeted_region_vs_old_region_alignment/`
- Hotfix area integration uncertainty: `output/phase1_p1_resolver_default_validation/diagnostics/area_integration_uncertainty_hotfix/`
- Hotfix identity coherence: `output/phase1_p1_resolver_default_validation/identity_coherence_hotfix/`
- Hotfix reviewed identity coherence: `output/phase1_p1_resolver_default_validation/identity_coherence_hotfix_reviewed/`
- Reviewed controls manifest: `output/phase1_p1_resolver_default_validation/identity_coherence_hotfix/identity_coherence_controls_manifest_8raw.reviewed.tsv`
- Pre-change identity-family baseline: `output/phase1_p1_resolver_default_validation/identity_coherence_prechange/serial/identity_coherence/untargeted_identity_coherence_decisions.tsv`

## Gate Results

| Gate | Result | Evidence |
|---|---|---|
| Targeted 8RAW runs | PASS | `output/phase1_p1_resolver_default_validation/targeted/local_minimum/validation_summary.csv`; `output/phase1_p1_resolver_default_validation/targeted/region_first_safe_merge/validation_summary.csv` |
| Area RSD / RT shift | PASS | `p1_resolver_default_gate_summary.tsv`: `overall_status=PASS`, `failed_count=0`, `max_area_rsd_delta_pct=0.17559`, `max_rt_median_abs_delta_sec=0` |
| Targeted reliability | PASS_WITH_WARNINGS | both reliability audits exited 0; ISTD `targeted_negative_count` regression check passed for 7 ISTDs |
| Safe-merge comparison | PASS_WITH_CHANGES | `changed_rows=10`, `changed_istd_rows=7`, affected labels include `15N5-8-oxodG` and `d3-N6-medA` |
| Untargeted alignment | PASS | both local-minimum and region-first-safe-merge alignment runs exited 0 and wrote matrix, review, cells, and integration audit TSVs |
| Strict ISTD benchmark | FAIL | baseline `active_fail_count=0`; candidate `active_fail_count=1`; new failure `15N5-8-oxodG: AREA_MISMATCH` |
| Evidence spine d3-N6-medA consistency | STOPPED | not run because strict ISTD benchmark already triggered P1 NO-GO |
| Area integration uncertainty | STOPPED | not run because strict ISTD benchmark already triggered P1 NO-GO |
| Identity coherence sidecar parity | STOPPED | not run because strict ISTD benchmark already triggered P1 NO-GO |
| Reviewed controls / decoys | NOT_ASSESSED | no reviewed controls manifest was present during plan review; strict ISTD benchmark failed before this gate |
| Identity-family pre-change count | NOT_ASSESSED | no pre-change identity-family baseline was present during plan review; strict ISTD benchmark failed before this gate |

## Hotfix Recheck

| Check | Result | Evidence |
|---|---|---|
| Alignment production resolver guard | PASS | `tests/test_run_alignment.py::test_run_alignment_cli_defaults_to_local_minimum_production_mode`; `tests/test_run_alignment.py::test_run_alignment_cli_keeps_region_first_safe_merge_out_of_production_mode` |
| 8RAW hotfix alignment | PASS | `output/phase1_p1_resolver_default_validation/alignment/region_first_safe_merge_hotfix/` |
| `15N5-8-oxodG` boundary | PASS | `FAM000538 / NormalBC2312_DNA` returned to `peak_start_rt=16.3855`, `peak_end_rt=16.86`, area `3.63547e+06` |
| Strict ISTD benchmark hotfix | PASS | hotfix candidate `active_fail_count=0`, `15N5-8-oxodG status=PASS`, `log_area_spearman=0.928571` |
| Matrix parity vs local-minimum | PASS | `Compare-Object` reported no differences between local-minimum and hotfix alignment matrix TSVs |

## Hotfix Evidence Chain Continuation

| Gate | Result | Evidence |
|---|---|---|
| Evidence spine consistency | PASS_WITH_WARNINGS | The initial hotfix command mixed targeted `region_first_safe_merge` with hotfix alignment production `local_minimum` and produced `d3-N6-medA / NormalBC2312_DNA` mismatch `boundary_start_delta_gt_0.10;region_verdict_mismatch;local_mixture_mismatch`. Same-surface probes show this is not a true evidence-spine blocker: targeted `local_minimum` vs hotfix alignment has `d3-N6-medA` `8/8` non-missing rows consistent and the reviewed row area ratio is `1.000001375`; targeted `region_first_safe_merge` vs region-first alignment also has `d3-N6-medA` `8/8` non-missing rows consistent. Remaining production-surface mismatches match the prior label-calibration warning class: `consistent_rows=41`, `mismatch_rows=31`, `missing_alignment_rows=16`. |
| Area integration uncertainty | PASS | `unexplained_area_mismatch_count=0`, `boundary_sensitive=1`; the `d3-N6-medA / NormalBC2312_DNA` mismatch is `label_only_mismatch`, not an unexplained area blocker |
| Identity coherence sidecar parity | PASS | serial/process sidecars exact-match: requests `2302`, decisions `2302`, cell evidence `7940`; initial report at `output/phase1_p1_resolver_default_validation/identity_coherence_hotfix/identity_coherence_8raw_validation_report.md`; reviewed rerun report at `output/phase1_p1_resolver_default_validation/identity_coherence_hotfix_reviewed/identity_coherence_8raw_validation_report.md` |
| Identity coherence v0.4 acceptance | PASS | `python -m scripts.validate_identity_coherence_8raw ... --controls-manifest output\phase1_p1_resolver_default_validation\identity_coherence_hotfix\identity_coherence_controls_manifest_8raw.reviewed.tsv --require-v04-acceptance` exited 0 and printed `PASS identity_coherence_v04_acceptance`; summary at `output/phase1_p1_resolver_default_validation/identity_coherence_hotfix_reviewed/identity_coherence_v04_acceptance.md` |
| Reviewed controls / decoys | PASS | reviewed manifest hash `A08F197E31E5F33C35035AB082488DC9F0B5494075BF6930CF9F4EBA42DE1FC6`; 5/5 positive controls passed and 3/3 identity decoys were rejected without coherent-seed promotion |
| Identity-family pre-change count | PASS | baseline rows `2302`, candidate rows `2302`, baseline hash = candidate hash = `F2D78B8D6AF69653B7848A04819A63C8E3E845F3B14E7D168CD24EC1D0DD0D93`, line diff count `0` |

## Review

- Post-run review status: completed.
- Findings fixed:
  - Patched the validation plan to require `keep_intermediate_csv=true` for
    targeted runs, because downstream comparison and P1 area/RT diagnostics read
    `xic_results.csv`.
  - Patched the validation plan gate semantics so real-data NO-GO metrics are
    recorded as `diagnostic_only` instead of `inconclusive`.
  - Stopped downstream real-data gates after the strict ISTD benchmark NO-GO to
    avoid implying P2 readiness.
  - Reclassified the hotfix evidence-spine `d3-N6-medA / NormalBC2312_DNA`
    mismatch as a mixed-surface diagnostic artifact after same-surface probes
    showed the row is consistent.
  - Supplied the reviewed 8RAW controls manifest from the accepted V0.4 handoff
    and reran the strict V0.4 acceptance gate against current P1 hotfix
    artifacts.
  - Supplied the matching pre-change identity-family baseline and verified the
    hotfix-reviewed decisions are byte-identical.

## Next Step

- P2 (AsLS baseline shadow path) may start next.
- Keep Cleanup C-spec implementation on hold until the full Phase 1
  modernization sequence has its own stable GO / NO-GO notes.
- Do not treat this as 85RAW or `production_ready`; broader production readiness
  still needs the separate 85RAW / production gate.
