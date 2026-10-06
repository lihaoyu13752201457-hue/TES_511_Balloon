from aa_common import *
import gzip, math
from collections import defaultdict
import numpy as np

sys.path.insert(0,str(SIGNAL/'code'))
from pixel_geometry_compton import PixelGeometry,PixelGeometryCompton,PixelMeasurement,load_kernel,canonical_uid
SIG=loadmod('aa_signal_analysis_reference',SIGNAL/'code/analyze_signal.py')
MIN=loadmod('aa_minimal_parser_reference',G/'70_m05_sg3_sh3_prompt_statistics_integration_20260828/code/build_sg3_minimal_compacts.py')

def parse(path):
    events=[];cur=None;ts=None;end=False;header={}
    with gzip.open(path,'rt') as f:
        for raw in f:
            line=raw.strip()
            if line.startswith(('Geometry ','Seed ')):
                k,v=line.split(maxsplit=1);header[k]=v
            elif line=='SE':
                if cur is not None:events.append(cur);cur=None
            elif line.startswith('ID '):
                assert cur is None
                ids=list(map(int,line.split()[1:]));cur={'id':ids,'cc':defaultdict(float),'ht':[],'init':[]}
            elif line.startswith('IA INIT'):cur['init'].append(line)
            elif line.startswith('CC HIT '):
                m=SIG.HIT.match(line);assert m
                v,e,*_=m.groups()
                if SIG.TP.fullmatch(v) or v in BGO:cur['cc'][canonical_uid(v) if SIG.TP.fullmatch(v) else v]+=float(e)
            elif line.startswith('HTsim '):
                # StoreSimulationInfo all appends origin IDs; init-only omits
                # them. Compare the six measurement fields, retaining raw SIM.
                m=MIN.HT_RE.fullmatch(';'.join(line.split(';')[:6]));assert m,line
                cur['ht'].append({k:m.group(k) for k in ['kind','x','y','z','e','t']})
            elif line=='EN':end=True
            elif line.startswith('TS '):ts=int(line.split()[1])
    if cur is not None:events.append(cur)
    assert end and ts==len(events),(end,ts,len(events))
    assert [e['id'][1] for e in events]==list(range(1,ts+1))
    assert all(len(e['init'])==1 for e in events)
    return events,header

