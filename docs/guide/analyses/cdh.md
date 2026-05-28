# cdh（C&DH / オンボード計算機）

オンボード記録容量・書換寿命・データスループット・CPU 負荷。

---

## 1. `daily_data_generation_mb` [B]

**式:**

$$V_{day} = \sum_i R_{i,\text{bps}} \cdot t_{i,\text{on,s}} / 8 / 10^6 \cdot \text{[Mbytes]}$$

**入力:** ミッションデータレート, 観測時間, HK レート, 各モード duty
**出力:** $V_{day}$ [MB/day]

---

## 2. `required_flash_capacity_gb` [S]

**式:**

$$C_{flash} = (V_{mission} + V_{HK} + V_{log}) \cdot k_{margin}$$

**入力:** 各データ種累積、マージン係数（既定 1.5）
**出力:** $C_{flash}$ [GB]

---

## 3. `flash_write_cycles` [B]

**式:** $N_{cycles} = V_{written,total} / C_{flash}$

**出力:** [—]

---

## 4. `flash_endurance_ok` [V]

**閾値:**（典型 NAND）$N_{cycles} \leq 10^4$～$10^5$

**入力:** 書込累積、容量、耐久仕様
**出力:** bool

---

## 5. `storage_fill_at_max_outage_mb` [V]

**用途:** 最大無コンタクト期間中の蓄積データ量。

**式:** $V_{stored} = V_{gen,day} \cdot N_{no-contact-days}$

**入力:** 1 日生成量、最大無コンタクト日数
**出力:** $V_{stored}$ [MB] / overflow 判定 bool

---

## 6. `data_throughput_ok` [V]

**式:** $V_{cap,downlink} \geq V_{gen}$

**入力:** [comm](comm.md).daily_downlink_capacity, 1 日生成量
**出力:** bool

---

## 7. `cpu_utilization_per_mode` [V]

**用途:** タスクスケジューラ余裕。

**式:**

$$U = \sum_i \frac{C_i}{T_i} \leq U_{max}$$

ここで $C_i$ は WCET、$T_i$ は周期。**閾値 $U_{max} \approx 0.7$–0.8**（RM スケジューリング上限）。

**入力:** タスク周期と WCET
**出力:** $U$ [—] / bool

---

## 8. `bus_utilization` [V]

**式:** $U_{bus} = \sum (\text{packet rate} \times \text{packet size}) / B_{bus}$

**入力:** バス帯域、各タスクのトラフィック
**出力:** バス占有率 [—] — **典型 ≤ 60%**

---

## 9. `command_response_latency_ms` [V]

**用途:** 緊急コマンドのレスポンス時間。

**式:** $t_{latency} = t_{queue} + t_{exec}$、tasks のスケジューリング解析から算出。

**出力:** [ms] — 要求値と比較。

---

## 10. `software_memory_footprint_kb` [B]

**式:** $M_{SW} = \sum_i (\text{RAM}_i + \text{ROM}_i)$（FSW モジュール総和）

**出力:** RAM/ROM 使用量 [kB] — MCU 仕様と比較。

---

## 依存関係

```
sensors + duty ── daily_data_generation ──┬── required_flash_capacity
                                          ├── flash_write_cycles ── endurance_ok
                                          └── storage_fill ── data_throughput_ok ←── comm.daily_downlink

tasks ── cpu_utilization ── verify
      └── command_response_latency
```
