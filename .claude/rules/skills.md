# スキルの使いどころ

> `my-plugin` が提供するスキルを「いつ呼ぶか」の正典。スキルは description に基づいて
> 自動で起動しうるが、取りこぼしを防ぐためここに状況→スキルの対応を明示する。
> スキルの中身（手順）は各 `SKILL.md` が持つ。ここは**トリガー判断だけ**を書く。

## 使う前に

- 何かを始める前に「この作業に効くスキルはないか」を一度考える。特に
  **テスト・セキュリティ・API 設計・E2E・ドキュメント調査・ファイル変換**は対応スキルがある。
- 該当が思い当たらないときは `find-skills` に「こういうことをしたい」と投げて探させる。

## 状況 → スキル 早見表

| こういう時 | 使うスキル |
|---|---|
| 新機能を書く / バグ修正 / リファクタする | `tdd-workflow`（テスト先行・カバレッジ80%+を強制） |
| 認証・ユーザー入力・秘密情報・決済・新規エンドポイントを扱う | `security-review`（セキュリティチェックリスト） |
| REST API を設計する（命名・ステータス・ページング・エラー形・バージョニング） | `api-design` |
| 命名・可読性・不変性など言語横断の基本規約を確認したい | `coding-standards` |
| ブラウザ越しの E2E テストを書く / Playwright・Page Object・CI 連携 | `e2e-testing` |
| MCP サーバを作る（tools / resources / prompts / Zod / stdio・HTTP） | `mcp-server-patterns` |
| ライブラリ/フレームワークの最新の使い方・API・サンプルを知りたい | `documentation-lookup`（Context7 経由で最新ドキュメント） |
| あるトピックを根拠付き・引用付きで深く調べたい | `deep-research`（firecrawl / exa で多源調査） |
| PDF・docx・xlsx・pptx・画像・音声・HTML 等を Markdown 化／中身を取り出す・読む・要約する | `markitdown` |
| エージェント（自分）の失敗を構造的に自己デバッグしたい | `agent-introspection-debugging` |
| エージェントの挙動を評価駆動（EDD）で形式的に測りたい | `eval-harness` |
| 長い作業の区切りで文脈を意図的に圧縮して保持したい | `strategic-compact` |
| 「〜できるスキルある？」「どうやって X する？」と機能を探している | `find-skills` |

## 迷いやすい境界

- **`tdd-workflow` と `e2e-testing`** … 実装サイクル全体（unit〜）の進め方なら `tdd-workflow`、
  ブラウザ越しのシナリオテスト実装テクニックなら `e2e-testing`。新機能なら前者で始め、
  E2E が要る段で後者を併用。
- **`documentation-lookup` と `deep-research`** … 特定ライブラリの「正しい使い方/API」は
  `documentation-lookup`（公式ドキュメント直引き）。トピックを横断して根拠を集めるなら
  `deep-research`（Web 多源 + 引用）。
- **PDF・Office を読む／要約したい** … いずれも `markitdown` で Markdown 化してから読む・要約する。
  専用の PDF 精読コマンドは無いので「変換 → 必要箇所を読む → 要約」の流れで扱う。
- **`security-review` は事後ではなく着手時に** … 認証・入力処理・秘密情報・決済の実装を
  「書き始める前」に呼ぶ。書き終えてからのレビューよりチェックリストが効く。

## トークン効率の良い読み方（markitdown）

大きいファイルを「生のまま」「丸ごと」読むとトークンを浪費する。**一度クリーンな
Markdown に変換してから読む／grep する**のが基本。

- **ページの多い PDF・Office 文書・スプレッドシート・画像 等** → まず `markitdown` で
  Markdown 化する。書式ノイズが落ちて compact なテキストになり、そのまま読む／必要箇所だけ
  grep できる。バイナリを直接読ませたりページを総当たりするより遥かに少ないトークンで済む。
  - 対応: PDF / .docx / .xlsx / .pptx / 画像 / 音声 / HTML / CSV / JSON / XML / ZIP / EPub / YouTube URL
- **読む・要約する場合も同じ**: まず `markitdown` で Markdown 化し、見出しから必要な節を
  絞って読む／要約する。専用の PDF 精読コマンドは無い（変換 → 読む → 要約 の流れで扱う）。
- **典型フロー**: `markitdown で .md 化` → 目次/見出しを掴む → 必要な節だけ Read/grep。
  全文をコンテキストに載せない。長文なら要約してから次の作業に渡す。

## codegraph の使い方（コードを書く前に引く）

codegraph は **全シンボル・呼び出し関係・ファイルの SQLite 知識グラフ**。読み取りはサブミリ秒で、
**コードを書く/直す前**に当たりを付けるために使う（書いている最中ではなく着手前）。

- **初回だけ index を作る**: `just -f .claude/justfile codegraph-init`
  （= `codegraph init -i`）。状態確認は `codegraph-status`。index はファイル監視で
  約1秒遅れて追従する。
- **原則: grep/Read のループより先に codegraph。** 構造的な問いは codegraph が
  事前構築済みの検索インデックスなので、自前で grep+read を繰り返すより速く・正確で・
  トークンも少ない。サブエージェントに探索を丸投げするのも二重作業。

| 知りたいこと | ツール |
|---|---|
| 「X はどう動く？」「アーキは？」「どこにある？」「この辺を概観したい」 | `codegraph_explore`（**第一候補・まずこれ1回**。関連シンボルの**ソースをファイル別に verbatim 返却** = Read 相当。たいていこれだけで足りる） |
| 「X から Y への流れ／経路」 | `codegraph_explore` に流れを跨ぐシンボル名を並べて渡す（コールバック等の動的ディスパッチも辿る） |
| 「シンボル X の場所だけ知りたい」 | `codegraph_search` |
| 「これを呼ぶのは？」「これは何を呼ぶ？」「変えたら何が壊れる？」 | `codegraph_callers` / `codegraph_callees` / `codegraph_impact` |
| 「特定シンボルの完全なソース／オーバーロード名」 | `codegraph_node` |
| 「ファイル一覧・構成」 | `codegraph_files` |
| 「index は健康？」 | `codegraph_status` |

- **`codegraph_explore` がほぼ唯一の入口**。自然文の質問でも、シンボル/ファイル名の羅列でも受ける。
  足りない一点を確かめる時だけ生の Read/grep に降りる。
- **codegraph が使えない環境**では `rg` / `rg --files` で代替し、「このセッションでは
  codegraph MCP が露出していない」と明記する。

## 関連する道具（スキル以外）

- `/setup-project` — ルール一式・Codex 機械を展開（コマンド）
- codegraph MCP — 上記「codegraph の使い方」を参照
- Codex 連携 — 実装の委譲は [`codex-workflow.md`](codex-workflow.md) を参照
