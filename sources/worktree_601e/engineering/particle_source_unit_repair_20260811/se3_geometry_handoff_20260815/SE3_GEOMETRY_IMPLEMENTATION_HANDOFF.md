# SE3 几何实施交接（2026-08-15）

## 结论先行

本任务是用户明确重新开启的 **SE3 几何设计**，独立于仓库当前 fix5 simulation-closure 主线。不要运行 fix5 closure，不要覆盖 fix5、S3d-O8 或其他权威产物。

一级配置已经锁定：从权威 S3d-O8 成品完整复制出新包 `44_geoopt_se3_minimal_20260815`，只做下列白名单修改：

1. 删除外层 MuMetal 圆筒和后环盖；
2. 原内层 Nb 圆筒和后环盖保持形状、位置、2 mm 厚度不变，材料改为 `Aluminium` 并重命名为 SE3 Al；
3. 50 mK、100 mK、0.7 K、4 K、60 K 五块冷盘从 6 mm 改为 4 mm，并加 `Ø4 mm THRU / 6 mm square pitch` 孔阵列；
4. BPE 默认保留 20 mm，但只在 BPE side shell 上开与 focused 光路共注册的方口；plastic scintillator **保持完整、不开孔**；
5. 除白名单外，TES、读出、W/Ta、Cu can/DR/support、BGO、plastic、Kapton、outer Al、阈值、copy、relief 和坐标全部不动。

本 session 只交付几何、质量账本、原生 WRL、二维详图和最小几何验证；**不启动 prompt/delayed/full-eight-family transport，不宣称 SE3 已提高最小可分辨通量。**

## 1. 唯一输入与新包

权威输入必须是：

- [S3d-O8 `.geo.setup`](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup)
- [S3d-O8 生成器](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/build_s3d_o8_geometry.py)

在新 session 自己的 worktree 中创建：

```text
engineering/geometry_optimization_20260815/44_geoopt_se3_minimal_20260815/
  code/
  geometry/
  data/
  figures/
  audit/
```

最终核心文件统一命名：

```text
geometry/DEMO2_DR_v3p5_SE3.geo
geometry/DEMO2_DR_v3p5_SE3.det
geometry/DEMO2_DR_v3p5_SE3.geo.setup
code/build_se3_geometry.py
```

实施方法：复制 S3d-O8 的五个 core geometry files 和生成逻辑，再做一次 fail-closed、exact-once 白名单 patch；不要从更早的 S3c 重新生成。原 worktree 只读，不复制 GB 级 SIM。

## 2. 精确几何白名单

### 2.1 近场屏蔽

| 动作 | S3d-O8 volume | SE3 要求 |
|---|---|---|
| REMOVE | `MuMetal_MagShield_Outer_Cylinder_2mm` | GEO 与对应 DET block 都删除 |
| REMOVE | `MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm` | GEO 与对应 DET block 都删除 |
| REPLACE/RENAME | `Nb_MagShield_Inner_Cylinder_2mm` | 同形、同位、同 2 mm 厚度；material=`Aluminium`；新名 `SE3_Al_Shield_Inner_Cylinder_2mm` |
| REPLACE/RENAME | `Nb_MagShield_Inner_Back_ColdFingerCap_2mm` | 同形、同位、同 2 mm 厚度；material=`Aluminium`；新名 `SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm` |

原几何参数保持：

- cylinder：local axial `-3.85..+4.10 cm`，`r=4.0..4.2 cm`；
- back cap：local axial `+4.10..+4.30 cm`，`r=1.85..4.2 cm`；
- 两者均 `Position 0 0 -5.2`、`Rotation 0 90 0`；
- 新 Al 两体继续保留等价 `0.001 keV` deposit scorer，便于以后追 first-pair/annihilation host；旧 Mu scorer 删除；Materials 文件不改。

`Win_MagShield_Al_foil_side` 暂保持原体、原位、原 scorer。注意这是一个 `25 µm × 37.96 mm × 37.96 mm` 方窗，位于旧 Mu 前端面；按本次“最小修改”执行后，SE3 是 **单层 Al 开口圆筒 + 后环盖 + 既有方窗的质量模型 proxy**，不是已证明连续/气密的完整 Al 盒。不得自行补画没有尺寸依据的 Ø80 mm 前端盖，也不得宣称磁学已合格。

### 2.2 五块冷盘

只修改以下五块；中心、半径、材料及原 DET 名保持：

| volume | material | R | center z′ | old t | SE3 t |
|---|---|---:|---:|---:|---:|
| `ColdPlate_MXC_50mK_SD_anchor` | Copper | 150 mm | 0 mm | 6 mm | 4 mm |
| `ColdPlate_CP_100mK_intercept` | Copper | 150 mm | 50 mm | 6 mm | 4 mm |
| `ColdPlate_Still_0p7K` | Copper | 150 mm | 110 mm | 6 mm | 4 mm |
| `ColdPlate_4K` | Copper | 175 mm | 200 mm | 6 mm | 4 mm |
| `ColdPlate_60K` | Aluminium | 175 mm | 290 mm | 6 mm | 4 mm |

