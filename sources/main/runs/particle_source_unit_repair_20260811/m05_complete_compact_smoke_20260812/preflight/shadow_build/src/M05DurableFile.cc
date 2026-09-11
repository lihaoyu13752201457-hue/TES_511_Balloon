#include "M05DurableFile.hh"
#include "M05NoReplace.hh"

#include <openssl/sha.h>

#include <cerrno>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <stdexcept>

#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

namespace {

#ifdef M05_DURABLE_TEST_HOOKS
bool g_FailNextDirectoryFsyncForTest = false;
#endif

std::string ErrnoMessage(const std::string& prefix)
{
  return prefix + ": " + std::strerror(errno);
}

std::string ParentDirectory(const std::string& path)
{
  const std::string::size_type slash = path.find_last_of('/');
  if (slash == std::string::npos) return ".";
  if (slash == 0) return "/";
  return path.substr(0, slash);
}

bool SameIdentity(const struct stat& left, const struct stat& right)
{
  return left.st_dev == right.st_dev && left.st_ino == right.st_ino;
}

}

M05DurableFile::M05DurableFile() : m_Stream(&m_Buffer), m_Device(0), m_Inode(0), m_ClosedSizeBytes(0),
  m_RowCount(0), m_ClosedDurable(false) {}

M05DurableFile::~M05DurableFile()
{
  // Never publish from a destructor. An interrupted process intentionally
  // leaves the exclusively created .partial as quarantined evidence.
  if (m_Buffer.is_open()) m_Buffer.close();
}

void M05DurableFile::Require(bool condition, const std::string& message)
{
  if (!condition) throw std::runtime_error("M05DurableFile fail-closed: " + message);
}

void M05DurableFile::RejectExisting(const std::string& path)
{
  struct stat state;
  errno = 0;
  const int result = ::lstat(path.c_str(), &state);
  Require(result != 0 && errno == ENOENT, "target already exists or cannot be inspected: " + path);
}

void M05DurableFile::OpenExclusive(const std::string& partialPath)
{
  Require(!m_Buffer.is_open() && m_PartialPath.empty(), "file opened twice");
  const int descriptor = ::open(partialPath.c_str(), O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW, 0660);
  if (descriptor < 0) throw std::runtime_error(ErrnoMessage("exclusive partial creation failed: " + partialPath));
  struct stat state;
  if (::fstat(descriptor, &state) != 0 || !S_ISREG(state.st_mode) || state.st_nlink != 1) {
    ::close(descriptor);
    throw std::runtime_error("exclusive partial is not a single-link regular file: " + partialPath);
  }
  m_Buffer = __gnu_cxx::stdio_filebuf<char>(descriptor, std::ios::out | std::ios::binary);
  Require(m_Buffer.is_open() && m_Stream.good(), "cannot attach stream to exclusive partial: " + partialPath);
  m_Device = static_cast<unsigned long long>(state.st_dev);
  m_Inode = static_cast<unsigned long long>(state.st_ino);
  m_PartialPath = partialPath;
}

std::ostream& M05DurableFile::Stream()
{
  Require(m_Buffer.is_open() && !m_ClosedDurable, "write requested outside open partial");
  return m_Stream;
}

void M05DurableFile::RequirePathStillNamesOpenedInode() const
{
  struct stat pathState;
  Require(::lstat(m_PartialPath.c_str(), &pathState) == 0 && S_ISREG(pathState.st_mode) &&
          !S_ISLNK(pathState.st_mode) && pathState.st_nlink == 1,
          "partial path is not a single-link regular file: " + m_PartialPath);
  Require(static_cast<unsigned long long>(pathState.st_dev) == m_Device &&
          static_cast<unsigned long long>(pathState.st_ino) == m_Inode,
          "partial path/inode identity changed: " + m_PartialPath);
}

