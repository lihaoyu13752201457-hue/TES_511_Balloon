from pathlib import Path
import hashlib, json, re, shutil, zipfile
W=Path.cwd(); O=W/'outputs/00_parent/revision_20260927_pairs_blue'
S=Path('/home/ubuntu/.codex/attachments/dec5e0eb-17be-427e-94b5-1900db4334fc/已粘贴的文本.txt')
s=S.read_text(); source_hash=hashlib.sha256(S.read_bytes()).hexdigest()
assert not (O/'paper_pairs_blue.tex').exists()
(O/'baseline_pasted.tex').write_text(s)
institution='The project is being developed at the Institute of High Energy Physics, Chinese Academy of Sciences.'
design='The lens and detector layouts considered here represent one early design concept. The simulation workflow can also be applied to future configurations by updating the geometry and calculating the corresponding optical and detector responses.'
design_zh='本文采用的透镜与探测器布局属于一种早期设计构想。通过更新几何结构并计算相应的光学和探测器响应，这套模拟流程也可用于后续其他构型。'
project_start='The Positron Annihilation Imaging high-Resolution Spectrometer (PAIRS) is a balloon-borne telescope project aimed at pointed spectroscopy of Galactic 511-keV annihilation radiation.'
assert s.count(project_start)==1
anchor='mechanisms and guide optimization of the detection system.'
assert s.count(anchor)==1
semantic=s.replace(project_start,project_start+' '+institution,1).replace(anchor,anchor+'\n\n'+design,1)
macro=r'''% Mark PAIRS project introductions in blue; use \markpairsfalse to turn off.
\newif\ifmarkpairs
\markpairstrue
\newcommand{\pairsintro}[1]{\ifmarkpairs{\color{blue}#1}\else#1\fi}
'''
assert semantic.count('\\usepackage{xcolor}\n')==1
marked=semantic.replace('\\usepackage{xcolor}\n','\\usepackage{xcolor}\n'+macro,1)
# Mark the project introduction in the abstract, the two introduction paragraphs,
# the paper-scope sentence, and the new conceptual-design statement.
a=semantic.index('The Positron Annihilation Imaging high-Resolution Spectrometer (PAIRS) is a proposed')
b=semantic.index(' Focused signal photons',a)
abstract_intro=semantic[a:b]
a=semantic.index(project_start);b=semantic.index('\n\n',a)
project_para=semantic[a:b]
a=semantic.index('The lens and cryogenic focal-plane assembly are connected');b=semantic.index('\n\n',a)
system_para=semantic[a:b]
a=semantic.index('This paper introduces the PAIRS instrument concept');b=semantic.index(' We classify',a)
scope=semantic[a:b]
blocks=[('abstract_project_intro',abstract_intro),('introduction_project_and_institution',project_para),('introduction_system_overview',system_para),('introduction_paper_scope',scope),('early_design_and_workflow_reuse',design)]
for key,old in blocks:
    assert marked.count(old)==1,(key,marked.count(old))
    marked=marked.replace(old,'\\pairsintro{'+old+'}',1)
# Removing only the marking macros must exactly reproduce the two approved additions.
recovered=marked.replace(macro,'',1)
for _,block in blocks:
    wrapper='\\pairsintro{'+block+'}'
    assert recovered.count(wrapper)==1
    recovered=recovered.replace(wrapper,block,1)
assert recovered==semantic
assert semantic.replace(project_start+' '+institution,project_start,1).replace(anchor+'\n\n'+design,anchor,1)==s
assert re.findall(r'\$[^$]*\$',s)==re.findall(r'\$[^$]*\$',semantic)
assert re.findall(r'\\cite\w*\{[^}]+\}',s)==re.findall(r'\\cite\w*\{[^}]+\}',semantic)
assert re.findall(r'\\includegraphics[^\n]+',s)==re.findall(r'\\includegraphics[^\n]+',semantic)
(O/'paper_pairs_blue.tex').write_text(marked)
(O/'validation/compile_unmarked.tex').write_text(marked.replace('\\markpairstrue\n','\\markpairsfalse\n',1))
fig_base=W/'outputs/00_parent/EA_submission_20260927_data_availability'
figs=re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',s)
assets=[]
for rel in figs:
    source=fig_base/rel;dest=O/rel
    assert source.is_file(),source
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
    assert source.read_bytes()==dest.read_bytes()
    assets.append({'path':rel,'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
changes=[{'id':'PAIRS_INSTITUTION','old':project_start,'new':project_start+' '+institution,'reason_zh':'在引言首次项目介绍句之后补充高能所研制单位。'}, {'id':'EARLY_DESIGN_REUSE','old':anchor,'new':anchor+'\n\n'+design,'approved_zh':design_zh,'reason_zh':'采用用户确认的“一种早期设计构想”和“后续其他构型”。'}]
(O/'CHANGES.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
report={'status':'TEXT_CHECKS_PASS','input':str(S),'input_sha256':source_hash,'output':str(O/'paper_pairs_blue.tex'),'only_two_semantic_additions':True,'blue_macro':macro,'blue_blocks':[x[0] for x in blocks],'color_toggle':'\\markpairstrue / \\markpairsfalse','source_unchanged':hashlib.sha256(S.read_bytes()).hexdigest()==source_hash,'math_unchanged':True,'citations_unchanged':True,'graphics_references_unchanged':True,'assets':assets,'production_simulation_started':False}
(O/'validation/CHECKS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(O/'README_ZH.md').write_text('''# PAIRS介绍蓝色标注TeX

2026-09-27。以用户本轮粘贴的完整TeX为基线，新建文件，不覆盖粘贴源或此前论文。

加入两处已确认文字：

1. 引言首次介绍PAIRS之后补充中国科学院高能物理研究所研制单位。
2. 引言本文工作段之后补充早期设计构想与后续构型流程复用说明。

摘要的项目介绍、引言的两个项目介绍段、本文定位句及新增说明采用蓝色。导言区默认`\\markpairstrue`；改为`\\markpairsfalse`即可关闭全部PAIRS蓝色标注。其他既有颜色（如待填声明的红色）独立保留。

用户确认的中文说明：

> 本文采用的透镜与探测器布局属于一种早期设计构想。通过更新几何结构并计算相应的光学和探测器响应，这套模拟流程也可用于后续其他构型。

交付文件：`paper_pairs_blue.tex`；`paper_pairs_blue.pdf`为编译预览；`paper_source.zip`含TeX及17幅图，可直接编译。图件复制自本工作区2026-09-27现有完整源包，只用于保持相对路径完整，未重绘图件。

所有数值、公式、引用、作者顺序和其他正文采用用户本轮粘贴版本。未运行生产模拟。当前最新稿指针未变更。
''')
print(json.dumps({'output':str(O/'paper_pairs_blue.tex'),'blue_blocks':len(blocks),'text_checks':'PASS','figures':len(figs)},ensure_ascii=False))
