# PARMA atmospheric-511 modular recomposition

## 结论先行

这个目录实现的是用户指定的最小更正：**只替换 atmospheric annihilation
510.99895-keV mono-line 模块**，随后做离线重合成。它不会、也没有：

- 运行 Cosima 或任何 transport；
- 重跑 prompt continuum、其他粒子、delayed/activation、signal 或 M 抽样；
- 改变几何、探测器响应、50-keV veto 或 topology/FoV selection；
- 修改 retained 产品、M04 中英文稿、M04 PDF 或图 2。

现有低统计 line-only SIM 只能形成 `DIAGNOSTIC_ONLY` 结果。最终 line campaign
aggregate 产生后，用它替换 `--line-input` 即可；其他模块不需要重新计算。

## 固定的模块分解

W2 (`510.58 <= E < 511.42 keV`) 逐时间箱使用

```text
R_new = R_old
      - R_legacy_atm511_sidecar
      - Delta_R_prompt_gamma_line
      + R_corrected_PARMA511_mono
```

离线 prompt-gamma 审计已经给出：

- `Delta_R_prompt_gamma_line(Broad480-550) = 0 cps`；
- `Delta_R_prompt_gamma_line(W2) = 0 cps`。

因此这两个选择窗的数值操作确实退化成“删除旧 sidecar、加入更正后的
PARMA 单能线”。prompt/delayed selected rate 与 45° slant signal 逐箱直接复制
最新 retained 81-bin mission timeline；它们没有被重新模拟或重新拟合。

但 `Delta_R=0` 只描述 **TES 选后率**，不代表偶然符合 occupancy 也是零。
同一去重审计在 `affected_events.step05_catalog` 中记录了 317,048 条
active-only、TES=0 的旧误置线事例，源归一率和为
`737.844505175763 cps`（作为事例占用率时数值上即 Hz）。这些事例不进入
Broad/W2 TES selected rate，却会进入 1-us coincidence occupancy；因此必须从
retained prompt occupancy 中离线扣除。

## 权威链与公式

配置文件对以下只读输入做 SHA-256 fail-closed 校验：

1. 最新 all-eight O8 detector-response summary；
2. retained mission-fold 构建代码；
3. 最新 45° signal-refold 后的 W2 81-bin mission timeline/summary；
4. package-43 的 81-bin trajectory；
5. frozen day-15 PARMA tuple、source-level line closure；
6. prompt-gamma line-de-dup audit；
7. frozen Step05 selection implementation；
8. M04 EN/ZH `.tex/.pdf` 与双语图 2 PDF。

逐箱重算：

```text
lambda_removed_prompt_gamma_line(t)
           = 737.844505175763 Hz * prompt_scale_gamma(t)

lambda_prompt_corrected(t)
           = lambda_prompt(retained,t)
           - lambda_removed_prompt_gamma_line(t)

lambda_new = lambda_prompt_corrected(t)
           + lambda_delayed(retained)
           + lambda_PARMA511(new)

live_new = exp(-lambda_new * 1 us)

S_i = sum(signal_retained * live_new * dt)
B_i = sum(background_new * live_new * dt)
Z_i = S_i / sqrt(B_i)
```

`prompt_scale_gamma` 不是经验选择：retained mission-fold 代码逐族计算
`prompt_family_day15_rate_hz * prompt_scale_<family>` 再求和，且脚本对全部
81 箱用 O8 response 中的八族 day-15 occupancy 反算
`prompt_event_rate_hz`，逐箱 fail-closed 验证。day 15 的
`prompt_scale_gamma=1`。

旧 sidecar 的 `atm511_event_rate_hz` 从来不属于 `prompt_event_rate_hz`。
重合成会单独省略旧 sidecar occupancy 一次、加入新 line occupancy 一次；
绝不再从 prompt 中扣一遍 sidecar。W2/Broad selected-rate 公式仍保持上述
`Delta_R_prompt_gamma_line=0`。

conditional endpoint 沿用旧链的定义：signal lower endpoint 与
componentwise background upper endpoints 相配；它不是联合 95% coverage。

PARMA 线通量只由本地、哈希锁定的 `parma511_driver` 调用官方
`get511fluxCpp()` 离线求值。固定 `W=114.6 MV`、`Rc=11.6 GV`，对 retained
trajectory 的 17 个不同柱深分别求通量。trajectory 自带的 Rc 仍只存在于
已经折叠好的 prompt/delayed 模块中，不能静默替代 line authority 的 Rc。

## 输入模式

脚本接受三种 JSON：

1. `existing_o8_line_module_reweight_summary.json`：现有 8 个 primary W2
   survivor 的低统计诊断；
2. `o8-parma511-line-step05-response-v1`：直接 response summary，仅作中间诊断；
3. `o8-parma511-line-campaign-aggregate-v1`：最终 line campaign aggregate receipt。

只有完整 aggregate，且它指向的 response summary 中
`primary_detector_rate_gate.passes_detector_rate_gate=true` 时，line input 才取得
campaign rate-gate 等级。真实 receipt 自身的路径是
`response.primary_gate.passes_detector_rate_gate`；脚本若看到该字段，还会要求它
与 response-summary gate 一致。脚本同时要求 response 的 Step05 hash 与 frozen
selection 完全一致，并要求 provenance 显式保留 passive Kapton veto blocker。

