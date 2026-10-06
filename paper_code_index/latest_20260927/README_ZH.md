# 最新论文代码索引与源码快照（论文版本：2026-09-27）

这是为用户“先索引最新版论文用的代码，然后 push git”建立的新索引包。**没有修改、移动或删除原代码、论文、仿真数据；没有运行生产模拟、数值重算或论文编译。**

## 1. 绑定的是哪一版论文

项目根目录以下路径为当前依据：

- 正式最新稿：`paper_review_workspace_20260920/outputs/00_parent/EA_submission_20260927_data_availability/paper_clean.tex`（同目录含 PDF、17 幅图和源包）。由 `outputs/00_parent/LATEST_MANUSCRIPT_ZH.md` 明确指定，不是仅按修改时间挑选。
- 后续独立蓝标副本：`outputs/00_parent/revision_20260927_pairs_blue/paper_pairs_blue.tex`。其 README 明确说明基于用户粘贴文本新建，**未改变正式最新稿指针**，所以独立索引，不自动覆盖正式稿。
- 当前数值权威：`outputs/00_parent/activation_correction_20260924/production_repair_20260925/final/data/RESULTS.json`。20 天通量为下置 `(6.97 ± 0.51) × 10^-5`、侧置 `(3.30 ± 0.28) × 10^-5`，对应末版正文，不采用较早目录中旧的“final”数字。

以上论文身份的 SHA-256、原始路径和大小见 [INDEX.json](INDEX.json)。本次没有新上传论文正文、PDF 或图件，仅记录其身份。

## 2. 怎么读这个索引

- [SOURCES.tsv](SOURCES.tsv)：逐文件分组、原始路径、快照路径、字节数和 SHA-256。
- [INDEX.json](INDEX.json)：机器可读总索引、模块边界、源文件实际位置、原软链接指向、排除范围和外部依赖。
- [DEPENDENCIES.json](DEPENDENCIES.json)：人工核对的核心直接代码依赖及引用行号。
- `snapshot/project/`：保持原项目相对路径的源码和小型出处/数值表副本；**不是修改原文件**。
- `snapshot/external/worktree_8633/tool/execute/`：AA 生产适配器确实使用的工作副本执行器代码。它原先不在本主工作树中，不能只记录一个未来可能失效的本机链接。

选择范围是“已核对入口 + 同模块保守保留的辅助源码”，**不声称每个辅助脚本都在末版构建时执行过**。核心依赖边也不等于穷尽了动态加载和运行时依赖。未采用清理/删除脚本、无关监控程序和 PPT 构建程序。

## 3. 科学与出版代码主线

路径缩写：`R = paper_review_workspace_20260920/outputs/00_parent`，`G = engineering/geometry_optimization_20260815`。

