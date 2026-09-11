# M05NEW 数据引用文件

表中 `Rxx` 均指向本地可审计文件。论文数字优先引用结果文件；方法合同引用配置或 manifest。

| 编号 | 文件 | 用途 |
|---|---|---|
| R01 | `core_md/balloon511_ea_latex_drafts/m05_atm511_source_revision_20260811/balloon511_ea_draft_en_m05_atm511_source_revision_20260811.tex` | M05 英文稿的数据槽位、旧表图和固定仪器/文献基准。中文稿在同目录。 |
| R02 | `DEEPSEEK_CODE/modified/analysis_inputs_optv3_B.json` | 当前候选、几何哈希、响应、veto、Step05、信号、任务和时间线合同。 |
| R03 | `engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json` | 修复后八类源、keV 总动能合同、环境、gamma/mono-511 合同。 |
| R04 | `engineering/particle_source_unit_repair_20260811/data/static_validation.json` | 160 个归一谱、24 张源卡、480 个修复引用和零 legacy 引用的静态验证。 |
| R05 | `core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_expacs_fullsphere_flux_summary.csv` | 八类粒子的 down/up/total 全空间积分通量。 |
| R06 | `engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/data/parma_energy_integrated_family_scales_81bins.csv` | 81 节点 family 时间缩放。 |
| R07 | `DEEPSEEK_CODE/outputs/03_gamma_expansion_audit_20260820.json` | gamma 扩统计量、round005 排除、种子与 receipt 审计。 |
| R08 | `DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/summary.json` | prompt/delayed 归一化、活动度、任务数、精确位置 lineage 和目录规模。 |
| R09 | `DEEPSEEK_CODE/outputs/05_mature_timeline_m05_fixed_20260820/summary.json`；`DEEPSEEK_CODE/outputs/05_mature_timeline_m05_fixed_20260820/mission_timeline_81nodes.csv` | OptV3 信号 Aeff、五锚点共时间轴、20 d counts、Fmin、显著度和统计误差。 |
| R10 | `DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/direct_cutflow.csv`；`direct_cutflow_totals.csv`；`combined_event_catalog.npz`；`category_registry.json` | 当前 cutflow、family/nuclide 分解、谱、多重性和 Step05 出图源。 |
| R11 | `DEEPSEEK_CODE/outputs/06_final_statistics_validation_20260820.json` | 14 项独立统计/信号变换/Step05 逻辑闭合验证。 |
| R12 | `/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon/engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/README.md` | OptV3 结构说明和几何验证状态。 |
| R13 | `/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon/engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/data/assembly_opt_v3_manifest.json` | OptV3 尺寸、CSG 合同、输出哈希和图形文件。 |
| R14 | `/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon/engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/geometry/SH3_Assembly_OptV3.det` | 六层 TES 与三块活动 BGO detector declarations、80 keV native trigger。 |
| R15 | `engineering/geometry_optimization_20260815/58_sg3b_m05_common_time_response_20260817/outputs/01_common_time_response/summary.json` | SG3B 修复后自有背景和条件代理信号边界。 |
| R16 | `engineering/geometry_optimization_20260815/58_sg3b_m05_common_time_response_20260817/outputs/01_common_time_response/sg3b_measured_cutflow.csv` | SG3B family-resolved measured cutflow。 |
| R17 | `engineering/geometry_optimization_20260815/59_sg3b_prompt_activation_coupling_20260818/outputs/02_coupling_analysis/summary.json`；同目录的 `activation_by_*.csv` 与 `selected_event_lineage.csv` | SG3B prompt/activation family、材料、核素、体积来源。 |
| R18 | `engineering/geometry_optimization_20260815/60_sg3b_time_audit_nuclide_section_20260818/outputs/summary.json`；`selected_w2_activation_origin_groups.csv` | SG3B 时间归一化审计和 selected W2 核素/体积明细。 |
| R19 | `/home/ubuntu/.codex/worktrees/4f50/TES_511_Balloon/engineering/geometry_optimization_20260815/55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816/README.md`；`data/sg3b_static_and_f3_estimate.json`；`audit/sg3b_geometry_validation.json` | SG3B 基线几何、质量改动、静态光路与 overlap 验证。 |
| R20 | `engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820/outputs/01_signal/summary.json`；`config/sg3b_signal_37194.source` | SG3B 自有 37,194-ray 信号输运、响应 cut-flow、Aeff 与 binomial 误差。 |
| R21 | `engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820/outputs/03_expanded_catalog/summary.json`；`expanded_direct_cutflow.csv`；`outputs/04_candidate_timeline/summary.json`；`mission_mature_flux_threshold.csv` | SG3B prompt-gamma 稀疏统计、总本底投稿精度门槛、扩展目录、同口径 cut-flow、81 节点任务灵敏度和统计误差。 |
| R22 | `engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820/outputs/05_optv3_delayed_origins/summary.json`；`optv3_delayed_origin_breakdown.csv`；`optv3_delayed_selected_events.csv` | OptV3 最终 delayed W2 事件的精确生产体积、材料、family 与父核素回连。 |
| R23 | `M05NEW_VALIDATION.json`；`SG3B_OPTV3_COMPARISON.json` | M05NEW 全部必需数据的独立终审与 SG3B--OptV3 匹配比较摘要。 |
| R24 | `engineering/geometry_optimization_20260815/66_m05new_mxc_bpe_veto_review_20260821/README.md`；`outputs/assessment.json`；`data/cross_section_geometry_contract.csv`；`data/cold_stage_origin_share.csv`；`data/optv3_background_composition.csv`；`data/optv3_bpe_plastic_upper_bounds.csv`；`M05NEW/figures/fig_mxc_tes_sg3b_sh3_section.{png,svg,pdf}` | SG3B/SH3 同尺度 MXC—TES 剖面、精确 delayed-source 位置、冷盘来源占比和 plastic/BPE 的 Fmin 理想上限。 |
| R25 | `engineering/particle_source_unit_repair_20260811/bpe_neutron_boundary_20260813/REPORT.md`；`outputs/summary.json`；`outputs/boundary_spectrum.csv`；`outputs/cu_reaction_fold.csv` | corrected-keV 2 cm、5 wt% BPE 的 100,000-history 边界诊断：能量依赖透射、慢化和 Cu-61/62/64 直接反应流折叠；不是 SH3 no-BPE/BPE 净本底 A/B。 |

