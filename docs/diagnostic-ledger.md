# Diagnostic Ledger And Rerun Policy

**Status:** maintained repo-local diagnostic memory
**Last updated:** 2026-05-28

This ledger records diagnostic conclusions that should survive branch and
worktree changes. Use it before rerunning expensive RAW validation or treating a
known target as a new blocker.

This file is not a replacement for task-specific validation notes. It is the
small durable index that tells future agents which prior conclusions are already
known, where the evidence lives, and when a rerun is justified.

## Use Rules

- Read this ledger before investigating a previously seen target, family,
  failure mode, or validation gate.
- If this ledger already closes the diagnostic question, reuse the cited note or
  artifact instead of rerunning RAW.
- Rerun only when current code touched selection, boundary, identity,
  consolidation, integration, matrix delivery, or the cited artifacts are stale.
- Do not escalate from 8RAW to 85RAW when the 8RAW evidence is already `NO_GO`.
- Worktree `output/` paths are evidence references, not reusable inputs. Inputs
  that must survive worktrees belong under `local_validation_artifacts/`.
  Small diagnostic snapshots that must survive worktrees belong under
  `docs/superpowers/fixtures/` with a source note and hash.
- If a rerun changes a durable conclusion, update this ledger in the same PR.

## Stable Inputs

| Purpose | Stable path |
| --- | --- |
| Accepted P8b 8RAW discovery input | `C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv` |
| Accepted P8b 85RAW discovery input | `C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\85raw\discovery_batch_index.csv` |
| Targeted GT 8RAW default workbook | `C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\targeted_gt_workbooks\8raw\xic_results_20260512_1151.xlsx`, SHA256 `788892188C8419C82DC4618C98E160B90AC6C44C38676C53609248AA529889F7` |
| RAW root | `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R` |
| Thermo DLL dir | `C:\Xcalibur\system\programs` |
| RAW-capable Python | `C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe` |

## Known Diagnostic Conclusions

### d3-N6-medA

**Current classification:** known RT-drift / same-surface case; not a standalone
RT blocker.

Known facts:

- `d3-N6-medA` has severe biological-matrix RT drift. The 85RAW target-only RT
  trend audit recorded target-only RT range `2.1538 min`,
  global-median absolute RT delta p95 `1.4571 min`, local rolling-median p95
  `0.0483 min`, and local moderate/severe drift rows `0 / 85`.
- The `d3-N6-medA / NormalBC2312_DNA` evidence-spine mismatch was reclassified
  as mixed-surface diagnostic artifact after same-surface probes. Same-surface
  comparison had `8/8` non-missing rows consistent and reviewed row area ratio
  about `1.000001375`.
- Area mismatch alone must not block P2B or handoff progression for this target
  when identity, local RT coherence, selected peak, boundary ownership, and
  matrix delivery are accepted.
- Absolute RT delta alone must not prove absence for this target. Use local RT
  coherence and same-surface evidence.

Post-fix 8RAW primary-delivery conclusion:

- The prior blocker was primary delivery / ownership-consolidation, not absence
  of a plausible peak, RT drift, or area mismatch.
- `FAM000264` is the consolidated delivery family in the post-fix 8RAW run:
  `DNA_dR`, `owner_complete_link`, `include_in_primary_matrix=TRUE`,
  `8/8 present`, `3 detected`, `5 MS1 backfilled`, `22` event clusters,
  and `24` event members.
- `FAM000264` contains `NormalBC2312_DNA#22176` as detected and contains a
  `TumorBC2312_DNA` rescued cell at RT `25.4204`, matching the strong
  target-derived `TumorBC2312_DNA#21195` MS1 apex RT.
- `FAM000264` is now present in `alignment_matrix.tsv`; the row carries
  `row_flags=rescue_heavy;weak_seed_tolerated` so the warning remains visible.
- The post-fix row-level gate has `GO blocker count: 0`. `TumorBC2312_DNA /
  d3-N6-medA` resolves by an equivalent current artifact because the strong
  source candidate `TumorBC2312_DNA#21195` was an ambiguous owner row, while the
  primary `FAM000264` cell has the same sample, target m/z class, and apex RT
  `25.4204`.
- A broad rule that promotes every `weak_seed_backfill_dependency` row with
  `q_detected >= 3` remains unacceptable. The accepted fix promoted 13
  additional `DNA_dR` rows, all flagged `rescue_heavy;weak_seed_tolerated`, and
  records the collateral table below.

Post-fix 85RAW primary-delivery conclusion:

- Foreground 85RAW `validation-minimal` completed with the canonical
  production-equivalent, audit-off, validation-fast, super-window, heartbeat
  command shape.
