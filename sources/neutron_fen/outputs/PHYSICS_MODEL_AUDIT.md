# SH3 Si/G4CMP 物理模型审计

日期：2026-09-03

## 可由当前输入支持的模型

G4CMP 的正式论文把它定义为低温固体中非平衡声子与载流子的产生和输运框架；它支持 Si/Ge 晶格中的各向异性声子传播、同位素散射、非谐下转换、表面反射/吸收以及可选的电荷和超导膜响应。论文也明确允许把声子直接作为 primary 注入。参见：

- [G4CMP: Condensed Matter Physics Simulation Using the Geant4 Toolkit](https://arxiv.org/abs/2302.05998)
- [G4CMP 官方仓库](https://github.com/G4CMP/G4CMP)
- [Si absorber 到 Al sensor 的非热声子透射测量与模拟](https://doi.org/10.1103/PhysRevApplied.11.064025)

本工作得到的是“加权声子 packet 的 Si 晶格传播与界面收集响应核”。每条原始 Si `CC HIT` 保留位置、时间和沉积能量；有限数量的 acoustic phonon primary 以 track weight 保持总能量。正式包络使用 62 meV（Si CrystalMap 的 Debye 尺度），并以 30 meV、2.7 meV 检查初始谱敏感性。62/30 meV 支路保留 G4CMP 的同位素散射和非谐下转换。

## 不能由当前输入支持的部分

当前 SH3 质量模型没有真实 SiO2/SiNx/Ta/AlMn 薄膜、布线、键合、接触面积、晶向、工作温度、界面透射、膜准粒子参数、TES 热容/热导、偏置点、ETF 回路和脉冲重建滤波器。质量代理中的 Si 与 Ta/Cu 甚至存在真空间隙。因此：

- `sensor_absorption` 是“到达理想收集界面后被吸收”的每次相遇概率，不是已知 TES 效率；
- Ta 的 65.28% 投影覆盖率只是扫描端点，不是真实 collector 覆盖率；
- direct acoustic primary 没有执行完整的 `G4CMPEnergyPartition` recoil/EM 到电子—声子初态分区；
- 输出的 arrival time 和 channel pattern 是 athermal kernel，不是完成的电流脉冲；
- A/B/C 的 ROI 判断只能是条件性包络，不能成为未经标定的绝对预测。

G4CMP 论文说明其 Monte Carlo 主要处理非平衡激发，平衡慢热过程并非显式模型。这里没有足够的边界条件和 TES 参数建立可信的 FEniCS 慢热 PDE；使用 FEniCS 只会把未知物理参数变成数值上的伪精度。因此本轮没有使用 FEniCS。

## 数值质量门槛

- 每个被接受的 chunk 要求 `summary.status == COMPLETE`；
- 加权输入与 sensor+bath+bulk 能量闭合误差小于 `1e-9`；
- 固定 seed；官方 example 的两次 smoke 输出逐字节相同；
- 86 个事件全部模拟，另有 exact A/B/C 与 51 strict 阶梯；
- C 的窄窗判断额外使用 5 个独立 seed、每个 8192 packet 的重复；
- packet MC 误差与接口系统包络分别报告。

## 解释边界

这套计算足以回答：在给定界面端点下，Si 中的能量能否在时空和通道上到达 TES 投影面，以及什么参数区间可能把 A/B/C 推入 ROI。它不足以回答：真实飞行器器件的唯一绝对耦合率、真实 AlMn/Ta 电流脉冲形状或最终 PSD 接受率。后者需要器件 CAD/膜栈、低温材料参数和源位标定数据。