## 论文引用规则

1. 主灵敏度、day-15 rate、20 d counts 和统计误差引用 R09，并用 R11 作为独立闭合凭据。
2. prompt/delayed 分量率引用 R08/R10；不要从 rounded mission anchor rate 反推分量率。
3. 源合同引用 R03/R04；不要再引用或恢复 `cosima_spectra_dp_2602units` 旧结果。
4. R12–R14 是当前工作树中的 OptV3 几何来源。投稿归档前应按原路径/哈希固化到最终数据包，但这不改变本表数值。
5. R15 的旧 SG3B 灵敏度仍是历史条件代理；论文中的 SG3B 候选自有信号、扩统计背景和灵敏度只引用 R20/R21。
6. OptV3 的 delayed 材料/体积叙事只引用 R22 的 selected-event 回连结果，不用总 activation inventory 代替 science-window 贡献。
7. MXC/冷盘几何因果、外置 plastic/BPE 上限引用 R24；BPE 的直接中子输运机制引用 R25。
   不能把 R25 的边界 current ratio 写成最终 W2 本底抑制率。

## 外部材料物理参考（只支撑一般机制）

- IAEA, *Neutron monitoring for radiation protection*, Safety Reports Series：含氢材料通过散射慢化，
  高能中子常需分层屏蔽；硼俘获会伴随约 0.43 MeV gamma，因此屏蔽顺序和次级光子也要考虑。
  https://www-pub.iaea.org/MTCD/Publications/PDF/PUB1987_web.pdf
- Pan, Lin & Pan (2013), *Experimental Studies and Analysis of 5% Borated Polyethylene
  Shielding Fast Neutron*, DOI `10.13491/j.cnki.issn.1004-714x.2013.04.001`：给出 3.2--22.4 cm
  的标准中子源透射实验。该实验只说明厚度尺度，不替代本项目大气谱运输。
