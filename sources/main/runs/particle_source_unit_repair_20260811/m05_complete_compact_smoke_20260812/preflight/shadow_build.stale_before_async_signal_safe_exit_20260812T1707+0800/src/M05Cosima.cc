#include "MCMain.hh"
#include "M05CompactScorer.hh"

#include "TApplication.h"
#include "MStreams.h"

#include <csignal>
#include <exception>
#include <iostream>

MCMain* g_Main = nullptr;
int g_NInterrupts = 3;

void CatchSignal(int signal)
{
  // The flag assignment itself is signal-safe. Legacy MCMain::Interrupt and
  // diagnostics are retained here; publication nevertheless rechecks the flag
  // at EndRun and fails closed.
  M05CompactScorer::NotifyTerminationSignal();
  std::cerr << "Caught signal " << signal << std::endl;
  if (--g_NInterrupts <= 0) std::abort();
  if (g_Main != nullptr) g_Main->Interrupt();
}

int main(int argc, char** argv)
{
  try {
    std::signal(SIGINT, CatchSignal);
    std::signal(SIGTERM, CatchSignal);
    TApplication rootApplication("ROOT", 0, 0);
    MGlobal::Initialize("M05Cosima", "isolated TES511 compact-output benchmark");
    __merr.SetHeader("M05-COSIMA-ERROR:");
    g_Main = new MCMain();
    const unsigned int parseStatus = g_Main->ParseCommandLine(argc, argv);
    if (parseStatus >= 2) throw std::runtime_error("Cosima command-line parsing failed");
    if (parseStatus == 1) {
      delete g_Main;
      g_Main = nullptr;
      return 0;
    }
    if (!g_Main->Initialize()) throw std::runtime_error("Geant4 initialization failed");
    // Parameter-file parsing and Geant4 initialization must succeed before the
    // scorer creates any partial output.  Inspect the actual initialized
    // parameters (one run, Everything/All/StoreOneHit=false) at this boundary.
    M05CompactScorer::Instance().ConfigureAfterInitialization(g_Main->GetParameterFile());
    if (!g_Main->Execute()) throw std::runtime_error("run execution failed");
    delete g_Main;
    g_Main = nullptr;
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "M05 fail-closed exception: " << error.what() << std::endl;
    delete g_Main;
    g_Main = nullptr;
    return 97;
  }
}
