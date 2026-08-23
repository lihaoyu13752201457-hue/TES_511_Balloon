# O8 既有 broadband-gamma 的离线 line-term 去重审计

## 结论

可以在不重跑任何模拟的前提下，对既有 O8 broadband-gamma SIM 做 event-level line-term 去重。所需事件可由 Step05 catalog 的 `(source_file, local_id)` 精确回接到原始 SIM 的 `ID`/`IA INIT` 记录，再用初始能量和方向计算正的重要性权重。

但必须按实际 SIM 能量轴执行：retained O8 源卡引用的 `_2602units` DP 把已经正确的 keV 横轴又除以 1000，因此旧宽箱 511-line 凸起实际被输运在 **0.44965--0.71264 keV**，峰节点为 **0.56608 keV**，不是 449.65--712.64 keV。故离线去重只影响 sub-keV active-only 事件；对 Broad480--550 与 W2 的事件数和率修正均严格为零。

**科学 blocker：这个因子 1000 的横轴错误作用于整个旧 O8 prompt-photon module，不只作用于 511 凸起。** 因而该 legacy prompt-gamma continuum 不能被本审计提升为绝对物理 fidelity authority。本轮范围只是在用户指定复用该模块的前提下，离线移除误置的 line term；它不解决整个横轴 blocker，也不授权、不触发、不要求或建议 continuum/其他模块重跑。

本审计没有调用 Cosima、没有生成粒子、没有做 transport、没有运行 continuum，也没有修改 retained 产品。机器可读权威为：

- `data/o8_prompt_gamma_line_dedup_audit.json`

## 1. 旧表、PDF 与实际生成关系

旧表和源卡链路如下：

1. 原始 EXPACS/PARMA 宽箱表：`expacs_fullsphere_20bin_sources/raw_expacs/spectrum_gamma_binXX_..._BHNo.dat`，横轴单位 MeV。
2. 正确的 Cosima keV DP：`expacs_fullsphere_20bin_sources/cosima_spectra_dp/gamma_binXX_..._pdf.dat`，线附近横轴为 449.65、566.08、712.64 keV。
3. O8 实际引用的 DP：`expacs_fullsphere_20bin_sources/cosima_spectra_dp_2602units/gamma_binXX_..._pdf.dat`，同三点为 0.44965、0.56608、0.71264；文件首行也明确写着“archived keV values divided by 1000”。
4. 实际源卡：`engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/config/full_prompt_all8/source_cards/Background_gamma_fullsphere20.source`，第 10 行和每个 `.Spectrum File` 均指向 `_2602units`。
5. Cosima `MCSource::SetEnergy()` 对 DP 横轴执行 `ScaleX(keV)`；SIM 的 `IA INIT` 也直接打印出 0.060、0.693、25.765 keV 等初能。1000 万个初级光子中 7,639,501 个低于 1 keV，直接确认这不是文档标签误差。

原始表在旧条件 `W=118.3, Rc=11.6 GV, depth=3.84535 g cm^-2, g=0` 下可由未修改 PARMA 函数复现。以角箱 00 为例：

| E (MeV) | 原始总表 | PARMA pure continuum | 说明 |
| ---: | ---: | ---: | --- |
| 0.44965 | 0.010419978329 | 0.010419978892 | 一致 |
| 0.56608 | 0.011532694788 | 0.004580036911 | 宽箱 line bump |
| 0.71264 | 0.002036948903 | 0.002036948892 | 一致 |

用 `get511fluxCpp=0.1737829279352 ph cm^-2 s^-1` 和该能箱宽 `0.12977 MeV` 加回 line term，得到 0.011532701111，与原始总表相差 (5.48\times10^{-7})（相对值）。20 个角箱按旧线性插值积分后，宽化 line bump 为 0.176442631228 ph cm(^{-2}) s(^{-1})；去重后的 continuum 通量为 4.623218946557，而旧总 gamma 通量为 4.799661577785 ph cm(^{-2}) s(^{-1})。

没有在仓库中定位到原始 raw-to-PDF 生成脚本；`manifest.csv`、`extraction_log.csv`、两套 DP、官方 PARMA 解析函数和实际 SIM 初能共同闭合了数值生成关系。这是 provenance 缺口，但不妨碍本次 event-level 去重。

## 2. Catalog/SIM lineage 是否足够

Step05 catalog：

`engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/fullchain/step05/work/event_catalog.pkl`

保留字段为：

`stream, tag, source_file, local_id, rate_hz, tes_total_keV, bgo_total_keV, pix_start, pix_count, pix_uid, pix_layer, pix_e, pix_x, pix_y, pix_z`，另有两个总计字段。

Catalog 不保留初能、初方向或 source-bin ID；但是 `(source_file, local_id)` 能唯一回接原始 SIM。SIM 中：

- `ID <local_id> <trigger_id>` 给出事件键；
- `IA INIT` 分号拆分后的字段 16--18 是初始方向，字段 22 是初始能量；
- 初能打印精度为 0.001 keV，方向余弦为 (10^{-5})。

FarFieldAreaSource 的入射方向满足

\[
\mu_{\rm source}=-d_z,\qquad
\theta_{\rm source}=\arccos(-d_z),\qquad
i=\left\lfloor 10(1+d_z)\right\rfloor .
\]

