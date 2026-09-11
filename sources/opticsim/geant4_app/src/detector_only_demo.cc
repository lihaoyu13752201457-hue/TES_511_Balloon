#include <algorithm>
#include <cerrno>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/stat.h>
#include <vector>

#include "G4Box.hh"
#include "G4Element.hh"
#include "G4EmStandardPhysics.hh"
#include "G4Event.hh"
#include "G4Gamma.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4ParticleGun.hh"
#include "G4RunManager.hh"
#include "G4SDManager.hh"
#include "G4Step.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "G4Track.hh"
#include "G4UserEventAction.hh"
#include "G4VModularPhysicsList.hh"
#include "G4VSensitiveDetector.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4VPhysicalVolume.hh"
#include "G4VProcess.hh"
#include "G4VTouchable.hh"
#include "globals.hh"
#include "Randomize.hh"

namespace {

struct PhaseSpacePhoton {
  int eventId;
  double energyKeV;
  double xMm;
  double yMm;
  double zMm;
  double ux;
  double uy;
  double uz;
  double weight;
  std::string sourceTag;
};

std::vector<std::string> SplitCSV(const std::string& line) {
  std::vector<std::string> out;
  std::stringstream ss(line);
  std::string item;
  while (std::getline(ss, item, ',')) {
    while (!item.empty() && (item.back() == '\r' || item.back() == '\n' || item.back() == ' ' || item.back() == '\t')) {
      item.pop_back();
    }
    std::size_t first = 0;
    while (first < item.size() && (item[first] == ' ' || item[first] == '\t')) {
      ++first;
    }
    out.push_back(item.substr(first));
  }
  return out;
}

std::map<std::string, std::size_t> HeaderMap(const std::vector<std::string>& header) {
  std::map<std::string, std::size_t> index;
  for (std::size_t i = 0; i < header.size(); ++i) {
    index[header[i]] = i;
  }
  return index;
}

std::string ValueAt(
    const std::vector<std::string>& row,
    const std::map<std::string, std::size_t>& header,
    const std::string& key) {
  std::map<std::string, std::size_t>::const_iterator it = header.find(key);
  if (it == header.end() || it->second >= row.size()) {
    throw std::runtime_error("phase-space CSV is missing column: " + key);
  }
  return row[it->second];
}

std::vector<PhaseSpacePhoton> ReadPhaseSpace(const std::string& path) {
  std::ifstream in(path.c_str());
  if (!in) {
    throw std::runtime_error("cannot open phase-space CSV: " + path);
  }
  std::string line;
  if (!std::getline(in, line)) {
    throw std::runtime_error("empty phase-space CSV: " + path);
  }
  const std::map<std::string, std::size_t> header = HeaderMap(SplitCSV(line));
  std::vector<PhaseSpacePhoton> photons;
  while (std::getline(in, line)) {
    if (line.empty()) continue;
    const std::vector<std::string> row = SplitCSV(line);
    PhaseSpacePhoton photon;
    photon.eventId = std::atoi(ValueAt(row, header, "event_id").c_str());
    photon.energyKeV = std::atof(ValueAt(row, header, "E_keV").c_str());
    photon.xMm = std::atof(ValueAt(row, header, "x_mm").c_str());
    photon.yMm = std::atof(ValueAt(row, header, "y_mm").c_str());
    photon.zMm = std::atof(ValueAt(row, header, "z_mm").c_str());
    photon.ux = std::atof(ValueAt(row, header, "ux").c_str());
    photon.uy = std::atof(ValueAt(row, header, "uy").c_str());
    photon.uz = std::atof(ValueAt(row, header, "uz").c_str());
    photon.weight = std::atof(ValueAt(row, header, "weight").c_str());
    photon.sourceTag = ValueAt(row, header, "source_tag");
    photons.push_back(photon);
  }
  return photons;
}

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

std::string PixelUID(int layer, int i, int j) {
  std::ostringstream os;
  os << "L" << std::setw(2) << std::setfill('0') << layer
     << "_I" << std::setw(2) << std::setfill('0') << i
     << "_J" << std::setw(2) << std::setfill('0') << j;
  return os.str();
}

struct EventAccum {
  int eventId;
  double weight;
  double totalTesEdepKeV;
  double bgoEdepKeV;
  std::set<std::string> tesPixels;
};

class DetectorRunState {
 public:
  explicit DetectorRunState(const std::string& outDir, double bgoThresholdKeV)
      : outDir_(outDir),
        bgoThresholdKeV_(bgoThresholdKeV),
        nHits_(0),
        nEvents_(0),
        nTesDetected_(0),
        nBgoVeto_(0),
        totalTesEdepKeV_(0.0),
        totalBgoEdepKeV_(0.0) {
    EnsureDirectory(outDir_);
    hits_.open((outDir_ + "/hits.csv").c_str());
    events_.open((outDir_ + "/event_summary.csv").c_str());
    if (!hits_ || !events_) {
      throw std::runtime_error("cannot open detector output CSV files in: " + outDir_);
    }
    hits_ << "event_id,track_id,detector_kind,layer_id,pixel_i,pixel_j,pixel_uid,"
          << "x_mm,y_mm,z_mm,edep_keV,process_name,time_ns\n";
    events_ << "event_id,total_tes_edep_keV,n_tes_pixel_hits,is_singlehit,is_multihit,"
            << "bgo_edep_keV,bgo_veto,reco_energy_keV,weight\n";
  }

