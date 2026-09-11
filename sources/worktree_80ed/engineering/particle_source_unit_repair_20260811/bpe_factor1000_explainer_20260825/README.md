# 2 cm BPE 与 factor-1000 中子能量轴解释图

本目录保存两幅**不纳入论文**的机制解释图。它们回答的是：为什么旧中子能量轴低 (10^3) 倍时，2 cm、5 wt% 含硼聚乙烯（BPE）曾显得很有效；修正为当前 MeV 能区后，为什么 BPE 对最终问题只剩有限收益。

## 图件

1. `outputs/figure_1_bpe_neutron_spectra_current_vs_factor1000.{png,pdf}`
   - 上图：已有 corrected-keV、20 个等 \(\mu\) 角箱合并的真实 BPE 外/内边界电流谱。
   - 右图：保持积分电流不变，只把能量坐标变为 \(E_{old}=E_{current}/1000\) 的反事实输入；实线再乘当前输运给出的分能段 first-passage 到达比例。
   - 该实线是 attenuation-only screening proxy，没有能量再分布，**不是旧口径的输运输出谱**。

2. `outputs/figure_2_natural_cu_beta_plus_overlap.{png,pdf}`
   - 天然铜产生 \(^{61}\mathrm{Cu}\)、\(^{62}\mathrm{Cu}\) 和 \(^{64}\mathrm{Cu}\) 的 G4NDL4.5 有效截面；天然丰度取 \(^{63}\mathrm{Cu}=0.6915\)、\(^{65}\mathrm{Cu}=0.3085\)。
   - 右侧面板把 corrected-keV 和 factor-1000 情形的 BPE 后中子谱直接叠加，不再定义谱加权反应核。
   - 截面与中子谱保持为两个原始物理量；factor-1000 曲线仍是反事实筛查谱。

## 主要数值

当前真实 BPE 边界诊断中，全部边界穿越的中位能量由 1.320 MeV 降至 0.358 MeV；初级中子的 first-passage 到达比例为 67.55%。但快中子仍大量穿过：1–10 MeV 和 \(\ge39\) MeV 的到达比例分别为 76.09% 和 85.55%。

当前 corrected-keV 的自然铜直接反应电流后/前比为：

| 产物 | BPE 后/前 |
|---|---:|
| \(^{61}\mathrm{Cu}\) | \(0.8848\pm0.0127\) |
| \(^{62}\mathrm{Cu}\) | \(0.8421\pm0.0103\) |
| \(^{64}\mathrm{Cu}\) | \(0.8966\pm0.0971\) |

这意味着 2 cm BPE 不是“完全无效”，而是对当前快速中子场的直接铜活化只给出约 10–16% 的中心抑制。

factor-1000 反事实把大部分中子移到 keV 及更低能区，远离 \(^{61}\mathrm{Cu}\) 和 \(^{62}\mathrm{Cu}\) 的多中子发射阈区；同时 \(^{63}\mathrm{Cu}(n,\gamma)^{64}\mathrm{Cu}\) 截面在低能区增大。这解释了旧口径为何会改变对 BPE 的判断。

历史 S3 全屏蔽堆栈的旧口径诊断给出内部相互作用率 547.5 → 293.8 s\(^{-1}\)（下降 46.3%），源初始中位能约 4.25 keV，入内包络首相互作用能量中位约 1.11 keV。但该比较同时改变 BPE、塑料、CsI 和几何，不能作为 BPE-only 因果量；图 1 只把它作为旁证注释。

## 不能从这两图推出的结论

- 图中截面和边界中子谱不能直接视为核素产生率；实际计算还需要铜原子数、自屏蔽和库存演化。
- 图中截面未按正电子分支加权；尤其 \(^{64}\mathrm{Cu}\) 具有混合 \(\beta^+\)/EC/\(\beta^-\) 衰变。
- 直接铜折叠只到 100 MeV，不含更高能强子级联、BPE 旁路、活化位置、延迟输运及最终 veto/响应。
- 第二幅中的旧口径 BPE 后谱只是筛查代理。得到真正的旧口径 BPE-only 输出谱需要匹配输运或 \(K(E_{out}\mid E_{in})\) 响应矩阵。

## 可复现文件

- 生成脚本：`code/build_figures.py`
- 数值闭合检查：`code/validate_outputs.py`
- 图用谱：`outputs/spectra_for_figures.csv`
- 天然铜截面：`outputs/natural_cu_cross_sections.csv`
- 积分结果：`outputs/integrated_cu_indices.csv`
- 输入哈希、口径与限制：`outputs/provenance.json`

运行：

```bash
python3 engineering/particle_source_unit_repair_20260811/bpe_factor1000_explainer_20260825/code/build_figures.py
python3 engineering/particle_source_unit_repair_20260811/bpe_factor1000_explainer_20260825/code/validate_outputs.py
```

默认只读取 `ebb2` 中已有的小型 CSV/JSON 权威和本机 G4NDL4.5 表，不读取 SIM/NPZ，不启动输运，也不修改论文。
