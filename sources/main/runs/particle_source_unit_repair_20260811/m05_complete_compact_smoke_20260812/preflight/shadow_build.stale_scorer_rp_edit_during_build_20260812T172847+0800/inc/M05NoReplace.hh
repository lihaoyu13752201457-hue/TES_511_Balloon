#ifndef __M05NoReplace__
#define __M05NoReplace__

#include <cerrno>

#include <fcntl.h>
#include <linux/fs.h>
#include <sys/syscall.h>
#include <unistd.h>

// Linux-only atomic write-once publication primitive. There is deliberately
// no ordinary-rename fallback: an unavailable kernel primitive is a hard
// publication failure, never permission to overwrite an incumbent artifact.
inline int M05RenameNoReplace(const char* partialPath, const char* finalPath)
{
#ifdef SYS_renameat2
  return static_cast<int>(::syscall(SYS_renameat2, AT_FDCWD, partialPath,
                                    AT_FDCWD, finalPath, RENAME_NOREPLACE));
#else
  (void) partialPath;
  (void) finalPath;
  errno = ENOSYS;
  return -1;
#endif
}

#endif
