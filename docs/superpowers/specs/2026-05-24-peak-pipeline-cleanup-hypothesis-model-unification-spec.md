# C3 — Hypothesis Model Unification Spec

**Date:** 2026-05-24
**Status:** Phase 3 executable closeout v0.5 — current inventory plus first
handoff-spine audit projection locked; full legacy model removal deferred
**Overview:** [Peak pipeline cleanup roadmap overview](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md)
**Current reassessment:** [Peak pipeline cleanup current-state reassessment](2026-06-01-peak-pipeline-cleanup-current-state-reassessment-spec.md)
**One-goal execution contract:** [Peak pipeline cleanup one-goal phase contract](2026-06-01-peak-pipeline-cleanup-one-goal-phase-contract-spec.md)
**Precondition:** current-state reassessment accepted. C2 resolver public-surface
contract is either complete or explicitly classified. Full legacy model removal
is not part of the next one-goal cleanup unless a later plan narrows it to a
separate parity-backed implementation phase.

## Purpose

Move the cleanup program toward the handoff spine without pretending the whole
legacy model can be removed in one pass.

The handoff vision defines one peak data spine:
`PeakHypothesis` + `EvidenceVector` + `IntegrationResult` + `AuditTrail`.
The legacy spine (`PeakCandidate` + `PeakResult` + `PeakDetectionResult`) still
owns many producer, reader, scoring, recovery, and audit paths. The next C3
phase should therefore do two bounded things:

1. build a current-state consumer inventory against the actual codebase;
2. migrate one low-risk consumer or projection surface to the handoff spine with
   parity tests.

This phase introduces no resolver, scoring, area, matrix, or schema behavior
change. Full legacy model removal is a later multi-phase refactor after the
inventory proves the field mapping and public compatibility story.

For the current Step 1 source of truth, see
`../notes/2026-05-27-handoff-productization-c0-source-of-truth.md`.
`peak_candidates.tsv` is a schema-frozen debug/audit projection of the spine,
not the canonical domain model and not the downstream production matrix.

## Current State

Two model layers exist:

### Legacy spine

- `xic_extractor/peak_detection/models.py`:
  - `PeakResult` — selected peak coordinates and area
  - `PeakCandidate` — candidate + selection metadata
  - `PeakCandidatesResult` — wrapper with status/n_points
  - `PeakDetectionResult` — final detection output
  - `PeakCandidateScore` — score breakdown
  - `LocalMinimumRegionQuality` — region quality metadata

### Handoff spine

- `xic_extractor/peak_detection/hypotheses.py`:
  - `PeakHypothesis` — candidate + selected flag + reason
  - `EvidenceVector` — multi-source evidence
  - `IntegrationResult` — integration output
  - `AuditTrail` — audit metadata

The two spines are connected via adapters in `hypotheses.py` that wrap
legacy results. Many producer, scoring, recovery, and alignment consumers still
read legacy types, while candidate and boundary audit projections can already
read `PeakHypothesis`. Adding a new evidence dimension or audit field may still
require touching both layers until the remaining consumers are migrated.

2026-05-27 update: `extraction/peak_candidate_boundaries.py` is the first audit
consumer migrated to project rows from `PeakHypothesis`, with a lower-level
`BoundaryCandidateContext` preserving boundary-enumerator compatibility for
legacy callers. This is still scaffold/dual-write work, not production behavior
readiness. Candidate and boundary TSV projections also expose explicit
`*_from_hypotheses` builders so later migrated consumers can bypass legacy row
projection without changing public TSV schemas.

2026-06-01 Phase 3 execution closeout: the first migration slice is the
candidate/boundary audit projection path:

- `extraction/peak_candidate_audit.py::append_peak_audit_rows` builds one
  audited hypothesis tuple through
  `peak_candidate_table.build_peak_candidate_audit_hypotheses`;
- `append_peak_candidate_rows_from_hypotheses` and
  `append_peak_candidate_boundary_rows_from_hypotheses` consume that same tuple;
- legacy callers may still pass `PeakDetectionResult`, but the TSV projection
  no longer needs separate candidate-table and boundary-table legacy
  conversions;
- this is not `diagnostic_only` because a named audit projection consumer is
  already spine-backed and covered by focused projection tests;
- this does not unlock broad C4 scoring refactors beyond the evidence-decision
  spec work, because producer/scoring/alignment consumers below still depend on
  legacy DTO semantics.

### Shared evidence layer

C3 must also preserve the existing shared evidence semantics:

- `xic_extractor/evidence_semantics.py`
- `CommonEvidence` / `EvidenceSignalSet` consumers
- `xic_extractor/peak_scoring_evidence.py`
- drift / ISTD evidence adapter boundaries such as `drift_evidence.py`

