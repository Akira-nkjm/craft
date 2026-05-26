# 開発コマンドリファレンス

> プロジェクトごとに編集するテンプレート。実際に動くコマンドだけを書く（陳腐化防止）。

## セットアップ

```bash
# 依存インストール
<install-command>
```

## 実行

```bash
# 開発サーバ / メインエントリ
<run-command>
```

## テスト

```bash
<test-command>                 # 全テスト
<test-command> <filter>        # 単一テスト
<coverage-command>             # カバレッジ
```

## コード品質

```bash
<lint-command>                 # Lint
<lint-command> --fix           # 自動修正
<format-command>               # フォーマット
<typecheck-command>            # 型チェック
```

## ビルド / リリース

```bash
<build-command>
<release-command>
```

## その他のタスク

<!-- プロジェクト固有のコマンドをここに -->
