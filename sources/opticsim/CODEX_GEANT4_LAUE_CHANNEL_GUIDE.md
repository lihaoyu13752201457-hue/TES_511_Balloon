# Codex 开发指导：500-511 keV Laue 透镜与 Channel Optics 的 Geant4 模拟

> 目标：让 Codex 在一个可维护的仓库中实现两条线：
>
> 1. **Laue 透镜 Geant4 复现线**：参考 Barhoum 2022 的 Geant4 Laue diffraction advanced-example 思路，先做参数化 Laue focusing process，再逐步接入 Bragg/Laue 物理模型。
> 2. **Channel optics Geant4 迁移线**：先复现 511-CAM/Shirazi 的 IMD + IDL ray tracing + MEGAlib detector baseline，再把 channeling 写成 Geant4 的 gamma boundary process 或 fast simulation process。

本文件给 Codex 用，写代码时优先保证：**可测试、可对标、可逐步替换物理模型**。不要一上来做全功能大系统。

---

## 0. 总原则

### 0.1 不要把标准 Geant4 gamma EM 过程当成聚焦光学

标准 Geant4 gamma EM 过程可以做：

- photoelectric effect
- Compton scattering
- Rayleigh scattering
- pair production
- detector energy deposition
- shield / veto / background

但它不会自动生成：

- Laue lens 的 Bragg/Laue diffraction 聚焦
- W/Si 多层膜的高能 total external reflection / channeling
- bent multilayer channel 中的多次 specular reflection

所以必须新增光学过程：

```text
Laue:   custom diffraction / Bragg process
Channel: custom gamma boundary reflection / fast-simulation process
```

### 0.2 不要真实建 30 nm W + 150 nm Si 的每一层

对 channel optics，几何上不要建纳米层。正确做法是：

```text
Geant4 geometry: effective channel wall / channel segment
Physics model:  R(E, theta), A(E, theta), T(E, theta), open_fraction
Sampling:       boundary hit -> reflect / absorb / leak
```

真实纳米层普通输运既慢，也不会自动给出相干多层膜反射。

### 0.3 每一步都必须有 benchmark

每个模块必须有对应的最小验收指标。

```text
Laue toy:       diffracted / transmitted / absorbed 分开，焦点位置正确
Channel toy:    单次反射方向正确，多次 bounce survival 正确
511-CAM optics: 3.5-3.6 cm focal spot, ~80% transmissivity, A_eff ~50.89 cm^2
Detector:       511 keV line response, hit table, single/multihit statistics
```

---

## 1. 推荐仓库结构

```text
gamma-optics-geant4/
  CMakeLists.txt
  README.md
  docs/
    literature_notes.md
    validation_matrix.md
    physics_assumptions.md

  config/
    cam511_channel_baseline.yaml
    laue_toy_baseline.yaml
    detector_tes_bgo.yaml

  data/
    reflectivity/
      WSi_reflectivity_grid.csv
      IrSi_reflectivity_grid.csv
      README.md
    laue/
      laue_efficiency_grid.csv
      crystal_materials.yaml

  external_baseline/
    channel_raytrace_py/
      channel_raytrace.py
      geometry.py
      reflectivity_table.py
      run_cam511_baseline.py
      plot_focal_spot.py
    laue_raytrace_py/
      laue_raytrace.py
      bragg.py
      run_toy_lens.py

  geant4_app/
    include/
      DetectorConstruction.hh
      PhysicsList.hh
      PrimaryGeneratorAction.hh
      EventAction.hh
      SteppingAction.hh
      SensitiveDetector.hh

      optics/LaueLensProcess.hh
      optics/LaueLensProperties.hh
      optics/LaueLensGeometry.hh
      optics/CrystalEfficiencyTable.hh

      optics/GammaChannelReflection.hh
      optics/ChannelSurfaceRegistry.hh
      optics/ReflectivityTable.hh
      optics/ChannelOpticsGeometry.hh
      optics/OpticsHistoryRecorder.hh

    src/
      DetectorConstruction.cc
      PhysicsList.cc
      PrimaryGeneratorAction.cc
      EventAction.cc
      SteppingAction.cc
      SensitiveDetector.cc

      optics/LaueLensProcess.cc
      optics/LaueLensProperties.cc
      optics/LaueLensGeometry.cc
      optics/CrystalEfficiencyTable.cc

      optics/GammaChannelReflection.cc
      optics/ChannelSurfaceRegistry.cc
      optics/ReflectivityTable.cc
      optics/ChannelOpticsGeometry.cc
      optics/OpticsHistoryRecorder.cc

    main.cc

  analysis/
    read_hits.py
    summarize_optics_history.py
    plot_focal_spot.py
    plot_energy_spectrum.py
    compare_raytrace_vs_geant4.py

  tests/
    unit/
      test_reflectivity_table.py
      test_specular_reflection.py
      test_bragg_geometry.py
    integration/
      test_channel_two_wall.py
      test_laue_one_ring.py
      test_cam511_detector_only.py
```

