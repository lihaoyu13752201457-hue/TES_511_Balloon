# SH3 中子诱发 Si 衬底声子/TES 耦合评估

日期：2026-09-03  
状态：**完成，但绝对 TES 校正仍是条件性的**

机器可读结果：[FINAL_EVALUATION.json](/home/ubuntu/neutron_fen/FINAL_EVALUATION.json)

## 结论

10^7 中子输运中的 86 个 `Si>0 && BGO<50 keV` 事件已经全部进入 G4CMP 阶梯。所有接受运行的加权能量闭合误差小于 `1e-9`，逐像素能量、到达时间、多重性和 420 eV FWHM 响应卷积均已保存。

结果不能支持一个唯一的 SH3 Si→TES 校正率。原因不是数值求解不足，而是当前质量模型没有真实 Si–膜–TES/热浴接触、晶向和 TES 电热学参数；代理几何中的 Si 与 Ta/Cu 还留有真空间隙。可复现结论是：

1. A、B 在参数化响应核中**可以分别达到**所需的 97.06% 和 89.92% 收集，但只在大面积、近理想收集且弱浴损失的高端包络附近；现有 SH3 资料不能证明器件位于该区间。
2. C 的 13.58% 收集很容易由中等界面端点产生。`area_scale=0.12, p_sensor=0.3, p_bath=0.1` 的五个独立 8192-packet 重复给出 `eta=0.13572 ± 0.00064 (MC SEM)`，对应重建均值 `510.964 ± 0.248 keV (MC SEM)`。但单次重复的 ROI 概率从 0.072 到 0.785，证明 840 eV 窄窗判断尚受显著 packet 误差影响。
3. 没有任何已扫描的**同一个**界面参数点让 A/B/C 同时进入 ROI。趋近 A/B 的高收集端点会把 C 推到 ROI 上方；匹配 C 的端点会把 A/B 留在远低于 ROI 的位置。
4. C 有很强的可识别拓扑：原有 458.392 keV 直接 TES 能量集中在 L1 的两个像素，而 Si 沉积在 L0；Si 声子分量的中位到达约 0.688 us、90% 约 2.42 us，形成跨层、多通道、延迟尾，而不是单像素瞬时线事件。A/B 也呈多像素声子尾，但 C 的跨层标签最强。
5. 在接口未标定前，建议不给论文或基线预算写入单一中心校正。对这 10^7 输运样本，携带 `[0, 3/1911.8824] = [0, 1.569×10^-3] s^-1` 的三候选中心包络；若把三件全部视为计数，其输运样本 Poisson 单侧 95% 上限为 `4.056×10^-3 s^-1`。这是保守包络，不是预测值。

## 上游复核

- 等效时间：1911.8824 s；中子数：10,000,000。
- 任意正 Si 沉积：3161；严格 `Si* + neutron + hadElastic`：533，速率 0.278783 s^-1。
- 严格反冲且 `BGO<50 keV`：51，速率 0.0266753 s^-1。
- 所有未 veto 正 Si 事件：86，共 327 条 Si HIT；其中 strict 51 个、54 条严格反冲 HIT。
- strict recoil 能量：0.522–1407.343 keV，中位 29.147 keV；原始 strict ROI 计数为 0。
- 只有 A/B/C 在 `E_direct + eta E_Si`、`0<=eta<=1` 下代数可进入 ROI。事件与坐标提取见 [unvetoed_events.json](/home/ubuntu/neutron_fen/outputs/unvetoed_events.json) 和 [g4cmp_input_manifest.json](/home/ubuntu/neutron_fen/outputs/g4cmp_input_manifest.json)。

## 安装与兼容性门槛