- `alignment_matrix.tsv` contains `597` primary rows. The primary warning
  surface is `376` `rescue_heavy` rows plus `5`
  `rescue_heavy;weak_seed_tolerated` rows.
- `single_dr_production_gate_decision_report.py` found `0` risky
  extreme-backfill rows, `0` risky weak-seed rows, and `0` duplicate
  rescue-pressure rows.
- `targeted_istd_benchmark.py` still reports strict `AREA_MISMATCH` for
  `d4-N6-2HE-dA` and `d3-N6-medA`. Treat this as a known quantitative /
  baseline follow-up surface, not a qualitative delivery blocker, because all
  active ISTDs have one selected primary family and `85/85` untargeted
  positives.
- Current qualitative classification is `production_candidate` with five watch
  rows, not full quantitative production readiness.

Authoritative notes and artifacts:

| Evidence | Path / fact |
| --- | --- |
| P2B area mismatch triage | `docs/superpowers/notes/2026-05-26-p2b-area-mismatch-triage-note.md` |
| Resolver default hotfix / same-surface d3 note | `docs/superpowers/notes/2026-05-24-resolver-default-switch-validation-note.md` |
| 85RAW super-window acceptance | `docs/superpowers/notes/2026-05-26-p8b-85raw-superwindow-acceptance-note.md` |
| Product-priority Phase 1 gate | `docs/superpowers/notes/2026-05-28-qualitative-selection-acceptance-gate-note.md` |
| Current 8RAW resolved matrix snapshot | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/phase1_review_matrix_resolved.tsv`, SHA256 `315B6E7053CFFA008724FA491DB143AE879F9C1A3494E10F9A075BC2A53F0938` |
| Post-fix 8RAW resolved matrix snapshot | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/phase1_review_matrix_resolved_primary_delivery_fix.tsv`, SHA256 `84B97ECD198B25911E98641C6F962DE8449EEB99EF2C4164373AE431DFC30F5A` |
| Current 8RAW row triage snapshot | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/target_derived_review_row_triage.tsv`, SHA256 `73601AE36C879CE827AEA5816F6E690DF023F8DEB59B63F97ED8BBDEE635A3F9` |
| Post-fix 8RAW row triage snapshot | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/target_derived_review_row_triage_primary_delivery_fix.tsv`, SHA256 `73601AE36C879CE827AEA5816F6E690DF023F8DEB59B63F97ED8BBDEE635A3F9` |
| Post-fix collateral promotion table | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/collateral_promoted_primary_rows_primary_delivery_fix.csv`, SHA256 `9CFD07DBDD067748DEFEA883086894E481E947C157C15727E7BACC6DDCB71296` |
| Post-fix 85RAW validation summary | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/85raw_primary_delivery_fix_summary.tsv`, SHA256 `2D77F99F9429BD7EB82A9D69F70D299AB8F76228567EDAD7DCA07FF63D90934B` |
| Post-fix 85RAW weak-seed watch rows | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/85raw_weak_seed_tolerated_watch_rows.tsv`, SHA256 `E003FDEAC97E1DAE6E0D6AF929CDD7EA3A004BC9873A0340EF8A7B2E099683E4` |
| Current 8RAW diagnostic tool usage snapshot | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/diagnostic_tool_usage_current_8raw.tsv` |
| Current 8RAW targeted GT default checkpoint | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/targeted_gt_alignment_audit_default_5medc_current_8raw_comparison.csv`, SHA256 `DB05B546B99CB9567D7873216906181FB20F57BA021BEFC3A503CC3128BE77D8`; report `targeted_gt_alignment_audit_default_5medc_current_8raw_failure_mode_report.md`, SHA256 `425B5ABD766A86BAF7970ADC6FC2C06F405454CAB3AAAFB066BE52FAA8679C88` |
| Post-fix 8RAW targeted GT default checkpoint | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/targeted_gt_alignment_audit_default_5medc_primary_delivery_fix_comparison.csv`, SHA256 `DB05B546B99CB9567D7873216906181FB20F57BA021BEFC3A503CC3128BE77D8`; report `targeted_gt_alignment_audit_default_5medc_primary_delivery_fix_failure_mode_report.md`, SHA256 `FFB5EA89BD1DAECA685BBBA2F9BA96D069C934996DD7C5B3A332992B15D76D98` |

Source worktree output for the snapshots above was
`output/product_priority_reset_phase1/`. The committed fixture copies are the
durable reference; do not require the original worktree output to exist before
using the ledger.

Recommended next check:

1. Do not rerun RT drift diagnostics just to re-prove drift.
2. Do not treat `d3-N6-medA` area shift or absolute RT delta as a blocker when
   the post-fix primary delivery evidence still holds.
