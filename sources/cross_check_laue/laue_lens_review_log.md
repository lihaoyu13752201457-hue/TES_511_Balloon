# Laue Lens 交叉校验 / 设计审阅日志

> 本文件记录 Claude 对 `/home/ubuntu/cross_check_laue/laue511_validation` 交叉校验包
> 及 `/home/ubuntu/opticsim` Geant4 Laue 模拟的审阅与设计建议。按时间倒序/顺序追加。

---

## 2026-06-01 — 条目 11:面向审稿人接受的复审(B-FULL 最新版,Claude 实测构建+运行)

> 目标:让这套 Laue 模拟 + 交叉校验达到审稿人可接受。读了最新 `laue_multiring_bfull_demo.cc`
> (1480 行)、`validation_summary.py`、全套 benchmark/report,联网核对文献,并亲手在 Geant4 11.4 上
> 构建+运行。三个**新发现**(前几轮未记):

### 🔴 NEW-A:新颖性已被 2025 论文部分抢占,必须重定位(最大接受风险)
- **Reiazi et al., J. Phys. D 58 (2025-07), "G4BraggReflection"**:自称 Geant4 内首个专用 Bragg
  反射过程,**已做 mosaic 晶体**(back-to-back perfect crystallites,高斯抽镶嵌取向)、**与标准 EM
  竞争**(最短 MFP 触发)——与 B-FULL 思路几乎同构。但**只做 Bragg 反射几何,未做 Laue 透射**,只测
  Al @8/59 keV。加上 Guan 2023,"Geant4 原生离散晶体衍射过程"不能再称首创。
- 可辩护差异化(必须引用并写进引言):**Laue 透射几何 + 480–550 keV 软伽马 + 多环整镜涌现聚焦/PSF
  + 焦平面相空间桥到 MEGAlib 探测器/本底**。不改定位 → 大概率被新颖性关挡下。

### 🔴 NEW-B:外部曲线路径的吸收双重计数(~17% 系统偏低,且未门控)
- `BFullEquivalentDiffractionScale`(`laue_multiring_bfull_demo.cc:524-530`):在线后端喂**无吸收**
  `0.5(1-e^{-2σt})`(✓ EM 再吸收);外部 CRYSTAL 后端喂 `rockingCurve.reflectivity`,而 CRYSTAL 的
  R(峰 0.2575)**已含吸收**(≈在线核含吸收 p_diff 0.2469,非无吸收 0.39)→ EM 又吸收一遍 = 双重计数。
- **留存数据自证**:`bfull_single_tile_xop_scan` XOP peak=0.257 vs **obs peak=0.213**;full-lens
  obs=0.2132。我用竞争公式 P=[1/λ_d/(1/λ_d+µ)]·[1-e^{-(1/λ_d+µ)L}] 解得 **0.2136**,与实测吻合 →
  确认 EM 把已含吸收的 0.257 又削 17%,直接传到 A_eff。
- **门控盲区**:当前只检 `max p delta=6.76e-11`(读表保真),不检"涌现衍射分数 vs 输入 R"(差 ~0.044)。
- 修:外部曲线喂 MFP 前除掉吸收 `R_0=R/(1-A)`(两后端口径一致);并新增涌现衍射分数 vs 输入 R 的残差门控。

### 🟠 NEW-D:头部 B-FULL 进程锁死 Geant4 10.2.3,在 11.4 上崩(实测)
- 在 G4 11.4 构建:`PrintInfo() override`(`:1216`)编译失败(11.x 基类已无此虚函数,去 `override` 即过)。
- 修编译后运行仍崩:`G4Exception em0002 — G4EmModelManager::Initialise: No models found out for
  gamma!`——`GuanStyleLaueBraggProcess` 派生 `G4VEmProcess` 却只挂空 `BFullLaueEmBookkeepingModel`,
  11.x 严格 model manager 不接受(设能量限也无效,API 变了)。即**所有 B-FULL 证据都跑在 2016 的 10.2.3 上**。
- 坐实上轮 MED-4(G4VEmProcess 派生脆、收益只是标签)。改成普通 `G4VDiscreteProcess`
  (本质就是重写 GetMeanFreePath+PostStepDoIt,EM model 是空壳),既能在 11.x 跑、去赘瘤,只失去一个
  本就是标签的 EM-category 徽章。

