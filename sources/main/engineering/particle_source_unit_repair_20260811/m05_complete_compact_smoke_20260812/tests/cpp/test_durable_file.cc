#include "M05DurableFile.hh"
#include "M05FrozenInput.hh"

#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <sys/stat.h>
#include <unistd.h>

namespace {
bool Exists(const std::string& path)
{
  struct stat state;
  return ::lstat(path.c_str(), &state) == 0;
}
}

int main(int argc, char** argv)
{
  if (argc != 2) return 64;
  const std::string directory = argv[1];
  const std::string partial = directory + "/data.partial";
  const std::string final = directory + "/data.final";
  M05DurableFile file;
  file.OpenExclusive(partial);
  file << "header\nrow\n";
  file.AddRows(1);
  const M05DurableMetadata metadata = file.CloseDurable();
  if (metadata.sizeBytes != 11 || metadata.rowCount != 1 || metadata.sha256.size() != 64) return 1;
  file.Publish(final);
  M05DurableFile::FsyncDirectory(directory);
  if (Exists(partial) || !Exists(final) || M05DurableFile::SHA256File(final) != metadata.sha256) return 2;

  bool collisionRejected = false;
  try { M05DurableFile::RejectExisting(final); }
  catch (const std::runtime_error&) { collisionRejected = true; }
  if (!collisionRejected) return 3;

  // Publication is race-safe: an existing final appearing after the initial
  // check is never replaced, and both the final and partial bytes survive.
  const std::string racedPartial = directory + "/raced.partial";
  const std::string racedFinal = directory + "/raced.final";
  M05DurableFile raced;
  raced.OpenExclusive(racedPartial);
  raced << "new-bytes\n";
  raced.CloseDurable();
  {
    std::ofstream incumbent(racedFinal.c_str(), std::ios::binary);
    incumbent << "incumbent\n";
  }
  bool noReplaceRejected = false;
  try { raced.Publish(racedFinal); }
  catch (const std::runtime_error&) { noReplaceRejected = true; }
  if (!noReplaceRejected || !Exists(racedPartial) || !Exists(racedFinal)) return 5;
  std::ifstream incumbent(racedFinal.c_str(), std::ios::binary);
  std::string incumbentBytes;
  std::getline(incumbent, incumbentBytes);
  if (incumbentBytes != "incumbent") return 6;

  // A validated input is one descriptor snapshot: later path mutation cannot
  // change the bytes/hash parsed and durably copied by the scorer.
  const std::string source = directory + "/source.tsv";
  {
    std::ofstream input(source.c_str(), std::ios::binary);
    input << "frozen\n";
  }
  const M05FrozenInput frozen = M05ReadFrozenInputOneDescriptor(source);
  {
    std::ofstream mutated(source.c_str(), std::ios::binary | std::ios::trunc);
    mutated << "mutated\n";
  }
  if (frozen.bytes != "frozen\n" || frozen.sha256 == M05DurableFile::SHA256File(source)) return 7;
  const std::string frozenCopy = directory + "/frozen-copy.partial";
  M05DurableFile::WriteExclusiveDurable(frozenCopy, frozen.bytes);
  if (M05DurableFile::SHA256File(frozenCopy) != frozen.sha256) return 8;

  // The scorer's whole-directory commit uses the same no-replace primitive.
  const std::string stageDirectory = directory + "/bundle.partial";
  const std::string finalDirectory = directory + "/bundle.final";
  if (::mkdir(stageDirectory.c_str(), 0700) != 0 || ::mkdir(finalDirectory.c_str(), 0700) != 0) return 9;
  bool directoryNoReplaceRejected = false;
  try { M05DurableFile::PublishDirectoryDurableNoReplace(stageDirectory, finalDirectory); }
  catch (const std::runtime_error&) { directoryNoReplaceRejected = true; }
  if (!directoryNoReplaceRejected || !Exists(stageDirectory) || !Exists(finalDirectory)) return 10;

  // A parent-fsync failure after a successful stage->final rename must leave
  // no final-looking transaction.  The exact owned inode is moved to the next
  // collision-safe quarantine name, while incumbent quarantine names remain.
  const std::string fsyncStage = directory + "/fsync-bundle.partial";
  const std::string fsyncFinal = directory + "/fsync-bundle.final";
  const std::string failed0 = fsyncFinal + ".failed";
  const std::string failedPid = failed0 + "." + std::to_string(static_cast<long>(::getpid()));
  const std::string failedNext = failedPid + ".1";
  if (::mkdir(fsyncStage.c_str(), 0700) != 0 || ::mkdir(failed0.c_str(), 0700) != 0 ||
      ::mkdir(failedPid.c_str(), 0700) != 0) return 13;
  {
    std::ofstream marker((fsyncStage + "/owned-marker").c_str(), std::ios::binary);
    marker << "owned\n";
  }
  {
    std::ofstream marker((failed0 + "/foreign-marker").c_str(), std::ios::binary);
    marker << "foreign-zero\n";
  }
  {
    std::ofstream marker((failedPid + "/foreign-marker").c_str(), std::ios::binary);
    marker << "foreign-pid\n";
  }
  M05DurableFile::FailNextDirectoryFsyncForTest();
  bool postRenameFsyncRejected = false;
  try { M05DurableFile::PublishDirectoryDurableNoReplace(fsyncStage, fsyncFinal); }
  catch (const std::runtime_error&) { postRenameFsyncRejected = true; }
  if (!postRenameFsyncRejected || Exists(fsyncStage) || Exists(fsyncFinal) || !Exists(failedNext) ||
      !Exists(failedNext + "/owned-marker")) return 14;
  std::ifstream foreign0((failed0 + "/foreign-marker").c_str(), std::ios::binary);
  std::ifstream foreignPid((failedPid + "/foreign-marker").c_str(), std::ios::binary);
  std::string foreign0Bytes;
  std::string foreignPidBytes;
  std::getline(foreign0, foreign0Bytes);
  std::getline(foreignPid, foreignPidBytes);
  if (foreign0Bytes != "foreign-zero" || foreignPidBytes != "foreign-pid") return 15;

  // A path swap after exclusive open must be detected: durability and digest
  // remain attached to the opened inode, while publication refuses the new
  // lexical occupant. Both objects remain quarantined for audit.
  const std::string swappedPartial = directory + "/swapped.partial";
  const std::string displacedPartial = directory + "/swapped.displaced";
  const std::string swappedFinal = directory + "/swapped.final";
  M05DurableFile swapped;
  swapped.OpenExclusive(swappedPartial);
  swapped << "opened-inode\n";
  if (::rename(swappedPartial.c_str(), displacedPartial.c_str()) != 0) return 11;
  {
    std::ofstream replacement(swappedPartial.c_str(), std::ios::binary);
    replacement << "replacement\n";
  }
  bool pathSwapRejected = false;
  try { swapped.CloseDurable(); }
  catch (const std::runtime_error&) { pathSwapRejected = true; }
  if (!pathSwapRejected || Exists(swappedFinal) || !Exists(swappedPartial) || !Exists(displacedPartial)) return 12;

  // Destruction can leave quarantined evidence but must never create a final marker.
  const std::string interruptedPartial = directory + "/interrupted.partial";
  const std::string interruptedFinal = directory + "/interrupted.final";
  {
    M05DurableFile interrupted;
    interrupted.OpenExclusive(interruptedPartial);
    interrupted << "uncommitted\n";
  }
  if (!Exists(interruptedPartial) || Exists(interruptedFinal)) return 4;
  std::cout << "PASS durable_file_nontransport\n";
  return 0;
}
