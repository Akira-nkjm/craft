# propulsion（推進）

Tsiolkovsky 方程式・タンク設計・燃焼時間・推進剤バジェット。

## 共通定数

$g_0 = 9.80665$ m/s²。

---

## 1. `propellant_mass_kg` [S]

**用途:** ロケット方程式から必要推進剤質量。

**式:**（Tsiolkovsky）

$$m_p = m_{dry}\left(\exp\!\frac{\Delta v}{I_{sp} \, g_0} - 1\right)$$

**入力:**

| 記号 | 説明 | 単位 |
|---|---|---|
| $m_{dry}$ | 乾燥質量 | kg |
| $\Delta v$ | 必要 Δv | m/s |
| $I_{sp}$ | 比推力 | s |

**出力:** $m_p$ [kg]

---

## 2. `burn_time_s` [B]

**用途:** インパルス機動の燃焼時間。

**式:**（平均質量近似）

$$t_b = \frac{m_p \cdot I_{sp} \cdot g_0}{F}$$

または $t_b = \Delta v / (F / \bar m)$、$\bar m = m_{dry} + m_p/2$。

**入力:** 推進剤質量、Isp、推力
**出力:** $t_b$ [s]

---

## 3. `thrust_to_weight` [B]

**式:** $T/W = F / (m \cdot g_0)$

**出力:** [—]。低 T/W では gravity loss が顕著。

---

## 4. `gravity_loss_m_s` [E]

**用途:** 低推力エンジンでの ΔV ロス。

**式:**（重力場内連続噴射の簡易近似）

$$\Delta v_{loss} = g_0 \cdot t_b \cdot \sin\gamma$$

**入力:** 燃焼時間、飛行経路角
**出力:** $\Delta v_{loss}$ [m/s]

---

## 5. `tank_volume_m3` [S]

**式:**

$$V_{tank} = (m_p / \rho_{prop}) \cdot (1 + f_{ullage})$$

**入力:** 推進剤質量、密度、ullage 係数（既定 7.5%）
**出力:** $V_{tank}$ [m³]

---

## 6. `tank_wall_thickness_m` [S]

**用途:**（球形タンクの hoop 応力）

**式:**

$$t = \frac{P \cdot R \cdot \mathrm{FoS}}{2 \sigma_{yield}}$$

円筒タンクは $t = P R \, \mathrm{FoS} / \sigma_{yield}$（縦継ぎ目）。

**入力:** 内圧、半径、降伏応力、安全率（≈1.5）
**出力:** $t$ [m]

---

## 7. `tank_margin_of_safety` [V]

**式:** $\mathrm{MoS} = \sigma_{allow} / (\sigma_{applied} \cdot \mathrm{FoS}) - 1 \geq 0$

**入力:** 圧力 → hoop stress、許容応力、FoS
**出力:** MoS [—]

---

## 8. `total_delta_v_m_s` [B]

**用途:** ΔV バジェットの集計。

**式:**

$$\Delta v_{total} = (\Delta v_{insertion} + \Delta v_{SK} + \Delta v_{att} + \Delta v_{deorbit}) \cdot (1 + m_{margin})$$

**入力:** 各セグメント Δv、マージン係数（既定 10%）
**出力:** $\Delta v_{total}$ [m/s]

---

## 9. `propellant_budget_kg` [B]

**式:** `propellant_mass_kg(m_dry, total_delta_v, Isp)` を呼び出すか、各機動分の合算。

**出力:** [kg]

---

## 10. `verify_isp_feasibility` [V]

**用途:** 与えられたタンク容量・Isp でミッション ΔV が達成できるか。

**式:** $\Delta v_{achievable} = I_{sp} g_0 \ln((m_{dry} + m_{p,max})/m_{dry}) \geq \Delta v_{required}$

**出力:** bool

---

## 11. `pressurant_mass_kg` [S]

**用途:** ガス押し式タンクの加圧ガス（He/N2）量。

**式:**（理想気体・blowdown）

$$m_{press} = \frac{P_0 V_{tank}}{R_{gas} T} \cdot \frac{1}{1 - P_f/P_0}$$

**入力:** 初期/最終圧力、タンク体積、ガス定数、温度
**出力:** $m_{press}$ [kg]

---

## 12. `ion_engine_power_at_distance_w` [E]

**用途:** 深宇宙でのイオンエンジン出力（太陽電池依存）。

**式:** $P_{IE}(r) = P_{IE,1AU} / r_{AU}^2 \cdot \eta_{degradation}$

**入力:** 1AU 時電力、距離、劣化係数
**出力:** $P_{IE}$ [W]

---

## 13. `gimbal_misalignment_torque_nm` [E]

**用途:** スラスタ偏角による姿勢外乱トルク。

**式:** $T_{gimbal} = F \cdot \sin\theta_{gimbal} \cdot d_{cg}$

**入力:** 推力、偏角、重心からの距離
**出力:** $T_{gimbal}$ [Nm] — AOCS へ。

---

## 比推力の典型値

| 推進方式 | $I_{sp}$ [s] | 用途 |
|---|---|---|
| Cold gas (N2) | 60–80 | 小型姿勢制御 |
| Monopropellant (Hydrazine) | 220–230 | 軌道修正 |
| Bipropellant (NTO/MMH) | 280–310 | 大型機動 |
| Resistojet | 150–300 | 小型衛星 |
| Hall thruster | 1500–2500 | EOR, 深宇宙 |
| Ion (Gridded) | 3000–4000 | 深宇宙 |

---

## 依存関係

```
mission.delta_v_required ── propellant_mass ── tank_volume ── tank_wall_thickness ── tank_MoS
                                    │                           └── structure (mass)
                                    └── propellant_budget ── verify_isp_feasibility
thrust + mass ── burn_time
              └── gimbal_torque ── aocs.disturbance
```
