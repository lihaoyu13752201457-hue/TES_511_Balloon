# M05-complete compact isolated smoke 执行报告（输运前交接稿）

> **HISTORICAL_WITHDRAWN__DO_NOT_USE_AS_CURRENT_CONTRACT.** 本文正文保留早期设计轨迹，
> 其中 12-cell/3-shard、`m05-tape-root-v1`、逐step deposits、active-veto选full truth、
> 仅1% control、反馈01状态均已被撤回。当前唯一状态见 `EXECUTION_STATUS.json`，治理合同为
> `GPT56_SOL_ULTRA_SMOKE_FOLLOWUP.md`（SHA-256 `5288aa348a1fa5f669e8ad0f6c8e2c0e51e7bbac2f7b911183379754167b14be`）
> 与反馈02（SHA-256 `caa97d522214b9ef811a9b6d71a5307dffd9f551e5687f1c736bcfe081a2a1d7`）。
> 当前冻结方向是 28 cells、每cell 4 shards、40列 `m05-tape-root-v2`、27,200 unique tape rows、
> 56 seeds、112 geometry-cell shards、448 planned jobs/217,600 invocation histories，
> `runnable_job_count=0`。TES pixel与24/6 active block在线聚合；production deposits表仅header；
> native full truth仅 raw-TES-positive 与每shard前三行加稳定root约1%的outcome-independent controls，
> active-only仅保typed block。F/U preload observer仍是未执行compile-only candidate；需独立授权的
> 672-event sentinel关闭P12后才能产生新runnable revision。N0缺失只限制pure stepping因果宣称。
> C仅发布并用m05cc-v2验证`record_bundle.json`；N1仅发布独立
> `m05cc-n1-v1-commit`的`commit.json`，严格验证root/generated/footer/tape/native-DAT，且绝不作为materializer输入。
> `transport_authorized=false`、`transport_events_launched=0`，本文任何“必跑/可运行”措辞无放行效力。

## 结论先行

当前是 `WAIT`，不是 benchmark PASS。隔离包已形成 output-only 因果比较的实现方向和五项反馈整改证据，但仍须完成根会话的最终 build/preflight、冻结所有 artifact hash，并交给第二次独立评估。`EXECUTION_STATUS.json` 当前约束为 `transport_authorized=false`、`transport_events_launched=0`；本文没有启动 Cosima，也没有产生可计入生产的 event、TT、seed、RP 或 rate。

另有一个与 transport 无关、在预检阶段即可确定的结论：在未测 family/mode/cell 采用 no-benefit bound 时，e−/mu± 子集的容量下界已超过 80 GB。因此，这个最小四族 smoke 无论未来 F/C 实测多好，都不能单独给出 full-seven-family capacity GO；本轮容量结论预注册为 `NO_GO__CAPACITY_GATE_UNREACHABLE_UNDER_UNMEASURED_NO_BENEFIT`。

## 1. 提案与边界

首轮候选仅改变输出表示/序列化路径，不改变 geometry、材料、production cuts、energy support、physics process、Geant4 data 或 primary probability measure。两条 geometry 必须是：

- Mass_model_511 bundle SHA-256 `6170bfaaefaea1f9a85b9ca6dc51117fb1c9e08ba10f52c9436cedc4b57a0b61`；
- S3d-O8 bundle SHA-256 `8cdb6577489cd049c812dbce1f1ad46225332141c9754cdf5a2eda58f4a73492`。

所有 source 必须来自 corrected-keV contract；遇到 `cosima_spectra_dp_2602units` 旧引用应 fail closed。O8 neutron、e+、alpha 的重机制以及 BPE、BGO、plastic、pair→annihilation、high-energy shower 与 activation 必须完整输运，不能用小样本零 survivor 为理由裁能段或关过程。

计划的 matched cells 为每 geometry：prompt gamma 10,000、BUILDUP neutron 2,000、prompt e+ 500、BUILDUP e+ 500、prompt alpha 100、BUILDUP alpha 100；每 cell 分 3 个 subshard。同一 geometry/cell/shard 的可执行 arms 使用相同 EventList 初态 tape 与相同 transport seed，且 scorer 不取 RNG。arm 顺序轮转；O8 n/e+/alpha 串行，避免 RSS 叠加。所有将来输出均标记 `NON_MERGEABLE_BENCHMARK`。

## 2. 外部与本机实现审查如何影响设计

`EXTERNAL_IMPLEMENTATION_REVIEW.md` 是 transport 前设计证据，不是放行文件：

