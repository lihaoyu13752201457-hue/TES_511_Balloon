# M04 冻结内容科学更正提案（仅供用户决策）

- 状态：`PROPOSAL_ONLY__NO_M04_EDIT__USER_DECISION_REQUIRED`
- 日期：2026-08-10
- 适用基线：
  - EN M04：`balloon511_ea_draft_en_m04_atm511_revision_20260804.tex`
  - ZH M04：`balloon511_ea_draft_zh_m04_atm511_revision_20260804.tex`
- 本文件只提出后继稿中的精确更正，不修改 M04、其 PDF、图件、retained 产品或任何分析结果。
- 本文件没有调用 Cosima，没有生成粒子，也没有运行任何 prompt、continuum、delayed、signal 或全链模拟。

## 1. 冻结基线与用语

本提案中的行号只对下列逐字节基线有效：

| 对象 | SHA-256 |
| --- | --- |
| EN M04 `.tex` | `3eb0c1edccd7af7b198ab397371d633392c6a316a4ee3fbdf258057f54c7c53e` |
| ZH M04 `.tex` | `66df5babd3ecf5107c6f15e0eab525b25aaaea4fe5a641879962cd753524ba19` |
| EN 冻结前缀（第 1--1199 行） | `c72137b78a66e45add8c4d5c25dfd07261a873862b7c202916b73d0c125f5e50` |
| ZH 冻结前缀（第 1--669 行） | `1b11acad70efd5f10df6adba63a993462466954d052a2bab12f441f70276fc47` |

以下区分三种处理：

- **必须解除冻结修正**：原 Methods/源定义/选择定义本身与实现或权威数据冲突。只在后文增加说明会让同一稿件保留两套互相矛盾的定义，不能作为 submission-ready 稿。
- **可在后继新节或 Results 表中补充**：新增内容本身不需要改动冻结前缀；但若冻结前缀中仍有相反陈述，则仍须同时修正该前缀陈述。
- **保持条件式边界**：当前执行范围不授权相应输运或重处理。缺失证据只降低结论强度，不触发全量或其他粒子重跑。

建议的总体决策是：M04 永久保持原样；用户若同意科学更正，只在隔离的 M05 或后继副本中解除相应前缀冻结。若用户坚持后继稿也保持前缀逐字节不变，则该后继稿只能标为审阅增补稿，不能标为 submission-ready。

## 2. 决策总表

| ID | 科学问题 | M04 主要位置 | 可只靠新节澄清？ | 后继稿所需用户决定 |
| --- | --- | --- | --- | --- |
| F01 | PARMA 原生 511 线与旧 semi-empirical sidecar | EN 333, 458--547, 643, 1097, 1120--1134；ZH 141, 227--301, 364, 594, 614--625 | 否 | 解除冻结，删除旧 nominal sidecar 定义，改为单份官方 PARMA 510.99895-keV 线；旧观测参数只作 alternate/systematic |
| F02 | retained broadband gamma `_2602units` 整体能轴低 1000 倍 | EN 394--453, 642；ZH 183--223, 363 | 否 | 解除冻结并披露 legacy photon-axis blocker；保留“line-term 离线修正对 Broad/W511 为 0”，但不得把旧 continuum 升格为物理 authority |
| F03 | 延迟源实际活动分配键为 `(VN,ZA)` | EN 571--580；ZH 317--324 | 否 | 解除冻结，把“按体积、核素和激发态匹配”改为“按 `(VN,ZA)` 分配；`exc_keV` 仅记录” |
| F04 | `ACTIVE_SHIELD` 子串误纳三件被动 Kapton | EN 306--310, 900--915, 1328；ZH 125, 502--515, 746 | 否（新节只能说明设计意图） | 二选一：准确冻结并披露历史谓词，或另行授权纯离线重选；不得称 BGO-only 或 BGO+plastic-only |
| F05 | final geometry 漏写 BPE/plastic，且上游信号透过未闭合 | EN 244--252, 297--304, 331, 685--706, 1287--1338；ZH 117, 123, 139, 384--396, 720--751 | 部分可以 | 新节可补完整层级与证据边界；但 EN 299--304 / ZH 123 的“贯穿周围壳层”及 final-only-BGO 表述仍须解除冻结限定 |

## 3. F01：PARMA 原生 511 线取代旧 nominal sidecar

### 3.1 精确冲突位置

