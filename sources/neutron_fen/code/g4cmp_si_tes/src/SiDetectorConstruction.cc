#include "SiDetectorConstruction.hh"

#include "G4Box.hh"
#include "G4CMPLogicalBorderSurface.hh"
#include "G4CMPSurfaceProperty.hh"
#include "G4LatticeLogical.hh"
#include "G4LatticeManager.hh"
#include "G4LatticePhysical.hh"
#include "G4LogicalVolume.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4SDManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4UserLimits.hh"
#include "G4VisAttributes.hh"
#include "SiPhononSensitivity.hh"

#include <cfloat>
#include <cmath>
#include <stdexcept>
#include <string>

SiDetectorConstruction::SiDetectorConstruction(
    const RunConfig& config,
    std::shared_ptr<const std::vector<DepositGroup>> groups,
    std::shared_ptr<const std::vector<Pixel>> pixels)
    : config_(config), groups_(std::move(groups)), pixels_(std::move(pixels)) {}

SiDetectorConstruction::~SiDetectorConstruction() {
  delete sensorSurface_;
  delete bathSurface_;
}

G4VPhysicalVolume* SiDetectorConstruction::Construct() {
  auto* nist = G4NistManager::Instance();
  auto* air = nist->FindOrBuildMaterial("G4_AIR");
  auto* silicon = nist->FindOrBuildMaterial("G4_Si");
  auto* aluminum = nist->FindOrBuildMaterial("G4_Al");

  auto* worldSolid = new G4Box("WorldSolid", 30. * mm, 30. * mm, 30. * mm);
  auto* worldLogical = new G4LogicalVolume(worldSolid, air, "WorldLogical");
  worldLogical->SetUserLimits(new G4UserLimits(10. * mm, DBL_MAX, DBL_MAX, 0., 0.));
  auto* worldPhysical = new G4PVPlacement(nullptr, G4ThreeVector(), worldLogical,
                                          "WorldPhysical", nullptr, false, 0);

  // G4 axes are (input local y, input local z, input thickness x).
  auto* siliconSolid = new G4Box("SiSlabSolid", 18. * mm, 18. * mm, 0.15 * mm);
  auto* siliconLogical = new G4LogicalVolume(siliconSolid, silicon, "SiSlabLogical");
  auto* siliconPhysical = new G4PVPlacement(nullptr, G4ThreeVector(), siliconLogical,
                                            "SiSlabPhysical", worldLogical, false, 0);

  auto* latticeManager = G4LatticeManager::GetLatticeManager();
  auto* siliconLogicalLattice = latticeManager->LoadLattice(silicon, "Si");
  if (!siliconLogicalLattice) throw std::runtime_error("G4CMP failed to load Si lattice");
  auto* siliconPhysicalLattice = new G4LatticePhysical(siliconLogicalLattice);
  siliconPhysicalLattice->SetMillerOrientation(config_.millerH, config_.millerK,
                                                config_.millerL);
  latticeManager->RegisterLattice(siliconPhysical, siliconPhysicalLattice);

  if (!sensitivity_) {
    sensitivity_ = new SiPhononSensitivity("SiPhononAbsorption", config_, groups_, pixels_);
    G4SDManager::GetSDMpointer()->AddNewDetector(sensitivity_);
  }
  siliconLogical->SetSensitiveDetector(sensitivity_);

  sensorSurface_ = new G4CMPSurfaceProperty(
      "SensorSurface", 0., 1., 0., 0., config_.sensorAbsorption, 1.,
      config_.specularProbability, 0.);
  bathSurface_ = new G4CMPSurfaceProperty(
      "BathSurface", 0., 1., 0., 0., config_.bathAbsorption, 1.,
      config_.specularProbability, 0.);

  // sensorAreaScale scales projected area; the physical half-width scales as sqrt(area).
  const G4double sensorHalfWidth = 0.75 * std::sqrt(config_.sensorAreaScale) * mm;
  const G4double padHalfThickness = 0.5 * um;
  auto* padSolid = new G4Box("SensorPadSolid", sensorHalfWidth, sensorHalfWidth,
                             padHalfThickness);
  auto* padLogical = new G4LogicalVolume(padSolid, aluminum, "SensorPadLogical");
  for (const auto& pixel : *pixels_) {
    const G4ThreeVector position(pixel.ymm * mm, pixel.zmm * mm,
                                 -0.15 * mm - padHalfThickness);
    const auto name = "SensorPadPhysical_" + std::to_string(pixel.id);
    auto* padPhysical = new G4PVPlacement(nullptr, position, padLogical, name,
                                          worldLogical, false, pixel.id);
    new G4CMPLogicalBorderSurface("SiToSensor_" + std::to_string(pixel.id),
                                  siliconPhysical, padPhysical, sensorSurface_);
  }
  new G4CMPLogicalBorderSurface("SiToBath", siliconPhysical, worldPhysical,
                                bathSurface_);

  worldLogical->SetVisAttributes(G4VisAttributes::GetInvisible());
  return worldPhysical;
}
