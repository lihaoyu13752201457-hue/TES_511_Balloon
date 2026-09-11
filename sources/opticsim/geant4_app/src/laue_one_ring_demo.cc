#include <cerrno>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/stat.h>
#include <vector>

#include "G4Box.hh"
#include "G4DynamicParticle.hh"
#include "G4Event.hh"
#include "G4Gamma.hh"
#include "G4LogicalVolume.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4ParticleChange.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4ProcessManager.hh"
#include "G4RunManager.hh"
#include "G4Step.hh"
#include "G4StepPoint.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "G4Track.hh"
#include "G4VDiscreteProcess.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPhysicsList.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4VPhysicalVolume.hh"
#include "Randomize.hh"

namespace {

bool DirectoryExists(const std::string& path) {
  struct stat st;
  return stat(path.c_str(), &st) == 0 && S_ISDIR(st.st_mode);
}

void EnsureDirectory(const std::string& path) {
  if (path.empty() || DirectoryExists(path)) return;
  std::string current;
  for (std::size_t i = 0; i < path.size(); ++i) {
    current.push_back(path[i]);
    if (path[i] != '/' && i + 1 != path.size()) continue;
    if (current.empty() || current == "/") continue;
    if (!DirectoryExists(current) && mkdir(current.c_str(), 0755) != 0 && errno != EEXIST) {
      throw std::runtime_error("cannot create directory " + current + ": " + std::strerror(errno));
    }
  }
}

bool NameContains(const G4VPhysicalVolume* volume, const G4String& token) {
  if (volume == 0) return false;
  if (volume->GetName().find(token) != G4String::npos) return true;
  const G4LogicalVolume* logical = volume->GetLogicalVolume();
  return logical != 0 && logical->GetName().find(token) != G4String::npos;
}

class LaueRunState {
 public:
  LaueRunState(const std::string& outDir, double focalLengthMm, double energyKeV)
      : outDir_(outDir),
        focalLengthMm_(focalLengthMm),
        energyKeV_(energyKeV),
        nDiff_(0),
        nAbs_(0),
        nLeak_(0) {
    EnsureDirectory(outDir_);
    phase_.open((outDir_ + "/phase_space.csv").c_str());
    history_.open((outDir_ + "/optics_history.csv").c_str());
    if (!phase_ || !history_) {
      throw std::runtime_error("cannot open Laue output CSV files in: " + outDir_);
    }
    phase_ << "event_id,E_keV,x_mm,y_mm,z_mm,ux,uy,uz,weight,source_tag\n";
    history_ << "event_id,track_id,optics_kind,stage,ring_id,tile_id,surface_id,E_keV,"
             << "x_mm,y_mm,z_mm,ux_in,uy_in,uz_in,ux_out,uy_out,uz_out,"
             << "grazing_angle_rad,p_reflect,p_absorb,p_transmit,n_bounce,weight\n";
  }

  void Record(
      int eventId,
      int trackId,
      const std::string& stage,
      int tileId,
      const G4ThreeVector& pos,
      const G4ThreeVector& inDir,
      const G4ThreeVector& outDir,
      double pDiff,
      double pAbs,
      double pLeak) {
    history_ << eventId << "," << trackId << ",LAUE," << stage << ",0," << tileId
             << ",LaueCrystal," << energyKeV_ << "," << std::setprecision(10)
             << pos.x() / mm << "," << pos.y() / mm << "," << pos.z() / mm << ","
             << inDir.x() << "," << inDir.y() << "," << inDir.z() << ","
             << outDir.x() << "," << outDir.y() << "," << outDir.z() << ","
             << "," << pDiff << "," << pAbs << "," << pLeak << ",1,1\n";
    if (stage == "DIFFRACT") {
      ++nDiff_;
      const double t = (focalLengthMm_ * mm - pos.z()) / outDir.z();
      const G4ThreeVector focus = pos + t * outDir;
      phase_ << eventId << "," << energyKeV_ << "," << std::setprecision(10)
             << focus.x() / mm << "," << focus.y() / mm << "," << focalLengthMm_ << ","
             << outDir.x() << "," << outDir.y() << "," << outDir.z()
             << ",1.0,geant4_laue_one_ring_toy\n";
    } else if (stage == "ABSORB") {
      ++nAbs_;
    } else if (stage == "LEAK") {
      ++nLeak_;
    }
  }

