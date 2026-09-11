#include <cstdlib>
#include <iostream>

#include "G4Box.hh"
#include "G4Gamma.hh"
#include "G4LogicalVolume.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4ParticleGun.hh"
#include "G4ProcessManager.hh"
#include "G4RunManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPhysicsList.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "Randomize.hh"
#include "optics/GammaChannelReflection.hh"

namespace {

class TwoWallDetectorConstruction : public G4VUserDetectorConstruction {
 public:
  G4VPhysicalVolume* Construct() override {
    G4NistManager* nist = G4NistManager::Instance();
    G4Material* vacuum = nist->FindOrBuildMaterial("G4_Galactic");
    G4Material* wallMaterial = nist->FindOrBuildMaterial("G4_W");

    G4Box* worldSolid = new G4Box("WorldSolid", 20.0 * mm, 5.0 * mm, 25.0 * mm);
    G4LogicalVolume* worldLogic = new G4LogicalVolume(worldSolid, vacuum, "WorldLogical");
    G4VPhysicalVolume* world =
        new G4PVPlacement(0, G4ThreeVector(), worldLogic, "World", 0, false, 0);

    G4Box* wallSolid = new G4Box("ChannelWallSolid", 10.0 * mm, 0.5 * mm, 10.0 * mm);
    G4LogicalVolume* topLogic = new G4LogicalVolume(wallSolid, wallMaterial, "TopChannelWallLogical");
    G4LogicalVolume* bottomLogic = new G4LogicalVolume(wallSolid, wallMaterial, "BottomChannelWallLogical");

    new G4PVPlacement(
        0, G4ThreeVector(0.0, 1.5 * mm, 10.0 * mm), topLogic, "TopChannelWall", worldLogic, false, 0);
    new G4PVPlacement(
        0, G4ThreeVector(0.0, -1.5 * mm, 10.0 * mm), bottomLogic, "BottomChannelWall", worldLogic, false, 0);
    return world;
  }
};

class TwoWallPhysicsList : public G4VUserPhysicsList {
 public:
  explicit TwoWallPhysicsList(optics::GammaChannelReflection* process) : process_(process) {}

  void ConstructParticle() override {
    G4Gamma::GammaDefinition();
  }

  void ConstructProcess() override {
    AddTransportation();
    G4ProcessManager* pm = G4Gamma::GammaDefinition()->GetProcessManager();
    pm->AddDiscreteProcess(process_);
  }

  void SetCuts() override {
    SetCutsWithDefault();
  }

 private:
  optics::GammaChannelReflection* process_;
};

class TwoWallPrimaryGenerator : public G4VUserPrimaryGeneratorAction {
 public:
  TwoWallPrimaryGenerator() {
    gun_ = new G4ParticleGun(1);
    gun_->SetParticleDefinition(G4Gamma::GammaDefinition());
    gun_->SetParticleEnergy(511.0 * keV);
    gun_->SetParticlePosition(G4ThreeVector(0.0, 0.0, -1.0 * mm));
    gun_->SetParticleMomentumDirection(G4ThreeVector(0.0, 0.2, 1.0).unit());
  }

  ~TwoWallPrimaryGenerator() override {
    delete gun_;
  }

  void GeneratePrimaries(G4Event* event) override {
    gun_->GeneratePrimaryVertex(event);
  }

 private:
  G4ParticleGun* gun_;
};

}  // namespace

int main(int argc, char** argv) {
  G4int nEvents = 1;
  G4double R = 1.0;
  G4double A = 0.0;
  G4double T = 0.0;
  if (argc > 1) nEvents = std::atoi(argv[1]);
  if (argc > 4) {
    R = std::atof(argv[2]);
    A = std::atof(argv[3]);
    T = std::atof(argv[4]);
  }

  CLHEP::HepRandom::setTheSeed(12345);
  optics::GammaChannelReflection* process = new optics::GammaChannelReflection();
  process->SetProbabilities(R, A, T);
  process->SetRequiredVolumeToken("ChannelWall");

  G4RunManager* runManager = new G4RunManager;
  runManager->SetUserInitialization(new TwoWallDetectorConstruction());
  runManager->SetUserInitialization(new TwoWallPhysicsList(process));
  runManager->SetUserAction(new TwoWallPrimaryGenerator());
  runManager->Initialize();
  process->ResetCounters();
  runManager->BeamOn(nEvents);

  std::cout << "CHANNEL_TWO_WALL_SUMMARY"
            << " events=" << nEvents
            << " boundary=" << process->GetBoundaryCount()
            << " reflect=" << process->GetReflectCount()
            << " absorb=" << process->GetAbsorbCount()
            << " leak=" << process->GetLeakCount()
            << std::endl;

  delete runManager;
  return 0;
}
