import importlib.util,sys
from pathlib import Path
_source=Path('/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920/outputs/00_parent/activation_correction_20260924/code/common.py')
sys.path.append(str(_source.parent))
_spec=importlib.util.spec_from_file_location('prior_correction_common',_source)
_m=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_m)
for _k,_v in vars(_m).items():
    if not _k.startswith('_'):globals()[_k]=_v
O=Path('/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920/outputs/00_parent/activation_correction_20260924/production_repair_20260925/final')
def background(model):
    d=O/'data'/model/'response';m=read(d/'manifest.json')
    return {k:np.load(d/(k+'.npy'),mmap_mode='r') for k in m['arrays']},read(d/'category_registry.json')['categories'],np.load(d/'category_factors.npy')
