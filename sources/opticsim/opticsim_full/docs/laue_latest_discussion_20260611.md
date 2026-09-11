# 2026-06-11 Laue 最新讨论与版本复盘

检索时间: 2026-06-11 15:25 CST  
范围: `/home/ubuntu/opticsim`, `/home/ubuntu/cross_check_laue`, `/home/ubuntu/codex_tes_511_sim/new_geo_re`, `~/.codex/history.jsonl`, `~/.claude/history.jsonl` 与相关 Claude session/memory 文件。  
口径: 这是本地记录检索, 没有联网; 目标是避免以后把旧的 Laue/B-FULL 记录误当成当前版本。

## 一句话结论

当前项目级最新 Laue 透镜权威是 `new_geo_re` 里的 **B-FULL Ge(111) 511-keV 单环 f=9 m 设计**:

- 设计名: `balloon511_f9m_ge111_511line`
- B-FULL 代码源: `/home/ubuntu/opticsim/geant4_app/src/laue_multiring_bfull_demo.cc`
- Geant4 过程: `G4VDiscreteProcess`, 有限 Laue diffraction MFP, 与标准 EM 过程竞争; 不是 Geant4 toolkit patch
- 光学权威: `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step04_opticsim/optics_aeff_authority.json`
- `A_eff(511) = 15.29928 cm2`
- 焦距: `9000 mm`
- 单环 511 keV, `27` 块 `15 mm` Ge(111) tile, mosaicity `30 arcsec`
- Step09 科学交接源只用 `focal_crossings.csv` 中 `source_tag=laue_bfull_diffracted` 且落入 Be 窗的 tracked crossings, 不用 analytic `phase_space.csv`

所以: 如果你问"现在做的是不是最新", 答案是 **是, 但要看 Step04/Step09 f=9 m B-FULL 权威文件**。如果你看的还是 `cross_check_laue` retained B-FULL 报告里的 `G4VEmProcess`, 或 `LAUE_COMPUTATION_PRINCIPLE_AND_CODE.md` 里的 8.3 m / 13.56 cm2 数字, 那些已经不是当前项目权威。

## 最新讨论线索

### Claude / cross_check_laue 侧

- `~/.claude/history.jsonl:75-77`: 2026-06-01 用户要求 Claude review `opticsim` 与 `cross_check_laue` 最新 Laue 模拟, 并把 `laue_review_20260601.html`/日志作为论文版块审阅依据。
- `/home/ubuntu/cross_check_laue/laue_lens_review_log.md`: Claude 复审记录。核心结论是 B-FULL 物理路线可以作为论文中的 Laue 版块, 但措辞必须收敛:
  - 可写成 application-level B-FULL Laue transmission / mosaic flat-crystal baseline。
  - 不可写成 Geant4 原生 Laue patch。
  - 不可把 C++/Python `5e-11` 当独立物理验证; 需要 XOP/CRYSTAL、Barriere/Kohnle 等外锚。
  - 旧 `G4VEmProcess` 在 Geant4 11.4 上脆弱, 已推动改为 `G4VDiscreteProcess`。
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step04_opticsim/optics_design_rationale.md`: 嵌入了 Claude 2026-06-02 对 f=9 m 定稿设计与全链更新的 review。结论是实现正确、全链/探测器耦合超出原 spec, 显著性降低是从占位 A_eff/理想焦斑切换到真实 Laue + 探测器响应后的诚实结果。
- `/home/ubuntu/.claude/projects/-home-ubuntu-codex-tes-511-sim-new-geo-re/memory/full-review-20260610-findings.md`: 2026-06-10 Claude 全链 review 发现 Step05 ledger 仍残留 `A_opt=50.89 cm2`; 但 W1/W2/spot headline 来自 Step09 EventList, 已经是 `15.30 cm2` 口径。这个问题随后由 2026-06-11 A-series 修复。

### Codex 侧

- `~/.codex/history.jsonl:1062`: 2026-06-01 用户要求 Codex 使用 `opticsim` + `cross_check_laue` 最新 B-FULL 模型, 设计一个符合 `new_geo_re` Be 窗/spot 的 Laue 镜并接入。
- `~/.codex/history.jsonl:1069-1076`: 用户指定按 `LAUE_LENS_DESIGN_SPEC_20260601.md`、`FOCUSING_LENS_SCIENCE_RATIONALE_20260601.md`、`EXECUTE_ROUTE_A_FULLCHAIN_AND_REPORT_20260601.md` 执行, 最终走 f=9 m Route-A 真实镜闭环。
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/EXECUTE_ROUTE_A_FULLCHAIN_AND_REPORT_20260601.md`: 明确把设计改成 `balloon511_f9m_ge111_511line`, f=9 m, 单环 511 keV, A_eff 目标约 16 cm2, 天然 passband 约 501-521 keV。
- `/home/ubuntu/opticsim` git 最新相关提交:
  - `792fb9f 2026-06-01 23:49:09 +0800 Update 511 line lens to f9m design`
  - `6378ef4 2026-06-01 22:03:48 +0800 Add B-FULL Laue driver for 511 line lens`
