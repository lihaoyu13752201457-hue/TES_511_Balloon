#include <algorithm>
#include <cerrno>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/stat.h>
#include <vector>

#include "FTFP_BERT.hh"
#include "G4Box.hh"
#include "G4Event.hh"
#include "G4IonTable.hh"
#include "G4LogicalVolume.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4RadioactiveDecayPhysics.hh"
#include "G4RotationMatrix.hh"
#include "G4RunManager.hh"
#include "G4Step.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "G4Track.hh"
#include "G4UserSteppingAction.hh"
#include "G4VModularPhysicsList.hh"
#include "G4VPhysicalVolume.hh"
#include "G4VProcess.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "Randomize.hh"

namespace {

struct Options {
  std::string sourceCsv;
  std::string outDir = "runs/activation_decay_focal_smoke";
  int nEvents = 1000;
  long seed = 20260520;
  double focalZMm = 12000.0;
  double worldHalfXYMm = 15000.0;
  double worldHalfZMm = 15000.0;
  std::string crossingDirection = "positive_z";
  std::string opticsMass = "both";
  std::string channelRingConfigPath = "data/channel/cam511_channel_rings.csv";
  std::string laueRingConfigPath = "data/laue/ge111_480_550keV_multiring_darwin_config.csv";
  bool killAfterCrossing = true;
  bool recordNeutrinos = false;
};

struct DecayIon {
  int eventId = 0;
  int inventoryRow = -1;
  double day = 15.0;
  double timeS = 0.0;
  int z = 0;
  int a = 0;
  double excitationKeV = 0.0;
  double xMm = 0.0;
  double yMm = 0.0;
  double zMm = 0.0;
  double weight = 1.0;
  double activityBq = 0.0;
  std::string sourceTag = "optics_activation_day15";
  std::string sourceParticleName = "ion";
  int sourcePdgEncoding = 0;
  std::string volumeName = "unknown";
  std::string creatorProcess = "unknown";
  std::string nuclide = "unknown";
  double lifetimeS = 0.0;
};

struct ChannelMassRing {
  int ringId = 0;
  double radiusMm = 22.5;
  double lengthMm = 21.0;
  double widthMm = 10.0;
  double thicknessMm = 7.5;
  int nTiles = 14;
};

struct LaueMassRing {
  int ringId = 0;
  double radiusMm = 61.6618;
  int nTiles = 72;
  std::string material = "Ge";
  double tileSizeMm = 0.8;
  double thicknessMm = 10.0;
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

std::string Trim(const std::string& value) {
  const std::string whitespace = " \t\r\n";
  const std::size_t first = value.find_first_not_of(whitespace);
  if (first == std::string::npos) return "";
  const std::size_t last = value.find_last_not_of(whitespace);
  return value.substr(first, last - first + 1);
}

std::vector<std::string> SplitCsvLine(const std::string& line) {
  std::vector<std::string> cells;
  std::stringstream ss(line);
  std::string cell;
  while (std::getline(ss, cell, ',')) cells.push_back(Trim(cell));
  return cells;
}

std::map<std::string, std::size_t> HeaderMap(const std::vector<std::string>& header) {
  std::map<std::string, std::size_t> out;
  for (std::size_t i = 0; i < header.size(); ++i) out[header[i]] = i;
  return out;
}

std::string ValueAt(
    const std::vector<std::string>& row,
    const std::map<std::string, std::size_t>& header,
    const std::string& key) {
  const auto it = header.find(key);
  if (it == header.end() || it->second >= row.size()) {
    throw std::runtime_error("CSV is missing column: " + key);
  }
  return row[it->second];
}

std::string OptionalValueAt(
    const std::vector<std::string>& row,
    const std::map<std::string, std::size_t>& header,
    const std::string& key,
    const std::string& fallback) {
  const auto it = header.find(key);
  if (it == header.end() || it->second >= row.size() || row[it->second].empty()) return fallback;
  return row[it->second];
}

double ReadDouble(
    const std::vector<std::string>& row,
    const std::map<std::string, std::size_t>& header,
    const std::string& key) {
  return std::atof(ValueAt(row, header, key).c_str());
}

std::map<std::string, std::string> RowMap(
    const std::vector<std::string>& headers,
    const std::vector<std::string>& cells) {
  std::map<std::string, std::string> row;
  for (std::size_t i = 0; i < headers.size() && i < cells.size(); ++i) row[headers[i]] = cells[i];
  return row;
}

std::string MapString(const std::map<std::string, std::string>& row, const std::string& key) {
  const auto it = row.find(key);
  if (it == row.end() || it->second.empty()) throw std::runtime_error("missing CSV column: " + key);
  return it->second;
}

double MapDouble(const std::map<std::string, std::string>& row, const std::string& key) {
  return std::atof(MapString(row, key).c_str());
}

int MapInt(const std::map<std::string, std::string>& row, const std::string& key) {
  return std::atoi(MapString(row, key).c_str());
}

std::vector<ChannelMassRing> LoadChannelMassRings(const std::string& path) {
  std::ifstream input(path.c_str());
  if (!input) throw std::runtime_error("cannot open channel ring config: " + path);
  std::string line;
  if (!std::getline(input, line)) throw std::runtime_error("empty channel ring config: " + path);
  const auto headers = SplitCsvLine(line);
  std::vector<ChannelMassRing> rings;
  while (std::getline(input, line)) {
    if (Trim(line).empty()) continue;
    const auto row = RowMap(headers, SplitCsvLine(line));
    ChannelMassRing ring;
    ring.ringId = MapInt(row, "ring_id");
    ring.radiusMm = 10.0 * MapDouble(row, "radius_cm");
    ring.lengthMm = 10.0 * MapDouble(row, "length_cm");
    ring.widthMm = 10.0 * MapDouble(row, "width_cm");
    ring.thicknessMm = MapDouble(row, "thickness_mm");
    ring.nTiles = MapInt(row, "n_tiles");
    rings.push_back(ring);
  }
  if (rings.empty()) throw std::runtime_error("channel ring config has no data rows: " + path);
  return rings;
}

std::vector<LaueMassRing> LoadLaueMassRings(const std::string& path) {
  std::ifstream input(path.c_str());
  if (!input) throw std::runtime_error("cannot open Laue ring config: " + path);
  std::string line;
  if (!std::getline(input, line)) throw std::runtime_error("empty Laue ring config: " + path);
  const auto headers = SplitCsvLine(line);
  std::vector<LaueMassRing> rings;
  while (std::getline(input, line)) {
    if (Trim(line).empty()) continue;
    const auto row = RowMap(headers, SplitCsvLine(line));
    LaueMassRing ring;
    ring.ringId = MapInt(row, "ring_id");
    ring.radiusMm = MapDouble(row, "radius_mm");
    ring.nTiles = MapInt(row, "n_tiles");
    ring.material = MapString(row, "material");
    ring.tileSizeMm = MapDouble(row, "tile_size_mm");
    ring.thicknessMm = MapDouble(row, "thickness_mm");
    rings.push_back(ring);
  }
  if (rings.empty()) throw std::runtime_error("Laue ring config has no data rows: " + path);
  return rings;
}

std::vector<DecayIon> ReadDecayCsv(const std::string& path) {
  std::ifstream input(path.c_str());
  if (!input) throw std::runtime_error("cannot open decay-ion CSV: " + path);
  std::string line;
  if (!std::getline(input, line)) throw std::runtime_error("empty decay-ion CSV: " + path);
  const auto header = HeaderMap(SplitCsvLine(line));
  std::vector<DecayIon> ions;
  while (std::getline(input, line)) {
    if (Trim(line).empty()) continue;
    const auto row = SplitCsvLine(line);
    DecayIon ion;
    ion.eventId = std::atoi(ValueAt(row, header, "event_id").c_str());
    ion.inventoryRow = std::atoi(OptionalValueAt(row, header, "inventory_row", "-1").c_str());
    ion.day = std::atof(OptionalValueAt(row, header, "day", "15").c_str());
    ion.timeS = std::atof(OptionalValueAt(row, header, "time_s", "0").c_str());
    ion.z = std::atoi(ValueAt(row, header, "Z").c_str());
    ion.a = std::atoi(ValueAt(row, header, "A").c_str());
    ion.excitationKeV = std::atof(OptionalValueAt(row, header, "excitation_keV", "0").c_str());
    ion.xMm = ReadDouble(row, header, "x_mm");
    ion.yMm = ReadDouble(row, header, "y_mm");
    ion.zMm = ReadDouble(row, header, "z_mm");
    ion.weight = ReadDouble(row, header, "weight");
    ion.activityBq = std::atof(OptionalValueAt(row, header, "activity_Bq", "0").c_str());
    ion.sourceTag = OptionalValueAt(row, header, "source_tag", "optics_activation");
    ion.sourceParticleName = OptionalValueAt(row, header, "source_particle_name", "ion");
    ion.sourcePdgEncoding = std::atoi(OptionalValueAt(row, header, "source_pdg_encoding", "0").c_str());
    ion.volumeName = OptionalValueAt(row, header, "volume_name", "unknown");
    ion.creatorProcess = OptionalValueAt(row, header, "creator_process", "unknown");
    ion.nuclide = OptionalValueAt(row, header, "nuclide", "unknown");
    ion.lifetimeS = std::atof(OptionalValueAt(row, header, "lifetime_s", "0").c_str());
    if (ion.weight > 0.0 && ion.z > 0 && ion.a > 0) ions.push_back(ion);
  }
  return ions;
}

Options ParseOptions(int argc, char** argv) {
  Options opt;
  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    auto require = [&](const std::string& name) -> const char* {
      if (i + 1 >= argc) throw std::runtime_error("missing value for " + name);
      return argv[++i];
    };
    if (arg == "--source-csv") {
      opt.sourceCsv = require(arg);
    } else if (arg == "--out") {
      opt.outDir = require(arg);
    } else if (arg == "--n") {
      opt.nEvents = std::atoi(require(arg));
    } else if (arg == "--seed") {
      opt.seed = std::atol(require(arg));
    } else if (arg == "--focal-z-mm") {
      opt.focalZMm = std::atof(require(arg));
    } else if (arg == "--world-half-xy-mm") {
      opt.worldHalfXYMm = std::atof(require(arg));
    } else if (arg == "--world-half-z-mm") {
      opt.worldHalfZMm = std::atof(require(arg));
    } else if (arg == "--crossing-direction") {
      opt.crossingDirection = require(arg);
    } else if (arg == "--optics-mass") {
      opt.opticsMass = require(arg);
    } else if (arg == "--channel-ring-config") {
      opt.channelRingConfigPath = require(arg);
    } else if (arg == "--laue-ring-config") {
      opt.laueRingConfigPath = require(arg);
    } else if (arg == "--kill-after-crossing") {
      opt.killAfterCrossing = std::atoi(require(arg)) != 0;
    } else if (arg == "--record-neutrinos") {
      opt.recordNeutrinos = std::atoi(require(arg)) != 0;
    } else if (arg == "--help" || arg == "-h") {
      std::cout << "Usage: " << argv[0]
                << " --source-csv decay_ions.csv --out DIR --n N"
                << " [--focal-z-mm 12000] [--crossing-direction positive_z|negative_z|both]"
                << " [--optics-mass none|channel_4ring|laue_multiring|both]\n";
      std::exit(0);
    } else {
      throw std::runtime_error("unknown option: " + arg);
    }
  }
  if (opt.sourceCsv.empty()) throw std::runtime_error("--source-csv is required");
  if (opt.nEvents <= 0) throw std::runtime_error("--n must be positive");
  if (opt.crossingDirection != "positive_z" &&
      opt.crossingDirection != "negative_z" &&
      opt.crossingDirection != "both") {
    throw std::runtime_error("--crossing-direction must be positive_z, negative_z, or both");
  }
  if (opt.opticsMass != "none" &&
      opt.opticsMass != "channel_4ring" &&
      opt.opticsMass != "laue_multiring" &&
      opt.opticsMass != "both") {
    throw std::runtime_error("--optics-mass must be none, channel_4ring, laue_multiring, or both");
  }
  return opt;
}

class OpticsActivationConstruction : public G4VUserDetectorConstruction {
 public:
  explicit OpticsActivationConstruction(const Options& opt) : opt_(opt) {}

