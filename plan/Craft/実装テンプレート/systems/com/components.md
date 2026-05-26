---
tags: [project, dev, satellite, template, code]
mirror: systems/com/components.py
---

# systems/com/components.py

> 親: [[実装テンプレート/README|実装テンプレート]]

通信サブシステム。**`plural` キーワード引数** で TOML テーブル名を明示する例。

---

## ファイル全体

```python
"""Communication system components."""

from craft.schema import Component, MultiInstance, fld
from craft.schema.traits import PowerConsuming, TemperatureSensitive


class Transceiver(Component, MultiInstance, PowerConsuming, TemperatureSensitive):
    """通信機（送受信統合）。主/副冗長で複数積むため MultiInstance。"""

    frequency_band: str = fld(desc="周波数帯（S/X/Ka 等）")
    max_tx_power_w: float = fld(ge=0, unit="W")
    max_data_rate_kbps: float = fld(ge=0, unit="kbps")

    class Design:
        operating_mode: str = fld(default="normal")


class SbandAntenna(Component, MultiInstance, plural="sband_antennas"):
    """S 帯アンテナ。LGA / HGA 複数指向で MultiInstance、plural を明示。"""

    gain_dbi: float = fld(unit="dBi")
    beamwidth_deg: float = fld(ge=0, le=360, unit="deg")

    class Design:
        pointing_loss_db: float = fld(ge=0, default=1.0, unit="dB")
```

---

## 解説

### `plural=` キーワード引数

PEP 487 の `__init_subclass__` キーワード引数として渡す:

```python
class SbandAntenna(Component, MultiInstance, plural="sband_antennas"):
    ...
```

→ TOML では `[sband_antennas.lga1]` のように使われる。

### 自動推論ルール

| クラス名 | デフォルト推論 | 妥当か | 推奨 |
|---|---|---|---|
| `Battery` | `batteries` | ✅ | 自動 |
| `SolarPanel` | `solar_panels` | ✅ | 自動 |
| `Transceiver` | `transceivers` | ✅ | 自動 |
| `SbandAntenna` | `sbandantennas`? `sband_antennas`? | ⚠️ あいまい | **明示** |
| `HDRM` | `hdrms` | ⚠️ 略語 | **明示** |
| `MIF` | `mifs` | ⚠️ 略語 | **明示** |

→ 略語・複合語・あいまいなものは **明示**。registry が衝突検出するので、 違反は絶対起きない。

### system も明示できる

`plural` と同様に system も `__init_subclass__` キーワード引数で:

```python
class Transceiver(
    Component,
    PowerConsuming,
    system="com",     # 通常は自動推論されるが明示も可
    plural="transceivers",
):
    ...
```

→ 普段は不要、特殊ケースのみ。

---

## TOML の見え方

```toml
[transceivers.main]
[transceivers.main.spec]
frequency_band = "S"
max_tx_power_w = 5
max_data_rate_kbps = 256
default_power_consumption_per_unit_w = 8
operating_temperature_min_c = -30
operating_temperature_max_c = 60

[sband_antennas.lga1]                  # ← plural="sband_antennas" の効果
[sband_antennas.lga1.spec]
gain_dbi = 2.0
beamwidth_deg = 120

[sband_antennas.lga1.design]
pointing_loss_db = 1.0
```
