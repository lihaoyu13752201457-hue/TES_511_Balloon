# prompt-511 侧口本底:对"缝隙/建模过切"说法的澄清与纠正

日期: 2026-06-20  ·  作者: Claude (Opus 4.8)  ·  状态: `CLARIFICATION_EVIDENCE_BACKED`

## 0. 这份文档要回答的问题

在与 Codex 的讨论里出现了一个收敛性结论,被概括为:

> "current(v3p5 侧入)相比 new_geo_re,是因为**建模错误/过切**——侧窗没用曲面拓扑、
> 用平面代替,**留下了一小块完全没有窗、也没有被动屏蔽材料的缝隙,光子全然漏光**;
> old 上窗因为是平面所以没有这个问题。"

这个概括**大方向对、但最后一步的物理图像不准确,而且潜在结论很危险**。本文把它拿到磁盘
证据上逐条核对并纠正。所有数字均可复现,出处见 §5。

## 1. 一句话结论

- ✅ **对**:问题在**侧口扇区的"壁"**,不在窗箔;old 顶入也有壁泄漏,差别不是"有窗 vs 没窗"。
- ❌ **错/不准**:不是"**完全没有材料的缝隙 / 全然漏光**",也不是"**建模错误/平面代替曲面**"。
- ⚠️ **最重要**:本底是**真实的**(A_eff 真实翻倍),不是仿真 artifact。叫它"建模错误"会
  误导出"真实设计没事、改改仿真就行"的危险结论。**根因是真实的屏蔽拓扑缺失:侧口扇区里
  薄铝低温壳取代了 old 的厚 CsI 实心屏蔽柱。**

## 2. 讨论里"对"的部分(证据支持)

| 论点 | 证据 | 数值 |
|---|---|---|
| old 顶窗也有壁/非窗泄漏,差别不是"窗" | `prompt511_old_vs_v3p5_decomposition_summary.json` | old 窗漏 0.00231 / 壁漏 0.02217 cps;两边窗都 ~0.001–0.002 |
| 差别是侧口把更强的壁源放到对 TES 的短/直路径上 | 同上 (by_region) | v3p5 壁漏 0.0523,其中侧口侧壁 0.0414 cps(76%,61 ev) |
| 侧口确实在 φ 方向切掉了一段壳体 | 几何 `*.geo` 的 `side_port_band_00/01` | 每层壳被切成两段圆弧,中间留 **27.58° 的口**(z 限定 ±1.95cm) |

侧口尺寸的几何事实(以 Still 壳为例,其余层同构):

```
band_00.Shape PCON 0.025      166.187558 2 -1.95 8.5 8.6 1.95 8.5 8.6   → φ∈[0.025°, 166.21°]
band_01.Shape PCON 193.787442 166.187558 2 -1.95 8.5 8.6 1.95 8.5 8.6   → φ∈[193.79°, 359.97°]
                                                          缺口 = [166.21°, 193.79°] = 27.58°,居中于 180°(−x 视轴)
```

## 3. 讨论里"错/不准"的部分(证据反驳)

### 3.1 不是"完全没有材料的缝隙",也不是"全然漏光"

- 那 27.58° 的口里**有薄窗箔**(Be 0.015cm + 数层 Al foil,见 raytrace `current_side_axis_window_only`:
  `Be:0.015; Aluminium:0.013`),不是真空空洞。
- **更关键:主泄漏(96% 的壁项)根本不走那个口。** 这些 511 是**出生在实打实的薄铝壁里**,
  随后被衰减、**幸存**穿到 TES——不是"穿过一个洞"。证据:
  - 80 个选中 prompt-511 的出生体积全部是**铝**结构:
    `Vacuum_Jacket_Al_266mmClass_side_port_side_wall`(31 ev, r≈13.3),
    `Outer_Al_Mechanical_Shell_detector_bay_*`(13+11+8+5+5 ev),仅 1 ev 在 `Passive_Cu_Liner`。
  - 几何里这些 `side_port` / `side_wall` 体积的 `.Material` **全部 = Aluminium**(已逐行核对)。
  - 材料账(`prompt511_material_ledger_summary.json`,current_selected 32 ev):511 路径在
    **Aluminium 里共沉积 ~9397 keV**(≈294 keV/ev),Cu 24.5、W 0.8 keV。它们是穿铝被衰减的
    **幸存光子**,不是真空直冲。

> 机制定性:**薄屏蔽透射**(thin-shield transmission),**不是材料缺失的空洞漏光**。

