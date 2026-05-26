# craft analysis

`@analysis` デコレータで登録された計算・検証関数を管理・実行するコマンド群。
詳しい Analysis の書き方は [Analysis の書き方](../../guide/analysis.md) を参照。

---

## `craft analysis list`

登録済みのすべての analysis 関数を一覧表示する。

```bash
uv run craft analysis list
```

**出力例**

```json
[
  {
    "name": "total_pdm_power_w",
    "subsystem": "power",
    "verify": false,
    "desc": "全 PDM 消費電力合計 (W)"
  },
  {
    "name": "verify_battery_capacity",
    "subsystem": "power",
    "verify": true,
    "desc": "全バッテリが容量要件を満たすか"
  },
  {
    "name": "battery_eol_capacity",
    "subsystem": null,
    "verify": false,
    "desc": "バッテリ EOL 容量推定（ad-hoc）"
  }
]
```

| フィールド | 意味 |
|---|---|
| `verify: false` | `craft verify` の calculation として実行される |
| `verify: true` | `craft verify` の verification（✓/✗）として実行される |
| `subsystem: null` | ad-hoc analysis。`craft analysis run _ <name>` で実行 |

---

## `craft analysis run <subsystem|_> <name>`

指定した analysis を実行する。

```bash
# subsystem に紐づく analysis
uv run craft analysis run power total_pdm_power_w

# ad-hoc analysis（subsystem=None）は _ を指定
uv run craft analysis run _ battery_eol_capacity \
  --payload '{"initial_capacity_wh": 100.0, "years": 3.0}'

# キャッシュをバイパスして再実行
uv run craft analysis run _ battery_eol_capacity \
  --payload '{"initial_capacity_wh": 100.0}' \
  --no-cache
```

**引数・オプション**

| 引数 / オプション | 必須 | 説明 |
|---|---|---|
| `subsystem \| _` | はい | analysis が属する subsystem 名。`subsystem=None` の場合は `_` |
| `name` | はい | analysis 関数名 |
| `--payload <JSON>` | いいえ | ad-hoc analysis への kwargs を JSON で渡す |
| `--no-cache` | いいえ | キャッシュをバイパスして再計算する |

**出力例**

```json
{
  "value": 8.0
}
```

キャッシュヒット時:

```json
{
  "value": 89.075,
  "cache_hit": true
}
```

!!! note "`_` の使いどころ"
    `@analysis(subsystem=None, ...)` で登録された analysis は veriq に依存せず、
    CLI から `--payload` で引数を渡して単体実行できる。
    複数 subsystem をまたがる計算や、設計初期の試算に便利。
