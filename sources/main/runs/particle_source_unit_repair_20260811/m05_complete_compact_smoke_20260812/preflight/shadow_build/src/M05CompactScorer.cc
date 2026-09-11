#include "M05CompactScorer.hh"
#include "M05FrozenInput.hh"
#include "M05VetoPolicy.hh"

#include "MCEventAction.hh"
#include "MCParameterFile.hh"
#include "MCRun.hh"
#include "MCRunManager.hh"
#include "MSimEvent.h"
#include "MSimIA.h"

#include "G4Ions.hh"
#include "G4Event.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "G4ParticleDefinition.hh"
#include "G4GeneralParticleSource.hh"
#include "G4PrimaryParticle.hh"
#include "G4PrimaryVertex.hh"
#include "G4Step.hh"
#include "G4StepPoint.hh"
#include "G4SystemOfUnits.hh"
#include "G4TouchableHistory.hh"
#include "G4Track.hh"
#include "G4Threading.hh"
#include "G4VPhysicalVolume.hh"

#include <openssl/sha.h>

#include <algorithm>
#include <cerrno>
#include <cctype>
#include <csignal>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <iterator>
#include <limits>
#include <sstream>
#include <stdexcept>

#include <fcntl.h>
#include <limits.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

namespace {

const char* const kWhitelistSHA256 = "36f5c55f81cad8ab1f134c55e3d3efc699856d91571d9f8eef37c19fe6f12e3a";
volatile std::sig_atomic_t g_M05TerminationRequested = 0;

const char* const kMassCSI[] = {
  "CsI_Side_Segment_00", "CsI_Side_Segment_01", "CsI_Side_Segment_02",
  "CsI_Side_Segment_03_below_side_port", "CsI_Side_Segment_03_above_side_port",
  "CsI_Side_Segment_03_rectcut_window_band", "CsI_Side_Segment_04_below_side_port",
  "CsI_Side_Segment_04_above_side_port", "CsI_Side_Segment_04_rectcut_window_band",
  "CsI_Side_Segment_05", "CsI_Side_Segment_06", "CsI_Side_Segment_07",
  "CsI_Bottom_Quadrant_00", "CsI_Bottom_Quadrant_01", "CsI_Bottom_Quadrant_02", "CsI_Bottom_Quadrant_03",
  "CsI_TopAnnulus_Segment_00", "CsI_TopAnnulus_Segment_01", "CsI_TopAnnulus_Segment_02",
  "CsI_TopAnnulus_Segment_03", "CsI_TopAnnulus_Segment_04", "CsI_TopAnnulus_Segment_05",
  "CsI_TopAnnulus_Segment_06", "CsI_TopAnnulus_Segment_07"
};
const char* const kO8BGO[] = {
  "BGO_S3C_FullWrap_SideShell_WindowCut_40mm", "BGO_S3D_O8_FullWrap_BottomCap_30mm",
  "BGO_S3D_O8_FullWrap_TopAnnulus_10mm"
};
const char* const kO8Plastic[] = {
  "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm", "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
  "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm"
};

std::vector<std::string> SplitTab(const std::string& line)
{
  std::vector<std::string> fields;
  std::string field;
  std::istringstream input(line);
  while (std::getline(input, field, '\t')) fields.push_back(field);
  if (!line.empty() && line.back() == '\t') fields.push_back("");
  return fields;
}

double StrictDouble(const std::string& value)
{
  std::size_t used = 0;
  const double result = std::stod(value, &used);
  if (used != value.size() || !std::isfinite(result)) throw std::runtime_error("invalid finite double");
  return result;
}

long StrictLong(const std::string& value)
{
  std::size_t used = 0;
  const long result = std::stol(value, &used);
  if (used != value.size()) throw std::runtime_error("invalid integer");
  return result;
}

bool Near(double left, double right, double absolute = 1.0e-12, double relative = 1.0e-12)
{
  return std::fabs(left-right) <= std::max(absolute, relative*std::max(std::fabs(left), std::fabs(right)));
}

bool IsLowerHexDigest(const std::string& value)
{
  if (value.size() != 64) return false;
  for (const unsigned char c : value) {
    if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return false;
  }
  return true;
}

std::string RequiredEnvironment(const char* name)
{
  const char* value = std::getenv(name);
  if (value == nullptr || value[0] == '\0') throw std::runtime_error(std::string("missing environment ") + name);
  return value;
}

std::string ParentDirectory(const std::string& path)
{
  const std::string::size_type slash = path.find_last_of('/');
  if (slash == std::string::npos) return ".";
  if (slash == 0) return "/";
  return path.substr(0, slash);
}

void RequireRegularNoLink(const std::string& path)
{
  struct stat info;
  if (::lstat(path.c_str(), &info) != 0 || !S_ISREG(info.st_mode) || S_ISLNK(info.st_mode)) {
    throw std::runtime_error("missing/non-regular/symlinked file: " + path);
  }
}

void RequireAbsolutePathWithoutSymlinkComponents(const std::string& path, bool requireLeaf)
{
  if (path.empty() || path[0] != '/') throw std::runtime_error("path is not absolute: " + path);
  std::string current;
  std::istringstream parts(path);
  std::string part;
  while (std::getline(parts, part, '/')) {
    if (part.empty()) continue;
    if (part == "." || part == "..") throw std::runtime_error("dot component in path: " + path);
    current += "/" + part;
    struct stat state;
    errno = 0;
    if (::lstat(current.c_str(), &state) != 0) {
      const bool isLeaf = current == path;
      if (!isLeaf || requireLeaf || errno != ENOENT) {
        throw std::runtime_error("uninspectable lexical path component: " + current);
      }
      return;
    }
    if (S_ISLNK(state.st_mode)) throw std::runtime_error("symlink lexical path component: " + current);
  }
}

void SyncDirectory(const std::string& path)
{
  const int descriptor = ::open(path.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW);
  if (descriptor < 0) throw std::runtime_error("cannot open directory for fsync: " + path);
  const int result = ::fsync(descriptor);
  const int saved = errno;
  ::close(descriptor);
  if (result != 0) throw std::runtime_error("directory fsync failed: " + path + ": " + std::strerror(saved));
}

void SyncExistingRegularFile(const std::string& path)
{
  RequireRegularNoLink(path);
  const int descriptor = ::open(path.c_str(), O_RDONLY | O_NOFOLLOW);
  if (descriptor < 0) throw std::runtime_error("cannot open file for fsync: " + path);
  const int result = ::fsync(descriptor);
  const int saved = errno;
  ::close(descriptor);
  if (result != 0) throw std::runtime_error("file fsync failed: " + path + ": " + std::strerror(saved));
}

unsigned long long FileSize(const std::string& path)
{
  struct stat info;
  RequireRegularNoLink(path);
  if (::stat(path.c_str(), &info) != 0 || info.st_size < 0) throw std::runtime_error("cannot stat file: " + path);
  return static_cast<unsigned long long>(info.st_size);
}

std::string JsonEscape(const std::string& value)
{
  std::ostringstream out;
  for (const unsigned char c : value) {
    switch (c) {
    case '\\': out << "\\\\"; break;
    case '"': out << "\\\""; break;
    case '\b': out << "\\b"; break;
    case '\f': out << "\\f"; break;
    case '\n': out << "\\n"; break;
    case '\r': out << "\\r"; break;
    case '\t': out << "\\t"; break;
    default:
      if (c < 0x20) out << "\\u00" << std::hex << std::setw(2) << std::setfill('0') << static_cast<unsigned int>(c) << std::dec;
      else out << static_cast<char>(c);
    }
  }
  return out.str();
}

void WriteDurableExclusive(const std::string& path, const std::string& data)
{
  const int descriptor = ::open(path.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0660);
  if (descriptor < 0) throw std::runtime_error("refusing to overwrite transaction manifest: " + path);
  struct stat state;
  if (::fstat(descriptor, &state) != 0 || !S_ISREG(state.st_mode) || state.st_nlink != 1) {
    ::close(descriptor);
    throw std::runtime_error("transaction manifest is not a single-link regular file: " + path);
  }
  std::size_t offset = 0;
  while (offset < data.size()) {
    const ssize_t written = ::write(descriptor, data.data()+offset, data.size()-offset);
    if (written <= 0) {
      const int saved = errno;
      ::close(descriptor);
      throw std::runtime_error("manifest write failed: " + std::string(std::strerror(saved)));
    }
    offset += static_cast<std::size_t>(written);
  }
  if (::fsync(descriptor) != 0) {
    const int saved = errno;
    ::close(descriptor);
    throw std::runtime_error("manifest fsync failed: " + std::string(std::strerror(saved)));
  }
  if (::close(descriptor) != 0) throw std::runtime_error("manifest close failed");
}

template <std::size_t N>
bool Contains(const char* const (&values)[N], const std::string& value)
{
  for (std::size_t i = 0; i < N; ++i) if (value == values[i]) return true;
  return false;
}

} // namespace

M05CompactScorer& M05CompactScorer::Instance()
{
  static M05CompactScorer scorer;
  return scorer;
}

void M05CompactScorer::NotifyTerminationSignal()
{
  g_M05TerminationRequested = 1;
}

bool M05CompactScorer::TerminationRequested()
{
  return g_M05TerminationRequested != 0;
}

