# Corrected-keV gamma 物理权威复核

Status: `PASS_WITH_AUTHORITY_BLOCKERS__PORTABLE_HTML_QA_BLOCKED`

## 结论

这次复核把两个问题分开了：

1. **因子 1000 的能轴修复在软件/单位合同上成立。** 保留的
   EXPACS/PARMA gamma 横轴是 MeV，Cosima `Spectrum File` 横轴是
   keV，因此必须使用 `E_keV = 1000 * E_MeV`；归一化谱密度同步除以
   1000，每个角箱的绝对 `.Flux` 保持不变。旧 `E/1000` 结果即使与论文
   看起来接近，也可能是错误谱与不同选择口径造成的数值补偿，不能作为
   单位验证。
2. **当前 corrected-keV 输运仍不是物理本底或灵敏度权威。** 先前报告的
   Mass/O8 `101/99` 是未施加主动屏蔽 veto、FoV/Compton、1 microsecond
   时间关联或正式 Step05 的任意 TES-positive 毛命中。事件级主动体积复核
   后，Mass/O8 分别只剩 `12/3`；严格 W2 的 `7/8` 件都降为 0。

因此，`101/100000` 或 `99/100000` 约等于 `1e-3` 只表示“投掷一个
全空间宽带初级 gamma 后，在 TES 留下正沉积”的条件传输效率，不是 TES
最小可识别通量，也不是 511 keV 线灵敏度。

## 精确 cutflow

样本均为 corrected-keV instant gamma；每套几何 `4 x 25,000 = 100,000`
primaries。TES 响应为每像素 420 eV FWHM、0.3 keV post-noise threshold；
窗口是 measured TES event energy，W2 定义为 `[510.58, 511.42)` keV。

| Geometry / gate | Any TES | 480--550 keV | W2 |
|---|---:|---:|---:|
| Mass_model_511, veto 前 | 101 | 12 | 7 |
| Mass_model_511, explicit CsI `<50` keV | 12 | 1 | 0 |
| Mass_model_511, explicit CsI `<70` keV | 12 | 1 | 0 |
| Mass_model_511, explicit CsI `<80` keV | 12 | 1 | 0 |
| S3d-O8, veto 前 | 99 | 9 | 8 |
| S3d-O8, true BGO `<50` keV | 3 | 0 | 0 |
| S3d-O8, true BGO `<70` keV | 3 | 0 | 0 |
| S3d-O8, true BGO `<80` keV | 3 | 0 | 0 |

主动体积合同是显式白名单，而不是字符串模糊匹配：

- Mass_model_511：仅 `CsI_Side_Segment_*`、
  `CsI_Bottom_Quadrant_*`、`CsI_TopAnnulus_Segment_*`；
- S3d-O8：仅三块精确命名的真实 BGO 晶体；
- 两套几何都排除名称中含 `ActiveShield` 的被动 Kapton；
- O8 在 BGO 门后再加 plastic `<50` keV，本样本的 `3/0/0` 不变。

记录的 TT 为 Mass `1.840462 s`、O8 `1.851504 s`。未 veto 毛率分别为
`54.88 Hz` 与 `53.47 Hz`；80 keV 主动屏蔽诊断后为 `6.52 Hz` 与
`1.62 Hz`。这些仍是诊断率，不是 Step05 率。

## 为什么 W2 会在 veto 前出现 15 件

保留的 total-gamma 源约 23.43% 通量位于 1.022 MeV 成对产生阈值以上。
本样本 15 个未 veto W2 事件全部由高能初级 gamma 的成对产生/湮没次级链
贡献，并全部伴随真实主动屏蔽沉积。因此不能用“输出 W2 计数除以输入 W2
窄窗通量”估计 511 keV 有效面积；需要响应矩阵或独立的单能 511 keV
注入。

当前 `unit_only_total_gamma` 已包含保留宽箱 annihilation bump，源卡没有再加
mono-511，因此当前不存在双计数。未来若建立 continuum + line 模型，必须先
做线扣除、单一环境和总通量闭合。

## 与 511-CAM 论文的正确比较

