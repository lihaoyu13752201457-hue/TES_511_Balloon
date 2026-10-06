from pathlib import Path
import json,math
O=Path(__file__).resolve().parents[1];F=O/'targeted_response/final'
ref=json.loads((O/'validation/manuscript_reference.json').read_text());source=Path(ref['path']);text=source.read_text()
read=lambda p:json.loads(p.read_text())
v=read(F/'data/paper_values_corrected_current_sample.json');r=read(F/'data/RESULTS.json');env=read(F/'data/environment_results.json')
a=v['a']['compton_trajectory_veto'];b=v['b']['compton_trajectory_veto'];am=r['models']['a']['mission_20day'];bm=r['models']['b']['mission_20day']
oa=v['a']['origin_statistics'];ob=v['b']['origin_statistics'];ratio=r['ratios'];ed={x['environment']:x for x in env['screening']}
def sci(x,d=3):
    power=math.floor(math.log10(abs(x))) if x else 0
    return f'{x/10**power:.{d-1}f}'+r'\times10^{'+str(power)+'}'
def flux(m):return f"({m['F3']*1e5:.2f}\\pm{m['F3_MC_SE_approx']*1e5:.2f})"+r'\times10^{-5}'
def counts(m):return f"{m['Ns']:.0f}/{m['Nb']:,.0f}"
items=[]
def add(title,start,end,new,oldzh,newzh):
    i=text.index(start);j=text.index(end,i);old=text[i:j].strip()
    items.append(dict(id=f'{len(items)+1:02}',title=title,line=text[:i].count('\n')+1,old_en=old,new_en=new.strip(),old_zh=oldzh.strip(),new_zh=newzh.strip()))
