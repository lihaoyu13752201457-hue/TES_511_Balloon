#include "SiPrimaryGeneratorAction.hh"

#include "G4Event.hh"
#include "G4ParticleGun.hh"
#include "G4PhononLong.hh"
#include "G4PhononTransFast.hh"
#include "G4PhononTransSlow.hh"
#include "G4RandomDirection.hh"
#include "G4SystemOfUnits.hh"
#include "Randomize.hh"

#include <algorithm>
#include <stdexcept>

SiPrimaryGeneratorAction::SiPrimaryGeneratorAction(
    const RunConfig& config,
    std::shared_ptr<const std::vector<DepositGroup>> groups)
    : config_(config), groups_(std::move(groups)), gun_(new G4ParticleGun(1)) {}

SiPrimaryGeneratorAction::~SiPrimaryGeneratorAction() { delete gun_; }

void SiPrimaryGeneratorAction::GeneratePrimaries(G4Event* event) {
  const auto eventId = event->GetEventID();
  if (eventId < 0 || static_cast<std::size_t>(eventId) >= groups_->size()) {
    throw std::runtime_error("Geant4 event ID is outside deposit-group table");
  }
  const auto& group = groups_->at(static_cast<std::size_t>(eventId));
  const auto packetCounts = AllocatePacketCounts(group, config_);
  const G4double packetEnergy = config_.packetEnergyMeV * 1e-3 * eV;
  constexpr G4double halfThicknessMm = 0.15;
  constexpr G4double halfWidthMm = 18.0;
  constexpr G4double inwardMm = 2e-6;

  for (std::size_t depositIndex = 0; depositIndex < group.deposits.size(); ++depositIndex) {
    const auto& deposit = group.deposits[depositIndex];
    const int packetCount = packetCounts[depositIndex];
    // Input coordinates are (thickness x, in-plane y, in-plane z).  The G4CMP
    // lattice convention aligns (hkl) with geometry +Z, so map them to G4
    // coordinates (X,Y,Z)=(local y,local z,local x).
    const double localX = std::clamp(deposit.localXmm,
                                     -halfThicknessMm + inwardMm,
                                     halfThicknessMm - inwardMm);
    const double localY = std::clamp(deposit.localYmm,
                                     -halfWidthMm + inwardMm,
                                     halfWidthMm - inwardMm);
    const double localZ = std::clamp(deposit.localZmm,
                                     -halfWidthMm + inwardMm,
                                     halfWidthMm - inwardMm);
    const G4ThreeVector position(localY * mm, localZ * mm, localX * mm);
    const G4double packetWeight = deposit.energyKeV * keV /
                                  (packetCount * packetEnergy);

    for (int packet = 0; packet < packetCount; ++packet) {
      const G4double selector = G4UniformRand();
      if (selector < 0.531) {
        gun_->SetParticleDefinition(G4PhononTransSlow::Definition());
      } else if (selector < 0.907) {
        gun_->SetParticleDefinition(G4PhononTransFast::Definition());
      } else {
        gun_->SetParticleDefinition(G4PhononLong::Definition());
      }
      gun_->SetParticleEnergy(packetEnergy);
      gun_->SetParticleWeight(packetWeight);
      gun_->SetParticlePosition(position);
      gun_->SetParticleTime(deposit.timeNs * ns);
      gun_->SetParticleMomentumDirection(G4RandomDirection());
      gun_->GeneratePrimaryVertex(event);
    }
  }
}
