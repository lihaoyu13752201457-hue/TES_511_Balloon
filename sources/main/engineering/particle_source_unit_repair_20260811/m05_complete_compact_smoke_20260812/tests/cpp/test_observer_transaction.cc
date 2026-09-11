#include "M05ObserverTransaction.hh"

#include <fstream>
#include <iostream>
#include <string>

#include <sys/stat.h>
#include <unistd.h>

namespace {
int gSyncCalls = 0;

bool FailFirstSync(const std::string&)
{
  ++gSyncCalls;
  return gSyncCalls != 1;
}

bool AlwaysPassSync(const std::string&)
{
  return true;
}

bool Exists(const std::string& path)
{
  struct stat state;
  return ::lstat(path.c_str(), &state) == 0;
}
}

int main(int argc, char** argv)
{
  if (argc != 2) return 64;
  const std::string root = argv[1];
  const std::string stage = root + "/observer.gpsobs.partial";
  const std::string final = root + "/observer.gpsobs";
  const std::string failed0 = final + ".failed";
  const std::string failedPid = failed0 + "." + std::to_string(static_cast<long>(::getpid()));
  const std::string failedNext = failedPid + ".1";
  if (::mkdir(stage.c_str(), 0700) != 0 || ::mkdir(failed0.c_str(), 0700) != 0 ||
      ::mkdir(failedPid.c_str(), 0700) != 0) return 1;
  {
    std::ofstream marker((stage + "/observer_generated_only.json").c_str(), std::ios::binary);
    marker << "owned-pass-marker\n";
  }
  {
    std::ofstream marker((failed0 + "/foreign").c_str(), std::ios::binary);
    marker << "foreign-zero\n";
  }
  {
    std::ofstream marker((failedPid + "/foreign").c_str(), std::ios::binary);
    marker << "foreign-pid\n";
  }
  std::string quarantine;
  const M05ObserverPublishResult result = M05ObserverPublishDirectoryNoReplaceDurable(
    stage, final, FailFirstSync, &quarantine);
  if (result != M05ObserverPublishResult::PostRenameFsyncFailedQuarantined || gSyncCalls != 2 ||
      quarantine != failedNext || Exists(stage) || Exists(final) || !Exists(failedNext) ||
      !Exists(failedNext + "/observer_generated_only.json")) return 2;
  std::ifstream foreign0((failed0 + "/foreign").c_str(), std::ios::binary);
  std::ifstream foreignPid((failedPid + "/foreign").c_str(), std::ios::binary);
  std::string foreign0Bytes;
  std::string foreignPidBytes;
  std::getline(foreign0, foreign0Bytes);
  std::getline(foreignPid, foreignPidBytes);
  if (foreign0Bytes != "foreign-zero" || foreignPidBytes != "foreign-pid") return 3;

  // A foreign final present before publication is never moved or replaced.
  const std::string collisionStage = root + "/collision.partial";
  const std::string collisionFinal = root + "/collision.final";
  if (::mkdir(collisionStage.c_str(), 0700) != 0 || ::mkdir(collisionFinal.c_str(), 0700) != 0) return 4;
  {
    std::ofstream marker((collisionFinal + "/foreign").c_str(), std::ios::binary);
    marker << "incumbent\n";
  }
  quarantine.clear();
  if (M05ObserverPublishDirectoryNoReplaceDurable(
        collisionStage, collisionFinal, AlwaysPassSync, &quarantine) !=
        M05ObserverPublishResult::InitialRenameFailed ||
      !Exists(collisionStage) || !Exists(collisionFinal) || !quarantine.empty()) return 5;
  std::ifstream incumbent((collisionFinal + "/foreign").c_str(), std::ios::binary);
  std::string incumbentBytes;
  std::getline(incumbent, incumbentBytes);
  if (incumbentBytes != "incumbent") return 6;

  std::cout << "PASS observer_transaction_nontransport\n";
  return 0;
}
