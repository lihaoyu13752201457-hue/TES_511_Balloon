# GPT Pro 审核请求：opticsim Laue optics / Channel optics 模拟链路

日期：2026-05-24
仓库：`/home/ubuntu/opticsim`

## 最新闭环 addendum

本审核包的主线已经由 `records/2026-05-24_optics_evidence_gap_closure/` 收口。请优先阅读：

- `records/2026-05-24_optics_evidence_gap_closure/final_summary.md`
- `records/2026-05-24_optics_evidence_gap_closure/laue/laue_vector_diagnostics_prod100k_group_residuals.md`
- `records/2026-05-24_optics_evidence_gap_closure/laue/laue_vector_diagnostics_prod100k_event_invariants.md`
- `records/2026-05-24_optics_evidence_gap_closure/channel/channel_wallbywall_roughness_sweep.md`
- `records/2026-05-24_optics_evidence_gap_closure/schema/channel_schema_separation.md`

最新边界：

- Laue 已从 smoke 升级到 100k Guan-style 生产级诊断，24467 个 diffracted events；per-ring/per-tile residual 已报告。
- `scattering_q_vector_* = |k|*(k_out-k_in)`；旧 `reciprocal_vector_*` 仅保留为兼容 alias；`lattice_G_nominal/perturbed_*` 单独输出。
- 非零 `q-G` 和 relative Bragg residual 是当前 virtual-crystallite 近似的系统误差诊断，不应被当作隐藏调参。
- Channel public wall-by-wall roughness sweep 已跑；transmissivity 约 `0.3773 -> 0.16705`，没有向 0.80 调参。
- calibrated detector handoff 与 public wall-by-wall reconstruction 已 schema 分离，双方都保持 `is_first_principles_80pct_closure=false`。
- `xraydb`/manual Parratt 只作为本地 backend cross-check；外部 IMD/DarpanX/CXRO/Henke provenance 仍 open。

## 0. 请 GPT Pro 重点回答的问题

请把下面内容当作一个第三方技术审核包，而不是让你补写论文。核心问题：

1. **物理上有没有明显问题？**
   - Laue lens 的 Bragg/Darwin/mosaic 处理、环半径、焦距、衍射方向、概率分支是否自洽？
   - Channel optics 的 W/Si multilayer 反射、open fraction、Si path absorption、many-bounce 几何、12 m 聚焦解释是否自洽？
   - 哪些结果只能称为 calibrated / scaffold，不能称为 first-principles 或 publication-grade？

2. **代码实现有没有明显问题？**
   - 是否有坐标定义、单位换算、概率归一化、边界触发、抽样分支、I/O schema 等 bug 风险？
   - Geant4 app-level process 的做法是否会产生重复触发、错误杀轨迹、错误 secondary 方向、错误 parent/track 语义？
   - Python wall-by-wall channel 的求交、反射、吸收、投影到焦平面是否有逻辑漏洞？

3. **代码实现是否偏离主线或主流方式？如果不是主流，逻辑是否自洽？**
   - Laue：当前使用 app-level `G4VDiscreteProcess` + 外部 Darwin table / online Darwin model，而不是修改 Geant4 EM category。这个路线是否合理？
   - Channel：当前没有把 30/150 nm 纳米层真实建成 Geant4 volume，而是使用 table-driven boundary/path model。这个选择是否物理和计算上合理？
   - Channel calibrated 80% handoff 与 public-geometry wall-by-wall reconstruction 并存，是否边界说清楚？有没有偷换 claim？

请特别找错。若结论是“可接受但有边界”，请明确边界；若结论是“物理/实现不成立”，请指出最小反例或最该先改的代码位置。

## 1. 外部参考文献和主源

### 1.1 511-CAM / Channel optics

1. Shirazi et al., **The 511-CAM Mission: A Pointed 511 keV Gamma-Ray Telescope with a Focal Plane Detector Made of Stacked TES Microcalorimeter Arrays**, arXiv:2206.14652.
   URL: https://arxiv.org/abs/2206.14652
   本项目用到的参数：12 m focal length；channeling optics 四环半径 2.25/3/3.75/4.5 cm；W/Si 30/150 nm multilayers；9 cm aperture；3.6 cm focused beam diameter；80% optics transmissivity；50.89 cm2 effective area；TES stack 390 eV FWHM/65% detector stack efficiency 等。

