# S3d-O8 thermal-Cu rethink：冻结的最终 prompt 判决

> **2026-08-14 联合门最终更新：** `BG_J4_JOINT_GATE_REVIEW.md` 已复算联合式并用
> actual sibling IA 证伪其物理前提。4-cm 方案要求 delayed 有效 BGO 耦合
> `q>=91.6767%`；实测只有 `8.439%` mission counts 有 `>50 keV` escape gamma，
> `10.593%` 到达 current-BGO/outer-region proxy。因此 `BG-J4` 作为统一系统候选 KILL，
> 不能用 418 条纯 CSG 相交射线领取 `D exp(-0.985L)`。本文件原 `BG-TAU5+BPE-O`
> 仅保留为 physics-defined conditional topology，flight-admissible verdict 仍为 NONE。

## Answer first

**Flight-admissible verdict：`NO_ADMISSIBLE_PROMPT_CANDIDATE`，当前不要启动 transport。**

**Physics-defined conditional optimum：`BG-TAU5 + BPE-O`。** 其中 BG-TAU5 是现有 BGO detector/readout channel 的全周新增 active optical depth，要求非 relief 的 4--8 MeV 直线 `Delta tau_BGO >= ln(5)`；`BPE-O` 是 delayed 团队若需要的外置 BPE，必须在 BGO 外侧，prompt 账领取零收益。它是唯一在物理上不依赖 cold-core partner escape、三事件方位或 pair-host 材料的方案。

二者不是矛盾：BG-TAU5 是**物理定义的条件最优**，但简单全包尺度约增加 `0.61 t` BGO、还需迁移 outer Kapton/Al/BPE/plastic/support；在没有 balloon payload/envelope、现有 BGO readout、结构和 self-activation authority 前，它不是**flight-admissible geometry**。

新冷盘边界允许的 25% 外径缩小、10% 厚度减少和少量 M4 孔只能作辅助敏感性，prompt suppression 记为零。`TC-SK1`、`DR/Ag standoff`、`Nb/Mu standoff`、`+1--3 cm BGO + standoff`、Cu→Al 和 mK guard 全部冻结为 `KILL`。

## 1. 为什么较小 BGO + pair-host standoff 在理想式中看起来可行

若错误地假设 pair production rate 不变、annihilation 近似各向同性、TES projected area 不变，则 pair-to-TES coupling 可写成 `C_Omega ~ 1/d^2`。和新增 BGO primary factor 相乘：

`R_prompt ~ exp(-0.276 Delta L_BGO) * (d0/d1)^2`。

要求 `R_prompt<=0.20` 得到：

| added BGO (cm) | primary factor | required `C_Omega,new/C_Omega,old` | required `d1/d0` |
|---:|---:|---:|---:|
| 1 | 0.759 | <=0.264 | >=1.948 |
| 2 | 0.576 | <=0.347 | >=1.697 |
| 3 | 0.437 | <=0.458 | >=1.478 |

真实 ANNI-to-TES distances 是 3883 `5.071 cm`、19932 `6.941 cm`。所以 +3 cm BGO 的最乐观 standoff target 分别为 `7.495 cm` 与 `10.259 cm`，增加 `2.424/3.318 cm`。机读量在 `standoff_solid_angle_scaling.csv`。

这只说明 ideal product 可以过 0.20，**不证明工程或 transport 可以做到**。它漏掉了最关键的 production term：

`R_pair-to-TES = [sum_j T_before,j * P_pair,j * C_TES,j]_candidate / [same]_baseline`。

移动或加厚 host 会同时改变 `P_pair`、上游透射和 host identity；磁壳为保持 shielding 而加厚/加第二层还会增加 Nb/Mu pair opacity 与 activation mass。因此不能只用 `1/d^2`。

## 2. 真实几何已经证伪 standoff

几何证据来自 `agents/geometry/FINAL_THERMAL_CU_GEOMETRY_REVIEW.md` 与 `FINAL_GEOMETRY_NUMBERS.csv`：

- 当前 Mu-metal closed shell 外半径 `4.45 cm`，中心 `z_IF=-5.2 cm`；上方到 MXC plate 仅 `0.45 cm`，下方到 50-mK can bottom 仅 `0.05 cm`。
- 同心壳半径受 MXC plate 限制在约 `<4.9 cm`。`R=8--10 cm` 会直接穿 MXC plate；向下移又会穿 can bottom、多层 shield caps 和现有 W bottom plate。
- DR Cu/Ag 单体达到 8/10-cm standoff 需横向偏置 `4.786/7.677 cm`。计入 CuNi、NbTi 与 G10 后包络为 `12.536/15.427 cm`；前者占据 r=6--9 cm rods/service，后者超过 R=15 cm cold-plate envelope。
- 单移 DR 不消除 3883/8081 的 Nb roots，也不消除 19932 的三块不可约 cold-plate Cu chord。

prompt lineage 还给出直接 host-migration falsifier。若移除 19932 当前 DR-Cu host，其原 primary 继续前进会依次穿：

- `0.991 cm Ag proxy`；
- `0.917 cm MXC Cu plate`。

这两个 host 比当前 ANNI 点更靠近 TES，且在 5.77 MeV 都有不可忽略的 pair opacity。此前 LC1 已实测简单减 Cu 后 pair 总数近似不变、host 迁移。故 `DR center thinning/annularization` 不能领取 `1/d^2` 收益。

