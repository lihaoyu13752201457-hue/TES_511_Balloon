#include "SimulationData.hh"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <unordered_map>

namespace {

std::vector<std::string> SplitCsv(const std::string& line) {
  std::vector<std::string> out;
  std::string value;
  bool quoted = false;
  for (std::size_t i = 0; i < line.size(); ++i) {
    const char c = line[i];
    if (c == '"') {
      if (quoted && i + 1 < line.size() && line[i + 1] == '"') {
        value.push_back('"');
        ++i;
      } else {
        quoted = !quoted;
      }
    } else if (c == ',' && !quoted) {
      out.push_back(value);
      value.clear();
    } else {
      value.push_back(c);
    }
  }
  out.push_back(value);
  return out;
}

std::string CsvEscape(const std::string& value) {
  if (value.find_first_of(",\"\n\r") == std::string::npos) return value;
  std::string out = "\"";
  for (const char c : value) out += (c == '"' ? "\"\"" : std::string(1, c));
  out += '"';
  return out;
}

std::string Get(const std::vector<std::string>& row,
                const std::unordered_map<std::string, std::size_t>& col,
                const std::string& name, const std::string& fallback = "") {
  const auto it = col.find(name);
  return (it == col.end() || it->second >= row.size()) ? fallback : row[it->second];
}

std::string GetAny(const std::vector<std::string>& row,
                   const std::unordered_map<std::string, std::size_t>& col,
                   const std::vector<std::string>& names,
                   const std::string& fallback = "") {
  for (const auto& name : names) {
    const auto it = col.find(name);
    if (it != col.end() && it->second < row.size() && !row[it->second].empty()) {
      return row[it->second];
    }
  }
  return fallback;
}

double ToDouble(const std::string& value, const std::string& field,
                std::size_t lineNumber, double fallback = 0.) {
  if (value.empty()) return fallback;
  try {
    std::size_t used = 0;
    const double out = std::stod(value, &used);
    if (used != value.size() || !std::isfinite(out)) throw std::runtime_error("bad");
    return out;
  } catch (...) {
    throw std::runtime_error("invalid " + field + " at CSV line " +
                             std::to_string(lineNumber) + ": " + value);
  }
}

long long ToLong(const std::string& value, const std::string& field,
                 std::size_t lineNumber, long long fallback = 0) {
  if (value.empty()) return fallback;
  try {
    std::size_t used = 0;
    const long long out = std::stoll(value, &used);
    if (used != value.size()) throw std::runtime_error("bad");
    return out;
  } catch (...) {
    throw std::runtime_error("invalid " + field + " at CSV line " +
                             std::to_string(lineNumber) + ": " + value);
  }
}

bool ToBool(const std::string& value) {
  return value == "1" || value == "true" || value == "True" || value == "TRUE";
}

std::string RequireOption(int& i, int argc, char** argv) {
  if (++i >= argc) throw std::runtime_error(std::string("missing value after ") + argv[i - 1]);
  return argv[i];
}

}  // namespace

