# Qualitative Selection Acceptance Gate Note

**Date:** 2026-05-28
**Status:** `production_candidate_85raw_validated`

Final Classification: GO_FOR_NEXT_PRODUCT_DECISION_PR

## Verdict

Phase 1 now clears the 8RAW and 85RAW qualitative delivery gates. The previous
blocker was not `d3-N6-medA` RT drift or ASLS/area behavior. The blocker was
that accepted `d3-N6-medA` evidence did not reach the downstream
`alignment_matrix.tsv` delivery surface.

That delivery blocker is fixed in the current 8RAW run and survived the 85RAW
watch:

- `FAM000264` is now `production_family`, `identity_reason=owner_complete_link`,
  `include_in_primary_matrix=TRUE`.
- `FAM000264` has `8/8` accepted cells, `3` detected cells, `5` rescued cells,
  `22` event clusters, and `24` event members.
- `TumorBC2312_DNA / d3-N6-medA` resolves to `FAM000264` through an equivalent
  current artifact: the strong discovery candidate `TumorBC2312_DNA#21195`
  has apex RT `25.4204`, and the primary delivered `FAM000264` cell for
  `TumorBC2312_DNA` is the same m/z class and apex RT `25.4204`.
- `NormalBC2312_DNA / d3-N6-medA` resolves directly to primary `FAM000264`.

`d3-N6-medA` remains a known RT-drift / same-surface case. It must not be reused
as a qualitative blocker unless a new current run loses identity, local RT
coherence, selected peak ownership, boundary ownership, or matrix delivery.

The remaining warnings are not qualitative blockers:

- The 85RAW strict targeted ISTD benchmark still reports `AREA_MISMATCH` for
  `d4-N6-2HE-dA` and `d3-N6-medA`. Those are known quantitative / baseline /
  targeted-oracle issues, not evidence that the qualitative delivery row is
  wrong.
- Five 85RAW primary rows carry `rescue_heavy;weak_seed_tolerated`. They remain
  explicit watch rows, with no extreme-backfill or weak-seed hard gate candidate.

## Fixed Review Manifest

| Kind | Sample / scope | Label or control | Gate result |
| --- | --- | --- | --- |
| positive ISTD | `BenignfatBC1151_DNA` | `d3-5-hmdC` | PASS: primary `FAM000162` |
| positive ISTD | `BenignfatBC1055_DNA` | `d3-5-medC` | PASS: primary `FAM000030` |
| positive ISTD | `BenignfatBC1055_DNA` | `15N5-8-oxodG` | PASS: primary `FAM000563` |
| positive ISTD | `TumorBC2312_DNA` | `d3-N6-medA` | PASS: primary `FAM000264`, equivalent candidate apex `TumorBC2312_DNA#21195` |
| positive ISTD | `NormalBC2263_DNA` | `d3-dG-C8-MeIQx` | PASS: primary `FAM001807` |
| identity decoy aggregate | reviewed controls manifest hash `A08F197E31E5F33C35035AB082488DC9F0B5494075BF6930CF9F4EBA42DE1FC6` | `identity_decoy_specificity` | accepted V0.4 aggregate oracle: `3/3` reviewed decoys rejected, `0` promoted |
| prior blocker | `NormalBC2312_DNA` | `15N5-8-oxodG` | PASS: primary `FAM000563` |
| prior warning | `NormalBC2312_DNA` | `d3-N6-medA` | PASS: primary `FAM000264` |

## Per-row Decision Matrix

Authoritative post-fix resolved row evidence:

- `output/product_priority_reset_phase1/phase1_review_matrix_resolved.tsv`
- SHA256:
  `84B97ECD198B25911E98641C6F962DE8449EEB99EF2C4164373AE431DFC30F5A`
- durable fixture:
  `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/phase1_review_matrix_resolved_primary_delivery_fix.tsv`