add('活度定义', 'For isotope $k$,', 'Early assessments suggested',r'''
Nuclide activities include direct production and feeding from radioactive parents.
For nuclide $k$, $A_k(t)=\lambda_kN_k(t)$, with
$\lambda_k=\ln2/t_{1/2,k}$. Day 15 is the reference epoch;
the inventory evolution is defined in Section~\ref{sec:mission_time_fold}.
''','对于核素 k，活度为 Pₖ[1−exp(−λₖt)]，λₖ=ln2/t₁/₂,ₖ。Pₖ 为产生率，参考状态取飞行第15天。',
'核素活度包含直接产生及放射性母核衰变的馈入。对于核素 k，Aₖ(t)=λₖNₖ(t)，其中 λₖ=ln2/t₁/₂,ₖ。第15天为参考时刻；核素存量演化见任务时间积分一节。')
add('源位置抽样与子体响应','Sampling was weighted by the','Figure~\\ref{fig:activation_source_positions}',r'''
Directly produced radionuclides were sampled according to their day-15 activities
in each production volume, with positions drawn uniformly from the matched
production coordinates. Daughter-decay responses retain the production positions
of their ancestors. Decay states requiring separate response sampling are
weighted by their activities and sampling probabilities.
''','按照各放射性核素在其产生体积内的第15天活度加权抽样，并从匹配的模拟产生坐标中等概率抽取衰变位置。',
'按照直接产生核素在各产生体积内的第15天活度抽样，并从匹配的产生坐标中等概率抽取位置。子体衰变响应保留其祖先核素的产生位置。需单独抽样响应的衰变核态按各自活度和抽样概率赋权。')
add('删除不成立的统一延迟等效曝光','For each incident-particle species with nonzero delayed-source activity, each configuration transports','\\endgroup',r'''
Decay responses are sampled separately for each incident-particle species and
configuration; the sample sizes are listed in Table~\ref{tab:background_source_model}.
The rate weight of each event is obtained from the time-dependent rate of its
decay class and the corresponding Monte Carlo sampling rate. The normalization
includes all generated histories, including those with no detector energy deposit.
''','对每种延迟源活度非零的入射粒子，两种构型各输运一百万次延迟衰变。在第15天参考条件下，等效曝光为衰变总数除以该粒子族的活度，每条事例的率权重为活度除以衰变总数，即等效曝光的倒数。任务积分根据母核活度曲线更新这些第15天权重。',
'对每一种入射粒子和构型分别抽样衰变响应，样本数见表3。每个事例的率权重由其所属衰变类别的时变物理率和相应蒙特卡罗抽样率确定。归一化包含全部生成历史，包括未在探测器中沉积能量的历史。')
add('包含子体馈入的任务演化','Because the retained nuclides have different production histories and','The total background rate before accidental-coincidence correction',r'''
The nuclide inventory is evolved separately for each incident-particle species
and production position. The production rate retains the source scaling
\begin{equation}
 P_{g,a,k}(t)=P_{g,a,k}(t_{15})\frac{\Phi_a(t)}{\Phi_a(t_{15})}
 =\Phi_a(t)Y_{g,a,k},
 \label{eq:activation_production}
\end{equation}
where $Y_{g,a,k}$ is fixed by the production catalogue. Linear interpolation
of the production rates between time nodes is combined with
\begin{equation}
 \frac{\mathrm dN_{g,a,k}}{\mathrm dt}
 =P_{g,a,k}(t)-\lambda_kN_{g,a,k}(t)
 +\sum_j b_{j\to k}\lambda_jN_{g,a,j}(t),
 \qquad A_{g,a,k}(t)=\lambda_kN_{g,a,k}(t),
 \label{eq:delayed_inventory}
\end{equation}
where $b_{j\to k}$ is the branching fraction from state $j$ to state $k$.
The initial condition is $N_{g,a,k}(0)=0$, excluding pre-activation before
the first trajectory node. The selected delayed rate is
\begin{equation}
 R_{\mathrm{delayed},g}(t)=\sum_a\sum_k A_{g,a,k}(t)\varepsilon_{g,a,k},
 \label{eq:delayed_selected}
\end{equation}
with the response coefficients evaluated at the corresponding production
positions. Each coefficient includes the probability that the decay starts
a separate coincidence group; decays within $\tau$ of a preceding decay
are included in that group's response.
''','由于保留核素的产生历史和半衰期不同，对每种入射粒子和母核分别推进延迟活化。各母核产生率随相应粒子通量缩放；相邻节点之间线性插值，再与自身指数衰变卷积。选后延迟率是各母核活度与其选后衰变响应系数的乘积之和。分别推进这些分量可保留各自半衰期和响应。初始存量为零，不包括地面预活化和首个轨迹节点前上升段积累。',
'对每种入射粒子及产生位置分别推进核素存量。产生率仍按相应粒子通量缩放，并在相邻节点间线性插值。存量方程包含直接产生、自身衰变和母核衰变馈入；bⱼ→ₖ 是核态 j 到核态 k 的分支比，活度为 λₖNₖ。初始存量取零，不计首个轨迹节点前的预活化。选后延迟率由相应产生位置的活度与响应系数求和得到。响应系数包含一次衰变开启独立符合组的概率；与前一次衰变相隔不超过 τ 的衰变计入前一组响应。')
# The insertion is anchored to the existing, unchanged time-overlay paragraph.
add('时间叠加前的同链相关沉积','The independent signal and background draws are merged','All energy deposits',r'''
Correlated decays within $\tau$ are combined before time overlay.
The independent signal and background draws are merged and ordered by arrival time.
Events separated by no more than $\tau=1\,\mu\mathrm{s}$ are linked transitively
into one coincidence candidate group $c$. Here $\tau$ is the adopted
anticoincidence window.
''','独立抽取的信号与本底按到达时间合并排序。间隔不超过 τ=1 μs 的事例通过传递关系连成一个符合候选组 c；τ 是采用的反符合时间窗。',
'时间叠加前，先合并相隔不超过 τ 的同链相关衰变。独立抽取的信号与本底按到达时间合并排序。间隔不超过 τ=1 μs 的事例通过传递关系连成一个符合候选组 c；τ 是采用的反符合时间窗。')
add('下置本底预算','The nonzero components of the final isolated-event background are delayed activation','\\begin{table}',fr'''
The nonzero components of the final isolated-event background are delayed activation
and atmospheric $\gamma$ rays (Table~\ref{{tab:reference_background_budget}}).
Delayed activation contributes ${sci(a['delayed']['rate'],4)}\cps$
({100*a['delayed']['rate']/a['total']['rate']:.2f}\%), and atmospheric $\gamma$ rays
contribute ${sci(a['gamma']['rate'],4)}\cps$
({100*a['gamma']['rate']/a['total']['rate']:.2f}\%).
The total has {a['total']['n']} selected groups and $N_{{\mathrm{{eff}}}}={a['total']['neff']:.2f}$.
''','逐事例独立筛选后的非零本底分量为延迟活化和大气γ射线。延迟活化贡献3.025×10⁻² s⁻¹（70.30%），大气γ贡献1.278×10⁻² s⁻¹（29.70%）。由于分量权重不同，记录数不能单独衡量统计支持；409条记录总计对应有效样本量39.85。',
f"逐事例独立筛选后的非零本底分量为延迟活化和大气γ射线。延迟活化贡献{a['delayed']['rate']:.4g} s⁻¹（{100*a['delayed']['rate']/a['total']['rate']:.2f}%），大气γ贡献{a['gamma']['rate']:.4g} s⁻¹（{100*a['gamma']['rate']/a['total']['rate']:.2f}%）。总计{a['total']['n']}个选中组，有效样本量为{a['total']['neff']:.2f}。")
com=oa['components']
add('下置来源部件','Grouping the parent-production sites by transport component','Figure~\\ref{fig:activation_origin_donuts}',fr'''
Grouping the parent-production sites by transport component identifies the TES
substrate-support copper panels as the largest source, at {100*com['tes_substrate_cu_panels']['share']:.2f}\%
of the final delayed rate. The TES-stack copper heat-sink ring and MXC copper
cold plate contribute {100*com['tes_cu_heat_sink']['share']:.2f}\% and {100*com['mxc_50mk_cu_plate']['share']:.2f}\%, respectively.
Aluminium cryostat and shield components, the Bi passive-shield layer,
the remaining dilution-refrigerator/cold-stage hardware, and the tungsten
collimator contribute {100*com['al_cryostat_shields']['share']:.2f}\%, {100*com['nearfield_bi_liner']['share']:.2f}\%,
{100*com['other_dr_cold_hardware']['share']:.2f}\%, and {100*com['other_detector_bay']['share']:.2f}\%, respectively.
An independent spatial projection assigns {100*oa['regions']['DR/MXC and cold plates']['share']:.2f}\%
of the delayed rate to the DR mixing chamber and staged cold region.
''','按母核产生位置所属输运部件分组，TES衬底支撑铜板贡献最大，占最终延迟率的41.03%。TES堆叠铜热沉环和MXC铜冷盘分别占17.69%和15.73%。铝低温恒温器及屏蔽、Bi被动屏蔽层、其余DR/冷级硬件、钨准直器分别占10.36%、9.06%、5.23%、0.90%。独立空间投影将17.88%的延迟率归于DR混合室和分级冷区。',
f"按母核产生位置所属输运部件分组，TES衬底支撑铜板贡献最大，占最终延迟率的{100*com['tes_substrate_cu_panels']['share']:.2f}%。TES堆叠铜热沉环和MXC铜冷盘分别占{100*com['tes_cu_heat_sink']['share']:.2f}%和{100*com['mxc_50mk_cu_plate']['share']:.2f}%。铝低温恒温器及屏蔽、Bi被动屏蔽层、其余DR/冷级硬件、钨准直器分别占{100*com['al_cryostat_shields']['share']:.2f}%、{100*com['nearfield_bi_liner']['share']:.2f}%、{100*com['other_dr_cold_hardware']['share']:.2f}%、{100*com['other_detector_bay']['share']:.2f}%。独立空间投影将{100*oa['regions']['DR/MXC and cold plates']['share']:.2f}%的延迟率归于DR混合室和分级冷区。")
add('侧置本底及两构型比较','The final Lateral-chimney isolated-event background contains','Table~\\ref{tab:optimized_component_precision}',fr'''
The final Lateral-chimney isolated-event background contains
${sci(b['non_gamma']['rate'],4)}\cps$ from the seven non-$\gamma$ prompt species,
${sci(b['gamma']['rate'],4)}\cps$ from atmospheric $\gamma$ rays, and
${sci(b['delayed']['rate'],4)}\cps$ from delayed activation.
The total rate is ${sci(b['total']['rate'],4)}\cps$,
a factor of {a['total']['rate']/b['total']['rate']:.2f} below Under-stage.
The delayed-background rate is lower by a factor of {a['delayed']['rate']/b['delayed']['rate']:.2f}.
''','侧置逐事例本底中，非γ瞬时、大气γ、延迟活化分别贡献1.811×10⁻³、5.863×10⁻³、3.725×10⁻³ s⁻¹，占15.89%、51.43%、32.68%。相对下置，延迟和大气γ分别降到12.316%和45.89%，总率1.140×10⁻² s⁻¹为下置的26.50%，低3.77倍。',
f"侧置逐事例本底中，七种非γ瞬时、大气γ和延迟活化分别贡献{b['non_gamma']['rate']:.4g}、{b['gamma']['rate']:.4g}和{b['delayed']['rate']:.4g} s⁻¹。总率为{b['total']['rate']:.4g} s⁻¹，比下置低{a['total']['rate']/b['total']['rate']:.2f}倍；延迟本底低{a['delayed']['rate']/b['delayed']['rate']:.2f}倍。")
cu=ob['materials']['Copper'];ra=oa['regions']['DR/MXC and cold plates'];rb=ob['regions']['DR/MXC and cold plates']
add('残余铜来源','Copper-derived events contribute','\\begin{figure}',fr'''
Copper-derived events contribute ${sci(cu['rate'],3)}\cps$, or
{100*cu['share']:.2f}\% of the final Lateral-chimney delayed rate.
The DR/mixing-chamber and staged-cold-plate contribution decreases from
${sci(ra['rate'],3)}\cps$ in Under-stage to ${sci(rb['rate'],3)}\cps$
in Lateral-chimney. The TES copper support panels and heat-sink ring together
account for {100*(ob['components']['tes_substrate_cu_panels']['share']+ob['components']['tes_cu_heat_sink']['share']):.2f}\%
of the residual delayed rate, and the MXC copper plate contributes
{100*ob['components']['mxc_50mk_cu_plate']['share']:.2f}\%.
Protons are the leading initiating particles ({100*ob['families']['p']['share']:.2f}\%;
Figure~\ref{{fig:activation_origin_donuts_b}}).
''','铜来源事例贡献(2.35±0.44)×10⁻³ s⁻¹，占侧置延迟本底63.04%。DR/混合室及分级冷盘贡献由下置(0.54±0.16)×10⁻²降到侧置(1.4±1.1)×10⁻⁴ s⁻¹。总延迟率由(3.02±0.37)×10⁻²降到(3.73±0.55)×10⁻³ s⁻¹。TES铜支撑板与热沉环合占51.83%，MXC铜冷盘占3.85%。质子为主要起始粒子，占55.64%。',
f"铜来源事例贡献{cu['rate']:.3g} s⁻¹，占侧置延迟本底{100*cu['share']:.2f}%。DR/混合室及分级冷盘贡献从下置{ra['rate']:.3g}降到侧置{rb['rate']:.3g} s⁻¹。TES铜支撑板与热沉环合占{100*(ob['components']['tes_substrate_cu_panels']['share']+ob['components']['tes_cu_heat_sink']['share']):.2f}%，MXC铜冷盘占{100*ob['components']['mxc_50mk_cu_plate']['share']:.2f}%。质子为主要起始粒子，占{100*ob['families']['p']['share']:.2f}%。")
qa=oa['actual_decaying_nuclides']['29062'];qb=ob['actual_decaying_nuclides']['29062'];cas=[sum(o['actual_decaying_nuclides'].get(k,{}).get('share',0) for k in ['29061','29062','29064']) for o in [oa,ob]]
add('核素组成：实际衰变核素','When grouped by parent nuclide,','\\begin{figure}',fr'''
When grouped by the decaying nuclide, $^{{62}}$Cu is the largest single
delayed-background contributor in both configurations. Its weighted rates are
${sci(qa['rate'],4)}\cps$ and ${sci(qb['rate'],4)}\cps$ in Under-stage and
Lateral-chimney, respectively, corresponding to {100*qa['share']:.2f}\% and {100*qb['share']:.2f}\%
of their final delayed rates. Together, $^{{61}}$Cu, $^{{62}}$Cu and $^{{64}}$Cu
contribute {100*cas[0]:.2f}\% and {100*cas[1]:.2f}\%, respectively.
Figure~\ref{{fig:selected_delayed_parent_nuclides}} compares the nuclide compositions.
''','按母核素分组，Cu-62在两种质量模型中都是最大的单一延迟本底贡献者；下置和侧置的加权率分别为1.589×10⁻²和1.236×10⁻³ s⁻¹，占52.53%和33.19%。Cu-61、Cu-62、Cu-64合计占73.49%和50.02%。图比较主要母核素的组成。',
f"按实际发生衰变的核素分组，Cu-62在两种构型中都是最大的单一延迟本底贡献者。下置和侧置的加权率分别为{qa['rate']:.4g}和{qb['rate']:.4g} s⁻¹，占{100*qa['share']:.2f}%和{100*qb['share']:.2f}%。Cu-61、Cu-62、Cu-64合计占{100*cas[0]:.2f}%和{100*cas[1]:.2f}%。图比较核素组成。")
add('来源图注权重','Each of the 116 records carries','Both panels use',r'Contributions are summed using their day-15 decay-rate weights.',
'汇总前，这116条记录分别赋予其母核在第15天的率权重。','各项贡献按第15天的衰变率权重求和。')
add('累计计数','At 20 d, the expected signal/background counts are','\\subsection{Mission significance',fr'''
At 20 d, the expected signal/background counts are {counts(am)} for Under-stage
and {counts(bm)} for Lateral-chimney. Atmospheric $\gamma$ rays and the remaining
background contribute {am['background_component_counts']['gamma_continuum']:,.0f}/{am['background_component_counts']['other']:,.0f}
counts in Under-stage and {bm['background_component_counts']['gamma_continuum']:,.0f}/{bm['background_component_counts']['other']:,.0f}
in Lateral-chimney. The Lateral-chimney cumulative background is
{100*ratio['Nb_lateral_over_under']:.2f}\% of the Under-stage value.
''','第20天，下置和侧置的信号/本底计数分别为2985/71677和3126/19625。大气γ及其余本底在下置分别贡献21749/49928，在侧置贡献10212/9414。侧置累计本底为下置的27.38%。',
f"第20天，下置和侧置的信号/本底计数分别为{counts(am)}和{counts(bm)}。大气γ及其余本底在下置分别贡献{am['background_component_counts']['gamma_continuum']:.0f}/{am['background_component_counts']['other']:.0f}，在侧置贡献{bm['background_component_counts']['gamma_continuum']:.0f}/{bm['background_component_counts']['other']:.0f}。侧置累计本底为下置的{100*ratio['Nb_lateral_over_under']:.2f}%。")
add('显著性和灵敏度','Figure~\\ref{fig:optimized_mission_significance} and','\\begin{figure}',fr'''
Figure~\ref{{fig:optimized_mission_significance}} and Table~\ref{{tab:primary_sensitivity}}
summarize the mission performance. At $\fref$, the 20 d counting significances
are {am['Z']:.2f} for Under-stage and {bm['Z']:.2f} for Lateral-chimney.
The corresponding $3\sigma$ minimum detectable top-of-atmosphere fluxes are
${flux(am)}$ and ${flux(bm)}\phcms$.
''','图和表汇总任务性能。在参考通量下，下置和侧置20天计数显著性分别为11.15和22.31；相应大气层顶3σ最小可探测通量为(6.46±0.52)×10⁻⁵和(3.23±0.28)×10⁻⁵ ph cm⁻² s⁻¹。',
f"图和表汇总任务性能。在参考通量下，下置和侧置20天计数显著性分别为{am['Z']:.2f}和{bm['Z']:.2f}；相应大气层顶3σ最小可探测通量为({am['F3']*1e5:.2f}±{am['F3_MC_SE_approx']*1e5:.2f})×10⁻⁵和({bm['F3']*1e5:.2f}±{bm['F3_MC_SE_approx']*1e5:.2f})×10⁻⁵ ph cm⁻² s⁻¹。")
add('摘要的数值部分','At day 15, the delayed-background rate after single-event selection','Nearby copper supports',fr'''
At day 15, the delayed-background rate after single-event selection decreases
from ${sci(a['delayed']['rate'])}$ to ${sci(b['delayed']['rate'])}\cps$,
and the total background rate decreases from ${sci(a['total']['rate'])}$
to ${sci(b['total']['rate'])}\cps$. Active anticoincidence and Compton selection
retain 98.01\% of the focused-signal events in the analysis window.
For an idealized 20-day on-source observation including time-dependent
activation and atmospheric transmission, the projected top-of-atmosphere
$3\sigma$ minimum detectable line flux is ${flux(bm)}\phcms$,
a factor of {ratio['F3_under_over_lateral']:.2f} below the reference configuration;
the uncertainty is statistical.
''','第15天逐事例筛选后的延迟本底率从3.02×10⁻²降到3.73×10⁻³ s⁻¹，总本底率从4.30×10⁻²降到1.14×10⁻² s⁻¹。主动反符合和康普顿筛选保留能窗内98.01%的聚焦信号事例。在包含时变活化和大气透过率的理想20天在源观测中，预计大气层顶3σ最小可探测线通量为(3.23±0.28)×10⁻⁵ ph cm⁻² s⁻¹，比参考构型低2.00倍；不确定度为统计不确定度。',
f"第15天逐事例筛选后的延迟本底率从{a['delayed']['rate']:.3g}降到{b['delayed']['rate']:.3g} s⁻¹，总本底率从{a['total']['rate']:.3g}降到{b['total']['rate']:.3g} s⁻¹。主动反符合和康普顿筛选保留能窗内98.01%的聚焦信号事例。在包含时变活化和大气透过率的理想20天在源观测中，预计大气层顶3σ最小可探测线通量为({bm['F3']*1e5:.2f}±{bm['F3_MC_SE_approx']*1e5:.2f})×10⁻⁵ ph cm⁻² s⁻¹，比参考构型低{ratio['F3_under_over_lateral']:.2f}倍；不确定度为统计不确定度。")
ant=ed['antarctic']
add('南极外推结果','For the Antarctic reference spectrum,','At this Antarctic latitude,',fr'''
For the Antarctic reference spectrum, the selected prompt-gamma and delayed
background rates are ${sci(ant['prompt_cps'],4)}\cps$ and
${sci(ant['delayed_cps'],4)}\cps$, respectively. Their sum is {ant['ratio']:.3f}
times the reference balloon value, giving a 20 d estimated minimum detectable
line flux of ${sci(ant['F3'],4)}\phcms$ under the same altitude and elevation
assumptions. The lower geomagnetic cutoff increases the particle background,
particularly activation.
''','南极参考谱的选后瞬时γ及延迟本底率分别为9.726×10⁻³和2.186×10⁻² s⁻¹，合计为参考气球的3.294倍。在相同高度和仰角假设下，20天最小可探测线通量估计为5.856×10⁻⁵ ph cm⁻² s⁻¹。较低地磁截断增加粒子本底，尤其是活化本底。',
f"南极参考谱的选后瞬时γ及延迟本底率分别为{ant['prompt_cps']:.4g}和{ant['delayed_cps']:.4g} s⁻¹，合计为参考气球的{ant['ratio']:.3f}倍。在相同高度和仰角假设下，20天最小可探测线通量估计为{ant['F3']:.4g} ph cm⁻² s⁻¹。较低地磁截断增加粒子本底，尤其是活化本底。")
doc=['# 原文及拟改文案：英文与中文对照\n',f'原稿：[{source.name}]({source})。下列修改**均未写入论文**。数值对应本轮最终有界结果；采用前须同时处理结果报告中明确列出的 W-176 直接响应和原源库激发态范围，不能只换数字便声称全链完整覆盖。\n',
'保持最小修改：方法段纠正实质定义，结果段替换必要数字。项目调试历史、路径、补算批次不进入正文；500 eV、1 μs、信号 spot 和实际像素顶点判定保持不变。\n']
for it in items:
    doc.extend([f"## {it['id']}. {it['title']}（原稿第{it['line']}行）",'**原文英文**','```tex',it['old_en'],'```','**原文中文**',it['old_zh'],'**拟改英文**','```tex',it['new_en'],'```','**拟改中文**',it['new_zh'],''])
