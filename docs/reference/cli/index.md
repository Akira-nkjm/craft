# CLI リファレンス

Craft CLI (`craft`) は宇宙機概念設計レジストリを操作するコマンドラインツール。
[Typer](https://typer.tiangolo.com/) で構築されており、`uv run craft <command>` で実行する。

---

## クイックリファレンス

| コマンド | 説明 | ページ |
|---|---|---|
| `craft schema list` | 登録済み system / component を一覧 | [Schema](schema.md) |
| `craft schema show <sub> <comp>` | component の JSON Schema を表示 | [Schema](schema.md) |
| `craft get <sub> <comp> [<inst>]` | インスタンスを取得（ETag 付き） | [Instances](instances.md) |
| `craft create <sub> <comp> <inst>` | 新規インスタンスを作成 | [Instances](instances.md) |
| `craft put <sub> <comp> <inst>` | インスタンスを完全置換 | [Instances](instances.md) |
| `craft patch <sub> <comp> <inst>` | インスタンスを部分更新 | [Instances](instances.md) |
| `craft delete <sub> <comp> <inst>` | インスタンスを削除 | [Instances](instances.md) |
| `craft spec get <sub> <comp>` | MultiInstance の共有 spec を取得 | [Instances](instances.md) |
| `craft spec set <sub> <comp>` | MultiInstance の共有 spec を更新 | [Instances](instances.md) |
| `craft merge` | `data.toml` → `merged.toml` を生成 | [Pipeline](pipeline.md) |
| `craft scaffold [<sub>]` | registry から `data.toml` 雛形を生成 | [Pipeline](pipeline.md) |
| `craft verify` | merge → veriq 検証を実行 | [Pipeline](pipeline.md) |
| `craft runs list` | verification run の一覧 | [Pipeline](pipeline.md) |
| `craft runs show <run_id>` | run の詳細 | [Pipeline](pipeline.md) |
| `craft runs latest` | 最新 run を表示 | [Pipeline](pipeline.md) |
| `craft runs artifact <run_id> <name>` | run のアーティファクトを stdout に出力 | [Pipeline](pipeline.md) |
| `craft analysis list` | 登録済み @analysis 関数の一覧 | [Analysis](analysis.md) |
| `craft analysis run <sub\|_> <name>` | analysis を実行 | [Analysis](analysis.md) |
| `craft gen-stubs` | system ごとに `_stubs.pyi` を生成 | [Tools](tools.md) |
| `craft init system <name>` | system の雛形ディレクトリを生成 | [Tools](tools.md) |
| `craft history [<path>]` | git log を JSON で出力 | [Tools](tools.md) |
| `craft diff <from> <to> [<path>]` | 2 つの ref 間の差分を表示 | [Tools](tools.md) |

---

## コマンドグループ

<div class="grid cards" markdown>

- **[Schema](schema.md)**

    Registry に登録された system・component のメタ情報を確認する。
    新しい Component を追加した後の確認に使う。

- **[Instances](instances.md)**

    `get` / `create` / `put` / `patch` / `delete` / `spec` —
    インスタンスデータの読み書きと ETag による排他制御。

- **[Pipeline](pipeline.md)**

    `merge` / `scaffold` / `verify` / `runs` —
    data.toml から veriq 検証までの処理フローを操作する。

- **[Analysis](analysis.md)**

    `@analysis` 関数の一覧と実行。veriq バインド型と ad-hoc 型の両方に対応。

- **[Tools](tools.md)**

    `gen-stubs` / `init` / `history` / `diff` —
    開発支援ツールとプロジェクト初期化。

</div>
