# LC-MS/MS CID Neutral-Loss Discovery Codebase-Aligned Plan

## Status

This plan replaces the greenfield draft. It is intentionally tied to the
current XIC Extractor codebase and must not create a second independent
Discovery pipeline.

Research input:

- `docs/deepresearch/LC-MS CID Neutral Loss Discovery.md`

Historical defect and current architecture driver:

- `d4-N6-2HE-dA`, approximately `300.1605 -> 184.113`, was missed by the old
  scan-precursor-only CID-NL row-identity path.
- The current codebase already has a `product_plus_neutral_loss` rescue
  baseline. This plan protects that recall behavior and converts it into a
  durable MS1-feature-first Discovery contract; it is not a request to build a
  second rescue path.

Current repo state this plan must respect:

- `xic_extractor/discovery/` owns untargeted Discovery and seed generation.
- `xic_extractor/peak_detection/` owns trace, peak, boundary, and integration
  logic.
- `xic_extractor/neutral_loss.py` owns reusable targeted/candidate NL checks.
- `xic_extractor/raw_reader.py` owns Thermo RAW scan access.
- `scripts/run_discovery.py` is the public Discovery CLI.
- `discovery_candidates.csv`, `discovery_review.csv`, and
  `discovery_batch_index.csv` are public alignment handoff surfaces.
- `xic_extractor/alignment/csv_io.py` is the reader contract for Discovery
  outputs entering alignment.

Forbidden implementation shape:

- Do not add a parallel `src/feature_detection`, `src/ms2_association`,
  `src/nl_discovery`, `src/ms2_collapse`, or `src/decision` tree.
- Do not make CID-NL, product+NL, library scoring, or a single MS2 scan direct
  matrix-writing authority.
- Do not change ProductWriter, default matrix activation, workbook/GUI behavior,
  Backfill authority, or 85RAW scope as part of this Discovery plan.
- Do not treat this plan as permission to run 85RAW.

## North Star

CID-NL Discovery should be:

1. MS1-feature-first for row identity.
2. Evidence-provider based for MS2/NL support.
3. Explicitly auditable when scan precursor, isolation target, inferred
   precursor, and MS1 feature disagree.
4. Conservative against row inflation from repeated DDA scans, isotope triggers,
   co-isolation, and noisy products.

Plain rule:

> A product row represents an MS1 chromatographic feature. Scan precursor and
> product+NL evidence can support or rescue association to that feature, but
> cannot create an unchecked normal row without MS1 reconciliation.

## Existing Pipeline Map

Current Discovery flow:

1. `scripts/run_discovery.py`
   - CLI, settings parsing, raw path selection.
2. `xic_extractor.discovery.pipeline.run_discovery`
   - Orchestrates one RAW file.
3. `xic_extractor.discovery.ms2_seeds.collect_strict_nl_seeds`
   - Builds MS2 seed evidence.
   - Current basis values: `scan_precursor`, `product_plus_neutral_loss`.
4. `xic_extractor.discovery.grouping.group_discovery_seeds`
   - Groups same-sample, same-tag, close RT/mz/product seeds.
5. `xic_extractor.discovery.ms1_backfill.backfill_ms1_candidates`
   - Extracts XIC for grouped precursor hypotheses.
   - Detects MS1 peak via existing peak detection facade.
   - Creates `DiscoveryCandidate`.
   - Merges candidates by MS1 peak.
6. `xic_extractor.discovery.feature_family.assign_feature_families`
   - Assigns sample-local feature families/superfamilies.
7. `xic_extractor.discovery.csv_writer`
   - Writes `discovery_candidates.csv` and `discovery_review.csv`.
8. `xic_extractor.alignment.csv_io`
   - Reads Discovery candidates into alignment.

Default stance:

- Start by deepening these owners because they are the current public workflow
  and compatibility surface.
- Do not treat the current workflow as automatically correct. A replacement or
  larger refactor is allowed when it has better evidence than incremental reuse.

## Architecture Replacement Gate

Use this gate before replacing a current owner, changing the Discovery workflow,
or introducing a new module boundary for CID-NL Discovery.

Replacement proposal must state:

- Current pain:
  - the existing owner/workflow failure mode;
  - why a small patch would preserve the wrong model;
  - which current tests or real-data artifacts expose the limitation.
- Proposed owner boundary:
  - the new package/module location;
  - what behavior moves there;
  - which old owner becomes a facade, adapter, or deleted path.
- Evidence-provider role:
  - how CID-NL/MS2 evidence enters `PeakHypothesis`, `EvidenceVector`, model
    selection, or audit fields;
  - why the replacement still does not make CID-NL or a single MS2 event direct
    matrix-writing authority.
- Call-cost comparison:
  - RAW opens;
  - MS2 scans iterated;
  - XIC calls;
  - repeated smoothing/integration work;
  - seed/group/candidate counts;
  - expected 8RAW runtime delta.
- Public contract migration:
  - CLI/config changes;
  - `DiscoverySettings`, seed/group/candidate model changes;
  - CSV schema and parser compatibility;
  - candidate/row identity migration;
  - batch index behavior;
  - expected diff for existing fixtures and real outputs.
- Validation oracle:
  - focused tests proving the old limitation and the replacement behavior;
  - named one-RAW manual EIC/MS2 check for `300.1605 -> 184.113`;
  - 8RAW Discovery/parser parity before any alignment or matrix claim;
  - row-inflation and duplicate-row negative checks.
- Kill switch:
  - what metric or failed oracle kills the replacement and returns to
    incremental repair.

Approval rule:

- Replace a workflow only when the evidence shows at least one material gain:
  better true-feature recall, lower false row inflation, clearer row identity,
  lower call cost, or materially simpler maintainability.
- If the replacement only looks cleaner but cannot beat the current workflow on
  a named oracle, keep it as research/design notes instead of product code.
- If the existing workflow is proven wrong but the replacement is not proven
  better, first isolate the wrong behavior behind a compatibility facade and add
  tests before deleting or replacing it.

## Public Contract Surfaces

Any implementation phase that changes one of these is a public-contract change:

- `scripts/run_discovery.py` flags/defaults.
- `DiscoverySettings` fields and preset propagation.
- `DiscoverySeed`, `DiscoverySeedGroup`, `DiscoveryCandidate`.
- `DISCOVERY_CANDIDATE_COLUMNS`, `DISCOVERY_BRIEF_COLUMNS`, and
  provenance columns.