These modules prevent targeted, untargeted, drift, and scoring code from
inventing incompatible evidence meanings. C3 may move adapters, but it must
not duplicate or bypass this evidence layer while unifying peak models.

## Required Change

The executable next-goal C3 scope is inventory plus one parity-backed migration
slice. The older full-unification steps are retained below as future targets,
but they are not executable in the next one-goal cleanup unless a separate
implementation plan narrows them.

### Step 1 — Inventory legacy consumers

Run a grep for every reference to `PeakResult`, `PeakCandidate`,
`PeakCandidatesResult`, `PeakDetectionResult`, `PeakCandidateScore`,
`CommonEvidence`, `EvidenceSignalSet`, and public
`xic_extractor.signal_processing` imports. Catalog each as one of:

- (a) producer site (where the legacy object is constructed)
- (b) reader site (where the legacy object is consumed)
- (c) audit site (where the legacy object is serialized to TSV)
- (d) re-export shim (where the legacy object is exposed under a different
  import path)
- (e) shared evidence boundary (where evidence semantics are translated
  between targeted / untargeted / scoring / drift contexts)

Expected sites (verify at refactor time):

- producers: `local_minimum.py`, `legacy_savgol.py` (kept as a clean-trace /
  compatibility path unless a separate migration contract changes it),
  `cwt.py`, `recovery.py`, `region_safe_merge.py`, `facade.py`
- readers: `peak_scoring.py`, `alignment/ownership.py`,
  `alignment/owner_backfill.py`, `extraction/*`
- audit: `extraction/peak_candidate_table.py`,
  `extraction/peak_candidate_boundaries.py`, `alignment/tsv_writer.py`
- re-export shim: `xic_extractor/signal_processing.py` re-exports
  `LocalMinimumQualityFlag`, `LocalMinimumRegionQuality`, `PeakCandidate`,
  `PeakCandidateScore`, `PeakCandidatesResult`, `PeakDetectionResult`,
  `PeakResult`, `PeakStatus`, `find_peak_and_area`, `find_peak_candidates`
  via its `__all__`. Many callers (e.g.
  `extraction/istd_recovery.py:from xic_extractor.signal_processing import
  PeakCandidate, PeakDetectionResult`) use the shim instead of importing
  from `peak_detection.models` directly. C3 must either update the shim
  with compatibility aliases, or delete the shim and migrate every shim
  consumer under a separate breaking-change decision.
- evidence semantics: `evidence_semantics.py`, `peak_scoring_evidence.py`,
  and drift evidence adapters must be cataloged before moving fields onto
  `EvidenceVector`.

Inventory output must include:

| Field | Requirement |
|---|---|
| Site | File/function or public import surface |
| Category | Producer, reader, audit writer, public shim, compatibility adapter, shared-evidence boundary |
| Current model | Legacy DTO, handoff spine, adapter, or mixed |
| Public surface | Yes/no; name CLI/config/TSV/API/import if public |
| Migration risk | Low, medium, high |
| Required parity oracle | Unit, writer schema, focused TSV parity, or RAW validation |
| First-slice candidate | Yes/no with reason |

### 2026-06-01 Consumer Inventory

