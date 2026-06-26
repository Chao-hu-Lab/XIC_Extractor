# Selected Full-Envelope Quantitation Boundary Spec

**Date:** 2026-06-03
**Status:** Draft v0.4 - selected-full-envelope remains externalized;
`ChromPeakSegment` is the scoped product-candidate pivot
**Readiness label:** selected-full-envelope `diagnostic_only`;
`chrom_peak_segment` candidate slice `production_candidate`
**Related specs:** [AsLS primary matrix value policy](retired-provenance:66796b0ff1ab), [Region-boundary decision owner design](retired-provenance:44f1b5db924b), [Region-boundary public behavior addendum](2026-06-02-region-boundary-public-behavior-addendum.md), [Mature package flow reference](retired-provenance:ebcb7b73c424)

## Verdict

Final quantitative area should be computed over the selected peak's complete
baseline-supported envelope, not over the narrow discovery/resolver interval
when that interval clips real peak flanks.

2026-06-04 update: the selected-full-envelope policy is no longer the product
boundary owner. It remains diagnostic/review evidence. The active product
candidate direction is now:

```text
raw XIC / AsLS context
  -> Gaussian15 morphology evidence
  -> ChromPeakSegment candidates
  -> evidence/model selection of the segment
  -> raw/original XIC integration over selected segment bounds
  -> AsLS baseline correction
```

The first scoped wiring is intentionally narrow: scored `region_first_safe_merge`
extraction can add `chrom_peak_segment` candidates, while unscored resolver
behavior and direct `find_peak_candidates()` compatibility remain unchanged.
This is `production_candidate`, not `production_ready`.

This does not authorize integrating every positive residual in the broader RT
context. The product target is:

```text
selected peak apex / hypothesis
  -> bounded selected-peak envelope
  -> raw/original XIC area
  -> AsLS baseline correction
  -> selected IntegrationResult
```

Savitzky-Golay, CWT, local-minimum, derivative, WIS, and shape/SN signals are
boundary or model-selection evidence. They may propose, corroborate, or
contradict an envelope, but no single evidence family silently becomes final
integration authority.

The first implementation slice is not production-ready until it proves, with
manual or plot-backed row-level evidence, that the full-envelope boundary fixes
flank clipping without over-merging neighboring peaks, shoulders, tailing,
carryover, or noise.

## Why This Spec Exists

The AsLS primary matrix policy retired raw/linear-edge area as the product value
source. The current MS1 morphology policy goes further: when typed morphology
facts exist, user-facing and final matrix area prefer Gaussian15-smoothed
positive AsLS residual area. Boundary selection still matters because selected
integrations can inherit an overly narrow resolver `peak_start` / `peak_end`.

That leaves one product gap:

```text
Gaussian15 morphology area/shape is the active endpoint,
but the RT segment fed into integration may be too narrow.
```

For normal single peaks, the desired quantitation behavior is to integrate the
whole selected chromatographic envelope above baseline. If the resolver boundary
cuts the left or right flank, AsLS cannot recover the missing area because the
missing scans were never included in the integration interval.

The fix is a boundary-owner change, not another baseline tweak.

## External Method Support

The external literature and mature tools support a layered approach. The
primary product direction for this spec is OpenMS-style separation of mass
trace, smoothed elution-peak morphology, explicit peak boundaries, and raw
trace integration. Other tools and papers are supporting references used to
sharpen specific failure modes, not independent product authorities:

- Skyline uses derivative and Savitzky-Golay evidence to place automatic peak
  boundaries, but calculates peak area from raw/interpolated unsmoothed
  chromatogram points within those boundaries and subtracts background.
  Source: <https://skyline.ms/home/software/Skyline/wiki-page.view?name=tip_peak_calc>
- OpenMS `ElutionPeakDetection` extracts chromatographic peaks from mass traces
  by first smoothing the mass trace, then using local minima/maxima, expected
  peak width, and S/N concepts to split elution peaks. This is the closest
  architectural match for this product direction: smoothing is morphology
  evidence, not final area data. Source:
  <https://openms.de/documentation/classOpenMS_1_1ElutionPeakDetection.html>
