# Untargeted LC-MS Literature Gap Assessment

Date: 2026-05-14

Scope: assess whether the current untargeted pipeline addresses real LC-MS / untargeted metabolomics failure modes seen in the literature, and define which issues can be handled on the data-processing side.

## Bottom Line

目前 pipeline 有解決一個真實且重要的 LC-MS untargeted 問題：同一個化學訊號因 RT drift、peak picking failure、local low signal、single-sample owner fragmentation 或 duplicate claim 被拆成多個 row 或從 final matrix 消失。

但不能宣稱它已經解決所有質譜分析問題。

目前已經有實作或驗證支撐的範圍：

- sample-local XIC owner confirmation
- owner-centered gap filling / backfill
- drift-aware owner alignment
- pre-backfill identity-family consolidation
- primary matrix vs Review / Audit 分層
- strict targeted ISTD benchmark for RT / area trend
- inactive RNA tag exclusion in DNA-only evaluation

目前尚未真正解決，或只做到診斷/部分防護的範圍：

- matrix effect / ion suppression
- global intensity drift / batch effect correction
- random missingness mechanism classification
- blank/background contaminant removal
- isotope/adduct/in-source fragment/salt-cluster artifact annotation
- true endogenous compound vs artifact credentialing
- post-acquisition quantitative normalization

因此比較準確的產品定位是：

```text
Current pipeline = alignment + recovery + primary matrix hygiene layer
Not yet = full LC-MS QA/QC normalization + artifact deconvolution layer
```

## Literature Signals

### DNA Adductomics-Specific Evidence Strengthens The Same Direction

Vangeenderhuysen et al. 2026 is directly relevant because it focuses on
large-scale untargeted DNA adductomics, not generic metabolomics. The paper
builds a fit-for-purpose preprocessing and normalization workflow using xcms,
known DNA adducts, ISTDs, QCs, technical replicates, and normalization
performance metrics.

The main implications for us are:

- data-set-specific preprocessing is required; their optimized xcms parameters
  are explicitly not gold standards for every DNA adductomics data set;
- known adducts and ISTDs are useful benchmark anchors for peak detection, RT
  alignment, feature grouping, and normalization evaluation;
- DNA adducts are low-abundance and may appear in a minority of samples, so
  overly aggressive prevalence/grouping filters can remove real features;
- gap filling is important, but remaining high-missingness features still need
  filtering or special handling;
- feature-based normalization methods, especially QC-RLSC / local methods,
  performed better than sample-based TIC / median normalization in their
  evaluation;
- sample-based normalization can inflate ISTD variation and create misleading
  downstream statistics;
- RSD* and D-ratio are useful objective metrics, but PCA/QC clustering remains
  necessary because metrics alone can mislead.

This paper strengthens our current conclusion. Our alignment/backfill/family
consolidation layer addresses the preprocessing side: false missingness,
RT-driven splitting, and primary matrix pollution. It does not yet address the
normalization side that the paper treats as mandatory for large-scale
adductomics.

### Pooled QC Samples Are Standard For Untargeted Data Quality

Davis et al. 2023 reviewed LC-MS untargeted metabolomics studies and concluded that pooled QC samples are useful for monitoring and correcting analytical variance. They also noted that many studies create pooled QC samples but do not fully use them for data quality improvement, especially feature filtering, analytical drift correction, and metabolite annotation.

Implication for us:

- Our strict ISTD benchmark is consistent with the literature's QC-first direction.
- But ISTD-only benchmarking is narrower than pooled QC-based correction.
- If the batch includes pooled QC and blanks, the next correct data-side step is to consume them explicitly.

### RT / m/z / Intensity Drift Are Expected, Not Edge Cases

Brunius et al. 2016 describe multi-batch LC-MS data as affected by signal intensity changes, mass accuracy drift, and RT drift. Their method addressed between-batch feature misalignment and within-batch signal intensity drift correction; they reported improved feature recovery and lower QC CV.

Implication for us:

- Our RT drift-aware owner alignment is solving a literature-recognized problem.
- Our current recentering step addresses false drift reporting after family consolidation.
- But our current pipeline does not yet implement full within-batch or between-batch intensity drift correction.

### Gap Filling From Raw m/z-RT Regions Is A Known Data-Side Fix

XCMS `fillChromPeaks()` fills missing chromatographic peaks after correspondence by integrating signal in the feature's m/z-RT region. It explicitly treats many missing values as peak detection failures rather than true biological absence, but still keeps `NA` if no signal exists in that raw region.

Implication for us:

- Our owner-centered backfill is conceptually aligned with established LC-MS preprocessing.
- Our version is more constrained because it uses tag/product/observed-loss family evidence before backfilling.
- This supports the current direction: backfill should recover missing sample-level signal only for already-supported families, not create standalone final row identities.

### Missing Values Have Multiple Mechanisms

Do et al. 2018 showed that missing values in untargeted MS data can arise from fixed LOD, probabilistic LOD, run-day-specific LOD, random missingness, and mixtures of mechanisms. They also showed that imputation methods assuming a single missingness mechanism can inflate error or lose power when the assumption is wrong.

Implication for us:

- Our `MISS` vs `rescued` distinction is not enough.
- We should classify missingness mechanism before downstream imputation or filtering.
- Backfill can solve peak-detection failure, but cannot prove true absence or correct matrix-suppressed signal without QC/blank/replicate evidence.

### QC-Based Signal Correction And SERRF Address Intensity Drift

Fan et al. 2019 introduced SERRF, a random-forest method using pooled QC samples to remove systematic variation in large-scale untargeted lipidomics. The paper frames large untargeted studies as affected by batch differences, longitudinal drift, and instrument-to-instrument variation; SERRF reduced technical error in large cohort datasets.

Implication for us:

- Our 85 RAW runtime and alignment improvements do not equal signal normalization.
- We need a post-matrix intensity correction layer if the output is used for quantitative comparison.
- A conservative first version could export enough metadata for external QC-RLSC / SERRF, then later implement native correction.

### Matrix Effect Is Not Fully Solvable By Final Matrix Processing Alone

Schrimpe-Rutledge et al. 2019 demonstrated that identical concentrations of labeled standards can have different signal intensities across biofluids and even between co-eluting standards due to matrix effect and ionization efficiency. Their conclusion is directly relevant: untargeted signal intensities cannot be directly compared across matrices or between analytes without proper response correction.

Zhu et al. 2024 further discuss post-column infusion for matrix-effect monitoring in untargeted methods. This points to an important boundary: real matrix-effect correction often requires experimental controls or acquisition-side signals, not only a final feature matrix.

Implication for us:

- Current pipeline does not solve matrix effect.
- ISTD area correlation only tells us whether the selected ISTD trend agrees with targeted extraction.
- Matrix effect correction needs internal standards, pooled QC, blanks, matrix-matched controls, post-extraction spikes, post-column infusion, dilution series, or some other explicit control.

### Artifacts Are A Known Untargeted Feature-Table Problem

Filtering literature notes that untargeted feature tables contain background signals, duplicate signals from the same analyte, adducts, isotopes, in-source fragments, noise, incorrect integration regions, and missing values.

CAMERA exists specifically to annotate isotope peaks, adducts, fragments, and clusters of mass signals originating from one metabolite using mass differences and peak-shape evidence.

MS-FLO similarly targets false positive peak reports in untargeted LC-MS feature lists.

Credentialing approaches use stable isotope labeling to distinguish biological features from artifactual features. This matters because many artifacts cannot be confidently separated from unknown endogenous features by m/z/RT alone.

Implication for us:

- Our family consolidation reduces one artifact-like symptom: multiple near-identical rows for a likely same feature.
- Our active DNA neutral-loss gate reduces off-target candidates for this specific assay.
- But we do not yet implement general isotope/adduct/in-source-fragment/blank artifact annotation.

## Issue-By-Issue Assessment

