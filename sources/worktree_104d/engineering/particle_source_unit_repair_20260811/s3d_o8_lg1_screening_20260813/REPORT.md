# S3d-O8 本底来源与优化方向报告

日期：2026-08-14  
状态：`SOURCE_DIAGNOSIS_COMPLETE__LG1_FIRST_PASS_SMOKE_COMPLETE__FULL_CHAIN_TARGET_NOT_YET_CLOSED`

## 技术摘要

S3d-O8 当前共同响应 W2（510.58–511.42 keV）本底为
`0.08832268 cps`：瞬发 `0.03384293 cps`，day-15 延迟活化
`0.05447975 cps`。瞬发最终率只由 2 个 Monte Carlo 事件支撑，延迟率的
加权有效样本量约为 28.75，因此中央值可用于确定优化方向，但不能当作已经
收敛的工程预算。

来源诊断给出两个必须同时处理的通道：

1. **瞬发泄漏是内层被动高 Z/中高 Z 构件中的成对产生。** 两个最终事件均为
   4–6 MeV 入射 gamma，在内层 Nb 或 mixing-chamber Cu 中产生 e+/e−，正电子
   湮没后的一个 511 keV gamma 被 TES 全吸收。它们在现有 3 个 BGO 和 3 个
   plastic 精确主动体积中的沉积均为零，降低 50 keV veto 阈值不能解决“零沉积”。
2. **延迟本底是近 TES Cu/Nb/MuMetal 活化与几何耦合的共同结果。** n 和 p
   生产族分别占选后 delayed 的 43.46% 和 39.19%；Cu-62、Cu-64、Cu-61 合计
   占 64.24%。MXC 50 mK 冷盘、Nb 内筒、MuMetal 外筒、L0 Cu 深盘和 Cu can
   bottom 是首要空间源。

仅用信号先验冻结的可实现选择（像素中心能量质心 `r<=1.35 cm`，最深命中层
`<=L3`）保留 90.60% 最终信号，使中央情景 F3 从 `6.92e-5` 约降至
`5.15e-5 ph cm-2 s-1`。把关键 pair-host 结构做成有效能量读出的事件记录筛查
进一步给出 `2.24e-5` 的设计上限估计，已经跨过 `3e-5` 目标；这说明方向是对的，
实际工程需要把该读出能力实现出来。

第一代实体候选 LG1 是一个前端开放、位于 Nb 内筒内的 5 mm BGO 侧套加
3 mm 后环，总解析质量 `0.56310 kg`。16-job、8192-event 的新输运 smoke 表明：

- 对 4.15 MeV 的 Nb/MuMetal 根路径，三个副本中出现的 5 个“原六主动体漏过且
  raw-W2”事件在 80 keV 仍被 LG1 截获 5/5；
- 对 5.77 MeV 的 mixing-chamber Cu 根路径，出现的 2 个同类事件被截获 0/2；
- focused first-1000 的 raw-W2 为 826（基线）对 817（LG1），输运损失约 1.1%；
  LG1 与候选中幸存的 817 个 raw-W2 无符合，所以额外 veto 没有继续误杀这些事件。

因此 LG1 证明了局部 gamma guard 的可行方向，但其开放轴向/薄径向厚度未解决
冻结选择后仍存活的 mixing-chamber Cu 路径。下一迭代必须把“源宿主读出或减耦”
作为主线，而不是只把现有 BGO 继续均匀加厚。

## 1. 范围、定义与证据等级

- `W2`：measured TES total energy 510.58–511.42 keV。
- 现有共同选择：0.3 keV measured-pixel threshold、0.42 keV FWHM、现有主动 veto
  50 keV、随后 Step05 Compton/FoV。
- `F3`：当前 mission analytic-family-scalar scenario 的 20-day 3-sigma flux；它是
  统一比较口径，不是最终多点输运灵敏度 authority。
- **观测级**：直接来自现有 corrected-keV SIM、catalog、lineage 和新 LG1 SIM。
- **设计上限级**：在不改变已有输运的前提下，把指定被动体的 CC-HIT 能量当作
  可读出 veto；用于量化“若实现读出，最多能得到什么”，不等于某个器件已实现。
