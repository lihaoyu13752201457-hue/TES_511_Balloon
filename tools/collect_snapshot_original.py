#!/usr/bin/env python3
"""Create a source-only paper snapshot; no simulation payload is opened."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone

STAGE=Path('/tmp/tes511-paper-backup-stage-20260911')
MAIN=Path('/home/ubuntu/TES_511_Balloon')
CODE={'.py','.sh','.bash','.c','.cc','.cpp','.cxx','.h','.hh','.hpp','.hxx','.f','.f90','.f95','.m','.r','.jl','.js','.mjs','.ts','.cmake','.mk','.patch','.diff','.tcl'}
BUILD={'Makefile','CMakeLists.txt','Dockerfile','configure','requirements.txt','environment.yml','pyproject.toml','setup.cfg'}
CONFIG={'.geo','.setup','.det','.mac','.source','.cfg','.conf','.ini','.yaml','.yml','.toml','.xml','.spectrum','.raw-spectrum','.inc'}
TEXT={'.md','.rst','.txt','.csv','.json','.dat','.tex','.bib','.sty','.cls','.bst','.plus','.mins','.table','.tab','.html','.svg'}
SKIP_DIR={'.git','.codex','.agents','.claude','.tools','.cache','.venv','venv','node_modules','__pycache__','CMakeFiles','build','install','lib','bin','freecad-appimage','freecad-debs','backups','_recovery_logs','literature'}
RAW={'.gz','.bz2','.xz','.zip','.tar','.7z','.root','.sim','.npz','.npy','.h5','.hdf5','.fits','.fit','.parquet','.fcstd','.step','.stp','.obj','.o','.so','.a','.dll','.exe','.deb','.appimage','.pptx','.xlsx','.xdv','.log','.aux','.fls','.fdb_latexmk','.out','.pyc'}
SECRET={'.env','.pem','.key','.p12','.pfx'}

def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')

def git_state(root):
    def call(*args):
        r=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True)
        return r.stdout.strip() if r.returncode==0 else None
    return {'HEAD':call('rev-parse','HEAD'),'branch':call('branch','--show-current'),'tracked_changes':call('status','--porcelain','--untracked-files=no')}

def category(p,rel):
    s=p.suffix.lower(); name=p.name; size=p.stat().st_size
    if s in SECRET or name in {'.env','credentials','id_rsa','id_ed25519'}: return None,'credential_file'
    if s in CODE or name in BUILD: return 'program_source',None
    if s in RAW: return None,'simulation_payload_or_build_product'
    if 'runs' in rel.parts or 'run' in rel.parts:
        # Program sources were accepted above. Keep only compact run-level audit summaries.
        i = min(j for j,part in enumerate(rel.parts) if part in {'run','runs'})
        if len(rel.parts[i+1:]) <= 3 and s in {'.md','.json','.csv'} and size <= 128*1024:
            return 'small_input_or_summary',None
        return None,'generated_run_input_or_output'
    if any(part in {'receipts','job_catalogs','attempts','failed_attempts','isotope_stores'} for part in rel.parts):
        return None,'per_job_intermediate'
    if s in {'.svg','.html'}: return None,'generated_visual_not_final_paper_asset'
    if s=='.source' and size>128*1024: return None,'generated_activation_position_source_not_program_code'
    if s in CONFIG: return ('configuration',None) if size<=4*2**20 else (None,'large_generated_configuration')
    if s in TEXT:
        if s in {'.dat','.csv'} and ('.inc' in name or any(v in name.lower() for v in ['event_catalog','hit_catalog','phase_space','trajector','hit_records'])) and size>128*1024: return None,'event_level_dataset'
        if s=='.json' and size>512*1024: return None,'large_generated_json'
        if s in {'.csv','.dat'} and size>256*1024: return None,'large_scientific_table'
        if size>2*2**20: return None,'large_text_artifact'
        return ('document' if s in {'.md','.rst','.tex','.bib','.sty','.cls','.bst','.html','.svg'} else 'small_input_or_summary'),None
    if name.lower().startswith(('license','copying','readme')) and size<2**20:return 'document',None
    return None,'non_source_asset'

def walk(root):
    for d,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=sorted(x for x in dirs if x not in SKIP_DIR and not x.startswith('.') and not x.startswith('build') and not x.endswith(('-build','-install')))
        for name in sorted(files):
            if name.startswith('.'):continue
            p=Path(d)/name
            if p.is_symlink():
                # Preserve only explicitly collected file contents; never traverse a data mount.
                continue
            if p.is_file():yield p

def copy_hash(p,dst,role):
    data=p.read_bytes()
    if b'\0' in data[:8192] and role not in {'paper_pdf','paper_figure'}:
        raise RuntimeError(f'Unexpected binary classified as text: {p}')
    sha=hashlib.sha256(data).hexdigest()
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_bytes(data)
    dst.chmod(0o755 if os.access(p,os.X_OK) else 0o644)
    return sha,len(data)

def main():
    if STAGE.exists(): raise RuntimeError('Stage already exists')
    STAGE.mkdir()
    (STAGE/'manifests').mkdir()
    roots=[('main',MAIN,'main')]
    roots += [('worktree_'+p.parent.name,p,'overlay') for p in sorted(Path('/home/ubuntu/.codex/worktrees').glob('*/TES_511_Balloon'))]
    roots += [('opticsim',Path('/home/ubuntu/opticsim'),'independent'),('cross_check_laue',Path('/home/ubuntu/cross_check_laue'),'independent'),('neutron_fen',Path('/home/ubuntu/neutron_fen'),'supplemental'),('megalib',Path('/home/ubuntu/MEGAlib_Install/megalib-main'),'runtime_source')]
    entries=[]; excluded=[]; rootinfo=[]; base={}; counts=Counter(); external_refs=defaultdict(set)
    for rid,root,kind in roots:
        if not root.exists():continue
        seen=0; new=0; size=0
        for p in walk(root):
            rel=p.relative_to(root)
            if rid=='main' or rid.startswith('worktree_'):
                # Keep older helper code: current P67 explicitly imports old/code Step05.
                if rel.parts[0] in {'cube_satelite','PPT0821','review_annotations_20260823'}:continue
            if rid=='megalib' and rel.parts[0] not in {'src','config','resource','include','Makefile','configure','setup.sh','License.md','Readme.md','CodingConventions.md','Dockerfile'}:continue
            if rid=='megalib' and rel.parts[0]=='resource' and len(rel.parts)>1 and rel.parts[1] not in {'examples','patches','templates'}:continue
            role,reason=category(p,rel)
            if role is None:
                if reason!='non_source_asset':excluded.append({'root_id':rid,'relative_path':str(rel),'bytes':p.stat().st_size,'reason':reason})
                continue
            data=p.read_bytes()
            if b'\0' in data[:8192]:
                excluded.append({'root_id':rid,'relative_path':str(rel),'bytes':len(data),'reason':'binary_input_not_source'});continue
            sha=hashlib.sha256(data).hexdigest();seen+=1;size+=len(data)
            same=kind=='overlay' and str(rel) in base and base[str(rel)]['sha256']==sha
            if same:archive=base[str(rel)]['archive_path']
            else:
                archive=str(Path('sources')/rid/rel)
                dst=STAGE/archive;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data)
                dst.chmod(0o755 if os.access(p,os.X_OK) else 0o644);new+=1
            entry={'root_id':rid,'original_path':str(p),'relative_path':str(rel),'archive_path':archive,'sha256':sha,'bytes':len(data),'role':role,'shared_with_main':same}
            entries.append(entry)
            if rid=='main':base[str(rel)]=entry
            counts[role]+=1
            if role=='program_source':
                text=data.decode('utf-8',errors='replace')
                for m in re.finditer(r'/home/ubuntu/([A-Za-z0-9_.-]+)',text):external_refs[m.group(1)].add(str(p))
        rootinfo.append({'id':rid,'original_root':str(root),'kind':kind,'selected_files':seen,'new_archive_files':new,'logical_bytes':size,'git':git_state(root)})
        print(rid,seen,'files',new,'stored',round(size/2**20,2),'logical MiB',flush=True)
    # Keep final paper self-contained, without LaTeX intermediates.
    paper=Path('/home/ubuntu/paper_new');tex=paper/'balloon511_ea_manuscript_en_20260831.tex'
    assets=[tex,tex.with_suffix('.pdf')]
    for name in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',tex.read_text()):assets.append(paper/name)
    assert len(assets)==18
    for p in assets:
        rel=p.relative_to(paper);archive=str(Path('paper')/rel);role='document' if p.suffix=='.tex' else ('paper_pdf' if p==tex.with_suffix('.pdf') else 'paper_figure')
        sha,size=copy_hash(p,STAGE/archive,role)
        entries.append({'root_id':'final_paper','original_path':str(p),'relative_path':str(rel),'archive_path':archive,'sha256':sha,'bytes':size,'role':role,'shared_with_main':False})
    for p in [Path('/home/ubuntu/paper/balloon511_ea_draft_en_sg3_sh3_revision_20260821.tex')]:
        archive='paper/history/'+p.name;sha,size=copy_hash(p,STAGE/archive,'document')
        entries.append({'root_id':'earlier_paper','original_path':str(p),'relative_path':p.name,'archive_path':archive,'sha256':sha,'bytes':size,'role':'document','shared_with_main':False})
    (STAGE/'manifests/files.jsonl').write_text(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in entries))
    (STAGE/'manifests/excluded_files.jsonl').write_text(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in excluded))
    dump(STAGE/'manifests/source_roots.json',rootinfo)
    dump(STAGE/'manifests/external_project_references.json',{k:{'source_files':len(v),'examples':sorted(v)[:5]} for k,v in sorted(external_refs.items())})
    dump(STAGE/'manifests/collection_summary.json',{'created_utc':datetime.now(timezone.utc).isoformat(),'roles':counts,'logical_files':len(entries),'physical_files':len(set(e['archive_path'] for e in entries)),'physical_bytes':sum(p.stat().st_size for p in STAGE.rglob('*') if p.is_file()),'excluded_files':len(excluded),'excluded_reasons':Counter(x['reason'] for x in excluded),'simulation_payloads_opened':0,'excluded_bytes_by_reason':{reason:sum(e['bytes'] for e in excluded if e['reason']==reason) for reason in sorted(set(e['reason'] for e in excluded))},'source_policy':'All program sources in collected roots, with main/worktree overlays deduplicated by path+SHA256. Small configurations and summaries retained; large generated sampling cards/data excluded.'})
    print('STAGE',STAGE,flush=True)

if __name__=='__main__':main()
