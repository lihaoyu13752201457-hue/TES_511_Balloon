# Codex 下一步任务书：opticsim 从 scaffold 走向物理级 Geant4 模拟

> 目标：在不破坏现有 Python/Geant4 scaffold、IO contract、测试与报告体系的前提下，把当前“有效模型 / toy process”推进为可审稿的 physics-refinement 实现。优先完成 511-CAM channel optics 的 curved-wall / per-bounce Geant4 模拟；Laue 透镜作为并行验证线，从 constant-probability toy 过渡到效率表驱动；TES/BGO 从 scaffold 过渡到可审计质量模型和电子学响应。

> 2026-05-21 checkpoint：Channel optics 当前阶段已经完成
> `analysis/complete_channel_optics_plan.py` 所定义的可验证计划：
> public-geometry wall-by-wall Python truth generator、parameterized Geant4
> optics handoff、strict public-parameter pressure test、以及
> wall-by-wall `phase_space.csv` 驱动的 1k Geant4 detector-only smoke。仍不得
> 宣称 Geant4 channel 已经是 full wall-by-wall geometry；IDL/IMD provenance 和
> 独立 reflectivity 来源仍是开放项。HTML 汇报见
> `records/2026-05-21_channel_confidence_report.html`。
> 2026-05-21 independent closure：`analysis/build_channel_independent_closure.py`
> 已完成光学常数/反射率闭合，但无校正 public geometry 仍未推出 CAM511
> 80% headline；报告见 `records/2026-05-21_channel_independent_closure.html`。

---

## 0. 当前状态和不能破坏的东西

### 当前已有成果

- Python 4-ring channel optics calibrated baseline：transmissivity ≈ 0.79942，Aeff ≈ 50.8569 cm²，spot d90 ≈ 3.605 cm。
- W/Si Parratt cross-check：240 rows，manual recursion 与 xraydb multilayer table 当前一致，status PASS。
- Geant4 4-ring channel effective scaffold：transmissivity ≈ 0.79715，Aeff ≈ 50.7125 cm²，spot d90 ≈ 3.5941 cm。
- Geant4 Laue one-ring toy：2000 events，p_diff=1，contract PASS；但目前不是 dynamical diffraction。
- Python detector-only backend：39930 selected line-window events，FWHM ≈ 392.07 eV。
- Geant4 detector-only scaffold：1000 events，6256 raw hits，TES detection fraction ≈ 0.771；但还不是 validated flight TES/BGO mass model。
- 审计：Python tests 23 OK，CMake build OK，IO contract PASS，project audit PASS。

### 不允许破坏的接口

必须保留并继续验证以下 contract tables：

```text
phase_space.csv
optics_history.csv
hits.csv
event_summary.csv
```

`phase_space.csv` 是 optics -> detector 的主接口；`optics_history.csv` 是 optics 物理过程验证的主接口；`hits.csv` 和 `event_summary.csv` 是 detector backend 与后处理的主接口。所有新增程序都必须写这些表，或者显式声明只写 optics-only subset。

### 不能过度声称

任何 README、report、summary 中都必须保留如下边界：

- 当前 4-ring channel Geant4 仍是 effective scaffold，除非已经完成 curved-wall / per-bounce geometry 并通过验收。
- 当前 Laue Geant4 是 constant probability toy，除非已经接入 energy-angle-material dependent diffraction table。
- 当前 W/Si 光学常数仍需独立来源 provenance，例如 IMD、DarpanX、CXRO/Henke 或手工 XOP/文献交叉检查。
- 当前 Geant4 detector-only 仍是 minimal geometry scaffold，除非完成 TES/BGO 质量模型、阈值、分辨率、veto、event reconstruction 的审计。

---

## 1. 总体优先级

### P0：冻结基线并确保可回归

先把现有 scaffold 固化成 regression baseline。任何新增物理都必须与当前基线做 A/B 对比。

### P1：Channel optics curved-wall / per-bounce Geant4

这是主线。当前最大技术缺口不是 throughput 数值，而是“G4 4-ring effective scaffold 还不是 wall-by-wall curved channel geometry”。下一步要把 `GammaChannelReflection` 放进真正的 boundary/per-bounce channel geometry。

### P2：独立 optical constants / reflectivity provenance

