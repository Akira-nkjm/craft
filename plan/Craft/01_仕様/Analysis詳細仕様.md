---
project: "Craft"
tags: [project, dev, satellite, architecture, analysis]
date_updated: 2026-05-22
---

# `@analysis` 詳細仕様

> 親: [[最終構成]] / 関連: [[UnifiedRegistry設計]] / [[veriq仕様メモ]] / [[API設計]]
> 引数参照（`vq.Ref` 流儀）は §13 を参照。

**唯一の decorator**（Component / Config は base class 方式）。本ノートで実装可能レベルまで具体化する。

---

## 1. 何を表す decorator か

**「component / 過去計算結果 を入力に取り、値を返す純粋関数」** を登録する。

- 入力: `vq.Ref` で TOML 経由の component / 計算結果、または直接受け取る scalar
- 出力: 任意の型（プリミティブ / Pydantic model / `vq.Table`）
- 純粋関数（副作用なし、決定性あり）が前提

veriq の `@scope.calculation()` / `@scope.verification()` の **薄いラッパとして機能** し、registry にも登録。

---

## 2. 完全シグネチャ

```python
def analysis(
    *,
    subsystem: str | None = None,   # None = ファイルパスから自動推論（default）
    name: str | None = None,
    desc: str | None = None,
    tags: Iterable[str] = (),

    # veriq 連携
    verify: bool = False,
    imports: Iterable[str] = (),

    # 実行制御
    cache: bool = True,
    code_version: str | None = None,
    async_only: bool = False,
    timeout_s: float | None = None,
) -> Callable[[Callable[P, T]], AnalysisFunction[T, P]]: ...
```

### 2.1 引数詳細

| 引数 | 型 | 説明 |
|---|---|---|
| `subsystem` | `str \| None` | 通常は **省略**（`subsystems/<name>/analyses.py` のパスから自動推論）。`str` 明示も可。`None` 明示 + `subsystems/` 外配置 = ad-hoc（veriq 非登録） |
| `name` | `str \| None` | 登録名。`None` なら `func.__name__` |
| `desc` | `str \| None` | 短い説明。`None` なら docstring 1 行目 |
| `tags` | `Iterable[str]` | 検索・分類用 |
| `verify` | `bool` | True なら veriq の `@scope.verification()`、False なら `@scope.calculation()`。`subsystem=None` の時は無視 |
| `imports` | `Iterable[str]` | veriq cross-scope imports（例: `["orbital", "thermal"]`）。`subsystem` 必須 |
| `cache` | `bool` | 結果を `generated/runs/analyses/{name}/{key}.toml` にキャッシュ（[[データパイプライン]] §2） |
| `code_version` | `str \| None` | キャッシュキー用バージョン。`None` なら関数 source の sha256 から自動算出 |
| `async_only` | `bool` | True なら同期 API でも常に job 化して返す |
| `timeout_s` | `float \| None` | 実行制限時間。超えたら `AnalysisTimeout` |

### 2.2 戻り値型

```python
@dataclass(frozen=True)
class AnalysisFunction[T, **P]:
    definition: AnalysisDefinition
    __call__: Callable[P, T]    # そのまま呼び出せる
```

→ decorator 適用後の `battery_eol_capacity` は普通の関数として呼べる。
→ `battery_eol_capacity.definition` で AnalysisDefinition にアクセス可能。

---

## 3. 関数シグネチャの規約

### 3.1 引数

3 種類:

```python
@analysis(subsystem="power")
def my_analysis(
    # (1) Ref 経由: TOML / 過去計算から値を取得
    spec: Annotated[BatterySpec, vq.Ref("$.batteries.main.spec")],
    altitude: Annotated[float, vq.Ref("$.orbit.altitude_km", scope="orbital")],
    eclipse: Annotated[float, vq.Ref("@calc_eclipse_s", scope="orbital")],

    # (2) Table 経由: 全インスタンス受領
    batteries: Annotated[vq.Table[BatteriesName, BatteryEntry], vq.Ref("$.batteries")],

    # (3) 直接パラメータ: API/CLI から渡される
    mode: OperationMode,
    safety_margin: float = 0.1,
) -> PowerBudgetResult: ...
```

### 3.2 戻り値型

