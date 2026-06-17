# Diagnostic Ledger And Rerun Policy

**Status:** maintained repo-local diagnostic memory
**Last updated:** 2026-06-16

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

### 2026-06-16 5-hmdC Own-Max Support Explicit Opt-In Smoke

Verdict: `production_ready` for the headless explicit limited
`targeted_ms1_shape_identity_support_tsv` workflow only. The ready claim is
limited to `limited_5hmdc_5medc_v1`, `5-hmdC + 5-medC`, and
`detected_flagged` output. This is not default automatic rescue: GUI is not
connected, the default extraction path remains off, and broader targets still
need separate expected-diff evidence.

Update on the same date: the original five-row TSV was a handpicked review
surface, not a product limitation. A generic RAW-backed support producer now
finds all eligible baseline rows that are analyte `NL_FAIL` / `NO_MS2`, blocked
only by `analyte_nl_fail_requires_policy`, already supported by paired RT/area
ratio, and then passes Gaussian-smoothed own-max same-peak identity.

Generic producer smoke:
`output/ms1_shape_identity_generic_support_85raw_20260616/`

2026-06-17 support key-set gate update: the limited expected-diff gate now reads
the actual `targeted_ms1_shape_identity_v0.tsv` with `--support-tsv` and fails
closed unless accepted support keys exactly match product long-row diff keys.
The existing 85RAW generic artifact rerun passed with `long_changed_rows=11`,
`matrix_changed_cells=66`, and `support_tsv_supported_rows=11`.

Current 8RAW smoke:
`output/ms1_shape_identity_optin_8raw_20260616/`

Current 85RAW smoke:
`output/ms1_shape_identity_optin_85raw_20260616/`

Key facts:

- Baseline and opt-in runs both used
  `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation` for 8RAW and
  `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R` for 85RAW; all runs used
  CSV-only output.
- Opt-in runs used
  `output/ms1_rescue_5hmdc_own_max_similarity_20260616/targeted_ms1_shape_identity_v0.tsv`.
- 8RAW `expected_diff_summary.tsv` found exactly one changed row:
  `TumorBC2263_DNA / 5-hmdC`.
- That row changed from `Product State=not_counted`,
  `Counted Detection=FALSE`, `RT=ND`, `Area=ND` to
  `Product State=detected_flagged`, `Counted Detection=TRUE`, `RT=9.1705`,
  `Area=145695.76`.
- 85RAW `expected_diff_summary.tsv` found exactly five changed rows, exactly
  matching the reviewed support TSV keys:
  `BenignfatBC1028_DNA / 5-hmdC`,
  `BenignfatBC1108_DNA / 5-hmdC`,
  `NormalBC2302_DNA / 5-hmdC`,
  `TumorBC2263_DNA / 5-hmdC`, and
  `TumorBC2294_DNA / 5-hmdC`.
- All five changed from `not_counted / FALSE` to `detected_flagged / TRUE`.
  Unexpected changed rows = `0`; support rows not changed = `0`.
- The 85RAW wide matrix changed `30` value cells, only those five samples'
  `5-hmdC_RT`, `5-hmdC_Int`, `5-hmdC_Area`, `5-hmdC_PeakStart`,
  `5-hmdC_PeakEnd`, and `5-hmdC_PeakWidth`.
- In both 8RAW and 85RAW, support reasons gained
  `own_max_same_peak_support` and `analyte_nl_fail_requires_policy` was
  removed.
- The generic producer read the existing 85RAW baseline long CSV and emitted
  `11` diagnostic support rows: `10` for `5-hmdC` and `1` for `5-medC`.
  All `11` were `own_max_same_peak_supported`.
- A new 85RAW opt-in run using that generic TSV changed exactly `11` rows:
  `BenignfatBC0980_DNA / 5-hmdC`,
  `BenignfatBC1028_DNA / 5-hmdC`,
  `BenignfatBC1108_DNA / 5-hmdC`,
  `NormalBC2259_DNA / 5-hmdC`,
  `NormalBC2264_DNA / 5-medC`,
  `NormalBC2270_DNA / 5-hmdC`,
  `NormalBC2272_DNA / 5-hmdC`,
  `NormalBC2294_DNA / 5-hmdC`,
  `NormalBC2302_DNA / 5-hmdC`,
  `TumorBC2263_DNA / 5-hmdC`, and
  `TumorBC2294_DNA / 5-hmdC`.
- All `11` changed from `not_counted / FALSE` to
  `detected_flagged / TRUE`. The wide matrix changed `66` value cells
  (`11` rows x `RT/Int/Area/PeakStart/PeakEnd/PeakWidth`). Baseline and
  generic opt-in `xic_diagnostics.csv` SHA256 values were identical.

