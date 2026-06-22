# GUIDE — prompt-511 几何修复(返工指令 + Loop-Engineering 框架)

收件: Codex · 发件: Claude (Opus 4.8) 评审后 · 日期: 2026-06-20
原始几何**完好**: `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/`(172 体, 无 collar, 罐/Cryoperm/冷指未压缩)。**从它开始, 不要改它本体。**

---

## 启动清单与顺序(Codex 从这里开始 —— 所有需要的文件都在下表)

仓库根 `/home/ubuntu/TES_511_Balloon`。**严格按"序"列执行**;`动作`列说明读/跑/禁改。

| 序 | 文件 / 目录 | 角色 | 动作 |
|---|---|---|---|
| 0 | `core_md/PRE_PROMPT_CODEX_PROMPT511.md` | 启动器(用户已粘贴它把你拉到这) | 已触发, 无需再读 |
| 1 | `AGENTS.md`(仓库根) | 会话级强制指针 | 读一次 |
| 2a | `core_md/Project_Memory.md`, `core_md/README.md`, `core_md/workflow.md` | 项目总览(仪器/流水 step00–09) | 读一次, 取要点 |
| 2b | `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo` | 参考(低 prompt)厚 CsI 阱设计; old 总 prompt 0.0323 | 浏览(⚠️ 别用 step01 的 CeBr3 过时快照) |
| 2c | `core_md/CLAUDE_PROMPT511_SIDEPORT_GAP_CLARIFICATION_20260620.md` + `outputs/reports/prompt511_entry_audit_20260617/prompt511_entry_audit.md` | 根因(511 在 r≥13.3 夹套出生→内飞 TES; baseline eplus 0.0543) | 读一次 |
| 2d | `core_md/CLAUDE_REVIEW_ACTIVE_CSI_COLLAR_20260620.md` | 上一版为何退回(冷区闪烁体+压缩 DR) | 读一次 |
| 3 | **本 GUIDE**(背景 + loop 框架全文) | 读一次的"为什么" | 完整读(就是本文) |
| 4 | `core_md/CONSTRAINTS_PROMPT511.md` | 每轮强制的契约 + 目标函数 + 三层点名 | **每轮重读 + 注入每个 subagent** |
| 5 | `code/tools/check_prompt511_constraints.py` | 硬门(三层/冷区闪烁体/归一化/overlap/`--results`) | 每迭代**跑** |
| 6 | `code/tools/recompute_rates.py` | 独立重算归一化/抑制/显著性 | Verifier **跑** |
| 7 | `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/` | 基线 | **禁改**, 只作新增屏蔽的母本 |
| 8 | `outputs/geometry/DEMO2_DR_v3p5_jacket_W_liner_variantB_megalib_proxy/` | 干净种子(W 衬 @r11.9–12.8, overlap-clean) | Iteration 1 起点 |

**启动顺序(一句话流程)**: 0 已触发 → 读 1,2a–2d 建立背景 → 读 3(本 GUIDE)懂框架 → 读 4(CONSTRAINTS)拿红线 → **交 CHECKPOINT 自证**(见 PRE_PROMPT)→ 用 5/6 脚本上门禁 → 以 8 为种子开 Iteration 1, 禁碰 7。脚本(5/6)是"每轮跑"不是"读一次"; 契约(4)是"每轮重读+注入 subagent"; 其余(1,2,3)是"读一次建立理解"。

## 0. 一句话任务

把 prompt-511 侧口本底(eplus 0.0543 cps, ~87% 头条)用**几何**降到 ≤ old new_geo_re(总 prompt 0.0323)量级, **不用 ROI/源把戏**, 不削信号(≥ Laue 焦斑), 并通过 MC 四项净账。

## 1. 根因(已定位, 勿重查)

大气 e⁺ **几乎全部在 r≥13.3 的真空夹套(室温外层)就地湮灭**出 511(出生半径 10 分位=13.3), 朝内直奔 TES(r≈3, z=-5.2)。侧入设计把 old 那根厚 CsI 侧屏蔽换成了薄铝, 所以漏。证据: `outputs/reports/prompt511_entry_audit_20260617/`。

