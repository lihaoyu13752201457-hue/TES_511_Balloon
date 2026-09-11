#ifndef SH3_SI_PRIMARY_GENERATOR_ACTION_HH
#define SH3_SI_PRIMARY_GENERATOR_ACTION_HH

#include "G4VUserPrimaryGeneratorAction.hh"
#include "SimulationData.hh"

#include <cstddef>
#include <memory>
#include <vector>

class G4Event;
class G4ParticleGun;

class SiPrimaryGeneratorAction : public G4VUserPrimaryGeneratorAction {
 public:
  SiPrimaryGeneratorAction(const RunConfig& config,
                           std::shared_ptr<const std::vector<DepositGroup>> groups);
  ~SiPrimaryGeneratorAction() override;
  void GeneratePrimaries(G4Event* event) override;

 private:
  RunConfig config_;
  std::shared_ptr<const std::vector<DepositGroup>> groups_;
  G4ParticleGun* gun_ = nullptr;
};

#endif
