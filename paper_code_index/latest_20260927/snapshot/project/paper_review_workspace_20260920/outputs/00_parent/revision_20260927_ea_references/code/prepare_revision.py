from pathlib import Path
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import zipfile

ROOT = Path('/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920')
PARENT = ROOT / 'outputs/00_parent'
BASE = PARENT / 'revision_20260927_source_sentence'
OUT = Path(__file__).resolve().parents[1]
for folder in ('baseline', 'figures', 'validation'):
    (OUT / folder).mkdir(exist_ok=True)
assert not (OUT / 'paper_clean.tex').exists(), 'Do not overwrite an existing revision'
for name in ('paper_clean.tex', 'paper_clean.pdf', 'paper_source.zip'):
    shutil.copy2(BASE / name, OUT / 'baseline' / name)
with zipfile.ZipFile(OUT / 'original_backup.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for path in sorted((OUT / 'baseline').iterdir()):
        z.write(path, path.name)

old = (BASE / 'paper_clean.tex').read_text()
new = old
changes = []
updates = [
    ('Kierans2017', 'arXiv:1701.05558, 2017.',
     r'PoS INTEGRAL2016 (2017) 075, \url{https://doi.org/10.22323/1.285.0075}.',
     None, 'https://pos.sissa.it/285/075/'),
    ('Vavagiakis2017AlMnMagnetic', 'arXiv:1710.08456, 2017.',
     r'J. Low Temp. Phys. 193 (2018) 288--297, \url{https://doi.org/10.1007/s10909-018-1920-5}.',
     ('Vavagiakis et al.(2017)', 'Vavagiakis et al.(2018)'),
     'https://link.springer.com/article/10.1007/s10909-018-1920-5'),
    ('Vavagiakis2019AlMnFabrication', 'arXiv:1910.10199 (2019)',
     'J. Low Temp. Phys. 199 (2020) 408--415',
     ('Vavagiakis et al.(2019)', 'Vavagiakis et al.(2020)'),
     'https://link.springer.com/article/10.1007/s10909-019-02281-9'),
]
for key, a, b, label, url in updates:
    pattern = r'\\bibitem\[[^\n]+\]\{' + re.escape(key) + r'\}.*?(?=\n\\bibitem|\n\\end\{thebibliography\})'
    matches = list(re.finditer(pattern, new, re.S))
    assert len(matches) == 1, key
    oldblock = matches[0].group()
    assert oldblock.count(a) == 1
    newblock = oldblock.replace(a, b)
    if label:
        assert newblock.count(label[0]) == 1
        newblock = newblock.replace(*label)
    new = new.replace(oldblock, newblock, 1)
    changes.append({'id': key, 'old': oldblock, 'new': newblock,
                    'reason_zh': '采用已核实的正式出版信息；正文作者—年份引文随书目标签同步。',
                    'source': url})

mapping = json.loads((PARENT / 'ea_submission_check_20260927/CHECKS.json').read_text())['figures']
for item in mapping:
    src = item['current_file']
    dst = 'figures/' + item['suggested_file']
    assert new.count('{' + src + '}') == 1, src
    new = new.replace('{' + src + '}', '{' + dst + '}', 1)
    shutil.copy2(BASE / src, OUT / dst)
    changes.append({'id': 'figure_filename_' + str(item['figure']),
                    'old': '{' + src + '}', 'new': '{' + dst + '}',
                    'reason_zh': '图件文件名与论文实际图号对应；图件内容不变。'})

restored = new
for change in reversed(changes):
    assert restored.count(change['new']) == 1, change['id']
    restored = restored.replace(change['new'], change['old'], 1)
assert restored == old
(OUT / 'paper_clean.tex').write_text(new)
(OUT / 'CHANGES.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2) + '\n')
(OUT / 'validation/TEX_DIFF.patch').write_text(''.join(difflib.unified_diff(
    old.splitlines(True), new.splitlines(True), fromfile='previous/paper_clean.tex', tofile='current/paper_clean.tex')))
(OUT / 'COMPILE_README.txt').write_text(
    'Compile paper_clean.tex with pdfLaTeX three times, from the directory containing the TeX file.\n'
    'No shell escape, external system font, or bibliography processor is needed.\n'
    'Keep the figures subdirectory alongside paper_clean.tex; it contains Fig1.pdf through Fig17.pdf.\n'
    'All references are included in the TeX file.\n'
    'Author metadata and declarations marked TO BE FILLED still require author input.\n'
    'This package contains manuscript source files, not simulation or analysis program source code.\n')
baseline_hash = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (OUT / 'baseline').iterdir()}
(OUT / 'validation/BASELINE_SHA256.json').write_text(json.dumps(baseline_hash, indent=2) + '\n')
for i in range(1, 4):
    result = subprocess.run(['/usr/bin/pdflatex', '-interaction=nonstopmode', '-halt-on-error',
                             'paper_clean.tex'], cwd=OUT, text=True, capture_output=True)
    (OUT / 'validation' / f'compile_pass{i}.txt').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, f'Compilation failed, pass {i}'
print('Prepared and compiled revision: three references updated; 17 figure files renamed.')