- EN 333：框架概述称所用 EXPACS/PARMA 表“只有 continuum interpolation”，因此另加测量约束的 511-keV 线。
- EN 458--467：把 20 个光子表定义为 smooth continuum，并把潜在线重叠仅列为未量化不确定度。
- EN 469--547：把 Peterson/Harris 启发的半经验归一、刚度阶梯、上下半球核和 `0.0515559 ph cm^-2 s^-1` 定义为 nominal line source。
- EN 643：源模型表保留旧 `3.0e6`、`5143.83 s` 和旧通量。
- EN 1097、1120--1134：任务折叠继续引用旧式 `eq:atm511_flux`、`Rc=11.0 GV` 代理曲线。
- ZH 对应位置：141；227--232；234--301；364；594；614--625。

### 3.2 现有原文（关键句）

EN 333：

```text
It was transported separately because the EXPACS/PARMA photon tables used here contain only continuum interpolation at 511 keV, rather than a discrete line entry.
```

EN 458--467：

```text
The 20 atmospheric photon tables used for the EXPACS/PARMA prompt source represent a smooth continuum. ... We retained these tables unchanged and transported a separate atmospheric positron-annihilation component modeled as monoenergetic at 511 keV. ... Possible overlap is therefore recognized as an unquantified source-model uncertainty rather than assumed to be zero.
```

EN 469--472：

```text
The line source is semi-empirical. Its reference normalization, rigidity factors, and upward limb-darkening form are informed by atmospheric gamma-ray measurements ...
```

ZH 141：

```text
本文单独输运该线源，是因为所用 EXPACS/PARMA 光子表在 511 keV 处只有连续谱插值，而没有独立的谱线条目。
```

ZH 227--236：

```text
输运所用的 20 个 EXPACS/PARMA 大气光子表描述平滑连续谱。……本文原样保留这些连续谱表，并另行输运在输入中建模为 511 keV 单能的大气正电子湮没线。……该线源采用半经验模型。
```

### 3.3 建议替代文本

以下文字应替换 EN 333 中的大气线来源句，并作为 EN 458--547 的新定义核心；旧半经验方程不再作为 nominal：

```text
PARMA's photon model contains an explicit atmospheric positron-annihilation line. For the frozen day-15 authority tuple (2025-08-31, latitude 34 deg, longitude 100 deg, altitude 38.75 km, W=114.6, Rc=11.6 GV, and X=3.4614689720143224 g cm^-2), the archived official PARMA routines give a full-sphere line-integrated flux of 0.16651547160226118 ph cm^-2 s^-1 at 0.51099895 MeV. We represent this physical component exactly once as a monoenergetic 510.99895-keV photon module. The line flux is distributed among equal-mu angular bins with the normalized PARMA photon angular distribution evaluated at the line energy; get511fluxCpp is already a full-sphere integral and is not divided by 4 pi. Peterson/Harris/Mahoney measurements are retained only as alternate or line-shape systematic constraints and do not provide a second nominal line normalization.
```

建议中文对应文本：

```text
PARMA 光子模型显式包含大气正电子湮没线。对冻结的第 15 天权威参数组（2025-08-31，纬度 34 deg，经度 100 deg，海拔 38.75 km，W=114.6，Rc=11.6 GV，X=3.4614689720143224 g cm^-2），归档的未修改 PARMA 官方程序给出 0.51099895 MeV 处全空间线积分通量 0.16651547160226118 ph cm^-2 s^-1。本文只用一个 510.99895-keV 单能光子模块表示该物理分量，并用线能处归一化的 PARMA 光子角分布把总线通量分配到等 mu 角箱。get511fluxCpp 的返回值已经是全空间积分，不再除以 4 pi。Peterson、Harris 和 Mahoney 的观测仅作为替代归一或线型系统学约束，不再提供第二份名义线归一。
```

EN 643 / ZH 364 的旧源模型表行建议分别替换为：

```text
Atmospheric 511-keV line & Atmospheric positron-annihilation photons spectrally degenerate with the science line & One official-PARMA monoenergetic module at 510.99895 keV; day-15 full-sphere flux 0.16651547160226118 ph cm^-2 s^-1; angular bins and transported statistics are taken from the final line-only campaign manifest. \\
```