| OK | 例 |
|---|---|
| プリミティブ | `float`, `int`, `bool`, `str` |
| Pydantic model | `class PowerBudgetResult(BaseModel): ...` |
| `vq.Table` | mode 別の結果など複数 key の場合 |
| `verify=True` の時 | `bool` または `vq.Table[K, bool]` 必須 |

❌ NG: `dict`, `tuple`, `dataclass` （JSON Schema 化できないと API 露出に困る）

### 3.3 引数推論ロジック

decorator 適用時に `inspect.signature()` で関数を検査:

```
for each param:
  if Annotated 内に vq.Ref → 「Ref 引数」として扱う
  else → 「直接 input 引数」として input_model に追加
```

**input_model** は直接 input 引数だけからなる動的 Pydantic model を生成（API ペイロード用）。

```python
class _MyAnalysisInputs(BaseModel):
    mode: OperationMode
    safety_margin: float = 0.1
```

→ API は `POST /api/analyses/power/my_analysis` のボディとして **`_MyAnalysisInputs`** + Ref 引数の `$ref` envelope を期待。

---

## 4. キャッシュキー計算

```python
key = sha256(
    name +
    code_version +                     # 関数 source 由来
    canonicalize_json(direct_inputs) + # 直接 input 引数の正規化 JSON
    refs_resolved_hash                 # Ref 経由データの内容ハッシュ
).hexdigest()
```

保存場所: `generated/runs/analyses/{name}/{key}.toml`

### 4.1 cache invalidation

| 変化 | 結果 |
|---|---|
| 関数本体を変更 | `code_version` 変化 → 自動失効 |
| 入力 component の TOML を変更 | `refs_resolved_hash` 変化 → 自動失効 |
| `mode` 引数を変えた | `direct_inputs` 変化 → 別キャッシュ |

### 4.2 cache=False のケース

- ランダム性を含む解析（モンテカルロ等）
- 外部リソース参照
- 時刻依存

---

## 5. veriq bridge 実装

decorator は **解決された subsystem の値で 3 分岐**（`subsystem` 省略時はファイルパスから推論済み）:

### 5.1 subsystem 解決不能（ad-hoc、`subsystems/` 外）
```python
defn = AnalysisDefinition(name, subsystem=None, ...)
default_registry.register_analysis(defn)
# veriq には何もしない
```

### 5.2 `subsystem="power", verify=False`（veriq calculation）
```python
# 内部で
power_scope.calculation(name=name, imports=imports)(func)
# + registry にも登録
default_registry.register_analysis(defn)
```

### 5.3 `subsystem="power", verify=True`（veriq verification）
```python
power_scope.verification(name=name, imports=imports)(func)
default_registry.register_analysis(AnalysisDefinition(..., verify=True))
```

### 5.4 scope オブジェクトの解決

```python
# subsystem 名から Scope オブジェクトを取り出す
from craft.verification.project import get_scope
scope = get_scope("power")   # → veriq.Scope インスタンス
```

`verification/project.py` に scope を登録する register と get があり、`@analysis` がそれを参照。

---

## 6. 実行経路

`@analysis` で登録された関数は **3 つの経路** から呼ばれる。

### 6.1 Python 直接呼び出し
```python
result = battery_eol_capacity(spec=BatterySpec(...), years=5)
```
→ 普通の関数。decorator 透過。

### 6.2 veriq 経由
```python
# veriq evaluate_project が内部で呼ぶ
# Ref が自動解決され、依存グラフ上の他ノードと連動
```

### 6.3 API / CLI 経由
```
POST /api/analyses/power/battery_eol_capacity
Body: {
  "spec": { "$ref": "$.batteries.main.spec" },
  "years": 5
}
  ↓
runner.resolve_refs(body, current_toml_data)
  ↓ Ref を実値に変換
runner.invoke(definition, kwargs)
  ↓
if cache hit: return cached
else: execute, cache, return
```

### 6.4 runner の責務

`analyses/_runner.py`:
```python
class AnalysisRunner:
    def invoke(self, defn: AnalysisDefinition, **kwargs) -> Any:
        """API/CLI から呼ばれる。Ref 解決済みの kwargs を受け取る"""

    def invoke_async(self, defn: AnalysisDefinition, **kwargs) -> JobId:
        """非同期 job として登録"""

    def resolve_refs(self, body: dict, toml_data: dict) -> dict:
        """{"$ref": ...} を実値に変換"""
```

