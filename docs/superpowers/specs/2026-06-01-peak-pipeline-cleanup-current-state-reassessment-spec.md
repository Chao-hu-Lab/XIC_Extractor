# Peak Pipeline Cleanup Current-State Reassessment Spec

**Date:** 2026-06-01
**Status:** Draft v0.1 - current-state reassessment before next cleanup goal
**Readiness label:** `diagnostic_only`
**Current control map:** [Cleanup current truth map](2026-06-04-cleanup-current-truth-map.md)
**Current repo sources:** [Handoff productization C0 source of truth](../notes/2026-05-27-handoff-productization-c0-source-of-truth.md), `docs/superpowers/notes/2026-05-28-handoff-productization-phase-closeout.md`, [Product priority reset decision spec](2026-05-28-product-priority-reset-decision-spec.md)
**Historical handoff input:** user-provided `lcms_gcms_peak_pipeline_handoff.md`
**Execution contract:** [Peak pipeline cleanup one-goal phase contract](2026-06-01-peak-pipeline-cleanup-one-goal-phase-contract-spec.md)
**Related roadmap:** [Peak pipeline cleanup roadmap overview](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md)
**Related debt roadmap:** [Technical debt and dead-code cleanup roadmap v2](2026-06-01-technical-debt-and-dead-code-cleanup-roadmap-v2-spec.md)
**Related repo-wide inventory:** [Repo semantic-overlap inventory](2026-06-02-repo-semantic-overlap-inventory-spec.md)
**Related slices:** [C2 resolver collapse](2026-05-24-peak-pipeline-cleanup-resolver-collapse-spec.md), [C3 hypothesis model unification](2026-05-24-peak-pipeline-cleanup-hypothesis-model-unification-spec.md), [C4 peak scoring split](2026-05-24-peak-pipeline-cleanup-peak-scoring-split-spec.md), [C6 alignment grouping consolidation](2026-05-24-peak-pipeline-cleanup-alignment-grouping-consolidation-spec.md)

## Verdict

Do not execute the remaining C2/C3/C4/C6 cleanup roadmap literally from the
older specs. The codebase has moved closer to the handoff spine, and the next
cleanup goal should be recalibrated around evidence-chain / hypothesis-decision
work rather than continuing a simple method-deletion campaign.

The settled closeout remains settled:

- `linear_edge` baseline integration is retired from production/config paths;
  keep only rejection contracts and historical diagnostic readers.
- `arbitrated` resolver mode is retired; keep only migration evidence and
  tests that old inputs fail with the retirement message.

The remaining work is different:

- keep `legacy_savgol` as a useful clean-trace resolver or compatibility path;
  do not treat it as dead code;
- keep local-minimum internals as boundary/proposal evidence, even if public
  exposure is later simplified;
- treat `region_first_safe_merge` as a compatibility token for conservative
  local-minimum + WIS/safe-merge behavior; renaming is low priority unless a
  public contract migration needs it;
- stop treating CWT as a deletion candidate. Its current implementation is only
  limited same-apex proposal/evidence support, but the handoff direction says it
  should be tested as a possible evidence source, not a final integrator;
- keep C3 as the main near-term cleanup spine because it moves the code toward
  `TraceGroup` / `PeakHypothesis` / `EvidenceVector` / `IntegrationResult` /
  `AuditTrail`;
- reframe C4 from "split `peak_scoring.py` into a package" to "separate evidence
  extraction, evidence interpretation, and decision policy"; a mechanical split
  before C3 can preserve the wrong architecture;
- reframe C6 from "extract generic grouping primitives" to "inventory and
  characterize alignment grouping semantics"; generic primitives are premature
  until current graph, winner/loser, review, and matrix-delivery semantics are
  pinned.

## Why This Spec Exists

The earlier cleanup roadmap was written when the immediate concern was retiring
old peak detection / integration methods and reducing duplicate code paths. That
was correct for `linear_edge` and `arbitrated`, which now have explicit
retirement closeout.

It is no longer correct to keep asking "which old methods can we delete?" as the
main question. The handoff direction is:

