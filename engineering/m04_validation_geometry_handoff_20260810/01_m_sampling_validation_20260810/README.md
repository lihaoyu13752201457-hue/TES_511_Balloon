# WP1：M 抽样零 transport 离线校验

## 结论先行

本包的判定是：

`CONDITIONAL_OFFLINE_FINITE_M_VARIANCE_ESTIMATE__NOT_HANDOFF_TRANSPORT_PASS`

现有 package-44 的 source card 可逐块精确复现；七族既有 raw SIM、冻结 event catalog 和 64 个 response seeds 也已完成只读回接。以每个 sampled source block 的最终 W511 selected yield `h_j` 为率变量，中子 `M=50,000` 的 finite-M rate CV 点估计为 `2.6853%`，重复-success-pair rare-Poisson 单侧 95% 上界为 `5.9141%`。二者满足交接第 7.5(2) 项“点估计不大于 5%、95% upper 不大于 10%”的数值子门槛。七族合计在“族间独立”假设下为 `2.6244%`、上界 `5.8389%`；考虑 retained 七族共用 source seed 的完美正相关敏感性，则为 `2.8110%`、上界 `7.0559%`。

因此可以保留“在固定 BUILDUP 表、冻结 predicate 和声明的 Poisson 计数模型下，从单个既有 M50 概率样本构造去 transport 计数噪声的条件式 factorial-moment 点估计”。即使第 7.5(2) 项的数值子门槛通过，也不能写成原交接定义的 transport-backed `PASS_M_SAMPLING` 或 `PASS_M50000_CONDITIONAL_ON_FIXED_BUILDUP`：当前没有独立 source-seed / M50--M100 配对，物理 selected 计数 RSE 仍约 12.6%，其余交接门槛也未由本次零 transport 审计闭合。

## 用户覆盖与硬边界

- 交接 §7.3B 的多 source-seed / 多 M Cosima transport matrix 被用户覆盖，本包不执行。
- 交接 §8.4.6 的 detector transport 被用户覆盖，本包不执行。
- **WP1 不调用任何 transport；WP2 独立只处理 atmospheric annihilation 511-keV 单能模块。**

程序没有调用 Cosima、package-44 runner、任何 transport、编译器或下载器，也没有生成 source card。它只做冻结输入验哈希、weighted-table 内存重抽样、已有 source card 回放、已有 raw SIM 流式解析、已有 response catalog 的 64-seed 重放和离线统计。

## 构建器、seed、Triggers 与 TE

`code/tools/build_fix5_1of10_exactpos_delayed_source.py` 的实际语义是：

- 固定活度的分配键是 `(VN,ZA)`；`exc_keV` 被记录，但不在匹配键中。
- 每个 eligible RPIP 行的权重等于组活度乘 `wfile` 后在组内归一。
- `random.Random(seed)` 按活度权重有放回抽 M 次；每个 PointSource 通量相同，均为 `A/M`。
- package-44 使用 `M=50,000`、source seed `260613`、每个正活度族 `DecayRun.Triggers=1,000,000`。source 与 transport 当前恰好共用 seed `260613`，不能当作独立随机维度。
- M 是 sampled source blocks 数，不是 transport 事件数。`Triggers` 是请求的 ID 记录数；SIM `TE` 才是率归一 authority，单事件率权重为 `1/TE`，且 TE 不是气球物理曝光时间。

## 冻结输入与 source-card 回放

`config/offline_validation_config.json` 冻结 44 个输入的 size/SHA-256，包括构建器与 runner 语义、五个 O8 几何文件、七族 weighted table/manifest/source card/raw SIM、primary selected lineage、response summary、64 replicas、event catalog 和 response/selection 实现。任一哈希不符立即停止；本次 44/44 全部 `PASS`。

程序用序列化表权重重新执行 builder 等价 CDF 抽样，把七张 source card 各 50,000 个 PointSource 的 ZA 与 `(x,y,z)` 按顺序逐块比较。七族均为 0 mismatch，通量均为单一 `A/M`，几何、manifest、SIM header、SE/ID/TS/TE binding 均闭合。