## 2. 上一版(active-CsI collar)为什么要返工 —— 必须纠正的 5 点

1. **不要在制冷机冷区放闪烁体当 active veto。** 你把 4 个 CsI 环放在 r4.25–5.95(探测器冷级)。常规闪烁体 veto 在 mK/4K **无法工作**: 光电读出(PMT 冷端失效 / SiPM 热负载+冷电子学)、光纤引出 DR、CsI 低温光产额下降。冷区闪烁体 bolometer 虽存在(CUORE/CUPID)但是 ms 级慢响应、给不了快反符合。→ **veto 不可实现时, 那圈 CsI 退化成低密度被动吸收体(ρ=4.51, 1.7cm 仅 ~50%), 没理由用闪烁体。**
2. **不要为塞屏蔽去压缩探测器/DR 硬件。** 你(经上游 repack)把 50mK 罐(6.8→3.25)、Cryoperm 磁屏蔽(6.3→3.25)、冷指(1.54→0.18)压缩了, 且**完成审计未披露**, 磁屏蔽/热路径功能影响未评估。**禁止改动任何既有探测器/DR 体。**
3. **抑制比不要把两个改动混在一起。** 你的 2.1× 是 (原始 baseline) vs (压缩+环), 没隔离环的净贡献。
4. **统计太低。** ~19–25 条线事件, 2.1×±0.5, "低于 old"在 ~1σ 内 —— 只能说"同量级"。
5. **"吸收 e⁺"不等于消灭 511。** e⁺ 停在屏蔽里**就地湮灭**出 511(瞬发, 与活化无关)。被动屏蔽挡不住自己产的残余。

## 3. 正确方案(照此做)

**被动高 Z 金属套筒, 放在室温真空夹套内侧, 在源头截 511, 不碰冷区、不碰 DR。**

| 设计项 | 要求 |
|---|---|
| 材料 | 高 Z 被动金属(W: μ/ρ=0.137@511, 0.9cm≈91%; 或 Ta)。**非闪烁体。** |
| 位置 | 真空夹套内侧 **r≈11.9–12.8**(60K 壳 11.6 与夹套 12.9 之间的**空真空夹层**, 室温、已验证该处所有 φ 为空) |
| 拓扑 | 近 4π 套筒包住 TES 视线, **仅在信号锥开口**(φ≈180=-x, z≈-5.2) |
| 厚度 | 面密度够厚**自吸收自身瞬发湮灭 511**(~17 g/cm² 给 90%); 让 e⁺ 停在远 TES 外侧 |
| 信号口 | ≥ Laue 焦斑(探测器耦合 r99=1.22cm, max=1.70cm; 几何上别削) |
| 活化 | 尽量低 β⁺ 活化材料(次要, 可标定) |
| 禁止 | 改原始 baseline 任何体; ROI/spot/PointSource/HomogeneousBeam; 冷区放闪烁体 |

参考已建并 overlap-clean 的样板: `outputs/geometry/DEMO2_DR_v3p5_jacket_W_liner_variantB_megalib_proxy/`(W 衬 @r11.9–12.8, proxy 预测 ~96% 命中)。可直接接手跑 MC, 或按上表自建。

## 4. 验收门(全过才算完成 —— "done"定义)

- **G-norm**: SurroundingSphere=60 不变; collar 与 baseline 同 flux×area; `rate_per_event` 自洽(查 ×8-bug 区)。
- **G-prompt(MC)**: eplus prompt 实测降到 ≤ old 量级; 统计足够(目标 ≥ baseline 的 rep 数, 抑制比误差 < 25%)。
- **G-addback(MC)**: 套筒**自身瞬发湮灭 511** 的净账(加回项已含在残余里, 不是只看吸收)。
- **G-neutron(MC)**: 高 Z 增产次级中子的净效果。
- **G-delayed**: 新增活化(β⁺/511)估计, 不恶化 delayed。
- **G-signal**: step09 焦斑 replay, 信号保持 ≈1.0。
- **G-disclosure**: 审计列出**相对原始 baseline 的全部几何 delta**(应只有"+套筒", 无任何探测器体改动)。