```text
trace / trace-group construction
  -> peak hypothesis enumeration
  -> boundary hypothesis enumeration
  -> multi-evidence scoring
  -> model selection
  -> raw / baseline-corrected integration
  -> audit trail
```

Local minimum, Savitzky-Golay, CWT, WIS, RT prior, MS2/NL evidence, and shape
metrics are inputs to that chain. None of them should silently become the final
authority, and none should be deleted merely because the product direction is
moving toward evidence-based decisions.

## Source-Of-Truth Role

This spec is a current-state interpretation layer for the remaining cleanup
work. The
[one-goal phase contract](2026-06-01-peak-pipeline-cleanup-one-goal-phase-contract-spec.md)
defines how a future single runtime goal may execute these directions. This
spec does not replace the roadmap overview, the debt roadmap, or the handoff
closeout notes. Instead, it tells future cleanup goals how to read the older
C2/C3/C4/C6 slices after `linear_edge` and `arbitrated` were retired and after
the handoff spine partially landed.

Source priority for future agents:

1. repo-local current status / closeout notes;
2. the one-goal phase contract when executing a single runtime goal;
3. this reassessment for remaining C2/CWT/C3/C4/C6 cleanup direction;
4. older C-specs for historical rationale, file lists, and parity constraints;
5. the downloaded handoff memo as design input, not as the current repo source
   of truth.

## Current-State Evidence

This reassessment is anchored to the current branch
`codex/cleanup-retirement-foundation`.

CodeGraph status at reassessment time:

- files: 705
- nodes: 13,844
- edges: 30,877
- index status: up to date

Observed current code state after the Phase 1 C2 cleanup:

- `xic_extractor/settings_schema.py` accepts `legacy_savgol`, `local_minimum`,
  and `region_first_safe_merge`; `arbitrated` is outside `RESOLVER_MODES` and
  has a retirement message.
- `xic_extractor/peak_detection/facade.py` routes `local_minimum` and
  `region_first_safe_merge` through `find_peak_candidates_local_minimum`.
  `arbitrated` raises the retirement message. Unsupported programmatic
  `resolver_mode` values now raise an explicit error instead of falling through
  to `legacy_savgol`.
- `xic_extractor/configuration/models.py` keeps the public
  `ExtractionConfig.resolver_mode` dataclass field at `legacy_savgol` as a
  tested programmatic compatibility default.
- `scripts/run_alignment.py` still maps `region_first_safe_merge` back to
  `local_minimum` for production alignment quantification.
- `scripts/run_discovery.py` still defaults to `local_minimum`.
- `README.md` distinguishes the tracked settings / validation harness default
  `region_first_safe_merge` from the `legacy_savgol` programmatic compatibility
  default.
- `xic_extractor/peak_detection/cwt.py` uses `scipy.signal.find_peaks_cwt` to
  add `centwave_cwt` proposals for audit / proposal support.
- `xic_extractor/peak_scoring.py` still assigns
  `cwt_same_apex_support` a small positive point value and uses that same-apex
  support to relax part of the trace-quality cap. This means CWT is not dead
  code, but it is not yet a serious evidence-chain implementation.
- `xic_extractor/peak_detection/hypotheses.py` already defines
  `IntegrationResult`, `EvidenceVector`, `AuditTrail`, and `PeakHypothesis`,
  but imports and adapts legacy `PeakCandidate`, `PeakCandidateScore`, and
  `PeakDetectionResult`. The handoff spine exists, but the legacy DTOs still
  own many producer/reader paths.
- `xic_extractor/extraction/handoff_spine_runtime.py` and candidate projection
  builders show that runtime projection onto the handoff spine is partial, not
  the universal product contract.
- `config/settings.example.csv` is tracked public example config and should
  describe `baseline_integration_method` as AsLS-only after the baseline
  retirement. Phase 0 fixes this housekeeping item rather than reopening the
  baseline behavior question.
- The local `config/settings.csv` runtime copy may contain the same stale
  wording, but it is ignored/local runtime state. Do not edit it in a PR unless
  the user explicitly asks to update this machine's runtime config.

## Public Surface Drift Inventory

Before the next C2/CWT/C3/C4/C6 goal changes code, it must classify these
surfaces as synchronized, intentionally divergent, or stale:

