"""Small fixed-N response supplement, separate geometry and production family."""
from pathlib import Path
import sys,json,re,time,subprocess,concurrent.futures,collections
import numpy as np
P=Path(__file__).resolve().parents[1];O=P.parent;sys.path.insert(0,str(O/'code'))
from targeted_environment import sha
from prepare_repair import env

def plan():
    assert json.loads((P/'data/location_validation.json').read_text())['status']=='PASS'
    registry=json.loads((P/'data/restored_registry.json').read_text());rates=np.load(P/'data/restored_rates_81nodes.npy');jobs=json.loads((O/'data/runtime_jobs.json').read_text())
    groups=collections.defaultdict(list)
    for r in registry:
        groups[r['model'],r['family'],'bgo' if r['material'].lower()=='bgo' or 'BGO' in r['volume'] else 'other'].append(r['category_id'])
    out=P/'responses';out.mkdir(exist_ok=True);plans=[]
    assert not (out/'plan.json').exists(),'Immutable registered response plan already exists'
    # Fixed allocation before any response result: 40,000 per material stratum,
    # 80,000 per geometry. Do not expand merely because a pool selects zero.
    for model in ['a','b']:
        for stratum in ['bgo','other']:
            keys=sorted(k for k in groups if k[0]==model and k[2]==stratum)
            q=np.array([rates[:,groups[k]].max(axis=0).sum() for k in keys]);target=40000*np.sqrt(q)/np.sqrt(q).sum();counts=np.floor(target).astype(int)
            counts[np.argsort(-(target-counts))[:40000-counts.sum()]]+=1
            for key,n in zip(keys,counts):
                if not n:continue
                cat=np.array(groups[key]);bound=rates[:,cat].max(axis=0);qsum=bound.sum();seed=1690271101+len(plans);rng=np.random.default_rng(seed);pick=rng.choice(cat,size=n,p=bound/qsum)
                name='_'.join(key);directory=out/name;directory.mkdir(exist_ok=True);source=directory/'run.source';elist=directory/'events.dat'
                elist.write_text('\n'.join(f'{i} 0 {registry[c]["za"]} {registry[c]["exc_keV"]:.12g} {i+1} {registry[c]["x"]:.12g} {registry[c]["y"]:.12g} {registry[c]["z"]:.12g} 0 0 1 0 0 0 0.000001' for i,c in enumerate(pick))+'\n')
                np.savez_compressed(directory/'draws.npz',category=pick,point_id=np.array([registry[c]['ledger_id'] for c in pick],dtype='i4'))
                geometry=re.search(r'(?m)^Geometry\s+(.*)$',Path(next(j for j in jobs if j['model']==model)['source_path']).read_text()).group(1)
                source.write_text(f'''Version 1
Geometry {geometry}
Seed {seed}
PhysicsListHD qgsp-bic-hp
PhysicsListEM LivermorePol
PhysicsListRadioactiveDecay true
DecayMode ActivationDelayedDecay
DetectorTimeConstant 1e-6
StoreSimulationInfo init-only
StoreIsotopes true
Run response
response.FileName {directory}/response
response.Triggers {n}
response.Source explicit
explicit.EventList {elist}
''')
                plans.append(dict(job=name,model=model,family=key[1],stratum=stratum,events=int(n),seed=seed,source=str(source),source_sha256=sha(source),geometry=geometry,geometry_setup_sha256=sha(geometry),eventlist_sha256=sha(elist),directory=str(directory),proposal_sum_cps=float(qsum),normalization='Exact restored point activity(t)/maximum point activity * total proposal / fixed N'))
    assert sum(r['events'] for r in plans)==160000
    (out/'plan.json').write_text(json.dumps(plans,indent=2)+'\n');print('PLAN',len(plans),'pools',160000,'decays',flush=True)

def run(r):
    d=Path(r['directory']);receipt=d/'receipt.json'
    if receipt.exists():return json.loads(receipt.read_text())
    assert not (d/'started.json').exists(),('Do not silently reuse a seed',r['job'])
    assert sha(r['source'])==r['source_sha256'] and sha(d/'events.dat')==r['eventlist_sha256']
    start=time.time();(d/'started.json').write_text(json.dumps({'seed':r['seed'],'started':start}))
    with (d/'run.log').open('w') as log:
        p=subprocess.run([str(P/'runtime/cosima'),'-s',str(r['seed']),'-z',r['source']],cwd=d,env=env(),stdout=log,stderr=subprocess.STDOUT)
    sims=list(d.glob('response*.sim.gz'));assert p.returncode==0 and len(sims)==1
    out={**r,'status':'TRANSPORT_COMPLETE','sim':str(sims[0]),'sim_bytes':sims[0].stat().st_size,'seconds':time.time()-start}
    receipt.write_text(json.dumps(out,indent=2)+'\n');print(r['job'],r['events'],'complete',round(out['seconds'],1),flush=True);return out

if __name__=='__main__':
    if sys.argv[1]=='plan':plan()
    elif sys.argv[1]=='run':
        plans=json.loads((P/'responses/plan.json').read_text())
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:out=list(pool.map(run,plans))
        (P/'responses/transport_complete.json').write_text(json.dumps(out,indent=2)+'\n')