---

## 2. 配置文件设计

### 2.1 `config/cam511_channel_baseline.yaml`

```yaml
system: cam511_channel_baseline
energy_keV: 511.0
focal_length_m: 12.0
lens_outer_diameter_cm: 9.0

rings:
  - id: 0
    radius_cm: 2.25
    bending_angle_deg: 0.11
    length_cm: 2.1
    width_cm: 1.0
    thickness_mm: 7.5
  - id: 1
    radius_cm: 3.00
    bending_angle_deg: 0.14
    length_cm: 2.7
    width_cm: 1.0
    thickness_mm: 7.5
  - id: 2
    radius_cm: 3.75
    bending_angle_deg: 0.18
    length_cm: 3.5
    width_cm: 1.0
    thickness_mm: 7.5
  - id: 3
    radius_cm: 4.50
    bending_angle_deg: 0.22
    length_cm: 4.6
    width_cm: 1.0
    thickness_mm: 7.5

multilayer:
  high_Z_material: W
  low_Z_material: Si
  high_Z_thickness_nm: 30.0
  low_Z_thickness_nm: 150.0
  total_stack_thickness_um: 5.4
  open_fraction: 0.8333333333   # 150 / (30 + 150), verify convention
  roughness_nm: 5.0             # placeholder; scan later

expected:
  focused_beam_diameter_cm: 3.6
  transmissivity: 0.80
  effective_area_cm2: 50.89
```

### 2.2 `config/laue_toy_baseline.yaml`

```yaml
system: laue_toy_baseline
energy_keV: 511.0
focal_length_m: 8.3
source:
  type: parallel
  direction: [0, 0, 1]

crystals:
  material: Ge
  hkl: [1, 1, 1]
  d_spacing_A: 3.266  # check value for selected plane
  thickness_mm: 2.0
  mosaic_spread_arcmin: 1.0

rings:
  - id: 0
    radius_cm: 10.0
    tile_radial_mm: 10.0
    tile_tangential_mm: 10.0
    n_tiles: 64
  - id: 1
    radius_cm: 15.0
    tile_radial_mm: 10.0
    tile_tangential_mm: 10.0
    n_tiles: 96

process:
  mode: parameterized_focus
  p_diffraction_table: data/laue/laue_efficiency_grid.csv
  p_absorption_mode: xcom_table
```

---

## 3. 数据结构

### 3.1 `primary` 表

每个入射 photon 一行。

```text
event_id
E_keV
x_mm, y_mm, z_mm
ux, uy, uz
weight
source_tag
```

### 3.2 `optics_history` 表

每次光学过程一行。

```text
event_id
track_id
optics_kind          # LAUE or CHANNEL
stage                # ENTRY, BOUNCE, DIFFRACT, ABSORB, LEAK, EXIT
ring_id
tile_id
surface_id
E_keV
x_mm, y_mm, z_mm
ux_in, uy_in, uz_in
ux_out, uy_out, uz_out
grazing_angle_rad
p_reflect
p_absorb
p_transmit
n_bounce
weight
```

### 3.3 `hits` 表

标准 detector hits。

```text
event_id
track_id
detector_kind        # TES_PIXEL, BGO, WINDOW, PASSIVE
layer_id
pixel_i
pixel_j
pixel_uid
x_mm, y_mm, z_mm
edep_keV
process_name
time_ns
```

### 3.4 `event_summary` 表

后处理聚合。

```text
event_id
total_tes_edep_keV
n_tes_pixel_hits
is_singlehit
is_multihit
bgo_edep_keV
bgo_veto
reco_energy_keV
weight
```

---