- **工程推断级**：结合文献提出的实现路线，必须再过几何、热、磁、时序、活化和
  完整八族输运门。

## 2. 瞬发本底从哪里来、为何没被屏蔽

### 2.1 总体筛选行为

S3d-O8 的 261 个 measured-W2 pre-veto 事件中，258 个被现有主动层拒绝，3 个
主动层精确能量为零而漏过；其中 1 个多像素事件被 Step05 拒绝，剩下 2 个成为
最终瞬发事件。252/261 可由 track parentage 直接闭合为
`pair/conv -> e+ -> annihilation -> 511 gamma -> TES`，另 3 个有正电子/湮没祖先，
6 个复杂 shower 因记录前代缺口未完全闭合。

这说明外层 BGO/plastic 对绝大多数事件有效，残余问题不是阈值不够低，而是中性
gamma 在主动体中没有相互作用、随后在主动层以内的被动结构中成对产生。原始块
没有可用的主动层 ENTR/EXIT 边界记录，因此不能仅凭这 3 个事件判断它们究竟从
开口进入，还是穿过主动材料但未相互作用。

### 2.2 两个最终事件

| 事件 | 入射 gamma | 起点与方向（global） | 首个关键过程 | 511 keV 到 TES | 现有主动能量 |
|---|---:|---|---|---|---:|
| ID 3883 | 4148.29 keV | `(-37.97,-13.86,-31.08)`, `(0.7695,0.2715,0.5781)` | Nb 内磁屏蔽筒中 PAIR；邻近 MuMetal 湮没 | L2 单像素，510.909 keV measured | BGO=0, plastic=0 |
| ID 19932 | 5768.82 keV | `(62.49,-16.04,-0.23)`, `(-0.9648,0.2602,0.0393)` | `DR_MixingChamber_Cu` 中 PAIR 和湮没 | L2 单像素，511.019 keV measured | BGO=0, plastic=0 |

第三个 veto 漏过事件 ID 8081 是 6345.94 keV gamma 在 Nb 中 PAIR、在 L0 Cu 深盘
附近湮没，产生两个 TES 像素（441.4+69.6 keV），因此由 Step05 拒绝。

信号先验冻结选择恰好去掉 ID 3883、保留 ID 19932。故实体 guard 的关键检验不是
能否再次拒绝已经被空间/层深选择去掉的侧向事件，而是能否处理 mixing-chamber Cu
产生、又落入信号足迹的 511 keV gamma。

## 3. 延迟活化本底由什么粒子和材料产生

### 3.1 生产粒子族

| 入射生产族 | delayed W2 (cps) | 占 delayed | day-15 ground inventory (Bq) | 选后耦合代理 (cps/Bq) |
|---|---:|---:|---:|---:|
| n | 0.0236791 | 43.46% | 348.222 | 6.80e-5 |
| p | 0.0213511 | 39.19% | 762.539 | 2.80e-5 |
| alpha | 0.00448663 | 8.24% | 280.414 | 1.60e-5 |
| e+ | 0.00382994 | 7.03% | 3.75485 | 1.02e-3 |
| gamma | 0.000784331 | 1.44% | 8.17012 | 9.60e-5 |
| e- | 0.000346659 | 0.64% | 0.780764 | 4.44e-4 |

p 产生的总活度最大，但 detector-selected W2 中 n 与 p 接近，说明“活度大”不能
替代 detector coupling。mu- 有 2 个选后事件，mu+ 中央计数为零；后者不能解释为
物理零。

### 3.2 母核素与空间源

| 母核素 | delayed W2 (cps) | 占 delayed | 加权有效样本量 |
|---|---:|---:|---:|
| Cu-62 | 0.0155902 | 28.62% | 10.92 |
| Cu-64 | 0.0124196 | 22.80% | 7.17 |
| Cu-61 | 0.00698845 | 12.83% | 3.70 |

