# SG3B 远场源面与共时间轴审计

## 结论

1. 当前 `SurroundingSphere` 是 `R=60 cm, center_world=(5,0,9) cm, distance=60 cm`。
   它在 InstrumentFrame 中的圆心为
   `(-2.828427, 0, 9.899495) cm`。
   保留的非真空包络最远 3D 顶点距离圆心 58.028299 cm，径向余量
   1.971701 cm；最远顶点属于
   `NF2_OuterSupport_Al_BaseMountAnnulus` (Aluminium)。因此当前 R=60 cm 确实包住质量模型，
   但余量只有约 2 cm。

2. 对球形 start area，MEGAlib 使用的平均起始面积是 `pi*R^2`，不是 `4*pi*R^2`。
   `FarFieldAreaSource theta_min theta_max phi_min phi_max` 先按立体角在给定角箱中抽方向，
   再在垂直于该方向的半径 R 圆盘上均匀抽起点。远场源的物理事件率是
   `lambda=Phi*pi*R^2`，所以固定源卡 Flux 和事件数 N 时，`T_eq=N/(Phi*pi*R^2)`。

3. 当前 gamma 20 个角箱总通量为 4.79966157779 cm^-2 s^-1。
   合并 3x 的 N=3,207,738 个 gamma 对应解析期望
   T=59.092981 s；receipt 合计 TT=59.105470 s，
   差 +0.012489 s，即 +0.379 个
   Poisson 到达时间标准差，闭合正常。

   若保持球心不变，把半径压到“当前最远非真空顶点外 2 mm”，则
   `R=58.228299 cm`。发射圆盘面积和生成率下降
   5.818%，固定 N 的等效时间提高
   6.178%。3x gamma 从
   59.092981 s 增至
   62.743709 s；1000 万 gamma 从
   184.220098 s 增至
   195.601103 s。

4. package 58 的 prompt/delayed **物理率归一化与独立泊松率的叠加是对的**：prompt 用
   `1/sum(TT_family)`，delayed 在 day 15 用 `A_family/1e6`，随后按源核素 ZA 的活动曲线缩放；
   每个任务节点将 prompt 和 delayed occupancy 率相加。

5. 项目内已有成熟且正确的逐事件公共时间轴方案：对每条流按总产率抽
   `N~Poisson(R*T)`（等价于指数到达间隔），按事件模板的相对率有放回抽样，赋予 `[0,T]` 均匀时刻并
   merge/sort；随后把相邻间隔小于 tau 的事件组成候选，累加候选内 TES pixel 与主动屏蔽沉积，再做 veto。
   保留实现位于 `old/code/tools/make_complete_day15_report_ADR.py` 和
   `old/code/tools/build_v3p5_centerfinger_step05_l1_response.py`。

6. 需要区分的是：SG3B package 58 当前结果**没有调用这套成熟的逐事件 replay**。它在 81 个任务节点使用解析式
   `L=exp[-tau*(R_prompt+R_delayed)]`；唯一的显式泊松抽样是 day-15、46.6 s 的两条聚合流 toy validation。
   这不是对 M05 方法的否定，而是 package 58 的实现范围说明。

## day-15 时间模型边界

- prompt occupancy: 20237.815965 s^-1
- delayed occupancy: 1221.396075 s^-1
- total: 21459.212039 s^-1
- tau: 1e-06 s
- 当前实现 `exp(-R*tau)`: 0.978769399
- 仅作定义对照的双侧隔离 `exp(-2R*tau)`: 0.957989536
- 仅作定义对照的非延长死时间 `1/(1+R*tau)`: 0.978991611

当前 package-58 occupancy 统计“TES、plastic 或 BGO 任一正能量沉积”。因此 package 58 的
`exp(-R*tau)` 是成熟公共时间轴算法的解析期望代理；真正要输出 SG3B 的 time-window veto 数字，应调用
项目已有的逐事件实现，在候选组内分别求和 plastic、BGO 和 TES 沉积。

## 最小安全后续动作

不重跑输运，也不重新发明算法：直接迁移复用现有 `draw_timeline`/`analyze_timeline`，输入 SG3B 已接受的
compact event templates 与 family/ZA 的时间变产率，把旧单一 BGO 通道适配为独立 plastic 与 BGO 通道，
再施加 50 keV veto 和 Compton 选择，并与 package 58 的解析期望闭合。
