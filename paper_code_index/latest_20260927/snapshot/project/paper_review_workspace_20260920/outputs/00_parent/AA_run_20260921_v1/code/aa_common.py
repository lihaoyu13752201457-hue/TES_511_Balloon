"""AA adapters around the retained canonical executor; no copied executor."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import hashlib, importlib.util, json, os, re, time
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
WORKSPACE=ROOT.parents[2]
PROJECT=WORKSPACE.parent
ASSESS=ROOT.parent/'AA_simulation_assessment_20260921'
G=PROJECT/'engineering/geometry_optimization_20260815'
AA=PROJECT/'engineering/mass_model_AA_20260921'
EXEC=Path('/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute')
DISK=Path('/media/ubuntu/903261CE3261BA3C')
DATA=DISK/'TES_Balloon_511_data/AA/aa_reproduce_A_20260921_v1'
SIGNAL=WORKSPACE/'outputs/02_sources_response_compton/corrected_optics_signal_20260920'
SETUP=AA/'geometry/Mass_model_AA.geo.setup'
MINIMAL_SETUP=ROOT/'geometry/Mass_model_AA_MINIMAL.geo.setup'
FAMILIES=('gamma','n','eminus','eplus','p','alpha','muminus','muplus')
BGO=('BGO_S3C_FullWrap_SideShell_WindowCut_40mm','BGO_S3D_O8_FullWrap_BottomCap_30mm','AA_BGO_TopCap_12Ports_10mm')
RESERVE=150_000_000_000
DEADLINE=1789924825+8*3600
START=1789924825
GiB=2**30
TOKEN='engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/'
FORBIDDEN='cosima_spectra_dp_2602units'
sys.path.insert(0,str(EXEC))
import common as C
def loadmod(name,path):
    spec=importlib.util.spec_from_file_location(name,str(path));m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
R=loadmod('aa_canonical_executor',EXEC/'run.py')
PREP=loadmod('aa_canonical_source_preparer',EXEC/'prepare.py')
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj):C.atomic_json(Path(p),obj)
def utc():return datetime.now(timezone.utc).isoformat()
def event(kind,**kw):
    row={'at':utc(),'kind':kind,**kw}
    with (ROOT/'events.jsonl').open('a',buffering=1) as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    return row
def frozen_geometry():
    expected=read(ASSESS/'PARALLEL_PLAN.json')['geometry_bundle']
    for f,h in expected.items():
        if sha(f)!=h:raise RuntimeError(f'AA geometry drift: {f}')
    return expected
def occupied_seeds():
    seeds=set();sources=[]
    cfg=C.load_config(EXEC/'config.json')
    inherited,evidence=PREP.occupied_seeds(cfg);seeds.update(inherited)
    sources.append(evidence)
    # Accepted recent receipts/registries are bounded by the assessed lineage.
    paths=set(read(ASSESS/'SOURCES.json')['sources'])
    for model in ('sh3','sg3','sg3_minimal'):
        paths.add(str(G/'70_m05_sg3_sh3_prompt_statistics_integration_20260828/outputs'/model/'jobs.json'))
    for p in sorted(paths):
        f=Path(p)
        if f.suffix!='.json' or not f.is_file() or f.stat().st_size>20_000_000:continue
        d=read(f);seeds.update(PREP.extract_seed_values(d))
    seeds.update(PREP.extract_seed_values(read(SIGNAL/'inputs_manifest.json')))
    current=ROOT/'data/seed_registry.json'
    if current.exists():seeds.update(x['seed'] for x in read(current)['seeds'])
    return seeds,sources
def new_seed(identity,occupied):return PREP.derive_seed('AA_20260921_8H_NEW_PRODUCTION',identity,occupied)

def minimal_geometry():
    frozen_geometry()
    # MEGAlib resolves transitive relative Include paths against setup root.
    for name in ['Mass_model_AA.geo','Intro_Mass_model_AA.geo','Materials_Mass_model_AA.geo']:
        C.write_once_text(ROOT/'geometry'/name,(AA/'geometry'/name).read_text())
    m=loadmod('aa_minimal_builder_reference',G/'68_sg3_minimal_sd_prompt_supplement_20260823/code/build_minimal_alpha_pilot.py')
    det=(AA/'geometry/Mass_model_AA.det').read_text()
    names=[f'D{i}' for i in range(1,7)]+[x+'_SD' for x in BGO]
    selected={}
    for block in re.split(r'\n\s*\n',det):
        name=m.first_definition(block)
        if name in names:selected[name]=block.strip()
    assert set(selected)==set(names),(set(names)-set(selected))
    text='// Same physical AA geometry. Six TES layers and three BGO scorers only.\n\n'+'\n\n'.join(selected[n] for n in names)+'\n'
    C.write_once_text(ROOT/'geometry/Mass_model_AA_MINIMAL.det',text)
    C.write_once_text(MINIMAL_SETUP,'Name Mass_model_AA_MINIMAL\nVersion 1\nInclude Mass_model_AA.geo\nInclude Mass_model_AA_MINIMAL.det\nSurroundingSphere 60 5 0 9 60\n')
    return {'status':'PASS__SAME_AA_PHYSICAL_GEOMETRY_MINIMAL_DETECTORS','detectors':names,'setup':str(MINIMAL_SETUP),'physical_geo_sha256':sha(AA/'geometry/Mass_model_AA.geo'),'minimal_det_sha256':sha(ROOT/'geometry/Mass_model_AA_MINIMAL.det')}

def source_text(family,mode,job,seed,n,prefix,setup,minimal=False):
    # The retained source builder verifies flux/angle/energy/physics contracts.
    templates=PROJECT/'engineering/particle_source_unit_repair_20260811/config/source_cards/s3d_o8'
    candidates=sorted(templates.glob(f'*_{family}_*.source'))
    if not candidates:
        candidates=[p for p in templates.glob('*.source') if re.search(rf'particle={re.escape(family)}\s',p.read_text())]
    assert len(candidates)==1,(family,candidates)
    cfg=C.load_config(EXEC/'config.json')
    t=PREP.patch_source(candidates[0].read_text(),setup=setup,output_prefix=prefix,job_id=job,run_name=job,mode=mode,seed=seed,events=n,config=cfg)
    if minimal:t=t.replace('StoreSimulationInfo all','StoreSimulationInfo init-only')
    # Relative corrected spectra resolve under the unchanged project cwd.
    refs=re.findall(r'^\S+\.Spectrum File\s+(\S+)',t,re.M)
    assert len(refs)==20 and FORBIDDEN not in t and all(TOKEN in r for r in refs)
    assert all((PROJECT/r).is_file() for r in refs)
    return t

def config_for(name,setup,policy='corrected_keV_background'):
    gen=ROOT/'bundles'/name/'generated';run=DATA/name
    return {'schema_version':1,'profile_id':'AA_8H_'+name,'candidate':'AA','allowed_stages':['background','delayed','signal','atm511'],'source_policy':policy,'preflight_pass_status':'PASS__AA_INPUT_PREFLIGHT','source_manifest_pass_status':'PASS__AA_SOURCES','seed_registry_pass_status':'PASS__AA_FRESH_SEEDS','geometry_setup':str(setup),'cosima':'/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima','megalib_environment':'/home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh','cosima_workdir':str(PROJECT),'generated_root':str(gen),'run_root':str(run),'workers':12,'max_workers':12,'max_attempts':3,'start_free_bytes':RESERVE+2*GiB,'dynamic_reserve_bytes':RESERVE+GiB,'launch_mem_available_bytes':768*2**20,'runtime_mem_floor_bytes':512*2**20,'launch_swap_free_bytes':2*GiB,'runtime_swap_floor_bytes':GiB,'launch_worker_reservation_bytes':768*2**20,'aggregate_worker_rss_ceiling_bytes':0,'launch_memory_full_psi_avg10_max':5.,'runtime_memory_full_psi_avg10_max':15.,'poll_seconds':2.,'progress_interval_seconds':15.,'corrected_token':TOKEN,'forbidden_legacy_token':FORBIDDEN,'deadline_unix':DEADLINE,'additive_mono511':False}

def finish_bundle(name,cfg,jobs,source_rows):
    assert jobs
    jobs[0]['production_canary']=True
    cfg.update(expected_jobs=len(jobs),canary_job_id=jobs[0]['job_id'],expected_instant_histories=sum(j['events'] for j in jobs if j['mode']=='instant'),expected_buildup_histories=sum(j['events'] for j in jobs if j['mode']=='buildup'))
    totals={'jobs':len(jobs),'instant_histories':cfg['expected_instant_histories'],'buildup_histories':cfg['expected_buildup_histories']}
    gen=Path(cfg['generated_root']);ident={'schema_version':1,'profile_id':cfg['profile_id'],'candidate':'AA'}
    C.write_once_json(gen/'job_plan.json',{**ident,'status':'PASS','jobs':jobs,'totals':totals})
    C.write_once_json(gen/'seed_registry.json',{**ident,'status':cfg['seed_registry_pass_status'],'seeds':[{'job_id':j['job_id'],'seed':j['seed']} for j in jobs]})
    C.write_once_json(gen/'source_manifest.json',{**ident,'status':cfg['source_manifest_pass_status'],'sources':source_rows})
    C.write_once_json(gen/'preflight.json',{**ident,'status':cfg['preflight_pass_status'],'job_plan':totals,'AA_geometry_hashes':frozen_geometry(),'source_cards_checked':len(jobs),'source_refs_legacy':0})
    path=ROOT/'bundles'/name/'config.json';C.write_once_json(path,cfg)
    C.validate_generated_bundle(cfg,C.load_plan(cfg))
    return str(path)

def job_row(cfg,ordinal,identity,family,mode,n,seed,estimate,reference=None):
    prefix=Path(cfg['run_root'])/'jobs'/identity/'active'/identity
    stage='background' if mode in ('instant','buildup') else mode
    return {'ordinal':ordinal,'job_id':identity,'candidate':'AA','stage':stage,'mode':mode,'family':family,'events':int(n),'seed':seed,'source_path':str(Path(cfg['generated_root'])/'sources'/f'{identity}.source'),'setup_path':cfg['geometry_setup'],'output_prefix':str(prefix),'estimated_bytes':int(estimate),'requires_isotope_dat':mode in ('instant','buildup'),'production_canary':False,'reference':reference}
def source_row(j):return {**{k:j[k] for k in ['job_id','mode','family','events','seed','source_path','setup_path']},'source_sha256':sha(j['source_path'])}
