# XIC Extractor vs Mature LC-MS Tools Differentiation Report

Status: `diagnostic_only`

Date: 2026-06-15

## Bottom Line

XIC Extractor 不應定位成通用 LC-MS preprocessing / peak-picking / alignment
平台。這條路已經被 Skyline、MS-DIAL、MZmine、XCMS 佔得很深，而且它們在
成熟度、格式支援、社群、批次處理、方法文件上都明顯更強。

XIC Extractor 真正有防守力的定位是：

> An assay-specific LC-MS evidence adjudication and auditable quantitation layer
> for nucleoside/nucleotide DNA/RNA adduct workflows.

換句話說，它的價值不是「我也能抽 XIC、做 baseline、做 alignment、算 ISTD」。
這些都是 commodity。它的價值是把 domain-specific evidence 轉成可審閱、
可稽核、可明確區分 measured signal 與 counted detection 的產品決策。

## What Was Actually Run

### Skyline

- Installed from official Skyline Unplugged 64-bit package.
- Executable:
  `output/external_tools/skyline/Skyline-64_25_1_0_237/Skyline-64_25_1_0_237/Application Files/Skyline_25_1_0_237/SkylineCmd.exe`
- Version observed:
  `Skyline (64-bit) 25.1.0.237 (519d29babc)`
- Ran an 8-sample mzML targeted small-molecule transition-list probe for:
  `5-hmdC`, `5-medC`, `8-oxo-Guo` plus heavy standards.
- Outputs:
  - `output/skyline_expressibility_20260615/molecule_transition_results_8sample.tsv`
  - `output/skyline_expressibility_20260615/molecule_ratio_results_8sample.tsv`
  - `output/skyline_expressibility_20260615/molecule_rt_results_8sample.tsv`
  - `docs/superpowers/reports/2026-06-15-skyline-8sample-smoke.md`

Result: Skyline is a serious comparator. It supports small-molecule targeted
quantification, stable-isotope internal standards, raw-data import, peak
integration, calibration/ratio workflows, and report export. In this bounded run,
it exported quantitative peak evidence but did not natively emit XIC-equivalent
`Product State`, `Counted Detection`, or reason strings.

### MZmine

- Existing portable installation:
  `<local MZmine portable>/mzmine_console.exe`
- Version observed in console log:
  `mzmine 4.9.14`
- Ran an existing CTDNA batch workflow through `mzmine_console.exe` with output
  redirected into this repo.
- Command output completed 12 batch steps:
  import, mass detection, chromatogram builder, local minimum resolver,
  RT correction, isotope grouper, duplicate filtering, join aligner, gap filling,
  legacy CSV export.
- Output:
  `output/mature_tools/mzmine_ctdna_probe/ctdna_probe_quant_mzmine.csv`
- Observed output shape:
  19,316 rows, 16 columns. Columns are feature-level row ID, row m/z,
  row retention time, and per-file peak area columns.

Result: MZmine is a mature feature table engine. It can process batch mzML data
and produce aligned area matrices. Its native output surface is feature-centric,
not target-decision-centric.

### MS-DIAL

- Downloaded latest GitHub release console package:
  `MSDIAL.console.v5.5.260323-windows-net48.zip`
- Extracted executable:
  `output/external_tools/msdial/MSDIAL.console.v5.5.260323-windows-net48/MSDIALCUI.exe`
- Version/help observed:
  `Msdial Console App Version 5.5.260323`
- CLI requires:
  `MSDIALCUI.exe <analysisType> -i <input folder> -o <output folder> -m <method file> -p`
- Official demo ZIP was checked but not downloaded because it is
  `970,712,749` bytes. This probe therefore stops at install + CLI help gate,
  not full demo processing.

Result: MS-DIAL is a strong untargeted metabolomics/lipidomics workbench with
vendor and mzML support, deconvolution, peak identification, alignment, library
search, normalization, and console automation. The bounded local probe does not
claim numerical output, but the official CLI and package are present and runnable.

### XCMS

- Local R found at:
  `C:/Program Files/R/R-4.5.3/bin/Rscript.exe`
- Installed via Bioconductor into user library:
  `<local R user library>/4.5`
- Installed package versions observed:
  `xcms 4.8.0`, `MSnbase 2.36.0`, `mzR 2.44.0`, `MsExperiment 1.12.0`,
  `Spectra 1.20.1`
- Probe script:
  `docs/superpowers/reports/2026-06-15-xcms-centwave-probe.R`
