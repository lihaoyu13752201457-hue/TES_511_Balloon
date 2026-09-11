# 项目内部待修复与待补充清单

日期：2026-06-23

用途：这是论文之外的项目工程清单。它列的是不能只靠改论文文字闭合的问题，包括模拟重跑、证据溯源、配置权威表、验证工具、图件数据管线和是否扩展论文 claim 的判断。它不是正文，也不应该直接复制进论文。

当前论文已经收缩到一个相对稳妥的 scope：基于当前探测器/低温系统 proxy 质量模型，对未分辨 511 keV 线做 reference-exposure selected-rate estimate。只在这个 scope 下，Phase 1 修改后的论文可以暂时闭合。如果要声称“最终飞行性能”“整机本底闭合”“活化本底最终精度”或“投稿级灵敏度”，下面的项目侧工作必须继续做。

## 判断标准

| 判断 | 含义 | 我怎么用 |
|---|---|---|
| 立即做 | 成本低、收益高、会直接影响论文可信度，或很容易导致旧错误回流。 | 下一轮认真修稿前优先安排。 |
| 值得做 | 科学或工程价值明确，但不一定是当前窄 scope 的硬门槛。 | 有时间应做，尤其是投稿前或扩展 claim 前。 |
| 条件性做 | 只有当论文 claim 扩展时才值得投入。 | 例如从 proxy estimate 改成 flight forecast 时才做。 |
| 现在不值得做 | 问题真实存在，但当前阶段投入产出比差，会把项目带到另一个大方向。 | 保留为 limitation/future work，不在当前主线消耗资源。 |

## 总优先级概览

| 优先级 | ID | 项目 | 判断 | 核心理由 |
|---:|---|---|---|---|
| 1 | PI-01 | 证据溯源 manifest 与旧文件隔离 | 立即做 | 防止旧错误数值和 debug 文件重新污染论文。 |
| 2 | PI-02 | 延迟本底 selected-rate 高统计收敛 | 立即做 | 当前延迟率只来自 30 个选后事例，是最弱的定量环节。 |
| 3 | PI-03 | source normalization 完整审计 | 立即做 | 所有 rate、effective area 和 flux claim 都依赖源归一化。 |
| 4 | PI-04 | Geant4/MEGAlib 配置权威表 | 立即做 | NIM A 审稿会看可复现性，不能靠记忆写版本和 physics list。 |
| 5 | PI-05 | 最终图件与数据管线重建 | 立即做/值得做 | 当前图更像工程诊断图，投稿图需要可追溯数据和更清晰呈现。 |
| 6 | PI-06 | selected delayed background 分解 | 值得做 | 解释延迟本底由哪些核素/材料/粒子贡献，强化活化故事。 |
| 7 | PI-07 | likelihood 与 nuisance 参数灵敏度 | 值得做 | 最终 sensitivity claim 需要它，但当前 diagnostic rate 论文可先不做。 |
| 8 | PI-08 | 代表性轨迹、可见性、slant-column 和 duty cycle | 值得做 | 若要把阈值解释成任务性能，就必须加。 |
| 9 | PI-09 | 整机/透镜支撑 prompt background 边界 | 条件性做 | 对 flight-background claim 必须；对当前 proxy 论文可明确 scoped out。 |
| 10 | PI-10 | 多命中 reconstruction 验证 | 条件性做/值得做 | 若要把 topology 作为最终重建方法，就需要 Revan/Mimrec 或等价验证。 |
| 11 | PI-11 | detector-response envelope scan | 条件性做 | 做参数包络值得；完整 TES/CsI 电子学引擎当前不值得。 |
| 12 | PI-12 | broad-line / centroid-offset cases | 条件性做 | 对天体物理解读有用；若 headline 只是不分辨线，则不是硬需求。 |
| 13 | PI-13 | prompt/delayed spectra 与 cut-flow 诊断 | 值得做 | 能解释本底形状和选择流程，提升图表说服力。 |
| 14 | PI-14 | CsI 替代屏蔽材料 trade study | 现在不值得做 | 会重开设计优化问题，更像另一篇设计研究。 |
| 15 | PI-15 | diffuse sky / foreground model | 现在不值得做 | 属于天体观测 forecast，不是当前仪器本底 estimate。 |
| 16 | PI-16 | 全 CAD 探测器/低温系统与服务结构模型 | 现在不值得做/条件性做 | 对飞行设计 claim 有用，但当前工程设计未必稳定。 |
| 17 | PI-17 | veto/threshold/line-window 等参数扫描 | 值得做 | 检验结果是否依赖某个单点参数，但应排在核心收敛之后。 |
| 18 | PI-18 | 活化历史和核数据校验 | 值得做 | 支撑 delayed activation 的物理可信度，应和 PI-02/PI-06 结合。 |
| 19 | PI-19 | 可复现归档包 | 值得做 | 投稿前必须有代码、几何、源定义、脚本、校验和的归档计划。 |

