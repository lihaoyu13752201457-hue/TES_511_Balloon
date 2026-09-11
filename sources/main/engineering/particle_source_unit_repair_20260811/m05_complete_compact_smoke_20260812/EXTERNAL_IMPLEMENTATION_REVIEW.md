# 外部与已安装实现审查（输运前硬门）

> **HISTORICAL_WITHDRAWN__DO_NOT_USE_AS_CURRENT_CONTRACT.** 本文正文是反馈01时期的设计审查，
> 旧3-shard/12-cell/tape-v1/1% control/逐step deposits及“本轮必跑”措辞不再具权威。
> 当前治理合同 SHA-256 为 `5288aa348a1fa5f669e8ad0f6c8e2c0e51e7bbac2f7b911183379754167b14be`，
> 当前反馈02 SHA-256 为 `caa97d522214b9ef811a9b6d71a5307dffd9f551e5687f1c736bcfe081a2a1d7`，
> 当前机器状态只由 `EXECUTION_STATUS.json` 与write-once preflight artifacts定义。现计划为
> 28 cells/4 shards/40-column `m05-tape-root-v2`/448 jobs，TES与veto采用stream aggregates，
> full truth为raw-TES-positive加每shard前三行及stable-hash controls。F/U observer仅compile-only，
> P12 sentinel未运行，planned=448/runnable=0；`transport_authorized=false`、events=0。

状态：`PASS__SUFFICIENT_FOR_PREFLIGHT_ONLY__TRANSPORT_BLOCKED_PENDING_INDEPENDENT_REREVIEW`  
访问日期：2026-08-12  
执行合同 SHA-256：`5288aa348a1fa5f669e8ad0f6c8e2c0e51e7bbac2f7b911183379754167b14be`

本文件在任何新 Cosima 输运之前写成，随后按独立评估反馈 01 补齐不可变身份与实现边界。公开来源清单见 `external_sources.json`：论文使用显式 arXiv 版本/期刊 DOI，公开代码使用 40 位 commit 链接；公开仓库始终只是设计证据，实际执行 authority 是本机逐文件 SHA-256。评估反馈 SHA-256 为 `57f52999ced570af079344ea538935ce0505502003c05229597b85faadf78748`，其二次复核前禁止输运。

## 1. 公开实现事实与可迁移边界

### 1.1 COSI：完整质量模型、DEE 与同一重建链

