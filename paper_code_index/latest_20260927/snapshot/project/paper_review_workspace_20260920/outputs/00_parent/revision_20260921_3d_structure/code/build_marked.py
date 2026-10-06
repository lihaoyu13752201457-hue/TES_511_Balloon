from pathlib import Path
import re,json,subprocess
O=Path(__file__).resolve().parents[1];W=O.parents[2]
vendor=W/'inputs/latest/code/vendor/latexdiff'
original=W/'inputs/latest/original/balloon511_ea_manuscript_en_20260831.tex'
clean=(O/'paper_clean.tex').read_text()
def tables(s):
    return {re.search(r'\\label\{([^}]+)\}',m.group())[1]:m.group() for m in re.finditer(r'\\begin\{table\}.*?\\end\{table\}',s,re.S)}
newtables=tables(clean)
currentlabels=set(re.findall(r'\\label\{([^}]+)\}',clean))

def build(oldpath,stem,cumulative):
    old=oldpath.read_text();oldtables=tables(old)
    r=subprocess.run(['perl',str(vendor),'--type=UNDERLINE','--floattype=FLOATSAFE','--graphics-markup=both',str(oldpath),'paper_clean.tex'],cwd=O,text=True,capture_output=True,check=True)
    (O/'validation'/f'{stem}_latexdiff_stderr.txt').write_text(r.stderr)
    s=r.stdout
    changed=newtables if cumulative else {k:v for k,v in newtables.items() if v!=oldtables.get(k)}
    for lab,t in changed.items():
        label=re.search(r'(?m)^[^%\n]*\\label\{'+re.escape(lab)+r'\}',s);assert label,lab
        begins=list(re.finditer(r'(?m)^[^%\n]*\\begin\{table\}',s[:label.end()]));a=begins[-1].start()+begins[-1].group().index(r'\begin{table}')
        end=re.search(r'(?m)^[^%\n]*\\end\{table\}',s[label.end():]);assert end
        b=label.end()+end.end()
        blue=t.replace(r'\centering',r'\color{blue}\captionsetup{font+={color=blue},labelfont+={color=blue}}'+'\n'+r'\centering',1)
        s=s[:a]+r'\begingroup'+'\n'+blue+'\n'+r'\endgroup'+s[b:]
    oldkeys=re.findall(r'\\bibitem\{([^}]+)\}',old);newkeys=set(re.findall(r'\\bibitem\{([^}]+)\}',clean));depth=0;parts=[];last=0
    for m in re.finditer(r'\\DIFdelbegin(?:FL)?|\\DIFdelend(?:FL)?|\\bibitem\{([^}]+)\}',s):
        parts.append(s[last:m.start()]);token=m.group()
        if token.startswith('\\DIFdelbegin'):depth+=1
        elif token.startswith('\\DIFdelend'):depth=max(0,depth-1)
        elif m.group(1) and depth:
            k=m.group(1);num=oldkeys.index(k)+1;label=('deleted:'+k) if k in newkeys else k
            token=r'\bibitem[{\color{red}old '+str(num)+'}]{'+label+'}'
        parts.append(token);last=m.end()
    s=''.join(parts)+s[last:]
    # Historical references removed from the current paper are printed as such;
    # do not resurrect labels or invent current equation numbers in deletions.
    missing=set(re.findall(r'\\(?:ref|eqref)\{([^}]+)\}',s))-set(re.findall(r'\\label\{([^}]+)\}',s))
    assert not missing & currentlabels
    for key in missing:
        s=s.replace(r'\eqref{'+key+'}','(former definition)').replace(r'\ref{'+key+'}','[former reference]')
    bib=clean[clean.index('\\begin{thebibliography}'):clean.index('\\end{thebibliography}')+len('\\end{thebibliography}')]
    a=s.index('\\begin{thebibliography}');b=s.index('\\end{thebibliography}',a)+len('\\end{thebibliography}')
    s=s[:a]+('\\begingroup\\color{blue}\n'+bib+'\n\\endgroup' if cumulative else bib)+s[b:]
    def historical_citation(m):
        keys=m.group(1).split(',');valid=[k for k in keys if k in newkeys]
        gone=[k for k in keys if k not in newkeys]
        if not gone:return m.group()
        return (r'\cite{'+','.join(valid)+'}' if valid else '')+' [previous reference '+', '.join(str(oldkeys.index(k)+1) for k in gone)+']'
    s=re.sub(r'\\cite\{([^}]+)\}',historical_citation,s)
    changed_figures='02|04|05|07|08|09|10|11|12|13|14|15|16' if cumulative else '02'
    s=re.sub(r'\\includegraphics(\[[^\]]*\])?\{figures/fig('+changed_figures+r')\.pdf\}',
             lambda m:r'\DIFaddincludegraphics'+(m.group(1) or '')+'{figures/fig'+m.group(2)+'.pdf}',s)
    title='Cumulative revision' if cumulative else 'Three-dimensional structure revision'
    subtitle='Changes from the original manuscript of 31 August 2026.' if cumulative else 'This edit only, relative to the unified manuscript of 21 September 2026.'
    legend=r'''\begin{document}
\begin{center}
{\large\bfseries '''+title+r''' --- 21 September 2026}\\[0.35em]
'''+subtitle+r'''\\
{\color{blue}Blue underlining: additions or replacement text.}\\
{\color{red}Red strike-through: deleted text.}\\
Figure 2 was redrawn in this edit. Earlier revisions remain marked in the cumulative version.\\
\end{center}
\vspace{0.6em}
'''
    extra=r'''
\renewcommand{\DIFaddincludegraphics}[2][]{{\setlength{\linewidth}{0.98\linewidth}\setlength{\fboxsep}{1pt}\color{blue}\fbox{\DIFOincludegraphics[#1]{#2}}}}
\renewcommand{\DIFdelincludegraphics}[2][]{{\color{red}\fbox{\small Previous figure replaced; see the source manuscript.}}}
\renewcommand{\DIFaddbegin}{\DIFOaddbegin\let\includegraphics\DIFaddincludegraphics\ifhmode\penalty0\hskip0pt\relax\fi}
\pdfstringdefDisableCommands{\def\DIFaddbegin{}\def\DIFaddend{}\def\DIFdelbegin{}\def\DIFdelend{}}
\emergencystretch=3em
'''
    s=s.replace(r'\begin{document}',extra+'\n'+legend,1)
    appendix='\n'+r'\clearpage\section*{Previous tables retained for comparison}'+'\n'
    append_keys=list(oldtables) if cumulative else [k for k in oldtables if k in changed]
    for number,(lab,t) in enumerate(oldtables.items(),1):
        if lab not in append_keys:continue
        t=re.sub(r'\\begin\{table\}(?:\[[^]]*\])?',lambda m:r'\begin{table}[p]',t)
        t=t.replace(r'\caption{',r'\caption*{Previous table '+str(number)+'. ',1)
        t=t.replace('\\label{'+lab+'}','\\label{previous:'+lab+'}')
        for key in set(re.findall(r'\\(?:ref|eqref)\{([^}]+)\}',t))-currentlabels:
            t=t.replace(r'\eqref{'+key+'}','(former definition)').replace(r'\ref{'+key+'}','[former reference]')
        t=t.replace(r'\centering',r'\color{red}\captionsetup{font+={color=red},labelfont+={color=red}}'+'\n'+r'\centering',1)
        appendix+='\n'+r'\begingroup\color{red}'+'\n'+t+'\n'+r'\endgroup\clearpage'+'\n'
    s=s.replace(r'\end{document}',(appendix if append_keys else '')+'\n'+r'\end{document}')
    s=s.replace(r'\begin{figure}[H]',r'\begin{figure}[!htbp]')
    # Old and new long configuration names coexist only in this marked equation.
    # Fit the annotation without changing the clean equation or its values.
    if cumulative:
        s=re.sub(r'\\begin\{equation\}.*?\\end\{equation\}',
                 lambda m:r'\begingroup\small'+'\n'+m.group()+'\n'+r'\endgroup'
                 if r'\label{eq:fmin_ratio_decomposition}' in m.group() else m.group(),s,flags=re.S)
    (O/(stem+'.tex')).write_text(s)
    return {'stem':stem,'baseline':str(oldpath),'blue_tables':list(changed),'red_previous_tables':len(append_keys),'removed_historical_reference_labels':sorted(missing)}

result=[build(O/'baseline/merged_before_this_edit.tex','paper_this_edit_marked',False),build(original,'paper_cumulative_marked',True)]
(O/'validation/annotation_policy.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
