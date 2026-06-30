"""Retire dated documents from repo to vault.

Checks whether each file already exists in the vault. If yes, deletes from repo.
If not, copies to vault first, then deletes from repo.

Usage:
    uv run python tools/diagnostics/retire_docs.py --sweep              # dry-run: show what would retire
    uv run python tools/diagnostics/retire_docs.py --sweep --execute    # actually retire
    uv run python tools/diagnostics/retire_docs.py FILE [FILE ...]      # retire specific files
"""
from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

VAULT_ARCHIVE_DIR = "XIC/20 Archived Plans And Specs/Repo Retired"

RETIRE_CANDIDATES = (
    "docs/superpowers/notes",
    "docs/superpowers/plans",
    "docs/superpowers/specs",
)

KEEP_PATTERNS = {
    "README.md",
    "productization_authority_manifest.v1.json",
    "productization_control_plane_schema.v1.json",
}

KEEP_PREFIXES = (
    "docs/superpowers/plans/2026-06-15-productization-control-plane.md",
)


def _normalize_title(filename: str) -> str:
    stem = Path(filename).stem
    return stem.lower().replace("-", " ").replace("_", " ").strip()


def _find_in_vault(title: str, vault_path: Path) -> Path | None:
    normalized = _normalize_title(title)
    for md in vault_path.rglob("*.md"):
        if _normalize_title(md.name) == normalized:
            return md
    return None


def _should_keep(rel_path: str) -> bool:
    name = Path(rel_path).name
    if name in KEEP_PATTERNS:
        return True
    for prefix in KEEP_PREFIXES:
        if rel_path == prefix:
            return True
    if name.endswith(".json") or name.endswith(".tsv"):
        return True
    return False


@dataclass
class RetireResult:
    already_in_vault: list[tuple[str, Path]] = field(default_factory=list)
    copied_to_vault: list[tuple[str, Path]] = field(default_factory=list)
    kept: list[tuple[str, str]] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)


def find_retire_candidates(repo_root: Path) -> list[Path]:
    candidates: list[Path] = []
    for dir_rel in RETIRE_CANDIDATES:
        d = repo_root / dir_rel
        if not d.is_dir():
            continue
        for f in sorted(d.rglob("*.md")):
            rel = f.relative_to(repo_root).as_posix()
            if not _should_keep(rel):
                candidates.append(f)
    return candidates


def retire_files(
    files: list[Path],
    repo_root: Path,
    vault_path: Path,
    *,
    execute: bool = False,
) -> RetireResult:
    result = RetireResult()
    vault_archive = vault_path / VAULT_ARCHIVE_DIR

    for fpath in files:
        rel = fpath.relative_to(repo_root).as_posix()

        if _should_keep(rel):
            result.kept.append((rel, "protected file"))
            continue

        if not fpath.exists():
            result.errors.append((rel, "file does not exist"))
            continue

        vault_match = _find_in_vault(fpath.name, vault_path)

        if vault_match:
            result.already_in_vault.append((rel, vault_match))
            if execute:
                fpath.unlink()
        else:
            dest = vault_archive / fpath.name
            result.copied_to_vault.append((rel, dest))
            if execute:
                vault_archive.mkdir(parents=True, exist_ok=True)
                shutil.copy2(fpath, dest)
                fpath.unlink()

    return result


def _resolve_vault_path() -> Path | None:
    config = Path.home() / ".obsidian-wiki" / "config"
    if not config.exists():
        return None
    for line in config.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("OBSIDIAN_VAULT_PATH="):
            val = line.split("=", 1)[1].strip().strip('"').strip("'")
            p = Path(val)
            if p.is_dir():
                return p
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="specific files to retire")
    parser.add_argument("--sweep", action="store_true", help="find all retire candidates")
    parser.add_argument("--execute", action="store_true", help="actually retire (default: dry-run)")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--vault-path", type=Path, default=None)
    args = parser.parse_args(argv)

    vault_path = args.vault_path or _resolve_vault_path()
    if not vault_path:
        print("ERROR: Cannot find vault path. Set OBSIDIAN_VAULT_PATH in ~/.obsidian-wiki/config", file=sys.stderr)
        return 1

    repo_root = args.repo_root.resolve()

    if args.sweep:
        files = find_retire_candidates(repo_root)
    elif args.files:
        files = [f.resolve() for f in args.files]
    else:
        parser.error("provide file paths or use --sweep")
        return 1

    mode = "EXECUTE" if args.execute else "DRY-RUN"
    print(f"Mode: {mode}\n")

    result = retire_files(files, repo_root, vault_path, execute=args.execute)

    if result.already_in_vault:
        print(f"Already in vault — {'deleted from repo' if args.execute else 'would delete'} ({len(result.already_in_vault)}):")
        for rel, vault_match in result.already_in_vault:
            print(f"  {rel}")
            print(f"    vault: {vault_match}")

    if result.copied_to_vault:
        print(f"\nNot in vault — {'copied + deleted' if args.execute else 'would copy + delete'} ({len(result.copied_to_vault)}):")
        for rel, dest in result.copied_to_vault:
            print(f"  {rel} → {dest}")

    if result.kept:
        print(f"\nKept ({len(result.kept)}):")
        for rel, reason in result.kept:
            print(f"  {rel} ({reason})")

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for rel, reason in result.errors:
            print(f"  {rel} ({reason})")

    total = len(result.already_in_vault) + len(result.copied_to_vault)
    print(f"\nSummary: {total} {'retired' if args.execute else 'retirable'}, {len(result.kept)} kept, {len(result.errors)} errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