- CSV formatting, ordering, row identity, candidate id semantics, and batch
  index paths.
- `alignment/csv_io.py` parser acceptance/rejection behavior.
- Alignment reader row-identity semantics.
- Default matrix contents are out of scope for this plan and require a separate
  ProductWriter/default-output activation contract.

Required for public-contract changes:

- Add a schema/version note or prove backward-compatible additive columns.
- Add writer/reader roundtrip tests.
- Add negative parser tests for invalid enum/basis/identity mismatch.
- State expected output diff before running real RAW validation.

## Phase 0 - Contract Lock And Current-State Characterization

Goal:

Lock the codebase-native shape before behavior changes.

Work:

- Document current Discovery ownership in this plan.
- Convert deepresearch citation placeholders into stable source links before any
  source-backed architecture doc is promoted.
- Characterize the current `300.1605 -> 184.113` behavior in tests/artifacts:
  - direct scan-precursor path can fail;
  - product+NL rescue can recover;
  - recovered rows retain `scan_precursor_mz`,
    `scan_precursor_delta_da`, and `precursor_mz_basis`;
  - existing isotope-related rows such as `301.165 -> 185.116` remain valid.
- State that current output evidence is `diagnostic_only` unless a later phase
  explicitly reruns public outputs and passes expected-diff tests.

Deliverables:

- This codebase-aligned plan.
- A short implementation note or issue brief that names exact owner modules.

Acceptance:

- No new package tree is proposed for responsibilities already owned by
  `xic_extractor.discovery`, `xic_extractor.peak_detection`, `raw_reader`, or
  `alignment/csv_io`.
- The plan names public CSV/alignment contracts before implementation.
- No ProductWriter/default matrix/backfill authority behavior is changed.

Validation:

- Docs-only smoke: read the plan and verify no `src/...` deliverables remain.
- Subagent review: `strategy-challenger` and
  `implementation-contract-reviewer`.

## Phase 1 - Discovery Evidence Model In Existing Modules

Goal:

Make precursor metadata disagreement representable without making illegal states
look authoritative.

Existing owner/helper to reuse:

- `xic_extractor.discovery.models`
- `xic_extractor.discovery.ms2_seeds`
- `xic_extractor.discovery.grouping`
- `xic_extractor.raw_reader.Ms2Scan`
- `xic_extractor.tabular_io`

Work:

- Keep current basis values:
  - `scan_precursor`
  - `product_plus_neutral_loss`
  - grouped `mixed`
- Add only codebase-native acquisition metadata fields if the RAW reader can
  supply them. The owner sequence is:
  - optional fields on `raw_reader.Ms2Scan`;
  - propagation to `DiscoverySeed` and `DiscoveryCandidate`;
  - additive render in `discovery.csv_writer`;
  - optional parse/roundtrip in `alignment/csv_io.py`.
- Candidate fields to consider:
  - `filter_string`
  - `selected_ion_mz`
  - `isolation_target_mz`
  - `isolation_lower_offset`
  - `isolation_upper_offset`
  - `isolation_window_min_mz`
  - `isolation_window_max_mz`
- Add `acquisition_metadata_absence_reason` when a field cannot be reliably
  supplied from Thermo RAW. Do not fake mzML semantics.
- New metadata columns must be backward compatible:
  - legacy rows with missing headers remain readable until a schema-versioned
    migration explicitly removes support;
  - blank metadata values are valid;
  - invalid enum-like metadata values fail closed only after the field becomes a
    declared enum.
- Preserve `scan_precursor_mz` as acquisition evidence, not row identity.
- Preserve `precursor_mz` as the current Discovery row/candidate precursor
  hypothesis until Phase 3 formalizes the MS1-feature-first identity.

Acceptance:

- A seed/candidate can represent:
  - scan precursor approximately equals candidate precursor;
  - scan precursor disagrees but product+NL inferred precursor matches the
    candidate;
  - mixed grouped evidence;
  - missing isolation metadata.
- `alignment/csv_io.py` still accepts legacy rows with blank or absent new
  metadata columns until a versioned migration explicitly changes that contract.
- Invalid basis values fail closed.

Tests:

- `tests/test_discovery_ms2_seeds.py`
- `tests/test_discovery_grouping.py`
- `tests/test_discovery_csv.py`
- `tests/test_alignment_csv_io.py`

Stop rule:

- Stop if adding metadata would require a broad RAW reader rewrite before the
  300.1605 decision can be protected. In that case, keep fields absent and move
  with current `scan_precursor_mz`/delta audit.

## Phase 2 - MS1 Feature Reconciliation Before Normal Row Status

Goal:

Make the current `ms1_backfill`/feature-family layer the explicit row-identity
gate for CID-NL Discovery candidates.

Existing owner/helper to reuse:

- `xic_extractor.discovery.ms1_backfill`
- `xic_extractor.discovery.feature_family`
- `xic_extractor.signal_processing.find_peak_and_area`
- `xic_extractor.peak_detection` modules when moving behavior behind the facade

Work:

- Treat current `DiscoveryCandidate.ms1_peak_found`,
  `ms1_apex_rt`, `ms1_peak_rt_start`, `ms1_peak_rt_end`, `ms1_area`,
  `ms1_height`, `ms1_trace_quality`, and `ms1_scan_support_score` as the first
  MS1-feature reconciliation surface.
- Add a real public field only when CSV migration is handled:
  `discovery_candidate_state`.
- `discovery_candidate_state` is owned by `discovery.models`, assigned by
  `discovery.ms1_backfill`/`discovery.feature_family`, rendered by
  `discovery.csv_writer`, and parsed/validated by `alignment/csv_io.py`.
- Candidate states are enum values, not free-text `reason` fragments:
  - `ms1_feature_nl_supported`
  - `ms1_feature_nl_rescued`
  - `review_only_orphan_nl`
  - `review_only_ambiguous_coisolation`
  - `rejected_noise_or_outside_rt`
- `reason` remains human-readable explanation. It must not be the machine
  contract for normal/review-only/reject status.
- Keep current `merge_candidates_by_ms1_peak` and
  `assign_feature_families` as the first repeated-MS2 collapse mechanism.
- Any move from `signal_processing` facade into `peak_detection` must be
  behavior-preserving and characterization-tested first.

Acceptance:

