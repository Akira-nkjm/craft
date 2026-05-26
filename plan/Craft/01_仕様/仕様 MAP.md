---
project: "Craft"
tags: [project, dev, satellite, spec-map]
---

# 仕様 MAP

> 親: [[Craft]] / 真: [[最終構成]]

`01_仕様/` は **確定済み詳細仕様**（実装の参照源）。`最終構成.md` を要素ごとに掘り下げたもの。

---

## 中央契約

| ノート | 役割 | 関連 |
|---|---|---|
| [[UnifiedRegistry設計]] | components / configs / analyses を束ねる中央 registry の interface と契約 | [[最終構成]] §3, §5.3 |

## 宣言要素（設計者が書くもの）

| ノート | 何を定義するか | 例 |
|---|---|---|
| [[コンポーネントデコレータ仕様]] | hardware: `class X(Component, trait, ...):`（§9 に「なぜ base class か」の根拠） | Battery, SolarPanel |
| [[Config設計]] | 非 hardware: `class X(Config):` | MissionProfile, OrbitalParameters |
| [[Analysis詳細仕様]] | 解析関数: `@analysis def f(...) -> T:`（§13 に `vq.Ref` 引数参照記法） | battery_eol_capacity |

## 多重度・データ整形

| ノート | 役割 |
|---|---|
| [[インスタンス多重度]] | Singleton（OBC等 1 個確定）と Multi-instance の TOML テーブル名規約 |

> 同型製品の共通 spec は **`class X(Component):` の default (`shared_spec=True`)** で表現
> （[[宣言とTOMLの対応表]] §P1）。旧 `WithDatasheet` 案は採用見送り（archive [[Datasheet設計]]）。

## 横断レイヤ

| ノート | 役割 |
|---|---|
| [[API設計]] | FastAPI ルート全体（Schema/Instances/Analyses/Verification/Runs/History/Meta） |
| [[MCP設計]] | MCP サーバ — registry から tool を自動派生（Claude Code/Desktop 連携） |
| [[データパイプライン]] | TOML merge（systems/* → generated/merged.toml）と scaffold（registry → data.toml 雛形） |
| [[プロジェクト初期化]] | `craft init` CLI — project / system / component / config / analysis の立ち上げボイラープレート自動生成 |
| [[テスト戦略]] | テストピラミッド（Unit/Contract/Integration/Property/E2E） |

---

## 読み順のおすすめ

1. [[最終構成]] で全体像
2. [[コンポーネントデコレータ仕様]] / [[Config設計]] で「何を書くか」
3. [[UnifiedRegistry設計]] で「書いたものがどう束ねられるか」
4. [[API設計]] で「外からどう見えるか」
5. 必要に応じて [[Analysis詳細仕様]] / [[インスタンス多重度]] / [[宣言とTOMLの対応表]]