---

## 7. エラー処理

### 7.1 設計時エラー（decorator 適用時）

| エラー | 原因 |
|---|---|
| `InvalidSignature` | Annotated に複数 Ref、戻り値型が無い、verify=True で戻り値が bool でない |
| `SubsystemNotFound` | `subsystem="xxx"` だが verification/project.py に scope 無し |
| `DuplicateRegistration` | 同名 analysis が既存 |

→ decorator 適用 = import 時に raise。起動時に発覚するので安全。

### 7.2 実行時エラー

| エラー | 原因 |
|---|---|
| `RefResolutionError` | $ref の path が TOML に存在しない |
| `AnalysisTimeout` | timeout_s 超過 |
| `AnalysisFunctionError` | 関数内部の例外をラップ |

API ではこれらが [[共通エラーレスポンス仕様]] に従って JSON 化される。

---

## 8. 例

### 8.1 ad-hoc 解析（veriq 非連携）
```python
@analysis(
    desc="2 つの面の熱結合係数を計算（暫定）",
    cache=False,
)
def thermal_coupling_estimate(
    a: PanelSurface,
    b: PanelSurface,
    distance_m: float,
) -> float:
    return 0.5 * a.emissivity * b.emissivity / distance_m ** 2
```

### 8.2 veriq calculation
```python
@analysis(
    subsystem="power",
    desc="OperationMode 別の総消費電力",
    imports=["orbital"],
)
def total_power_by_mode(
    batteries: Annotated[vq.Table[BatteriesName, BatteryEntry], vq.Ref("$.batteries")],
    pdms: Annotated[vq.Table[PDMName, PDMEntry], vq.Ref("$.pdms")],
    eclipse_s: Annotated[float, vq.Ref("@calc_eclipse_duration_s", scope="orbital")],
    mode: OperationMode,
) -> float:
    total = 0.0
    for b in batteries.values():
        total += b.design.power_modes.get(mode, 0)
    for p in pdms.values():
        total += p.design.power_modes.get(mode, 0)
    return total
```

### 8.3 veriq verification
```python
@analysis(
    subsystem="power",
    verify=True,
    desc="バッテリー容量が要求 DoD を満たすか",
)
def verify_battery_capacity(
    batteries: Annotated[vq.Table[BatteriesName, BatteryEntry], vq.Ref("$.batteries")],
    eclipse_energy_wh: Annotated[float, vq.Ref("@calc_eclipse_energy_wh")],
) -> vq.Table[BatteriesName, bool]:
    return vq.Table({
        name: b.spec.capacity_wh * b.requirements.depth_of_discharge_max >= eclipse_energy_wh
        for name, b in batteries.items()
    })
```

---

## 9. テスタビリティ

```python
def test_total_power_by_mode():
    # 直接呼び出しでテスト
    batteries = vq.Table({"main": BatteryEntry(...)})
    result = total_power_by_mode(
        batteries=batteries,
        pdms=vq.Table({}),
        eclipse_s=3600,
        mode=OperationMode.SAFE,
    )
    assert result == pytest.approx(50.0)
```

→ `@analysis` decorator は呼び出し可能性を維持。テストは普通の関数として扱える。

---

## 10. 実装サイズ感

- `analyses/_decorator.py` — 200 行
- `analyses/_definition.py`（AnalysisDefinition）— 50 行
- `analyses/_runner.py` — 300 行
- `analyses/_cache.py` — 100 行
- `analyses/_ref_resolver.py` — 150 行（veriq 非連携モード用）

合計 ~800 行。

---

## 11. 確定事項

| 項目 | 決定 |
|---|---|
| シグネチャ | §2 のとおり |
| 引数 3 種 | Ref / Table / 直接パラメータ |
| 戻り値 | プリミティブ / Pydantic / vq.Table（verify は bool 限定） |
| キャッシュキー | `name + code_version + inputs_hash + refs_hash` |
| veriq bridge | `subsystem` の値で 3 分岐、verify=True が verification |
| 実行経路 | Python 直接 / veriq 経由 / API runner の 3 つ |
| エラー設計 | decorator 時と実行時を区別、専用例外 |
| テスト | 直接呼び出し可能性を維持 |

