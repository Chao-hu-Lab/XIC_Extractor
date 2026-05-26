# P7 — Evidence Chain Cost Control Spec

**Date:** 2026-05-25
**Status:** Proposed; P7 stabilization reviewer fixes applied; ready for implementation-plan redrafting
**Overview:** [Peak pipeline modernization overview](2026-05-24-peak-pipeline-modernization-overview-spec.md)
**Depends on:** P1, P2 shadow evidence, P4/P5 audit fields, P2b revised gate semantics
**Does not depend on:** P3 external-reference tooling or P6 OBI-Warp shadow

## Purpose

Reduce meaningless RAW/XIC and audit-evidence work while preserving production
result equivalence.

The current evidence chain is scientifically useful but operationally too wide:
expensive evidence is generated for families that are later excluded from the
primary matrix or used only for audit/review. This made the 85RAW P2b follow-up
validation operationally blocked even though the 8RAW targeted plots and P2b
logic point in the right direction.

This spec turns the performance finding into a controlled optimization sequence.
The implementation must preserve production matrix semantics first, then make
audit expansion explicit and opt-in.

## Observed Trigger

The 2026-05-25 85RAW follow-up run produced:

- targeted extraction: passed on 85 RAW
- discovery index: 85 samples, 30,289 discovery candidates
- 85RAW alignment with full evidence: stopped because wall-clock exceeded the
  practical validation budget
- no completed 85RAW P2b GO/NO-GO decision from this run

The 8RAW timing probe supplied during review reported:

| Stage | Wall-clock | Share | XIC calls |
|---|---:|---:|---:|
| `alignment.owner_backfill` | 193.72 s | 80.4% | 15,372 |
| `alignment.build_owners` | 32.27 s | 13.4% | 3,343 |
| `alignment.write_outputs` | 11.32 s | 4.7% | 0 |
| all other stages | 3.91 s | 1.6% | 0 |

The same probe's owner-backfill economics reported that only 733 of 2,756
backfill request targets went to families that entered the primary matrix.
The remaining request targets belonged to `provisional_discovery` or
`audit_family` rows. This is a predicate-pushdown failure: cheap exclusion
information is available earlier than the expensive RAW/XIC backfill, but the
pipeline currently applies the exclusion after most evidence has already been
collected.

The first P7 implementation improved request count on 8RAW, but a follow-up
single-worker 8RAW profile showed that the remaining wall-clock was dominated
by audit computation leaking into the validation path:

| Hot path | Calls | Cumulative time |
|---|---:|---:|
| `build_peak_region_audit_summary` | 16,480 | 1028.0 s |
| `_backfill_feature_sample_trace` | 14,140 | 950.1 s |
| `compute_asls_residual_mad` / `asls_baseline` | 152,119 | 883.4 s |
| RAW `extract_xic_many` | 290 | 94.7 s |

This changes the P7 stabilization target: feature-level predicate pushdown is
necessary but not sufficient. P7 must also separate output artifacts from
execution cost, so `output-level=validation` cannot silently trigger region
audit, integration audit, AsLS, or boundary-scoring work.

## Current Code State

The current alignment path in `xic_extractor/alignment/pipeline.py` is:

```text
read discovery index
  -> read candidates
  -> build sample-local owners
  -> cluster owners
  -> optional identity-coherence diagnostic
  -> optional pre-backfill consolidation
  -> owner_backfill
  -> build owner alignment matrix
  -> claim registry
  -> primary consolidation
  -> recenter
  -> write outputs
```

`OwnerAlignedFeature` currently has fields such as `review_only`, `evidence`,
`owners`, and `confirm_local_owners_with_backfill`. It does **not** have
`identity_decision` or `include_in_primary_matrix`.

Those decisions are computed later from the full matrix by:

- `xic_extractor/alignment/matrix_identity.py`
- `xic_extractor/alignment/production_decisions.py`
- TSV/XLSX writers that consume those decisions

Therefore the optimization must not assume that final matrix identity decisions
already exist before backfill. It needs a narrow, explicitly verified
pre-backfill eligibility model that uses only facts available before RAW/XIC
backfill.

