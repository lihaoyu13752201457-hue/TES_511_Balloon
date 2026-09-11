# New Session Bootstrap

Paste the block below into a new Codex session when this engineering package is
the active task. It orients the session and points at the execution contract
(`HARNESS_MASS_MODEL_511_NEARFIELD_MIGRATION.md`).

```text
你正在接手 `/home/ubuntu/TES_511_Balloon` 中的 Mass_model_511 近场几何迁移工程。

Active engineering package:
`engineering/Mass_model_511_nearfield_migration_20260701/`

请先按序读取（只读，先核实再动手）：
1. `README.md`
2. `HARNESS_MASS_MODEL_511_NEARFIELD_MIGRATION.md`   ← 执行合同
3. `00_manifest/FINAL_STATUS.md`
4. `01_geometry/geometry_gate.md`
5. `04_bridge_resolution/bridge_resolution.md`
6. `05_optics_migration/optics_migration.md`          ← 新增：一体光学模型迁移记录
7. `06_smoke_closure/CONCLUSION.md`                   ← smoke-matrix Step05 闭合结论

当前状态（读 FINAL_STATUS 为准）：
- G0 authority `AUTHORITY_PASS` / G1 geometry `GEOMETRY_PASS`
- G2 source migration `SOURCE_COPY_PREPARED`
- G5 optics bridge `OPTICS_BRIDGE_NOT_REQUIRED_DETECTOR_ONLY`
- G3/G4 detector transport `PASS_G3_G4_DETECTOR_TRANSPORT_SMOKE`
- G6 smoke-matrix detector response closure `PASS_SMOKE_MATRIX_CLOSURE`
- 05_optics_migration `OPTICS_GEOMETRY_MIGRATED_AND_MC_SMOKE_VERIFIED_IN_REPO`（平行记录）

任务边界（硬约束，别踩）：
- 不回写 / 覆盖 `engineering/nearfield_mass_impact_20260625/` 的任何结论或文件。
- 不改 source authority cards；本地副本已在 `03_source_migration/source_dirs/Mass_model_511/`，
  只允许改各卡里的 `Geometry` 行与 `# geometry_setup=` 注释。
- Step05 / normalization / cuts 权威保持不变。
- 当前 candidate detector geometry：
  `outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

已执行的主工作（detector-only 背景链，G3/G4）：
- baseline 与 `candidate_Mass_model_511` prompt / buildup / delayed S0/S1
  transport 已执行；见 `03_detector_transport/transport_gate.md` 与 delayed
  branch manifests。
- focused signal smoke 已执行；见 `06_smoke_closure/signal_transport_manifest.json`。
- Step05 smoke-matrix detector-response closure 已完成；见
  `06_smoke_closure/CONCLUSION.md`。
- 该结果仍是 smoke-matrix closure；full-stat 背景率/no-effect release 与
  Step06--Step08 mission-axis 再生成未完成。

关于新光学模型（`05_optics_migration/`，重要边界，别搞错）：
- 它是一个"可用的光学几何模型"的平行迁移记录：一体版（1245 个 Ge tile + G10/Al 支撑，
  单模板 MB_Tile），已在库内 cosima 验证（`CheckForOverlaps` 无重叠 + 可输运）。
- 它【未】耦合进探测器背景输运链；G5 仍是 detector-only `NOT_REQUIRED`。
  别把它翻成"已引入光学模型"，也别拿它宣称任何背景率。
- 若要接背景：必须另建显式 optics→detector 桥，不能塞进 G5。
- 若要推进光学侧本身（可选，见 `05_optics_migration/optics_migration.md` 的 allowed_next_steps）：
  抽取逐环输运后 A_eff；给 5 个非 511 能量生成外部 XOP/CRYSTAL 曲线。
  在此之前，per-energy A_eff 仍是 design-stage 估计。

诚实机制：
- 逐项核实，不继承"最严"；判断以 gate/manifest 里写死的状态为准。
- 每步产物落对应 gate 目录或 `05_optics_migration/verify/`，不覆盖旧结论。
- 已证事实包括"几何/源就绪"、"G3/G4 smoke transport"、和
  "`PASS_SMOKE_MATRIX_CLOSURE`"。Full-stat 背景/no-effect/发表级结果未证，别宣称。
```

## Quick File Map

- Harness (execution contract): `HARNESS_MASS_MODEL_511_NEARFIELD_MIGRATION.md`
- Final status: `00_manifest/FINAL_STATUS.md`
- Authority manifest: `00_manifest/authority_manifest.json`
- Geometry gate: `01_geometry/geometry_gate.md`
- Source copies: `03_source_migration/source_dirs/Mass_model_511/`
- Bridge resolution: `04_bridge_resolution/bridge_resolution.md`
- Optics migration (parallel): `05_optics_migration/optics_migration.md` / `.json`
  - core geo: `05_optics_migration/geometry/MultibandUnified_TilesAndSupport_f10m.geo`
  - repo-local runnable: `05_optics_migration/geometry/multiband_unified_migrated.setup` / `.source`
  - in-repo verify: `05_optics_migration/verify/`
  - regen: `python3 05_optics_migration/build_optics_migration.py`
- Run plan: `02_run_plan/smoke_run_matrix.csv`
- Smoke closure conclusion: `06_smoke_closure/CONCLUSION.md`
- Claim boundary: `11_manuscript_support/claim_boundary.md`

## Two execution targets (pick per the ask)

| Target | What to run | Status now |
| --- | --- | --- |
| Detector background chain (main) | Smoke matrix through G3/G4 transport and Step05 detector-response closure | `PASS_SMOKE_MATRIX_CLOSURE` |
| Optics migration (parallel) | Already verified in-repo; only advance the `allowed_next_steps` if asked — never fold into G5 | `MIGRATED_AND_MC_SMOKE_VERIFIED_IN_REPO` |
