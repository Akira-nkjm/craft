"""Aggregation utilities for cross-subsystem analyses.

`systems/<sys>/analyses.py` の中で「全 PowerConsuming コンポを集計」「全コンポの
質量を合算」のようなコードを 1 行で書けるようにする。

設計思想:
- `vq.Table`（MultiInstance）と Singleton component を同じ API で扱う
  → `iter_instances` が両者を吸収する
- 各ヘルパは「インスタンス上に必要な属性が無ければ skip」する寛容な実装
  → power_modes が未定義の Component（Antenna 等）でも安全に渡せる
- veriq.Ref の制約上、analysis 関数のシグネチャでは各テーブルを明示で並べる必要がある
  ため、本ヘルパは*本体*を短くするのが目的。シグネチャの長さは別問題。
"""

from collections.abc import Iterable, Iterator
from typing import Any


def iter_instances(table_or_singleton: Any) -> Iterator[Any]:
    """vq.Table（dict-like）→ values()、Singleton（属性アクセス）→ それ自身、を統一。

    None / 空テーブルは何も yield しない。
    """
    if table_or_singleton is None:
        return
    # dict-like (vq.Table) なら values() を走査
    values_attr = getattr(table_or_singleton, "values", None)
    if callable(values_attr):
        try:
            yield from values_attr()
            return
        except TypeError:
            pass
    # Singleton component の場合はそれ自身を 1 個分として返す
    yield table_or_singleton


def _design_attr(inst: Any, name: str, default: Any = None) -> Any:
    """inst.design.<name> を安全に取得。design が無い場合 default。"""
    design = getattr(inst, "design", None)
    if design is None:
        return default
    return getattr(design, name, default)


def _instance_quantity(inst: Any) -> int:
    """inst.design.quantity を取得。設計値が無ければ 1 とみなす（Singleton 等）。"""
    qty = _design_attr(inst, "quantity", 1)
    try:
        return int(qty) if qty else 1
    except TypeError, ValueError:
        return 1


def power_for_mode(mode_name: str, *tables: Any) -> float:
    """指定モードで ON のインスタンスについて power_per_unit_w × quantity を合算 [W]。

    各 table は vq.Table または Singleton（OBC など）。power_modes / power_per_unit_w
    属性を持たないコンポは 0 として扱う（PassiveComponent 安全）。
    """
    total = 0.0
    for tbl in tables:
        for inst in iter_instances(tbl):
            power_modes = _design_attr(inst, "power_modes")
            if power_modes is None:
                continue
            if not power_modes.get(mode_name, False):
                continue
            power = getattr(getattr(inst, "spec", None), "power_per_unit_w", 0.0) or 0.0
            total += power * _instance_quantity(inst)
    return total


def power_per_mode(modes: Iterable[Any], *tables: Any) -> dict[str, float]:
    """各モードで全 ON インスタンスの消費電力 [W] を返す。

    `modes` には `vq.Table[OperationMode, ...]` や `list[str]` を渡せる。
    """
    return {str(m): power_for_mode(str(m), *tables) for m in modes}


def total_mass_kg(*tables: Any) -> float:
    """全インスタンスの spec.mass_kg × design.quantity を合算 [kg]。

    spec.mass_kg を持たないコンポは 0 として扱う。
    """
    total = 0.0
    for tbl in tables:
        for inst in iter_instances(tbl):
            mass = getattr(getattr(inst, "spec", None), "mass_kg", 0.0) or 0.0
            total += mass * _instance_quantity(inst)
    return total


def total_quantity(*tables: Any) -> int:
    """全テーブル合計の搭載個数。Singleton は 1。"""
    return sum(_instance_quantity(inst) for tbl in tables for inst in iter_instances(tbl))