三种 Cu 核素合计 `0.0349983 cps`，占 delayed 64.24%。Cu-64 的 12.701 h 半衰期和
beta-plus 分支使其天然产生 511 keV 湮没光子；Cu-61/62 同样通过正电子衰变进入
该拓扑。source parent 必须与 SIM 中 radioactive-decay daughter 区分。

| 源体积 | delayed W2 (cps) | 占 delayed |
|---|---:|---:|
| MXC 50 mK cold plate | 0.0167715 | 30.78% |
| Nb inner magnetic cylinder | 0.00780860 | 14.33% |
| MuMetal outer cylinder | 0.00776545 | 14.25% |
| L0 deepest Cu disk | 0.00584951 | 10.74% |
| Cu can bottom | 0.00401569 | 7.37% |

前五项合计约 77.5%。材料聚合为 other_internal 50.24%、cold_plates 35.33%、
outer_mechanics 14.25%。这清楚地把优化焦点指向 TES 邻近 Cu、Nb、MuMetal 的质量、
立体角和读出，而不是只优化远端外壳。

### 3.3 统计边界

49 个 exact `family x parent x volume` 路径中，25 个单事件路径贡献 delayed 中央率的
67.99%；p 的 7 条非零路径全部是单事件。当前 source realization 相对 full inventory
的 joint total-variation 约为 p 0.169、n 0.167、alpha 0.165。所以下一轮必须优先补强
p/n/alpha 的源混合与高权重路径，不能据当前 1–3 个事件的细排序直接加工硬件。

## 4. 目标预算

当前 S3d-O8 中央情景：

- `Aeff0 = 15.04170 cm2`
- `B0 = 0.08832268 cps`
- `F3_0 = 6.92375e-5 ph cm-2 s-1`

同一情景下近似满足

`F3/F3_0 = sqrt(B/B0) / (Aeff/Aeff0)`。

因此若采用冻结选择的 `Aeff = 13.62852 cm2`，最低目标 `F3<=3e-5` 要求
`B<=0.01362 cps`。冻结后当前 `B=0.04012714 cps`，仍需进一步降低至少 66.1%。
即使 prompt 完全消失，delayed 的 `0.02320567 cps` 仍超预算；即使 delayed 完全
消失，prompt 的 `0.01692146 cps` 也超预算。两条链必须一起优化。

| 方案/读出策略 | Aeff (cm2) | B (cps) | 相对基线 S/sqrt(B) | F3 同口径估计 |
|---|---:|---:|---:|---:|
| 当前基线 | 15.04170 | 0.08832268 | 1.000 | 6.92375e-5 |
| 冻结像素中心+层深选择 | 13.62852 | 0.04012714 | 1.344 | 5.14899e-5 |
| 冻结选择 + pair-host 理想能量读出（1 keV） | 13.62852 | 0.00758334 | 3.092 | 2.23574e-5 |
| 冻结选择 + pair-host/近TES-Cu 联合读出上限（1 keV） | 13.62852 | 0.00003004 | 49.13 | 1.40536e-6 |

最后一行是有意给出的优秀设计上边界：它说明来源信息足够强，并不宣称现有硬件已经
拥有该读出。最低 promotion budget 建议设为 `Aeff>=13.35 cm2`、
`prompt+delayed<=0.0131 cps`；拉伸目标 `F3<=2e-5` 对应总本底约 `<=0.0058 cps`。

pair-host 读出的阈值不是次要细节。按同一 mission family-scalar 时间链独立重算：

| pair-host 阈值 | frozen 后总本底 (cps) | F3 约值 | 是否跨过 3e-5 |
|---:|---:|---:|---|
| 1/5 keV | 0.00758334 | 2.23574e-5 | 是 |
| 50 keV | 0.01069357 | 2.65657e-5 | 是 |
| 80 keV | 0.01378879 | 3.01767e-5 | 否，略高 |

