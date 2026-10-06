"""AA data adapter around retained P67 Poisson and 81-node mission algorithms."""
from aa_common import *
import math,csv,collections
from types import SimpleNamespace
import numpy as np
from merge_aa import OUT,Q,csvrows
sys.path.insert(0,str(SIGNAL/'code'))
from pixel_geometry_compton import PixelGeometry,PixelGeometryCompton,PixelMeasurement,load_kernel
SIG=loadmod('aa_replay_signal_rng',SIGNAL/'code/analyze_signal.py')
E=loadmod('aa_retained_poisson',Q/'code/run_fluxclosed_timeline.py');E.WINDOWS[E.FINAL_WINDOW]=(510.5,511.5)

class Replay(E.Replay):
    def __init__(self,fixture=None):
        self.model='AA';self.out=DATA/'derived/timeline';self.out.mkdir(parents=True,exist_ok=True)
        self.manifest=read(OUT/'manifest.json');assert self.manifest['status'].startswith('PASS')
        self.a={k:np.load(OUT/(k+'.npy'),mmap_mode='r',allow_pickle=False) for k in self.manifest['files']}
        self.categories=read(OUT/'category_registry.json')['categories'];self.n_categories=len(self.categories)
        self.starts=np.array([x['event_start'] for x in self.categories]);self.counts=np.array([x['event_count'] for x in self.categories])
        self.cat_component_names=[x['component'] for x in self.categories];self.cat_components=np.array([E.COMPONENT_CODES[x] for x in self.cat_component_names],dtype=np.uint8)
        self.streams=[x['stream'] for x in self.categories];self.families=[x['family'] for x in self.categories];self.zas=np.array([x['source_parent_ZA'] for x in self.categories])
        self.common_factor=np.load(OUT/'category_factors.npy');self.days=np.arange(81)/4;self.line_ratio=np.zeros((81,80))
        self.gamma_scale=np.array([float(x['gamma_continuum_scale_to_reference']) for x in csvrows(Q/'outputs/00_source_closure/trajectory_component_scales_81nodes.csv')])
        self.atmosphere=csvrows(PROJECT/'engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/fullchain/step06/atmosphere_transmission_511_by_time.csv')
        self.seed=2026092101;self.chunk_events=1000000;self.exposure_s=20000.;self.signal_trials=2000000
        signal=read(ROOT/'signal_response/data/signal_aa_summary.json');p=signal['retention']['narrow']['total_per_focal_photon'];area=signal['optical_area_cm2']
        self.authority=SimpleNamespace(candidate='AA',mission={'source_elevation_deg':27.},timeline={'coincidence_window_s':1e-6,'plastic_threshold_keV':50.,'bgo_threshold_keV':50.},signal={'input_rays':signal['events'],'stage_count':p['kept'],'optical_aperture_cm2':area,'aeff_cm2':area*p['fraction'],'aeff_sigma_cm2':area*p['standard_error'],'authority':str(ROOT/'signal_response/data/signal_aa_summary.json'),'quantity':'optical effective area multiplied by signal retention; internal legacy interface field only'})
        self.pixel=PixelGeometryCompton(PixelGeometry(AA/'geometry/Mass_model_AA.geo'),load_kernel()['side_entry_disk']((-13.1,0,-5.2),1.898,45.),True)
        self.sigma_keV=.5/2.3548200450309493;self.veto_threshold_keV=50.;self.pixel_threshold_keV=.3
        self.total_aggregates=[];self.selection_aggregates={};self.continuum_qmax=np.zeros(self.n_categories);self.continuum_acceptance=np.ones(self.n_categories);self.line_indices={}
        # P67's historical helper requires an atmospheric-line category. AA uses
        # the paper's continuum-only sum; aggregate the same q/q^2 without that
        # unrelated requirement. Sampling/timeline/integration stay inherited.
        for i,row in enumerate(self.categories):
            sl=slice(int(self.starts[i]),int(self.starts[i]+self.counts[i]));q=self.a['event_base_weight_cps'][sl]
            if self.cat_components[i]==0:self._constant(q,'AA category weight')
            else:self.continuum_qmax[i]=float(q.max());self.continuum_acceptance[i]=float(q.mean()/q.max())
            def aggregate(mask=None):
                v=q if mask is None else q[mask]
                return E.Aggregate(count=len(v),sum_q=float(np.sum(v,dtype=np.float64)),sum_q2=float(np.sum(v*v,dtype=np.float64)))
            a=aggregate();assert math.isclose(a.sum_q,row['sum_event_base_weight_cps'],rel_tol=3e-12)
            assert math.isclose(a.sum_q2,row['sum_event_base_weight2_cps2'],rel_tol=3e-12)
            self.total_aggregates.append(a)
            for window,field in E.WINDOW_FLAG_FIELDS.items():
                for stage,bit in E.STAGE_BITS.items():self.selection_aggregates[(i,window,stage)]=aggregate((self.a[field][sl]&bit)!=0)
        self.category_rate_matrix=np.array([[self._aggregate_value(a,i,node)[0] for i,a in enumerate(self.total_aggregates)] for node in range(81)])
        self.fingerprint_payload={'AA_merge':sha(OUT/'manifest.json'),'AA_geometry':frozen_geometry(),'signal':sha(ROOT/'signal_response/data/signal_aa_summary.json'),'corrected_compton':sha(SIGNAL/'code/pixel_geometry_compton.py'),'adapter':sha(__file__),'engine':sha(Q/'code/run_fluxclosed_timeline.py'),'parameters':{'seed':self.seed,'anchor_exposure_s':self.exposure_s,'signal_trials':self.signal_trials,'nodes':81,'tau_s':1e-6,'fwhm_keV':.5,'source_elevation_deg':27.,'atmospheric_mono511_added':False}}
        self.fingerprint_sha256=E.canonical_digest(self.fingerprint_payload)
    def combined_flags(self,event_indices,node,serial):
        bgo=float(np.sum(self.a['bgo_keV'][event_indices],dtype=np.float64));pixels=collections.defaultdict(float)
        for i in event_indices:
            for h in range(int(self.a['hit_start'][i]),int(self.a['hit_start'][i]+self.a['hit_count'][i])):pixels[int(self.a['hit_code'][h])]+=float(self.a['hit_energy_keV'][h])
        hits=[]
        for code,e in sorted(pixels.items()):
            layer=code//100000;uid=f'TP_L{layer}_{code-layer*100000}';measured=e+self.sigma_keV*SIG.normal('AA','mature_timeline',self.seed,node,serial,uid)
            if measured>=.3:hits.append(PixelMeasurement(uid,measured))
        total=math.fsum(h.energy_keV for h in hits);active=bgo<50.
        keep=self.pixel.classify(hits)[0] if active and 480<=total<550 else False
        flags=[]
        for low,high in E.WINDOWS.values():
            bits=0
            if low<=total<high:bits=1|2|(4|8 if active else 0)|(16 if active and keep else 0)
            flags.append(bits)
        return tuple(flags)
    def process_groups(self,*args,**kw):
        if time.time()>DEADLINE-10:raise RuntimeError('eight-hour deadline: replay stopped with completed anchors retained')
        return super().process_groups(*args,**kw)