- `~/.codex/history.jsonl:1193`: 2026-06-10/11 附近的待修参考仍以"现在这个 Laue 以及现在的 Aeff 的透镜系统"为当前口径。
- `~/.codex/history.jsonl:1204-1206`: 2026-06-11 用户再次要求复盘 `opticsim` 与 `cross_check_laue` 的最新 Laue 版本, 并检索 Codex/Claude 讨论后落盘。本文件即对应这次检索。

## 当前权威文件

### `opticsim`

- `/home/ubuntu/opticsim/geant4_app/src/laue_multiring_bfull_demo.cc`: 当前 B-FULL Geant4 driver。
- `/home/ubuntu/opticsim/data/laue/ge111_balloon511_f9m_511keV_line_config.csv`: f=9 m 单环 511 keV config。
- `/home/ubuntu/opticsim/analysis/run_with_geant4_114.sh`: 本地可用的 Geant4 11.4 环境包装命令。当前 B-FULL 已可用该环境构建/运行; 旧"只能跑 10.2.3"说法只适用于改成 `G4VDiscreteProcess` 之前的状态。

### `new_geo_re`

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/Project_Memory.md`: 当前项目总记忆, 明确当前 optics 是 `balloon511_f9m_ge111_511line`, `A_eff(511)=15.29928 cm2`。
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/README.md`: 当前 DEMO2/Route-A science authority, 记录 Step09 focused EventList 与 detector-coupled 结果。
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step04_opticsim/README.md`: Step04 最新光学审计, `PASS_BFULL_XOPMAP_EVENTLIST_READY`。
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step04_opticsim/optics_aeff_authority.json`: A_eff 与 focal stats 权威。
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step04_opticsim/real_design_crosscheck_20260601.md`: f=9 m 设计门控摘要。
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/ROUTE_A_FULLCHAIN_EXECUTION_LOG_20260601.md`: f=9 m 光学接入全链后的关键数字。
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/CODEX_A_SERIES_EXECUTION_REPORT_20260611.md`: 2026-06-11 current-data 修复, 把 Step05 ledger/report 对齐到 `15.29928 cm2`; 没有新跑 Geant4/Cosima。

### `cross_check_laue`

- `/home/ubuntu/cross_check_laue/laue_lens_review_log.md`: Claude 审阅与物理 claim 边界的主要记录。
- `/home/ubuntu/cross_check_laue/laue511_validation/reports/laue511_crosscheck_summary.md`: 交叉验证包总览, 仍显示 `Production validation ready: False`。这个目录是外部/独立检查包, 不是 `new_geo_re` 最新生产权威。
- 注意: `cross_check_laue/laue511_validation/reports/bfull_*` 多数 retained 报告仍写 `G4VEmProcess`。这些报告对旧阶段有用, 但已落后于当前 `opticsim` B-FULL `G4VDiscreteProcess` 版本。

## 时间线

1. **2026-05-29 前后**: `cross_check_laue` 聚焦在 B-FULL 验证套件、XOP/CRYSTAL backend、off-axis/rocking scan, 但 retained 报告仍是旧 `G4VEmProcess` 口径。
2. **2026-06-01 中午**: Claude review 提醒 B-FULL 应改为 `G4VDiscreteProcess`, 避免旧 `G4VEmProcess` 在 Geant4 11.4 上崩; 也要求把 novelty/claim 从"原生 Geant4 Laue"收敛为 application-level Laue transmission model。
3. **2026-06-01 下午-晚上**: Codex 根据 `LAUE_LENS_DESIGN_SPEC_20260601.md` 和执行 prompt, 将设计定为 `balloon511_f9m_ge111_511line`: f=9 m, Ge(111), 单环 511 keV, 27 tiles。
4. **2026-06-01 23:49 CST**: `/home/ubuntu/opticsim` 提交 `792fb9f` 更新到 f=9 m 511 line lens。
5. **2026-06-02**: Claude 对 Codex f=9 m 定稿设计 + 全链更新复审, 认为实现正确; 明确真实性能下降来自真实 A_eff 与 detector-coupled Compton broadening, 不是退步。
6. **2026-06-10**: Claude 全链 review 发现 Step05 broad-window ledger 仍是旧 `A_opt=50.89 cm2`; 判断 headline W1/W2/spot 已经干净, 但 ledger/report 需要 current-data 修复。
7. **2026-06-11**: A-series 修复完成: Step05 science ledger 改为 `A_opt_cm2=15.299280`, Step05/Step08/experiment report 刷新, validator 20/20 PASS。没有重新跑光学 Geant4, 也没有重跑 Cosima transport。

## 当前关键数字

- B-FULL f=9 m run: `50,000` primaries
- diffracted focal crossings: `12,605`
- within-Be focused rows: `12,592`
- Be radius: `1.898 cm`
- optical focal `r99`: `0.291410 cm`
- max within-Be focal radius: `1.45767 cm`
- emergent focal diffraction fraction: `0.2521`
- analytic/reference fraction: `0.257481`
- emergent - analytic: `-0.00538123`, strict `<0.01` diagnostic gate pass
- `A_eff(511)`: `15.29928 cm2`
- natural passband FWHM: `500.993937-521.006063 keV`
- detector-coupled spatial headline after full chain: `spot_r90` background `0.0551005 cps`, time-dependent `Z20d=4.50779`, 20-day 3-sigma flux `6.655e-5 ph cm^-2 s^-1`

## 不要误引用

- 不要把 `phase_space.csv` 当科学注入源; 它是 analytic projection, 会高估 focused flux。当前 Step09 只用 tracked `focal_crossings.csv`。
- 不要声称这是 Geant4/MEGAlib 原生 Laue 衍射物理; 这是 opticsim application-level `G4VDiscreteProcess`。
- 不要声称可模拟 Jiang/IHEP 那类 bent-crystal lens 的完整弯晶聚焦/PSF。当前模型是 mosaic flat-crystal Laue baseline; 可以吃 bent-crystal reflectivity map, 但不等于弯晶几何聚焦模型。
- 不要把 `cross_check_laue` retained `G4VEmProcess` B-FULL 报告当当前 f=9 m 生产权威。
- 不要把 `LAUE_COMPUTATION_PRINCIPLE_AND_CODE.md` 当前残留的 8.3 m / `A_eff=13.5562 cm2` 当最新数字; Step04 README 与 `optics_aeff_authority.json` 已经是 f=9 m / `15.29928 cm2`。
- 不要继续引用旧 `A_opt=50.89 cm2` 作为 Route-A Laue A_eff。那是 channel/homogeneous-beam 占位口径; 2026-06-11 已修正 ledger/report。

## Review 结论

当前 f=9 m B-FULL 版本是主线最新, 物理与工程 claim 边界比 5 月版本清楚得多: 有标准 EM 竞争、有 XOP/CRYSTAL 外部曲线、有 Be-window tracked crossing、有 detector-coupled 全链响应。作为论文中的"511 keV Ge(111) Laue focused source + detector-coupled background/sensitivity chain"版块, 当前证据链可用。

剩余风险不是"现在跑的是旧版", 而是以下文档/验证债:

1. `cross_check_laue` 的 retained B-FULL 报告需要用当前 `G4VDiscreteProcess` binary 重跑/重标注, 否则读者会看到旧 `G4VEmProcess` 口径。
2. `LAUE_COMPUTATION_PRINCIPLE_AND_CODE.md` 需要更新到 f=9 m / `15.29928 cm2`, 或明确标为 superseded。
3. Laue lens hardware mass 的 cosmic-ray prompt/self-activation 还没有作为上游本底源加入 `new_geo_re`; 当前只是 focused-photon optics handoff。
4. 如果要把 claim 推到"宽能段 480-550 keV Laue 聚焦"或"弯晶透镜", 需要新设计与新验证。当前 f=9 m 设计是 511-line-first; 480-550 keV 是 TES/analysis window。

## 推荐下一步

1. 更新或废弃 `LAUE_COMPUTATION_PRINCIPLE_AND_CODE.md` 的 8.3 m 残留数字。
2. 在 `cross_check_laue` 新增一轮 current-B-FULL retained scans: Geant4 11.4 + `G4VDiscreteProcess` + f=9 m config + XOP map。
3. 给 f=9 m run 写一条固定复现命令, 必须包含 `--focal-mm 9000` 和 `--require-rocking-curve-map`。
4. 论文/报告引用只使用 Step04 README、`optics_aeff_authority.json`、Step09 bridge、`Project_Memory.md` 与 2026-06-11 A-series report, 避免旧 50.89 cm2 / 8.3 m / G4VEmProcess 混入。
