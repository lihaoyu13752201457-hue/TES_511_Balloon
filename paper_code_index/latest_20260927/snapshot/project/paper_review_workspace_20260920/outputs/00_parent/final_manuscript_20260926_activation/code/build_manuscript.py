from pathlib import Path
import copy, csv, hashlib, json, math, re, shutil

O=Path(__file__).resolve().parents[1]
P=O.parent
B=P/'final_manuscript_20260924_authors_antarctic'
D=P/'activation_correction_20260924/production_repair_20260925/final/data'
src=(O/'baseline/paper_clean.tex').read_text()
text=src
changes=[]
def change(key,old,new,reason):
    global text
    assert text.count(old)==1,(key,text.count(old),old[:100])
    changes.append(dict(id=key,old=old,new=new,reason=reason,
        baseline_line=src[:src.index(old)].count('\n')+1 if old in src else None))
    text=text.replace(old,new,1)

proposed=json.loads((P/'activation_manuscript_proposal_20260926/CHANGES_PROPOSED.json').read_text())
items={x['id']:copy.deepcopy(x) for x in proposed['text_and_caption_changes']}
local=json.loads((P/'activation_proposal_concise_20260926/CHANGES_PROPOSED.json').read_text())
for x in local['text_and_caption_changes']:items[x['id']]=x
# Keep the original source-attribution terminology, defined explicitly once.
for i in ['12','20','27','F07','F10','F11','F12']:
    s=items[i]['proposed_en']
    for old,new in [('initially-produced-nuclide','parent-nuclide'),
                    ('initially produced nuclides','parent nuclides'),
                    ('initially produced nuclide','parent nuclide'),
                    ('production-nuclide compositions','parent-nuclide compositions')]:s=s.replace(old,new)
    items[i]['proposed_en']=s
items['12']['proposed_en']=items['12']['old_en']+'''\nHere the parent nuclide denotes the initially produced activation product;
its contribution includes selected decays of its radioactive descendants.'''

items['02']['proposed_en']=r'''The delayed source is built from a separate activation-production transport.
This stage records the nuclide, material volume, incident species, and stopping
position of each radioactive product retained for delayed transport.
Ground-state half-lives are checked against NUBASE2020 \cite{Kondev2021NUBASE}.
In the transport configuration used here, no decay products were generated
for $^{158}$Er. We addressed this issue with additional simulations using
Geant4 RadioactiveDecay 6.1.2 and the corresponding $^{158}$Ho level data
from PhotonEvaporation 6.1.
Nuclide activities include direct production and feeding from radioactive
parents. For nuclear state $k$, $A_k(t)=\lambda_kN_k(t)$, with
$\lambda_k=\ln2/t_{1/2,k}$. The reference epoch is
$t_{\mathrm{flight}}=15\,\mathrm{d}$; the inventory evolution is defined in
Section~\ref{sec:mission_time_fold}.'''
items['03']['proposed_en']=r'''The radioactive-product records retain the nuclide identities and stopping
positions used to construct the delayed source. Direct production is normalized
separately for each incident-particle species using its activation-production
exposure. Daughter feeding is included in the inventory evolution, while
the original production material and position are retained for source tracing.'''
items['04']['proposed_en']=r'''Balancing computational cost against statistical precision, the initial
decay transport used $10^4$ activation-position point sources for each
incident-particle species with nonzero delayed-source activity. Source
nuclides were sampled by their day-15 activities in each production volume,
with positions drawn uniformly from the matched production coordinates.
Additional decays were simulated for selected nuclear states with known
sampling probabilities. The normalization includes all simulated decay events,
including those with no detector energy deposit. Each daughter response retains
the original activation product's identity and position, separately from the
identity of the decaying nuclide.
Figure~\ref{fig:activation_source_positions} shows the production sites for
delayed events passing all selections.'''
items['05']['proposed_en']=r'''Decay responses are normalized separately for each configuration and
incident-particle species. Each event is weighted by the time-dependent
activity of its decaying nuclear state divided by the corresponding sampling
normalization. For the initial transport samples, this normalization accounts
for the finite transport exposure and daughter decays generated during it.
For independently sampled states, it uses the number of simulated decays and
their sampling probabilities, including decays with no detector energy deposit.
Sample sizes are listed in Table~\ref{tab:background_source_model}.'''
# Other requested edits concern the already reviewed computation and its numbers.
for i,x in items.items():
    if i in ['38','39']:continue
    change(i,x['old_en'],x['proposed_en'],x.get('reason','Approved activation correction'))

