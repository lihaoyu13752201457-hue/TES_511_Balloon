/*
 * MCTrackingAction.cxx
 *
 *
 * Copyright (C) by Andreas Zoglauer.
 * All rights reserved.
 *
 *
 * This code implementation is the intellectual property of
 * Andreas Zoglauer.
 *
 * By copying, distributing or modifying the Program (or any work
 * based on the Program) you indicate your acceptance of this statement,
 * and all its terms.
 *
 */


// Cosima:
#include "MCTrackingAction.hh"
#include "MCTrackInformation.hh"
#include "MCRunManager.hh"
#include "MCPhysicsList.hh"

// MEGAlib:
#include "MStreams.h"

// Geant4:

// Standard lib:

#include "MCEventAction.hh"
/******************************************************************************
 * Default constructor
 */
MCTrackingAction::MCTrackingAction()
{
  // Intentionally left blank
}


/******************************************************************************
 * Default destructor
 */
MCTrackingAction::~MCTrackingAction()
{
  // Intentionally left blank
}


/******************************************************************************
 * Actions before tracking starts
 */
void MCTrackingAction::PreUserTrackingAction(const G4Track* Track)
{
  // ===== NEW: build & register TrackMeta =====
  TrackMeta meta;
  meta.tid = Track->GetTrackID();
  meta.pid = Track->GetParentID();

  // this track particle name
  meta.particle = Track->GetDefinition()->GetParticleName();

  // creator process (primary has none)
  if (Track->GetCreatorProcess() != nullptr) {
    meta.creatorProcess = Track->GetCreatorProcess()->GetProcessName();
  } else {
    meta.creatorProcess = "primary";
  }

  if (meta.pid == 0) {
    // this is a primary track
    meta.primid = meta.tid;
    meta.primaryParticle = meta.particle;
    meta.parentParticle = "none";
  } else {
    // inherit primary info from parent track
    TrackMeta parent;
    if (MCEventAction::GetTrackMeta(meta.pid, parent)) {
      meta.primid = parent.primid;
      meta.primaryParticle = parent.primaryParticle;
      meta.parentParticle = parent.particle;
    } else {
      // fallback if parent not found (rare)
      meta.primid = meta.pid;
      meta.primaryParticle = "unknown";
      meta.parentParticle = "unknown";
    }
  }

  MCEventAction::RegisterTrackMeta(meta);

  G4Track* MyTrack = const_cast<G4Track*>(Track); 

  if (MyTrack->GetUserInformation() == 0) {
    MyTrack->SetUserInformation(new MCTrackInformation(m_NPrimaries, m_NPrimaries));
    m_NPrimaries--;
  }
  
//   if (Track->GetDefinition()->GetParticleName() == "gamma") {
//     MCRunManager::GetMCRunManager()->GetPhysicsList()->SetGammaCuts();
//   }

}


/******************************************************************************
 * Set the number of generated particles
 */
void MCTrackingAction::SetNGeneratedParticles(int NGeneratedParticles)
{
  m_NPrimaries = NGeneratedParticles;
}


/*
 * MCTrackingAction.cc: the end...
 ******************************************************************************/
