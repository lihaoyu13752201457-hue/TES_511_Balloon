#include <algorithm>
#include <cfloat>
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
#include "G4ProcessManager.hh"
#include "G4RunManager.hh"
#include "G4Step.hh"
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

struct RingSpec {
  int id;
  double radiusMm;
  double survival;
  int nBounce;
};

const RingSpec kRings[4] = {
    {0, 22.5, 0.7979735682819383, 1},
    {1, 30.0, 0.7994297868488935, 2},
    {2, 37.5, 0.7998060205474531, 2},
    {3, 45.0, 0.8018108023727756, 3},
};

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

int NearestRingId(double rMm) {
  int best = 0;
  double bestDist = std::fabs(rMm - kRings[0].radiusMm);
  for (int i = 1; i < 4; ++i) {
    const double dist = std::fabs(rMm - kRings[i].radiusMm);
    if (dist < bestDist) {
      best = i;
      bestDist = dist;
    }
  }
  return best;
}

double SpotD90Cm(const std::vector<double>& xsMm, const std::vector<double>& ysMm) {
  if (xsMm.empty()) return 0.0;
  std::vector<double> radii;
  for (std::size_t i = 0; i < xsMm.size(); ++i) {
    radii.push_back(std::sqrt(xsMm[i] * xsMm[i] + ysMm[i] * ysMm[i]));
  }
  std::sort(radii.begin(), radii.end());
  const std::size_t idx = std::min<std::size_t>(radii.size() - 1, static_cast<std::size_t>(std::ceil(0.9 * radii.size()) - 1));
  return 2.0 * radii[idx] / 10.0;
}

