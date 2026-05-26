---
project: "Craft"
tags: [project, dev, satellite, architecture, registry]
date_updated: 2026-05-22
---

# UnifiedRegistry 詳細設計

> 親: [[最終構成]] / 関連: [[コンポーネントデコレータ仕様]] / [[Analysis詳細仕様]]

decorator が登録し、consumer (API / CLI / MCP / gen_stubs / doc) が introspect する **中央契約**。
ここを確定させると、後続の consumer 設計はすべて「registry を叩くだけ」になる。

---

## 1. 役割

| 役割 | 内容 |
|---|---|
| **登録口** | Component / Config base class の `__init_subclass__` と `@analysis` decorator の唯一の登録先 |
| **検索口** | 「power の battery」「全 analysis」「特定 system の全て」を高速検索 |
| **introspection 口** | JSON Schema 配信、stub 生成、doc 生成、MCP tool 一覧の元データ |
| **ライフサイクル管理** | クリア、スナップショット、リストア（主にテスト用） |

---

## 2. データ型（定義物の構造）

### 2.1 `ComponentDefinition`

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True, slots=True)
class ComponentDefinition:
    # 識別
    system: str                              # "power"
    name: str                                   # "battery"
    plural: str                                 # "batteries"

    # 生成された Pydantic モデル
    spec: type[BaseModel]                       # BatterySpec
    design: type[BaseModel]                     # BatteryDesign
    requirements: type[BaseModel] | None        # BatteryRequirements or None
    entry: type[ComponentEntry]                 # BatteryEntry

    # メタ
    options: ComponentOptions                   # mixin, has_power_mode, base
    desc: str | None
    tags: tuple[str, ...]
    source: SourceLocation                      # file:line for debugging
```

### 2.2 `AnalysisDefinition`

```python
@dataclass(frozen=True, slots=True)
class AnalysisDefinition:
    name: str                                   # "battery_eol_capacity"
    system: str | None                       # None = ad-hoc, str = veriq scope に登録

    func: Callable                              # 関数本体
    input_model: type[BaseModel]                # 関数 signature から自動生成
    output_type: type                           # 戻り値型

    # フラグ
    verify: bool                                # veriq の verification として登録
    cache: bool
    async_only: bool
    imports: tuple[str, ...]                    # veriq cross-scope imports

    # メタ
    desc: str | None
    tags: tuple[str, ...]
    code_version: str                           # cache key 用、source hash デフォルト
    source: SourceLocation
```

### 2.3 `ComponentOptions`

```python
@dataclass(frozen=True, slots=True)
class ComponentOptions:
    base: Literal["spec", "power_spec"] = "spec"
    mixin: Literal["temperature"] | None = None
    has_power_mode: bool = False
    plural_override: str | None = None
```

### 2.4 `SourceLocation`

```python
@dataclass(frozen=True, slots=True)
class SourceLocation:
    file: str           # "/abs/path/to/schema/systems/power.py"
    line: int
    module: str         # "craft.schema.systems.power"
```

→ デバッグ・エラーメッセージ・doc 生成で「定義箇所」を示すため必須。

---

## 3. `UnifiedRegistry` クラス API

```python
class UnifiedRegistry:
    """全 decorator の唯一の登録先 / consumer の唯一の introspection 口。"""

    # ───── 登録 ─────
    def register_component(self, defn: ComponentDefinition) -> None: ...
    def register_analysis(self, defn: AnalysisDefinition) -> None: ...

    # ───── 取得（単一）─────
    def component(self, system: str, name: str) -> ComponentDefinition: ...
    def analysis(self, system: str | None, name: str) -> AnalysisDefinition: ...

    def component_or_none(self, system: str, name: str) -> ComponentDefinition | None: ...
    def analysis_or_none(self, system: str | None, name: str) -> AnalysisDefinition | None: ...

    # ───── 取得（複数）─────
    def components(self, *, system: str | None = None) -> list[ComponentDefinition]: ...
    def analyses(self, *, system: str | None = None, verify: bool | None = None) -> list[AnalysisDefinition]: ...

    # ───── メタ照会 ─────
    def systems(self) -> set[str]:
        """登録されている全 system 名（component / analysis の和集合）"""

    def has_component(self, system: str, name: str) -> bool: ...
    def has_analysis(self, system: str | None, name: str) -> bool: ...

    # ───── ライフサイクル（テスト用）─────
    def clear(self) -> None: ...
    def snapshot(self) -> RegistrySnapshot: ...
    def restore(self, snapshot: RegistrySnapshot) -> None: ...

    # ───── プロパティ ─────
    @property
    def frozen(self) -> bool:
        """True なら新規登録を拒否（auto-discovery 後に固める用途）"""

    def freeze(self) -> None: ...
    def unfreeze(self) -> None: ...
