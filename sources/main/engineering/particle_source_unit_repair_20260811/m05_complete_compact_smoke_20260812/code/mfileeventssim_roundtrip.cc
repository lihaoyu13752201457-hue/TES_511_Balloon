// Real MEGAlib reader/serializer gate for materialized M05 standalone SIMs.
// This executable performs no transport.  It loads the supplied geometry,
// reads every event through MFileEventsSim, and requires byte-identical
// MSimEvent::ToSimString(All, 17, 101) output plus ID/IA/HT count closure. It
// then exercises the real Revan MRawEventAnalyzer input and analysis paths on
// the hit-populated subset. It never starts Cosima, EventList, or Geant4.

#include "MFileEventsSim.h"
#include "MGlobal.h"
#include "MGeometryRevan.h"
#include "MRawEventAnalyzer.h"
#include "MRERawEvent.h"
#include "MSimEvent.h"
#include "MSimIA.h"

#include "TApplication.h"
#include "TROOT.h"

#include <openssl/sha.h>

#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

const char* const kSchema = "m05-standalone-sim-materializer-v1";

struct ExpectedEvent
{
  unsigned long eventID;
  unsigned long eventListID;
  std::string stableRootID;
  std::string representation;
  unsigned long iaCount;
  unsigned long htCount;
  std::string eventSHA256;
};

void ConfigureRevan(MRawEventAnalyzer& analyzer, MGeometryRevan& geometry,
                    const std::string& simPath)
{
  analyzer.SetGeometry(&geometry);
  analyzer.SetBatch(true);
  analyzer.SetCoincidenceAlgorithm(MRawEventAnalyzer::c_CoincidenceAlgoNone);
  analyzer.SetEventClusteringAlgorithm(MRawEventAnalyzer::c_EventClusteringAlgoNone);
  analyzer.SetHitClusteringAlgorithm(MRawEventAnalyzer::c_HitClusteringAlgoNone);
  analyzer.SetTrackingAlgorithm(MRawEventAnalyzer::c_TrackingAlgoNone);
  analyzer.SetCSRAlgorithm(MRawEventAnalyzer::c_CSRAlgoNone);
  analyzer.SetDecayAlgorithm(MRawEventAnalyzer::c_DecayAlgoNone);
  if (!analyzer.SetInputModeFile(simPath.c_str())) {
    throw std::runtime_error("Revan MRawEventAnalyzer::SetInputModeFile failed");
  }
  if (!analyzer.PreAnalysis()) {
    throw std::runtime_error("Revan MRawEventAnalyzer::PreAnalysis failed");
  }
}

std::vector<std::string> SplitTab(const std::string& line)
{
  std::vector<std::string> result;
  std::string field;
  std::istringstream input(line);
  while (std::getline(input, field, '\t')) result.push_back(field);
  if (!line.empty() && line.back() == '\t') result.push_back("");
  return result;
}

unsigned long StrictUnsigned(const std::string& value, const std::string& name, bool positive)
{
  if (value.empty()) throw std::runtime_error(name + ": empty integer");
  if (value.size() > 1 && value[0] == '0') throw std::runtime_error(name + ": noncanonical integer");
  for (const char c : value) {
    if (c < '0' || c > '9') throw std::runtime_error(name + ": invalid integer");
  }
  std::size_t used = 0;
  const unsigned long result = std::stoul(value, &used);
  if (used != value.size() || (positive && result == 0)) throw std::runtime_error(name + ": invalid range");
  return result;
}

bool IsDigest(const std::string& value)
{
  if (value.size() != 64) return false;
  for (const char c : value) {
    if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return false;
  }
  return true;
}

std::string SHA256Hex(const std::string& value)
{
  unsigned char digest[SHA256_DIGEST_LENGTH];
  ::SHA256(reinterpret_cast<const unsigned char*>(value.data()), value.size(), digest);
  std::ostringstream output;
  output << std::hex << std::setfill('0');
  for (const unsigned char byte : digest) output << std::setw(2) << static_cast<unsigned int>(byte);
  return output.str();
}

