// Native SF3/SG3 frozen-bank geometry comparison. No transport is launched.

R__LOAD_LIBRARY(libMEGAlib.so)

#include "TSystem.h"

#include "MGlobal.h"
#include "MString.h"
#include "MVector.h"
#include "MDGeometryQuest.h"
#include "MDMaterial.h"
#include "MDVolume.h"
#include "MDVolumeSequence.h"

#include <algorithm>
#include <array>
#include <cerrno>
#include <cctype>
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>

namespace {

constexpr std::size_t kExpectedRows = 37194;
constexpr std::size_t kExpectedFields = 15;
constexpr double kRotationYDeg = 45.0;
constexpr double kInjectionX = -30.0001;
constexpr double kEndX = 4.70;
constexpr double kToleranceCm = 2.0e-5;
constexpr double kBiThicknessCm = 0.4796;
constexpr double kRingPathDeltaCm = -0.4;
constexpr double kBiX0 = -3.8;
constexpr double kBiX1 = 4.0;
constexpr double kBiLowerZ = -2.39;

const char* kBiVolume = "SG3_Bi_MXC_TES_ShadowUmbrella_4p796mm";
const char* kRingVolume = "SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm";
const char* kOldDiskVolume = "Cu_SubstrateSupport_SolidDisk_L0_deepest";

struct Ray {
  std::size_t id = 0;
  std::array<double, 3> point{};
  std::array<double, 3> direction{};
};

struct Stats {
  std::size_t count = 0;
  long double sum = 0.0L;
  double minimum = std::numeric_limits<double>::infinity();
  double maximum = -std::numeric_limits<double>::infinity();
  void Add(double value) {
    ++count;
    sum += value;
    minimum = std::min(minimum, value);
    maximum = std::max(maximum, value);
  }
  double Mean() const {
    return count == 0 ? std::numeric_limits<double>::quiet_NaN()
                      : static_cast<double>(sum / count);
  }
};

std::string Trim(const std::string& input) {
  std::size_t first = 0;
  while (first < input.size() && std::isspace(static_cast<unsigned char>(input[first]))) ++first;
  std::size_t last = input.size();
  while (last > first && std::isspace(static_cast<unsigned char>(input[last - 1]))) --last;
  return input.substr(first, last - first);
}

bool ParseDouble(const std::string& text, double& value) {
  const std::string stripped = Trim(text);
  char* end = nullptr;
  errno = 0;
  value = std::strtod(stripped.c_str(), &end);
  return errno == 0 && end != stripped.c_str() && *end == '\0' && std::isfinite(value);
}

MVector InstrumentToWorld(double x, double y, double z) {
  const double angle = kRotationYDeg * std::acos(-1.0) / 180.0;
  const double c = std::cos(angle);
  const double s = std::sin(angle);
  return MVector(c * x + s * z, y, -s * x + c * z);
}

std::array<double, 3> WorldToInstrument(double x, double y, double z) {
  const double angle = kRotationYDeg * std::acos(-1.0) / 180.0;
  const double c = std::cos(angle);
  const double s = std::sin(angle);
  return {{c * x - s * z, y, s * x + c * z}};
}

std::array<double, 3> AtX(const Ray& ray, double x) {
  const double t = (x - ray.point[0]) / ray.direction[0];
  return {{x, ray.point[1] + t * ray.direction[1],
           ray.point[2] + t * ray.direction[2]}};
}

bool SequenceHas(const MDVolumeSequence& sequence, const std::string& name) {
  for (unsigned int index = 0; index < sequence.GetNVolumes(); ++index) {
    MDVolume* volume = sequence.GetVolumeAt(index);
    if (volume != nullptr && volume->GetName().GetString() == name) return true;
  }
  return false;
}

bool DeepestIs(const MDVolumeSequence& sequence, const std::string& name) {
  MDVolume* deepest = sequence.GetDeepestVolume();
  return deepest != nullptr && deepest->GetName().GetString() == name;
}

std::vector<Ray> ReadRays(const std::string& path, std::vector<std::string>& errors) {
  std::ifstream input(path);
  std::vector<Ray> rays;
  if (!input) {
    errors.push_back("unable to open EventList: " + path);
    return rays;
  }
  std::string line;
  std::size_t physical = 0;
  while (std::getline(input, line)) {
    ++physical;
    const std::string stripped = Trim(line);
    if (stripped.empty() || stripped[0] == '#') continue;
    std::istringstream stream(stripped);
    std::vector<double> values;
    std::string token;
    bool valid = true;
    while (stream >> token) {
      double value = 0.0;
      if (!ParseDouble(token, value)) {
        valid = false;
        break;
      }
      values.push_back(value);
    }
    if (!valid || values.size() != kExpectedFields) {
      errors.push_back("invalid EventList row " + std::to_string(physical));
      continue;
    }
    const long long id = std::llround(values[0]);
    if (id != static_cast<long long>(rays.size()) || values[14] != 511.0) {
      errors.push_back("EventList ID/energy contract failed at row " + std::to_string(physical));
      continue;
    }
    Ray ray;
    ray.id = static_cast<std::size_t>(id);
    ray.point = WorldToInstrument(values[5], values[6], values[7]);
    ray.direction = WorldToInstrument(values[8], values[9], values[10]);
    const double norm = std::sqrt(ray.direction[0] * ray.direction[0] +
                                  ray.direction[1] * ray.direction[1] +
                                  ray.direction[2] * ray.direction[2]);
    if (std::abs(ray.point[0] - kInjectionX) > 1.0e-7 ||
        ray.direction[0] <= 0.999 || std::abs(norm - 1.0) > 1.0e-8) {
      errors.push_back("EventList coordinate contract failed at ID " + std::to_string(id));
      continue;
    }
    rays.push_back(ray);
  }
  if (rays.size() != kExpectedRows) {
    errors.push_back("EventList count=" + std::to_string(rays.size()));
  }
  return rays;
}

std::map<std::string, double> PathMap(MDGeometryQuest& geometry,
                                      const MVector& start, const MVector& stop,
                                      bool& valid) {
  std::map<std::string, double> result;
  valid = true;
  const std::map<MDMaterial*, double> native = geometry.GetPathLengths(start, stop);
  for (const auto& entry : native) {
    if (entry.first == nullptr || !std::isfinite(entry.second) || entry.second < 0.0) {
      valid = false;
      continue;
    }
    result[entry.first->GetName().GetString()] += entry.second;
  }
  return result;
}

double MaterialLength(MDGeometryQuest& geometry,
                      const std::array<double, 3>& start,
                      const std::array<double, 3>& stop,
                      const std::string& material, bool& valid) {
  const auto paths = PathMap(geometry, InstrumentToWorld(start[0], start[1], start[2]),
                             InstrumentToWorld(stop[0], stop[1], stop[2]), valid);
  const auto found = paths.find(material);
  return found == paths.end() ? 0.0 : found->second;
}

void WriteString(std::ostream& out, const std::string& value) {
  out << '"';
  for (char c : value) {
    if (c == '"' || c == '\\') out << '\\';
    if (c == '\n') out << "\\n";
    else if (c != '\r') out << c;
  }
  out << '"';
}

void WriteNumber(std::ostream& out, double value) {
  if (std::isfinite(value)) out << std::setprecision(17) << value;
  else out << "null";
}

void WriteStats(std::ostream& out, const Stats& stats) {
  out << "{\"count\":" << stats.count << ",\"min\":";
  WriteNumber(out, stats.count ? stats.minimum : std::numeric_limits<double>::quiet_NaN());
  out << ",\"mean\":";
  WriteNumber(out, stats.Mean());
  out << ",\"max\":";
  WriteNumber(out, stats.count ? stats.maximum : std::numeric_limits<double>::quiet_NaN());
  out << "}";
}

int Run(const char* sf3_setup_arg, const char* sg3_setup_arg,
        const char* eventlist_arg, const char* output_arg) {
  const std::string sf3_setup = sf3_setup_arg ? sf3_setup_arg : "";
  const std::string sg3_setup = sg3_setup_arg ? sg3_setup_arg : "";
  const std::string eventlist = eventlist_arg ? eventlist_arg : "";
  const std::string output = output_arg ? output_arg : "";
  std::vector<std::string> errors;
  const bool initialized = MGlobal::Initialize(
      "SG3NativeNavigationAudit", "SF3/SG3 frozen-bank geometry-only comparison");
  if (!initialized) errors.push_back("MGlobal::Initialize returned false");
  const std::vector<Ray> rays = ReadRays(eventlist, errors);

  std::size_t all_non_cu_material_equal = 0;
  std::size_t no_positive_cu_delta = 0;
  std::size_t reduced_cu_rays = 0;
  std::size_t zero_bi_rays = 0;
  std::size_t zero_w_delta_rays = 0;
  std::size_t no_bi_probe_passes = 0;
  std::size_t no_bi_probe_queries = 0;
  std::size_t analytic_bi_clearance_passes = 0;
  Stats copper_delta;
  Stats bismuth_chord;
  Stats tungsten_delta;
  Stats maximum_other_material_delta;
  Stats bi_vertical_clearance;
  std::size_t witness_volume_passes = 0;
  double witness_bi_cm = 0.0;
  double witness_cu_delta_cm = 0.0;

  if (initialized && rays.size() == kExpectedRows) {
    MDGeometryQuest sf3;
    MDGeometryQuest sg3;
    if (!sf3.ScanSetupFile(MString(sf3_setup.c_str()), true, false, false)) {
      errors.push_back("failed to load SF3 setup");
    } else if (!sg3.ScanSetupFile(MString(sg3_setup.c_str()), true, false, false)) {
      errors.push_back("failed to load SG3 setup");
    } else {
      for (const Ray& ray : rays) {
        const auto stop = AtX(ray, kEndX);
        bool parent_valid = true;
        bool candidate_valid = true;
        const auto parent = PathMap(
            sf3, InstrumentToWorld(ray.point[0], ray.point[1], ray.point[2]),
            InstrumentToWorld(stop[0], stop[1], stop[2]), parent_valid);
        const auto candidate = PathMap(
            sg3, InstrumentToWorld(ray.point[0], ray.point[1], ray.point[2]),
            InstrumentToWorld(stop[0], stop[1], stop[2]), candidate_valid);
        if (!parent_valid || !candidate_valid) {
          if (errors.size() < 50) errors.push_back("invalid native path at ray " + std::to_string(ray.id));
          continue;
        }
        std::set<std::string> materials;
        for (const auto& entry : parent) materials.insert(entry.first);
        for (const auto& entry : candidate) materials.insert(entry.first);
        double max_other = 0.0;
        for (const std::string& material : materials) {
          // Removing the solid Cu centre necessarily replaces its chord with
          // inherited InstrumentFrame Vacuum.  All other materials must stay equal.
          if (material == "Copper" || material == "Bi" || material == "Vacuum") continue;
          const auto p = parent.find(material);
          const auto c = candidate.find(material);
          const double pv = p == parent.end() ? 0.0 : p->second;
          const double cv = c == candidate.end() ? 0.0 : c->second;
          max_other = std::max(max_other, std::abs(cv - pv));
        }
        maximum_other_material_delta.Add(max_other);
        if (max_other <= kToleranceCm) ++all_non_cu_material_equal;

        const double parent_cu = parent.count("Copper") ? parent.at("Copper") : 0.0;
        const double candidate_cu = candidate.count("Copper") ? candidate.at("Copper") : 0.0;
        const double cu_delta = candidate_cu - parent_cu;
        copper_delta.Add(cu_delta);
        if (cu_delta <= kToleranceCm) ++no_positive_cu_delta;
        if (cu_delta < -kToleranceCm) ++reduced_cu_rays;

        const double bi = candidate.count("Bi") ? candidate.at("Bi") : 0.0;
        bismuth_chord.Add(bi);
        if (std::abs(bi) <= kToleranceCm) ++zero_bi_rays;
        const double parent_w = parent.count("W") ? parent.at("W") : 0.0;
        const double candidate_w = candidate.count("W") ? candidate.at("W") : 0.0;
        tungsten_delta.Add(candidate_w - parent_w);
        if (std::abs(candidate_w - parent_w) <= kToleranceCm) ++zero_w_delta_rays;

        const auto z0 = AtX(ray, kBiX0);
        const auto z1 = AtX(ray, kBiX1);
        const double clearance = kBiLowerZ - std::max(z0[2], z1[2]);
        bi_vertical_clearance.Add(clearance);
        if (clearance > 0.0) ++analytic_bi_clearance_passes;
        for (double x : {-3.0, 0.1, 3.9}) {
          ++no_bi_probe_queries;
          const auto point = AtX(ray, x);
          const auto sequence = sg3.GetVolumeSequence(
              InstrumentToWorld(point[0], point[1], point[2]));
          if (!SequenceHas(sequence, kBiVolume)) ++no_bi_probe_passes;
          else if (errors.size() < 50) errors.push_back("focused ray enters Bi at ID " + std::to_string(ray.id));
        }
      }

      const auto parent_bi_seq = sf3.GetVolumeSequence(InstrumentToWorld(0.1, 0.0, -2.1502));
      const auto candidate_bi_seq = sg3.GetVolumeSequence(InstrumentToWorld(0.1, 0.0, -2.1502));
      if (!SequenceHas(parent_bi_seq, kBiVolume) && DeepestIs(candidate_bi_seq, kBiVolume)) {
        ++witness_volume_passes;
      } else errors.push_back("Bi volume witness failed");

      const auto parent_ring_seq = sf3.GetVolumeSequence(InstrumentToWorld(3.42, 2.3, -5.2));
      const auto candidate_ring_seq = sg3.GetVolumeSequence(InstrumentToWorld(3.42, 2.3, -5.2));
      if (!SequenceHas(parent_ring_seq, kRingVolume) && DeepestIs(candidate_ring_seq, kRingVolume)) {
        ++witness_volume_passes;
      } else errors.push_back("Cu ring volume witness failed");

      const auto parent_hole_seq = sf3.GetVolumeSequence(InstrumentToWorld(3.42, 0.0, -5.2));
      const auto candidate_hole_seq = sg3.GetVolumeSequence(InstrumentToWorld(3.42, 0.0, -5.2));
      if (SequenceHas(parent_hole_seq, kOldDiskVolume) &&
          !SequenceHas(candidate_hole_seq, kRingVolume)) {
        ++witness_volume_passes;
      } else errors.push_back("Cu ring center-opening witness failed");

      bool sf3_valid = true;
      bool sg3_valid = true;
      witness_bi_cm = MaterialLength(
          sg3, {{0.1, 0.0, -2.6}}, {{0.1, 0.0, -1.7}}, "Bi", sg3_valid);
      const double parent_cu = MaterialLength(
          sf3, {{3.42, -3.0, -5.2}}, {{3.42, 3.0, -5.2}}, "Copper", sf3_valid);
      const double candidate_cu = MaterialLength(
          sg3, {{3.42, -3.0, -5.2}}, {{3.42, 3.0, -5.2}}, "Copper", sg3_valid);
      witness_cu_delta_cm = candidate_cu - parent_cu;
      if (!sf3_valid || !sg3_valid || std::abs(witness_bi_cm - kBiThicknessCm) > kToleranceCm) {
        errors.push_back("Bi thickness witness failed");
      }
      if (std::abs(witness_cu_delta_cm - kRingPathDeltaCm) > kToleranceCm) {
        errors.push_back("Cu ring path witness failed");
      }
    }
  }

  const bool passed = errors.empty() && rays.size() == kExpectedRows &&
      all_non_cu_material_equal == kExpectedRows &&
      no_positive_cu_delta == kExpectedRows && reduced_cu_rays > 0 &&
      zero_bi_rays == kExpectedRows && zero_w_delta_rays == kExpectedRows &&
      analytic_bi_clearance_passes == kExpectedRows &&
      no_bi_probe_passes == no_bi_probe_queries &&
      no_bi_probe_queries == 3 * kExpectedRows && witness_volume_passes == 3;

  std::ofstream out(output, std::ios::out | std::ios::trunc);
  if (!out) return 2;
  out << "{\n\"status\":\"" << (passed ? "PASS" : "FAIL")
      << "\",\n\"transport_launched\":false,\n\"engine\":\"MEGAlib MDGeometryQuest\",";
  out << "\n\"rows\":" << rays.size();
  out << ",\n\"material_path_contract\":{\"tolerance_cm\":" << kToleranceCm
      << ",\"all_non_Cu_non_Vacuum_material_equal_rays\":" << all_non_cu_material_equal
      << ",\"maximum_other_material_delta_cm\":";
  WriteStats(out, maximum_other_material_delta);
  out << ",\"no_positive_Cu_delta_rays\":" << no_positive_cu_delta
      << ",\"reduced_Cu_rays\":" << reduced_cu_rays
      << ",\"sg3_minus_sf3_Cu_cm\":";
  WriteStats(out, copper_delta);
  out << ",\"zero_Bi_chord_rays\":" << zero_bi_rays << ",\"Bi_chord_cm\":";
  WriteStats(out, bismuth_chord);
  out << ",\"zero_W_delta_rays\":" << zero_w_delta_rays
      << ",\"sg3_minus_sf3_W_cm\":";
  WriteStats(out, tungsten_delta);
  out << "}";
  out << ",\n\"bi_focused_clearance\":{\"analytic_passes\":"
      << analytic_bi_clearance_passes << ",\"vertical_clearance_cm\":";
  WriteStats(out, bi_vertical_clearance);
  out << ",\"native_queries\":" << no_bi_probe_queries
      << ",\"native_no_Bi_passes\":" << no_bi_probe_passes << "}";
  out << ",\n\"presence_witnesses\":{\"volume_passes\":" << witness_volume_passes
      << ",\"Bi_thickness_cm\":" << std::setprecision(17) << witness_bi_cm
      << ",\"ring_minus_disk_Cu_path_cm\":" << witness_cu_delta_cm << "}";
  out << ",\n\"error_count\":" << errors.size() << ",\n\"errors\":[";
  for (std::size_t i = 0; i < errors.size() && i < 50; ++i) {
    if (i != 0) out << ',';
    WriteString(out, errors[i]);
  }
  out << "]\n}\n";
  out.flush();
  return passed ? 0 : 1;
}

}  // namespace

void sg3_native_navigation_audit(const char* sf3_setup, const char* sg3_setup,
                                 const char* eventlist, const char* output_json) {
  gSystem->Exit(Run(sf3_setup, sg3_setup, eventlist, output_json));
}