- Multiple MS2 seeds under the same detected MS1 peak produce one Discovery
  candidate/family, not one row per scan.
- Product+NL evidence without a detected MS1 peak is review-only, not a normal
  product row.
- The `300.1605 -> 184.113` scenario is recovered through MS1 evidence, not by
  trusting product+NL alone.
- Invalid `discovery_candidate_state` values are rejected by parser tests once
  the field is public.

Tests:

- Existing `tests/test_discovery_ms1_backfill.py`.
- New focused cases for:
  - same MS1 peak with mixed scan precursor values;
  - product+NL with no MS1 peak;
  - two RT-separated MS1 peaks with same product ion;
  - repeated MS2 under one peak.

Stop rule:

- Stop if the implementation requires replacing the peak detector. The first
  product slice must reuse current trace extraction and peak detection.

## Phase 3 - MS2 Association And Evidence Paths

Goal:

Keep all legitimate CID-NL evidence paths while preventing row explosion.

Existing owner/helper to reuse:

- `xic_extractor.discovery.ms2_seeds`
- `xic_extractor.neutral_loss`
- `xic_extractor.ms2_trace_evidence`

Evidence paths:

- Path A: scan precursor minus configured neutral loss.
- Path B: observed product plus configured neutral loss.
- Path C: expected product from the already extracted MS1 feature hypothesis.
- Path D: combined evidence with RT boundary and MS1 feature reconciliation.

Path C/D boundary:

- In v1, Path C and D may only operate inside existing MS2-seeded
  candidate/groups and their extracted MS1 peaks.
- They must not start a global MS1 feature enumeration, a new MS2 association
  workflow, or a second Discovery pipeline.
- The implementation must report lightweight call-cost counters for real RAW
  validation: RAW opens, MS2 scans iterated, XIC calls, seed count, group count,
  and candidate count.

Work:

- Do not discard B/C/D only because Path A fails.
- Do not accept solely because product+NL inferred precursor exists.
- Record, at minimum:
  - evidence path;
  - scan id and RT;
  - observed product m/z/intensity/base ratio;
  - configured neutral loss;
  - inferred precursor;
  - scan precursor versus inferred precursor delta;
  - candidate/MS1 peak RT relation;
  - decision reason code.
- Keep product ion matching and intensity thresholds transparent and
  configurable through existing Discovery settings/presets only after public
  config tests are added.
- Stop the phase if call-cost counters show new work outside the existing
  single-RAW orchestration shape.

Acceptance:

- The `300.203/300.180/301.165` scan precursor examples can support the same
  `300.160` MS1 feature through product+NL and RT/MS1 reconciliation.
- A matching inferred precursor outside the MS1 feature RT boundary is rejected
  or review-only.
- Multiple strong MS1 features inside the same isolation/acquisition window are
  ambiguous, not silently accepted as confirmed.

Tests:

- Focused synthetic tests for all four paths.
- Negative tests for product noise and outside-RT inferred precursor.
- Parser/writer tests if new evidence fields are emitted.

Stop rule:

- Stop if a proposed score starts acting as write authority. Evidence scores may
  rank review output, but row creation must still be rule/audit based.
- Stop if Path C or D requires global MS1-feature enumeration, a second
  Discovery workflow, or extra RAW opens beyond the existing single-RAW
  orchestration.

## Phase 4 - Public Output Migration

Goal:

Expose the new evidence without breaking alignment or downstream review.

Existing owner/helper to reuse:

- `xic_extractor.discovery.csv_writer`
- `xic_extractor.alignment.csv_io`
- `xic_extractor.tabular_io`
- `scripts/check_discovery_precursor_inference_artifact.py`

Work:

- Prefer additive columns to existing CSVs.
- If a breaking schema is unavoidable, introduce a versioned output and keep the
  existing reader path until alignment migration is complete.
- Current `candidate_id` is a legacy public key that encodes
  `best_ms2_scan_id`, precursor m/z, and product m/z. Preserve it until an
  expected-diff migration replaces the join contract.
- `best_ms2_scan_id` and `seed_scan_ids` are provenance, not MS1 row truth.
- Add `ms1_feature_row_id` before changing alignment row identity:
  - owner: `discovery.models`;
  - rendered by `discovery.csv_writer`;
  - parsed by `alignment/csv_io.py`;
  - stable across representative-seed changes for the same reconciled MS1
    feature;
  - duplicate values are rejected for two normal rows in the same sample/tag
    scope unless the rows are explicitly marked review-only.
- If `candidate_id` semantics change, the expected diff must list changed ids,
  old/new row keys, and downstream parser behavior.
- All new enums must have parser validation and negative tests.
- Avoid generated validation outputs in version control unless they are durable
  fixtures by explicit plan.

Acceptance:

- Current alignment reader still parses existing fixtures.
- New rows roundtrip through writer -> reader.
- New audit fields do not change row ordering unless expected-diff approves it.
- Discovery batch index remains the single source for candidate/review CSV paths
  in a run.
- Legacy `candidate_id` remains available as provenance until
  `ms1_feature_row_id` is activated as the alignment row key by separate
  expected-diff review.

Tests:

- `tests/test_discovery_csv.py`
- `tests/test_alignment_csv_io.py`
- `tests/test_run_discovery.py`
- `tests/test_discovery_pipeline.py`

Stop rule:

- Stop before changing alignment behavior if Discovery output migration is not
  covered by expected-diff tests.

## Phase 5 - Validation Gates

Goal:

Validate recall rescue and row-inflation safety in increasing cost tiers.

Gate 1 - focused/synthetic:

- `collect_strict_nl_seeds` direct path passes.
- product+NL rescue passes.
- same-scan candidate id uniqueness passes.
- repeated-MS2 same-feature collapse passes.
- product+NL without MS1 peak is review-only.
- co-isolation ambiguity is not confirmed.

Gate 2 - one RAW regression:

- Use the same Thermo RAW path shape documented in
  `docs/agent-parameter-settings.md`.
- Validate only the named case first:
  - `TumorBC2312_DNA`
  - RT window around 22-25 min
  - recovered `300.1605 -> 184.113`
  - no loss of valid isotope-related rows.

Gate 3 - 8RAW Discovery:

