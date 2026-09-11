#include "MGlobal.h"
#include "MGeometryRevan.h"
#include "MDMaterial.h"
#include "MDVolume.h"
#include "MDVolumeSequence.h"
#include "MVector.h"

#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

int main(int argc, char** argv)
{
  if (argc != 2) {
    std::cerr << "usage: query_megalib_geometry GEOMETRY.setup\n";
    return 2;
  }

  MGlobal::Initialize("query_megalib_geometry", "Read-only point membership query");
  MGeometryRevan geometry;
  if (geometry.ScanSetupFile(argv[1], false, false, false) == false) {
    std::cerr << "geometry scan failed: " << argv[1] << "\n";
    return 3;
  }

  std::cout << "query_id,x_cm,y_cm,z_cm,deepest_volume,material,volume_sequence\n";
  std::string line;
  while (std::getline(std::cin, line)) {
    if (line.empty() || line[0] == '#') continue;
    std::istringstream input(line);
    std::string query_id;
    double x = 0.0;
    double y = 0.0;
    double z = 0.0;
    if (!(input >> query_id >> x >> y >> z)) {
      std::cerr << "bad query line: " << line << "\n";
      return 4;
    }

    MDVolumeSequence sequence = geometry.GetVolumeSequence(MVector(x, y, z));
    MDVolume* deepest = sequence.GetDeepestVolume();
    std::string deepest_name = deepest == nullptr ? "" : deepest->GetName().Data();
    std::string material_name;
    if (deepest != nullptr && deepest->GetMaterial() != nullptr) {
      material_name = deepest->GetMaterial()->GetName().Data();
    }

    std::ostringstream names;
    for (unsigned int i = 0; i < sequence.GetNVolumes(); ++i) {
      if (i != 0) names << ">";
      names << sequence.GetVolumeAt(i)->GetName().Data();
    }
    std::cout << query_id << ',' << std::setprecision(10) << x << ',' << y << ',' << z
              << ',' << deepest_name << ',' << material_name << ',' << names.str() << '\n';
  }
  return 0;
}
