# LC-MS/MS Handoff Progress Checklist

Date: 2026-05-21

Source handoff:

- `C:\Users\user\Downloads\lcms_gcms_peak_pipeline_handoff.md`

This note converts the original handoff into a progress checklist. It is not a
new implementation plan. Its purpose is to make later PR planning easier by
separating finished work, audit-only/shadow work, blocked work, and out-of-scope
items.

Legend:

- `[x]` implemented and validated enough to treat as current project surface.
- `[~]` partially implemented, audit-only, shadow-only, or not production-ready.
- `[ ]` not implemented.
- `[-]` intentionally out of current scope.

## Current Product Position

- The project is currently LC-MS/MS only.
- GC-MS from the original handoff is not part of the current repo direction.
- The mature layer is evidence, audit, and review traceability.
- Production matrix / reliability / resolver / scoring changes must still pass
  explicit gates before they become product behavior.

Current high-level decisions:

- Targeted and untargeted now share trace / boundary / region evidence language.
- `region_first_safe_merge` remains an opt-in targeted resolver.
- Untargeted alignment production quantification remains `local_minimum`; region
  evidence is audit context only.
- Instrument QC RT evidence is Level 2 `go` for audit / alignment-support.
- Level 2.5 row-level RT-supported shadow gate is now available as
  audit-only alignment-support evidence.
- RT production correction remains Level 3 `no_go`.
- Response / area production correction remains Level 4/5 `no_go`.

## Handoff Checklist

### 1. Trace And TraceGroup Spine

- [x] Minimal `Trace` model exists.
- [x] Minimal `TraceGroup` model exists.
- [x] Targeted extraction routes peak audit through trace groups.
- [x] Untargeted detected / rescued cell region audit routes through trace
  groups.
- [~] TraceGroup is a shared semantic wrapper, not yet a full universal engine.
- [ ] Adaptive ROI / Kalman-like mass-trace tracking is not implemented.

Current reference points:

- `xic_extractor/peak_detection/traces.py`
- `xic_extractor/extraction/trace_context.py`
- `xic_extractor/alignment/trace_context.py`
- `docs/superpowers/notes/2026-05-18-shared-evidence-spine-adoption-decision.md`

### 2. PeakHypothesis And EvidenceVector

- [x] `PeakHypothesis`, `EvidenceVector`, `IntegrationResult`, and `AuditTrail`
  exist.
- [x] Targeted candidate rows can be represented through the hypothesis spine.
- [x] Candidate table exposes shared evidence fields for debug / audit.
- [~] EvidenceVector is useful but still tuned around current targeted /
  untargeted needs, not a final universal scoring contract.
- [ ] ML / DL model training is not implemented.

Current reference points:

- `xic_extractor/peak_detection/hypotheses.py`
- `xic_extractor/extraction/peak_candidate_table.py`
- `docs/superpowers/specs/2026-05-16-peak-hypothesis-spine-v1-spec.md`
- `docs/superpowers/specs/2026-05-16-peak-candidate-table-v1-spec.md`

### 3. Boundary Hypotheses And Integration Audit

- [x] Boundary hypothesis enumeration exists.
- [x] Boundary scoring exists.
- [x] Candidate boundary TSV exposes alternate boundaries.
- [x] Baseline-corrected area and area uncertainty are available in audit
  fields.
- [x] Alignment integration audit sidecar exists as opt-in output.
- [~] Area integration uncertainty diagnostic is audit-only.
- [~] Representative `d3-N6-medA` area mismatch did not reproduce during the
  area uncertainty validation, so production area changes remain inconclusive.

Current reference points:

- `xic_extractor/peak_detection/boundaries.py`
- `xic_extractor/peak_detection/boundary_scoring.py`
- `xic_extractor/peak_detection/baseline.py`
- `xic_extractor/peak_detection/integration_audit.py`
- `tools/diagnostics/area_integration_uncertainty_audit.py`
- `docs/superpowers/specs/2026-05-18-area-integration-uncertainty-decision.md`

### 4. CWT, WIS, Local Minimum, And Region Model Selection

- [x] CWT evidence is present as candidate / boundary / audit evidence.
- [x] WIS / region selection logic exists as shadow decision support.
- [x] Region-first model-selection shadow report exists.
- [x] Region mixture diagnostic exists.
- [~] `region_first_safe_merge` can be used as an opt-in targeted resolver.
- [~] `region_first_safe_merge` is not a default resolver candidate yet.
- [~] In untargeted alignment, region-first evidence is audit-only and must not
  mutate production quantification.
