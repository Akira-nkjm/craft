# launch_env（打ち上げ環境）

フェアリング・ランダム振動・衝撃・CLA。多くは [structure](structure.md) と重複するが、**ロケット ICD 由来の制約**を独立にまとめる。

---

## 1. `fairing_volume_fit` [V]

**用途:** 衛星 envelope（収納時・展開機構収納）がフェアリング静的包絡線内に収まる。

**入力:** 衛星 CAD envelope, フェアリング ICD（典型: SpaceX Falcon 9, JAXA H3, Rocket Lab Electron, ISRO PSLV/SSLV）
**出力:** bool / 干渉箇所

**備考:** 静的+動的（音響加振による変形）両方の包絡線で確認。

---

## 2. `rail_dimension_check` [V]

**用途:** CubeSat deployer（P-POD/ISIPOD/EXOpod）規格との整合。

**主な ICD:**

| 規格 | 単位寸法 | 質量上限 |
|---|---|---|
| 1U | 100×100×113.5 mm | 1.33 kg |
| 3U | 100×100×340.5 mm | 4 kg |
| 6U | 226.3×100×366 mm | 12 kg |
| 12U | 226.3×226.3×366 mm | 24 kg |

**入力:** 衛星寸法、突起物高さ、質量
**出力:** bool / 違反項目

---

## 3. `quasi_static_load_per_axis_g` [V]

**用途:** ロケット QSL（Quasi-Static Load）に対する応力評価。

**典型値:**

| ロケット | 軸 [g] | 横 [g] |
|---|---|---|
| Falcon 9 | 6.0 | 2.0 |
| H3 | 5.5 | 2.5 |
| Electron | 6.5 | 2.0 |

**式:** [structure.quasi_static_stress_pa](structure.md#7-quasi_static_stress_pa-v) に渡す
**出力:** 各軸での MoS

---

## 4. `acoustic_loading_db` [E]

**用途:** 打ち上げ時音響加振（フェアリング内 OASPL 130–140 dB 典型）。

**入力:** ロケット音響スペクトル、衛星表面積、Q 値
**出力:** 等価ランダム振動 PSD（[structure.random_vibration_grms](structure.md#11-random_vibration_grms-v) の入力）

---

## 5. `random_vibration_qualification` [V]

**用途:** 加振試験仕様（PSD level + duration）に対するコンポネント耐性。

**入力:** ロケット PSD（typical 7.5–10 g_rms, 20–2000 Hz）, qualification factor (×1.5)
**出力:** 各コンポ MoS

---

## 6. `shock_response_envelope_ok` [V]

**用途:** ペイロード分離・フェアリング分離・段間分離による衝撃応答。

**典型 SRS:** 100–10000 Hz, peak 1000–5000 g（分離面付近）

**入力:** SRS curves, コンポネント定格
**出力:** 全コンポ envelope クリア bool

---

## 7. `coupled_loads_analysis_check` [V]

**用途:** ロケット側 CLA（Coupled Loads Analysis）結果との照合。

**入力:** CLA テーブル（モード形状 × 荷重ケース）, 衛星 NASTRAN モデル整合
**出力:** 各モード MoS / モード周波数比較

---

## 8. `depressurization_rate_ok` [V]

**用途:** 打ち上げ中のフェアリング内減圧速度（密閉部品のベント設計）。

**典型値:** 100 mbar/s（最大）

**入力:** 密閉容器ベント面積、容積、減圧プロファイル
**出力:** ベント内圧履歴、最大差圧

---

## 9. `thermal_during_ascent` [V]

**用途:** 上昇中の熱環境（フェアリング内 → 開放後）。

**入力:** フェアリング内温度プロファイル、開放後の自由分子流加熱
**出力:** 表面ピーク温度（[thermal](thermal.md) と相互参照）

---

## 10. `static_envelope_dynamic_margin` [V]

**用途:** 動的包絡線（音響振動による瞬間変形）を含むクリアランス。

**典型マージン:** 静的包絡線から 25–50 mm 内側

**入力:** 衛星寸法、フェアリングデータ
**出力:** 最小クリアランス [mm]

---

## ロケット ICD の確認項目（チェックリスト）

- [ ] 静的・動的包絡線
- [ ] 質量上限・重心制約
- [ ] 軸/横 QSL
- [ ] ランダム振動 PSD（qualification spec）
- [ ] サイン振動（low frequency, 5–100 Hz）
- [ ] 衝撃 SRS（フェアリング分離・段間分離・衛星分離）
- [ ] 音響 OASPL とスペクトル
- [ ] 減圧プロファイル
- [ ] 上昇中熱環境
- [ ] 電磁適合性（EMC）
- [ ] 清浄度（particle/molecular contamination）

---

## 依存関係

```
launcher ICD ──┬── fairing_envelope ── fairing_volume_fit
               ├── QSL ── structure.quasi_static_stress
               ├── PSD ── structure.random_vibration
               ├── SRS ── shock_response_envelope_ok
               ├── CLA ── coupled_loads_check
               ├── thermal ── thermal_during_ascent
               └── depressurization ── vented containers
```
