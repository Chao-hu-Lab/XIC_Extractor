# Shared Peak Identity V2 Diagnostic Note

## Verdict

V2 completed as `exploratory_only`.

The current seed-row shadow labels can organize the manual semantics, but the
machine-only evidence chain is not ready for autonomous pass/fail labels.

After the literature-backed provenance update, the more precise verdict is:
the current machine status labels are often directionally close to manual labels,
but the decisive shape / pattern / opportunity facts are still proxy-only or
manual-oracle-derived rather than machine-observed.

After adding optional CWT-shape and Tier2 raw-trace evidence inputs, the current
verdict is sharper again: machine-observed evidence is now present but partial.
CWT and raw-trace sidecars remove the need to call shape and intensity
opportunity entirely manual-derived, but they expose conflicts and still do not
provide candidate-aligned MS2 / neutral-loss pattern evidence or a DDA
opportunity policy.

After adding literature-guarded CID neutral-loss / product-ion context from
`alignment_review.tsv`, family-level pattern context is recorded only as
context/proxy evidence. It can explain why a family-level DNA-dR-like hypothesis
is plausible, but it no longer closes row-level `formal_pattern_metric`.
Row-level pattern evidence must come from a candidate/source-aligned sidecar or
the explicit RAW-boundary fallback described below.

After tightening CWT conflict semantics and support-status accounting, rows are
counted as `machine_observed_sufficient` when all decisive manual tags have
machine-observed basis and `missing_machine_evidence` is empty. CWT now compares
only against manual shape tags; it no longer treats every manual `fail` as a
shape failure. RT conflict also has a machine-observed component when
`rt_delta_sec` exceeds the alignment preferred RT window.

The follow-up implementation adds a fail-closed
`--candidate-ms2-pattern-evidence-tsv` input contract and a matching
`--candidate-ms2-pattern-batch-index` producer for sample/candidate-aligned MS2
pattern evidence. The real run below now generates
`shared_peak_identity_candidate_ms2_pattern_evidence.tsv` from the same 8RAW
discovery batch index that fed the alignment run. This intentionally does not
use `output/peak_candidates.tsv`, because that file is target-label oriented and
does not provide a reviewed `feature_family_id + sample_stem` join for these
oracle rows.

The latest checkpoint adds an opt-in RAW-backed fallback for rows that lack
`alignment_cells.source_candidate_id`. It reuses the existing Thermo RAW reader
and `neutral_loss.collect_candidate_ms2_evidence`; it does not add a new MS/MS
interpretation model. The fallback is deliberately conservative after literature
review: strict neutral-loss / product-ion observations may support a row, but
missing DDA product evidence is not treated as absence. A conflict is reported
only when a boundary-aligned precursor MS2 scan exists and the nearest
non-matching product peak is the spectrum base peak outside the diagnostic
product window.

## Run

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.shared_peak_identity_explanation `
  --manual-oracle-tsv docs\superpowers\fixtures\shared_peak_identity_manual_oracle_v1.tsv `
  --alignment-review-tsv output\tiered_backfill_candidate_gate_8raw_current\alignment_review.tsv `
  --alignment-cells-tsv output\tiered_backfill_candidate_gate_8raw_current\alignment_cells.tsv `
  --candidate-gate-tsv output\tier2_v0_1_coherence_8raw_current_gate\alignment_production_candidate_gate.tsv `
  --enable-blast-radius `
  --blast-radius-8raw-run output\tiered_backfill_candidate_gate_8raw_current `
  --blast-radius-85raw-run output\tiered_backfill_candidate_gate_85raw_current `
  --optional-blast-radius-artifact candidate_gate_8raw=output\tiered_backfill_candidate_gate_8raw_current\alignment_production_candidate_gate.tsv `
  --optional-blast-radius-artifact candidate_gate_85raw=output\tiered_backfill_candidate_gate_85raw_current\alignment_production_candidate_gate.tsv `
  --enable-shadow-label-alignment `
  --cwt-shape-evidence-tsv output\tier2_v0_1_coherence_8raw_current\alignment_tier2_cwt_manual_agreement_probe_relaxed.tsv `
  --tier2-trace-evidence-tsv output\tier2_v0_1_coherence_8raw_current\alignment_tier2_trace_evidence.tsv `
  --candidate-ms2-pattern-batch-index local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv `
  --candidate-ms2-pattern-raw-dll-dir C:\Xcalibur\system\programs `
  --output-dir output\shared_peak_identity_evidence_explanation_v2
```

