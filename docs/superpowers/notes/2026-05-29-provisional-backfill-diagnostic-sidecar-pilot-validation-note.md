# Provisional Backfill Diagnostic Sidecar Pilot Validation Note

## Verdict

`diagnostic_only`

The implementation emits `alignment_production_candidate_gate.tsv` as a machine
sidecar. It does not modify `alignment_review.tsv`, `alignment_matrix.tsv`,
workbook schemas, or downstream correction/statistics contracts.

## Source Artifacts

| Run | Alignment Dir | Sidecar Rows | Production Candidate Rows | Keep Provisional Rows | Audit Rows | Excluded Rows | Source Review SHA256 | Source Cells SHA256 | Source Matrix SHA256 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| 8RAW | `output\tiered_backfill_candidate_gate_8raw_current` | 7 | 0 | 7 | 0 | 0 | `6DD0DE5C80A6E5E7BDCFA00C70ABEC393AB16F152E8D1B4DC2F471E3A33DA2DD` | `4EDD5846AB77C714AD565BB8BF5C77925B0CE8E441817C75717F3996C3C6C2CA` | `FD6F11A03084CCBE3685DB3F3D997497ACE408B18E743D6DA2EB91837E443FC8` |
| 85RAW | `output\tiered_backfill_candidate_gate_85raw_current` | 7 | 0 | 7 | 0 | 0 | `4F6430DED2160C0D2051C9D294D33069558CE1DA840A3DDD7EA9513398CBA42A` | `7379DCF74910C1B027FB217C50D891ABEA0CD43F95E6DE6E5E86C0C3D0F5299B` | `2AC1ADDF5302477D46BEB46FC1C893877B40DE92AE05E77A7BFCE9D5DC9E5D57` |

## Commands

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.provisional_backfill_candidate_gate --alignment-dir output\tiered_backfill_candidate_gate_8raw_current --output-dir output\tiered_backfill_candidate_gate_8raw_current
.venv\Scripts\python.exe -m tools.diagnostics.provisional_backfill_candidate_gate --alignment-dir output\tiered_backfill_candidate_gate_85raw_current --output-dir output\tiered_backfill_candidate_gate_85raw_current
```

## Gate Interpretation

- `production_candidate` remains a sidecar status only.
- `production_ready=false` remains true in both JSON summaries.
- `matrix_contract_changed=false` remains true in both JSON summaries.
- The pilot allowlist currently accepts only `validated_tier2_trace_evidence` as
  independent positive Tier 2 support.
- All artifact-only retention candidates remain `keep_provisional` because the
  current inputs do not include allowlisted non-provenance Tier 2 positive
  support.

## Verification

```text
Focused pytest result: 31 passed in 1.47s
Ruff result: All checks passed!
Diff check result: git diff --check exited 0
```

## Acceptance Review

`validation-evidence-reviewer`, mode `acceptance`:

```text
run_ok=true
gate_ok=true
production_ready=false
inconclusive=false
```

Current subagent acceptance re-check confirmed `gate_ok=true`,
`production_ready=false`, and `inconclusive=false` for diagnostic-only
acceptance. The reviewer-local fresh pytest rerun was blocked by PyQt6 DLL
access denied, so the focused pytest line above records the main-agent rerun
performed outside the sandbox restriction.

## Next Action

Use the sidecar for diagnostic calibration and future promotion-contract
drafting. Do not promote any row into `alignment_matrix.tsv` without a separate
reviewed promotion contract.
