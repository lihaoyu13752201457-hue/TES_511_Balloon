# 既有 O8 atmospheric-511 单能模块离线角度重权审计

审计状态：`DIAGNOSTIC_REWEIGHT_REPRODUCED_BUT_FAILS_PASS_PARMA_511_STATISTICS`

审计日期：2026-08-10。范围严格限于只读检查与离线数值复算；未调用 Cosima、未生成新 SIM、未改动任何其他粒子模块。

## 结论先行

既有 O8 mono-511 输运在技术上可以用新的 PARMA line angular weights 做离线 importance reweight，原因是旧 20 个等 μ 角箱覆盖完整 4π、每箱旧 flux 与实际生成数都保留在源卡/日志中，SIM 的每个事件也保留了 `IA INIT` 入射方向。旧 SIM 没有显式 source name/source-bin ID，但对现有 9 个 unsmeared W511 事件，可以无歧义地由方向恢复角箱。

这只能形成诊断性复用，不能成为 `PASS_PARMA_511` 的论文级 detector-response authority：

- unsmeared W511 只有 9 个事件；420 eV FWHM 主 response seed 后只有 8 个；
- PARMA 80-bin importance reweight 的相对 MC 误差分别为 34.00% 和 36.14%，ESS 分别为 8.65 和 7.65；
- 40/80 中心值差虽只有 0.43%/0.91%，但统计误差远达不到交接要求的合并计数误差 `<1.5%`；
- 14/20 个旧角箱没有 W511 survivor，而这些箱包含新 PARMA line flux 的 66.07%；
- 交接门槛要求累计至少 400 个最终 W511，或纯计数相对误差不大于 5%，现有样本明确不满足。

因此：现有模块可用于零模拟 preview、方向约定检查和粗略影响边界；若要关闭论文级 `PASS_PARMA_511`，只应输运修正后的 atmospheric 510.99895-keV mono-line 模块。其他粒子、continuum、prompt、delayed、science 模块全部复用并重合成，不应全量重跑。

## 1. 输入权威与哈希

| 角色 | 路径 | SHA-256 |
| --- | --- | --- |
| 旧 O8 line-only source | `runs/geometry_optimization_20260704/s3d_o8_atm511_sidecar_3m_20260712/Atm511SidecarS3dO8_3M.source` | `323621f39737171ddc77a377f58dabc7a8c7148bfe195c101961b95d68008b2e` |
| 旧 O8 line-only SIM | `runs/geometry_optimization_20260704/s3d_o8_atm511_sidecar_3m_20260712/Atm511SidecarS3dO8_3M.inc1.id1.sim.gz` | `f07b1c8073764257ba95e25eb340726d27e2740c4f17bffe108a13ecc15b234c` |
| 旧 Cosima log | `runs/geometry_optimization_20260704/s3d_o8_atm511_sidecar_3m_20260712/cosima_Atm511SidecarS3dO8_3M.log` | `185d2f7d98f6928f818b7599db18ce93fb5b2f3e3c20658e0c7bb3a8bff4a450` |
| 旧 replay summary | `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_atm511_replay_summary.json` | `b2c4e6ab26ca0f1210fc828086b574435a52100712cbc2f9a9209d324b31ec80` |
| 带 provenance 的 ATM compact cache | `engineering/ea_s3d_o8_all8_detector_response_closure_20260713/data/s3d_o8_all8_atm511_compact_catalog.pkl` | `c7c803309598944838d49c2874b75ab5b645de8688d08109bb2613ed89f893ed` |
| 420 eV response authority | `engineering/ea_detector_response_closure_20260713/data/o8_energy_response_closure_summary.json` | `810b1e3182e5247f5caacd346f24415ddce7833921840b601dde0a38da1779bd` |
| 新 PARMA 20-bin weights | `line/parma511_day15_20bins.csv` | `3e4c73e50f6a5e97c2cd613b9b85a666f27723d7faaa26e105803774936a7ecd` |
| 新 PARMA 40-bin weights | `line/parma511_day15_40bins.csv` | `093175c5b73a72bfba510f23e7bfecb4aa8c93bed19f80a7a5271bccab18daa5` |
| 新 PARMA 80-bin weights | `line/parma511_day15_80bins.csv` | `2f4ae904bf89179fe1709e3a8123ff864f4450e8bcf443389898ea43cd6a5a32` |