当前 W/Si Parratt arithmetic 已经自洽，但还没有 publication-level provenance。需要生成至少两个独立来源的 reflectivity grid，并量化差异。

### P3：Detector Geant4 mass model + electronics response

当 channel optics 能稳定给出 phase_space 后，升级 detector-only Geant4。目标不是只看 raw edep，而是完成 TES/BGO event reconstruction。

### P4：Laue dynamical diffraction table

Laue 线保留为第二套系统：从 toy process 过渡到 table-driven diffraction。它是老师关心的“500 keV G4 直接模拟”参考线，但不应阻塞 511-CAM channel 主线。

---

## 2. Sprint A：基线冻结和验收保护

### A1. 新增基线锁定脚本

新增：

```text
analysis/freeze_baseline.py
reports/baseline_manifest.json
reports/baseline_metrics.json
```

脚本行为：

1. 读取当前关键 summaries：
   - `runs/channel_4ring_calibrated_v2/summary.json`
   - `runs/geant4_channel_4ring_effective/summary.json`
   - `runs/geant4_laue_one_ring/summary.json`
   - `runs/geant4_detector_only_1k/summary.json`
   - `runs/wsi_parratt_crosscheck/summary.json`
2. 写出固定 metric snapshot。
3. 记录 git hash 或 file hash；若无 git，则记录所有关键文件 SHA256。
4. 输出 Markdown summary。

### A2. 新增 regression compare

新增：

```text
analysis/compare_to_baseline.py
```

比较字段：

```text
channel_python.transmissivity
channel_python.effective_area_cm2
channel_python.spot_d90_cm
geant4_channel.transmissivity
geant4_channel.effective_area_cm2
geant4_channel.spot_d90_cm
detector_python.measured_peak_fwhm_eV
detector_python.n_selected_line_window
wsi_crosscheck.max_abs_delta_R
```

建议容差：

```yaml
channel_python:
  transmissivity_abs: 0.01
  effective_area_cm2_abs: 1.0
  spot_d90_cm_abs: 0.10
geant4_channel_effective:
  transmissivity_abs: 0.02
  effective_area_cm2_abs: 2.0
  spot_d90_cm_abs: 0.20
detector_python:
  fwhm_eV_abs: 30.0
  n_selected_fraction_abs: 0.03
wsi_crosscheck:
  max_abs_delta_R_abs: 1e-12
```

### A3. 验收命令

```bash
python3 analysis/freeze_baseline.py --out reports/baseline
python3 analysis/compare_to_baseline.py --baseline reports/baseline/baseline_metrics.json --current reports/baseline/baseline_metrics.json
python3 -m unittest discover -s tests
cmake --build /tmp/opticsim-build
python3 analysis/run_project_audit.py --out reports/project_audit
```

---

## 3. Sprint B：Channel two-wall/per-bounce 物理核升级

### B1. 新增 table-driven R/A/T lookup

修改或新增：

```text
geant4_app/include/optics/ReflectivityTable.hh
geant4_app/src/optics/ReflectivityTable.cc
geant4_app/include/optics/GammaChannelReflection.hh
geant4_app/src/optics/GammaChannelReflection.cc
```

功能要求：

- 支持读取 CSV：

```text
E_keV, theta_rad, R, A, T, source, stack_id
```

- 支持固定 energy slice，例如 511 keV。
- 支持 nearest、linear interpolation 两种模式。
- 对每次 boundary hit 输出：

```text
source_event_id
track_id
boundary_index
ring_id
segment_id
surface_id
E_keV
theta_grazing_rad
R
A
T
u_before_x,u_before_y,u_before_z
u_after_x,u_after_y,u_after_z
x_mm,y_mm,z_mm
action  # REFLECT / ABSORB / LEAK / PASS
```

### B2. `GammaChannelReflection` 行为

伪代码：