3. If production behavior changes again, rerun 8RAW validation-minimal first.
4. Do not rerun 85RAW just to re-prove this fix. Rerun 85RAW only after a new
   production behavior change or if a current artifact contradicts the 85RAW
   summary fixture.

## Reusable Diagnostics

Prefer existing tools before creating a new diagnostic:

| Question | Existing diagnostic |
| --- | --- |
| Targeted-vs-untargeted checkpoint for named targets | `tools/diagnostics/targeted_gt_alignment_audit.py` |
| Single-dR production gate pressure | `tools/diagnostics/single_dr_production_gate_decision_report.py` |
| Low-seed / high-backfill family review queue | `tools/diagnostics/family_ms1_backfill_review_report.py` |
| Alignment decision summary with known exceptions | `tools/diagnostics/alignment_decision_report.py` |
| RT normalization / target trend context | `tools/diagnostics/analyze_rt_normalization_anchors.py` |

If these tools cannot answer the current question, record why in the new plan or
validation note before adding another diagnostic.

## Current Tool Coverage

For the original product-priority 8RAW gate, the pre-fix tool coverage snapshot
is:

`docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/diagnostic_tool_usage_current_8raw.tsv`

Pre-fix summary:

- `tools/diagnostics/INDEX.md` was consulted before adding the ledger.
- `single_dr_production_gate_decision_report.py` was run on the current 8RAW
  alignment. It found 269 single-dR primary rows and 0 risky weak-seed or
  extreme-backfill primary rows. This confirms the current issue is not a bad
  primary row already leaking into the matrix.
- `family_ms1_backfill_review_report.py` was run on the current 8RAW alignment
  with `DNA_dR` scope. It queued 0 primary families, which is expected because
  `FAM000264` is excluded before primary-family review.
- `owner_backfill_request_economics.py` was run on the current 8RAW alignment.
  It found 2756 request targets, with 733 production targets and 2023 non-primary
  targets. This supports keeping reruns narrow and not treating broad evidence
  expansion as free.
- `alignment_decision_report.py` was run on the current 8RAW alignment and
  returned `WARN` with `d3-N6-medA` declared as a known exception.
- `targeted_gt_alignment_audit.py` was run on the current 8RAW alignment using
  the default positive checkpoint `5-medC / d3-5-medC`. It used the stable
  targeted GT 8RAW workbook under `local_validation_artifacts/` and found
  `PASS 8 / 8`, with `SPLIT 0`, `DRIFT 0`, `DUPLICATE 0`, and `MISS 0`.
  Do not use the 85-sample workbook against an 8RAW alignment: that creates
  off-scope `MISS` rows and is a workbook/sample-set mismatch, not a product
  signal.
- `targeted_istd_benchmark.py`, `analyze_rt_normalization_anchors.py`, and
  `evidence_spine_consistency.py` were not rerun from stale worktree-specific
  targeted workbook artifacts. Their prior conclusions are reused from the
  authoritative notes listed above.

Post-fix coverage:

- Foreground 8RAW validation-minimal run:
  `output/product_priority_reset_phase1/alignment_8raw_primary_delivery_fix`.
- `phase1_review_matrix_resolved_primary_delivery_fix.tsv` has
  `GO blocker count: 0`.
- `single_dr_production_gate_decision_report.py` on the post-fix 8RAW alignment
  found `282` single-dR primary rows and `0` risky weak-seed or
  extreme-backfill primary rows.
- `targeted_gt_alignment_audit.py` default checkpoint remains `PASS 8 / 8`.
- `alignment_decision_report.py` returns `WARN`, not `FAIL`, because `40`
  primary rows are `rescue_heavy`; the 13 newly promoted rows are all flagged
  `rescue_heavy;weak_seed_tolerated`.

85RAW post-fix coverage:

- Foreground 85RAW run:
  `output/product_priority_reset_phase1/alignment_85raw_primary_delivery_fix`.
- `alignment_matrix.tsv` has `597` primary rows and SHA256
  `53EC16DA87D7BC3AE02C88120E5FBBD22CB45BB4C7FFCA07F605EE7D9EA8564D`.
- `single_dr_production_gate_decision_report.py` found `0` risky weak-seed,
  extreme-backfill, or duplicate-rescue-pressure primary rows.
- `alignment_decision_report.py` returned `WARN`, not `FAIL`.
- `targeted_istd_benchmark.py` failed only the known strict area mismatch rows:
  `d4-N6-2HE-dA` and `d3-N6-medA`.

This coverage is enough to stop treating `d3-N6-medA` as a qualitative blocker.
The remaining risk is explicit watch surface, not a GO/NO-GO blocker: five
85RAW primary rows carry `rescue_heavy;weak_seed_tolerated`, and strict area
benchmark mismatches stay in the quantitative follow-up lane.