2. Shirazi, Bloser, Legere, McConnell, **Performance simulation of the soft gamma-ray concentrator**, JATIS 6(2), 024001, 2020. DOI 10.1117/1.JATIS.6.2.024001.
   OSTI page: https://www.osti.gov/biblio/1716823
   Accepted manuscript: https://www.osti.gov/servlets/purl/1716823
   本项目用到的主线：multilayer optical properties by IMD + IDL ray tracing + MEGAlib focal-plane detector simulation；channeling efficiency 形如 product of reflectance terms, Si absorption exponentials, open fraction, support/mount factor；parallel-beam path 中 reflection count 是 many-bounce 量级，文中给出 17-38 的 lineage clue。注意：这是 122 keV soft gamma concentrator lineage，不是 511-CAM 四环的直接参数。

3. Geant4 Physics Reference Manual, **G4XrayReflection**.
   URL: https://geant4.web.cern.ch/documentation/dev/prm_html/PhysicsReferenceManual/electromagnetic/gamma_incident/xrayreflection/G4XrayReflection.html
   相关点：Geant4 有 X-ray reflection process，但默认模型不是 511 keV W/Si multilayer channel 的完整解；官方文档也说明 multilayer 等 specific cases 可以替换为 user-provided models。该项目因此走 table-driven custom boundary/path model。

4. Mondal et al., **DarpanX: A Python Package for Modeling X-ray Reflectivity of Multilayer Mirrors**, arXiv:2101.02571.
   URL: https://arxiv.org/abs/2101.02571
   用途：作为独立 multilayer reflectivity software family 的参照；当前项目还没有用 DarpanX 生成独立 511 keV W/Si 表，只把它列为下一步 publication-grade provenance check。

5. CXRO/Henke optical constants and multilayer tools.
   URL: https://henke.lbl.gov/optical_constants/
   用途：光学常数和 multilayer reflectivity 的公共基准来源；当前项目用 xraydb/Chantler + manual Parratt 交叉核验，仍建议补 CXRO/IMD/DarpanX 独立导出表。

### 1.2 Laue optics

6. Barriere et al., **Experimental and theoretical study of diffraction properties of various crystals for the realization of a soft gamma-ray Laue lens**, arXiv:0907.0458 / J. Appl. Cryst. 2009.
   URL: https://arxiv.org/abs/0907.0458
   用途：Cu/Au/SiGe Laue crystal benchmark；项目的 Zachariasen/Darwin mosaic implementation 用其 Cu/Au tables 做邻近文献闭合，不是 Ge(111) 511 keV 直接实验闭合。

7. Kohnle, **A Gamma-Ray Lens for Nuclear Astrophysics**, PhD thesis, Universite Paul Sabatier, 1998.
   本地来源：`records/laue_external_sources/Diss_Kohnle_98.pdf`；出版/列表页缓存：`records/laue_external_sources/irap_max_publications.html`
   用途：Ge(111) APS endpoint check；项目用 200/500 keV Ge(111) endpoint 检查 Darwin mosaic implementation 的量级。

8. PyTTE 1.0 / Takagi-Taupin perfect-crystal check.
   PyPI: https://pypi.org/project/pyTTE/1.0/
   用途：独立 perfect-crystal Takagi-Taupin sanity check；项目只用它确认 perfect-crystal peak branch 高于 mosaic Darwin branch，不能替代 mosaic Ge(111) flight-like benchmark。

## 2. 本项目的模拟对象和 claim 边界

### 2.1 Laue optics 主线

目标：在 Geant4 中放置 480-550 keV 的五环 Ge(111) Laue lens，平行 gamma 源从上游打到 lens plane，符合 Bragg 条件的 photon 通过 Laue diffraction 聚焦到 8.3 m focal plane。

当前有两条 Laue 实现：

1. **01 Barhoum-style / table-driven baseline**
   - 主程序：`geant4_app/src/laue_multiring_table_demo.cc`
   - 几何：`data/laue/ge111_480_550keV_multiring_darwin_config.csv`
   - 概率表：`data/laue/Ge111_480_550keV_darwin_mosaic_table.csv`
   - 物理：外部 Zachariasen/Darwin mosaic table 给出 `p_abs / p_diff / p_trans`，Geant4 process 在晶体边界抽样三分支。