- Rupprecht et al. describe automated LC-MS/MS quantification with CWT,
  smoothing, second-derivative evidence, boundary widening/correction, and
  AUC over the chromatographic data constrained to the corrected peak bounds
  after baseline/slope subtraction. The method is validated against expert
  manual quantification. Source: <https://ar5iv.org/pdf/2101.08841>
- XCMS/centWave uses CWT to locate chromatographic peaks at different scales
  and reports original integrated intensity plus baseline-corrected integrated
  intensity over peak RT bounds. Source:
  <https://sneumann.github.io/xcms/reference/findPeaks.centWave-methods.html>
  and <https://www.bioconductor.org/packages/release/bioc/manuals/xcms/man/xcms.pdf>
- OpenMS/OpenSWATH separates peak picking, boundary selection, peak integration,
  and background subtraction. Its workflow can integrate original chromatogram
  data, and `PeakIntegrator` computes area/background from explicit left/right
  boundaries. Sources:
  <https://www.openms.org/doxygen/release/3.0.0/html/UTILS_OpenSwathWorkflow.html>
  and <https://www.openms.org/doxygen/release/3.0.0/html/classOpenMS_1_1PeakIntegrator.html>
- MZmine local-minimum resolver is useful for shoulder splitting in clean peak
  shapes, but its documentation warns that overly narrow search ranges can cut
  off peak edges. This supports demoting resolver intervals to proposal
  evidence when final quantitation needs the full envelope. Source:
  <https://mzmine.github.io/mzmine_documentation/module_docs/featdet_resolver_local_minimum/local-minimum-resolver.html>
- CPC uses smoothed EICs, derivative/inflection evidence, baseline expansion,
  and then separate valley/shoulder handling for co-eluting clusters. This
  supports a boundary policy that expands the selected peak envelope before
  classifying true splits, instead of treating the first raw local valley as
  final. Source:
  <https://mdpi-res.com/d_attachment/metabolites/metabolites-12-00137/article_deploy/metabolites-12-00137-v2.pdf>
- PeakClimber documents why valley-to-valley integration can undercount
  overlapping chromatographic tails. This supports treating local minima as
  split evidence only, with model fitting deferred to a later research slice for
  genuinely overlapping peaks. Source:
  <https://atiredvegan.github.io/files/publications/PeakClimber.pdf>
- El-MAVEN exposes EIC smoothing, baseline calculation, and multiple
  quantitation types. This supports keeping smoothing/baseline/area roles
  explicit instead of collapsing them into one hidden score. Sources:
  <https://elmaven.readthedocs.io/en/documentation-website/IntroductiontoElMAVENUI.html>
  and <https://elmaven.readthedocs.io/en/documentation-website/IntroductiontoElMAVENCLI.html>

The common pattern is not "smooth data and integrate the smoothed peak." It is:

```text
use signal-processing evidence to find the selected peak and its boundary;
integrate raw/original trace within the selected boundary;
subtract a named baseline/background model;
surface ambiguous cases instead of forcing a single hidden authority.
```

## OpenMS-First Boundary Spine

The intended boundary policy is:

```text
selected candidate / PeakHypothesis
  -> raw XIC and AsLS baseline over a named quantitation context
  -> morphology trace for boundary decisions
  -> selected elution-envelope boundary
  -> raw/original XIC integration with AsLS baseline subtraction
```

The morphology trace is a decision trace, not an area trace. Its first
production-candidate calibration should mimic the analyst's Xcalibur review
practice as closely as the repo can support, starting with a `gaussian_15`
window as the named default candidate. Xcalibur's smoothing implementation is
not treated as an open contract; `gaussian_15` is an Xcalibur-like review
surface, not a claim that the repo reproduces the proprietary method exactly.
The implementation may use Savitzky-Golay or another existing local smoother
only if the diagnostic fields name the method, window, and effective point count
used for each row.

