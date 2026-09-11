#ifndef SH3_SIMULATION_DATA_HH
#define SH3_SIMULATION_DATA_HH

#include <cstdint>
#include <map>
#include <memory>
#include <string>
#include <vector>

struct Deposit {
  int eventOrder = 0;
  int hitOrder = 0;
  int layer = 0;
  std::string sampleId;
  std::string jobId;
  std::int64_t originalEventId = 0;
  std::string candidate;
  bool strictRecoil = false;
  double directTesKeV = 0.;
  double bgoKeV = 0.;
  double localXmm = 0.;
  double localYmm = 0.;
  double localZmm = 0.;
  double timeNs = 0.;
  double energyKeV = 0.;
};

struct DepositGroup {
  int simEventId = 0;
  std::string groupKey;
  int eventOrder = 0;
  int layer = 0;
  std::string sampleId;
  std::string jobId;
  std::int64_t originalEventId = 0;
  std::string candidate;
  bool strictRecoil = false;
  double directTesKeV = 0.;
  double bgoKeV = 0.;
  double inputEnergyKeV = 0.;
  double referenceTimeNs = 0.;
  std::vector<Deposit> deposits;
};

struct Pixel {
  int id = -1;
  double ymm = 0.;
  double zmm = 0.;
};

struct RunConfig {
  std::string inputCsv;
  std::string pixelCsv;
  std::string outputCsv;
  std::string eventMapCsv;
  std::string summaryJson;
  int packetsPerHit = 128;
  int packetsPerGroup = 0;
  double packetEnergyMeV = 2.7;
  double sensorAreaScale = 1.;
  double sensorAbsorption = 0.30;
  double bathAbsorption = 0.10;
  double specularProbability = 0.;
  int maxPhononBounces = 20000;
  int millerH = 1;
  int millerK = 0;
  int millerL = 0;
  long seed1 = 240903;
  long seed2 = 511420;
};

std::vector<DepositGroup> LoadDepositGroups(const std::string& path);
std::vector<Pixel> LoadPixels(const std::string& path);
void WriteEventMap(const std::string& path,
                   const std::vector<DepositGroup>& groups,
                   const RunConfig& config);
std::vector<int> AllocatePacketCounts(const DepositGroup& group,
                                      const RunConfig& config);
RunConfig ParseArguments(int argc, char** argv);
void PrintUsage(const char* argv0);
std::string JsonEscape(const std::string& in);

#endif
