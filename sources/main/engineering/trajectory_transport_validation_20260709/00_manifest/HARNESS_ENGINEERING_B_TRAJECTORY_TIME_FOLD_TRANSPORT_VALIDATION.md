---
document_type: harness_engineering
project: TES_511_BALLOON
workstream: trajectory-time-fold-transport-validation
version: 1.0
status: ready-for-codex
primary_language: zh-CN
created: 2026-06-25
repo_root_hint: /home/ubuntu/TES_511_Balloon
public_repository: lihaoyu13752201457-hue/TES_511_Balloon
execution_style: bounded-multipoint-transport-validation
current_step06_path_hint: stepwise_maintenance/step06_mission_time_variation
trajectory_policy: validate the existing synthetic 20-day profile at one reference and four off-reference trajectory points
geometry_policy: use the current paper-facing detector geometry unless an explicit completed promotion manifest from the mass-model study exists
source_policy: rebuild EXPACS/PARMA sources at each selected latitude/longitude/altitude with the same angular/energy/source-surface semantics
prompt_validation_policy: direct Cosima transport versus current analytic prompt curve
activation_validation_policy: state/volume production transport at selected points, history-aware activity integration, and time-specific exact-position delayed replay
selection_policy: current Step05 hash and all cuts frozen
manuscript_policy: produce validation or correction text and a numerical-promotion manifest; no silent manuscript edits
context_packet_policy: minimum task-specific allowlist; independent prompt, activation, delayed, and verification agents
default_flags:
  APPLY_MANUSCRIPT_CHANGES: false
  ALLOW_HEAVY_RUN: false
  ALLOW_TRAJECTORY_EDIT: false
  ALLOW_SOURCE_PROXY_SUBSTITUTION: false
  ALLOW_UNIFORM_PER_BQ_AS_FINAL_WITHOUT_TEST: false
  ALLOW_STEP07_STEP08_PROMOTION: false
  ACTIVATE_REPO_TASK_POINTER: false
---

# 0. 新 Codex Session 启动提示词

```text
你正在接手 `/home/ubuntu/TES_511_Balloon` 的 mission-time trajectory transport validation 工程。

当前 Step06 是 synthetic 20-day trajectory 的 rate-level fold：latitude约34±0.25 deg，longitude约100±0.25 deg，altitude 38.75±2.5 km。它没有在每个时间 bin 重跑 Cosima。Prompt curve使用 EXPACS/PARMA time-bin spectra与当前 480–550 keV final-prompt particle weights进行折叠；delayed curve先用粒子加权production scale驱动逐核素ODE，再用uniform per-Bq detector-response proxy转换成rate。

本任务不是重做整条20日81-bin全输运，而是在 day-15 reference 加四个预注册的其他轨迹点重建真实 source cards并运行 matched prompt/buildup/delayed transport，检验现有解析曲线的幅度、趋势和 delayed处理是否可信。

先只读：
- 本 harness；
- `AGENTS.md`、`README.md`、`CLOSURE_DIGEST_20260624.md`；
- current Step05 authority；
- `stepwise_maintenance/step06_mission_time_variation/README.md`、code、trajectory_profile.csv、summary JSON、background_time_variation.csv、activity_by_time_nuclide_volume.csv；
- current EXPACS/PARMA source builder/driver、source migration manifest和prompt normalization audit；
- current activation inventory、exact-position delayed builder、selected delayed decomposition；
- current Step07/Step08 outputs和manuscript。

先执行 WP00 authority lock、WP01 validation-point selection和WP02 source-card generation audit。不得直接运行full-stat。

非协商边界：
- 不修改 synthetic trajectory；本任务验证它，不优化它；
- 不改变 detector geometry、60 cm source radius、20 equal-mu bins、Step05 cuts、W2或detector response；
- 各时间点必须使用该点真实的 altitude/latitude/longitude EXPACS/PARMA spectra，而不是只乘一个scalar；
- prompt validation比较direct transport与analytic curve；
- delayed validation必须区分 instantaneous production、history-integrated inventory和detector response；不能用“该点恒定照射若干天”冒充真实飞行历史；
- time-specific delayed source必须保留nuclide/volume/production-position信息；
- smoke低统计不能宣布curve正确；必须用置信区间和预注册阈值；
- 若解析曲线通过，论文加入validation段落；若失败，生成Step06修正和Step07/08重算请求；默认不直接改正文。

请创建 `engineering/trajectory_transport_validation_YYYYMMDD/`，先生成authority manifest、validation-point table、source-generation plan和resource estimate。
```

