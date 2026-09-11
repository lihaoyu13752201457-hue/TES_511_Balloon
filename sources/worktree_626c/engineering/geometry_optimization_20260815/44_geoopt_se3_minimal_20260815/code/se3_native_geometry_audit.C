// Native MEGAlib geometry/navigation audit for the SE3 minimal geometry.
//
// This is intentionally a geometry-only check.  It loads the .geo.setup with
// MDGeometryQuest, queries the native navigator for every accepted cold-plate
// hole, and uses MDGeometryQuest::GetPathLengths for the pinned optics
// EventList.  It does not construct a source or launch particle transport.

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
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

constexpr std::size_t kExpectedEventCount = 37194;
constexpr double kInstrumentRotationDeg = 45.0;
constexpr double kEventInputPlaneX = -13.1;
constexpr double kSegmentStartX = -35.0;
constexpr double kSegmentStopX = -10.0;
constexpr double kApertureHalfWidth = 1.898;
constexpr double kApertureCenterZ = -5.2;
constexpr double kBpeOuterRadius = 29.0;
constexpr double kBpeInnerRadius = 27.0;
constexpr double kBpeZeroTolerance = 1.0e-9;
constexpr double kPlasticPositiveTolerance = 1.0e-9;
constexpr double kHoleProbeOffsetZ = 0.199;
constexpr double kRequiredSolidMargin = 0.2;
constexpr double kWebProbeDepth = 0.1;
constexpr std::size_t kExpectedHolesPerPlate = 48;
constexpr std::size_t kExpectedHoleCount = 240;
constexpr std::size_t kMaxFailureSamples = 50;

const char* kBpeMaterial = "BoratedPolyethylene5wtB";
const char* kPlasticMaterial = "PlasticScintillator";

struct PlateSpec {
  std::string key;
  std::string volume;
  std::string material;
  double radius = 0.0;
  double z = 0.0;
};

const std::array<PlateSpec, 5> kPlateSpecs = {{
    {"MXC_50mK", "ColdPlate_MXC_50mK_SD_anchor", "Copper", 15.0, 0.0},
    {"CP_100mK", "ColdPlate_CP_100mK_intercept", "Copper", 15.0, 5.0},
    {"Still_0p7K", "ColdPlate_Still_0p7K", "Copper", 15.0, 11.0},
    {"4K", "ColdPlate_4K", "Copper", 17.5, 20.0},
    {"60K", "ColdPlate_60K", "Aluminium", 17.5, 29.0},
}};

struct HoleRow {
  std::size_t csv_line = 0;
  std::string plate_key;
  std::string plate_volume;
  std::string plate_material;
  std::string copy_name;
  double plate_radius = 0.0;
  double plate_z = 0.0;
  double x = 0.0;
  double y = 0.0;
  double hole_radius = 0.0;
  double edge_solid = 0.0;
  double keepout_clearance = 0.0;
  double nearest_hole_web = 0.0;
};

struct Failure {
  std::string check;
  std::string item;
  std::string detail;
};

struct RunningStats {
  std::size_t count = 0;
  long double sum = 0.0L;
  double minimum = std::numeric_limits<double>::infinity();
  double maximum = -std::numeric_limits<double>::infinity();

  void Add(double value) {
    ++count;
    sum += static_cast<long double>(value);
    minimum = std::min(minimum, value);
    maximum = std::max(maximum, value);
  }

  double Mean() const {
    return count == 0 ? std::numeric_limits<double>::quiet_NaN()
                      : static_cast<double>(sum / static_cast<long double>(count));
  }
};

struct PlateAudit {
  std::size_t accepted_holes = 0;
  std::size_t hole_probe_passes = 0;
  std::size_t web_passes = 0;
};

struct HoleAudit {
  std::size_t accepted_holes = 0;
  std::size_t hole_probe_queries = 0;
  std::size_t hole_probe_passes = 0;
  std::size_t web_holes_checked = 0;
  std::size_t web_candidate_queries = 0;
  std::size_t web_passes = 0;
  std::size_t nearest_pair_web_passes = 0;
  std::size_t outer_edge_web_passes = 0;
  std::map<std::string, PlateAudit> by_plate;
};

struct EventAudit {
  std::size_t parsed_rows = 0;
  std::size_t path_length_calls = 0;
  std::size_t bpe_zero_passes = 0;
  std::size_t plastic_positive_passes = 0;
  std::size_t analytic_clearance_passes = 0;
  std::size_t input_plane_passes = 0;
  std::size_t forward_direction_passes = 0;
  RunningStats segment_chord_cm;
  RunningStats bpe_chord_cm;
  RunningStats plastic_chord_cm;
  RunningStats aperture_clearance_cm;
  RunningStats aperture_y_clearance_cm;
  RunningStats aperture_z_clearance_cm;
};

std::string Trim(const std::string& input) {
  std::size_t first = 0;
  while (first < input.size() &&
         (input[first] == ' ' || input[first] == '\t' || input[first] == '\r' ||
          input[first] == '\n')) {
    ++first;
  }
  std::size_t last = input.size();
  while (last > first &&
         (input[last - 1] == ' ' || input[last - 1] == '\t' ||
          input[last - 1] == '\r' || input[last - 1] == '\n')) {
    --last;
  }
  return input.substr(first, last - first);
}

