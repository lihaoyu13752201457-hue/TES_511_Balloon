# CODEX 执行方案: `balloon511_f10m_ge111_511line` v1

Date: 2026-06-11
Author: Claude Fable 5 (review + plan), 基于 `CLAUDE_FABLE5_LAUE_OPTION3_REVIEW_PROMPT_20260611.md` 的评审结论与用户对设计参数的更正。
执行者: Codex
状态: 待执行 (Phase 0 当天可出权威草案)

---

## 0. 背景与裁决记录 (为什么是这个方案)

### 0.1 设计参数更正

- 原 review prompt 中 `A_eff = 200 cm^2` 是用户误输入。**真实设计参数是 `A_eff = 20 cm^2`。**
- 修正后 `laue.png` 物理上自洽: f=10 m 下严格 Ge(111)、30 arcsec 马赛克、~1 cm 厚单环透镜的诚实 A_eff(511) 正是 15-20 cm^2 区间。

### 0.2 Option 3 裁决 (归档, 不进主线)

GPT_pro `GE_MULTIHKL_LINE200_STRETCH` 的 253.5 cm^2 估计高估约一个数量级, 两个独立错误:

1. 平均反射率 0.30 假设: 2 arcmin 马赛克 Ge 在 511 keV 的峰值叠层反射率只有 ~0.085
   (sigma_peak = Q*W(0) ≈ 0.17 /cm; Q ≈ 1.07e-4 /cm, 与代码常数 Lambda0=539.8 um
   换算值 1.11e-4 一致到 3%, 与本地 XOP 曲线峰 0.257481@30arcsec/10.2mm 交叉验证)。
2. 四个轴向层 (同半径同能量, z=0/2.5/5/7.5 mm) 被线性相加: 投影 2876 cm^2 vs
   可用环带 ~1025 cm^2, 重叠 x2.8。马赛克晶体理论上限 0.5, 等效宣称 ~0.7 不可能。

结论: Option 3 as-written 的诚实值 ~20-25 cm^2。既然目标本来就是 20 cm^2, 单环
Ge(111) 即可达成, **不需要多 HKL、不需要四层、不需要 2 arcmin 马赛克**。

### 0.3 物理余量备忘 (未来要更大面积时再看, 本方案不用)

- 带式几何 (按能段铺环, Option-3 风格): f=10 m 上限 ~20-25 cm^2。
- line-dedicated 几何 (每个 HKL 在自己的 511 Bragg 半径放一条宽行, 30 arcsec,
  最优厚度 ~1-1.6 cm, 行内 delta_theta=0 为方向条件, 整行峰值反射):
  - 4-5 个 HKL x 18 mm 行宽 ≈ 70-110 cm^2 (放弃"仅 Ge(111)");
  - ~30 mm 行宽 ≈ 150-200 cm^2 (代价: ~10 kg Ge, 焦斑 r90~16 mm 贴 Be 窗边,
    放弃 5.8 mm 分辨率)。
- 线面积标度 A_eff ∝ f^2 (r0=2f*thetaB, 窗宽=2f*dtheta); 文献锚:
  MAX f=86 m / ~8000 晶体 / 30 arcsec / 115 kg 才到几百 cm^2@511;
  LAUE 项目弯晶 Ge(111) 曲率 40 m 对应 f=20 m; 511-CAM 为同构 (Laue+堆叠 TES) 公开概念。
  (arXiv:2206.14652, arXiv:1511.02990, arXiv:astro-ph/0603152, Frontera & von Ballmoos 2010)

### 0.4 评审中发现的既有问题 (与本方案一并处理)

1. **PSF 缺 tile 足迹项**: 默认 `--source-jitter-mm 0.3` 只照亮 tile 中心
   ±0.15 mm, 平板晶体的平行出射束足迹本应 ≈ tile 尺寸。f=9 m 权威的
   r99=0.2914 cm 是"只有马赛克弥散"的数字, 诚实焦斑是 tile 足迹主导。
   修法零代码: jitter 设为 tile 尺寸即整面泛光 (见 Phase 0 R2)。
2. **tile 放置不旋转, 斜方位角相邻盒体静默重叠**
   (`laue_multiring_bfull_demo.cc:1342` rotation=0, PVPlacement 未开 checkOverlaps;
   f=9 m 老几何同样存在)。对中心瞄准模式无实际影响, Phase 1 修。
3. 在线 Darwin 后端 Ge(111) 硬编码 (`:395-422`)、Bragg/MFP 用 ring 设计能量而非
   光子实际能量 (`:1219, :1269`)——对本方案无影响 (单环、设计能量=511), 但若未来
   做宽带/多能量模拟必须先修, 已记录。

