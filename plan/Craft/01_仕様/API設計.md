---
project: "Craft"
tags: [project, dev, satellite, api]
date_updated: 2026-05-22
---

# API 設計 — API ファースト土台

> 親: [[最終構成]] / 関連: [[UnifiedRegistry設計]] / [[Analysis詳細仕様]] / [[veriq仕様メモ]] / [[対処方針]]

主目的は **「API + CLI で全機能が叩ける状態」を作ること**。
Web UI は API が安定した後（Phase 2+）に検討。Swagger UI / OpenAPI を当面の対話 UI とする。

---

## 設計原則

1. **RESTful**: リソース指向、HTTP 動詞、ステータスコードを忠実に
2. **OpenAPI が一次仕様**: FastAPI の自動生成 schema を CI で版数管理
3. **path に `/projects/{project_id}` の場所を確保**（Phase 1 では `default` 固定でも、構造は入れる）
4. **CLI と API は機能等価**: `craft cli <verb>` が `curl <endpoint>` と 1:1 対応
5. **ETag / If-Match による楽観的ロック**（[[対処方針]] §C.1）
6. **エラーは Pydantic ValidationError をフィールド単位で返す**（RFC 7807 problem details に近い形）

---

## エンドポイント全体像

### Schema（型情報配信）

| Method | Path | 説明 |
|---|---|---|
| GET | `/api/projects/{pid}/schema/systems` | サブシステム一覧 |
| GET | `/api/projects/{pid}/schema/{system}` | サブシステム配下の component 型一覧 |
| GET | `/api/projects/{pid}/schema/{system}/{component}` | 単一 component の JSON Schema (`<Name>Entry`) |
| GET | `/api/projects/{pid}/schema/openapi.json` | OpenAPI ドキュメント |

### Instances（CRUD）

| Method | Path | 説明 |
|---|---|---|
| GET | `/api/projects/{pid}/components/{system}` | サブシステム全インスタンス一覧（plural ごとにグルーピング） |
| GET | `/api/projects/{pid}/components/{system}/{component}` | 単一 component の全インスタンス一覧 |
| GET | `/api/projects/{pid}/components/{system}/{component}/{instance}` | 単一インスタンス取得（ETag 付き） |
| POST | `/api/projects/{pid}/components/{system}/{component}/{instance}` | 新規作成（既存なら 409） |
| PUT | `/api/projects/{pid}/components/{system}/{component}/{instance}` | 全置換（If-Match 必須） |
| PATCH | `/api/projects/{pid}/components/{system}/{component}/{instance}` | 部分更新（If-Match 必須） |
| DELETE | `/api/projects/{pid}/components/{system}/{component}/{instance}` | 削除（If-Match 必須） |

### Verification（検証実行・結果）

| Method | Path | 説明 |
|---|---|---|
| POST | `/api/projects/{pid}/verify/{system}` | サブシステム検証を実行（非同期 job） |
| POST | `/api/projects/{pid}/verify` | 全サブシステム検証 |
| GET | `/api/projects/{pid}/runs` | 過去の検証 run 一覧 |
| GET | `/api/projects/{pid}/runs/{run_id}` | 検証結果詳細 |
| GET | `/api/projects/{pid}/runs/latest` | 最新の検証結果 |

### Diff / History

| Method | Path | 説明 |
|---|---|---|
| GET | `/api/projects/{pid}/history?path=power.toml&limit=20` | 変更履歴（git log 由来） |
| GET | `/api/projects/{pid}/diff?from={sha}&to={sha}` | 任意の2点間 diff |

### Meta

| Method | Path | 説明 |
|---|---|---|
| GET | `/api/projects` | プロジェクト一覧（Phase 1 は `[default]` のみ） |
| GET | `/api/healthz` | ヘルスチェック |
| GET | `/api/version` | スキーマバージョン + アプリバージョン |

---

## リクエスト/レスポンス例

