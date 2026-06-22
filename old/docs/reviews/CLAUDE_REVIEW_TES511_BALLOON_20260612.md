# Claude Review: TES_511_Balloon 项目评审报告

Date: 2026-06-12
Reviewer: Claude (Fable 5)
Scope: 全仓库文档、v3p5 链 Step00-09 产物、f10m A1 光学采纳、与旧仓库
`/home/ubuntu/codex_tes_511_sim/new_geo_re` 的交叉数值验证。
Mode: 只读评审。本报告本身是唯一新增文件; 未修改任何代码/数据/配置。
所有关键数字均为本次评审直接从盘上产物重新计算得出, 附录 A 给出复现命令。

---

## 0. 一句话总结

本仓库的新链路 (v3p5 center-finger + f10m A1 光学) 做得比它继承的文档所描述的
旧主线更正确 —— 真正的问题在被当作 "current authority" 引用的旧主线延迟活化源
本身: **旧 new_geo_re DEMO2 主线的固定延迟源被夸大了 ×8.01**。修正后主线与
v3p5 将收敛到 `Z20d≈12`、20 天 3σ ≈ 2.4-2.5e-5 ph cm^-2 s^-1 的同一量级。
这对论文是好消息, 但所有对外数字在重跑确认前都应暂停引用。

---

## 1. P0 发现: 旧主线延迟活化源 ×8.01 归一化膨胀 (v3p5 是对的)

### 1.1 证据链 (全部为本次直接计算)

1. **Geant4 层面两个几何的 I-128 产率一致。** 直接统计 buildup `.dat`
   (Cosima universal isotope store) 的 53128 条目:
   - 主线 8 个中子 rep 合计 `288,363` 个 / ΣTT `4332.1 s` = **66.56 /等效秒**;
   - v3p5 fullstat_v2 8 个 rep 合计 `97,200 / 1473.7 s` = **65.96 /s**;
   - v3p5 1of10 单 rep `1,191 / 18.34 s` = **64.95 /s**。
   两套几何、三个统计量级, 物理产率全部 ≈ 66/s。两边 CsI 质量几乎相同
   (65.15 vs 62.83 kg)、侧壁同为 4 cm 厚、源卡通量逐行相同 (仅 Geometry 行不同)、
   物理列表相同 (QGSP_BIC_HP, Geant4 10.2.3)、谱文件含热中子 (E_min≈1.1e-8 keV),
   所以这个一致性正是物理预期。

2. **v3p5 固定源与 Geant4 严格吻合**: fullstat_v2 固定源 I-128 = `66.00 Bq`
   ↔ 真值 65.96/s; 三个统计量级 (12k / 1.19M / 25.2M 粒子) 总活度稳定
   (`79.58 / 86.38 / 85.64 Bq`) —— 归一化与样本量无关, 正确。

3. **主线固定源 I-128 = `533.28 Bq` = 真值的 ×8.01**, 而主线中子流恰有
   8 个独立 rep (每个 TT≈541.5 s, 非累计)。总活度同样: 624.27 Bq ≈ 8 × 78 Bq,
   修正后与 v3p5 的 86.4 Bq 在几何差异范围内一致。

4. **机制定位到代码行** (`code/tools/makedecaysourcewithplot_rpip.py`, 与旧仓库
   `stepwise_maintenance/step02_raw_background_simulation/source_snapshots/` 快照
   逐字节相同):
   - L176: `rp[(tag, vn, za, exc)] += val / div` —— 计数按粒子 tag **跨文件累加**;
   - L178-179: `tt_by_tag[tag] = tt_val` —— TT 按 tag **覆盖**, 只留最后一个文件的
     单 rep 时长;
   - L150: 非 gamma 流的 `div = float(non_gamma_div)` —— 多 rep 必须靠
     `--non-gamma-div N_reps` 抵消; gamma 流硬编码 `div=1.0`。

