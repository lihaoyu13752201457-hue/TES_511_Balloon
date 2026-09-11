# M05NEW 数据引用文件

表中 `Rxx` 均指向本地可审计文件。论文数字优先引用结果文件；方法合同引用配置或 manifest。

| 编号 | 文件 | 用途 |
|---|---|---|
| R01 | `core_md/balloon511_ea_latex_drafts/m05_atm511_source_revision_20260811/balloon511_ea_draft_en_m05_atm511_source_revision_20260811.tex` | M05 英文稿的数据槽位、旧表图和固定仪器/文献基准。中文稿在同目录。 |
| R02 | `DEEPSEEK_CODE/modified/analysis_inputs_optv3_B.json` | 当前候选、几何哈希、响应、veto、Step05、信号、任务和时间线合同。 |
| R03 | `engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json` | 历史宽带运输输入与keV总动能合同；其旧“宽带内含线、不得加单能线”结论已由R26的通量守恒分解取代，不能作为当前511线归一依据。 |
| R04 | `engineering/particle_source_unit_repair_20260811/data/static_validation.json` | 160 个归一谱、24 张源卡、480 个修复引用和零 legacy 引用的静态验证。 |
| R05 | `core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_expacs_fullsphere_flux_summary.csv` | 八类粒子的 down/up/total 全空间积分通量。 |
| R06 | `engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/data/parma_energy_integrated_family_scales_81bins.csv` | 81 节点 family 时间缩放。 |
| R07 | `DEEPSEEK_CODE/outputs/03_gamma_expansion_audit_20260820.json` | gamma 扩统计量、round005 排除、种子与 receipt 审计。 |
| R08 | `DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/summary.json` | 历史宽带目录输入；当前三分量flux-closed目录以R29为准。 |
| R09 | `DEEPSEEK_CODE/outputs/05_mature_timeline_m05_fixed_20260820/summary.json`；`DEEPSEEK_CODE/outputs/05_mature_timeline_m05_fixed_20260820/mission_timeline_81nodes.csv` | 质量模型B信号响应与旧宽带时间线输入；当前含单能线任务结果以R30/R33为准。 |
| R10 | `DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/direct_cutflow.csv`；`direct_cutflow_totals.csv`；`combined_event_catalog.npz`；`category_registry.json` | 历史目录的cutflow与分类输入；当前谱、多重性及分量图以R29/R30/R32为准。 |
| R11 | `DEEPSEEK_CODE/outputs/06_final_statistics_validation_20260820.json` | 历史无显式单能线闭合检查；当前统计验收以R31为准。 |
| R12 | `/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon/engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/README.md` | OptV3 结构说明和几何验证状态。 |
| R13 | `/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon/engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/data/assembly_opt_v3_manifest.json` | OptV3 尺寸、CSG 合同、输出哈希和图形文件。 |
| R14 | `/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon/engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/geometry/SH3_Assembly_OptV3.det` | 六层 TES 与三块活动 BGO detector declarations、80 keV native trigger。 |
| R15 | `engineering/geometry_optimization_20260815/58_sg3b_m05_common_time_response_20260817/outputs/01_common_time_response/summary.json` | SG3B 修复后自有背景和条件代理信号边界。 |
| R16 | `engineering/geometry_optimization_20260815/58_sg3b_m05_common_time_response_20260817/outputs/01_common_time_response/sg3b_measured_cutflow.csv` | SG3B family-resolved measured cutflow。 |
| R17 | `engineering/geometry_optimization_20260815/59_sg3b_prompt_activation_coupling_20260818/outputs/02_coupling_analysis/summary.json`；同目录的 `activation_by_*.csv` 与 `selected_event_lineage.csv` | SG3B prompt/activation family、材料、核素、体积来源。 |
| R18 | `engineering/geometry_optimization_20260815/60_sg3b_time_audit_nuclide_section_20260818/outputs/summary.json`；`selected_w2_activation_origin_groups.csv` | SG3B 时间归一化审计和 selected W2 核素/体积明细。 |
| R19 | `/home/ubuntu/.codex/worktrees/4f50/TES_511_Balloon/engineering/geometry_optimization_20260815/55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816/README.md`；`data/sg3b_static_and_f3_estimate.json`；`audit/sg3b_geometry_validation.json` | SG3B 基线几何、质量改动、静态光路与 overlap 验证。 |
| R20 | `engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820/outputs/01_signal/summary.json`；`config/sg3b_signal_37194.source` | SG3B 自有 37,194-ray 信号输运、响应 cut-flow、Aeff 与 binomial 误差。 |
| R21 | `engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820/outputs/01_signal/summary.json` | 质量模型A自有37194-ray信号响应；当前背景与任务灵敏度以R30/R33为准。 |
| R22 | `engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820/outputs/05_optv3_delayed_origins/summary.json`；`optv3_delayed_origin_breakdown.csv`；`optv3_delayed_selected_events.csv` | OptV3 最终 delayed W2 事件的精确生产体积、材料、family 与父核素回连。 |
| R23 | `M05NEW_VALIDATION.json`；`SG3B_OPTV3_COMPARISON.json` | M05NEW结构化终审与质量模型A/B匹配比较；当前版本由R26–R33证据链生成。 |
| R24 | `engineering/geometry_optimization_20260815/66_m05new_mxc_bpe_veto_review_20260821/README.md`；`outputs/assessment.json`；`data/cross_section_geometry_contract.csv`；`data/cold_stage_origin_share.csv`；`data/optv3_background_composition.csv`；`data/optv3_bpe_plastic_upper_bounds.csv`；`M05NEW/figures/fig_mxc_tes_sg3b_sh3_section.{png,svg,pdf}` | SG3B/SH3 同尺度 MXC—TES 剖面、精确 delayed-source 位置、冷盘来源占比和 plastic/BPE 的 Fmin 理想上限。 |
| R25 | `engineering/particle_source_unit_repair_20260811/bpe_neutron_boundary_20260813/REPORT.md`；`outputs/summary.json`；`outputs/boundary_spectrum.csv`；`outputs/cu_reaction_fold.csv` | corrected-keV 2 cm、5 wt% BPE 的 100,000-history 边界诊断：能量依赖透射、慢化和 Cu-61/62/64 直接反应流折叠；不是 SH3 no-BPE/BPE 净本底 A/B。 |
| R26 | `engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/outputs/00_source_closure/source_closure.json`；`coarse_line_decomposition_20bins.csv`；`mono511_target_81x80.csv`；`trajectory_component_scales_81nodes.csv` | 当前源级权威：宽带总量减粗分箱线面积后再加PARMA单能线；day-15线通量`0.16651547160226118 ph cm^-2 s^-1`，80个等mu分量，81节点逐分量权重。哈希依次为`acfa91b0cfc36b6492e218a9164473cef51f2cca2c47a186d45ec96f5983cbae`、`f2394067e057d9092851244cd5e5076d8b867fe3b05fe1d9b77d8af173aaecf4`、`92ee53428dceb36f4d6c1eb0b7efd72ad239dd233f25af73618aa654ee6cdd90`、`e72d4707be4fcb4b54ebf304a6dcb61748198326c8858f987264c864cc7f42fa`。 |
| R27 | `engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/outputs/01_line_response_a/summary.json`；`mono_line_event_catalog.npz`；`mono_line_cutflow.csv`；`mono_line_final_by_source_bin80.csv` | 质量模型A的510.99895 keV、PARMA 80分量、共同响应/选择线响应；3000000 incident、12 final。哈希：`72e13caa705025e633a9a24ac67db2eb0587e82c781ec6416c7eba2c32c3e662`、`2f84d8f74f67d6c2269cd9e855f1df747351207829fdf705043e040f1f29f6f2`、`2d691e21f8c7f0d3deba9b462d1825762b9caa2a14d6074f8117badcea4386a4`、`d2afbcc91f68c7eb4ca95dda2f7e06d9aac5e815d812f0d8473406c5ecd5f9ab`。 |
| R28 | `engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/outputs/01_line_response_b60/summary.json`；`mono_line_event_catalog.npz`；`mono_line_cutflow.csv`；`mono_line_final_by_source_bin80.csv`；`MERGE_RECEIPT.json` | 质量模型B的共同线响应及最小必要增量统计合并；15709417 incident、186 final。主要哈希：`d6487790c9818f0dde9fef1323e164ae3dc500559381fdfdca6ffd21558de1e2`、`15e5688688f8c3da4998dfa32119e77f1d9ef0685a30cc4fb1beea06ed80e77d`、`e264f97841eb80ed636293c38da02bbccb69c1a1b3e0b49ab055dc29d3e33986`、`b970ee2483eedbb0415497b3e6d59cfed0b3de4eb732ee922fb554dbd9ac5456`。 |
| R29 | `engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/outputs/02_fluxclosed_catalog_{a,b}/` | 质量模型A/B的正权重三分量目录、`sumw2`、ESS与一次性连续谱去线权重审计。summary哈希：A `2de6a9520ea4149171b6a80c1df8939dda9385d3aff5125eea27704c6460a50c`；B `63ee8e7114256fde6c7698bc5931f29aef7d501b8d2f908f341dbe0e32b7625e`。 |
| R30 | `engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/outputs/03_fluxclosed_timeline_{a,b}/` | 五个公共时间锚点、81节点占空率、累计本底、信号核、Gaussian/Asimov显著度和Fmin及误差；summary哈希：A `058b43d8fe73e13d25a82b8aa9d5ea3a800db16439c12bd91e778f8f734f946d`；B `90e8ebc1d530ee2d863bd13c0ee6f8118dbebb38ed35621c3ca293c109c1d426`。 |
| R31 | `engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/outputs/04_validation/topup_decision.json` | 源公式、响应、目录、五锚点/81节点、`sumw2`/ESS、误差传播及增量统计门槛的独立验证；最终`PASS__FLUXCLOSED_RESULTS_VALIDATED__NO_TOPUP`。哈希`453171491f36530ab36e3e2e30b8a3ee9f12d02e803c36b186592445421c6fac`。 |
| R32 | `engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/outputs/05_figures_staging/receipt.json`；`chart_map.json`；`fig03`–`fig10` | 当前出图证据与输入哈希闭合，receipt状态`PASS__M05_FLUXCLOSED_FIGURES_STAGED`、哈希`36c232953a128dc72e3bc2202dd61180aae47b89c5b9b50f692dd7ae26e3ad8b`。M05NEW图3按用户要求保留原图；仅图4–10从此包刷新。 |
| R33 | `engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/outputs/06_publication_values/publication_values.json`；`source_closure_values.csv`；`day15_component_values.csv`；`five_anchor_values.csv`；`model_summary_values.csv`；`ab_improvement_values.csv`；`receipt.json` | 稿件唯一数值回填表；publication JSON哈希`35f9b714b854edae43a95f58ac86de7cab4a7d876935b6846ff9acee25b38c5a`，receipt哈希`d784ac831779a0a65071e6959d06d957494c87a1a0a26858c8d934d7f8252c64`。 |
| R34 | `M05NEW_VALIDATION.json`；`SG3B_OPTV3_COMPARISON.json`；`M05_PAPER_DATA_TABLE.csv`；`README.md` | 当前M05NEW结构化发布层；TeX/PDF最终哈希必须在双语编译完成后另行填写，不能预构造。 |

