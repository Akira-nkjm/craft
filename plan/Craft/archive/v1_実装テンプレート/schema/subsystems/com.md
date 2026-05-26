---
tags: [project, dev, satellite, template, code]
mirror: schema/subsystems/com.py
---

# schema/subsystems/com.py

> 親: [[実装テンプレート/README|実装テンプレート]]

通信サブシステム。**`plural` 上書き** が必要なケース（不規則複数形）の例。

---

## ファイル全体

```python
"""Communication subsystem components."""

from craft.schema import component, fld


@component(subsystem="com", base="power_spec", mixin="temperature")
class Transceiver:
    """通信機（送受信統合）。"""

    frequency_band: str = fld(desc="周波数帯（S/X/Ka 等）")
    max_tx_power_w: float = fld(ge=0, unit="W", desc="最大送信出力")
    max_data_rate_kbps: float = fld(ge=0, unit="kbps")

    class Design:
        operating_mode: str = fld(default="normal", desc="運用モード識別子")


@component(subsystem="com", plural="sband_antennas")    # ← 自動複数形化が変な単語
class SbandAntenna:
    """S 帯アンテナ。"""

    gain_dbi: float = fld(unit="dBi")
    beamwidth_deg: float = fld(ge=0, le=360, unit="deg")

    class Design:
        pointing_loss_db: float = fld(ge=0, default=1.0, unit="dB")
```

---

## 解説

### `plural=` の必要性

デフォルトの複数形化ルールは英語の単純な s 付加（`battery → batteries`、`heater → heaters`）。
不規則な英単語や略語が混じると意図せぬ TOML キーになる:

| クラス名 | デフォルト推定 | 妥当な指定 |
|---|---|---|
| `Battery` | `batteries` | ✅（指定不要）|
| `SolarPanel` | `solar_panels` | ✅ |
| `SbandAntenna` | `sband_antennas`? `sbandantennas`? | ⚠️ 明示推奨 → `plural="sband_antennas"` |
| `HDRM` | `hdrms` | ⚠️ `plural="hdrms"` を明示すると安全 |

→ **悩んだら明示する**のが安全。registry が衝突検出するので絶対に違反は起きない。

### `base="power_spec"`

Transceiver は電力を食う → `BasePowerSpec` 由来の `default_power_consumption_per_unit_w` を持つ。
`has_power_mode=True` を併用すれば「モード別の消費電力」も書ける（今回の例では未使用）。

---

## TOML の見え方

```toml
[transceivers.main]
[transceivers.main.spec]
frequency_band = "S"
max_tx_power_w = 5
max_data_rate_kbps = 256
default_power_consumption_per_unit_w = 8

[sband_antennas.lga1]                  # ← plural="sband_antennas" の効果
[sband_antennas.lga1.spec]
gain_dbi = 2.0
beamwidth_deg = 120
```