std::vector<DepositGroup> LoadDepositGroups(const std::string& path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open deposit CSV: " + path);

  std::string line;
  if (!std::getline(input, line)) throw std::runtime_error("empty deposit CSV: " + path);
  if (!line.empty() && line.back() == '\r') line.pop_back();
  const auto header = SplitCsv(line);
  std::unordered_map<std::string, std::size_t> col;
  for (std::size_t i = 0; i < header.size(); ++i) col[header[i]] = i;

  const std::vector<std::string> energyNames = {"edep_keV", "energy_keV"};
  const std::vector<std::string> xNames = {"slab_local_x_mm", "local_x_mm"};
  const std::vector<std::string> yNames = {"slab_local_y_mm", "local_y_mm"};
  const std::vector<std::string> zNames = {"slab_local_z_mm", "local_z_mm"};
  if (GetAny(header, col, energyNames).empty()) {
    // Header lookup above intentionally uses the generic helper; detect by key too.
    bool found = false;
    for (const auto& n : energyNames) found = found || col.count(n);
    if (!found) throw std::runtime_error("deposit CSV lacks edep_keV/energy_keV");
  }
  for (const auto& names : {xNames, yNames, zNames}) {
    bool found = false;
    for (const auto& n : names) found = found || col.count(n);
    if (!found) throw std::runtime_error("deposit CSV lacks a required local-coordinate column");
  }

  std::vector<DepositGroup> groups;
  std::unordered_map<std::string, std::size_t> groupIndex;
  std::size_t lineNumber = 1;
  while (std::getline(input, line)) {
    ++lineNumber;
    if (!line.empty() && line.back() == '\r') line.pop_back();
    if (line.empty() || line[0] == '#') continue;
    const auto row = SplitCsv(line);

    Deposit d;
    d.eventOrder = static_cast<int>(ToLong(
        GetAny(row, col, {"event_order", "source_event_order", "group_event_index"}, "0"),
        "event_order", lineNumber));
    d.hitOrder = static_cast<int>(ToLong(
        GetAny(row, col, {"hit_order", "hit_id", "group_hit_index"}, "0"),
        "hit_order", lineNumber));
    d.layer = static_cast<int>(ToLong(Get(row, col, "layer", "0"), "layer", lineNumber));
    d.sampleId = GetAny(row, col, {"sample_id", "original_sample_id"}, "synthetic");
    d.jobId = GetAny(row, col, {"job_id", "original_job_id"}, "synthetic");
    d.originalEventId = ToLong(
        GetAny(row, col, {"event_id", "original_event_id", "group_event_index"}, "0"),
        "event_id", lineNumber);
    d.candidate = Get(row, col, "candidate", "");
    d.strictRecoil = ToBool(Get(row, col, "strict_recoil_event", "0"));
    d.directTesKeV = ToDouble(
        GetAny(row, col, {"tes_total_keV", "direct_tes_keV", "event_tes_direct_keV"}, "0"),
        "direct TES energy", lineNumber);
    d.bgoKeV = ToDouble(
        GetAny(row, col, {"bgo_total_keV", "event_bgo_total_keV"}, "0"),
        "BGO energy", lineNumber);
    d.localXmm = ToDouble(GetAny(row, col, xNames), "local_x_mm", lineNumber);
    d.localYmm = ToDouble(GetAny(row, col, yNames), "local_y_mm", lineNumber);
    d.localZmm = ToDouble(GetAny(row, col, zNames), "local_z_mm", lineNumber);
    d.timeNs = ToDouble(GetAny(row, col, {"time_ns", "hit_time_ns"}, "0"),
                        "time_ns", lineNumber);
    d.energyKeV = ToDouble(GetAny(row, col, energyNames), "energy_keV", lineNumber);
    if (!(d.energyKeV > 0.)) throw std::runtime_error("non-positive deposit energy at CSV line " + std::to_string(lineNumber));
    if (d.layer < 0 || d.layer > 5) throw std::runtime_error("layer outside [0,5] at CSV line " + std::to_string(lineNumber));

    std::string key = GetAny(row, col,
                             {"group_key", "input_event_key", "synthetic_point_id"}, "");
    if (key.empty()) {
      key = d.sampleId + "|" + d.jobId + "|" + std::to_string(d.originalEventId) +
            "|L" + std::to_string(d.layer);
    } else {
      // Every Geant4 event represents one physical Si slab/layer.  The
      // prepared input key identifies the original event, so append layer.
      key += "|L" + std::to_string(d.layer);
    }
    auto found = groupIndex.find(key);
    if (found == groupIndex.end()) {
      DepositGroup g;
      g.groupKey = key;
      g.eventOrder = d.eventOrder;
      g.layer = d.layer;
      g.sampleId = d.sampleId;
      g.jobId = d.jobId;
      g.originalEventId = d.originalEventId;
      g.candidate = d.candidate;
      g.strictRecoil = d.strictRecoil;
      g.directTesKeV = d.directTesKeV;
      g.bgoKeV = d.bgoKeV;
      g.referenceTimeNs = d.timeNs;
      groupIndex[key] = groups.size();
      groups.push_back(g);
      found = groupIndex.find(key);
    }
    auto& g = groups[found->second];
    if (g.layer != d.layer || g.jobId != d.jobId ||
        g.originalEventId != d.originalEventId) {
      throw std::runtime_error("group_key maps incompatible rows at CSV line " + std::to_string(lineNumber));
    }
    g.deposits.push_back(d);
    g.inputEnergyKeV += d.energyKeV;
    g.referenceTimeNs = std::min(g.referenceTimeNs, d.timeNs);
  }
  if (groups.empty()) throw std::runtime_error("deposit CSV has no data rows: " + path);

  std::stable_sort(groups.begin(), groups.end(), [](const auto& a, const auto& b) {
    if (a.eventOrder != b.eventOrder) return a.eventOrder < b.eventOrder;
    if (a.layer != b.layer) return a.layer < b.layer;
    return a.groupKey < b.groupKey;
  });
  for (std::size_t i = 0; i < groups.size(); ++i) {
    groups[i].simEventId = static_cast<int>(i);
    std::stable_sort(groups[i].deposits.begin(), groups[i].deposits.end(),
                     [](const auto& a, const auto& b) {
      if (a.timeNs != b.timeNs) return a.timeNs < b.timeNs;
      return a.hitOrder < b.hitOrder;
    });
  }
  return groups;
}