sentence=r'Motivated by the nanosecond timing capability reported for BGO detectors and microsecond arrival-time estimates derived from TES pulse rising edges, we adopt a reference coincidence time scale of $1\,\mu\mathrm{s}$.'
anchor='The radiation environment evolves along the balloon trajectory, but much more'
change('TIME01',anchor,sentence+'\n\n'+anchor,'Insert only the sentence supplied by the user; no additional timing qualification.')

# Synchronize only the previously identified terminology candidates.
for old,new,key in [
    ('signal-survival fractions','signal-retention fractions','TERM01'),
    ('accidental signal-survival fraction','signal-retention fraction after accidental coincidences','TERM02'),
    ('In the isolated-event diagnostics,','In the isolated-event results,','TERM03'),
    ('\\textit{Isolated-event diagnostics}','\\textit{Isolated-event results}','TERM04'),
    ('in the near-field shield','in the nearby shield','TERM05'),
    ('activation-prone near-field structures','activation-prone structures near the TES','TERM06'),
    ('the next near-field redesign','further modifications to these structures','TERM07')]:
    if old in text:change(key,old,new,'Use established detector terminology consistently without a blanket rewrite.')

V=json.loads((D/'paper_values_corrected_current_sample.json').read_text())
R=json.loads((D/'RESULTS.json').read_text())
E=json.loads((D/'environment_results.json').read_text())
T3=json.loads((D/'table3_delayed_replacement.json').read_text())
for name in ['paper_values_corrected_current_sample.json','RESULTS.json','environment_results.json','table3_delayed_replacement.json','ANCHORS.csv']:
    shutil.copy2(D/name,O/'data'/name)
for m in 'ab':
    (O/'data'/m).mkdir(exist_ok=True)
    for name in ['direct_spectra.csv','direct_81nodes.csv','mission_81nodes.csv','selected_delayed_origins_enriched.csv','anchor_060_results.json']:
        shutil.copy2(D/m/name,O/'data'/m/name)
    for n in [0,20,40,80]:shutil.copy2(D/m/f'anchor_{n:03d}_results.json',O/'data'/m/f'anchor_{n:03d}_results.json')

def num(x,sig=4):
    if x==0:return '0'
    if abs(x)<.1 or abs(x)>=1e4:
        a,b=f'{x:.{sig-1}e}'.split('e');return a+r'\times10^{'+str(int(b))+'}'
    return f'{x:.{sig}g}'
def count(x):return f'{int(round(x)):,}'.replace(',',r'{,}')
def tabular(label,index=0):
    start=text.index(r'\label{'+label+'}')
    end=text.index(r'\end{table}',start)
    matches=list(re.finditer(r'\\begin\{tabular\}.*?\\end\{tabular\}',text[start:end],re.S))
    return matches[index].group()
stages=['pre_veto','combined_active_veto','compton_trajectory_veto']
for model,label in [('a','tab:phase2_cutflow'),('b','tab:optimized_cutflow')]:
    old=tabular(label);new=old
    for stream,caption in [('delayed','Delayed activation'),('total','Total background')]:
        row=caption+' & '+' & '.join(str(V[model][s][stream]['n'])+' / $'+num(V[model][s][stream]['rate'])+r'\cps$' for s in stages)+r' \\'
        oldrow=re.search(r'^'+caption+r' &.*$',new,re.M).group()
        new=new.replace(oldrow,row,1)
    if model=='b':
        row=r'Total background & 491354 / $2.457\cps$ & 2388 / $1.194\times10^{-2}\cps$ & 2320 / $1.160\times10^{-2}\cps$ \\'
        oldrow=re.findall(r'^Total background &.*$',new,re.M)[1]
        new=new.replace(oldrow,row)
    change('TABLE_'+model+'_cutflow',old,new,'Update delayed and total rows; preserve prompt and signal samples.')
for model,label in [('a','tab:reference_background_budget'),('b','tab:optimized_component_precision')]:
    old=tabular(label);new=old;total=V[model][stages[-1]]['total']['rate']
    for stream,caption in [('non_gamma',r'Non-$\gamma$ prompt'),('gamma',r'Atmospheric $\gamma$'),('delayed','Delayed activation'),('total','Total')]:
        z=V[model][stages[-1]][stream]
        if model=='a' and stream=='non_gamma':continue
        line=next(x for x in new.splitlines() if x.startswith(caption+' &'))
        row=caption+f" & {z['n']} & $"+num(z['rate'])+'$ & $'+num(z['sigma'])+f"$ & {z['neff']:.2f} & {100*z['rate']/total:.2f}"+r' \\'
        new=new.replace(line,row)
    change('TABLE_'+model+'_precision',old,new,'Keep the weighted standard-error definition; update values from final retained results.')