因此真实实现应把有效阈值争取到 `<=50 keV`，而不是把 80 keV 当成足够。这个
50→80 keV 跃迁又受两个 proton-family delayed 事件控制：其结构沉积约
45.34/52.02 keV、每个权重约 `0.003050 cps`；A5 残余 delayed 的加权有效样本量
仅约 6.37。阈值排序是强设计提示，不是已经收敛到末位数字的工程预测。按 mission
时间链，frozen 信号对应的 20-day 本底预算为 22,224.9 counts；A80 为 22,487.5，
超预算约 1.18%。

## 5. LG1 实体候选与真实 smoke

LG1 在原 O8 GEO/DET 后只追加两个 BGO 体积和 scorer，剥离 patch 后原文件逐字节
一致。侧套为 `x=-3.55..3.10 cm, r=3.10..3.60 cm`，后环为
`x=3.70..4.00 cm, r=1.85..3.60 cm`；负 X 光学入口开放。静态解析质量
`0.5630968 kg`，最小记录净空为 1.0–2.4 mm 量级。显式 Cosima overlap/load
检查退出 0；随后 16 个 write-once A/B jobs 全部通过，8192 事件、总 SIM 18.1 MB。

### 5.1 信号

focused first-1000 中，基线/候选 TES-hit 为 978/962，raw-W2 为 826/817。
候选的 817 个 raw-W2 在 1–80 keV 阈值下均与 LG1 无符合；因此第一轮看到的是
BGO 改变输运造成约 1.1% raw-W2 净损失，而不是 veto 对最终 raw-W2 的额外误杀。
配对不一致计数为 142 对 133，精确检验 `p=0.63`，未显示显著信号损失。
不过新增材料会改变后续随机历史，共 seed/事件 ID 不能把 A/B 解释为逐轨迹因果配对；
first-1000 也不能替代全 37194 EventList 和共同 TES response。

### 5.2 已知瞬发根路径

| serialized root | 候选 raw-W2 且原六主动体漏过 | LG1>=80 keV | 解释 |
|---|---:|---:|---|
| 4148 keV / Nb-MuMetal | 5 | 5 | 侧/后局部 guard 对该路径有力 |
| 5769 keV / mixing-chamber Cu | 2 | 0 | 当前薄套未可靠截获轴向/源侧路径 |
| forced back-to-back 511 | 1 | 0 | 24-event 几何 cassette 支持仍很低 |

5/5 与 0/2 都是小分母；它们只回答这两条定向 cassette 的条件截获，不是天空
gamma 拒绝率。尤其 5/5 的 95% 二项下界仍很宽。LG1 也尚未做新增 BGO 自身的
BUILDUP/inventory/delayed 闭环。

把所有旧六主动体未触发事件作为较宽分母，在 50 keV 下 LG1 对 4.15 MeV
Nb/MuMetal cassette 的条件命中为 `94/301=31.2%`，对 5.77 MeV
mixing-chamber Cu cassette 只有 `6/118=5.08%`。forced-511 只覆盖六个预设方向，
并未复现两个原事件的真实 ANNI 方向；它只能用于覆盖 smoke。上述对比进一步说明：
保留 LG1 的有效侧/后段，但当前 LG1 本身不应 promotion。

## 6. 文献与类似工程的约束

