"""Isolated single-decay response runtime; installed binaries/data are read-only."""
from pathlib import Path
import os, subprocess, shlex, json, hashlib
O=Path(__file__).resolve().parents[1]
T=O/'targeted_response'; T.mkdir(exist_ok=True)
M=Path('/home/ubuntu/MEGAlib_Install/megalib-main')
G=M/'external/geant4_v10.02.p03'; R=M/'external/root_v6.36.6'
GD=G/'share/Geant4-10.2.3/data'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def environment(corrected=True):
    e=os.environ.copy();e.update(MEGALIB=str(M),ROOTSYS=str(R))
    e['PATH']=f'{G}/bin:{R}/bin:{M}/bin:'+e.get('PATH','')
    e['LD_LIBRARY_PATH']=f'{T}/lib:{M}/lib:{R}/lib:{G}/lib:'+e.get('LD_LIBRARY_PATH','')
    for key,name in {'G4NEUTRONHPDATA':'G4NDL4.5','G4LEDATA':'G4EMLOW6.48','G4LEVELGAMMADATA':'PhotonEvaporation3.2','G4RADIOACTIVEDATA':'RadioactiveDecay4.3.2','G4ENSDFSTATEDATA':'G4ENSDFSTATE1.2.3','G4SAIDXSDATA':'G4SAIDDATA1.1','G4PARTICLEXSDATA':'G4PARTICLEXS3.1','G4PIIDATA':'G4PII1.3','G4REALSURFACEDATA':'RealSurface1.0','G4ABLADATA':'G4ABLA3.0','G4NEUTRONXSDATA':'G4NEUTRONXS1.4'} .items():
        if (GD/name).exists():e[key]=str(GD/name)
    if corrected:
        e['G4RADIOACTIVEDATA']=str(T/'rdm')
        e['G4LEVELGAMMADATA']=str(T/'photon')
    e['OMP_NUM_THREADS']='1';e['OPENBLAS_NUM_THREADS']='1'
    return e
def build():
    lib=T/'lib';lib.mkdir(exist_ok=True)
    original=M/'src/cosima/src/MCSteppingAction.cc'
    text=original.read_text();start=text.index('} else if (m_DecayMode == MCParameterFile::c_DecayModeActivationDelayedDecay) {')
    end=text.index('//cout<<"  P:',start)
    segment=text[start:end]
    assert segment.count('FutureEvent = true;')==1
    segment=segment.replace('FutureEvent = true;','FutureEvent = false; // Explicit-state response: daughter inventory is handled separately.')
    patched=T/'MCSteppingAction.cc';patched.write_text(text[:start]+segment+text[end:])
    env=environment(False)
    def flags(tool,arg):return shlex.split(subprocess.check_output([str(tool),arg],env=env,text=True))
    gflags=flags(G/'bin/geant4-config','--cflags');rlibs=flags(R/'bin/root-config','--libs')
    cmd=['g++','-O3','-fno-strict-aliasing','-DNDEBUG','-fPIC','-D_REENTRANT','-D___LINUX___','-D___CLING___','-DG4VIS_USE','-I'+str(M/'include'),'-I'+str(M/'src/cosima/inc')]+gflags+flags(R/'bin/root-config','--cflags')+['-c',str(patched),'-o',str(lib/'MCSteppingAction.o')]
    subprocess.run(cmd,env=env,check=True)
    source=M/'src/cosima/src/MCSource.cc';st=source.read_text()
    old='Entry->m_ParticleExcitation = Tokens.GetTokenAtAsInt(3);'
    assert st.count(old)==1
    patched_source=T/'MCSource.cc';patched_source.write_text(st.replace(old,'Entry->m_ParticleExcitation = Tokens.GetTokenAtAsDouble(3)*keV; // Explicit keV in targeted EventList.'))
    cmd[-4:]=['-c',str(patched_source),'-o',str(lib/'MCSource.o')]
    subprocess.run(cmd,env=env,check=True)
    objects=[str(lib/(p.stem+'.o')) if p.stem in ('MCSteppingAction','MCSource') else str(M/'lib'/(p.stem+'.o')) for p in sorted((M/'src/cosima/src').glob('*.cc')) if p.name!='MCCosima.cc']
    assert all(Path(p).exists() for p in objects)
    subprocess.run(['g++','-shared','-o',str(lib/'libCosima.so')]+objects+flags(G/'bin/geant4-config','--libs')+rlibs+['-L'+str(M/'lib'),'-lSivan','-lGeomega','-lCommonMisc','-lCommonGui'],env=env,check=True)
    subprocess.run(['g++','-O3','-D___LINUX___','-D___CLING___','-I'+str(M/'include')]+gflags+flags(R/'bin/root-config','--cflags')+[str(M/'src/cosima/src/MCCosima.cc'),str(lib/'libCosima.so'),'-L'+str(M/'lib'),'-lSivan','-lGeomega','-lCommonMisc','-lCommonGui']+flags(G/'bin/geant4-config','--libs')+rlibs+['-o',str(T/'cosima')],env=env,check=True)
    (T/'build_manifest.json').write_text(json.dumps({'original':str(original),'original_sha256':sha(original),'patched_sha256':sha(patched),'library_sha256':sha(lib/'libCosima.so'),'change':'Disable future daughter queue only in ActivationDelayedDecay. Keep primary and daughters with inter-decay gap <= DetectorTimeConstant. DetectorTimeConstant set to 1 us in new source cards.','installed_objects':objects},indent=2)+'\n')