## 详细清单

### PI-01：证据溯源 manifest 与旧文件隔离

判断：立即做。

要补什么：
- 为论文中仍在使用的所有关键数值建立当前 evidence manifest。
- 把 upstream Ge-proxy delayed evidence 从 `old/` 中提升为当前论文证据，或建立一个当前 manifest 指向旧路径，并明确旧文件中的旧 upper limit 已过时。
- 标记废弃的 manuscript-support tables、旧 workflow tables、旧 debug 文件，避免后续又被 `\input` 回正文。
- 区分当前英文论文材料、中文内部稿、生成 PDF、图件源表、废弃支持材料。

为什么重要：
- N2 的 upstream Ge-proxy 结果已经在论文中修正为 `6.38e-5 cps` 和 `0.16%`，但原始证据还在 `old/`，且旧 JSON 里有错误的旧值。
- 这是最容易导致论文回归的地方。

闭环产物：
- `paper_evidence_manifest_20260623.md/json`
- `deprecated_manifest.md`

我的考虑：
- 这是最低成本、最高确定性的修复。先做它，比先重跑模拟更理性。

### PI-02：延迟本底 selected-rate 高统计收敛

判断：立即做。

要补什么：
- 用更高 delayed-decay 统计量重跑 delayed replay。
- 用多个 production-position sampling，必要时多个 seed。
- 报告 selected event count、selected rate、统计误差、weighted variance、不同 sampling 间方差。
- 明确区分 source inventory/serialization 审计和 selected-rate convergence。

为什么重要：
- 当前 delayed component 是 `2.6(5)e-3 cps`，统计尺度来自 30 个选后延迟事例。
- 这可以作为当前论文里的谨慎诊断值，但不能支撑最终 activation-background claim。

闭环产物：
- `delayed_selected_rate_convergence.md`
- `delayed_selected_rate_convergence.json`
- 可选 `delayed_selected_rate_convergence.csv`

我的考虑：
- 这是最重要的物理闭环。即使论文保持当前窄 scope，也值得做，因为 production-position delayed source 是本文最有方法学价值的部分。

### PI-03：source normalization 完整审计

判断：立即做。

要补什么：
- 写清 prompt atmospheric source、delayed activity source、focused point-source photon flux 的单位和权重推导。
- 定义 source-plane area、projected area、solid angle、particle-family exposure 的约定。
- 保存或摘要 EXPACS/PARMA 输入和 MEGAlib source card 转换。
- 给出解析检查，证明每个粒子族的权重和 exposure 闭合。

为什么重要：
- 论文已经修正 photon flux 单位和 selected effective area，但项目里还需要一个唯一权威文档说明 source card 如何变成 rate。
- 审稿人如果质疑归一化，这个文件就是答复基础。

闭环产物：
- `source_normalization_audit.md`
- `source_normalization_audit.json`
- source-card manifest，包括路径、hash、source area、flux、generated primaries、exposure。

我的考虑：
- 很值得做。它基本不需要新模拟，但保护所有主结果。

### PI-04：Geant4/MEGAlib 配置权威表

判断：立即做。

要补什么：
- 收集真实运行环境中的 Geant4、MEGAlib/Cosima、ROOT、编译器、physics list、production cuts、decay data、radioactive-decay settings、自定义 hook/patch、seed policy。
- 缺失项标为 `UNKNOWN`，不能凭记忆编。

为什么重要：
- NIM A 是仪器和方法期刊，可复现性是基本要求。
- 论文不能写不确定的软件版本或 physics list。

闭环产物：
- `simulation_config_authority.json`
- `simulation_config_table.md` 或 `simulation_config_table.tex`

我的考虑：
- 高价值、成本通常低。投稿前必须有。

### PI-05：最终图件与数据管线重建

判断：图件溯源立即做；完整视觉重画值得做。

要补什么：
- 每张图都要有 source data、生成脚本、命令、输出 hash。
- 修掉小字、低分辨率 raster label、过载多面板。
- 增加或重画：
  - `A_eff(E)` 或 selected-area response；
  - focal spot / encircled energy；
  - selected prompt/delayed spectra；
  - 更清晰的 cut-flow；
  - mission-time fold 图，区分 day-15 rate 和 time-folded counts。

