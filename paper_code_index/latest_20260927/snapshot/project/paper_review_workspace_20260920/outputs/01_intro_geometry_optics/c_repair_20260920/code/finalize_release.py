"""Record the validated release and check protected sources without transport."""
from pathlib import Path
import json,hashlib,sys,platform,subprocess,re,os
H=Path(__file__).resolve().parents[1];V=H.parent/'c_validation_20260920'
os.environ['MPLCONFIGDIR']=str(H/'tmp/mpl')
import numpy,scipy,pandas,matplotlib
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads((H/p).read_text())
checks=[]
for x in json.loads((V/'inputs/source_manifest_before.json').read_text()):
 actual=sha(x['path']);checks.append({'path':x['path'],'expected':x['sha256'],'actual':actual,'unchanged':actual==x['sha256']})
assert all(x['unchanged'] for x in checks)
(H/'reports/protected_source_integrity.json').write_text(json.dumps({'status':'PASS','n_files':len(checks),'checks':checks},indent=2)+'\n')
gates={p:read('reports/'+p+'.json')['status'] for p in ['transport_validation','reference_shape_validation','conditional_kernel_validation','geometry_validation','step_validation','release_validation','run_ledger','protected_source_integrity']}
assert all(v=='PASS' for v in gates.values()),gates
ref=read('reports/reference_validation.json');assert abs(ref['Q_relative_difference'])<1e-5 and ref['max_relative_rate_thickness_variation']<1e-6
gates['reference_validation']='PASS';gates['focus_export']=read('paper_ready/focus_export_manifest.json')['status'];assert gates['focus_export']=='PASS'
log=(H/'logs/paper_xelatex_final.log').read_text();assert not re.search(r'Warning|Overfull|Missing character|undefined',log);assert '6 pages' in log
ledger=read('reports/run_ledger.json');assert ledger['n_valid_primaries']==2100000 and len(ledger['valid_runs'])==42
suite=sha(H/'build/suite_version/laue511');current=sha(H/'build/laue511');assert all(x['executable_sha256']==suite for x in ledger['valid_runs'])
assert all(x['executable_sha256']==current for x in read('reports/release_validation.json')['observation_only_replays'])
seeds={}
for x in ledger['valid_runs']:seeds.setdefault(x['seed'],[]).append(x['name'])
reused={str(k):v for k,v in seeds.items() if len(v)>1};assert len(reused)==1 and set(next(iter(reused.values())))=={'combined_off0','step0','step0p2','step5'}
# Resolve documentation paths and check every local link.
for p in [H/'REPORT_ZH.md',H/'README_ZH.md',H/'HANDOFF_ZH.md']:
 s=p.read_text()
 def fix(m):
  path=m.group(2)
  if path.startswith(('http:','https:','/','#')):return m.group(0)
  target=(p.parent/path).resolve()
  assert target.exists() or target.name=='MACHINE_HANDOFF.json',target
  return m.group(1)+str(target)+')'
 s=re.sub(r'(\]\()([^\)]+)\)',fix,s);p.write_text(s)
files=[]
for folder in ['src','code','inputs']:
 files+=sorted(p for p in (H/folder).iterdir() if p.is_file())
files += [H/x for x in ['CMakeLists.txt','PROTOCOL_ZH.md','README_ZH.md','REPORT_ZH.md','HANDOFF_ZH.md','SOURCES_ZH.md','build/laue511','build/kernel_check','build/suite_version/laue511','build/suite_version/laue511.cc','build/suite_version/CrystalKernel.hh','paper_ready/REPAIR_NOTE_ZH.pdf','paper_ready/REPAIR_NOTE_ZH.tex','paper_ready/optics_methods.tex','paper_ready/references.bib','paper_ready/INSERTION_ZH.md','paper_ready/focal_crossings_corrected.csv','paper_ready/focus_export_manifest.json']]
files+=sorted((H/'figures').glob('*'))
files+=sorted(p for p in (H/'reports').glob('*.json') if p.name not in ['release_manifest.json','final_validation.json'])
for x in ledger['valid_runs']:
 for f in ['run_metadata.json','summary.json']:files.append(H/'runs'/x['name']/f)