- Run Discovery only unless the phase explicitly needs alignment acceptance.
- Expected checks:
  - recovered `300.1605 -> 184.113` rows across relevant samples;
  - no duplicate candidate id collisions;
  - row count delta explained by basis and evidence path;
  - no broad row inflation from product noise;
  - no regression for existing `scan_precursor` rows.

Gate 4 - 8RAW alignment parser compatibility smoke:

- This gate is read-only compatibility, not matrix/backfill activation.
- It may run only after the Discovery output contract passes.
- Expected checks:
  - `discovery_batch_index.csv` resolves candidate/review CSV paths;
  - `alignment/csv_io.py` accepts the Discovery output schema;
  - row identity fields parse and duplicate ids fail closed;
  - parser behavior matches the expected-diff contract.
- If stale duplicate-claim state, accepted-cell counts, default matrix values,
  or Backfill authority fail, stop and open a separate alignment/matrix plan.
  Do not fix those behaviors inside this Discovery foundation plan.

85RAW:

- Not part of the default plan.
- May run only after 8RAW closes a named product decision and the launch shape
  follows `docs/agent-parameter-settings.md`.

Evidence labels:

- Synthetic tests: `focused_tests`.
- One RAW: `manual_eic_ms2_review` only if paired with manual EIC/MS2 inspection,
  otherwise `diagnostic_only`.
- 8RAW Discovery plus parser smoke: `8RAW_parity` only when expected-diff gates
  pass.
- No test result alone is `production_ready` without the public output contract.

## Phase 6 - Product Decision Policy For Discovery Rows

Goal:

Translate natural-language Discovery behavior into deterministic row states.

Existing owner/helper to reuse:

- `xic_extractor.discovery.models`
  - owns the machine enum for `discovery_candidate_state`.
- `xic_extractor.discovery.ms1_backfill`
  - assigns state from MS1 peak, RT boundary, seed, and trace evidence.
- `xic_extractor.discovery.feature_family`
  - resolves repeated-MS2/same-MS1-feature collapse and family context.
- `xic_extractor.discovery.priority`
  - owns review priority and human-readable reason generation.
- `xic_extractor.discovery.evidence_score`
  - may rank review output, but must not become write authority.
- `xic_extractor.discovery.csv_writer`
  - renders fields only; it must not recompute state.
- `xic_extractor.alignment.csv_io`
  - parses and validates public enum values.

Forbidden owner shape:

- Do not add a new `decision` package or put policy in the CSV writer.
- Do not make ProductWriter, default matrix, Backfill, or alignment acceptance
  depend on this policy inside the Discovery foundation phase.

Normal Discovery row candidate:

- MS1 peak exists.
- MS2 scan RT overlaps or is explainably close to the MS1 feature boundary.
- At least one CID-NL evidence path supports the feature.
- The evidence is not better explained by a stronger co-isolated feature.
- The candidate is not a duplicate representation of an already represented
  MS1 feature.

Review-only:

- product+NL evidence exists but no MS1 peak was detected.
- multiple strong MS1 features can explain the same MS2 evidence.
- isolation metadata conflicts with feature assignment.
- scan precursor, inferred precursor, and MS1 feature disagree with no
  explainable isotope/co-isolation path.
- product evidence is weak or non-reproducible.
- isotope/adduct explanation is plausible but unresolved.

Reject:

- MS2 RT is outside the candidate MS1 feature boundary and not covered by an
  explicit boundary-rescue rule.
- product ion is below configured intensity/SNR threshold.
- neutral-loss delta is outside tolerance.
- inferred precursor has no MS1 support and no review-only rationale.
- accepting would create a duplicate normal row for the same MS1 feature.

Tests:

- Focused state-assignment tests for normal/rescued/review-only/reject cases.
- Writer/reader roundtrip for `discovery_candidate_state`.
- Negative parser test for invalid state enum.
- Regression test proving ProductWriter/default matrix/Backfill authority is not
  touched by Discovery state classification.

Stop rule:

- Stop if implementing this phase requires a new decision module, changes
  ProductWriter/default matrix output, or promotes `evidence_score` to authority.

Open policy decisions before implementation:

- Product m/z tolerance and low-m/z Da/ppm hybrid behavior.
- Minimum product relative intensity.
- Whether repeated-MS2 support can promote review-only to normal.
- How much isolation-window metadata is available from Thermo RAW on this
  machine.
- Whether isotope/adduct grouping is required for v1 or only an audit flag.
- Whether orphan MS2 evidence can ever become quantifiable. Default: no.

## Phase 7 - Implementation Backlog

Ticket 1 - Current contract tests

- Owners: `tests/test_discovery_ms2_seeds.py`,
  `tests/test_discovery_ms1_backfill.py`, `tests/test_discovery_csv.py`,
  `tests/test_alignment_csv_io.py`.
- Done when current 300.1605 behavior and output parsing are pinned.

Ticket 2 - Acquisition metadata audit fields

- Owners: `raw_reader.py`, `discovery/models.py`, `discovery/csv_writer.py`.
- Done when available precursor/isolation metadata and
  `acquisition_metadata_absence_reason` can be emitted additively, and blank or
  absent fields remain backward-compatible.

Ticket 3 - MS1-feature reconciliation states

- Owners: `discovery/models.py`, `discovery/ms1_backfill.py`,
  `discovery/feature_family.py`, `discovery/priority.py`,
  `discovery/csv_writer.py`, `alignment/csv_io.py`.
- Done when `discovery_candidate_state` explicitly distinguishes normal,
  rescued, review-only, and rejected Discovery states without changing matrix
  authority.

Ticket 4 - Evidence path consolidation

- Owners: `discovery/ms2_seeds.py`, `neutral_loss.py` if reusable checks are
  extracted.
- Done when Path A/B/C/D evidence is represented with reason codes and no path
  alone can create an unchecked normal row.

Ticket 5 - Public CSV migration

- Owners: `discovery/models.py`, `discovery/csv_writer.py`,
  `alignment/csv_io.py`, `scripts/run_discovery.py`.
- Done when writer/reader roundtrip, enum validation, `ms1_feature_row_id`
  migration, expected row ordering, and batch index behavior are tested.

Ticket 6 - One-RAW and 8RAW validation

- Owners: existing scripts and task-specific `output/` or
  `docs/superpowers/validation/` summaries.
- Done when the named 300.1605 regression and row-inflation checks pass.

Ticket 7 - Release/handoff update

- Owners: current handoff and control plane only if tier, active lane,
  authority, or public surface actually changes.
