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
#include "G4ProcessManager.hh"
#include "G4RunManager.hh"
#include "G4Step.hh"
#include "G4StepPoint.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "G4Track.hh"
#include "G4VDiscreteProcess.hh"
#include "G4VPhysicalVolume.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPhysicsList.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "Randomize.hh"

#include "optics/LaueEfficiencyTable.hh"

namespace {

constexpr double kPi = 3.14159265358979323846;
constexpr double kHcKeVA = 12.398419843320026;

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

double BraggAngleRad(double energyKeV, double dSpacingA) {
  const double arg = (kHcKeVA / energyKeV) / (2.0 * dSpacingA);
  if (arg <= 0.0 || arg >= 1.0) {
    throw std::runtime_error("invalid Bragg argument for Laue table demo");
  }
  return std::asin(arg);
}

double FwhmArcminToSigmaRad(double fwhmArcmin) {
  if (fwhmArcmin <= 0.0) return 0.0;
  return (fwhmArcmin / 60.0) * kPi / 180.0 / 2.355;
}

double ContainmentDiameterCm(const std::vector<G4ThreeVector>& points, double fraction) {
  if (points.empty()) return 0.0;
  std::vector<double> radii;
  radii.reserve(points.size());
  for (const auto& p : points) {
    radii.push_back(std::sqrt(p.x() * p.x() + p.y() * p.y()) / mm);
  }
  std::sort(radii.begin(), radii.end());
  const std::size_t idx = static_cast<std::size_t>(
      std::max(0.0, std::ceil(fraction * static_cast<double>(radii.size())) - 1.0));
  return 2.0 * radii[std::min(idx, radii.size() - 1)] / 10.0;
}

struct WrlSegment {
  G4ThreeVector start;
  G4ThreeVector end;
  std::string stage;
};

struct Options {
  int nEvents = 20000;
  std::string outDir = "runs/geant4_laue_one_ring_table";
  long seed = 12345;
  std::string tablePath = "data/laue/Ge111_480_550keV_darwin_mosaic_table.csv";
  int nTiles = 64;
  double energyKeV = 511.0;
  double focalLengthMm = 8300.0;
  double ringRadiusMm = 61.6618;
  double dSpacingA = 3.266;
  double sourceJitterMm = 1.5;
  std::string material = "Ge";
  int h = 1;
  int k = 1;
  int l = 1;
};

void PrintUsage(const char* argv0) {
  std::cout
      << "Usage: " << argv0 << " [options]\n"
      << "  --n N\n"
      << "  --out DIR\n"
      << "  --seed SEED\n"
      << "  --efficiency-table PATH\n"
      << "  --n-tiles N\n"
      << "  --energy-keV E\n"
      << "  --focal-mm MM\n"
      << "  --ring-radius-mm MM\n";
}

Options ParseOptions(int argc, char** argv) {
  Options opt;
  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    auto requireValue = [&](const std::string& name) -> const char* {
      if (i + 1 >= argc) {
        throw std::runtime_error("missing value for " + name);
      }
      return argv[++i];
    };
    if (arg == "--help" || arg == "-h") {
      PrintUsage(argv[0]);
      std::exit(0);
    } else if (arg == "--n") {
      opt.nEvents = std::atoi(requireValue(arg));
    } else if (arg == "--out") {
      opt.outDir = requireValue(arg);
    } else if (arg == "--seed") {
      opt.seed = std::atol(requireValue(arg));
    } else if (arg == "--efficiency-table") {
      opt.tablePath = requireValue(arg);
    } else if (arg == "--n-tiles") {
      opt.nTiles = std::atoi(requireValue(arg));
    } else if (arg == "--energy-keV") {
      opt.energyKeV = std::atof(requireValue(arg));
    } else if (arg == "--focal-mm") {
      opt.focalLengthMm = std::atof(requireValue(arg));
    } else if (arg == "--ring-radius-mm") {
      opt.ringRadiusMm = std::atof(requireValue(arg));
    } else {
      std::ostringstream msg;
      msg << "unknown option: " << arg;
      throw std::runtime_error(msg.str());
    }
  }
  if (opt.nEvents <= 0 || opt.nTiles <= 0 || opt.energyKeV <= 0.0 ||
      opt.focalLengthMm <= 0.0 || opt.ringRadiusMm <= 0.0) {
    throw std::runtime_error("invalid non-positive Laue table demo option");
  }
  return opt;
}

