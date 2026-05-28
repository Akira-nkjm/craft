# thermal（熱制御）

熱収支・節点法・許容温度確認・ヒータ設計。**hot case と cold case の両端で成立する**ことが目標。

## 共通定数

$$G_{sun} = 1361 \text{ W/m}^2, \quad \sigma_{SB} = 5.67 \times 10^{-8} \text{ W/m}^2/\text{K}^4$$

地球 IR フラックス $q_{IR} \approx 237$ W/m²、アルベド係数 $a \approx 0.30$（平均）。

---

## 1. `solar_absorbed_power_w` [E]

**式:**

$$Q_{sun} = \alpha \cdot A \cdot G_{sun} \cdot \cos\theta / r_{AU}^2$$

**入力:**

| 記号 | 説明 | 単位 |
|---|---|---|
| $\alpha$ | 吸収率 | — |
| $A$ | 受光面積 | m² |
| $\cos\theta$ | 入射角 | — |
| $r_{AU}$ | 太陽距離 | AU |

**出力:** $Q_{sun}$ [W]

---

## 2. `albedo_absorbed_power_w` [E]

**式:**

$$Q_{alb} = \alpha \cdot A \cdot a \cdot G_{sun} \cdot F_{ea}$$

ビューファクター $F_{ea} \approx (R_\oplus/(R_\oplus+h))^2$（nadir）。

**入力:** $\alpha$, $A$, $a$, $h$
**出力:** $Q_{alb}$ [W]

---

## 3. `earth_ir_absorbed_power_w` [E]

**式:** $Q_{IR} = \epsilon \cdot A \cdot q_{IR} \cdot F_{ea}$

**入力:** 放射率 $\epsilon$, 面積、高度
**出力:** $Q_{IR}$ [W]

---

## 4. `total_heat_input_w` [B]

**式:** $Q_{in} = Q_{sun} + Q_{alb} + Q_{IR} + Q_{internal}$

**入力:** 上記 + 内部発熱（電源系から）
**出力:** $Q_{in}$ [W]

---

## 5. `equilibrium_temperature_k` [E]

**式:**（Stefan-Boltzmann 平衡）

$$T_{eq} = \left(\frac{Q_{in}}{\epsilon \cdot A_{rad} \cdot \sigma_{SB}}\right)^{1/4}$$

**入力:** 総入熱 $Q_{in}$、放射率 $\epsilon$、放熱面積 $A_{rad}$
**出力:** $T_{eq}$ [K]

---

## 6. `node_steady_state_temp_hot_k` [E]

**用途:** hot case（最大入熱・最大内部発熱・α/ε 劣化後）。

**式:** `equilibrium_temperature_k` を hot 条件入力で評価。
**出力:** $T_{hot}$ [K]

---

## 7. `node_steady_state_temp_cold_k` [E]

**用途:** cold case（蝕中・内部発熱最小・α/ε BOL）。

**入力:** $Q_{sun}=0$, $Q_{internal}=P_{min}$
**出力:** $T_{cold}$ [K]

---

## 8. `effective_absorptivity` [B]

**用途:** 複合表面の面積加重 α。

**式:**

$$\bar\alpha = \frac{\sum_i \alpha_i A_i}{\sum_i A_i}$$

**出力:** [—]

---

## 9. `effective_emissivity` [B]

**式:** $\bar\epsilon = \sum \epsilon_i A_i / \sum A_i$

---

## 10. `heater_power_required_w` [S]

**用途:** cold case で許容下限 $T_{min}$ を維持するための補助熱。

**式:**

$$Q_{htr} = \epsilon \sigma_{SB} A_{rad} T_{min}^4 - Q_{in,cold} - Q_{internal,min}$$

**入力:** $T_{min,req}$, 環境最小入熱、最小内部発熱
**出力:** $Q_{htr}$ [W] — 電源系へ反映。

---

## 11. `verify_component_temp_range` [V]

**用途:** 各コンポネントが許容範囲内にあるか。

**式:** $T_{min,allow} \leq T(t) \leq T_{max,allow}$ を hot/cold 両ケースで検証。

**入力:** ノード温度プロファイル、コンポネント許容温度
**出力:** bool / 違反コンポネント list

---

## 12. `thermal_margin_per_node` [V]

**用途:** Qualification マージン（典型 5–10°C）。

**式:** $\min(T_{max,qual} - T_{hot}, T_{cold} - T_{min,qual}) \geq \Delta T_{margin}$

**出力:** マージン [°C]

---

## 13. `radiator_area_required_m2` [S]

**式:**

$$A_{rad} = \frac{Q_{dissipate}}{\epsilon \sigma_{SB} T_{max}^4 - Q_{env,hot}}$$

**入力:** 放熱すべき内部発熱、許容最大温度、環境入熱
**出力:** $A_{rad}$ [m²]

---

## 14. `mli_layer_estimate` [S]

**用途:** MLI（多層断熱）層数の推定。

**式:**（経験式）

$$\epsilon^* \approx \frac{\epsilon_1 \epsilon_2}{n(\epsilon_1 + \epsilon_2 - \epsilon_1 \epsilon_2) + \epsilon_1 \epsilon_2}$$

**入力:** 内外側 ε、目標等価放射率
**出力:** 層数 $n$

---

## 15. `eclipse_temperature_drop_k` [E]

**用途:** 蝕中の温度降下推定。

**式:**（簡易、線形近似）

$$\Delta T \approx \frac{Q_{in,sun} - Q_{rad}}{m \cdot c_p} \cdot t_{ecl}$$

**入力:** 質量、比熱、蝕時間
**出力:** $\Delta T$ [K]

---

## 16. `view_factor_to_earth` [E]

**式:** $F_{se} = (R_\oplus / (R_\oplus + h))^2$（ナディア指向、円板近似）

**出力:** ビューファクター [—]

---

## 17. `mli_conductive_leak_w` [E]

**用途:** MLI 支持金具経由の熱漏れ。

**式:** $Q_{leak} = (k \cdot A / L) \cdot \Delta T$

**入力:** 熱伝導率、断面積、長さ、温度差
**出力:** $Q_{leak}$ [W]

---

## 依存関係

```
orbital.beta_angle ─┐
                    ├── solar_absorbed ──┐
attitude ───────────┘                    ├── total_heat_input ── equilibrium_temp ── verify_range
power.internal_w ────────────────────────┘                                          └── heater_power
                                                                                       └─→ power
```
