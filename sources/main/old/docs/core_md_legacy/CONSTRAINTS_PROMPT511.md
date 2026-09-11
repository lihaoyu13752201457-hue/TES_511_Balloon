# CONSTRAINTS — prompt-511 refix (ENFORCED contract + OBJECTIVE, keep SHORT)

> 被**强制检查**的契约, 不是"请记得读"。短=能塞进每个 subagent prompt + 被脚本逐条验。
> 硬门:
> - 几何/约束: `python3 code/tools/check_prompt511_constraints.py <cand.geo> <cand_dir>`
> - 结果门(有 MC 结果后): `... <cand.geo> <cand_dir> --results <results.json>`
> - 数值复核(独立重算归一化/抑制/显著性): `python3 code/tools/recompute_rates.py ...`
> exit≠0 = 违约, 不准过。

## 任务 = 一个有约束的优化(不是 pass/fail)
```
minimize   屏蔽侵入度  (优先级: 不改三层 > 加质量小 > 厚度薄)
subject to PROMPT_total ≤ old new_geo_re (0.0323 cps)   [统计上不高于, 见显著性]
           DELAYED(baseline+shield) ≤ DELAYED(baseline)·(1+ε),  ε=0.10   [净账, 必 MC]
           SIGNAL_keep ≥ 0.99   (step09 焦斑 replay)
           三层禁改 + 几何 overlap=0 + 归一化一致
report     Pareto 前沿(材料×厚度×半径), human 选工作点; 若前沿空 → 见 C9 上报
```

## 受保护的三层(CRITICAL, 改任一即整体 FAIL)
- `TES_*`(核心探测区)
- `Cu_ColdFinger_*`(导热 / 热路径)
- `Cryoperm_*`(磁屏蔽)
广义上: **不改/不压缩原始 baseline 任何既有体**(只允许新增屏蔽体)。三层是其中最硬的子集, 按名点检。

## 硬门(逐条脚本可验)
C1. 不改/删 baseline 任何既有体(尤其上面三层)。改=FAIL。 ← 防压缩 DR 复发, 也保证抑制比是"纯净隔离对照"
C2. 屏蔽=被动高 Z 金属(W/Ta/Pb), **冷区(r<11)不放闪烁体**(冷端 veto 不可实现)。
C3. SurroundingSphere=60 不变; flux×area / rate_per_event 自洽。 ← 防 ×8-bug(`recompute_rates.py` 验)
C4. 背景/信号源卡禁 ROI/PointSource/HomogeneousBeam(只 FarFieldAreaSource; overlap 源除外)。
C5. 几何 overlap=0(`cosima CheckForOverlaps`)。
C6. 信号口 ≥ Laue 焦斑(探测器耦合 r99=1.22, max=1.70 cm), 不削信号。
C7. predict-before-spend: (a) prompt proxy-ray 命中 ≥90%; (b) **delayed 廉价预筛**(isotope smoke + β⁺ 清单)不超预算——两者都过才准跑昂贵 MC。
C8. 成功=**四项 MC 闭环 + 信号 + 全披露**: prompt 降幅 + 屏蔽**自身瞬发湮灭 511 的 add-back 净账** + 次级中子 + **delayed 净账**。不是只看 prompt。
C9. **诚实结局**: 若在"不改三层"的空间内无被动屏蔽能同时满足 PROMPT 与 DELAYED 约束(Pareto 前沿为空)→ **停, 上报 human**(换材料 / 加质量预算 / 架构回轴入), **不得改三层蒙混**。

## delayed 是"净账", 不是"只算加多少"(关键认知)
被动金属**挡不住自己活化的 511**(active 才能 veto)。所以:
```
Δdelayed = (+) 屏蔽自活化 β⁺→511, 近 TES 侧, 部分到达 TES
         (−) 被屏蔽挡掉的、来自外层活化结构的 delayed-511
```
两项一加一减, **符号事先未知 → 必须 delayed 输运 MC**。材料是变量: W 紧凑(压 prompt 好)但 β⁺ 活化多; Ta/Pb 可能 delayed 更友好。**别钦定 W, 让 Pareto 说话。**

## 怎么"不会忘"(强制机制, 三层)
1. **硬门脚本**(最强): orchestrator 每迭代跑 checker + recompute; 红就 block。脚本不会忘。
2. **prompt 注入**: orchestrator 把本文件整段粘进每个 subagent task prompt(冷启动 subagent 由构造即带契约)。
3. **AGENTS.md 指针**(兜底): 仓库根放一行指向本文件, 每会话自动加载。
