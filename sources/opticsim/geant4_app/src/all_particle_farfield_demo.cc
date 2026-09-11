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
#include "G4Ions.hh"
#include "G4LogicalVolume.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4RotationMatrix.hh"
#include "G4RunManager.hh"
#include "G4Step.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "G4Track.hh"
#include "G4UserSteppingAction.hh"
#include "G4UserTrackingAction.hh"
#include "G4VModularPhysicsList.hh"
#include "G4VPhysicalVolume.hh"
#include "G4VProcess.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "Randomize.hh"

namespace {

struct Options {
  std::string sourceCsv = "";
  std::string outDir = "runs/all_particle_farfield_smoke";
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
};

struct SourcePrimary {
  int eventId = 0;
  double timeS = 0.0;
  std::string particleName = "gamma";
  int pdgEncoding = 22;
  double energyKeV = 0.0;
  double xMm = 0.0;
  double yMm = 0.0;
  double zMm = 0.0;
  double ux = 0.0;
  double uy = 0.0;
  double uz = 1.0;
  double weight = 1.0;
  std::string sourceTag = "all_particle_farfield";
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

bool HasColumn(const std::map<std::string, std::size_t>& header, const std::string& key) {
  return header.find(key) != header.end();
}

std::string ValueAt(
    const std::vector<std::string>& row,
    const std::map<std::string, std::size_t>& header,
    const std::string& key) {
  const auto it = header.find(key);
  if (it == header.end() || it->second >= row.size()) {
    throw std::runtime_error("source CSV is missing column: " + key);
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

std::vector<SourcePrimary> ReadSourceCsv(const std::string& path) {
  std::ifstream input(path.c_str());
  if (!input) throw std::runtime_error("cannot open all-particle source CSV: " + path);
  std::string line;
  if (!std::getline(input, line)) throw std::runtime_error("empty all-particle source CSV: " + path);
  const auto header = HeaderMap(SplitCsvLine(line));
  std::vector<SourcePrimary> primaries;
  while (std::getline(input, line)) {
    if (Trim(line).empty()) continue;
    const auto row = SplitCsvLine(line);
    SourcePrimary p;
    p.eventId = std::atoi(ValueAt(row, header, "event_id").c_str());
    p.timeS = HasColumn(header, "time_s") ? ReadDouble(row, header, "time_s") : 0.0;
    p.particleName = OptionalValueAt(row, header, "particle_name", "gamma");
    p.pdgEncoding = std::atoi(OptionalValueAt(row, header, "pdg_encoding", "22").c_str());
    p.energyKeV = ReadDouble(row, header, "E_keV");
    p.xMm = ReadDouble(row, header, "x_mm");
    p.yMm = ReadDouble(row, header, "y_mm");
    p.zMm = ReadDouble(row, header, "z_mm");
    p.ux = ReadDouble(row, header, "ux");
    p.uy = ReadDouble(row, header, "uy");
    p.uz = ReadDouble(row, header, "uz");
    p.weight = ReadDouble(row, header, "weight");
    p.sourceTag = ValueAt(row, header, "source_tag");
    if (p.weight > 0.0) primaries.push_back(p);
  }
  return primaries;
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
    } else if (arg == "--help" || arg == "-h") {
      std::cout << "Usage: " << argv[0]
                << " --source-csv primaries.csv --out DIR --n N"
                << " [--focal-z-mm 12000] [--crossing-direction positive_z|negative_z|both]"
                << " [--optics-mass none|channel_4ring|laue_multiring|both]\n";
      std::exit(0);
    } else {
      throw std::runtime_error("unknown option: " + arg);
    }
  }
  if (opt.sourceCsv.empty()) throw std::runtime_error("--source-csv is required");
  if (opt.nEvents <= 0) throw std::runtime_error("--n must be positive");
  if (opt.worldHalfXYMm <= 0.0 || opt.worldHalfZMm <= 0.0) {
    throw std::runtime_error("world half dimensions must be positive");
  }
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

G4ParticleDefinition* FindParticleDefinition(const SourcePrimary& primary) {
  G4ParticleTable* table = G4ParticleTable::GetParticleTable();
  G4ParticleDefinition* particle = table->FindParticle(primary.particleName);
  if (particle == 0 && primary.pdgEncoding != 0) {
    particle = table->FindParticle(primary.pdgEncoding);
  }
  if (particle == 0) {
    throw std::runtime_error(
        "Geant4 particle table does not contain particle_name=" + primary.particleName +
        " pdg=" + std::to_string(primary.pdgEncoding));
  }
  return particle;
}

class FarfieldConstruction : public G4VUserDetectorConstruction {
 public:
  explicit FarfieldConstruction(const Options& opt) : opt_(opt) {}

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
    if (opt_.opticsMass == "channel_4ring" || opt_.opticsMass == "both") {
      AddChannelMass(nist, worldLogic);
    }
    if (opt_.opticsMass == "laue_multiring" || opt_.opticsMass == "both") {
      AddLaueMass(nist, worldLogic);
    }
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

class FarfieldPrimaryGenerator : public G4VUserPrimaryGeneratorAction {
 public:
  explicit FarfieldPrimaryGenerator(const std::vector<SourcePrimary>* primaries)
      : primaries_(primaries) {
    gun_ = new G4ParticleGun(1);
  }

  ~FarfieldPrimaryGenerator() override { delete gun_; }

  void GeneratePrimaries(G4Event* event) override {
    const auto idx = static_cast<std::size_t>(event->GetEventID());
    const SourcePrimary& primary = primaries_->at(idx);
    gun_->SetParticleDefinition(FindParticleDefinition(primary));
    gun_->SetParticleEnergy(primary.energyKeV * keV);
    gun_->SetParticleTime(primary.timeS * s);
    gun_->SetParticlePosition(G4ThreeVector(primary.xMm * mm, primary.yMm * mm, primary.zMm * mm));
    G4ThreeVector direction(primary.ux, primary.uy, primary.uz);
    if (direction.mag2() <= 0.0) direction = G4ThreeVector(0.0, 0.0, 1.0);
    gun_->SetParticleMomentumDirection(direction.unit());
    gun_->GeneratePrimaryVertex(event);
  }

 private:
  const std::vector<SourcePrimary>* primaries_;
  G4ParticleGun* gun_;
};

class FarfieldRunState {
 public:
  FarfieldRunState(const Options& opt, const std::vector<SourcePrimary>* primaries)
      : opt_(opt),
        primaries_(primaries),
        nCrossings_(0),
        nPrimaryCrossings_(0),
        nSecondaryCrossings_(0),
        nActivationIons_(0) {
    EnsureDirectory(opt_.outDir);
    phase_.open((opt_.outDir + "/phase_space.csv").c_str());
    if (!phase_) throw std::runtime_error("cannot open phase_space.csv in: " + opt_.outDir);
    phase_ << "event_id,E_keV,x_mm,y_mm,z_mm,ux,uy,uz,weight,source_tag,"
           << "particle_name,pdg_encoding,track_id,parent_id,creator_process,"
           << "source_particle_name,source_pdg_encoding,time_s,crossing_direction\n";
    activation_.open((opt_.outDir + "/activation_inventory.csv").c_str());
    if (!activation_) throw std::runtime_error("cannot open activation_inventory.csv in: " + opt_.outDir);
    activation_ << "event_id,source_event_id,source_particle_name,source_pdg_encoding,"
                << "track_id,parent_id,particle_name,pdg_encoding,Z,A,excitation_keV,"
                << "stable,lifetime_s,kinetic_energy_keV,x_mm,y_mm,z_mm,time_s,"
                << "volume_name,creator_process,source_tag,weight\n";
  }

  bool AcceptCrossing(double preZ, double postZ) const {
    const double z = opt_.focalZMm * mm;
    const bool positive = preZ < z && postZ >= z;
    const bool negative = preZ > z && postZ <= z;
    if (opt_.crossingDirection == "positive_z") return positive;
    if (opt_.crossingDirection == "negative_z") return negative;
    return positive || negative;
	  }

	  void RecordActivationIon(const G4Track* track) {
	    if (!track || track->GetParentID() == 0) return;
	    const G4ParticleDefinition* particle = track->GetParticleDefinition();
	    const G4Ions* ion = dynamic_cast<const G4Ions*>(particle);
	    if (!ion || ion->GetAtomicNumber() <= 0 || ion->GetAtomicMass() <= 0) return;

	    const G4Event* event = G4RunManager::GetRunManager()->GetCurrentEvent();
	    const int eventIndex = event ? event->GetEventID() : -1;
	    const SourcePrimary* source = 0;
	    if (eventIndex >= 0 && static_cast<std::size_t>(eventIndex) < primaries_->size()) {
	      source = &primaries_->at(static_cast<std::size_t>(eventIndex));
	    }
	    const int sourceEventId = source ? source->eventId : eventIndex;
	    const std::string sourceParticleName = source ? source->particleName : "unknown";
	    const int sourcePdg = source ? source->pdgEncoding : 0;
	    const std::string tag = source ? source->sourceTag : "all_particle_farfield";
	    const double outWeight = source ? source->weight : 1.0;
	    const G4VProcess* creator = track->GetCreatorProcess();
	    const std::string creatorProcess = creator ? creator->GetProcessName() : "unknown";
	    std::string volumeName = "unknown";
	    if (track->GetVolume()) volumeName = track->GetVolume()->GetName();
	    const G4ThreeVector pos = track->GetPosition();
	    const double lifetime = particle ? particle->GetPDGLifeTime() / s : 0.0;
	    activation_ << eventIndex << "," << sourceEventId << ","
	                << sourceParticleName << "," << sourcePdg << ","
	                << track->GetTrackID() << "," << track->GetParentID() << ","
	                << particle->GetParticleName() << "," << particle->GetPDGEncoding() << ","
	                << ion->GetAtomicNumber() << "," << ion->GetAtomicMass() << ","
	                << std::setprecision(12) << ion->GetExcitationEnergy() / keV << ","
	                << (particle->GetPDGStable() ? 1 : 0) << ","
	                << lifetime << ","
	                << track->GetKineticEnergy() / keV << ","
	                << pos.x() / mm << "," << pos.y() / mm << "," << pos.z() / mm << ","
	                << track->GetGlobalTime() / s << ","
	                << volumeName << "," << creatorProcess << ","
	                << tag << "," << outWeight << "\n";
	    ++nActivationIons_;
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
    const SourcePrimary* source = 0;
    if (eventIndex >= 0 && static_cast<std::size_t>(eventIndex) < primaries_->size()) {
      source = &primaries_->at(static_cast<std::size_t>(eventIndex));
    }
    const int outEventId = source ? source->eventId : eventIndex;
    const double outWeight = source ? source->weight : 1.0;
    const std::string tag = source ? source->sourceTag : "all_particle_farfield";
    const std::string crossing = denom > 0.0 ? "positive_z" : "negative_z";
    const double timeS = (pre->GetGlobalTime() + frac * (post->GetGlobalTime() - pre->GetGlobalTime())) / s;
    const double crossingEnergyKeV =
        (pre->GetKineticEnergy() + frac * (post->GetKineticEnergy() - pre->GetKineticEnergy())) / keV;
    const G4ParticleDefinition* particle = track->GetParticleDefinition();
    const std::string particleName = particle ? particle->GetParticleName() : "unknown";
    const int pdg = particle ? particle->GetPDGEncoding() : 0;
    const G4VProcess* creator = track->GetCreatorProcess();
    const std::string creatorProcess = creator ? creator->GetProcessName() : "primary";
    const std::string sourceParticleName = source ? source->particleName : "unknown";
    const int sourcePdg = source ? source->pdgEncoding : 0;
    phase_ << outEventId << "," << std::setprecision(12)
           << crossingEnergyKeV << ","
           << pos.x() / mm << "," << pos.y() / mm << "," << pos.z() / mm << ","
           << dir.x() << "," << dir.y() << "," << dir.z() << ","
           << outWeight << "," << tag << ","
           << particleName << "," << pdg << ","
           << track->GetTrackID() << "," << track->GetParentID() << ","
           << creatorProcess << "," << sourceParticleName << "," << sourcePdg << ","
           << timeS << "," << crossing << "\n";
    ++nCrossings_;
    if (track->GetParentID() == 0) {
      ++nPrimaryCrossings_;
    } else {
      ++nSecondaryCrossings_;
    }
  }

	  void WriteSummary(const std::string& sourceCsv, int nInputRows, int nSimulated, long seed) {
	    phase_.flush();
	    activation_.flush();
	    std::ofstream summary((opt_.outDir + "/summary.json").c_str());
    summary << "{\n";
    summary << "  \"system\": \"geant4_all_particle_farfield_demo\",\n";
    summary << "  \"model\": \"FTFP_BERT_transport_with_focal_plane_crossing_scorer\",\n";
    summary << "  \"warning\": \"This connects the all-particle far-field source, existing optics mass scaffolds, focal-plane scorer, and secondary ion inventory logging. The channel/Laue mass geometry is still the current simplified scaffold, not a publication-grade full optical-assembly mass or delayed activation model.\",\n";
    summary << "  \"source_csv\": \"" << sourceCsv << "\",\n";
    summary << "  \"seed\": " << seed << ",\n";
    summary << "  \"focal_z_mm\": " << opt_.focalZMm << ",\n";
    summary << "  \"optics_mass\": \"" << opt_.opticsMass << "\",\n";
    summary << "  \"channel_ring_config\": \"" << opt_.channelRingConfigPath << "\",\n";
    summary << "  \"laue_ring_config\": \"" << opt_.laueRingConfigPath << "\",\n";
    summary << "  \"crossing_direction\": \"" << opt_.crossingDirection << "\",\n";
    summary << "  \"kill_after_crossing\": " << (opt_.killAfterCrossing ? "true" : "false") << ",\n";
    summary << "  \"world_half_xy_mm\": " << opt_.worldHalfXYMm << ",\n";
    summary << "  \"world_half_z_mm\": " << opt_.worldHalfZMm << ",\n";
    summary << "  \"n_input_rows\": " << nInputRows << ",\n";
    summary << "  \"n_simulated\": " << nSimulated << ",\n";
    summary << "  \"n_crossings\": " << nCrossings_ << ",\n";
    summary << "  \"n_primary_crossings\": " << nPrimaryCrossings_ << ",\n";
    summary << "  \"n_secondary_crossings\": " << nSecondaryCrossings_ << ",\n";
    summary << "  \"activation_inventory_csv\": \"activation_inventory.csv\",\n";
    summary << "  \"n_activation_ion_candidates\": " << nActivationIons_ << ",\n";
    summary << "  \"activation_inventory_note\": \"Secondary ions produced during prompt transport are recorded as isotope-inventory candidates. This is not a delayed radioactive-decay source; cooling/observation-time decay generation is a separate workflow.\"\n";
    summary << "}\n";
  }

  bool killAfterCrossing() const { return opt_.killAfterCrossing; }

 private:
	  Options opt_;
	  const std::vector<SourcePrimary>* primaries_;
	  std::ofstream phase_;
	  std::ofstream activation_;
	  long nCrossings_;
	  long nPrimaryCrossings_;
	  long nSecondaryCrossings_;
	  long nActivationIons_;
	};

class FocalPlaneSteppingAction : public G4UserSteppingAction {
 public:
  explicit FocalPlaneSteppingAction(FarfieldRunState* state) : state_(state) {}

  void UserSteppingAction(const G4Step* step) override {
    const double preZ = step->GetPreStepPoint()->GetPosition().z();
    const double postZ = step->GetPostStepPoint()->GetPosition().z();
    if (!state_->AcceptCrossing(preZ, postZ)) return;
    state_->RecordCrossing(step);
    if (state_->killAfterCrossing()) step->GetTrack()->SetTrackStatus(fStopAndKill);
  }

 private:
  FarfieldRunState* state_;
	};

	class ActivationTrackingAction : public G4UserTrackingAction {
	 public:
	  explicit ActivationTrackingAction(FarfieldRunState* state) : state_(state) {}

	  void PreUserTrackingAction(const G4Track* track) override { state_->RecordActivationIon(track); }

	 private:
	  FarfieldRunState* state_;
	};

}  // namespace

int main(int argc, char** argv) {
  try {
    const Options opt = ParseOptions(argc, argv);
    std::vector<SourcePrimary> primaries = ReadSourceCsv(opt.sourceCsv);
    if (primaries.empty()) throw std::runtime_error("source CSV has no positive-weight primaries");
    const int nEvents = std::min<int>(opt.nEvents, static_cast<int>(primaries.size()));
    CLHEP::HepRandom::setTheSeed(opt.seed);

    FarfieldRunState state(opt, &primaries);
    G4RunManager* runManager = new G4RunManager;
    runManager->SetUserInitialization(new FarfieldConstruction(opt));
    G4VModularPhysicsList* physics = new FTFP_BERT(0);
    physics->SetDefaultCutValue(0.1 * mm);
    runManager->SetUserInitialization(physics);
    runManager->SetUserAction(new FarfieldPrimaryGenerator(&primaries));
    runManager->SetUserAction(new FocalPlaneSteppingAction(&state));
    runManager->SetUserAction(new ActivationTrackingAction(&state));
    runManager->Initialize();
    runManager->BeamOn(nEvents);
    delete runManager;

    state.WriteSummary(opt.sourceCsv, static_cast<int>(primaries.size()), nEvents, opt.seed);
    std::cout << "ALL_PARTICLE_FARFIELD_SUMMARY"
              << " source=" << opt.sourceCsv
              << " out=" << opt.outDir
              << " events=" << nEvents
              << std::endl;
  } catch (const std::exception& exc) {
    std::cerr << "all_particle_farfield_demo error: " << exc.what() << std::endl;
    return 1;
  }
  return 0;
}
