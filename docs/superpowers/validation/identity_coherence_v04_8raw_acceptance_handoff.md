# Identity Coherence V0.4 8RAW Acceptance Handoff

**Date:** 2026-05-24
**Status:** Accepted 8RAW diagnostic handoff
**Branch:** `codex/untargeted-backfill-logic-reset`

This handoff freezes the reviewed 8RAW method-acceptance evidence for the
untargeted identity-coherence diagnostic. It is diagnostic-only. It does not
clear 85RAW execution, production defaults, Backfill behavior, final-matrix
filtering, blank/QC/background filtering, area correction, normalization, or
statistics.

## Strict Acceptance Command

The accepted run used the reviewed controls manifest and strict V0.4 acceptance:

```powershell
uv run python scripts\validate_identity_coherence_8raw.py `
  --discovery-batch-index output\discovery\timing_phase0_8raw\discovery_batch_index.csv `
  --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
  --dll-dir "C:\Xcalibur\system\programs" `
  --output-root output\identity_coherence_8raw_validation_reviewed `
  --controls-manifest output\identity_coherence_8raw_validation\identity_coherence_controls_manifest_8raw.reviewed.tsv `
  --require-v04-acceptance
```

Observed terminal result:

```text
PASS identity_coherence_sidecar_parity summary=output\identity_coherence_8raw_validation_reviewed\identity_coherence_8raw_validation_report.md
PASS identity_coherence_v04_acceptance scope=8raw_method_review_only not_85raw_ready summary=output\identity_coherence_8raw_validation_reviewed\identity_coherence_v04_acceptance.md
```

## Accepted Outputs

```text
output\identity_coherence_8raw_validation_reviewed\
  identity_coherence_8raw_validation_summary.tsv
  identity_coherence_8raw_validation_report.md
  identity_coherence_v04_acceptance.tsv
  identity_coherence_v04_acceptance.md
```

Strict acceptance TSV:

```text
serial_process_sidecar_parity  pass
reviewed_controls_manifest    pass
positive_control_sensitivity  pass  # 5/5 serial and 5/5 process
identity_decoy_specificity    pass  # 0 promoted, 3/3 rejected
v04_acceptance                pass
```

Representative diagnostic counters from the serial sidecar summary:

```text
input_row_count = 2302
coherent_seed = 1705
review_only_seed_gate_failed = 597
would_primary_provisional_identity_family_support = 1387
raw_xic_request_count = 15118
xic_point_count = 125661
projected_85raw_identity_request_count = not_assessed
```

## Reviewed Controls Manifest

Reviewed manifest:

```text
output\identity_coherence_8raw_validation\identity_coherence_controls_manifest_8raw.reviewed.tsv
```

Manifest provenance:

```text
rows = 8
sha256 = A08F197E31E5F33C35035AB082488DC9F0B5494075BF6930CF9F4EBA42DE1FC6
```

The reviewed manifest contains:

- 3 `identity_decoy` controls copied from the current V0.4 proposal and reviewed
  for strict validation;
- 5 `positive_targeted_istd` controls mapped to current V0.4 8RAW frozen
  decision/family/seed IDs.

Controls are validation-only yardsticks. They do not promote identities and do
not filter the final matrix.

## Benchmark Sources

The positive controls were derived from the targeted ISTD benchmark output in
the `area-mismatch-production-fix` worktree.

8RAW benchmark source:

```text
C:\Users\user\Desktop\XIC_Extractor\.worktrees\area-mismatch-production-fix\output\diagnostics\untargeted_revalidation_after_targeted_fix_8raw\targeted_istd_benchmark\targeted_istd_benchmark_summary.tsv
rows = 7
sha256 = 32B3F4B4BD544A780ACA56A7C5FEBDDAE0FEFD56C6235C8434207CA8D3DDAE4D
```

85RAW benchmark reference:

```text
C:\Users\user\Desktop\XIC_Extractor\.worktrees\area-mismatch-production-fix\output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\targeted_istd_benchmark\targeted_istd_benchmark_summary.tsv
rows = 7
sha256 = 09D663F80ED26A2B22B50403A40E8A59A96323BAC103FAADFE5D0D230ACD6DC3
```

## Positive-Control Mapping

| Control | 8RAW benchmark | 85RAW benchmark | Decision | Family | Seed candidate | m/z error ppm | RT delta sec |
| --- | --- | --- | --- | --- | --- | ---: | ---: |
| `d3-5-hmdC` | PASS | PASS | `ICD000285` | `ICF000285` | `BenignfatBC1151_DNA#5012` | 7.659 | -3.633 |
| `d3-5-medC` | PASS | WARN | `ICD000092` | `ICF000092` | `BenignfatBC1055_DNA#9537` | 4.079 | 0.054 |
| `15N5-8-oxodG` | PASS | PASS | `ICD000206` | `ICF000206` | `BenignfatBC1055_DNA#13111` | 3.459 | -0.006 |
| `d3-N6-medA` | PASS | PASS | `ICD002276` | `ICF002276` | `TumorBC2312_DNA#21195` | 3.715 | -25.740 |
| `d3-dG-C8-MeIQx` | PASS | PASS | `ICD001456` | `ICF001456` | `NormalBC2263_DNA#35245` | 0.000 | 0.315 |

Excluded from strict 8RAW positive controls:

| Control | 8RAW benchmark | 85RAW benchmark | Reason |
| --- | --- | --- | --- |
| `d4-N6-2HE-dA` | PASS | PASS | no current V0.4 8RAW would-primary mapping within 20 ppm and 60 sec |

`d4-N6-2HE-dA` should be reconsidered during 85RAW control remapping. Its 8RAW
exclusion is a current-output mapping fact, not evidence that the control is
invalid.

## Handoff Boundary

This handoff closes only V0.4 8RAW method acceptance.

It permits the next roadmap step:

```text
85RAW cost and threshold policy preflight
```

It does not permit:

- direct 85RAW execution without a reviewed request-budget ceiling and
  count+fraction policy shape;
- production adoption;
- final-matrix filtering;
- blank/QC/background gating;
- Backfill behavior changes;
- using controls as identity promotion evidence.