The current single-point raw residual stop rule is not sufficient. A boundary is
accepted only after sustained return to baseline, slope/shape flattening, or
equivalent morphology evidence. A one-scan dip below the AsLS residual threshold
inside an otherwise coherent peak must be treated as `internal_dip` evidence and
bridged unless independent split evidence is present.

Local minima, CWT ridges, SavGol shape, derivative/inflection points, WIS,
S/N, and RT all become evidence facts inside this boundary spine. They may
support, contradict, or externalize a boundary decision, but none of them is a
single-source product boundary authority.

## Product Rule

### Selected envelope scope

`selected_full_envelope_boundary` is anchored to one selected peak or
`PeakHypothesis`.

It may expand beyond the selected discovery/resolver interval only inside the
candidate's quantitation context window. It must remain a selected-peak
boundary, not a whole-context positive-residual sum.

The quantitation context is a domain fence, not a writer convenience. Before
promotion, the implementation must name the context owner and record the context
RT start/end used for each evaluated row. The context may be wider than the
resolver interval, but it must not fall back to an unconstrained
`seed_rt +/- max_rt_sec` style search without a named policy and changed-row
gate.

Required inputs:

| Input | Role |
|---|---|
| selected apex RT | Center of the envelope search. |
| selected candidate or hypothesis id | Prevents unrelated context peaks from being integrated. |
| raw/original XIC points | Final area source. |
| AsLS baseline over the quantitation context | Primary baseline/background model. |
| morphology trace such as `gaussian_15` | OpenMS-style elution-envelope and boundary decision source. |
| resolver interval | Starting evidence, not final truth. |
| SG / CWT / local-minimum / derivative / WIS / shape/SN evidence | Boundary proposal and conflict evidence. |

### Area source

Final candidate area is produced by the existing AsLS integration owner over the
accepted selected envelope:

```text
selected_full_envelope_boundary
  -> AsLS IntegrationResult
  -> IntegrationResult.area_baseline_corrected
```

`area_raw_counts_seconds` remains the raw trace integral over the same selected
envelope. Smoothed traces may produce boundary evidence. They may also emit a
shadow smoothed-area comparison for review, but they must not become the final
area data source unless a future spec introduces an explicitly named
smoothed-area product mode.

The low-level AsLS integration implementation may use positive residual clipping
as a baseline-correction detail. That clipping must not be used to expand the
boundary. Boundary expansion is controlled only by the selected-envelope
evidence and stop rules below.

### Stop conditions

Envelope expansion must stop, or mark the row review-only, when it reaches any
of these conditions:

| Condition | Product action |
|---|---|
| sustained return to baseline | Stop envelope at the baseline-supported edge. Single-point return is insufficient. |
| short internal dip without independent split evidence | Bridge the dip and keep expanding the selected envelope. |
| qualified valley before another apex | Stop at valley or emit split/neighbor conflict depending on evidence. |
| neighboring apex has stronger or comparable support | Do not switch apex silently; emit `neighbor_apex_preferred` / review state. |
| shoulder or mixed interval evidence | Emit `split_supported` or `ambiguous_review`; do not auto-swallow both peaks. |
| low-SN tail with no stable baseline return | Stop by tail rule or emit `tail_boundary_uncertain`. |
| carryover, blank-like signal, or unrelated context peak evidence | Do not integrate as selected envelope; emit conflict reason. |
| max width / low scan support / malformed trace | Keep current boundary or mark invalid/review-only. |

The implementation may choose exact numeric thresholds only after calibration.
The contract requires the thresholds to be named, surfaced in audit output,
covered by fixtures, and treated as pre-promotion gates; hidden dead constants
are not acceptable.

### Pre-promotion hard gates

These gates must be defined and audited before `selected_full_envelope` can
write primary matrix values:

| Gate | Required before promotion |
|---|---|
| quantitation context fence | Named owner, RT start/end in diagnostics, and no broad fallback without a policy. |
| morphology trace owner | Named smoothing/morphology method, window, and effective point count in diagnostics. |
| sustained baseline return | Named rule and fixture coverage for clean return and noisy near-return cases. |
| internal dip bridge | Fixture coverage proving short intra-peak dips do not recreate local-minimum under-integration. |
| tail stop | Named rule and changed-row flag for tail uncertainty or tail inflation. |
| max envelope width | Workflow-aware max-width policy and rejection reason when exceeded. |
| neighboring apex / split | Explicit review or split state; no silent apex switch or multi-peak swallowing. |
| carryover / blank-like signal | Conflict reason and no automatic product promotion. |

## Disallowed Interpretations

This spec does not allow:

- returning to `linear_edge` area as a primary product comparator;
- summing all AsLS-positive signal inside the quantitation context;
- using Savitzky-Golay area as the final matrix value;
- treating a single raw residual dip, local minimum, or one-point baseline
  return as final selected-envelope termination;
- treating CWT, local minimum, WIS, RT, shape, or score as a single-source
  product veto or product selector;
- silently promoting wider boundaries for co-eluting or split-supported rows;
- treating a passing 8RAW/85RAW source-contract run as proof of boundary truth.

## Public Surface Contract

### Domain owner

The boundary/envelope decision belongs in `xic_extractor/peak_detection`.

Alignment, workbook, CSV, TSV, and HTML output layers must consume selected
integration results and render audit fields. They must not recompute envelope
boundaries or rescan RAW data.

### Required audit fields

The first diagnostic sidecar is `selected_envelope_diagnostics.tsv`, emitted
with the existing `emit_peak_candidates` audit-output switch. It is an
audit-only selected-envelope comparison surface, not a primary matrix writer.

The implementation may name fields differently, but the product/audit surface
must expose equivalent information:

| Field | Purpose |
|---|---|
| `selected_candidate_id` | The selected candidate or PeakHypothesis identity anchoring the envelope; prevents unrelated context peaks from becoming the integration target. |
| `selected_boundary_mode` | `resolver_interval`, `selected_full_envelope`, `review_only`, or `invalid_trace`. |
| `row_boundary_decision` | Row-level boundary disposition: accept candidate, reject, externalize, or defer. This is not the aggregate promotion gate. |
| `legacy_resolver_provenance` | Historical resolver token such as `region_first_safe_merge` when needed for compatibility/audit; not product authority. |
| `resolver_rt_start/end` | Historical selected resolver interval. |
| `envelope_rt_start/end` | Final selected envelope interval when available. |
| `quantitation_context_rt_start/end` | Domain context fence used for envelope evaluation. |
| `morphology_trace_method` / `morphology_trace_window_points` / `morphology_trace_effective_points` | Named decision trace used for OpenMS-style boundary morphology, such as `gaussian_15`, including the configured window and row-level effective point count. |
| `policy_snapshot` / `resolved_baseline_return_threshold` | The named thresholds actually used for the row, so writers do not need to recompute policy. |
| `boundary_change_class` | no change, flank recovered, internal dip bridged, split supported, neighbor apex, tail uncertain, overmerge rejected, malformed. |
| `boundary_evidence_sources` | SG, CWT, local minimum, derivative, WIS, baseline return, RT, shape/SN as applicable. |
| `boundary_stop_reason` | Machine-readable stop or review reason. |
| `asls_area_old_interval` | Diagnostic area over the old resolver interval. |
| `asls_area_selected_envelope` | Candidate product area over the selected envelope. |
| `area_delta_ratio` | Review prioritization for changed rows. |
| `gaussian15_area_old_interval_shadow` / `gaussian15_area_selected_envelope_shadow` / `gaussian15_area_delta_ratio_shadow` | Diagnostic-only area comparison computed from the Gaussian15-smoothed residual over the same old/envelope intervals. This helps visual review and calibration; it is not a product matrix value. |
| `plot_path` | Overlay plot for changed or high-risk rows. |