2. **02 Guan/Reiazi-style process/model split**
   - 主程序：`geant4_app/src/laue_multiring_darwin_guan_demo.cc`
   - 几何同 01。
   - 物理：`GuanDarwinDynamicalModel` 在线计算 Bragg mismatch、plane normal 和 Darwin-Hamilton mosaic probabilities；`GuanStyleLaueBraggProcess` 只作为 Geant4 step adapter。
   - 明确 non-claim：不是 Guan/Reiazi source-code port；不是 Geant4 toolkit EM-category patch；只是 app-level compiled process/model split。

### 2.2 Channel optics 主线

目标：模拟 511-CAM channeling optics：511 keV gamma 在弯曲 W/Si multilayer spacer 中以小 grazing angle 多次 total external reflection，最后在 12 m focal plane 聚焦。

当前有三层 Channel 实现/证据：

1. **Geant4 calibrated multibounce handoff scaffold**
   - 主程序：`geant4_app/src/channel_4ring_multibounce_demo.cc`
   - 几何：`data/channel/cam511_channel_rings.csv`
   - W/Si 表：`data/reflectivity/WSi_511keV_parratt_grid_dense.csv`
   - 作用：复现 511-CAM headline scale，写 `phase_space.csv` 和 per-bounce `optics_history.csv`，用于 detector handoff。
   - Claim 边界：parameterized path model，不是 full wall-by-wall IDL geometry reproduction。

2. **Python public-geometry wall-by-wall reconstruction**
   - 主程序：`analysis/run_channel_wallbywall_rebuild.py`
   - 核心：`external_baseline/channel_raytrace_py/wallbywall_channel.py`
   - 作用：按公开 30 nm W / 150 nm Si bilayer spacer 几何采样入口；W layer entry blocked；Si spacer 中逐墙求交；每次 wall hit 查 W/Si R/A/T 表；可选 Si path absorption；自然生成 bounce count 和 grazing angle。
   - Claim 边界：不使用 calibrated `n_bounce` 或 `theta_calibrated_rad`，但仍是 reconstruction，因为原始 511-CAM IDL/IMD source、路径模型和装配容差不可用。

3. **Reflectivity table provenance / cross-check**
   - 生成/模型：`external_baseline/channel_raytrace_py/parratt_reflectivity.py`
   - 表：`data/reflectivity/WSi_511keV_parratt_grid_dense.csv`
   - 做法：`xraydb.multilayer_reflectivity` 生成候选表；manual s-polarization Parratt recursion 独立重算，用 xraydb 只取材料 optical constants。
   - Claim 边界：这验证表生成算术和递推逻辑，但 optical constants 仍同源；publication-grade 仍需 IMD/DarpanX/CXRO/Henke 独立导出比较。

## 3. 关键配置和几何参数

### 3.1 Laue 五环

文件：`data/laue/ge111_480_550keV_multiring_darwin_config.csv`

| ring | energy keV | radius mm | tiles | material | hkl | tile mm | thickness mm |
|---:|---:|---:|---:|---|---|---:|---:|
| 0 | 480 | 65.644327 | 72 | Ge | 111 | 0.8 | 9.452263 |
| 1 | 500 | 63.018438 | 72 | Ge | 111 | 0.8 | 9.947306 |
| 2 | 511 | 61.661820 | 72 | Ge | 111 | 0.8 | 10.218801 |
| 3 | 530 | 59.451215 | 72 | Ge | 111 | 0.8 | 10.686285 |
| 4 | 550 | 57.289274 | 72 | Ge | 111 | 0.8 | 11.176250 |

焦距：8.3 m。半径由近似 `R = F tan(2 theta_B)` 检查。
主结果：`runs/geant4_laue_multiring_darwin/summary.json`

### 3.2 Channel 四环

文件：`data/channel/cam511_channel_rings.csv`

| ring | radius cm | bend deg | length cm | width cm | thickness mm | tiles | calibrated bounces | calibrated theta rad |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 2.25 | 0.11 | 2.1 | 1.0 | 7.5 | 14 | 1 | 1.56013e-4 |
| 1 | 3.00 | 0.14 | 2.7 | 1.0 | 7.5 | 19 | 2 | 1.51494e-4 |
| 2 | 3.75 | 0.18 | 3.5 | 1.0 | 7.5 | 24 | 2 | 1.51494e-4 |
| 3 | 4.50 | 0.22 | 4.6 | 1.0 | 7.5 | 28 | 3 | 1.51447e-4 |