  G4VPhysicalVolume* Construct() override {
    G4NistManager* nist = G4NistManager::Instance();
    G4Material* vacuum = nist->FindOrBuildMaterial("G4_Galactic");
    G4Box* worldSolid = new G4Box(
        "WorldSolid",
        opt_.worldHalfXYMm * mm,
        opt_.worldHalfXYMm * mm,
        opt_.worldHalfZMm * mm);
    G4LogicalVolume* worldLogic = new G4LogicalVolume(worldSolid, vacuum, "WorldLogical");
    G4VPhysicalVolume* world = new G4PVPlacement(0, G4ThreeVector(), worldLogic, "World", 0, false, 0);
    if (opt_.opticsMass == "channel_4ring" || opt_.opticsMass == "both") AddChannelMass(nist, worldLogic);
    if (opt_.opticsMass == "laue_multiring" || opt_.opticsMass == "both") AddLaueMass(nist, worldLogic);
    return world;
  }

 private:
  void AddChannelMass(G4NistManager* nist, G4LogicalVolume* worldLogic) const {
    G4Material* silicon = nist->FindOrBuildMaterial("G4_Si");
    const auto rings = LoadChannelMassRings(opt_.channelRingConfigPath);
    for (const auto& ring : rings) {
      G4Box* tileSolid = new G4Box(
          ("ChannelMassTileSolid_r" + std::to_string(ring.ringId)).c_str(),
          0.5 * ring.thicknessMm * mm,
          0.5 * ring.widthMm * mm,
          0.5 * ring.lengthMm * mm);
      G4LogicalVolume* tileLogic = new G4LogicalVolume(
          tileSolid,
          silicon,
          ("ChannelMassTileLogical_r" + std::to_string(ring.ringId)).c_str());
      for (int i = 0; i < ring.nTiles; ++i) {
        const double phi = 2.0 * M_PI * static_cast<double>(i) / static_cast<double>(ring.nTiles);
        G4RotationMatrix* rot = new G4RotationMatrix();
        rot->rotateZ(phi);
        new G4PVPlacement(
            rot,
            G4ThreeVector(ring.radiusMm * std::cos(phi) * mm, ring.radiusMm * std::sin(phi) * mm, 0.0),
            tileLogic,
            "ChannelMassTile",
            worldLogic,
            false,
            ring.ringId * 1000 + i);
      }
    }
  }

