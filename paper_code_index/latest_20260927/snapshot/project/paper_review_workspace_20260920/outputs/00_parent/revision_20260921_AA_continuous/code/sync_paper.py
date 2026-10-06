from common import *
import re,difflib
base=(O/'baseline/merged_before_this_edit.tex').read_text();s=base;changes=[]
def replace(old,new):
 global s
 assert old in s,old
 if old==new:return
 s=s.replace(old,new)
 changes.append({'old':old,'new':new,'occurrences':base.count(old),'reason':'AA data replacement / continuous selection recalculation; numerical values only'})
def scoped(old,new,a,b):
 global s
 i=s.index(a);j=s.index(b,i);part=s[i:j];assert old in part,old
 part=part.replace(old,new);s=s[:i]+part+s[j:]
def sci(v,d=3):
 if v==0:return '0'
 power=int(math.floor(math.log10(abs(v))));return f'{v/10**power:.{d}f}'+r'\times10^{'+str(power)+'}'
def compact(v):
 if v==0:return '0'
 return f'{v:.4g}' if .1<=v<1e4 else sci(v)
def integer(v):return f'{round(v):,}'.replace(',',r'{,}')
def table(label,fn):
 global s
 pattern=r'\\begin\{table\}.*?\\end\{table\}'
 for m in re.finditer(pattern,s,re.S):
  if '\\label{'+label+'}' in m.group():
   old=m.group();new=fn(old);s=s[:m.start()]+new+s[m.end():];return
 raise ValueError(label)
def line(t,prefix,new):
 ls=t.splitlines();found=[i for i,x in enumerate(ls) if x.startswith(prefix)];assert len(found)==1,(prefix,found);ls[found[0]]=new;return '\n'.join(ls)
V=read(O/'data/paper_values_500.json');R=read(O/'data/RESULTS.json');A=V['a'];B=V['b'];M=R['models'];ma=M['a']['mission_20day'];mb=M['b']['mission_20day'];sg={m:read(O/f'data/{m}/signal_summary.json')['counts']['narrow'] for m in 'ab'}
# Only prose edit: delete the discrete sampling and connecting-segment clauses.
old='''81 candidate cones. Each cone is sampled
at 24 uniformly spaced azimuths and extended forward to the entrance plane. The
cone intersects the disk if a sampled point lies inside it or if a segment
joining adjacent samples crosses it. One intersection among the 81 candidate
cones is sufficient to retain that order.'''
new='''81 candidate cones. One intersection among the 81 candidate
cones is sufficient to retain that order.'''
replace(old,new);changes[-1]['reason']='User-authorized deletion of 24-point sampling and connecting-segment description.'
# Direct cut-flow tables; existing headings/captions retained.
stages=['pre_veto','combined_active_veto','compton_trajectory_veto']
for model,label in [('a','tab:phase2_cutflow'),('b','tab:optimized_cutflow')]:
 def patch(t):
  for prefix,key in [('Non-$\\gamma$ prompt','non_gamma'),('Atmospheric $\\gamma$','gamma'),('Delayed activation','delayed')]:
   vals=[V[model][st][key] for st in stages];t=line(t,prefix,prefix+' & '+' & '.join(f"{v['n']} / ${compact(v['rate'])}\\cps$" for v in vals)+r' \\')
  # B has a second total row for actual timeline groups.
  ls=t.splitlines();ix=[i for i,l in enumerate(ls) if l.startswith('Total background &')]
  vals=[V[model][st]['total'] for st in stages];ls[ix[0]]='Total background & '+' & '.join(f"{v['n']} / ${compact(v['rate'])}\\cps$" for v in vals)+r' \\'
  if model=='b':
   rr=read(O/'data/b/anchor_060_results.json');T=rr['timeline']['T'];ns=[rr[k] for k in ['background_pre_count','background_active_count','background_bgo_final_count']];ls[ix[1]]='Total background & '+' & '.join(f'{n} / ${compact(n/T)}\\cps$' for n in ns)+r' \\'
  t='\n'.join(ls);v=sg[model];t=line(t,'Focused signal &',f"Focused signal & {v['pre']} / $100\\%$ & {v['active']} / $100\\%$ & {v['final']} / ${100*v['final']/v['pre']:.2f}\\%$"+r' \\');return t
 table(label,patch)
