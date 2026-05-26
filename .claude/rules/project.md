# プロジェクト固有の設定

## プロジェクト概要

Craft — Concept Registry for Automated spacecraFT design。
詳細な計画は [`plan/Craft/Craft.md`](../../plan/Craft/Craft.md) を参照。

## 規約・注意事項

### Python パッケージ構成

**フラットなディレクトリ構成・単一 `pyproject.toml`** で運用する。

```
craft/
├── pyproject.toml          # 全 deps をここに集約
├── schema/                 # framework: base classes
├── core/                   # framework: I/O 等
├── systems/                # ユーザ領域 (system ごとに 1 ディレクトリ)
│   └── power/
├── api/                    # FastAPI
└── tests/
```

- workspace 機能や `packages/<name>/` 階層は使わない（最終構成.md と一致させるため）
- 全依存はルート `pyproject.toml` の `[project].dependencies` に集約
- 開発ツール（ruff / pyrefly / pytest）はルートの `[dependency-groups].dev`

#### 分割を検討するケース（将来）

以下のいずれかが当てはまるようになったら、その時点で分割を検討する:

- consumer が 3 個以上に増え、依存範囲を明示的に切り分けたい（例: api/cli/mcp が独立した重い依存を持つ）
- 外部から再利用される独立ライブラリができた
- バージョン管理を個別にしたい

それまでは「1 ディレクトリ追加で機能が増える」状態を保つ。

## 関連ドキュメント

- 開発コマンドは [`commands.md`](commands.md) に書く
- アーキテクチャと設計判断は [`architecture.md`](architecture.md) に書く
