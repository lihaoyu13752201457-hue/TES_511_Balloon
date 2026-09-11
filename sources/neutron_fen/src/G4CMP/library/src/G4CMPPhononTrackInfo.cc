/***********************************************************************\
 * This software is licensed under the terms of the GNU General Public *
 * License version 3 or later. See G4CMP/LICENSE for the full license. *
\***********************************************************************/

/// \file library/src/G4CMPPhononTrackInfo.cc
/// \brief Implementation of the G4CMPPhononTrackInfo class. Used to store
/// auxiliary information that a G4Track can't store, but is necessary for
/// physics processes to know.
///
/// Note: Wavevectors need to be passed in the global coordinate system.
//
// $Id: d22f55d5ad1f5c6f2ae81eb4a3ba0adae87f385c $
//
// 20161111 Initial commit - R. Agnese
// 20170728 M. Kelsey -- Replace "k" function args with "theK" (-Wshadow)

#include "G4CMPPhononTrackInfo.hh"

//G4Allocator<G4CMPPhononTrackInfo> G4CMPPhononTrackInfoAllocator;

G4CMPPhononTrackInfo::G4CMPPhononTrackInfo(const G4LatticePhysical* lat,
                                           G4ThreeVector theK)
  : G4CMPVTrackInfo(lat), waveVec(theK) {;}

void G4CMPPhononTrackInfo::Print() const {
//TODO
}
