#include <algorithm>
#include <cfloat>
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

#include "G4Box.hh"
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
#include "G4VPhysicalVolume.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPhysicsList.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "Randomize.hh"

#include "optics/ReflectivityTable.hh"

namespace {

constexpr double kPi = 3.14159265358979323846;
constexpr int kCopyStride = 1000;

struct RingSpec {
  int ringId = 0;
  double radiusCm = 2.25;
  double bendDeg = 0.11;
  double lengthCm = 2.1;
  double widthCm = 1.0;
  double thicknessMm = 7.5;
  int nTiles = 14;
  int nBounceCalibrated = 1;
  double thetaCalibratedRad = 1.5044773216627076e-4;
};

struct Options {
  int nEvents = 100000;
  std::string outDir = "runs/channel/geant4_4ring_multibounce_calibrated";
  long seed = 20260520;
  std::string ringConfigPath = "data/channel/cam511_channel_rings.csv";
  std::string reflectivityTablePath = "data/reflectivity/WSi_511keV_parratt_grid_dense.csv";
  std::string stackId = "WSi_30_150";
  std::string thetaPolicy = "ring_calibrated";
  std::string openFractionPolicy = "already_in_target";
  std::string pathAbsorptionPolicy = "none";
  double energyKeV = 511.0;
  double focalLengthMm = 12000.0;
  double apertureRadiusMm = 45.0;
  double spotD90Cm = 3.6;
  double openFraction = 150.0 / 180.0;
  double diagnosticThetaRad = 1.5e-4;
  double siMuCmInv = 0.20193273411049242;
};

struct RingStats {
  long nPrimaries = 0;
  long nExit = 0;
  long nAbsorb = 0;
  long nPathAbsorb = 0;
  long nLeak = 0;
  long nBounceRows = 0;
  double sumTheta = 0.0;
  double sumReflectivity = 0.0;
};

struct RingOpticsCache {
  int nBounce = 1;
  double thetaRad = 0.0;
  optics::ReflectivityTableRow probabilities;
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

std::string ReadString(const std::map<std::string, std::string>& row, const std::string& key) {
  const auto it = row.find(key);
  if (it == row.end() || it->second.empty()) throw std::runtime_error("missing CSV column: " + key);
  return it->second;
}

double ReadDouble(const std::map<std::string, std::string>& row, const std::string& key) {
  return std::stod(ReadString(row, key));
}

int ReadInt(const std::map<std::string, std::string>& row, const std::string& key) {
  return std::stoi(ReadString(row, key));
}

std::vector<RingSpec> LoadRings(const std::string& path) {
  std::ifstream input(path.c_str());
  if (!input) throw std::runtime_error("failed to open channel ring config: " + path);
  std::string line;
  if (!std::getline(input, line)) throw std::runtime_error("empty channel ring config: " + path);
  const std::vector<std::string> headers = SplitCsvLine(line);
  std::vector<RingSpec> rings;
  while (std::getline(input, line)) {
    if (Trim(line).empty()) continue;
    const auto cells = SplitCsvLine(line);
    std::map<std::string, std::string> row;
    for (std::size_t i = 0; i < headers.size() && i < cells.size(); ++i) row[headers[i]] = cells[i];
    RingSpec ring;
    ring.ringId = ReadInt(row, "ring_id");
    ring.radiusCm = ReadDouble(row, "radius_cm");
    ring.bendDeg = ReadDouble(row, "bending_angle_deg");
    ring.lengthCm = ReadDouble(row, "length_cm");
    ring.widthCm = ReadDouble(row, "width_cm");
    ring.thicknessMm = ReadDouble(row, "thickness_mm");
    ring.nTiles = ReadInt(row, "n_tiles");
    ring.nBounceCalibrated = ReadInt(row, "n_bounce_calibrated");
    ring.thetaCalibratedRad = ReadDouble(row, "theta_calibrated_rad");
    rings.push_back(ring);
  }
  if (rings.empty()) throw std::runtime_error("channel ring config has no rows: " + path);
  std::sort(rings.begin(), rings.end(), [](const RingSpec& a, const RingSpec& b) { return a.ringId < b.ringId; });
  return rings;
}

Options ParseOptions(int argc, char** argv) {
  Options opt;
  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    auto require = [&](const std::string& name) -> const char* {
      if (i + 1 >= argc) throw std::runtime_error("missing value for " + name);
      return argv[++i];
    };
    if (arg == "--n") {
      opt.nEvents = std::atoi(require(arg));
    } else if (arg == "--out") {
      opt.outDir = require(arg);
    } else if (arg == "--seed") {
      opt.seed = std::atol(require(arg));
    } else if (arg == "--ring-config") {
      opt.ringConfigPath = require(arg);
    } else if (arg == "--reflectivity-table") {
      opt.reflectivityTablePath = require(arg);
    } else if (arg == "--stack-id") {
      opt.stackId = require(arg);
    } else if (arg == "--theta-policy") {
      opt.thetaPolicy = require(arg);
    } else if (arg == "--open-fraction-policy") {
      opt.openFractionPolicy = require(arg);
    } else if (arg == "--path-absorption-policy") {
      opt.pathAbsorptionPolicy = require(arg);
    } else if (arg == "--diagnostic-theta-rad") {
      opt.diagnosticThetaRad = std::atof(require(arg));
    } else if (arg == "--si-mu-cm-inv") {
      opt.siMuCmInv = std::atof(require(arg));
    } else if (arg == "--help" || arg == "-h") {
      std::cout << "Usage: " << argv[0]
                << " --n N --out DIR --theta-policy ring_calibrated|paper_bend|fixed"
                << " --open-fraction-policy already_in_target|paper_once"
                << " --path-absorption-policy none|si_length\n";
      std::exit(0);
    } else {
      throw std::runtime_error("unknown option: " + arg);
    }
  }
  if (opt.nEvents <= 0) throw std::runtime_error("--n must be positive");
  if (opt.siMuCmInv < 0.0) throw std::runtime_error("--si-mu-cm-inv must be non-negative");
  if (opt.pathAbsorptionPolicy != "none" && opt.pathAbsorptionPolicy != "si_length") {
    throw std::runtime_error("unknown path absorption policy: " + opt.pathAbsorptionPolicy);
  }
  return opt;
}

bool NameContains(const G4VPhysicalVolume* volume, const G4String& token) {
  if (volume == 0) return false;
  if (volume->GetName().find(token) != G4String::npos) return true;
  const G4LogicalVolume* logical = volume->GetLogicalVolume();
  return logical != 0 && logical->GetName().find(token) != G4String::npos;
}

int TotalTiles(const std::vector<RingSpec>& rings) {
  int total = 0;
  for (const auto& ring : rings) total += ring.nTiles;
  return total;
}

std::pair<const RingSpec*, int> RingAndTileForEvent(const std::vector<RingSpec>& rings, int eventId) {
  int idx = eventId % TotalTiles(rings);
  for (const auto& ring : rings) {
    if (idx < ring.nTiles) return {&ring, idx};
    idx -= ring.nTiles;
  }
  return {&rings.back(), rings.back().nTiles - 1};
}

const RingSpec& RingFromCopyNo(const std::vector<RingSpec>& rings, int copyNo) {
  const int ringId = copyNo / kCopyStride;
  for (const auto& ring : rings) {
    if (ring.ringId == ringId) return ring;
  }
  throw std::runtime_error("invalid channel ring copy number");
}

int BounceCountForPolicy(const RingSpec& ring, const Options& opt) {
  if (opt.thetaPolicy == "ring_calibrated") return std::max(1, ring.nBounceCalibrated);
  if (opt.thetaPolicy == "fixed" || opt.thetaPolicy == "paper_bend") {
    const double bendRad = ring.bendDeg * kPi / 180.0;
    return std::max(1, static_cast<int>(std::ceil(bendRad / (2.0 * opt.diagnosticThetaRad))));
  }
  throw std::runtime_error("unknown theta policy: " + opt.thetaPolicy);
}

double ThetaForPolicy(const RingSpec& ring, const Options& opt, int nBounce) {
  if (opt.thetaPolicy == "ring_calibrated") return ring.thetaCalibratedRad;
  if (opt.thetaPolicy == "fixed") return opt.diagnosticThetaRad;
  if (opt.thetaPolicy == "paper_bend") {
    const double bendRad = ring.bendDeg * kPi / 180.0;
    return bendRad / (2.0 * std::max(1, nBounce));
  }
  throw std::runtime_error("unknown theta policy: " + opt.thetaPolicy);
}

double SpotD90Cm(const std::vector<double>& xsMm, const std::vector<double>& ysMm) {
  if (xsMm.empty()) return 0.0;
  std::vector<double> radii;
  for (std::size_t i = 0; i < xsMm.size(); ++i) {
    radii.push_back(std::sqrt(xsMm[i] * xsMm[i] + ysMm[i] * ysMm[i]));
  }
  std::sort(radii.begin(), radii.end());
  const std::size_t idx = std::min<std::size_t>(
      radii.size() - 1,
      static_cast<std::size_t>(std::ceil(0.9 * radii.size()) - 1));
  return 2.0 * radii[idx] / 10.0;
}

class ChannelRunState {
 public:
  ChannelRunState(const Options& opt, const std::vector<RingSpec>& rings, const optics::ReflectivityTable& table)
      : opt_(opt), rings_(rings), table_(table), ringStats_(rings.size()) {
    for (const auto& ring : rings_) {
      RingOpticsCache cached;
      cached.nBounce = BounceCountForPolicy(ring, opt_);
      cached.thetaRad = ThetaForPolicy(ring, opt_, cached.nBounce);
      cached.probabilities =
          table_.Lookup(opt_.energyKeV, cached.thetaRad, optics::ReflectivityLookupMode::kLinear, opt_.stackId);
      opticsCache_[ring.ringId] = cached;
    }
    EnsureDirectory(opt_.outDir);
    phase_.open((opt_.outDir + "/phase_space.csv").c_str());
    history_.open((opt_.outDir + "/optics_history.csv").c_str());
    if (!phase_ || !history_) throw std::runtime_error("cannot open channel multibounce output files");
    phase_ << "event_id,E_keV,x_mm,y_mm,z_mm,ux,uy,uz,weight,source_tag,particle_name,pdg_encoding,track_id,parent_id\n";
    history_ << "event_id,track_id,optics_kind,stage,ring_id,tile_id,surface_id,E_keV,"
             << "x_mm,y_mm,z_mm,ux_in,uy_in,uz_in,ux_out,uy_out,uz_out,"
             << "grazing_angle_rad,p_reflect,p_absorb,p_transmit,n_bounce,weight\n";
  }

