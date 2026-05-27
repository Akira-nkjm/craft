"""アトミック書き込みユーティリティ。

同一ディレクトリに tempfile → os.replace の順でファイルを書き込み、
中断時でも既存ファイルが壊れないことを保証する。
"""

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """bytes をアトミックに書き込む。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except Exception:
        # os.fdopen が raise した場合は fd がまだ開いているため閉じる。
        # os.fdopen が成功した場合は with ブロックで既に閉じられているため EBADF を抑制。
        with contextlib.suppress(OSError):
            os.close(fd)
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """str をアトミックに書き込む。"""
    atomic_write_bytes(path, text.encode(encoding))


def atomic_write_json(path: Path, obj: Any, *, indent: int | None = 2) -> None:
    """JSON シリアライズした結果をアトミックに書き込む。"""
    text = json.dumps(obj, indent=indent, ensure_ascii=False, default=str)
    atomic_write_text(path, text)


def atomic_write_bytes_or_text(path: Path, content: bytes | str) -> None:
    """bytes または str をアトミックに書き込む。型で自動選択。"""
    if isinstance(content, bytes):
        atomic_write_bytes(path, content)
    else:
        atomic_write_text(path, content)
