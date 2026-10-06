from pathlib import Path
import json,csv,hashlib
O=Path(__file__).resolve().parents[1];R=json.loads((O/'data/RESULTS.json').read_text());M=O.parent/'revision_20260921_pro04_09/paper_clean.tex'
def loss(f):return 1-f['value']
def loss_ci(f):return [1-f['ci95_wilson'][1],1-f['ci95_wilson'][0]]
def pct(x):return f'{100*x:.2f}%'
def loss_text(f):
 ci=loss_ci(f);return f"{f['denominator']-f['numerator']}/{f['denominator']} = {pct(loss(f))}（95% 区间 {pct(ci[0])}–{pct(ci[1])}）"
def table(headers,rows):return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+''.join('| '+' | '.join(map(str,row))+' |\n' for row in rows)
a=R['models']['a'];b=R['models']['b'];models=[a,b]
summary='重算完成；论文、PDF、图件与最新稿指针未改。信号现在作为实际泊松流进入共同时间轴，使用输运记录中的原始沉积参与叠加，再执行响应和筛选。没有调用旧信号替代估计，也没有新开粒子输运。\n\n'
lines=['# 实际三路泊松叠加：结果与最小修改建议\n\n',summary,'## 1. 直接计数结果\n\n','下表汇总第 0、5、10、15、20 天的五次重放，每个时刻各 200,000 s。它是五次蒙特卡洛时间重放的计数汇总，不是一次实际观测，也不等同于 20 天任务积分计数。主动 BGO 损失的分母是叠加后仍在分析能窗内的信号事例；全链保留率的分母则是同一时间轴中叠加前通过全部筛选的信号事例。\n\n']
lines.append(table(['量','Under-stage','Lateral-chimney'],[
 ['输入信号实例数',a['pooled_counts']['signal_events'],b['pooled_counts']['signal_events']],
 ['BGO 主动屏蔽损失',loss_text(a['pooled_active_BGO_retention']),loss_text(b['pooled_active_BGO_retention'])],
 ['叠加后全链保留率',pct(a['pooled_retention_bgo']['value']),pct(b['pooled_retention_bgo']['value'])],
 ['全链保留计数',f"{a['pooled_retention_bgo']['numerator']}/{a['pooled_retention_bgo']['denominator']}",f"{b['pooled_retention_bgo']['numerator']}/{b['pooled_retention_bgo']['denominator']}"],
 ['额外能窗损失',a['pooled_counts']['window_loss'],b['pooled_counts']['window_loss']],
 ['通过 BGO 后的额外康普顿损失',a['pooled_counts']['compton_loss_after_bgo'],b['pooled_counts']['compton_loss_after_bgo']],
 ['由原未选中变成选中的信号',a['pooled_counts']['gain_from_isolated_unselected'],b['pooled_counts']['gain_from_isolated_unselected']]]))
lines.append('\n这里的“额外”均相对于同一个已完成孤立响应的信号事例。零次观察损失只说明本次样本没有出现，不能据此给出严格的零物理损失。本次全部节点的信号开/关净计数均与上述保留计数一致，未观察到叠加使原未选中信号进入选区的情况。\n\n')
lines.append('## 2. 第 15 天与旧稿对照\n\n')
lines.append(table(['量','Under-stage','Lateral-chimney'],[
 ['旧稿信号存活率',f"{a['old_manuscript']['eta_day15']:.6f}",f"{b['old_manuscript']['eta_day15']:.6f}"],
 ['新三路叠加、仅 BGO 的全链保留率',f"{a['day15']['eta_bgo']:.6f}",f"{b['day15']['eta_bgo']:.6f}"],
 ['新三路叠加、保留旧双通道对照',f"{a['day15']['eta_dual']:.6f}",f"{b['day15']['eta_dual']:.6f}"],
 ['新第 15 天 BGO 损失',loss_text(a['day15']['BGO_retention']),loss_text(b['day15']['BGO_retention'])],
 ['新第 15 天信号率 / s⁻¹',f"{a['day15']['signal_final_rate_cps']:.6g}",f"{b['day15']['signal_final_rate_cps']:.6g}"]]))
