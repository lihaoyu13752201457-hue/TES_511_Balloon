# 530 km 近赤道 LEO 卫星源谱与 38 km 气球源谱对比

状态：`PASS__SOURCE_INPUT_COMPARISON__NOT_TRANSPORT_AUTHORITY`

这个目录是一个不覆盖旧结果的新包。它把未来 511-CAM 卫星版暂时落到一个可复现的代理基线：COSI DC4 的 530 km、0° 近赤道 LEO 背景源库；然后与本项目已经修复单位错误的 38 km、八族、20 等 μ 角箱气球源比较。

这里比较的是入射源，不是探测器计数、本底率、活化、延迟本底、灵敏度或 Mass511/S3d 的优选结论。

## 本次固定的两套环境

卫星代理：

- COSI DC4 background source library，固定提交 `eec0dbf1aaabc79fea2706946434e30f7060a59a`；
- 530 km、名义倾角 0°、参考平均 cutoff rigidity 12.6 GV、solar modulation 520 MV；
- normal-science 静态源谱，排除 SAA proton、Galactic diffuse sky map 和轨道时间权重；
- atmospheric 511 keV 是独立 mono 分量。

气球基线：

- `engineering/particle_source_unit_repair_20260811/`；
- 34°N、100°E、38 km、11.6 GV、`W=118.3`、2025-08-31；
- 8 个粒子族、20 个等 μ 全空间角箱；
- source contract SHA-256 为 `5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326`，静态验证 `PASS`，160 个 corrected-keV 谱、0 个 legacy 引用。

## 一个很重要的“×1000”区别

COSI DC4 里也出现了 1000，但它与我们之前的错误性质完全不同：

- 我们之前的问题是意外把能量轴缩小 1000 倍，属于物理输入错误；
- COSI DC4 是有意把 normal-background 通量分到 1000 个并行 simulation shard。固定快照里的 `run_parallel_flux_sims.py` 明确建立 1000 份模拟并要求按并行数缩放源通量。

所以本包同时保留：

- 原 `.source` 卡中的单 shard `simulation_flux_cm2_s`；
- 乘回 1000 后用于物理比较的 `physical_flux_cm2_s`。

图、band 积分和环境对比均使用恢复后的物理通量。SAA 是独立例外，本次不乘 1000，也不并入 normal-science prompt。

## 简版四图入口

如果只想快速判断，不需要先看原来的六面板审计图，优先看第 0 张入射谱总览，再按需要看后三张：

0. [`simple_00_incident_component_spectra.png`](outputs/simple/figures/simple_00_incident_component_spectra.png)：按用户给出的文献图式画 prompt 入射源谱；LEO primary/secondary 分开，气球保留八族，所有 activation/delayed 分量均略去；
1. [`simple_01_gamma_source.png`](outputs/simple/figures/simple_01_gamma_source.png)：gamma 连续谱、511 keV 附近原生节点和五个宽能带积分；
2. [`simple_02_family_band_ratio.png`](outputs/simple/figures/simple_02_family_band_ratio.png)：非 gamma 粒子族的 `LEO / balloon` 离散比值；`NA` 没有被补成零；
3. [`simple_03_readout.png`](outputs/simple/figures/simple_03_readout.png)：哪些问题已经由源输入支持，哪些仍需 matched transport 或资源 pilot。

四图的中文判读见 [`SIMPLE_COMPARISON_GUIDE.md`](SIMPLE_COMPARISON_GUIDE.md)，图表合同见 [`SIMPLE_CHART_CONTRACT.md`](SIMPLE_CHART_CONTRACT.md)，独立验证见 [`SIMPLE_FIGURES_VALIDATION.md`](SIMPLE_FIGURES_VALIDATION.md)。当前简版验证为 `PASS`：0 errors、4 个明确保留的边界 warnings。

## 主要结果

卫星代理恢复后的主要角域积分通量为：

| 分量 | 物理通量 [cm⁻² s⁻¹] |
|---|---:|
| cosmic photons | 1.223509 |
| albedo photon continuum | 0.756819 |
| atmospheric mono-511 | 0.028207 |
| primary proton | 0.091132 |
| secondary proton | 0.046914 |
| primary alpha | 0.017755 |
| primary electron | 0.000642 |
| secondary electron | 0.064602 |
| primary positron | 0.0000416 |
| secondary positron | 0.213187 |
| albedo neutron 10-GV proxy | 0.039068 |

几个比较值可帮助建立直觉，但都只能解释为“两个完整环境模型的差异”，不能只归因于高度：

| 粒子/能带 | 气球 full [cm⁻² s⁻¹] | LEO proxy [cm⁻² s⁻¹] | LEO/balloon | 口径 |
|---|---:|---:|---:|---|
| gamma 100–300 keV | 1.18768 | 1.39245 | 1.172 | continuum，B 级环境对照 |
| gamma 300–450 keV | 0.259984 | 0.156732 | 0.603 | continuum，B 级环境对照 |
| gamma 450–600 keV | 0.271022 | 0.102302 | 0.377 | LEO continuum + mono-511；只作 annihilation-region proxy |
| gamma 600–1000 keV | 0.284936 | 0.091112 | 0.320 | continuum，B 级环境对照 |
| gamma 1–10 MeV | 0.659111 | 0.197861 | 0.300 | continuum，B 级环境对照 |
| proton 1–10 MeV | 0.000530 | 0.011413 | 21.53 | 主要来自 LEO secondary；部分/混合有效域 |
| electron 1–10 MeV | 0.058177 | 0.026998 | 0.464 | 只累计模型有效的分量 |
| positron 1–10 MeV | 0.019595 | 0.089093 | 4.55 | 只累计模型有效的分量 |