  void SimulatePath(
      int eventId,
      int trackId,
      const RingSpec& ring,
      int tileId,
      const G4ThreeVector& entryPos,
      const G4ThreeVector& inDir) {
    if (ring.ringId < 0 || ring.ringId >= static_cast<int>(ringStats_.size())) {
      throw std::runtime_error("ring id outside stats range");
    }
    RingStats& stats = ringStats_[ring.ringId];
    ++stats.nPrimaries;

    const RingOpticsCache& optics = opticsCache_.at(ring.ringId);
    const int nBounce = optics.nBounce;
    const double theta = optics.thetaRad;
    const optics::ReflectivityTableRow& probs = optics.probabilities;

    const double phi = 2.0 * kPi * static_cast<double>(tileId) / static_cast<double>(ring.nTiles);
    const G4ThreeVector radial(std::cos(phi), std::sin(phi), 0.0);
    G4ThreeVector dir = inDir.unit();
    G4ThreeVector pos = entryPos;
    bool lost = false;

    if (opt_.openFractionPolicy == "paper_once") {
      const double uOpen = G4UniformRand();
      if (uOpen > opt_.openFraction) {
        ++stats.nLeak;
        RecordRow(eventId, trackId, "LEAK", ring, tileId, "open_fraction", pos, dir, dir, theta, 0.0, 0.0, 1.0, 0);
        return;
      }
    } else if (opt_.openFractionPolicy != "already_in_target") {
      throw std::runtime_error("unknown open fraction policy: " + opt_.openFractionPolicy);
    }

    const double segmentCm = ring.lengthCm / static_cast<double>(nBounce);
    const double segmentPathSurvival =
        opt_.pathAbsorptionPolicy == "si_length" ? std::exp(-opt_.siMuCmInv * segmentCm) : 1.0;

    for (int bounce = 1; bounce <= nBounce; ++bounce) {
      const G4ThreeVector before = dir;
      const double frac = static_cast<double>(bounce) / static_cast<double>(nBounce);
      const double focusDeflection = std::atan((ring.radiusCm * 10.0) / opt_.focalLengthMm);
      const double deflection = frac * focusDeflection;
      const G4ThreeVector after =
          (-std::sin(deflection) * radial + std::cos(deflection) * G4ThreeVector(0.0, 0.0, 1.0)).unit();
      const double zMm = frac * ring.lengthCm * 10.0;
      pos = G4ThreeVector(entryPos.x(), entryPos.y(), zMm * mm);

      if (opt_.pathAbsorptionPolicy == "si_length" && G4UniformRand() > segmentPathSurvival) {
        ++stats.nAbsorb;
        ++stats.nPathAbsorb;
        RecordRow(
            eventId,
            trackId,
            "ABSORB",
            ring,
            tileId,
            "si_path_absorption",
            pos,
            before,
            before,
            theta,
            0.0,
            1.0 - segmentPathSurvival,
            segmentPathSurvival,
            bounce);
        lost = true;
        break;
      }

      const double u = G4UniformRand();
      ++stats.nBounceRows;
      stats.sumTheta += theta;
      stats.sumReflectivity += probs.R;
      if (u < probs.A) {
        ++stats.nAbsorb;
        RecordRow(eventId, trackId, "ABSORB", ring, tileId, "multibounce", pos, before, before, theta, probs.R, probs.A, probs.T, bounce);
        lost = true;
        break;
      }
      if (u >= probs.A + probs.R) {
        ++stats.nLeak;
        RecordRow(eventId, trackId, "LEAK", ring, tileId, "multibounce", pos, before, before, theta, probs.R, probs.A, probs.T, bounce);
        lost = true;
        break;
      }
      dir = after;
      RecordRow(eventId, trackId, "BOUNCE", ring, tileId, "multibounce", pos, before, dir, theta, probs.R, probs.A, probs.T, bounce);
    }
    if (lost) return;

    const double spotSigmaMm = (opt_.spotD90Cm * 10.0) / std::sqrt(-2.0 * std::log(0.1)) / 2.0;
    const G4ThreeVector target(
        G4RandGauss::shoot(0.0, spotSigmaMm) * mm,
        G4RandGauss::shoot(0.0, spotSigmaMm) * mm,
        opt_.focalLengthMm * mm);
    const G4ThreeVector outDir = (target - pos).unit();
    ++stats.nExit;
    RecordRow(eventId, trackId, "EXIT", ring, tileId, "focal_plane", pos, dir, outDir, theta, 1.0, 0.0, 0.0, nBounce);
    const double t = (opt_.focalLengthMm * mm - pos.z()) / outDir.z();
    const G4ThreeVector focus = pos + t * outDir;
    focusXs_.push_back(focus.x() / mm);
    focusYs_.push_back(focus.y() / mm);
    phase_ << eventId << "," << opt_.energyKeV << "," << focus.x() / mm << ","
           << focus.y() / mm << "," << opt_.focalLengthMm << "," << outDir.x() << ","
           << outDir.y() << "," << outDir.z() << ",1.0,geant4_channel_4ring_multibounce,gamma,22,"
           << trackId << ",0\n";
  }

