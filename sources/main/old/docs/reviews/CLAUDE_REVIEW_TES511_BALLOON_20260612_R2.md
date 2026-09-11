# Claude Review R2: TES_511_Balloon 修复后复审报告

Date: 2026-06-12 (第二轮)
Reviewer: Claude (Fable 5)
Scope: 对照 `CLAUDE_REVIEW_TES511_BALLOON_20260612.md` (R1) 与
`outputs/reports/claude_review_execution_20260612/` 执行报告, 逐项核实修复;
并对修复后立为新权威的 v3p5 fullstat_v2 链做数值复审。
Mode: 只读评审。本报告是唯一新增文件。所有关键数字均直接从盘上产物重新计算,
附录 A 给出复现命令。

---

## 0. 一句话总结

R1 的 P0 修复**执行质量高且数值全部复核通过** (主线 div8 重建 78.04 Bq、
构建器护栏实测有效、BGO 源级无 ×8、文档冻结到位)。但本轮在新基线里发现一个
**新的 P0**: v3p5 Step05 的 prompt 归一化 override 丢掉了 non-gamma 的
1/replicas 权重 —— 对 1of10 (replicas=1) 恰好无害, 换 fullstat_v2 (replicas=8)
后**所有 non-gamma prompt 率被 ×8**。刚立为权威的 fullstat headline
(`W2 本底 0.486 cps / Z20d=2.20 / 1Ms 3σ=1.77e-4`) 全部带病; 修正后约为
**0.073 cps / Z20d≈5.7 / 1Ms≈6.9e-5**。这是 ×8 家族两天内第二次发作,
两次机制同构 (多 rep 计数累加 + 单 rep 时间), 仓库至今没有版本控制。

---

## 1. R1 修复项核实 (逐项)

| R1 事项 | 状态 | 本轮核实 |
| --- | --- | --- |
| P0-1 主线 div8 重建复核 | **DONE ✓** | 重算 `runs/step02_decay_source_mainline_div8_review_20260612/`: 总活度 **78.035103 Bq**、I-128 **66.6294 Bq** (n 流 66.56/s + p/μ 小贡献, 自洽); groundstate 修复版 77.999 Bq。与 R1 预测 ~78 Bq 一致 |
| P0-1 构建器护栏 | **DONE ✓** | 两个工具 (`makedecaysourcewithplot_rpip.py`, `build_fixed_delay_source.py`) 均加了 div≠文件数即 FAIL、TT 缺失/不全即 FAIL、TT 改用 mean×N (数学上 = ΣTT, 精确)、`--gamma-div auto`、审计落盘。本轮**实测**: 1 文件 + div=8 → `tag=n has 1 files but division=8`; div=1 → 干净, 单 rep I-128 率 65.39/s 符合物理 |
| P0-2 BGO 分支 | **DONE ✓ (且推翻 R1 猜测)** | 外部修复版 BGO 源 17.2370 Bq vs 本地正确归一重读 17.1837 Bq, 差 0.3% —— **BGO 源没有 ×8** (R1 "大概率同样×8" 被数据否定, 这是好事)。44 dat = 5 流×8 + gamma×4, 账齐。下游 (Step06+/Route B/对比报告) 仍 stale, 执行报告已如实声明 |
| P0-3 文档冻结 | **DONE ✓** | README 顶部 review-hold 框 + "Legacy DEMO2 (Pre-Fix)" 分节; VALIDATION.md 标 `LEGACY_PRE_FIX_REVIEW_HOLD`; workflow/ROUTE_B 均有横幅; Project_Memory "What Not To Misquote" 含 ×8 条目与 BGO 排除条目; 1 Ms 对比 CSV 的 DEMO2 行已标 `DEMO2_legacy_pre_fix` |
| P1 git init | **未做** (执行报告自认) | `.git` 仍是空目录。两天内两起同族归一化事故后, 这是最高工程风险项 |
| P1 validator 在本仓库跑通 | **未做** | `outputs/reports/validation_new_geo_re/` 仍为空; Memory "Fast Authority Map" 仍指向该空路径 |
| P1 current/legacy 分层 | **部分** | 横幅到位, 但 README "Current Authority"/Layout 仍有 ≥9 个本仓库不存在的路径 (geometry、`review_20260531.html`、day15/csi/half-life 报告、`runs/*_equiv2602_aligned` 等) 被当现状引用 |
| P1 解析锚重算 | **未做** (自认) | 8.185 vs 6.323 的假阳性锚未重做 |
| P2 gamma 多 part 归一 | **DONE ✓** | `--gamma-div auto` + prompt 侧 gamma 时间用流总时长 |
| P2 realpos 延迟源方法迁移 | **DONE ✓** | `tests/realpos_delayed_smoke/` 已有 README/构建/运行脚本 (不再是空目录) |
| P2 光学 per-seed CSV | **部分** | combined `focal_crossings.csv` + `seed_runs_summary.json` 已入库; per-seed 原始 CSV 仍指 `/home/ubuntu/opticsim` |
| P2 "1/10" 标签 | **未做** | 各文档仍称 "1/10"; 实际 instant/buildup 粒子数比 1/21.2, **non-gamma 等效曝光比 1/80** (18.4 s vs 1472 s, 见 §2.4) |
| P2 T_atm 倾斜视线论证 | **未做** | 仍只有 "inherited" 标注 |
| P2 f10m Phase 1 | **未做** | 维持原状 (P2, 不催) |

