from __future__ import annotations

import argparse
import json
import re
import tempfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

_NETWORK_COMMAND_PATTERNS = (
    r"\bnpx\b",
    r"\bnpm\s+install\b",
    r"\bpip\s+install\b",
    r"\buv\s+add\b",
    r"\buv\s+pip\s+install\b",
    r"\bgit\s+clone\b",
    r"\bgh\s+(?:pr|api|repo|release)\b",
)


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    next_action: str


@dataclass(frozen=True)
class DoctorReport:
    status: str
    workspace_root: str
    allowed_write_roots: tuple[str, ...]
    command: str
    findings: tuple[Finding, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["findings"] = [asdict(finding) for finding in self.findings]
        return payload


def classify_command(
    command: str,
    *,
    workspace_root: Path,
    allowed_write_roots: Sequence[Path],
) -> tuple[Finding, ...]:
    normalized = _normalize_command(command)
    lower = normalized.lower()
    findings: list[Finding] = []

    if re.search(r"<<\s*['\"]?[a-z_][a-z0-9_]*['\"]?", normalized, re.I):
        findings.append(
            Finding(
                severity="blocker",
                code="powershell_bash_heredoc",
                message="Command appears to use Bash heredoc syntax.",
                next_action=(
                    "Use PowerShell here-string piping, python -c, or a checked-in "
                    "script instead."
                ),
            )
        )
    if re.search(r"(^|\s)export\s+[A-Za-z_][A-Za-z0-9_]*=", normalized):
        findings.append(
            Finding(
                severity="blocker",
                code="powershell_export",
                message="Command uses Bash export syntax in a PowerShell repo.",
                next_action=(
                    "Use PowerShell environment syntax such as $env:NAME='value'."
                ),
            )
        )
    if "&&" in normalized:
        findings.append(
            Finding(
                severity="review",
                code="powershell_chain_operator",
                message="Command uses &&, which has caused shell drift in this repo.",
                next_action="Use semicolons or separate PowerShell lines.",
            )
        )

    if "start-process" in lower and _looks_like_long_raw_run(lower):
        findings.append(
            Finding(
                severity="blocker",
                code="background_long_raw_run",
                message=(
                    "Command launches a long RAW/alignment run through Start-Process."
                ),
                next_action=(
                    "Use the documented foreground command with timing heartbeat, "
                    "or get explicit approval for an external terminal/automation."
                ),
            )
        )

    if _looks_like_raw_alignment_command(lower) and not _uses_project_venv(lower):
        findings.append(
            Finding(
                severity="blocker",
                code="raw_runner_not_venv",
                message=(
                    "RAW/DLL alignment command is not using "
                    ".venv\\Scripts\\python.exe."
                ),
                next_action=(
                    "Run RAW/Thermo commands with .venv\\Scripts\\python.exe so "
                    "pythonnet and the DLL runtime match the documented contract."
                ),
            )
        )

    output_dir = _extract_option_path(normalized, "--output-dir")
    if output_dir is not None:
        resolved_output = _resolve_cli_path(output_dir, workspace_root)
        if not _is_under_any_root(resolved_output, allowed_write_roots):
            findings.append(
                Finding(
                    severity="review",
                    code="output_outside_writable_roots",
                    message=(
                        "Output path is outside documented writable roots: "
                        f"{output_dir}"
                    ),
                    next_action=(
                        "Prefer a task-specific output\\... path in the active "
                        "worktree or C:\\tmp; request approval only when external "
                        "writes are truly required."
                    ),
                )
            )

    if any(re.search(pattern, lower) for pattern in _NETWORK_COMMAND_PATTERNS):
        findings.append(
            Finding(
                severity="review",
                code="network_or_github_approval_needed",
                message="Command likely needs network or GitHub access.",
                next_action=(
                    "Confirm the network step is necessary, then request a narrow "
                    "approval/prefix instead of broad sandbox changes."
                ),
            )
        )

    if "danger-full-access" in lower or 'approval_policy = "never"' in lower:
        findings.append(
            Finding(
                severity="blocker",
                code="dangerous_runtime_config",
                message=(
                    "Command or config references a broad unsafe Codex runtime mode."
                ),
                next_action=(
                    "Use workspace-write/on-request by default; document a bounded "
                    "exception with rollback before changing runtime posture."
                ),
            )
        )

    return tuple(findings)


def build_environment_report(
    *,
    workspace_root: Path,
    allowed_write_roots: Sequence[Path],
    command: str = "",
    probe_write: bool = False,
) -> DoctorReport:
    resolved_workspace = workspace_root.resolve()
    resolved_roots = tuple(root.resolve() for root in allowed_write_roots)
    findings = list(
        classify_command(
            command,
            workspace_root=resolved_workspace,
            allowed_write_roots=resolved_roots,
        )
    )
    if probe_write:
        findings.extend(_probe_write_roots(resolved_roots))

    if any(finding.severity == "blocker" for finding in findings):
        status = "preflight_blocked"
    elif any(finding.severity == "review" for finding in findings):
        status = "needs_review"
    else:
        status = "ok"

    return DoctorReport(
        status=status,
        workspace_root=str(resolved_workspace),
        allowed_write_roots=tuple(str(root) for root in resolved_roots),
        command=command,
        findings=tuple(findings),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    workspace_root = args.workspace_root.resolve()
    allowed_write_roots = (
        tuple(root.resolve() for root in args.allowed_write_root)
        if args.allowed_write_root
        else _default_allowed_write_roots(workspace_root)
    )
    report = build_environment_report(
        workspace_root=workspace_root,
        allowed_write_roots=allowed_write_roots,
        command=args.command or "",
        probe_write=args.probe_write,
    )
    _print_report(report)
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(report.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )

    if not args.strict:
        return 0
    if any(finding.severity == "blocker" for finding in report.findings):
        return 2
    if any(finding.severity == "review" for finding in report.findings):
        return 1
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight common Codex sandbox, PowerShell, and RAW-run command "
            "friction before launching expensive workflows."
        )
    )
    parser.add_argument(
        "--command",
        default="",
        help="Command string to classify. No command is executed.",
    )
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--allowed-write-root",
        action="append",
        type=Path,
        default=None,
        help=(
            "Allowed write root. Repeatable. Defaults to workspace root and "
            "C:\\tmp when that is an absolute path on the current platform."
        ),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Optional JSON report path.",
    )
    parser.add_argument(
        "--probe-write",
        action="store_true",
        help="Create and remove tiny probe files in allowed write roots.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero for blocker/review findings.",
    )
    return parser.parse_args(argv)


