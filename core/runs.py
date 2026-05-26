"""Verification run の永続化 — `generated/runs/<run_id>/`。

仕様: plan/Craft/01_仕様/データパイプライン.md §2.1

run_id: `<ISO8601 UTC (T15-42-18Z 形式)>-<short hash>`
short hash: `sha256(input + registry_sha)[:6]`

各 run のディレクトリ:
    generated/runs/<run_id>/
    ├── result.toml      veriq export_to_toml の出力 (input + .calc + .verification)
    ├── input.toml       merged.toml のスナップショット
    ├── meta.json        status / duration / errors / registry_sha
    └── trace.json       build_traceability_report の JSON 化 (optional)

`latest` symlink (or `latest.txt` fallback) で最新 run_id を保持。
"""

import contextlib
import hashlib
import importlib
import json
import os
import shutil
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

merge_mod = importlib.import_module("core.merge")


def _runs_dir() -> Path:
    return merge_mod.GENERATED_DIR / "runs"


def _latest_marker() -> Path:
    return _runs_dir() / "latest.txt"


def _latest_symlink() -> Path:
    return _runs_dir() / "latest"


@dataclass(frozen=True, slots=True)
class Run:
    id: str
    created_at: str  # ISO8601 UTC
    status: str  # "success" | "failure" | "running"
    duration_s: float
    errors: tuple[str, ...] = field(default_factory=tuple)
    input_sha: str = ""
    registry_sha: str = ""


def _format_timestamp(dt: datetime) -> str:
    """`2026-05-26T15-42-18Z` 形式（コロンをハイフンに）。"""
    s = dt.strftime("%Y-%m-%dT%H-%M-%SZ")
    return s


def _short_hash(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
    return h.hexdigest()[:6]


def new_run_id(*, input_sha: str = "", registry_sha: str = "") -> str:
    ts = _format_timestamp(datetime.now(tz=UTC))
    short = _short_hash(input_sha, registry_sha, str(time.monotonic_ns()))
    return f"{ts}-{short}"


def run_dir(run_id: str) -> Path:
    return _runs_dir() / run_id


def create_run_dir(run_id: str) -> Path:
    d = run_dir(run_id)
    d.mkdir(parents=True, exist_ok=False)
    return d


def _is_run_dir(path: Path) -> bool:
    reserved = {"latest", "analyses", "jobs"}
    return (
        path.is_dir()
        and not path.is_symlink()
        and not path.name.startswith("_")
        and path.name not in reserved
        and (path / "meta.json").exists()
    )


def write_run_artifacts(
    run_id: str,
    *,
    result_toml: bytes | str | None = None,
    input_toml: bytes | str | None = None,
    meta: dict[str, Any] | None = None,
    trace: dict[str, Any] | None = None,
) -> None:
    """既存の run dir に各成果物を書き込む。"""
    d = run_dir(run_id)
    if not d.exists():
        raise FileNotFoundError(f"Run directory not found: {d}")
    if result_toml is not None:
        _write_text_or_bytes(d / "result.toml", result_toml)
    if input_toml is not None:
        _write_text_or_bytes(d / "input.toml", input_toml)
    if meta is not None:
        (d / "meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
    if trace is not None:
        (d / "trace.json").write_text(
            json.dumps(trace, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )


def _write_text_or_bytes(path: Path, content: bytes | str) -> None:
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def update_latest(run_id: str) -> None:
    """`latest` symlink (or fallback) を更新。"""
    runs = _runs_dir()
    runs.mkdir(parents=True, exist_ok=True)
    symlink = _latest_symlink()
    # symlink update を atomic に
    tmp_symlink = symlink.with_suffix(".tmp")
    with contextlib.suppress(FileNotFoundError):
        tmp_symlink.unlink()
    try:
        os.symlink(run_id, tmp_symlink)
        os.replace(tmp_symlink, symlink)
    except (OSError, NotImplementedError):
        # symlink 不可な FS なら text fallback
        _latest_marker().write_text(run_id, encoding="utf-8")


def latest_run_id() -> str | None:
    """最新 run_id を返す。`latest` symlink → latest.txt → ディレクトリ最大値 の順で解決。"""
    symlink = _latest_symlink()
    if symlink.exists():
        try:
            target = os.readlink(symlink)
            return Path(target).name
        except OSError:
            pass
    marker = _latest_marker()
    if marker.exists():
        return marker.read_text(encoding="utf-8").strip() or None
    # fallback: dir 内最大値
    runs = _runs_dir()
    if not runs.exists():
        return None
    candidates = [p.name for p in runs.iterdir() if _is_run_dir(p)]
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1]


def list_runs(*, limit: int | None = None) -> list[Run]:
    """全 run の Run dataclass リストを新しい順で返す。"""
    runs = _runs_dir()
    if not runs.exists():
        return []
    entries: list[Run] = []
    for d in sorted(runs.iterdir(), reverse=True):
        if not _is_run_dir(d):
            continue
        run = _load_run(d)
        if run is not None:
            entries.append(run)
        if limit is not None and len(entries) >= limit:
            break
    return entries


def get_run(run_id: str) -> Run | None:
    """単一 run の Run。存在しなければ None。"""
    d = run_dir(run_id)
    if not _is_run_dir(d):
        return None
    return _load_run(d)


def get_run_artifact(run_id: str, name: str) -> bytes | None:
    """run dir 内の任意ファイル中身をバイト列で返す。"""
    p = run_dir(run_id) / name
    if not p.exists() or not p.is_file():
        return None
    return p.read_bytes()


def _load_run(d: Path) -> Run | None:
    meta_path = d / "meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
    else:
        meta = {}
    return Run(
        id=d.name,
        created_at=meta.get("created_at", ""),
        status=meta.get("status", "unknown"),
        duration_s=float(meta.get("duration_s", 0.0)),
        errors=tuple(meta.get("errors", [])),
        input_sha=meta.get("input_sha", ""),
        registry_sha=meta.get("registry_sha", ""),
    )


def prune_runs(*, keep: int) -> list[str]:
    """最新 `keep` 件を残し、それ以前を削除。削除した run_id のリストを返す。"""
    runs = (
        sorted(
            (p for p in _runs_dir().iterdir() if _is_run_dir(p)),
            reverse=True,
        )
        if _runs_dir().exists()
        else []
    )
    removed: list[str] = []
    for old in runs[keep:]:
        shutil.rmtree(old, ignore_errors=True)
        removed.append(old.name)
    return removed


def run_to_dict(run: Run) -> dict[str, Any]:
    d = asdict(run)
    d["errors"] = list(d["errors"])
    return d