---

## 2. 新 P0: v3p5 Step05 prompt 流 non-gamma ×8 (fullstat_v2 全链带病)

### 2.1 证据链 (全部为本次直接计算)

1. **运行设计** (`runs/step02_instant_v3p5_centerfinger_fullstat_v2/normalization.json`):
   `non_gamma_replicas=8`, `gamma_splits=12`,
   `gamma_prompt_time_s_with_farfield_area=184.22 s`; 且文件里就有
   `non_gamma_combined_norm_factor = gamma_factor/8` —— 生成层 (`code/tools/`
   `run_equiv2602_pipeline_NEW_GEO.py` L365) 明确知道 non-gamma 要 ÷replicas。

2. **盘上 TT 实测** (fullstat_v2 instant, 按 tag 汇总 .dat TT 行):
   gamma 12 文件 ΣTT=184.26 s; **每个 non-gamma tag 8 文件 ΣTT≈1472-1485 s**
   (= 8 × 184.2; eplus 1472.27, n 1473.60, muplus 1485.18)。
   1of10 对照: non-gamma 每 tag 1 文件 TT≈18.4 s, gamma 12 文件 ΣTT=18.39 s。

3. **代码机制**: 旧主线解析器 `code/tools/make_complete_day15_report_ADR.py`
   L159-163 是对的: `weight = 1.0 if tag=="gamma" else 1.0/8.0`, 再 ÷prompt_time。
   v3p5 override (`code/tools/build_v3p5_centerfinger_step05_l1_response.py`
   L222-224) 改成对**所有** prompt tag 统一 `1.0/prompt_time_s()` —— 丢了
   non-gamma 的 1/replicas。对 1of10 (replicas=1, 单 rep TT≈gamma 总时长)
   恰好正确; 对 fullstat_v2 (replicas=8) 即 ×8。

4. **数值闭环**: W2 最终 prompt 87 个事件 (eplus 80 + n 6 + muplus 1,
   gamma 0 个) × 1/184.22 = **0.47226 cps**, 与 step05 summary 的
   `side_compton_fov_pass_rate = 0.4722611742` 逐位吻合; eplus 80/184.22 =
   0.434263 与 breakdown JSON 的 `rate_hz=0.43426314871` 逐位吻合 ——
   证明下游不存在任何补偿除法。

### 2.2 修正后的预期数字 (算术确定, 以重跑为准)

按各 tag 实际 ΣTT 重算 (eplus 80/1472.273 + n 6/1473.602 + μ+ 1/1485.177):

| 量 | 现 documented (fullstat_v2) | 修正后预期 |
| --- | --- | --- |
| W2 prompt 本底 | 0.472261 cps | **0.059083 cps** |
| W2 总本底 (prompt+delayed) | 0.486136 cps | **0.072958 cps** (÷6.66) |
| prompt:eplus 占比 | 89.3% | ~74.5% (定性结论 "prompt e+ 主导" 存活) |
| Z20d @1e-4 | 2.20208 | **≈5.68** (×√6.66=×2.581; 统计 ±~4.5%) |
| 20 天 3σ 流量 | 1.36235e-4 | **≈5.3e-5 ph cm⁻² s⁻¹** |
| 1 Ms 3σ 流量 | 1.76837e-4 | **≈6.9e-5 ph cm⁻² s⁻¹** |
| broad 480-550 prompt | 0.591684 cps | 需按 tag 重跑 (109 事件的 tag 构成未落盘) |

- delayed 流 (1/11531.6 s) 与 science 流 (1/37194 × 注入率) 归一化**核实无误**;
  Step06 是纯继承 Step05 率的折叠 (修正线性传播), Step07/08 同。
  **修复 = 改一行 + 重跑 Step05→06→07→08→closure→1Ms 对比 (纯后处理, 无需新输运)。**