```

### 3.1 例外

```python
class RegistryError(Exception): ...
class DuplicateRegistration(RegistryError): ...
class NotRegistered(RegistryError): ...
class RegistryFrozen(RegistryError): ...
```

- `register_component` で重複 → `DuplicateRegistration`
- `component()` で未登録 → `NotRegistered`（`_or_none` 版は None を返す）
- `freeze()` 後の登録 → `RegistryFrozen`

### 3.2 thread safety

- 登録 (`register_*`, `clear`, `restore`) は **書き込みロック**
- 取得 (`component`, `components`, ...) はロックなし（dict は GIL で atomic、frozen dataclass は immutable）
- 通常運用では auto-discovery 後 `freeze()` するので、書き込みは起動時のみ

---

## 4. グローバルインスタンスと依存注入

```python
# experiment/registry.py
default_registry: UnifiedRegistry = UnifiedRegistry()
```

### 4.1 通常コード
```python
from craft.registry import default_registry as registry

defn = registry.component("power", "battery")
```

### 4.2 テスト
```python
@pytest.fixture
def fresh_registry(monkeypatch):
    new = UnifiedRegistry()
    monkeypatch.setattr("craft.registry.default_registry", new)
    return new

def test_my_thing(fresh_registry):
    class Foo(Component, system="test"): ...
    assert fresh_registry.has_component("test", "foo")
```

→ `monkeypatch` で差し替えるパターン。`Component.__init_subclass__` 内で `from craft.registry import default_registry` するため有効。

### 4.3 別案: base class が registry 引数を取る

```python
class Battery(Component, system="power", registry=my_registry): ...
```

→ テスト用途以外で使わない。**default は default_registry**、明示時のみ override。

---

## 5. introspection API（consumer 用）

registry に **「外側から叩く」高レベルメソッド** を持たせるべきか論点。
→ ✅ **持たせない**。registry は **データ提供だけ**、変換は別モジュール。

| 機能 | 場所 |
|---|---|
| JSON Schema 配信 | `api/routers/schema.py` が `registry.components()` を叩いて構築 |
| .pyi stub 生成 | `schema/_stubgen.py` が `registry.components()` を走査 |
| OpenAPI routes 生成 | `api/main.py` が起動時に走査 |
| MCP tool 一覧生成 | `mcp_server/tools.py` が走査 |
| markdown doc 生成 | `docs/_gen.py` が走査 |

→ registry は **「素朴な dict + 検索」** に留める。変換ロジックは膨らむので外出し。

---

## 6. auto-discovery との連携

```python
# experiment/schema/systems/__init__.py
import pkgutil
import importlib

for info in pkgutil.iter_modules(__path__):
    if not info.name.startswith("_"):
        importlib.import_module(f"{__name__}.{info.name}")
```

import の **副作用** で `Component.__init_subclass__` / `Config.__init_subclass__` / `@analysis` decorator が `default_registry.register_*()` を呼ぶ。

### 6.1 起動時の流れ

```
app start
  ↓
