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
};

struct Options {
  int nEvents = 50000;
  std::string outDir = "runs/geant4_laue_darwin_guan_process";
  long seed = 12345;
  std::string efficiencyTablePath = "data/laue/Ge111_480_550keV_darwin_mosaic_table.csv";
  std::string ringConfigPath = "data/laue/ge111_480_550keV_multiring_darwin_config.csv";
  double focalLengthMm = 8300.0;
  double sourceJitterMm = 0.3;
  double offAxisXArcmin = 0.0;
  double offAxisYArcmin = 0.0;
  double mosaicFwhmArcsec = 30.0;
  double crystalliteThicknessUm = 5.0;
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

G4ThreeVector ReflectAcrossPlane(const G4ThreeVector& inDir, const G4ThreeVector& planeNormal) {
  const G4ThreeVector k = inDir.unit();
  const G4ThreeVector n = planeNormal.unit();
  return (k - 2.0 * k.dot(n) * n).unit();
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
    } else if (arg == "--help" || arg == "-h") {
      std::cout << "Usage: " << argv[0] << " --n N --ring-config rings.csv --efficiency-table table.csv --out DIR"
                << " [--offaxis-x-arcmin X] [--offaxis-y-arcmin Y]"
                << " [--mosaic-fwhm-arcsec FWHM] [--crystallite-um UM]\n";
      std::exit(0);
    } else {
      throw std::runtime_error("unknown option: " + arg);
    }
  }
  if (opt.nEvents <= 0 || opt.focalLengthMm <= 0.0 || opt.mosaicFwhmArcsec <= 0.0 || opt.crystalliteThicknessUm <= 0.0) {
    throw std::runtime_error("invalid multiring demo options");
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
    const double expectedRadius = focalLengthMm * std::tan(2.0 * BraggAngleRad(ring.designEnergyKeV, ring.dSpacingA));
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
  MultiRingRunState(const Options& opt, const std::vector<RingSpec>& rings)
      : opt_(opt), rings_(rings), ringStats_(rings.size()) {
    EnsureDirectory(opt_.outDir);
    phase_.open((opt_.outDir + "/phase_space.csv").c_str());
    transmitted_.open((opt_.outDir + "/transmitted_space.csv").c_str());
    history_.open((opt_.outDir + "/optics_history.csv").c_str());
    if (!phase_ || !transmitted_ || !history_) {
      throw std::runtime_error("cannot open multiring Laue output files in: " + opt_.outDir);
    }
    phase_ << "event_id,E_keV,x_mm,y_mm,z_mm,ux,uy,uz,weight,source_tag,particle_name,pdg_encoding,track_id,parent_id\n";
    transmitted_ << "event_id,E_keV,x_mm,y_mm,z_mm,ux,uy,uz,weight,source_tag,particle_name,pdg_encoding,track_id,parent_id\n";
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
             << ",1.0,geant4_laue_darwin_guan_process,gamma,22," << trackId << ",0\n";
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
                   << ",1.0,geant4_laue_darwin_guan_process_transmitted,gamma,22," << trackId << ",0\n";
      AddWrl(pos, hit, stage);
    }
  }

  void WriteOutputs() {
    phase_.flush();
    transmitted_.flush();
    history_.flush();
    WritePerRingSummary();
    WriteWrl(opt_.outDir + "/laue_multiring_scene.wrl");
    std::ofstream summary((opt_.outDir + "/summary.json").c_str());
    const double n = static_cast<double>(opt_.nEvents);
    summary << "{\n";
    summary << "  \"system\": \"geant4_laue_darwin_guan_process\",\n";
    summary << "  \"model\": \"guan_reiazi_style_online_darwin_hamilton_virtual_crystallite_v2\",\n";
    summary << "  \"warning\": \"Compiled Geant4 C++ process/model split inspired by Guan/Reiazi. This is not Guan/Reiazi source-code migration and not a Geant4 toolkit EM-category patch. Unlike the 01 baseline, branch probabilities are computed online in the model and are not read from the 01 pAbs/pDiff/pTrans efficiency table.\",\n";
    summary << "  \"geant4_bottom_code_modified\": false,\n";
    summary << "  \"model_process_split\": true,\n";
    summary << "  \"registered_process\": \"GuanStyleLaueBraggProcess added to gamma G4ProcessManager as a discrete process\",\n";
    summary << "  \"registered_in_geant4_em_category\": false,\n";
    summary << "  \"uses_external_efficiency_table_for_physics\": false,\n";
    summary << "  \"online_physics_backend\": \"Darwin-Hamilton mosaic formula with virtual crystallite plane-normal sampling\",\n";
    summary << "  \"vector_diagnostics_in_optics_history\": true,\n";
    summary << "  \"plane_normal_diagnostic_model\": \"guan_virtual_crystallite_plane_normal; emitted DIFFRACT direction is reflected across the recorded plane normal\",\n";
    summary << "  \"mosaic_fwhm_arcsec\": " << opt_.mosaicFwhmArcsec << ",\n";
    summary << "  \"crystallite_thickness_um\": " << opt_.crystalliteThicknessUm << ",\n";
    summary << "  \"n_primaries\": " << opt_.nEvents << ",\n";
    summary << "  \"n_rings\": " << rings_.size() << ",\n";
    summary << "  \"n_diffracted\": " << nDiff_ << ",\n";
    summary << "  \"n_absorbed\": " << nAbs_ << ",\n";
    summary << "  \"n_transmitted\": " << nTrans_ << ",\n";
    summary << "  \"diffraction_fraction\": " << (n ? nDiff_ / n : 0.0) << ",\n";
    summary << "  \"absorption_fraction\": " << (n ? nAbs_ / n : 0.0) << ",\n";
    summary << "  \"transmission_fraction\": " << (n ? nTrans_ / n : 0.0) << ",\n";
    summary << "  \"spot_d90_cm\": " << ContainmentDiameterCm(detectorHits_) << ",\n";
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
    csv << "ring_id,design_energy_keV,radius_mm,n_primaries,n_diffracted,n_absorbed,n_transmitted,diffraction_fraction,mean_p_diff,mean_p_abs,mean_p_trans\n";
    std::ofstream json((opt_.outDir + "/per_ring_summary.json").c_str());
    json << "[\n";
    for (std::size_t i = 0; i < rings_.size(); ++i) {
      const auto& ring = rings_[i];
      const auto& st = ringStats_[i];
      const double n = static_cast<double>(st.n);
      csv << ring.ringId << "," << ring.designEnergyKeV << "," << ring.radiusMm << ","
          << st.n << "," << st.diff << "," << st.abs << "," << st.trans << ","
          << (n ? st.diff / n : 0.0) << "," << (n ? st.sumPDiff / n : 0.0) << ","
          << (n ? st.sumPAbs / n : 0.0) << "," << (n ? st.sumPTrans / n : 0.0) << "\n";
      json << "  {\"ring_id\": " << ring.ringId
           << ", \"design_energy_keV\": " << ring.designEnergyKeV
           << ", \"radius_mm\": " << ring.radiusMm
           << ", \"n_primaries\": " << st.n
           << ", \"n_diffracted\": " << st.diff
           << ", \"n_absorbed\": " << st.abs
           << ", \"n_transmitted\": " << st.trans
           << ", \"diffraction_fraction\": " << (n ? st.diff / n : 0.0)
           << ", \"mean_p_diff\": " << (n ? st.sumPDiff / n : 0.0)
           << ", \"mean_p_abs\": " << (n ? st.sumPAbs / n : 0.0)
           << ", \"mean_p_trans\": " << (n ? st.sumPTrans / n : 0.0) << "}";
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
        wrl << ring.radiusMm * std::cos(phi) << " " << ring.radiusMm * std::sin(phi) << " 0,\n";
      }
      wrl << "] } coordIndex [\n";
      for (int j = 0; j < nCircle; ++j) wrl << j << ", " << j + 1 << ", -1,\n";
      wrl << "] } }\n";
      for (int i = 0; i < ring.nTiles; ++i) {
        const double phi = 2.0 * kPi * static_cast<double>(i) / static_cast<double>(ring.nTiles);
        wrl << "Transform { translation " << ring.radiusMm * std::cos(phi) << " "
            << ring.radiusMm * std::sin(phi) << " 0 children [ Shape { appearance Appearance { material Material { diffuseColor 0.0 0.55 0.25 } } geometry Box { size "
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
  std::ofstream phase_;
  std::ofstream transmitted_;
  std::ofstream history_;
  std::vector<RingStats> ringStats_;
  std::vector<G4ThreeVector> detectorHits_;
  std::vector<WrlSegment> segments_;
  double nDiff_ = 0.0;
  double nAbs_ = 0.0;
  double nTrans_ = 0.0;
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
      const G4ThreeVector& pos,
      const G4ThreeVector& inDir,
      const Options& opt) const {
    CrystalDecision decision;
    const double offAxisXRad = opt.offAxisXArcmin / 60.0 * kPi / 180.0;
    const double offAxisYRad = opt.offAxisYArcmin / 60.0 * kPi / 180.0;
    const G4ThreeVector focusPoint(
        opt.focalLengthMm * std::tan(offAxisXRad) * mm,
        opt.focalLengthMm * std::tan(offAxisYRad) * mm,
        opt.focalLengthMm * mm);
    decision.idealOutDir = (focusPoint - pos).unit();
    decision.focusDirection = decision.idealOutDir;
    decision.idealPlaneNormal = (inDir.unit() - decision.idealOutDir).unit();
    decision.planeNormal = PerturbDirection(decision.idealPlaneNormal, FwhmArcsecToSigmaRad(opt.mosaicFwhmArcsec));
    decision.reflectedOutDir = ReflectAcrossPlane(inDir, decision.planeNormal);
    decision.mosaicPerturbationRad = AngleBetweenRad(decision.planeNormal, decision.idealPlaneNormal);
    decision.reflectionVectorError = AngleBetweenRad(decision.reflectedOutDir, ReflectAcrossPlane(inDir, decision.planeNormal));
    decision.thetaLocalRad = 0.5 * std::acos(std::max(-1.0, std::min(1.0, inDir.unit().dot(decision.idealOutDir))));
    decision.thetaBRad = BraggAngleRad(ring.designEnergyKeV, ring.dSpacingA);
    decision.deltaThetaRad = decision.thetaLocalRad - decision.thetaBRad;
    const double braggFromPlane = std::asin(std::fabs(inDir.unit().dot(decision.planeNormal)));
    decision.planeMinusBraggAbsRad = std::fabs(braggFromPlane - decision.thetaBRad);
    decision.probs = OnlineDarwinMosaicProbabilities(ring, decision.deltaThetaRad, opt);
    return decision;
  }
};

