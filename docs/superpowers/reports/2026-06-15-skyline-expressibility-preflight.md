# Skyline Expressibility Preflight

Status: `diagnostic_only`

This preflight scopes the first competitive experiment: can Skyline express the
same domain decision that XIC Extractor exports today, without hiding the
decision in an external spreadsheet script?

No RAW processing was launched. No public XIC contract was changed.

## External Baseline

- Skyline is a mature, free, open-source Windows client for targeted
  quantitative mass spectrometry, including small molecule and metabolomics
  workflows:
  <https://pubmed.ncbi.nlm.nih.gov/31984744/>
- The MacCoss Lab describes Skyline as supporting SRM/MRM, PRM, DIA/SWATH, DDA
  with MS1 quantification, small molecules/metabolomics, major vendor formats,
  custom workflows, and external tools:
  <https://maccosslab.org/resources/>
- ProteoWizard provides the data-access layer used by tools including
  `msconvert` and Skyline, with direct vendor raw reading on Windows:
  <https://proteowizard.sourceforge.io/>

This means `.raw` support, targeted quantification, transition lists, peak
review, and internal-standard quantification are not defensible standalone
differentiators.

## Local Inventory

Tool discovery on this workstation did not find `SkylineRunner`, `Skyline`,
`msdial`, `MsdialConsoleApp`, `MZmine`, `Rscript`, or `java` on `PATH`.
Directory search found an installed local MZmine folder:

`<local MZmine portable dir>`

The first Skyline test therefore needs either an installed Skyline path or a
new installation step before any true execution claim.

## XIC Artifacts Used

- `config/targets.example.csv` includes core XIC target fields plus domain
  intent fields: `isotope_label_type`, `paired_rt_relation`, and
  `sample_applicability`.
- `config/targets.csv` currently carries the core target fields:
  m/z, RT window, ppm tolerance, neutral-loss thresholds, `is_istd`, and
  `istd_pair`.
- `config/MixSTDs.csv` includes DNA and RNA target examples, including
  `5-hmdC`, `5-medC`, `8-oxo-Guo`, and their internal standards.
- `local_validation_artifacts/targeted_gt_workbooks/8raw/xic_results_20260512_1151.xlsx`
  has sheets: `Overview`, `Review Queue`, `XIC Results`, `Summary`, `Targets`,
  `Diagnostics`, and `Run Metadata`.

Representative workbook facts:

- `5-medC` can be accepted with strict neutral-loss support and paired
  `d3-5-medC`.
- `d3-5-medC` can be accepted as the internal standard with its own RT and
  area.
- `8-oxo-Guo` can have a measured area but still be exported as
  `VERY_LOW` with reason text:
  `decision: review only, not counted; cap: VERY_LOW due to nl fail`.
- `Diagnostics` records reasons such as selected candidate lacking strict
  neutral-loss match and neutral-loss anchor fallback.

## Expressibility Matrix

| Decision Surface | Skyline Expected Capability | XIC Differentiation Test |
|---|---|---|
| Vendor raw / mzML access | Strong. Skyline and ProteoWizard cover targeted raw-data workflows. | Not a moat. |
| Small-molecule target list | Strong. Skyline supports small-molecule targeted workflows. | Not a moat. |
| ISTD pairing / quantitation | Strong. Skyline supports quantitative workflows with standards and reports. | Not a moat unless paired RT/evidence policy is first-class. |
| Product-ion / neutral-loss transition | Likely expressible as transitions or reportable signal. | The test is whether neutral-loss failure can drive `not counted` authority without custom post-processing. |
| Paired ISTD RT relation | Likely inspectable or reportable, but not proven as a native acceptance policy. | `paired_rt_relation=istd_not_later_than_pair` should be tested as a decision rule, not a visual check. |
| Isotope label type | Likely representable through standards/heavy labels or annotations. | The differentiator is whether label type changes evidence policy, not naming. |
| Sample applicability | Likely possible as annotations or filtering. | Test whether RNA/DNA applicability can suppress or cap target decisions natively. |
| Confidence and reason strings | Skyline has scoring, reports, and manual review; mProphet-style models are not the same as XIC's reason text. | XIC wins if the exported number is coupled to transparent `accepted/review_only/not_counted` reasons. |
| Review queue | Skyline has rich manual review surfaces. | XIC wins only if review queue is domain-specific and action-oriented beyond generic manual curation. |
| Audit trail / run metadata | Skyline has document/report history surfaces, but exact parity is unverified. | XIC must preserve reproducible rule decisions, target health, and schema-stable export reasons. |

## Minimal Skyline Experiment

Prepared inputs:

- Skyline candidate transition list:
  `docs/superpowers/reports/2026-06-15-skyline-three-pair-transition-list.csv`
- XIC decision oracle:
  `docs/superpowers/reports/2026-06-15-xic-skyline-expressibility-oracle.csv`
- Same-sample mzML manifest for first expressibility run:
  `docs/superpowers/reports/2026-06-15-skyline-8raw-mzml-manifest.csv`
- Execution runbook:
  `docs/superpowers/reports/2026-06-15-skyline-expressibility-runbook.md`
- Single-sample smoke result:
  `docs/superpowers/reports/2026-06-15-skyline-single-sample-smoke.md`
- 8-sample mzML smoke result:
  `docs/superpowers/reports/2026-06-15-skyline-8sample-smoke.md`

Use three target pairs:

1. Positive control: `5-medC` / `d3-5-medC`
2. Positive control: `5-hmdC` / `d3-5-hmdC`
3. Negative/review control: `8-oxo-Guo` / `[13C,15N2]-8-oxo-Guo`

Acceptance criteria:

1. Skyline can import the targets and raw files and export RT/area for the
   target and ISTD pairs.
2. Skyline can represent neutral-loss evidence for each target in a reusable
   method, not only by visual inspection.
3. Skyline can reproduce the XIC decision distinction:
   `accepted` versus `review only, not counted`.
4. Skyline can preserve the reason for the distinction in an exportable review
   surface without a custom downstream script.

Interpretation:

- Full pass: Skyline natively reproduces target area, ISTD context,
  neutral-loss decision, confidence class, review-only status, and reason text.
- Partial pass: Skyline extracts comparable quantitation but needs custom
  reports/scripts to reproduce XIC's decision authority.
- Fail: Skyline can quantify the chromatograms but cannot encode the domain
  evidence policy that decides whether a value is counted.

## Current Verdict

The first defensible claim is not "XIC extracts better peaks than Skyline."

The first defensible claim to test is:

> XIC Extractor turns nucleoside/adduct-specific evidence rules into auditable
> quantitation authority, while mature tools may require external scripting or
> manual interpretation to reproduce the same `counted` versus `review-only`
> decision.

This remains `diagnostic_only`. Skyline has now been located and run from the
official Unplugged package for one-sample and 8-sample mzML smokes. The
RAW-backed fidelity test remains open, and the current mzML/product-transition
run is not a peak-area parity benchmark.
