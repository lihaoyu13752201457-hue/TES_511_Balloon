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
#include "G4DynamicParticle.hh"
#include "G4EmStandardPhysics.hh"
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
#include "G4StepLimiter.hh"
#include "G4StepPoint.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "G4Track.hh"
#include "G4VDiscreteProcess.hh"
#include "G4VModularPhysicsList.hh"
#include "G4VPhysicalVolume.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPhysicsList.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4UserSteppingAction.hh"
#include "G4UserLimits.hh"
#include "G4VProcess.hh"
#include "Randomize.hh"

#include "optics/LaueEfficiencyTable.hh"

namespace {

constexpr double kPi = 3.14159265358979323846;
constexpr double kHcKeVA = 12.398419843320026;
constexpr int kCopyStride = 100000;

struct RingSpec {
  int ringId = 0;
  double designEnergyKeV = 511.0;
  double radiusMm = 61.6618;
  int nTiles = 64;
  std::string material = "Ge";
  int h = 1;
  int k = 1;
  int l = 1;
  double dSpacingA = 3.266;
  double tileSizeMm = 2.4;
  double thicknessMm = 2.0;
  double zOffsetMm = 0.0;
};

struct Options {
  int nEvents = 50000;
  std::string outDir = "runs/geant4_laue_bfull_process";
  long seed = 12345;
  std::string efficiencyTablePath = "data/laue/Ge111_480_550keV_darwin_mosaic_table.csv";
  std::string ringConfigPath = "data/laue/ge111_480_550keV_multiring_darwin_config.csv";
  std::string rockingCurvePath;
  std::string rockingCurveMapPath;
  bool requireRockingCurveMap = false;
  double focalLengthMm = 8300.0;
  double sourceJitterMm = 0.3;
  double offAxisXArcmin = 0.0;
  double offAxisYArcmin = 0.0;
  double mosaicFwhmArcsec = 30.0;
  double crystalliteThicknessUm = 5.0;
  double maxStepMm = 0.0;
  std::string outgoingMosaicModel = "gaussian_plane";
  int onlyRingId = -1;
  int onlyTileId = -1;
};

struct WrlSegment {
  G4ThreeVector start;
  G4ThreeVector end;
  std::string stage;
};

struct LaueVectorDiagnostics {
  bool valid = false;
  std::string model;
  G4ThreeVector planeNormal;
  G4ThreeVector reciprocalVectorInvA;
  G4ThreeVector scatteringQVectorInvA;
  G4ThreeVector latticeGNominalInvA;
  G4ThreeVector latticeGPerturbedInvA;
  G4ThreeVector focusDirection;
  double reciprocalVectorMagInvA = 0.0;
  double reciprocalVectorExpectedMagInvA = 0.0;
  double scatteringQVectorMagInvA = 0.0;
  double latticeGNominalMagInvA = 0.0;
  double latticeGPerturbedMagInvA = 0.0;
  double qMinusGNominalMagInvA = 0.0;
  double qMinusGPerturbedMagInvA = 0.0;
  double relativeBraggResidualNominal = 0.0;
  double relativeBraggResidualPerturbed = 0.0;
  double thetaBRad = 0.0;
  double thetaLocalRad = 0.0;
  double deltaThetaRad = 0.0;
  double mosaicPerturbationRad = 0.0;
  double angleCodeVsRecordedReflectRad = 0.0;
  double elasticError = 0.0;
};

constexpr int kVectorDiagnosticFieldCount = 34;

double Clamp(double value, double lo, double hi) {
  return std::max(lo, std::min(hi, value));
}

double AngleBetweenRad(const G4ThreeVector& a, const G4ThreeVector& b) {
  return std::acos(Clamp(a.unit().dot(b.unit()), -1.0, 1.0));
}

double WaveNumberInvA(double energyKeV) {
  return 2.0 * kPi * energyKeV / kHcKeVA;
}

G4ThreeVector LatticeGAlignedWithQ(
    const G4ThreeVector& planeNormal,
    const G4ThreeVector& scatteringQ,
    double magnitudeInvA) {
  G4ThreeVector g = magnitudeInvA * planeNormal.unit();
  if (g.dot(scatteringQ) < 0.0) g = -g;
  return g;
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
  while (std::getline(ss, cell, ',')) {
    cells.push_back(Trim(cell));
  }
  return cells;
}

std::string ReadString(const std::map<std::string, std::string>& row, const std::string& key) {
  const auto it = row.find(key);
  if (it == row.end() || it->second.empty()) {
    throw std::runtime_error("missing CSV column: " + key);
  }
  return it->second;
}

double ReadDouble(const std::map<std::string, std::string>& row, const std::string& key) {
  return std::stod(ReadString(row, key));
}

int ReadInt(const std::map<std::string, std::string>& row, const std::string& key) {
  return std::stoi(ReadString(row, key));
}

double ReadOptionalDouble(const std::map<std::string, std::string>& row, const std::string& key, double fallback) {
  const auto it = row.find(key);
  if (it == row.end() || it->second.empty()) return fallback;
  return std::stod(it->second);
}

std::string ReadOptionalString(const std::map<std::string, std::string>& row, const std::string& key, const std::string& fallback) {
  const auto it = row.find(key);
  if (it == row.end() || it->second.empty()) return fallback;
  return it->second;
}

struct RockingCurvePoint {
  double deltaThetaRad = 0.0;
  double reflectivity = 0.0;
  double transmittivity = 1.0;
  double absorption = 0.0;
};

struct RockingCurveTable {
  bool enabled = false;
  std::string path;
  std::vector<RockingCurvePoint> points;
};

RockingCurveTable LoadRockingCurveTable(const std::string& path) {
  RockingCurveTable table;
  if (path.empty()) return table;
  std::ifstream input(path.c_str());
  if (!input) throw std::runtime_error("failed to open rocking curve CSV: " + path);
  std::string line;
  if (!std::getline(input, line)) throw std::runtime_error("empty rocking curve CSV: " + path);
  const std::vector<std::string> headers = SplitCsvLine(line);
  while (std::getline(input, line)) {
    if (Trim(line).empty()) continue;
    const std::vector<std::string> cells = SplitCsvLine(line);
    std::map<std::string, std::string> row;
    for (std::size_t i = 0; i < headers.size() && i < cells.size(); ++i) row[headers[i]] = cells[i];
    RockingCurvePoint point;
    point.deltaThetaRad = ReadDouble(row, "delta_theta_rad");
    point.reflectivity = ReadDouble(row, "reflectivity");
    point.absorption = ReadOptionalDouble(row, "absorption", 0.0);
    point.transmittivity = ReadOptionalDouble(row, "transmittivity", std::max(0.0, 1.0 - point.reflectivity - point.absorption));
    point.reflectivity = Clamp(point.reflectivity, 0.0, 0.999999999);
    point.absorption = Clamp(point.absorption, 0.0, 1.0);
    point.transmittivity = Clamp(point.transmittivity, 0.0, 1.0);
    table.points.push_back(point);
  }
  if (table.points.size() < 2) throw std::runtime_error("rocking curve CSV needs at least two rows: " + path);
  std::sort(table.points.begin(), table.points.end(), [](const RockingCurvePoint& a, const RockingCurvePoint& b) {
    return a.deltaThetaRad < b.deltaThetaRad;
  });
  table.enabled = true;
  table.path = path;
  return table;
}

RockingCurvePoint InterpolateRockingCurve(const RockingCurveTable& table, double deltaThetaRad) {
  if (!table.enabled || table.points.empty()) throw std::runtime_error("rocking curve table is not enabled");
  if (deltaThetaRad <= table.points.front().deltaThetaRad) return table.points.front();
  if (deltaThetaRad >= table.points.back().deltaThetaRad) return table.points.back();
  auto upper = std::lower_bound(
      table.points.begin(),
      table.points.end(),
      deltaThetaRad,
      [](const RockingCurvePoint& point, double value) { return point.deltaThetaRad < value; });
  if (upper == table.points.begin()) return *upper;
  const auto lower = upper - 1;
  const double span = upper->deltaThetaRad - lower->deltaThetaRad;
  const double f = span != 0.0 ? (deltaThetaRad - lower->deltaThetaRad) / span : 0.0;
  RockingCurvePoint out;
  out.deltaThetaRad = deltaThetaRad;
  out.reflectivity = lower->reflectivity + f * (upper->reflectivity - lower->reflectivity);
  out.transmittivity = lower->transmittivity + f * (upper->transmittivity - lower->transmittivity);
  out.absorption = lower->absorption + f * (upper->absorption - lower->absorption);
  return out;
}

struct RockingCurveLibrary {
  RockingCurveTable singleTable;
  std::map<int, RockingCurveTable> byRingId;
  std::string mapPath;

  bool HasAny() const { return singleTable.enabled || !byRingId.empty(); }
  bool UsesMap() const { return !byRingId.empty(); }

  const RockingCurveTable* FindForRing(int ringId) const {
    const auto it = byRingId.find(ringId);
    if (it != byRingId.end()) return &it->second;
    if (singleTable.enabled) return &singleTable;
    return 0;
  }

