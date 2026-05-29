# REST API

Craft は FastAPI ベースの **REST API** を公開している。CLI / MCP と同じ registry を
共有しているので、`systems/<name>/components.py` に Component を追加すれば
API エンドポイントも自動で増える。

```bash
uv run uvicorn api.main:app --reload
# → http://localhost:8000/docs   (Swagger UI)
# → http://localhost:8000/redoc  (ReDoc)
```

Swagger UI から実際に GET/PUT/PATCH/POST を叩けるので、最初の探索には UI からの
操作が手早い。

---

## エンドポイント全体図

| プレフィックス | 目的 | 主な操作 |
|---|---|---|
| `/schema` | registry の JSON Schema を返す | GET 一覧 / GET 単品 |
| `/components` | Component インスタンスの CRUD | GET / POST / PUT / PATCH / DELETE |
| `/configs` | Config（単一・多重）の CRUD | GET / PUT / PATCH / DELETE |
| `/scaffold` | `data.toml` の雛形生成 / プレビュー | POST / GET |
| `/merge` | `data.toml` → `merged.toml` | POST / GET |
| `/verify` | veriq 検証実行（同期 / 非同期） | POST / GET job |
| `/analyses` | `@analysis` のメタ情報・実行 | GET / POST |
| `/runs` | verification run の履歴 | GET 一覧 / 詳細 / artifact |
| `/history` `/diff` | git log / git diff | GET |
| `/veriq` | veriq 内部の graph / trace / schema | GET （詳細以下） |

---

## /schema — registry の JSON Schema

```
GET  /schema                       # 登録済み system / component 一覧
GET  /schema/{system}/{component}  # 単一 component の JSON Schema
```

CLI の `craft schema list` / `craft schema show <sys> <comp>` と同じ内容を返す。
クライアント側でフォームを描画するときの **真の出所**。

---

## /components — Component CRUD

```
GET    /components/{system}/{component}             # 全インスタンス
GET    /components/{system}/{component}/{instance}  # 単一インスタンス
POST   /components/{system}/{component}/{instance}  # 新規作成 (MultiInstance のみ)
PUT    /components/{system}/{component}/{instance}  # 完全置換
PATCH  /components/{system}/{component}/{instance}  # 部分更新
DELETE /components/{system}/{component}/{instance}  # 削除
```

- 単一・複数の取得は **`ETag` レスポンスヘッダ** を返す
- 書き込み系は `If-Match` リクエストヘッダで楽観的排他制御
- Singleton では `{instance}` は固定キー（例: `obc/main` ではなく `/components/cdh/obc` 直下を扱う）

!!! note "MultiInstance の共有 spec"
    共有 spec を 1 リクエストでまとめて更新するエンドポイントは現状 API では
    `PUT /components/<sys>/<comp>/<inst>` 経由で各インスタンスを書き換える形か、
    [MCP の `set_<plural>_spec`](mcp.md#multiinstance) を使う。
    CLI なら `craft spec set <sys> <comp>` 一発。

---

## /configs — Config CRUD

### 単一 Config（フラット）

```
GET /configs/{system}/{config}   # 全体取得
PUT /configs/{system}/{config}   # 全置換 (If-Match 対応)
```

### MultiInstance Config（名前付きエントリ）

```
GET    /configs/{system}/{config}         # 全エントリ一覧
GET    /configs/{system}/{config}/{key}   # 1 エントリ取得
PUT    /configs/{system}/{config}/{key}   # 作成 or 全置換
PATCH  /configs/{system}/{config}/{key}   # 部分更新
DELETE /configs/{system}/{config}/{key}   # 削除
```

`OperationModeConfig` のような「名前付きパターンの集合」がこれに該当する。

---

## /scaffold — 雛形生成 / プレビュー

```
POST /scaffold              # 全 system に対して実行
POST /scaffold/{system}     # 特定 system のみ
GET  /scaffold/preview/{system}   # dry-run でプレビュー（書き込みなし）
```

`POST` は `?dry_run=true` を付けると変更を返すだけでファイルを書き換えない
（CLI の `--dry-run` と同等）。

レスポンス例:

```json
{
  "system": "power",
  "file_path": "systems/power/data.toml",
  "written": true,
  "added_paths": ["batteries.aux.requirements.depth_of_discharge_max"],
  "removed_warnings": []
}
```

---

## /merge — data.toml → merged.toml

```
POST /merge   # generated/merged.toml を更新
GET  /merged  # 現在の merged.toml の中身を返す
```

CLI の `craft merge` と同等。`merge` 直後に `verify` を呼ぶ典型的なフローを
スクリプト化したい場合はこのエンドポイントを使う（`/verify` も内部で merge を呼ぶので
通常はそれ一本でよい）。

---

## /verify — 検証実行

```
POST /verify                     # 同期実行（completion まで待つ）
POST /verify/async               # 非同期実行（job_id を返して即時応答）
GET  /verify/jobs/{job_id}       # job ステータス取得
```

同期レスポンス例:

```json
{
  "success": true,
  "errors": 0,
  "run_id": "20260526_120000_abc",
  "results": [
    { "scope": "power", "name": "verify_battery_capacity", "value": true }
  ]
}
```

非同期レスポンス:

```json
{ "job_id": "01HXYZ...", "status": "pending" }
```

長時間かかる verification や CI 連携では `POST /verify/async` → `GET /verify/jobs/<id>`
でポーリングする。

---

## /analyses — @analysis の照会と実行

```
GET  /analyses                       # 登録済み解析一覧 (ref_inputs / direct_inputs 付き)
GET  /analyses/{system}/{name}       # 単一解析のメタ情報
POST /analyses/{system}/{name}       # 解析実行
POST /analyses/_/{name}              # ad-hoc 解析 (system=None) 実行
```

- veriq バインド型では `POST` の body は空 (`{}`) でよい
- ad-hoc 型では body に引数 JSON を渡す（例: `{"initial_capacity_wh": 100.0, "years": 3.0}`)
- `/analyses` の `direct_inputs` を見ると、ad-hoc 型がどんな引数を期待しているか分かる

