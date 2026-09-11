#include "MGlobal.h"
#include "MDGeometry.h"
#include "MDMaterial.h"
#include "MDVolume.h"
#include "MDVolumeSequence.h"
#include "MVector.h"

#include <cmath>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

namespace {

struct State {
  std::string volume;
  std::string material;
  std::string sequence;
};

bool operator==(const State& a, const State& b)
{
  return a.volume == b.volume && a.material == b.material && a.sequence == b.sequence;
}

State state_at(MDGeometry& geometry, double x, double y, double z)
{
  MDVolumeSequence sequence = geometry.GetVolumeSequence(MVector(x, y, z));
  MDVolume* deepest = sequence.GetDeepestVolume();
  State state;
  if (deepest != nullptr) {
    state.volume = deepest->GetName().Data();
    if (deepest->GetMaterial() != nullptr) {
      state.material = deepest->GetMaterial()->GetName().Data();
    }
  }
  std::ostringstream names;
  for (unsigned int i = 0; i < sequence.GetNVolumes(); ++i) {
    if (i != 0) names << ">";
    names << sequence.GetVolumeAt(i)->GetName().Data();
  }
  state.sequence = names.str();
  return state;
}

bool is_active(const std::string& volume)
{
  return volume == "BGO_S3C_FullWrap_SideShell_WindowCut_40mm" ||
         volume == "BGO_S3D_O8_FullWrap_BottomCap_30mm" ||
         volume == "BGO_S3D_O8_FullWrap_TopAnnulus_10mm" ||
         volume == "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm" ||
         volume == "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm" ||
         volume == "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm";
}

void point(double x0, double y0, double z0, double dx, double dy, double dz,
           double t, double& x, double& y, double& z)
{
  x = x0 + t*dx;
  y = y0 + t*dy;
  z = z0 + t*dz;
}

State state_on_ray(MDGeometry& geometry,
                   double x0, double y0, double z0,
                   double dx, double dy, double dz, double t)
{
  double x = 0.0, y = 0.0, z = 0.0;
  point(x0, y0, z0, dx, dy, dz, t, x, y, z);
  return state_at(geometry, x, y, z);
}

void emit(const std::string& ray_id, unsigned int segment_index,
          double x0, double y0, double z0,
          double dx, double dy, double dz,
          double t_entry, double t_exit, const State& state)
{
  double x_entry = 0.0, y_entry = 0.0, z_entry = 0.0;
  double x_exit = 0.0, y_exit = 0.0, z_exit = 0.0;
  point(x0, y0, z0, dx, dy, dz, t_entry, x_entry, y_entry, z_entry);
  point(x0, y0, z0, dx, dy, dz, t_exit, x_exit, y_exit, z_exit);
  std::cout << ray_id << ',' << segment_index << ','
            << std::setprecision(12) << t_entry << ',' << t_exit << ','
            << (t_exit-t_entry) << ','
            << x_entry << ',' << y_entry << ',' << z_entry << ','
            << x_exit << ',' << y_exit << ',' << z_exit << ','
            << state.volume << ',' << state.material << ','
            << (is_active(state.volume) ? "true" : "false") << ','
            << state.sequence << '\n';
}

}  // namespace

int main(int argc, char** argv)
{
  if (argc != 2) {
    std::cerr << "usage: trace_true_geometry_rays GEOMETRY.setup\n"
              << "stdin: ray_id x0 y0 z0 dx dy dz t_max step_cm\n";
    return 2;
  }

  MGlobal::Initialize("trace_true_geometry_rays", "Read-only exact-geometry ray membership trace");
  MDGeometry geometry;
  if (geometry.ScanSetupFile(argv[1], false, false, false) == false) {
    std::cerr << "geometry scan failed: " << argv[1] << '\n';
    return 3;
  }

  std::cout << "ray_id,segment_index,t_entry_cm,t_exit_cm,path_cm,"
               "entry_x_cm,entry_y_cm,entry_z_cm,exit_x_cm,exit_y_cm,exit_z_cm,"
               "deepest_volume,material,is_active,volume_sequence\n";

  std::string line;
  while (std::getline(std::cin, line)) {
    if (line.empty() || line[0] == '#') continue;
    std::istringstream input(line);
    std::string ray_id;
    double x0 = 0.0, y0 = 0.0, z0 = 0.0;
    double dx = 0.0, dy = 0.0, dz = 0.0;
    double t_max = 0.0, step = 0.0;
    if (!(input >> ray_id >> x0 >> y0 >> z0 >> dx >> dy >> dz >> t_max >> step)) {
      std::cerr << "bad ray line: " << line << '\n';
      return 4;
    }
    const double norm = std::sqrt(dx*dx + dy*dy + dz*dz);
    if (!(norm > 0.0) || !(t_max > 0.0) || !(step > 0.0)) {
      std::cerr << "invalid ray parameters: " << line << '\n';
      return 5;
    }
    dx /= norm;
    dy /= norm;
    dz /= norm;

    double segment_start = 0.0;
    State current = state_on_ray(geometry, x0, y0, z0, dx, dy, dz, 0.0);
    unsigned int segment_index = 0;
    for (double t_left = 0.0; t_left < t_max; ) {
      const double t_right = std::min(t_left + step, t_max);
      const State right = state_on_ray(geometry, x0, y0, z0, dx, dy, dz, t_right);
      if (!(right == current)) {
        double lo = t_left;
        double hi = t_right;
        for (unsigned int iteration = 0; iteration < 50 && hi-lo > 1.0e-9; ++iteration) {
          const double mid = 0.5*(lo+hi);
          const State middle = state_on_ray(geometry, x0, y0, z0, dx, dy, dz, mid);
          if (middle == current) lo = mid;
          else hi = mid;
        }
        const double boundary = 0.5*(lo+hi);
        emit(ray_id, segment_index++, x0, y0, z0, dx, dy, dz,
             segment_start, boundary, current);
        segment_start = boundary;
        current = state_on_ray(geometry, x0, y0, z0, dx, dy, dz,
                               std::min(boundary + 2.0e-9, t_max));
      }
      t_left = t_right;
    }
    emit(ray_id, segment_index, x0, y0, z0, dx, dy, dz,
         segment_start, t_max, current);
  }
  return 0;
}
