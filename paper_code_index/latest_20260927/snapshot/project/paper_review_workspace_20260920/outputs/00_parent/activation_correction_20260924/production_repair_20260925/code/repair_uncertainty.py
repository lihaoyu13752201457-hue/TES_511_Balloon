from pathlib import Path
import json,math,collections,numpy as np
P=Path(__file__).resolve().parents[1];plans=json.loads((P/'responses/plan.json').read_text());groups=collections.defaultdict(list)
for r in plans:
    report=json.loads((Path(r['directory'])/'compact.json').read_text());groups[r['model'],r['stratum']].append((r,report))
assert len(groups)==4
strata=[]
for (m,s),rr in sorted(groups.items()):
    N=sum(r['events'] for r,_ in rr);k=sum(v['selected'] for _,v in rr);w=max(r['proposal_sum_cps']/r['events'] for r,_ in rr)
    strata.append(dict(model=m,stratum=s,N=N,selected=k,rate_cps=sum(v['day15_selected_cps'] for _,v in rr),fixed_N_standard_error_cps=math.sqrt(sum(v['fixed_N_variance'] for _,v in rr)),max_history_weight_cps=w,zero_count_simultaneous95_rate_upper_cps=-math.log(.05/4)*w if k==0 else None))
models={}
for m in ['a','b']:
    rs=[r for r in strata if r['model']==m];bound=sum(r['zero_count_simultaneous95_rate_upper_cps'] or 0 for r in rs)
    models[m]=dict(valid_histories=sum(r['N'] for r in rs),selected=sum(r['selected'] for r in rs),added_day15_selected_cps=sum(r['rate_cps'] for r in rs),added_fixed_N_MC_SE_cps=math.sqrt(sum(r['fixed_N_standard_error_cps']**2 for r in rs)),zero_strata_joint95_additional_rate_upper_cps=bound,zero_strata_20day_isolated_count_upper=bound*20*86400)
out={'status':'FIXED_N_RESTORED_SOURCE_RESPONSE_STATISTICS','strata':strata,'models':models,'method':'Four geometry/material strata specified before transport, 40000 histories each. Independent production-family pools. For an entirely zero stratum, R(t) <= -ln(0.05/4)*max_f(Q_f/N_f), simultaneously for the four strata and conservatively at every mission node. All generated zero-deposit histories remain in N.','limitations':['Finite original atmospheric production, deterministic old source-bank sampling and nuclear/transport systematics are not included in response MC errors.','Zero-stratum bound refers to isolated-event rate; it is not advertised as a bound on nonlinear coincidence selection.','Source-inventory repair is separate from the previous W176 unknown-branching bound.']}
(P/'data/response_uncertainty.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(models,indent=2))
