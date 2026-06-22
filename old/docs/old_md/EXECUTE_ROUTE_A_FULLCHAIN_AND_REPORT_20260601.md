# 执行 Prompt:路线A 真实聚焦镜 → 全链收束 → 实验报告(20260601)

> 时序标记 **20260601**。这是给执行 AI(如 Codex)的**有序可执行任务书**。
> 三件事:① 按路线A建真实聚焦镜并跑;② 按 `stepwise_maintenance` 分步拆解收束全链;
> ③ 写一份有条理的实验报告(含 DIXE / 立方星图8 风格的 non-X-ray 本底统计)。
> 配套已存在文档(**必须先读**):
> - **`LAUE_LENS_DESIGN_SPEC_20260601.md`(任务A 的独立设计文档:设计要求 + B-FULL 模拟原理 + 交叉校验)**
> - `OPTICS_BFULL_BACKEND_INTEGRATION_20260601.md`(光学→后端集成细则、归一化坑、不变量)
> - `stepwise_maintenance/CURRENT_PROGRESS_STEP_BREAKDOWN.md`(分步拆解 + 各 step outputs 权威)
> - `stepwise_maintenance/step04_opticsim/laue_review_20260601.html`(B-FULL 物理审阅)
> - `review_20260531.html` / `outputs/reports/review_20260531_closure/`(0531 总审阅 + closure 矩阵)
> - `基于立方星的康普顿望远镜在轨性能模拟.md`(图7/图8 本底谱样式参考)

---

## 0. 主线任务(防止跑偏,先记住全局)

大气高空气球项目,科学目标:探测**银心 511 keV 点源**。质量模型用 **DEMO2 复制**(代表性、抗审稿)。
完整物理链(用户原始 8 步)↔ 现有 stepwise_maintenance:

| 用户步骤 | 含义 | 对应 step |
|---|---|---|
| 1 | 探测器 + 制冷机质量模型 | Step01 几何(DEMO2:CsI active shield / Al 窗 / Nb can / ADR / Cu-W 屏蔽 / Be 窗) |
| 2 | 聚焦光学质量模型 | **Step04 B-FULL Laue + Step09 桥**(本任务路线A要升级) |
| 3 | 瞬时宇宙线大气源(EXPACS)+ buildup 活化 + V404 参考源 | Step02 瞬时/活化 + Step03 延时 + Step07(V404) |
| 4 | 源→聚焦光学→焦平面所有粒子记为聚焦源 | Step04/Step09(产聚焦相空间) |
| 5 | 聚焦源 + 瞬时本底 + 延时源 → 质量模型 | Step02/Step05(输运进 DEMO2 几何) |
| 6 | 开跑,第 15 天为基准点 | Step05/Step06 |
| 7 | 闪烁体反符合 | Step05 CsI 主动屏蔽 veto(阈 50 keV) |
| 8 | Compton veto 符合(非典型散射-吸收体) | Step08 Compton/FoV |

当前阻塞点(本任务要解决):**主链科学源还是 `HomogeneousBeam(r=1.8cm)` 占位,不是真聚焦 PSF;
且聚焦镜真实几何尚未确定(现有 0.573 cm² 5 环是一次性 smoke 玩具),主链 A_opt=50.89 cm² 只是历史占位标量。**
本任务:**由 Codex 设计真实镜 → 计算其 A_eff(E) → 替换占位 → 真聚焦源贯通主链。** 见 §2、§5。

---

## 1. 任务总览(三个交付)

- **A 路线A**:用本 session 确认的 B-FULL **模拟模型**,由你(Codex)**自行设计**一个合适复杂度/焦距/spot 的 Ge(111) Laue 镜(真实几何尚未定),带入模拟跑出聚焦源,并**计算**其 A_eff(E)。
- **B 全链收束**:用真聚焦源替换占位盘,按 stepwise_maintenance 重跑 step04→step10,validator 全 PASS。
- **C 实验报告**:按分步拆解写,含各 step 更新后的 outputs + DIXE/立方星图8 风格的 non-X-ray 本底统计。