import craft.systems            # systems/<name>/{components,configs,analyses}.py を一括 import
  ↓
  - class X(Component, ...): が全部発火（__init_subclass__ → register_component）
  - class X(Config): が全部発火          （__init_subclass__ → register_config）
  - @analysis def f(...): が全部発火     （decorator → register_analysis）
  ↓
default_registry.freeze()                 # 以降の登録を禁止
  ↓
api/cli/mcp consumers が registry を introspect
```

### 6.2 注意

- `freeze()` は **production / serve モード** で実行。テストでは frozen=False のまま
- system 跨ぎ参照（例: `@analysis` の引数型に他 system の Spec を使う）が **import 順序** に依存しないよう、 **遅延参照** を許容
  - `Annotated[BatterySpec, ...]` の `BatterySpec` は `from craft.schema.systems.power import BatterySpec` で OK（その前に import されている）
  - 完全な遅延が必要なら文字列アノテーション ... ❌ veriq が嫌うので使えない
  - → **systems 配下は import 順序を `__init__.py` で固定**するのが安全（alphabetical で十分なはず）

---

## 7. 登録物の同一性（重複検出）

### 7.1 component の重複

`(system, name)` がキー。重複 = `DuplicateRegistration`。

ただし **同じ system 内で同名 component を上書きしたいケース**（テストで monkey patch 等）は明示的 API で:
```python
registry.unregister_component("power", "battery")
registry.register_component(new_defn)
```

### 7.2 analysis の重複

`(system, name)` がキー。`system=None` の場合は `(None, name)`。
ad-hoc 同名は禁止（typo 防止）。

### 7.3 plural の重複

`(system, plural)` も unique でないと TOML 構造が壊れる:
```toml
[batteries.main]   # ← この "batteries" が複数 component から指されると死ぬ
```
→ registry が登録時に検出してエラー。

---

## 8. RegistrySnapshot（テスト・移行用）

```python
@dataclass(frozen=True)
class RegistrySnapshot:
    components: tuple[ComponentDefinition, ...]
    analyses: tuple[AnalysisDefinition, ...]
    frozen: bool

# 使い方
snap = registry.snapshot()
... # 試験的に色々登録
registry.restore(snap)   # 元に戻す
```

→ pytest fixture や開発時の「ちょっと試す」用途。

---

## 9. 並行プロセスとの関係

`default_registry` は **プロセスローカル**。FastAPI worker が複数プロセスなら各プロセスが独自の registry を持つ。
これは **問題にならない**:
- 全プロセスが同じ system ファイルを import → 同じ登録物になる
- registry は read-only（freeze 後）なので不整合が起きる余地が無い

将来 hot reload で system を動的追加したくなったら → 別途設計（Phase 3 以降）。

---

## 10. 実装サイズ感

- `_registry.py` — 200〜300 行
- `_definitions.py`（dataclass 群） — 100 行
- `_exceptions.py` — 30 行

→ 比較的軽量。実装難度は低い。

---

## 11. 確定事項

| 項目 | 決定 |
|---|---|
| クラス名 | `UnifiedRegistry` |
| インスタンス | グローバル `default_registry`、テストは monkeypatch |
| 登録粒度 | component / analysis の 2 種 |
| キー | `(system, name)` (component) / `(system or None, name)` (analysis) |
| 重複検出 | 必須（typo 防止） |
| plural 衝突検出 | 必須 |
| Thread safety | freeze 後は読み取りのみで安全 |
| introspection 変換 | registry にロジック持たせず、外部モジュールが叩く |
| 例外設計 | 専用 `RegistryError` 階層 |

---

## 12. 残る論点

- **`unregister_*` API を公開するか** — テスト以外で需要があるか
- **登録順序の保持** — `components()` の戻り値順序は登録順? アルファベット?（→ **登録順** に決め打ち、整列は consumer 側）
- **`freeze()` の解除** — production で `unfreeze` を呼ぶシナリオはほぼ無い、テストのみ
- **複数 registry 同時運用** — マルチプロジェクト時のために `Project(registry=...)` で渡せる構造に