  void AddLaueMass(G4NistManager* nist, G4LogicalVolume* worldLogic) const {
    const auto rings = LoadLaueMassRings(opt_.laueRingConfigPath);
    for (const auto& ring : rings) {
      G4Material* material = nist->FindOrBuildMaterial(ring.material == "Ge" ? "G4_Ge" : ring.material);
      G4Box* tileSolid = new G4Box(
          ("LaueMassCrystalSolid_r" + std::to_string(ring.ringId)).c_str(),
          0.5 * ring.tileSizeMm * mm,
          0.5 * ring.tileSizeMm * mm,
          0.5 * ring.thicknessMm * mm);
      G4LogicalVolume* tileLogic = new G4LogicalVolume(
          tileSolid,
          material,
          ("LaueMassCrystalLogical_r" + std::to_string(ring.ringId)).c_str());
      for (int i = 0; i < ring.nTiles; ++i) {
        const double phi = 2.0 * M_PI * static_cast<double>(i) / static_cast<double>(ring.nTiles);
        G4RotationMatrix* rot = new G4RotationMatrix();
        rot->rotateZ(phi);
        new G4PVPlacement(
            rot,
            G4ThreeVector(ring.radiusMm * std::cos(phi) * mm, ring.radiusMm * std::sin(phi) * mm, 0.0),
            tileLogic,
            "LaueMassCrystal",
            worldLogic,
            false,
            100000 + ring.ringId * 1000 + i);
      }
    }
  }

  Options opt_;
};

class DecayIonPrimaryGenerator : public G4VUserPrimaryGeneratorAction {
 public:
  explicit DecayIonPrimaryGenerator(const std::vector<DecayIon>* ions) : ions_(ions) {
    gun_ = new G4ParticleGun(1);
  }

  ~DecayIonPrimaryGenerator() override { delete gun_; }

  void GeneratePrimaries(G4Event* event) override {
    const auto idx = static_cast<std::size_t>(event->GetEventID());
    const DecayIon& src = ions_->at(idx);
    G4IonTable* ionTable = G4ParticleTable::GetParticleTable()->GetIonTable();
    G4ParticleDefinition* ion = ionTable->GetIon(src.z, src.a, src.excitationKeV * keV);
    if (ion == 0) {
      throw std::runtime_error("Geant4 ion table cannot create ion Z=" + std::to_string(src.z) +
                               " A=" + std::to_string(src.a));
    }
    gun_->SetParticleDefinition(ion);
    gun_->SetParticleEnergy(0.0);
    gun_->SetParticleTime(src.timeS * s);
    gun_->SetParticlePosition(G4ThreeVector(src.xMm * mm, src.yMm * mm, src.zMm * mm));
    gun_->SetParticleMomentumDirection(G4ThreeVector(0.0, 0.0, 1.0));
    gun_->GeneratePrimaryVertex(event);
  }

 private:
  const std::vector<DecayIon>* ions_;
  G4ParticleGun* gun_;
};

class DecayRunState {
 public:
  DecayRunState(const Options& opt, const std::vector<DecayIon>* ions)
      : opt_(opt),
        ions_(ions),
        nCrossings_(0),
        nPrimaryCrossings_(0),
        nSecondaryCrossings_(0),
        nNeutrinoCrossingsSkipped_(0) {
    EnsureDirectory(opt_.outDir);
    phase_.open((opt_.outDir + "/phase_space.csv").c_str());
    if (!phase_) throw std::runtime_error("cannot open phase_space.csv in: " + opt_.outDir);
    phase_ << "event_id,E_keV,x_mm,y_mm,z_mm,ux,uy,uz,weight,source_tag,"
           << "particle_name,pdg_encoding,track_id,parent_id,creator_process,"
           << "source_particle_name,source_pdg_encoding,time_s,crossing_direction,"
           << "source_Z,source_A,source_excitation_keV,source_volume,inventory_row,activity_Bq\n";
  }

  bool AcceptCrossing(double preZ, double postZ) const {
    const double z = opt_.focalZMm * mm;
    const bool positive = preZ < z && postZ >= z;
    const bool negative = preZ > z && postZ <= z;
    if (opt_.crossingDirection == "positive_z") return positive;
    if (opt_.crossingDirection == "negative_z") return negative;
    return positive || negative;
  }

  void RecordCrossing(const G4Step* step) {
    const G4Track* track = step->GetTrack();
    const G4StepPoint* pre = step->GetPreStepPoint();
    const G4StepPoint* post = step->GetPostStepPoint();
    const double preZ = pre->GetPosition().z();
    const double postZ = post->GetPosition().z();
    const double denom = postZ - preZ;
    if (denom == 0.0) return;
    const double focalZ = opt_.focalZMm * mm;
    const double frac = std::max(0.0, std::min(1.0, (focalZ - preZ) / denom));
    const G4ThreeVector pos = pre->GetPosition() + frac * (post->GetPosition() - pre->GetPosition());
    G4ThreeVector dir = track->GetMomentumDirection();
    if (dir.mag2() <= 0.0) dir = post->GetMomentumDirection();
    if (dir.mag2() <= 0.0) dir = G4ThreeVector(0.0, 0.0, denom > 0.0 ? 1.0 : -1.0);
    dir = dir.unit();

    const G4Event* event = G4RunManager::GetRunManager()->GetCurrentEvent();
    const int eventIndex = event ? event->GetEventID() : -1;
    const DecayIon* source = 0;
    if (eventIndex >= 0 && static_cast<std::size_t>(eventIndex) < ions_->size()) {
      source = &ions_->at(static_cast<std::size_t>(eventIndex));
    }
    const int outEventId = source ? source->eventId : eventIndex;
    const double outWeight = source ? source->weight : 1.0;
    const std::string tag = source ? source->sourceTag : "optics_activation";
    const std::string crossing = denom > 0.0 ? "positive_z" : "negative_z";
    const double timeS = (pre->GetGlobalTime() + frac * (post->GetGlobalTime() - pre->GetGlobalTime())) / s;
    const double crossingEnergyKeV =
        (pre->GetKineticEnergy() + frac * (post->GetKineticEnergy() - pre->GetKineticEnergy())) / keV;
    const G4ParticleDefinition* particle = track->GetParticleDefinition();
    const std::string particleName = particle ? particle->GetParticleName() : "unknown";
    const int pdg = particle ? particle->GetPDGEncoding() : 0;
    if (!opt_.recordNeutrinos && (std::abs(pdg) == 12 || std::abs(pdg) == 14 || std::abs(pdg) == 16)) {
      ++nNeutrinoCrossingsSkipped_;
      return;
    }
    const G4VProcess* creator = track->GetCreatorProcess();
    const std::string creatorProcess = creator ? creator->GetProcessName() : "primary";
    const std::string sourceName = source ? source->nuclide : "unknown";
    const int sourcePdg = source ? source->sourcePdgEncoding : 0;
    phase_ << outEventId << "," << std::setprecision(12)
           << crossingEnergyKeV << ","
           << pos.x() / mm << "," << pos.y() / mm << "," << pos.z() / mm << ","
           << dir.x() << "," << dir.y() << "," << dir.z() << ","
           << outWeight << "," << tag << ","
           << particleName << "," << pdg << ","
           << track->GetTrackID() << "," << track->GetParentID() << ","
           << creatorProcess << "," << sourceName << "," << sourcePdg << ","
           << timeS << "," << crossing << ","
           << (source ? source->z : 0) << "," << (source ? source->a : 0) << ","
           << (source ? source->excitationKeV : 0.0) << ","
           << (source ? source->volumeName : "unknown") << ","
           << (source ? source->inventoryRow : -1) << ","
           << (source ? source->activityBq : 0.0) << "\n";
    ++nCrossings_;
    if (track->GetParentID() == 0) {
      ++nPrimaryCrossings_;
    } else {
      ++nSecondaryCrossings_;
    }
  }