---

# Loop-Engineering 框架(用 2–3 subagent, 有约束有检查)

> 设计目标: 让迭代**收敛而非空转**, 让 subagent **不能给自己打分**, 让昂贵步骤(MC)**只在便宜预测通过后才花**, 让"被卡住"**上报而不是偷改几何蒙混过关**(上一版压缩 DR 就是偷改的反例)。

## 角色(职责分离 = 防自评)

- **Orchestrator(主线程)**: 持有 `CONSTRAINTS.md`、状态、门禁、停止决策。**自己不建几何。** 只派活、收结构化证据、过门、决定 继续/重设计/上报。
- **Subagent A = Builder**: 窄任务——按约束实现"下一步改动"+ 便宜自检(overlap=0, predict-proxy 命中率)。产出 artifacts + 结构化结果(数字+pass/fail)。
- **Subagent B = Verifier(对抗性)**: **只看 Builder 的 artifacts, 不看其推理**, **独立重算**关键数(归一化、命中率、信号保持), 主动猎杀已知失效模式(×8 归一化 / 混账 / 未披露改动 / 冷区闪烁体 / 自湮灭 add-back 漏算)。签字或否决。
- **Subagent C = Runner(可选, 仅设计门全过后)**: 跑 MC + 四项闭环。

## 阅读模型(理解 vs 红线 —— 读一次 ≠ 读全部 ≠ 不读)

门禁只防"做错", 给不了"理解"; 只懂约束不懂背景的 agent 会产出"过门的废设计"。所以分两种节奏:

- **Phase 0 — Onboarding(读一次, 只 orchestrator)**: 开工前**完整读一次本 GUIDE**(根因 + 为什么上一版错 + 为什么选室温夹套), 建立全局理解。这是"为什么"。
- **每轮 — 约束强制**: 短 `CONSTRAINTS_PROMPT511.md` 由**脚本门 + prompt 注入**每轮强制。这是"红线"。
- **冷启动 subagent 的关键动作 = 上下文蒸馏分发**: subagent 是冷的, orchestrator 读过不等于它读过。**不要让 subagent 去读全部 core_md**(贵且不可靠); orchestrator 把"它那一步需要的背景"**蒸馏成一段 task brief 注入它的 prompt**(相关"为什么" + 约束全文 + 窄任务 + 输入路径)。
- 三档取舍: ❌ 每 agent 反复读全 core_md;  ❌ 谁都不读只靠门;  ✅ **orchestrator 读一次→蒸馏分发→约束每轮强制。**

## 单次迭代流水(便宜→昂贵, fail-closed)

```
PLAN ─▶ BUILD(A) ─▶ SELF-CHECK(A) ─▶ VERIFY(B 独立重算) ─▶ GATE ─▶ {advance | redesign | escalate}
                                                                │
              每道门红 = 不准前进; 红在哪退回哪一步, 绝不为过门去改受保护结构
```

## 这是优化, 不是 pass/fail(目标函数 + 设计空间 + Pareto)

```
minimize   侵入度 (不改三层 > 加质量小 > 厚度薄)
s.t.       PROMPT ≤ old 0.0323(统计上, 见显著性) ; DELAYED ≤ baseline·1.1(净账, MC) ;
           SIGNAL_keep ≥ 0.99 ; 三层禁改 ; overlap=0 ; 归一化一致
search     设计空间 = {材料 W/Ta/Pb} × {厚度} × {半径(室温夹套~12)} × {覆盖立体角} × {信号口}
           建议序: 固定位置@夹套内侧 → 扫厚度命中 PROMPT → 查 DELAYED 净账 → 不达标则换材料(低β⁺)/调厚 → 报 Pareto
output     Pareto 前沿(每点: 材料/厚度/质量/prompt/delayed/signal), human 选工作点
```
**别钦定 W**: W 紧凑(prompt 好)但 β⁺ 活化多可能抬 delayed; Ta/Pb 可能 delayed 更友好。让 Pareto 说话。

