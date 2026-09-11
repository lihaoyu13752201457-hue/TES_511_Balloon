# 03 implementation manual: Channel wall-by-wall optics

## 给没接触过本工作的人的一句话

Channel 光学不是 Bragg 衍射，而是 511 keV gamma 在弯曲 W/Si multilayer spacer 中做小掠入射多次反射。当前实现不输入固定反射次数：每个 photon 从公开几何入口采样，在弯曲 channel 中逐墙求交，按 W/Si reflectivity table 抽样反射、吸收或泄漏，最后能到焦平面的才写入 `phase_space.csv`。

## 物理原理

1. W/Si 周期是 30 nm W + 150 nm Si，入口几何 open fraction 是 `150/(150+30)=0.8333`。
2. 落到 W 层的 photon 直接被 entry geometry block；落到 Si spacer 的 photon 才进入 channel。
3. 弯曲 channel 让局部 wall tangent 随路径长度变化，因此撞墙位置和 grazing angle 由几何自然产生。
4. 每次 wall hit 查 `R/A/T(E, theta)`，当前表来自 xraydb multilayer reflectivity，并用独立 Parratt recursion 做闭合。
5. 如果打开 Si path absorption，photon 在 spacer 中飞行的路径也会按 `exp(-mu * path)` 生存抽样。

## 当前运行结果

| item | value |
|---|---:|
| primaries | 20000 |
| survived | 5804 |
| transmissivity | 0.2902 |
| effective area cm2 | 18.4617 |
| spot D90 cm | 1.0329 |
| mean bounces per survivor | 19.6239 |
| include Si path absorption | True |

## no-fudge CAM511 对齐边界

| item | value |
|---|---:|
| CAM511 target transmissivity | 0.8 |
| best no-fudge transmissivity | 0.7615 |
| best no-fudge delta | -0.0385 |
| 1 nm roughness no-Si transmissivity | 0.7369 |
| no-fudge reaches CAM511 | False |

## 代码函数地图

| file | line | function/class | role | review focus |
|---|---:|---|---|---|
| `external_baseline/channel_raytrace_py/geometry.py` | 75 | `load_channel_config` | 读取 CAM511 public geometry YAML。 | 四环半径、长度、弯角、W/Si 厚度。 |
| `external_baseline/channel_raytrace_py/parratt_reflectivity.py` | 90 | `compute_reflectivity_rows` | 用 xraydb multilayer reflectivity 生成 R/A/T(theta)。 | 511 keV、W/Si 30/150 nm、roughness。 |
| `external_baseline/channel_raytrace_py/parratt_reflectivity.py` | 142 | `manual_parratt_reflectivity_s` | 独立 Parratt recursion 交叉核验。 | 不要只相信一个库函数。 |
| `external_baseline/channel_raytrace_py/wallbywall_channel.py` | 86 | `simulate_wallbywall_channel` | 主 Monte Carlo loop：采样入口、trace、汇总 history。 | 没有输入固定反射次数。 |
| `external_baseline/channel_raytrace_py/wallbywall_channel.py` | 325 | `_sample_entrance` | 按 ring 面积和 W/Si 周期采样入口点。 | W 层 entry blocked，Si spacer 才进入。 |
| `external_baseline/channel_raytrace_py/wallbywall_channel.py` | 399 | `_trace_one_event` | 在弯曲 channel 内逐墙求交、查 R/A/T、反射/吸收/泄漏。 | 反射次数由几何自然产生。 |
| `external_baseline/channel_raytrace_py/wallbywall_channel.py` | 628 | `_next_wall_hit` | 解二次方程找下一次撞墙位置。 | 弯曲项和正根选择。 |
| `external_baseline/channel_raytrace_py/wallbywall_channel.py` | 662 | `_global_position_direction` | 把局部 channel 坐标转为全局 x/y/z 和方向。 | 焦平面投影和 ring/tile 方位。 |
| `external_baseline/channel_raytrace_py/wallbywall_channel.py` | 125 | `summarize_wallbywall` | 计算 transmissivity、Aeff、D90、bounce/grazing-angle 统计。 | 性能数值的来源。 |
| `analysis/run_channel_wallbywall_rebuild.py` | 23 | `main` | CLI runner，连接 config、reflectivity table 和 wall-by-wall 核心。 | 默认是否含 Si path absorption。 |
| `analysis/build_channel_independent_closure.py` | 121 | `optical_constant_checks` | 低能 CXRO/Henke 范围和 511 keV electron-density/xraydb 检查。 | 光学常数闭合边界。 |
| `analysis/build_channel_independent_closure.py` | 184 | `run_wallbywall_variant` | 扫描 roughness 和 Si path absorption 的 no-fudge variants。 | 与 CAM511 0.80 headline 的差距来自哪里。 |

## 复现流程

主 wall-by-wall run：

```bash
python3 analysis/run_channel_wallbywall_rebuild.py \
  --n 20000 \
  --seed 20260521 \
  --reflectivity-table data/reflectivity/WSi_511keV_parratt_grid_dense.csv \
  --out runs/channel_wallbywall_rebuild
```

无 Si path absorption 的对照：

```bash
python3 analysis/run_channel_wallbywall_rebuild.py \
  --n 5000 \
  --seed 20260521 \
  --no-si-path-absorption \
  --out runs/channel_wallbywall_rebuild_no_si_abs_smoke
```

独立闭合包：

```bash
python3 analysis/build_channel_independent_closure.py
```

## 输出文件怎么读

- `wallbywall_events.csv`：每个 primary 的最终 outcome、bounce 数、路径长度。
- `optics_history.csv`：每一次 wall hit 的 stage、grazing angle、R/A/T。
- `phase_space.csv`：只有 `EXIT` photon，被投影到焦平面。
- `per_ring_summary.json`：每个 channel ring 的透过率和 bounce 统计。
- `summary.json`：总透过率、有效面积、D90、平均掠入射角和模型 warning。

## WRL 可视化

![WRL quicklook](channel_wrl_quicklook.png)

本目录里的 `channel_wallbywall_scene.wrl` 是用 `optics_history.csv` 的 wall-hit rows 生成的 WRL 审阅场景。蓝色 ring 用 `IndexedLineSet` 画在入口 x-y plane，不再用容易误导视角的 cylinder；深蓝线段显示 incident segment，绿色/红色/黄色/灰色分别表示 BOUNCE/EXIT/ABSORB/LEAK。

它不是原始 Geant4 可视化输出，而是基于本次 wall-by-wall path history 的审阅图，用来快速看 ring、wall-hit stage 和出射方向。

## 审阅优先级

先审 `_sample_entrance` 是否正确处理 W/Si open fraction，再审 `_next_wall_hit` 的几何求交和 `_trace_one_event` 的 R/A/T 抽样，最后审 no-fudge variants 是否把 roughness、Si path absorption 和 CAM511 headline 的差距说清楚。
