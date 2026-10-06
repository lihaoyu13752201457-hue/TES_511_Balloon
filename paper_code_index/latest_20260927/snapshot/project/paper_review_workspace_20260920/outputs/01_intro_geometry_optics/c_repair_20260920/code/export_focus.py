"""Export only the accepted, corrected 25-tile optical phase space.
Units and columns match the read-only Step09 focal-crossing input contract.
No detector transport or detector-response reweighting is implied.
"""
from pathlib import Path
import json,hashlib
import pandas as pd,numpy as np
H=Path(__file__).resolve().parents[1];out=H/'paper_ready';frames=[];provenance=[]
for i in range(3):
 p=H/'runs'/f'ring25cut_s{i}';f=pd.read_csv(p/'focal.csv');n=len(f);f=f[(f.n_diffraction>0)&(f.within_18p98==1)].copy();f['event_id']+=i*50000;f['source_tag']='laue_bfull_diffracted';f['creator_process']='Laue511';f['particle_name']='gamma';f['pdg_encoding']=22;f['weight']=1.;frames.append(f)
 provenance.append({'run':str(p),'focal_input_sha256':hashlib.sha256((p/'focal.csv').read_bytes()).hexdigest(),'n_incident':50000,'n_selected':len(f),'run_metadata':json.loads((p/'run_metadata.json').read_text())})
a=pd.concat(frames,ignore_index=True);p=out/'focal_crossings_corrected.csv';a.to_csv(p,index=False,float_format='%.17g')
assert np.isfinite(a[['E_keV','x_mm','y_mm','z_mm','ux','uy','uz']]).all().all();assert np.max(abs(np.linalg.norm(a[['ux','uy','uz']].to_numpy(),axis=1)-1))<1e-12;assert np.hypot(a.x_mm,a.y_mm).max()<=18.98;assert (a.z_mm==10000).all();assert a.event_id.nunique()==len(a)
geo=json.loads((H/'reports/geometry_validation.json').read_text());ar=geo['total_area_cm2']*len(a)/150000;comp=json.loads((H/'reports/comparison.json').read_text());target=next(x for x in comp['groups'] if x['group']=='ring25cut');assert abs(ar-target['Aeff_cm2'])<1e-12
meta={'status':'PASS','schema':'Step09-compatible optical focal_crossings CSV, selected within 18.98 mm; no coordinate rotation to detector frame applied yet','units':{'E':'keV','xyz':'mm','u':'dimensionless'},'n_incident':150000,'n_selected':len(a),'sampled_crystal_area_cm2':geo['total_area_cm2'],'Aeff_opt_cm2':ar,'Aeff_MC_SE_cm2':target['Aeff_SE_cm2'],'input_photon_weights':1,'event_ids_unique':True,'unit_directions':True,'phase_space_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'runs':provenance,'not_executed':['detector-frame EventList transport','500 eV response','selected effective area','A/B sensitivity']}
(out/'focus_export_manifest.json').write_text(json.dumps(meta,indent=2)+'\n');print('Exported',len(a),'focused photons; Aeff',ar)