| 阶段 | 主要入口（原项目相对路径） | 本次索引含义 |
|---|---|---|
| 修正光学与独立参考 | `paper_review_workspace_20260920/outputs/01_intro_geometry_optics/c_repair_20260920/src/CrystalKernel.hh`、`src/laue511.cc`、`code/build_reference.py`、`code/export_focus.py` | 自定义 Geant4 Laue 过程、XOP 参考、焦面信号导出，附发布清单 |
| 光学信号和像素响应 | `paper_review_workspace_20260920/outputs/02_sources_response_compton/corrected_optics_signal_20260920/code/analyze_signal.py`、`pixel_geometry_compton.py`、`legacy_side_compton.py` | 固定像素几何及康普顿核；该包 A 几何是 AA 更新前的前驱，最终 A 入口在下一行 |
| 最终下置 AA 几何与输运 | `engineering/mass_model_AA_20260921/code/build_aa.py`；`R/AA_run_20260921_v1/code/aa_common.py`、`analyze_aa_signal.py` | 实际 AA 几何、规范源卡/种子、信号响应；执行器来自工作副本 8633 |
| 侧置 SH3 事例目录 | `G/70_m05_sg3_sh3_prompt_statistics_integration_20260828/code/` | 合并统计和下游实际使用的 B 响应事例入口，不混用前驱 A 结果 |
| 连续几何共同响应 | `R/revision_20260921_AA_continuous/code/common.py`、`continuous_disk.py`、`pixel_geometry_compton.py` | 500 eV 像素响应、主动 BGO、实际像素与连续圆锥判选 |
| 活化核链和归一化 | `R/activation_correction_20260924/code/decay_kernel.py`、`correct_response.py`、`common.py` | 母核/子体身份、解析库存与响应权重；保留父模块依赖 |
| 生产库存修复 | `R/activation_correction_20260924/production_repair_20260925/code/analyze_production.py`、`build_ledger.py`、`combine_repaired.py` | 母核生产时差索引错误修复和最终合并结果 |
| 两种独立 Cosima 模式 | 同修复包 `runtime/production_timing_fix.patch`、`runtime/production/MCSteppingAction.cc`、`runtime/MCSteppingAction.cc`；父包 `targeted_response/MCSource.cc` | 普通生产仅修正索引；逐核态响应还采用独立库存/禁重复排队语义，两者**不能互换**；保存源码不保存二进制 |
| 三路物理泊松时间轴 | `R/three_stream_poisson_20260921/code/timeline_deferred.cpp`；修复包 `final/code/prepare_timelines.py`、`analyze.py`、`integrate_corrected.py` | 末版采用修复包 final 的响应和积分，早期模块仅作上游支持 |
| 跨环境筛查 | `G/71.../code/build_environment_screening.py` → `G/65.../code/build_complete_l2_solar.py` → `G/64.../code/build_sh3_environment_projection.py`；`R/antarctic_environment_20260924/code/` | 保留谱重加权/代理环境边界，不把它写成新增轨道匹配输运 |
| 论文数字、图表与核验 | `R/final_manuscript_20260926_activation/code/build_manuscript.py`、`update_figures.py`、`build_environment_figure.py`、`validate_package.py` | 使用已修复结果；旧目录中仍使用的图样式与剖视代码已单独保存 |
| 投稿样式与 PAIRS 蓝标副本 | `R/revision_20260927_ea_references/code/`；`R/revision_20260927_pairs_blue/code/build.py` | 出版/文字辅助与科学计算代码分组区分 |

表中的缩写只用于阅读。逐文件完整路径请查 TSV/JSON；快照保留完整目录名。

## 4. 不能因“代码已经 push”而删除的数据

这份索引**不是可单独运行的完整复现包，更不是删除授权**。仍须另行保留：

1. corrected-keV 原始/转换谱、源卡合同、核数据和几何递归输入；旧错误能量轴结果不能代替它们。
2. 实际 AA/SH3 的原始 SIM/DAT、响应目录、NPY/NPZ、激活库存、每个分层的曝光、seed/receipt/ledger。
3. 论文完整 TeX/PDF/17 幅图，以及未打包的大数值数组和原始焦面/输运事件。
4. MEGAlib、Geant4、ROOT、XOP/DIFF_PAT、xoppylib、xraylib、DABAX、crystalpy 的固定安装版本与许可材料。

原始数据清单含 `/media/ubuntu/903261CE3261BA3C/TES_Balloon_511_data/`；建索引时该外盘目录未挂载。没有假称已经验证这些外盘原始文件的备份完整性。

源码保留原有绝对路径、环境、历史任务期限和种子合同，未静默替换成本机的新路径。跨机器复现必须显式配置依赖、恢复数据、审定重定位和新的运行目录/种子，**不要直接批量运行快照里的生产或修改脚本**。

## 5. 只读验证

在项目根目录运行（不导入科学代码、不启动模拟、不产生 pyc）：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 paper_code_index/latest_20260927/verify_index.py
```

在原电脑额外检查原文件与论文身份是否仍匹配：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 paper_code_index/latest_20260927/verify_index.py --check-originals
```

本轮校验结果见 [VALIDATION.json](VALIDATION.json)：逐文件 SHA-256/大小、Python AST 语法、核心依赖端点和原始文件一致性。**这些是代码存档检查，不是重新验证物理结果，也不是证明可以删除未快照的数据。**