- COSI 的 DEE 论文明确使用全面质量模型和逐条 strip/整机效应模型，并把 Cosima/Geant4 输出经 DEE 后送入和实测相同的 calibration、event reconstruction、imaging pipeline（[arXiv:1701.05563v1](https://arxiv.org/abs/1701.05563v1)，DOI `10.22323/1.285.0087`）。这支持“输运真值与电子学/响应分层”，不支持只留最终 511-keV 计数。
- 2016 COSI bottom-up 模型按小时构造 EXPACS/PARMA 环境，并分开 prompt 与 activation/delayed；三阶段方法先输运并存同位素，再按照射时间求 build-up，最后模拟衰变（[arXiv:2503.02493v2](https://arxiv.org/abs/2503.02493v2)，DOI `10.3847/1538-4357/add6a0`）。论文还用飞行/标定数据检验总谱和核素线。可迁移要求是：prompt 与 BUILDUP 输出合同可不同，但 `TT`、核素态、生产位置/体积和延迟源来源不能被 TES 紧凑表替代。
- COSI ACS 工作把极昂贵的 optical-photon transport 移出主输运，用单独完整 Geant4 光学模拟和实验标定建立位置/能量响应图，再送入 DEE（[arXiv:2409.12327v1](https://arxiv.org/abs/2409.12327v1)，DOI `10.1117/12.3020252`）。可迁移的是“把已独立验证的下游探测器效应参数化”；不可迁移的是跳过 BGO/CsI/plastic 中的高能粒子输运。当前 smoke 仍完整输运 O8 BGO、plastic、BPE 以及 alpha/e+/n，绝不把真实 veto 变成经验布尔量。

### 1.2 ComPair：EXPACS、Cosima、DEE、ACD 与 Compton/pair

ComPair 的公开背景工作把 EXPACS 多粒子环境送入含详细仪器和 gondola 的 Cosima，随后 DEE 模拟 coincidence/dead time/trigger/threshold/noise/ADC，再用 ACD、Revan 及 Compton/pair 分类分析；软/硬 ACD 是保留信息后比较的两种策略（[arXiv:2506.15916v2](https://arxiv.org/abs/2506.15916v2)，DOI `10.3390/particles8030069`）。它说明高能 shower/pair 会决定 ACD 和 511-keV feed-down，故不能因为小样本 W2 survivor 为零就删高能支持或 e+/alpha 机制。未找到官方公开 ComPair 实现仓库，清单明确记录 `NOT_FOUND__PAPER_ONLY_DESIGN_EVIDENCE`，没有杜撰 commit。

### 1.3 cosipy 与 phase-space/response 表示

- cosipy 的 commit `feae2fc518d41314b58ac4b8d079803cefca4bc5` 中 `FullDetectorResponse.py` 使用版本化 HDF5 `DRM`，显式保存 `AXES`、`COUNTS`、`EFF_AREA`；方向轴为 `NuLambda`，测量空间至少含 `Ei/Em/Phi/PsiChi`，并按方向 chunk/cache 读取（[不可变源文件](https://github.com/cositools/cosipy/blob/feae2fc518d41314b58ac4b8d079803cefca4bc5/cosipy/response/FullDetectorResponse.py)）。稳定 v0.3.4 的 peeled commit `5134b1d49d68dc52c219bc1453918d49d2ad66fb` 使用较旧 schema，两者没有混称为同一版本。它支持版本化、分块的派生 response，不是删掉 event truth 的依据。
- COSI atmosphere commit `1236ffd0e745fac7196ccc41e93bd654ef08458a` 的教程同时保存 all-thrown 与穿过 watched boundary 的 event list，再构建角度/能量 HDF5 response（[不可变教程](https://github.com/cositools/cosi-atmosphere/blob/1236ffd0e745fac7196ccc41e93bd654ef08458a/docs/tutorials/spherical_mass_model/spherical_mass_model_tutorial.ipynb)）。这支持未来经验证的 phase-space boundary reuse，但本项目两个几何在边界内仍有不同被动/主动材料，不能在未证明 Markov 边界与权重闭合前共用内部 shower。

### 1.4 Geant4：MT、production cut、biasing、scoring

- 官方 MT 模型是 `G4MTRunManager` master/worker 的 event-level parallelism，几何和 physics table 共享，user actions/hits 为线程私有；事件完成次序不保证顺序（[官方 MT 文档](https://geant4.web.cern.ch/documentation/pipelines/master/bftd_html/ForToolkitDeveloper/OOAnalysisDesign/Multithreading/mt.html)）。本机 Geant4 10.2.3 库虽带 `G4MULTITHREADED`，当前 Cosima `MCRunManager` 直接继承单线程 `G4RunManager`，所以不能把 `mcosima` 称为线程化输运。
- region cut 是次级粒子 production threshold，而非 tracking energy kill（[region cut](https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/TrackingAndPhysics/cutsPerRegion.html)，[threshold versus cut](https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/TrackingAndPhysics/thresholdVScut.html)）。改变它会改变局部沉积、电子/光子次级以及 pair/annihilation 细节；没有完整 matched closure 前不能进生产。当前 smoke 不改 cut。
- Geant4 importance sampling 在跨 cell 时 splitting/Russian roulette 并改变 history weight；analog 与 biased 均值应相同但方差不同。官方也警告每个粒子类型、cell 和 importance 都需物理判断（[biasing 文档](https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/Fundamentals/biasing.html)）。若目标分布为 `p(x)`、抽样分布为 `q(x)>0`，prompt 单历史权重为 `w=p(x)/q(x)`，估计量为 `sum(w_i f_i)/N_q`；splitting 子历史权重为父权重除以复制数，roulette 以存活概率 `s` 留存时存活权重除以 `s`。activation 必须对每个 RP 同样携带 root weight，并用 `sum(w*RP)/sum(w*TT contribution)` 的预注册曝光合同验证，不能用 prompt survivor 权重代替。
- 标准 hits/scorers适合聚合剂量/通量，但 M05 还要 TES pixel UID、interaction order、pair/annihilation ancestry 与逐 RP root lineage，故只用 primitive scorer 会丢信息。官方 phase-space 示例可作边界复用先例，但须另做全带宽、重粒子、两几何 matched pilot。

结论：这次只冻结输出表示/序列化的安全因果臂。cut、物理过程裁剪、能段限制、importance/splitting/RR 和 phase-space reuse 均记录为后续显式 weighted candidate；在本烟雾的稀疏统计下无法证明 M05 全观测量无偏，故不以它们制造速度数字。

## 2. 已安装 MEGAlib/Cosima 源码审查

安装根：`/home/ubuntu/MEGAlib_Install/megalib-main`；无可用 `.git` 元数据。生产基线 `bin/cosima` SHA-256 为 `3fb7613de58ebb365f2a55c3336e54d2aabea2a4ddb282003a5d25eac6f1c74a`，MEGAlib 4.02.00，Geant4 10.02.p03。

### 2.1 COSI balloon mass model

- `resource/examples/geomega/cosiballoon/README.md:1-13` 称其为 2016 COSI balloon 官方 v4，并指定 9/10/12 detector setup；`:28-31` 说明 detector-head-only 含主要质量且 surrounding sphere 较小，gondola 更大、更慢；`:41-55` 明列模型近似/遗漏。
- `COSIBalloon.12Detector.geo.setup:5-30` 包含 shields、12 active GeD、upper/lower shield、detector head、thermal radiator、graded-Z，surrounding sphere 半径 60 cm。
- `Shields.det:4-65` 把各 CsI panel 定为 sensitive scintillator 并给出 80 keV threshold；`:68-76` 的 trigger 是 `Veto true`、按 detector 触发。
- `COSIBalloon.WithGondola.geo.setup:3-38` 使用 150-cm sphere 且当前引用本目录不存在的旧文件名，因而只作范围/成本证据，不作为本 smoke geometry。

映射：完整 detector-head 而非只留 detector 是本项目 mass-complete 思路的外部先例；但 COSI 的 Ge/CsI 命名、阈值、材料均不能直接替代 TES/CsI/BGO/plastic 规则。

### 2.2 ModifiedCosimaOutput 与 EventList

- `resource/examples/advanced/ModifiedCosimaOutput/ReadMe.txt:18-24` 指定 `MCMain::SetEventRelegator`，回调收到新鲜 `MSimEvent*`，并建议注释 `FileName` 关闭标准输出。
- `ModifiedCosima.cxx:56-62,69-104` 展示固定二进制 struct、缓冲和临时文件 rename；`:106-178` 从 IA 中选择 INIT/ANNI/COMP/RAYL/终止过程；`:199-203,222-245` 注册回调。它只证明可扩展输出模式：回调晚于富事件构造，且无法单独补回 `AddIsotope` 时的 root/material/logical volume，因此不再把 event relegator 称为完整 C 臂。
- `resource/examples/advanced/EventList/EventListCreator.cxx:216-277` 写 ID、successor、particle/state、time、position、direction、polarization、energy；实际 parser `src/cosima/src/MCSource.cc:2228-2307` 要求严格 15 token，单位分别 s/cm/keV，并每批最多读 500,000 条。
- `src/cosima/src/MCParameterFile.cc:977-1005` 规定 EventList source 不可同时有其他源参数。`MCSource.cc:2281` 虽解析 row ID，但它没有传播到事件，且 `:2291` 把 file-EventList volume 置空；因此 frozen tape 还必须有按行 sidecar，并由隔离 hook 在消费前传播 ID、在末端核对唯一 IA INIT。scorer 不调用 RNG。

### 2.3 当前富事件构造与 N0/N1/C 边界

- `MCEventAction.cc:142-191` 表明 run `FileName` 为空只令 `m_SaveEvents=false`。
- `MCEventAction.cc:381-426` 的 `AddIA` 总是 new/add，`AddComment` 总是保存 CC；没有 `m_SaveEvents` 守卫。
- `MCEventAction.cc:487-638` 总是取全部 sensitive hit collections、求能量并跑 trigger；`:659-746` 对被选事件仍 `PrintAllHits()` 并构造 PM/HT；`:774-780` 在保存函数之后调用 relegator。
- `MCEventAction.cc:895-905` 只有最终 `ToBinary/ToSimString` 和写文件受 `m_SaveEvents` 守卫。因此：N1 可由当前二进制 + 空 FileName 安全实现；它不是 N0。C 通过 relegator + 空 FileName 避免全事件序列化/压缩，但仍承担富 IA/CC/HT 构造成本。
- `MCParameterFile.cc:357-375` 接受 all/init-only/none/ia-only，而 deposits-only 被注释；`MCSteppingAction.cc:211-219` 虽设置 `m_StoreSimulationInfo`，实际各过程的 `AddIA` 调用（如 COMP/PAIR/ANNI 在 `:428-555`）没有受该变量统一保护。因此不能把 `StoreSimulationInfo none` 宣称为 N0。
- 本地 `MCSteppingAction.cc:60-180` 不是可假设的上游原版：它额外把逐 sensitive step 写为 `CC HIT`，并在真正 `AddIsotope` 同一处写 `IP RP`；`:1028-1062` 先发精确 RP 注释再进入聚合 store；`:1456-1466` 每个 sensitive step 后发 HIT。所有基线/紧凑臂必须绑定这些文件的 hash。

N0 需要修改 event/stepping/hit 构造路径，且生产 `cosima` ELF 把 `libCosima.so` 以绝对 NEEDED 路径固定。未先做隔离重链接、ABI/物理回归，就无法安全执行 N0。本轮允许先执行 F/C/U/N1；若隔离 N0 build 未通过，不得声称纯 Geant4 stepping/transport 的因果 speed decomposition 或 physics-algorithm speedup。仍可按预注册统计合同报告 matched F/C 端到端 simulation-output-path wall ratio 及其 lower-95% gate。

### 2.4 Sensitive detectors、activation 与 region/physics

- `MCEventAction.cc:499-534,538-574` 枚举 2D/3D strip、calorimeter、voxel、scintillator、drift、Anger hits；`:583-631` 把 calibrated hit 送入 trigger。这些对象是 TES 和真实 veto 能量的原生来源。
- `MCPhysicsList.cc:113-177` 注册 Livermore/Penelope/standard EM、QGSP_BIC_HP 等 hadron list，并始终注册 radioactive decay；`:325-335` 先 default cuts，再按 region range cut 设置 production cuts。
- `MCDetectorConstruction.cc:1067-1107` 要求 region root 是 geometry 中真实非 virtual volume；`MCRegion.hh:53-68` 还可 `CutAllSecondaries`。后者会直接杀次级，不适合未验证的高能 shower/activation 优化。
- 原生 `MCIsotopeStore.cc:166-193` 只写 `TT`、`VN`、`RP ZA excitation value`；`MCRun.cc:292-309` 按 logical volume 聚合，故它没有 exact position/material/root lineage。M05 完整 BUILDUP 必须同时保留本地 `IP RP` sidecar；原生 `.dat` 仍是 TT/聚合交叉核验 authority。
- `MCActivator.cc` 读取每个 isotope file 的 TT 后合并、除总时间并做 constant irradiation/cooldown。任何 compact contract 都必须保留零-RP job 的正 TT，且不能只汇总有 RP 的 job。

### 2.5 Background/Activation/CoolDown/Pipeline/DEE examples

- `resource/examples/advanced/Background/Background.txt:34-70` 明确分 photonic/leptonic、hadronic prompt/build-up/decay，并要求 prompt 产 isotope list、build-up 用单个 cosima、再跑 decay。
- `ActivationPlotter/CreateSourceFiles.py:75-150` 生成 Step1 `ActivationBuildup + IsotopeProductionFile`、Step2 constant irradiation activator、Step3 delayed decay。
- `CoolDown/ReadMe.txt` 和三份 Phase source 保持 irradiation、cooldown、timed decay 分层；`CoolDown.cxx` 用 event time 与 reconstructed energy，说明 time 不是可删元数据。
- `Pipeline/Readme.txt:1-16` 与 `SimulateSources.sh:95-117` 生成窄线/宽线/continuum，启动独立 cosima 进程，随后跑同一 `mrevan`；它不是线程内 transport。
- 安装例 `DetectorEffectsEngine.cxx:168-225` 读取 event、按 `MDVolumeSequence` 聚类并填 energy/depth/surface；它只是一个轻量输出消费者示例，不是 COSI 逐 strip DEE。它证明 volume sequence/position 若被删，后续 detector-effects/response 无法恢复。

### 2.6 dcosima/mcosima/mpicosima 与调度

- `bin/mcosima:30-55` 自称同机 parallel，但 `:399-432` 实际为每 worker 从 `/dev/urandom` 取 seed 并启动独立 `cosima`；`:467-569` 生成 `IN` concatenation manifest。它不满足 matched seed/tape 与 arm 轮转。
- `bin/mpicosima:4-23,156-165` 用 MPI `bundler` 分发独立 cosima 命令和不同 seed，不是 Cosima 内部 MT。
- `bin/dcosima:36-60` 是远程提交/rsync 工具；本任务没有远端授权，也不使用。
- 本机 Geant4 config 含 `-DG4MULTITHREADED`，但 `src/cosima/inc/MCRunManager.hh:43-49` 明确继承 `G4RunManager`。把应用迁移到 `G4MTRunManager` 还需把全局 `MCEventAction`、isotope store、relegator、ROOT 和输出变为 thread-safe，超出安全 smoke。当前 runner 采用显式进程、固定 tape/seed、三 subshard、arm 顺序轮转，并串行 O8 n/e+/alpha。

## 3. 输运前候选映射与冻结决定

| arm | 本地模式 | 是否改物理 | 可归因成本 | 本轮决定 |
|---|---|---:|---|---|
| F | 当前 `cosima`，rich gzip | 否 | transport + rich 构造 + stringify + gzip + I/O | 必跑参考 |
| U | 当前 `cosima -u`，rich plaintext | 否 | transport + rich 构造 + stringify + I/O | 必跑 |
| N1 | byte-copy shadow transport + root observer，空 FileName | 否 | transport + rich 构造；无 event stringify/file；observer 开销单列 | 二次复核后必跑 |
| C | 在 Begin/EventList/敏感 step/真实 AddIsotope 提交/EndRun 的隔离 typed hook，空 FileName，紧凑 sidecar + candidate/control native truth | 否 | 与 N1 同富构造 + compact encoding | 编译/单元测试且二次复核后必跑 |
| N0 | 禁用 IA/CC/HT/字符串对象 | 本意不改，但需改引擎控制流 | transport/hits 最低边界 | 只有隔离 build 与回归全过才跑；否则精确 BLOCKED |
| CUT/PHYS | region cut、process 配置 | 是 | transport stepping | 稀疏 smoke 不能证明高能 shower/pair/activation 等价；本轮 NO_GO candidate |
| BIAS/STRATA | energy/direction `q(x)`、splitting/RR | 统计测度改变 | survivor efficiency | 需逐 history/root weight 和 prompt/activation 方差研究；本轮 REVIEWED_NOT_EXECUTED |
| PHASE | watched-boundary phase space | 边界外输运复用 | 外部 transport | 需两几何共同边界与全机制 closure；本轮 REVIEWED_NOT_EXECUTED |

首个可执行实现采用 F/U/N1/C，完全相同的 geometry、LivermorePol、QGSP_BIC_HP、DecayMode、production cuts、Geant4 data、EventList tape 和 transport seed；C scorer 不取随机数。每条 tape sidecar 冻结 row index、stable root、driver/family、完整 primary tuple、source-card/source-contract/donor-SIM provenance；Geant4 对 direction 执行 `.unit()`，所以同时保留原始行哈希和规范化生成 tuple 哈希。BUILDUP RP 在原生 `AddIsotope` 返回单调提交序号后逐条写出，并与 DAT 聚合及零-RP 正 TT 闭合。C 的 selected/control truth 是 stable-root 哈希的预注册 1% 规则，不能按运行结果事后调参。

## 4. 硬门结论

可靠公开源访问完整；已安装源、examples、调度脚本和关键引擎路径均可读。只允许进入“合同/静态 tape/scorer build/preflight”。外部审查不是 transport PASS；独立反馈 01 的二次复核前，`transport_authorized=false` 且事件计数必须为零。七族投影还必须把未测 e−/μ± 及漏掉的 gamma-BUILDUP/n-prompt cells 设为 no-benefit；若该下界已超过 80 GB，则本最小 smoke 不可宣称 full-target capacity GO。
