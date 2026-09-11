# SH3 日–地 L2 五族连续源集与太阳活动投影

## 结论

在统一使用“单个初级粒子总动能”和“声明角域积分的微分通量”后，日–地 L2 的
安静期连续源集已覆盖当前 SH3 八族响应中可外部定义的五类：`gamma / p / alpha /
e- / e+`。外部中子和大气 muon 在 L2 设为物理缺失；磁鞘软质子、SEP、重离子和
方向性银河弥散 gamma 单列，不伪装成静态 4π 曲线。

使用保留的 SH3_OPTV3_60cm 响应做源谱重加权，得到：

- 2009 太阳极小、GCR 最大，`phi = 0.3793 GV`：20 天 3 sigma
  `Fmin = (4.88 +/- 1.09)e-5 ph cm^-2 s^-1`，为当前 SH3 气球值的 `2.19x`；
- 2014 太阳极大、GCR 最小，`phi = 0.803 GV`：
  `Fmin = (3.45 +/- 0.72)e-5 ph cm^-2 s^-1`，为气球值的 `1.55x`；
- 太阳极大/极小的 quiet-GCR 本底比为 `0.499`，Fmin 比为 `0.706`。

这里的误差只表示有限 SH3 响应样本的条件统计。L2 太阳极小值由质子活化主导：
delayed 占 `99.75%`，质子占 delayed 的 `98.11%`，前五个末级事件占 `94.70%`。
因此数字可用于筛选方向和更新本 PPT，不能替代 L2 匹配的 prompt -> activation ->
delayed 输运。

## 旧 L2 曲线为什么没有画满

旧包直接沿用固定 COSI 表的离散支撑：p/alpha 为 10 MeV–10 TeV，e+/- 为
658 MeV–351 GeV，gamma 为 0.1 MeV–739 GeV。图外空白代表“表没有数据”，不是零通量。
本包改用公开 L2 任务分析的解析式或作者图，并只在有物理依据的地方连续延展：

- p：Athena/Usoskin 1 AU 力场模型，100 GeV 以上连续接 COSI/AMS；
- alpha：Athena/Kuznetsov，能量严格按每个 alpha 核的总动能；
- e-：Athena/Grimani Jovian-max 作者图，加文中低/高能渐近式；
- e+：AMS 表内为实测，表外以固定 e+/e- 比补齐，仅作覆盖代理；
- gamma：COSI 宇宙 gamma，低能用 Tuerler CXB 延至 3 keV。

完整的五族口径、公式、有效域与文献见 [L2_COMPLETE_SOURCE_CONTRACT.md](L2_COMPLETE_SOURCE_CONTRACT.md)。

## 产物

- `outputs/tables/l2_source_spectra.csv`：2009 太阳极小五类 4π 源谱；
- `outputs/tables/l2_solar_max_source_spectra.csv`：2014 太阳极大五类 4π 源谱；
- `outputs/tables/l2_directional_soft_proton_spectra.csv`：50–5000 keV L2 方向性软质子；
- `outputs/tables/sh3_prompt_delayed_response_weighted_primary_energy_bands.csv`：prompt/delayed 分开的加权 10–90% 初级能区；
- `outputs/tables/l2_solar_activity_performance.csv`：两个太阳活动端点的 SH3 投影；
- `outputs/summary.json`：结果、来源合同、权威边界和警告；
- `outputs/figures/02_full_spectrum_comparison_sh3_l2.png`：四环境连续谱；
- `outputs/figures/04_l2_solar_activity_sh3.png`：太阳调制与性能端点。

主分析使用已有语义检查点，不重新扫描原始 SIM，也不做无意义的哈希校验：

```bash
python3 code/build_complete_l2_solar.py
```

## 权威边界

本包授权“公开源谱 + 保留 SH3 响应”的条件投影，不授权 L2 最终物理率。仍缺少：
L2 专用 4π 源卡、匹配的 prompt/活化/延迟输运、Z>2 重离子、SEP 时间史、磁鞘软质子
方向响应、任务姿态/停机占空比和 L2 偶然符合闭合。