### GET instance
```http
GET /api/projects/default/components/power/battery/main
→ 200 OK
ETag: "sha256:abc123..."
Content-Type: application/json

{
  "spec": { "capacity_wh": 100, "nominal_voltage_v": 3.7, ... },
  "design": { "depth_of_discharge": 0.8 },
  "requirements": { "depth_of_discharge_max": 0.8 }
}
```

### PATCH with optimistic lock
```http
PATCH /api/projects/default/components/power/battery/main
If-Match: "sha256:abc123..."
Content-Type: application/json

{ "spec": { "capacity_wh": 120 } }

→ 200 OK    (成功時、新 ETag を返す)
→ 412 Precondition Failed   (他者が先に更新済み)
→ 422 Unprocessable Entity  (validation error)
```

### Validation Error
```json
{
  "type": "validation_error",
  "errors": [
    {
      "loc": ["spec", "capacity_wh"],
      "msg": "Input should be greater than or equal to 0",
      "type": "greater_than_equal",
      "input": -10
    }
  ]
}
```

---

## CLI 対応表

```bash
# schema
craft schema list                                # GET /schema/systems
craft schema show power battery                  # GET /schema/power/battery

# components
craft get power battery                          # list instances
craft get power battery main                     # get one
craft create power battery aux --from spec.toml  # POST
craft patch power battery main --set spec.capacity_wh=120
craft delete power battery aux

# verify
craft verify power                               # system
craft verify                                     # all
craft runs list
craft runs show {run_id}
craft runs latest

# history
craft history power.toml --limit 20
craft diff <sha1>..<sha2>
```

実装方針: CLI は **API クライアントの薄いラッパ**（在宅サーバを叩く）にして、ロジックの二重実装を避ける。
オプション: `--offline` で直接 file system にアクセスするモードも持つ（CI / バッチ用）。

---

## OpenAPI / Swagger UI の活用

- FastAPI が `/docs` で Swagger UI を自動提供 → これが **Phase 1 の主 UI**
- 「触れる API ドキュメント」として開発者が直接操作
- ReDoc (`/redoc`) で閲覧専用ドキュメントも自動生成
- `openapi.json` を CI で artifact 化 → クライアント SDK (TypeScript / Python) の自動生成にも将来活用可

---

## Web 時代に追加される endpoints（想定済みリスト）

> Phase 2 で Web UI を本格化する際、**追加** が確実に発生する endpoint 群。
> 「想定外の rework」を避けるため、ここに先回りで列挙しておく。
> 追加であって既存 API の破壊変更ではないことを確認する場として使う。

### per-field validation
| Method | Path | 用途 |
|---|---|---|
| POST | `/api/projects/{pid}/validate/{system}/{component}` | 部分ペイロード受領、フィールド単位の検証結果を返す。入力中のリアルタイムフィードバック用 |
| POST | `/api/projects/{pid}/validate/{system}/{component}/field` | 単一フィールドのみ検証（軽量） |

### drafts / staging
| Method | Path | 用途 |
|---|---|---|
| POST | `/api/projects/{pid}/drafts` | 編集中状態の保存（コミット前） |
| GET | `/api/projects/{pid}/drafts/{draft_id}` | draft 取得 |
| POST | `/api/projects/{pid}/drafts/{draft_id}/commit` | draft → 本データへ反映 |
| DELETE | `/api/projects/{pid}/drafts/{draft_id}` | 破棄 |

### 集約ビュー
| Method | Path | 用途 |
|---|---|---|
| GET | `/api/projects/{pid}/summary` | 衛星全体のサマリ（mass / power / thermal の総計） |
| GET | `/api/projects/{pid}/summary/{system}` | サブシステムサマリ |
| GET | `/api/projects/{pid}/dependencies` | サブシステム間依存グラフ |

### Push 通信
| Method | Path | 用途 |
|---|---|---|
| GET | `/api/projects/{pid}/runs/{run_id}/stream` (SSE) | 検証進捗の push |
| GET | `/api/projects/{pid}/events` (SSE / WS) | 任意の TOML 変更通知（多人数編集対応） |

