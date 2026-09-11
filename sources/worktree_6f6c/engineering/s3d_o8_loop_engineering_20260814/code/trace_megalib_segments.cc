#include "MGlobal.h"
#include "MGeometryRevan.h"
#include "MDMaterial.h"
#include "MDVolume.h"
#include "MDVolumeSequence.h"
#include "MVector.h"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

namespace {

struct Membership
{
  std::string volume;
  std::string material;
};

Membership Locate(MGeometryRevan& geometry, double x, double y, double z)
{
  MDVolumeSequence sequence = geometry.GetVolumeSequence(MVector(x, y, z));
  MDVolume* deepest = sequence.GetDeepestVolume();
  if (deepest == nullptr) return {"", ""};
  std::string material;
  if (deepest->GetMaterial() != nullptr) material = deepest->GetMaterial()->GetName().Data();
  return {deepest->GetName().Data(), material};
}

void Emit(const std::string& id, const Membership& membership,
          double s0, double s1, double length,
          double x0, double y0, double z0,
          double dx, double dy, double dz)
{
  const double u0 = length > 0.0 ? s0 / length : 0.0;
  const double u1 = length > 0.0 ? s1 / length : 0.0;
  std::cout << id << ',' << membership.volume << ',' << membership.material << ','
            << std::setprecision(10) << s0 << ',' << s1 << ',' << (s1 - s0) << ','
            << (x0 + u0 * dx) << ',' << (y0 + u0 * dy) << ',' << (z0 + u0 * dz) << ','
            << (x0 + u1 * dx) << ',' << (y0 + u1 * dy) << ',' << (z0 + u1 * dz) << '\n';
}

}  // namespace

int main(int argc, char** argv)
{
  if (argc != 2) {
    std::cerr << "usage: trace_megalib_segments GEOMETRY.setup\n";
    return 2;
  }
  MGlobal::Initialize("trace_megalib_segments", "Read-only sampled geometry chords");
  MGeometryRevan geometry;
  if (geometry.ScanSetupFile(argv[1], false, false, false) == false) {
    std::cerr << "geometry scan failed: " << argv[1] << "\n";
    return 3;
  }

  std::cout << "ray_id,volume,material,s0_cm,s1_cm,length_cm,x0_cm,y0_cm,z0_cm,x1_cm,y1_cm,z1_cm\n";
  std::string line;
  while (std::getline(std::cin, line)) {
    if (line.empty() || line[0] == '#') continue;
    std::istringstream input(line);
    std::string id;
    double x0 = 0.0, y0 = 0.0, z0 = 0.0, x1 = 0.0, y1 = 0.0, z1 = 0.0, step = 0.0;
    if (!(input >> id >> x0 >> y0 >> z0 >> x1 >> y1 >> z1 >> step) || step <= 0.0) {
      std::cerr << "bad ray line: " << line << "\n";
      return 4;
    }
    const double dx = x1 - x0;
    const double dy = y1 - y0;
    const double dz = z1 - z0;
    const double length = std::sqrt(dx * dx + dy * dy + dz * dz);
    const unsigned long bins = std::max<unsigned long>(1, static_cast<unsigned long>(std::ceil(length / step)));
    const double ds = length / static_cast<double>(bins);

    Membership current;
    double run_start = 0.0;
    for (unsigned long i = 0; i < bins; ++i) {
      const double u = (static_cast<double>(i) + 0.5) / static_cast<double>(bins);
      const Membership found = Locate(geometry, x0 + u * dx, y0 + u * dy, z0 + u * dz);
      if (i == 0) {
        current = found;
        run_start = 0.0;
      } else if (found.volume != current.volume || found.material != current.material) {
        Emit(id, current, run_start, static_cast<double>(i) * ds, length,
             x0, y0, z0, dx, dy, dz);
        current = found;
        run_start = static_cast<double>(i) * ds;
      }
    }
    Emit(id, current, run_start, length, length, x0, y0, z0, dx, dy, dz);
  }
  return 0;
}