def data():
    rdm=T/'rdm';rdm.mkdir(exist_ok=True)
    for p in (GD/'RadioactiveDecay4.3.2').iterdir():
        dest=rdm/p.name
        if not dest.exists():dest.symlink_to(p)
    # Only Er158 is replaced. W176 remains unmodified in the transport runtime;
    # its downstream Ta176 activity is calculated separately, with a documented
    # unresolved feeding-scheme uncertainty, not a fictitious decay channel.
    source=O/'data/reference_rdm_6_1_2/z68.a158'
    # Convert the corresponding Ho158 level table without rounding or mapping
    # changed evaluated levels onto different old levels.
    photon=T/'photon';photon.mkdir(exist_ok=True)
    for p in (GD/'PhotonEvaporation3.2').iterdir():
        if not (photon/p.name).exists():(photon/p.name).symlink_to(p)
    pe=O/'data/nuclear_references/PhotonEvaporation6.1_z67.a158'
    lines=iter(pe.read_text().splitlines());outpe=[];levels={};level_manifest=[]
    for line in lines:
        if not line.strip():continue
        w=line.split();assert len(w)==6,w
        idx=int(w[0]);energy=float(w[2]);hl=float(w[3]);spin=float(w[4]);nt=int(w[5]);levels[idx]=energy
        level_manifest.append(dict(index=idx,energy_keV=energy,half_life_s=hl,transitions=nt))
        for k in range(nt):
            tr=next(lines).split();assert len(tr)==16,tr
            daughter=int(tr[0]);eg=energy-levels[daughter]
            assert abs(eg-float(tr[1]))<.051,(idx,daughter,eg,tr[1])
            # The old reader uses energy, intensity, lifetime, spin, total and
            # subshell conversion coefficients; its multipolarity is ignored.
            outpe.append(' '.join([f'{energy:.9g}',f'{eg:.9g}',tr[2],'1+',str(hl),str(abs(spin)),tr[5]]+tr[6:]))
    dest=photon/'z67.a158'
    if dest.is_symlink():dest.unlink()
    dest.write_text('\n'.join(outpe)+'\n')
    out=[]
    for line in source.read_text().splitlines():
        if not line.strip() or line.startswith('#'):continue
        words=line.split();words=[w for w in words if w!='-']
        if words[0] in ('KshellEC','LshellEC','MshellEC') and len(words)==4:
            assert min(abs(float(words[1])-v) for v in levels.values())<1e-6
        out.append(' '.join(words))
    dest=rdm/'z68.a158'
    if dest.is_symlink():dest.unlink()
    dest.write_text('# Er158 EC-only update from G4RadioactiveDecay6.1.2, format conversion only.\n'+'\n'.join(out)+'\n')
    ho=rdm/'z67.a158';original=(GD/'RadioactiveDecay4.3.2/z67.a158').read_text()
    if ho.is_symlink():ho.unlink()
    ho.write_text(original.replace('P      146.712','P      146.801'))
    (T/'nuclear_patch_manifest.json').write_text(json.dumps({'reference':str(source),'reference_sha256':sha(source),'patched_sha256':sha(dest),'photon_reference':str(pe),'photon_reference_sha256':sha(pe),'photon_converted_sha256':sha(photon/'z67.a158'),'photon_levels':level_manifest,'W176':'No transport data invented. Ta176 downstream response will be sampled explicitly; W176 prompt EC radiation remains a nuclear-scheme limitation.'},indent=2)+'\n')
if __name__=='__main__':data();build();print('isolated runtime built',flush=True)
