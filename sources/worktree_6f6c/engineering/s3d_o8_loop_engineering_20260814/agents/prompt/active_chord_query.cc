#include "MGlobal.h"
#include "MDGeometry.h"
#include "MDMaterial.h"
#include "MDVolume.h"
#include "MVector.h"

#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

namespace {

MVector world_to_instrument(const MVector& p)
{
  const double c = std::sqrt(0.5);
  return MVector(c*(p.X()-p.Z()), p.Y(), c*(p.X()+p.Z()));
}

}  // namespace

int main(int argc, char** argv)
{
  if (argc != 2) {
    std::cerr << "usage: active_chord_query GEOMETRY.setup\n"
              << "stdin: id x y z dx dy dz [tmax_cm]\n";
    return 2;
  }
  MGlobal::Initialize("active_chord_query", "Exact active-volume chord query");
  MDGeometry geometry;
  if (geometry.ScanSetupFile(argv[1], false, false, false) == false) return 3;
  const std::vector<std::string> bgo_names = {
    "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
    "BGO_S3D_O8_FullWrap_BottomCap_30mm",
    "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
  };
  const std::vector<std::string> plastic_names = {
    "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
  };
  std::vector<MDVolume*> bgo, plastic;
  for (const auto& name : bgo_names) {
    MDVolume* v = geometry.GetVolume(name.c_str());
    if (v == nullptr) { std::cerr << "missing " << name << '\n'; return 4; }
    bgo.push_back(v);
  }
  for (const auto& name : plastic_names) {
    MDVolume* v = geometry.GetVolume(name.c_str());
    if (v == nullptr) { std::cerr << "missing " << name << '\n'; return 4; }
    plastic.push_back(v);
  }

  std::cout << "id,bgo_chord_cm,plastic_chord_cm,active_grammage_g_cm2\n";
  std::string line;
  while (std::getline(std::cin, line)) {
    if (line.empty() || line[0] == '#') continue;
    std::istringstream in(line);
    std::string id;
    double x, y, z, dx, dy, dz, tmax = 200.0;
    if (!(in >> id >> x >> y >> z >> dx >> dy >> dz)) return 5;
    in >> tmax;
    const double norm = std::sqrt(dx*dx+dy*dy+dz*dz);
    dx /= norm; dy /= norm; dz /= norm;
    MVector start = world_to_instrument(MVector(x, y, z));
    MVector stop = world_to_instrument(MVector(x+tmax*dx, y+tmax*dy, z+tmax*dz));
    double lbgo = 0.0, lplastic = 0.0;
    for (MDVolume* v : bgo) {
      std::map<MDMaterial*, double> lengths;
      lbgo += v->GetAbsorptionLengths(lengths, start, stop);
    }
    for (MDVolume* v : plastic) {
      std::map<MDMaterial*, double> lengths;
      lplastic += v->GetAbsorptionLengths(lengths, start, stop);
    }
    std::cout << id << ',' << std::setprecision(12) << lbgo << ',' << lplastic
              << ',' << (7.1*lbgo + 1.03*lplastic) << '\n';
  }
  return 0;
}
