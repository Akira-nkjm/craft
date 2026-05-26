# craft schema

Registry に登録された subsystem・component のメタ情報を確認するコマンド群。

---

## `craft schema list`

登録済みのすべての subsystem とそれに属する component を JSON 形式で出力する。

```bash
uv run craft schema list
```

**出力例**

```json
{
  "power": [
    {"name": "battery", "plural": "batteries", "cardinality": "multi", "traits": ["MultiInstance", "TemperatureSensitive"]},
    {"name": "solar_panel", "plural": "solar_panels", "cardinality": "multi", "traits": ["MultiInstance"]}
  ],
  "cdh": [
    {"name": "obc", "plural": "obcs", "cardinality": "single", "traits": []}
  ]
}
```

!!! tip
    新しい Component を `components.py` に追加した後、このコマンドで registry への登録を確認する。
    `cardinality: "multi"` なら `MultiInstance`、`"single"` なら Singleton。

---

## `craft schema show <subsystem> <component>`

指定した component の Entry モデルに対応する JSON Schema を出力する。
Swagger UI での表示内容と同一で、フィールド型・バリデーション・`unit` 等のメタ情報が確認できる。

```bash
uv run craft schema show power battery
```

**引数**

| 引数 | 必須 | 説明 |
|---|---|---|
| `subsystem` | はい | 対象の subsystem 名 |
| `component` | はい | 対象の component 名（小文字） |

**出力例**

```json
{
  "$defs": {
    "BatterySpec": {
      "properties": {
        "capacity_wh": {
          "title": "Capacity Wh",
          "type": "number",
          "x-unit": "Wh"
        },
        "nominal_voltage_v": {
          "default": 0.0,
          "title": "Nominal Voltage V",
          "type": "number"
        }
      },
      "required": ["capacity_wh"],
      "title": "BatterySpec",
      "type": "object"
    },
    "BatteryDesign": { "..." : "..." },
    "BatteryRequirements": { "..." : "..." }
  },
  "title": "BatteryEntry",
  "type": "object"
}
```

!!! note "Entry モデルの構造"
    JSON Schema は `Entry` モデル全体のスキーマ。
    `spec` / `design` / `requirements` / `meta` の各セクションが `$defs` に展開される。
    `SpecOnly` trait を持つ component は `design` セクションを持たない。
