#include "optics/GammaChannelReflection.hh"

#include <cfloat>
#include <cmath>
#include <stdexcept>

#include "G4ExceptionSeverity.hh"
#include "G4DynamicParticle.hh"
#include "G4Event.hh"
#include "G4Gamma.hh"
#include "G4LogicalVolume.hh"
#include "G4Navigator.hh"
#include "G4ParticleChange.hh"
#include "G4ParticleDefinition.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4RotationMatrix.hh"
#include "G4RunManager.hh"
#include "G4Step.hh"
#include "G4StepPoint.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "G4Track.hh"
#include "G4TransportationManager.hh"
#include "G4VPhysicalVolume.hh"
#include "Randomize.hh"

namespace {

G4double Clamp01(G4double value) {
  if (value < 0.0) return 0.0;
  if (value > 1.0) return 1.0;
  return value;
}

G4bool NameContains(const G4VPhysicalVolume* volume, const G4String& token) {
  if (volume == 0 || token.empty()) return false;
  if (volume->GetName().find(token) != G4String::npos) return true;
  const G4LogicalVolume* logical = volume->GetLogicalVolume();
  return logical != 0 && logical->GetName().find(token) != G4String::npos;
}

}  // namespace

namespace optics {

GammaChannelReflection::GammaChannelReflection(const G4String& name)
    : G4VDiscreteProcess(name),
      params_{1.0, 0.0, 0.0, 0.0},
      lookupMode_(ReflectivityLookupMode::kLinear),
      stackId_(""),
      useTable_(false),
      recordHistory_(false),
      requiredVolumeToken_("ChannelWall"),
      nBoundary_(0),
      nReflect_(0),
      nAbsorb_(0),
      nLeak_(0) {}

GammaChannelReflection::~GammaChannelReflection() = default;

G4bool GammaChannelReflection::IsApplicable(const G4ParticleDefinition& particle) {
  return &particle == G4Gamma::GammaDefinition();
}

G4double GammaChannelReflection::GetMeanFreePath(
    const G4Track&,
    G4double,
    G4ForceCondition* condition) {
  *condition = Forced;
  return DBL_MAX;
}

G4VParticleChange* GammaChannelReflection::PostStepDoIt(
    const G4Track& track,
    const G4Step& step) {
  aParticleChange.Initialize(track);

  if (track.GetDefinition() != G4Gamma::GammaDefinition()) {
    return &aParticleChange;
  }
  if (step.GetPostStepPoint()->GetStepStatus() != fGeomBoundary) {
    return &aParticleChange;
  }
  if (!IsChannelBoundary(step)) {
    return &aParticleChange;
  }

  G4bool normalValid = false;
  G4ThreeVector normal = SurfaceNormal(step, &normalValid);
  if (!normalValid || normal.mag2() == 0.0) {
    return &aParticleChange;
  }
  ++nBoundary_;

  normal = normal.unit();
  const G4ThreeVector k = track.GetMomentumDirection().unit();
  const G4double grazingAngle = std::asin(Clamp01(std::fabs(k.dot(normal))));
  const G4double energyKeV = track.GetKineticEnergy() / keV;
  const ChannelReflectivity probabilities = LookupReflectivity(energyKeV, grazingAngle);

  const G4double u = G4UniformRand();
  if (u < probabilities.A) {
    ++nAbsorb_;
    RecordBoundary(track, step, grazingAngle, probabilities, k, k, "ABSORB");
    aParticleChange.ProposeTrackStatus(fStopAndKill);
    return &aParticleChange;
  }

  if (u < probabilities.A + probabilities.R) {
    G4ThreeVector reflected = k - 2.0 * k.dot(normal) * normal;
    if (reflected.mag2() > 0.0) {
      reflected = reflected.unit();
      G4DynamicParticle* secondary =
          new G4DynamicParticle(G4Gamma::GammaDefinition(), reflected, track.GetKineticEnergy());
      aParticleChange.SetNumberOfSecondaries(1);
      aParticleChange.AddSecondary(
          secondary,
          step.GetPostStepPoint()->GetPosition() + 1.0e-5 * mm * reflected,
          true);
      aParticleChange.ProposeTrackStatus(fStopAndKill);
    }
    ++nReflect_;
    RecordBoundary(track, step, grazingAngle, probabilities, k, reflected, "REFLECT");
    return &aParticleChange;
  }

  // Toy-policy leakage: remove the photon and let optics_history record LEAK
  // in the eventual SteppingAction/EventAction layer.
  ++nLeak_;
  RecordBoundary(track, step, grazingAngle, probabilities, k, k, "LEAK");
  aParticleChange.ProposeTrackStatus(fStopAndKill);
  return &aParticleChange;
}

void GammaChannelReflection::SetProbabilities(G4double R, G4double A, G4double T) {
  const G4double sum = R + A + T;
  if (R < 0.0 || A < 0.0 || T < 0.0 || std::fabs(sum - 1.0) > 1.0e-9) {
    G4Exception(
        "GammaChannelReflection::SetProbabilities",
        "GammaChannelReflection001",
        FatalException,
        "R/A/T must be non-negative and sum to one.");
  }
  params_.R = R;
  params_.A = A;
  params_.T = T;
  useTable_ = false;
}

void GammaChannelReflection::LoadReflectivityTable(
    const G4String& path,
    ReflectivityLookupMode mode,
    const G4String& stackId) {
  try {
    table_ = ReflectivityTable::FromCsv(path);
  } catch (const std::exception& exc) {
    G4Exception(
        "GammaChannelReflection::LoadReflectivityTable",
        "GammaChannelReflection002",
        FatalException,
        exc.what());
  }
  lookupMode_ = mode;
  stackId_ = stackId;
  useTable_ = true;
}

void GammaChannelReflection::ClearReflectivityTable() {
  table_ = ReflectivityTable();
  stackId_ = "";
  useTable_ = false;
}

void GammaChannelReflection::SetRecordHistory(G4bool enabled) {
  recordHistory_ = enabled;
}

void GammaChannelReflection::SetRequiredVolumeToken(const G4String& token) {
  requiredVolumeToken_ = token;
}

const ChannelReflectivity& GammaChannelReflection::GetProbabilities() const {
  return params_;
}

const std::vector<ChannelBoundaryRecord>& GammaChannelReflection::GetHistory() const {
  return history_;
}

void GammaChannelReflection::ClearHistory() {
  history_.clear();
}

void GammaChannelReflection::ResetCounters() {
  nBoundary_ = 0;
  nReflect_ = 0;
  nAbsorb_ = 0;
  nLeak_ = 0;
  history_.clear();
}

G4int GammaChannelReflection::GetBoundaryCount() const {
  return nBoundary_;
}

G4int GammaChannelReflection::GetReflectCount() const {
  return nReflect_;
}

G4int GammaChannelReflection::GetAbsorbCount() const {
  return nAbsorb_;
}

G4int GammaChannelReflection::GetLeakCount() const {
  return nLeak_;
}

G4bool GammaChannelReflection::IsChannelBoundary(const G4Step& step) const {
  return ChannelBoundaryVolume(step) != 0;
}

const G4VPhysicalVolume* GammaChannelReflection::ChannelBoundaryVolume(const G4Step& step) const {
  const G4VPhysicalVolume* pre = step.GetPreStepPoint()->GetPhysicalVolume();
  const G4VPhysicalVolume* post = step.GetPostStepPoint()->GetPhysicalVolume();
  if (NameContains(post, requiredVolumeToken_)) return post;
  if (NameContains(pre, requiredVolumeToken_)) return pre;
  return 0;
}

G4ThreeVector GammaChannelReflection::SurfaceNormal(const G4Step& step, G4bool* valid) const {
  *valid = false;
  const G4VPhysicalVolume* pre = step.GetPreStepPoint()->GetPhysicalVolume();
  const G4VPhysicalVolume* post = step.GetPostStepPoint()->GetPhysicalVolume();
  const G4VPhysicalVolume* channelVolume = ChannelBoundaryVolume(step);
  if (NameContains(channelVolume, "CurvedTopChannelWall") ||
      NameContains(channelVolume, "CurvedBottomChannelWall")) {
    const G4RotationMatrix* rotation = channelVolume->GetObjectRotation();
    G4ThreeVector localNormal(0.0, 1.0, 0.0);
    G4ThreeVector broadFaceNormal = localNormal;
    if (rotation != 0) {
      broadFaceNormal = ((*rotation) * localNormal).unit();
    }
    G4Navigator* navigator =
        G4TransportationManager::GetTransportationManager()->GetNavigatorForTracking();
    if (navigator == 0) {
      *valid = true;
      return broadFaceNormal;
    }
    G4bool actualValid = false;
    G4ThreeVector actualNormal =
        navigator->GetGlobalExitNormal(step.GetPostStepPoint()->GetPosition(), &actualValid);
    if (!actualValid || actualNormal.mag2() == 0.0) {
      *valid = true;
      return broadFaceNormal;
    }
    actualNormal = actualNormal.unit();
    if (std::fabs(actualNormal.dot(broadFaceNormal)) < 0.7) {
      *valid = false;
      return G4ThreeVector();
    }
    *valid = true;
    return actualNormal;
  }
  if (NameContains(pre, "TopChannelWall") || NameContains(post, "TopChannelWall")) {
    *valid = true;
    return G4ThreeVector(0.0, -1.0, 0.0);
  }
  if (NameContains(pre, "BottomChannelWall") || NameContains(post, "BottomChannelWall")) {
    *valid = true;
    return G4ThreeVector(0.0, 1.0, 0.0);
  }
  G4Navigator* navigator =
      G4TransportationManager::GetTransportationManager()->GetNavigatorForTracking();
  if (navigator == 0) {
    return G4ThreeVector();
  }
  return navigator->GetGlobalExitNormal(step.GetPostStepPoint()->GetPosition(), valid);
}

ChannelReflectivity GammaChannelReflection::LookupReflectivity(
    G4double energyKeV,
    G4double thetaRad) const {
  if (!useTable_) {
    return params_;
  }
  try {
    const ReflectivityTableRow row = table_.Lookup(
        energyKeV,
        thetaRad,
        lookupMode_,
        stackId_.empty() ? std::string() : std::string(stackId_));
    return ChannelReflectivity{row.R, row.A, row.T, 0.0};
  } catch (const std::exception& exc) {
    G4Exception(
        "GammaChannelReflection::LookupReflectivity",
        "GammaChannelReflection003",
        FatalException,
        exc.what());
  }
  return params_;
}

void GammaChannelReflection::RecordBoundary(
    const G4Track& track,
    const G4Step& step,
    G4double thetaRad,
    const ChannelReflectivity& probabilities,
    const G4ThreeVector& directionBefore,
    const G4ThreeVector& directionAfter,
    const G4String& action) {
  if (!recordHistory_) return;
  const G4ThreeVector posMm = step.GetPostStepPoint()->GetPosition() / mm;
  const G4Event* event = G4RunManager::GetRunManager()->GetCurrentEvent();
  const G4int eventId = event ? event->GetEventID() : -1;
  const G4VPhysicalVolume* surface = ChannelBoundaryVolume(step);
  const G4int copyNo = surface ? surface->GetCopyNo() : -1;
  const G4String surfaceName = surface ? surface->GetName() : G4String("");
  history_.push_back(ChannelBoundaryRecord{
      eventId,
      nBoundary_,
      track.GetTrackID(),
      track.GetParentID(),
      track.GetKineticEnergy() / keV,
      thetaRad,
      probabilities,
      posMm,
      directionBefore,
      directionAfter,
      copyNo,
      surfaceName,
      action});
}

}  // namespace optics