---

## 2. 任务A — 路线A:聚焦镜(★已定稿设计,Codex 改成这个)

**模拟模型已定 = 本 session 确认并修复的 B-FULL**(absorption-free MFP、`G4VDiscreteProcess`、emergent-vs-analytic 门控)。
科学定位已定(见 `FOCUSING_LENS_SCIENCE_RATIONALE_20260601.md`):**以 511 探测效率为主 + 一个适当的天然展宽**;
Laue 是工程定死的光学;不必逐片精算(用户不负责镜子设计)。

### ★ 确定的合理设计 `balloon511_f9m_ge111_511line`(Codex:把当前 8.3m 单环改成这个)

| 参数 | 值 | 依据(公开资料) |
|---|---|---|
| 材料/反射 | **Ge(111)**, d=3.266590088 Å | Ge(111) 衍射效率最高、能区偏高,软伽马标准选择 |
| 焦距 f | **9 m**(6–9m 上限取最大,A_eff 最大;括住 511-CAM Laue 8.3m) | 511-CAM Laue=8.3m(从 CLAIRE 2.77m 缩放);气球可接受 |
| 几何 | **单环 @ 511 keV**,r(511)≈**66.9 mm**,满方位密排 | r=f·tan(2θ_B);A_eff ∝ 圆周 ∝ f |
| tile | **15 mm**(real Laue 晶片 10–15mm;保证几何焦斑落在 Be 窗内) | LAUE 项目/CLAIRE 晶片量级 |
| 镶嵌度 ω | **30 arcsec**(已验证 B-FULL 基线;CLAIRE 反推 ~40″) | Laue 晶 30″–2′ 标准 |
| **天然能窗(FWHM)** | **≈ 501–521 keV**(=511±10keV) | ΔE/E = cot θ_B × ω = 269×1.45e-4 = **3.9%**(Frontera 综述 passband 公式) |
| **A_eff(511)** | **≈ 16 cm²**(单能 Ge Laue 气球焦距现实值,A_eff ≈ 1.7 cm²/m × f) | 这是 f≤9m 的物理上限;要更大需更长焦或 channel 光学 |
| 焦斑 | tracked r99 ≤ Be 1.898 cm(15mm tile 几何斑 < Be) | 硬约束 |

**给 Codex 的修改**:
1. 新建 `ge111_balloon511_f9m_511line_config.csv`(单环 511keV、f=9m、r=66.9mm、15mm tile、满方位密排约 28 片),Bragg 自洽。
2. 跑 B-FULL(外部 XOP map,可复用 511keV 曲线),**计算 A_eff(511)** 写 `optics_aeff_authority.json`,**替换 Step07 的 50.89 cm² 占位**。
3. **记录天然能窗 FWHM(~501–521keV)** —— 这是后面统计要用的"设计覆盖能窗"(见 §4.2/§4.3)。
4. 注意:B-FULL 在 tile 中心发光,报告的 r99 偏小(未铺满 tile 面);**几何焦斑实际 ~tile 尺寸**,故 tile≤15mm 才稳进 Be 窗——别为加 A_eff 把 tile 放太大。

> A_eff 老实说:f≤9m 的单能 Ge(111) Laue,A_eff(511) 天花板就 ~16 cm²(∝f);这是物理,不是没优化。9m 已是范围内最大。

> **⚑ Review 门**:Codex 按上表产出设计包(config + `optics_design_rationale.md` + `optics_aeff_authority.json` + B-FULL run + 交叉校验)后**停下交人类→Claude review**;通过后才跑 §3 全链。
> 注意:任务A **只设计聚焦镜并产聚焦源**;透镜硬件当本底质量模型是另一条解耦任务,本次不做(§5 不变量3)。

---

## 3. 任务B — 全链收束(按 stepwise_maintenance 分步拆解)

按 `CURRENT_PROGRESS_STEP_BREAKDOWN.md` 的 step 顺序,用**真聚焦源**贯通:

