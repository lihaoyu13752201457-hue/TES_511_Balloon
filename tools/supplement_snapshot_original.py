from pathlib import Path
import hashlib
import importlib.util
import json
import os
from collections import Counter

BASE=Path('/tmp/tes511-paper-backup-stage-20260911')
spec=importlib.util.spec_from_file_location('collector','/tmp/collect_tes511_paper_backup_20260911.py')
collector=importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)
rows=[json.loads(x) for x in (BASE/'manifests/files.jsonl').read_text().splitlines()]
roots=json.loads((BASE/'manifests/source_roots.json').read_text())
known={r['original_path'] for r in rows}
added=[]

def add(root_id, root, p, role):
    if str(p) in known: return
    raw=p.read_bytes()
    if b'\0' in raw[:8192]: raise RuntimeError(f'Unexpected binary input: {p}')
    if len(raw)>8*2**20: raise RuntimeError(f'Unexpected large supplemental source/input: {p}')
    rel=p.relative_to(root);archive=str(Path('sources')/root_id/rel)
    dst=BASE/archive;dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_bytes(raw);dst.chmod(0o755 if os.access(p,os.X_OK) else 0o644)
    e={'root_id':root_id,'original_path':str(p),'relative_path':str(rel),'archive_path':archive,
       'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'role':role,'shared_with_main':False}
    rows.append(e);known.add(str(p));added.append(e)

legacy=Path('/home/ubuntu/codex_tes_511_sim')
for p in collector.walk(legacy):
    rel=p.relative_to(legacy)
    if p.suffix.lower() in collector.CODE or p.name in collector.BUILD:
        add('codex_tes_511_sim',legacy,p,'program_source')
    elif 'expacs_parma' in rel.parts and ('input' in rel.parts or p.name=='Readme.txt') and p.suffix.lower() not in {'.zip','.gz'}:
        # PARMA reads these coefficient tables, including .out files, as INPUT.
        add('codex_tes_511_sim',legacy,p,'configuration')

roots.append({'id':'codex_tes_511_sim','original_root':str(legacy),'kind':'upstream_source',
              'git':collector.git_state(legacy),'selection_note':'All program sources; EXPACS/PARMA input coefficient tables and upstream readmes.'})

megalib=Path('/home/ubuntu/MEGAlib_Install/megalib-main')
extra=[*sorted((megalib/'bin').glob('*.sh')),
       megalib/'external/geant4_v10.02.p03/bin/geant4.sh',
       megalib/'external/geant4_v10.02.p03/bin/geant4-config']
for p in extra:
    if p.is_file():add('megalib',megalib,p,'program_source')

# Less common script/config extensions, missed by the first generic selection.
for info in roots:
    if info['id'] in {'megalib','codex_tes_511_sim'}:continue
    root=Path(info['original_root'])
    for p in collector.walk(root):
        if p.suffix.lower() in {'.awk','.pl','.sed','.fcmacro','.gnuplot','.gp','.inp','.g4mac'}:
            if p.stat().st_size<=4*2**20:
                role='configuration' if p.suffix.lower() in {'.inp','.g4mac'} else 'program_source'
                add(info['id'],root,p,role)

for info in roots:
    group=[e for e in rows if e['root_id']==info['id']]
    info.update(selected_files=len(group),new_archive_files=sum(not e['shared_with_main'] for e in group),logical_bytes=sum(e['bytes'] for e in group))
(BASE/'manifests/files.jsonl').write_text(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in rows))
(BASE/'manifests/source_roots.json').write_text(json.dumps(roots,indent=2,ensure_ascii=False)+'\n')
(BASE/'manifests/supplemental_sources.json').write_text(json.dumps({'files':added,'bytes':sum(e['bytes'] for e in added)},indent=2,ensure_ascii=False)+'\n')
summary=json.loads((BASE/'manifests/collection_summary.json').read_text())
summary.update(logical_files=len(rows),physical_files=len(set(e['archive_path'] for e in rows)),
               physical_bytes=sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file()),
               roles=Counter(e['role'] for e in rows),supplemental_files=len(added))
(BASE/'manifests/collection_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
audit=json.loads((BASE/'manifests/absolute_source_dependency_audit.json').read_text())
audit['resolved_missing_refs']=[p for p in audit['absolute_source_refs_missing_from_snapshot'] if p in known]
audit['absolute_source_refs_missing_from_snapshot']=[p for p in audit['absolute_source_refs_missing_from_snapshot'] if p not in known]
(BASE/'manifests/absolute_source_dependency_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps({'added_files':len(added),'added_MiB':sum(e['bytes'] for e in added)/2**20,
                  'absolute_missing':audit['absolute_source_refs_missing_from_snapshot']},indent=2))
