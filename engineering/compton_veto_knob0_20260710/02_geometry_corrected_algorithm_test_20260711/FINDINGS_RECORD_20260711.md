# Knob0 发现记录与处置结论（2026-07-11）

**状态**：`RECORDED_NEGATIVE_RESULT; GEOMETRY_REPAIR_NOT_YET_AUTHORITY`  
**适用范围**：Mass_model_511 W2 prompt/delayed + focused signal 的重放，以及
S3c 3M atmospheric-511 的全部 W2 active-pass 事例。  
**决策**：`DO_NOT_PROMOTE_FLUORESCENCE_MERGE_OR_LONG_ARM_TIGHTENING`。

本记录固化本轮审阅与几何修正诊断的发现。它不改写任何 retained
Mass_model_511 或 S3c authority 产物；原始
`KNOB0_FLUORESCENCE_ARM_STRATIFICATION_BRIEF.md` 保留为方案提出时的历史
简报。涉及 Knob0 是否晋级的判断，以本记录和同目录的可复现审计数据为准。

## 结论卡

1. **不晋级 Knob0 算法。** 在几何修正后的共同基线下，荧光合并与长杠杆臂
   收紧均没有拒除任何 prompt/delayed 本底，却会拒除 focused signal；最好的
   候选是 `k=2.5`，但它是 no-op。
2. **“S0/S1 字面规则使 S3c 从 6 变 7”的归因不成立为稳健结论。** 采用实际
   像素形状与 45° 旋转后，未加任何 Knob0 收紧的基线本身就是 `7`；事件
   `30621` 从 legacy veto 变为 geometry-corrected keep。因此旧的 `6 -> 7`
   主要暴露了位置/几何实现差异，不能再单独归因给 S0/S1 保留规则。
3. **几何修正是正确性维护项，不是灵敏度优化结论。** 它会改变许多事件的
   分类，尚未经过独立的 detector-response 闭环；不得据此替换现行 Step05
   authority 或修改已发布的 S3c 性能数字。

## 已确认的实现问题

现行 legacy 代码以能量加权的原始 `CC HIT` 连续位置构造事件位置，并用与世界
坐标轴对齐的代表盒枚举不确定度。实际 TES 吸收体的局部半尺寸为
`(3.0, 1.5, 1.5) mm / 2`，而 `InstrumentFrame` 有 `y = 45°` 旋转。诊断重放
改为使用像素 UID 中心和真实旋转后体素的八个角点，且将位置协方差也在旋转坐标
中传播。

这两个实现不能被视为同一个坐标约定：跨 Mass_model_511 和 S3c 的 `30,412`
个 W2 active-pass 事例中，共有 `751` 个 legacy/geometry 选择差异。所有
`2,256` 个像素 UID 都能映射到相应几何，输入字段长度、像素区间、复合事件键和
能量有效性均已通过检查；legacy 输出也被逐流精确重现后才应用修正。

## 量化证据

| 项目 | Legacy 现行实现 | 几何修正诊断基线 | 相对修正基线的 Knob0 结果 |
|---|---:|---:|---|
| Mass prompt 选后事例 | 65 | 63 | 荧光合并、`k=2/2.5/3` 均不再拒除本底 |
| Mass delayed 选后事例 | 28 | 27 | 荧光合并、`k=2/2.5/3` 均不再拒除本底 |
| Mass focused signal 选后事例 | 29,687 | 29,186 | 合并拒除 43；`k=2` 拒除 5；`k=2.5/3` 为 no-op |
| S3c 3M atm511 选后事例 | 6 | 7 | 全部单调 Knob0 候选保持 `7 -> 7` |

Mass_model_511 的加权 `S/sqrt(B)` 比较（`B = prompt + delayed`）进一步给出：

| 策略 | 相对 `S/sqrt(B)` |
|---|---:|
| geometry-current | 1.000000 |
| 荧光合并 | 0.998527 |
| 长臂收紧 `k=2` | 0.999829 |
| 长臂收紧 `k=2.5` 或 `k=3` | 1.000000（no-op） |

机制证据与这个结果一致：几何修正后的 prompt/delayed 幸存者中，
`L >= 20 mm` 的长臂事例为 **0**，而 focused signal 中有 **934** 个。因而
长臂收紧没有可拒除的已测本底目标，只能损失信号。荧光合并同样给出
`ΔB = 0, ΔS = -43`；`k=2` 给出 `ΔB = 0, ΔS = -5`。

## 对 Fable5 v1.1 修订与原简报的处置

- “只允许收紧、不得复活既有 veto”的单调性原则保留，并已在所有候选中验证：
  违反数为 `0`。
- 但原简报的 §4/§9 仍留有与该原则冲突的旧表述（例如 S0/S1 一律量热保留、
  `6 -> 7` 的单独归因）。本记录不把这些旧表述作为现行规范。
- 原简报中用于下一步的 Mass 多击数 `prompt 23 + delayed 14` 与当前 retained
  catalog 的 W2 active 组成不同；本轮直接在完整的 `71` prompt、`28` delayed
  与 `30,305` focused-signal active-pass 事例上重放，避免以过期计数作决策。
- 运行时 Ta 线窗必须跟随所用物理表。本重放冻结了独立 IA-PHOT 审计的
  `56.402, 57.686, 65.381, 67.523 keV`，各用 `±0.42 keV`，没有用 W2 结果
  回调这些参数。

## 边界与后续处置

本次没有新输运；Mass event catalog 的 `CC HIT` 能量没有做完整 detector-response
卷积。因此荧光打标在本测试中是偏乐观的。即使在这个对打标有利的边界下也未拒除
本底，故没有证据支持算法晋级；但它不是“所有未来设计都无算法机会”的普适定理。

建议保持现行 authority 选择不变，并将 Knob0 标注为已验证的负结果。若以后要
替换位置几何实现，应单列维护任务，并先完成：原始 SIM 或独立 response 的对称
signal/background 闭环、几何代表点的端到端回归、以及重算后的 S3c 下游 FoV/
性能报告。此前不得把诊断基线 `6 -> 7` 用于设计比较或灵敏度声明。

## 可追溯证据

- `README.md`：测试设计、数据质量边界和完整结果。
- `data/geometry_corrected_knob0_test_summary.json`：输入 hash、冻结定义、策略、
  机制证据和正式 decision。
- `data/policy_yields.csv`、`data/mass_model_511_significance_proxy.csv`：逐策略
  收益与加权 proxy。
- `data/geometry_current_strata.csv`、`data/policy_transitions.csv`：长臂空本底与
  配对迁移证据。
- `data/validation_result.json`：独立 validator，状态
  `PASS_GEOMETRY_CORRECTED_KNOB0_TEST_VALIDATION`。

复现命令：

```bash
python3 code/run_geometry_corrected_knob0_test.py
python3 code/validate_geometry_corrected_knob0_test.py
```