为什么重要：
- Phase 1 删除了最糟糕的 toy/debug 图，但现在的图仍偏工程诊断图。
- NIM A 审稿人会非常依赖图表判断模拟链是否可信。

闭环产物：
- figure generation scripts；
- `figures_audit.md`；
- 更新后的 PNG/PDF/SVG 图件。

我的考虑：
- 投稿前值得做。它不一定改变 physics result，但会显著改善可信度。

### PI-06：selected delayed background 分解

判断：值得做。

要补什么：
- 将 selected delayed background 按 isotope、material/volume、production particle、decay mode、selected rate contribution 分解。
- 区分 source activity contribution 和 selected-rate contribution。
- 识别主导 selected delayed channels，并判断是否物理合理。

为什么重要：
- 当前论文说 delayed activation 有空间和材料结构，但还没展示哪些核素/材料真正进入 selected rate。
- 这会让 delayed source 方法从“一个数”变成“有物理解释的结果”。

闭环产物：
- `delayed_selected_decomposition.csv`
- `delayed_selected_decomposition.json`
- 可放入论文或补充材料的紧凑表/图。

我的考虑：
- 应在 PI-02 后做。它不是比收敛更急，但非常提升论文质量。

### PI-07：likelihood 与 nuisance 参数灵敏度

判断：最终 sensitivity claim 前值得做；当前 diagnostic selected-rate estimate 不强制。

要补什么：
- 用 spatial-spectral likelihood 或至少 energy-window likelihood 替代 headline `S/sqrt(B)`。
- 加入 prompt normalization、delayed normalization、energy scale/resolution、atmospheric transmission、selected effective area 等 nuisance 参数。
- 报告 median expected `3 sigma`/`5 sigma` threshold 和 upper limit。
- 如果声称 discovery/upper-limit performance，需要 toy MC 或 coverage check。

为什么重要：
- 当前 `S/sqrt(B)` 已经被论文标为 diagnostic。
- 仅 1% 背景归一化系统误差就可能显著降低 nominal significance。

闭环产物：
- likelihood code；
- `likelihood_sensitivity_report.md/json`；
- counting threshold 和 nuisance-profile threshold 对比图。

我的考虑：
- 科学上重要，但不是第一步。它依赖稳定的 background components 和系统误差定义，应在 PI-02、PI-03、PI-04 后做。

### PI-08：代表性轨迹、可见性、slant-column 和 duty cycle

判断：如果要写 mission-performance，值得做。

要补什么：
- 用代表性气球轨迹和目标坐标替代或补充当前 synthetic 20 d reference trajectory。
- 计算 source zenith angle、line-of-sight atmospheric column、transmission、可见性、on-source duty cycle。
- 当前 synthetic trajectory 可以保留为 controlled reference，但不能叫 flight forecast。

为什么重要：
- 当前阈值假设连续在源曝光和参考大气透过处理。
- 这对 reference calculation 可以，但不能直接解释成实际任务性能。

闭环产物：
- `trajectory_visibility_slant_column_report.md/json`
- time-series 表：altitude、lat/lon、target zenith angle、transmission、live exposure、source rate scale。

我的考虑：
- 如果目标是让 NIM A 审稿人相信这个数能映射到真实观测，应做。如果只保留 detector-coupled reference estimate，可排后。

### PI-09：整机/透镜支撑 prompt background 与 optics self-background 边界

判断：条件性做。若声称 flight-background，必须做；若当前只做 proxy paper，可以 formal scoped out。

要补什么：
- 加入 lens support、optical bench、gondola-near mass、electronics、pressure vessels、services 等会影响 prompt background 的质量。
- 区分 upstream hardware prompt self-background 和普通 detector/cryostat atmospheric prompt background。
- 若暂不建模，写清楚哪些质量被排除、为什么排除。

为什么重要：
- 当前结果不是 full-payload background closure。
- upstream Ge-proxy delayed 已有边界，但 upstream hardware prompt self-background 没进主预算。

闭环产物：
- full/partial payload geometry manifest；
- prompt self-background selected-rate budget；
- 或 `scope_boundary_full_payload_exclusions.md`。

我的考虑：
- 不建议当前立刻开做，除非你决定把论文 claim 扩成 flight performance。否则它会变成大型几何项目。

### PI-10：多命中 reconstruction 验证

判断：条件性做/值得做。

要补什么：
- 用 Revan/Mimrec 或独立实现交叉验证当前 multi-hit topology 选择。
- 报告 ARM/source-direction residual、multiplicity confusion matrix、selected-rate impact。
- 明确 single-site、valid reconstructed multi-site、unreconstructed retained events。