M05CompactScorer::M05CompactScorer() :
  m_Configured(false), m_Finalized(false), m_ShardIndex(-1), m_Seed(-1),
  m_RootCount(0), m_GeneratedObservationRowCount(0), m_InitCount(0), m_SECount(0), m_IDCount(0),
  m_EventRowCount(0), m_PixelRowCount(0), m_DepositRowCount(0),
  m_VetoBlockRowCount(0), m_TruthIndexRowCount(0), m_TESZeroControlCount(0), m_GeneratedParticle(0),
  m_GeneratedExcitationKeV(0.0), m_GeneratedSourceTimeSeconds(0.0),
  m_GeneratedEnergyKeV(0.0), m_DepositSequence(0), m_RPCount(0), m_NativeAddedIsotopeCount(0),
  m_KaptonDiagnosticKeV(0.0)
{
  std::fill(m_GeneratedPosition, m_GeneratedPosition+3, 0.0);
  std::fill(m_GeneratedDirection, m_GeneratedDirection+3, 0.0);
  std::fill(m_GeneratedPolarization, m_GeneratedPolarization+3, 0.0);
}

M05CompactScorer::~M05CompactScorer()
{
  // Any exception, signal, timeout, abort, or failed count closure intentionally
  // leaves only the .m05cc.partial directory.  Destruction never publishes it.
}

void M05CompactScorer::Require(bool condition, const std::string& message) const
{
  if (!condition) throw std::runtime_error("M05CompactScorer fail-closed: " + message);
}

void M05CompactScorer::ConfigureAfterInitialization(MCParameterFile& parameters, long actualCommandLineSeed)
{
  Require(!m_Configured, "configured twice");
  Require(!G4Threading::IsMultithreadedApplication(), "shadow scorer rejects a Geant4 MT application");
  Require(MCRunManager::GetMCRunManager() != nullptr,
          "initialized single-thread MCRunManager authority is absent");
  m_Arm = RequiredEnvironment("TES511_SMOKE_ARM");
  m_Geometry = RequiredEnvironment("TES511_GEOMETRY");
  m_Mode = RequiredEnvironment("TES511_MODE");
  m_Family = RequiredEnvironment("TES511_FAMILY");
  m_JobID = RequiredEnvironment("TES511_JOB_ID");
  m_ShardIndex = StrictLong(RequiredEnvironment("TES511_SHARD_INDEX"));
  m_Seed = StrictLong(RequiredEnvironment("TES511_SEED"));
  const std::string tape = RequiredEnvironment("TES511_TAPE_ROOT_SIDECAR");
  m_OutputPrefix = RequiredEnvironment("TES511_OUTPUT_PREFIX");
  const std::string allowedDirectory = RequiredEnvironment("TES511_ALLOWED_RUN_DIRECTORY");
  m_RecordSchemaSHA256 = RequiredEnvironment("TES511_RECORD_SCHEMA_SHA256");
  m_N1CommitSchemaSHA256 = RequiredEnvironment("TES511_N1_COMMIT_SCHEMA_SHA256");
  m_WhitelistSHA256 = RequiredEnvironment("TES511_VETO_WHITELIST_SHA256");
  m_GeometryClassificationSHA256 = RequiredEnvironment("TES511_GEOMETRY_CLASSIFICATION_SHA256");
  m_GeometryBundleSHA256 = RequiredEnvironment("TES511_GEOMETRY_BUNDLE_SHA256");
  m_TapeSHA256 = RequiredEnvironment("TES511_TAPE_ROOT_SIDECAR_SHA256");
  m_RuntimeSourceCardSHA256 = RequiredEnvironment("TES511_RUNTIME_SOURCE_CARD_SHA256");
  m_CorrectedSourceCardSHA256 = RequiredEnvironment("TES511_CORRECTED_SOURCE_CARD_SHA256");
  m_SourceContractSHA256 = RequiredEnvironment("TES511_SOURCE_CONTRACT_SHA256");

  Require(m_Arm == "C" || m_Arm == "N1", "shadow executable permits only C or N1");
  Require(m_Geometry == "mass_model_511" || m_Geometry == "s3d_o8", "unknown geometry identity");
  Require(m_Mode == "instant" || m_Mode == "buildup", "unknown mode identity");
  Require(m_ShardIndex >= 0 && m_Seed > 0 && m_Seed <= 2147483646L, "invalid shard/seed identity");
  Require(actualCommandLineSeed == m_Seed,
          "actual parsed command-line seed differs from harness identity");
  Require(IsLowerHexDigest(m_RecordSchemaSHA256), "invalid record schema digest");
  Require(IsLowerHexDigest(m_N1CommitSchemaSHA256), "invalid N1 commit schema digest");
  Require(IsLowerHexDigest(m_GeometryClassificationSHA256), "invalid geometry-classification digest");
  Require(IsLowerHexDigest(m_GeometryBundleSHA256) && IsLowerHexDigest(m_TapeSHA256) &&
          IsLowerHexDigest(m_RuntimeSourceCardSHA256) && IsLowerHexDigest(m_CorrectedSourceCardSHA256) &&
          IsLowerHexDigest(m_SourceContractSHA256),
          "invalid tape/source/geometry provenance digest");
  Require(m_WhitelistSHA256 == kWhitelistSHA256, "active-volume whitelist digest drift");
  Require(!m_JobID.empty() && m_JobID.size() <= 128, "invalid job ID length");
  for (const unsigned char c : m_JobID) {
    Require(std::isalnum(c) || c == '.' || c == '_' || c == '-', "invalid job ID character");
  }
  Require(!m_OutputPrefix.empty() && m_OutputPrefix[0] == '/' && allowedDirectory.size() > 1 &&
          allowedDirectory[0] == '/', "run/output paths must be absolute");
  Require(m_OutputPrefix.find("..") == std::string::npos && allowedDirectory.find("..") == std::string::npos,
          "parent traversal in run/output path");
  RequireAbsolutePathWithoutSymlinkComponents(allowedDirectory, true);
  RequireAbsolutePathWithoutSymlinkComponents(ParentDirectory(m_OutputPrefix), true);
  RequireAbsolutePathWithoutSymlinkComponents(m_OutputPrefix, false);
  RequireAbsolutePathWithoutSymlinkComponents(tape, true);
  char resolvedAllowed[PATH_MAX];
  char resolvedParent[PATH_MAX];
  Require(::realpath(allowedDirectory.c_str(), resolvedAllowed) != nullptr, "allowed run directory does not resolve");
  Require(::realpath(ParentDirectory(m_OutputPrefix).c_str(), resolvedParent) != nullptr, "output parent does not resolve");
  Require(std::string(resolvedAllowed) == std::string(resolvedParent), "output parent differs from allowed run directory");

  const M05FrozenInput tapeAuthority = M05ReadFrozenInputOneDescriptor(tape);
  Require(tapeAuthority.sha256 == m_TapeSHA256, "tape sidecar digest differs from harness identity");
  LoadTapeBytes(tapeAuthority.bytes);
  Require(!m_Tape.empty(), "empty tape sidecar");
  Require(m_Tape.front().family == m_Family && m_Tape.front().mode == m_Mode, "environment/tape cell mismatch");
  for (const TapeRow& row : m_Tape) {
    Require(row.sourceCardSHA256 == m_CorrectedSourceCardSHA256 &&
            row.sourceContractSHA256 == m_SourceContractSHA256,
            "tape/source-card/source-contract provenance mismatch");
  }
  Require(parameters.GetNRuns() == 1, "parameter file must contain exactly one run");
  Require(parameters.GetPreTriggerMode() == MCParameterFile::c_PreTriggerEverything,
          "PreTriggerMode must be Everything");
  Require(parameters.StoreSimulationInfo() == MSimEvent::c_StoreSimulationInfoAll,
          "StoreSimulationInfo must be All");
  Require(parameters.StoreOneHitPerEvent() == false, "StoreOneHitPerEvent must be false");
  const std::string runtimeSourceCard = parameters.GetFileName().ToString();
  RequireAbsolutePathWithoutSymlinkComponents(runtimeSourceCard, true);
  Require(SHA256File(runtimeSourceCard) == m_RuntimeSourceCardSHA256,
          "actual parsed runtime source card differs from harness identity");
  MCRun& run = parameters.GetCurrentRun();
  Require(run.GetStopCondition() == MCRun::c_StopByEvents && run.GetEvents() == static_cast<long>(m_Tape.size()),
          "run event stop/count differs from frozen tape");
  Require(run.GetFileName() == "", "C/N1 must disable native rich event-file output");
  m_StageDirectory = m_OutputPrefix + ".m05cc.partial";
  m_FinalDirectory = m_OutputPrefix + ".m05cc";
  struct stat info;
  Require(::lstat(m_StageDirectory.c_str(), &info) != 0 && errno == ENOENT, "partial transaction path already exists");
  Require(::lstat(m_FinalDirectory.c_str(), &info) != 0 && errno == ENOENT, "final transaction path already exists");
  Require(::mkdir(m_StageDirectory.c_str(), 0700) == 0, "cannot create transaction staging directory");
  m_TapePath = "tape_roots.tsv";
  WriteDurableExclusive(m_StageDirectory + "/" + m_TapePath, tapeAuthority.bytes);
  Require(SHA256File(m_StageDirectory + "/" + m_TapePath) == m_TapeSHA256,
          "transactional tape-root copy differs from validated input");
  Require(run.GetIsotopeStoreFileName().ToString() == m_StageDirectory + "/native",
          "native isotope DAT base is outside transaction envelope");
  OpenOutputs();
  m_Configured = true;
}