class GuanStyleLaueBraggProcess : public G4VDiscreteProcess {
 public:
  GuanStyleLaueBraggProcess(
      MultiRingRunState* state,
      const Options& opt,
      const std::vector<RingSpec>& rings)
      : G4VDiscreteProcess("GuanStyleLaueBraggProcess"), state_(state), opt_(opt), rings_(rings) {}

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
    const G4VPhysicalVolume* volume = step.GetPostStepPoint()->GetPhysicalVolume();
    if (volume == 0 || !NameContains(volume, "LaueCrystal")) volume = step.GetPreStepPoint()->GetPhysicalVolume();
    const int copyNo = volume ? volume->GetCopyNo() : 0;
    const RingSpec& ring = RingFromCopyNo(rings_, copyNo);
    const int tileId = copyNo % kCopyStride;
    const G4Event* event = G4RunManager::GetRunManager()->GetCurrentEvent();
    const int eventId = event ? event->GetEventID() : -1;
    const G4ThreeVector pos = step.GetPostStepPoint()->GetPosition();
    const G4ThreeVector inDir = track.GetMomentumDirection().unit();
    const CrystalDecision decision = model_.Evaluate(ring, pos, inDir, opt_);
    const optics::LaueEfficiencyRow probs = decision.probs;
    const double u = G4UniformRand();
    if (u < probs.pAbs) {
      state_->Record(eventId, track.GetTrackID(), "ABSORB", ring, tileId, pos, inDir, G4ThreeVector(), probs, decision.deltaThetaRad);
      aParticleChange.ProposeTrackStatus(fStopAndKill);
      return &aParticleChange;
    }
    if (u >= probs.pAbs + probs.pDiff) {
      state_->Record(eventId, track.GetTrackID(), "TRANSMIT", ring, tileId, pos, inDir, inDir, probs, decision.deltaThetaRad);
      aParticleChange.ProposeTrackStatus(fStopAndKill);
      return &aParticleChange;
    }
    const G4ThreeVector outDir = decision.reflectedOutDir;
    const LaueVectorDiagnostics diagnostics = MakeLaueVectorDiagnostics(
        "guan_virtual_crystallite_plane_normal",
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
  GuanDarwinDynamicalModel model_;
};

class MultiRingDetectorConstruction : public G4VUserDetectorConstruction {
 public:
  MultiRingDetectorConstruction(const std::vector<RingSpec>& rings, double focalLengthMm)
      : rings_(rings), focalLengthMm_(focalLengthMm) {}

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
      for (int i = 0; i < ring.nTiles; ++i) {
        const double phi = 2.0 * kPi * static_cast<double>(i) / static_cast<double>(ring.nTiles);
        new G4PVPlacement(
            0,
            G4ThreeVector(ring.radiusMm * std::cos(phi) * mm, ring.radiusMm * std::sin(phi) * mm, 0.0),
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
};

class MultiRingPhysicsList : public G4VUserPhysicsList {
 public:
  explicit MultiRingPhysicsList(GuanStyleLaueBraggProcess* process) : process_(process) {}
  void ConstructParticle() override { G4Gamma::GammaDefinition(); }
  void ConstructProcess() override {
    AddTransportation();
    G4Gamma::GammaDefinition()->GetProcessManager()->AddDiscreteProcess(process_);
  }
  void SetCuts() override { SetCutsWithDefault(); }
 private:
  GuanStyleLaueBraggProcess* process_;
};

class MultiRingPrimaryGenerator : public G4VUserPrimaryGeneratorAction {
 public:
  MultiRingPrimaryGenerator(const Options& opt, const std::vector<RingSpec>& rings) : opt_(opt), rings_(rings) {
    gun_ = new G4ParticleGun(1);
    gun_->SetParticleDefinition(G4Gamma::GammaDefinition());
    sourceZMm_ = -0.5 * MaxCrystalThicknessMm(rings_) - 5.0;
  }
  ~MultiRingPrimaryGenerator() override { delete gun_; }
  void GeneratePrimaries(G4Event* event) override {
    const auto ringAndTile = RingAndTileForEvent(rings_, event->GetEventID());
    const RingSpec& ring = *ringAndTile.first;
    const int tile = ringAndTile.second;
    const double phi = 2.0 * kPi * static_cast<double>(tile) / static_cast<double>(ring.nTiles);
    const double dx = (G4UniformRand() - 0.5) * opt_.sourceJitterMm;
    const double dy = (G4UniformRand() - 0.5) * opt_.sourceJitterMm;
    const double offAxisXRad = opt_.offAxisXArcmin / 60.0 * kPi / 180.0;
    const double offAxisYRad = opt_.offAxisYArcmin / 60.0 * kPi / 180.0;
    const G4ThreeVector direction(std::tan(offAxisXRad), std::tan(offAxisYRad), 1.0);
    const G4ThreeVector dir = direction.unit();
    const double targetX = ring.radiusMm * std::cos(phi) + dx;
    const double targetY = ring.radiusMm * std::sin(phi) + dy;
    const double pathToCrystal = (0.0 - sourceZMm_) / dir.z();
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

}  // namespace

int main(int argc, char** argv) {
  try {
    const Options opt = ParseOptions(argc, argv);
    const std::vector<RingSpec> rings = LoadRingConfig(opt.ringConfigPath, opt.focalLengthMm);
    CLHEP::HepRandom::setTheSeed(opt.seed);
    MultiRingRunState state(opt, rings);
    GuanStyleLaueBraggProcess* process = new GuanStyleLaueBraggProcess(&state, opt, rings);
    G4RunManager* runManager = new G4RunManager;
    runManager->SetUserInitialization(new MultiRingDetectorConstruction(rings, opt.focalLengthMm));
    runManager->SetUserInitialization(new MultiRingPhysicsList(process));
    runManager->SetUserAction(new MultiRingPrimaryGenerator(opt, rings));
    runManager->Initialize();
    runManager->BeamOn(opt.nEvents);
    delete runManager;
    state.WriteOutputs();
    std::cout << "LAUE_DARWIN_GUAN_PROCESS_SUMMARY events=" << opt.nEvents
              << " rings=" << rings.size() << " out=" << opt.outDir << std::endl;
  } catch (const std::exception& exc) {
    std::cerr << "laue_multiring_darwin_guan_demo error: " << exc.what() << std::endl;
    return 1;
  }
  return 0;
}
