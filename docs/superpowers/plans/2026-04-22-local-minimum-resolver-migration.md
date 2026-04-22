# Local Minimum Resolver Migration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate targeted XIC extraction from width-based `legacy_savgol` peak
boundaries toward an MZmine-inspired `local_minimum` resolver, then make that
resolver generic enough to handle weak, broad, and clipped peaks without
exploding into target-specific recovery logic.

**Architecture:** Keep the two-mode `resolver_mode=legacy_savgol|local_minimum`
boundary and the current scoring/output plumbing. Treat the already-landed
resolver dispatch, comparison harness, and branch-only recovery patches as the
starting point, not as work still to do. The next implementation phase focuses
on changing `local_minimum` from a hard-pruning resolver into a
candidate-producing resolver that emits region-quality metadata for downstream
selection and scoring.

**Tech Stack:** Python 3.13, `numpy`, `scipy.signal.find_peaks`, existing
`pytest` suite, real RAW regression via `scripts/run_extraction.py` and
`scripts/compare_resolvers.py`.

---

## Why This Plan Was Rewritten

The original migration plan was correct about the algorithmic direction, but it
predated several facts now learned on the branch:

1. `resolver_mode` dual-mode dispatch already exists.
2. The A/B comparison harness already exists.
3. Paired anchor mismatch is already downgraded from `ND` to soft penalty.
4. Two real-data ISTD regression clusters showed that the next generic problem
   is not paired `ΔRT` logic, but `local_minimum` using too many shape rules as
   candidate existence gates.

This rewritten plan merges the original migration work with the newer review
conclusion:

**keep `local_minimum`, but make candidate generation more permissive before
continuing RT-rule simplification.**

---

## Current Branch Status

### Already completed on this branch

- `resolver_mode=legacy_savgol|local_minimum`
- config/schema support for resolver parameters
- resolver dispatch in `signal_processing.py`
- local-minimum candidate segmentation backend
- A/B comparison harness in `scripts/compare_resolvers.py`
- paired anchor mismatch downgraded to diagnostic + confidence penalty
- temporary ISTD recoveries for broad peaks and anchor-clipped traces

### Important current limitation

`local_minimum` still decides `PEAK_NOT_FOUND` too early when a region fails:

- `resolver_peak_duration_max`
- `resolver_min_scans`
- `resolver_min_ratio_top_edge`

That means the current branch still mixes up:

1. **does a plausible candidate region exist?**
2. **is this candidate strong enough to trust?**

Those must be separated.

---

## Stable Decisions

These decisions remain correct and should not be revisited in the next slice:

1. Keep `local_minimum` as opt-in until real-data acceptance is clear.
2. Keep `legacy_savgol` available as the fallback and A/B baseline.
3. Keep scoring/output schema stable.
4. Use `output/xic_results_20260420_0309.xlsx` as the current trusted workbook
   reference.

---

## Core Design Direction

The next generic iteration should follow two rules:

1. **Candidate generation 寬進**
2. **Ranking / scoring 嚴出**

Concretely:

- `local_minimum` should keep more plausible regions
- weak regions should survive as flagged candidates, not disappear as
  `PEAK_NOT_FOUND`
- selector/scorer should decide whether flagged candidates become selected
  low-confidence peaks or remain unselected

This is the branch's main architectural goal now.

---

## Scope for the Next Implementation Slice

### In scope

- `xic_extractor/signal_processing.py`
- `xic_extractor/peak_scoring.py`
- tests in:
  - `tests/test_signal_processing.py`
  - `tests/test_signal_processing_selection.py`
  - `tests/test_peak_scoring.py` if scoring consumes new metadata

### Explicitly out of scope for this slice

- changing workbook schema
- changing shipped CSV/XLSX columns
- switching the default resolver
- removing the compare harness
- large extractor orchestration rewrites
- more target-specific recoveries unless needed to preserve current behavior
  during the refactor

---

## Next Tasks

### Task 1: Freeze current branch behavior before generic refactor

**Files:**
- Modify: `tests/test_signal_processing.py`
- Modify: `tests/test_signal_processing_selection.py`
- Modify: `tests/test_extractor.py` only if temporary recoveries need guardrail tests

**Goal:**
Capture the branch behaviors that must not regress during the generic
refactor:

- broad ISTD recovery still finds the previously recovered peak
- edge-clipped ISTD retry still finds the previously recovered peak
- paired anchor mismatch remains low-confidence, not `ND`
- `legacy_savgol` output path remains unchanged

**Verification:**
- `uv run pytest tests\test_signal_processing.py tests\test_signal_processing_selection.py tests\test_extractor.py -v`

### Task 2: Extend candidate data with region-quality metadata

**Files:**
- Modify: `xic_extractor/signal_processing.py`
- Test: `tests/test_signal_processing.py`

**Goal:**
Add candidate-level metadata that can represent weak-but-plausible regions,
such as:

- edge-clipped
- too broad
- too short
- low top/edge ratio
- low scan count