## 门禁(便宜在前, 贵在后; 每道有脚本)

| 门 | 阶段 | 通过条件 | 工具 / 谁查 |
|---|---|---|---|
| **G0 约束+三层** | 静态 | 不改三层(`TES_/Cu_ColdFinger_/Cryoperm_`)与任何 baseline 体; 无 ROI/PointSource | `check_prompt511_constraints.py` (A+B) |
| **G1 几何 sanity** | 便宜 | `cosima CheckForOverlaps`=0, 可加载 | A |
| **G2 prompt 预测** | 便宜 | proxy-ray 在 80 漏 511 命中 ≥90%; 信号口 ≥ 焦斑 | A 出, B 独立复算 |
| **G2.5 delayed 预筛** | 便宜 | isotope-store smoke + β⁺ 清单: 仅"自活化"项已超 +10% → 早杀 | A 出, B 复核 |
| **G3 MC + 归一化** | 贵 | prompt 实测 ≤ old(显著性); flux×area/rate_per_event 自洽 | C 跑, B 用 `recompute_rates.py` |
| **G-delayed** | 贵 | **delayed 净账** ≤ baseline·1.1(自活化 − 挡掉外层 delayed, 必 delayed 输运) | C 跑, `--results` 门 |
| **G-signal** | 贵 | step09 焦斑 replay, 信号保持 ≥0.99 | C 跑, `--results` 门 |
| **G4 闭环+审计** | 贵 | 自湮灭 add-back/中子/delayed 全过; 全 delta 披露; B 签字 | B |

**关键纪律 1 — predict-before-spend**: G2 **和** G2.5(prompt 预测 + delayed 预筛)都不过, **绝不进 G3 跑昂贵 MC**。根治"做无效 smoke / 花 MC 跑错位置"。
**关键纪律 2 — 诚实结局**: 若扫遍设计空间, Pareto 前沿为空(没有被动屏蔽能同时满足 PROMPT 与 DELAYED 而不改三层)→ **停, 上报 human**(换材料预算 / 加质量预算 / 架构回轴入)。**绝不为过门去改三层。**

## 约束契约 `CONSTRAINTS.md`(每个迭代开头重读, 不靠记忆)

写死这些不变量, 每道门对照检查:
1. 不改原始 baseline 任何既有体(只允许新增屏蔽体)。
2. 屏蔽=被动高 Z 金属, 不在冷区放闪烁体。
3. 信号口 ≥ Laue 焦斑(r99=1.22, max=1.70cm)。
4. 同 SurroundingSphere/flux×area; 归一化自洽。
5. G2 不过不跑 MC。
6. 成功判据=四项 MC 闭环 + 信号 + 全披露, 不是只看 prompt。
7. 被卡住(放不下/过不了门)→ **上报 human**, 不得压缩/删改受保护结构蒙混。

## 状态与可恢复

每迭代写 `iteration_NN/`(geo + proxy json + overlap log + verify json + 一行 verdict)。loop 可从最后通过的门续跑。`MANIFEST.json` 记每步 delta 与门禁结果。

## 停止条件

- **成功**: G0–G4 全绿 + Verifier 签字。
- **失败/上报**: 达 max-iter, 或出现"必须改受保护结构才能继续" → 停, 把权衡摆给 human(例如 mass/cryo 预算 vs 架构是否该回轴入)。

---

## 附: 给 Codex 的最小起步序列
1. 读本 GUIDE + `CONSTRAINTS.md`; 确认 baseline 完好。
2. Builder: 在新目录, 原始 baseline + W 套筒@r11.9–12.8(或接手 variantB), 过 G0/G1/G2。
3. Verifier: 独立复算 G2 命中率与归一化口径。
4. G2 绿 → Runner 跑 eplus prompt MC + step09 信号 + 自湮灭/中子/delayed。
5. Verifier 过 G3/G4 并签字; Orchestrator 写披露审计(全 delta)。
