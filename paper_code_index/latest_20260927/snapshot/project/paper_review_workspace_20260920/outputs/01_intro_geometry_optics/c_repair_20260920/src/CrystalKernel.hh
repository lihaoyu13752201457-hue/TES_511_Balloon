#pragma once
// Local-rate, energy-conserving mosaic kernel for the validated Ge111 511-keV
// line. Conditional Bragg-cone kernel: Bornemann, Li & Wuttke (2020), Eqs.
// 10--16.
#include "G4ThreeVector.hh"
#include "Randomize.hh"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
namespace laue {
constexpr double pi = 3.1415926535897932384626433832795;
struct Reference {
  double energy = 0, d = 0, fwhm = 0, Q = 0, peak = 0, tref = 0, mu = 0,
         eta = 0, theta = 0;
  explicit Reference(const std::string &file) {
    std::ifstream f(file);
    if (!f)
      throw std::runtime_error("missing physics reference");
    std::map<std::string, double> m;
    std::string k;
    double v;
    while (f >> k >> v) {
      if (m.count(k) || !std::isfinite(v))
        throw std::runtime_error("duplicate/nonfinite reference value");
      m[k] = v;
    }
    if (!f.eof() || m.size() != 8 || m.at("format_version") != 1)
      throw std::runtime_error("invalid reference schema");
    energy = m.at("energy_keV");
    d = m.at("d_spacing_A");
    fwhm = m.at("mosaic_fwhm_arcsec");
    Q = m.at("Q_cm_inv");
    peak = m.at("sigma_peak_cm_inv");
    tref = m.at("reference_thickness_mm");
    mu = m.at("mu_photo_cm_inv");
    if (energy != 511 || std::abs(d - 3.266590088) > 1e-10 || fwhm != 30 ||
        Q <= 0 || peak <= 0 || mu <= 0 || tref <= 0)
      throw std::runtime_error("reference outside validated physical contract");
    eta = fwhm * pi / (180 * 3600 * std::sqrt(8 * std::log(2.)));
    theta = std::asin(12.398419843320026 / (energy * 2 * d));
    if (std::abs(Q / (eta * std::sqrt(2 * pi)) / peak - 1) > 1e-8)
      throw std::runtime_error("reference Q/peak normalization mismatch");
  }
  // This is an inverse cm local coefficient, independent of slab thickness or
  // G4Step.
  double Rate(const G4ThreeVector &u, const G4ThreeVector &nominal) const {
    double m = std::clamp(std::abs(u.dot(nominal)), 0., 1.);
    double delta = std::asin(m) - theta;
    if (std::abs(delta) > 10 * eta)
      return 0.; // discarded orientation mass < 2e-23
    double b = std::cos(theta) * std::sqrt(1 - m * m), x = b / (eta * eta);
    // Scaled I0 large-x expansion. In this contract x>2e8; next term <1e-26.
    double I0e = (1 + 1 / (8 * x) + 9 / (128 * x * x)) / std::sqrt(2 * pi * x);
    double s = std::sin(delta / 2);
    return Q * std::cos(theta) / (eta * eta) *
           std::exp(-2 * s * s / (eta * eta)) * I0e;
  }
  G4ThreeVector SampleNormal(const G4ThreeVector &u, G4ThreeVector nominal,
                             double &phi) const {
    if (u.dot(nominal) < 0)
      nominal = -nominal;
    double m = u.dot(nominal),
           b = std::cos(theta) * std::sqrt(std::max(0., 1 - m * m)),
           x = b / (eta * eta);
    if (x < 1e8)
      throw std::runtime_error(
          "conditional sampler outside narrow-mosaic contract");
    auto e1 = (nominal - m * u).unit();
    auto e2 = u.cross(e1).unit();
    constexpr double zmax = 12.;
    double z = 0.;
    const double logEnvelope = std::pow(zmax, 4) / (24 * x);
    for (int tries = 0;; ++tries) {
      if (tries > 1000)
        throw std::runtime_error("conditional sampler did not converge");
      z = G4RandGauss::shoot(0., 1.);
      if (std::abs(z) > zmax)
        continue;
      phi = z / std::sqrt(x);
      double s = std::sin(phi / 2);
      double logAccept = .5 * z * z - 2 * x * s * s - logEnvelope;
      if (std::log(G4UniformRand()) < logAccept)
        break;
    }
    // Exact energy-conserving Laue cone; no post-hoc angle or energy clipping.
    return std::sin(theta) * u +
           std::cos(theta) * (std::cos(phi) * e1 + std::sin(phi) * e2);
  }
};
inline G4ThreeVector Reflect(const G4ThreeVector &u, const G4ThreeVector &n) {
  return (u - 2 * u.dot(n) * n).unit();
}
inline G4ThreeVector UnconditionalNormal(const G4ThreeVector &n, double eta) {
  auto e1 = n.cross(G4ThreeVector(0, 0, 1));
  if (e1.mag2() < 1e-24)
    e1 = n.cross(G4ThreeVector(1, 0, 0));
  e1 = e1.unit();
  auto e2 = n.cross(e1).unit();
  return (n + G4RandGauss::shoot(0., eta) * e1 +
          G4RandGauss::shoot(0., eta) * e2)
      .unit();
}
struct LegacyCurve {
  std::vector<double> x, r, a;
  explicit LegacyCurve(const std::string &file) {
    std::ifstream f(file);
    if (!f)
      throw std::runtime_error("missing legacy curve");
    std::string line;
    std::getline(f, line);
    while (std::getline(f, line)) {
      std::vector<std::string> z;
      size_t pos = 0, start = 0;
      while ((pos = line.find(',', start)) != std::string::npos) {
        z.push_back(line.substr(start, pos - start));
        start = pos + 1;
      }
      z.push_back(line.substr(start));
      if (z.size() < 4)
        throw std::runtime_error("bad legacy CSV");
      x.push_back(std::stod(z[0]));
      r.push_back(std::stod(z[1]));
      a.push_back(std::stod(z[3]));
    }
    if (x.size() < 2 || !std::is_sorted(x.begin(), x.end()))
      throw std::runtime_error("invalid legacy curve grid");
  }
  double P0(double offset) const {
    auto it = std::lower_bound(x.begin(), x.end(), offset);
    size_t j = it - x.begin();
    if (j == 0)
      return r[0] / (1 - a[0]);
    if (j == x.size())
      return r.back() / (1 - a.back());
    double w = (offset - x[j - 1]) / (x[j] - x[j - 1]);
    double rr = r[j - 1] * (1 - w) + r[j] * w,
           aa = a[j - 1] * (1 - w) + a[j] * w;
    if (aa < 0 || aa >= 1 || rr < 0 || rr > 1 - aa)
      throw std::runtime_error("invalid legacy probability");
    return rr / (1 - aa);
  }
};
} // namespace laue
