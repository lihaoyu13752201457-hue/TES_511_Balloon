# Chart contract

## 分析问题

在只比较 prompt 入射源、略去活化与探测器响应的条件下，裸露月面、530 km 近赤道 LEO 代理和 38 km 气球场的粒子源谱与 511 keV 邻域 γ 通量如何不同？

## 图 1：三环境 prompt 组件

- 形式：三个共享坐标的 log-log 小面板。
- 横轴：total kinetic energy，MeV。
- 纵轴：各组件原生角域积分 `dF/dE`，`cm^-2 s^-1 MeV^-1`。
- 粒子族颜色固定，实线/虚线区分 primary/secondary 或天空/月壤。
- 不跨粒子族求和，不画 `Total`。
- LEO mono-511 只标位置，不赋微分高度。
- LEO broken-link neutron proxy 不进入图。

## 图 2：γ 主图

- 上图：100–10000 keV，`E dF/dE [cm^-2 s^-1]`。
- 下图：五个共同宽能带的积分 γ 通量，log 横轴。
- 气球：corrected-keV 全空间 broadband total γ。
- LEO：cosmic + albedo continuum；450–600 keV 带另加入积分 mono-511。
- 月面：REDMoon regolith-up γ + 2π cosmic-sky spectral proxy。
- REDMoon 512.86-keV 节点保持原生，不进行 spline 或 log-log 平滑。
- 450–600 keV 标记为 annihilation-region proxy，不能称为线通量。

## 允许的结论

只允许报告源级能谱形状、共同宽能带积分和环境数量级对照。不能报告探测器本底、活化率、延迟谱、灵敏度、CPU/磁盘需求或几何优选。
