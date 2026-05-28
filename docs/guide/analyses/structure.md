# structure（構造）

質量バジェット・重心・慣性モーメント・固有振動数・打ち上げ荷重応力。

## 共通定数

$g_0 = 9.80665$ m/s²。

---

## 1. `total_mass_kg` [B]

**式:** $M = \sum_i m_i$

**入力:** 全コンポネント質量
**出力:** $M$ [kg]

---

## 2. `mass_budget_per_subsystem` [B]

**式:** $M_j = \sum_{i \in j} m_i$

**入力:** コンポネント × 所属サブシステム
**出力:** dict[subsys → mass[kg]]

---

## 3. `mass_margin` [V]

**式:** $M_{margin} = (M_{limit} - M_{actual}) / M_{limit}$

**閾値:** PDR ≥ 20%, CDR ≥ 10%, FM ≥ 5%（typical）
**入力:** ロケット質量上限、現質量
**出力:** マージン [%] / bool

---

## 4. `center_of_mass_m` [B]

**式:**

$$\vec r_{cm} = \frac{\sum m_i \vec r_i}{\sum m_i}$$

**入力:** コンポネント質量と位置
**出力:** $(x, y, z)$ [m]
**備考:** 推進剤消費で時間変化。BOL/MOL/EOL の 3 ケース推奨。

---

## 5. `moment_of_inertia_tensor` [B]

**用途:** AOCS 入力。

**式:**（点質量近似）

$$I_{ij} = \sum_k m_k (\delta_{ij} |\vec r_k|^2 - r_{k,i} r_{k,j})$$

**入力:** コンポネント質量と位置（重心原点）
**出力:** 3×3 テンソル [kg·m²]

---

## 6. `principal_inertias_kg_m2` [B]

**式:** $I_{ij}$ の固有値分解

**出力:** $(I_x, I_y, I_z)$ と主軸方向。
**備考:** 重力傾度トルク・スピン安定性の入力。

---

## 7. `quasi_static_stress_pa` [V]

**用途:** 打ち上げ準静的荷重に対する応力。

**式:**

$$\sigma = \frac{m \cdot a_{load} \cdot g_0}{A_{section}}$$

**入力:** 質量、荷重係数（軸方向 $\sim 6$g, 横方向 $\sim 3$g）、断面積
**出力:** $\sigma$ [Pa]

---

## 8. `stress_margin_of_safety` [V]

**式:**

$$\mathrm{MoS} = \frac{\sigma_{allow}}{\sigma_{applied} \cdot \mathrm{FoS}} - 1 \geq 0$$

**入力:** 許容応力、作用応力、安全率（既定 1.25 yield, 1.4 ultimate）
**出力:** MoS [—]

---

## 9. `natural_frequency_hz` [V]

**式:**（単純な梁・SDOF 近似）

$$f_n = \frac{1}{2\pi}\sqrt{k / m}$$

FEM の詳細解析結果も同じ関数で照合可能。

**入力:** 等価剛性 $k$、質量 $m$
**出力:** $f_n$ [Hz]

---

## 10. `natural_frequency_ok` [V]

**閾値:**（典型ロケット要求）

| 軸 | 要求 |
|---|---|
| 軸方向 | $\geq 50$ Hz |
| 横方向 | $\geq 15$ Hz |

**入力:** $f_n$, 軸方向
**出力:** bool

---

## 11. `random_vibration_grms` [V]

**用途:** ランダム振動応答。打ち上げ環境試験仕様。

**式:**（SDOF 近似応答）

$$G_{rms}^2 = \int_0^\infty |H(f)|^2 \cdot \mathrm{PSD}(f) \, df$$

伝達関数 $|H|^2 = 1/[(1-(f/f_n)^2)^2 + (2\zeta f/f_n)^2]$

**入力:** PSD（ロケット仕様）、$f_n$、減衰比 $\zeta$（≈0.02–0.05）
**出力:** $G_{rms}$ [g]

---

## 12. `shock_response_envelope_ok` [V]

**用途:** 分離衝撃に対するコンポネント耐性確認。

**入力:** SRS（衝撃応答スペクトル）、コンポネント定格
**出力:** bool — 各帯域で envelope 超過なし。

---

## 13. `coupled_loads_analysis_summary` [V]

**用途:** ロケット側 CLA 結果との整合確認。

**入力:** CLA 結果テーブル（モード・荷重ケース）、コンポネント定格
**出力:** 各コンポネント MoS list

---

## 14. `fairing_volume_ok` [V]

**式:** 衛星の最大寸法がフェアリング静的包絡線（dynamic envelope 含む）に収まる。

**入力:** 衛星 envelope (CAD), フェアリング図面
**出力:** bool / 干渉箇所 list

---

## 15. `rail_dimension_check` [V]

**用途:** CubeSat レール仕様（P-POD/ISIPOD）整合。

**入力:** レール寸法、突起物高さ、deployer 規格
**出力:** bool

---

## 16. `honeycomb_panel_buckling_margin` [V]

**用途:** ハニカムサンドイッチ面材座屈チェック。

**式:**（面材局部座屈）

$$\sigma_{cr} = \frac{\pi^2 E}{12(1-\nu^2)}\left(\frac{t_f}{a}\right)^2 \cdot k$$

**入力:** 面材材料、厚さ、寸法
**出力:** MoS

---

## 17. `deployable_first_mode_hz` [V]

**用途:** SAP・アンテナ展開構造の固有振動数（片持ち梁モデル）。

**式:** $f_1 = (1.875)^2 / (2\pi L^2) \sqrt{EI/(\rho A)}$

**入力:** 長さ、剛性、線密度
**出力:** $f_1$ [Hz]

---

## 18. `mmod_impact_probability` [E]

**用途:** 微小デブリ・流星衝突の確率評価。

**式:**（Poisson）

$$P_{impact} = 1 - \exp(-F \cdot A \cdot T)$$

**入力:** flux $F$ [#/m²/s]、暴露面積、時間
**出力:** $P_{impact}$ [—]

---

## 依存関係

```
components ──┬── total_mass ── mass_margin
             ├── center_of_mass ──┐
             └── moment_of_inertia (cm 原点) ── aocs
                                 │
launcher_QSL ── quasi_static_stress ── stress_margin
launcher_PSD ── random_vibration_grms
launcher_SRS ── shock_envelope
```