```cpp
G4VParticleChange* GammaChannelReflection::PostStepDoIt(
    const G4Track& track, const G4Step& step) {
  if (!IsGamma(track)) return DoNothing();
  if (!IsGeomBoundary(step)) return DoNothing();
  if (!IsChannelSurface(step)) return DoNothing();

  auto normal = GetSurfaceNormal(step);
  auto kin = track.GetMomentumDirection();
  double theta = ComputeGrazingAngle(kin, normal);
  auto rat = table.Lookup(E_keV, theta);
  double u = rng.Uniform();

  if (u < rat.R) {
      auto kout = SpecularReflect(kin, normal);
      particleChange.ProposeMomentumDirection(kout);
      LogBoundary("REFLECT", theta, rat, ...);
  } else if (u < rat.R + rat.A) {
      particleChange.ProposeTrackStatus(fStopAndKill);
      LogBoundary("ABSORB", theta, rat, ...);
  } else {
      // leak / transmit: either let track pass or kill and record leak, depending on geometry mode
      LogBoundary("LEAK", theta, rat, ...);
      if (kill_leaked) particleChange.ProposeTrackStatus(fStopAndKill);
  }
  return &particleChange;
}
```

### B3. Two-wall validation

新增 executable：

```text
geant4_app/src/channel_two_wall_table_demo.cc
```

输入：

```bash
/tmp/opticsim-build/channel_two_wall_table_demo \
  --n 100000 \
  --energy-keV 511 \
  --theta-rad 1.5e-4 \
  --reflectivity-table data/reflectivity/WSi_511keV_parratt_grid.csv \
  --out runs/geant4_channel_two_wall_table \
  --seed 20260517
```

验收：

- R=1/A=0/T=0：每个设计应反射两次，reflect count 正确。
- R=0/A=1/T=0：第一次 boundary 后 absorb。
- R=0/A=0/T=1：第一次 boundary 后 leak。
- Table mode：统计 survival fraction 与 Python two-wall kernel 在 3 sigma 统计误差内一致。
- `optics_history.csv` 行数等于 boundary action 总数。

---

## 4. Sprint C：Channel curved-wall geometry

### C1. 不要真实建 30/150 nm 纳米层

几何上只建 effective channel wall / surface；物理上通过 R/A/T table 决定 boundary action。真实纳米层几何无法自动给出相干多层膜反射，且计算量和物理语义都不对。

### C2. 新增一根 curved channel demo

新增：

```text
geant4_app/src/channel_single_curved_demo.cc
geant4_app/include/geometry/CurvedChannelBuilder.hh
geant4_app/src/geometry/CurvedChannelBuilder.cc
```

几何要求：

- 支持以下参数：

```yaml
energy_keV: 511
channel:
  length_cm: 4.6
  width_cm: 1.0
  thickness_mm: 7.5
  bend_angle_deg: 0.22
  focal_length_m: 12.0
  n_expected_bounces: 1|2|3
  ring_radius_cm: 4.5
```

- 先允许用 segmented polyline surface 近似弯曲面，例如 32、64、128 segments。
- 每个 segment surface 带 `ChannelSurfaceInfo`：ring_id、segment_id、local curvature、surface normal。
- 输出每个 photon 的 boundary history。

### C3. 单根 curved channel 验收

- segment 数量从 32 到 128 时，输出焦点位置变化 < 5%。
- 固定 R=1 时，几何上可以完成预期反射次数并出射到近似焦点。
- 使用 table R/A/T 时，survival fraction 与 Python curved-kernel 匹配在 5% 内。
- grazing angle 分布的均值应接近当前 ring-calibrated theta 数量级，即约 1.5e-4 rad，但不应硬编码为固定值。

---

## 5. Sprint D：Geant4 4-ring wall-by-wall channel optics

### D1. 新增 full 4-ring executable

新增：

```text
geant4_app/src/channel_4ring_curved_demo.cc
```

输入参数来自：

```text
config/cam511_channel_baseline.yaml
```

需要支持：

- 4 个 ring：2.25、3.0、3.75、4.5 cm。
- 12 m focal length。
- W/Si 30/150 nm reflectivity table。
- per-ring length、bend angle、width、thickness、segment count。
- 输出 `phase_space.csv`、`optics_history.csv`、`per_ring_summary.csv/json`、`summary.json`。

### D2. 4-ring 验收标准

先用 current 511-CAM-like baseline 做 project-stage 验收：

```text
transmissivity: 0.80 ± 0.03
effective_area: 50.89 ± 2.0 cm²
spot_d90: 3.6 ± 0.25 cm
```

附加诊断：

```text
per-ring survival fraction
per-ring n_bounces distribution
grazing angle histogram
absorb/leak/reflect counts
focal plane x/y distribution
optics_history action fractions
```