5. **为什么 v3p5 没踩坑**: fullstat_v2 的
   `runs/step02_decay_source_v3p5_centerfinger_fullstat_v2/activation_inventory_day15.csv`
   显示 `RP_yield = Points / 8` (例: CsI_Bottom_Quadrant_03 为 11812/8 = 1476.5)
   —— 构建时正确传了 `div=8`; 1of10 每流只有 1 个 rep, `div=1` 天然正确。
   **旧主线 equiv2602 生产构建用了 div=1** (533.28/66.56 = 8.01), 8 个 rep 的
   计数全加、时间只算一份 → ×8。

### 1.2 影响面 (算术确定, 具体数字需重跑确认)

| 量 | 现 documented (主线) | ×8 修正后预期 |
| --- | --- | --- |
| 固定源总活度 | 624.27 Bq | ~78 Bq (+gamma 小修) |
| I-128 比活度 | 8.185 Bq/kg | ~1.03 Bq/kg |
| W2 final 本底 | 0.184347 cps | ~0.027 cps (延迟分量 ÷8, prompt 不变) |
| spot_r90 本底 | 0.0551005 cps | ~0.008 cps |
| W2 Z20d | 2.735 | ~7.1 |
| spot_r90 Z20d | 4.508 | ~11.8 |
| 20 天 3σ (spot_r90) | 6.66e-5 | ~2.5e-5 ph cm^-2 s^-1 |

- 修正后主线与 v3p5 (`Z20d=12.35`, `2.43e-5`) **收敛**。v3p5 比主线
  "好 ×11.7" 的 W2 本底差异中, ×8.01 是本 bug, 真实几何/选择贡献只有 ×1.46。
- `Project_Memory.md` 的 A5 解析锚 "chain 8.185 vs analytic 6.323 Bq/kg,
  ratio 1.29 PASS" 是**假阳性**: 它验证的是被 ×8 污染的数。真实链值 ~1.03 Bq/kg
  比解析锚低 ×6 —— 解析锚本身也要重做 (CsI 4 cm 厚 vs 热中子 mfp ~2.7 cm,
  自屏蔽 ×2-2.5 + 各向异性/遮挡未计入)。
- **BGO 分支** (`../new_geo_re_2`) 用同一构建器、同样多 rep 结构, 其延迟源
  大概率同样 ×8; BGO/CsI 的**比值**结论可能存活, 绝对数不行。Pending Fix #5
  重跑时必须带正确 div。
- gamma 流硬编码 `div=1.0`, gamma 多 part 时光核产物被 ×N_parts
  (主线 ×4, v3p5 1of10 ×12) —— 绝对量小 (光核产额低), 但属同族隐患。
- 论文叙事反转: 之前 "honest downgrade" (Z 从 ~22 降到 ~4.5) 降过头了,
  修正后灵敏度回升 ×~2.6。

### 1.3 P0 建议

1. 立即把本发现写入 `Project_Memory.md` 的 "What Not To Misquote";
   冻结所有引用主线 `0.184 / 0.0551 / 4.51 / 6.66e-5` 的对外口径。
2. 用现成 `.dat` 以 `div=8` 重建主线固定源做快速复核 (预期总活度 ~78 Bq),
   再决定: 重跑主线 Step05+ 或直接以 v3p5/fullstat_v2 为新基线。
3. 给构建器加 ΣTT 正规化或 "文件数 × div 一致性" 断言 (代码改动, 本次未做)。
4. 解析锚按自屏蔽+遮挡重算后再用作重建源的独立闸门。

---

## 2. f10m A1 光学采纳: 执行质量高, 按预登记闸门走

`stepwise_maintenance/step04_opticsim/optics_aeff_authority_f10m_a1.json`
显示 2026-06-11 Phase-0 计划被忠实执行:

- R1 (legacy jitter) + R2 (整面泛光) × 3 种子 × 50k; 预登记 `[19.4, 21.4] cm²`
  闸门全过。
