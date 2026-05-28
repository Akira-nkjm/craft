# mission（運用・ミッションプロファイル）

運用モード時系列・duty 比・ミッション周回数・成立性チェック。**他系の最悪条件を生成する基盤**。

---

## 1. `operation_mode_timeline` [B]

**用途:** 1 周回 / 1 日 / ミッション全体のモード遷移タイムライン。

**式:**（疑似コード）

```
timeline = []
for orbit in orbits:
    for segment in [sunlit, eclipse]:
        for mode in mode_configs:
            if mode.active_in(orbit, segment):
                timeline.append((t_start, t_end, mode))
```

**入力:** mode_configs, orbital.eclipse_duration_s, mission lifetime
**出力:** list[(t_start_s, t_end_s, mode_name)]

---

## 2. `mode_duty_cycle` [B]

**用途:** モード別の時間比率。電力収支・データ生成量の基盤。

**式:** $d_{mode} = t_{mode} / T_{orbit}$

**入力:** timeline
**出力:** dict[mode → duty [—]]
**備考:** 全モード合計が 1.0 になることを検証。

---

## 3. `mission_lifetime_orbits` [B]

**式:** $N_{orbits} = T_{mission,days} \cdot 86400 / T_{orbit,s}$

**入力:** ミッション期間, 軌道周期
**出力:** 周回数 [—] — バッテリサイクル寿命確認の入力。

---

## 4. `eclipse_to_sunlit_ratio_per_mode` [E]

**用途:** モード × 蝕の重ね合わせ。例:「ペイロード観測モードのうち何割が蝕中か」。

**式:** $r_{ecl,m} = t_{m,ecl} / t_{m,total}$

**入力:** timeline, 蝕タイムライン
**出力:** dict[mode → 蝕時間比率]

---

## 5. `mode_transition_graph` [B]

**用途:** モード間遷移の妥当性確認。

**入力:** mode_configs（許可される遷移）
**出力:** 有向グラフ — 孤立モード・到達不能モード検出

---

## 6. `verify_mode_exclusive` [V]

**式:** 排他制約 $\{m_i, m_j\}$ に対し $\forall t: \neg(\mathbb{1}[m_i] \wedge \mathbb{1}[m_j])$

**入力:** 排他リスト、timeline
**出力:** bool / 違反タイムスタンプ list

---

## 7. `mode_max_consecutive_duration_s` [B]

**用途:** モード連続稼働の上限が許容内か。

**入力:** timeline
**出力:** dict[mode → 最長連続時間]

---

## 8. `mission_success_criteria_coverage` [V]

**用途:** フル/エクストラサクセス基準の充足度。

**入力:** 各 success metric の達成しきい値 + 解析結果
**出力:** dict[criterion → bool]

---

## 9. `ground_contact_per_mode` [B]

**用途:** モード × 地上局可視の重ね合わせ。

**式:** orbital.daily_contact ∩ mode timeline

**入力:** timeline, contact windows
**出力:** dict[mode → contact_time_per_day]
**備考:** TT&C モードに必ず contact が含まれるかの検証も兼ねる。

---

## 10. `peak_concurrent_power_mode_w` [B]

**用途:** 最大消費電力モードの抽出（電源系最悪条件）。

**式:** $\max_m P_{mode}(m)$、`power.aggregate_mode_power_w` を全モードに適用。

**入力:** 全コンポネント、全モード
**出力:** (mode_name, $P_{max}$ [W])

---

## 依存関係

```
mode_configs ──┬── timeline ──┬── duty_cycle ── power.energy_balance
               │              ├── eclipse_to_sunlit_ratio ── thermal cases
               │              └── ground_contact_per_mode ── comm verify
               └── mode_transition_graph ── verify_mode_exclusive

orbital.eclipse + period ── mission_lifetime_orbits ── power.battery_cycle_count
```
