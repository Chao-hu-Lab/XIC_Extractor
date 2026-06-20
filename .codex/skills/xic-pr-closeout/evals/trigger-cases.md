# Trigger Cases

## Positive Triggers

- "幫我準備 XIC PR closeout，包含 validation tier 和 residual risk。"
- "Update the PR body for this RAW-backed validation branch."
- "收尾這個 XIC branch，說清楚 output artifacts 和未驗證風險。"
- "This PR changes workflow rules; write the durable review narrative."

## Negative Triggers

- "跑 git status。"
- "這個 tiny commit 幫我 commit，不需要 PR body。"
- "幫我查 GitHub CI 狀態，不用 closeout narrative。"
- "純 merge/pull/push sync，不需要說明文字。"

## Near Neighbors

- Use global `pr-closeout` for non-XIC branches.
- Use `create-pr` or GitHub tooling for pure PR mechanics.
- Use `xic-goal-execution` when the branch still needs an executable finish-line
  goal before PR closeout.
