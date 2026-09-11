# 月面、LEO 与 38 km 气球入射源谱对比

状态：`PASS__SOURCE_INPUT_PROXY__NOT_TRANSPORT_AUTHORITY`

这个目录在不覆盖现有气球/LEO 包的前提下，增加一个裸露月面 prompt 入射源代理。主用途是回答：如果把 511 keV 望远镜放到月面，源谱在数量级和 511 keV 附近会怎样变化。

这里比较的是入射源，不是探测器计数、本底率、活化、延迟本底或灵敏度。

## 两张图

1. [`three_environment_prompt_components.png`](outputs/figures/three_environment_prompt_components.png)：与用户给出的 CubeSat 图式一致，分别展示 38 km 气球、530 km 近赤道 LEO 代理和裸露月面的 prompt 粒子组件；没有跨粒子族绘制 `Total`。
2. [`gamma_balloon_leo_lunar_comparison.png`](outputs/figures/gamma_balloon_leo_lunar_comparison.png)：100 keV–10 MeV 的三环境 γ 源谱，以及五个共同宽能带的积分通量；这是更适合 511 keV 项目引用的主图。

两图同时提供 PDF 版本。

## 月面模型

月壤上行源来自 REDMoon 的公开 Figure 5 数表：

- 2019 年太阳活动极小期；
- Apollo-17 月壤剖面；
- Geant4 4.10.06.p01；
- `FTFP_BERT_HP`；
- 上行半球角积分 `dF/dE [cm^-2 s^-1 MeV^-1]`。

固定输入 [`fig5.txt`](inputs/redmoon_zenodo_5561427/fig5.txt) 的 SHA-256 为 `82d72b510ead4d136a289de0f32091bab5446418447c53168af32a3822f0c1f5`。公开数据 DOI 为 [10.5281/zenodo.5561427](https://doi.org/10.5281/zenodo.5561427)，对应论文 DOI 为 [10.1029/2021JE006930](https://doi.org/10.1029/2021JE006930)。

月面“总 γ 代理”定义为：

`REDMoon 月壤上行 γ + 2π 可见天空宇宙 γ 代理`

天空项复用了现有 COSI cosmic-photon 光谱强度并按 2π 可见天空缩放。这是明确标记的模型拼接，不是 REDMoon 原生输出；在 0.1–10 MeV 内只占月面总代理约 1.7%。未来输运时必须继续把 `sky_down` 与 `regolith_up` 分开，不能用一条无方向的总谱替代。

## 核心源级结果

0.1–10 MeV 的角域积分 γ 通量为：

| 环境 | 通量 [cm⁻² s⁻¹] |
|---|---:|
| 38 km 气球，全空间 | 2.66273 |
| 530 km LEO 代理，连续谱+mono-511 | 1.94046 |
| 月壤上行 | 51.83175 |
| 月面总代理 | 52.72391 |

因此该月面代理约为气球的 `19.8×`、LEO 代理的 `27.2×`。

在 450–600 keV 湮灭区域代理带宽内：

| 环境 | 通量 [cm⁻² s⁻¹] |
|---|---:|
| 气球 | 0.271022 |
| LEO，含独立 mono-511 | 0.102302 |
| 月面总代理 | 5.29119 |

月面/气球约 `19.5×`，月面/LEO 约 `51.7×`。这只是宽带环境对照，不是精确 511 keV 线通量比。

REDMoon 表中最大的 γ 节点位于 `512.86 keV`，为 `325.06 cm^-2 s^-1 MeV^-1`。图中保留原生节点，不做平滑；其有限宽度属于公开表的能格，不能解释为本征线宽或 TES 响应线宽。月面总 γ 已包含该结构，禁止再叠加独立 mono-511。

## 重要边界

- 月面是 Apollo-17 月壤代理，不是中国未来月球南极基地的最终地质模型。
- 未包含南极水冰、局部地形/地平线、基地平台、着陆器、RTG/反应堆或支架材料。
- 未包含 SEP；太阳粒子事件必须另建瞬变场景。
- 图中略去了活化和延迟谱，按用户要求只画 prompt 入射源。
- LEO 的 SAA 未并入 normal-science 源；月面也没有地球 SAA，但仍受 SEP 和太阳周期影响。
- 三种环境具有不同物理角域，因此主 γ 图使用角域积分通量，不能把它解释为共同方向上的局部强度比。
- 本结果不能直接推出 detector counts、CPU 负担、灵敏度或 Mass511/S3d-O8 的设计晋级。

## 数据与复现

- [`lunar_prompt_components.csv`](outputs/tables/lunar_prompt_components.csv)：REDMoon 五个公开 prompt 组件的规范长表。
- [`three_environment_gamma_spectra.csv`](outputs/tables/three_environment_gamma_spectra.csv)：三环境 γ 连续谱及月面拼接分量。
- [`gamma_band_integrals.csv`](outputs/tables/gamma_band_integrals.csv)：共同能带积分。
- [`line_components.csv`](outputs/tables/line_components.csv)：LEO delta-511 的独立积分通量和绘图规则。
- [`summary.json`](outputs/summary.json)：机器可读摘要。
- [`validation.json`](data/validation.json)：输入哈希、积分锚点、原生 512.86-keV 节点和图像静态 QA。

从仓库根目录运行：

```bash
python3 engineering/lunar_surface_source_comparison_20260813/code/build_lunar_comparison.py
python3 engineering/lunar_surface_source_comparison_20260813/code/validate_lunar_comparison.py
```

下一步若要生成可投入 Cosima 的月面源卡，应把 REDMoon/Apollo-17 代理替换为南极地点的 `E × μ` 月壤响应，并补充 BON2020 的 H–Ni 直达 GCR、太阳极小/极大和独立 SEP 场景。
