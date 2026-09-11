#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <sys/stat.h>
#include <vector>

#include "G4Box.hh"
#include "G4Event.hh"
#include "G4Gamma.hh"
#include "G4LogicalVolume.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4ParticleGun.hh"
#include "G4ProcessManager.hh"
#include "G4RotationMatrix.hh"
#include "G4RunManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPhysicsList.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "Randomize.hh"
#include "optics/GammaChannelReflection.hh"

namespace {

struct Options {
  int nEvents = 1000;
  double energyKeV = 511.0;
  double thetaRad = 1.5e-4;
  double lengthMm = 46.0;
  double halfGapMm = 0.001;
  double wallThicknessMm = 0.010;
  double widthMm = 10.0;
  double bendAngleRad = 3.0e-4;
  double focalLengthMm = 12000.0;
  int segments = 64;
  double R = 1.0;
  double A = 0.0;
  double T = 0.0;
  std::string tablePath;
  std::string stackId = "WSi_30_150";
  std::string outDir = "runs/geant4_channel_single_curved";
  long seed = 20260517;
};

struct EventResult {
  bool hasHistory = false;
  bool lost = false;
  std::string lastAction = "PASS";
  G4ThreeVector lastPositionMm;
  G4ThreeVector lastDirection;
  int nBoundary = 0;
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

Options ParseOptions(int argc, char** argv) {
  Options opts;
  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    auto value = [&](const std::string& name) -> std::string {
      if (i + 1 >= argc) throw std::runtime_error("missing value for " + name);
      return argv[++i];
    };
    if (arg == "--n") {
      opts.nEvents = std::stoi(value(arg));
    } else if (arg == "--energy-keV") {
      opts.energyKeV = std::stod(value(arg));
    } else if (arg == "--theta-rad") {
      opts.thetaRad = std::stod(value(arg));
    } else if (arg == "--length-mm") {
      opts.lengthMm = std::stod(value(arg));
    } else if (arg == "--half-gap-mm") {
      opts.halfGapMm = std::stod(value(arg));
    } else if (arg == "--bend-angle-rad") {
      opts.bendAngleRad = std::stod(value(arg));
    } else if (arg == "--segments") {
      opts.segments = std::stoi(value(arg));
    } else if (arg == "--reflectivity-table") {
      opts.tablePath = value(arg);
    } else if (arg == "--stack-id") {
      opts.stackId = value(arg);
    } else if (arg == "--R") {
      opts.R = std::stod(value(arg));
    } else if (arg == "--A") {
      opts.A = std::stod(value(arg));
    } else if (arg == "--T") {
      opts.T = std::stod(value(arg));
    } else if (arg == "--out") {
      opts.outDir = value(arg);
    } else if (arg == "--seed") {
      opts.seed = std::stol(value(arg));
    } else {
      throw std::runtime_error("unknown argument: " + arg);
    }
  }
  if (opts.segments < 1) throw std::runtime_error("--segments must be positive");
  return opts;
}

double ArcRadiusMm(const Options& opts) {
  if (std::fabs(opts.bendAngleRad) < 1.0e-12) return 1.0e30;
  return opts.lengthMm / opts.bendAngleRad;
}

G4ThreeVector CenterlinePositionMm(const Options& opts, double theta) {
  if (std::fabs(opts.bendAngleRad) < 1.0e-12) {
    return G4ThreeVector(0.0, 0.0, theta);
  }
  const double radius = ArcRadiusMm(opts);
  return G4ThreeVector(0.0, radius * (1.0 - std::cos(theta)), radius * std::sin(theta));
}

G4ThreeVector Tangent(double theta) {
  return G4ThreeVector(0.0, std::sin(theta), std::cos(theta)).unit();
}

G4ThreeVector Normal(double theta) {
  return G4ThreeVector(0.0, std::cos(theta), -std::sin(theta)).unit();
}

double SpotD90Cm(const std::vector<double>& xs, const std::vector<double>& ys) {
  if (xs.empty()) return 0.0;
  std::vector<double> radii;
  for (std::size_t i = 0; i < xs.size(); ++i) {
    radii.push_back(std::sqrt(xs[i] * xs[i] + ys[i] * ys[i]));
  }
  std::sort(radii.begin(), radii.end());
  const std::size_t idx =
      std::min<std::size_t>(radii.size() - 1, static_cast<std::size_t>(std::ceil(0.9 * radii.size()) - 1));
  return 2.0 * radii[idx] / 10.0;
}

class CurvedChannelConstruction : public G4VUserDetectorConstruction {
 public:
  explicit CurvedChannelConstruction(const Options& opts) : opts_(opts) {}

