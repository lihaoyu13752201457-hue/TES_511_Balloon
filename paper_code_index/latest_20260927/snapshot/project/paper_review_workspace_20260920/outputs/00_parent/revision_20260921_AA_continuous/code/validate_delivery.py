from common import *
import re
sys.path.insert(0,str(W/'outputs/00_parent/latest_manuscript_audit_20260920/_deps'));import pymupdf as fitz
base=O/'baseline/merged_before_this_edit.tex';old=base.read_text();new=(O/'paper_clean.tex').read_text();check=old
for r in read(O/'CHANGES.json'):
 assert check.count(r['old'])==1;check=check.replace(r['old'],r['new'])
assert check==new
assert '24 uniformly spaced azimuths' not in new
assert 'segment\njoining adjacent samples' not in new
assert read(O/'validation/prose_scope.json')['status']=='PASS'
changed=[7,9,11,12,13,14,15,16];prior=O.parent/'revision_20260921_compton_continuous'
figures=[]
for n in range(1,17):
 p=O/f'figures/fig{n:02}.pdf';same=sha(p)==sha(prior/f'figures/fig{n:02}.pdf');assert same==(n not in changed),(n,same)
 d=fitz.open(p);fonts=sorted({f[3] for page in d for f in page.get_fonts()});figures.append({'figure':n,'updated':not same,'fonts':fonts,'sha256':sha(p)})
 if n in changed:assert all('DejaVu' in f or 'STIXSizeOneSym-Regular' in f for f in fonts),(n,fonts)
keys=re.findall(r'\\bibitem\{([^}]+)\}',new);order=[]
for c in re.findall(r'\\cite\{([^}]+)\}',new):
 for k in c.split(','):
  if k not in order:order.append(k)
assert keys==order
pdfs={}
for stem in ['paper_clean','paper_this_edit_marked','paper_cumulative_marked']:
 log=(O/(stem+'.log')).read_text()
 for bad in ['undefined','multiply defined','multiply-defined','Overfull','Missing character','! LaTeX Error']:assert bad not in log,(stem,bad)
 d=fitz.open(O/(stem+'.pdf'));pdfs[stem]={'pages':len(d),'sha256':sha(O/(stem+'.pdf'))}
 if stem=='paper_clean':
  text='\n'.join(p.get_text() for p in d);assert '24 uniformly' not in text
  for tag,needle in [('cutflow','Under-stage analysis-window cut flow'),('transport','Particle-family transport statistics'),('sensitivity','20 d background counts')]:
   for i,p in enumerate(d):
    if needle in p.get_text():p.get_pixmap(matrix=fitz.Matrix(1.3,1.3)).save(O/f'validation/page_{tag}.png');pdfs[stem][tag+'_page']=i+1;break
 for p in d:assert len(p.get_text().strip())>0
result={'status':'PASS','unique_changes_reproduce_clean':True,'prose_scope':read(O/'validation/prose_scope.json'),'citations_in_first_occurrence_order':True,'figures':figures,'pdfs':pdfs,'numeric_geometry_validation':read(O/'validation/continuous_geometry.json'),'known_wording_inconsistencies_intentionally_retained':'WORDING_REVIEW_ZH.md'}
save(O/'validation/FINAL_CHECKS.json',result);print(json.dumps(pdfs,indent=2))