| Real-world issue | Literature data-side method | Current pipeline status | Assessment |
| --- | --- | --- | --- |
| RT drift | RT alignment, injection-order modeling, QC/ISTD trend, recentering | drift-aware owner edges, targeted ISTD trend adapter, recentering | mostly addressed for alignment; not a full chromatogram warping system |
| m/z drift | mass tolerance, feature alignment, calibrants | ppm gates only | partially addressed; no explicit mass drift model |
| Peak picking false missing | raw m/z-RT gap filling, targeted extraction, weak signal recovery | owner-centered backfill | addressed for supported families |
| Random missingness | missingness mechanism classification, replicate-aware imputation, KNN/RF/QRILC/MI depending on mechanism | status/reason fields, no mechanism classifier | not solved |
| LOD / low abundance missingness | LOD-aware imputation, group-wise prevalence, QC missingness filters | backfill plus absent/rescued status | partially solved; no downstream imputation policy |
| Intensity drift | QC-RLSC, spline/LOESS, SERRF, batch correction | targeted area benchmark only | not solved as correction; only diagnostic |
| Batch effect | pooled QC, reference material, injection order, batch correction | run metadata and guardrails, no correction engine | not solved |
| Matrix effect / ion suppression | internal standards, matrix-matched calibration, post-extraction spike, post-column infusion, dilution series | ISTD benchmark only | not solved; needs controls |
| Adduct/isotope duplication | CAMERA/MS-FLO-like annotation and grouping | identity-family consolidation only within tag/product/loss logic | partially solved for this assay, not general |
| In-source fragments | in-source fragment annotation, MS/MS/library evidence, collision-energy evidence | product/observed loss gates only | partially protected, not annotated |
| Background contaminants / blanks | blank subtraction, blank/sample ratio, batch blank filtering | no blank-aware gate | not solved |
| Artificial compounds / artifacts | credentialing, blanks, sample prep controls, isotope labeling, annotation | Audit/Review preserves evidence; no artifact credentialing | not solved |
| Wrong targeted peak | target-vs-untargeted RT/area benchmark | strict benchmark exposes `d3-N6-medA` anomaly | diagnostic solved; correction belongs to targeted method |
| DNA adductomics normalization | feature-based QC/local normalization, RSD*, D-ratio, PCA/QC clustering | no native normalization layer | not solved; now a high-priority next phase |

## What We Have Actually Solved

### 1. False Missing From Peak Detection Failure

The literature supports raw-data gap filling when a feature is detected in some samples but absent in others due to peak detection failure. Our owner-centered backfill is a domain-specific implementation of that idea.

The key improvement is that we do not blindly fill every m/z-RT hole. We require family support first:

```text
candidate evidence
  -> sample-local owner
  -> identity-compatible family
  -> owner-centered backfill
  -> rescued / absent / review-only cell status
```

This addresses the old pipeline failure where stable ISTDs could disappear from the final matrix because upstream peak detection/filtering missed them.

### 2. Duplicate m/z / RT Matrix Pollution

The literature recognizes duplicate signals from adducts, isotopes, fragments, and same-analyte feature splitting as a serious untargeted problem.

Our current fix is narrower but relevant:

- same tag
- compatible precursor m/z
- compatible RT
- compatible product m/z
- compatible observed neutral loss
- disjoint or compatible sample ownership

Pre-backfill identity-family consolidation collapses compatible single-sample owner families before expensive backfill and before production matrix promotion.

This is why the new matrix now looks closer to the old pipeline's clean output while retaining Review/Audit evidence.

### 3. RT Drift In Alignment

RT drift is an expected LC-MS phenomenon. Our current system handles it at the feature alignment layer:

- sample-local owners are found first;
- RT drift evidence can be derived from targeted ISTD trend;
- owner edges can be evaluated with drift-corrected RT deltas;
- consolidated rows are recentered from present cells.

This solves the observed failure mode where a same-feature-like family splits only because raw RT shifted across samples.

### 4. Targeted Benchmark As A Diagnostic Gate

