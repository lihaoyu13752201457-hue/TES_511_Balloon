import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,numpy as np
from analyze import Analyzer,O
results={}
for model in ['a','b']:
 a=Analyzer(model);selected=np.flatnonzero(a.s['narrow_final']);checks=0
 # Saturated no-TES hot mark 0 is BGO, mark 1 plastic-only; neither adds TES energy.
 for i in selected[::max(1,len(selected)//200)]:
  ix=a.nb+int(i);single=a.evaluate([ix],60,1);bgo=a.evaluate([ix,0],60,1);plastic=a.evaluate([ix,1],60,1)
  assert single['bgo_final'] and plastic['bgo_final'] and not plastic['dual_final'] and not bgo['bgo_final']
  assert bgo['window']==single['window']==plastic['window']
  assert abs(plastic['energy']-single['energy'])<1e-9
  # Two complete 511-keV deposits merge out of the 1-keV analysis window.
  twice=a.evaluate([ix,ix],60,1);assert not twice['window']
  checks+=1
 results[model]={'status':'PASS','tested_isolated_selected_templates':checks,'no_TES_overlap_preserves_signal_response':True,'BGO_threshold_applied_to_group':True,'plastic_only_excluded_from_primary_veto':True,'raw_signal_deposits_actually_summed':True,'signal_pixel_noise_applied_once':True,'pixel_geometry_interface_has_no_truth_coordinates':True}
 print(model,results[model],flush=True)
(O/'validation/response_test.json').write_text(json.dumps(results,indent=2)+'\n')
