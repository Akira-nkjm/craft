"""TOML I/O — atomic 書き込みつき。

`tomlkit` を使うことで:
- 既存ファイルのコメントを保持
- field の順序を制御
- `# unit / desc` を field 直後に挿入

`read_toml` は pure dict を返す(`tomllib` 経由)。`read_toml_doc` は
`tomlkit.TOMLDocument` を返し、書き戻し時にコメントを温存する。
"""

import contextlib
import os
import tempfile
import tomllib
from pathlib import Path
from typing import Any

import tomlkit
from tomlkit import TOMLDocument


def read_toml(path: Path) -> dict[str, Any]:
    """TOML を pure dict として読み込む。存在しないなら空。"""
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def read_toml_doc(path: Path) -> TOMLDocument:
    """TOML を tomlkit TOMLDocument として読み込む(コメント保持)。"""
    if not path.exists():
        return tomlkit.document()
    return tomlkit.parse(path.read_text(encoding="utf-8"))


def write_toml_atomic(path: Path, data: dict[str, Any] | TOMLDocument | str) -> None:
    """同一ファイルシステム上で temp に書いてから rename。

    `data` が str ならそのまま書く。dict なら tomli_w 相当の最小整形。
    TOMLDocument なら tomlkit のフォーマットをそのまま温存。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        if isinstance(data, str):
            content = data
        elif isinstance(data, TOMLDocument):
            content = tomlkit.dumps(data)
        else:
            content = tomlkit.dumps(_dict_to_doc(data))
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def _dict_to_doc(data: dict[str, Any]) -> TOMLDocument:
    """pure dict から TOMLDocument に変換。None は除外。"""
    doc = tomlkit.document()
    for k, v in data.items():
        item = _value_to_item(v)
        if item is not None:
            doc[k] = item
    return doc


def _value_to_item(value: Any) -> Any:
    """tomlkit の item を構築。None は呼び元で skip。"""
    if value is None:
        return None
    if isinstance(value, dict):
        tbl = tomlkit.table()
        for k, v in value.items():
            item = _value_to_item(v)
            if item is not None:
                tbl[k] = item
        return tbl
    if isinstance(value, list):
        arr = tomlkit.array()
        for v in value:
            if v is not None:
                arr.append(v)
        return arr
    return value