为什么重要：
- 论文已经不再把 unreconstructed retained events 叫 FoV passing，这是对的。
- 但当前 topology logic 还不是最终 reconstruction method。

闭环产物：
- `reconstruction_validation_report.md/json`
- confusion matrix；
- 严格多命中拒绝前后的 selected-rate 对比。

我的考虑：
- 如果想把 multi-hit selection 作为成熟重建方法，必须做。若只是 baseline detector-level cut，可以排后。

### PI-11：detector-response envelope scan

判断：条件性做。做 bounded envelope 值得；完整 detector-effects engine 现在不值得。

要补什么：
- 扫描 TES Gaussian width、non-Gaussian tail proxy、energy scale shift、pile-up/dead-time proxy。
- 扫描 CsI veto threshold、veto coincidence window、shield threshold efficiency 或 energy resolution。

为什么重要：
- 当前 detector response 是理想化 single Gaussian event-energy proxy。
- 审稿人会问 threshold 对真实响应变化是否脆弱。

闭环产物：
- `detector_response_envelope_scan.md/json`
- 参数范围与 selected signal/background/threshold 影响表。

我的考虑：
- 做 envelope，不要做完整电子学引擎。完整 TES/CsI 响应模拟是另一项大工程。

### PI-12：broad-line 与 centroid-offset cases

判断：条件性做。

要补什么：
- 跑几个代表性 intrinsic line width 和 centroid offset case。
- 至少比较 unresolved-line case 与 1-2 个天体物理上合理的 broader-line case。
- 若保留当前窄窗，应报告信号损失；若重新优化窗宽，应报告本底变化。

为什么重要：
- 当前主结果明确只针对 unresolved line。
- 实际 511 keV 源可能有线宽或中心偏移。

闭环产物：
- `source_line_profile_case_scan.md/json`
- line width、centroid offset、selected signal rate、background window rate、threshold 表。

我的考虑：
- 有用，但不是硬门槛。不要先跑大网格，等核心 unresolved-line 结果稳定后再做代表性 cases。

### PI-13：prompt/delayed spectra 与 cut-flow 诊断

判断：值得做。

要补什么：
- 生成 511 keV 附近 prompt、delayed、signal 的 selected/pre-selected spectra。
- 将 cut-flow 拆成 pre-veto、active-shield pass、topology pass、energy-window pass、final selected rate。
- 给 rates 和 fractions 加 MC uncertainty。

为什么重要：
- 审稿人需要看到 selected 511 keV window 是由 line、continuum leakage、activation lines 还是 veto/topology 行为主导。

闭环产物：
- `selected_spectra_and_cutflow_report.md/json`
- figure source tables；
- final plot scripts。

我的考虑：
- 值得做，且可能复用已有 event outputs，不一定需要新 full simulation。

### PI-14：CsI 替代屏蔽材料 trade study

判断：现在不值得做。

如果以后重开，要补什么：
- 在匹配几何、veto 假设、activation production、selected background 条件下比较 CsI 与替代主动屏蔽材料。

为什么重要：
- iodine activation 是真实工程信号。

闭环产物：
- `shield_material_trade_study.md/json`

我的考虑：
- 当前不要做。它会重开设计优化问题，容易变成另一篇设计研究。论文里保留一句 future work 即可。

### PI-15：diffuse sky / foreground model

判断：现在不值得做。

如果以后重开，要补什么：
- 加入 diffuse Galactic 511 keV emission、continuum foreground、cosmic diffuse gamma background、off-axis leakage。

为什么重要：
- 对真实 observation forecast 或 target-specific likelihood 是必要的。

闭环产物：
- `diffuse_foreground_model_report.md/json`

我的考虑：
- 当前仪器本底 estimate 不需要。除非论文改成天体观测 forecast，否则保持 scoped out。

### PI-16：全 CAD 探测器/低温系统与服务结构模型

判断：当前不值得做；若要 flight design claim，则条件性做。

如果以后重开，要补什么：
- 用 CAD-derived mass model 替代 proxy masses，包括 supports、harnesses、readout boxes、thermal straps、service penetrations、material inventories。

为什么重要：
- proxy geometry 限制了绝对 flight-background claim 的含义。

闭环产物：
- CAD-to-Geant4 geometry manifest；
- material/mass table；
- proxy 与 CAD selected rate 对比。

我的考虑：
- 当前阶段太大。只有工程设计稳定后，细化 CAD 才真正有意义。