## 4. Laue 透镜实现路线

### 4.1 第一阶段：工程型 `LaueLensProcess`

目标是复现 Barhoum 2022 的 advanced-example 思路。

#### C++ 类

```cpp
class LaueLensProcess : public G4VDiscreteProcess {
public:
    LaueLensProcess(const G4String& name = "LaueLensProcess");

    G4double GetMeanFreePath(
        const G4Track& track,
        G4double previousStepSize,
        G4ForceCondition* condition) override;

    G4VParticleChange* PostStepDoIt(
        const G4Track& track,
        const G4Step& step) override;

private:
    LaueLensGeometry geometry_;
    CrystalEfficiencyTable efficiency_;
    OpticsHistoryRecorder* recorder_ = nullptr;
};
```

#### `GetMeanFreePath`

```cpp
G4double LaueLensProcess::GetMeanFreePath(
    const G4Track&, G4double, G4ForceCondition* condition) {
    *condition = StronglyForced;
    return DBL_MAX;
}
```

#### `PostStepDoIt` 逻辑

```cpp
G4VParticleChange* LaueLensProcess::PostStepDoIt(
    const G4Track& track, const G4Step& step) {

    aParticleChange.Initialize(track);

    if (track.GetDefinition() != G4Gamma::Gamma()) {
        return &aParticleChange;
    }

    const auto* material = track.GetMaterial();
    if (!HasLaueLensProperties(material)) {
        return &aParticleChange;
    }

    const auto E = track.GetKineticEnergy();
    const auto x = step.GetPostStepPoint()->GetPosition();
    const auto k = track.GetMomentumDirection();

    auto crystal = geometry_.FindCrystalOrRing(x);
    if (!crystal.valid) return &aParticleChange;

    auto probs = efficiency_.Evaluate(E, k, crystal);
    double u = G4UniformRand();

    if (u < probs.p_absorb) {
        aParticleChange.ProposeTrackStatus(fStopAndKill);
        RecordAbsorption(track, x, crystal, probs);
        return &aParticleChange;
    }

    if (u < probs.p_absorb + probs.p_diffraction) {
        G4ThreeVector newDir;
        if (crystal.mode == ParameterizedFocus) {
            newDir = (crystal.focusPoint - x).unit();
        } else {
            newDir = ComputeBraggDiffractedDirection(k, crystal);
        }
        aParticleChange.ProposeMomentumDirection(newDir);
        RecordDiffraction(track, x, k, newDir, crystal, probs);
        return &aParticleChange;
    }

    RecordTransmission(track, x, crystal, probs);
    return &aParticleChange;
}
```

### 4.2 第二阶段：接入真实 Bragg 物理

把 `CrystalEfficiencyTable::Evaluate()` 拆成三个层次：

```text
Level 0: constant p_diff / p_abs toy model
Level 1: Bragg-law + mosaic angular acceptance + absorption table
Level 2: XOP / Darwin / Zachariasen / G4BraggReflection benchmark table
```

不要在第一版中试图完整重写 dynamical diffraction。先让几何和数据结构跑通。

### 4.3 Laue 单元测试

#### `test_bragg_geometry.py`

测试：

- 给定 E 和 d-spacing，计算 lambda。
- 用 Bragg law 得到 theta_B。
- 用 F = r / tan(2 theta_B) 检查 ring radius 与 focal length。

#### `test_laue_one_ring`

Geant4 integration test：

- 一个 ring。
- 一个 parallel gamma beam。
- 开 `p_diffraction=1, p_absorb=0`。
- 所有 photon 应该打到 focal plane 附近。

通过标准：

```text
mean(focal_x, focal_y) within 1 mm of expected focus
RMS spot controlled by configured angular spread
transmitted/diffracted/absorbed counts sum to total primaries
```

---

## 5. Channel optics 实现路线

### 5.1 先复现 Python/IDL baseline

先写一个不依赖 Geant4 的 Python ray tracer。目标不是漂亮，而是和 511-CAM/Shirazi 的 IDL ray tracing 功能等价。

#### 文件

```text
external_baseline/channel_raytrace_py/
  geometry.py
  reflectivity_table.py
  channel_raytrace.py
  run_cam511_baseline.py
  plot_focal_spot.py
```

#### 核心函数

