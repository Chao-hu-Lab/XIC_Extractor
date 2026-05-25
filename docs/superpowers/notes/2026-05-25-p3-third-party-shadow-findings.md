# P3 Third-Party Shadow Findings

Gate status: `diagnostic_only`.
Maintenance disposition: external runner / normalizer / joiner code is not
retained as maintained Phase 1 code after this audit. The retained artifacts
are this findings note, the P3 spec disposition, and local output evidence
under `output/phase1_p3_third_party_shadow_comparison/`.

P3 produced partial third-party evidence from asari. MassCube remains
`inconclusive_external_runner` for this run because the installed workflow
cannot import under the isolated Python 3.13 venv before processing starts.
No production RAW-reading, peak-picking, integration, alignment, config, or
workbook behavior changed.

## Inputs

- Internal comparator:
  `output/phase1_p2_asls_shadow_validation/alignment/asls_shadow/alignment_cell_integration_audit.tsv`
- Strict ISTD mapping:
  `output/phase1_p2_asls_shadow_validation/diagnostics/targeted_istd_benchmark/targeted_istd_benchmark_summary.tsv`
- User-provided experimental mzML source:
  `C:\Users\user\Desktop\NTU cancer\NTU Tissue preprocess\mzml`
- 8 validation mzML files were present; 79 extra mzML files were ignored for
  the 8RAW run.
- 8-file hardlink staging folder:
  `C:\tmp\xic_p3_mzml_8raw`

## Third-Party Environment

- Isolated venv: `C:\tmp\xic_p3_shadow_venv`
- `asari-metabolomics==1.17.0`
- `masscube==1.2.20`
- Installed MassCube metadata reports license `CC BY-NC 4.0`; keep
  MassCube-derived artifacts local unless redistribution is separately
  reviewed.

## Historical Run Commands

