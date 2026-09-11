# Source this to get a working MEGAlib/cosima environment.
# Mirrors cosima_env() in the project's run_gate_e_corrected_full_delayed.py.
export MEGALIB=/home/ubuntu/MEGAlib_Install/megalib-main
G4=$MEGALIB/external/geant4_v10.02.p03
G4DATA=$G4/share/Geant4-10.2.3/data
export LD_LIBRARY_PATH=$MEGALIB/lib:$MEGALIB/external/root_v6.36.6/lib:$G4/lib:${LD_LIBRARY_PATH}
export PATH=$MEGALIB/bin:$PATH
export G4NEUTRONHPDATA=$G4DATA/G4NDL4.5
export G4LEDATA=$G4DATA/G4EMLOW6.48
export G4LEVELGAMMADATA=$G4DATA/PhotonEvaporation3.2
export G4RADIOACTIVEDATA=$G4DATA/RadioactiveDecay4.3.2
export G4NEUTRONXSDATA=$G4DATA/G4NEUTRONXS1.4
export G4PIIDATA=$G4DATA/G4PII1.3
export G4REALSURFACEDATA=$G4DATA/RealSurface1.0
export G4SAIDXSDATA=$G4DATA/G4SAIDDATA1.1
export G4ABLADATA=$G4DATA/G4ABLA3.0
export G4ENSDFSTATEDATA=$G4DATA/G4ENSDFSTATE1.2.3