### 2026-06-01 后续:用户决定 B-FULL 接入论文 → NEW-B/NEW-D 三项修复已实施并验证
> 用户澄清主论文 = `codex_tes_511_sim/new_geo_re`,Laue 是其一版块,且决定用 B-FULL(认为 EM 竞争更物理)。
> 据此在 `opticsim/geant4_app/src/laue_multiring_bfull_demo.cc` 实施三修复,Geant4 11.4 实测:
> 1. **吸收双计**:`BFullEquivalentDiffractionScale` 外部曲线分支改喂无吸收效率 `R/(1−A)`。
> 2. **版本崩溃**:`GuanStyleLaueBraggProcess` 由 `G4VEmProcess`→`G4VDiscreteProcess`,删 no-op `BFullLaueEmBookkeepingModel`。
> 3. **验证门控**:summary.json/per-ring 新增 `analytic_reference_focal_diffraction_fraction` vs `emergent_focal_diffraction_fraction`。
>
> 实测(G4 11.4,20000 事件,seed 20260601):两后端均跑通(旧版崩 em0002)。
> 在线:涌现 0.2465 vs 解析 0.2462 = **+0.1%**;外部 XOP-map:涌现 0.2488 vs 解析 0.2570 = **−3.2%**(修前 −33%);
> 两后端一致(0.2465 vs 0.2488)。即 EM 竞争 MC 现精确复现已验证衍射物理。
> **待用户做**:用修复二进制重生成 `cross_check_laue` 的 bfull 留存报告(旧报告是 10.2.3 含 bug 二进制跑的);
> 加门控 `|emergent−analytic|<容差`;跑 A_eff(E)/PSF(E);d90 对 HEART/McXtrace 原生核验。
> 详见 HTML 报告 `new_geo_re/.../step04_opticsim/laue_review_20260601.html`。

### 已复核仍成立的旧结论(不重复展开)
- C++↔Python 5e-11 = 循环(`probabilities.py`≡`OnlineDarwinMosaicProbabilities`,常数逐字相同);
  但 Barriere(<1.6%)/CRYSTAL diff_pat(~4%)/Kohnle(1.3%)是**真独立外锚**——论文主打这三条。
- H2(PSF 非独立):d90 由 `PerturbDirection` 对法向施加整条 mosaic σ 重建(法向偏 δ→反射偏 2δ,且与
  Δθ 无关),疑系统展宽;须对 HEART/McXtrace **原生**核验。
- 范围:`0.5(1-e^{-2σt})` 封顶 50% = mosaic 物理上限;弯晶(姜维春 511 镜)给不出 >50%/1′ PSF。
  必须写成"镶嵌平晶基线/方法学",非弯晶镜。CrystalPy perfect-crystal 峰 0.571>0.5 佐证。

### 最小接受路径(P0)
1. 引用 Reiazi 2025 + Guan 2023,重定位卖点;2. 修吸收双重计数 + 加门控;3. 明确镶嵌基线范围声明;
4. Laue 过程改 G4VDiscreteProcess 迁 11.x;5. 验证叙事切到三外锚 + A_eff(E)/PSF(E)。

Sources: Reiazi 2025 (iopscience.iop.org/article/10.1088/1361-6463/aded1d);Guan 2023
(pmc.ncbi.nlm.nih.gov/articles/PMC11935221/);Virgilli 2016 A&A aa26745-15;Barrière 2009 arXiv:0910.0488。

---

## 2026-05-29 — 条目 10:PyTTE / "Ferrara" 是什么、能否与 Geant4 组链路

纠正:PyTTE 与 Ferrara 不是一回事(之前连写 "PyTTE-Ferrara" 是误导)。
- PyTTE:开源 Python 包(Honkanen),解 Takagi-Taupin,算完美/弯曲单晶反射率 R(Δθ,E),Bragg+Laue。只给单晶反射率,不做整镜几何/光追。= "反射率那半"。
- "Ferrara":费拉拉大学 Laue lens 组(Frontera/Virgilli/Ferro),做弯晶制备/装配/TRILL-ASTENA + in-house 整镜射线追踪码(未公开)。不是开源工具。
- 替 Ferrara 角色的开源整镜光追:xrt(自带弯晶 TT)、McXtrace(蒙卡 X 光追,可搭 Laue lens)。HEART=镶嵌不弯;CrystalPy/XOP=单晶不整镜。

与 Geant4 结合(关键:PyTTE 只给反射率不给聚焦几何):
- 路 A(现实,少写码):PyTTE(R 表)→ xrt/McXtrace(弯晶整镜光追,出焦面相空间)→ Geant4/MEGAlib(探测器+本底+灵敏度)。形似当前链路,但光学从 Geant4 换成 xrt/McXtrace;代价:失去"Geant4 自己做衍射"创新点。
- 路 B(保留 Geant4 做衍射):PyTTE → 喂现有 --rocking-curve-map(反射率✓)→ 焦面 → MEGAlib。但聚焦几何仍要自己在 Geant4 写(大工作量);PyTTE 只省反射率半块。

结论:PyTTE 开源好接(反射率);弯晶整镜开源替代=xrt/McXtrace。要可信又少写码走路 A(Geant4 退为探测器/本底);要保留 Geant4 衍射卖点走路 B(逃不掉大工作量)。当下做镶嵌几何仍是对的;弯晶优先路 A。
(凭知识回答未联网核实仓库/许可证。)

---

## 2026-05-29 — 条目 9:这套物理能模拟弯晶吗?拓展工作量?