| Surface | Current drift / risk | Required next action |
|---|---|---|
| `README.md` resolver docs | Phase 1 synchronized user-facing default wording with settings schema and harness defaults. | Keep this wording aligned if future resolver naming changes. |
| `settings_schema.py` / `config/settings.example.csv` | Canonical defaults prefer `region_first_safe_merge`; Phase 0 fixes tracked example baseline wording to AsLS-only. | Keep resolver descriptions aligned with accepted values in C2. |
| Ignored `config/settings.csv` | Machine-local runtime state can drift from tracked templates. | Do not modify in PR by default; mention when local runtime cleanup is optional. |
| GUI resolver combo | GUI rejects or normalizes retired `arbitrated` and still exposes the surviving resolver modes plus local-minimum controls. | Any resolver policy change needs GUI tests for visible choices and panel behavior. |
| CLI defaults/coercion | `run_alignment` accepts `region_first_safe_merge` but coerces production extraction to `local_minimum`; `run_discovery` defaults to `local_minimum`. | Preserve unless a later behavior spec changes the discovery/alignment contract. |
| `ExtractionConfig.resolver_mode` | Programmatic dataclass default remains `legacy_savgol`. | Kept and tested as compatibility default. |
| `peak_detection.facade.find_peak_candidates` | Phase 1 changed unknown programmatic resolver values from silent legacy fallback to explicit `ValueError`. | Keep accepted-mode behavior covered by focused tests. |
| `xic_extractor.signal_processing` | Public compatibility import surface for legacy peak models. | C3 must preserve imports unless a separate breaking-change spec exists. |
| `xic_extractor.peak_scoring` | Public module import path and reason/confidence contract. | C4 redesign must choose module vs package/shim strategy before moving code. |
| TSV/workbook outputs | `peak_candidates.tsv`, boundary TSVs, and alignment TSVs are public/generated contract surfaces. | Cleanup must preserve schemas and values unless a behavior spec says otherwise. |

## Reassessed Cleanup Decisions

### C2 - Resolver Surface And Method Roles

`legacy_savgol` should not be deleted in the next cleanup goal. It is still
useful for normal, cleaner peaks. The issue is not that SG is bad; the issue is
that SG/local-minimum-only selection is insufficient in complex matrix
conditions.

Phase 1 C2 cleanup resolved the public-surface drift items:

1. `legacy_savgol` is preserved as an explicit clean-trace / compatibility path
   and the tested programmatic `ExtractionConfig` default.
2. Local-minimum internals remain boundary/proposal evidence.
3. Public config continues exposing all three accepted values:
   `legacy_savgol`, `local_minimum`, and `region_first_safe_merge`.
4. Unsupported programmatic resolver modes now fail explicitly instead of
   silently using `legacy_savgol`.
5. `region_first_safe_merge` naming is left unchanged; renaming still requires a
   real config migration and tests.

This is a contract cleanup, not a detector deletion phase.

### CWT - Evidence-Chain Integration, Not Retirement

CWT has not been seriously integrated into the evidence chain yet. The current
state is limited same-apex support:

- it can add `centwave_cwt` proposal provenance;
- it can expose legacy presence-like metrics;
- it can contribute `cwt_same_apex_support`;
- it can affect confidence cap logic.

The next CWT question is not "delete CWT?" It is:

```text
Which evidence role should CWT own, and what minimum local evidence proves that
role is useful?
```

Allowed future roles:

- apex proposal source;
- peak-width prior;
- ridge / persistence support;
- shoulder or overlapping-peak proposal evidence;
- shape corroboration.

Disallowed roles without a separate behavior spec:

- final boundary authority;
- final integrator;
- wavelet-smoothed area source;
- single-source peak-existence verdict.

Before any production behavior change, run a bounded CWT assessment:

1. inventory current CWT fields and labels in candidate, boundary, scoring, and
   audit outputs;
2. define one evidence-chain target field set for `EvidenceVector`;
3. run a small 8RAW ablation / comparison only after the result-to-action table
   below is filled for the tested CWT role;
4. classify the result as `promote_to_evidence_source`, `keep_audit_only`, or
   `externalize_or_kill`.

