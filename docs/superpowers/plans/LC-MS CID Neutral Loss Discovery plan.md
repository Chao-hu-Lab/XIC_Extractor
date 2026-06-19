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
