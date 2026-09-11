# neutron_fen 唯一入口交接（2026-09-03）

> 新会话必须从本文件开始，完整阅读后再安装或运行。除本文件列出的当前
> SH3/Si-SD 产物外，不得把旧几何、旧质量模型、旧源口径或历史优化结果
> 引入本任务。

## 1. 用户要求与工作边界

新会话的目标依次为：

1. 复习当前 M05 项目和本次 SH3 大气中子/Si 衬底模拟结果；
2. 安装并验证 Geant4CMP；
3. 完成 Si 衬底能量向 TES 声子/热脉冲耦合的模拟评估，判断其是否会在
   $510.58$--$511.42\,\mathrm{keV}$ 窄线 ROI 内形成未 veto 背景。

所有新代码、下载、源码、build、install、日志、模拟和报告必须写在：

```text
/home/ubuntu/neutron_fen
```

`/home/ubuntu/TES_511_Balloon` 及其 Codex worktree 只读使用。不得修改论文、
现有几何、源卡、SIM、CSV、JSON、图件或未提交文件。不得复制 17 GB SIM
到新目录；优先使用本文件列出的紧凑目录。不要扫描无关的大型 SIM/NPZ/job
catalog。不得读取错误任务 `01a02314-a50b-78d2-bb8c-b43ffa350704` 的产物。

当前论文只保留 SG3（质量模型 A）和 SH3（质量模型 B）；本任务只研究当前
SH3。不得恢复或引用历史质量模型作为物理权威。除非用户另行要求，不改论文。

## 2. 项目和论文口径

当前 M05 总入口：

```text
/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/M05_CURRENT_SESSION_HANDOFF_20260823.md
```

当前英文稿（只读，必要时用于术语/口径核对）：

```text
/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/balloon511_ea_draft_en_sg3_sh3_revision_20260830_step01_intro.tex
```

必须区分三个能量概念：

- TES 响应假设：511 keV 处 FWHM 为 420 eV；
- 当前未分辨线科学 ROI：$511\,\mathrm{keV}\pm420\,\mathrm{eV}$，即
  $[510.58,511.42)\,\mathrm{keV}$，总宽 840 eV；
- 480--550 keV 在当前论文中是探测器侧背景/选择诊断区。当前信号模拟仍是
  单环、单色 511 keV 参考响应，并未给出完整的 480--550 keV 宽带
  $A_{\rm eff}(E)$、PSF 和源灵敏度折叠。

Si 衬底事例绕过 Laue 光学。不能在原始 Si 沉积谱上先施加 480--550 keV
光学带宽；正确次序是：完整 Si 沉积 $\rightarrow$ 声子/热耦合 $\rightarrow$
TES 重建响应 $\rightarrow$ 511-keV ROI。

## 3. 当前 SH3+Si-SD 输运权威

本次独立、非覆盖工作包：

```text
/home/ubuntu/TES_511_Balloon/engineering/geometry_optimization_20260815/72_sh3_si_substrate_sd_neutron_canary_20260903
```

关键几何：

```text
geometry/SH3_Assembly_OptV3_SiSubstrateSD.det
geometry/SH3_Assembly_OptV3_SiSubstrateSD_60cm.geo.setup
```

只在当前 SH3 的六层 Si substrate proxy 上新增了六个诊断 Scintillator SD，
阈值 0.001 keV；没有把 Si 声称为 TES，也没有建立 Si-to-TES 热响应。底层
SH3 `.geo`/`.det` 与当前论文模型 B 一致。Geant4 production range cut 为
$5\,\mu\mathrm{m}$。

输运配置与权威状态：

```text
production_10m/config.json
production_10m/run/controller_state.json
production_10m/FINALIZER_STATE.json
production_10m/generated/job_plan.json
production_10m/generated/seed_registry.json
production_10m/generated/source_manifest.json
```

统计量与归一化：

- 原始 all-event canary：100,000 个中子，TT = 19.1897 s；
- 正式批次：99 x 100,000 = 9,900,000 个中子，99/99 回执全部 PASS；
- 合计：10,000,000 个中子；
- 合计等效时间：1911.8824 s = 31.8647067 min = 0.5310784 h；
- 100 个 SIM 合计 17,398,005,050 bytes；
- 正式批次使用 `PreTriggerMode everyeventwithhits` 与
  `StoreSimulationInfo all`。同种子 10k 验证已证明所有具有敏感体命中的
  IA INIT 和 TES/Si/BGO CC HIT 与 all-event 存储逐行一致：
  `HITSONLY_VALIDATION.json`；
