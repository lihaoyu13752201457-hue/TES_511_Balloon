#include "CrystalKernel.hh"
#include <iomanip>
#include <iostream>
int main(int argc, char **argv) {
  try {
    if (argc != 3)
      throw std::runtime_error("kernel_check reference output.csv");
    laue::Reference ref(argv[1]);
    CLHEP::HepRandom::setTheSeed(92028001);
    std::ofstream f(argv[2]);
    f << std::setprecision(17)
      << "offset_arcsec,phi,bragg_residual,reciprocal_relative_residual,rate_"
         "cm_inv,ux,uy,uz\n";
    G4ThreeVector n(std::cos(ref.theta), 0, std::sin(ref.theta));
    for (double off : {-60., -30., 0., 18., 60.}) {
      double angle = off * laue::pi / (180 * 3600);
      G4ThreeVector u(std::sin(angle), 0, std::cos(angle));
      for (int i = 0; i < 40000; ++i) {
        double phi;
        auto normal = ref.SampleNormal(u, n, phi);
        auto v = laue::Reflect(u, normal);
        double b = u.dot(normal) - std::sin(ref.theta),
               r = (v - u).mag() / (2 * std::sin(ref.theta)) - 1;
        if (std::abs(b) > 1e-12 || std::abs(r) > 1e-9 ||
            std::abs(v.mag() - 1) > 1e-14)
          throw std::runtime_error("kinematic invariant failed");
        f << off << ',' << phi << ',' << b << ',' << r << ',' << ref.Rate(u, n)
          << ',' << v.x() << ',' << v.y() << ',' << v.z() << '\n';
      }
    }
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 2;
  }
}