  G4VPhysicalVolume* Construct() override {
    G4NistManager* nist = G4NistManager::Instance();
    G4Material* vacuum = nist->FindOrBuildMaterial("G4_Galactic");
    G4Material* wallMaterial = nist->FindOrBuildMaterial("G4_W");

    const double worldY = std::max(10.0, 5.0 + opts_.halfGapMm + opts_.wallThicknessMm + std::fabs(opts_.lengthMm * opts_.bendAngleRad));
    G4Box* worldSolid =
        new G4Box("WorldSolid", opts_.widthMm * mm, worldY * mm, (opts_.lengthMm / 2.0 + 10.0) * mm);
    G4LogicalVolume* worldLogic = new G4LogicalVolume(worldSolid, vacuum, "WorldLogical");
    G4VPhysicalVolume* world =
        new G4PVPlacement(0, G4ThreeVector(), worldLogic, "World", 0, false, 0);

    const double segLen = opts_.lengthMm / opts_.segments;
    G4Box* wallSolid =
        new G4Box("CurvedChannelWallSolid", opts_.widthMm / 2.0 * mm, opts_.wallThicknessMm / 2.0 * mm, segLen / 2.0 * mm);
    G4LogicalVolume* topLogic = new G4LogicalVolume(wallSolid, wallMaterial, "CurvedTopChannelWallLogical");
    G4LogicalVolume* bottomLogic = new G4LogicalVolume(wallSolid, wallMaterial, "CurvedBottomChannelWallLogical");

    for (int i = 0; i < opts_.segments; ++i) {
      const double f = (static_cast<double>(i) + 0.5) / opts_.segments - 0.5;
      const double theta = f * opts_.bendAngleRad;
      const double s = f * opts_.lengthMm;
      const G4ThreeVector center = std::fabs(opts_.bendAngleRad) < 1.0e-12
                                      ? G4ThreeVector(0.0, 0.0, s)
                                      : CenterlinePositionMm(opts_, theta);
      const G4ThreeVector normal = Normal(theta);
      const double wallCenterOffsetMm = opts_.halfGapMm + opts_.wallThicknessMm / 2.0;
      G4RotationMatrix* rotation = new G4RotationMatrix();
      rotation->rotateX(-theta);
      G4RotationMatrix* rotation2 = new G4RotationMatrix();
      rotation2->rotateX(-theta);

      new G4PVPlacement(
          rotation,
          (center + wallCenterOffsetMm * normal) * mm,
          topLogic,
          "CurvedTopChannelWall_" + std::to_string(i),
          worldLogic,
          false,
          10000 + i);
      new G4PVPlacement(
          rotation2,
          (center - wallCenterOffsetMm * normal) * mm,
          bottomLogic,
          "CurvedBottomChannelWall_" + std::to_string(i),
          worldLogic,
          false,
          20000 + i);
    }
    return world;
  }

 private:
  Options opts_;
};

class CurvedChannelPhysicsList : public G4VUserPhysicsList {
 public:
  explicit CurvedChannelPhysicsList(optics::GammaChannelReflection* process) : process_(process) {}

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

class CurvedChannelPrimaryGenerator : public G4VUserPrimaryGeneratorAction {
 public:
  explicit CurvedChannelPrimaryGenerator(const Options& opts) : opts_(opts) {
    gun_ = new G4ParticleGun(1);
    gun_->SetParticleDefinition(G4Gamma::GammaDefinition());
    gun_->SetParticleEnergy(opts_.energyKeV * keV);
  }

  ~CurvedChannelPrimaryGenerator() override {
    delete gun_;
  }

