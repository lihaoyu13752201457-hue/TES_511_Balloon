# Installed MEGAlib Activation Semantics

Decision: use EventList for exact-position custom source-v2 authority, and use `Run.ActivationSources <isotope-store.dat>` for the native volume-based oracle.

Evidence from installed source code:
- `MCParameterFile.cc:977-985` parses `Source.EventList <file>`.
- `MCSource.cc:2274-2289` requires 15 EventList tokens and reads particle type from token 2, an excitation field from token 3, time from token 4, and position from tokens 5-7.
- `MCSource.cc:2466-2479`, `2636-2642`, and `2792-2797` use the EventList particle, energy, position, and direction when firing the particle gun.
- `MCParameterFile.cc:919-929` parses `Run.ActivationSources`, loads an `MCIsotopeStore`, and adds sources from `CreateSourceListByActivity()`.
- `MCIsotopeStore.cc:175-188` documents the isotope-store format: `VN <volume>` and `RP <ZA> <excitation_keV> <value>`.
- `MCIsotopeStore.cc:239-282` loads excitation from token 2 in keV and value from token 3.
- `MCIsotopeStore.cc:371-394` creates activation sources with particle type, particle excitation, activation spectrum, near-field activation beam, volume, and flux.
- `MCSource.cc:2502-2521` resolves the source particle definition through `MCSteppingAction::GetParticleDefinition(particle_type, particle_excitation)`.
- `MCSteppingAction.cc:1911-1922` asks Geant4's ion table for `GetIon(Z, A, excitation)`.

Rejected path:
- Ordinary source-card `ParticleType` supports the ZA integer but has no parser token for excitation.
- The `.Particles Ion <ZA> <excitation>` syntax is not accepted by this installed parser; see `excited_ion_source_syntax_test.log`.

Implication for WP04:
- The current G1 inventory has no positive non-ground states, so WP04 can emit an exact-position EventList and external weight ledger without state substitution.
- Positive nonzero excitation in a future run must block or move to a hybrid/native stream until EventList excitation units are proven; the file parser reads token 3 as an integer and does not visibly multiply by keV.
- WP04 should also emit a matching isotope-store activity file so WP05 can run the native volume-based comparison.
- ParticleType-only delayed source cards can be retained only as legacy/comparator evidence, not as the state-resolved authority.
