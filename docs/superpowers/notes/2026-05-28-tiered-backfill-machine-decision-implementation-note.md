# Tiered Backfill Machine Decision Implementation Note

## Verdict

`diagnostic_only`

The first tiered-backfill machine-decision contract is implemented as a pure
projection over existing alignment review/cell artifacts. It does not change
`alignment_matrix.tsv` schema or primary inclusion semantics.

## Scope Implemented

- One-detected-seed rows with supported rescue evidence stay
  `identity_decision=provisional_discovery`.
- Such rows receive explicit row flags:
  `single_detected_seed`, `provisional_retention_candidate`, and
  `skip_expensive_evidence`.
- `xic_extractor.alignment.machine_decision.project_machine_decision()` maps
  existing review/cell fields to `matrix_role`, `evidence_tier`,
  `support_reasons`, `blockers`, `confidence`, and `recommended_action`.
- `tools/diagnostics/analyze_matrix_identity_blast_radius.py` displays the
  projected vector for machine gate review.

## Out Of Scope

- Tier 2 evidence routing.
- New `provisional-candidates` execution scope.
- Skipped-evidence ledger.
- New sidecar schema.
- `alignment_matrix.tsv` schema or primary-matrix inclusion changes.
- Fresh RAW validation.

## Verification

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_alignment_machine_decision.py tests\test_alignment_matrix_identity.py tests\test_alignment_tsv_writer.py tests\test_matrix_identity_blast_radius.py -q
```

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_untargeted_final_matrix_contract.py tests\test_targeted_gt_alignment_audit.py tests\test_targeted_istd_benchmark.py -q
```

```powershell
git diff --check
```

## Remaining Risk

The vector is currently a projection contract, not a new production schema.
Downstream correction/statistics tools remain protected because
`alignment_matrix.tsv` stays primary-only. If a later PR needs durable external
consumption of provisional rows, it should add a versioned sidecar with schema
tests and named consumers.

The implementation can be relabeled `shadow_ready` only after a current
existing-artifact smoke classification, or an explicitly hash-pinned 8RAW gate
artifact, proves the projection can split primary / provisional / audit /
excluded rows without new evidence collection.
