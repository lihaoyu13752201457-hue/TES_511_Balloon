# Laue 聚焦镜:设计要求 + 模拟原理 + 交叉校验(20260601)

> 时序标记 **20260601**。**独立设计文档**。给执行 AI(如 Codex)的任务:**只做一件事——按本文设计一台 Laue 聚焦镜**,
> 产出设计包(§IV),然后**交人类 → Claude review**。**review 通过后**,才执行主文档
> `EXECUTE_ROUTE_A_FULLCHAIN_AND_REPORT_20260601.md` 的 Step B(全链收束)。本文不跑全链、不动探测器质量模型。
>
> 背景:**模拟模型已定 = 本 session 确认并修复的 B-FULL**(见 §II);**真实几何未定 = 本文要你设计**。

---

## Part I — 设计要求

### I.1 硬约束(必须满足)
1. **能窗 480–550 keV**,材料 **Ge(111)**(d = 3.266590088 Å),分环 Bragg 调谐,**511 keV 在中段**。
2. **焦斑 ≤ Be 窗**:tracked 衍射焦面穿越的 **r99 ≤ 1.898 cm**(硬上限;这是探测器 Be 窗半径,聚焦光必须落进去)。
3. **Bragg 几何自洽**:每环 `radius = focal_length × tan(2 θ_B)`,其中 `θ_B = asin(λ/2d)`,`λ = 12.398/E[keV] Å`。
   (B-FULL 的 `LoadRingConfig` 会硬校验,半径偏差 > 0.2 mm 直接报错。)

### I.2 物理真实护栏(关键,决定能否过审/过 review)
- 参数取**气球 Laue 镜文献量级**,**不得为抬高灵敏度 Z 把镜做得不切实际地大**。
- 每个设计选择都要有**理由 + 文献锚**,写进 `optics_design_rationale.md`。
- 参考锚点:CLAIRE 气球 Laue 镜焦距 ~2.8 m;真实 Laue 镜晶片 ~5–15 mm、晶体总数数百~低千、镶嵌度 ~30 arcsec、
  软伽马 Laue 镜 A_eff 量级为数十 cm²(随设计而定,不是越大越好)。

### I.3 设计可调量 + 物理权衡(你来优化)
**目标:在 `r99 ≤ Be 窗` 硬约束下,用下列组合取一个合理(非最大化作弊)的 A_eff(511),且全部参数物理真实。**

| 可调量 | 影响 | 权衡 |
|---|---|---|
| **焦距 f** | 环半径/口径 ∝ f;镶嵌焦斑半径 ~ (mosaic_FWHM/2)×f | f 越长→口径越大(A_eff↑)但焦斑越大(逼近 Be 窗);demo 用 8.3 m 偏长,可重选 |
| **tile 尺寸 a** | 单片几何面积 ∝ a²;几何焦斑 ~ tile 投影 ~ a | a 越大→面积↑但焦斑↑;真实 5–15 mm(demo 0.8 mm 不真实) |
| **环数 / 每环 tile 数 / 口径** | 总几何收集面积 = Σ tile 面积 | 越多→A_eff↑;晶体总数取真实量级(数百~低千) |
| **镶嵌度 mosaicity** | 衍射效率/带宽 + 焦斑角展宽 | 保留 30 arcsec(已验证)或注明依据;越大→焦斑越宽 |

> 焦斑量级估算(自检):镶嵌贡献半径 ≈ (mosaic_FWHM/2)×f;几何贡献 ≈ a/2。两者求和应 ≤ Be 窗 1.898 cm 的 r99。
> 例:mosaic 30″ = 1.45e-4 rad,f = 3 m → 镶嵌半径 ≈ 0.22 cm;tile 10 mm → 几何半径 ≈ 0.5 cm;合计量级 ~0.7 cm < 1.898 cm ✓。

### I.4 交付物(设计包,§IV 详列)
1. 环配置 CSV(新建,别覆盖 demo);2. `optics_design_rationale.md`;3. `optics_aeff_authority.json`(计算的 A_eff(E));
4. B-FULL run 输出目录;5. 交叉校验结果(§III)。

---

## Part II — 模拟原理(B-FULL 模型,已定,勿改物理)