- COSI DEE/共同 reconstruction pipeline 要求保留足以复演响应与重建的 event truth，而不是只存最终 511-keV boolean（`:11-15`）。COSI bottom-up 背景工作支持 prompt 与 activation/delayed 分层，但要求 BUILDUP TT、核素/位置 lineage 完整。
- COSI ACS 的光学参数化只说明“经独立标定后把昂贵 detector effect 下游化”可行，不允许跳过本项目 BGO/CsI/plastic 中的粒子输运（`:15`）。
- ComPair 的 EXPACS→Cosima→DEE→ACD/Revan/Compton-pair 链说明高能 shower、pair/annihilation 与 veto 信息不能过早裁掉；官方公开实现仓库未找到，故只引用 versioned paper，不虚构代码 authority（`:17-19`）。
- cosipy/cosi-atmosphere 提供版本化 response 与 boundary phase-space 先例，但不能证明两个 geometry 内部 transport 可共用；Geant4 cuts、importance/splitting/RR/phase-space 都留作以后带权显式 candidate，本稀疏 smoke 不执行（`:21-33`）。
- 已安装 ModifiedCosimaOutput 证明可以用 extension hook 避免标准 event file，却仍晚于 rich event 构造，且不能补足 exact AddIsotope lineage；EventList parser 的 ID/empty-volume 缺口促成了 frozen root sidecar 和 engine hook（`:48-53`）。
- 本机 `MCEventAction`/`MCSteppingAction` 表明 FileName 为空只关闭 stringify/file；IA/CC/HT/hits 仍构造。`StoreSimulationInfo none` 也不是可靠 N0（`:55-64`）。
- native isotope DAT 只保 TT 和 volume/ZA/state/count 聚合；因此 C 必须在真实 `AddIsotope` commit 点逐 RP 捕获，并用 DAT 作独立聚合 authority（`:66-72`）。
- `mcosima`/`mpicosima` 是多个独立 Cosima 进程与不同 seed，`dcosima` 是远程提交；它们既非当前应用内 MT，也不满足 matched tape/seed。因此本 pilot 使用显式受控进程调度（`:82-87`）。

不可变公开论文/commit 与本机逐文件执行 authority 收录于 `external_sources.json`。F/U 执行 authority 是安装版 production `cosima` SHA-256 `3fb7613de58ebb365f2a55c3336e54d2aabea2a4ddb282003a5d25eac6f1c74a`；C/N1 只能在 isolated shadow build manifest 完成且二次复核后成为候选执行 authority。

## 3. 因果 arms

| arm | 实现合同 | 能回答的成本 | 当前状态/限制 |
|---|---|---|---|
| F | 安装版 production Cosima，current rich gzip | transport + rich objects + stringify + gzip + I/O 总成本 | 必须作为 reference；待授权 transport |
| U | 同一安装版与 rich records，`-u` plaintext | 从 F/U 差分观察 gzip 成本及 bytes | 待授权 transport；磁盘硬门仍适用 |
| N1 | isolated shadow + root observer，rich records 仍构造，空 FileName | transport + rich object/hit 构造，不含 full stringify/file | build/preflight/二次复核后才可运行 |
| C | 同一 shadow transport；typed TES/veto/RP sidecars + candidate/control native truth，空 FileName | N1 成本 + compact capture/encoding | build/preflight/二次复核后才可运行 |
| N0 | 本意为 IA/CC/HT/string/hit construction 也关闭 | 理论 transport/hits 最低边界 | `BLOCKED_NOT_RUN`：当前 SaveEvents/StoreSimulationInfo 不能安全实现；需另改 engine control flow 与完整 ABI/physics 回归 |

F/U/N1/C 都不得改物理。若 N0 不可执行，就不能声称完整的 stepping/对象构造/序列化/压缩四项因果 speed decomposition 或纯 transport/physics-algorithm speedup；但可按预注册统计合同报告 F/C 端到端 simulation-output-path wall ratio 及 lower-95% gate，并用 U/N1 作输出路径构造/压缩的辅助括号。

cuts、process configuration、energy restriction、stratification/weighted sampling、splitting/Russian roulette、phase-space boundary 和 MT/tasking 已审查，但本轮没有足够支持证明 prompt 与 activation 的 M05 全 observable 无偏，因此分别是 `NO_GO_CANDIDATE` 或 `REVIEWED_NOT_EXECUTED`，不能用来制造速度数字。

