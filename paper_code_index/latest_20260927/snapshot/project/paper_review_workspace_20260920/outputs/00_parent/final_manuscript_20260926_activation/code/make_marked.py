from pathlib import Path
import ast, hashlib, json, re, subprocess
OUT=Path(__file__).resolve().parents[1];WORK=OUT.parents[2]
text=(OUT/'paper_clean.tex').read_text()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=OUT.parent/'final_manuscript_20260921/code/build_final.py';s=p.read_text()
exec('\n\n'.join(ast.get_source_segment(s,n) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name in ['bibliography','make_marked']),globals())
marks=[make_marked(OUT/'baseline/paper_clean.tex','paper_this_edit_marked','Activation correction and approved text revisions')]
p=OUT/'paper_this_edit_marked.tex';s=p.read_text()
s=re.sub(r'\\changedfinalfigure\[[^\]]+\]\{figures/(fig08|fig09).pdf\}',lambda m:r'\changedfinalfigure[width=\linewidth,height=0.72\textheight,keepaspectratio]{figures/'+m.group(1)+'.pdf}',s)
clean_tables=re.findall(r'\\begin\{tabular\}.*?\\end\{tabular\}',text,re.S)
marked_tables=list(re.finditer(r'\\begin\{tabular\}.*?\\end\{tabular\}',s,re.S))
assert len(clean_tables)==len(marked_tables)==8
updated=[]
for i,m in reversed(list(enumerate(marked_tables))):
    if r'\DIF' in m.group():
        # Display the revised table at its original size. Inline old/new numbers
        # nearly double its width; the original table is available in the backup.
        s=s[:m.start()]+'{\\color{blue}\n'+clean_tables[i]+'\n}'+s[m.end():]
        updated.append(i)
s=s.replace('Blue figure frames identify updated figures.',r'Blue figure frames identify updated figures.\\ Blue tables show revised values; original tables are retained in the backup.')
s=s.replace(r'final delayed rate of \DIFdelbegin',r'final delayed rate of \linebreak \DIFdelbegin')
p.write_text(s)
marks[0]['tables_displayed_as_blue_revised_values']=sorted(updated)
(OUT/'validation/ANNOTATION_BASELINES.json').write_text(json.dumps(marks,indent=2)+'\n')
for i in range(3):
    r=subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error','paper_this_edit_marked.tex'],cwd=OUT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (OUT/f'validation/marked_pass{i+1}.txt').write_text(r.stdout)
    print('Marked pass',i+1,'exit',r.returncode,flush=True)
    if r.returncode:print(r.stdout[-5000:]);raise SystemExit(r.returncode)
log=(OUT/'paper_this_edit_marked.log').read_text()
assert not re.search(r'Overfull|undefined|Missing character|LaTeX Error',log)
print('Marked PDF passed the layout and reference checks.')
