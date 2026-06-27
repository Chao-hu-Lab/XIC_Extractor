from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass

CONTROL_PLANE_PATH = "docs/superpowers/plans/2026-06-15-productization-control-plane.md"
HANDOFF_CURRENT_DIR = "docs/superpowers/handoffs/current/"
HANDOFF_ARCHIVE_DIR = "docs/superpowers/handoffs/archive/"
PRODUCTIZATION_STATUS_ANCHOR_PATH = (
    "docs/superpowers/productization/status/cc-framework-improvements-productization.md"
)
# Backward-compatible import name for existing hook code. The file is no longer
# a handoff; keep the alias until hook call sites are renamed in a focused pass.
PRODUCTIZATION_STATUS_HANDOFF_PATH = PRODUCTIZATION_STATUS_ANCHOR_PATH
HANDOFF_MAX_LINES = 200

PRODUCT_SURFACE_PATHS = [
    "README.md",
    "AGENTS.md",
    "docs/architecture-contract.md",
    "docs/product/",
    "docs/agent/product-validation-contract.md",
    "docs/agent/architecture-public-contracts.md",
    "docs/superpowers/specs/",
    "docs/superpowers/plans/",
    "xic_extractor/extractor.py",
    "xic_extractor/signal_processing.py",
    "xic_extractor/output/",
    "xic_extractor/alignment/",
    "xic_extractor/extraction/",
    "xic_extractor/peak_detection/",
    "xic_extractor/configuration/",
    "xic_extractor/settings_schema.py",
    "scripts/",
    "gui/",
]

DOC_PLACEMENT_MARKER = "Doc placement:"
DOC_REPO_OWNER_MARKER = "Repo owner:"
DOC_PLACEMENT_VALUES = {
    "formal_repo_doc",
    "repo_active_stub",
    "branch_closeout_summary",
    "repo_stub_plus_obsidian",
    "private_obsidian_note",
    "ignored_artifact",
    "throwaway_scratch",
}
DOC_PLACEMENTS_REQUIRING_REPO_OWNER = {
    "formal_repo_doc",
    "repo_active_stub",
    "branch_closeout_summary",
    "repo_stub_plus_obsidian",
    "ignored_artifact",
}
NON_REPO_DOC_PLACEMENTS = {
    "private_obsidian_note",
    "throwaway_scratch",
}
DOC_CANONICAL_OWNER_DIRS = [
    "docs/product/",
    "docs/agent/",
    "docs/engineering-skills/",
    "docs/solutions/",
    "docs/superpowers/specs/",
    "docs/superpowers/validation/",
    "docs/superpowers/fixtures/",
    "docs/superpowers/productization/",
    "docs/superpowers/file-management/",
    "docs/superpowers/closeouts/",
    "docs/validation/",
    "tests/fixtures/",
]
DOC_CANONICAL_OWNER_FILES = {
    "AGENTS.md",
    "CONTEXT.md",
    "README.md",
    "docs/architecture-contract.md",
    "docs/confidence-reason-precedence-contract.md",
    "docs/deepresearch/README.md",
    "docs/diagnostic-ledger.md",
    "docs/lcms-msms-evidence-rules.md",
    "docs/project-layout.md",
    "docs/research-line-triage.md",
    "docs/superpowers/README.md",
    PRODUCTIZATION_STATUS_HANDOFF_PATH,
    "docs/superpowers/notes/backfill_broad_autowrite_feasibility_gate_v1.md",
    "docs/superpowers/plans/2026-06-15-productization-control-plane.md",
    "docs/superpowers/plans/README.md",
}
HIGH_RISK_DOC_DIRS = [
    "docs/deepresearch/",
    "docs/superpowers/deepresearch/",
    "docs/superpowers/handoffs/current/",
    "docs/superpowers/handoffs/archive/",
    "docs/superpowers/notes/",
    "docs/superpowers/plans/",
    "docs/superpowers/reports/",
]
PRIVATE_HISTORY_SIGNALS = [
    "implementation diary",
    "command log",
    "command transcript",
    "review rationale",
    "branch sequencing",
    "development diary",
    "private obsidian",
    "raw transcript",
]
CLOSEOUT_DIR = "docs/superpowers/closeouts/"
MISPLACED_HANDOFF_PUBLIC_RECORD_PATTERNS = [
    re.compile(r"productization", re.IGNORECASE),
    re.compile(r"closeout-summary", re.IGNORECASE),
    re.compile(r"file-management", re.IGNORECASE),
    re.compile(r"git-rm-candidate-manifest", re.IGNORECASE),
    re.compile(r"public-surface-stub-audit", re.IGNORECASE),
    re.compile(r"source-of-truth-queue", re.IGNORECASE),
    re.compile(r"historical-referrer", re.IGNORECASE),
]
GIT_GLOBAL_OPTIONS_WITH_VALUE = {
    "-C",
    "-c",
    "--config-env",
    "--exec-path",
    "--git-dir",
    "--namespace",
    "--super-prefix",
    "--work-tree",
}
GIT_COMMIT_OPTIONS_WITH_VALUE = {
    "-m",
    "-F",
    "-C",
    "-c",
    "--message",
    "--file",
    "--reuse-message",
    "--reedit-message",
    "--author",
    "--date",
    "--cleanup",
    "--fixup",
    "--squash",
    "--template",
    "--trailer",
}
SHELL_COMMAND_FLAGS = {"-c", "-command", "/c"}
POSIX_SHELL_EXECUTABLES = {"bash", "bash.exe", "sh", "sh.exe"}
POWERSHELL_EXECUTABLES = {
    "powershell",
    "powershell.exe",
    "pwsh",
    "pwsh.exe",
}
CMD_EXECUTABLES = {"cmd", "cmd.exe"}


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def normalize_path_text(text: str) -> str:
    normalized = text.replace("\\", "/")
    while "/./" in normalized:
        normalized = normalized.replace("/./", "/")
    return normalized