采用官方 `G4CMP/G4CMP` 的 `g4cmp-V10-05-00`，归档 SHA256 为 `1de5c665...e0bc4`，隔离安装到工作区。官方 ChangeHistory 已包含 Geant4 v11 编译/链接兼容项，并在该标签包含 Geant4 11.4.2 的 `PhysicsModelCatalog` 调整；但仓库 README 仍保留旧的 Geant4 10.4–10.7 说明，所以没有仅凭文字宣称兼容，而是以本机验证作为门槛。[官方仓库](https://github.com/G4CMP/G4CMP)；[Geant4 releases](https://github.com/Geant4/geant4/releases)。

本机 Geant4 11.4.0 下：

- Release 构建 193/193 成功，安装与官方 phonon example 单独链接成功；
- 官方 100-event smoke 两次输出逐字节相同：430 terminal hits、0.2699999978365 eV / 0.270 eV 能量闭合；
- 官方 10,000-event stress：45,106 terminal hits，退出码 0；
- 登录环境继承的 MEGAlib/Geant4 10.2.3 数据变量已由 [env/g4cmp.sh](/home/ubuntu/neutron_fen/env/g4cmp.sh) 全量覆盖，未修改或覆盖 MEGAlib 与既有 Geant4；
- 完整安装记录见 [INSTALL_MANIFEST.json](/home/ubuntu/neutron_fen/INSTALL_MANIFEST.json)。

定制高多重 primary 程序在少数负载下曾于所有 `COMPLETE` 输出写完之后，进入 G4CMP process-global 静态析构时崩溃；官方 stress 不复现。程序现显式关闭 run manager、刷新输出并用 `_Exit(0)` 绕过残余静态析构。每个 chunk 仍必须先通过 `COMPLETE` 与能量闭合检查才会合并。这个限制已公开记录，未作为物理成功掩盖。

## 几何和模型

几何审计 4679 项检查全部通过：每层 Si 为 `36×36×0.3 mm`；每层 376 个 `1.5×1.5 mm` Ta 投影像素，投影面积 65.2778%。Ta–Si 间隙为 0.15 mm，Cu support 与 Si 也不接触。因此 simulation 将像素 footprint 折叠到 Si 的 Ta 侧表面，并显式扫描：

- `sensor_area_scale = 0.01, 0.1, 1.0`，以及 C 的 0.12；
- 每次界面相遇 `p_sensor = 0.05, 0.3, 1.0`；
- 非传感表面/浴损失 `p_bath = 0.01, 0.1, 1.0`；
- diffuse/specular 两端；
- primary packet 能量 2.7、30、62 meV；参考晶向为 `[100]` 法向。

这只是 G4CMP athermal 界面响应核。G4CMP 可模拟非平衡声子与电荷输运，但器件参数通常必须由用户提供或用数据拟合；界面透射本身也需要测量约束。[G4CMP 物理论文](https://arxiv.org/abs/2302.05998)，[Si–Al 界面测量](https://doi.org/10.1103/PhysRevApplied.11.064025)，[本工作物理边界审计](/home/ubuntu/neutron_fen/outputs/PHYSICS_MODEL_AUDIT.md)。

## 模拟阶梯

### 1. 点源/能量/位置

对 30、140、500、568、1407 keV，在 center/edge 与 front/middle/back 深度共运行 30 点。track weight 使响应对沉积总能量保持线性；差异来自位置、声子频率和有限 MC。

| packet 能量 | center front/mid/back 平均 eta | edge front/mid/back 平均 eta |
|---|---:|---:|
| 2.7 meV | 0.728 / 0.730 / 0.733 | 0.276 / 0.278 / 0.277 |
| 30 meV | 0.811 / 0.730 / 0.617 | 0.122 / 0.127 / 0.113 |
| 62 meV | 0.801 / 0.723 / 0.619 | 0.113 / 0.126 / 0.123 |

30 与 62 meV 相符，说明 Debye 尺度支路已大致收敛；2.7 meV 不发生相同程度的下转换，保留为低频弹道系统端点。明显的 edge/depth 依赖说明用一个全局常数 eta 会遗漏事件拓扑。

### 2. Exact A/B/C

| 候选 | 目标 eta | 名义 62 meV eta | optimistic eta | 解释 |
|---|---:|---:|---:|---|
| A | 0.970647 | 0.767602 | 0.997547 | 高端参数族中存在交点，但未标定 |
| B | 0.899193 | 0.718235 | 0.979996 | 高端参数族中存在交点，但未标定 |
| C | 0.135811 | 0.578945 | 0.956029 | 中等面积端点可匹配 |

C 的五重复匹配点：

- eta：`0.135719 ± 0.000640`（独立 seed 的均值 ± SEM）；
- reconstructed mean：`510.964 ± 0.248 keV`（MC SEM）；
- Gaussian ROI probability 的重复均值 `0.455 ± 0.161 SEM`，范围 0.072–0.785；
- 对应的**条件性**速率 `2.381×10^-4 ± 8.422×10^-5 s^-1`（只含这一个输运样本事件和 packet MC，不含接口系统误差）。

该条件速率不能当作 SH3 校正中心值，因为 `area_scale=0.12` 是为了展示可达性而选的未标定参数。

### 3. Strict 51 与全部 86

strict 51 在名义 62 meV 参数点全部完成，ROI 期望为 0。全部 86 在七个预注册端点和一个 C 附近点完成；全样本 Si 加权输入 6283.423 keV，所有端点能量闭合。全局 sensor eta 范围为 `4.64×10^-5` 到 `0.787`；名义 62、30、2.7 meV 分别为 0.3967、0.3931、0.4420。预注册离散点均未稳定产生 ROI 事件；只有连续参数空间中的 C 附近窄带显示明显条件性概率。

逐事件和逐通道产品位于 [runs/staircase/04_all86](/home/ubuntu/neutron_fen/runs/staircase/04_all86)，每个场景均含 `analysis.json`、`events.csv`、`channels.csv`、原始 hit 与 chunk manifest。

## 通道、时序与 veto/PSD

原 SIM 仅针对 A/B/C 做了两份 PASS receipt 绑定文件的定向流式读取，没有复制 SIM：

- A：直接能量 17.13377 keV，`L1:P49`；
- B：无直接 TES 能量；
- C：`L1:P231 = 433.54379 keV`、`L1:P147 = 24.84798 keV`，合计 458.391770806 keV；其 Si 能量却在 L0。

见 [candidate_direct_tes_channels.csv](/home/ubuntu/neutron_fen/outputs/candidate_direct_tes_channels.csv)。

名义 62 meV 下，A/B/C 的声子到达 q50 分别为 0.345/0.472/0.632 us，q90 为 1.412/1.425/1.651 us，hit-channel 数为 48/30/147，但能量 IPR 有效多重性仅 2.19/2.29/5.53。匹配 C 的高统计重复给出 q10/q50/q90/q99 = 0.173/0.688/2.423/4.995 us，约 62.8% 在 1 us 内、37.2% 在 1–10 us、约 0.022% 晚于 10 us，有效多重性约 3.02。

因此最有力的额外选择不是把所有能量压成一个 eta，而是：

1. Si-substrate tag；
2. 多像素能量 IPR/重心；
3. 数百 ns 到数 us 的声子尾；
4. C 特有的 L0 substrate + L1 direct-TES 跨层 coincidence。

但真实 PSD 接受率仍需 TES ETF、采样率、触发与滤波器模型，当前不能数值化。

## 为什么没有用 FEniCS

慢热 PDE 所需的温度依赖热容、面内/厚度热导、Kapitza/薄膜边界导热、支撑热沉、TES 偏置点与 ETF 参数全部缺失。FEniCS 无法从质量代理的真空间隙推导这些边界条件，也不能替代 G4CMP 的非热声子输运。因此本轮不使用 FEniCS，避免伪精度。若补齐器件 CAD 和低温材料/接口数据，可把 G4CMP 输出作为 FEniCS 或 lumped electrothermal model 的时空源项。

## 可复现命令

从本工作区执行；不需要也不应复制 17 GB SIM。安装细节和固定哈希以 `INSTALL_MANIFEST.json` 为准。

```bash
cd /home/ubuntu/neutron_fen

# 重建紧凑输入与几何审计
python3 code/extract_unvetoed_events.py
python3 code/audit_sh3_unit_geometry.py
python3 code/prepare_g4cmp_inputs.py
python3 code/chunk_g4cmp_input.py outputs/g4cmp_inputs/03_strict51.csv outputs/g4cmp_chunks/strict51 --max-hits 48 --max-groups 8
python3 code/chunk_g4cmp_input.py outputs/g4cmp_inputs/04_all86.csv outputs/g4cmp_chunks/all86 --max-hits 48 --max-groups 8

# 隔离环境与定制程序
env -i PATH=/usr/bin:/bin bash --noprofile --norc
source /home/ubuntu/neutron_fen/env/g4cmp.sh
cmake -S /home/ubuntu/neutron_fen/code/g4cmp_si_tes -B /home/ubuntu/neutron_fen/build/g4cmp_si_tes -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build /home/ubuntu/neutron_fen/build/g4cmp_si_tes --parallel 4

# strict 与全部 86 的阶梯
python3 code/run_scenario_matrix.py outputs/g4cmp_chunks/strict51 runs/staircase/03_strict51 --scenario nominal_envelope_point
python3 code/run_scenario_matrix.py outputs/g4cmp_chunks/all86 runs/staircase/04_all86

# 仅定向流式核对 A/B/C 的 direct TES 通道并重建最终 JSON
python3 code/extract_candidate_direct_tes.py
python3 code/build_final_evaluation.py
```

官方 smoke 的重放方式：

```bash
export G4CMP_HIT_FILE=/home/ubuntu/neutron_fen/runs/official_smoke_recheck/hits.csv
mkdir -p /home/ubuntu/neutron_fen/runs/official_smoke_recheck
/home/ubuntu/neutron_fen/build/g4cmp_official_phonon_smoke/g4cmpPhonon \
  /home/ubuntu/neutron_fen/config/g4cmp_official_phonon_smoke.mac \
  > /home/ubuntu/neutron_fen/runs/official_smoke_recheck/stdout_stderr.log 2>&1
```

## 下一步所需数据

若要把包络收缩为可用于论文的中心校正，最少需要：真实膜栈/CAD 与晶向；Si–膜、裸 Si–浴的低温界面透射或 coupon pulse 数据；AlMn/Ta collector/QP 参数；TES `C,G,Tc,Rn,bias,ETF`；采样、触发、最优滤波和 PSD 定义。取得这些数据后，应先用校准脉冲拟合界面参数，再冻结模型重跑 86 事件，不能从本包络反向挑选一个“正好落窗”的 eta。
