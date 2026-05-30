# Shared Peak Identity V1.5 / V2 Implementation Plan

## Decision

V1.5 clarifies that expected blast-radius manifests are freshness guards only,
not evidence-chain proof. V2 can therefore run as an exploratory
`diagnostic_only` shadow-label alignment even when the blast-radius surface is
not `present_current`; the V2 readiness row owns the final answer.

## Scope

Now:

- Add V2 shadow-label schemas and token contracts.
- Map Slice 0 explanation classes to shadow labels and alignment status.
- Add a literature-backed machine-evidence provenance sidecar so V2 can
  distinguish machine-observed evidence from machine proxies and
  manual-oracle-derived facts.
- Allow the sidecar to consume optional CWT shape evidence and Tier2 raw-trace
  evidence sidecars as machine-observed but diagnostic-only support, with CWT
  limited to shape-tag evidence rather than chemical identity evidence.
- Add a fail-closed `--candidate-ms2-pattern-evidence-tsv` input contract keyed
  by `feature_family_id + sample_stem`, so sample/candidate-aligned MS2 pattern
  support or conflict can be consumed without RT/mz heuristic joins.
- Add a matching `--candidate-ms2-pattern-batch-index` producer that generates
  `shared_peak_identity_candidate_ms2_pattern_evidence.tsv` from the same
  discovery batch index used by the alignment run, but only for rows whose
  `source_candidate_id` resolves to a discovery candidate.
- Add an opt-in `--candidate-ms2-pattern-raw-dll-dir` fallback for rows without
  `source_candidate_id`. The fallback may only reuse the existing RAW reader and
  neutral-loss helper against alignment-cell boundaries; it remains
  `diagnostic_only` and must treat missing DDA/product evidence as
  `not_observed`, not chemical absence.
- Extend generated MS1 pattern coherence evidence with a diagnostic-only
  peak-quality feature vector when `family_ms1_overlay_*` trace-data JSON
  provides RAW-backed `rt` / `intensity` arrays. This is an optional schema
  expansion of `shared_peak_identity_ms1_pattern_coherence_evidence.tsv`, not a
  new entrypoint or product scoring rule.
- Emit V2 row-level labels, summary, readiness, and report from the existing
  diagnostic CLI.
- Update the diagnostic index and spec wording so old 85RAW freshness is not
  confused with semantic validation.
- Run focused tests and a real current-artifact diagnostic.

Later:

- Rebuild a fresh 85RAW evidence-chain diagnostic if V2 needs to move from
  `exploratory_only` to `shadow_ready_candidate`.
- Calibrate the machine-only RAW-backed MS1 peak-quality feature vector against
  a stratified oracle before attempting V2 product labels. The first implemented
  vector stays interpretable and diagnostic-only; do not train a CNN/ML model
  until a stratified oracle exists.
- Add machine-only pattern / opportunity metrics.
- Replace proxy provenance with actual machine metrics only after the metric
  implementation cites the relevant LC-MS peak-quality, MS/MS spectral
  similarity, DDA opportunity, or RT-alignment literature.
- Calibrate CWT shape evidence before using it outside this diagnostic sidecar,
  because CWT is a peak-shape observer only. In V2 it can satisfy shape tags
  when the CWT sidecar agrees, but it must not explain RT, MS2 pattern, DDA
  opportunity, matrix drift, or scope failures.

Not in scope:

- Production promotion.
- Workbook or matrix mutation.
- New full RAW extraction run or production RAW-dependent gate. The only RAW
  access in scope is the opt-in diagnostic boundary probe above.
- Treating non-seed rows as manual truth.

## Acceptance

- `--enable-shadow-label-alignment` writes:
  `shared_peak_identity_shadow_labels.tsv`,
  `shared_peak_identity_shadow_alignment_summary.tsv`,
  `shared_peak_identity_v2_readiness.tsv`,
  `shared_peak_identity_machine_evidence_support.tsv`, and
  `shared_peak_identity_v2_report.md`.
- `--cwt-shape-evidence-tsv` and `--tier2-trace-evidence-tsv` can upgrade the
  support sidecar from proxy-only to machine-observed partial or sufficient row
  evidence when every decisive tag is machine-observed, but cannot mark the
  labeler ready while pattern / DDA / conflict-policy blockers remain.
- `--candidate-ms2-pattern-evidence-tsv` can close
  `candidate_aligned_ms2_pattern` only when it provides sample/candidate-aligned
  `conflict` evidence for a manual `pattern_mismatch`; supportive evidence
  against a mismatch is reported as `pattern_metric_not_supportive`.
- `--candidate-ms2-pattern-batch-index` writes a generated sidecar and feeds it
  back into V2. Rows without `source_candidate_id` must stay `not_available`
  rather than inferred from target labels or RT/mz proximity.