  void BeginEvent(const PhaseSpacePhoton& photon) {
    current_.eventId = photon.eventId;
    current_.weight = photon.weight;
    current_.totalTesEdepKeV = 0.0;
    current_.bgoEdepKeV = 0.0;
    current_.tesPixels.clear();
  }

  void AddHit(
      int trackId,
      const std::string& detectorKind,
      int layerId,
      int pixelI,
      int pixelJ,
      const std::string& pixelUid,
      const G4ThreeVector& pos,
      double edepKeV,
      const std::string& processName,
      double timeNs) {
    if (edepKeV <= 0.0) return;
    hits_ << current_.eventId << "," << trackId << "," << detectorKind << ","
          << layerId << "," << pixelI << "," << pixelJ << "," << pixelUid << ","
          << std::setprecision(10) << pos.x() / mm << "," << pos.y() / mm << ","
          << pos.z() / mm << "," << edepKeV << "," << processName << ","
          << timeNs << "\n";
    ++nHits_;
    if (detectorKind == "TES_PIXEL") {
      current_.totalTesEdepKeV += edepKeV;
      current_.tesPixels.insert(pixelUid);
    } else if (detectorKind == "BGO") {
      current_.bgoEdepKeV += edepKeV;
    }
  }

  void EndEvent() {
    const int nPixels = static_cast<int>(current_.tesPixels.size());
    const int isSingle = nPixels == 1 ? 1 : 0;
    const int isMulti = nPixels > 1 ? 1 : 0;
    const int bgoVeto = current_.bgoEdepKeV >= bgoThresholdKeV_ ? 1 : 0;
    events_ << current_.eventId << "," << std::setprecision(10)
            << current_.totalTesEdepKeV << "," << nPixels << ","
            << isSingle << "," << isMulti << "," << current_.bgoEdepKeV << ","
            << bgoVeto << "," << current_.totalTesEdepKeV << ","
            << current_.weight << "\n";
    ++nEvents_;
    if (current_.totalTesEdepKeV > 0.0) ++nTesDetected_;
    if (bgoVeto) ++nBgoVeto_;
    totalTesEdepKeV_ += current_.totalTesEdepKeV;
    totalBgoEdepKeV_ += current_.bgoEdepKeV;
  }

  void WriteSummary(
      const std::string& sourcePath,
      int nInputPhotons,
      int nSimulated,
      long seed) {
    hits_.flush();
    events_.flush();
    std::ofstream summary((outDir_ + "/summary.json").c_str());
    summary << "{\n";
    summary << "  \"system\": \"geant4_detector_only_demo\",\n";
    summary << "  \"model\": \"geant4_emstandard_tes_bgo_minimal_geometry\",\n";
    summary << "  \"warning\": \"Standalone detector-only Geant4 prototype; geometry/source/hit contract scaffold, not yet a validated TES/BGO flight mass model.\",\n";
    summary << "  \"source_phase_space\": \"" << sourcePath << "\",\n";
    summary << "  \"seed\": " << seed << ",\n";
    summary << "  \"n_input_photons\": " << nInputPhotons << ",\n";
    summary << "  \"n_simulated\": " << nSimulated << ",\n";
    summary << "  \"n_events_written\": " << nEvents_ << ",\n";
    summary << "  \"n_hits\": " << nHits_ << ",\n";
    summary << "  \"n_tes_detected\": " << nTesDetected_ << ",\n";
    summary << "  \"n_bgo_veto\": " << nBgoVeto_ << ",\n";
    summary << "  \"tes_detection_fraction\": "
            << (nEvents_ ? static_cast<double>(nTesDetected_) / nEvents_ : 0.0) << ",\n";
    summary << "  \"bgo_veto_fraction\": "
            << (nEvents_ ? static_cast<double>(nBgoVeto_) / nEvents_ : 0.0) << ",\n";
    summary << "  \"total_tes_edep_keV\": " << totalTesEdepKeV_ << ",\n";
    summary << "  \"total_bgo_edep_keV\": " << totalBgoEdepKeV_ << "\n";
    summary << "}\n";
  }

 private:
  std::string outDir_;
  double bgoThresholdKeV_;
  std::ofstream hits_;
  std::ofstream events_;
  EventAccum current_;
  long nHits_;
  long nEvents_;
  long nTesDetected_;
  long nBgoVeto_;
  double totalTesEdepKeV_;
  double totalBgoEdepKeV_;
};

class DetectorSensitiveDetector : public G4VSensitiveDetector {
 public:
  explicit DetectorSensitiveDetector(const G4String& name, DetectorRunState* state)
      : G4VSensitiveDetector(name), state_(state) {}

  G4bool ProcessHits(G4Step* step, G4TouchableHistory*) override {
    const double edepKeV = step->GetTotalEnergyDeposit() / keV;
    if (edepKeV <= 0.0) return true;
    const G4VTouchable* touchable = step->GetPreStepPoint()->GetTouchable();
    const G4VPhysicalVolume* volume = step->GetPreStepPoint()->GetPhysicalVolume();
    const std::string volumeName = volume ? volume->GetName() : "";
    std::string kind = "PASSIVE";
    int layer = -1;
    int i = -1;
    int j = -1;
    std::string uid = "PASSIVE";
    if (volumeName.find("TESPixel") != std::string::npos) {
      kind = "TES_PIXEL";
      const int copyNo = touchable ? touchable->GetCopyNumber() : -1;
      const int perLayer = 20 * 20;
      layer = copyNo / perLayer;
      const int rem = copyNo % perLayer;
      i = rem % 20;
      j = rem / 20;
      uid = PixelUID(layer, i, j);
    } else if (volumeName.find("BGO") != std::string::npos) {
      kind = "BGO";
      uid = "BGO";
    }
    const G4VProcess* proc = step->GetPostStepPoint()->GetProcessDefinedStep();
    const std::string processName = proc ? proc->GetProcessName() : "unknown";
    state_->AddHit(
        step->GetTrack()->GetTrackID(),
        kind,
        layer,
        i,
        j,
        uid,
        step->GetPostStepPoint()->GetPosition(),
        edepKeV,
        processName,
        step->GetPostStepPoint()->GetGlobalTime() / ns);
    return true;
  }

 private:
  DetectorRunState* state_;
};

class DetectorConstruction : public G4VUserDetectorConstruction {
 public:
  explicit DetectorConstruction(DetectorRunState* state) : state_(state) {}

  G4VPhysicalVolume* Construct() override {
    G4NistManager* nist = G4NistManager::Instance();
    G4Material* vacuum = nist->FindOrBuildMaterial("G4_Galactic");
    G4Material* bi = nist->FindOrBuildMaterial("G4_Bi");
    G4Material* bgo = BuildBGO(nist);

    const double pixelX = 1.45 * mm;
    const double pixelY = 1.45 * mm;
    const double pixelZ = 2.0 * mm;
    const int pixelsX = 20;
    const int pixelsY = 20;
    const int layers = 8;
    const double activeX = pixelsX * pixelX;
    const double activeY = pixelsY * pixelY;
    const double stackZ = layers * pixelZ;
    const double side = 20.0 * mm;
    const double bottom = 50.0 * mm;

    G4Box* worldSolid = new G4Box(
        "WorldSolid",
        activeX / 2.0 + side + 20.0 * mm,
        activeY / 2.0 + side + 20.0 * mm,
        90.0 * mm);
    G4LogicalVolume* worldLogic = new G4LogicalVolume(worldSolid, vacuum, "WorldLogical");
    G4VPhysicalVolume* world =
        new G4PVPlacement(0, G4ThreeVector(), worldLogic, "World", 0, false, 0);

    G4Box* pixelSolid = new G4Box("TESPixelSolid", pixelX / 2.0, pixelY / 2.0, pixelZ / 2.0);
    G4LogicalVolume* pixelLogic = new G4LogicalVolume(pixelSolid, bi, "TESPixelLogical");
    for (int layer = 0; layer < layers; ++layer) {
      for (int j = 0; j < pixelsY; ++j) {
        for (int i = 0; i < pixelsX; ++i) {
          const double x = -activeX / 2.0 + pixelX / 2.0 + i * pixelX;
          const double y = -activeY / 2.0 + pixelY / 2.0 + j * pixelY;
          const double z = pixelZ / 2.0 + layer * pixelZ;
          const int copyNo = layer * pixelsX * pixelsY + j * pixelsX + i;
          new G4PVPlacement(
              0,
              G4ThreeVector(x, y, z),
              pixelLogic,
              "TESPixel",
              worldLogic,
              false,
              copyNo);
        }
      }
    }

    G4Box* bottomSolid = new G4Box(
        "BGOBottomSolid",
        activeX / 2.0 + side,
        activeY / 2.0 + side,
        bottom / 2.0);
    G4LogicalVolume* bottomLogic = new G4LogicalVolume(bottomSolid, bgo, "BGOBottomLogical");
    new G4PVPlacement(
        0,
        G4ThreeVector(0.0, 0.0, stackZ + bottom / 2.0),
        bottomLogic,
        "BGOBottom",
        worldLogic,
        false,
        9000);

    G4Box* sideXSolid = new G4Box("BGOSideXSolid", side / 2.0, activeY / 2.0, stackZ / 2.0);
    G4LogicalVolume* sideXLogic = new G4LogicalVolume(sideXSolid, bgo, "BGOSideXLogical");
    new G4PVPlacement(
        0,
        G4ThreeVector(activeX / 2.0 + side / 2.0, 0.0, stackZ / 2.0),
        sideXLogic,
        "BGOSideXPlus",
        worldLogic,
        false,
        9001);
    new G4PVPlacement(
        0,
        G4ThreeVector(-activeX / 2.0 - side / 2.0, 0.0, stackZ / 2.0),
        sideXLogic,
        "BGOSideXMinus",
        worldLogic,
        false,
        9002);

    G4Box* sideYSolid = new G4Box(
        "BGOSideYSolid",
        activeX / 2.0 + side,
        side / 2.0,
        stackZ / 2.0);
    G4LogicalVolume* sideYLogic = new G4LogicalVolume(sideYSolid, bgo, "BGOSideYLogical");
    new G4PVPlacement(
        0,
        G4ThreeVector(0.0, activeY / 2.0 + side / 2.0, stackZ / 2.0),
        sideYLogic,
        "BGOSideYPlus",
        worldLogic,
        false,
        9003);
    new G4PVPlacement(
        0,
        G4ThreeVector(0.0, -activeY / 2.0 - side / 2.0, stackZ / 2.0),
        sideYLogic,
        "BGOSideYMinus",
        worldLogic,
        false,
        9004);

    DetectorSensitiveDetector* sd = new DetectorSensitiveDetector("DetectorOnlySD", state_);
    G4SDManager::GetSDMpointer()->AddNewDetector(sd);
    pixelLogic->SetSensitiveDetector(sd);
    bottomLogic->SetSensitiveDetector(sd);
    sideXLogic->SetSensitiveDetector(sd);
    sideYLogic->SetSensitiveDetector(sd);
    return world;
  }