void M05CompactScorer::OpenOutputs()
{
  const std::string roots = m_StageDirectory + "/roots.tsv";
  m_RootOut.OpenExclusive(roots);
  Require(m_RootOut.good(), "cannot open root output");
  m_RootOut << "simulation_event_id\trow_index0\teventlist_id\tstable_root_id\tbenchmark_driver_id\t"
               "driver_inference\tdriver_inference_quality\tdriver_inference_ambiguity_set\tfamily\tgenerated_flag\t"
               "started_flag\tnative_event_populated\tcompleted_flag\taborted_flag\traw_tape_line_sha256\t"
               "expected_generated_tuple_sha256\tobserved_generated_tuple_sha256\tobserved_ia_init_tuple_sha256\t"
               "control_flag\n";
  m_GeneratedObservationOut.OpenExclusive(m_StageDirectory + "/generated_observations.tsv");
  Require(m_GeneratedObservationOut.good(), "cannot open generated-observation output");
  m_GeneratedObservationOut << "simulation_event_id\tstable_root_id\teventlist_id\traw_eventlist_binary64_sha256\t"
    "observed_generated_particle\tobserved_generated_excitation_keV\tobserved_generated_source_time_s\t"
    "observed_generated_x_cm\tobserved_generated_y_cm\tobserved_generated_z_cm\tobserved_generated_dx\t"
    "observed_generated_dy\tobserved_generated_dz\tobserved_generated_px\tobserved_generated_py\t"
    "observed_generated_pz\tobserved_generated_energy_keV\tobserved_generated_binary64_sha256\t"
    "native_event_time_s\tserialized_ia_particle\tserialized_ia_time_s\tserialized_ia_x_cm\t"
    "serialized_ia_y_cm\tserialized_ia_z_cm\tserialized_ia_dx\t"
    "serialized_ia_dy\tserialized_ia_dz\tserialized_ia_px\tserialized_ia_py\tserialized_ia_pz\t"
    "serialized_ia_energy_keV\tserialized_ia_quantized_sha256\t"
    "serialized_ia_position_energy_abs_tolerance\t"
    "serialized_ia_direction_polarization_abs_tolerance\tserialized_ia_rel_tolerance\tprecision_contract\n";
  if (IsCompactArm()) {
    m_EventOut.OpenExclusive(m_StageDirectory + "/events.tsv");
    m_PixelOut.OpenExclusive(m_StageDirectory + "/pixels.tsv");
    m_DepositOut.OpenExclusive(m_StageDirectory + "/deposits.tsv");
    m_VetoBlockOut.OpenExclusive(m_StageDirectory + "/veto_blocks.tsv");
    m_ActivationOut.OpenExclusive(m_StageDirectory + "/activation.tsv");
    m_TruthOut.OpenExclusive(m_StageDirectory + "/truth.sim");
    m_TruthIndexOut.OpenExclusive(m_StageDirectory + "/truth_index.tsv");
    Require(m_EventOut.good() && m_PixelOut.good() && m_DepositOut.good() && m_VetoBlockOut.good() &&
            m_ActivationOut.good() && m_TruthOut.good() && m_TruthIndexOut.good(), "cannot open compact outputs");
    m_EventOut << "simulation_event_id\tstable_root_id\tgeometry\tsource_time_s\troot_weight\ttes_raw_keV\t"
                  "mass_csi_keV\to8_bgo_keV\to8_plastic_keV\tactive_shield_keV\tactive_veto_total_keV\t"
                  "kapton_diagnostic_keV\ttes_multiplicity\traw_tes_positive\tcandidate_reason\tcontrol_flag\t"
                  "truth_required\tpass_veto50\tpass_veto70\tpass_veto80\n";
    m_PixelOut << "simulation_event_id\tstable_root_id\ttes_uid\tlayer\ttouchable_copy_path\tsum_energy_keV\t"
                  "centroid_x_cm\tcentroid_y_cm\tcentroid_z_cm\tpost_time_min_s\tpost_time_max_s\t"
                  "post_time_energy_weighted_s\tdeposit_count\tfirst_sequence\tlast_sequence\ttime_semantics\n";
    m_DepositOut << "simulation_event_id\tstable_root_id\tsequence\trole\tphysical_volume\tlogical_volume\t"
                    "touchable_copy_path\tmaterial\tedep_keV\tpre_x_cm\tpre_y_cm\tpre_z_cm\tpost_x_cm\tpost_y_cm\t"
                    "post_z_cm\tpre_time_s\tpost_time_s\ttrack_id\tparent_track_id\tprimary_track_id\tparticle\t"
                    "parent_particle\tprimary_particle\tcreator_process\tstep_process\n";
    m_VetoBlockOut << "simulation_event_id\tstable_root_id\tgeometry\tdetector_uid\tdetector_type\tphysical_volume\t"
                      "sum_energy_keV\tpost_time_min_s\tpost_time_max_s\tpost_time_energy_weighted_s\t"
                      "deposit_count\ttime_semantics\tveto_whitelist_sha256\n";
    m_ActivationOut << "simulation_event_id\tstable_root_id\teventlist_id\tdriver\tfamily\troot_weight\t"
                       "production_serial\tza\tz\ta\texcitation_keV\texcitation_f64_bits\tnative_dat_volume\t"
                       "physical_volume\tlogical_volume\ttouchable_copy_path\tmaterial\tproduction_x_cm\t"
                       "production_y_cm\tproduction_z_cm\tproduction_time_s\ttrack_id\tparent_track_id\t"
                       "primary_track_id\tparticle\tparent_particle\tprimary_particle\tcreator_process\t"
                       "step_process\tancestry_chain\n";
    m_TruthIndexOut << "simulation_event_id\tstable_root_id\treason\toffset\tlength\tsha256\n";
  }
  m_FooterOut.OpenExclusive(m_StageDirectory + "/footer.tsv");
  Require(m_FooterOut.good(), "cannot open footer output");
  m_FooterOut << "arm\tgeometry\tmode\tfamily\tjob_id\tshard_index\tseed\ttape_count\tgenerated_count\t"
               "started_count\tcompleted_count\tnative_populated_count\troot_count\tia_init_count\t"
               "native_observed_simulation_event_id_count\tnative_observed_event_id_count\taborted_count\t"
               "rp_row_count\tTT_s\tactive_block_coverage\tveto_whitelist_sha256\t"
               "record_schema_sha256\tfinalized\n";
}

void M05CompactScorer::LoadTapeBytes(const std::string& bytes)
{
  std::istringstream input(bytes);
  std::string line;
  Require(static_cast<bool>(std::getline(input, line)), "empty tape sidecar");
  const std::vector<std::string> header = SplitTab(line);
  static const char* expected[] = {
    "schema", "row_index0", "global_row_index0", "eventlist_id", "stable_root_id", "driver",
    "driver_assignment", "bin_index", "family", "mode", "source_card_path", "source_card_sha256",
    "source_contract_path", "source_contract_sha256", "spectrum_path", "spectrum_sha256",
    "sampler_algorithm", "sampler_seed_u64", "sampler_counter_start0", "sampler_counter_end0",
    "particle", "excitation_keV", "source_time_s", "global_poisson_time_s", "shard_global_time_offset_s",
    "x_cm", "y_cm", "z_cm", "dx", "dy", "dz", "px", "py", "pz", "energy_keV",
    "raw_eventlist_line_sha256", "expected_eventlist_binary64_sha256", "expected_generated_binary64_sha256",
    "expected_generated_tuple_sha256", "control_flag"
  };
  Require(header.size() == sizeof(expected)/sizeof(expected[0]), "wrong tape sidecar header width");
  for (std::size_t i = 0; i < header.size(); ++i) Require(header[i] == expected[i], "wrong tape sidecar header/order");
  while (std::getline(input, line)) {
    Require(!line.empty(), "blank tape sidecar row");
    const std::vector<std::string> f = SplitTab(line);
    Require(f.size() == header.size(), "wrong tape sidecar field count");
    TapeRow row;
    Require(f[0] == "m05-tape-root-v2" && f[6] == "sampled_exact_not_inferred", "wrong tape row semantics");
    row.rowIndex0 = StrictLong(f[1]);
    row.globalRowIndex0 = StrictLong(f[2]);
    row.eventListID = StrictLong(f[3]);
    row.stableRootID = f[4];
    row.driver = f[5];
    row.family = f[8];
    row.mode = f[9];
    row.sourceCardSHA256 = f[11];
    row.sourceContractSHA256 = f[13];
    row.particle = static_cast<int>(StrictLong(f[20]));
    row.excitationKeV = StrictDouble(f[21]);
    row.sourceTimeSeconds = StrictDouble(f[22]);
    for (int i = 0; i < 3; ++i) row.position[i] = StrictDouble(f[25+i]);
    for (int i = 0; i < 3; ++i) row.direction[i] = StrictDouble(f[28+i]);
    for (int i = 0; i < 3; ++i) row.polarization[i] = StrictDouble(f[31+i]);
    row.energyKeV = StrictDouble(f[34]);
    row.rawLineSHA256 = f[35];
    row.expectedEventListBinary64SHA256 = f[36];
    row.expectedGeneratedBinary64SHA256 = f[37];
    row.expectedGeneratedTupleSHA256 = f[38];
    Require(f[39] == "0" || f[39] == "1", "invalid tape control flag");
    row.control = f[39] == "1";
    Require(row.rowIndex0 == static_cast<long>(m_Tape.size()), "out-of-order/duplicate tape row");
    Require(row.eventListID == row.rowIndex0+1, "event-list ID/order mismatch");
    Require(IsLowerHexDigest(row.stableRootID) && IsLowerHexDigest(row.rawLineSHA256) &&
            IsLowerHexDigest(row.expectedEventListBinary64SHA256) &&
            IsLowerHexDigest(row.expectedGeneratedBinary64SHA256) &&
            IsLowerHexDigest(row.expectedGeneratedTupleSHA256) && IsLowerHexDigest(row.sourceCardSHA256) &&
            IsLowerHexDigest(row.sourceContractSHA256) && IsLowerHexDigest(f[15]), "invalid tape digest");
    if (!m_Tape.empty()) {
      Require(row.globalRowIndex0 == m_Tape.back().globalRowIndex0+1, "non-contiguous global tape row");
      Require(row.sourceTimeSeconds > m_Tape.back().sourceTimeSeconds, "non-monotonic tape time");
      Require(row.family == m_Tape.front().family && row.mode == m_Tape.front().mode, "mixed tape cell");
    }
    m_Tape.push_back(row);
  }
  std::set<std::string> roots;
  bool hasControl = false;
  for (const TapeRow& row : m_Tape) { roots.insert(row.stableRootID); hasControl = hasControl || row.control; }
  Require(roots.size() == m_Tape.size(), "duplicate stable root IDs");
  Require(hasControl && !m_Tape.empty() && m_Tape.front().control, "subshard lacks guaranteed pre-registered control");
}

