# Codex handoff — verify analytic trajectory-curve accuracy

**Date:** 2026-07-09  
**Package:** `engineering/trajectory_transport_validation_20260709/`  
**Primary goal for the next agent:**  
**用多点直接输运（Cosima）检验 Step06 解析外推曲线是否准确**，并把残差写成可审计的 claim 级别（不是“看起来差不多”）。

---

## 1. 任务一句话

当前主分析用 **day-15 锚定的解析时间折叠**（Step06）把 20 天轨迹上的 prompt / activation / signal 外推成率与显著性曲线。  
历史 Fable5 工作已证明：**旧“单标量”解析曲线会被多点直接输运证伪**；修正后的五层/粒子族模型曾改善吻合，但包体丢失、主线未晋升。

**你现在要做的是：**在 **Mass_model_511** 几何与现有轨迹点上，**重新用直接模拟验证解析外推是否成立**，明确：

- 哪些通道（prompt / activation / signal / W2 / delayed）被验证到什么残差；
- 旧单标量是否仍失败；
- 是否需要族-response 修正曲线才能与 MC 重合；
- 结论能否晋升到文稿（默认 **不能** 在 incomplete 时宣称 full validation）。

---

## 2. 验证对象（“解析外推曲线”指什么）

权威时间曲线来自 Step06 trajectory profile（本包装冻副本）：

| 曲线 | CSV 列 | 物理含义 |
|------|--------|----------|
| Prompt background scale | `prompt_scale_to_day15` | 本地瞬发本底相对 day-15 的标量外推 |
| Activation production scale | `delayed_production_scale_to_day15` | 活化产生率标量（旧模型与 prompt 共用单标量） |
| Signal (atm transmission) | `science_atm_scale_to_day15` / `T_atm_511` | 天体 511 透过率相对 day-15 |

文件：

- `01_points/trajectory_profile_frozen.csv`（= Mass_model Step06 profile，已核对 byte-identical）
- `01_points/validation_points.csv` — 冻结验证点 **REF / L1 / L2 / H1**
- `01_points/analytic_predictions_at_points.csv`

判据（相对 day-15 REF 归一）：

\[
Q(t)=\frac{R^{\mathrm{MC}}(t)/R^{\mathrm{MC}}(\mathrm{REF})}{S^{\mathrm{analytic}}(t)}
\]

理想 \(Q\approx 1\)。若 \(Q\) 系统偏离 1，则解析外推在该通道失败或需改模型。

**点位（必须保留）：**

| ID | day | 角色 |
|----|-----|------|
| REF | 15.0 | 归一锚点 |
| L1 | 3.75 | 低空 / 早期 |
| H1 | 6.25 | 高空 |
| L2 | 18.75 | 低空 / 晚期 |

---

## 3. 已完成（可复用，勿推倒重来）

### 3.1 工程包与管线

- 活包：`engineering/trajectory_transport_validation_20260709/`
- 几何：Mass_model_511 megalib proxy  
  `outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/`
- Live PARMA：**必须** `cwd=parma_cpp` 跑 `phase2_parma_grid_driver`（否则全零通量）
- 角通量：equal-μ，`dΩ = 2π Δμ`，`Δμ=0.1`
- HTsim **能量字段 index=4**（不是 5；5 是 time）

### 3.2 已跑通的 Cosima 矩阵

| 战役 | 事件数/点 | 路径 | 状态 |
|------|-----------|------|------|
| Smoke | e+ 50k / n 30k / γ 60k | `04_prompt_smoke/` | 12/12 OK |
| **Targeted** | **e+ 1e6 / n 2e5 / γ 5e5** | `05_targeted_stats/` | **12/12 OK** |

脚本：

- `scripts/run_targeted_stats_escalation.py`
- `scripts/extract_targeted_stats.py`
- `scripts/plot_analytic_curve_vs_mc.py`
- `scripts/plot_fable5_style_two_figures.py`
- 单测：`scripts/test_extract_targeted_stats.py`（4/4 OK）

### 3.3 已得到的核心物理结论（prompt 通道，粗 TES proxy）

Live PARMA 环境 vs 解析 \(S_{\rm prompt}\)（e+）：

| Point | \(Q_{\rm env}(e+)\) |
|-------|---------------------:|
| L1 | ~1.07 |
| H1 | ~0.93 |
| L2 | ~1.06 |

Targeted Cosima **e+ 480–550 band** vs analytic / vs live PARMA：