def path_match_text(text: str) -> str:
    normalized = normalize_path_text(text)
    return normalized.replace("../", "").replace("./", "")


def mentions_path(text: str, path: str) -> bool:
    normalized_path = normalize_path_text(path).lstrip("./")
    return normalized_path in path_match_text(text)


def mentions_any_path(text: str, paths: list[str]) -> bool:
    return any(mentions_path(text, path) for path in paths)


def path_is_under(path: str, root: str) -> bool:
    normalized_path = normalize_path_text(path).lstrip("./")
    normalized_root = normalize_path_text(root).lstrip("./")
    if normalized_root.endswith("/"):
        return normalized_path.startswith(normalized_root)
    return normalized_path == normalized_root


def touches_product_surface(paths: list[str]) -> bool:
    return any(
        path_is_under(path, root)
        for path in paths
        for root in PRODUCT_SURFACE_PATHS
    )


def touches_control_plane(paths: list[str]) -> bool:
    return any(path_is_under(path, CONTROL_PLANE_PATH) for path in paths)


def touches_handoff(paths: list[str]) -> bool:
    return any(path_is_under(path, HANDOFF_CURRENT_DIR) for path in paths)


def is_productization_status_handoff(path: str) -> bool:
    return path_is_under(path, PRODUCTIZATION_STATUS_HANDOFF_PATH)


