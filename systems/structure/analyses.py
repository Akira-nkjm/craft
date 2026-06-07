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

    CSV §1.structure CAD-DD 列積み上げ値 ~1038g を再現することを意図する。
    フライト確定質量 8.925kg (S2E ini) は全サブシステム込み（光学系・推進剤・ハーネス含む）の値。
    この analysis は構体系単体の積み上げチェックに使う。
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
    desc="フライト確定質量（S2E ini 値 8.925 kg）に対する構体系質量マージン [%]"
    "（toolbox.structure.mass）",
)
def structure_mass_margin_pct(
    actual_mass_kg: Annotated[float, vq.Ref("@total_structure_mass_kg")],
) -> float:
    """構体系積み上げ質量とフライト確定値（8.925 kg）の差を割合で表す。

    フライト確定質量 8.925 kg は全サブシステム込みの値なので、構体系単体（~1038 g）との
    比較では構体 mass_limit を 8.925 kg とし、残余（他サブシステム + 未計上分）のバジェットを
    確認する用途に使う。正値 = 構体系が limit より軽い（余裕あり）。
    mass_limit_kg は S2E フライト確定質量 [S2E satellite_structure.ini]。
    """
    mass_limit_kg = 8.925  # [確定値 S2E satellite_structure.ini]
    return tb_mass_margin_pct(actual_mass_kg, mass_limit_kg)


@analysis(
    verify=True,
    desc="構体系質量が全機フライト確定質量 8.925 kg を超えていないか",
)
def verify_structure_mass_within_limit(
    actual_mass_kg: Annotated[float, vq.Ref("@total_structure_mass_kg")],
) -> bool:
    """構体系積み上げ質量が全機フライト確定値 8.925 kg 以内か検証する。

    構体系単体は ~1038 g の見込みなので通常 pass するが、
    部品追加・見直しで構体系が突出していないかのガードとして機能する。
    """
    mass_limit_kg = 8.925  # [確定値 S2E satellite_structure.ini]
    return actual_mass_kg <= mass_limit_kg


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