class ChannelRunState {
 public:
  ChannelRunState(const std::string& outDir, double focalLengthMm, double energyKeV)
      : outDir_(outDir),
        focalLengthMm_(focalLengthMm),
        energyKeV_(energyKeV),
        nExit_(0),
        nAbsorb_(0),
        nLeak_(0) {
    EnsureDirectory(outDir_);
    phase_.open((outDir_ + "/phase_space.csv").c_str());
    history_.open((outDir_ + "/optics_history.csv").c_str());
    if (!phase_ || !history_) {
      throw std::runtime_error("cannot open channel output CSV files in: " + outDir_);
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
      int ringId,
      int tileId,
      const G4ThreeVector& pos,
      const G4ThreeVector& inDir,
      const G4ThreeVector& outDir,
      const RingSpec& ring,
      double pAbs,
      double pLeak) {
    history_ << eventId << "," << trackId << ",CHANNEL," << stage << "," << ringId << ","
             << tileId << ",Channel4RingEffective," << energyKeV_ << "," << std::setprecision(10)
             << pos.x() / mm << "," << pos.y() / mm << "," << pos.z() / mm << ","
             << inDir.x() << "," << inDir.y() << "," << inDir.z() << ","
             << outDir.x() << "," << outDir.y() << "," << outDir.z() << ","
             << "," << ring.survival << "," << pAbs << "," << pLeak << ","
             << ring.nBounce << ",1\n";
    if (stage == "EXIT") {
      ++nExit_;
      const double t = (focalLengthMm_ * mm - pos.z()) / outDir.z();
      const G4ThreeVector focus = pos + t * outDir;
      xsMm_.push_back(focus.x() / mm);
      ysMm_.push_back(focus.y() / mm);
      phase_ << eventId << "," << energyKeV_ << "," << focus.x() / mm << ","
             << focus.y() / mm << "," << focalLengthMm_ << "," << outDir.x() << ","
             << outDir.y() << "," << outDir.z() << ",1.0,geant4_channel_4ring_effective\n";
    } else if (stage == "ABSORB") {
      ++nAbsorb_;
    } else if (stage == "LEAK") {
      ++nLeak_;
    }
  }

  void WriteSummary(int nEvents, double apertureRadiusMm, double spotSigmaMm) {
    phase_.flush();
    history_.flush();
    const double areaCm2 = M_PI * (apertureRadiusMm / 10.0) * (apertureRadiusMm / 10.0);
    std::ofstream summary((outDir_ + "/summary.json").c_str());
    summary << "{\n";
    summary << "  \"system\": \"geant4_channel_4ring_effective\",\n";
    summary << "  \"model\": \"geant4_effective_boundary_process_ring_calibrated\",\n";
    summary << "  \"warning\": \"Effective Geant4 4-ring channel scaffold; not wall-by-wall curved channel geometry.\",\n";
    summary << "  \"n_primaries\": " << nEvents << ",\n";
    summary << "  \"n_survived\": " << nExit_ << ",\n";
    summary << "  \"n_absorbed\": " << nAbsorb_ << ",\n";
    summary << "  \"n_leaked\": " << nLeak_ << ",\n";
    summary << "  \"transmissivity\": " << (nEvents ? static_cast<double>(nExit_) / nEvents : 0.0) << ",\n";
    summary << "  \"effective_area_cm2\": " << areaCm2 * (nEvents ? static_cast<double>(nExit_) / nEvents : 0.0) << ",\n";
    summary << "  \"spot_d90_cm\": " << SpotD90Cm(xsMm_, ysMm_) << ",\n";
    summary << "  \"energy_keV\": " << energyKeV_ << ",\n";
    summary << "  \"focal_length_mm\": " << focalLengthMm_ << ",\n";
    summary << "  \"aperture_radius_mm\": " << apertureRadiusMm << ",\n";
    summary << "  \"spot_sigma_mm\": " << spotSigmaMm << "\n";
    summary << "}\n";
  }

 private:
  std::string outDir_;
  double focalLengthMm_;
  double energyKeV_;
  std::ofstream phase_;
  std::ofstream history_;
  long nExit_;
  long nAbsorb_;
  long nLeak_;
  std::vector<double> xsMm_;
  std::vector<double> ysMm_;
};

class ChannelEffectiveProcess : public G4VDiscreteProcess {
 public:
  ChannelEffectiveProcess(ChannelRunState* state, double focalLengthMm, double spotSigmaMm)
      : G4VDiscreteProcess("Channel4RingEffectiveProcess"),
        state_(state),
        focalLengthMm_(focalLengthMm),
        spotSigmaMm_(spotSigmaMm) {}

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
    if (!NameContains(step.GetPostStepPoint()->GetPhysicalVolume(), "ChannelTile") &&
        !NameContains(step.GetPreStepPoint()->GetPhysicalVolume(), "ChannelTile")) {
      return &aParticleChange;
    }
    const G4VPhysicalVolume* volume = step.GetPostStepPoint()->GetPhysicalVolume();
    const int copyNo = volume ? volume->GetCopyNo() : 0;
    const int ringId = std::max(0, std::min(3, copyNo / 1000));
    const int tileId = copyNo % 1000;
    const RingSpec& ring = kRings[ringId];
    const double pLoss = std::max(0.0, 1.0 - ring.survival);
    const double pAbs = 0.75 * pLoss;
    const double pLeak = 0.25 * pLoss;
    const double u = G4UniformRand();
    const G4Event* event = G4RunManager::GetRunManager()->GetCurrentEvent();
    const int eventId = event ? event->GetEventID() : -1;
    const G4ThreeVector pos = step.GetPostStepPoint()->GetPosition();
    const G4ThreeVector inDir = track.GetMomentumDirection().unit();
    if (u < pAbs) {
      state_->Record(eventId, track.GetTrackID(), "ABSORB", ringId, tileId, pos, inDir, G4ThreeVector(), ring, pAbs, pLeak);
      aParticleChange.ProposeTrackStatus(fStopAndKill);
      return &aParticleChange;
    }
    if (u < pAbs + pLeak) {
      state_->Record(eventId, track.GetTrackID(), "LEAK", ringId, tileId, pos, inDir, inDir, ring, pAbs, pLeak);
      aParticleChange.ProposeTrackStatus(fStopAndKill);
      return &aParticleChange;
    }
    const G4ThreeVector target(
        G4RandGauss::shoot(0.0, spotSigmaMm_) * mm,
        G4RandGauss::shoot(0.0, spotSigmaMm_) * mm,
        focalLengthMm_ * mm);
    const G4ThreeVector outDir = (target - pos).unit();
    G4DynamicParticle* secondary =
        new G4DynamicParticle(G4Gamma::GammaDefinition(), outDir, track.GetKineticEnergy());
    aParticleChange.SetNumberOfSecondaries(1);
    aParticleChange.AddSecondary(secondary, pos + 1.0e-5 * mm * outDir, true);
    aParticleChange.ProposeTrackStatus(fStopAndKill);
    state_->Record(eventId, track.GetTrackID(), "EXIT", ringId, tileId, pos, inDir, outDir, ring, pAbs, pLeak);
    return &aParticleChange;
  }

 private:
  ChannelRunState* state_;
  double focalLengthMm_;
  double spotSigmaMm_;
};

class ChannelDetectorConstruction : public G4VUserDetectorConstruction {
 public:
  explicit ChannelDetectorConstruction(int nTiles) : nTiles_(nTiles) {}

