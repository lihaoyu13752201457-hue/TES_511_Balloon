#include "SiPhononSensitivity.hh"

#include "G4CMPElectrodeHit.hh"
#include "G4Event.hh"
#include "G4HCofThisEvent.hh"
#include "G4PhononLong.hh"
#include "G4PhononTransFast.hh"
#include "G4PhononTransSlow.hh"
#include "G4RunManager.hh"
#include "G4SDManager.hh"
#include "G4Step.hh"
#include "G4SystemOfUnits.hh"
#include "G4Track.hh"

#include <cmath>
#include <iomanip>
#include <stdexcept>

SiPhononSensitivity::SiPhononSensitivity(
    const G4String& name, const RunConfig& config,
    std::shared_ptr<const std::vector<DepositGroup>> groups,
    std::shared_ptr<const std::vector<Pixel>> pixels)
    : G4CMPElectrodeSensitivity(name), config_(config), groups_(std::move(groups)),
      pixels_(std::move(pixels)), output_(config.outputCsv, std::ios::trunc) {
  if (!output_) throw std::runtime_error("cannot write hit output: " + config.outputCsv);
  output_ << "sim_event_id,group_key,event_order,job_id,event_id,layer,candidate,"
             "track_id,particle,start_energy_eV,start_time_ns,end_time_ns,"
             "arrival_from_group_ns,energy_deposited_eV,track_weight,weighted_energy_eV,"
             "end_local_x_mm,end_local_y_mm,end_local_z_mm,surface_class,pixel_id\n";
  output_ << std::setprecision(17);
}

SiPhononSensitivity::~SiPhononSensitivity() {
  output_.flush();
  output_.close();
}

G4bool SiPhononSensitivity::IsHit(const G4Step* step,
                                  const G4TouchableHistory*) const {
  const auto* track = step->GetTrack();
  const auto* particle = track->GetDefinition();
  const bool phonon = particle == G4PhononLong::Definition() ||
                      particle == G4PhononTransFast::Definition() ||
                      particle == G4PhononTransSlow::Definition();
  return phonon && track->GetTrackStatus() == fStopAndKill &&
         step->GetNonIonizingEnergyDeposit() > 0.;
}

std::pair<std::string, int> SiPhononSensitivity::Classify(
    double localXmm, double localYmm, double localZmm) const {
  constexpr double boundaryToleranceMm = 2e-5;
  const double sensorHalfWidth = 0.75 * std::sqrt(config_.sensorAreaScale);
  if (std::abs(localXmm + 0.15) <= boundaryToleranceMm) {
    for (const auto& pixel : *pixels_) {
      if (std::abs(localYmm - pixel.ymm) <= sensorHalfWidth + boundaryToleranceMm &&
          std::abs(localZmm - pixel.zmm) <= sensorHalfWidth + boundaryToleranceMm) {
        return {"sensor", pixel.id};
      }
    }
  }
  const bool atBoundary = std::abs(std::abs(localXmm) - 0.15) <= boundaryToleranceMm ||
                          std::abs(std::abs(localYmm) - 18.) <= boundaryToleranceMm ||
                          std::abs(std::abs(localZmm) - 18.) <= boundaryToleranceMm;
  return atBoundary ? std::make_pair(std::string("bath"), -1)
                    : std::make_pair(std::string("bulk"), -1);
}

void SiPhononSensitivity::EndOfEvent(G4HCofThisEvent* hce) {
  const G4int collectionId = G4SDManager::GetSDMpointer()->GetCollectionID(hitsCollection);
  if (collectionId < 0 || !hce) return;
  auto* hitCollection =
      static_cast<G4CMPElectrodeHitsCollection*>(hce->GetHC(collectionId));
  if (!hitCollection) return;

  const auto eventId = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
  if (eventId < 0 || static_cast<std::size_t>(eventId) >= groups_->size()) {
    throw std::runtime_error("hit event ID outside group table");
  }
  const auto& group = groups_->at(static_cast<std::size_t>(eventId));
  for (const auto* hit : *hitCollection->GetVector()) {
    // Inverse of generator mapping (G4 X,Y,Z)=(local y,local z,local x).
    const double localXmm = hit->GetFinalPosition().z() / mm;
    const double localYmm = hit->GetFinalPosition().x() / mm;
    const double localZmm = hit->GetFinalPosition().y() / mm;
    const auto classified = Classify(localXmm, localYmm, localZmm);
    const double weightedEV = hit->GetEnergyDeposit() / eV * hit->GetWeight();
    if (classified.first == "sensor") sensorEnergyEV_ += weightedEV;
    else if (classified.first == "bath") bathEnergyEV_ += weightedEV;
    else bulkEnergyEV_ += weightedEV;
    ++recordedHits_;
    ++classCounts_[classified.first];

    output_ << eventId << ',' << group.groupKey << ',' << group.eventOrder << ','
            << group.jobId << ',' << group.originalEventId << ',' << group.layer << ','
            << group.candidate << ',' << hit->GetTrackID() << ','
            << hit->GetParticleName() << ',' << hit->GetStartEnergy() / eV << ','
            << hit->GetStartTime() / ns << ',' << hit->GetFinalTime() / ns << ','
            << hit->GetFinalTime() / ns - group.referenceTimeNs << ','
            << hit->GetEnergyDeposit() / eV << ',' << hit->GetWeight() << ','
            << weightedEV << ',' << localXmm << ',' << localYmm << ',' << localZmm
            << ',' << classified.first << ',' << classified.second << '\n';
  }
}
