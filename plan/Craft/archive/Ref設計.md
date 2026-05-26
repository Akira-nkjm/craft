---
project: "Craft"
tags: [project, dev, satellite, architecture, ref]
date_updated: 2026-05-22
---

# Ref 設計 — `@analysis` における component 参照

> ⚠️ **archive**: 確定事項は [[Analysis詳細仕様]] §13「引数参照 — vq.Ref 流儀」に統合済み。
> 本ノートは案A/B/C の比較、代替案の検討経緯、未確認事項の詳細記録として残置。

> 関連: [[Analysis詳細仕様]] / [[veriq仕様メモ]] / [[API設計]]

`@analysis` が component インスタンスを入力に取る記法を決める。
**結論: veriq の `vq.Ref` 流儀をそのまま継承**。新しい DSL を発明しない。

---

## 1. 設計原則

1. **veriq に揃える** — `@analysis(verify=True)` で veriq calculation に流れる以上、記法を別物にすると認知コスト 2 倍
2. **Python annotation と API ペイロードを 1:1 対応** — `Annotated[T, Ref(...)]` と `{"$ref": ..., "subsystem": ...}` が同じ意味
3. **DSL を発明しない** — フィルタ・集計は **Python 関数本体** で書く（型の力で読みやすい）

---

## 2. veriq `vq.Ref` の実コード調査結果

ユーザリポジトリ `design/scopes/` から抽出した実用パターン:

### 2.1 同一 scope のフィールド参照
```python
loss_atmosphere: Annotated[float, vq.Ref("$.stations.domestic_main.uplink.loss_atmosphere_db")]
```

### 2.2 クロス scope のフィールド参照
```python
altitude_km: Annotated[float, vq.Ref("$.orbit.altitude_km", scope="orbital")]
```

### 2.3 他 scope の計算結果参照
```python
slant_range_km: Annotated[float, vq.Ref("@calc_slant_range_km", scope="orbital")]
```
`@` prefix で **計算ノード名** を指す。

### 2.4 Table 全体の参照（**横断集計の鍵**）
```python
heaters: Annotated[vq.Table[HeaterName, HeaterEntry], vq.Ref("$.heaters")]
panels:  Annotated[vq.Table[PanelName, PanelEntry], vq.Ref("$.panels", scope="structure")]
```
**全 instance を辞書ライクに受け取れる** → power_mode 横断検索などはここで完結。

---

## 3. 採用方針

### 3.1 `Ref` クラス（veriq のものをそのまま使う）

```python
import veriq as vq
from typing import Annotated

@analysis(subsystem="power")
def power_budget_by_mode(
    # 単一インスタンスのフィールド
    eps_efficiency: Annotated[float, vq.Ref("$.eps.efficiency")],

    # 全 battery 受け取り（集計に使う）
    batteries: Annotated[vq.Table[BatteriesName, BatteryEntry], vq.Ref("$.batteries")],

    # クロスサブシステム参照
    altitude: Annotated[float, vq.Ref("$.orbit.altitude_km", scope="orbital")],

    # 他サブシステムの計算結果
    eclipse_time: Annotated[float, vq.Ref("@calc_eclipse_duration_s", scope="orbital")],

    # 解析パラメータ（ref ではなく直接受け取る）
    mode: OperationMode,
) -> PowerBudget:
    total = sum(b.spec.capacity_wh * eps_efficiency for b in batteries.values())
    ...
```

→ veriq の `Ref` をそのまま使う。**独自 `Ref` クラスは作らない**。

### 3.2 `subsystem` vs `scope` の用語

veriq は `scope=`、本プロジェクトのドメイン用語は `subsystem`。
**veriq の `scope=` をそのまま使う**（noise less than aliasing）。
本プロジェクトの「subsystem」は **scope と等価** と用語集に明記。

---

## 4. API ペイロードでの表現

HTTP 経由で `@analysis` を呼ぶときの JSON body は **Annotation と対称**:

### 4.1 単一フィールド参照
```json
{
  "eps_efficiency": { "$ref": "$.eps.efficiency" },
  "altitude": { "$ref": "$.orbit.altitude_km", "scope": "orbital" }
}
```

### 4.2 計算結果参照
```json
{
  "eclipse_time": { "$ref": "@calc_eclipse_duration_s", "scope": "orbital" }
}
```

### 4.3 Table 全体
```json
{
  "batteries": { "$ref": "$.batteries" }
}
```

### 4.4 直値（参照ではなく定数）
```json
{
  "mode": "safe",
  "eps_efficiency": 0.85
}
```

直値はそのまま、参照は `{"$ref": ...}` envelope。Pydantic の discriminator で識別。

### 4.5 ショートハンド（議論余地）

将来 CLI などで楽したくなったら:
```
"$.eps.efficiency"            # 文字列で渡せば自動的に $ref と解釈
"@orbital:calc_eclipse_..."   # scope を文字列に埋める
```
→ **採らない**。あいまいさが増えてエラー報告が複雑化。**JSON は冗長でも明示的に**。

---

## 5. 横断集計の書き方（DSL を発明しない）

ユーザが当初言及した「power_mode で全コンポーネント横断検索」のような要件:

