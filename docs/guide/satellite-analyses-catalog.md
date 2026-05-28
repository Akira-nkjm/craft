# 衛星解析カタログ（網羅版）

Craft の `systems/<sys>/analyses/` に実装する解析関数を、サブシステム単位で網羅的に列挙したカタログ。各解析には目的を示す**タグ**（後述）を付け、入力／出力を一行で要約する。実装の優先順は最後の「実装優先度」セクションを参照。

各解析の**詳細**（計算式・入力記号・出力単位・備考）は [解析リファレンス](analyses/index.md) を参照（サブシステム毎に 1 ページ）。

## 凡例（解析タグ）

| タグ | 意味 | 典型的な使い方 |
|------|------|----------------|
| **[B]** | 予算（budget） | 合算とマージン確認 |
| **[S]** | サイジング | コンポーネント寸法・容量の決定 |
| **[V]** | 検証（verify） | 制約充足チェック — `@analysis(verify=True)` で実装 |
| **[T]** | トレード | 設計選択肢の比較 |
| **[E]** | 環境応答 | 軌道・熱・放射線 等の外乱に対する応答 |
| **[A]** | ad-hoc | `system=None` の一発計算（API/CLI 用） |

## 出典

- **[ut-issl/spacecraft-design-marimo](https://github.com/ut-issl/spacecraft-design-marimo/tree/refactor/component-first-3axis)** — Craft と同等の目的を持つ先行実装。`src/analysis/<subsys>/<theme>.py` 構造の純関数群（Pydantic 非依存）と、`docs/satellite-design/{INITIAL_DESIGN_CALCULATIONS,SATELLITE_CORE_CALCULATIONS}.md` を参照。**本カタログで最も参考にした単一資料。**
- **JAXA JERG 設計標準** — JERG-2-000B（宇宙機設計）/ 100（システム）/ 130（試験）/ 200（電気）/ 214（電源）/ 215（太陽電池パドル）/ 400 系（通信）
- **SMAD**（Wertz & Larson, *Space Mission Analysis and Design*）/ **NASA SSRI Knowledge Base** / **CubeSat handbook**
- **Drive 内資料**: 「電源系紹介ドキュメント」(2026/3/30, GEO-X 大井) ほか

---

## 1. mission（ミッション・運用）

ミッション解析は他系の前提を生む。**最初に固める。**

| 解析 | 種別 | 入力 | 出力 |
|---|---|---|---|
| `operation_mode_timeline` | [B] | mode_configs, orbit | モード遷移タイムライン（s/orbit）|
| `mode_duty_cycle` | [B] | timeline | モード別 duty 比 |
| `mission_lifetime_orbits` | [S] | lifetime_years, orbital_period | 軌道周回数 |
| `eclipse_to_sunlit_ratio_per_mode` | [E] | mode_timeline, eclipse_s | モード × 蝕の重ね合わせ |
| `verify_mode_exclusive` | [V] | mode_configs | 同時 ON 不可モードの排他確認 |
| `mission_success_criteria_coverage` | [V] | success_metrics | フル/エクストラサクセス充足 |

## 2. orbital（軌道）

| 解析 | 種別 | 入力 | 出力 |
|---|---|---|---|
| `orbital_period_s` | [A] | semi-major axis | 周期 [s] |
| `eclipse_duration_s` | [E] | orbit, beta_angle | 1 周期あたり蝕時間 |
| `beta_angle_profile` | [E] | orbit, epoch, mission_lifetime | β 角の年間変動 |
| `sun_vector_in_body_frame` | [E] | orbit, attitude_law | 時系列 sun vector |
| `ground_station_access_per_pass` | [B] | orbit, GS lat/lon, min_elevation | 1 パスあたり可視時間 |
| `ground_station_contact_per_day` | [B] | access, orbit | 1 日の合計通信時間 |
| `j2_secular_drift` | [E] | orbit | RAAN/AoP 摂動 |
| `atmospheric_density_at_altitude` | [E] | altitude, solar_flux | 大気密度 |
| `drag_decay_lifetime_years` | [S] | mass, Cd, A, altitude | 軌道寿命 |
| `station_keeping_delta_v_per_year` | [B] | orbit_type, perturbations | 年間 ΔV |
| `delta_v_budget_total` | [B] | rendezvous + SK + EOL deorbit | ミッション全 ΔV |
| `verify_25_year_deorbit` | [V] | orbit, ballistic_coef | IADC 25 年則充足 |
| `radiation_dose_per_year` | [E] | orbit, shielding | TID [krad/year] |

## 3. power（電源）

> JERG-2-214 / JERG-2-215 準拠。GEO-X 資料の項目を網羅。

| 解析 | 種別 | 入力 | 出力 |
|---|---|---|---|
| `total_pdm_power_w` ★既存 | [B] | pdms, mode | 消費電力合計 |
| `pdm_power_per_mode_w` ★既存 | [B] | pdms, modes | モード別電力 |
| `required_orbit_energy_wh` ★既存 | [B] | power, eclipse | 蝕中必要 Wh |
| `solar_array_power_bol_w` | [S] | SAP area, eff, sun_vec | BOL 発電量 |
| `solar_array_power_eol_w` | [S] | BOL, degradation, years | EOL 発電量（高温EOL条件） |
| `solar_array_voltage_eol` | [V] | series_count, cell_V, temp | EOL 電圧 > BUS 必要電圧 |
| `solar_array_sizing` | [S] | required_power, eff, margin | 必要 SAP 面積/直並列数 |
| `battery_capacity_required_wh` | [S] | eclipse_load, DoD, margin | 必要容量 |
| `battery_dod_per_mode` | [V] | capacity, mode_load, eclipse | DoD < DoD_max 充足 |
| `battery_eol_capacity` ★既存(ad-hoc) | [A] | initial, cycles | EOL 容量 |
| `battery_cycle_life` | [V] | DoD profile, years | 充放電サイクル耐性 |
| `bus_voltage_margin` | [V] | SAP V, BAT V, BUS req | 動作電圧マージン |
| `pcdu_channel_loading` | [V] | PDM per channel, channel_A_max | チャネル電流マージン |
| `pcdu_efficiency` | [B] | losses | 配電効率 |
| `power_budget_per_mode_with_margin` | [B] | gen, load, margin | モード毎 P_gen − P_load |
| `verify_energy_balance_per_orbit` | [V] | gen/orbit, load/orbit | 周期エネルギー収支 ≥ 0 |
| `solar_array_temperature_profile` | [E] | sun, attitude, thermal | SAP 温度時系列 |
| `harness_voltage_drop` | [V] | I, R, length | ハーネス電圧降下 |

## 4. thermal（熱）

> JERG-2-310/320 系。STM 熱真空試験の解析モデル相関の基盤。

| 解析 | 種別 | 入力 | 出力 |
|---|---|---|---|
| `solar_flux_at_orbit` | [E] | orbit, sun_dist | 太陽放射照度 |
| `albedo_flux_at_attitude` | [E] | nadir_angle, alt | 地球アルベド |
| `earth_ir_flux` | [E] | alt, attitude | 地球赤外 |
| `node_steady_state_temp_hot` | [E] | fluxes, absorptivity, emissivity | hot case 定常温度 |
| `node_steady_state_temp_cold` | [E] | fluxes (eclipse), ε | cold case 定常温度 |
| `transient_temp_profile` | [E] | thermal_capacity, fluxes(t) | 時系列温度 |
| `heater_power_required_w` | [S] | T_min_required, env_min | ヒータ電力 |
| `verify_component_temp_range` | [V] | T(t), comp.T_min/max | 全コンポ温度 ∈ 許容範囲 |
| `radiator_area_required` | [S] | Q_dissipate, T_max, ε | 放熱面積 |
| `mli_layer_estimate` | [S] | leak_rate, ΔT | MLI 層数 |
| `thermal_margin_per_node` | [V] | T_op, T_qual | qualification マージン |
| `eclipse_temperature_drop` | [E] | C_p, P_in, t_eclipse | 蝕中温度降下 |

## 5. aocs（姿勢制御）

| 解析 | 種別 | 入力 | 出力 |
|---|---|---|---|
| `disturbance_torque_srp` | [E] | area, c_p−c_g, sun_vec | 太陽放射圧トルク |
| `disturbance_torque_gravity_gradient` | [E] | inertia, orbit | 重力傾斜トルク |
| `disturbance_torque_aero` | [E] | area, Cd, density, c_p | 大気抵抗トルク |
| `disturbance_torque_magnetic` | [E] | residual_dipole, B_field | 磁気トルク |
| `total_disturbance_torque_envelope` | [B] | all above | 最大外乱トルク |
| `reaction_wheel_torque_sizing` | [S] | T_dist, agility_req | 必要 RW トルク |
| `reaction_wheel_momentum_sizing` | [S] | T_dist × secular_time | 必要 RW 角運動量 |
| `momentum_dump_period` | [B] | RW capacity, T_secular | アンローディング周期 |
| `magnetorquer_sizing` | [S] | T_dump_req, B_min | MTQ ダイポール |
| `slew_time_estimate` | [B] | inertia, RW_torque, angle | スリュー時間 |
| `pointing_budget_per_mode` | [V] | sensor_err, actuator_jitter | 指向誤差 < req |
| `pointing_stability_jitter` | [V] | RW imbalance, structural | jitter < req |
| `attitude_determination_accuracy` | [V] | sensor suite, geometry | 姿勢決定精度 |
| `eclipse_attitude_safe_mode` | [E] | sun_sensor outage | safe mode 維持 |

## 6. cdh（C&DH / オンボード計算機）

| 解析 | 種別 | 入力 | 出力 |
|---|---|---|---|
| `data_generation_rate_per_mode` | [B] | sensors, sampling | bps per mode |
| `daily_data_volume` | [B] | rate × duty | Mbit/day |
| `onboard_storage_sizing` | [S] | volume × buffer_days | 必要 mass memory |
| `storage_fill_at_max_outage` | [V] | gen − downlink, contact_gap | overflow しないか |
| `cpu_utilization_per_mode` | [V] | task_periods × ms_each | <80% margin |
| `bus_utilization` | [V] | telemetry traffic | bus 占有率 |
| `verify_command_response_latency` | [V] | task scheduling | latency < req |
| `software_memory_footprint` | [B] | flight SW components | RAM/ROM |
| `radiation_seu_rate_per_chip` | [E] | env, chip_xsec | SEU/day |
| `verify_fdir_coverage` | [V] | failure modes | FDIR カバレッジ |

## 7. communications（通信）★ **未実装サブシステム**

> craft では `cdh/` に含めるか、`comm/` として独立させるか要判断。
> JERG-2-400 系 / SMAD ch.13 / NASA SSRI KB Communications。

| 解析 | 種別 | 入力 | 出力 |
|---|---|---|---|
| `eirp_dbm` | [B] | Tx_power, antenna_gain, losses | EIRP |
| `free_space_path_loss` | [E] | freq, slant_range | FSPL [dB] |
| `gt_ratio_ground_station` | [B] | GS_antenna, GS_Tsys | G/T |
| `link_budget_uplink` | [V] | EIRP_GS, G/T_sat, BW, BER | C/N0, margin |
| `link_budget_downlink` | [V] | EIRP_sat, G/T_GS | C/N0, margin |
| `data_rate_supported` | [S] | C/N0, mod, FEC | 達成可能 bps |
| `daily_downlink_capacity` | [B] | rate × contact | Mbit/day |
| `verify_downlink_volume` | [V] | downlink_cap vs data_gen | 流せるか |
| `doppler_shift_max` | [E] | orbit, freq | 最大ドップラー |
| `antenna_pattern_coverage` | [E] | beam, attitude | 受信エリア |

## 8. structure（構造）★ **未実装サブシステム**

| 解析 | 種別 | 入力 | 出力 |
|---|---|---|---|
| `total_mass` | [B] | all components | 質量合計 |
| `mass_budget_per_subsystem` | [B] | components × subsys | 系別質量 |
| `mass_margin` | [V] | total, launcher_limit | マージン充足 |
| `center_of_mass` | [B] | components, positions | CoM |
| `moment_of_inertia_tensor` | [B] | components | I_xx, I_yy, I_zz, products |
| `quasi_static_load_check` | [V] | mass, launcher_QSL | σ < σ_yield |
| `first_mode_frequency` | [V] | FEM result | f1 > launcher_min |
| `random_vibration_response` | [V] | PSD, modal | RMS stress |
| `shock_response_envelope` | [V] | SRS, comp_rating | 衝撃耐性 |
| `coupled_loads_analysis` | [V] | CLA result | quals 充足 |
| `safety_factor_per_member` | [V] | σ, σ_allow, FoS | FoS ≥ 規定 |

## 9. propulsion（推進系）★ **未実装サブシステム**

| 解析 | 種別 | 入力 | 出力 |
|---|---|---|---|
| `propellant_mass_required` | [S] | ΔV, Isp, dry_mass | m_prop (rocket eq.) |
| `tank_volume_sizing` | [S] | m_prop, density, T | タンク容積 |
| `tank_wall_thickness` | [S] | P, R, σ_yield, FoS | タンク肉厚 |
| `tank_margin_of_safety` | [V] | hoop stress, allowable | MoS ≥ 0 |
| `burn_time_per_maneuver` | [B] | ΔV, thrust, mass | 燃焼時間 |
| `thrust_to_weight_orbit_avg` | [B] | thrust, mass | T/W |
| `gravity_loss` | [E] | burn_arc, low_thrust | ΔV ロス |
| `propellant_budget` | [B] | maneuvers + margin | 総推進剤 |
| `verify_isp_sufficient` | [V] | mission_ΔV, m_dry, m_prop_max | feasibility |
| `pressurant_sizing` | [S] | tank_V, blowdown_ratio | He/N2 量 |
| `ion_engine_power_at_distance` | [E] | sun_dist, panel_power | EP 出力（深宇宙）|
| `gimbal_misalignment_torque` | [E] | thrust, gimbal_angle, offset | スラスタ姿勢外乱 |

## 10. payload / mission instrument（ペイロード）

ミッション固有なので個別。**汎用例:**

| 解析 | 種別 | 入力 | 出力 |
|---|---|---|---|
| `field_of_view_coverage` | [E] | FoV, attitude, orbit | 観測領域 |
| `ground_sample_distance` | [B] | aperture, alt, λ | GSD [m] |
| `diffraction_limit_resolution` | [B] | aperture, λ | 回折限界角分解能 |
| `signal_to_noise_ratio` | [V] | source, optics, detector | SNR |
| `integration_time_required` | [S] | SNR_req, source | exposure |
| `pointing_jitter_impact_on_image` | [V] | jitter, exposure | smear ≤ pixel |
| `data_rate_per_observation` | [B] | resolution, framerate | bps |
| `sar_resolution_nesz` | [B] | bandwidth, antenna, PRF | range/azimuth res, NESZ |
| `optical_comm_photon_budget` | [V] | Tx_power, λ, aperture | photons/bit ≥ req |

## 11. environment / radiation（宇宙環境）★ **新規サブシステム想定**

> 軌道に依存するが、他系（電源/CDH/構造）で参照されるため独立 system に分けてもよい。

| 解析 | 種別 | 入力 | 出力 |
|---|---|---|---|
| `orbit_tid_per_year_gy` | [E] | orbit, shielding | TID [Gy/year] |
| `tid_margin_ok` | [V] | TID_orbit, TID_comp, RDF | TID マージン |
| `seu_rate_per_day` | [E] | xsec, flux, n_bits | SEU events/day |
| `displacement_damage_dose` | [E] | proton_fluence, NIEL | DDD |
| `solar_cell_radiation_degradation` | [E] | proton fluence, cell type | 残存効率 |
| `shielding_tid_reduction_factor` | [B] | Al_thickness | 低減率 |
| `mmod_impact_probability` | [E] | area, time, flux model | 衝突確率 |

## 12. reliability（信頼性・FDIR）★ **横断機能**

| 解析 | 種別 | 入力 | 出力 |
|---|---|---|---|
| `component_reliability` | [B] | λ, t | R(t) = e^(-λt) |
| `series_reliability` | [B] | R_i list | ΠR_i |
| `parallel_reliability` | [B] | R_i list | 1 - Π(1-R_i) |
| `k_of_n_reliability` | [B] | R, n, k | k/n 冗長系 |
| `mission_reliability_ok` | [V] | R_sys, R_min | 適合 |
| `mtbf_hours` | [B] | λ | MTBF |
| `verify_fdir_coverage` | [V] | failures, detectable | カバレッジ |

## 13. launch_environment（打ち上げ環境）★ **横断機能**

| 解析 | 種別 | 入力 | 出力 |
|---|---|---|---|
| `fairing_volume_fit` | [V] | sat_envelope, fairing | 体積適合 |
| `rail_dimension_check` | [V] | CubeSat dim, deployer | レール寸法 |
| `quasi_static_load_per_axis` | [V] | mass, launcher QSL, FoS | 応力許容 |
| `coupled_loads_analysis_summary` | [V] | CLA result | quals 充足 |
| `random_vibration_grms` | [V] | PSD, modal | RMS 応答 |
| `shock_response_envelope_ok` | [V] | SRS, comp_rating | 衝撃耐性 |

---

## 横断（系をまたぐ）解析

複数 system の Ref を組み合わせるもの。craft の `imports=[...]` 機能で実装。

| 解析 | 含む系 | 趣旨 |
|---|---|---|
| `mass_power_thermal_summary` | structure, power, thermal | PDR 用サマリ |
| `worst_case_hot_balance` | thermal, power, orbital | hot case 電力×熱整合 |
| `worst_case_cold_balance` | thermal, power, orbital | cold case （蝕＋低β）整合 |
| `safe_mode_survivability` | power, thermal, aocs | サブシステム最低運用で生存 |
| `eol_margin_summary` | power, propulsion, structure | EOL での全マージン |
| `launch_environment_compliance` | structure, comm, power | 打ち上げ規定充足 |

---

## ディレクトリ構成案（次のステップ）

現状 `systems/<sys>/analyses.py` 1 ファイル → `systems/<sys>/analyses/` ディレクトリへ。

### Option A（タグ単位）

```
systems/power/analyses/
├── __init__.py          # re-export（registry が拾うため）
├── budget.py            # *_budget_*, *_per_mode_w  系（[B]）
├── sizing.py            # *_sizing, *_required_* 系（[S]）
├── verify.py            # @analysis(verify=True) 系（[V]）
├── environment.py       # SAP 温度, 蝕応答 など（[E]）
└── adhoc.py             # system=None の便利関数（[A]）
```

メリット: `verify.py` 単体で「成立性チェックリスト」が見える。pytest 別実行も容易。

### Option B（テーマ/コンポ単位） **← ut-issl 流・推奨**

ut-issl/spacecraft-design-marimo の構成。「いま電源系のうちバッテリの解析を読みたい」直感に近い。

```
systems/power/analyses/
├── __init__.py          # re-export
├── solar.py             # SAP 発電量・EOL 補正
├── battery.py           # 容量サイジング・DoD・サイクル寿命
└── budget.py            # 電力収支・モード集計
```

```
systems/orbital/analyses/
├── mechanics.py         # period, velocity, SSO inclination
├── geometry.py          # slant range, pass duration, contact time
└── lifetime.py          # decay, 25-year rule
```

```
systems/aocs/analyses/
├── disturbances.py      # gravity gradient, aero, SRP, magnetic
├── actuators.py         # RW saturation, MTQ
└── attitude.py          # pointing budget, slew time
```

```
systems/thermal/analyses/
├── balance.py           # equilibrium temp, absorbed power
├── nodal.py             # node-based steady/transient（重い場合）
└── verify.py            # temp range check
```

```
systems/comm/analyses/      ★ 新サブシステム
├── link.py              # FSPL, EIRP, G/T, C/N0, margin
└── data.py              # data rate, downlink capacity
```

```
systems/cdh/analyses/
└── data.py              # storage sizing, throughput
```

```
systems/structure/analyses/  ★ 新サブシステム
└── loads.py             # natural freq, QSL, MoI, CoM
```

```
systems/propulsion/analyses/  ★ 新サブシステム
└── delta_v.py           # propellant mass, burn time, tank
```

```
systems/environment/analyses/ ★ 新サブシステム（or orbital に含める）
└── radiation.py         # TID, SEU, DDD, shielding
```

**推奨理由:**
- 既存のオープンソース実装（ut-issl）と整合 → 関数移植や参考実装の取り込みが容易
- ファイル名で「コンポ/物理現象」が一目で分かる
- `verify=True` 関数は同じファイル内に置けば足り、別ファイル化のメリットが薄い
- 横断系の収支（`power_budget`）は `budget.py` という汎用名に収まる

### `__init__.py` の registry 拾わせ方

craft の `@analysis` デコレータは `UnifiedRegistry` に `__init_subclass__` 的に登録される想定（既存 `analyses.py` がそのまま import される）。
ディレクトリ化後は `__init__.py` で全モジュールを import すれば現状の挙動を保てる:

```python
# systems/power/analyses/__init__.py
from . import solar, battery, budget  # noqa: F401  -- register @analysis decorators
```

`core.discovery.discover_systems` が `systems/<sys>/` の package を import する仕組みなら、`__init__.py` 内 import で十分。必要に応じ `discover_systems` 側でサブモジュール再帰スキャンを足す。

---

## 実装優先度（個人的推奨）

### Tier 1（PDR で必須・既存資産が活用できる）
1. **power**: solar_array_power_bol/eol_w, battery_capacity_required_wh, verify_energy_balance_per_orbit
2. **orbital**: eclipse_duration_s ★既存, ground_station_access, delta_v_budget_total
3. **mission**: mode_duty_cycle, mission_lifetime_orbits
4. **structure（新規）**: total_mass, mass_margin, moment_of_inertia_tensor

### Tier 2（CDR までに）
5. **thermal**: node_steady_state_temp_hot/cold, verify_component_temp_range, heater_power_required_w
6. **aocs**: disturbance_torque_*, reaction_wheel_*_sizing, pointing_budget_per_mode
7. **comm（新規）**: link_budget_uplink/downlink, daily_downlink_capacity

### Tier 3（詳細設計フェーズ）
8. **propulsion**: propellant_mass_required, propellant_budget
9. **cdh**: storage_fill_at_max_outage, cpu_utilization_per_mode
10. **横断**: worst_case_hot/cold_balance, safe_mode_survivability

---

## 参考資料

### JAXA 設計標準（JERG）
- [JERG-2-000B 宇宙機（人工衛星・探査機）設計標準](https://sma.jaxa.jp/TechDoc/Docs/JAXA-JERG-2-000B.pdf)
- [JERG-2-100 システム設計標準](https://sma.jaxa.jp/TechDoc/Docs/JAXA-JERG-2-100.pdf)
- [JERG-2-130D 宇宙機一般試験標準](https://sma.jaxa.jp/TechDoc/Docs/JAXA-JERG-2-130D.pdf)
- JERG-2-214 電源系設計標準
- JERG-2-215 太陽電池パドル系設計標準
- [JERG-2-200A 電気設計標準](https://sma.jaxa.jp/TechDoc/Docs/JAXA-JERG-2-200A_N1.pdf)
- JERG-2-400 系（通信）

### 書籍 / 教科書
- *Space Mission Analysis and Design* (SMAD) — Wertz, Larson
- *Spacecraft Systems Engineering* — Fortescue, Stark, Swinerd
- 衛星設計入門（東大中須賀研, NAS にあるとのこと）

### Web リファレンス
- [NASA SSRI Knowledge Base — Subsystem Design](https://s3vi.ndc.nasa.gov/ssri-kb/topics/31/)
- [A Guide to CubeSat Mission and Bus Design (Hawaii Pressbooks)](https://pressbooks-dev.oer.hawaii.edu/epet302/)
- [State of the Art of Small Spacecraft Technology (NASA)](https://sst-soa.arc.nasa.gov/04-propulsion)

### Drive 内資料
- 「電源系紹介ドキュメント」(M1 大井, 2026/3/30) — GEO-X 電源系の網羅的解説
- 「STEP衛星班_予備審査書.pdf」 — 筑波大 STEP プロジェクト

### GitHub 先行実装（最重要）
- [ut-issl/spacecraft-design-marimo](https://github.com/ut-issl/spacecraft-design-marimo/tree/refactor/component-first-3axis) — Craft と類似目的の Marimo notebook + Pydantic ベース設計ツール。
  - [`src/analysis/`](https://github.com/ut-issl/spacecraft-design-marimo/tree/refactor/component-first-3axis/src/analysis) — Pydantic 非依存・純関数の解析群（移植元として最有力）
  - [`docs/satellite-design/INITIAL_DESIGN_CALCULATIONS.md`](https://github.com/ut-issl/spacecraft-design-marimo/blob/refactor/component-first-3axis/docs/satellite-design/INITIAL_DESIGN_CALCULATIONS.md) — 14 章 100+ 計算を網羅
  - [`docs/satellite-design/SATELLITE_CORE_CALCULATIONS.md`](https://github.com/ut-issl/spacecraft-design-marimo/blob/refactor/component-first-3axis/docs/satellite-design/SATELLITE_CORE_CALCULATIONS.md) — 設計フレームワーク・成立性チェックリスト
  - [`docs/implementation/ANALYSIS_FUNCTIONS.md`](https://github.com/ut-issl/spacecraft-design-marimo/blob/refactor/component-first-3axis/docs/implementation/ANALYSIS_FUNCTIONS.md) — 関数シグネチャ一覧（API 設計の参考）

**取り込み戦略（推奨）:**
1. Craft の `@analysis` デコレータでラップする薄い層を `systems/<sys>/analyses/<theme>.py` に置く
2. 純計算は ut-issl の関数を **ライセンス確認の上で** 移植 or 参考にして再実装
3. veriq `Ref` を引数に取る wrapper と、純関数（ad-hoc）を併設して柔軟性を確保
