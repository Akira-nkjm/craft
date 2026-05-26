# Instincts

セッションから抽出した**再利用可能なパターン**を蓄積するディレクトリ。ECC の continuous-learning システムの軽量版。

## 何が入るか

エージェントが作業中に学んだ「経験則」を YAML で保存する。例:

- 特定のライブラリの落とし穴と回避策
- このプロジェクト固有のビルド失敗パターンと対処
- ユーザーが好む実装スタイル（過去のフィードバック由来）
- よく使われるコマンドの組み合わせ

## ディレクトリ構成

```
.claude/instincts/
├── README.md              # このファイル
├── project/               # このプロジェクト固有のインスティンクト
│   └── <topic>.yaml
└── inherited/             # 他プロジェクトから移植したもの
    └── <topic>.yaml
```

`project/` がプライマリ。汎用性が確認されたら `~/.claude/instincts/` に昇格（promote）する。

## YAML スキーマ

```yaml
name: <short-kebab-case>           # ファイル名と一致させる
description: <一行サマリー>
scope: project | inherited
confidence: low | medium | high    # 観測回数で上げていく
observations: <int>                # 何回観測されたか
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [<tag1>, <tag2>]

# 本体
trigger: |
  いつこのインスティンクトが発火するか（観測可能な条件）

guidance: |
  そのとき何をすべきか（実行可能な手順）

rationale: |
  なぜそうするのか（理由がないと風化する）

examples:
  - context: <状況>
    action: <とった行動>
    outcome: <結果>
```

## いつ書くか

- 同じ修正・回避策を 2 回以上したとき
- ユーザーから明示的なフィードバックを受けたとき
- ハマったあとに「最初からこうすればよかった」と気づいたとき

## いつ読むか

- 新しいタスクの計画段階
- ビルド・テスト失敗時
- ユーザーの好みに関わる判断時

## メモリとの違い

| | memory (`~/.claude/projects/.../memory/`) | instincts (`.claude/instincts/`) |
|---|---|---|
| スコープ | エージェントの長期記憶（自由形式） | 再利用可能パターン（構造化 YAML） |
| 共有 | 個人のローカル | git でチーム共有可 |
| 形式 | Markdown フリーフォーム | スキーマ付き YAML |
| 用途 | 「ユーザーは X 派」「過去に Y で失敗」 | 「Z パターンには W で対処」 |

## ECC 完全版との差

ECC は `instinct-cli.py` (72KB) で promote / evolve / prune などを自動化していますが、本リポジトリは **手書き YAML** + 通常の git 管理で運用します。仕組みが必要になったら CLI 化を検討してください。