[官方 arXiv v3](https://arxiv.org/pdf/2206.14652v3) 中约 60 Hz 是由
XL-Calibur 测量按探测器质量缩放得到的 `>15 keV` 宇宙线与大气总本底
毛率；它不是最终窄线选择率。论文的信号模拟另用聚焦的单能 511 keV
近场源，并包含 BGO veto 和 detector-response 假设。发表记录见
[JATIS DOI](https://doi.org/10.1117/1.JATIS.9.2.024006)。

当前约 54 Hz 是 EXPACS/PARMA gamma-only、任意 TES 正沉积、未正式 veto
的毛率。两者同量级说明约 100 个毛命中本身不构成明显矛盾，但成分、几何、
阈值和选择口径不同，既不能相互验证，也不能用旧 `E/1000` 的最终选择结果
反推旧单位正确。

## Authority boundary

当前可以作为 authority 的内容：

- MeV-to-keV 能轴和 PDF Jacobian 变换；
- 20 个等 mu 角箱的 `.Flux` 保持与 `4 pi` 闭合；
- `Flux * pi * R^2` FarField launch-rate 合同；
- 本 100k/geometry 样本的 TES 毛命中、事件级真实主动体积沉积与诊断
  cutflow；
- 50/70/80 keV 阈值下 W2 全部可 veto 的样本内稳健性。

当前不能作为 authority 的内容：

- 正式 Step05 post-veto 本底率；
- 0.84 keV 窄窗的 line/continuum 形状；
- 聚焦 511 keV 有效面积或最小可识别通量；
- prompt + activation + delayed + detector-response 的任务本底；
- 任务灵敏度或几何晋级。

两套几何在诊断 veto 后 W2 都是 0 件，但约 1.85 s 内 0 件的单侧 95%
Poisson 率上限仍约 `1.62 Hz`，远不足以证明任务级低本底。

## 下一步

1. 冻结 corrected-keV 源合同，不回退旧能轴。
2. 在现有 corrected SIM 上冻结几何专属主动体积翻译、50/70/80 keV 阈值
   语义、1 microsecond 时间关联、plastic veto、单像素/edge、FoV/Compton
   与 W2 顺序，生成正式逐步 cutflow。
3. 分开跑独立的定向/光学耦合 mono-511 信号基准和 corrected broadband
   feeddown 基准。
4. 先规定希望约束的 post-selection W2 率，再由 Poisson 上限反推所需 TT
   和 primaries；不要仅按“再跑 100k”决定统计量。
5. 完成八族 corrected-keV prompt、activation、delayed 与 detector response
   闭合后，再恢复任务灵敏度和几何比较。

## 复现

从仓库根目录运行事件级审计：

```bash
python3 engineering/particle_source_unit_repair_20260811/gamma_physics_authority_reaudit_20260811/code/audit_corrected_gamma_tes.py
```

复核 JSON 可解析和关键状态：

```bash
python3 -m json.tool \
  engineering/particle_source_unit_repair_20260811/gamma_physics_authority_reaudit_20260811/data/corrected_gamma_tes_authority_reaudit_summary.json \
  >/dev/null
python3 -m json.tool \
  engineering/particle_source_unit_repair_20260811/gamma_physics_authority_reaudit_20260811/data/normalization_physics_audit.json \
  >/dev/null
```

两份 chart/table SQL 是 values-only 的 reviewed snapshot，可用 Python 标准库
SQLite 复核：

```bash
python3 -c "import pathlib,sqlite3; c=sqlite3.connect(':memory:').cursor(); p=pathlib.Path('engineering/particle_source_unit_repair_20260811/gamma_physics_authority_reaudit_20260811/data/cutflow_chart_snapshot.sql'); print(len(c.execute(p.read_text()).fetchall()))"
```

期望输出为 `12`；exact-table SQL 期望为 `6`。

## 产物

- `code/audit_corrected_gamma_tes.py`：事件级 SIM 审计实现；
- `data/corrected_gamma_tes_authority_reaudit_summary.json`：完整 cutflow、
  能量/角度 driver 与白名单合同；
- `data/corrected_gamma_tes_positive_events.csv.gz`：200 个 TES-positive 事件；
- `data/normalization_physics_audit.json`：单位、Flux、FarField、能段、论文口径、
  Poisson 边界与 authority blocker；
- `data/cutflow_chart_snapshot.sql`：原生图 12 行 reviewed snapshot；
- `data/cutflow_exact_snapshot.sql`：精确表 6 行 reviewed snapshot；
- `data/chart_map.json`：图形合同与最终上下文 QA 计划；
- `data/report_source_notes.md`：技术报告结构、证据清单和遗漏理由；
- `artifact.json`：canonical Data Analytics report payload。

## Portable HTML delivery blocker

`artifact.json` 已通过 canonical schema validation、payload packaging 和静态
chart extraction。官方 `npm run report:deliver` 在已安装 Chromium 的最终浏览器
QA 阶段稳定失败：

```text
stage=verification
code=horizontal_overflow
viewport=1440px
document scrollWidth=1433
document clientWidth=1425
overflow=8px
```

收窄表格并移除所有显式 `layout: full` 后结果不变；诊断显示这是共享 portable
reader report row/panel 的恒定 8 px 布局溢出，而不是本报告数据表宽度。失败截图
保留为 `report.html.tmp-*.verification-failure.png`。根据 report skill 的交付合同，
**未生成、未发布、也不应声称存在已验证的 `report.html`**；不得用结构性草稿冒充
浏览器 QA PASS 交付。
