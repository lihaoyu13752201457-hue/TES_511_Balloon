#ifndef __M05ObserverTransaction__
#define __M05ObserverTransaction__

#include "../shadow_extensions/M05NoReplace.hh"

#include <cerrno>
#include <sstream>
#include <string>

#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

enum class M05ObserverPublishResult
{
  Published,
  InvalidPartial,
  InitialRenameFailed,
  PublishedIdentityLost,
  QuarantineRenameFailed,
  QuarantineNamesExhausted,
  PostRenameFsyncFailedQuarantined,
  PostRenameFsyncFailedQuarantineUndurable
};

inline const char* M05ObserverPublishResultName(M05ObserverPublishResult result)
{
  switch (result) {
  case M05ObserverPublishResult::Published: return "Published";
  case M05ObserverPublishResult::InvalidPartial: return "InvalidPartial";
  case M05ObserverPublishResult::InitialRenameFailed: return "InitialRenameFailed";
  case M05ObserverPublishResult::PublishedIdentityLost: return "PublishedIdentityLost";
  case M05ObserverPublishResult::QuarantineRenameFailed: return "QuarantineRenameFailed";
  case M05ObserverPublishResult::QuarantineNamesExhausted: return "QuarantineNamesExhausted";
  case M05ObserverPublishResult::PostRenameFsyncFailedQuarantined:
    return "PostRenameFsyncFailedQuarantined";
  case M05ObserverPublishResult::PostRenameFsyncFailedQuarantineUndurable:
    return "PostRenameFsyncFailedQuarantineUndurable";
  }
  return "Unknown";
}

inline std::string M05ObserverParent(const std::string& path)
{
  const std::string::size_type slash = path.find_last_of('/');
  if (slash == std::string::npos) return ".";
  if (slash == 0) return "/";
  return path.substr(0, slash);
}

// No exceptions and no ordinary rename fallback: this helper is safe to call
// from an atexit finalizer.  It snapshots the owned stage inode before the
// no-replace publish.  If the subsequent parent fsync fails, only that exact
// inode may be moved to a collision-safe *.failed* namespace.  A foreign
// incumbent or a path whose identity changed is never touched.
template <typename DirectorySync>
M05ObserverPublishResult M05ObserverPublishDirectoryNoReplaceDurable(
    const std::string& partialPath,
    const std::string& finalPath,
    DirectorySync syncDirectory,
    std::string* quarantinePath)
{
  if (quarantinePath != nullptr) quarantinePath->clear();
  if (M05ObserverParent(partialPath) != M05ObserverParent(finalPath)) {
    return M05ObserverPublishResult::InvalidPartial;
  }
  struct stat ownedIdentity;
  if (::lstat(partialPath.c_str(), &ownedIdentity) != 0 || !S_ISDIR(ownedIdentity.st_mode) ||
      S_ISLNK(ownedIdentity.st_mode)) {
    return M05ObserverPublishResult::InvalidPartial;
  }
  if (M05RenameNoReplace(partialPath.c_str(), finalPath.c_str()) != 0) {
    return M05ObserverPublishResult::InitialRenameFailed;
  }
  if (syncDirectory(M05ObserverParent(finalPath))) return M05ObserverPublishResult::Published;

  struct stat publishedIdentity;
  if (::lstat(finalPath.c_str(), &publishedIdentity) != 0 || !S_ISDIR(publishedIdentity.st_mode) ||
      S_ISLNK(publishedIdentity.st_mode) || publishedIdentity.st_dev != ownedIdentity.st_dev ||
      publishedIdentity.st_ino != ownedIdentity.st_ino) {
    return M05ObserverPublishResult::PublishedIdentityLost;
  }

  std::string quarantined;
  for (unsigned int attempt = 0; attempt < 10000; ++attempt) {
    std::ostringstream candidate;
    candidate << finalPath << ".failed";
    if (attempt >= 1) candidate << '.' << static_cast<long>(::getpid());
    if (attempt >= 2) candidate << '.' << (attempt - 1);
    errno = 0;
    if (M05RenameNoReplace(finalPath.c_str(), candidate.str().c_str()) == 0) {
      quarantined = candidate.str();
      break;
    }
    if (errno != EEXIST) return M05ObserverPublishResult::QuarantineRenameFailed;
  }
  if (quarantined.empty()) return M05ObserverPublishResult::QuarantineNamesExhausted;
  if (quarantinePath != nullptr) *quarantinePath = quarantined;
  if (!syncDirectory(M05ObserverParent(finalPath))) {
    return M05ObserverPublishResult::PostRenameFsyncFailedQuarantineUndurable;
  }
  return M05ObserverPublishResult::PostRenameFsyncFailedQuarantined;
}

#endif