bool ParseFiniteDouble(const std::string& text, double& value) {
  const std::string stripped = Trim(text);
  if (stripped.empty()) return false;
  char* end = nullptr;
  errno = 0;
  value = std::strtod(stripped.c_str(), &end);
  if (errno != 0 || end == stripped.c_str() || *end != '\0' || !std::isfinite(value)) {
    return false;
  }
  return true;
}

bool ParseCsvLine(const std::string& line, std::vector<std::string>& fields,
                  std::string& error) {
  fields.clear();
  std::string field;
  bool quoted = false;
  bool field_started = false;
  for (std::size_t i = 0; i < line.size(); ++i) {
    const char c = line[i];
    if (quoted) {
      if (c == '"') {
        if (i + 1 < line.size() && line[i + 1] == '"') {
          field.push_back('"');
          ++i;
        } else {
          quoted = false;
        }
      } else {
        field.push_back(c);
      }
      continue;
    }
    if (c == ',') {
      fields.push_back(field);
      field.clear();
      field_started = false;
    } else if (c == '"') {
      if (field_started || !field.empty()) {
        error = "quote inside unquoted CSV field";
        return false;
      }
      quoted = true;
      field_started = true;
    } else if (c != '\r') {
      field.push_back(c);
      field_started = true;
    }
  }
  if (quoted) {
    error = "unterminated quoted CSV field";
    return false;
  }
  fields.push_back(field);
  return true;
}

const PlateSpec* FindPlate(const std::string& key) {
  for (const PlateSpec& plate : kPlateSpecs) {
    if (plate.key == key) return &plate;
  }
  return nullptr;
}

void AddFailure(std::vector<Failure>& failures, std::size_t& total,
                const std::string& check, const std::string& item,
                const std::string& detail) {
  ++total;
  if (failures.size() < kMaxFailureSamples) {
    failures.push_back({check, item, detail});
  }
}