焦距：12 m。W/Si multilayer：30 nm W + 150 nm Si；open fraction = 150 / 180 = 0.833333。
配置来源：`config/cam511_channel_baseline.yaml` 和 511-CAM paper Table 2。

## 4. 模拟原理摘要

### 4.1 Laue optics 原理

1. 入射 gamma 近似平行光，沿 `+z` 进入 lens plane。
2. 每个 Ge(111) ring 对应一个 design energy。Bragg 条件给出 `theta_B`，环半径满足 `R = F tan(2 theta_B)`。
3. Mosaic crystal 的微晶取向分布导致局部 `delta_theta = theta_local - theta_B`，进而改变 `p_diff / p_abs / p_trans`。
4. 01 baseline 从 Darwin/Zachariasen mosaic table 查表；02 Guan-style 在线计算同类概率。
5. Geant4 不改底层 EM physics，而是在 app-level `G4VDiscreteProcess` 上强制边界 process：到 Laue crystal 边界时抽样 `ABSORB / TRANSMIT / DIFFRACT`。
6. `DIFFRACT` branch 生成 secondary gamma，方向指向 8.3 m focal plane，并加 mosaic spread 对焦斑的影响。

### 4.2 Channel optics 原理

1. 入射 gamma 沿 `+z` 进入每个 channel segment 入口。
2. Photon 只有落入 150 nm Si spacer 才进入 channel；落入 30 nm W layer 或 support closed fraction 视为 entry blocked/leak。
3. 在弯曲 spacer 中逐墙求交；wall hit 的 local grazing angle 由几何自然产生。
4. 每次 wall hit 查 W/Si `R/A/T(E, theta)` 表，抽样 `BOUNCE / ABSORB / LEAK`。
5. 如果打开 Si path absorption，spacer 内每段路径按 `exp(-mu * path)` 抽样生存。
6. 存活的 `EXIT` photon 投影到 12 m focal plane，输出 `phase_space.csv`。
7. Geant4 calibrated multibounce line 用 per-ring calibrated theta/bounce 复现 80% headline；Python wall-by-wall line 用 public geometry 自然产生 bounce/grazing angle，因此用于物理压力测试。

## 5. 代码实现摘要和审查点

### 5.1 Laue table-driven Geant4 baseline

关键文件：

- `geant4_app/src/laue_multiring_table_demo.cc`
- `geant4_app/src/optics/LaueEfficiencyTable.cc`
- `external_baseline/laue_raytrace_py/build_mosaic_darwin_table.py`
- `external_baseline/laue_raytrace_py/mosaic_darwin.py`

关键代码点：

- `LoadRingConfig` 在 `laue_multiring_table_demo.cc:191` 读取五环配置，并检查 ring radius 与 Bragg radius。
- `MultiRingProcess::PostStepDoIt` 在 `laue_multiring_table_demo.cc:514` 只处理 primary gamma、geometry boundary、LaueCrystal volume。
- `thetaLocal = 0.5 * atan2(r, F-z)` 在 `laue_multiring_table_demo.cc:532`；`deltaTheta` 后查表。
- `LaueEfficiencyTable::FromCsv` 在 `LaueEfficiencyTable.cc:95`；`ValidateProbabilities` 在 `:55`；`Lookup` 在 `:156`，按 material/hkl/energy 和 delta-theta 插值或 clamp。
- `DIFFRACT` branch 在 `laue_multiring_table_demo.cc:551` 构造 focal target 并产生 secondary gamma。

GPT Pro 请重点审查：

- `thetaLocal = 0.5 * atan2(r, F-z)` 是否符合本几何下 Bragg angle / scattering angle 定义。
- `Lookup` 使用 nearest design energy + delta-theta 插值是否合理；clamp table edge 是否会隐藏 out-of-range physics。
- 以 secondary gamma 表示衍射后 photon 是否符合 Geant4 process 语义，是否会影响后续 detector handoff。

### 5.2 Guan-style Laue split

关键文件：

- `geant4_app/src/laue_multiring_darwin_guan_demo.cc`
- `analysis/compare_geant4_darwin_guan_vs_barhoum.py`

关键代码点：

