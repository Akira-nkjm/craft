#!/usr/bin/env python3
"""Non-destructive installer for this agent-settings template.

Environment:
  FORCE=1   overwrite existing files after creating .bak.<timestamp> backups
  DRY_RUN=1 show planned changes and diffs without writing

Default behavior preserves existing files and copies only missing files. Directory
targets are traversed recursively so new template files can be added without
overwriting project-specific edits such as .claude/rules/project.md.
"""
from __future__ import annotations

import difflib
import os
import re
import shutil
from datetime import datetime
from pathlib import Path


TARGETS = [
    ".claude",
    ".codex",
    ".codegraph",
    ".tasks",
    "CLAUDE.md",
    "AGENTS.md",
    "RULES.md",
    "SOUL.md",
    ".mcp.json",
    "justfile",
    ".gitignore",
]

EXCLUDED_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache"}
EXCLUDED_PATHS = {".claude/sessions"}
EXCLUDED_SUFFIXES = (".db", ".db-wal", ".db-shm", ".log")


def is_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


FORCE = is_enabled("FORCE")
DRY_RUN = is_enabled("DRY_RUN")
TIMESTAMP = datetime.now().strftime("%Y%m%d%H%M%S")


def log(message: str) -> None:
    print(message)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def show_diff(label: str, old: str, new: str) -> None:
    if old == new:
        return
    print(f"--- diff: {label} ---")
    for line in difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"existing/{label}",
        tofile=f"template/{label}",
    ):
        print(line, end="")
    if not old.endswith("\n") or not new.endswith("\n"):
        print()


def backup(path: Path) -> Path:
    backup_path = path.with_name(f"{path.name}.bak.{TIMESTAMP}")
    if DRY_RUN:
        log(f"DRY_RUN backup: {path} -> {backup_path}")
        return backup_path
    shutil.copy2(path, backup_path)
    log(f"Backed up: {backup_path}")
    return backup_path


def copy_file(src: Path, dst: Path, label: str) -> None:
    if not dst.exists():
        if DRY_RUN:
            log(f"DRY_RUN copy: {label}")
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        log(f"Copied: {label}")
        return

    if DRY_RUN:
        show_diff(label, read_text(dst), read_text(src))
        return

    if FORCE:
        backup(dst)
        shutil.copy2(src, dst)
        log(f"Overwritten: {label}")
    else:
        log(f"Skipped existing: {label}")


def copy_directory(src_dir: Path, dst_dir: Path, label: str) -> None:
    for src in sorted(src_dir.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(src_dir)
        rel_label = f"{label}/{rel.as_posix()}"
        if any(part in EXCLUDED_PARTS for part in rel.parts) or rel_label in EXCLUDED_PATHS or rel_label.startswith(".claude/sessions/"):
            continue
        if src.name.endswith(EXCLUDED_SUFFIXES):
            continue
        copy_file(src, dst_dir / rel, rel_label)


def recipe_name(block: str) -> str | None:
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*)\b", stripped)
        return match.group(1) if match else None
    return None


def merge_justfile(src: Path, dst: Path) -> None:
    src_text = read_text(src)
    dst_text = read_text(dst)
    blocks = re.split(r"\n{2,}", src_text.strip())
    existing = {
        match.group(1)
        for match in re.finditer(r"^([A-Za-z][A-Za-z0-9_-]*)[\s:]", dst_text, re.MULTILINE)
    }
    additions = [block for block in blocks if (name := recipe_name(block)) and name not in existing]
    skipped = [name for block in blocks if (name := recipe_name(block)) and name in existing]

    if not additions:
        log("justfile up to date")
        if skipped:
            log("以下の recipe は既存と重複するため追加されませんでした: " + ", ".join(skipped))
        return

    new_text = dst_text.rstrip() + "\n\n" + "\n\n".join(additions) + "\n"
    if DRY_RUN:
        show_diff("justfile", dst_text, new_text)
        return
    backup(dst)
    write_text(dst, new_text)
    log(f"Merged {len(additions)} recipe(s) into justfile")
    if skipped:
        log("以下の recipe は既存と重複するため追加されませんでした: " + ", ".join(skipped))


def merge_gitignore(src: Path, dst: Path) -> None:
    src_lines = read_text(src).splitlines()
    dst_text = read_text(dst)
    existing = set(dst_text.splitlines())
    additions = [line for line in src_lines if line not in existing]
    if not additions:
        log(".gitignore up to date")
        return
    new_text = dst_text.rstrip() + "\n" + "\n".join(additions) + "\n"
    if DRY_RUN:
        show_diff(".gitignore", dst_text, new_text)
        return
    backup(dst)
    write_text(dst, new_text)
    log(f"Merged {len(additions)} line(s) into .gitignore")


def install_target(src_root: Path, dst_root: Path, rel_name: str) -> None:
    src = src_root / rel_name
    dst = dst_root / rel_name
    if not src.exists():
        return
    if rel_name == "justfile" and dst.exists() and not FORCE:
        merge_justfile(src, dst)
    elif rel_name == ".gitignore" and dst.exists() and not FORCE:
        merge_gitignore(src, dst)
    elif src.is_dir():
        copy_directory(src, dst, rel_name)
    else:
        copy_file(src, dst, rel_name)


def main() -> int:
    src_root = Path.cwd().resolve()
    dst_root = src_root.parent
    log(f"Installing to: {dst_root}")
    if DRY_RUN:
        log("DRY_RUN=1: no files will be changed")
    if FORCE:
        log("FORCE=1: existing files will be backed up and overwritten")

    for target in TARGETS:
        install_target(src_root, dst_root, target)

    log("Done. Edit .claude/rules/project.md, architecture.md, and commands.md for project-specific settings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