```text
大气 511-keV 线 & 与科学线在能谱上简并的大气正电子湮没光子 & 单份官方 PARMA 510.99895-keV 单能模块；第 15 天全空间线通量为 0.16651547160226118 ph cm^-2 s^-1；角分箱与输运统计量以最终 line-only campaign manifest 为准。 \\
```

EN 1120--1134 / ZH 614--625 的任务折叠建议改为角箱响应形式，而不是继续引用旧代理刚度曲线：

```latex
R_{\mathrm{atm511},j}(t)=\sum_i \Phi_{511,i}^{\mathrm{PARMA}}(t)K_{j,i},
```

其中 `i` 是保留 source-bin identity 的 PARMA 等 `mu` 角箱，`K_{j,i}` 是同一 O8 几何和同一冻结选择下的 line-only detector-response coefficient。该解析折叠复用角箱响应，不要求在每个任务时间箱重新输运，更不要求重跑 continuum 或其他粒子模块。

### 3.4 用户决策与边界

- **必须解除冻结修正。** 后文新增一句“PARMA 原生含线”不能消除 EN 333/458--547 与 ZH 141/227--301 中相反的 nominal 定义。
- 旧 sidecar 的 detector rate、占比、任务折叠和 headline number 必须从模块化总量中移除，再加一次新 PARMA line module；prompt、delayed、signal 和其他粒子模块保持不变。
- 最终 line-only 计数、曝光和 detector rate 只能从通过 gate 的最终 line campaign manifest 填入；不得把旧 `3.0e6`、`5143.83 s` 或旧 `0.0515559` 沿用为新 PARMA 结果。

## 4. F02：retained broadband gamma 的 `_2602units` 能轴错误

### 4.1 精确冲突位置

- EN 394--453 把 photon 与其他粒子一起描述为由 EXPACS/PARMA differential spectrum 正确转换、输运和按曝光归一。
- EN 642 的源模型表把整个 prompt bundle 列为可直接解释的 EXPACS/PARMA full-sphere field。
- ZH 对应位置为 183--223 和 363。

这些行没有披露：O8 实际 photon source card 指向 `cosima_spectra_dp_2602units/`，该目录把已经是 keV 的整个横轴再次除以 1000。

### 4.2 现有原文（关键句）

EN 412--423：

```text
For each particle family the EXPACS/PARMA differential spectrum is converted into a MEGAlib far-field area source ... Both hemispheres are retained in the prompt transport ...
```

EN 440--453：

```text
All particles are then transported through the detector/cryostat mass model ... This per-species normalization is required ... over-sampling changes the Monte Carlo variance but not the expected physical rate.
```

ZH 193--222：

```text
对每个粒子族，EXPACS/PARMA 微分谱被转换为 MEGAlib 远场面积源……随后所有粒子经 Geant4/MEGAlib 在探测器/低温系统质量模型中输运……过采样只改变蒙特卡洛方差，不改变物理期望率。
```

### 4.3 已闭合的事实，必须同时写全

1. 正确的 Cosima photon DP 在线附近应为 `449.65, 566.08, 712.64 keV`；O8 实际 DP 为 `0.44965, 0.56608, 0.71264 keV`。
2. 该因子 1000 错误作用于整个旧 O8 prompt-photon module，不只作用于旧宽箱 line bump。
3. 1000 万个旧 gamma primaries 中有 7,639,501 个初能低于 1 keV；SIM `IA INIT` 直接确认这不是标签错误。
4. 离线移除误置 line term 只改变 sub-keV active-only 事例；`Broad480--550` 和 `W511` 的事件数与率修正都严格为 `0`。
5. “本次去重对 W511 为 0”不等于“正确能轴的 photon continuum 对 W511 必为 0”。前者是既有错误 SIM 的离线差值，后者没有被本审计证明。

### 4.4 建议替代文本

建议在 EN prompt-source Methods 中、紧接粒子族源构建后加入并限定原有转换陈述：

```text
The retained O8 broadband-photon source card references the legacy `_2602units` differential-probability tables. Their abscissae were divided by 1000 after conversion to keV, so the complete transported photon-energy axis is a factor of 1000 too low. This legacy photon module is retained under the present modular-reuse scope but is not a physical broadband-gamma authority. An event-level audit removes the misplaced broad-bin PARMA line term offline; because that term was transported at 0.44965--0.71264 keV, the correction to both Broad480--550 and W511 is exactly 0 cps. This zero correction does not validate the remaining legacy continuum or predict the response of a correctly energized continuum. The seven non-photon prompt families are unaffected by this photon-axis defect.
```