- **A_eff = 20.085 ± 0.221 cm²** (R2 聚合); R1/R2 互差 0.24% (<2% 闸门)。
- r50 = 7.16 mm, r90 = 10.29 mm, 与计划预测 (7.2/10.5) 吻合 ≤3%;
  R1 legacy 焦斑 (r50=0.84 mm) 仅作 legacy 诊断保留, 口径正确。
- `emergent - analytic = -0.0091`, 过 0.01 严格闸门但已贴边 (R2 泛光边缘效应),
  后续 off-axis/变体跑次注意监控。
- Bragg 半径残差 4.5e-7 mm; within-Be 0.99834; 切向最小净隙 0.668 mm。
- Step09 桥接 `37,194/37,194` 行全输运 (`PASS_EVENTLIST_BRIDGE_FULL_TRANSPORTED`);
  Step05 物理归一自洽: `20.0848 × 0.739042 × 1e-4 = 0.00148435 s^-1`;
  W2 响应 11.81 cps/(ph cm^-2 s^-1) = 注入率 × 0.7957 探测效率
  (与 f9m 链的 0.7945 一致, 合理)。

未尽事项 (authority 自标 + 本次确认):

- Phase 1 (tile 切向旋转 + checkOverlaps) 未做;
- authority json 的 per-seed `focal_crossings` 指向 `/home/ubuntu/opticsim`
  绝对路径 (跨仓库依赖, 建议把 per-seed CSV 也拷入本仓库);
- "f9m 仍是 published headline" 的声明边界写得正确。

---

## 3. v3p5 1/10 闭环链评审

**好的方面**: 每步有 status/claim-level; "18 个 W2 本底事件、closure-only、
非论文统计" 的低统计警告在 README / Project_Memory / closure 报告三处一致;
direct 与 time-fold 双口径并存且闭合 (12.359 vs 12.3501); Step06 day-15
闭合误差 ~1e-13。

需要修的:

1. **"1/10" 标签不准确**: 只对延迟输运成立 (100k vs 1M);
   instant/buildup 实际是主线的 **1/21.2** (1,190,129 vs 25,210,216)。
2. W2 prompt = 0 cps 是 1/21 统计下的零事件, 非物理零; Z20d=12.35 建立在
   18 个本底事件上 (本底 ±24% MC 误差 → Z 不确定度约 ±1.5), 引用必须带误差。
3. 延迟源仍是 RadialProfileBeam 轴对称压缩 (已自标); 对 45° 倾斜几何,
   方位角均匀化近似比主线更值得尽快换 exact-position。注意
   `tests/realpos_delayed_smoke/` 在本仓库是**空目录**, 方法 README 没迁过来。
4. `T_atm = 0.739042` 从主线轨迹继承; 倾斜指向的视线大气厚度是否需重算,
   值得一句明确论证或标注。
5. fullstat_v2 已在产出 (25.2M 粒子, 与主线预算对齐), 其延迟源归一化正确;
   后续 Step05+ 重跑时**不要**漏掉构建器 div (或先做 1.3-3 的断言修复)。

---

## 4. 仓库卫生 (P1)

1. **`.git` 是空目录, 项目没有任何版本控制** —— 一个正在跑全统计生产、
   刚发现过归一化事故的活跃仓库, 这是最高优先级工程风险。
   `git init` + 首提交成本极低 (.gitignore 已存在)。
2. **core_md 一半是旧仓库快照冒充现状**:
   - `core_md/README.md` 自称 "NEW_GEO_RE", 其 "Current Authority" 引用的
     `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/`、
     `outputs/reports/day15_complete_report/`、`runs/step02_*_equiv2602_aligned/`、
     `review_20260531.html` 在本仓库**不存在**;
   - `core_md/VALIDATION.md` 的 20 行 PASS 全是旧仓库产物复述
     (含已知 ×8 污染的 `fixed_activity_Bq=624.27`);
   - `outputs/reports/validation_new_geo_re/` 是**空目录** —— validator 从未在
     本仓库跑通过。
   建议把 core_md 拆成 "current (v3p5/f10m)" 与 "legacy reference (指向旧仓库
   绝对路径并标 superseded)" 两层 —— 这正是 `old_md/MIGRATION_DIRECTORY.md`
   原本规定的规则。
