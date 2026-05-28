"""Component traits.

trait は marker class。`Component.__init_subclass__` が `__mro__` を走査して
trait を検出し、各 trait が宣言した field を Spec / Design / Requirements
にマージする。

新しい trait を書く場合は `_Trait` を継承し、必要に応じて以下の ClassVar をオーバーライドする:
- ``cardinality``: ``"single"`` | ``"multi"``  — instances 数の制約
- ``design_extra``: ``{name: (type, FieldInfo)}``  — Design モデルに追加するフィールド
- ``spec_only``: ``bool``  — ``True`` の場合 Design を持たない
"""

from typing import Any, ClassVar

from craft.schema.common import OperationMode
from craft.schema.dsl.placement import Placement
from craft.schema.fields import fld


class _Trait:
    """全 trait の基底マーカー。Component と区別するため。"""

    cardinality: ClassVar[str] = "single"
    design_extra: ClassVar[dict[str, Any]] = {}  # Must NOT be mutated in-place
    spec_only: ClassVar[bool] = False


class MultiInstance(_Trait):
    """インスタンスを複数許可する component。

    default は Singleton（trait 不要）。
    """

    cardinality: ClassVar[str] = "multi"


class PowerConsuming(_Trait):
    """電力を消費する component。

    自動追加されるフィールド:
        Spec:   power_per_unit_w  (float, W)            — 単位あたり消費電力
        Design: power_modes       (dict[mode, bool])    — モード別 on/off
    """

    power_per_unit_w: float = fld(
        ge=0,
        unit="W",
        desc="単位あたりの想定消費電力",
    )

    design_extra: ClassVar[dict[str, Any]] = {
        "power_modes": (
            dict[OperationMode, bool],
            fld(
                default_factory=dict,
                desc="OperationMode 別の on/off",
                key_source="mission.operation_mode_configs",
            ),
        ),
    }


class TemperatureSensitive(_Trait):
    """動作温度範囲を持つ component。

    自動追加されるフィールド:
        Spec: temp_min_c  (float, degC) — 動作温度下限
              temp_max_c  (float, degC) — 動作温度上限
    """

    temp_min_c: float = fld(unit="degC", desc="動作温度下限")
    temp_max_c: float = fld(unit="degC", desc="動作温度上限")


class SpecOnly(_Trait):
    """Design を持たない component（datasheet 型）。"""

    spec_only: ClassVar[bool] = True


class Placeable(_Trait):
    """搭載位置情報を持つ component。opt-in で ``placement`` フィールドを Design に追加する。"""

    design_extra: ClassVar[dict[str, Any]] = {
        "placement": (Placement | None, fld(default=None, desc="搭載位置・CAD パラメータ")),
    }
