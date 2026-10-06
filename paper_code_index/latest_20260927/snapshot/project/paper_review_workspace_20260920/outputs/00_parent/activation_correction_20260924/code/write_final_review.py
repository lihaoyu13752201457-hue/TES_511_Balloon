"""Readable final review and bilingual proposals; does not edit manuscript."""
from pathlib import Path
import json,math,csv
O=Path(__file__).resolve().parents[1];T=O/'targeted_response';F=T/'final'
read=lambda p:json.loads(p.read_text())
old=read(O.parent/'revision_20260921_AA_continuous/data/paper_values_500.json')
v=read(F/'data/paper_values_corrected_current_sample.json');r=read(F/'data/RESULTS.json')
previous=read(O.parent/'revision_20260921_AA_continuous/data/RESULTS.json')
u=read(T/'uncertainty.json');env=read(F/'data/environment_results.json')
labels={'a':'冷级下置（Under-stage）','b':'侧置（Lateral-chimney）'}
final=lambda x,m:x[m]['compton_trajectory_veto']
af=final(v,'a');bf=final(v,'b');am=r['models']['a']['mission_20day'];bm=r['models']['b']['mission_20day']
f=lambda x:f'{x:.6g}'
origin=lambda m,key:v[m]['origin_statistics'][key]
report=['# 活化链核查与定向补算：最终有界结果\n',
'''本报告替代本目录较早的“现有样本修正”报告。已完成用户批准的定向响应补算、两构型重筛选、三路泊松时间叠加、20 天积分及原有环境谱重加权；没有修改论文、原模拟数据或安装中的物理库。

**结论：原计算确实含子体输运，问题在子体记录的归一化、物理时间演化及短时间相关衰变处理。修正后，两构型的本底绝对值改变，侧置构型约两倍的灵敏度优势仍然存在。以下是保留源库与明确核数据假设下的结果，不是对全部活化贡献已完整验证的声明。**

## 1. 已确认的问题与实际处理

| 项目 | 原实现/证据 | 本次处理 |
|---|---|---|
| 子体是否模拟 | 103 个原任务共 1500 万条延迟记录；下置 700 万条中有 1,244,218 条排队子体记录，侧置 800 万条中有 1,156,828 条 | 确认“完全漏掉子体”不成立 |
| 统一归一化 | 全部记录数含子体，源活度却仅指独立注入的初始核素；二者直接相除不能代表所有核态的抽样曝光 | 由各原任务实际模拟时长及有限时长核链计算核态抽样数，再按实际衰变核态的物理率赋权 |
| 时间演化 | 子体沿用最初生产核素的积累曲线；每个短模拟任务开始时的子体队列也不等于飞行第 15 天存量 | 求解含直接生产与母核馈入的生成—衰变耦合方程，仍使用原来的 81 个任务节点 |
| 相关衰变 | 原输出拆分的近时刻同链记录不能当作独立的物理泊松源重复处理 | 同链 1 μs 内相关沉积先合并；在实际像素上求和能量，再施加响应和筛选 |
| Er-158 | 原核库将相关分支作为不允许的 β⁺ 衰变，原生测试出现无有效产物并终止 | 本输出内采用经核对的官方 EC 分支及匹配 Ho-158 能级；32768 次核衰变测试有效，未修改原安装 |
| W-176 | 旧库同样终止；评估资料又没有给出完整归一化 EC 馈入 | 按已知短寿命能级恢复 W-176→Ta-176 的存量馈入；未编造 W-176 直接辐射的分支。该直接响应仍未计入 |
| 稀疏 Ho-156 | 仅重加权旧样本时，侧置一个记录贡献 8.2165×10⁻⁴ s⁻¹ | 用相同源位置分布的独立响应替代；16 个选中记录合计 2.5737×10⁻⁵ s⁻¹，避免把旧单记录高权重解释为稳定的钨结构贡献 |

W-176 的已评估 EC 能级最高约 195.1 keV，已列出的跃迁不能单独解释 511 keV 能窗事例；但馈入强度未归一化，且低能沉积也可能影响反符合。因此没有把“未得到直接选中响应”写成“严格没有影响”。评估资料见 [NNDC W-176 EC 数据](https://www.nndc.bnl.gov/nudat3/getdecaydataset.jsp?dsid=176w%20ec%20decay&nucleus=176Ta)，本地原文保存在 `data/nuclear_references/W176_EC_ENSDF.html`。

## 2. 主要结果前后对比

原值取当前论文对应的 AA/侧置结果；“修正后”包含此次定向响应。日 15 率为逐事例筛选，20 天计数已包含时间叠加；两种口径不能直接互换。

| 量 | 下置原值 | 下置修正后 | 侧置原值 | 侧置修正后 |
|---|---:|---:|---:|---:|''']
for name,access in [('日15延迟本底 / s⁻¹',lambda d,m:final(d,m)['delayed']['rate']),('日15总本底 / s⁻¹',lambda d,m:final(d,m)['total']['rate']),('日15延迟本底统计标准误 / s⁻¹',lambda d,m:final(d,m)['delayed']['sigma']),('最终延迟记录/组数',lambda d,m:final(d,m)['delayed']['n']),('总本底有效样本量',lambda d,m:final(d,m)['total']['neff'])]:
    report.append('|'+name+'|'+'|'.join(f(access(d,m)) for m in ['a','b'] for d in [old,v])+'|')