  std::vector<int> CoveredRingIds() const {
    std::vector<int> ids;
    for (const auto& entry : byRingId) ids.push_back(entry.first);
    return ids;
  }
};

bool IsAbsolutePath(const std::string& path) {
  return !path.empty() && path[0] == '/';
}

std::string DirectoryName(const std::string& path) {
  const std::size_t pos = path.find_last_of('/');
  if (pos == std::string::npos) return ".";
  if (pos == 0) return "/";
  return path.substr(0, pos);
}

std::string ResolveRelativeCsvPath(const std::string& baseCsv, const std::string& path) {
  if (path.empty() || IsAbsolutePath(path)) return path;
  return DirectoryName(baseCsv) + "/" + path;
}

std::string CurvePathFromMapRow(const std::map<std::string, std::string>& row) {
  std::string path = ReadOptionalString(row, "curve_csv", "");
  if (!path.empty()) return path;
  path = ReadOptionalString(row, "rocking_curve_csv", "");
  if (!path.empty()) return path;
  path = ReadOptionalString(row, "path", "");
  if (!path.empty()) return path;
  throw std::runtime_error("rocking-curve map CSV requires curve_csv, rocking_curve_csv, or path column");
}

RockingCurveLibrary LoadRockingCurveLibrary(const Options& opt) {
  if (!opt.rockingCurvePath.empty() && !opt.rockingCurveMapPath.empty()) {
    throw std::runtime_error("--rocking-curve-csv and --rocking-curve-map are mutually exclusive");
  }
  RockingCurveLibrary library;
  library.singleTable = LoadRockingCurveTable(opt.rockingCurvePath);
  if (opt.rockingCurveMapPath.empty()) return library;

  std::ifstream input(opt.rockingCurveMapPath.c_str());
  if (!input) throw std::runtime_error("failed to open rocking-curve map CSV: " + opt.rockingCurveMapPath);
  std::string line;
  if (!std::getline(input, line)) throw std::runtime_error("empty rocking-curve map CSV: " + opt.rockingCurveMapPath);
  const std::vector<std::string> headers = SplitCsvLine(line);
  while (std::getline(input, line)) {
    if (Trim(line).empty()) continue;
    const std::vector<std::string> cells = SplitCsvLine(line);
    std::map<std::string, std::string> row;
    for (std::size_t i = 0; i < headers.size() && i < cells.size(); ++i) row[headers[i]] = cells[i];
    const int ringId = ReadInt(row, "ring_id");
    const std::string curvePath = ResolveRelativeCsvPath(opt.rockingCurveMapPath, CurvePathFromMapRow(row));
    if (library.byRingId.find(ringId) != library.byRingId.end()) {
      throw std::runtime_error("duplicate ring_id in rocking-curve map CSV");
    }
    library.byRingId[ringId] = LoadRockingCurveTable(curvePath);
  }
  if (library.byRingId.empty()) throw std::runtime_error("rocking-curve map CSV has no data rows: " + opt.rockingCurveMapPath);
  library.mapPath = opt.rockingCurveMapPath;
  return library;
}

std::string RockingCurveBackendName(const RockingCurveLibrary& library) {
  if (library.UsesMap()) return "external_per_ring_csv_map";
  if (library.singleTable.enabled) return "external_csv";
  return "online_darwin_hamilton";
}

std::string RockingCurveSourceForRing(const RockingCurveLibrary& library, int ringId) {
  if (library.byRingId.find(ringId) != library.byRingId.end()) return "external_rocking_curve_map_csv";
  if (library.singleTable.enabled) return "external_rocking_curve_csv";
  return "online_darwin_hamilton_virtual_crystallite_ge111";
}

std::string RockingCurvePathForRing(const RockingCurveLibrary& library, int ringId) {
  const auto it = library.byRingId.find(ringId);
  if (it != library.byRingId.end()) return it->second.path;
  if (library.singleTable.enabled) return library.singleTable.path;
  return "";
}

double BraggAngleRad(double energyKeV, double dSpacingA) {
  const double arg = (kHcKeVA / energyKeV) / (2.0 * dSpacingA);
  if (arg <= 0.0 || arg >= 1.0) {
    throw std::runtime_error("invalid Bragg argument");
  }
  return std::asin(arg);
}

double FwhmArcsecToSigmaRad(double fwhmArcsec) {
  return (fwhmArcsec / 3600.0) * kPi / 180.0 / 2.355;
}

double MosaicWeightRadInv(double deltaThetaRad, double mosaicFwhmArcsec) {
  const double omega = mosaicFwhmArcsec / 3600.0 * kPi / 180.0;
  if (omega <= 0.0) throw std::runtime_error("mosaic FWHM must be positive");
  return 2.0 * std::sqrt(std::log(2.0) / kPi) / omega *
         std::exp(-std::log(2.0) * std::pow(deltaThetaRad / (0.5 * omega), 2.0));
}

double DarwinFApprox(double aParam) {
  if (std::fabs(aParam) < 1.0e-10) return 1.0;
  // Guan-style online model: keep the crystallite finite-thickness correction
  // local to the model. For the current 5 um Ge(111), a is small and this
  // Bessel-series approximation differs negligibly from numeric quadrature.
  return 1.0 - 0.5 * aParam * aParam + (aParam * aParam * aParam * aParam) / 12.0;
}

double Ge111ExtinctionLengthCm(double energyKeV) {
  // Direct C++ online backend, not a read of the 01 pAbs/pDiff/pTrans table.
  // The normalization is anchored to the same Ge(111) dynamical-diffraction
  // constants used in the local validation record; energy scaling follows the
  // lambda dependence of the extinction length near 480-550 keV.
  constexpr double kLambda0At511Cm = 539.7909510452002e-4;
  return kLambda0At511Cm * (energyKeV / 511.0);
}

double GeMassAttenuationMuCmInv(double energyKeV) {
  // Compact Ge attenuation fit over 480-550 keV, derived from the local
  // xraydb-backed material_mu validation values. It avoids using the 01
  // probability table at runtime while preserving the correct attenuation scale.
  constexpr double kMuAt511CmInv = 0.4321058247470657;
  return kMuAt511CmInv * std::pow(511.0 / energyKeV, 0.55);
}

double DarwinQGe111CmInv(
    double energyKeV,
    const RingSpec& ring,
    double crystalliteThicknessUm) {
  const double thetaB = BraggAngleRad(energyKeV, ring.dSpacingA);
  const double dCm = ring.dSpacingA * 1.0e-8;
  const double lambda0Cm = Ge111ExtinctionLengthCm(energyKeV);
  const double t0Cm = crystalliteThicknessUm * 1.0e-4;
  const double aParam = kPi * t0Cm / (lambda0Cm * std::cos(thetaB));
  return kPi * kPi * dCm / (lambda0Cm * lambda0Cm * std::cos(thetaB)) * DarwinFApprox(aParam);
}

optics::LaueEfficiencyRow OnlineDarwinMosaicProbabilities(
    const RingSpec& ring,
    double deltaThetaRad,
    const Options& opt) {
  optics::LaueEfficiencyRow row;
  row.energyKeV = ring.designEnergyKeV;
  row.thetaBRad = BraggAngleRad(ring.designEnergyKeV, ring.dSpacingA);
  row.deltaThetaRad = deltaThetaRad;
  row.material = ring.material;
  row.h = ring.h;
  row.k = ring.k;
  row.l = ring.l;
  row.mosaicFwhmArcmin = opt.mosaicFwhmArcsec / 60.0;
  row.thicknessMm = ring.thicknessMm;
  const double thicknessCm = ring.thicknessMm / 10.0;
  const double qCmInv = DarwinQGe111CmInv(ring.designEnergyKeV, ring, opt.crystalliteThicknessUm);
  const double wRadInv = MosaicWeightRadInv(deltaThetaRad, opt.mosaicFwhmArcsec);
  const double sigmaCmInv = qCmInv * wRadInv;
  const double muCmInv = GeMassAttenuationMuCmInv(ring.designEnergyKeV);
  const double absorptionTransmission = std::exp(-muCmInv * thicknessCm / std::cos(row.thetaBRad));
  const double diffractionEfficiency = 0.5 * (1.0 - std::exp(-2.0 * sigmaCmInv * thicknessCm));
  row.pDiff = diffractionEfficiency * absorptionTransmission;
  row.pAbs = 1.0 - absorptionTransmission;
  row.pTrans = std::max(0.0, absorptionTransmission - row.pDiff);
  const double sum = row.pDiff + row.pAbs + row.pTrans;
  if (sum > 0.0) {
    row.pDiff /= sum;
    row.pAbs /= sum;
    row.pTrans /= sum;
  }
  row.source = "online_darwin_hamilton_virtual_crystallite_ge111";
  return row;
}

optics::LaueEfficiencyRow BFullBackendProbabilities(
    const RingSpec& ring,
    double deltaThetaRad,
    const Options& opt,
    const RockingCurveLibrary& rockingCurves) {
  optics::LaueEfficiencyRow row = OnlineDarwinMosaicProbabilities(ring, deltaThetaRad, opt);
  const RockingCurveTable* rockingCurve = rockingCurves.FindForRing(ring.ringId);
  if (rockingCurve == 0) return row;
  const RockingCurvePoint point = InterpolateRockingCurve(*rockingCurve, deltaThetaRad);
  row.pDiff = Clamp(point.reflectivity, 0.0, 0.999999999);
  row.pAbs = Clamp(point.absorption, 0.0, 1.0);
  row.pTrans = Clamp(point.transmittivity, 0.0, 1.0);
  row.source = RockingCurveSourceForRing(rockingCurves, ring.ringId);
  return row;
}

double AnalyticReferenceFocalDiffraction(
    const RingSpec& ring,
    const Options& opt,
    const RockingCurveLibrary& rockingCurves) {
  // Absorption-included diffracted fraction at the design Bragg peak (dtheta=0).
  // This is the validated mosaic-Laue reference the emergent EM-competing B-FULL
  // focal-plane diffraction fraction must reproduce: either the external
  // XOP/CRYSTAL curve reflectivity, or the Darwin-Hamilton closed form
  // 0.5(1-exp(-2 sigma t)) exp(-mu t / cos theta_B).
  const RockingCurveTable* rockingCurve = rockingCurves.FindForRing(ring.ringId);
  if (rockingCurve != 0) {
    return Clamp(InterpolateRockingCurve(*rockingCurve, 0.0).reflectivity, 0.0, 1.0);
  }
  return Clamp(OnlineDarwinMosaicProbabilities(ring, 0.0, opt).pDiff, 0.0, 1.0);
}

G4ThreeVector ReflectAcrossPlane(const G4ThreeVector& inDir, const G4ThreeVector& planeNormal) {
  const G4ThreeVector k = inDir.unit();
  const G4ThreeVector n = planeNormal.unit();
  return (k - 2.0 * k.dot(n) * n).unit();
}

G4ThreeVector DesignFocusPoint(const Options& opt) {
  return G4ThreeVector(0.0, 0.0, opt.focalLengthMm * mm);
}

G4ThreeVector TileCenter(const RingSpec& ring, int tileId) {
  const double phi = 2.0 * kPi * static_cast<double>(tileId) / static_cast<double>(ring.nTiles);
  return G4ThreeVector(ring.radiusMm * std::cos(phi) * mm, ring.radiusMm * std::sin(phi) * mm, ring.zOffsetMm * mm);
}

G4ThreeVector FixedTilePlaneNormal(const RingSpec& ring, int tileId, const Options& opt) {
  const G4ThreeVector center = TileCenter(ring, tileId);
  const G4ThreeVector nominalInDir(0.0, 0.0, 1.0);
  const G4ThreeVector nominalOutDir = (DesignFocusPoint(opt) - center).unit();
  return (nominalInDir - nominalOutDir).unit();
}

struct BFullInteractionScale {
  double thetaBRad = 0.0;
  double thetaLocalRad = 0.0;
  double deltaThetaRad = 0.0;
  double qCmInv = 0.0;
  double wRadInv = 0.0;
  double sigmaCmInv = 0.0;
  double diffractionOnlyProbability = 0.0;
  double pathLengthCm = 0.0;
  double meanFreePathCm = 0.0;
};

BFullInteractionScale BFullEquivalentDiffractionScale(
    const RingSpec& ring,
    double deltaThetaRad,
    const G4ThreeVector& inDir,
    const Options& opt,
    const RockingCurveLibrary& rockingCurves) {
  BFullInteractionScale scale;
  scale.thetaBRad = BraggAngleRad(ring.designEnergyKeV, ring.dSpacingA);
  scale.thetaLocalRad = scale.thetaBRad + deltaThetaRad;
  scale.deltaThetaRad = deltaThetaRad;
  scale.qCmInv = DarwinQGe111CmInv(ring.designEnergyKeV, ring, opt.crystalliteThicknessUm);
  scale.wRadInv = MosaicWeightRadInv(deltaThetaRad, opt.mosaicFwhmArcsec);
  scale.sigmaCmInv = scale.qCmInv * scale.wRadInv;
  const double thicknessCm = ring.thicknessMm / 10.0;
  const double zProjection = std::max(1.0e-6, std::fabs(inDir.unit().z()));
  scale.pathLengthCm = thicknessCm / zProjection;
  const RockingCurveTable* rockingCurve = rockingCurves.FindForRing(ring.ringId);
  if (rockingCurve != 0) {
    // The external XOP/CRYSTAL rocking-curve reflectivity R(dtheta) is the
    // diffracted fraction with photo/Compton absorption already folded in
    // (R = R0 * exp(-mu t / cos theta_B)). Standard Geant4 EM independently
    // attenuates the same beam, so feeding R straight to the diffraction MFP
    // double-counts absorption. Recover the absorption-free diffraction
    // efficiency R0 = R / (1 - A) and let EM apply absorption exactly once.
    const RockingCurvePoint point = InterpolateRockingCurve(*rockingCurve, deltaThetaRad);
    const double absorptionSurvival = std::max(1.0e-6, 1.0 - point.absorption);
    scale.diffractionOnlyProbability = point.reflectivity / absorptionSurvival;
  } else {
    scale.diffractionOnlyProbability = 0.5 * (1.0 - std::exp(-2.0 * scale.sigmaCmInv * thicknessCm));
  }
  scale.diffractionOnlyProbability = Clamp(scale.diffractionOnlyProbability, 0.0, 0.999999999);
  if (scale.diffractionOnlyProbability > 1.0e-12) {
    scale.meanFreePathCm = -scale.pathLengthCm / std::log(1.0 - scale.diffractionOnlyProbability);
  } else {
    scale.meanFreePathCm = DBL_MAX;
  }
  return scale;
}

LaueVectorDiagnostics MakeLaueVectorDiagnostics(
    const std::string& model,
    double energyKeV,
    const G4ThreeVector& inDir,
    const G4ThreeVector& outDir,
    const G4ThreeVector& nominalPlaneNormal,
    const G4ThreeVector& planeNormal,
    const G4ThreeVector& focusDirection,
    double dSpacingA,
    double thetaBRad,
    double thetaLocalRad,
    double deltaThetaRad,
    double mosaicPerturbationRad) {
  LaueVectorDiagnostics diag;
  diag.valid = true;
  diag.model = model;
  diag.planeNormal = planeNormal.unit();
  diag.focusDirection = focusDirection.unit();
  const double kInvA = WaveNumberInvA(energyKeV);
  diag.reciprocalVectorInvA = kInvA * (outDir.unit() - inDir.unit());
  diag.reciprocalVectorMagInvA = diag.reciprocalVectorInvA.mag();
  diag.reciprocalVectorExpectedMagInvA = 2.0 * kInvA * std::sin(thetaBRad);
  diag.scatteringQVectorInvA = diag.reciprocalVectorInvA;
  diag.scatteringQVectorMagInvA = diag.reciprocalVectorMagInvA;
  const double latticeGMagInvA = 2.0 * kPi / dSpacingA;
  diag.latticeGNominalInvA = LatticeGAlignedWithQ(nominalPlaneNormal, diag.scatteringQVectorInvA, latticeGMagInvA);
  diag.latticeGPerturbedInvA = LatticeGAlignedWithQ(planeNormal, diag.scatteringQVectorInvA, latticeGMagInvA);
  diag.latticeGNominalMagInvA = diag.latticeGNominalInvA.mag();
  diag.latticeGPerturbedMagInvA = diag.latticeGPerturbedInvA.mag();
  diag.qMinusGNominalMagInvA = (diag.scatteringQVectorInvA - diag.latticeGNominalInvA).mag();
  diag.qMinusGPerturbedMagInvA = (diag.scatteringQVectorInvA - diag.latticeGPerturbedInvA).mag();
  diag.relativeBraggResidualNominal =
      diag.latticeGNominalMagInvA > 0.0 ? diag.qMinusGNominalMagInvA / diag.latticeGNominalMagInvA : 0.0;
  diag.relativeBraggResidualPerturbed =
      diag.latticeGPerturbedMagInvA > 0.0 ? diag.qMinusGPerturbedMagInvA / diag.latticeGPerturbedMagInvA : 0.0;
  diag.thetaBRad = thetaBRad;
  diag.thetaLocalRad = thetaLocalRad;
  diag.deltaThetaRad = deltaThetaRad;
  diag.mosaicPerturbationRad = mosaicPerturbationRad;
  diag.angleCodeVsRecordedReflectRad = AngleBetweenRad(outDir, ReflectAcrossPlane(inDir, diag.planeNormal));
  diag.elasticError = std::fabs(outDir.unit().mag() - inDir.unit().mag());
  return diag;
}

G4ThreeVector PerturbDirection(const G4ThreeVector& direction, double sigmaRad) {
  const G4ThreeVector base = direction.unit();
  if (sigmaRad <= 0.0) return base;
  G4ThreeVector e1 = base.cross(G4ThreeVector(0.0, 0.0, 1.0));
  if (e1.mag2() < 1.0e-24) e1 = base.cross(G4ThreeVector(1.0, 0.0, 0.0));
  e1 = e1.unit();
  const G4ThreeVector e2 = base.cross(e1).unit();
  return (base + G4RandGauss::shoot(0.0, sigmaRad) * e1 + G4RandGauss::shoot(0.0, sigmaRad) * e2).unit();
}

bool NameContains(const G4VPhysicalVolume* volume, const G4String& token) {
  if (volume == 0) return false;
  if (volume->GetName().find(token) != G4String::npos) return true;
  const G4LogicalVolume* logical = volume->GetLogicalVolume();
  return logical != 0 && logical->GetName().find(token) != G4String::npos;
}

Options ParseOptions(int argc, char** argv) {
  Options opt;
  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    auto requireValue = [&](const std::string& name) -> const char* {
      if (i + 1 >= argc) throw std::runtime_error("missing value for " + name);
      return argv[++i];
    };
    if (arg == "--n") {
      opt.nEvents = std::atoi(requireValue(arg));
    } else if (arg == "--out") {
      opt.outDir = requireValue(arg);
    } else if (arg == "--seed") {
      opt.seed = std::atol(requireValue(arg));
    } else if (arg == "--efficiency-table") {
      opt.efficiencyTablePath = requireValue(arg);
    } else if (arg == "--ring-config") {
      opt.ringConfigPath = requireValue(arg);
    } else if (arg == "--rocking-curve-csv") {
      opt.rockingCurvePath = requireValue(arg);
    } else if (arg == "--rocking-curve-map") {
      opt.rockingCurveMapPath = requireValue(arg);
    } else if (arg == "--require-rocking-curve-map") {
      opt.requireRockingCurveMap = true;
    } else if (arg == "--focal-mm") {
      opt.focalLengthMm = std::atof(requireValue(arg));
    } else if (arg == "--source-jitter-mm") {
      opt.sourceJitterMm = std::atof(requireValue(arg));
    } else if (arg == "--offaxis-x-arcmin") {
      opt.offAxisXArcmin = std::atof(requireValue(arg));
    } else if (arg == "--offaxis-y-arcmin") {
      opt.offAxisYArcmin = std::atof(requireValue(arg));
    } else if (arg == "--mosaic-fwhm-arcsec") {
      opt.mosaicFwhmArcsec = std::atof(requireValue(arg));
    } else if (arg == "--crystallite-um") {
      opt.crystalliteThicknessUm = std::atof(requireValue(arg));
    } else if (arg == "--max-step-mm") {
      opt.maxStepMm = std::atof(requireValue(arg));
    } else if (arg == "--outgoing-mosaic-model") {
      opt.outgoingMosaicModel = requireValue(arg);
    } else if (arg == "--only-ring-id") {
      opt.onlyRingId = std::atoi(requireValue(arg));
    } else if (arg == "--only-tile-id") {
      opt.onlyTileId = std::atoi(requireValue(arg));
    } else if (arg == "--help" || arg == "-h") {
      std::cout << "Usage: " << argv[0] << " --n N --ring-config rings.csv --efficiency-table table.csv --out DIR"
                << " [--offaxis-x-arcmin X] [--offaxis-y-arcmin Y]"
                << " [--mosaic-fwhm-arcsec FWHM] [--crystallite-um UM]"
                << " [--max-step-mm MM]"
                << " [--outgoing-mosaic-model gaussian_plane|gaussian_outgoing|ideal_plane]"
                << " [--only-ring-id ID] [--only-tile-id ID]"
                << " [--rocking-curve-csv CSV]"
                << " [--rocking-curve-map CSV] [--require-rocking-curve-map]\n";
      std::exit(0);
    } else {
      throw std::runtime_error("unknown option: " + arg);
    }
  }
  if (opt.nEvents <= 0 || opt.focalLengthMm <= 0.0 || opt.sourceJitterMm < 0.0 ||
      opt.mosaicFwhmArcsec <= 0.0 || opt.crystalliteThicknessUm <= 0.0 || opt.maxStepMm < 0.0) {
    throw std::runtime_error("invalid multiring demo options");
  }
  if (opt.outgoingMosaicModel != "gaussian_plane" &&
      opt.outgoingMosaicModel != "gaussian_outgoing" &&
      opt.outgoingMosaicModel != "ideal_plane") {
    throw std::runtime_error(
        "--outgoing-mosaic-model must be gaussian_plane, gaussian_outgoing, or ideal_plane");
  }
  if (opt.onlyTileId >= 0 && opt.onlyRingId < 0) {
    throw std::runtime_error("--only-tile-id requires --only-ring-id");
  }
  if (!opt.rockingCurvePath.empty() && !opt.rockingCurveMapPath.empty()) {
    throw std::runtime_error("--rocking-curve-csv and --rocking-curve-map are mutually exclusive");
  }
  if (opt.requireRockingCurveMap && opt.rockingCurveMapPath.empty()) {
    throw std::runtime_error("--require-rocking-curve-map requires --rocking-curve-map");
  }
  return opt;
}

