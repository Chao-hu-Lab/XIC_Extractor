# Claim Registry Hot Path Decision

**Date:** 2026-05-20  
**Branch:** `codex/claim-registry-hot-path`  
**Decision:** `optimized_equivalent`

## Summary

The `claim_registry` hot path now caches each active fuzzy claim group's winner
sort key after it is first computed. This preserves complete-link grouping,
winner tie-break order, exact-duplicate handling, and all matrix/cell output
semantics.

No matrix identity, production gate, scoring, reliability, TSV/XLSX schema, or
pipeline ordering behavior changed.

## Benchmark Fixture Shape

The deterministic operation-count fixture uses synthetic `AlignmentMatrix`
inputs only:

- many samples with one claim each;
- one sample with many compatible claims;
- one sample with many sparse m/z groups;
- exact duplicate claims outside the fuzzy m/z gate.

The fixture calls the public `apply_ms1_peak_claim_registry()` entry point and
uses test-local instrumentation around private helpers to count:

- exact peak key calls;
- fuzzy compatibility checks;
- group sort key evaluations;
- winner sort key evaluations;
- duplicate replacement calls.

## Operation-Count Evidence

Representative hot path: one sample with six mutually compatible fuzzy claims.

| metric | before | after |
|---|---:|---:|
| exact peak key calls | 6 | 6 |
| fuzzy compatibility checks | 15 | 15 |
| group sort key evaluations | 5 | 5 |
| winner sort key evaluations | 26 | 12 |
| duplicate replacement calls | 1 | 1 |

The optimization intentionally does not reduce complete-link compatibility
checks, because doing so would change the core grouping semantics. It only
removes repeated winner-key recomputation while keeping group choice identical.

Sparse and single-claim scenarios remain unchanged:

- many samples / one claim each: no compatibility or winner-key calls;
- sparse m/z groups: no compatibility or winner-key calls;
- exact duplicate outside fuzzy m/z gate: exact duplicate path still resolves
  the loser before fuzzy grouping.

## Validation

```powershell
uv --cache-dir .uv-cache run pytest tests\test_alignment_claim_registry.py tests\test_alignment_claim_registry_hot_path.py -q
uv --cache-dir .uv-cache run pytest tests\test_alignment_owner_backfill.py tests\test_alignment_tsv_writer.py tests\test_alignment_pipeline.py -q
uv --cache-dir .uv-cache run pytest tests\test_untargeted_final_matrix_contract.py tests\test_alignment_production_decisions.py -q
uv --cache-dir .uv-cache run ruff check xic_extractor\alignment\claim_registry.py tests\test_alignment_claim_registry.py tests\test_alignment_claim_registry_hot_path.py
uv --cache-dir .uv-cache run mypy xic_extractor
```

Results:

- claim registry tests: `15 passed`;
- alignment owner/writer/pipeline shard: `61 passed`;
- final matrix / production decision shard: `14 passed`;
- ruff: passed;
- mypy: passed.

## Follow-Up

Do not broaden this PR into `clustering.py`, `family_integration.py`, or
`owner_backfill.py`. If additional production hot path work is needed, start
with a separate characterization/benchmark checkpoint for the target module.