old=tabular('tab:background_source_model',1)
lines=[r'\begin{tabular}{clrrrr}',r'\toprule',r'Model & Species & $N_{\mathrm{rec}}$ & $N_{\mathrm{add}}$ & $N_{\mathrm{det+}}$ & $R_{\mathrm{cat},15}$ ($\mathrm{s^{-1}}$) \\',r'\midrule']
species={'gamma':r'\gamma','n':'n','eminus':'e^-','eplus':'e^+','p':'p','alpha':r'\alpha','muminus':r'\mu^-','muplus':r'\mu^+'}
for model,name in [('a','Under-stage'),('b','Lateral-chimney')]:
    if model=='b':lines.append(r'\midrule')
    for k,z in enumerate(x for x in T3 if x['model']==model):
        lines.append((name if k==0 else ' ')+ ' & $'+species[z['family']]+'$ & $'+count(z['original_raw_decay_records'])+'$ & $'+count(z['targeted_independent_histories'])+'$ & $'+count(z['positive_response_groups'])+'$ & $'+num(z['day15_detector_positive_rate_cps'])+r'$ \\')
lines += [r'\bottomrule',r'\end{tabular}']
change('TABLE3B',old,'\n'.join(lines),'Use original records and additional independent decays; remove the inapplicable single delayed exposure column.')
old=tabular('tab:primary_sensitivity');new=old
missions=[R['models'][m]['mission_20day'] for m in 'ab']
replacement=[
    ('Day-15 isolated-event background / cps',[num(V[m][stages[-1]]['total']['rate']) for m in 'ab']),
    (r'Day-15 signal at $\fref$ / cps',[num(R['models'][m]['day15']['signal_final_rate_cps']) for m in 'ab']),
    ('20 d background counts',[str(round(x['Nb'])) for x in missions]),
    (r'20 d signal counts at $\fref$',[str(round(x['Ns'])) for x in missions]),
    (r'$Z_{20\mathrm d}=N_s/\sqrt{N_b}$',[f"{x['Z']:.2f}" for x in missions]),
    (r'$T_{3\sigma}$ at $\fref$ / d',[f"{x['T3_days']:.3f}" for x in missions]),
    (r'$T_{5\sigma}$ at $\fref$ / d',[f"{x['T5_days']:.3f}" for x in missions]),
    (r'$F_{3\sigma}(20\,\mathrm d)$ / $\phcms$',[f"({x['F3']*1e5:.2f}"+r'\pm'+f"{x['F3_MC_SE_approx']*1e5:.2f})"+r'\times10^{-5}' for x in missions]),
    (r'$F_{5\sigma}(20\,\mathrm d)$ / $\phcms$',[f"({x['F5']*1e5:.2f}"+r'\pm'+f"{x['F5_MC_SE_approx']*1e5:.2f})"+r'\times10^{-5}' for x in missions])]
for prefix,vals in replacement:
    oldrow=next(x for x in new.splitlines() if x.startswith(prefix+' &'))
    new=new.replace(oldrow,prefix+' & $'+vals[0]+'$ & $'+vals[1]+r'$ \\')
change('TABLE6',old,new,'Update rates, cumulative counts, thresholds and correlated Monte Carlo errors together.')
old=tabular('tab:environment_screening');new=old
for prefix,z in zip(['Balloon reference','Antarctic balloon','530 km LEO','Exposed lunar surface','Sun--Earth L2 (2014)','Sun--Earth L2 (2009)'],E['screening']):
    oldrow=next(x for x in new.splitlines() if x.startswith(prefix+' &'))
    cols=oldrow.split(' & ')
    cols[-2]=f"{z['ratio']:.3f}" if z['ratio']<10 else f"{z['ratio']:.2f}"
    cols[-1]='$'+num(z['F3'])+r'$ \\'
    new=new.replace(oldrow,' & '.join(cols))
change('TABLE7',old,new,'Use the same corrected balloon response for all six spectral estimates.')

assert 'the uncertainty is statistical' not in text
assert '16.4' not in text
assert '416-record total' not in text
assert r'\widehat\eta_{g,r}$ is the fraction' in text
assert text.count(sentence)==1
assert not any(x in text for x in ['signal probe','N^{\\mathrm{probe}}','24 azimuth','24-point'])
(O/'paper_clean.tex').write_text(text)
(O/'CHANGES.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
(O/'data/TEXT_BUILD_MANIFEST.json').write_text(json.dumps({'baseline':str(B),'baseline_sha256':hashlib.sha256(src.encode()).hexdigest(),'applied_changes':len(changes),'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'not_applied_optional_items':['S01','S02','S03','S04'],'withheld_full_term_renaming':['38','39'],'timing_sentence':sentence,'raw_simulations_rerun':False},indent=2)+'\n')
print('Manuscript text updated:',len(changes),'tracked changes')
