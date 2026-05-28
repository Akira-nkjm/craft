"""共有ヘルパ・例外 — components.py / configs.py から参照される内部モジュール。"""

import hashlib
import json
from typing import Any

from craft.core.errors import ETagMismatch, PreconditionRequired


class InstanceNotFound(Exception):  # noqa: N818
    pass


class InstanceAlreadyExists(Exception):  # noqa: N818
    pass


class SingletonNotInstanceable(Exception):  # noqa: N818
    pass


class SharedSpecConflict(Exception):  # noqa: N818
    """payload の spec が shared と矛盾している。"""


def _dig(d: dict[str, Any], keys: list[str]) -> dict[str, Any] | None:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur if isinstance(cur, dict) else None


def _ensure_dig(d: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    cur = d
    for k in keys:
        nxt = cur.get(k)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[k] = nxt
        cur = nxt
    return cur


def _pop_dig(d: dict[str, Any], keys: list[str]) -> dict[str, Any] | None:
    if not keys:
        return None
    *parents, leaf = keys
    parent = _dig(d, parents)
    if parent is None or leaf not in parent or not isinstance(parent[leaf], dict):
        return None
    removed = parent.pop(leaf)
    for i in range(len(parents), 0, -1):
        upper = _dig(d, parents[: i - 1])
        key = parents[i - 1]
        if upper is None:
            break
        node = upper.get(key)
        if isinstance(node, dict) and not node:
            upper.pop(key)
        else:
            break
    return removed


def compute_etag(payload: dict[str, Any]) -> str:
    canon = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return 'W/"sha256:' + hashlib.sha256(canon.encode("utf-8")).hexdigest()[:32] + '"'


def _check_etag(current: dict[str, Any], expected_etag: str | None) -> None:
    if expected_etag is None:
        raise PreconditionRequired("If-Match header is required for this operation")
    actual = compute_etag(current)
    if expected_etag.strip() != actual:
        raise ETagMismatch(f"If-Match did not match current ETag ({actual})")


def _deep_merge(base: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in delta.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out