| Row | Current evidence | Gate interpretation |
| --- | --- | --- |
| `d3-5-hmdC / BenignfatBC1151_DNA` | selected `FAM000162`, `detected`, RT `9.0256`, primary matrix row present | PASS |
| `d3-5-medC / BenignfatBC1055_DNA` | selected `FAM000030`, `detected`, RT `12.5593`, primary matrix row present | PASS |
| `15N5-8-oxodG / BenignfatBC1055_DNA` | selected `FAM000563`, `detected`, RT `16.4283`, primary matrix row present | PASS |
| `d3-N6-medA / TumorBC2312_DNA` | selected `FAM000264`, `rescued`, RT `25.4204`; equivalent current artifact `TumorBC2312_DNA#21195`; primary matrix row present | PASS |
| `d3-dG-C8-MeIQx / NormalBC2263_DNA` | selected `FAM001807`, `detected`, RT `40.6203`, primary matrix row present | PASS |
| `15N5-8-oxodG / NormalBC2312_DNA` | selected `FAM000563`, `detected`, RT `16.5806`, primary matrix row present | PASS |
| `d3-N6-medA / NormalBC2312_DNA` | selected `FAM000264`, `detected`, RT `26.232`, primary matrix row present | PASS |

GO blocker count: 0.

## 8RAW Validation

8RAW delivery freshness: GO. The accepted 8RAW discovery index has `rows=8`,
`stale_refs=0`, and hash
`6A17FE7FEB58AE2DA1FA0F48150D2303750E8943DAB48C05E50B3DF897E485C9`.

The foreground validation-minimal run completed at:

`output/product_priority_reset_phase1/alignment_8raw_primary_delivery_fix`

Artifacts:

| Artifact | Rows | SHA256 |
| --- | ---: | --- |
| `alignment_matrix.tsv` | 282 | `49CC57F1AE893B791C4D8CCCDC0E24B874585EA2C8940E9B38958AE48D7B6B9F` |
| `alignment_review.tsv` | 2395 | `13CB08C033C1954A154BFE8FBA7A87B0F744C19C42E391CF4C436F0549D278D2` |
| `alignment_cells.tsv` | 19160 | `F16B4E9F5A332E0CA012E97EDDC0E5988F91C6ED988ED2E02A91F8B84909310F` |

Run shape:

- `output-level=validation-minimal`
- `backfill-scope=production-equivalent`
- `audit-evidence-mode=none`
- `owner-backfill-window-strategy=super-window`
- `raw_workers=8`

Focused diagnostics:

- `single_dr_production_gate_decision_report.py`: `282` single-dR primary rows,
  `0` risky weak-seed or extreme-backfill primary rows.
- `targeted_gt_alignment_audit.py` default checkpoint (`5-medC / d3-5-medC`):
  `PASS 8 / 8`, `SPLIT 0`, `DRIFT 0`, `DUPLICATE 0`, `MISS 0`.
- `alignment_decision_report.py`: `WARN`, not `FAIL`. The warning load is
  `rescue_heavy` / `weak_seed_tolerated`; it is a watch surface, not a named
  qualitative blocker.

## Oracle Status

| Oracle | Status | Evidence |
| --- | --- | --- |
| Diagnostic ledger | updated post-fix | `docs/diagnostic-ledger.md` now records that `d3-N6-medA` is not an 8RAW blocker after primary delivery is restored. |
| Row-level gate matrix | GO | `phase1_review_matrix_resolved_primary_delivery_fix.tsv` records `7/7` reviewed rows as PASS and `GO blocker count: 0`. |
| Targeted GT default checkpoint | PASS | `5-medC / d3-5-medC` remains `PASS 8 / 8`. |
| Single-dR gate pressure | PASS with watch rows | 8RAW: `282` single-dR primary rows, `0` risky weak-seed or extreme-backfill rows. 85RAW: `597` single-dR primary rows, `0` risky weak-seed or extreme-backfill rows. |
| Collateral promotion audit | PASS with watch rows | 8RAW promoted 13 `DNA_dR` rows, all warning-marked. 85RAW has five `rescue_heavy;weak_seed_tolerated` primary rows and no hard gate candidate. |
| Strict targeted ISTD area benchmark | QUANT_FOLLOWUP | 85RAW fails only `AREA_MISMATCH` for known `d4-N6-2HE-dA` and `d3-N6-medA`; not a qualitative delivery blocker. |

## Collateral Promotions

The fix promotes 13 additional `DNA_dR` primary rows relative to the previous
8RAW run. All 13 carry `row_flags=rescue_heavy;weak_seed_tolerated`.

Durable collateral table:

