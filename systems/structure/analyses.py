"""Structure system analyses。

veriq 制約: scope に貼られる calculation / verification の引数は全て
`Annotated[..., vq.Ref(...)]` であること。生のパラメータが必要なら
`system=None` で ad-hoc 化する。

出典: ONGLAISAT S2E satellite_structure.ini / mass_inertia_breakdown.csv §1.structure
"""

from typing import Annotated

import veriq as vq
from toolbox.structure.mass import mass_margin_pct as tb_mass_margin_pct

from craft.schema import analysis


@analysis(
    desc="構体系コンポーネントの総質量 [kg]"
    "（Frame + Panel + Bracket + Hinge + HRM + Fastener + Harness）",
)
def total_structure_mass_kg(
    frames: Annotated[vq.Table, vq.Ref("$.frames")],
    structural_panels: Annotated[vq.Table, vq.Ref("$.structural_panels")],
    brackets: Annotated[vq.Table, vq.Ref("$.brackets")],
    hinges: Annotated[vq.Table, vq.Ref("$.hinges")],
    hold_release_mechanisms: Annotated[vq.Table, vq.Ref("$.hold_release_mechanisms")],
    fasteners: Annotated[vq.Table, vq.Ref("$.fasteners")],
    harnesses: Annotated[vq.Table, vq.Ref("$.harnesses")],
) -> float:
    """構体系の積み上げ質量合計 [kg]。

    Frame/Panel/Bracket（CSV §1.structure CAD-DD ~1038g）に加え、Hinge/HRM/
    Fastener/Harness の推定分を含む**構体サブシステム全体**の積み上げ。
    CSV §1（frames 主体）より大きくなるのは展開機構・締結・配線を含むため。
    フライト確定質量 8.925kg (S2E ini) は全サブシステム込みの全機質量で、別途
    mission::total_bus_mass_kg と突き合わせる（mission::verify_mass_budget_reconciled）。
    """
    tables = [
        frames,
        structural_panels,
        brackets,
        hinges,
        hold_release_mechanisms,
        fasteners,
        harnesses,
    ]
    total = 0.0
    for table in tables:
        if not table:
            continue
        for entry in table.values():
            qty = entry.design.quantity if hasattr(entry.design, "quantity") else 1
            total += entry.spec.mass_kg * qty
    return total


@analysis(
    desc="構体系質量がフライト全機質量に占める割合の余裕 [%]（toolbox.structure.mass）",
    imports=["mission"],
)
def structure_mass_margin_pct(
    actual_mass_kg: Annotated[float, vq.Ref("@total_structure_mass_kg")],
    flight_mass_kg: Annotated[float, vq.Ref("$.missionprofile.flight_mass_kg", scope="mission")],
) -> float:
    """構体系質量が全機質量に占める割合の余裕 [%]。

    `mass_margin_pct(structure, flight)` = (1 − structure/flight)×100。
    基準の全機質量は data.toml の `missionprofile.flight_mass_kg` を参照する。
    全機質量バジェットの突き合わせ自体は mission::verify_mass_budget_reconciled で行う。
    """
    return tb_mass_margin_pct(actual_mass_kg, flight_mass_kg)


@analysis(
    verify=True,
    desc="構体系質量が全機質量の妥当な割合（<= 40%）に収まるか",
    imports=["mission"],
)
def verify_structure_mass_fraction(
    actual_mass_kg: Annotated[float, vq.Ref("@total_structure_mass_kg")],
    flight_mass_kg: Annotated[float, vq.Ref("$.missionprofile.flight_mass_kg", scope="mission")],
) -> bool:
    """構体系質量が全機フライト質量の 40% 以内かを検証する。

    構体は通常 全機の 20–35% 程度。40% を超えるなら構体系の質量計上が過大
    （または他サブシステムの未計上）を示すガード。基準の全機質量は data.toml の
    `missionprofile.flight_mass_kg` を参照。全機質量そのものの整合は
    mission::verify_mass_budget_reconciled が担う。
    """
    return actual_mass_kg <= 0.40 * flight_mass_kg


@analysis(
    desc="慣性テンソル対角成分 (Ixx, Iyy, Izz) [kg m²]（S2E ini 確定値）",
)
def inertia_tensor_diagonal_kg_m2(
    frames: Annotated[vq.Table, vq.Ref("$.frames")],  # noqa: ARG001
) -> dict[str, float]:
    """フライト確定慣性テンソル対角成分を返す。

    値は S2E satellite_structure.ini から直接引用（全機慣性テンソル）。
    frames を引数として取るのは veriq の依存グラフ登録のためであり、計算には使用しない。
    TODO: 将来的には mass_inertia_breakdown.csv 各部品慣性テンソルを積み上げる実装に置換。
    出典: S2E satellite_structure.ini [KINEMATIC_PARAMETERS]
    """
    # フライト確定値 [S2E satellite_structure.ini]
    return {
        "Ixx": 0.151,  # [確定値 S2E]
        "Iyy": 0.164,  # [確定値 S2E]（最大慣性軸）
        "Izz": 0.108,  # [確定値 S2E]（最小 = 長軸 Z）
    }
