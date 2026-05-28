"""Field helper — 統一フィールド宣言。

`fld()` は Pydantic の `Field()` への薄いラッパで、UI hint (unit/group/order)
を `json_schema_extra` に乗せる。

戻り値は実体としては `FieldInfo` だが、`dataclass_transform` の field_specifier
として宣言されたクラス（`Component`/`Config`）の中で `capacity_wh: float = fld(...)`
のようにフィールド宣言にも使うため、型ヒント上は `Any` を返す。
これにより pyrefly / mypy が `FieldInfo` をフィールド型に代入できないと誤検出する
のを防ぐ。
"""

from typing import Any

from pydantic import Field


def fld(
    *,
    default: Any = ...,
    default_factory: Any = None,
    ge: float | None = None,
    le: float | None = None,
    gt: float | None = None,
    lt: float | None = None,
    unit: str | None = None,
    desc: str | None = None,
    group: str | None = None,
    order: int | None = None,
    key_source: str | None = None,
) -> Any:
    """Component / Config / Analysis の field 宣言ヘルパー。

    Args:
        default: デフォルト値。指定しない場合 required (= `...`)。
        default_factory: 可変なデフォルトに使うファクトリ。
        ge/le/gt/lt: 数値制約。
        unit: 物理単位（"W", "Wh", "degC" 等）。UI ヒント、JSON Schema に乗る。
        desc: 説明文。
        group: UI 上のグループ名。
        order: UI 上の表示順序。
    """
    extra: dict[str, Any] = {}
    if unit is not None:
        extra["unit"] = unit
    if group is not None:
        extra["group"] = group
    if order is not None:
        extra["order"] = order
    if key_source is not None:
        extra["key_source"] = key_source

    kwargs: dict[str, Any] = {}
    if default_factory is not None:
        kwargs["default_factory"] = default_factory
    else:
        kwargs["default"] = default
    if ge is not None:
        kwargs["ge"] = ge
    if le is not None:
        kwargs["le"] = le
    if gt is not None:
        kwargs["gt"] = gt
    if lt is not None:
        kwargs["lt"] = lt
    if desc is not None:
        kwargs["description"] = desc
    if extra:
        kwargs["json_schema_extra"] = extra

    return Field(**kwargs)