```python
def trace_photon(photon, channel_geometry, reflectivity_table, rng):
    history = []
    for bounce in range(MAX_BOUNCES):
        hit = channel_geometry.next_wall_intersection(photon)
        if hit is None:
            return Exit(photon, history)

        theta = grazing_angle(photon.direction, hit.normal)
        R, A, T = reflectivity_table.lookup(photon.energy_keV, theta, hit.surface_id)
        u = rng.random()

        if u < A:
            return Absorbed(hit, history)
        elif u < A + R:
            new_dir = specular_reflect(photon.direction, hit.normal)
            new_dir = apply_slope_error(new_dir, hit.surface.sigma_slope_rad, rng)
            photon = photon.with_position_direction(hit.position, new_dir)
            history.append(Bounce(hit, theta, R, A, T))
        else:
            return Leaked(hit, history)

    return MaxBounceExceeded(photon, history)
```

#### Python baseline 验收

使用 `cam511_channel_baseline.yaml`。

```text
N = 1e5 photons
E = 511 keV
input = parallel beam
output focal plane = z = 12 m
expected focal spot diameter = 3.5-3.6 cm
expected transmissivity ~0.8, if using paper's effective R/A/open-fraction table
```

注意：如果没有原始 IMD/IDL 表，先用一个可调的 `R_eff(theta)` toy model 调到 paper benchmark，再逐步替换成真实 multilayer 表。报告中要明确 toy/physics table 的区别。

### 5.2 生成 `ReflectivityTable`

CSV 格式：

```csv
stack_id,E_keV,theta_rad,R,A,T,open_fraction,sigma_slope_rad,sigma_rough_nm,source
WSi_30_150,511.0,1.0e-6,0.92,0.04,0.04,0.833333,0.0,5.0,imd_or_parratt
WSi_30_150,511.0,2.0e-6,0.91,0.05,0.04,0.833333,0.0,5.0,imd_or_parratt
```

约束：

```text
R >= 0, A >= 0, T >= 0
R + A + T = 1 within tolerance
最终生存概率可以另乘 open_fraction，也可以把 open_fraction 吸收到 R/A/T 中；二者只能选一种，不能重复乘。
```

### 5.3 Geant4 `GammaChannelReflection`

#### C++ 类

```cpp
class GammaChannelReflection : public G4VDiscreteProcess {
public:
    GammaChannelReflection(const G4String& name = "GammaChannelReflection");

    G4bool IsApplicable(const G4ParticleDefinition& p) override;

    G4double GetMeanFreePath(
        const G4Track& track,
        G4double previousStepSize,
        G4ForceCondition* condition) override;

    G4VParticleChange* PostStepDoIt(
        const G4Track& track,
        const G4Step& step) override;

private:
    ReflectivityTable table_;
    ChannelSurfaceRegistry surfaces_;
    OpticsHistoryRecorder* recorder_ = nullptr;
};
```

#### 关键逻辑

```cpp
G4double GammaChannelReflection::GetMeanFreePath(
    const G4Track&, G4double, G4ForceCondition* condition) {
    *condition = Forced;
    return DBL_MAX;
}
```

`PostStepDoIt` 只在几何边界做事：

```cpp
if (step.GetPostStepPoint()->GetStepStatus() != fGeomBoundary) {
    return &aParticleChange;
}
```

判断是否 channel surface：

```cpp
auto surface = surfaces_.Lookup(step);
if (!surface.valid || surface.kind != ChannelWall) {
    return &aParticleChange;
}
```

计算 grazing angle：

```cpp
G4ThreeVector k = track.GetMomentumDirection().unit();
G4ThreeVector n = surface.localNormal(step).unit();

// grazing angle = angle relative to surface plane, not normal
// If alpha is angle between ray and normal, theta_grazing = pi/2 - alpha.
double cos_alpha = std::abs(k.dot(n));
double theta_grazing = std::asin(std::clamp(cos_alpha, 0.0, 1.0));
```

specular reflection：

```cpp
G4ThreeVector k2 = k - 2.0 * k.dot(n) * n;
k2 = k2.unit();
```

抽样：