### UI hint metadata
- スキーマレスポンスに `x-ui:` namespace を追加
- 例: `{ "x-ui": { "group": "electrical", "order": 1, "widget": "slider" } }`
- Component 側で `fld(group="electrical", order=1, widget="slider")` を生やす拡張
- → JSON Schema は不変、追加情報のみ。後方互換性あり

### Search / Pagination
- `GET /api/projects/{pid}/components/{system}?q=...&page=...&limit=...`
- スキーマ既存 endpoint の **クエリパラメータ追加** で済む（破壊なし）

---

## Analysis API — 関数の自動 API 化

> **アイデア**: コンポーネント定義と同じ思想で、**解析関数も decorator で登録 → 自動 API 化**。
> 解析一覧を別途メンテする必要がなくなる。Swagger UI に自動掲載。

### 動機

- 旧スタイルでは「power_budget」「link_budget」「thermal_balance」などの解析関数を、
  - (1) Python モジュールに実装
  - (2) CLI コマンドに登録
  - (3) Web 用エンドポイントを別途実装
  - (4) ドキュメントに「使える解析一覧」を手動メンテ
  - → **4箇所メンテ**
- 新スタイル: **decorator 1 つで全部** に流れる

### `@analysis` decorator イメージ

詳細シグネチャは [[Analysis詳細仕様]] を参照（引数の `vq.Ref` 規約は §13）。

```python
from craft.schema import analysis, fld
import veriq as vq

@analysis(
    name="battery_eol_capacity",                     # system はファイルパスから推論
    desc="バッテリーの End-of-Life 容量を寿命と充放電サイクルから算出",
    tags=["power", "lifetime"],
)
def battery_eol_capacity(
    batteries: Annotated[vq.Table[BatteriesName, BatteryEntry], vq.Ref("$.batteries")],
    years: float = fld(ge=0, unit="year"),
    cycles_per_day: float = fld(ge=0, default=1.0),
) -> EolResult:                                      # 戻り値は Pydantic model
    ...
    return EolResult(capacity_wh=..., degradation_pct=...)
```

### field helper は `fld()` 一本

`cf()` / `af()` / `qf()` は全廃止。`fld()` で Component / Config / Analysis のフィールドを統一表現（[[最終構成]] §5.1）。

### 自動生成される endpoint

| Method | Path | 用途 |
|---|---|---|
| GET | `/api/analyses` | 登録済み解析一覧（system / name / desc / tags） |
| GET | `/api/analyses/{system}` | サブシステム単位の解析一覧 |
| GET | `/api/analyses/{system}/{name}/schema` | 入力 / 出力 JSON Schema |
| POST | `/api/analyses/{system}/{name}` | 解析実行（同期） |
| POST | `/api/analyses/{system}/{name}/async` | 非同期実行（job ID 返却、`/runs/{id}` でポーリング） |

### 自動生成される CLI

```bash
craft analysis list                              # GET /api/analyses
craft analysis show power battery_eol_capacity   # schema 表示
craft analysis run power battery_eol_capacity \
  --spec data/system/power.toml#batteries.main \
  --years 5 --cycles-per-day 2
```

### Swagger UI への自動掲載

- FastAPI の `add_api_route()` を analyses registry から動的に呼び出し
- `/docs` を開けば全解析が **「触れる API ドキュメント」** として現れる
- 解析名・説明・パラメータ・例が自動的にカタログ化される
- → **「使える解析一覧」を別途書かなくていい**

### veriq との関係（**方針 C で確定**）

`@scope.calculation()` / `@scope.verification()` と概念が近い。重複を避けつつ柔軟性を取るため:

✅ **方針 C 採用**: `@analysis` は両モードをサポート
- `@analysis(scope=power, verify=True)` → 内部で `@power.calculation()` を呼び、veriq 検証フローに乗る + API/Swagger に露出
- `@analysis(scope=None)` → veriq 外のアドホック解析。API/CLI 用途のみ

