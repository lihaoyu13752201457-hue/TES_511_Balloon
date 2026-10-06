from pathlib import Path
import os,json,math
H=Path(__file__).resolve().parents[1]
os.environ['MPLCONFIGDIR']=str(H/'tmp/mpl');os.environ['MPLBACKEND']='Agg'
import numpy as np
import pandas as pd
from scipy.linalg import expm
from scipy import stats,integrate
import matplotlib.pyplot as plt
r=json.loads((H/'reports/reference_validation.json').read_text());eta=r['mosaic_sigma_rad'];theta=r['thetaB_rad'];Q=r['Q_cm_inv'];sigma=r['rate_peak_cm_inv']
ledger=json.loads((H/'reports/run_ledger.json').read_text());xs=pd.read_csv(H/'runs/combined_off0/em_coefficients.csv');muEM=float(xs.mu_cm_inv.sum())
def rate(off):
 a=theta+off;b=math.cos(theta)*math.cos(a);x=b/eta**2
 return Q*math.cos(theta)/eta**2*math.exp(-2*math.sin(off/2)**2/eta**2)*(1+1/(8*x)+9/(128*x*x))/math.sqrt(2*math.pi*x)
def expected(s):
 off=math.radians(s['offset']/3600);c0=math.cos(off);c1=math.cos(off-2*theta);a=rate(off)/c0;b=rate(-off)/c1;t=s['thickness']/10
 mu=0 if s['physics']=='laue_only' else .4 if s['physics']=='loss' else muEM
 if s['physics']=='em_only':a=b=0
 mat=np.array([[-a-mu/c0,b],[a,-b-mu/c1]])
 T,R=expm(mat*t)@np.array([1.,0.]);return float(R),float(T),math.exp(-(a+mu/c0)*t),float(a*t)
rows=[];validation=[];summaries={}
for s in ledger['valid_runs']:
 name=s['name'];p=H/'runs'/name;e=pd.read_csv(p/'events.csv');su=json.loads((p/'summary.json').read_text());summaries[name]=su
 assert len(e)==s['n'] and e.event_id.nunique()==s['n'];assert (e.R_clean+e.T_coherent+e.other_gamma+e.no_gamma==1).all()
 row={k:s[k] for k in ['name','model','physics','geometry','thickness','offset','step','point','n','seed']};row['area_cm2']=su['incident_area_cm2']
 for col in ['R_clean','T_coherent','T_uncollided','other_gamma','no_gamma','n_diffraction','focus_photons','focus_clean_photons','edep_keV','escape_keV']:row[col]=float(e[col].mean())
 row['n_ge2_diffraction_fraction']=float((e.n_diffraction>=2).mean());row['max_energy_residual_keV']=su['max_energy_residual_keV'];row['max_bragg_residual']=su['max_bragg_residual'];row['max_reciprocal_relative_residual']=su['max_reciprocal_relative_residual']
 row['Aeff_cm2']=su['incident_area_cm2']*row['focus_photons'];row['Aeff_SE_cm2']=su['incident_area_cm2']*float(e.focus_photons.std(ddof=1))/math.sqrt(len(e));row['Aeff_clean_cm2']=su['incident_area_cm2']*row['focus_clean_photons']
 f=pd.read_csv(p/'focal.csv');f=f[f.n_diffraction>0];within=f[f.within_18p98==1];rad=np.hypot(within.x_mm,within.y_mm)
 for q in [.5,.9,.99]:row[f'r{int(q*100)}_mm']=float(np.quantile(rad,q)) if len(rad) else None
 odd_all=f[f.n_diffraction%2==1];row['r90_all_odd_mm']=float(np.quantile(np.hypot(odd_all.x_mm,odd_all.y_mm),.9)) if len(odd_all) else None
 row['focal_laue_photons']=len(f);row['capture_any_laue_history_fraction']=float(len(within)/len(f)) if len(f) else None;odd=f[f.n_diffraction%2==1];row['capture_18p98_fraction']=float(odd.within_18p98.mean()) if len(odd) else None;row['focal_count_max_per_event']=int(e.focus_photons.max())
 if s['point'] and not name.startswith('step'):
  R,T,T0,a=expected(s);row.update(expected_R=R,expected_T=T,expected_T0=T0)
  z={'name':name,'R_expected':R,'T_expected':T,'T0_expected':T0,'R_observed':row['R_clean'],'T_observed':row['T_coherent'],'T0_observed':row['T_uncollided']}
  for key,obs,pr in [('R',row['R_clean'],R),('T',row['T_coherent'],T),('T0',row['T_uncollided'],T0)]:
   tol=5*math.sqrt(max(0,pr*(1-pr))/s['n'])+2e-4;z[key+'_residual']=obs-pr;z[key+'_tolerance']=tol;z[key+'_pass']=abs(obs-pr)<=tol;z[key+'_exact_binomial_p']=float(stats.binomtest(round(obs*s['n']),s['n'],min(1,max(0,pr))).pvalue) if 0<pr<1 else (1. if obs==pr else 0.)
  if s['physics']=='laue_only' and s['offset']==0:
   z['P_ge2_expected']=1-math.exp(-a)*(1+a);z['P_ge2_observed']=row['n_ge2_diffraction_fraction'];z['P_ge2_pass']=abs(z['P_ge2_expected']-z['P_ge2_observed'])<5*math.sqrt(z['P_ge2_expected']*(1-z['P_ge2_expected'])/s['n'])+2e-4
  validation.append(z)
 rows.append(row)