### II.1 是什么
B-FULL = `/home/ubuntu/opticsim/geant4_app/src/laue_multiring_bfull_demo.cc`。
一个**自定义 Geant4 离散 Laue 衍射过程**,与**标准 EM 保持竞争**(非 forced),**固定 tile 取向正演**,**聚焦从几何涌现**(非反解构造)。
定位:**镶嵌平晶基线 / Laue 透射几何**;引用 Reiazi 2025、Guan 2023;**不得**称弯晶镜 / Geant4 原生 patch。

### II.2 物理公式与常数(逐项已手算/外锚核对,见 `step04_opticsim/laue_review_20260601.html`)
- **Bragg 几何**:`n λ = 2 d sinθ_B`;入射→衍射偏转 `2θ_B`;环半径 `r = f tan(2θ_B)`。
- **镶嵌 Darwin–Hamilton 衍射效率**(含吸收,焦面口径):
  `p_diff = 0.5·(1 − e^{−2σt})·e^{−µt/cosθ_B}`,其中 `σ = Q·W(Δθ)`。
  **0.5 是镶嵌晶物理上限**(disregarding absorption);弯晶才能超 50%——这是范围所在。
- **关键常数**(Ge(111) @511keV):消光长度 `Λ = 539.79 µm`(Pendellösung,πV·cosθ_B/(r_e·λ·|F_111|),手算 ≈537µm,<1%);
  线衰减 `µ = 0.432 cm⁻¹`(NIST XCOM,总衰减;@511 ~95% 康普顿)。能量标度:`Λ ∝ E`,`µ ∝ (511/E)^0.55`。
- **镶嵌分布**:高斯 `W(Δθ)`,FWHM = mosaicity(默认 30 arcsec),归一已核(峰=1/(√2π σ))。
- **涌现聚焦**:每 tile 一个**固定晶面法向**(让 on-axis 平行束反射到焦点);实际光子跨**镶嵌扰动后的法向**反射 →
  聚焦从各 tile 取向涌现,PSF 从镶嵌展宽涌现(非逐光子反解对焦)。
- **有限 MFP + EM 竞争**:衍射 MFP 设成"沿晶体路径衍射概率 = **无吸收**衍射效率 `0.5(1−e^{−2σt})`",
  与标准 EM(康普顿/光电/瑞利)竞争;吸收由 EM 做一次(不双计)。

### II.3 本 session 已修复(用这版,别退回)
1. **吸收双计**:外部 XOP 曲线喂 MFP 前改用 `R/(1−A)`(无吸收效率),EM 只吸收一次。
2. **`G4VEmProcess` → `G4VDiscreteProcess`**:旧版在 G4 11.4 崩 `em0002`,改后 10.2/11.4 均可跑。
3. **门控**:summary 出 `emergent_focal_diffraction_fraction` vs `analytic_reference_focal_diffraction_fraction`(残差应 < 0.01~0.04)。

### II.4 怎么跑 + 用哪个输出
重建+跑(干净 Geant4 11.4)见主文档 §6。**关键输出**:
- **`focal_crossings.csv`(`source_tag=laue_bfull_diffracted`,within-Be)= 唯一正确的聚焦相空间**。
- **`phase_space.csv` = 解析投影,高估 ~28%,禁用**(忽略衍射光出晶 EM 衰减/康普顿散射)。
- `summary.json`(效率、能窗、emergent-vs-analytic)、`per_ring_summary.csv`(逐环)。

---

## Part III — 交叉校验(`/home/ubuntu/cross_check_laue/laue511_validation`)

### III.1 真·独立 oracle(论文该主打这几条)
| oracle | 验什么 | 现状 | 独立性 |
|---|---|---|---|
| **Barrière 2009** | 实测 Cu/Au 峰值衍射效率/反射率 | 误差 <0.9% / <1.6% | ✓ 实测 |
| **CRYSTAL diff_pat**(xoppylib+DABAX) | Ge(111)@511 镶嵌摇摆曲线(独立动力学码) | 峰 0.2575 vs 核 0.2469,~4% | ✓ 独立码 |
| **Kohnle 1998** | 实测 Ge(111) APS 端点 | <1.4% | ✓ 实测 |
| **PyTTE / CrystalPy** | Takagi–Taupin 完美晶反射率 | 定性一致(完美晶峰>0.5) | ✓ 独立 |
| benchmarks/ | `xop_crystal/ kohnle1998/ xrt_pytte/ crystalpy/ opticsim_table_lens/` | — | — |