- [ ] Full local mixture production resolver is not implemented.

Current reference points:

- `xic_extractor/peak_detection/region_model_selection.py`
- `xic_extractor/peak_detection/region_safe_merge.py`
- `xic_extractor/peak_detection/region_mixture_diagnostic.py`
- `tools/diagnostics/region_first_safe_merge_comparison.py`
- `docs/superpowers/specs/2026-05-18-region-first-safe-merge-validation-decision.md`

### 5. Targeted Evidence And Reliability

- [x] Targeted reliability audit exists.
- [x] Targeted NL dropout root-cause audit exists.
- [x] Targeted evidence HTML review report exists.
- [x] RT-gate behavior was corrected so coherent ISTD evidence is not rejected
  by RT alone.
- [x] Candidate MS2 evidence exposes NL / product / trigger context.
- [~] Targeted reliability is stronger, but still not a formal quantitative
  validation system with calibration curve / LLOQ / ULOQ.

Current reference points:

- `tools/diagnostics/targeted_peak_reliability_audit.py`
- `tools/diagnostics/targeted_nl_dropout_root_cause_audit.py`
- `tools/diagnostics/targeted_evidence_review_report.py`
- `xic_extractor/ms2_trace_evidence.py`

### 6. Untargeted Alignment, Matrix Identity, And Backfill Review

- [x] Final matrix identity has production / provisional / audit separation.
- [x] Backfill cannot silently create final matrix identity.
- [x] Detected-cell region audit parity is implemented.
- [x] Owner backfill seed audit exists.
- [x] Family MS1 overlay review exists.
- [x] Low MS1 assessable coverage audit exists.
- [x] Seed-aware backfill review exists as shadow gate candidate.
- [~] Seed-aware rule is not a production gate yet.
- [~] Many rescued-heavy families remain `not_assessable` until seed-specific
  overlays are generated.
- [~] Neighboring interference still blocks automatic escalation for key
  families.

Current reference points:

- `xic_extractor/alignment/cell_region_audit.py`
- `xic_extractor/alignment/owner_backfill.py`
- `tools/diagnostics/family_ms1_backfill_review_report.py`
- `tools/diagnostics/family_ms1_overlay_evidence.py`
- `tools/diagnostics/seed_aware_backfill_review.py`
- `docs/superpowers/notes/2026-05-19-seed-aware-backfill-review-index.md`
- `docs/superpowers/notes/2026-05-19-untargeted-ms1-coherence-backfill-review.md`

Relationship to Level 2.5 RT shadow gate:

- Seed-aware backfill review answers: does rescued-heavy MS1 evidence look like
  the same feature family, or is it likely neighboring interference / weak
  shape / missing seed context?
- Level 2.5 RT shadow gate answers: is the row's RT behavior locally supported
  by both clean-standard RT evidence and biological ISTD transfer evidence?
- These are complementary evidence axes, not replacements.
- `FAM004459` remains a good counterexample: even if RT support is available,
  high neighboring MS1 interference should keep it in review-only status. RT
  evidence alone must not rescue a family whose MS1 shape context is conflicted.
- Future production-gate experiments should require both axes to agree:
  seed-specific MS1 shape support, low neighboring interference, and local
  biological-ISTD-supported RT context.

### 7. Instrument QC And Calibration Productization

- [x] Method / sequence docs are the first-class source for injection order.
- [x] SDO/LEK clean-standard trend extraction exists.
- [x] Mix STDs audit exists.
- [x] HCD / CID product-ion audit exists as review evidence.
- [x] Instrument QC workbook is the primary human review surface.
- [x] Clean-standard RT model preview exists.
- [x] Biological QC ISTD transfer audit exists.
- [x] Calibration maturity gate exists for Level 2 through Level 5 decisions.
- [x] Level 2.5 RT-supported shadow gate exists as row-level audit /
  alignment-support evidence.
- [x] RT x MS1 backfill cross-evidence diagnostic exists as audit-only
  follow-up.
- [~] Level 2 RT-aware audit / alignment-support is `go`.
- [~] Level 2.5 8RAW smoke is `shadow_gate_ready`, with 430
  `rt_supported_shadow_candidate` rows.
