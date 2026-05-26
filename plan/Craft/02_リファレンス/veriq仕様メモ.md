---
project: "Craft"
tags: [project, dev, satellite, reference]
date_updated: 2026-05-22
source: https://www.space.t.u-tokyo.ac.jp/veriq/
---

# veriq 公式仕様メモ

> 親: [[Craft]] / 関連: [[API設計]]

公式ドキュメント (https://www.space.t.u-tokyo.ac.jp/veriq/) から抜粋した API / CLI サーフェスのリファレンス。

---

## 概要

東京大学 中須賀・船瀬研由来の Python 検証フレームワーク。

- Pydantic ベースの設計パラメータ管理
- 計算間の依存関係を自動解決
- 要求検証
- TOML 入出力で再現性確保
- 「賢い表計算ソフト」のような位置付け

---

## Core API

```python
import veriq as vq
from pydantic import BaseModel
from typing import Annotated

# プロジェクト + スコープ
project = vq.Project("MySatellite")
power = vq.Scope("Power")
project.add_scope(power)

# 入力モデル定義
@power.root_model()
class PowerModel(BaseModel):
    battery_capacity: float

# 計算（依存関係から順序自動決定）
@power.calculation()
def usable_capacity(
    capacity: Annotated[float, vq.Ref("$.battery_capacity")]
) -> float:
    return capacity * 0.8

# 検証
@power.verification()
def verify_capacity(
    capacity: Annotated[float, vq.Ref("$.battery_capacity")]
) -> bool:
    return capacity >= 100.0
```

### vq.Ref

JSONPath ライクな構文でスコープ内 / 横断参照:
- `vq.Ref("$.battery_capacity")` — 同一スコープ内のフィールド
- クロススコープ参照は別シンタックス（要追加調査）

### vq.Table

enum をキーとする多次元データ構造。本プロジェクトでは:
```python
vq.Table[BatteriesName, BatteryEntry]   # batteries.main / batteries.aux ...
```
として使用。auto-discovery の核心。

---

## CLI 一覧（全 12 サブコマンド）

| Command | 用途 |
|---|---|
| `check` | プロジェクト構造の妥当性検証 |
| `calc` | 計算 + 検証実行（メイン） |
| `schema` | 入力の JSON Schema 生成 |
| `init` | サンプル input TOML 生成 |
| `update` | スキーマ変更に伴う既存 input の更新 |
| `diff` | 2 つの TOML 比較 |
| `edit` | 対話 TUI で input 編集 |
| `trace` | 要求 ↔ 検証 のトレーサビリティ表示 |
| `scopes` | プロジェクトの全スコープ列挙 |
| `list` | 依存グラフのノード列挙 |
| `show` | ノード詳細 |
| `tree` | ノードの依存ツリー表示 |

### Global options
`--verbose / --no-verbose`, `--version`, `--install-completion`, `--show-completion`, `--help`

### 共通フラグ
- **Project/File**: `--project NAME`, `-i/--input PATH`, `-o/--output PATH`, `-p/--path PATH`
- **Output filter**: `--json`, `--kind {model,calc,verification}`, `--scope NAME`, `--leaves`, `--depth N`, `--indent N`
- **Verify/Analysis**: `--verify`, `--invert` (逆依存), `--dry-run`

### 典型コマンド
```bash
# 計算 + 検証
veriq calc my_project.py -i input.toml -o output.toml --verify

# スコープ一覧
veriq scopes -p my_project.py

# 依存グラフ
veriq tree my_project.py:power.battery_capacity --depth 3
veriq list  my_project.py --kind verification --scope power
veriq show  my_project.py:power.verify_capacity --json

# 要求トレーサビリティ
veriq trace my_project.py

# input 編集
veriq edit  my_project.py -i input.toml
```

---

## 本プロジェクトへの示唆

### 1. CLI 機能を API でラップする価値
veriq の `scopes` / `list` / `tree` / `trace` / `show` は **検証メタデータ参照** として API に向く。
→ [[API設計]] §veriq Pass-through API を新設して、これらを HTTP で叩けるようにする。

### 2. `--json` フラグの活用
全コマンドが `--json` で機械可読出力可能 → API ラップは `subprocess` + JSON パースで実装可能。

### 3. `update` の存在
スキーマ変更時の既存 input 更新コマンドがある → [[対処方針]] §A.4 のスキーマ migration と協調できる。

### 4. `edit` (TUI) の存在
公式が **CLI + TUI** で完結する設計思想 → 本プロジェクトの「API + CLI + Swagger」方針と親和性が高い。Web UI を急がない判断を裏付ける。

### 5. `trace` (要求 ↔ 検証 トレーサビリティ)
これは UI / API としても重要な可視化機能。→ [[API設計]] に `GET /api/projects/{pid}/trace` を追加すべき。

---

## 公式 Python API（要確認 → ✅ 確認済み）

ソース `veriq/__init__.py` の `__all__` に **39 個の symbol が公開**。subprocess 不要、直接 import で全機能アクセス可。

### 主要公開関数（signature 抜粋、v0.4.2）

```python
# 評価エンジン（最重要）
evaluate_project(project: Project, model_data: Mapping[str, BaseModel]) -> EvaluationResult
evaluate_graph(...)  # 低レベル版

# TOML I/O
load_model_data_from_toml(project: Project, input_path: Path | str) -> dict[str, BaseModel]
export_to_toml(project, model_data, result: EvaluationResult, output_path: Path | str) -> None

# 依存グラフ / 構造
build_graph_spec(project: Project) -> GraphSpec
DependencyGraph
NodeKind, NodeSpec, PathNode, ScopeTree

# 要求トレーサビリティ
build_traceability_report(project, evaluation_results: EvaluationResult | None) -> TraceabilityReport
RequirementStatus, RequirementTraceEntry, VerificationResult

# コアモデル
Project, Scope, Ref, Table, Requirement
```

### 補助 API
- `assume`, `depends`, `with_range` — 追加メタ情報を関数に貼る decorator
- `StrEnumWithDoc` — ドキュメント付き enum（インスタンス名に説明を持たせられる）
- `ExternalData`, `FileRef` — 大きなデータを外部ファイル参照
- `ChecksumValidationEntry/Result` — 外部データのチェックサム検証
- `TableFieldHandler` — bounded-models 連携

### `Ref` クラス実体（dataclass）
```python
@dataclass(slots=True, frozen=True)
class Ref:
    path: str
    scope: str | None = None
```

→ [[Analysis詳細仕様]] §13 の方針と完全一致。安心して採用可能。

### TOML 入出力の構造（重要、Step 5 ドキュメントより）

veriq の TOML は **3 段の top-level 階層** を持つ:

```
[<ScopeName>.model.<root_model_field>...]         ← 入力（root_model の field 値）
[<ScopeName>.calc.<calc_func_name>.<...>]         ← 出力（@calculation 関数の戻り値）
[<ScopeName>.verification.<verify_func_name>]    ← 出力（@verification 関数の戻り値）
```

具体例（Step 5 チュートリアル抜粋）:

```toml
[Power.model]
battery_capacity = 100.0                # scalar field は [.model] 直下

[Power.model.power_consumption]         # table field は [.model.<field>] 配下
nominal = 50.0
safe = 20.0
mission = 80.0

[Power.calc.calculate_power_margin]     # 計算出力
margin = 10.0
```

#### 多次元テーブル

複数キー（`vq.Table[K1, K2, V]`）はカンマ区切り文字列キー:

```toml
[Scope.model.values]
"a,x" = 100.0
"a,y" = 200.0
```

#### 本プロジェクトでの適用

- `scope = vq.Scope("power")` の TOML 入力 → `[power.model.<field>...]`
- subsystem 名 = scope 名 を **小文字統一** することを推奨
- `<root_model_field>` は registry から auto-derive される（[[最終構成]] §2 Subsystem Model）
- 詳細は [[データパイプライン]] §2 を参照

### 本プロジェクトでの使い方

```python
import veriq as vq
from pathlib import Path

# 1. プロジェクト import（既存 verification/project.py）
from craft.verification.project import project

# 2. TOML 入力ロード
model_data = vq.load_model_data_from_toml(project, "design/data/input.toml")

# 3. 評価（calc + verify）
result = vq.evaluate_project(project, model_data)

# 4. 結果取得
print(result.values)       # 計算値
print(result.validity)     # 各ノードの妥当性
print(result.errors)       # エラー一覧

# 5. 結果を TOML 出力
vq.export_to_toml(project, model_data, result, "out.toml")

# 6. トレーサビリティ
trace = vq.build_traceability_report(project, result)
```

→ **API ラッパは subprocess 経由を完全に回避**できる。Phase 1a/1b 区別不要。直接 API でいける。

---

## 残る未確認項目

- `vq.Table` の dict 風 API（`.values()`, `.items()`, `[key]` の動作）— 実コードで動いてるので OK のはず
- `@scope.calculation` / `@scope.verification` の追加フラグ（cache 等）
- 循環参照の検出（`build_traceability_report` は循環検出するが calc 側は?）
- エラー型一覧（`EvaluationResult.errors` の構造）

→ 実装着手時に実機で確認。

---

## Sources

- [veriq Documentation home](https://www.space.t.u-tokyo.ac.jp/veriq/)
- [veriq on PyPI](https://pypi.org/project/veriq)