The primary matrix may use `asls_area_selected_envelope` only after the
promotion gate passes.

## Validation Gate

### FE0 - Diagnostic characterization

Produce a row-level diagnostic comparing the current resolver boundary against
the selected full-envelope boundary under the same selected peak and AsLS
baseline.

Required outputs:

- old/new RT bounds;
- old/new AsLS area;
- area delta ratio;
- Gaussian15 shadow area and shadow delta ratio;
- selected candidate id and row-level boundary decision;
- resolved policy thresholds;
- flank recovered flag;
- split/neighbor/tail/carryover/noise flags;
- overlay plot for changed and high-risk rows.

### FE1 - Synthetic fixtures

Lock the boundary semantics with targeted fixtures:

- clean single peak with flanks clipped by resolver;
- clean single peak where resolver already matches envelope;
- normal single peak with a short internal dip that local-minimum would cut but
  the morphology trace should bridge;
- deep internal valley with independent split/neighbor evidence that must be
  externalized rather than bridged;
- two resolved neighboring peaks;
- shoulder peak requiring split/review;
- tailing peak with uncertain tail;
- low-SN trace;
- carryover or blank-like context peak;
- low scan support / malformed trace.

### FE2 - Manual / role-aware benchmark oracle

Use manual or expert-reviewed overlay boundaries/areas as the boundary oracle.
The `manual-2raw` suite may be used when its rows match the boundary decision
being tested.

Targeted benchmark subsets may be used as row selectors, role-aware controls,
and calibration inputs, especially for ISTD/STD RT-pair behavior. They are not
boundary truth by themselves, and targeted workbook area must not become a
strict pass/fail comparator.

Compare:

- current resolver interval area;
- selected full-envelope interval area;
- manual or expert-reviewed boundary/area;
- SavGol normal-peak comparator where the row is clean and single-peak.

SavGol's observed normal-peak performance may support envelope calibration, but
it is not a production oracle for complex tissue matrix rows.

### FE3 - 8RAW changed-row review

Run an 8RAW changed-row diagnostic before any 85RAW run.

Acceptance requires:

- changed rows are listed and stratified by reason;
- changed-row denominator is explicit for each status/role stratum;
- high area-decrease rows are explained;
- high area-increase rows have overlay plots;
- false merge / neighbor apex / carryover cases are not promoted silently;
- unresolved blocker counts are machine-readable;
- a gate manifest states `promote`, `no_go`, `externalize`, or `defer`;
- targeted ISTD/STD rows used as benchmarks remain role-aware and do not leak
  target labels into untargeted identity decisions.

Any `no_go` result stops the path before 85RAW. Any `defer` result must name
one bounded follow-up gate that can close the missing evidence.

### FE4 - 85RAW scale gate

Only after FE0-FE3 pass should the behavior enter an 85RAW scale gate.
This gate evaluates whether conditional product wiring is allowed. It does not
itself mutate primary matrix behavior.

85RAW acceptance must report:

- changed-row counts and reason distribution;
- area delta distribution by status/role;
- high-risk stratum coverage and unresolved blocker counts;
- representative plot-backed review rows;
- whether conditional product wiring would change product matrix values from
  `resolver_interval` to `selected_full_envelope`;
- whether any changed rows require policy rollback, review-only externalization,
  or further model-selection evidence.

85RAW closeout must emit a machine-readable final decision:

```text
gate_decision = promote | no_go | externalize | defer
```

`promote` is allowed only when high-risk strata have sufficient reviewed
coverage, promotion-critical changed/high-risk rows have machine-readable
expert-reviewed overlay verdicts, and no area-decrease/area-increase cluster
indicates false merge, tail inflation, carryover absorption, or neighbor-apex
switching.

Overlay plots are review evidence, not boundary oracle by themselves. A domain
waiver may explain why a non-critical row remains acceptable, but it must not
replace the required expert-reviewed boundary verdict for promotion-critical
rows and must not waive false merge, tail inflation, carryover absorption, or
neighbor-apex switching.

