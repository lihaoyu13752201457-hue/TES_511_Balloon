from pathlib import Path
import csv,hashlib,json,math,re,sys,zipfile
import numpy as np
O=Path(__file__).resolve().parents[1];P=O.parent;W=O.parents[2]
sys.path.insert(0,str(P/'latest_manuscript_audit_20260920/_deps'))
import pymupdf as pdf
src=(O/'paper_clean.tex').read_text();log=(O/'paper_clean.log').read_text()
read=lambda f:json.loads(Path(f).read_text())
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
checks={};detail={}
checks['backup_matches_original']=sha(O/'baseline/paper_clean.tex')==sha(P/'final_manuscript_20260924_authors_antarctic/paper_clean.tex')=='dc856b91bd357c0f3ecc5f674a0238cc0b30784d3dcc0ad5b655a02b5f23989d'
checks['backup_pdf_matches_original']=sha(O/'baseline/paper_clean.pdf')==sha(P/'final_manuscript_20260924_authors_antarctic/paper_clean.pdf')
checks['clean_compile_has_no_missing_references_or_characters']=not re.search(r'undefined|Missing character|LaTeX Error|Overfull',log,re.I)
refs=set(re.findall(r'\\(?:ref|eqref)\{([^}]+)\}',src));labels=re.findall(r'\\label\{([^}]+)\}',src)
checks['all_cross_references_defined']=refs<=set(labels)
checks['unique_labels']=len(labels)==len(set(labels))
body=src.split(r'\begin{thebibliography}')[0]
citations=[]
for group in re.findall(r'\\cite\{([^}]+)\}',body):
    for k in group.split(','):
        if k not in citations:citations.append(k)
bib=re.findall(r'\\bibitem\{([^}]+)\}',src)
checks['all_citations_defined']=set(citations)<=set(bib)
checks['references_in_first_citation_order']=citations==[x for x in bib if x in citations]
detail['first_citation_order']=citations
figures=re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',src)
checks['seventeen_figure_files_present']=len(figures)==17 and all((O/f).is_file() for f in figures)
changed=[]
for f in figures:
    old=O/'baseline'/f;new=O/f
    if sha(old)!=sha(new):changed.append(f)
checks['only_expected_figures_changed']=set(changed)=={f'figures/fig{n:02}.pdf' for n in [7,9,10,11,12,13,14,15,16]}
detail['changed_figures']=changed
checks['timing_sentence_once']=src.count('Motivated by the nanosecond timing capability reported for BGO detectors and microsecond arrival-time estimates derived from TES pulse rising edges, we adopt a reference coincidence time scale of')==1
checks['no_extra_pulse_recovery_qualification']='pulse-recovery' not in src and 'pulse recovery' not in src
checks['removed_passages_absent']=all(x not in src for x in ['the uncertainty is statistical','These uncertainties are conditional','416-record total','16.4','so no single delayed','these values are most useful for setting the priority'])
checks['signal_retention_range_paragraph_removed']='0.9559--0.9747' not in src
checks['eta_defined_before_use']=src.index(r'$\widehat\eta_{g,r}$ is the fraction')<src.index(r'S_g(t)=S^{\mathrm{dir}}_g(t)\eta_g(t)')
checks['only_final_compton_results_repeat_9801']=src.count('98.01')==2
checks['no_probe_or_24_point_method']=not re.search(r'signal probe|N\^\{\\mathrm\{probe\}|24 azimuth|24-point',src,re.I)
V=read(O/'data/paper_values_corrected_current_sample.json');R=read(O/'data/RESULTS.json')
def rows(p):
    with Path(p).open() as f:return list(csv.DictReader(f))
for m in 'ab':
    rs=rows(O/f'data/{m}/selected_delayed_origins_enriched.csv');w=np.array([float(x['day15_weight_cps']) for x in rs]);z=V[m]['compton_trajectory_veto']['delayed']
    checks[m+'_selected_origin_count']=len(w)==z['n']
    checks[m+'_origin_rate_sum']=math.isclose(float(w.sum()),z['rate'],rel_tol=1e-11)
    checks[m+'_origin_weighted_standard_error']=math.isclose(float(np.sqrt(w@w)),z['sigma'],rel_tol=1e-11)
    rs=rows(O/f'data/{m}/mission_81nodes.csv');days=np.array([float(r['day']) for r in rs]);s=np.array([float(r['signal_final_rate_cps']) for r in rs]);b=np.array([float(r['background_final_cps']) for r in rs]);dt=np.diff(days)*86400
    ns=float(np.sum((s[:-1]+s[1:])/2*dt));nb=float(np.sum((b[:-1]+b[1:])/2*dt));r=R['models'][m]['mission_20day']
    checks[m+'_81_node_integral']=len(rs)==81 and math.isclose(ns,r['Ns'],rel_tol=1e-12) and math.isclose(nb,r['Nb'],rel_tol=1e-12)
    checks[m+'_sensitivity_from_counts']=math.isclose(2.4e-4*3*math.sqrt(nb)/ns,r['F3'],rel_tol=1e-12)
    checks[m+'_day15_rate_same_in_time_data']=math.isclose(float(rs[60]['background_direct_BGO_cps']),V[m]['compton_trajectory_veto']['total']['rate'],rel_tol=1e-12)
    detail[m]={'Ns20':ns,'Nb20':nb,'F3':r['F3'],'day15_delayed_rate':z['rate']}
with pdf.open(O/'paper_clean.pdf') as d:
    detail['clean_pages']=len(d)
    extracted='\n'.join(p.get_text() for p in d)
checks['compiled_text_contains_timing_and_decay_update']='nanosecond timing capability' in extracted and 'RadioactiveDecay 6.1.2' in extracted
detail['remaining_author_fields']=re.findall(r'\\projectfill\{([^}]+)\}',src)
result={'result':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'detail':detail,'scope':'Document, compact-result consistency and compilation checks; no new production simulation.'}
(O/'validation/FINAL_CHECKS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
if not all(checks.values()):raise SystemExit(1)

(O/'COMPILE_README.txt').write_text('Compile paper_clean.tex with XeLaTeX three times. All 17 figure PDFs are included. Main font: TeX Gyre Termes. Red TO BE FILLED fields are author metadata and declarations awaiting confirmation; corresponding-author emails remain omitted as requested.\n')
with zipfile.ZipFile(O/'paper_source.zip','w',zipfile.ZIP_DEFLATED) as z:
    for f in [O/'paper_clean.tex',O/'COMPILE_README.txt',*[O/x for x in figures]]:z.write(f,f.relative_to(O))
with zipfile.ZipFile(O/'original_backup.zip','w',zipfile.ZIP_DEFLATED) as z:
    for f in [O/'baseline/paper_clean.tex',O/'baseline/paper_clean.pdf',O/'baseline/BACKUP_MANIFEST.json',*sorted((O/'baseline/figures').glob('*.pdf'))]:z.write(f,f.relative_to(O/'baseline'))
print('Source and original backup archives written.')
