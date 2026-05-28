# orbital（軌道）

軌道力学・地上局可視・軌道寿命・Δv に関する解析。**他系の前提を与える**ため最初に確定させる。

## 共通定数

$$R_\oplus = 6371 \text{ km}, \quad \mu = 3.986 \times 10^{14} \text{ m}^3/\text{s}^2, \quad J_2 = 1.082 \times 10^{-3}$$

---

## 1. `orbital_period_s` [A]

**用途:** 軌道周期。ほぼ全ての時系列計算の基準。

**式:**

$$T = 2\pi \sqrt{\frac{a^3}{\mu}}, \quad a = R_\oplus + h$$

**入力:**

| 記号 | 説明 | 単位 |
|---|---|---|
| $h$ | 軌道高度 | km |

**出力:** $T$ [s] — 円軌道の周期。

---

## 2. `orbital_velocity_km_s` [A]

**式:** $v = \sqrt{\mu / a}$

**入力:** $h$ [km]
**出力:** $v$ [km/s] — 円軌道速度。

---

## 3. `eclipse_duration_s` [E]

**用途:** 電力・熱・バッテリの最悪条件入力。

**式:**（β = 0 最悪ケース、円柱影モデル）

$$\rho = \arcsin(R_\oplus / a)$$

$$t_{ecl} = \frac{\rho}{\pi} \cdot T$$

**入力:**

| 記号 | 説明 | 単位 |
|---|---|---|
| $h$ | 軌道高度 | km |
| $\beta$ | β 角（軌道面と太陽方向） | deg |

**出力:** $t_{ecl}$ [s] — 1 周期あたり最大日食時間。
**備考:** β > 0 のケースでは $t_{ecl}$ は短くなる。$\beta_{crit} = \arcsin(R_\oplus/a)$ を超えると永続日照。

---

## 4. `beta_angle_profile` [E]

**用途:** ミッション期間中の β 角変動（日食最大ケースの判定）。

**式:**

$$\sin\beta = \cos\delta_\odot \sin i \sin(\Omega - \alpha_\odot) + \sin\delta_\odot \cos i$$

**入力:** 軌道要素 $(i, \Omega)$, 日付（黄経 $\alpha_\odot$, 黄緯 $\delta_\odot$）
**出力:** $\beta(t)$ [deg] 時系列。

---

## 5. `sso_inclination_deg` [A]

**用途:** 太陽同期軌道の傾斜角を高度から逆算。

**式:** $\dot\Omega = -\frac{3}{2} n J_2 (R_\oplus/a)^2 \cos i / (1-e^2)^2 = +0.9856°/\text{day}$ を $i$ について解く。

**入力:** $h$ [km], 離心率 $e$（既定 0）
**出力:** $i_{SSO}$ [deg] — 典型値: 500–800 km → 97–99°。

---

## 6. `slant_range_km` [B]

**用途:** 地上局−衛星の斜距離。リンクバジェットの FSPL 入力。

**式:**

$$d = \sqrt{(R_\oplus + h)^2 - R_\oplus^2 \cos^2 \epsilon} - R_\oplus \sin \epsilon$$

**入力:** $h$ [km], 最小仰角 $\epsilon_{min}$ [deg]
**出力:** $d$ [km] — 最大スラントレンジ。

---

## 7. `max_nadir_angle_deg` [B]

**用途:** アンテナビーム幅要求の入力。

**式:** $\eta_{max} = \arcsin(R_\oplus \cos\epsilon / (R_\oplus + h))$

**入力:** $h$, $\epsilon_{min}$
**出力:** $\eta_{max}$ [deg]

---

## 8. `pass_duration_min` [B]

**用途:** 1 パスの可視時間。データダウンリンク量の基礎。

**式:**

$$\theta_{max} = \arccos\!\left(\frac{R_\oplus}{R_\oplus+h}\cos\epsilon\right) - \epsilon$$

$$t_{pass} \approx \frac{T}{\pi} \cdot \theta_{max}$$

**入力:** $h$, $\epsilon_{min}$, $T$
**出力:** $t_{pass}$ [min] — 中央パスでの可視時間（緯度依存は別途補正）。

---

## 9. `passes_per_day` [B]

**式:** $N_{pass} = 1440 / T_{min}$

**入力:** $T$ [min]
**出力:** $N$ [/day] — 上限値（地上局緯度・軌道形状で実効は減少）。

---

