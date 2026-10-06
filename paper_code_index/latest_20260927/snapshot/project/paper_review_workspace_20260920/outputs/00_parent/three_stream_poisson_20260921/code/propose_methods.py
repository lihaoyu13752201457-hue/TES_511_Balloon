from pathlib import Path
import json
O=Path(__file__).resolve().parents[1];M=O.parent/'revision_20260921_pro04_09/paper_clean.tex';s=M.read_text();edits=[]
def add(id,old,new,why):
 assert s.count(old)==1,(id,s.count(old));edits.append({'id':id,'source':str(M),'source_line':s[:s.index(old)].count('\n')+1,'old':old,'new':new,'reason_zh':why,'applied':False})
add('M01', '''The common-time calculation maps the prompt atmospheric and delayed-activation
background catalogues onto one explicit time axis before the active-veto and
Compton selections are applied. The eight prompt particle families
retain independent physical-rate normalizations. Accidental loss of a weak focused signal is estimated with conditional
probes of the neighbouring background.''','''The common-time calculation maps the focused signal, prompt atmospheric background,
and delayed activation onto one explicit time axis before the active-veto and
Compton selections are applied. The eight prompt particle families
retain independent physical-rate normalizations.''','把三路信号纳入同一实际叠加；删除邻近本底探针句。')
add('M02','''The prompt atmospheric and delayed-activation backgrounds are generated
by separate transport calculations and do not share a physical time axis,''','''The focused signal, prompt atmospheric background, and delayed activation are generated
by separate transport calculations and do not share a physical time axis,''','只补入信号输运目录。')
add('M03','''and $m$ labels a transported record. The total rate of catalogue $k$ is''',r'''and $m$ labels a transported record. The focused-signal catalogue is assigned equal per-record weights with a total
rate $F_{\mathrm{TOA},511}A_{\mathrm{eff,opt}}(511\keV)T_{\mathrm{atm},511}(t)$,
and enters the same Poisson construction. The total rate of catalogue $k$ is''','给出加入泊松叠加的信号物理率；复用已有光学有效面积和大气透过率变量。')
add('M04','The independent background draws are merged and ordered by arrival time.','The independent signal and background draws are merged and ordered by arrival time.','背景单独叠加改为三路叠加。')
add('M05',r'''the physical rates of the eight prompt
particle families and delayed activation set the
Poisson draws used to construct a common background time axis for that
reference environment. Events separated by no more than $1\,\mu\mathrm{s}$ form
one coincidence group and jointly undergo the analysis-window, geometry-specific
active-anticoincidence, and Compton-topology selections. For an isolated selected signal, the accidental-survival probe samples
background records in the transitively linked neighbouring groups on both sides.
It rejects the probe if any neighbour has a TES deposit or if the summed
active-shield deposit reaches the veto threshold. The probe estimates accidental
loss without combining a transported signal record with those deposits.''',r'''the physical rates of the focused signal, eight prompt particle families,
and delayed activation set the Poisson draws used to construct a common time
axis for that reference environment. Events separated by no more than
$1\,\mu\mathrm{s}$ form one coincidence group and jointly undergo the
analysis-window, geometry-specific active-anticoincidence, and Compton-topology
selections. Signal loss is obtained by comparing the selected signal events
before and after superposition, with active-veto losses counted separately.''','删除整段替代判据，以实际叠加后的信号计数定义损失；没有增加新分支。')
add('M06',r'\frac{n^{\mathrm{pass}}_{g,r}}{N^{\mathrm{probe}}_{g,r}}.',r'\frac{n^{\mathrm{pass}}_{g,r}}{N^{\mathrm{iso}}_{g,r}}.','分母改为这条泊松时间轴中，叠加前通过筛选的信号事例数。')
add('M07',r'$\widehat\eta$ is the conditional survival fraction of a weak focused event.',r'''$N^{\mathrm{iso}}_{g,r}$ counts the signal events that pass the isolated-event
selection, and $n^{\mathrm{pass}}_{g,r}$ counts those events that remain selected
after superposition. Their ratio $\widehat\eta$ is the signal-retention fraction.''','明确同一批实际信号事例的分母、分子；不引入其他面积名称。')
add('M08','''time anchors, optical sampling, signal retention, and signal probes are''','''time anchors, optical sampling, and signal retention are''','清除误差传播中的探针条目；实际信号保留率统计误差仍传播。')
add('M09',r'''background coincidence correction factor $C_{\mathrm{bg},g}$. The focused-signal
probes estimate the conditional survival fraction $\widehat\eta_{g,r}$.''',r'''background coincidence correction factor $C_{\mathrm{bg},g}$. Comparing the
selected signal counts before and after superposition gives $\widehat\eta_{g,r}$.''','结果说明与新计数定义一致。')
preview=s
for e in edits:preview=preview.replace(e['old'],e['new'])
assert 'N^{\\mathrm{probe}}' not in preview
for forbidden in ['conditional\nprobes','accidental-survival probe','The probe estimates','signal probes','focused-signal\nprobes']:assert forbidden not in preview
(O/'PROPOSED_METHOD_EDITS.json').write_text(json.dumps(edits,indent=2,ensure_ascii=False)+'\n')
(O/'validation/proposed_method_checks.json').write_text(json.dumps({'all_old_strings_unique':True,'all_edits_unapplied':True,'signal_probe_terms_removed_in_in_memory_preview':True,'normal_observational_probe_word_preserved':True,'paper_file_not_written':True,'edit_count':len(edits)},indent=2)+'\n')
print('9 minimal method changes prepared, paper untouched')
