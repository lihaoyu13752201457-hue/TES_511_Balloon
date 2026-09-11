#ifndef __M05DurableFile__
#define __M05DurableFile__

#include <cstddef>
#include <ext/stdio_filebuf.h>
#include <iomanip>
#include <ostream>
#include <string>

struct M05DurableMetadata
{
  std::string path;
  std::string sha256;
  unsigned long long sizeBytes = 0;
  unsigned long long rowCount = 0;
};

// Linux/POSIX write-once file used by the isolated smoke only. Creation is
// O_EXCL|O_NOFOLLOW and the same owned descriptor remains attached to the
// stream through flush, fstat, descriptor hashing, and fsync. The path/inode
// identity is rechecked immediately before a no-replace publish.
class M05DurableFile
{
public:
  M05DurableFile();
  ~M05DurableFile();
  M05DurableFile(const M05DurableFile&) = delete;
  M05DurableFile& operator=(const M05DurableFile&) = delete;

  void OpenExclusive(const std::string& partialPath);
  std::ostream& Stream();
  template <typename T> M05DurableFile& operator<<(const T& value)
  {
    Stream() << value;
    return *this;
  }
  M05DurableFile& operator<<(std::ostream& (*manipulator)(std::ostream&))
  {
    manipulator(Stream());
    return *this;
  }
  void write(const char* data, std::streamsize size) { Stream().write(data, size); }
  std::streamoff tellp() { return Stream().tellp(); }
  bool good() const { return m_Stream.good(); }
  void AddRows(unsigned long long count = 1) { m_RowCount += count; }
  M05DurableMetadata CloseDurable();
  void Publish(const std::string& finalPath);
  void VerifyClosedIdentity() const;
  bool IsOpen() const { return m_Buffer.is_open(); }
  const std::string& PartialPath() const { return m_PartialPath; }

  static void RejectExisting(const std::string& path);
  static void PublishPathNoReplace(const std::string& partialPath, const std::string& finalPath);
  static void FsyncDirectory(const std::string& directory);
  static M05DurableMetadata WriteExclusiveDurable(const std::string& partialPath,
                                                  const std::string& data);
  static std::string SHA256File(const std::string& path);

private:
  static void Require(bool condition, const std::string& message);
  static std::string SHA256Descriptor(int descriptor);
  void RequirePathStillNamesOpenedInode() const;

  std::string m_PartialPath;
  __gnu_cxx::stdio_filebuf<char> m_Buffer;
  std::ostream m_Stream;
  unsigned long long m_Device;
  unsigned long long m_Inode;
  unsigned long long m_ClosedSizeBytes;
  std::string m_ClosedSHA256;
  unsigned long long m_RowCount;
  bool m_ClosedDurable;
};

#endif
