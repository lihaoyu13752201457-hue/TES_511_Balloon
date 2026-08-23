# M05 SG3/SH3 当前 Session 总交接

日期：2026-08-23  
状态：`CURRENT_ENTRY__READ_THIS_FIRST`  
建议模型：`gpt-5.6-sol`，reasoning effort=`xhigh`

## 0. 唯一入口与绝对路径

后续 Session 以本文件为唯一当前入口：

`/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/M05_CURRENT_SESSION_HANDOFF_20260823.md`

当前 `M05NEW` 是 `ebb2` 工作树中的未跟踪目录。新 Session 即使运行在
`/home/ubuntu/TES_511_Balloon` 或另一个 Codex 工作树，也必须按本文件给出的绝对路径读取
当前稿件；不得因为自己的相对路径中缺少文件，就改读主项目中的旧稿或同名历史文件。

本文件用于复习、审稿和后续有边界的修订。默认模式是只读复习；没有用户新的明确授权时，
不得修改论文、启动模拟或扩展研究范围。

## 1. 三份交接文件的角色

1. `M05_CURRENT_SESSION_HANDOFF_20260823.md`：当前唯一入口，记录已完成稿、证据等级、已知
   问题和新 Session 的阅读顺序。
2. `M05_TEMPLATE_DATA_REPLACEMENT_HANDOFF_20260821.md`：历史执行合同。它准确记录了母版、
   10 个图位、7 个表位、禁止事项和数据替换边界，但其中的“开始复制和替换”步骤已经完成，
   不得再次执行。
3. `NEW_PAPER_SESSION_HANDOFF_20260821.md`：已废止的错误交接审计记录。不得执行其“新写一篇
   论文”、新 scaffold 或新参考文献库指令。

严禁读取或复用错误任务 `01a02314-a50b-78d2-bb8c-b43ffa350704` 的产物。

## 2. 当前论文成品

唯一当前英文稿：

- `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/balloon511_ea_draft_en_sg3_sh3_revision_20260821.tex`
- `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/balloon511_ea_draft_en_sg3_sh3_revision_20260821.pdf`

唯一当前中文稿：

- `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/balloon511_ea_draft_zh_sg3_sh3_revision_20260821.tex`
- `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/balloon511_ea_draft_zh_sg3_sh3_revision_20260821.pdf`

当前编译成品为英文 25 页、中文 24 页，均为 A4；两版各保留 10 个图形插入和 7 个表位。
图均在 `M05NEW/figures/`。这四个文件已经完成 SG3/SH3 数据替换，不再执行一次“复制母版
再替换”的流程。

四个 2026-08-10 `pre_framework_rewrite` 母版仍是结构和成熟文字来源，必须只读：

- `core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_en_m04_atm511_revision_20260804_pre_framework_rewrite_20260810.tex/.pdf`
- `core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_zh_m04_atm511_revision_20260804_pre_framework_rewrite_20260810.tex/.pdf`

不得修改或删除母版。不得把当前稿重新压缩成短论文，不建新 scaffold，不重建参考文献库。

## 3. 新 Session 的强制阅读顺序

### 第一层：任务边界和全文

1. 仓库根目录 `AGENTS.md`。
2. 本文件全文。
3. `M05_TEMPLATE_DATA_REPLACEMENT_HANDOFF_20260821.md`，只用于理解母版与替换边界，不重做
   已完成步骤。
4. 当前英文 TeX 和 25 页 PDF，必须完整阅读。
5. 当前中文 TeX 和 24 页 PDF，必须完整阅读；检查物理含义和内部说明口吻是否与英文一致。

### 第二层：当前数据与几何口径

6. `M05NEW/README.md`：了解数据包原始状态；其中 `PASS` 表示内部闭合，不等于外部物理验证。
7. `M05NEW/M05_PAPER_DATA_TABLE.csv`：论文槽位数值入口。
8. `M05NEW/REFERENCES.md`：槽位到来源文件的索引。
9. `M05NEW/M05NEW_VALIDATION.json` 和 `SG3B_OPTV3_COMPARISON.json`：内部数值一致性。
10. `M05NEW/MXC_BPE_PLASTIC_REVIEW.md`：SG3/SH3 几何因果和 BPE/plastic 边界。
11. `engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/README.md`：SH3 几何、机械边界和
    detector declarations。