建议中文对应文本：

```text
保留的 O8 宽带光子源卡引用 legacy `_2602units` 微分概率表。该表在转换为 keV 后又把横轴除以 1000，因而已输运的整个光子能轴比应有值低 1000 倍。当前模块化复用范围保留该旧光子模块，但不把它作为物理宽带伽马权威。逐事例离线审计移除误置的 PARMA 宽箱线项；由于该线项实际在 0.44965--0.71264 keV 输运，它对 Broad480--550 与 W511 的率修正均严格为 0 cps。这个零修正既不能验证剩余旧连续谱，也不能预测正确能轴连续谱的探测器响应。其余七个非光子瞬发族不受该 photon-axis 缺陷影响。
```

EN 642 / ZH 363 的 prompt 表行必须把 `gamma` 与七个非光子族的 authority 分开；不能再用一行无条件把八族都称为同等有效的 EXPACS/PARMA 物理场。建议状态列明确写：

```text
seven non-photon families: retained transport authority; broadband gamma: legacy factor-1000 energy-axis blocker, zero selected W511 records in the retained catalogue, not a physical continuum authority
```

```text
七个非光子族：保留的输运权威；宽带 gamma：legacy 能轴低 1000 倍的 blocker，保留目录中 W511 选后记录为零，但不构成物理连续谱权威
```

### 4.5 用户决策与边界

- **必须解除冻结修正**，否则 Methods 仍把一个已知整体错能轴的 photon module 描述为物理 differential field。
- 当前用户范围明确不授权 continuum 重跑。本提案不要求、不建议、也不触发该重跑；后继稿只能降低 prompt-photon 结论强度并保留 blocker。
- 该 blocker 不改变本次 line-term 去重的 `Broad/W511 delta=0`，也不改变“只新输运 PARMA 单能线”的模块化执行合同。

## 5. F03：延迟源分配键实际为 `(VN,ZA)`

### 5.1 精确冲突位置与现有原文

EN 571--580，核心句位于 578--580：

```text
The fixed day-15 population is then matched to these records by volume, isotope, and excitation state, so the delayed source can use the simulated production coordinates rather than only volume-integrated activities.
```

ZH 317--324，核心句位于 321--322：

```text
固定第 15 天群体随后按体积、核素和激发态与这些记录匹配，使延迟源能够使用模拟产生坐标，而不是只有体积积分活度。
```

实现权威 `code/tools/build_fix5_1of10_exactpos_delayed_source.py` 的活动表和 RPIP 分配键均为 `(VN,ZA)`；`exc_keV` 写入 weighted table 供记录和审计，但不进入活动分配键。

### 5.2 建议逐句替换

EN：

```text
The fixed day-15 activity is allocated to production-position records by the canonical logical-volume name and nuclide identifier, i.e. the `(VN,ZA)` key. The RPIP excitation energy (`exc_keV`) is retained in the weighted table as provenance but is not part of the activity-allocation key. The delayed source therefore preserves sampled production coordinates conditional on the implemented `(VN,ZA)` grouping rather than on a separately matched excitation state.
```

ZH：

```text
固定第 15 天活度按规范化逻辑体名称和核素编号，即 `(VN,ZA)` 键，分配到产生位置记录。RPIP 激发能 `exc_keV` 保留在加权表中作为来源记录，但不属于活度分配键。因此，延迟源是在实现的 `(VN,ZA)` 分组条件下保留采样产生坐标，并未另按激发态匹配活度。
```

### 5.3 用户决策与边界

- **必须解除冻结修正。** 这是一处 Methods 实现描述错误，不能只靠后继新节补充。
- 本更正不改变现有 source、SIM、率或有限 `M` 离线校验，也不授权加入 excitation-state 维度重建源。
- 若未来要把 `exc_keV` 加入分配键，那是新的源算法版本，必须另建工作包；不能把未来设计反写成当前实现。

## 6. F04：冻结 active-veto 谓词误纳被动 Kapton

### 6.1 精确冲突位置

- EN 306--310 / ZH 125：把最终 50-keV 门概括为 scintillator active-shield deposit。
- EN 900--915 / ZH 502--515：定义 `E_sh`，但只说明 baseline CsI 情形，没有给出 final O8 的实际字符串谓词。
- EN 1328 / ZH 746：明确把 final 门写成 `BGO offline anticoincidence` 和 “active BGO volumes”。

