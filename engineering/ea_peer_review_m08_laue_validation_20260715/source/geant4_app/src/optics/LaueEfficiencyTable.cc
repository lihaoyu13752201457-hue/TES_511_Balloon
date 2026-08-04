#include "optics/LaueEfficiencyTable.hh"

#include <algorithm>
#include <cmath>
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

std::string ReadString(
    const std::map<std::string, std::string>& row,
    const std::string& key,
    const std::string& fallback = "") {
  const auto it = row.find(key);
  if (it == row.end()) return fallback;
  return it->second;
}

double ReadDouble(const std::map<std::string, std::string>& row, const std::string& key) {
  const auto it = row.find(key);
  if (it == row.end() || it->second.empty()) {
    throw std::runtime_error("missing CSV column: " + key);
  }
  return std::stod(it->second);
}

int ReadInt(const std::map<std::string, std::string>& row, const std::string& key) {
  const auto it = row.find(key);
  if (it == row.end() || it->second.empty()) {
    throw std::runtime_error("missing CSV column: " + key);
  }
  return std::stoi(it->second);
}

void ValidateProbabilities(const optics::LaueEfficiencyRow& row) {
  if (row.pDiff < 0.0 || row.pAbs < 0.0 || row.pTrans < 0.0) {
    throw std::runtime_error("Laue probabilities must be non-negative");
  }
  const double sum = row.pDiff + row.pAbs + row.pTrans;
  if (std::fabs(sum - 1.0) > 1.0e-8) {
    throw std::runtime_error("Laue probabilities must sum to one");
  }
}

optics::LaueEfficiencyRow Interpolate(
    const optics::LaueEfficiencyRow& lower,
    const optics::LaueEfficiencyRow& upper,
    double deltaThetaRad) {
  if (upper.deltaThetaRad == lower.deltaThetaRad) return lower;
  const double f = (deltaThetaRad - lower.deltaThetaRad) /
                   (upper.deltaThetaRad - lower.deltaThetaRad);
  auto lerp = [f](double a, double b) { return a + f * (b - a); };
  optics::LaueEfficiencyRow out = lower;
  out.deltaThetaRad = deltaThetaRad;
  out.thetaBRad = lerp(lower.thetaBRad, upper.thetaBRad);
  out.mosaicFwhmArcmin = lerp(lower.mosaicFwhmArcmin, upper.mosaicFwhmArcmin);
  out.thicknessMm = lerp(lower.thicknessMm, upper.thicknessMm);
  out.pDiff = lerp(lower.pDiff, upper.pDiff);
  out.pAbs = lerp(lower.pAbs, upper.pAbs);
  out.pTrans = lerp(lower.pTrans, upper.pTrans);
  const double sum = out.pDiff + out.pAbs + out.pTrans;
  if (sum > 0.0) {
    out.pDiff /= sum;
    out.pAbs /= sum;
    out.pTrans /= sum;
  }
  out.source = lower.source + ":delta_interpolated";
  return out;
}

}  // namespace

