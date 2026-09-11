#include "SimulationData.hh"
#include "SiActionInitialization.hh"
#include "SiDetectorConstruction.hh"
#include "SiPhononSensitivity.hh"

#include "G4CMPConfigManager.hh"
#include "G4CMPPhysicsList.hh"
#include "G4RunManager.hh"
#include "G4SystemOfUnits.hh"
#include "Randomize.hh"

#include <chrono>
#include <cstdlib>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <numeric>
#include <stdexcept>

namespace {

std::size_t CountPrimaryPackets(const std::vector<DepositGroup>& groups,
                                const RunConfig& config) {
  std::size_t total = 0;
  for (const auto& group : groups) {
    const auto counts = AllocatePacketCounts(group, config);
    total += std::accumulate(counts.begin(), counts.end(), std::size_t(0));
  }
  return total;
}

void WriteSummary(const RunConfig& config,
                  const std::vector<DepositGroup>& groups,
                  const SiPhononSensitivity& sensitivity,
                  double elapsedSeconds) {
  double inputKeV = 0.;
  std::size_t deposits = 0;
  for (const auto& group : groups) {
    inputKeV += group.inputEnergyKeV;
    deposits += group.deposits.size();
  }
  const double inputEV = inputKeV * 1e3;
  const double sensorEV = sensitivity.SensorEnergyEV();
  const double bathEV = sensitivity.BathEnergyEV();
  const double bulkEV = sensitivity.BulkEnergyEV();
  const double recordedEV = sensorEV + bathEV + bulkEV;
  std::ofstream out(config.summaryJson, std::ios::trunc);
  if (!out) throw std::runtime_error("cannot write summary JSON: " + config.summaryJson);
  out << std::setprecision(17);
  out << "{\n"
      << "  \"schema_version\": 1,\n"
      << "  \"status\": \"COMPLETE\",\n"
      << "  \"engine\": {\"g4cmp_version\": \""
      << JsonEscape(G4CMPConfigManager::Version()) << "\", \"geant4_version\": \"11.4.0\"},\n"
      << "  \"paths\": {\"input_csv\": \"" << JsonEscape(config.inputCsv)
      << "\", \"pixel_csv\": \"" << JsonEscape(config.pixelCsv)
      << "\", \"hit_csv\": \"" << JsonEscape(config.outputCsv)
      << "\", \"event_map_csv\": \"" << JsonEscape(config.eventMapCsv) << "\"},\n"
      << "  \"configuration\": {\n"
      << "    \"packets_per_hit\": " << config.packetsPerHit << ",\n"
      << "    \"packets_per_group\": " << config.packetsPerGroup << ",\n"
      << "    \"packet_energy_meV\": " << config.packetEnergyMeV << ",\n"
      << "    \"sensor_area_scale\": " << config.sensorAreaScale << ",\n"
      << "    \"sensor_absorption_probability_per_encounter\": " << config.sensorAbsorption << ",\n"
      << "    \"bath_absorption_probability_per_encounter\": " << config.bathAbsorption << ",\n"
      << "    \"specular_probability\": " << config.specularProbability << ",\n"
      << "    \"max_phonon_bounces\": " << config.maxPhononBounces << ",\n"
      << "    \"miller_indices\": [" << config.millerH << ',' << config.millerK << ',' << config.millerL << "],\n"
      << "    \"seeds\": [" << config.seed1 << ',' << config.seed2 << "]\n"
      << "  },\n"
      << "  \"counts\": {\"groups\": " << groups.size()
      << ", \"deposits\": " << deposits
      << ", \"primary_packets\": " << CountPrimaryPackets(groups, config)
      << ", \"recorded_terminal_hits\": " << sensitivity.RecordedHits() << "},\n"
      << "  \"energy_eV\": {\"input_weighted\": " << inputEV
      << ", \"sensor\": " << sensorEV << ", \"bath\": " << bathEV
      << ", \"bulk\": " << bulkEV << ", \"recorded_total\": " << recordedEV
      << ", \"closure_fraction\": " << (inputEV > 0. ? recordedEV / inputEV : 0.)
      << ", \"sensor_eta\": " << (inputEV > 0. ? sensorEV / inputEV : 0.) << "},\n"
      << "  \"wall_time_s\": " << elapsedSeconds << "\n"
      << "}\n";
}

}  // namespace

int main(int argc, char** argv) {
  try {
    const RunConfig config = ParseArguments(argc, argv);
    auto groups = std::make_shared<const std::vector<DepositGroup>>(
        LoadDepositGroups(config.inputCsv));
    auto pixels = std::make_shared<const std::vector<Pixel>>(LoadPixels(config.pixelCsv));
    WriteEventMap(config.eventMapCsv, *groups, config);

    // CLHEP engines accept a zero-terminated seed vector; keep the sentinel
    // even though Ranecu consumes the first two entries.
    long seeds[3] = {config.seed1, config.seed2, 0};
    CLHEP::HepRandom::setTheSeeds(seeds, 2);

    auto* runManager = new G4RunManager;
    auto* detector = new SiDetectorConstruction(config, groups, pixels);
    runManager->SetUserInitialization(detector);
    auto* physics = new G4CMPPhysicsList;
    physics->SetCuts();
    runManager->SetUserInitialization(physics);
    runManager->SetUserInitialization(new SiActionInitialization(config, groups));

    G4CMPConfigManager::Instance();
    G4CMPConfigManager::SetVerboseLevel(0);
    G4CMPConfigManager::SetMaxPhononBounces(config.maxPhononBounces);
    G4CMPConfigManager::SetTemperature(0.);
    G4CMPConfigManager::SetMinPhononEnergy(0.);
    G4CMPConfigManager::RecordMinETracks(true);

    const auto start = std::chrono::steady_clock::now();
    runManager->Initialize();
    runManager->BeamOn(static_cast<G4int>(groups->size()));
    const auto stop = std::chrono::steady_clock::now();
    const double elapsed = std::chrono::duration<double>(stop - start).count();
    auto* sensitivity = detector->GetSensitivity();
    if (!sensitivity) throw std::runtime_error("sensitive detector was not constructed");
    WriteSummary(config, *groups, *sensitivity, elapsed);
    sensitivity->Flush();
    const double sensorEV = sensitivity->SensorEnergyEV();
    const double bathEV = sensitivity->BathEnergyEV();
    const double bulkEV = sensitivity->BulkEnergyEV();
    std::cout << "COMPLETE groups=" << groups->size()
              << " deposits=" << std::accumulate(groups->begin(), groups->end(), std::size_t(0),
                   [](std::size_t n, const DepositGroup& g) { return n + g.deposits.size(); })
              << " sensor_eta=";
    double inputEV = 0.;
    for (const auto& group : *groups) inputEV += group.inputEnergyKeV * 1e3;
    std::cout << (inputEV > 0. ? sensorEV / inputEV : 0.)
              << " closure=" << (inputEV > 0. ? (sensorEV + bathEV + bulkEV) / inputEV : 0.)
              << '\n';
    delete runManager;
    std::cout.flush();
    std::cerr.flush();
    // G4CMP V10-05-00 may double-release its shared phonon-boundary helper
    // from Geant4's process-table static destructor for high-multiplicity
    // custom primary stacks.  The official example stress test is clean and
    // all run-owned objects/files above have already been closed.  Bypass only
    // the remaining process-global static teardown; the OS reclaims it.
    std::_Exit(0);
  } catch (const std::exception& error) {
    std::cerr << "ERROR: " << error.what() << '\n';
    return 2;
  }
}
