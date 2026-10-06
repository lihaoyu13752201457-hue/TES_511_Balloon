from pathlib import Path
import sys,subprocess,shlex,json,hashlib
P=Path(__file__).resolve().parents[1];O=P.parent;sys.path.insert(0,str(O/'code'))
from targeted_environment import M,G,R,T,environment,sha
d=P/'runtime';lib=d/'lib';lib.mkdir(parents=True,exist_ok=True);base=(T/'MCSteppingAction.cc').read_text();old='TimeDelay = (*fpSteppingManager->GetSecondary())[0]->GetGlobalTime() - Step->GetPreStepPoint()->GetGlobalTime();';new='const size_t FirstNewSecondary = fpSteppingManager->GetSecondary()->size() - GeneratedSecondaries;\n          TimeDelay = (*fpSteppingManager->GetSecondary())[FirstNewSecondary]->GetGlobalTime() - Step->GetPreStepPoint()->GetGlobalTime();';assert base.count(old)==1;base=base.replace(old,new)
anchor='double Time = Step->GetPostStepPoint()->GetGlobalTime()/second;';assert base.count(anchor)==1
probe=r'''
  if (Track->GetTrackID() == 1 && Track->GetCurrentStepNumber() == 1) {
    auto p = Step->GetPreStepPoint();
    std::ostringstream loc;
    loc << "INITIAL_LOCATION " << p->GetPhysicalVolume()->GetName()
        << " material=" << p->GetMaterial()->GetName()
        << " ion=" << Track->GetDefinition()->GetParticleName();
    EventAction->AddComment(loc.str());
  }
'''
audit=r'''
          const double OldIndexedDelay = (*fpSteppingManager->GetSecondary())[0]->GetGlobalTime() - Step->GetPreStepPoint()->GetGlobalTime();
          if (!IsPrimaryDecay && ((OldIndexedDelay > m_DetectorTimeConstant) != (TimeDelay > m_DetectorTimeConstant))) {
            std::ostringstream timing;
            timing << "REPAIRED_TIME_DECISION ion=" << Track->GetDefinition()->GetParticleName()
                   << " old_delay_s=" << OldIndexedDelay/second << " new_delay_s=" << TimeDelay/second;
            EventAction->AddComment(timing.str());
          }
'''
assert base.count(new)==1
base=base.replace(new,new+audit)
src=d/'MCSteppingAction.cc';src.write_text(base.replace(anchor,anchor+probe));env=environment()
def flags(tool,arg):return shlex.split(subprocess.check_output([str(tool),arg],env=env,text=True))
gf=flags(G/'bin/geant4-config','--cflags');rf=flags(R/'bin/root-config','--cflags');gl=flags(G/'bin/geant4-config','--libs');rl=flags(R/'bin/root-config','--libs')
subprocess.run(['g++','-O3','-fno-strict-aliasing','-DNDEBUG','-fPIC','-D_REENTRANT','-D___LINUX___','-D___CLING___','-DG4VIS_USE','-I'+str(M/'include'),'-I'+str(M/'src/cosima/inc')]+gf+rf+['-c',str(src),'-o',str(lib/'MCSteppingAction.o')],env=env,check=True)
objects=[str(lib/'MCSteppingAction.o') if p.stem=='MCSteppingAction' else str(T/'lib/MCSource.o') if p.stem=='MCSource' else str(M/'lib'/(p.stem+'.o')) for p in sorted((M/'src/cosima/src').glob('*.cc')) if p.name!='MCCosima.cc']
subprocess.run(['g++','-shared','-o',str(lib/'libCosima.so')]+objects+gl+rl+['-L'+str(M/'lib'),'-lSivan','-lGeomega','-lCommonMisc','-lCommonGui'],env=env,check=True)
subprocess.run(['g++','-O3','-D___LINUX___','-D___CLING___','-I'+str(M/'include')]+gf+rf+[str(M/'src/cosima/src/MCCosima.cc'),str(lib/'libCosima.so'),'-L'+str(M/'lib'),'-lSivan','-lGeomega','-lCommonMisc','-lCommonGui']+gl+rl+['-o',str(d/'cosima')],env=env,check=True)
(d/'manifest.json').write_text(json.dumps({'source_sha256':sha(src),'library_sha256':sha(lib/'libCosima.so'),'binary_sha256':sha(d/'cosima'),'independent_installed_files_unmodified':True,'changes':['Index first secondary created in current decay step for time decision.','Retain prior explicit-state excitation parser.','Future daughter queue disabled only in ActivationDelayedDecay; analytical inventory owns those states.','Record initial physical volume/material/ion as compact geometry check.']},indent=2)+'\n');print('repair runtime built',flush=True)