```cpp
auto params = table_.Lookup(E_keV, theta_grazing, surface.stackId);
double u = G4UniformRand();

if (u < params.A) {
    aParticleChange.ProposeTrackStatus(fStopAndKill);
    RecordAbsorb(...);
} else if (u < params.A + params.R) {
    auto k_out = ApplySlopeError(k2, params.sigmaSlopeRad);
    aParticleChange.ProposeMomentumDirection(k_out);
    RecordBounce(...);
} else {
    // Either let it transmit into material or mark it leaked and kill.
    // Choose one policy and document it.
    aParticleChange.ProposeTrackStatus(fStopAndKill);
    RecordLeak(...);
}
```

### 5.4 Step limiter

为了确保边界事件能被稳定捕捉，需要给 channel region 加 step limiter。

```cpp
class ChannelStepLimiter : public G4UserLimits {
  // max step smaller than channel wall spacing / curvature scale
};
```

在 geometry 中：

```cpp
logicChannel->SetUserLimits(new G4UserLimits(maxStep));
```

### 5.5 Channel 单元测试

#### `test_specular_reflection.py`

输入：

```text
k = normalized([1, 0, -1])
n = [0, 0, 1]
```

期望：

```text
k' = normalized([1, 0, 1])
|k'| = 1
angle_in = angle_out
```

#### `test_channel_two_wall`

Geant4 integration：

- 两个平行 wall。
- `R=1, A=0, T=0`。
- photon 以小 grazing angle 入射。
- 记录 bounce count。

通过标准：

```text
no absorption
no leakage
bounce count matches analytic estimate within tolerance
exit direction equals expected direction
```

#### `test_channel_absorb`

- 设置 `A=1`。
- 第一次碰壁 kill。
- `optics_history.stage == ABSORB`。

---

## 6. Detector-only benchmark

先做 511-CAM detector-only，不等 optics。

### 6.1 几何

```yaml
absorber:
  material: Bi
  n_layers: 8
  pixels_x: 20
  pixels_y: 20
  pixel_size_mm: [1.45, 1.45, 2.0]
  gap_mm: 0.0  # or actual gap if available

bgo:
  enabled: true
  side_thickness_cm: 2.0
  bottom_thickness_cm: 5.0
  threshold_keV: 70.0
  resolution_fwhm_keV: 10.0

tes:
  threshold_keV: 1.2
  pixel_resolution_fwhm_eV_at_511: 230.0
```

### 6.2 源

```text
511 keV concentrated radial beam
focal spot diameter 3.6 cm
or phase-space file from optics ray tracer
```

### 6.3 输出与后处理

- 聚合同一 `pixel_uid` 内的多个 raw hits。
- 生成 per-event pixel-hit table。
- 分 single-hit / multi-hit。
- 加 TES energy resolution。
- 加 BGO veto。

通过标准：

```text
511 keV peak exists
FWHM near 390 eV if using paper response assumptions
93% detected events in approximately 510.3-511.8 keV window, if same cuts/resolution
```

---

## 7. PhysicsList 注册

```cpp
void PhysicsList::ConstructProcess() {
    G4VModularPhysicsList::ConstructProcess();

    auto gamma = G4Gamma::Gamma();
    auto* pm = gamma->GetProcessManager();

    if (enableLaueProcess_) {
        pm->AddDiscreteProcess(new LaueLensProcess());
    }

    if (enableChannelReflection_) {
        pm->AddDiscreteProcess(new GammaChannelReflection());
    }
}
```

注意：

- 先不要同时打开 Laue 和 channel process，避免调试混乱。
- 每个 process 只响应自己的 volume/surface/material。
- 每个 process 必须记录为什么没有 action：不是 gamma、不是边界、不是 channel surface、没有 Laue 属性等。

---

## 8. Primary generator

支持两种模式：

### 8.1 Analytical source

```text
parallel beam
point source
near-field concentrated radial beam
```

### 8.2 Phase-space source

读取 CSV/HDF5：

```text
event_id,E_keV,x_mm,y_mm,z_mm,ux,uy,uz,weight
```

这是连接 Python/IDL ray tracer 和 detector-only Geant4 的主接口。

---

## 9. 输出文件格式

优先 HDF5，其次 ROOT。

```text
/output/primaries
/output/optics_history
/output/raw_hits
/output/pixel_hits
/output/event_summary
/output/run_metadata
```

`run_metadata` 必须记录：

```text
geant4_version
physics_list
config_file
reflectivity_table_sha256
random_seed
n_primaries
commit_hash
```

---

## 10. 开发顺序给 Codex

