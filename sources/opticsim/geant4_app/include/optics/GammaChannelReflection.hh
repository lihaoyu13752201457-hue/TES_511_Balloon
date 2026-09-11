#ifndef OPTICS_GAMMA_CHANNEL_REFLECTION_HH
#define OPTICS_GAMMA_CHANNEL_REFLECTION_HH

#include "G4String.hh"
#include "G4ThreeVector.hh"
#include "G4VDiscreteProcess.hh"
#include "globals.hh"
#include "optics/ReflectivityTable.hh"

#include <vector>

class G4ParticleDefinition;
class G4Step;
class G4Track;
class G4VParticleChange;
class G4VPhysicalVolume;

namespace optics {

struct ChannelReflectivity {
  G4double R;
  G4double A;
  G4double T;
  G4double sigmaSlopeRad;
};

struct ChannelBoundaryRecord {
  G4int sourceEventId;
  G4int boundaryIndex;
  G4int trackId;
  G4int parentId;
  G4double energyKeV;
  G4double thetaGrazingRad;
  ChannelReflectivity probabilities;
  G4ThreeVector positionMm;
  G4ThreeVector directionBefore;
  G4ThreeVector directionAfter;
  G4int surfaceCopyNo;
  G4String surfaceName;
  G4String action;
};

class GammaChannelReflection : public G4VDiscreteProcess {
 public:
  explicit GammaChannelReflection(const G4String& name = "GammaChannelReflection");
  ~GammaChannelReflection() override;

  G4bool IsApplicable(const G4ParticleDefinition& particle) override;

  G4double GetMeanFreePath(
      const G4Track& track,
      G4double previousStepSize,
      G4ForceCondition* condition) override;

  G4VParticleChange* PostStepDoIt(const G4Track& track, const G4Step& step) override;

  void SetProbabilities(G4double R, G4double A, G4double T);
  void LoadReflectivityTable(
      const G4String& path,
      ReflectivityLookupMode mode = ReflectivityLookupMode::kLinear,
      const G4String& stackId = "");
  void ClearReflectivityTable();
  void SetRecordHistory(G4bool enabled);
  void SetRequiredVolumeToken(const G4String& token);
  const ChannelReflectivity& GetProbabilities() const;
  const std::vector<ChannelBoundaryRecord>& GetHistory() const;
  void ClearHistory();
  void ResetCounters();
  G4int GetBoundaryCount() const;
  G4int GetReflectCount() const;
  G4int GetAbsorbCount() const;
  G4int GetLeakCount() const;

 private:
  G4bool IsChannelBoundary(const G4Step& step) const;
  const G4VPhysicalVolume* ChannelBoundaryVolume(const G4Step& step) const;
  G4ThreeVector SurfaceNormal(const G4Step& step, G4bool* valid) const;
  ChannelReflectivity LookupReflectivity(G4double energyKeV, G4double thetaRad) const;
  void RecordBoundary(
      const G4Track& track,
      const G4Step& step,
      G4double thetaRad,
      const ChannelReflectivity& probabilities,
      const G4ThreeVector& directionBefore,
      const G4ThreeVector& directionAfter,
      const G4String& action);

  ChannelReflectivity params_;
  ReflectivityTable table_;
  ReflectivityLookupMode lookupMode_;
  G4String stackId_;
  G4bool useTable_;
  G4bool recordHistory_;
  G4String requiredVolumeToken_;
  G4int nBoundary_;
  G4int nReflect_;
  G4int nAbsorb_;
  G4int nLeak_;
  std::vector<ChannelBoundaryRecord> history_;
};

}  // namespace optics

#endif