- `OnlineDarwinMosaicProbabilities` 在 `laue_multiring_darwin_guan_demo.cc:190` 在线计算概率。
- `ReflectAcrossPlane` 在 `:224`。
- `GuanDarwinDynamicalModel::Evaluate` 在 `:618`，集中计算 focus point、plane normal、delta theta 和概率。
- `GuanStyleLaueBraggProcess::PostStepDoIt` 在 `:679` 调用 model 并抽样。
- Summary 明确写 `uses_external_efficiency_table_for_physics=false`。

数值闭合：

- `runs/geant4_laue_darwin_guan_process/barhoum_comparison_summary.json`
- 100k vs 100k：diffraction fraction delta = +0.00037；absorption delta = -0.00129；transmission delta = +0.00092；spot D90 delta = -0.001167 cm；max abs delta mean p_diff by ring = 0.000631。

GPT Pro 请重点审查：

- `ReflectAcrossPlane` 和 plane normal 定义是否确实对应 Laue diffraction plane，而不是镜面反射了错误平面。
- online Darwin-Hamilton mosaic formula 与 table-driven baseline 数值闭合是否足以说明代码未偏离主线。
- “不是 EM-category patch，只是 app-level process”是否会影响 claim。

### 5.3 Channel W/Si reflectivity table

关键文件：

- `external_baseline/channel_raytrace_py/parratt_reflectivity.py`
- `data/reflectivity/generate_wsi_parratt_table.py`
- `data/reflectivity/WSi_511keV_parratt_grid_dense.csv`

关键代码点：

- `compute_reflectivity_rows` 在 `parratt_reflectivity.py:90` 调用 `xraydb.multilayer_reflectivity` 生成 R。
- `_nonreflected_transmission` 在 `:81` 用 stack thickness / sin(theta) 估计未反射部分传输。
- `A = 1 - R - T`，并 clamp 到非负。
- `manual_parratt_reflectivity_s` 在 `:142` 独立 s-polarization Parratt recursion，不调用 `xraydb.multilayer_reflectivity`。

GPT Pro 请重点审查：

- `T = (1-R) * T_nonreflected` 与 `A = 1-R-T` 是否是当前 channel wall-hit 语义下合理的近似，还是把 multilayer stack transmission 和 channel leakage 混在一起。
- roughness、period count、total stack thickness、ambient/substrate 假设是否符合 511 keV W/Si channel photon 在 Si spacer 内看 W/Si wall 的问题。
- s-polarization Parratt check 是否足够，是否需要 polarization averaging 或 gamma-ray energy limit correction。

### 5.4 Python Channel wall-by-wall reconstruction

关键文件：

- `external_baseline/channel_raytrace_py/wallbywall_channel.py`
- `external_baseline/channel_raytrace_py/geometry.py`
- `analysis/run_channel_wallbywall_rebuild.py`

关键代码点：

- `simulate_wallbywall_channel` 在 `wallbywall_channel.py:86`。
- `_sample_entrance` 在 `:325`：按 ring area 采样；抽 W/Si period；只允许 150 nm Si spacer 进入。
- `_trace_one_event` 在 `:399`：主 loop 逐墙求交，抽样 R/A/T 和 Si path absorption。
- `_next_wall_hit` 在 `:628`：解二次方程找下一 wall hit。
- `_global_position_direction` 在 `:662`：从 local channel coordinate 转成 global x/y/z 和方向。
- `_write_phase_space` 在 `:739`。

主结果：

- `runs/channel_wallbywall_rebuild/summary.json`
- 20k primaries；survived 5804；T = 0.2902；Aeff = 18.4617 cm2；spot D90 = 1.0329 cm；survivor mean bounces = 19.6239；include Si path absorption = true。
- 无 Si path absorption 对照：`runs/channel_wallbywall_rebuild_no_si_abs_smoke/summary.json`，T = 0.5938；survivor mean bounces = 21.4015。

GPT Pro 请重点审查：

- `_global_position_direction` 的曲率定义、`r_mm = radius + (cos(theta)-1)/curvature`、`z_mm = sin(theta)/curvature` 是否符合弯曲 channel 的几何。
- `_next_wall_hit` 的二次方程是否正确表示 spacer 中 `q(s)` 与 inner/outer wall 交点。
- 反射后 `reflected_alpha = -theta_hit` 是否符合局部壁面坐标中的 specular reflection。
- Si path absorption 是否应按 `ds/cos(theta)` 还是有漏项；单位 `cm/mm` 是否正确。
- 入口 open fraction 和 support open fraction 是否重复或漏算。

