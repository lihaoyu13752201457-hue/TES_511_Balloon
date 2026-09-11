# SH3 OptV3 主动 BGO 小口 + SG3 网络板（2026-08-25）

这是一个独立、可复跑的 SH3 几何版本。原 SH3 OptV3、原 35×35
网络板版以及其他旧目录均未删除、未覆盖。

## 几何定义

- 前端主动 BGO 的方形开孔由 `6.000 cm` 缩为 `3.796 cm`。
- 开孔内放置与 SG3 完全相同的 `25×25` 网络板：节距 `1.55 mm`、
  W 筋宽 `0.13 mm`、W 深度 `7.98 mm`、625 个通道。
- 原来占据大 BGO recess 的四条 W 外框被移除；缩小开孔后，该区域由
  主动 BGO 实体填回，否则四条 W 外框会与 BGO 重叠。
- 原外层 Al 光学滤膜保持材料、半径和厚度不变，只由局部
  `x=-42.15 cm` 移至 `x=-41.65 cm`。这是让滤膜避开填回 BGO 的最小
  必要改动；新位置位于 BGO 下游面与 Layer05 上游面之间的既有空隙。
- TES、其余 BGO、冷结构、材料文件、探测器定义和 setup 均保持原定义。

该版本新增 `86.361536 cm³` 主动 BGO；移除旧 W 外框后加入中央网络板，
W 的净体积变化为 `-11.883887136 cm³`。

## 验证结果

- 静态构造：`PASS__SH3_OPTV3_BGO_SMALLAP_SG3GRID_STATIC`
- Geant4 全装配重叠检查：
  `PASS__SH3_OPTV3_BGO_SMALLAP_SG3GRID_OVERLAP_NO_TRANSPORT`
- 原生 WRL：`PASS__SH3_OPTV3_BGO_SMALLAP_SG3GRID_NATIVE_WRL_NO_TRANSPORT`
- 可视化预览：`PASS__SH3_OPTV3_BGO_SMALLAP_SG3GRID_PREVIEW`
- 冻结聚焦 EventList 包络：
  `PASS__SH3_OPTV3_BGO_SMALLAP_SIGNAL_CLEARANCE_AUDIT`

重叠检查使用 `CheckForOverlaps 10000 0.0001`，只构造几何，不启动粒子束。
WRL 含 3316 个 Shape/IndexedFaceSet，其中网络板 W 固体为 624 个，旧 W
外框为 0 个。

37,194 条冻结轴上聚焦光线在整个前 BGO 小口内均不碰口沿，最小方边
余量为约 `5.33 mm`。但 7.98 mm 深网络板的直线几何直通比例仅约
`79.58%`；这不是吸收或选后信号效率。正式使用该版本的有效面积或
最小可分辨通量前，必须用同一 EventList 做信号重放。

## 主要文件

- `geometry/SH3_Assembly_OptV3.geo.setup`
- `geometry/SH3_Assembly_OptV3.geo`
- `figures/SH3_Chimney_DR_Assembly_OptV3_BGO_SmallAp_SG3Grid.wrl`
- `figures/SH3_Assembly_OptV3_BGO_SmallAp_SG3Grid_preview.png`
- `data/bgo_smallap_sg3grid_manifest.json`
- `audit/bgo_smallap_sg3grid_static_validation.json`
- `audit/bgo_smallap_sg3grid_overlap_validation.json`
- `audit/bgo_smallap_sg3grid_wrl_export_validation.json`
- `audit/bgo_smallap_signal_clearance.json`

## 复跑顺序

```bash
python3 code/build_sh3_bgo_smallap_sg3grid.py
python3 code/run_sh3_bgo_smallap_overlap.py
python3 code/export_sh3_bgo_smallap_wrl.py
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/sh3_bgo_smallap_mpl \
  python3 -B code/render_sh3_bgo_smallap_preview.py
python3 code/audit_bgo_smallap_signal_clearance.py
```

本目录只闭合几何、重叠、WRL 和只读光线包络，不包含大气 511 keV、
其他本底、活化、信号响应或灵敏度输运结果。