SIM 大小为 809,084,946 bytes；compact cache 大小为 10,896 bytes。cache 自带 metadata，并绑定上述 SIM 的大小/hash、旧 parser `4917e77f...`、旧 replay summary `b2c4e6ab...` 及生成它的 response script `c064afca...`。

旧 source 与 SIM header 都指向最终 O8 setup：

`engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

setup 的权威 SHA-256 为 `86a9e56e54dc86834dfe2a9b03a5f71373fb40f2ef24e3889fa66f216058fbec`。源卡 seed 为 `26070917`；SIM header 同为 `26070917`。

## 2. 旧 20 箱 source/flux/实生成数

源卡第 18–37 行绑定 20 个 source；第 39–137 行逐箱定义 `ParticleType 1`、`FarFieldAreaSource`、`Spectrum Mono 511` 和 `.Flux`。20 箱是等 μ 分箱，φ 均为 0–360°，彼此不重叠且覆盖 4π。日志第 4,303,117–4,303,136 行保存逐 source 实际生成数；共同 average start area 为 11,309.7 cm²，总计 3,000,000，observation time 为 5,143.83 s。

| bin | 旧 source / θ 范围 (deg) | 旧 flux | 实生成 N | 新 PARMA-20 flux | 新/旧 | W2 9→8 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 0 | `Atm511_bin00_down` 0–25.841933 | 4.3193374e-4 | 25,283 | 6.3923815e-4 | 1.480 | 0→0 |
| 1 | `Atm511_bin01_down` 25.841933–36.869898 | 4.7439064e-4 | 27,734 | 9.7626375e-4 | 2.058 | 1→1 |
| 2 | `Atm511_bin02_down` 36.869898–45.572996 | 5.2596831e-4 | 30,384 | 1.3422537e-3 | 2.552 | 0→0 |
| 3 | `Atm511_bin03_down` 45.572996–53.130102 | 5.8987870e-4 | 34,519 | 1.7441504e-3 | 2.957 | 2→1 |
| 4 | `Atm511_bin04_down` 53.130102–60 | 6.7096363e-4 | 39,276 | 2.1919910e-3 | 3.267 | 0→0 |
| 5 | `Atm511_bin05_down` 60–66.421822 | 7.7675443e-4 | 45,104 | 2.7011903e-3 | 3.478 | 0→0 |
| 6 | `Atm511_bin06_down` 66.421822–72.542397 | 9.1915846e-4 | 53,355 | 3.2975266e-3 | 3.588 | 0→0 |
| 7 | `Atm511_bin07_down` 72.542397–78.463041 | 1.1157167e-3 | 64,584 | 4.0301344e-3 | 3.612 | 0→0 |
| 8 | `Atm511_bin08_down` 78.463041–84.260830 | 1.3754536e-3 | 80,401 | 5.0174616e-3 | 3.648 | 0→0 |
| 9 | `Atm511_bin09_down` 84.260830–90 | 1.5728489e-3 | 92,049 | 7.4966083e-3 | 4.766 | 0→0 |
| 10 | `Atm511_bin10_up` 90–95.739170 | 2.5279200e-3 | 146,628 | 1.4390691e-2 | 5.693 | 0→0 |
| 11 | `Atm511_bin11_up` 95.739170–101.536959 | 2.9240001e-3 | 169,753 | 1.5062416e-2 | 5.151 | 0→0 |
| 12 | `Atm511_bin12_up` 101.536959–107.457603 | 3.3200795e-3 | 193,115 | 1.4636634e-2 | 4.409 | 0→0 |
| 13 | `Atm511_bin13_up` 107.457603–113.578178 | 3.7161590e-3 | 215,928 | 1.4256923e-2 | 3.836 | 1→1 |
| 14 | `Atm511_bin14_up` 113.578178–120 | 4.1122392e-3 | 239,084 | 1.3905638e-2 | 3.382 | 1→1 |
| 15 | `Atm511_bin15_up` 120–126.869898 | 4.5083188e-3 | 262,147 | 1.3574462e-2 | 3.011 | 0→0 |
| 16 | `Atm511_bin16_up` 126.869898–134.427004 | 4.9043980e-3 | 285,675 | 1.3258614e-2 | 2.703 | 0→0 |
| 17 | `Atm511_bin17_up` 134.427004–143.130102 | 5.3004777e-3 | 308,731 | 1.2955023e-2 | 2.444 | 1→1 |
| 18 | `Atm511_bin18_up` 143.130102–154.158067 | 5.6965576e-3 | 331,291 | 1.2661564e-2 | 2.223 | 3→3 |
| 19 | `Atm511_bin19_up` 154.158067–180 | 6.0926373e-3 | 354,959 | 1.2376689e-2 | 2.031 | 0→0 |

旧总 flux 为 0.0515558541130 ph cm⁻² s⁻¹；新 PARMA line flux 为 0.1665154716023 ph cm⁻² s⁻¹，总量比为 3.229807254。逐箱比从 1.48 到 5.69，不是一个共同 scalar；直接用总 flux 比缩放旧 rate 会丢失角响应信息。

## 3. SIM 是否保留 source ID / 方向

对整个 gzip SIM 的 source-token 扫描只有一条 header：

`BeamType FarFieldAreaSource 0 25.8419 0 360`

全文件没有 `Atm511_bin*`、`SourceID` 或 `SI` source-lineage record。因此 SIM 不保留显式 source name/source-bin ID；header 的单条 `BeamType` 也只是第一个 source 的全局描述，不能给每事件归箱。

但每个事件都有 `IA INIT`。仓库现有 parser 在 `build_s3c_lightweight_analysis.py:100-110` 把分号字段 16–18 读为 `dir_x/y/z`。`FarFieldAreaSource` 的 θ 是 source-side 天空方向，而 `IA INIT` 向量指向探测器内部，故

`mu_source = cos(theta_source) = -dir_z`

由此：

- 旧 20 箱：`bin20 = floor((1 + dir_z) * 10)`；
- 新 G 箱：`binG = floor((1 + dir_z) * G / 2)`；
- G-bin event importance ratio：`(G/20) * Phi_new,Gbin / Phi_old,20bin`；
- event rate weight：上述 ratio 再除以旧 observation time 5,143.83 s。

全 3M `IA INIT` 方向扫描确实得到 3M 条，但 `dir_z` 只打印 5 位小数。以半个末位单位为边界候选定义，共有 271 个潜在边界事件；方向反推逐箱数与日志的显式 source 计数最多相差 16。故全流 source-bin lineage 不是 bit-exact。

现有 9 个 W2 事件没有这个问题：最靠近旧箱边界者仍相距 0.4844°，9 个全部无歧义。逐事件表见 `response/existing_o8_line_module_reweight_events.csv`。

## 4. Compact catalog 实际字段与缺口

带 provenance 的 compact cache 顶层是 `metadata` 与 `catalog`。`catalog` 字段为：

`label, event_id, stream, tag, rate_hz, active_keV, raw_total_keV, hit_start, hit_count, hit_uid, hit_layer, hit_e_keV, hit_x_cm, hit_y_cm, hit_z_cm, active_only_rate_by_stream, active_only_events_by_stream, generated_events`

实际有 69 个 TES events、84 个 pixel hits；另有 1,041,436 个 active-only events 只以 aggregate 保存。catalog 没有 `dir_x/y/z`、source name 或 source-bin 字段。其 `event_id` 是原 SIM local ID，因此可以离线只读 join `SIM ID -> IA INIT`，但 catalog 单独使用不能做角重权。

旧 atmospheric parser 本身也只构建 `local_id, tes_total_keV, active_total_keV, pix_*` 数组（`build_geo_opt_atm511_sidecar_replay.py:422-518`）；后来的 compact builder 仍未加入方向（`build_s3d_o8_all8_energy_response.py:1244-1263`）。这不是 transport 缺失，而是持久化 schema 的 lineage 缺口。

## 5. 9 个 unsmeared / 8 个 420-eV 主 realization 的角箱

| 状态 | old20 角箱分布 |
| --- | --- |
| unsmeared 9 | bin01:1, bin03:2, bin13:1, bin14:1, bin17:1, bin18:3 |
| primary 420 eV FWHM 8 | bin01:1, bin03:1, bin13:1, bin14:1, bin17:1, bin18:3 |

420-eV authority 使用 atmospheric response seed `1026071308`、σ=0.1783575781 keV。事件 `1733826` 从 raw 511.000000 keV 被卷积到 510.576650 keV，略低于 W2 下限 510.58 keV，因此 9→8。其余 8 个保持在 W2，且 8/8 均有 `active_keV=0`。

旧 replay summary 的 9 个事件及方向见 `s3d_o8_atm511_replay_summary.json:132-300`；unsmeared 9/9 闭合见 response summary 第 185–204 行；420-eV 主 realization 8/8/8 见第 656–717 行。

## 6. 新 PARMA 权重的离线诊断结果

| 样本 | grid | 重权 rate (cps) | MC σ (cps) | 相对 σ | ESS |
| --- | ---: | ---: | ---: | ---: | ---: |
| unsmeared 9 | 20 | 0.00472443 | 0.00161098 | 34.10% | 8.60 |
| unsmeared 9 | 40 | 0.00474635 | 0.00161575 | 34.04% | 8.63 |
| unsmeared 9 | 80 | 0.00476665 | 0.00162089 | 34.00% | 8.65 |
| primary 420 eV 8 | 20 | 0.00414960 | 0.00150494 | 36.27% | 7.60 |
| primary 420 eV 8 | 40 | 0.00413671 | 0.00149633 | 36.17% | 7.64 |
| primary 420 eV 8 | 80 | 0.00417490 | 0.00150900 | 36.14% | 7.65 |

40 相对 80 的中心值差为：

- unsmeared：−0.4259%；
- primary 420 eV：−0.9146%。

但这些小中心差不是“40/80 response gate 已通过”，因为两者复用相同的 9/8 个低统计事件，单个 rate 的计数误差仍是 34–36%。

作为必要对照，若错误地只乘总 flux 比，得到 unsmeared 0.00565109 cps、primary 0.00502319 cps；80-bin 角重权分别低 15.65% 和 16.89%。这直接证明新 line 不能只做 day-15 总通量 scalar rescale。

## 7. 为什么只能诊断、不能 PASS

交接 `SESSION_BOOTSTRAP.md:396` 要求保留每角箱 detector response coefficient；`408-410` 又要求 40/80 W511 响应差不大于 2%、合并计数误差小于 1.5%，并累计至少 400 个最终 W511 或相对计数误差不大于 5%。

现有 9/8 个事件只满足“方向映射可做”和“40/80 中心值粗诊断接近”，不满足统计门槛。更关键的是，有 W2 survivor 的 6 个 old20 箱只含新 PARMA flux 的 33.93%；其余 14 箱含 66.07% 新 flux，却全部是 0-survivor response estimate。零计数不能证明真实 response 为零。

此外，旧 transport 是 511.00000 keV，新 PARMA nominal 是 510.99895 keV，差 0.00105 keV。它仅为 detector σ 的约 0.59%，作为 preview 可记录为近似；论文权威 transport 仍应使用正确能量。

最终判定：

1. `PASS_ZERO_SIM_OFFLINE_DIAGNOSTIC_REWEIGHT`：可以；
2. `PASS_PARMA_511` detector-response authority：不可以；
3. 若需要关闭后者：只重跑 corrected atmospheric mono-line module；
4. 禁止据此扩大到全链或其他粒子重跑；其余模块原样复用并重合成。

## 8. 对 WP3 的现有同-SIM A/B 边界

ATM compact catalog 对所有 69 个 TES events 保存 `active_keV`，因此 veto on/off 可以在同一 SIM 上离线 A/B，不需要任何新 transport。当前 W2 的 9 个 unsmeared 和 8 个 primary-response survivors 全部 `active_keV=0`，故该 line module 的现有 W2 veto A/B 是 9→9、8→8：没有观察到 veto 收益，也没有观察到 veto 代价。

这只是 9/8 事件的低统计模块化证据。WP3 应把它写成“现有同-SIM offline A/B 未见变化”的边界性结论，不应推广为高统计 veto 效率结论，更不应据此要求其他粒子或全链 transport。

## 9. 可复现产物

- 结构化汇总：`data/existing_o8_line_module_reweight_summary.json`
- 9 个 W2 逐事件 lineage/weights：`response/existing_o8_line_module_reweight_events.csv`
- 只读复现脚本：`code/audit_existing_o8_line_reweight.py`

复现脚本默认读取 source/log/SIM-derived catalog 并在 stdout 输出审计 JSON；加 `--deep-sim-audit` 才扫描全部 3M `IA INIT`。两种模式都不会调用模拟器，也不会写文件。

## 10. 本次实际阅读的文件

- `engineering/m04_validation_geometry_handoff_20260810/SESSION_BOOTSTRAP.md`（WP2 相关 333–413 行）
- `runs/geometry_optimization_20260704/s3d_o8_atm511_sidecar_3m_20260712/Atm511SidecarS3dO8_3M.source`
- `runs/geometry_optimization_20260704/s3d_o8_atm511_sidecar_3m_20260712/Atm511SidecarS3dO8_3M.inc1.id1.sim.gz`（header、W2 lineage、全 3M `IA INIT` 扫描）
- `runs/geometry_optimization_20260704/s3d_o8_atm511_sidecar_3m_20260712/cosima_Atm511SidecarS3dO8_3M.log`（源初始化、尾部逐箱统计）
- `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_atm511_replay_manifest.json`
- `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_atm511_replay_summary.json`
- `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/build_o8_screening_analysis.py`
- `engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/code/build_s3c_lightweight_analysis.py`
- `engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708/build_geo_opt_atm511_sidecar_replay.py`
- `old/code/tools/make_complete_day15_report_ADR.py`
- `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/fullchain/step05/step05_s3d_o8_fullchain_l1_response_summary.json`
- `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/fullchain/step05/work/event_catalog.pkl`（字段/流结构审计）
- `engineering/ea_detector_response_closure_20260713/code/build_o8_energy_response_closure.py`
- `engineering/ea_detector_response_closure_20260713/data/o8_atm511_compact_catalog.pkl`
- `engineering/ea_detector_response_closure_20260713/data/o8_energy_response_closure_summary.json`
- `engineering/ea_s3d_o8_all8_detector_response_closure_20260713/code/build_s3d_o8_all8_energy_response.py`
- `engineering/ea_s3d_o8_all8_detector_response_closure_20260713/data/s3d_o8_all8_atm511_compact_catalog.pkl`
- `engineering/ea_s3d_o8_all8_detector_response_closure_20260713/data/s3d_o8_all8_energy_response_summary.json`
- `line/parma511_day15_20bins.csv`
- `line/parma511_day15_40bins.csv`
- `line/parma511_day15_80bins.csv`
- `data/parma_line_closure.json`
- `data/build_manifest.json`
