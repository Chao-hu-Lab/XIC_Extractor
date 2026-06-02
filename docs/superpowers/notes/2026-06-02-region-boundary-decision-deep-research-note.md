# Region-Boundary Decision Deep Research Note

**Date:** 2026-06-02
**Status:** Draft v0.1 - external design input
**Readiness label:** `diagnostic_only`
**Related spec:** [Region-boundary decision owner design](../specs/2026-06-02-region-boundary-decision-owner-design.md)

## Verdict

Mature LC-MS tools do not support treating `legacy_savgol`,
`local_minimum`, `region_first_safe_merge`, CWT, or a baseline-return rule as
the final product authority by itself.

The better direction for XIC Extractor is:

```text
proposal sources
  -> selected peak hypothesis / evidence chain
  -> explicit boundary + baseline integration
  -> audit trail and changed-row validation
```

This confirms the current RB0/RB1 direction. Keep product behavior stable first,
characterize current boundary decisions, and introduce one typed region-decision
projection before promoting any new boundary behavior.

The OpenMS-style architecture is closest to the desired long-term shape, but it
should be adapted rather than copied: mass-trace / elution-peak / feature
hypothesis thinking maps well to `Trace`, `PeakHypothesis`, `EvidenceVector`,
`IntegrationResult`, and `AuditTrail`. MZmine-style resolvers and XCMS/centWave
remain useful as candidate and morphology evidence sources.

## Sources