std::vector<ExpectedEvent> LoadIndex(const std::string& path)
{
  std::ifstream input(path.c_str(), std::ios::in | std::ios::binary);
  if (!input.good()) throw std::runtime_error("cannot open materialization index");
  const std::vector<std::string> expectedHeader = {
    "schema", "simulation_event_id", "eventlist_id", "stable_root_id", "representation",
    "selection_reason", "standalone_offset", "standalone_length", "standalone_sha256",
    "source_truth_offset", "source_truth_length", "source_truth_sha256", "ia_count", "ht_count",
    "init_tuple_sha256", "raw_tape_line_sha256", "expected_generated_tuple_sha256",
    "expected_eventlist_binary64_sha256", "expected_generated_binary64_sha256",
    "observed_generated_binary64_sha256",
    "serialized_ia_quantized_sha256"
  };
  std::string line;
  if (!std::getline(input, line) || (!line.empty() && line.back() == '\r')) {
    throw std::runtime_error("missing/non-LF materialization index header");
  }
  if (SplitTab(line) != expectedHeader) throw std::runtime_error("wrong exact materialization index header");
  std::vector<ExpectedEvent> result;
  std::set<std::string> roots;
  while (std::getline(input, line)) {
    if (!line.empty() && line.back() == '\r') throw std::runtime_error("CR in materialization index");
    if (line.empty()) throw std::runtime_error("blank materialization index row");
    const std::vector<std::string> fields = SplitTab(line);
    if (fields.size() != expectedHeader.size()) throw std::runtime_error("wrong materialization index field count");
    ExpectedEvent expected;
    if (fields[0] != kSchema) throw std::runtime_error("wrong materialization index schema");
    expected.eventID = StrictUnsigned(fields[1], "simulation_event_id", true);
    expected.eventListID = StrictUnsigned(fields[2], "eventlist_id", true);
    expected.stableRootID = fields[3];
    expected.representation = fields[4];
    if (!IsDigest(expected.stableRootID) || !roots.insert(expected.stableRootID).second) {
      throw std::runtime_error("invalid/duplicate stable root ID");
    }
    if (expected.representation != "native" && expected.representation != "minimal_init") {
      throw std::runtime_error("invalid representation");
    }
    expected.eventSHA256 = fields[8];
    if (!IsDigest(expected.eventSHA256) || !IsDigest(fields[14]) || !IsDigest(fields[15]) ||
        !IsDigest(fields[16]) || !IsDigest(fields[17]) || !IsDigest(fields[18]) || !IsDigest(fields[19]) ||
        !IsDigest(fields[20]) || fields[14] != fields[20] || fields[18] != fields[19]) {
      throw std::runtime_error("invalid index digest");
    }
    expected.iaCount = StrictUnsigned(fields[12], "ia_count", true);
    expected.htCount = StrictUnsigned(fields[13], "ht_count", false);
    if (expected.eventID != result.size()+1 || expected.eventListID != expected.eventID) {
      throw std::runtime_error("index event/EventList order is not contiguous");
    }
    if (expected.representation == "minimal_init" && (expected.iaCount != 1 || expected.htCount != 0)) {
      throw std::runtime_error("minimal INIT index count mismatch");
    }
    result.push_back(expected);
  }
  if (!input.eof() || result.empty()) throw std::runtime_error("index read failure or empty index");
  return result;
}

}  // namespace

