#!/usr/bin/env bash
# Isolated runtime environment for G4CMP g4cmp-V10-05-00 with Geant4 11.4.0.
# Source this file from a clean shell; it intentionally overrides every
# Geant4 dataset variable that the login shell may inherit from MEGAlib.

export NEUTRON_FEN_ROOT=/home/ubuntu/neutron_fen
export NEUTRON_FEN_GEANT4_PREFIX=/home/ubuntu/software/geant4-11.4.0-install
export NEUTRON_FEN_G4CMP_PREFIX="$NEUTRON_FEN_ROOT/install/G4CMP-g4cmp-V10-05-00-g4.11.4.0"

export Geant4_DIR="$NEUTRON_FEN_GEANT4_PREFIX/lib/cmake/Geant4"
export G4CMPINSTALL="$NEUTRON_FEN_G4CMP_PREFIX/share/G4CMP"
export G4CMPLIB="$NEUTRON_FEN_G4CMP_PREFIX/lib"
export G4CMPINCLUDE="$NEUTRON_FEN_G4CMP_PREFIX/include/G4CMP"
export G4LATTICEDATA="$G4CMPINSTALL/CrystalMaps"

export G4NEUTRONHPDATA="$NEUTRON_FEN_GEANT4_PREFIX/share/Geant4/data/G4NDL4.7.1"
export G4LEDATA="$NEUTRON_FEN_GEANT4_PREFIX/share/Geant4/data/G4EMLOW8.8"
export G4LEVELGAMMADATA="$NEUTRON_FEN_GEANT4_PREFIX/share/Geant4/data/PhotonEvaporation6.1.2"
export G4RADIOACTIVEDATA="$NEUTRON_FEN_GEANT4_PREFIX/share/Geant4/data/RadioactiveDecay6.1.2"
export G4PARTICLEXSDATA="$NEUTRON_FEN_GEANT4_PREFIX/share/Geant4/data/G4PARTICLEXS4.2"
export G4PIIDATA="$NEUTRON_FEN_GEANT4_PREFIX/share/Geant4/data/G4PII1.3"
export G4REALSURFACEDATA="$NEUTRON_FEN_GEANT4_PREFIX/share/Geant4/data/RealSurface2.2"
export G4SAIDXSDATA="$NEUTRON_FEN_GEANT4_PREFIX/share/Geant4/data/G4SAIDDATA2.0"
export G4ABLADATA="$NEUTRON_FEN_GEANT4_PREFIX/share/Geant4/data/G4ABLA3.3"
export G4INCLDATA="$NEUTRON_FEN_GEANT4_PREFIX/share/Geant4/data/G4INCL1.3"
export G4ENSDFSTATEDATA="$NEUTRON_FEN_GEANT4_PREFIX/share/Geant4/data/G4ENSDFSTATE3.0"
export G4CHANNELINGDATA="$NEUTRON_FEN_GEANT4_PREFIX/share/Geant4/data/G4CHANNELING2.0"

export PATH="$NEUTRON_FEN_G4CMP_PREFIX/bin:$NEUTRON_FEN_GEANT4_PREFIX/bin${PATH:+:$PATH}"
export LD_LIBRARY_PATH="$NEUTRON_FEN_G4CMP_PREFIX/lib:$NEUTRON_FEN_GEANT4_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
