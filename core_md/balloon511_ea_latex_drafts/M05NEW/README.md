# M05NEW 数据替换包

本目录只服务于将 M05 原稿中的历史数值替换为当前 `SH3_OPTV3_60cm` 结果，不扩展新的论文主题。

## 当前结论

- **主结果已闭合，可进入 M05 改稿**：20 d、3σ 最小可分辨通量为
  `(2.2294 ± 0.2086) × 10^-5 ph cm^-2 s^-1`（Gaussian，误差为当前统计误差）；
  Asimov 值为 `2.2383 × 10^-5 ph cm^-2 s^-1`。
- day-15 共时间轴最终背景为 `9.280 × 10^-3 cps`；对应 `F0=10^-4 ph cm^-2 s^-1`
  的信号率为 `9.7904 × 10^-4 cps`。
- 当前源合同使用八类修复后的 keV 总动能谱；宽带 gamma 已包含湮没隆起，**不再添加独立单能大气 511 keV 分量**。
- OptV3 当前统计闭合检查为 `14/14 PASS`；M05NEW 的 SG3B--OptV3 匹配检查为
  `21/21 PASS__M05NEW_ALL_REQUIRED_DATA_CLOSED`。
- SG3B 自有 37,194-ray 信号运输给出
  `Aeff = 15.12324 ± 0.04492 cm2`；20 d、3σ 最小可分辨通量为
  `(5.4058 ± 0.4014) × 10^-5 ph cm^-2 s^-1`。
- OptV3 保留 SG3B 的 `99.75%` 有效面积，把 day-15 成熟本底降到 SG3B 的
  `18.10%`，并把 20 d 最小可分辨通量降到 `41.24%`（改善约 `2.43×`）。
- 新的同尺度二维剖面已闭合：SG3B 的 TES 位于 MXC/冷盘投影下方，而 SH3 把 TES
  横向移入 chimney；`DR/MXC + staged cold plates` 在 selected delayed W2 中的占比
  由 `32.18%` 降至 `3.92%`。图见 `figures/fig_mxc_tes_sg3b_sh3_section.*`。
- 外置塑料层和至多 5 cm BPE **不作为 M05 主优化**：当前 prompt 源初正电子末端为零，
  neutron-induced delayed 仅占 direct-final 的 `8.00%`；即使理想删除该分量且信号不损失，
  `Fmin` 仍为 `2.1383e-5`，达不到 `1.5e-5`。项目已有 corrected-keV 2 cm BPE
  边界诊断显示有限正收益、未见直接 Cu 活化惩罚，但不足以推出 SH3 的净本底改善。

## 论文逻辑

保留一条紧凑主线：`SG3B 可审计基线 -> 本底限制诊断 -> SH3 OptV3 优化几何 ->
同源、同响应、同任务轴可行性比较`。SG3B 只承担参考和工程因果，不扩写成第二套主结果；
论文主结论仍是 OptV3。

## 文件

- `M05_PAPER_DATA_TABLE.csv`：M05 数据槽位主表；论文替换以此表为准。
- `REFERENCES.md`：表中引用编号对应的本地文件和用途。
- `MXC_BPE_PLASTIC_REVIEW.md`：二维剖面图注、正电子来源、BPE 判断及论文采用边界。

## 状态含义

- `READY`：数值已闭合，可直接用于改稿。
- `DERIVABLE`：当前事件目录或时间线已有全部数据，只需制表/出图，不需新运输。
- `MISSING_REQUIRED_IF_RETAINED`：只有保留 M05 对应叙事或对照时才必须补。
- `REMOVE_OLD_MODEL`：旧 M05 项与当前源合同冲突，应删除而不是补模拟。
- `OPTIONAL_REMOVE`：不是 EA 主结果必需项，可从 M05 删除。

## 闭合状态

1. SG3B 自有信号、扩统计背景、81 节点任务灵敏度和 Fmin 误差已写入主表。
2. OptV3 delayed 的精确生产体积/材料回连已闭合：111 个 selected events、39 个组。
3. prompt-gamma 合并样本有 6 个 W2-final 原始存活；该稀疏分量误差被显式传播。
   总 direct-final 本底相对统计误差为 `14.80%`，SG3B Fmin 相对误差为 `7.42%`，
   均通过本包投稿门槛。
4. M05 的旧 64-seed 段落删除，不再作为投稿硬门槛。
5. MXC/冷盘—TES 几何因果和外置 plastic/BPE 的当前上限已经闭合；不需要为 M05
   再启动一轮屏蔽层运输。

旧图仍需按当前目录和时间线重画；这是 `DERIVABLE` 制图工作，不缺物理数据。

2026-08-21 主机重启后外部 `/mnt/data` 盘未重新枚举。重启前已通过 receipt、SIM-header
seed、geometry、source hash 的 32 个 SG3B compact catalogs 保留在工作区；最终合并使用这些
缓存和前 15 片精确 activation-TT 的 pooled exposure-per-primary。该恢复边界记录在 R21，
没有把中断或失败 SIM 纳入目录。