# 1. 目的与当前风险

当前 Step06 具有明确优点：

- 使用 official EXPACS/PARMA driver形成81-bin环境变化；
- prompt按粒子族折叠；
- delayed逐nuclide/volume解ODE；
- day-15与Step05精确闭合。

但它仍是解析/响应折叠，不是 time-bin detector transport。需要验证的风险包括：

1. 粒子谱形随 altitude/geomagnetic position变化，单一particle-family scalar可能不能正确预测 W2；
2. current prompt weights来自有限的480--550 keV final events，未必代表 W2；
3. 当前 delayed-production driver对所有nuclide/volume使用粒子加权scale，可能忽略reaction threshold和spectral-shape差异；
4. uniform per-Bq delayed response忽略 I-128、Cu-64、Cu-62和不同位置的 detector coupling差异；
5. delayed at time \(t\) 取决于此前整个irradiation history，不能只模拟该点瞬时环境；
6. synthetic trajectory不是telemetry，即使验证通过，结论也只覆盖该profile envelope。

# 2. 冻结边界

## 2.1 Trajectory不修改

当前 profile为：

```text
20 days
0.25 day nominal bins
81 time points
altitude_ref = 38.75 km
altitude range = 36.25--41.25 km
latitude center = 34.0 deg, max offset 0.25 deg
longitude center = 100.0 deg, max offset 0.25 deg
```

本工程不改变振幅、相位或轨迹函数。

## 2.2 Geometry authority

默认使用新 session开始时的 current paper-facing geometry。

若质量模型工程A已完成并存在：

```text
COMPLETE_MATERIAL_EFFECT_REQUIRES_PROMOTION_DECISION
```

但尚未用户promote，则仍使用旧 paper baseline。

只有显式 promotion manifest 才允许切换到 NF2。

## 2.3 Analysis冻结

- current Step05 code hash；
- 50 keV active shield veto；
- 1 us coincidence；
- W2；
- topology/FoV；
- detector response；
- day-15 source normalization。

# 3. 预注册 validation points

必须包含 day-15 reference和至少四个off-reference点。

当前 trajectory_profile 推荐点：

| ID | day | altitude km | latitude deg | longitude deg | Rc GV | analytic prompt scale | 选择理由 |
|---|---:|---:|---:|---:|---:|---:|---|
| REF | 15.00 | 38.75 | 34.0000 | 100.0000 | 11.0000 | 1.000000 | day-15 authority |
| L1 | 3.75 | 36.25 | 34.1559 | 99.7500 | 10.9800 | 1.052988 | minimum altitude / maximum prompt driver |
| L2 | 18.75 | 36.25 | 33.9444 | 100.1250 | 11.0082 | 1.052448 | same minimum altitude, different geographic/rigidity condition |
| H1 | 6.25 | 41.25 | 33.7500 | 100.0434 | 11.0213 | 0.964753 | maximum altitude / minimum prompt driver |
| M1 | 10.00 | 38.75 | 34.2437 | 100.0855 | 10.9831 | 1.000308 | reference altitude, different latitude/longitude/Rc |

orchestrator必须从 current trajectory CSV重新读取数值，不得盲目硬编码。若 profile变化，使用同一规则重新选择：

1. minimum altitude；
2. maximum altitude且minimum prompt scale；
3. 与minimum altitude相同或最接近、但 \(|Rc-Rc_{L1}|\) 最大的点；
4. altitude在reference ±0.05 km内、且 \(|Rc-Rc_{ref}|\) 最大的点；
5. day-15 reference。

输出：

```text
validation_points.csv
validation_point_selection.json
```

# 4. 关键数学定义

## 4.1 Analytic prompt prediction

当前 curve：

\[
R^{\rm ana}_{p}(t)=R_{p,\rm ref}\,S_p(t),
\]

其中 \(S_p(t)\) 是粒子族谱/flux的解析折叠。

Direct transport得到：

