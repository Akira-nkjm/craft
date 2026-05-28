# aocs（姿勢制御）

外乱トルク・アクチュエータサイジング・指向誤差・スリュー時間。

## 共通定数

太陽輻射圧 $P_{sun} = 4.56 \times 10^{-6}$ N/m²、地磁場参照 $B_0 = 3.12 \times 10^{-5}$ T。

---

## 1. `gravity_gradient_torque_nm` [E]

**式:**

$$T_{gg} = \frac{3 \mu}{2 r^3} |I_z - I_x| \sin(2\phi)$$

**入力:**

| 記号 | 説明 | 単位 |
|---|---|---|
| $r$ | 軌道半径 | m |
| $I_z, I_x$ | 主慣性モーメント差 | kg·m² |
| $\phi$ | 姿勢誤差 | rad |

**出力:** $T_{gg}$ [Nm]

---

## 2. `aerodynamic_torque_nm` [E]

**用途:** LEO（特に <500 km）で支配的。

**式:**

$$T_{aero} = \tfrac{1}{2} \rho_a v^2 C_D A \cdot d_{cp-cg}$$

**入力:**

| 記号 | 説明 | 単位 |
|---|---|---|
| $\rho_a$ | 大気密度 | kg/m³ |
| $v$ | 軌道速度 | m/s |
| $C_D$ | 抵抗係数（≈2.2）| — |
| $A$ | 投影面積 | m² |
| $d_{cp-cg}$ | 圧力中心−重心オフセット | m |

**出力:** $T_{aero}$ [Nm]

---

## 3. `srp_torque_nm` [E]

**用途:** 高高度・GEO で支配的。

**式:**

$$T_{srp} = P_{sun} \cdot (1 + q_{refl}) \cdot A \cdot d_{cp-cg} / r_{AU}^2$$

**入力:** 反射率 $q_{refl}$, 投影面積、CP-CG オフセット、太陽距離
**出力:** $T_{srp}$ [Nm]

---

## 4. `magnetic_torque_nm` [E]

**式:** $T_{mag} = m_{res} \cdot B(h)$、$B(h) \approx B_0 (R_\oplus/r)^3$

**入力:** 残留磁気モーメント $m_{res}$ [A·m²], 高度
**出力:** $T_{mag}$ [Nm]

---

## 5. `total_disturbance_torque_nm` [B]

**式:** $T_{dist} = T_{gg} + T_{aero} + T_{srp} + T_{mag}$（直和、保守側）

**出力:** 総外乱トルク [Nm]。RW サイジングの入力。

---

## 6. `rw_momentum_capacity_nms` [B]

**式:** $H_{RW} = I_{wheel} \cdot \omega_{max}$

**入力:** RW 慣性、最大角速度
**出力:** $H_{RW}$ [Nms]

---

## 7. `rw_saturation_time_h` [B]

**用途:** アンローディング頻度の決定。

**式:**

$$t_{sat} = \frac{H_{RW} \cdot (1 - m_{margin})}{T_{dist,secular}}$$

**入力:** RW 角運動量、外乱トルクの永年成分、マージン
**出力:** $t_{sat}$ [h]

---

## 8. `rw_unloading_frequency_per_day` [B]

**式:** $f_{unload} = 24 / t_{sat}$

**出力:** [/day]。1 日 1 回程度に設計するのが典型。

---

## 9. `required_rw_torque_nm` [S]

**用途:** スリュー機動への対応。

**式:** $T_{RW,req} = I_{sc} \cdot \ddot\theta_{max}$

**入力:** 衛星慣性、最大角加速度要求
**出力:** $T_{RW,req}$ [Nm]

---

## 10. `required_rw_momentum_nms` [S]

**式:** $H_{RW,req} = I_{sc} \cdot \dot\theta_{max}$

**入力:** 衛星慣性、最大スリューレート
**出力:** $H_{RW,req}$ [Nms]

---

## 11. `mtq_torque_nm` [B]

**用途:** RW 角運動量ダンプ用 MTQ 性能。

**式:** $T_{MTQ} = m \cdot B(h) \cdot \eta_{geom}$、$\eta_{geom} \approx 0.5$（平均的姿勢）

**入力:** MTQ ダイポール $m$、軌道高度、幾何効率
**出力:** $T_{MTQ}$ [Nm]

---

## 12. `mtq_desaturation_time_s` [B]

**式:** $t_{desat} = H_{dump} / T_{MTQ}$

**入力:** ダンプ角運動量、MTQ トルク
**出力:** $t_{desat}$ [s]

---

## 13. `slew_time_s` [B]

**用途:** 機動コマンド設計。

**式:**（bang-bang、加減速対称）

$$t_{slew} = 2\sqrt{\theta / \ddot\theta_{max}}$$

**入力:** スリュー角 $\theta$ [rad]、最大角加速度 $\ddot\theta_{max} = T_{RW}/I_{sc}$
**出力:** $t_{slew}$ [s]

---

## 14. `total_pointing_error_deg` [B]

**用途:** Absolute Pointing Error（APE）の集計。

**式:**（RSS 合成）

$$\sigma_{APE} = \sqrt{\sigma_{ADS}^2 + \sigma_{ctrl}^2 + \sigma_{align}^2 + \sigma_{jitter}^2}$$

**入力:** 姿勢決定誤差、制御誤差、機械アライメント、ジッタ
**出力:** $\sigma_{APE}$ [deg]

---

## 15. `pointing_meets_requirement` [V]

**式:** $\sigma_{APE} \leq \sigma_{req}$

**出力:** bool

---

## 16. `attitude_determination_accuracy_deg` [B]

**用途:** センサ組み合わせから姿勢決定精度を推定。

**式:**（センサ毎の精度 RSS、簡易）

$$\sigma_{ADS} = \min\!\left(\sqrt{\sum_i \sigma_i^{-2}}\right)^{-1}$$

**入力:** sun sensor、magnetometer、star tracker 等の各精度
**出力:** $\sigma_{ADS}$ [deg]

---

## 17. `pointing_stability_jitter_arcsec` [V]

**用途:** ペイロード撮像時のスメア限界。

**式:** $\sigma_{jit} = $ RW imbalance × spectral response + 構造振動応答

**入力:** RW 静的/動的アンバランス、構造伝達関数
**出力:** $\sigma_{jit}$ [arcsec] — ペイロード要求と比較。

---

## 依存関係

```
orbital ──┬── eclipse ──┐
          └── density ──┤
                        ├── disturbance_torques ── RW sizing ── unloading_freq
mass_inertia ────────────┤                      └── slew_time
                         └── required_rw_torque/momentum
```