- If `--candidate-ms2-pattern-raw-dll-dir` is also provided, rows without
  `source_candidate_id` may become `sample_boundary_aligned` only through the
  existing RAW reader / neutral-loss helper and alignment-cell boundary context.
  `OK` neutral-loss/product observations may be `supportive`; `WARN`
  observations (`nl_ppm_warn < best_ppm <= nl_ppm_max`, currently `20..50 ppm`
  for the targeted DNA contract) are `partial_support`, not absence. A
  `conflict` requires either direct/source NL evidence outside `nl_ppm_max` or a
  boundary-aligned precursor MS2 trigger plus a decisive non-matching base peak
  outside the diagnostic product window. Other missing or weak product evidence
  remains `not_observed`.
- `--generate-ms1-pattern-coherence-evidence` plus
  `--ms1-pattern-coherence-overlay-trace-data-json` writes optional
  `peak_quality_*` columns when the overlay JSON includes RAW-backed
  `rt` / `intensity` vectors. The vector reports trace point count, boundary
  point count, S/N proxy, FWHM, sharpness, zigzag/noise, tailing, boundary
  margin, status, basis, and reason. Older overlay JSON without vectors remains
  readable but does not close the richer formal shape evidence chain.
- If blast radius is unpinned or unassessed, V2 still writes artifacts but
  reports `v2_gate_status=exploratory_only` and
  `machine_only_labeler_ready=FALSE`.
- If a future run has `blast_radius_assessed=present_current`,
  `max_overfit_risk=low`, zero stale artifacts, no seed contradictions, high
  seed alignment, and machine-observed decisive evidence, the readiness row may
  report `shadow_ready_candidate`.
- Tests cover schema constants, token vocabulary, shadow-label mapping,
  machine-evidence provenance, readiness gate behavior, writer output, and CLI
  integration.

## Literature Guard

Do not promote a metric because it sounds intuitively reasonable. The current
V2 sidecar records these literature anchors:

- peak shape / XIC quality: Tautenhahn 2008 centWave, Zhang 2014 EIC quality,
  Kumler 2023 peak quality;
- MS2 / neutral-loss pattern: product-ion / neutral-loss annotation evidence,
  Watrous 2012 GNPS molecular networking, Huber 2021 Spec2Vec, Biesinger 2022
  modified-cosine / neutral-loss comparison;
- DDA opportunity: Koelmel 2017 iterative exclusion and 2017 target-directed
  DDA coverage work;
- RT drift / orthogonal evidence: Prince 2006 OBI-Warp and Sumner 2007 MSI
  chemical-analysis reporting standards.

Any new shape, MS2-pattern, DDA-opportunity, RT-drift, or matrix-behavior rule
that lacks a paper or official-method anchor stays exploratory and must not
promote/reject rows or close V2 blockers.

## DeepResearch Intake For Next Checkpoint

The user-supplied external local markdown
`Feature Recognition_deepresearch_MLDL_chatgpt_deepresearch.md` is now part of
the design context for the next V2 checkpoint. It remains uncommitted and is not
a product authority, because its embedded citations still need paper or
official-doc verification before any rule closes a blocker.

Actionable interpretation:

- Preserve the two-stage strategy: current alignment/rescue/backfill artifacts
  generate candidates for recall; V2 evidence sidecars judge peak quality and
  label alignment for precision.
- Extend `family_ms1_overlay_*` RAW-backed evidence into an interpretable
  peak-quality vector before considering ML/DL. NeatMS-style fixed-length trace
  plus boundary mask is a useful artifact shape, but not a model-training
  commitment.
- Add a small stratified oracle plan before any classifier work. Stratification
  must include intensity, RT drift phase, matrix/sample type, boundary quality,
  MS2/DDA opportunity, and failure mode; `human_unjudgeable` remains a held-out
  label, not binary training data.
- Add injection-local QC MS1 pattern context as an RT-drift support surface when
  a reliable injection-order source is available: compare the reviewed sample
  against the nearest / nearby-injection QC pattern, carry the QC provenance, and
  keep the signal diagnostic-only until a later contract defines promotion
  behavior.
- Evaluate future classifier-like evidence on paired raw-file/sample units with
  precision/recall/F1 or PR-AUC/calibration context. Do not count thousands of
  peaks from one sample as independent proof.
- Keep profile-mode PeakBot / 3D-MSNet-style work as research-only unless a
  separate spec funds raw annotation, GPU/model maintenance, and benchmark
  infrastructure.

The next implementation plan should therefore target:

```text
diagnostic-only MS1 peak-quality feature-vector sidecar
```

not:

```text
V2 product label promotion
```