1. **Step04 审计**:对新 run 跑 `build_step04_opticsim_audit.py`,确认 tracked 焦斑/能窗/A_eff。
2. **Step09 桥**:`build_step09_optics_bridge.py` 产 EventList(**只用 `focal_crossings.csv` 的 `laue_bfull_diffracted`、within-Be**;禁用 phase_space)。
3. **集成(关键)**:按 `OPTICS_BFULL_BACKEND_INTEGRATION_20260601.md` 的 Step C–F,
   把 **Step07 的 `HomogeneousBeam(r=1.8cm)` 科学源替换成聚焦 EventList 源**,
   **绝对归一按 `optics_aeff_authority.json` 计算的 A_eff(E) × Flux × T**(不是直接用 EventList 行数),
   **并把 Step07 的 50.89 cm² 占位标量替换成这个计算值**。
4. **全量 Cosima 输运**(非 1000 smoke):聚焦源 + 瞬时本底 + 延时源进 DEMO2 几何,走 Step05 veto/time-axis。
5. **Step06/07/08** 重算:day15 基准、源案例、时变显著性,显著性 headline 用稳健 cut(`spot_r90`,**不用 spot_rmax**)。
6. **Step10 validator**:`python3 code/tools/validate_new_geo_re.py` 全 PASS;更新 0531 closure 的
   `P1_FOCUSED_SPOT_SPATIAL_PROXY` 由 PARTIAL → CLOSED(detector-coupled transport done)。

---

## 4. 任务C — 实验报告(核心交付)

报告文件:`outputs/reports/experiment_report_20260601/experiment_report.md`(+ 图存同目录 `figures/`)。
**按分步拆解组织,有条理、有逻辑、可读。**

### 4.1 分步 outputs(更新光学后)
逐 step(Step01→Step10)给**更新后的 outputs 权威值**(几何、活化、聚焦源 A_eff、veto 率、day15 速率、显著性…),
引用各 step 的 output authority 文件(见拆解 md 里每个 step 末的 "Output authority")。表格化呈现"旧占位 vs 新真聚焦"对比。

### 4.2 ★ non-X-ray 本底统计(仿 DIXE / 立方星图8,核心新增)

**目的**:像 *Simulation of non X-ray background for the DIXE mission* 和立方星图8 那样,
**统计 TES 实际探测到的本底**(非聚焦粒子本底),量化各 veto 机制的压制。

**数据来源**:TES 实际探测事例 = day15 事例目录 `outputs/reports/day15_complete_report/work/event_catalog.pkl`
(含 stream=prompt/delayed、tes_total_keV、bgo_total_keV、像素、rate_hz)。**统计基于 TES 实测,不是解析估计。**

**两个能窗(★口径已更新 20260601)**:
- **W1 = 设计天然覆盖能窗 ≈ 501–521 keV**(=511±10keV,即 §2 定稿镜 30″ 镶嵌的 FWHM passband)。
  **替换原来的 480–550**——统计宽窗一律改成"这台镜实际聚焦覆盖的能窗"(以 `optics_aeff_authority.json` 里记录的 FWHM 为准;若镜参数微调,W1 跟着改)。
- **W2 = 511 ± 420 eV**(最终 3σ 显著度窗;TES 分辨率理论极限 140 eV,**保守用 3× = 420 eV**)。**不变。**

> **三个口径分工(务必照此,不要混)**:
> - **W1(宽窗 ~501–521keV)**= 本底谱统计 / veto 压制因子的"设计覆盖能窗"(随镜设计走)。
> - **W2(511±420eV)**= **最终 3σ 显著度**就用这个窄线窗,**不变**。
> - **参考科学源**= **V404 的 511 源,扫强度(flux scan)**,**不变**(沿用 Step07 的 V404 case)。

**四个 veto 变体(逐级压制,给 before/after)**:
1. **raw**:无 veto(TES 原始探测);
2. **+ 闪烁体反符合**:加 CsI active shield veto(阈 50 keV,窗 1e-6 s);
3. **+ Compton 符合**:加 Compton/FoV veto(注意:非典型散射-吸收体,按 Step08 既有 Compton/FoV 逻辑);
4. **after both**:两种符合都加(最终)。

