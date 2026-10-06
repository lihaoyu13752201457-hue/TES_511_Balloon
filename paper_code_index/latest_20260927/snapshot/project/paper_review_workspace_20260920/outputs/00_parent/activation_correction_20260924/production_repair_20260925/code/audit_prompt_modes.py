from pathlib import Path
import json,re,hashlib,collections
P=Path(__file__).resolve().parents[1];W=P.parents[3];PROJECT=W.parent
rebase=lambda p:Path(str(p).replace('/mnt/data','/media/ubuntu/903261CE3261BA3C'))
entries=[]
AA=W/'outputs/00_parent/AA_run_20260921_v1'
manifest=json.loads(Path('/media/ubuntu/903261CE3261BA3C/TES_Balloon_511_data/AA/aa_reproduce_A_20260921_v1/derived/merged/manifest.json').read_text())
used={re.match(r'job_\d+_(.+)\.npz',Path(p).name).group(1) for p in manifest['input_compacts']}
for kind in ['instant_full','instant_minimal']:
    plan=json.loads((AA/'bundles'/kind/'generated/job_plan.json').read_text())
    for j in plan['jobs']:
        if j['job_id'] in used:entries.append(dict(model='a',job_id=j['job_id'],source=str(rebase(j['source_path']))))
jobs=json.loads((PROJECT/'core_md/balloon511_ea_latex_drafts/meeting_revision_20260916/data/identity_b_jobs.json').read_text())
missing=[]
for j in jobs:
    if j['stream']!='prompt':continue
    sim=rebase(j['sim_path']);rc=sim.parents[4]/'receipts'/f'{j["job_id"]}.json'
    if not rc.exists():missing.append(dict(job_id=j['job_id'],receipt=str(rc)));continue
    r=json.loads(rc.read_text());entries.append(dict(model='b',job_id=j['job_id'],source=str(rebase(r['source_path']))))
for r in entries:
    p=Path(r['source'])
    if not p.exists():missing.append(r);continue
    raw=p.read_text();m=re.search(r'(?mi)^\s*DecayMode\s+(\S+)',raw);r['explicit_mode']=m[1] if m else None;r['effective_mode']=m[1] if m else 'Ignore';r['source_sha256']=hashlib.sha256(raw.encode()).hexdigest()
    assert r['effective_mode'].lower()=='ignore',r
source=Path('/home/ubuntu/MEGAlib_Install/megalib-main/src/cosima/src/MCParameterFile.cc');s=source.read_text();assert 'm_DecayMode = c_DecayModeIgnore' in s
out=dict(status='PASS' if not missing else 'PARTIAL_MISSING_SOURCE_CARDS',checked_by_model=dict(collections.Counter(r['model'] for r in entries if 'effective_mode' in r)),missing=missing,default_source=str(source),default_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),explanation='All checked prompt source cards use Ignore, which unconditionally suppresses radioactive decays and does not use the disputed delay index.',entries=entries)
(P/'data/prompt_mode_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'],out['checked_by_model'],'missing',len(missing))
