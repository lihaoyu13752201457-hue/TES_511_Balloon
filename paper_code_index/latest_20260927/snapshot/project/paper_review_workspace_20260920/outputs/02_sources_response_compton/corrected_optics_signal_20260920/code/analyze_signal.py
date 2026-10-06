"""500 eV isolated response and pixel-geometry selection; retain raw replay inputs."""
from pathlib import Path
from collections import Counter
import csv,gzip,hashlib,json,math,re,sys,time
import numpy as np
from pixel_geometry_compton import PixelGeometry,PixelGeometryCompton,PixelMeasurement,load_kernel

O=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,x:p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
HIT=re.compile(r'^CC HIT\s+(\S+)\s+edep_keV=([-\deE.+]+)\s+x=([-\deE.+]+)\s+y=([-\deE.+]+)\s+z=([-\deE.+]+)\s+t=([-\deE.+]+)')
TP=re.compile(r'^TP_L(\d+)_(\d+)$')
def normal(*keys):
    d=hashlib.blake2b('|'.join(map(str,keys)).encode(),digest_size=16).digest()
    return math.sqrt(-2*math.log(max(int.from_bytes(d[:8],'little')/2**64,1e-300)))*math.cos(2*math.pi*int.from_bytes(d[8:],'little')/2**64)
def binomial(k,n):
    p=k/n
    return {'kept':int(k),'denominator':int(n),'fraction':float(p),'standard_error':math.sqrt(p*(1-p)/n)}