拆两半:
- 反射率/效率(>50%):能,几乎免费。外部曲线路 reflectivity 只 clamp 到 0.999999999,无 0.5 上限(0.5 封顶仅在内部镶嵌公式)。喂弯晶 R(Δθ) 曲线即成立,换数据不改代码。
- 聚焦/PSF:不能。当前"固定平面法向反射+镶嵌高斯"平进平出,结构上不聚焦;弯晶 1 arcmin 全靠单晶片自聚焦,必须换掉整个方向模型。

工作量:大。需要 法向随晶内位置按 1/R_c 连续变化的弯晶聚焦几何 + 弯晶窄摇摆曲线替代 30″镶嵌 + PyTTE 弯晶动力学反射率(2mm/R30m/Ge111) + 二维 QM 聚焦 + 厚晶像差 + PSF 对独立计算验证。做到论文可信≈在 Geant4 里重写弯晶 raytracer,而 Ferrara/Virgilli 已有成熟工具。玩具版聚焦中等工作量但 PSF 不可信,放进讲姜弯晶镜的论文是把柄。

结论(按用户规则"大则不给方案"):大工作量,不给方案。做镶嵌几何是对的。镶嵌定位="Geant4 EM 竞争离散 Laue 过程 + 镶嵌平晶基线 demo",弯晶列后续/走 PyTTE-Ferrara 现成工具。免费的半块(效率>50%)= PyTTE 弯晶曲线喂 --rocking-curve-map,1 天数据活,但单独不修 PSF,对"模拟弯晶镜"无用。

---

## 2026-05-29 — 条目 8:当前模型够不够模拟姜维春(IHEP)那台 511 弯晶 Laue 镜?

### 目标镜规格(姜维春 2024-05 报告,近期 511 望远镜)
- 能段 450–550 keV;A_eff >400 cm²@511;角分辨 1 arcmin(HPD);FOV ~4′;能量分辨 <0.1%@511(TES)。
- Ge(111) Laue lens,焦距 ~15 m,口径 ~30 cm(×3 模块),焦面 TES(像素化 100μm)。
- 晶体 = 自保持弯曲晶体(bent):柱面 1×3cm×2mm、曲率半径 30±1.5m;曲面焦距 15m;厚 ~1.7mm。
- 报告强调弯晶:单晶片自聚焦→更好角分辨;衍射效率 >50%(平晶上限 50%);展宽能区;对齐预算 10″。
- 中期:Laue+Wolter I,f30m,Laue 口径 ~3m;远期:FIONA 0.2-2MeV、100-1000cm²。

### 判断:不够——核心是 镶嵌平晶 vs 弯晶 的物理错配
当前 B-FULL = 镶嵌晶+平板 tile 模型(Darwin-Hamilton、0.5(1-e^-2σt) 封顶 0.5、平 G4Box、镶嵌高斯角展宽)。目标是弯晶。三个核心量给不对:
1. 衍射效率结构性封顶 50% → 给不出弯晶 >50%(整台镜的卖点);A_eff 系统偏低、能量依赖错。
2. PSF 全错:弯晶单晶片自聚焦(1 arcmin 来自曲率+对齐);当前焦斑来自固定平面法向+镶嵌 30″ 展宽。3cm 平 tile 反射平行束≈3cm 斑,弯晶聚成 ~mm → 差一两个量级。
3. 能区带通机制不同(弯晶曲率/QM vs 镶嵌 mosaicity)→ A_eff(E) 形状错。
参数级错配(可配但须改真值):f15m/demo8.3m;口径30cm-3模块/demo~13cm;晶体1×3cm×2mm弯晶/demo0.8mm平tile;厚1.7mm/10mm;A_eff>400cm²/demo0.57cm²;焦面TES未建。

### 可复用(架构是对的)
- G4VEmProcess + 标准 EM 竞争;
- 外部摇摆曲线 CSV 后端(--rocking-curve-map)= 关键钩子,换成弯晶反射率曲线即可;
- 焦平面相空间/tracked crossing 输出 = 交 TES+本底仿真的接口。

### 要"够"需补(真物理扩展)
1. 弯晶反射率模型(PyTTE 弯晶/Takagi-Taupin,或 XOP 弯晶模式,允许 >50%)→ 喂现有 CSV 后端。
2. 弯晶聚焦几何替换"平面法向反射+镶嵌高斯":曲率映射→指向焦点,角展宽用弯晶窄摇摆曲线(1 arcmin PSF 来源)。核心工作量。
3. 真实参数:Ge(111)、f15m、口径30cm/3模块、1×3cm×2mm弯晶、按 A_eff>400cm² 算真实晶体数(几百~上千)。
4. TES 焦面+本底(Geant4/MEGAlib)出灵敏度(×12 vs SPI)。

### 实操建议
- 论文="模拟姜这台 511 弯晶镜":当前模型不够,必须先做 #1+#2,否则 efficiency/PSF/A_eff 三个核心数不可信。
- 论文="Geant4 内可与 EM 竞争的离散 Laue 过程"方法学:镶嵌 5 环 demo 可发表(按条目6措辞),但不得声称代表姜那台弯晶镜;定位为"镶嵌平晶基线 demo,弯晶为后续工作"。
- 务实路径:先用 PyTTE 弯晶反射率当外部曲线接入(成本中等),弯晶聚焦几何作下一步,逐步从镶嵌 demo 走到弯晶镜。