  void WriteSummary(int nEvents, double ringRadiusMm, double spotSigmaMm) {
    phase_.flush();
    history_.flush();
    std::ofstream summary((outDir_ + "/summary.json").c_str());
    summary << "{\n";
    summary << "  \"system\": \"geant4_laue_one_ring_toy\",\n";
    summary << "  \"model\": \"constant_probability_laue_boundary_process\",\n";
    summary << "  \"warning\": \"Toy Laue process with constant diffraction/absorption probabilities; not dynamical diffraction.\",\n";
    summary << "  \"n_primaries\": " << nEvents << ",\n";
    summary << "  \"n_diffracted\": " << nDiff_ << ",\n";
    summary << "  \"n_absorbed\": " << nAbs_ << ",\n";
    summary << "  \"n_leaked\": " << nLeak_ << ",\n";
    summary << "  \"diffraction_fraction\": " << (nEvents ? static_cast<double>(nDiff_) / nEvents : 0.0) << ",\n";
    summary << "  \"energy_keV\": " << energyKeV_ << ",\n";
    summary << "  \"ring_radius_mm\": " << ringRadiusMm << ",\n";
    summary << "  \"focal_length_mm\": " << focalLengthMm_ << ",\n";
    summary << "  \"spot_sigma_mm\": " << spotSigmaMm << "\n";
    summary << "}\n";
  }

 private:
  std::string outDir_;
  double focalLengthMm_;
  double energyKeV_;
  std::ofstream phase_;
  std::ofstream history_;
  long nDiff_;
  long nAbs_;
  long nLeak_;
};

class LaueToyProcess : public G4VDiscreteProcess {
 public:
  LaueToyProcess(LaueRunState* state, double focalLengthMm, double spotSigmaMm, double pDiff, double pAbs)
      : G4VDiscreteProcess("LaueToyProcess"),
        state_(state),
        focalLengthMm_(focalLengthMm),
        spotSigmaMm_(spotSigmaMm),
        pDiff_(pDiff),
        pAbs_(pAbs) {}

  G4bool IsApplicable(const G4ParticleDefinition& particle) override {
    return &particle == G4Gamma::GammaDefinition();
  }

  G4double GetMeanFreePath(const G4Track&, G4double, G4ForceCondition* condition) override {
    *condition = Forced;
    return DBL_MAX;
  }

  G4VParticleChange* PostStepDoIt(const G4Track& track, const G4Step& step) override {
    aParticleChange.Initialize(track);
    if (track.GetDefinition() != G4Gamma::GammaDefinition()) return &aParticleChange;
    if (track.GetParentID() != 0) return &aParticleChange;
    if (step.GetPostStepPoint()->GetStepStatus() != fGeomBoundary) return &aParticleChange;
    if (!NameContains(step.GetPostStepPoint()->GetPhysicalVolume(), "LaueCrystal") &&
        !NameContains(step.GetPreStepPoint()->GetPhysicalVolume(), "LaueCrystal")) {
      return &aParticleChange;
    }

    const G4Event* event = G4RunManager::GetRunManager()->GetCurrentEvent();
    const int eventId = event ? event->GetEventID() : -1;
    const int tileId = step.GetPostStepPoint()->GetPhysicalVolume()
                           ? step.GetPostStepPoint()->GetPhysicalVolume()->GetCopyNo()
                           : -1;
    const G4ThreeVector pos = step.GetPostStepPoint()->GetPosition();
    const G4ThreeVector inDir = track.GetMomentumDirection().unit();
    const double u = G4UniformRand();
    const double pLeak = std::max(0.0, 1.0 - pDiff_ - pAbs_);
    if (u < pAbs_) {
      state_->Record(eventId, track.GetTrackID(), "ABSORB", tileId, pos, inDir, G4ThreeVector(), pDiff_, pAbs_, pLeak);
      aParticleChange.ProposeTrackStatus(fStopAndKill);
      return &aParticleChange;
    }
    if (u > pAbs_ + pDiff_) {
      state_->Record(eventId, track.GetTrackID(), "LEAK", tileId, pos, inDir, inDir, pDiff_, pAbs_, pLeak);
      aParticleChange.ProposeTrackStatus(fStopAndKill);
      return &aParticleChange;
    }

    const G4ThreeVector target(
        G4RandGauss::shoot(0.0, spotSigmaMm_) * mm,
        G4RandGauss::shoot(0.0, spotSigmaMm_) * mm,
        focalLengthMm_ * mm);
    G4ThreeVector outDir = (target - pos).unit();
    G4DynamicParticle* secondary =
        new G4DynamicParticle(G4Gamma::GammaDefinition(), outDir, track.GetKineticEnergy());
    aParticleChange.SetNumberOfSecondaries(1);
    aParticleChange.AddSecondary(secondary, pos + 1.0e-5 * mm * outDir, true);
    aParticleChange.ProposeTrackStatus(fStopAndKill);
    state_->Record(eventId, track.GetTrackID(), "DIFFRACT", tileId, pos, inDir, outDir, pDiff_, pAbs_, pLeak);
    return &aParticleChange;
  }

 private:
  LaueRunState* state_;
  double focalLengthMm_;
  double spotSigmaMm_;
  double pDiff_;
  double pAbs_;
};

class LaueDetectorConstruction : public G4VUserDetectorConstruction {
 public:
  LaueDetectorConstruction(int nTiles, double ringRadiusMm) : nTiles_(nTiles), ringRadiusMm_(ringRadiusMm) {}

