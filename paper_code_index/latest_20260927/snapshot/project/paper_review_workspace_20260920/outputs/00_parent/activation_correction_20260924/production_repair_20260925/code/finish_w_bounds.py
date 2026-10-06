from pathlib import Path
import numpy as np,json,math,csv
from scipy.optimize import minimize_scalar
from scipy.special import log_ndtr
C=Path(__file__).resolve().parents[1];F=C/'final';tau=1e-6
r=json.loads((C/'data/W176_preliminary_rates.json').read_text());old=json.loads((F/'data/RESULTS.json').read_text())['models'];out={}
# Any selected energy <= true deposited energy + sum max(noise_pixel,0).
# Bound all 2256 pixels independently: never assume only a few are hit.
sigma=.5/2.3548200450309493;pixels=2256;energy_upper=270.;gap=510.5-energy_upper
logmgf=lambda s:np.logaddexp(math.log(.5),.5*(s*sigma)**2+log_ndtr(s*sigma))
opt=minimize_scalar(lambda s:pixels*logmgf(s)-s*gap,bounds=(0,100),method='bounded');pnoise=math.exp(opt.fun)
for model in ('a','b'):
 w=r[model]['W176_max_cps'];bg=r[model]['existing_rate_summary']['all_positive']['max_cps'];tes=r[model]['existing_rate_summary']['bgo_free_TES']['max_cps'];sin=2.4e-4*19.716576335319342
 lam=bg+w+sin;c=math.expm1(lam*tau)/lam
 pairs_w_tes=2*w*tes*c;pairs_w_w=w*w*c
 db=2*pairs_w_tes+pairs_w_w+w*pnoise
 p_signal=min(1.,2*w*c);dS=20*86400*sin*p_signal;dB=20*86400*db
 v=old[model]['mission_20day'];Ns=v['Ns'];Nb=v['Nb'];flo=v['F3']*math.sqrt(max(0,1-dB/Nb))/(1+dS/Ns);fhi=v['F3']*math.sqrt(1+dB/Nb)/(1-dS/Ns)
 out[model]={'W176_rate_max_cps':w,'all_rate_upper_cps':lam,'TES_eligible_rate_upper_cps':tes,'connected_W_TES_pair_rate_bound_cps':pairs_w_tes,'connected_W_W_pair_rate_bound_cps':pairs_w_w,'background_abs_change_rate_bound_cps':db,'background_20day_abs_change_bound_counts':dB,'signal_photon_connection_probability_bound':p_signal,'signal_20day_abs_change_bound_counts':dS,'F3_central_conditional':v['F3'],'F3_interval_known_level_unknown_branching_only':[flo,fhi],'F3_relative_max_change':max(1-flo/v['F3'],fhi/v['F3']-1),'assumptions':['Rates from the repaired retained production inventory and combined response catalog are held fixed; finite production and nuclear-model uncertainties are separate.','Arbitrary normalized feeding among ENSDF W176 EC levels <=195.1 keV, with conservative 270 keV total visible-energy cap.','No claim to bound hypothetical unobserved higher-energy feeding, radiative EC, or source production uncertainties.','All W decays count as detector-positive arrivals; no shielding efficiency or BGO veto probability reduction applied.','Poisson nearest-neighbour transitive grouping with tau=1 us; all existing background arrivals may mediate connections.','Conservative bound includes removing pre-existing selected groups, creating new groups, W-W overlap and finite 500eV Gaussian tails.','Existing Ta176 daughter inventory and response are unchanged; no second Ta injection.']}
 print(model,out[model],flush=True)
result={'method':'Poisson connected-component marked-pair envelope, not an extra Poisson replay or fitted branch centre','pair_derivation':'For a Palm arrival in a stationary Poisson process of rate L, the mean number of other arrivals in its transitive tau-component is 2(expm1(L*tau)). Mark thinning gives connected W-TES cross pairs per second 2*w*rT*expm1(L*tau)/L and unordered W-W pairs w*w*expm1(L*tau)/L. Each altered old selected group and each new mixed selected group has a W-TES pair; W-only selected groups require a W-W pair, except the bounded noise tail.','isolated_noise_bound':{'pixels':pixels,'sigma_keV':sigma,'true_visible_energy_cap_keV':energy_upper,'chernoff_tail_probability_upper':pnoise,'exponent':opt.fun,'optimizing_s':opt.x},'models':out}
(C/'data/W176_bounds.json').write_text(json.dumps(result,indent=2)+'\n')