std::vector<RingSpec> LoadRingConfig(const std::string& path, double focalLengthMm) {
  std::ifstream input(path.c_str());
  if (!input) throw std::runtime_error("failed to open Laue ring config: " + path);
  std::string line;
  if (!std::getline(input, line)) throw std::runtime_error("empty Laue ring config: " + path);
  const std::vector<std::string> headers = SplitCsvLine(line);
  std::vector<RingSpec> rings;
  while (std::getline(input, line)) {
    if (Trim(line).empty()) continue;
    const std::vector<std::string> cells = SplitCsvLine(line);
    std::map<std::string, std::string> row;
    for (std::size_t i = 0; i < headers.size() && i < cells.size(); ++i) row[headers[i]] = cells[i];
    RingSpec ring;
    ring.ringId = ReadInt(row, "ring_id");
    ring.designEnergyKeV = ReadDouble(row, "design_energy_keV");
    ring.radiusMm = ReadDouble(row, "radius_mm");
    ring.nTiles = ReadInt(row, "n_tiles");
    ring.material = ReadString(row, "material");
    ring.h = ReadInt(row, "h");
    ring.k = ReadInt(row, "k");
    ring.l = ReadInt(row, "l");
    ring.dSpacingA = ReadDouble(row, "d_spacing_A");
    ring.tileSizeMm = ReadDouble(row, "tile_size_mm");
    ring.thicknessMm = ReadDouble(row, "thickness_mm");
    ring.zOffsetMm = ReadOptionalDouble(row, "z_offset_mm", 0.0);
    const double axialFocalLengthMm = focalLengthMm - ring.zOffsetMm;
    if (axialFocalLengthMm <= 0.0) {
      std::ostringstream msg;
      msg << "ring " << ring.ringId << " z_offset_mm " << ring.zOffsetMm
          << " leaves non-positive axial distance to focal plane " << focalLengthMm << " mm";
      throw std::runtime_error(msg.str());
    }
    const double expectedRadius = axialFocalLengthMm * std::tan(2.0 * BraggAngleRad(ring.designEnergyKeV, ring.dSpacingA));
    if (std::fabs(expectedRadius - ring.radiusMm) > 0.2) {
      std::ostringstream msg;
      msg << "ring " << ring.ringId << " radius " << ring.radiusMm
          << " mm is inconsistent with Bragg radius " << expectedRadius << " mm";
      throw std::runtime_error(msg.str());
    }
    rings.push_back(ring);
  }
  if (rings.empty()) throw std::runtime_error("Laue ring config has no data rows: " + path);
  std::sort(rings.begin(), rings.end(), [](const RingSpec& a, const RingSpec& b) { return a.ringId < b.ringId; });
  return rings;
}

