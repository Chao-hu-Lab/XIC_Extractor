# Region-first Safe Merge Validation Gate

**Date:** 2026-05-18
**Status:** Planned validation
**Branch:** `codex/region-first-safe-merge-validation`
**Depends on:** `2026-05-18-region-first-safe-merge-promotion-v1-spec.md`

## Summary

This gate validates whether the opt-in `region_first_safe_merge` resolver should
remain experimental, be tightened, or become a future default candidate.

The gate does not change scoring, neutral-loss logic, targeted reliability
states, workbook schemas, XIC Results schemas, untargeted matrix identity, or
default resolver behavior.

Low-detection target improvements are observations only. They are not success
criteria because the resolver is intended to reduce local-minimum
under-integration without creating apparent low-confidence rescues.

## Checkpoints

1. **8RAW targeted extraction gate**
   - Run `tissue-8raw` with `resolver_mode=local_minimum`.
   - Run `tissue-8raw` with `resolver_mode=region_first_safe_merge`.
   - Use `parallel_workers=11` and `emit_peak_candidates=true`.
   - Required artifacts: both `xic_results.csv` files, both workbooks, the safe
     `peak_candidates.tsv`, and the safe
     `peak_region_selection_shadow_summary.tsv`.

2. **8RAW decision comparison**
   - Run `region_first_safe_merge_comparison.py`.
   - Run targeted reliability audit for both resolver outputs.
   - Changed rows must preserve target label, m/z identity, selected RT identity,
     and neutral-loss logic.
   - ISTD, 5-medC, and 5-hmdC must not show widespread detection or reliability
     regression.
   - If the default 8RAW run does not reproduce the d3-N6-medA area mismatch,
     record `D3_CHECK_INCONCLUSIVE` instead of treating the resolver as fixed.

3. **85RAW targeted blast radius**
   - Run only if the 8RAW gate is not failed.
   - Use the same resolver pair and `--confirm-full-run`.
   - Stop promotion if ISTD reliability, 5-medC, or 5-hmdC regresses, or if
     low-detection targets are broadly rescued without strong evidence.

4. **Untargeted audit bridge validation**
   - Run only if targeted 8RAW and 85RAW do not fail.
   - If the 8RAW discovery index is absent, rebuild a dR-only discovery index in
     this branch output before alignment.
   - Run default and safe-merge alignment with `--emit-alignment-cells` and the
     `validation-fast` profile.
   - Region audit context may explain local-minimum split/merge behavior, but it
     must not change final matrix identity or production gates in this phase.

5. **Final decision note**
   - Record artifact paths, 8RAW verdict, 85RAW verdict, untargeted verdict,
     d3-N6-medA status, and high-detection target regression status.
   - Final verdict must be exactly one of: `keep_opt_in`, `tighten_gate`,
     `candidate_for_default_later`, or `inconclusive`.

## Output Policy

Real-data output directories remain untracked validation artifacts. Commit only
docs, code, or tests that are needed to define or fix the validation workflow.

Each checkpoint must be reviewed before the next checkpoint starts. If a
checkpoint fails, stop and write the failure reason instead of patching around
the result.
