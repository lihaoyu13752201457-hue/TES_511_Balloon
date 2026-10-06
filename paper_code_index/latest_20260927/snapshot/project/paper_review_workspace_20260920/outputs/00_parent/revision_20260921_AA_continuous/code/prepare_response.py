from common import *
import time

def update_signal(model):
    d=O/'data'/model;d.mkdir(exist_ok=True)
    z=dict(np.load(signal_path(model)));r=recon(model);old=r.kernel['sample_cone_side_disk'];reference=recon(model,False)
    differences=[]
    ix=np.flatnonzero((z['measured_total_keV']>=480)&(z['measured_total_keV']<550)&(z['bgo_keV']<50))
    for i in ix:
        h=measurements(z,i);keep=bool(r.classify(h)[0])
        if keep!=bool(z['compton_pass'][i]):
            assert bool(reference.classify(h)[0])==bool(z['compton_pass'][i])
            reference.kernel['N_CONE_SAMPLES']=1536;dense=bool(reference.classify(h)[0]);reference.kernel['N_CONE_SAMPLES']=24
            assert keep==dense
            differences.append({'event_id':int(z['event_id'][i]),'old':bool(z['compton_pass'][i]),'continuous':keep,'dense1536':dense,'narrow':bool(z['narrow_pre'][i])})
        z['compton_pass'][i]=keep
    for window in ['narrow','broad']:
        z[window+'_final']=z[window+'_pre']&(z['bgo_keV']<50)&z['compton_pass']
    np.savez_compressed(d/'signal_catalog.npz',**z)
    counts={win:{'pre':int(z[win+'_pre'].sum()),'active':int(np.sum(z[win+'_pre']&(z['bgo_keV']<50))),'final':int(z[win+'_final'].sum())} for win in ['narrow','broad']}
    n=len(z['event_id']);k=counts['narrow']['final'];conv=OPTICAL_AREA*k/n
    # Optical and detector response share the original 150,000 optical trials.
    inc=150000;area_inc=OPTICAL_AREA*inc/n;se=area_inc*math.sqrt((k/inc)*(1-k/inc)/inc)
    result={'physical_model':'AA' if model=='a' else 'Lateral-chimney','input':n,'counts':counts,'conversion':{'value_cm2':conv,'combined_optical_detector_SE_cm2':se},'differences':differences,'source':str(signal_path(model)),'source_sha256':sha(signal_path(model))}
    save(d/'signal_summary.json',result);print(model,'signal',counts,flush=True)