bool LoadAcceptedHoles(const std::string& path, std::vector<HoleRow>& accepted,
                       std::map<std::string, std::size_t>& accepted_by_plate,
                       std::size_t& total_rows, std::size_t& keepout_skipped_rows,
                       std::size_t& selection_skipped_rows,
                       std::vector<Failure>& failures, std::size_t& failure_total) {
  std::ifstream input(path);
  if (!input) {
    AddFailure(failures, failure_total, "hole_csv_open", path,
               "unable to open the hole ledger");
    return false;
  }

  std::string line;
  if (!std::getline(input, line)) {
    AddFailure(failures, failure_total, "hole_csv_header", path,
               "hole ledger is empty");
    return false;
  }
  std::vector<std::string> header;
  std::string parse_error;
  if (!ParseCsvLine(line, header, parse_error)) {
    AddFailure(failures, failure_total, "hole_csv_header", path, parse_error);
    return false;
  }
  if (!header.empty() && header[0].size() >= 3 &&
      static_cast<unsigned char>(header[0][0]) == 0xef &&
      static_cast<unsigned char>(header[0][1]) == 0xbb &&
      static_cast<unsigned char>(header[0][2]) == 0xbf) {
    header[0].erase(0, 3);
  }

  std::map<std::string, std::size_t> column;
  for (std::size_t i = 0; i < header.size(); ++i) {
    const std::string name = Trim(header[i]);
    if (name.empty() || column.count(name) != 0) {
      AddFailure(failures, failure_total, "hole_csv_header", path,
                 "empty or duplicate header field: " + name);
      return false;
    }
    column[name] = i;
  }
  const std::array<const char*, 13> required = {{
      "status", "plate_key", "plate_volume", "plate_material",
      "plate_radius_cm", "plate_center_z_cm", "x_instrument_cm",
      "y_instrument_cm", "hole_radius_cm", "edge_solid_cm",
      "keepout_clearance_cm", "nearest_hole_web_cm", "copy_name",
  }};
  for (const char* name : required) {
    if (column.count(name) == 0) {
      AddFailure(failures, failure_total, "hole_csv_header", path,
                 std::string("missing required column: ") + name);
      return false;
    }
  }

  bool valid = true;
  std::set<std::string> copy_names;
  std::size_t csv_line = 1;
  while (std::getline(input, line)) {
    ++csv_line;
    if (Trim(line).empty()) continue;
    ++total_rows;
    std::vector<std::string> values;
    parse_error.clear();
    if (!ParseCsvLine(line, values, parse_error) || values.size() != header.size()) {
      AddFailure(failures, failure_total, "hole_csv_row",
                 "line " + std::to_string(csv_line),
                 parse_error.empty() ? "field count does not match header" : parse_error);
      valid = false;
      continue;
    }
    auto Get = [&](const char* name) -> std::string {
      return Trim(values[column.at(name)]);
    };
    const std::string status = Get("status");
    const std::string key = Get("plate_key");
    const PlateSpec* plate = FindPlate(key);
    if (status != "ACCEPTED" && status != "SKIPPED_KEEP_OUT" &&
        status != "SKIPPED_EQUIVALENT_48_SELECTION") {
      AddFailure(failures, failure_total, "hole_csv_status",
                 "line " + std::to_string(csv_line), "unexpected status: " + status);
      valid = false;
      continue;
    }
    if (plate == nullptr) {
      AddFailure(failures, failure_total, "hole_csv_plate",
                 "line " + std::to_string(csv_line), "unknown plate_key: " + key);
      valid = false;
      continue;
    }
    double radius = 0.0;
    double z = 0.0;
    double x = 0.0;
    double y = 0.0;
    double hole_radius = 0.0;
    if (!ParseFiniteDouble(Get("plate_radius_cm"), radius) ||
        !ParseFiniteDouble(Get("plate_center_z_cm"), z) ||
        !ParseFiniteDouble(Get("x_instrument_cm"), x) ||
        !ParseFiniteDouble(Get("y_instrument_cm"), y) ||
        !ParseFiniteDouble(Get("hole_radius_cm"), hole_radius) ||
        !(hole_radius > 0.0)) {
      AddFailure(failures, failure_total, "hole_csv_numeric",
                 "line " + std::to_string(csv_line), "invalid finite coordinate or plate value");
      valid = false;
      continue;
    }
    const std::string volume = Get("plate_volume");
    const std::string material = Get("plate_material");
    const std::string copy = Get("copy_name");
    if (volume != plate->volume || material != plate->material ||
        std::abs(radius - plate->radius) > 1.0e-10 ||
        std::abs(z - plate->z) > 1.0e-10) {
      AddFailure(failures, failure_total, "hole_csv_plate_contract",
                 "line " + std::to_string(csv_line),
                 "plate metadata disagrees with the locked SE3 plate table");
      valid = false;
      continue;
    }
    if (std::hypot(x, y) >
        radius - hole_radius - kRequiredSolidMargin + 1.0e-9) {
      AddFailure(failures, failure_total, "hole_csv_edge_rule",
                 "line " + std::to_string(csv_line),
                 "candidate center violates the dynamic radius + 0.2 cm edge rule");
      valid = false;
      continue;
    }

    if (status != "ACCEPTED") {
      if (status == "SKIPPED_KEEP_OUT") {
        ++keepout_skipped_rows;
      } else {
        ++selection_skipped_rows;
      }
      if (!copy.empty()) {
        AddFailure(failures, failure_total, "hole_csv_skipped_copy",
                   "line " + std::to_string(csv_line),
                   "skipped keep-out row has a non-empty copy_name");
        valid = false;
      }
      continue;
    }

    double edge_solid = 0.0;
    double keepout_clearance = 0.0;
    double nearest_hole_web = 0.0;
    if (!ParseFiniteDouble(Get("edge_solid_cm"), edge_solid) ||
        !ParseFiniteDouble(Get("keepout_clearance_cm"), keepout_clearance) ||
        !ParseFiniteDouble(Get("nearest_hole_web_cm"), nearest_hole_web) ||
        edge_solid < kRequiredSolidMargin - 1.0e-9 ||
        keepout_clearance < kRequiredSolidMargin - 1.0e-9 ||
        nearest_hole_web < kRequiredSolidMargin - 1.0e-9) {
      AddFailure(failures, failure_total, "hole_csv_clearance_contract",
                 "line " + std::to_string(csv_line),
                 "accepted equivalent hole violates a 0.2 cm edge, keep-out, or web margin");
      valid = false;
      continue;
    }

    const std::string prefix = "SE3_HOLE_" + key + "_";
    bool copy_format_ok = copy.size() == prefix.size() + 5 &&
                          copy.compare(0, prefix.size(), prefix) == 0;
    if (copy_format_ok) {
      for (std::size_t i = prefix.size(); i < copy.size(); ++i) {
        if (copy[i] < '0' || copy[i] > '9') copy_format_ok = false;
      }
    }
    if (!copy_format_ok || !copy_names.insert(copy).second) {
      AddFailure(failures, failure_total, "hole_csv_copy_name",
                 "line " + std::to_string(csv_line),
                 "copy_name is malformed or duplicated: " + copy);
      valid = false;
      continue;
    }
    accepted.push_back({csv_line, key, volume, material, copy, radius, z, x, y,
                        hole_radius, edge_solid, keepout_clearance,
                        nearest_hole_web});
    ++accepted_by_plate[key];
  }

  if (total_rows == 0 || accepted.empty()) {
    AddFailure(failures, failure_total, "hole_csv_population", path,
               "ledger has no rows or no accepted holes");
    valid = false;
  }
  for (const PlateSpec& plate : kPlateSpecs) {
    if (accepted_by_plate[plate.key] != kExpectedHolesPerPlate) {
      AddFailure(failures, failure_total, "hole_csv_population", plate.key,
                 "plate does not have exactly 48 accepted equivalent-area holes");
      valid = false;
    }
  }
  if (accepted.size() != kExpectedHoleCount) {
    AddFailure(failures, failure_total, "hole_csv_population", path,
               "accepted equivalent-area hole total is not exactly 240");
    valid = false;
  }
  return valid;
}

MVector InstrumentToWorld(double x, double y, double z) {
  const double angle = kInstrumentRotationDeg * std::acos(-1.0) / 180.0;
  const double c = std::cos(angle);
  const double s = std::sin(angle);
  return MVector(c * x + s * z, y, -s * x + c * z);
}

std::array<double, 3> WorldToInstrument(double x, double y, double z) {
  const double angle = kInstrumentRotationDeg * std::acos(-1.0) / 180.0;
  const double c = std::cos(angle);
  const double s = std::sin(angle);
  return {{c * x - s * z, y, s * x + c * z}};
}

std::string SequenceDescription(const MDVolumeSequence& sequence) {
  std::ostringstream out;
  if (sequence.GetNVolumes() == 0) return "<empty>";
  for (unsigned int i = 0; i < sequence.GetNVolumes(); ++i) {
    if (i != 0) out << "/";
    MDVolume* volume = sequence.GetVolumeAt(i);
    out << (volume == nullptr ? "<null>" : volume->GetName().GetString());
  }
  return out.str();
}