for model,label in [('a','tab:reference_background_budget'),('b','tab:optimized_component_precision')]:
 def patch(t):
  for prefix,key in [('Non-$\\gamma$ prompt','non_gamma'),('Atmospheric $\\gamma$','gamma'),('Delayed activation','delayed'),('Total &','total')]:
   if not any(l.startswith(prefix) for l in t.splitlines()):continue
   v=V[model][stages[-1]][key];name='Total' if key=='total' else prefix
   t=line(t,prefix,name+f" & {v['n']} & ${sci(v['rate'])}$ & ${sci(v['sigma'])}$ & {v['neff']:.2f} & {100*v['rate']/V[model][stages[-1]]['total']['rate']:.2f}"+r' \\')
  return t
 table(label,patch)
# AA source normalization table: preserve B rows, independent family weights.
tt=read(O/'data/aa_transport_table.json');labels={'gamma':r'\gamma','n':'n','eminus':'e^-','eplus':'e^+','p':'p','alpha':r'\alpha','muminus':r'\mu^-','muplus':r'\mu^+'}
def transport(t):
 for stream in ['prompt','delayed']:
  start=t.index('Under-stage &');end=t.index('\\midrule',start)
  out=[]
  for r in [x for x in tt if x['stream']==stream]:
   n=r['transported'];ns=('$'+integer(n)+'$') if stream=='prompt' else (r'$1.0\times10^6$' if n else '$0$')
   eq=('$'+compact(r['Teq_s'])+'$') if r['Teq_s'] is not None else '--'
   out.append(('Under-stage' if r['family']=='gamma' else ' ')+f" & ${labels[r['family']]}$ & {ns} & {eq} & ${integer(r['detector_positive'])}$ & ${compact(r['occupancy_day15_cps'])}$"+r' \\')
  # For delayed, search second Under-stage after prompt was patched.
  if stream=='delayed':
   start=t.index('Under-stage &',t.index(r'\textit{(b)'));end=t.index('\\midrule',start)
  t=t[:start]+'\n'.join(out)+'\n'+t[end:]
 return t
