#ifndef OPTICS_LAUE_EFFICIENCY_TABLE_HH
#define OPTICS_LAUE_EFFICIENCY_TABLE_HH

#include <string>
#include <vector>

namespace optics {

struct LaueEfficiencyRow {
  double energyKeV;
  double thetaBRad;
  double deltaThetaRad;
  std::string material;
  int h;
  int k;
  int l;
  double mosaicFwhmArcmin;
  double thicknessMm;
  double pDiff;
  double pAbs;
  double pTrans;
  std::string source;
};

class LaueEfficiencyTable {
 public:
  LaueEfficiencyTable() = default;

  static LaueEfficiencyTable FromCsv(const std::string& path);

  bool empty() const;
  const std::vector<LaueEfficiencyRow>& rows() const;
  LaueEfficiencyRow Lookup(
      double energyKeV,
      double deltaThetaRad,
      const std::string& material,
      int h,
      int k,
      int l) const;

 private:
  std::vector<LaueEfficiencyRow> rows_;
};

}  // namespace optics

#endif