## 论文引用规则

1. 当前源定义只引用R26：严格使用“宽带总量−粗分箱线面积+PARMA单能线”。不得把R27/R28的线响应直接加到未去线的旧宽带目录。
2. 单能线的积分通量和80分量角分布由PARMA专用线参数化给出；day-15全空间通量固定为`0.16651547160226118 ph cm^-2 s^-1`。论文参考文献[33,34]（Mahoney/Harris）只证明大气湮没线成分的存在和物理背景，不提供本模拟的数值归一。
3. 质量模型A/B线响应分别引用R27/R28，统一目录引用R29，五锚点及81节点任务折叠引用R30，统计/增量判断引用R31。
4. day-15分量率、20 d counts、Gaussian/Asimov Fmin及误差和A/B比值优先引用R33；不要从图或四舍五入的锚点率反推。
5. 加权结果使用`sumw`、`sumw2`和ESS；旧常权scaled-Garwood条目不得作为当前总本底或Fmin主误差。
6. R26明确记录混合模板边界：连续谱去线参考为W=118.3/g=0，物理线目标为W=114.6/g=0.15；不得把它写成全套宽带分量在单一参数状态下重新生成。PARMA物理源系统学在当前统计误差中排除。
7. 图3保留当前M05NEW图像；图4–10使用R32刷新。质量模型A/B几何与候选自有信号仍由R12–R14、R19–R22提供，不交叉借用信号核。

## 外部材料物理参考（只支撑一般机制）

- IAEA, *Neutron monitoring for radiation protection*, Safety Reports Series：含氢材料通过散射慢化，
  高能中子常需分层屏蔽；硼俘获会伴随约 0.43 MeV gamma，因此屏蔽顺序和次级光子也要考虑。
  https://www-pub.iaea.org/MTCD/Publications/PDF/PUB1987_web.pdf
- Pan, Lin & Pan (2013), *Experimental Studies and Analysis of 5% Borated Polyethylene
  Shielding Fast Neutron*, DOI `10.13491/j.cnki.issn.1004-714x.2013.04.001`：给出 3.2--22.4 cm
  的标准中子源透射实验。该实验只说明厚度尺度，不替代本项目大气谱运输。