lines.append('\n以上六位小数仅用于机器核对；建议正文按统计量级报告约 1 位小数的百分比。旧值来自两百万次本底替代抽样，新值来自实际物理信号率下的有限信号实例，因此不能把小数末位变化解释为显著物理差异。\n\n')
lines.append('## 3. 数值联动\n\n使用原有 81 节点、0.25 天步长和梯形积分，只替换新重放得到的修正系数。下列 BGO 口径积分同时包含去掉旧塑料否决的变化和新的本底时间抽样；不能全部归因于删除旧信号估计方法。\n\n')
lines.append(table(['20 天量','Under-stage','Lateral-chimney'],[
 ['信号计数',f"{a['mission_20day']['Ns']:.1f}",f"{b['mission_20day']['Ns']:.1f}"],
 ['本底计数',f"{a['mission_20day']['Nb']:.1f}",f"{b['mission_20day']['Nb']:.1f}"],
 ['计数显著度',f"{a['mission_20day']['Z']:.3f}",f"{b['mission_20day']['Z']:.3f}"],
 ['3σ 通量 / ph cm⁻² s⁻¹',f"{a['mission_20day']['F3']:.4g}",f"{b['mission_20day']['F3']:.4g}"],
 ['其近似蒙特卡洛标准误差',f"{a['mission_20day']['F3_MC_SE_approx']:.2g}",f"{b['mission_20day']['F3_MC_SE_approx']:.2g}"],
 ['3σ / 5σ 达到时间 / d',f"{a['mission_20day']['T3_days']:.3f} / {a['mission_20day']['T5_days']:.3f}",f"{b['mission_20day']['T3_days']:.3f} / {b['mission_20day']['T5_days']:.3f}"]]))
lines.append('\n作为隔离算法变化的对照，保留旧双通道和旧稿本底积分，仅替换直接信号叠加保留率时：\n\n')
lines.append(table(['量','Under-stage','Lateral-chimney'],[
 ['20 天信号数',f"{a['algorithm_change_only_control']['Ns']:.1f}",f"{b['algorithm_change_only_control']['Ns']:.1f}"],
 ['3σ 通量 / ph cm⁻² s⁻¹',f"{a['algorithm_change_only_control']['F3']:.4g}",f"{b['algorithm_change_only_control']['F3']:.4g}"]]))
