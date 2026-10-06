"""Read-only adapter to the pinned manuscript analysis, with response overlays."""
import importlib.util
import sys
from pathlib import Path
ORIGINAL = Path(__file__).resolve().parents[2] / 'revision_20260921_AA_continuous'
sys.path.append(str(ORIGINAL / 'code'))
spec = importlib.util.spec_from_file_location('pinned_common', ORIGINAL / 'code/common.py')
pinned = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pinned)
for _key, _value in vars(pinned).items():
    if not _key.startswith('_'):
        globals()[_key] = _value
O = Path(__file__).resolve().parents[1]
base_background = pinned.background

def background(model):
    a, _, _ = base_background(model)
    d = O / 'data' / model / 'response'
    manifest = read(d / 'manifest.json')
    for key in manifest['arrays']:
        a[key] = np.load(d / (key + '.npy'), mmap_mode='r')
    reg = read(d / 'category_registry.json')['categories']
    fac = np.load(d / 'category_factors.npy')
    return a, reg, fac

# Separate authorized targeted-response result package. Existing-sample output
# remains immutable and can still be reproduced with the environment unset.
import os
if os.environ.get('ACTIVATION_TARGETED_FINAL') == '1':
    O = O / 'targeted_response/final'
    def background(model):
        d=O/'data'/model/'response'
        manifest=read(d/'manifest.json')
        a={key:np.load(d/(key+'.npy'),mmap_mode='r') for key in manifest['arrays']}
        return a,read(d/'category_registry.json')['categories'],np.load(d/'category_factors.npy')
