# Independent optimization audit request

你是一个独立的科学计算、Geant4/MEGAlib 和蒙特卡洛统计审查者。请在
`/home/ubuntu/TES_511_Balloon` 内进行深入但严格只读的项目复习，并用中文给出
可执行、可验证的第二意见。

## 执行边界

1. 先读根目录 `AGENTS.md`，遵守其中的 retained-package 与不覆盖约束。
2. 不修改任何文件，不启动 Cosima，不删除或压缩现有项目数据，不重写论文。
3. 不要仅相信本提示词；对关键结论必须打开实际文件、ledger、validation、source
   card、geometry setup/include、MEGAlib 源码与 M05，并引用精确路径和行号。
4. M05 中的旧数值来自错误能轴，不能作为当前物理真值；但 M05 的完整分析方法
   与数据依赖是本次“需要保留什么”的主要需求。M06 是有意缩减的中期稿，不能
   单独作为数据裁剪合同。
5. 只提出方案和验证计划，不实施方案。任何不确定性请明确列出。

先完整阅读交接日志：

`engineering/particle_source_unit_repair_20260811/second_opinion_optimization_review_20260812/SIMULATION_HANDOFF_LOG.md`

## 问题一：复习两条几何主线

仔细复习并画出文件/组件/物理功能对应关系：

1. `Mass_model_511` 基础 mass-complete detector/cryostat geometry；
2. 由该路线发展的、加入 BPE 中子屏蔽和 plastic/charged-particle（positron）veto
   层的候选几何。必须核实本轮 corrected-keV transport 实际使用的是哪个 canonical
   setup（预期为 S3d-O8），并解释它和 retained S3c-C0/S3c-LW1 历史主线的关系，
   不要把 S3c 与 S3d-O8 混为一谈。

至少阅读：

- `engineering/Mass_model_511_nearfield_migration_20260701/SESSION_BOOTSTRAP.md`
- `engineering/Mass_model_511_nearfield_migration_20260701/README.md`
- `engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/README.md`
- `engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/data/s3c_mainline_analysis_summary.json`
- `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/`
- batch0000--0005 的实际 geometry header/bundle authority。

输出几何差异矩阵：TES、被动材料、active BGO/CsI、plastic veto、BPE、入口窗口、
关键体积名、哪些体积必须用于 veto、哪些只用于 activation/provenance，以及对存储
裁剪的影响。

## 问题二：复习 factor-1000 能谱错误

从 raw evidence、builder、source contract、legacy/control 与 corrected cards 重新验证：

- raw 横轴单位是什么；Cosima `Spectrum File` 横轴单位是什么；
- non-alpha 为什么乘 1000；alpha 为什么乘 `4*1000`；
- 为什么修能轴而不把 `.Flux` 除以 1000；
- PDF/Jacobian/归一、20 equal-mu angle bins 与 far-field `pi R^2` 归一是否闭合；
- corrected total gamma 已含 broad-bin annihilation bump，何时会和 mono-511 双计；
- 旧谱偶然接近旧论文结果为什么不能反证修复，但新谱又有哪些未闭合物理条件。

至少阅读：

- `engineering/particle_source_unit_repair_20260811/README.md`
- `engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json`
- builder/static/dynamic validators；
- legacy 与 corrected 的代表谱、source card 和 gamma A/B diagnostic；
- 本地 MEGAlib/Cosima 读谱实现。

## 问题三：寻找大幅提速并减少容量、同时保留 M05 信息的方法

在完成前两项后，结合 batch0000--0005 的真实 SIM/log/DAT/receipt、运行时间、RSS、
bytes/event 和当前 gamma TES/veto 结果，提出至少三档候选架构并量化收益、偏差风险和
实现难度。不要只建议“多开核心”或“gzip 更高压缩率”。重点审查：

1. `StoreSimulationInfo all` 实际写了哪些 IA/CC/HT/PM/其他记录，M05 每一项结果真正
   读取哪些记录；给出字段级 data-dependency matrix。
2. prompt 与 BUILDUP 是否应使用不同的输出合同：
   - prompt 是否可在输运时做 TES pixel、真实 active veto、plastic、primary driver、
     pair/annihilation、hit order/position 的紧凑 event scorer；
   - 是否只对 TES/window/veto 候选保存 full event truth，同时保留预注册比例的全真值
     control shards；
   - BUILDUP 是否可将 TT、RP、nuclide/state、volume/material、exact production position
     流式写入紧凑 sidecar，而不保存与下游无关的普通 step 记录；
   - 哪些 M05 Compton/FoV、Revan、coincidence、delayed-source 与 mission-fold 信息会因
     裁剪而丢失。
3. 能否通过源端的分层/重要性抽样、方向/能量 strata、splitting/Russian roulette、
   phase-space boundary scoring 或 Geant4 biasing 提高 480--550 keV/W2 survivor 效率。
   必须给出无偏权重公式，并区分 prompt 与 activation；不能未经证明删除高能段或提高
   production cut，因为高能 shower、pair->annihilation 和 activation 可能馈入 511 keV。
4. 现有 rich SIM 中约 60--90% 未压缩记录字节来自 CC（几乎都是 CC HIT），且时间/事件
   与压缩字节/事件高度相关。请从 MEGAlib/Cosima 源码判断可节省的是序列化、压缩、
   transport stepping 还是三者，并设计 no-output/full-output/compact-output 的 matched
   benchmark 来因果拆分。
5. 设计一个很小但有判别力的 A/B pilot：相同输入合同、明确 seed/初态配对边界、两个
   geometry、prompt 与 BUILDUP 分开。规定 event-level/aggregate-level 等价门，包括
   M05 所需 TES response、veto、宽窗/W2、multiplicity、Compton order/FoV、primary
   drivers、TT、RP/TT、nuclide-volume-state-position、delayed source 与 Step05 结果。
6. 给出推荐生产架构的磁盘模型、CPU/wall 模型、RAM 调度和 fail-closed provenance；
   至少估算相对当前 retain-all 的保守/中位/理想提速与容量缩减倍数。区分已经有实测
   支持的数字和仍需 pilot 测定的数字。

## M05 信息合同

请通读，不要只搜索关键词：

- `core_md/balloon511_ea_latex_drafts/m05_atm511_source_revision_20260811/balloon511_ea_draft_en_m05_atm511_source_revision_20260811.tex`
- 对应中文 M05；
- M05 调用的分析脚本、figure/table builders、Step05/response/delayed/trajectory 代码。

最终回答必须包含：

1. 经文件证据核实的两几何与能谱修复结论；
2. `M05 observable -> required raw fields -> proposed retained representation -> validation`
   的矩阵；
3. 方案 A/B/C 的优缺点与预计收益；
4. 一个明确的首选方案，以及为什么它仍忠实于论文而不是 M06 式过度简化；
5. 可在 1--2 小时内完成的验证性 pilot 计划与 GO/NO-GO 门；
6. 哪些物理结论在 pilot/优化链完成前必须继续 BLOCKED。