bool DeepestMatches(const MDVolumeSequence& sequence, const std::string& volume_name,
                    const std::string& material_name) {
  MDVolume* deepest = sequence.GetDeepestVolume();
  if (deepest == nullptr || deepest->GetName().GetString() != volume_name ||
      deepest->GetMaterial() == nullptr) {
    return false;
  }
  return deepest->GetMaterial()->GetName().GetString() == material_name;
}

HoleAudit AuditHoles(MDGeometryQuest& geometry, const std::vector<HoleRow>& holes,
                     std::vector<Failure>& failures, std::size_t& failure_total) {
  HoleAudit audit;
  for (const PlateSpec& plate : kPlateSpecs) audit.by_plate[plate.key] = PlateAudit{};
  const std::array<double, 3> z_offsets = {{-kHoleProbeOffsetZ, 0.0, kHoleProbeOffsetZ}};

  for (const HoleRow& hole : holes) {
    ++audit.accepted_holes;
    ++audit.by_plate[hole.plate_key].accepted_holes;
    for (double dz : z_offsets) {
      ++audit.hole_probe_queries;
      const MVector world = InstrumentToWorld(hole.x, hole.y, hole.plate_z + dz);
      const MDVolumeSequence sequence = geometry.GetVolumeSequence(world);
      const bool passed =
          DeepestMatches(sequence, hole.copy_name, "Vacuum") &&
          sequence.HasVolume(MString(hole.plate_volume.c_str()));
      if (passed) {
        ++audit.hole_probe_passes;
        ++audit.by_plate[hole.plate_key].hole_probe_passes;
      } else {
        std::ostringstream detail;
        detail << "instrument point=(" << std::setprecision(12) << hole.x << ","
               << hole.y << "," << hole.plate_z + dz << "), expected deepest="
               << hole.copy_name << " material=Vacuum under " << hole.plate_volume
               << ", got " << SequenceDescription(sequence);
        AddFailure(failures, failure_total, "accepted_hole_navigation",
                   hole.copy_name, detail.str());
      }
    }

    ++audit.web_holes_checked;
    const HoleRow* nearest = nullptr;
    double nearest_distance = std::numeric_limits<double>::infinity();
    for (const HoleRow& other : holes) {
      if (&other == &hole || other.plate_key != hole.plate_key) continue;
      const double distance = std::hypot(other.x - hole.x, other.y - hole.y);
      if (distance < nearest_distance) {
        nearest_distance = distance;
        nearest = &other;
      }
    }
    bool nearest_pair_passed = false;
    bool outer_edge_passed = false;
    std::ostringstream observed;
    if (nearest == nullptr) {
      AddFailure(failures, failure_total, "nearest_hole_web", hole.copy_name,
                 "no other accepted hole exists on the plate");
    } else {
      const double computed_web =
          nearest_distance - hole.hole_radius - nearest->hole_radius;
      if (computed_web < kRequiredSolidMargin - 1.0e-9 ||
          std::abs(computed_web - hole.nearest_hole_web) > 1.0e-8) {
        std::ostringstream detail;
        detail << std::setprecision(17) << "computed nearest web=" << computed_web
               << " cm, CSV=" << hole.nearest_hole_web << " cm";
        AddFailure(failures, failure_total, "nearest_hole_web", hole.copy_name,
                   detail.str());
      }

      // Probe 1 mm into the actual nearest-pair solid gap.  Since the locked
      // gap is >=2 mm, this point is outside both Vacuum daughters.
      const double ux = (nearest->x - hole.x) / nearest_distance;
      const double uy = (nearest->y - hole.y) / nearest_distance;
      const double probe_distance = hole.hole_radius + kWebProbeDepth;
      const double gap_x = hole.x + probe_distance * ux;
      const double gap_y = hole.y + probe_distance * uy;
      ++audit.web_candidate_queries;
      const MDVolumeSequence gap_sequence = geometry.GetVolumeSequence(
          InstrumentToWorld(gap_x, gap_y, hole.plate_z));
      nearest_pair_passed =
          DeepestMatches(gap_sequence, hole.plate_volume, hole.plate_material);
      if (!nearest_pair_passed) {
        observed << "nearest-pair gap point=(" << gap_x << "," << gap_y << ")->"
                 << SequenceDescription(gap_sequence);
      } else {
        ++audit.nearest_pair_web_passes;
      }
    }

    // Independently probe 1 mm beyond the hole rim toward the plate's outer
    // edge.  The CSV contract guarantees >=2 mm solid edge and keep-out
    // clearance, so this is a second unambiguous parent-plate point.
    double radial_norm = std::hypot(hole.x, hole.y);
    const double outer_ux = radial_norm > 0.0 ? hole.x / radial_norm : 1.0;
    const double outer_uy = radial_norm > 0.0 ? hole.y / radial_norm : 0.0;
    const double outer_distance = hole.hole_radius + kWebProbeDepth;
    const double outer_x = hole.x + outer_distance * outer_ux;
    const double outer_y = hole.y + outer_distance * outer_uy;
    ++audit.web_candidate_queries;
    const MDVolumeSequence outer_sequence = geometry.GetVolumeSequence(
        InstrumentToWorld(outer_x, outer_y, hole.plate_z));
    outer_edge_passed =
        DeepestMatches(outer_sequence, hole.plate_volume, hole.plate_material);
    if (!outer_edge_passed) {
      if (observed.tellp() > 0) observed << "; ";
      observed << "outer-edge gap point=(" << outer_x << "," << outer_y << ")->"
               << SequenceDescription(outer_sequence);
    } else {
      ++audit.outer_edge_web_passes;
    }

    if (nearest_pair_passed && outer_edge_passed) {
      ++audit.web_passes;
      ++audit.by_plate[hole.plate_key].web_passes;
    } else {
      AddFailure(failures, failure_total, "adjacent_web_navigation", hole.copy_name,
                 "dynamic-radius nearest-pair/outer-edge web probe failed; " +
                     observed.str());
    }
  }
  return audit;
}

