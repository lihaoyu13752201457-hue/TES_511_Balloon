"""Finite-statistical bounds for the independently sampled response gaps."""
from targeted_environment import *
import collections,math,numpy as np
plans=[]
for p in sorted(T.glob('batch*/plan.json')):plans.extend(json.loads(p.read_text()))
groups=collections.defaultdict(list)
for r in plans:groups[r['model'],r['stratum'],r['family']].append(r)
pools=[]
for key,rs in groups.items():
    N=sum(r['events'] for r in rs);q=rs[0]['proposal_sum_cps'];assert all(math.isclose(q,r['proposal_sum_cps'],rel_tol=1e-12) for r in rs)
    rate=var=0.;selected=0
    for r in rs:
        report=json.loads((Path(r['directory'])/'compact.json').read_text());assert report.get('decoder')=='native_HTsim_v1'
        fraction=r['events']/N;rate+=report['day15_selected_cps']*fraction;var+=report['sumw2']*fraction*fraction;selected+=report['selected']
    pools.append(dict(model=key[0],stratum=key[1],family=key[2],N=N,selected=selected,rate_cps=rate,sumw2=var,standard_error_cps=math.sqrt(max(0,(var-rate*rate/N)*N/(N-1))) if N>1 else math.sqrt(var),max_history_weight_cps=q/N))
strata=[]
for m in ['a','b']:
    for s in sorted({r['stratum'] for r in pools if r['model']==m}):
        rr=[r for r in pools if (r['model'],r['stratum'])==(m,s)];k=sum(r['selected'] for r in rr);wmax=max(r['max_history_weight_cps'] for r in rr)
        strata.append(dict(model=m,stratum=s,N=sum(r['N'] for r in rr),selected=k,rate_cps=sum(r['rate_cps'] for r in rr),standard_error_cps=math.sqrt(sum(r['standard_error_cps']**2 for r in rr)),max_history_weight_cps=wmax,zero_count_95_bound_cps=-math.log(.05)*wmax if not k else None))
zero=[s for s in strata if not s['selected']]
# All eight predeclared geometry/stratum combinations enter multiplicity,
# including strata with observed selections. Do not select K from the data.
alpha=.05/len(strata)
summary={}
for m in ['a','b']:
    ss=[s for s in strata if s['model']==m]
    bound=sum(-math.log(alpha)*s['max_history_weight_cps'] for s in ss if not s['selected'])
    summary[m]=dict(events=sum(s['N'] for s in ss),selected=sum(s['selected'] for s in ss),targeted_rate_cps=sum(s['rate_cps'] for s in ss),targeted_statistical_SE_cps=math.sqrt(sum(s['standard_error_cps']**2 for s in ss)),zero_strata_joint95_additional_rate_bound_cps=bound,conservative_20day_additional_counts_bound=bound*20*86400)
result=dict(status='BOUNDED_TARGETED_STATISTICS_COMPLETE',transport_histories=sum(r['events'] for r in plans),validation_histories=2000,total_histories_in_authorized_cap=sum(r['events'] for r in plans)+2000,source_pools=pools,strata=strata,models=summary,zero_bound_method='For a stratum with zero selections, R(t) <= sum_f Q_f p_f and wmax=max_f(Q_f/N_f). The no-success likelihood-ratio martingale reaches at least exp(R(t)/wmax) whenever this bound fails. Ville inequality therefore permits predictable allocation and stopping while the within-pool proposal is fixed. Use alpha=0.05/8 for all eight predeclared geometry/stratum combinations, not the observed number of zero strata. R <= -log(alpha)*wmax is a simultaneous 95% upper bound for the entirely zero strata, conservative at every one of the 81 nodes. The count bound integrates the isolated-event rates, without a claim to bound the nonlinear time-overlay selection.',limitations=['Zero-stratum bound does not replace uncertainty for selected strata, which is reported separately.','W176 prompt EC radiation with unnormalized feeding scheme is not assigned a synthetic response and is outside this finite-sampling bound.','Directly produced excited states held out of the original source bank are not covered.','Finite production pools, material/transport model and other nuclear-library systematic errors are not included.'])
(T/'uncertainty.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(summary,indent=2))
