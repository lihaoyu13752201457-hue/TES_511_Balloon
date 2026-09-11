# GEANT4 Darwin/Guan-style vs Barhoum-style Laue Comparison

## 1. Geant4 底层原理

Geant4 的粒子输运不是把所有物理都写在 tracking loop 里，而是让 process manager 在每一步询问各个 physics process。离散过程通常通过 mean-free-path / interaction-length 竞争决定 step 限制，然后在 `PostStepDoIt` 改变 track、产生 secondary 或终止 track。

Barhoum-style Laue lens advanced example 的核心是：用一个 forced discrete process 在 lens boundary 处接管光子，在 `PostStepDoIt` 中决定 `ABSORB / TRANSMIT / DIFFRACT`。这能快速把 Laue focusing 放入 Geant4 tracking，但晶体物理与 Geant4 step bookkeeping 容易混在同一个 process 类里。

Guan/Reiazi-style 路线更接近 Geant4 EM process 的结构：process 类负责 Geant4 接口，Darwin/Zachariasen 或 dynamical diffraction model 类负责晶体物理。本目录复现的是这种分层思想，而不是声称移植了他们的源码。

## 2. 本目录实现

- 本 Python runner 是 legacy table-backed closure check：`DarwinDynamicalModel` 读取同一张 Zachariasen/Darwin mosaic-crystal 概率表，并按材料、hkl、能量、Bragg mismatch 插值。
- 当前 02 的 compiled Geant4 executable 已把物理后端移到在线 Darwin-Hamilton mosaic 计算，不在 tracking 时读取 01 概率表。
- `GuanStyleCrystalBraggModel`: 只负责晶体物理，计算局部 Bragg mismatch、概率、晶面法向和由 Bragg/specular geometry 得到的理想衍射方向。
- `Geant4ProcessAdapter`: 只模拟 Geant4 `PostStepDoIt` 的应用层行为：根据概率抽样三分支，必要时给衍射方向叠加 mosaic angular spread。
- 几何完全沿用 canonical Ge(111) 五环配置，目录内保留一份快照用于 hash/回归检查。

## 3. 关键结果

- 事件数：`100000`；环数：`5`；总 tile 数：`360`。
- Guan-style expected diffraction fraction: `0.245078`。
- Guan-style sampled diffraction fraction: `0.244350`。
- Barhoum-style Geant4 sampled diffraction fraction: `0.246380`。
- total expected delta vs Barhoum sampled fraction: `-0.001302`。
- max per-ring expected-p delta vs Barhoum mean-p: `9.120063e-06`。
- max reflection vector error: `8.270777e-14`。
- max plane-Bragg residual: `1.422032e-05` rad。
- sampled focal D90 from mosaic angular spread: `0.220905` cm。

## 4. Per-ring Comparison

| ring | keV | Guan expected p_diff | Barhoum mean p_diff | delta |
|---:|---:|---:|---:|---:|
| 0 | 480 | 0.255821 | 0.255812 | +9.120e-06 |
| 1 | 500 | 0.249369 | 0.249369 | -4.982e-08 |
| 2 | 511 | 0.245910 | 0.245914 | -3.630e-06 |
| 3 | 530 | 0.240088 | 0.240091 | -2.802e-06 |
| 4 | 550 | 0.234158 | 0.234158 | +2.687e-07 |

## 5. 信心边界

高信心：同几何、model/process 分层、Bragg/specular 方向闭合、legacy table-backed runner 与现有 Barhoum-style mean probabilities 对齐。

不能声称：这不是 Guan/Reiazi 源码移植；没有把 `G4CrystalBraggReflection` 或 `G4BraggReflection` 真正注册进 Geant4 EM category；也没有完成真实晶体批次、弯曲晶体、装调误差和 publication-grade same-lens validation。

## 6. Sources

- Barhoum 2022: https://agenda.infn.it/event/21084/contributions/178539/
- Guan 2023: https://digitalcommons.library.tmc.edu/uthgsbs_docs/3758/
- Reiazi 2025: https://mdanderson.elsevierpure.com/en/publications/g4braggreflection-for-accurate-modeling-of-bragg-reflection-in-pe-2/
- Geant4 process model: https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/TrackingAndPhysics/physicsProcess.html
