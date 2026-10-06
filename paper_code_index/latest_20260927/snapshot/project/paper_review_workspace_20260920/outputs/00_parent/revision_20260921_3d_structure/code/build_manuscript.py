from pathlib import Path
import re,json,hashlib
O=Path(__file__).resolve().parents[1];B=O.parent/'revision_20260921_unified_review'
old=(O/'baseline/merged_before_this_edit.tex').read_text()
pat=r'\\caption\{The Under-stage reference configuration\..*?\\label\{fig:mass_model\}'
m=re.search(pat,old,re.S);assert m
caption=r'''\caption{The Under-stage reference configuration.
(a) Orthographic cutaway showing the cold plates, TES array, Al cryostat and
thermal shields, BGO, and borated polyethylene (BPE). Front halves of the
shells and plates are removed to expose the interior. The dashed box locates (b).
(b) Enlarged six-layer TES assembly, Cu supports, heat sink and thermal links,
with the MXC plate cropped and local Al and Bi shields cut away.
(c) Optical entrance sequence; separations and foil thicknesses are enlarged.
Orange arrows indicate the focused 511 keV beam. Dense hole arrays in the
cold plates are omitted for clarity.}
\label{fig:mass_model}'''
clean=old[:m.start()]+caption+old[m.end():]
(O/'paper_clean.tex').write_text(clean)
(O/'CHANGES.json').write_text(json.dumps([dict(issue='USER_3D_STRUCTURE',meeting='R16.1–R16.3',
    old=m.group(),new=caption,occurrences=1,reason='Three-dimensional opaque cutaway, labelled cold-end enlargement, and explicit omission of dense cold-plate hole arrays.')],ensure_ascii=False,indent=2)+'\n')
s=(B/'code/build_marked.py').read_text()
s=s.replace("title='Cumulative revision' if cumulative else 'Unified manuscript revision'","title='Cumulative revision' if cumulative else 'Three-dimensional structure revision'")
s=s.replace('This edit only, relative to the signal-retention revision of 21 September 2026.','This edit only, relative to the unified manuscript of 21 September 2026.')
s=s.replace("s=s[:a]+'\\\\begingroup\\\\color{blue}\\n'+bib+'\\n\\\\endgroup'+s[b:]", "s=s[:a]+('\\\\begingroup\\\\color{blue}\\n'+bib+'\\n\\\\endgroup' if cumulative else bib)+s[b:]")
source="""    s=re.sub(r'\\\\includegraphics(\\[[^\\]]*\\])?\\{figures/fig(02|04|05|07|08|09|10|11|12|13|14|15|16)\\.pdf\\}',"""
assert source in s
s=s.replace(source,"""    changed_figures='02|04|05|07|08|09|10|11|12|13|14|15|16' if cumulative else '02'
    s=re.sub(r'\\\\includegraphics(\\[[^\\]]*\\])?\\{figures/fig('+changed_figures+r')\\.pdf\\}',""")
a=s.index('Changed tables are blue;');b=s.index('\\end{center}',a)
s=s[:a]+"Figure 2 was redrawn in this edit. Earlier revisions remain marked in the cumulative version.\\\\\n"+s[b:]
s=s.replace("s=s.replace(r'\\end{document}',appendix+'\\n'+r'\\end{document}')","s=s.replace(r'\\end{document}',(appendix if append_keys else '')+'\\n'+r'\\end{document}')")
(O/'code/build_marked.py').write_text(s)
print('Caption and annotation builder written; all other clean text unchanged.')