| Site | Category | Current model | Public surface | Migration risk | Required parity oracle | First-slice candidate |
|---|---|---|---|---|---|---|
| `peak_detection/local_minimum.py`, `legacy_savgol.py`, `cwt.py`, `recovery.py`, `region_safe_merge.py`, `facade.py` | Producer | Legacy DTO | Indirect through `find_peak_and_area` / `find_peak_candidates` | High | focused selection parity plus RAW validation before production behavior changes | No; changing producers would risk peak selection, scoring, and area semantics. |
| `peak_detection/hypotheses.py::build_peak_hypotheses` | Compatibility adapter | Legacy DTO to handoff spine | No direct CLI/API, but used by audit/runtime projections | Medium | hypothesis unit tests and projection parity | No; this is the bridge, not the consumer being migrated. |
| `extraction/handoff_spine_runtime.py::build_production_peak_hypotheses` | Compatibility adapter / runtime bridge | Mixed | Internal extraction runtime | Medium | handoff spine runtime tests and selected-result parity | No; production selected-result assembly is broader than the audit projection slice. |
| `extraction/peak_candidate_table.py::*_from_hypotheses` | Audit writer | Handoff spine | `peak_candidates.tsv` schema | Low | writer schema/value tests | Yes; already spine-backed and suitable for focused parity. |
| `extraction/peak_candidate_boundaries.py::*_from_hypotheses` | Audit writer | Handoff spine | `peak_candidate_boundaries.tsv` schema | Low | writer schema/value tests | Yes; already spine-backed and suitable for focused parity. |
| `extraction/peak_candidate_audit.py::append_peak_audit_rows` | Audit orchestrator | Mixed input, spine projection | Candidate and boundary TSV emission path | Low | audit appender tests proving one hypothesis build and both TSV row families populated | Chosen slice; reduces duplicate legacy projection by sharing one `PeakHypothesis` tuple. |
| `xic_extractor/signal_processing.py` | Public shim | Legacy DTO re-export | Public import surface and `find_peak_*` functions | High | import smoke plus return-shape tests | No; deletion or alias changes require a breaking-change spec. |
| `evidence_semantics.py`, `peak_scoring_evidence.py`, drift evidence adapters | Shared-evidence boundary | Shared evidence models plus legacy candidate adapters | Internal evidence contract used across targeted/discovery/scoring contexts | Medium | evidence semantics tests | No; preserve as the semantic bridge until C4 evidence-decision work narrows ownership. |
| `peak_scoring.py` | Reader / scoring decision | Legacy DTO plus shared evidence | Production confidence/reason behavior | High | byte-stable confidence/reason tests and RAW validation before behavior changes | No; C4 must first separate evidence facts from decision policy. |
| `extractor.py`, `extraction/result_assembly.py` | Runtime result assembly | Mixed legacy DTO plus `PeakHypothesis` / `IntegrationResult` selected-result helpers | Public `TargetResult` shape and extraction facade behavior | High | target extraction and result assembly tests; RAW if selected peak/area can change | No; this is runtime behavior, not an audit-only projection. |
| `extraction/anchors.py`, `diagnostics.py`, `istd_recovery.py`, `ms2_selection.py`, `target_extraction.py`, `rt_windows.py`, `scoring_factory.py` | Extraction readers / adapters | Legacy DTO | Internal extraction behavior, diagnostics, RT windows, and scoring-context construction | Medium to high | focused extraction, scoring-factory, RT-window, and recovery tests; RAW if selected peaks can change | No; not smaller than audit projection and may change recovery/scoring coupling. |
| `output/csv_writers.py`, `output/messages.py` | Output writer / message formatter | Legacy DTO protocol for `peak_result` | CSV/workbook-facing output and user-visible diagnostic messages | High | writer/message tests plus schema parity | No; this is public output behavior. |
| `discovery/ms1_backfill.py` | Discovery reader / backfill adapter | Legacy `PeakResult` from public `find_peak_and_area` | Discovery backfill output | Medium | discovery backfill tests and targeted parity if backfill values can change | No; outside audit projection and depends on public finder return shape. |
| `peak_detection/boundaries.py`, `selection.py`, `region_audit.py` | Peak-detection support / audit helpers | Legacy DTO, with boundary context adapter in `boundaries.py` | Internal selection and region audit behavior | Medium to high | boundary/region/selection characterization tests | No; support helpers sit below producer behavior and can change selected intervals. |
| `alignment/matrix_handoff.py` | Compatibility adapter | Legacy `PeakResult` to `IntegrationResult` | Alignment matrix handoff contract | Medium | matrix handoff and alignment matrix tests | No; useful bridge, but downstream-facing matrix behavior is too broad for the first slice. |
| `alignment/ownership.py`, `alignment/owner_backfill.py`, `alignment/tsv_writer.py`, alignment matrix/cell writers | Reader / output writer | Mixed legacy and `IntegrationResult` | Downstream TSV/workbook contract | High | alignment matrix/cell parity plus validation-minimal run | No; public downstream schema risk is too high for first C3 slice. |
| `alignment/identity_gates.py` | Shared evidence decision reader | `CommonEvidence` sequences | Alignment identity gate semantics | High | identity-gate tests plus alignment decision parity | No; this belongs to evidence-decision/identity policy, not DTO projection cleanup. |
| `tests/*` importing `xic_extractor.signal_processing` legacy names | Public compatibility coverage | Legacy DTO through shim | Test oracle for public import compatibility | Low | unit/import smoke | No; keep as coverage, not a migration target. |

### Step 2 — Select the first migration slice

Chosen Phase 3 slice: candidate/boundary audit projection. The current code
already exposes `*_from_hypotheses` builders and `append_peak_audit_rows` uses
one shared hypothesis tuple for both candidate and boundary row families. The
surface is pinned by writer and audit-appender tests without changing public TSV
schemas.

Alternative first slices are allowed only if the inventory proves they have a
smaller public-contract surface.

Disallowed first slices:

