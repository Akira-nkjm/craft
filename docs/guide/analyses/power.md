# power（電源）

太陽電池発電・バッテリ容量・電力収支・モード集計。JERG-2-214/215 準拠。

## 共通定数

$$G_{sun} = 1361 \text{ W/m}^2$$

---

## 1. `solar_cell_power_at_temperature_w` [E]

**用途:** 温度補正されたセル電力。

**式:**

$$P_{cell}(T) = P_{ref} + \frac{dP_{max}}{dT}(T - T_{ref})$$

**入力:**

| 記号 | 説明 | 単位 |
|---|---|---|
| $P_{ref}$ | データシート最大電力（$T_{ref}$ 時） | W |
| $dP/dT$ | 温度係数 | W/°C |
| $T$ | 動作温度 | °C |
| $T_{ref}$ | 基準温度（既定 28°C）| °C |

**出力:** $P_{cell}(T)$ [W]

---

## 2. `solar_array_power_w` [B]

**用途:** アレイ出力。BOL/EOL いずれにも適用。

**式:**

$$P_{SA} = P_{cell}(T) \cdot N_{cells} \cdot \cos\theta \cdot \frac{1}{r_{AU}^2} \cdot \eta_{life}$$

**入力:**

| 記号 | 説明 | 単位 |
|---|---|---|
| $N_{cells}$ | 直列×並列 セル数 | — |
| $\cos\theta$ | 入射角コサイン | — |
| $r_{AU}$ | 太陽距離 | AU |
| $\eta_{life}$ | 寿命劣化（BOL=1） | — |

**出力:** $P_{SA}$ [W]

---

## 3. `eol_efficiency` [B]

**式:**

$$\eta_{EOL} = \eta_{BOL} \cdot \eta_r \cdot \eta_t$$

ここで $\eta_t = 1 + \gamma_T (T - T_{ref})$（$\gamma_T < 0$）。

**入力:** $\eta_{BOL}$, 放射線劣化 $\eta_r$（5 年で 0.85–0.92 典型）, 温度補正 $\eta_t$
**出力:** $\eta_{EOL}$ [—]

---

## 4. `required_solar_array_area_m2` [S]

**式:**

$$A_{SA} = \frac{P_{required}}{G_{sun} \cdot \eta_{EOL} \cdot \eta_{pack} \cdot \cos\theta}$$

**入力:**

| 記号 | 説明 | 単位 |
|---|---|---|
| $P_{required}$ | 必要発電量 | W |
| $\eta_{pack}$ | パネル充填率（≈0.9）| — |
| $\eta_{EOL}$ | EOL 効率 | — |
| $\cos\theta$ | 平均入射角 | — |

**出力:** $A_{SA}$ [m²]

---

## 5. `required_solar_array_power_w` [S]

**用途:** 1 軌道で蝕中・日照中の電力を賄うために発電すべき電力。

**式:**

$$P_{SA} = \frac{P_e \cdot t_e / \eta_{batt,d} + P_d \cdot t_d / \eta_{path}}{t_d}$$

**入力:**

| 記号 | 説明 | 単位 |
|---|---|---|
| $P_e, P_d$ | 蝕中・日照中消費電力 | W |
| $t_e, t_d$ | 蝕・日照時間 | h |
| $\eta_{batt,d}$ | バッテリ放電効率 | — |
| $\eta_{path}$ | 配電路効率 | — |

**出力:** $P_{SA}$ [W]
**備考:** 最悪条件は β=0 ケース × EOL × ピーク消費モードの組み合わせ。

---

## 6. `required_battery_capacity_wh` [S]

**式:**

$$C_{req} = \frac{P_e \cdot t_e}{\mathrm{DoD}_{max} \cdot \eta_{batt}}$$

**入力:**

| 記号 | 説明 | 単位 |
|---|---|---|
| $P_e$ | 蝕中消費電力 | W |
| $t_e$ | 最大蝕時間 | h |
| $\mathrm{DoD}_{max}$ | 許容深放電率 | — |
| $\eta_{batt}$ | 放電効率（≈0.95）| — |

**出力:** $C_{req}$ [Wh]

---

## 7. `battery_cycle_count` [B]

**式:** $N_{cycles} = T_{mission}/T_{orbit}$