最值得记住的是：卫星环境不是“把气球谱整体乘一个高度因子”。天区 photons、Earth albedo、primary GCR、secondary/albedo charged particles、trapped/SAA 必须拆开；它们有不同角域、能谱和任务时间语义。

## 图和数据

- [`gamma_source_comparison.png`](outputs/figures/gamma_source_comparison.png)：gamma 宽带及 300–800 keV 原生节点对比；mono-511 只标积分通量，不伪装成连续谱密度。
- [`particle_family_source_comparison.png`](outputs/figures/particle_family_source_comparison.png)：p、alpha、e−、e+、n 与 muon 可用性；LEO primary/secondary 分开。
- [`common_support_shape_comparison.png`](outputs/figures/common_support_shape_comparison.png)：共同有效能区内的单位化形状，去除绝对通量和角域归一化。
- [`component_inventory.csv`](outputs/tables/component_inventory.csv)：每个分量的卡通量、恢复物理通量、角域、能区、哈希和 QA 状态。
- [`environment_contrasts.csv`](outputs/tables/environment_contrasts.csv)：按能带的 LEO/balloon 环境对照；无有效覆盖或缺失组件写 `NA`，不补零。
- [`band_integrals.csv`](outputs/tables/band_integrals.csv)：气球 full/down/up、卫星单分量和 profile 的完整积分表。
- [`summary.json`](outputs/summary.json)：机器可读摘要。
- [`VALIDATION_REPORT.md`](VALIDATION_REPORT.md)：最终验证报告。

生成的 10 个卫星连续谱在 `outputs/spectra/cosi_dc4_physical_restored_unit_pdf/`。它们采用 total kinetic keV 和单位积分 `IP LOGLOG` PDF；绝对通量必须从 `component_inventory.csv` 读取。它们不是可直接投入 Mass511/S3d 的完整 source card，因为角域、轨道时间和几何发射面尚未绑定。

## 已发现并保留的上游问题

1. `AlbedoNeutrons.source` 引用一个 12.6-GV 文件，但固定提交实际只有 10-GV 文件。本包只把现有谱作为明确标记的 diagnostic proxy；不能称为严格的 12.6-GV neutron baseline。
2. secondary electron/positron 文件仍标 10 GV。
3. secondary-proton 的恢复卡通量与 spectrum header 积分比约 0.588；albedo-photon 约 0.876。比较以实际 DC4 卡归一化为准，同时在 inventory 保留 header 值和比值。
4. COSI DC4 没有 mu−/mu+ 对应源。缺失不是零。
5. Galactic diffuse 是方向—能量函数，SAA 是轨道时间相关激活环境；两者都没有被强行压成一条静态 family 曲线。

## 复现

从仓库根目录运行：

```bash
python3 engineering/satellite_leo530_source_comparison_20260813/code/build_comparison.py
python3 engineering/satellite_leo530_source_comparison_20260813/code/validate_comparison.py
python3 engineering/satellite_leo530_source_comparison_20260813/code/build_simple_comparison_figures.py
python3 engineering/satellite_leo530_source_comparison_20260813/code/validate_simple_comparison_figures.py
```

验证会重新打开固定输入、160 个气球角箱、10 个卫星连续谱、mono-511、全部表和三组 PNG/PDF；当前结果为 `PASS`，0 errors、5 个设计上保留的 warnings。

## 外部来源

- [COSI DC4 background 固定目录](https://github.com/cositools/cosi-sim/tree/eec0dbf1aaabc79fea2706946434e30f7060a59a/cosi_sim/Source_Library/DC4/backgrounds)
- [1000 路并行及 Flux 缩放脚本](https://github.com/cositools/cosi-sim/blob/eec0dbf1aaabc79fea2706946434e30f7060a59a/cosi_sim/run_parallel_flux_sims.py#L12)
- [Pre-flight Background Estimates for COSI](https://arxiv.org/abs/2510.25304)
- [LEOBackground 的 PrimaryAlphas 总动能实现](https://github.com/cositools/cosi-background/blob/d83bc7b9b73d4a1a6bf6b1eda0c6e177cdfffe82/LEOBackgroundGenerator.py#L729)

## 下一步如何变成真正的卫星模拟源

在进入 Mass511/S3d transport 前，还需单独建立一个 orbit-aware 包：

1. 冻结最终高度、倾角、epoch、太阳调制、pointing/rocking 和任务时间线；
2. 逐时间步计算 cutoff rigidity、Earth limb 与 normal-science exposure；
3. normal prompt 与 SAA/AP9 activation 分成两条链，SAA 内不作为普通科学曝光；
4. 为本项目几何重新定义每个分量的 Beam、角域、发射面和 Flux，不直接照搬 COSI spacecraft source card；
5. 用同一轨道源契约对 Mass_model_511 与 S3d-O8 做 matched prompt → activation → delayed → response；
6. 只有全链闭合后才讨论卫星版屏蔽收益、灵敏度或设计晋级。

## Authority boundary

本包只授权“固定输入下的源谱与源级环境对比”。它不恢复旧 factor-1000 模拟派生结果，也不构成新的 detector background、activation、delayed response、mission sensitivity 或 geometry promotion authority。