def _print_report(report: DoctorReport) -> None:
    print(f"Sandbox doctor status: {report.status}")
    print(f"Workspace root: {report.workspace_root}")
    print("Allowed write roots:")
    for root in report.allowed_write_roots:
        print(f"  - {root}")
    if report.command:
        print(f"Command: {report.command}")
    if not report.findings:
        print("Findings: none")
        return
    print("Findings:")
    for finding in report.findings:
        print(f"  - [{finding.severity}] {finding.code}: {finding.message}")
        print(f"    next: {finding.next_action}")


def _normalize_command(command: str) -> str:
    return " ".join(command.replace("`", " ").split())


def _default_allowed_write_roots(workspace_root: Path) -> tuple[Path, ...]:
    roots = [workspace_root.resolve()]
    tmp_root = Path("C:/tmp")
    if tmp_root.is_absolute():
        roots.append(tmp_root.resolve())
    return tuple(roots)


def _looks_like_long_raw_run(lower_command: str) -> bool:
    return any(
        marker in lower_command
        for marker in (
            "scripts.run_alignment",
            "run_alignment.py",
            "--expected-sample-count 85",
            "--timing-live-output",
            "85raw",
        )
    )


def _looks_like_raw_alignment_command(lower_command: str) -> bool:
    return (
        (
            "scripts.run_alignment" in lower_command
            or "run_alignment.py" in lower_command
        )
        and ("--raw-dir" in lower_command or "--dll-dir" in lower_command)
    )


def _uses_project_venv(lower_command: str) -> bool:
    normalized = lower_command.replace("/", "\\")
    return ".venv\\scripts\\python.exe" in normalized


def _extract_option_path(command: str, option: str) -> str | None:
    pattern = re.compile(
        rf"(?:^|\s){re.escape(option)}(?:=|\s+)(?:\"([^\"]+)\"|'([^']+)'|(\S+))"
    )
    match = pattern.search(command)
    if match is None:
        return None
    return next(group for group in match.groups() if group is not None)


def _resolve_cli_path(path_text: str, workspace_root: Path) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = workspace_root / path
    return path.resolve()


def _is_under_any_root(path: Path, roots: Sequence[Path]) -> bool:
    resolved_path = path.resolve()
    for root in roots:
        resolved_root = root.resolve()
        if resolved_path == resolved_root or _is_relative_to(
            resolved_path, resolved_root
        ):
            return True
    return False


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _probe_write_roots(roots: Sequence[Path]) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for root in roots:
        try:
            root.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                prefix=".agent_sandbox_doctor_probe_",
                dir=root,
                delete=False,
            ) as handle:
                probe = Path(handle.name)
                handle.write("ok\n")
            probe.unlink()
        except OSError as exc:
            findings.append(
                Finding(
                    severity="review",
                    code="write_probe_failed",
                    message=f"Cannot write probe file under {root}: {exc}",
                    next_action=(
                        "Move outputs to an allowed worktree/C:\\tmp path or request "
                        "a narrow approval for the specific external write."
                    ),
                )
            )
    return tuple(findings)


if __name__ == "__main__":
    raise SystemExit(main())