std::string M05DurableFile::SHA256Descriptor(int descriptor)
{
  Require(descriptor >= 0, "invalid descriptor hash request");
  SHA256_CTX context;
  SHA256_Init(&context);
  char buffer[1024*1024];
  off_t offset = 0;
  while (true) {
    const ssize_t count = ::pread(descriptor, buffer, sizeof(buffer), offset);
    if (count < 0) throw std::runtime_error(ErrnoMessage("descriptor hash read failed"));
    if (count == 0) break;
    SHA256_Update(&context, reinterpret_cast<unsigned char*>(buffer), static_cast<std::size_t>(count));
    offset += count;
  }
  unsigned char digest[SHA256_DIGEST_LENGTH];
  SHA256_Final(digest, &context);
  std::ostringstream out;
  out << std::hex << std::setfill('0');
  for (unsigned char byte : digest) out << std::setw(2) << static_cast<unsigned int>(byte);
  return out.str();
}

std::string M05DurableFile::SHA256File(const std::string& path)
{
  std::ifstream input(path, std::ios::binary);
  Require(input.good(), "cannot hash file: " + path);
  SHA256_CTX context;
  SHA256_Init(&context);
  char buffer[1024*1024];
  while (input.good()) {
    input.read(buffer, sizeof(buffer));
    const std::streamsize count = input.gcount();
    if (count > 0) SHA256_Update(&context, reinterpret_cast<unsigned char*>(buffer), static_cast<std::size_t>(count));
  }
  Require(input.eof(), "read failure while hashing: " + path);
  unsigned char digest[SHA256_DIGEST_LENGTH];
  SHA256_Final(digest, &context);
  std::ostringstream out;
  out << std::hex << std::setfill('0');
  for (unsigned char byte : digest) out << std::setw(2) << static_cast<unsigned int>(byte);
  return out.str();
}

M05DurableMetadata M05DurableFile::CloseDurable()
{
  Require(m_Buffer.is_open() && !m_ClosedDurable, "durable close requested twice/outside open file");
  m_Stream.flush();
  Require(m_Stream.good(), "flush failed: " + m_PartialPath);
  const int descriptor = m_Buffer.fd();
  Require(descriptor >= 0, "stream descriptor is unavailable: " + m_PartialPath);
  struct stat state;
  Require(::fstat(descriptor, &state) == 0 && S_ISREG(state.st_mode) && state.st_nlink == 1,
          "durable descriptor is not a single-link regular file: " + m_PartialPath);
  Require(static_cast<unsigned long long>(state.st_dev) == m_Device &&
          static_cast<unsigned long long>(state.st_ino) == m_Inode,
          "durable descriptor identity changed: " + m_PartialPath);
  RequirePathStillNamesOpenedInode();
  const std::string descriptorDigest = SHA256Descriptor(descriptor);
  if (::fsync(descriptor) != 0) throw std::runtime_error(ErrnoMessage("fsync failed: " + m_PartialPath));
  Require(m_Buffer.close() != nullptr, "stream descriptor close failed: " + m_PartialPath);

  M05DurableMetadata result;
  result.path = m_PartialPath;
  result.sizeBytes = static_cast<unsigned long long>(state.st_size);
  result.rowCount = m_RowCount;
  result.sha256 = descriptorDigest;
  m_ClosedSizeBytes = result.sizeBytes;
  m_ClosedSHA256 = result.sha256;
  m_ClosedDurable = true;
  return result;
}

void M05DurableFile::VerifyClosedIdentity() const
{
  Require(m_ClosedDurable && !m_Buffer.is_open(), "closed identity requested before durable close");
  RequirePathStillNamesOpenedInode();
  struct stat state;
  Require(::lstat(m_PartialPath.c_str(), &state) == 0 &&
          static_cast<unsigned long long>(state.st_size) == m_ClosedSizeBytes,
          "closed durable size changed before commit: " + m_PartialPath);
  Require(SHA256File(m_PartialPath) == m_ClosedSHA256,
          "closed durable digest changed before commit: " + m_PartialPath);
}

void M05DurableFile::Publish(const std::string& finalPath)
{
  Require(m_ClosedDurable && !m_PartialPath.empty(), "publish before durable close");
  VerifyClosedIdentity();
  PublishPathNoReplace(m_PartialPath, finalPath);
}

