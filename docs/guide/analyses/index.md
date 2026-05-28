# 解析リファレンス

`systems/<sys>/analyses/` に実装する解析関数の**詳細リファレンス**。サブシステム毎に 1 ページ。

各ページの構成は統一：

- **関数名** — Craft 実装名（snake_case）
- **タグ** — `[B][S][V][T][E][A]`（[カタログの凡例](../satellite-analyses-catalog.md#凡例解析タグ)参照）
- **用途** — 何のために計算するか
- **計算式** — 数式（LaTeX）
- **入力** — 表形式（記号・説明・単位）
- **出力** — 戻り値の意味・単位
- **備考** — 仮定・最悪条件・参考

## 一覧

| ページ | 主な解析 |
|---|---|
| [orbital](orbital.md) | 周期・速度、日食、SSO、地上局可視、軌道寿命、Δv |
| [power](power.md) | 太陽電池発電、バッテリ容量、モード集計、電力収支、EOL 補正 |
| [aocs](aocs.md) | 外乱トルク（4 種）、RW/MTQ サイジング、指向誤差、スリュー時間 |
| [thermal](thermal.md) | 熱収支、定常温度、ヒータ電力、許容温度確認 |
| [comm](comm.md) | FSPL、EIRP、G/T、リンクマージン、データレート、ITU 大気減衰 |
| [structure](structure.md) | 質量・CoM・MoI、固有振動数、準静的応力、フェアリング |
| [propulsion](propulsion.md) | Tsiolkovsky、燃焼時間、タンク体積・肉厚 |
| [cdh](cdh.md) | 必要 Flash 容量、書換寿命、データスループット |
| [mission](mission.md) | モード時系列、duty 比、ミッション周回数 |
| [environment](environment.md) | TID、SEE、変位損傷、シールド低減 |
| [reliability](reliability.md) | 直/並列、k/n、MTBF、ミッション信頼性 |
| [launch_env](launch_env.md) | フェアリング、ランダム振動、衝撃、CLA |

## 凡例（再掲）

| タグ | 意味 |
|------|------|
| **[B]** | 予算（合算とマージン確認） |
| **[S]** | サイジング（寸法・容量決定） |
| **[V]** | 検証（`@analysis(verify=True)`） |
| **[T]** | トレード（設計選択肢比較） |
| **[E]** | 環境応答（軌道/熱/放射線外乱） |
| **[A]** | ad-hoc（`system=None`） |

## 数式表記の規約

- 単位は SI を基本（ただし慣用に従い高度は km、周期は min など混在）
- 地球関係: $R_\oplus = 6371$ km、$\mu = 3.986 \times 10^{14}$ m³/s²、$J_2 = 1.082 \times 10^{-3}$
- 太陽: $G_{sun} = 1361$ W/m²、$g_0 = 9.80665$ m/s²
- 真空誘電率や Boltzmann 定数等は各ページで明示