对完整 aggregate：

- W2 central rate = primary 420-eV response 的 PARMA80 `count/TE`；
- W2 upper endpoint = transported count 的 two-sided 95% Garwood upper / `TE`；
- line occupancy = merged `tes_or_active_events/TE`；
- broad line rate从同目录 `primary_event_response.csv` 按 frozen
  broad/active/topology predicate 直接计数。

对现有低统计诊断：

- W2 central = 80-bin angular importance reweight；
- endpoint 仅为 `rate + 1.95996 sigma_MC` 的诊断近似；
- compact cache 没有 active-only event directions，所以 line occupancy 只能用
  `old occupancy * Phi_PARMA/Phi_legacy`；
- broad corrected-line rate不可从该紧凑 W2 表可靠恢复，输出为 `null`。

## 运行

从仓库根目录：

```bash
python3 engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/recomposition/code/build_modular_recomposition.py \
  --self-test \
  --self-test-output engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/recomposition/outputs/self_test_report.json
```

默认低统计诊断重合成：

```bash
python3 engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/recomposition/code/build_modular_recomposition.py
```

最终 aggregate 到位后：

```bash
python3 engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/recomposition/code/build_modular_recomposition.py \
  --line-input /path/to/aggregate_receipt.json \
  --output-dir engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/recomposition/outputs/final_line_campaign
```

脚本默认拒绝覆盖同名产物；只有显式 `--force` 才会替换目标输出目录中由本
脚本管理的六个文件，不删除任何其他文件。

## 当前 DIAGNOSTIC 结果

用现有 low-stat line input：

- day-15 retained prompt：`0.00339303151412 cps`；
- day-15 retained delayed：`0.00201657067387 cps`；
- day-15 retained 45° signal：`0.000986227890904 cps`；
- 删除 legacy sidecar：`0.00155526135195 cps`；
- 加入 diagnostic corrected PARMA line：`0.00417489551561 cps`；
- recomposed day-15 background：`0.00958449770360 cps`；
- day-15 从 prompt occupancy 中扣除旧误置线项：`737.844505175763 Hz`；
- day-15 prompt occupancy：`23733.99409699 -> 22996.14959182 Hz`；
- day-15 total occupancy：`24407.05889991 -> 23669.21439474 Hz`；
- day-15 live factor：`0.975888384844 -> 0.976608704435`；
- W2/Broad selected-rate 去重差分仍均为 `0 cps`；
- diagnostic 20-day central：`S=1650.79217224`、`B=16014.96663336`、
  `Z=13.04455841`；相对未扣这项 occupancy 的旧重合成分别变化
  `+1.21703758`、`+12.11882424`、`+0.00468234`。

这些数值不能写入论文：line input 只有 8 个 primary W2 events、RSE 约
36.1%，而 occupancy 还是标量近似。它们的用途是验证模块接口、删除/加入
方向、live-factor 和 mission-fold 算术。

## 必须保留的科学 blocker

1. **factor-1000 legacy prompt-gamma axis**：retained O8 prompt-photon DP
   横轴比正确 Cosima-keV 横轴低 1000 倍。这影响整个 prompt-gamma 模块，
   `Delta_R_line(W2)=0` 与离线删除 active-only line occupancy 都不能修复
   continuum。按用户范围，本包冻结其 selected-rate 实现，不触发 continuum
   重跑。
2. **passive Kapton 被 frozen veto predicate 纳入**：Step05 使用
   `"ACTIVE_SHIELD" in volume.upper()`，因此三个材料为 Kapton 的
   `ActiveShield_S3C_BGO_Kapton_*` scorer 也进入 50-keV veto。历史 selection
   在本重合成中原样复用；这里不修 predicate、不重跑。
3. **day-15 angular response 冻结**：20-day 轨迹柱深变化时 PARMA line 的角分布
   也可能变化，但当前只允许复用 day-15 response。因此 mission output 是
   fixed-response 条件折叠，不是新的 time-bin transport authority。

即使最终 line campaign 的统计 gate 通过，前两个 blocker 仍使总背景不能成为
publication authority；这不构成要求全量重跑的指令，只是如实限定现有保留模块。

## 产物

- `outputs/self_test_report.json`：authority/hash、旧公式恒等式、
  `prompt_scale_gamma` 语义、81-bin corrected occupancy 非负/恒等式、PARMA flux、
  完整 aggregate schema 的临时 fixture 自测；
- `outputs/diagnostic_existing_line/parma511_line_flux_by_time.csv`；
- `outputs/diagnostic_existing_line/w2_modular_recomposition_by_time.csv`；
- `outputs/diagnostic_existing_line/day15_modular_recomposition.json`；
- `outputs/diagnostic_existing_line/mission_20d_modular_recomposition.json`；
- `outputs/diagnostic_existing_line/RECOMPOSITION_RESULT.md`；
- `outputs/diagnostic_existing_line/recomposition_manifest.json`。

所有输出都重复记录 `cosima_launched=false`、`transport_launched=false`、
`continuum_rerun=false`、`other_particle_rerun=false`、`m_sampling_rerun=false`。