### PI-17：veto、threshold、shielding、analysis window 参数扫描

判断：值得做，但优先级低于 PI-02 到 PI-06。

要补什么：
- 扫描 CsI threshold、veto window、line-window width、TES resolution proxy。
- 如不重开几何优化，可在当前几何内扫描 W sleeve/aperture 相关 analysis-sensitive 参数。
- 每个 case 报 selected signal、prompt background、delayed background、threshold。

为什么重要：
- 检验结果是否只在单一参数点成立。

闭环产物：
- `analysis_parameter_scan_report.md/json`
- robustness table。

我的考虑：
- 值得做，但不要把它变成新几何优化。先做核心统计和溯源闭环。

### PI-18：活化历史和核数据校验

判断：值得做，但应在 PI-02 之后。

要补什么：
- 检查 dominant activation channels、half-lives、decay signatures 是否和 selected delayed events 一致。
- 记录 nuclear data library、radioactive-decay settings。
- 比较 source inventory、transported delayed spectra、selected delayed channels。

为什么重要：
- 项目已经做了 NUBASE ground-state correction，但更强的 activation claim 需要从 isotope inventory 到 selected detector events 的验证链。

闭环产物：
- `activation_history_validation.md/json`
- dominant isotopes/materials/decay modes/selected contribution 表。

我的考虑：
- 值得做，但应和 PI-02、PI-06 绑定，不应孤立做成纯文档。

### PI-19：可复现归档包

判断：投稿前值得做。

要补什么：
- 建立 code、geometry、source definitions、run manifests、seeds、derived data、figure scripts、manuscript source 的 archive manifest。
- 区分哪些 raw Cosima/event outputs 太大，不能放论文归档，只能用命令、checksum、summary metadata 表示。
- 区分可公开共享材料和本机 scratch outputs。

为什么重要：
- 论文数据与软件可用性部分已经承诺会提供复现材料。
- 投稿前需要一个具体归档包方案。

闭环产物：
- `paper_reproducibility_archive_manifest.md/json`
- checksum list；
- public archive README。

我的考虑：
- 值得做。它不改变物理结论，但会显著降低审稿和复现风险。

## 我现在不建议投入的方向

| 方向 | 为什么现在不值得 | 替代处理 |
|---|---|---|
| 完整 TES/CsI 电子学响应模拟 | 范围太大，会变成 detector-characterization 项目。 | 做 PI-11 的 bounded response envelope。 |
| CsI 与替代屏蔽材料大优化 | 会重开仪器设计优化，不是当前论文主线。 | 在 discussion 保留 iodine activation 的 future-work 说明。 |
| diffuse sky / foreground 建模 | 属于天体观测 forecast，不是当前仪器本底 estimate。 | 继续 scoped out，等目标观测 likelihood 再加。 |
| 全 CAD 替换 proxy geometry | 工程设计未稳定时投入产出比低。 | 明确 proxy 边界；必要时只补缺失大质量组件。 |
| 大规模 broad-line/off-axis 网格 | 当前 headline 是 unresolved-line，不需要大网格。 | 如需科学解释，只跑少数代表性 cases。 |
| 新几何优化 | 用户没有重开几何设计；会破坏当前 closure 方向。 | 固定当前几何，优先验证和溯源。 |

## 推荐执行顺序

1. 先做不需要重跑模拟的闭环：PI-01、PI-03、PI-04、PI-19。
2. 再做核心物理统计闭环：PI-02，然后 PI-06 和 PI-18。
3. 同步提升论文证据呈现：PI-05 和 PI-13。
4. 结果稳定后再做鲁棒性和统计方法：PI-07、PI-11、PI-17。
5. 只有明确扩展 claim 时才做：PI-08、PI-09、PI-10、PI-12。
6. PI-14、PI-15、PI-16 当前保持 future work，不进入主线。

## 最小验收标准

- 论文使用的每个新数值，都必须有机器可读 provenance 和人工可读 audit note。
- 保留的旧输出必须标记 current、archived 或 stale；stale 文件不能直接作为论文权威来源。
- 当前 paper-facing `.tex/.md` 不应再出现内部/debug 语言。
- 新模拟输出不得覆盖现有 authority outputs；必须用新 run directory 和 manifest。
- 任何用于 rate claim 的运行都必须记录 source card path、geometry path、generated events、physical exposure/activity、selected events、selected rate、uncertainty method、code/config metadata。
- 如果 claim 从 reference selected-rate estimate 扩展到 flight performance，PI-07、PI-08、PI-09 必须先完成。