void ValidateRockingCurveCoverage(
    const std::vector<RingSpec>& rings,
    const Options& opt,
    const RockingCurveLibrary& rockingCurves) {
  if (!opt.requireRockingCurveMap) return;
  std::vector<int> missing;
  int selected = 0;
  for (const auto& ring : rings) {
    if (opt.onlyRingId >= 0 && ring.ringId != opt.onlyRingId) continue;
    ++selected;
    if (rockingCurves.byRingId.find(ring.ringId) == rockingCurves.byRingId.end()) missing.push_back(ring.ringId);
  }
  if (selected == 0) throw std::runtime_error("--only-ring-id does not match ring config");
  if (!missing.empty()) {
    std::ostringstream msg;
    msg << "rocking-curve map missing required ring_id";
    for (int ringId : missing) msg << " " << ringId;
    throw std::runtime_error(msg.str());
  }
}

const RingSpec& RingFromCopyNo(const std::vector<RingSpec>& rings, int copyNo) {
  const int ringId = copyNo / kCopyStride;
  for (const auto& ring : rings) {
    if (ring.ringId == ringId) return ring;
  }
  throw std::runtime_error("invalid Laue ring copy number");
}

int TotalTiles(const std::vector<RingSpec>& rings) {
  int total = 0;
  for (const auto& ring : rings) total += ring.nTiles;
  return total;
}

double MaxCrystalThicknessMm(const std::vector<RingSpec>& rings) {
  double thickness = 0.0;
  for (const auto& ring : rings) thickness = std::max(thickness, ring.thicknessMm);
  return thickness;
}

double MinCrystalZMm(const std::vector<RingSpec>& rings) {
  double z = rings.empty() ? 0.0 : rings.front().zOffsetMm;
  for (const auto& ring : rings) z = std::min(z, ring.zOffsetMm);
  return z;
}

double MaxRingOuterRadiusMm(const std::vector<RingSpec>& rings) {
  double radius = 0.0;
  for (const auto& ring : rings) radius = std::max(radius, ring.radiusMm + 0.5 * ring.tileSizeMm);
  return radius;
}

double WorldHalfXYMm(const std::vector<RingSpec>& rings) {
  return std::max(160.0, MaxRingOuterRadiusMm(rings) + 20.0);
}

double WorldHalfZMm(const std::vector<RingSpec>& rings, double focalLengthMm) {
  return std::max(8500.0, focalLengthMm + MaxCrystalThicknessMm(rings) + 100.0);
}

std::pair<const RingSpec*, int> RingAndTileForEvent(const std::vector<RingSpec>& rings, int eventId) {
  int idx = eventId % TotalTiles(rings);
  for (const auto& ring : rings) {
    if (idx < ring.nTiles) return {&ring, idx};
    idx -= ring.nTiles;
  }
  return {&rings.back(), rings.back().nTiles - 1};
}

class MultiRingRunState {
 public:
  MultiRingRunState(const Options& opt, const std::vector<RingSpec>& rings, const RockingCurveLibrary& rockingCurves)
      : opt_(opt), rings_(rings), rockingCurves_(rockingCurves), ringStats_(rings.size()) {
    EnsureDirectory(opt_.outDir);
    phase_.open((opt_.outDir + "/phase_space.csv").c_str());
    transmitted_.open((opt_.outDir + "/transmitted_space.csv").c_str());
    history_.open((opt_.outDir + "/optics_history.csv").c_str());
    focal_.open((opt_.outDir + "/focal_crossings.csv").c_str());
    if (!phase_ || !transmitted_ || !history_ || !focal_) {
      throw std::runtime_error("cannot open multiring Laue output files in: " + opt_.outDir);
    }
    phase_ << "event_id,E_keV,x_mm,y_mm,z_mm,ux,uy,uz,weight,source_tag,particle_name,pdg_encoding,track_id,parent_id\n";
    transmitted_ << "event_id,E_keV,x_mm,y_mm,z_mm,ux,uy,uz,weight,source_tag,particle_name,pdg_encoding,track_id,parent_id\n";
    focal_ << "event_id,track_id,parent_id,E_keV,x_mm,y_mm,z_mm,ux,uy,uz,source_tag,creator_process\n";
    history_ << "event_id,track_id,optics_kind,stage,ring_id,tile_id,surface_id,E_keV,"
             << "x_mm,y_mm,z_mm,ux_in,uy_in,uz_in,ux_out,uy_out,uz_out,"
             << "grazing_angle_rad,p_reflect,p_absorb,p_transmit,n_bounce,weight,"
             << "vector_diagnostic_model,plane_normal_x,plane_normal_y,plane_normal_z,"
             << "reciprocal_vector_x_invA,reciprocal_vector_y_invA,reciprocal_vector_z_invA,"
             << "reciprocal_vector_mag_invA,reciprocal_vector_expected_mag_invA,"
             << "scattering_q_vector_x_invA,scattering_q_vector_y_invA,scattering_q_vector_z_invA,"
             << "scattering_q_vector_mag_invA,"
             << "lattice_G_nominal_x_invA,lattice_G_nominal_y_invA,lattice_G_nominal_z_invA,"
             << "lattice_G_nominal_mag_invA,"
             << "lattice_G_perturbed_x_invA,lattice_G_perturbed_y_invA,lattice_G_perturbed_z_invA,"
             << "lattice_G_perturbed_mag_invA,"
             << "q_minus_G_nominal_mag_invA,q_minus_G_perturbed_mag_invA,"
             << "relative_bragg_residual_nominal,relative_bragg_residual_perturbed,"
             << "focus_direction_x,focus_direction_y,focus_direction_z,"
             << "theta_B_rad,theta_local_rad,delta_theta_model_rad,mosaic_perturbation_rad,"
             << "angle_code_vs_recorded_reflect_rad,elastic_error\n";
  }

  struct RingStats {
    long n = 0;
    long diff = 0;
    long abs = 0;
    long trans = 0;
    double sumPDiff = 0.0;
    double sumPAbs = 0.0;
    double sumPTrans = 0.0;
  };

  void Record(
      int eventId,
      int trackId,
      const std::string& stage,
      const RingSpec& ring,
      int tileId,
      const G4ThreeVector& pos,
      const G4ThreeVector& inDir,
      const G4ThreeVector& outDir,
      const optics::LaueEfficiencyRow& probs,
      double deltaThetaRad,
      const LaueVectorDiagnostics& diagnostics = LaueVectorDiagnostics()) {
    RingStats& stats = ringStats_.at(static_cast<std::size_t>(ring.ringId));
    ++stats.n;
    stats.sumPDiff += probs.pDiff;
    stats.sumPAbs += probs.pAbs;
    stats.sumPTrans += probs.pTrans;
    history_ << eventId << "," << trackId << ",LAUE," << stage << "," << ring.ringId << "," << tileId
             << ",LaueCrystalMultiRing," << ring.designEnergyKeV << "," << std::setprecision(10)
             << pos.x() / mm << "," << pos.y() / mm << "," << pos.z() / mm << ","
             << inDir.x() << "," << inDir.y() << "," << inDir.z() << ","
             << outDir.x() << "," << outDir.y() << "," << outDir.z() << ","
             << deltaThetaRad << "," << probs.pDiff << "," << probs.pAbs << ","
             << probs.pTrans << ",1,1";
    WriteVectorDiagnostics(diagnostics);
    history_ << "\n";
    AddWrl(pos - 60.0 * mm * inDir, pos, "INCIDENT");

    if (stage == "DIFFRACT") {
      ++nDiff_;
      ++stats.diff;
      const G4ThreeVector hit = PlaneHit(pos, outDir);
      detectorHits_.push_back(hit);
      phase_ << eventId << "," << ring.designEnergyKeV << "," << std::setprecision(10)
             << hit.x() / mm << "," << hit.y() / mm << "," << opt_.focalLengthMm
             << "," << outDir.x() << "," << outDir.y() << "," << outDir.z()
             << ",1.0,geant4_laue_bfull_projected_diffraction,gamma,22," << trackId << ",0\n";
      AddWrl(pos, hit, stage);
    } else if (stage == "ABSORB") {
      ++nAbs_;
      ++stats.abs;
      AddWrl(pos, pos + 15.0 * mm * inDir, stage);
    } else {
      ++nTrans_;
      ++stats.trans;
      const G4ThreeVector hit = PlaneHit(pos, inDir);
      transmitted_ << eventId << "," << ring.designEnergyKeV << "," << std::setprecision(10)
                   << hit.x() / mm << "," << hit.y() / mm << "," << opt_.focalLengthMm
                   << "," << inDir.x() << "," << inDir.y() << "," << inDir.z()
                   << ",1.0,geant4_laue_bfull_projected_transmitted,gamma,22," << trackId << ",0\n";
      AddWrl(pos, hit, stage);
    }
  }