- Done when downstream readers know whether the change is diagnostic-only,
  production-candidate, or production-ready.

## Definition Of Done

This Discovery redesign is product-ready only when:

- It uses the existing XIC package owners, not a new parallel pipeline.
- It creates one normal row per reconciled MS1 chromatographic feature, not one
  row per MS2 event.
- It recovers true CID-NL features when scan precursor metadata is offset from
  true MS1 feature m/z.
- It does not promote noisy product+NL inference into uncontrolled row creation.
- It collapses repeated DDA events under the same MS1 peak.
- It flags co-isolation, isotope/adduct, and precursor disagreement cases.
- It preserves enough scan-level and row-level audit fields to explain both
  accepted and rejected/review-only decisions.
- It keeps row creation, MS2 association, annotation, alignment, Backfill, and
  matrix writing as separate responsibilities.
- It passes focused tests plus the named RAW/8RAW gates required by the public
  surface being changed.

## Review Requirements

Before implementation:

- `strategy-challenger` reviews whether this advances the product direction and
  does not preserve a bad legacy path.
- `implementation-contract-reviewer` reviews owner placement, public CSV/API
  migration, and test coverage.

Before any RAW-backed acceptance:

- `validation-evidence-reviewer` reviews the gate shape and evidence label.

Control plane:

- No control-plane update is required for this docs-only plan rewrite.
- Update the control plane only if a later implementation changes tier, active
  lane, ProductWriter/default-output authority, public schema, or validation
  readiness claim.

## Decision Spike v1 Addendum - A Owner-Deepening Execution Contract

Status:

- This addendum is the next executable slice after the A/B architecture decision
  spike in
  `docs/superpowers/plans/LC-MS CID Neutral Loss Discovery Architecture Alternatives Brief.md`.
- It narrows Phase 7 tickets 3, 5, and 6 into one end-to-end continuation.
- It does not replace the North Star, existing owner map, or A/B brief. It only
  defines how to deepen the existing A path before reopening any B adapter.
- It does not authorize ProductWriter/default matrix/workbook/GUI/Backfill
  authority changes, default activation, 85RAW, or a second maintained Discovery
  system.

Plain-language decision:

- The decision to continue with A is not a claim that the original A design was
  clean. It is a claim that the current evidence does not justify maintaining a
  second Discovery system.
- A already recovers the named biology oracle in the one-RAW baseline:
  `300.1605 -> 184.113`.
- A also preserves the isotope-related `301.165 -> 185.116` row when it carries
  its own `DNA_dR` tag evidence.
- The current failure is architectural explicitness: the public Discovery CSV
  still lacks a first-class row state and a stable MS1 feature row identity.
- Therefore the next move is to absorb B's useful concepts into A: feature-first
  row identity, evidence-late support, explicit states, parser fail-closed
  behavior, and writer-as-renderer discipline.

Required context to read before implementation:

This addendum is the execution contract for the next slice. The A/B brief is the
decision record, the control plane owns maturity tier and active lane, and the
current handoff is only a compact state snapshot.

- `AGENTS.md`
- `docs/agent-parameter-settings.md`
- `docs/architecture-contract.md`
- `docs/agent-subagent-routing.md`
- `docs/deepresearch/LC-MS CID Neutral Loss Discovery.md`
- `docs/superpowers/plans/LC-MS CID Neutral Loss Discovery plan.md`
- `docs/superpowers/plans/LC-MS CID Neutral Loss Discovery Architecture Alternatives Brief.md`
- `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md`
  as current state, not contract authority
- `scripts/check_discovery_architecture_ab_artifact.py`
- `tests/test_discovery_architecture_ab_artifact.py`

### Architecture Preflight

Objective:

- Deepen the existing Discovery A path so every normal candidate row is an MS1
  chromatographic feature with explicit state, provenance, tag evidence, and a
  stable `ms1_feature_row_id`.

Existing owners to reuse:

- `scripts/run_discovery.py` remains the public CLI.
- `xic_extractor.discovery.pipeline` orchestrates.
- `xic_extractor.discovery.ms2_seeds` creates MS2/CID-NL evidence.
- `xic_extractor.discovery.grouping` groups seed evidence.
- `xic_extractor.discovery.ms1_backfill` reconciles hypotheses to MS1 traces and
  peaks.
- `xic_extractor.discovery.feature_family` owns family grouping.
- `xic_extractor.discovery.models` owns Discovery row data.
- `xic_extractor.discovery.csv_writer` renders Discovery CSVs.
- `xic_extractor.alignment.csv_io` owns the alignment reader contract.

No new owners:

- Do not create a parallel `feature_primary` Discovery product path.
- Do not hide a B adapter behind `scripts/run_discovery.py` CLI/config flags.
- Do not add a second manifest or source of truth for Discovery rows.
- Do not let diagnostic TSVs, candidates, or sidecars become matrix authority.

Evidence role:

- CID-NL, MS2 scan precursor, product+neutral-loss inference, isolation metadata,
  MS1 shape, RT, and future models are evidence providers.
- They support `EvidenceVector`, `PeakHypothesis`, candidate state, and
  `AuditTrail`; they do not directly write ProductWriter authority.

Public contract risk:

- `discovery_candidates.csv` changes additively by gaining
  `discovery_candidate_state` and `ms1_feature_row_id`.
- The alignment reader must accept valid new rows and fail closed on invalid
  state/identity rows.
- `candidate_id` remains provenance and compatibility identity; it must not be
  promoted back into row authority.
- `discovery_batch_index.csv` and existing public paths remain compatible.

Call-cost model:

- Phase 0 to Phase 3 use static code review and focused tests only.
- Phase 4 uses one RAW: `TumorBC2312_DNA.raw`, RT `22-25`.
- Phase 5 may use 8RAW Discovery/parser evidence only if the one-RAW oracle
  passes and the implementation is otherwise contract-clean.
- Do not run 85RAW or default activation in this slice.

Stop rule:

- Stop and document the blocker if the work requires ProductWriter/default
  matrix/workbook/GUI/Backfill authority changes, a global MS1 feature
  enumerator, a B runtime flag, 85RAW, or a candidate-as-matrix-row shortcut.

### Concepts To Absorb From B

1. Feature-first row identity:
   A row is primarily an MS1 chromatographic feature in a sample/tag context,
   not an MS2 scan event and not a formatted `candidate_id`.

