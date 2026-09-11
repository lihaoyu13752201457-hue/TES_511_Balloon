#include <cmath>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

double getHPcpp(int, int, int);
double getrcpp(double, double);
double getdcpp(double, double);
double getSpecCpp(int, double, double, double, double, double);
double getSpecAngFinalCpp(int, double, double, double, double, double, double);

struct Particle {
  std::string name;
  int ip;
  int iang;
};

int main(int argc, char** argv) {
  if (argc != 8) {
    std::cerr << "usage: phase2_parma_grid_driver year month day lat_deg lon_deg altitude_km g\n";
    return 2;
  }
  int year = std::stoi(argv[1]);
  int month = std::stoi(argv[2]);
  int day = std::stoi(argv[3]);
  double lat = std::stod(argv[4]);
  double lon = std::stod(argv[5]);
  double altitude_km = std::stod(argv[6]);
  double g = std::stod(argv[7]);

  double s = getHPcpp(year, month, day);
  double r = getrcpp(lat, lon);
  double d = 0.0;
  if (altitude_km >= 25.0) {
    // PARMA's public C++ helper warns and falls back outside its comfortable
    // altitude helper range for stratospheric balloon values.  Use a compact
    // standard-atmosphere depth approximation in g/cm2 for the Phase-2 balloon
    // grid; the PARMA spectrum functions themselves still receive depth.
    d = 1033.0 * std::exp(-altitude_km / 6.8);
  } else {
    d = getdcpp(altitude_km, lat);
  }

  std::vector<Particle> particles = {
      {"n", 0, 1},       {"p", 1, 2},       {"alpha", 2, 3},
      {"muplus", 29, 4}, {"muminus", 30, 4}, {"eminus", 31, 5},
      {"eplus", 32, 5},  {"gamma", 33, 6},
  };
  std::vector<double> mu_mid = {
      0.95, 0.85, 0.75, 0.65, 0.55, 0.45, 0.35, 0.25, 0.15, 0.05,
      -0.05, -0.15, -0.25, -0.35, -0.45, -0.55, -0.65, -0.75, -0.85, -0.95,
  };
  std::vector<double> energies;
  const double e_min = 1.0e-2;
  const double e_max = 1.0e4;
  const int n_energy = 64;
  for (int i = 0; i < n_energy; ++i) {
    double f = static_cast<double>(i) / static_cast<double>(n_energy - 1);
    energies.push_back(std::exp(std::log(e_min) + f * (std::log(e_max) - std::log(e_min))));
  }

  std::cout << std::setprecision(12);
  std::cout << "META," << s << "," << r << "," << d << "\n";
  std::cout << "particle,angle_bin,mu_mid,theta_mid_deg,energy_bin,energy_MeV,"
               "angular_integrated_flux_cm2_s_MeV,differential_flux_cm2_s_sr_MeV\n";
  for (const auto& p : particles) {
    for (size_t ia = 0; ia < mu_mid.size(); ++ia) {
      double mu = mu_mid[ia];
      double theta = std::acos(mu) * 180.0 / M_PI;
      for (size_t ie = 0; ie < energies.size(); ++ie) {
        double e = energies[ie];
        double flux = getSpecCpp(p.ip, s, r, d, e, g);
        double ang = flux * getSpecAngFinalCpp(p.iang, s, r, d, e, g, mu);
        if (!std::isfinite(flux)) flux = 0.0;
        if (!std::isfinite(ang)) ang = 0.0;
        std::cout << p.name << "," << ia << "," << mu << "," << theta << "," << ie
                  << "," << e << "," << flux << "," << ang << "\n";
      }
    }
  }
  return 0;
}