  void GeneratePrimaries(G4Event* event) override {
    const double thetaFront = -0.5 * opts_.bendAngleRad;
    const G4ThreeVector center = std::fabs(opts_.bendAngleRad) < 1.0e-12
                                    ? G4ThreeVector(0.0, 0.0, -0.5 * opts_.lengthMm + 1.0e-6)
                                    : CenterlinePositionMm(opts_, thetaFront) + 1.0e-6 * Tangent(thetaFront);
    const G4ThreeVector direction = (Tangent(thetaFront) + opts_.thetaRad * Normal(thetaFront)).unit();
    gun_->SetParticlePosition(center * mm);
    gun_->SetParticleMomentumDirection(direction);
    gun_->GeneratePrimaryVertex(event);
  }

 private:
  Options opts_;
  G4ParticleGun* gun_;
};

void WriteHistory(const Options& opts, const optics::GammaChannelReflection& process) {
  std::ofstream out((opts.outDir + "/optics_history.csv").c_str());
  out << "source_event_id,track_id,boundary_index,ring_id,segment_id,surface_id,E_keV,"
      << "theta_grazing_rad,R,A,T,u_before_x,u_before_y,u_before_z,"
      << "u_after_x,u_after_y,u_after_z,x_mm,y_mm,z_mm,action\n";
  for (const auto& row : process.GetHistory()) {
    const int ringId = row.surfaceCopyNo >= 0 ? row.surfaceCopyNo / 10000 : 0;
    const int segmentId = row.surfaceCopyNo >= 0 ? row.surfaceCopyNo % 10000 : 0;
    out << row.sourceEventId << "," << row.trackId << "," << row.boundaryIndex << ","
        << ringId << "," << segmentId << "," << row.surfaceName << "," << std::setprecision(12)
        << row.energyKeV << "," << row.thetaGrazingRad << "," << row.probabilities.R << ","
        << row.probabilities.A << "," << row.probabilities.T << ","
        << row.directionBefore.x() << "," << row.directionBefore.y() << ","
        << row.directionBefore.z() << "," << row.directionAfter.x() << ","
        << row.directionAfter.y() << "," << row.directionAfter.z() << ","
        << row.positionMm.x() << "," << row.positionMm.y() << "," << row.positionMm.z()
        << "," << row.action << "\n";
  }
}

void WritePhaseAndSummary(const Options& opts, const optics::GammaChannelReflection& process) {
  std::vector<EventResult> events(opts.nEvents);
  double thetaSum = 0.0;
  int thetaCount = 0;
  for (const auto& row : process.GetHistory()) {
    if (row.sourceEventId < 0 || row.sourceEventId >= opts.nEvents) continue;
    EventResult& ev = events[row.sourceEventId];
    ev.hasHistory = true;
    ev.lastAction = row.action;
    ev.lastPositionMm = row.positionMm;
    ev.lastDirection = row.directionAfter;
    ev.nBoundary += 1;
    if (row.action == "ABSORB" || row.action == "LEAK") ev.lost = true;
    thetaSum += row.thetaGrazingRad;
    thetaCount += 1;
  }

  const double thetaFront = -0.5 * opts.bendAngleRad;
  const G4ThreeVector initialPos = std::fabs(opts.bendAngleRad) < 1.0e-12
                                      ? G4ThreeVector(0.0, 0.0, -0.5 * opts.lengthMm + 1.0e-6)
                                      : CenterlinePositionMm(opts, thetaFront) + 1.0e-6 * Tangent(thetaFront);
  const G4ThreeVector initialDir = (Tangent(thetaFront) + opts.thetaRad * Normal(thetaFront)).unit();

  std::ofstream phase((opts.outDir + "/phase_space.csv").c_str());
  phase << "event_id,E_keV,x_mm,y_mm,z_mm,ux,uy,uz,weight,source_tag\n";
  std::vector<double> xs;
  std::vector<double> ys;
  int nSurvived = 0;
  int nZeroBoundary = 0;
  int nWithBoundary = 0;
  int maxBounces = 0;
  for (int i = 0; i < opts.nEvents; ++i) {
    const EventResult& ev = events[i];
    if (!ev.hasHistory) ++nZeroBoundary;
    if (ev.hasHistory) ++nWithBoundary;
    maxBounces = std::max(maxBounces, ev.nBoundary);
    if (ev.lost) continue;
    const G4ThreeVector pos = ev.hasHistory ? ev.lastPositionMm : initialPos;
    const G4ThreeVector dir = ev.hasHistory ? ev.lastDirection : initialDir;
    if (dir.z() <= 0.0) continue;
    const double t = (opts.focalLengthMm - pos.z()) / dir.z();
    const G4ThreeVector focus = pos + t * dir;
    phase << i << "," << opts.energyKeV << "," << focus.x() << "," << focus.y() << ","
          << opts.focalLengthMm << "," << dir.x() << "," << dir.y() << "," << dir.z()
          << ",1.0,geant4_channel_single_curved\n";
    xs.push_back(focus.x());
    ys.push_back(focus.y());
    ++nSurvived;
  }

  std::ofstream summary((opts.outDir + "/summary.json").c_str());
  summary << "{\n";
  summary << "  \"system\": \"geant4_channel_single_curved\",\n";
  summary << "  \"model\": \"" << (opts.tablePath.empty() ? "segmented_curved_constant_RAT" : "segmented_curved_table_RAT") << "\",\n";
  summary << "  \"warning\": \"Segmented single-channel curved-wall optics v0; not yet the full four-ring wall-by-wall system.\",\n";
  summary << "  \"n_primaries\": " << opts.nEvents << ",\n";
  summary << "  \"n_boundary\": " << process.GetBoundaryCount() << ",\n";
  summary << "  \"n_reflect\": " << process.GetReflectCount() << ",\n";
  summary << "  \"n_absorb\": " << process.GetAbsorbCount() << ",\n";
  summary << "  \"n_leak\": " << process.GetLeakCount() << ",\n";
  summary << "  \"n_survived\": " << nSurvived << ",\n";
  summary << "  \"n_zero_boundary\": " << nZeroBoundary << ",\n";
  summary << "  \"n_with_boundary\": " << nWithBoundary << ",\n";
  summary << "  \"max_boundary_per_event\": " << maxBounces << ",\n";
  summary << "  \"survival_fraction\": " << std::setprecision(12)
          << (opts.nEvents ? static_cast<double>(nSurvived) / opts.nEvents : 0.0) << ",\n";
  summary << "  \"mean_grazing_angle_rad\": "
          << (thetaCount ? thetaSum / thetaCount : 0.0) << ",\n";
  summary << "  \"spot_d90_cm\": " << SpotD90Cm(xs, ys) << ",\n";
  summary << "  \"energy_keV\": " << opts.energyKeV << ",\n";
  summary << "  \"length_mm\": " << opts.lengthMm << ",\n";
  summary << "  \"half_gap_mm\": " << opts.halfGapMm << ",\n";
  summary << "  \"bend_angle_rad\": " << opts.bendAngleRad << ",\n";
  summary << "  \"segments\": " << opts.segments << ",\n";
  summary << "  \"reflectivity_table\": \"" << opts.tablePath << "\"\n";
  summary << "}\n";
}

}  // namespace

int main(int argc, char** argv) {
  try {
    Options opts = ParseOptions(argc, argv);
    EnsureDirectory(opts.outDir);
    CLHEP::HepRandom::setTheSeed(opts.seed);

    optics::GammaChannelReflection* process = new optics::GammaChannelReflection();
    process->SetRequiredVolumeToken("Curved");
    process->SetRecordHistory(true);
    if (opts.tablePath.empty()) {
      process->SetProbabilities(opts.R, opts.A, opts.T);
    } else {
      process->LoadReflectivityTable(opts.tablePath, optics::ReflectivityLookupMode::kLinear, opts.stackId);
    }

    G4RunManager* runManager = new G4RunManager;
    runManager->SetUserInitialization(new CurvedChannelConstruction(opts));
    runManager->SetUserInitialization(new CurvedChannelPhysicsList(process));
    runManager->SetUserAction(new CurvedChannelPrimaryGenerator(opts));
    runManager->Initialize();
    process->ResetCounters();
    runManager->BeamOn(opts.nEvents);

    WriteHistory(opts, *process);
    WritePhaseAndSummary(opts, *process);
    std::cout << "CHANNEL_SINGLE_CURVED_SUMMARY"
              << " events=" << opts.nEvents
              << " boundary=" << process->GetBoundaryCount()
              << " reflect=" << process->GetReflectCount()
              << " absorb=" << process->GetAbsorbCount()
              << " leak=" << process->GetLeakCount()
              << std::endl;
    delete runManager;
  } catch (const std::exception& exc) {
    std::cerr << "channel_single_curved_demo: " << exc.what() << std::endl;
    return 1;
  }
  return 0;
}