const M05CompactScorer::TapeRow& M05CompactScorer::CurrentRow() const
{
  const long id = m_Lifecycle.CurrentID();
  Require(id >= 1 && id <= static_cast<long>(m_Tape.size()), "active event outside tape");
  return m_Tape[static_cast<std::size_t>(id-1)];
}

void M05CompactScorer::BeginGeneratedEvent(long simulationEventID)
{
  Require(m_Configured && !m_Finalized, "BeginGeneratedEvent outside configured run");
  m_Lifecycle.BeginGeneratedEvent(simulationEventID, static_cast<long>(m_Tape.size()));
  m_DepositSequence = 0;
  m_KaptonDiagnosticKeV = 0.0;
  m_PixelAggregates.clear();
  m_BlockAggregates.clear();
}

void M05CompactScorer::RecordGenerated(long eventListID,
                                       const std::string&,
                                       double sourceTimeSeconds,
                                       int particle,
                                       double excitationKeV,
                                       const G4Event* generatedEvent,
                                       int vertexIndex,
                                       G4GeneralParticleSource* particleSource,
                                       const G4ThreeVector& position,
                                       const G4ThreeVector& direction,
                                       const G4ThreeVector& polarization,
                                       double energyKeV)
{
  const TapeRow& row = CurrentRow();
  Require(m_Lifecycle.IsActive() && !m_Lifecycle.IsGenerated(), "multiple/out-of-phase generated primary");
  Require(generatedEvent != nullptr && particleSource != nullptr && vertexIndex >= 0 &&
          generatedEvent->GetNumberOfPrimaryVertex() == vertexIndex+1,
          "actual generated event did not add exactly one vertex");
  G4PrimaryVertex* vertex = generatedEvent->GetPrimaryVertex(vertexIndex);
  Require(vertex != nullptr && vertex->GetNumberOfParticle() == 1,
          "actual generated vertex does not contain exactly one primary");
  G4PrimaryParticle* primary = vertex->GetPrimary(0);
  Require(primary != nullptr,
          "actual generated primary is null");
  const auto SameBinary64 = [](double left, double right) {
    std::uint64_t leftBits = 0, rightBits = 0;
    std::memcpy(&leftBits, &left, sizeof(leftBits));
    std::memcpy(&rightBits, &right, sizeof(rightBits));
    return leftBits == rightBits;
  };
  const auto SameVectorBinary64 = [&](const G4ThreeVector& left, const G4ThreeVector& right) {
    return SameBinary64(left.x(), right.x()) && SameBinary64(left.y(), right.y()) &&
           SameBinary64(left.z(), right.z());
  };
  Require(primary->GetG4code() == particleSource->GetParticleDefinition() &&
          SameVectorBinary64(vertex->GetPosition(), position) &&
          SameVectorBinary64(primary->GetMomentumDirection(), direction) &&
          SameVectorBinary64(primary->GetPolarization(), polarization) &&
          SameBinary64(primary->GetKineticEnergy(), particleSource->GetParticleEnergy()) &&
          SameBinary64(vertex->GetT0(), particleSource->GetParticleTime()) &&
          SameBinary64(energyKeV, primary->GetKineticEnergy()/keV),
          "actual G4PrimaryVertex/G4PrimaryParticle bits differ from particle-gun state");
  Require(eventListID == row.eventListID, "EventList row ID was not propagated in order");
  Require(particle == row.particle && Near(excitationKeV, row.excitationKeV), "generated particle/state mismatch");
  Require(Near(sourceTimeSeconds, row.sourceTimeSeconds), "generated source time mismatch");
  const double inputPosition[3] = {position.x()/cm, position.y()/cm, position.z()/cm};
  const double inputDirection[3] = {direction.x(), direction.y(), direction.z()};
  const double inputPolarization[3] = {polarization.x(), polarization.y(), polarization.z()};
  const double rowNorm = std::sqrt(row.direction[0]*row.direction[0] + row.direction[1]*row.direction[1] +
                                   row.direction[2]*row.direction[2]);
  Require(rowNorm > 0.0, "zero tape direction");
  for (int i = 0; i < 3; ++i) {
    m_GeneratedPosition[i] = inputPosition[i];
    m_GeneratedDirection[i] = inputDirection[i];
    m_GeneratedPolarization[i] = inputPolarization[i];
    Require(Near(inputPosition[i], row.position[i], 1.0e-9, 1.0e-12), "generated position mismatch");
    Require(Near(inputDirection[i], row.direction[i]/rowNorm, 1.0e-12, 1.0e-12), "generated direction mismatch");
    Require(Near(inputPolarization[i], row.polarization[i], 1.0e-12, 1.0e-12), "generated polarization mismatch");
  }
  m_GeneratedParticle = particle;
  m_GeneratedExcitationKeV = excitationKeV;
  m_GeneratedSourceTimeSeconds = sourceTimeSeconds;
  m_GeneratedEnergyKeV = energyKeV;
  Require(Near(energyKeV, row.energyKeV, 1.0e-9, 1.0e-12), "generated energy mismatch");
  m_Lifecycle.MarkGenerated();
}

void M05CompactScorer::ConfirmEventStarted(long simulationEventID)
{
  Require(m_Configured && !m_Finalized, "ConfirmEventStarted outside configured run");
  m_Lifecycle.ConfirmEventStarted(simulationEventID);
}

std::string M05CompactScorer::ClassifyVolume(const std::string& volume) const
{
  bool exactTES = volume.size() >= 7 && volume.compare(0, 4, "TP_L") == 0 &&
                  volume[4] >= '0' && volume[4] <= '5' && volume[5] == '_';
  for (std::size_t i = 6; exactTES && i < volume.size(); ++i) exactTES = std::isdigit(static_cast<unsigned char>(volume[i]));
  if (exactTES) return "tes";
  std::string upper = volume;
  std::transform(upper.begin(), upper.end(), upper.begin(), [](unsigned char c){ return std::toupper(c); });
  if (upper.find("KAPTON") != std::string::npos) return "kapton";
  if (Contains(kMassCSI, volume)) return "mass_csi";
  if (Contains(kO8BGO, volume)) return "o8_bgo";
  if (Contains(kO8Plastic, volume)) return "o8_plastic";
  return "";
}

std::string M05CompactScorer::TouchablePath(const G4TouchableHistory* history) const
{
  Require(history != nullptr, "missing touchable history");
  std::ostringstream out;
  for (int level = 0; level <= history->GetHistoryDepth(); ++level) {
    G4VPhysicalVolume* physical = history->GetVolume(level);
    Require(physical != nullptr && physical->GetLogicalVolume() != nullptr, "incomplete touchable path");
    if (level != 0) out << '/';
    out << physical->GetName() << ':' << physical->GetLogicalVolume()->GetName() << ':' << history->GetCopyNumber(level);
  }
  return out.str();
}

std::string M05CompactScorer::AncestryChain(int trackID) const
{
  struct Edge { int tid; int pid; };
  std::vector<Edge> chain;
  std::set<int> seen;
  int current = trackID;
  while (current != 0) {
    Require(seen.insert(current).second, "track ancestry loop");
    TrackMeta meta;
    Require(MCEventAction::GetTrackMeta(current, meta), "missing track ancestry node");
    chain.push_back(Edge{meta.tid, meta.pid});
    Require(meta.tid == current && meta.pid >= 0, "invalid track ancestry edge");
    current = meta.pid;
  }
  std::reverse(chain.begin(), chain.end());
  Require(!chain.empty() && chain.front().pid == 0 && chain.back().tid == trackID, "incomplete ancestry chain");
  for (std::size_t i = 1; i < chain.size(); ++i) Require(chain[i].pid == chain[i-1].tid, "disconnected ancestry edge");
  std::ostringstream out;
  for (std::size_t i = 0; i < chain.size(); ++i) {
    if (i != 0) out << ',';
    out << chain[i].tid << ':' << chain[i].pid;
  }
  return out.str();
}