 private:
  G4Material* BuildBGO(G4NistManager* nist) const {
    G4Material* existing = G4Material::GetMaterial("BGO", false);
    if (existing) return existing;
    G4Material* bgo = new G4Material("BGO", 7.13 * g / cm3, 3);
    bgo->AddElement(nist->FindOrBuildElement("Bi"), 4);
    bgo->AddElement(nist->FindOrBuildElement("Ge"), 3);
    bgo->AddElement(nist->FindOrBuildElement("O"), 12);
    return bgo;
  }

  DetectorRunState* state_;
};

class DetectorPhysicsList : public G4VModularPhysicsList {
 public:
  DetectorPhysicsList() {
    defaultCutValue = 0.1 * mm;
    RegisterPhysics(new G4EmStandardPhysics());
  }
};

class PhaseSpacePrimaryGenerator : public G4VUserPrimaryGeneratorAction {
 public:
  explicit PhaseSpacePrimaryGenerator(const std::vector<PhaseSpacePhoton>* photons)
      : photons_(photons) {
    gun_ = new G4ParticleGun(1);
    gun_->SetParticleDefinition(G4Gamma::GammaDefinition());
  }

  ~PhaseSpacePrimaryGenerator() override {
    delete gun_;
  }

  void GeneratePrimaries(G4Event* event) override {
    const int idx = event->GetEventID();
    const PhaseSpacePhoton& photon = photons_->at(static_cast<std::size_t>(idx));
    gun_->SetParticleEnergy(photon.energyKeV * keV);
    gun_->SetParticlePosition(G4ThreeVector(photon.xMm * mm, photon.yMm * mm, -1.0 * mm));
    G4ThreeVector direction(photon.ux, photon.uy, photon.uz);
    if (direction.mag2() <= 0.0) {
      direction = G4ThreeVector(0.0, 0.0, 1.0);
    }
    gun_->SetParticleMomentumDirection(direction.unit());
    gun_->GeneratePrimaryVertex(event);
  }

 private:
  const std::vector<PhaseSpacePhoton>* photons_;
  G4ParticleGun* gun_;
};

class DetectorEventAction : public G4UserEventAction {
 public:
  DetectorEventAction(const std::vector<PhaseSpacePhoton>* photons, DetectorRunState* state)
      : photons_(photons), state_(state) {}

  void BeginOfEventAction(const G4Event* event) override {
    state_->BeginEvent(photons_->at(static_cast<std::size_t>(event->GetEventID())));
  }

  void EndOfEventAction(const G4Event*) override {
    state_->EndEvent();
  }

 private:
  const std::vector<PhaseSpacePhoton>* photons_;
  DetectorRunState* state_;
};

}  // namespace

int main(int argc, char** argv) {
  std::string sourcePath = "runs/channel_4ring_calibrated_v2/phase_space.csv";
  std::string outDir = "runs/geant4_detector_only_smoke";
  int nEventsRequested = 1000;
  long seed = 12345;
  if (argc > 1) sourcePath = argv[1];
  if (argc > 2) outDir = argv[2];
  if (argc > 3) nEventsRequested = std::atoi(argv[3]);
  if (argc > 4) seed = std::atol(argv[4]);

  try {
    std::vector<PhaseSpacePhoton> photons = ReadPhaseSpace(sourcePath);
    if (photons.empty()) {
      throw std::runtime_error("phase-space source has no photons");
    }
    const int nEvents = std::min<int>(nEventsRequested, static_cast<int>(photons.size()));
    CLHEP::HepRandom::setTheSeed(seed);

    DetectorRunState state(outDir, 70.0);
    G4RunManager* runManager = new G4RunManager;
    runManager->SetUserInitialization(new DetectorConstruction(&state));
    runManager->SetUserInitialization(new DetectorPhysicsList());
    runManager->SetUserAction(new PhaseSpacePrimaryGenerator(&photons));
    runManager->SetUserAction(new DetectorEventAction(&photons, &state));
    runManager->Initialize();
    runManager->BeamOn(nEvents);
    delete runManager;

    state.WriteSummary(sourcePath, static_cast<int>(photons.size()), nEvents, seed);
    std::cout << "DETECTOR_ONLY_SUMMARY"
              << " source=" << sourcePath
              << " out=" << outDir
              << " events=" << nEvents
              << std::endl;
  } catch (const std::exception& exc) {
    std::cerr << "detector_only_demo error: " << exc.what() << std::endl;
    return 1;
  }
  return 0;
}
