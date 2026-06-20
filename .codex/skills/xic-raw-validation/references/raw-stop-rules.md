# RAW Stop Rules

Stop and inspect instead of relaunching when:

- heartbeat stalls or exceeds expected runtime;
- preflight checks a weaker contract than the real command;
- output artifacts are missing or unexpectedly huge;
- the run cannot change the next action;
- the command uses an undocumented runner/path combination;
- PowerShell, sandbox, approval, or writable-root uncertainty appears.

When sandbox or command-shape uncertainty is the issue, run:

```powershell
python -m scripts.agent_sandbox_doctor --command "<command>"
```

The doctor is diagnostic only; it does not execute the command or replace user
approval.