### Task 1: Python channel baseline

1. 读取 `cam511_channel_baseline.yaml`。
2. 实现 ring/channel geometry。
3. 实现 `ReflectivityTable`，先支持 constant R/A/T。
4. 实现 ray tracing。
5. 输出 focal-plane CSV。
6. 画 focal spot 和 throughput。

验收：

```bash
python external_baseline/channel_raytrace_py/run_cam511_baseline.py \
  --config config/cam511_channel_baseline.yaml \
  --n 100000 \
  --out runs/channel_baseline/
```

输出：

```text
runs/channel_baseline/focal_spot.png
runs/channel_baseline/phase_space.csv
runs/channel_baseline/summary.json
```

### Task 2: Geant4 detector-only

1. 建 TES 8 层 20x20 Bi 像素。
2. 建 BGO shield。
3. 读取 phase-space source。
4. 输出 hits 和 event summary。

验收：

```bash
./geant4_app --config config/detector_tes_bgo.yaml \
  --source runs/channel_baseline/phase_space.csv \
  --out runs/detector_only/
```

### Task 3: Laue toy process

1. 写 `LaueLensProcess`。
2. p_diffraction/p_absorb 先用 constant。
3. one-ring geometry。
4. 输出 optics_history。

验收：

```text
p_diff=1 -> photons focus
p_abs=1 -> photons killed
p_diff=0,p_abs=0 -> photons transmitted
```

### Task 4: Channel boundary process toy

1. 写 `GammaChannelReflection`。
2. two-wall geometry。
3. `R=1` 测反射；`A=1` 测吸收；`T=1` 测泄漏。

### Task 5: Full channel geometry

1. 建 4-ring channel geometry。
2. 接 reflectivity table。
3. 对比 Python ray tracer。

通过标准：

```text
focal spot diameter agreement within 10-20% initially
throughput agreement within 10-20% initially
then tighten after reflectivity table validated
```

### Task 6: Physical tables

1. 用 IMD/Parratt/DarpanX/xraylib/XCOM 生成 W/Si 表。
2. 保存 provenance。
3. 对比 122 keV、50-430 keV、511 keV 三个能段。

---

## 11. 常见坑

1. **grazing angle 定义错**：channel optics 用的是相对表面的 grazing angle，不是相对法线的 polar angle。
2. **重复乘 open fraction**：R/A/T 如果已经包含 open fraction，就不要后处理再乘。
3. **Geant4 边界没有触发**：检查 step status、surface registry、几何容差和 user limits。
4. **把 leaked photon 当 transmitted photon 打进 detector**：需要统一 policy。建议 optics 泄漏直接 kill 并记录 LEAK，除非明确模拟外部杂散光。
5. **权重和 accept/reject 混用**：要么全部 weighted photon，要么全部 accept/reject。混合时后处理容易错。
6. **把 Laue process 和 channel process 同时打开**：调试阶段禁止。
7. **用 30 keV 以下 optical constants 直接外推到 511 keV**：必须标记为 toy/placeholder。

---

## 12. 最小可交付成果

组会前最小成果：

```text
1. channel Python baseline focal spot plot
2. detector-only 511 keV hit/spectrum plot
3. Laue Geant4 one-ring toy focusing plot
4. channel Geant4 two-wall reflection toy plot
5. validation matrix table
```

中期成果：

```text
1. 4-ring channel Geant4 boundary process
2. optics_history HDF5
3. raytrace vs Geant4 focal spot comparison
4. reflectivity table provenance
5. Laue vs channel effective-area comparison
```

最终成果：

```text
1. 511-CAM channel optics + detector end-to-end simulation
2. Laue optics + detector comparison system
3. sensitivity / background / veto / multihit analysis
4. Chinese report + reproducible code package
```

---

## 13. 给 Codex 的实现纪律

- 每写一个 C++ class，同时写一个 Python 或 C++ test。
- 所有单位显式写入变量名：`E_keV`, `x_mm`, `theta_rad`。
- 所有随机抽样都接受 seed。
- 所有表格查值都支持边界检查，不能 silent extrapolate。
- 所有 physics placeholder 都必须在日志中打印：`WARNING: using toy reflectivity model`。
- 输出文件必须包含 metadata 和 config copy。
- 不要把几何、物理表、detector response 写死在 C++ 源码里。

