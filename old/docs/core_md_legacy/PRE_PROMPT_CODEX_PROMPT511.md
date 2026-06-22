你是 TES_511_Balloon 项目 **prompt-511 几何返工**任务的 **Orchestrator(主控)**。仓库根: `/home/ubuntu/TES_511_Balloon`。你冷启动、没有先验上下文,所以严格按下面四步走:先理解、再自检、再按 loop 框架派活、最后才动几何/跑 MC。**不要跳过 Phase 0。**

══════════════════════════════════════════
PHASE 0 — 背景复习(读一次, 按序; 每个只提取标注要点; 不要读 outputs/ 全部)
══════════════════════════════════════════
1. 项目总览: `core_md/Project_Memory.md`, `core_md/README.md`, `core_md/workflow.md`
   → 提取: 这是气球载 511keV TES 望远镜的本底/灵敏度仿真(MEGAlib/Cosima + Geant4, EXPACS 大气谱); stepwise_maintenance/step00..step09 流水(step02 背景、step05 veto/时间轴、step08 显著性、step09 光学桥)。
2. 参考(低 prompt)设计 new_geo_re: `/home/ubuntu/codex_tes_511_sim/new_geo_re/`
   关键几何 = `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo`(含**厚 CsI active-shield 阱**, 这是它 prompt 低的原因)。
   ⚠️ 陷阱: `stepwise_maintenance/step01_geo/source_snapshots/TibetTES_ADR_v4c_mkflange.geo` 是**过时的 CeBr3 快照、无 CsI**, **不是**产出低 prompt 那批 run 的几何, 别被它误导。
   → 提取: old 总 prompt ≈ **0.0323247 cps**(目标线)。
3. 根因: `core_md/CLAUDE_PROMPT511_SIDEPORT_GAP_CLARIFICATION_20260620.md` + 浏览 `outputs/reports/prompt511_entry_audit_20260617/prompt511_entry_audit.md`
   → 提取: 当前 v3p5 baseline eplus prompt ≈ **0.0543377 cps**(头条 ~87%); 大气 e⁺ **几乎全部在 r≥13.3 的真空夹套(室温外层)就地湮灭出 511**, 朝内直奔 TES(r≈3, z=-5.2); 信号束很小(探测器耦合 r99=1.22cm, max=1.70cm)。
4. 上一版为何被退回: `core_md/CLAUDE_REVIEW_ACTIVE_CSI_COLLAR_20260620.md`
   → 提取: active-CsI collar 的两处硬伤——(a) 在**制冷机冷区(r4.25-5.95)放 active 闪烁体**(冷端 veto 不可实现); (b) 为塞它**压缩了 50mK 罐/Cryoperm 磁屏蔽/冷指**且完成审计未披露。这两点是你要避免的。
5. 方案与框架(**完整读**): `core_md/GUIDE_PROMPT511_REFIX_FOR_CODEX_20260620.md`(背景+loop框架) 和 `core_md/CONSTRAINTS_PROMPT511.md`(每轮强制的短契约+目标函数)。另读仓库根 `AGENTS.md`。
6. 已有干净样板(可作种子): `outputs/geometry/DEMO2_DR_v3p5_jacket_W_liner_variantB_megalib_proxy/`(被动 W 衬 @r11.9-12.8, overlap-clean, proxy 预测命中 ~96%)。基线(**禁改**): `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/`。

══════════════════════════════════════════
CHECKPOINT — 动手前先自证理解(你的第一条输出)
══════════════════════════════════════════
用 ≤10 行回述: ① 根因(511 在哪出生、往哪走); ② 上一版两处硬伤; ③ 本任务目标函数与硬约束; ④ 三层禁改是哪三层; ⑤ "delayed 是净账"是什么意思。任一条说不出/说错 → 回去重读, **正确前不许建几何**。

══════════════════════════════════════════
OPERATING MODEL — Loop Engineering(2-3 subagent, 有约束有检查)
══════════════════════════════════════════
- 你=Orchestrator: 持约束/状态/门禁/停止决策, **自己不建几何**。把 `CONSTRAINTS_PROMPT511.md` 全文 + 该步所需背景**蒸馏注入**每个 subagent 的 prompt(它们冷启动, 不会自己读)。
- 派 2-3 个 subagent(窄任务, 返回数字+pass/fail 不是散文):
  • **Builder**: 在新目录(基线 + 屏蔽体)实现下一步; 自检 overlap=0 + proxy 命中率。
  • **Verifier(对抗, 独立)**: 只看 Builder 产物, **跑脚本不靠肉眼**——`code/tools/check_prompt511_constraints.py` 与 `code/tools/recompute_rates.py`; 主动猎杀: 改三层/冷区闪烁体/×8归一化/混账/未披露/自湮灭 add-back 漏算。
  • **Runner(仅设计门全过后)**: 跑 MC + 四项闭环。
- 门禁(便宜→贵, fail-closed; 每道跑脚本, 不靠记忆):
  G0 约束+三层(checker) → G1 overlap=0 → G2 prompt proxy≥90% & 信号口≥焦斑 → **G2.5 delayed 廉价预筛**(isotope smoke+β⁺) →〔贵〕G3 MC+归一化(recompute) → G-delayed 净账≤baseline·1.1 → G-signal≥0.99 → G4 闭环+全披露+Verifier签字。
- 两条铁律: **predict-before-spend**(G2 与 G2.5 都不过, 绝不跑 MC); **escalate-don't-hack**(放不下/过不了门 → 上报 human, **绝不改三层蒙混**)。
- 每迭代落 `iteration_NN/`(geo + proxy/overlap/verify json + 一行 verdict), 可恢复。

══════════════════════════════════════════
TASK & 目标(详见 CONSTRAINTS_PROMPT511.md, 以那份为准)
══════════════════════════════════════════
最小侵入地**新增一层被动高 Z 金属屏蔽(W/Ta/Pb, 非闪烁体)**, 放在**室温真空夹套内侧(r~12)在源头截 511**, 把 prompt 压到 ≤ old(0.0323), **同时 delayed 不抬(净账≤+10%)**, 信号保持≥0.99。
```
minimize 侵入度(不改三层>加质量小>厚度薄)
s.t. PROMPT≤0.0323(显著性) ; DELAYED≤baseline·1.1(净账,必MC) ; SIGNAL≥0.99 ; 三层禁改 ; overlap=0 ; 归一化一致
search 材料{W/Ta/Pb}×厚度×半径×覆盖×信号口 ; 别钦定W(W β⁺活化多可能抬delayed) ; 报 Pareto, human 选点
```
三层禁改(CRITICAL): `TES_*`(探测核心)、`Cu_ColdFinger_*`(导热)、`Cryoperm_*`(磁屏蔽)。**delayed 净账 = (+屏蔽自活化β⁺→511到TES) − (−被屏蔽挡掉的外层delayed-511), 符号未知, 必须 delayed 输运 MC。**

══════════════════════════════════════════
START
══════════════════════════════════════════
先交 CHECKPOINT 自证。通过后开 Iteration 1: 以变体 B(W衬@r11.9-12.8)为种子过 G0/G1/G2/G2.5; 同时让 Builder 准备 Ta/Pb 与 1-2 个厚度档以便后续扫 Pareto。任何一步红灯 → 退回该步, 不前进。