### D3. 失败处理

如果出现 throughput = 0 或 d90 = 0 这类现象，不要调参掩盖。必须输出：

```text
first_boundary_position
first_boundary_normal
computed_grazing_angle
surface_id
pre/post momentum
```

并写入 `debug_boundary_events.csv` 前 100 个事件。

---

## 6. Sprint E：Optical constants provenance

### E1. 新增多来源反射率生成器

新增：

```text
data/reflectivity/generate_wsi_reflectivity_grid.py
analysis/compare_reflectivity_sources.py
docs/optical_constants_provenance.md
```

来源至少包括：

1. 当前 xraydb/Chantler 表。
2. 手工 Parratt recursion。
3. 一个独立外部来源的离线表，例如 IMD/DarpanX/CXRO/Henke 导出的 CSV。不要在脚本里依赖联网下载。

输出：

```text
data/reflectivity/WSi_511keV_xraydb.csv
data/reflectivity/WSi_511keV_imd_or_darpanx.csv
data/reflectivity/WSi_511keV_comparison.csv
runs/reflectivity_provenance/summary.json
runs/reflectivity_provenance/reflectivity_overlay.png
```

### E2. 验收

- 所有 reflectivity table 都有 source、date、method、layer model、roughness、density、citation fields。
- `R(theta)` 的 critical transition 区域有足够采样。
- 对 1e-4 到 3e-4 rad 区间做最大差异统计。
- 报告 table source 差异对 4-ring transmissivity/Aeff/d90 的影响。

---

## 7. Sprint F：Laue dynamical diffraction table

### F1. 从 constant p_diff 转为 table-driven

新增：

```text
data/laue/Ge111_511keV_diffraction_table.csv
geant4_app/include/optics/LaueEfficiencyTable.hh
geant4_app/src/optics/LaueEfficiencyTable.cc
```

Table schema：

```text
E_keV, theta_B_rad, delta_theta_rad, material, hkl, mosaic_fwhm_arcmin, thickness_mm, p_diff, p_abs, p_trans, source
```

### F2. 修改 Laue process

修改：

```text
geant4_app/src/laue_one_ring_demo.cc
```

或新增：

```text
geant4_app/src/laue_one_ring_table_demo.cc
```

行为：

- 根据 photon energy、crystal hkl、晶体法线与入射方向计算 Bragg mismatch。
- 查表得到 p_diff/p_abs/p_trans。
- 若 diffraction，按 Laue 几何把方向更新为指向 focal plane 的 diffracted direction，并叠加 mosaic spread / alignment error。
- 输出 optics_history。

### F3. 验收

- Bragg geometry unit tests：给定 E、d-spacing、ring radius、focus，计算 θB、tile orientation、diffracted direction。
- p_diff=1 table 时应复现旧 toy 结果。
- realistic table 时输出 throughput、bandpass、PSF、focal spot map。
- 不声称 publication-grade，除非效率表已与 XOP/Zachariasen/文献结果 benchmark。

---

## 8. Sprint G：Detector Geant4 mass model + response

### G1. 完善几何

在 `detector_only_demo` 基础上扩展：

```text
geant4_app/include/detector/TesBgoDetectorBuilder.hh
geant4_app/src/detector/TesBgoDetectorBuilder.cc
```

必须包括：

- 8 layers Bi。
- 每层 20x20 pixels。
- Pixel size 1.45 x 1.45 x 2 mm³。
- Pixel gaps。
- BGO shield：bottom 5 cm, side 2 cm，top aperture 匹配焦斑。
- Low-Z entrance window、tungsten collimator、electronics board、copper plane 作为可开关 passive material。

### G2. 电子学 / 后处理

新增：

```text
analysis/reconstruct_tes_bgo_events.py
analysis/plot_detector_validation.py
```

功能：

- raw hits 聚合为 pixel hits。
- per-pixel threshold 1.2 keV。
- BGO threshold 70 keV。
- BGO resolution 10 keV。
- TES per-pixel energy resolution 230 eV FWHM @ 511 keV。
- event summed energy。
- single-hit / multi-hit classification。
- line window 510.3-511.8 keV。
- optional edge-pixel cut。

### G3. Detector 验收

基准验收：