- `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/collateral_promoted_primary_rows_primary_delivery_fix.csv`
- SHA256:
  `9CFD07DBDD067748DEFEA883086894E481E947C157C15727E7BACC6DDCB71296`

This is acceptable for the 8RAW qualitative gate because the previous broad
`q_detected >= 3` promotion was rejected, while the current rule requires
trusted detected seed support and keeps the warning visible. The 85RAW watch is
now complete and found five primary rows with `rescue_heavy;weak_seed_tolerated`,
with no risky weak-seed or extreme-backfill hard gate candidate.

## 85RAW

85RAW foreground validation completed for this production behavior change.

Run directory:

`output/product_priority_reset_phase1/alignment_85raw_primary_delivery_fix`

Run shape:

- `output-level=validation-minimal`
- `backfill-scope=production-equivalent`
- `audit-evidence-mode=none`
- `performance-profile=validation-fast`
- `owner-backfill-window-strategy=super-window`
- `owner-backfill-superwindow-span-factor=2`
- foreground run with `timing.json` and `timing.live.json`

Primary artifacts:

| Artifact | Rows | SHA256 |
| --- | ---: | --- |
| `alignment_matrix.tsv` | 597 | `53EC16DA87D7BC3AE02C88120E5FBBD22CB45BB4C7FFCA07F605EE7D9EA8564D` |
| `alignment_review.tsv` | 21812 | `17C478A04A8B97058AB473702933D0DC38D7ACF237AC56ECF52B69A2B4776E20` |
| `alignment_cells.tsv` | 1854020 | `FFC309A7A249742D8C0CEC9DCE9063A0F3620D902B7193B13A7D882434683B93` |
| `timing.json` | - | `A15F7EC0EF42AC52C6FFB8D315F27B867C487157D394D52C4489A8C9AADC9157` |
| `alignment_run_metadata.json` | - | `FEBBBC775025EDDA1884D65BC507F0EA90C1C74CECFA10215D0F63F993456FDE` |

Durable summary fixtures:

- `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/85raw_primary_delivery_fix_summary.tsv`,
  SHA256 `2D77F99F9429BD7EB82A9D69F70D299AB8F76228567EDAD7DCA07FF63D90934B`
- `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/85raw_weak_seed_tolerated_watch_rows.tsv`,
  SHA256 `E003FDEAC97E1DAE6E0D6AF929CDD7EA3A004BC9873A0340EF8A7B2E099683E4`

85RAW diagnostics:

- `single_dr_production_gate_decision_report.py`: `597` single-dR primary rows,
  `0` risky extreme-backfill rows, `0` risky weak-seed rows, and `0` duplicate
  rescue-pressure rows.
- `alignment_decision_report.py`: `WARN`, not `FAIL`. Warning load is
  `rescue_heavy` and `rescue_heavy;weak_seed_tolerated`, not a named
  qualitative blocker.
- `targeted_istd_benchmark.py`: strict benchmark exits non-zero because
  `d4-N6-2HE-dA` and `d3-N6-medA` still have known `AREA_MISMATCH`. All active
  ISTDs have one selected primary family and `85/85` untargeted positives. This
  result is a quantitative follow-up surface, not a qualitative delivery NO-GO.

## Subagent Review Resolution

Prior reviewer concerns that shaped this gate are now resolved in the current
artifact set:

- `d3-N6-medA` is separated into known RT-drift context vs actual primary
  delivery state.
- The prior sample-only shortcut is replaced with row-local evidence:
  source-candidate match when available, or a same-sample / same-m/z /
  same-apex equivalent current artifact when the source candidate is represented
  as an ambiguous owner row.
- Collateral promotions are not hidden; the 13-row 8RAW table and five-row 85RAW
  watch table are durable fixtures.

## Next Action

Close this phase as `production_candidate` for qualitative selection and move to
the next product decision. Do not treat `d3-N6-medA` drift or known area mismatch
as a blocker for this qualitative gate.

Recommended next PR target: ASLS / baseline quantitative correction decision.
Reason: qualitative delivery is now `production_candidate`, while the remaining
named failures are strict `AREA_MISMATCH` rows tied to quantitative integration
behavior. CWT productization should be an explicit product decision when the
evidence points to boundary or hypothesis-source defects, not another
scaffold-only detour.
