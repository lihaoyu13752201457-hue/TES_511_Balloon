# SE3-V2A 二维剖面标注（2026-08-16）

本包复用冻结 SE3 的 parser-validated native mesh 与
`44_geoopt_se3_minimal_20260815/code/build_se3_visuals.py` 中的精确
`y′=0` 剖面绘制函数，生成两张 proposal-only 图：

1. `figures/se3_v2a_global_section_markup.*`：全局剖面，标出 V2A 的
   50 mK Cu can 底盖、L0 Cu 实心盘，以及 V2B 后继的 MXC 冷板区域；
2. `figures/se3_v2a_local_nearfield_section_markup.*`：TES–50 mK/MXC
   局部放大，标出环形底盖、open-ring/spokes 与热路外移的概念意图。

红色/琥珀色轮廓来自当前 SE3 native mesh 的真实实体边界；绿色和紫色
仅表示拟修改方向，尺寸尚未冻结。图不修改 SE3 几何，不是 overlap、
navigation、signal-clearance、transport 或 physics authority。

生成命令：

```bash
python3 engineering/geometry_optimization_20260815/51_se3_v2a_section_markup_20260816/code/build_se3_v2a_section_markup.py
```

校验记录位于 `audit/se3_v2a_section_markup_validation.json`。