- 中子源为 particle-source-unit-repair 包中的 corrected-keV full-sphere
  20-bin 源；源卡中旧 `cosima_spectra_dp_2602units` 引用为零；
- Cosima 使用 MEGAlib 内置 Geant4 10.2.3、QGSP_BIC_HP 和
  Livermore polarized EM。该 Geant4 仅是上游输运环境，不得被 Geant4CMP
  安装覆盖。

## 4. 已完成的中子/Si 结果

首先阅读：

```text
production_10m/analysis_10m/si_deposition_summary_10m.json
production_10m/quick_parallel_recoil_audit.json
production_10m/recoil_spectrum/strict_si_elastic_recoil_spectrum_10m.json
production_10m/recoil_spectrum/strict_si_recoil_thermal_coupling_screen_10m.json
production_10m/recoil_spectrum/strict_si_elastic_recoil_spectrum_10m.png
```

完整紧凑目录：

```text
production_10m/analysis_10m/si_event_catalog_10m.csv
production_10m/analysis_10m/si_hit_catalog_10m.csv
production_10m/recoil_spectrum/strict_si_elastic_recoil_events_10m.csv
production_10m/recoil_spectrum/strict_si_elastic_recoil_spectrum_10m.csv
```

SIM 只有在紧凑目录不足以完成某项审计时才允许读取，且只限上述工作包内
由 99 个 PASS receipt 绑定的文件与原 100k canary；不要扫描别的 run。

两条独立流式解析链得到完全一致的主要结果：

- 任意 Si 正沉积：3161 事例；
- 严格 Si 弹性反冲定义：Si SD 的 CC HIT 同时满足 secondary=`Si*`、
  parent=`neutron`、creation process=`hadElastic`；
- 严格弹性反冲：533 事例（0.27878284 s^-1）；
- 其中 BGO < 50 keV：51 事例（0.02667528 s^-1）；
- 严格反冲能量：min 0.5224525 keV，median 29.14737 keV，
  q90 140.477042 keV，q99 549.2515072 keV，max 1407.3428 keV；
- 严格反冲在 480--550 keV：3 事例，其中 2 个 BGO<50 keV；
- 严格反冲直接落入 $[510.58,511.42)$ keV：0；
- 严格反冲分量 >=511 keV：6，其中仅 1 个 BGO<50 keV；
- 所有 Si 正沉积中 BGO<50 keV：86 事例；热评估不能只看 51 个严格反冲，
  因为 TES 热系统不识别 Geant4 过程标签。

## 5. 三个未 veto 的必要能量学候选

先采用最简单但可审计的能量平衡：

\[
E_{\rm rec}=E_{\rm TES,direct}+\eta E_{\rm Si,total},\qquad 0\leq\eta\leq1.
\]

在全部 86 个 BGO<50 keV 的 Si 正沉积事例中，只有三个存在某个
$\eta\in[0,1]$ 可进入窄 ROI；这只是必要条件，不是热模型结论。

### 候选 A：严格反冲

- job/event：`sh3_sisd_n10m_shard0037`, event 989；
- L1；单个 Si28 hadElastic HIT；
- Si/反冲 = 508.801 keV；直接 TES = 17.13377 keV；BGO = 0；
- global position = (-28.22312, -0.8229261, 24.35640) cm；
- hit time = 4.863801 ns；
- 到 511 keV 所需 eta = 0.97064713；
- 进入 ROI 的 eta 区间 = [0.96982166, 0.97147260]。

### 候选 B：严格反冲

- job/event：`sh3_sisd_n10m_shard0049`, event 2764；
- L4；两个相邻 Si28 hadElastic HIT：529.9021 + 38.38494 = 568.28704 keV；
- 直接 TES = 0；BGO = 0；
- global positions 约 (-25.94176, 1.489410, 21.53913) cm；
- hit time 约 10.146 ns；
- 到 511 keV 所需 eta = 0.89919348；
- 进入 ROI 的 eta 区间 = [0.89845441, 0.89993254]。

### 候选 C：非弹性中子次级级联（不是严格反冲，但会加热 Si）

- job/event：`sh3_sisd_n10m_shard0049`, event 639；
- L0；neutronInelastic gamma 后续 Compton/electron 级联；
- Si total = 387.3621815 keV；直接 TES = 458.391770806 keV；BGO = 0；
- 主要 Si 命中时间约 21.826--21.940 ns；详细位置/逐 HIT 见完整 hit catalog；
- 到 511 keV 所需 eta = 0.13581147；
- 进入 ROI 的 eta 区间 = [0.13472722, 0.13689573]。

候选 C 所需耦合率仅约 13.6%，比两个严格反冲候选更需要优先验证。最终评估
必须覆盖全部 86 个未 veto Si 事例，不能只模拟 A/B。