实际冻结函数位于 package-44 Step05 的 `is_s3d_active_veto_volume`：

```python
upper.startswith("CSI_")
or "ACTIVE_SHIELD" in upper
or "ACTIVESHIELD" in upper
or "CEBR3" in upper
or "BGO" in upper
or upper.startswith("GEOOPT_S1_PLASTICFULLWRAP")
or upper.startswith("GEOOPT_S2B_CRYOSHELL_PLASTIC")
```

三件被动 scorer 的名称为：

```text
ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm
ActiveShield_S3C_BGO_Kapton_BottomCap_0p3mm
ActiveShield_S3C_BGO_Kapton_TopAnnulus_0p3mm
```

它们因名称含 `ACTIVE_SHIELD` 而被计入 `E_sh`；同一名称还含 `BGO`，也会独立命中谓词中的宽泛 `"BGO" in upper` 分支。retained raw SIM 中存在这些名称下的 `CC HIT`；因此这不是纯文字风险，而是已执行选择的一部分。package-44 的说明文字称 Kapton excluded，与实际谓词不一致。

### 6.2 现有原文（关键句）

EN 306--310：

```text
For the final scintillator active-veto calculation, energy deposits in the active-shield volumes are summed event by event in post-processing. ... an offline deposited-energy veto threshold of 50 keV for the scintillator shield ...
```

EN 1328：

```text
BGO offline anticoincidence & E_sh^(c)<50 keV & Event-by-event sum of recorded energy deposits in the active BGO volumes
```

ZH 125、746：

```text
在最终闪烁体主动 veto 计算中，主动屏蔽体积内的能量沉积在后处理中按事例汇总。
```

```text
BGO 离线反符合 & E_sh^(c)<50 keV & 按事例汇总 BGO 主动体积中记录的能量沉积
```

### 6.3 若保留历史谓词，建议替代文本

这是当前执行合同下不重处理其他模块时可采用的准确文本。

EN Methods：

```text
For the retained O8 results, the 50-keV offline veto uses the frozen string-based volume predicate applied in Step05. The predicate includes the BGO volumes and the retained active-plastic shell, but its broad `ACTIVE_SHIELD` and `BGO` substring rules also include the three passive `ActiveShield_S3C_BGO_Kapton_*` scorer volumes. Accordingly, the reported historical rates are conditional on a BGO+plastic+passively-named-Kapton offline mask; they are not results of a BGO-only or pure-scintillator anticoincidence. The 50-keV value is an event-level post-processing threshold rather than a demonstrated native hardware trigger threshold.
```

ZH Methods：

```text
保留的 O8 结果采用 Step05 中冻结的字符串体积谓词施加 50-keV 离线 veto。该谓词包含 BGO 体积与保留的主动塑料包络，但其中宽泛的 `ACTIVE_SHIELD` 与 `BGO` 子串规则还会纳入三件被动 `ActiveShield_S3C_BGO_Kapton_*` scorer 体积。因此，历史率以“BGO+plastic+名称被动纳入的 Kapton”离线 mask 为条件，并非 BGO-only 或纯闪烁体反符合结果。50-keV 数值是逐事例后处理阈值，不是已经验证的硬件原生触发阈值。
```

EN 1328 / ZH 746 表行建议改为：

```text
Historical offline volume-name veto & E_sh^(c)<50 keV & Frozen Step05 sum over BGO, active plastic, and three passively named ActiveShield/Kapton scorer volumes
```

```text
历史离线体积名称 veto & E_sh^(c)<50 keV & 冻结 Step05 对 BGO、主动塑料和三件名称被动纳入的 ActiveShield/Kapton scorer 的逐事例求和
```

### 6.4 用户必须二选一

1. **保留历史谓词并准确披露（与当前执行范围一致）**：不改数据、不重选其他模块；所有旧/新 line 比较都使用同一冻结谓词，结果明确为条件式。新几何节可以说明设计意图中的主动层是 BGO+plastic，但不得把历史率改称为 pure scintillator veto。
2. **修正谓词后重算选择**：需要用户另行授权对所有 retained event catalog 做统一的纯离线重选和模块化重组；这不需要重新输运粒子，但会改变 prompt、delayed、signal 和 line 的选后率。未获授权前不得静默执行。

