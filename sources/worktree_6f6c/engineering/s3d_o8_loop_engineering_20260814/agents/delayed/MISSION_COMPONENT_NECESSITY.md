# S3d-O8 delayed mission component necessity

## 结论

**FACT（官方 central realization）：20 天精确 family×parent-ZA 折叠不会推翻 day-15 必要性判决。** 即使把全部 prompt 置零，并把对应 delayed 行 100% 删除，MXC-only、G-Nb-S1 的“全部 inner-Nb 都消失”上界和 all-Cu 仍不能达到正式任务门

```text
S20 = 1645.387753066 counts
B20,max = (S20/10)^2 = 27073.008579396 counts.
```

四部件 `MXC + Nb inner + Mu outer + L0` 的非物理 100% 删除才在 central 算术上过门；它不是一个工程 topology。用 baseline live 得到的残余为 `26387.036791` counts；即使令 live=1，残余仍为 `26966.453439` counts，只比门低 `106.555140` counts（0.394%）。任何非零 prompt、未完全删除、host migration 或 signal 损失都会抹掉这点余量。

因此本任务对候选的判决是：

- **G-Nb-S1：KILL by official-central necessity.** 完美删除全部 inner-Nb delayed 尚余 `76007.823653` counts，是门的 `2.8075` 倍；真实 2→1 mm 减薄只能更弱。
- **MXC-only：KILL by official-central necessity.** 完美删除尚余 `61374.929525` counts，是门的 `2.2670` 倍。
- **all-Cu：KILL as a sufficient single material-class answer.** 完美删除尚余 `29528.548385` counts，是门的 `1.0907` 倍。
- **四部件删除：arithmetic necessity witness only，非候选。** 它要求四个独立热/磁/结构系统的 observed contribution 全消失且 prompt=0。

这些是 retained weighted-MC central ceiling，不是覆盖率声明。低 position Neff 仍然存在：MXC `7.77`、Nb inner `2.95`、Mu `2.93`、L0 `2.19`、all-Cu `17.74`、四部件合并 `15.68`。因此不能把各 component count 当成可确定实现的几何收益。

## 精确联接与定义

输入保持 `S3d_O8 × delayed × family` 边界，没有跨 geometry 或 family 混池：

1. 从官方 `selected_background_w2_lineage.csv` 取得 420 个 selected rows、31 个 exact `(family,parent-ZA)` keys 和各自 static day-15 `event_weight_cps`。
2. 对每个事件和每个任务节点使用

   ```text
   r_e(t) = event_weight_e(day15 constant environment)
            × activity_scale(family,parent-ZA,t)
   ```

   其中 scale 来自 `family_parent_activity_by_time.csv`。同一 family-parent 的 source volume 继承同一时间 scale；volume/position 差异已包含在 day-15 event weight 中。
3. component 的 20-day baseline-live counts 定义为

   ```text
   C_component = Σ_t quadrature_weight_s(t)
                   × accidental_live_factor_baseline(t)
                   × Σ_e∈component r_e(t).
   ```

活动表的 `2517 family-parent keys × 81 nodes = 203877` 个 S3d cells 复合键唯一；31 个 selected keys 在 81 个节点全部联接，无缺格。逐节点重建的 delayed rate 与 `mission_timeline.csv` 最大差异小于 `1e-13 cps`。

闭合量为：

```text
D20 =  88804.862651876 delayed counts
P20 =  55398.979434025 prompt counts
B20 = 144203.842085901 total counts
```

与 mission authority 完全闭合。baseline live factor 范围为 `0.97552237–0.98137520`，baseline effective live exposure 为 `1691053.762192 s`。

## 20-day component counts 与必要性门

下表的“残余”都采用对候选极端有利的条件：selected scope 100% 消失、全部 prompt 消失、signal 不变、没有 host migration。`baseline-live residual` 是 occupancy 只下降时的候选计数下界。