## Result-Equivalence Contract

This spec uses two separate equivalence levels:

1. **Production-equivalent mode**
   - `alignment_matrix.tsv` values that are included in the primary matrix
     must be identical to the legacy full-evidence run.
   - `alignment_results.xlsx` `Matrix` sheet must be identical after normal
     workbook metadata normalization.
   - `Review` and `Audit` workbook sheets are review surfaces, not production
     analytical values. In `production-equivalent` mode they may omit evidence
     that was intentionally skipped only if the skipped evidence appears in the
     required sidecar ledger described below.
   - `Metadata` must record the backfill scope and whether the workbook is
     `full-audit`, `production-equivalent`, or `diagnostic_only`.
   - strict targeted ISTD benchmark decisions must not introduce new active
     failures.
   - non-primary review/audit rows may be omitted from expensive evidence
     collection only if the output carries row-level machine-readable skipped
     evidence.

2. **Full-audit-equivalent mode**
   - default legacy behavior remains available.
   - all review/audit rows and integration audit fields that were previously
     emitted must remain available when the user explicitly requests full audit
     scope.
   - this mode may stay slow; it exists for focused investigation, not routine
     85RAW gate execution.

No optimization may silently change a production value and call the result a
performance improvement.

## Execution Surface Contract

`output-level` defines only the artifact surface: which workbook, TSV, HTML, or
sidecar files are requested. It must not directly decide whether heavy evidence
algorithms run.

Heavy evidence includes:

- region audit construction
- boundary-scoring audit over candidate regions
- CWT audit proposal expansion
- cell integration audit construction
- AsLS residual or AsLS shadow baseline computation

P7 introduces an explicit audit-execution mode, here called
`audit_evidence_mode`, separate from `output-level`:

| Mode | Meaning |
|---|---|
| `none` | Do not compute heavy audit evidence. Audit columns may be blank or omitted according to the writer schema. |
| `full` | Legacy full-audit behavior for every eligible row. This is required for rollback and focused manual review. |
| `selected` | Compute heavy audit evidence only for an explicit family allowlist, used by selected-family diagnostics. |

Implementation details may use `auto` internally or at the CLI, but resolved
metadata must record one of `none`, `full`, or `selected`.

Default resolution:

- `full-audit` scope preserves legacy behavior unless the user explicitly asks
  for a thinner mode.
- `production-equivalent` validation resolves to `audit_evidence_mode=none`
  unless the user explicitly opts into audit evidence.
- `selected-families` resolves to `audit_evidence_mode=selected` only when
  audit evidence is explicitly requested; otherwise it remains `none`.

Acceptance:

- a validation run with `backfill_scope=production-equivalent` and no explicit
  audit opt-in must not call region audit, integration audit, CWT audit, AsLS, or
  boundary-scoring audit code paths.
- metadata must record `audit_evidence_mode`, `heavy_audit_enabled`, and the
  resolved reason, for example `production_equivalent_default_no_audit`.
- `alignment_cells.tsv` can still be emitted in validation mode, but in
  `audit_evidence_mode=none` its `region_*` columns are empty review fields, not
  a promise that region audit was computed.
- `alignment_cell_integration_audit.tsv` and AsLS shadow columns require an
  explicit audit opt-in. Their writers must not force recomputation at write
  time.

### Skipped-Evidence Ledger

Any optimized run that skips expensive evidence must write a sidecar ledger,
preferably:

```text
skipped_evidence_ledger.tsv
```

Minimum columns:

- `feature_family_id`
- `sample_stem`
- `family_center_mz`
- `family_center_rt`
- `rt_window_start`
- `rt_window_end`
- `pre_backfill_category`
- `skipped_stage`
- `skip_reason`
- `backfill_scope`
- `predicate_version`
- `raw_xic_requests_skipped`
- `would_emit_in_full_audit`
- `full_audit_available`
- `source_artifact`

Aggregate skipped-evidence counters are useful but insufficient by themselves.
Reviewers must be able to trace which family/sample was skipped and why.

## Non-Negotiable Constraints