一句话:当前模型是这台镜子仿真的合理骨架+镶嵌基线,但还不是它的可信模型——缺弯晶衍射(>50%)和单晶片聚焦(1 arcmin PSF)两块核心物理。补上前只能写成"镶嵌平晶基线/方法学",不能写成"姜维春 511 弯晶望远镜前端光学仿真"。

---

## 2026-05-29 — 条目 7:能否作为 511 keV 探测项目的前端光学系统写进论文?

### 直接结论
可以,但身份要摆对:它是论文里"前端聚焦光学的物理仿真模型",不是"探测器系统性能预测"。
此定位下站得住、可发表。差的不是光学物理,而是 真实镜设计 + A_eff(E) + 与焦平面探测器/本底耦合 三步。

### 现在能支撑(已验证)
几何自洽;单 tile 峰值反射率有 XOP 外锚(0.257 vs kernel 0.247);μ/消光长度经核对;EM 竞争下吸收/透射/衍射涌现;离轴效率物理跌落;焦斑涌现 d90≈0.34cm;输出焦平面相空间(交探测器仿真的接口)。
→ 可写:"Geant4 内、与标准 EM 竞争、消费外部 XOP 摇摆曲线的离散 Laue 过程,对前端聚焦光学端到端仿真"。真实方法学贡献(Guan2023 只做平板;此处全镜+生态桥)。

### 对探测项目还差什么(关键)
1. 现跑的是 5 环 demo(A_eff≈0.57cm²),不是真镜(几十~上百 cm²)。论文须用项目实际设计。
2. 没有 A_eff(E) 带通曲线(511 线+连续谱)。基础设施已支持扫能量,曲线未产出。
3. 没接探测器/本底 → 没有灵敏度。相空间接口就位,MEGAlib/Cosima 段未做。这是"光学模型"与"探测系统性能"最大鸿沟。
4. 镶嵌晶 vs 弯晶(ASTENA/TRILL 用弯晶求更小 PSF):首研可,须点明取舍。
5. 理想化未扫:完美对齐/平行 on-axis/无装配误差。真机性能由 <10 arcsec 对齐预算主导;代码能扰动法向但未扫。