The strict ISTD benchmark is strongly aligned with the literature's QC-first stance.

It does not merely check feature presence. It checks:

- exactly one primary matrix hit
- RT mean delta
- sample-level RT median and p95
- log-area Pearson / Spearman
- coverage against targeted positives
- inactive RNA tag exclusion in DNA-only mode

This makes targeted data a benchmark for untargeted behavior without leaking target labels into production identity decisions.

## What We Have Not Solved Yet

### 1. Matrix Effect

Matrix effect is not solved by the current pipeline.

We can detect symptoms through ISTD behavior, but we cannot correct arbitrary feature intensities without additional controls. If two compounds have different ionization efficiency, or the same analyte behaves differently in plasma/urine/tissue matrix, a final matrix algorithm cannot infer the true correction from feature intensity alone.

Required data-side additions:

- per-sample ISTD normalization outputs
- feature-to-ISTD assignment strategy
- pooled QC sample support
- blank/sample ratio
- post-extraction spike or post-column infusion metadata if available
- optional matrix-effect diagnostic plots by RT window

### 2. Global Intensity Drift

We currently benchmark area trend against targeted for ISTDs, but we do not correct all feature intensities across injection order.

Required additions:

- parse sample type: sample / QC / blank / calibration / pooled QC
- preserve injection order in run metadata
- export `area_raw`
- export corrected columns separately, e.g. `area_qc_rlsc`, `area_serrf`, `area_istd_norm`
- report pre/post correction QC CV and drift slope
- report RSD* and D-ratio in the adductomics style, while keeping PCA/QC clustering
  as a required visual/diagnostic check

### 3. Random Missingness

Backfill can recover missing peaks caused by feature detection failure. It does not distinguish all missingness mechanisms.

Required additions:

- missingness classifier per feature/sample
- reason labels such as `below_lod`, `processing_miss`, `raw_absent`, `matrix_suppressed`, `random_missing`, `ambiguous`
- group-wise prevalence report
- QC missingness report
- downstream imputation recommendation, not automatic silent imputation

### 4. Artificial Compounds And Artifacts

The current DNA tag logic is useful but not a universal artifact filter.

Required additions:

- blank-aware contaminant scoring
- isotope/adduct grouping
- in-source fragment annotation
- salt cluster / mass defect filters when appropriate
- peak-shape correlation across co-eluting signals
- Review/Audit flags that explain whether a row may be adduct/isotope/fragment/background
- optional stable-isotope credentialing support if experimental design provides it

## Recommended Data-Side Roadmap

### Phase 1: Make QC / Blank / Injection Metadata First-Class

Add or standardize sample metadata columns:

- `sample_stem`
- `sample_type`: `sample`, `pooled_qc`, `blank`, `calibration`, `istd_mix`, `other`
- `batch_id`
- `injection_order`
- `matrix_type`
- `prep_batch`
- `technical_replicate_group`
- `normalization_qc_role`: `training_qc`, `evaluation_qc`, `none`

Do not correct signals yet. First make the evidence available and exportable.

### Phase 2: Add Feature-Level QA Report

New diagnostic outputs:

- `feature_qc_metrics.tsv`
- `feature_missingness_mechanism.tsv`
- `feature_blank_contaminant_flags.tsv`
- `feature_artifact_annotation.tsv`
- `feature_intensity_drift.tsv`

Important metrics:

- QC CV before correction
- ISTD RSD*
- feature RSD* in technical replicates / evaluation QCs
- D-ratio
- blank/sample ratio
- sample prevalence
- QC prevalence
- rescued cell fraction
- high backfill dependency
- injection-order area slope
- ISTD-normalized area slope
- RT drift slope
- m/z drift summary

### Phase 3: Keep Matrix Columns Explicit

Never overwrite raw area silently. Export separate quantitative layers:

```text
area_raw
area_backfilled
area_istd_normalized
area_qc_corrected
area_final_recommended
```

This prevents us from hiding matrix effect or correction artifacts.

### Phase 4: Add Artifact-Aware Primary Promotion Gates

