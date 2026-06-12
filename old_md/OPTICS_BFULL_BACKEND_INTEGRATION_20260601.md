# 前端聚焦光学(B-FULL Laue)→ 后端探测器系统:集成交接 Prompt

> 时序标记 **20260601**。本文件是给后续执行 AI(如 Codex)的**有序可执行指令**:
> 记录 2026-06-01 对聚焦光学的审阅+修复、当前"未接入主链"的真实状态、
> **从哪里搬运前端聚焦、如何桥接、归一化怎么对、验收标准**。
> 关联:`OPTICS_BFULL_TEMP_MEMORY.md`、HTML 报告
> `stepwise_maintenance/step04_opticsim/laue_review_20260601.html`、
> `/home/ubuntu/cross_check_laue/laue_lens_review_log.md` 条目 11。

---

## 0. 一句话目标

把**聚焦光学(opticsim B-FULL Ge(111) Laue 镜)作为源生成器**,产生**真实聚焦 PSF 相空间**,
替换主链现在的占位科学源 `HomogeneousBeam(r=1.8cm)`,跑**全量 Cosima 探测器输运**,
让 Step08 显著性建立在 **detector-coupled 聚焦响应**上,而不是均匀盘近似 + 空间 proxy。

这正是 0531 review 里 `P1_FOCUSED_SPOT_SPATIAL_PROXY`(PARTIAL_L1,"Detector-coupled focused-spot
PSF transport ... still not run")要闭合的那条。

---

## 1. 2026-06-01 已完成的审阅与修复(前置事实,勿重复)

**物理审阅(详见 `laue_review_20260601.html`)**:B-FULL 底层衍射物理正确并被三个真独立外锚
锚定(Barrière 2009 实测 <1.6%、CRYSTAL diff_pat ~4%、Kohnle 1998 <1.4%)。

**已实施并在 Geant4 11.4 实测验证的修复**(改的是 `/home/ubuntu/opticsim/geant4_app/src/laue_multiring_bfull_demo.cc`):
1. **吸收双重计数**:外部 XOP 曲线喂衍射 MFP 前改用无吸收效率 `R/(1-A)`(EM 只吸收一次)。
2. **`G4VEmProcess` → `G4VDiscreteProcess`**:旧版在 G4 11.4 崩 `em0002`,改后可在 10.2/11.4 跑。
3. **验证门控**:summary 新增 `emergent_focal_diffraction_fraction` vs `analytic_reference_focal_diffraction_fraction`(在线 0.1%、外部 map −3.2%)。

**Step09 交接修复(本仓库内)**:Step09 原来桥接 `phase_space.csv`(6358 行=解析投影,**高估 28%**),
已改为桥接 **`focal_crossings.csv` 里 `source_tag=laue_bfull_diffracted` 且落在 Be 窗内的真实穿越(4968 行)**。
Step04 审计、Step08 best-cut、validator 已同步。当前 `validate_new_geo_re.py` = 19/19 PASS。

> 不变量:**下游永远用 tracked 焦面穿越(focal_crossings.csv),不用 phase_space.csv 投影。**

---

## 2. 当前集成状态(三层,务必看清"差哪一层")

| 环节 | 状态 | 证据 |
| --- | --- | --- |
| 光学 → 聚焦 EventList | ✅ 已做 | `step09_optics_bridge/outputs/eventlists/Opticsim_laue_new_geo_re.eventlist.dat`(4968 行,纯光子 ptype=1) |
| EventList → Cosima 探测器输运 | ⚠️ 仅 1000-event **smoke** | `runs/step09_optics_bridge/..._smoke1000.inc1.id1.sim.gz` |
| **主链科学源 = 聚焦 EventList** | ⬜ **未做** | Step07 仍是 `HomogeneousBeam 0 0 16.051 0 0 -1 1.8`,文件自标 "rate-folding prototype, **replace in Step09 with detector-coupled optics EventList bridge**" |

即:**主链显著性的信号侧本质还是 r=1.8cm 均匀盘 + 用 EventList 半径分布做的空间切割 proxy**,
不是真把聚焦光子丢进探测器跑出来的。要闭合就是把上表第 3 行做了。

---

## 3. ⚠️ 最关键的坑:归一化(形状 vs 绝对有效面积)——不读这段会把信号砍 ~89×

| 量 | 主链当前(Step07/08) | B-FULL demo 镜 |
| --- | --- | --- |
| 511keV 有效面积 | **A_opt = 50.89 cm²**(峰值;三角带通占位 `aeff_cm2=[0,0,20,50.89,20,0,0]`) | **A_eff ≈ 0.573 cm²**(几何面积 2.304 cm² × 效率 0.2488) |
| 来源 | Step05 标量(511-CAM 量级目标镜占位) | 5 环 × 72 tile × 0.8mm tile 的玩具镜 |

**两者差约 89×。** 所以**绝不能**把 `HomogeneousBeam`(按 50.89 cm² 归一)直接替换成 B-FULL demo 的 4968 个光子——
那会让信号掉 ~89× 或被错误归一。必须把**两件事分开**:

- **PSF 形状(空间 x/y + 方向 + 能量分布)** ← 来自 B-FULL EventList(真实、已验证,这是光学工具的价值)。
- **绝对有效面积 A_eff(E)** ← 项目采纳的**真实目标镜**(不是 0.573 cm² 玩具镜)。

**还有能量梳问题**:EventList 是 480/500/**511**/530/550 五条线(各 ~1280)。若科学线是 **511**,
只有 ring 2(511keV)那 ~1285 个是 511 线信号,其余 4 条在别的能量 bin——**别把 5 能当 511 线信号**。

**两条整合路线(执行 AI 二选一,先和人确认)**:
- **路线 A(推荐,物理最干净)**:用**真实目标 Laue 镜几何**(真实环数/口径/A_eff,达到项目 A_eff 设计)重跑 B-FULL,
  产出 shape+归一都对的 EventList,直接当科学源。需要项目提供真实镜参数。
- **路线 B(快,解耦)**:B-FULL demo EventList **只取 PSF 形状**(x/y/方向分布,按需只取 511keV 子集);
  **绝对计数按 `N = Flux × A_eff(511) × T_obs` 缩放**到项目采纳的 A_eff(把 demo 当 PSF 模板,A_eff 另给)。

---

## 4. 从哪里搬运前端聚焦(精确路径)

**opticsim 侧(光学引擎,只读)**:
- 进程源码(已修复):`/home/ubuntu/opticsim/geant4_app/src/laue_multiring_bfull_demo.cc`
- 二进制(临时):`/tmp/opticsim-bfull-build/laue_multiring_bfull_demo`
  (正式用按 README 在干净 Geant4 11.4 环境重建:见 §6 命令)
- 环梳配置:`/home/ubuntu/opticsim/data/laue/ge111_480_550keV_multiring_darwin_config.csv`
- 外部 XOP/CRYSTAL 摇摆曲线 map:
  `/home/ubuntu/cross_check_laue/laue511_validation/reports/bfull_rocking_curve_map_status/available_rocking_curve_map.csv`

**本仓库侧(已落地的光学 run 输出)**:
- 标称 run 目录:`stepwise_maintenance/step04_opticsim/outputs/opticsim_laue_bfull_xopmap_20k/`
  - **`focal_crossings.csv`** ← **唯一正确的科学交接源**(过滤 `source_tag==laue_bfull_diffracted`、落在 Be 窗内)
  - `summary.json` ← 含 `emergent_focal_diffraction_fraction`、能量/几何
  - `phase_space.csv` ← **禁用**(解析投影,高估 28%,仅留作参考)
- 在线后端闭环 run(交叉校验,勿当科学源):`opticsim_laue_bfull_online_20k/`

**探测器几何 / 注入面权威**:
- 几何:`outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo.setup`
- 注入面:`science_beam_z_cm = 16.051`,Be 窗半径 `1.898 cm`(见 `outputs/geometry/.../bounds.json` 的 META)

---

## 5. 如何桥接:有序可执行步骤

> 坐标/单位约定(Step09 已固化,保持一致):opticsim 输出 mm → cm 用 `×0.1`;
> 注入面 `z = 16.051 cm`;方向保留 x/y、**反转 uz**(让光线射向探测器,uz<0)。

**Step A — 定标(先决,卡 §3 归一化)**
- 与人确认走路线 A 还是 B,确定 **A_eff(E) 权威值**(真实镜 or 采纳的 A_opt 曲线)与**科学能量**(511 线 or 480–550 宽带)。
- 产出一张明确的 `optics_aeff_authority.json`:`{energy_keV: aeff_cm2}` + 选定能窗。

**Step B — 产出/确认聚焦 EventList(形状)**
- 若路线 A:用真实镜环配置重跑 B-FULL(命令见 §6),输出新 run 目录。
- 运行 `stepwise_maintenance/step09_optics_bridge/code/build_step09_optics_bridge.py`
  确认 EventList 来自 `focal_crossings.csv` 的 `laue_bfull_diffracted`、within-Be、ptype=1。
- 记录:`n_within_be_window`、`r95/r99`、能量分布。

**Step C — 用聚焦 EventList 替换 Step07 占位科学源**
- 定位 `stepwise_maintenance/step07_source_cases/code/build_step07_source_cases.py` 里写
  `HomogeneousBeam ... 16.051 ... -1.0 1.8` 的逻辑(约 L963/L969)。
- 改成 MEGAlib `EventList` 源(参考 Step09 已生成的 `.source`:`<Name>.EventList <eventlist.dat>`),
  指向聚焦 EventList;**绝对触发数/Flux 按 Step A 的 A_eff 归一**(不是直接用 4968)。
- 保留 claim 控制注释,改述为 "detector-coupled optics EventList science source (B-FULL focused PSF)"。

**Step D — 全量 Cosima 输运(非 smoke)**
- 用真实镜的 A_eff×Flux×T 推出的触发数跑 Cosima 全量(不是 1000),
  几何用 `XZTES_ADR_v4c_mkflange_cm`,EM `LivermorePol`、HD `qgsp-bic-hp`(与现 Step09 source 一致)。
- 输出 `.sim.gz` → 走现有 Step05 veto/time-axis 后处理,得到聚焦信号的探测器级 hits/能谱/空间分布。

**Step E — Step08 用 detector-coupled 聚焦响应出 Z**
- 把 Step08 的科学侧从"占位盘 rate-folding + EventList 空间 proxy"换成
  **真实聚焦源的探测器响应**(能量落在 511±kσ 窗内、空间落在焦斑的计数)。
- 背景侧**不动**(探测器全天 far-field 维持)。best-cut 逻辑沿用(`spot_r90` 等稳健 cut,**不要** `spot_rmax`)。

**Step F — 重验**
- `python3 code/tools/validate_new_geo_re.py` 须仍全 PASS;
- 更新 0531 closure:`P1_FOCUSED_SPOT_SPATIAL_PROXY` 由 PARTIAL → CLOSED(detector-coupled transport done)。

---

## 6. 关键命令(复制即用)

**重建 B-FULL 二进制(干净 Geant4 11.4 环境)**:
```bash
env -i HOME="$HOME" USER="$USER" SHELL=/bin/bash \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  bash -lc 'source /home/ubuntu/software/geant4-11.4.0-install/bin/geant4.sh; \
  cd /home/ubuntu/opticsim; \
  cmake -S . -B /tmp/opticsim-bfull-build -DCMAKE_BUILD_TYPE=Release; \
  cmake --build /tmp/opticsim-bfull-build --target laue_multiring_bfull_demo -j4'
```

**跑 B-FULL 外部 XOP-map(标称科学 run;路线 A 时把 --ring-config 换成真实镜)**:
```bash
env -i HOME="$HOME" USER="$USER" SHELL=/bin/bash \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  bash -lc 'source /home/ubuntu/software/geant4-11.4.0-install/bin/geant4.sh; \
  cd /home/ubuntu/opticsim; \
  /tmp/opticsim-bfull-build/laue_multiring_bfull_demo \
    --n <N> --seed 20260601 \
    --ring-config /home/ubuntu/opticsim/data/laue/ge111_480_550keV_multiring_darwin_config.csv \
    --rocking-curve-map /home/ubuntu/cross_check_laue/laue511_validation/reports/bfull_rocking_curve_map_status/available_rocking_curve_map.csv \
    --require-rocking-curve-map \
    --out <NEW_RUN_DIR>'
```

**桥接 + 后处理 + 验证**:
```bash
cd /home/ubuntu/codex_tes_511_sim/new_geo_re
python3 stepwise_maintenance/step04_opticsim/code/build_step04_opticsim_audit.py
python3 stepwise_maintenance/step09_optics_bridge/code/build_step09_optics_bridge.py
# Cosima 全量(MEGAlib 环境):
source /home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh
cosima <step07 或 step09 生成的科学源 .source>
python3 stepwise_maintenance/step08_significance/code/build_spatial_line_proxy.py
python3 code/tools/validate_new_geo_re.py
```

---

## 7. 不变量 / 禁止事项(踩了就错)

1. **科学交接源 = `focal_crossings.csv` 的 `laue_bfull_diffracted`(within Be);禁用 `phase_space.csv`。**
2. **归一化:形状来自 EventList,绝对 A_eff 来自项目权威;禁止直接把 demo 的 4968/0.573cm² 当真实镜信号。**
3. **背景侧不动**:探测器全天 4π far-field 维持。**不要**把"光学 all-particle 桥(n/p 穿透镜)"叠到全天本底上
   = 会重复计算那块立体角的 n/p。透镜对本底的唯一真实净增量是**透镜质量自身产生的次级/活化**(那是另一条
   `P1/P2` 任务,需要先插透镜硬件质量,与本信号集成解耦)。
4. **能量**:511 线科学只算 511keV 子集(ring 2),别把 5 能梳全当 511 线。
5. **坐标/单位**:mm→cm ×0.1、z=16.051cm、反转 uz。
6. **显著性 headline 用稳健 cut**(`spot_r90` 等),**不要** `spot_rmax`(被康普顿散射尾驱动)。
7. **定位措辞**:B-FULL = "镶嵌平晶基线 / Laue 透射几何 / 与标准 EM 竞争的 G4VDiscreteProcess";
   引用 Reiazi 2025 + Guan 2023;不得称弯晶镜、不得称 Geant4 原生 patch、不得把 C++↔Python 1e-11 当物理验证。

---

## 8. 验收标准(done 的样子)

- [ ] 主链 Step07 科学源是聚焦 EventList(B-FULL 真实 PSF),不再是 `HomogeneousBeam(r=1.8cm)`。
- [ ] 绝对归一对齐项目采纳的 A_eff(E)(有 `optics_aeff_authority.json` 记录来源与数值)。
- [ ] Cosima 全量输运完成(非 smoke),走完 Step05 后处理。
- [ ] Step08 的 Z 来自 detector-coupled 聚焦响应(能量窗 + 焦斑空间),背景侧未变。
- [ ] `validate_new_geo_re.py` 全 PASS;0531 closure 的 `P1_FOCUSED_SPOT_SPATIAL_PROXY` 标 CLOSED。
- [ ] 新写一条 `*_20260xxx.md` 时序日志记录本次集成结果与最终 Z。

---

## 9. 指针

- 光学物理审阅(HTML):`stepwise_maintenance/step04_opticsim/laue_review_20260601.html`
- 光学修复记录:`OPTICS_BFULL_TEMP_MEMORY.md`、`/home/ubuntu/cross_check_laue/laue_lens_review_log.md` 条目 11
- 0531 总 review:`review_20260531.html`、`outputs/reports/review_20260531_closure/review_20260531_closure.md`
- Step09 桥脚本:`stepwise_maintenance/step09_optics_bridge/code/build_step09_optics_bridge.py`
- Step07 源生成:`stepwise_maintenance/step07_source_cases/code/build_step07_source_cases.py`(含 `aeff_cm2`/`A_opt` 占位)
- Step08 显著性:`stepwise_maintenance/step08_significance/code/build_spatial_line_proxy.py`