1. **Hitomi SXS / XRISM Resolve**：50 mK 微量热计下方使用 0.5 mm Si anti-co，
   Hitomi 的触发阈值约 10 keV、正式 coincidence 选择约 30 keV/1 ms；Resolve 保留
   能量和时间供地面优化。这支持“近 TES、完整下传能量/时间、离线扫阈值”，但
   薄 Si 主要抓穿越带电粒子，不能单独拒绝在 Cu/Nb 中生成后进入 TES 的 511 gamma。
   [Hitomi SXS](https://academic.oup.com/pasj/article/70/2/18/4969724)，
   [XRISM Resolve POG](https://heasarc.gsfc.nasa.gov/docs/xrism/proposals/POG/Resolve.html)
2. **Athena X-IFU CryoAC**：4 像素、约 1 cm2/像素、距主阵列小于 1 mm；500 um Si
   原型在 50 mK 的总冷端耗散约 10 nW，5-sigma 阈值 1.4 keV。X-IFU 研究还发现
   Nb 产生而不穿过 CryoAC 的次级电子需要约 250 um Kapton 低 Z liner；这一经验
   值得独立测试，但原问题是 2–10 keV 电子/荧光，不能直接外推到 511 gamma。
   [CryoAC prototype](https://link.springer.com/article/10.1007/s10909-023-03034-5)，
   [Athena background review](https://arxiv.org/abs/2101.02526)
3. **INTEGRAL/SPI**：91 块分段 BGO ACS 保留观测孔径，低阈值约 75 keV，在轨
   对 Ge 总本底约有 20 倍抑制；工程手册同时警告 BGO 过厚会增加次级中子。
   可迁移的是分段、侧/后覆盖、阈值和厚度共同优化，而不是无条件增加 BGO。
   [SPI Observer's Manual](https://integral.esac.esa.int/AO7/AO7_SPI_om.pdf)，
   [SPI in-flight performance](https://arxiv.org/abs/astro-ph/0310793)
4. **COSI balloon**：现代 bottom-up 本底工作把时变环境、46 天活化 buildup、衰变、
   veto、dead time、串扰和重建放进同一链；即使如此，在 0.1–1.6 MeV 仍需经验
   修正后才达到约 10–20% 数据一致性。这支持本项目必须对新增 BGO 重走完整活化链。
   [COSI background paper](https://doi.org/10.3847/1538-4357/add6a0)
5. **低温 BGO 可行性边界**：46 g BGO 已在 20 mK 工作；更大的一块
   `5x5x5 cm3, 891 g` BGO 已在 10 mK 运行，所以 0.563 kg 不能仅因质量被否决。
   但 6 K BGO 的长衰减分量约 138 us，薄套筒的航天振动、热连接、读出耗散、
   磁兼容和误符合仍未被这些地面量热实验验证。
   [46 g BGO](https://doi.org/10.1016/j.optmat.2008.09.016)，
   [891 g BGO](https://doi.org/10.1088/1748-0221/7/10/P10022)，
   [low-temperature decay](https://doi.org/10.1016/j.nima.2008.07.008)
6. **Cu-64**：IAEA 给出 `Cu-63(n,gamma)Cu-64` 及 Cu-64 的 12.701 h 半衰期和
   beta-plus 分支，直接说明 Cu 与中子环境会形成 511 keV delayed 通道。
   [IAEA TRS 473](https://www-nds.iaea.org/publications/tecdocs/technical-reports-series-473.pdf)

## 7. 优化优先级

### P0：把 pair-host 读出能力变成真实硬件

这是唯一已经在事件记录上把中央估计推过 `3e-5` 的方向。应并行比较三种实现：

- **源侧分段 gamma guard（LG2）**：保留 LG1 的侧/后覆盖，针对
  `DR_MixingChamber_Cu -> TES` 视线增加局部厚扇区或多层分段，而不是均匀加厚；
  中央光束包络必须由独立 optics calibration 冻结；第一张定向卡应复现原
  event 19932 的真实 ANNI 逃逸方向。
- **减少/移开高耦合 pair-host 质量**：对 mixing-chamber Cu、Nb/MuMetal 和近 TES Cu
  逐体积做质量/立体角灵敏度扫描。热学允许处优先改成环形、开孔或移到低耦合位置；
  材料替换必须比较完整八族活化，不能凭材料名称决定。
- **宿主本体或贴面低热容读出**：把关键结构分段并配置 phonon/semiconductor 标签；
  大块 Cu 的热容和脉冲时间常数可能使 keV 阈值不可行，必须先做热模型和台架门。

### P1：压低 Cu delayed inventory 与 detector coupling

- 首先处理 MXC plate、L0 disk、Cu can bottom 和近 TES rings；目标不是简单减少总 Cu，
  而是减少“生产率 x beta-plus 分支 x TES 立体角/耦合”。
- p/n/alpha 三族必须共同优化。20 mm BPE 的既有边界 fold 对 Cu-61/62/64 只有约
  10–16% inward-current 改善，且不含绕行、级联和位置耦合；它不能单独支撑目标。
- 对 borated polyethylene、B4C/Li 类吸收层或分级 moderator 的任何选择，都必须先
  解决捕获 gamma、质量和自身活化，随后重走 BUILDUP 链。

### P2：近 TES Si CryoAC 与 Nb 低 Z liner

这两项有成熟项目先例、质量和新增活化风险较低，适合与 P0 并行。它们最可能减少
带电次级和 Nb 荧光，不应被包装成对 mixing-chamber 511 gamma 的替代方案。

### P3：读出与软件联合优化

- 固定像素中心、层深和光轴标定，不用 science/background 重新拟合中心。
- guard 必须下传每段能量和时间，预留 1/5/10/20/50/80 keV 与 coincidence-window
  扫描；把 accidental veto、pile-up、dead time 纳入 signal Aeff。
- 保留 Step05，但当前单像素 mixing-chamber 事件说明仅靠 Compton/FoV 不够。

## 8. 下一阶段验证门

1. 对 LG2、Cu-reduced/relocated、Si-CryoAC+liner 至少三类候选做独立静态和
   Cosima overlap/load；任何候选不覆盖原 authority。
2. 用完整 37194 focused EventList 做 fresh-seed A/B，共同 TES response 后要求
   `Aeff>=13.35 cm2`；另外加入 pointing、guard coincidence 和 dead-time 折损。
3. prompt 不能靠 25k broadband smoke 判断 W2；现有 gamma authority约 3.21M
   primaries 仅 2 个最终事件。应使用定向/importance cassette 验证机制，再用足够
   统计量的 corrected-keV 八族 production 恢复率。
4. delayed 必须重走 `BUILDUP -> day-15 inventory -> source -> delayed -> common response`，
   包括新增 BGO/Si/liner 的自身活化与 NUBASE ground-state correction。
5. promotion 最低门：中央 `prompt+delayed<=0.0131 cps`、`F3<=3e-5`；拉伸门：
   `B<=0.0058 cps`、`F3<=2e-5`。同时要求主要路径不再由 1–3 个高权重事件决定。
6. 工程门：冷端耗散、热恢复时间、阈值、误符合死时间、磁兼容、线缆、振动、
   质量与装配公差全部通过；低温 BGO 的实验质量先例不能替代这些门。

## 9. 可复现入口

- 几何、builder、validator、smoke plan：本目录 `README.md`、`code/`、`data/`。
- LG1 诊断：`LG1_SMOKE_DIAGNOSTIC.md` 与 `data/lg1_smoke_diagnostic.json`。
- write-once SIM：
  `runs/particle_source_unit_repair_20260811/s3d_o8_lg1_screening_20260814_v1/`。
- corrected-keV 来源、inventory、lineage 与 mission authority：
  `engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/`。
- 信号冻结辅助：`/tmp/s3d_o8_frozen_policy_pass.json`，SHA256
  `3c711b86df8d3d74188f226ac3db46b227e5d9cb84f81f53a60bb65273bf991f`。
- 结构读出筛查辅助：`/tmp/s3d_o8_virtual_guard_screen/summary.json`，SHA256
  `7d66d8521ab6c0217b393bd89a818c9926d123245511f4d7be7e35b6ff40b60e`。

## 结论

S3d-O8 的优化不是“再加一层外屏蔽”问题，而是**内层 pair-host 的可读出性/减耦**与
**近 TES Cu 活化的生产率和几何耦合**问题。事件级证据已经给出一条跨过 `3e-5` 的
读出目标；LG1 又用新输运证明局部 BGO 对 Nb/MuMetal 路径有效，但同时暴露了
mixing-chamber Cu 路径这一决定性缺口。下一步应保留 LG1 的有效侧/后段，集中设计
源侧 LG2 与 Cu 减耦，并以完整八族 prompt+activation+delayed 共同响应闭环决定最终
工程方案。
