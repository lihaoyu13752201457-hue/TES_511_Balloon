#ifndef __M05DurableFile__
#define __M05DurableFile__

#include <cstddef>
#include <fstream>
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
// O_EXCL|O_NOFOLLOW; CloseDurable reopens the same lexical path without
// following a symlink, verifies a regular single-link file, hashes it, and
// fsyncs it before any rename.
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
  bool IsOpen() const { return m_Stream.is_open(); }
  const std::string& PartialPath() const { return m_PartialPath; }

  static void RejectExisting(const std::string& path);
  static void FsyncDirectory(const std::string& directory);
  static M05DurableMetadata WriteExclusiveDurable(const std::string& partialPath,
                                                  const std::string& data);
  static std::string SHA256File(const std::string& path);

private:
  static void Require(bool condition, const std::string& message);

  std::string m_PartialPath;
  std::ofstream m_Stream;
  unsigned long long m_RowCount;
  bool m_ClosedDurable;
};

#endif