---

## 1. 设计冻结

模型名: `balloon511_f10m_ge111_511line`。两个变体, **默认 A1**:

| 参数 | A1 (面积优先, 默认) | A2 (焦斑优先, 备选) |
|---|---|---|
| 几何 | 单环 Ge(111), f=10 m | 同左 |
| 环半径 | **74.277929 mm** (theta_B=3.7138281 mrad) | 同左 |
| tile | **25 块 18x18x10.218801 mm** | **30 块 15x15x10.218801 mm** |
| 切向间距 | pitch 18.668 mm, gap 0.668 mm | pitch 15.557 mm, gap 0.557 mm |
| 马赛克 | 30 arcsec (沿用 f9m 晶体规格) | 同左 |
| rocking curve | 现有 `ge111_511keV_rocking_curve.csv` 原样复用 | 同左 |
| 预期 A_eff(511) | **20.40 ± 0.2 cm^2** (=25x3.24x0.25184) | 17.00 ± 0.2 cm^2 |
| 预期焦斑 (含足迹, MC 预算) | r50=7.2 mm, r90=10.5 mm, r99=12.8 mm | r50=6.0 mm, r90=8.9 mm, r99=11.0 mm |
| within-Be (r=18.98 mm) | ~1.000 | ~1.000 |
| 自然通带 FWHM | 501.0-521.0 keV (20.0 keV) | 同左 |
| Ge 质量 | 440.6 g | 367.2 g |

硬约束 (违反任意一条 = 配置作废):

- **厚度必须保持 `10.218801 mm` 不动**: XOP 曲线的有效性取决于 (E=511, HKL=111,
  t=10.2188 mm, Omega=30arcsec), 与焦距无关; 改厚度曲线即失效。
- 半径必须用与 `LoadRingConfig` 相同的公式生成
  (`r = (f - z_offset) * tan(2*asin(lambda/(2d)))`, d=3.266590088 A,
  lambda=12.398419843320026/511 A), 否则过不了 0.2 mm 一致性闸门。

### 1.1 对 laue.png 的逐行忠实度 (报告必须含此表)

| slide 行 | v1 状态 |
|---|---|
| Material: Ge(111) | PASS, 严格满足 |
| Energy range 450-550 keV | PASS (定义为 TES 分析窗); 透镜自然通带 501-521 keV, 如实标注 |
| Focus length 10 m | PASS |
| Size ⌀40 cm x 30 cm | PASS (仅用 r≈65-84 mm 环带) |
| Focus area 100 cm^2 | PASS (焦斑 r99≈13 mm << 56.4 mm 包络半径) |
| Working temperature 20±5 C | PASS (delta_theta≈5e-8 rad, 可忽略, 报告一句话) |
| Spatial resolution 2 arcmin (5.8 mm) | A2 基本满足 (r50=6.0); A1 偏差 +24% (r50=7.2), 如实记偏差 |
| FOV 5 arcmin | **FAIL (A/A2 均不满足)**: 30 arcsec 马赛克环平均响应 HEW ≈ ±20-25 arcsec, 见 §6 决定 2 |
| Pointing 15/10 arcsec | 可用但有代价: 见下表, 报告必须给曲线 |
| A_eff = 20 cm^2 | A1 PASS (20.4); A2 17.0 (-15%) |

指向/离轴损失预算 (环平均权重 W = exp(-a/2)*I0(a/2), a = ln2*(alpha/15arcsec)^2):

| 离轴/指向偏差 | 5" | 10" | 15" | 20" | 30" | 60" | 150" (2.5') |
|---|---|---|---|---|---|---|---|
| A_eff 保留率 | 0.96 | 0.86 | 0.73 | 0.59 | 0.39 | 0.17 | 0.07 |

---

## 2. Phase 0 — 零 C++ 改动, 当天出数

### 2.1 新增 `tools/make_f10m_config.py` (~40 行, 唯一新生成逻辑)

用 §1 公式计算半径并写出 (A1/A2 各一套):

`data/laue/ge111_balloon511_f10m_511keV_line_config.csv`

```csv
ring_id,design_energy_keV,radius_mm,n_tiles,material,h,k,l,d_spacing_A,tile_size_mm,thickness_mm,z_offset_mm
0,511.0,74.277929,25,Ge,1,1,1,3.266590088,18.000000,10.218801,0.000000
```

(A2 变体: `n_tiles=30, tile_size_mm=15.000000`, 文件名加 `_a2`。)

