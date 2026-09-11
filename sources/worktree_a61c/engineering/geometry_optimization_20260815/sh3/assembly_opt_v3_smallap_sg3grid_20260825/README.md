# SH3 OptV3 有效小口 + SG3 网络板（W 遮罩备选，2026-08-25）

这是独立保留的被动遮罩备选方案；原 SH3 OptV3、原 35×35 网络板版和
其他旧目录均未删除、未覆盖。

中央使用与 SG3 完全相同的 `3.796 cm`、`25×25` W 网络板。原 `5.40 cm`
机械方口中，中央网络板以外的区域由四块实心 W 封住，每侧宽
`0.802 cm`。TES、主动 BGO、原 BGO 大 recess、旧四边 W 框、窗口和冷结构
均不改。因此它缩小的是**有效通道**，不是把外围实体恢复成主动 BGO；
主推荐的真实 BGO 小口版本位于相邻目录
`assembly_opt_v3_bgo_smallap_sg3grid_20260825/`。

验证结果：

- `PASS__SH3_OPTV3_SMALLAP_SG3GRID_STATIC`
- `PASS__SH3_OPTV3_SMALLAP_SG3GRID_OVERLAP_NO_TRANSPORT`
- `PASS__SH3_OPTV3_SMALLAP_SG3GRID_NATIVE_WRL_NO_TRANSPORT`
- `PASS__SH3_OPTV3_SMALLAP_SG3GRID_PREVIEW`
- `PASS__SH3_OPTV3_SMALLAP_SIGNAL_CLEARANCE_AUDIT`

重叠检查与 WRL 导出均只构造几何、不启动粒子束。WRL 含 3324 个
Shape/IndexedFaceSet：624 个中央网络板 W 固体、4 个实心 W 遮罩体和 4 个
原 W 框固体。

37,194 条冻结聚焦光线在整个 `3.796 cm` 方形走廊内均有正余量；最坏
方边余量约 `5.33 mm`。深网络板的直线几何直通比例约 `79.58%`，不能
替代信号 EventList 重放，也不能据此冻结旧 SH3 有效面积或计算灵敏度。

复跑顺序：

```bash
python3 code/build_sh3_smallap_sg3grid.py
python3 code/run_sh3_smallap_overlap.py
python3 code/export_sh3_smallap_wrl.py
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/sh3_smallap_mpl \
  python3 -B code/render_sh3_smallap_preview.py
python3 code/audit_smallap_signal_clearance.py
```