tab=pd.DataFrame(rows).sort_values('name');tab.to_csv(H/'reports/all_run_metrics.csv',index=False)
# Gates from independent point counts, plus exact-binomial significance diagnostics.
pointpass=all(x[k] for x in validation for k in x if k.endswith('_pass'))
# Pure-Laue R counts are independent between configurations; Pearson statistic excludes rare tails.
pure=[x for x in validation if x['name'].startswith('laue_only') and .001<x['R_expected']<.999]
chi=sum(50000*(x['R_observed']-x['R_expected'])**2/(x['R_expected']*(1-x['R_expected'])) for x in pure);pchi=float(stats.chi2.sf(chi,len(pure)))
val={'status':'PASS' if pointpass and pchi>.001 else 'FAIL','point_checks':validation,'pure_laue_joint_chi2':chi,'degrees_of_freedom':len(pure),'joint_p':pchi,'threshold_rule':'5 binomial SE(prediction) + 0.0002 per point; pure-Laue joint p>0.001','em_mu_cm_inv':muEM}
(H/'reports/transport_validation.json').write_text(json.dumps(val,indent=2)+'\n')
# Matched steps compare the same primary events; no pooling of the four realizations.
base=pd.read_csv(H/'runs/combined_off0/events.csv');step=[]
for name in ['step0','step0p2','combined_off0','step5']:
 e=pd.read_csv(H/'runs'/name/'events.csv');cols=['R_clean','T_coherent','T_uncollided','other_gamma','no_gamma','n_diffraction','focus_photons','focus_clean_photons'];s=summaries[name]
 step.append({'name':name,'event_count_or_category_disagreements':int((e[cols]!=base[cols]).any(axis=1).sum()),'max_abs_fraction_difference':float(abs(e[cols].mean()-base[cols].mean()).max()),'max_energy_difference_keV':float(abs(e.edep_keV-base.edep_keV).max()),'all_particle_max_step_mm':s['max_step_mm'],'all_particle_crystal_steps':s['n_crystal_steps']})