| scope | rows / position Neff | component D20 counts | baseline-live residual | live=1 residual | residual / B20,max | static day-15 residual cps | exact mission gate |
|---|---:|---:|---:|---:|---:|---:|---|
| baseline delayed | 420 / 24.93 | 88804.863 | 88804.863 | 90757.883 | 3.2802 | 0.05447975 | FAIL |
| MXC | 57 / 7.77 | 27429.933 | 61374.930 | 62724.284 | 2.2670 | 0.03770826 | FAIL |
| Nb inner | 24 / 2.95 | 12797.039 | 76007.824 | 77679.242 | 2.8075 | 0.04667115 | FAIL |
| Mu outer | 20 / 2.93 | 12735.445 | 76069.418 | 77742.187 | 2.8098 | 0.04671430 | FAIL |
| L0 Cu disk | 93 / 2.19 | 9455.409 | 79349.454 | 81094.390 | 2.9309 | 0.04863025 | FAIL |
| all Copper | 374 / 17.74 | 59276.314 | 29528.548 | 30177.893 | 1.0907 | 0.01808860 | FAIL |
| MXC + Nb inner | 81 / 10.63 | 40226.972 | 48577.891 | 49645.643 | 1.7943 | 0.02989965 | FAIL |
| MXC + Nb + Mu + L0 | 194 / 15.68 | 62417.826 | 26387.037 | 26966.453 | 0.9747 | 0.01628469 | PASS arithmetically only |

若保留 baseline prompt，最有利的四部件行仍为 `81786.016225` total counts，全部方案都失败。

## day-15 rate 门与正式 mission count 门不可混用

日 15 必要性 screen 使用 `B_target=0.016581812 cps`。把它乘 baseline effective live exposure 得到 `28040.735567 counts`，**这不是**正式 20-day authority。正式门必须由任务自己的 signal 计算，即 `(S20/10)^2=27073.008579 counts`；在同一 baseline effective exposure 下相当于 `0.0160095493 cps`。

mission-folded baseline-live rate-equivalent 也保持同一排序：all-Cu 删除后的残余为 `0.0174616260 cps`，仍失败；四部件残余为 `0.0156039018 cps`，才通过。故时间演化没有把 G-Nb、MXC 或 all-Cu 从 day-15 FAIL 翻成 mission PASS。

## accidental-live feedback 的严格边界

mission 使用

```text
L(t) = exp[-1e-6 × (prompt_occupancy(t) + delayed_occupancy(t))].
```

若候选只会降低 occupancy，则 `L_candidate(t) >= L_baseline(t)`，因此

```text
C_residual(using baseline live)
    <= C_residual(candidate live)
    <= C_residual(live=1).
```

所以 baseline accidental live 可用于**必要性下界**，但不能作为候选计数预测；删除高 occupancy 后恢复的 live time 会让剩余背景和 signal 都多记录，而不是进一步压低背景。G-Nb-S1 和 MXC 的下界已远高于任务门，live-factor feedback 不可能改变其 impossible verdict。若候选反而新增 occupancy，以死时间“改善”背景也不成立，因为 candidate-own `S20` 同时下降，必须重算更小的 `B20,max`。

## 适用边界与唯一工程 blocker

- 本折叠只重用官方 420-row selected lineage 与 M05 family-parent 时间模型；没有运行 transport，也没有宣称候选真实删除效率。
- activity 时间变化按 exact family-parent 处理，但非 day-15 delayed occupancy 只有 family-total-activity proxy；没有 component-specific active-occupancy lineage。因此只能给上述单调 live bound，不能给 candidate live 曲线。
- central count 是 observed weighted realization，单事件高权重与低 Neff 没有被平滑或包装成确定收益；没有构造一侧统计覆盖界。
- 四部件 arithmetic crossing 不能从现有 BOM/CAD 定义为一个保留热、磁、结构功能的简单单 topology。这个 function-constrained topology map 仍是唯一工程阻断证据；在它出现前不能启动 candidate-own focused S20/full-chain 来把算术 witness 冒充优化方案。

机器可读结果见 `mission_component_necessity.csv`；复算脚本为 `build_mission_component_necessity.py`。
