from pathlib import Path
import sys, re, json, shutil, hashlib, subprocess, concurrent.futures, ast
OUT=Path(__file__).resolve().parents[1]
WORK=OUT.parents[2]
BASE=OUT.parent/'final_manuscript_20260921'
old=(BASE/'paper_clean.tex').read_text();text=old;changes=[]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def replace(cid,before,after,reason):
    global text
    assert text.count(before)==1,cid
    changes.append(dict(id=cid,old=before,new=after,reason_zh=reason,
                        baseline_line=old[:old.index(before)].count('\n')+1))
    text=text.replace(before,after,1)

before='and delayed activation falls from $0.1724\\cps$ to $3.219\\times10^{-2}\\cps$.'
replace('P01',before,before+' A zero selected count in a finite Monte Carlo sample does not establish a zero physical background rate.',
        '按用户要求，仅补一句说明有限蒙特卡罗样本的零选中计数不等于物理本底严格为零。')
replace('P02','cold-service opening. L0--L5 identify the six TES layers.',
        'cold-service opening.','新图8不再使用L0–L5标签，删除失去对应的层号说明。')
replace('P03',r'''Figure~\ref{fig:optimized_shield_background} compares the two cold-end
structures in the same instrument coordinates and at the same scale. The
detector-neighbourhood panels emphasize the six-layer TES, layer-by-layer copper
thermal supports, bent copper cold finger, rear cold port, and surrounding active BGO.''',
        r'''Figure~\ref{fig:optimized_shield_background} compares the two configurations
at the same scale, showing the cold plates, TES, copper thermal connections,
and active BGO.''',
        '图8由四格全局/局部图改为两格同尺度结构图，仅同步对应说明。')
replace('P04',r'''\caption{Structural comparison of Under-stage (left) and Lateral-chimney (right). The upper panels show the cold stages and focal-plane locations on a common coordinate scale; the lower panels enlarge the two detector regions at the same physical scale. Colour identifies the TES, copper thermal links, BGO, and the aluminium envelopes. In Lateral-chimney, the envelopes are labelled by function: the high-purity aluminium magnetic shield, three intermediate cold-stage shells, and outer mechanical jacket. The focused beam, MXC cold plate, and bent copper cold finger show the optical and thermal connections.}''',
        r'''\caption{Functional $x'$--$z'$ views of (a) Under-stage and (b) Lateral-chimney at the same physical scale. Copper structures and the TES are shown in colour; BGO is diagonally hatched, and the remaining structures are shown in grey. Arrows indicate the focused beam. Dense holes in the cold plates and small service details are omitted.}''',
        '图8采用Pro的上下对照思路，补上冷盘并简化标注；同步图注和省略说明。')
replace('P05',r'''\caption{Parent-nuclide production sites for selected day-15 delayed events in Under-stage (left) and Lateral-chimney (right). The upper panels show the cryostat region and the lower panels enlarge the TES neighbourhood at a common scale. Structural outlines locate the cold plates, TES, and shields; colours and symbols identify parent nuclides. The five nuclides with the largest combined selected day-15 rate across both configurations have individual symbols, and the remaining parents are grouped as Other. The panels share one nuclide legend. Symbols have a fixed display size; coincident projected sites within each legend category are shown once. Event selection uses the $[510.50,511.50)\keV$ analysis energy window, active veto, and final Compton selection.}''',
        r'''\caption{Parent-nuclide production sites for selected day-15 delayed events in (a) Under-stage and (b) Lateral-chimney, overlaid on the structures of Figure~\ref{fig:optimized_shield_background} at the same scale. Symbols identify the five parent nuclides with the largest combined selected rate across both configurations; the remaining nuclides are grouped as Other. Symbol size is fixed, and coincident projected sites within a category are shown once. All events have passed the analysis energy window, active veto, and Compton selection.}''',
        '按用户最新要求，图10直接在图8的相同结构底图上叠加核素符号，取消热图、色标与下方部件率面板；同步图注。')
replace('P06',r'\includegraphics[width=\linewidth]{figures/fig08.pdf}',
        r'\includegraphics[width=\linewidth,height=0.85\textheight,keepaspectratio]{figures/fig08.pdf}',
        '将较高的两格图按版心排入整页，保持横纵比例。')
replace('P07',r'\includegraphics[width=\linewidth]{figures/fig09.pdf}',
        r'\includegraphics[width=\linewidth,height=0.85\textheight,keepaspectratio]{figures/fig09.pdf}',
        '图10与图8保持相同版面比例。')

