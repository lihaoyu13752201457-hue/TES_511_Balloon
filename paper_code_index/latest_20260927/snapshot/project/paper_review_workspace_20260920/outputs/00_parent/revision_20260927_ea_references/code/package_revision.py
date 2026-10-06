from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path('/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920')
PARENT = ROOT / 'outputs/00_parent'
OUT = Path(__file__).resolve().parents[1]
BASE = PARENT / 'revision_20260927_source_sentence'
DELIVERY = PARENT / 'EA_submission_20260927'
sys.path.insert(0, str(PARENT / 'latest_manuscript_audit_20260920/_deps'))
import pymupdf as fitz

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

old = (BASE / 'paper_clean.tex').read_text()
new = (OUT / 'paper_clean.tex').read_text()
changes = json.loads((OUT / 'CHANGES.json').read_text())
restored = new
for change in reversed(changes):
    assert restored.count(change['new']) == 1
    restored = restored.replace(change['new'], change['old'], 1)
assert restored == old
assert len(changes) == 20

fig_changes = [c for c in changes if c['id'].startswith('figure_filename_')]
assert len(fig_changes) == 17
for c in fig_changes:
    assert sha(BASE / c['old'][1:-1]) == sha(OUT / c['new'][1:-1])
for name, digest in json.loads((OUT / 'validation/BASELINE_SHA256.json').read_text()).items():
    assert sha(BASE / name) == sha(OUT / 'baseline' / name) == digest

bibkeys = re.findall(r'\\bibitem\[[^\n]+\]\{([^}]+)\}', new)
cited = {k.strip() for group in re.findall(r'\\cite\w*(?:\[[^]]*\])*\{([^}]+)\}', new) for k in group.split(',')}
assert len(bibkeys) == 45 and len(set(bibkeys)) == 45
assert cited == set(bibkeys)
log = (OUT / 'paper_clean.log').read_text(errors='replace')
for forbidden in ('undefined', 'Overfull', 'Missing character', 'Fatal error'):
    assert forbidden not in log, forbidden
for key, year in [('Vavagiakis2017AlMnMagnetic',2018),('Vavagiakis2019AlMnFabrication',2020)]:
    assert f'\\bibitem[Vavagiakis et al.({year})]{{{key}}}' in new

doc = fitz.open(OUT / 'paper_clean.pdf')
assert len(doc) == 36
assert sum(len(list(p.annots() or [])) for p in doc) == 0
queries = [
    (2, 'Vavagiakis et al., 2020', 'Formal journal publication year updated from 2019 to 2020.'),
    (2, 'Vavagiakis et al., 2018', 'Formal journal publication year updated from 2017 to 2018.'),
    (33, 'PoS INTEGRAL2016 (2017) 075', 'COSI flight reference updated to the published proceedings, with DOI.'),
    (34, 'J. Low Temp. Phys. 193 (2018) 288–297', 'AlMn magnetic-sensitivity reference updated to its journal version and DOI.'),
    (34, 'J. Low Temp. Phys. 199 (2020) 408–415', 'AlMn fabrication reference updated to its formal journal volume, pages and year.'),
]
annotation_count = 0
for pno, text, explanation in queries:
    page = doc[pno]
    matches = page.search_for(text, quads=True)
    assert matches, text
    ann = page.add_highlight_annot(matches)
    ann.set_colors(stroke=(1.0, 0.83, 0.2))
    ann.set_info(title='This revision — 27 September 2026', content=explanation)
    ann.update()
    annotation_count += 1
doc.save(OUT / 'paper_this_edit_marked.pdf', garbage=4, deflate=True)
doc.close()
with fitz.open(OUT / 'paper_clean.pdf') as clean:
    for pno in (33,34):
        clean[pno].get_pixmap(matrix=fitz.Matrix(1.35,1.35)).save(OUT / 'validation' / f'page_{pno+1:02d}.png')

font_result = subprocess.run(['/usr/bin/pdffonts',str(OUT/'paper_clean.pdf')], capture_output=True, text=True, check=True)
(OUT/'validation/PDF_FONTS.txt').write_text(font_result.stdout)
font_flags = re.findall(r'\s(yes|no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$', font_result.stdout, re.M)
assert font_flags and all(flags[0]=='yes' for flags in font_flags)

sources = [OUT/'paper_clean.tex',OUT/'COMPILE_README.txt'] + sorted((OUT/'figures').glob('Fig*.pdf'))
with zipfile.ZipFile(OUT/'paper_source.zip','w',zipfile.ZIP_DEFLATED) as z:
    for path in sources:
        z.write(path,path.relative_to(OUT))
with zipfile.ZipFile(OUT/'paper_source.zip') as z:
    assert z.testzip() is None and len(z.namelist()) == 19
    for path in sources:
        assert z.read(str(path.relative_to(OUT))) == path.read_bytes()

assert not DELIVERY.exists(), 'Do not overwrite an existing submission directory'
DELIVERY.mkdir()
(DELIVERY/'figures').mkdir()
for path in [OUT/'paper_clean.pdf',OUT/'paper_source.zip'] + sources:
    shutil.copy2(path, DELIVERY/path.relative_to(OUT))

