# EA draft — Mass_model_511 前半稿对齐清单（2026-07-11）

## 本轮边界

- 范围：摘要、引言、探测器/模拟框架、源构建、事例选择与任务时间折叠；后续恢复缺口不补写。
- 原则：仅替换旧模拟的数值、窗口定义和与当前模拟状态冲突的事实陈述；不把 Mass_model_511 写成与旧 fix5 等效。
- 用户已明确授权采用 Mass_model_511 作为 EA 稿的当前数值权威。

## 采用的权威输入

- Step05 W2 响应与 cut-flow：`stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1/step05_Mass_model_511_fullstat_v1_l1_response_summary.json`
- Step08 20 d 轨迹折叠：`stepwise_maintenance/step08_significance/outputs_Mass_model_511_fullstat_v1/step08_Mass_model_511_fullstat_v1_time_dependent_summary.json`
- 精确产生位置延迟源：`engineering/Mass_model_511_nearfield_migration_20260701/03_detector_transport/delayed/candidate_Mass_model_511/fullstat_v1/F1/delayed_source_exactpos_summary.json`
- 光学信号权威：`stepwise_maintenance/step04_opticsim/optics_aeff_authority_f10m_a1.json`

## 已对齐

- [x] 主线窗统一为 W2：`510.58--511.42 keV`（`511 ± 420 eV`）。旧的 `510.79--511.21 keV` 没有可直接替换的 Mass 闭环权威，故未保留。
- [x] 摘要、任务时间段、紧凑结果表和结论同步为：

| 指标 | 旧 EA/fix5 | Mass_model_511 |
| --- | ---: | ---: |
| 第 15 天选后本底 | `3.92e-2 cps` | `4.807e-2 cps` |
| 第 15 天选后信号（`F0=1e-4`） | `1.19e-3 cps` | `1.185e-3 cps` |
| 瞬发本底比例 | `93.4%` | `91.7%` |
| 20 d `Z` | `7.80` | `7.04` |
| 20 d `F3` | `3.85e-5` | `4.26e-5 ph cm^-2 s^-1` |

- [x] W2 cut-flow 已替换为当前 Mass event catalog 的逐事件权重二次和不确定度：prompt `153 → 71 → 65`，delayed `43 → 28 → 28`，signal `30305 → 30305 → 29687`。
- [x] 延迟源固定 day-15 总活度更新为 `141.8334 Bq`；入射族活度更新为 `n=133.6723 Bq`、`mu-=7.6327 Bq`、`p=0.4337 Bq`、`alpha=0.0825 Bq`。
- [x] 公共时间轴图、图注与正文更新为 prompt/delayed/signal `927.909/97.121/0.98661 s^-1`、`7,215,233` instances、`1275` mixed candidates、`L≈0.9990`。
- [x] 已将“多环 450--550 keV 光学本底一并输运”的旧陈述缩小为当前实际的 511-keV 单环信号响应；光学质量的 prompt/delayed 本底明确不在主要探测器本底预算内。
- [x] 已明确 Revan 数字是保留的旧几何交叉检查，尚未在 Mass_model_511 上重跑。
- [x] active EN/ZH 和 recovered compile-ready EN/ZH 的共享前半部分均已同步。

## 已有但不应静默并入本基准数值

- [x] P1 宽线/窗宽扫描已做，但它是选后 sideband 加解析卷积；正文目前只保留“宽线需重优化”的边界句。
- [x] P2 大气 511 keV 情景已做（3M mono-511）；Harris 常量情景会使 `F3=4.639e-5`，但尚未进入 Step08 时间演化基准，故没有替换 `4.262e-5` 的主结果。
- [x] P3 只给出北天/近天顶参考解释；没有当前 Mass 的银河中心低仰角直接输运，故不能把当前 `T=0.739` 结果写成银河中心可见性预测。

## 仍未完成／只能标记的项目

- [ ] Mass_model_511 的 Revan/Mimrec 全量重建交叉检查、ARM/阈值稳定性。
- [ ] 明确 Laue 晶片和支撑硬件的全统计 prompt/delayed 自本底；当前仅完成信号 EventList 到当前 Mass 探测器的重放。
- [ ] Mass 的 `mu-` 材料类别比例；旧稿的 `32%/29%/21%` 已不能沿用，正文已标成未重制。
- [ ] Mass 版延迟产生位置/材料分类附录图；当前 EA 仍有失配的附录引用标签，未在本轮补附录。
- [ ] 同统计量多 seed 的延迟选后率收敛；当前只有一个 full-stat `M=50000, seed=260613` 权威样本。
- [ ] 四轨迹点的 W2、activation 和 delayed 闭合；已完成的 multi-point 验证只覆盖 Mass 几何下 `e+ / n / gamma` 的 `480--550 keV` targeted prompt。
- [ ] 将当前 live-PARMA 粒子族源--响应真正接入 Step08 数值折叠；Step08 现仍由历史 scalar 实现驱动。
- [ ] 大气 511 keV 的高度/轨迹时间演化，及银河中心低仰角、可见性与指向损失输运。
- [ ] 空间--谱 profile likelihood、系统误差包络、TES pile-up/saturation 与最终 CAD/DR 响应。
- [ ] 论文结构恢复：中文稿缺 Results/Discussion，英文 Results 后有 recovery gap；本轮不补这些后续章节。

## 发布前复查

- [x] 已重新生成本轮受影响的公共时间轴图，并编译 active 与 recovered compile-ready 的 EN/ZH PDF；四份 PDF 均编译成功。
- [x] 已移除前半稿中指向缺失延迟附录、收敛小节和上游光学小节的失配交叉引用；相关 Mass 图和收敛工作仍列在未完成项中。
- [ ] 决定是否把 EA 数值同步回 README 指定的 NIM-A source-of-truth，避免两个稿本继续分叉。