## 6. 本机可用构建环境（只读复核后使用）

独立 Geant4 11.4.0 已存在：

```text
/home/ubuntu/software/geant4-11.4.0-install
/home/ubuntu/software/geant4-11.4.0-install/bin/geant4-config --version  # 11.4.0
/home/ubuntu/software/geant4-11.4.0-install/lib/cmake/Geant4/Geant4Config.cmake
```

其他环境：

- CMake 3.22.1；
- GCC/G++ 11.4.0；
- ROOT 6.36.06（当前 shell 默认来自 MEGAlib）；
- MEGAlib 自带 Geant4 10.2.3：
  `/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03`。

不要修改 `/home/ubuntu/software/geant4-11.4.0-*` 或 MEGAlib。Geant4CMP 必须
安装到 `/home/ubuntu/neutron_fen` 内的独立 source/build/install 前缀。开始前
从 Geant4CMP 官方仓库/文档核对当前版本与 Geant4 11.4.0 的兼容性，不能假定
兼容。若不兼容，在 `neutron_fen` 内构建一个被支持的 Geant4 版本；不得替换
现有安装。需要系统包或 sudo 时先向用户请求批准。

## 7. 新会话执行顺序和最低验收标准

### 7.1 安装与 smoke validation

1. 记录主机资源、工具链和现有 Geant4 11.4.0 的 CMake feature 配置；
2. 只用 Geant4CMP 官方仓库/发行说明确认兼容矩阵，固定 commit/tag；
3. 在 `neutron_fen/src`, `build`, `install` 分离安装；
4. 保存 clone commit、submodule、CMake cache、编译日志和环境脚本；
5. 运行官方最小声子示例，要求可重复、正常退出、产生非零声子/传感器输出；
6. 若示例未通过，不得进入物理结论阶段。

### 7.2 几何和物理模型

先建立一个最小但与当前 SH3 一致的单层单元：Si substrate proxy、Ta absorber、
TES/收集界面、支撑/热浴边界。尺寸与相对位置从当前 SH3 `.geo/.det` 只读提取，
不得凭空发明。论文明确指出 Si 是 SiO2--SiNx--Si 的 proxy，且没有逐层 TES、
布线和真实界面；因此未知参数必须作为显式参数包络，而不是暗中取单值。

Geant4CMP 负责 prompt/athermal phonon 传播、界面损失、表面散射、进入各 TES
收集界面的能量与到达时间。FEniCS 只在 Geant4CMP 表明慢热化、层间热串扰或
恢复时间可能重要时用于连续介质热扩散；不能用 FEniCS 替代弹道/非热声子。

### 7.3 模拟阶梯

1. 单能/单点单元测试：约 30、140、500、568、1407 keV，在中心/边缘和不同
   深度注入，验证能量守恒及边界条件；
2. 精确复现候选 A/B/C 的层、位置、总沉积和时间结构；
3. 扩展到全部 51 个未 veto 严格反冲；
4. 最终扩展到全部 86 个未 veto Si 正沉积事例；
5. 对每个事例输出每 TES 的 prompt/late collected energy、到达时间分布、
   channel multiplicity、总收集率 eta；
6. 使用论文当前事件求和口径，加入直接 TES 沉积，形成重建能量/脉冲；
7. 卷积 420 eV FWHM TES 响应后再施加 $[510.58,511.42)$ keV ROI，并沿用
   上游 BGO<50 keV 条件；
8. 报告进入 ROI 的期望事例数/率及有限样本不确定度。不得把“存在某个 eta”
   当作真实事件概率。

### 7.4 最终判断必须回答

- 候选 A/B 的约 97.1%/89.9% 收集率在实际几何中能否达到？
- 候选 C 的约 13.6% 收集率是否能达到，脉冲是否与 511-keV Ta 吸收脉冲同形？
- 能否通过 pulse shape、channel multiplicity、arrival time 或 substrate tag
  排除，而不损失真正 focused 511-keV signal？
- Si 衬底引起的 511-keV ROI 背景是否可忽略；若可忽略，给出数值上限；若
  不可忽略，给出应加入 SH3 响应链的校正率及不确定度。
- 480--550 keV 其他能量只在完成 Si-to-TES 映射后解释。局部衬底背景不受
  Laue 光学通带保护；ROI 外事例仍可能贡献触发、死时间、堆积和边带诊断。

### 7.5 新目录应交付

至少建立：

