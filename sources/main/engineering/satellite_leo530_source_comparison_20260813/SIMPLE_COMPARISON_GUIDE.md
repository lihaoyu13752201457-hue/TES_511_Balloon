# 四张图怎么读

这四张图是“源输入环境对比”的简版入口，不是新的探测器本底或灵敏度结果。

## 图 0：prompt 入射粒子源谱

[`simple_00_incident_component_spectra.png`](outputs/simple/figures/simple_00_incident_component_spectra.png)

这是最接近用户给出的文献图式的一张，但物理量已改为真正的入射源强度谱：

- 横轴是每颗粒子的 total kinetic energy，单位 MeV，范围 0.1 MeV--1 TeV；
- 纵轴是各自源支持角域上的平均 `dJ/dE`，单位 `cm^-2 s^-1 sr^-1 MeV^-1`；
- 左图是 530 km 近赤道 LEO proxy，primary/secondary proton、electron 和 positron 分开；
- 右图是 corrected 38 km balloon full-sphere 的八族谱；
- 所有 activation/delay 曲线、SAA 分量和 Galactic diffuse sky map 均略去；
- 不画跨粒子族 `Total`，因为不同入射粒子数谱相加不能替代共同探测器响应后的 count spectrum；
- LEO mono-511 只用 0.511 MeV 竖线和积分强度标注，不赋予任意微分峰高；气球 gamma 则仍是带粗湮灭隆起的 broadband total。

该图的数据表是 [`simple_incident_component_spectra.csv`](outputs/simple/tables/simple_incident_component_spectra.csv)。

## 图 1：先看 gamma

[`simple_01_gamma_source.png`](outputs/simple/figures/simple_01_gamma_source.png)

- 100--300 keV：LEO proxy 是气球的约 `1.17×`；
- 300--450 keV：约 `0.60×`；
- 450--600 keV：约 `0.38×`，但这是宽的 annihilation-region proxy，LEO 一侧包含独立 mono-511，不能当作窄线比值；
- 600--1000 keV：约 `0.32×`；
- 1--10 MeV：约 `0.30×`。

蓝色曲线在 511 keV 附近的隆起由少数原生能量节点描述，只能说明宽带 bump，不能从中抽出气球窄 511 线通量。橙色 LEO mono-511 只标积分通量 `0.028207 cm^-2 s^-1`，没有人为赋予连续谱高度。

## 图 2：再看非 gamma 粒子

[`simple_02_family_band_ratio.png`](outputs/simple/figures/simple_02_family_band_ratio.png)

颜色表示 band-integrated `LEO / balloon`：蓝色小于 1，橙色大于 1，灰白接近 1；这只是入射源通量，不是探测器计数。

- neutron proxy 在所示能带明显低于气球，但它使用上游 10-GV fallback，只能作 diagnostic；
- proton 在 1--10 MeV 为约 `21.5×`，随后在更高能段接近 1；
- positron 在 1--10 MeV 为约 `4.55×`，electron 在所示能带多低于气球；
- alpha 的低能强抑制主要反映近赤道 geomagnetic cutoff 和模型环境差异，不能直接翻译成屏蔽收益；
- COSI DC4 没有 muon 源，图中保持 `NA`，不是零；
- `~` 表示只有 partial/mixed cited validity，SAA 不在这张 normal-science 矩阵里。

## 图 3：最后看结论边界

[`simple_03_readout.png`](outputs/simple/figures/simple_03_readout.png)

目前真正闭合的是源谱、单位和源级环境对照。以下量仍没有由这四张图建立：

- Mass511/S3d 的 prompt detector background；
- activation 与 delayed background；
- 511-window detector count rate；
- sensitivity 和设计排序；
- CPU、磁盘和每个轨道状态需要的统计量。

因此最简短的评估是：normal-orbit 的宽带 gamma 和 neutron 入射环境在多个关键能带看起来更轻，但低能 proton/positron、独立 511 线以及未计入的 SAA/活化使我们还不能说“卫星总本底一定更好”。计算消耗也不能由 flux ratio 推出，应该先对每个组件和代表性轨道状态做小规模 pilot，量出每 primary 的时间、保留事件量和 isotope 输出。

## 复现与验证

```bash
python3 engineering/satellite_leo530_source_comparison_20260813/code/build_simple_comparison_figures.py
python3 engineering/satellite_leo530_source_comparison_20260813/code/validate_simple_comparison_figures.py
```

当前状态：`PASS`，0 errors。源表哈希、prompt 入射组件、五个 gamma band、24 个非 gamma 矩阵单元、8 行 authority/readiness 状态以及 4 组 PNG/PDF 均重新检查。
