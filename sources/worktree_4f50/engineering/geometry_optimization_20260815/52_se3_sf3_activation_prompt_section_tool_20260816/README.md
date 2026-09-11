# SE3 activation + SF3 prompt detailed-section TOOL

本包把“详细二维剖面、活化母核素源点、prompt 瞬时轨迹及其统计”收成一个可复用、
默认自包含的轻量工具。入口为
[`TOOL/README.md`](TOOL/README.md)，一条命令即可重建 PNG/SVG/PDF、CSV、JSON 和分析报告。

本包没有启动 transport、没有打开或哈希大型 SIM。运行时只读取 TOOL 内约 2.4 MB 的
派生资产快照：SE3 原生网格、SE3 延迟 W2 源点/统计表，以及 SF3 三条 prompt W2 路由 JSON。

## 当前定量结论

- SE3 延迟 W2：47 个选择事件，`0.0601133620585 cps`；Cu-61/Cu-62/Cu-64 合计
  `92.9946%`。
- MXC 50 mK Cu 冷板：7 个事件，`0.0150711950460 cps`，占 `25.0713%`。因此不能用
  加入被动 W 后的 SF3 活化结果来否定 MXC 的 SE3 风险。
- 50 mK Cu 底盖与 L0 Cu 实心盘合计覆盖观测到的 `38.9850%` 延迟 W2；加上 MXC 后
  覆盖 `64.0563%`。
- SF3 的 3 个 prompt 幸存事件合计 `0.152255126811 cps`：两个 PAIR 顶点在新增侧壁 W，
  第三个在 W 外 PAIR、随后在新增前 W 发生 RAYL；三者主动 veto 沉积均为零。

所以后续优先级仍是：先做 V2A（L0 实心盘改开口环 + 50 mK 底盖改 aperture/ring-cap），
再做 V2B（MXC 受热工约束的错位开孔/减铜），4 K 冷板留作更高工程风险的后续分支；
不在聚焦接受路径附近添加高 Z 被动 W。

这些是候选方向，不是几何晋级。mono-511 仍禁用，被动 W 不属于 veto，SF3 没有补
full-stat，目前没有最终最优几何。

