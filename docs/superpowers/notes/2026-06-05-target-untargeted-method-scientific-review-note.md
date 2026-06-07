# Targeted / Untargeted Method Scientific Review

**Date:** 2026-06-05
**Branch:** `codex/cleanup-retirement-foundation`
**Status:** Investigation / discussion input — **no decision, no code change.** A mass-spectrometrist's read of the raw→matrix science, intended as input for a product-direction conversation with Codex.
**Method:** 4 parallel read-only explorer agents mapping the targeted path, the untargeted/alignment path, the evidence chain, and diagnostic adoption — followed by (a) literature / mature-tool comparison (OpenMS, MZmine, Eilers AsLS, Thermo Genesis/ICIS, NL-scanning lipidomics) done directly, and (b) direct verification of the single most damning agent claim (see Correction below).

## Verdict

The **backbone is mainstream and defensible.** Every major choice — resolver, baseline,
neutral-loss identity, RT alignment, gap-fill, cross-sample grouping — maps to an
established method in OpenMS / MZmine / the primary literature (table below). The
problems are **not in method selection.** They are in four places:

1. A non-standard **integration definition** (integrating the smoothed residual as the
   reported area, vs the standard "smooth to find boundaries, integrate raw").
2. **Backfill** that fills "not detected" with "any peak in a wide window" — a recognized
   but double-edged practice for quantitation.
3. **Evidence-chain wiring** issues (a statistically invalid paired-ratio gate; a
   suspected triple-count of one ISTD anchor; uncalibrated thresholds).
4. **Diagnostic adoption:** ~75% of the diagnostic evidence the product computes never
   feeds back into a product decision.

## Correction to the agent sweep (verified directly)