| Source | What it contributes to this decision |
|---|---|
| [MZmine Local Minimum Resolver](https://mzmine.github.io/mzmine_documentation/module_docs/featdet_resolver_local_minimum/local-minimum-resolver.html) | Local minima split overlapping or shoulder EIC features after chromatogram building; the docs explicitly frame it as suitable for low-noise traces with good peak shapes. |
| [MZmine Chromatogram Builder](https://mzmine.github.io/mzmine_documentation/module_docs/lc-ms_featdet/featdet_adap_chromatogram_builder/adap-chromatogram-builder.html) | EIC construction and resolving are separate stages; built EICs can be resolved by different deconvolution algorithms. |
| [MZmine CentWave Resolver](https://mzmine.github.io/mzmine_documentation/module_docs/featdet_resolver_centwave/centwave-resolver.html) | Wavelet response across scales can locate candidate features and infer width, then reconstruct from the original chromatogram. |
| [MZmine ADAP Resolver](https://mzmine.github.io/mzmine_documentation/module_docs/featdet_resolver_adap/adap-resolver.html) | CWT ridgelines and local-minimum boundary logic can coexist; CWT is not just a weak support label. |
| [MZmine Baseline Resolver](https://mzmine.github.io/mzmine_documentation/module_docs/featdet_resolver_baseline/baseline-resolver.html) | Simple baseline cutoff is a didactic/simple resolver, not evidence that baseline cutoff should own final integration. |
| [MZmine Gap Filling / Peak Finder](https://mzmine.github.io/mzmine_documentation/module_docs/gapfill_peak_finder/gap-filling.html) | Mature workflows revisit raw data in expected m/z and RT windows, select candidate segments, and mark filled features as estimated. |
| [OpenMS FeatureFinderMetabo](https://openms.org/documentation/html/TOPP_FeatureFinderMetabo.html) | Mass traces are assembled into metabolite features, with detailed feature metadata preserved for inspection. |
| [OpenMS FeatureFindingMetabo class](https://www.openms.org/documentation/html/classOpenMS_1_1FeatureFindingMetabo.html) | Mass traces are detected, split into elution peaks, assembled into feature hypotheses, and scored by RT, m/z, isotope, and intensity compatibility. |
| [OpenMS ElutionPeakDetection](https://openms.de/documentation/classOpenMS_1_1ElutionPeakDetection.html) | Elution peaks are extracted from mass traces using smoothing, local extrema, peak-width, and S/N concepts. |
| [OpenMS FeatureFinderMetaboIdent](https://openms.de/documentation/TOPP_FeatureFinderMetaboIdent.html) | Targeted feature detection uses target files, extracted chromatograms, candidate outputs, and optional elution-model fitting. |
| [Kenar et al. 2014, OpenMS metabolite quantification](https://portal.fis.tum.de/en/publications/automated-label-free-quantification-of-metabolites-from-liquid-ch/) | The OpenMS paper frames detection as mass-trace detection plus aggregation into features using m/z spacing, co-elution, and isotope-pattern classification. |
| [XCMS centWave documentation](https://rdrr.io/bioc/xcms/man/findChromPeaks-centWave.html) | centWave uses ROI detection and CWT to locate chromatographic peaks at multiple scales, with settings for S/N, peak width, integration, and Gaussian fitting. |
| [Tautenhahn et al. 2008, centWave](https://pmc.ncbi.nlm.nih.gov/articles/PMC2639432/) | centWave combines ROI detection in m/z with CWT chromatographic resolution, local noise/baseline estimates, boundary localization, and benchmark-style recall/precision evaluation. |
| [Yu and Peng 2010, bi-Gaussian mixture model](https://link.springer.com/article/10.1186/1471-2105-11-559) | Model-based deconvolution can improve asymmetric/overlapping peak quantification, but requires model-selection evidence and is not a small cleanup change. |

## Question 1 - What Should Proposal Sources Return?

Proposal sources should return candidates and evidence facts, not product
decisions.

| Proposal source | Should return | Should not own |
|---|---|---|
| `local_minimum` | valley positions, split candidate regions, edge/top ratio facts, scan-count and width checks | final split authority, final boundary authority |
| `legacy_savgol` | smoothed apex/edge candidates and trace-shape facts for regular peaks | final product default for complex matrix cases |
| `region_first_safe_merge` | a conservative merge candidate over adjacent local-minimum regions plus eligibility/rejection reasons | general model selection or permanent public resolver semantics |
| CWT / wavelet | apex proposals, scale/ridge persistence, possible width and shoulder evidence under named role gates | standalone peak-existence or identity authority |
| half-height / width | morphology descriptors and rough boundary hints | hard rejection without context |
| baseline return / AsLS | baseline-corrected integration state and audit facts | hidden boundary replacement by itself |
| derivative / curvature | inflection, shoulder, or local-shape evidence | opaque score authority |
| model fitting | fitted component hypotheses and residual/model-selection facts | behavior change before changed-row/manual-review oracle exists |

Design implication: RB1 should make these facts typable and reusable. It should
not collapse them into one numeric score.

## Question 2 - Who Owns Split, Merge, Wider Boundary, Or Neighbor Apex?

The owner should be the selected `PeakHypothesis` / region-decision contract,
not a specific resolver implementation.

Mature tools split the workflow:

- MZmine builds EICs, then resolver modules split or reconstruct features.
- OpenMS detects mass traces, splits elution peaks, then assembles compatible
  traces into feature hypotheses.
- XCMS/centWave detects ROI-level candidates and CWT peaks, then reports
  metrics and fitted or integrated peak properties.

For XIC Extractor, this means:

- `select_candidate(...)` remains the current product selector until RB0/RB1
  characterize it.
- `RegionSelectionDecision` or its successor should become the common typed
  projection of split/merge/wider-boundary/neighbor-apex evidence.
- Product promotion still needs an explicit `product_action`, such as
  `no_change`, `safe_merge_eligible`, or `behavior_change_required`.
- CWT, WIS, RT, shape, S/N, MS2/NL, and local minima can support or conflict
  with a hypothesis, but none should silently override the selected peak.

This keeps the future system evidence-first without turning it back into
score-weight tuning.

## Question 3 - How Should Integration Avoid Too-Narrow Or Too-Wide Areas?

The known XIC Extractor failure is not only "wrong peak proposal." It is also
boundary/integration authority being too tied to one resolver's edge behavior.

Near-term decision:

- Keep AsLS as the settled baseline integration contract.
- Do not revive `linear_edge`.
- Treat local-minimum edges as candidate boundaries, not final integration
  truth.
- Use safe merge as an explicitly gated transitional behavior, not the final
  region-decision model.

Longer-term direction:

- selected hypothesis defines the intended peak;
- boundary candidates explain plausible integration ranges;
- baseline integration computes area for the selected range;
- audit trail records rejected ranges and why they were rejected;
- changed-row validation classifies whether the change was false split, false
  merge, wider boundary, neighbor apex, or no-change.

Model fitting, such as asymmetric or mixture models, is a later research slice.
It may help when peaks overlap or tail, but it would be a behavior-changing
promotion and needs its own oracle.

## Question 4 - What Is The Validation Oracle?

The minimum useful oracle is not only aggregate RSD or total area movement. It
has to be row-level and failure-mode-specific.

Recommended oracle stack:

1. Strict RB0/RB1 parity tests for current public outputs.
2. Changed-row TSV for any later behavior-changing region decision.
3. Manual EIC review index for high-risk changed rows.
4. Targeted benchmark rows where ISTD/STD or prior manual review provides a
   strong local truth source.
5. Optional 8RAW validation only after the changed-row schema can explain what
   changed.

Changed rows should be classified at least as:

- `false_split_fixed`
- `false_merge_introduced`
- `wider_boundary_preferred`
- `neighbor_apex_changed`
- `same_apex_area_changed`
- `no_material_change`
- `inconclusive`

This mirrors the mature-tool lesson: candidate generation, deconvolution,
gap-filling, and integration can all change rows for different reasons. The
validation artifact has to preserve that reason, otherwise the cleanup will
hide science risk behind an aggregate score.

## Consequences For The Current Region-Boundary Spec

RB0/RB1 should stay narrow:

- characterize current resolver/output behavior;
- preserve all public TSV/workbook/alignment/config/import contracts;
- introduce or harden one typed internal region-decision projection;
- keep `region_first_safe_merge` as current opt-in behavior;
- do not promote CWT, model fitting, or new boundary selection yet.

RB2 should map region facts into the handoff spine:

- selected boundary -> `IntegrationResult`;
- alternate/rejected boundaries -> `AuditTrail`;
- local-minimum/CWT/WIS/shape/SN provenance -> `EvidenceVector`;
- selected product action -> `PeakHypothesis` or a successor decision record.

RB3/RB4 should remain deferred until there is a changed-row oracle:

- resolver-token retirement or rename;
- CWT named-role promotion;
- model-fitting exploration;
- default behavior change.

## Plain-Language Summary

The endpoint is not "choose Savgol" or "choose local minimum" or "choose safe
merge." The endpoint is:

```text
pick the right peak hypothesis,
show the evidence,
integrate it with the right baseline and boundary,
and make every changed row explainable.
```

`local_minimum`, `legacy_savgol`, `region_first_safe_merge`, and CWT remain
useful, but they should become evidence-producing tools inside one clearer
region-decision system.

## Open Follow-Up

The first behavior-changing slice should likely target false split / too-narrow
boundary cases before neighbor-apex promotion. That directly matches the known
area-underestimation risk and can reuse the existing safe-merge and shadow
evidence. Neighbor-apex and model-fitting changes need a stronger manual-review
oracle before promotion.
