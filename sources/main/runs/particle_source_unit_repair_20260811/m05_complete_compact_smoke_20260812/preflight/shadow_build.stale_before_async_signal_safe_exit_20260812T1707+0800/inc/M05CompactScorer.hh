#ifndef __M05CompactScorer__
#define __M05CompactScorer__

#include "G4ThreeVector.hh"
#include "M05DurableFile.hh"
#include "M05LifecycleState.hh"

#include <cstdint>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <vector>

class G4Ions;
class G4Step;
class G4TouchableHistory;
class MCParameterFile;
class MSimEvent;

class M05CompactScorer
{
public:
  static M05CompactScorer& Instance();
  // Async-signal-safe notification only sets a sig_atomic_t flag. Publication
  // is rejected later at the normal EndRun boundary.
  static void NotifyTerminationSignal();

  // Called only after MCMain::ParseCommandLine and MCMain::Initialize succeed.
  void ConfigureAfterInitialization(MCParameterFile& parameters);
  bool IsConfigured() const { return m_Configured; }
  bool IsCompactArm() const { return m_Arm == "C"; }

  // Geant4 lifecycle: GeneratePrimaries precedes BeginOfEventAction.
  void BeginGeneratedEvent(long simulationEventID);
  void RecordGenerated(long eventListID,
                       const std::string& sourceName,
                       double sourceTimeSeconds,
                       int particle,
                       double excitationKeV,
                       const G4ThreeVector& position,
                       const G4ThreeVector& direction,
                       const G4ThreeVector& polarization,
                       double energyKeV);
  void ConfirmEventStarted(long simulationEventID);
  void RecordSensitiveDeposit(const G4Step* step,
                              double postGlobalTimeSeconds,
                              const std::string& stepProcess);
  void RecordCommittedIsotope(unsigned long productionSerial,
                              const G4Step* step,
                              G4TouchableHistory* history,
                              G4Ions* nucleus,
                              double postGlobalTimeSeconds,
                              const std::string& stepProcess);
  void EndEvent(MSimEvent* event, bool aborted, bool nativeEventPopulated);
  void EndRun(double simulatedTimeSeconds,
              unsigned long nativeAddedIsotopes,
              bool nativeStopConditionReached,
              const std::string& nativeDatPath,
              int parallelID,
              int incarnationID);

private:
  M05CompactScorer();
  ~M05CompactScorer();
  M05CompactScorer(const M05CompactScorer&) = delete;
  M05CompactScorer& operator=(const M05CompactScorer&) = delete;

  struct TapeRow {
    long rowIndex0 = -1;
    long globalRowIndex0 = -1;
    long eventListID = -1;
    std::string stableRootID;
    std::string driver;
    std::string family;
    std::string mode;
    std::string sourceCardSHA256;
    std::string sourceContractSHA256;
    int particle = 0;
    double excitationKeV = 0.0;
    double sourceTimeSeconds = 0.0;
    double position[3] = {0.0, 0.0, 0.0};
    double direction[3] = {0.0, 0.0, 0.0};
    double polarization[3] = {0.0, 0.0, 0.0};
    double energyKeV = 0.0;
    std::string rawLineSHA256;
    std::string expectedEventListBinary64SHA256;
    std::string expectedGeneratedBinary64SHA256;
    std::string expectedGeneratedTupleSHA256;
    bool control = false;
  };

  struct PixelAggregate {
    std::string physicalVolume;
    std::string touchablePath;
    double energyKeV = 0.0;
    double weightedPrePositionCM[3] = {0.0, 0.0, 0.0};
    double weightedPostTimeSeconds = 0.0;
    double postTimeMinSeconds = 0.0;
    double postTimeMaxSeconds = 0.0;
    unsigned long depositCount = 0;
    unsigned long firstSequence = 0;
    unsigned long lastSequence = 0;
  };

