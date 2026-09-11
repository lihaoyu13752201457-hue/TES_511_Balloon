# opticsim_full Project Introduction

`opticsim_full` 是从原 `/home/ubuntu/opticsim` 中拆出来的干净版 Laue 光学模拟子项目。它只保留当前论文链路使用的最新 B-FULL Laue 透镜闭环代码和最小配置, 不迁移旧版 Laue/Channel 原型、不迁移历史 run 数据、不迁移大报告资产。

## 当前模型

当前权威模型是 `balloon511_f9m_ge111_511line`:

- 物理目标: 511 keV Ge(111) Laue 线聚焦, 用作后端 TES/本底模拟的前端 focused source 生成器。
- 几何: 单环, 焦距 `9000 mm`, `27` 块 `15 mm x 15 mm` Ge(111) tile。
- 晶体: Ge(111), `d = 3.266590088 A`, mosaicity `30 arcsec`。
- B-FULL 过程: application-level `G4VDiscreteProcess`, 有限 Laue diffraction mean free path, 与 Geant4 标准 EM 过程竞争。
- 外部物理锚: 511 keV XOP/CRYSTAL rocking curve map。
- 当前项目权威数: `A_eff(511) = 15.29928 cm2`, optical focal `r99 = 0.291410 cm`, Be window radius `1.898 cm`。

这不是 Geant4 toolkit patch, 也不是弯晶透镜工程模型。它是一个 mosaic flat-crystal Laue transmission baseline, 用来生成 tracked focal-plane crossings。

## Directory Layout

```text
opticsim_full/
  CMakeLists.txt
  Project_Introduction.md
  analysis/
    run_bfull_f9m.sh
    run_with_geant4_114.sh
  data/laue/
    ge111_balloon511_f9m_511keV_line_config.csv
    ge111_balloon511_f9m_511keV_xop_map.csv
    ge111_511keV_rocking_curve.csv
    Ge111_480_550keV_darwin_mosaic_table.csv
  docs/
    laue_latest_discussion_20260611.md
  geant4_app/
    include/optics/LaueEfficiencyTable.hh
    src/optics/LaueEfficiencyTable.cc
    src/laue_multiring_bfull_demo.cc
```

## Build And Run

默认使用本机已安装的 Geant4 11.4 包装脚本:

```bash
cd /home/ubuntu/opticsim/opticsim_full
analysis/run_bfull_f9m.sh
```

可用环境变量覆盖默认值:

```bash
N_EVENTS=20000 OUT_DIR=/tmp/opticsim_full_bfull_smoke analysis/run_bfull_f9m.sh
```

脚本会构建到 `/tmp/opticsim_full_build_g4_11_4`, 并运行:

```text
laue_multiring_bfull_demo
  --ring-config data/laue/ge111_balloon511_f9m_511keV_line_config.csv
  --efficiency-table data/laue/Ge111_480_550keV_darwin_mosaic_table.csv
  --rocking-curve-map data/laue/ge111_balloon511_f9m_511keV_xop_map.csv
  --require-rocking-curve-map
  --focal-mm 9000
```

## Outputs

一次运行会在 `OUT_DIR` 下生成:

- `summary.json`: run-level physics/geometry/closure summary。
- `per_ring_summary.csv`: per-ring diffraction and reference comparison。
- `phase_space.csv`: analytic projection diagnostics only, 不作为科学注入源。
- `focal_crossings.csv`: tracked focal-plane crossings; downstream science handoff 应过滤 `source_tag=laue_bfull_diffracted` 且 within Be。
- `transmitted_space.csv`: actual primary/transmitted focal-plane crossings。
- `optics_history.csv`: event-level process history and vector diagnostics。
- `laue_bfull_particles.wrl`: lightweight visualization。

## Claim Boundaries

可以写:

- 使用 application-level Geant4 B-FULL Laue process 生成 511 keV focused source。
- Laue diffraction MFP 与标准 EM 过程竞争。
- XOP/CRYSTAL rocking curve map 用作 511 keV 外部物理锚。
- 下游使用 tracked `focal_crossings.csv`, 而不是 analytic `phase_space.csv`。

不要写:

- Geant4/MEGAlib 原生支持 Laue diffraction。
- 当前模型完整模拟弯晶 Laue 透镜。
- 当前单环设计等权聚焦整个 `480-550 keV` 宽能段。
- Laue lens hardware mass 的 cosmic-ray prompt/self-activation 已经包含在后端本底中。

## Source Provenance

本目录来自原仓库当前 B-FULL/f=9m 权威版本:

- 原 B-FULL driver: `/home/ubuntu/opticsim/geant4_app/src/laue_multiring_bfull_demo.cc`
- 原 f=9m config: `/home/ubuntu/opticsim/data/laue/ge111_balloon511_f9m_511keV_line_config.csv`
- 原 XOP curve: `/home/ubuntu/cross_check_laue/laue511_validation/benchmarks/xop_crystal/multiring/ge111_511keV_rocking_curve.csv`
- 当前复盘记录: `docs/laue_latest_discussion_20260611.md`
