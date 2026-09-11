#!/usr/bin/env python3
"""Verify archived bytes, critical-code coverage, and optional paper compilation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

BASE = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--latex', action='store_true')
    args = p.parse_args()
    entries = [json.loads(s) for s in (BASE/'manifests/files.jsonl').read_text().splitlines()]
    unique = {e['archive_path']:e for e in entries}
    errors = []
    for name,e in unique.items():
        rel=Path(name)
        if rel.is_absolute() or '..' in rel.parts:
            errors.append('unsafe manifest path: '+name); continue
        f=BASE/rel
        if not f.is_file() or f.is_symlink():
            errors.append('missing file or symlink: '+name); continue
        raw=f.read_bytes()
        if len(raw)!=e['bytes'] or hashlib.sha256(raw).hexdigest()!=e['sha256']:
            errors.append('hash/size mismatch: '+name)
        if f.suffix.lower() in {'.sim','.npz','.npy','.root','.h5','.hdf5'} or len(raw)>25*2**20:
            errors.append('unexpected large data artifact: '+name)
    coverage=json.loads((BASE/'manifests/critical_code_coverage.json').read_text())
    if any(not e['present'] for e in coverage['files']):
        errors.append('missing critical program source')
    originals={e['original_path'] for e in entries}
    if any(e['original_path'] not in originals for e in coverage['files']):
        errors.append('critical coverage entry absent from inventory')
    tex=BASE/'paper/balloon511_ea_manuscript_en_20260831.tex'
    # Match the literal LaTeX command, not a regex escape.
    figures=re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',tex.read_text())
    if len(figures)!=16 or any(not (tex.parent/f).is_file() for f in figures):
        errors.append('paper figure inventory is incomplete')
    if errors:
        print(json.dumps({'status':'FAIL','errors':errors},indent=2)); raise SystemExit(1)
    result={'status':'PASS','logical_entries':len(entries),'physical_snapshot_files':len(unique),
            'program_files':sum(e['role']=='program_source' for e in unique.values()),
            'snapshot_bytes':sum(e['bytes'] for e in unique.values()),'paper_figures':len(figures),
            'critical_code_files':len(coverage['files'])}
    if args.latex:
        exe='/usr/bin/xelatex' if Path('/usr/bin/xelatex').exists() else shutil.which('xelatex')
        if not exe: raise RuntimeError('XeLaTeX is required for --latex')
        with tempfile.TemporaryDirectory(prefix='tes511-paper-compile-') as td:
            for _ in range(2):
                r=subprocess.run([exe,'-interaction=nonstopmode','-halt-on-error',f'-output-directory={td}',tex.name],
                                 cwd=tex.parent,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                if r.returncode:
                    print(r.stdout[-10000:]); raise SystemExit(r.returncode)
            pdf=Path(td)/tex.with_suffix('.pdf').name
            if not pdf.is_file(): raise RuntimeError('No compiled PDF')
            log=(Path(td)/tex.with_suffix('.log').name).read_text(errors='replace')
            if 'undefined references' in log or 'undefined citations' in log:
                raise RuntimeError('Unresolved LaTeX references or citations')
            result['latex']={'status':'PASS','passes':2,'compiled_bytes':pdf.stat().st_size,
                             'original_pdf_overwritten':False}
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