  void RecordFocalCrossing(const G4Track& track, const G4ThreeVector& hit, const G4ThreeVector& dir) {
    const G4Event* event = G4RunManager::GetRunManager()->GetCurrentEvent();
    const int eventId = event ? event->GetEventID() : -1;
    const G4VProcess* creator = track.GetCreatorProcess();
    const std::string creatorName = creator ? creator->GetProcessName() : "primary";
    std::string sourceTag = "laue_bfull_other_gamma";
    if (track.GetParentID() == 0) {
      sourceTag = "laue_bfull_primary_or_transmitted";
      ++nPrimaryFocalCrossings_;
      const double offAxisXRad = opt_.offAxisXArcmin / 60.0 * kPi / 180.0;
      const double offAxisYRad = opt_.offAxisYArcmin / 60.0 * kPi / 180.0;
      const G4ThreeVector expectedDirection(std::tan(offAxisXRad), std::tan(offAxisYRad), 1.0);
      bool energyMatchesPrimary = false;
      for (const auto& ring : rings_) {
        if (std::fabs(track.GetKineticEnergy() / keV - ring.designEnergyKeV) <= 1.0e-6) {
          energyMatchesPrimary = true;
          break;
        }
      }
      const bool directionMatchesPrimary = AngleBetweenRad(dir, expectedDirection.unit()) <= 1.0e-9;
      if (energyMatchesPrimary && directionMatchesPrimary) {
        sourceTag = "laue_bfull_uncollided_transmitted";
        ++nUncollidedPrimaryFocalCrossings_;
        uncollidedTransmittedEventIds_.insert(eventId);
      } else {
        sourceTag = "laue_bfull_scattered_primary";
        ++nScatteredPrimaryFocalCrossings_;
      }
      transmitted_ << eventId << "," << track.GetKineticEnergy() / keV << "," << std::setprecision(10)
                   << hit.x() / mm << "," << hit.y() / mm << "," << hit.z() / mm << ","
                   << dir.x() << "," << dir.y() << "," << dir.z()
                   << ",1.0,geant4_laue_bfull_focal_primary_or_transmitted,gamma,22,"
                   << track.GetTrackID() << ",0\n";
    } else if (creatorName == "BFullLaueBraggProcess") {
      sourceTag = "laue_bfull_diffracted";
      ++nLaueFocalCrossings_;
      diffractedEventIds_.insert(eventId);
      focalDetectorHits_.push_back(hit);
    } else {
      ++nOtherFocalCrossings_;
    }
    ++nFocalCrossings_;
    focal_ << eventId << "," << track.GetTrackID() << "," << track.GetParentID()
           << "," << track.GetKineticEnergy() / keV << "," << std::setprecision(10)
           << hit.x() / mm << "," << hit.y() / mm << "," << hit.z() / mm << ","
           << dir.x() << "," << dir.y() << "," << dir.z() << ","
           << sourceTag << "," << creatorName << "\n";
  }

  void RecordCrystalStep(double stepLengthMm) {
    ++nCrystalSteps_;
    sumCrystalStepMm_ += stepLengthMm;
    maxObservedCrystalStepMm_ = std::max(maxObservedCrystalStepMm_, stepLengthMm);
  }

  void WriteOutputs() {
    phase_.flush();
    transmitted_.flush();
    history_.flush();
    focal_.flush();
    WritePerRingSummary();
    WriteWrl(opt_.outDir + "/laue_multiring_scene.wrl");
    std::ofstream summary((opt_.outDir + "/summary.json").c_str());
    const double n = static_cast<double>(opt_.nEvents);
    summary << "{\n";
    summary << "  \"system\": \"geant4_laue_bfull_process\",\n";
    summary << "  \"model\": \"bfull_fixed_tile_orientation_geant4_discrete_competing_laue_mfp_v4\",\n";
    summary << "  \"warning\": \"B-FULL: standard Geant4 EM physics is enabled; the Laue process is a non-forced G4VDiscreteProcess with a finite equivalent diffraction mean free path that competes with the standard EM processes. The tile geometry/lattice-plane evaluation remains application-level code, not a Geant4 toolkit source patch.\",\n";
    summary << "  \"geant4_bottom_code_modified\": false,\n";
    summary << "  \"model_process_split\": true,\n";
    summary << "  \"registered_process\": \"BFullLaueBraggProcess derives from G4VDiscreteProcess and is added to the gamma G4ProcessManager as a non-forced finite-MFP post-step process competing with standard EM\",\n";
    summary << "  \"registered_in_geant4_em_category\": false,\n";
    summary << "  \"geant4_process_base_class\": \"G4VDiscreteProcess\",\n";
    summary << "  \"geant4_builds_on_geant4_11\": true,\n";
    summary << "  \"standard_geant4_em_enabled\": true,\n";
    summary << "  \"uses_external_efficiency_table_for_physics\": false,\n";
    summary << "  \"uses_external_rocking_curve_for_laue_mfp\": " << (rockingCurves_.HasAny() ? "true" : "false") << ",\n";
    summary << "  \"rocking_curve_backend\": \"" << RockingCurveBackendName(rockingCurves_) << "\",\n";
    summary << "  \"rocking_curve_csv\": \"" << opt_.rockingCurvePath << "\",\n";
    summary << "  \"rocking_curve_map_csv\": \"" << opt_.rockingCurveMapPath << "\",\n";
    summary << "  \"rocking_curve_map_required\": " << (opt_.requireRockingCurveMap ? "true" : "false") << ",\n";
    summary << "  \"rocking_curve_map_covered_ring_ids\": [";
    const std::vector<int> coveredRingIds = rockingCurves_.CoveredRingIds();
    for (std::size_t i = 0; i < coveredRingIds.size(); ++i) {
      if (i) summary << ", ";
      summary << coveredRingIds[i];
    }
    summary << "],\n";
    summary << "  \"online_physics_backend\": \"Darwin-Hamilton mosaic formula or external rocking-curve CSV converted to an equivalent finite diffraction mean free path; Geant4 standard EM processes remain enabled\",\n";
    summary << "  \"vector_diagnostics_in_optics_history\": true,\n";
    summary << "  \"plane_normal_diagnostic_model\": \"bfull_fixed_tile_plane_normal_em_competing; outgoing model="
            << opt_.outgoingMosaicModel << "\",\n";
    summary << "  \"mosaic_fwhm_arcsec\": " << opt_.mosaicFwhmArcsec << ",\n";
    summary << "  \"crystallite_thickness_um\": " << opt_.crystalliteThicknessUm << ",\n";
    summary << "  \"max_step_mm\": " << opt_.maxStepMm << ",\n";
    summary << "  \"outgoing_mosaic_model\": \"" << opt_.outgoingMosaicModel << "\",\n";
    summary << "  \"n_crystal_steps\": " << nCrystalSteps_ << ",\n";
    summary << "  \"mean_crystal_step_mm\": " << (nCrystalSteps_ ? sumCrystalStepMm_ / nCrystalSteps_ : 0.0) << ",\n";
    summary << "  \"max_observed_crystal_step_mm\": " << maxObservedCrystalStepMm_ << ",\n";
    summary << "  \"only_ring_id\": " << opt_.onlyRingId << ",\n";
    summary << "  \"only_tile_id\": " << opt_.onlyTileId << ",\n";
    summary << "  \"n_primaries\": " << opt_.nEvents << ",\n";
    summary << "  \"custom_laue_only_branch_counters\": true,\n";
    summary << "  \"custom_laue_branch_scope\": \"DIFFRACT is the only sampled custom Laue branch; ABSORB/TRANSMIT probabilities are backend diagnostics while standard Geant4 EM processes compete independently\",\n";
    summary << "  \"standard_em_losses_are_not_written_to_optics_history\": true,\n";
    summary << "  \"transmitted_space_source\": \"actual primary gamma focal-plane crossings recorded by BFullFocalPlaneSteppingAction\",\n";
    summary << "  \"n_rings\": " << rings_.size() << ",\n";
    summary << "  \"n_laue_interactions\": " << nDiff_ << ",\n";
    summary << "  \"laue_interaction_fraction\": " << (n ? nDiff_ / n : 0.0) << ",\n";
    summary << "  \"n_diffracted\": " << nDiff_ << ",\n";
    summary << "  \"n_custom_laue_diffracted\": " << nDiff_ << ",\n";
    summary << "  \"n_custom_laue_absorbed\": " << nAbs_ << ",\n";
    summary << "  \"n_custom_laue_transmitted\": " << nTrans_ << ",\n";
    summary << "  \"n_absorbed\": " << nAbs_ << ",\n";
    summary << "  \"n_transmitted\": " << nTrans_ << ",\n";
    summary << "  \"n_absorbed_field_scope\": \"custom Laue branch only; not total Geant4 EM absorption\",\n";
    summary << "  \"n_transmitted_field_scope\": \"custom Laue branch only; use primary_or_transmitted_focal_crossings/transmitted_space.csv for tracked transmitted primaries\",\n";
    summary << "  \"diffraction_fraction\": " << (n ? nDiff_ / n : 0.0) << ",\n";
    summary << "  \"absorption_fraction\": " << (n ? nAbs_ / n : 0.0) << ",\n";
    summary << "  \"transmission_fraction\": " << (n ? nTrans_ / n : 0.0) << ",\n";
    summary << "  \"non_focal_event_estimate\": " << (opt_.nEvents - nFocalCrossings_) << ",\n";
    summary << "  \"estimated_standard_em_or_nonfocal_losses\": " << (opt_.nEvents - nFocalCrossings_) << ",\n";
    summary << "  \"focal_crossings\": " << nFocalCrossings_ << ",\n";
    summary << "  \"primary_or_transmitted_focal_crossings\": " << nPrimaryFocalCrossings_ << ",\n";
    summary << "  \"uncollided_transmitted_focal_crossings\": " << nUncollidedPrimaryFocalCrossings_ << ",\n";
    summary << "  \"scattered_primary_focal_crossings\": " << nScatteredPrimaryFocalCrossings_ << ",\n";
    summary << "  \"transmitted_space_rows\": " << nPrimaryFocalCrossings_ << ",\n";
    summary << "  \"laue_diffracted_focal_crossings\": " << nLaueFocalCrossings_ << ",\n";
    summary << "  \"other_gamma_focal_crossings\": " << nOtherFocalCrossings_ << ",\n";
    long emergentOverlap = 0;
    for (const int eventId : diffractedEventIds_) {
      if (uncollidedTransmittedEventIds_.count(eventId)) ++emergentOverlap;
    }
    const long emergentR = static_cast<long>(diffractedEventIds_.size());
    const long emergentT = static_cast<long>(uncollidedTransmittedEventIds_.size());
    const long emergentAOrRemoved = opt_.nEvents - emergentR - emergentT + emergentOverlap;
    summary << "  \"emergent_r_events\": " << emergentR << ",\n";
    summary << "  \"emergent_t_events\": " << emergentT << ",\n";
    summary << "  \"emergent_a_or_removed_events\": " << emergentAOrRemoved << ",\n";
    summary << "  \"emergent_r_t_event_overlap\": " << emergentOverlap << ",\n";
    summary << "  \"emergent_r_fraction\": " << (n ? emergentR / n : 0.0) << ",\n";
    summary << "  \"emergent_t_fraction\": " << (n ? emergentT / n : 0.0) << ",\n";
    summary << "  \"emergent_a_or_removed_fraction\": " << (n ? emergentAOrRemoved / n : 0.0) << ",\n";
    summary << "  \"emergent_rta_closure\": " << (n ? (emergentR + emergentT + emergentAOrRemoved - emergentOverlap) / n : 0.0) << ",\n";
    summary << "  \"emergent_rta_definition\": \"R: BFull-Laue-created gamma reaches focal plane; T: uncollided primary reaches focal plane with incident energy and direction; A_or_removed: all remaining primary events, including standard-EM absorption/scatter and diffracted photons lost before emergence\",\n";
    double analyticRefSum = 0.0;
    long analyticRefN = 0;
    for (std::size_t i = 0; i < rings_.size(); ++i) {
      analyticRefSum += AnalyticReferenceFocalDiffraction(rings_[i], opt_, rockingCurves_) *
                        static_cast<double>(ringStats_[i].n);
      analyticRefN += ringStats_[i].n;
    }
    const double analyticRef = analyticRefN ? analyticRefSum / static_cast<double>(analyticRefN) : 0.0;
    const double emergentFocal = n ? static_cast<double>(nLaueFocalCrossings_) / n : 0.0;
    summary << "  \"analytic_reference_focal_diffraction_fraction\": " << analyticRef << ",\n";
    summary << "  \"emergent_focal_diffraction_fraction\": " << emergentFocal << ",\n";
    summary << "  \"emergent_minus_analytic_focal_diffraction\": " << (emergentFocal - analyticRef) << ",\n";
    summary << "  \"diffraction_validation_note\": \"emergent EM-competing focal-plane diffracted fraction (laue_diffracted_focal_crossings/n_primaries) vs the absorption-included mosaic-Laue reference at the Bragg peak (Darwin-Hamilton closed form or external XOP/CRYSTAL curve); they should agree within Monte-Carlo and thick-crystal point-diffraction error, which is the gate that the EM-competing process reproduces the validated diffraction physics\",\n";
    summary << "  \"projected_interaction_spot_d90_cm\": " << ContainmentDiameterCm(detectorHits_) << ",\n";
    summary << "  \"focal_crossing_spot_d90_cm\": " << ContainmentDiameterCm(focalDetectorHits_) << ",\n";
    summary << "  \"energy_min_keV\": " << rings_.front().designEnergyKeV << ",\n";
    summary << "  \"energy_max_keV\": " << rings_.back().designEnergyKeV << ",\n";
    summary << "  \"focal_length_mm\": " << opt_.focalLengthMm << ",\n";
    summary << "  \"world_half_xy_mm\": " << WorldHalfXYMm(rings_) << ",\n";
    summary << "  \"world_half_z_mm\": " << WorldHalfZMm(rings_, opt_.focalLengthMm) << ",\n";
    summary << "  \"ring_config\": \"" << opt_.ringConfigPath << "\",\n";
    summary << "  \"benchmark_efficiency_table_not_used_for_physics\": \"" << opt_.efficiencyTablePath << "\",\n";
    summary << "  \"visualization_wrl\": \"" << opt_.outDir << "/laue_multiring_scene.wrl\"\n";
    summary << "}\n";
  }

