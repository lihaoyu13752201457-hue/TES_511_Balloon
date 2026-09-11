#ifndef __M05LifecycleState__
#define __M05LifecycleState__

#include <stdexcept>
#include <string>

// Pure C++ event-state machine shared by the shadow scorer and its
// zero-transport fixture.  It deliberately has no Geant4/ROOT dependency.
class M05LifecycleState
{
public:
  M05LifecycleState() : m_Expected(0), m_Current(0), m_Generated(0), m_Started(0),
    m_Completed(0), m_NativePopulated(0), m_Aborted(0),
    m_HaveBegun(false), m_HaveGenerated(false), m_HaveStarted(false) {}

  void BeginGeneratedEvent(long simulationEventID, long expected)
  {
    if (m_Expected == 0) m_Expected = expected;
    Require(expected > 0 && expected == m_Expected && !m_HaveBegun,
            "generated-event begin overlaps an active event or changes expected count");
    Require(simulationEventID == m_Generated + 1 && simulationEventID <= m_Expected,
            "generated-event ID/order mismatch");
    m_Current = simulationEventID;
    m_HaveBegun = true;
    m_HaveGenerated = false;
    m_HaveStarted = false;
  }

  void MarkGenerated()
  {
    Require(m_HaveBegun && !m_HaveGenerated,
            "generated primary outside its event lifecycle");
    m_HaveGenerated = true;
    ++m_Generated;
  }

  void ConfirmEventStarted(long simulationEventID)
  {
    Require(m_HaveBegun && m_HaveGenerated && !m_HaveStarted && simulationEventID == m_Current,
            "BeginOfEventAction did not confirm the generated event");
    m_HaveStarted = true;
    ++m_Started;
  }

  void FinishEvent(long simulationEventID, bool aborted, bool nativeEventPopulated)
  {
    Require(m_HaveBegun && m_HaveGenerated && m_HaveStarted && simulationEventID == m_Current,
            "event completion outside confirmed lifecycle");
    Require(simulationEventID == m_Completed + 1, "completed-event ID/order mismatch");
    if (aborted) {
      Require(!nativeEventPopulated, "aborted event cannot be marked native-populated");
      ++m_Aborted;
    } else {
      Require(nativeEventPopulated, "non-aborted event lacks populated native event");
      ++m_NativePopulated;
    }
    ++m_Completed;
    m_HaveBegun = false;
    m_HaveGenerated = false;
    m_HaveStarted = false;
    m_Current = 0;
  }

  void RequireFinalClosure(long expected) const
  {
    Require(expected == m_Expected && !m_HaveBegun && m_Expected > 0,
            "run ended with wrong expected count or active/incomplete event");
    Require(m_Generated == m_Expected && m_Started == m_Expected && m_Completed == m_Expected,
            "generated/started/completed counts differ from tape length");
    Require(m_Aborted == 0, "aborted_count must be zero");
    Require(m_NativePopulated == m_Expected, "native-populated count differs from tape length");
  }

  long CurrentID() const { return m_Current; }
  long GeneratedCount() const { return m_Generated; }
  long StartedCount() const { return m_Started; }
  long CompletedCount() const { return m_Completed; }
  long NativePopulatedCount() const { return m_NativePopulated; }
  long AbortedCount() const { return m_Aborted; }
  bool IsActive() const { return m_HaveBegun; }
  bool IsGenerated() const { return m_HaveGenerated; }
  bool IsStarted() const { return m_HaveStarted; }

private:
  static void Require(bool condition, const std::string& message)
  {
    if (!condition) throw std::runtime_error("M05LifecycleState fail-closed: " + message);
  }

  long m_Expected;
  long m_Current;
  long m_Generated;
  long m_Started;
  long m_Completed;
  long m_NativePopulated;
  long m_Aborted;
  bool m_HaveBegun;
  bool m_HaveGenerated;
  bool m_HaveStarted;
};

#endif
