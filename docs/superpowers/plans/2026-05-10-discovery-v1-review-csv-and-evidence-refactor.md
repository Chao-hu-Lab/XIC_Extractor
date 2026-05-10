# Discovery V1 Review CSV and Evidence Refactor Plan Index

> **For agentic workers:** Do not execute this index file directly. Execute the smaller implementation plans listed below in order.

**Goal:** Split the original oversized discovery v1 refactor plan into focused, reviewable implementation plans.

**Architecture:** The original plan mixed three independent concerns: human review CSV output, evidence-score configuration, and numeric MS1 trace support. Each concern now has its own plan so implementation, review, and regression analysis stay bounded.

**Tech Stack:** Python, pytest, csv, dataclasses, existing `xic_extractor.discovery` modules.

---

## Why This Was Split

The original revision tried to implement all of the following at once:

- Dual CSV output for human review and full downstream alignment.
- Evidence-score weights and thresholds as configurable dataclasses.
- A numeric MS1 trace-quality metric used by scoring.

Those changes are related, but they fail and regress differently. Keeping them in one large task makes context usage high and makes it hard to identify which layer caused a real-data change.

## Execution Order

Run these plans in order:

1. [Plan A: Discovery Review CSV Dual Output](2026-05-10-discovery-review-csv-dual-output-plan.md)
2. [Plan B: Discovery Evidence Config Foundation](2026-05-10-discovery-evidence-config-plan.md)
3. [Plan C: Discovery MS1 Scan Support Scoring](2026-05-10-discovery-ms1-scan-support-plan.md)

## Design Decisions Carried Forward

### Brief CSV Is A Review Index

`discovery_review.csv` is not a smaller full CSV. It is the human review entry point. It should answer:

- Is this row worth inspecting?
- Why is it ranked here?
- How do I locate it in full CSV or Xcalibur?

The brief CSV should include only base review information. Advanced diagnostics remain in `discovery_candidates.csv`.

### Brief CSV Columns

The brief CSV should use these columns:

```text
review_priority
evidence_tier
evidence_score
ms2_support
ms1_support
rt_alignment
family_context
candidate_id
precursor_mz
best_seed_rt
ms1_area
seed_event_count
neutral_loss_tag
review_note
```

`review_note` is intentionally shorter than the full `reason` field. It summarizes why the row is worth review without becoming another diagnostics column.

### Full CSV Remains Alignment-Ready

`discovery_candidates.csv` keeps full review and provenance fields for downstream alignment and developer debugging. The brief CSV must not replace it in standard archival runs.

### Evidence Config Belongs Outside Models Long-Term

Evidence weights and thresholds belong in `xic_extractor/discovery/evidence_config.py`, not permanently in `models.py`. Normal users should eventually choose a profile such as `loose`, `default`, or `strict`; raw weights are developer-facing.

Plan B builds the config foundation while avoiding premature tuning of `loose` and `strict`.

### MS1 Scan Support Is Not Full Trace Quality

The numeric metric from scan count should be named `ms1_scan_support_score`, not `ms1_trace_quality_score`. Scan support is useful evidence, but it is not equivalent to chromatographic trace quality.

Future trace-quality evidence may add continuity, edge recovery, or baseline recovery as separate metrics.

## Out Of Scope

- Cross-sample alignment.
- Discovery output performance levels and candidate budget controls. See [Discovery Output Performance and Candidate Budget Spec](../specs/2026-05-10-discovery-output-performance-spec.md).
- GUI changes.
- RAW reader or XIC scanning performance.
- Scoring weight tuning beyond moving existing defaults behind a config object.

