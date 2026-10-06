#include "CrystalKernel.hh"
#include "G4Box.hh"
#include "G4Electron.hh"
#include "G4EmCalculator.hh"
#include "G4EmStandardPhysics.hh"
#include "G4Event.hh"
#include "G4ExtrudedSolid.hh"
#include "G4Gamma.hh"
#include "G4GammaGeneralProcess.hh"
#include "G4LogicalVolume.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4ParticleGun.hh"
#include "G4Positron.hh"
#include "G4ProcessManager.hh"
#include "G4RunManager.hh"
#include "G4Step.hh"
#include "G4StepLimiter.hh"
#include "G4SystemOfUnits.hh"
#include "G4Transform3D.hh"
#include "G4UserEventAction.hh"
#include "G4UserLimits.hh"
#include "G4UserSteppingAction.hh"
#include "G4VDiscreteProcess.hh"
#include "G4VModularPhysicsList.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include <cfloat>
#include <filesystem>
#include <iomanip>
#include <memory>
#include <set>
#include <sstream>
namespace fs = std::filesystem;
struct Opt {
  int n = 50000;
  long seed = 92028100;
  std::string model = "dh", physics = "combined", geometry = "single", out,
              data, legacy;
  double t = 10.218801, offset = 0, maxstep = 1, gap = .2, muLoss = .4;
  bool point = false, allowLegacy = false, checkOnly = false;
};
Opt parse(int argc, char **argv) {
  Opt o;
  for (int i = 1; i < argc; ++i) {
    std::string a = argv[i];
    auto val = [&]() {
      if (++i >= argc)
        throw std::runtime_error("missing option argument");
      return std::string(argv[i]);
    };
    if (a == "--n")
      o.n = std::stoi(val());
    else if (a == "--seed")
      o.seed = std::stol(val());
    else if (a == "--model")
      o.model = val();
    else if (a == "--physics")
      o.physics = val();
    else if (a == "--geometry")
      o.geometry = val();
    else if (a == "--out")
      o.out = val();
    else if (a == "--data")
      o.data = val();
    else if (a == "--legacy-curve")
      o.legacy = val();
    else if (a == "--thickness")
      o.t = std::stod(val());
    else if (a == "--offset")
      o.offset = std::stod(val());
    else if (a == "--step")
      o.maxstep = std::stod(val());
    else if (a == "--gap")
      o.gap = std::stod(val());
    else if (a == "--mu-loss")
      o.muLoss = std::stod(val());
    else if (a == "--point")
      o.point = true;
    else if (a == "--allow-invalid-legacy")
      o.allowLegacy = true;
    else if (a == "--check-only")
      o.checkOnly = true;
    else
      throw std::runtime_error("unknown option: " + a);
  }
  if (o.model != "dh" && o.model != "legacy" && o.model != "input_only")
    throw std::runtime_error("unknown model");
  if (o.physics != "combined" && o.physics != "laue_only" &&
      o.physics != "loss" && o.physics != "em_only")
    throw std::runtime_error("unknown physics");
  if (o.geometry != "single" && o.geometry != "ring22" &&
      o.geometry != "ring25cut" && o.geometry != "legacy25")
    throw std::runtime_error("unknown geometry");
  if (o.geometry == "legacy25" && !o.allowLegacy)
    throw std::runtime_error("legacy25 contains overlapping solids; explicit "
                             "diagnostic override required");
  if (!std::isfinite(o.t) || !std::isfinite(o.offset) ||
      !std::isfinite(o.maxstep) || !std::isfinite(o.gap) ||
      !std::isfinite(o.muLoss))
    throw std::runtime_error("nonfinite option");
  if (o.n < 1 || o.n > 1000000 || o.seed <= 0 || o.t <= 0 || o.t > 20 ||
      o.maxstep < 0 || o.gap < 0 || o.gap > 1 || o.muLoss < 0 ||
      std::abs(o.offset) > 120 || o.out.empty())
    throw std::runtime_error("option outside validated contract");
  if (fs::exists(o.out))
    throw std::runtime_error(
        "output directory already exists; refuse overwrite");
  return o;
}
constexpr double radius = 74.277928547, focal = 10000., side = 18.;
bool crystal(const G4VPhysicalVolume *v) {
  return v && v->GetName() == "Crystal";
}
struct Geometry {
  Opt o;
  int count;
  double area;
  std::vector<G4TwoVector> polygon;
  explicit Geometry(const Opt &opt)
      : o(opt), count(o.geometry == "single"   ? 1
                      : o.geometry == "ring22" ? 22
                                               : 25) {
    polygon = {{-9, -9}, {9, -9}, {9, 9}, {-9, 9}};
    if (o.geometry == "ring25cut") {
      // Maximal intersection of the square envelope with a separated angular
      // sector.
      double alpha = laue::pi / count;
      for (int sign : {-1, 1}) {
        auto old = polygon;
        polygon.clear();
        auto f = [&](const G4TwoVector &p) {
          return sign * p.y() * std::cos(alpha) -
                 (radius + p.x()) * std::sin(alpha) + o.gap / 2;
        };
        for (size_t i = 0; i < old.size(); ++i) {
          auto a = old[i], b = old[(i + 1) % old.size()];
          double fa = f(a), fb = f(b);
          if (fa <= 0)
            polygon.push_back(a);
          if ((fa < 0 && fb > 0) || (fa > 0 && fb < 0)) {
            double q = fa / (fa - fb);
            polygon.push_back(a + q * (b - a));
          }
        }
      }
    }
    area = 0;
    for (size_t i = 0; i < polygon.size(); ++i) {
      auto a = polygon[i], b = polygon[(i + 1) % polygon.size()];
      area += a.x() * b.y() - a.y() * b.x();
    }
    area = std::abs(area) / 2;
  }
  double phi(int i) const { return 2 * laue::pi * i / count; }
  G4ThreeVector center(int i) const {
    return {radius * std::cos(phi(i)), radius * std::sin(phi(i)), 0};
  }
  G4ThreeVector normal(int i) const {
    return (G4ThreeVector(0, 0, 1) -
            (G4ThreeVector(0, 0, focal) - center(i)).unit())
        .unit();
  }
  bool rotated() const { return o.geometry != "legacy25"; }
  bool contains(double x, double y) const {
    if (o.geometry != "ring25cut")
      return true;
    double a = laue::pi / count;
    return std::abs(y) * std::cos(a) - (radius + x) * std::sin(a) + o.gap / 2 <=
           0;
  }
};
struct TrackInfo {
  int nd = 0;
  bool em = false;
};
struct State {
  const Opt &o;
  const Geometry &g;
  const laue::Reference &r;
  std::ofstream ev, ex, fp, inter;
  std::map<int, TrackInfo> tracks;
  std::set<int> focalSeen;
  int event = 0;
  int gammaExit = 0, ndEvent = 0, rExit = 0, tExit = 0, tUncoll = 0,
      focusAll = 0, focusClean = 0;
  double edep = 0, escape = 0, maxE = 0, maxB = 0, maxQ = 0, maxStep = 0,
         maxGammaStep = 0;
  long gammaSteps = 0, steps = 0, totalDiff = 0;
  bool anyFocalEm = false;
  State(const Opt &oo, const Geometry &gg, const laue::Reference &rr)
      : o(oo), g(gg), r(rr) {
    fs::create_directory(o.out);
    ev.open(o.out + "/events.csv");
    ex.open(o.out + "/exits.csv");
    fp.open(o.out + "/focal.csv");
    inter.open(o.out + "/diffractions.csv");
    ev << std::setprecision(17)
       << "event_id,gamma_exits,R_clean,T_coherent,T_uncollided,other_gamma,no_"
          "gamma,n_diffraction,focus_photons,focus_clean_photons,edep_keV,"
          "escape_keV,energy_residual_keV\n";
    ex << std::setprecision(17)
       << "event_id,track_id,parent_id,particle,E_keV,x_mm,y_mm,z_mm,ux,uy,uz,"
          "n_diffraction,em_history\n";
    fp << std::setprecision(17)
       << "event_id,track_id,parent_id,E_keV,x_mm,y_mm,z_mm,ux,uy,uz,n_"
          "diffraction,em_history,within_18p98,within_15\n";
    inter << std::setprecision(17)
          << "event_id,track_id,n_diffraction,E_keV,phi,bragg_residual,"
             "reciprocal_relative_residual,in_x,in_y,in_z,out_x,out_y,out_z\n";
  }
  TrackInfo &info(const G4Track *t) {
    int id = t->GetTrackID();
    if (!tracks.count(id)) {
      int p = t->GetParentID();
      tracks[id] = p ? tracks[p] : TrackInfo{};
    }
    return tracks[id];
  }
  void begin(const G4Event *e) {
    event = e->GetEventID();
    tracks.clear();
    focalSeen.clear();
    gammaExit = ndEvent = rExit = tExit = tUncoll = focusAll = focusClean = 0;
    edep = escape = 0;
    anyFocalEm = false;
  }
  void diffraction(const G4Track &t, const G4ThreeVector &n,
                   const G4ThreeVector &out, double phi) {
    auto &z = info(&t);
    ++z.nd;
    ++ndEvent;
    ++totalDiff;
    double br = t.GetMomentumDirection().dot(n) - std::sin(r.theta),
           q = (out - t.GetMomentumDirection()).mag() /
                   (2 * std::sin(r.theta)) -
               1;
    maxB = std::max(maxB, std::abs(br));
    maxQ = std::max(maxQ, std::abs(q));
    if (o.model == "dh" && (std::abs(br) > 1e-12 || std::abs(q) > 1e-9))
      throw std::runtime_error("Bragg/reciprocal invariant failed");
    auto u = t.GetMomentumDirection();
    inter << event << ',' << t.GetTrackID() << ',' << z.nd << ','
          << t.GetKineticEnergy() / keV << ',' << phi << ',' << br << ',' << q
          << ',' << u.x() << ',' << u.y() << ',' << u.z() << ',' << out.x()
          << ',' << out.y() << ',' << out.z() << '\n';
  }
  void step(const G4Step *s) {
    const auto *t = s->GetTrack();
    auto &z = info(t);
    auto pre = s->GetPreStepPoint(), post = s->GetPostStepPoint();
    bool inside = crystal(pre->GetPhysicalVolume());
    bool gamma = t->GetDefinition() == G4Gamma::GammaDefinition();
    const G4VProcess *p = post->GetProcessDefinedStep();
    if (auto general = dynamic_cast<const G4GammaGeneralProcess *>(p))
      if (general->GetSelectedProcess())
        p = general->GetSelectedProcess();
    std::string name = p ? p->GetProcessName() : "";
    if (inside && gamma) {
      ++gammaSteps;
      maxGammaStep = std::max(maxGammaStep, s->GetStepLength() / mm);
    }
    if (inside) {
      ++steps;
      maxStep = std::max(maxStep, s->GetStepLength() / mm);
      if (gamma && name != "Transportation" && name != "StepLimiter" &&
          name != "Laue511" && !name.empty())
        z.em = true;
    }
    edep += s->GetTotalEnergyDeposit() / keV;
    if (!post->GetPhysicalVolume())
      escape += post->GetKineticEnergy() / keV;
    if (inside && post->GetStepStatus() == fGeomBoundary &&
        !crystal(post->GetPhysicalVolume())) {
      auto v = post->GetMomentumDirection(), a = post->GetPosition();
      double en = post->GetKineticEnergy() / keV;
      bool clean = gamma && !z.em && std::abs(en - 511) < 1e-6;
      if (gamma) {
        ++gammaExit;
        if (clean) {
          if (z.nd % 2)
            rExit = 1;
          else
            tExit = 1;
          if (z.nd == 0)
            tUncoll = 1;
        }
      }
      ex << event << ',' << t->GetTrackID() << ',' << t->GetParentID() << ','
         << t->GetDefinition()->GetParticleName() << ',' << en << ','
         << a.x() / mm << ',' << a.y() / mm << ',' << a.z() / mm << ',' << v.x()
         << ',' << v.y() << ',' << v.z() << ',' << z.nd << ',' << z.em << '\n';
    }
    double za = pre->GetPosition().z() / mm, zb = post->GetPosition().z() / mm;
    if (gamma && za < focal && zb >= focal && zb > za &&
        !focalSeen.count(t->GetTrackID())) {
      focalSeen.insert(t->GetTrackID());
      double w = (focal - za) / (zb - za);
      auto pnt =
          pre->GetPosition() + w * (post->GetPosition() - pre->GetPosition());
      auto u = pre->GetMomentumDirection();
      double rho = pnt.perp() / mm, en = pre->GetKineticEnergy() / keV;
      bool hit = rho <= 18.98;
      if (hit && z.nd > 0) {
        ++focusAll;
        if (!z.em && std::abs(en - 511) < 1e-6)
          ++focusClean;
        else
          anyFocalEm = true;
      }
      fp << event << ',' << t->GetTrackID() << ',' << t->GetParentID() << ','
         << en << ',' << pnt.x() / mm << ',' << pnt.y() / mm << ',' << focal
         << ',' << u.x() << ',' << u.y() << ',' << u.z() << ',' << z.nd << ','
         << z.em << ',' << hit << ',' << (rho <= 15) << '\n';
    }
  }
  void end() {
    double residual = 511 - edep - escape;
    maxE = std::max(maxE, std::abs(residual));
    if (std::abs(residual) > 1e-6)
      throw std::runtime_error("event energy balance failed");
    ev << event << ',' << gammaExit << ',' << rExit << ',' << tExit << ','
       << tUncoll << ',' << (gammaExit > 0 && !rExit && !tExit) << ','
       << (gammaExit == 0) << ',' << ndEvent << ',' << focusAll << ','
       << focusClean << ',' << edep << ',' << escape << ',' << residual << '\n';
  }
  void finish() {
    std::ofstream f(o.out + "/summary.json");
    f << std::setprecision(17)
      << "{\n\"n_primaries\":" << (o.checkOnly ? 0 : o.n) << ",\n\"model\":\""
      << o.model << "\",\n\"geometry\":\"" << o.geometry
      << "\",\n\"physics\":\"" << o.physics << "\",\n\"tiles\":" << g.count
      << ",\n\"single_tile_area_mm2\":" << g.area
      << ",\n\"incident_area_cm2\":" << g.count * g.area / 100
      << ",\n\"source_is_point\":" << (o.point ? "true" : "false")
      << ",\n\"n_diffraction_interactions\":" << totalDiff
      << ",\n\"n_crystal_steps\":" << steps << ",\n\"max_step_mm\":" << maxStep
      << ",\n\"max_gamma_step_mm\":" << maxGammaStep
      << ",\n\"n_gamma_crystal_steps\":" << gammaSteps
      << ",\n\"max_energy_residual_keV\":" << maxE
      << ",\n\"max_bragg_residual\":" << maxB
      << ",\n\"max_reciprocal_relative_residual\":" << maxQ << "\n}\n";
  }
};
class Detector : public G4VUserDetectorConstruction {
  const Geometry &g;

public:
  explicit Detector(const Geometry &gg) : g(gg) {}
  G4VPhysicalVolume *Construct() override {
    auto n = G4NistManager::Instance();
    auto worldL = new G4LogicalVolume(
        new G4Box("world", 160 * mm, 160 * mm, (10100 + g.o.t) * mm),
        n->FindOrBuildMaterial("G4_Galactic"), "world");
    auto world =
        new G4PVPlacement(nullptr, {}, worldL, "World", nullptr, false, 0);
    G4VSolid *solid =
        g.o.geometry == "ring25cut"
            ? static_cast<G4VSolid *>(
                  new G4ExtrudedSolid("tile", g.polygon, g.o.t / 2 * mm,
                                      G4TwoVector(), 1, G4TwoVector(), 1))
            : static_cast<G4VSolid *>(
                  new G4Box("tile", 9 * mm, 9 * mm, g.o.t / 2 * mm));
    auto logic =
        new G4LogicalVolume(solid, n->FindOrBuildMaterial("G4_Ge"), "tile");
    if (g.o.maxstep > 0)
      logic->SetUserLimits(new G4UserLimits(g.o.maxstep * mm));
    bool overlap = false;
    for (int i = 0; i < g.count; ++i) {
      G4RotationMatrix rot;
      if (g.rotated())
        rot.rotateZ(g.phi(i));
      auto pv = new G4PVPlacement(G4Transform3D(rot, g.center(i) * mm), logic,
                                  "Crystal", worldL, false, i);
      if (g.o.geometry != "legacy25")
        overlap = pv->CheckOverlaps(3000, 1e-6 * mm, false, 1) || overlap;
    }
    if (overlap)
      throw std::runtime_error("physical crystal overlap detected");
    return world;
  }
};
class LaueProcess : public G4VDiscreteProcess {
  State &s;
  const Opt &o;
  const Geometry &g;
  const laue::Reference &r;
  std::unique_ptr<laue::LegacyCurve> legacy;

public:
  LaueProcess(State &ss)
      : G4VDiscreteProcess("Laue511"), s(ss), o(ss.o), g(ss.g), r(ss.r) {
    if (o.model == "legacy")
      legacy = std::make_unique<laue::LegacyCurve>(o.legacy);
  }
  double rate(const G4Track &t) {
    if (!crystal(t.GetVolume()) ||
        t.GetDefinition() != G4Gamma::GammaDefinition())
      return 0;
    if (o.model != "legacy" &&
        std::abs(t.GetKineticEnergy() / keV - r.energy) > 1e-6)
      return 0; // line-model contract: degraded photons retain all standard EM
    if (o.model != "dh" && t.GetParentID() != 0)
      return 0;
    auto u = t.GetMomentumDirection();
    auto n = g.normal(t.GetVolume()->GetCopyNo());
    double delta = std::asin(std::clamp(std::abs(u.dot(n)), 0., 1.)) - r.theta;
    if (o.model == "dh")
      return r.Rate(u, n);
    double p =
        legacy ? legacy->P0(delta)
               : .5 * (-std::expm1(-2 * r.peak *
                                   std::exp(-.5 * std::pow(delta / r.eta, 2)) *
                                   r.tref / 10));
    return -std::log1p(-p) / (o.t / 10 / std::max(1e-6, std::abs(u.z())));
  }
  G4double GetMeanFreePath(const G4Track &t, G4double,
                           G4ForceCondition *c) override {
    *c = NotForced;
    double a = rate(t);
    return a > 0 ? cm / a : DBL_MAX;
  }
  G4VParticleChange *PostStepDoIt(const G4Track &t, const G4Step &) override {
    aParticleChange.Initialize(t);
    ClearNumberOfInteractionLengthLeft();
    if (rate(t) <= 0)
      return &aParticleChange;
    auto u = t.GetMomentumDirection(),
         n0 = g.normal(t.GetVolume()->GetCopyNo());
    double phi = 0;
    auto n = o.model == "dh"
                 ? r.SampleNormal(u, n0, phi)
                 : laue::UnconditionalNormal(n0, r.fwhm * laue::pi /
                                                     (180 * 3600 * 2.355));
    auto v = laue::Reflect(u, n);
    s.diffraction(t, n, v, phi);
    if (o.model == "dh")
      aParticleChange.ProposeMomentumDirection(v);
    else {
      aParticleChange.SetNumberOfSecondaries(1);
      aParticleChange.AddSecondary(
          new G4DynamicParticle(G4Gamma::GammaDefinition(), v,
                                t.GetKineticEnergy()),
          t.GetPosition() + 1e-5 * mm * v, true);
      aParticleChange.ProposeTrackStatus(fStopAndKill);
    }
    return &aParticleChange;
  }
};
class LossProcess : public G4VDiscreteProcess {
  double mu;

public:
  explicit LossProcess(double v) : G4VDiscreteProcess("UniformLoss"), mu(v) {}
  G4double GetMeanFreePath(const G4Track &t, G4double,
                           G4ForceCondition *c) override {
    *c = NotForced;
    return crystal(t.GetVolume()) && mu > 0 ? cm / mu : DBL_MAX;
  }
  G4VParticleChange *PostStepDoIt(const G4Track &t, const G4Step &) override {
    aParticleChange.Initialize(t);
    aParticleChange.ProposeLocalEnergyDeposit(t.GetKineticEnergy());
    aParticleChange.ProposeEnergy(0);
    aParticleChange.ProposeTrackStatus(fStopAndKill);
    return &aParticleChange;
  }
};
class Physics : public G4VModularPhysicsList {
  State &s;

public:
  explicit Physics(State &ss) : s(ss) {
    defaultCutValue = .1 * mm;
    if (s.o.physics == "combined" || s.o.physics == "em_only")
      RegisterPhysics(new G4EmStandardPhysics());
  }
  void ConstructParticle() override {
    G4VModularPhysicsList::ConstructParticle();
    G4Gamma::GammaDefinition();
    G4Electron::ElectronDefinition();
    G4Positron::PositronDefinition();
  }
  void ConstructProcess() override {
    G4VModularPhysicsList::ConstructProcess();
    auto pm = G4Gamma::GammaDefinition()->GetProcessManager();
    if (s.o.physics != "em_only")
      pm->AddDiscreteProcess(new LaueProcess(s));
    if (s.o.physics == "loss")
      pm->AddDiscreteProcess(new LossProcess(s.o.muLoss));
    if (s.o.maxstep > 0)
      pm->AddDiscreteProcess(new G4StepLimiter());
  }
};
class Source : public G4VUserPrimaryGeneratorAction {
  const Geometry &g;
  G4ParticleGun gun{1};

public:
  explicit Source(const Geometry &gg) : g(gg) {
    gun.SetParticleDefinition(G4Gamma::GammaDefinition());
  }
  void GeneratePrimaries(G4Event *e) override {
    int i = e->GetEventID() % g.count;
    double x = 0, y = 0;
    if (!g.o.point) {
      do {
        x = (G4UniformRand() - .5) * side;
        y = (G4UniformRand() - .5) * side;
      } while (!g.contains(x, y));
    } else {
      G4UniformRand();
      G4UniformRand();
    }
    double ph = g.rotated() ? g.phi(i) : 0;
    auto target =
        g.center(i) + G4ThreeVector(x * std::cos(ph) - y * std::sin(ph),
                                    x * std::sin(ph) + y * std::cos(ph), 0);
    double a = g.o.offset * laue::pi / (180 * 3600);
    G4ThreeVector u(std::sin(a), 0, std::cos(a));
    double z = -g.o.t / 2 - 5;
    auto pos = target + z / u.z() * u;
    gun.SetParticleEnergy(511 * keV);
    gun.SetParticlePosition(pos * mm);
    gun.SetParticleMomentumDirection(u);
    gun.GeneratePrimaryVertex(e);
  }
};
class Stepping : public G4UserSteppingAction {
  State &s;

public:
  explicit Stepping(State &ss) : s(ss) {}
  void UserSteppingAction(const G4Step *x) override { s.step(x); }
};
class Events : public G4UserEventAction {
  State &s;

public:
  explicit Events(State &ss) : s(ss) {}
  void BeginOfEventAction(const G4Event *e) override { s.begin(e); }
  void EndOfEventAction(const G4Event *) override { s.end(); }
};
int main(int argc, char **argv) {
  try {
    auto o = parse(argc, argv);
    laue::Reference ref(o.data);
    Geometry geo(o);
    State state(o, geo, ref);
    CLHEP::HepRandom::setTheSeed(o.seed);
    auto rm = std::make_unique<G4RunManager>();
    rm->SetUserInitialization(new Detector(geo));
    rm->SetUserInitialization(new Physics(state));
    rm->SetUserAction(new Source(geo));
    rm->SetUserAction(new Stepping(state));
    rm->SetUserAction(new Events(state));
    rm->Initialize();
    if (!o.checkOnly)
      rm->BeamOn(o.n);
    state.finish();
    if (!o.checkOnly && (o.physics == "combined" || o.physics == "em_only")) {
      G4EmCalculator calc;
      std::ofstream f(o.out + "/em_coefficients.csv");
      f << std::setprecision(17) << "process,mu_cm_inv\n";
      for (const std::string p : {"phot", "compt", "Rayl", "conv"})
        f << p << ','
          << calc.ComputeCrossSectionPerVolume(
                 511 * keV, G4Gamma::GammaDefinition(), p,
                 G4NistManager::Instance()->FindOrBuildMaterial("G4_Ge")) *
                 cm
          << '\n';
    }
    return 0;
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 2;
  }
}