void M05CompactScorer::RecordSensitiveDeposit(const G4Step* step,
                                              double postGlobalTimeSeconds,
                                              const std::string&)
{
  if (!IsCompactArm()) return;
  Require(m_Lifecycle.IsStarted(), "sensitive deposit outside started event");
  Require(step != nullptr && step->GetTrack() != nullptr && step->GetPreStepPoint() != nullptr &&
          step->GetPostStepPoint() != nullptr, "incomplete sensitive step");
  const double edep = step->GetTotalEnergyDeposit()/keV;
  if (!(edep > 0.0)) return;
  G4VPhysicalVolume* physical = step->GetPreStepPoint()->GetPhysicalVolume();
  Require(physical != nullptr && physical->GetLogicalVolume() != nullptr &&
          physical->GetLogicalVolume()->GetMaterial() != nullptr, "sensitive deposit lacks volume/material");
  const std::string role = ClassifyVolume(physical->GetName());
  if (role.empty()) return;
  const unsigned long sequence = ++m_DepositSequence;
  const G4TouchableHistory* history = static_cast<const G4TouchableHistory*>(step->GetPreStepPoint()->GetTouchable());
  const std::string touchablePath = TouchablePath(history);
  const G4ThreeVector pre = step->GetPreStepPoint()->GetPosition();
  const double preTimeSeconds = step->GetPreStepPoint()->GetGlobalTime()/second;
  Require(std::isfinite(preTimeSeconds) && std::isfinite(postGlobalTimeSeconds) &&
          preTimeSeconds >= 0.0 && postGlobalTimeSeconds >= preTimeSeconds,
          "invalid PRE/POST step times");
  if (role == "tes") {
    PixelAggregate& aggregate = m_PixelAggregates[touchablePath];
    if (aggregate.depositCount == 0) {
      aggregate.physicalVolume = physical->GetName();
      aggregate.touchablePath = touchablePath;
      aggregate.postTimeMinSeconds = postGlobalTimeSeconds;
      aggregate.postTimeMaxSeconds = postGlobalTimeSeconds;
      aggregate.firstSequence = sequence;
    } else {
      Require(aggregate.physicalVolume == physical->GetName() && aggregate.touchablePath == touchablePath,
              "one TES touchable UID maps to inconsistent detector identity");
      aggregate.postTimeMinSeconds = std::min(aggregate.postTimeMinSeconds, postGlobalTimeSeconds);
      aggregate.postTimeMaxSeconds = std::max(aggregate.postTimeMaxSeconds, postGlobalTimeSeconds);
    }
    aggregate.energyKeV += edep;
    aggregate.weightedPrePositionCM[0] += edep*pre.x()/cm;
    aggregate.weightedPrePositionCM[1] += edep*pre.y()/cm;
    aggregate.weightedPrePositionCM[2] += edep*pre.z()/cm;
    aggregate.weightedPostTimeSeconds += edep*postGlobalTimeSeconds;
    ++aggregate.depositCount;
    aggregate.lastSequence = sequence;
  } else if (role == "mass_csi" || role == "o8_bgo" || role == "o8_plastic") {
    BlockAggregate& aggregate = m_BlockAggregates[physical->GetName()];
    if (aggregate.depositCount == 0) {
      aggregate.role = role;
      aggregate.physicalVolume = physical->GetName();
      aggregate.postTimeMinSeconds = postGlobalTimeSeconds;
      aggregate.postTimeMaxSeconds = postGlobalTimeSeconds;
    } else {
      Require(aggregate.role == role && aggregate.physicalVolume == physical->GetName(),
              "active block UID maps to inconsistent detector identity");
      aggregate.postTimeMinSeconds = std::min(aggregate.postTimeMinSeconds, postGlobalTimeSeconds);
      aggregate.postTimeMaxSeconds = std::max(aggregate.postTimeMaxSeconds, postGlobalTimeSeconds);
    }
    aggregate.energyKeV += edep;
    aggregate.weightedPostTimeSeconds += edep*postGlobalTimeSeconds;
    ++aggregate.depositCount;
  } else {
    Require(role == "kapton", "unknown retained sensitive role");
    m_KaptonDiagnosticKeV += edep;
  }
}

std::string M05CompactScorer::Escape(const std::string& value) const
{
  std::ostringstream out;
  out << std::hex << std::uppercase;
  for (const unsigned char c : value) {
    if (c == '%' || c == '\t' || c == '\n' || c == '\r') {
      out << '%' << std::setw(2) << std::setfill('0') << static_cast<unsigned int>(c);
    } else out << static_cast<char>(c);
  }
  return out.str();
}

std::string M05CompactScorer::SHA256(const std::string& value) const
{
  unsigned char digest[SHA256_DIGEST_LENGTH];
  ::SHA256(reinterpret_cast<const unsigned char*>(value.data()), value.size(), digest);
  std::ostringstream out;
  out << std::hex << std::setfill('0');
  for (const unsigned char byte : digest) out << std::setw(2) << static_cast<unsigned int>(byte);
  return out.str();
}

std::string M05CompactScorer::SHA256File(const std::string& path) const
{
  RequireRegularNoLink(path);
  std::ifstream input(path.c_str(), std::ios::binary);
  Require(input.good(), "cannot hash output file");
  SHA256_CTX context;
  SHA256_Init(&context);
  char buffer[1024*1024];
  while (input.good()) {
    input.read(buffer, sizeof(buffer));
    const std::streamsize count = input.gcount();
    if (count > 0) SHA256_Update(&context, buffer, static_cast<std::size_t>(count));
  }
  Require(input.eof(), "output read failed during hash");
  unsigned char digest[SHA256_DIGEST_LENGTH];
  SHA256_Final(digest, &context);
  std::ostringstream out;
  out << std::hex << std::setfill('0');
  for (const unsigned char byte : digest) out << std::setw(2) << static_cast<unsigned int>(byte);
  return out.str();
}

std::string M05CompactScorer::QuantizedTupleSHA256(int particle,
                                                   double excitationKeV,
                                                   double sourceTimeSeconds,
                                                   const double position[3],
                                                   const double direction[3],
                                                   const double polarization[3],
                                                   double energyKeV) const
{
  const double norm = std::sqrt(direction[0]*direction[0] + direction[1]*direction[1] + direction[2]*direction[2]);
  Require(norm > 0.0, "zero direction in tuple hash");
  std::vector<long long> q;
  q.push_back(particle);
  q.push_back(std::llround(excitationKeV*1.0e6));
  q.push_back(std::llround(sourceTimeSeconds*1.0e12));
  for (int i = 0; i < 3; ++i) q.push_back(std::llround(position[i]*1.0e6));
  for (int i = 0; i < 3; ++i) q.push_back(std::llround(direction[i]/norm*1.0e9));
  for (int i = 0; i < 3; ++i) q.push_back(std::llround(polarization[i]*1.0e9));
  q.push_back(std::llround(energyKeV*1.0e6));
  std::ostringstream canonical;
  canonical << '[';
  for (std::size_t i = 0; i < q.size(); ++i) { if (i != 0) canonical << ','; canonical << q[i]; }
  canonical << "]\n";
  return SHA256(canonical.str());
}

std::string M05CompactScorer::IAStateSHA256(int particle,
                                            double iaTimeSeconds,
                                            const double position[3],
                                            const double direction[3],
                                            const double polarization[3],
                                            double energyKeV) const
{
  const double norm = std::sqrt(direction[0]*direction[0] + direction[1]*direction[1] + direction[2]*direction[2]);
  Require(particle > 0 && std::isfinite(iaTimeSeconds) && norm > 0.0,
          "invalid IA INIT state in hash");
  std::vector<long long> q;
  q.push_back(particle);
  q.push_back(std::llround(iaTimeSeconds*1.0e12));
  for (int i = 0; i < 3; ++i) q.push_back(std::llround(position[i]*1.0e6));
  for (int i = 0; i < 3; ++i) q.push_back(std::llround(direction[i]/norm*1.0e9));
  for (int i = 0; i < 3; ++i) q.push_back(std::llround(polarization[i]*1.0e9));
  q.push_back(std::llround(energyKeV*1.0e6));
  std::ostringstream canonical;
  static const char domain[] = "m05-ia-init-state-v1";
  canonical.write(domain, sizeof(domain)); // include the NUL domain separator
  canonical << '[';
  for (std::size_t i = 0; i < q.size(); ++i) { if (i != 0) canonical << ','; canonical << q[i]; }
  canonical << "]\n";
  return SHA256(canonical.str());
}

std::string M05CompactScorer::Binary64TupleSHA256(int particle,
                                                  double excitationKeV,
                                                  double sourceTimeSeconds,
                                                  const double position[3],
                                                  const double direction[3],
                                                  const double polarization[3],
                                                  double energyKeV) const
{
  static_assert(sizeof(double) == 8, "binary64 precision contract requires 8-byte double");
  Require(particle > 0, "binary64 tuple particle is invalid");
  const double values[12] = {
    excitationKeV, sourceTimeSeconds,
    position[0], position[1], position[2],
    direction[0], direction[1], direction[2],
    polarization[0], polarization[1], polarization[2], energyKeV
  };
  std::string payload;
  static const char domain[] = "m05-eventlist-binary64-v1";
  payload.append(domain, sizeof(domain)); // sizeof includes the required NUL domain terminator
  const std::uint32_t particleBits = static_cast<std::uint32_t>(particle);
  for (int shift = 24; shift >= 0; shift -= 8) {
    payload.push_back(static_cast<char>((particleBits >> shift) & 0xffU));
  }
  for (double value : values) {
    Require(std::isfinite(value), "non-finite binary64 tuple field");
    std::uint64_t bits = 0;
    std::memcpy(&bits, &value, sizeof(bits));
    for (int shift = 56; shift >= 0; shift -= 8) {
      payload.push_back(static_cast<char>((bits >> shift) & 0xffULL));
    }
  }
  return SHA256(payload);
}

