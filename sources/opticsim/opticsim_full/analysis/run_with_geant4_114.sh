#!/usr/bin/env bash
set -euo pipefail

G4ROOT="${G4ROOT:-/home/ubuntu/software/geant4-11.4.0-install}"
if [[ ! -f "${G4ROOT}/bin/geant4.sh" ]]; then
  echo "Geant4 setup script not found: ${G4ROOT}/bin/geant4.sh" >&2
  exit 2
fi

# shellcheck disable=SC1091
source "${G4ROOT}/bin/geant4.sh"

G4DATA="${GEANT4_DATA_DIR:-${G4ROOT}/share/Geant4/data}"
export G4NEUTRONHPDATA="${G4DATA}/G4NDL4.7.1"
export G4LEDATA="${G4DATA}/G4EMLOW8.8"
export G4LEVELGAMMADATA="${G4DATA}/PhotonEvaporation6.1.2"
export G4RADIOACTIVEDATA="${G4DATA}/RadioactiveDecay6.1.2"
export G4PARTICLEXSDATA="${G4DATA}/G4PARTICLEXS4.2"
export G4PIIDATA="${G4DATA}/G4PII1.3"
export G4SAIDXSDATA="${G4DATA}/G4SAIDDATA2.0"
export G4ABLADATA="${G4DATA}/G4ABLA3.3"
export G4INCLDATA="${G4DATA}/G4INCL1.3"
export G4ENSDFSTATEDATA="${G4DATA}/G4ENSDFSTATE3.0"
export G4CHANNELINGDATA="${G4DATA}/G4CHANNELING2.0"

exec "$@"
