"""Audit repo/Obsidian documentation management health.

This checker is read-only. It catches workflow drift that the staged
docs-placement guard intentionally does not cover, such as stale branch
handoffs after a commit, vault manifest stats that no longer match the vault,
pending raw/staged wiki files, missing wiki lifecycle metadata, and local-path
exposure that needs a focused retention/privacy review.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.diagnostics.handoff_retention_audit import (  # noqa: E402
    run_handoff_retention_audit,
)

DEFAULT_CONFIG = Path.home() / ".obsidian-wiki" / "config"
LOCAL_ENV_FILES = (".env.xic-local", ".env")

STALE_HANDOFF_PATTERNS = (
    "no commit has been made",
    "the branch is not committed",
    "staged deletions",
    "staged for removal",
    "review staged diff",
    "before commit review",
)
LOCAL_PATH_PATTERNS = (
    re.compile(r"C:\\Users\\user\\", re.IGNORECASE),
    re.compile(r"C:/Users/user/", re.IGNORECASE),
    re.compile(r"C:\\Vaults(?:\\|$)", re.IGNORECASE),
    re.compile(r"C:\\Xcalibur(?:\\|$)", re.IGNORECASE),
    re.compile(r"C:\\Python\d+(?:\\|$)", re.IGNORECASE),
    re.compile(r"Research Vault", re.IGNORECASE),
)
LOCAL_PATH_SCAN_EXCLUSIONS = {"tools/diagnostics/docs_management_audit.py"}
LOCAL_PATH_SCAN_FALLBACK_DIRS = (
    "docs",
    "tests",
    "tools",
    "scripts",
    ".github",
    ".codex/hooks",
)
LOCAL_PATH_SCAN_TEXT_SUFFIXES = {
    ".cfg",
    ".csv",
    ".env",
    ".example",
    ".ini",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
}
LOCAL_PATH_SCAN_TEXT_FILENAMES = {
    ".env.example",
    ".gitignore",
    "AGENTS.md",
    "CONTEXT.md",
    "README.md",
}
VALID_LIFECYCLES = {"draft", "reviewed", "verified", "disputed", "archived"}
VALID_TIERS = {"core", "supporting", "peripheral"}


@dataclass(frozen=True)
class AuditMessage:
    severity: str
    path: str
    message: str


@dataclass(frozen=True)
class AuditResult:
    messages: tuple[AuditMessage, ...]
    summary: dict[str, object]

    @property
    def blockers(self) -> tuple[AuditMessage, ...]:
        return tuple(msg for msg in self.messages if msg.severity == "blocker")


def _repo_rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    values: dict[str, str] = {}
    current_key: str | None = None
    for line in text[3:end].splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if line.startswith((" ", "\t")) or stripped.startswith("- "):
            if current_key and stripped.startswith("- "):
                item = stripped[2:].strip().strip('"').strip("'")
                values[current_key] = " ".join(
                    part for part in (values.get(current_key, ""), item) if part
                )
            continue
        if ":" not in line:
            current_key = None
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        values[current_key] = value.strip().strip('"').strip("'")
    return values


def _git_visible_paths(root: Path) -> tuple[str, ...] | None:
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return tuple(
        line.strip().replace("\\", "/")
        for line in completed.stdout.splitlines()
        if line.strip()
    )


def _fallback_local_path_scan_paths(root: Path) -> tuple[str, ...]:
    paths: set[str] = set()
    for base in LOCAL_PATH_SCAN_FALLBACK_DIRS:
        base_path = root / base
        if base_path.is_file():
            paths.add(_repo_rel(base_path, root))
        elif base_path.exists():
            paths.update(_repo_rel(path, root) for path in base_path.rglob("*"))
    for filename in LOCAL_PATH_SCAN_TEXT_FILENAMES:
        if (root / filename).exists():
            paths.add(filename)
    return tuple(sorted(paths))


def _is_local_path_scan_target(path: Path, rel_path: str) -> bool:
    if rel_path in LOCAL_PATH_SCAN_EXCLUSIONS:
        return False
    if not path.is_file():
        return False
    if path.name in LOCAL_PATH_SCAN_TEXT_FILENAMES:
        return True
    return path.suffix.lower() in LOCAL_PATH_SCAN_TEXT_SUFFIXES


def _config_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in _read_text(path).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def resolve_vault(root: Path, explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit
    env_value = os.environ.get("OBSIDIAN_VAULT_PATH")
    if env_value:
        return Path(env_value)

    current = root.resolve()
    home = Path.home().resolve()
    for candidate_dir in (current, *current.parents):
        for filename in LOCAL_ENV_FILES:
            candidate = candidate_dir / filename
            if candidate.exists():
                values = _config_values(candidate)
                vault = values.get("OBSIDIAN_VAULT_PATH")
                if vault:
                    return Path(vault)
        if candidate_dir == home:
            break

    values = _config_values(DEFAULT_CONFIG)
    vault = values.get("OBSIDIAN_VAULT_PATH")
    return Path(vault) if vault else None


def audit_repo(root: Path) -> tuple[list[AuditMessage], dict[str, object]]:
    messages: list[AuditMessage] = []
    docs = sorted((root / "docs").rglob("*.md"))
    docs_by_top = Counter(
        path.relative_to(root / "docs").parts[0]
        if path.relative_to(root / "docs").parts
        else "."
        for path in docs
    )

    stale_targets = [
        root
        / (
            "docs/superpowers/handoffs/current/"
            "codex-docs-cleanup-official-docs-and-handoff.md"
        ),
        root
        / (
            "docs/superpowers/handoffs/archive/"
            "2026-06-26_codex-docs-cleanup_branch-closeout-summary.md"
        ),
    ]
    for path in stale_targets:
        if not path.exists():
            continue
        text = _read_text(path).lower()
        for pattern in STALE_HANDOFF_PATTERNS:
            if pattern in text:
                messages.append(
                    AuditMessage(
                        "blocker",
                        _repo_rel(path, root),
                        f"stale branch-state phrase after commit: {pattern!r}",
                    )
                )

    local_path_counts: Counter[str] = Counter()
    scan_paths = _git_visible_paths(root) or _fallback_local_path_scan_paths(root)
    for rel_path in scan_paths:
        path = root / rel_path
        if not _is_local_path_scan_target(path, rel_path):
            continue
        text = _read_text(path)
        count = sum(len(pattern.findall(text)) for pattern in LOCAL_PATH_PATTERNS)
        if count:
            local_path_counts[rel_path] = count

    top_local_path_files = [
        {"path": path, "count": count}
        for path, count in local_path_counts.most_common(20)
    ]
    if local_path_counts:
        messages.append(
            AuditMessage(
                "warning",
                "repo",
                (
                    "local/private path exposure remains in tracked text; "
                    f"{len(local_path_counts)} files, "
                    f"{sum(local_path_counts.values())} hits"
                ),
            )
        )

    handoff_result = run_handoff_retention_audit(root)
    messages.extend(
        AuditMessage(
            msg.severity,
            msg.path,
            f"handoff retention: {msg.message}",
        )
        for msg in handoff_result.messages
    )

    summary: dict[str, object] = {
        "repo_markdown_files": len(docs),
        "docs_by_top_level": dict(sorted(docs_by_top.items())),
        "local_path_files": len(local_path_counts),
        "local_path_hits": sum(local_path_counts.values()),
        "top_local_path_files": top_local_path_files,
        "handoff_retention": handoff_result.summary,
    }
    return messages, summary


def _manifest_stats(manifest: Path) -> tuple[dict[str, object], list[str]]:
    data = json.loads(manifest.read_text(encoding="utf-8"))
    sources = data.get("sources", {})
    problems: list[str] = []
    source_values = sources.values() if isinstance(sources, dict) else []
    for source, metadata in sources.items() if isinstance(sources, dict) else []:
        if not Path(str(source)).exists():
            problems.append(f"manifest source missing on disk: {source}")
        if isinstance(metadata, dict):
            for key in ("pages_created", "pages_updated"):
                value = metadata.get(key)
                if value is not None and not isinstance(value, list):
                    problems.append(f"{source}: manifest {key} must be a list or null")
    stats = data.get("stats", {})
    if not isinstance(stats, dict):
        stats = {}
    return {
        "source_count": len(sources) if isinstance(sources, dict) else 0,
        "stats_total_sources_ingested": stats.get("total_sources_ingested"),
        "stats_total_pages": stats.get("total_pages"),
        "stats_total_projects": stats.get("total_projects"),
        "source_type_counts": dict(
            Counter(
                str(metadata.get("source_type", "(missing)"))
                for metadata in source_values
                if isinstance(metadata, dict)
            )
        ),
    }, problems


def _vault_link_health(md_files: Sequence[Path], vault: Path) -> dict[str, object]:
    page_keys: dict[str, str] = {}
    base_keys: dict[str, list[str]] = {}
    for path in md_files:
        rel = path.relative_to(vault).as_posix()
        no_ext = rel[:-3]
        page_keys[rel.lower()] = rel
        page_keys[no_ext.lower()] = rel
        base_keys.setdefault(path.stem.lower(), []).append(rel)

    incoming: Counter[str] = Counter()
    broken: list[dict[str, str]] = []
    for path in md_files:
        rel = path.relative_to(vault).as_posix()
        text = _read_text(path)
        for raw_target in re.findall(r"\[\[([^\]\n]+)\]\]", text):
            target = raw_target.split("|", 1)[0].strip().replace("\\", "/")
            target = target.split("#", 1)[0].strip()
            if not target or target.startswith(("http:", "https:")):
                continue
            no_ext = target[:-3] if target.endswith(".md") else target
            candidates: list[str] = []
            if target.lower() in page_keys:
                candidates = [page_keys[target.lower()]]
            elif no_ext.lower() in page_keys:
                candidates = [page_keys[no_ext.lower()]]
            else:
                candidates = base_keys.get(Path(no_ext).name.lower(), [])
            if candidates:
                incoming[candidates[0]] += 1
            else:
                broken.append({"source": rel, "target": target})

    all_pages = {path.relative_to(vault).as_posix() for path in md_files}
    orphans = sorted(page for page in all_pages if incoming[page] == 0)
    return {
        "broken_wikilinks": len(broken),
        "broken_wikilink_sample": broken[:20],
        "orphan_pages": len(orphans),
        "orphan_page_sample": orphans[:20],
    }


def audit_vault(vault: Path | None) -> tuple[list[AuditMessage], dict[str, object]]:
    messages: list[AuditMessage] = []
    if vault is None:
        return [
            AuditMessage(
                "warning",
                "vault",
                "Obsidian vault path is not configured; vault audit skipped",
            )
        ], {"vault_configured": False}
    if not vault.exists():
        return [
            AuditMessage(
                "blocker",
                str(vault),
                "configured Obsidian vault path does not exist",
            )
        ], {"vault_configured": True, "vault_exists": False}

    md_files = sorted(vault.rglob("*.md"))
    top_level = Counter(path.relative_to(vault).parts[0] for path in md_files)
    staging_md = (
        list((vault / "_staging").rglob("*.md"))
        if (vault / "_staging").exists()
        else []
    )
    raw_files = [
        path
        for path in (vault / "_raw").glob("*")
        if path.name != ".gitkeep"
    ] if (vault / "_raw").exists() else []

    if staging_md:
        messages.append(
            AuditMessage(
                "blocker",
                "_staging",
                f"{len(staging_md)} staged wiki markdown files are pending review",
            )
        )
    if raw_files:
        messages.append(
            AuditMessage(
                "blocker",
                "_raw",
                f"{len(raw_files)} raw wiki files are pending ingest/classification",
            )
        )

    missing_visibility = 0
    missing_lifecycle = 0
    invalid_lifecycle = 0
    missing_tier = 0
    invalid_tier = 0
    for path in md_files:
        fm = _frontmatter(_read_text(path))
        tags = fm.get("tags", "")
        if "visibility/" not in tags:
            missing_visibility += 1
        lifecycle = fm.get("lifecycle")
        if not lifecycle:
            missing_lifecycle += 1
        elif lifecycle not in VALID_LIFECYCLES:
            invalid_lifecycle += 1
        tier = fm.get("tier")
        if not tier:
            missing_tier += 1
        elif tier not in VALID_TIERS:
            invalid_tier += 1

    for label, count in (
        ("missing visibility tag", missing_visibility),
        ("missing lifecycle", missing_lifecycle),
        ("invalid lifecycle", invalid_lifecycle),
        ("missing tier", missing_tier),
        ("invalid tier", invalid_tier),
    ):
        if count:
            messages.append(
                AuditMessage("warning", "vault", f"{count} pages have {label}")
            )

    manifest_summary: dict[str, object] = {"manifest_exists": False}
    manifest = vault / ".manifest.json"
    if manifest.exists():
        manifest_summary, manifest_problems = _manifest_stats(manifest)
        manifest_summary["manifest_exists"] = True
        expected_sources = manifest_summary.get("source_count")
        expected_pages = len(md_files)
        if manifest_summary.get("stats_total_sources_ingested") != expected_sources:
            messages.append(
                AuditMessage(
                    "blocker",
                    ".manifest.json",
                    "manifest stats.total_sources_ingested does not match source count",
                )
            )
        if manifest_summary.get("stats_total_pages") != expected_pages:
            messages.append(
                AuditMessage(
                    "blocker",
                    ".manifest.json",
                    "manifest stats.total_pages does not match vault markdown count",
                )
            )
        for problem in manifest_problems[:20]:
            messages.append(AuditMessage("blocker", ".manifest.json", problem))
    else:
        messages.append(
            AuditMessage("blocker", ".manifest.json", "manifest is missing")
        )

    link_health = _vault_link_health(md_files, vault)
    if link_health["broken_wikilinks"]:
        messages.append(
            AuditMessage(
                "warning",
                "vault",
                (
                    f"{link_health['broken_wikilinks']} approximate broken "
                    "wikilinks remain"
                ),
            )
        )

    summary: dict[str, object] = {
        "vault_configured": True,
        "vault_exists": True,
        "vault_path": str(vault),
        "vault_markdown_files": len(md_files),
        "vault_by_top_level": dict(sorted(top_level.items())),
        "staging_markdown_files": len(staging_md),
        "raw_top_level_files": len(raw_files),
        "frontmatter": {
            "missing_visibility": missing_visibility,
            "missing_lifecycle": missing_lifecycle,
            "invalid_lifecycle": invalid_lifecycle,
            "missing_tier": missing_tier,
            "invalid_tier": invalid_tier,
        },
        "manifest": manifest_summary,
        "link_health": link_health,
    }
    return messages, summary


def run_audit(root: Path = ROOT, vault: Path | None = None) -> AuditResult:
    repo_messages, repo_summary = audit_repo(root)
    resolved_vault = resolve_vault(root, vault)
    vault_messages, vault_summary = audit_vault(resolved_vault)
    messages = [*repo_messages, *vault_messages]
    summary = {"repo": repo_summary, "vault": vault_summary}
    return AuditResult(tuple(messages), summary)


def format_text(result: AuditResult) -> str:
    lines = ["docs management audit"]
    lines.append(f"blockers: {len(result.blockers)}")
    warning_count = sum(1 for msg in result.messages if msg.severity == "warning")
    lines.append(f"warnings: {warning_count}")
    if result.messages:
        lines.append("")
    for msg in result.messages:
        lines.append(f"- {msg.severity}: {msg.path}: {msg.message}")
    lines.append("")
    lines.append(json.dumps(result.summary, indent=2, ensure_ascii=False))
    return "\n".join(lines)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--vault", type=Path)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of text.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_audit(args.root.resolve(), args.vault)
    if args.json:
        print(
            json.dumps(
                {
                    "blockers": [msg.__dict__ for msg in result.blockers],
                    "messages": [msg.__dict__ for msg in result.messages],
                    "summary": result.summary,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(format_text(result))
    return 1 if result.blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