void M05CompactScorer::RecordCommittedIsotope(unsigned long productionSerial,
                                              const G4Step* step,
                                              G4TouchableHistory* history,
                                              G4Ions* nucleus,
                                              double postGlobalTimeSeconds,
                                              const std::string& stepProcess)
{
  if (!IsCompactArm()) return;
  Require(m_Lifecycle.IsStarted(), "isotope commit outside started event");
  Require(step != nullptr && step->GetTrack() != nullptr && history != nullptr && nucleus != nullptr,
          "incomplete committed isotope callback");
  Require(productionSerial == m_RPCount+1, "isotope production serial has gap/duplicate");
  G4VPhysicalVolume* physical = history->GetVolume(0);
  Require(physical != nullptr && physical->GetLogicalVolume() != nullptr &&
          physical->GetLogicalVolume()->GetMaterial() != nullptr, "isotope lacks volume/material");
  const std::string logical = physical->GetLogicalVolume()->GetName();
  Require(logical.size() >= 3, "logical volume cannot reproduce native DAT name");
  const std::string nativeDATVolume = logical.substr(0, logical.size()-3);
  const int z = nucleus->GetAtomicNumber();
  const int a = nucleus->GetAtomicMass();
  const int za = 1000*static_cast<int>(nucleus->GetPDGCharge()/eplus) + nucleus->GetBaryonNumber();
  Require(z >= 1 && z <= 118 && a >= 1 && a <= 400 && za == 1000*z+a, "native ZA reconstruction mismatch");
  const double excitationKeV = nucleus->GetExcitationEnergy()/keV;
  Require(std::isfinite(excitationKeV) && excitationKeV >= 0.0, "invalid isotope excitation");
  std::uint64_t bits = 0;
  static_assert(sizeof(bits) == sizeof(excitationKeV), "double is not 64-bit");
  std::memcpy(&bits, &excitationKeV, sizeof(bits));
  const int trackID = step->GetTrack()->GetTrackID();
  TrackMeta meta;
  Require(MCEventAction::GetTrackMeta(trackID, meta), "isotope lacks track metadata");
  const std::string chain = AncestryChain(trackID);
  TrackMeta rootMeta;
  Require(MCEventAction::GetTrackMeta(meta.primid, rootMeta), "isotope lacks primary root metadata");
  Require(rootMeta.pid == 0 && rootMeta.tid == meta.primid && rootMeta.primaryParticle == rootMeta.particle &&
          rootMeta.primaryParticle == meta.primaryParticle, "isotope primary/root disagreement");
  const TapeRow& row = CurrentRow();
  std::string expected;
  if (row.family == "gamma") expected = "gamma";
  else if (row.family == "n") expected = "neutron";
  else if (row.family == "eplus") expected = "e+";
  else if (row.family == "eminus") expected = "e-";
  else if (row.family == "alpha") expected = "alpha";
  else if (row.family == "muplus") expected = "mu+";
  else if (row.family == "muminus") expected = "mu-";
  else Require(false, "unsupported tape family at isotope root");
  Require(rootMeta.particle == expected, "isotope root particle differs from tape family");
  // Geant4's track vertex is the creation position of this residual-ion
  // track.  The callback can occur on a later commit/store step, so PRE/POST
  // step positions are not a production-position authority.
  const G4ThreeVector position = step->GetTrack()->GetVertexPosition();
  const double productionTimeSeconds =
    step->GetTrack()->GetGlobalTime()/second - step->GetTrack()->GetLocalTime()/second;
  Require(std::isfinite(productionTimeSeconds) && productionTimeSeconds >= 0.0 &&
          postGlobalTimeSeconds >= productionTimeSeconds,
          "isotope production/commit time semantics are invalid");
  m_ActivationOut << m_Lifecycle.CurrentID() << '\t' << row.stableRootID << '\t' << row.eventListID << '\t'
                  << Escape(row.driver) << '\t' << Escape(row.family) << "\t1\t" << productionSerial << '\t'
                  << za << '\t' << z << '\t' << a << '\t' << std::setprecision(17) << excitationKeV << '\t'
                  << std::hex << std::setw(16) << std::setfill('0') << bits << std::dec << std::setfill(' ') << '\t'
                  << Escape(nativeDATVolume) << '\t' << Escape(physical->GetName()) << '\t' << Escape(logical) << '\t'
                  << Escape(TouchablePath(history)) << '\t' << Escape(physical->GetLogicalVolume()->GetMaterial()->GetName())
                  << '\t' << position.x()/cm << '\t' << position.y()/cm << '\t' << position.z()/cm << '\t'
                  << productionTimeSeconds << '\t' << trackID << '\t' << step->GetTrack()->GetParentID() << '\t'
                  << meta.primid << '\t' << Escape(meta.particle) << '\t' << Escape(meta.parentParticle) << '\t'
                  << Escape(meta.primaryParticle) << '\t' << Escape(meta.creatorProcess) << '\t'
                  << Escape(stepProcess) << '\t' << chain << '\n';
  Require(m_ActivationOut.good(), "activation sidecar write failure");
  ++m_RPCount;
}