class LaueTableRunState {
 public:
  LaueTableRunState(const Options& opt, const optics::LaueEfficiencyTable& table)
      : opt_(opt),
        table_(table),
        nDiff_(0),
        nAbs_(0),
        nLeak_(0),
        sumPDiff_(0.0),
        sumPAbs_(0.0),
        sumPTrans_(0.0),
        sumAbsDeltaTheta_(0.0) {
    EnsureDirectory(opt_.outDir);
    phase_.open((opt_.outDir + "/phase_space.csv").c_str());
    history_.open((opt_.outDir + "/optics_history.csv").c_str());
    if (!phase_ || !history_) {
      throw std::runtime_error("cannot open Laue table output CSV files in: " + opt_.outDir);
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
      const optics::LaueEfficiencyRow& row,
      double deltaThetaRad) {
    ++nRecords_;
    sumPDiff_ += row.pDiff;
    sumPAbs_ += row.pAbs;
    sumPTrans_ += row.pTrans;
    sumAbsDeltaTheta_ += std::fabs(deltaThetaRad);
    tableSources_.push_back(row.source);

    history_ << eventId << "," << trackId << ",LAUE," << stage << ",0," << tileId
             << ",LaueCrystalTable," << opt_.energyKeV << "," << std::setprecision(10)
             << pos.x() / mm << "," << pos.y() / mm << "," << pos.z() / mm << ","
             << inDir.x() << "," << inDir.y() << "," << inDir.z() << ","
             << outDir.x() << "," << outDir.y() << "," << outDir.z() << ","
             << deltaThetaRad << "," << row.pDiff << "," << row.pAbs << ","
             << row.pTrans << ",1,1\n";

    if (stage == "DIFFRACT") {
      ++nDiff_;
      const double t = (opt_.focalLengthMm * mm - pos.z()) / outDir.z();
      const G4ThreeVector focus = pos + t * outDir;
      focusPoints_.push_back(focus);
      phase_ << eventId << "," << opt_.energyKeV << "," << std::setprecision(10)
             << focus.x() / mm << "," << focus.y() / mm << "," << opt_.focalLengthMm
             << "," << outDir.x() << "," << outDir.y() << "," << outDir.z()
             << ",1.0,geant4_laue_one_ring_table\n";
      AddWrlSegment(pos, focus, "DIFFRACT");
    } else if (stage == "ABSORB") {
      ++nAbs_;
      AddWrlSegment(pos, pos + 20.0 * mm * inDir, "ABSORB");
    } else if (stage == "LEAK") {
      ++nLeak_;
      const double t = (opt_.focalLengthMm * mm - pos.z()) / inDir.z();
      AddWrlSegment(pos, pos + t * inDir, "LEAK");
    }
  }

  void WriteSummary() {
    phase_.flush();
    history_.flush();
    WriteWrl(opt_.outDir + "/laue_table_scene.wrl");

    std::ofstream summary((opt_.outDir + "/summary.json").c_str());
    const double n = static_cast<double>(opt_.nEvents);
    summary << "{\n";
    summary << "  \"system\": \"geant4_laue_one_ring_table\",\n";
    summary << "  \"model\": \"table_driven_laue_boundary_process_v0\",\n";
    summary << "  \"warning\": \"Table-driven Laue process infrastructure. The default table is a placeholder gaussian mosaic acceptance, not a benchmarked dynamical-diffraction table.\",\n";
    summary << "  \"geant4_bottom_code_modified\": false,\n";
    summary << "  \"geant4_bottom_code_note\": \"No Geant4 source or MEGAlib Geant4 installation was modified.\",\n";
    summary << "  \"n_primaries\": " << opt_.nEvents << ",\n";
    summary << "  \"n_diffracted\": " << nDiff_ << ",\n";
    summary << "  \"n_absorbed\": " << nAbs_ << ",\n";
    summary << "  \"n_leaked\": " << nLeak_ << ",\n";
    summary << "  \"diffraction_fraction\": " << (n ? static_cast<double>(nDiff_) / n : 0.0) << ",\n";
    summary << "  \"absorption_fraction\": " << (n ? static_cast<double>(nAbs_) / n : 0.0) << ",\n";
    summary << "  \"leak_fraction\": " << (n ? static_cast<double>(nLeak_) / n : 0.0) << ",\n";
    summary << "  \"mean_p_diff\": " << (nRecords_ ? sumPDiff_ / nRecords_ : 0.0) << ",\n";
    summary << "  \"mean_p_abs\": " << (nRecords_ ? sumPAbs_ / nRecords_ : 0.0) << ",\n";
    summary << "  \"mean_p_trans\": " << (nRecords_ ? sumPTrans_ / nRecords_ : 0.0) << ",\n";
    summary << "  \"mean_abs_delta_theta_rad\": " << (nRecords_ ? sumAbsDeltaTheta_ / nRecords_ : 0.0) << ",\n";
    summary << "  \"spot_d90_cm\": " << ContainmentDiameterCm(focusPoints_, 0.9) << ",\n";
    summary << "  \"energy_keV\": " << opt_.energyKeV << ",\n";
    summary << "  \"material\": \"" << opt_.material << "\",\n";
    summary << "  \"hkl\": [" << opt_.h << ", " << opt_.k << ", " << opt_.l << "],\n";
    summary << "  \"theta_B_rad\": " << BraggAngleRad(opt_.energyKeV, opt_.dSpacingA) << ",\n";
    summary << "  \"ring_radius_mm\": " << opt_.ringRadiusMm << ",\n";
    summary << "  \"focal_length_mm\": " << opt_.focalLengthMm << ",\n";
    summary << "  \"n_tiles\": " << opt_.nTiles << ",\n";
    summary << "  \"efficiency_table\": \"" << opt_.tablePath << "\",\n";
    summary << "  \"efficiency_table_rows\": " << table_.rows().size() << ",\n";
    summary << "  \"visualization_wrl\": \"" << opt_.outDir << "/laue_table_scene.wrl\"\n";
    summary << "}\n";
  }

 private:
  void AddWrlSegment(const G4ThreeVector& start, const G4ThreeVector& end, const std::string& stage) {
    if (wrlSegments_.size() >= 160) return;
    wrlSegments_.push_back({start, end, stage});
  }

  void WriteWrl(const std::string& path) const {
    std::ofstream wrl(path.c_str());
    wrl << "#VRML V2.0 utf8\n";
    wrl << "WorldInfo { title \"Geant4 11.4 table-driven Laue one-ring optics\" }\n";
    wrl << "Viewpoint { position 0 -260 120 orientation 1 0 0 1.1 description \"Laue one-ring overview\" }\n";
    wrl << "Background { skyColor [ 1 1 1 ] }\n";

    wrl << "Transform { translation 0 0 0 children [ Shape { appearance Appearance { material Material { diffuseColor 0.1 0.5 0.85 transparency 0.35 } } geometry Cylinder { radius "
        << opt_.ringRadiusMm << " height 0.4 } } ] }\n";
    wrl << "Transform { translation 0 0 " << opt_.focalLengthMm
        << " children [ Shape { appearance Appearance { material Material { diffuseColor 0.9 0.1 0.1 } } geometry Sphere { radius 4 } } ] }\n";

    for (int i = 0; i < opt_.nTiles; ++i) {
      const double phi = 2.0 * kPi * static_cast<double>(i) / static_cast<double>(opt_.nTiles);
      const double x = opt_.ringRadiusMm * std::cos(phi);
      const double y = opt_.ringRadiusMm * std::sin(phi);
      wrl << "Transform { translation " << x << " " << y << " 0 children [ Shape { appearance Appearance { material Material { diffuseColor 0.0 0.55 0.25 } } geometry Box { size 2.4 2.4 0.3 } } ] }\n";
    }

    auto writeSegments = [&](const std::string& stage, double r, double g, double b) {
      std::vector<const WrlSegment*> selected;
      for (const auto& seg : wrlSegments_) {
        if (seg.stage == stage) selected.push_back(&seg);
      }
      if (selected.empty()) return;
      wrl << "Shape { appearance Appearance { material Material { emissiveColor "
          << r << " " << g << " " << b << " diffuseColor " << r << " " << g << " " << b
          << " } } geometry IndexedLineSet { coord Coordinate { point [\n";
      for (const auto* seg : selected) {
        wrl << seg->start.x() / mm << " " << seg->start.y() / mm << " " << seg->start.z() / mm << ",\n";
        wrl << seg->end.x() / mm << " " << seg->end.y() / mm << " " << seg->end.z() / mm << ",\n";
      }
      wrl << "] } coordIndex [\n";
      for (std::size_t i = 0; i < selected.size(); ++i) {
        wrl << 2 * i << ", " << 2 * i + 1 << ", -1,\n";
      }
      wrl << "] } }\n";
    };
    writeSegments("DIFFRACT", 0.9, 0.05, 0.05);
    writeSegments("LEAK", 0.45, 0.45, 0.45);
    writeSegments("ABSORB", 0.95, 0.6, 0.0);
  }

  Options opt_;
  const optics::LaueEfficiencyTable& table_;
  std::ofstream phase_;
  std::ofstream history_;
  long nDiff_;
  long nAbs_;
  long nLeak_;
  long nRecords_ = 0;
  double sumPDiff_;
  double sumPAbs_;
  double sumPTrans_;
  double sumAbsDeltaTheta_;
  std::vector<std::string> tableSources_;
  std::vector<G4ThreeVector> focusPoints_;
  std::vector<WrlSegment> wrlSegments_;
};

class LaueTableProcess : public G4VDiscreteProcess {
 public:
  LaueTableProcess(
      LaueTableRunState* state,
      const Options& opt,
      const optics::LaueEfficiencyTable& table)
      : G4VDiscreteProcess("LaueTableProcess"),
        state_(state),
        opt_(opt),
        table_(table) {}