| Point | \(Q_{\rm band}\) vs analytic | \(Q_{\rm band}\) vs live PARMA |
|-------|-----------------------------:|-------------------------------:|
| L1 | **1.069** | **1.000** |
| H1 | **0.933** | **1.003** |
| L2 | **1.053** | **0.994** |

**解释：**

- MC **跟踪 live PARMA 通量**，**不跟踪** 旧单标量 \(S_{\rm prompt}\)。
- e+ band 已 ~5e4 计数/点 → 残差是 **系统差**，不是统计噪声。
- 因此：**仅就 prompt 粗 TES/band 代理而言，旧解析外推曲线已被证伪约 ±7% 量级。**

n / γ 也有 gen-rate 与粗 TES，但 **480–550 band 计数仍低（O(10²)）**，不能当 W2 证据。

### 3.4 Claim 级别（必须遵守）

当前正式 claim：

```text
TARGETED_STATS_NOT_FULL4
```

**明确不是：**

- Fable5 full4（~1e8 primaries / Step05 W2 / activation 16.6% 等）
- Step05 W2 选后验证
- Activation production 直接验证
- Delayed history-aware 验证
- “轨迹 fold 已全面验证、可写进正文无 limitation”

历史 Fable5 叙述（仅供对照，**不要当本仓已复现数字**）：  
`engineering/trajectory_curve_validation_RECOVERED_20260709/`  
旧 scalar：activation 16.6% / all-TES 19.5% / **W2 60.7%**；修正后生产 1.1%、all-TES 4.4%、W2 LOO ~18%。

### 3.5 图

- `10_curve_validation/figures2/` — 应用 **通道对应** 的方式画：prompt MC 只对 prompt 曲线  
- 正确 match 图：`figures2/prompt_curve_vs_cosima_eplus.png`  
- 错误教训：不要把 e+ band 点叠到 signal / activation 曲线上冒充“验证”

---

## 4. 为什么之前“只有 e+”？

不是物理上只该有 e+，而是 **本轮战役只把 e+ 跑到高统计 + 粗 TES band 可用**：

| 物种 | 本轮统计 | 对解析曲线的用途 |
|------|----------|------------------|
| e+ | 1e6/点，band ~5e4 | **可**做 prompt 曲线 match（最佳本轮证据） |
| n | 2e5/点 | gen-rate / 粗 TES；band 仍稀 |
| γ | 5e5/点 | 同上；且大气 γ ≠ 天体 signal 曲线 |

**解析曲线有三条物理通道，验证必须分通道：**

1. **Prompt curve** ← 多粒子大气本底 Cosima（e+/n/γ/…）+ Step05 选后  
2. **Activation production curve** ← 同位素产生 / activation 战役（本轮 **未跑**）  
3. **Signal \(T_{\rm atm}\) curve** ← 天体 511 透过（不是本地 e+ 本底；本轮 **未跑**）

下一步 Codex **不要再只加 e+** 就宣称“曲线验证完”；应按通道补齐。

---

## 5. 你要完成的验证目标（acceptance）

### 最低完成（prompt 外推准确性 — 可交付）

1. 冻结并文档化：解析 \(S_{\rm prompt}(t)\) 与多点 MC 的 \(Q\) 表（已有 targeted e+；补全 n/γ 在 **同一 proxy 定义** 下的清晰表）。  
2. 图：每个通道 **只叠该通道 MC** 到对应解析曲线；写出 \(Q\) 与是否通过门槛。  
3. 明确 verdict：  
   - 旧单标量 prompt：PASS / FAIL（当前证据倾向 **FAIL ~±7% e+ band**）  
   - 相对 live PARMA：PASS（~1%）

建议门槛（与 harness 一致，可写进 FINAL_STATUS）：

- Prompt 粗 480–550：NRMSE 或 max |Q−1| 是否 ≤10%  
- 若用 W2：≤15%（需足够计数）

### 完整曲线验证（对齐 Fable5 意图 — 仍 open）

| 通道 | 需要做什么 | 现状 |
|------|------------|------|
| Prompt all-TES / W2 | Step05 选后 + 更高统计；W2 期望计数 ≥10 才宣称 | 未做 Step05；W2 在 1e6 e+ 下期望 ≪1 |
| Activation production | 多点 activation / 同位素产额 vs `delayed_production_scale` | 未跑 |
| Delayed selected rate | history-aware activity + response | 未跑 |
| Signal \(T_{\rm atm}\) | 独立信号透过验证（若要宣称 signal 曲线） | 未跑 |
| 修正模型 | 族×E×θ source–response 或 live 分种 PARMA 权重曲线，使 MC 点落在**预测曲线**上 | 仅有 live PARMA 尺度，未建成可晋升的修正 Step06 |