- [x] Scope-matched 85RAW RT x MS1 cross-evidence smoke exists:
  101 seed-aware families, 20756 RT families, and all 101 seed-aware families
  have matching RT rows.
- [~] Scope-matched cross-evidence is still review-only. It identifies only 2
  `rt_ms1_supported_review_candidate` families; most rows remain RT-only or
  RT-uncertain review cases.
- [x] Cross-evidence now reports `evidence_grade`, `blocking_evidence`, and
  `missing_evidence` so RT uncertainty is treated as missing confirmation, not
  as negative evidence.
- [x] Cross-evidence now reports `current final matrix status x evidence grade`.
  In the 85RAW seed-aware scope, all 101 reviewed families are already in the
  current FinalMatrix with accepted rescue values.
- [~] Level 3 RT production correction is `no_go`.
- [ ] Level 4 response shadow model is not implemented.
- [ ] Level 5 response production correction is not implemented.

Current reference points:

- `scripts/run_instrument_qc.py`
- `xic_extractor/instrument_qc/pipeline.py`
- `xic_extractor/instrument_qc/hcd_evidence.py`
- `xic_extractor/instrument_qc/calibration_product_preview.py`
- `xic_extractor/instrument_qc/rt_transfer_audit.py`
- `xic_extractor/instrument_qc/calibration_maturity_gate.py`
- `tools/diagnostics/instrument_qc_matrix_calibration_preview.py`
- `tools/diagnostics/instrument_qc_biological_istd_transfer_audit.py`
- `tools/diagnostics/instrument_qc_calibration_maturity_gate.py`
- `tools/diagnostics/instrument_qc_rt_supported_shadow_gate.py`
- `tools/diagnostics/rt_ms1_backfill_cross_evidence.py`
- `docs/superpowers/notes/2026-05-21-instrument-qc-rt-aware-midterm-preview.md`
- `docs/superpowers/notes/2026-05-21-instrument-qc-level3-no-go-convergence.md`
- `docs/superpowers/notes/2026-05-21-instrument-qc-level2-5-rt-supported-shadow-gate-validation.md`
- `docs/superpowers/specs/2026-05-21-rt-ms1-backfill-cross-evidence-spec.md`

### 8. Human Review Surfaces

- [x] Targeted evidence HTML report exists.
- [x] Alignment decision HTML report exists.
- [x] Instrument QC workbook is usable for manual review.
- [x] Overlay plot conventions were improved and documented.
- [~] Some diagnostic tools are still too broad and should be split when they
  become the next active maintenance target.
- [~] Human-facing reports still need continued reduction: machine TSVs can stay
  wide, but review surfaces should summarize first and drill down second.

Current reference points:

- `tools/diagnostics/targeted_evidence_review_report.py`
- `tools/diagnostics/alignment_decision_report.py`
- `xic_extractor/instrument_qc/workbook.py`
- `docs/superpowers/notes/2026-05-19-seed-aware-backfill-review-index.md`

### 9. Explicitly Not Done Or Deferred

- [-] GC-MS pipeline.
- [-] mzML conversion / Parquet cache as default architecture.
- [ ] ML / DL model.
- [ ] Adaptive ROI / Kalman-like trace tracking.
- [ ] Full production local mixture resolver.
- [ ] Production RT correction.
- [ ] Production response / area correction.
- [ ] Downstream DNP / statistical compatibility for corrected matrix.

## Next PR Candidates

### Candidate A: Level 2.5 RT-Supported Shadow Gate Follow-up

The first Level 2.5 implementation now exists on
`codex/handoff-level2-rt-shadow-gate`.

Current result:

- 8RAW smoke verdict: `shadow_gate_ready`.
- `rt_supported_shadow_candidate`: 430 rows.
- Scope-matched 85RAW Level 2.5 gate verdict: `shadow_gate_ready`.
- Scope-matched 85RAW RT x MS1 cross-evidence:
  - seed-aware families evaluated: 101;
  - families with matching RT context: 101;
  - `rt_ms1_supported_review_candidate`: 2 families;
  - `rt_supported_ms1_interference_review`: 2 families;
  - `ms1_supported_rt_uncertain_review`: 3 families;
  - `rt_only_review`: 40 families;
  - `rt_uncertain_review`: 48 families.
- Scope-matched evidence grades:
  - `A_dual_axis_supported`: 2 families;
  - `B_ms1_shape_supported_rt_unconfirmed`: 3 families;
  - `C_manual_review_interference`: 5 families;
  - `D_single_axis_or_not_ready`: 91 families.