namespace optics {

LaueEfficiencyTable LaueEfficiencyTable::FromCsv(const std::string& path) {
  std::ifstream input(path.c_str());
  if (!input) {
    throw std::runtime_error("failed to open Laue efficiency table: " + path);
  }

  std::string line;
  if (!std::getline(input, line)) {
    throw std::runtime_error("Laue efficiency table is empty: " + path);
  }
  const std::vector<std::string> headers = SplitCsvLine(line);
  LaueEfficiencyTable table;
  while (std::getline(input, line)) {
    if (Trim(line).empty()) continue;
    const std::vector<std::string> cells = SplitCsvLine(line);
    std::map<std::string, std::string> row;
    for (std::size_t i = 0; i < headers.size() && i < cells.size(); ++i) {
      row[headers[i]] = cells[i];
    }
    LaueEfficiencyRow parsed;
    parsed.energyKeV = ReadDouble(row, "E_keV");
    parsed.thetaBRad = ReadDouble(row, "theta_B_rad");
    parsed.deltaThetaRad = ReadDouble(row, "delta_theta_rad");
    parsed.material = ReadString(row, "material", "Ge");
    parsed.h = ReadInt(row, "h");
    parsed.k = ReadInt(row, "k");
    parsed.l = ReadInt(row, "l");
    parsed.mosaicFwhmArcmin = ReadDouble(row, "mosaic_fwhm_arcmin");
    parsed.thicknessMm = ReadDouble(row, "thickness_mm");
    parsed.pDiff = ReadDouble(row, "p_diff");
    parsed.pAbs = ReadDouble(row, "p_abs");
    parsed.pTrans = ReadDouble(row, "p_trans");
    parsed.source = ReadString(row, "source", "");
    ValidateProbabilities(parsed);
    table.rows_.push_back(parsed);
  }
  if (table.rows_.empty()) {
    throw std::runtime_error("Laue efficiency table has no data rows: " + path);
  }
  std::sort(
      table.rows_.begin(),
      table.rows_.end(),
      [](const LaueEfficiencyRow& a, const LaueEfficiencyRow& b) {
        if (a.material != b.material) return a.material < b.material;
        if (a.h != b.h) return a.h < b.h;
        if (a.k != b.k) return a.k < b.k;
        if (a.l != b.l) return a.l < b.l;
        if (a.energyKeV != b.energyKeV) return a.energyKeV < b.energyKeV;
        return a.deltaThetaRad < b.deltaThetaRad;
      });
  return table;
}

bool LaueEfficiencyTable::empty() const {
  return rows_.empty();
}

const std::vector<LaueEfficiencyRow>& LaueEfficiencyTable::rows() const {
  return rows_;
}

LaueEfficiencyRow LaueEfficiencyTable::Lookup(
    double energyKeV,
    double deltaThetaRad,
    const std::string& material,
    int h,
    int k,
    int l) const {
  if (rows_.empty()) {
    throw std::runtime_error("Laue efficiency table is empty");
  }

  std::vector<LaueEfficiencyRow> candidates;
  for (const auto& row : rows_) {
    if (row.material == material && row.h == h && row.k == k && row.l == l) {
      candidates.push_back(row);
    }
  }
  if (candidates.empty()) {
    std::ostringstream msg;
    msg << "no Laue efficiency rows for " << material << "(" << h << k << l << ")";
    throw std::runtime_error(msg.str());
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

  std::vector<LaueEfficiencyRow> sameEnergy;
  for (const auto& row : candidates) {
    if (std::fabs(row.energyKeV - nearestEnergy) < 1.0e-9) {
      sameEnergy.push_back(row);
    }
  }
  std::sort(
      sameEnergy.begin(),
      sameEnergy.end(),
      [](const LaueEfficiencyRow& a, const LaueEfficiencyRow& b) {
        return a.deltaThetaRad < b.deltaThetaRad;
      });

  if (sameEnergy.size() == 1) return sameEnergy.front();
  if (deltaThetaRad <= sameEnergy.front().deltaThetaRad) {
    LaueEfficiencyRow out = sameEnergy.front();
    out.source += ":delta_clamped_low";
    return out;
  }
  if (deltaThetaRad >= sameEnergy.back().deltaThetaRad) {
    LaueEfficiencyRow out = sameEnergy.back();
    out.source += ":delta_clamped_high";
    return out;
  }

  for (std::size_t i = 0; i + 1 < sameEnergy.size(); ++i) {
    const auto& lower = sameEnergy[i];
    const auto& upper = sameEnergy[i + 1];
    if (lower.deltaThetaRad <= deltaThetaRad && deltaThetaRad <= upper.deltaThetaRad) {
      return Interpolate(lower, upper, deltaThetaRad);
    }
  }
  return *std::min_element(
      sameEnergy.begin(),
      sameEnergy.end(),
      [deltaThetaRad](const LaueEfficiencyRow& a, const LaueEfficiencyRow& b) {
        return std::fabs(a.deltaThetaRad - deltaThetaRad) <
               std::fabs(b.deltaThetaRad - deltaThetaRad);
      });
}

}  // namespace optics
