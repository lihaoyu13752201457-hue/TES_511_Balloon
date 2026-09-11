// Native SE3/SF3 full-envelope geometry comparison.  No transport is launched.

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
constexpr double kMaterialToleranceCm = 2.0e-5;
constexpr double kZeroWDeltaToleranceCm = 2.0e-5;
constexpr double kWitnessToleranceCm = 2.0e-5;
constexpr double kExpectedWitnessW = 0.29;
constexpr double kWindowHalf = 1.9;
constexpr double kCenterZ = -5.2;
constexpr double kSideInnerRadius = 4.205;
constexpr double kRearInnerRadius = 1.85;
constexpr double kFrontX0 = -4.6475;
constexpr double kFrontX1 = -4.3575;
constexpr double kSideX0 = -4.3575;
constexpr double kSideX1 = 4.305;
constexpr double kRearX0 = 4.305;
constexpr double kRearX1 = 4.595;

const char* kFrontVolume = "SF3_W_NearField_FrontWindowPlate_2p9mm";
const char* kSideVolume = "SF3_W_NearField_SideSleeve_2p9mm";
const char* kRearVolume = "SF3_W_NearField_RearColdFingerAnnulus_2p9mm";

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

struct GeometryPaths {
  bool loaded = false;
  std::vector<std::map<std::string, double>> paths;
};