## 4. M05 信息保真合同

| M05 需求 | retained representation | 验证门 |
|---|---|---|
| primary event/root/family/E/position/direction/time/driver | write-once EventList + `m05-tape-root-v1` sidecar；C/N1 root observer 记录 observed generated 与 IA INIT tuple hash | 严格一行一 event、无 successor、顺序/ID/tuple/root 唯一；frozen/generated/唯一 IA INIT 三向 closure |
| TES pixel UID/layer、0.3-keV threshold、420-eV response、centroid/time、multiplicity/order | compact pixel + typed deposit sequence；candidate/control native truth | UID/layer/energy/centroid/time/first-last sequence event-level exact/float tolerance；相同 response seed 的下游 fixture |
| Mass CsI、O8 BGO、O8 plastic，50/70/80-keV veto；Kapton 排除 | typed physical/logical/touchable/material deposit rows + per-event separated sums；Kapton 仅 diagnostic | exact whitelist 与 geometry volume audit；eventwise sums、阈值 bits、veto cut-flow 对 F 一致 |
| primary/pair/annihilation/process ancestry | 每个 typed deposit 的 track/parent/primary/process；所有 candidate 与 stable-root 预注册 1% control 保存 native full truth | IA process/order/root lineage 一致；pair/ANNI cassette 与 control inclusion predicate 固定且 scorer 无 RNG |
| Compton/FoV、Revan/ARM input | candidate/control native IA/HT truth fragment + position/order/energy | cassette structural equivalence；相同 Revan config/status 与 deterministic fixture；不能用 final boolean 代替输入 |
| full-band/coincidence/occupancy/time | event source time、TES/shield/plastic totals、typed deposit times、native truth | event template、occupancy/coincidence 与相同 time/response seed 闭合 |
| BUILDUP TT、RP、NUBASE/delayed/mission fold | 每次 native AddIsotope 后一条 activation sidecar；native DAT 保留 TT/aggregate；footer 保留 zero-RP positive TT | production serial 1..N；sidecar count/aggregate = native DAT；ZA/state bits/volume/material/exact position/root one-to-one；delayed-source hash/parent-position 与 mission-fold fixture |
| geometry/source/transport/scorer/seed identity | contract/run manifest + bundle/source/tape/sidecar/binary/source/patch/toolchain/schema/table hashes | strict canonical JSON、write-once paths、hash/bytes、seed registry、NON_MERGEABLE 标志、fail-closed completeness |

逻辑 schema 位于 `schema/m05cc_v1.schema.json`，但它不能代替对实际 TSV/header/join 的验证。最终 preflight 必须证明物理输出列能无损实例化该逻辑合同；任何逻辑字段只能通过明确、hash-bound、唯一键 join 获得，不能靠未记录推断。

## 5. 五项反馈的实现摘要

完整逐条映射见 `EVALUATOR_FEEDBACK_01_REMEDIATION.md`。核心为：

1. `code/tape_contract.py` + `schema/tape_root_v1.schema.json` 冻结 root/driver/source/donor/primary tuple；shadow hook 在 consume 前传 EventList ID，并在 event end 核唯一 IA INIT。
2. `patches/m05_shadow_hooks.patch` 在真实 native `AddIsotope` commit 后给出单调 serial；`M05CompactScorer.cc` 写 exact RP sidecar；`code/rp_validation.py` 与 native DAT/TT/footer 闭合。
3. `external_sources.json` 使用显式 arXiv versions、DOI、immutable 40-hex commits，并以本机逐文件 hash 为 executable authority。
4. `code/seven_family_projection.py` 覆盖 28 个 geometry/mode/family cells；未测 16 cells 为 identity/no-benefit，绝不把四族重归一。
5. `code/manifest_discovery.py` 只接受 hash-pinned batch0001 ledger 与 batch0003 paired ordinal-76 prefix ledger；明确拒绝额外未配对 Mass shard0077 与 live-state/目录扫描。

## 6. 保守 full-target 容量结论

七族每 geometry×mode 的目标为 23,338,408 events；两 geometry×两 mode 总计 93,353,632。最小 smoke 所覆盖的 cell 类型在 full target 中对应 43,974,176 events（47.10494%），其余 49,379,456 events 不可用四族结果替代。

对 16 个未测 cells 预注册 `compact bytes/event = retain-all bytes/event`、`compact CPU/event = retain-all CPU/event`。其中仅 e−、mu−、mu+ 的 no-benefit 容量下界就约 114.5 GB，已经严格大于 80 GB；连同未测 gamma-BUILDUP、n-prompt 后总下界约 367 GB。因为这个下界尚未加 tape、1% control truth、RP sidecars 与固定开销，新增项只会使容量更大。