2. Evidence-late support:
   CID-NL/MS2 evidence explains why a feature is plausible. It does not create
   an unchecked normal row without MS1 reconciliation.

3. Explicit state:
   The state must be a data field, not an inference from reason strings,
   candidate IDs, or missing columns.

4. Candidate ID demotion:
   `candidate_id` remains useful for traceability and compatibility, but the
   durable row concept is `ms1_feature_row_id` plus state/provenance.

5. Ambiguity as a first-class outcome:
   Co-isolation, repeated DDA, isotope/adduct pressure, and missing MS1 support
   must become explicit states or audit facts, not silent row inflation.

6. Writer render-only:
   The CSV writer serializes fields already decided by Discovery owners. It must
   not recompute state, tag evidence, or row identity.

7. Parser fail-closed:
   Alignment input parsing must reject invalid state/identity combinations
   before downstream model selection can treat them as usable evidence.

### Successor Contract

Required public CSV fields:

- `discovery_candidate_state`
- `ms1_feature_row_id`

Required state semantics:

- A normal Discovery row has MS1 feature support and tag/evidence provenance.
- A rescued Discovery row still has MS1 feature support; the rescue is about the
  evidence path, not permission to skip feature identity.
- A review-only row is observable evidence but not a normal matrix candidate.
- A rejected row is explainable evidence that must not enter normal candidate
  flow.

Recommended initial state vocabulary:

- `ms1_feature_nl_supported`
- `ms1_feature_nl_rescued`
- `review_only_orphan_nl`
- `review_only_ambiguous_coisolation`
- `rejected_noise_or_outside_rt`

This vocabulary may be renamed during implementation, but the final names must
remain short, human-explainable, and test-covered. Avoid nested
dataset-specific qualifiers.

`ms1_feature_row_id` invariant:

- Stable inside one Discovery output for the same sample, tag, MS1 feature m/z
  region, and RT peak.
- Independent of the representative MS2 scan number.
- Independent of whether the evidence basis is `scan_precursor`,
  `product_plus_neutral_loss`, or `mixed`.
- Distinct for `300.1605 -> 184.113` and `301.165 -> 185.116` when both carry
  their own tag evidence.

Successor checker must assert:

- `300.1605 -> 184.113` is recovered for `TumorBC2312_DNA`.
- The recovered row has explicit state, `ms1_feature_row_id`, tag evidence,
  source/provenance, and parser compatibility.
- `301.165 -> 185.116` is preserved as its own `DNA_dR` tag pair, not merely as
  any row near that product m/z.
- Row identity/provenance/tag/source state pass, not only m/z/product
  existence.

### Phase 0 - Research And Trap Inventory

Tasks:

- Re-read the authoritative inputs above.
- Inspect the current Discovery owner path from seed collection through CSV
  writing and alignment parsing.
- Enumerate design traps found in the current A path: scan-event identity,
  product+NL row inflation, reason-string authority, writer recomputation,
  parser permissiveness, isotope demotion, and candidates-as-matrix-rows.
- Check existing tests before adding new ones, especially
  `tests/test_discovery_ms2_seeds.py`, `tests/test_discovery_ms1_backfill.py`,
  `tests/test_discovery_csv.py`, `tests/test_alignment_csv_io.py`, and
  `tests/test_discovery_architecture_ab_artifact.py`.

Deliverables:

- A short owner/trap note in the implementation summary or handoff.
- A concrete list of files that will be changed.
- A statement that no ProductWriter/default matrix/workbook/GUI/Backfill
  authority is in scope.

Decision point:

- If the existing owners can express the successor contract, continue to Phase
  1.
- If they cannot, stop and propose a minimal owner refactor inside
  `xic_extractor.discovery`, not a B product adapter.

Acceptance criteria:

- The implementer can name the exact owner for state assignment, row identity,
  CSV rendering, and parser validation.
- No new parallel Discovery workflow is introduced.

### Phase 1 - Design The A Successor Contract

Tasks:

- Define the final `discovery_candidate_state` enum or literal vocabulary.
- Define `ms1_feature_row_id` construction and collision rules.
- Define how state is assigned from grouped MS2 evidence and MS1 backfill
  results.
- Define invalid state/identity combinations for parser rejection.
- Define the expected additive CSV diff and backward-compatibility behavior.

Deliverables:

- Contract notes in the plan, commit message body, or implementation summary.
- Focused tests written first or updated first for state assignment, writer
  output, reader parsing, and checker behavior.
- Expected one-RAW diff: current A's biology recall should remain, while the
  successor checker changes from intentional fail to pass.

Decision point:

- If state requires ProductWriter or alignment model-selection authority to be
  meaningful, stop. The state is being placed too late.
- If `candidate_id` must be parsed as the only durable row identity, stop. The
  successor contract has not actually been implemented.

Acceptance criteria:

- The design can explain why `300.1605 -> 184.113` and
  `301.165 -> 185.116` are distinct rows without special-casing either pair.
- The design can explain where orphan NL evidence goes without becoming a
  normal matrix candidate.

### Phase 2 - Implement Existing-Owner Deepening

Tasks:

- Add the new state and `ms1_feature_row_id` to existing Discovery models.
- Assign state and feature row identity in the existing MS1 reconciliation path.
- Render the new fields additively from `discovery.csv_writer`.
- Parse and validate the new fields in `alignment.csv_io`.
- Preserve current public CLI shape in `scripts/run_discovery.py`.
- Preserve current default matrix, workbook, GUI, and Backfill behavior.

Deliverables:

- Implementation code in existing owners only.
- Updated focused tests.
- No B adapter, no new CLI/config flag, no second source of truth.

Decision point:

- If implementation starts duplicating seed grouping/backfill logic under a new
  adapter, stop and refactor back into existing owners.
- If the writer needs to infer state from strings, move the state assignment
  earlier.

Acceptance criteria:

- Existing valid Discovery output remains parseable.
- New Discovery output contains `discovery_candidate_state` and
  `ms1_feature_row_id`.
- Invalid state values fail closed in parser tests.
- `alignment.csv_io` parser tests reject normal or rescued rows with blank
  `ms1_feature_row_id`, duplicate `ms1_feature_row_id` in the same sample/tag
  scope, and any state/identity combination declared invalid in Phase 1.
- `301.165 -> 185.116` is not demoted or deleted when it has tag evidence.

