# environment（宇宙環境・放射線）

TID・SEE・変位損傷・シールド低減・MMOD。**TID 絶対値は SPENVIS 等で算出し、Craft は判定・マージン計算を担当**。

---

## 1. `orbit_tid_per_year_gy` [E]

**用途:** 軌道別 TID（外部ツール参照）。

**典型値**（ALICE シリーズや SPENVIS 出力の概算）:

| 軌道 | TID [krad/year] (Al 2 mm 後) |
|---|---|
| LEO 400 km, $i=51.6°$ | 0.5–1 |
| SSO 600 km | 1–3 |
| MEO | 10–100 |
| GEO | 5–20 |
| HEO (Van Allen) | >100 |

**入力:** 軌道、シールド厚（簡易テーブル）
**出力:** TID [Gy/year]

---

## 2. `shielding_tid_reduction_factor` [B]

**用途:** Al シールド厚による TID 低減比。

**式:**（経験的指数モデル）

$$f_{shield}(t_{mm}) = \exp(-\lambda \cdot t_{mm})$$

$\lambda$ は粒子種・エネルギー依存（典型 0.5–1.0 /mm）。

**入力:** Al シールド厚 [mm]
**出力:** 低減比 [—]

---

## 3. `tid_design_allowable_gy` [B]

**用途:** RDF（Radiation Design Factor, 既定 2.0）を考慮した設計許容 TID。

**式:** $\mathrm{TID}_{design} = \mathrm{TID}_{component} / \mathrm{RDF}$

**出力:** [Gy]

---

## 4. `tid_margin_ok` [V]

**式:** $\mathrm{TID}_{design} \geq \mathrm{TID}_{orbit} \cdot T_{mission}$

**出力:** bool

---

## 5. `seu_rate_per_day` [E]

**用途:** SEU（Single Event Upset）発生率。

**式:**（飽和断面積モデル、線形近似）

$$R_{SEU} = \sigma_{sat} \cdot \Phi_{HZE} \cdot N_{bits} \cdot 86400$$

**入力:** 飽和断面積 $\sigma_{sat}$ [cm²/bit], HZE flux $\Phi$ [/cm²/s], ビット数
**出力:** SEU events/day

---

## 6. `seu_mitigation_target_events_per_day` [V]

**用途:** SEU 対策（EDAC, scrubbing）後の達成目標との比較。

**入力:** 観測 SEU rate, EDAC error correction capability
**出力:** bool / 検出不能 SEU 残存数

---

## 7. `displacement_damage_dose` [E]

**用途:** 太陽電池・撮像素子の劣化評価。

**式:** $\mathrm{DDD} = \Phi_p \cdot \mathrm{NIEL}$

**入力:** 陽子フルエンス $\Phi_p$ [/cm²], NIEL [MeV·cm²/g]
**出力:** DDD [MeV/g]

---

## 8. `solar_cell_radiation_degradation` [E]

**用途:** 太陽電池の EOL 残存性能（[power](power.md) の入力）。

**式:**（経験式）

$$\eta_{remain} = 1 - C \cdot \log_{10}(1 + \Phi_p / \Phi_0)$$

**入力:** セル材料、陽子フルエンス
**出力:** 残存効率比 [—]

---

## 9. `single_event_latchup_critical` [V]

**用途:** SEL（Single Event Latchup）危険部品の識別。

**入力:** 部品 SEL threshold LET、軌道 HZE LET 分布
**出力:** bool — `True` ならラッチアップ防止回路（current limiter）必須。

---

## 10. `proton_fluence_per_year` [E]

**入力:** 軌道、シールド厚
**出力:** $\Phi_p$ [/cm²/year]

---

## 11. `electron_fluence_per_year` [E]

**入力:** 軌道（Van Allen 通過回数）、シールド
**出力:** $\Phi_e$ [/cm²/year]

---

## 12. `solar_event_extra_dose` [E]

**用途:** 太陽プロトンイベント（SPE）の追加 TID。

**入力:** ミッション期間、太陽活動レベル
**出力:** SPE 追加 TID [Gy]

---

## 依存関係

```
orbit + shield ──┬── orbit_tid ── × T_mission ── tid_margin_ok ←── component.TID_rating
                 ├── proton_fluence ── solar_cell_degradation ── power.eol_efficiency
                 ├── proton_fluence ── DDD
                 └── HZE flux ── seu_rate ── seu_mitigation
                             └── SEL ── current limiter design
```