---

## 12. 残る論点

- **`@analysis` で複数戻り値（tuple unpack）** をサポートするか → ❌ Pydantic model にラップさせる
- **進捗報告** (`progress: ProgressReporter` 引数注入) → 長時間解析で必要。Phase 2 検討
- **依存解析の自動可視化** — `@analysis` の依存グラフを registry から生成して MCP で見せる
- **既存 calculations との混在** — design/scopes/ 内の旧 calculation 関数を `@analysis` に段階移行する手順

---

## 13. 引数参照 — `vq.Ref` 流儀（旧「Ref設計」要約）

> 詳細な比較・代替案・経緯は archive [[Ref設計]] を参照。本節は確定事項の要約。

### 13.1 結論

**veriq の `vq.Ref` をそのまま使う**。新しい DSL は発明しない（[[最終構成]] §10-4）。

```python
@analysis
def total_power_by_mode(
    # (a) 単一インスタンスの spec を直接引く
    spec: Annotated[BatterySpec, vq.Ref("$.batteries.main.spec")],

    # (b) 別 scope（subsystem）の値を引く
    altitude: Annotated[float, vq.Ref("$.orbit.altitude_km", scope="orbital")],

    # (c) 別 scope の計算結果を引く（@calcname 記法）
    eclipse: Annotated[float, vq.Ref("@calc_eclipse_s", scope="orbital")],

    # (d) Table 受領（全インスタンス）
    batteries: Annotated[vq.Table[BatteriesName, BatteryEntry], vq.Ref("$.batteries")],

    # (e) 直接パラメータ（API / CLI から渡る）
    mode: OperationMode,
) -> float: ...
```

### 13.2 記法表（確定）

| 記法 | 意味 | scope 引数 |
|---|---|---|
| `vq.Ref("$.batteries")` | 自 scope の TOML パス | 省略可（= 自 scope） |
| `vq.Ref("$.orbit.altitude_km", scope="orbital")` | 他 scope の TOML パス | 必須 |
| `vq.Ref("@calc_name")` | 自 scope の前回計算結果 | 省略可 |
| `vq.Ref("@calc_name", scope="thermal")` | 他 scope の計算結果 | 必須 |
| `vq.Table[Name, Entry]` + `vq.Ref("$.tablename")` | テーブル全体を dict-like で受領 | パス指定通り |

### 13.3 部分選択は関数内フィルタ

`batteries.main` と `batteries.aux` だけ欲しい時は、**Table 全部受領 + 関数内で辞書フィルタ**。新 DSL は作らない（archive [[Ref設計]] §7）。

```python
selected = {k: batteries[k] for k in ("main", "aux")}
```

### 13.4 横断集計 / メタデータ照会

- **横断集計**（例: 全 OperationMode 列挙、消費電力合計）→ `@analysis` の素直なループで実装。`@query` は廃止（[[最終構成]] §10 / [[API設計]] §Cross-component Query）
- **メタデータ照会**（例: フィールドを持つ全 component 列挙）→ built-in introspection endpoint（`GET /api/projects/{pid}/registry/...`、[[API設計]]）

### 13.5 アドホックモード（veriq 非起動）の Ref 解決

`subsystem=None` で veriq を起動しない場合も同じ記法を維持。`core/ref_resolver.py` の薄いリゾルバが TOML / 前回計算結果から `vq.Ref` を解決:

```python
def resolve_ref(ref: vq.Ref, data_root: Path) -> Any:
    # "$.foo.bar"  → TOML から path 取得
    # "@calcname"  → generated/runs/latest/ から取得
    ...
```

### 13.6 API ペイロード envelope

API/CLI から `Ref` を渡す場合の JSON 形:

```json
{"$ref": "$.batteries.main.spec"}
{"$ref": "@calc_name", "scope": "orbital"}
```

直値はそのまま JSON 値で渡す（ショートハンド文字列形式は採らない、明示優先）。

### 13.7 未確認事項

- veriq の `vq.Ref` が `@calcname` をクロス scope で参照する時のエラー挙動
- `vq.Table` の dict ライク API の確定形 (`.values()` / `.items()` / `[key]` がそれぞれ動くか)
- 循環参照 (A→B, B→A) の検出

→ 実装着手時に確認、本ノートに追記。