def main(model):
    cfg=json.loads((O/'inputs_manifest.json').read_text());m=cfg['models'][model];n=cfg['n_input']
    receipt=json.loads((O/'runs'/model/'receipt.json').read_text());assert receipt['returncode']==0
    for item in m['geometry_provenance']:assert sha(Path(item['snapshot']))==item['sha256']
    assert sha(Path(m['source_card']))==m['source_card_sha256'] and sha(Path(m['eventlist']))==m['eventlist_sha256']
    source=np.loadtxt(m['eventlist']);identity=np.load(O/'data/optical_identity.npz')
    g=PixelGeometry(Path(m['geometry_geo']));disk=load_kernel()['side_entry_disk'](m['reference_plane_local_cm'],m['aperture_radius_cm'],45.)
    recon=PixelGeometryCompton(g,disk,True);sigma=.5/2.3548200450309493
    arrays={k:[] for k in ['event_id','primary_id','source_row','optical_event_id','event_time_s','hit_start','hit_count','plastic_keV','bgo_keV','true_total_keV','measured_total_keV','retained_hit_count','active_pass','narrow_pre','narrow_final','broad_pre','broad_final','compton_pass','compton_class']}
    hits={k:[] for k in ['hit_uid','hit_layer','hit_code','hit_energy_keV','hit_measured_energy_keV','hit_retained','hit_x_cm','hit_y_cm','hit_z_cm']}
    # Per-deposition timing supports future event grouping without retransport.
    dep={k:[] for k in ['event_index','volume_index','energy_keV','time_s']};volumes={}
    current=None;header={};pixels={};ep=eb=0.;init_count=0;evtime=0.;max_pos_err=0.;max_dir_err=0.;max_excess=0.;en_seen=False;ts=None;volcount=Counter();cc_lines=0
    def flush():
        nonlocal current,pixels,ep,eb,init_count,evtime
        if current is None:return
        eid,primary=current;i=primary-1
        assert eid==primary==len(arrays['event_id'])+1 and init_count==1,(model,current,init_count)
        start=len(hits['hit_uid']);measurements=[];true_total=0.
        for uid,record in sorted(pixels.items()):
            e,x,y,z=record;true_total+=e
            measured=e+sigma*normal('corrected_optics_signal_20260920',model,m['seed'],eid,uid)
            retained=measured>=.3
            layer,pixel=map(int,TP.fullmatch(uid).groups())
            values=[uid,layer,layer*100000+pixel,e,measured,retained,x/e,y/e,z/e]
            for k,v in zip(hits,values):hits[k].append(v)
            if retained:measurements.append(PixelMeasurement(uid,measured))
        total=math.fsum(x.energy_keV for x in measurements);active=ep<50 and eb<50
        narrow=510.5<=total<511.5;broad=480<=total<550
        keep,cls=recon.classify(measurements) if broad and active else (False,'not_evaluated_outside_broad_or_active')
        values=[eid,primary,i,int(identity['optical_event_id'][i]),evtime,start,len(pixels),ep,eb,true_total,total,len(measurements),active,narrow,narrow and active and keep,broad,broad and active and keep,keep,cls]
        for k,v in zip(arrays,values):arrays[k].append(v)
        current=None;pixels={};ep=eb=0.;init_count=0;evtime=0.
        if eid%5000==0:print(model,'response',eid,'/',n,flush=True)
    with gzip.open(m['sim'],'rt') as f:
        for raw in f:
            line=raw.strip()
            if line.startswith(('Geometry ','Seed ')):
                key,value=line.split(maxsplit=1);header[key]=value
            elif line=='SE':flush()
            elif line.startswith('ID '):
                assert current is None
                current=tuple(map(int,line.split()[1:3]));assert 1<=current[1]<=n
            elif line.startswith('TI '):evtime=float(line.split()[1])
            elif line.startswith('IA INIT'):
                assert current is not None
                fields=line.split(';');i=current[1]-1
                p=np.array(list(map(float,fields[4:7])));d=np.array(list(map(float,fields[16:19])))
                max_pos_err=max(max_pos_err,float(np.max(np.abs(p-source[i,5:8]))))
                max_dir_err=max(max_dir_err,float(np.max(np.abs(d-source[i,8:11]))))
                assert int(fields[15])==1 and float(fields[-1])==511.
                init_count+=1
            elif line.startswith('CC HIT '):
                h=HIT.match(line);assert h,line
                assert current is not None
                uid,e,x,y,z,t=h.groups();e=float(e);x=float(x);y=float(y);z=float(z);t=float(t)
                cc_lines+=1;volcount[uid]+=1
                ispixel=TP.fullmatch(uid)
                if ispixel or uid in m['plastic_volumes'] or uid in m['bgo_volumes']:
                    vi=volumes.setdefault(uid,len(volumes))
                    for k,v in zip(dep,[current[1]-1,vi,e,t]):dep[k].append(v)
                if ispixel:
                    max_excess=max(max_excess,g.deposition_excess_cm(uid,(x,y,z)))
                    record=pixels.setdefault(uid,[0.,0.,0.,0.]);record[0]+=e;record[1]+=e*x;record[2]+=e*y;record[3]+=e*z
                elif uid in m['plastic_volumes']:ep+=e
                elif uid in m['bgo_volumes']:eb+=e
            elif line=='EN':en_seen=True
            elif line.startswith('TS '):ts=int(line.split()[1])
    flush()
    assert len(arrays['event_id'])==ts==n and en_seen,(len(arrays['event_id']),ts,en_seen)
    assert header['Geometry']==m['geometry_setup'] and int(header['Seed'])==m['seed'],header
    assert max_pos_err<5.01e-6 and max_dir_err<5.01e-6,(max_pos_err,max_dir_err)
    assert max_excess<2e-4,max_excess
    a={k:np.asarray(v) for k,v in arrays.items()};h={k:np.asarray(v) for k,v in hits.items()}
    a.update(h);catalog=O/'data'/f'signal_{model}_catalog.npz';np.savez_compressed(catalog,**a)
    dp=O/'data'/f'signal_{model}_deposits.npz';np.savez_compressed(dp,**{k:np.asarray(v) for k,v in dep.items()})
    write(O/'data'/f'signal_{model}_volumes.json',list(volumes))
    stages={};rates={}
    for window in ['narrow','broad']:
        pre=a[window+'_pre'];plastic=a['plastic_keV']<50;bgo=a['bgo_keV']<50
        masks={'pre_veto':pre,'plastic_positron_veto':pre&plastic,'bgo_active_scintillator_veto':pre&bgo,'combined_active_veto':pre&plastic&bgo,'compton_trajectory_veto':a[window+'_final']}
        stages[window]={k:int(v.sum()) for k,v in masks.items()}
        rates[window]={
            'analysis_window_per_focal_photon':binomial(stages[window]['pre_veto'],n),
            'active_per_window':binomial(stages[window]['combined_active_veto'],stages[window]['pre_veto']),
            'compton_per_active':binomial(stages[window]['compton_trajectory_veto'],stages[window]['combined_active_veto']),
            'total_per_focal_photon':binomial(stages[window]['compton_trajectory_veto'],n)}
    nopt=cfg['optical_manifest']['n_incident'];area=cfg['optical_manifest']['sampled_crystal_area_cm2'];k=stages['narrow']['compton_trajectory_veto']
    area_factor=area*k/nopt;p=k/nopt
    result={'status':'PASS','model':model,'events':n,'stage_counts':stages,'retention':rates,'optical_area_cm2':cfg['optical_manifest']['Aeff_opt_cm2'],
        'isolated_signal_count_conversion':{'quantity':'optical_area_times_total_signal_retention','value_cm2':area_factor,'mc_standard_error_cm2':area*math.sqrt(p*(1-p)/nopt),'denominator_incident_optical_primaries':nopt,'selected_count':k},
        'raw_TES_positive_events':int((a['hit_count']>0).sum()),'retained_pixel_positive_events':int((a['retained_hit_count']>0).sum()),
        'selected_multiplicity':dict(Counter(map(str,a['retained_hit_count'][a['narrow_final']]))),
        'compton_classes':dict(Counter(a['compton_class'][a['broad_pre']&a['active_pass']])),'header':header,
        'audit':{'gzip_crc_complete':True,'terminal_EN':en_seen,'TS':ts,'one_INIT_per_event':True,'eventlist_SIM_position_max_error_cm':max_pos_err,'eventlist_SIM_direction_max_error':max_dir_err,'max_deposit_outside_pixel_cm':max_excess,'raw_CC_hit_lines':cc_lines,'pixel_count':len(g.centres),'truth_positions_used_in_reconstruction':False},
        'provenance':{'sim':m['sim'],'sim_sha256':sha(Path(m['sim'])),'sim_bytes':Path(m['sim']).stat().st_size,'source_card':m['source_card'],'source_sha256':m['source_card_sha256'],'eventlist_sha256':m['eventlist_sha256'],'geometry':m['geometry_provenance'],'response_script_sha256':sha(Path(__file__)),'reconstruction':cfg['reconstruction_code']},
        'replay_interface':{'catalog':str(catalog),'catalog_sha256':sha(catalog),'per_deposition_file':str(dp),'volume_names':str(O/'data'/f'signal_{model}_volumes.json'),'raw_energy':'hit_energy_keV before noise and pixel threshold; pixel identity in hit_uid/hit_code/hit_layer','measured_energy':'hit_measured_energy_keV, one independent 500 eV FWHM Gaussian per deposited pixel','event_id_mapping':'source_row=primary_id-1; optical_event_id maps shared optical photons across A/B','timing':'deposition time_s is relative Geant4 primary-flight time in seconds; artificial EventList event_time_s is NOT a physical mission rate','event_group_replay':'merge raw pixel energies and active deposits, then apply response once per grouped pixel and the frozen pixel-geometry kernel','conditional_proxy_interface':'Existing signal_probe uses background-only contamination, not actual signal deposits; new samples support an explicit signal-dependent replay if requested.'}}
    write(O/'data'/f'signal_{model}_summary.json',result)
    write(O/'validation'/f'transport_{model}.json',{'status':'PASS',**result['audit'],'header':header,'seed':m['seed'],'sim_sha256':result['provenance']['sim_sha256']})
    with (O/'data'/f'signal_{model}_events.csv').open('w') as f:
        keys=['event_id','source_row','optical_event_id','true_total_keV','measured_total_keV','retained_hit_count','plastic_keV','bgo_keV','narrow_pre','narrow_final','compton_class']
        writer=csv.writer(f);writer.writerow(keys)
        writer.writerows(zip(*(a[k] for k in keys)))
    print(json.dumps({'model':model,'status':'PASS','stage_counts':stages,'retention':rates['narrow']},indent=2),flush=True)

if __name__=='__main__': main(sys.argv[1])
