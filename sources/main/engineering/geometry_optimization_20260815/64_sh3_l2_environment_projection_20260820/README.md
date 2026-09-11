# SH3 的大气、LEO、月面与日–地 L2 源谱响应外推

状态：`PASS__SH3_FOUR_ENVIRONMENT_SOURCE_SPECTRUM_PROJECTION`。

## 本包回答什么

本包沿用 `PPT0821` 的方法，但把旧几何响应替换成当前 M05NEW 的
`SH3_OPTV3_60cm`：

1. 从 SH3 的 W2 末级 prompt 事件恢复原初粒子总动能；
2. 从 SH3 BUILDUP 的 `IA INIT` 与 `CC IP RP` 恢复每个活化母核态的原初能量分布；
3. 在 `粒子族 × 产生体积 × 母核 ZA × 激发能` 内，用目标环境/气球源谱比重加权；
4. 把重加权后的 prompt 与 day-15 delayed 率相加，形成同质量模型的源谱响应代理；
5. 对非大气环境，再移除 SH3 气球 20 天信号核中的平均 45° 大气衰减，估算 20 天、
   3σ 最小可分辨通量。

这里的计算对应 M05 论文流程中的“源环境 → prompt/activation/delayed → 共同响应 →
任务折叠”，但目标环境只重加权源谱，没有重跑输运。

## 当前 SH3 权威输入

- 几何：`SH3_OPTV3_60cm`；
- W2：`510.58–511.42 keV`；
- 信号有效面积：`15.08544 cm2`；
- SH3 气球 20 天、3σ Gaussian：`2.229369e-5 ph cm-2 s-1`；
- SH3 末级事件：12 个 prompt、111 个 delayed；
- 气球 day-15 直接无偶然符合 W2 率：prompt `0.0057940144 cps`、delayed
  `0.0036246664 cps`。

这些值来自：

- `core_md/balloon511_ea_latex_drafts/M05NEW/`；
- `DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/`；
- `DEEPSEEK_CODE/outputs/05_mature_timeline_m05_fixed_20260820/`；
- `engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820/`。

## L2 口径

详见 [`L2_SOURCE_CONTRACT.md`](L2_SOURCE_CONTRACT.md)。简要说：L2 是近 1 AU 深空
静态代理，与 LEO 使用同一 COSI primary 母谱，但去除 `12.6 GV` 地磁传输并扩展至
`4π`；gamma 只保留 full-sky cosmic-photon 连续谱。没有把 Earth albedo、独立大气
511、LEO secondary、SAA 搬到 L2，也没有把 SEP 混进静态均值。

固定模型支撑域上的 L2 角域积分通量为：gamma `1.8397`、p `2.7959`、alpha
`0.4580`、e- `0.0470`、e+ `0.00445 cm-2 s-1`。这些积分只覆盖
`L2_SOURCE_CONTRACT.md` 声明的实际节点范围，不是全能区外推。

## SH3 外推结果

以当前 SH3 气球 `F3 = (2.229 ± 0.209)e-5 ph cm-2 s-1` 为基准，四环境中心值为：

| 环境 | day-15 本底比 | 含信号透过的相对 F3 | 20 天、3σ F3 [ph cm-2 s-1] |
|---|---:|---:|---:|
| 38 km 气球 | 1.000 | 1.000 | `2.229e-5` |
| 530 km LEO proxy | 0.551 | 0.480 | `1.070e-5` |
| 月面 proxy | 23.370 | 3.126 | `6.970e-5` |
| 日–地 L2 静态 proxy | 6.802 | 1.687 | `(3.760 ± 0.788_cond.MC)e-5` |

L2 的 projected rate 为 `0.06407 cps`；`99.58%` 是 delayed，其中 `96.37%`
来自 proton activation。前 5 个 delayed 末级事件、也就是前 2 个活化键，贡献
`90.75%` 的 L2 delayed 中心值；有限响应样本的加权有效事件数只有 `5.70`。因此
`1.69×` 应按数量级中心估计使用，`±0.79e-5` 只是保留响应样本的条件统计误差，
不含 L2 源模型、重离子、SEP、方向分布或匹配输运系统误差。

85 条 activation RP 中有 6 条低于保留的 L2 e-/e+ 曲线支撑；数值代理把这些项记为
coverage gap/0，而不是宣称该能区物理通量为零。它们对当前 W2 中心值可以忽略，
但完整 L2 输运前仍应补齐低能电子与正电子模型。

## 输出

- `outputs/tables/l2_source_spectra.csv`：L2 五个连续入射分量；
- `outputs/tables/sh3_prompt_w2_primary_energy.csv`：12 个 SH3 prompt 末级事件；
- `outputs/tables/sh3_activation_key_energy_response.csv`：SH3 活化键的原初能区和环境比；
- `outputs/tables/sh3_projected_background_components.csv`：四环境、stream、family 率；
- `outputs/tables/sh3_projected_delayed_event_contributions.csv`：逐 delayed 事件的环境外推贡献；
- `outputs/tables/sh3_environment_performance_estimates.csv`：最终性能代理；
- `outputs/tables/sh3_response_weighted_primary_energy_bands.csv`：PPT 阴影能区；
- `outputs/figures/`：三张 PPT 替换图；
- `outputs/summary.json`：机器可读结论与边界；
- `PPT0821/ppt_SH3_L2_20260821.pptx`：保留原 5 页简约结构的更新版。

## 复现

首次运行需要一次语义扫描；不计算 SIM 哈希：

```bash
python3 engineering/geometry_optimization_20260815/64_sh3_l2_environment_projection_20260820/code/scan_sh3_activation_primary_energy.py --workers 6
python3 engineering/geometry_optimization_20260815/64_sh3_l2_environment_projection_20260820/code/build_sh3_environment_projection.py
python3 engineering/geometry_optimization_20260815/64_sh3_l2_environment_projection_20260820/code/build_ppt0821_sh3_l2.py
```

## 权威边界

本包是 SH3 事件响应上的源谱外推，不是 LEO、月面或 L2 的匹配输运。尤其未覆盖：

- L2 的 SEP 与 `Z>2` GCR 重离子活化；
- LEO 的 SAA 驻留、停机策略及出 SAA 后延迟本底；
- 月面地点/地质/平台材料变化；
- 目标环境改变后的全能段占用率与偶然符合；
- 各环境真实姿态、方向源与任务时间线。

因此这些数值适合判断数量级和下一步优先级，不恢复任何历史 factor-1000 结果，也不
构成几何晋级权威。