**要出的图/表(图8 风格)**:
- **本底能谱图**:count rate (cps/keV) vs energy,叠加 4 个变体(raw → +scint → +compton → final),
  标注 W1/W2 窗口区,标注 511 峰。可另出一张**按成分分解**(prompt vs delayed,仿图7)。
- **窗口计数率表**:W1、W2 两窗 × 4 变体的本底 cps,以及每级 veto 的**压制因子**(rejection factor)。
- 可对 prompt / delayed / (若有)聚焦泄漏分别列。

**建议可加的统计(你觉得有用就做)**:
- 各 veto 对各本底成分(prompt 宇宙线分量、延时活化核素如 I-128)的**剔除效率**;
- W2 窗内**信噪**:聚焦 511 信号 cps vs 本底 cps(对 day15 基准),及 Z20d;
- 511 峰的**峰/连续比**随 veto 的变化;
- 焦斑空间切割(spot_r90)叠加在 veto 之上的额外压制(承接 Step08 spatial proxy)。

### 4.3 报告结构要求
- 摘要 → 模拟方案(质量模型/源/光学/流程图)→ 分步结果(4.1)→ non-X-ray 本底统计(4.2)→ 显著性 → 讨论/局限 → 结论。
- 每个数都标 output authority 来源;图有图注;窗口/变体定义清晰。
- 局限明说:镶嵌平晶基线(非弯晶)、透镜硬件本底未建、A_eff 来源、Compton veto 非典型散射-吸收体。

---

## 5. 不变量 / 禁止事项(踩了就错,逐条遵守)

1. **科学交接源 = `focal_crossings.csv` 的 `laue_bfull_diffracted`(within Be);禁用 `phase_space.csv`(高估 28%)。**
2. **归一化分离 + A_opt 计算**:PSF 形状来自 EventList,**绝对 A_eff(E) 由你设计的镜计算得到**
   (几何面积 × 涌现效率)并写 `optics_aeff_authority.json`,**用它替换主链 Step07 的 50.89 cm² 占位**;
   **禁止**把一次性 smoke 玩具镜(0.573 cm²/4968 行)当设计基线或真实镜信号;**禁止**为抬 Z 做非现实大镜。
3. **背景侧立体角不重复**:探测器全天 4π far-field 本底维持;**不要**把"光学 all-particle 桥(n/p 穿透镜)"叠加到全天本底
   = 重复计算那块立体角的 n/p。透镜对本底的唯一真实净增量是**透镜质量自身的次级/活化**(本次不做,另列任务)。
4. **能窗口径**:定稿镜是**单环 511**(EventList 全是 ~511±10keV,无 5 能梳),所以 **W1 = 设计天然窗 ~501–521keV**(本底统计/veto);**W2 = 511±420eV**(最终 3σ);参考源 = **V404 511 扫强度**。三者别混(见 §4.2)。
5. **坐标/单位**:opticsim mm→cm ×0.1;注入面 z=16.051 cm;反转 uz(uz<0 射向探测器)。
6. **显著性 headline 用稳健 cut(`spot_r90`),不用 `spot_rmax`**(被康普顿散射尾驱动)。
7. **TES 能量分辨率**:理论极限 140 eV;**饱和能量下分辨率不随能量变**;W2 保守用 ±420 eV。
8. **措辞**:B-FULL = 镶嵌平晶基线 / Laue 透射几何 / 与标准 EM 竞争的 `G4VDiscreteProcess`;引用 Reiazi 2025 + Guan 2023;
   不得称弯晶镜 / Geant4 原生 patch / 把 C++↔Python 1e-11 当物理验证。
9. **DEMO2 几何权威不动**:`outputs/geometry/XZTES_ADR_v4c_mkflange_cm/`;不改探测器质量模型。

---

## 6. 关键命令(复制即用)

