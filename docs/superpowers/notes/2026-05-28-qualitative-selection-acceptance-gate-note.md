# Qualitative Selection Acceptance Gate Note

**Date:** 2026-05-28
**Status:** `phase1b_go_after_owner_backfill_scan_support_fix`

Final Classification: GO_FOR_NEXT_PRODUCT_DECISION_PR

## Verdict

Phase 1b now clears the qualitative selection gate for the current
production-equivalent alignment path.

The earlier `NO_GO` was valid, but the root cause was narrower than the
backfill concept itself: `owner_backfill` was being used as a support label while
`owner_backfill.py` did not emit the independent `scan_support_score` that the
shared promotion policy requires. That made real rescued MS1 peaks look
unsupported and pushed rows such as `FAM000264 / d3-N6-medA` out of the primary
matrix.

The fix is production-path evidence, not a target exception:

- owner-backfill cells now compute `scan_support_score` from the extracted XIC
  trace and selected peak boundary;
- `trace_quality=owner_backfill` still does not count as independent support by
  itself;
- high-backfill promotion requires at least two detected identity cells, so a
  single detected seed cannot promote a mostly backfilled row;
- supported high-backfill rows are capped at medium confidence and marked with
  `high_backfill_dependency_capped`.

This does not declare the whole product production-ready. It means the
qualitative selected-peak / backfill-promotion blocker is closed, and the next
PR can move to the next product behavior decision.

## Changed Behavior

Shared policy owner:

`xic_extractor/alignment/promotion_policy.py`

Production and diagnostic consumers:

- `xic_extractor/alignment/matrix_identity.py`
- `tools/diagnostics/single_dr_production_gate_decision_report.py`

Root-cause fix:

- `xic_extractor/alignment/owner_backfill.py` now emits scan support for both
  exact and batch owner-backfill paths.

Review-driven safeguards:

- `height` is part of `BackfillCellEvidence` and complete-peak evaluation.
- TSV numeric parsing handles Excel-safe negative numbers such as `'-4.96409`.
- TSV fallback quantifiable-rescue logic excludes out-of-window `review_rescue`
  rows when serialized `alignment_cells.tsv` lacks explicit `quality_status`.
- The single-dR diagnostic includes policy-blocked dR rows outside the primary
  matrix so demoted rows do not disappear from the gate report.

## 8RAW Validation

Run directory:

`output\product_priority_reset_phase1b\alignment_8raw_scan_support_fix`

Command shape:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\product_priority_reset_phase1b\alignment_8raw_scan_support_fix `
  --expected-sample-count 8 `
  --output-level validation-minimal `
  --resolver-mode region_first_safe_merge `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --timing-output output\product_priority_reset_phase1b\alignment_8raw_scan_support_fix\timing.json `
  --timing-live-output output\product_priority_reset_phase1b\alignment_8raw_scan_support_fix\timing.live.json
```

Wall-clock: `27.0 s`

| Artifact | Rows | SHA256 |
| --- | ---: | --- |
| `alignment_matrix.tsv` | 323 | `FD6F11A03084CCBE3685DB3F3D997497ACE408B18E743D6DA2EB91837E443FC8` |
| `alignment_review.tsv` | 2395 | `B64F0B5B31ACAC3B5A3A01A7C85D11FA9E6F1C459B19C5AFACBFDA87E94390D2` |
| `alignment_cells.tsv` | 19160 | `4EDD5846AB77C714AD565BB8BF5C77925B0CE8E441817C75717F3996C3C6C2CA` |
| `timing.json` | - | `6D89DE0F07A118A554AE7BA29F9579CCCA2CA9BE183A5A2D141A592470350C9E` |

Single-dR diagnostic:

`output\product_priority_reset_phase1b\single_dr_gate_8raw_scan_support_fix`

| Metric | Value |
| --- | ---: |
| single-dR gate rows | 418 |
| single-dR primary rows | 323 |
| strong rows | 173 |
| weak rows | 106 |
| supported backfill capped rows | 57 |
| blocked low-coverage rows | 20 |
| risky extreme backfill rows | 45 |
| risky weak-seed rows | 14 |
| watch duplicate rescue rows | 3 |
| hard gate candidate primary rows | 0 |

`FAM000264 / d3-N6-medA` current 8RAW status:

| Family | Primary | Decision | Confidence | Reason | Supported / assessed rescue | Flags |
| --- | --- | --- | --- | --- | --- | --- |
| `FAM000264` | `TRUE` | `production_family` | `medium` | `dda_limited_ms2_but_ms1_shape_supported` | `5 / 5` | `rescue_heavy;weak_seed_backfill_dependency;high_backfill_dependency_capped` |

## 85RAW Validation

Run directory:

`output\product_priority_reset_phase1b\alignment_85raw_scan_support_fix`