```text
FWHM around 511 keV: 390 ± 50 eV
line-window fraction: 0.93 ± 0.03, after comparable event selection
TES detection efficiency including gaps: 0.65 ± 0.08 relative to photons reaching active focal area
```

同时输出：

```text
singlehit_fraction
multihit_fraction
BGO veto fraction
layer occupancy
pixel occupancy heatmap
energy spectrum before/after BGO veto
energy spectrum before/after edge cut
```

---

## 9. Sprint H：End-to-end production runs

### H1. Channel end-to-end

命令模板：

```bash
/tmp/opticsim-build/channel_4ring_curved_demo \
  --config config/cam511_channel_baseline.yaml \
  --reflectivity-table data/reflectivity/WSi_511keV_best.csv \
  --n 1000000 \
  --out runs/channel_4ring_curved_1M \
  --seed 20260517

/tmp/opticsim-build/detector_only_demo \
  runs/channel_4ring_curved_1M/phase_space.csv \
  runs/g4_detector_channel_curved_1M \
  1000000 \
  20260517

python3 analysis/reconstruct_tes_bgo_events.py \
  --hits runs/g4_detector_channel_curved_1M/hits.csv \
  --event-summary runs/g4_detector_channel_curved_1M/event_summary.csv \
  --out runs/g4_detector_channel_curved_1M/reco
```

### H2. Laue end-to-end

命令模板：

```bash
/tmp/opticsim-build/laue_one_ring_table_demo \
  --config config/laue_toy_baseline.yaml \
  --efficiency-table data/laue/Ge111_511keV_diffraction_table.csv \
  --n 200000 \
  --out runs/laue_table_one_ring_200k \
  --seed 20260517
```

之后接同一个 detector pipeline。

---

## 10. 报告和审计输出

### 每个 sprint 必须更新

```text
docs/physics_assumptions.md
docs/validation_matrix.md
docs/optical_constants_provenance.md
reports/progress_report.pdf
reports/project_audit/audit_report.md
reports/gpt_pro_review_packet.md
```

### 每个 sprint 必须有 summary

每个 run directory 都要写：

```text
summary.json
run_config.yaml
file_hashes.json
stdout.log
stderr.log
```

### 最终审计命令

```bash
python3 -m unittest discover -s tests
cmake --build /tmp/opticsim-build
python3 analysis/run_project_audit.py --out reports/project_audit
python3 analysis/build_progress_pdf.py
python3 analysis/build_gpt_pro_review_packet.py
python3 analysis/compare_to_baseline.py --baseline reports/baseline/baseline_metrics.json --current reports/current_metrics.json
```

---

## 11. Definition of Done

### Project-stage Done

- Channel curved-wall G4 demo 可以生成非零 throughput，且几何诊断可信。
- `GammaChannelReflection` 使用 table-driven R/A/T，而不是常数 toy。
- 4-ring curved channel 输出 `phase_space.csv` 和 `optics_history.csv`，并接入 detector-only Geant4。
- Laue 至少有 table-driven one-ring demo，旧 p_diff=1 toy 仅作为 regression test。
- Detector 有 raw edep -> reconstructed event 的后处理，能重现 511-CAM 级别 FWHM 和 line-window fraction。
- 所有 claim boundaries 在 README/report 中清晰保留。

### Publication-prep Done

- Optical constants provenance 至少双来源交叉检查。
- Channel geometry 的 grazing angle / bounce history / focal spot 不再依赖 ring-calibrated fixed theta。
- Laue efficiency table 有文献或独立理论工具 benchmark。
- Detector mass model 中 passive material 和 BGO veto 经过 sensitivity study。
- End-to-end runs 有统计误差、系统误差、参数扫描和 reproducible hashes。

---

## 12. 立即执行的第一批 PR 建议

1. `baseline-freeze-and-regression`：添加 baseline freeze/compare 脚本。
2. `reflectivity-table-reader-g4`：为 `GammaChannelReflection` 增加 CSV table lookup。
3. `two-wall-table-demo`：新增 table-driven two-wall demo 与 Python kernel 对比。
4. `curved-channel-builder-v0`：实现 segmented curved wall geometry，先跑单根 channel。
5. `detector-reco-postprocess`：把 Geant4 raw hits 聚合成 TES/BGO event response。
6. `laue-table-process-v0`：把 Laue toy 改成 table-driven process，p_diff=1 表作为 regression。