- 受污染的产物清单: step05/06/07/08 的 `outputs_v3p5_centerfinger_fullstat_v2*`、
  `w2_background_source_breakdown/`、
  `outputs/reports/v3p5_fullstat_performance_w2_closure_20260612/`、
  1Ms 对比 CSV 的 v3p5 行、Project_Memory "Full-stat v2 headline" 段、
  README 第 38 行引用。**1of10 数字不受此 bug 影响** (但统计空洞依旧)。

### 2.3 修复建议

1. Step05 override 恢复 per-tag 权重, 且**不要硬编码 8**: 从
   `normalization.json` 读 `non_gamma_replicas`/`gamma_splits`, 或更稳——
   像新审计那样直接按 tag 对 .dat/.sim 求 ΣTT 用 `1/ΣTT_tag`。
2. 给 Step05 加断言 (×8 家族第三次就该绝迹): 对每个 tag 校验
   `weight_tag × ΣTT_tag ≈ 1`, 不符即 FAIL —— 与 Step02 构建器护栏同构。
3. 重跑后同步改 Memory/README/closure/对比四处 headline, 并在
   "What Not To Misquote" 加 fullstat_v2 prompt ×8 条目。

### 2.4 顺带的统计学澄清 ("1/10" 标签)

non-gamma 等效曝光: fullstat 1472 s vs 1of10 18.4 s = **1/80** (不是 1/10
也不是 1/21)。由此 1of10 的 W2 prompt 期望 ≈ 0.059×18.5 ≈ **1.1 个事件**,
P(0)=33% —— 1of10 当时测到 0 个 prompt 事件是**正常涨落, 不是小概率诡异**;
R1 说的 "非物理零" 定量根据在此。建议标签按流写清:
gamma 曝光 1/10、non-gamma 曝光 1/80、粒子数 1/21.2。

### 2.5 修正后的格局判断 (供叙事预期管理)

- 修正后 v3p5 W2-only: Z ∝ R/√B = 11.81/√0.073 ≈ 43.7; 修正后主线 W2 (R1 预测
  0.027 cps): 8.98/√0.027 ≈ 54.7 —— **倾斜几何在 W2-only 口径下比主线差 ~25%**,
  主因是侧窗收的大气 e+ 瞬发 511 线本底 (0.059 cps vs 主线 ~0.005 cps)。
- 但 v3p5 还**没有用 spot 切割**: 信号是聚焦的 (37k EventList 焦斑事件),
  prompt e+ 本底在 TES 上是弥散的 —— 主线 spot_r90 把线窗本底压到 0.30×,
  对 prompt 主导的 v3p5 大概率收益更大。**把 spot_r90 等价切割移植到 v3p5
  fullstat 是当前性价比最高的分析升级**, 比换延迟源采样更先。
- `outputs/reports/compare_511_narrow_1Ms_20260612/` 里
  "TES_511_Balloon = 2.99e-5 (rank 2)" 的本质是 **delayed-only** 假设
  (反推 B=0.0139 cps = 恰好等于延迟分量; "reduced prompt-particle" 即把 prompt
  全部去掉)。修正后现实数字是 ~6.9e-5 (介于 SPI 5e-5 与 COSI-scaled 9.5e-5
  之间); 2.99e-5 只能作为 "prompt 完全被 spot/反符合压掉" 的上限愿景引用,
  该报告需要重打标签或随重跑再生。

---

## 3. 其他发现 (P1/P2)

1. **README/Memory 悬空指针未清** (P1, R1 遗留): "Current Authority" 与
   "Fast Authority Map" 合计 ≥9 处指向本仓库不存在的路径
   (`outputs/geometry/XZTES_ADR_v4c_mkflange_cm/`、`review_20260531.html`、
   `outputs/reports/day15_complete_report/` 等)。横幅缓解了误引用风险,
   但 "current" 字样 + 死链的组合仍会误导新会话。建议按
   `old_md/MIGRATION_DIRECTORY.md` 规则改成指旧仓库绝对路径并标 superseded。
2. **validator 从未在本仓库跑通** (P1): `validate_new_geo_re.py` 在,
   `outputs/reports/validation_new_geo_re/` 空。其主线检查项在本仓库多半
   会因缺文件而 FAIL —— 正好说明它需要一个 v3p5 版; 移植时把 §2.3-2 的
   prompt 权重断言放进去。
3. v3p5 fullstat_v2 / 1of10 的 decay source 目录没有 normalization 审计文件
   (构建早于护栏)。R1 已用 `RP_yield=Points/8` 旁证 div 正确, 建议用新构建器
   做一次只读 backfill 审计落盘存证 (P2)。