void M05DurableFile::PublishPathNoReplace(const std::string& partialPath, const std::string& finalPath)
{
  if (M05RenameNoReplace(partialPath.c_str(), finalPath.c_str()) != 0) {
    throw std::runtime_error(ErrnoMessage("atomic no-replace rename failed: " + partialPath));
  }
}

void M05DurableFile::PublishDirectoryDurableNoReplace(const std::string& partialPath,
                                                      const std::string& finalPath)
{
  Require(ParentDirectory(partialPath) == ParentDirectory(finalPath),
          "transaction directory publish must remain in one parent");
  struct stat ownedIdentity;
  Require(::lstat(partialPath.c_str(), &ownedIdentity) == 0 && S_ISDIR(ownedIdentity.st_mode) &&
          !S_ISLNK(ownedIdentity.st_mode),
          "transaction partial is not an owned directory: " + partialPath);

  PublishPathNoReplace(partialPath, finalPath);
  try {
    FsyncDirectory(ParentDirectory(finalPath));
    return;
  } catch (const std::exception& fsyncError) {
    const std::string originalFailure = fsyncError.what();
    struct stat publishedIdentity;
    Require(::lstat(finalPath.c_str(), &publishedIdentity) == 0 && S_ISDIR(publishedIdentity.st_mode) &&
            !S_ISLNK(publishedIdentity.st_mode) && SameIdentity(ownedIdentity, publishedIdentity),
            originalFailure + "; published path no longer names the owned directory; foreign namespace untouched");

    std::string quarantinePath;
    for (unsigned int attempt = 0; attempt < 10000; ++attempt) {
      std::ostringstream candidate;
      candidate << finalPath << ".failed";
      if (attempt >= 1) candidate << '.' << static_cast<long>(::getpid());
      if (attempt >= 2) candidate << '.' << (attempt - 1);
      errno = 0;
      if (M05RenameNoReplace(finalPath.c_str(), candidate.str().c_str()) == 0) {
        quarantinePath = candidate.str();
        break;
      }
      if (errno != EEXIST) {
        throw std::runtime_error(originalFailure + "; failed to quarantine owned published directory: " +
                                 std::strerror(errno));
      }
    }
    Require(!quarantinePath.empty(),
            originalFailure + "; exhausted collision-safe quarantine names for owned published directory");
    try {
      FsyncDirectory(ParentDirectory(finalPath));
    } catch (const std::exception& quarantineFsyncError) {
      throw std::runtime_error(originalFailure + "; owned published directory moved to " + quarantinePath +
                               " but quarantine parent fsync failed: " + quarantineFsyncError.what());
    }
    throw std::runtime_error(originalFailure + "; owned published directory quarantined as " + quarantinePath);
  }
}

void M05DurableFile::FsyncDirectory(const std::string& directory)
{
#ifdef M05_DURABLE_TEST_HOOKS
  if (g_FailNextDirectoryFsyncForTest) {
    g_FailNextDirectoryFsyncForTest = false;
    errno = EIO;
    throw std::runtime_error(ErrnoMessage("injected parent-directory fsync failure: " + directory));
  }
#endif
  const int descriptor = ::open(directory.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW);
  if (descriptor < 0) throw std::runtime_error(ErrnoMessage("cannot open parent directory for fsync: " + directory));
  if (::fsync(descriptor) != 0) {
    const std::string message = ErrnoMessage("parent-directory fsync failed: " + directory);
    ::close(descriptor);
    throw std::runtime_error(message);
  }
  Require(::close(descriptor) == 0, "parent-directory descriptor close failed");
}

#ifdef M05_DURABLE_TEST_HOOKS
void M05DurableFile::FailNextDirectoryFsyncForTest()
{
  g_FailNextDirectoryFsyncForTest = true;
}
#endif

M05DurableMetadata M05DurableFile::WriteExclusiveDurable(const std::string& partialPath,
                                                         const std::string& data)
{
  M05DurableFile file;
  file.OpenExclusive(partialPath);
  file.Stream().write(data.data(), static_cast<std::streamsize>(data.size()));
  Require(file.Stream().good(), "manifest write failed: " + partialPath);
  return file.CloseDurable();
}
