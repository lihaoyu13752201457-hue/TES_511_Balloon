# 代码导航

下列相对路径均相对于恢复后的来源根目录。主项目入口通常在 `sources/main/`；历史工作树采用差异存储，**缺少实体副本不代表代码未保存**，须用 `manifests/files.jsonl` 或恢复工具查看该来源的完整集合。

| 环节 | 主要代码位置 |
|---|---|
| 最终 27° 重算与论文图表 | `tmp/m05_issue9_fixed27_20260831/build_fixed27_paper_assets.py`、同目录 `build_environment_screening_fixed27.py` 与三个来源饼图脚本 |
| 最终英文稿与中间 45° 图表 | `tmp/m05_environment_extension_20260830/build_clean_english_manuscript_20260831.py`、`build_section4_reference_flux_20260830.py`、`figure_revision_r19/`、`figures/` |
| 最终章节与几何绘图 | `core_md/balloon511_ea_latex_drafts/M05NEW/`；`tmp/m05_environment_extension_20260830/figures/` |
| A/B 正式统计整合、共同时间轴、不确定度 | `engineering/geometry_optimization_20260815/70_m05_sg3_sh3_prompt_statistics_integration_20260828/code/` |
| P70 调用的 flux-closed timeline | 来源 `worktree_ebb2`：`engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/code/run_fluxclosed_timeline.py` |
| SG3B/SH3 几何、信号与背景分析 | 各来源 `engineering/geometry_optimization_20260815/` 下 P56–P70；`DEEPSEEK_CODE/modified/` |
| TES 响应与 Compton 选择 | `DEEPSEEK_CODE/modified/build_event_catalog_sh3_step05.py`、`step05_side_compton.py`；`old/code/tools/build_v3p5_centerfinger_step05_l1_response.py` |
| 修正 keV 粒子源、输运、活化、紧凑记录与钩子 | `engineering/particle_source_unit_repair_20260811/` 中代码、源契约、谱表和配置；`code/tools/` |
| PARMA 粒子源上游 | 来源 `codex_tes_511_sim`：`COSMOSRAY_BALLOON_SIM/tools/phase2_parma_grid_driver.cpp`、`external/expacs_parma/parma_cpp/` 及系数表；也保留 Fortran 实现 |
| 环境比较 | P71 `code/build_environment_screening.py` 及 P64/P65；`engineering/environment_response_projection_20260813/`、卫星/月面环境包 |
| Laue 光学 Geant4 实现 | 来源 `opticsim`：`opticsim_full/geant4_app/src/laue_multiring_bfull_demo.cc`、相应 headers、CMake、config、analysis；`external_baseline/` |
| 光学独立校验与补丁 | 来源 `cross_check_laue`：`laue511_validation/` 与根目录 `.patch` 文件 |
| 聚焦光子到 Cosima 的桥接 | `stepwise_maintenance/step09_optics_bridge/` 及光学/独立校验中的转换代码 |
| 实际安装的 Cosima/MEGAlib 实现 | 来源 `megalib`：`src/`、`config/`、安装脚本、补丁及相关模板；含 MCSource、MCEventAction、MCSteppingAction、MCRun、MCIsotopeStore |
| 后续低温响应研究 | 来源 `neutron_fen`：源代码、配置和依赖说明；属于补充研究 |

为防止动态加载、跨工作树导入或临时作图脚本遗漏，保留了这些来源中的更广泛程序源码集合。原代码没有为本次备份修改；因此历史算法、已弃用入口和实验脚本也在快照中，具体入口要以最终稿链条为准。

原始源码的绝对引用统计见 `manifests/external_project_references.json`。该表包含历史和可选工具引用，不等同于最终论文的必需依赖清单。对论文关键入口的备份覆盖检查见 `manifests/critical_code_coverage.json`。
