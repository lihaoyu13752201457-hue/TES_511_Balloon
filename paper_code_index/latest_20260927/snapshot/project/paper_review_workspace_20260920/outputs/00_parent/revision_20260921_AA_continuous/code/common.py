import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,csv,hashlib,math,ast
import numpy as np
from pixel_geometry_compton import PixelGeometry,PixelGeometryCompton,PixelMeasurement,load_kernel
from continuous_disk import make_kernel
O=Path(__file__).resolve().parents[1];W=O.parents[2];P=W.parent
AA=O.parent/'AA_run_20260921_v1'
AS=Path('/media/ubuntu/903261CE3261BA3C/TES_Balloon_511_data/AA/aa_reproduce_A_20260921_v1')
S=W/'outputs/02_sources_response_compton/corrected_optics_signal_20260920'
D=P/'core_md/balloon511_ea_latex_drafts/meeting_revision_20260916/data'
BC=P/'engineering/geometry_optimization_20260815/70_m05_sg3_sh3_prompt_statistics_integration_20260828/outputs/01_integrated_catalog_b'
OLD=W/'outputs/03_mission_baseline_design/numeric_sync_20260920/data'
TAU=1e-6;SIGMA=.5/2.3548200450309493;FREF=2.4e-4
OPTICAL_AREA=19.716576335319342
DT=np.dtype([('plastic','<f4'),('bgo','<f4'),('hits','<u2'),('flags','u1'),('stream','u1')])
def read(p):return json.loads(Path(p).read_text())
def save(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def rows(p):return list(csv.DictReader(Path(p).open()))
def write(p,rs):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    if not rs:p.write_text('');return
    with p.open('w') as f:
        wr=csv.DictWriter(f,fieldnames=list(rs[0]));wr.writeheader();wr.writerows(rs)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def normal(*keys):
    d=hashlib.blake2b('|'.join(map(str,keys)).encode(),digest_size=16).digest()
    return math.sqrt(-2*math.log(max(int.from_bytes(d[:8],'little')/2**64,1e-300)))*math.cos(2*math.pi*int.from_bytes(d[8:],'little')/2**64)
path=P/'engineering/particle_source_unit_repair_20260811/seven_family_tes_activation_postprocess_20260812/code/analyze_seven_family_tes_activation.py'
nodes=[n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ['canonical_json_bytes','keyed_standard_normal'] or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='RESPONSE_NAMESPACE' for t in n.targets)]
ns={'Any':object,'json':json,'hashlib':hashlib,'math':math};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns)
a_normal=ns['keyed_standard_normal']
def geometry(model):
    return AA/'geometry/Mass_model_AA.geo' if model=='a' else Path(read(S/'inputs_manifest.json')['models']['b']['geometry_geo'])
def recon(model,continuous=True):
    r=PixelGeometryCompton(PixelGeometry(geometry(model)),load_kernel()['side_entry_disk']((-13.1,0,-5.2) if model=='a' else (-46,0,-2.8),1.898 if model=='a' else 1.9,45.),True)
    if continuous:r.kernel['sample_cone_side_disk']=make_kernel(r.kernel)
    return r
def background(model):
    if model=='a':
        d=AS/'derived/merged';m=read(d/'manifest.json');a={k:np.load(d/(k+'.npy'),mmap_mode='r') for k in m['files']}
        reg=read(d/'category_registry.json')['categories'];fac=np.load(d/'category_factors.npy')
    else:
        z=np.load(BC/'combined_event_catalog.npz');a={k:z[k] for k in z.files};a.update(dict(np.load(D/'response_b_500.npz')))
        reg=read(BC/'category_registry.json')['categories'];f=dict(np.load(D/'category_factors_b.npz'));fac=f['common_factor'].copy()
        for i,c in enumerate(reg):
            if c['component']=='gamma_continuum':fac[:,i]=f['gamma_scale']
            if c['component']=='atm511':fac[:,i]=0
    return a,reg,fac
def signal_path(model):return AA/'signal_response/data/signal_aa_catalog.npz' if model=='a' else S/'data/signal_b_catalog.npz'
def measurements(z,i):
    st=int(z['hit_start'][i]);end=st+int(z['hit_count'][i])
    return [PixelMeasurement(str(z['hit_uid'][j]),float(z['hit_measured_energy_keV'][j])) for j in range(st,end) if z['hit_retained'][j]]
