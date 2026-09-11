#ifndef SH3_SI_DETECTOR_CONSTRUCTION_HH
#define SH3_SI_DETECTOR_CONSTRUCTION_HH

#include "G4VUserDetectorConstruction.hh"
#include "SimulationData.hh"

#include <memory>
#include <vector>

class G4CMPSurfaceProperty;
class G4VPhysicalVolume;
class SiPhononSensitivity;

class SiDetectorConstruction : public G4VUserDetectorConstruction {
 public:
  SiDetectorConstruction(const RunConfig& config,
                         std::shared_ptr<const std::vector<DepositGroup>> groups,
                         std::shared_ptr<const std::vector<Pixel>> pixels);
  ~SiDetectorConstruction() override;

  G4VPhysicalVolume* Construct() override;
  SiPhononSensitivity* GetSensitivity() const { return sensitivity_; }

 private:
  RunConfig config_;
  std::shared_ptr<const std::vector<DepositGroup>> groups_;
  std::shared_ptr<const std::vector<Pixel>> pixels_;
  G4CMPSurfaceProperty* sensorSurface_ = nullptr;
  G4CMPSurfaceProperty* bathSurface_ = nullptr;
  SiPhononSensitivity* sensitivity_ = nullptr;
};

#endif
