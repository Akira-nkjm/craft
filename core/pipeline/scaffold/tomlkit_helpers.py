"""Scaffold 内で使う tomlkit 構造操作ヘルパー（section comment / nl / table 確保）。"""

from typing import Any

import tomlkit
from tomlkit import TOMLDocument
from tomlkit.items import Comment, Table, Whitespace


def ensure_section_comment(parent: TOMLDocument, key: str, title: str | None = None) -> None:
    """parent 内の key 直前に '# === Title ===' コメントが無ければ挿入する。

    既にコメントがある場合（=== を含む）はスキップ。
    """
    if title is None:
        title = key.replace("_", " ").title()
    body = parent._body  # TOMLDocument は Container を直接継承するため _body を直接持つ
    key_idx = next(
        (i for i, (k, _) in enumerate(body) if k is not None and str(k) == key),
        None,
    )
    if key_idx is None:
        # 未登録セクション: 後で ensure_table が追加するので、今は先行コメントだけ挿入
        # 空行数は normalize_scaffold_spacing が統一するので nl は 1 つだけ追加
        parent.add(tomlkit.nl())
        parent.add(tomlkit.comment(f"=== {title} ==="))
        parent.add(tomlkit.nl())
        return

    # 直前に === コメントが既にあるか確認（空行数は text 正規化に任せる）
    for i in range(key_idx - 1, -1, -1):
        k, v = body[i]
        if k is not None:
            break
        if isinstance(v, Comment) and "===" in str(v):
            return  # 既にある

    new_items = [
        (None, tomlkit.nl()),
        (None, tomlkit.comment(f"=== {title} ===")),
        (None, tomlkit.nl()),
    ]
    for i, item in enumerate(new_items):
        body.insert(key_idx + i, item)
    n = len(new_items)
    map_ = parent._map
    for mk in list(map_.keys()):
        idx = map_[mk]
        if isinstance(idx, tuple):
            map_[mk] = tuple(i + n if i >= key_idx else i for i in idx)
        elif isinstance(idx, int) and idx >= key_idx:
            map_[mk] = idx + n


def ensure_nl_before_key(section: Table, key: str) -> None:
    """section 内の key 直前に空行（改行）が無ければ挿入する。"""
    body = section.value._body
    key_idx = next(
        (i for i, (k, _) in enumerate(body) if k is not None and str(k) == key),
        None,
    )
    if key_idx is None:
        section.add(tomlkit.nl())
        return
    for i in range(key_idx - 1, -1, -1):
        k, v = body[i]
        if k is not None:
            break
        if isinstance(v, Whitespace) and "\n" in str(v):
            return
    body.insert(key_idx, (None, tomlkit.nl()))
    map_ = section.value._map
    for mk in list(map_.keys()):
        idx = map_[mk]
        if isinstance(idx, tuple):
            map_[mk] = tuple(i + 1 if i >= key_idx else i for i in idx)
        elif isinstance(idx, int) and idx >= key_idx:
            map_[mk] = idx + 1


def ensure_table(parent: TOMLDocument | Table, key: str) -> Table:
    """parent[key] を Table として確保。既存値が table でなければ作り直す。"""
    if key in parent:
        existing = parent[key]
        if isinstance(existing, Table):
            return existing
    new_tbl = tomlkit.table()
    parent[key] = new_tbl
    return parent[key]  # type: ignore[return-value]


def is_nested_table(value: Any) -> bool:
    return isinstance(value, (dict, Table)) and bool(value)
