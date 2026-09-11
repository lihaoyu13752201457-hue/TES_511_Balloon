# 独立评估反馈 01 整改对照（输运前）

状态：`WAIT__TRANSPORT_BLOCKED_PENDING_INDEPENDENT_REREVIEW`  
评估文件：`engineering/particle_source_unit_repair_20260811/second_opinion_optimization_review_20260812/INDEPENDENT_EVALUATOR_FEEDBACK_01.md`  
评估文件 SHA-256：`57f52999ced570af079344ea538935ce0505502003c05229597b85faadf78748`  
执行合同 SHA-256：`5288aa348a1fa5f669e8ad0f6c8e2c0e51e7bbac2f7b911183379754167b14be`

本文件只记录隔离包中的整改设计、实现落点与尚待验证的门。它不是 transport PASS，也不是 physics/performance PASS。截至本文起草时，`EXECUTION_STATUS.json` 明确给出 `transport_authorized=false`、`transport_events_launched=0`；任何构建或静态测试结果都不能自行解除二次独立复核门。

## 1. EventList root/driver provenance

评估问题：安装版 `MCSource.cc` 虽解析 EventList row ID，却不把它传播到模拟事件；file-EventList 的 volume 为空。因此，共用 tape 只能证明初态，不能单独证明 root/driver 身份。

隔离整改：

- `schema/tape_root_v1.schema.json:7-28` 冻结一行一个 primary 的 sidecar 合同：row/global index、EventList ID、稳定 root ID、driver/family/mode、source-card/source-contract、donor SIM/event、完整 primary tuple、原始行与预期生成 tuple 哈希；successor 必须为 false，运行时必须闭合 `ordered tape row <-> generated primary <-> exactly one IA INIT`。
- `code/tape_contract.py:19-60` 固定 corrected-keV source contract 与 sidecar 列；`:93-135` 只从 hash-bound rich SIM 的唯一 `IA INIT`/`TI` 抽取 donor 初态；`:138-166` 从 20 个角度源恢复 primary driver；`:200-214` 生成严格 15-field EventList 行；`:217-343` 生成 write-once tape/root sidecar 和完整 donor provenance；`:346-371` 拒绝列头、计数、顺序、successor、行哈希、root 重复或时间单调性错误。
- `patches/m05_shadow_hooks.patch:7-11,59-87` 在 `GenerateParticles` 消耗行之前取得 EventList ID/state，在 native IA INIT 加入后记录实际 particle-gun tuple；`:102-119` 在 event begin/end、且在 `Reset()` 前调用 scorer。
- `code/shadow_extensions/M05CompactScorer.cc:154-215` fail-closed 读取 sidecar 并要求 event/row 严格顺序；`:217-249` 核对传播的 EventList ID 与归一化方向后的完整 generated tuple；`:476-516` 要求且仅允许一个 `IA INIT`，并把 frozen/generated/IA tuple 三个哈希闭合。
- 控制样本不调用模拟 RNG：`M05CompactScorer.cc:411-416` 使用 stable-root SHA-256 的预注册模 100 规则；`code/build_shadow.py:28-30,64-67,90-93` 同时做源码 token 与 object undefined-symbol 扫描。

对应测试：

- `tests/test_preflight.py:89-117`：tape/sidecar 顺序与原始行哈希、successor 拒绝。
- `tests/test_preflight.py:191-201`：hook 调用顺序与 scorer RNG token 拒绝。

二次复核必检：实际生成的每个 shard 必须逐行通过 tape validator，shadow scorer 的物理 TSV 列头必须与冻结 schema 精确一致；运行时 closure 尚未执行，不能由单元 fixture 替代。任何列数/列名、tuple quantization 或方向归一差异均为 NO-GO。

## 2. exact BUILDUP RP completeness

评估问题：本地 `IP RP` 注释缺 root/material/显式 logical volume；native isotope DAT 只有 TT 与 volume/ZA/state/count 聚合。selected truth 不能替代每一次真实 isotope production。

隔离整改：