4. 根目录 4 月空模板 `基于立方星的康普顿望远镜在轨性能模拟.md` 仍在 (P2);
   `step02_delayed_transport_mainline_div8_review_20260612/` 是空占位目录,
   建议放个 README 说明 "主线延迟输运未重跑, 见执行报告边界声明" (P3)。
5. 审计工具一个边角: TT 解析每文件只记**最后一条** TT 行 —— 若有人把多个
   store 级联进单个 .dat (cat rep0*.dat), 计数翻倍而 TT 不翻, 且
   `tt_count==files` 护栏抓不到。建议每文件数 TT 行, >1 即 FAIL (P3)。

---

## 4. 优先级清单 (R2)

| 级别 | 事项 |
| --- | --- |
| **P0 (新)** | Step05 prompt 权重修复 (1 行, 读 replicas 勿硬编码) + per-tag `weight×ΣTT≈1` 断言 + 重跑 Step05-08/closure/1Ms 对比 (纯后处理) + 四处 headline 与 Misquote 条目同步; 在此之前冻结引用 `0.486 / 2.202 / 1.36e-4 / 1.77e-4` 及 "89.3% eplus" |
| **P0** | `git init` + 首提交。×8 家族 48 小时内发作两次, 每次都靠考古 .dat 定位; 没有版本控制是在裸奔 |
| P1 | compare_511_narrow 报告重打标签 (delayed-only 假设显式化) 或随修正重跑; spot_r90 等价切割移植到 v3p5 fullstat (修正后 prompt 主导, 收益最大) |
| P1 | README/Memory 悬空指针清理; validator v3p5 化并真实跑通; 解析锚重算 (R1 遗留) |
| P2 | "1/10"→分流标注 (gamma 1/10, non-gamma 1/80, 粒子数 1/21.2); T_atm 倾斜视线一句论证; per-seed 光学 CSV 入库; decay source 审计 backfill; 根目录模板挪走 |
| P3 | 审计工具多 TT 行防护; 空占位目录加 README |

---

## 附录 A: 关键数字复现命令

A1. 新 P0 的完整数值闭环 (TT 结构 + 逐位吻合验证):

```bash
python3 - <<'EOF'
import glob, re, json
from collections import defaultdict
d="runs/step02_instant_v3p5_centerfinger_fullstat_v2"
tt=defaultdict(float)
for fp in glob.glob(d+"/*.dat.inc1.dat"):
    tag=re.search(r"Background_([a-z]+)_",fp).group(1)
    v=None
    for line in open(fp,errors="ignore"):
        if line.startswith("TT"): v=float(line.split()[1])
    tt[tag]+=v
print({k:round(v,2) for k,v in tt.items()})          # non-gamma ~1472-1485, gamma 184.26
n=json.load(open(d+"/normalization.json"))
T=n["gamma_prompt_time_s_with_farfield_area"]        # 184.22
print("claimed eplus:", 80/T, "(= breakdown 0.434263)")
print("corrected W2 prompt:", 80/tt["eplus"]+6/tt["n"]+1/tt["muplus"])   # 0.059083
print("corrected W2 total:", 80/tt["eplus"]+6/tt["n"]+1/tt["muplus"]+0.013874919470617803)
EOF
```

A2. 代码对照: `code/tools/make_complete_day15_report_ADR.py` L159-163
(原版含 `1.0/8.0`) vs `code/tools/build_v3p5_centerfinger_step05_l1_response.py`
L222-224 (override 丢失); 生成层规则在
`code/tools/run_equiv2602_pipeline_NEW_GEO.py` L365。

A3. R1 修复核实: 主线 div8 源总活度/I-128 (78.035/66.629 Bq) —— 对
`runs/step02_decay_source_mainline_div8_review_20260612/activation_decay_day15.source`
求 ΣFlux; 审计 JSON 同目录 `normalization_audit_day15.json` (status PASS,
8 文件÷8 + gamma 4÷auto)。

A4. 护栏实测: 对单个 n rep .dat 调 `parse_rp_from_dat(files, 8.0, "auto", False)`
→ `['tag=n has 1 files but division=8']`; 改 div=1 → 无 problem,
I-128 率 65.39/s。

A5. compare_511 的 2.99e-5 反推: F=3e-4/Z(1Ms), Z=S·T/√(B·T) 代
S=0.00118117, T=1e6 → B≈0.0139 cps ≈ 恰为延迟分量 0.013875 (prompt 被整体去掉)。