### 5.5 Geant4 Channel calibrated multibounce handoff

关键文件：

- `geant4_app/src/channel_4ring_multibounce_demo.cc`
- `data/channel/cam511_channel_rings.csv`

关键代码点：

- `LoadRings` 在 `channel_4ring_multibounce_demo.cc:140`。
- `BounceCountForPolicy` 在 `:247`，`ThetaForPolicy` 在 `:256`。
- `ChannelRunState::SimulatePath` 在 `:301`。
- `focusDeflection = atan(radius/focalLength)` 在 `:343`，per-bounce direction 被逐步 deflect inward。
- 每 bounce 记录 `BOUNCE/ABSORB/LEAK`，final `EXIT` 投影到 12 m focal plane。
- `summary` 在 `:447` 明确写 model warning 和 theta/open/path absorption policy。

主结果：

- `runs/channel/geant4_4ring_multibounce_calibrated/summary.json`
- 100k primaries；T = 0.80075；Aeff = 50.9415 cm2；spot D90 = 3.61328 cm；policy = `ring_calibrated`, `already_in_target`, `none`。
- `per_ring_summary.csv`：四环 T 约 0.8005/0.8011/0.8033/0.7984。

诊断结果：

- `runs/channel/geant4_4ring_multibounce_paper_bend_openfraction/summary.json`
- 20k primaries；T = 0.5614；Aeff = 35.7147 cm2；policy = `paper_bend`, `paper_once`, no Si path absorption。
- `runs/channel/physics_confidence_audit/summary.json` 显示 headline fully first-principles = false；主因是 original IMD/IDL path and open-area accounting 未恢复。

GPT Pro 请重点审查：

- 这个 Geant4 multibounce scaffold 是否只是合理 handoff，不应被称为 wall-by-wall geometry。
- `ring_calibrated` theta/bounce 是否本质上在调参复现 80%；是否在 summary/records 中充分标注。
- `paper_bend` diagnostic 如何解释；是否说明了 80% 与 public physics gap 的来源。

## 6. 已有验证和数值证据

### 6.1 Laue

主 run：`runs/geant4_laue_multiring_darwin/summary.json`

- n = 100000
- n_rings = 5
- diffraction fraction = 0.24638
- absorption fraction = 0.35894
- transmission fraction = 0.39468
- spot D90 = 0.220582 cm
- focal length = 8300 mm

Confidence audit：`runs/laue_physics_confidence_audit/summary.json`

- Bragg geometry audit checked 360 tiles; `ok=true`。
- max abs theta geometry vs theta_B error ~ 7.14e-7 rad。
- Barriere benchmark: 6 cases, max abs diffraction efficiency error ~0.00893, max reflectivity error ~0.01581, `ok=true`。
- Kohnle Ge(111) endpoint check: endpoint max abs error ~0.01349, `ok=true`。
- PyTTE check included as perfect-crystal sanity check, not final Ge(111) mosaic validation。

### 6.2 Channel

Calibrated Geant4 handoff：`runs/channel/geant4_4ring_multibounce_calibrated/summary.json`

- n = 100000
- T = 0.80075
- Aeff = 50.9415 cm2
- spot D90 = 3.61328 cm
- reproduces 511-CAM headline scale but is explicitly calibrated/parameterized。

Public-geometry wall-by-wall：`runs/channel_wallbywall_rebuild/summary.json`

- n = 20000
- T = 0.2902 with Si path absorption
- Aeff = 18.4617 cm2
- spot D90 = 1.03293 cm
- survivor mean bounces = 19.6239
- mean grazing angle = 7.55e-5 rad

No-Si path absorption check：`runs/channel_wallbywall_rebuild_no_si_abs_smoke/summary.json`

- n = 5000
- T = 0.5938
- Aeff = 37.7759 cm2
- survivor mean bounces = 21.4015

Plan completion record：`records/2026-05-21_channel_optics_plan_completion.md`

- Public-geometry wall-by-wall truth generator: done for current stage。
- Geant4 channel optics handoff: done parameterized。
- IDL/IMD provenance recovery: open external provenance。
- Detector handoff: end-to-end smoke only, not detector physics closure。

## 7. 当前项目明确的 non-claims