`data/laue/ge111_balloon511_f10m_511keV_xop_map.csv`

```csv
ring_id,design_energy_keV,curve_csv,source,status
0,511.0,ge111_511keV_rocking_curve.csv,CRYSTAL-diff_pat,covered
```

### 2.2 新增 `analysis/run_f10m.sh`

照抄 `run_bfull_f9m.sh`, 改: config/map 指向 f10m 文件、`--focal-mm 10000`、
透传 `EXTRA_ARGS` (用于 jitter/offaxis)。保留 `--require-rocking-curve-map`。

### 2.3 运行矩阵 (每个 N=50000, 主种子 12345, 另加 2 个种子变体)

| run | 额外选项 | 目的 |
|---|---|---|
| R1 | (默认 jitter 0.3) | 与 f=9 m 同口径的 A_eff 记账 (回归对照) |
| R2 | `--source-jitter-mm 18` (A2 用 15) | **诚实 PSF**: jitter=tile 尺寸即整面泛光照明 (tile 为轴对齐盒、束斑均匀方形, 全覆盖不外溢); 焦斑从此包含 tile 足迹项 |
| R3-R6 | `--offaxis-x-arcmin 0.25 / 0.5 / 1.0 / 2.5` | FOV/渐晕曲线 + 指向损失实测 vs §1.1 预算表 |

### 2.4 新增 `analysis/aeff_f10m_report.py`

输入 `focal_crossings.csv`, 过滤 `source_tag=laue_bfull_diffracted` 且
r <= 18.98 mm, 输出 `optics_aeff_authority_f10m.json`:

- `A_eff_cm2 = (n_tiles * tile_size_cm^2) * (within-Be diffracted fraction)`
- r50/r90/r99 (R2 口径)、within-Be fraction、自然通带、统计误差
- off-axis 表、git hash、config/curve 路径与 provenance、运行命令
- 同时给 R1 (legacy 口径) 与 R2 (honest 口径) 两套焦斑数, 显式标注口径

### 2.5 预登记闸门 (跑完对表; 偏离 = 审计, 不是发布)

1. `emergent_focal_diffraction_fraction` = 0.252 ± 0.006, 且既有
   `|emergent - analytic| < 0.01` 闸门通过 (物理与 f=9 m 同源, 最强回归检验)。
2. A_eff: A1 ∈ [19.4, 21.4] cm^2; A2 ∈ [16.2, 17.8]。R1 与 R2 的 A_eff 互差 < 2%
   (照明方式只许改焦斑, 不许改面积)。
3. R2 焦斑: A1 r50 = 7.2 ± 1.0 mm, r90 = 10.5 ± 1.5 mm。
   **若 r50 仍 ≈ 3 mm, 说明 jitter 未生效, 全部数字作废。**
4. within-Be > 0.995。
5. 离轴: HEW ∈ [15", 35"]; 15" 处损失 25-30% (对表 §1.1)。
6. 统计: 衍射 crossings ≥ 12000 (相对误差 < 1%)。

---

## 3. Phase 1 — 唯一小代码 PR (~1 天), 合入后才盖 authority 章

1. 每块 tile 加切向 `G4RotationMatrix` (绕 z 转 phi), PVPlacement 开
   `checkOverlaps=true` 验证零重叠; WRL 可视化同步旋转。
   (动机: 现 18 mm 轴对齐盒在 ~45 度方位角相邻中心距 18.67 mm < 18*sqrt2,
   存在静默重叠; f=9 m 老几何同病。)
2. 重跑 R1/R2, 确认 A_eff/焦斑变化 < 统计误差; 若超出, 停下分析原因。
3. (可选, 同 PR) summary.json 增加 within-Be 计数与 Be 半径参数; 不做也行,
   report 脚本已覆盖。

**显式不做** (超出 20 cm^2 主线, 挂 Phase 2 备选): 能量依赖 Bragg 重构、
矩形 tile、多 HKL 曲线、四层堆叠、弯晶、宽带模式。

---

## 4. Phase 2 — 条件触发分支 B (仅当设计方裁决 FOV 5' 为硬需求)

30 arcsec 马赛克物理上给不出 5' 视场 (§1.1 表)。若 FOV 必须满足:

- 切换 "Option-3-lite": **单层** line-dedicated, 2 arcmin 马赛克, 4 个 HKL 各一行,
  111/220/311/400 在各自 r0 = 74.3 / 121.3 / 142.2 / 171.5 mm,
  `design_energy_keV` 全部 511 —— **仍零 C++ 改动** (多环 + per-ring map 已支持)。