Primary matrix promotion should eventually consume artifact evidence:

- high blank ratio -> Review, not Matrix
- likely isotope/adduct/fragment duplicate -> representative in Matrix, related ions in Audit
- low QC reproducibility -> Review or flagged Matrix
- high random missingness -> Review
- high matrix-effect susceptibility without correction -> flagged Matrix

This matches the literature direction: do not delete evidence, but do not let every signal become a biological feature row.

### Phase 5: Add Optional Correction Engines

Candidate correction engines:

- QC-RLSC / LOESS for per-feature injection-order drift
- SERRF-like random forest correction when enough pooled QC samples exist
- ISTD normalization for targeted families or RT-near/class-near features
- blank subtraction or blank ratio filtering
- local mean / local feature-based signal correction as a lower-complexity
  baseline against QC-RLSC

These should be opt-in at first and benchmarked with:

- QC CV improvement
- RSD* improvement without inflating ISTD variation
- D-ratio improvement without artificial biological variance inflation
- PCA clustering of QCs and technical replicates
- biological group preservation
- ISTD RT/area trend preservation
- no increase in false primary matrix artifacts

## Decision For Current Pipeline

Current pipeline should be described as:

> A DNA-tagged untargeted alignment and recovery pipeline that uses raw XIC ownership, family consolidation, backfill, and targeted ISTD benchmarking to produce a cleaner primary matrix while preserving audit evidence.

It should not be described as:

> A complete LC-MS matrix-effect, artifact, and batch-correction solution.

The next product-quality milestone should be:

```text
strict ISTD gate
  + QC/blank-aware diagnostics
  + missingness mechanism report
  + artifact annotation flags
  + adductomics-style normalization evaluation
  + optional correction layer with raw/corrected areas kept separate
```

## References

- Davis et al. 2023, Current practices in LC-MS untargeted metabolomics: a scoping review on the use of pooled quality control samples. Analytical Chemistry. https://doi.org/10.1021/acs.analchem.3c02924
- Vangeenderhuysen et al. 2026, Challenges and Good Practices in Preprocessing and Normalization of Untargeted DNA Adductomics Data in Exposomics Research. Analytical Chemistry. https://doi.org/10.1021/acs.analchem.5c06549
- Brunius et al. 2016, Large-scale untargeted LC-MS metabolomics data correction using between-batch feature alignment and cluster-based within-batch signal intensity drift correction. Metabolomics. https://doi.org/10.1007/s11306-016-1124-4
- xcms `fillChromPeaks()` documentation. https://rdrr.io/bioc/xcms/man/fillChromPeaks.html
- Do et al. 2018, Characterization of missing values in untargeted MS-based metabolomics data and evaluation of missing data handling strategies. Metabolomics. https://doi.org/10.1007/s11306-018-1420-2
- Fan et al. 2019, Systematic Error Removal Using Random Forest for Normalizing Large-Scale Untargeted Lipidomics Data. Analytical Chemistry. https://doi.org/10.1021/acs.analchem.8b05592
- Schrimpe-Rutledge et al. 2019, Impact of matrix effects and ionization efficiency in non-quantitative untargeted metabolomics. Metabolomics. https://doi.org/10.1007/s11306-019-1597-z
- Zhu et al. 2024, Development of an Untargeted LC-MS Metabolomics Method with Postcolumn Infusion for Matrix Effect Monitoring in Plasma and Feces. Journal of the American Society for Mass Spectrometry. https://doi.org/10.1021/jasms.3c00418
- Kuhl et al. / CAMERA documentation, LC-MS peak annotation and identification with CAMERA. https://rdrr.io/bioc/CAMERA/f/inst/doc/CAMERA.pdf
- Filtering procedures for untargeted LC-MS metabolomics data. BMC Bioinformatics. https://doi.org/10.1186/s12859-019-2871-9
- Mahieu et al. 2014, Credentialing features: a platform to benchmark and optimize untargeted metabolomic methods. Analytical Chemistry. https://doi.org/10.1021/ac503092d