\[
R^{\rm MC}_{p}(t)=\sum_{i\in p,t,\rm selected} w_i.
\]

比较：

\[
Q_p(t)=\frac{R^{\rm MC}_p(t)/R^{\rm MC}_p(t_{ref})}{S_p(t)}.
\]

理想情况下 \(Q_p=1\)。归一化到同一reference可消除部分绝对rate MC系统误差。

## 4.2 Delayed production

对state/volume \(k\)：

\[
P_k(t_j)=\frac{N_{k,j}}{T_j}.
\]

当前 analytic driver近似：

\[
P_k^{\rm ana}(t)=P_k(t_{ref})\,S_{\rm prod}(t).
\]

Transport validation直接比较：

\[
Q^{\rm prod}_k(t)=\frac{P_k^{\rm MC}(t)/P_k^{\rm MC}(t_{ref})}{S_{\rm prod}(t)}.
\]

## 4.3 History-aware activity

必须用从mission start到 \(t\) 的production history：

\[
\frac{dN_k}{dt}=P_k(t)-\lambda_k N_k(t)+\sum_m b_{m\to k}\lambda_mN_m(t).
\]

禁止用“在位置 \(t_j\) 的恒定source照射 \(t_j\) 天”替代。

## 4.4 Detector response matrix

uniform per-Bq proxy仅可作为被检验模型：

\[
R_d^{\rm uniform}(t)=A_{\rm total}(t)\,\epsilon_{\rm uniform}.
\]

推荐建立至少下列response classes：

```text
Cu-64 near focal-plane Cu
Cu-62 near focal-plane Cu
I-128 in CsI
other beta-plus states
other non-beta-plus states
```

\[
R_d^{\rm matrix}(t)=\sum_c A_c(t)\epsilon_c.
\]

# 5. 输出目录

```text
engineering/trajectory_transport_validation_YYYYMMDD/
├── 00_manifest/
│   ├── authority_manifest.json
│   ├── environment.json
│   ├── hashes.sha256
│   ├── decision_log.md
│   └── FINAL_STATUS.md
├── 01_points/
│   ├── trajectory_profile_frozen.csv
│   ├── validation_points.csv
│   ├── validation_point_selection.json
│   └── analytic_predictions_at_points.csv
├── 02_sources/
│   ├── source_generation_manifest.json
│   ├── per_point_source_cards/
│   ├── source_flux_closure.csv
│   ├── spectral_shape_comparison.csv
│   └── source_audit.md
├── 03_run_plan/
│   ├── smoke_matrix.csv
│   ├── targeted_matrix.csv
│   ├── full_matrix.csv
│   ├── seed_manifest.json
│   └── resource_estimate.json
├── 04_prompt_smoke/
│   ├── per_point/
│   ├── prompt_direct_vs_analytic.csv
│   ├── prompt_by_particle.csv
│   ├── prompt_by_energy_band.csv
│   └── prompt_smoke_verdict.json
├── 05_activation_smoke/
│   ├── per_point/
│   ├── production_state_volume.csv
│   ├── production_direct_vs_analytic.csv
│   ├── rpip_position_comparison.csv
│   └── activation_smoke_verdict.json
├── 06_history_model/
│   ├── transport_informed_production_grid.csv
│   ├── bateman_activity_by_time.csv
│   ├── analytic_vs_transport_activity.csv
│   ├── response_class_matrix.csv
│   └── history_model_verdict.json
├── 07_delayed_sources/
│   ├── per_validation_time/
│   ├── exactpos_source_manifests/
│   ├── activity_closure.csv
│   └── position_sampling_audit.csv
├── 08_delayed_smoke/
│   ├── per_point/
│   ├── delayed_direct_vs_analytic.csv
│   ├── delayed_by_class.csv
│   └── delayed_smoke_verdict.json
├── 09_targeted_or_full/
├── 10_curve_validation/
│   ├── prompt_curve_residuals.csv
│   ├── delayed_curve_residuals.csv
│   ├── curve_metrics.json
│   ├── revised_curve_if_needed.csv
│   ├── validation_decision.json
│   └── figures/
├── 11_step06_step08_integration/
└── 12_manuscript_support/
    ├── manuscript_insertions_en.md
    ├── manuscript_change_request.md
    ├── manuscript_numbers_manifest.json
    ├── manuscript_claim_boundary.md
    ├── supplement_validation_table.md
    └── paper_impact_summary_zh.md
```

