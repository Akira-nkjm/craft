---
project: "Craft"
status: 進行中
start_date: 2026-05-22
end_date:
tech: "Python, Pydantic, FastAPI, veriq, TOML"
tags: [project, dev, satellite]
---

# Craft — Concept Registry for Automated spacecraFT design

> **C**oncept **R**egistry for **A**utomated spacecra**FT** design
> 旧称: SatDesignAuto（2026-05-26 改名）。CLI / Python package も `craft`。

## 概要
> 宇宙機（衛星・深宇宙機含む）の概念設計を **「型付き計算グラフ」** として宣言的に書き、
> API / CLI / Swagger / LLM が同じ定義から自動派生する基盤。
> veriq による検証パイプラインとシームレスに統合する。

## 目標
- コンポーネント定義のボイラープレートを最小化（旧 ~50行 → 新 ~15行）
- Python コード変更なしに Web / API からインスタンス追加可能にする
- Pydantic JSON Schema をフロントに配信し、フォームを自動生成
- veriq による検証パイプラインとシームレスに統合

## 技術スタック
- **型定義**: Pydantic v2 + Component / Config base class（方式 C、decorator なし）
- **API**: FastAPI（Swagger UI を Phase 1 の主 UI とする）
- **データ**: TOML（アトミック書き込み、動的 StrEnum）
- **検証**: veriq（Python API 直接呼び出し、subprocess 廃止）
- **LLM**: MCP サーバ方式（Claude Code / Desktop から直接対話）
- **フロント**: Vanilla JS SPA（Phase 2 以降）

---

## ドキュメント構成

### 🎯 入口 — まずここを読む
- [[最終構成]] — **目標アーキテクチャ（唯一の真）**。他ノートと矛盾したらこちらを採る

### 📂 フォルダ別 MAP（各フォルダの hub）
- [[仕様 MAP]] — `01_仕様/` 配下を役割別に整理
- [[リファレンス MAP]] — `02_リファレンス/` 配下の早見表
- [[議論 MAP]] — `03_議論と未決事項/` 配下の論点フロー
- [[archive MAP]] — `archive/` 配下の旧資料と統合先

### 01_仕様/ — 確定済み詳細仕様（実装の参照源）
- [[UnifiedRegistry設計]] — 中央 registry の interface と契約
- [[コンポーネントデコレータ仕様]] — Component base class の仕様（§9 に「なぜ base class か」の根拠も統合）
- [[Analysis詳細仕様]] — `@analysis` の完全シグネチャ（§13 に `vq.Ref` 引数参照も統合）
- [[Config設計]] — `Config` base class（mission_profile, orbital_parameters 等）
- [[インスタンス多重度]] — Singleton vs Multi-instance、命名規約
- [[API設計]] — FastAPI ルーティング、`@analysis` の自動 API 化、veriq pass-through
- [[MCP設計]] — MCP サーバ仕様（tool 命名規約、registry 派生、stdio 接続）
- [[データパイプライン]] — TOML merge (`generated/merged.toml`) と scaffold（registry → data.toml 雛形）
- [[プロジェクト初期化]] — `craft init` CLI（project / subsystem / component / config / analysis）
- [[テスト戦略]] — テストピラミッドと E2E（CLI / HTTP / MCP）

### 02_リファレンス/ — 外部仕様・早見表
- [[veriq仕様メモ]] — 公式ドキュメント抜粋（CLI / Python API）
- [[宣言とTOMLの対応表]] — 全 11 パターンの Python ⇔ TOML 対応

### 03_議論と未決事項/ — 開いている論点
- [[懸念事項]] — 全体横断の懸念洗い出し（観点の網羅性メモ）
- [[対処方針]] — 懸念事項への推奨アプローチ（✅/🤔/❌で優先順位付き、**結論はここ**）
- [[課題と検討事項]] — 未解決の設計課題（決着済みは末尾に隔離済み）

