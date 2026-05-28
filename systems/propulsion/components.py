"""Propulsion system components.

Source: SEIRIOS 子衛星 (shared drive: SEIRIOS)
  - SEIRIOS_コンポ管理シート / 子衛星1 FF セクション
  - 電源モード検討 / 子衛星電力消費 行 21
"""

from craft.schema import (
    Component,
    MultiInstance,
    Placeable,
    PowerConsuming,
    TemperatureSensitive,
    fld,
)


class Thruster(Component, MultiInstance, PowerConsuming, TemperatureSensitive, Placeable):
    """推進機。SEIRIOS 子機の FF 制御推進機 PERSEUS (Pale Blue) 想定。"""

    propellant_type: str = fld(desc="推進剤種別: water / hydrazine / cold_gas 等")
    thrust_mn: float = fld(ge=0, default=0.0, unit="mN", desc="定格推力")
    specific_impulse_s: float = fld(ge=0, default=0.0, unit="s", desc="比推力 Isp")
    min_impulse_bit_ns: float = fld(ge=0, default=0.0, unit="N*s", desc="最小インパルスビット")

    class Design:
        pass


class PropellantTank(Component, MultiInstance, Placeable):
    """推進剤タンク（空タンク）。中身は `Propellant` で別管理。"""

    propellant_type: str = fld(desc="格納する推進剤種別")
    volume_l: float = fld(ge=0, default=0.0, unit="L", desc="タンク容積")
    max_pressure_bar: float = fld(ge=0, default=0.0, unit="bar", desc="最大充填圧")

    class Design:
        pass


class Propellant(Component, MultiInstance):
    """推進剤（消費物）。spec.mass_kg で初期充填量を表現し、質量集計に乗る。

    タンク側 (`PropellantTank`) と分離することで:
      - タンク自体の質量 = PropellantTank.spec.mass_kg
      - 推進剤質量      = Propellant.spec.mass_kg
    が独立して扱える。残量管理や ∆V 計算には initial / current の区別が要るが、
    まずは初期充填量のみを保持する。
    """

    propellant_type: str = fld(desc="推進剤種別: water / hydrazine / cold_gas 等")
    density_kg_per_l: float = fld(ge=0, default=0.0, unit="kg/L", desc="密度（参考値）")

    class Design:
        pass