 private:
  G4ThreeVector PlaneHit(const G4ThreeVector& pos, const G4ThreeVector& dir) const {
    const double t = (opt_.focalLengthMm * mm - pos.z()) / dir.z();
    return pos + t * dir;
  }

  double ContainmentDiameterCm(const std::vector<G4ThreeVector>& points) const {
    if (points.empty()) return 0.0;
    std::vector<double> radii;
    for (const auto& p : points) radii.push_back(std::sqrt(p.x() * p.x() + p.y() * p.y()) / mm);
    std::sort(radii.begin(), radii.end());
    const std::size_t idx = std::min(radii.size() - 1, static_cast<std::size_t>(std::ceil(0.9 * radii.size()) - 1.0));
    return 2.0 * radii[idx] / 10.0;
  }

  void AddWrl(const G4ThreeVector& start, const G4ThreeVector& end, const std::string& stage) {
    if (segments_.size() >= 480) return;
    segments_.push_back({start, end, stage});
  }

  void WriteVectorDiagnostics(const LaueVectorDiagnostics& diag) {
    if (!diag.valid) {
      for (int i = 0; i < kVectorDiagnosticFieldCount; ++i) history_ << ",";
      return;
    }
    history_ << "," << diag.model
             << "," << diag.planeNormal.x() << "," << diag.planeNormal.y() << "," << diag.planeNormal.z()
             << "," << diag.reciprocalVectorInvA.x() << "," << diag.reciprocalVectorInvA.y()
             << "," << diag.reciprocalVectorInvA.z()
             << "," << diag.reciprocalVectorMagInvA << "," << diag.reciprocalVectorExpectedMagInvA
             << "," << diag.scatteringQVectorInvA.x() << "," << diag.scatteringQVectorInvA.y()
             << "," << diag.scatteringQVectorInvA.z()
             << "," << diag.scatteringQVectorMagInvA
             << "," << diag.latticeGNominalInvA.x() << "," << diag.latticeGNominalInvA.y()
             << "," << diag.latticeGNominalInvA.z()
             << "," << diag.latticeGNominalMagInvA
             << "," << diag.latticeGPerturbedInvA.x() << "," << diag.latticeGPerturbedInvA.y()
             << "," << diag.latticeGPerturbedInvA.z()
             << "," << diag.latticeGPerturbedMagInvA
             << "," << diag.qMinusGNominalMagInvA << "," << diag.qMinusGPerturbedMagInvA
             << "," << diag.relativeBraggResidualNominal << "," << diag.relativeBraggResidualPerturbed
             << "," << diag.focusDirection.x() << "," << diag.focusDirection.y() << "," << diag.focusDirection.z()
             << "," << diag.thetaBRad << "," << diag.thetaLocalRad << "," << diag.deltaThetaRad
             << "," << diag.mosaicPerturbationRad << "," << diag.angleCodeVsRecordedReflectRad
             << "," << diag.elasticError;
  }

  void WritePerRingSummary() const {
    std::ofstream csv((opt_.outDir + "/per_ring_summary.csv").c_str());
    csv << "ring_id,design_energy_keV,radius_mm,n_laue_process_interactions,n_diffracted,n_custom_laue_absorbed,n_custom_laue_transmitted,laue_process_diffraction_fraction,analytic_reference_focal_p_diff,mean_p_diff,mean_p_abs,mean_p_trans,rocking_curve_source,rocking_curve_path\n";
    std::ofstream json((opt_.outDir + "/per_ring_summary.json").c_str());
    json << "[\n";
    for (std::size_t i = 0; i < rings_.size(); ++i) {
      const auto& ring = rings_[i];
      const auto& st = ringStats_[i];
      const double n = static_cast<double>(st.n);
      const double analyticRefPDiff = AnalyticReferenceFocalDiffraction(ring, opt_, rockingCurves_);
      csv << ring.ringId << "," << ring.designEnergyKeV << "," << ring.radiusMm << ","
          << st.n << "," << st.diff << "," << st.abs << "," << st.trans << ","
          << (n ? st.diff / n : 0.0) << "," << analyticRefPDiff << "," << (n ? st.sumPDiff / n : 0.0) << ","
          << (n ? st.sumPAbs / n : 0.0) << "," << (n ? st.sumPTrans / n : 0.0) << ","
          << RockingCurveSourceForRing(rockingCurves_, ring.ringId) << ","
          << RockingCurvePathForRing(rockingCurves_, ring.ringId) << "\n";
      json << "  {\"ring_id\": " << ring.ringId
           << ", \"design_energy_keV\": " << ring.designEnergyKeV
           << ", \"radius_mm\": " << ring.radiusMm
           << ", \"n_laue_process_interactions\": " << st.n
           << ", \"n_diffracted\": " << st.diff
           << ", \"n_custom_laue_absorbed\": " << st.abs
           << ", \"n_custom_laue_transmitted\": " << st.trans
           << ", \"laue_process_diffraction_fraction\": " << (n ? st.diff / n : 0.0)
           << ", \"analytic_reference_focal_p_diff\": " << analyticRefPDiff
           << ", \"mean_p_diff\": " << (n ? st.sumPDiff / n : 0.0)
           << ", \"mean_p_abs\": " << (n ? st.sumPAbs / n : 0.0)
           << ", \"mean_p_trans\": " << (n ? st.sumPTrans / n : 0.0)
           << ", \"rocking_curve_source\": \"" << RockingCurveSourceForRing(rockingCurves_, ring.ringId) << "\""
           << ", \"rocking_curve_path\": \"" << RockingCurvePathForRing(rockingCurves_, ring.ringId) << "\"}";
      json << (i + 1 == rings_.size() ? "\n" : ",\n");
    }
    json << "]\n";
  }