12. `engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820/README.md`：
    SG3 自有信号、扩统计背景和匹配任务结果。
13. `engineering/geometry_optimization_20260815/66_m05new_mxc_bpe_veto_review_20260821/README.md`：
    同尺度剖面与 BPE/plastic 上限。

### 第三层：只针对争议点深化

14. 源模型：
    - `engineering/particle_source_unit_repair_20260811/README.md`
    - `engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json`
    - `engineering/particle_source_unit_repair_20260811/data/static_validation.json`
15. SH3 事件和时间线只先读摘要与小表：
    - `DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/summary.json`
    - `DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/direct_cutflow_totals.csv`
    - `DEEPSEEK_CODE/outputs/05_mature_timeline_m05_fixed_20260820/summary.json`
    - `DEEPSEEK_CODE/outputs/05_mature_timeline_m05_fixed_20260820/mission_timeline_81nodes.csv`
16. Laue 外部/独立验证边界：
    - `engineering/ea_peer_review_m08_laue_validation_20260715/README.md`
    - `engineering/ea_peer_review_m08_laue_validation_20260715/reports/M08_VALIDATION_REPORT_ZH.md`
17. 大气 511 keV 线的历史独立模块与限制：
    - `engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/response/wp2_final_180m_20260811/PARMA_ATM511_CONCLUSION.md`

初次复习禁止递归打开全部 job catalog、大型 SIM、完整 NPZ 或哈希清单。只有一个具体物理
问题无法从摘要、CSV 和正文回答时，才读取对应的最小数组或事件记录。

## 4. 已完成并可作为内部结果使用的部分

以下是当前匹配分析的内部结果，不代表整机外部实验验证：

- SG3 最终有效面积：`15.12324 +/- 0.04492 cm2`。
- SH3 最终有效面积：`15.08544 +/- 0.04503 cm2`，为 SG3 的 `99.75%`。
- SG3 day-15 最终本底：`0.05128019 cps`。
- SH3 day-15 最终本底：`0.009280 cps`，为 SG3 的约 `18.10%`。
- SG3 20 d Gaussian 3 sigma Fmin：`(5.4058 +/- 0.4014)e-5 ph cm^-2 s^-1`。
- SH3 20 d Gaussian 3 sigma Fmin：`(2.2294 +/- 0.2086)e-5 ph cm^-2 s^-1`。
- 当前匹配口径下 Fmin 改善约 `2.43` 倍。
- selected delayed 中 `DR/MXC + staged cold plates` 占比由 `32.18%` 降至 `3.92%`。
- 当前内部数据检查为 `21/21 PASS`；它证明表、源文件、事件目录和时间线之间按既定合同
  一致，不证明源模型、光学、BGO 硬件或整机本底已被外部实验验证。

论文主线仍是：SG3 参考几何定位冷盘/MXC 邻近本底耦合，SH3 把 TES 横向移入侧烟囱并以
BGO 主动反符合降低科学窗本底。BPE 和外置塑料不是当前主优化。

## 5. 当前不能宣称“完全物理闭合”的问题

独立只读审稿任务 `01a024de-763a-70e1-a0ae-72a594959892` 完整阅读了四份成品，裁决为
`NOT CLOSED / Major revision`。这是审稿意见，不自动取代项目数据；后续 Session 应逐条判定
“确实需补证”“只需收窄表述”或“已有本地证据可部分回答”。主要问题如下。

### 5.1 整机范围与遗漏本底

当前本底质量模型主要覆盖探测器和低温系统。Laue 晶体/支撑、吊舱/平台以及视场内天体或
弥散光子未完整进入总本底，却在标题、摘要和结论中被外推为整台球载 Laue 望远镜的绝对
灵敏度。最小处理可以是把结论明确限定为“探测器—低温系统预算下的条件式/理想下限”；
只有坚持整机绝对灵敏度时，才需要补入遗漏本底的约束。

### 5.2 银河中心目标与固定 45 度参考轨迹

