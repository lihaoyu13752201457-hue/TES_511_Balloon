#ifndef SH3_SI_ACTION_INITIALIZATION_HH
#define SH3_SI_ACTION_INITIALIZATION_HH

#include "G4VUserActionInitialization.hh"
#include "SimulationData.hh"

#include <memory>
#include <vector>

class SiActionInitialization : public G4VUserActionInitialization {
 public:
  SiActionInitialization(const RunConfig& config,
                         std::shared_ptr<const std::vector<DepositGroup>> groups)
      : config_(config), groups_(std::move(groups)) {}
  void Build() const override;

 private:
  RunConfig config_;
  std::shared_ptr<const std::vector<DepositGroup>> groups_;
};

#endif
