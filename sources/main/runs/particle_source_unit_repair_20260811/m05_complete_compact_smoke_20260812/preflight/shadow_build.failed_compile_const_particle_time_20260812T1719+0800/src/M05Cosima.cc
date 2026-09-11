#include "MCMain.hh"
#include "M05CompactScorer.hh"

#include "TApplication.h"
#include "MStreams.h"

#include <csignal>
#include <exception>
#include <iostream>
#include <unistd.h>

MCMain* g_Main = nullptr;

void CatchSignal(int signal)
{
  // Do not call iostreams, allocation, MCMain, ROOT, or Geant4 from a signal
  // handler.  The sig_atomic_t notification plus POSIX _exit are the complete
  // handler: an interrupted process cannot reach EndRun/publication, and any
  // exclusively created *.partial transaction remains quarantined.
  M05CompactScorer::NotifyTerminationSignal();
  ::_exit(128 + signal);
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