  G4bool IsApplicable(const G4ParticleDefinition& particle) override {
    return &particle == G4Gamma::GammaDefinition();
  }

  G4double GetMeanFreePath(const G4Track&, G4double, G4ForceCondition* condition) override {
    *condition = StronglyForced;
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
    const double radiusMm = pos.perp() / mm;
    const double localTwoTheta = std::atan2(radiusMm, opt_.focalLengthMm - pos.z() / mm);
    const double thetaLocal = 0.5 * localTwoTheta;
    const double thetaB = BraggAngleRad(opt_.energyKeV, opt_.dSpacingA);
    const double deltaTheta = thetaLocal - thetaB;
    const optics::LaueEfficiencyRow probs =
        table_.Lookup(opt_.energyKeV, deltaTheta, opt_.material, opt_.h, opt_.k, opt_.l);

    const double u = G4UniformRand();
    if (u < probs.pAbs) {
      state_->Record(eventId, track.GetTrackID(), "ABSORB", tileId, pos, inDir, G4ThreeVector(), probs, deltaTheta);
      aParticleChange.ProposeTrackStatus(fStopAndKill);
      return &aParticleChange;
    }
    if (u >= probs.pAbs + probs.pDiff) {
      state_->Record(eventId, track.GetTrackID(), "LEAK", tileId, pos, inDir, inDir, probs, deltaTheta);
      aParticleChange.ProposeTrackStatus(fStopAndKill);
      return &aParticleChange;
    }

    const double spotSigmaMm = FwhmArcminToSigmaRad(probs.mosaicFwhmArcmin) * opt_.focalLengthMm;
    const G4ThreeVector target(
        G4RandGauss::shoot(0.0, spotSigmaMm) * mm,
        G4RandGauss::shoot(0.0, spotSigmaMm) * mm,
        opt_.focalLengthMm * mm);
    const G4ThreeVector outDir = (target - pos).unit();
    G4DynamicParticle* secondary =
        new G4DynamicParticle(G4Gamma::GammaDefinition(), outDir, track.GetKineticEnergy());
    aParticleChange.SetNumberOfSecondaries(1);
    aParticleChange.AddSecondary(secondary, pos + 1.0e-5 * mm * outDir, true);
    aParticleChange.ProposeTrackStatus(fStopAndKill);
    state_->Record(eventId, track.GetTrackID(), "DIFFRACT", tileId, pos, inDir, outDir, probs, deltaTheta);
    return &aParticleChange;
  }