shutil.copy2(BASE/'paper_clean.tex',OUT/'baseline/paper_before.tex')
pointer=OUT.parent/'LATEST_MANUSCRIPT_ZH.md'
if not (OUT/'baseline/LATEST_MANUSCRIPT_before.md').exists():shutil.copy2(pointer,OUT/'baseline/LATEST_MANUSCRIPT_before.md')
for p in (BASE/'figures').glob('*.pdf'):shutil.copy2(p,OUT/'figures'/p.name)
shutil.copy2(OUT/'figures/Figure08.pdf',OUT/'figures/fig08.pdf')
shutil.copy2(OUT/'figures/Figure10.pdf',OUT/'figures/fig09.pdf')
(OUT/'paper_clean.tex').write_text(text)
(OUT/'CHANGES.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
(OUT/'FIGURE_CHANGES.json').write_text(json.dumps([
 dict(figure_number=n,file=f,old_sha256=sha(BASE/'figures'/f),new_sha256=sha(OUT/'figures'/f))
 for n,f in [(8,'fig08.pdf'),(10,'fig09.pdf')]],ensure_ascii=False,indent=2)+'\n')

vendor=WORK/'inputs/latest/code/vendor/latexdiff'
def marked(base,stem,title):
    proc=subprocess.run(['perl',str(vendor),'--type=UNDERLINE','--floattype=FLOATSAFE',
                         '--graphics-markup=none',str(base),str(OUT/'paper_clean.tex')],
                        capture_output=True,text=True,check=True)
    m=proc.stdout
    (OUT/'validation'/f'{stem}_diff_stderr.txt').write_text(proc.stderr)
    # Preserve the unchanged current bibliography; mark only replaced prose.
    current_bib=re.search(r'\\begin\{thebibliography\}.*?\\end\{thebibliography\}',text,re.S).group()
    m=re.sub(r'\\begin\{thebibliography\}.*?\\end\{thebibliography\}',lambda q:current_bib,m,flags=re.S)
    m=m.replace(r'\begin{document}',r'''
\newcommand{\updatedfigure}[2][]{{\setlength{\linewidth}{0.98\linewidth}\setlength{\fboxsep}{1pt}\color{blue}\fbox{\includegraphics[#1]{#2}}}}
\begin{document}
\begin{center}\textbf{'''+title+r'''}\\
Blue underlining: additions. Red strike-through: deletions.\\
Blue frames identify updated figures.\end{center}
''',1)
    for f in ['fig08.pdf','fig09.pdf']:
        m=re.sub(r'\\includegraphics\[[^\]]+\]\{figures/'+re.escape(f)+r'\}',
                 lambda q:r'\updatedfigure[width=\linewidth,height=0.72\textheight,keepaspectratio]{figures/'+f+'}',m)
    (OUT/(stem+'.tex')).write_text(m)
marked(BASE/'paper_clean.tex','paper_this_edit_marked','Figure 8/10 and finite-sample clarification')

# Keep the same common baseline as the previous combined marked manuscript.
# Reuse the existing bibliography-aware diff helper without executing its edits.
previous_builder=(BASE/'code/build_final.py').read_text()
functions=[ast.get_source_segment(previous_builder,n) for n in ast.parse(previous_builder).body
           if isinstance(n,ast.FunctionDef) and n.name in ['bibliography','make_marked']]
exec('\n\n'.join(functions).replace("glob('*.pdf')", "glob('fig*.pdf')"),globals())
common=OUT.parent/'revision_20260921_dr_modules_pipes/paper_clean.tex'
make_marked(common,'paper_combined_marked','Four-part revisions and approved figure updates')
path=OUT/'paper_combined_marked.tex';s=path.read_text()
s=re.sub(r'\\changedfinalfigure\[[^\]]+\]\{figures/(fig08|fig09).pdf\}',
         lambda q:r'\changedfinalfigure[width=\linewidth,height=0.72\textheight,keepaspectratio]{figures/'+q.group(1)+'.pdf}',s)
path.write_text(s)

def compile(stem):
    for i in range(3):
        with (OUT/'validation'/f'{stem}_pass{i+1}.txt').open('w') as f:
            subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error',stem+'.tex'],
                           cwd=OUT,stdout=f,stderr=subprocess.STDOUT,check=True)
    return stem
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    for stem in pool.map(compile,['paper_clean','paper_this_edit_marked','paper_combined_marked']):print('Compiled',stem,flush=True)