for name,key in [('20天信号计数','Ns'),('20天本底计数','Nb'),('20天计数显著性','Z'),('3σ通量阈值 / ph cm⁻² s⁻¹','F3'),('该阈值的近似MC统计标准误','F3_MC_SE_approx'),('参考通量下3σ时间 / d','T3_days'),('参考通量下5σ时间 / d','T5_days')]:
    report.append('|'+name+'|'+'|'.join(f(d['models'][m]['mission_20day'][key]) for m in ['a','b'] for d in [previous,r])+'|')
report.append(f'''
日15延迟本底降低倍数：{final(old,'a')['delayed']['rate']/final(old,'b')['delayed']['rate']:.3f} → **{af['delayed']['rate']/bf['delayed']['rate']:.3f}**；日15总本底降低倍数：{final(old,'a')['total']['rate']/final(old,'b')['total']['rate']:.3f} → **{af['total']['rate']/bf['total']['rate']:.3f}**。

20 天通量阈值改善：{previous['ratios']['F3_under_over_lateral']:.3f} → **{r['ratios']['F3_under_over_lateral']:.3f}**。

按论文显示精度：下置 **({am['F3']*1e5:.2f} ± {am['F3_MC_SE_approx']*1e5:.2f})×10⁻⁵**，侧置 **({bm['F3']*1e5:.2f} ± {bm['F3_MC_SE_approx']*1e5:.2f})×10⁻⁵ ph cm⁻² s⁻¹**。±仍为既有定义的近似 MC 统计标准误，不含下文源库/核数据库的缺项、不代表实测系统误差，也不包含所有零计数上限。

直接筛选的信号记录及 98.01% 保留率不变；20 天信号数的微小变化来自重算后的偶然符合。中间仅用旧响应重加权得到的 3.43×10⁻⁵ 不再是本轮交付值。

## 3. 来源结论是否改变

| 指标 | 下置修正后 | 侧置修正后 |
|---|---:|---:|''')
for name,key in [('铜材料占延迟本底比例','Copper')]:report.append(f"|{name}|{100*origin('a','materials')[key]['share']:.2f}%|{100*origin('b','materials')[key]['share']:.2f}%|")
for name,key in [('TES铜支撑板','tes_substrate_cu_panels'),('TES铜热沉环','tes_cu_heat_sink'),('混合室铜冷盘','mxc_50mk_cu_plate')]:report.append(f"|{name}占延迟本底|{100*origin('a','components')[key]['share']:.2f}%|{100*origin('b','components')[key]['share']:.2f}%|")
report.append(f"|实际衰变 Cu-62 占延迟本底|{100*origin('a','actual_decaying_nuclides')['29062']['share']:.2f}%|{100*origin('b','actual_decaying_nuclides')['29062']['share']:.2f}%|")
report.append(f"\n侧置近场铜支撑板与热沉环合计 **{100*sum(origin('b','components')[k]['share'] for k in ['tes_substrate_cu_panels','tes_cu_heat_sink']):.2f}%**。铜支撑仍值得优化。源的生产位置与实际发生辐射的核素是两个不同标签：空间来源仍追溯原生产位置，核素组成应明确采用哪一种标签。完整分类及其统计误差在最终数值 JSON 中。")
report.append('''
## 4. 新样本、零计数及剩余边界

生产响应 1,998,000 次：下置 1,580,000，侧置 418,000；另有 2,000 次验证输运，合计恰为用户批准的 2,000,000 次上限。没有新做大气粒子活化生产。60 个独立任务按构型、粒子族和来源层分别保留；相同来源池的两批响应按合计样本数归一化，没有重复叠加两份完整物理率。

| 新响应统计 | 下置 | 侧置 |
|---|---:|---:|''')
for name,key in [('新增选中响应数','selected'),('新增选中率 / s⁻¹','targeted_rate_cps'),('新增选中率标准误 / s⁻¹','targeted_statistical_SE_cps'),('完全零选中分层的合计95%上限 / s⁻¹','zero_strata_joint95_additional_rate_bound_cps')]:report.append('|'+name+'|'+'|'.join(f(u['models'][m][key]) for m in ['a','b'])+'|')
report.append('''
上限只针对此次补算中**完全零选中**的分层。它使用全部八个预先定义分层作多重比较校正；抽样权重上限由 81 节点最大活度得到。每个来源池的抽样分布固定，零成功概率的界限允许分批追加，计算依据写在 `targeted_response/uncertainty.json`。这不是整个延迟本底的95%区间，也不覆盖旧瞬时非γ零计数。

新增非零贡献的标准误低于原总本底统计误差的20%。但零计数上限并未在所有比较口径下达到“原误差20%”的精度目标：下置和侧置上限分别约为修正后延迟本底标准误的26%和63%。因此本轮按已批准上限停止，不能写成所有小分量均已高精度收敛。

**两个尚不能消去的物理范围限制：**

1. W-176 的直接 EC 辐射未有可靠的完整归一化方案。本次恢复其已知下游 Ta-176 馈入并补算响应，但没有声称已补齐它本身的全部沉积及偶然符合影响。其他未逐一审计的核库分支也仍是系统模型假设。
2. 原生产源库明确排除了少量直接产生的激发态。正活度清单为下置 Na-24m、Sr-87m 合计 0.09414 Bq，侧置 Na-22m、Na-24m 合计 0.04679 Bq。这些是源端活度，不能直接加到 511 keV 本底；本次定向响应从原保留源点出发，未包含这些被排除的初始源及其后续馈入。另有原清单未定半衰期的 Ti-50/B-10 能级，安装核表可识别为约纳秒级，不能未经检查就当作新的长寿命活化本底。

因此上述表格是**明确范围内完成的修正结果**；它支持既有构型比较结论，但目前不宜写“全部活化核态已完整覆盖”。论文是否采用这些条件性数值，应连同这些边界一起审核，不能只换数字并继续保留完整覆盖的暗示。

## 5. 现有跨环境外推的同步结果

保持原有谱重加权近似；没有新增轨道、南极输运。新选中来源所需的三个生产能量键已回到原记录核对，未给未知能量随意赋值。

| 环境 | 原本底比 | 新本底比 | 原3σ通量 | 新3σ通量 |
|---|---:|---:|---:|---:|''')
for e in env['screening']:report.append(f"|{e['environment']}|{e['old_ratio']:.5g}|{e['ratio']:.5g}|{e['old_F3']:.6g}|{e['F3']:.6g}|")
report.append('''
本底比为瞬时γ与延迟分量的合并比，非γ瞬时项仍沿用原合并缩放近似。两种气球情景维持相同大气透过率；空间情景去掉气球大气损失。这里没有加入新的任务可见性、SAA 历史或核库系统误差。

## 6. 已核验及交付入口

- 原论文 TeX 校验值与核查前完全相同；原数据只读。
- 原瞬时本底的响应及全部81节点权重未变；新补算中无探测器沉积的历史计入抽样分母，但不进入探测器时间叠加。
- 60 个新任务的种子、几何入口、输入数、每输入一个初级记录、源位置及禁止重复追加远时子体均通过；实际像素/BGO能量与原生记录的独立比对通过。
- 短链的解析解、任务核链计算与原程序的有限时长队列计数交叉检查通过；这验证实现对应关系，不构成全部核数据的独立实验证明。
- 五个锚点/构型的信号、瞬时、延迟三路泊松时间叠加完成。500 eV、BGO 50 keV、1 μs、实际像素顶点/中心和连续圆锥判定保持原约定，不引入单信号探针。

文件入口：

1. `FINAL_WORDING_ZH.md`：原文索引、英文原文、忠实中文及拟改中英文。
2. `targeted_response/final/data/NUMERIC_COMPARISON_TWO_MODELS.csv`：全部原值/新值。
3. `targeted_response/final/data/RESULTS.json`：最终时间积分与统计误差。
4. `targeted_response/final/data/paper_values_corrected_current_sample.json`：最终筛选表及全部来源分类；文件名沿用接口，内容已是补算后的结果。
5. `targeted_response/final/data/table3_delayed_replacement.csv`：延迟样本表建议数据，取消不成立的单一等效曝光列。
6. `targeted_response/final/validation/final_input_and_response_audit.json`：最终核验。
7. `targeted_response/uncertainty.json`、`W176_limitations.json`、`final/data/positive_source_holdouts.json`：误差及范围限制。

数据与代码出处：原源库两份 activation/manifest.json；`data/runtime_jobs.json` 所列103份原源/回执；原始核素与时刻对应；原 AA/侧置像素响应；NUBASE2020；核库原生导出与官方 Er-158/Ho-158 对照文件；新增两批 plan/receipt/compact；全部最终锚点与来源清单。精确路径、种子和哈希保存在这些机器记录中，未扫描整盘或混用旧单位错误源包。
''')
(O/'FINAL_RESULTS_REVIEW_ZH.md').write_text('\n'.join(report))
print('wrote FINAL_RESULTS_REVIEW_ZH.md')
