// Paired native navigator audit for the frozen x'=-30.0001 cm signal bank.
//
// This macro loads the frozen S3d-O8 and SE3 setup files with
// MDGeometryQuest.  It performs geometry/navigation queries only: no source is
// constructed and no particle transport is launched.

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
#include <sstream>
#include <string>
#include <vector>

namespace {

constexpr std::size_t kExpectedRows = 37194;
constexpr std::size_t kExpectedFields = 15;
constexpr std::size_t kMaxFailureSamples = 50;
constexpr double kRotationYDeg = 45.0;
constexpr double kInjectionX = -30.0001;
constexpr double kPlasticOuterRadius = 30.0;
constexpr double kPlasticInnerRadius = 29.0;
constexpr double kBpeInnerRadius = 27.0;
constexpr double kApertureHalfWidth = 1.898;
constexpr double kApertureCenterZ = -5.2;
constexpr double kPlaneTolerance = 1.0e-7;
constexpr double kDirectionNormTolerance = 1.0e-8;
constexpr double kBpeZeroTolerance = 1.0e-9;
constexpr double kChordClosureTolerance = 2.0e-5;
constexpr double kBoundaryPad = 1.0e-4;

const char* kPlasticMaterial = "PlasticScintillator";
const char* kBpeMaterial = "BoratedPolyethylene5wtB";
const char* kPlasticVolume = "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm";
const char* kBpeVolume = "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm";

struct GeometrySpec {
  std::string key;
  std::string observed_order;
  bool expect_bpe_port = false;
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

struct GeometryAudit {
  GeometrySpec spec;
  std::string setup_path;
  std::string eventlist_path;
  bool geometry_loaded = false;
  std::size_t logical_rows = 0;
  std::size_t parsed_rows = 0;
  std::size_t id_passes = 0;
  std::size_t energy_passes = 0;
  std::size_t plane_passes = 0;
  std::size_t forward_direction_passes = 0;
  std::size_t analytic_outside_passes = 0;
  std::size_t native_outside_passes = 0;
  std::size_t ordered_intersection_passes = 0;
  std::size_t path_length_calls = 0;
  std::size_t material_map_passes = 0;
  std::size_t plastic_positive_passes = 0;
  std::size_t plastic_full_chord_passes = 0;
  std::size_t plastic_probe_queries = 0;
  std::size_t plastic_probe_passes = 0;
  std::size_t bpe_positive_passes = 0;
  std::size_t bpe_full_chord_passes = 0;
  std::size_t bpe_zero_passes = 0;
  std::size_t bpe_probe_queries = 0;
  std::size_t bpe_probe_passes = 0;
  std::size_t aperture_clearance_passes = 0;
  RunningStats outside_clearance_cm;
  RunningStats plastic_expected_cm;
  RunningStats plastic_native_cm;
  RunningStats plastic_abs_error_cm;
  RunningStats bpe_expected_cm;
  RunningStats bpe_native_cm;
  RunningStats bpe_abs_error_cm;
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
  return errno == 0 && end != stripped.c_str() && *end == '\0' &&
         std::isfinite(value);
}

void AddFailure(std::vector<Failure>& failures, std::size_t& failure_total,
                const std::string& check, const std::string& item,
                const std::string& detail) {
  ++failure_total;
  if (failures.size() < kMaxFailureSamples) {
    failures.push_back({check, item, detail});
  }
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

bool SequenceHasVolume(const MDVolumeSequence& sequence,
                       const std::string& volume_name) {
  for (unsigned int i = 0; i < sequence.GetNVolumes(); ++i) {
    MDVolume* volume = sequence.GetVolumeAt(i);
    if (volume != nullptr && volume->GetName().GetString() == volume_name) return true;
  }
  return false;
}

bool SequenceHasMaterial(const MDVolumeSequence& sequence,
                         const std::string& material_name) {
  for (unsigned int i = 0; i < sequence.GetNVolumes(); ++i) {
    MDVolume* volume = sequence.GetVolumeAt(i);
    if (volume != nullptr && volume->GetMaterial() != nullptr &&
        volume->GetMaterial()->GetName().GetString() == material_name) {
      return true;
    }
  }
  return false;
}

bool DeepestMaterialMatches(const MDVolumeSequence& sequence,
                            const std::string& material_name) {
  MDVolume* deepest = sequence.GetDeepestVolume();
  return deepest != nullptr && deepest->GetMaterial() != nullptr &&
         deepest->GetMaterial()->GetName().GetString() == material_name;
}

std::string SequenceDescription(const MDVolumeSequence& sequence) {
  if (sequence.GetNVolumes() == 0) return "<empty>";
  std::ostringstream out;
  for (unsigned int i = 0; i < sequence.GetNVolumes(); ++i) {
    if (i != 0) out << "/";
    MDVolume* volume = sequence.GetVolumeAt(i);
    if (volume == nullptr) {
      out << "<null>";
    } else {
      out << volume->GetName().GetString();
      if (volume->GetMaterial() != nullptr) {
        out << "[" << volume->GetMaterial()->GetName().GetString() << "]";
      }
    }
  }
  return out.str();
}

bool FirstNegativeXIntersection(const std::array<double, 3>& point,
                                const std::array<double, 3>& direction,
                                double radius, double& result) {
  const double a = direction[0] * direction[0] + direction[1] * direction[1];
  const double b = 2.0 * (point[0] * direction[0] +
                          point[1] * direction[1]);
  const double c = point[0] * point[0] + point[1] * point[1] - radius * radius;
  if (!(a > 0.0)) return false;
  const double discriminant = b * b - 4.0 * a * c;
  if (discriminant < 0.0) return false;
  const double root = std::sqrt(std::max(0.0, discriminant));
  const std::array<double, 2> candidates = {{(-b - root) / (2.0 * a),
                                             (-b + root) / (2.0 * a)}};
  bool found = false;
  result = std::numeric_limits<double>::infinity();
  for (double candidate : candidates) {
    if (candidate < -1.0e-9) continue;
    const double x = point[0] + candidate * direction[0];
    if (x >= 0.0) continue;
    if (!found || candidate < result) {
      result = candidate;
      found = true;
    }
  }
  return found;
}

MVector PointAt(const std::array<double, 3>& point,
                const std::array<double, 3>& direction, double t) {
  return InstrumentToWorld(point[0] + t * direction[0],
                           point[1] + t * direction[1],
                           point[2] + t * direction[2]);
}

bool PortClearance(const std::array<double, 3>& point,
                   const std::array<double, 3>& direction,
                   double t_outer, double t_inner,
                   double& y_clearance, double& z_clearance,
                   double& clearance) {
  const double outer_y = point[1] + t_outer * direction[1];
  const double inner_y = point[1] + t_inner * direction[1];
  const double outer_z = point[2] + t_outer * direction[2];
  const double inner_z = point[2] + t_inner * direction[2];
  y_clearance = kApertureHalfWidth -
                std::max(std::abs(outer_y), std::abs(inner_y));
  z_clearance = kApertureHalfWidth -
                std::max(std::abs(outer_z - kApertureCenterZ),
                         std::abs(inner_z - kApertureCenterZ));
  clearance = std::min(y_clearance, z_clearance);
  return std::isfinite(clearance);
}

GeometryAudit AuditGeometry(MDGeometryQuest& geometry, const GeometrySpec& spec,
                            const std::string& setup_path,
                            const std::string& eventlist_path,
                            std::vector<Failure>& failures,
                            std::size_t& failure_total) {
  GeometryAudit audit;
  audit.spec = spec;
  audit.setup_path = setup_path;
  audit.eventlist_path = eventlist_path;

  std::ifstream input(eventlist_path);
  if (!input) {
    AddFailure(failures, failure_total, "eventlist_open", spec.key,
               "unable to open " + eventlist_path);
    return audit;
  }

  const std::array<double, 5> fractions = {{0.1, 0.3, 0.5, 0.7, 0.9}};
  std::string line;
  std::size_t physical_line = 0;
  while (std::getline(input, line)) {
    ++physical_line;
    const std::string stripped = Trim(line);
    if (stripped.empty() || stripped[0] == '#') continue;
    const std::size_t logical_row = audit.logical_rows++;

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
    if (!row_valid || values.size() != kExpectedFields) {
      AddFailure(failures, failure_total, "eventlist_row",
                 spec.key + ":line " + std::to_string(physical_line),
                 "expected exactly 15 finite numeric fields");
      continue;
    }
    ++audit.parsed_rows;

    const long long event_id = std::llround(values[0]);
    if (std::abs(values[0] - static_cast<double>(event_id)) <= 1.0e-12 &&
        event_id == static_cast<long long>(logical_row)) {
      ++audit.id_passes;
    } else {
      AddFailure(failures, failure_total, "eventlist_id",
                 spec.key + ":line " + std::to_string(physical_line),
                 "event IDs must be consecutive from zero");
    }
    if (values[14] == 511.0) {
      ++audit.energy_passes;
    } else {
      AddFailure(failures, failure_total, "eventlist_energy",
                 spec.key + ":" + std::to_string(event_id),
                 "energy is not exactly 511 keV");
    }

    const std::array<double, 3> point =
        WorldToInstrument(values[5], values[6], values[7]);
    const std::array<double, 3> direction =
        WorldToInstrument(values[8], values[9], values[10]);
    const double direction_norm =
        std::sqrt(direction[0] * direction[0] + direction[1] * direction[1] +
                  direction[2] * direction[2]);
    if (std::abs(point[0] - kInjectionX) <= kPlaneTolerance) {
      ++audit.plane_passes;
    } else {
      AddFailure(failures, failure_total, "injection_plane",
                 spec.key + ":" + std::to_string(event_id),
                 "point does not invert to x'=-30.0001 cm");
    }
    if (direction[0] > 0.999 &&
        std::abs(direction_norm - 1.0) <= kDirectionNormTolerance) {
      ++audit.forward_direction_passes;
    } else {
      AddFailure(failures, failure_total, "forward_direction",
                 spec.key + ":" + std::to_string(event_id),
                 "direction is not unit forward +x'");
    }

    const double outside_clearance =
        std::hypot(point[0], point[1]) - kPlasticOuterRadius;
    audit.outside_clearance_cm.Add(outside_clearance);
    if (outside_clearance > 0.0) {
      ++audit.analytic_outside_passes;
    } else {
      AddFailure(failures, failure_total, "analytic_start_outside",
                 spec.key + ":" + std::to_string(event_id),
                 "injection point is not radially outside r=30 cm");
    }

    const MDVolumeSequence start_sequence = geometry.GetVolumeSequence(
        InstrumentToWorld(point[0], point[1], point[2]));
    const bool native_outside =
        !SequenceHasVolume(start_sequence, kPlasticVolume) &&
        !SequenceHasVolume(start_sequence, kBpeVolume) &&
        !SequenceHasMaterial(start_sequence, kPlasticMaterial) &&
        !SequenceHasMaterial(start_sequence, kBpeMaterial);
    if (native_outside) {
      ++audit.native_outside_passes;
    } else {
      AddFailure(failures, failure_total, "native_start_outside",
                 spec.key + ":" + std::to_string(event_id),
                 "start sequence contains an envelope: " +
                     SequenceDescription(start_sequence));
    }

    double t30 = 0.0;
    double t29 = 0.0;
    double t27 = 0.0;
    const bool intersections =
        FirstNegativeXIntersection(point, direction, kPlasticOuterRadius, t30) &&
        FirstNegativeXIntersection(point, direction, kPlasticInnerRadius, t29) &&
        FirstNegativeXIntersection(point, direction, kBpeInnerRadius, t27) &&
        t30 >= -1.0e-9 && t30 < t29 && t29 < t27;
    if (!intersections) {
      AddFailure(failures, failure_total, "ordered_shell_intersections",
                 spec.key + ":" + std::to_string(event_id),
                 "failed required t(r30)<t(r29)<t(r27) on the negative-x' side");
      continue;
    }
    ++audit.ordered_intersection_passes;

    const double expected_plastic = (t29 - t30) * direction_norm;
    const double expected_bpe = (t27 - t29) * direction_norm;
    audit.plastic_expected_cm.Add(expected_plastic);
    audit.bpe_expected_cm.Add(expected_bpe);

    const MVector start_world =
        InstrumentToWorld(point[0], point[1], point[2]);
    const MVector stop_world = PointAt(point, direction, t27 + kBoundaryPad);
    std::map<MDMaterial*, double> lengths =
        geometry.GetPathLengths(start_world, stop_world);
    ++audit.path_length_calls;
    double plastic = 0.0;
    double bpe = 0.0;
    bool material_map_ok = true;
    for (const auto& entry : lengths) {
      if (entry.first == nullptr || !std::isfinite(entry.second) ||
          entry.second < 0.0) {
        material_map_ok = false;
        continue;
      }
      const std::string material = entry.first->GetName().GetString();
      if (material == kPlasticMaterial) plastic += entry.second;
      if (material == kBpeMaterial) bpe += entry.second;
    }
    if (material_map_ok) {
      ++audit.material_map_passes;
    } else {
      AddFailure(failures, failure_total, "path_length_material_map",
                 spec.key + ":" + std::to_string(event_id),
                 "GetPathLengths returned a null material or invalid length");
    }

    const double plastic_error = std::abs(plastic - expected_plastic);
    audit.plastic_native_cm.Add(plastic);
    audit.plastic_abs_error_cm.Add(plastic_error);
    if (plastic > 0.0) {
      ++audit.plastic_positive_passes;
    } else {
      AddFailure(failures, failure_total, "plastic_positive_chord",
                 spec.key + ":" + std::to_string(event_id),
                 "native plastic chord is not positive");
    }
    if (plastic_error <= kChordClosureTolerance) {
      ++audit.plastic_full_chord_passes;
    } else {
      std::ostringstream detail;
      detail << std::setprecision(17) << "native=" << plastic
             << " expected full shell=" << expected_plastic
             << " abs_error=" << plastic_error;
      AddFailure(failures, failure_total, "plastic_full_chord",
                 spec.key + ":" + std::to_string(event_id), detail.str());
    }
    for (double fraction : fractions) {
      ++audit.plastic_probe_queries;
      const double t = t30 + fraction * (t29 - t30);
      const MDVolumeSequence sequence = geometry.GetVolumeSequence(
          PointAt(point, direction, t));
      if (DeepestMaterialMatches(sequence, kPlasticMaterial)) {
        ++audit.plastic_probe_passes;
      } else {
        AddFailure(failures, failure_total, "plastic_continuity_probe",
                   spec.key + ":" + std::to_string(event_id),
                   "plastic-shell interior probe returned " +
                       SequenceDescription(sequence));
      }
    }

    audit.bpe_native_cm.Add(bpe);
    if (!spec.expect_bpe_port) {
      const double bpe_error = std::abs(bpe - expected_bpe);
      audit.bpe_abs_error_cm.Add(bpe_error);
      if (bpe > 0.0) {
        ++audit.bpe_positive_passes;
      } else {
        AddFailure(failures, failure_total, "bpe_positive_chord",
                   spec.key + ":" + std::to_string(event_id),
                   "native BPE chord is not positive");
      }
      if (bpe_error <= kChordClosureTolerance) {
        ++audit.bpe_full_chord_passes;
      } else {
        std::ostringstream detail;
        detail << std::setprecision(17) << "native=" << bpe
               << " expected full shell=" << expected_bpe
               << " abs_error=" << bpe_error;
        AddFailure(failures, failure_total, "bpe_full_chord",
                   spec.key + ":" + std::to_string(event_id), detail.str());
      }
      for (double fraction : fractions) {
        ++audit.bpe_probe_queries;
        const double t = t29 + fraction * (t27 - t29);
        const MDVolumeSequence sequence = geometry.GetVolumeSequence(
            PointAt(point, direction, t));
        if (DeepestMaterialMatches(sequence, kBpeMaterial)) {
          ++audit.bpe_probe_passes;
        } else {
          AddFailure(failures, failure_total, "bpe_complete_shell_probe",
                     spec.key + ":" + std::to_string(event_id),
                     "BPE-shell interior probe returned " +
                         SequenceDescription(sequence));
        }
      }
    } else {
      audit.bpe_abs_error_cm.Add(std::abs(bpe));
      if (std::abs(bpe) <= kBpeZeroTolerance) {
        ++audit.bpe_zero_passes;
      } else {
        std::ostringstream detail;
        detail << std::setprecision(17) << "native BPE chord=" << bpe;
        AddFailure(failures, failure_total, "bpe_port_zero_chord",
                   spec.key + ":" + std::to_string(event_id), detail.str());
      }
      for (double fraction : fractions) {
        ++audit.bpe_probe_queries;
        const double t = t29 + fraction * (t27 - t29);
        const MDVolumeSequence sequence = geometry.GetVolumeSequence(
            PointAt(point, direction, t));
        if (!SequenceHasMaterial(sequence, kBpeMaterial) &&
            !SequenceHasVolume(sequence, kBpeVolume)) {
          ++audit.bpe_probe_passes;
        } else {
          AddFailure(failures, failure_total, "bpe_port_probe",
                     spec.key + ":" + std::to_string(event_id),
                     "focused-port probe still contains BPE: " +
                         SequenceDescription(sequence));
        }
      }
      double y_clearance = 0.0;
      double z_clearance = 0.0;
      double clearance = 0.0;
      if (PortClearance(point, direction, t29, t27, y_clearance,
                        z_clearance, clearance)) {
        audit.aperture_y_clearance_cm.Add(y_clearance);
        audit.aperture_z_clearance_cm.Add(z_clearance);
        audit.aperture_clearance_cm.Add(clearance);
        if (clearance > 0.0) {
          ++audit.aperture_clearance_passes;
        } else {
          std::ostringstream detail;
          detail << std::setprecision(17) << "clearance=" << clearance
                 << " y=" << y_clearance << " z=" << z_clearance;
          AddFailure(failures, failure_total, "analytic_port_clearance",
                     spec.key + ":" + std::to_string(event_id), detail.str());
        }
      } else {
        AddFailure(failures, failure_total, "analytic_port_clearance",
                   spec.key + ":" + std::to_string(event_id),
                   "non-finite focused-port clearance");
      }
    }
  }

  if (audit.logical_rows != kExpectedRows || audit.parsed_rows != kExpectedRows) {
    std::ostringstream detail;
    detail << "logical=" << audit.logical_rows << " parsed=" << audit.parsed_rows
           << " expected=" << kExpectedRows;
    AddFailure(failures, failure_total, "eventlist_count", spec.key, detail.str());
  }
  return audit;
}

bool AuditCountersPass(const GeometryAudit& audit) {
  const std::size_t rows = kExpectedRows;
  const std::size_t probes = rows * 5;
  bool passed = audit.geometry_loaded && audit.logical_rows == rows &&
                audit.parsed_rows == rows && audit.id_passes == rows &&
                audit.energy_passes == rows && audit.plane_passes == rows &&
                audit.forward_direction_passes == rows &&
                audit.analytic_outside_passes == rows &&
                audit.native_outside_passes == rows &&
                audit.ordered_intersection_passes == rows &&
                audit.path_length_calls == rows &&
                audit.material_map_passes == rows &&
                audit.plastic_positive_passes == rows &&
                audit.plastic_full_chord_passes == rows &&
                audit.plastic_probe_queries == probes &&
                audit.plastic_probe_passes == probes &&
                audit.bpe_probe_queries == probes &&
                audit.bpe_probe_passes == probes;
  if (audit.spec.expect_bpe_port) {
    passed = passed && audit.bpe_zero_passes == rows &&
             audit.aperture_clearance_passes == rows;
  } else {
    passed = passed && audit.bpe_positive_passes == rows &&
             audit.bpe_full_chord_passes == rows;
  }
  return passed;
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
  WriteJsonNumberOrNull(out, stats.count == 0
                                ? std::numeric_limits<double>::quiet_NaN()
                                : stats.minimum);
  out << ",\"mean\":";
  WriteJsonNumberOrNull(out, stats.Mean());
  out << ",\"max\":";
  WriteJsonNumberOrNull(out, stats.count == 0
                                ? std::numeric_limits<double>::quiet_NaN()
                                : stats.maximum);
  out << "}";
}

void WriteGeometry(std::ostream& out, const GeometryAudit& audit) {
  out << "{\"status\":\"" << (AuditCountersPass(audit) ? "PASS" : "FAIL")
      << "\",\"setup\":";
  WriteJsonString(out, audit.setup_path);
  out << ",\"eventlist\":";
  WriteJsonString(out, audit.eventlist_path);
  out << ",\"geometry_loaded\":" << (audit.geometry_loaded ? "true" : "false")
      << ",\"observed_order\":";
  WriteJsonString(out, audit.spec.observed_order);
  out << ",\"expected_rows\":" << kExpectedRows
      << ",\"logical_rows\":" << audit.logical_rows
      << ",\"parsed_rows\":" << audit.parsed_rows
      << ",\"id_passes\":" << audit.id_passes
      << ",\"energy_511kev_passes\":" << audit.energy_passes
      << ",\"input_plane_passes\":" << audit.plane_passes
      << ",\"forward_direction_passes\":" << audit.forward_direction_passes
      << ",\"analytic_start_outside_passes\":" << audit.analytic_outside_passes
      << ",\"native_start_outside_passes\":" << audit.native_outside_passes
      << ",\"ordered_intersection_passes\":" << audit.ordered_intersection_passes
      << ",\"get_path_lengths_calls\":" << audit.path_length_calls
      << ",\"material_map_passes\":" << audit.material_map_passes
      << ",\"outside_clearance_cm\":";
  WriteStats(out, audit.outside_clearance_cm);
  out << ",\"plastic\":{\"material\":";
  WriteJsonString(out, kPlasticMaterial);
  out << ",\"positive_chord_passes\":" << audit.plastic_positive_passes
      << ",\"full_chord_passes\":" << audit.plastic_full_chord_passes
      << ",\"continuity_probe_queries\":" << audit.plastic_probe_queries
      << ",\"continuity_probe_passes\":" << audit.plastic_probe_passes
      << ",\"expected_full_chord_cm\":";
  WriteStats(out, audit.plastic_expected_cm);
  out << ",\"native_chord_cm\":";
  WriteStats(out, audit.plastic_native_cm);
  out << ",\"absolute_closure_error_cm\":";
  WriteStats(out, audit.plastic_abs_error_cm);
  out << "},\"bpe\":{\"material\":";
  WriteJsonString(out, kBpeMaterial);
  out << ",\"expectation\":\""
      << (audit.spec.expect_bpe_port ? "ZERO_CHORD_THROUGH_PORT"
                                     : "POSITIVE_COMPLETE_SHELL_CHORD")
      << "\",\"positive_chord_passes\":" << audit.bpe_positive_passes
      << ",\"full_chord_passes\":" << audit.bpe_full_chord_passes
      << ",\"zero_chord_passes\":" << audit.bpe_zero_passes
      << ",\"probe_queries\":" << audit.bpe_probe_queries
      << ",\"probe_passes\":" << audit.bpe_probe_passes
      << ",\"expected_full_shell_chord_cm\":";
  WriteStats(out, audit.bpe_expected_cm);
  out << ",\"native_chord_cm\":";
  WriteStats(out, audit.bpe_native_cm);
  out << ",\"absolute_closure_error_cm\":";
  WriteStats(out, audit.bpe_abs_error_cm);
  out << "},\"focused_port\":{\"half_width_cm\":" << kApertureHalfWidth
      << ",\"center_z_cm\":" << kApertureCenterZ
      << ",\"positive_clearance_passes\":" << audit.aperture_clearance_passes
      << ",\"clearance_cm\":";
  WriteStats(out, audit.aperture_clearance_cm);
  out << ",\"y_clearance_cm\":";
  WriteStats(out, audit.aperture_y_clearance_cm);
  out << ",\"z_clearance_cm\":";
  WriteStats(out, audit.aperture_z_clearance_cm);
  out << "}}";
}

bool WriteReport(const std::string& output_path, bool global_initialized,
                 const GeometryAudit& s3d, const GeometryAudit& se3,
                 const std::vector<Failure>& failures,
                 std::size_t failure_total, bool passed) {
  std::ofstream out(output_path, std::ios::out | std::ios::trunc);
  if (!out) return false;
  out << "{\n  \"schema_version\":1,\n  \"status\":\""
      << (passed ? "PASS" : "FAIL")
      << "\",\n  \"engine\":\"MEGAlib MDGeometryQuest\",\n"
         "  \"transport_launched\":false,\n"
         "  \"mglobal_initialized\":"
      << (global_initialized ? "true" : "false") << ",\n"
      << "  \"coordinate_contract\":{\"instrument_rotation_y_deg\":"
      << kRotationYDeg << ",\"injection_plane_xprime_cm\":" << kInjectionX
      << ",\"shell_radii_cm\":{\"plastic_outer\":" << kPlasticOuterRadius
      << ",\"plastic_inner_bpe_outer\":" << kPlasticInnerRadius
      << ",\"bpe_inner\":" << kBpeInnerRadius
      << "},\"chord_closure_tolerance_cm\":" << kChordClosureTolerance
      << ",\"bpe_zero_tolerance_cm\":" << kBpeZeroTolerance << "},\n"
      << "  \"wording_interpretation\":{\"handoff_requirement\":"
         "\"complete BPE then continuous plastic\","
         "\"frozen_forward_encounter_order\":"
         "\"outer plastic r=29..30 cm precedes BPE r=27..29 cm\","
         "\"resolution\":"
         "\"report physical forward navigator order; interpret handoff phrase as layer-coverage requirements, not an instruction to reverse the frozen geometry\"},\n"
      << "  \"geometries\":{\"S3d_O8\":";
  WriteGeometry(out, s3d);
  out << ",\"SE3\":";
  WriteGeometry(out, se3);
  out << "},\n  \"failure_count\":" << failure_total
      << ",\n  \"failure_samples_truncated\":"
      << (failure_total > failures.size() ? "true" : "false")
      << ",\n  \"failure_samples\":[";
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

int RunAudit(const char* s3d_setup_file, const char* s3d_eventlist_file,
             const char* se3_setup_file, const char* se3_eventlist_file,
             const char* output_json) {
  const std::string s3d_setup = s3d_setup_file == nullptr ? "" : s3d_setup_file;
  const std::string s3d_eventlist =
      s3d_eventlist_file == nullptr ? "" : s3d_eventlist_file;
  const std::string se3_setup = se3_setup_file == nullptr ? "" : se3_setup_file;
  const std::string se3_eventlist =
      se3_eventlist_file == nullptr ? "" : se3_eventlist_file;
  const std::string output = output_json == nullptr ? "" : output_json;
  std::vector<Failure> failures;
  std::size_t failure_total = 0;
  GeometryAudit s3d;
  s3d.spec = {"S3d_O8", "PLASTIC_THEN_BPE", false};
  GeometryAudit se3;
  se3.spec = {"SE3", "PLASTIC_THEN_BPE_PORT", true};

  if (s3d_setup.empty() || s3d_eventlist.empty() || se3_setup.empty() ||
      se3_eventlist.empty() || output.empty()) {
    AddFailure(failures, failure_total, "arguments", "paired audit",
               "all five absolute path arguments are required");
  }

  bool global_initialized = false;
  try {
    global_initialized = MGlobal::Initialize(
        "PairedFullEnvelopeNavigationAudit",
        "S3d-O8/SE3 geometry-only full-envelope navigator audit");
    if (!global_initialized) {
      AddFailure(failures, failure_total, "mglobal_initialize", "MEGAlib",
                 "MGlobal::Initialize returned false");
    } else {
      {
        MDGeometryQuest geometry;
        const bool loaded = geometry.ScanSetupFile(
            MString(s3d_setup.c_str()), true, false, false);
        if (!loaded) {
          AddFailure(failures, failure_total, "scan_setup_file", "S3d_O8",
                     "MDGeometryQuest::ScanSetupFile returned false");
          s3d.setup_path = s3d_setup;
          s3d.eventlist_path = s3d_eventlist;
        } else {
          s3d = AuditGeometry(geometry,
                              {"S3d_O8", "PLASTIC_THEN_BPE", false},
                              s3d_setup, s3d_eventlist, failures, failure_total);
          s3d.geometry_loaded = true;
        }
      }
      {
        MDGeometryQuest geometry;
        const bool loaded = geometry.ScanSetupFile(
            MString(se3_setup.c_str()), true, false, false);
        if (!loaded) {
          AddFailure(failures, failure_total, "scan_setup_file", "SE3",
                     "MDGeometryQuest::ScanSetupFile returned false");
          se3.setup_path = se3_setup;
          se3.eventlist_path = se3_eventlist;
        } else {
          se3 = AuditGeometry(geometry,
                              {"SE3", "PLASTIC_THEN_BPE_PORT", true},
                              se3_setup, se3_eventlist, failures, failure_total);
          se3.geometry_loaded = true;
        }
      }
    }
  } catch (const std::exception& error) {
    AddFailure(failures, failure_total, "native_exception", "std::exception",
               error.what());
  } catch (...) {
    AddFailure(failures, failure_total, "native_exception", "unknown",
               "non-standard exception escaped the native audit");
  }

  const bool passed = global_initialized && failure_total == 0 &&
                      AuditCountersPass(s3d) && AuditCountersPass(se3);
  if (!WriteReport(output, global_initialized, s3d, se3, failures,
                   failure_total, passed)) {
    return 2;
  }
  return passed ? 0 : 1;
}

}  // namespace

void paired_full_envelope_navigation_audit(
    const char* s3d_setup, const char* s3d_eventlist,
    const char* se3_setup, const char* se3_eventlist,
    const char* output_json) {
  const int status = RunAudit(s3d_setup, s3d_eventlist, se3_setup,
                              se3_eventlist, output_json);
  gSystem->Exit(status);
}
