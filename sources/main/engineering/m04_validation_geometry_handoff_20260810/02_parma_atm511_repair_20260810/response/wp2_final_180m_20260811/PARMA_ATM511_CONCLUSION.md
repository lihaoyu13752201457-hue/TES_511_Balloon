# PARMA atmospheric-511 WP2 conclusion

状态：`PASS_PARMA511_MONO_LINE_MODULE_AND_OFFLINE_RECOMPOSITION__SCIENTIFIC_BLOCKERS_REMAIN`  
总体证据等级：`SHARE_WITH_CAVEATS__NOT_PUBLICATION_AUTHORITY`

## 结论

PARMA 给出的大气湮没线已作为唯一被替换的物理模块处理：单能 gamma 为 510.99895 keV，day-15 全立体角通量为 0.166515471602261 ph cm^-2 s^-1。其余 prompt、delayed/activation、signal、continuum 和其他粒子模块均沿用 retained 产品并只做离线重组；本最终化步骤没有模拟或 transport 执行接口。

完整单 campaign 由 60 个批次组成，TS=180,000,000，TE=95575.475072 s，transport seeds=60。80-bin 主响应选后 663 个事件，day-15 率为 0.00693692602104 cps，RSE=3.884%，40/80 同事件组合相对差为 0.121%。动态 detector-rate gate 通过。

离线重组严格复核公式：

`R_new = R_old - R_legacy_sidecar - Delta_R_prompt_gamma_line + R_PARMA511_corrected`

day-15 retained prompt=0.00339303151412 cps，retained delayed=0.00201657067387 cps，移除旧 sidecar=0.00155526135195 cps，加入修正 PARMA line=0.00693692602104 cps，重组本底=0.012346528209 cps。20 d 条件式折叠得到 source counts=1650.787710、background counts=20734.191748、Z=11.464303。这些总本底和任务指标仍是条件式结果，不是论文发表权威。

偶然符合 occupancy 也只做离线去重：`lambda(t) = prompt_event_rate_hz(t) - removed_prompt_gamma_line_occupancy_hz(t) + delayed_event_rate_hz(t) + corrected_PARMA511_event_rate_hz(t)`。day-15 从 retained prompt occupancy 中按 `prompt_scale_gamma` 移除 737.844505176 Hz 的错误展宽线项，再加入修正 line occupancy；legacy sidecar occupancy 独立省略一次，未从 prompt 重复扣除。该修正没有重新运行任何粒子或输运。

外部 raw 清理凭据覆盖 60/60 个新 campaign raw 路径；这些 raw 已不存在，不能本地恢复。其精确路径、原大小、SHA-256、source cards、seeds、compact catalogs、response 输出与分批清理凭据仍保留可审计链路。

## 仍然存在的科学 blocker

- `LEGACY_PROMPT_GAMMA_AXIS_FACTOR_1000` (SCIENTIFIC_BLOCKER): The complete retained O8 prompt-photon DP abscissa is 1000 times below the correct Cosima-keV axis. The selected W2 rate delta is zero and the active-only misplaced-line occupancy is removed offline, but neither operation repairs absolute prompt-gamma continuum fidelity.
- `FROZEN_ACTIVE_SHIELD_NAME_MATCH_INCLUDES_PASSIVE_KAPTON` (SCIENTIFIC_BLOCKER): The frozen final predicate matches the substring ACTIVE_SHIELD and therefore includes three passive ActiveShield_S3C_BGO_Kapton_* scorer volumes in the 50-keV veto; it is not a BGO-plus-plastic-only mask.
- `DAY15_ANGULAR_RESPONSE_HELD_FIXED_ACROSS_MISSION` (CONDITIONAL_MODEL_QUALIFICATION): Only the day-15 line detector response is available. The 20-day fold holds that angular response fixed while evaluating PARMA line flux at retained depths with fixed W and Rc.

## 顶层状态字符串的处理

以下 producer 顶层字符串或计数可能硬编码为 diagnostic/prepared，本工具没有用它们替代动态数值门槛：

- `aggregate_receipt.status` = `CAMPAIGN_COMPACT_AGGREGATE_COMPLETE_DIAGNOSTIC_ONLY`：仅作信息记录；producer top-level status may retain a hard-coded DIAGNOSTIC string; the dynamic primary gate is authoritative。
- `response_summary.status` = `DIAGNOSTIC_ONLY_LINE_MODULE_RESPONSE_NOT_MANUSCRIPT_PASS`：仅作信息记录；producer top-level status may retain a hard-coded DIAGNOSTIC string; the dynamic primary gate is authoritative。
- `campaign_manifest.batch_status_counts` = `{'PARSED_AND_RESPONSE_DIAGNOSTIC_COMPLETE': 60}`：仅作信息记录；PREPARED/DIAGNOSTIC labels are producer bookkeeping; included compact batch receipts and their checks are validated directly。
- `recomposition_manifest.status` = `MODULAR_RECOMPOSITION_COMPLETE__SCIENTIFIC_BLOCKERS_REMAIN__NOT_PUBLICATION_AUTHORITY`：仅作信息记录；numeric validity is reconstructed from final-input gates, formulas, hashes, and invariants; publication blockers are reported separately。
- `day15_modular_recomposition.status` = `MODULAR_RECOMPOSITION_COMPLETE__SCIENTIFIC_BLOCKERS_REMAIN__NOT_PUBLICATION_AUTHORITY`：仅作信息记录；not used as a substitute for the dynamic line gate or formula audit。
- `mission_20d_modular_recomposition.status` = `MODULAR_RECOMPOSITION_COMPLETE__SCIENTIFIC_BLOCKERS_REMAIN__NOT_PUBLICATION_AUTHORITY`：仅作信息记录；not used as a substitute for the dynamic line gate or formula audit。

## 声明边界

修正后的 PARMA 单线模块及其离线替换算术通过。本结论不授权、也不建议重跑 continuum、prompt、delayed/activation、signal、其他粒子或全链；现有科学 blocker 未解决前，不得把重组后的总本底和任务指标直接写成 publication authority。
