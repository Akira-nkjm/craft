# プロジェクト固有の設定

## プロジェクト概要

Craft — Concept Registry for Automated spacecraFT design。
詳細な計画は [`plan/Craft/Craft.md`](../../plan/Craft/Craft.md) を参照。

## 規約・注意事項

### Python パッケージ構成

**`src/craft/` レイアウト + `systems/` を root に残す**構成・単一 `pyproject.toml` で運用する。

```
craft/
├── pyproject.toml          # 全 deps をここに集約
├── src/craft/              # framework 本体
│   ├── schema/             # base classes / registry
│   ├── core/               # I/O / merge / scaffold 等
│   ├── api/                # FastAPI
│   ├── cli/                # Typer CLI
│   └── mcp_server/         # MCP サーバ
├── systems/                # ユーザ領域 (system ごとに 1 ディレクトリ)
│   ├── project.py          # veriq エントリポイント
│   └── power/
└── tests/
```

- ユーザが日常的に編集するのは `systems/` のみ。framework 実装は `src/craft/` に隠して root の見通しを保つ
- workspace 機能や `packages/<name>/` 階層は使わない（単一 pyproject.toml で配布する方針）
- 全依存はルート `pyproject.toml` の `[project].dependencies` に集約
- 開発ツール（ruff / pyrefly / pytest）はルートの `[dependency-groups].dev`
- `pyproject.toml` の `tool.hatch.build.targets.wheel.packages = ["src/craft", "systems"]` で単一 wheel としてビルド

#### 分割を検討するケース（将来）

以下のいずれかが当てはまるようになったら、その時点で分割を検討する:

- consumer が 3 個以上に増え、依存範囲を明示的に切り分けたい（例: api/cli/mcp が独立した重い依存を持つ）
- 外部から再利用される独立ライブラリができた
- バージョン管理を個別にしたい

それまでは「1 ディレクトリ追加で機能が増える」状態を保つ。

## 関連ドキュメント

- 開発コマンドは [`commands.md`](commands.md) に書く
- アーキテクチャと設計判断は [`architecture.md`](architecture.md) に書く
