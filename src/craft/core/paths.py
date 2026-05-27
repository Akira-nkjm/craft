"""パス計算。systems ディレクトリと generated/ 配下の位置はこのファイルが基準。"""

from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[3]

# ─── systems/ ────────────────────────────────────────────────────────


def subsystems_root() -> Path:
    """`<repo_root>/systems` を返す。"""
    return REPO_ROOT / "systems"


def subsystem_dir(name: str) -> Path:
    """`<repo_root>/systems/<name>` を返す。"""
    return subsystems_root() / name


def system_data_path(name: str) -> Path:
    """`<repo_root>/systems/<name>/data.toml` を返す。"""
    return subsystem_dir(name) / "data.toml"


# ─── generated/ ──────────────────────────────────────────────────────

GENERATED_DIR: Path = REPO_ROOT / "generated"
MERGED_TOML: Path = GENERATED_DIR / "merged.toml"
MERGED_LOCK: Path = GENERATED_DIR / "merged.lock"


def runs_dir() -> Path:
    """`<repo_root>/generated/runs` を返す。"""
    return GENERATED_DIR / "runs"


def jobs_dir() -> Path:
    """`<repo_root>/generated/runs/jobs` を返す（非同期 verify 用）。"""
    return runs_dir() / "jobs"


def analysis_cache_dir() -> Path:
    """`<repo_root>/generated/runs/analyses` を返す（ad-hoc analysis cache）。"""
    return runs_dir() / "analyses"