### 论文定位/措辞
- 写成"前端光学仿真/方法学"章节,交付 A_eff(E)、PSF/d90、离轴响应。
- 不要写:Geant4 原生 Laue patch;"与 XOP 一致到 1e-11"当物理验证;探测灵敏度=X(除非做了#3)。
- 灵敏度单独成节,明确依赖焦平面探测器与本底假设。

### 进论文前最小补齐(优先级)
1. 真实镜参数重跑 → A_eff(E) + PSF/包围能量(前端光学最低交付)。
2. 焦平面相空间喂 MEGAlib/Cosima → 含本底的(哪怕粗的)灵敏度。
3. 失配扫描(扰动 tile 法向 vs <10 arcsec 预算)展示 PSF/Aeff 退化。
4.(可选)全镜独立 PSF(McXtrace/HEART 原生固定取向)。

### 待澄清
项目属于核天体物理(银心 511 线/ASTENA 类)、实验室正电子源、还是医学/PET?决定本底模型与镜设计,从而决定#1/#2 的源谱、能段、探测器几何。

一句话:当前这套可以且应作为论文前端光学仿真模块写进去(真东西、有外锚、能复现);但"作为探测项目前端光学系统"要兑现,必须补 真实镜+A_eff(E)+探测器/本底耦合;在那之前定位为"经独立基准校验的聚焦光学物理仿真",不是"探测系统性能"。

---

## 2026-05-29 — 条目 6:review HIGH-1 修复 + B-FULL 验证套件(Claude 实测复现)

### 总评
HIGH-1 真修好了,我用当前源码重建二进制独立复现确认。MED-2(外部 XOP 后端)、MED-3(离轴扫描)从"有能力没行使"变成"真在跑且进门控"。扎实收尾。

实测(均到 /tmp,未触碰 retained 报告):
- 当前源码重新编译(上轮 /tmp/bfull_build 是旧版)→ 编译/运行通过。
- 单 tile XOP 扫描(自跑):ok=True;p_reflect−XOP=6.76e-11(与 retained 完全一致);observed 0.22→0.023 随 XOP 曲线跌落;transmitted_space_rows 与 summary 匹配;G4VEmProcess base 确认。
- 直接跑:transmitted_space.csv 614 行(旧 0);estimated_standard_em_or_nonfocal_losses=542;tracked 焦斑 focal_crossing_spot_d90_cm=0.336cm。
- 门控有效:我那个旧二进制(没 transmitted 契约)被 all_transmitted_space_rows_match_summary=False 当场判负——非橡皮图章。

### 上轮 finding 处置
- 🔴 HIGH-1 假零/空 transmitted → ✅ 修复并验证:RecordFocalCrossing 写 14 列(876-880);transmitted_space_rows=614 匹配 CSV;旧字段加 *_field_scope 注释。
- 🟡 MED-2 H1 循环 → ✅ 真破:full-lens all_per_ring_sources_external=true + --require-rocking-curve-map;单 tile p_reflect−XOP=6.76e-11 读表保真。
- 🟡 MED-3 只取峰值/无离轴 → ✅ 行使:full-lens 离轴 [-5..5]′ 效率 peak/min≈27×(物理渐晕);单 tile ±30″ 跌到 0.023。
- 🟡 MED-4 G4VEmProcess 脆/badge → 〜 不变,新增 all_process_base_g4vemprocess 门控加固;"EM category" 仍是标签声明。

### Findings(本轮,偏小)
- 🟡 framing(重要):p_reflect−XOP~1e-11 是"读表保真"≠物理一致。真正物理校验是 xop_crystal benchmark(XOP 峰 0.257 vs Darwin kernel 0.247,Δ0.011)。论文别写"Geant4 与 XOP 一致到 1e-11"。
- 🟡 NEW-LOW-A:残留误导性顶层零值 n_absorbed:0/n_transmitted:0/absorption_fraction:0(已加 *_field_scope 注释)。更干净:删死字段或填涌现真值(abs≈542、trans≈614)。diffraction_fraction:0.293 是相互作用分数,非焦面通量(344/1500=0.23);算有效面积用 laue_diffracted_focal_crossings。
- 🟡 carry-over MED:离轴 ring2 observed peak/min=16.0 vs XOP 预测 24.7(~35% 缺口)。归因 EM+tile 平均+n=1000 统计;要么加统计要么定量解释。
- 🟢 LOW:run_lightweight_crosscheck 不重建 bfull 扫描(只重建 Python map-status,再按 status==needs_attention 门控 retained JSON)——合理但需文档写明"冻结+门控"且把 cmake 构建命令固化进 README(runner 默认找 /tmp/opticsim-bfull-build);non_focal_event_estimate 与 estimated_standard_em_or_nonfocal_losses 同值两名冗余;WRL 标题仍 "Geant4 11.4" 实际 10.2.3。

### 论文表述(与条目 5 一致 + 限定)
可写:custom Geant4 G4VEmProcess Laue 输运 + 标准 EM 竞争 + 逐环外部 XOP/CRYSTAL 有限-MFP 后端 + tracked 焦平面透射 primary;离轴效率物理跌落;固定取向涌现焦斑 d90≈0.34cm(比旧构造更诚实)。
不可写:Geant4 toolkit 原生 Laue patch;纯 G4VEmModel 截面表实现;完整 EM 吸收/透射分支已进 optics_history.csv;"Geant4 与 XOP 数值一致"当物理验证。

### 一句话
两个硬门都关上了,且我亲手重建+复现验证了 HIGH-1 修复与门控有效性(非只读 summary)。剩下全是表述层小事:别把读表保真卖成物理一致;清掉/填真残留 0 值字段;解释离轴 16 vs 24.7。骨架与证据链现已站得住。

---

## 2026-05-29 — 条目 5:Codex follow-up to 条目 4

### 判断
基本认同条目 4。需要更新两点:

- 外部 XOP/CRYSTAL per-ring map、off-axis、single-tile 与 full-lens retained
  报告已经闭合,不再只是"有出口未行使"。
- HIGH-1 成立:旧 B-FULL `n_absorbed/n_transmitted` 是 custom Laue branch
  计数,不是总 Geant4 EM 吸收/透射;`transmitted_space.csv` 也不应继续为空。

### 已跟进

- `laue_multiring_bfull_demo.cc` 现在在 `BFullFocalPlaneSteppingAction`
  记录 parentID=0 的真实焦平面 crossing 到 `transmitted_space.csv`。
- B-FULL summary 新增 `custom_laue_branch_scope`,
  `n_custom_laue_*`, `n_absorbed_field_scope`,
  `n_transmitted_field_scope`, `transmitted_space_source`,
  `transmitted_space_rows`, `estimated_standard_em_or_nonfocal_losses`。
- per-ring summary 表头从 `n_primaries/n_absorbed/n_transmitted` 改成
  `n_laue_process_interactions/n_custom_laue_absorbed/n_custom_laue_transmitted`,
  避免把 custom-process 诊断误读成全 Geant4 分支统计。
- 三个 B-FULL retained runner 均加入门控:
  `all_process_base_g4vemprocess=true`,
  `all_transmitted_space_rows_match_summary=true`。

### 当前保守表述

可写:custom Geant4 `G4VEmProcess` Laue transport + standard EM competition +
per-ring external XOP/CRYSTAL finite-MFP backend + tracked focal-plane
transmitted primaries。

不可写:Geant4 toolkit 原生 Laue patch、纯 `G4VEmModel` cross-section table
implementation, 或完整 EM 吸收/透射分支已进入 `optics_history.csv`。

---

## 2026-05-29 — 条目 4:review `laue_multiring_bfull_demo.cc`(用户实现的 Route B)

### 总评
真实、正确、实质性升级:从"反解对焦+强制过程+关EM"→"固定取向正演+有限MFP与开启的EM竞争+焦平面涌现PSF"。
实测:compile-only(G4 10.2.3 头)exit0;cmake 构建链接成功;单环 2000 事件 smoke run 正常退出,G4VEmProcess 运行期初始化不崩。
上轮 4 个结构性问题修掉 3 个;但 summary 分支统计有误报 bug,默认后端仍循环。

构建/运行环境:Geant4 10.2.3(MEGAlib 自带);构建 /tmp/bfull_build,smoke run /tmp/bfull_run(均临时,可删)。

### 上轮问题处置(带运行证据)
- E(EM 被关)✅ 修复:RegisterPhysics(G4EmStandardPhysics)(1337);run 中 ~594 primary 被 EM 吸收,597 次衍射有 134 个衍射光子出晶被 EM 吃掉(597→焦面 463)。
- M3(forced 过程)✅ 修复:GetMeanFreePath 返回 NotForced+有限 MFP(1224-1242);PostStepGPIL 委托 G4VDiscreteProcess::(1217-1222,已确认 G4VEmProcess:public G4VDiscreteProcess,合法)。
- M1(反解对焦)✅ 修复:FixedTilePlaneNormal(ring,tileId) 从 tile 中心定一次(489-494);outDir=反射过固定法向(1144)。涌现光斑 d90=0.327cm(更宽、诚实)vs 旧构造 0.219cm。
- H1(循环)🟡 加出口未默认:支持外部摇摆曲线 CSV(318-347,458-472),但本次 run backend=online_darwin_hamilton,仍硬编码常数(395-410)。
- M2(只取峰值)🟡 有能力未行使:离轴现在物理(固定法向→Δθ≠0),但默认单色 on-axis Δθ≈0:per-ring mean_p_diff=0.246844=旧峰值未变。
- 新增亮点 ✅:BFullFocalPlaneSteppingAction(1415-1438)记录真实焦面穿越,区分 diffracted/transmitted/other-gamma → 涌现 PSF,与解析投影分开。

### Findings
- 🔴 HIGH-1 吸收/透射统计是死的,summary 报假零。Record 只以 "DIFFRACT" 调用(1277);Record 内 ABSORB/TRANSMIT 分支(851-864)与 nAbs_/nTrans_(1100-1106)永不触发。
  实测:summary n_absorbed=0/n_transmitted=0/absorption_fraction=0/transmission_fraction=0,但实际 809 透射、~594 吸收;per_ring diffraction_fraction=1.0;transmitted_space.csv=0 行(旧 39560);optics_history 仅 DIFFRACT。→ 下游 cosima_bridge_transmit/full_lens 透射审计静默归零。这是 overclaim 风险。
  修法:真实吸收/透射从 focal_crossings 或 G4 sensitive detector 导出;用 tracked transmitted crossings 重填 transmitted_space.csv;删/改死计数器与 per-ring diffraction_fraction。
- 🟡 MED-2 H1 循环默认未破:默认 online_darwin_hamilton(硬编码常数=Python 同源)。已有 benchmarks/xop_crystal/multiring/ 逐环 XOP 曲线——验证级 run 用 --rocking-curve-map + --require-rocking-curve-map,Python 校验读同一 CSV。
- 🟡 MED-3 默认工作点仍峰值(M2):mean_p_diff=0.2468 实证 Δθ≈0。需真跑 off-axis+能量扫描才能支撑 A_eff(E)/离轴 PSF。
- 🟡 MED-4 G4VEmProcess 派生脆,收益仅 registered_in_geant4_em_category badge。EM model 是 no-op(1159-1180),GPIL 手工绕回 discrete 基类。普通 G4VDiscreteProcess+开 EM 物理等价且不脆。"EM category" 说法擦边(类型 fElectromagnetic 但不用 EM 截面表)。
- 🟢 LOW:WRL 标题 "Geant4 11.4"(1044)实际 10.2.3;类名 GuanStyleLaueBraggProcess vs 进程名 BFullLaueBraggProcess 漂移;phase_space 仍写解析投影命中(846-849)下游应优先 focal_crossings;MFP 用 0.5(1-e^{-2σt}) 解耦吸收合理但该式自带吸收假设有轻微双计;nDiff_/nAbs_/nTrans_ 用 double 存计数。

### 一句话
骨架对了,亲手编译+跑过确认工作。上线两个硬门:(1) 修吸收/透射假零统计;(2) 验证级 run 走外部 XOP 摇摆曲线 + Python 读同一文件真正破循环。再跑离轴/能量扫描兑现新架构价值。

---

## 2026-05-29 — 条目 3:如果是我,我会怎么做这套聚焦光学(Laue lens)模拟

### 0. 立场
当前 opticsim 的做法是"对准焦点 + 峰值反射率 + 关掉 EM"的快速一阶模型,够用但天花板低。
我会换成"固定取向正演 + 分层独立验证"的架构,让聚焦、有效面积、PSF **涌现**而非构造进去。

### 1. 文献现状(决定"正确做法"长什么样)
- 主流是专用射线追踪器 + 镶嵌/弯晶反射率模型(Virgilli/Frontera)。有效面积 = 几何投影面积 × 反射效率 R(E),**显式依赖能量**,必须扫能量,不能只取峰值。
- 现代趋势是**弯晶**(bent crystals)而非镶嵌晶:TRILL/ASTENA(50–700 keV,20 m 焦距,Ge(111)/GaAs(220)),PSF 目标 30 arcsec,晶面定位要求 <10 arcsec。→ **像差/失配建模是核心卖点**;"对准焦点"模型做不了。
- HEART(arXiv:2503.16955,Comput. Phys. Commun.,European XFEL 验证):开源镶嵌晶 X 射线追踪器,天然独立 oracle。
- **opticsim 的 "Guan-style" 直接源自 Guan et al. 2023**(`G4CrystalBraggReflection` + `G4DarwinDynamicalModel`)。但 Guan 原文里 Bragg 过程与**标准 EM 过程并存**注册;opticsim 反而把 EM 全关、用 MFP=DBL_MAX 强制触发——是对其引用工作的**倒退**,论文应说清。

### 2. 总体架构:先决定 Geant4 的角色(关键分叉)
- 路线 A(领域主流):射线追踪器优先。衍射+几何在专用追踪器(自研/HEART/McXtrace),Geant4/MEGAlib/Cosima 只做焦平面探测器 + 本底/活化。
- 路线 B(坚持 Geant4 原生,才是真创新):把衍射写成"真" `G4VDiscreteProcess`,给真实平均自由程 λ_diff(E,θ)=1/μ_diff,在 GetPhysicalInteractionLength 里与**保持开启**的标准 EM 竞争。不强制、不手填分支比、不关 EM。三分支比例成为**可检验的涌现结果**。修掉上轮 M3+E,与 Guan 原文一致。
- 我的选择:B 当头条贡献,A/HEART/McXtrace 当独立 oracle。

### 3. 衍射物理模块:forward,不要"构造"
- 每个 tile 固定晶体学取向(切割+装配定义的晶面法向),**与焦点无关**;聚焦从"各 tile 指向哪里"涌现。
- 给定 (E,k_in,命中位置) 算相对精确 Bragg 的 Δθ;反射率 R(E,Δθ) 取自镶嵌摇摆曲线(Darwin-Hamilton:结构因子→峰值 Q、镶嵌分布 W、次级消光、光电 μ),**能量+角度依赖、沿整条曲线采样,不锁峰值**。出射 = 跨采样晶粒法向反射(镶嵌从 W 采样;弯晶用曲率+Δθ 确定映射)。
- 反射率用独立 oracle 建表(XOP/XCRYSTAL diff_pat,或 PyTTE 单晶粒⊗镶嵌卷积),C++ 过程与 Python 校验**读同一张表** → 修掉 H1(同公式同常数的同义反复)。
- 从一开始同时支持镶嵌晶和弯晶(弯晶用 Takagi-Taupin/PyTTE)。

### 4. 源与采样
多色源覆盖全带 + on-axis 平行束(设计态)+ 发散/展源 + 离轴指向。
→ 得到当前算不出的两条核心结果:A_eff(E) 曲线 与 离轴 PSF/包围能量。

### 5. 缺陷与真实性(论文新意)
显式建模并扫描:晶面失配(<10 arcsec 预算)、逐 tile 镶嵌散布、tile 间隙、径向离焦、厚度公差、弯晶曲率误差;报告 PSF/Aeff 退化(对标 Virgilli 失配/畸变研究)。

### 6. 探测器 + 本底:Geant4/MEGAlib 真正用武之地
衍射/透射/散射相空间送入 Geant4/Cosima 焦平面位置灵敏探测器:电荷分享、逃逸、荧光,尤其**本底**(决定灵敏度)。把现有 bridge 做成实际科学产出。

### 7. 验证阶梯(逐层独立,零循环)
- L0 μ(E):xraylib CS_Total / NIST XCOM(换掉 xraydb)
- L1 结构因子/消光长度:xraylib Crystal_F_H_StructureFactor(已用 Cromer-Mann 验到 0.4%)
- L2 整条单 tile 摇摆曲线(峰值+积分+FWHM):XOP/CRYSTAL diff_pat × PyTTE 晶粒⊗镶嵌(**最关键,破循环**)
- L3 单 tile 三分支:正确 G4 过程涌现比例 vs 解析
- L4 全 lens PSF+Aeff(E):McXtrace / HEART **原生**固定取向(报告原生 PSF,不要 rebin 成自己的约定)
- L5 系统灵敏度:Virgilli/Frontera/Halloin(CLAIRE)文献设计表

### 8. 与当前实现的对照:我会逆转的 4 个选择
1. MFP=DBL_MAX 强制 + EM 关闭 → 真实 λ_diff 与开启的 EM 竞争(回到 Guan 原文)。
2. 晶面法向反解对焦 → 固定逐 tile 取向,聚焦涌现。
3. 概率只在摇摆曲线峰值 → 沿整条 R(E,Δθ) 采样 + 多色源。
4. C++/Python 各自硬编码同一批常数 → 单一反射率表(外部 oracle 来源)。

一句话:当前模型适合"快速出 on-axis 通量/几何图";我的设计支撑论文里 Aeff(E)、PSF、失配容差、灵敏度的定量声明。前者是后者的退化特例。

### Sources
- Guan et al. 2023, Adding the X-ray Bragg reflection process to Geant4 part I — https://pmc.ncbi.nlm.nih.gov/articles/PMC11935221/
- HEART (arXiv:2503.16955) — https://arxiv.org/abs/2503.16955
- Frontera & von Ballmoos, Laue Gamma-Ray Lenses: Status and Prospects — https://onlinelibrary.wiley.com/doi/10.1155/2010/215375
- TRILL project (arXiv:2309.11187) — https://sfera.unife.it/retrieve/0ea530be-383d-4353-b766-4d7e87bdec68/2309.11187v1.pdf
- Simulation of a Laue lens with bent Ge(111) crystals (arXiv:1511.02990) — https://arxiv.org/pdf/1511.02990
- Expected performance of a Laue lens based on bent crystals (arXiv:1211.4997) — https://arxiv.org/pdf/1211.4997
- Focusing effect of bent GaAs crystals: MC + experiment — https://link.springer.com/article/10.1007/s10686-015-9490-x
- Laue lenses review (2022) — https://www.worldscientific.com/doi/pdf/10.1142/9789811269776_0276

---

## 背景:前两轮审阅要点(条目 1–2 摘要)

**条目 1（Geant4 模拟是否生效 / 交叉校验是否成立）核心结论**
- Geant4 程序真实运行(G4RunManager/G4VDiscreteProcess/几何/tracking/G4UniformRand 三分支抽样)。
- 但它是 forced 过程(GetMeanFreePath→DBL_MAX, StronglyForced,仅在 fGeomBoundary 动作),非 cross-section 驱动;PhysicsList 只有 AddTransportation + 自定义过程,**未注册标准 EM**。
- **H1(高危,循环依赖)**:Python "独立 kernel" 与 C++ 同公式同常数(μ 常数 0.4321058247470657、消光长度 539.7909510452002e-4 cm 两处一致),且代数上 p_diff+p_abs+p_trans≡1 使 normalize 为 no-op → 5e-11 delta 只是跨语言浮点复现,非独立物理验证。
  - 文件:`opticsim/.../laue_multiring_darwin_guan_demo.cc:215,223,239-271` ↔ `laue511/probabilities.py:45-125`,`materials.py:13`。
- **H2(高危,HEART 光斑不独立)**:保留的 d90 由 opticsim 自己的 `_guan_direction_detector_image` 用设计方向+镶嵌/jitter 重建;HEART 原生(更窄、不一致)被丢弃。有效面积是真 HEART 跑出来的(可信独立量),光斑不是。
  - 文件:`tools/run_patched_heart_lens_oracle.py:258-308`,`tools/rebuild_heart_detector_from_tile_summary.py:45-62`,`reports/validation_status.md:104-116`。
- M1 晶面取向反解对焦(`demo:772-774`);M2 概率只在摇摆曲线峰值(`demo:779-781`,Δθ≈0);M3 forced 过程非 cross-section(`demo:801-804`)。
- production_validation_ready=false 是**硬编码包策略标志**(`validation_summary.py:77`),非模拟失败;状态门在任一必需检查 ok=False 时转 needs_attention。
- 生产 opticsim worktree **clean,未被交叉校验包改动**;交叉校验只读 opticsim CSV,边界干净。

**条目 2（如何用非实验手段校验）核心结论 + 实测**
- 实测更正:539.79e-4 cm = **539.79 μm**(非 5.4 μm)。
  - μ 拟合 vs xraydb:480–550 keV 误差 <0.11%。
  - 消光长度 vs Cromer-Mann 形状因子 + 金刚石 |F_111|≈155 的 Pendellösung 长度 ≈537 μm:**吻合 0.4%**。
  - 结论:两个硬编码常数物理上站得住;上轮 L3(常数未追溯)基本撤销。
- 验证路线见上方条目 3 的 L0–L5 阶梯;最优先两件:PyTTE→镶嵌卷积(破循环)、McXtrace/HEART 原生全 lens(测"非构造聚焦")。
- 零成本自诊断:`--offaxis-x-arcmin 5` —— 本模型逐光子反解对焦,离轴仍"完美聚焦",反差本身即证明聚焦是构造的。