def update_background(model):
    d=O/'data'/model;d.mkdir(exist_ok=True);a,reg,fac=background(model);r=recon(model);ref=recon(model,False)
    final=(a['broad_flags']&16)>0;final=final.copy();candidates=np.flatnonzero((a['broad_flags']&4)>0)
    active=set(map(int,candidates));mapped=set();diff=[];origins=[];max_error=0.;parity=0
    old_pixel={int(x['event_index']):x['pixel_geometry']=='True' for x in rows(W/'outputs/02_sources_response_compton/a_geometry_comparison_20260920/data/background_b_events.csv')} if model=='b' else {}
    mats={}
    for p in geometry(model).parent.glob('*.geo'):
        import re
        mats.update(re.findall(r'(?m)^([^\s.]+)\.Material\s+(\S+)\s*$',p.read_text()))
    def evaluate(i,h,meta,eid,volume=None,sourceza=None):
        nonlocal parity,max_error
        total=math.fsum(v.energy_keV for v in h);err=abs(total-float(a['measured_total_keV'][i]));max_error=max(max_error,err);assert err<1e-4,(i,err)
        reference=bool(ref.classify(h)[0]);assert reference==(old_pixel[i] if model=='b' else bool((a['broad_flags'][i]&16)>0)),(model,i,'old parity')
        parity+=1;keep=bool(r.classify(h)[0]);final[i]=keep;mapped.add(i)
        if keep!=reference:
            ref.kernel['N_CONE_SAMPLES']=1536;dense=bool(ref.classify(h)[0]);ref.kernel['N_CONE_SAMPLES']=24;assert keep==dense
            diff.append({'catalog_index':i,'old':reference,'continuous':keep,'dense1536':dense,'energy_keV':total})
        if keep and 510.5<=total<511.5 and meta.get('stream')=='delayed':
            cat=int(a['event_category'][i]);assert reg[cat]['source_parent_ZA']==sourceza
            origins.append({'catalog_index':i,'event_id':int(eid),'job_id':meta['job_id'],'family':meta['family'],'source_parent_ZA':int(sourceza),'source_volume':volume,'source_material':mats[volume],'day15_weight_cps':float(a['event_base_weight_cps'][i]*fac[60,cat]),'measured_total_keV':total,'sim_path':meta['sim_path'],'seed':int(meta['seed'])})
    if model=='a':
        cats={(c['stream'],c['family'],c['inventory_epoch'],c['source_parent_ZA']):c for c in reg}
        curs={k:c['event_start'] for k,c in cats.items()};nh=0
        files=read(AS/'derived/merged/manifest.json')['input_compacts']
        for ordinal,p in enumerate(files):
            p=Path(p);meta=read(p.with_suffix('.json'));z=np.load(p);stream=meta['stream'];fam=meta['family']
            if stream=='prompt':groups=[(('prompt',fam,-1,-1),np.arange(meta['detector_positive_events']))]
            else:
                za=z['source_za'];groups=[(('delayed',fam,0,int(q)),np.flatnonzero(za==q)) for q in np.unique(za)]
            selected=[]
            for key,idx in groups:
                st=curs[key];end=st+len(idx);curs[key]=end
                # Restrict extraction to previously identified active broad candidates.
                positions=candidates[(candidates>=st)&(candidates<end)]
                selected.extend((int(i),int(idx[i-st])) for i in positions)
            if selected:
                zz={k:z[k] for k in ['event_id','hit_start','hit_count','hit_code','hit_energy_keV']}
                vols=z['source_volume'] if stream=='delayed' else None
                mode='delayed' if stream=='delayed' else 'instant'
                for i,j in selected:
                    eid=int(zz['event_id'][j]);hs=int(zz['hit_start'][j]);hc=int(zz['hit_count'][j]);h=[]
                    assert hs+nh==a['hit_start'][i] and hc==a['hit_count'][i]
                    for q in range(hs,hs+hc):
                        code=int(zz['hit_code'][q]);uid=f'TP_L{code//100000}_{code%100000:05d}'
                        e=float(zz['hit_energy_keV'][q])+SIGMA*a_normal('sg3b',mode,fam,meta['batch_id'],int(meta['seed']),meta['job_id'],eid,uid)
                        if e>=.3:h.append(PixelMeasurement(uid,e))
                    evaluate(i,h,meta,eid,str(vols[j]) if vols is not None else None,int(za[j]) if stream=='delayed' else None)
            nh+=meta['raw_pixel_hits'];z.close()
            if ordinal%200==0:print(model,'compact metadata',ordinal,'/',len(files),'classified',len(mapped),flush=True)
        assert all(curs[k]==c['event_start']+c['event_count'] for k,c in cats.items())
        assert nh==len(a['hit_code'])
    else:
        identity=dict(np.load(D/'identity_b.npz'));jobs=read(D/'identity_b_jobs.json')
        for i in candidates:
            i=int(i);job=jobs[int(identity['event_job'][i])];eid=int(identity['event_id'][i]);h=[]
            for q in range(int(a['hit_start'][i]),int(a['hit_start'][i]+a['hit_count'][i])):
                code=int(a['hit_code'][q]);uid=f'TP_L{code//100000}_{code%100000:05d}'
                e=float(a['hit_energy_keV'][q])+SIGMA*normal('sh3_optv3',job['mode'],job['family'],job['batch_id'],int(job['seed']),job['job_id'],eid,uid)
                if e>=.3:h.append(PixelMeasurement(uid,e))
            evaluate(i,h,{**job,'stream':'prompt'},eid)
        # This lineage already has all selected source positions. Require exact identity closure.
        origins=rows(OLD/'delayed_origins_b_500.csv')
        expected={int(v['catalog_index']) for v in origins}
        sel={int(i) for i in candidates if final[i] and 510.5<=a['measured_total_keV'][i]<511.5 and reg[int(a['event_category'][i])]['stream']=='delayed'}
        assert expected==sel,(expected^sel)
    assert mapped==active
    np.save(d/'background_broad_continuous.npy',final)
    write(d/'origin_tasks.csv',origins)
    save(d/'background_response_validation.json',{'physical_model':'AA' if model=='a' else 'Lateral-chimney','broad_active_candidates':len(active),'old_classification_parity':parity,'maximum_energy_rounding_error_keV':max_error,'continuous_differences':diff,'selected_delayed_origin_records':len(origins),'no_truth_positions_in_reconstruction':True})
    print(model,'background COMPLETE',len(active),'differences',len(diff),'origins',len(origins),flush=True)

if __name__=='__main__':
    model=sys.argv[1];update_signal(model);update_background(model)
