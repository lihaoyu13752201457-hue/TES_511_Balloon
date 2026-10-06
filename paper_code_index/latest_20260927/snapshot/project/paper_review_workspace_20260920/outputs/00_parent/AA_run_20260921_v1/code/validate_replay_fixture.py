"""Synthetic interface validation only; no production credit or AA rate claim."""
from aa_common import *
import tempfile,numpy as np
import replay_aa as M
from merge_aa import EVENT_DT,HIT_DT
with tempfile.TemporaryDirectory(prefix='aa_replay_fixture_') as td:
    p=Path(td);M.OUT=p;M.DATA=p
    geom=M.PixelGeometry(AA/'geometry/Mass_model_AA.geo');uid=next(iter(geom.centres));layer=int(uid.split('_')[1][1:]);code=layer*100000+int(uid.split('_')[2]);xyz=geom.centres[uid]
    arrays={k:np.zeros(2,dtype=t) for k,t in {**EVENT_DT,**HIT_DT}.items()}
    arrays.update(event_category=np.array([0,1],dtype='i4'),event_component=np.array([0,1],dtype='u1'),event_base_weight_cps=np.array([100.,50.]),continuum_importance_weight=np.array([1.,.5]),hit_start=np.array([0,1]),hit_count=np.ones(2,dtype='u2'),hit_code=np.full(2,code,dtype='i4'),hit_layer=np.full(2,layer,dtype='u1'),hit_energy_keV=np.full(2,511.,dtype='f4'),measured_total_keV=np.full(2,511.,dtype='f4'),broad_flags=np.full(2,31,dtype='u1'),w2_flags=np.full(2,31,dtype='u1'))
    for k,v in zip('xyz',xyz):arrays[f'hit_{k}_cm']=np.full(2,v,dtype='f4')
    for k,a in arrays.items():np.save(p/(k+'.npy'),a)
    np.save(p/'category_factors.npy',np.ones((81,2)))
    cats=[{'category_id':i,'stream':'prompt','family':fam,'inventory_epoch':-1,'source_parent_ZA':-1,'component':comp,'event_start':i,'event_count':1,'sum_event_base_weight_cps':w,'sum_event_base_weight2_cps2':w*w} for i,fam,comp,w in [(0,'n','other',100.),(1,'gamma','gamma_continuum',50.)]]
    save(p/'category_registry.json',{'categories':cats});save(p/'manifest.json',{'status':'PASS__SYNTHETIC_FIXTURE','files':list(arrays)})
    r=M.Replay();r.exposure_s=1.;r.signal_trials=1000;r.chunk_events=1000
    # Time factors are deliberately all one for this API closure fixture.
    r.gamma_scale[:]=1
    (r.out/'receipts').mkdir()
    receipts=[r.anchor_receipt(n,i,r.out/'receipts'/f'{n}.json') for i,n in enumerate(M.E.ANCHOR_NODES)]
    cut,spec,mul,components,schema=r.day15_products();anchors,acomp=M.E.anchor_rows(r,receipts);mission,mcomp,unc=M.E.build_mission(r,receipts)
    assert len(mission)==81 and mission[-1]['day_mid']==20
    save(ROOT/'data/replay_end_to_end_fixture.json',{'status':'PASS__SYNTHETIC_INTERFACE_ONLY','five_anchors':len(receipts),'mission_nodes':len(mission),'production_credit':False,'validates':'AA adapter/P67 inherited sampling, grouping, products and mission interface; not physical AA results'})
    print('PASS synthetic end-to-end adapter; no physics production credit')
