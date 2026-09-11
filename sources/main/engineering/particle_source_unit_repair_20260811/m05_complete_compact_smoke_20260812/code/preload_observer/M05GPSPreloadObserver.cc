// Read-only post-GPS observer for the installed Cosima F/U reference arms.
//
// This translation unit is compiled as a small LD_PRELOAD library.  It
// interposes the exported MCRun::GeneratePrimaries boundary, invokes the
// installed implementation exactly once, and only then inspects the primary
// vertex that the installed implementation added.  It never changes the GPS,
// event, run, source, physics, or random-engine state.

#include "MCRun.hh"
#include "../shadow_extensions/M05NoReplace.hh"
#include "M05ObserverTransaction.hh"

#include "G4Event.hh"
#include "G4GeneralParticleSource.hh"
#include "G4Ions.hh"
#include "G4ParticleDefinition.hh"
#include "G4PrimaryParticle.hh"
#include "G4PrimaryVertex.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"

#include <openssl/sha.h>

#include <cmath>
#include <csignal>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <fcntl.h>
#include <fstream>
#include <iomanip>
#include <limits.h>
#include <sstream>
#include <string>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <vector>

namespace {

const char* const kTargetSymbol =
  "_ZN5MCRun17GeneratePrimariesEP7G4EventP23G4GeneralParticleSource";
const char* const kPinnedLibCosimaPath =
  "/home/ubuntu/MEGAlib_Install/megalib-main/lib/libCosima.so";
const char* const kPinnedLibCosimaSHA256 =
  "0656a54e0351a72347ad70437a96097b4d37688d10ac9059038e0b697ce6a495";
volatile std::sig_atomic_t gTerminationSignal = 0;

struct Row {
  long eventListID;
  std::string stableRootID;
  int particle;
  double excitationKeV;
  double sourceTimeSeconds;
  std::string expectedGeneratedBinary64SHA256;
};

std::vector<Row> gRows;
std::string gArm;
std::string gTapeSHA256;
std::string gStage;
std::string gFinal;
std::string gObservationPath;
std::string gResolvedOriginalLibraryPath;
std::string gExpectedOriginalLibrarySHA256;
int gOutput = -1;
dev_t gOutputDevice = 0;
ino_t gOutputInode = 0;
std::size_t gObserved = 0;
double gPreviousExpectedRuntimeInternalTime = 0.0;
bool gInitialized = false;
bool gFinalized = false;
thread_local bool gInsideHook = false;

void Finalize() noexcept;

[[noreturn]] void Fail(const std::string& message)
{
  const std::string line = "M05 MCRun preload observer failure: " + message + "\n";
  const ssize_t ignored = ::write(STDERR_FILENO, line.data(), line.size());
  (void) ignored;
  ::_exit(125);
}

void SignalQuarantine(int signalNumber)
{
  gTerminationSignal = signalNumber;
  ::_exit(128 + signalNumber); // the .partial directory remains quarantined
}

std::string RequiredEnvironment(const char* name)
{
  const char* value = ::getenv(name);
  if (value == nullptr || *value == '\0') Fail(std::string("missing environment ") + name);
  return value;
}

bool IsDigest(const std::string& value)
{
  if (value.size() != 64) return false;
  for (unsigned char c : value) {
    if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return false;
  }
  return true;
}

std::vector<std::string> SplitTab(const std::string& line)
{
  std::vector<std::string> fields;
  std::string field;
  std::istringstream input(line);
  while (std::getline(input, field, '\t')) fields.push_back(field);
  if (!line.empty() && line.back() == '\t') fields.push_back("");
  return fields;
}

long StrictLong(const std::string& text)
{
  try {
    std::size_t used = 0;
    const long value = std::stol(text, &used);
    if (used != text.size()) Fail("invalid integer in tape roots");
    return value;
  } catch (...) {
    Fail("invalid integer in tape roots");
  }
}

double StrictDouble(const std::string& text)
{
  try {
    std::size_t used = 0;
    const double value = std::stod(text, &used);
    if (used != text.size() || !std::isfinite(value)) Fail("invalid finite double in tape roots");
    return value;
  } catch (...) {
    Fail("invalid finite double in tape roots");
  }
}

void RequireExistingComponentsNoSymlink(const std::string& absolutePath)
{
  if (absolutePath.empty() || absolutePath[0] != '/' || absolutePath.find("/../") != std::string::npos ||
      (absolutePath.size() >= 3 && absolutePath.compare(absolutePath.size()-3, 3, "/..") == 0)) {
    Fail("path is not an absolute traversal-free path");
  }
  std::string cursor;
  std::istringstream parts(absolutePath);
  std::string part;
  while (std::getline(parts, part, '/')) {
    if (part.empty()) continue;
    cursor += "/" + part;
    struct stat state;
    if (::lstat(cursor.c_str(), &state) != 0) Fail("missing path component: " + cursor);
    if (S_ISLNK(state.st_mode)) Fail("symlinked path component is forbidden: " + cursor);
  }
}

void RequireRegularNoLink(const std::string& path)
{
  RequireExistingComponentsNoSymlink(path);
  struct stat state;
  if (::lstat(path.c_str(), &state) != 0 || !S_ISREG(state.st_mode) || state.st_nlink != 1) {
    Fail("path is not a single-link regular file: " + path);
  }
}

std::string Parent(const std::string& path)
{
  const std::size_t slash = path.rfind('/');
  if (slash == std::string::npos || slash == 0) Fail("observer output prefix has invalid parent");
  return path.substr(0, slash);
}

std::string CanonicalExistingDirectory(const std::string& path)
{
  RequireExistingComponentsNoSymlink(path);
  struct stat state;
  if (::lstat(path.c_str(), &state) != 0 || !S_ISDIR(state.st_mode)) Fail("not an existing directory: " + path);
  char resolved[PATH_MAX];
  if (::realpath(path.c_str(), resolved) == nullptr || path != resolved) Fail("directory is not canonical: " + path);
  return path;
}

std::string CanonicalExistingRegularFile(const std::string& path)
{
  RequireRegularNoLink(path);
  char resolved[PATH_MAX];
  if (::realpath(path.c_str(), resolved) == nullptr || path != resolved) {
    Fail("regular file is not canonical: " + path);
  }
  return path;
}

bool IsWithin(const std::string& path, const std::string& root)
{
  return path == root || (path.size() > root.size() && path.compare(0, root.size(), root) == 0 &&
                          path[root.size()] == '/');
}

std::string SHA256File(const std::string& path)
{
  const int descriptor = ::open(path.c_str(), O_RDONLY | O_NOFOLLOW);
  if (descriptor < 0) Fail("cannot open authority file without following links: " + path);
  struct stat state;
  if (::fstat(descriptor, &state) != 0 || !S_ISREG(state.st_mode) || state.st_nlink != 1) {
    ::close(descriptor);
    Fail("authority descriptor is not a single-link regular file: " + path);
  }
  SHA256_CTX context;
  SHA256_Init(&context);
  char buffer[1024*1024];
  while (true) {
    const ssize_t count = ::read(descriptor, buffer, sizeof(buffer));
    if (count < 0) {
      ::close(descriptor);
      Fail("authority hash read failed: " + path);
    }
    if (count == 0) break;
    SHA256_Update(&context, buffer, static_cast<std::size_t>(count));
  }
  if (::close(descriptor) != 0) Fail("authority hash descriptor close failed: " + path);
  unsigned char digest[SHA256_DIGEST_LENGTH];
  SHA256_Final(digest, &context);
  std::ostringstream out;
  out << std::hex << std::setfill('0');
  for (unsigned char byte : digest) out << std::setw(2) << static_cast<unsigned int>(byte);
  return out.str();
}

std::string SHA256Descriptor(int descriptor)
{
  if (descriptor < 0) Fail("invalid observer descriptor hash request");
  SHA256_CTX context;
  SHA256_Init(&context);
  char buffer[1024*1024];
  off_t offset = 0;
  while (true) {
    const ssize_t count = ::pread(descriptor, buffer, sizeof(buffer), offset);
    if (count < 0) Fail("observer descriptor hash read failed");
    if (count == 0) break;
    SHA256_Update(&context, buffer, static_cast<std::size_t>(count));
    offset += count;
  }
  unsigned char digest[SHA256_DIGEST_LENGTH];
  SHA256_Final(digest, &context);
  std::ostringstream out;
  out << std::hex << std::setfill('0');
  for (unsigned char byte : digest) out << std::setw(2) << static_cast<unsigned int>(byte);
  return out.str();
}

struct FrozenBytes {
  std::string bytes;
  std::string sha256;
};

FrozenBytes ReadAndHashOneDescriptor(const std::string& path)
{
  const int descriptor = ::open(path.c_str(), O_RDONLY | O_NOFOLLOW);
  if (descriptor < 0) Fail("cannot open frozen input without following links: " + path);
  struct stat state;
  if (::fstat(descriptor, &state) != 0 || !S_ISREG(state.st_mode) || state.st_nlink != 1 || state.st_size < 0) {
    ::close(descriptor);
    Fail("frozen input descriptor is not a single-link regular file: " + path);
  }
  FrozenBytes result;
  result.bytes.reserve(static_cast<std::size_t>(state.st_size));
  SHA256_CTX context;
  SHA256_Init(&context);
  char buffer[1024*1024];
  while (true) {
    const ssize_t count = ::read(descriptor, buffer, sizeof(buffer));
    if (count < 0) {
      ::close(descriptor);
      Fail("frozen input read failed: " + path);
    }
    if (count == 0) break;
    result.bytes.append(buffer, static_cast<std::size_t>(count));
    SHA256_Update(&context, buffer, static_cast<std::size_t>(count));
  }
  if (::close(descriptor) != 0) Fail("frozen input descriptor close failed: " + path);
  unsigned char digest[SHA256_DIGEST_LENGTH];
  SHA256_Final(digest, &context);
  std::ostringstream out;
  out << std::hex << std::setfill('0');
  for (unsigned char byte : digest) out << std::setw(2) << static_cast<unsigned int>(byte);
  result.sha256 = out.str();
  return result;
}

std::string Binary64Digest(int particle, double excitationKeV, double sourceTimeSeconds,
                           const double position[3], const double direction[3],
                           const double polarization[3], double energyKeV)
{
  static_assert(sizeof(double) == 8, "binary64 observer requires eight-byte double");
  const double values[12] = {
    excitationKeV, sourceTimeSeconds, position[0], position[1], position[2],
    direction[0], direction[1], direction[2], polarization[0], polarization[1], polarization[2], energyKeV
  };
  static const char domain[] = "m05-eventlist-binary64-v1";
  static_assert(sizeof(domain) == 26, "binary64 domain must be exactly 25 bytes plus one NUL");
  std::string payload(domain, sizeof(domain)); // one and only one NUL domain separator
  const std::uint32_t particleBits = static_cast<std::uint32_t>(particle);
  for (int shift = 24; shift >= 0; shift -= 8) {
    payload.push_back(static_cast<char>((particleBits >> shift) & 0xffU));
  }
  for (double value : values) {
    if (!std::isfinite(value)) Fail("non-finite generated primary field");
    std::uint64_t bits = 0;
    std::memcpy(&bits, &value, sizeof(bits));
    for (int shift = 56; shift >= 0; shift -= 8) {
      payload.push_back(static_cast<char>((bits >> shift) & 0xffULL));
    }
  }
  unsigned char digest[SHA256_DIGEST_LENGTH];
  ::SHA256(reinterpret_cast<const unsigned char*>(payload.data()), payload.size(), digest);
  std::ostringstream out;
  out << std::hex << std::setfill('0');
  for (unsigned char byte : digest) out << std::setw(2) << static_cast<unsigned int>(byte);
  return out.str();
}

bool SameBinary64(double left, double right)
{
  std::uint64_t a = 0;
  std::uint64_t b = 0;
  std::memcpy(&a, &left, sizeof(a));
  std::memcpy(&b, &right, sizeof(b));
  return a == b;
}

bool SameVectorBinary64(const G4ThreeVector& left, const G4ThreeVector& right)
{
  return SameBinary64(left.x(), right.x()) && SameBinary64(left.y(), right.y()) &&
         SameBinary64(left.z(), right.z());
}

void WriteAll(int descriptor, const std::string& data)
{
  std::size_t offset = 0;
  while (offset < data.size()) {
    const ssize_t count = ::write(descriptor, data.data()+offset, data.size()-offset);
    if (count <= 0) Fail("durable observer write failed");
    offset += static_cast<std::size_t>(count);
  }
}

void WriteExclusive(const std::string& path, const std::string& data)
{
  const int descriptor = ::open(path.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
  if (descriptor < 0) Fail("refusing to overwrite observer artifact");
  WriteAll(descriptor, data);
  if (::fsync(descriptor) != 0 || ::close(descriptor) != 0) Fail("observer artifact durability failure");
}

bool TrySyncDirectory(const std::string& path)
{
  const int descriptor = ::open(path.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW);
  if (descriptor < 0) return false;
  const bool synced = ::fsync(descriptor) == 0;
  const bool closed = ::close(descriptor) == 0;
  return synced && closed;
}

void SyncDirectory(const std::string& path)
{
  if (!TrySyncDirectory(path)) Fail("directory durability failure");
}

void InitializeObserver()
{
  if (gInitialized) return;
  gArm = RequiredEnvironment("TES511_PRELOAD_ARM");
  if (gArm != "F" && gArm != "U") Fail("preload observer permits only F/U");
  const std::string expectedLibrary = RequiredEnvironment("TES511_PRELOAD_EXPECTED_LIBCOSIMA");
  gExpectedOriginalLibrarySHA256 = RequiredEnvironment("TES511_PRELOAD_EXPECTED_LIBCOSIMA_SHA256");
  if (expectedLibrary != kPinnedLibCosimaPath ||
      gExpectedOriginalLibrarySHA256 != kPinnedLibCosimaSHA256 ||
      !IsDigest(gExpectedOriginalLibrarySHA256)) {
    Fail("runtime libCosima authority differs from the compile-time frozen identity");
  }
  gResolvedOriginalLibraryPath = CanonicalExistingRegularFile(expectedLibrary);
  if (SHA256File(gResolvedOriginalLibraryPath) != gExpectedOriginalLibrarySHA256) {
    Fail("runtime libCosima SHA-256 differs from the compile-time frozen identity");
  }

  const std::string tape = RequiredEnvironment("TES511_PRELOAD_TAPE_ROOT_SIDECAR");
  gTapeSHA256 = RequiredEnvironment("TES511_PRELOAD_TAPE_ROOT_SIDECAR_SHA256");
  RequireRegularNoLink(tape);
  const FrozenBytes tapeAuthority = ReadAndHashOneDescriptor(tape);
  if (!IsDigest(gTapeSHA256) || tapeAuthority.sha256 != gTapeSHA256) Fail("tape-root SHA-256 mismatch");

  const std::string allowedRoot = CanonicalExistingDirectory(RequiredEnvironment("TES511_PRELOAD_ALLOWED_ROOT"));
  const std::string prefix = RequiredEnvironment("TES511_PRELOAD_OUTPUT_PREFIX");
  if (prefix.empty() || prefix[0] != '/' || prefix.find("..") != std::string::npos) {
    Fail("unsafe observer output prefix");
  }
  const std::string outputParent = CanonicalExistingDirectory(Parent(prefix));
  if (!IsWithin(outputParent, allowedRoot)) Fail("observer output is outside the allowlisted run root");
  if (prefix.find('/', outputParent.size()+1) != std::string::npos) Fail("observer prefix must be a direct child path");

  gStage = prefix + ".gpsobs.partial";
  gFinal = prefix + ".gpsobs";
  struct stat state;
  if (::lstat(gStage.c_str(), &state) == 0 || ::lstat(gFinal.c_str(), &state) == 0) {
    Fail("observer transaction path exists");
  }
  if (::mkdir(gStage.c_str(), 0700) != 0) Fail("cannot create observer transaction stage");
  SyncDirectory(outputParent);

  std::istringstream input(tapeAuthority.bytes);
  std::string line;
  if (!std::getline(input, line)) Fail("empty tape roots");
  static const char* expectedHeader =
    "schema\trow_index0\tglobal_row_index0\teventlist_id\tstable_root_id\tdriver\tdriver_assignment\tbin_index\t"
    "family\tmode\tsource_card_path\tsource_card_sha256\tsource_contract_path\tsource_contract_sha256\t"
    "spectrum_path\tspectrum_sha256\tsampler_algorithm\tsampler_seed_u64\tsampler_counter_start0\t"
    "sampler_counter_end0\tparticle\texcitation_keV\tsource_time_s\tglobal_poisson_time_s\t"
    "shard_global_time_offset_s\tx_cm\ty_cm\tz_cm\tdx\tdy\tdz\tpx\tpy\tpz\tenergy_keV\t"
    "raw_eventlist_line_sha256\texpected_eventlist_binary64_sha256\texpected_generated_binary64_sha256\t"
    "expected_generated_tuple_sha256\tcontrol_flag";
  if (line != expectedHeader) Fail("tape-root exact 40-column header mismatch");
  while (std::getline(input, line)) {
    if (line.empty()) Fail("blank tape-root row");
    const std::vector<std::string> fields = SplitTab(line);
    if (fields.size() != 40 || fields[0] != "m05-tape-root-v2") Fail("malformed tape-root row");
    Row row;
    row.eventListID = StrictLong(fields[3]);
    row.stableRootID = fields[4];
    row.particle = static_cast<int>(StrictLong(fields[20]));
    row.excitationKeV = StrictDouble(fields[21]);
    row.sourceTimeSeconds = StrictDouble(fields[22]);
    row.expectedGeneratedBinary64SHA256 = fields[37];
    if (row.eventListID != static_cast<long>(gRows.size()+1) || !IsDigest(row.stableRootID) ||
        !IsDigest(row.expectedGeneratedBinary64SHA256) || row.excitationKeV != 0.0) {
      Fail("tape-root order/digest/excitation contract mismatch");
    }
    gRows.push_back(row);
  }
  if (!input.eof() || gRows.empty()) Fail("tape-root read/count failure");

  gObservationPath = gStage + "/generated_observations.tsv";
  gOutput = ::open(gObservationPath.c_str(),
                   O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
  if (gOutput < 0) Fail("cannot open observer sidecar exclusively");
  struct stat outputState;
  if (::fstat(gOutput, &outputState) != 0 || !S_ISREG(outputState.st_mode) || outputState.st_nlink != 1) {
    Fail("observer sidecar descriptor is not a single-link regular file");
  }
  gOutputDevice = outputState.st_dev;
  gOutputInode = outputState.st_ino;
  WriteAll(gOutput,
    "simulation_event_id\tstable_root_id\teventlist_id\tarm\tobserved_particle\t"
    "observed_excitation_keV\texpected_source_time_s\tobserved_source_time_s\t"
    "observed_x_cm\tobserved_y_cm\tobserved_z_cm\tobserved_dx\tobserved_dy\tobserved_dz\t"
    "observed_px\tobserved_py\tobserved_pz\tobserved_energy_keV\t"
    "expected_generated_binary64_sha256\tobserved_generated_binary64_sha256\n");
  ::signal(SIGINT, SignalQuarantine);
  ::signal(SIGTERM, SignalQuarantine);
  ::signal(SIGHUP, SignalQuarantine);
  if (std::atexit(Finalize) != 0) Fail("cannot register observer finalizer");
  gInitialized = true;
}

int M05ParticleType(const G4ParticleDefinition* definition)
{
  if (definition == nullptr) Fail("GPS has no generated particle definition");
  switch (definition->GetPDGEncoding()) {
  case 22: return 1;
  case -11: return 2;
  case 11: return 3;
  case 2112: return 6;
  case -13: return 8;
  case 13: return 9;
  case 1000020040: return 21;
  default: Fail("unsupported generated PDG code");
  }
}

double ExcitationKeV(const G4ParticleDefinition* definition)
{
  if (definition == nullptr) Fail("GPS has no generated particle definition");
  const G4Ions* ion = dynamic_cast<const G4Ions*>(definition);
  return ion == nullptr ? 0.0 : ion->GetExcitationEnergy()/keV;
}

using OriginalFunction = void (*)(MCRun*, G4Event*, G4GeneralParticleSource*);

OriginalFunction ResolveOriginal()
{
  (void) ::dlerror();
  void* address = ::dlsym(RTLD_NEXT, kTargetSymbol);
  const char* error = ::dlerror();
  if (address == nullptr || error != nullptr) {
    Fail(std::string("RTLD_NEXT symbol resolution failed: ") + (error == nullptr ? "null" : error));
  }
  Dl_info information;
  std::memset(&information, 0, sizeof(information));
  if (::dladdr(address, &information) == 0 || information.dli_fname == nullptr) {
    Fail("dladdr cannot attest the RTLD_NEXT target origin");
  }
  char resolvedOrigin[PATH_MAX];
  if (::realpath(information.dli_fname, resolvedOrigin) == nullptr ||
      gResolvedOriginalLibraryPath != resolvedOrigin) {
    Fail("RTLD_NEXT target does not originate from the frozen installed libCosima");
  }
  OriginalFunction function = nullptr;
  static_assert(sizeof(function) == sizeof(address), "function pointer representation mismatch");
  std::memcpy(&function, &address, sizeof(function));
  return function;
}

void FinalizeImpl()
{
  if (!gInitialized || gFinalized || gTerminationSignal != 0) return;
  if (gObserved != gRows.size() || gOutput < 0) return; // incomplete artifacts remain .partial
  struct stat descriptorState;
  if (::fstat(gOutput, &descriptorState) != 0 || !S_ISREG(descriptorState.st_mode) ||
      descriptorState.st_nlink != 1 || descriptorState.st_dev != gOutputDevice ||
      descriptorState.st_ino != gOutputInode) return;
  const std::string observationSHA256 = SHA256Descriptor(gOutput);
  if (::fsync(gOutput) != 0 || ::close(gOutput) != 0) return;
  gOutput = -1;
  struct stat observationState;
  if (::lstat(gObservationPath.c_str(), &observationState) != 0 ||
      !S_ISREG(observationState.st_mode) || observationState.st_nlink != 1 ||
      observationState.st_dev != gOutputDevice || observationState.st_ino != gOutputInode ||
      observationState.st_size != descriptorState.st_size) return;
  std::ostringstream commit;
  commit << "{\"arm\":\"" << gArm << "\",\"artifact_is_transport_authority\":false,"
         << "\"event_count\":" << gObserved << ","
         << "\"generated_observations_path\":\"generated_observations.tsv\","
         << "\"generated_observations_sha256\":\"" << observationSHA256 << "\","
         << "\"generated_observations_size_bytes\":" << observationState.st_size << ","
         << "\"resolved_original_library_path\":\"" << gResolvedOriginalLibraryPath << "\","
         << "\"resolved_original_library_sha256\":\"" << gExpectedOriginalLibrarySHA256 << "\","
         << "\"schema_version\":2,"
         << "\"status\":\"PASS__GENERATED_OBSERVATIONS_ONLY__NOT_JOB_PASS\","
         << "\"tape_root_sidecar_sha256\":\"" << gTapeSHA256 << "\"}\n";
  WriteExclusive(gStage + "/observer_generated_only.json", commit.str());
  SyncDirectory(gStage);
  std::string quarantinePath;
  const M05ObserverPublishResult publish = M05ObserverPublishDirectoryNoReplaceDurable(
    gStage, gFinal, TrySyncDirectory, &quarantinePath);
  if (publish != M05ObserverPublishResult::Published) {
    Fail(std::string("observer transaction publication failed: ") +
         M05ObserverPublishResultName(publish) +
         (quarantinePath.empty() ? "" : "; quarantined as " + quarantinePath));
  }
  gFinalized = true;
}

void Finalize() noexcept
{
  try {
    FinalizeImpl();
  } catch (...) {
    static const char message[] =
      "M05 MCRun preload observer failure: exception escaped transaction finalizer\n";
    const ssize_t ignored = ::write(STDERR_FILENO, message, sizeof(message)-1);
    (void) ignored;
    ::_exit(125);
  }
}

} // namespace

void MCRun::GeneratePrimaries(G4Event* event, G4GeneralParticleSource* particleSource)
{
  if (gInsideHook) Fail("recursive MCRun preload hook");
  gInsideHook = true;
  InitializeObserver();
  if (event == nullptr || particleSource == nullptr || gObserved >= gRows.size() ||
      event->GetEventID() != static_cast<int>(gObserved)) {
    Fail("event pointer/order/count mismatch before installed GeneratePrimaries call");
  }
  const int before = event->GetNumberOfPrimaryVertex();
  static OriginalFunction original = ResolveOriginal();
  original(this, event, particleSource); // exactly one call to the installed implementation
  if (event->GetNumberOfPrimaryVertex() != before+1) Fail("installed MCRun did not add exactly one vertex");
  G4PrimaryVertex* vertex = event->GetPrimaryVertex(before);
  if (vertex == nullptr || vertex->GetNumberOfParticle() != 1) {
    Fail("installed MCRun vertex does not contain exactly one primary");
  }
  G4PrimaryParticle* primary = vertex->GetPrimary(0);
  if (primary == nullptr) Fail("generated primary is null");

  const Row& row = gRows[gObserved];
  const G4ParticleDefinition* definition = particleSource->GetParticleDefinition();
  const int particle = M05ParticleType(definition);
  const double excitationKeV = ExcitationKeV(definition);
  const double sourceTimeSeconds = GetSimulatedTime()/s;
  const double parsedRuntimeInternalTime = row.sourceTimeSeconds*second;
  const double nextRuntimeInternalTime = parsedRuntimeInternalTime - gPreviousExpectedRuntimeInternalTime;
  const double expectedRuntimeInternalTime = nextRuntimeInternalTime + gPreviousExpectedRuntimeInternalTime;
  const double expectedRuntimeTime = expectedRuntimeInternalTime/second;
  if (particle != row.particle || !SameBinary64(excitationKeV, row.excitationKeV) ||
      !SameBinary64(sourceTimeSeconds, expectedRuntimeTime)) {
    Fail("observed particle/excitation/native simulated time differs from tape runtime projection");
  }

  const G4ThreeVector positionVector = particleSource->GetParticlePosition();
  const double position[3] = {positionVector.x()/cm, positionVector.y()/cm, positionVector.z()/cm};
  const G4ThreeVector directionVector = particleSource->GetParticleMomentumDirection();
  const double direction[3] = {directionVector.x(), directionVector.y(), directionVector.z()};
  const G4ThreeVector polarizationVector = particleSource->GetParticlePolarization();
  const double polarization[3] = {polarizationVector.x(), polarizationVector.y(), polarizationVector.z()};
  const double energyKeV = particleSource->GetParticleEnergy()/keV;
  const G4ThreeVector vertexPosition(vertex->GetX0(), vertex->GetY0(), vertex->GetZ0());
  if (primary->GetG4code() != definition || !SameVectorBinary64(vertexPosition, positionVector) ||
      !SameVectorBinary64(primary->GetMomentumDirection(), directionVector) ||
      !SameVectorBinary64(primary->GetPolarization(), polarizationVector) ||
      !SameBinary64(primary->GetKineticEnergy(), particleSource->GetParticleEnergy()) ||
      !SameBinary64(vertex->GetT0(), particleSource->GetParticleTime())) {
    Fail("actual vertex/primary bits differ from the post-GPS getter state");
  }
  const std::string observed = Binary64Digest(
      particle, excitationKeV, sourceTimeSeconds, position, direction, polarization, energyKeV);
  if (observed != row.expectedGeneratedBinary64SHA256) {
    Fail("post-GPS actual binary64 digest differs from frozen tape runtime projection");
  }

  std::ostringstream output;
  output << std::setprecision(17) << (gObserved+1) << '\t' << row.stableRootID << '\t' << row.eventListID
         << '\t' << gArm << '\t' << particle << '\t' << excitationKeV << '\t' << row.sourceTimeSeconds
         << '\t' << sourceTimeSeconds;
  for (double value : position) output << '\t' << value;
  for (double value : direction) output << '\t' << value;
  for (double value : polarization) output << '\t' << value;
  output << '\t' << energyKeV << '\t' << row.expectedGeneratedBinary64SHA256 << '\t' << observed << '\n';
  WriteAll(gOutput, output.str());
  gPreviousExpectedRuntimeInternalTime = expectedRuntimeInternalTime;
  ++gObserved;
  gInsideHook = false;
}
