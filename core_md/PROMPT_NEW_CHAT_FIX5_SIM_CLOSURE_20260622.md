# PROMPT — new chat entry for fix5 simulation closure

你正在接手 `/home/ubuntu/TES_511_Balloon` 的 fix5 simulation closure 工程。

请用中文和用户沟通。不要重新设计几何；当前任务不是优化几何，而是验证已经建好的 fix5 几何是否能替代 current v3p5 selected-511-rate authority。

## 0. 立即读取

进入仓库后，先按顺序读取：

1. `AGENTS.md`
2. `core_md/METHOD_FIX5_SIM_CLOSURE.md`
3. `core_md/GUIDE_FIX5_SIM_CLOSURE_FOR_CODEX_20260621.md`
4. `core_md/CONSTRAINTS_FIX5_SIM_CLOSURE.md`
5. `core_md/fix5_benchmarks.json`
6. `core_md/PRE_PROMPT_FIX5_SIM_CLOSURE_20260621.md`
7. `core_md/Project_Memory.md` 中 "The 11-Step Conceptual Chain" 的 Step 9/10/11
8. `core_md/HANDOFF_20260617.md`
9. `core_md/workflow.md`
10. `outputs/reports/user_redesign_multiholeW_fix5_20260621/USER_CYLMAG_REDESIGN_MULTIHOLEW_FIX5_SUMMARY.md`
11. `outputs/reports/user_redesign_multiholeW_fix5_20260621/side_window_material_path_audit_fix5.json`

没有完成下面 checkpoint 前，不要启动 MC。

## 1. 先向用户汇报 checkpoint

汇报这些点：

1. fix5 `.geo.setup` 路径：
   `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
2. 用自己的话说明 Step05 如何把 prompt/delayed/focused streams 放到共同 Poisson time axis，Step06 如何把 day-15 点折算到 20-day mission。
3. delayed normalization recipe：NUBASE ground-state correction、per-family TT division guard、M-sampling inventory audit。
4. old `new_geo_re` 只是 1/10 coarse screen；current v3p5 exact-position authority 才是 full-stat promotion bar。
5. 必须产物：
   `fix5_source_manifest.json`,
   `fix5_benchmark_alignment.json`,
   `fix5_verification_verdict.json`,
   `fix5_promotion_decision.json`。
6. 1/10 gate 必须报告 `N_eff` 和 Poisson sigma，并使用 `fix5_benchmarks.json` 中的 `provisional_pass_formula` / `hard_fail_formula` / `inconclusive_if`。
7. old `new_geo_re` 的 0.0323 / 0.1515 只有在 `fix5_benchmark_alignment.json` 的 `decision == ALIGNED` 后才能做 pass/fail gate；否则只是历史参考。
8. append/merge 不是默认路线；默认 clean full-stat。append/merge 必须有 PASS 的 `fix5_merge_verdict.json`。

## 2. 子代理分工

如果环境支持 subagent / multi-agent tools，使用两个子代理；如果不支持，就在主对话中严格模拟两个独立 pass，不要让同一段逻辑既构建又审查。

### Subagent A — Builder

职责：

- 只基于 fix5 `.geo.setup` 创建 fix5 source cards，不修改 baseline/v3p5/BGO/new_geo_re authority outputs。
- 输出 `fix5_source_manifest.json`，字段按 `core_md/fix5_benchmarks.json` -> `required_artifacts.source_manifest`。
- 准备 `fix5_benchmark_alignment.json` 的证据：line window、active-shield thresholds、Compton/FoV、source-surface/far-field normalization、rate units。
- 生成 run manifests、命令行、环境、预期 SIM 输出路径。
- 在 Orchestrator 明确放行前，不启动昂贵 full-stat MC。

禁止：

- 不得把 baseline `.geo.setup` 写入任何 fix5 source card。
- 不得覆盖 current v3p5、BGO、old new_geo_re authority outputs。
- 不得把目录名里的 `fix5` 当作 provenance 证明。

### Subagent B — Verifier

职责：

- 只读审查 Builder 产物和后续 SIM/summary 输出。
- 发出 `fix5_verification_verdict.json`，每项包含 `{check, status, evidence_path, blocking}`。
- 检查 source cards 和 SIM headers 都指向 fix5 `.geo.setup`，且不含 baseline `.geo.setup`。
- 检查 prompt `1/sum(TT)` 归一化自洽。
- 检查 delayed normalization：`normalization_audit_groundstate_fix.json` PASS、NUBASE audit、M-sampling thresholds、W/collimator-origin delayed rows。
- 检查 `fix5_benchmark_alignment.json` 是否 `ALIGNED`；不 aligned 时 old `new_geo_re` 不得做 gate。
- 检查 Step05--Step08 是否读取 fix5 outputs，而不是 v3p5 fallback。
- 检查 full-stat promotion decision 是否满足 `promotion_thresholds`。

禁止：

- Verifier 不修改 source cards。
- Verifier 不替 Builder 补产物。
- Verifier 不用 prose 替代 deterministic file/script assertions。

### 主对话 — Orchestrator/Runner

职责：

- 持有 gate 和 stop rules。
- 调度 Builder / Verifier。
- 只有在 C0/C1/C1b 和 verification verdict 通过后，才启动 Runner。
- 先跑 1/10；如果 hard fail，停止；如果 inconclusive，加统计；如果 pass，再 clean full-stat。
- full-stat 结束后生成 `fix5_promotion_decision.json` 和最终 closure report。

## 3. 执行顺序

1. Phase 0：读取文档并汇报 checkpoint。
2. Phase 1：Builder 生成 fix5 source cards、source manifest、benchmark alignment 证据。
3. Phase 1 review：Verifier 审查 source provenance、alignment、geometry path。
4. Phase 2：通过后运行 1/10 prompt instant、activation buildup、delayed source、delayed transport。
5. Phase 3：运行 Step05；只在 provenance/normalization 通过后生成 Step06/07/08。
6. Phase 3 gate：按 `fix5_benchmarks.json` 的 prompt/delayed 1/10 公式判定 pass/fail/inconclusive。
7. Phase 4：若通过，默认 clean full-stat fix5；不要默认 append。
8. Phase 5：full-stat closure，比较 old `new_geo_re` 和 current v3p5；只有满足 promotion thresholds 才能说 fix5 可替代 v3p5。

## 4. 必须 fail closed

- source/SIM header 指向错误几何 -> 该 run 无效，必须重跑。
- 缺 `fix5_source_manifest.json` 或 `fix5_verification_verdict.json` -> 不得 gate。
- old `new_geo_re` benchmark 未 aligned -> 不得用它 pass/fail。
- delayed normalization 不可审计 -> 不得声称 delayed 更低。
- 1/10 统计不足 -> inconclusive，加统计，不得硬判。
- append/merge 没有 PASS merge verdict -> clean full-stat。
- full-stat 与 1/10 冲突 -> full-stat 结果优先。

开始工作时，先完成 Phase 0 checkpoint，然后给出 Builder/Verifier 的第一轮具体任务清单。