  void WriteWrl(const std::string& path) const {
    std::ofstream wrl(path.c_str());
    wrl << "#VRML V2.0 utf8\n";
    wrl << "WorldInfo { title \"Geant4 11.4 Guan-style Darwin model/process Laue optics\" }\n";
    wrl << "Viewpoint { position 0 -310 135 orientation 1 0 0 1.15 description \"Guan-style Darwin Laue lens\" }\n";
    wrl << "Background { skyColor [ 1 1 1 ] }\n";
    for (const auto& ring : rings_) {
      wrl << "Shape { appearance Appearance { material Material { emissiveColor 0.1 0.45 0.9 diffuseColor 0.1 0.45 0.9 transparency 0.15 } } "
          << "geometry IndexedLineSet { coord Coordinate { point [\n";
      const int nCircle = 144;
      for (int j = 0; j <= nCircle; ++j) {
        const double phi = 2.0 * kPi * static_cast<double>(j) / static_cast<double>(nCircle);
        wrl << ring.radiusMm * std::cos(phi) << " " << ring.radiusMm * std::sin(phi) << " "
            << ring.zOffsetMm << ",\n";
      }
      wrl << "] } coordIndex [\n";
      for (int j = 0; j < nCircle; ++j) wrl << j << ", " << j + 1 << ", -1,\n";
      wrl << "] } }\n";
      for (int i = 0; i < ring.nTiles; ++i) {
        const double phi = 2.0 * kPi * static_cast<double>(i) / static_cast<double>(ring.nTiles);
        wrl << "Transform { translation " << ring.radiusMm * std::cos(phi) << " "
            << ring.radiusMm * std::sin(phi) << " " << ring.zOffsetMm
            << " children [ Shape { appearance Appearance { material Material { diffuseColor 0.0 0.55 0.25 } } geometry Box { size "
            << ring.tileSizeMm << " " << ring.tileSizeMm << " " << ring.thicknessMm * 0.15 << " } } ] }\n";
      }
    }
    wrl << "Transform { translation 0 0 " << opt_.focalLengthMm
        << " children [ Shape { appearance Appearance { material Material { diffuseColor 0.9 0.1 0.1 } } geometry Sphere { radius 5 } } ] }\n";
    auto writeSegments = [&](const std::string& stage, double r, double g, double b) {
      std::vector<const WrlSegment*> selected;
      for (const auto& segment : segments_) {
        if (segment.stage == stage) selected.push_back(&segment);
      }
      if (selected.empty()) return;
      wrl << "Shape { appearance Appearance { material Material { emissiveColor " << r << " " << g << " " << b
          << " diffuseColor " << r << " " << g << " " << b << " } } geometry IndexedLineSet { coord Coordinate { point [\n";
      for (const auto* segment : selected) {
        wrl << segment->start.x() / mm << " " << segment->start.y() / mm << " " << segment->start.z() / mm << ",\n";
        wrl << segment->end.x() / mm << " " << segment->end.y() / mm << " " << segment->end.z() / mm << ",\n";
      }
      wrl << "] } coordIndex [\n";
      for (std::size_t i = 0; i < selected.size(); ++i) wrl << 2 * i << ", " << 2 * i + 1 << ", -1,\n";
      wrl << "] } }\n";
    };
    writeSegments("INCIDENT", 0.05, 0.15, 0.95);
    writeSegments("DIFFRACT", 0.9, 0.05, 0.05);
    writeSegments("TRANSMIT", 0.45, 0.45, 0.45);
    writeSegments("ABSORB", 0.95, 0.6, 0.0);
  }

  Options opt_;
  std::vector<RingSpec> rings_;
  RockingCurveLibrary rockingCurves_;
  std::ofstream phase_;
  std::ofstream transmitted_;
  std::ofstream history_;
  std::ofstream focal_;
  std::vector<RingStats> ringStats_;
  std::vector<G4ThreeVector> detectorHits_;
  std::vector<G4ThreeVector> focalDetectorHits_;
  std::vector<WrlSegment> segments_;
  double nDiff_ = 0.0;
  double nAbs_ = 0.0;
  double nTrans_ = 0.0;
  long nFocalCrossings_ = 0;
  long nPrimaryFocalCrossings_ = 0;
  long nUncollidedPrimaryFocalCrossings_ = 0;
  long nScatteredPrimaryFocalCrossings_ = 0;
  long nLaueFocalCrossings_ = 0;
  long nOtherFocalCrossings_ = 0;
  std::set<int> diffractedEventIds_;
  std::set<int> uncollidedTransmittedEventIds_;
  long nCrystalSteps_ = 0;
  double sumCrystalStepMm_ = 0.0;
  double maxObservedCrystalStepMm_ = 0.0;
};

struct CrystalDecision {
  double thetaLocalRad = 0.0;
  double thetaBRad = 0.0;
  double deltaThetaRad = 0.0;
  optics::LaueEfficiencyRow probs;
  G4ThreeVector idealOutDir;
  G4ThreeVector reflectedOutDir;
  G4ThreeVector focusDirection;
  G4ThreeVector idealPlaneNormal;
  G4ThreeVector planeNormal;
  double reflectionVectorError = 0.0;
  double planeMinusBraggAbsRad = 0.0;
  double mosaicPerturbationRad = 0.0;
};

class GuanDarwinDynamicalModel {
 public:
  GuanDarwinDynamicalModel() = default;

  CrystalDecision Evaluate(
      const RingSpec& ring,
      int tileId,
      const G4ThreeVector& pos,
      const G4ThreeVector& inDir,
      const Options& opt,
      const RockingCurveLibrary& rockingCurves) const {
    CrystalDecision decision;
    const double offAxisXRad = opt.offAxisXArcmin / 60.0 * kPi / 180.0;
    const double offAxisYRad = opt.offAxisYArcmin / 60.0 * kPi / 180.0;
    const G4ThreeVector diagnosticFocusPoint(
        opt.focalLengthMm * std::tan(offAxisXRad) * mm,
        opt.focalLengthMm * std::tan(offAxisYRad) * mm,
        opt.focalLengthMm * mm);
    decision.focusDirection = (diagnosticFocusPoint - pos).unit();
    decision.idealPlaneNormal = FixedTilePlaneNormal(ring, tileId, opt);
    decision.idealOutDir = ReflectAcrossPlane(inDir, decision.idealPlaneNormal);
    if (opt.outgoingMosaicModel == "gaussian_plane") {
      decision.planeNormal = PerturbDirection(
          decision.idealPlaneNormal, FwhmArcsecToSigmaRad(opt.mosaicFwhmArcsec));
      decision.reflectedOutDir = ReflectAcrossPlane(inDir, decision.planeNormal);
    } else if (opt.outgoingMosaicModel == "gaussian_outgoing") {
      decision.planeNormal = decision.idealPlaneNormal;
      decision.reflectedOutDir = PerturbDirection(
          decision.idealOutDir, FwhmArcsecToSigmaRad(opt.mosaicFwhmArcsec));
    } else {
      decision.planeNormal = decision.idealPlaneNormal;
      decision.reflectedOutDir = decision.idealOutDir;
    }
    decision.mosaicPerturbationRad = AngleBetweenRad(decision.planeNormal, decision.idealPlaneNormal);
    decision.reflectionVectorError = AngleBetweenRad(decision.reflectedOutDir, ReflectAcrossPlane(inDir, decision.planeNormal));
    decision.thetaLocalRad = std::asin(std::fabs(inDir.unit().dot(decision.idealPlaneNormal)));
    decision.thetaBRad = BraggAngleRad(ring.designEnergyKeV, ring.dSpacingA);
    decision.deltaThetaRad = decision.thetaLocalRad - decision.thetaBRad;
    const double braggFromPlane = std::asin(std::fabs(inDir.unit().dot(decision.planeNormal)));
    decision.planeMinusBraggAbsRad = std::fabs(braggFromPlane - decision.thetaBRad);
    decision.probs = BFullBackendProbabilities(ring, decision.deltaThetaRad, opt, rockingCurves);
    return decision;
  }
};

// Non-forced discrete Laue diffraction process. It overrides GetMeanFreePath
// with a finite equivalent diffraction MFP, so it competes with the standard
// Geant4 EM processes (kept enabled in the physics list) rather than being a
// forced boundary process. It deliberately derives from G4VDiscreteProcess
// instead of G4VEmProcess: the former is portable across Geant4 10.2/11.x and
// needs no no-op G4VEmModel, while the EM competition (the physically relevant
// behaviour) is identical. The earlier G4VEmProcess variant only bought a
// cosmetic "EM category" label and failed to initialise on Geant4 11.x.
class GuanStyleLaueBraggProcess : public G4VDiscreteProcess {
 public:
  GuanStyleLaueBraggProcess(
      MultiRingRunState* state,
      const Options& opt,
      const std::vector<RingSpec>& rings,
      const RockingCurveLibrary& rockingCurves)
      : G4VDiscreteProcess("BFullLaueBraggProcess", fElectromagnetic),
        state_(state),
        opt_(opt),
        rings_(rings),
        rockingCurves_(rockingCurves) {
    SetProcessSubType(9001);
  }

  void ProcessDescription(std::ostream& out) const override {
    out << "B-FULL Laue Bragg process: non-forced G4VDiscreteProcess with a finite "
        << "equivalent diffraction mean free path competing with standard Geant4 EM; "
        << "tile-dependent geometry and lattice-plane evaluation are performed in PostStepDoIt.";
  }

  G4double GetMeanFreePath(const G4Track& track, G4double, G4ForceCondition* condition) override {
    if (condition) *condition = NotForced;
    if (track.GetDefinition() != G4Gamma::GammaDefinition()) return DBL_MAX;
    if (track.GetParentID() != 0) return DBL_MAX;
    const G4VPhysicalVolume* volume = track.GetVolume();
    if (!NameContains(volume, "LaueCrystal")) return DBL_MAX;
    const int copyNo = volume ? volume->GetCopyNo() : 0;
    const RingSpec& ring = RingFromCopyNo(rings_, copyNo);
    const int tileId = copyNo % kCopyStride;
    const G4ThreeVector inDir = track.GetMomentumDirection().unit();
    const G4ThreeVector fixedPlaneNormal = FixedTilePlaneNormal(ring, tileId, opt_);
    const double thetaLocal = std::asin(std::fabs(inDir.dot(fixedPlaneNormal)));
    const double deltaTheta = thetaLocal - BraggAngleRad(ring.designEnergyKeV, ring.dSpacingA);
    const BFullInteractionScale scale = BFullEquivalentDiffractionScale(ring, deltaTheta, inDir, opt_, rockingCurves_);
    if (!std::isfinite(scale.meanFreePathCm) || scale.meanFreePathCm <= 0.0 || scale.meanFreePathCm == DBL_MAX) {
      return DBL_MAX;
    }
    return scale.meanFreePathCm * cm;
  }

  G4VParticleChange* PostStepDoIt(const G4Track& track, const G4Step& step) override {
    aParticleChange.Initialize(track);
    if (track.GetDefinition() != G4Gamma::GammaDefinition()) return &aParticleChange;
    if (track.GetParentID() != 0) return &aParticleChange;
    const G4VPhysicalVolume* volume = step.GetPreStepPoint()->GetPhysicalVolume();
    if (!NameContains(volume, "LaueCrystal")) return &aParticleChange;
    const int copyNo = volume ? volume->GetCopyNo() : 0;
    const RingSpec& ring = RingFromCopyNo(rings_, copyNo);
    const int tileId = copyNo % kCopyStride;
    const G4Event* event = G4RunManager::GetRunManager()->GetCurrentEvent();
    const int eventId = event ? event->GetEventID() : -1;
    const G4ThreeVector pos = step.GetPostStepPoint()->GetPosition();
    const G4ThreeVector inDir = track.GetMomentumDirection().unit();
    const CrystalDecision decision = model_.Evaluate(ring, tileId, pos, inDir, opt_, rockingCurves_);
    const optics::LaueEfficiencyRow probs = decision.probs;
    const G4ThreeVector outDir = decision.reflectedOutDir;
    const LaueVectorDiagnostics diagnostics = MakeLaueVectorDiagnostics(
        "bfull_fixed_tile_plane_normal_em_competing",
        ring.designEnergyKeV,
        inDir,
        outDir,
        decision.idealPlaneNormal,
        decision.planeNormal,
        decision.focusDirection,
        ring.dSpacingA,
        decision.thetaBRad,
        decision.thetaLocalRad,
        decision.deltaThetaRad,
        decision.mosaicPerturbationRad);
    G4DynamicParticle* secondary = new G4DynamicParticle(G4Gamma::GammaDefinition(), outDir, track.GetKineticEnergy());
    aParticleChange.SetNumberOfSecondaries(1);
    aParticleChange.AddSecondary(secondary, pos + 1.0e-5 * mm * outDir, true);
    aParticleChange.ProposeTrackStatus(fStopAndKill);
    state_->Record(eventId, track.GetTrackID(), "DIFFRACT", ring, tileId, pos, inDir, outDir, probs, decision.deltaThetaRad, diagnostics);
    return &aParticleChange;
  }