Do not rerun 85RAW for this path unless current code changes product
projection, support TSV parsing, selected-candidate semantics, matrix writing,
or the cited artifacts become stale. If only the human review wording changes,
reuse the 85RAW artifact above.

### 2026-06-05 Gaussian15 MS1 Morphology Primary Area Owner

Verdict: `production_ready` for the Gaussian15 MS1 morphology ownership
transition. Active primary matrix area now requires
`primary_matrix_area_source=gaussian15_positive_asls_residual`; historical
`asls_baseline_corrected` is compatibility/debug-only and must not write product
area. Missing typed morphology facts fail closed as
`missing_ms1_morphology_area`.

Durable closeout:
`docs/superpowers/notes/2026-06-05-gaussian15-ms1-morphology-production-ready-closeout.md`

Current 85RAW foreground gate:
`output/gaussian15_ms1_morphology_85raw_20260605/alignment_validation_minimal_no_asls_fallback/`

Key facts:

- `matrix_value_policy=gaussian15_positive_asls_residual_primary`
- `primary_matrix_area_nonblank_count=1546489`
- `non_gaussian_source_with_area=0`
- `asls_source_with_area=0`
- `raw_source_with_area=0`
- `matrix_sample_count=85`
- `matrix_row_count=614`

Do not rerun 85RAW just to re-prove ASLS fallback retirement. Rerun only after
a new production behavior change, a new target/default validation contract, or a
current artifact contradicts the closeout facts above.

### 2026-06-05 Gaussian15 MS1 Peak-Group NL Scope

Verdict: `production_ready` for targeted candidate MS2/NL evidence ownership
under Gaussian15 MS1 peak-group scope. Selected `chrom_peak_segment` candidates
must not borrow active strict NL support from a different Gaussian15 MS1 peak
group. Outside-group strict NL stays diagnostic context.

Durable closeout:
`docs/superpowers/notes/2026-06-05-gaussian15-ms1-peak-group-nl-scope-production-ready-closeout.md`

Current 8RAW targeted gate:
`output/gaussian15_ms1_peak_group_nl_scope_8raw_20260605/nl_peak_group_scope_8raw/ms1_peak_group_nl_scope_gate/ms1_peak_group_nl_scope_gate_manifest.json`

Current 85RAW targeted gate:
`output/gaussian15_ms1_peak_group_nl_scope_85raw_20260605/nl_peak_group_scope_85raw/ms1_peak_group_nl_scope_gate/ms1_peak_group_nl_scope_gate_manifest.json`

Key facts:

- 8RAW: `gate_decision=promote`, `selected_chrom_count=80`,
  `borrowed_strict_nl_support_rows=0`, `review_row_count=0`,
  `context_row_count=15`.
- 85RAW: `gate_decision=promote`, `selected_chrom_count=811`,
  `borrowed_strict_nl_support_rows=0`, `review_row_count=0`,
  `context_row_count=156`.
- The gate also requires `ms1_peak_group_source=gaussian15_ms1_peak_group` and
  selected apex inside the group bounds.

Do not rerun 85RAW just to re-prove this scoped NL ownership behavior. Rerun
only after current code changes targeted candidate MS2/NL evidence ownership,
chrom peak segment selection, candidate-table projection, or the cited artifacts
are stale or contradictory.

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

Post-fix 85RAW primary-delivery conclusion before implementation-review
hardening:

- Foreground 85RAW `validation-minimal` completed with the canonical
  production-equivalent, audit-off, validation-fast, super-window, heartbeat
  command shape.
- `alignment_matrix.tsv` contains `597` primary rows. The primary warning
  surface is `376` `rescue_heavy` rows plus `5`
  `rescue_heavy;weak_seed_tolerated` rows.
- Original `single_dr_production_gate_decision_report.py` found `0` risky
  extreme-backfill rows, `0` risky weak-seed rows, and `0` duplicate
  rescue-pressure rows.
- After implementation-review hardening of the trusted-seed contract, the same
  committed artifacts reclassify the prior weak-seed tolerated rows as
  `risky_weak_seed_backfill`: 8RAW has `13` such primary rows, including
  `FAM000264`; 85RAW has `5`.
- `targeted_istd_benchmark.py` still reports strict `AREA_MISMATCH` for
  `d4-N6-2HE-dA` and `d3-N6-medA`. Treat this as a known quantitative /
  baseline follow-up surface, not a qualitative delivery blocker, because all
  active ISTDs have one selected primary family and `85/85` untargeted
  positives.