- replacing local-minimum producers;
- changing scoring input contracts;
- deleting `PeakCandidate` / `PeakDetectionResult`;
- changing `xic_extractor.signal_processing` public imports;
- changing alignment matrix output.

### Step 3 — Migrate one consumer or defer with a named spine blocker

Phase 3 migration decision:

- migrated/currently locked consumer:
  `extraction/peak_candidate_audit.py::append_peak_audit_rows`;
- reduced dependency: candidate-table and boundary-table audit emission no
  longer perform separate legacy-to-row projection work when using the combined
  audit appender;
- compatibility: legacy callers still pass `PeakDetectionResult`, and
  `xic_extractor.signal_processing` legacy imports remain unchanged;
- parity oracle: `tests/test_peak_candidate_audit.py`,
  `tests/test_peak_candidate_table.py`, and
  `tests/test_peak_candidate_boundaries.py`.

For future migration slices:

- preserve emitted column names and values;
- name the current consumer or projection path being migrated and the legacy DTO
  dependency it reduces;
- add focused tests for the projection or adapter;
- keep legacy callers working through compatibility wrappers or adapters.

If a future slice cannot be migrated:

- name the missing `PeakHypothesis`, `EvidenceVector`, `IntegrationResult`, or
  `AuditTrail` field;
- document whether the missing field is a real spine gap or a legacy projection
  artifact;
- close the phase as `diagnostic_only` only;
- do not unlock C4 implementation work from a deferred C3 closeout;
- stop before broadening to another high-risk consumer.

### Step 4 — Preserve public compatibility

`xic_extractor.signal_processing` remains public. C3 must preserve legacy import
names and return shapes unless a separate breaking-change spec exists.

## Later Full-Unification Targets

The following steps describe the long-term direction after inventory and one or
more parity-backed migration slices. They are not executable as a single next
phase.

### Later Step A — Replace producers with hypothesis spine

Every producer site that currently returns `PeakCandidate` /
`PeakCandidatesResult` returns the hypothesis spine instead:

- `find_peak_candidates_local_minimum` → returns
  `tuple[PeakHypothesis, ...]`
- `find_peak_and_area` → returns a `PeakHypothesis` with `selected = True`
- `region_safe_merge` → produces and promotes `PeakHypothesis` directly

The fields previously on `PeakCandidate` (selection_apex_rt,
selection_apex_intensity, region_scan_count, quality_flags, prominence,
proposal_sources, source_apex_rank, region_*) move into `PeakHypothesis` or
its embedded `AuditTrail`. Field-by-field mapping is recorded in this spec
at implementation time.

### Later Step B — Replace readers with hypothesis spine

Every reader site reads `PeakHypothesis` instead of `PeakCandidate`. Field
name changes are mechanical; semantic differences (if any are found during
mapping) are recorded as discrepancies and resolved before landing.

### Later Step C — Replace audit serialization

The TSV writers serialize from the hypothesis spine. Column names in the
emitted TSVs must remain identical to current production (this is a hard
constraint from the validation contract).

If a TSV column has no direct equivalent on the hypothesis spine, add the
corresponding field to `AuditTrail` rather than reviving a legacy type.

### Later Step D — Resolve the signal_processing shim

Two options:

- (a) **Keep the shim with compatibility aliases**: preserve old import names
  (`PeakCandidate`, `PeakDetectionResult`, etc.) and return shapes until a
  separate breaking-change spec removes them. The implementation may back
  those names with wrappers/adapters around the hypothesis spine, but import
  statements and public `find_peak_and_area` / `find_peak_candidates` return
  contracts must keep working.
- (b) **Delete the shim**: migrate every caller of
  `xic_extractor.signal_processing` to import directly from
  `xic_extractor.peak_detection.hypotheses` (or wherever the type lives).
  This is a breaking public-surface change and is not allowed in C3 unless a
  separate approval note exists.

Decision: lean toward (a). The shim has historically been the "external
import surface" and callers depend on its stability. Compatibility aliases
keep C3 a refactor instead of a public API break. Deletion would be a wider
change that competes for review attention with the model unification itself.

Document the decision in `xic_extractor/signal_processing.py` docstring at
implementation time.

### Later Step E — Retire legacy concrete storage

After all producer, reader, and audit sites consume the hypothesis spine,
and after Later Step D resolves the shim, remove legacy concrete storage where it
is internal-only. If a legacy name is public through
`xic_extractor.signal_processing`, keep a compatibility wrapper or alias until
a separate breaking-change spec retires it. The file may still contain shared
support types (`LocalMinimumRegionQuality`, `LocalMinimumQualityFlag`,
`PeakStatus`); keep those.

## Validation Contract

