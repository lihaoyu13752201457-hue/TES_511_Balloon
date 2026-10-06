"""Stock Cosima semantics plus only the corrected secondary-time index."""
from pathlib import Path
import sys,subprocess,shlex,json,difflib
P=Path(__file__).resolve().parents[1];O=P.parent;sys.path.insert(0,str(O/'code'))
from targeted_environment import M,G,R,environment,sha
d=P/'runtime/production';lib=d/'lib';lib.mkdir(parents=True,exist_ok=True)
original=M/'src/cosima/src/MCSteppingAction.cc';text=original.read_text()
old='TimeDelay = (*fpSteppingManager->GetSecondary())[0]->GetGlobalTime() - Step->GetPreStepPoint()->GetGlobalTime();'
new='const size_t FirstNewSecondary = fpSteppingManager->GetSecondary()->size() - GeneratedSecondaries;\n          TimeDelay = (*fpSteppingManager->GetSecondary())[FirstNewSecondary]->GetGlobalTime() - Step->GetPreStepPoint()->GetGlobalTime();'
assert text.count(old)==1
patched=text.replace(old,new);source=d/'MCSteppingAction.cc';source.write_text(patched)
(P/'runtime/production_timing_fix.patch').write_text(''.join(difflib.unified_diff(text.splitlines(True),patched.splitlines(True),fromfile='a/src/cosima/src/MCSteppingAction.cc',tofile='b/src/cosima/src/MCSteppingAction.cc')))
env=environment(False)
def flags(tool,arg):return shlex.split(subprocess.check_output([str(tool),arg],env=env,text=True))
gf=flags(G/'bin/geant4-config','--cflags');rf=flags(R/'bin/root-config','--cflags');gl=flags(G/'bin/geant4-config','--libs');rl=flags(R/'bin/root-config','--libs')
subprocess.run(['g++','-O3','-fno-strict-aliasing','-DNDEBUG','-fPIC','-D_REENTRANT','-D___LINUX___','-D___CLING___','-DG4VIS_USE','-I'+str(M/'include'),'-I'+str(M/'src/cosima/inc')]+gf+rf+['-c',str(source),'-o',str(lib/'MCSteppingAction.o')],env=env,check=True)
objects=[str(lib/'MCSteppingAction.o') if p.stem=='MCSteppingAction' else str(M/'lib'/(p.stem+'.o')) for p in sorted((M/'src/cosima/src').glob('*.cc')) if p.name!='MCCosima.cc']
subprocess.run(['g++','-shared','-o',str(lib/'libCosima.so')]+objects+gl+rl+['-L'+str(M/'lib'),'-lSivan','-lGeomega','-lCommonMisc','-lCommonGui'],env=env,check=True)
subprocess.run(['g++','-O3','-D___LINUX___','-D___CLING___','-I'+str(M/'include')]+gf+rf+[str(M/'src/cosima/src/MCCosima.cc'),str(lib/'libCosima.so'),'-L'+str(M/'lib'),'-lSivan','-lGeomega','-lCommonMisc','-lCommonGui']+gl+rl+['-o',str(d/'cosima')],env=env,check=True)
(d/'manifest.json').write_text(json.dumps({'original_source':str(original),'original_sha256':sha(original),'source_sha256':sha(source),'library_sha256':sha(lib/'libCosima.so'),'binary_sha256':sha(d/'cosima'),'only_change':'Select first secondary created in the current decay step. Original daughter queue and source-parser behavior retained.','no_atmospheric_production_run':True,'installed_files_unchanged':True},indent=2)+'\n')
print('stock-semantics production runtime compiled; no production launched',flush=True)