## 10. `daily_contact_time_min` [B]

**式:** $t_{day} = N_{pass} \cdot \overline{t_{pass}} \cdot N_{GS}$

**入力:** パス時間、パス数、地上局数 $N_{GS}$
**出力:** $t_{day}$ [min/day]

---

## 11. `atmospheric_density_kg_m3` [E]

**用途:** 軌道寿命・空力トルクの入力。

**式:** 標準大気テーブル（USSA76 or NRLMSISE）から高度で対数線形補間。

**入力:** $h$ [km]（200–800 範囲推奨）
**出力:** $\rho_a$ [kg/m³]

---

## 12. `orbital_lifetime_years` [S]

**用途:** デブリ軽減 25 年則の判定。

**式:**（指数大気近似）

$$\tau \approx -\frac{H}{\Delta h_{rev}} T \cdot \ln(1 - \Delta h_{rev}/h_0)$$

ここで $\Delta h_{rev} = 2\pi a^2 \rho_a / (B \cdot v)$、$B = m/(C_D A)$ は弾道係数。

**入力:**

| 記号 | 説明 | 単位 |
|---|---|---|
| $h_0$ | 初期高度 | km |
| $B$ | 弾道係数 $m/(C_D A)$ | kg/m² |
| $H$ | スケールハイト | km |

**出力:** $\tau$ [years]

---

## 13. `deorbit_delta_v_m_s` [S]

**用途:** EOL でのデオービット噴射量。

**式:**（Hohmann で近地点を $h_p$ に下げる）

$$\Delta v = \sqrt{\frac{\mu}{a}}\left(1 - \sqrt{\frac{2 r_p}{r_a + r_p}}\right)$$

**入力:** 現高度 $h$、目標近地点高度 $h_p$（既定 50 km — 大気圏再突入）
**出力:** $\Delta v$ [m/s]

---

## 14. `station_keeping_delta_v_per_year` [B]

**用途:** 年間軌道維持 Δv。

**経験値:**

| 軌道種別 | 主な摂動 | $\Delta v_{SK}$ [m/s/year] |
|---|---|---|
| LEO 500 km | 空気抵抗 | 0–10（高度依存）|
| SSO | 傾斜角ドリフト | 1–2 |
| GEO | E-W（経度）+ N-S（傾斜）| 50（うち N-S 45）|

**出力:** $\Delta v_{SK}$ [m/s/year]

---

## 15. `delta_v_budget_total` [B]

**用途:** ミッション総 Δv の集計。

**式:**

$$\Delta v_{total} = (\Delta v_{insertion} + \Delta v_{SK} \cdot T_{years} + \Delta v_{deorbit}) \cdot (1 + m_{margin})$$

**入力:** 各セグメント Δv、ミッション期間、マージン係数（既定 10%）
**出力:** $\Delta v_{total}$ [m/s] — 推進系サイジング入力。

---

## 16. `meets_25_year_rule` [V]

**用途:** IADC デブリ軽減ガイドライン。

**式:** $\tau \leq 25$ years を `orbital_lifetime_years` で判定。

**入力:** $h$, $B$
**出力:** bool

---

## 17. `j2_secular_drift` [E]

**用途:** SSO 設計の検証、長期軌道予測。

**式:**

$$\dot\Omega = -\frac{3}{2} n J_2 \frac{R_\oplus^2}{a^2 (1-e^2)^2} \cos i$$

$$\dot\omega = +\frac{3}{4} n J_2 \frac{R_\oplus^2}{a^2 (1-e^2)^2} (5\cos^2 i - 1)$$

**入力:** $a$, $e$, $i$
**出力:** $(\dot\Omega, \dot\omega)$ [deg/day]

---

## 18. `radiation_dose_per_year` [E]

**用途:** 放射線環境（[environment](environment.md) と相互参照）。

**入力:** 軌道, シールド厚 → 外部ツール SPENVIS 等で TID 算出。
**出力:** TID [Gy/year]
**備考:** Craft 内では SPENVIS 結果をパラメータとして取り込む簡易モデルに留める。

---

## 依存関係

```
period ──┬── eclipse ──┬── power.required_battery_capacity
         │             └── thermal.eclipse_temperature_drop
         ├── pass_duration ── comm.daily_downlink_capacity
         └── orbital_lifetime ── verify_25_year_rule
                                  └── deorbit_delta_v ── propulsion.propellant_mass
```
