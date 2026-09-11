#ifndef OPTICS_REFLECTIVITY_TABLE_HH
#define OPTICS_REFLECTIVITY_TABLE_HH

#include <string>
#include <vector>

namespace optics {

enum class ReflectivityLookupMode {
  kNearest,
  kLinear,
};

struct ReflectivityTableRow {
  std::string stackId;
  double energyKeV;
  double thetaRad;
  double R;
  double A;
  double T;
  std::string source;
};

class ReflectivityTable {
 public:
  ReflectivityTable() = default;

  static ReflectivityTable FromCsv(const std::string& path);

  bool empty() const;
  const std::vector<ReflectivityTableRow>& rows() const;
  ReflectivityTableRow Lookup(
      double energyKeV,
      double thetaRad,
      ReflectivityLookupMode mode = ReflectivityLookupMode::kLinear,
      const std::string& stackId = "") const;

 private:
  std::vector<ReflectivityTableRow> rows_;
};

}  // namespace optics

#endif
