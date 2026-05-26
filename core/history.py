"""git history / diff helpers."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from core.paths import REPO_ROOT


@dataclass(frozen=True, slots=True)
class GitLogEntry:
    sha: str
    author: str
    date: str
    message: str


class GitError(Exception):
    """Base exception for git command failures."""


class GitRefNotFound(GitError):  # noqa: N818 - public API name is specified.
    """Raised when a requested git ref cannot be resolved."""


_REF_NOT_FOUND_MARKERS = (
    "unknown revision",
    "bad revision",
    "ambiguous argument",
    "invalid object name",
    "not a valid object name",
    "unknown commit",
)


def _run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout

    stderr = result.stderr.strip()
    lower_stderr = stderr.lower()
    if any(marker in lower_stderr for marker in _REF_NOT_FOUND_MARKERS):
        raise GitRefNotFound(stderr or "git ref not found")
    raise GitError(stderr or f"git exited with status {result.returncode}")


def git_log(path: Path | str | None = None, *, limit: int = 20) -> list[GitLogEntry]:
    if limit <= 0:
        return []

    args = [
        "log",
        "--format=%H%x09%an%x09%aI%x09%s",
        f"--max-count={limit}",
    ]
    if path is not None:
        args.extend(["--", str(path)])

    output = _run_git(args)
    entries: list[GitLogEntry] = []
    for line in output.splitlines():
        sha, author, date, message = line.split("\t", maxsplit=3)
        entries.append(GitLogEntry(sha=sha, author=author, date=date, message=message))
    return entries


def git_diff(from_sha: str, to_sha: str, path: Path | str | None = None) -> str:
    args = ["diff", from_sha, to_sha]
    if path is not None:
        args.extend(["--", str(path)])
    return _run_git(args)
