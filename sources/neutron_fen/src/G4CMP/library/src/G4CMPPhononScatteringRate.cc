/***********************************************************************\
 * This software is licensed under the terms of the GNU General Public *
 * License version 3 or later. See G4CMP/LICENSE for the full license. *
\***********************************************************************/

/// \file library/src/G4CMPPhononScatteringRate.cc
/// \brief Compute rate for phonon impurity scattering (mode mixing)
//
// $Id: 2839f414b19f047a391d6936b4a022927c091991 $

#include "G4CMPPhononScatteringRate.hh"
#include "G4LatticePhysical.hh"
#include "G4PhysicalConstants.hh"


// Scattering rate is computed from electric field

G4double G4CMPPhononScatteringRate::Rate(const G4Track& aTrack) const {
  G4double B = theLattice->GetScatteringConstant();
  G4double Eoverh = GetKineticEnergy(aTrack)/h_Planck;
  
  return (Eoverh*Eoverh*Eoverh*Eoverh*B);
}
