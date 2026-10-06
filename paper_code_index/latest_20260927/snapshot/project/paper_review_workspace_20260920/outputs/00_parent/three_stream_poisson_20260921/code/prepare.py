import sys
sys.dont_write_bytecode=True
from pathlib import Path
import importlib.util,json,math,csv
import numpy as np
O=Path(__file__).resolve().parents[1];W=O.parents[2]
def load():
 p=W/'outputs/03_mission_baseline_design/numeric_sync_20260920/code/run_numeric_sync.py'
 spec=importlib.util.spec_from_file_location('retained_adapter',p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);m.O=O;return m

def main(model):
 m=load();r=m.Replay(model);d=O/'data'/model;d.mkdir(exist_ok=True)
 s=dict(np.load(m.S/'data'/f'signal_{model}_catalog.npz'));nb=len(r.a['hit_count']);ns=len(s['event_id']);a=r.a
 # Original BGO-only survivors rejected by the plastic channel need the same
 # cached isolated response and the unchanged pixel-centre/vertex Compton test.
 bgo_final=(a['w2_flags']&16)>0
 missing=np.flatnonzero(((a['w2_flags']&4)>0)&((a['w2_flags']&8)==0))
 identity=dict(np.load(m.D/f'identity_{model}.npz'));jobs=m.read(m.D/f'identity_{model}_jobs.json');extra=[]
 for i in missing:
  j=jobs[int(identity['event_job'][i])];eid=int(identity['event_id'][i]);measure=[]
  for h in range(int(a['hit_start'][i]),int(a['hit_start'][i]+a['hit_count'][i])):
   layer=int(a['hit_layer'][h]);uid=f"TP_L{layer}_{int(a['hit_code'][h])-layer*100000:05d}"
   z=(m.R.a_background_normal if model=='a' else m.R.normal)('sg3b' if model=='a' else 'sh3_optv3',j['mode'],j['family'],j['batch_id'],int(j['seed']),j['job_id'],eid,uid)
   e=float(a['hit_energy_keV'][h])+r.sigma_keV*z
   if e>=.3:measure.append(m.PixelMeasurement(uid,e))
  assert abs(sum(x.energy_keV for x in measure)-a['measured_total_keV'][i])<4e-5
  keep=r.pixel.classify(measure)[0];bgo_final[i]=keep
  extra.append({'event_index':int(i),'pixel_compton_keep':bool(keep)})
 dtype=np.dtype([('plastic','<f4'),('bgo','<f4'),('hits','<u2'),('flags','u1'),('stream','u1')]);record=np.zeros(nb+ns,dtype=dtype)
 for name,key in [('plastic','plastic_keV'),('bgo','bgo_keV'),('hits','hit_count')]:record[name]=np.r_[a[key],s[key]]
 # flags: bit1 pre-window; bit2 BGO+Compton; bit4 legacy dual-veto+Compton.
 record['flags'][:nb]=((a['w2_flags']&1)>0).astype('u1')+2*bgo_final.astype('u1')+4*((a['w2_flags']&16)>0).astype('u1')
 record['flags'][nb:]=s['narrow_pre'].astype('u1')+6*s['narrow_final'].astype('u1')
 catstream=np.array([int(c['stream']=='delayed') for c in r.categories],dtype='u1');record['stream'][:nb]=catstream[a['event_category']];record['stream'][nb:]=2
 record.tofile(d/'records.bin')
 metadata={'model':model,'background_records':nb,'signal_records':ns,'optical_area_cm2':m.H['optical_area_cm2'],'Fref':2.4e-4,'input_hashes':r.input_hashes,'signal_sha256':m.sha(m.S/'data'/f'signal_{model}_catalog.npz'),'parameters':{'tau_s':1e-6,'FWHM_keV':.5,'pixel_threshold_keV':.3,'window_keV':[510.5,511.5],'bgo_threshold_keV':50.,'reference_elevation_deg':27.},'bgo_only_additional_candidates':extra,'anchors':{}}
 direct=[]
 for node in range(81):
  weights=np.zeros(nb+ns)
  for k,(st,cnt) in enumerate(zip(r.starts,r.counts)):weights[st:st+cnt]=r.event_weights_for_category(k,node)
  assert np.all(weights>=0) and np.all(weights[:nb][a['event_component']==2]==0)
  bg=float(weights[:nb].sum());assert math.isclose(bg,r.category_rate_matrix[node].sum(),rel_tol=1e-11)
  transmission=float(r.atmosphere[node]['T_atm_511'])**(1/math.sin(math.radians(27)))
  signalrate=2.4e-4*m.H['optical_area_cm2']*transmission;weights[nb:]=signalrate/ns
  direct.append({'node':node,'day':node/4,'transmission':transmission,'signal_input_rate':signalrate,'isolated_signal_final_rate':signalrate*float(s['narrow_final'].mean()),'background_bgo_final_rate':float(weights[:nb][bgo_final].sum()),'background_dual_final_rate':r.direct_stats(node,m.E.FINAL_WINDOW,m.E.FINAL_STAGE)['rate_cps']})
  if node in m.E.ANCHOR_NODES:
   weights.tofile(d/f'weights_{node:03d}.bin');metadata['anchors'][str(node)]={**direct[-1],'total_background_rate':bg,'prompt_rate':float(weights[:nb][record['stream'][:nb]==0].sum()),'delayed_rate':float(weights[:nb][record['stream'][:nb]==1].sum())}
 m.write(d/'direct_81nodes.csv',direct);m.save(d/'metadata.json',metadata)
 print(model,'PREPARED',metadata['anchors']['60'],flush=True)
if __name__=='__main__':main(sys.argv[1])
