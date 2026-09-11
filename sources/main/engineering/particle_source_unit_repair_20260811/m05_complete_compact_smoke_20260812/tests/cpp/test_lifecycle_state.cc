#include "M05LifecycleState.hh"

#include <functional>
#include <iostream>
#include <stdexcept>

namespace {
void ExpectThrow(const std::function<void()>& action, const char* label)
{
  try { action(); }
  catch (const std::runtime_error&) { return; }
  throw std::runtime_error(std::string("expected fail-closed exception: ") + label);
}
}

int main()
{
  M05LifecycleState state;
  ExpectThrow([&](){ state.MarkGenerated(); }, "generation before begin");
  state.BeginGeneratedEvent(1, 2);
  ExpectThrow([&](){ state.ConfirmEventStarted(1); }, "start before generated tuple");
  state.MarkGenerated();
  state.ConfirmEventStarted(1);
  ExpectThrow([&](){ state.FinishEvent(1, false, false); }, "completed event without native population");
  state.FinishEvent(1, false, true);
  state.BeginGeneratedEvent(2, 2);
  state.MarkGenerated();
  state.ConfirmEventStarted(2);
  state.FinishEvent(2, false, true);
  state.RequireFinalClosure(2);
  if (state.GeneratedCount() != 2 || state.StartedCount() != 2 ||
      state.CompletedCount() != 2 || state.NativePopulatedCount() != 2 ||
      state.AbortedCount() != 0) return 2;

  M05LifecycleState aborted;
  aborted.BeginGeneratedEvent(1, 1);
  aborted.MarkGenerated();
  aborted.ConfirmEventStarted(1);
  aborted.FinishEvent(1, true, false);
  ExpectThrow([&](){ aborted.RequireFinalClosure(1); }, "aborted run publication");

  std::cout << "PASS lifecycle_state_nontransport\n";
  return 0;
}