table('tab:background_source_model',transport)
# Numerical tokens in prose, preserving every surrounding phrase.
pre=A['pre_veto'];act=A['combined_active_veto'];fin=A['compton_trajectory_veto'];tot=fin['total']['rate'];delay=fin['delayed']['rate'];origin=A['origin_statistics']
repls={
 r'5.63\times10^{-2}':sci(tot,2),r'5.629\times10^{-2}':sci(tot),r'3.840\times10^{-2}':sci(delay),r'1.789\times10^{-2}':sci(fin['gamma']['rate']),
 '3,093 records':f"{pre['total']['n']:,} records",r'5.451\cps':f"{pre['total']['rate']:.3f}\\cps",'to 444 records':f"to {act['total']['n']} records",r'6.327\times10^{-2}':sci(act['total']['rate']),r'98.84\%':f"{100*(1-act['total']['rate']/pre['total']['rate']):.2f}\\%",
 r'2.919\cps':f"{pre['non_gamma']['rate']:.3f}\\cps",r'2.364\cps':f"{pre['gamma']['rate']:.3f}\\cps",r'2.045\times10^{-2}':sci(act['gamma']['rate']),r'0.1675\cps':f"{pre['delayed']['rate']:.4f}\\cps",r'4.282\times10^{-2}':sci(act['delayed']['rate']),
 '400 background records':f"{fin['total']['n']} background records",r'88.98\%':f"{100*tot/act['total']['rate']:.2f}\\%",'22,032':'28,394','21,303':'27,426',r'96.69\%':f"{100*sg['a']['final']/sg['a']['pre']:.2f}\\%",r'68.22\%':f'{100*delay/tot:.2f}\\%',r'31.78\%':f"{100*fin['gamma']['rate']/tot:.2f}\\%",'400-record total':'409-record total',r'N_{\mathrm{eff}}=47.14':f"N_{{\\mathrm{{eff}}}}={fin['total']['neff']:.2f}",
 '36 records':f"{origin['families']['p']['n']} records",r'2.555\times10^{-2}':sci(A['origin_families']['p']),r'45.39\%':f"{100*A['origin_families']['p']/tot:.2f}\\%",
 r'7.492\times10^{-3}':sci(A['origin_families']['alpha']),r'3.601\times10^{-3}':sci(A['origin_families']['n']),r'1.655\times10^{-3}':sci(A['origin_families']['gamma']),r'7.607\times10^{-5}':sci(A['origin_families']['eplus']),r'2.592\times10^{-5}':sci(A['origin_families']['eminus']),
 r'71.39\%':f"{100*A['origin_materials']['Copper']/delay:.2f}\\%",r'33.47\%':f"{100*A['origin_regions']['DR/MXC and cold plates']/delay:.2f}\\%",
 '28,001':'28,000',r'98.02\%':f"{100*sg['b']['final']/sg['b']['pre']:.2f}\\%",r'9.701\%':f"{100*B['compton_trajectory_veto']['delayed']['rate']/delay:.3f}\\%",r'32.77\%':f"{100*B['compton_trajectory_veto']['gamma']['rate']/fin['gamma']['rate']:.2f}\\%",r'20.25\%':f"{100*B['compton_trajectory_veto']['total']['rate']/tot:.2f}\\%",'factor of 4.94 lower':f"factor of {tot/B['compton_trajectory_veto']['total']['rate']:.2f} lower",
 r'(1.29\pm0.28)\times10^{-2}':f"({A['origin_regions']['DR/MXC and cold plates']*100:.2f}\\pm{origin['regions']['DR/MXC and cold plates']['sigma']*100:.2f})\\times10^{{-2}}",r'(3.84\pm0.46)\times10^{-2}':f"({delay*100:.2f}\\pm{fin['delayed']['sigma']*100:.2f})\\times10^{{-2}}",
 r'1.771\times10^{-2}':sci(A['origin_nuclides']['29062']),r'46.11\%':f"{100*A['origin_nuclides']['29062']/delay:.2f}\\%",r'64.27\%':f"{100*sum(A['origin_nuclides'].get(k,0) for k in ['29061','29062','29064'])/delay:.2f}\\%",
}
for old,k in [(r'28.10\%','mxc_50mk_cu_plate'),(r'27.24\%','tes_substrate_cu_panels'),(r'9.92\%','tes_cu_heat_sink'),(r'7.36\%','nearfield_bi_liner'),(r'15.08\%','al_cryostat_shields'),(r'7.00\%','other_dr_cold_hardware'),(r'3.45\%','w_bottom_plate'),(r'1.87\%','bpe_bgo_shielding')]:repls[old]=f"{100*A['origin_components'].get(k,0)/delay:.2f}\\%"
# Apply longest first; replacement never creates a later original key here.
for old,new in sorted(repls.items(),key=lambda kv:-len(kv[0])):replace(old,new)
# The retained prose explicitly names only L2/L4, so its number uses that pair.
allpanels=f"{100*A['origin_components']['tes_substrate_cu_panels']/delay:.2f}\\%"
pair=sum(A['origin_volumes'].get(k,0) for k in ['Cu_SubstrateSupport_OpenRing_L2_ZP_panel','Cu_SubstrateSupport_OpenRing_L4_YP_panel'])
scoped(allpanels,f'{100*pair/delay:.2f}\\%', 'The two TES substrate-support', 'Figure~\\ref{fig:activation_origin_donuts}')
# Actual mission replay numbers. Preserve the old probe language for the requested separate review list.
replace(r'$2\times10^4$ s for Under-stage',r'$2\times10^5$ s for Under-stage')
for m,old in [('a','1.83'),('b','1.55')]:replace('$'+old+r'\sigma$',f"${M[m]['max_direct_vs_timeline_z']:.2f}\\sigma$")
for old,m,key in [('0.9467--1.0019','a','rho_range'),('0.9885--1.0404','b','rho_range'),('0.9681--0.9704','a','eta_range'),('0.9955--0.9958','b','eta_range')]:replace(old,'--'.join(f'{x:.4f}' for x in M[m][key]))
replace('are 0.9682 and 0.9955',f"are {M['a']['day15']['eta_bgo']:.4f} and {M['b']['day15']['eta_bgo']:.4f}")
for old,m in [(r'1.349\times10^{-3}','a'),(r'1.823\times10^{-3}','b')]:replace(old,sci(M[m]['day15']['signal_final_rate_cps']))
replace('2315/$92{,}871$',f"{ma['Ns']:.0f}/${integer(ma['Nb'])}$");replace('3127/$19{,}752$',f"{mb['Ns']:.0f}/${integer(mb['Nb'])}$")
for old,m in [('$29{,}998$/$62{,}873$','a'),('$10{,}279$/$9{,}473$','b')]:
 vals=M[m]['mission_20day']['background_component_counts'];replace(old,'$'+integer(vals['gamma_continuum'])+'$/$'+integer(vals['other'])+'$')