(H/'reports/step_validation.json').write_text(json.dumps({'status':'PASS' if all(x['event_count_or_category_disagreements']==0 for x in step) else 'REVIEW','rows':step,'note':'StepLimiter applies to gamma. All-particle max includes unconstrained charged secondaries; final instrumentation audit records gamma-only max.'},indent=2)+'\n')
# Conditional sampling versus independent numerical integration, not a fit to the samples.
sam=pd.read_csv(H/'reports/kernel_samples.csv');kernel=[]
for off,group in sam.groupby('offset_arcsec'):
 a=theta+math.radians(off/3600);b=math.cos(theta)*math.cos(a);k=b/eta**2;z=group.phi.to_numpy()*math.sqrt(k)
 grid=np.linspace(-12,12,24001);den=np.exp(-2*k*np.sin(grid/(2*math.sqrt(k)))**2);cdf=integrate.cumulative_trapezoid(den,grid,initial=0);cdf/=cdf[-1]
 ks=stats.kstest(z,lambda x:np.interp(x,grid,cdf));kernel.append({'offset_arcsec':off,'n':len(z),'mean_z':float(z.mean()),'std_z':float(z.std(ddof=1)),'KS_D':float(ks.statistic),'KS_p':float(ks.pvalue),'pass':bool(ks.pvalue>.001)})
ang={'status':'PASS' if all(x['pass'] for x in kernel) else 'FAIL','checks':kernel,'max_abs_Bragg_residual':float(sam.bragg_residual.abs().max()),'max_abs_reciprocal_relative_residual':float(sam.reciprocal_relative_residual.abs().max())}
(H/'reports/conditional_kernel_validation.json').write_text(json.dumps(ang,indent=2)+'\n')
# Aggregate independent seeds ONLY within the identical model and geometry.
groups=[]
for prefix in ['foot_legacy','foot_input_only','foot_dh','legacy25','ring25cut','ring22']:
 a=tab[tab.name.str.startswith(prefix+'_s')];assert len(a)==3
 scale=25 if prefix.startswith('foot_') else 1
 groups.append({'group':prefix,'n_seeds':3,'n_primaries':int(a.n.sum()),'kind':'isolated_tile_times25_equivalent_not_a_physical_ring' if scale==25 else 'invalid_legacy_geometry_reference' if prefix=='legacy25' else 'physical_ring','area_cm2':float(a.area_cm2.iloc[0]*scale),'Aeff_cm2':float(a.Aeff_cm2.mean()*scale),'Aeff_SE_cm2':float(np.sqrt((a.Aeff_SE_cm2**2).sum())/3*scale),'Aeff_clean_cm2':float(a.Aeff_clean_cm2.mean()*scale),'mean_r50_mm':float(a.r50_mm.mean()),'mean_r90_mm':float(a.r90_mm.mean()),'mean_r99_mm':float(a.r99_mm.mean()),'mean_capture_18p98_fraction':float(a.capture_18p98_fraction.mean())})
auth=json.loads(Path('/home/ubuntu/opticsim/opticsim_full/docs/optics_aeff_authority_f10m_20260611.json').read_text());old=[x for x in auth['runs'] if x['label'].startswith('a1_R2_')];assert len(old)==3
historical_radii=[]
for x in old:
 f=pd.read_csv(x['focal_crossings_csv']);f=f[f.source_tag=='laue_bfull_diffracted'];rr=np.hypot(f.x_mm,f.y_mm)
 assert len(f)==x['diffracted_focal_crossings']
 historical_radii.append(float(np.quantile(rr[rr<=auth['be_radius_mm']],.9)))
hist={'group':'historical_A1','Aeff_cm2':float(np.mean([x['aeff_cm2'] for x in old])),'Aeff_SE_cm2':float(np.sqrt(sum(x['aeff_stat_error_cm2']**2 for x in old))/3),'mean_r90_mm':float(np.mean(historical_radii)),'mean_r90_all_odd_mm':float(np.mean([x['r90_mm'] for x in old])),'n_primaries':150000,'radius_mm':auth['be_radius_mm']}
for group in groups:
 group['mean_r90_all_odd_mm']=float(tab[tab.name.str.startswith(group['group']+'_s')].r90_all_odd_mm.mean())
