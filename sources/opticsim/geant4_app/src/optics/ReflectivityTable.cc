#include "optics/ReflectivityTable.hh"

#include <algorithm>
#include <cerrno>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <map>
#include <sstream>
#include <stdexcept>

namespace {

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

double ReadDouble(
    const std::map<std::string, std::string>& row,
    const std::string& key) {
  const auto it = row.find(key);
  if (it == row.end() || it->second.empty()) {
    throw std::runtime_error("missing CSV column: " + key);
  }
  errno = 0;
  char* end = 0;
  const double parsed = std::strtod(it->second.c_str(), &end);
  if (end == it->second.c_str()) {
    throw std::runtime_error("invalid numeric CSV column " + key + "='" + it->second + "'");
  }
  if (errno == ERANGE && parsed != 0.0) {
    const double tiny = parsed > 0.0 ? 0.0 : -0.0;
    return tiny;
  }
  return parsed;
}

std::string ReadString(
    const std::map<std::string, std::string>& row,
    const std::string& key,
    const std::string& fallback = "") {
  const auto it = row.find(key);
  if (it == row.end()) return fallback;
  return it->second;
}

void ValidateRat(const optics::ReflectivityTableRow& row) {
  if (row.R < 0.0 || row.A < 0.0 || row.T < 0.0) {
    throw std::runtime_error("R/A/T must be non-negative");
  }
  const double sum = row.R + row.A + row.T;
  if (std::fabs(sum - 1.0) > 1.0e-8) {
    throw std::runtime_error("R/A/T must sum to one");
  }
}

optics::ReflectivityTableRow Interpolate(
    const optics::ReflectivityTableRow& lower,
    const optics::ReflectivityTableRow& upper,
    double thetaRad) {
  if (upper.thetaRad == lower.thetaRad) return lower;
  const double f = (thetaRad - lower.thetaRad) / (upper.thetaRad - lower.thetaRad);
  auto lerp = [f](double a, double b) { return a + f * (b - a); };
  optics::ReflectivityTableRow out = lower;
  out.thetaRad = thetaRad;
  out.R = lerp(lower.R, upper.R);
  out.A = lerp(lower.A, upper.A);
  out.T = lerp(lower.T, upper.T);
  const double sum = out.R + out.A + out.T;
  if (sum > 0.0) {
    out.R /= sum;
    out.A /= sum;
    out.T /= sum;
  }
  out.source = lower.source + ":theta_interpolated";
  return out;
}

}  // namespace

namespace optics {

ReflectivityTable ReflectivityTable::FromCsv(const std::string& path) {
  std::ifstream input(path.c_str());
  if (!input) {
    throw std::runtime_error("failed to open reflectivity table: " + path);
  }

  std::string line;
  if (!std::getline(input, line)) {
    throw std::runtime_error("reflectivity table is empty: " + path);
  }
  const std::vector<std::string> headers = SplitCsvLine(line);
  ReflectivityTable table;
  while (std::getline(input, line)) {
    if (Trim(line).empty()) continue;
    const std::vector<std::string> cells = SplitCsvLine(line);
    std::map<std::string, std::string> row;
    for (std::size_t i = 0; i < headers.size() && i < cells.size(); ++i) {
      row[headers[i]] = cells[i];
    }
    ReflectivityTableRow parsed;
    parsed.stackId = ReadString(row, "stack_id", "default");
    parsed.energyKeV = ReadDouble(row, "E_keV");
    parsed.thetaRad = ReadDouble(row, "theta_rad");
    parsed.R = ReadDouble(row, "R");
    parsed.A = ReadDouble(row, "A");
    parsed.T = ReadDouble(row, "T");
    parsed.source = ReadString(row, "source", "");
    ValidateRat(parsed);
    table.rows_.push_back(parsed);
  }
  if (table.rows_.empty()) {
    throw std::runtime_error("reflectivity table has no data rows: " + path);
  }
  std::sort(
      table.rows_.begin(),
      table.rows_.end(),
      [](const ReflectivityTableRow& a, const ReflectivityTableRow& b) {
        if (a.stackId != b.stackId) return a.stackId < b.stackId;
        if (a.energyKeV != b.energyKeV) return a.energyKeV < b.energyKeV;
        return a.thetaRad < b.thetaRad;
      });
  return table;
}

bool ReflectivityTable::empty() const {
  return rows_.empty();
}

const std::vector<ReflectivityTableRow>& ReflectivityTable::rows() const {
  return rows_;
}

ReflectivityTableRow ReflectivityTable::Lookup(
    double energyKeV,
    double thetaRad,
    ReflectivityLookupMode mode,
    const std::string& stackId) const {
  if (rows_.empty()) {
    throw std::runtime_error("reflectivity table is empty");
  }

  std::vector<ReflectivityTableRow> candidates;
  for (const auto& row : rows_) {
    if (stackId.empty() || row.stackId == stackId) {
      candidates.push_back(row);
    }
  }
  if (candidates.empty()) {
    throw std::runtime_error("no reflectivity rows for stack_id=" + stackId);
  }

  double nearestEnergy = candidates.front().energyKeV;
  double nearestEnergyDelta = std::fabs(nearestEnergy - energyKeV);
  for (const auto& row : candidates) {
    const double delta = std::fabs(row.energyKeV - energyKeV);
    if (delta < nearestEnergyDelta) {
      nearestEnergy = row.energyKeV;
      nearestEnergyDelta = delta;
    }
  }

  std::vector<ReflectivityTableRow> sameEnergy;
  for (const auto& row : candidates) {
    if (std::fabs(row.energyKeV - nearestEnergy) < 1.0e-9) {
      sameEnergy.push_back(row);
    }
  }
  std::sort(
      sameEnergy.begin(),
      sameEnergy.end(),
      [](const ReflectivityTableRow& a, const ReflectivityTableRow& b) {
        return a.thetaRad < b.thetaRad;
      });

  const double tol = 1.0e-12;
  if (thetaRad < sameEnergy.front().thetaRad - tol ||
      thetaRad > sameEnergy.back().thetaRad + tol) {
    std::ostringstream msg;
    msg << "theta_rad=" << thetaRad << " outside reflectivity table range ["
        << sameEnergy.front().thetaRad << ", " << sameEnergy.back().thetaRad << "]";
    throw std::runtime_error(msg.str());
  }
  if (sameEnergy.size() == 1) return sameEnergy.front();

  if (mode == ReflectivityLookupMode::kNearest) {
    return *std::min_element(
        sameEnergy.begin(),
        sameEnergy.end(),
        [thetaRad](const ReflectivityTableRow& a, const ReflectivityTableRow& b) {
          return std::fabs(a.thetaRad - thetaRad) < std::fabs(b.thetaRad - thetaRad);
        });
  }

  if (thetaRad <= sameEnergy.front().thetaRad + tol) return sameEnergy.front();
  if (thetaRad >= sameEnergy.back().thetaRad - tol) return sameEnergy.back();
  for (std::size_t i = 0; i + 1 < sameEnergy.size(); ++i) {
    const auto& lower = sameEnergy[i];
    const auto& upper = sameEnergy[i + 1];
    if (lower.thetaRad <= thetaRad && thetaRad <= upper.thetaRad) {
      return Interpolate(lower, upper, thetaRad);
    }
  }
  return *std::min_element(
      sameEnergy.begin(),
      sameEnergy.end(),
      [thetaRad](const ReflectivityTableRow& a, const ReflectivityTableRow& b) {
        return std::fabs(a.thetaRad - thetaRad) < std::fabs(b.thetaRad - thetaRad);
      });
}

}  // namespace optics