- Current qualitative classification is `NO_GO_FIX_SELECTION_OR_BOUNDARY_FIRST`
  for the production behavior as written. `d3-N6-medA` drift and area mismatch
  are not the blocker; the blocker is the weak-seed promotion contract.

Authoritative notes and artifacts:

| Evidence | Path / fact |
| --- | --- |
| P2B area mismatch triage | `docs/superpowers/notes/2026-05-26-p2b-area-mismatch-triage-note.md` |
| Resolver default hotfix / same-surface d3 note | `docs/superpowers/notes/2026-05-24-resolver-default-switch-validation-note.md` |
| 85RAW super-window acceptance | `docs/superpowers/notes/2026-05-26-p8b-85raw-superwindow-acceptance-note.md` |
| Product-priority Phase 1 gate | `docs/superpowers/notes/2026-05-28-qualitative-selection-acceptance-gate-note.md` |
| Current 8RAW resolved matrix snapshot | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/phase1_review_matrix_resolved.tsv`, SHA256 `9A63FC81C811CF92925853884837B623878B644A26311799FAF64FA4947548E8` |
| Post-fix 8RAW resolved matrix snapshot | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/phase1_review_matrix_resolved_primary_delivery_fix.tsv`, SHA256 `B38EC06D01714B4AACA6825B1C003C9BB724264689FCD78FBCB8DD2F9AB0CE9D` |
| Current 8RAW row triage snapshot | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/target_derived_review_row_triage.tsv`, SHA256 `73601AE36C879CE827AEA5816F6E690DF023F8DEB59B63F97ED8BBDEE635A3F9` |
| Post-fix 8RAW row triage snapshot | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/target_derived_review_row_triage_primary_delivery_fix.tsv`, SHA256 `73601AE36C879CE827AEA5816F6E690DF023F8DEB59B63F97ED8BBDEE635A3F9` |
| Post-fix collateral promotion table | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/collateral_promoted_primary_rows_primary_delivery_fix.csv`, SHA256 `9CFD07DBDD067748DEFEA883086894E481E947C157C15727E7BACC6DDCB71296` |
| Post-fix 85RAW validation summary | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/85raw_primary_delivery_fix_summary.tsv`, SHA256 `4CF19B045F850B205E23888F1B3C5A6E3AF1C0BEC0C516E4447B61738CEAC24B` |
| Post-fix 85RAW weak-seed watch rows | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/85raw_weak_seed_tolerated_watch_rows.tsv`, SHA256 `E003FDEAC97E1DAE6E0D6AF929CDD7EA3A004BC9873A0340EF8A7B2E099683E4` |
| Post-review hardened single-dR gate summary | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/post_review_hardened_single_dr_gate_summary.tsv`, SHA256 `43FE4E4BCFF9DD20CA6B16F183F7A414EE89DCF1657A7E2E3B20559E32DE48E3` |
| Current 8RAW diagnostic tool usage snapshot | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/diagnostic_tool_usage_current_8raw.tsv` |
| Current 8RAW targeted GT default checkpoint | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/targeted_gt_alignment_audit_default_5medc_current_8raw_comparison.csv`, SHA256 `DB05B546B99CB9567D7873216906181FB20F57BA021BEFC3A503CC3128BE77D8`; report `targeted_gt_alignment_audit_default_5medc_current_8raw_failure_mode_report.md`, SHA256 `425B5ABD766A86BAF7970ADC6FC2C06F405454CAB3AAAFB066BE52FAA8679C88` |
| Post-fix 8RAW targeted GT default checkpoint | `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/targeted_gt_alignment_audit_default_5medc_primary_delivery_fix_comparison.csv`, SHA256 `DB05B546B99CB9567D7873216906181FB20F57BA021BEFC3A503CC3128BE77D8`; report `targeted_gt_alignment_audit_default_5medc_primary_delivery_fix_failure_mode_report.md`, SHA256 `FFB5EA89BD1DAECA685BBBA2F9BA96D069C934996DD7C5B3A332992B15D76D98` |

Source worktree output for the snapshots above was
`output/product_priority_reset_phase1/`. The committed fixture copies are the
durable reference; do not require the original worktree output to exist before
using the ledger.

Recommended next check:

1. Do not rerun RT drift diagnostics just to re-prove drift.
2. Do not treat `d3-N6-medA` area shift or absolute RT delta as a blocker.
3. Do treat the current weak-seed promotion contract as the active blocker until
   a new reviewed production identity policy replaces it.
4. If production behavior changes again, rerun 8RAW validation-minimal first.
5. Do not rerun 85RAW just to re-prove this fix. Rerun 85RAW only after a new
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
