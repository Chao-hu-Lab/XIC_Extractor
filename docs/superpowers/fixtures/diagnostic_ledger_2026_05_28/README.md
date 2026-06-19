# Diagnostic Ledger Fixture Packet 2026-05-28

This directory is a frozen diagnostic-ledger evidence packet from 2026-05-28.
It is retained as historical evidence, not as an active product fixture or a
generated-output staging area.

Files stay here because `docs/diagnostic-ledger.md`, related notes, or this
packet README cite the packet or individual paths. Rerunning diagnostics should
write new output outside this dated snapshot unless a new ledger entry promotes
the new result.

Current SHA256 values are authoritative in
`docs/superpowers/fixtures/ARTIFACT_INVENTORY.tsv`.

## Observations

- `target_derived_review_row_triage.tsv` and
  `target_derived_review_row_triage_primary_delivery_fix.tsv` currently have
  identical SHA256 values. Keep the non-suffixed current snapshot as canonical;
  the primary-delivery-fix duplicate is retained as `archive_later` until ledger
  references are rewritten or summarized.
- `targeted_gt_alignment_audit_default_5medc_current_8raw_comparison.csv` and
  `targeted_gt_alignment_audit_default_5medc_primary_delivery_fix_comparison.csv`
  currently have identical SHA256 values. Keep the current comparison as
  canonical; the primary-delivery-fix duplicate is retained as `archive_later`
  until ledger references are rewritten or summarized.
- Several historical ledger or note hashes differ from current file hashes.
  Do not silently rewrite historical conclusions; use the inventory current
  SHA256 and the `next_action` drift note for cleanup follow-up.

## Hash Drift Notes

| Path | Referenced hash | Current SHA256 |
| --- | --- | --- |
| `85raw_primary_delivery_fix_summary.tsv` | `4CF19B045F850B205E23888F1B3C5A6E3AF1C0BEC0C516E4447B61738CEAC24B` | `DC655DA7A7713784BE183A94B990576EFA360D344016B8E40D630D00D57365CA` |
| `85raw_weak_seed_tolerated_watch_rows.tsv` | `E003FDEAC97E1DAE6E0D6AF929CDD7EA3A004BC9873A0340EF8A7B2E099683E4` | `BA635DCE2F410C539A6B3F5B0A850052CA16AF70897826CC7D673999860BB2D0` |
| `post_review_hardened_single_dr_gate_summary.tsv` | `43FE4E4BCFF9DD20CA6B16F183F7A414EE89DCF1657A7E2E3B20559E32DE48E3` | `5089929399B4D3E642BA6C869C3B8D140D58178C55283FB5C4B37528775FAF0A` |
| `phase1b_8raw_policy_delta.tsv` | `A889FEEE29682A12E274B273EF0DEC45BACCD7CBB6166D2BB97A55C6025083C3` | `3C22793B385AF0EECA030C96F2D6B497D4DE5C4227523BB264BAE63CA278A264` |
| `phase1b_85raw_policy_delta.tsv` | `EAA72BD296B4DBA270349583EEB799A9D2C98CC2BB32421D5317CF9C92CD70B2` | `14B126AAF40EBC1EEE84980E89AEE5B757CFAF8CFBCC16C63EE5E735F9A97D8B` |
| `phase1b_policy_delta_summary.tsv` | `533C74ABAE7313D2B8A52B3B963A63C2A5E4EF2B5F03905CEAABA35005CEB1BA` | `297CE32319BF7EEE8EFD155EE762A558984F0C943696B1072FD046F61762F2D6` |