These commands are run provenance for the 2026-05-25 audit. The temporary P3
wrapper modules used to generate the evidence were discarded before commit
because the external tools are not accepted as production gates or promotion
evidence.

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.p3_shadow_inputs --internal-integration-audit-tsv output\phase1_p2_asls_shadow_validation\alignment\asls_shadow\alignment_cell_integration_audit.tsv --mzml-dir "C:\Users\user\Desktop\NTU cancer\NTU Tissue preprocess\mzml" --output-tsv output\phase1_p3_third_party_shadow_comparison\p3_shadow_input_manifest.tsv
uv venv C:\tmp\xic_p3_shadow_venv
uv pip install --python C:\tmp\xic_p3_shadow_venv\Scripts\python.exe asari-metabolomics masscube
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.asari_shadow_runner --venv-python C:\tmp\xic_p3_shadow_venv\Scripts\python.exe --mzml-dir C:\tmp\xic_p3_mzml_8raw --asari-output-dir output\phase1_p3_third_party_shadow_comparison\asari_run --standardized-output-tsv output\phase1_p3_third_party_shadow_comparison\shadow_comparison_asari_8raw.tsv
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.third_party_shadow_tables asari --asari-output-dir output\phase1_p3_third_party_shadow_comparison\asari_run --output-tsv output\phase1_p3_third_party_shadow_comparison\shadow_comparison_asari_8raw.tsv
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.third_party_shadow_tables masscube --masscube-output-dir C:\tmp\xic_p3_masscube_8raw --output-tsv output\phase1_p3_third_party_shadow_comparison\shadow_comparison_masscube_8raw.tsv
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.shadow_comparison_join --internal-integration-audit-tsv output\phase1_p2_asls_shadow_validation\alignment\asls_shadow\alignment_cell_integration_audit.tsv --targeted-istd-summary-tsv output\phase1_p2_asls_shadow_validation\diagnostics\targeted_istd_benchmark\targeted_istd_benchmark_summary.tsv --asari-features-tsv output\phase1_p3_third_party_shadow_comparison\shadow_comparison_asari_8raw.tsv --masscube-features-tsv output\phase1_p3_third_party_shadow_comparison\shadow_comparison_masscube_8raw.tsv --output-dir output\phase1_p3_third_party_shadow_comparison
```

## Outputs

- Manifest:
  `output/phase1_p3_third_party_shadow_comparison/p3_shadow_input_manifest.tsv`
- asari native output:
  `output/phase1_p3_third_party_shadow_comparison/asari_run_asari_project_5259212/preferred_Feature_table.tsv`
- asari standardized output:
  `output/phase1_p3_third_party_shadow_comparison/shadow_comparison_asari_8raw.tsv`
  with 69,886 sample-level rows.
- MassCube standardized output:
  `output/phase1_p3_third_party_shadow_comparison/shadow_comparison_masscube_8raw.tsv`
  with 0 rows because native output was unavailable.
- Join report:
  `output/phase1_p3_third_party_shadow_comparison/shadow_comparison_8raw.tsv`
- Join summary:
  `output/phase1_p3_third_party_shadow_comparison/shadow_comparison_8raw_summary.tsv`
- Relaxed asari target-window audit:
  `output/phase1_p3_third_party_shadow_comparison/asari_target_window_audit.tsv`

## Result Summary

- Join rows: 48
- `pair_match_asari`: 7
- `internal_only`: 41
- `empty_tools`: `masscube`

Off-target asari-only features are intentionally excluded from this strict
ISTD report. A third-party `*_only` row now means the third-party feature fell
inside a strict ISTD target m/z/RT window but no internal row matched it. The
69,879 off-target asari features from the untargeted table are not internal
ISTD misses.

The only strict ISTD with asari pair matches was `d3-dG-C8-MeIQx`
(`FAM001878`), with 7 of 8 validation samples matched. The asari areas were
lower than internal AsLS areas by about 58.15% to 59.55%, so the row verdicts
are `disagree_high_internal`.

However, this disagreement is mostly an absolute scale disagreement, not a
cross-sample pattern disagreement:

- internal AsLS RSD: 35.63%
- asari RSD: 36.28%
- internal-vs-asari Pearson across matched samples: 0.9995

## P2 AsLS Interpretation

P3 does not make P2b production-ready.

For the one matched P2 NO-GO family (`d3-dG-C8-MeIQx`), asari supports a
coherent feature at the same m/z/RT and strongly agrees with the cross-sample
pattern, but it reports a lower absolute area scale. That is useful shadow
evidence, but it does not decide whether internal AsLS or asari absolute area
is more correct.

For `d3-5-hmdC` and `d4-N6-2HE-dA`, asari produced no strict ISTD pair match
under the 10 ppm / 6 sec join gate, so P3 is inconclusive for those P2
baseline-truth cases.

## Asari Support Audit

The asari native feature table stores `rtime`, `rtime_left_base`, and
`rtime_right_base` in seconds. The P3 normalizer converts them to minutes
before matching, so the strict-match result is not caused by a minute/second
RT unit mismatch.

The area disagreement is more likely caused by a different integration
contract. asari's sample columns are not the same area definition as
XIC_Extractor. For `asari==1.17.0`, the default `peak_area=sum` path sums the
sample mass-track intensity over asari's own feature boundaries after its
batch alignment and mass-grid mapping. XIC_Extractor integrates direct RAW XIC
windows using its selected boundaries and baseline correction. The two area
scales are therefore not expected to be interchangeable absolute truths.

Target-by-target relaxed audit against `export/full_Feature_table.tsv`:

| Target | Best asari candidate | RT delta sec | Coverage | Pearson vs internal AsLS | Verdict |
|---|---|---:|---:|---:|---|
| d3-5-hmdC | F1059 | 23.8 | 6/8 | -0.413 | coverage_low |
| d3-5-medC | F172 | 13.3 | 5/8 | -0.260 | coverage_low |
| d4-N6-2HE-dA | F3215 | 66.1 | 6/8 | -0.031 | rt_mismatch |
| 15N5-8-oxodG | F2578 | 20.8 | 7/8 | 0.315 | pattern_not_supported |
| d3-N6-medA | F1531 | 30.0 | 8/8 | 0.845 | weak_relaxed_window_support |
| d3-dG-C8-MeIQx | F11885 | 3.1 | 7/8 | 0.999 | strong_pattern_support |

This explains why asari is only a limited reviewer here: it is an independent
untargeted feature detector, but for strict ISTD evidence it is not
target-aware, does not use the targeted MS/MS evidence chain, and often
selects a nearby but lower-coverage or weakly correlated feature. It can
support peak existence and sample-pattern coherence when it agrees, but it is
not a sufficient absolute-area adjudicator for P2b promotion.

## P6 OBI-Warp Escalation

Do not escalate P6 solely from this P3 result. The matched asari feature is
close in RT, but coverage is too sparse to diagnose a systematic RT correction
problem. Keep P6 as a later RT-shadow option only if a broader RT diagnostic
shows systematic drift or mismatch.

## Current Verdict

P3 is useful as `diagnostic_only` external shadow evidence and confirms the
temporary tooling can run asari without changing production RAW assumptions.
It is not a production gate and does not clear P2b.

Do not keep the P3 runner stack as live code in this Phase 1 branch. If a
future 85RAW or broader external-shadow comparison is needed, write a new
diagnostic plan from this findings note instead of treating the discarded P3
runner code as reusable infrastructure.
