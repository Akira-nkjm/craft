"""Thermal system configurations。

熱解析のモデルパラメータ（放熱面積・内部発熱）を data 駆動にするための config。
表面光学特性（α/ε）は PanelSurface、日照割合は orbital を参照し、ここには
熱モデル固有の面積・内部発熱（single source）を置く。
"""

from craft.schema import Config, fld


class ThermalModel(Config):
    """熱解析モデルのパラメータ。

    Source: [S2E-AOBC] satellite_structure.ini（面積）、S2E heatload.csv（内部発熱）。
    詳細 CAD / 熱解析で精緻化予定（[推定] 含む）。
    """

    sap_thermal_area_m2: float = fld(
        ge=0, default=0.1312, unit="m^2", desc="SAP 受熱面積（軌道熱入力評価用）[推定]"
    )
    radiator_area_m2: float = fld(
        ge=0, default=0.08, unit="m^2", desc="機体放熱面（PX/MX）面積 [S2E-AOBC]"
    )
    internal_dissipation_w: float = fld(
        ge=0,
        default=10.57,
        unit="W",
        desc="内部発熱合計（AOCS+BOARD+BP+COMM+BAT）[S2E heatload.csv]",
    )
