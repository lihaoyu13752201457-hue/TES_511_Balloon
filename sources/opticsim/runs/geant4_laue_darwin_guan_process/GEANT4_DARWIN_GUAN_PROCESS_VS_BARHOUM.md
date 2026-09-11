# Compiled Geant4 Darwin/Guan-style Process vs Barhoum-style Process

## Geant4 底层原理

Geant4 tracking 通过 `G4ProcessManager` 调用每个 process 的 GPIL/DoIt 接口。Barhoum-style 和本 Guan-style executable 都是真实编译运行的 `G4VDiscreteProcess`，并通过 gamma 的 process manager 参与 tracking。

区别在于物理后端和代码组织：Barhoum-style process 直接在 `PostStepDoIt` 内查 01 概率表；Guan/Reiazi-style process 把在线 Darwin-Hamilton/Bragg 判断拆到 `GuanDarwinDynamicalModel`，`GuanStyleLaueBraggProcess` 只负责 Geant4 step 条件、branch sampling 和 secondary 生成。

## Summary

- Guan-style compiled process: `guan_reiazi_style_online_darwin_hamilton_virtual_crystallite_v2`
- Barhoum-style process: `multiring_zachariasen_darwin_mosaic_laue_process_v3`
- Guan registered process: `GuanStyleLaueBraggProcess added to gamma G4ProcessManager as a discrete process`
- Guan registered in Geant4 EM category: `False`
- Guan uses 01 efficiency table for physics: `False`
- Guan online backend: `Darwin-Hamilton mosaic formula with virtual crystallite plane-normal sampling`
- Diffraction fraction: Guan `0.246750`, Barhoum `0.246380`, delta `+0.000370`
- Absorption fraction: Guan `0.357650`, Barhoum `0.358940`, delta `-0.001290`
- Transmission fraction: Guan `0.395600`, Barhoum `0.394680`, delta `+0.000920`
- Spot D90: Guan `0.219415 cm`, Barhoum `0.220582 cm`, delta `-0.001167 cm`
- Max per-ring mean p_diff delta: `6.310000e-04`

## Per-ring p_diff

| ring | keV | Guan mean p_diff | Barhoum mean p_diff | delta |
|---:|---:|---:|---:|---:|
| 0 | 480 | 0.256290 | 0.255812 | +4.780e-04 |
| 1 | 500 | 0.249861 | 0.249369 | +4.920e-04 |
| 2 | 511 | 0.246427 | 0.245914 | +5.130e-04 |
| 3 | 530 | 0.240646 | 0.240091 | +5.550e-04 |
| 4 | 550 | 0.234789 | 0.234158 | +6.310e-04 |

## Boundary

This is a compiled C++/Geant4 model/process split implementation, not a copy of Guan/Reiazi source code. It is registered as an application-level discrete process for gamma, not as a Geant4 toolkit EM-category patch. The 02 backend no longer reads the 01 branch-probability CSV during tracking; it still uses compact Ge(111) attenuation/extinction constants anchored to the local validation chain, so a direct XOP reproduction remains the next publication-grade check.
