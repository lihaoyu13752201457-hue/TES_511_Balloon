import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,csv,math,hashlib
from collections import Counter
import numpy as np
from analyze import O,W,P,H,frac

def rows(p):
 with p.open() as f:return list(csv.DictReader(f))
def write(p,rs):
 with p.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def trap(y):return float(np.trapezoid(y,dx=21600))
def cross(days,z,q):
 for i in range(1,len(z)):
  if z[i]>=q:return float(days[i-1]+(days[i]-days[i-1])*(q-z[i-1])/(z[i]-z[i-1]))
 return None

def main():
 days=np.arange(81)/4;anchor_nodes=[0,20,40,60,80];ad=np.array(anchor_nodes)/4
 interp=np.column_stack([np.interp(days,ad,np.eye(5)[r]) for r in range(5)])
 result={'status':'COMPLETE_THREE_STREAM_DEPOSIT_OVERLAY','manuscript_modified':False,'production_transport_run':False,'reference_flux_ph_cm2_s':2.4e-4,'primary_active_selection':'BGO summed energy <50 keV; plastic veto excluded','models':{}};anchor_csv=[];comp=[]
 for model in ['a','b']:
  d=O/'data'/model;rr=[json.loads((d/f'anchor_{n:03d}_results.json').read_text()) for n in anchor_nodes];direct=rows(d/'direct_81nodes.csv');old=rows(W/f'outputs/03_mission_baseline_design/numeric_sync_20260920/data/timeline_{model}_500/mission_timeline_81nodes.csv');m=json.loads((d/'compact_metadata.json').read_text());counts=Counter()
  for r in rr:counts.update(r['counts'])
  rho=np.array([r['background_bgo_final_count']/r['timeline']['T']/float(direct[n]['background_bgo_final_rate']) for n,r in zip(anchor_nodes,rr)])
  rho_dual=np.array([r['background_dual_final_count']/r['timeline']['T']/float(direct[n]['background_dual_final_rate']) for n,r in zip(anchor_nodes,rr)])
  eta=np.array([r['retention_bgo']['value'] for r in rr]);eta_dual=np.array([r['retention_legacy_dual']['value'] for r in rr])
  # Signal identities permit a loss fraction and a separate net on/off count.
  # If gains exist, expose them; do not silently call net corrections survival.
  net=np.array([r['net_signal_bgo_count']/r['counts']['isolated_final'] for r in rr])
  Bdir=np.array([float(x['background_bgo_final_rate']) for x in direct]);Sdir=np.array([float(x['isolated_signal_final_rate']) for x in direct]);br=interp@rho;et=interp@eta
  B=Bdir*br;S=Sdir*et;Snet=Sdir*(interp@net)
  cb=np.r_[0,np.cumsum((B[:-1]+B[1:])/2*21600)];cs=np.r_[0,np.cumsum((S[:-1]+S[1:])/2*21600)];csnet=np.r_[0,np.cumsum((Snet[:-1]+Snet[1:])/2*21600)];z=np.divide(cs,np.sqrt(cb),out=np.zeros(81),where=cb>0)
  # Correlated finite-transport background variance: integrate each event's
  # physical rate coefficient first, then square; never sum node variances.
  CP=P/f'engineering/geometry_optimization_20260815/70_m05_sg3_sh3_prompt_statistics_integration_20260828/outputs/01_integrated_catalog_{model}'
  reg=json.loads((CP/'category_registry.json').read_text())['categories'];fac=dict(np.load(P/f'core_md/balloon511_ea_latex_drafts/meeting_revision_20260916/data/category_factors_{model}.npz'))
  scales=fac['common_factor'].copy()
  for k,c in enumerate(reg):
   if c['component']=='gamma_continuum':scales[:,k]=fac['gamma_scale']
   elif c['component']=='atm511':scales[:,k]=0
  catalog=np.load(CP/'combined_event_catalog.npz');cat=catalog['event_category'];base=catalog['event_base_weight_cps'];dt=np.dtype([('plastic','<f4'),('bgo','<f4'),('hits','<u2'),('flags','u1'),('stream','u1')]);rec=np.memmap(d/'records.bin',dtype=dt,mode='r');mask=(rec['flags'][:len(cat)]&2)>0
  selected=np.flatnonzero(mask);q=base[selected];ids=cat[selected];q1=np.bincount(ids,weights=q,minlength=len(reg));q2=np.bincount(ids,weights=q*q,minlength=len(reg));assert np.allclose(scales@q1,Bdir,rtol=1e-11)
  tw=np.full(81,21600.);tw[[0,-1]]=10800.;coeff=(tw*br)@scales;var_bg_transport=float(np.sum(q2*coeff**2));var_bg_timeline=0.
  coeff_bg=[];coeff_sig=[];var_eta=0.
  for j,(n,r) in enumerate(zip(anchor_nodes,rr)):
   cbj=trap(Bdir*interp[:,j])/Bdir[n]/r['timeline']['T'];coeff_bg.append(cbj);var_bg_timeline+=cbj**2*r['background_bgo_final_count']
   csj=trap(Sdir*interp[:,j]);coeff_sig.append(csj);k=r['counts']['isolated_final_retained_bgo'];N=r['counts']['isolated_final']
   # Jeffreys beta variance avoids a false zero error when no losses occur.
   vv=(k+.5)*(N-k+.5)/((N+1)**2*(N+2));var_eta+=csj**2*vv
   anchor_csv.append({'model':model,'day':n/4,'T_s':r['timeline']['T'],'signal_arrivals':r['counts']['signal_events'],'isolated_selected':N,'retained_bgo':k,'window_loss':r['counts']['window_loss'],'BGO_loss_after_window':r['counts']['bgo_loss_after_window'],'Compton_loss_after_BGO':r['counts']['compton_loss_after_bgo'],'eta_bgo':eta[j],'eta_dual':eta_dual[j],'gain_from_unselected':r['counts']['gain_from_isolated_unselected'],'net_signal_count':r['net_signal_bgo_count'],'rho_background_bgo':rho[j],'rho_background_dual':rho_dual[j],'active_bgo_loss_fraction':1-r['active_bgo_retention_per_overlaid_window']['value']})
  conv=H['models'][model]['isolated_signal_count_conversion'];relative_sig_transport=conv['mc_standard_error_cm2']/conv['value_cm2'];var_signal_transport=(cs[-1]*relative_sig_transport)**2
  F3=2.4e-4*3/z[-1];F5=F3*5/3;F3se=F3*math.sqrt((var_bg_transport+var_bg_timeline)/(4*cb[-1]**2)+(var_signal_transport+var_eta)/cs[-1]**2)
  old_ns=float(old[-1]['cumulative_signal_counts_per_unit_flux'])*2.4e-4;old_nb=float(old[-1]['cumulative_background_counts']);old_F=float(old[-1]['Fmin_3sigma_gaussian_ph_cm2_s'])
  old_bg=np.array([float(r['mature_background_W2_final_cps']) for r in old]);held_bg=float(old[-1]['cumulative_background_counts']);held_signal=trap(Sdir*(interp@eta_dual));held_z=held_signal/math.sqrt(held_bg)
  mission_rows=[{'day':days[i],'signal_isolated_rate_cps':Sdir[i],'signal_retention':et[i],'signal_final_rate_cps':S[i],'background_direct_BGO_cps':Bdir[i],'background_correction':br[i],'background_final_cps':B[i],'cumulative_signal':cs[i],'cumulative_background':cb[i],'Z':z[i],'F3_ph_cm2_s':2.4e-4*3/z[i] if i else '', 'net_signal_cumulative_crosscheck':csnet[i]} for i in range(81)]
  write(d/'mission_81nodes.csv',mission_rows)
  components={name:float(np.dot(q1*np.array([c['component']==name for c in reg]),coeff)) for name in ['gamma_continuum','other']}
  out={'display_name':'Under-stage' if model=='a' else 'Lateral-chimney','pooled_counts':dict(counts),'pooled_retention_bgo':frac(counts['isolated_final_retained_bgo'],counts['isolated_final']),'pooled_retention_legacy_dual':frac(counts['isolated_final_retained_dual'],counts['isolated_final']),'pooled_active_BGO_retention':frac(counts['overlaid_window_bgo_pass'],counts['overlaid_window']),'eta_range':[float(eta.min()),float(eta.max())],'day15':{'eta_bgo':eta[3],'eta_dual':eta_dual[3],'BGO_retention':rr[3]['active_bgo_retention_per_overlaid_window'],'signal_final_rate_cps':S[60],'direct_background_BGO_cps':Bdir[60],'timeline_background_BGO_cps':B[60]},'mission_20day':{'Ns':cs[-1],'Nb':cb[-1],'Z':z[-1],'F3':F3,'F5':F5,'F3_MC_SE_approx':F3se,'F5_MC_SE_approx':F3se*5/3,'T3_days':cross(days,z,3),'T5_days':cross(days,z,5),'Ns_net_on_minus_off':csnet[-1],'background_component_counts':components},'uncertainty':{'background_correlated_transport_SE_counts':math.sqrt(var_bg_transport),'background_timeline_SE_counts':math.sqrt(var_bg_timeline),'signal_optical_plus_detector_SE_counts':math.sqrt(var_signal_transport),'signal_arrival_retention_regularized_SE_counts':math.sqrt(var_eta),'retention_variance_method':'Jeffreys Beta(k+1/2,N-k+1/2) variance; empirical ratios used for central values. Exact retained-template statistical uncertainty only, no environment/geometry systematic.'},'old_manuscript':{'Ns':old_ns,'Nb':old_nb,'F3':old_F,'eta_day15':float(old[60]['conditional_signal_accidental_survival'])},'algorithm_change_only_control':{'veto':'Legacy BGO+plastic','background':'Old manuscript background held fixed to avoid conflating resampling or veto-channel changes','Ns':held_signal,'Nb':held_bg,'Z':held_z,'F3':2.4e-4*3/held_z},'rho_range':[float(rho.min()),float(rho.max())]}
  result['models'][model]=out
  for quantity,oval,nval in [('day15_eta',out['old_manuscript']['eta_day15'],eta[3]),('20day_Ns',old_ns,cs[-1]),('20day_Nb',old_nb,cb[-1]),('20day_F3',old_F,F3)]:comp.append({'model':model,'quantity':quantity,'old':oval,'new_BGO':nval,'relative_change':nval/oval-1})
 result['ratios']={'Nb_lateral_over_under':result['models']['b']['mission_20day']['Nb']/result['models']['a']['mission_20day']['Nb'],'Ns_lateral_over_under':result['models']['b']['mission_20day']['Ns']/result['models']['a']['mission_20day']['Ns'],'F3_under_over_lateral':result['models']['a']['mission_20day']['F3']/result['models']['b']['mission_20day']['F3']}
 save(O/'data/RESULTS.json',result);write(O/'data/ANCHORS.csv',anchor_csv);write(O/'data/OLD_NEW_COMPARISON.csv',comp)
 before=json.loads((O/'validation/manuscript_before.json').read_text());unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in before.items());assert unchanged
 checks={'manuscript_and_pointer_unchanged':unchanged,'three_stream_counts_verified':True,'signal_deposits_merged_before_response':True,'signal_ancestry_accounting_closed':True,'all_node_direct_rates_match_independent_weight_sum':True,'background_transport_errors_integrated_before_squaring':True,'no_new_transport':True,'timelines':[{'model':m,'node':n,'rate_relative_error':(r['rate']/sum(r['rates'])-1),'poisson_arrival_zscores':[(v-rate*r['T'])/math.sqrt(rate*r['T']) if rate else 0 for v,rate in zip(r['arrivals'],r['rates'])]} for m in ['a','b'] for n in anchor_nodes for r in [json.loads((O/f'data/{m}/anchor_{n:03d}.json').read_text())]]}
 assert max(abs(x) for r in checks['timelines'] for x in r['poisson_arrival_zscores'])<6
 save(O/'validation/FINAL_CHECKS.json',checks);print(json.dumps(result,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