bool NegativeCylinderIntersection(const std::array<double, 3>& point,
                                  const std::array<double, 3>& direction,
                                  double radius, double t_min, double t_max,
                                  double& result) {
  const double a = direction[0] * direction[0] + direction[1] * direction[1];
  const double b = 2.0 * (point[0] * direction[0] + point[1] * direction[1]);
  const double c = point[0] * point[0] + point[1] * point[1] - radius * radius;
  if (!(a > 0.0)) return false;
  const double discriminant = b * b - 4.0 * a * c;
  if (discriminant < 0.0) return false;
  const double root = std::sqrt(std::max(0.0, discriminant));
  const std::array<double, 2> candidates = {{(-b - root) / (2.0 * a),
                                             (-b + root) / (2.0 * a)}};
  bool found = false;
  for (double candidate : candidates) {
    if (candidate < t_min - 1.0e-9 || candidate > t_max + 1.0e-9) continue;
    const double x = point[0] + candidate * direction[0];
    if (x >= 0.0) continue;
    if (!found || candidate < result) {
      result = candidate;
      found = true;
    }
  }
  return found;
}

bool AnalyticApertureClearance(const std::array<double, 3>& point,
                               const std::array<double, 3>& direction,
                               double t_min, double t_max, double& y_clearance,
                               double& z_clearance, double& clearance) {
  double outer_t = 0.0;
  double inner_t = 0.0;
  if (!NegativeCylinderIntersection(point, direction, kBpeOuterRadius, t_min, t_max,
                                    outer_t) ||
      !NegativeCylinderIntersection(point, direction, kBpeInnerRadius, t_min, t_max,
                                    inner_t)) {
    return false;
  }
  const double outer_y = point[1] + outer_t * direction[1];
  const double inner_y = point[1] + inner_t * direction[1];
  const double outer_z = point[2] + outer_t * direction[2];
  const double inner_z = point[2] + inner_t * direction[2];
  y_clearance = kApertureHalfWidth - std::max(std::abs(outer_y), std::abs(inner_y));
  z_clearance =
      kApertureHalfWidth -
      std::max(std::abs(outer_z - kApertureCenterZ),
               std::abs(inner_z - kApertureCenterZ));
  clearance = std::min(y_clearance, z_clearance);
  return std::isfinite(clearance);
}