### 5.1 集計 (例: mode 別合計)

```python
@analysis(subsystem="power")
def total_power_by_mode(
    batteries: Annotated[vq.Table[BatteriesName, BatteryEntry], vq.Ref("$.batteries")],
    pdms: Annotated[vq.Table[PDMName, PDMEntry], vq.Ref("$.pdms")],
    mode: OperationMode,
) -> float:
    """OperationMode 別の消費電力合計を算出。"""
    total = 0.0
    for b in batteries.values():
        total += b.design.power_modes.get(mode, 0)
    for p in pdms.values():
        total += p.design.power_modes.get(mode, 0)
    return total
```

→ **Python の素直なループ**。`@query` のような特別な仕組みは不要。

### 5.2 「特定 mode で動く全コンポーネント」を列挙

これは「メタデータ照会」なので **`@analysis` ではなく built-in introspection endpoint**（`@query` は廃止、[[最終構成]] §10 / [[API設計]] §Cross-component Query）:

```
GET /api/introspect/components-with-value?path=design.power_modes.safe&exists=true
```

設計者がコードを書かなくても、registry から自動で答えられる。

---

## 6. 「参照のない `@analysis`」のための register-time 解決

`@analysis(scope=None)` のアドホックモード（[[最終構成]] §2 方針 C）では、 veriq が動かない。
このとき `Ref` をどう解決するか:

### 6.1 案 A: アドホック用の Ref も同じクラス
- 関数呼び出し前に **本プロジェクト独自のリゾルバ** が `Ref` をたどって TOML から値を取得
- 利点: コードが完全に同じ書き方になる
- 欠点: リゾルバを veriq と本体で 2 つ持つ重複

### 6.2 案 B: アドホックは Ref を許さず、引数は直値のみ
- `@analysis(scope=None)` は API/CLI から直値だけ受け取る（or 呼び出し側が事前解決）
- 利点: 実装単純
- 欠点: アドホック解析の使い勝手低下

### 6.3 ✅ 推奨: 案 A、ただしリゾルバを薄く実装

`Ref(path).resolve(toml_data)` の薄いユーティリティを `core/ref_resolver.py` に置く:

```python
def resolve_ref(ref: vq.Ref, data_root: Path) -> Any:
    """veriq を起動せずに Ref を解決。
    - "$.foo.bar"            → TOML から path 取得
    - "@calcname"            → 前回の calc 結果から取得（runs/latest/...）
    """
    ...
```

→ veriq と等価な記法を維持しつつ、軽量。

---

## 7. 「複数 instance への単一指定」をどう書くか

例: 「batteries.main と batteries.aux **だけ** を入力にしたい」

### 案 A: JSONPath のサブセット指定
```python
Annotated[vq.Table[..., ...], vq.Ref("$.batteries[main,aux]")]
```
→ veriq が対応していなければ自作 DSL。**避けたい**。

### 案 B: 全部受け取って関数内でフィルタ
```python
batteries: Annotated[vq.Table[...], vq.Ref("$.batteries")],
...
selected = {k: batteries[k] for k in ("main", "aux")}
```
→ **シンプル、可読、型 OK**。✅ こちらを推奨。

### 案 C: 解析メタデータで宣言
```python
@analysis(
    subsystem="power",
    inputs={"batteries": vq.Ref("$.batteries"), "selection": ["main", "aux"]},
)
```
→ overkill、API も複雑化。❌

---

## 8. 確定事項（このノートの結論）

| 項目 | 決定 |
|---|---|
| `Ref` クラス | **veriq の `vq.Ref` をそのまま使う** |
| キーワード名 | **`scope=`**（veriq に揃える）。`subsystem` は概念用語 |
| Table 参照 | **`vq.Table[Name, Entry]` + `vq.Ref("$.tablename")`** で全インスタンス受領 |
| 計算結果参照 | **`@calcname`** prefix |
| API ペイロード | **`{"$ref": "...", "scope": "..."}`** envelope |
| 直値 | **そのまま JSON 値** |
| ショートハンド文字列 | **採らない**（明示優先） |
| 部分選択 (主に部分集合) | **Table 全部受領 + 関数内フィルタ** |
| 横断集計 | **`@analysis` で素直に書く**、DSL なし |
| メタデータ照会 | **built-in introspection endpoints**（`@query` decorator は廃止） |
| アドホックモード | **薄いリゾルバ `core/ref_resolver.py` を実装** |

---

## 9. [[最終構成]] への反映

- §10 ❓4「`$ref` 記法」 → ✅ veriq 流儀採用で解決
- §2 の decorator 一覧から `@query` を削除、`@component` / `@analysis` の 2 種類に
- §5.2 `@analysis` のシグネチャ例を本ノートの 3.1 で置き換え

---

## 10. 未確認事項

- veriq の `vq.Ref` が `@calcname` をクロス scope で参照する時のエラー挙動
- `vq.Table` の dict ライク API の確定形 (`.values()` / `.items()` / `[key]` がそれぞれ動くか)
- 循環参照の検出（A→B, B→A）

→ 実装着手時に確認、本ノートに追記。