# 6. Agent与上下文隔离

```text
orchestrator
  ├── authority_agent
  ├── point_selection_agent
  ├── source_agent
  ├── prompt_transport_agent
  ├── activation_transport_agent
  ├── history_activity_agent
  ├── delayed_source_agent
  ├── delayed_transport_agent
  ├── verifier_agent
  └── manuscript_agent
```

Blinding：

- source agent不读取当前 curve residual预期；
- prompt agent只获得point ID，不获得analytic scale，直到rates冻结；
- activation agent不读取 delayed rate curve；
- verifier独立计算 analytic/direct ratios；
- manuscript agent只读取verified outputs。

# 7. 状态机

```text
S0 LOCK_AUTHORITY
 -> G0 PASS | BLOCKED_AUTHORITY

S1 SELECT_POINTS
 -> G1 POINTS_FROZEN

S2 BUILD_AND_AUDIT_SOURCES
 -> G2 SOURCES_PASS | BLOCKED_SOURCE_DRIVER

S3 RUN_PROMPT_SMOKE
 -> G3 PROMPT_SMOKE_COMPLETE

S4 RUN_ACTIVATION_SMOKE
 -> G4 ACTIVATION_SMOKE_COMPLETE

S5 BUILD_HISTORY_AWARE_MODEL
 -> G5 HISTORY_MODEL_COMPLETE | BLOCKED_HISTORY_MODEL

S6 BUILD_TIME_SPECIFIC_DELAYED_SOURCES
 -> G6 DELAYED_SOURCES_PASS | BLOCKED_EXACTPOS_HISTORY

S7 RUN_DELAYED_SMOKE
 -> G7 DELAYED_SMOKE_COMPLETE

S8 DECIDE_ESCALATION
 -> CURVE_VALIDATED_SMOKE
  | TARGETED_REQUIRED
  | FULL_REQUIRED
  | INCONCLUSIVE_RESOURCE_LIMIT

S9 RUN_REQUIRED_ESCALATION
 -> G9 COMPLETE | RESOURCE_BLOCKED

S10 VERIFY_CURVES
 -> G10 VALIDATED | MODEL_CORRECTION_REQUIRED

S11 UPDATE_STEP06/07/08_SUPPORT
 -> G11 SUPPORT_COMPLETE

S12 BUILD_MANUSCRIPT_SUPPORT
 -> DONE
```

# 8. WP00：Authority lock

必须定位：

- current trajectory profile和Step06 code/summary；
- current Step05 rates/event catalog/selection hash；
- current source driver和EXPACS/PARMA tables/executable；
- current fix5 source migration manifest；
- current prompt/buildup runner；
- current activation inventory和exact-position builder；
- current selected delayed decomposition；
- current Step07/Step08 outputs；
- current manuscript；
- geometry authority或A工程promotion manifest。

记录所有 hashes。若A工程正在运行但未promotion，B不等待，使用当前paper baseline。

# 9. WP01：Point selection and analytic freeze

读取 current CSV，冻结validation points。为每点保存：

```text
time_bin_id
day_mid
dt_s
altitude_km
latitude_deg
longitude_deg
Rc_GV
depth_g_cm2
T_atm_511
prompt_scale_to_day15
delayed_production_scale_to_day15
analytic_activity_scale_to_day15
analytic_prompt/delayed raw, veto, final rates
```

在任何transport结果可见之前写hash并freeze。

# 10. WP02：Per-point source generation

## 10.1 Source cards

对 REF/L1/L2/H1/M1分别运行 official EXPACS/PARMA driver，生成八族 fullsphere20 source cards。

保持：

- 20 equal-mu bins；
- energy support/bins；
- particle mapping；
- 60 cm source radius；
- detector orientation；
- source-card syntax；
- seed/job topology。

## 10.2 Audit

逐点逐族输出：

- total flux；
- bin flux；
- spectral ratio to REF；
- angular ratio；
- source-card/manifest closure；
- observation-time formula；
- generated-events/weights plan。

禁止直接把 `prompt_scale_to_day15` 写回reference source card作为替代。

