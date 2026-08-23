# M 抽样离线结论

## 判定

`CONDITIONAL_OFFLINE_FINITE_M_VARIANCE_ESTIMATE__NOT_HANDOFF_TRANSPORT_PASS`

WP1 已用现有 source cards、七族 raw SIM、冻结 event catalog 和 64 response seeds 完成零 transport 离线校验。`M=50,000` 的 source-layer 实现精确复现；在固定 BUILDUP 表、冻结 predicate 和声明的 Poisson 计数模型下，可从这个单一 M50 概率样本构造总体 finite-M rate variance 的条件式 factorial-moment 点估计。点估计 `2.68531%` 与 rare-pair 95% upper `5.91410%` 满足交接第 7.5(2) 项的 `5%/10%` 数值子门槛；状态仍不能升级为 handoff PASS，因为没有独立 source-seed / M50--M100 配对，物理计数 RSE 仍约 12.6%，64 seeds 不是独立 transport，而且冻结 active-veto predicate 仍误纳被动 Kapton。

## 主结果

1. builder 以 `(VN,ZA)` 分配活度，`exc_keV` 不在键中；按活度权重有放回抽 M，每块通量 `A/M`。七族 retained M50 source cards 各 50,000 块逐块 0 mismatch；44/44 冻结输入 hash 通过。
2. 中子 M50 抽到 30,951/58,672 个位置，覆盖逐位置目标质量 `65.2060548794%`；没抽到的 `(VN,ZA)` 活度是 `0.5150170333%`。两者不同，也不是率误差界。M50 是 `p` 的 i.i.d. 概率样本，34.79% 未出现目标行只限制逐行归因，不自动阻断总体 `Var_p(h)`。
3. 七个 SIM 共 7,000,000 个 ID，全部各有一个 IA INIT。adaptive unique mapping 为 alpha/eplus/gamma/muplus/p 各 1M，muminus 999,914，n 999,993；剩余 86+7 个都是全部 response seeds 下的 selected=0。任一 seed 曾 selected 的 82 个唯一 `(family,local_id)` 全部唯一回接。
4. INIT ZA 是 transport/daughter ZA，不保证等于 source parent；各族 mismatch 为 `0.6029%–30.5467%`。强制同 ZA 会丢 daughter 事件，parent authority 是逐块复现的 source-card 坐标。
5. raw trial share 不等于 `K/M`（中子 TV `0.0934325`），所以主率变量不是 `q=s/n`，而是每 source block selected yield `h`。用 `S_j~Poisson(T*A*K_j/M*h_j)` 的 factorial moments 去除 selected transport 计数噪声。
6. primary 中子有 60 selected、58 个成功位置、2 对重复成功。exact-row `h`-yield finite-M rate CV 点估计 `2.68531%`；rare-pair Poisson 单侧 95% upper `5.91410%`。64 response seeds 的点估计范围 `1.26291%–2.93585%`，upper 范围 `4.96809%–6.45175%`。
7. 七族合计，族间独立 RSS 的点 CV `2.62439%`、upper `5.83892%`；完美正相关 sensitivity 为 `2.81103%`、upper `7.05586%`。固定 `h_hat` source bootstrap CV `10.2412%`，因保留稀疏 transport outcome 噪声，只作含噪诊断。
8. `q` 层按 Binomial factorial moment保留：中子点 CV `2.42981%`，固定 `q_hat` bootstrap `10.5049%`，极保守 pair upper `25.2502%`；它不是 selected-rate authority。
9. primary 有 60 个中子、七族 78 个物理 selected events；计数 RSE 分别约 `12.91%` 与 `12.62%`。64 response seeds 共用同一批 transport events，不能提供 64 倍 transport statistics。

## 用户覆盖与模块边界

- 交接 §7.3B 的新 Cosima transport matrix：被用户覆盖，不执行。
- 交接 §8.4.6 的 detector transport：被用户覆盖，不执行。
- **WP1 不调用任何 transport；WP2 独立只处理 atmospheric annihilation 511-keV 单能模块。**

全过程没有运行 Cosima、package runner、任何 transport、PARMA/C++ 编译或下载。

## 冻结 selection blocker

response predicate 的 `"ACTIVE_SHIELD" in upper` 会把被动 `ActiveShield_S3C_BGO_Kapton_*` 纳入 active veto。WP1 为复现冻结 replicas 而保留该 mask，没有修改 selection 或重跑。因此本包只能说明“在冻结 predicate 下”的 M 敏感性，不能证明该 selected rate 的物理正确性。

## 允许与禁止的结论

允许：

- `PASS_SOURCE_LAYER_REPLAY`
- `CONDITIONAL_OFFLINE_FINITE_M_VARIANCE_ESTIMATE`
- `CONDITIONAL_OFFLINE_FINITE_M_VARIANCE_ESTIMATE__NOT_HANDOFF_TRANSPORT_PASS`

禁止：

- `PASS_M_SAMPLING`
- `PASS_M50000_CONDITIONAL_ON_FIXED_BUILDUP`
- “34.79% 未出现目标行使总体 M 方差不可估”
- “0.515% 组漏抽就是 W511 率误差上限”
- “64 response seeds 是 64 个独立 transport 样本”
- “`Var_p(q)` 在 raw trial share 不等于 `K/M` 时就是率方差”

即使 exact-row 点估计与 rare-pair upper 已满足第 7.5(2) 项的数值子门槛，只要独立 source-seed / 多 M 配对和其余交接门槛未闭合、冻结 selection blocker 未修复，或有人试图把本离线条件估计包装成原交接 transport-backed PASS，就必须保持当前 conditional 等级。