## Output

- `output/shared_peak_identity_evidence_explanation_v2/shared_peak_identity_shadow_labels.tsv`
- `output/shared_peak_identity_evidence_explanation_v2/shared_peak_identity_shadow_alignment_summary.tsv`
- `output/shared_peak_identity_evidence_explanation_v2/shared_peak_identity_v2_readiness.tsv`
- `output/shared_peak_identity_evidence_explanation_v2/shared_peak_identity_candidate_ms2_pattern_evidence.tsv`
- `output/shared_peak_identity_evidence_explanation_v2/shared_peak_identity_machine_evidence_support.tsv`
- `output/shared_peak_identity_evidence_explanation_v2/shared_peak_identity_v2_report.md`

## Key Facts

- `v2_gate_status`: `exploratory_only`
- `machine_only_labeler_ready`: `FALSE`
- `semantic_generalization_evidence`: `seed_only_manual_oracle_derived`
- `machine_evidence_basis`: `machine_observed_partial`
- `machine_evidence_supported_rows`: `12`
- `machine_observed_partial_rows`: `9`
- `machine_observed_conflict_rows`: `7`
- `machine_proxy_only_rows`: `3`
- `manual_oracle_derived_rows`: `11`
- `machine_evidence_coverage_fraction`: `0.387097`
- `blast_radius_assessed`: `not_assessed`
- `max_overfit_risk`: `unassessed`
- `blast_radius_stale_artifact_count`: `0`
- seed rows total: `39`
- shadow rows total: `40` including one context row
- aligned or partial decision rows: `31`
- contradicted rows: `0`
- context-only rows: `1`
- human-unjudgeable rows: `8`

Current machine status-label proximity:

- `proxy_agrees`: `21`
- `proxy_partial`: `2`
- `proxy_contradicts`: `8`
- `not_evaluable`: `8`
- `context_only`: `1`

Machine evidence provenance after CWT/Tier2 sidecars, candidate-MS2 sidecar /
RAW-boundary fallback, and shape-tag-aligned CWT conflict semantics:

- `machine_observed_sufficient`: `12`
- `machine_observed_partial`: `9`
- `machine_observed_conflict`: `7`
- `blocked_missing_metric`: `3`
- `not_evaluable`: `8`
- `context_only`: `1`
- `pattern_basis_status=machine_observed`: `26`
- `pattern_basis_status=mixed`: `8`
- `pattern_basis_status=machine_proxy`: `5`
- `pattern_basis_status=not_available`: `1`

Candidate-MS2 producer status counts:

- `candidate_ms2_pattern_status=supportive`: `25`
  - `21` from RAW boundary fallback.
  - `4` from direct discovery source candidates.
- `candidate_ms2_pattern_status=not_observed`: `9`
- `candidate_ms2_pattern_status=not_available`: `4`
- `candidate_ms2_pattern_status=conflict`: `1`

Supportive rows from direct discovery source candidates:

- FAM000610 / TumorBC2263: `TumorBC2263_DNA#10747`, `ms2_support=strong`,
  `matched_tag_count=1`, `matched_tag_names=DNA_dR`.
- FAM001227 / TumorBC2312: `TumorBC2312_DNA#3290`, `ms2_support=moderate`,
  `matched_tag_count=1`, `matched_tag_names=DNA_dR`.
- FAM001589 / TumorBC2312: `TumorBC2312_DNA#5954`, `ms2_support=moderate`,
  `matched_tag_count=1`, `matched_tag_names=DNA_dR`.
- FAM002175 / TumorBC2263: `TumorBC2263_DNA#26931`, `ms2_support=moderate`,
  `matched_tag_count=1`, `matched_tag_names=DNA_dR`.

FAM000144 remains fail-closed for candidate-aligned MS2 evidence:

FAM000144 now shows the intended distinction:

- BenignfatBC1151 still emits `not_available` because the current alignment cell
  is `absent` and has no boundary context for RAW MS2 probing.