# 11. WP03：Smoke statistics

## 11.1 Prompt/activation production

每点：

```text
gamma = 1,000,000
other species = 0.1 * current full-stat generated counts
same split/replica topology
same deterministic seed schedule by point and mode
instant + buildup
```

REF必须在同一session重跑smoke，不能只拿旧full-stat作统计比较。

## 11.2 Delayed

先做：

```text
250,000 decays per validation time
```

仅用于syntax、normalization和broad-band趋势。

若W2 expected effective events <10，禁止据此验证W2；进入targeted level：

```text
>= 1,000,000 decays per key time
```

# 12. WP04：Prompt direct-vs-analytic

每点和REF比较：

- by particle family；
- raw/active-veto/final；
- W2；
- 480--550；
- all TES >0；
- broad bands；
- multiplicity；
- annihilation-origin fractions。

## 12.1 Primary metric

\[
Q(t)=\frac{R^{MC}(t)/R^{MC}(REF)}{S^{analytic}(t)}.
\]

输出paired或independent CI。

## 12.2 Current weight audit

必须单独比较：

```text
current 480-550 final-prompt family weights
W2-specific family weights
source-rate weights
transport-derived bin-resolved weights if statistics permit
```

若current weights由少量/zero-count families决定，报告其Poisson uncertainty。

# 13. WP05：Activation production transport

逐点从 buildup `.dat` 和RPIP提取：

```text
production_family
raw_volume
ZA
excitation_state
production_rate
RPIP positions
```

比较：

- total production；
- by family；
- by material/volume；
- Cu-64、Cu-62、I-128；
- all states contributing ≥0.5% activity；
- all known W2-selected states regardless of activity fraction。

检测 spectrum-shape效应：若不同nuclides的production ratio明显不等于统一scalar，current delayed-production driver需要response matrix。

# 14. WP06：Transport-informed history model

## 14.1 Interpolation

使用 selected validation points构建 \(P_k(alt,R_c)\) 的低阶、预注册interpolator。首选：

- altitude线性/二次项；
- rigidity一阶项；
- 不超过available points可支持的参数数；
- leave-one-point-out检查。

禁止高阶拟合过拟合5个点。

## 14.2 ODE/Bateman

在冻结的81-bin trajectory上积分每个nuclide/volume。使用 current native/direct chain authority和相同half-life data。

输出：

- transport-informed activity curve；
- current analytic activity curve；
- per-state residual；
- total residual；
- day15 closure。

## 14.3 Position distribution

比较各点RPIP：

- volume fractions；
- radial/z distributions；
- distance to TES；
- selected key states。

若 distributions稳定，允许建立pooled basis并给出误差；若变化material，time-specific source必须按history贡献混合各点positions。

# 15. WP07：Delayed response matrix

Current uniform per-Bq必须被检验。

## 15.1 Minimum classes

```text
C1 Cu-64 focal-plane Cu
C2 Cu-62 focal-plane Cu
C3 I-128 CsI
C4 other beta-plus
C5 other decays
```

每类计算：

```text
raw cps/Bq
active-veto cps/Bq
final cps/Bq
W2 cps/Bq
broad-band cps/Bq
MC uncertainty
```

可使用现有 selected-event decomposition加 targeted decay replay。

## 15.2 Uniform proxy acceptance

只有当 matrix curve与uniform curve在所有validation times的差异95% CI位于±20%内，才可继续使用uniform per-Bq作为论文主fold。

否则Step06应升级为class/state response matrix。

# 16. WP08：Time-specific exact-position delayed sources

对REF/L1/L2/H1/M1：

1. 从history-aware inventory得到time-specific activity by state/volume；
2. 从对应或history-weighted RPIP basis抽样真实positions；
3. 保留state identity和production family；
4. source activity完全闭合；
5. 相同sampling seed policy；
6. 禁止将全部activity均匀重新分配到day15 positions而不做position-stability audit。

若parent-daughter feeding产生无direct position states，沿用current v2/native boundary并显式标记fallback。

# 17. Smoke validation gates

## 17.1 Prompt curve通过条件

所有点满足：