 private:
  LaueTableRunState* state_;
  Options opt_;
  const optics::LaueEfficiencyTable& table_;
};

class LaueTableDetectorConstruction : public G4VUserDetectorConstruction {
 public:
  explicit LaueTableDetectorConstruction(const Options& opt) : opt_(opt) {}

  G4VPhysicalVolume* Construct() override {
    G4NistManager* nist = G4NistManager::Instance();
    G4Material* vacuum = nist->FindOrBuildMaterial("G4_Galactic");
    G4Material* ge = nist->FindOrBuildMaterial("G4_Ge");
    G4Box* worldSolid = new G4Box("WorldSolid", 140.0 * mm, 140.0 * mm, 8500.0 * mm);
    G4LogicalVolume* worldLogic = new G4LogicalVolume(worldSolid, vacuum, "WorldLogical");
    G4VPhysicalVolume* world =
        new G4PVPlacement(0, G4ThreeVector(), worldLogic, "World", 0, false, 0);

    G4Box* tileSolid = new G4Box("LaueCrystalSolid", 1.2 * mm, 1.2 * mm, 0.05 * mm);
    G4LogicalVolume* tileLogic = new G4LogicalVolume(tileSolid, ge, "LaueCrystalLogical");
    for (int i = 0; i < opt_.nTiles; ++i) {
      const double phi = 2.0 * kPi * static_cast<double>(i) / static_cast<double>(opt_.nTiles);
      new G4PVPlacement(
          0,
          G4ThreeVector(opt_.ringRadiusMm * std::cos(phi) * mm, opt_.ringRadiusMm * std::sin(phi) * mm, 0.0),
          tileLogic,
          "LaueCrystal",
          worldLogic,
          false,
          i);
    }
    return world;
  }