- RAW remains first-class input. Do not require `.mzML` conversion.
- Do not use `ms1-index` or any approximate backend to satisfy the equivalence
  contract. Approximate modes stay diagnostic-only.
- Do not make `preconsolidate_owner_families=True` the default in this spec.
  It is an algorithmic change, not a pure cost-control change.
- Do not change AsLS promotion semantics. This spec only controls when and
  where evidence is computed.
- Do not implement Cleanup C-specs as part of this work.

## Optimization Order

### P7a — Measurement And Guardrails First

Add or extend diagnostics so every future optimization can show both cost and
equivalence:

- owner-backfill request economics by family class
- per-stage `TimingRecorder` summary with XIC call counts
- production-row parity comparison between full-audit and optimized runs
- targeted ISTD benchmark regression check

Acceptance:

- 8RAW full-audit baseline produces timing/economics artifacts.
- optimized runs can be compared against the same full-audit baseline without
  hand-editing paths.
- the report distinguishes `production_family`, `provisional_discovery`, and
  `audit_family` request targets.

### P7b — Destination-Gated Audit Evidence

Audit-only evidence must be computed only when a destination asks for it.

Required gates:

- `output-level` alone is not an audit destination. It may request
  `alignment_cells.tsv` as a review surface, but that does not authorize heavy
  audit computation.
- Heavy audit computation requires `audit_evidence_mode` to resolve to `full` or
  `selected`.
- When `audit_evidence_mode=none`, alignment-cell region/integration audit
  builders must not run even if `alignment_cells.tsv` is emitted.
- `baseline_audit_method=""` means AsLS shadow columns are not computed.
- P4 residual MAD provenance is computed only when heavy audit evidence is
  enabled for the current row.
- P5 CWT audit markers are emitted only by audit writers; production and
  validation scoring must not recompute audit marker state.

Acceptance:

- focused unit tests prove that `audit_evidence_mode=none` prevents region
  audit, integration audit, CWT audit, AsLS, and boundary-scoring builders from
  running.
- default production output is unchanged.
- enabling explicit audit evidence still emits the same full-audit schema as
  before.

### P7c — Pre-Backfill Eligibility Classifier

Introduce a small pre-backfill classifier that uses only `OwnerAlignedFeature`
state available before owner backfill.

The classifier must not import workbook writers, TSV writers, RAW readers, or
post-backfill production-decision builders. It should live near alignment
domain logic, for example:

```text
xic_extractor/alignment/backfill_scope.py
```

Suggested model:

```text
BackfillScope:
  full_audit
  production_equivalent
  selected_families

PreBackfillEligibility:
  feature_family_id
  category
  should_backfill
  reason
```

Initial eligibility rules:

- `review_only=True` never needs production-equivalent backfill.
- `len(feature.owners) < 2` is **not** sufficient for a safe skip. Single-
  detected families can still participate in post-backfill duplicate claims and
  primary consolidation. If a family can affect claim registry,
  `primary_consolidation.py`, or accepted primary cell values, it remains
  backfill-eligible.
- A single-detected family may be skipped only when a pre-backfill
  consolidation-risk predictor proves it has no possible compatible
  duplicate-claim or near-primary competitor under the same identity and RT/mz
  tolerances. If the predictor is absent or uncertain, keep the family
  backfill-eligible.
- multi-detected, non-review-only families remain backfill-eligible.
- `confirm_local_owners_with_backfill=True` features remain eligible whenever
  the family is otherwise production-equivalent eligible, because confirmation
  can supersede a weak local owner.

Acceptance:

- tests prove skipped classes cannot become primary rows under the current
  matrix identity contract.
- tests prove production-eligible families still generate the same backfill
  requests as the legacy path.
- tests cover the existing duplicate-claim consolidation shape where multiple
  single-detected families are consolidated into one primary row. The optimized
  classifier must not skip those families or change the final primary matrix.
- any future change that allows rescues, duplicate claims, or consolidation to
  promote a skipped class into production must fail a P7 guardrail test until
  this classifier is updated.

### P7d — Scope-Aware Owner Backfill

Thread `BackfillScope` through:

- `scripts/run_alignment.py`
- `xic_extractor/alignment/pipeline.py`
- `xic_extractor/alignment/process_backend.py`
- `xic_extractor/alignment/owner_backfill.py`

CLI proposal:

```powershell
python -m scripts.run_alignment `
  --backfill-scope production-equivalent
```

Selected-family diagnostic mode requires an explicit immutable allowlist:

```powershell
python -m scripts.run_alignment `
  --backfill-scope selected-families `
  --backfill-family-list-tsv path\to\selected_families.tsv `
  --backfill-family-id-column feature_family_id
```

The implementation may also support repeated `--backfill-family-id FAM001`
arguments, but the TSV allowlist is the required public surface for reproducible
diagnostics. The parsed allowlist must be passed through single-process and
process-backend paths as the same immutable family-id set.

Process workers must receive a request-level plan, not the entire feature set
for every sample. This is still predicate pushdown, not P8 request fusion:

- compute the sample-specific feature subset from the same
  `backfill_request_sample_stems()` predicate used by the single-process path
- each `OwnerBackfillSampleJob` carries only features that can request that
  sample
- each job records `request_plan_id`, `backfill_scope`, resolved
  `audit_evidence_mode`, and `feature_payload_count`
- no mz/RT request is merged, cached, approximated, or otherwise transformed in
  P7

This reduces serialization and per-sample loop overhead while preserving the
exact legacy XIC request semantics for the selected feature/sample pairs.

Allowed values:

- `full-audit` — legacy behavior and full review/audit surface
- `production-equivalent` — only backfill families that can affect primary
  matrix values
- `selected-families` — only backfill a supplied family allowlist, used by
  focused diagnostics such as P2b selected ISTD review; this mode is
  `diagnostic_only` and must not be used to claim matrix or workbook parity

`selected-families` outputs must include mode metadata, the allowlist path or
inline ids, and an incomplete-scope warning. If the command writes normal matrix
or workbook artifacts for operator convenience, those artifacts are explicitly
diagnostic surfaces and must not be compared as production-equivalent outputs.

Default rollout:

1. keep CLI default at `full-audit` until 8RAW parity is proven
2. use `production-equivalent` explicitly for 85RAW P2b validation commands
3. after accepted parity evidence, consider making production output level use
   `production-equivalent` by default while validation/debug can still request
   `full-audit`

Acceptance:

- `full-audit` output remains byte-identical to the current legacy output.
- `production-equivalent` output has identical primary matrix and workbook
  analytical values.
- optimized output includes skipped-evidence counters so the user can see how
  much audit work was intentionally not performed.
- optimized output includes the row-level skipped-evidence ledger described in
  this spec.
- process-worker tests prove each sample job receives only the feature subset
  that can request that sample.
- audit-mode tests prove unauthorized rows do not call heavy audit builders.

### P7e — Focused AsLS / P2b Evidence

Do not require full alignment-cell AsLS shadow to answer a selected ISTD P2b
question.

Add a focused diagnostic path that computes linear-edge and AsLS area evidence
only for selected feature families and samples needed by the P2b gate.

Possible interfaces:

```powershell
python -m tools.diagnostics.p2_selected_asls_shadow_gate `
  --alignment-dir output\phase1_p7_evidence_chain_cost_control\alignment\region_first_safe_merge_85raw `
  --targeted-istd-benchmark-summary-tsv output\phase1_p7_evidence_chain_cost_control\diagnostics\targeted_istd_benchmark_85raw\targeted_istd_benchmark_summary.tsv `
  --selected-role ISTD `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\phase1_p7_evidence_chain_cost_control\diagnostics\p2_selected_asls_shadow_gate_85raw
```

Acceptance:

- selected-family AsLS results match the full `alignment_cell_integration_audit`
  AsLS columns on the 8RAW baseline for the same rows.
- P2b can run from selected-family evidence without computing AsLS for every
  non-selected alignment cell.
- full-audit AsLS remains available for manual review.

### P7f — 8RAW Equivalence Gate

Before any 85RAW production-candidate claim, run 8RAW A/B validation:

1. legacy `full-audit` alignment
2. optimized `production-equivalent` alignment
3. strict targeted ISTD benchmark on both
4. workbook comparison
5. owner-backfill request economics comparison

Required correctness pass conditions:

- no changed primary matrix values
- no changed workbook `Matrix` sheet values after metadata normalization
- no new strict ISTD active failures
- no changed primary `identity_decision` for families included in the matrix

Required operations pass conditions:

- at least one resource or timing metric improves in the optimized run, such as
  skipped RAW/XIC requests, reduced request targets, fewer `extract_xic` calls,
  fewer raw chromatogram calls, shorter owner-backfill wall-clock, or shorter
  whole-alignment wall-clock
- timing JSON and owner-backfill economics artifacts exist for both A/B runs
- the skipped-evidence ledger explains every skipped family/sample request
- the cost summary separates machine-readable `correctness_status` from
  `operations_status`. `operations_status=PASS` must never be interpreted as a
  full P7 gate pass unless `correctness_status=PASS`.

The 50% request-reduction, 2x owner-backfill speedup, and 35%
whole-alignment speedup numbers are reporting targets, not hard gates. Under a
result-equivalence contract, any observed resource reduction is a positive P7
operations result. If correctness passes but no resource or timing metric
improves, the outcome is `inconclusive` with `outcome_detail=perf_stall`, and
P7g must not run without an explicit human override note.
If operations pass but correctness fails, the outcome is `diagnostic_only` with a
correctness blocker.

### P7g — 85RAW Re-Entry Gate

Only after P7f passes, rerun 85RAW P2b validation using:

- `--backfill-scope production-equivalent`
- `audit_evidence_mode=none` for the main production-equivalent run
- selected-family AsLS diagnostic for P2b ISTDs
- `--performance-profile validation-fast`, equivalent to
  `--raw-workers 8 --raw-xic-batch-size 64` unless explicit raw flags override
  the profile
- mandatory `--timing-output`
- mandatory `--timing-live-output`
- profiling sidecar for at least one scoped preflight run before launching any
  full 85RAW attempt

85RAW execution budget:

- set an overall wall-clock budget in the validation note before launch
- set an `alignment.owner_backfill` stage budget before launch
- on timeout, stop the run and preserve partial timing, owner-backfill
  economics, skipped-evidence ledger, stdout/stderr, and completed-sample
  counts when available
- timeout status is `inconclusive` with `outcome_detail=timeout`; it is not a
  correctness NO-GO and cannot be upgraded to `production_candidate`

85RAW acceptance can then state one of:

- `production_candidate` — 85RAW completed and P2b blockers pass
- `diagnostic_only` — 85RAW completed and produced a correctness blocker
- `inconclusive` — environment or data access prevented the optimized run

The decision note must include `outcome_status` and `outcome_detail` as separate
fields. Legacy labels such as `inconclusive_timeout` and `inconclusive_perf` may
be kept as human-readable aliases, but they are not separate top-level gate
states.

The current pre-P7 85RAW state is `inconclusive` because validation cost
blocked completion. It is not a scientific NO-GO.

## Validation Commands

The implementation plan must provide exact PowerShell commands that satisfy this
command contract. The final validation note must include the executed command
lines and artifact paths for:

- 8RAW full-audit command with `--backfill-scope full-audit`,
  `--timing-output`, fixed output directory, fixed resolver/config inputs, and
  fixed raw worker/batch settings
- 8RAW optimized command with `--backfill-scope production-equivalent`,
  `--timing-output`, the same resolver/config inputs, and the same raw
  worker/batch settings
- 8RAW workbook comparison command
- strict targeted ISTD benchmark commands
- owner-backfill economics commands
- skipped-evidence ledger summary command
- 85RAW optimized command with `--performance-profile validation-fast`,
  `--timing-output`, `--timing-live-output`, and explicit output directory
- selected-family AsLS diagnostic command using the same selected-family
  allowlist contract

All paths must stay under a task-specific output root such as:

```text
output/phase1_p7_evidence_chain_cost_control/
```

Required artifact tree:

```text
output/phase1_p7_evidence_chain_cost_control/
  alignment/8raw_full_audit/
  alignment/8raw_production_equivalent/
  alignment/85raw_production_equivalent/
  compare/8raw_matrix_parity.tsv
  compare/8raw_workbook_matrix_compare.txt
  diagnostics/owner_backfill_economics_8raw_full_audit.json
  diagnostics/owner_backfill_economics_8raw_production_equivalent.json
  diagnostics/skipped_evidence_ledger_8raw.tsv
  diagnostics/skipped_evidence_summary_8raw.json
  diagnostics/p7_cost_summary_8raw/
  diagnostics/p2_selected_asls_shadow_gate_85raw/
  profiling/8raw_single_worker_or_scoped_85raw/
  notes/p7_validation_decision.md
```

The exact implementation may add files, but these names are the minimum human
review surface.

## Rollback

Production rollback is simple: run `--backfill-scope full-audit`.

Validation fallback is narrower: because full-audit 85RAW is already known to be
operationally expensive, do not use rollback as a reason to launch another full
85RAW full-audit run. Instead, prove fallback availability with 8RAW full-audit
parity plus a selected-family full-audit smoke test. If 85RAW optimized fails,
record the blocker and return to selected-family/full-audit smoke evidence.

No production result should depend on the optimized path until the 8RAW
equivalence gate and focused P2b selected-family audit have passed.

## Cleanup Hook

Phase 2 cleanup may remove temporary compatibility flags only after this spec
has a validation note proving:

- `production-equivalent` is accepted for production output
- full-audit remains available for manual investigations
- skipped-evidence ledgers are sufficient for reviewers to understand why a
  non-primary family did not receive expensive evidence

Do not fold this into Cleanup C-specs before the P7 validation note exists.

## Spec Review Result

Reviewed on 2026-05-25 against the current code shape, CodeGraph context, the
modernization overview, P2b/P4/P5 specs, and the 85RAW timeout symptom.

Findings patched into this spec:

- **Incorrect shortcut avoided:** the initial optimization idea assumed
  `OwnerAlignedFeature` already carried `identity_decision` and
  `include_in_primary_matrix`. Current code computes those decisions only after
  matrix construction, so the spec now requires a separate pre-backfill
  eligibility classifier.
- **Equivalence scope clarified:** the spec now separates
  `production-equivalent` from `full-audit-equivalent` so audit surface changes
  cannot be hidden under a vague "same results" claim.
- **AsLS cost isolated:** full alignment-cell AsLS shadow is no longer a
  prerequisite for P2b. A selected-family diagnostic path is required, and the
  review replaced loose ellipsis command-path examples with concrete P7 output
  roots.
- **Algorithmic change excluded:** `preconsolidate_owner_families=True` stays
  out of scope because it can change identity consolidation semantics.
- **85RAW status corrected:** the current state is recorded as operationally
  inconclusive, not a P2b scientific NO-GO.
- **Validation contract tightened:** the spec now requires timeout budgets,
  fixed profile/worker/batch semantics, A/B timing artifacts, an operations gate,
  and a row-level skipped-evidence ledger before 85RAW re-entry.
- **Unsafe owner-count shortcut removed:** single-detected families are no
  longer skipped merely because they have one local owner; any possible duplicate
  claim or primary-consolidation participant remains backfill-eligible.
- **Diagnostic scope isolated:** `selected-families` is explicitly
  `diagnostic_only` and requires a reproducible allowlist.
- **P7 stabilization review applied:** `output-level` is now artifact-only;
  heavy audit execution is controlled by resolved `audit_evidence_mode`, and
  production-equivalent validation defaults to no heavy audit.
- **Request-plan pushdown added:** process workers must receive only the
  per-sample feature subset needed by the backfill predicate. Request fusion,
  caching, vectorization, and numeric hot-loop optimization remain P8.
- **Gate wording normalized:** P7 cost summaries must separate
  `correctness_status` from `operations_status`; timeout and perf stalls are
  `outcome_detail` values under top-level `inconclusive`.

No unresolved blocker remains for redrafting the implementation plan from this
spec.