int main(int argc, char** argv)
{
  try {
    if (argc != 4) {
      std::cerr << "Usage: mfileeventssim_roundtrip GEOMETRY STANDALONE.sim INDEX.tsv\n";
      return 2;
    }
    const std::string geometryPath = argv[1];
    const std::string simPath = argv[2];
    const std::string indexPath = argv[3];
    const std::vector<ExpectedEvent> expected = LoadIndex(indexPath);

    MGlobal::Initialize("M05StandaloneSIMRoundTrip", "MFileEventsSim materialization gate");
    gROOT->SetBatch(true);
    int appArgc = 1;
    char appName[] = "m05-roundtrip";
    char* appArgv[] = {appName, nullptr};
    TApplication application("M05StandaloneSIMRoundTrip", &appArgc, appArgv);

    MGeometryRevan geometry;
    if (!geometry.ScanSetupFile(geometryPath.c_str())) throw std::runtime_error("geometry scan failed");
    geometry.ActivateNoising(false);
    geometry.SetGlobalFailureRate(0.0);

    MFileEventsSim reader(&geometry);
    if (!reader.Open(simPath.c_str())) throw std::runtime_error("MFileEventsSim::Open failed");
    if (reader.GetVersion() != 101) throw std::runtime_error("MFileEventsSim observed wrong Version");
    if (reader.GetFileType() != "sim") throw std::runtime_error("MFileEventsSim observed wrong Type");
    if (reader.GetGeometryFileName() != geometryPath.c_str()) throw std::runtime_error("MFileEventsSim observed wrong Geometry");

    unsigned long eventCount = 0;
    unsigned long iaCount = 0;
    unsigned long htCount = 0;
    std::ostringstream sequence;
    MSimEvent* event = nullptr;
    while ((event = reader.GetNextEvent(false)) != nullptr) {
      if (eventCount >= expected.size()) {
        delete event;
        throw std::runtime_error("reader returned more events than the index");
      }
      const ExpectedEvent& wanted = expected[eventCount];
      ++eventCount;
      if (event->GetID() != static_cast<long>(wanted.eventID) ||
          event->GetSimulationEventID() != static_cast<long>(wanted.eventID)) {
        delete event;
        throw std::runtime_error("MFileEventsSim event/started ID mismatch");
      }
      const unsigned long observedIA = event->GetNIAs();
      const unsigned long observedHT = event->GetNHTs();
      unsigned long initCount = 0;
      for (unsigned int i = 0; i < event->GetNIAs(); ++i) {
        MSimIA* ia = event->GetIAAt(i);
        if (ia != nullptr && ia->GetProcess() == "INIT") ++initCount;
      }
      if (observedIA != wanted.iaCount || observedHT != wanted.htCount || initCount != 1) {
        delete event;
        throw std::runtime_error("MFileEventsSim IA/HT/unique-INIT count mismatch");
      }
      const std::string roundTrip = event->ToSimString(MSimEvent::c_StoreSimulationInfoAll, 17, 101).Data();
      const std::string roundTripSHA = SHA256Hex(roundTrip);
      if (roundTripSHA != wanted.eventSHA256) {
        delete event;
        throw std::runtime_error("MFileEventsSim parse/ToSimString event hash changed");
      }
      sequence << wanted.eventID << ':' << wanted.eventID << ':' << observedIA << ':' << observedHT
               << ':' << roundTripSHA << '\n';
      iaCount += observedIA;
      htCount += observedHT;
      delete event;
    }
    reader.Close();
    if (eventCount != expected.size()) throw std::runtime_error("MFileEventsSim returned fewer events than the index");

    std::set<unsigned long> expectedHitEventIDs;
    unsigned long expectedHitCount = 0;
    for (const ExpectedEvent& eventExpectation : expected) {
      if (eventExpectation.htCount > 0) {
        expectedHitEventIDs.insert(eventExpectation.eventID);
        expectedHitCount += eventExpectation.htCount;
      }
    }

    unsigned long revanInitialEventCount = 0;
    unsigned long revanInitialRESECount = 0;
    std::set<unsigned long> revanInitialIDs;
    {
      MRawEventAnalyzer analyzer;
      ConfigureRevan(analyzer, geometry, simPath);
      MRERawEvent* raw = nullptr;
      while ((raw = analyzer.GetNextInitialRawEventFromFile()) != nullptr) {
        ++revanInitialEventCount;
        revanInitialRESECount += static_cast<unsigned long>(raw->GetNRESEs());
        revanInitialIDs.insert(raw->GetEventID());
        delete raw;
      }
      if (!analyzer.PostAnalysis()) throw std::runtime_error("Revan initial-reader PostAnalysis failed");
    }
    if (revanInitialIDs != expectedHitEventIDs || revanInitialRESECount != expectedHitCount) {
      throw std::runtime_error("Revan initial raw-event ID/RESE closure differs from hit-populated SIM subset");
    }

    unsigned long revanAnalyzeSuccessCount = 0;
    std::set<unsigned long> revanAnalyzedIDs;
    {
      MRawEventAnalyzer analyzer;
      ConfigureRevan(analyzer, geometry, simPath);
      while (true) {
        const unsigned int code = analyzer.AnalyzeEvent();
        if (code == MRawEventAnalyzer::c_AnalysisNoEventsLeftInFile) break;
        if (code != MRawEventAnalyzer::c_AnalysisSucess) {
          throw std::runtime_error("Revan AnalyzeEvent returned a non-success terminal/intermediate code");
        }
        MRERawEvent* raw = analyzer.GetInitialRawEvent();
        if (raw == nullptr) throw std::runtime_error("Revan AnalyzeEvent success lacks initial raw event");
        ++revanAnalyzeSuccessCount;
        revanAnalyzedIDs.insert(raw->GetEventID());
      }
      if (!analyzer.PostAnalysis()) throw std::runtime_error("Revan analysis PostAnalysis failed");
    }
    if (revanAnalyzedIDs != expectedHitEventIDs || revanAnalyzeSuccessCount != expectedHitEventIDs.size()) {
      throw std::runtime_error("Revan analyzed-event closure differs from hit-populated SIM subset");
    }

    std::ostringstream revanIDs;
    for (const unsigned long id : revanInitialIDs) revanIDs << id << '\n';

    std::cout << "M05_ROUNDTRIP_JSON {\"schema_version\":\"m05-mfileeventssim-roundtrip-v1\","
              << "\"status\":\"PASS__REAL_MFILEEVENTSSIM_ROUNDTRIP__REAL_REVAN_INPUT_AND_ANALYZE\","
              << "\"event_count\":" << eventCount << ",\"ia_count\":" << iaCount
              << ",\"ht_count\":" << htCount << ",\"unique_init_count\":" << eventCount
              << ",\"revan_initial_event_count\":" << revanInitialEventCount
              << ",\"revan_initial_rese_count\":" << revanInitialRESECount
              << ",\"revan_analyze_success_count\":" << revanAnalyzeSuccessCount
              << ",\"revan_hit_event_id_hash_sha256\":\"" << SHA256Hex(revanIDs.str()) << "\""
              << ",\"event_ia_ht_hash_sha256\":\"" << SHA256Hex(sequence.str()) << "\"}" << std::endl;
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "M05 standalone SIM round-trip FAIL: " << error.what() << std::endl;
    return 1;
  }
}