EventAudit AuditEventList(MDGeometryQuest& geometry, const std::string& path,
                          std::vector<Failure>& failures,
                          std::size_t& failure_total) {
  EventAudit audit;
  std::ifstream input(path);
  if (!input) {
    AddFailure(failures, failure_total, "eventlist_open", path,
               "unable to open the pinned EventList");
    return audit;
  }

  std::string line;
  std::size_t physical_line = 0;
  std::size_t logical_row = 0;
  while (std::getline(input, line)) {
    ++physical_line;
    const std::string stripped = Trim(line);
    if (stripped.empty() || stripped[0] == '#') continue;

    std::istringstream stream(stripped);
    std::vector<double> values;
    std::string token;
    bool row_valid = true;
    while (stream >> token) {
      double value = 0.0;
      if (!ParseFiniteDouble(token, value)) {
        row_valid = false;
        break;
      }
      values.push_back(value);
    }
    if (!row_valid || values.size() != 15) {
      AddFailure(failures, failure_total, "eventlist_row",
                 "line " + std::to_string(physical_line),
                 "expected exactly 15 finite numeric fields");
      ++logical_row;
      continue;
    }
    const long long event_id = std::llround(values[0]);
    if (std::abs(values[0] - static_cast<double>(event_id)) > 1.0e-12 ||
        event_id != static_cast<long long>(logical_row)) {
      AddFailure(failures, failure_total, "eventlist_id",
                 "line " + std::to_string(physical_line),
                 "event IDs must be consecutive from zero");
      ++logical_row;
      continue;
    }
    ++logical_row;
    ++audit.parsed_rows;

    const std::array<double, 3> point =
        WorldToInstrument(values[5], values[6], values[7]);
    const std::array<double, 3> direction =
        WorldToInstrument(values[8], values[9], values[10]);
    const double direction_norm = std::sqrt(direction[0] * direction[0] +
                                            direction[1] * direction[1] +
                                            direction[2] * direction[2]);
    const bool input_plane_ok = std::abs(point[0] - kEventInputPlaneX) <= 1.0e-7;
    const bool forward_ok = direction[0] > 0.999 &&
                            std::abs(direction_norm - 1.0) <= 1.0e-8;
    if (input_plane_ok) {
      ++audit.input_plane_passes;
    } else {
      AddFailure(failures, failure_total, "eventlist_input_plane",
                 std::to_string(event_id), "world point does not invert to x'=-13.1 cm");
    }
    if (forward_ok) {
      ++audit.forward_direction_passes;
    } else {
      AddFailure(failures, failure_total, "eventlist_direction",
                 std::to_string(event_id), "ray is not a unit, forward +x' direction");
    }
    if (!(direction[0] > 0.0) || !std::isfinite(direction_norm)) continue;

    const double start_t = (kSegmentStartX - point[0]) / direction[0];
    const double stop_t = (kSegmentStopX - point[0]) / direction[0];
    const double t_min = std::min(start_t, stop_t);
    const double t_max = std::max(start_t, stop_t);
    const std::array<double, 3> start_local = {{
        point[0] + start_t * direction[0], point[1] + start_t * direction[1],
        point[2] + start_t * direction[2]}};
    const std::array<double, 3> stop_local = {{
        point[0] + stop_t * direction[0], point[1] + stop_t * direction[1],
        point[2] + stop_t * direction[2]}};
    const MVector start_world =
        InstrumentToWorld(start_local[0], start_local[1], start_local[2]);
    const MVector stop_world =
        InstrumentToWorld(stop_local[0], stop_local[1], stop_local[2]);

    std::map<MDMaterial*, double> lengths = geometry.GetPathLengths(start_world, stop_world);
    ++audit.path_length_calls;
    double bpe = 0.0;
    double plastic = 0.0;
    bool material_map_ok = true;
    for (const auto& entry : lengths) {
      if (entry.first == nullptr || !std::isfinite(entry.second) || entry.second < 0.0) {
        material_map_ok = false;
        continue;
      }
      const std::string material = entry.first->GetName().GetString();
      if (material == kBpeMaterial) bpe += entry.second;
      if (material == kPlasticMaterial) plastic += entry.second;
    }
    if (!material_map_ok) {
      AddFailure(failures, failure_total, "path_length_material_map",
                 std::to_string(event_id), "null material or invalid path length returned");
    }
    const double segment_chord = (stop_world - start_world).Mag();
    audit.segment_chord_cm.Add(segment_chord);
    audit.bpe_chord_cm.Add(bpe);
    audit.plastic_chord_cm.Add(plastic);
    if (std::abs(bpe) <= kBpeZeroTolerance) {
      ++audit.bpe_zero_passes;
    } else {
      std::ostringstream detail;
      detail << std::setprecision(17) << "BPE chord=" << bpe << " cm";
      AddFailure(failures, failure_total, "bpe_focused_port_path",
                 std::to_string(event_id), detail.str());
    }
    if (plastic > kPlasticPositiveTolerance) {
      ++audit.plastic_positive_passes;
    } else {
      std::ostringstream detail;
      detail << std::setprecision(17) << "plastic chord=" << plastic << " cm";
      AddFailure(failures, failure_total, "plastic_uncut_path",
                 std::to_string(event_id), detail.str());
    }

    double y_clearance = 0.0;
    double z_clearance = 0.0;
    double clearance = 0.0;
    if (AnalyticApertureClearance(point, direction, t_min, t_max, y_clearance,
                                  z_clearance, clearance)) {
      audit.aperture_y_clearance_cm.Add(y_clearance);
      audit.aperture_z_clearance_cm.Add(z_clearance);
      audit.aperture_clearance_cm.Add(clearance);
      if (clearance > 0.0) {
        ++audit.analytic_clearance_passes;
      } else {
        std::ostringstream detail;
        detail << std::setprecision(17) << "transverse clearance=" << clearance
               << " cm (y=" << y_clearance << ", z=" << z_clearance << ")";
        AddFailure(failures, failure_total, "analytic_aperture_clearance",
                   std::to_string(event_id), detail.str());
      }
    } else {
      AddFailure(failures, failure_total, "analytic_aperture_intersection",
                 std::to_string(event_id),
                 "could not intersect the negative-x' r=29 and r=27 cm shell surfaces");
    }
  }

  if (logical_row != kExpectedEventCount || audit.parsed_rows != kExpectedEventCount) {
    std::ostringstream detail;
    detail << "logical rows=" << logical_row << ", valid parsed rows=" << audit.parsed_rows
           << ", expected=" << kExpectedEventCount;
    AddFailure(failures, failure_total, "eventlist_count", path, detail.str());
  }
  return audit;
}

std::string JsonEscape(const std::string& input) {
  std::ostringstream out;
  for (unsigned char c : input) {
    switch (c) {
      case '"': out << "\\\""; break;
      case '\\': out << "\\\\"; break;
      case '\b': out << "\\b"; break;
      case '\f': out << "\\f"; break;
      case '\n': out << "\\n"; break;
      case '\r': out << "\\r"; break;
      case '\t': out << "\\t"; break;
      default:
        if (c < 0x20) {
          out << "\\u" << std::hex << std::setw(4) << std::setfill('0')
              << static_cast<int>(c) << std::dec << std::setfill(' ');
        } else {
          out << static_cast<char>(c);
        }
    }
  }
  return out.str();
}

void WriteJsonString(std::ostream& out, const std::string& value) {
  out << '"' << JsonEscape(value) << '"';
}

void WriteJsonNumberOrNull(std::ostream& out, double value) {
  if (std::isfinite(value)) {
    out << std::setprecision(17) << value;
  } else {
    out << "null";
  }
}

void WriteStats(std::ostream& out, const RunningStats& stats) {
  out << "{\"count\":" << stats.count << ",\"min\":";
  WriteJsonNumberOrNull(out, stats.count == 0 ? std::numeric_limits<double>::quiet_NaN()
                                               : stats.minimum);
  out << ",\"mean\":";
  WriteJsonNumberOrNull(out, stats.Mean());
  out << ",\"max\":";
  WriteJsonNumberOrNull(out, stats.count == 0 ? std::numeric_limits<double>::quiet_NaN()
                                               : stats.maximum);
  out << "}";
}