SIM 没有逐事件显式 source name/ID，因此不是所有事件都能 bit-exact 恢复角箱。全 1000 万事件中 9,999,022 个由打印方向唯一归箱；978 个落在五位小数舍入后的角箱边界候选。line 支撑内只有 85 个边界候选，相邻箱权重差最大 0.01364、平均 0.00220。无论如何归箱，这些事件的初能都低于 0.713 keV，所以 Broad/W2 结论不受影响。

## 3. 离线权重

对旧角箱 (i)，将 old-total 表复制一份，仅把实际 SIM 能量轴上的 0.56608-keV 节点替换为官方 PARMA continuum 节点，并保持旧表相同的线性插值。推荐直接使用未归一化强度比：

\[
w_i(E_0)=\frac{J_{i,\rm cont}(E_0)}{J_{i,\rm old\ total}(E_0)}.
\]

等价的归一化 PDF 写法必须包含通量比：

\[
w_i(E_0)=\frac{F_{i,\rm cont}}{F_{i,\rm old}}
\frac{p_{i,\rm cont}(E_0)}{p_{i,\rm old}(E_0)}.
\]

只用两个各自归一化 PDF 的比值会漏掉 (F_{\rm cont}/F_{\rm old})，不能去除 line 的总归一。

取值规则：

- (0.44965<E_0<0.71264\) keV：按上式；
- 其余初能：(w=1)。

按实际旧表各角箱的节点比值，理论最小权重为 0.3971350；受 SIM 0.001-keV 打印量化影响，实际样本最小为 0.397344，严格支撑内最大为 0.997995。continuum 和 old-total 在支撑内均为正，所以比例形式没有零分母、零权或负权风险。不要用两套独立舍入表做 `1-line/total` 减法；版本或插值不一致时该写法可能产生负权。

## 4. 受影响事件数和率

| 层级 | 受影响事件 | 旧率/等效量 | 去重后 | 去除量 |
| --- | ---: | ---: | ---: | ---: |
| 10M raw gamma 初级事件 | 858,044 | 858,044 等效事件 | 490,243.344 | 367,800.656 |
| raw gamma 生成率 | -- | -- | -- | 1,995.980 cps（有限 MC） |
| Step05 gamma catalog | 317,048 | 1,720.555682 cps | 982.711177 cps | 737.844505 cps |
| Broad480--550 selected | 0 | -- | -- | **0 cps** |
| W2 selected | 0 | -- | -- | **0 cps** |

317,048 个受影响 catalog 事件全部只有 active-volume 沉积，`tes_total_keV=0`；因此它们不会进入任何 511-keV TES 窗口。

retained Broad 最终 gamma 只有 1 个事件，率为 0.005426798726 cps：

- SIM：`.../Background_gamma_fullsphere20_rep01_part12.inc1.id1.sim.gz`
- `local_id=432618`
- `E0=570.076 keV`
- `TES=494.54719 keV`

它不在线凸起支撑内，权重保持 1。retained W2 gamma 的 raw/active/final 计数均为 0；其 0.0200188-cps 95% 上限只是零计数统计上限，不是中央率。

## 5. 与 corrected mono-line 模块的重合成

定义：

- (R_{\rm rest})：除 broadband prompt gamma 和 legacy atmospheric-511 sidecar 外的所有 retained 模块；
- (R_{\gamma,\rm old})：既有 broadband prompt-gamma 率；
- \(\Delta R_{\gamma,\rm line}=\sum_e a_e(W)r_e[1-w_i(E_{0,e})]\)；
- (R_{\gamma,\rm dedup}=R_{\gamma,\rm old}-\Delta R_{\gamma,\rm line})；
- (R_{511,\rm corrected})：修正后的独立 PARMA mono-line 模块率。

其中 (a_e(W)) 同时包含能窗、active veto 和 topology/FoV 选择。模块化重合成为

\[
R_{\rm corrected}(W)=R_{\rm rest}(W)
+R_{\gamma,\rm dedup}(W)
+R_{511,\rm corrected}(W).
\]

若从旧总率直接更新：

\[
R_{\rm corrected}(W)=R_{\rm total,old}(W)
-R_{\rm legacy\ sidecar}(W)
-\Delta R_{\gamma,\rm line}(W)
+R_{511,\rm corrected}(W).
\]

对 Broad 和 W2，已实证 \(\Delta R_{\gamma,\rm line}=0\)。所以在这两个论文窗口中，实际操作就是：保留 broadband gamma 和其他所有模块的既有 selected rate，仅移除 legacy sidecar 并加入 corrected mono-line 模块。没有任何 continuum transport，也没有任何全量粒子重跑。

## 6. 必须保留的 claim boundary

这项审计证明的是“既有 broadband-gamma 中的旧 line term 可以离线去重，且 W511 修正为零”。`_2602units` 的因子 1000 横轴错误是整个旧 prompt-photon module 的预存科学 blocker；本轮不把其余 continuum 提升为新的物理 fidelity authority。该模块仅按用户指示作为 retained legacy module 复用，本轮不授权、不触发、不要求或建议 continuum/其他模块 transport。