- `patches/m05_shadow_hooks.patch:20-24,42-51` 令 shadow `MCRun::AddIsotope` 返回 native 单调提交序号；`:132-144` 只在 native `AddIsotope` 已成功提交之后调用 `RecordCommittedIsotope`；`:166-174` 在 native `SaveIsotopeStore()` 后以 native added-count 与 TT 结束 scorer。
- `code/shadow_extensions/M05CompactScorer.cc:418-474` 要求 production serial 无缺口，逐次保存 stable root、driver/family/root weight、ZA/Z/A、显示 excitation 与原始 f64 bits、native DAT volume、physical/logical volume、完整 touchable-copy path、material、exact production position/time、track/parent/primary、particle/process 与 ancestry chain。
- `M05CompactScorer.cc:582-617` 要求 positive finite TT、sidecar/native count 相等，写 zero-RP-positive-TT sentinel，并且只在全部 closure 后把 `.partial` 原子改为 final。
- `code/rp_validation.py:13-20` 冻结上述 required fields；`:23-54` 严格解析 native `TT/VN/RP/EN`；`:57-91` 拒绝 serial、lineage、volume/material、ZA、state bits 或 analog root weight 错误；`:94-118` 要求 sidecar 聚合一对一等于 native DAT、footer count 一致，且 zero-RP job 仍有正 TT。
- `schema/m05cc_v1.schema.json:99-109,116-122` 冻结 activation 与 job footer 的逻辑字段合同。

对应测试：

- `tests/test_preflight.py:137-176`：两条真实语义 RP fixture 的 serial 与显示 state 聚合闭合，并拒绝 serial gap。
- `tests/test_preflight.py:178-188`：zero-RP + positive TT 接受，TT=0 拒绝。
- `tests/test_preflight.py:195-199`：静态确认 callback 晚于 `AddIsotope`、footer 晚于 `SaveIsotopeStore`。

二次复核必检：用 manifest-bound cassette 的非零 RP 和 zero-RP/positive-TT 两类输入验证真实 sidecar ↔ native DAT，而非只跑合成 fixture；每个 production serial 必须是一条且仅一条 native commit。运行时 RP closure 尚未执行。

## 3. frozen external/source identities

评估问题：未版本化 arXiv URL、GitHub mutable branch 不能作不可变 authority；真正执行 authority 应是本机文件 hash。

隔离整改：

- `external_sources.json` schema v2 把四篇论文固定到显式 arXiv version 与 DOI；公开代码均为 40-hex commit/blob URL，并明确 `public_code_is_design_evidence_only=true`。ComPair 官方实现未找到时记录 `NOT_FOUND__DO_NOT_INVENT_COMMIT`，没有虚构 commit。
- 同一清单冻结本机 production `cosima`、`libCosima.so`、`MCSource.cc`、`MCEventAction.cc`、`MCSteppingAction.cc`、`MCRun.cc`、`MCIsotopeStore.cc` 和 `geant4-config` 的绝对路径、SHA-256、bytes 与执行角色。
- `EXTERNAL_IMPLEMENTATION_REVIEW.md:11-33` 区分 COSI/ComPair/cosipy/Geant4 的外部事实与本项目推断；`:35-87` 记录安装版 COSI balloon、ModifiedCosimaOutput、EventList、DEE、Background/Activation/CoolDown/Pipeline、dcosima/mcosima/mpicosima 及核心 engine 的实际行为；`:89-106` 只放行 contract/scorer/build/preflight，不放行 transport。
- `code/build_shadow.py:16-27,57-76` 在复制/patch 前逐文件核对安装源 hash；`:84-123` 要求 shadow ELF 不链接安装版 `libCosima`、动态库无缺失、scorer 不导入 RNG，并将 source/patch/toolchain/binary/build-log 身份写入 build manifest。

对应测试：

- `tests/test_preflight.py:26-44`：显式 arXiv version、40-hex immutable URL、本机 authority hash/bytes。
- `tests/test_preflight.py:46-50`：状态必须 fail-closed 且零事件。

二次复核必检：最终 isolated shadow build manifest 的实际路径、binary SHA、source manifest SHA、patch SHA、toolchain 与 build-log hash 必须由根会话生成后填写到 preflight；在此之前 build 状态为 `PENDING_ROOT_CONFIRMATION`，不能从源码可编译性推定 PASS。

## 4. full seven-family projection

评估问题：最小 smoke 只覆盖 gamma、n、e+、alpha；不能把四族重归一为七族，也不能忽略 e−/muons 或未覆盖 mode。

隔离整改：

- `code/seven_family_projection.py:16-35` 明列七族、两几何、两 mode、每 cell 生产事件目标，以及最小 smoke 实测的 6 种 family/mode cell 类型。
- `seven_family_projection.py:38-73` 只从 canonical batch0001 ledger 绑定的 run-summary/job/SIM/DAT/log/source-card 计算校准，要求七族 job 集合精确闭合。
- `seven_family_projection.py:76-124` 构造完整 2 geometry × 2 mode × 7 family = 28 cells；12 个实测 cell 等待 F/C paired measurement，16 个未测 cell 逐 cell 采用 `compact = retain-all` 的 no-benefit bound。
- `seven_family_projection.py:125-166` 要求总目标恰为 93,353,632、实测覆盖 43,974,176（47.10494%）；e−/mu−/mu+ 的 no-benefit bytes 下界本身必须大于 80,000,000,000 bytes，否则 validator 失败。该下界还未计 tape、control truth、RP sidecar 或紧凑固定开销，因此是对 compact 容量最有利的下界。

