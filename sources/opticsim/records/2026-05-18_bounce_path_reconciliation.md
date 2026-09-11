# 2026-05-18 通道反射路径核对工作记录

## 1. 工作目标

本次继续推进 opticsim 的主线：511 keV channel optics。

上一轮已经发现，当前 `channel_single_curved_demo` 只是一个诊断用的
single-curved geometry v0，不能直接升级成四环 wall-by-wall Geant4。原因是
简单把 `46 mm / 12 m` 当作单根通道弯曲角时，局部 grazing angle 会进入
毫弧度量级，远高于当前 W/Si 反射率表能维持高反射的角度范围。

所以这一步的目标不是继续调 detector，也不是强行做四环几何，而是把
“缺少真实 channel path / bounce model” 这个 blocker 变成可以查验的数据产物。

需要同时对比三件事：

1. 当前 effective model 的 bounce bookkeeping 只有 `1-3` 次。
2. 如果用当前校准的 W/Si grazing angle 承担四环配置里的总偏转，需要约
   `6-13` 次小角反射。
3. Shirazi/Bloser 同源 channel-optics 文献线索里出现过 `17-38` 次反射。

这里的 `17-38` 只作为 many-bounce 量级线索，不作为 511-CAM 的直接输入参数。

## 2. 新增脚本

新增脚本：

```text
analysis/reconcile_channel_bounce_path.py
```

脚本读取：

```text
config/cam511_channel_baseline.yaml
runs/channel_4ring_calibrated_v2/ring_theta_calibration.json
```

脚本输出：

```text
runs/channel_bounce_path_reconciliation/summary.json
runs/channel_bounce_path_reconciliation/channel_bounce_path_reconciliation.csv
runs/channel_bounce_path_reconciliation/channel_bounce_path_reconciliation.md
runs/channel_bounce_path_reconciliation/channel_bounce_path_reconciliation.png
```

## 3. 计算逻辑

脚本对四个 511-CAM ring 分别计算：

1. 从 `bending_angle_deg` 读取配置中的总弯曲角。
2. 从 `ring_theta_calibration.json` 读取当前 W/Si effective model 的校准
   grazing angle。
3. 用 `总偏转 = 2 * N * theta` 估算：如果由多次小角镜面反射累积总偏转，
   需要多少次反射。
4. 如果只把 `17-38` 次反射作为 many-bounce bracket，反推出每个 ring
   对应的局部 grazing angle 区间。
5. 用简化 parallel-wall 关系估算这个 bracket 对应的 half-gap 量级。

这一步是诊断桥接，不是最终 channel 几何模型。

## 4. 核心结果

结果来自：

```text
runs/channel_bounce_path_reconciliation/summary.json
```

关键数值：

```text
effective_model_bounce_range: 1-3
required_bounce_range_at_calibrated_theta: 6.3805-12.8741
literature_reflection_range: 17-38
theta_range_if_literature_reflections_rad: 2.526e-5 to 1.129e-4
half_gap_range_if_literature_reflections_um: 0.00698 to 0.15279
all_literature_theta_below_calibrated_theta: true
```

解释：

当前 `1-3` 次 bounce 的 effective bookkeeping 太浅，不能作为最终
wall-by-wall 几何的反射次数假设。按当前校准角承接四环总偏转已经需要
`6-13` 次反射；如果只用同源文献里的 `17-38` 次反射作为 bracket，则对应的
局部 grazing angle 还会更小，范围为 `2.526e-5` 到 `1.129e-4 rad`，低于当前
`~1.5e-4 rad` 的 effective 校准角量级。

这说明下一步真正缺的是原始 IDL / Shirazi channel path 模型，而不是 detector
tuning，也不是简单修改 single-curved demo 的参数。

## 5. 接入项目链路

本次更新了以下文件，使新诊断进入项目记录、审计和报告链路：

```text
README.md
docs/physics_assumptions.md
docs/literature_notes.md
docs/validation_matrix.md
analysis/run_project_audit.py
analysis/build_gpt_pro_review_packet.py
analysis/freeze_baseline.py
reports/build_progress_pdf.py
```

新增自动审计项：

```text
channel_bounce_path_reconciliation
```

## 6. 构建和审计过程

第一次跑完整审计时失败，原因是临时构建目录不存在：

```text
/tmp/opticsim-build is not a directory
```

这不是源码失败，而是 `/tmp` 下的 CMake build 目录被清掉了。

重新配置并构建：

```bash
cmake -S . -B /tmp/opticsim-build -DGeant4_DIR=/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03/lib/Geant4-10.2.3
cmake --build /tmp/opticsim-build
```

随后重新运行：

```bash
python3 analysis/run_project_audit.py --out reports/project_audit
```

最终审计结果：

```text
PASS
23 checks
duration_s: 69.321
```

## 7. 汇总 PDF 更新

已重新生成：

```text
reports/opticsim_progress_report.pdf
```

PDF 状态：

```text
Pages: 19
CreationDate: Mon May 18 15:10:20 2026 CST
File size: 1779777 bytes
```

已渲染查验：

```text
page 10: Channel Bounce/Path Reconciliation
page 19: GPT Pro audit status, 23 checks PASS
```

## 8. Review Packet 更新

已重新生成：

```text
reports/gpt_pro_review_packet.md
reports/gpt_pro_review_manifest.json
```

review packet 现在包含新的 bounce/path 诊断和更新后的文件哈希。

## 9. 当前结论和下一步

不要把当前 `channel_single_curved_demo` 直接升级成四环 wall-by-wall Geant4。

下一步应先恢复或重建真实的 Shirazi/IDL channel path 模型：

1. 明确 channel length、gap、curvature、ring radius 如何决定反射次数。
2. 验证真实路径里的局部 grazing angle 是否保持在 W/Si 表的高反射区。
3. 只有在路径模型自洽之后，再基于 `GammaChannelReflection` 和
   `ReflectivityTable` 构建四环 wall-by-wall Geant4。