即每盘 local half-thickness 从 `±0.3 cm` 改为 `±0.2 cm`。`Plate_300K_Top_Service_Lid` 不是 cold plate，本次保持不动；其他 Cu can、DR Cu、cold fingers、clamps、supports 全部不动。

### 2.3 孔阵列

孔规则固定，不再做样式选择：

- 圆通孔直径 `4.0 mm`，半径 `0.2 cm`；
- 正方晶格，孔心距 `6.0 mm`；
- 盘心锁相：`(x′,y′)=(0.6 i,0.6 j) cm`；孔轴沿 plate-local z；
- 孔间最小 web 为 2 mm；外缘也保留至少 2 mm 实边，因此无 keep-out 时接受 `sqrt(x′²+y′²) <= R-0.4 cm`；
- 与 clamp pad、cold finger、XS400 rod 或明确热接口投影相交的孔跳过，但不移动其余晶格点。每个跳过点必须在 ledger 中记录 keep-out 原因；
- 优先用每盘一个 `Vacuum` PCON 孔模板及 daughter `.Copy`，避免一万级串联 Boolean；孔不加 scorer，父盘 scorer 自动记录剩余材料。

无限方格的解析开孔率是 `π·2²/6² = 34.9066%`。6→4 mm 后、忽略边缘/keep-out 时，质量剩余率约 `43.3956%`；这只是检查量，不是最终质量。无功能 keep-out 的参考孔数为 R150 盘 1869、R175 盘 2561，最终值必须由实际 `hole_pattern.csv` 闭合，不能预填。

每盘质量账本至少输出：`R, t, material, accepted_hole_count, void_cm3, mass_before_kg, mass_after_kg, delta_mass_kg, open_fraction`。五盘旧质量约 18.131 kg；只减薄约 12.087 kg；无功能 keep-out 的孔板参考约 8.061 kg，最后以生成几何为准。

## 3. BPE 决策与 focused 口

### 一级选择：`SE3-P20`

保留现有 20 mm、5 wt% BPE side/bottom/top；只在 `GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm` 的负 x′ focused 入口开方口。BPE bottom/top cap 不改。

方口与现有 BGO/Al window 共注册：

```text
full aperture = 37.96 mm × 37.96 mm
center in InstrumentFrame = (y′, z′) = (0, -52 mm)
suggested BPE-side cut BRIK half-size = (14.5001, 1.898, 1.898) cm
relative cut position in BPE-side volume = (-14.5, 0, -15.95) cm
```

`GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm` 及两个 plastic caps 必须 shape/volume/scorer 不变，**不准开孔**。图中要明确画出 focused rays 穿过完整的 10 mm plastic。

物理依据只到以下程度：

- FACT：原卡 37,194/37,194 focused rays 都穿 BPE 与 plastic；官方 stage04 signal 是 outer-envelope 之后注入，不能给 BPE/plastic 透射定价；
- FACT：20 mm BPE 对 Cu-61/62/64 的 direct-natural-Cu boundary-current index 约 `0.885/0.842/0.897`，只证明 modest direct-n mechanism，不是 W2/F3；
- INFERENCE：完全删除 BPE 可能丢掉这点中子收益，并让已知 4.15–6.35 MeV prompt gamma 更易到达内层 pair host；
- UNKNOWN：高能 primary n、p/alpha 产生的内层 secondary-n、以及 SE3 新 Al/多孔冷盘的 total prompt+delayed 净效应。

因此本几何 session 不增厚 BPE，也不做厚度盲扫。只生成一级 `P20-port`；同时让生成器可参数化输出 `P0` 作为以后 matched falsifier。只有未来 P0/P20 区间仍不决时才补 10 mm；没有新证据不做 >20 mm。

## 4. 为什么不能先报性能收益

以下是冻结的 S3d-O8 物理图，不需要新 session 重跑确认：

- delayed W2=`0.0544797522 cps`；旧 Nb 与 MuMetal 分别占 16.89% 与 14.25%；被本次修改触及的旧 host 合计约 66.5%，但这绝不是 SE3 的预期降幅；
- prompt root 3883：4.148 MeV gamma，PAIR@Nb→ANNI@Mu；root 8081：6.346 MeV，PAIR@Nb→ANNI@L0 Cu；删旧壳会迁移 host，不等于事件消失；
- prompt root 19932：5.769 MeV，PAIR+ANNI@DR Cu；它不依赖 Nb/Mu，且冷盘变薄/多孔会提高部分 511 逃逸；
- Al 不是“零活化”材料；SE3 后续必须把新 Al volume 作为 exact material/position 重新做 n/p/alpha activation screen。

