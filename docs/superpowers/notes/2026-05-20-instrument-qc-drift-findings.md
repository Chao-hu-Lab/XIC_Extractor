# Instrument QC Drift Findings, 2026-05-20

## Scope

本 note 整理目前 instrument QC 的數據發現，重點是把兩種證據分清楚：

- clean standards：SDO/LEK 與 Mix STDs，反映乾淨基質下的儀器、方法、RT/area/HCD product-ion 表現。
- biological QC ISTDs：85 RAW 生物樣本中的 pooled QC 內標，反映真實 matrix 下的 RT/area/intensity 漂移。

clean standards 可以定位儀器本身的行為，但不能單獨代表生物樣本 matrix effect。biological QC ISTDs 是目前生物樣本中唯一額外添加的標準品，因此是判斷真實流程穩定性的主要 anchor。

## Artifacts

- Instrument QC output:
  `output\instrument_qc\hcd_audit_v1_sdolek_whcd_review_20260520`
- Main workbook:
  `output\instrument_qc\hcd_audit_v1_sdolek_whcd_review_20260520\instrument_qc_trend_sdolek.xlsx`
- Drift overview plot:
  `output\instrument_qc\hcd_audit_v1_sdolek_whcd_review_20260520\plots\instrument_qc_clean_vs_biological_drift_overview_readable.png`
- SDO/LEK dedicated trend plot:
  `output\instrument_qc\hcd_audit_v1_sdolek_whcd_review_20260520\plots\instrument_qc_sdolek_trend_lines.png`
- Decision cards:
  `output\instrument_qc\hcd_audit_v1_sdolek_whcd_review_20260520\plots\instrument_qc_drift_findings_cards.png`
- Biological QC ISTD source workbook:
  `C:\Users\user\Desktop\XIC_Extractor\output\validation_harness\targeted_ms2_trace_selection_fix_85raw\tissue_85raw_local_minimum\xic_results_process_w4.xlsx`

The 85 RAW targeted workbook is an existing validation artifact from 2026-05-08. It is useful for drift interpretation, but final product-level conclusions should rerun 85 RAW targeted extraction with the current code.

## Finding 1: Clean Chemical Evidence Is Strong

Current clean-standard audit is no longer pointing to missing chemistry evidence:

- SDO/LEK MS1 trend: `22/22 detected`.
- Mix STDs MS1 trend: `192/192 detected`.
- HCD/product-ion audit: `211/214 hcd_supported`.
- Manual Review Queue: `0`.

The remaining three non-supported HCD rows are row-level context, not priority review blockers after unmapped / isotope-supported logic.

Interpretation: the previous visible failures were mainly stale RT priors / windowing and review-surface semantics, not absence of expected product-ion evidence.

## Finding 2: RT Drift Exists, But It Is Not One Global Offset

Clean standards:

- SDO RT is very stable: range `0.049 min`, RT-order correlation near zero.
- LEK shows a clear batch trend: RT range `0.539 min`, RT-order correlation about `0.95`.
- Mix STDs show compound-dependent RT spread; some compounds move more than others.

The overview plot intentionally shows SDO/LEK as endpoint arrows rather than full sparse-point trend lines. The full SDO/LEK point-to-point view belongs in the dedicated trend plot.

Biological QC ISTDs:

- `d3-N6-medA`, `d4-N6-2HE-dA`, `d3-dG-C8-MeIQx`, and `d3-5-medC` trend later with injection order.
- `15N5-8-oxodG` and `[13C,15N2]-8-oxo-Guo` trend earlier with injection order.
- `d3-N6-medA` is the strongest RT-drift example in QC, with about `2.12 min` QC RT range.

Interpretation: a single global RT correction model is too coarse. The project should treat RT drift as compound/RT-region-specific evidence and prefer local residual windows over one universal correction.

## Finding 3: Area / Intensity Drift Has A Mid-Late Run Event

Clean standards show a visible signal dip around injection order `78`:

- Mix STDs median log2 area ratio near order `78`: about `-1.09`, roughly half signal.

Biological QC ISTDs show a related but target-specific pattern:

- The QC median does not collapse globally, but several ISTDs dip strongly around order `76`, `97`, or `110`.
- `15N5-8-oxodG`, `d3-N6-medA`, `d4-N6-2HE-dA`, and `d3-5-medC` show stronger late-run area drops than the QC median.
- Some ISTDs remain stable in QC, especially `d3-5-hmdC` and `d3-dG-C8-MeIQx`.

Interpretation: this is not a full-run failure. It looks more like a target-specific sensitivity / ionization / matrix interaction pattern, with a clean-standard signal event near the biological QC mid-late run.

## Finding 4: Clean Standards And Biological ISTDs Answer Different Questions

Use clean standards to answer:

- did the method see known compounds in a clean matrix?
- are RT priors/windows plausible?
- are expected CID/wHCD product ions visible?
- is there an instrument-level signal or RT drift trend?

Use biological QC ISTDs to answer:

- does the same instrument behavior survive real matrix?
- are internal standards stable across pooled QC injections?
- does a drift event affect final biological runs?
- which RT regions or compounds need local correction / review?

Therefore, clean standards can support instrument diagnosis, but production confidence in biological extraction still needs the biological QC ISTD layer.

## Current Decision

Decision: `instrument_drift_evidence_ready_for_diagnostic`

Meaning:

- The current data are enough to explain that RT and signal drift are real.
- The drift is not a single global shift.
- Clean-standard HCD/MS1 evidence is strong enough to be used as an instrument QC anchor.
- Biological QC ISTDs should be the main anchor for real matrix behavior.
- No production area / RT / scoring / matrix gate should be changed from this note alone.

## Recommended Next Step

Create an audit-only biological ISTD drift diagnostic that uses current-code 85 RAW targeted output and docs-derived injection order:

- input: current 85 RAW targeted workbook with Score Breakdown / peak evidence.
- input: `instrument_qc_injection_order.csv`.
- output: QC ISTD RT trend, area trend, intensity trend, and target-specific drift flags.
- output: one human-facing workbook sheet and one compact PNG/PDF report.

Acceptance should be based on whether the diagnostic can clearly separate:

- global instrument signal event,
- compound-specific RT drift,
- target-specific area/intensity instability,
- real matrix effect,
- and stale RT prior / window issues.