Pre-registered CWT gate template:

| Field | Requirement before running 8RAW |
|---|---|
| Tested role | Exactly one of: apex proposal, width prior, ridge/persistence support, shoulder/coelution proposal support. |
| Comparator | Current supported resolver/scoring behavior with existing CWT handling, plus a controlled ablation or candidate implementation of the tested role. |
| Artifacts | `alignment_matrix.tsv`, `alignment_review.tsv`, `alignment_cells.tsv`, targeted benchmark output when applicable, candidate/boundary audit rows that include CWT labels and proposal sources. |
| Metrics | Pre-register row-level changed decisions, strict benchmark status, confidence/reason changes, CWT-supported candidate count, false-support concerns, and any selected peak/area changes. |
| Promote condition | The tested CWT role provides useful independent evidence without degrading benchmark or selected-output contracts, and the result names the exact `EvidenceVector` fields to promote. |
| Keep audit-only condition | CWT explains or annotates cases but does not improve a decision enough to justify production behavior or scoring-policy change. |
| Externalize/kill condition | CWT evidence is non-actionable, misleading, redundant with existing evidence, or introduces selected-output regressions that cannot be justified by a behavior spec. |
| Inconclusive condition | Changed rows cannot be interpreted without manual EIC review, comparator artifacts are stale, or the tested role was not isolated. |

If this table cannot be filled before the run, do not run RAW validation. Do
only the inventory and keep CWT `diagnostic_only` / audit-only.

2026-06-01 Phase 2 update:

- [P5 CWT evidence honesty spec](2026-05-24-peak-pipeline-cwt-evidence-honesty-spec.md)
  now records the current CWT surface inventory and gate.
- The next tested role is `apex proposal source`.
- Current classification is `inconclusive_pending_named_evidence`.
- No RAW run is justified until a controlled comparator, changed-decision
  schema, and manual EIC review slice exist.

### C3 - Handoff Spine Unification Remains Mainline

C3 is still important, but the first step should be a current-state consumer
inventory, not a restart of the original 2026-05-24 plan.

Required first slice:

- catalog legacy DTO producer, reader, audit, shim, and shared-evidence
  boundary sites against current code;
- explicitly mark which sites already project to `PeakHypothesis` /
  `EvidenceVector`;
- choose one consumer migration with parity evidence;
- preserve public `xic_extractor.signal_processing` compatibility unless a
  separate breaking-change spec exists.

The goal is not to delete `PeakCandidate` immediately. The goal is to make the
handoff spine the surface that future CWT, scoring, and audit work can target.

### C4 - Scoring Split Is Stale As Written

The old C4 "turn `peak_scoring.py` into `xic_extractor/peak_scoring/` package"
is too mechanical and may be technically awkward because Python cannot expose a
same-level `peak_scoring.py` module and `peak_scoring/` package under the same
import name without a migration decision.

More importantly, the handoff direction is no longer "split a big scorer into
smaller arbitrary scoring files." It is:

```text
evidence extraction
  -> evidence normalization / interpretation
  -> decision policy
  -> reason / audit projection
```

Next C4 work should be a redesign spec, not implementation:

1. classify every major `peak_scoring.py` responsibility into evidence
   extraction, evidence interpretation, decision policy, output reason, or
   compatibility adapter;
2. decide whether the public import path remains `xic_extractor.peak_scoring`
   as a module, moves to a package with a shim, or moves to a different
   internal package;
3. preserve score/reason/confidence parity until a behavior spec intentionally
   changes decision policy;
4. do not split on line count alone.

### C6 - Alignment Grouping Needs Characterization Before Primitives

The old C6 primitive set (`group_by_tolerance`, `eject_and_reattach`,
`tie_break_sort`) is too coarse for the current alignment code. The current
alignment pipeline includes graph-like relationships, owner and loser
semantics, review fields, matrix identity, and downstream delivery behavior.

Next C6 work should be inventory-only:

- map grouping-like stages and their owner/output semantics;
- identify which stages are true generic grouping, which are identity/gate
  policy, and which are matrix delivery;
- add characterization / golden parity around the smallest stage that is safe
  to move;
