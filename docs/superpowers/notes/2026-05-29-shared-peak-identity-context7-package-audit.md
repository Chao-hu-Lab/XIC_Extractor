# Shared Peak Identity Evidence Context7 Package Audit

**Date:** 2026-05-29
**Status:** Task 0 audit, diagnostic/planning only
**Branch:** `codex/shared-peak-identity-evidence`
**Related:** GitHub issue #74 and
`docs/superpowers/notes/2026-05-29-shared-peak-identity-context7-task0-note.md`

## Verdict

The current shared peak identity evidence phase should treat `scipy.signal` as
the primary package-semantics risk. `find_peaks_cwt`, `find_peaks`,
`peak_widths`, and `savgol_filter` sit directly on peak proposal, shape, apex,
and boundary behavior.

`numpy` is a second-tier risk because it defines area integration, finite/NaN
handling, medians, argmax/argmin, and hand-rolled correlation metrics. Context7
returned useful NaN-propagation reminders but did not return enough detail for
`trapezoid`, `argmax`, or tie behavior in this pass, so those need direct
official-doc follow-up if the implementation changes area, apex tie-breaking,
or missing-value semantics.

`openpyxl` is relevant for workbook-derived validation oracles. It should not
drive peak identity logic, but it can affect whether workbook evidence is read
as cached values, formulas, the intended named sheet, or an accidental active
sheet.

No direct production import of `pandas` or `sklearn` was found in the current
repo scan. Do not add Context7 gates for them until the implementation actually
introduces or changes such usage.

## Current Environment Snapshot

Direct dependencies from `pyproject.toml`:

- `PyQt6 >= 6.6`
- `matplotlib >= 3.10.9`
- `numpy >= 1.26`
- `openpyxl >= 3.1`
- `pythonnet >= 3.0`
- `scipy >= 1.11`

Resolved runtime versions checked from `.venv\Scripts\python.exe`:

- `scipy 1.17.1`
- `numpy 2.4.4`
- `openpyxl 3.1.5`
- `matplotlib 3.10.9`

The first version probe failed inside the sandbox while importing NumPy C
extensions with `DLL load failed ... 存取被拒`; the same query succeeded with
escalation. Treat future NumPy/SciPy runtime probes as sandbox-sensitive.

## Context7 Official-Docs Findings

### SciPy

Context7 library: `/websites/scipy_doc_scipy`

Official-doc sources returned:

- <https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks_cwt.html>
- <https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html>
- <https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.peak_widths.html>

Relevant current usages:

- `xic_extractor/peak_detection/cwt.py`
  - `scipy.signal.find_peaks_cwt`
  - current explicit parameters: `widths`, `min_length`, `min_snr=1`
  - current implicit defaults: `wavelet`, `max_distances`, `gap_thresh`,
    `noise_perc`, `window_size`
- `xic_extractor/peak_detection/local_minimum.py`
  - `scipy.signal.find_peaks`
  - current use finds local maxima; repo code adds endpoint handling and
    computes boundaries itself.
- `xic_extractor/peak_detection/legacy_savgol.py`
  - `scipy.signal.savgol_filter`
  - `scipy.signal.find_peaks`
  - current use smooths first, then finds prominent peaks on the smoothed
    signal.
- `xic_extractor/peak_detection/integration.py`
  - `scipy.signal.peak_widths`
  - current use converts interpolated `left_ips` / `right_ips` into integer
    bounds with floor/ceil and integrates raw intensity inside those bounds.
- `xic_extractor/baseline.py`
  - `scipy.sparse.diags`
  - `scipy.sparse.linalg.spsolve`
  - AsLS behavior is package-sensitive but belongs to the AsLS / baseline track
    unless this branch changes baseline-derived evidence.

Decision impact:

- `find_peaks_cwt` is not a generic "peak shape is real" oracle. Official
  semantics depend on expected-width coverage and ridge-line persistence across
  CWT widths. `max_distances`, `gap_thresh`, `min_length`, `min_snr`,
  `noise_perc`, and `window_size` can all change which peaks appear.
- The current `_cwt_widths()` maps RT sampling and
  `resolver_peak_duration_max` into CWT widths. That is a reasonable audit
  starting point, but it must be recorded as an observer configuration, not
  treated as calibrated production evidence.
- `peak_widths` measures width at a relative prominence height and returns
  interpolated intersections. The current floor/ceil conversion means boundaries
  are a deterministic approximation of a prominence contour on the input
  signal, not the same thing as manual integration boundaries.
- `find_peaks` returns local maxima under optional property constraints. In the
  local-minimum resolver, boundary decisions are repo logic, not SciPy logic.
- Context7 did not return enough `savgol_filter` detail in this pass to settle
  window/edge semantics. If `legacy_savgol` becomes part of the next
  implementation slice, run a narrower official-doc lookup before changing it.

