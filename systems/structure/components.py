"""Structure system components.

Source: SEIRIOS 子衛星 (shared drive: SEIRIOS)
  - SEIRIOS_コンポ管理シート / 子衛星1 Structure セクション
  - 子機分離機構設計

設計判断:
- 構造系は基本的に passive。HRM のみ pyro/burn-wire 駆動で電力を瞬時消費
- 構造体・パネル・締結具はマス管理の対象。Placeable で配置情報を持つ
"""

from craft.schema import (
    Component,
    MultiInstance,
    Placeable,
    PowerConsuming,
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


class Bracket(Component, MultiInstance, Placeable):
    """搭載ブラケット（コンポ取り付け用）。"""

    material: str = fld(default="Al7075", desc="材料")

    class Design:
        pass


class Hinge(Component, MultiInstance, Placeable):
    """展開ヒンジ。SAP / アンテナ展開などで使用。"""

    deploy_angle_deg: float = fld(ge=0, le=360, default=180.0, unit="deg", desc="展開角度")

    class Design:
        pass


class HoldReleaseMechanism(Component, MultiInstance, PowerConsuming, Placeable):
    """HRM（Hold/Release Mechanism）。打ち上げ拘束を軌道上で解放。

    PowerConsuming: pyro / burn-wire 式は瞬時電力消費。
    SEIRIOS HRM = 5.0W/個 × 2、分離後 1 回のみ駆動。
    """

    release_mechanism: str = fld(default="burn_wire", desc="release 方式: pyro / burn_wire / motor")

    class Design:
        pass


class SeparationBracket(Component, MultiInstance, Placeable):
    """子衛星分離ブラケット。打ち上げ時の親-子拘束、軌道上で分離。"""

    side: str = fld(default="child", desc="設置側: parent / child")

    class Design:
        pass


class SeparationConnector(Component, MultiInstance, Placeable):
    """分離コネクタ（電源 / 信号）。"""

    connector_type: str = fld(default="electrical", desc="electrical / fluid / RF")
    contact_count: int = fld(ge=0, default=0, desc="接点数")

    class Design:
        pass


class Baffle(Component, MultiInstance, Placeable):
    """光学バッフル（迷光遮蔽）。Mission / STT 等で使用。"""

    instrument: str = fld(default="", desc="対象光学機器名")

    class Design:
        pass


class CounterMass(Component, MultiInstance, Placeable):
    """質量バランス用ダミーマス。"""

    class Design:
        pass


class Fastener(Component, MultiInstance):
    """ボルト・ナット類の総量（個別配置を持たない）。"""

    material: str = fld(default="A286", desc="材料")

    class Design:
        pass


class Harness(Component, MultiInstance):
    """ハーネス・計装類の総量（個別配置を持たない）。"""

    class Design:
        pass
