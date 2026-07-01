# Trigger Cases

Use these cases when checking whether `xic-performance-diagnosis` should route a
request.

## Should Trigger

- "The 85RAW preset is still slow; tell me the top bottlenecks from timing.json."
- "Before optimizing owner_backfill, inspect timing/live timing and decide the
  next exact-safe change."
- "We need to compare 8RAW baseline and optimized outputs before accepting a
  worker-budget change."
- "I do not have current timing artifacts; decide the minimal baseline command
  and stop rule."
- "Is ms1_index_hybrid ready as an opt-in fast-mode candidate?"
- "Check RAW locality and repeated extraction cost before we touch the pipeline."

## Should Not Trigger

- "What is a profiler?"
- "Speed up this unit test helper with no XIC timing or validation surface."
- "Review a matrix activation plan that has no runtime or call-cost question."
- "Launch 85RAW now." Use `xic-raw-validation` for launch/acceptance preflight;
  this skill can only define the performance decision the run should close.
- "Can this diagnostic evidence advance product tier?" Read or update the
  productization control plane after performance evidence exists.

## Borderline

- If the request is a generic performance concept question, answer directly or
  use the global `performance-optimization-discipline` skill.
- If the request is implementation after a performance diagnosis already exists,
  use this skill only to restate the artifact-backed gate, then use
  `xic-architecture-preflight` before edits.
- If timing artifacts are missing but the task is XIC preset/runtime work, this
  skill should still trigger and usually return `baseline_needed`.
