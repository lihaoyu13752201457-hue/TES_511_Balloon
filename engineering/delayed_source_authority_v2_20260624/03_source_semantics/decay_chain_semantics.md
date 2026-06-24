# Decay Chain Semantics

The custom exact-position stream uses EventList rows. Its source-card normalization is external: each row has a weight from the WP04 activity ledger, and selected-rate analysis must consume the EventList weight sidecar.

`ActivationSources` values are interpreted as activities in Bq by `CreateSourceListByActivity()` and are reserved for the native volume-based oracle.

For custom exact-position delayed-source transport, use:
- `PhysicsListRadioactiveDecay true`
- `DecayMode ActivationDelayedDecay`
- `Run.Source <event-list-source>`
- `<event-list-source>.EventList <source-v2.eventlist.dat>`

For native cross-check transport, use:
- `Run.ActivationSources <source-v2-activity-store.dat>`

The source nucleus is the primary delayed decay. Secondary decays inside the chain are handled by the installed Geant4 radioactive-decay path. `MCSteppingAction.cc` applies `DetectorTimeConstant` to decide whether non-primary delayed secondaries are kept in the same event or moved to future-event handling.

This gate does not promote a numerical delayed rate. It only chooses the source representation needed by WP04.