def branch_slug(branch: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", branch.strip().lower()).strip("-")


def touched_handoff_paths(paths: list[str]) -> list[str]:
    return [
        normalize_path_text(path).lstrip("./")
        for path in paths
        if path_is_under(path, HANDOFF_CURRENT_DIR)
    ]


def is_markdown_path(path: str) -> bool:
    normalized = normalize_path_text(path).lower()
    return normalized.endswith((".md", ".markdown"))


def is_repo_doc_path(path: str) -> bool:
    normalized = normalize_path_text(path).lstrip("./")
    return is_markdown_path(normalized) and (
        normalized in DOC_CANONICAL_OWNER_FILES or normalized.startswith("docs/")
    )


def is_branch_closeout_summary_path(path: str) -> bool:
    normalized = normalize_path_text(path).lstrip("./").lower()
    return normalized.startswith(CLOSEOUT_DIR) and normalized.endswith(
        "_branch-closeout-summary.md"
    )


def is_public_handoff_archive_evidence_path(path: str) -> bool:
    return False


def is_misplaced_handoff_public_record_path(path: str) -> bool:
    normalized = normalize_path_text(path).lstrip("./")
    if not (
        normalized.startswith(HANDOFF_CURRENT_DIR)
        or normalized.startswith(HANDOFF_ARCHIVE_DIR)
    ):
        return False
    filename = os.path.basename(normalized)
    return any(
        pattern.search(filename)
        for pattern in MISPLACED_HANDOFF_PUBLIC_RECORD_PATTERNS
    )


def is_canonical_doc_owner_path(path: str) -> bool:
    normalized = normalize_path_text(path).lstrip("./")
    if normalized in DOC_CANONICAL_OWNER_FILES:
        return True
    if is_public_handoff_archive_evidence_path(normalized):
        return True
    return any(path_is_under(normalized, root) for root in DOC_CANONICAL_OWNER_DIRS)


def is_high_risk_repo_doc_path(path: str) -> bool:
    normalized = normalize_path_text(path).lstrip("./")
    if normalized in DOC_CANONICAL_OWNER_FILES:
        return False
    if is_branch_closeout_summary_path(normalized):
        return False
    return any(path_is_under(normalized, root) for root in HIGH_RISK_DOC_DIRS)


def marker_value(text: str, marker: str) -> str:
    marker_lower = marker.lower()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(marker_lower):
            return stripped.split(":", 1)[1].strip().strip("`")
    return ""


def doc_placement_value(text: str) -> str:
    return marker_value(text, DOC_PLACEMENT_MARKER)


def repo_owner_value(text: str) -> str:
    return marker_value(text, DOC_REPO_OWNER_MARKER)


def doc_placement_requires_repo_owner(placement: str) -> bool:
    return placement in DOC_PLACEMENTS_REQUIRING_REPO_OWNER


def doc_placement_is_non_repo(placement: str) -> bool:
    return placement in NON_REPO_DOC_PLACEMENTS


def has_private_history_signal(text: str) -> bool:
    lowered = text.lower()
    return any(signal in lowered for signal in PRIVATE_HISTORY_SIGNALS)


def is_git_add_command(command: str) -> bool:
    return bool(git_subcommand_tails(command, "add"))


def is_git_commit_command(command: str) -> bool:
    return bool(git_subcommand_tails(command, "commit"))


def git_commit_tail(command: str) -> str:
    tails = git_subcommand_tails(command, "commit")
    if not tails:
        return ""
    return " ".join(tails[0])


def git_commit_uses_autostage_or_pathspec(command: str) -> bool:
    return any(
        commit_tail_uses_autostage_or_pathspec(tail)
        for tail in git_subcommand_tails(command, "commit")
    )


def split_shell_words(command: str) -> list[str]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        return list(lexer)
    except ValueError:
        try:
            return shlex.split(command, posix=True)
        except ValueError:
            return command.split()


def clean_shell_token(token: str) -> str:
    return token.strip().strip("'\"").strip()


def command_word(token: str) -> str:
    return clean_shell_token(token).strip("&;|()")


def token_basename(token: str) -> str:
    cleaned = normalize_path_text(command_word(token))
    return cleaned.rsplit("/", 1)[-1].lower()


def is_shell_separator(token: str) -> bool:
    cleaned = clean_shell_token(token)
    return bool(cleaned) and all(char in ";&|()" for char in cleaned)


def is_git_executable(token: str) -> bool:
    return token_basename(token) in {"git", "git.exe"}


def is_shell_executable(token: str) -> bool:
    return token_basename(token) in {
        "bash",
        "bash.exe",
        "cmd",
        "cmd.exe",
        "powershell",
        "powershell.exe",
        "pwsh",
        "pwsh.exe",
        "sh",
        "sh.exe",
    }


def is_shell_command_flag(shell_token: str, option: str) -> bool:
    shell = token_basename(shell_token)
    option = option.lower()
    if shell in POSIX_SHELL_EXECUTABLES:
        return option == "-c" or (
            option.startswith("-")
            and not option.startswith("--")
            and "c" in option[1:]
        )
    if shell in POWERSHELL_EXECUTABLES:
        return option in {"-c", "-command"}
    if shell in CMD_EXECUTABLES:
        return option == "/c"
    return option in SHELL_COMMAND_FLAGS


def skip_git_global_options(tokens: list[str], index: int) -> int:
    while index < len(tokens):
        token = command_word(tokens[index])
        if not token or is_shell_separator(tokens[index]):
            return index
        option = token.split("=", 1)[0]
        if option in GIT_GLOBAL_OPTIONS_WITH_VALUE:
            index += 1 if "=" in token else 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return index
    return index


def command_tail_until_separator(tokens: list[str], index: int) -> list[str]:
    tail: list[str] = []
    while index < len(tokens) and not is_shell_separator(tokens[index]):
        tail.append(command_word(tokens[index]))
        index += 1
    return tail


def next_command_start(tokens: list[str], index: int) -> int:
    while index < len(tokens) and not is_shell_separator(tokens[index]):
        index += 1
    return index


def nested_shell_commands(tokens: list[str]) -> list[str]:
    commands: list[str] = []
    for index, token in enumerate(tokens):
        if not is_shell_executable(token):
            continue
        for option_index in range(index + 1, len(tokens)):
            option = command_word(tokens[option_index]).lower()
            if (
                is_shell_command_flag(token, option)
                and option_index + 1 < len(tokens)
            ):
                commands.append(" ".join(tokens[option_index + 1 :]))
                break
    return commands


def git_subcommand_tails(
    command: str,
    subcommand: str,
    *,
    depth: int = 0,
) -> list[list[str]]:
    if depth > 3:
        return []
    tokens = split_shell_words(command)
    tails: list[list[str]] = []
    index = 0
    at_command_start = True
    subcommand_lower = subcommand.lower()
    while index < len(tokens):
        token = command_word(tokens[index])
        if not token:
            index += 1
            continue
        if is_shell_separator(tokens[index]):
            at_command_start = True
            index += 1
            continue
        if at_command_start and is_git_executable(token):
            subcommand_index = skip_git_global_options(tokens, index + 1)
            if (
                subcommand_index < len(tokens)
                and command_word(tokens[subcommand_index]).lower() == subcommand_lower
            ):
                tails.append(command_tail_until_separator(tokens, subcommand_index + 1))
            index = next_command_start(tokens, index + 1)
            continue
        at_command_start = False
        index += 1

    for nested in nested_shell_commands(tokens):
        if nested and nested != command:
            tails.extend(git_subcommand_tails(nested, subcommand, depth=depth + 1))
    return tails


def short_option_uses_autostage(token: str) -> bool:
    return token.startswith("-") and not token.startswith("--") and "a" in token[1:]


def commit_tail_uses_autostage_or_pathspec(tokens: list[str]) -> bool:
    index = 0
    after_separator = False
    while index < len(tokens):
        token = command_word(tokens[index])
        if not token:
            index += 1
            continue
        if after_separator:
            return True
        if token == "--":
            after_separator = True
            index += 1
            continue
        option = token.split("=", 1)[0]
        if token == "--all" or token.startswith("--all="):
            return True
        if option == "--pathspec-from-file":
            return True
        if short_option_uses_autostage(token):
            return True
        if token.startswith("-"):
            if option in GIT_COMMIT_OPTIONS_WITH_VALUE and "=" not in token:
                index += 2
            else:
                index += 1
            continue
        return True
    return False


def is_shell_command_event(tool_name: str, command: str) -> bool:
    if not command.strip():
        return False
    lowered = tool_name.lower()
    if any(name in lowered for name in ("apply_patch", "edit", "write")):
        return False
    return True


def repo_root_from_cwd(cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd or ".",
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return cwd or "."
    if result.returncode != 0:
        return cwd or "."
    return result.stdout.strip() or cwd or "."


def run_docs_placement_guard(cwd: str) -> CommandResult:
    override = os.environ.get("XIC_DOCS_PLACEMENT_GUARD_EXIT_CODE")
    if override is not None:
        try:
            returncode = int(override)
        except ValueError:
            returncode = 1
        return CommandResult(
            returncode=returncode,
            stdout=os.environ.get("XIC_DOCS_PLACEMENT_GUARD_STDOUT", ""),
            stderr=os.environ.get("XIC_DOCS_PLACEMENT_GUARD_STDERR", ""),
        )

    root = repo_root_from_cwd(cwd)
    script = os.path.join(root, "tools", "diagnostics", "docs_placement_guard.py")
    try:
        result = subprocess.run(
            [sys.executable, script, "--staged"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CommandResult(
            returncode=1,
            stdout="",
            stderr=f"docs placement guard could not run: {exc}",
        )
    return CommandResult(
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )
