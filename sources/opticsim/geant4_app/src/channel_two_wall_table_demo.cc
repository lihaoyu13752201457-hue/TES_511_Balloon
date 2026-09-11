#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <sys/stat.h>

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
#include "optics/ReflectivityTable.hh"

namespace {

struct Options {
  int nEvents = 1000;
  double energyKeV = 511.0;
  double thetaRad = 1.5e-4;
  std::string tablePath;
  std::string stackId = "WSi_30_150";
  optics::ReflectivityLookupMode lookupMode = optics::ReflectivityLookupMode::kLinear;
  double R = 1.0;
  double A = 0.0;
  double T = 0.0;
  std::string outDir = "runs/geant4_channel_two_wall_table";
  long seed = 20260517;
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
    auto requireValue = [&](const std::string& name) -> std::string {
      if (i + 1 >= argc) throw std::runtime_error("missing value for " + name);
      return argv[++i];
    };
    if (arg == "--n") {
      opts.nEvents = std::stoi(requireValue(arg));
    } else if (arg == "--energy-keV") {
      opts.energyKeV = std::stod(requireValue(arg));
    } else if (arg == "--theta-rad") {
      opts.thetaRad = std::stod(requireValue(arg));
    } else if (arg == "--reflectivity-table") {
      opts.tablePath = requireValue(arg);
    } else if (arg == "--stack-id") {
      opts.stackId = requireValue(arg);
    } else if (arg == "--lookup") {
      const std::string mode = requireValue(arg);
      if (mode == "nearest") {
        opts.lookupMode = optics::ReflectivityLookupMode::kNearest;
      } else if (mode == "linear") {
        opts.lookupMode = optics::ReflectivityLookupMode::kLinear;
      } else {
        throw std::runtime_error("lookup must be nearest or linear");
      }
    } else if (arg == "--R") {
      opts.R = std::stod(requireValue(arg));
    } else if (arg == "--A") {
      opts.A = std::stod(requireValue(arg));
    } else if (arg == "--T") {
      opts.T = std::stod(requireValue(arg));
    } else if (arg == "--out") {
      opts.outDir = requireValue(arg);
    } else if (arg == "--seed") {
      opts.seed = std::stol(requireValue(arg));
    } else {
      throw std::runtime_error("unknown argument: " + arg);
    }
  }
  return opts;
}

class TwoWallTableDetectorConstruction : public G4VUserDetectorConstruction {
 public:
  G4VPhysicalVolume* Construct() override {
    G4NistManager* nist = G4NistManager::Instance();
    G4Material* vacuum = nist->FindOrBuildMaterial("G4_Galactic");
    G4Material* wallMaterial = nist->FindOrBuildMaterial("G4_W");

    const double length = 22.0 * mm;
    const double halfGap = 0.001 * mm;
    const double wallThickness = 0.010 * mm;
    G4Box* worldSolid = new G4Box("WorldSolid", 2.0 * mm, 0.05 * mm, 13.0 * mm);
    G4LogicalVolume* worldLogic = new G4LogicalVolume(worldSolid, vacuum, "WorldLogical");
    G4VPhysicalVolume* world =
        new G4PVPlacement(0, G4ThreeVector(), worldLogic, "World", 0, false, 0);

    G4Box* wallSolid = new G4Box("ChannelWallSolid", 1.0 * mm, wallThickness / 2.0, length / 2.0);
    G4LogicalVolume* topLogic = new G4LogicalVolume(wallSolid, wallMaterial, "TopChannelWallLogical");
    G4LogicalVolume* bottomLogic = new G4LogicalVolume(wallSolid, wallMaterial, "BottomChannelWallLogical");

    new G4PVPlacement(
        0,
        G4ThreeVector(0.0, halfGap + wallThickness / 2.0, 0.0),
        topLogic,
        "TopChannelWall",
        worldLogic,
        false,
        0);
    new G4PVPlacement(
        0,
        G4ThreeVector(0.0, -halfGap - wallThickness / 2.0, 0.0),
        bottomLogic,
        "BottomChannelWall",
        worldLogic,
        false,
        0);
    return world;
  }
};

class TwoWallTablePhysicsList : public G4VUserPhysicsList {
 public:
  explicit TwoWallTablePhysicsList(optics::GammaChannelReflection* process) : process_(process) {}

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

class TwoWallTablePrimaryGenerator : public G4VUserPrimaryGeneratorAction {
 public:
  TwoWallTablePrimaryGenerator(double energyKeV, double thetaRad) {
    gun_ = new G4ParticleGun(1);
    gun_->SetParticleDefinition(G4Gamma::GammaDefinition());
    gun_->SetParticleEnergy(energyKeV * keV);
    gun_->SetParticlePosition(G4ThreeVector(0.0, 0.0, -11.0 * mm + 1.0e-6 * mm));
    gun_->SetParticleMomentumDirection(G4ThreeVector(0.0, std::sin(thetaRad), std::cos(thetaRad)).unit());
  }

  ~TwoWallTablePrimaryGenerator() override {
    delete gun_;
  }

  void GeneratePrimaries(G4Event* event) override {
    gun_->GeneratePrimaryVertex(event);
  }