  struct BlockAggregate {
    std::string role;
    std::string physicalVolume;
    double energyKeV = 0.0;
    double weightedPostTimeSeconds = 0.0;
    double postTimeMinSeconds = 0.0;
    double postTimeMaxSeconds = 0.0;
    unsigned long depositCount = 0;
  };

  void LoadTapeBytes(const std::string& bytes);
  const TapeRow& CurrentRow() const;
  std::string ClassifyVolume(const std::string& physicalVolume) const;
  std::string TouchablePath(const G4TouchableHistory* history) const;
  std::string QuantizedTupleSHA256(int particle,
                                  double excitationKeV,
                                  double sourceTimeSeconds,
                                  const double position[3],
                                  const double direction[3],
                                  const double polarization[3],
                                  double energyKeV) const;
  std::string IAStateSHA256(int particle,
                            double iaTimeSeconds,
                            const double position[3],
                            const double direction[3],
                            const double polarization[3],
                            double energyKeV) const;
  std::string Binary64TupleSHA256(int particle,
                                 double excitationKeV,
                                 double sourceTimeSeconds,
                                 const double position[3],
                                 const double direction[3],
                                 const double polarization[3],
                                 double energyKeV) const;
  std::string SHA256(const std::string& value) const;
  std::string SHA256File(const std::string& path) const;
  std::string Escape(const std::string& value) const;
  std::string AncestryChain(int trackID) const;
  void Require(bool condition, const std::string& message) const;
  void OpenOutputs();
  void FlushSyncClose(M05DurableFile& stream, const std::string& path);
  void PublishTransaction();
  static bool TerminationRequested();

  bool m_Configured;
  bool m_Finalized;
  std::string m_Arm;
  std::string m_Geometry;
  std::string m_Mode;
  std::string m_Family;
  std::string m_JobID;
  long m_ShardIndex;
  long m_Seed;
  std::string m_OutputPrefix;
  std::string m_StageDirectory;
  std::string m_FinalDirectory;
  std::string m_RecordSchemaSHA256;
  std::string m_WhitelistSHA256;
  std::string m_GeometryClassificationSHA256;
  std::string m_GeometryBundleSHA256;
  std::string m_TapeSHA256;
  std::string m_TapePath;
  std::string m_RuntimeSourceCardSHA256;
  std::string m_CorrectedSourceCardSHA256;
  std::string m_SourceContractSHA256;
  std::string m_NativeDatPath;
  std::vector<TapeRow> m_Tape;
  M05LifecycleState m_Lifecycle;
  long m_RootCount;
  long m_GeneratedObservationRowCount;
  long m_InitCount;
  long m_SECount;
  long m_IDCount;
  long m_EventRowCount;
  long m_PixelRowCount;
  long m_DepositRowCount;
  long m_VetoBlockRowCount;
  long m_TruthIndexRowCount;
  long m_TESZeroControlCount;
  std::set<long> m_NativeIDs;
  int m_GeneratedParticle;
  double m_GeneratedExcitationKeV;
  double m_GeneratedSourceTimeSeconds;
  double m_GeneratedPosition[3];
  double m_GeneratedDirection[3];
  double m_GeneratedPolarization[3];
  double m_GeneratedEnergyKeV;
  unsigned long m_DepositSequence;
  unsigned long m_RPCount;
  double m_KaptonDiagnosticKeV;
  std::map<std::string, PixelAggregate> m_PixelAggregates;
  std::map<std::string, BlockAggregate> m_BlockAggregates;

  M05DurableFile m_RootOut;
  M05DurableFile m_GeneratedObservationOut;
  M05DurableFile m_EventOut;
  M05DurableFile m_PixelOut;
  M05DurableFile m_DepositOut;
  M05DurableFile m_VetoBlockOut;
  M05DurableFile m_ActivationOut;
  M05DurableFile m_TruthOut;
  M05DurableFile m_TruthIndexOut;
  M05DurableFile m_FooterOut;
};

#endif
