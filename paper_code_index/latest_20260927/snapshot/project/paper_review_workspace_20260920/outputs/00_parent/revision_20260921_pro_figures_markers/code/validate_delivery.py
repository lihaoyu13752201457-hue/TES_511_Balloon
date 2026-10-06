from pathlib import Path
import sys,re,json,hashlib,zipfile
OUT=Path(__file__).resolve().parents[1];WORK=OUT.parents[2]
BASE=OUT.parent/'final_manuscript_20260921'
sys.path.insert(0,str(WORK/'outputs/00_parent/latest_manuscript_audit_20260920/_deps'))
import pymupdf as pdf
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=(BASE/'paper_clean.tex').read_text();new=(OUT/'paper_clean.tex').read_text()
changes=json.loads((OUT/'CHANGES.json').read_text());rebuilt=old
for c in changes:
    assert rebuilt.count(c['old'])==1,c['id'];rebuilt=rebuilt.replace(c['old'],c['new'],1)
assert rebuilt==new
checks=dict(replacement_reconstruction=True,text_changes=len(changes))
for env in ['tabular','equation','thebibliography']:
    p=r'\\begin\{'+env+r'\}.*?\\end\{'+env+r'\}'
    a=re.findall(p,old,re.S);b=re.findall(p,new,re.S);assert a==b,env
    checks[env+'_bodies_unchanged']=len(a)
abstract=lambda s:s.split(r'\noindent\textbf{Abstract}')[1].split(r'\noindent\textbf{Keywords}')[0]
assert abstract(old)==abstract(new)
title=lambda s:s.split(r'{\LARGE\bfseries ')[1].split(r'\par}')[0]
assert title(old)==title(new)
checks['title_and_abstract_remain_proposals']=True
refs=re.findall(r'\\bibitem\{([^}]+)\}',new);checks['references_unchanged']=len(refs)
assert len(refs)==45
changed=[];same=[]
used=re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',new)
assert len(used)==17
for f in used:
    assert (OUT/f).is_file()
    (same if sha(OUT/f)==sha(BASE/f) else changed).append(f)
assert set(changed)=={'figures/fig08.pdf','figures/fig09.pdf'}
checks['changed_figure_assets']=changed;checks['unchanged_figure_assets']=same
audit=json.loads((OUT/'validation/FIGURE_DATA_CHECKS.json').read_text())
for p,h in audit['inputs'].items():assert sha(Path(p))==h,p
checks['small_input_hashes_unchanged']=audit['inputs']
checks['compile']={};checks['pdf_pages']={}
for stem in ['paper_clean','paper_this_edit_marked','paper_combined_marked']:
    log=(OUT/'validation'/f'{stem}_pass3.txt').read_text()
    bad=[s for s in log.splitlines() if any(q in s for q in [
        'Overfull','Float too large','Missing character','undefined','multiply defined','! LaTeX Error'])]
    assert not bad,(stem,bad)
    d=pdf.open(OUT/(stem+'.pdf'));checks['pdf_pages'][stem]=len(d)
    checks['compile'][stem]=dict(passes=3,errors=[],warnings=[s for s in log.splitlines() if 'Warning:' in s])
    if stem=='paper_clean':
        targets={}
        for i,p in enumerate(d):
            t=' '.join(p.get_text().split())
            for key,needle in [('zero_count','A zero selected'),('figure08','Functional x'),('figure10','Figure 10: Parent-nuclide production sites')]:
                if needle in t:
                    targets[key]=i+1;p.get_pixmap(matrix=pdf.Matrix(1.35,1.35)).save(OUT/'validation'/f'{stem}_p{i+1:02d}.png')
        assert len(targets)==3,targets
        checks['paper_locations']=targets
    d.close()

checks['figure_fonts']={}
for name in ['Figure08','Figure10']:
    d=pdf.open(OUT/'figures'/(name+'.pdf'));p=d[0]
    spans=[s for b in p.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
    scale=min((17/2.54*72)/p.rect.width,(.85*24.8/2.54*72)/p.rect.height)
    scaled=[s['size']*scale for s in spans]
    checks['figure_fonts'][name]=dict(fonts=sorted(set(s['font'] for s in spans)),
        paper_minimum_size_pt=min(scaled),paper_maximum_size_pt=max(scaled),
        includes_smaller_math_superscripts=True,type3_fonts=[f for f in p.get_fonts() if f[2]=='Type3'])
    assert not checks['figure_fonts'][name]['type3_fonts']
    d.close()

preview=pdf.open()
for f in ['Figure08.pdf','Figure10.pdf']:
    d=pdf.open(OUT/'figures'/f);preview.insert_pdf(d);d.close()
preview.save(OUT/'FIGURES_PREVIEW.pdf');preview.close()
with zipfile.ZipFile(OUT/'paper_source.zip','w',zipfile.ZIP_DEFLATED) as z:
    z.write(OUT/'paper_clean.tex','paper_clean.tex')
    for f in used:z.write(OUT/f,f)
with zipfile.ZipFile(OUT/'paper_source.zip') as z:assert z.testzip() is None
checks['source_zip_verified']=True
checks['production_simulation_run']=False
checks['result']='PASS'
(OUT/'validation/FINAL_CHECKS.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
handoff=dict(status='complete',base=str(BASE),latest_clean_pdf=str(OUT/'paper_clean.pdf'),
    clean_tex=str(OUT/'paper_clean.tex'),this_edit_marked=str(OUT/'paper_this_edit_marked.pdf'),
    combined_marked=str(OUT/'paper_combined_marked.pdf'),
    combined_marked_baseline=str(OUT.parent/'revision_20260921_dr_modules_pipes/paper_clean.tex'),
    title_abstract_status='proposal_only_not_applied',proposal=str(OUT/'proposal/TITLE_ABSTRACT_ZH.md'),
    preview=str(OUT/'FIGURES_PREVIEW.pdf'),
    user_requested_edits=['one_sentence_zero_count_note','figure08_black_white_hatched_bgo_coloured_tes_copper',
                          'figure10_same_geometry_plus_nuclide_markers_no_heatmap'],
    production_simulations=False,validation=str(OUT/'validation/FINAL_CHECKS.json'),
    checksums={f:sha(OUT/f) for f in ['paper_clean.tex','paper_clean.pdf','paper_this_edit_marked.pdf','paper_combined_marked.pdf','paper_source.zip']})
(OUT/'MACHINE_HANDOFF.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:checks[k] for k in ['result','pdf_pages','paper_locations','text_changes','figure_fonts']},ensure_ascii=False,indent=2))