本次状态只能写 `GEOMETRY GENERATED/VALIDATED — PHYSICS UNKNOWN`，不能写 `PHYSICS PROMOTED`。边缘像素属于后续分析 cut，不删除 TES 像素、通道或读出。

## 5. 必须交付的图与数据

复用而非手绘下列 S3d-O8 可视化流程：

- [现有可视化说明与正确朝向](/home/ubuntu/.codex/worktrees/601e/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_event_geometry_visualization_20260814/README.md)
- [原生 WRL 宏](/home/ubuntu/.codex/worktrees/601e/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_event_geometry_visualization_20260814/code/export_s3d_o8_vrml.mac)
- [WRL/mesh 解析器](/home/ubuntu/.codex/worktrees/601e/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_event_geometry_visualization_20260814/code/build_geometry_mesh_products.py)
- [真网格剖面绘图](/home/ubuntu/.codex/worktrees/601e/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_event_geometry_visualization_20260814/code/build_final_visuals.py)

必须产物：

```text
geometry/se3_native_geant4_full.wrl
figures/se3_mass_model_detail.{svg,pdf,png}
figures/se3_dimensioned_sections.{svg,pdf,png}
data/se3_geometry_volume_manifest.csv
data/se3_hole_pattern.csv
data/se3_mass_ledger.csv
audit/se3_geometry_validation.json
audit/se3_visual_validation.json
audit/se3_wrl_parser_validation.json
```

`se3_mass_model_detail` 至少含：(A) 全外包络 world X-Z 飞行侧视；(B) InstrumentFrame `y′=0` 原生 mesh 真剖面；(C) detector-bay 放大；(D) focused window face。`se3_dimensioned_sections` 至少含：(A) x′-z′ 尺寸剖面；(B) R150 与 R175 冷盘俯视孔阵列、keep-out 和实际孔数；(C) BPE-port / uncut-plastic / BGO-window 层叠尺寸图。

坐标硬门：保留 `InstrumentFrame.Rotation 0 45 0`；world `+Z` 是 sky/up；sky-facing optical axis 是 `-x′=(-1/√2,0,+1/√2)`，相对水平向上 45°；incoming focused photon 是反向 `+x′`。任何倒置，或把图称作 MASS511，均为 NO-GO。WRL 单位明确为 mm。

旧 S3d 的 activation 点和 prompt 轨迹不是 SE3 预测；本次纯几何图不要把它们重标到新 Al 上。

## 6. 最小验收门

只做这些，不重复全项目审计：

1. **静态 diff**：除 2 个 Mu 删除、2 个 Nb→Al name/material mapping、5 盘 thickness/holes、BPE side port 与相应 DET/setup 更新外，diff=0；plastic/BGO/TES 必须逐块不变。
2. **命名/集合**：setup 只 Include SE3 文件；若孔作为 vacuum daughters，非真空 solid 预期从 3096 变 3094；Nb=0、MuMetal=0，Al 非真空 placement 比原来净增2，其余材料集合不变。
3. **load/overlap**：SE3 `.geo.setup` 可由 Cosima/Geomega load，overlap 检查 PASS；WRL 由同一几何 0-event 原生导出并实际 parser load PASS。
4. **孔导航**：每个接受孔中心贯穿 4 mm 都解析为 Vacuum；相邻 web 解析为原盘材料；hole ledger、WRL 与 navigator 的中心集合一致。
5. **光路导航**：37,194/37,194 rays 的 BPE chord=0；plastic chord 仍非零、约 1 cm；Al/cold-plate 修改不得误切 focused bundle。报告最小 aperture clearance，但不要把 plastic 代价误写成零。
6. **质量闭合**：逐盘和整机 `before/after/Δmass` 由 exact geometry 计算；解析公式只作交叉检查。

完成上述门后停止并交付，不跑粒子 transport。后续若另行授权，唯一最小物理配对才是同一 SE3 core 的 `P20-port` vs `P0`，两臂都从 plastic 外侧重算 candidate-own focused S20、matched total prompt+delayed，并用候选自身 `B20_max=(S20/10)^2` 判断。

## 7. 已冻结证据入口（按需查，不要求重审）

- [S3d-O8 综合仲裁报告](/home/ubuntu/.codex/worktrees/601e/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_integrated_arbitration_20260814/REPORT.md)
- [近场与边缘像素分析](/home/ubuntu/.codex/worktrees/601e/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_event_geometry_visualization_20260814/NEARFIELD_BACKGROUND_AND_EDGE_PIXEL_ANALYSIS.md)
- [Delayed 前五链审计](/home/ubuntu/.codex/worktrees/601e/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_event_geometry_visualization_20260814/DELAYED_TOP5_TES_CHAIN_AUDIT.md)
- [BPE 专项交接](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/session_handoffs_20260814/BPE_HANDOFF.md)

执行优先级：**完整复制 → 白名单 patch → exact diff/mass ledger → load/overlap/ray navigation → native WRL → 2D/尺寸图 → 停止。**