所以即使实测 12 cells 的 compact 输出理想化为 0 bytes，full-target `<80 GB` 仍不成立。这是本轮的容量 `NO_GO`，不是 C 表示本身的 physics NO-GO。要重新打开容量门，必须测量或以另一条经独立验证的保守合同约束全部未测族/cells，不能重归一。

## 7. build、test 与 preflight 状态（待根会话确认）

以下条目刻意不写 PASS；只有实际 artifact 出现、hash 绑定并经根会话复核后才能替换占位状态：

| 项目 | 预期 durable path | 当前文档状态 |
|---|---|---|
| unit/fixture tests | `tests/test_preflight.py` 对应的日志与 exit code，路径待 `preflight_validation.json` 绑定 | `PENDING_ROOT_CONFIRMATION` |
| patch dry-run | 同上；须记录 installed upstream hash 与 patch SHA | `PENDING_ROOT_CONFIRMATION` |
| isolated shadow build | `runs/particle_source_unit_repair_20260811/m05_complete_compact_smoke_20260812/preflight/shadow_build/build_manifest.json` | `PENDING_ROOT_CONFIRMATION__EXECUTABLE_MUST_NOT_BE_RUN` |
| benchmark contract | `benchmark_contract.json` | `PENDING_WRITE_ONCE_FREEZE` |
| tape provenance | `runs/particle_source_unit_repair_20260811/m05_complete_compact_smoke_20260812/preflight/tape_provenance_manifest.json`（最终路径以 contract 为准） | `PENDING_ROOT_CONFIRMATION` |
| seven-family projection | `runs/particle_source_unit_repair_20260811/m05_complete_compact_smoke_20260812/preflight/seven_family_projection.json`（最终路径以 contract 为准） | `PENDING_ROOT_CONFIRMATION` |
| representation cassette | manifest-only cassette manifest，最终路径待 contract 冻结 | `PENDING_ROOT_CONFIRMATION` |
| full preflight | `preflight_validation.json` | `PENDING_ROOT_CONFIRMATION__SECOND_REVIEW_REQUIRED` |

即使上述项目之后全部 PASS，`EXECUTION_STATUS.json` 也只能更新为类似 `WAIT__PREFLIGHT_PASS__TRANSPORT_BLOCKED_PENDING_INDEPENDENT_REREVIEW`；不能由执行者自行翻转 `transport_authorized`。

## 8. 刻意不存在的 post-transport 交付物

下列文件在获得独立 transport authorization 并实际运行 matched smoke 前应当不存在，不能用空壳或 fixture 冒充最终结果：

- `raw_metrics.csv`：没有 BeamOn/wall/CPU/RSS/bytes/record counts 的实际 transport measurement；
- `physics_equivalence.json`：没有 F/C/U/N1 matched event 与 downstream equivalence；
- `performance_summary.json`：没有 paired speed/size/RSS interval，也不能声称 1.5× wall-speed；
- `FINAL_VALIDATION.json`：没有完整 expected arm/cell/consumer closure，绝不能发布 PASS。

preflight fixture 可以在 `preflight_validation.json` 中明确标为 fixture，但不等同于这些 post-transport 产物。

## 9. 执行者的暂定判定

- external/local implementation review：`SUFFICIENT_FOR_PREFLIGHT_ONLY`；
- feedback-01 remediation source/schema：`IMPLEMENTED_SUBJECT_TO_FINAL_BUILD_AND_PREFLIGHT`；
- transport：`WAIT__BLOCKED_PENDING_SECOND_INDEPENDENT_REVIEW`；
- transport events：`0`；
- M05 physics equivalence：`NOT_MEASURED`；
- wall-speed/RSS：`NOT_MEASURED`；
- compact representation：`PROPOSED_NOT_YET_TRANSPORT_VALIDATED`；
- full-seven-family disk `<80 GB`：`NO_GO_UNDER_CONSERVATIVE_UNMEASURED_NO_BENEFIT_BOUND`；
- production use/merge/geometry ranking/rates：`BLOCKED`。

下一步仅是完成并复核 write-once contract、actual source/build/tape/cassette/projection hashes 与 strict preflight，然后停在二次独立评估门。未得到新的明确授权前，第一条 Cosima event 仍不得启动。
