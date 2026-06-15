# Skyline Single-Sample Smoke

Status: `diagnostic_only`

This smoke test verifies that Skyline can be run locally from the official
Unplugged distribution and can process the prepared three-pair small-molecule
document for one same-sample mzML file.

It does not test Thermo RAW fidelity, full 8-sample parity, or production
readiness.

## Tool

- Download source:
  `https://skyline.ms/wiki/home/software/Skyline/page.view?name=install-64-disconnected`
- Local executable:
  `output/external_tools/skyline/Skyline-64_25_1_0_237/Skyline-64_25_1_0_237/Application Files/Skyline_25_1_0_237/SkylineCmd.exe`
- Version smoke:
  `Skyline (64-bit) 25.1.0.237 (519d29babc)`
- ProteoWizard:
  `ProteoWizard MSData 3.0.25237`

## Inputs

- Skyline transition list:
  `docs/superpowers/reports/2026-06-15-skyline-three-pair-transition-list.csv`
- XIC oracle:
  `docs/superpowers/reports/2026-06-15-xic-skyline-expressibility-oracle.csv`
- Skyline document:
  `output/skyline_expressibility_20260615/xic_three_pair.sky`
- mzML input:
  `<mzML fixture dir>\BenignfatBC1055_DNA.mzML`
- XIC reference workbook:
  `local_validation_artifacts/targeted_gt_workbooks/8raw/xic_results_20260512_1151.xlsx`

## Commands Executed

The document was created with full-scan DDA settings, centroided precursor
extraction, centroided product extraction, and a 1-minute scheduled RT filter.

The first import attempt without full-scan settings failed because the mzML file
does not contain SRM/MRM chromatograms. The successful run used the full-scan
settings above.

Generated Skyline reports:

- `output/skyline_expressibility_20260615/molecule_transition_results.tsv`
- `output/skyline_expressibility_20260615/molecule_ratio_results.tsv`
- `output/skyline_expressibility_20260615/molecule_rt_results.tsv`

## Skyline Output

`Molecule Transition Results` for `BenignfatBC1055_DNA`:

| Molecule | Precursor m/z | Product m/z | RT | Area | PeakRank |
|---|---:|---:|---:|---:|---:|
| 5-hmdC heavy | 261.12728 | 145.079876 | 9.0850 | 17757614 | 1 |
| 8-oxo-Guo light | 300.0939 | 168.0516 | 13.7273 | 0 | 0 |
| 8-oxo-Guo heavy | 303.0913 | 171.0490 | 13.7871 | 12152847 | 1 |

`Molecule Ratio Results`:

| Molecule | RT | RatioToStandard | Quantification |
|---|---:|---:|---:|
| 5-hmdC | 9.0850 | #N/A | #N/A |
| 8-oxo-Guo | 13.7572 | #N/A | #N/A |

Skyline import log also discarded several chromatograms because the explicit RT
did not fall within the available chromatogram RT range:

- `5-hmdC` light product transition
- `5-medC` light product transition
- `5-medC` heavy product transition

## XIC Reference For The Same Sample

`XIC Results` for `BenignfatBC1055_DNA`, with workbook merged sample cells
forward-filled:

| Target | RT | Area | Confidence | Decision surface |
|---|---:|---:|---|---|
| 5-hmdC | 9.0845 | 1489314.54 | HIGH | accepted; strict NL OK |
| d3-5-hmdC | 9.0015 | 11306175.95 | HIGH | accepted; strict NL OK |
| 5-medC | 12.6420 | 35356308.27 | HIGH | accepted; strict NL OK |
| d3-5-medC | 12.5593 | 21593757.17 | HIGH | accepted; strict NL OK |
| 8-oxo-Guo | 13.8842 | 775588.11 | VERY_LOW | review only, not counted; NL fail |
| [13C,15N2]-8-oxo-Guo | 13.6035 | 30327636.92 | HIGH | accepted; strict NL OK |

## Interpretation

Skyline passed the local execution smoke:

- official free Skyline executable downloaded and ran in place;
- transition list imported;
- full-scan settings allowed a same-sample mzML import;
- built-in molecule reports exported.

Skyline did not yet reproduce XIC's product-decision authority:

- the exported Skyline reports provide RT, area, peak rank, ratio, and
  quantification fields;
- they do not contain native `product_state`, `counted_detection`, or
  human-readable reason fields equivalent to XIC's workbook;
- the single-sample Skyline run represented product-transition evidence, not
  XIC's MS1 Gaussian15 positive AsLS residual area;
- `8-oxo-Guo` is present as a zero-area light product transition plus a heavy
  product transition, not as XIC's finite-area `review only, not counted` row.

Current verdict:

Skyline is executable and strong enough to be a real comparator. The first smoke
supports a `partial pass`: Skyline can carry the target/product-transition
workflow and export useful reports, but this run does not show native parity
with XIC's counted-vs-review-only decision layer.

## Next Bounded Step

Run the same three-pair Skyline document across the remaining seven mzML files,
then compare:

- which XIC counted detections are absent or zero in Skyline product-transition
  reports;
- which Skyline target ratios become `#N/A`;
- whether any Skyline report or annotation path can preserve the XIC
  `not_counted` reason without an external post-export script.