稿件使用纬度约 `+34 deg`、固定 `45 deg` 仰角并持续在源的参考折叠。银河中心赤纬约
`-28.9 deg`，在该纬度最大仰角仅约 `27 deg`。当前数值可作为抽象的 45 度轴上窄线参考，
不能直接称为真实银河中心 20 d 指向预测。该问题通常只需收窄科学声明，或重做可见性、
大气透过和在源时间折叠，不必重跑探测器输运。

### 5.3 零计数高权重分量的总不确定度

Table 6 有多个最终零计数分量，单分量 Garwood 上限较大；当前
`sqrt(sum w_i^2)` 对零条记录给出零观测方差。应检查总本底区间是否需要联合 Poisson/似然
或明确的保守上限，而不是仅报告中心值的 delta-method 误差。只有联合区间仍不可用时，才
考虑对少数高权重分量增加定向统计。

### 5.4 BGO 50/80 keV 接口

SH3 分析使用 `50 keV` 离线 BGO 门，几何 detector declaration 给出 `80 keV` native
trigger。必须说明 TES 触发时 BGO 是否连续读出或被强制读出，从而保留 50--80 keV 沉积。

2026-08-21 的只读事件目录阈值重放显示：相对 50 keV，70 keV 使最终率增加 `1.84%`、
Gaussian Fmin 增加 `0.92%`；80 keV 使最终率增加 `3.75%`、Fmin 增加 `1.86%`。因此
50--80 keV 的性能结论数值上较稳健，但硬件读出逻辑仍需定义。该重放没有新输运，也没有
写入论文。

### 5.5 Laue 光学只部分闭合

M08 验证状态为 `PARTIAL_PASS`：反射率 `R` 在 65/65 点通过，步长收敛通过；完整 R/T/A
只有 29/65 点通过，最大 T/A 系统差约 3.75 个百分点。更重要的是，当前 production 等价
`gaussian_plane` 点源 `d90=0.406226 cm`，比 HEART 参考宽 `51.93%`；经验证的
`gaussian_outgoing` 得到 `d90=0.265752 cm`，与解析和 HEART 均在约 1% 内。

18 mm footprint 的 Be 门通过率变化很小，所以当前有效面积中心值预计变化不大；但 PSF
不能宣称闭合。当前 SG3/SH3 信号源仍追溯到保留的 Step09 EventList：

`stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat`

完成 production 出射角修正并重建 EventList 前，Aeff 可称部分验证，PSF 不可称最终验证。

### 5.6 大气 511 keV 线形是当前最需要独立判断的源问题

当前 corrected-keV broadband gamma 用 `IP LIN`，511 keV 附近只有约 `449.65` 和
`566.08 keV` 两个相邻节点：

`engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/gamma_bin00_theta18.19_pdf.spectrum`

它保留了湮没隆起的总面积，却把线形摊在约 116 keV 的区间内。2026-08-21 的只读源级积分
得到当前 W2 (`510.58--511.42 keV`) 表示的光子通量约
`1.4810e-3 ph cm^-2 s^-1`；PARMA day-15 单线全空间通量为
`0.1665155 ph cm^-2 s^-1`。若采用 HEAO-3 大气线 FWHM `2.29 keV` 并与 `0.42 keV`
TES 响应卷积，约 `32.8%` 的线光子进入 W2，对应源级 W2 通量约
`5.466e-2 ph cm^-2 s^-1`，约为当前粗表 W2 表示量的 `36.9` 倍。

这个 `36.9` 只是源级窄窗光子含量比，不是探测器本底倍率，不能直接乘到论文背景率。
若以后修复，必须从 broadband 中扣除同一湮没线面积，再加入同环境、同角度、同时间归一的
解析线形；绝不能在当前 broadband 上直接叠加 mono-511，否则双计数。现阶段没有授权新输运。

### 5.7 活化与 TES 的外部验证等级

- exact-position lineage、NUBASE 基态半衰期处理和同时间轴递推是内部验证；它们不等于绝对
  核素产额/活度的实验验证。稿件还应明确初始库存 `N(0)`、地面预活化和上升段边界，尤其
  是在报告 `0.724 d` 早期 3 sigma 时间时。
- `0.420 keV` TES FWHM 与 511-CAM 的约 `0.390 keV` 设计目标数量级相容，但尚未在本文
  的 `1.5 x 1.5 x 3 mm` absorber/TES 堆栈上实测。它应标为响应假设，不能写成已验证硬件
  指标。未来最直接的实验闭合是 `22Na` 的 511 keV 标定和 `133Ba` 增益转移。

