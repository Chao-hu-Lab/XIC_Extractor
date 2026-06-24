# XIC Performance Artifact Contract

This checklist is the repo-local companion to the global
`performance-optimization-discipline` skill. It exists because XIC performance
work is controlled by concrete artifacts, RAW I/O cost, and product parity.

## Timing Source Priority

Prefer timing sources in this order:

1. Fresh stage timing from the exact command under discussion.
2. `timing.live.json` / heartbeat timing for long-running foreground RAW runs.
3. `timing.json` / preset summary timing.
4. Stage replay timing when it uses matching input artifact hashes.
5. RAW locality or call-count summaries that explain the timing.
6. `cProfile` only for the covered code region. Do not treat base-profile output
   as full preset timing when the command does not wrap the tail stage.

If the top bottleneck changes depending on timing source, report
`inconclusive` and collect a narrower measurement.

## Artifact Inventory

For 8RAW or 85RAW performance work, inspect or name the absence of:

- output directory and command;
- `timing.json`;
- `timing.live.json` or heartbeat log when available;
- preset summary JSON;
- RAW locality summary;
- profiler sidecars and the code region they cover;
- published matrix TSV/workbook;
- review queue TSV;
- matrix identity sidecars;
- manifests and artifact hashes;
- standard-peak summary/status artifacts when relevant;
- replay manifests for stage-only diagnosis.

Do not call diagnostic sidecars product evidence unless the active contract says
they are part of delivery.

Inventory should be narrow and filename-driven. Prefer `rg --files` patterns,
known output roots, preset labels, and sidecar names before opening large TSVs or
walking run directories. If only a few fields are needed from a large artifact,
use a schema-aware or targeted reader instead of loading the entire table.

## Call-Cost Model

Classify bottlenecks by dominant cost:

- RAW opens and Thermo DLL setup;
- XIC extraction request count;
- repeated extraction over the same sample/window;
- per-chunk replay of matrix-only evidence;
- repeated large TSV/CSV scans for small lookups;
- sorting/grouping/joining large tables;
- peak finding, crop, smoothing, correlation, or audit loops;
- matrix/write/report rendering;
- overlay/PDF generation;
- cache/index build time versus reuse benefit;
- worker budget, process startup, scheduling, and nondeterministic ordering;
- memory pressure from full-table loads or unbounded caches.

The recommendation must name which cost is removed, reduced, batched, cached, or
parallelized.

## Workload Class

State the workload because it changes the best optimization:

- `8RAW`: fast feedback and parity gate. Use before 85RAW when changing exact
  paths.
- `85RAW`: stress oracle for wall-clock cost and locality. Do not launch via
  background `Start-Process` from Codex shell without explicit approval.
- `stage_replay`: targeted diagnosis filter, not readiness evidence.
- `one_time_import`: prefer simple batching/streaming; persistent indexes may
  not pay back.
- `repeated_modeling`: indexes, replay manifests, reusable intermediates, and
  cacheable locality summaries can pay back quickly.
- `production_preset`: requires public-output parity or approved expected diff.
- `fast_mode_candidate`: opt-in only; exact outputs remain default.

If the workload is `baseline_needed`, stop at command shape, expected artifacts,
and decision this run can close. Do not turn missing evidence into speculative
implementation.

## Correctness Oracles

Choose the oracle before editing:

- byte-identical public TSVs or stable normalized hash comparison;
- published matrix parity;
- review queue row-count/order/status parity;
- matrix identity sidecar parity;
- manifest/input SHA parity;
- workbook/report schema and public sheet parity;
- focused unit tests for crop boundaries, fallback behavior, worker ordering,
  replay reuse, and output writers;
- expected-diff packet for fast mode or intentionally changed behavior.

If selected peak, selected area, counted detections, confidence/reason, active
lane, schema, or matrix identity changes without an approved expected diff,
reject the optimization.

## Exact-Safe Opportunities

Prefer these before semantic changes:

- global summary reuse instead of per-chunk repeated RAW/XIC evidence generation;
- sample-local caches for scan-to-RT and RT-window lookups;
- monotonic `searchsorted` slice views with fallback for non-monotonic, NaN, or
  reversed traces;
- replacing repeated full-table reads with keyed indexes or targeted loads;
- batching extraction requests by sample/window locality;
- stable worker-budget tuning with fixed output ordering;
- reuse of existing replay manifests and artifact hashes;
- moving reusable mechanics from `tools/diagnostics/` orchestration into package
  helpers only when the third repeated implementation appears.

## Expected-Diff And Fast-Mode Packet

For non-exact paths, produce an expected-diff packet before accepting results:

- feature/family/sample key coverage;
- missing/extra cell counts;
- status delta;
- apex drift;
- boundary drift;
- area drift and correlation;
- counted-detection delta;
- identity/confidence/reason delta;
- held/failed bucket;
- runtime and call-count delta;
- rollback path and opt-in profile name.

The result can be `diagnostic_only` or `fast_mode_candidate`; it is not default
production behavior without a separate activation decision.

## Stop Rules

Stop or report `inconclusive` when:

- baseline timing is stale, missing, or does not cover the suspected stage;
- warm/cold cache state differs and explains the improvement;
- output folders or chunks are dirty/reused ambiguously;
- artifact hashes do not match replay inputs;
- public TSV/workbook/matrix/identity outputs differ unexpectedly;
- worker parallelism changes row order, nondeterminism, or status values;
- the change improves total runtime but not the target bottleneck;
- 8RAW exact path fails before 85RAW validation;
- artifact discovery requires broad, expensive directory scans before a concrete
  run folder or sidecar target is identified.

## Minimal Final Report

Use this shape:

```markdown
Verdict:
Workload:
Timing source:
Top bottleneck:
Optimization lane:
Expected call-cost change:
Correctness gate:
Validation run:
Result:
Residual risk:
Next bottleneck/action:
```
