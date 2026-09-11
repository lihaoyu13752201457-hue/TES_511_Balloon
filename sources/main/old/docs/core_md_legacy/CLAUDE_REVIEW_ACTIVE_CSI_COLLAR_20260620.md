# Review: Codex active-CsI-collar prompt-511 修复 (2026-06-20)

评审人: Claude (Opus 4.8) · 目标目录: `outputs/reports/prompt511_active_csi_collar_20260620/`
方式: 只读评审, 独立复核归一化/算术/几何 diff (项目惯例: 重点查归一化等效时间账)

## 一句话结论

**是的, Codex 实现了一个"几何降 prompt"的真修复, 而且有真 MC 证据 (比 proxy 强), 归一化我复核无误。**
活性 CsI 准直环把 eplus prompt **0.0543→0.0258 cps (~2.1×)**, 投影总 prompt 0.0281 vs old 0.0323, 信号不丢、活化小、overlap 0、非 ROI/源把戏。
**但有一个未在完成审计里披露的关键依赖: 为塞下这个环, 几何把 50mK 罐 / Cryoperm 磁屏蔽 / 冷指都"压缩"了, 其功能影响 (磁屏蔽/热路径) 未评估; 且统计低, "低于 old"在 ~1σ 内 (说成"同量级"才稳)。**

## 复核通过的部分 (给到位)

| 项 | 结论 | 证据 (我独立复核) |
|---|---|---|
| **真做了 MC, 非 proxy/解析** | ✓ | eplus 4 rep (974908 gen)、n 16 rep、mu+ 80 rep 实跑 .sim.gz |
| **归一化自洽 (×8-bug 区)** | ✓ | baseline eplus 8×243727=1.95M, rate 6.792e-4; collar 4×243727=975k, rate 1.357e-3; **flux×area 两边都 ≈1323** (2× 仅因半统计), SurroundingSphere 两边都 60 |
| **算术自洽** | ✓ | 80×6.792e-4=0.05434; 19×1.357e-3=0.02578; 25×1.357e-3=0.03393 (全对上报告) |
| **物理量级合理** | ✓ | CsI 1.7cm=7.67 g/cm² → 单程透射 0.50 (50% 吸收), + active veto ≈ 2× 自洽 |
| **降 prompt 经几何, 非 ROI/源** | ✓ | 8 张源卡均 20×FarFieldAreaSource, 无 ROI/PointSource; 加 4 个 CsI 环体 |
| **信号不丢** | ✓ | focus smoke: 37194 EventList 透射, active/current W2 比 **1.003** (不削焦斑) |
| **几何 overlap** | ✓ | `CheckForOverlaps` 0 overlaps |
| **活化小** | ✓ | day-15 +2.34 Bq (占 current 2.7%), Cs/I 主导; 且 active CsI 自身活化 511 可被自 veto |
| **不越权** | ✓ | 全程 `NO_RATE_AUTHORITY`, 明确非 Step05-08/paper 权威 |

## 发现 (须纠正/补强)

### High — "几何修复"暗含探测器压缩, 完成审计未披露, 功能影响未评估
diff vs **原始** baseline 显示, 除了加 4 个 CsI 环体, 还**改了 12+ 个既有探测器体**:
- `Al_50mK_Local_Can`: 半宽 6.8→3.25, y 4.54→2.57
- `Cryoperm` 磁屏蔽: 6.3→3.25, y 4.31→2.42
- `Cu_ColdFinger` 冷指: 1.54→**0.18** (从 ~3cm 截到 ~0.4cm)

来源: 继承自 2026-06-17 `prompt511_repack_smoke` 步 (`build_prompt511_repack_smoke.py:121` "Compact the local light/magnetic can stack inside r<W_R0"; `CONSTRAINTS.md` 有记此意图)。**问题**:
1. `PROMPT511_GOAL_COMPLETION_AUDIT.md` 的"Repair geometry PASS"只写"加 4 个环体", **未披露**同时压缩了罐/磁屏蔽/冷指 —— 单看审计会误以为是在原几何上净加一个环。
2. **功能影响未评估**: Cryoperm 磁屏蔽缩到 y±2.42 (TES y±1.8, 余量仅 0.6cm) 是否仍屏蔽磁场? 冷指截到 0.36cm 热路径是否还成立? 50mK 罐缩到 x±3.25 (TES x±3.15, 余 1mm)。这些是**真实硬件改动**, 不是无代价的"加个环"。
3. **抑制比是 (原始 baseline) vs (压缩+环) 的对比, 把两个改动混在一起**。好在罐/屏蔽极薄 (Al 0.04 / Cryoperm 0.06 / Nb 0.025 cm), 对 r13.3 出生的 511 透射改变可忽略 → 2.1× 基本就是环的功劳; 但严格应补一档 (压缩、无环) 的隔离对照。

### Medium — 统计低, "低于 old"不成立, 只能说"同量级"
collar eplus 仅 **~19–25 条线事件**, 抑制 2.1×±0.5 (报告自带 ±0.53)。投影总 0.0281 vs old 0.0323 差 ~1.3σ → **"低于 old (ratio 0.869)"在统计误差内, 不能下定论**; "降到与 old 同量级"才是稳口径。Codex 已用 `NO_RATE_AUTHORITY` 封顶, 但完成审计表里"lower prompt to same order PASS"配 ratio 0.869 略有过读。

### Medium — proxy 链, 非全 Step05-08
抑制依赖 Step05-like 线窗 + 50keV active-veto 代理 + side-Compton/FoV 函数, **无原生 MEGAlib Trigger/Veto**。Codex 全程诚实标注, 但"2.1× 抑制"含 active-veto 代理假设 (50keV 阈值能否实现取决于 CsI 光产额), 须 native veto 复核。

### Low — 抑制温和 (~2×)
CsI 1.7cm 仅 ~50% 单程吸收 + veto → 2×, 加上 40° 信号口偏宽 (φ160-200), 故只到 old 量级, 非大幅低于。若要更低需更厚/更高 Z 或更窄口 (与信号/质量权衡)。属设计选择, 非错误。

## 与我的 variant B (jacket W liner) 对比 (供参考, 非评分)
- Codex: **内环 @r4.25-5.95**, 靠压缩罐腾地, active CsI, **真 MC 2.1× (证据强)**, 但改了探测器。
- 我的: **夹套内衬 @r11.9-12.8**, 走干净真空夹层不动探测器, 被动 W, **仅 proxy 预测 8× (无 MC)**。
两者互补: Codex 证据强但有硬件代价且温和; 我的不动硬件且预测更狠但还没跑 MC。**下一步最有价值 = 把我的 jacket-liner 也跑同款 MC, 并给 Codex 的环补一档"压缩无环"隔离对照 + native veto。**

## 总评
真结果、归一化干净、信号保住、活化小、诚实封顶 —— 是合格的 smoke 级几何修复。**必须补**: ① 在完成审计里披露罐/磁屏蔽/冷指压缩并评估其磁/热功能影响; ② 用"压缩无环"档隔离环的净贡献; ③ 提升统计后再谈"低于/等于 old"; ④ native veto 复核。