One agent flagged the `ms1_peak_group_*` / `outside_ms1_peak_group_*` strict-NL scan
counts as **decorative evidence** ("computed but never read; NL inside vs outside the
peak group treated identically"). **This is wrong** and is corrected here.

`neutral_loss.py:251-293` shows that when a valid `ms1_peak_group` scope exists, the
`inside_region` used to compute the **primary** `strict_nl_scan_count` / `nl_match` **is
the peak-group window**, and that primary value is what flows into
`ScoringContext.strict_nl_scan_count` / `nl_match` (`scoring_factory.py:206-218`) and
drives the decision. The recent commit `feat: scope MS2 NL evidence to Gaussian15 peak
groups` folded the spatial attribution **into the primary metric.** The separate
`ms1_peak_group_*` / `outside_*` fields are **redundant diagnostic mirrors** (output /
audit only), not discarded decision evidence. This is good scientific direction and
should be credited, not flagged. (It also argues for skepticism toward the other
"decorative / double-count" claims below — see Verification status.)

---

## Pipeline backbone vs mature tools — these are sound

| Stage | XIC_Extractor | Mature-tool / literature analog | Verdict |
|---|---|---|---|
| Peak resolver | `local_minimum` / `legacy_savgol` / `region_first_safe_merge` (incl. CWT) | MZmine resolvers: Local minimum, Savitzky-Golay, ADAP (CWT) — near 1:1 | ✅ mainstream |
| Baseline | AsLS `lam=1e5`, `p=0.01` (`baseline.py:17-19`) | Eilers & Boelens AsLS; λ commonly 10²–10⁹, p 0.001–0.1 → params in-range | ✅ standard |
| NL identity | neutral-loss tag → compound class | DDA-driven neutral-loss scanning (Schwudke 2006); PC 184 headgroup — lipidomics standard | ✅ literature-backed |
| RT alignment | anchor-based + drift-aware + piecewise/affine | OpenMS pose-clustering; MZmine RANSAC (non-linear); ISTD-anchor ≈ identification-based alignment | ✅ reasonable / robust |
| Gap-fill backfill | find a peak in the expected RT window and fill | MZmine "Peak Finder" gap-filler (return to raw, find local max) — same concept | ✅ concept mainstream (caveat below) |
| Cross-sample grouping | complete-link + hard gates | complete-link resists the chaining that single-link suffers — conservative, correct | ✅ sound |
| MS2 NL scoped to peak group | primary strict-NL uses the peak-group window | correct attribution of fragments to the right MS1 peak | ✅ recent, right direction |

---

## Scientifically questionable steps (raw → matrix)

### S1. Integration definition is non-standard and inconsistent  *(highest)*

Standard practice (Thermo Genesis included) is **smooth to detect boundaries, then
integrate the raw signal between them.** Here `reported_peak_area` (`extractor.py:108-115`)
prefers `area_ms1_morphology`, which **integrates the Gaussian-smoothed positive
residual** (`ms1_morphology.py:55` clips negative residual to 0) — i.e. the smoothed
trace itself becomes the measured value. Two consequences:

- Clipping negatives systematically under-integrates peak shoulders that dip below the
  AsLS baseline estimate.
- `DEFAULT_GAUSSIAN15_WINDOW_POINTS = 15` is a fixed point count, **not scaled to scan
  rate**; at different acquisition rates 15 points spans a different time width, so the
  value drifts systematically across batches.

Both `area_ms1_morphology` and `area_raw_counts_seconds` are computed
(`hypotheses.py`), but only one is reported — and `model_selection` compares both — so
the product carries two area definitions in different places. (This connects to the
prior dual-system note; here the concern is purely scientific.)

### S2. Backfill assumes "not detected = present-but-missed", risking interference fill  *(untargeted, highest)*

`owner_backfill.py` uses `strict_preferred_rt=False` over a 3-min window
(`max_rt_sec=180s`) and fills any detected peak as `status="rescued"`. MZmine's
gap-filler does the same in spirit, but in metabolomics this is a **recognized
double-edged practice**: for high-missingness contrasts (e.g. tumor/normal differential
compounds), a truly-absent analyte gets filled with a neighbouring interferent's area,
**shrinking the group difference and reducing statistical power.** MZmine at least marks
gap-filled cells grey. Needs: confirm rescued values are flagged downstream, and a
spike-out false-positive-rate measurement.

### S3. Pre-backfill consolidation merges identities across a 3-min RT window  *(untargeted)*

`pre_backfill_consolidation.py` (`identity_rt_candidate_window_sec=180s`) can merge two
feature families up to 3 min apart into one identity row, guarded only by "disjoint
sample sets". On HILIC, 3 min usually spans several compounds — a **false-identity-row
risk**. The merged row then drives backfill at up to two seed centers, widening the
mis-attribution.

---

## Evidence-chain assessment

(First: the `ms1_peak_group` "decorative" claim is **withdrawn** — see Correction.)

### E1. `paired_area_ratio` gate uses a leave-one-out min/max range, not a statistical tolerance  *(highest evidence concern; agent-traced, not personally re-verified)*

`paired_area_ratio_projection.py:173-178` accepts an observed ratio if it falls inside
the **min–max** of the other samples. This is statistically backwards: **fewer samples →
narrower band, more samples → wider band**, the opposite of confidence scaling; and with
`MIN_..._POINTS=3`, a 3-point min–max is highly unstable. This gate **directly decides
whether an NL-dropout peak is promoted to `counted_detection`** — i.e. it changes the
final matrix. Recommend a MAD-based or mean±k·SD tolerance instead.

### E2. Suspected triple-count of a single ISTD anchor  *(agent-traced, NOT personally verified)*

Agent reported that one ISTD anchor RT may feed `rt_prior_close` (+15),
`paired_istd_aligned` (+20), and `paired_istd_rt_close` (a support reason), all from the
same physical observation (`scoring_factory.py:110-116`, `evidence_facts.py:230-243`).
If true, one observation is counted in both the additive score and the support-reason
count. **Flagged as needs-confirmation**, not asserted.

### E3. Uncalibrated thresholds  *(agent-traced)*

S/N hard=2.0 / soft=3.0 (`evidence_facts.py:588-590`; LC-MS convention is LOQ S/N≥10,
detection≥3 — 2.0 is loose), jaggedness 0.3/0.5, symmetry hard (0.3, 3.0), rt_centrality
1%/10%. Not necessarily wrong, but **none is calibrated against ground truth** — they
read as sensible hand-tuned numbers.

---

## Literature analogs — and the two places with none

Most choices have a clear analog (table above). The two without a good mature-tool /
literature analog — the ones worth discussing:

- **Integrating the Gaussian-smoothed positive residual as the reported area** (S1).
  Mature tools smooth-to-detect, integrate-raw. This is bespoke; it needs spike-in
  evidence that it beats raw trapezoid on recovery linearity, or it should revert to a
  standard integrator.
- **Using strict-NL scan *count* as graded evidence.** The literature uses NL
  presence/absence for identity (qualitative). Scan *count* is governed by DDA duty
  cycle / Top-N — an **instrument parameter, not a chemical signal.** Using `count==0` as
  a "DDA dropout" criterion (`result_assembly.py` ISTD downgrade) risks treating
  instrument happenstance as chemical evidence.

---

## Diagnostic adoption — ~75% never feeds a decision

Rough split of emitted diagnostic / sidecar artifacts:

| Class | Meaning | Share |
|---|---|---|
| A | Read back by product code, changes matrix / detection / selection | ~25% |
| B | Human-review only (phase gates, benchmarks, audit trails) | ~50% |
| C | Orphan / write-only, no reader at all | ~25% |

- **The "shadow" region selection gates only 1 of its 4 verdicts.**
  `safe_merge_eligible` has an in-memory gate that edits peak boundaries
  (`region_safe_merge.py`); but `behavior_change_required`, `wider_boundary_preferred`,
  `neighbor_apex_preferred`, `split_supported` are **computed, written to TSV, and read
  by nothing.** The product recognizes "this boundary is wrong" and takes no action.
- **`area_integration_uncertainty` outputs are fully orphan** — the name implies a gate,
  but no `xic_extractor` code reads them.
- **`target_pair_rt_auto_reselection`** has a designed cross-run closed loop
  (propose → human approval → registry → next run changes selection), but it is currently
  held by `phase_2_product_switch_blocked`, so most proposals are de-facto "record only".

Opinion: for a research tool, much of B is legitimately human-facing. But if the
region-selection verdicts and area-uncertainty audit were *meant* to influence peak
picking, that investment has not been cashed in.

---

## MS-scientist priorities — all settle with existing data, no intent debate needed

1. **Pick one integration definition (S1):** spike-in concentration series, compare
   recovery linearity (R², residuals) of `area_ms1_morphology` vs
   `area_raw_counts_seconds`; let the data choose the reported area.
2. **Backfill false-positive rate (S2):** spike-out (known-absent) samples; measure
   rescued false-positive rate and filled-area CV — the crux of untargeted quant trust.
3. **Statistical paired-ratio tolerance (E1):** replace min–max with MAD-based band,
   because it directly gates counted detection.
4. **Diagnostic adoption decision:** decide whether the 3 unused region-selection
   verdicts and area-uncertainty are promoted to gates or explicitly demoted to review —
   stop the half-wired state.

## Verification status

| ID | Claim | Verification |
|----|-------|--------------|
| Correction | `ms1_peak_group` NL counts are decorative | **Refuted by me** — `neutral_loss.py:251-293`, `scoring_factory.py:206-218`; scoping IS adopted |
| Backbone table | resolver/baseline/NL/alignment/gap-fill analogs | my literature comparison (sources below) |
| S1 | smoothed-residual-as-area, fixed 15-pt window | code-path verified prior round + agent-traced |
| S2 / S3 | backfill window / 180s consolidation | agent-traced with file:line; not personally re-read this round |
| E1 | paired-ratio min/max gate | agent-traced; **not personally re-verified** |
| E2 | ISTD anchor triple-count | agent-traced; **not personally verified — needs confirmation** |
| E3 | uncalibrated thresholds | agent-traced file:line |
| Adoption | ~25/50/25 A/B/C split | agent-traced reader/writer map |

## Sources

- MZmine resolvers: [Local minimum](https://mzmine.github.io/mzmine_documentation/module_docs/featdet_resolver_local_minimum/local-minimum-resolver.html), [ADAP/CWT](https://mzmine.github.io/mzmine_documentation/module_docs/featdet_resolver_adap/adap-resolver.html)
- MZmine gap-filling: [Peak finder](https://mzmine.github.io/mzmine_documentation/module_docs/gapfill_peak_finder/gap-filling.html), [Same m/z & RT range](https://mzmine.github.io/mzmine_documentation/module_docs/gapfill_same_mz_and_RT_range/same_mz_and_RT_range_gap_filler.html)
- [Eilers & Boelens, AsLS baseline correction (2005)](https://prod-dcd-datasets-public-files-eu-west-1.s3.eu-west-1.amazonaws.com/dd7c1919-302c-4ba0-8f88-8aa61e86bb9d)
- [OpenMS MapAlignerPoseClustering](https://abibuilder.cs.uni-tuebingen.de/archive/openms/Documentation/nightly/html/TOPP_MapAlignerPoseClustering.html); [MZmine 2 (RANSAC / Join aligner), BMC Bioinformatics 2010](https://link.springer.com/article/10.1186/1471-2105-11-395)
- [Thermo Xcalibur Genesis/ICIS integration (TraceFinder)](https://mytracefinder.com/2012/04/25/peak-integration-algorithms-hmmmm-which-one-to-use/)
- [Schwudke et al., DDA-driven neutral-loss scanning, Anal. Chem. 2006](https://pubs.acs.org/doi/10.1021/ac051605m); [LC-MS metabolomics identification confidence levels](https://www.metwarebio.com/lc-ms-metabolomics-metabolite-identification-confidence-levels/)

## Key files

- `xic_extractor/extractor.py:108-115` — reported_peak_area dual definition (S1)
- `xic_extractor/peak_detection/ms1_morphology.py:55` — positive-residual clip, fixed 15-pt window (S1)
- `xic_extractor/peak_detection/baseline.py:17-19` — AsLS params
- `xic_extractor/neutral_loss.py:251-293` — NL primary scope = peak group (Correction)
- `xic_extractor/extraction/scoring_factory.py:150-239` — evidence assembly into ScoringContext
- `xic_extractor/alignment/owner_backfill.py` — gap-fill, strict_preferred_rt=False (S2)
- `xic_extractor/alignment/pre_backfill_consolidation.py` — 180s identity merge (S3)
- `xic_extractor/extraction/paired_area_ratio_projection.py:173-178` — min/max gate (E1)
- `xic_extractor/peak_detection/region_model_selection.py` + `region_safe_merge.py` — shadow verdicts, 1 of 4 gated (Adoption)
- `tools/diagnostics/area_integration_uncertainty_audit.py` — orphan diagnostic (Adoption)