### III.2 循环警示(别当物理验证)
`historical_probability_kernel` 那条 **C++↔Python 5e-11 是循环**(同公式同硬编码常数),只能写成"跨语言实现回归",
**不可**当独立物理验证。物理验证 = 上表四个外 oracle。

### III.3 怎么校验一个**新设计**的镜
1. 若新镜仍是 480–550 Ge(111)、厚度与现有相近 → **可复用**现有逐环 XOP map
   `cross_check_laue/.../reports/bfull_rocking_curve_map_status/available_rocking_curve_map.csv`。
2. 若改了能量/厚度/镶嵌度 → **重生成逐环 XOP/CRYSTAL 摇摆曲线**:
   `cd /home/ubuntu/cross_check_laue/laue511_validation && python3 tools/generate_xop_crystal_multiring_curves.py --ring-config <你的新配置>`
   (需 xoppylib/dabax;否则保留在线 Darwin 后端,但要在报告里注明未走外锚)。
3. B-FULL 用 `--rocking-curve-map <map> --require-rocking-curve-map` 跑新镜。
4. **门控自检**:`summary.json` 里 emergent ≈ analytic(残差 < ~0.04);逐环 `p_reflect` 对 XOP 曲线读表保真。
5. 跑包级校验:`python3 tools/run_lightweight_crosscheck.py` 与 `python3 tools/build_validation_summary.py`,看 `reports/laue511_crosscheck_summary.md`。

### III.4 交叉校验验收(设计阶段)
- [ ] emergent 焦面衍射分数 ≈ analytic/CRYSTAL 参考(残差 < ~4%);
- [ ] 逐环 XOP map 覆盖所有设计环;
- [ ] 若改材料/能量,核(Darwin 公式)仍对 Barrière/Kohnle 外锚成立;
- [ ] 报告区分"读表保真(1e-11)"与"物理一致(~4%)"。

---

## Part IV — 交付给 review 的设计包(Codex 做完这些就停,交人类)

放在 `stepwise_maintenance/step04_opticsim/outputs/opticsim_laue_bfull_xopmap_real/` 及旁边:
1. **环配置 CSV**:`/home/ubuntu/opticsim/data/laue/ge111_<设计名>_multiring_config.csv`(分环 E/半径/tile 数/tile 尺寸/厚度,Bragg 自洽)。
2. **`optics_design_rationale.md`**:焦距/口径/tile 尺寸/晶体总数/镶嵌度的**选择值 + 理由 + 文献锚 + 焦斑权衡估算**;
   并自检 r99 ≤ Be 窗的量级。
3. **`optics_aeff_authority.json`**:**这台镜计算的 A_eff(E)**(几何收集面积、逐能量 emergent 效率、A_eff(511) 与 480–550 各点)。
4. **B-FULL run**:`summary.json` + `focal_crossings.csv` + `per_ring_summary.csv`;关键数:r99、emergent-vs-analytic 残差、A_eff。
5. **交叉校验结果**:§III 的门控自检 + `laue511_crosscheck_summary.md` 状态。

**然后停。** 交人类 → Claude review 这台镜(焦距/口径/A_eff 是否物理合理、焦斑是否真 ≤ Be、交叉校验是否过)。
**review 通过后**再执行 `EXECUTE_ROUTE_A_FULLCHAIN_AND_REPORT_20260601.md` 的 Step B(全链)。

---

## 指针
- **能段与科学论证(为什么聚焦 511 而非平摊 480–550):`FOCUSING_LENS_SCIENCE_RATIONALE_20260601.md`**
- 主执行文档:`EXECUTE_ROUTE_A_FULLCHAIN_AND_REPORT_20260601.md`
- 光学→后端集成细则:`OPTICS_BFULL_BACKEND_INTEGRATION_20260601.md`
- B-FULL 物理审阅:`stepwise_maintenance/step04_opticsim/laue_review_20260601.html`
- B-FULL 源码:`/home/ubuntu/opticsim/geant4_app/src/laue_multiring_bfull_demo.cc`
- demo 环配置(模板,勿当基线):`/home/ubuntu/opticsim/data/laue/ge111_480_550keV_multiring_darwin_config.csv`
- 交叉校验包:`/home/ubuntu/cross_check_laue/laue511_validation/`(`tools/run_lightweight_crosscheck.py`、`tools/build_validation_summary.py`、`reports/laue511_crosscheck_summary.md`)