void M05CompactScorer::EndEvent(MSimEvent* event, bool aborted, bool nativeEventPopulated)
{
  Require(m_Configured && m_Lifecycle.IsStarted(), "EndEvent outside started event");
  const long simulationID = m_Lifecycle.CurrentID();
  const TapeRow& row = CurrentRow();
  if (aborted || !nativeEventPopulated) {
    m_Lifecycle.FinishEvent(simulationID, aborted, nativeEventPopulated);
    Require(false, aborted ? "aborted event quarantined" : "native event was not populated");
  }
  Require(event != nullptr, "native event pointer is null");
  MSimIA* init = nullptr;
  unsigned int initCount = 0;
  for (unsigned int i = 0; i < event->GetNIAs(); ++i) {
    MSimIA* candidate = event->GetIAAt(i);
    if (candidate != nullptr && candidate->GetProcess() == "INIT") { init = candidate; ++initCount; }
  }
  Require(initCount == 1 && init != nullptr, "event does not contain exactly one IA INIT");
  ++m_InitCount;
  Require(event->GetSimulationEventID() == simulationID, "native simulation event ID mismatch");
  Require(event->GetID() > 0 && m_NativeIDs.insert(event->GetID()).second, "native ID is zero/duplicate");
  ++m_IDCount;
  ++m_SECount;
  Require(init->GetSecondaryParticleID() == m_GeneratedParticle, "IA INIT particle mismatch");
  const double nativeEventTimeSeconds = event->GetTime().GetAsSeconds();
  const double iaTimeSeconds = init->GetTime();
  Require(Near(nativeEventTimeSeconds, m_GeneratedSourceTimeSeconds, 1.1e-9, 1.0e-12),
          "native event time differs from generated source time");
  Require(Near(iaTimeSeconds, 0.0, 1.0e-15, 0.0), "serialized IA INIT time is not zero");
  double iaPosition[3], iaDirection[3], iaPolarization[3];
  for (int i = 0; i < 3; ++i) {
    iaPosition[i] = init->GetPosition()[i];
    iaDirection[i] = init->GetSecondaryDirection()[i];
    iaPolarization[i] = init->GetSecondaryPolarization()[i];
    Require(Near(iaPosition[i], m_GeneratedPosition[i]), "IA INIT position mismatch");
    Require(Near(iaDirection[i], m_GeneratedDirection[i]), "IA INIT direction mismatch");
    Require(Near(iaPolarization[i], m_GeneratedPolarization[i]), "IA INIT polarization mismatch");
  }
  Require(Near(init->GetSecondaryEnergy(), m_GeneratedEnergyKeV), "IA INIT energy mismatch");
  const std::string generatedHash = QuantizedTupleSHA256(
      m_GeneratedParticle, m_GeneratedExcitationKeV, m_GeneratedSourceTimeSeconds,
      m_GeneratedPosition, m_GeneratedDirection, m_GeneratedPolarization, m_GeneratedEnergyKeV);
  const std::string iaHash = IAStateSHA256(
      init->GetSecondaryParticleID(), iaTimeSeconds, iaPosition, iaDirection,
      iaPolarization, init->GetSecondaryEnergy());
  Require(generatedHash == row.expectedGeneratedTupleSHA256, "generated tuple hash differs from frozen tape");

  {
    const std::string observedBinary64 = Binary64TupleSHA256(
        m_GeneratedParticle, m_GeneratedExcitationKeV, m_GeneratedSourceTimeSeconds,
        m_GeneratedPosition, m_GeneratedDirection, m_GeneratedPolarization, m_GeneratedEnergyKeV);
    Require(observedBinary64 == row.expectedGeneratedBinary64SHA256,
            "observed post-GPS generated binary64 tuple differs from normalized frozen tape expectation");
    m_GeneratedObservationOut << simulationID << '\t' << row.stableRootID << '\t' << row.eventListID << '\t'
      << row.expectedEventListBinary64SHA256 << '\t' << m_GeneratedParticle << '\t' << std::setprecision(17)
      << m_GeneratedExcitationKeV << '\t' << m_GeneratedSourceTimeSeconds;
    for (double value : m_GeneratedPosition) m_GeneratedObservationOut << '\t' << value;
    for (double value : m_GeneratedDirection) m_GeneratedObservationOut << '\t' << value;
    for (double value : m_GeneratedPolarization) m_GeneratedObservationOut << '\t' << value;
    m_GeneratedObservationOut << '\t' << m_GeneratedEnergyKeV << '\t' << observedBinary64 << '\t'
      << nativeEventTimeSeconds << '\t' << init->GetSecondaryParticleID() << '\t' << iaTimeSeconds;
    for (double value : iaPosition) m_GeneratedObservationOut << '\t' << value;
    for (double value : iaDirection) m_GeneratedObservationOut << '\t' << value;
    for (double value : iaPolarization) m_GeneratedObservationOut << '\t' << value;
    m_GeneratedObservationOut << '\t' << init->GetSecondaryEnergy() << '\t' << iaHash
      << "\t1e-06\t1e-09\t1e-09\tGENERATED_BINARY64_BE_V1__IA_SERIALIZED_17G_FIELD_TOL_V2\n";
    Require(m_GeneratedObservationOut.good(), "generated-observation output write failure");
    ++m_GeneratedObservationRowCount;
  }

  m_RootOut << simulationID << '\t' << row.rowIndex0 << '\t' << row.eventListID << '\t'
            << row.stableRootID << '\t' << Escape(row.driver) << "\t\tunavailable\t[]\t" << Escape(row.family)
            << "\t1\t1\t1\t1\t0\t" << row.rawLineSHA256 << '\t' << row.expectedGeneratedTupleSHA256 << '\t'
            << generatedHash << '\t' << iaHash << '\t' << (row.control ? 1 : 0) << '\n';
  Require(m_RootOut.good(), "root output write failure");
  ++m_RootCount;

  if (IsCompactArm()) {
    double massCSI = 0.0, o8BGO = 0.0, o8Plastic = 0.0, tes = 0.0;
    for (const auto& pixel : m_PixelAggregates) tes += pixel.second.energyKeV;
    for (const auto& block : m_BlockAggregates) {
      if (block.second.role == "mass_csi") massCSI += block.second.energyKeV;
      else if (block.second.role == "o8_bgo") o8BGO += block.second.energyKeV;
      else if (block.second.role == "o8_plastic") o8Plastic += block.second.energyKeV;
      else Require(false, "unknown online active-block aggregate role");
    }
    if (m_Geometry == "mass_model_511") Require(o8BGO == 0.0 && o8Plastic == 0.0, "O8 active block in Mass geometry");
    else Require(massCSI == 0.0, "Mass CsI active block in O8 geometry");

    for (const auto& pixel : m_PixelAggregates) {
      const PixelAggregate& value = pixel.second;
      int layer = -1;
      if (value.physicalVolume.size() > 4 && std::isdigit(static_cast<unsigned char>(value.physicalVolume[4]))) {
        layer = value.physicalVolume[4]-'0';
      }
      Require(layer >= 0 && layer <= 5 && value.energyKeV > 0.0 && value.depositCount > 0,
              "invalid TES aggregate");
      m_PixelOut << simulationID << '\t' << row.stableRootID << '\t' << Escape(pixel.first) << '\t' << layer
                 << '\t' << Escape(value.touchablePath) << '\t' << std::setprecision(17) << value.energyKeV
                 << '\t' << value.weightedPrePositionCM[0]/value.energyKeV
                 << '\t' << value.weightedPrePositionCM[1]/value.energyKeV
                 << '\t' << value.weightedPrePositionCM[2]/value.energyKeV
                 << '\t' << value.postTimeMinSeconds << '\t' << value.postTimeMaxSeconds
                 << '\t' << value.weightedPostTimeSeconds/value.energyKeV << '\t' << value.depositCount
                 << '\t' << value.firstSequence << '\t' << value.lastSequence << "\tPOST_GLOBAL_V1\n";
      ++m_PixelRowCount;
    }

    const std::vector<std::pair<std::string, std::string> > activeBlocks = [&]() {
      std::vector<std::pair<std::string, std::string> > result;
      if (m_Geometry == "mass_model_511") {
        for (const char* value : kMassCSI) result.push_back(std::make_pair(std::string(value), std::string("mass_csi")));
      } else {
        for (const char* value : kO8BGO) result.push_back(std::make_pair(std::string(value), std::string("o8_bgo")));
        for (const char* value : kO8Plastic) result.push_back(std::make_pair(std::string(value), std::string("o8_plastic")));
      }
      return result;
    }();
    Require((m_Geometry == "mass_model_511" && activeBlocks.size() == 24) ||
            (m_Geometry == "s3d_o8" && activeBlocks.size() == 6), "active block cardinality drift");
    for (const auto& block : activeBlocks) {
      const auto found = m_BlockAggregates.find(block.first);
      const bool populated = found != m_BlockAggregates.end();
      if (populated) Require(found->second.role == block.second && found->second.physicalVolume == block.first &&
                             found->second.energyKeV > 0.0 && found->second.depositCount > 0,
                             "active block deposit/type mismatch");
      const double energy = populated ? found->second.energyKeV : 0.0;
      m_VetoBlockOut << simulationID << '\t' << row.stableRootID << '\t' << m_Geometry << '\t'
                    << Escape(block.second + ":" + block.first) << '\t' << block.second << '\t' << Escape(block.first) << '\t'
                    << std::setprecision(17) << energy << '\t';
      if (populated) m_VetoBlockOut << found->second.postTimeMinSeconds << '\t' << found->second.postTimeMaxSeconds
                                    << '\t' << found->second.weightedPostTimeSeconds/energy;
      else m_VetoBlockOut << "\t\t";
      m_VetoBlockOut << '\t' << (populated ? found->second.depositCount : 0)
                     << "\tPOST_GLOBAL_V1\t" << m_WhitelistSHA256 << '\n';
      ++m_VetoBlockRowCount;
    }

    const double activeShield = m_Geometry == "mass_model_511" ? massCSI : o8BGO;
    const double activeVetoTotal = M05ActiveVetoTotalKeV(m_Geometry, massCSI, o8BGO, o8Plastic);
    const bool rawTES = tes > 0.0;
    if (row.control && !rawTES) ++m_TESZeroControlCount;
    const bool activePositive = activeVetoTotal > 0.0;
    std::string reason = "none";
    if (rawTES && activePositive) reason = "tes+active_veto";
    else if (rawTES) reason = "tes";
    else if (activePositive) reason = "active_veto";
    const bool truthRequired = rawTES || row.control;
    const bool pass50 = M05PassActiveVeto(m_Geometry, massCSI, o8BGO, o8Plastic, 50.0);
    const bool pass70 = M05PassActiveVeto(m_Geometry, massCSI, o8BGO, o8Plastic, 70.0);
    const bool pass80 = M05PassActiveVeto(m_Geometry, massCSI, o8BGO, o8Plastic, 80.0);
    m_EventOut << simulationID << '\t' << row.stableRootID << '\t' << m_Geometry << '\t'
               << std::setprecision(17) << m_GeneratedSourceTimeSeconds << "\t1\t" << tes << '\t' << massCSI << '\t'
               << o8BGO << '\t' << o8Plastic << '\t' << activeShield << '\t' << activeVetoTotal << '\t'
               << m_KaptonDiagnosticKeV << '\t' << m_PixelAggregates.size() << '\t' << (rawTES ? 1 : 0)
               << '\t' << reason << '\t' << (row.control ? 1 : 0)
               << '\t' << (truthRequired ? 1 : 0) << '\t' << (pass50 ? 1 : 0) << '\t' << (pass70 ? 1 : 0)
               << '\t' << (pass80 ? 1 : 0) << '\n';
    ++m_EventRowCount;
    if (truthRequired) {
      const std::string truth = event->ToSimString(
          MSimEvent::c_StoreSimulationInfoAll, 17, MSimEvent::GetOutputVersion()).Data();
      Require(!truth.empty(), "selected full truth serialization is empty");
      const std::streamoff offset = m_TruthOut.tellp();
      m_TruthOut.write(truth.data(), static_cast<std::streamsize>(truth.size()));
      const std::string truthReason = rawTES && row.control ? "candidate+control" : (rawTES ? "candidate" : "control");
      m_TruthIndexOut << simulationID << '\t' << row.stableRootID << '\t' << truthReason << '\t'
                      << offset << '\t' << truth.size() << '\t' << SHA256(truth) << '\n';
      ++m_TruthIndexRowCount;
    }
    Require(m_EventOut.good() && m_PixelOut.good() && m_DepositOut.good() && m_VetoBlockOut.good() &&
            m_TruthOut.good() && m_TruthIndexOut.good(), "compact event output write failure");
  }
  m_Lifecycle.FinishEvent(simulationID, false, true);
}

void M05CompactScorer::FlushSyncClose(M05DurableFile& stream, const std::string& path)
{
  const M05DurableMetadata metadata = stream.CloseDurable();
  Require(metadata.path == path, "durable output path mismatch: " + path);
  Require(metadata.sha256 == SHA256File(path), "durable output digest verification failed: " + path);
  Require(metadata.sizeBytes == FileSize(path), "durable output size verification failed: " + path);
}