### 3.2 不是"平面拓扑代替曲面"

- 几何里这些壳全是 `PCON`(polycone,**绕轴的回转曲面**);侧口是**圆弧扇区**(φ 起止角),
  不是用平面去切。"没用曲面、用平面代替导致缺口"这个描述对不上几何。
- 缺口在 z 方向也是**有界**的(band 体积 z 半高 1.95cm);band 之外(`above/below_side_port`)
  壳是完整 `PCON 0 360`。所以是一个**有界的圆弧窗口**,不是无限长的平面切缝。

### 3.3 不是"建模错误",本底是真实的(最重要)

- A_eff(e⁺→W2 511)从 0.209 真实涨到 0.465 cm²(×2.22),远场归一化已核实自洽抵消——
  **真实翻倍,不是 bug、不是归一化假象。**
- 因此**不能叫"建模错误/过切"**:那会误导出"真实硬件没事、只要修仿真几何"的结论。
- **真实根因(设计后果)**:45° 侧入把 old 那根**实心厚 CsI 侧屏蔽柱**,在侧口扇区换成了
  **薄铝低温壳**。沿同一条侧轴对比(raytrace `*_side_axis_centerline`):

| 沿侧入轴到 TES | current(v3p5) | old(new_geo_re) |
|---|---|---|
| 材料 | Cu 0.35 + Be 0.015 + Al 0.013 cm | CsI 4 + Cu 3.5 + 低碳钢 1.69 + Al 1.22 + 不锈钢 0.5 + W 0.06 cm |
| 面密度 | ≈ **3.2 g/cm²** | ≈ **71 g/cm²** |
| 511 透射 | ≈ **76%** | ≈ **0.24%** |

### 3.4 old 为什么没事——不是"因为是平面"

old **压根没有侧开口**(整根侧桶是连续实心 active-CsI;SurroundingSphere=35,0 侧开口),
窗在顶上,残差是另一条**顶/轴向** outer-Al-shell 项(0.0203 cps,88/106)。所以 old 是
"**实心屏蔽 + 一个入口**"的拓扑,跟"平面"无关。

## 4. 正确的物理图像与最小修复

**图像**:侧入窗口本身没问题(窗漏仅 0.002 cps,4%)。问题是侧口扇区把 old 的厚 CsI 屏蔽
柱整段替换成了薄铝低温壳——大气 e⁺ 在这些近探测器薄铝壁里湮灭出 511,只隔薄铝(或那个
开着的信号孔径)就能打到近轴 TES(r≈2–3.5, z≈−5)。这是**真实的屏蔽拓扑缺失**。

**最小修复**(不是"补一个建模漏掉的洞",而是恢复面密度):
在侧口立体角、TES(r≈3)与发射体(r≈13–19)之间补 **~27 g/cm²**(=1.4cm W / 3.8cm BGO /
6cm CsI / 10cm Al),**只在信号孔径(≈28° φ 带 @ z=−5.2)留空**。
→ prompt 0.0543 → **~0.013 cps,低于 old 0.0245,无需 ROI**。
CsI/BGO 兼作 active veto(= old 做法)。

**仍需 MC 闭环的告警**:① 屏蔽自身 e⁺ 湮灭 511 的 add-back;② 新增 Cu/W/CsI 的延迟活化
(BGO 教训)。解析 ~27 g/cm² / Z 改善为上界,未经 MC,不得作权威口径。

## 5. 可复现证据(repo 内)

- 分解脚本/产物:`outputs/reports/prompt511_entry_audit_20260617/build_old_vs_v3p5_prompt_decomposition.py`
  → `prompt511_old_vs_v3p5_decomposition_summary.json`
- 出生体积/泄漏类:`current_eplus_prompt_final_records.json`(80 ev)、`old_eplus_prompt_final_records.json`(106 ev)
- 沿轴材料对比:`prompt511_raytrace_line_chords.csv`(`current/old_side_axis_centerline`、`current_side_axis_window_only`)
- 材料账:`prompt511_material_ledger_summary.json`(`current_selected` cc_edep_by_material)
- 几何:`outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo`(`side_port_band_00/01`、各 `side_wall` 体积 `.Material Aluminium`)
- 前序定位/修复评审:`core_md/CLAUDE_PROMPT511_SIDEPORT_FIX_REVIEW_20260617.md`(本文是对其中"缝隙/过切"措辞的澄清,不改其根因结论)
