#ifndef __M05FrozenInput__
#define __M05FrozenInput__

#include <openssl/sha.h>

#include <cerrno>
#include <cstring>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <string>

#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

struct M05FrozenInput
{
  std::string bytes;
  std::string sha256;
};

// Read, hash, and snapshot one immutable logical authority through a single
// O_NOFOLLOW descriptor. Consumers must parse and publish `bytes`, never
// reopen the source path after validating `sha256`.
inline M05FrozenInput M05ReadFrozenInputOneDescriptor(const std::string& source)
{
  const int descriptor = ::open(source.c_str(), O_RDONLY | O_NOFOLLOW);
  if (descriptor < 0) {
    throw std::runtime_error("cannot open frozen input without following links: " + source +
                             ": " + std::strerror(errno));
  }
  struct stat state;
  if (::fstat(descriptor, &state) != 0 || !S_ISREG(state.st_mode) || state.st_nlink != 1 || state.st_size < 0) {
    ::close(descriptor);
    throw std::runtime_error("frozen input descriptor is not a single-link regular file: " + source);
  }
  M05FrozenInput result;
  result.bytes.reserve(static_cast<std::size_t>(state.st_size));
  SHA256_CTX context;
  SHA256_Init(&context);
  char buffer[1024*1024];
  while (true) {
    const ssize_t count = ::read(descriptor, buffer, sizeof(buffer));
    if (count < 0) {
      const int saved = errno;
      ::close(descriptor);
      throw std::runtime_error("frozen input read failed: " + std::string(std::strerror(saved)));
    }
    if (count == 0) break;
    result.bytes.append(buffer, static_cast<std::size_t>(count));
    SHA256_Update(&context, buffer, static_cast<std::size_t>(count));
  }
  if (::close(descriptor) != 0) throw std::runtime_error("frozen input descriptor close failed");
  unsigned char digest[SHA256_DIGEST_LENGTH];
  SHA256_Final(digest, &context);
  std::ostringstream out;
  out << std::hex << std::setfill('0');
  for (unsigned char byte : digest) out << std::setw(2) << static_cast<unsigned int>(byte);
  result.sha256 = out.str();
  return result;
}

#endif
