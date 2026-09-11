# GPT Pro Geometry Optimization Package

This directory intentionally contains exactly 10 files. It replaces the previous data-only complement package when the goal is to ask GPT Pro for optimization directions.

## Use This Prompt

```text
我上传了当前 TES 511 keV 探测器 geo-opt S1/BPE/W5 几何、W2 线窗背景事件轨迹、入口位置分类、veto 标志、塑闪 veto 效果、BPE/中子活化效果数据。

请不要主要复述数据结论。我已经完成初步分析，现在需要你基于这些文件提出下一轮几何优化方向。

重点任务：
1. 根据 W2 背景事件的入射位置和轨迹，判断哪些几何区域最值得优先修改。
2. 分别针对 e+、neutron、atm511、activation，提出可执行的几何或 veto 优化方案。
3. 判断哪些方案可能真实降低 TES W2 本底，哪些只是看起来合理但风险大。
4. 给出一个优先级排序：最高优先、次高优先、暂不建议。
5. 对每个建议说明：预期压制的背景成分、可能副作用、需要跑什么最小验证模拟。

请特别关注 side_wall、side_window、top、bottom、envelope_miss 的泄漏路径，以及 plastic skin veto、non-plastic active veto、Compton/FoV veto、BPE shield stack 的实际作用。目标是找到下一轮最值得测试的几何改动，而不是重新总结已有分析。

几何图和 WRL 用于帮助你理解空间结构；真正的优化判断请以 W2 事件轨迹和 veto/entry CSV 为主。
```

## File Roles

- `03_geometry_2d_detail.png`: quick geometry overview.
- `04_geometry_3d_wrl.wrl`: CAD-like 3D context.
- `05_geoopt_added_geometry_manifest.json` and `06_geoopt_added_volumes.geo`: added plastic/BPE/W geometry definitions.
- `07_w2_particle_trajectories_enriched.csv`: one W2 raw TES event per row with source point, direction, TES centroid, entry class, and veto priority.
- `08_w2_event_veto_flags.csv`: explicit event-level plastic, active, and Compton/FoV veto flags.
- `09_w2_entry_angle_veto_summary.csv`: compact entry/angle/veto aggregate table.
- `10_plastic_bpe_neutron_effects.csv`: plastic-veto, BPE/shield-stack activation, and W2 neutron-depth evidence in one table.

## Caveats

- BPE effect is not isolated by a no-BPE A/B transport; current evidence is for the S1/BPE/W5 shield stack.
- Plastic-off means post-processing veto accounting off; plastic material remains in transport.
- Entry window is a proxy based on envelope crossing near local negative-X side-window axis, not a CAD boundary scorer.
- Neutron depth table uses first-hit depth proxy, not continuous energy-loss-vs-depth scoring.