### archive/ — 取り込み済み・古い案（履歴参照用、現役ではない）
- [[設計書]] — 旧アーキテクチャ概要（最終構成に統合済み）
- [[構成見直し案]] — subsystem 中心レイアウト提案（採用済み）
- [[設計レビュー]] — 旧状態の横断レビュー（指摘は最終構成・各仕様に反映済み）
- [[未決事項解説]] — §10 論点の解説（論点は全て決着済み）
- [[型検証と宣言方式]] — 方式 A/B/C 比較の詳細記録（結論は [[コンポーネントデコレータ仕様]] §9 に統合）
- [[Ref設計]] — `vq.Ref` 設計の比較・経緯（結論は [[Analysis詳細仕様]] §13 に統合）
- [[Datasheet設計]] — `WithDatasheet` trait 案（採用見送り、`shared_spec=True` default で代替）

### 📁 [[実装テンプレート/README|実装テンプレート/]]
- Component base class + subsystem 中心レイアウトの最小例集

---

## Phase 方針

- **Phase 1（現在）**: API + CLI + 型基盤を固める。Swagger UI を当面の対話 UI とする
- **Phase 2**: Component 拡張（datasheet_only / ネスト型）、マルチプロジェクト化、Web UI

---

## API 早見表（詳細は [[API設計]]）

すべて `/api/projects/{pid}/...` 配下（Phase 1 は `pid=default` 固定）。

| グループ | 主要エンドポイント | 役割 |
|---|---|---|
| Schema | `GET /schema/{subsystem}/{component}` | Pydantic JSON Schema を配信（フォーム自動生成の元） |
| Instances | `GET/POST/PUT/PATCH/DELETE /components/{subsystem}/{component}/{instance}` | TOML 上のインスタンス CRUD（ETag / If-Match で楽観的ロック） |
| Analyses | `POST /analyses/{subsystem}/{name}` | `@analysis` 関数を自動 API 化（[[Analysis詳細仕様]]） |
| Merge | `POST /merge` / `GET /merged` | 全 subsystems/*/data.toml を `generated/merged.toml` に統合（[[データパイプライン]]） |
| Scaffold | `POST /scaffold[/{subsystem}]` / `GET /scaffold/preview/{subsystem}` | registry から data.toml の雛形を生成・整形（既存値は破壊しない） |
| Verification | `POST /verify` / `POST /verify/{subsystem}` | veriq 検証を非同期 job として実行（実行前に merge 自動再生成） |
| Runs | `GET /runs` / `GET /runs/{id}` / `GET /runs/latest` | 検証結果の参照 |
| History | `GET /history` / `GET /diff` | TOML 変更履歴（git 由来） |
| Meta | `GET /projects` / `GET /healthz` / `GET /version` | プロジェクト一覧・死活・スキーマ版数 |

設計原則:
- **OpenAPI が一次仕様**（FastAPI 自動生成 → CI で版数管理）
- **CLI と API は機能等価**（`craft cli <verb>` ↔ `curl <endpoint>` 1:1 対応）
- **エラーは RFC 7807 互換**の共通レスポンス形式（[[最終構成]] §5.4）
- **veriq pass-through は subprocess 廃止**、Python API を直接 import（[[veriq仕様メモ]]）

---

## タスク

### Todo
- [ ] Component の表現力拡張（datasheet_only、ネスト型）の設計
- [ ] `build_project(data_root)` factory による in-process verify 対応
- [ ] `com` / `thermal` サブシステムの veriq スコープ実装
- [ ] `aocs` / `cdh` / `payload` / `prop` / `structure` の Component 移行
- [ ] **`@analysis` decorator** による解析関数の自動 API 化
- [ ] **Swagger UI** をプロジェクト主 UI として正式採用、tags / examples の整備
- [ ] **MCP サーバ**実装（LLM 連携）
- [ ] **merge / scaffold** 実装 — `core/{merge,scaffold,toml_formatter}.py` + CLI / API（[[データパイプライン]]）
- [ ] **craft init** CLI 実装 — project/subsystem/component/config/analysis、テンプレート 3 種（[[プロジェクト初期化]]）

### In Progress
- [ ] `experiment/` PoC の継続検証

### Done
- [x] `power` サブシステムの Component 移行と veriq 連携
- [x] 動的 StrEnum による Web 追加 → veriq 認識の検証
- [x] アトミック TOML 書き込みの実装
- [x] ドキュメント整理（2026-05-26、22ファイルを 4 階層に再編）

---

## 参考資料（コードベース）
- 既存スタック: `design/scopes/subsystem/power/models.py`
- 新スタック: `experiment/schema/subsystems/power.py`
