from common import *
model=sys.argv[1];d=O/'data'/model;a,reg,fac=background(model)
s=dict(np.load(d/'signal_catalog.npz'));nb=len(a['hit_count']);ns=len(s['event_id'])
final=np.load(d/'background_broad_continuous.npy');window=(a['measured_total_keV']>=510.5)&(a['measured_total_keV']<511.5)
final_window=window&final;active_window=window&(a['bgo_keV']<50)
record=np.zeros(nb+ns,dtype=DT)
record['bgo']=np.r_[a['bgo_keV'],s['bgo_keV']];record['hits']=np.r_[a['hit_count'],s['hit_count']]
record['flags'][:nb]=window.astype('u1')+6*final_window.astype('u1')+8*active_window.astype('u1')
record['flags'][nb:]=s['narrow_pre'].astype('u1')+6*s['narrow_final'].astype('u1')+8*(s['narrow_pre']&(s['bgo_keV']<50)).astype('u1')
catstream=np.array([int(c['stream']=='delayed') for c in reg],dtype='u1')
record['stream'][:nb]=catstream[a['event_category']];record['stream'][nb:]=2
record.tofile(d/'records.bin')
masks=[]
for stream in [0,1]:
    masks.extend([(record['hits']==0)&(record['stream']==stream)&(record['bgo']>=50),np.zeros(nb+ns,dtype=bool)])
retained=np.flatnonzero(~np.logical_or.reduce(masks));hot=np.zeros(4,dtype=DT);hot['bgo'][[0,2]]=50;hot['plastic'][[1,3]]=50;hot['stream']=[0,0,1,1]
compact=np.r_[hot,record[retained]];mapping=np.r_[-np.arange(1,5,dtype='i8'),retained]
compact.tofile(d/'compact_records.bin');mapping.tofile(d/'compact_to_original.bin')
cat=np.asarray(a['event_category']);base=np.asarray(a['event_base_weight_cps']);nc=len(reg)
q1=np.bincount(cat[final_window],weights=base[final_window],minlength=nc);q2=np.bincount(cat[final_window],weights=base[final_window]**2,minlength=nc)
np.savez_compressed(d/'category_sums.npz',q1=q1,q2=q2,scales=fac)
save(d/'category_registry.json',{'categories':reg})
atm=rows(P/'engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/fullchain/step06/atmosphere_transmission_511_by_time.csv')
bg=fac@q1;bgvar=fac**2@q2;direct=[];metadata={'model':model,'physical_model':'AA' if model=='a' else 'Lateral-chimney','background_records':nb,'signal_records':ns,'optical_area_cm2':OPTICAL_AREA,'Fref':FREF,'anchors':{},'parameters':{'tau_s':TAU,'FWHM_keV':.5,'pixel_threshold_keV':.3,'window_keV':[510.5,511.5],'bgo_threshold_keV':50,'source_elevation_deg':27},'continuous_kernel_sha256':sha(O/'code/continuous_disk.py')}
for node in range(81):
    transmission=float(atm[node]['T_atm_511'])**(1/math.sin(math.radians(27)));signalrate=FREF*OPTICAL_AREA*transmission
    row={'node':node,'day':node/4,'transmission':transmission,'signal_input_rate':signalrate,'isolated_signal_final_rate':signalrate*float(s['narrow_final'].mean()),'background_bgo_final_rate':float(bg[node]),'background_dual_final_rate':float(bg[node]),'direct_transport_sigma_cps':float(np.sqrt(bgvar[node]))}
    direct.append(row)
    if node in [0,20,40,60,80]:
        weights=np.r_[base*fac[node,cat],np.full(ns,signalrate/ns)]
        nw=np.r_[[weights[mask].sum() for mask in masks],weights[retained]]
        for stream in [0,1,2]:assert np.isclose(nw[compact['stream']==stream].sum(),weights[record['stream']==stream].sum(),rtol=1e-13)
        nw.tofile(d/f'compact_weights_{node:03d}.bin')
        metadata['anchors'][str(node)]={**row,'total_background_rate':float(weights[:nb].sum()),'prompt_rate':float(weights[record['stream']==0].sum()),'delayed_rate':float(weights[record['stream']==1].sum())}
write(d/'direct_81nodes.csv',direct);save(d/'metadata.json',metadata)
cm={**metadata,'original_background_records':nb,'background_records':len(compact)-ns,'hot_marks':4,'compression':'Only no-TES BGO>=50 marks collapsed; prompt and delayed independent. No change to arrivals or subthreshold deposits.'};save(d/'compact_metadata.json',cm)
w=base*fac[60,cat];positive=w>0;delayed=catstream[cat].astype(bool)
comps={'total':np.ones(nb,dtype=bool),'delayed':delayed,'gamma':np.asarray(a['event_component'])==1,'non_gamma':~delayed&(np.asarray(a['event_component'])==0)}
stats={};spec=[]
for stage,mask in [('pre_veto',np.ones(nb,dtype=bool)),('combined_active_veto',np.asarray(a['bgo_keV'])<50),('compton_trajectory_veto',final)]:
    stats[stage]={}
    for name,c in comps.items():
        selected=mask&window&c&positive;q=w[selected];rate=float(q.sum());var=float((q*q).sum())
        stats[stage][name]={'n':int(selected.sum()),'rate':rate,'variance':var,'sigma':math.sqrt(var),'neff':rate*rate/var if var else 0}
    selected=mask&positive&(a['measured_total_keV']>=480)&(a['measured_total_keV']<550);edges=np.arange(480,550.01,.25)
    y=np.histogram(a['measured_total_keV'][selected],bins=edges,weights=w[selected])[0];v=np.histogram(a['measured_total_keV'][selected],bins=edges,weights=w[selected]**2)[0]
    spec.extend({'stage':stage,'stream':'all','component':'all','energy_low_keV':float(edges[j]),'sumw_cps':float(y[j]),'sqrt_sumw2_cps':float(np.sqrt(v[j]))} for j in range(len(y)))
assert math.isclose(stats['compton_trajectory_veto']['total']['rate'],bg[60],rel_tol=1e-12)
save(d/'direct_statistics.json',stats);write(d/'direct_spectra.csv',spec)
save(d/'family_transport.json',[{'family':f,'stream':stream,'detector_positive':sum(c['event_count'] for c in reg if c['stream']==stream and c['family']==f),'occupancy_day15_cps':float(sum(fac[60,i]*c['sum_event_base_weight_cps'] for i,c in enumerate(reg) if c['stream']==stream and c['family']==f))} for stream in ['prompt','delayed'] for f in ['gamma','n','eminus','eplus','p','alpha','muminus','muplus']])
print(model,'PREPARED',len(record),'->',len(compact),'day15',metadata['anchors']['60'],flush=True)