  void WriteOutputs() {
    phase_.flush();
    history_.flush();
    std::ofstream perRing((opt_.outDir + "/per_ring_summary.csv").c_str());
    perRing << "ring_id,radius_cm,bending_angle_deg,length_cm,n_tiles,n_bounce,theta_rad,"
            << "n_primaries,n_survived,n_absorbed,n_path_absorbed,n_leaked,"
            << "transmissivity,path_survival,mean_R,mean_theta_rad\n";
    long total = 0;
    long exit = 0;
    long absorb = 0;
    long pathAbsorb = 0;
    long leak = 0;
    for (const auto& ring : rings_) {
      const RingStats& stats = ringStats_[ring.ringId];
      total += stats.nPrimaries;
      exit += stats.nExit;
      absorb += stats.nAbsorb;
      pathAbsorb += stats.nPathAbsorb;
      leak += stats.nLeak;
      const RingOpticsCache& optics = opticsCache_.at(ring.ringId);
      const int nBounce = optics.nBounce;
      const double theta = optics.thetaRad;
      const double meanR = stats.nBounceRows ? stats.sumReflectivity / stats.nBounceRows : 0.0;
      const double meanTheta = stats.nBounceRows ? stats.sumTheta / stats.nBounceRows : 0.0;
      const double pathSurvival =
          opt_.pathAbsorptionPolicy == "si_length" ? std::exp(-opt_.siMuCmInv * ring.lengthCm) : 1.0;
      perRing << ring.ringId << "," << ring.radiusCm << "," << ring.bendDeg << ","
              << ring.lengthCm << "," << ring.nTiles << "," << nBounce << ","
              << theta << "," << stats.nPrimaries << "," << stats.nExit << ","
              << stats.nAbsorb << "," << stats.nPathAbsorb << "," << stats.nLeak << ","
              << (stats.nPrimaries ? static_cast<double>(stats.nExit) / stats.nPrimaries : 0.0)
              << "," << pathSurvival << "," << meanR << "," << meanTheta << "\n";
    }

    const double transmissivity = total ? static_cast<double>(exit) / total : 0.0;
    const double apertureAreaCm2 = kPi * (opt_.apertureRadiusMm / 10.0) * (opt_.apertureRadiusMm / 10.0);
    std::ofstream summary((opt_.outDir + "/summary.json").c_str());
    summary << "{\n";
    summary << "  \"system\": \"geant4_channel_4ring_multibounce\",\n";
    summary << "  \"model\": \"paper_parameterized_multibounce_table_process_v1\",\n";
    summary << "  \"warning\": \"Geant4 app-level multi-bounce channel optics. It records per-bounce table-driven reflection, but it is still a parameterized path model, not a full wall-by-wall IDL geometry reproduction.\",\n";
    summary << "  \"geant4_bottom_code_modified\": false,\n";
    summary << "  \"schema_version\": \"channel_optics_summary_v2\",\n";
    summary << "  \"model_class\": \"calibrated_detector_handoff\",\n";
    summary << "  \"is_calibrated_handoff\": true,\n";
    summary << "  \"is_public_wallbywall_geometry\": false,\n";
    summary << "  \"is_first_principles_80pct_closure\": false,\n";
    summary << "  \"calibration_target\": \"511-CAM headline transmissivity scale; detector handoff only\",\n";
    summary << "  \"n_primaries\": " << total << ",\n";
    summary << "  \"n_survived\": " << exit << ",\n";
    summary << "  \"n_absorbed\": " << absorb << ",\n";
    summary << "  \"n_path_absorbed\": " << pathAbsorb << ",\n";
    summary << "  \"n_leaked\": " << leak << ",\n";
    summary << "  \"transmissivity\": " << transmissivity << ",\n";
    summary << "  \"target_transmissivity\": 0.8,\n";
    summary << "  \"effective_area_cm2\": " << apertureAreaCm2 * transmissivity << ",\n";
    summary << "  \"target_effective_area_cm2\": 50.89,\n";
    summary << "  \"spot_d90_cm\": " << SpotD90Cm(focusXs_, focusYs_) << ",\n";
    summary << "  \"target_spot_d90_cm\": 3.6,\n";
    summary << "  \"energy_keV\": " << opt_.energyKeV << ",\n";
    summary << "  \"focal_length_mm\": " << opt_.focalLengthMm << ",\n";
    summary << "  \"theta_policy\": \"" << opt_.thetaPolicy << "\",\n";
    summary << "  \"open_fraction_policy\": \"" << opt_.openFractionPolicy << "\",\n";
    summary << "  \"path_absorption_policy\": \"" << opt_.pathAbsorptionPolicy << "\",\n";
    summary << "  \"si_mu_cm_inv\": " << opt_.siMuCmInv << ",\n";
    summary << "  \"ring_config\": \"" << opt_.ringConfigPath << "\",\n";
    summary << "  \"reflectivity_table\": \"" << opt_.reflectivityTablePath << "\"\n";
    summary << "}\n";
  }