- 480--550 final：\(|Q-1|\) 的95% CI位于±10%；
- W2 final：95% CI位于±15%；
- eplus/neutron family：95% CI位于±20%；
- normalized RMSE ≤10%（480--550）且≤15%（W2）；
- predicted trend direction正确；
- 无单点 >20%且 >3σ偏差。

若W2统计不足，但480--550通过且W2 CI仍允许>15%，进入targeted，不得直接PASS。

## 17.2 Activation production通过条件

- total production ratio residual ≤15%；
- total day-specific activity residual ≤15%；
- Cu-64/Cu-62 production/activity residual ≤25%；
- no key W2 state >35%且>3σ；
- position distribution变化不会导致 >20% detector-response上界。

## 17.3 Delayed rate curve通过条件

- final W2 direct/analytic residual 95% CI位于±25%；
- final 50--8000 residual位于±20%；
- normalized RMSE ≤20%；
- L1/L2 same-altitude pair的差异方向与rigidity/latitude prediction一致或统计相容；
- no point >35%且>3σ；
- response-matrix vs uniform proxy差异≤20%。

## 17.4 `CURVE_VALIDATED_SMOKE`

只有prompt、production、history和delayed全部满足且统计功效足够才允许。

# 18. Escalation policy

## 18.1 Targeted level

优先增加最有判别力的统计：

```text
prompt eplus/neutron at L1/H1/REF
activation neutron/proton/gamma at L1/H1/REF
Cu64/Cu62 targeted delayed replay
>=1M delayed decays at REF/L1/H1
```

L2/M1主要检验geographic effect；若analytic predicted difference <1%，不要求用MC解析出该微小差异，只要求结果给出兼容上界。

## 18.2 Full level

任一触发：

- prompt W2 residual point estimate ≥20%；
- prompt broad residual ≥15%；
- key production/activity residual ≥30%；
- delayed W2 residual ≥35%；
- current scalar与state-response matrix给出相反趋势；
- analytic curve落在direct 99% CI外；
- targeted后仍无法把CI压到acceptance threshold内。

Full-stat不要求81个点；至少：

```text
REF
L1 minimum altitude
H1 maximum altitude
one same-altitude geographic control
```

Delayed full至少3 source-position seeds或current convergence contract。

# 19. Curve correction policy

若验证失败，不允许只乘经验修正因子。按归因选择：

## Prompt failure

- family weights问题 -> W2-specific或energy-bin response matrix；
- spectral-shape问题 -> flux-bin response fold；
- source generation问题 ->修正source driver并重审计。

## Delayed production failure

- state ratios不统一 -> state/volume production response matrix；
- history问题 -> transport-informed \(P_k(t)\) grid；
- position变化 -> time-dependent RPIP mixture。

## Delayed response failure

- uniform per-Bq失败 -> class/state-specific cps/Bq matrix。

修正后重建Step06，并重新运行Step07/Step08；旧curve标记STALE，不得部分混用。

# 20. Manuscript integration

## 20.1 验证通过

加入Methods：

- synthetic trajectory定义；
- five-point direct transport validation；
- per-point source rebuild；
- prompt和activation comparison；
- delayed history/response matrix audit；
- acceptance thresholds。

加入Results：

- point table；
- analytic/direct ratios；
- maximum residual/RMSE；
- delayed response proxy bound。

推荐英文表述：

> The rate-level trajectory fold was checked with direct prompt and activation transport at the day-15 reference and four off-reference altitude/geomagnetic locations. Across the tested trajectory envelope, the direct-to-analytic ratios were [range] for the prompt component and [range] for the delayed component after history-aware activity folding. The largest residuals were [values], supporting use of the analytic curve within the quoted validation bounds.

Discussion必须说明：trajectory是synthetic，不是flight telemetry。

## 20.2 验证失败

生成：

- Step06 correction request；
- revised curve；
- Step07/08 rerun matrix；
- old/new number ledger；
- Abstract/Results/Discussion/Conclusion更新建议；
- significance/flux threshold重算需求。

不得仅修改一张time-curve图。

## 20.3 Mandatory files

```text
manuscript_insertions_en.md
manuscript_change_request.md
manuscript_numbers_manifest.json
manuscript_claim_boundary.md
supplement_validation_table.md
paper_impact_summary_zh.md
```

# 21. 测试要求

## Source