```python
# veriq 連携モード
@analysis(scope=power, desc="バッテリ消費電力")
def battery_drain(spec: BatterySpec, mode: OperationMode) -> float:
    ...   # veriq の依存グラフに乗る

# アドホックモード
@analysis(desc="任意 2 コンポーネントの熱結合係数")
def thermal_coupling(a: PanelSurface, b: PanelSurface) -> float:
    ...   # veriq には登録されない、純粋な API
```

実装段階:
1. **Phase 1a**: アドホックモード（`scope=None`）のみ実装、API/CLI/Swagger 連携を完成
2. **Phase 1b**: veriq 連携モードを追加。`scope` 渡された時に `@scope.calculation()` を内部呼び出し
3. **Phase 2**: veriq 側の `--kind calc` 出力と analysis registry の整合性を CI で検証

### registry の拡張

[[UnifiedRegistry設計]] の `analyses` 名前空間に登録する:

```
schema/_registry.py        ← UnifiedRegistry (components / configs / analyses を束ねる)
schema/_analysis.py        ← @analysis decorator 実装
schema/auto_discover.py    ← systems/<name>/analyses.py を pkgutil 走査
api/routers/analyses.py    ← /api/analyses/* を動的に生やす
```

`systems/power/components.py` と同じディレクトリの `systems/power/analyses.py` に `@analysis` 関数を書く（[[最終構成]] §4）。

### 入力ソースの解決

解析は **既存の TOML データを入力に取りたい** ことが多い:

```bash
# CLI: TOML パスを直接指定
craft analysis run power battery_eol_capacity \
  --spec data/system/power.toml#batteries.main \
  --years 5
```

API でも同様に、**「インスタンス参照」を入力にできる** ようにする:

```http
POST /api/analyses/power/battery_eol_capacity
{
  "spec": { "$ref": "components/power/battery/main" },
  "years": 5,
  "cycles_per_day": 2
}
```

`$ref` を解析関数の起動前にレジストリで解決。生 dict 渡しも当然サポート。

### キャッシュ / 再現性

- 解析結果は `generated/runs/analyses/{name}/{key}.toml` にキャッシュ可（[[データパイプライン]] §2）
- hash = `(analysis_name, input_payload_hash, code_version)`
- 同一入力なら即返し、再現性も担保

### 議論ポイント

- `@analysis` と `@scope.calculation` の住み分けを早期に決める（方針 A/B/C）
- 解析の **副作用許容**（TOML を更新する解析を許すか）→ 原則 pure function 推奨、副作用版は別 decorator
- **長時間解析** の非同期化基準（5秒 threshold とか）

---

## Cross-component Query — 横断検索

> **動機**: `power_mode` のような複数コンポーネントで共通に現れる属性を横断検索したい。
> 「使われている全 OperationMode 列挙」「safe_mode で動く全コンポーネント」「消費電力合計」など。

### 方針: `@query` は採用せず、`@analysis` + `vq.Table` で書く

旧案では `@query` decorator を導入する方向だったが、[[最終構成]] §10 / [[Analysis詳細仕様]] §13.4 で **`@query` は廃止** に決定。
理由:
- `@analysis` が既に「入力 → 戻り値」の純粋関数を表現できる
- `vq.Table[K, V] + vq.Ref("$.batteries")` で「サブシステム内の全インスタンス」を入力に取れる
- decorator が増えるほど学習コスト・registry 分岐が増える

### 横断集計の書き方（例）

```python
@analysis(tags=["introspection"])
def enum_usage(
    batteries: Annotated[vq.Table[BatteriesName, BatteryEntry], vq.Ref("$.batteries")],
    panels:    Annotated[vq.Table[PanelsName, SolarPanelEntry], vq.Ref("$.solar_panels", scope="power")],
    enum_type: str,
) -> dict[str, list[ComponentRef]]:
    """使用中の enum 値を集計"""
    ...
```

→ Python の素直なループで実装、自動 API 化も `@analysis` の機構をそのまま使える。

### メタデータ照会は built-in introspection endpoint