### Phase 3 - Focused Contract Verification

Tasks:

- Run the focused checker tests.
- Run Discovery CSV writer/reader tests.
- Run alignment CSV parser tests, including negative cases for invalid states,
  blank normal/rescued `ms1_feature_row_id`, duplicate normal/rescued
  `ms1_feature_row_id` in the same sample/tag scope, and Phase 1 invalid
  state/identity combinations.
- Run ruff on changed files.
- Run `scripts/check_productization_state.py` only to verify no accidental
  control-plane inconsistency if docs/control-plane-adjacent files changed.

Minimum commands:

```powershell
python -m pytest tests\test_discovery_architecture_ab_artifact.py tests\test_discovery_precursor_inference_artifact.py -q
uv run pytest tests/test_discovery_csv.py tests/test_alignment_csv_io.py -v --tb=short
uv run ruff check xic_extractor/discovery xic_extractor/alignment scripts/check_discovery_architecture_ab_artifact.py tests/test_discovery_architecture_ab_artifact.py
uv run python scripts/check_productization_state.py
```

Deliverables:

- Test output summary in final/handoff.
- Any failing checker output preserved under task-specific `output/` if useful.

Decision point:

- If focused tests fail due to a contract disagreement, fix the contract or
  implementation before RAW validation.
- Do not use RAW output to compensate for failing unit/contract tests.

Acceptance criteria:

- Focused tests pass.
- Parser compatibility is explicit.
- No ProductWriter/default matrix/Backfill authority change is observed.

### Phase 4 - One-RAW Product Oracle

Tasks:

- Rerun Discovery on `TumorBC2312_DNA.raw` with RT `22-25`.
- Run the legacy precursor-inference checker to ensure recall did not regress.
- Run the successor architecture checker against the new A output.
- Inspect row facts for both named pairs.

One-RAW command shape:

```powershell
.venv\Scripts\python.exe scripts\run_discovery.py `
  --raw C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation\TumorBC2312_DNA.raw `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\discovery_architecture_ab\a_incremental\one_raw_tumorbc2312 `
  --rt-min 22 `
  --rt-max 25 `
  --timing-output output\discovery_architecture_ab\a_incremental\one_raw_tumorbc2312\timing.json
```

Checker command shape:

```powershell
.venv\Scripts\python.exe scripts\check_discovery_architecture_ab_artifact.py `
  --baseline-candidates output\discovery_architecture_ab\a_incremental\one_raw_tumorbc2312\discovery_candidates.csv `
  --candidate-candidates output\discovery_architecture_ab\a_incremental\one_raw_tumorbc2312\discovery_candidates.csv `
  --focus-sample TumorBC2312_DNA `
  --focus-precursor-mz 300.1605 `
  --focus-product-mz 184.113 `
  --preserve-precursor-mz 301.165 `
  --preserve-product-mz 185.116 `
  --preserve-tag DNA_dR `
  --summary-json output\discovery_architecture_ab\a_incremental\one_raw_tumorbc2312\architecture_ab_check.json `
  --check-only
```

Deliverables:

- Updated one-RAW output under
  `output/discovery_architecture_ab/a_incremental/one_raw_tumorbc2312/`.
- `architecture_ab_check.json` with `diagnostic_only` label and pass/fail
  result.
- A short evidence summary documenting row count, basis counts, parser status,
  focus pair, preserved pair, state, `ms1_feature_row_id`, tag evidence, and
  source/provenance.

Decision point:

- If A passes the successor checker, B remains closed unless a separate
  structural reason or material one-RAW advantage is demonstrated.
- If A still fails only because the successor contract is too vague, revise the
  contract and tests before touching B.
- If A cannot express the feature-first contract without becoming a pile of
  patches, stop the A pass and document the exact structural limitation. The
  next decision must choose exactly one path: a minimal refactor inside existing
  Discovery owners, a temporary B comparison adapter with deletion/facade
  endpoint, or killing B with evidence that A is sufficient.

Acceptance criteria:

- `300.1605 -> 184.113` is recovered.
- `301.165 -> 185.116` is preserved as its own `DNA_dR` tag pair.
- Both named facts include state, row identity, provenance, tag/source fields,
  and parser compatibility.
- No default activation is run.

### Phase 5 - Optional 8RAW Discovery/Parser Evidence

Entry criteria:

- Phase 4 passes.
- The remaining product decision cannot be answered by focused tests and the
  one-RAW oracle.

Tasks:

- Run at most 8RAW Discovery/parser validation.
- Do not run default activation.
- Do not run 85RAW.
- Do not claim product readiness from candidate volume alone.

Deliverables:

- 8RAW output under a task-specific `output/` path.
- Parser smoke summary.
- A statement whether the new state/identity fields remain coherent across the
  8RAW batch.

Decision point:

- If 8RAW exposes row inflation, parser, or provenance drift, fix A before B.
- If 8RAW is clean and one-RAW already passes, close B unless there is a
  documented material advantage.

Acceptance criteria:

- 8RAW, if run, is still `diagnostic_only`.
- Candidate rows are not treated as matrix rows.
- Control plane remains unchanged unless tier, active lane, or writer authority
  truly changes.

### Phase 6 - Delivery And Review

Tasks:

- Update the A/B Alternatives Brief with the new evidence and decision.
- Update the current handoff only if the next-action state changes or the
  current snapshot would otherwise be stale.
- Request subagent review for implementation and contract blast radius.
- Fix review findings before commit.
- Commit only task-scoped files after inspecting `git status --short --branch`
  and staged diff.

Deliverables:

- Updated code/tests/docs if implementation occurred.
- Focused verification summary.
- One-RAW oracle evidence summary.
- Explicit final decision: A closed successfully, A needs another owner-deepening
  pass, or B is reopened as a temporary comparison adapter.
- Explicit control-plane statement: updated because authority changed, or not
  updated because no tier/active lane/ProductWriter/Backfill authority changed.

Decision point:

- If product public surface changed only additively for Discovery diagnostics,
  label the evidence `diagnostic_only` or `production_candidate` according to
  validation. Do not claim default matrix readiness.
- If any matrix authority changed, open a separate expected-diff/default
  activation task instead of folding it into this Discovery slice.

Acceptance criteria:

- The branch contains one coherent Discovery path.
- The successor checker evidence is documented.
- The handoff gives the next agent a clear continue/stop point.
- No unrelated dirty files are staged or committed.

### B Reopen Criteria

B has two different reopen gates. Do not collapse them into a vague second pass
on A.

Gate 1 - A succeeds but B may still have material value:

- A emits `discovery_candidate_state` and `ms1_feature_row_id`.
- A passes focused tests and the one-RAW successor checker.
- B can name a material one-RAW advantage that A does not already provide.
- The proposed B adapter can test that advantage without modifying
  ProductWriter/default matrix/workbook/GUI/Backfill authority.
- The adapter is not hidden behind `scripts/run_discovery.py` CLI/config flags.
- The same plan names the deletion or facade endpoint so there will not be two
  maintained Discovery systems.

Gate 2 - A structural blocker:

- Phase 1 or Phase 2 documents that existing Discovery owners cannot express the
  successor contract cleanly without a brittle patch stack.
- The blocker names the exact owner/invariant that fails.
- The next decision chooses exactly one: minimal refactor inside existing
  Discovery owners, temporary B comparison adapter, or kill B with a documented
  reason.
- This gate does not require A to emit the successor fields first, because the
  blocker may be that A cannot emit them cleanly.

A gets one bounded owner-deepening pass. If focused tests plus the one-RAW
successor checker do not prove explicit state, stable `ms1_feature_row_id`,
parser fail-closed behavior, and preservation of both named pairs, stop and use
Gate 2 instead of opening an unbounded A cleanup loop.

B must be deleted or left unmerged when:

- It does not materially beat A on the one-RAW oracle.
- It only improves naming while duplicating the same owner responsibilities.
- It makes candidates look more like matrix rows.
- It requires public product authority changes to prove value.

### End-To-End Goal Prompt

```text
/goal
在 C:\Users\user\Desktop\XIC_Extractor 的 cc/framework-improvements branch，end-to-end 執行 LC-MS CID-NL Discovery A owner-deepening successor contract，讓既有 A path 吸收 B 的 feature-first/evidence-late 概念，並用 focused tests + one-RAW oracle 收斂是否仍需 B temporary comparison adapter。