レスポンス例（ad-hoc）:

```json
{
  "analysis": "battery_eol_capacity",
  "system": null,
  "value": 89.075,
  "cache_hit": false
}
```

---

## /runs — verification run 履歴

```
GET /runs                            # 一覧 (新しい順)
GET /runs/latest                     # 最新 run
GET /runs/{run_id}                   # 詳細
GET /runs/{run_id}/artifacts/{name}  # artifact ファイル取得 (例: result.toml)
```

`craft runs ...` CLI と同じデータを HTTP で取得できる。
CI ダッシュボード等から verification の通過率を取りたい場合のエントリポイント。

---

## /history と /diff — git 履歴

```
GET /history?path=<path>&limit=<N>   # git log を JSON で返す
GET /diff?from=<sha>&to=<sha>&path=<path>   # git diff
```

`craft history` / `craft diff` の HTTP 版。設計変更のトレース・diff レビューに使う。

---

## /veriq — veriq pass-through

veriq の **graph / trace / schema** 機能を Python API で薄くラップしている
（CLI を subprocess 呼びしているわけではない）。

```
GET /veriq/scopes                    # 登録済み scope と calculation / verification 数
GET /veriq/nodes                     # 依存グラフの全ノード（kind / scope でフィルタ可）
GET /veriq/nodes/{node_path}         # 単一ノード詳細（path は `scope::path` 形式）
GET /veriq/trace                     # 要求 ↔ verification のトレーサビリティレポート
GET /veriq/check                     # project.input_model() が組み立て可能か
GET /veriq/schema                    # project.input_model() の JSON Schema
```

`/veriq/nodes` のクエリパラメータ:

| パラメータ | 例 | 説明 |
|---|---|---|
| `kind` | `MODEL` / `CALCULATION` / `VERIFICATION` | ノード種別でフィルタ |
| `scope` | `power` / `orbital` | scope 名でフィルタ |

`/veriq/trace` のレスポンスは「どの requirement がどの verification によって
検証されているか」「結果は何か」を summary 付きで返す。
**要求トレーサビリティ表** をビルドする時の真の出所。

---

## エラーレスポンス

`api.errors` の例外群が以下の HTTP ステータスに対応する:

| 例外 | HTTP | 用途 |
|---|---|---|
| `NotFoundError` | 404 | registry 未登録 / インスタンス無し |
| `ValidationFailedError` | 422 | スキーマ違反・引数エラー |
| `ConflictError` | 409 | ETag mismatch / merge conflict |
| `CraftAPIError` | 500 | veriq 内部例外などの想定外エラー |

全エラーレスポンスは `{ "detail": "<message>" }` 形式。

---

## CORS / 認証

現状の `api/main.py` には **認証は付いていない**（ローカル開発向け）。
本番運用する場合は uvicorn の前にリバースプロキシ（nginx / Caddy）を置くか、
FastAPI の dependency で API key 認証を追加する。

---

## 関連

- [Swagger UI](http://localhost:8000/docs)（ローカル起動時）
- [CLI リファレンス](cli/index.md) — 同じ操作を端末から行う
- [MCP リファレンス](mcp.md) — 同じ操作を LLM エージェントから行う