- per-point source flux closure；
- equal-mu angular closure；
- 60 cm radius；
- observation time；
- job seeds；
- geometry path；
- no scalar-only proxy source。

## Transport

- baseline REF smoke reproduces current response withinMC；
- event weights sum；
- sum_w2；
- per-family rates；
- parser/selection hash。

## History

- constant-production analytic test；
- single isotope exact solution；
- parent-daughter test；
- day15 closure；
- grid-step convergence；
- interpolation leave-one-out。

## Delayed source

- activity closure；
- state identity；
- volume/position support；
- sampling reproducibility；
- class-response closure。

# 22. Failure / legal endpoints

```text
BLOCKED_AMBIGUOUS_AUTHORITY
BLOCKED_SOURCE_DRIVER
BLOCKED_EXPACS_ENVIRONMENT
BLOCKED_HISTORY_MODEL
BLOCKED_EXACTPOS_HISTORY
PROMPT_SMOKE_INCONCLUSIVE
ACTIVATION_SMOKE_INCONCLUSIVE
DELAYED_SMOKE_INCONCLUSIVE
CURVE_VALIDATED_SMOKE
CURVE_VALIDATED_FULL
MODEL_CORRECTION_REQUIRED
RESOURCE_BLOCKED_WITH_VALIDATION_PLAN
COMPLETE_VALIDATED_ANALYTIC_CURVE
COMPLETE_REVISED_TIME_FOLD_REQUIRED
```

# 23. FINAL_STATUS 模板

```text
# FINAL_STATUS

repo_head:
repo_status:
harness_version:
geometry_authority:
step05_hash:
trajectory_hash:
source_driver_hash:

Validation points:
| ID | day | alt | lat | lon | Rc | analytic scale | status |
|---|---:|---:|---:|---:|---:|---:|---|

| Gate | Status | Evidence | Blocking | Next action |
|---|---|---|---:|---|
| G0 authority | | | | |
| G1 points | | | | |
| G2 sources | | | | |
| G3 prompt | | | | |
| G4 activation | | | | |
| G5 history | | | | |
| G6 delayed source | | | | |
| G7 delayed transport | | | | |
| G8 escalation | | | | |
| G9 full/targeted | | | | |
| G10 curve verdict | | | | |
| G11 Step06-08 support | | | | |
| G12 manuscript | | | | |

Prompt metrics:
- 480-550 NRMSE:
- W2 NRMSE:
- max residual:
- family residuals:

Delayed metrics:
- production NRMSE:
- total activity NRMSE:
- Cu64/Cu62 residuals:
- final W2 NRMSE:
- uniform-vs-matrix residual:

Final verdict:
- COMPLETE_VALIDATED_ANALYTIC_CURVE
- COMPLETE_REVISED_TIME_FOLD_REQUIRED
- RESOURCE_BLOCKED_WITH_VALIDATION_PLAN
- BLOCKED_...

Manuscript support generated:
- ...

Files intentionally not modified:
- trajectory definition
- baseline geometry/source cards
- current Step05 authority
- current Step06/07/08 outputs
- manuscript source
```

# 24. Orchestrator 最终指令

```text
1. Lock all current authorities and hashes.
2. Freeze REF plus four off-reference points before seeing transport results.
3. Rebuild actual EXPACS/PARMA source cards at every point; do not use scalar-rescaled reference cards.
4. Audit source flux, angular bins, radius, observation time, and weights.
5. Run matched 0.1-full prompt and buildup smoke at all points, including a new REF smoke.
6. Compare direct prompt rates to the current analytic curve by species, energy band, and selection stage.
7. Build state/volume activation-production ratios at each point.
8. Construct a transport-informed, history-aware activity model over the frozen 81-bin trajectory.
9. Test the current uniform per-Bq delayed-response proxy against a minimum class-specific response matrix.
10. Build time-specific production-position-sampled delayed sources for validation times.
11. Run delayed smoke; do not use low-count W2 zeros as evidence.
12. Apply preregistered gates; run targeted statistics before full-stat when appropriate.
13. If the curve passes, generate validation text and bounds.
14. If it fails, generate a corrected Step06 model and Step07/08 rerun request; do not silently patch numbers.
15. Generate manuscript-support artifacts for either outcome.
16. End with FINAL_STATUS.md.
```