bool WriteReport(const std::string& output_path, bool global_initialized,
                 bool geometry_loaded, const std::string& setup_path,
                 const std::string& csv_path, const std::string& event_path,
                 std::size_t csv_rows, std::size_t keepout_skipped_rows,
                 std::size_t selection_skipped_rows,
                 const HoleAudit& holes, const EventAudit& events,
                 const std::vector<Failure>& failures,
                 std::size_t failure_total, bool passed) {
  std::ofstream out(output_path, std::ios::out | std::ios::trunc);
  if (!out) return false;
  out << "{\n";
  out << "  \"schema_version\": 1,\n";
  out << "  \"status\": \"" << (passed ? "PASS" : "FAIL") << "\",\n";
  out << "  \"engine\": \"MEGAlib MDGeometryQuest\",\n";
  out << "  \"transport_launched\": false,\n";
  out << "  \"inputs\": {\"setup\":";
  WriteJsonString(out, setup_path);
  out << ",\"hole_csv\":";
  WriteJsonString(out, csv_path);
  out << ",\"eventlist\":";
  WriteJsonString(out, event_path);
  out << "},\n";
  out << "  \"geometry_load\": {\"mglobal_initialized\":"
      << (global_initialized ? "true" : "false") << ",\"scan_setup_file\":"
      << (geometry_loaded ? "true" : "false")
      << ",\"create_nodes\":true,\"virtualize_non_detector_volumes\":false,"
         "\"allow_cross_section_creation\":false},\n";
  out << "  \"hole_navigation\": {\n";
  out << "    \"csv_candidate_rows\":" << csv_rows
      << ",\"csv_skipped_keep_out_rows\":" << keepout_skipped_rows
      << ",\"csv_skipped_equivalent_selection_rows\":" << selection_skipped_rows
      << ",\"accepted_holes\":" << holes.accepted_holes << ",\n";
  out << "    \"z_offsets_cm\":[-0.199,0,0.199],"
         "\"hole_probe_queries\":" << holes.hole_probe_queries
      << ",\"hole_probe_passes\":" << holes.hole_probe_passes << ",\n";
  out << "    \"web_probe_depth_beyond_hole_rim_cm\":" << kWebProbeDepth
      << ",\"required_solid_margin_cm\":" << kRequiredSolidMargin
      << ",\"web_holes_checked\":" << holes.web_holes_checked
      << ",\"web_candidate_queries\":" << holes.web_candidate_queries
      << ",\"nearest_pair_web_passes\":" << holes.nearest_pair_web_passes
      << ",\"outer_edge_web_passes\":" << holes.outer_edge_web_passes
      << ",\"web_passes\":" << holes.web_passes << ",\n";
  out << "    \"by_plate\":{";
  bool first_plate = true;
  for (const PlateSpec& plate : kPlateSpecs) {
    if (!first_plate) out << ",";
    first_plate = false;
    WriteJsonString(out, plate.key);
    const PlateAudit& value = holes.by_plate.at(plate.key);
    out << ":{\"accepted_holes\":" << value.accepted_holes
        << ",\"hole_probe_passes\":" << value.hole_probe_passes
        << ",\"web_passes\":" << value.web_passes << "}";
  }
  out << "}\n  },\n";
  out << "  \"eventlist_navigation\": {\n";
  out << "    \"expected_rows\":" << kExpectedEventCount
      << ",\"parsed_rows\":" << events.parsed_rows
      << ",\"get_path_lengths_calls\":" << events.path_length_calls << ",\n";
  out << "    \"instrument_frame_rotation_y_deg\":" << kInstrumentRotationDeg
      << ",\"input_plane_x_cm\":" << kEventInputPlaneX
      << ",\"segment_x_cm\":[" << kSegmentStartX << "," << kSegmentStopX << "],\n";
  out << "    \"input_plane_passes\":" << events.input_plane_passes
      << ",\"forward_direction_passes\":" << events.forward_direction_passes
      << ",\n";
  out << "    \"bpe_material\":";
  WriteJsonString(out, kBpeMaterial);
  out << ",\"bpe_zero_tolerance_cm\":" << std::setprecision(17)
      << kBpeZeroTolerance << ",\"bpe_zero_passes\":" << events.bpe_zero_passes
      << ",\"bpe_chord_cm\":";
  WriteStats(out, events.bpe_chord_cm);
  out << ",\n    \"plastic_material\":";
  WriteJsonString(out, kPlasticMaterial);
  out << ",\"plastic_positive_tolerance_cm\":" << kPlasticPositiveTolerance
      << ",\"plastic_positive_passes\":" << events.plastic_positive_passes
      << ",\"plastic_chord_cm\":";
  WriteStats(out, events.plastic_chord_cm);
  out << ",\n    \"segment_chord_cm\":";
  WriteStats(out, events.segment_chord_cm);
  out << ",\n    \"analytic_aperture\":{\"shape\":\"square BPE-only port\","
         "\"half_width_cm\":" << kApertureHalfWidth
      << ",\"center_y_cm\":0,\"center_z_cm\":" << kApertureCenterZ
      << ",\"negative_x_shell_radii_cm\":[" << kBpeOuterRadius << ","
      << kBpeInnerRadius << "],\"method\":"
         "\"line intersections with r=29 and r=27 cm; minimum transverse "
         "y/z distance to square boundary\",\"positive_clearance_passes\":"
      << events.analytic_clearance_passes << ",\"clearance_cm\":";
  WriteStats(out, events.aperture_clearance_cm);
  out << ",\"y_clearance_cm\":";
  WriteStats(out, events.aperture_y_clearance_cm);
  out << ",\"z_clearance_cm\":";
  WriteStats(out, events.aperture_z_clearance_cm);
  out << "}\n  },\n";
  out << "  \"failure_count\":" << failure_total << ",\n";
  out << "  \"failure_samples_truncated\":"
      << (failure_total > failures.size() ? "true" : "false") << ",\n";
  out << "  \"failure_samples\":[";
  for (std::size_t i = 0; i < failures.size(); ++i) {
    if (i != 0) out << ",";
    out << "{\"check\":";
    WriteJsonString(out, failures[i].check);
    out << ",\"item\":";
    WriteJsonString(out, failures[i].item);
    out << ",\"detail\":";
    WriteJsonString(out, failures[i].detail);
    out << "}";
  }
  out << "]\n}\n";
  out.flush();
  return static_cast<bool>(out);
}