| 族 | eligible 行 | M50 不同位置 | 目标逐位置质量覆盖 | 未抽 `(VN,ZA)` 活度 | primary W511 | TE (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alpha | 560 | 422 | 99.986147% | 0.008943% | 1 | 2,872,055.496907 |
| eplus | 9 | 5 | 99.999989% | 0.000011% | 0 | 465,103,453.491270 |
| gamma | 3 | 1 | 99.999990% | 0.000010% | 0 | 183,019,346.724261 |
| muminus | 6,197 | 5,794 | 99.966560% | 0.012555% | 5 | 237,581.250236 |
| muplus | 8 | 3 | 99.999952% | 0.000048% | 0 | 1,258,991,152.384783 |
| n | 58,672 | 30,951 | 65.206055% | 0.515017% | 60 | 30,484.193888 |
| p | 4,285 | 2,928 | 99.829363% | 0.053829% | 12 | 445,369.147711 |

中子的 `65.2060548794%` 是这一个 M50 realization 覆盖的目标逐位置质量；`0.5150170333%` 是没抽到的 `(VN,ZA)` 组活度。两者不是同一量，也都不是 W511 率误差上限。更重要的是，M50 本身是从目标 `p` 得到的 i.i.d. 概率样本：34.79% 未出现在该 realization 的目标行限制逐行归因，但不因其本身阻断用 `K_j/M` 估计总体 `Var_p(h)`。

## 七族 raw-SIM 全事件回接

每个既有 SIM 的 1,000,000 个 `ID` 都有且只有一个 `IA INIT`，ID 顺序无缺失。候选仅限 retained source card 中 `K_j>0` 的行；距离使用逐轴最大绝对差。source/table 坐标为六位小数、SIM INIT 为五位小数，纯打印误差上限约 `5.51e-6 cm/axis`。考虑短程 radioactive-ion 位移后，主映射还同时要求：最近距离不超过 `1e-3 cm`、与次近邻间隔至少 `1.102e-5 cm`、次近/最近距离比至少 2。

| 族 | 唯一映射 / 1M | 未映射且 selected=0 | nearest p99.999 (cm) | nearest max (cm) | INIT ZA ≠ parent ZA |
| --- | ---: | ---: | ---: | ---: | ---: |
| alpha | 1,000,000 | 0 | 0.000350 | 0.000400 | 27.7444% |
| eplus | 1,000,000 | 0 | 0.000020 | 0.000020 | 11.3003% |
| gamma | 1,000,000 | 0 | 0.000062 | 0.000062 | 0.6029% |
| muminus | 999,914 | 86 | 6.790363 | 44.327140 | 6.2626% |
| muplus | 1,000,000 | 0 | 0.000020 | 0.000020 | 30.5467% |
| n | 999,993 | 7 | 0.000320 | 1.161778 | 6.8027% |
| p | 1,000,000 | 0 | 0.000360 | 0.000410 | 24.5697% |

muminus 的 86 个和 n 的 7 个 INIT 已发生厘米级长位移，不能诚实归到某个源行；它们在全部 64 response seeds 下都不是 final W511，因此 selected indicator 确知为 0。全部 82 个“任一 response seed 曾 selected”的唯一 `(family,local_id)` 均通过主守卫回接；64 seeds 合计 4,966 个 selected occurrences 也全部可定位。强制把未映射事件配给全局最近行的 sensitivity 另存，不能冒充主映射。

`IA INIT parts[15]` 是 transport/daughter ZA，不保证等于 sampled source-parent ZA；上表量化了差异。若强制同 ZA 会系统性丢失 daughter 事件。只在同-ZA 自适应映射实际可接受时，它与坐标 parent 的一致数为 100%，冲突数为 0；主 authority 仍是已逐块复现的 source-card 坐标。

## 主率口径：每源块 selected yield h

raw transport trial share 与 `K/M` 明显不同：source-block share 对 ID-trial share 的 total variation 为 alpha `0.213132`、muminus `0.063029`、n `0.0934325`、p `0.183254`。这说明不同 radioactive source blocks 的 ID 生成强度并非常数。对中子，单纯 `K/M` 加权的 `q_j=s_j/n_j` 会预测 `0.00206166 cps`，而直接 authority `S/T` 是 `0.00196823 cps`，高 `4.7465%`。因此 `q` 层不能作为 selected-rate 的主 M 方差。

主模型改用每源块 selected yield `h_j`。对某一族，总活度为 `A`、TE 为 `T`、第 j 个聚合源行有 `K_j` 个 source blocks，`w_j=K_j/M`，final selected 计数为 `S_j`：

```text
S_j ~ Poisson(T * A * w_j * h_j)
mu_h       = S_total / (T*A)
E_p(h^2)   = sum_j w_j*S_j*(S_j-1)/(T*A*w_j)^2
mu_h^2     = S_total*(S_total-1)/(T*A)^2
Var_p(h)   = M/(M-1) * [E_p(h^2) - mu_h^2]
R          = A*mu_h = S_total/T
CV_M(rate) = sqrt(Var_p(h)/M) / mu_h
```

`S(S-1)` factorial moment显式去除 selected transport Poisson 计数噪声；exact-position row 是主分辨率。`(VN,ZA)` 聚合假设组内常 `h`，会压低空间异质性，只作为模型诊断。

primary response seed 的中子 60 个 selected 分布在 58 个精确位置行，恰有 2 对同位置重复成功：

- authority rate `S/T = 0.00196823312 cps`；
- debiased finite-M rate SD `5.28531e-5 cps`，CV `2.68531%`；
- exact repeated-pair count转成 rare-Poisson 单侧 95% mean upper，再用最大 `2*w_j/(T*A*w_j)^2` 保守分配，得到 SD upper `1.16403e-4 cps`、CV upper `5.91410%`；
- 在 64 response seeds 间，点 CV 范围 `1.26291%–2.93585%`，Poisson-pair upper 范围 `4.96809%–6.45175%`，中位数分别为 `2.68531%` 与 `5.91410%`。

七族合计以 primary seed 的 exact-row 结果合成：

- 族间独立 RSS：点 CV `2.62439%`，Poisson-pair upper `5.83892%`；
- 完美正相关 sensitivity：点 CV `2.81103%`，upper `7.05586%`；
- 固定观测 `h_hat=S/(T*A*w)` 的 Poissonized source-block bootstrap CV 为 `10.2412%`。它保留稀疏 transport outcome 噪声，只是含噪保守诊断，不替代 factorial moment。

## q 层、source-only 重抽样与 64 response seeds

按用户要求同时保留 `q_j=s_j/n_j` 的 Binomial factorial moment：中子点 CV `2.42981%`；固定 `q_hat` bootstrap CV `10.5049%`；最大 pair-coefficient 的极保守 Poisson upper `25.2502%`。由于 `n` share 不等于 `K/M`，这些只描述 selection-probability 层，不是率 authority。

source-only 在内存中使用 seeds `260613,260614,260615,260617` 扫描 M50/M100：中子 M50 的逐位置质量覆盖均值 `65.0768766%`、范围 `64.9288011%–65.2060549%`；M100 均值 `87.2865841%`、范围 `87.1894510%–87.4877833%`。这是空间支持诊断，不是后选率证据。

现有 64 response replicas 的 delayed mean 为 `0.00200834148 cps`，跨 seed SD 为 `5.7439e-5 cps`，mean SE/mean 为 `0.3575%`。它们重放同一批 transport events，只约束 response 展宽敏感性；不能把 primary 的中子计数 RSE `12.91%` 或七族加权计数 RSE `12.62%` 除以 `sqrt(64)`。

## 既存冻结 selection blocker

冻结 response 的 active-veto predicate 使用 `"ACTIVE_SHIELD" in upper`，因此把被动 `ActiveShield_S3C_BGO_Kapton_*` 也当成 active veto。实际冻结 mask 是 BGO + plastic + 被名称谓词捕获的 Kapton，不是“仅 BGO + plastic”。本包严格重放这个既有 predicate 以保持 replicas 一致，但没有修正它，也没有重跑；所以本包不能验证冻结 selected rate 的物理正确性，不能据此升级 handoff claim。

## 主要产物与复现

```bash
python3 -B engineering/m04_validation_geometry_handoff_20260810/01_m_sampling_validation_20260810/code/run_offline_m_sampling_validation.py
```

脚本需要本地已有 Python、NumPy、SciPy 和冻结 response 模块；缺失依赖即停止，不下载。主要输出：

- `data/input_hash_audit.csv`：44 个冻结输入的 hash/size 审计。
- `data/source_population_summary.csv`：七族 target/source replay 与逐位置、组级覆盖。
- `source_only/source_only_resampling.csv`：M50/M100 × 4 seeds 的纯源表诊断。
- `data/raw_sim_parse_summary.csv`：7M ID/INIT、nearest/second-nearest、ZA 语义、歧义/未映射审计。
- `data/raw_sim_source_row_clusters.csv`：`K_j`、raw `n_j`、primary `S_j` 与 nearest-all sensitivity。
- `data/response_seed_selected_lineage.csv`：64 seeds 的 selected `(family,local_id)` 到源行回接。
- `data/cluster_source_variance_by_response_seed.csv`：`h` 主率矩、`q` 诊断、pair upper 与 mapping sensitivity。
- `data/cluster_poisson_bootstrap_primary_seed.csv`：固定 `h_hat` / `q_hat` 的含噪 source-block bootstrap。
- `data/conditional_selected_rate_reweight.csv`：既有 primary selected events 的条件式 truncated/Hájek 重权。
- `data/m_sampling_offline_summary.json`：机器可读总判定、公式、64-seed 范围、停止条件与 blocker。
- `data/output_manifest.json`：本包代码、配置、文档和结果的 size/SHA-256。

## 停止条件

以下任一出现都不得升级为 handoff PASS：冻结输入哈希或 geometry/SIM/TE/lineage binding 不一致；source card 无法逐块复现；任一 selected lineage 不能唯一回接；把 daughter ZA 强制当 parent ZA；把未通过位移/间隔守卫的 INIT 强行当主映射；把 `Var_p(q)` 在 `n share != K/M` 时冒充率方差；重复-success-pair 上界超过目标；把 64 response seeds 当独立 transport；或未解决被动 Kapton 被 active-veto predicate 捕获的既存 blocker。
