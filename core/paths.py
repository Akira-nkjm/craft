"""パス計算。subsystems ディレクトリの位置はこのファイルが基準。"""

from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parent.parent


def subsystems_root() -> Path:
    """`<repo_root>/subsystems` を返す。"""
    return REPO_ROOT / "subsystems"


def subsystem_dir(name: str) -> Path:
    """`<repo_root>/subsystems/<name>` を返す。"""
    return subsystems_root() / name


def subsystem_data_path(name: str) -> Path:
    """`<repo_root>/subsystems/<name>/data.toml` を返す。"""
    return subsystem_dir(name) / "data.toml"