先讀：
- AGENTS.md
- docs/agent-parameter-settings.md
- docs/architecture-contract.md
- docs/agent-subagent-routing.md
- docs/deepresearch/LC-MS CID Neutral Loss Discovery.md
- docs/superpowers/plans/LC-MS CID Neutral Loss Discovery plan.md
- docs/superpowers/plans/LC-MS CID Neutral Loss Discovery Architecture Alternatives Brief.md
- docs/superpowers/handoffs/current/cc-framework-improvements-productization.md

目前決策：
- 不先做 B feature-primary adapter。
- A 不是因為原始設計完美才被選中，而是因為目前 one-RAW evidence 顯示 A 已 recover 300.1605 -> 184.113 並 preserve 301.165 -> 185.116，沒有證據支持維護第二套 Discovery 系統。
- 下一步是在既有 Discovery owners 中加入 explicit discovery_candidate_state 與 ms1_feature_row_id，並讓 parser/checker fail-closed。

必須守住：
- 不維護兩套 Discovery 系統。
- 不把 CID-NL/MS2 evidence 直接變 ProductWriter authority。
- 不改 default matrix/ProductWriter/workbook/GUI/Backfill authority。
- 不跑 default activation。
- 不跑 85RAW；8RAW 只有在 one-RAW/focused tests 無法回答產品決策時才可考慮。
- 不新增第二份獨立 manifest/source of truth。
- 不把 candidates 當 matrix rows。
- 不 demote/delete 301.165 -> 185.116，只要它有自己的 tag evidence 就應保留。
- B temporary adapter 不可藏在 scripts/run_discovery.py CLI/config flag 後面。
- B 若 one-RAW oracle 沒明顯勝過 A，就刪掉 adapter 或不 merge product code。
- A owner-deepening 只有一個 bounded pass；若 focused tests + one-RAW successor checker 仍無法證明 state、ms1_feature_row_id、parser fail-closed 與兩個 named pairs，就停止並記錄 A structural blocker，不開無界 A cleanup。

分階段執行：
1. Research: 讀 owner path、現有 tests、checker 與 handoff，列出 A 目前地雷與要改的 owner，不動 ProductWriter/default matrix。
2. Design: 定義 discovery_candidate_state vocabulary、ms1_feature_row_id invariant、parser invalid combinations、expected additive CSV diff。
3. Implement: 在既有 xic_extractor.discovery owners 補 state/row identity，在 csv_writer render，在 alignment.csv_io parse/validate；不新增 B adapter、不改 CLI public shape。
4. Verify focused: 跑 focused checker/parser/writer tests 與 ruff；parser negative tests 必須涵蓋 invalid state、blank normal/rescued ms1_feature_row_id、同 sample/tag scope duplicate normal/rescued ms1_feature_row_id、以及 Phase 1 宣告的 invalid state/identity combinations。失敗先修 contract 或實作，不用 RAW 蓋過 unit/contract failure。
5. Verify one-RAW: rerun TumorBC2312_DNA RT 22-25，跑 legacy precursor checker 與 successor architecture checker，明確 assert 300.1605 -> 184.113 recovered、301.165 -> 185.116 preserved as its own DNA_dR tag pair，並檢查 row identity/provenance/tag/source/state。
6. Delivery: 更新 Alternatives Brief 與必要 handoff；請 subagent review，修復後 commit。control plane 只有 tier/active lane/authority 真改才更新；否則明說不需要更新。

完成條件：
- discovery_candidates.csv additive contract 有 discovery_candidate_state 與 ms1_feature_row_id。
- writer/reader/parser/checker focused tests 通過。
- one-RAW successor checker 通過或失敗原因被文件化成明確 A structural blocker。
- parser fail-closed tests 涵蓋 state + ms1_feature_row_id 組合，不只 invalid enum。
- 300.1605 -> 184.113 recovered。
- 301.165 -> 185.116 preserved as its own tag-evidence row。
- row identity/provenance/tag/source/state 被驗證，不只是 m/z/product 存在。
- A/B 決策被更新：A closed、A needs one more owner-deepening pass、或 B reopened under temporary-adapter constraints。
- 若實作，subagent review 後修復並 commit。
- 無 default activation、無 85RAW、無 ProductWriter/default matrix/workbook/GUI/Backfill authority change。
```