- 需要 4 条新 XOP/CRYSTAL 曲线: Ge 111/220/311/400 @511 keV, t≈16 mm (2' 最优厚度),
  Omega=2', 沿用现有 CSV schema (reflectivity/transmittivity/absorption)。
  在线 Darwin 后端对 220/311/400 不可用作权威 (Ge111 硬编码), 必须外部曲线。
- 预期: A_eff ≈ 18-22 cm^2, FOV HEW ≈ ±2', r50 ≈ 8-10 mm, Ge 质量 ~4 kg。
- 这是 GPT_pro 几何唯一值得保留的精华: **多 HKL 解决的是 FOV/指向容差, 不是面积。**

---

## 5. 集成 `TES_511_Balloon` 与交接

立即可用 (Phase 0 前即可):

- v1 质量代理进质量模型: 晶体 441 g (A1) + 支撑结构估计 1-2 kg。
- 透镜激活/瞬发宇宙线本底源项立项 (老债, 当前链路仍未含)。

Phase 0 闸门全过 + Phase 1 合入后:

- `optics_aeff_authority_f10m.json` 成为现行光学权威;
  f=9 m `A_eff=15.29928 cm^2` 归档 historical (不删, 标 superseded)。
- Step09 桥接流程不变: 只用 tracked `focal_crossings.csv`
  (`source_tag=laue_bfull_diffracted`, within Be 1.898 cm), 不用 `phase_space.csv`。
- 灵敏度口径提醒: 对 spot-r90 孔径提取, A1 相对 f=9 m 诚实基线 (15.3 cm^2 /
  r50≈6 mm 含足迹) 约 +5-10%, **不是** +33%; 报告写清楚, 不超卖。

---

## 6. 留给设计方的三个决定 (Codex 不要自行拍板)

1. **A1 还是 A2**: A_eff 命中 20 (焦斑 7.2 mm) vs 焦斑命中 5.8-6.0 (A_eff 17)。
   两套 config 都跑, 默认推 A1, 由 A_eff/r90 灵敏度品质因子 + 需求优先级定。
2. **FOV 5' 的定义**: 若指透镜接受角 → 与 Ge(111)+30" 不相容, 选 Phase 2 B 分支
   或修订 slide; 若指焦平面/探测器视场 → v1 已满足, 关闭问题。
3. **指向预算**: 15" 精度 = -27% 面积; 建议运行规划按 ≤10" (-14%) 做,
   或在 A_eff 余量里显式吃掉这笔。

---

## 7. 措辞边界

允许:

- "f=10 m Ge(111) 511-line Laue lens, application-level Geant4 B-FULL
  (G4VDiscreteProcess, EM-competing), XOP/CRYSTAL anchored;
  A_eff(511) = <R1/R2 实测> ± stat cm^2; spot r50/r90 = <R2 实测>;
  natural passband 501-521 keV; tracked focal_crossings handoff."
- "FOV (lens acceptance HEW) ≈ ±20-25 arcsec; 15 arcsec pointing error costs ~27%."

禁止:

- 宣称满足 5 arcmin FOV (除非 Phase 2 B 分支落地)。
- A1 口径下宣称满足 5.8 mm 分辨率。
- 引用 Option 3 的 253.5 / 862.8 cm^2 任何数字。
- 把 focus area 100 cm^2 说成 A_eff; 把 phase_space.csv 当科学注入源。
- 宣称 Geant4/MEGAlib 原生 Laue、宣称弯晶模型。

---

## 8. 参考

- 评审 prompt: `docs/CLAUDE_FABLE5_LAUE_OPTION3_REVIEW_PROMPT_20260611.md`
- 评审结论记录: Claude session 2026-06-11 (Option 3 x10 高估; 20 cm^2 自洽性;
  本文件 §0 为权威摘要)
- 现行 f=9 m 权威: `docs/laue_latest_discussion_20260611.md`,
  `new_geo_re/stepwise_maintenance/step04_opticsim/optics_aeff_authority.json`
- GPT_pro 几何包 (归档): `/home/ubuntu/laue_design/opticsim_full_laue_geometry_system/`
- 公开文献: 511-CAM (arXiv:2206.14652, JATIS 9(2) 024006); LAUE 弯晶 Ge(111)
  (arXiv:1511.02990); MAX (arXiv:astro-ph/0603152); Frontera & von Ballmoos 2010
  (X-Ray Optics and Instrumentation 215375); Laue/Fresnel lenses review
  (arXiv:2208.12362)。
