"""Structure system components.

Source: ONGLAISAT（6U 地球観測 CubeSat, ISSL 東大バス）
  - 08_Structure/Structure and Configuration.md、00_System/Mass Budget.md
  - mass_inertia_breakdown.csv「1.structure」、satellite_structure.ini

設計判断:
- 構造系は基本的に passive。HRM のみ pyro/burn-wire 駆動で電力を瞬時消費
- 構造体・パネル・締結具はマス管理の対象。Placeable で配置情報を持つ
"""

from craft.schema import (
    Component,
    MultiInstance,
    Placeable,
    fld,
)


class Frame(Component, MultiInstance, Placeable):
    """構体フレーム（一次構造）。"""

    material: str = fld(default="Al7075", desc="主材料")
    yield_strength_mpa: float = fld(ge=0, default=0.0, unit="MPa", desc="降伏応力")

    class Design:
        pass


class StructuralPanel(Component, MultiInstance, Placeable):
    """構造パネル（外板）。SAP 太陽電池基板とは別概念。"""

    material: str = fld(default="Al honeycomb", desc="材料: Al honeycomb / CFRP 等")
    thickness_mm: float = fld(ge=0, default=0.0, unit="mm", desc="厚さ")

    class Design:
        pass