new=next(x for x in groups if x['group']=='ring25cut');diff={'corrected_minus_historical_cm2':new['Aeff_cm2']-hist['Aeff_cm2'],'relative_change':new['Aeff_cm2']/hist['Aeff_cm2']-1,'difference_SE_cm2':math.hypot(new['Aeff_SE_cm2'],hist['Aeff_SE_cm2']),'not_a_detector_sensitivity_recalculation':True}
comp={'historical':hist,'groups':groups,'chosen_design':'ring25cut','comparison':diff,'radius_convention':'mean of three per-seed quantiles about optical axis; mean_r90_mm uses accepted diffracted photons within 18.98 mm in every row; mean_r90_all_odd_mm uses all odd-diffraction photons reaching focal plane'}
(H/'reports/comparison.json').write_text(json.dumps(comp,indent=2)+'\n');pd.DataFrame(groups).to_csv(H/'reports/comparison.csv',index=False)
# Sharp, independent observables to distinguish the corrected direction law.
point=pd.read_csv(H/'runs/combined_off0/focal.csv');point=point[(point.n_diffraction%2==1)&(point.em_history==0)];rad=np.hypot(point.x_mm,point.y_mm)
(H/'reports/point_kernel_summary.json').write_text(json.dumps({'n_clean_odd':len(point),'d90_about_axis_cm':float(2*np.quantile(rad,.9)/10),'sigma_xy_mm':point[['x_mm','y_mm']].std().to_dict()},indent=2)+'\n')
fig,ax=plt.subplots(1,3,figsize=(15,4.8),constrained_layout=True)
for ph,mark in [('laue_only','o'),('loss','s')]:
 a=tab[(tab.physics==ph)&(tab.offset==0)&tab.point].sort_values('thickness');t=np.linspace(.1,20,300);mu=0 if ph=='laue_only' else .4
 ax[0].plot(t,.5*(-np.expm1(-2*sigma*t/10))*np.exp(-mu*t/10),label=ph+' analytic');ax[0].errorbar(a.thickness,a.R_clean,yerr=np.sqrt(a.R_clean*(1-a.R_clean)/a.n),fmt=mark,capsize=3)
ax[0].set_xlabel('Crystal thickness (mm)');ax[0].set_ylabel('Clean diffracted fraction');ax[0].set_title('Local-rate transport, independent slabs');ax[0].legend(fontsize=8)
labels=['Historical\n(overlapping)','Current replay\n(overlapping)','Corrected\n25 clipped','Corrected\n22 squares'];sel=[hist,next(x for x in groups if x['group']=='legacy25'),new,next(x for x in groups if x['group']=='ring22')]
ax[1].bar(range(4),[x['Aeff_cm2'] for x in sel],yerr=[x['Aeff_SE_cm2'] for x in sel],capsize=4,color=['#9a9a9a','#bbbbbb','#257aa8','#43a487']);ax[1].set_xticks(range(4),labels,fontsize=8);ax[1].set_ylabel('Optical effective area (cm2)');ax[1].set_ylim(0,23);ax[1].set_title('Same 18.98 mm entrance aperture')
for prefix,label in [('legacy25','Current replay'),('ring25cut','Corrected 25 clipped')]:
 rr=[]
 for i in range(3):
  f=pd.read_csv(H/'runs'/f'{prefix}_s{i}'/'focal.csv');f=f[(f.n_diffraction>0)&(f.within_18p98==1)];rr.extend(np.hypot(f.x_mm,f.y_mm))
 rr=np.sort(rr);ax[2].plot(rr,np.arange(1,len(rr)+1)/len(rr),label=label)
ax[2].set_xlim(0,15);ax[2].set_ylim(0,1.01);ax[2].set_xlabel('Radius at 10 m focal plane (mm)');ax[2].set_ylabel('Enclosed fraction within aperture');ax[2].set_title('Full crystal footprint');ax[2].legend(fontsize=9)
fig.savefig(H/'figures/physics_comparison.png',dpi=180);fig.savefig(H/'figures/physics_comparison.pdf');plt.close(fig)
print(json.dumps({'transport':val['status'],'joint_p':pchi,'conditional':ang['status'],'steps':step,'comparison':comp},indent=2))
assert val['status']=='PASS' and ang['status']=='PASS'
