# 论文主题与最终版本

**题名**：Monte Carlo simulation of background and 511-keV point-source sensitivity for a balloon-borne Laue-lens TES telescope.

研究链：Laue 聚焦光子 → Geant4/MEGAlib 输运 → 瞬发粒子与活化衰变 → TES 响应 → 反符合与 Compton 选择 → 共同时间轴 → 任务期本底积分和顶层大气点源灵敏度。

正文比较 mass model A（SG3B 参考构型）和 mass model B（SH3 OptV3 侧向 chimney 构型），利用选中活化事件的材料、部件、母核素来源来解释结构优化的效果。

本备份的最终版本是 `balloon511_ea_manuscript_en_20260831.tex`，采用固定 **27° 仰角** 的任务期折叠。`tmp/m05_issue9_fixed27_20260831/` 中的代码是最终任务性能和环境外推图表的入口。较早 45° 版本的结果属于上游中间状态，不能代替最终值。

最终稿报告：模型 B 的 day-15 本底约 1.07e-2 s^-1，20 d 条件下的 3σ 线通量阈值约 (3.09 ± 0.28)e-5 ph cm^-2 s^-1，模型 A/B 阈值比约 2.23。

本备份保存现有最终稿的科学口径，不进行结果订正。P70 的当前主链采用去线 gamma continuum，独立 atm511 分支关闭；完整大气 511 线闭合、有限统计和探测器响应仍应按原报告区分。2026-09-11 复核见 `sources/main/engineering/manuscript_gap_review_20260911/`。

`paper/history/` 中 2026-08-21 命名的前稿仅用于版本核对。`sources/` 内其他论文草稿、旧构型和历史代码用于溯源；`neutron_fen` 是后续低温响应研究，不能当作本论文已完成的探测器响应验证。