```text
/home/ubuntu/neutron_fen/README.md
/home/ubuntu/neutron_fen/INSTALL_MANIFEST.json
/home/ubuntu/neutron_fen/env/
/home/ubuntu/neutron_fen/src/
/home/ubuntu/neutron_fen/build/
/home/ubuntu/neutron_fen/install/
/home/ubuntu/neutron_fen/config/
/home/ubuntu/neutron_fen/code/
/home/ubuntu/neutron_fen/runs/
/home/ubuntu/neutron_fen/outputs/
/home/ubuntu/neutron_fen/FINAL_EVALUATION.md
/home/ubuntu/neutron_fen/FINAL_EVALUATION.json
```

所有运行要有固定 seed、配置快照、stdout/stderr、输入/输出哈希和非覆盖目录。
最终 README 必须给出一条从干净 shell 复现安装 smoke 和物理评估的命令链。

## 8. 关键哈希

```text
1f2ee4e4535da77d8cc5728bc6bb5a454967d2ea8cef66219de64e1752534e62  si_deposition_summary_10m.json
a6c635c40c3a6a673d4a315b967a5fe0c1473469842e55b5a476e0b9fb151c0d  quick_parallel_recoil_audit.json
ee7453385bb4bceb484ff015f313b22aa11be7fa2e0575a93f5786c1205718dc  strict_si_elastic_recoil_spectrum_10m.json
27b9bdcf1c67ea7f64a69621c0e3387174e93e403aea363f8ea81f61009a08ed  strict_si_recoil_thermal_coupling_screen_10m.json
a1dcb621c141667cf07d9ff16d7535de32a904563e91d492d73e485713e62f77  SH3_Assembly_OptV3_SiSubstrateSD_60cm.geo.setup
```

哈希只绑定上述当时文件。新会话复制紧凑输入后应生成自己的 snapshot manifest。

## 9. 当前结论（不得提前强化）

当前上游 Geant4 结果证明：SH3 的 Si substrate proxy 中存在中子诱发沉积，
其中有 533 个严格弹性反冲；原始严格反冲没有直接落入 511-keV ROI。能量平衡
筛查留下两个严格反冲候选和一个更值得关注的非弹性次级级联候选。是否形成
511-keV 等效 TES 脉冲尚未解决，唯一缺口正是 Geant4CMP 声子收集、真实界面
参数、TES 脉冲形成/重建与响应卷积。本任务的最终结论必须来自这些模拟，不能
从当前 eta 代数筛查直接推断。

## 10. 本工作区完成状态（2026-09-03）

上述第 9 节是交接时的未决状态；本节记录独立工作区中的后续完成状态。不得把
这里的条件性包络误写成已标定的器件预测。

- G4CMP `g4cmp-V10-05-00` 已隔离安装，并在本机 Geant4 11.4.0 下通过
  两次逐字节一致的官方 100-event smoke 和官方 10,000-event stress；
- 86 个未 veto Si 事件、51 个 strict 子集、A/B/C 以及 30 点能量/位置阶梯
  已全部完成；所有接受 chunk 的加权能量闭合误差小于 `1e-9`；
- 当前几何没有真实 Si–TES/热浴接触和 TES 电热参数，最终结果是条件性
  athermal interface-response envelope，不是绝对效率标定；
- 建议校正为三候选中心包络 `[0,1.569e-3] s^-1`，而非单一中心值；完整
  条件、时序、通道和 Poisson 上限见最终报告。

权威输出：

```text
/home/ubuntu/neutron_fen/INSTALL_MANIFEST.json
/home/ubuntu/neutron_fen/FINAL_EVALUATION.md
/home/ubuntu/neutron_fen/FINAL_EVALUATION.json
/home/ubuntu/neutron_fen/outputs/PHYSICS_MODEL_AUDIT.md
```

### 10.1 从干净 shell 重放已安装版本的 smoke

```bash
cd /home/ubuntu/neutron_fen
env -i PATH=/usr/bin:/bin bash --noprofile --norc
source /home/ubuntu/neutron_fen/env/g4cmp.sh
mkdir -p /home/ubuntu/neutron_fen/runs/official_smoke_recheck
export G4CMP_HIT_FILE=/home/ubuntu/neutron_fen/runs/official_smoke_recheck/hits.csv
/home/ubuntu/neutron_fen/build/g4cmp_official_phonon_smoke/g4cmpPhonon \
  /home/ubuntu/neutron_fen/config/g4cmp_official_phonon_smoke.mac \
  > /home/ubuntu/neutron_fen/runs/official_smoke_recheck/stdout_stderr.log 2>&1
sha256sum /home/ubuntu/neutron_fen/runs/official_smoke_recheck/hits.csv
# 期望 c9867a8d3124a921fb9121bcfa73fd3dbb3119765752dcf4317e91c3725014ea
```

