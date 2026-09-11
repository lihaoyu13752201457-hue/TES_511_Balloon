# S3d-O8 质量模型、活化点与 prompt 轨迹可视化

## 身份与朝向

本目录只使用 **S3d-O8** 几何，不使用 `Mass_model_511` 作为底图。几何权威是：

`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

M05 论文的坐标约定是 `InstrumentFrame.Rotation 0 45 0`，局部侧窗朝向天空的方向为 `-x′`。本图把 world `+Z` 明确定义为 sky/up，因此：

- sky-facing optical axis：`(-1/sqrt(2), 0, +1/sqrt(2))`，相对水平向上 45°；
- 入射 focused photon 传播方向：相反的 `(+1/sqrt(2), 0, -1/sqrt(2))`；
- world 到 InstrumentFrame：`x′=(X-Z)/sqrt(2)`, `y′=Y`, `z′=(X+Z)/sqrt(2)`。

二维图和 WRL 的默认侧视视角都采用上述朝向。事件表同时保留 world 与 InstrumentFrame 坐标，显示朝向没有改变事件数据。

## 主要产物

- `figures/s3d_o8_mass_model_activation_prompt_detail.png`：高分辨率二维总图。
- 同名 `.svg` / `.pdf`：矢量标签版本；几何面为栅格化原生网格，避免丢失 3096 个实体时产生超大矢量文件。
- `geometry/s3d_o8_mass_model_activation_prompt_tracks.wrl`：带材料颜色、66 个 delayed 点和三条 prompt 事件轨迹的最终 WRL；单位是 **mm**。
- `geometry/s3d_o8_native_geant4_full.wrl`：未经事件叠加的 Cosima/Geant4 原生 CSG tessellation。
- `data/geometry_volume_manifest.csv`：3096 行，一行对应一个 WRL SOLID；记录 exact material、母体、Copy 来源、CSG 标志、顶点/面数和 world/Instrument 边界。
- `data/geometry_mesh_products.npz`：压缩几何网格和完整坐标变换；可用 `allow_pickle=False` 读取。
- `figures/s3d_o8_nearfield_activation_detail.png` / `.svg` / `.pdf`：TES 近场 (y'=0) 真剖面、66 个三维活化点投影、prompt 路径与主要 host 排名。
- `figures/s3d_o8_edge_pixel_sensitivity.png` / `.svg` / `.pdf`：fixed-pixel radial gate 的 signal/background retention 与 20 天最小可分辨通量。
- `NEARFIELD_BACKGROUND_AND_EDGE_PIXEL_ANALYSIS.md`：近场来源表、边缘像素定量结论、证据分级与最小验证门。
- `DELAYED_TOP5_TES_CHAIN_AUDIT.md`：delayed 前五 source volumes 的 direct-production、DECA→ANNI→TES raw ancestry、空间耦合与 prompt 共通终端机制。

二维图四个 panel：

1. world X-Z 飞行侧视图：显示全部 3096 个非真空 placement，`+Z` 向上，并叠加全部 delayed 点和三条 prompt 事件。
2. `y′=0` 原生网格真剖面：直接对 Geant4 CSG tessellation 求交，保留开窗和 NF2 relief，不是手绘示意图。
3. detector-bay 放大图：仅为看清内部而移除最外层 BPE/plastic/BGO/Kapton/Al veto envelopes；这些外层仍完整保留在 panel 1、panel 2 和 WRL。
4. TES 横截面：六层 376-pixel Ta 图样在投影中重合；星号是 HTsim fixed pixel center，细点是 TES CC deposit，虚线圆以 `(y′,z′)=(0,-5.2 cm)` 为中心、半径 `1.35 cm`。

## Delayed activation 点

**FACT**：420 条 S3d-O8 delayed W2 事件对应 66 个唯一 sampled decay-source 坐标、49 个 `family×volume×ZA×state` key、15 个核素，总 W2 率为 `0.0544797522273 cps`。

15 个 parent isotopes：V-46、Fe-53、Co-54、Co-55、Ni-57、Cu-61、Cu-62、Cu-64、Zn-63、Sr-83、Y-85、Zr-85、Nb-89、Nb-90、Ag-106。

- `data/delayed_selected_event_ledger.csv`：420 行事件表；包括 W2 权重、核素、source volume、exact material、world/InstrumentFrame 坐标和 inventory-cell 上下文。
- `data/delayed_source_point_ledger.csv`：66 行绘图点表；包括点上事件数和 W2 rate。
- `data/delayed_partial_production_origin_links.csv`：25 行 exact-coordinate production ancestry link。

每个点的 `source_volume` 是产生/采样该活化核素的 S3d-O8 几何体，`exact_material` 来自该体的 `.Material`，不是名称前缀猜测。420 行 exact material 计数为 Copper 373、Nb 25、MuMetal 20、SilverSinterProxy 1、CuNi 1。

“由什么粒子激发”分两层记录：

- **FACT，420/420**：`incident_family` 是 activation inventory/lineage 携带的 incident-primary family 分支。
- **FACT，25/420**：`interacting_particle` 与 `creator_process` 是唯一坐标匹配的实际成核 projectile/channel。
- **UNKNOWN，395/420**：现有 production-origin scan 没有覆盖这些行；表中明确写成 `NOT_SCANNED_FAMILY` 或 `COMPONENT_FILTERED_OR_NOT_RETAINED`，没有用 incident family 代替真正 projectile。

点球半径仅用于可视化 W2 rate，不代表核素云或零件的物理尺寸。inventory-cell 字段是 cell total，复制到事件行仅供上下文，不能按 420 行再次求和。

## Prompt 路径

三条路径直接从各自原始 `.sim.gz` 事件块重建，而不是使用硬编码 ray summary：

| event | INIT energy | PAIR host | annihilation host | selection |
|---|---:|---|---|---|
| 3883 | 4148.29 keV | Nb inner magnetic shield | MuMetal outer magnetic shield | Step05 pass；frozen reject，r=1.40358 cm，L2 |
| 19932 | 5768.82 keV | DR mixing-chamber Cu | DR mixing-chamber Cu | frozen pass，r=1.09602 cm，L2 |
| 8081 | 6345.94 keV | Nb inner magnetic shield | L0 Cu substrate-support disk | Step05 reject；frozen reject，r=1.54158 cm，L5 |

三条事件的 active BGO 和 plastic raw deposit 都是 `0 keV`。

- `data/prompt_events.csv`：3 行事件级选择、能量、host、fixed-pixel centroid 和 selection level。
- `data/prompt_ia_nodes.csv`：86 个 IA 节点及 IA origin DAG。
- `data/prompt_cc_hits.csv`：285 个真实 energy-deposit 坐标。
- `data/prompt_htsim_hits.csv`：16 个 detector hit；type-2 TES 行记录 fixed pixel center。
- `data/prompt_ancestry_edges.csv`：547 条 IA/track/HTsim ancestry edges。
- `data/prompt_track_vertices.csv` / `prompt_track_segments.csv`：375 个顶点和 262 条绘图线段。

线段语义必须分开理解：

- `ia_chord` 是两个已记录 IA interaction vertex 之间的直线弦；
- `cc_deposit_polyline` 只连接同一 track 的离散 deposit 样本；
- 两者都不是完整的 Geant4 step/boundary history；每行 `is_complete_geant4_step_path=False`。

## 几何保真与验证

原生 WRL 由 Cosima/Geant4 `VRML2FILE` 在 **0 event transport** 条件下导出。它包含：

- 3096 个唯一非真空 SOLID，名称集合与权威 `.geo` 的 drawable placement 集合完全一致；
- 64,305 vertices、66,223 原始 polygons、116,526 triangles；
- 20 个 placed CSG；
- BPE、plastic、BGO、Kapton、outer-Al 各 3 个；
- 6 个 active-veto volumes、5 个窗口 CSG bands、7 个窗口 foils；
- 2256 个 Ta TES pixel copies 和 625 个 W placements。

审计文件：

- `audit/geometry_validation.json`：27/27 PASS。
- `delayed_validation.json`：21 项 delayed 硬检查 PASS。
- `data/prompt_validation.json`：三条 raw-SIM 事件全部 PASS。
- `audit/visualization_validation.json`：最终 WRL、二维图、方向、事件数和 marker/segment 数联合 PASS。
- `audit/wrl_parser_validation.json`：最终 WRL 已由 `view3dscene 4.0.0` 实际载入并转写，语法检查 PASS。
- `audit/agent_background_source_summary_audit.json`：本底来源汇总的 grain、null/duplicate/rate closure 与 exact-origin coverage 审计记录。
- `audit/nearfield_figure_validation.json`：S3d-O8 mesh、66 点、420 行、三条 prompt ID、W2 总率和三种图形输出检查 PASS。
- `data/agent_background_edge_cut_audit.json`：420 delayed + 2 prompt 的 fixed-pixel cut 重放、20 天轨迹折算及 frozen 135-row 集合精确闭合。
- `audit/edge_pixel_fiducial_validation.json`：signal/background edge-cut 合并与 (F_\mathrm{cut}/F_\mathrm{base}=\sqrt{f_B}/f_S) 检查 PASS。
- `audit/delayed_top5_chain_validation.json`：前五体积、compact ANNI/PAIR flag 与 exact production link 的加权闭合 PASS。
- `data/agent_delayed_top5_tes_chain_audit.json`：205 个 top-five raw delayed event 的 DECA→HTsim contributor→TES IA 链检查 PASS。
- `audit/top5_delayed_sources_audit.json`：full-volume activity、W2-linked activity、exact-origin 加权覆盖和 raw decay/TES deposit 交叉审计。

复现顺序：

```bash
python3 code/build_delayed_ledgers.py
python3 code/build_prompt_track_ledgers.py
python3 code/build_geometry_mesh_products.py
MPLCONFIGDIR=/tmp/mpl-s3do8-event-visual python3 code/build_final_visuals.py
python3 code/build_background_source_summary.py
MPLCONFIGDIR=/tmp/mpl-s3do8-nearfield python3 code/build_nearfield_figure.py
python3 code/agent_build_background_edge_cut.py
python3 code/audit_signal_edge_cut.py
MPLCONFIGDIR=/tmp/mpl-s3do8-edge python3 code/build_edge_pixel_performance.py
python3 code/build_delayed_top5_chain_audit.py
python3 code/agent_trace_delayed_tes_chains.py
python3 code/audit_top5_delayed_sources.py
```

重新导出 native WRL 时使用 `code/s3d_o8_geometry_only.source` 和 `code/export_s3d_o8_vrml.mac`；宏中没有 `/run/beamOn`。