 private:
  Options opt_;
};

class LaueTablePhysicsList : public G4VUserPhysicsList {
 public:
  explicit LaueTablePhysicsList(LaueTableProcess* process) : process_(process) {}

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
  LaueTableProcess* process_;
};

class LaueTablePrimaryGenerator : public G4VUserPrimaryGeneratorAction {
 public:
  explicit LaueTablePrimaryGenerator(const Options& opt) : opt_(opt) {
    gun_ = new G4ParticleGun(1);
    gun_->SetParticleDefinition(G4Gamma::GammaDefinition());
    gun_->SetParticleEnergy(opt_.energyKeV * keV);
  }

  ~LaueTablePrimaryGenerator() override {
    delete gun_;
  }

  void GeneratePrimaries(G4Event* event) override {
    const int tile = event->GetEventID() % opt_.nTiles;
    const double phi = 2.0 * kPi * static_cast<double>(tile) / static_cast<double>(opt_.nTiles);
    const double dx = (G4UniformRand() - 0.5) * opt_.sourceJitterMm;
    const double dy = (G4UniformRand() - 0.5) * opt_.sourceJitterMm;
    const double x = opt_.ringRadiusMm * std::cos(phi) + dx;
    const double y = opt_.ringRadiusMm * std::sin(phi) + dy;
    gun_->SetParticlePosition(G4ThreeVector(x * mm, y * mm, -5.0 * mm));
    gun_->SetParticleMomentumDirection(G4ThreeVector(0.0, 0.0, 1.0));
    gun_->GeneratePrimaryVertex(event);
  }

 private:
  Options opt_;
  G4ParticleGun* gun_;
};

}  // namespace

int main(int argc, char** argv) {
  try {
    const Options opt = ParseOptions(argc, argv);
    CLHEP::HepRandom::setTheSeed(opt.seed);
    const optics::LaueEfficiencyTable table = optics::LaueEfficiencyTable::FromCsv(opt.tablePath);
    LaueTableRunState state(opt, table);
    LaueTableProcess* process = new LaueTableProcess(&state, opt, table);
    G4RunManager* runManager = new G4RunManager;
    runManager->SetUserInitialization(new LaueTableDetectorConstruction(opt));
    runManager->SetUserInitialization(new LaueTablePhysicsList(process));
    runManager->SetUserAction(new LaueTablePrimaryGenerator(opt));
    runManager->Initialize();
    runManager->BeamOn(opt.nEvents);
    delete runManager;
    state.WriteSummary();
    std::cout << "LAUE_ONE_RING_TABLE_SUMMARY events=" << opt.nEvents
              << " out=" << opt.outDir
              << " table=" << opt.tablePath
              << std::endl;
  } catch (const std::exception& exc) {
    std::cerr << "laue_one_ring_table_demo error: " << exc.what() << std::endl;
    return 1;
  }
  return 0;
}
