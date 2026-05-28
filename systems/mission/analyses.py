"""Mission-level analyses（衛星全体ビュー）。

`@auto_inject_refs` が registry から全 component を列挙して
`Annotated[vq.Table, vq.Ref(...)]` 引数を一括注入する。元関数は
`*tables` で受け取り、body は 1 行で書ける。
"""

from craft.analyses import auto_inject_refs, total_mass_kg, total_quantity
from craft.schema import analysis


@analysis(desc="衛星全体の総質量 [kg]（コンポ + 構造体 + 推進剤）= wet mass 相当")
@auto_inject_refs()
def total_bus_mass_kg(*tables) -> float:
    """全 instance の spec.mass_kg × design.quantity を合算 [kg]。"""
    return total_mass_kg(*tables)


@analysis(desc="衛星全体の搭載コンポ個数（quantity 合計、debug 用）")
@auto_inject_refs()
def total_component_count(*tables) -> int:
    """全テーブルの quantity 合計。"""
    return total_quantity(*tables)