 private:
  MultiRingRunState* state_;
  Options opt_;
  std::vector<RingSpec> rings_;
  RockingCurveLibrary rockingCurves_;
  GuanDarwinDynamicalModel model_;
};

class MultiRingDetectorConstruction : public G4VUserDetectorConstruction {
 public:
  MultiRingDetectorConstruction(const std::vector<RingSpec>& rings, const Options& opt)
      : rings_(rings), focalLengthMm_(opt.focalLengthMm), maxStepMm_(opt.maxStepMm) {}

  G4VPhysicalVolume* Construct() override {
    G4NistManager* nist = G4NistManager::Instance();
    G4Material* vacuum = nist->FindOrBuildMaterial("G4_Galactic");
    G4Material* ge = nist->FindOrBuildMaterial("G4_Ge");
    G4Box* worldSolid = new G4Box("WorldSolid", WorldHalfXYMm(rings_) * mm, WorldHalfXYMm(rings_) * mm, WorldHalfZMm(rings_, focalLengthMm_) * mm);
    G4LogicalVolume* worldLogic = new G4LogicalVolume(worldSolid, vacuum, "WorldLogical");
    G4VPhysicalVolume* world = new G4PVPlacement(0, G4ThreeVector(), worldLogic, "World", 0, false, 0);
    for (const auto& ring : rings_) {
      G4Box* tileSolid = new G4Box(("LaueCrystalSolid_r" + std::to_string(ring.ringId)).c_str(),
                                   0.5 * ring.tileSizeMm * mm,
                                   0.5 * ring.tileSizeMm * mm,
                                   0.5 * ring.thicknessMm * mm);
      G4LogicalVolume* tileLogic = new G4LogicalVolume(tileSolid, ge, ("LaueCrystalLogical_r" + std::to_string(ring.ringId)).c_str());
      if (maxStepMm_ > 0.0) tileLogic->SetUserLimits(new G4UserLimits(maxStepMm_ * mm));
      for (int i = 0; i < ring.nTiles; ++i) {
        const double phi = 2.0 * kPi * static_cast<double>(i) / static_cast<double>(ring.nTiles);
        new G4PVPlacement(
            0,
            G4ThreeVector(ring.radiusMm * std::cos(phi) * mm, ring.radiusMm * std::sin(phi) * mm, ring.zOffsetMm * mm),
            tileLogic,
            "LaueCrystal",
            worldLogic,
            false,
            ring.ringId * kCopyStride + i);
      }
    }
    return world;
  }

 private:
  std::vector<RingSpec> rings_;
  double focalLengthMm_ = 8300.0;
  double maxStepMm_ = 0.0;
};

class MultiRingPhysicsList : public G4VModularPhysicsList {
 public:
  MultiRingPhysicsList(
      MultiRingRunState* state,
      const Options& opt,
      const std::vector<RingSpec>& rings,
      const RockingCurveLibrary& rockingCurves)
      : state_(state), opt_(opt), rings_(rings), rockingCurves_(rockingCurves) {
    defaultCutValue = 0.1 * mm;
    RegisterPhysics(new G4EmStandardPhysics());
  }

  void ConstructParticle() override {
    G4VModularPhysicsList::ConstructParticle();
    G4Gamma::GammaDefinition();
  }

  void ConstructProcess() override {
    G4VModularPhysicsList::ConstructProcess();
    GuanStyleLaueBraggProcess* process = new GuanStyleLaueBraggProcess(state_, opt_, rings_, rockingCurves_);
    G4Gamma::GammaDefinition()->GetProcessManager()->AddDiscreteProcess(process);
    if (opt_.maxStepMm > 0.0) {
      G4Gamma::GammaDefinition()->GetProcessManager()->AddDiscreteProcess(new G4StepLimiter("M08CrystalStepLimiter"));
    }
  }

 private:
  MultiRingRunState* state_;
  Options opt_;
  std::vector<RingSpec> rings_;
  RockingCurveLibrary rockingCurves_;
};

class MultiRingPrimaryGenerator : public G4VUserPrimaryGeneratorAction {
 public:
  MultiRingPrimaryGenerator(const Options& opt, const std::vector<RingSpec>& rings) : opt_(opt), rings_(rings) {
    gun_ = new G4ParticleGun(1);
    gun_->SetParticleDefinition(G4Gamma::GammaDefinition());
    sourceZMm_ = MinCrystalZMm(rings_) - 0.5 * MaxCrystalThicknessMm(rings_) - 5.0;
  }
  ~MultiRingPrimaryGenerator() override { delete gun_; }
  void GeneratePrimaries(G4Event* event) override {
    const int eventId = event->GetEventID();
    const RingSpec* ringPtr = 0;
    int tile = 0;
    if (opt_.onlyRingId >= 0) {
      for (const auto& candidate : rings_) {
        if (candidate.ringId == opt_.onlyRingId) {
          ringPtr = &candidate;
          break;
        }
      }
      if (ringPtr == 0) throw std::runtime_error("--only-ring-id does not match ring config");
      if (opt_.onlyTileId >= 0) {
        if (opt_.onlyTileId >= ringPtr->nTiles) throw std::runtime_error("--only-tile-id is outside selected ring");
        tile = opt_.onlyTileId;
      } else {
        tile = eventId % ringPtr->nTiles;
      }
    } else {
      const auto ringAndTile = RingAndTileForEvent(rings_, eventId);
      ringPtr = ringAndTile.first;
      tile = ringAndTile.second;
    }
    const RingSpec& ring = *ringPtr;
    const double phi = 2.0 * kPi * static_cast<double>(tile) / static_cast<double>(ring.nTiles);
    const double dx = (G4UniformRand() - 0.5) * opt_.sourceJitterMm;
    const double dy = (G4UniformRand() - 0.5) * opt_.sourceJitterMm;
    const double offAxisXRad = opt_.offAxisXArcmin / 60.0 * kPi / 180.0;
    const double offAxisYRad = opt_.offAxisYArcmin / 60.0 * kPi / 180.0;
    const G4ThreeVector direction(std::tan(offAxisXRad), std::tan(offAxisYRad), 1.0);
    const G4ThreeVector dir = direction.unit();
    const double targetX = ring.radiusMm * std::cos(phi) + dx;
    const double targetY = ring.radiusMm * std::sin(phi) + dy;
    const double pathToCrystal = (ring.zOffsetMm - sourceZMm_) / dir.z();
    gun_->SetParticleEnergy(ring.designEnergyKeV * keV);
    gun_->SetParticlePosition(G4ThreeVector((targetX - dir.x() * pathToCrystal) * mm,
                                            (targetY - dir.y() * pathToCrystal) * mm,
                                            sourceZMm_ * mm));
    gun_->SetParticleMomentumDirection(dir);
    gun_->GeneratePrimaryVertex(event);
  }
 private:
  Options opt_;
  std::vector<RingSpec> rings_;
  G4ParticleGun* gun_;
  double sourceZMm_ = -5.0;
};


class BFullFocalPlaneSteppingAction : public G4UserSteppingAction {
 public:
  BFullFocalPlaneSteppingAction(MultiRingRunState* state, double focalLengthMm)
      : state_(state), focalLengthMm_(focalLengthMm) {}

  void UserSteppingAction(const G4Step* step) override {
    const G4Track* track = step->GetTrack();
    if (track->GetDefinition() != G4Gamma::GammaDefinition()) return;
    if (NameContains(step->GetPreStepPoint()->GetPhysicalVolume(), "LaueCrystal")) {
      state_->RecordCrystalStep(step->GetStepLength() / mm);
    }
    const G4ThreeVector pre = step->GetPreStepPoint()->GetPosition();
    const G4ThreeVector post = step->GetPostStepPoint()->GetPosition();
    const double focalZ = focalLengthMm_ * mm;
    if (!((pre.z() < focalZ && post.z() >= focalZ) || (pre.z() > focalZ && post.z() <= focalZ))) return;
    const double dz = post.z() - pre.z();
    if (std::fabs(dz) < 1.0e-12 * mm) return;
    const double f = (focalZ - pre.z()) / dz;
    if (f < 0.0 || f > 1.0) return;
    const G4ThreeVector hit = pre + f * (post - pre);
    state_->RecordFocalCrossing(*track, hit, track->GetMomentumDirection().unit());
  }

 private:
  MultiRingRunState* state_;
  double focalLengthMm_ = 8300.0;
};

}  // namespace

int main(int argc, char** argv) {
  try {
    const Options opt = ParseOptions(argc, argv);
    const std::vector<RingSpec> rings = LoadRingConfig(opt.ringConfigPath, opt.focalLengthMm);
    const RockingCurveLibrary rockingCurves = LoadRockingCurveLibrary(opt);
    ValidateRockingCurveCoverage(rings, opt, rockingCurves);
    CLHEP::HepRandom::setTheSeed(opt.seed);
    MultiRingRunState state(opt, rings, rockingCurves);
    G4RunManager* runManager = new G4RunManager;
    runManager->SetUserInitialization(new MultiRingDetectorConstruction(rings, opt));
    runManager->SetUserInitialization(new MultiRingPhysicsList(&state, opt, rings, rockingCurves));
    runManager->SetUserAction(new MultiRingPrimaryGenerator(opt, rings));
    runManager->SetUserAction(new BFullFocalPlaneSteppingAction(&state, opt.focalLengthMm));
    runManager->Initialize();
    runManager->BeamOn(opt.nEvents);
    delete runManager;
    state.WriteOutputs();
    std::cout << "LAUE_BFULL_PROCESS_SUMMARY events=" << opt.nEvents
              << " rings=" << rings.size() << " out=" << opt.outDir << std::endl;
  } catch (const std::exception& exc) {
    std::cerr << "laue_multiring_bfull_demo error: " << exc.what() << std::endl;
    return 1;
  }
  return 0;
}
