#include "MGlobal.h"
#include "MGeometryRevan.h"

#include <iostream>
#include <sstream>

int main(int argc, char** argv)
{
  if (argc != 2) {
    std::cerr << "usage: check_geometry_overlaps GEOMETRY.setup\n";
    return 2;
  }
  MGlobal::Initialize("check_geometry_overlaps", "Read-only ROOT overlap query");
  MGeometryRevan geometry;
  if (geometry.ScanSetupFile(argv[1], false, false, false) == false) {
    std::cerr << "geometry scan failed: " << argv[1] << "\n";
    return 3;
  }
  std::ostringstream diagnostics;
  const bool ok = geometry.CheckOverlaps(diagnostics);
  std::cout << "overlap_ok=" << (ok ? 1 : 0) << "\n" << diagnostics.str();
  return ok ? 0 : 1;
}