3. `core_md/Project_Memory.md` (06-12 更新) 总体质量高, 但其主线 headline 段
   现在已知携带 ×8 偏差, 需加警示框。
4. 杂项: 根目录 `基于立方星的康普顿望远镜在轨性能模拟.md` 是 4 月的空模板,
   与气球项目无关, 建议挪走; `config/run_configs/` 的 science 卡仍指旧几何路径
   (迁移文档已声明, 已知债)。

---

## 5. 优先级清单

| 级别 | 事项 |
| --- | --- |
| P0 | 主线 ×8 修正裁决: 以 div=8 重建主线源复核 (~78 Bq 预期), 决定重跑主线或改以 v3p5 为基线; 冻结旧 headline 引用; Memory 加防误引用条目 |
| P0 | BGO 分支重跑 (Pending Fix #5) 必须带正确 div, 否则比较报告继续带病 |
| P1 | `git init` + 首提交; core_md current/legacy 分层; validator 移植到本仓库并真实跑一遍 |
| P1 | 解析锚 (I-128 Bq/kg) 按自屏蔽+遮挡重算; 构建器加断言 (代码改动, 待批) |
| P2 | f10m Phase 1 (tile 旋转 + checkOverlaps); "1/10" 标签更正; exact-position 延迟源; gamma 多 part 归一化小修; T_atm 倾斜视线复核; per-seed 光学 CSV 拷入本仓库 |

---

## 附录 A: 关键数字复现命令

A1. Geant4 层 I-128 产率 (两仓库、跨 rep):

```bash
python3 - <<'EOF'
import glob
def scan(pattern):
    tots=0.0; tt=0.0
    for fp in glob.glob(pattern):
        for line in open(fp):
            if line.startswith('TT'): tt+=float(line.split()[1])
            elif line.startswith('RP'):
                p=line.split()
                if p[1]=='53128': tots+=float(p[3])
    return tots, tt
c,t=scan('/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_buildup_equiv2602_aligned/Background_n_fullsphere20_rep0*.dat.inc1.dat')
print(f'mainline: I128={c:.0f}/{t:.1f}s = {c/t:.2f}/s ; source=533.28 Bq -> x{533.28/(c/t):.2f}')
c,t=scan('/home/ubuntu/TES_511_Balloon/runs/step02_buildup_v3p5_centerfinger_fullstat_v2/Background_n_fullsphere20_rep0*.dat.inc1.dat')
print(f'v3p5 fullstat: {c/t:.2f}/s ; fixed source I128=66.00 Bq')
EOF
```

A2. 固定源活度按统计量级对比 (应不随样本量变化):

```bash
grep -oE '\.Flux [0-9.eE+-]+' runs/step02_delay_fix_v3p5_centerfinger_{lowstat10k,1of10,fullstat_v2}/activation_decay_day15_groundstate_fixed.source | awk -F'[/ ]' '{s[$1]+=$NF} END {for (k in s) print k, s[k]}'
```

A3. fullstat_v2 div=8 证据: `activation_inventory_day15.csv` 中
`RP_yield == Points/8` (例: 1476.5 = 11812/8)。

A4. 构建器机制: `code/tools/makedecaysourcewithplot_rpip.py`
L150 (div), L176 (counts +=), L178-179 (TT 覆盖), L977/L983 (R=N/TT)。

A5. 源卡一致性: `diff config/megalib_sources_fullsphere20{,_v3p5_centerfinger_tilt45}/Background_n_fullsphere20.source`
仅 Geometry 行与注释不同; 20 个 Flux 行总和相同 (0.4622 n/cm^2/s)。
两边生成速率/球面归一自洽: 5252/s ↔ R=60 cm, 1778/s ↔ R≈35 cm。