doc.append('''## 16. 表3：结构和数据同步

原文表注将延迟样本的等效曝光解释为“原样本所代表的物理曝光”，表内用全部延迟记录数除以初级活度。该定义对含有限时长子体队列的样本不成立，应删除延迟块的单一 T_eq,del 列；瞬时块保持原样。

拟改表注英文：

> Delayed responses are normalized by decay class. The table lists the original recorded histories, separately sampled decay histories, retained energy-depositing groups, and their physical rates at day 15.

拟改中文：

> 延迟响应按衰变类别分别归一化。表中列出原模拟记录数、单独抽样的衰变历史数、保留的有能量沉积组数及其第15天物理率。

准确数值见 `targeted_response/final/data/table3_delayed_replacement.csv`。这张表区分“生成分母”和“有沉积组数”，不能把新增200万个历史都写成探测器触发，也不能把两种不同来源池的曝光简单相加。

## 17. 其余同步数字：保留原句结构

以下不是新增论点，只是同一结果在正文、表格、图中重复出现处的同步。原始值与最终值均列在机器清单中。

| 位置/原含义 | 原值 | 拟改值 |
|---|---:|---:|''')
pre=v['b']['pre_veto']['total'];active=v['b']['combined_active_veto']['total']
entries=[('侧置主动屏蔽前：记录数/率','7704 / 2.390',f"{pre['n']} / {pre['rate']:.4g}"),('侧置主动屏蔽后：记录数/率','140 / 0.01172',f"{active['n']} / {active['rate']:.4g}"),('侧置主动屏蔽后/之前','0.4902%',f"{100*active['rate']/pre['rate']:.4f}%"),('侧置康普顿本底保留率','97.31%',f"{100*b['total']['rate']/active['rate']:.2f}%"),('下置铜材料占比','76.60%',f"{100*oa['materials']['Copper']['share']:.2f}%"),('侧置近场铜支撑及热沉环','51.83%',f"{100*(ob['components']['tes_substrate_cu_panels']['share']+ob['components']['tes_cu_heat_sink']['share']):.2f}%"),('20天本底比','27.38%',f"{100*ratio['Nb_lateral_over_under']:.2f}%"),('20天信号比','1.047',f"{ratio['Ns_lateral_over_under']:.3f}"),('改善倍数分解','1.911 × 1.047 ≈ 2.002',f"{math.sqrt(am['Nb']/bm['Nb']):.3f} × {ratio['Ns_lateral_over_under']:.3f} ≈ {ratio['F3_under_over_lateral']:.3f}"),('质子致延迟本底生产能量10–90%范围','1.37–48.1 GeV',f"{env['primary_energy_bands'][1]['energy_p10_MeV']/1000:.3g}–{env['primary_energy_bands'][1]['energy_p90_MeV']/1000:.3g} GeV")]
for name,before,after in entries:doc.append(f'|{name}|{before}|{after}|')
doc.append('\n各锚点的保留率/符合修正也应只换数字：')
for m,name in [('a','Under-stage'),('b','Lateral-chimney')]:
    z=r['models'][m];doc.append(f"- {name}：背景修正范围 {z['rho_range'][0]:.4f}–{z['rho_range'][1]:.4f}；信号偶然符合后保留率范围 {z['eta_range'][0]:.4f}–{z['eta_range'][1]:.4f}，第15天 {z['day15']['eta_bgo']:.4f}；第15天最终信号率 {z['day15']['signal_final_rate_cps']:.4g} s⁻¹。")
