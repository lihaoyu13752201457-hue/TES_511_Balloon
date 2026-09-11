# 日–地 L2 五族连续公开源集合同

## 统一口径

- 位置：日–地 L2 视为约 1 AU 的近地行星际环境；L1/L2 的日心距离差约 2%，安静
  GCR 不另乘轨道因子。
- 能量：横轴一律为单个入射粒子的动能；alpha 使用每个核的总动能，不是 MeV/n。
- 静态各向同性源：表内存 `dF/dE`，已对 `4 pi sr` 积分，单位
  `cm^-2 s^-1 keV^-1`。
- 方向源：软质子保留为 `cm^-2 s^-1 sr^-1 keV^-1`，不乘 4π 后混入安静 GCR。
- 主情景：2009 太阳极小/GCR 最大，`phi = 0.3793 GV`；太阳活动比较为 2014
  太阳极大/GCR 最小，`phi = 0.803 GV`。

## 五类连续曲线

| 家族 | 数值支撑（总动能） | 采用模型 | 物理状态 |
|---|---:|---|---|
| gamma | 3 keV–739 GeV | COSI/Cumani 宇宙 gamma；100 keV 以下接 Tuerler CXB | 4π 静态基线；银河弥散天图另建 |
| p | 5 MeV–10 TeV | Athena/Usoskin 力场谱到 100 GeV；其上连续接 COSI/AMS | 4π；SH3 关键 1.37–48.4 GeV 完全在权威段内 |
| alpha | 10 MeV–10 TeV | Kuznetsov 在 0.32–400 GeV 总动能有效；两端连续接 COSI，2014 用同一力场差分变换 | 4π；总动能/核 |
| e- | 1 MeV–10 TeV | Athena/Grimani Jovian-max 作者图；文中低/高能渐近式 | 4π 保守电子端点；Jovian 包络不是太阳周期时钟 |
| e+ | 1 MeV–10 TeV | COSI/AMS 实测支撑；表外固定 e+/e- 比连续延展 | 4π；表外仅为绘图/覆盖代理，非独立 L2 权威 |

## 采用公式

### GCR proton

Lotti et al. 给出的 Usoskin 1 AU 模型为

```text
J(E,phi) = J_LIS(E+phi) * E(E+2Er) / [(E+phi)(E+phi+2Er)]
J_LIS(E) = 1.9 [E(E+2Er)]^-1.39 /
           {1 + 0.4866 [E(E+2Er)]^-1.255}
```

其中 `E` 和 `Er=0.938` 用 GeV，`J` 为
`cm^-2 s^-1 sr^-1 GeV^-1`。2009 与 2014 只改变 `phi`。100 GeV 以上太阳调制
已很弱，本包按 100 GeV 节点连续接 COSI/AMS 高能形状。

### GCR alpha

```text
F_He(E) = 1.085e5 E^-2.72 [E/(E+2304)]^3.7
```

`E` 是 MeV/alpha nucleus，`F_He` 是
`cm^-2 s^-1 sr^-1 MeV^-1`。2014 曲线从 2009 参考作 `Z=2, A=4` 的相对力场变换；
总能量平移为 `2 * Delta(phi)`。

### Electron

3 GeV 以上采用论文给出的 PAMELA 2009 拟合：

```text
F_e-(E) = 200 E^-3.14  [m^-2 s^-1 sr^-1 GeV^-1]
```

10 MeV–3 GeV 使用论文作者源文件 `GCRspectra.png` 中的 Jovian-max 曲线数字化；
低于图支撑使用文中 `3.56 E^-1.5` 渐近式，并作 m²→cm² 换算。数字化表保存在
`data/athena_jovian_electron_digitized.csv`。

### L2 soft proton

Athena 表 1 的 50–5000 keV 方向强度为：

```text
quiet magnetosheath: 8.6e5 E^-2.94
worst magnetosheath: 7.0e6 E^-3.11
```