Command shape:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\85raw\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\product_priority_reset_phase1b\alignment_85raw_scan_support_fix `
  --expected-sample-count 85 `
  --output-level validation-minimal `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --timing-output output\product_priority_reset_phase1b\alignment_85raw_scan_support_fix\timing.json `
  --timing-live-output output\product_priority_reset_phase1b\alignment_85raw_scan_support_fix\timing.live.json
```

Wall-clock: `692.8 s`

| Artifact | Rows | SHA256 |
| --- | ---: | --- |
| `alignment_matrix.tsv` | 610 | `2AC1ADDF5302477D46BEB46FC1C893877B40DE92AE05E77A7BFCE9D5DC9E5D57` |
| `alignment_review.tsv` | 21812 | `878CEAAE61BC46E16310994E224C91EF86089455F5AA0A7BB6EAFDB3F696D8E1` |
| `alignment_cells.tsv` | 1854020 | `7379DCF74910C1B027FB217C50D891ABEA0CD43F95E6DE6E5E86C0C3D0F5299B` |
| `timing.json` | - | `FA42807CFDCA58156AECF3C99BAD8ACD991E93DAD6834433C3128AAA9DA52F7D` |

Single-dR diagnostic:

`output\product_priority_reset_phase1b\single_dr_gate_85raw_scan_support_fix`

| Metric | Value |
| --- | ---: |
| single-dR gate rows | 858 |
| single-dR primary rows | 610 |
| strong rows | 476 |
| weak rows | 125 |
| supported backfill capped rows | 19 |
| blocked low-coverage rows | 69 |
| risky extreme backfill rows | 118 |
| risky weak-seed rows | 47 |
| watch duplicate rescue rows | 4 |
| hard gate candidate primary rows | 0 |

## Delta Fixture

Delta baselines:

- 8RAW: `output\product_priority_reset_phase1\alignment_8raw_primary_delivery_fix\alignment_review.tsv`
- 85RAW: `output\product_priority_reset_phase1\alignment_85raw_primary_delivery_fix\alignment_review.tsv`

| Scope | Delta rows | Promoted rows | Demoted rows | Supported capped primary | Hard-gate primary | Fixture | SHA256 |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 8RAW | 80 | 43 | 2 | 54 | 0 | `docs\superpowers\fixtures\diagnostic_ledger_2026_05_28\phase1b_8raw_policy_delta.tsv` | `A889FEEE29682A12E274B273EF0DEC45BACCD7CBB6166D2BB97A55C6025083C3` |
| 85RAW | 96 | 17 | 4 | 18 | 0 | `docs\superpowers\fixtures\diagnostic_ledger_2026_05_28\phase1b_85raw_policy_delta.tsv` | `EAA72BD296B4DBA270349583EEB799A9D2C98CC2BB32421D5317CF9C92CD70B2` |

Summary fixture:

`docs\superpowers\fixtures\diagnostic_ledger_2026_05_28\phase1b_policy_delta_summary.tsv`

SHA256:

`533C74ABAE7313D2B8A52B3B963A63C2A5E4EF2B5F03905CEAABA35005CEB1BA`

## Verification

Focused tests:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
.venv\Scripts\python.exe -m pytest `
  tests\test_alignment_owner_backfill.py `
  tests\test_alignment_matrix_identity.py `
  tests\test_single_dr_production_gate_decision_report.py `
  tests\test_alignment_production_decisions.py `
  tests\test_discovery_evidence.py `
  tests\test_alignment_tsv_writer.py `
  -q
```

Result: `102 passed`.

Collateral tests:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
.venv\Scripts\python.exe -m pytest `
  tests\test_alignment_decision_report.py `
  tests\test_alignment_primary_consolidation.py `
  tests\test_untargeted_alignment_guardrails.py `
  -q
```

Result: `46 passed`.

## Review Resolution

- Implementation-contract review: blocking findings accepted. Fixed `height`
  parity, review-rescue TSV fallback, diagnostic blocked coverage, and writer
  header contract tests.
- Strategy challenge: blocking finding accepted. `owner_backfill` remains a
  trace-quality label, not independent support.
- Follow-up root-cause review: accepted. The production path was missing
  owner-backfill scan support emission, so valid rescued MS1 peaks were being
  demoted by the corrected policy.

## Next Action

Proceed to the next product-decision PR. Recommended target:

`Tiered Backfill Machine Decision Contract`

Reason: qualitative selection/backfill promotion is no longer the blocker. The
next blocker is the machine-routing contract between evidence collection,
provisional retention, and primary matrix promotion. The next PR should include
the whole narrow tiered scope: one-detected-seed provisional retention,
deterministic projection from existing review/cell fields, tests, docs, and no
change to `alignment_matrix.tsv`.

Normal downstream correction/statistics continue to consume the primary-only
`alignment_matrix.tsv`; provisional rows are consumed by review/gate diagnostics
and kept out of the quantitative matrix unless a future promotion contract says
otherwise.

`ASLS / linear-edge quantitative behavior and boundary guard` remains the next
high-value quantitative behavior candidate after tiered backfill. It is deferred
so the quantitative PR does not also have to define row-role semantics.