Task 0 consequence:

- Next plan should keep CWT as `audit_only` or `observer` unless a calibration
  task explicitly records CWT width grid, ridge parameters, noise parameters,
  expected peak-width strata, and manual-oracle agreement.
- Any shared evidence vector that includes CWT must store enough provenance to
  reproduce the observed support: at minimum `widths` summary, `min_length`,
  `min_snr`, `noise_perc`, `window_size`, `max_distances` policy, and whether
  the CWT proposal matched the selected apex or introduced a new candidate.

### NumPy

Context7 library: `/numpy/numpy`

Context7 returned official project docs but only partially answered the target
API question. The useful finding for this branch is that normal NumPy arithmetic
and reductions can propagate NaN unless the code intentionally uses NaN-aware
variants such as `np.nansum`.

Relevant current usages:

- `np.asarray(..., dtype=float)` throughout peak detection, alignment,
  backfill, and trace loading.
- `np.isfinite` in AsLS input validation.
- `np.max`, `np.min`, `np.argmax`, `np.argmin`, `np.median`, `np.diff`, and
  `np.abs` in peak/trace metrics.
- `np.trapezoid` in `integrate_area_counts_seconds()`.
- `math.log10` and hand-rolled Pearson correlation in
  `xic_extractor/alignment/validation_compare.py`.

Decision impact:

- Existing AsLS explicitly rejects non-finite inputs, which is good.
- Not every trace/evidence path has an equivalent finite-value guard. If the
  next implementation compares shape, area, or pattern across cells, it should
  decide whether non-finite values are invalid evidence, missing evidence, or a
  diagnostic bug.
- Area integration with `np.trapezoid` and apex tie behavior with `np.argmax`
  were not sufficiently documented by this Context7 pass. Do not change area
  semantics, apex tie-breaking, or NaN policy without a narrower official-doc
  check and regression tests.

Task 0 consequence:

- Shared evidence-chain work should add explicit finite/missing-value status
  fields rather than letting NaN silently propagate into scores.
- If the slice computes new area, similarity, or correlation values, document
  the exact NumPy/statistical semantics in the spec or implementation note.

### openpyxl

Context7 library: `/websites/openpyxl_readthedocs_io_en_stable`

Official-doc source returned:

- <https://openpyxl.readthedocs.io/en/stable/_modules/openpyxl/reader/excel.html>
- <https://openpyxl.readthedocs.io/en/stable/optimized.html>

Relevant current usages:

- `load_workbook(..., read_only=True, data_only=True)` in targeted benchmark,
  drift evidence, RT normalization, false-missing fixture, and legacy workbook
  loaders.
- `iter_rows(values_only=True)` for workbook-derived row extraction.
- Named sheet access such as `"Targets"` and `"XIC Results"`.
- Some older scripts use `workbook.active` or explicit merged-cell handling.

Decision impact:

- `data_only=True` reads cached formula results stored by the last Excel
  calculation, not recalculated formulas. Workbook-derived evidence must not
  assume formulas were recalculated by openpyxl.
- `read_only=True` returns read-only / lazy worksheet objects and official docs
  say the workbook should be closed after reading.
- `iter_rows(values_only=True)` returns values, not Cell objects, so formatting,
  comments, and merged-cell metadata are not available in that path.
- Named sheet access is safer than `workbook.active` for machine evidence. Any
  future oracle loader should prefer explicit sheet names.

Task 0 consequence:

- Any manual-oracle workbook loader added in this branch should use explicit
  sheet names, `data_only=True` only when cached formula values are acceptable,
  and a close pattern.
- If merged cells matter, do not use `values_only=True` alone; add explicit
  merged-cell handling or normalize the workbook to TSV before it enters the
  evidence chain.

## Lower-Priority Packages For This Branch

- `matplotlib`: currently diagnostic rendering / plots. It can affect visual
  review, but not machine evidence unless plot-derived review state becomes an
  input, which it should not.
- `PyQt6`: GUI/event loop only for this phase.
- `pythonnet`: RAW reader runtime. Important operationally, but current Task 0
  should validate RAW behavior through real trace artifacts and existing RAW
  validation rules rather than treating pythonnet docs as the identity oracle.

## Recommended Next Step

Before writing the next shared evidence-chain spec / goal / plan:

1. Declare CWT mode as `audit_only observer` for the next slice unless the slice
   explicitly calibrates CWT against manual rows.
2. Add a package-semantics subsection to the spec with the SciPy / NumPy /
   openpyxl findings above.
3. If the implementation introduces new shape similarity, MS2 pattern
   similarity, CWT scoring, or NumPy correlation/area calculations, run a
   narrower Context7 official-doc lookup for that exact API before coding.
4. Keep AsLS / baseline package semantics out of this branch unless the shared
   evidence vector starts consuming baseline-derived fields as identity
   evidence.
