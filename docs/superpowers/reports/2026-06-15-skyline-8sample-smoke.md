# Skyline 8-Sample Smoke

Status: `diagnostic_only`

This run extends the Skyline single-sample smoke to the eight same-sample mzML
files listed in `2026-06-15-skyline-8raw-mzml-manifest.csv`.

It remains a mzML expressibility test, not a Thermo RAW fidelity test.

## Execution

Skyline executable:

`output/external_tools/skyline/Skyline-64_25_1_0_237/Skyline-64_25_1_0_237/Application Files/Skyline_25_1_0_237/SkylineCmd.exe`

Skyline version:

`Skyline (64-bit) 25.1.0.237 (519d29babc)`

Generated document:

`output/skyline_expressibility_20260615/xic_three_pair_8sample.sky`

All eight mzML imports completed with exit code `0` after fixing a PowerShell
wrapper interpolation mistake from the first attempt.

Exported reports:

- `output/skyline_expressibility_20260615/molecule_transition_results_8sample.tsv`
- `output/skyline_expressibility_20260615/molecule_ratio_results_8sample.tsv`
- `output/skyline_expressibility_20260615/molecule_rt_results_8sample.tsv`

## Skyline Summary

Rows in `Molecule Transition Results`:

| Target role | Present rows | Nonzero area rows |
|---|---:|---:|
| 5-hmdC light | 0 | 0 |
| d3-5-hmdC heavy | 4 | 4 |
| 5-medC light | 0 | 0 |
| d3-5-medC heavy | 0 | 0 |
| 8-oxo-Guo light | 1 | 0 |
| [13C,15N2]-8-oxo-Guo heavy | 6 | 6 |

Rows in `Molecule Ratio Results`:

| Molecule | Ratio rows | Valid RatioToStandard rows |
|---|---:|---:|
| 5-hmdC | 4 | 0 |
| 5-medC | 0 | 0 |
| 8-oxo-Guo | 6 | 0 |

The report surface is quantitative but not decision-authoritative:

- RT and product-transition area are exported.
- `RatioToStandard` remains `#N/A` in this run.
- No exported field is equivalent to XIC `product_state`,
  `counted_detection`, or the workbook `Reason` decision text.

## XIC Reference Summary

Same eight sample names in
`local_validation_artifacts/targeted_gt_workbooks/8raw/xic_results_20260512_1151.xlsx`:

| Target role | Present finite-area rows | Accepted rows | Review-only / not-counted rows |
|---|---:|---:|---:|
| 5-hmdC | 8 | 7 | 1 |
| d3-5-hmdC | 8 | 8 | 0 |
| 5-medC | 8 | 7 | 1 |
| d3-5-medC | 8 | 8 | 0 |
| 8-oxo-Guo | 7 | 0 | 7 |
| [13C,15N2]-8-oxo-Guo | 8 | 8 | 0 |

## Interpretation

This is a useful partial pass for Skyline:

- Skyline can be run locally without system-wide installation.
- The corrected transition list imports as three light/heavy molecule pairs.
- Skyline can import the eight same-sample mzML files with full-scan DDA
  settings.
- Skyline can export molecule transition, ratio, and RT reports.

This is not parity with XIC:

- The Skyline run uses product-transition extraction from mzML, while XIC's
  reference workbook reports MS1 Gaussian15 positive AsLS residual area plus
  candidate-aligned MS2/neutral-loss evidence.
- Skyline reports useful peak evidence but does not natively emit
  `accepted`, `review only`, `not_counted`, or reason strings matching XIC's
  product projection layer.
- The clean positive controls (`5-hmdC`, `5-medC`) are mostly absent in Skyline
  light product-transition output under this method, while XIC reports finite
  MS1 areas and decision reasons.
- The negative/review control (`8-oxo-Guo`) becomes mostly absent or zero-area
  light product-transition output in Skyline, while XIC preserves finite MS1
  area but marks it `review only, not counted` because of NL failure.

Current strategic read:

Skyline is not a weak comparator; it is clearly capable infrastructure. But this
bounded run supports the earlier positioning: XIC's defensible difference is not
generic extraction. It is the explicit product-decision projection that keeps a
measured signal separate from a counted detection and preserves the reason.

## Next Bounded Tests

1. Try a Skyline MS1-focused document that explicitly targets precursor traces
   rather than only NL product transitions.
2. Try a Skyline annotation/custom-report path to see whether XIC-style
   decision reasons can be carried as imported metadata. That would be
   workflow parity, not native decision parity, if the reason is computed
   outside Skyline.
3. Repeat the same experiment with RAW input only after the matching Thermo RAW
   files are located.