manifest={'schema_version':1,'environment':{'python':sys.version,'platform':platform.platform(),'numpy':numpy.__version__,'scipy':scipy.__version__,'pandas':pandas.__version__,'matplotlib':matplotlib.__version__,'Geant4':'11.4.0','G4EMLOW':'8.8','xoppylib':'1.0.55','xraylib':'4.2.1','dabax':'1.0.12','compiler':subprocess.check_output(['/usr/bin/c++','--version'],text=True).splitlines()[0]},'checks':gates,'paired_seed_reuse_only':reused,'files':[{'path':str(p.relative_to(H)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(set(files))],'external_reference_hashes':ref['sha256'],'suite_executable':suite,'release_executable':current,'release_csv_equivalence':'all four CSV outputs in four 50k-event paired step runs are bitwise identical'}
(H/'reports/release_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
comparison=read('reports/comparison.json');export=read('paper_ready/focus_export_manifest.json')
obj={'schema_version':1,'status':'PASS_WITHIN_MONOCHROMATIC_MODEL_CONTRACT','task':'Fork01 extra c implementation repair and comparison; original manuscript not modified','recommended_geometry':'25 radially oriented clipped Ge111 tiles, 18 mm envelope, 0.2 mm sector gap','physical_scope':'511-keV line; ideal-imperfect mosaic; selected +/-111; FWHM30 arcsec; unit temperature factor; ideal alignment; standard EM competition','geometry_optimality_scope':'maximum retained area within fixed square envelopes and separated sectors; not a global lens or engineering optimum','independent_validations':gates,'executed_transport':{'formal_runs':42,'formal_primaries':2100000,'preflight_primaries':12000,'release_replayed_primaries':200000,'paired_replays_are_not_independent_statistics':True,'no_atmospheric_or_detector_main_simulation':True},'kernel_samples':200000,'comparison':comparison,'phase_space':{k:export[k] for k in ['n_incident','n_selected','sampled_crystal_area_cm2','Aeff_opt_cm2','Aeff_MC_SE_cm2','phase_space_sha256']},'outputs':{'chinese_report':str(H/'REPORT_ZH.md'),'PDF':str(H/'paper_ready/REPAIR_NOTE_ZH.pdf'),'candidate_methods':str(H/'paper_ready/optics_methods.tex'),'reference_bib':str(H/'paper_ready/references.bib'),'code':str(H/'src/laue511.cc'),'runtime_physics':str(H/'inputs/corrected_physics.dat'),'focus_csv':str(H/'paper_ready/focal_crossings_corrected.csv'),'run_ledger':str(H/'reports/run_ledger.json'),'release_manifest':str(H/'reports/release_manifest.json')},'release_manifest_sha256':sha(H/'reports/release_manifest.json'),'not_executed':['manuscript replacement','detector-coordinate conversion and EventList signal transport','500 eV response','selected effective area','A/B sensitivity recalculation','experimental crystal calibration','fabrication or alignment tolerance validation','broadband Laue response'],'protected_files_unchanged':23,'next_step':'If adopting in full manuscript, propagate corrected focal phase space through signal branch and synchronize affected values; do not replace sensitivities by an area-ratio rescaling. No background rerun required by this optical repair.'}
(H/'MACHINE_HANDOFF.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
(H/'reports/final_validation.json').write_text(json.dumps({'status':'PASS','gates':gates,'report_pdf_pages':6,'paper_compile_warnings':0,'protected_source_files':23,'release_manifest_files':len(manifest['files']),'paper_applied':False,'machine_handoff_sha256':sha(H/'MACHINE_HANDOFF.json')},indent=2)+'\n')
print(json.dumps({'status':obj['status'],'manifest_files':len(manifest['files']),'protected_files':23,'PDF_pages':6}))
