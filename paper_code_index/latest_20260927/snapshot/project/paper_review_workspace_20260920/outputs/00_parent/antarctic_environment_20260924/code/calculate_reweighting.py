from pathlib import Path
import csv,json,math,hashlib
from collections import defaultdict
import numpy as np
O=Path(__file__).resolve().parents[1];W=O.parents[2];P=W.parent
read=lambda p:json.loads(p.read_text())
rows=lambda p:list(csv.DictReader(p.open()))
D4=W/'outputs/04_results_environments_conclusions/numeric_sync_20260920/data';D3=W/'outputs/03_mission_baseline_design/numeric_sync_20260920/data'
REF=P/'engineering/satellite_leo530_source_comparison_20260813/outputs/tables/balloon_aggregated_spectra.csv'
source={}
for name,path in [('reference',REF),('antarctic',O/'data/antarctic_native.csv'),('rebuilt_reference',O/'data/reference_native.csv')]:
 data=[r for r in rows(path) if r.get('domain','full')=='full'];source[name]={}
 for f in sorted({r['family'] for r in data}):
  rr=[r for r in data if r['family']==f];source[name][f]=(np.array([float(r['energy_keV_total']) for r in rr]),np.array([float(r['differential_flux_cm2_s_keV']) for r in rr]))
def flux(name,f,e):
 x,y=source[name][f];assert x[0]<=e<=x[-1],(name,f,e)
 return float(np.interp(e,x,y))
def ratio(name,f,e):
 den=flux('reference',f,e);assert den>0;return flux(name,f,e)/den
keys=read(D4/'activation_key_transfer.json');km={}
for k in keys:
 key=(k['family'],k['source_volume'],int(k['source_parent_ZA']));assert key not in km
 assert k['primary_records']==len(k['primary_energies_keV_total'])==k['manifest_sum_RP'];km[key]=k
prompt=read(P/'core_md/balloon511_ea_latex_drafts/meeting_revision_20260916/data/environment_prompt_500.json');delayed=rows(D3/'delayed_origins_b_500.csv');old=read(W/'outputs/00_parent/revision_20260921_AA_continuous/data/environment_kernel_500.json')
events=[]
for r in prompt:
 events.append({'stream':'prompt','family':'gamma','job_id':r['job_id'],'event_id':int(r['event_id']),'balloon_weight_cps':r['event_weight_cps'],'energies':[r['primary_energy_keV_total']],'key':None})
for r in delayed:
 key=(r['family'],r['source_volume'],int(r['source_parent_ZA']));k=km[key]
 events.append({'stream':'delayed','family':r['family'],'job_id':r['job_id'],'event_id':int(r['event_id']),'balloon_weight_cps':float(r['day15_weight_cps']),'energies':k['primary_energies_keV_total'],'key':key})
assert len(events)==130
old_ev={(r['environment'],r['job_id'],int(r['event_id'])):r for r in rows(D4/'environment_event_contributions_500.csv')}
errors=[];cc=[]
for r in events:
 orig=old_ev[('balloon_38km',r['job_id'],r['event_id'])];assert math.isclose(float(orig['balloon_weight_cps']),r['balloon_weight_cps'],rel_tol=1e-12)
 k=r['key']
 if k:
  for env,q in km[k]['ratios'].items():
   expected=old_ev[(env,r['job_id'],r['event_id'])];assert math.isclose(q,float(expected['spectrum_ratio']),rel_tol=1e-12,abs_tol=1e-15)
 ratios=[ratio('antarctic',r['family'],e) for e in r['energies']]
 q=float(np.mean(ratios));r['spectrum_ratio']=q;r['projected_rate_cps']=q*r['balloon_weight_cps']
 errors.extend(abs(ratio('rebuilt_reference',r['family'],e)-1) for e in r['energies'])
 cc.append({k:v for k,v in r.items() if k not in ['key','energies']})
agg={}
for stream in ['prompt','delayed']:
 rr=[r for r in events if r['stream']==stream];base=sum(r['balloon_weight_cps'] for r in rr);target=sum(r['projected_rate_cps'] for r in rr)
 agg[stream]={'events':len(rr),'reference_cps':base,'antarctic_cps':target,'ratio':target/base,'catalog_mcse_cps':math.sqrt(sum(r['projected_rate_cps']**2 for r in rr))}
expected=old['environment_aggregates']['balloon_38km']['known_subtotal'];assert math.isclose(agg['prompt']['reference_cps'],expected['gamma_cps'],rel_tol=1e-12);assert math.isclose(agg['delayed']['reference_cps'],expected['delayed_cps'],rel_tol=1e-12)
q=sum(v['antarctic_cps'] for v in agg.values())/sum(v['reference_cps'] for v in agg.values());Fref=old['screening'][0]['F3_screening_ph_cm2_s'];Fnew=Fref*math.sqrt(q)
# Conditional upper-transit transmission illustration, same day-15 residual column.
mu=.08736;X=3.461;lat=-77.85;dec=-29.;emin=abs(lat)+abs(dec)-90;emax=90-abs(lat-dec)
T=lambda e:math.exp(-mu*X/math.sin(math.radians(e)))
geom={'latitude_deg':lat,'source_declination_deg_approx':dec,'elevation_min_deg':emin,'elevation_max_deg':emax,'column_g_cm2':X,'mu_cm2_g':mu,'transmission_at_reference_27deg':T(27),'transmission_at_upper_transit':T(emax),'upper_transit_ratio':T(emax)/T(27)}
result={'status':'COMPUTED','scenario':'antarctic_38km_77p85S_166p67E','source_metadata':read(O/'data/native_spectra_validation.json')['metadata']['antarctic'],'components':agg,'represented_background_ratio_to_balloon':q,'scaled_non_gamma_prompt_cps':old['balloon_final_components']['non_gamma_prompt']['rate_cps']*q,'estimated_total_background_cps':old['balloon_final_total_cps']*q,'reference_F3_ph_cm2_s':Fref,'F3_screening_ph_cm2_s':Fnew,'signal_exposure_ratio_to_reference':1.,'sensitivity_assumptions':'same reference altitude history, fixed 27 deg elevation, 20 d on-source exposure, optical and signal retention response; standard atmosphere same at equal altitude; day-15 spectral reweighting, not a new mission time evolution','catalog_errors_scope':'sum of squared reweighted catalog weights only; not parent-production or source-model uncertainty','reference_spectral_reconstruction_max_relative_error_at_used_energies':max(errors),'legacy_activation_ratios_reproduced':True,'selected_records':len(events),'activation_keys':len(km),'activation_primary_records':sum(k['primary_records'] for k in keys),'transport_run':False,'raw_simulation_scan':False,'conditional_atmospheric_geometry':geom}
(O/'data/RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
with (O/'data/antarctic_event_contributions.csv').open('w') as f:
 cw=csv.DictWriter(f,fieldnames=list(cc[0]));cw.writeheader();cw.writerows(cc)
print(json.dumps(result,indent=2))
