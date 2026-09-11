# Balloon → LEO → lunar response projection

## 推荐使用的简化两图

根据报告可读性要求，主展示图已改为只围绕 S3d-O8：

1. `outputs/simple/figures/01_s3do8_response_bands_on_spectra.{png,pdf}`
   按粒子分成五个面板；线型区分气球、LEO、月面，粒子颜色阴影表示
   S3d-O8 W2 本底的响应加权初级能量 10–90% 区间。五族合计覆盖
   当前 S3d-O8 W2 中央本底的 99.6%。
2. `outputs/simple/figures/02_s3do8_environment_relative_ratios.{png,pdf}`
   只比较 S3d-O8，把气球静态代理设为 1。LEO 的已映射 W2 本底为
   `0.527×`、F3 为 `0.726×`；月面分别为 `11.97×` 和 `3.459×`。

对应机器可读数据是
`outputs/simple/tables/s3do8_response_energy_bands.csv` 与
`outputs/simple/tables/s3do8_environment_relative_ratios.csv`。旧的三张审计图仍保留，
但简单报告优先使用这两张。

## PPT 公开版三图

进一步去掉内部几何、响应阶段与统计术语后的三张公开图位于
`outputs/public/figures/`：

1. `01_background_energy_bands`：按粒子显示三环境谱与彩色贡献能区；
2. `02_full_spectrum_comparison`：大气、LEO、月面三面板全谱；
3. `03_normalized_minimum_detectable_flux`：以大气为 1 的三根柱状图。

三图均由 `code/build_public_figures.py` 使用 Python/Matplotlib 生成，PNG 与
PDF 同源。图 1 的线型图例区分三种环境；图 2 的颜色/线型图例区分粒子族；
图 3 的色块图例区分三种环境。图 2 内的 `[1]`–`[3]` 引用及完整链接见
`outputs/public/REFERENCES.md`，机器可读核验记录见
`outputs/public/source_reference_audit.json`。

图 2 的纵轴是**各分量物理入射角域积分**的
`E dF/dE [cm^-2 s^-1]`，不是某一个方向的 `sr^-1` 强度，也不能笼统称为
三套谱统一的全立体角积分：大气谱是 20 个等 μ 角箱求和后的严格 `4π`；
LEO 谱是各 primary/albedo/secondary 分量按自身角域积分后求和；月面谱主要是
月壤上行 `2π`，其中 gamma 另加天空下行 `2π` 代理。因此三者单位相同，
但曲线高度不是严格的共同方向强度比。

第三图绘制的是最小可分辨通量代理，归一值为大气 `1.00`、LEO `0.73`、
月面 `3.46`；数据见
`outputs/public/tables/normalized_minimum_detectable_flux.csv`。图中为方便报告而省略的
方法边界仍由本 README 和父级数据表约束。

## 结论

这个包把 corrected balloon 后处理结果中的最终 W2（510.58–511.42 keV）
候选，追溯到造成它们的初级粒子种类和能量，再把同一个探测器响应作为
重要性采样基底，映射到 530 km 近赤道 LEO 代理谱和暴露月面代理谱。

核心结论是：S3d-O8 相对 Mass511 的 day-15 W2 本底降低
`0.1429498366 cps`。按入射粒子族合并 prompt 与 delayed 后，主贡献为：

| 粒子族 | Mass − S3d-O8 | 占总净降低 |
|---|---:|---:|
| gamma | 0.0688814 cps | 48.2% |
| proton | 0.0400687 cps | 28.0% |
| positron | 0.0189091 cps | 13.2% |
| alpha | 0.0132351 cps | 9.3% |
| neutron | 0.00194046 cps | 1.4% |

其中 gamma 包括 prompt（47.38%）和 delayed（0.80%）两部分；positron
包括 prompt 的改善与 delayed 的反向抵消，所以合并净占比为 13.2%。
electron 与 negative-muon 的小反向项保留在 CSV 中。

## 哪些初级能量起作用

最终 prompt W2 候选可以精确回到原 SIM 的 `IA INIT`：

- Mass511 gamma：4.181、6.743、8.083、8.146、14.728、62.992 MeV；
- Mass511 positron：112.810 MeV；
- S3d-O8 gamma：4.148、5.769 MeV。

9 个 prompt 候选全部带有 pair/annihilation 链。它们只是极低计数的响应
标记，不是光滑响应函数。

对 delayed 本底，本包扫描 446 个 corrected BUILDUP rich SIM，把
97,247 条 `CC IP RP` 与同一 history 的 `IA INIT` 精确连接，并按最终
母核—激发态—逻辑体积的 W2 响应率回配。S3d-O8 的响应加权 10–90% 初能区为：