- NormalBC2312 emits `supportive / sample_boundary_aligned`: `3` precursor MS2
  triggers in the boundary probe, `1` strict neutral-loss/product match,
  `best_loss_ppm=9.70487`, `raw_ms2_trace_strength=moderate`.
- TumorBC2312 emits `conflict / sample_boundary_aligned`: `1` boundary-aligned
  precursor MS2 trigger, `0` strict neutral-loss/product matches,
  `diagnostic_product_absence_reason=product_outside_diagnostic_window`, nearest
  product loss error `147223 ppm`, nearest product base ratio `1.0`. This closes
  the earlier `candidate_aligned_ms2_pattern` blocker for this reviewed fail
  row without using an RT/mz heuristic join.

Rows currently counted as machine-observed sufficient:

- FAM000144: TumorBC2312.
- FAM000610: BenignfatBC1151, QC3, QC5, NormalBC2263, NormalBC2312,
  TumorBC2312.
- FAM001227: QC5, TumorBC2312.
- FAM002175: QC3, QC5, TumorBC2263.

## Required Evidence To Promote

The dominant missing or conflicting machine evidence is:

- `shape_metric_not_supportive`: `14`
- `formal_pattern_metric`: `8`
- `human_review_or_retire_from_training`: `8`
- `dda_opportunity_policy`: `6`
- `manual_scope_policy`: `3`
- `sample_level_negative_evidence`: `3`
- `matrix_rt_drift_policy`: `2`
- `delta_mass_family_model`: `1`

The V2 readiness artifact additionally reports these active machine-evidence
blockers after CWT/Tier2 evidence and CID/NL context:

- `dda_opportunity_policy`
- `formal_pattern_metric`
- `shape_metric_not_supportive`
- `manual_scope_policy`
- `sample_level_negative_evidence`
- `matrix_rt_drift_policy`

## Verification

```powershell
python -m pytest tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_candidate_ms2_pattern.py tests\test_shared_peak_identity_cli.py -q
# 28 passed

python -m pytest tests -q -k shared_peak_identity
# 77 passed, 2607 deselected

uv --cache-dir .uv-cache run ruff check xic_extractor\alignment\shared_peak_identity_explanation tools\diagnostics\shared_peak_identity_explanation.py tests\test_shared_peak_identity_schema.py tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_candidate_ms2_pattern.py tests\test_shared_peak_identity_cli.py
# All checks passed

uv --cache-dir .uv-cache run mypy xic_extractor\alignment\shared_peak_identity_explanation tools\diagnostics\shared_peak_identity_explanation.py
# Success: no issues found in 12 source files

git diff --check
# exit 0; CRLF warnings only
```

## Literature Guard

Future metric changes must cite primary literature or official method
documentation. The current support sidecar uses ref ids for:

- SciPy `find_peaks_cwt` / `find_peaks` / `peak_widths` official docs: CWT and
  peak properties are 1-D peak detection / shape evidence, not chemical identity
  evidence.
- LC-MS peak shape / EIC quality: Tautenhahn 2008 centWave, Zhang 2014 EIC
  quality, Kumler 2023 peak-quality metrics.
- MS2 / neutral-loss pattern: product-ion / neutral-loss annotation evidence,
  Watrous 2012 GNPS molecular networking, Huber 2021 Spec2Vec, Biesinger 2022
  modified-cosine / neutral-loss comparison.
- DDA opportunity: Koelmel 2017 iterative exclusion and 2017 target-directed
  DDA coverage work.
- RT drift / orthogonal evidence: Prince 2006 OBI-Warp and Sumner 2007 MSI
  chemical-analysis reporting standards.

## Interpretation

This closes the RAW-backed candidate-MS2 pattern checkpoint, still as a
diagnostic artifact rather than a product gate. The important change is that the
machine evidence chain now reproduces the key human distinction inside
FAM000144: NormalBC2312 has boundary-aligned NL/product support, while the
extra TumorBC2312 rescue has boundary-aligned precursor MS2 with a decisive
non-matching base peak.

The remaining blockers have shifted. The dominant semantic gaps are now DDA
opportunity policy, CWT/shape calibration conflicts on several manual-pass rows,
manual scope-derived negative evidence, and matrix RT-drift policy. Pinning old
85RAW artifacts would improve freshness accounting, but it still would not make
the labeler autonomous until those evidence rules are resolved.