### 10.2 重建输入、程序和 86-event 评估

```bash
cd /home/ubuntu/neutron_fen
python3 code/extract_unvetoed_events.py
python3 code/audit_sh3_unit_geometry.py
python3 code/prepare_g4cmp_inputs.py
python3 code/chunk_g4cmp_input.py outputs/g4cmp_inputs/03_strict51.csv outputs/g4cmp_chunks/strict51 --max-hits 48 --max-groups 8
python3 code/chunk_g4cmp_input.py outputs/g4cmp_inputs/04_all86.csv outputs/g4cmp_chunks/all86 --max-hits 48 --max-groups 8

source /home/ubuntu/neutron_fen/env/g4cmp.sh
cmake -S code/g4cmp_si_tes -B build/g4cmp_si_tes -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/g4cmp_si_tes --parallel 4
python3 code/run_scenario_matrix.py outputs/g4cmp_chunks/strict51 runs/staircase/03_strict51 --scenario nominal_envelope_point
python3 code/run_scenario_matrix.py outputs/g4cmp_chunks/all86 runs/staircase/04_all86
python3 code/extract_candidate_direct_tes.py
python3 code/build_final_evaluation.py
```

G4CMP 从归档到安装的精确 URL、tag/commit、SHA256、CMake 选项和日志路径见
`INSTALL_MANIFEST.json`；不要用这条重放链覆盖 MEGAlib 或既有 Geant4。

## 11. 新增 Ta+TES 集总电热/FEniCS 评估（2026-09-03）

在用户补充 `C_TES=0.04 pJ/K`、`Tc=100 mK`、`alpha~100`、`beta=0`、
`L=1000 nH`、`Rshunt=0.31 mOhm` 并允许显式假设 TES--bath 热导后，已完成
逐像素集总 Ta+TES 非线性电热模型。论文中的 Ta 尺寸和比热给出单像素
`C_Ta=67.3363 pJ/K`；主模型取 `Tb=50 mK`、`Rn=10 mOhm`、
`R0=0.3Rn`、`n=3`、`G(Tc)=1 nW/K`。该点的两个线性极点均为负实数，
形成过阻尼稳定脉冲；同时完成 `G=0.5,1,2,5 nW/K`、另一电阻转变律和
二倍时间步加密检查。

FEniCS 2019.2 使用 `DG0` 单元索引彼此独立的集总 TES 像素；该网格不是
空间热扩散网格，也没有伪造 TES--Si 回流或像素间热导。候选 C 使用五次
G4CMP 的实际逐像素/逐到达时间声子流与直接 Ta/TES 沉积；A/B 只做
“把收集能量强制缩放到 511 keV”的反事实脉冲形状测试。

主结果：候选 C 的固定均值为 `510.964285 keV`，仅偏离 511 keV
`35.7 eV = 0.200 sigma`，所以只看标量能量时可混入；但它有 L1 两个直接
像素和 L0 分布式 substrate 响应，15 个通道能量大于等于 0.42 keV（这里只是
报告阈值，不是硬件触发阈值）。其
阵列求和脉冲相对最佳缩放的单像素 511-keV 模板仍有 `8.84%` L2 形状残差。
因此对丢弃 channel/layer 身份的能量求和，它是条件性不可分背景；对保留
逐像素逐层信息的读出，它不等同于单像素 511-keV 事件。缺少 SQUID/readout
噪声 PSD 和真实 511-keV 多点 Compton 信号库，当前不能把形状残差换算成
统计 sigma 或无信号损失的拒绝率。

权威新增文件：

```text
/home/ubuntu/neutron_fen/config/tes_lumped_fenics_model.json
/home/ubuntu/neutron_fen/code/simulate_tes_fenics.py
/home/ubuntu/neutron_fen/outputs/tes_fenics/TES_FENICS_EVALUATION.md
/home/ubuntu/neutron_fen/outputs/tes_fenics/TES_FENICS_EVALUATION.json
/home/ubuntu/neutron_fen/outputs/tes_fenics/pulse_traces.csv
/home/ubuntu/neutron_fen/outputs/tes_fenics/channel_summary.csv
/home/ubuntu/neutron_fen/outputs/figures/sh3_tes_fenics_pulse_comparison.png
/home/ubuntu/neutron_fen/outputs/figures/sh3_tes_fenics_pulse_comparison.pdf
```

复现（系统 FEniCS 只读使用，JIT 缓存仍写入本工作区）：

```bash
cd /home/ubuntu/neutron_fen
mkdir -p build/fenics_cache/dijitso
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 code/simulate_tes_fenics.py
```
