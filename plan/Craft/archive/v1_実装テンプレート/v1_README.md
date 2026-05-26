---
project: "Craft"
tags: [project, dev, satellite, archive, template]
---

# v1 実装テンプレート（archive）

> ⚠️ **archive**: 旧レイアウト（v1）の実装テンプレート。現役は [[実装テンプレート/README|実装テンプレート/ (v2)]]。

---

## v1 と v2 の違い

| 観点 | v1（このフォルダ、archive） | v2（現役、`実装テンプレート/`） |
|---|---|---|
| 宣言方式 | `@component(system="power", mixin="temperature")` decorator + 文字列引数 | `class X(Component, TemperatureSensitive):` base class + trait 多重継承 |
| field helper | `cf()` / `af()` / `qf()` を使い分け | `fld()` 一本 |
| レイアウト | `schema/systems/<name>.py` + `analyses/systems/<name>.py` + `verification/scopes/<name>.py` の 3 並列 | `systems/<name>/{components,configs,analyses,scope,data}.py` に統合 |
| system 指定 | 引数で明示 | ファイルパスから自動推論 |

v1 → v2 への移行根拠は [[型検証と宣言方式]] と archive [[構成見直し案]] を参照。

---

## 含まれるファイル（参考）

- `schema/systems/{power,com,thermal}.md` — 旧 component 定義テンプレ
- `analyses/systems/power.md` — 旧 analysis 定義テンプレ
- `data/system/power.md` — 旧 TOML データ配置
- `verification/scopes/power.md` — 旧 veriq scope 定義テンプレ

→ いずれも対応する v2 ファイルが `実装テンプレート/systems/<name>/` にある。