- defer shared primitives until the inventory proves two stages share the same
  semantics.

Do not run C6 as a broad refactor goal until this characterization exists.

## Revised Execution Order

### Now

1. Accept this reassessment as the current cleanup direction.
2. Link this reassessment from the canonical cleanup entrypoints so future
   agents do not execute stale C2/C3/C4/C6 wording literally.
3. Fix tracked stale `baseline_integration_method` wording as housekeeping when
   touching config docs; leave ignored runtime config alone unless explicitly
   asked.
4. Choose exactly one narrow next implementation slice:
   - C2 resolver contract cleanup;
   - CWT evidence-role inventory with a pre-registered gate;
   - C3 current-state inventory plus one parity-backed consumer migration.

### Later

1. Rewrite C4 as an evidence-decision architecture spec after C3 inventory
   exposes the actual spine boundary.
2. Run C6 grouping characterization and golden parity before extracting any
   generic helper.
3. Consider public resolver naming only if it reduces real config/API drift,
   not because the current name is aesthetically imperfect.

### Not In Scope

- Reintroducing `linear_edge`.
- Reintroducing `arbitrated`.
- Deleting `legacy_savgol`.
- Deleting local-minimum internals.
- Promoting CWT to production behavior without a CWT evidence-chain spec and
  validation gate.
- Splitting `peak_scoring.py` only to reduce line count.
- Running a broad C6 refactor without characterization parity.
- Any matrix identity, selected-peak, or area-value behavior change under the
  label "cleanup".

## Acceptance Criteria For The Next Goal

A next cleanup goal can use this spec only if it states:

- that it follows the
  [one-goal phase contract](2026-06-01-peak-pipeline-cleanup-one-goal-phase-contract-spec.md);
- which phase advances `TraceGroup`, `PeakHypothesis`, `EvidenceVector`,
  `IntegrationResult`, model selection, or `AuditTrail`;
- whether each phase is `docs-only`, `contract cleanup`, `move-only`,
  `split-only`, `diagnostic_only`, or behavior-affecting;
- exact public surfaces touched: CLI, config, GUI, TSV/workbook schemas,
  README, `ExtractionConfig`, `signal_processing`, `peak_scoring`, diagnostic
  entry points;
- parity or contract tests for each touched public surface;
- an exit rule for CWT: promote, keep audit-only, externalize, or kill after a
  named missing evidence item is resolved.

## Stop Rules

Stop and write a behavior spec instead of continuing cleanup if a phase:

- changes selected peak, area, confidence, reason text, matrix identity, or
  downstream TSV values;
- needs a new CWT point weight, cap rule, or resolver behavior;
- removes a public resolver/config value rather than rejecting or aliasing it
  through an approved migration contract;
- finds that a supposedly generic C6 grouping helper would need stage-specific
  side effects to preserve behavior.

## Validation Expectations

This reassessment is docs-only. Required smoke checks:

- Markdown path / stale-wording scan for the new spec and linked specs;
- `git diff --check`.

Implementation phases derived from this spec need their own validation:

- C2 contract cleanup: focused config/facade/CLI tests plus lint/typecheck on
  touched modules. Include a README stale-wording scan, example-config
  baseline-method wording check, facade unknown-resolver failure test, and an
  explicit `ExtractionConfig.resolver_mode` default policy test if that default
  is touched.
- CWT assessment: no RAW run unless the ablation result can change the next
  action; if run, use 8RAW validation-minimal plus targeted benchmark artifacts
  and record `run_ok`, `gate_ok`, `production_ready`, and `inconclusive`.
- C3 inventory/migration: focused adapter/projection tests and parity of
  affected candidate/boundary outputs.
- C4 redesign: docs/spec review only until implementation scope is accepted.
- C6 inventory: characterization/golden parity plan before any refactor.

## Open Questions

1. Which C3 consumer is the safest first migration under current code:
   candidate projection, scoring input, recovery, or alignment audit?
2. Should C4 keep `xic_extractor.peak_scoring` as a module shim, or should the
   redesign choose a different internal package name to avoid module/package
   collision?
3. Which C6 stage has the best existing oracle for characterization:
   primary consolidation, owner clustering, matrix identity, or folding?
