# 2026-06-12 8RAW Matrix-Only vs Deep-Audit Parity And Timing Note

Validation status: `8RAW_parity_passed`; `85RAW_not_run`.

This note records the fresh 8RAW gate for the `dna_dr` preset after the
diagnostics helper cleanup on branch `codex/backfill-diagnostics-architecture`.
It is a validation and bottleneck-positioning note, not a production behavior
change.

## Decision Closed

Product-facing outputs from `matrix-only` and `deep-audit` are identical on the
8RAW validation subset:

- activation decisions: identical
- activation value delta: identical
- activation acceptance: identical
- published matrix: identical
- published matrix identity: identical

The performance delta is therefore not a product-decision delta. It is an
artifact/rendering and review-surface cost delta.

## Commands

Preflight:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --preset dna_dr `
  --discovery-batch-index local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\standard_peak_publication_8raw_goal_matrix_only_20260612 `
  --expected-sample-count 8 `
  --output-level validation-minimal `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --raw-workers 8 `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --standard-peak-backfill-publication-mode matrix-only `
  --timing-output output\standard_peak_publication_8raw_goal_matrix_only_20260612\timing.json `
  --timing-live-output output\standard_peak_publication_8raw_goal_matrix_only_20260612\timing.live.json `
  --preflight-only
```

Matrix-only run:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --preset dna_dr `
  --discovery-batch-index local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\standard_peak_publication_8raw_goal_matrix_only_20260612 `
  --expected-sample-count 8 `
  --output-level validation-minimal `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --raw-workers 8 `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --standard-peak-backfill-publication-mode matrix-only `
  --timing-output output\standard_peak_publication_8raw_goal_matrix_only_20260612\timing.json `
  --timing-live-output output\standard_peak_publication_8raw_goal_matrix_only_20260612\timing.live.json
```

Deep-audit run:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --preset dna_dr `
  --discovery-batch-index local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\standard_peak_publication_8raw_goal_deep_audit_20260612 `
  --expected-sample-count 8 `
  --output-level validation-minimal `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --raw-workers 8 `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --standard-peak-backfill-publication-mode deep-audit `
  --timing-output output\standard_peak_publication_8raw_goal_deep_audit_20260612\timing.json `
  --timing-live-output output\standard_peak_publication_8raw_goal_deep_audit_20260612\timing.live.json