 private:
  void RecordRow(
      int eventId,
      int trackId,
      const std::string& stage,
      const RingSpec& ring,
      int tileId,
      const std::string& surfaceId,
      const G4ThreeVector& pos,
      const G4ThreeVector& inDir,
      const G4ThreeVector& outDir,
      double theta,
      double pReflect,
      double pAbsorb,
      double pTransmit,
      int bounceIndex) {
    history_ << eventId << "," << trackId << ",CHANNEL," << stage << ","
             << ring.ringId << "," << tileId << "," << surfaceId << ","
             << opt_.energyKeV << "," << std::setprecision(12)
             << pos.x() / mm << "," << pos.y() / mm << "," << pos.z() / mm << ","
             << inDir.x() << "," << inDir.y() << "," << inDir.z() << ","
             << outDir.x() << "," << outDir.y() << "," << outDir.z() << ","
             << theta << "," << pReflect << "," << pAbsorb << "," << pTransmit << ","
             << bounceIndex << ",1\n";
  }

  Options opt_;
  std::vector<RingSpec> rings_;
  const optics::ReflectivityTable& table_;
  std::ofstream phase_;
  std::ofstream history_;
  std::vector<RingStats> ringStats_;
  std::map<int, RingOpticsCache> opticsCache_;
  std::vector<double> focusXs_;
  std::vector<double> focusYs_;
};

class ChannelMultiBounceProcess : public G4VDiscreteProcess {
 public:
  ChannelMultiBounceProcess(ChannelRunState* state, const std::vector<RingSpec>& rings)
      : G4VDiscreteProcess("Channel4RingMultiBounceProcess"), state_(state), rings_(rings) {}

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
    if (volume == 0 || !NameContains(volume, "ChannelTile")) volume = step.GetPreStepPoint()->GetPhysicalVolume();
    const int copyNo = volume ? volume->GetCopyNo() : 0;
    const RingSpec& ring = RingFromCopyNo(rings_, copyNo);
    const int tileId = copyNo % kCopyStride;
    const G4Event* event = G4RunManager::GetRunManager()->GetCurrentEvent();
    const int eventId = event ? event->GetEventID() : -1;
    state_->SimulatePath(eventId, track.GetTrackID(), ring, tileId, step.GetPostStepPoint()->GetPosition(), track.GetMomentumDirection());
    aParticleChange.ProposeTrackStatus(fStopAndKill);
    return &aParticleChange;
  }

 private:
  ChannelRunState* state_;
  std::vector<RingSpec> rings_;
};

class ChannelConstruction : public G4VUserDetectorConstruction {
 public:
  explicit ChannelConstruction(const std::vector<RingSpec>& rings) : rings_(rings) {}

  G4VPhysicalVolume* Construct() override {
    G4NistManager* nist = G4NistManager::Instance();
    G4Material* vacuum = nist->FindOrBuildMaterial("G4_Galactic");
    G4Material* silicon = nist->FindOrBuildMaterial("G4_Si");
    G4Box* worldSolid = new G4Box("WorldSolid", 70.0 * mm, 70.0 * mm, 200.0 * mm);
    G4LogicalVolume* worldLogic = new G4LogicalVolume(worldSolid, vacuum, "WorldLogical");
    G4VPhysicalVolume* world = new G4PVPlacement(0, G4ThreeVector(), worldLogic, "World", 0, false, 0);
    G4Box* tileSolid = new G4Box("ChannelTileSolid", 2.0 * mm, 2.0 * mm, 0.05 * mm);
    G4LogicalVolume* tileLogic = new G4LogicalVolume(tileSolid, silicon, "ChannelTileLogical");
    for (const auto& ring : rings_) {
      for (int tile = 0; tile < ring.nTiles; ++tile) {
        const double phi = 2.0 * kPi * static_cast<double>(tile) / static_cast<double>(ring.nTiles);
        new G4PVPlacement(
            0,
            G4ThreeVector(ring.radiusCm * 10.0 * std::cos(phi) * mm, ring.radiusCm * 10.0 * std::sin(phi) * mm, 0.0),
            tileLogic,
            "ChannelTile",
            worldLogic,
            false,
            ring.ringId * kCopyStride + tile);
      }
    }
    return world;
  }

 private:
  std::vector<RingSpec> rings_;
};

class ChannelPhysicsList : public G4VUserPhysicsList {
 public:
  explicit ChannelPhysicsList(ChannelMultiBounceProcess* process) : process_(process) {}

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
  ChannelMultiBounceProcess* process_;
};

class ChannelPrimaryGenerator : public G4VUserPrimaryGeneratorAction {
 public:
  ChannelPrimaryGenerator(const Options& opt, const std::vector<RingSpec>& rings) : opt_(opt), rings_(rings) {
    gun_ = new G4ParticleGun(1);
    gun_->SetParticleDefinition(G4Gamma::GammaDefinition());
    gun_->SetParticleEnergy(opt_.energyKeV * keV);
  }

  ~ChannelPrimaryGenerator() override {
    delete gun_;
  }

  void GeneratePrimaries(G4Event* event) override {
    const auto ringAndTile = RingAndTileForEvent(rings_, event->GetEventID());
    const RingSpec& ring = *ringAndTile.first;
    const int tile = ringAndTile.second;
    const double phi = 2.0 * kPi * static_cast<double>(tile) / static_cast<double>(ring.nTiles);
    const double x = ring.radiusCm * 10.0 * std::cos(phi);
    const double y = ring.radiusCm * 10.0 * std::sin(phi);
    gun_->SetParticlePosition(G4ThreeVector(x * mm, y * mm, -5.0 * mm));
    gun_->SetParticleMomentumDirection(G4ThreeVector(0.0, 0.0, 1.0));
    gun_->GeneratePrimaryVertex(event);
  }

 private:
  Options opt_;
  std::vector<RingSpec> rings_;
  G4ParticleGun* gun_;
};

}  // namespace

int main(int argc, char** argv) {
  try {
    Options opt = ParseOptions(argc, argv);
    EnsureDirectory(opt.outDir);
    CLHEP::HepRandom::setTheSeed(opt.seed);
    const std::vector<RingSpec> rings = LoadRings(opt.ringConfigPath);
    optics::ReflectivityTable table = optics::ReflectivityTable::FromCsv(opt.reflectivityTablePath);
    ChannelRunState state(opt, rings, table);
    ChannelMultiBounceProcess* process = new ChannelMultiBounceProcess(&state, rings);
    G4RunManager* runManager = new G4RunManager;
    runManager->SetUserInitialization(new ChannelConstruction(rings));
    runManager->SetUserInitialization(new ChannelPhysicsList(process));
    runManager->SetUserAction(new ChannelPrimaryGenerator(opt, rings));
    runManager->Initialize();
    runManager->BeamOn(opt.nEvents);
    delete runManager;
    state.WriteOutputs();
    std::cout << "CHANNEL_4RING_MULTIBOUNCE_SUMMARY events=" << opt.nEvents
              << " out=" << opt.outDir << std::endl;
  } catch (const std::exception& exc) {
    std::cerr << "channel_4ring_multibounce_demo error: " << exc.what() << std::endl;
    return 1;
  }
  return 0;
}