### 图与产品要求

- 更新 `00_manifest/FINAL_STATUS.md` claim 级别（诚实）  
- 机器可读：`05_targeted_stats/` 或新 dated 目录下的 `*_residuals.csv` / `validation_decision.json`  
- 图放 **新目录**（勿覆盖用户 reference）；`figures2` 风格：点必须是 **该曲线对应观测量的 MC 标度**

---

## 6. 关键路径速查

```text
engineering/trajectory_transport_validation_20260709/
  00_manifest/
    FINAL_STATUS.md                          # 当前 claim
    HARNESS_ENGINEERING_B_...md              # 完整验收门槛
    CODEX_HANDOFF_CURVE_VALIDATION.md        # 本文件
  01_points/                                 # 冻结点 + 解析预测
  02_sources/parma_live/                     # live PARMA 尺度
  02_sources/spectra_live/                   # 20-bin 谱
  04_prompt_smoke/                           # 中等统计
  05_targeted_stats/                         # 高统计 e+/n/γ + Q 表
  10_curve_validation/figures2/              # 通道对应图
  scripts/                                   # 可复现流水线

engineering/trajectory_curve_validation_RECOVERED_20260709/  # Fable5 叙述重建（非权威数字源）
stepwise_maintenance/step06_.../outputs_Mass_model_511_fullstat_v1/
stepwise_maintenance/step08_.../outputs_Mass_model_511_fullstat_v1/  # 累计 Z fold
```

环境依赖：

- Cosima + `geant4.sh`（与既有 runner 相同）
- PARMA：`.../expacs_parma/phase2_parma_grid_driver`，**cwd=`parma_cpp`**

---

## 7. 建议执行顺序（给 Codex）

1. **读** `FINAL_STATUS.md` + 本 handoff + harness 中 prompt/W2 门槛。  
2. **不要重跑** 已完成的 12 targeted Cosima，除非完整性失败；优先 `extract_targeted_stats.py` 复现表。  
3. **补 prompt 验证表述**：n/γ gen 与 e+ band/TES 分表；图只叠对应曲线。  
4. **若要冲击 Fable5 同级 claim**：  
   - 接 Step05 W2 选后流水线；按期望计数抬 primaries；  
   - 单独 activation production 战役；  
   - 再考虑 delayed。  
5. **若目标是“点贴曲线”**：重建 **修正预测曲线**（live 分种 PARMA 或族-response），再叠 MC——不要指望 MC 贴回已证伪的旧单标量。  
6. 结束时更新 `FINAL_STATUS`：  
   - `PROMPT_SCALAR_FAILS_MC` / `PROMPT_MATCHES_LIVE_PARMA` / `FULL_CURVE_STILL_OPEN` 等诚实状态机。

---

## 8. 禁止事项

- 宣称与 Fable5 16.6% / 19.5% / 60.7% **数值等同**（未复现 full4 + W2 + activation）。  
- 用 e+ 本底点验证 **signal \(T_{\rm atm}\)** 或 **activation production** 曲线。  
- 用低计数 n/γ band 或 W2 零事件宣称 PASS。  
- 覆盖保留的 Mass_model / geo-opt 权威产物；新 run 用新 dated 子目录。  
- 恢复已删除的 fix5 authority 输出（除非用户明确要求）。

---

## 9. 一句话任务卡（可直接贴给 Codex）

> 在 `engineering/trajectory_transport_validation_20260709/` 上继续 **解析外推曲线验证**：以 Step06 `prompt_scale` / `delayed_production_scale` / `science_atm_scale` 为被检验模型，用 REF/L1/L2/H1 多点直接输运算 \(Q=(R/R_{\rm REF})/S\)。已有 targeted Cosima（e+1e6/n2e5/γ5e5）表明 **e+ prompt 通道跟踪 live PARMA 而非旧单标量（|Q−1|~7%）**。请补齐通道对应的残差表与图，推进 Step05 W2 / activation（若要完整 claim），并保持 claim 为可审计的非 full4 级别，直到证据齐备。

---

## 10. 当前数字备忘（targeted e+ band，便于对照）

```
L1: Q_band vs analytic = 1.069, vs PARMA = 1.000
H1: Q_band vs analytic = 0.933, vs PARMA = 1.003
REF: 1.000 / 1.000
L2: Q_band vs analytic = 1.053, vs PARMA = 0.994
Claim: TARGETED_STATS_NOT_FULL4
```
