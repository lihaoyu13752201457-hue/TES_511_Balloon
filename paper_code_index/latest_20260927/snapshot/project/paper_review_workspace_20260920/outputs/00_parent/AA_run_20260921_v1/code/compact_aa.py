"""AA adapter for the retained P62 catalog and P70 native HTsim decoder.
Only new AA PASS receipts are read. Reconstruct with physical pixels, never
energy-weighted deposition centroids. Preserve raw deposits for timeline reuse.
"""
from aa_common import *
import contextlib,gzip,math,shutil,traceback
from types import SimpleNamespace
import numpy as np
sys.path.insert(0,str(SIGNAL/'code'))
from pixel_geometry_compton import PixelGeometry,PixelGeometryCompton,PixelMeasurement,load_kernel
CAT=loadmod('aa_p62_catalog',G/'62_sg3b_mature_poisson_timeline_20260818/code/build_event_catalog.py')
COMMON=loadmod('aa_p58_common',G/'58_sg3b_m05_common_time_response_20260817/code/analyze_sg3b_common_time.py')
MIN=loadmod('aa_p70_minimal',G/'70_m05_sg3_sh3_prompt_statistics_integration_20260828/code/build_sg3_minimal_compacts.py')
GEOM=PixelGeometry(AA/'geometry/Mass_model_AA.geo')
DISK_REF=load_kernel()['side_entry_disk']((-13.1,0,-5.2),1.898,45.)
RECO=PixelGeometryCompton(GEOM,DISK_REF,True)
PARSER,CORE,STEP05,_=COMMON.runtime();CORE.SIGMA_KEV=.5/2.3548200450309493
COMMON.runtime=lambda:(PARSER,CORE,STEP05,DISK_REF)
COMMON.topology_keep=lambda hits,*unused:RECO.classify([PixelMeasurement(h.pixel_uid,h.e) for h in hits])
CAT.common_module=lambda:COMMON
CAT.WINDOWS['w2_510p58_511p42']=(510.5,511.5)
CENTRES=read(ROOT/'data/bridge_validation.json')['BGO_native_centres'];MIN.SCINT_CENTERS=CENTRES
MAPPING={'centers':{k:tuple(x) for k,x in GEOM.centres.items()},'codes':{k:(int(k.split('_')[1][1:]),int(k.split('_')[1][1:])*100000+int(k.split('_')[2])) for k in GEOM.centres},'center_by_key':{MIN.xyz_key(x):k for k,x in GEOM.centres.items()},'active_by_key':{MIN.xyz_key(x):k for k,x in CENTRES.items()}}