最终判决：

- `DR Cu/Ag standoff + 1--3 cm BGO`：`KILL`；
- `Nb/Mu closed-shell standoff + 1--3 cm BGO`：`KILL`；
- `+1--3 cm BGO alone`：`KILL FOR 0.20`。

## 3. 冷盘允许改动的冻结处理

最激进地使用允许边界，三条 sibling 的 Cu-only survival 从 `0.113/0.052/0.251` 只变到 `0.230/0.0597/0.283`。最终等权根中，19932 改善约 15%；即使另一根完全消失，prompt survival 下界尺度仍是 0.5。

因此最终候选中：

- cold-plate outer diameter、thickness 与 M4 holes 保持 baseline 最适合单因果 prompt test；
- 如果热/结构团队后来使用允许的 25%/10% envelope，必须视为辅助变化；
- prompt budget 对它记 `suppression=0`，直到 combined paired transport 给出净 rate；
- 不允许按 3883/19932/8081 的射线位置选择 M4 hole。

## 4. BG-TAU5 + BPE-O 的 prompt 必要门

### Geometry / ordering

1. 新增 BGO 必须属于现有 detector/readout channel；不新增 detector、scorer 或读出。
2. 对 complete gamma denominator 中所有会到达 cold-core envelope、且不穿 immutable relief 的 4--8 MeV INIT rays，用候选自己的材料系数计算 `Delta tau_BGO(E,ray)`；最小值必须 `>=ln(5)=1.609438`。
3. 5.77-MeV 参考厚度为 `Delta L≈5.831 cm`，但最终门是 optical depth，不是把单能系数冒充整个谱。
4. 若统一候选含 delayed BPE，BPE 必须位于 BGO 外侧。对由内向外的 annihilation sibling，顺序必须是 `cold core -> BGO -> BPE`；BPE 不得先散射 partner。prompt 对 BPE 领取零 suppression，并独立记录它产生的 capture gamma/secondary。
5. frozen signal EventList 对新增 BGO/plastic 的 active chord 必须为零。

### Relief denominator

top 的 12 个真实 service relief、6 个 NF2 relief，以及 side/bottom 的 immutable window/relief 不能从分母删除。使用原始 `3,207,738` gamma INIT histories，至少输出：

- `N_incident(E,mu,az,G_active)`；
- `N_core_aim`：直线进入预登记 cold-core envelope；
- `N_relief_core`：因 immutable relief 使 `Delta tau<ln(5)` 且仍进入 core envelope；
- `N_covered_core=N_core_aim-N_relief_core`；
- 各类的 pre-W2、veto leak、Step05、权重与 Neff。

令 `f_relief=N_relief_core/N_core_aim`，covered 与 relief 的 candidate/baseline survival 分别为 `s_covered`、`s_relief`。总门是

`s_total=(1-f_relief)*s_covered + f_relief*s_relief <=0.20`。

因此 `Delta tau>=ln(5)` 只在 covered rays 上刚好给 0.20 时，没有任何 relief 余量。实际候选必须靠更大的 covered optical depth 留出 relief budget，或证明 relief rays 不进入 pair-capable core；不能把 relief 标成“工程孔”后排除。

### Transport / statistics

1. 首先做 baseline vs BG-TAU5(+BPE-O) paired gamma mechanism；cold core 完全相同，隔离 BGO 因果。
2. 分别输出 active BGO any interaction、deposit、`>=50 keV` veto；不能用 `1-exp(-tau)` 冒充 gate efficiency。
3. 输出 BGO 内 pair/Compton 后逃逸的 gamma/electron/neutron、冷芯 first-pair/ANNI host 与 TES ancestry。
4. full corrected-gamma final prompt candidate/baseline exact one-sided 95% upper 必须 `<=0.20`，包含 relief histories。candidate=0、equal exposure/equal weight 时 baseline 至少需 17 个 final events；否则用准确 rate-ratio interval。
5. 保持 `geometry x mode x family` TT/weight normalization boundary，单列高权重事件与 Neff。

门的机读版在 `bgo_tau5_candidate_gates.csv`。

## 5. Physics optimum 与 flight admissibility

| level | verdict | meaning |
|---|---|---|
| Physics-defined topology | **KEEP BG-TAU5 + BPE-O, conditional only** | 唯一能在不改变 cold-core host 的情况下给 primary 约 5 倍 optical-depth suppression；BPE 只服务 delayed。 |
| Geometry feasibility | **UNKNOWN / currently not certified** | 简单全包增量约 613.5 kg，还需外移 outer layers/support，并处理所有 relief。 |
| Prompt performance | **UNKNOWN** | 必须通过含 relief 的 exact ratio upper `<=0.20`。 |
| Delayed performance | **UNKNOWN** | 新 BGO 的 production Bq、secondary 与 W2/Bq coupling 必须进入联合预算；外置 BPE 不自动等于净改善。 |
| Flight-admissible candidate today | **NONE** | 缺 payload/envelope、结构、readout、BGO self-activation authority；P0 未过，不应启动 transport。 |

**唯一重开条件：** 用户/工程 authority 明确认可约 0.61-t 量级 active-BGO envelope（或给出满足同一 `Delta tau` 门的更轻真实 CAD），并提供现有 channel/readout、结构和 payload 边界。通过后才值得做 focused transport；否则最终状态保持 `NO_ADMISSIBLE_PROMPT_CANDIDATE`。