**重建 B-FULL(干净 Geant4 11.4)+ 跑真实镜**:
```bash
env -i HOME="$HOME" USER="$USER" SHELL=/bin/bash \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  bash -lc 'source /home/ubuntu/software/geant4-11.4.0-install/bin/geant4.sh; cd /home/ubuntu/opticsim; \
  cmake -S . -B /tmp/opticsim-bfull-build -DCMAKE_BUILD_TYPE=Release; \
  cmake --build /tmp/opticsim-bfull-build --target laue_multiring_bfull_demo -j4; \
  /tmp/opticsim-bfull-build/laue_multiring_bfull_demo --n <N> --seed 20260601 \
    --ring-config /home/ubuntu/opticsim/data/laue/<REAL_RING_CONFIG>.csv \
    --rocking-curve-map /home/ubuntu/cross_check_laue/laue511_validation/reports/bfull_rocking_curve_map_status/available_rocking_curve_map.csv \
    --require-rocking-curve-map \
    --out /home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step04_opticsim/outputs/opticsim_laue_bfull_xopmap_real'
```

**全链收束 + 验证**:
```bash
cd /home/ubuntu/codex_tes_511_sim/new_geo_re
python3 stepwise_maintenance/step04_opticsim/code/build_step04_opticsim_audit.py
python3 stepwise_maintenance/step09_optics_bridge/code/build_step09_optics_bridge.py
source /home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh
cosima <step07/step09 生成的聚焦科学源 .source>     # 全量,非 1000 smoke
# … Step05 veto/time-axis 后处理 …
python3 stepwise_maintenance/step08_significance/code/build_spatial_line_proxy.py
python3 code/tools/validate_new_geo_re.py            # 须全 PASS
```

**本底统计数据源**:`outputs/reports/day15_complete_report/work/event_catalog.pkl`
(字段:`stream / tes_total_keV / bgo_total_keV / pix_* / rate_hz`;读法参考
`stepwise_maintenance/step08_significance/code/build_spatial_line_proxy.py` 的 `selected_background_events`)。

---

## 7. 总验收标准(done 的样子)

- [ ] **任务A**:Codex 自设计镜 + B-FULL run 完成;`optics_design_rationale.md`(选择+理由+文献锚)就位;
      焦斑 r99 ≤ Be 窗;A_eff(E) **由该镜计算**写入 `optics_aeff_authority.json`;emergent-analytic 残差<0.01;参数物理真实。
- [ ] **任务B**:主链科学源 = 聚焦 EventList(非占位盘),全量 Cosima 输运完成,走完 Step05–08,
      `validate_new_geo_re.py` 全 PASS,0531 closure `P1_FOCUSED_SPOT` 标 CLOSED。
- [ ] **任务C**:实验报告 `experiment_report_20260601/` 完成,含
      (a) 各 step 更新 outputs,
      (b) W1/W2 两窗 × 4 veto 变体的 non-X-ray 本底谱图 + 计数率表 + 压制因子(基于 TES 实测),
      (c) 报告有条理、可读、标来源、列局限。
- [ ] 新写一条 `*_20260xxx.md` 时序日志记录本次执行结果与最终 Z 和本底数。

---

## 8. 指针
- **聚焦镜设计文档(任务A):`LAUE_LENS_DESIGN_SPEC_20260601.md`**
- 集成细则:`OPTICS_BFULL_BACKEND_INTEGRATION_20260601.md`
- 分步拆解 + outputs 权威:`stepwise_maintenance/CURRENT_PROGRESS_STEP_BREAKDOWN.md`
- 光学物理审阅:`stepwise_maintenance/step04_opticsim/laue_review_20260601.html`
- 0531 总审阅 / closure:`review_20260531.html` / `outputs/reports/review_20260531_closure/review_20260531_closure.md`
- 本底谱样式参考:`基于立方星的康普顿望远镜在轨性能模拟.md`(图7 成分分解 / 图8 总谱+计数率表)
- 本底数据源:`outputs/reports/day15_complete_report/work/event_catalog.pkl`
- 显著性脚本:`stepwise_maintenance/step08_significance/code/build_spatial_line_proxy.py`