「登録済み component 一覧」「フィールド検索」のような registry メタ照会は、解析関数ではなく専用 endpoint:

| Method | Path | 用途 |
|---|---|---|
| GET | `/api/projects/{pid}/registry/components` | 全 component の (system, name, plural, fields) |
| GET | `/api/projects/{pid}/registry/analyses` | 全 @analysis の (name, signature, tags) |
| GET | `/api/projects/{pid}/registry/search?field=...` | フィールド名・型で横断検索 |

→ [[UnifiedRegistry設計]] の introspection API がそのまま HTTP に出る。

---

## veriq Pass-through API

> [[veriq仕様メモ]] にある veriq CLI 機能を HTTP 経由で叩けるラッパ。
> Web / 他システムから veriq の依存グラフや要求トレーサビリティを取得するために必要。

### 設計方針

- veriq CLI は `--json` 出力をサポートする → `subprocess` で実行して JSON をそのまま返す
- 重い計算系 (`calc`) は **非同期 job** に、軽い参照系 (`scopes`/`list`/`show`/`tree`/`trace`) は **同期** で

### Endpoints

| Method | Path | 対応 veriq CLI |
|---|---|---|
| GET | `/api/projects/{pid}/veriq/scopes` | `veriq scopes` |
| GET | `/api/projects/{pid}/veriq/nodes?kind=...&scope=...` | `veriq list --json` |
| GET | `/api/projects/{pid}/veriq/nodes/{node_id}` | `veriq show <node> --json` |
| GET | `/api/projects/{pid}/veriq/nodes/{node_id}/tree?depth=N&invert=bool` | `veriq tree <node> --json` |
| GET | `/api/projects/{pid}/veriq/trace` | `veriq trace --json` |
| GET | `/api/projects/{pid}/veriq/check` | `veriq check` (構造妥当性) |
| GET | `/api/projects/{pid}/veriq/schema` | `veriq schema` (入力 JSON Schema) |
| POST | `/api/projects/{pid}/veriq/calc` | `veriq calc --verify` (job 化) |
| POST | `/api/projects/{pid}/veriq/diff` | `veriq diff` |

### CLI ラッパの注意

- `subprocess` 経由は **環境依存性が高い**（PATH、Python venv）→ Python API で直接叩く方が望ましい
  - veriq の Python API が CLI と等価なら **`veriq.cli.main` を import して呼ぶ** か、 **内部関数を直接叩く**
- いずれにせよ Phase 1a は subprocess で動かして、Phase 1b で Python API に移行する段階運用

### Tracability の活用

`veriq trace` の出力（要求 ↔ 検証マッピング）は将来の Web UI で **「要求充足ダッシュボード」** の基盤になる。今のうちに API で叩ける状態にしておく価値が高い。

---

## Swagger UI の常時運用

- FastAPI デフォルトで `/docs` (Swagger UI) と `/redoc` (ReDoc) を自動提供
- **無効化しない**。むしろ Phase 1 の主 UI として正式採用
- カスタマイズ:
  - `tags_metadata` でセクション分け（Schema / Components / Verify / Analysis / History）
  - 各 endpoint に `summary` / `description` / `response_model` / `examples` を必ず付ける
  - OpenAPI title / description / version をプロジェクト名に
- 開発時は `--reload` で常駐、`http://localhost:8002/docs` を開きっぱなしにする運用
- CI で `openapi.json` を生成 → 差分が出たら PR コメントで通知（破壊的変更の早期検知）

---

## 未決定論点

- **非同期 job 管理**: `POST /verify` は同期 / 非同期 / SSE のどれにするか
  - 暫定: 短時間 (<5s) は同期、長時間は job ID 返却 + `GET /runs/{id}` ポーリング
- **ETag 計算コスト**: 大きい TOML で毎回 sha256 を計算するコスト → mtime ベース or キャッシュ
- **bulk operation**: 「複数インスタンス一括追加」のニーズが出たら考える
- **websocket / SSE**: 検証進捗の push 通知。Phase 2 で
