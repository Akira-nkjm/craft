# comm（通信）

リンクバジェット・データレート・ダウンリンク容量。

## 共通定数

Boltzmann 定数 $k = -228.6$ dBW/K/Hz、光速 $c = 3 \times 10^8$ m/s。

---

## 1. `wavelength_m` [A]

**式:** $\lambda = c / f$

**入力:** $f$ [Hz]
**出力:** $\lambda$ [m]

---

## 2. `fspl_db` [E]

**用途:** 自由空間伝搬損失。

**式:**

$$L_{fs} = 20 \log_{10}(4\pi d / \lambda) = 92.45 + 20\log_{10}(d_{\text{km}}) + 20\log_{10}(f_{\text{GHz}})$$

**入力:** $d$ [km], $f$ [GHz]
**出力:** $L_{fs}$ [dB]

---

## 3. `antenna_gain_db` [B]

**用途:** 開口面アンテナの利得。

**式:**

$$G = 10 \log_{10}\!\left(\eta_a \frac{4\pi A}{\lambda^2}\right) = 10\log_{10}(\eta_a \pi^2 (D/\lambda)^2)$$

**入力:** 口径 $D$ [m], 周波数, 開口効率 $\eta_a$（≈0.55–0.65）
**出力:** $G$ [dBi]

---

## 4. `antenna_beamwidth_deg` [B]

**式:** $\theta_{3dB} \approx 70 \cdot \lambda / D$

**入力:** $D$, $\lambda$
**出力:** $\theta_{3dB}$ [deg]

---

## 5. `eirp_dbw` [B]

**式:**

$$\mathrm{EIRP} = 10\log_{10}(P_{tx}) + G_{tx} - L_{feed} - L_{point}$$

**入力:** 送信電力 $P_{tx}$ [W], 送信利得, 給電損失, 指向損失
**出力:** EIRP [dBW]

---

## 6. `system_noise_temp_k` [B]

**用途:** 受信系雑音温度。

**式:**

$$T_{sys} = T_{ant} \cdot 10^{-L_{feed}/10} + T_{feed}(1 - 10^{-L_{feed}/10}) + T_{LNA}$$

**入力:** アンテナ雑音 $T_{ant}$, フィード損失 $L_{feed}$, フィード温度, LNA 雑音温度
**出力:** $T_{sys}$ [K]

---

## 7. `g_over_t_db_k` [B]

**用途:** 受信性能指標。

**式:** $G/T = G_{rx} - L_{feed} - L_{point} - 10\log_{10}(T_{sys})$

**入力:** 受信利得・損失・$T_{sys}$
**出力:** G/T [dB/K]

---

## 8. `cn0_dbhz` [V]

**式:**

$$C/N_0 = \mathrm{EIRP} + G/T - L_{total} - k$$

ここで $k = -228.6$ dBW/K/Hz。

**入力:** EIRP, G/T, 総損失（FSPL + 大気 + その他）
**出力:** $C/N_0$ [dBHz]

---

## 9. `link_margin_db` [V]

**式:**

$$M = C/N_0 - 10\log_{10}(R_{bps}) - (E_b/N_0)_{req}$$

**入力:** $C/N_0$, データレート $R$, 必要 $E_b/N_0$（変調・FEC 依存）
**出力:** マージン [dB]

---

## 10. `link_margin_ok` [V]

**閾値:** ダウンリンク $M \geq 3$ dB、TT&C は $\geq 6$ dB が一般的。

**出力:** bool

---

## 11. `atmospheric_attenuation_db` [E]

**用途:** ITU-R P.676 簡易モデル。

**式:**（近似）

$$L_{atm} \approx (L_{O_2} + L_{H_2O}) / \sin\epsilon$$

仰角下限 5° でクランプ。

**入力:** 周波数、仰角、降雨率（option）
**出力:** $L_{atm}$ [dB]

---

## 12. `required_data_rate_bps` [B]

**式:** $R_{req} = V_{daily} / t_{contact,day}$

**入力:** 1 日データ量 [Mb], 1 日コンタクト時間 [s]
**出力:** $R_{req}$ [bps]

---

## 13. `daily_downlink_capacity_mb` [B]

**式:** $V_{cap} = R \cdot t_{contact} \cdot \eta_{link}$

**入力:** データレート, 1 日コンタクト時間, リンク効率（≈0.9）
**出力:** $V_{cap}$ [MB/day]

---

## 14. `data_volume_per_pass_mb` [B]

**式:** $V_{pass} = R \cdot t_{pass} \cdot \eta_{link}$

**出力:** [MB/pass]

---

## 15. `verify_downlink_volume` [V]

**式:** $V_{cap} \geq V_{daily} \cdot (1 + m_{margin})$

**出力:** bool

---

## 16. `doppler_shift_max_hz` [E]

**式:** $\Delta f = (v_r / c) \cdot f$、$v_r$ は最大視線速度

**入力:** 軌道速度、周波数
**出力:** $\Delta f$ [Hz] — 受信機 TCXO 引込範囲確認用。

---

## 17. `inter_satellite_link_budget` [V]

**用途:** 衛星間通信のリンクバジェット。

**式:** 上記と同じだが大気減衰なし、距離は ISL geometry から。

**出力:** マージン [dB]

---

## 依存関係

```
orbital.slant_range ── FSPL ──┐
                              ├── C/N0 ── link_margin ── verify
antenna_gain / EIRP ──────────┤
G/T (ground or sat) ──────────┘
                              
orbital.daily_contact ── required_data_rate ── verify_downlink_volume
                                              ├── daily_downlink_capacity
                                              └── cdh.daily_data_generation
```