lines.append('\n## 4. 精度与未解决的历史口径\n\n- 损失率区间采用 Wilson 95% 区间；五个时刻各自的分子、分母在 ANCHORS.csv。零损失时仍有非零区间上限。\n- 信号数和通量误差包含光学/探测器模板统计及保留率统计；对于零损失节点，用 Jeffreys Beta 方差避免给出虚假的零标准误差。中心值仍是实际计数比。该近似误差不包含环境、材料与几何系统误差。\n- 本底有限输运误差先把每个原始记录在 81 节点的权重积分，再对其贡献平方求和，保留跨时间相关性。\n- 新重放中每个时刻仅数百个输入信号。不同节点保留率的散布主要受有限计数影响，不能把零损失节点读成该时刻物理上没有偶然符合。\n- 旧稿把双通道结果称作 BGO 结果。单独去掉塑料否决后，Under-stage 的直接分析能窗内主动筛选记录从 444 变为 449，最终康普顿记录从 400 变为 405，直接最终率从 0.05629456 变为 0.05733236 s⁻¹；Lateral-chimney 的直接最终率不变。新增 5 条均为延迟本底。上述差异与是否使用旧信号估计方法是两件事。\n- **“仅 BGO”仍是既有输运目录上的离线判据。Under-stage 的保留几何仍包含塑料材料，原目录的时间占用率也未重新输运为完全无塑料的硬件。这个历史差异尚未解决；本轮没有擅自扩大为几何输运重做。**\n\n')
lines.append('## 5. 最小修改范围\n\n1. PROPOSED_METHOD_EDITS.json 给出 9 处唯一 old/new 字符串：只处理共同时间轴的流、信号归一化、旧判据、保留率分母、误差说明及结果描述。没有应用到 TeX。\n2. 用 PROPOSED_WORDING_ZH.md 中的新计数段替换旧保留率段；保留 Figure 5 的三路泊松示意，不再新增信号探针或信号损失分支。\n3. 数字必须联动到第 15 天信号率、20 天计数、显著度和通量表，以及对应 Figure 14/15 和重复引用这些数字的摘要/结论。Figure 14 的 Under-stage 时间抽样时长需由 20,000 s 同步为 200,000 s。只是数据同步，不重写相邻论述。\n4. 若采用本包仅 BGO 的完整数值口径，Under-stage 的直接切流表、背景预算及来源百分比还须同步新增 5 条延迟本底；这些来源细分没有在本轮重新编造。若暂时只讨论替换旧信号估计方法，应使用单列的旧双通道对照，不能混用两列数据。\n5. 与此次重算无关的章节、术语、结构图和字体不改。\n\n')
lines.append('## 6. 可追溯入口\n\n输入文件及 SHA-256 见 SOURCE_MANIFEST.json；关键入口是 Fork02 的 corrected_optics_signal_20260920/data/signal_a_catalog.npz、signal_b_catalog.npz，原项目 70_m05_sg3_sh3_prompt_statistics_integration_20260828 的 combined_event_catalog.npz，以及 meeting_revision_20260916/data 的 500 eV 响应和逐类别时间系数。\n\n逐信号记录见 data/a、data/b 下的 anchor_NNN_signal_events.csv；物理到达计数、时长、种子和总率见对应 anchor_NNN.json。算法及数值测试见 validation/；论文、PDF 和最新稿指针的 SHA-256 在运算前后完全一致。\n')
(O/'REPORT_ZH.md').write_text(''.join(lines))
method_en='''The focused signal, prompt atmospheric background, and delayed activation are assigned independent Poisson arrival times according to their physical rates and merged onto a common time axis. Consecutive events separated by no more than 1 μs are linked transitively into a group, and their deposits are combined before the detector response, active anticoincidence, and Compton selections are applied. Signal retention is determined by comparing the same signal events before and after superposition, with losses due to active anticoincidence counted separately.'''
method_zh='''根据各自的物理率，为聚焦信号、瞬发大气本底和延迟活化本底生成独立的泊松到达时间，并合并到同一时间轴。相邻间隔不超过 1 μs 的事例连续归入同一组，先合并其能量沉积，再施加探测器响应、主动反符合和康普顿筛选。比较同一批信号事例在叠加前后的筛选结果，得到信号保留率，并单独统计主动反符合造成的损失。'''
pa=a['pooled_active_BGO_retention'];pb=b['pooled_active_BGO_retention']
result_en=f"Across the five reference times, the BGO veto rejects {pa['denominator']-pa['numerator']} of {pa['denominator']} overlaid signal events in the analysis energy window for Under-stage and {pb['denominator']-pb['numerator']} of {pb['denominator']} for Lateral-chimney, corresponding to losses of {100*loss(pa):.2f}% and {100*loss(pb):.2f}%, respectively. The corresponding 95% binomial confidence intervals are {100*loss_ci(pa)[0]:.2f}–{100*loss_ci(pa)[1]:.2f}% and {100*loss_ci(pb)[0]:.2f}–{100*loss_ci(pb)[1]:.2f}%. The signal-retention fractions at day 15 are {a['day15']['eta_bgo']:.3f} and {b['day15']['eta_bgo']:.3f}. The factors at the five reference times are interpolated to the 81 mission nodes and combined with the same atmospheric transmission and component responses."
result_zh=f"汇总五个参考时刻，Under-stage 在叠加后落入分析能窗的 {pa['denominator']} 个信号事例中有 {pa['denominator']-pa['numerator']} 个被 BGO 否决；Lateral-chimney 的相应计数为 {pb['denominator']} 个中的 {pb['denominator']-pb['numerator']} 个，损失率分别为 {pct(loss(pa))} 和 {pct(loss(pb))}，95% 区间分别为 {pct(loss_ci(pa)[0])}–{pct(loss_ci(pa)[1])} 和 {pct(loss_ci(pb)[0])}–{pct(loss_ci(pb)[1])}。第 15 天的信号保留率分别为 {a['day15']['eta_bgo']:.3f} 和 {b['day15']['eta_bgo']:.3f}。五个参考时刻的系数插值到 81 个任务节点，并与相同的大气透过率和各本底分量响应结合。"
wording=f'''# 建议表述（未写入论文）

下面是便于审阅的连贯表述；实际落稿按 PROPOSED_METHOD_EDITS.json 的 9 处局部替换，避免把整节重写一遍。

## 方法的核心意思

{method_en}

忠实中文：

{method_zh}

保留原有 η 符号。仅把公式分母从旧变量替换为 N_iso，定义为同一条泊松时间轴中叠加前通过筛选的信号事例数；分子为其中叠加后仍通过筛选的事例数。主动 BGO 损失则以叠加后仍落入能窗的信号为分母，避免把能窗/康普顿损失混入主动屏蔽损失。

## 结合新计数的结果段

{result_en}

忠实中文：

{result_zh}

## 只需同步数字的原句

第 15 天最终信号率：Under-stage {a['day15']['signal_final_rate_cps']:.4g} s⁻¹，Lateral-chimney {b['day15']['signal_final_rate_cps']:.4g} s⁻¹。

20 天计数、显著度、通量和达到时间见 REPORT_ZH.md 第 3 节及 data/RESULTS.json。落稿前必须保持 BGO 口径一致；不把旧双通道的本底数值和本次 BGO 保留率混在同一列。保留几何中的塑料材料差异见报告第 4 节，不能由这段离线表述掩盖。

Figure 5 保留原三路泊松图。正文中用于天体观测意义的“probe”和泊松过程“Conditional on the event count”是正常术语，不属于旧信号方法，不作机械删除。
'''
(O/'PROPOSED_WORDING_ZH.md').write_text(wording)
code_manifest=[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted((O/'code').glob('*')) if p.is_file()]
handoff={'status':'COMPLETE__COMPUTED_NOT_APPLIED_TO_PAPER','user_request':'直接三路泊松叠加、实际沉积及主动屏蔽损失统计；提供新数据和最小表述，暂不改论文','package':str(O),'latest_manuscript_unchanged':str(M),'summary':str(O/'REPORT_ZH.md'),'wording':str(O/'PROPOSED_WORDING_ZH.md'),'method_edits':str(O/'PROPOSED_METHOD_EDITS.json'),'data':str(O/'data/RESULTS.json'),'validation':str(O/'validation/FINAL_CHECKS.json'),'signal_probe_called':False,'new_transport':False,'models':{k:{'display_name':v['display_name'],'active_BGO_loss_fraction':loss(v['pooled_active_BGO_retention']),'active_BGO_loss_ci95':loss_ci(v['pooled_active_BGO_retention']),'retention_day15':v['day15']['eta_bgo']} for k,v in R['models'].items()},'limitations':['Underlying retained Under-stage transport still includes plastic material and original timing occupancy; BGO-only offline veto is not a no-plastic transport model.','Finite physical signal counts support percent-level reporting, not the old substitute-draw precision.','BGO-only change also changes five direct delayed-background survivors; do not attribute that to the signal method or mix normalization columns.'],'code_manifest':code_manifest,'next_action':'等待用户后续指示；当前没有修改 TeX/PDF/图表，也未更新最新稿指针。'}
(O/'MACHINE_HANDOFF.json').write_text(json.dumps(handoff,indent=2,ensure_ascii=False)+'\n')
print('Wrote report, proposed wording, and machine handoff')
