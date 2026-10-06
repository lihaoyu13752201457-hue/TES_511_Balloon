"""Independent closed-form and fast-level elimination checks."""
from decay_kernel import *
data=NuclearData();reports=[]
for root,daughter in [('Zn62','Cu62'),('Sm141','Pm141'),('Er156','Ho156')]:
    model=[]
    for cut in [1e-5,1e-4,1e-3]:
        k=LineageKernel(data,root,fast_cut_s=cut)
        finite=k.finite_counts(131.336995731,1e-6)[k.idx[daughter]]
        mission=k.mission(np.arange(81)*21600,np.ones(81),1e-6)[60,k.idx[daughter]]
        model.append({'cut_s':cut,'finite_count_per_Bq':float(finite),'day15_rate_per_production_cps':float(mission),
                      'ratio':float(mission/finite)})
    span=(max(r['ratio'] for r in model)-min(r['ratio'] for r in model))/model[1]['ratio']
    reports.append({'root':root,'daughter':daughter,'fast_cut_checks':model,'relative_spread':span})
    assert span<5e-4,(root,span)
k=LineageKernel(data,'Zn62')
T=131.336995731;t=15*86400.;l1=1/data.tau('Zn62',True);l2=1/data.tau('Cu62',True)
closed_mission=1-(l2*math.exp(-l1*t)-l1*math.exp(-l2*t))/(l2-l1)
computed=k.mission([0,t],[1,1],1e-6)[-1,k.idx['Cu62']]
native_tau=data.tau('Cu62');closed_finite=T-native_tau*(-math.expm1(-T/native_tau))
finite=k.finite_counts(T,1e-6)[k.idx['Cu62']]
closed={'root':'Zn62','daughter':'Cu62','mission_analytic':closed_mission,'mission_computed':float(computed),
        'finite_analytic':closed_finite,'finite_computed':float(finite),'native_child_fraction':float(finite/T)}
assert abs(computed/closed_mission-1)<1e-6
assert abs(finite/closed_finite-1)<1e-6
out={'closed_form':closed,'fast_level_precision':reports,'note':'Checks concern the installed-library chain kernel, not independent validation of the nuclear evaluation or transport efficiency.'}
(D/'kernel_precision_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