无论选择哪一项，**Methods 前缀都必须解除冻结修正**，因为当前稿件把实际三类体积 mask 明确写成 BGO-only/scintillator-only。

## 7. F05：完整 final stack 与信号适用范围

### 7.1 精确冲突位置

- EN 244--252 / ZH 117：把定量构型概括为 initial CsI 与 final BGO，遗漏 final retained BPE/plastic。
- EN 297--304 / ZH 123：称侧入射孔由 Boolean cuts 贯穿 surrounding shells，并称 final 以 BGO 替换 outer active shield。
- EN 331 / ZH 139：称每版 focused signal 与全部 background 在同一 complete detector--cryostat mass model 中输运，未说明 signal 从 Be plane 注入、未穿过外包络上游路径。
- EN 685--706 / ZH 384--396：实际已经写明 EventList 条目位于 Be aperture；这是正确的下游边界，应保留并加强。
- EN 1287--1338 / ZH 720--751：final geometry 正文与表只列 BGO、Al/Kapton、光路和 veto，遗漏 20-mm BPE 与 10-mm active plastic。

### 7.2 现有原文（关键句）

EN 297--304：

```text
These side-entry apertures are generated by Boolean cuts through the surrounding shells. The initial reference geometry used segmented CsI on the sidewalls and end surfaces; the final optimized geometry replaces this outer active shield with BGO.
```

EN 1290--1295：

```text
The final active shield converts the background map into a simple geometry. ... The focused beam still enters through the aligned side aperture. A thin Al/Kapton outer enclosure remains, with no continuous external W layer.
```

ZH 123：

```text
这些侧入射开口均由贯穿周围壳层的布尔切口生成。初始参考几何在侧壁和端面使用分段 CsI，最终优化版本将这层外部主动屏蔽替换为 BGO。
```

ZH 723：

```text
聚焦光束仍通过对准的侧孔进入。外部保留薄 Al/Kapton 包络，不设置连续外部 W 层。
```

### 7.3 建议的完整 final-geometry 文本

以下内容可写入后继稿新增的“屏蔽几何优化”节，并应同步补入 final-geometry 表：

EN：

```text
The final O8 transport geometry is not a BGO-only shield. It retains a 20-mm 5-wt%-borated-polyethylene side shell and 20-mm top/bottom caps, followed by a 10-mm active-plastic side skin and 10-mm top/bottom caps. Inside this outer enclosure, the directionally graded BGO is 40 mm on the side, 30 mm on the bottom, and a 10-mm annulus on the top. The BGO is wrapped by 0.3-mm Kapton and enclosed by 3-mm Al. “No outer W” means that the continuous external W2 shell is absent; the W bottom plate and multihole collimator remain. These dimensions describe transport geometry and pre-relief bookkeeping, not structural qualification.
```

ZH：

```text
最终 O8 输运几何不是 BGO-only 屏蔽。它保留 20-mm、5 wt% 含硼聚乙烯侧壳及 20-mm 顶/底盖，并在其外保留 10-mm 主动塑料侧层及 10-mm 顶/底盖。该外包络内侧的方向分级 BGO 为侧面 40 mm、底部 30 mm、顶部 10-mm 环；BGO 外有 0.3-mm Kapton，最外为 3-mm Al。“无外部 W”仅指连续外部 W2 壳被移除，W 底板与多孔准直器仍保留。这些尺寸是输运几何与 relief 前的核算，不构成结构鉴定。
```

建议 final-geometry 表至少增加四行：

| Element / 部件 | Final setting / 最终设置 |
| --- | --- |
| 5 wt% BPE side | 20 mm; `r=27--29 cm`, `z=-24.5--46.0 cm` |
| 5 wt% BPE caps | 20 mm; `r=0--29 cm`, bottom `z=-26.5---24.5 cm`, top `z=46--48 cm` |
| Active plastic side | 10 mm; `r=29--30 cm`, `z=-26.5--48 cm` |
| Active plastic caps | 10 mm; `r=0--30 cm`, bottom `z=-27.5---26.5 cm`, top `z=48--49 cm` |

### 7.4 建议信号适用范围替代文本

EN 299--304、331 与 1294/1326 的贯穿式表述应改为：

