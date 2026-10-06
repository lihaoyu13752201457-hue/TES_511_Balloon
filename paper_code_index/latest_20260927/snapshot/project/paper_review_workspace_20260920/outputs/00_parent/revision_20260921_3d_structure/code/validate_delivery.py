from pathlib import Path
import hashlib,json,re,sys
O=Path(__file__).resolve().parents[1];B=O.parent/'revision_20260921_unified_review'
sys.path.insert(0,str(O.parent/'latest_manuscript_audit_20260920/_deps'))
import pymupdf as fitz
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
clean=(O/'paper_clean.tex').read_text();base=(B/'paper_clean.tex').read_text()
c=json.loads((O/'CHANGES.json').read_text());assert len(c)==1
assert base.count(c[0]['old'])==1 and base.replace(c[0]['old'],c[0]['new'])==clean
assert re.findall(r'\\begin\{table\}.*?\\end\{table\}',base,re.S)==re.findall(r'\\begin\{table\}.*?\\end\{table\}',clean,re.S)
unchanged={}
for n in range(1,17):
    if n==2:continue
    p=f'figures/fig{n:02}.pdf';assert sha(O/p)==sha(B/p);unchanged[p]=sha(O/p)
geo=json.loads((O/'validation/geometry_manifest.json').read_text())
assert sha(geo['geometry_source'])==geo['geometry_sha256']
assert geo['single_MXC'] and not geo['plastic_drawn']
assert len(geo['visible_plates'])==5 and geo['individual_pixels_in_detail']==2256
source=Path(geo['geometry_source']).read_text()
holes={n:len(re.findall(r'^SE3_HOLE_\S+\.Mother '+re.escape(n)+r'$',source,re.M)) for n in geo['visible_plates']}
assert holes['ColdPlate_MXC_50mK_SD_anchor']>0
figdoc=fitz.open(O/'figures/fig02.pdf');fs=[s for b in figdoc[0].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans']]
fonts=sorted({s['font'] for s in fs});assert all('DejaVu' in f for f in fonts)
assert 'Dense hole arrays in the cold plates are omitted for clarity.' in figdoc[0].get_text()
assert len(figdoc[0].get_images())==0
docs=[]
for stem in ['paper_clean','paper_this_edit_marked','paper_cumulative_marked']:
    log=(O/(stem+'.log')).read_text(errors='replace')
    issues=[s for s in log.splitlines() if any(w in s for w in ['Overfull','undefined','Missing character','LaTeX Error'])]
    assert not issues,(stem,issues)
    d=fitz.open(O/(stem+'.pdf'))
    picks=[i for i,p in enumerate(d) if re.search(r'Figure\s+2\s*:',p.get_text())];assert len(picks)==1
    i=picks[0];d[i].get_pixmap(matrix=fitz.Matrix(1.45,1.45)).save(O/'validation'/(stem+'_figure2_page.png'))
    ds=[s for b in d[i].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans']]
    sizes=[s['size'] for s in ds if s['font'] in fonts]
    docs.append(dict(stem=stem,pages=len(d),figure2_page=i+1,pdf_sha256=sha(O/(stem+'.pdf')),
                     figure_font_size_pt=[round(min(sizes),2),round(max(sizes),2)],compile_problems=issues))
result=dict(status='PASS',only_clean_text_change='Figure 2 caption',only_figure_change=2,
            all_tables_and_science_text_unchanged=True,unchanged_figures=unchanged,
            source_geometry_unchanged=True,source_geometry_sha256=geo['geometry_sha256'],
            physical_holes_retained_by_plate=holes,displayed_holes=0,single_MXC=True,plastic_drawn=False,
            figure_is_vector=True,figure_fonts=fonts,documents=docs,visual_review='pending')
(O/'validation/FINAL_CHECKS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['status','documents','physical_holes_retained_by_plate']},ensure_ascii=False,indent=2))