- proton：10.69–80.80 GeV（中位数 15.56 GeV）；
- alpha：22.42–114.31 GeV **整颗 alpha 总动能**，即约
  5.60–28.58 GeV/n；
- neutron：14.18 MeV–336.71 GeV（中位数 1.73 GeV，能区很宽）；

这些范围是母核/体积层面的响应加权归因；不是每个 delayed decay 与某个
BUILDUP primary 的唯一因果配对。尤其 S3d-O8 的 delayed proton 仅 7 个、
alpha 仅 4 个最终候选，分位数只能作宽能区指示。

## 三环境 F3 映射结果

表中 `F3` 使用同一个 S3d-O8/Mass511 W2 响应，把 **day-15 探测器面
本底率静态保持 20 d**，并假设无大气吸收、100% live，按

`F3 = 3 sqrt(B) / (Aeff sqrt(T))`

计算。它是“已观察候选的连续谱 + 已映射活化”的中央响应代理，不是从零
库存起算的 0–20 d 活化时间线，也不是完整环境的最终最小可分辨通量。

| 环境 | Mass511 W2 B | Mass511 F3 | S3d-O8 W2 B | S3d-O8 F3 |
|---|---:|---:|---:|---:|
| balloon source reference | 0.2313 cps | 7.26e-5 | 0.08832 cps | 4.51e-5 |
| LEO quiet mapped proxy | 0.1582 cps | 6.00e-5 | 0.04655 cps | 3.27e-5 |
| lunar mapped proxy | 2.540 cps | 2.41e-4 | 1.057 cps | 1.56e-4 |

这给出一个简单判断：在目前能映射的连续谱与活化分量内，安静近赤道 LEO
比大气基准低，暴露月面则明显更差；S3d-O8 在三个环境中都保留相对优势。

当前 balloon 任务轨迹/大气吸收/有效 live 已折叠的正式解析场景值不同：
Mass511 `1.107e-4`，S3d-O8 `6.924e-5 ph cm^-2 s^-1`。不要把表中的
静态无大气参考值替换这一当前 balloon 数值。

## 为什么 LEO/月面数值不是总 Fmin

以下分量尚未被当前 balloon proposal 的响应支持覆盖，因此从所有 LEO/月面
投影值中明确排除：

- LEO 独立 delta-511、SAA/trapped 粒子、轨道时间与姿态权重；
- 月面 REDMoon 原生 511-bin 的直接响应、SEP、南极当地月壤/地形；
- 月球基地、着陆器、RTG/反应堆与支撑材料产生的 prompt/delayed 本底；
- HZE、角分布变化、占空比变化及偶然 veto 的改变。
- balloon prompt 中零幸存的 p/n/alpha/e-/mu 族仍按中央值 0；它们的非零
  统计上限缺少初能，不能重加权，因而未计入目标环境误差；
- 图中条件 MC 误差不含有限 RP/谱比重权和源模型系统学，不是覆盖区间。
- 目标环境落在 balloon proposal 支撑外的能区（例如部分 LEO 高能尾和月面
  近 TeV neutron）无法用重要性重权估计，因此也未计入中央值。

特别是 511 keV 入射线不能用数 MeV prompt gamma 候选任意赋权。LEO 的
`3.27e-5` 很可能是乐观部分值；月面的 `1.56e-4` 也仍是不完整值，但月壤
上行 gamma/neutron 已经显示出更高本底的明确风险。完整结论需做目标环境
source card 的 matched prompt + buildup + delayed transport。

## 文件

- `outputs/figures/01_source_spectra_with_w2_response_energy.{png,pdf}`：三环境源谱与响应能区；
- `outputs/figures/02_current_performance_contributors.{png,pdf}`：粒子族和能量贡献；
- `outputs/figures/03_projected_background_and_f3.{png,pdf}`：本底与 F3 代理；
- `outputs/tables/prompt_w2_primary_energy.csv`：9 个 prompt 精确初能；
- `outputs/tables/activation_rp_primary_energy.csv.gz`：97,247 条 BUILDUP RP 初能连接；
- `outputs/tables/w2_primary_energy_intervals.csv`：响应加权能区；
- `outputs/tables/f3_projection.csv`：投影数字与边界字段；
- `outputs/summary.json`：机器可读总表；
- `data/validation.json`：闭合和图文件验证。

重建顺序：

```bash
python3 code/scan_activation_primary_response.py
python3 code/build_response_projection.py
python3 code/build_simplified_s3do8_figures.py
python3 code/build_public_figures.py
python3 code/validate_response_projection.py
```

最终验证状态为 `PASS`，但 authority boundary 是
`NOT_ENVIRONMENT_TRANSPORT_AUTHORITY`。
