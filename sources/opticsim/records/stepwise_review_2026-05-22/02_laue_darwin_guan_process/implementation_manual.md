# 02 implementation manual: Guan-style Darwin process split

## 给没接触过本工作的人的一句话

这一步是真正把 02 从 01 的查表变体中拆出来：`GuanDarwinDynamicalModel` 负责 Bragg/Darwin 物理判断和在线三分支概率计算，`GuanStyleLaueBraggProcess` 只负责接入 Geant4 tracking。它更接近 Guan/Reiazi 论文里“物理模型 + Geant4 process adapter”的路线，但仍不是他们的源码移植，也不是 Geant4 toolkit patch。

## 物理原理

1. 仍使用同一 Ge(111) 五环几何，方便与 01 做同结构对比。
2. 模型层在线计算理想焦点方向、晶面法线、局部 Bragg mismatch 和 Darwin-Hamilton mosaic 三分支概率。
3. process 层只在 Geant4 边界 step 触发，按模型返回的概率抽样。
4. 衍射方向由晶面法线反射得到，再加 virtual-crystallite/mosaic angular spread。

## 当前运行结果

| item | value |
|---|---:|
| primaries | 100000 |
| diffraction fraction | 0.2467 |
| absorption fraction | 0.3577 |
| transmission fraction | 0.3956 |
| spot D90 cm | 0.2194 |
| uses 01 probability table | False |
| online backend | Darwin-Hamilton mosaic formula with virtual crystallite plane-normal sampling |
| registered in Geant4 EM category | False |
| WRL | runs/geant4_laue_darwin_guan_process/laue_multiring_scene.wrl |

## 与 01 的数值闭合

| item | value |
|---|---:|
| delta diffraction fraction | 3.7000e-04 |
| delta absorption fraction | -0.0013 |
| delta transmission fraction | 9.2000e-04 |
| delta spot D90 cm | -0.0012 |
| max abs delta mean p_diff by ring | 6.3100e-04 |

## 代码函数地图

| file | line | function/class | role | review focus |
|---|---:|---|---|---|
| `geant4_app/src/laue_multiring_darwin_guan_demo.cc` | 190 | `OnlineDarwinMosaicProbabilities` | 在线计算 p_diff/p_abs/p_trans，不读取 01 概率表。 | 确认 02 的物理后端不是 01 的 CSV 查表。 |
| `geant4_app/src/laue_multiring_darwin_guan_demo.cc` | 224 | `ReflectAcrossPlane` | 按晶面法线做镜面反射方向计算。 | 反射几何是否与 Bragg 平面定义一致。 |
| `geant4_app/src/laue_multiring_darwin_guan_demo.cc` | 230 | `PerturbDirection` | 用 mosaic sigma 给衍射方向加小角度散布。 | sigma 单位由 arcsec 转 rad。 |
| `geant4_app/src/laue_multiring_darwin_guan_demo.cc` | 292 | `LoadRingConfig` | 与 01 相同的五环几何读取和 Bragg 半径核验。 | 确保 same-geometry comparison。 |
| `geant4_app/src/laue_multiring_darwin_guan_demo.cc` | 614 | `GuanDarwinDynamicalModel` | 把 Bragg mismatch、晶面法线、理想出射方向和在线 Darwin 概率集中在模型层。 | 这是 02 与 01 的主要架构和物理后端差异。 |
| `geant4_app/src/laue_multiring_darwin_guan_demo.cc` | 618 | `GuanDarwinDynamicalModel::Evaluate` | 计算 focusPoint、planeNormal、deltaTheta，并调用在线 Darwin-Hamilton mosaic 模型。 | deltaTheta 定义是否与 01 等价，概率是否不再查表。 |
| `geant4_app/src/laue_multiring_darwin_guan_demo.cc` | 644 | `GuanStyleLaueBraggProcess` | Geant4 process adapter，只处理 step 条件、抽样和 secondary。 | 物理和 Geant4 glue 是否拆开。 |
| `geant4_app/src/laue_multiring_darwin_guan_demo.cc` | 661 | `GuanStyleLaueBraggProcess::PostStepDoIt` | 调用模型 Evaluate 后走 ABSORB/TRANSMIT/DIFFRACT 三分支。 | process 是否只做 Geant4 adapter。 |
| `geant4_app/src/laue_multiring_darwin_guan_demo.cc` | 750 | `MultiRingPhysicsList::ConstructProcess` | 把 process 加到 gamma process manager。 | 这是 app-level discrete process，不是 EM-category patch。 |
| `analysis/compare_geant4_darwin_guan_vs_barhoum.py` | 23 | `compare` | 对 02 和 01 的 summary/per-ring 输出做数值闭合。 | mean p_diff delta 和 sampled fraction delta 分开看。 |

## 复现流程

```bash
cmake --build /tmp/opticsim-build-g4-11.4.0 --target laue_multiring_darwin_guan_demo

/tmp/opticsim-build-g4-11.4.0/laue_multiring_darwin_guan_demo \
  --n 100000 \
  --seed 20260521 \
  --ring-config data/laue/ge111_480_550keV_multiring_darwin_config.csv \
  --efficiency-table data/laue/Ge111_480_550keV_darwin_mosaic_table.csv \
  --mosaic-fwhm-arcsec 30 \
  --crystallite-um 5 \
  --out runs/geant4_laue_darwin_guan_process

python3 analysis/compare_geant4_darwin_guan_vs_barhoum.py
```

## 输出文件怎么读

- `summary.json`：明确写出 `model_process_split=true`、`registered_in_geant4_em_category=false` 和 `uses_external_efficiency_table_for_physics=false`。
- `barhoum_comparison_summary.json`：与 01 的直接数值差异。
- `per_ring_summary.json`：检查同 ring 的 mean `p_diff` 是否与 01 对齐。
- `laue_multiring_scene.wrl`：Guan-style run 自己输出的 WRL 场景。

## WRL 可视化

![WRL quicklook](guan_wrl_quicklook.png)

本目录的 `laue_multiring_scene.wrl` 是从 Guan-style run 的 `optics_history.csv` 重新生成的审阅 WRL。它显式画出 x-y lens plane 上的 ring、tile、incident segments 和输出分支，避免旧 decorative cylinder 视角下看起来像 beam 没打到 tile 的问题。

quicklook 左图显示同一五环几何，右图显示该 run 的焦平面 phase-space 点。

## 审阅优先级

先审 `OnlineDarwinMosaicProbabilities` 是否真的不读 01 概率表，再审 `GuanDarwinDynamicalModel::Evaluate` 的几何定义，最后看 `compare()` 里 online mean probability 和 sampled fraction 是否被混为一谈。