- Ran 2 CTDNA mzML files with RT filter `0-600` seconds and:
  `CentWaveParam(ppm=10, peakwidth=c(5, 60), prefilter=c(3, 10000), noise=10000)`
- Output:
  `output/mature_tools/xcms_probe/xcms_centwave_2sample_peaks.csv`
- Observed output:
  2,682 chromatographic peak rows.
- Output columns:
  `mz`, `mzmin`, `mzmax`, `rt`, `rtmin`, `rtmax`, `into`, `intb`, `maxo`,
  `sn`, `sample`.

Result: XCMS is a mature, scriptable R/Bioconductor preprocessing framework.
Its native surface is chromatographic peak detection and feature abundance, not
assay-specific target adjudication.

## Capability Matrix

| Dimension | XIC Extractor | Skyline | MS-DIAL | MZmine | XCMS |
|---|---|---|---|---|---|
| Input format | Thermo RAW-first product scope; mzML only external/reference context | Strong vendor/raw and mzML support | Vendor formats plus mzML/netCDF/ABF depending workflow | mzML plus multiple vendor formats; portable batch mode confirmed | mzML/mzXML/CDF/NetCDF style preprocessing |
| Usage mode | Targeted, domain-specific extraction and workbook review | Targeted quantification/method development | Untargeted metabolomics/lipidomics workbench | Modular GUI/batch feature detection and annotation | R/Bioconductor scripted preprocessing |
| Peak detection/integration | Good enough for scoped assay, but not unique | Mature targeted peak integration | Mature peak detection/deconvolution/alignment | Mature modular feature detection/alignment/gap fill | Mature centWave/CWT-style peak detection |
| ISTD quantitation | Domain-linked paired ISTD evidence and workbook projection | Strong stable-isotope internal standard and ratio workflows | Internal-standard/QC normalization workflows | Standard-compound/intensity normalization modules | Possible downstream, not native target adjudication |
| MS2/NL evidence | Candidate-aligned MS2/NL becomes decision evidence | Can target product ions/transitions, but reason projection is not native | Strong MS/MS library/fragment/lipid rule workflows | MS2 pairing, neutral loss filter, annotation modules | LC-MS/MS preprocessing possible, not assay decision layer |
| Scoring transparency | Human-readable support/conflict/review/not-counted reasons | Strong visual/manual review; statistical scores exist but not XIC-style reason taxonomy | Identification/scoring rich but workflow-oriented | Feature/annotation evidence rich, not target decision reason text | Algorithmic peak table; transparent if scripted, but not product review semantics |
| Manual review workflow | Review Queue + workbook diagnostics + reasons | Excellent GUI chromatogram/manual integration | Excellent GUI for metabolomics/lipidomics review | Excellent GUI visual inspection | Script and plots; weaker human review product surface |
| Cross-sample alignment | Product/domain alignment in progress; not general-purpose winner | Targeted replicate comparison, retention time handling | Strong alignment in untargeted workflows | Strong join/RANSAC/gap filling workflows | Strong RT correction/correspondence workflows |
| Reproducibility/audit | Run metadata, decision projection, explicit compatibility/status fields | Document/report reproducibility strong | Project/parameter workflows, console available | Batch XML and output logs strong | Script/package-version reproducibility strong |
| Open/free maturity | Young project, narrow scope | Very mature, free/open-source | Mature, source/release available | Mature open-source | Very mature Bioconductor/GPL |
| Domain specialization | Strongest: nucleoside/nucleotide DNA/RNA adduct evidence semantics | Generic targeted quant platform | Generic metabolomics/lipidomics | Generic MS feature/annotation platform | Generic untargeted preprocessing |

## What Is Not Differentiation

These should not be used as the headline:

- `.raw` direct read. This is a useful scoping/fidelity choice for Thermo labs,
  but mature tools can also consume vendor data or vendor-converted workflows.
- AsLS baseline correction.
- Savitzky-Golay smoothing.
- Generic peak picking.
- Generic cross-sample alignment.
- ISTD ratio calculation by itself.
- Excel export by itself.
- A GUI by itself.
- MS2/product-ion handling by itself.

All of those either already exist in mature tools or can be approximated by
their scripting/reporting surfaces.

## What Is Actually Defensible

### 1. Product-decision projection

XIC requires targeted product projection fields before targeted workbook rows are
valid. `xic_extractor/output/workbook_builder.py` rejects rows where
`Counted Detection` is not `TRUE/FALSE`, where `Product State` is missing, or
where counted/non-counted state contradicts the product state.

This is a product contract, not just an output column. It separates:

- measured area
- confidence/review status
- counted detection
- not-counted signal
- product-state authority

That separation is the clearest observed differentiation from Skyline/MZmine/XCMS
outputs in these probes.

### 2. Assay-specific evidence semantics

`xic_extractor/evidence_semantics.py` maps typed LC-MS evidence into decision
classes:

- `accepted`
- `review`
- `not_counted`
- `ambiguous`
- `excluded`

It also emits interpretable support/conflict/review/not-counted reasons such as:

- `ms1_coherent`
- `candidate_aligned_ms2_nl`
- `role_aware_rt_support`
- `paired_area_ratio_support`
- `missing_ms2_not_observed`
- `plausible_nl_dropout_review`
- `paired_istd_rt_mismatch_policy`
- `legacy_review_only_projection`

This is not just a peak score. It is a domain-specific decision grammar.

### 3. Reviewable quantitation rather than black-box quantitation

The product philosophy is:

> Do not only output a number. Output a number plus why it is counted, why it is
> review-only, or why it must not be counted.

This is valuable in nucleoside/nucleotide DNA/RNA adduct workflows where false
positive counting is often worse than preserving a review-only signal.

### 4. Domain-fit over generality

The strongest XIC-specific pieces are:

- nucleoside/nucleotide target context
- DNA/RNA applicability
- paired isotope-labeled ISTD relationship
- RT relation to paired ISTD
- candidate-aligned MS2/neutral-loss evidence
- review queue and workbook-level evidence handoff

Mature tools can express parts of these as transitions, annotations, custom
reports, or scripts. They do not appear to natively own this exact decision
contract as the main product surface.

## Hard Strategic Judgment

Skyline is the real direct competitor, not FH.

If the user only needs:

- targeted small-molecule quantification
- isotope-labeled internal standard ratio
- manual chromatogram review
- calibration curves
- vendor-neutral data import
- mature reporting

then Skyline is the better product today.

XIC Extractor deserves to exist only if it doubles down on what Skyline and the
untargeted platforms do not make native:

1. assay-specific evidence adjudication,
2. counted-vs-not-counted decision authority,
3. reviewer-readable reasons,
4. workbook/diagnostic handoff tuned to nucleoside/nucleotide adduct assays.

The strategic position should be:

> XIC Extractor is not a general replacement for Skyline, MS-DIAL, MZmine, or
> XCMS. It is a narrow, auditable decision layer for Thermo RAW-backed
> nucleoside/nucleotide adduct quantitation where target-domain evidence must
> decide whether a measured signal is allowed to become a counted detection.

## Practical Product Recommendation

Invest in:

- `EvidenceVector` / `PeakHypothesis` / `AuditTrail` as first-class concepts.
- Stable exported fields for `Product State`, `Counted Detection`, `Decision Class`,
  `Reason`, and `Review Queue`.
- Tests that prove measured area can remain present while counted detection is
  false.
- Skyline comparison fixtures that show which decisions Skyline can carry only
  as external metadata versus compute natively.
- Clear docs saying `.raw` direct read is fidelity/scoping, not the moat.

Do not over-invest in:

- becoming a general MZmine/XCMS replacement,
- generic feature detection tuning as a product headline,
- broad vendor-format support before the decision grammar is proven,
- adding algorithms just because mature tools have them.

## Sources Used

- Skyline Small Molecule Quantification tutorial:
  https://skyline.ms/tutorials/25-1/SmallMoleculeQuantification/en/
- Skyline 64-bit Unplugged installation page:
  https://skyline.ms/wiki/home/software/Skyline/page.view?name=install-64-disconnected
- MS-DIAL main documentation:
  https://systemsomicslab.github.io/compms/msdial/main.html
- MS-DIAL console documentation:
  https://systemsomicslab.github.io/compms/msdial/consoleapp.html
- MS-DIAL GitHub releases:
  https://github.com/systemsomicslab/MsdialWorkbench/releases
- MZmine documentation:
  https://mzmine.github.io/mzmine_documentation/index.html
- MZmine targeted feature detection documentation:
  https://mzmine.github.io/mzmine_documentation/module_docs/lc-ms_featdet/targeted_featdet/targeted-featdet.html
- MZmine mass detection/module index:
  https://mzmine.github.io/mzmine_documentation/module_docs/featdet_mass_detection/mass-detection.html
- XCMS Bioconductor package page:
  https://bioconductor.org/packages/release/bioc/html/xcms.html
- XCMS LC-MS preprocessing vignette:
  https://sneumann.github.io/xcms/articles/xcms.html