def scan(cfg,j):
    receipt=C.load_bound_receipt(cfg,j);assert receipt
    minimal=Path(j['setup_path'])==MINIMAL_SETUP
    cache=DATA/'derived/catalogs'/cfg['profile_id'];cache.mkdir(parents=True,exist_ok=True)
    identity=cache/f"job_{j['ordinal']:03d}_{j['job_id']}.json"
    if identity.exists():
        old=read(identity)
        if old.get('AA_audit',{}).get('status')=='PASS':return old
        raise RuntimeError('Unclosed compact artifact retained for audit: '+str(identity))
    job={**j,'scan_index':j['ordinal'],'stream':'delayed' if j['mode']=='delayed' else 'prompt','batch_id':cfg['profile_id'],'expected_geometry':j['setup_path'],'sim_path':receipt['sim_path'],'sim_bytes':receipt['sim_bytes'],'plastic_volumes':[],'bgo_volumes':list(BGO),'weight_cps':1.}
    if j['mode']=='delayed':job['positions_path']=j['reference']['positions_path']
    initials={};seen=[];ts=None;terminal=False;init_count=0;last_id=None;ht=0
    @contextlib.contextmanager
    def audited_open(path,*args,**kw):
        def lines(handle):
            nonlocal ts,terminal,init_count,last_id,ht
            for raw in handle:
                line=raw.strip()
                if line=='SE':
                    if last_id is not None:assert init_count==1,(j['job_id'],last_id,init_count)
                    last_id=None;init_count=0
                elif line.startswith('ID '):
                    ids=list(map(int,line.split()[1:3]));assert len(ids)==2 and ids[1]==len(seen)+1 and ids[0] not in initials
                    last_id=ids[0];seen.append(ids[0])
                elif line.startswith('IA INIT'):
                    assert last_id is not None
                    parts=line.split(';');assert len(parts)>=23
                    init_count+=1;initials[last_id]=(float(parts[-1]),float(parts[18]),tuple(map(float,parts[4:7])))
                elif line=='EN':terminal=True
                elif line.startswith('TS '):ts=int(line.split()[1])
                if minimal and line.startswith('HTsim '):
                    m=MIN.HT_RE.fullmatch(line);assert m,line
                    d=MIN.decode_htsim_record(m,MAPPING,context=j['job_id']);ht+=1
                    uid=d['target'];energy=d['energy_keV'];x,y,z=GEOM.centres[uid] if uid in GEOM.centres else CENTRES[uid]
                    if energy>0:yield f'CC HIT {uid} edep_keV={energy:.12g} x={x:.12g} y={y:.12g} z={z:.12g} t=0\n'
                else:yield raw
            if last_id is not None:assert init_count==1
            assert terminal and ts==j['events']==len(seen)==len(initials),(j['job_id'],terminal,ts,len(seen),len(initials))
        with gzip.open(path,*args,**kw) as handle:yield lines(handle)
    CAT.gzip=SimpleNamespace(open=audited_open)
    meta=CAT.scan_job(job,str(cache),50.)
    p=Path(meta['catalog_path']);a=dict(np.load(p,allow_pickle=False));values=[initials[int(i)] for i in a['event_id']]
    a['primary_energy_keV']=np.array([v[0] for v in values],dtype=np.float64)
    a['primary_dir_z']=np.array([v[1] for v in values],dtype=np.float64)
    if j['mode']=='delayed':
        locator=COMMON.position_locator(Path(job['positions_path']));parents=[COMMON.locate_source(locator,v[2])[0] for v in values]
        a['source_volume']=np.array([v[0] for v in parents],dtype=str)
        a['source_excitation_keV']=np.array([v[2] for v in parents],dtype=float)
        assert np.array_equal(a['source_za'],[v[1] for v in parents])
    tmp=p.with_suffix('.aa.tmp')
    with tmp.open('wb') as f:np.savez_compressed(f,**a)
    os.replace(tmp,p)
    meta['AA_audit']={'status':'PASS','gzip_crc_complete':True,'terminal_EN':terminal,'TS':ts,'one_INIT_per_event':True,'ordered_primary_ID':True,'native_HTsim_records':ht,'representation':'minimal_init_only' if minimal else 'full_CC','fwhm_keV':.5,'pixel_threshold_keV':.3,'bgo_threshold_keV':50,'narrow_window_keV':[510.5,511.5],'truth_positions_used_in_reconstruction':False,'corrected_compton_sha256':sha(SIGNAL/'code/pixel_geometry_compton.py'),'source_sha256':receipt['source_sha256'],'normalization':'UNNORMALIZED; rates must use AA-only TT and own epoch inventory; weight_cps placeholder is not a physical rate','receipt_TT_s':(receipt.get('isotope_dat') or {}).get('TT_s'),'reference':j.get('reference')}
    save(identity,meta);return meta


def service(entry_script='compact_aa.py'):
    os.nice(10);completed=set();error=None
    try:
        while time.time()<DEADLINE-15:
            progress=False
            for cp in sorted((ROOT/'bundles').glob('*/config.json')):
                cfg=C.load_config(cp)
                if any(x in cfg['profile_id'] for x in ('pilot','signal')):continue
                for j in C.load_plan(cfg):
                    if j['mode'] not in ('instant','delayed') or j['job_id'] in completed:continue
                    if not C.load_bound_receipt(cfg,j):continue
                    if shutil.disk_usage(DISK).free<RESERVE+GiB:raise RuntimeError('150GB compact-write reserve gate')
                    if C.meminfo()['MemAvailable']<900*2**20:continue
                    scan(cfg,j);completed.add(j['job_id']);progress=True
                    save(ROOT/'data/compact_service.json',{'status':'RUNNING','pid':os.getpid(),'entry_script':entry_script,'completed_jobs':len(completed),'at':utc(),'routine_agent_notification':False})
            # This is local bounded receipt monitoring, not agent polling.
            final=ROOT/'CAMPAIGN_FINAL.json';launch=read(ROOT/'data/campaign_launch.json')
            if final.exists() and read(final)['at']>launch['at'] and not progress:break
            time.sleep(15 if not progress else .1)
        save(ROOT/'data/compact_service.json',{'status':'STOPPED','completed_jobs':len(completed),'at':utc(),'deadline_unix':DEADLINE})
    except BaseException as e:
        error={'status':'EXCEPTION','error':str(e),'traceback':traceback.format_exc(),'completed_jobs':len(completed),'at':utc()};save(ROOT/'data/compact_service.json',error)
        print(json.dumps(error,ensure_ascii=False),flush=True);raise
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--fixture':
        prep=read(ROOT/'data/preparation.json')
        for name in ['pilot_full','pilot_minimal_init']:
            cfg=C.load_config(prep['bundles'][name]);m=scan(cfg,C.load_plan(cfg)[0]);print(name,m['AA_audit']['status'],m['detector_positive_events'])
    else:service()