  G4VPhysicalVolume* Construct() override {
    G4NistManager* nist = G4NistManager::Instance();
    G4Material* vacuum = nist->FindOrBuildMaterial("G4_Galactic");
    G4Material* silicon = nist->FindOrBuildMaterial("G4_Si");
    G4Box* worldSolid = new G4Box("WorldSolid", 80.0 * mm, 80.0 * mm, 12100.0 * mm);
    G4LogicalVolume* worldLogic = new G4LogicalVolume(worldSolid, vacuum, "WorldLogical");
    G4VPhysicalVolume* world =
        new G4PVPlacement(0, G4ThreeVector(), worldLogic, "World", 0, false, 0);
    G4Box* tileSolid = new G4Box("ChannelTileSolid", 1.2 * mm, 1.2 * mm, 0.05 * mm);
    G4LogicalVolume* tileLogic = new G4LogicalVolume(tileSolid, silicon, "ChannelTileLogical");
    for (int ring = 0; ring < 4; ++ring) {
      for (int tile = 0; tile < nTiles_; ++tile) {
        const double phi = 2.0 * M_PI * static_cast<double>(tile) / static_cast<double>(nTiles_);
        const int copyNo = ring * 1000 + tile;
        new G4PVPlacement(
            0,
            G4ThreeVector(kRings[ring].radiusMm * std::cos(phi) * mm, kRings[ring].radiusMm * std::sin(phi) * mm, 0.0),
            tileLogic,
            "ChannelTile",
            worldLogic,
            false,
            copyNo);
      }
    }
    return world;
  }

 private:
  int nTiles_;
};

class ChannelPhysicsList : public G4VUserPhysicsList {
 public:
  explicit ChannelPhysicsList(ChannelEffectiveProcess* process) : process_(process) {}

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
  ChannelEffectiveProcess* process_;
};

class ChannelPrimaryGenerator : public G4VUserPrimaryGeneratorAction {
 public:
  ChannelPrimaryGenerator(int nTiles, double energyKeV, double apertureRadiusMm)
      : nTiles_(nTiles), apertureRadiusMm_(apertureRadiusMm) {
    gun_ = new G4ParticleGun(1);
    gun_->SetParticleDefinition(G4Gamma::GammaDefinition());
    gun_->SetParticleEnergy(energyKeV * keV);
  }

  ~ChannelPrimaryGenerator() override {
    delete gun_;
  }

  void GeneratePrimaries(G4Event* event) override {
    const double sampledR = apertureRadiusMm_ * std::sqrt(G4UniformRand());
    const double phi = 2.0 * M_PI * G4UniformRand();
    const int ring = NearestRingId(sampledR);
    int tile = static_cast<int>(std::floor(phi / (2.0 * M_PI) * nTiles_));
    if (tile >= nTiles_) tile = nTiles_ - 1;
    const double tilePhi = 2.0 * M_PI * static_cast<double>(tile) / static_cast<double>(nTiles_);
    const double dx = (G4UniformRand() - 0.5) * 1.5;
    const double dy = (G4UniformRand() - 0.5) * 1.5;
    const double x = kRings[ring].radiusMm * std::cos(tilePhi) + dx;
    const double y = kRings[ring].radiusMm * std::sin(tilePhi) + dy;
    gun_->SetParticlePosition(G4ThreeVector(x * mm, y * mm, -5.0 * mm));
    gun_->SetParticleMomentumDirection(G4ThreeVector(0.0, 0.0, 1.0));
    gun_->GeneratePrimaryVertex(event);
  }

 private:
  int nTiles_;
  double apertureRadiusMm_;
  G4ParticleGun* gun_;
};

}  // namespace

int main(int argc, char** argv) {
  int nEvents = 20000;
  std::string outDir = "runs/geant4_channel_4ring_effective";
  long seed = 12345;
  if (argc > 1) nEvents = std::atoi(argv[1]);
  if (argc > 2) outDir = argv[2];
  if (argc > 3) seed = std::atol(argv[3]);

  const int nTiles = 48;
  const double energyKeV = 511.0;
  const double focalLengthMm = 12000.0;
  const double apertureRadiusMm = 45.0;
  const double spotSigmaMm = 36.0 / std::sqrt(-2.0 * std::log(0.1)) / 2.0;
  CLHEP::HepRandom::setTheSeed(seed);

  try {
    ChannelRunState state(outDir, focalLengthMm, energyKeV);
    ChannelEffectiveProcess* process = new ChannelEffectiveProcess(&state, focalLengthMm, spotSigmaMm);
    G4RunManager* runManager = new G4RunManager;
    runManager->SetUserInitialization(new ChannelDetectorConstruction(nTiles));
    runManager->SetUserInitialization(new ChannelPhysicsList(process));
    runManager->SetUserAction(new ChannelPrimaryGenerator(nTiles, energyKeV, apertureRadiusMm));
    runManager->Initialize();
    runManager->BeamOn(nEvents);
    delete runManager;
    state.WriteSummary(nEvents, apertureRadiusMm, spotSigmaMm);
    std::cout << "CHANNEL_4RING_EFFECTIVE_SUMMARY events=" << nEvents
              << " out=" << outDir
              << std::endl;
  } catch (const std::exception& exc) {
    std::cerr << "channel_4ring_effective_demo error: " << exc.what() << std::endl;
    return 1;
  }
  return 0;
}