For the next one-goal C3 phase:

1. Inventory docs must be internally consistent and name the first migration
   slice.
2. If one consumer is migrated, it must be a named current consumer or
   projection path and it must reduce at least one legacy DTO dependency.
3. If no consumer is migrated, the phase is `diagnostic_only`; the note must
   name the missing spine field and explicitly say C4 implementation is not
   unlocked.
4. Public import smoke tests for `xic_extractor.signal_processing` legacy names
   must pass if the migration touches peak model imports.
5. Candidate/boundary TSV schemas and values must be unchanged for the touched
   projection surface.
6. No RAW validation is required for docs-only inventory or synthetic writer
   parity. If the migration can affect real generated rows beyond focused
   tests, stop and add a RAW validation preflight before implementation.

Suggested focused tests:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_target_extraction.py tests/test_peak_candidate_audit.py tests/test_peak_candidate_table.py tests/test_peak_candidate_boundaries.py tests/test_signal_processing.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

If the migration touches shim, hypothesis, runtime spine, or shared-evidence
surfaces, include the relevant focused tests from:
`tests/test_peak_detection_module_boundaries.py`, `tests/test_peak_hypotheses.py`,
`tests/test_handoff_spine_runtime.py`, and `tests/test_evidence_semantics.py`.

## Implementation Strategy

Current one-goal phase split:

| Slice | Scope | Validation |
|----|-------|------------|
| 3-current-inventory | Catalog current legacy/spine consumers and choose first migration slice. | docs smoke + grep evidence |
| 3-first-migration | Migrate one low-risk consumer or defer with a named spine field blocker. | focused projection / adapter tests |
| 3-closeout | Record remaining full-unification backlog and update C4/CWT dependencies. | docs smoke |

Long-term full-unification split, after this phase:

| PR | Scope | Validation |
|----|-------|------------|
| 3a | Add new fields to `PeakHypothesis` / `AuditTrail` so they can express everything legacy fields express. Compile only; no behavior change. | unit tests for new fields |
| 3b | Switch producers to emit both legacy and hypothesis spine (dual write). | parity TSV check |
| 3c | Switch readers one consumer at a time to the hypothesis spine. | parity TSV check after each consumer |
| 3d | Switch audit serializers to read from hypothesis spine. | parity TSV check |
| 3e | Delete dual-write code paths; only hypothesis spine remains. | parity TSV check |
| 3f | Update `signal_processing.py` shim with compatibility aliases / wrappers backed by the hypothesis spine. | compile + tests + import smoke |
| 3g | Delete internal legacy storage while preserving public aliases; defer any public deletion to a breaking-change spec. | compile + tests |

This long-term staging keeps later PRs reviewable. The intermediate dual-write
state adds memory cost but is safe to revert at any step.

## Rollback Condition

Stop or roll back this phase if:

- compile fails or tests regress (unit-level rollback)
- focused projection parity fails
- a previously-undetected field semantic difference between legacy and
  hypothesis spine surfaces (resolve in spec, then continue)
- migration requires changing resolver, scoring, area, matrix, or public TSV
  behavior

## What This Spec Does Not Change

- TSV column names or contents
- production scoring values
- alignment / matrix decisions
- resolver behavior
- baseline / area computation

## Open Questions

- First migrated consumer decision is closed for Phase 3:
  candidate/boundary audit projection through `append_peak_audit_rows`. Future
  slices should choose the next consumer from the inventory above, not reopen
  producer/scoring/alignment migration inside this phase.
- Remaining full-unification blocker: `PeakCandidate` still needs a
  field-by-field semantic map before producer, scoring, recovery, or alignment
  consumers move to `PeakHypothesis`.
- Should `PeakHypothesis` gain optional fields to absorb the
  `LocalMinimumRegionQuality` data, or should that stay as a separate
  embedded type? Keep separate for now; revisit if it complicates audit.
- The hypothesis spine currently uses `selected: bool`. After unification,
  does the selection decision logic move to a dedicated method on
  `PeakHypothesis`, or stay in `selection.py`? Defer the API choice to
  refactor time.
- Adapter functions in `hypotheses.py` that wrap legacy types can be deleted
  only after later full-unification work proves no external caller imports them.
- Which evidence semantics should live on `EvidenceVector` versus remain in
  `CommonEvidence` / `EvidenceSignalSet`? Default: preserve the shared
  evidence layer and only add adapter fields when parity requires them.

## Acceptance Owner

Engineering owner records the inventory, first-slice decision, focused tests,
and remaining blockers under `docs/superpowers/notes/`. This phase does not
promise final legacy-type removal and does not automatically trigger C4
implementation.