 private:
  G4ParticleGun* gun_;
};

void WriteHistory(const std::string& outDir, const optics::GammaChannelReflection& process) {
  std::ofstream out((outDir + "/optics_history.csv").c_str());
  out << "source_event_id,track_id,boundary_index,ring_id,segment_id,surface_id,E_keV,"
      << "theta_grazing_rad,R,A,T,u_before_x,u_before_y,u_before_z,"
      << "u_after_x,u_after_y,u_after_z,x_mm,y_mm,z_mm,action\n";
  for (const auto& row : process.GetHistory()) {
    const int ringId = row.surfaceCopyNo >= 0 ? row.surfaceCopyNo / 10000 : 0;
    const int segmentId = row.surfaceCopyNo >= 0 ? row.surfaceCopyNo % 10000 : 0;
    out << row.sourceEventId << "," << row.trackId << "," << row.boundaryIndex
        << "," << ringId << "," << segmentId << "," << row.surfaceName << "," << std::setprecision(12) << row.energyKeV << ","
        << row.thetaGrazingRad << "," << row.probabilities.R << ","
        << row.probabilities.A << "," << row.probabilities.T << ","
        << row.directionBefore.x() << "," << row.directionBefore.y() << ","
        << row.directionBefore.z() << "," << row.directionAfter.x() << ","
        << row.directionAfter.y() << "," << row.directionAfter.z() << ","
        << row.positionMm.x() << "," << row.positionMm.y() << "," << row.positionMm.z()
        << "," << row.action << "\n";
  }
}

void WriteSummary(
    const std::string& outDir,
    const Options& opts,
    const optics::ChannelReflectivity& expected,
    const optics::GammaChannelReflection& process) {
  const int nLoss = process.GetAbsorbCount() + process.GetLeakCount();
  const int nSurvived = std::max(0, opts.nEvents - nLoss);
  std::ofstream out((outDir + "/summary.json").c_str());
  out << "{\n";
  out << "  \"system\": \"geant4_channel_two_wall_table\",\n";
  out << "  \"model\": \"" << (opts.tablePath.empty() ? "constant_RAT" : "table_driven_RAT") << "\",\n";
  out << "  \"warning\": \"Two-wall per-bounce validation geometry for channel optics; not a full curved 4-ring system.\",\n";
  out << "  \"n_primaries\": " << opts.nEvents << ",\n";
  out << "  \"n_boundary\": " << process.GetBoundaryCount() << ",\n";
  out << "  \"n_reflect\": " << process.GetReflectCount() << ",\n";
  out << "  \"n_absorb\": " << process.GetAbsorbCount() << ",\n";
  out << "  \"n_leak\": " << process.GetLeakCount() << ",\n";
  out << "  \"n_survived\": " << nSurvived << ",\n";
  out << "  \"survival_fraction\": " << std::setprecision(12)
      << (opts.nEvents ? static_cast<double>(nSurvived) / opts.nEvents : 0.0) << ",\n";
  out << "  \"energy_keV\": " << opts.energyKeV << ",\n";
  out << "  \"theta_rad\": " << opts.thetaRad << ",\n";
  out << "  \"expected_R\": " << expected.R << ",\n";
  out << "  \"expected_A\": " << expected.A << ",\n";
  out << "  \"expected_T\": " << expected.T << ",\n";
  out << "  \"reflectivity_table\": \"" << opts.tablePath << "\",\n";
  out << "  \"lookup_mode\": \"" << (opts.lookupMode == optics::ReflectivityLookupMode::kNearest ? "nearest" : "linear") << "\"\n";
  out << "}\n";
}

}  // namespace

int main(int argc, char** argv) {
  try {
    const Options opts = ParseOptions(argc, argv);
    EnsureDirectory(opts.outDir);
    CLHEP::HepRandom::setTheSeed(opts.seed);

    optics::GammaChannelReflection* process = new optics::GammaChannelReflection();
    process->SetRequiredVolumeToken("ChannelWall");
    process->SetRecordHistory(true);

    optics::ChannelReflectivity expected{opts.R, opts.A, opts.T, 0.0};
    if (opts.tablePath.empty()) {
      process->SetProbabilities(opts.R, opts.A, opts.T);
    } else {
      process->LoadReflectivityTable(opts.tablePath, opts.lookupMode, opts.stackId);
      const optics::ReflectivityTable table = optics::ReflectivityTable::FromCsv(opts.tablePath);
      const optics::ReflectivityTableRow row =
          table.Lookup(opts.energyKeV, opts.thetaRad, opts.lookupMode, opts.stackId);
      expected = optics::ChannelReflectivity{row.R, row.A, row.T, 0.0};
    }

    G4RunManager* runManager = new G4RunManager;
    runManager->SetUserInitialization(new TwoWallTableDetectorConstruction());
    runManager->SetUserInitialization(new TwoWallTablePhysicsList(process));
    runManager->SetUserAction(new TwoWallTablePrimaryGenerator(opts.energyKeV, opts.thetaRad));
    runManager->Initialize();
    process->ResetCounters();
    runManager->BeamOn(opts.nEvents);

    WriteHistory(opts.outDir, *process);
    WriteSummary(opts.outDir, opts, expected, *process);
    std::cout << "CHANNEL_TWO_WALL_TABLE_SUMMARY"
              << " events=" << opts.nEvents
              << " boundary=" << process->GetBoundaryCount()
              << " reflect=" << process->GetReflectCount()
              << " absorb=" << process->GetAbsorbCount()
              << " leak=" << process->GetLeakCount()
              << std::endl;
    delete runManager;
  } catch (const std::exception& exc) {
    std::cerr << "channel_two_wall_table_demo: " << exc.what() << std::endl;
    return 1;
  }
  return 0;
}