void M05CompactScorer::PublishTransaction()
{
  m_RootOut.VerifyClosedIdentity();
  m_GeneratedObservationOut.VerifyClosedIdentity();
  m_FooterOut.VerifyClosedIdentity();
  if (IsCompactArm()) {
    m_EventOut.VerifyClosedIdentity();
    m_PixelOut.VerifyClosedIdentity();
    m_DepositOut.VerifyClosedIdentity();
    m_VetoBlockOut.VerifyClosedIdentity();
    m_ActivationOut.VerifyClosedIdentity();
    m_TruthOut.VerifyClosedIdentity();
    m_TruthIndexOut.VerifyClosedIdentity();
  }
  const std::string stagePrefix = m_StageDirectory + "/";
  Require(m_NativeDatPath.compare(0, stagePrefix.size(), stagePrefix) == 0,
          "native isotope DAT resolved outside transaction envelope");
  const std::string nativeDatBasename = m_NativeDatPath.substr(stagePrefix.size());
  Require(!nativeDatBasename.empty() && nativeDatBasename.find('/') == std::string::npos,
          "native isotope DAT basename is invalid");
  RequireRegularNoLink(m_NativeDatPath);
  Require(FileSize(m_NativeDatPath) > 0, "native isotope DAT is empty");
  SyncExistingRegularFile(m_NativeDatPath);
  std::ostringstream manifest;
  if (IsCompactArm()) {
    const auto binding = [&](const std::string& name, long rows) {
      const std::string path = m_StageDirectory + "/" + name;
      std::ostringstream out;
      out << "{\"path\":\"" << name << "\",\"row_count\":" << rows
          << ",\"sha256\":\"" << SHA256File(path) << "\"}";
      return out.str();
    };
    const auto blob = [&](const std::string& name) {
      const std::string path = m_StageDirectory + "/" + name;
      std::ostringstream out;
      out << "{\"path\":\"" << name << "\",\"sha256\":\"" << SHA256File(path)
          << "\",\"size_bytes\":" << FileSize(path) << '}';
      return out.str();
    };
    manifest << "{\"blobs\":{\"native_dat\":" << blob(nativeDatBasename)
             << ",\"truth_stream\":" << blob("truth.sim") << "},\"record_schema_sha256\":\""
             << m_RecordSchemaSHA256 << "\",\"geometry_classification_sha256\":\""
             << m_GeometryClassificationSHA256 << "\",\"provenance\":{\"geometry_bundle_sha256\":\""
             << m_GeometryBundleSHA256 << "\",\"tape_root_sidecar_sha256\":\"" << m_TapeSHA256
             << "\",\"tape_root_sidecar_path\":\"" << m_TapePath
             << "\",\"source_card_sha256\":\"" << m_CorrectedSourceCardSHA256
             << "\",\"source_contract_sha256\":\"" << m_SourceContractSHA256
             << "\"},\"run\":{\"active_block_coverage\":\"geometry_specific\",\"arm\":\"C\"," 
             << "\"expected_event_count\":" << m_Tape.size() << ",\"family\":\"" << JsonEscape(m_Family)
             << "\",\"geometry\":\"" << JsonEscape(m_Geometry) << "\",\"job_id\":\"" << JsonEscape(m_JobID)
             << "\",\"mode\":\"" << JsonEscape(m_Mode) << "\",\"seed\":" << m_Seed
             << ",\"shard_index\":" << m_ShardIndex << "},\"schema_version\":\"m05cc-v2-record-bundle\",\"tables\":{"
             << "\"activation\":" << binding("activation.tsv", static_cast<long>(m_RPCount))
             << ",\"deposits\":" << binding("deposits.tsv", m_DepositRowCount)
             << ",\"events\":" << binding("events.tsv", m_EventRowCount)
             << ",\"footer\":" << binding("footer.tsv", 1)
             << ",\"generated_observations\":" << binding("generated_observations.tsv", m_GeneratedObservationRowCount)
             << ",\"pixels\":" << binding("pixels.tsv", m_PixelRowCount)
             << ",\"roots\":" << binding("roots.tsv", m_RootCount)
             << ",\"truth_index\":" << binding("truth_index.tsv", m_TruthIndexRowCount)
             << ",\"veto_blocks\":" << binding("veto_blocks.tsv", m_VetoBlockRowCount)
             << "},\"veto_whitelist_sha256\":\"" << m_WhitelistSHA256 << "\"}\n";
    WriteDurableExclusive(m_StageDirectory + "/record_bundle.json", manifest.str());
  } else {
    const auto tableBinding = [&](const std::string& name, long rows) {
      const std::string path = m_StageDirectory + "/" + name;
      std::ostringstream out;
      out << "{\"path\":\"" << name << "\",\"row_count\":" << rows
          << ",\"sha256\":\"" << SHA256File(path) << "\",\"size_bytes\":" << FileSize(path) << '}';
      return out.str();
    };
    const auto blobBinding = [&](const std::string& name) {
      const std::string path = m_StageDirectory + "/" + name;
      std::ostringstream out;
      out << "{\"path\":\"" << name << "\",\"sha256\":\"" << SHA256File(path)
          << "\",\"size_bytes\":" << FileSize(path) << '}';
      return out.str();
    };
    manifest << "{\"arm\":\"N1\",\"corrected_source_card_sha256\":\"" << m_CorrectedSourceCardSHA256
             << "\",\"footer\":" << tableBinding("footer.tsv", 1)
             << ",\"generated_observations\":"
             << tableBinding("generated_observations.tsv", m_GeneratedObservationRowCount)
             << ",\"geometry_bundle_sha256\":\"" << m_GeometryBundleSHA256
             << "\",\"geometry_classification_sha256\":\"" << m_GeometryClassificationSHA256
             << "\",\"n1_commit_schema_sha256\":\"" << m_N1CommitSchemaSHA256
             << "\",\"native_added_isotope_count\":" << m_NativeAddedIsotopeCount
             << ",\"native_dat\":" << blobBinding(nativeDatBasename)
             << ",\"roots\":" << tableBinding("roots.tsv", m_RootCount)
             << ",\"run\":{\"arm\":\"N1\",\"expected_event_count\":" << m_Tape.size()
             << ",\"family\":\"" << JsonEscape(m_Family) << "\",\"geometry\":\"" << JsonEscape(m_Geometry)
             << "\",\"job_id\":\"" << JsonEscape(m_JobID) << "\",\"mode\":\"" << JsonEscape(m_Mode)
             << "\",\"seed\":" << m_Seed << ",\"shard_index\":" << m_ShardIndex << '}'
             << ",\"runtime_source_card_sha256\":\"" << m_RuntimeSourceCardSHA256
             << "\",\"schema_version\":\"m05cc-n1-v1-commit\",\"source_contract_sha256\":\""
             << m_SourceContractSHA256 << "\",\"status\":\"PASS__N1_TRANSACTION_COMPLETE\""
             << ",\"tape_root_sidecar\":" << tableBinding(m_TapePath, static_cast<long>(m_Tape.size()))
             << ",\"veto_whitelist_sha256\":\"" << m_WhitelistSHA256 << "\"}\n";
    WriteDurableExclusive(m_StageDirectory + "/commit.json", manifest.str());
  }
  SyncDirectory(m_StageDirectory);
  M05DurableFile::PublishDirectoryDurableNoReplace(m_StageDirectory, m_FinalDirectory);
}

void M05CompactScorer::EndRun(double simulatedTimeSeconds,
                              unsigned long nativeAddedIsotopes,
                              bool nativeStopConditionReached,
                              const std::string& nativeDatPath,
                              int parallelID,
                              int incarnationID)
{
  Require(m_Configured && !m_Finalized, "EndRun outside active run");
  Require(!TerminationRequested(), "termination signal observed; publication quarantined");
  Require(nativeStopConditionReached, "native run ended before its stop condition");
  Require(parallelID >= 0 && incarnationID >= 0, "invalid native parallel/incarnation identity");
  std::ostringstream expectedNativeDat;
  expectedNativeDat << m_StageDirectory << "/native";
  if (parallelID != 0) expectedNativeDat << ".p" << parallelID;
  expectedNativeDat << ".inc" << incarnationID << ".dat";
  Require(nativeDatPath == expectedNativeDat.str(),
          "native SaveIsotopeStore target differs from derived parallel/incarnation path");
  m_NativeDatPath = nativeDatPath;
  m_NativeAddedIsotopeCount = nativeAddedIsotopes;
  m_Lifecycle.RequireFinalClosure(static_cast<long>(m_Tape.size()));
  Require(m_RootCount == static_cast<long>(m_Tape.size()) && m_InitCount == static_cast<long>(m_Tape.size()) &&
          m_SECount == static_cast<long>(m_Tape.size()) && m_IDCount == static_cast<long>(m_Tape.size()) &&
          m_NativeIDs.size() == m_Tape.size(), "root/IA INIT/SE/ID count closure failed");
  Require(std::isfinite(simulatedTimeSeconds) && simulatedTimeSeconds > 0.0, "TT is not positive finite");
  Require(m_GeneratedObservationRowCount == static_cast<long>(m_Tape.size()),
          "generated-observation table count mismatch");
  Require(!IsCompactArm() || nativeAddedIsotopes == m_RPCount, "RP sidecar/native AddIsotope count mismatch");
  if (IsCompactArm()) {
    Require(m_EventRowCount == static_cast<long>(m_Tape.size()), "event table count mismatch");
    const long expectedBlocks = static_cast<long>(m_Tape.size()) * (m_Geometry == "mass_model_511" ? 24L : 6L);
    Require(m_VetoBlockRowCount == expectedBlocks, "per-event active block completeness mismatch");
    Require(m_TruthIndexRowCount > 0, "pre-registered control truth was not serialized");
    Require(m_TESZeroControlCount > 0,
            "shard lacks a post-transport TES-zero pre-registered control; extend/review without publication");
  }
  m_FooterOut << m_Arm << '\t' << m_Geometry << '\t' << m_Mode << '\t' << m_Family << '\t'
              << m_JobID << '\t' << m_ShardIndex << '\t' << m_Seed << '\t' << m_Tape.size() << '\t'
              << m_Lifecycle.GeneratedCount() << '\t' << m_Lifecycle.StartedCount() << '\t'
              << m_Lifecycle.CompletedCount() << '\t' << m_Lifecycle.NativePopulatedCount() << '\t'
              << m_RootCount << '\t' << m_InitCount << '\t' << m_SECount << '\t' << m_IDCount << '\t'
              << m_Lifecycle.AbortedCount() << '\t' << m_RPCount << '\t' << std::setprecision(17)
              << simulatedTimeSeconds << "\tgeometry_specific\t" << m_WhitelistSHA256 << '\t'
              << (IsCompactArm() ? m_RecordSchemaSHA256 : m_N1CommitSchemaSHA256) << "\t1\n";

  FlushSyncClose(m_RootOut, m_StageDirectory + "/roots.tsv");
  FlushSyncClose(m_GeneratedObservationOut, m_StageDirectory + "/generated_observations.tsv");
  FlushSyncClose(m_FooterOut, m_StageDirectory + "/footer.tsv");
  if (IsCompactArm()) {
    FlushSyncClose(m_EventOut, m_StageDirectory + "/events.tsv");
    FlushSyncClose(m_PixelOut, m_StageDirectory + "/pixels.tsv");
    FlushSyncClose(m_DepositOut, m_StageDirectory + "/deposits.tsv");
    FlushSyncClose(m_VetoBlockOut, m_StageDirectory + "/veto_blocks.tsv");
    FlushSyncClose(m_ActivationOut, m_StageDirectory + "/activation.tsv");
    FlushSyncClose(m_TruthOut, m_StageDirectory + "/truth.sim");
    FlushSyncClose(m_TruthIndexOut, m_StageDirectory + "/truth_index.tsv");
  }
  PublishTransaction();
  m_Finalized = true;
}