```text
The retained focused-signal EventList is initialized at the Be-window aperture plane and therefore measures detector-side acceptance only downstream of that injection plane. The BGO, Kapton, and Al side volumes contain the aligned optical Boolean cut, whereas the retained BPE/plastic primitives contain NF2 support reliefs but no corresponding named RectWindowCut, pump-line relief, or top central-service subtraction. The present signal result therefore does not establish transmission through the complete BPE/plastic outer envelope, and no claim of an uninterrupted full-envelope optical path is made.
```

ZH 对应文本：

```text
保留的聚焦信号 EventList 在 Be 窗孔径平面初始化，因此只测量该注入平面下游的探测器侧接受。BGO、Kapton 与 Al 侧壁含有对准的光学布尔切口；保留的 BPE/plastic 原语只有 NF2 支撑 relief，没有对应的命名 RectWindowCut、泵管 relief 或顶部中心服务切除。因此，现有信号结果没有闭合完整 BPE/plastic 外包络的透过率，本文不声称存在贯穿完整外包络的连续光路。
```

### 7.5 用户决策与边界

- **完整 stack 的新增说明和表行可以在后继新节/Results 完成**，无需修改 M04 本体。
- 但 EN 297--304 / ZH 123 的“贯穿 surrounding shells”与 final-only-BGO 概括位于冻结前缀；若要把后继稿标为 submission-ready，仍须解除冻结并采用上面的限定文本。
- 在当前只允许新输运 PARMA 单能大气线的范围内，上游信号透过保持 `UNCLOSED`。本 blocker 不触发 signal 或全链重跑；只要求删除/限制超过现有 Be-plane EventList 证据的论断。

## 8. 建议的用户批准语句

若用户同意在未来隔离后继稿中纠正，而继续保持 M04 永久只读，可采用以下批准语句：

```text
保持 M04 EN/ZH、PDF 和图件逐字节不变；允许只在隔离的 M05/后继副本中解除冻结，按 F01--F05 修正 Methods 与 Results。F04 选择采用“保留并准确披露历史谓词”或另行明确授权纯离线重选。除已授权的 PARMA 510.99895-keV 单能大气线模块外，不新增任何 continuum、prompt、delayed、signal、其他粒子或全链输运。
```

若用户不解除后继稿前缀冻结，则应记录：

```text
后继稿只作为审阅增补稿；不得标记 submission-ready，不得在后文用澄清句掩盖冻结 Methods 中与 PARMA、gamma 能轴、延迟源键、active-veto mask 或外包络光路相冲突的定义。
```

## 9. 本提案的证据入口

| 主题 | 权威入口 |
| --- | --- |
| M04 冻结合同 | `engineering/m04_validation_geometry_handoff_20260810/SESSION_BOOTSTRAP.md` |
| 总体稿件复核 | `engineering/m04_validation_geometry_handoff_20260810/00_review/PROJECT_AND_M04_REVIEW.md` |
| claim-to-source 映射 | `engineering/m04_validation_geometry_handoff_20260810/00_review/manuscript_claim_to_source_matrix.csv` |
| PARMA source-level closure | `engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/data/parma_line_closure.json` |
| day-15 authority | `engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/config/day15_environment_authority.json` |
| legacy photon-axis/line-term audit | `engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/response/O8_PROMPT_GAMMA_LINE_DEDUP_AUDIT.md` |
| delayed source builder | `code/tools/build_fix5_1of10_exactpos_delayed_source.py` |
| frozen O8 selection predicate | `engineering/geometry_optimization_20260704/44_s3d_o8_all8_activation_20260713/code/run_s3d_o8_all8_step05.py` |
| final O8 geometry | `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo` |
| Be-plane EventList boundary | `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/step09_optics_bridge_summary.json` |

## 10. 验收边界

- 本提案不自动修改任何论文。
- 本提案不把 source-level `PASS_PARMA_511_SOURCE_LEVEL_ONLY` 误写成 detector-level 或 manuscript-number PASS。
- 本提案不把旧 photon line-term 的 `Broad/W511 delta=0` 误写成对整个 continuum 的物理验证。
- 本提案不把字符串谓词的历史一致性误写成正确的 scintillator-only 实现。
- 本提案不把 Be-plane 下游 signal acceptance 误写成完整 BPE/plastic 外包络透过率。
- 本提案不产生任何要求全量推倒重来或重跑其他模块的含义。