**出力:** 充放電サイクル数。サイクル寿命との照合に使う。

---

## 8. `verify_battery_cycle_life` [V]

**用途:** 設計 DoD × 動作温度でメーカー曲線に対するサイクル寿命がミッション期間を満たすか。

**入力:** $\mathrm{DoD}_{op}$, $T_{cell}$, メーカー寿命表
**出力:** bool

---

## 9. `usable_capacity_wh` [B]

**式:** $C_{usable} = C_{rated} \cdot \mathrm{DoD} \cdot N_{cells,par}$

**出力:** 実効容量。EOL では rated を EOL 値で置き換え。

---

## 10. `battery_eol_capacity` [A]（既存）

**式:**

$$C_{EOL} = C_{BOL} \cdot (1 - D), \quad D = \min(0.2, k_{deg} \cdot N_{cycles})$$

**入力:** 初期容量、サイクル数、劣化係数（既定 0.0001）
**出力:** EOL 容量 [Wh]
**備考:** ad-hoc（$ system=None $）。簡易推定用。

---

## 11. `aggregate_mode_power_w` [B]（既存 `total_pdm_power_w` / `pdm_power_per_mode_w` の一般化）

**式:**

$$P_{mode} = \sum_i P_{i,spec} \cdot \mathbf{1}[mode_i = \text{on}]$$

**入力:** コンポネント毎の消費電力と mode フラグ
**出力:** モード別合計 [W]

---

## 12. `energy_balance_wh` [V]

**式:** $E_{balance} = (P_{gen} - P_{load}) \cdot t$

**入力:** 発電・消費・時間
**出力:** $E_{balance}$ [Wh]。**正であること** が運用成立条件。

---

## 13. `power_margin_pct` [V]

**式:** $M = (P_{gen} - P_{load})/P_{gen} \times 100$

**入力:** 発電・消費
**出力:** マージン [%]。**閾値 ≥ 20%** が一般的（PDR 段階）。

---

## 14. `pdm_voltage_compatible` [V]

**用途:** SAP 出力電圧が PCDU/DCDC の入力範囲に収まる。

**式:** $V_{min,SA}(T_{hot}, \text{EOL}) \leq V_{in,PDM} \leq V_{max,SA}(T_{cold}, \text{BOL})$

**入力:** セル温度範囲、直列数 $N_s$、DCDC 仕様
**出力:** bool

---

## 15. `verify_energy_balance_per_orbit` [V]

**式:**

$$E_{gen,orbit} - E_{consume,orbit} \geq E_{margin}$$

**入力:** 各モード duty 比、$P_{SA}(t)$、$P_{load}(mode)$
**出力:** bool — 1 周期のエネルギー収支。

---

## 16. `solar_array_voltage_eol` [V]

**式:**

$$V_{SA,EOL,hot} = N_s \cdot V_{mp}(T_{hot}) \cdot (1 - \delta_{rad}) \geq V_{bus,req}$$

**入力:** 直列セル数 $N_s$、高温時 $V_{mp}$、放射線電圧劣化、必要 BUS 電圧
**出力:** bool

---

## 17. `harness_voltage_drop_v` [V]

**式:** $\Delta V = I \cdot R \cdot L \cdot 2$（往復）

**入力:** 電流、線抵抗、長さ
**出力:** $\Delta V$ [V]。ハーネスマージン確認。

---

## 18. `required_orbit_energy_wh` [B]（既存）

**式:** $E_{req} = P_{load} \cdot t_{ecl} / 3600$

**出力:** 蝕中必要エネルギー [Wh]

---

## 19. `pcdu_channel_loading` [V]

**式:** 各チャネル：$I_{ch,peak} \leq I_{ch,rated}$、$I_{ch,avg} \leq I_{ch,avg,max}$

**入力:** チャネル毎の負荷リスト、定格電流
**出力:** チャネル毎 bool / 全体 OK / NG

---

## 依存関係

```
orbital.eclipse ─┐
                 ├── required_solar_array_power ── required_solar_array_area ── (構造へ)
mode_power ──────┤                                                              ├── A_SA
                 └── required_battery_capacity ── verify_dod ── (バッテリ選定へ)
                          │
                          └── battery_cycle_count ── verify_cycle_life
```