int RunAudit(const char* setup_file, const char* hole_csv, const char* eventlist,
             const char* output_json) {
  const std::string setup_path = setup_file == nullptr ? "" : setup_file;
  const std::string csv_path = hole_csv == nullptr ? "" : hole_csv;
  const std::string event_path = eventlist == nullptr ? "" : eventlist;
  const std::string output_path = output_json == nullptr ? "" : output_json;
  std::vector<Failure> failures;
  std::size_t failure_total = 0;
  std::vector<HoleRow> accepted;
  std::map<std::string, std::size_t> accepted_by_plate;
  std::size_t csv_rows = 0;
  std::size_t keepout_skipped_rows = 0;
  std::size_t selection_skipped_rows = 0;
  HoleAudit hole_audit;
  EventAudit event_audit;
  bool global_initialized = false;
  bool geometry_loaded = false;

  if (setup_path.empty() || csv_path.empty() || event_path.empty() || output_path.empty()) {
    AddFailure(failures, failure_total, "arguments", "native audit",
               "all four absolute path arguments are required");
  }
  const bool csv_valid =
      !csv_path.empty() &&
      LoadAcceptedHoles(csv_path, accepted, accepted_by_plate, csv_rows,
                        keepout_skipped_rows, selection_skipped_rows, failures,
                        failure_total);

  try {
    global_initialized = MGlobal::Initialize(
        "SE3NativeGeometryAudit", "SE3 geometry-only load and navigator audit");
    if (!global_initialized) {
      AddFailure(failures, failure_total, "mglobal_initialize", "MEGAlib",
                 "MGlobal::Initialize returned false");
    } else if (!setup_path.empty()) {
      MDGeometryQuest geometry;
      geometry_loaded = geometry.ScanSetupFile(MString(setup_path.c_str()), true, false, false);
      if (!geometry_loaded) {
        AddFailure(failures, failure_total, "scan_setup_file", setup_path,
                   "MDGeometryQuest::ScanSetupFile returned false");
      } else {
        if (csv_valid) {
          hole_audit = AuditHoles(geometry, accepted, failures, failure_total);
        }
        if (!event_path.empty()) {
          event_audit = AuditEventList(geometry, event_path, failures, failure_total);
        }
      }
    }
  } catch (const std::exception& error) {
    AddFailure(failures, failure_total, "native_exception", "std::exception", error.what());
  } catch (...) {
    AddFailure(failures, failure_total, "native_exception", "unknown",
               "non-standard exception escaped the audit");
  }

  bool passed = global_initialized && geometry_loaded && csv_valid && failure_total == 0;
  passed = passed && hole_audit.accepted_holes == accepted.size();
  passed = passed && hole_audit.hole_probe_queries == accepted.size() * 3;
  passed = passed && hole_audit.hole_probe_passes == hole_audit.hole_probe_queries;
  passed = passed && hole_audit.web_holes_checked == accepted.size();
  passed = passed && hole_audit.web_passes == accepted.size();
  passed = passed && hole_audit.nearest_pair_web_passes == accepted.size();
  passed = passed && hole_audit.outer_edge_web_passes == accepted.size();
  passed = passed && event_audit.parsed_rows == kExpectedEventCount;
  passed = passed && event_audit.path_length_calls == kExpectedEventCount;
  passed = passed && event_audit.bpe_zero_passes == kExpectedEventCount;
  passed = passed && event_audit.plastic_positive_passes == kExpectedEventCount;
  passed = passed && event_audit.analytic_clearance_passes == kExpectedEventCount;
  passed = passed && event_audit.input_plane_passes == kExpectedEventCount;
  passed = passed && event_audit.forward_direction_passes == kExpectedEventCount;

  if (!WriteReport(output_path, global_initialized, geometry_loaded, setup_path, csv_path,
                   event_path, csv_rows, keepout_skipped_rows,
                   selection_skipped_rows, hole_audit, event_audit, failures,
                   failure_total, passed)) {
    return 2;
  }
  return passed ? 0 : 1;
}

}  // namespace

void se3_native_geometry_audit(const char* setup_file, const char* hole_csv,
                               const char* eventlist, const char* output_json) {
  const int status = RunAudit(setup_file, hole_csv, eventlist, output_json);
  gSystem->Exit(status);
}
