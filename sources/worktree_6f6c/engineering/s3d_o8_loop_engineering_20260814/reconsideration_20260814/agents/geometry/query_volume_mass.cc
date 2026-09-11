#include "MGlobal.h"
#include "MGeometryRevan.h"
#include "MDMaterial.h"
#include "MDShape.h"
#include "MDVolume.h"
#include "TRandom.h"
#include "TRandom3.h"

#include <cstdint>
#include <iomanip>
#include <iostream>
#include <string>

namespace {
std::uint32_t StableSeed(const std::string& value)
{
  std::uint32_t hash = 2166136261u;
  for (const unsigned char byte : value) {
    hash ^= byte;
    hash *= 16777619u;
  }
  return hash == 0 ? 1u : hash;
}
}  // namespace

int main(int argc, char** argv)
{
  if (argc < 3) {
    std::cerr << "usage: query_volume_mass GEOMETRY.setup VOLUME [VOLUME ...]\n";
    return 2;
  }

  MGlobal::Initialize("query_volume_mass", "Read-only Geomega CSG volume/mass query");
  MGeometryRevan geometry;
  if (geometry.ScanSetupFile(argv[1], false, false, false) == false) {
    std::cerr << "geometry scan failed: " << argv[1] << "\n";
    return 3;
  }

  std::cout << "volume,material,volume_cm3,density_g_cm3,mass_kg\n";
  std::cout << std::setprecision(15);
  for (int i = 2; i < argc; ++i) {
    const std::string name = argv[i];
    MDVolume* volume = geometry.GetVolume(name.c_str());
    if (volume == nullptr || volume->GetShape() == nullptr || volume->GetMaterial() == nullptr) {
      std::cerr << "missing/incomplete volume: " << name << "\n";
      return 4;
    }
    // ROOT TGeoCompositeShape::Capacity() is Monte Carlo.  Resetting a stable
    // per-volume seed makes the estimate independent of command-line order.
    if (gRandom == nullptr) gRandom = new TRandom3();
    gRandom->SetSeed(StableSeed(name));
    const double volume_cm3 = volume->GetShape()->GetVolume();
    const double density_g_cm3 = volume->GetMaterial()->GetDensity();
    std::cout << name << ',' << volume->GetMaterial()->GetName() << ',' << volume_cm3 << ','
              << density_g_cm3 << ',' << volume_cm3 * density_g_cm3 / 1000.0 << '\n';
  }
  return 0;
}
