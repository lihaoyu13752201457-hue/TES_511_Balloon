---
title: TES_511 — 能带分辨的 prompt/delayed 本底构成（坐实"高能段活化占比"）
date: 2026-06-24
type: read-only follow-up analysis（只读；未改动任何 baseline/Step05 权威）
source_catalog: stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/work/event_catalog.pkl
script: scratchpad band_comp.py / band_comp2.py（逐事件 sum(rate_hz)，veto = bgo_total_keV<50）
data: energy_band_composition.csv
---

# 目的

CLOSURE_DIGEST §4.7 / §7-3 标注的 **"1500–3000 keV delayed ≈ 48.9%"** 此前只在必要性文档出现、无执行级 provenance。本分析直接从 **Step05 事件目录（1,615,224 事件，逐事件 stream / tes_total_keV / bgo_total_keV / rate_hz）** 重算能带构成，给出可复核数字。

# 方法与验证

- 逐事件按 `stream` 分类，在能带内 `sum(rate_hz)`；veto 阶段 = `bgo_total_keV < 50 keV`（与 Step05 权威同阈值）。
- delayed 占比 = delayed / (prompt + delayed)（science=信号，排除在背景外）。
- **验证（W2 510.58–511.42 keV）**：本方法重算 prompt raw = **0.118771**（官方 0.118771，精确）、delayed raw = **0.004635**（官方 0.0046354）、active-veto delayed 占比 = **6.5%**（官方 final 6.57%）。→ 方法可信。
- active-veto 占比是 final 占比的**忠实代理**：W2 处 side_compton_fov 对 prompt/delayed 各约 −10%，占比不变（6.5% ≈ 6.57%）。

# 结果（能带构成）

| 能带 (keV) | prompt cps (av) | delayed cps (av) | **delayed% (raw)** | **delayed% (active-veto)** |
|---|---:|---:|---:|---:|
| 100–300 | 0.206972 | 0.044980 | 6.4% | 17.9% |
| 300–480 | 0.145898 | 0.005923 | 3.1% | 3.9% |
| 480–550 (broad) | 0.073285 | 0.003691 | 2.9% | 4.8% |
| **510.58–511.42 (W2)** | 0.040712 | 0.002833 | 3.8% | **6.5%** |
| 550–800 | 0.076002 | 0.002318 | 2.1% | 3.0% |
| 800–1100 | 0.067180 | 0.001631 | 1.3% | 2.4% |
| 1100–1500 | 0.027829 | 0.007125 | 4.2% | 20.4% |
| **1500–3000** | 0.086876 | 0.047985 | 13.5% | **35.6%** |
| 3000–8000 | 0.040046 | 0.006696 | 3.8% | 14.3% |
| **FULL 50–8000** | 0.738340 | 0.124382 | 5.5% | **14.4%** |

# 结论（含对先前数字的更正）

1. **"1500–3000 keV ≈ 48.9%" 不成立** —— 实测 **35.6%（active-veto）/ 13.5%（raw）**。必要性文档的 48.9% 偏高、无法复现，应以本数替换。
2. **全谱（50–8000 keV）delayed 仅 14.4%（av）/ 5.5%（raw）** —— 即**整条谱都是 prompt 主导（~86–94%）**，并非"宽带活化主导"。
3. **delayed 占比能量依赖**：在 1500–3000 keV 的活化线/连续谱带升到峰值 ~35.6%，但**任何能带都未超过 prompt**。低能 100–300 keV(17.9%) 与 1100–1500 keV(20.4%) 也有局部抬升。
4. **物理解读**：微小 TES 不自活化 + active CsI 屏蔽自 veto → delayed 在**所有能量**只以 ~0.3% 几何耦合到达 TES，故全谱 prompt 主导。这与 COSI（Ge 探测器自活化 → 活化主导）的本质区别一致；不是建模错误，是聚焦+微探测器+主动屏蔽架构的必然。

# 对"和 GPT argue"的影响

- **可放心主张**：W2 prompt 主导是真实且**能扩展到全谱**（全谱 delayed 14.4%）；这反而比"只有窄窗 prompt 主导"更强。
- **必须更正**：不要再用 48.9% 或"宽带活化主导"；正确表述是"**全谱 prompt 主导(~86%)，delayed 在 1500–3000 keV 活化带升至峰值 ~36% 但不主导**"。
- **诚实边界**：本表为 active-veto 阶段（final 还含 side_compton_fov，在 W2 处对占比影响 <0.1pt；高能段 final 占比未独立复算，可能略有差异，但不改"prompt 全谱主导"的定性）。

# 复核

```bash
python3 <scratchpad>/band_comp2.py   # 逐事件重算；W2 与官方精确吻合
```
数据：`engineering/energy_band_composition_20260624/energy_band_composition.csv`