readme = '''# EA 首次投稿材料（2026-09-27）

本目录已落实：三条文献改用正式出版信息，17 个图件文件名按实际图号统一。图件内容、计算结果和其余正文未改。36 页，已重新编译检查。

## 文件用途

| 文件 | 用途 |
|---|---|
| `paper_clean.pdf` | 最新完整论文，含正文、全部图表与参考文献 |
| `paper_source.zip` | 完整可编译论文源包：TeX、17 幅图和编译说明；用于系统的 LaTeX/source files 上传入口 |
| `paper_clean.tex`、`figures/` | 与压缩包相同的展开版本，供修改或逐文件上传；不必与源包重复上传 |
| `COMPILE_README.txt` | 编译说明 |

论文源包不包含模拟或分析程序代码。中文说明文件供作者使用，不作为正文或补充材料上传。内部修改标注、历史备份与核查报告保留在工作区，未混入本目录。

## 首次投稿是否要交源代码

模拟和分析程序没有被 EA 的一般初投稿指南列为统一必交附件。论文的可编辑源文件另有要求：指南的 Text 部分允许初投 PDF，而 Source Files 部分要求提供可编辑文件。因此本目录同时备好 PDF 和 TeX/图件源包，建议按投稿系统栏目一并提供。

依据：[Experimental Astronomy 投稿指南](https://link.springer.com/journal/10686/submission-guidelines)，核对日期 2026-09-27。

## 尚需作者填写

作者单位与通讯邮箱，以及文末贡献确认、经费、利益冲突、数据和代码可用性仍按上一版保留待填。本轮仅按授权修改参考文献和图件文件名，未代填这些信息。AI 使用说明也沿用上一轮待作者确认的状态。

正式上传前请完成这些信息，并由共同作者确认最终稿。补填 TeX 后应重新编译 PDF，并同步更新源包。
'''
(DELIVERY/'README_ZH.md').write_text(readme)

bundle = PARENT/'EA_submission_20260927.zip'
assert not bundle.exists()
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
    for path in sorted(DELIVERY.rglob('*')):
        if path.is_file():
            z.write(path,path.relative_to(PARENT))
with zipfile.ZipFile(bundle) as z:
    assert z.testzip() is None

checks = {
    'status':'PASS','pages':36,'authorized_reference_updates':3,'figure_filename_updates':17,
    'only_authorized_tex_edits':True,'all_figure_bytes_unchanged':True,
    'baseline_files_preserved':True,'all_45_citations_resolved_and_used':True,
    'all_pdf_fonts_embedded':True,'source_archive_entries':19,'source_archive_verified':True,
    'clean_pdf_annotation_count':0,'marked_pdf_annotations':annotation_count,
    'remaining_placeholders':re.findall(r'\\projectfill\{([^}]+)\}',new),
    'scientific_results_changed':False,'submission_directory':str(DELIVERY),
    'submission_folder_matches_revision':all(sha(DELIVERY/p.relative_to(OUT))==sha(p) for p in [OUT/'paper_clean.pdf',OUT/'paper_source.zip']+sources),
    'compile_warnings':[line for line in log.splitlines() if 'Warning' in line],
}
assert checks['submission_folder_matches_revision']
(OUT/'validation/FINAL_CHECKS.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
(OUT/'validation/DELIVERY_SHA256.json').write_text(json.dumps({str(p.relative_to(DELIVERY)):sha(p) for p in sorted(DELIVERY.rglob('*')) if p.is_file()},indent=2)+'\n')
(OUT/'MACHINE_HANDOFF.json').write_text(json.dumps({
    'date':'2026-09-27','latest_directory':str(OUT),'baseline':str(BASE),
    'status':'complete','changes':'three published references and 17 figure filenames only',
    'submission_directory':str(DELIVERY),'submission_bundle':str(bundle),
    'scientific_inputs_changed':False,'original_files_preserved':True,
    'author_metadata_and_declarations_still_pending':True,
    'validation':'validation/FINAL_CHECKS.json'},ensure_ascii=False,indent=2)+'\n')
(OUT/'README_ZH.md').write_text('''# 本轮修改：EA 参考文献与图件命名

以 revision_20260927_source_sentence 为基准，仅落实用户同意的第 4、5 项。

- Vavagiakis 的磁敏感性论文更新为 J. Low Temp. Phys. 193, 288–297 (2018)，DOI 10.1007/s10909-018-1920-5。
- Vavagiakis 的薄膜制备论文更新为 J. Low Temp. Phys. 199, 408–415 (2020)，DOI 10.1007/s10909-019-02281-9。
- Kierans 的 COSI 飞行论文更新为 PoS INTEGRAL2016 (2017) 075，DOI 10.22323/1.285.0075。
- 17 幅图的文件名统一为 Fig1.pdf 至 Fig17.pdf，TeX 路径同步；图件字节内容未变。
- 书目作者—年份标签同步，正文两处引用显示为 2018、2020。

`paper_clean.pdf` 为最新稿，`paper_this_edit_marked.pdf` 标记本轮三条文献及两处年份变化；`CHANGES.json` 列出全部旧/新字符串。原版保存在 `baseline/` 与 `original_backup.zip`。

检查通过：36 页、45 条参考文献、17 幅图；无未定义引用或排版溢出；所有字体嵌入。完整源包逐项核验，独立投稿目录与本版内容一致。作者信息和声明的待填项保持原样。

新建材料目录：`../EA_submission_20260927/`；整体打包：`../EA_submission_20260927.zip`。

出版信息来源：

- https://link.springer.com/article/10.1007/s10909-018-1920-5
- https://link.springer.com/article/10.1007/s10909-019-02281-9
- https://pos.sissa.it/285/075/
''')
print(json.dumps({'checks':checks,'bundle_bytes':bundle.stat().st_size},ensure_ascii=False,indent=2))