std::vector<Pixel> LoadPixels(const std::string& path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open pixel CSV: " + path);
  std::string line;
  if (!std::getline(input, line)) throw std::runtime_error("empty pixel CSV: " + path);
  if (!line.empty() && line.back() == '\r') line.pop_back();
  const auto header = SplitCsv(line);
  std::unordered_map<std::string, std::size_t> col;
  for (std::size_t i = 0; i < header.size(); ++i) col[header[i]] = i;
  for (const auto& name : {"pixel_id", "y_mm", "z_mm"}) {
    if (!col.count(name)) throw std::runtime_error("pixel CSV lacks column " + std::string(name));
  }
  std::vector<Pixel> pixels;
  std::size_t lineNumber = 1;
  while (std::getline(input, line)) {
    ++lineNumber;
    if (!line.empty() && line.back() == '\r') line.pop_back();
    if (line.empty() || line[0] == '#') continue;
    const auto row = SplitCsv(line);
    Pixel p;
    p.id = static_cast<int>(ToLong(Get(row, col, "pixel_id"), "pixel_id", lineNumber));
    p.ymm = ToDouble(Get(row, col, "y_mm"), "y_mm", lineNumber);
    p.zmm = ToDouble(Get(row, col, "z_mm"), "z_mm", lineNumber);
    pixels.push_back(p);
  }
  std::sort(pixels.begin(), pixels.end(), [](const auto& a, const auto& b) { return a.id < b.id; });
  if (pixels.size() != 376) {
    throw std::runtime_error("expected exactly 376 TES pixels, got " + std::to_string(pixels.size()));
  }
  for (std::size_t i = 0; i < pixels.size(); ++i) {
    if (pixels[i].id != static_cast<int>(i)) {
      throw std::runtime_error("pixel IDs must be contiguous 0..375");
    }
  }
  return pixels;
}

std::vector<int> AllocatePacketCounts(const DepositGroup& group,
                                      const RunConfig& config) {
  if (config.packetsPerGroup <= 0) {
    return std::vector<int>(group.deposits.size(), config.packetsPerHit);
  }
  if (config.packetsPerGroup < static_cast<int>(group.deposits.size())) {
    throw std::runtime_error("packets-per-group is smaller than deposit count for " +
                             group.groupKey);
  }
  std::vector<int> counts(group.deposits.size(), 1);
  const int remaining = config.packetsPerGroup - static_cast<int>(group.deposits.size());
  struct Fraction { std::size_t index; double remainder; };
  std::vector<Fraction> fractions;
  int assigned = 0;
  for (std::size_t i = 0; i < group.deposits.size(); ++i) {
    const double exact = remaining * group.deposits[i].energyKeV / group.inputEnergyKeV;
    const int whole = static_cast<int>(std::floor(exact));
    counts[i] += whole;
    assigned += whole;
    fractions.push_back({i, exact - whole});
  }
  std::stable_sort(fractions.begin(), fractions.end(), [](const auto& a, const auto& b) {
    if (a.remainder != b.remainder) return a.remainder > b.remainder;
    return a.index < b.index;
  });
  for (int i = assigned; i < remaining; ++i) ++counts[fractions[i - assigned].index];
  return counts;
}

void WriteEventMap(const std::string& path,
                   const std::vector<DepositGroup>& groups,
                   const RunConfig& config) {
  std::ofstream out(path, std::ios::trunc);
  if (!out) throw std::runtime_error("cannot write event map: " + path);
  out << "sim_event_id,group_key,event_order,sample_id,job_id,event_id,layer,candidate,"
         "strict_recoil_event,direct_tes_keV,bgo_total_keV,deposit_count,input_energy_keV,"
         "reference_time_ns,primary_packet_count,packet_energy_meV\n";
  out << std::setprecision(17);
  for (const auto& g : groups) {
    const auto packetCounts = AllocatePacketCounts(g, config);
    const int primaryPackets = std::accumulate(packetCounts.begin(), packetCounts.end(), 0);
    out << g.simEventId << ',' << CsvEscape(g.groupKey) << ',' << g.eventOrder << ','
        << CsvEscape(g.sampleId) << ',' << CsvEscape(g.jobId) << ',' << g.originalEventId << ','
        << g.layer << ',' << CsvEscape(g.candidate) << ',' << (g.strictRecoil ? 1 : 0) << ','
        << g.directTesKeV << ',' << g.bgoKeV << ',' << g.deposits.size() << ','
        << g.inputEnergyKeV << ',' << g.referenceTimeNs << ','
        << primaryPackets << ','
        << config.packetEnergyMeV << '\n';
  }
}

void PrintUsage(const char* argv0) {
  std::cerr
      << "Usage: " << argv0 << " --input deposits.csv --pixels tes_pixel_map.csv\n"
      << "  --output hits.csv --event-map event_map.csv --summary summary.json\n"
      << "  [--packets-per-hit 128 | --packets-per-group N] [--packet-energy-meV 2.7]\n"
      << "  [--sensor-area-scale 1] [--sensor-absorption 0.3]\n"
      << "  [--bath-absorption 0.1] [--specular-probability 0]\n"
      << "  [--max-phonon-bounces 20000] [--miller-h 1 --miller-k 0 --miller-l 0]\n"
      << "  [--seed1 240903 --seed2 511420]\n";
}

RunConfig ParseArguments(int argc, char** argv) {
  RunConfig c;
  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    if (arg == "--help" || arg == "-h") {
      PrintUsage(argv[0]);
      std::exit(0);
    } else if (arg == "--input") c.inputCsv = RequireOption(i, argc, argv);
    else if (arg == "--pixels") c.pixelCsv = RequireOption(i, argc, argv);
    else if (arg == "--output") c.outputCsv = RequireOption(i, argc, argv);
    else if (arg == "--event-map") c.eventMapCsv = RequireOption(i, argc, argv);
    else if (arg == "--summary") c.summaryJson = RequireOption(i, argc, argv);
    else if (arg == "--packets-per-hit") c.packetsPerHit = std::stoi(RequireOption(i, argc, argv));
    else if (arg == "--packets-per-group") c.packetsPerGroup = std::stoi(RequireOption(i, argc, argv));
    else if (arg == "--packet-energy-meV") c.packetEnergyMeV = std::stod(RequireOption(i, argc, argv));
    else if (arg == "--sensor-area-scale") c.sensorAreaScale = std::stod(RequireOption(i, argc, argv));
    else if (arg == "--sensor-absorption") c.sensorAbsorption = std::stod(RequireOption(i, argc, argv));
    else if (arg == "--bath-absorption") c.bathAbsorption = std::stod(RequireOption(i, argc, argv));
    else if (arg == "--specular-probability") c.specularProbability = std::stod(RequireOption(i, argc, argv));
    else if (arg == "--max-phonon-bounces") c.maxPhononBounces = std::stoi(RequireOption(i, argc, argv));
    else if (arg == "--miller-h") c.millerH = std::stoi(RequireOption(i, argc, argv));
    else if (arg == "--miller-k") c.millerK = std::stoi(RequireOption(i, argc, argv));
    else if (arg == "--miller-l") c.millerL = std::stoi(RequireOption(i, argc, argv));
    else if (arg == "--seed1") c.seed1 = std::stol(RequireOption(i, argc, argv));
    else if (arg == "--seed2") c.seed2 = std::stol(RequireOption(i, argc, argv));
    else throw std::runtime_error("unknown argument: " + arg);
  }
  for (const auto* value : {&c.inputCsv, &c.pixelCsv, &c.outputCsv, &c.eventMapCsv, &c.summaryJson}) {
    if (value->empty()) throw std::runtime_error("all five path options are required");
  }
  if (c.packetsPerHit <= 0) throw std::runtime_error("packets-per-hit must be positive");
  if (c.packetsPerGroup < 0) throw std::runtime_error("packets-per-group cannot be negative");
  if (!(c.packetEnergyMeV > 0.)) throw std::runtime_error("packet-energy-meV must be positive");
  if (!(c.sensorAreaScale > 0. && c.sensorAreaScale <= 1.)) throw std::runtime_error("sensor-area-scale must be in (0,1]");
  for (const auto& item : {std::make_pair(c.sensorAbsorption, "sensor-absorption"),
                           std::make_pair(c.bathAbsorption, "bath-absorption"),
                           std::make_pair(c.specularProbability, "specular-probability")}) {
    if (item.first < 0. || item.first > 1.) throw std::runtime_error(std::string(item.second) + " must be in [0,1]");
  }
  if (c.maxPhononBounces <= 0) throw std::runtime_error("max-phonon-bounces must be positive");
  if (c.millerH == 0 && c.millerK == 0 && c.millerL == 0) throw std::runtime_error("Miller indices cannot all be zero");
  return c;
}

std::string JsonEscape(const std::string& in) {
  std::ostringstream out;
  for (const unsigned char c : in) {
    switch (c) {
      case '\\': out << "\\\\"; break;
      case '"': out << "\\\""; break;
      case '\n': out << "\\n"; break;
      case '\r': out << "\\r"; break;
      case '\t': out << "\\t"; break;
      default:
        if (c < 0x20) out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << int(c);
        else out << c;
    }
  }
  return out.str();
}