replace('7.60 for Under-stage',f"{ma['Z']:.2f} for Under-stage");replace('22.25 for Lateral-chimney',f"{mb['Z']:.2f} for Lateral-chimney")
for old,m in [(r'(9.48\pm0.70)\times10^{-5}','a'),(r'(3.24\pm0.29)\times10^{-5}','b')]:
 v=M[m]['mission_20day'];replace(old,f"({v['F3']*1e5:.2f}\\pm{v['F3_MC_SE_approx']*1e5:.2f})\\times10^{{-5}}")
ratio=R['ratios'];replace(r'21.27\%',f"{100*ratio['Nb_lateral_over_under']:.2f}\\%");replace(r'34.14\%',f"{100/ratio['F3_under_over_lateral']:.2f}\\%");replace('1.351',f"{ratio['Ns_lateral_over_under']:.3f}");replace('2.168',f"{math.sqrt(1/ratio['Nb_lateral_over_under']):.3f}");replace('2.930',f"{ratio['F3_under_over_lateral']:.3f}");replace('factor of 2.93',f"factor of {ratio['F3_under_over_lateral']:.2f}")
def mission_table(t):
 specs=[('20 d background counts','Nb',lambda x:f'{x:.0f}'),('20 d signal counts','Ns',lambda x:f'{x:.0f}'),('$Z_','Z',lambda x:f'{x:.2f}'),('$T_{3','T3_days',lambda x:f'{x:.3f}'),('$T_{5','T5_days',lambda x:f'{x:.3f}'),('$F_{3','F3',None),('$F_{5','F5',None)]
 for prefix,key,fmt in specs:
  old=next(l for l in t.splitlines() if l.startswith(prefix));name=old.split(' & ')[0]
  vals=[fmt(v[key]) if fmt else f"({v[key]*1e5:.2f}\\pm{v[key+'_MC_SE_approx']*1e5:.2f})\\times10^{{-5}}" for v in [ma,mb]]
  t=line(t,prefix,name+' & '+' & '.join('$'+v+'$' for v in vals)+r' \\')
 return t
table('tab:primary_sensitivity',mission_table)
# Environment uses the existing transfer ratios with the new balloon normalization.
env=read(O/'data/environment_kernel_500.json')['screening']
for old,r in zip([r'3.236\times10^{-5}',r'1.206\times10^{-5}',r'8.071\times10^{-5}',r'3.850\times10^{-5}',r'5.447\times10^{-5}'],env):replace(old,sci(r['F3_screening_ph_cm2_s']))
(O/'paper_clean.tex').write_text(s)
# Record complete, unique paragraph-level edits (including tables) against frozen baseline.
a=base.split('\n\n');b=s.split('\n\n');chunks=[]
for tag,i,j,k,l in difflib.SequenceMatcher(a=a,b=b,autojunk=False).get_opcodes():
 if tag=='equal':continue
 old='\n\n'.join(a[i:j]);new='\n\n'.join(b[k:l]);assert base.count(old)==1
 chunks.append({'id':f'AA-CONT-{len(chunks)+1:03d}','old':old,'new':new,'reason':'Numerical refill, or deletion of the discrete cone-sampling description.'})
save(O/'CHANGES.json',chunks);save(O/'validation/numeric_replacements.json',changes)
# Assert lexical invariance outside the explicitly approved sampling deletion.
def letters(t):
 t=re.sub(r'\d+(?:[.,]\d+)*','',t);t=t.replace('{,}','').replace(',','').replace('$','').replace('{','').replace('}','').replace('\\times','').replace('^','').replace('--','').replace('-','').replace('+','');return re.findall('[A-Za-z]+',t)
allowed=base.replace(old if False else '''81 candidate cones. Each cone is sampled
at 24 uniformly spaced azimuths and extended forward to the entrance plane. The
cone intersects the disk if a sampled point lies inside it or if a segment
joining adjacent samples crosses it. One intersection among the 81 candidate
cones is sufficient to retain that order.''','''81 candidate cones. One intersection among the 81 candidate
cones is sufficient to retain that order.''')
assert letters(allowed)==letters(s),'Unauthorized lexical change'
save(O/'validation/prose_scope.json',{'status':'PASS','alphabetic_tokens_identical_except_authorized_discrete_sampling_deletion':True,'change_blocks':len(chunks)})
print('PAPER DATA FILLED',len(chunks))
