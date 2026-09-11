#include "M05DurableFile.hh"
#include "M05NoReplace.hh"

#include <openssl/sha.h>

#include <cerrno>
#include <cstring>
#include <iomanip>
#include <sstream>
#include <stdexcept>

#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

namespace {

std::string ErrnoMessage(const std::string& prefix)
{
  return prefix + ": " + std::strerror(errno);
}

}

M05DurableFile::M05DurableFile() : m_RowCount(0), m_ClosedDurable(false) {}

M05DurableFile::~M05DurableFile()
{
  // Never publish from a destructor. An interrupted process intentionally
  // leaves the exclusively created .partial as quarantined evidence.
  if (m_Stream.is_open()) m_Stream.close();
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
  Require(!m_Stream.is_open() && m_PartialPath.empty(), "file opened twice");
  const int descriptor = ::open(partialPath.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0660);
  if (descriptor < 0) throw std::runtime_error(ErrnoMessage("exclusive partial creation failed: " + partialPath));
  std::ostringstream procPath;
  procPath << "/proc/self/fd/" << descriptor;
  m_Stream.open(procPath.str(), std::ios::out | std::ios::app | std::ios::binary);
  const int closeResult = ::close(descriptor);
  Require(m_Stream.good() && closeResult == 0, "cannot attach stream to exclusive partial: " + partialPath);
  m_PartialPath = partialPath;
}

std::ostream& M05DurableFile::Stream()
{
  Require(m_Stream.is_open() && !m_ClosedDurable, "write requested outside open partial");
  return m_Stream;
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
  Require(m_Stream.is_open() && !m_ClosedDurable, "durable close requested twice/outside open file");
  m_Stream.flush();
  Require(m_Stream.good(), "flush failed: " + m_PartialPath);
  m_Stream.close();
  Require(!m_Stream.fail(), "close failed: " + m_PartialPath);

  const int descriptor = ::open(m_PartialPath.c_str(), O_RDWR | O_NOFOLLOW);
  if (descriptor < 0) throw std::runtime_error(ErrnoMessage("cannot reopen durable partial: " + m_PartialPath));
  struct stat state;
  const int statResult = ::fstat(descriptor, &state);
  if (statResult != 0 || !S_ISREG(state.st_mode) || state.st_nlink != 1) {
    ::close(descriptor);
    throw std::runtime_error("durable partial is not a single-link regular file: " + m_PartialPath);
  }
  if (::fsync(descriptor) != 0) {
    const std::string message = ErrnoMessage("fsync failed: " + m_PartialPath);
    ::close(descriptor);
    throw std::runtime_error(message);
  }
  Require(::close(descriptor) == 0, "descriptor close failed: " + m_PartialPath);

  M05DurableMetadata result;
  result.path = m_PartialPath;
  result.sizeBytes = static_cast<unsigned long long>(state.st_size);
  result.rowCount = m_RowCount;
  result.sha256 = SHA256File(m_PartialPath);
  m_ClosedDurable = true;
  return result;
}

void M05DurableFile::Publish(const std::string& finalPath)
{
  Require(m_ClosedDurable && !m_PartialPath.empty(), "publish before durable close");
  PublishPathNoReplace(m_PartialPath, finalPath);
}

void M05DurableFile::PublishPathNoReplace(const std::string& partialPath, const std::string& finalPath)
{
  if (M05RenameNoReplace(partialPath.c_str(), finalPath.c_str()) != 0) {
    throw std::runtime_error(ErrnoMessage("atomic no-replace rename failed: " + partialPath));
  }
}

void M05DurableFile::FsyncDirectory(const std::string& directory)
{
  const int descriptor = ::open(directory.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW);
  if (descriptor < 0) throw std::runtime_error(ErrnoMessage("cannot open parent directory for fsync: " + directory));
  if (::fsync(descriptor) != 0) {
    const std::string message = ErrnoMessage("parent-directory fsync failed: " + directory);
    ::close(descriptor);
    throw std::runtime_error(message);
  }
  Require(::close(descriptor) == 0, "parent-directory descriptor close failed");
}

M05DurableMetadata M05DurableFile::WriteExclusiveDurable(const std::string& partialPath,
                                                         const std::string& data)
{
  M05DurableFile file;
  file.OpenExclusive(partialPath);
  file.Stream().write(data.data(), static_cast<std::streamsize>(data.size()));
  Require(file.Stream().good(), "manifest write failed: " + partialPath);
  return file.CloseDurable();
}
