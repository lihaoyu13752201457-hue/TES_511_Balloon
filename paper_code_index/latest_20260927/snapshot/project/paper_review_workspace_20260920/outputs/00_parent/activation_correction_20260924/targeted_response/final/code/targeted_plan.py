"""Bounded fixed-N explicit-state sampling, separate geometry/family pools."""
from targeted_environment import *
import numpy as np, collections, re, csv,sys

def main():
    registry=json.loads((T/'physical_registry.json').read_text());rates=np.load(T/'physical_rates_81nodes.npy');jobs=json.loads((O/'data/runtime_jobs.json').read_text())
    batch=sys.argv[1] if len(sys.argv)>1 else 'batch01'
    assert batch in ('batch01','batch02')
    out=T/batch;out.mkdir(exist_ok=True);entries=[]
    for model in ['a','b']:
        for family in sorted({j['family'] for j in jobs if j['model']==model}):
            pts=json.loads((O/'data'/f'points_{model}_{family}.json').read_text())['points']
            byroot=collections.defaultdict(list)
            for p in pts:byroot[p['za']].append(p)
            for c in registry:
                if (c['model'],c['family'],c['policy'])!=(model,family,'targeted'):continue
                pp=byroot[c['root_za']];norm=sum(p['source_blocks'] for p in pp);bound=float(rates[:,c['category_id']].max())
                for p in pp:
                    s=('rare' if c['state']=='Ho156' else 'ec' if c['za'] in (68158,67158,73176) else 'missing_bgo' if p['volume'].startswith(('BGO_','AA_BGO_','SH3_BGO40_')) else 'missing_other')
                    entries.append(dict(model=model,family=family,stratum=s,category=c['category_id'],point=p['point_id'],proposal=bound*p['source_blocks']/norm))
    pools=collections.defaultdict(list)
    for e in entries:pools[e['model'],e['stratum'],e['family']].append(e)
    # Each model receives 200000 production histories. Relative allocation is
    # chosen before seeing any selected result. Strata protect non-BGO sources.
    budgets={m:dict(missing_bgo=80000,missing_other=40000,ec=40000,rare=40000) for m in ['a','b']}
    if batch=='batch02':
        assert (T/'batch01/compact_summary.json').exists()
        budgets={'a':dict(missing_bgo=1100000,missing_other=100000,ec=140000,rare=40000),'b':dict(missing_bgo=160000,missing_other=30000,ec=0,rare=28000)}
    previous={(r['model'],r['stratum'],r['family']):r['events'] for r in json.loads((T/'batch01/plan.json').read_text())} if batch=='batch02' else {}
    plan=[]
    for model in ['a','b']:
        for stratum,budget in budgets[model].items():
            if not budget:continue
            keys=sorted(k for k in pools if k[:2]==(model,stratum));q=np.array([sum(e['proposal'] for e in pools[k]) for k in keys])
            assert len(keys)>0
            if batch=='batch01':target=budget*np.sqrt(q)/np.sqrt(q).sum()
            else:
                # Equalise the largest possible weight in a zero-result pool.
                old=np.array([previous.get(k,0) for k in keys]);target=np.maximum(0,(budget+old.sum())*q/q.sum()-old)
                target*=budget/target.sum()
            counts=np.floor(target).astype(int)
            counts[np.argsort(-(target-counts))[:budget-counts.sum()]]+=1
            for key,n in zip(keys,counts):
                if n==0:continue
                family=key[2];items=pools[key];q=np.array([e['proposal'] for e in items]);qsum=float(q.sum());seed=1690259101+len(plan)+(1000 if batch=='batch02' else 0)
                rng=np.random.default_rng(seed);pick=rng.choice(len(items),size=int(n),p=q/qsum)
                cats=np.array([items[i]['category'] for i in pick],dtype='i4');pointids=np.array([items[i]['point'] for i in pick],dtype='i4')
                name=f'{model}_{stratum}_{family}';directory=out/name;directory.mkdir(exist_ok=True)
                pts=json.loads((O/'data'/f'points_{model}_{family}.json').read_text())['points'];ev=[]
                for i,(cat,pid) in enumerate(zip(cats,pointids)):
                    c=registry[cat];p=pts[pid];ev.append(f'{i} 0 {c["za"]} {c["exc_keV"]:.12g} {i+1} {p["x"]:.12g} {p["y"]:.12g} {p["z"]:.12g} 0 0 1 0 0 0 0.000001')
                elist=directory/'events.dat';elist.write_text('\n'.join(ev)+'\n')
                np.savez_compressed(directory/'draws.npz',category=cats,point_id=pointids)
                old=next(j for j in jobs if j['model']==model);geometry=re.search(r'(?m)^Geometry\s+(.*)$',Path(old['source_path']).read_text()).group(1)
                source=directory/'run.source';source.write_text(f'''Version 1
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
                r=dict(job=name,model=model,family=family,stratum=stratum,events=int(n),seed=seed,source=str(source),source_sha256=sha(source),geometry=geometry,geometry_setup_sha256=sha(geometry),eventlist_sha256=sha(elist),directory=str(directory),proposal_sum_cps=qsum,normalization='rate(category,t)/max_rate(category) * proposal_sum/N; retained source-point multiplicity sampled within each family and geometry')
                (directory/'plan.json').write_text(json.dumps(r,indent=2)+'\n');plan.append(r)
    assert all(sum(r['events'] for r in plan if r['model']==m)==sum(budgets[m].values()) for m in ['a','b'])
    (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    print('prepared',len(plan),'separate pools',sum(r['events'] for r in plan),'histories',flush=True)
if __name__=='__main__':main()