This metadata should describe quality, not force immediate rejection.

**Verification:**
- `uv run pytest tests\test_signal_processing.py -v -k "local_minimum or candidate"`

### Task 3: Convert local-minimum region filters from hard reject to flagged retention

**Files:**
- Modify: `xic_extractor/signal_processing.py`
- Test: `tests/test_signal_processing.py`

**Goal:**
Change `local_minimum` so that the following mostly become flags rather than
existence gates:

- `resolver_peak_duration_min`
- `resolver_peak_duration_max`
- `resolver_min_scans`
- `resolver_min_ratio_top_edge`

Only keep hard candidate failure for:

- no signal
- window too short
- malformed arrays / invalid trace

**Verification:**
- `uv run pytest tests\test_signal_processing.py -v`

### Task 4: Teach selector/scorer to consume weak-candidate metadata

**Files:**
- Modify: `xic_extractor/signal_processing.py`
- Modify: `xic_extractor/peak_scoring.py`
- Test: `tests/test_signal_processing_selection.py`
- Test: `tests/test_peak_scoring.py` if needed

**Goal:**
Make downstream logic prefer stronger candidates while still allowing flagged
candidates to survive as lower-confidence outcomes when they are the best
available region.

Expected behavior:

- strong candidate beats weak candidate when both are plausible
- weak candidate can still beat "no peak" when it is the only plausible region
- confidence/reason explain the weakness instead of collapsing to `ND`

**Verification:**
- `uv run pytest tests\test_signal_processing_selection.py tests\test_peak_scoring.py -v`

### Task 5: Re-evaluate temporary recoveries after generic softening

**Files:**
- Modify: `xic_extractor/extractor.py` only if some temporary recovery becomes redundant
- Test: `tests/test_extractor.py`

**Goal:**
Decide whether the current branch's broad-peak and wider-window recoveries are:

- still necessary
- simplifiable
- or removable because the generic resolver now handles the same cases

This is a cleanup task, not the primary mechanism.

**Verification:**
- `uv run pytest tests\test_extractor.py tests\test_signal_processing_selection.py -v`

### Task 6: Truth-aware real-data validation

**Files:**
- Reuse: `scripts/compare_resolvers.py`
- Manual compare against: `output/xic_results_20260420_0309.xlsx`

**Goal:**
Evaluate both:

1. `legacy_savgol` vs `local_minimum`
2. `local_minimum` vs trusted workbook truth proxy

Focus cohorts:

- `d3-N6-medA`
- `d3-5-hmdC`
- `8-oxo-Guo`
- `8-oxodG`

The comparison should distinguish:

- resolver differences
- workbook-truth differences
- domain-truth interpretation for targets like `8-oxo-Guo`

**Verification:**
- `uv run python scripts\compare_resolvers.py --base-dir .`
- regenerate workbook and compare against `output/xic_results_20260420_0309.xlsx`

### Task 7: Only then continue RT-rule simplification

**Files:**
- Later follow-up only

**Goal:**
Do not touch these until Tasks 1-6 are stable:

- paired `strict_preferred_rt=True`
- target `NL anchor` dependence on paired ISTD RT
- anchor-centered extraction-window width

Reason: those controls are easier to evaluate once the resolver no longer
deletes plausible candidates too early.

---

## Acceptance Gate

Do not switch `local_minimum` to default until all of the following are true:

- no unexpected ISTD catastrophe remains in the tissue batch
- the previously recovered ISTD rows stay recovered without fragile special
  casing
- focus targets are at least as explainable as the trusted workbook
- row-level confidence/reason feels more truthful, not more mysterious
- the branch behavior can be explained as a generic rule set rather than a pile
  of one-off escapes

---

## Risks

1. **Over-softening risk**
   - If the resolver keeps too many bad regions, candidate inventory may become
     noisy and move the problem downstream.
   - Mitigation: attach explicit quality metadata and keep scoring penalties
     strong.

2. **Hidden coupling risk**
   - Temporary extractor recoveries may mask whether the generic resolver is
     actually working.
   - Mitigation: freeze current behavior in tests, then re-evaluate recoveries
     explicitly in Task 5.

3. **Truth-source ambiguity**
   - `output/xic_results_20260420_0309.xlsx` is a trusted reference, but some
     target-specific domain truth is even stricter than that workbook.
   - Mitigation: treat workbook compare and domain review as separate layers.

4. **Premature RT-path edits**
   - If paired RT logic is simplified before resolver hard gates are fixed, the
     root cause of improvements or regressions becomes impossible to isolate.
   - Mitigation: delay RT-rule simplification until after candidate-softening.

---

## Bottom Line

The migration direction is still correct:

- keep `local_minimum`
- keep two-mode validation
- keep workbook-truth comparison

But the next generic step is now clearly:

**stop using local-minimum region-shape checks as early existence gates, emit
candidate-quality metadata instead, and let selection/scoring make the harder
judgment.**