## 6. “粉红大象”与人类论文口吻

独立审稿定位了以下高优先模式。后续若获授权修改，只做局部删除或改成直接肯定陈述，不得
因此重写整篇论文。

1. 反复写 `corrected/repaired total-kinetic-energy`，把旧能量轴错误和修复史召回正文。
   科学正文只需定义输入是 keV 总动能，alpha 表是 MeV/n。
2. 多处重复 `no independent monoenergetic atmospheric line is added`。源方法中保留一次必要
   边界即可，其余改为肯定句说明 broadband 包含连续谱和湮没成分；同时必须解决第 5.6 节的
   线形分辨问题。
3. `all 480 references resolve`、十二位小数归一范围、路径/包/审计状态属于内部 QA，不应在
   投稿正文作为物理证据。
4. `retained/current/auditable/source contract/closure/closed` 等词把多版本管理带入论文；
   改成普通科学术语，如 reference geometry、input spectrum、validation comparison。
5. `rather than a reduced detector cartoon`、`not a flat, infinite absorber plate`、
   `not a visual comparison`、`no fitted empirical correction` 会引入读者原本不会假定的前提。
6. Laue 章节解释“process class 只处理 transport interface”属于代码职责，不是物理方法。
7. Data availability 中仍有 `Before publication... should provide` 和
   `To be completed before journal submission`，这是作者内部 TODO，应在投稿前变成最终声明。

双语还需注意：中文图 1 把 cylinder axis 写成“烟囱轴”；中文“按实际产生位置抽样”比英文
recorded production position 更强，应改成“按模拟记录的核素产生位置抽样”。

## 7. 新 Session 的默认工作方式

复习完成后，先在 commentary 中用不超过 12 条报告：

1. 当前四份稿件的绝对路径和页数；
2. SG3 -> 本底诊断 -> SH3 的论文主线；
3. 哪些结果是内部一致性，哪些是外部/实验验证；
4. 第 5 节问题中哪些会改变主结论，哪些只需收窄表述；
5. “粉红大象”最集中的章节；
6. 明确声明没有读取错误任务产物、没有做 hash、没有启动输运。

如果用户只要求 review：只给审稿意见，不修改任何文件。  
如果用户明确要求修改：只改当前 SG3/SH3 两份 TeX 及其直接生成的 PDF/图；先列出拟改槽位，
不得修改四个母版、`M05NEW/README.md`、`M05_PAPER_DATA_TABLE.csv`、既有 JSON 审计文件或
本交接文件。不得新建论文 scaffold、参考文献库或新输运。

## 8. 禁止事项

- 不使用 subagent；不把不同章节分给不同代理。
- 不做无明确物理收益的 HASHI/hash、manifest 扩展或二进制一致性审计。
- 不运行 Cosima、Geant4、新 activation、detector response 或大统计任务。
- 不恢复 factor-1000 历史结果，不读取错误任务产物。
- 不把旧 PARMA mono-line 模块直接叠加到当前 broadband。
- 不把 `PASS`、`authority`、`closure` 等内部状态字符串当作外部物理证据。
- 不因审稿意见而自动改稿；先保持 review 与 implementation 分离。

## 9. 可直接交给新 Session 的启动提示

```text
请完整阅读并严格执行：
/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/M05_CURRENT_SESSION_HANDOFF_20260823.md

当前阶段只读复习。必须按交接顺序完整阅读当前英文 25 页、中文 24 页 TeX/PDF及分层证据，
不要用自己的工作树中的同名旧文件替代 ebb2 的绝对路径。先用不超过 12 条说明论文主线、
证据等级、真正未闭合问题与粉红大象集中位置；不修改文件，不做 hash，不启动模拟，不读取
错误任务 01a02314-a50b-78d2-bb8c-b43ffa350704 的任何产物。等待我给出 review 或修改指令。
```

## 10. 当前保护边界

本次整理只新增本交接文件。现有两份交接、四个母版、当前中英文 TeX/PDF、README、数据表、
引用索引和审计 JSON 均保持原样。