Passing FE4 with `gate_decision=promote` authorizes only a separate conditional
product-wiring slice. The behavior becomes `production_candidate` only after
that wiring slice updates product behavior and passes its implementation
closeout. Neither FE4 nor the conditional wiring slice alone proves
`production_ready`.

## Exit Rule

After the first implementation slice, this path must choose one:

| Outcome | Meaning |
|---|---|
| `promote` | Full-envelope boundaries improve clean/normal peaks and changed-row review shows no unacceptable false merge or tail inflation. |
| `no_go` | Kill the product path because the rule mainly creates false merges, noise-tail inflation, target-specific patches, carryover absorption, or neighbor-apex switching. |
| `externalize` | The rule is useful as a diagnostic/review overlay but not safe for primary matrix behavior. |
| `defer` | Allowed only if the missing evidence is named and one bounded follow-up gate can close it. |

Permanent `shadow_only` without an exit rule is not allowed.

## Subagent Review Incorporated

Three xhigh review angles informed this spec:

- `outside-frame-researcher`: external tools and papers support separating
  boundary evidence from raw/original trace area calculation.
- `strategy-challenger`: the direction is correct only as a bounded
  selected-hypothesis envelope; context-wide positive residual integration is a
  product bug.
- `validation-evidence-reviewer`: existing AsLS source-contract validation does
  not prove boundary truth; the next gate must be manual/changed-row/plot-backed.

## Open Decisions

These are implementation decisions, but some are promotion blockers:

- whether FE0 is implemented as a new diagnostic CLI or an extension of an
  existing boundary diagnostic.

Settled implementation detail:

- exact diagnostic TSV column names are the
  `selected_envelope_diagnostics.tsv` headers defined by the required audit
  fields above;
- FE0/FE2 diagnostic sidecar emission is currently implemented as an extension
  of the existing `emit_peak_candidates` audit-output group;
- changed-row and boundary-oracle review queue packaging is implemented by
  `tools/diagnostics/selected_envelope_review_queue.py`, which consumes the
  sidecar and writes review artifacts without running RAW files or mutating
  product outputs.
- the first 8RAW changed-row gate closed as `externalize`, not `promote`;
  candidate envelopes with too few scans or intervals narrower than the resolver
  interval stay diagnostic/review-only, and must not authorize 85RAW scale-up or
  product wiring without a later reviewed 8RAW rerun.
- the current-branch 2026-06-04 FE4 rerun also closed as `externalize`, not
  `promote`. It wrote
  `output/selected_full_envelope_realdata_preflight/fe4_8raw_selected_envelope_current_branch_20260604/`
  with 95 changed rows, 66 accepted flank-recovery rows, and 29 unresolved
  blocker rows across `selected_envelope_narrower_than_resolver`,
  `split_supported_review_required`, and
  `stronger_context_apex_outside_envelope`. This confirms selected-envelope
  boundary remains diagnostic/review-only and must not be wired into product
  matrix behavior yet.
- `ChromPeakSegment` now exists as the replacement product-candidate spine for
  this issue. It is enumerated before model selection, projected as
  `chrom_peak_segment_context`, and uses raw/AsLS area over explicit segment
  bounds. Same-apex resolver candidates upgrade to the segment boundary while
  preserving proposal-source evidence. The 8RAW targeted smoke passed and the
  audit run selected 25 `chrom_peak_segment` rows, but segment-native
  changed-row gating is still missing.

These must be settled before product promotion:

- exact sustained-baseline-return threshold;
- exact morphology smoothing method and window, with `gaussian_15` as the first
  calibrated candidate because it matches the analyst's Xcalibur review habit
  without claiming exact Xcalibur method parity;
- exact internal-dip bridge rule and the evidence that turns a dip into a true
  split instead;
- max envelope width policy by workflow;
- tail-stop rule;
- whether SavGol comparator is fixture-only or also diagnostic output.
- the segment-native gate manifest and plot review that replaces
  selected-full-envelope FE4/FE5 promotion logic.