当前数学结论：未测的 49,379,456 个目标 histories 不被任何实测四族替代；仅 e−/mu± retain-all 下界已约 114.5 GB，超过 80 GB 硬门，全部未测 cell 的 no-benefit 下界约 367 GB。故本最小 smoke 即使将全部实测 cell 压到零字节，也不能通过 full-target `<80 GB` 容量门。正式精确值与每 cell 分解须由待生成且 hash-bound 的 `seven_family_projection.json` 给出；在该 artifact 完成前，近似值不得当作最终 authority。

对应测试：

- `tests/test_preflight.py:120-134`：七族、28 cells、12/16 coverage、精确事件数、e−/mu floor >80 GB，并逐个未测 cell 验证 compact bytes/CPU 等于 retain-all。

二次复核必检：projection JSON 必须绑定 canonical ledger/run-summary hashes，不能用目录发现或四族重归一；即使 transport 后 F/C 结果很好，本轮 full-target capacity 结论仍是 `NO_GO`，除非另加未测族/cell 的有权威 measurement。

## 5. manifest-only receipt discovery

评估问题：batch0003 有一个额外、未配对的 Mass shard0077 receipt；递归 glob 会污染 donor/cassette/初态 authority。

隔离整改：

- `code/manifest_discovery.py:13-31` 只有两个固定 authority：canonical batch0001 ledger 与 validated batch0003 paired ordinal-76 prefix ledger，并冻结各自 SHA/status。
- `manifest_discovery.py:62-74` 必须先核 ledger hash/status；`:95-118` 要求 prefix 恰为 2 geometry、每 geometry 76 jobs、ordinal 连续 1..76、76 个 pair receipts；`:121-152` 只遍历 ledger 内 jobs，selector 必须唯一。
- `manifest_discovery.py:155-199` donor selector 是明确的 authority/geometry/job-name 或 ordinal；没有 `glob/rglob/os.walk/os.scandir` receipt discovery。`:202-218` 只公布已注册 authority。
- `JobRef.bind_artifacts`（`:42-59`）对 ledger 内 SIM/DAT/log/source-card 再逐个核 hash/bytes。任何 cassette/tape 输入还必须记录 authority ID、job selector、artifact path 与 SHA。

对应测试：

- `tests/test_preflight.py:53-65` monkeypatch 禁止所有目录扫描 API，仍须能解析两个 authority 与 gamma donor。
- `tests/test_preflight.py:67-78` 要求 76-pair/ordinal 1..76 且显式证明 shard0077 未进入 ledger job 集合。
- `tests/test_preflight.py:80-86` 拒绝 ordinal77 与未注册 live-state JSON。

二次复核必检：最终 tape provenance、cassette manifest、source build manifest 里的每一个 donor/receipt 都必须反向解析到上述两个 authority 之一；任何仅凭路径存在、目录扫描或 live-state 发现的输入均为 NO-GO。

## 二次独立复核门

在第一条 Cosima event 之前，必须同时满足：

1. write-once `benchmark_contract.json` 已绑定两条 canonical geometry bundle（Mass_model_511 `6170bfaaefaea1f9a85b9ca6dc51117fb1c9e08ba10f52c9436cedc4b57a0b61`；S3d-O8 `8cdb6577489cd049c812dbce1f1ad46225332141c9754cdf5a2eda58f4a73492`）、corrected-keV source contract、tapes、seeds、F/U production binary 与 C/N1 isolated binary；
2. 所有 unit tests、patch dry-run、isolated build identity/RNG/link checks 与 preflight validation 都由 durable artifact 记录实际命令、退出码、日志 SHA 和零 transport events；
3. tape/schema/physical TSV headers、root join、RP/native DAT、cassette selectors、18 个 matched cell-shards、arm order与重粒子串行调度全部闭合；
4. `EXECUTION_STATUS.json` 仍为 fail-closed，直到独立评估者明确给出新的 transport authorization。

当前结论仍为 `WAIT__PREFLIGHT_REMEDIATION_PENDING_ROOT_CONFIRMATION__TRANSPORT_BLOCKED`。即使后续 build 与 preflight 自检 PASS，也只能提交二次复核；不得自动启动 Cosima。
