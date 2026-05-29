# Provisional Backfill Candidate Gate 85RAW Evidence Note

## Verdict

`diagnostic_only`

The 85RAW run supports continuing a selective Tier 2 sidecar experiment. It does
not prove that `production_candidate` is a production role, and it does not
authorize promotion into `alignment_matrix.tsv`.

## Decision Tested

The run tested whether the 8RAW retention-candidate subset was too narrow to be
useful, or whether a full 85RAW tissue set would make the candidate pool explode.

Result: the pool did not explode. The full 85RAW run still produced only seven
`provisional_retention_candidate` rows. The rows remain concentrated in
`DNA_dR` / `owner_complete_link`, so the next step should be a diagnostic
sidecar pilot that challenges those rows with Tier 2 evidence.

## Command

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index local_validation_artifacts\discovery\accepted_p8b\85raw\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\tiered_backfill_candidate_gate_85raw_current `
  --expected-sample-count 85 `
  --output-level validation-minimal `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --timing-output output\tiered_backfill_candidate_gate_85raw_current\timing.json `
  --timing-live-output output\tiered_backfill_candidate_gate_85raw_current\timing.live.json
```

Preflight passed before launch:

- discovery batch samples: 85;
- candidate CSVs found: 85;
- RAW paths found: 85;
- `expected-sample-count 85` canonical contract: enforced.

Foreground run completed successfully in about 617 seconds.

## Artifacts

```text
output\tiered_backfill_candidate_gate_85raw_current\alignment_review.tsv
output\tiered_backfill_candidate_gate_85raw_current\alignment_matrix.tsv
output\tiered_backfill_candidate_gate_85raw_current\alignment_cells.tsv
output\tiered_backfill_candidate_gate_85raw_current\skipped_evidence_ledger.tsv
output\tiered_backfill_candidate_gate_85raw_current\alignment_run_metadata.json
output\tiered_backfill_candidate_gate_85raw_current\timing.json
output\tiered_backfill_candidate_gate_85raw_current\timing.live.json
```

Hashes:

| Artifact | SHA256 |
| --- | --- |
| `alignment_review.tsv` | `4F6430DED2160C0D2051C9D294D33069558CE1DA840A3DDD7EA9513398CBA42A` |
| `alignment_matrix.tsv` | `2AC1ADDF5302477D46BEB46FC1C893877B40DE92AE05E77A7BFCE9D5DC9E5D57` |
| `alignment_cells.tsv` | `7379DCF74910C1B027FB217C50D891ABEA0CD43F95E6DE6E5E86C0C3D0F5299B` |

## Counts

| Metric | Count |
| --- | ---: |
| `alignment_review.tsv` rows | 21812 |
| `alignment_matrix.tsv` rows | 610 |
| `provisional_discovery` rows | 617 |
| provisional + one detected | 549 |
| provisional + one detected + rescue | 85 |
| `provisional_retention_candidate` rows | 7 |

Identity summary:

| Decision | Count |
| --- | ---: |
| `audit_family, FALSE` | 20585 |
| `provisional_discovery, FALSE` | 617 |
| `production_family, TRUE` | 610 |

## Retention Candidates

All seven candidates are `DNA_dR` rows with
`primary_evidence=owner_complete_link`.

| Family | m/z | RT | Reason | Rescue Count |
| --- | ---: | ---: | --- | ---: |
| `FAM000157` | 244.117 | 11.997 | `extreme_backfill_dependency` | 84 |
| `FAM008301` | 307.19 | 45.545 | `extreme_backfill_dependency` | 84 |
| `FAM013245` | 371.133 | 41.7996 | `insufficient_detected_identity_support` | 1 |
| `FAM014123` | 391.211 | 43.7349 | `extreme_backfill_dependency` | 84 |
| `FAM014855` | 407.207 | 43.3428 | `extreme_backfill_dependency` | 84 |
| `FAM017677` | 512.17 | 6.44265 | `insufficient_detected_identity_support` | 2 |
| `FAM020220` | 849.132 | 15.5817 | `insufficient_detected_identity_support` | 1 |

Candidate cell status summary:

| Status / Trace Quality | Count |
| --- | ---: |
| `rescued, owner_backfill` | 340 |
| `absent, absent` | 248 |
| `detected, owner_exact_apex_match` | 7 |

Rescued-cell scan support:

| Scan Support Score | Count |
| --- | ---: |
| `1` | 338 |
| `0.8` | 2 |

## Interpretation

The 85RAW run resolves the scale question:

- the candidate subset remains small;
- Tier 2 for the retention-candidate subset is computationally plausible;
- broad Tier 2 for all provisional rows is still not justified.

The run does not resolve the product-readiness question:

- candidates remain concentrated in one feature class;
- evidence still comes from owner-backfill provenance and Tier 1 fields;
- no independent Tier 2 evidence has been collected yet.

## Next Action

Proceed with a `diagnostic_only` sidecar pilot design. The pilot should classify
candidate rows as `keep_provisional`, `audit`, `excluded`, or
`production_candidate` only when at least one non-provenance Tier 2 support
component is available and all challenge checks pass.

Do not promote any row into `alignment_matrix.tsv` without a separate promotion
contract.