```

## Outputs

| Mode | Output dir | Exit | Wall time |
| --- | --- | --- | --- |
| matrix-only | `output\standard_peak_publication_8raw_goal_matrix_only_20260612` | 0 | 95 s |
| deep-audit | `output\standard_peak_publication_8raw_goal_deep_audit_20260612` | 0 | 972.1 s |

## Product Artifact Parity

| Artifact | Equal | SHA256 |
| --- | --- | --- |
| `alignment_matrix.tsv` | yes | `52e6289aa4351f19eda8224cd4218a8f06837b859f78b84d89f30d11d20b46d0` |
| `alignment_matrix_identity.tsv` | yes | `118022aaf7016df02eb1109283eaaa906851a4fa50e1767144825592cb79f38b` |
| `standard_peak_activation_value_delta.tsv` | yes | `3b4ec7c5b19fbc56fdab41c8bb402ba1c95967ba977f12fde855fa37f9b90bbf` |
| `standard_peak_activation_hypothesis_identity.tsv` | yes | `4b5c6f6c5aa94592bccdfa10ae2894d506bdb07965afbfb7c17c491a437d9479` |
| `standard_peak_activation_application_summary.tsv` | yes | `3e81e21b66ad6c5ee224817299aa6f957d0eadd9e3920a00ded17aaf67738a51` |
| consolidated activation decisions | yes | `bbd626e46de024e46d14c9552c7ea82e143d83feac9e6634655dbf749321a20a` |
| consolidated activation values | yes | `70c40904381772cb75d42213507c4789dc675d5de09103b9054744d4d62f89b4` |
| consolidated activation acceptance | yes | `ae2fd1652555a1de4d6eb82844777f11f299ded576d0aad11ee31dd4ed93d950` |

## Timing Findings

The new timing JSON derived summaries were used. Stage totals include nested
stage spans and should be read as bottleneck attribution, not wall-clock sum.

### Matrix-Only Top Stages

| Stage | Total seconds | Records |
| --- | ---: | ---: |
| `standard_peak.chunk` | 48.682 | 3 |
| `alignment.build_owners.extract_xic` | 21.597 | 8 |
| `alignment.owner_backfill.extract_xic` | 19.166 | 8 |
| `standard_peak.overlay_batch` | 18.550 | 3 |
| `alignment.owner_backfill` | 17.182 | 1 |
| `alignment.build_owners` | 16.528 | 1 |
| `standard_peak.shift_aware_batch` | 13.592 | 3 |
| `standard_peak.shift_aware_batch.row` | 12.602 | 273 |

Matrix-only RAW locality:

| Stage | RAW calls | XIC requests | RAW calls per XIC | Seconds |
| --- | ---: | ---: | ---: | ---: |
| `alignment.build_owners.extract_xic` | 3020 | 3343 | 0.9034 | 21.597 |
| `alignment.owner_backfill.extract_xic` | 56 | 5167 | 0.0108 | 19.166 |
| `standard_peak.overlay_batch` | 121 | 1977 | 0.0612 | 18.550 |

### Deep-Audit Top Stages

| Stage | Total seconds | Records |
| --- | ---: | ---: |
| `standard_peak.chunk` | 921.797 | 3 |
| `standard_peak.shift_aware_batch` | 673.996 | 3 |
| `standard_peak.shift_aware_batch.row` | 672.822 | 273 |
| `standard_peak.overlay_batch` | 234.403 | 3 |
| `alignment.build_owners.extract_xic` | 18.977 | 8 |
| `alignment.owner_backfill` | 17.232 | 1 |
| `alignment.owner_backfill.extract_xic` | 16.022 | 8 |

Deep-audit RAW locality:

| Stage | RAW calls | XIC requests | RAW calls per XIC | Seconds |
| --- | ---: | ---: | ---: | ---: |
| `standard_peak.overlay_batch` | 121 | 1977 | 0.0612 | 234.403 |
| `alignment.build_owners.extract_xic` | 3020 | 3343 | 0.9034 | 18.977 |
| `alignment.owner_backfill.extract_xic` | 56 | 5167 | 0.0108 | 16.022 |

## Interpretation

1. `matrix-only` is product-equivalent to `deep-audit` on the product-facing
   matrix, identity, activation decisions, activation values, and acceptance
   artifacts.
2. The remaining `deep-audit` cost is dominated by shift-aware row review
   rendering and full overlay/gallery behavior. This is not evidence for
   changing peak scoring, `raw_reader` window semantics, owner thresholds, or
   85RAW launch shape.
3. `standard_peak.overlay_batch` has good request reuse in both modes
   (`121` RAW chromatogram calls for `1977` XIC requests), but deep-audit spends
   far more time in that stage because it renders full review artifacts.
4. `alignment.build_owners.extract_xic` still has poor locality
   (`3020` RAW calls for `3343` XIC requests), matching prior locality findings:
   simple batching/sorting is unlikely to materially improve this stage without
   a broader algorithm or request-shape change.

## Stop Decision

No code optimization was applied after this gate.

The evidence points to two different next choices:

- For normal `dna_dr` publication, keep `matrix-only` as the default and do not
  optimize deep-audit rendering unless that review surface becomes a user-facing
  requirement.
- If deep-audit must become fast, the next safe target is shift-aware/gallery
  rendering reuse or lazy rendering, not RAW window semantics or peak scoring.

85RAW remains intentionally out of scope for this note.
