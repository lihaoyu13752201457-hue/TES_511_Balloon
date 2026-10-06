from aa_common import *
import shutil
def main():
    sys.path.insert(0,str(SIGNAL/'code'))
    module=loadmod('aa_signal_reuse',SIGNAL/'code/analyze_signal.py')
    cfg=C.load_config(read(ROOT/'data/preparation.json')['bundles']['signal']);j=C.load_plan(cfg)[0];r=C.load_bound_receipt(cfg,j);assert r
    out=ROOT/'signal_response'
    for d in ['runs/aa','data','validation']: (out/d).mkdir(parents=True,exist_ok=True)
    src=read(SIGNAL/'inputs_manifest.json');m=dict(src['models']['a'])
    m.update(geometry_setup=str(SETUP),geometry_geo=str(AA/'geometry/Mass_model_AA.geo'),seed=j['seed'],source_card=j['source_path'],source_card_sha256=sha(j['source_path']),sim=r['sim_path'],plastic_volumes=[],bgo_volumes=list(BGO))
    m['geometry_provenance']=[{'snapshot':p,'sha256':h} for p,h in frozen_geometry().items()]
    src['models']={'aa':m};save(out/'inputs_manifest.json',src);save(out/'runs/aa/receipt.json',r)
    shutil.copy2(SIGNAL/'data/optical_identity.npz',out/'data/optical_identity.npz')
    module.O=out;module.main('aa')
    result=read(out/'data/signal_aa_summary.json');assert result['status']=='PASS' and result['events']==37175
    save(ROOT/'data/signal_gate.json',{'status':'PASS__AA_FULL_ENVELOPE_500EV_PIXEL_COMPTON','summary':str(out/'data/signal_aa_summary.json'),'retention':result['retention'],'events':result['events'],'geometry_sha256':sha(AA/'geometry/Mass_model_AA.geo'),'corrected_compton_sha256':sha(SIGNAL/'code/pixel_geometry_compton.py')})
if __name__=='__main__':main()