def writecsv(p,rows):
    if not rows:return
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    r=Replay();receipts=[];(r.out/'receipts').mkdir(exist_ok=True)
    direct=[{'node':n,'day':n/4,**r.direct_stats(n,E.FINAL_WINDOW,E.FINAL_STAGE)} for n in range(81)]
    writecsv(r.out/'direct_final_81nodes.csv',direct)
    for ordinal,node in enumerate(E.ANCHOR_NODES):
        receipts.append(r.anchor_receipt(node,ordinal,r.out/'receipts'/f'anchor_{node:03d}.json'))
        event('AA_TIMELINE_ANCHOR_COMPLETE',node=node)
    cut,spectrum,multiplicity,components,schema=r.day15_products();anchors,acomp=E.anchor_rows(r,receipts);mission,mcomp,unc=E.build_mission(r,receipts)
    for name,rows in [('direct_cutflow_day15.csv',cut),('direct_energy_day15.csv',spectrum),('direct_multiplicity_day15.csv',multiplicity),('anchor_rates.csv',anchors),('anchor_components.csv',acomp),('mission_81nodes.csv',mission),('mission_components.csv',mcomp)]:writecsv(r.out/name,rows)
    result={'status':'PASS__AA_PIXEL_COMPTON_POISSON_MISSION','at':utc(),'fingerprint':r.fingerprint_payload,'mission_20day':mission[-1],'uncertainty':unc,'signal':r.authority.signal,'day15_schema':schema,'limitation':'signal_probe is retained background-only contamination proxy; no claim of joint signal/background transport','output':str(r.out)}
    save(r.out/'summary.json',result);save(ROOT/'data/replay.json',result)
if __name__=='__main__':main()
