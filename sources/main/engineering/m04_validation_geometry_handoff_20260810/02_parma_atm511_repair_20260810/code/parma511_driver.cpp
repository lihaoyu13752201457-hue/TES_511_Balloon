#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

// These functions are implemented by the unmodified official PARMA
// subroutines.cpp archived under ../vendor/.  This wrapper intentionally does
// not call the continuum-spectrum function and does not generate particles.
double getHPcpp(int, int, int);
double getrcpp(double, double);
double getdcpp(double, double);
double getSpecAngFinalCpp(int, double, double, double, double, double, double);
double get511fluxCpp(double, double, double);

namespace {

constexpr double kPi = 3.141592653589793238462643383279502884;
constexpr double kLineEnergyMeV = 0.51099895;

struct Inputs {
  int year = 2025;
  int month = 8;
  int day = 31;
  double latitude_deg = 34.0;
  double longitude_deg = 100.0;
  double altitude_km = 38.75;
  double solar_modulation_mv = 114.6;
  double cutoff_rigidity_gv = 11.6;
  double atmospheric_depth_g_cm2 = 3.4614689720143224;
  double local_geometry_g = 0.15;
  int bins = 80;
  int quadrature_order = 64;
};

double parse_double(const char* text, const char* label) {
  char* end = nullptr;
  const double value = std::strtod(text, &end);
  if (end == text || *end != '\0' || !std::isfinite(value)) {
    throw std::runtime_error(std::string("invalid ") + label + ": " + text);
  }
  return value;
}

int parse_int(const char* text, const char* label) {
  char* end = nullptr;
  const long value = std::strtol(text, &end, 10);
  if (end == text || *end != '\0' || value < 1 || value > 1000000) {
    throw std::runtime_error(std::string("invalid ") + label + ": " + text);
  }
  return static_cast<int>(value);
}

Inputs parse_args(int argc, char** argv) {
  Inputs x;
  for (int i = 1; i < argc; ++i) {
    const std::string arg(argv[i]);
    auto require_value = [&](const char* name) -> const char* {
      if (i + 1 >= argc) {
        throw std::runtime_error(std::string("missing value for ") + name);
      }
      return argv[++i];
    };
    if (arg == "--g") {
      x.local_geometry_g = parse_double(require_value("--g"), "g");
    } else if (arg == "--s") {
      x.solar_modulation_mv = parse_double(require_value("--s"), "s");
    } else if (arg == "--rc") {
      x.cutoff_rigidity_gv = parse_double(require_value("--rc"), "Rc");
    } else if (arg == "--depth") {
      x.atmospheric_depth_g_cm2 =
          parse_double(require_value("--depth"), "depth");
    } else if (arg == "--bins") {
      x.bins = parse_int(require_value("--bins"), "bins");
    } else if (arg == "--quadrature-order") {
      x.quadrature_order =
          parse_int(require_value("--quadrature-order"), "quadrature order");
    } else {
      throw std::runtime_error("unknown argument: " + arg);
    }
  }
  if (x.local_geometry_g < 0.0 && x.local_geometry_g != 10.0 &&
      x.local_geometry_g != 100.0) {
    throw std::runtime_error("unsupported negative g for this audit wrapper");
  }
  if (x.quadrature_order < 8 || x.quadrature_order > 256) {
    throw std::runtime_error("quadrature order must be in [8, 256]");
  }
  return x;
}

// Compute Gauss-Legendre nodes and weights on [-1, 1].
void gauss_legendre_rule(int n, std::vector<double>& nodes,
                         std::vector<double>& weights) {
  nodes.assign(n, 0.0);
  weights.assign(n, 0.0);
  const int half = (n + 1) / 2;
  for (int i = 0; i < half; ++i) {
    double z = std::cos(kPi * (static_cast<double>(i) + 0.75) /
                        (static_cast<double>(n) + 0.5));
    double p1 = 0.0;
    double derivative = 0.0;
    for (int iteration = 0; iteration < 100; ++iteration) {
      p1 = 1.0;
      double p2 = 0.0;
      for (int j = 1; j <= n; ++j) {
        const double p3 = p2;
        p2 = p1;
        p1 = ((2.0 * j - 1.0) * z * p2 - (j - 1.0) * p3) / j;
      }
      derivative = n * (z * p1 - p2) / (z * z - 1.0);
      const double next = z - p1 / derivative;
      if (std::abs(next - z) <= 4.0e-16) {
        z = next;
        break;
      }
      z = next;
    }
    // Re-evaluate the derivative at the final root.
    p1 = 1.0;
    double p2 = 0.0;
    for (int j = 1; j <= n; ++j) {
      const double p3 = p2;
      p2 = p1;
      p1 = ((2.0 * j - 1.0) * z * p2 - (j - 1.0) * p3) / j;
    }
    derivative = n * (z * p1 - p2) / (z * z - 1.0);
    const double w = 2.0 / ((1.0 - z * z) * derivative * derivative);
    nodes[i] = -z;
    nodes[n - 1 - i] = z;
    weights[i] = w;
    weights[n - 1 - i] = w;
  }
}

double integrate_angular_pdf(double mu_low, double mu_high, const Inputs& x,
                             const std::vector<double>& nodes,
                             const std::vector<double>& weights) {
  const double midpoint = 0.5 * (mu_low + mu_high);
  const double half_width = 0.5 * (mu_high - mu_low);
  double sum = 0.0;
  for (std::size_t i = 0; i < nodes.size(); ++i) {
    const double mu = midpoint + half_width * nodes[i];
    const double density = getSpecAngFinalCpp(
        6, x.solar_modulation_mv, x.cutoff_rigidity_gv,
        x.atmospheric_depth_g_cm2, kLineEnergyMeV, x.local_geometry_g, mu);
    sum += weights[i] * density;
  }
  // PARMA's angular function is differential per steradian and azimuthally
  // symmetric, so dOmega = 2*pi*dmu.
  return 2.0 * kPi * half_width * sum;
}

double integrate_angular_pdf_segmented(
    double mu_low, double mu_high, int segments, const Inputs& x,
    const std::vector<double>& nodes, const std::vector<double>& weights) {
  double sum = 0.0;
  for (int segment = 0; segment < segments; ++segment) {
    const double low =
        mu_low + (mu_high - mu_low) * segment / segments;
    const double high =
        mu_low + (mu_high - mu_low) * (segment + 1) / segments;
    sum += integrate_angular_pdf(low, high, x, nodes, weights);
  }
  return sum;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    const Inputs x = parse_args(argc, argv);
    std::vector<double> nodes;
    std::vector<double> weights;
    gauss_legendre_rule(x.quadrature_order, nodes, weights);

    const double derived_solar = getHPcpp(x.year, x.month, x.day);
    const double derived_rc = getrcpp(x.latitude_deg, x.longitude_deg);
    const double derived_depth = getdcpp(x.altitude_km, x.latitude_deg);
    const double line_flux = get511fluxCpp(
        x.solar_modulation_mv, x.cutoff_rigidity_gv,
        x.atmospheric_depth_g_cm2);

    std::vector<double> bin_integrals(x.bins, 0.0);
    double angular_integral = 0.0;
    for (int bin = 0; bin < x.bins; ++bin) {
      const double low = -1.0 + 2.0 * bin / x.bins;
      const double high = -1.0 + 2.0 * (bin + 1) / x.bins;
      bin_integrals[bin] =
          integrate_angular_pdf(low, high, x, nodes, weights);
      angular_integral += bin_integrals[bin];
    }

    double negative_mu_integral = 0.0;
    double positive_mu_integral = 0.0;
    // Integrate hemispheres independently so the result also works for odd
    // diagnostic bin counts.
    // The official angular parameterization is piecewise.  Segment each
    // hemisphere before applying Gaussian quadrature so a high-order rule does
    // not straddle internal interpolation boundaries.
    negative_mu_integral = integrate_angular_pdf_segmented(
        -1.0, 0.0, 40, x, nodes, weights);
    positive_mu_integral = integrate_angular_pdf_segmented(
        0.0, 1.0, 40, x, nodes, weights);

    std::cout << std::setprecision(17);
    std::cout << "record,key,value,unit\n";
    std::cout << "meta,date," << x.year << '-' << std::setw(2)
              << std::setfill('0') << x.month << '-' << std::setw(2) << x.day
              << std::setfill(' ') << ",YYYY-MM-DD\n";
    std::cout << "meta,latitude," << x.latitude_deg << ",deg\n";
    std::cout << "meta,longitude," << x.longitude_deg << ",deg\n";
    std::cout << "meta,altitude," << x.altitude_km << ",km\n";
    std::cout << "derived,solar_modulation," << derived_solar << ",MV\n";
    std::cout << "derived,cutoff_rigidity," << derived_rc << ",GV\n";
    std::cout << "derived,atmospheric_depth," << derived_depth
              << ",g_cm-2\n";
    std::cout << "authority,solar_modulation," << x.solar_modulation_mv
              << ",MV\n";
    std::cout << "authority,cutoff_rigidity," << x.cutoff_rigidity_gv
              << ",GV\n";
    std::cout << "authority,atmospheric_depth," << x.atmospheric_depth_g_cm2
              << ",g_cm-2\n";
    std::cout << "authority,local_geometry_g," << x.local_geometry_g
              << ",dimensionless\n";
    std::cout << "line,line_energy," << kLineEnergyMeV << ",MeV\n";
    std::cout << "line,integrated_flux," << line_flux << ",cm-2_s-1\n";
    std::cout << "angular,full_sphere_integral," << angular_integral
              << ",dimensionless\n";
    std::cout << "angular,mu_negative_fraction,"
              << negative_mu_integral /
                     (negative_mu_integral + positive_mu_integral)
              << ",dimensionless\n";
    std::cout << "angular,mu_positive_fraction,"
              << positive_mu_integral /
                     (negative_mu_integral + positive_mu_integral)
              << ",dimensionless\n";
    std::cout << "angular,positive_to_negative_ratio,"
              << positive_mu_integral / negative_mu_integral
              << ",dimensionless\n";
    std::cout << "angular,bins," << x.bins << ",count\n";
    std::cout << "angular,quadrature_order," << x.quadrature_order
              << ",count\n";

    std::cout << "bin,bin_id,mu_low,mu_high,fraction,line_flux_cm-2_s-1\n";
    for (int bin = 0; bin < x.bins; ++bin) {
      const double low = -1.0 + 2.0 * bin / x.bins;
      const double high = -1.0 + 2.0 * (bin + 1) / x.bins;
      const double fraction = bin_integrals[bin] / angular_integral;
      std::cout << "bin," << bin << ',' << low << ',' << high << ','
                << fraction << ',' << line_flux * fraction << '\n';
    }
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "parma511_driver: " << error.what() << '\n';
    return 2;
  }
}