  G4VPhysicalVolume* Construct() override {
    G4NistManager* nist = G4NistManager::Instance();
    G4Material* vacuum = nist->FindOrBuildMaterial("G4_Galactic");
    G4Material* ge = nist->FindOrBuildMaterial("G4_Ge");
    G4Box* worldSolid = new G4Box("WorldSolid", 120.0 * mm, 120.0 * mm, 8400.0 * mm);
    G4LogicalVolume* worldLogic = new G4LogicalVolume(worldSolid, vacuum, "WorldLogical");
    G4VPhysicalVolume* world =
        new G4PVPlacement(0, G4ThreeVector(), worldLogic, "World", 0, false, 0);

    G4Box* tileSolid = new G4Box("LaueCrystalSolid", 1.2 * mm, 1.2 * mm, 0.05 * mm);
    G4LogicalVolume* tileLogic = new G4LogicalVolume(tileSolid, ge, "LaueCrystalLogical");
    for (int i = 0; i < nTiles_; ++i) {
      const double phi = 2.0 * M_PI * static_cast<double>(i) / static_cast<double>(nTiles_);
      new G4PVPlacement(
          0,
          G4ThreeVector(ringRadiusMm_ * std::cos(phi) * mm, ringRadiusMm_ * std::sin(phi) * mm, 0.0),
          tileLogic,
          "LaueCrystal",
          worldLogic,
          false,
          i);
    }
    return world;
  }

 private:
  int nTiles_;
  double ringRadiusMm_;
};

class LauePhysicsList : public G4VUserPhysicsList {
 public:
  explicit LauePhysicsList(LaueToyProcess* process) : process_(process) {}

  void ConstructParticle() override {
    G4Gamma::GammaDefinition();
  }

  void ConstructProcess() override {
    AddTransportation();
    G4Gamma::GammaDefinition()->GetProcessManager()->AddDiscreteProcess(process_);
  }

  void SetCuts() override {
    SetCutsWithDefault();
  }

 private:
  LaueToyProcess* process_;
};

class LauePrimaryGenerator : public G4VUserPrimaryGeneratorAction {
 public:
  LauePrimaryGenerator(int nTiles, double ringRadiusMm, double energyKeV)
      : nTiles_(nTiles), ringRadiusMm_(ringRadiusMm) {
    gun_ = new G4ParticleGun(1);
    gun_->SetParticleDefinition(G4Gamma::GammaDefinition());
    gun_->SetParticleEnergy(energyKeV * keV);
  }

  ~LauePrimaryGenerator() override {
    delete gun_;
  }

  void GeneratePrimaries(G4Event* event) override {
    const int tile = event->GetEventID() % nTiles_;
    const double phi = 2.0 * M_PI * static_cast<double>(tile) / static_cast<double>(nTiles_);
    const double dx = (G4UniformRand() - 0.5) * 1.5;
    const double dy = (G4UniformRand() - 0.5) * 1.5;
    const double x = ringRadiusMm_ * std::cos(phi) + dx;
    const double y = ringRadiusMm_ * std::sin(phi) + dy;
    gun_->SetParticlePosition(G4ThreeVector(x * mm, y * mm, -5.0 * mm));
    gun_->SetParticleMomentumDirection(G4ThreeVector(0.0, 0.0, 1.0));
    gun_->GeneratePrimaryVertex(event);
  }

 private:
  int nTiles_;
  double ringRadiusMm_;
  G4ParticleGun* gun_;
};

}  // namespace

int main(int argc, char** argv) {
  int nEvents = 2000;
  std::string outDir = "runs/geant4_laue_one_ring";
  long seed = 12345;
  if (argc > 1) nEvents = std::atoi(argv[1]);
  if (argc > 2) outDir = argv[2];
  if (argc > 3) seed = std::atol(argv[3]);

  const int nTiles = 24;
  const double energyKeV = 511.0;
  const double focalLengthMm = 8300.0;
  const double ringRadiusMm = 61.66;
  const double spotSigmaMm = 4.4;
  CLHEP::HepRandom::setTheSeed(seed);

  try {
    LaueRunState state(outDir, focalLengthMm, energyKeV);
    LaueToyProcess* process = new LaueToyProcess(&state, focalLengthMm, spotSigmaMm, 1.0, 0.0);
    G4RunManager* runManager = new G4RunManager;
    runManager->SetUserInitialization(new LaueDetectorConstruction(nTiles, ringRadiusMm));
    runManager->SetUserInitialization(new LauePhysicsList(process));
    runManager->SetUserAction(new LauePrimaryGenerator(nTiles, ringRadiusMm, energyKeV));
    runManager->Initialize();
    runManager->BeamOn(nEvents);
    delete runManager;
    state.WriteSummary(nEvents, ringRadiusMm, spotSigmaMm);
    std::cout << "LAUE_ONE_RING_SUMMARY events=" << nEvents
              << " out=" << outDir
              << " p_diff=1 p_abs=0"
              << std::endl;
  } catch (const std::exception& exc) {
    std::cerr << "laue_one_ring_demo error: " << exc.what() << std::endl;
    return 1;
  }
  return 0;
}