`E` 用 keV，强度单位为 `cm^-2 s^-1 sr^-1 keV^-1`。论文同时指出 L2 附近观测只覆盖
两年中的数月，不能把这些式子解释为可靠的完整太阳周期平均；本包因此只交付方向源表，
不纳入中央性能条形图。

## 不能强行接成一条静态谱的成分

- SEP：CREME96/SAPPHIRE 的 worst-week/day/5-minute 是事件情景和停机问题，不是
  quiet-time GCR 的低能延长线；
- Z>2 GCR/HZE：BON2020、CREME96 或 ISO-15390 可提供 Z=1–28/92 离子环境，但保留
  SH3 八族响应没有这些初级粒子，不能凭通量比例制造性能贡献；
- 银河弥散 gamma：Fermi 模型是方向–能量天图，不可压成与各向同性 CXB 等价的 4π 曲线；
- L2 外部 neutron/muon：没有月壤/大气级联母体；航天器内次级中子必须由 p/alpha/HZE
  匹配输运产生，不能再加一条外部中子谱；
- SAA/俘获带：日–地 L2 不穿越地球俘获带。

## SH3 投影解释

当前保留响应中，L2 太阳极小投影有 94.70% 的本底来自五个 delayed 末级事件；其中
四个事件对应同一个 Cu-62 活化键，该键只有一个 1.366 GeV proton RP 记录，L2/气球
源谱比约 225。因此 `(4.88 +/- 1.09)e-5` 是高杠杆、低有效样本数的条件投影。
它说明“L2 对当前 SH3 的质子活化可能很不利”，但不等价于完成了 L2 活化率预测。
Athena 另报告不同太阳周期间 GCR 最大值的样本散布约 26%，这一源模型不确定度未计入
PPT 的条件 MC 误差棒。

## 公开来源

- Lotti et al., *Review of the particle background of the Athena X-IFU instrument*：
  [arXiv:2101.02526](https://arxiv.org/abs/2101.02526)。p、alpha、electron、L1/L2
  soft-proton 公式与太阳极小/极大调制势出自该文。
- Usoskin et al., *Heliospheric modulation of cosmic rays: Monthly reconstruction for
  1951–2004*：[DOI 10.1029/2005JA011250](https://doi.org/10.1029/2005JA011250)。
- Kuznetsov et al., *Empirical model of long-time variations of galactic cosmic ray
  particle fluxes*：[DOI 10.1002/2016JA022920](https://doi.org/10.1002/2016JA022920)。
- Cumani et al., *Background for a gamma-ray satellite on a low-Earth orbit*：
  [DOI 10.1007/s10686-019-09624-0](https://doi.org/10.1007/s10686-019-09624-0)；
  固定实现见 [cositools/cosi-background](https://github.com/cositools/cosi-background)。
- Slaba & Whitman, *The Badhwar–O'Neill 2020 GCR Model*：
  [DOI 10.1029/2020SW002456](https://doi.org/10.1029/2020SW002456)。用于确认深空离子
  环境的完整物种范围；本次没有把其 HZE 数值映射到不存在的 SH3 响应。
- APT L2 gamma 背景模拟公开海报：
  [HEAD 2023 poster](https://www.sudvarg.com/publications/HEAD2023_adapt_background_poster.pdf)。
  其公开做法是 BON 太阳极小 GCR ions、Ulysses/ACE electron/quiet solar proton，及
  Fermi/COMPTEL gamma sky；SEP 独立。
- Fermi LAT 弥散模型说明：
  [Background models](https://fermi.gsfc.nasa.gov/ssc/data/access/lat/BackgroundModels.html)。
- eROSITA L2 软质子实测约束：
  [arXiv:2401.17301](https://arxiv.org/abs/2401.17301)。该结果约束探测器本底，不被本包
  误写成各向同性入射源。

## 权威边界

本合同授权统一口径的 L2 源谱比较和 SH3 响应投影。最终性能仍需 L2 专用 source card、
同一质量模型的 prompt -> activation -> delayed -> response 闭合，以及 SEP/HZE/方向源的
任务级占空比处理。
