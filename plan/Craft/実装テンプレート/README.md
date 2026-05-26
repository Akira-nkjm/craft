---
tags: [project, dev, satellite, template]
date_updated: 2026-05-22
---

# 実装テンプレート (v2)

> 親: [[Craft]]
> 関連: [[型検証と宣言方式]] / [[構成見直し案]]

**方式 C** (Component を base class、`@component` decorator 廃止) + **subsystem 中心レイアウト** での最終形。

---

## ディレクトリ構造（実コードと 1:1）

```
実装テンプレート/                  ←→  craft/
├── subsystems/                    ←→  subsystems/
│   ├── power/                     ← hardware (Multi-instance 主体)
│   │   ├── components.md          ←→  components.py   (Component 派生)
│   │   ├── analyses.md            ←→  analyses.py     (@analysis 関数)
│   │   ├── scope.md               ←→  scope.py        (vq.Scope 定義)
│   │   └── data.md                ←→  data.toml       (インスタンスデータ)
│   ├── thermal/ ...
│   ├── com/ ...
│   ├── cdh/                       ← hardware default Singleton 例 (OBC)
│   │   └── components.md
│   └── mission/                   ← 非 hardware (Config 例)
│       └── configs.md             ←→  configs.py      (Config 派生)
│
└── _internals/                    ←→  schema/ (基盤、ユーザは触らない)
    ├── Component基底.md            ←→  schema/_component.py
    └── trait一覧.md                ←→  schema/traits.py
```

各 subsystem は以下のファイルを **必要に応じて** 持つ:
- `components.py` — `class X(Component, ...):` の hardware 定義
- `configs.py` — `class X(Config):` の 設定値定義
- `analyses.py` — `@analysis` 関数
- `scope.py` — `vq.Scope` 定義（新 subsystem 時のみ）
- `data.toml` — インスタンスデータ + Config 値

---

## ユーザが触るのは `subsystems/<name>/` だけ

| やりたいこと | 編集するファイル |
|---|---|
| 新 component (hardware) を追加 | `subsystems/<sub>/components.py` |
| 新 config (非 hardware) を追加 | `subsystems/<sub>/configs.py` |
| Singleton hardware (例: OBC、default) | components.py に `class X(Component):`（trait 不要） |
| MultiInstance hardware (例: Battery) | components.py に `class X(Component, MultiInstance, ...):` |
| 既存に field 追加 | 同上 |
| 新 subsystem 追加 | `subsystems/<new>/` を新規作成 |
| 解析関数追加 | `subsystems/<sub>/analyses.py` |
| veriq scope 設定 | `subsystems/<sub>/scope.py`（新 subsystem 時のみ） |
| インスタンスデータ編集 | API/CLI 経由、緊急時は `data.toml` 直接 |

→ **`schema/` (=core/_internals/) は触らない**。

---

## ファイル一覧

### subsystems/

| Subsystem | components | configs | analyses | scope | data |
|---|---|---|---|---|---|
| power | [[実装テンプレート/subsystems/power/components\|components]] | - | [[実装テンプレート/subsystems/power/analyses\|analyses]] | [[実装テンプレート/subsystems/power/scope\|scope]] | [[実装テンプレート/subsystems/power/data\|data]] |
| thermal | [[実装テンプレート/subsystems/thermal/components\|components]] | - | - | - | - |
| com | [[実装テンプレート/subsystems/com/components\|components]] | - | - | - | - |
| cdh | [[実装テンプレート/subsystems/cdh/components\|components]] (OBC: Singleton default) | - | - | - | - |
| mission | - | [[実装テンプレート/subsystems/mission/configs\|configs]] (Config の例) | - | - | - |

### _internals/

ユーザは触らないが、 **挙動を理解するため** に読むファイル群。

- [[実装テンプレート/_internals/Component基底\|Component基底]] — Component base class の中身
- [[実装テンプレート/_internals/trait一覧\|trait一覧]] — 利用可能 trait と各 trait が生やす field

---

## 大原則（再掲）

1. **2 つの基底クラス**: `Component`（hardware）と `Config`（非 hardware 設定）
2. **どちらも decorator なし**、`class X(Component/Config, ...):` の base class 方式
3. **analysis は `@analysis` decorator**（subsystem は自動推論）
4. **field helper は `fld()` 一本**
5. **trait は多重継承**（`MultiInstance`, `PowerConsuming`, `TemperatureSensitive`, `HasPowerMode`, `SpecOnly`）
6. **subsystem は親ディレクトリから自動推論**（明示は `class X(Component, subsystem="..."):`）
7. **`from __future__ import annotations` 禁止**
8. **自由メモは TOML の `meta` テーブル**
9. **Component の default は Singleton**。複数積む場合のみ `MultiInstance` を継承

## 4 つの基本パターン

| パターン | 例 | 書き方 | TOML 構造 |
|---|---|---|---|
| Component (Singleton, **default**) | OBC, BusStructure | `class X(Component, ...):` | `[obc.spec]` |
| Component (MultiInstance) | Battery, SolarPanel | `class X(Component, MultiInstance, ...):` | `[batteries.<name>...]` (or `[batteries.spec]` shared) |
| Config | MissionProfile, OrbitalParameters | `class X(Config):` | `[mission_profile]` |
| Analysis | 解析関数 | `@analysis def f(...) -> T:` | (TOML 無関係) |