struct Sf3RayAudit {
  std::size_t front_clearance_passes = 0;
  std::size_t side_clearance_passes = 0;
  std::size_t rear_clearance_passes = 0;
  std::size_t native_no_sf3_volume_queries = 0;
  std::size_t native_no_sf3_volume_passes = 0;
  Stats front_square_clearance_cm;
  Stats side_radial_clearance_cm;
  Stats rear_radial_clearance_cm;
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

double RadiusAboutTesAxis(const std::array<double, 3>& point) {
  return std::hypot(point[1], point[2] - kCenterZ);
}

bool SequenceHas(const MDVolumeSequence& sequence, const std::string& name) {
  for (unsigned int index = 0; index < sequence.GetNVolumes(); ++index) {
    MDVolume* volume = sequence.GetVolumeAt(index);
    if (volume != nullptr && volume->GetName().GetString() == name) return true;
  }
  return false;
}

bool SequenceHasAnySf3(const MDVolumeSequence& sequence) {
  return SequenceHas(sequence, kFrontVolume) || SequenceHas(sequence, kSideVolume) ||
         SequenceHas(sequence, kRearVolume);
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
    errors.push_back("EventList count=" + std::to_string(rays.size()) +
                     " expected=" + std::to_string(kExpectedRows));
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

GeometryPaths CollectPaths(MDGeometryQuest& geometry, const std::vector<Ray>& rays,
                           std::vector<std::string>& errors) {
  GeometryPaths output;
  output.loaded = true;
  output.paths.reserve(rays.size());
  for (const Ray& ray : rays) {
    const std::array<double, 3> stop = AtX(ray, kEndX);
    bool valid = true;
    output.paths.push_back(PathMap(
        geometry,
        InstrumentToWorld(ray.point[0], ray.point[1], ray.point[2]),
        InstrumentToWorld(stop[0], stop[1], stop[2]), valid));
    if (!valid && errors.size() < 50) {
      errors.push_back("invalid material path map at ray " + std::to_string(ray.id));
    }
  }
  return output;
}

Sf3RayAudit AuditSf3Apertures(MDGeometryQuest& geometry,
                              const std::vector<Ray>& rays,
                              std::vector<std::string>& errors) {
  Sf3RayAudit audit;
  for (const Ray& ray : rays) {
    const auto front0 = AtX(ray, kFrontX0);
    const auto front1 = AtX(ray, kFrontX1);
    const double front_clearance = kWindowHalf - std::max(
        std::max(std::abs(front0[1]), std::abs(front1[1])),
        std::max(std::abs(front0[2] - kCenterZ), std::abs(front1[2] - kCenterZ)));
    audit.front_square_clearance_cm.Add(front_clearance);
    if (front_clearance > 0.0) ++audit.front_clearance_passes;

    const auto side0 = AtX(ray, kSideX0);
    const auto side1 = AtX(ray, kSideX1);
    const double side_clearance =
        kSideInnerRadius - std::max(RadiusAboutTesAxis(side0), RadiusAboutTesAxis(side1));
    audit.side_radial_clearance_cm.Add(side_clearance);
    if (side_clearance > 0.0) ++audit.side_clearance_passes;

    const auto rear0 = AtX(ray, kRearX0);
    const auto rear1 = AtX(ray, kRearX1);
    const double rear_clearance =
        kRearInnerRadius - std::max(RadiusAboutTesAxis(rear0), RadiusAboutTesAxis(rear1));
    audit.rear_radial_clearance_cm.Add(rear_clearance);
    if (rear_clearance > 0.0) ++audit.rear_clearance_passes;

    for (double x : {0.5 * (kFrontX0 + kFrontX1),
                     0.5 * (kSideX0 + kSideX1),
                     0.5 * (kRearX0 + kRearX1)}) {
      ++audit.native_no_sf3_volume_queries;
      const auto point = AtX(ray, x);
      const MDVolumeSequence sequence = geometry.GetVolumeSequence(
          InstrumentToWorld(point[0], point[1], point[2]));
      if (!SequenceHasAnySf3(sequence)) {
        ++audit.native_no_sf3_volume_passes;
      } else if (errors.size() < 50) {
        errors.push_back("focused ray enters an SF3 W volume at ID " +
                         std::to_string(ray.id));
      }
    }
  }
  return audit;
}

double MaterialLength(MDGeometryQuest& geometry,
                      const std::array<double, 3>& start,
                      const std::array<double, 3>& stop,
                      const std::string& material,
                      bool& valid) {
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

int Run(const char* se3_setup_arg, const char* sf3_setup_arg,
        const char* eventlist_arg, const char* output_arg) {
  const std::string se3_setup = se3_setup_arg ? se3_setup_arg : "";
  const std::string sf3_setup = sf3_setup_arg ? sf3_setup_arg : "";
  const std::string eventlist = eventlist_arg ? eventlist_arg : "";
  const std::string output = output_arg ? output_arg : "";
  std::vector<std::string> errors;
  const bool global_initialized = MGlobal::Initialize(
      "SF3NativeNavigationAudit", "SE3/SF3 frozen-bank geometry-only comparison");
  if (!global_initialized) errors.push_back("MGlobal::Initialize returned false");
  const std::vector<Ray> rays = ReadRays(eventlist, errors);

  GeometryPaths se3_paths;
  GeometryPaths sf3_paths;
  Sf3RayAudit ray_audit;
  std::size_t witness_volume_passes = 0;
  std::array<double, 3> witness_deltas{{0.0, 0.0, 0.0}};
  if (global_initialized && rays.size() == kExpectedRows) {
    MDGeometryQuest se3;
    if (!se3.ScanSetupFile(MString(se3_setup.c_str()), true, false, false)) {
      errors.push_back("failed to load SE3 setup");
    } else {
      se3_paths = CollectPaths(se3, rays, errors);
      MDGeometryQuest sf3;
      if (!sf3.ScanSetupFile(MString(sf3_setup.c_str()), true, false, false)) {
        errors.push_back("failed to load SF3 setup");
      } else {
        sf3_paths = CollectPaths(sf3, rays, errors);
        ray_audit = AuditSf3Apertures(sf3, rays, errors);

        const std::array<std::array<double, 3>, 3> witness_points = {{{{-4.5025, 0.0, -2.2}},
                                                                      {{0.0, 4.35, -5.2}},
                                                                      {{4.45, 3.0, -5.2}}}};
        const std::array<std::string, 3> witness_names = {{kFrontVolume, kSideVolume, kRearVolume}};
        for (std::size_t i = 0; i < witness_points.size(); ++i) {
          const auto& p = witness_points[i];
          const MDVolumeSequence base_seq = se3.GetVolumeSequence(InstrumentToWorld(p[0], p[1], p[2]));
          const MDVolumeSequence candidate_seq = sf3.GetVolumeSequence(InstrumentToWorld(p[0], p[1], p[2]));
          if (!SequenceHasAnySf3(base_seq) && SequenceHas(candidate_seq, witness_names[i]) &&
              DeepestIs(candidate_seq, witness_names[i])) {
            ++witness_volume_passes;
          } else {
            errors.push_back("native witness volume failed: " + witness_names[i]);
          }
        }

        const std::array<std::array<double, 3>, 3> witness_start = {{{{-4.8, 0.0, -2.2}},
                                                                      {{0.0, 4.7, -5.2}},
                                                                      {{4.15, 3.0, -5.2}}}};
        const std::array<std::array<double, 3>, 3> witness_stop = {{{{-4.2, 0.0, -2.2}},
                                                                     {{0.0, 4.0, -5.2}},
                                                                     {{4.75, 3.0, -5.2}}}};
        for (std::size_t i = 0; i < 3; ++i) {
          bool base_valid = true;
          bool sf3_valid = true;
          const double base_w = MaterialLength(se3, witness_start[i], witness_stop[i], "W", base_valid);
          const double sf3_w = MaterialLength(sf3, witness_start[i], witness_stop[i], "W", sf3_valid);
          witness_deltas[i] = sf3_w - base_w;
          if (!base_valid || !sf3_valid ||
              std::abs(witness_deltas[i] - kExpectedWitnessW) > kWitnessToleranceCm) {
            errors.push_back("W thickness witness failed at index " + std::to_string(i));
          }
        }
      }
    }
  }

  std::size_t path_equal_rays = 0;
  std::size_t zero_added_w_rays = 0;
  Stats maximum_material_delta_per_ray;
  Stats added_w_delta_cm;
  if (se3_paths.paths.size() == kExpectedRows && sf3_paths.paths.size() == kExpectedRows) {
    for (std::size_t i = 0; i < kExpectedRows; ++i) {
      std::set<std::string> materials;
      for (const auto& entry : se3_paths.paths[i]) materials.insert(entry.first);
      for (const auto& entry : sf3_paths.paths[i]) materials.insert(entry.first);
      double max_delta = 0.0;
      for (const std::string& material : materials) {
        const auto base_it = se3_paths.paths[i].find(material);
        const auto sf3_it = sf3_paths.paths[i].find(material);
        const double base = base_it == se3_paths.paths[i].end() ? 0.0 : base_it->second;
        const double candidate = sf3_it == sf3_paths.paths[i].end() ? 0.0 : sf3_it->second;
        max_delta = std::max(max_delta, std::abs(candidate - base));
      }
      maximum_material_delta_per_ray.Add(max_delta);
      if (max_delta <= kMaterialToleranceCm) ++path_equal_rays;
      const auto base_w_it = se3_paths.paths[i].find("W");
      const auto sf3_w_it = sf3_paths.paths[i].find("W");
      const double base_w = base_w_it == se3_paths.paths[i].end() ? 0.0 : base_w_it->second;
      const double candidate_w = sf3_w_it == sf3_paths.paths[i].end() ? 0.0 : sf3_w_it->second;
      const double delta_w = candidate_w - base_w;
      added_w_delta_cm.Add(delta_w);
      if (std::abs(delta_w) <= kZeroWDeltaToleranceCm) ++zero_added_w_rays;
    }
  }

  const bool passed = errors.empty() && se3_paths.loaded && sf3_paths.loaded &&
      path_equal_rays == kExpectedRows && zero_added_w_rays == kExpectedRows &&
      ray_audit.front_clearance_passes == kExpectedRows &&
      ray_audit.side_clearance_passes == kExpectedRows &&
      ray_audit.rear_clearance_passes == kExpectedRows &&
      ray_audit.native_no_sf3_volume_passes == 3 * kExpectedRows &&
      witness_volume_passes == 3;

  std::ofstream out(output, std::ios::out | std::ios::trunc);
  if (!out) return 2;
  out << "{\n\"status\":\"" << (passed ? "PASS" : "FAIL")
      << "\",\n\"transport_launched\":false,\n\"engine\":\"MEGAlib MDGeometryQuest\","
      << "\n\"rows\":" << rays.size()
      << ",\n\"coordinate_contract\":{\"instrument_rotation_y_deg\":45,"
         "\"world_plus_Z\":\"sky/up\",\"sky_facing_axis\":\"-xprime\","
         "\"focused_direction\":\"+xprime\",\"injection_xprime_cm\":-30.0001},"
      << "\n\"full_path_material_comparison\":{\"end_xprime_cm\":" << kEndX
      << ",\"tolerance_cm\":" << kMaterialToleranceCm
      << ",\"equal_rays\":" << path_equal_rays
      << ",\"maximum_absolute_material_delta_per_ray_cm\":";
  WriteStats(out, maximum_material_delta_per_ray);
  out << "},\n\"added_W_focused_chord\":{\"zero_tolerance_cm\":"
      << kZeroWDeltaToleranceCm << ",\"zero_rays\":" << zero_added_w_rays
      << ",\"sf3_minus_se3_cm\":";
  WriteStats(out, added_w_delta_cm);
  out << "},\n\"analytic_clearance\":{\"front_square\":{\"passes\":"
      << ray_audit.front_clearance_passes << ",\"clearance_cm\":";
  WriteStats(out, ray_audit.front_square_clearance_cm);
  out << "},\"side_inner_radius\":{\"passes\":" << ray_audit.side_clearance_passes
      << ",\"clearance_cm\":";
  WriteStats(out, ray_audit.side_radial_clearance_cm);
  out << "},\"rear_service_aperture\":{\"passes\":"
      << ray_audit.rear_clearance_passes << ",\"clearance_cm\":";
  WriteStats(out, ray_audit.rear_radial_clearance_cm);
  out << "}},\n\"native_focused_volume_probes\":{\"queries\":"
      << ray_audit.native_no_sf3_volume_queries << ",\"no_SF3_W_passes\":"
      << ray_audit.native_no_sf3_volume_passes << "},"
      << "\n\"W_presence_witnesses\":{\"volume_passes\":" << witness_volume_passes
      << ",\"expected_thickness_cm\":" << kExpectedWitnessW << ",\"delta_W_cm\":["
      << witness_deltas[0] << "," << witness_deltas[1] << "," << witness_deltas[2]
      << "]},\n\"error_count\":" << errors.size() << ",\n\"errors\":[";
  for (std::size_t i = 0; i < errors.size() && i < 50; ++i) {
    if (i != 0) out << ',';
    WriteString(out, errors[i]);
  }
  out << "]\n}\n";
  out.flush();
  return passed ? 0 : 1;
}

}  // namespace

void sf3_native_navigation_audit(const char* se3_setup, const char* sf3_setup,
                                 const char* eventlist, const char* output_json) {
  gSystem->Exit(Run(se3_setup, sf3_setup, eventlist, output_json));
}
