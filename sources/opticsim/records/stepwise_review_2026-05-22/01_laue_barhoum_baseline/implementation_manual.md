# 01 implementation manual: Laue Barhoum-style baseline

## 给没接触过本工作的人的一句话

这一步是在 Geant4 里放一个五环 Ge(111) Laue lens。每个 gamma 打到晶体边界时，代码不使用经验校正因子，而是从本地 Zachariasen/Darwin mosaic 表查出 `p_abs / p_diff / p_trans`，再在 Geant4 的 `G4VDiscreteProcess::PostStepDoIt` 里随机抽样：吸收、透过或衍射到焦平面。

## 物理原理

1. Bragg 条件给出每个 ring 应该收哪一段能量：`lambda = 2 d sin(theta_B)`。
2. 焦距 `F` 固定后，ring 半径近似由 `R = F tan(2 theta_B)` 决定。
3. mosaic crystal 不是 perfect crystal：微晶取向有角分布，所以 `delta_theta = theta_local - theta_B` 会改变衍射效率。
4. `external_baseline/laue_raytrace_py/mosaic_darwin.py` 用结构因子、extinction length、mosaic weight、吸收系数计算三分支概率。
5. Geant4 只负责事件输运、几何边界、secondary gamma 和输出 phase space。

## 当前运行结果

| item | value |
|---|---:|
| primaries | 100000 |
| diffraction fraction | 0.2464 |
| absorption fraction | 0.3589 |
| transmission fraction | 0.3947 |
| spot D90 cm | 0.2206 |
| WRL | runs/geant4_laue_multiring_darwin/laue_multiring_scene.wrl |

## 代码函数地图

| file | line | function/class | role | review focus |
|---|---:|---|---|---|
| `external_baseline/laue_raytrace_py/mosaic_darwin.py` | 56 | `bragg_angle_rad` | 由能量和晶面间距计算 Bragg 角。 | 能量单位 keV、d-spacing 单位 Angstrom 是否一致。 |
| `external_baseline/laue_raytrace_py/mosaic_darwin.py` | 132 | `darwin_mosaic_probabilities` | 给出 p_diff、p_abs、p_trans 的物理概率。 | 吸收项、mosaic 权重、概率归一化。 |
| `external_baseline/laue_raytrace_py/build_mosaic_darwin_table.py` | 104 | `_write_table` | 扫描 delta-theta 并写出 Darwin 概率表。 | delta 网格范围、mosaic arcsec、厚度。 |
| `geant4_app/src/optics/LaueEfficiencyTable.cc` | 55 | `ValidateProbabilities` | 检查三分支概率非负且和为 1。 | 这是防止表损坏的第一道闸。 |
| `geant4_app/src/optics/LaueEfficiencyTable.cc` | 156 | `LaueEfficiencyTable::Lookup` | 按材料/晶面/能量找最近能量，并按 delta-theta 插值。 | 是否误用最近能量、是否 clamp 到表边界。 |
| `geant4_app/src/laue_multiring_table_demo.cc` | 191 | `LoadRingConfig` | 读取五环 Ge(111) 配置并核对半径与 Bragg 半径。 | 半径是否由 F*tan(2thetaB) 支持。 |
| `geant4_app/src/laue_multiring_table_demo.cc` | 300 | `MultiRingRunState::Record` | 记录 ABSORB/TRANSMIT/DIFFRACT，写 phase_space 和 history。 | 输出 schema 和 stage 语义。 |
| `geant4_app/src/laue_multiring_table_demo.cc` | 504 | `MultiRingProcess::PostStepDoIt` | Geant4 离散过程：边界触发、查表、抽样、生成二次 gamma。 | 只作用 primary gamma 和 LaueCrystal 边界。 |
| `geant4_app/src/laue_multiring_table_demo.cc` | 566 | `MultiRingDetectorConstruction::Construct` | 把 ring/tile 放进 Geant4 world。 | copy number 与 ring/tile 对应。 |
| `geant4_app/src/laue_multiring_table_demo.cc` | 650 | `main` | 装配 options、geometry、table、process、primary generator，并 BeamOn。 | 输入文件和 seed 是否是记录中的版本。 |

## 复现流程

1. 生成或更新 Darwin 表：

```bash
python3 -m external_baseline.laue_raytrace_py.build_mosaic_darwin_table \
  --ring-config data/laue/ge111_480_550keV_multiring_darwin_config.csv \
  --out-table data/laue/Ge111_480_550keV_darwin_mosaic_table.csv \
  --mosaic-arcsec 30 \
  --crystallite-um 5 \
  --delta-multiple 4 \
  --n-delta 81 \
  --optimize-thickness
```

2. 构建 Geant4 executable：

```bash
cmake --build /tmp/opticsim-build-g4-11.4.0 --target laue_multiring_table_demo
```

3. 运行主样本：

```bash
/tmp/opticsim-build-g4-11.4.0/laue_multiring_table_demo \
  --n 100000 \
  --seed 20260520 \
  --ring-config data/laue/ge111_480_550keV_multiring_darwin_config.csv \
  --efficiency-table data/laue/Ge111_480_550keV_darwin_mosaic_table.csv \
  --out runs/geant4_laue_multiring_darwin
```

## 输出文件怎么读

- `phase_space.csv`：只记录衍射后到焦平面的 gamma，可直接喂给后续 detector chain。
- `transmitted_space.csv`：未被吸收也未衍射的透过 gamma。
- `optics_history.csv`：每个 primary 在 lens 边界发生了哪种 stage，包含查表概率。
- `per_ring_summary.json`：每个 ring 的抽样分支和 mean table probability。
- `summary.json`：总 branch fraction、spot D90、输入表路径和 WRL 路径。
- `laue_multiring_scene.wrl`：Geant4/VRML 可视化场景。

## WRL 可视化

![WRL quicklook](laue_wrl_quicklook.png)

可直接打开本目录的 `laue_multiring_scene.wrl`。它是从 `ring_config` 和 `optics_history.csv` 重新生成的审阅 WRL：蓝色 ring 用 `IndexedLineSet` 画在 x-y lens plane，深蓝线段显示 incident beam 打到 tile 的入射段，红/灰/黄线段分别显示 DIFFRACT/TRANSMIT/ABSORB。这样避免旧 WRL 里 decorative cylinder 造成的视角误导。

这份 PNG 是从同一 ring config 和 `phase_space.csv` 生成的 quicklook，方便不装 WRL viewer 时先检查几何和焦斑。

## 审阅优先级

先审 `LoadRingConfig` 的 Bragg 半径核验，再审 `LaueEfficiencyTable::Lookup` 的 delta-theta 插值，最后审 `MultiRingProcess::PostStepDoIt` 的三分支抽样和 secondary 方向。
