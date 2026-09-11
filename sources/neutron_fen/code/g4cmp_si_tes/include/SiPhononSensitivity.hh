#ifndef SH3_SI_PHONON_SENSITIVITY_HH
#define SH3_SI_PHONON_SENSITIVITY_HH

#include "G4CMPElectrodeSensitivity.hh"
#include "SimulationData.hh"

#include <cstddef>
#include <fstream>
#include <map>
#include <memory>
#include <string>
#include <vector>

class G4HCofThisEvent;
class G4Step;
class G4TouchableHistory;

class SiPhononSensitivity : public G4CMPElectrodeSensitivity {
 public:
  SiPhononSensitivity(const G4String& name, const RunConfig& config,
                      std::shared_ptr<const std::vector<DepositGroup>> groups,
                      std::shared_ptr<const std::vector<Pixel>> pixels);
  ~SiPhononSensitivity() override;

  void EndOfEvent(G4HCofThisEvent* hce) override;
  G4bool IsHit(const G4Step* step, const G4TouchableHistory*) const override;

  double SensorEnergyEV() const { return sensorEnergyEV_; }
  double BathEnergyEV() const { return bathEnergyEV_; }
  double BulkEnergyEV() const { return bulkEnergyEV_; }
  std::size_t RecordedHits() const { return recordedHits_; }
  const std::map<std::string, std::size_t>& ClassCounts() const { return classCounts_; }
  void Flush() { output_.flush(); }

 private:
  std::pair<std::string, int> Classify(double localXmm, double localYmm,
                                       double localZmm) const;

  RunConfig config_;
  std::shared_ptr<const std::vector<DepositGroup>> groups_;
  std::shared_ptr<const std::vector<Pixel>> pixels_;
  std::ofstream output_;
  double sensorEnergyEV_ = 0.;
  double bathEnergyEV_ = 0.;
  double bulkEnergyEV_ = 0.;
  std::size_t recordedHits_ = 0;
  std::map<std::string, std::size_t> classCounts_;
};

#endif
