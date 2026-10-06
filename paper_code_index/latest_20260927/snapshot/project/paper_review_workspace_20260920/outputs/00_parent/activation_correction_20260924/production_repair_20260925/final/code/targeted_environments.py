"""Update the existing spectral-screening calculation with corrected weights."""
from common import *
from targeted_environment import T
import importlib.util,os
F=O;D4=W/'outputs/04_results_environments_conclusions/numeric_sync_20260920/data'
os.environ['MPLCONFIGDIR']=str(O/'matplotlib');os.environ['MPLBACKEND']='Agg'
path=P/'engineering/geometry_optimization_20260815/65_sh3_complete_l2_solar_activity_20260820/code/build_complete_l2_solar.py'
spec=importlib.util.spec_from_file_location('targeted_environment_sources',path);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);models=module.CompleteL2Models()
old=read(ORIGINAL/'data/environment_kernel_500.json');envs=[r['environment'] for r in old['screening']];envs.insert(1,'antarctic')
reference=P/'engineering/satellite_leo530_source_comparison_20260813/outputs/tables/balloon_aggregated_spectra.csv';antarctic=W/'outputs/00_parent/antarctic_environment_20260924/data/antarctic_native.csv';spectra={}
for name,p in [('reference',reference),('antarctic',antarctic)]:
    rr=[r for r in rows(p) if r.get('domain','full')=='full'];spectra[name]={f:(np.array([float(r['energy_keV_total']) for r in rr if r['family']==f]),np.array([float(r['differential_flux_cm2_s_keV']) for r in rr if r['family']==f])) for f in {r['family'] for r in rr}}
def ratio(env,f,e):
    if env=='antarctic':
        x,y=spectra['reference'][f];xx,yy=spectra['antarctic'][f];assert x[0]<=e<=x[-1];return float(np.interp(e,xx,yy)/np.interp(e,x,y))
    return float(models.ratio(env,f,e)[0])
keys={(r['family'],r['source_volume'],r['source_parent_ZA']):r['primary_energies_keV_total'] for r in read(D4/'activation_key_transfer.json')}
for r in read(T/'environment_new_keys.json'):
    key=(r['family'],r['source_volume'],r['source_parent_ZA']);assert key not in keys;keys[key]=[r['primary_energy_keV_total']]
prompt=read(P/'core_md/balloon511_ea_latex_drafts/meeting_revision_20260916/data/environment_prompt_500.json');events=[]
for r in prompt:events.append(dict(stream='prompt',family='gamma',weight=r['event_weight_cps'],energies=[r['primary_energy_keV_total']]))
for r in read(F/'data/b/selected_origins_all.json'):
    key=(r['family'],r['source_volume'],int(r['source_parent_ZA']));events.append(dict(stream='delayed',family=r['family'],weight=float(r['day15_weight_cps']),energies=keys[key]))
bands=[]
for stream,family in [('prompt','gamma'),('delayed','p')]:
    rr=[r for r in events if (r['stream'],r['family'])==(stream,family)]
    ee=np.array([e/1000 for r in rr for e in r['energies']]);ww=np.array([r['weight']/len(r['energies']) for r in rr for e in r['energies']])
    bands.append(dict(stream=stream,family=family,energy_p10_MeV=float(module.base.weighted_quantile(ee,ww,.1)),energy_p90_MeV=float(module.base.weighted_quantile(ee,ww,.9))))
agg={};qr={}
for env in envs:
    a={}
    for stream in ['prompt','delayed']:
        rr=[r for r in events if r['stream']==stream];weights=[r['weight']*np.mean([ratio(env,r['family'],e) for e in r['energies']]) for r in rr]
        a[stream]=dict(rate_cps=float(sum(weights)),catalog_sumw2=float(np.dot(weights,weights)),records=len(rr))
    a['represented_rate_cps']=a['prompt']['rate_cps']+a['delayed']['rate_cps'];agg[env]=a
direct=read(F/'data/b/direct_statistics.json')['compton_trajectory_veto'];assert math.isclose(agg['balloon_38km']['delayed']['rate_cps'],direct['delayed']['rate'],rel_tol=1e-12)
mission=read(F/'data/RESULTS.json')['models']['b']['mission_20day'];curve=rows(F/'data/b/mission_81nodes.csv');tr=rows(F/'data/b/direct_81nodes.csv')
noatm=np.array([float(r['signal_final_rate_cps'])/float(t['transmission']) for r,t in zip(curve,tr)]);effective_transmission=mission['Ns']/np.trapezoid(noatm,dx=21600)
screen=[]
for env in envs:
    q=agg[env]['represented_rate_cps']/agg['balloon_38km']['represented_rate_cps'];f=mission['F3']*math.sqrt(q)*(1 if env in ('balloon_38km','antarctic') else effective_transmission)
    before=next((r for r in old['screening'] if r['environment']==env),None)
    if env=='antarctic':before={'represented_background_ratio_to_balloon':3.294,'F3_screening_ph_cm2_s':read(W/'outputs/00_parent/antarctic_environment_20260924/data/RESULTS.json')['F3_screening_ph_cm2_s']}
    screen.append(dict(environment=env,ratio=q,F3=f,prompt_cps=agg[env]['prompt']['rate_cps'],delayed_cps=agg[env]['delayed']['rate_cps'],old_ratio=before['represented_background_ratio_to_balloon'],old_F3=before['F3_screening_ph_cm2_s']))
result=dict(status='UPDATED_EXISTING_SPECTRAL_SCREENING_NOT_NEW_ENVIRONMENT_TRANSPORT',screening=screen,effective_balloon_signal_transmission=float(effective_transmission),origin_keys=len(keys),newly_joined_keys=read(T/'environment_new_keys.json'),records=len(events),limitations=['Retains the original day-15 template and angular response approximation, including aggregate non-gamma prompt scaling.','The main result zero-count bounds and nuclear-data limitations are not converted into complete environment systematic intervals.'])
result['primary_energy_bands']=bands
save(F/'data/environment_results.json',result);write(F/'data/environment_comparison.csv',screen);print(json.dumps(screen,indent=2))