def close(a,b):return math.isclose(a,b,rel_tol=4e-5,abs_tol=1.2e-4)
def main():
    prep=read(ROOT/'data/preparation.json');all_events={};receipts={}
    for name in ['pilot_full','pilot_minimal_all','pilot_minimal_init']:
        cfg=C.load_config(prep['bundles'][name]);job=C.load_plan(cfg)[0];r=C.load_bound_receipt(cfg,job);assert r
        ev,h=parse(r['sim_path']);assert len(ev)==100 and h['Geometry']==job['setup_path'] and int(h['Seed'])==job['seed']
        all_events[name]=ev;receipts[name]=r
    full,ma,mi=[all_events[n] for n in ['pilot_full','pilot_minimal_all','pilot_minimal_init']]
    for a,b,c in zip(full,ma,mi):
        assert a['init']==b['init']==c['init'],('initials',a['id'])
        assert a['id']==b['id']==c['id']
        assert set(a['cc'])==set(b['cc']),('UID set',a['id'],set(a['cc'])^set(b['cc']))
        assert all(close(e,b['cc'][v]) for v,e in a['cc'].items()),('deposits',a['id'])
        assert b['ht']==c['ht'],('minimal HTsim all/init-only',a['id'])
    # Infer unique native scintillator label points from matched energy sums,
    # then demand a globally consistent one-to-one map across all observations.
    possibilities={}
    for e in ma:
        active={v:z for v,z in e['cc'].items() if v in BGO}
        for h in e['ht']:
            if int(h['kind'])!=4:continue
            key=tuple(float(h[k]) for k in ['x','y','z']);energy=float(h['e'])
            candidates={v for v,z in active.items() if close(z,energy)}
            assert candidates,('unmatched BGO HTsim',e['id'],h,active)
            possibilities[key]=possibilities.get(key,set(BGO))&candidates
    assert len(possibilities)==3 and all(len(v)==1 for v in possibilities.values()),possibilities
    centres={next(iter(v)):list(k) for k,v in possibilities.items()};assert set(centres)==set(BGO)
    MIN.SCINT_CENTERS=centres
    geom=PixelGeometry(AA/'geometry/Mass_model_AA.geo')
    mapping={'centers':{k:tuple(x) for k,x in geom.centres.items()},'codes':{k:(int(k.split('_')[1][1:]),int(k.split('_')[1][1:])*100000+int(k.split('_')[2])) for k in geom.centres},'center_by_key':{MIN.xyz_key(x):k for k,x in geom.centres.items()},'active_by_key':{MIN.xyz_key(x):k for k,x in centres.items()}}
    disk=load_kernel()['side_entry_disk']((-13.1,0,-5.2),1.898,45.)
    reco=PixelGeometryCompton(geom,disk,True);multi=0;bridge_max=0.;band=[];topology_checked=0
    for a,b in zip(ma,mi):
        decoded=defaultdict(float)
        for h in b['ht']:
            text=f"HTsim {h['kind']}; {h['x']}; {h['y']}; {h['z']}; {h['e']}; {h['t']}"
            row=MIN.decode_htsim_record(MIN.HT_RE.fullmatch(text),mapping,context=str(a['id']))
            decoded[row['target']]+=row['energy_keV']
        assert {v for v,z in decoded.items() if z>0}=={v for v,z in a['cc'].items() if z>1e-5},('bridge set',a['id'])
        for v,z in a['cc'].items():
            assert close(z,decoded.get(v,0)),(a['id'],v,z,decoded.get(v))
            bridge_max=max(bridge_max,abs(z-decoded.get(v,0)))
            if v in BGO and 50<=z<80:band.append({'event':a['id'][0],'volume':v,'energy_keV':decoded[v]})
        def measurements(d):
            out=[]
            for uid,z in sorted(d.items()):
                if not uid.startswith('TP_'):continue
                measured=z+.5/2.3548200450309493*SIG.normal('AA_bridge',a['id'][0],uid)
                if measured>=.3:out.append(PixelMeasurement(uid,measured))
            return out
        x,y=measurements(a['cc']),measurements(decoded)
        assert [m.pixel_uid for m in x]==[m.pixel_uid for m in y]
        if 2<=len(x)<=6:
            assert reco.classify(x)==reco.classify(y),('corrected Compton bridge',a['id']);multi+=1
        if x:topology_checked+=1
    assert multi>0,'bridge lacks nonempty multihit topology'
    report={'status':'PASS__AA_FULL_MINIMAL_RAW_AND_PIXEL_COMPTON_BRIDGE','events_each':100,'AA_geometry_hashes':frozen_geometry(),'matched_INITIALS_and_UIDs':True,'full_minimal_active_deposit_sums_close':True,'minimal_all_initonly_HTsim_exact':True,'BGO_native_centres':centres,'HTsim_bridge_max_abs_energy_difference_keV':bridge_max,'multihit_corrected_compton_checks':multi,'tes_topology_events_checked':topology_checked,'BGO_50_80_keV_examples':band,'BGO_50_80_observed':bool(band),'limitation':'100-alpha diagnostic is not a precision study; low-BGO band is also checked in focused/full records if absent here','production_credit':False,'corrected_compton_sha256':sha(SIGNAL/'code/pixel_geometry_compton.py'),'reused_decoder':str(G/'70_m05_sg3_sh3_prompt_statistics_integration_20260828/code/build_sg3_minimal_compacts.py'),'receipts':{n:r['sim_path'] for n,r in receipts.items()}}
    save(ROOT/'data/bridge_validation.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