1. 不声称 Channel 80% headline 已经 first-principles 闭合。
2. 不声称 Geant4 Channel line 已经是 full wall-by-wall IDL geometry。
3. 不声称拿到了 511-CAM original IDL / IMD source 或 exact assembly tolerances。
4. 不声称 Guan-style Laue 是 Guan/Reiazi source-code port 或 Geant4 toolkit EM-category patch。
5. 不声称 detector-only TES/BGO scaffold 是 final detector mass model。
6. 不把 public-geometry wall-by-wall 的 0.2902 / 0.5938 结果调参成 0.80；0.80 只在 calibrated handoff line 中复现。

## 8. 新增全局示意图

为了避免 WRL 尺度过大看不清，新增了 2D global schematics：

- `records/2026-05-24_optics_global_schematics/laue_optics_global_2d.png`
- `records/2026-05-24_optics_global_schematics/laue_optics_global_2d.svg`
- `records/2026-05-24_optics_global_schematics/channel_optics_global_2d.png`
- `records/2026-05-24_optics_global_schematics/channel_optics_global_2d.svg`
- 生成脚本：`records/2026-05-24_optics_global_schematics/build_optics_global_schematics.py`

这些图只用于全局 review：入口 ring geometry、source incidence、focusing path。侧视图故意压缩 z 轴、放大径向轴，不是 CAD/WRL 等比例替代。

## 9. 建议 GPT Pro 输出格式

请按下面结构回答：

1. **结论摘要**
   - Laue：物理/代码/主流性各给 High/Medium/Low confidence。
   - Channel：物理/代码/主流性各给 High/Medium/Low confidence。

2. **必须修正的问题**
   - 每条给出：问题、为什么是问题、影响、最小修复/验证方式、相关文件/行号。

3. **可以接受但必须保留边界的地方**
   - 例如 calibrated handoff、app-level process、Parratt/xraydb 同源问题。

4. **最值得补的三个验证**
   - 例如 independent IMD/DarpanX/CXRO table、Geant4 full wall-by-wall port、Laue Ge(111) 511 keV direct benchmark。

5. **是否偏离主流**
   - 对 Laue 和 Channel 分开说：如果偏离，是否有工程/物理理由；逻辑是否自洽。

## 10. 本地快速复查命令

```bash
# 看两套系统说明
sed -n '1,220p' systems/laue/README.md
sed -n '1,220p' systems/channel/README.md

# 看 stepwise review
sed -n '1,140p' records/stepwise_review_2026-05-22/01_laue_barhoum_baseline/implementation_manual.md
sed -n '1,140p' records/stepwise_review_2026-05-22/02_laue_darwin_guan_process/implementation_manual.md
sed -n '1,140p' records/stepwise_review_2026-05-22/03_channel_wallbywall/implementation_manual.md
sed -n '1,120p' records/stepwise_review_2026-05-22/05_review_checklist/review_checklist.md

# 看关键 summary
sed -n '1,120p' runs/geant4_laue_multiring_darwin/summary.json
sed -n '1,120p' runs/geant4_laue_darwin_guan_process/barhoum_comparison_summary.json
sed -n '1,120p' runs/channel/geant4_4ring_multibounce_calibrated/summary.json
sed -n '1,120p' runs/channel_wallbywall_rebuild/summary.json
sed -n '1,120p' runs/channel/physics_confidence_audit/summary.json

# 重新生成 2D schematic
python3 records/2026-05-24_optics_global_schematics/build_optics_global_schematics.py
```

## 11. 我们希望你特别警惕的潜在坑

1. **Channel open fraction / Si path absorption 可能重复或漏算。**
2. **W/Si reflectivity table 的 geometry meaning 可能与 photon-in-spacer wall hit 不完全一致。**
3. **Channel calibrated `theta_calibrated_rad` 可能是 benchmark tuning，不应解释成自然 wall geometry。**
4. **Python wall-by-wall 的 local curvature coordinate 若错，会影响所有 natural bounce/grazing angle 结论。**
5. **Laue diffracted direction 如果只是指向 focal target，可能 bypass 了更严格的 crystal-plane vector diffraction；需要判断这在 current scaffold 中是否可接受。**
6. **Laue table lookup 使用 nearest energy design row，可能不适合连续 spectrum；当前只用于 per-ring design energies。**
7. **Geant4 process 强制边界触发与 kill/secondary 方式是否可能影响后续 histories 或 secondary tracking。**

请以“找错/审稿人模式”回复，不要只总结。