- Current FinalMatrix overlap:
  - Grade A: 2 families already in matrix, 159 accepted rescue cells.
  - Grade B: 3 families already in matrix, 239 accepted rescue cells.
  - Grade C: 5 families already in matrix, 387 accepted rescue cells.
  - Grade D: 91 families already in matrix, 6519 accepted rescue cells.
- Output remains audit-only: no RT, area, reliability, scoring, resolver, DNP,
  or matrix mutation.

Key family interpretation from the scope-matched run:

- `FAM010804` and `FAM020262`: both axes agree, so they are review candidates
  for a future opt-in gate design.
- `FAM012728` and `FAM016922`: RT support exists, but neighboring MS1
  interference keeps them review-only.
- `FAM020034`, `FAM020336`, and `FAM020381`: Grade B. Seed-aware MS1 shape is
  supported; RT support is unconfirmed/uncertain, not contradictory.
- `FAM004459`, `FAM006664`, and `FAM014256`: Grade C. These remain review-only
  because neighboring MS1 interference is a blocker; RT uncertainty is secondary.

This means the current production backfill is broader than the new evidence
grades. The new work is not adding missing matrix values; it is measuring which
existing FinalMatrix backfills have enough evidence, which are MS1-supported but
RT-unconfirmed, and which have interference or single-axis risk.

Useful follow-up:

- Review the 2 `rt_ms1_supported_review_candidate` families manually before any
  production-gate planning.
- If the 2 families look scientifically plausible, write a narrow opt-in gate
  plan requiring both seed-aware MS1 shape support and local biological-ISTD RT
  support.
- Keep `neighbor_interference_review`, `shape_insufficient_review`, or
  `rt_model_uncertain` rows as review-only.
- Do not use RT support alone to override MS1 interference.

### Candidate B: Response Shadow Evidence

Only after Level 2.5 is stable.

Goal:

- Model response / intensity / area drift as shadow evidence.
- Separate clean-matrix standards from biological ISTD transfer.
- Do not scale production matrix.

Blockers:

- No response model yet.
- No biological response transfer audit yet.
- No downstream compatibility evidence.

### Candidate C: Seed-Aware Backfill Production Gate Candidate

Only after more seed-specific overlays are generated.

Goal:

- Convert the current seed-aware review rule into an opt-in production gate
  candidate.

Required protections:

- active ISTDs and known high-confidence targets require explicit review rules,
- neighboring interference blocks automatic promotion,
- low assessable coverage cannot silently demote,
- 8RAW then 85RAW strict benchmarks must not regress.

### Candidate D: Diagnostic Tool Responsibility Cleanup

This is architecture work, not scientific behavior.

Goal:

- Split broad diagnostic tools into loader, model, classifier, writer, and
  renderer modules.
- Preserve TSV / JSON / Markdown / HTML outputs.

Good targets:

- `tools/diagnostics/alignment_decision_report.py`
- `tools/diagnostics/seed_aware_backfill_review.py`
- `tools/diagnostics/instrument_qc_matrix_calibration_preview.py`
- `tools/diagnostics/instrument_qc_calibration_maturity_gate.py`

## Current Recommended Direction

The next scientific PR should not jump to production correction.

Recommended order:

1. Keep the Level 2.5 RT-supported shadow gate as audit evidence, not
   production correction.
2. Manually inspect the 2 Grade A families: `FAM010804` and `FAM020262`.
3. Also inspect the 3 Grade B families: `FAM020034`, `FAM020336`, and
   `FAM020381`; these may be strong MS1-backed candidates even without RT
   confirmation.
4. If manual review supports Grade A/B families, write a narrow opt-in
   production-gate plan with separate handling for:
   - Grade A: dual-axis evidence;
   - Grade B: MS1-backed evidence with neutral/missing RT confirmation.
5. Keep FAM004459-like Grade C cases out of automatic rescue unless neighboring
   MS1 interference is resolved by stronger evidence.
6. Decide whether Grade D current FinalMatrix backfills should stay as-is,
   move to review/provisional, or require additional MS1 overlay evidence.
7. Add response shadow evidence only after the RT/MS1 combined evidence table is
   accepted as interpretable.
8. In parallel or between scientific PRs, split oversized diagnostic tools.

This preserves the useful evidence accumulated so far while avoiding a premature
production matrix mutation.