  void WriteSummary(const std::string& sourceCsv, int nInputRows, int nSimulated, long seed) {
    phase_.flush();
    std::ofstream summary((opt_.outDir + "/summary.json").c_str());
    summary << "{\n";
    summary << "  \"system\": \"geant4_optics_activation_decay_focal_demo\",\n";
    summary << "  \"model\": \"RadioactiveDecay_at_true_inventory_positions_with_focal_plane_crossing_scorer\",\n";
    summary << "  \"warning\": \"Decay ions are sampled from the true production positions written by all_particle_farfield_demo. Rates remain scaffold-level until the optics mass and activation statistics are production quality.\",\n";
    summary << "  \"source_csv\": \"" << sourceCsv << "\",\n";
    summary << "  \"seed\": " << seed << ",\n";
    summary << "  \"focal_z_mm\": " << opt_.focalZMm << ",\n";
    summary << "  \"optics_mass\": \"" << opt_.opticsMass << "\",\n";
    summary << "  \"crossing_direction\": \"" << opt_.crossingDirection << "\",\n";
    summary << "  \"kill_after_crossing\": " << (opt_.killAfterCrossing ? "true" : "false") << ",\n";
    summary << "  \"record_neutrinos\": " << (opt_.recordNeutrinos ? "true" : "false") << ",\n";
    summary << "  \"world_half_xy_mm\": " << opt_.worldHalfXYMm << ",\n";
    summary << "  \"world_half_z_mm\": " << opt_.worldHalfZMm << ",\n";
    summary << "  \"n_input_rows\": " << nInputRows << ",\n";
    summary << "  \"n_simulated\": " << nSimulated << ",\n";
    summary << "  \"n_crossings\": " << nCrossings_ << ",\n";
    summary << "  \"n_primary_crossings\": " << nPrimaryCrossings_ << ",\n";
    summary << "  \"n_secondary_crossings\": " << nSecondaryCrossings_ << ",\n";
    summary << "  \"n_neutrino_crossings_skipped\": " << nNeutrinoCrossingsSkipped_ << "\n";
    summary << "}\n";
  }

  bool killAfterCrossing() const { return opt_.killAfterCrossing; }

 private:
  Options opt_;
  const std::vector<DecayIon>* ions_;
  std::ofstream phase_;
  long nCrossings_;
  long nPrimaryCrossings_;
  long nSecondaryCrossings_;
  long nNeutrinoCrossingsSkipped_;
};

class FocalPlaneSteppingAction : public G4UserSteppingAction {
 public:
  explicit FocalPlaneSteppingAction(DecayRunState* state) : state_(state) {}

  void UserSteppingAction(const G4Step* step) override {
    const double preZ = step->GetPreStepPoint()->GetPosition().z();
    const double postZ = step->GetPostStepPoint()->GetPosition().z();
    if (!state_->AcceptCrossing(preZ, postZ)) return;
    state_->RecordCrossing(step);
    if (state_->killAfterCrossing()) step->GetTrack()->SetTrackStatus(fStopAndKill);
  }

 private:
  DecayRunState* state_;
};

}  // namespace

int main(int argc, char** argv) {
  try {
    const Options opt = ParseOptions(argc, argv);
    std::vector<DecayIon> ions = ReadDecayCsv(opt.sourceCsv);
    if (ions.empty()) throw std::runtime_error("decay-ion CSV has no positive-weight ion rows");
    const int nEvents = std::min<int>(opt.nEvents, static_cast<int>(ions.size()));
    CLHEP::HepRandom::setTheSeed(opt.seed);

    DecayRunState state(opt, &ions);
    G4RunManager* runManager = new G4RunManager;
    runManager->SetUserInitialization(new OpticsActivationConstruction(opt));
    G4VModularPhysicsList* physics = new FTFP_BERT(0);
    physics->SetDefaultCutValue(0.1 * mm);
    physics->RegisterPhysics(new G4RadioactiveDecayPhysics(0));
    runManager->SetUserInitialization(physics);
    runManager->SetUserAction(new DecayIonPrimaryGenerator(&ions));
    runManager->SetUserAction(new FocalPlaneSteppingAction(&state));
    runManager->Initialize();
    runManager->BeamOn(nEvents);
    delete runManager;

    state.WriteSummary(opt.sourceCsv, static_cast<int>(ions.size()), nEvents, opt.seed);
    std::cout << "ACTIVATION_DECAY_FOCAL_SUMMARY"
              << " source=" << opt.sourceCsv
              << " out=" << opt.outDir
              << " events=" << nEvents
              << std::endl;
  } catch (const std::exception& exc) {
    std::cerr << "activation_decay_focal_demo error: " << exc.what() << std::endl;
    return 1;
  }
  return 0;
}
