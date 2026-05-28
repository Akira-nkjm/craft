# reliability（信頼性・FDIR）

故障率モデル・直/並列冗長・k-of-n 冗長・MTBF。**横断機能**：各サブシステムの信頼性を集約。

---

## 1. `component_reliability` [B]

**用途:** 指数分布モデルでの単部品信頼性。

**式:**

$$R(t) = \exp(-\lambda t)$$

**入力:** 故障率 $\lambda$ [1/h], 経過時間 $t$ [h]
**出力:** $R(t)$ [—]

---

## 2. `mtbf_hours` [B]

**式:** $\mathrm{MTBF} = 1/\lambda$

**出力:** [h] — 指数分布での MTBF = 平均故障時間。

---

## 3. `series_reliability` [B]

**用途:** 直列系（どれか 1 つでも故障で全体故障）。

**式:**

$$R_{series} = \prod_i R_i$$

**入力:** $R_i$ list
**出力:** [—]

---

## 4. `parallel_reliability` [B]

**用途:** 完全冗長（全部故障で初めて系故障）。

**式:**

$$R_{parallel} = 1 - \prod_i (1 - R_i)$$

**出力:** [—]

---

## 5. `k_of_n_reliability` [B]

**用途:** $n$ 中 $k$ 以上が動作すれば成立（例: 4-of-3 reaction wheel）。

**式:**（同一 $R$ の場合、二項分布）

$$R_{k/n} = \sum_{j=k}^{n} \binom{n}{j} R^j (1-R)^{n-j}$$

**入力:** 単部品 $R$, $n$, $k$
**出力:** [—]

---

## 6. `mission_reliability_ok` [V]

**閾値:** ミッション要求（典型 0.85–0.95）。

**式:** $R_{mission} \geq R_{required}$

**出力:** bool

---

## 7. `mission_duration_for_reliability_h` [B]

**用途:** 目標信頼性を満たす最大ミッション時間。

**式:**（指数分布）

$$t_{max} = -\ln(R_{target}) / \lambda$$

**入力:** 目標信頼性、故障率
**出力:** [h]

---

## 8. `fdir_detection_coverage_pct` [V]

**用途:** FDIR が検出できる故障モードの割合。

**式:** $C_{det} = N_{detected} / N_{total\_failure\_modes} \cdot 100$

**入力:** FMECA テーブル、FDIR 監視リスト
**出力:** [%] — **閾値 ≥ 90%**（typical PDR）

---

## 9. `fdir_recovery_action_defined` [V]

**用途:** 検出された故障モードに対する recovery 行動が定義されているか。

**入力:** 故障モード list, recovery action list
**出力:** bool / 未定義モード list

---

## 10. `redundancy_strategy_summary` [B]

**用途:** 系毎の冗長構成サマリ。

**入力:** 全コンポネントの冗長種別（cold/warm/hot, n+1, 2-of-3 等）
**出力:** dict[subsys → strategy]

---

## 11. `single_point_failure_list` [V]

**用途:** SPF（Single Point of Failure）の列挙。

**入力:** システム FT（fault tree）または block diagram
**出力:** SPF コンポネント list — **0 件が PDR 目標**（例外は cube/PocketQube 級のみ）

---

## 12. `safe_mode_survivability_h` [V]

**用途:** セーフモード（最低運用）でどれくらい持つか。

**入力:** safe mode power load, 安全裕度バッテリ容量, ヒータ要求
**出力:** [h] — typical 要求 24–72 h

---

## 故障率の典型値（参考）

| 部品種別 | $\lambda$ [FIT (10⁻⁹/h)] |
|---|---|
| MIL-spec MCU | 50–200 |
| 民生 MCU（rad-tolerant 評価済）| 500–2000 |
| Reaction wheel | 100–1000 |
| Star tracker | 50–500 |
| バッテリ（cell 単位）| 10–100 |
| MLI | <1 |

---

## 依存関係

```
component λ ── R(t) ──┬── series ── subsys reliability ──┐
                      ├── parallel ── redundant block     ├── mission_reliability_ok
                      └── k-of-n ── partial redundancy ───┘

FMECA ── fdir_detection_coverage ── verify
       └── fdir_recovery ── verify
       └── single_point_failure_list
```