doc.append('''
结果图同步范围：下置来源分解、侧置来源点与组成、核素组成、本底组成与能谱、时间曲线、累计灵敏度以及环境外推图。空间图仍可显示祖先核素产生位置；核素组成图若采用本报告第10条，应把 parent-nuclide 改为 decaying-nuclide，并按实际衰变核素重新分组，不能仅替换标题。图号以 TeX 标签为准，避免当前文件名与排版图号不一致。

## 18. 剩余模型范围的最低限度说明：需单独审核

原文没有明确交代本轮发现的 W-176 直接响应及原源库激发态排除范围。不能把核查记录整段塞入正文。如果在不补齐这两类响应的前提下采用本轮数值，方法/局限部分至少需如实交代以下意思。

拟改英文：

> The calculation uses the retained production inventory. Directly produced excited states excluded from that inventory and the direct radiation from W-176 are not included in the response estimate; feeding of the Ta-176 daughter is retained.

拟改中文：

> 计算采用保留的生产核素存量。响应估计未包含该存量排除的直接产生激发态及W-176本身的直接辐射，但保留了对其子体Ta-176的馈入。

这条是物理范围说明，不是修稿历史。若作者选择先补齐这些响应，则应改用补齐后的结果和相应说明；本轮未获超出200万次的计算授权，且不能用任意假定的W-176分支取代所缺核数据。
''')
(O/'FINAL_WORDING_ZH.md').write_text('\n\n'.join(doc)+'\n')
(F/'data/WORDING_PROPOSALS.json').write_text(json.dumps(items,indent=2,ensure_ascii=False)+'\n')
print('wrote',len(items),'bilingual original/revised passages')
