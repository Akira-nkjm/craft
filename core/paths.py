"""パス計算。systems ディレクトリの位置はこのファイルが基準。"""

from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parent.parent


def subsystems_root() -> Path:
    """`<repo_root>/systems` を返す。"""
    return REPO_ROOT / "systems"


def subsystem_dir(name: str) -> Path:
    """`<repo_root>/systems/<name>` を返す。"""
    return subsystems_root() / name


def system_data_path(name: str) -> Path:
    """`<repo_root>/systems/<name>/data.toml` を返す。"""
    return subsystem_dir(name) / "data.toml"
